/* Pet host implementation: USB-A host -> CH343 -> HachimoDock JSONL protocol. */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_timer.h"

#include "usb/usb_host.h"
#include "usb/cdc_acm_host.h"
#include "usb/vcp_ch34x.h"

#include "pet_host.h"

#define PET_VID        0x1A86
#define PET_PID        0x55D3
#define PET_BAUD       4000000
#define SESSION_ID     "p4-local-1"
#define AGENT_ID       "mk-local"

static const char *TAG = "pet_host";

static pet_log_fn s_log_fn = NULL;
static pet_input_fn s_input_fn = NULL;

static volatile bool s_open = false;
static volatile bool s_ready = false;
static volatile bool s_ack_sent = false;
static volatile bool s_hello_seen = false;
static volatile bool s_connect_pending = false;
static volatile bool s_dirty = false;

static cdc_acm_dev_hdl_t s_dev = NULL;
static SemaphoreHandle_t s_lock = NULL;

static char s_state[24] = "waiting_user";
static char s_status[24] = "idle";
static char s_text[512] = "你好，我是 ALINTEK 板上的本地 AI";

/* line parser state */
static char s_line[8192];
static int s_line_pos = 0;

static void plog(const char *fmt, ...) {
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    ESP_LOGI(TAG, "%s", buf);
    if (s_log_fn) s_log_fn(buf);
}

static void str_copy(char *dst, size_t cap, const char *src) {
    if (cap == 0) return;
    size_t i = 0;
    for (; src && src[i] && i + 1 < cap; i++) dst[i] = src[i];
    dst[i] = 0;
}

static void json_escape(const char *in, char *out, size_t cap) {
    size_t o = 0;
    for (size_t i = 0; in && in[i] && o + 2 < cap; i++) {
        char c = in[i];
        if (c == '"' || c == '\\') {
            out[o++] = '\\';
            out[o++] = c;
        } else if ((unsigned char)c < 0x20) {
            out[o++] = ' ';
        } else {
            out[o++] = c;
        }
    }
    out[o] = 0;
}

static void copy_field(const char *line, const char *key, char *out, size_t cap) {
    out[0] = 0;
    const char *p = strstr(line, key);
    if (!p) return;
    p += strlen(key);
    size_t i = 0;
    while (*p && *p != '"' && i + 1 < cap) {
        out[i++] = *p++;
    }
    out[i] = 0;
}

static int ch343_baud_fd(unsigned baud, unsigned char *fct, unsigned char *dvs) {
    unsigned char a, b;
    unsigned long c;
    if (baud == 6000000 || baud == 4000000 || baud == 2400000 ||
        baud == 921600 || baud == 307200 || baud == 256000) {
        b = 7; c = 12000000;
    } else if (baud > 6000000 / 255) { b = 3; c = 6000000; }
    else if (baud > 750000 / 255) { b = 2; c = 750000; }
    else if (baud > 93750 / 255) { b = 1; c = 93750; }
    else { b = 0; c = 11719; }
    a = (unsigned char)(c / baud);
    if (a == 0 || a == 0xFF) return -1;
    if ((c / a - baud) > (baud - c / (a + 1))) a++;
    a = 256 - a;
    *fct = a; *dvs = b;
    return 0;
}

/* CH343 vendor requests (WCH ch343.c semantics): 0xA1 line coding+baud,
 * 0xA4 modem control (~value; 0xFFFF = DTR/RTS deasserted). */
static void ch343_raw_init(void) {
    unsigned char fct = 0, dvs = 0;
    int ok = ch343_baud_fd(PET_BAUD, &fct, &dvs);
    esp_err_t e1 = cdc_acm_host_send_custom_request(s_dev, 0x40, 0xA1, 0xC38C,
                                                    (uint16_t)((fct << 8) | dvs), 0, NULL);
    plog("CH343 init: ok=%d fct=%u dvs=%u -> %s", ok, fct, dvs, esp_err_to_name(e1));
    cdc_acm_host_send_custom_request(s_dev, 0x40, 0xA4, 0xFFBF, 0, 0, NULL);
    vTaskDelay(pdMS_TO_TICKS(150));
    esp_err_t e2 = cdc_acm_host_send_custom_request(s_dev, 0x40, 0xA4, 0xFFFF, 0, 0, NULL);
    plog("CH343 modem deassert: %s", esp_err_to_name(e2));
}

