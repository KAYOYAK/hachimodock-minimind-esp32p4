# IEEE ESL 投稿检查清单

> 目标：IEEE Embedded Systems Letters（SCI 四区）。投稿前逐项打勾。

## A. 稿件文件
- [ ] `ESL-LETTER-DRAFT.tex` 填完所有 `<...>` 占位（作者、单位、设备 CE、规则评分、带宽、q2/mixed 数据）
- [ ] 按 IEEEtran `journal,letterpaper` 编译（Overleaf 模板：IEEEtran 官方）
- [ ] **4 页以内**（含图、表、参考文献；超页可能直接退修/收费）
- [ ] 图：无（本稿 0 图）；表：3 张，均在栏内不断裂
- [ ] 参考文献 15–18 条，格式统一（IEEE 风格）
- [ ] 补充材料（如放）：训练日志、评估脚本、额外 CE 表——可打包 zip 或引用 GitHub

## B. 作者与声明
- [ ] 作者姓名、单位、邮箱、ORCID（IEEE 投稿系统要求）
- [ ] 通讯作者标注（单作者则本人）
- [ ] 利益冲突声明（如无：无）
- [ ] 基金资助（如有）
- [ ] **AI 使用披露**（ESL 强制；放 Acknowledgments，三要素齐全：工具名、涉及章节、程度）
- [ ] 确认 AI 未列为作者

## C. 数据与可复现
- [ ] GitHub 仓库 URL 写入正文（脚注或 Data Availability）：https://github.com/KAYOYAK/hachimodock-minimind-esp32p4
- [ ] 模型 SHA256（`feb574f9...`）与尺寸（28,632,448 B）在正文或补充材料中一致
- [ ] 评估脚本（`paper/heldout_ids.json`、`eval_prompts.json`、`score_prompts.py`）随仓库公开
- [ ] 训练证据（`docs/TRAINING-EVIDENCE.md`）可访问

## D. 数字一致性（投稿前逐项核对）
- [ ] 27.3 MiB / 28,632,448 B / 27.3
- [ ] n_ctx = 96，KV FP32 = 2,359,296 B；KV 后 PSRAM 剩余 2,352,828 B
- [ ] 2,639 ms/token；0.379 tok/s；r = 0.988；2.13× kernel；Amdahl 1.97×
- [ ] 权重流量 10.98 MB/s；含 KV 11.75 MB/s；PSRAM `/bw` 数值
- [ ] 启动 20.6 s 及其分解（mount / read / kernel / ready）
- [ ] CE（windowed，285 tokens）：q4 6.949；q3e4 7.087（1.020×）；mixed 7.037（1.013×）；q3 7.090；q2 10.074（1.450×）；英文语料 q3e4 1.048× / q2 1.829×
- [ ] 设备/主机 CE 逐窗口 Δ<0.001
- [ ] 30-prompt 规则评分：q3e4 ≥80%？q2 明显低？q4 主机评分？
- [ ] mixed 是否可启动（论文 frontier 说法依据）
- [ ] p-for-llm ~9 tok/s（as reported）；PIE 0.61–4.31（as reported）

## E. 审稿预判（回应准备）
- [ ] R1 精度判据（预注册 + 两语料 + 自动规则）
- [ ] R2 q4 主机模拟（host/device 对拍 Δ<0.001）
- [ ] R3 上下文 96 token（Table I + Limitations）
- [ ] R4 归因（r=0.988 + 流量 + PSRAM 带宽对照 → 指令流瓶颈，非带宽）
- [ ] R5 对照公平（as reported 脚注）
- [ ] R6 frontier vs unique（已改口径）
- [ ] R7 复现包（GitHub + Release）

## F. 投稿系统
- [ ] IEEE Author Portal 账号（与 ORCID 关联）
- [ ] 选择期刊：IEEE Embedded Systems Letters
- [ ] 文章类型：Letter（4 页）
- [ ] 上传 PDF + 源文件（.tex/.bib/图）
- [ ] 填写 AI 使用声明（如系统有单独字段）
- [ ] 提交后保存稿件编号

## G. 时间安排（当前）
- 2026-11-05 夜：完成设备测量（q3e4/q2/mixed）与初稿数字
- 2026-11-06 中午/晚上：补完剩余测量、排版、作者信息
- 之后：投稿
