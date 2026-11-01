# HachimoDock × MiniMind × ESP-4P（ESP32-P4）— 全离线桌面 AI 宠物

> **主题：hachimodock + minimind + ESP-4P（ESP32-P4）**
> 把「哈基米机」的桌面宠物、开源的 MiniMind 小模型，以及 ESP32-P4 的端侧推理能力，合成一个**完全不需要电脑**的本地 AI 宠物。
> 模型权重训练、LoRA 微调、混合位宽量化与 P4 端部署均为本人完成；HachimoDock 与 MiniMind 为上游原创项目，本仓库只做集成、量化与端侧实现。

[![ESP32-P4](https://img.shields.io/badge/MCU-ESP32--P4-000000?logo=espressif)](https://www.espressif.com/)
[![MiniMind](https://img.shields.io/badge/LLM-MiniMind-3b82f6)](https://github.com/jingyaogong/minimind)
[![HachimoDock](https://img.shields.io/badge/Device-HachimoDock-f59e0b)](https://github.com/YizhengWw/HachimoDock)
[![Offline](https://img.shields.io/badge/Network-100%25%20Offline-22c55e)](#)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue)](#-许可证与原创归属)

---

## ✨ 这个项目做了什么

官方 HachimoDock 是一台**电脑配件**：设备只负责渲染与输入，真正的对话模型、语音、Agent 都在 PC 上。
本项目的目标是把它变成**独立设备**：

```
传统链路：  [PC 客户端 + 云端/本地 LLM] ──USB──▶ [哈基米机]
本项目：    [ESP32-P4 单板：本地训练+量化的 MiniMind] ──USB Host──▶ [哈基米机]
```

具体工作：

1. **模型全流程自研**：在本机 RTX 5070 Ti Laptop 上**从零训练** MiniMind-3 Zero（pre-train 1 epoch + SFT 1 epoch，共 **6h32m**，最终 loss 2.01 / 1.71），并用官方数据复刻医药 **LoRA**（rank=16，7,900 step，loss 1.2564）；再做**自定义混合位宽量化**（q3e4：embed q4，attention/FFN q3），把 63.91M 参数压到 **28.6 MB**，在 ESP32-P4 的 32 MB PSRAM 中全驻运行。
2. **端侧推理引擎**：基于 Kestrel-MCU（Apache-2.0）移植到 ESP32-P4，补齐 Qwen3 的 **q_norm / k_norm**，实现 KMCU 打包权重的零拷贝 GEMV，并做了 int16 量化的 GEMV 加速（约 2.1×）。
3. **替代官方 PC 客户端**：在 ESP32-P4 上实现 USB Host + CH343 驱动 + HachimoDock 官方 JSONL 协议（`hello / ack / heartbeat / session/current / speech/text / input/event / debug/screenshot`），让 P4 单板直接驱动哈基米机。
4. **协议细节逆向验证**：确认 CH343 的 4 Mbaud 运行时链路、DTR/RTS 与 P4 EN/GPIO35 的对应关系，以及乐鑫 CH34x host 驱动缺失的 CH343 vendor 初始化（`0xA1` LCR+波特率、`0xA4` 释放 DTR/RTS）。
5. **完整闭环**：宠物摇杆输入 → `input/event` → P4 本地生成中文回复 → `speech/text` 气泡 → 宠物屏幕显示，全程离线、无 PC、无网络。

> 一句话：**哈基米机（原创硬件/固件）+ MiniMind（原创模型架构）+ ESP32-P4 端侧推理（本项目原创实现）= 一台真正离线的 AI 桌宠。**

> **复刻状态**：按官方 BOM 完美复刻哈基米机（官方 V1.2 PCB + 官方固件；整机装配收尾中），软件与协议已与官方设备实测打通。

---

## 🧩 三方关系与原创归属

| 组成 | 来源 | 原创归属 | 本项目角色 |
|---|---|---|---|
| 哈基米机 HachimoDock 硬件 / 固件 / 协议 | [YizhengWw/HachimoDock](https://github.com/YizhengWw/HachimoDock) | 小米技术委创新产品团队 | 作为设备端，保持官方固件不改 |
| MiniMind 模型架构与开源代码 | [jingyaogong/minimind](https://github.com/jingyaogong/minimind) | MiniMind 原作者 | 在其架构上完成训练 / LoRA / 量化 |
| ESP32-P4 推理内核底座 | [m13253246268-ship-it/kestrel-llm-mcu](https://github.com/m13253246268-ship-it/kestrel-llm-mcu) | Kestrel-MCU（Apache-2.0） | 移植、修复 QK-norm、优化 GEMV |
| 桌面端替代（USB Host + 协议 host） | 本仓库 | **本项目原创** | 删除 PC 依赖的关键实现 |
| 训练/LoRA/量化/部署工程 | 本仓库 | **本项目原创** | 全流程可复现 |

**打标签建议**（GitHub Topics）：

```
hachimodock  minimind  esp-4p  esp32p4  esp32-p4  esp32  esp-idf  llm  edge-ai  offline-ai
local-llm  quantization  qwen3  tiny-llm  desktop-pet  usb-host  embedded-ai
```

---

## 🏷 原创 / 复刻 / 衍生 一览（必读）

为免混淆，明确区分三类内容：

### 原创（上游作者，本项目**不主张**版权）
- **HachimoDock / 哈基米机**：小米技术委创新产品团队 —— 硬件设计、官方固件、PC 客户端、USB 协议。
- **MiniMind**：MiniMind 原作者（jingyaogong/minimind）—— 模型架构、训练代码与数据集。
- **Kestrel-MCU**：端侧推理内核底座（Apache-2.0）。
- **ESP-IDF / ESP-SR / WCH CH343 驱动**：Espressif / WCH 等。

### 复刻（本人按上游公开资料完成）
- **哈基米机整机**：按官方 BOM 复刻（官方 V1.2 定制 PCB、官方固件 0.7.103-p4-r1、官方外壳/屏幕/轴体），非官方量产机。
- **MiniMind 训练链路**：按官方 mini 配方与公开数据，从零跑通 pretrain + SFT（本地 6h32m），得到本人训练的权重。
- **医药 LoRA**：用官方数据与官方超参重新训练（rank=16，7,900 step），属**效果级复刻**，与官方 LoRA 权重余弦相似度≈0，不是权重级复制。

### 原创（本人，Apache-2.0）
- **自训练权重**：`full_sft_768.pth` 及量化后的 `model.kmcu`（q3e4，28.6 MB）。
- **自定义混合位宽量化**：KMCU q4/q3/q2 布局、量化工具链、与上游框架的格式映射。
- **ESP32-P4 端侧部署**：QK-norm 修复、打包权重零拷贝 GEMV、int16 激活量化整数点积（2.1×）、内存/任务规划。
- **USB Host 协议桥**：在 ESP32-P4 + CH343 上实现官方 JSONL 协议 host，**替代官方 PC 客户端**；含 CH343 4 Mbaud vendor 初始化（`0xA1/0xA4`）的逆向结论。
- **三者集成方案**：离线、无 PC、无网络的 AI 桌宠完整闭环。

> 本项目**不包含**官方 HachimoDock 固件/客户端/素材，也不包含 MiniMind 官方权重；如需上游能力请移步各自仓库并遵守其许可证（HachimoDock 为个人非商业许可）。

---

## 🏗 系统架构

```
                 USB 2.0 (USB-A Host 口)
┌───────────────────────────┐        ┌──────────────────────────────┐
│ ALINTEK ESP32-P4 开发板    │        │ 哈基米机（官方固件，未修改）    │
│                           │        │                              │
│  ┌─────────────────────┐  │        │  ┌────────────────────────┐  │
│  │ MiniMind-3 (q3e4)   │  │        │  │ 渲染 / 动画 / 屏幕      │  │
│  │ 63.91M params       │  │        │  │ 摇杆 / 按键 / 麦克风     │  │
│  │ 28.6 MB in PSRAM    │  │        │  └────────────────────────┘  │
│  └─────────┬───────────┘  │        │              ▲               │
│            │ 本地推理       │        │              │ JSONL 协议     │
│  ┌─────────▼───────────┐  │ CH343  │              │               │
│  │ USB Host + 协议 host │◀─┼─4Mbaud─┼──────────────┘               │
│  │ hello/ack/heartbeat │  │        │                              │
│  │ session/speech/input│  │        │                              │
│  └─────────────────────┘  │        └──────────────────────────────┘
│  TF 卡：model.kmcu + tokenizer.bin │
└───────────────────────────┘
         供电：5V 充电器（USB-C）
```

---

## ⚡ 关键指标（实测）

| 项目 | 数值 |
|---|---|
| 主控 | ESP32-P4（rev v1.3），双核 360 MHz，16 MB Flash，**32 MB PSRAM** |
| 模型 | MiniMind-3 架构，63.91M 参数，自训练 + LoRA + **q3e4 混合量化** |
| 模型体积 | **28,632,448 B（27.3 MiB）**，全驻 PSRAM |
| 推理速度 | **2.64 s/token ≈ 0.38 tok/s**（q3e4，标量整数点积） |
| 模型加载 | **20.6 s**（TF 卡 4-bit 40 MHz；受卡/卡槽影响） |
| 设备协议 | 官方 `pet-usb-jsonl-v3`，CH343 4 Mbaud |
| 功耗 | 裸板 ~0.2–0.5 A（5V），整机峰值 ~0.8–1 A |
| 网络 | 无（完全离线） |

> 速度以「一句话几十秒」为代价换取完全离线与零云成本；后续可用 PIE 定点 SIMD 再提速。

> **已验证（2026-11-01，官方 v3 固件裸板）**：开机自动握手成功 → 摇杆/自动触发 → 本地生成中文 → `speech/text` 气泡下发。日志摘要：
> `hello from pet p4-e8f60ae8aa68` → `ack sent, handshake complete` → `[ai] 你好！我是一个AI助手，我是一个虚拟`。

---

---

## 📊 训练证据（可复核）

训练日志、逐 step loss、权重哈希已整理到 **[docs/TRAINING-EVIDENCE.md](docs/TRAINING-EVIDENCE.md)**，核心数据：

| 阶段 | 数据 | step | 耗时 | final loss |
|---|---|---|---|---|
| Pretrain | 1,270,238 条 / 1.18 GB | 39,695 | 2h26m | **2.01** |
| SFT | 905,718 条 / 1.66 GB | 56,608 | 4h06m | **1.71** |
| 医药 LoRA 复刻 | 25,276 条 / 10 epochs | 7,900 | 24min | **1.2564** |

![pretrain loss](docs/assets/pretrain_loss.svg)
![sft loss](docs/assets/sft_loss.svg)
![lora loss](docs/assets/lora_loss.svg)

> 环境：本地 RTX 5070 Ti Laptop 12GB，Python 3.12.10 + torch 2.14.1+cu130；无云服务器。
> 权重 SHA256、日志首尾摘录、模型样例见 [docs/TRAINING-EVIDENCE.md](docs/TRAINING-EVIDENCE.md)。

## 🚀 快速开始

### 硬件

- ALINTEK ESP32-P4 开发板（16 MB Flash / 32 MB PSRAM）
- 一台官方固件的哈基米机（或等价的 HachimoDock 设备）
- 32 GB TF 卡（实测注意：劣质/假卡会导致读取只有 0.2 MB/s 甚至挂载失败）
- 5V 充电器（最终形态，可选电脑首次烧录）

### 接线

```
电脑(仅首次烧录) ──USB-C──▶ ALINTEK "USB" 口（COM5，USB-Serial-JTAG 控制台）
ALINTEK "UART" 口（COM4，可选，看启动日志）
ALINTEK USB-A HOST 口 ──USB-A/C 数据线──▶ 哈基米机 USB-C
```

### 构建与烧录

```bash
# 1) 构建（ESP-IDF 6.1，P4 rev<3 配置）
powershell -File tools/build_firmware.ps1

# 2) 烧写（通过 USB-Serial-JTAG，自动进下载模式）
python tools/flash_p4.py --build build --uart COM4
```

> 详细环境（IDF 6.1 rev<3 配置、缺失子模块、CH343 host 组件）见 `docs/BUILD.md`。

### 模型与 TF 卡

```
TF 卡根目录：
  model.kmcu      # 自训练模型的 q3e4 量化结果（28.6 MB）
  tokenizer.bin   # 6400 词表 ByteLevel BPE 分词器
```

把卡插入板子，上电后约 20 秒模型加载完成、与哈基米机自动握手，按摇杆中键即可触发本地 AI 回复。

---

## 🔬 模型：训练 → LoRA → 量化

> 完整数据与日志见 `docs/MODEL.md`（来源：`D:\minimind`，2026-10-28 ~ 11-01 实测）。摘要如下：

1. **从零预训练**：`pretrain_t2t_mini.jsonl` 1,270,238 条，bs32×accum8、seq340、lr5e-4、bf16，**39,695 step / 2h26m / loss 2.01**。
2. **SFT + LoRA**：SFT 905,718 条（56,608 step / 4h06m / loss 1.71）；医药 LoRA 用官方数据复刻（rank=16、393,216 参数、7,900 step、24 min、loss 1.2564），医疗留出 loss 1.3109（基座 1.5553）。
3. **量化**：自定义 KMCU 混合位宽——
   - `q4_0`：18 B / 32 权重（fp16 scale + 16 B nibbles）
   - `q3_0`：14 B / 32 权重（fp16 scale + 12 B 3-bit）
   - 部署档位 `q3e4`：embedding 用 q4，attention 与 FFN 用 q3 → **28,632,448 B**
4. **数值对齐**：PC 端 NumPy 参考与端侧 kernel 对拍，greedy 序列逐 token 一致。
5. **端侧优化**：打包权重零拷贝 GEMV、int16 激活量化整数点积（QK-norm 已在 kernel 内实现）。

模型文件与 tokenizer 建议放在 **GitHub Release Assets**（weights 28.6 MB），仓库只保留转换脚本与校验哈希。

---

## 📡 协议实现要点（本项目原创部分）

官方协议是 JSON Lines，但「怎么在 P4 上跑通」有大量坑，已记录在 `docs/PROTOCOL.md`：

- CH343 USB-UART 运行时 **4,000,000 baud**（115200 只用于启动日志）；
- 设备主动发 `hello`，host 回 `ack` 完成握手；
- 每 2 s 发 `system/heartbeat`，6 s 无消息设备判定断连；
- `session/current` 每 2 s 刷新（12 s 不刷新会移除卡片）；
- `speech/text` 显示气泡，`ui/conversation` 是实时语音 HUD（不要混用）；
- `debug/screenshot` 可在无屏时验证画面；
- **CH343 专有初始化**：乐鑫 CH34x host 驱动只覆盖 CH340/CH341，CH343 需要 `0xA1`（LCR + 波特率因子）与 `0xA4`（`~modem` 控制）才能收发，这是 TX 一直超时的根因。

---

## 📁 仓库结构

```
.
├── README.md
├── NOTICE.md                    # 原创归属与许可证
├── docs/
│   ├── ARCHITECTURE.md          # 系统/任务/内存架构
│   ├── PROTOCOL.md              # 官方 JSONL 协议 + CH343 逆向笔记
│   ├── MODEL.md                 # 训练/LoRA/量化流程
│   ├── BUILD.md                 # ESP-IDF 环境与构建
│   └── HARDWARE.md              # 接线、供电、卡槽注意事项
├── firmware/                    # Kestrel-MCU fork（qk-norm + 优化 kernel）
├── firmware_app/                # P4 应用：AI 推理 + 宠物 USB Host
├── tools/                       # 转换/量化/烧录/对话/协议探测脚本
└── artifacts/                   # tokenizer.bin、校验和（模型走 Release）
```

---

## ⚠️ 已知限制

- 速度 **0.38 tok/s**，单句回复需要数十秒；适合「低频互动」而非实时对话。
- q3e4 量化后质量有限，短 prompt 可能不连贯；完整指令效果更好。
- 无语音 ASR/TTS、无 Agent 状态跟随——这些依赖 PC/云端，本方案主动放弃。
- TF 卡质量和卡槽接触直接影响启动耗时，建议正品卡。
- 部分 ESP32-P4 rev v1.3 板的 SD 高速时钟切换不稳定，固件已加降频/重试（见 docs/HARDWARE.md）。
- 设备侧偶发 `invalid_json` / `invalid_message` NACK（2–6 次/轮，集中在 `session/current` 连发时；最终 `speech/text` 气泡正常）。已尝试：UTF-8 边界裁剪、发送间隔化、关闭中间态更新，均未根除，判断与设备端解析时序有关；不影响本地生成与最终显示。

---

## 🙏 致谢与许可证

- **HachimoDock / 哈基米机**：小米技术委创新产品团队开源项目，遵循 *HachimoDock Project License v1.0*（**仅限个人非商业**）。本仓库不分发其固件/素材，设备端保持官方固件。
- **MiniMind**：MiniMind 原作者（[jingyaogong/minimind](https://github.com/jingyaogong/minimind)），遵循上游 LICENSE；本仓库不重新分发其官方权重，仅发布自训练/微调与量化产物。
- **Kestrel-MCU**：Apache-2.0，端侧推理内核底座。
- **ESP-IDF / ESP-SR / CH343 驱动**：Espressif / WCH，遵循各自许可证。

**本仓库原创代码**（USB Host 协议桥、量化/部署工程、集成方案）采用 **Apache-2.0** 发布；模型权重由作者自行训练/微调/量化，按「仅供学习研究，禁止商业转售」发布。
使用前请阅读 `NOTICE.md`；如上游许可证与本仓库声明冲突，以上游为准。

---

## 📌 如果这个项目对你有帮助

- Star ⭐ 本项目；
- 在 Issues 里告诉我你复刻成功或失败的地方；
- 欢迎 PR 补充：PIE 加速、LoRA 数据集、更多宠物动作映射。

---

---

## 📥 模型下载（Release v0.1.0）

| 文件 | 大小 | 链接 |
|---|---|---|
| `model.kmcu`（q3e4 自训练权重） | 28,632,448 B | [GitHub Release](https://github.com/KAYOYAK/hachimodock-minimind-esp32p4/releases/download/v0.1.0/model.kmcu) |
| `tokenizer.bin`（6400 词表） | 151,223 B | [GitHub Release](https://github.com/KAYOYAK/hachimodock-minimind-esp32p4/releases/download/v0.1.0/tokenizer.bin) |
| `SHA256SUMS` | — | 见 `artifacts/SHA256SUMS` |

下载后放入 TF 卡根目录即可；校验：
`fd162ab9...  model.kmcu` / `80db508d...  tokenizer.bin`