# ESL Letter — 4 页写作骨架（v6，数字已对齐仓库）

> 目标：IEEE Embedded Systems Letters，4 页（含图表与参考文献）。
> 标题（KV=96，已定）：**Fully-Resident Weight Storage for Mixed-Precision SLM Inference on a 32-MB PSRAM MCU**
> 一句话主张：在 32 MB PSRAM 硬容量下，q3e4 混合位宽让 63.91M 稠密 SLM 的 27.3 MiB 权重全驻留成为可能；0.465 tok/s（2,152 ms/token）的延迟由 GEMV 指令流主导，而非算力。

---

## Abstract（≈150 词，定稿前只改 N / 阈值 / r 三处）

We show that mixed-precision quantization is the enabling factor for fully-resident weight
storage of a dense SLM on a 32-MB PSRAM MCU. A 63.91M-parameter model, quantized to **q3e4
(embedding/output q4, attention/FFN q3)** and **27.3 MiB** total, runs entirely in on-package
PSRAM with a **192-token context** (FP16 K/V); no host participates at inference time. Measured decode
throughput is **0.465 tok/s (2.152 s/token) after int16/packed GEMV plus quantization hoisting** (2.61x cumulative over the 5,622 ms scalar baseline), and
int16 activation with zero-copy packed weights yields a **2.1× GEMV kernel-level speedup over
that baseline**. Our memory budget is auditable line-by-line (weights, KV cache, arena,
scratch, residual), and a three-point feasibility triangle — q2 crosses the accuracy cliff,
q4 exceeds the 32-MB budget, q3e4 satisfies both capacity and an accuracy lower bound — is
reported with pre-declared criteria. Unlike a 180.9M MoE design that trades residency and
host-assisted boot for throughput, the contribution here is a dense, self-contained residency
point plus its bandwidth–latency characterization.

## I. Introduction（≈300 词）

1. **死锁**：32 MB PSRAM 是硬容量；稠密 63.91M 模型 FP16 需 ~128 MiB，必须压缩；无主机启动依赖（不同于从 USB 灌权重）。
2. **两条绕行路径**：p-for-llm（180.9M MoE，W1.58A8，~44 MiB 分布在 Flash+PSRAM，USB 启动灌 PSRAM 权重，主机不参与推理但启动依赖主机；~9 tok/s 靠 Top-1 29 experts 稀疏路由）；PIE 系列（0.61→4.31 tok/s，内核级向量加速，不处理容量约束）。没有工作回答“稠密全驻留上界 + 到界后的代价”。2026 系统综述：MCU 全驻留 LLM 证据集中在 256–412 KB 任务 SLM 与一个 5.81 MB 全三值化 ViT；27.3 MiB 稠密权重落在空白区。
3. **答案**：q3e4 使 27.3 MiB 全驻留成立（192-token FP16-KV 上下文、0.465 tok/s）；贡献边界：不主张量化/系统架构创新，主结果是容量边界与带宽—延迟刻画。USB 协议桥只在实验设置一句带过。

## II. Method（≈450–500 词）

- **q3e4 定义**：embedding 与输出层 q4；attention 与 FFN 线性层 q3；激活 int16；**KV cache FP32（实测配置）**；norm 与 bias FP32/FP16（按固件实际）。
- **精度下界（先于结果声明）**：同时满足 (i) 固定文本集上每 token CE ≤ 1.15 × q4 CE（q4 主机同 recipe 模拟）；(ii) 20–30 条固定 prompt 的自动规则评分 ≥ 80%。阈值预注册，不随结果调整。
- **布局依据（容量计算而非“我们发现”）**：embedding/输出层参数占 ~5.8M（6400×768×2）且对词义敏感；FFN 占参数主体、是压缩主来源；attention 保守 q3。
- **零拷贝打包 GEMV**：逐元素反量化会吃掉带宽收益；权重按行对齐 + block-32 scale 预打包；激活量化 int16 做整数点积；减少无效 PSRAM 事务。
- **训练流水线一句**：pretrain 39,695 step/2h26m/loss 2.01 → SFT 56,608 step/4h06m/loss 1.71 → 医药 LoRA rank16/loss 1.2564 → q3e4。QK-norm 修复作为使能条件一句。

