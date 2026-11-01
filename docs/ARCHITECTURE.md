# 系统架构

## 1. 目标拓扑

```
                    USB-A Host（5V 供电 + 数据）
┌────────────────────────┐        ┌───────────────────────────┐
│ ALINTEK ESP32-P4        │        │ 哈基米机（官方固件）        │
│                        │        │                           │
│  MiniMind q3e4 (PSRAM)  │        │  屏幕渲染 / 宠物动画        │
│          │              │        │  摇杆 / 按键 / 麦克风       │
│   km_decode_step        │        │  音频                      │
│          ▼              │        │            ▲              │
│  AI 生成任务(core 1)     │        │            │ JSONL(4M)    │
│          │              │        │            │              │
│  气泡文本                │        │            │              │
│          ▼              │        │            │              │
│  协议 host 任务(core 0) ─┼─CH343──┼────────────┘              │
│  USB Host + CDC driver  │        │                           │
│                        │        │                           │
│  TF 卡 model.kmcu      │        │                           │
└────────────────────────┘        └───────────────────────────┘
        ▲
   5V 充电器（USB-C）
```

## 2. 启动顺序

1. ROM → bootloader → app；
2. 初始化 USB-Serial-JTAG 控制台（仅调试用，最终可不接）；
3. 挂载 TF 卡（SDMMC slot1，4-bit，40MHz，失败重试）；
4. 读 `model.kmcu`（28.6 MB）到 PSRAM，`km_open` + `km_fast_build`（打包权重零拷贝）；
5. 分配 KV cache（ctx 96）与 scratch；
6. 加载 `tokenizer.bin`；
7. 启动宠物 host：USB Host 栈 → CDC/CH34x 驱动 → 打开设备 → CH343 vendor 初始化 → 等待 `hello` → 回 `ack`；
8. 进入空闲：每 2 s 心跳 + 每 2 s `session/current`；等待摇杆输入。

## 3. 任务与核分配

| 任务 | 核 | 优先级 | 栈 | 职责 |
|---|---|---|---|---|
| `pet_usb` | 0 | 4 | 6 KB | USB Host 库事件循环 + CDC 驱动安装 |
| `pet_loop` | 0 | 3 | 12 KB | 心跳、hello/ack、session/current、speech/text、RX 解析 |
| `gen` | 1 | 3 | 16 KB | 本地推理，逐 token 更新气泡 |
| CDC driver task | 0 | 5 | 4 KB | CH34x 驱动内部收发 |
| main | 0 | 1 | 8 KB | 初始化后空闲 |

> 心跳/协议在 core 0，推理在 core 1：推理期间设备仍能收到心跳，不会被判掉线。

## 4. 内存预算（32 MB PSRAM）

| 项 | 大小 |
|---|---|
| `model.kmcu` | 28,632,448 B |
| arena（f32 norms） | 58,368 B |
| KV cache（ctx 96，fp32） | 2,359,296 B |
| scratch | 52,608 B |
| tokenizer（flash/内部 RAM） | ~150 KB |
| **合计（PSRAM）** | **≈ 29.66 MiB** |
| 余量 | ≈ 2.3 MiB |

## 5. 数据流

```
摇杆中键 → 设备 input/event → P4 host 解析 → gen 任务启动
  → 本地推理（token 流）→ 每 3 token 更新 speech/text（UTF-8 边界裁剪）
  → 设备渲染气泡 → 结束后 state=waiting_user
```

## 6. 为什么不用官方 PC 客户端

官方客户端承担：LLM 调用、ASR/TTS、Agent 会话、素材生成。本项目只保留「本地文本对话」：
- UV 不需要 PC、无网络、零云成本；
- 代价：无语音/无 Agent/无联网信息。
