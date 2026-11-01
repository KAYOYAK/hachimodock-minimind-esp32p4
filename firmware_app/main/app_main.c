/* MiniMind-3 on ESP32-P4 — 独立（离线）对话固件
 *
 * 流程：PSRAM → 挂载 TF 卡（必要时格式化 FAT32）→ 读 /sdcard/model.kmcu 到 PSRAM
 *       → km_open/km_fast_build（打包权重零拷贝）→ KV/scratch →
 *       通过 USB-Serial-JTAG（板子的 USB-C "USB" 口）交互：
 *         - 缺模型时进入上传模式（PC 通过 USB 推送 model.kmcu / tokenizer.bin）
 *         - 模型就绪后进入聊天循环（chat template → 采样 decode → 反 tokenize）
 *
 * 说明：
 *  - 内核：C:\p4test\firmware\main\kmcu.c（Kestrel-MCU fork + QK-norm + packed GEMV）
 *  - 本板 UART 口只有日志（P4 UART0 的 RX 未接到 CH343），交互与烧写都走 USB 口。
 *  - 交互协议/PC 工具：tools/p4_upload.py、tools/p4_chat.py
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <errno.h>
#include <math.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_psram.h"
#include "esp_vfs_fat.h"
#include "sdmmc_cmd.h"
#include "driver/sdmmc_host.h"
#include "driver/usb_serial_jtag.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "kmcu.h"
#include "tokenizer.h"
#include "board_config.h"
#include "pet_host.h"

static const char *TAG = "minimind";

static km_model_t   s_model;
static km_fast_t    s_fast;
static km_tensor_t *s_tensors;
static km_state_t   s_state;
static uint8_t     *s_model_buf;
static uint8_t     *s_arena;
static size_t       s_arena_size;
static float       *s_kcache;
static float       *s_vcache;
static float       *s_scratch;
static int          s_n_tensors;
static sdmmc_card_t *s_card;

/* ---------------- 控制台：UART 日志 + USB-JTAG 交互 ---------------- */

static bool s_usb_console = false;

static void con_init(void) {
    usb_serial_jtag_driver_config_t cfg = {
        .tx_buffer_size = 4096,
        .rx_buffer_size = 8192,
    };
    if (usb_serial_jtag_driver_install(&cfg) == ESP_OK) {
        s_usb_console = true;
        ESP_LOGI(TAG, "USB-Serial-JTAG console ready");
    } else {
        ESP_LOGW(TAG, "USB-Serial-JTAG install failed; fallback to UART stdin/stdout");
    }
}

static void con_write(const void *data, size_t n) {
    if (n == 0) return;
    fwrite(data, 1, n, stdout);
    fflush(stdout);
    if (s_usb_console) {
        usb_serial_jtag_write_bytes(data, n, pdMS_TO_TICKS(1000));
    }
}

static void con_printf(const char *fmt, ...) {
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    con_write(buf, strlen(buf));
}

/* 读取 n 字节原始数据（上传模式用）；返回实际字节数。 */
static int con_read_raw(uint8_t *buf, int n, int timeout_ms) {
    int got = 0;
    while (got < n) {
        int r = 0;
        if (s_usb_console) {
            r = usb_serial_jtag_read_bytes(buf + got, (uint32_t)(n - got),
                                           pdMS_TO_TICKS(timeout_ms));
        } else {
            int c = fgetc(stdin);
            if (c >= 0) { buf[got++] = (uint8_t)c; r = 1; }
            else vTaskDelay(pdMS_TO_TICKS(10));
        }
        if (r > 0) got += r;
        else break;
    }
    return got;
}

/* 读一行文本（去掉 \r\n），超时返回 0。 */
static int con_read_line(char *line, int cap) {
    int n = 0;
    while (n < cap - 1) {
        uint8_t c = 0;
        int r = con_read_raw(&c, 1, 200);
        if (r <= 0) {
            if (n == 0) return 0;
            continue;
        }
        if (c == '\n' || c == '\r') {
            if (n == 0) continue;
            break;
        }
        line[n++] = (char)c;
    }
    line[n] = '\0';
    return n;
}

/* ---------------- 模型装载 ---------------- */