## III. Results（≈600–650 词）

### Table I（左：预算；右：可行域三角）

| Left: budget (measured) | Bytes |
|---|---|
| q3e4 weights | 28,632,448 (27.3 MiB) |
| KV cache, 96 tok, FP32 | 2,359,296 (2.25 MiB) |
| Arena (norm f32, internal RAM) | 58,368 |
| Scratch + int16 activation + GEMV workspace (internal RAM) | 52,608 |
| PSRAM residual (USB/protocol/heap) | 2,352,828 |
| **PSRAM total** | **≤ 32 MiB** ✔ |

| Front | q2 | q3 | **q3e4** | mixed | q4 |
|---|---|---|---|---|---|
| Weight size (B) | 20,030,848 | 28,018,048 | **28,632,448** | 30,401,920 | 36,005,248 |
| Fits 32 MB PSRAM | yes | yes | **yes** | yes (~0.58 MB free) | no |
| CE (windowed, 285 tok) | 10.074 | 7.090 | **7.087** | 7.037 | 6.949 |
| CE / q4 | 1.450 | 1.020 | **1.020** | 1.013 | 1.000 |
| Rule score (30 prompts) | **0%** | 待测 | **80%** | 73.3% | 73.3% |
| Speed (device, optimized) | **1,352 ms (0.740 tok/s)** | 待测 | **2,152 ms (0.465 tok/s)** | 待测 | n/a |
| Accuracy bound | fail | pass | **pass** | pass | reference |
| Role | speed for quality cliff | - | **deployment point** | low headroom | capacity cliff |

> ⚠️ Provenance fix (2026-11-05): the previously published `model.kmcu` was quantized from
> `official_full_sft_768.pth`; it has been replaced by the **self-trained** `full_sft_768.pth`
> pipeline (`work/hf_minimind3_selftrained`, native-vs-HF logits max|diff|=0). New SHA256
> `feb574f9...` (28,632,448 B). CE numbers above are for the self-trained model (host simulation,
> same block-32 recipe; device CE to be measured).
>
> Frontier wording: mixed (30.40 MB) also satisfies capacity+accuracy but leaves only ~0.58 MB
> after KV; **q3e4 is the deployment point because it keeps ~2.35 MB headroom** (~4×), not
> because it is the unique feasible configuration. Paper claim must use this framing.

### Table II（GEMV 消融，2026-11-05 实测 r）

| Config | ms/token | Speedup | Bytes/token | r (GEMV share) | Removed bottleneck |
|---|---|---|---|---|---|
| scalar float / expanded | 5,622 | 1× | ~28.7 MB | — | 逐元素反量化 + 标量 float 点积 |
| int16 activation + zero-copy packed | **2,639** | **2.13× kernel-level** | 28.63 MB | **0.988** | 反量化内存流量 + 权重重排 |\n| + 激活量化外提 / offset 消除 | **2,152** | **2.61× 累计** | 28.63 MB | **0.985** | 每行重复量化 + 逐权重 offset |
| (future) PIE / vectorized unpack | — | 待评估 | — | — | 指令流（unpack + int dot） |

**Amdahl**：格式改动 r=0.988、kernel 2.13× → 预测 1.97×（实测 2.13×）；外提 r=0.985、kernel 1.23× → 预测 1.22×（实测 1.23×）。GEMV 占 decode 98.5%，内核优化几乎 1:1 传递到端到端。

> ⚠️ **归因更正（2026-11-05 实测）**：GEMV 有效权重流量 = 28.63 MB / 2.608 s ≈ **10.98 MB/s**，远低于 PSRAM 标称/可持续带宽；这指向 **GEMV 的指令流（解包 + 标量整数点积）** 是主瓶颈，而不是“PSRAM 带宽不够”。token 速率 0.38 tok/s 的说法必须建立在“GEMV 内核指令流”归因上；`/bw` 微基准（PSRAM 顺序读带宽）将给出带宽上限证据。论文措辞改为：
> “decode is dominated by the GEMV kernel (r=0.988), whose scalar unpack/dot instruction stream — not PSRAM bandwidth — limits throughput; a 2.1× kernel-level optimization therefore appears almost fully end-to-end.”

