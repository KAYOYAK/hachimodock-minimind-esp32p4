# ESP32-P4 固件骨架（MiniMind-3 离线推理）

## 组成

- `main/kmcu_wrapper.c`：直接 include `../../firmware/main/kmcu.c`（Kestrel-MCU fork：
  QK-norm + packed q4/q3/q2 GEMV + tied head）。
- `main/app_main.c`：PSRAM 检查 → TF 卡挂载 → 读 `model.kmcu` 到 PSRAM →
  `km_open`/`km_fast_build`（打包权重零拷贝）→ KV/scratch → 串口对话循环。
- `main/tokenizer_stub.c`：tokenizer 占位；bring-up 用 `/ids` 直接喂 token id。
- `main/board_config.h`：**SD 卡/UART 引脚必须按 ALIENTEK 板原理图填写**（当前 -1 占位）。

## 依赖

- ESP-IDF **6.x**（target `esp32p4`），PSRAM ≥ 32MB 版本。
- 模型镜像：`../artifacts/minimind-3-q3e4.kmcu`（27.31 MiB，默认）；
  质量优先可用 `minimind-3-q4.kmcu`（34.34 MiB，但需 TF 卡流式，当前骨架未实现）。
- Tokenizer：`../artifacts/tokenizer.bin`（151 KB，由 `tools/export_tokenizer.py` 生成；
  已在 PC 上与 HF tokenizer 79/79 对拍通过）。
- TF 卡：FAT32，根目录放 `model.kmcu` 与 `tokenizer.bin`。

## 构建（Windows，已提供一键脚本）

```powershell
# 一次性：安装 ESP-IDF 6.x 与 esp32p4 工具链（见 docs/TOKENIZER.md 同目录的 README 步骤）
# 之后每次构建：
powershell -ExecutionPolicy Bypass -File C:\p4test\tools\build_firmware.ps1
# 可选：-Clean 全量重建

# 手动方式：
#   . C:\espidf\esp-idf\export.ps1
#   cd C:\p4test\firmware_app
#   idf.py set-target esp32p4
#   idf.py menuconfig     # ESP PSRAM: 32MB, HEX/OPI 按模块，200M
#   idf.py -p COM5 build flash monitor
```

准备 TF 卡：

```powershell
powershell -ExecutionPolicy Bypass -File C:\p4test\tools\prepare_sd.ps1 -Drive E:
```

首次启动会打印：
```
PSRAM: 33554432 bytes
SD mounted, ... MB
model loaded: 28632448 bytes in ... ms
arch: layers=8 dim=768 nh=8 nkv=4 hd=96 ffn=2432 vocab=6400 ctx=96
packed weights ready (arena=58368 B), PSRAM free=...
KV ctx=96 tokens, PSRAM free=...
```

## 上板 bring-up 命令

- `/ids 1,832,311,234,1968,2` — 直接喂 token id（验证推理链路，无需 tokenizer）。
- `/reset` — 清 KV cache。
- `/quit` — 退出循环。

模型 prompt 示例（MiniMind-3 chat template 的 token id）：
```
/ids 1,832,311,234,1968,294,2919,2360,441,1153,2,234,1,1388,570,811,234,25,234,234,26,234,234
```
（对应 `"<|im_start|>user\n你好，介绍一下你自己<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"`）

## 构建验证（本机已通过）

```
[674/674] Generated C:/p4test/firmware_app/build/minimind_p4.bin
minimind_p4.bin binary size 0x54ea0 bytes. Smallest app partition is 0x400000 bytes.
0x3ab160 bytes (92%) free.
```

环境安装/避坑见 `../docs/BUILD.md`；一键构建 `tools\build_firmware.ps1`；
烧写 `tools\flash_firmware.ps1 -Port COM5`；TF 卡准备 `tools\prepare_sd.ps1 -Drive E:`。

## 待办（板子到货后）

1. 填 `board_config.h` 的 SD/UART 引脚（ALIENTEK 原理图）。
2. 确认 PSRAM = 32MiB；16MB 版本改 TF 卡流式或换 26M 模型。
3. 实测 token/s 与内存余量（`docs/MEMORY.md` 清单）。
4. 采样（temperature/top-k；当前 greedy）、屏幕/语音后续。
