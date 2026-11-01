# 协议实现笔记（HachimoDock pet-usb-jsonl-v3）

> 这些结论来自对官方 `firmware/protocol.md`、官方 PC 客户端源码的分析，以及对真机（官方 v3 固件 0.7.103-p4-r1）的实测。实测环境：ESP32-P4 作为 USB Host，CH343 4 Mbaud。

## 1. 物理链路

- 设备侧：ESP32-P4 → CH343 USB-UART → Type-C。
- 运行时波特率：**4,000,000**（启动日志仍是 115200）。
- 每行一个 JSON：`{"topic":"...","payload":{...}}\n`（UTF-8）。

## 2. 握手

设备主动发：

```json
{"topic":"hello","payload":{
  "boardDeviceId":"p4-e8f60ae8aa68",
  "fw":"0.7.103-p4-r1",
  "protocolSchema":7,
  "wireProtocol":"pet-usb-jsonl-v3",
  "capabilities":{ "...": "usbUartBaud=4000000 等" }
}}
```

Host 回：

```json
{"topic":"ack","payload":{"desktopDeviceId":"alintek-p4-local"}}
```

- 不发 `ack`，设备每 3 s 重发 `hello`，握手不完成。
- `protocolSchema` 以设备为准（当前为 7；文档部分示例仍写 6，按 `>=6` 兼容处理）。

## 3. 心跳与会话

- 每 **2 s** 发：`{"topic":"system/heartbeat","payload":{"requestId":"hb-N","ts":<ms>}}`
- 设备 **6 s** 收不到任何有效 host 消息即判定断连。
- `session/current` 每 **2 s** 刷新；**12 s** 不刷新设备会移除会话卡片：
  - `agentId/index/count/activeSessionIds/sessions[]`，`state` ∈ `working / thinking / waiting_user / done / error`
  - 终结态保留 60 s（`terminalRemainingMs`）。

## 4. 气泡

Agent 气泡用 `speech/text`（**不是** `ui/conversation`）：

```json
{"topic":"speech/text","payload":{
  "sessionId":"p4-local-1",
  "displayTitle":"ALINTEK 本地 AI",
  "displayContent":"你好，我是……",
  "status":"working",
  "statusText":"thinking",
  "tsMs":0
}}
```

- `ui/conversation` 是**实时语音 HUD**，会占用主屏气泡并隐藏 Agent 卡片，不要混用。
- `displayContent` 必须是合法 UTF-8/JSON：**流式更新时不要把中文截断在半个 UTF-8 字符上**（否则设备回 `invalid_json` NACK）。

## 5. 输入事件

设备上报：

```json
{"topic":"input/event","payload":{
  "version":9,"seq":1,"control":"encoder.press","gesture":"short_press",
  "event":"button.encoder.short_press","context":"main","action":"page_enter",
  "handledLocally":false
}}
```

实测动作映射（裸板，官方固件）：

| 输入 | event | action |
|---|---|---|
| 摇杆中键短按 | `button.encoder.short_press` | `page_enter` |
| 摇杆上 | `joystick.up` | `session_previous` |
| 摇杆下 | `joystick.down` | `session_next` |
| 旋钮左/右 | `knob.rotate_ccw/cw` | session 切换 |

本项目用中键短按触发本地 AI 生成。

## 6. 截图（无屏调试）

请求：`{"topic":"debug/screenshot","payload":{"fullResolution":true}}`

返回：
- `debug/screenshot_begin`（id/width/height/format=rgb565le）
- `debug/screenshot_chunk`（id/index/data=base64）
- `debug/screenshot_end`（id/chunks/nonBlack/checksum=fnv1a）

冒烟验证：`begin -> 200 chunks (640x480) -> end`，且 `nonBlack>0`。

## 7. CH343 主机侧关键（踩坑核心）

1. **乐鑫 `usb_host_ch34x_vcp` 只覆盖 CH340/CH341 的寄存器写，对 CH343 无效** → 表现为 `TX transfer timeout`。必须按 WCH `ch343.c` 语义补 vendor 请求：
   - `0xA1`：`wValue=(LCR<<8)|0x8C`，LCR=`0xC3`（EN_RX|EN_TX|8N1），`wIndex=(factor<<8)|divisor`；
   - 4 Mbaud 的 factor/divisor：**factor=0xFD，divisor=7**（CH343G 高波特率走 12 MHz 基准）；
   - `0xA4`：`wValue=~modem`，`0xFFFF` = DTR/RTS 均释放。
2. **DTR/RTS 电气含义**：DTR → P4 GPIO35（boot strap），RTS → EN。正常通信必须保持释放；拉 RTS 会复位设备，拉 DTR 会让下次复位进下载模式。
3. 打开顺序：打开串口 → 设置 CH343 线路/波特率 → 拉 RTS 脉冲复位一次 → 释放 → 发心跳 → 等 hello。
4. 设备端**不做** USB 连接检测，它只看 UART 数据；host 侧心跳是唯一保活手段。
