# IEEE Author Portal — 投稿信息（可直接复制）

> 作者：Shizhou Xu（单作者 / 通讯作者）
> 生成时间：2026-11-06

## 稿件

- **Manuscript type**: Research（regular research letter）
- **Title**: Fully-Resident Weight Storage for Mixed-Precision SLM Inference on a 32-MB PSRAM MCU
- **Keywords (5)**: Edge AI; on-device inference; large language models; mixed-precision quantization; PSRAM
- **Open Access**: Traditional（免费；不选 OA，避免 $2800 APC）
- **Conflicts of interest**: None
- **Funding**: None

## Abstract（约 200 词，可直接粘贴）

We show that mixed-precision quantization enables fully-resident weight storage of a dense small language model (SLM) on a 32-MB PSRAM microcontroller. A 63.91M-parameter model quantized to q3e4 (embedding/output q4, attention and FFN q3) occupies 27.3 MiB and runs entirely in on-package PSRAM with a 192-token context window (FP16 K/V cache) and no host at inference time. Measured decode throughput is 0.620 tok/s (1.61 s/token) after int16-activation, zero-copy packed GEMV, activation-quantization hoisting, and a 32-bit batch-unpack / four-way-unrolled / -O3 pass, a 3.49x cumulative speedup over the scalar baseline (2.13x storage format, 1.23x hoisting, 1.34x unpack); the GEMV kernel dominates decode time, so kernel-level gains pass through almost unchanged to end-to-end latency. A pre-registered accuracy lower bound (fixed-text cross-entropy within 1.15x of q4, plus a deterministic 30-prompt rule score >= 80%) separates the feasible configurations: q2 crosses the accuracy cliff, q4 exceeds the 32-MB budget, and mixed/q3e4 both meet the bound while q3e4 keeps about four times more PSRAM headroom and is selected for deployment.

## Author 1（对应系统里的 "Add Author"）

- **Given name**: Shizhou
- **Family name**: Xu
- **Affiliation**: Guangxi Medical University, Nanning, China
- **E-mail**: X16717701114@outlook.com
- **ORCID iD**: 0009-0001-1366-8144
- **IEEE member number**: 无（非会员，不影响投稿）
- **Corresponding author**: 是（唯一作者）

## AI 使用披露（Acknowledgments 已在稿件里；系统若单独询问）

The author used the DeepSeek Harness AI coding agent (DeepSeek model) to assist with the ESP32-P4 firmware implementation, quantization and measurement tooling, experiment automation, and manuscript editing. The AI system is not an author. The author independently verified all generated code, measurements and text and takes full responsibility for the accuracy, originality and integrity of this work. This work received no external funding, and the author declares no conflict of interest.

## 上传文件

- `/paper/submission/ESL-LETTER-DRAFT.pdf` — 4 页 PDF（投稿主文件）
- `/paper/submission/ESL-LETTER-source.zip` — .tex + 图 + README（可选上传，供排版）
- Cover letter：初次投稿**不要求**，可跳过（ESL 官方：仅 special issue / revision / 重叠工作时必须）

## 提交后

- 初审目标：约 1 个月；revision 需 2 周内返回；
- 录用后 minor revision 阶段必须交 **video graphical abstract**（视频 + 说明 + 封面图），等屏幕到货后录制；
- 排版后若超过 4 页会产生 $125/页 超页费（当前源文件正好 4 页）。