### Table III（对照，as reported）

| Work | Model | Residency | Boot host dependency | Throughput | Core contribution |
|---|---|---|---|---|---|
| p-for-llm | 180.9M MoE (W1.58A8) | partial: PSRAM weights + Flash XIP PLE | yes (USB weight transfer) | ~9 tok/s (reported) | MoE sparsity buys throughput |
| PIE | — | — | — | 0.61→4.31 tok/s (reported) | kernel-level vector acceleration |
| **This work** | 63.91M dense | **full: 27.3 MiB in PSRAM** | **no** | **0.465 tok/s** | capacity-bound residency point + cost model |

> Footnote: throughput values for p-for-llm and PIE are as reported by their authors, not reproduced here; different hardware/model scales — comparison positions constraint differences, not direct throughput.

## IV. Discussion & Limitation（≈200 词）

- 0.38 tok/s 只适合事件驱动、单轮短输出；端到端响应数百 ms–数秒（数据待测）。
- 上下文 96 token 是硬代价（KV FP32；FP16 KV 可到 ~192，未采用）。
- PSRAM 有效带宽受总线配置/cache/并发 DMA 影响，不能用标称带宽除 bytes/token 预测延迟。
- 设计准则：32 MB PSRAM 上混合位宽优先保 embedding/输出层；FFN 是压缩主来源；q2 越过精度悬崖。
- 训练/LoRA/固件/量化 artifact 已在 GitHub 开源（一句）。

## V. Acknowledgments（AI 披露，ESL 强制）

见 `paper/ACKNOWLEDGMENT-AI.md` 草稿；必须放 Conclusion 之后、References 之前。

## References（15–18 条配比）

1–3 MCU/边缘 transformer 推理系统与 2026 综述（语境：全驻留证据稀缺）
4–6 混合精度量化（INT2–INT8、层间分配；均不以全驻留为硬约束）
7–9 PSRAM 带宽/内存墙/MCU 存储层次实测
10 p-for-llm（GitHub/技术报告）
11 PIE 系列（技术报告）
12 QK-norm（Qwen3）
13 int16 激活推理
14 ESP32-P4 硬件文档
15 MiniMind 架构参考
16 HachimoDock 协议（系统闭环，可选）

## 4 页预算（排版时守）

| 部分 | 行数/词数 |
|---|---|
| Abstract | 150 词 |
| I Introduction | 300 词 |
| II Method | 450–500 词 |
| III Results + 3 tables | 600–650 词 |
| IV Discussion | 200 词 |
| V Acknowledgments | 60 词 |
| References | 15–18 条（约 0.5 页） |
| 合计 | ≈ 4 页（双栏） |

### 第二语料（英文 Apache-2.0 license 文本，192 token）— 已测

| profile | CE | CE/q4 |
|---|---|---|
| q4 | 5.415 | 1.000 |
| q3e4 | 5.676 | 1.048 |
| q3 | 5.647 | 1.043 |
| mixed | 5.645 | 1.042 |
| q2 | 9.905 | **1.829** |

结论：两个语料（中文技术文本 / 英文公共文本）的排序与结论一致——q3e4 均通过 1.15× 判据（中文 1.035×，英文 1.049×），q2 均明显越界（1.75× / 2.04×）。第二语料数据存 `paper/measurements/en/ce_host.csv`。

### 设备 / host 对拍（2026-11-05 实测，windowed 96-token）

- 设备 q3e4 CE（285 tokens / 3 windows）：`[6.662094, 7.368362, 7.231992]`，mean **7.087483**；
- host 同 recipe 同窗口：`[6.662139, 7.368315, 7.232006]`，mean **7.087486**；
- **逐窗口 Δ < 0.001** → “q4 主机模拟”口径可信；
- 设备 r=0.988，gemv=2607 ms/token，总 2639 ms/token（0.379 tok/s）。

> 说明：早期 (非 windowed) host CE 5.97 与设备不可比，已废弃；论文统一用 windowed CE（每 96 token 独立 reset，与部署上下文一致）。
