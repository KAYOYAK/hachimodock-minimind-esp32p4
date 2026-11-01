cmake_minimum_required(VERSION 3.16)

# 只构建 main 及其依赖（跳过 mbedtls/lwip/wifi 等无关组件；离线 AI 板不需要 TLS/网络）
set(COMPONENTS main)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(minimind_p4)
