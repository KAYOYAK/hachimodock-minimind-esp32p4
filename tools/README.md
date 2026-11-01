# 工具脚本

| 脚本 | 用途 |
|---|---|
| `build_firmware.ps1` | 构建 P4 应用固件（ESP-IDF 6.1） |
| `build_pethost.ps1` | 构建纯 USB Host 协议测试固件 |
| `flash_p4.py` | 一键烧录（UART 口控 DTR/RTS + USB-JTAG 写入） |
| `p4_chat.py` | PC 端通过 USB-JTAG 控制台与板子对话 |
| `p4_upload.py` | 通过 USB 口上传 model.kmcu / tokenizer.bin 到 TF 卡 |
| `hachi_probe.py` | PC 端最小官方协议 host（hello/heartbeat/气泡/按键） |
| `prepare_sd.ps1` | 用读卡器把模型写入 TF 卡 |
| `fetch_idf_submodules.ps1` | 补 ESP-IDF 缺失子模块（GitHub 不可直连时用 gh-proxy） |
| `pth2hf.py` | MiniMind .pth → HF Qwen3 格式 |
| `convert_minimind.py` | HF → KMCU 混合位宽量化 |
| `compare_native_hf.py` | 原生 MiniMind vs HF logits 对拍 |
| `export_tokenizer.py` | 导出 tokenizer.bin |
| `tokenizer_check.py` / `tokenizer_host_test.c` | 分词器 79/79 对拍 |
| `host_eval.c` | PC 端推理对拍 harness（含 pie_gemv_row stub） |
| `ref_minimind.py` | NumPy 参考实现 |
| `inspect_gguf.py` / `run_llamacpp_convert.py` | GGUF 检查与 llama.cpp 转换（可选） |
| `flash_firmware.ps1` | 早期烧录脚本（保留） |

> 使用前先看根目录 README 与 docs/BUILD.md；默认路径为 `C:\p4test`，换机器需改脚本里的路径。
