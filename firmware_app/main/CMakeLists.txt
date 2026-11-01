idf_component_register(
    SRCS "app_main.c" "tokenizer.c" "kmcu_wrapper.c" "pie_scalar.c" "pet_host.c"
    INCLUDE_DIRS "." "../../firmware/main"
    REQUIRES freertos esp_timer esp_psram sdmmc esp_driver_sdmmc vfs fatfs
             esp_driver_uart esp_driver_gpio esp_driver_usb_serial_jtag
             esp_system log heap
)
