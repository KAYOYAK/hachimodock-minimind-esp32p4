# 模型：从零训练 → LoRA → 量化 → 端侧部署

> 数据与日志来源：`D:\minimind`（2026-10-28 ~ 2026-11-01 实测产物）。所有数值来自训练日志，可复现。

## 1. 模型规格（MiniMind-3 Zero 架构，Qwen3 同构）

| 项目 | 值 |
|---|---|
| 参数量 | 63.91M |
| 层数 | 8 |
| hidden dim | 768 |
| heads / kv heads | 8 / 4（GQA） |
| head_dim | 96 |
| FFN | 2432（SwiGLU） |
| vocab | 6400（tied embedding） |
| rope_theta | 1,000,000 |
| max_position | 32768 |
| norm | Pre-Norm RMSNorm + **q_norm / k_norm**（每 head，RoPE 前） |
| 注意力 | SDPA（flash） |
| 训练精度 | BF16 autocast，FP32 部署前量化 |

## 2. 从零完整训练（本地 RTX 5070 Ti Laptop 12GB）

**数据**（ModelScope `gongjy/minimind_dataset`）：

| 文件 | 规模 | 用途 |
|---|---|---|
| `pretrain_t2t_mini.jsonl` | 1,270,238 条 / 1.184 GB | 预训练 |
| `sft_t2t_mini.jsonl` | 905,718 条 / 1.659 GB | SFT（含 Tool Call） |

**训练配置（官方 mini 配方，1 epoch）**

| 阶段 | 超参 | 步数 | 耗时 | 最终 loss |
|---|---|---|---|---|
| 预训练 | bs=32、accum=8（有效 256）、seq=340、lr=5e-4、bf16 | 39,695 | 2h26m03s | **2.01** |
| SFT | bs=16、accum=1、seq=768、lr=1e-5、bf16 | 56,608 | 4h06m14s | **1.71** |
| **合计** | AdamW + 余弦调度（0.1 下限）、梯度裁剪 1.0 | — | **6h32m17s** | — |

- GPU 稳定态：利用率 98–99%，功耗 132–139 W，温度 76–78 °C，显存 8.0–8.5 GB；
- 每 1000 step 存盘（权重 131 MB + 续训检查点 750 MB），看门狗 0 次重启；
- 与官方 Zero 同 prompt 对比：同一质量量级（身份记忆、事实准确率受 64M 上限限制）。

**产物**：`D:\minimind\src\minimind-master\out\full_sft_768.pth`（自训 SFT 权重）。

## 3. LoRA（医药领域复刻）

用官方数据 + 官方超参重新训练医药 LoRA（不是加载官方 LoRA）：

| 项目 | 值 |
|---|---|
| 基座 | 官方主线 SFT 权重（131.3 MB，`official_full_sft_768.pth`） |
| 数据 | `lora_medical.jsonl`，25,276 条（32.43 MB） |
| 结构 | rank=16，命中 16 个方阵 Linear（q_proj/o_proj × 8 层） |
| 可训练参数 | **393,216（0.39M）** |
| 训练 | 10 epochs / 7,900 step / 24 分钟 / final loss **1.2564** |
| 产物 | `out/lora_medical_repro_768.pth`（779 KB） |

**效果（留出集 loss，越低越好）**

| 模型 | 医疗留出 | 通用留出 |
|---|---|---|
| 裸基座 | 1.5553 | 0.8672 |
| 复刻 LoRA | **1.3109（-15.7%）** | 1.2935 |
| 官方 LoRA | 1.2263（-21.2%） | 1.5823 |

与官方 LoRA 权重余弦相似度 ≈ 0（效果级复刻，非权重级）。

## 4. 量化（本项目实现）

自定义 KMCU 格式，block=32 权重：

| dtype | 字节/32权重 | 说明 |
|---|---|---|
| `q4_0` | 18 | fp16 scale + 16 B nibbles，`w=(nib-8)*d` |
| `q3_0` | 14 | fp16 scale + 12 B 3-bit LSB-first，`w=(q-4)*d` |
| `q2_0` | 10 | fp16 scale + 8 B 2-bit（质量不可用，保留格式） |

部署档位 **q3e4**：embedding=q4，attention/FFN=q3 → **28,632,448 B（27.3 MiB）**，可全驻 32 MB PSRAM。
（q4 = 36 MB 装不下；mixed 30.4 MB 接近上限。）

量化命令：

```bash
python tools/convert_minimind.py --profile q3e4 \
  --input <hf_export_dir> --output artifacts/model.kmcu
```

> 若使用自训权重：先用 `tools/pth2hf.py` 将 `full_sft_768.pth` 转 HF Qwen3 格式，再量化。

## 4.5 量化质量验证（q3e4）

