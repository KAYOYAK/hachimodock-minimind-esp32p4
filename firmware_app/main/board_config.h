#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

/* ALIENTEK ATK-DNESP32P4 开发板（ESP32-P4 核心板）。
 * SD 引脚来自《DNESP32P4开发指南》第38章“SD卡实验”：
 *   SD1_CMD=IO44  SD1_CLK=IO43  SD1_D0=IO39  SD1_D1=IO40  SD1_D2=IO41  SD1_D3=IO42
 * 使用 SDMMC_HOST_SLOT_1、4 线模式、内部上拉、40MHz。 */
#define BOARD_SD_CLK_IO     43
#define BOARD_SD_CMD_IO     44
#define BOARD_SD_D0_IO      39
#define BOARD_SD_D1_IO      40
#define BOARD_SD_D2_IO      41
#define BOARD_SD_D3_IO      42
#define BOARD_SD_POWER_IO   -1   /* 板上无 TF 卡供电控制脚 */

/* 模型文件在 TF 卡上的路径（FATFS 挂载点 /sdcard） */
#define BOARD_MODEL_PATH    "/sdcard/model.kmcu"

/* 推理上下文长度（KV cache token 数）；PSRAM 预算见 docs/MEMORY.md */
#define BOARD_CTX_TOKENS    96

#endif /* BOARD_CONFIG_H */
