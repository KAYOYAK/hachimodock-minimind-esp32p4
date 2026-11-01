/* Pet host: drive the official HachimoDock device from the ALINTEK ESP32-P4.
 *
 * USB host -> CH343 (1A86:55D3) at 4 Mbaud, official JSONL protocol
 * (pet-usb-jsonl-v3): heartbeat, hello/ack handshake, session/current +
 * speech/text bubbles, input/event reception.
 */
#pragma once

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*pet_log_fn)(const char *msg);
typedef void (*pet_input_fn)(const char *event_name, const char *action);

/* Install the USB host stack and start talking to the pet. Non-blocking. */
void pet_host_start(void);

/* Optional logger (e.g. route to the USB console). */
void pet_host_set_logger(pet_log_fn fn);

/* Called for every pet input/event (joystick, encoder press...). */
void pet_host_set_input_cb(pet_input_fn fn);

/* Update what the pet main screen shows: session state + speech bubble text.
 * state: "thinking" / "working" / "waiting_user" / "done" / "error"
 * status_text: short tag shown in the bubble (e.g. "thinking"). */
void pet_host_report(const char *state, const char *text, const char *status_text);

/* True once the device hello handshake has been acknowledged. */
bool pet_host_ready(void);

#ifdef __cplusplus
}
#endif
