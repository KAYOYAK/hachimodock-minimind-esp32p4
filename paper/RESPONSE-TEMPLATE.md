# ESL 预期审稿意见 — 回应草稿（投稿前自检 + 投稿后 response letter 模板）

> 每条：审稿人可能问什么 → 我们已准备什么证据 → 一句话回应。

## R1. “精度下界定义不清 / 评估不严谨”
**回应**：判据在 Method 第一节预注册：(i) 固定文本集 CE ≤ 1.15× q4；(ii) 30 条固定 prompt 规则评分 ≥80%。
**证据**：`paper/heldout_text.txt`（472 字，367 token，作者自写固定文本）、`paper/heldout_ids.json`、`paper/eval_prompts.json`（8 条官方 eval + 22 条补充）、`paper/score_prompts.py`（5 条确定性规则）、`docs/TRAINING-EVIDENCE.md`。
**数字**（自训练模型，主机同 recipe 模拟）：q4 CE=5.772（参考锚点，36 MB 装不下）；q3e4 CE=5.972（1.035×）；mixed CE=5.913（1.024×）；q3 CE=5.994（1.039×）；q2 CE=10.095（1.749×，明显越界）。

## R2. “q4 是主机模拟的，不可信”
**回应**：q4 权重 36 MB > 32 MB PSRAM，无法在设备上运行；用**相同 block-32 量化 recipe** 在主机模拟，并以 q3e4 做 host/device 对拍：设备 CE 与主机 CE 差异 `<Δ>`（待测）。
**证据**：`tools/convert_minimind.py`（recipe 源码）、`paper/host_ce.py`、`paper/measurements/ce_host.csv`、设备 `/ppl` 日志。

## R3. “只有单一语料”
**回应**：两个固定语料：作者自写中文技术文本（192/288 token 窗口）+ 第二语料（英文 Apache-2.0 文本，同 tokenizer 同窗口）。两套语料的结论一致（待测第二套）。
**证据**：`paper/heldout_text.txt`、第二语料文件与 `ce_host.csv`。

## R4. “上下文太短（96 token）/ KV 预算不清”
**回应**：Table I 写明 n_ctx=96、KV FP32=2,359,296 B、公式与实测剩余内存（2,352,828 B after KV）。§Limitation 明确单轮短指令场景。
**可选增强**：KV FP16 → 192 token 的对照（待测）。

## R5. “0.38 tok/s 的瓶颈归因有证据吗？”
**回应**：实测 r=0.988：GEMV 占 decode 的 98.8%；2.13× kernel 优化端到端几乎 1:1（Amdahl 预测 1.97×）。有效权重流量 10.98 MB/s 远低于 PSRAM 上限 → 瓶颈在 GEMV 的**解包+标量整数点积指令流**，不是纯带宽。已用 `/bw` 微基准测 PSRAM 顺序读带宽作为上限证据（`<数值>`）。
**证据**：Table II、`logs/measure_selftrain_q3e4.log`。

## R6. “和 p-for-llm 不是同条件比较”
**回应**：不主张同条件吞吐；Table III 脚注 “as reported, not reproduced”；正文一句 “different hardware/model scale; positions constraint differences”。
**证据**：Table III、`docs/PROTOCOL.md` 引用口径。

## R7. “q3e4 是唯一可行配置吗？”
**回应（重要，已修正）**：不是唯一。mixed（30.40 MB）同样满足容量+精度，但 KV 后仅剩 ~0.58 MB；q3e4（28.63 MB）剩 ~2.35 MB（4× 余量），被选为**部署点**。论文用 “feasibility frontier + deployment point” 表述，不写 “unique feasible”。
**证据**：Table I 右半、内存预算实测。

## R8. “可复现性”
**回应**：GitHub 仓库含固件、量化/训练工具、论文评估脚本、模型 Release（自训练 q3e4，SHA256 `feb574f9...`）；一条命令可复跑测量。
**证据**：https://github.com/KAYOYAK/hachimodock-minimind-esp32p4

## R9. “AI 使用”
**回应**：Acknowledgments 按 IEEE 三要素披露（工具、章节、程度）；AI 不是作者；作者验证并担责。

## R10. “训练/模型质量”
**回应**：不主张模型质量或对话能力；精度仅用于划定可行域。训练细节（pretrain 39,695 step/loss 2.01；SFT 56,608 step/loss 1.71；LoRA rank16/loss 1.2564）见 `docs/TRAINING-EVIDENCE.md`。