static bool mount_sd(void) {
    esp_vfs_fat_sdmmc_mount_config_t mcfg = {
        .format_if_mount_failed = false,
        .max_files = 4,
        .allocation_unit_size = 16 * 1024,
    };
    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    host.slot = SDMMC_HOST_SLOT_1;
    host.max_freq_khz = SDMMC_FREQ_HIGHSPEED;
    sdmmc_slot_config_t slot = SDMMC_SLOT_CONFIG_DEFAULT();
    slot.width = 4;
    slot.clk = BOARD_SD_CLK_IO;
    slot.cmd = BOARD_SD_CMD_IO;
    slot.d0  = BOARD_SD_D0_IO;
    slot.d1  = BOARD_SD_D1_IO;
    slot.d2  = BOARD_SD_D2_IO;
    slot.d3  = BOARD_SD_D3_IO;
    slot.flags |= SDMMC_SLOT_FLAG_INTERNAL_PULLUP;
    esp_err_t err = ESP_FAIL;
    for (int attempt = 0; attempt < 3; attempt++) {
        err = esp_vfs_fat_sdmmc_mount("/sdcard", &host, &slot, &mcfg, &s_card);
        if (err == ESP_OK) break;
        con_printf("SD mount attempt %d failed: %s\n", attempt + 1, esp_err_to_name(err));
        ESP_LOGW(TAG, "SD mount attempt %d failed: %s", attempt + 1, esp_err_to_name(err));
        vTaskDelay(pdMS_TO_TICKS(200));
    }
    if (err != ESP_OK) {
        con_printf("SD mount failed: %s\n", esp_err_to_name(err));
        ESP_LOGE(TAG, "SD mount failed: %s", esp_err_to_name(err));
        return false;
    }
    con_printf("SD mounted, %llu MB\n", (unsigned long long)(s_card->csd.capacity) / 2048);
    ESP_LOGI(TAG, "SD mounted, %llu MB", (unsigned long long)(s_card->csd.capacity) / 2048);
    return true;
}

static bool load_model_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        con_printf("model open failed: %s\n", path);
        ESP_LOGE(TAG, "open %s failed", path);
        return false;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    con_printf("model size: %ld bytes\n", sz);
    if (sz <= 0) { fclose(f); return false; }

    s_model_buf = NULL;
    int64_t t0 = esp_timer_get_time();
    s_model_buf = (uint8_t *)heap_caps_malloc((size_t)sz, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!s_model_buf) {
        con_printf("PSRAM alloc failed, fallback internal\n");
        s_model_buf = (uint8_t *)heap_caps_malloc((size_t)sz, MALLOC_CAP_DEFAULT);
    }
    if (!s_model_buf) {
        con_printf("no memory for model (%ld bytes)\n", sz);
        ESP_LOGE(TAG, "not enough memory for model (%ld bytes)", sz);
        fclose(f);
        return false;
    }
    con_printf("model buffer: %p\n", s_model_buf);

    size_t rd = 0;
    const size_t CHUNK = 1024 * 1024;
    while (rd < (size_t)sz) {
        size_t want = (size_t)sz - rd;
        if (want > CHUNK) want = CHUNK;
        size_t got = fread(s_model_buf + rd, 1, want, f);
        if (got != want) {
            con_printf("read short at %u (%u/%u)\n", (unsigned)rd, (unsigned)got, (unsigned)want);
            break;
        }
        rd += got;
        if ((rd % (8 * 1024 * 1024)) == 0) {
            con_printf("read %u MB\n", (unsigned)(rd / (1024 * 1024)));
        }
    }
    fclose(f);
    con_printf("model read done: %u/%ld, %lld ms\n", (unsigned)rd, sz,
               (long long)((esp_timer_get_time() - t0) / 1000));
    if (rd != (size_t)sz) {
        ESP_LOGE(TAG, "short read: %u/%ld", (unsigned)rd, sz);
        return false;
    }
    ESP_LOGI(TAG, "model loaded: %ld bytes in %lld ms", sz,
             (long long)((esp_timer_get_time() - t0) / 1000));
    return true;
}