static esp_err_t pet_tx(const char *s) {
    if (!s_open || !s_dev) return ESP_ERR_INVALID_STATE;
    plog("TX %u: %.180s", (unsigned)strlen(s), s);
    return cdc_acm_host_data_tx_blocking(s_dev, (const uint8_t *)s, strlen(s), 1000);
}

/* ---------- RX JSONL parser ---------- */

static void handle_json_line(char *line) {
    if (strstr(line, "\"topic\":\"hello\"")) {
        s_hello_seen = true;
        char devid[64];
        copy_field(line, "\"boardDeviceId\":\"", devid, sizeof(devid));
        plog("hello from pet %s", devid);
    } else if (strstr(line, "\"topic\":\"protocol/ack\"")) {
        if (strstr(line, "\"ok\":false")) plog("device NACK: %.400s", line);
    } else if (strstr(line, "\"topic\":\"input/event\"")) {
        char evt[64], act[64];
        copy_field(line, "\"event\":\"", evt, sizeof(evt));
        copy_field(line, "\"action\":\"", act, sizeof(act));
        plog("input: %s / %s", evt, act);
        if (s_input_fn) s_input_fn(evt, act);
    }
}

static bool rx_cb(const uint8_t *data, size_t len, void *arg) {
    (void)arg;
    for (size_t i = 0; i < len; i++) {
        char c = (char)data[i];
        if (c == '\n') {
            s_line[s_line_pos] = 0;
            if (s_line_pos > 0 && s_line[0] == '{') handle_json_line(s_line);
            s_line_pos = 0;
        } else if (c != '\r') {
            if (s_line_pos < (int)sizeof(s_line) - 1) s_line[s_line_pos++] = c;
        }
    }
    return true;
}

static void event_cb(const cdc_acm_host_dev_event_data_t *evt, void *ctx) {
    (void)ctx;
    if (evt->type == CDC_ACM_HOST_DEVICE_DISCONNECTED) {
        plog("pet disconnected");
        s_open = false;
        s_ready = false;
        s_ack_sent = false;
        s_hello_seen = false;
        s_dev = NULL;
    } else if (evt->type == CDC_ACM_HOST_ERROR) {
        plog("CDC error %d", evt->data.error);
    }
}

static void new_dev_cb(usb_device_handle_t usb_dev) {
    const usb_device_desc_t *desc = NULL;
    if (usb_host_get_device_descriptor(usb_dev, &desc) != ESP_OK || !desc) return;
    plog("USB device VID=0x%04X PID=0x%04X", desc->idVendor, desc->idProduct);
    if (desc->idVendor == PET_VID) s_connect_pending = true;
}

/* ---------- tasks ---------- */

static void usb_lib_task(void *arg) {
    (void)arg;
    const usb_host_config_t host_config = { .skip_phy_setup = false, .intr_flags = ESP_INTR_FLAG_LOWMED };
    ESP_ERROR_CHECK(usb_host_install(&host_config));
    const cdc_acm_host_driver_config_t driver_config = {
        .driver_task_stack_size = 4096,
        .driver_task_priority = 5,
        .xCoreID = 0,
        .new_dev_cb = new_dev_cb,
    };
    ESP_ERROR_CHECK(cdc_acm_host_install(&driver_config));
    plog("USB host installed");
    while (1) {
        uint32_t flags = 0;
        usb_host_lib_handle_events(portMAX_DELAY, &flags);
        (void)flags;
    }
}

static void try_open(void) {
    const cdc_acm_host_device_config_t dev_config = {
        .connection_timeout_ms = 0,
        .out_buffer_size = 1024,
        .in_buffer_size = 0,
        .user_arg = NULL,
        .event_cb = event_cb,
        .data_cb = rx_cb,
    };
    cdc_acm_dev_hdl_t dev = NULL;
    esp_err_t err = ch34x_vcp_open(PET_PID, 0, &dev_config, &dev);
    if (err != ESP_OK) {
        plog("ch34x open failed: %s", esp_err_to_name(err));
        return;
    }
    s_dev = dev;
    ch343_raw_init();
    s_open = true;
    s_ready = false;
    s_ack_sent = false;
    s_hello_seen = false;
    plog("pet opened at %d baud", PET_BAUD);
}

