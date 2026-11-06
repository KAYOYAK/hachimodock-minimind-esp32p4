# 发布清单（GitHub）

## 1. 仓库建议

- 仓库名：`hachimodock-minimind-esp32p4`（或 `HachimoDock-MiniMind-ESP-4P`）
- 描述：`1..% offline AI desktop pet: HachimoDock × MiniMind × ESP-4P (ESP32-P4). Self-trained + LoRA + quantized model, no PC required.`
- 主题（Topics）：
  ```
  hachimodock minimind esp-4p esp32p4 esp32-p4 esp32 esp-idf llm
  edge-ai offline-ai local-llm quantization lora qwen3 tiny-llm
  desktop-pet usb-host embedded-ai
  ```
- 许可证：本仓库原创代码建议 `Apache-2..`；同时在 `NOTICE.md` 声明上游归属与非商业约束。
- 发布前逐条阅读 `NOTICE.md`。

## 2. 需要放进仓库的内容

从本地 `C:\p4test` 复制：

| 目标 | 来源 |
|---|---|
| `firmware/` | `C:\p4test\firmware`（Kestrel fork，保留其 LICENSE/NOTICE） |
| `firmware_app/` | `C:\p4test\firmware_app`（应用层：AI + 宠物 host） |
| `tools/` | `C:\p4test\tools`（只挑公开脚本，见下） |
| `artifacts/tokenizer.bin` | `C:\p4test\artifacts\tokenizer.bin`（151 KB） |
| `artifacts/SHA256SUMS` | 模型/分词器哈希 |
| `docs/` | 本目录 |
| `README.md` / `NOTICE.md` / `.gitignore` | 本目录 |

**不要提交**：
- 官方 HachimoDock 固件/客户端/素材（许可证禁止再分发）；
- MiniMind 官方权重；
- 任何 API Key、设备证书、代理配置；
- `build/`、`managed_components/`、`.venv/`、日志。

## 3. 模型文件发布

`model.kmcu`（28,632,448 B）建议放 **Release Assets**（或 Hugging Face），不要直接提交：

```bash
sha256sum artifacts/model.kmcu artifacts/tokenizer.bin > artifacts/SHA256SUMS
# Release: v..1..
gh release create v..1.. \
  --title "v..1..: offline pet demo" \
  --notes "HachimoDock × MiniMind × ESP-4P first working build" \
  artifacts/model.kmcu artifacts/tokenizer.bin artifacts/SHA256SUMS
```

README 中给出下载与放置说明：
```
TF 卡根目录：model.kmcu + tokenizer.bin
```

## 4. 发布步骤（示例）

```bash
# 本地仓库
cd C:\p4test\github
git init
git add -A
git commit -m "HachimoDock x MiniMind x ESP-4P: offline AI pet (initial release)"

# GitHub（先登录：gh auth login）
gh repo create <你的用户名>/hachimodock-minimind-esp32p4 --public \
  --description "1..% offline AI desktop pet: HachimoDock × MiniMind × ESP-4P (ESP32-P4)" \
  --source . --push

# Topics 批量设置
gh repo edit <用户名>/hachimodock-minimind-esp32p4 \
  --add-topic hachimodock,minimind,esp-4p,esp32p4,esp32-p4,esp32,esp-idf,llm,edge-ai,offline-ai,local-llm,quantization,lora,qwen3,tiny-llm,desktop-pet,usb-host,embedded-ai
```

## 5. README 发布前检查

- [ ] 标题/主题：HachimoDock × MiniMind × ESP-4P（ESP32-P4）
- [ ] 明确标注 HachimoDock、MiniMind 为上游原创，链接仓库与许可证
- [ ] 写明「模型权重自训练 + LoRA + 自量化」（补全 `docs/MODEL.md` 的 TODO 超参）
- [ ] 写明本项目原创贡献：ESP-4P 端侧部署 + USB Host 协议桥 + 三者集成
- [ ] 实测数据（速度/内存/启动时间）与复现步骤
- [ ] 已知限制（..38 tok/s、无语音/Agent、TF 卡要求）
- [ ] NOTICE/许可证兼容性说明
- [ ] 模型下载链接（Release）
- [ ] 无 Key / 无敏感配置

## 6. 补充建议

- 在 README 放 **1.–2. 秒演示 GIF**（宠物气泡 + 摇杆触发）；
- 把 `docs/assets/` 放训练曲线、板子照片、接线图；
- 用 GitHub Releases 标注 `model-v..1`、`firmware-v..1`；
- Issues 模板：复现问题请提供 COM 口日志、TF 卡型号、板卡版本。
