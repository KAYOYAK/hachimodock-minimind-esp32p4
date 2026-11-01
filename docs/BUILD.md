# 构建环境与烧录

## 1. 实测环境

| 项 | 值 |
|---|---|
| ESP-IDF | v6.1-rc1（Gitee 镜像 `EspressifSystems/esp-idf`） |
| 工具链 | `riscv32-esp-elf` GCC 15.2.0，`IDF_TOOLS_PATH=C:\et` |
| 目标 | `esp32p4`，16 MB Flash，32 MB hex PSRAM |
| 依赖组件（component manager） | `espressif/usb`、`usb_host_cdc_acm`、`usb_host_ch34x_vcp` |
| 应用分区 | 自定义 4 MB app（`partitions.csv`） |

## 2. 关键 sdkconfig（必须）

```
# ESP32-P4 rev v1.3（rev < 3.0）走独立代码路径
CONFIG_ESP32P4_SELECTS_REV_LESS_V3=y
CONFIG_ESP32P4_REV_MIN_100=y

# 主任务栈（默认 3584 会栈溢出）
CONFIG_ESP_MAIN_TASK_STACK_SIZE=8192

# USB Host（板载 USB-A 可能经 hub）
CONFIG_USB_HOST_HUBS_SUPPORTED=y

# PSRAM
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_HEX=y
CONFIG_SPIRAM_SPEED_200M=y

# 计算密集、离线设备
CONFIG_ESP_TASK_WDT_EN=n
CONFIG_ESP_INT_WDT=n
CONFIG_COMPILER_OPTIMIZATION_PERF=y
```

## 3. 本地 IDF 缺失子模块

Gitee 浅克隆不带 submodule。除 mbedtls/tlsf/micro-ecc 外，**构建 `set(COMPONENTS main)` 仍可能需要 lwip**（因 USB host 组件依赖链）。本机处理方式：

1. 从 `espressif/esp-lwip` 下载对应 commit 归档（`gh-proxy.com` 代理可用）；
2. 解压到 `components/lwip/lwip/`；
3. 重新构建。

> 若不想补子模块，也可以在项目 CMakeLists 中 `set(COMPONENTS main)` 限制组件集合（本项目已采用）。

## 4. 构建

```powershell
# MiniMind + 宠物 host 合一固件
powershell -ExecutionPolicy Bypass -File tools/build_firmware.ps1
```

产物：`build/minimind_p4.bin`，烧录参数在 `build/flash_args`。

## 5. 烧录

本板（ALINTEK ESP32-P4）的两种 USB-C：

- `UART` 口：CH343（COM4），**只有日志**，P4 UART0 RX 未接到 CH343，不能烧写；
- `USB` 口：P4 原生 USB-Serial/JTAG（COM5），**烧写 + 控制台**。

一键烧录脚本（UART 口控 DTR/RTS 进下载模式，USB 口用 esptool 写入）：

```powershell
python tools/flash_p4.py --build build --uart COM4
```

若仅插 USB 口：`esptool --chip esp32p4 -p COM5 -b 460800 --before default-reset write-flash @flash_args` 也可（P4 支持 USB-JTAG 复位），必要时手动按住 BOOT 点 RST。

## 6. TF 卡

```powershell
# 读卡器方式（推荐正品卡）
Copy-Item artifacts\model.kmcu E:\model.kmcu
Copy-Item artifacts\tokenizer.bin E:\tokenizer.bin
```

- 文件系统 FAT32；
- 卡质量差会导致读取只有 0.2–1.4 MB/s，甚至挂载失败；实测同一张卡在 USB 读卡器有 **19.9 MB/s**，在板子上明显更慢，请优先排查卡/卡槽接触。
- 固件里 SD 失败重试 3 次、40 MHz；若某板卡槽不稳定可降到 20 MHz（见 `docs/HARDWARE.md`）。

## 7. 首次上电验证

```
==== MiniMind-3 on ESP32-P4 (offline) ====
PSRAM: 33554432 bytes
SD mounted, 29710 MB
model read done: 28632448/28632448, ~20566 ms
tokenizer loaded
[pet] USB host installed
[pet] USB device VID=0x1A86 PID=0x55D3
[pet] CH343 init: ok=0 fct=253 dvs=7 -> ESP_OK
[pet] hello from pet p4-...
[pet] ack sent, handshake complete
```

按摇杆中键后：

```
[pet] input: button.encoder.short_press / page_enter
[ai] 你好！我是一个AI助手……
```
