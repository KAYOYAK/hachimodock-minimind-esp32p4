/* 把 ../../firmware/main/kmcu.c 编进 ESP-IDF 组件，避免复制两份内核源码。
 * 单文件 include 形式对 IDF 构建系统透明。 */
#include "../../firmware/main/kmcu.c"