static bool kernel_init(void) {
    memcpy(&s_n_tensors, s_model_buf + 52, 4);
    s_tensors = (km_tensor_t *)heap_caps_calloc((size_t)s_n_tensors, sizeof(km_tensor_t),
                                                MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!s_tensors) return false;
    memset(&s_model, 0, sizeof(s_model));
    s_model.tensors = s_tensors;
    km_err_t err;
    if (km_open(&s_model, s_model_buf, &err) != 0) {
        ESP_LOGE(TAG, "km_open: %s", err.buf);
        return false;
    }
    const km_arch_t *A = &s_model.arch;
    ESP_LOGI(TAG, "arch: layers=%u dim=%u nh=%u nkv=%u hd=%u ffn=%u vocab=%u ctx=%u",
             A->n_layers, A->dim, A->n_heads, A->n_kv_heads, A->head_dim,
             A->ffn_dim, A->vocab_size, A->max_seq);

    s_arena_size = km_fast_bytes(&s_model);
    s_arena = (uint8_t *)heap_caps_malloc(s_arena_size, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!s_arena) return false;
    s_fast.t = (km_ft_t *)heap_caps_calloc((size_t)s_n_tensors, sizeof(km_ft_t),
                                           MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!s_fast.t) return false;
    km_fast_build(&s_model, &s_fast, s_arena, s_arena_size);
    ESP_LOGI(TAG, "packed weights ready (arena=%u B), PSRAM free=%u B", (unsigned)s_arena_size,
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));

    uint32_t ctx = BOARD_CTX_TOKENS;
    if (ctx > A->max_seq) ctx = A->max_seq;
    size_t kv = (size_t)A->n_layers * ctx * A->n_kv_heads * A->head_dim;
    s_kcache = (float *)heap_caps_calloc(kv, sizeof(float), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    s_vcache = (float *)heap_caps_calloc(kv, sizeof(float), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    s_scratch = (float *)heap_caps_malloc(km_scratch_bytes(A),
                                          MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!s_kcache || !s_vcache || !s_scratch) {
        ESP_LOGE(TAG, "KV/scratch alloc failed");
        return false;
    }
    km_state_init(&s_state, A, ctx, s_kcache, s_vcache, s_scratch);
    ESP_LOGI(TAG, "KV ctx=%u tokens, PSRAM free=%u B after KV", (unsigned)ctx,
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
    return true;
}

/* ---------------- 上传模式（USB-Serial-JTAG 原始字节） ----------------
 * 协议（PC 端 tools/p4_upload.py）：
 *   固件: "MMUP1\n"（每次进入上传模式后等待命令）
 *   PC:  "PUT <filename> <size>\n"；固件: "READY\n"，随后 PC 发送 size 字节；固件写入后 "DONE\n"
 *   PC:  "END\n"；固件: "BYE\n" 然后重启
 */
static void upload_mode(void) {
    con_printf("MMUP1\n");
    ESP_LOGI(TAG, "upload mode ready");
    char cmd[192];
    for (;;) {
        int n = con_read_line(cmd, sizeof(cmd));
        if (n <= 0) continue;
        if (strncmp(cmd, "PUT ", 4) == 0) {
            char name[80];
            long size = 0;
            if (sscanf(cmd + 4, "%79s %ld", name, &size) != 2 || size <= 0) {
                con_printf("ERR\n");
                continue;
            }
            char path[128];
            snprintf(path, sizeof(path), "/sdcard/%s", name);
            FILE *f = fopen(path, "wb");
            if (!f) {
                con_printf("ERR\n");
                continue;
            }
            con_printf("READY\n");
            static uint8_t buf[8192];
            long remain = size;
            bool ok = true;
            while (remain > 0) {
                int want = remain > (long)sizeof(buf) ? (int)sizeof(buf) : (int)remain;
                int got = 0;
                while (got < want) {
                    int r = con_read_raw(buf + got, want - got, 5000);
                    if (r <= 0) break;
                    got += r;
                }
                if (got != want) {
                    ESP_LOGE(TAG, "upload read short: %d/%d", got, want);
                    ok = false;
                    break;
                }
                if (fwrite(buf, 1, (size_t)got, f) != (size_t)got) {
                    ESP_LOGE(TAG, "fwrite failed (errno=%d)", errno);
                    ok = false;
                    break;
                }
                con_write(".", 1);   /* flow-control ack: one byte per chunk */
                remain -= got;
            }
            fclose(f);
            if (ok) {
                con_printf("DONE\n");
                ESP_LOGI(TAG, "uploaded %s (%ld bytes)", name, size);
            } else {
                remove(path);
                con_printf("ERR\n");
                ESP_LOGE(TAG, "upload failed for %s", name);
            }
        } else if (strcmp(cmd, "END") == 0) {
            con_printf("BYE\n");
            vTaskDelay(pdMS_TO_TICKS(300));
            esp_restart();
        } else {
            con_printf("ERR\n");
        }
    }
}

/* ---------------- 对话 ---------------- */

static float s_temp = 0.8f;
static uint32_t s_rng = 0x12345678u;
static int s_max_new = 64;

static uint32_t rng_next(void) {
    s_rng = s_rng * 1664525u + 1013904223u;
    return s_rng;
}

static int pick_topk(const int *ids, const float *vals, int n) {
    if (n <= 0) return -1;
    if (n > 8) n = 8;
    if (s_temp <= 0.001f) return ids[0];
    float p[8];
    const float mx = vals[0];
    double sum = 0.0;
    for (int i = 0; i < n; i++) {
        p[i] = expf((vals[i] - mx) / s_temp);
        sum += p[i];
    }
    if (sum <= 0.0) return ids[0];
    double r = ((double)(rng_next() & 0xFFFFFFu) / 16777216.0) * sum;
    for (int i = 0; i < n; i++) {
        r -= p[i];
        if (r <= 0.0) return ids[i];
    }
    return ids[n - 1];
}

static void reset_state(void) {
    const km_arch_t *A = &s_model.arch;
    km_state_init(&s_state, A, s_state.n_ctx, s_kcache, s_vcache, s_scratch);
}

static int run_ids(const int *ids, int n, int max_new) {
    int ids_out[8];
    float vals_out[8];
    int last = -1;
    int64_t t0 = esp_timer_get_time();
    for (int i = 0; i < n; i++) {
        last = km_decode_step(&s_model, &s_fast, &s_state, ids[i], NULL,
                              ids_out, vals_out, 8, NULL, NULL, NULL, 0);
        if (last < 0) { ESP_LOGE(TAG, "decode failed (pos=%d)", i); return -1; }
    }
    int64_t t1 = esp_timer_get_time();
    con_printf("Assistant: ");
    int next = pick_topk(ids_out, vals_out, 8);
    int gen = 0;
    while (gen < max_new && next >= 0) {
        if (next == mm_tok_eos()) break;
        char piece[64];
        if (mm_tok_decode(&next, 1, piece, sizeof(piece)) > 0) {
            con_write(piece, strlen(piece));
        } else {
            con_printf("[%d]", next);
        }
        gen++;
        last = km_decode_step(&s_model, &s_fast, &s_state, next, NULL,
                              ids_out, vals_out, 8, NULL, NULL, NULL, 0);
        if (last < 0) break;
        next = pick_topk(ids_out, vals_out, 8);
    }
    int64_t t2 = esp_timer_get_time();
    con_printf("\n");
    ESP_LOGI(TAG, "prompt %d tok: %.0f ms; %d new tok: %.0f ms/tok (%.2f tok/s, temp=%.2f)",
             n, (t1 - t0) / 1000.0, gen, (t2 - t1) / 1000.0 / (gen > 0 ? gen : 1),
             1000.0 * gen / (double)((t2 - t1) > 0 ? (t2 - t1) : 1), (double)s_temp);
    return 0;
}

static int chat_text(const char *text) {
    const char *prefix = "<|im_start|>user\n";
    const char *suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
    static int ids[512];
    int n = 0;
    int r = mm_tok_encode(prefix, ids + n, (int)(sizeof(ids) / sizeof(ids[0])) - n);
    if (r < 0) { con_printf("tokenizer not loaded\n"); return -1; }
    n += r;
    r = mm_tok_encode(text, ids + n, (int)(sizeof(ids) / sizeof(ids[0])) - n);
    if (r < 0) return -1;
    n += r;
    r = mm_tok_encode(suffix, ids + n, (int)(sizeof(ids) / sizeof(ids[0])) - n);
    if (r < 0) return -1;
    n += r;
    return run_ids(ids, n, s_max_new);
}

static void bench_decode(int steps) {
    int ids_out[8];
    float vals_out[8];
    if (steps <= 0 || steps > 64) steps = 8;
    int64_t t0 = esp_timer_get_time();
    for (int i = 0; i < steps; i++) {
        km_decode_step(&s_model, &s_fast, &s_state, 1, NULL, ids_out, vals_out, 8, NULL, NULL, NULL, 0);
    }
    int64_t dt = esp_timer_get_time() - t0;
    double ms_tok = (double)dt / 1000.0 / steps;
    con_printf("bench: %d steps in %.1f ms => %.2f ms/token (%.3f tok/s)\n",
               steps, dt / 1000.0, ms_tok, 1000.0 / ms_tok);
    reset_state();
}

static void chat_loop(void) {
    static char line[512];
    con_printf("\nChat ready. Commands: /reset /greedy /temp X /maxnew N /bench N /ids ... /quit\n");
    for (;;) {
        con_printf("\nUser: ");
        int n;
        do { n = con_read_line(line, sizeof(line)); } while (n <= 0);
        if (strcmp(line, "/quit") == 0) { con_printf("bye\n"); return; }
        if (strcmp(line, "/reset") == 0) { reset_state(); con_printf("context reset\n"); continue; }
        if (strcmp(line, "/greedy") == 0) { s_temp = 0.0f; con_printf("greedy sampling\n"); continue; }
        if (strncmp(line, "/temp ", 6) == 0) {
            float t = strtof(line + 6, NULL);
            if (t >= 0.0f && t <= 2.0f) { s_temp = t; con_printf("temperature = %.2f\n", (double)t); }
            else con_printf("temperature must be 0..2\n");
            continue;
        }
        if (strncmp(line, "/maxnew ", 8) == 0) {
            int m = atoi(line + 8);
            if (m >= 1 && m <= 512) { s_max_new = m; con_printf("max_new = %d\n", m); }
            else con_printf("maxnew 1..512\n");
            continue;
        }
        if (strncmp(line, "/bench", 6) == 0) {
            int steps = atoi(line + 6);
            if (steps <= 0) steps = 8;
            con_printf("benchmarking %d decode steps...\n", steps);
            bench_decode(steps);
            continue;
        }
        if (strcmp(line, "/upload") == 0) {
            con_printf("entering upload mode\n");
            upload_mode();
            continue;
        }
        if (strncmp(line, "/enc ", 5) == 0) {
            static int eids[512];
            int r = mm_tok_encode(line + 5, eids, 512);
            con_printf("enc %d:", r);
            for (int i = 0; i < r && i < 64; i++) con_printf(" %d", eids[i]);
            con_printf("\n");
            continue;
        }
        if (strncmp(line, "/encp ", 6) == 0) {
            static int eids[512];
            int n = 0;
            int r = mm_tok_encode("<|im_start|>user\n", eids, 512);
            if (r > 0) n += r;
            r = mm_tok_encode(line + 6, eids + n, 512 - n);
            if (r > 0) n += r;
            r = mm_tok_encode("<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n", eids + n, 512 - n);
            if (r > 0) n += r;
            con_printf("encp %d:", n);
            for (int i = 0; i < n && i < 64; i++) con_printf(" %d", eids[i]);
            con_printf("\n");
            continue;
        }
        if (strncmp(line, "/ids ", 5) == 0) {
            int ids[256], cnt = 0;
            char *tok = strtok(line + 5, ",");
            while (tok && cnt < 256) { ids[cnt++] = atoi(tok); tok = strtok(NULL, ","); }
            con_printf("prompt ids: %d\n", cnt);
            run_ids(ids, cnt, s_max_new);
            continue;
        }
        chat_text(line);
    }
}

/* ---------------- 本地 AI -> 宠物气泡 ---------------- */

static volatile bool s_gen_busy = false;

static void host_log(const char *msg) {
    con_printf("[pet] %s\n", msg);
}

static void utf8_trim(char *s) {
    size_t n = strlen(s);
    if (n == 0) return;
    size_t i = n;
    while (i > 0 && (s[i - 1] & 0xC0) == 0x80) i--;
    if (i == 0) { s[0] = 0; return; }
    unsigned char lead = (unsigned char)s[i - 1];
    size_t need = 1;
    if ((lead & 0x80) == 0) need = 1;
    else if ((lead & 0xE0) == 0xC0) need = 2;
    else if ((lead & 0xF0) == 0xE0) need = 3;
    else if ((lead & 0xF8) == 0xF0) need = 4;
    if (n - (i - 1) < need) s[i - 1] = 0;
}

static char s_out_text[1024];

static void ai_generate_and_show(const char *user) {
    static const char *prefix = "<|im_start|>user\n";
    static const char *suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
    static int ids[512];
    static int ids_out[8];
    static float vals_out[8];
    int n = 0;
    int r = mm_tok_encode(prefix, ids, 512);
    if (r <= 0) return;
    n += r;
    r = mm_tok_encode(user, ids + n, 512 - n);
    if (r <= 0) return;
    n += r;
    r = mm_tok_encode(suffix, ids + n, 512 - n);
    if (r <= 0) return;
    n += r;

    reset_state();
    int last = 0;
    for (int i = 0; i < n; i++) {
        last = km_decode_step(&s_model, &s_fast, &s_state, ids[i], NULL,
                              ids_out, vals_out, 8, NULL, NULL, NULL, 0);
        if (last < 0) return;
    }
    s_temp = 0.0f;   /* greedy */
    int next = pick_topk(ids_out, vals_out, 8);
    int gen = 0;
    int len = 0;
    s_out_text[0] = 0;
    pet_host_report("working", "……", "thinking");
    while (gen < 10 && next >= 0) {
        if (next == mm_tok_eos()) break;
        char piece[64];
        int pl = mm_tok_decode(&next, 1, piece, sizeof(piece));
        if (pl > 0 && len + pl < (int)sizeof(s_out_text) - 1) {
            memcpy(s_out_text + len, piece, pl);
            len += pl;
            s_out_text[len] = 0;
        }
        gen++;
        if (gen % 3 == 0) { utf8_trim(s_out_text); pet_host_report("working", s_out_text, "speaking"); }
        last = km_decode_step(&s_model, &s_fast, &s_state, next, NULL,
                              ids_out, vals_out, 8, NULL, NULL, NULL, 0);
        if (last < 0) break;
        next = pick_topk(ids_out, vals_out, 8);
    }
    if (len == 0) {
        const char *dots = "……";
        memcpy(s_out_text, dots, strlen(dots) + 1);
    }
    con_printf("[ai] %s\n", s_out_text);
    pet_host_report("waiting_user", s_out_text, "done");
}

static void gen_task(void *arg) {
    (void)arg;
    static const char *prompts[] = {
        "你好，介绍一下你自己",
        "讲个笑话",
        "你现在心情怎么样？",
        "用一句话夸夸我",
    };
    static int idx = 0;
    const char *p = prompts[idx % (int)(sizeof(prompts) / sizeof(prompts[0]))];
    idx++;
    con_printf("[ai] prompt: %s\n", p);
    ai_generate_and_show(p);
    s_gen_busy = false;
    vTaskDelete(NULL);
}

static void pet_input_cb(const char *evt, const char *action) {
    if (s_gen_busy) return;
    s_gen_busy = true;
    con_printf("[pet] trigger from %s / %s\n", evt, action);
    xTaskCreatePinnedToCore(gen_task, "gen", 16384, NULL, 3, NULL, 1);
}
void app_main(void) {
    con_init();
    con_printf("\n==== MiniMind-3 on ESP32-P4 (offline) ====\n");
    con_printf("PSRAM: %u bytes\n", (unsigned)esp_psram_get_size());
    if (esp_psram_get_size() < 28u * 1024u * 1024u) {
        ESP_LOGW(TAG, "PSRAM < 28MB: q3e4 (28.6MB) may not fit; use TF streaming or 26M model");
    }

    if (!mount_sd()) {
        con_printf("SD mount failed; check TF card\n");
        return;
    }
    if (!load_model_file(BOARD_MODEL_PATH)) {
        con_printf("model.kmcu not found -> USB upload mode\n");
        upload_mode();   /* never returns (restarts after END) */
        return;
    }
    if (!kernel_init()) {
        con_printf("kernel init failed\n");
        return;
    }
    if (mm_tok_load("/sdcard/tokenizer.bin") == 0) {
        con_printf("tokenizer loaded\n");
    } else {
        con_printf("tokenizer load failed\n");
    }

    /* Standalone mode: no PC. Drive the HachimoDock pet over USB-A and answer
     * its input events with the local MiniMind model. */
    pet_host_set_logger(host_log);
    pet_host_set_input_cb(pet_input_cb);
    pet_host_start();
    pet_host_report("waiting_user", "你好，我是 ALINTEK 板上的本地 AI，按一下摇杆中键试试", "idle");
    con_printf("standalone mode: waiting for pet input\n");
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}