static void host_loop_task(void *arg) {
    (void)arg;
    int tick = 0;
    while (1) {
        if (s_connect_pending && !s_open) {
            s_connect_pending = false;
            vTaskDelay(pdMS_TO_TICKS(300));
            try_open();
        }
        if (s_open) {
            char buf[1024];
            if (s_hello_seen && !s_ack_sent) {
                snprintf(buf, sizeof(buf),
                         "{\"topic\":\"ack\",\"payload\":{\"desktopDeviceId\":\"alintek-p4-local\"}}\n");
                pet_tx(buf);
                s_ack_sent = true;
                s_ready = true;
                plog("ack sent, handshake complete");
            }
            if (s_ready) {
                snprintf(buf, sizeof(buf),
                         "{\"topic\":\"system/heartbeat\",\"payload\":{\"requestId\":\"hb-%d\",\"ts\":%lld}}\n",
                         tick, (long long)(esp_timer_get_time() / 1000));
                pet_tx(buf);
                if (tick % 2 == 0) {
                    char state[24], status[24], text[512], text_esc[600];
                    xSemaphoreTake(s_lock, portMAX_DELAY);
                    str_copy(state, sizeof(state), s_state);
                    str_copy(status, sizeof(status), s_status);
                    str_copy(text, sizeof(text), s_text);
                    xSemaphoreGive(s_lock);
                    json_escape(text, text_esc, sizeof(text_esc));
                    snprintf(buf, sizeof(buf),
                             "{\"topic\":\"session/current\",\"payload\":{\"agentId\":\"%s\",\"index\":0,\"count\":1,"
                             "\"activeSessionIds\":[\"%s\"],\"displayEnabled\":true,"
                             "\"sessions\":[{\"id\":\"%s\",\"title\":\"ALINTEK 本地 AI\",\"state\":\"%s\","
                             "\"transitionRevision\":%lld,\"terminalRemainingMs\":60000}]}}\n",
                             AGENT_ID, SESSION_ID, SESSION_ID, state, (long long)(esp_timer_get_time() / 1000));
                    pet_tx(buf);
                    if (s_dirty || tick % 6 == 0) {
                        snprintf(buf, sizeof(buf),
                                 "{\"topic\":\"speech/text\",\"payload\":{\"sessionId\":\"%s\","
                                 "\"displayTitle\":\"ALINTEK 本地 AI\",\"displayContent\":\"%s\","
                                 "\"status\":\"%s\",\"statusText\":\"%s\",\"tsMs\":%lld}}\n",
                                 SESSION_ID, text_esc, state, status, (long long)(esp_timer_get_time() / 1000));
                        pet_tx(buf);
                        s_dirty = false;
                    }
                }
                tick++;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void pet_host_set_logger(pet_log_fn fn) { s_log_fn = fn; }
void pet_host_set_input_cb(pet_input_fn fn) { s_input_fn = fn; }
bool pet_host_ready(void) { return s_ready; }

void pet_host_report(const char *state, const char *text, const char *status_text) {
    if (s_lock) xSemaphoreTake(s_lock, portMAX_DELAY);
    str_copy(s_state, sizeof(s_state), state ? state : "waiting_user");
    str_copy(s_status, sizeof(s_status), status_text ? status_text : "idle");
    if (text) str_copy(s_text, sizeof(s_text), text);
    s_dirty = true;
    if (s_lock) xSemaphoreGive(s_lock);
}

void pet_host_start(void) {
    s_lock = xSemaphoreCreateMutex();
    xTaskCreatePinnedToCore(usb_lib_task, "pet_usb", 6144, NULL, 4, NULL, 0);
    xTaskCreatePinnedToCore(host_loop_task, "pet_loop", 12288, NULL, 3, NULL, 0);
    plog("pet host started, waiting for USB device");
}
