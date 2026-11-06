# ESL 预期审稿意见 — 回应草稿（投稿前自检 + 投稿后 response letter 模板）

> 每条：审稿人可能问什么 → 我们已准备什么证据 → 一句话回应。
> 数字为 2026-11-06 最终实测（自训练模型，windowed CE，96-token 窗口 / 288 token 中文语料，除非注明）。

## R1. “精度下界定义不清 / 评估不严谨”
**回应**：判据在 Method 第一节预注册：(i) 固定文本集 windowed CE ≤ 1.15× q4；(ii) 30 条固定 prompt 规则评分 ≥80%；两阈值在测 q3e4 之前写死，之后未调整。
**证据**：`paper/heldout_text.txt`、`paper/heldout_ids.json`、`paper/heldout_en_ids.json`、`paper/eval_prompts.json`、`paper/score_prompts.py`、`paper/measurements/`。
**数字**：q4 CE=6.949（主机模拟锚点）；q3e4=7.087（1.020×，规则 80%）；mixed=7.037（1.013×，73.3%）；q3=7.090（1.020×）；mix432=7.467（1.075×）；mix42=7.673（1.104×）；q2=10.074（1.450×，规则 0%）。

## R2. “q4 是主机模拟的，不可信”
**回应**：q4 权重 36.0 MB > 32 MB PSRAM，无法在设备运行；用**相同 block-32 recipe** 主机模拟，并以 q3e4/q2 做 host/device 对拍：q3e4 逐窗口 Δ<0.001，q2 设备 10.073656 vs 主机 10.073659（Δ≈3e-6）。
**证据**：`tools/convert_minimind.py`、`paper/host_ce.py`、`paper/measurements/ce_host.csv`、设备日志 `logs/measure_q3e4_r.log`、`logs/measure_q2_all.log`。

## R3. “只有单一语料”
**回应**：两个固定语料，结论一致：中文技术文本（288 token/3 窗口）q3e4 1.020×、q2 1.450×；英文 Apache-2.0 license 文本（288 token）q3e4 1.048×、q2 1.829×。
**证据**：`paper/heldout_text.txt`、`paper/heldout_en_ids.json`、`paper/measurements/en/ce_host.csv`。

## R4. “上下文太短 / KV 预算不清”
**回应**：部署为 **192 token、FP16 K/V、2,359,296 B**（与 96 token FP32 同字节数），Table I 给出公式与实测剩余 2,352,828 B；FP16 替换实测 ΔCE=0.0015、速度不变；192 窗口 CE 5.970 vs 96 重置 7.014（约 −15%）。
**证据**：`board_config.h`（BOARD_CTX_TOKENS=192）、`logs/measure_kvfp16.log`、`logs/measure_kv192.log`。

## R5. “0.620 tok/s 的瓶颈归因有证据吗？”
**回应**：实测 r=0.977（最终构建，含 lm_head，GEMV 1,575 ms / 总 1,612 ms）；三个构建 r=0.988/0.985/0.977，Amdahl 预测（r 与 kernel 2.13×/1.23×/1.34×）分别 1.97×/1.22×/1.33×，与实测 2.13×/1.23×/1.34× 一致。GEMV 有效权重流量 18.2 MB/s（含 KV 19.2），PSRAM 顺序读微基准 95.9 MB/s → 瓶颈仍是解包+整数点积指令流，不是带宽。
**证据**：Table II、`logs/measure_q3e4_r.log`、`logs/measure_bw4.log`。

## R6. “为什么选 q3e4 而不是 mixed / 更小配置？”
**回应**：mixed 更准（1.013×）且更快（2,017 ms），但 KV 后 PSRAM 余量仅 0.58 MB；q3e4 余量 2.35 MB（约 4×），为 heap 碎片、USB 协议栈和上下文增长留余量。mix42/mix432 也通过判据但精度/规则分更低（1.104×/60%、1.075×/66.7%）。前沿是渐变的，不是单点唯一。
**证据**：Table III、`paper/measurements/ce_host.csv`、`rules_host.json`、`logs/measure_mixed.log`。

## R7. “容量结论是否只是算数？”
**回应**：不是——设备实测启动日志给出 q3e4 28,632,448 B 读入 20.6 s、KV 后 PSRAM 剩余 2,352,828 B；mixed（30.4 MB）在完整独立固件中也能启动并生成（frontier 可部署性）。
**证据**：`logs/measure_q3e4_r.log`、`logs/mixed_standalone_boot.log`、README。

## R8. “AI 使用是否披露？”
**回应**：Acknowledgments 已按 IEEE/ESL 政策披露：DeepSeek Harness AI coding agent（DeepSeek 模型）用于固件实现、量化/测量工具和文稿编辑；AI 不是作者，作者对全部内容负责。
**证据**：`paper/ACKNOWLEDGMENT-AI.md`、论文 Acknowledgments 段。
