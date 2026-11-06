# v0.2.0 — measured, auditable ESP32-P4 deployment

This release freezes the **self-trained** MiniMind-3 q3e4 image and the measurement state behind the IEEE ESL letter draft.

## Model asset

- `model.kmcu` — self-trained q3e4 KMCU image
- size: **28,632,448 B (27.3 MiB)**
- SHA-256: `feb574f966980a71c53c6b1f56daf054ff267ed425b72ee5ce93f6002ccf87f0`

The image is quantized from the author's own `full_sft_768.pth` (not the upstream official weights); the earlier official-weight image is intentionally not published.

## Measured on ALINTEK ESP32-P4 rev v1.3 (360 MHz, 16 MB flash, 32 MB PSRAM)

| Item | Value |
|---|---|
| decode speed (q3e4, final kernel) | **1,612 ms/token = 0.620 tok/s** |
| cumulative speedup vs scalar baseline (5,622 ms) | **3.49×** (2.13× storage format, 1.23× hoisting, 1.34× batch unpack / 4-way / -O3) |
| GEMV share r (incl. lm_head) | **0.977** |
| PSRAM sequential read | **95.9 MB/s** (1 MB microbenchmark); GEMV effective 18.2 MB/s (19.2 incl. KV) |
| context | **192 tokens**, FP16 K/V, 2,359,296 B |
| windowed CE (ZH, 288 tok) | q4 6.949 / q3e4 7.087 (1.020×) / mixed 7.037 (1.013×) / q2 10.074 (1.450×) |
| windowed CE (EN, 288 tok) | q4 5.415 / q3e4 5.676 (1.048×) / q2 9.905 (1.829×) |
| 30-prompt rule score | q3e4 **80%** (= fp32 80%), q2 **0%** |
| host/device CE agreement | Δ<0.001 per window (q3e4, q2) |
| boot to ready | ≈20 s (mount 53 ms, TF read 20.6 s) |

Full report: [`docs/MEASUREMENTS.md`](https://github.com/KAYOYAK/hachimodock-minimind-esp32p4/blob/main/docs/MEASUREMENTS.md).

## Firmware features

- fully-resident packed-weight GEMV on ESP32-P4, zero-copy unpack + int16 activations
- CH343 USB-host bridge to HachimoDock at 4 Mbaud (JSON protocol, `speech/text` bubbles)
- SW1 (button 1) triggers local generation; SW2/SW3 and joystick/knob stay device-local
- UTF-8 sanitizing before JSON TX (byte-level BPE can emit invalid sequences)

## Paper

IEEE Embedded Systems Letters draft (4 pages, local compile verified): [`paper/draft.pdf`](https://github.com/KAYOYAK/hachimodock-minimind-esp32p4/blob/main/paper/draft.pdf).