| 指标 | 结果 |
|---|---|
| HF 转换 vs 原生 MiniMind 前向 | logits `max|diff| = 0.000e+00` |
| 端侧 packed GEMV vs PC NumPy 参考 | top-8 token ids 全一致，`max|diff|≈0.00002` |
| greedy 序列 | 逐 token 完全一致（PC 参考 vs 板端 `/ids`） |
| 板端生成样例 | `你好！我是一个AI助手，我是一个虚拟`（与 PC 参考开头一致） |

不同量化档位（同架构、不同体积/质量取舍）：

| 档位 | 大小 | 说明 |
|---|---|---|
| q2 | 20,030,848 B | 可装下但质量明显下降，不推荐 |
| q3 | 28,018,048 B | 纯 q3，质量略低于 q3e4（embedding q3 拖累） |
| **q3e4（部署档）** | **28,632,448 B** | embedding q4 + attn/FFN q3，32MB PSRAM 全驻，最佳平衡 |
| q4 | 36,005,248 B | 质量最好但 36MB > 32MB PSRAM，只能 TF 流式（最终构建 0.620 tok/s；流式还会更慢） |

> q4 与非量化 bf16 的 1:1 逐 token 对拍未做（无 36MB 常驻内存条件），但 q3e4 的 top-8/贪心序列已与 fp32 参考完全一致，说明量化误差没有改变解码轨迹。

## 5. 数值对齐（已实测）

- HF Qwen3 转换 vs 原生 MiniMind 前向：logits `max|diff| = 0.000e+00`；
- 端侧 packed GEMV vs PC NumPy 参考：top-8 ids 全一致，`max|diff|≈0.00002`，greedy 序列逐 token 一致；
- 板端 `/ids` 贪心输出与 PC 参考一致（板端 kernel 数值正确）。

## 6. 端侧优化

1. **零拷贝打包权重**：`pk` 指向 PSRAM 中的 KMCU 镜像，按块现场反量化，arena 仅 58 KB；
2. **QK-norm**：Qwen3 的 q_norm/k_norm 在 GEMV 后、RoPE 前按 head 应用；
3. **int16 激活量化 GEMV**：激活量化到 int16，权重解包 int8 做整数点积 → 5,622 → **2,639 ms/token（2.13×）**；\n4. **激活量化外提 / offset 消除**：lm_head 的激活量化从 6400 行重复调用外提为每 token 一次，GEMV 用块和消除逐权重 offset → 2,152 ms/token（累计 2.61×），CE 不变；\n5. **批量解包 / 4 路展开 / `-O3`**：q4/q3/q2 全部 4 累加器 + 常量移位，两行同时计算，`-O3` 编译 → **1,612 ms/token（累计 3.49×）**；
4. KV cache FP32，ctx=96（约 2.36 MB PSRAM）；
5. 任务栈按实测调整（host 12 KB / 推理 16 KB），避免栈保护崩溃。

## 7. 实测性能

| 指标 | 值 |
|---|---|
| 解码速度 | **1,612 ms/token（0.620 tok/s）**，累计 **3.49×** 于标量基线 5,622 ms |\n| GEMV 占比 r | **0.977**（最终构建，含 lm_head） |\n| PSRAM 顺序读带宽 | **95.9 MB/s**（1 MB 微基准） |\n| 设备/主机 CE 对拍 | 逐窗口 **Δ<0.001** |\n| 30-prompt 规则评分 | q3e4 **80%**（fp32 80%）、q2 **0%** |
| prompt 处理 | 与逐 token 同速（无 batch prefill） |
| 模型加载 | 20.6 s（TF 卡条件相关） |
| PSRAM 占用 | ≈29.66 MiB / 32 MiB |
| 参数量 | 63.91M |

## 8. 复现工具

| 脚本 | 作用 |
|---|---|
| `tools/pth2hf.py` | MiniMind pth → HF Qwen3 格式 |
| `tools/convert_minimind.py` | HF → KMCU（q4/q3/q2/混合位宽） |
| `tools/export_tokenizer.py` | 导出 tokenizer.bin |
| `tools/host_eval.c` | PC 端推理对拍 harness |
| `tools/ref_minimind.py` | NumPy 参考实现 |
| `tools/tokenizer_check.py` | 分词器 79/79 对拍 |
| `D:\minimind\run_full_training.ps1` | 一键预训练 + SFT |
| `D:\minimind\overnight.ps1` | 无人值守训练 + 自动评测 |
| 训练脚本 | `trainer/train_pretrain.py`、`train_full_sft.py`、`train_lora.py` |

## 9. 训练环境

| 项 | 值 |
|---|---|
| GPU | RTX 5070 Ti Laptop 12 GB（sm_120） |
| Python | 3.12.10（便携 embeddable） |
| torch | 2.14.1+cu130 |
| transformers | 4.57.6 |
| datasets / numpy | 3.6.0 / 2.5.4 |
| 数据/权重来源 | ModelScope `gongjy/minimind_dataset`、`gongjy/minimind-3-pytorch` |
| 日志/报告 | `D:\minimind\logs\`、`REPORT.md`、`CONVERSATION_SUMMARY.md` |
