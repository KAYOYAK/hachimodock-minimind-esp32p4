# 硬件、接线与供电

## 1. 设备清单

| 件 | 说明 |
|---|---|
| ALINTEK ESP32-P4 开发板 | 16 MB Flash / 32 MB PSRAM，双核 360 MHz（本固件配置） |
| 哈基米机 | 官方 v3 固件（0.7.103-p4-r1，芯片 rev 302），硬件按官方 BOM 复刻 |
| TF 卡 32 GB | FAT32；**正品卡很重要**（假卡/劣质卡读取极慢） |
| 5V 充电器 | 最终形态给 ALINTEK 供电（建议 ≥2 A） |
| USB-A→USB-C 数据线 | ALINTEK USB-A 口 → 哈基米机 USB-C |
| 双 USB-C 数据线 | 仅首次烧录用（ALINTEK UART/USB 口 → 电脑） |

## 2. 接线

```
首次烧录/调试：
  电脑 ─USB-C→ ALINTEK "USB" 口   (COM5, USB-Serial-JTAG, 烧写+控制台)
  电脑 ─USB-C→ ALINTEK "UART" 口  (COM4, CH343, 启动日志, 可选)

宠物链路（始终）：
  ALINTEK USB-A HOST 口 ─USB-A/C 数据线→ 哈基米机 USB-C

最终形态（完全脱离电脑）：
  5V 充电器 ─USB-C→ ALINTEK "USB" 口（或任意供电口）
  ALINTEK USB-A → 哈基米机
```

注意事项：
- 哈基米机**同一时间只能接一个主机**：接电脑（官方客户端）或接 ALINTEK USB-A，不能同时；
- 两个 USB-C 口同时插同一台电脑是安全的（同源 5V），但最终形态不要依赖电脑；
- 哈基米机裸板峰值电流约 0.5–1 A，请保证 USB-A 口供电能力。

## 3. 板级引脚（ALINTEK）

### SD（SDMMC slot 1，4-bit）
| 信号 | GPIO |
|---|---|
| CLK | 43 |
| CMD | 44 |
| D0 | 39 |
| D1 | 40 |
| D2 | 41 |
| D3 | 42 |

### 串口
- UART0 TX/RX → CH343（仅日志，RX 不通）；
- 原生 USB-Serial/JTAG → Type-C "USB" 口（COM5）。

### 宠物 USB 主机
- USB-A HOST 口（板载，可能经 hub，固件已开 `CONFIG_USB_HOST_HUBS_SUPPORTED`）；
- 设备：哈基米机 CH343（VID `0x1A86` / PID `0x55D3`），运行在 4 Mbaud。

## 4. 实测踩坑

1. **TF 卡接触**：卡取出再插回后，读取速度从 20 MB/s 掉到 0.2 MB/s、偶发 `sdmmc_init_ocr` 超时/`setting clk div failed 0x107`。清洁金手指、插到底可恢复；固件已加 3 次挂载重试。
2. **CH343 主机驱动**：乐鑫 CH34x host 驱动对 CH343 初始化不完整 → TX 超时；需补 `0xA1/0xA4` vendor 请求（见 `docs/PROTOCOL.md`）。
3. **DTR/RTS**：DTR→P4 GPIO35（boot strap），RTS→EN；正常通信保持释放，否则会把设备复位/带入下载模式。
4. **裸板无屏**：官方固件会周期报 `task_wdt`（无 DSI 屏初始化），协议/握手仍可用；截图能力可在无屏时验证画面。
5. **供电**：ALINTEK 由 5V 充电器供电即可；宠物从 ALINTEK USB-A 取电，注意总电流。
