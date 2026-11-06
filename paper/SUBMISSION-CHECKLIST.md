# IEEE ESL 投稿检查清单（最终状态，2026-11-06）

> 目标：IEEE Embedded Systems Letters（SCI 四区，4 页 letter）。
> 图例：✅ 完成 ｜ ❌ 待办（仅剩 2 项外部操作）｜ ⏳ 录取后

## A. 稿件文件

- ✅ 所有 `<...>` 占位已填（作者、单位、邮箱、日期、CE、规则、带宽、q2/mixed 数据）
- ✅ 本地编译通过：`tectonic --web-bundle https://relay.fullyjustified.net/default_bundle.tar ESL-LETTER-DRAFT.tex`
- ✅ **4 页整**（含 1 图 + 4 表 + 14 条参考文献；无 Overfull）
- ✅ 图 1（双栏：容量—精度前沿 + 逐 token 延迟），表 I–IV 均在栏内不断裂
- ✅ 参考文献 14 条，IEEE 风格；p-for-llm / PIE / 2026 综述均给出可检索来源
- ✅ 补充材料：GitHub 仓库 `paper/`（评估脚本、语料、prompt、CE CSV、模型 SHA256）

## B. 作者与声明

- ✅ 作者：Shizhou Xu（Guangxi Medical University, Nanning, China）
- ✅ 邮箱：X16717701114@outlook.com
- ❌ **ORCID iD**：仍缺（IEEE 要求所有作者都有；去 https://orcid.org/register 免费注册后填入投稿系统）
- ✅ 通讯作者：单作者，本人
- ✅ 利益冲突：已在 Acknowledgment 写“no conflict of interest”
- ✅ 基金：已写“no external funding”
- ✅ **AI 使用披露**（ESL 强制）：工具 = DeepSeek Harness AI coding agent（DeepSeek 模型），用途 = 固件实现、量化/测量工具、实验自动化、文稿编辑；AI 非作者，作者承担全部责任
- ✅ AI 未列为作者

## C. 数据与可复现

- ✅ 正文 Reproducibility 段写入仓库 URL：https://github.com/KAYOYAK/hachimodock-minimind-esp32p4
- ✅ 模型 SHA256 `feb574f9…`、尺寸 28,632,448 B 一致
- ✅ 评估脚本/语料/prompt 随仓库公开
- ✅ 训练证据 `docs/TRAINING-EVIDENCE.md` 可访问

## D. 数字一致性（论文最终版）

- ✅ 27.3 MiB / 28,632,448 B
- ✅ 上下文 192 token、KV FP16 = 2,359,296 B；KV 后 PSRAM 剩余 2,352,828 B
- ✅ 速度 **1,612 ms/token = 0.620 tok/s**；累计 **3.49×**（2.13× + 1.23× + 1.34×）；r=0.977
- ✅ GEMV 有效权重流量 18.2 MB/s（含 KV 19.2）；PSRAM 顺序读 95.9 MB/s
- ✅ 启动 ≈20 s（mount 53 ms / TF 读 20.6 s / kernel 70 ms / ready ~19.9 s）
- ✅ CE（windowed，285 tokens）：q4 6.949；q3e4 7.087（1.020×）；mixed 7.037（1.013×）；q3 7.090；q2 10.074（1.450×）；英文 q3e4 1.048× / q2 1.829×
- ✅ 设备/主机 CE 逐窗口 Δ<0.001
- ✅ 30-prompt 规则评分：q3e4 host 80%（设备 22/30）、q2 host 0%（设备 0/30）、q4 host 73.3%
- ✅ mixed 在完整固件可启动/生成（frontier 论据）
- ✅ p-for-llm ~9 tok/s、PIE 0.61–4.31（as reported）

## E. 审稿预判（回应准备）

- ✅ `paper/RESPONSE-TEMPLATE.md` 已按最终数字重写（R1–R8）

## F. 投稿系统（剩下的是你的操作）

- ❌ **ORCID 注册**（2 分钟，免费）→ 拿到 16 位 iD
- ❌ 注册/登录 IEEE Author Portal，关联 ORCID，上传稿件
- ✅ 发表方式：**传统（免费）**（OA 需 $2800，不选）
- ⏳ 视频 Graphical Abstract：**初次投稿不要求**，minor revision 阶段必须交（等屏幕到货后录）
- ⏳ 超页费：只有排版后超 4 页才收（$125/页）；当前源文件 4 页整，投稿后若 IEEE 排版超页再处理（硬上限 8 页）
- ⏳ 版权转让（eCF）：录取后处理

## 投稿时需要的文件

- `paper/draft.pdf`（4 页 PDF）
- `paper/submission/ESL-LETTER-source.zip`（tex + 图 + README，供排版）
- 可选 cover letter（初次投稿非必需；special issue/重叠工作才必须）
