# MiniMind 本地复刻全记录（对话总结）

> 整理时间：2026-11-01 17:02（Asia/Shanghai）
> 会话跨度：2026-10-28 18:03 ～ 2026-11-01 17:01
> 记录人：DSH Lead（AI Agent）
> 对应项目目录：`D:\minimind`
> 文档定位：对本会话全部工作、决策、命令、数据、结果与踩坑的完整复盘，可独立阅读。

---

## 目录

1. [需求与最终结论](#一需求与最终结论)
2. [硬件与环境基线](#二硬件与环境基线)
3. [网络限制与资源获取策略](#三网络限制与资源获取策略)
4. [环境搭建过程（含失败与修复）](#四环境搭建过程含失败与修复)
5. [代码、数据、权重清单](#五代码数据权重清单)
6. [阶段三：官方权重推理验证](#六阶段三官方权重推理验证)
7. [阶段一：从零完整训练](#七阶段一从零完整训练)
8. [训练结果与模型质量评估](#八训练结果与模型质量评估)
9. [医药 LoRA 复刻](#九医药-lora-复刻)
10. [产物与目录结构](#十产物与目录结构)
11. [常用命令手册](#十一常用命令手册)
12. [踩坑与解决方案](#十二踩坑与解决方案)
13. [完整时间线](#十三完整时间线)
14. [经验总结与后续建议](#十四经验总结与后续建议)
15. [附录：关键数值表与对话样例](#附录关键数值表与对话样例)

---

## 一、需求与最终结论

### 1.1 用户需求

1. **原始需求**：「能不能复刻一下 MINIMIND，不租服务器」
   - 即在本地 GPU 上完整走通 MiniMind（jingyaogong/minimind）的训练链路，不使用云服务器。
2. **分阶段选择**（2026-10-28 18:13 用户确认）：
   - 先完成「阶段三」：环境搭建 + 官方权重推理对比；
   - 晚上再完成「阶段一」：从零完整训练（pretrain + SFT 各 1 epoch）。
3. **夜间要求**（2026-10-28 21:23）：「我去睡觉了，明天 7 点之前你将不会得到任何的回复了，一切由你自行解决」。
4. **关机要求**（2026-10-28 22:5x）：「如果 7 点前全部完成了的话你可以帮我关机」。
5. **后续需求**（2026-10-29 17:47）：「可以跑一遍 minimind 官方的医药 lora」，随后澄清：「不是直接用哦，是复刻这个 lora」——即用官方数据重新训练该 LoRA，而不是加载官方权重。
6. **收尾需求**（2026-11-01 17:01）：将本对话内容总结为详细全面的 Markdown 文件。

### 1.2 最终结论

| 目标 | 结果 |
|---|---|
| 本地环境（不租服务器） | ✅ 便携 Python 3.12.10 + torch 2.14.1+cu130（RTX 5070 Ti Laptop 12GB，sm_120） |
| 阶段三：官方权重推理 | ✅ 官方 Zero / 主线 SFT 权重均可在本地推理，60–74 tokens/s |
| 阶段一：从零完整训练 | ✅ pretrain 1 epoch + SFT 1 epoch，共 6h32m，最终 loss 2.01 / 1.71 |
| 训练失败保护 | ✅ 看门狗 0 次重启、每 1000 step 存盘、可断点续训 |
| 夜间自动评测 | ✅ 自训模型与官方 Zero 同 prompt 对比，03:49:34 完成 |
| 关机 | ✅ 04:56 发起（`shutdown /s /t 300`），约 05:01 断电（系统事件已验证） |
| 医药 LoRA 复刻 | ✅ 25,276 条官方医疗数据、10 epochs、24 分钟，产出 `lora_medical_repro_768.pth` |
| 复刻质量 | ⚠️ 链路级完全复刻；模型能力受 64M + 1 epoch 限制；LoRA 为「效果级复刻」而非权重级 |

**一句话总结**：在本机 12GB 笔记本显卡上，从零完成了 MiniMind-3 Zero（63.91M）的预训练 + SFT 全流程，并把官方医药 LoRA 用官方数据和官方超参重新训练了一遍；全流程无服务器、无中断，产物与日志完整保留在 `D:\minimind`。

---

## 二、硬件与环境基线

### 2.1 硬件（开局实测）

| 项 | 值 |
|---|---|
| 机型 | 笔记本（Windows，WDDM 驱动模型） |
| GPU | **NVIDIA GeForce RTX 5070 Ti Laptop GPU**，显存 **12,227 MiB**（12GB） |
| 驱动 / CUDA | 驱动 621.01，CUDA UMD 13.5，**compute capability (12, 0) = sm_120（Blackwell）** |
| 磁盘 | C: 可用 113GB / 总 298.9GB；D: 可用 350.9GB / 总 653.7GB |
| 内存 | WMI 查询受限，未取得确切总容量；实测可用约 21.6GB（推断 32GB 级别） |
| 电源 | 插电（AC，电量 100%），GPU 功耗墙：default 65W / max 140W，训练时实际 132–139W |

### 2.2 软件基线（开局）

| 项 | 状态 |
|---|---|
| Python | 仅 3.14.8（uv 管理，`C:\Users\XSZ20\AppData\Local\Python\pythoncore-3.14-64`），**无 torch** |
| 包管理器 | pip 可用、uv 可用（后续 cache 目录受限）、conda 无 |
| 其他 | git ✅、Node ✅、py launcher ✅ |
| 环境变量 | `HF_HOME=D:\models\hf_cache`（已存在） |
| 本机已有资源 | `D:\models`（HF 缓存、LoRA、MiMo-9B-GGUF）、`D:\llama.cpp`、`D:\AI` 等，与本次任务无关 |

### 2.3 关键性能画像（训练后实测）

- 训练稳定态：GPU 利用率 **98–99%**、功耗 **132–139W**、温度 **76–78°C**、显存 **8.0–8.5GB**
- 实测算力效率约 **17–19 TFLOPS**（bf16），明显低于桌面 3090（官方 2.31h vs 本机 6.32h，约 2.7–3 倍慢）
- 推理：**60–74 tokens/s**（64M 模型，half 精度，含 KV cache）

---

## 三、网络限制与资源获取策略

### 3.1 开局网络状况

| 目标 | 结果 |
|---|---|
| github.com | ❌ 连接失败（DNS 可解析，TCP 000） |
| raw.githubusercontent.com | ❌ |
| pypi.org | ✅ 200 |
| download.pytorch.org | ✅ 索引可用（根路径 403 属正常） |
| www.modelscope.cn | ✅ 302/200（国内直连） |
| python.org | ✅ 200 |
| hf-mirror.com / huggingface.co | 未使用（HF 直连不可用，改走 ModelScope） |

> 说明：初始 DSH 文件沙箱限制了网络，经用户批准切换到 danger-full-access 后仍无法直连 GitHub（属真实网络限制，非沙箱问题）。

### 3.2 实际采用的获取渠道

| 资源 | 渠道 | 结果 |
|---|---|---|
| MiniMind 源码（master tarball） | **`https://gh-proxy.com/https://github.com/...`** 镜像 | ✅ 10.27 MB，解压到 `D:\minimind\src\minimind-master` |
| 数据集（pretrain/sft/lora_medical） | ModelScope 数据集 API 直链 | ✅ 高速（约 10–25 MB/s） |
| 官方模型权重（.pth） | ModelScope 模型 API 直链 | ✅ |
| Python / pip / PyPI 包 | python.org、bootstrap.pypa.io、pypi.org | ✅ |
| torch CUDA 轮子 | `https://download.pytorch.org/whl/cu130` | ✅ cp312 win_amd64 存在 |

ModelScope 直链格式（本会话实际使用）：

```
# 数据集文件
https://www.modelscope.cn/api/v1/datasets/gongjy/minimind_dataset/repo?Revision=master&FilePath=<文件名>

# 模型文件
https://www.modelscope.cn/api/v1/models/gongjy/minimind-3-pytorch/repo?Revision=master&FilePath=<文件名>
```

---

## 四、环境搭建过程（含失败与修复）

### 4.1 Python 3.12 官方安装器失败（已解决并回滚）

1. 从 python.org 下载 `python-3.12.10-amd64.exe`（25.7MB），静默安装：
   ```powershell
   Start-Process python-3.12.10-amd64.exe -ArgumentList '/quiet','InstallAllUsers=0',
     'TargetDir=D:\python312','Include_pip=1','Include_launcher=0','AssociateFiles=0',
     'Shortcuts=0','PrependPath=0','Include_test=0' -Wait
   ```
2. 问题：退出码 0，但目录缺少 **`python312.dll`**；`python.exe --version` 返回 `-1073741515`（0xC0000135，STATUS_DLL_NOT_FOUND），venv 创建同样失败。
3. 处理：改用**免安装 embeddable 版本**；该破损安装后来已用安装器 `/uninstall` 卸载，并从 `py -0p` 中清除，系统状态恢复干净。

### 4.2 最终方案：便携 Python 3.12.10（embeddable zip）

```powershell
# 1) 下载并解压
curl.exe -sL -o python-3.12.10-embed-amd64.zip https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
Expand-Archive python-3.12.10-embed-amd64.zip -DestinationPath D:\minimind\python312

# 2) 打开 site-packages 支持（编辑 D:\minimind\python312\python312._pth）
python312.zip
Lib\site-packages
.
D:\minimind\src\minimind-master        # 关键：embed 版会忽略 PYTHONPATH

# 3) 安装 pip
curl.exe -sL -o get-pip.py https://bootstrap.pypa.io/get-pip.py
D:\minimind\python312\python.exe get-pip.py
```

最终解释器：`D:\minimind\python312\python.exe`，pip 26.2.2。

### 4.3 依赖安装

```powershell
# PyTorch（sm_120 需要 cu128+，选 cu130）
D:\minimind\python312\python.exe -m pip install "torch==2.14.1+cu130" `
  --index-url https://download.pytorch.org/whl/cu130 --extra-index-url https://pypi.org/simple

# 其余依赖（注意不要沿用 requirements.txt 的 numpy==1.26.4）
D:\minimind\python312\python.exe -m pip install `
  "transformers==4.57.6" "datasets==3.6.0" psutil jsonlines ujson safetensors `
  tokenizers sentencepiece
D:\minimind\python312\python.exe -m pip install "numpy>=2.0,<3"   # 升到 2.5.4
```

**关键坑：numpy 版本冲突**

- 官方 `requirements.txt` 固定 `numpy==1.26.4`，但实际安装的 `pyarrow 26.0.0` 要求 **NumPy ≥ 2.0**，导入 `datasets` 直接报：
  `ImportError: pyarrow requires NumPy 2.0 or newer, found 1.26.4`
- 解决：升级到 numpy **2.5.4**，MiniMind 代码与 transformers 4.57.6 均兼容，训练/推理正常。

**最终环境版本（实测）**

| 包 | 版本 |
|---|---|
| Python | 3.12.10（portable embeddable） |
| torch | **2.14.1+cu130**（CUDA 可用，sm_120 ✅） |
| transformers | 4.57.6 |
| datasets | 3.6.0 |
| numpy | 2.5.4 |
| pyarrow | 26.0.0 |
| tokenizers | 0.22.2 |
| pandas | 3.0.6 |
| huggingface-hub | 0.36.2 |
| 其他 | psutil 7.2.2、jsonlines 4.0.0、ujson 6.0.0、safetensors 0.8.0、sentencepiece 0.2.2 |

完整依赖快照：`D:\minimind\requirements-lock.txt`（`pip freeze` 结果）。

### 4.4 环境验证

```python
torch 2.14.1+cu130
cuda True
gpu NVIDIA GeForce RTX 5070 Ti Laptop GPU
cap (12, 0)
```

GPU 前向 + 反向 + AdamW 单步均通过；bf16 autocast 训练步通过；VRAM 占用 1.1GB（bs2/seq128 小样本）。

---

## 五、代码、数据、权重清单

### 5.1 源码（MiniMind master，2026-10 版本）

`D:\minimind\src\minimind-master`，核心结构：

```
model/
├── model_minimind.py     # 模型结构（MiniMindConfig / MiniMindForCausalLM，293 行）
├── model_lora.py         # 手写 LoRA（65 行）
├── tokenizer.json        # 仓库自带 tokenizer（451KB）
└── tokenizer_config.json # 含 chat_template（13KB）
dataset/
├── lm_dataset.py         # PretrainDataset / SFTDataset / DPODataset / RLAIF / AgentRL
└── *.jsonl               # 训练数据（见下）
trainer/
├── train_pretrain.py     # 预训练
├── train_full_sft.py     # 全参 SFT
├── train_tokenizer.py    # 训练 tokenizer（官方注明仅供学习，不建议重训）
├── train_lora.py         # LoRA 微调
├── train_dpo.py / train_ppo.py / train_grpo.py / train_agent.py / train_distillation.py
├── trainer_utils.py      # 模型初始化、checkpoint、LR 调度等
└── rollout_engine.py     # RL rollout 后端
eval_llm.py               # 推理/对话入口
scripts/                  # chat_api / web_demo / serve_openai_api / convert_model / eval_toolcall
```

**模型结构（minimind-3 Dense）**：hidden_size=768、8 层、8 注意力头、4 个 KV 头、head_dim=96、vocab=6400、intermediate_size=2432（`ceil(768*π/64)*64`）、RoPE theta=1e6、max_position=32768、tie_word_embeddings=True、Pre-Norm + RMSNorm、SwiGLU、GQA、SDPA（flash）注意力。参数量 **63.91M**。

**LoRA 结构**：对每个 `in_features == out_features` 的 Linear 注入 `B·A`（rank=16，A 高斯初始化、B 零初始化）；本模型命中 8 层 × (q_proj, o_proj) = 16 个模块，LoRA 参数 **393,216**（0.39M）。

### 5.2 数据（ModelScope `gongjy/minimind_dataset`）

| 文件 | 大小 | 行数 | 用途 |
|---|---|---|---|
| `pretrain_t2t_mini.jsonl` | 1,183.55 MB | 1,270,238 | 预训练（mini 快速复现） |
| `sft_t2t_mini.jsonl` | 1,658.63 MB | 905,718 | SFT（含 Tool Call 样本） |
| `lora_medical.jsonl` | 32.43 MB | 25,276 | 医药 LoRA |
| `lora_identity.jsonl` | 22.7 KB（仅探明大小） | — | 自我认知 LoRA（未下载数据） |
| `smoke_pretrain.jsonl` | 2.95 MB（自建，前 4096 行） | 4,096 | 冒烟测试 |
| `smoke_sft.jsonl` | 5.58 MB（自建，前 2048 行） | 2,048 | 冒烟测试 |

> 官方另外还提供 `pretrain_t2t.jsonl`（10GB）、`sft_t2t.jsonl`（14GB）、`rlaif.jsonl`（24MB）、`agent_rl.jsonl`（86MB）、`agent_rl_math.jsonl`（18MB），本会话未使用。
>
> 数据文件必须放在仓库的 `src/minimind-master/dataset/` 目录下：`datasets.load_dataset` 解析相对路径时以训练脚本 CWD（`trainer/`）为基准，最初放到 `D:\minimind\dataset` 时训练直接报 `FileNotFoundError`，移入仓库后恢复。

### 5.3 官方权重（ModelScope `gongjy/minimind-3-pytorch`）

| 文件 | 大小 | 说明 |
|---|---|---|
| `full_sft_zero_768.pth` | 131.3 MB | **Zero**：只用 mini 数据从零训练（本会话复刻目标 / 对照组） |
| `full_sft_768.pth` | 131.3 MB | 主线 SFT（14GB sft_t2t 数据训练，质量更好；作为 LoRA 的基座） |
| `pretrain_768.pth` | 131.3 MB | 官方预训练权重（本会话未用于训练） |
| `lora_medical_768.pth` | 778.6 KB | 官方医药 LoRA（本会话先试用、后复刻对照） |
| `lora_identity_768.pth` | 778.6 KB | 官方自我认知 LoRA（未训练/未深入使用） |
| 其他 | — | agent / grpo / ppo / dllm / sft_linear 等（未使用） |

官方另提供 transformers 格式 `gongjy/minimind-3`（`model.safetensors` 127.8MB + config + tokenizer + chat_template）。

**文件布局约定**：

- 官方权重备份：`D:\minimind\official\`（`full_sft_768.pth`、`full_sft_zero_768.pth`）
- 运行时权重目录：`src/minimind-master/out/`
  - `full_sft_768.pth` ← 本会话自训 SFT 模型（训练时每 1000 step 覆盖）
  - `full_sft_zero_768.pth` ← 官方 Zero（未改动）
  - `official_full_sft_768.pth` ← 官方主线基座副本（供 LoRA 训练/推理使用）
  - `pretrain_768.pth` ← 本会话自训预训练权重
  - `lora_medical_768.pth` / `lora_identity_768.pth` ← 官方 LoRA
  - `lora_medical_repro_768.pth` ← **本会话复刻的医药 LoRA**
- 断点续训检查点：`src/minimind-master/checkpoints/`（每 1000 step 保存；约 750MB/个）

---

## 六、阶段三：官方权重推理验证

### 6.1 目的

在不训练的前提下，先验证：环境、tokenizer、模型代码、GPU 推理链路是否完整可用，并建立「官方模型效果」基线。

### 6.2 只读避坑：embed 版 Python 的 sys.path

- embeddable Python 的 `._pth` 会**忽略 PYTHONPATH**，导致 `from model.model_minimind import ...` 报 `ModuleNotFoundError: No module named 'model'`。
- 解决：在 `python312._pth` 中追加仓库路径 `D:\minimind\src\minimind-master`。

### 6.3 推理入口

```powershell
cd D:\minimind\src\minimind-master
$env:PYTHONPATH='D:\minimind\src\minimind-master'
$env:TOKENIZERS_PARALLELISM='false'
"D:\minimind\python312\python.exe" eval_llm.py --load_from model --weight full_sft_zero --max_new_tokens 512
```

`eval_llm.py` 支持：`--weight`（权重前缀）、`--lora_weight`（叠加 LoRA）、`--open_thinking`（自适应思考）、`--historys`（多轮历史）、`--show_speed`（解码速度）等。
交互式对话双击 `D:\minimind\chat.cmd` 即可（内部使用 `--weight full_sft`，即自训模型）。

### 6.4 实测结果

- **官方 Zero**（`full_sft_zero_768.pth`）：8 条自动测试全部跑通，解码速度 8→73 tokens/s（首条含预热），回答结构完整但幻觉较多（64M 从零训练的正常水平）。
- **官方主线**（`full_sft_768.pth`）：质量明显更好，例如「用 Python 写斐波那契函数」给出正确递归实现，「解释机器学习」定义/分类/应用均正确。
- 说明：主线那次手动评测日志 `logs/eval_full_sft.log` 后来被夜间自动评测覆盖（现内容为自训模型评测），官方 Zero 评测日志保留在 `logs/eval_full_sft_zero.log`。

### 6.5 训练链路冒烟测试（训练前验证）

| 阶段 | 数据 | 结果 |
|---|---|---|
| pretrain | 前 4096 条，128 batch | exit 0，loss 8.07 → 7.21，耗时 105s |
| full SFT | 前 2048 条，128 batch | exit 0，loss 7.04 → 6.36，耗时 81s |

### 6.6 性能基准（为夜间训练选择参数）

BF16 autocast、AdamW、单卡实测（det=True）：

| batch × seq | 耗时/step | 吞吐 |
|---|---|---|
| 32 × 340（预训练配置） | 242–252 ms | 44.9k tok/s |
| 16 × 340 | 106 ms | 51.3k tok/s（最高） |
| 8 × 340 | 61 ms | 44.3k tok/s |
| 24 × 340 | 172 ms | 47.4k tok/s |
| 48 × 340 | 373 ms | 43.8k tok/s |
| 16 × 768（SFT 配置） | 289–295 ms | 42.6k tok/s |
| 8 × 768 | 126–134 ms | 45.9–48.7k tok/s |
| 24 × 768 | 450 ms | 41.0k tok/s |
| **32 × 768** | **2.6–3.4 s（异常慢路径）** | 7.2–9.5k tok/s ❌ |
| 64 × 340 | 630 ms | 34.5k tok/s |

- **重要发现**：`bs=32, seq=768` 会触发异常慢路径（约慢 10 倍），后续配置刻意避开。
- **DataLoader 实测**：`num_workers=0` 时数据 11.2 ms + 计算 227.6 ms/step；4/8 workers 时数据虽被掩盖但总耗时升至 245–249 ms/step，因此最终选择 `--num_workers 0`（Windows spawn 开销大于收益）。
- **全量数据加载耗时**：pretrain 2.9s（RSS 0.89GB）、SFT 3.6s（RSS 1.24GB），每条 SFT 样本处理约 1.1 ms。

---

## 七、阶段一：从零完整训练

### 7.1 训练方案（官方 mini 配方，1 epoch）

| 阶段 | 数据 | 超参（官方默认） |
|---|---|---|
| 预训练 | `pretrain_t2t_mini.jsonl`（1,270,238 条） | bs=32、accum=8（有效 batch 256）、seq=340、lr=5e-4、bf16、epochs=1 |
| SFT | `sft_t2t_mini.jsonl`（905,718 条） | bs=16、accum=1、seq=768、lr=1e-5、bf16、epochs=1 |

- 优化器：AdamW；LR 调度：余弦 + 0.1 下限（`get_lr`）；梯度裁剪 1.0
- 每 1000 step 保存：权重 131MB（`out/*.pth`）+ 续训检查点 750MB（`checkpoints/*_resume.pth`）
- `--from_resume 1` 支持断点续训（自动跳过已完成 step）

### 7.2 夜间无人值守设计

1. **训练封装**
   - `run_full_training.ps1`：按顺序执行 pretrain → SFT，支持 `-Resume` / `-SkipPretrain` / `-SkipSft`；
     通过 `Start-Process -RedirectStandardOutput/Error` 输出日志（UTF-8、无缓冲），避免 PowerShell 管道编码与 Python 缓冲问题。
   - `overnight.ps1`：调用训练脚本，**训练完成后自动评测**（自训模型 + 官方 Zero 各跑 8 条自动测试），并写状态文件 `logs/overnight_status.log`（含 `ALL DONE` 标记）。
2. **看门狗** `watchdog.ps1`
   - 每 60s 检查是否存在训练进程（CIM 命令行匹配 `train_pretrain|train_full_sft|eval_llm`）；
   - 连续 3 分钟无训练进程且未完成 → 自动 `overnight.ps1 -Resume` 从最近 checkpoint 续训，最多 4 次；
   - 检测到 `ALL DONE` 或超过 07:30 自行退出；每小时心跳日志。
   - 结果：**全程 0 次重启**，03:50:18 检测到 ALL DONE 后退出。
3. **防睡眠/防合盖中断**
   - 实测电源设置：AC 下 STANDBYIDLE=0（不休眠）、HIBERNATEIDLE=0、VIDEOIDLE=0；
   - **隐藏设置 LIDACTION（合盖操作）AC=0「不采取任何操作」**（用 `powercfg /qh` 查得；DC=1 睡眠）。
     即插电时合盖不影响训练，用户可直接合盖睡觉。
4. **日志方案迭代（重要踩坑）**
   - 第一版用 `Tee-Object` 写日志：Python 重定向时 stdout 是块缓冲（日志长期不刷新），且日志出现 UTF-16/UTF-8 混合乱码；
   - 21:15 重启训练，改为 `Start-Process` 直接重定向 + `PYTHONUNBUFFERED=1` + `PYTHONIOENCODING=utf-8`，日志实时、可读。
5. **夜间巡检**
   - 通过会话定时提醒（schedule）在 22:54 / 00:24 / 01:54 / 03:24 / 04:54 检查进度，另设 06:50 兜底；
   - 每次巡检汇报：阶段、step、loss、GPU、看门狗心跳、checkpoint 状态。

### 7.3 训练时间线（实测）

| 时间（10-28/29） | 事件 | 详情 |
|---|---|---|
| 21:15:15 | 训练启动（第二次、正式版） | pretrain 开始 |
| 21:23 | pretrain step 2000 | loss 3.77，checkpoint 正常 |
| 22:54 | 巡检 1/6 | step 26,800/39,695（67.5%），loss 2.14 |
| 23:41:18 | **pretrain 完成** | 总步数 39,695，耗时 **2h26m03s**，最终 loss **2.01** |
| 23:41:18 | SFT 自动开始 | 56,608 step |
| 00:24 | 巡检 2/6 | SFT 9,800/56,608，loss 1.86 |
| 01:54 | 巡检 3/6 | SFT 30,500/56,608，loss 1.53–1.75 |
| 03:24 | 巡检 4/6 | SFT 51,200/56,608（90.4%），loss 1.67 |
| 03:47:32 | **SFT 完成** | 耗时 **4h06m14s**，最终 loss **1.71** |
| 03:47:32 | 自动评测开始 | 依次评自训 `full_sft` 与官方 `full_sft_zero` |
| 03:48:42 | 自训模型评测完成 | `logs/eval_full_sft.log` |
| 03:49:34 | 官方 Zero 评测完成 → **ALL DONE** | `logs/eval_full_sft_zero.log` |
| 04:54 | 巡检 5/6（最终验收） | 核对权重、日志、GPU；写 `REPORT.md`；安排关机 |
| 04:56:20 | 执行 `shutdown /s /t 300` | 系统事件 1074 记录确认 |
| ≈05:01 | 机器断电 | 用户要求「7 点前全部完成则关机」已履行 |

**总训练时长：6 小时 32 分 17 秒**（不含 2 分钟评测）；官方 3090 参考值约 2.31h（1 epoch），本机约为其 2.8 倍。

### 7.4 训练稳定性

- 全程无异常、无 OOM、无进程崩溃；
- GPU 温度稳定 76–78°C，功耗 132–139W，利用率 98–99%；
- 每 1000 step 存盘成功（恢复点 750MB）；
- 看门狗 0 次介入；
- 训练中途用户要求「7 点前完成则关机」，最终 03:49 完成、04:56 发起关机，逻辑闭环。

---

## 八、训练结果与模型质量评估

### 8.1 结果数据

| 指标 | 预训练 | SFT |
|---|---|---|
| 数据量 | 1,270,238 条（1.18GB） | 905,718 条（1.66GB） |
| 步数 | 39,695 | 56,608 |
| 耗时 | 2h26m03s | 4h06m14s |
| 初始 loss | ~7.5 | ~2.0 |
| **最终 loss** | **2.01** | **1.71** |
| 产物 | `out/pretrain_768.pth` | `out/full_sft_768.pth` |

### 8.2 与官方 Zero 的对比（同一批 8 条 prompt）

| 维度 | 自训模型 | 官方 Zero |
|---|---|---|
| 中文流畅度 | 正常 | 正常 |
| 「什么是机器学习」 | ✅ 定义/分类/应用基本正确 | ✅ 类似 |
| 「Python 写斐波那契」 | ❌ 代码有语法错误、重复 | ❌ 同样错误 |
| 「介绍你自己」 | ❌ 说成「阿里云开发」（身份记错） | ✅ 「由中国的个人开发者独立开发」 |
| 「1+1 等于几」 | ⚠️ 首句对，随后发散 | ❌ 答成 3 和 4 的分数运算 |
| 重复/退化 | 偶发（如「ATP和ATP和ATP…」） | 偶发 |
| `</think>` 标签泄漏 | 有 | 有 |

**结论：自训模型与官方 Zero 处于同一量级**，官方 Zero 在身份类记忆上更准，双方都存在 64M 模型典型的事实错误与重复。

### 8.3 自定义样例（6 条，`logs/demo_ours.log`）

- 「什么是机器学习？」→ 定义准确，列出监督/无监督/强化学习、数据预处理/特征工程/评估/部署，结尾「应用广泛」
- 「用一句话描述秋天」→ 通顺、有画面感
- 「推荐一道中国的家常菜」→ 给番茄炒蛋 + 材料 + 步骤，基本可用
- 「1+1 等于几？」→ 首句正确，后续冗长发散
- 「介绍一下你自己」→ 身份记错（61 天前 SFT 数据里是个人开发者）
- 「如果明天下雨出门注意什么」→ 有合理建议（雨具、天气、安全），但夹带无关内容

### 8.4 与官方 Zero 的差距原因分析

1. **预训练序列长度**：本次用代码默认 `max_seq_len=340`，而 README 对 `pretrain_t2t_mini` 推荐 **≈768**。用 340 时每条语料截断到 340 token，预训练见到的 token 总量约少一半。
2. **epoch 数**：代码默认 `epochs=2`，本次按官方文档快速复现配方只跑 **1 epoch**（官方 Zero 权重可能用了更多训练量/不同数据版本）。
3. **采样随机性**：8 条 prompt 每次随机种子不同，64M 模型输出方差大，单次对比有偶然性。
4. **模型上限**：63.91M 参数 + 小型语料，事实知识与推理能力本身有限。

### 8.5 提升建议（已验证可行、脚本现成）

| 方案 | 预计耗时 | 说明 |
|---|---|---|
| 预训练 `--max_seq_len 768` | ≈5.5 h | 预训练见到的 token 约翻倍，最推荐 |
| `--epochs 2` | ≈6.5 h | 训练量翻倍，效果通常明显提升 |
| micro-batch 调优 | 省 ≈0.6 h | pretrain bs16+accum16、SFT bs8+accum2（有效 batch 不变） |
| 直接用官方主线权重 | — | `official/full_sft_768.pth`，效果明显更好，适合实用 |

---

## 九、医药 LoRA 复刻

### 9.1 官方医药 LoRA 试用（推理）

- 下载官方 `lora_medical_768.pth`（778.6 KB）与 `lora_identity_768.pth`；
- 把官方主线基座复制为 `out/official_full_sft_768.pth`（避免覆盖自训模型）；
- 编写 `D:\minimind\tools\demo_lora.py`：加载基座 → `apply_lora(rank=16)` → `load_lora(...)` → 7 条 prompt（6 医疗 + 1 通用对照）；
- 对比「裸基座」与「基座 + 官方 LoRA」（`logs/demo_med_base.log` vs `demo_med_lora.log`）。
  - 官方 LoRA 输出更医疗化（给检查建议、就医提醒），但仍有事实错误（如「高盐饮食可以帮助血管扩张」）。

### 9.2 复刻训练（核心）

**训练配置（官方默认超参）**

```powershell
cd D:\minimind\src\minimind-master\trainer
python train_lora.py `
  --from_weight official_full_sft `   # 基座 = 官方主线 full_sft（LoRA 依赖基座）
  --lora_name lora_medical_repro `    # 避免覆盖官方权重
  --epochs 10 --batch_size 32 --lora_rank 16 --max_seq_len 340 `
  --learning_rate 1e-4 --num_workers 0 --log_interval 10
```

**训练结果**

| 项 | 值 |
|---|---|
| 数据 | `lora_medical.jsonl`，25,276 条医疗对话（32.43MB） |
| 结构 | rank 16，命中 16 个方阵 Linear（q_proj/o_proj × 8 层），LoRA 参数 **393,216** |
| 步数 | 790 step/epoch × 10 = **7,900 step** |
| 耗时 | **24 分钟**（17:50:45 → 18:14:50，实测 5.0 step/s） |
| 最终 loss | **1.2564** |
| 各 epoch 末步 loss | 1.3219 / 1.3600 / 1.4281 / 1.2320 / 1.4763 / 1.3590 / 1.2741 / 1.2571 / 1.3627 / 1.2564 |
| 产物 | `out/lora_medical_repro_768.pth`（779.2 KB） |

**训练日志**：`logs/lora_train.log`（86.5KB，逐 10 step 记录 loss/lr）。

### 9.3 三方客观对比（留出集 loss，越低越好）

留出集：医疗数据最后 200 条（未参与训练）；通用数据 `smoke_sft.jsonl` 前 150 条。

| 模型 | 医疗留出 loss | 通用留出 loss |
|---|---|---|
| 裸基座（无 LoRA） | 1.5553 | **0.8672** |
| **复刻 LoRA** | **1.3109**（-15.7%） | 1.2935 |
| 官方 LoRA | **1.2263**（-21.2%） | 1.5823 |

**解读**：

1. 复刻 LoRA **确实学到了医疗领域适配**（医疗 loss 下降 15.7%），达到官方提升幅度（21.2%）的约 3/4；
2. 领域适配都会损伤通用能力：复刻版通用 loss 1.29（损失较小），官方版 1.58（更"偏科"）；
3. **权重层面**：复刻 LoRA 与官方 LoRA 的余弦相似度 ≈ 0（A 权重均值 -0.0024、B 权重 -0.0084；相对误差 >1），说明两次训练的数值轨迹完全不同（GPU/bf16 kernel 差异在 7,900 步训练中被放大，LoRA 又从零初始化），属于**效果级复刻而非权重级复刻**。

### 9.4 对话效果对比

- **裸基座**：泛泛而谈、部分跑题（如把发烧降温答成空调与空气净化器）。
- **官方 LoRA**：更常说「建议就医/做检查」，医学名词密度更高，但 64M 能力有限，仍有明显错误。
- **复刻 LoRA**：风格接近官方 LoRA（列表化、就医提醒、检查建议），同样受模型能力限制（如把"颈椎病"编出不存在的英文缩写）。

日志：`logs/demo_med_repro.log`（复刻）、`logs/demo_med_lora2.log`（官方）、`logs/demo_med_base.log`（裸基座）。

### 9.5 使用方式

```powershell
cd D:\minimind\src\minimind-master
$env:PYTHONPATH='D:\minimind\src\minimind-master'
"D:\minimind\python312\python.exe" eval_llm.py --load_from model --weight official_full_sft --lora_weight lora_medical_repro
```

---

## 十、产物与目录结构

### 10.1 目录总览

```
D:\minimind\
├─ python312\                       便携 Python 3.12.10 + 全部依赖（约 3GB）
├─ src\minimind-master\             MiniMind 官方代码（master，2026-10）
│  ├─ model\                        模型结构（model_minimind.py）+ 自带 tokenizer
│  ├─ dataset\                      训练数据（pretrain/sft/lora_medical/smoke）
│  ├─ trainer\                      训练脚本（pretrain/SFT/LoRA/DPO/PPO/GRPO/Agent/蒸馏）
│  ├─ scripts\                      chat_api / web_demo / convert_model / serve_openai_api
│  ├─ eval_llm.py                   推理/对话入口
│  ├─ out\                          运行时权重目录（见下表）
│  └─ checkpoints\                  断点续训检查点（约 2GB）
├─ official\                        官方权重备份（勿删）
│  ├─ full_sft_768.pth              官方主线 SFT（131.3MB）
│  └─ full_sft_zero_768.pth         官方 Zero（131.3MB）
├─ logs\                            全部训练/评测/样例日志
├─ tools\                           Python 安装包、get-pip、基准/评测脚本
├─ requirements-lock.txt            完整依赖快照
├─ README.md                        复刻说明（环境/数据/训练/评测/注意事项）
├─ REPORT.md                        完整训练报告（含质量分析与建议）
├─ CONVERSATION_SUMMARY.md          本文档
├─ run_full_training.ps1 / .cmd     一键完整训练（pretrain + SFT）
├─ overnight.ps1                    无人值守训练 + 自动评测
├─ watchdog.ps1                     训练看门狗（崩溃自动续训）
├─ chat.cmd                         双击启动交互式对话
└─ demo_chat.py                     6 条固定 prompt 的样例生成脚本
```

### 10.2 权重清单（`src/minimind-master/out/`，当前实测）

| 文件 | 大小 | 说明 |
|---|---|---|
| `pretrain_768.pth` | 131.31 MB | 本会话自训预训练权重（2026-10-28 23:41） |
| `full_sft_768.pth` | 131.31 MB | **本会话自训 SFT 最终模型**（2026-10-29 03:47） |
| `official_full_sft_768.pth` | 131.31 MB | 官方主线基座副本（LoRA 基座，2026-10-28 18:17 复制） |
| `full_sft_zero_768.pth` | 131.31 MB | 官方 Zero（未改动） |
| `lora_medical_768.pth` | 0.76 MB | 官方医药 LoRA |
| `lora_identity_768.pth` | 0.76 MB | 官方自我认知 LoRA |
| `lora_medical_repro_768.pth` | 0.76 MB | **本会话复刻的医药 LoRA**（2026-10-29 18:14） |

### 10.3 日志清单（`D:\minimind\logs\`，当前实测）

| 文件 | 大小 | 内容 |
|---|---|---|
| `pretrain.log` | 45.0 KB | 预训练逐 100 step 日志（含最终 loss 2.01） |
| `sft.log` | 64.5 KB | SFT 逐 100 step 日志（含最终 loss 1.71） |
| `stages.log` | 0.1 KB | 阶段起止时间（开始/完成 pretrain、sft） |
| `overnight_status.log` | 0.4 KB | 无人值守流程状态（含 ALL DONE） |
| `watchdog.log` | 0.8 KB | 看门狗心跳与重启记录（0 次重启） |
| `eval_full_sft.log` | 12.5 KB | 自训模型自动评测（8 条 prompt） |
| `eval_full_sft_zero.log` | 12.5 KB | 官方 Zero 自动评测（同 8 条 prompt） |
| `demo_ours.log` / `demo_official_zero.log` | 5.5 / 4.5 KB | 6 条自定义 prompt 对比样例 |
| `lora_train.log` / `.err.log` | 86.5 / 0.1 KB | LoRA 训练日志（7,900 step） |
| `demo_med_base.log` | 7.2 KB | 裸基座医疗问答样例 |
| `demo_med_lora.log` / `demo_med_lora2.log` | 7.1 / 7.0 KB | 官方 LoRA 医疗问答样例 |
| `demo_med_repro.log` | 7.0 KB | 复刻 LoRA 医疗问答样例 |

### 10.4 辅助工具脚本（`D:\minimind\tools\`）

| 脚本 | 用途 |
|---|---|
| `demo_lora.py` | 基座 ± LoRA 的 7 条医疗 prompt 样例生成 |
| `demo_chat.py`（根目录） | 自训模型 6 条通用 prompt 样例生成 |
| `cmp_lora.py` | 官方 vs 复刻 LoRA 权重余弦相似度对比 |
| `eval_lora_loss.py` | 留出集 loss 评测（裸基座 / 官方 LoRA / 复刻 LoRA） |
| `sanity_check.py` | 开机后模型加载 + 对话自检 |
| `bench_gpu.py` / `bench_gpu2.py` / `bench_sft.py` / `bench2.py` / `bench_pipeline.py` | 各种 batch/seq 吞吐基准 |
| `preflight_data.py` / `count_lines.py` | 全量数据加载预检与行数统计 |
| `gpu_sanity.py` | GPU 前向/反向/AMP 冒烟 |
| `python-3.12.10-amd64.exe` / `python-3.12.10-embed-amd64.zip` / `get-pip.py` | 环境安装物料 |

### 10.5 磁盘现状（2026-11-01）

- D: 剩余 **336.2 GB**
- `checkpoints/` 约占 2.16 GB（pretrain resume 750MB + full_sft resume 750MB + lora resume 267MB + 三份权重副本），确认不再续训后可删。
- `out/` 权重约 0.66 GB（5×131MB + 3×0.76MB）。

---

## 十一、常用命令手册

### 11.1 环境（已配置好，通常不需要重装）

```powershell
# 解释器
D:\minimind\python312\python.exe
# 环境变量（脚本内已设置，手动运行时需要）
$env:PYTHONPATH='D:\minimind\src\minimind-master'
$env:TOKENIZERS_PARALLELISM='false'
$env:PYTHONUNBUFFERED='1'
$env:PYTHONIOENCODING='utf-8'
```

### 11.2 推理 / 对话

```powershell
cd D:\minimind\src\minimind-master

# 自训 Zero 模型（本会话训练产物）
D:\minimind\python312\python.exe eval_llm.py --load_from model --weight full_sft

# 官方 Zero（对照组）
D:\minimind\python312\python.exe eval_llm.py --load_from model --weight full_sft_zero

# 官方主线基座 + 官方医药 LoRA
D:\minimind\python312\python.exe eval_llm.py --load_from model --weight official_full_sft --lora_weight lora_medical

# 官方主线基座 + 复刻医药 LoRA
D:\minimind\python312\python.exe eval_llm.py --load_from model --weight official_full_sft --lora_weight lora_medical_repro

# 交互式（双击即可）
D:\minimind\chat.cmd
```

### 11.3 训练

```powershell
# 一键完整训练（pretrain + SFT，约 7 小时）
D:\minimind\run_full_training.ps1
D:\minimind\run_full_training.ps1 -Resume        # 断点续训
D:\minimind\run_full_training.ps1 -SkipPretrain  # 只跑 SFT

# 无人值守（训练 + 自动评测 + 看门狗之外的状态记录）
pwsh -File D:\minimind\overnight.ps1
pwsh -File D:\minimind\overnight.ps1 -Resume

# 单独跑某阶段（在 trainer 目录下）
cd D:\minimind\src\minimind-master\trainer
D:\minimind\python312\python.exe train_pretrain.py --epochs 1 --num_workers 0
D:\minimind\python312\python.exe train_full_sft.py --epochs 1 --from_weight pretrain --num_workers 0
D:\minimind\python312\python.exe train_lora.py --from_weight official_full_sft --lora_name lora_medical_repro --epochs 10 --num_workers 0
```

### 11.4 评测与样例生成

```powershell
# LoRA 留出集 loss 对比
D:\minimind\python312\python.exe D:\minimind\tools\eval_lora_loss.py

# LoRA 权重相似度
D:\minimind\python312\python.exe D:\minimind\tools\cmp_lora.py

# 医疗问答样例（基座 vs 官方/复刻 LoRA）
D:\minimind\python312\python.exe D:\minimind\tools\demo_lora.py official_full_sft lora_medical_repro

# 通用样例
D:\minimind\python312\python.exe D:\minimind\demo_chat.py full_sft
```

### 11.5 监控

```powershell
nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu --format=csv,noheader
Get-Content D:\minimind\logs\sft.log -Encoding utf8 -Tail 5
Get-Content D:\minimind\logs\stages.log -Encoding utf8 -Tail 5
Get-Content D:\minimind\logs\watchdog.log -Encoding utf8 -Tail 5
```

---

## 十二、踩坑与解决方案

| # | 问题 | 现象 | 解决方案 |
|---|---|---|---|
| 1 | GitHub 直连被阻断 | curl 返回 000，DNS 可解析但 TCP 失败 | 用 `gh-proxy.com` 代理下载 tarball；数据/权重走 ModelScope 直链 |
| 2 | 官方 Python 3.12 安装器不完整 | 缺 `python312.dll`，`0xC0000135`，venv 失败 | 改用 embeddable zip；破损安装已卸载回滚 |
| 3 | embeddable Python 忽略 PYTHONPATH | `ModuleNotFoundError: No module named 'model'` | 把仓库路径写入 `python312._pth` |
| 4 | numpy 与 pyarrow 冲突 | `pyarrow requires NumPy 2.0 or newer, found 1.26.4` | 放弃官方 pin，升级 numpy 到 2.5.4 |
| 5 | 数据路径解析 | `load_dataset` 在 `trainer/` 下解析相对路径，报 `FileNotFoundError` | 数据移入仓库 `src/minimind-master/dataset/` |
| 6 | SFT 权重路径与 `--save_dir` 无关 | 传 `--save_dir` 仍去 `../out` 找 `pretrain_768.pth` | 把预训练权重放 `../out/`，或复制到该目录 |
| 7 | Windows DataLoader 多进程开销大 | 4/8 workers 反而比 0 慢 | 训练统一 `--num_workers 0` |
| 8 | `bs=32, seq=768` 异常慢 | 2.6–3.4 s/step（正常约 0.29s） | 避免该组合；SFT 用 bs16，或 bs8 更快 |
| 9 | 重定向后 Python 输出不刷新 | 训练日志长期停留在初始几行 | `PYTHONUNBUFFERED=1` |
| 10 | Tee-Object 日志编码混合 | 日志出现 UTF-16 乱码、难以阅读 | 改用 `Start-Process -RedirectStandardOutput/Error` 直接写文件 |
| 11 | 夜间训练怕系统睡眠/合盖 | 合盖可能中断 7 小时训练 | 用 `powercfg /qh` 查隐藏 LIDACTION，确认 AC=0；睡眠/休眠超时均为 0 |
| 12 | 训练中断无保护 | 崩溃会丢进度 | 每 1000 step 存盘 + 独立 `watchdog.ps1` 自动 `-Resume`（本次 0 次触发） |
| 13 | 长时间任务需要自主推进 | 用户睡觉、7 点前不回复 | 会话定时提醒巡检 + 训练完成后自动评测 + 完成后按用户要求关机 |
| 14 | LoRA 训练覆盖官方权重风险 | 默认 `lora_name=lora_medical` 会覆盖官方文件 | 用 `--lora_name lora_medical_repro` 区分；基座另存 `official_full_sft_768.pth` |
| 15 | 评测日志被覆盖 | 自动评测覆盖了此前手动评测的 `eval_full_sft.log` | 关键日志另存/先复制；官方 Zero 日志未受影响 |

---

## 十三、完整时间线

| 日期时间 | 事件 |
|---|---|
| **2026-10-28 18:03** | 用户提出「复刻 MINIMIND，不租服务器」；开始硬件/网络/环境侦察 |
| 18:05–18:10 | 确认 GPU（5070 Ti Laptop 12GB/sm_120）、Python 3.14 无 torch、GitHub 不通、pypi/ModelScope 可用 |
| 18:10 | 经用户批准获得 danger-full-access（网络）；gh-proxy 下载 MiniMind master tarball（10.27MB） |
| 18:10 | 开始并行下载数据集 + 安装 Python 3.12 官方安装器（失败，缺 DLL） |
| 18:13 | 用户选择：先完成「阶段三」，晚上再完成「阶段一」完整训练 |
| 18:13–18:20 | 改用便携 Python 3.12.10 embeddable + pip；安装 torch 2.14.1+cu130 等 |
| 18:20–18:40 | numpy/pyarrow 冲突修复；下载 pretrain/sft 数据集（1.18GB + 1.66GB）；下载官方 Zero/主线权重；官方权重推理验证 |
| 18:40–19:00 | 冒烟测试 pretrain/SFT、GPU 基准测试、脚本与 README 编写、发布阶段三总结 |
| **21:12** | 用户：「开始吧！」→ 启动完整训练 |
| 21:15:15 | 正式训练开始（此前 21:13 启动的版本因日志缓冲/编码问题被终止并修复重启） |
| 21:23 | 用户：「我去睡觉了，明天 7 点之前你将不会得到任何的回复了，一切由你自行解决」 |
| 21:23–21:30 | 部署看门狗、调整巡检、验证电源设置（合盖不休眠） |
| 22:5x | 用户补充：「如果 7 点前全部完成了的话你可以帮我关机」→ 写入巡检/兜底提醒 |
| 22:54 | 巡检 1：pretrain 26,800/39,695 |
| 23:41:18 | **预训练完成**，loss 2.01，耗时 2h26m；SFT 开始 |
| **2026-10-29 00:24** | 巡检 2：SFT 9,800/56,608 |
| 01:54 | 巡检 3：SFT 30,500/56,608 |
| 03:24 | 巡检 4：SFT 51,200/56,608 |
| 03:47:32 | **SFT 完成**，loss 1.71，耗时 4h06m；自动评测开始 |
| 03:49:34 | 双模型评测完成 → **ALL DONE** |
| 04:56 | 最终验收、写 `REPORT.md`、删除巡检提醒、安排关机 |
| ≈05:01 | 机器关机（系统事件记录确认） |
| 11:46–11:49 | 用户回来，确认完整复刻完成；开机后模型加载/对话复测正常 |
| 17:47 | 用户：「可以跑一遍 minimind 官方的医药 lora」 |
| 17:48 | 试用官方医药 LoRA（下载权重、与裸基座对比） |
| 17:49 | 用户澄清：「不是直接用哦，是复刻这个 lora」 |
| 17:50:45 | 启动医药 LoRA 复刻训练（官方数据 + 默认超参） |
| 18:14:50 | LoRA 训练完成（24 分钟，final loss 1.2564）；三方评测开始 |
| 18:20 | 汇报复刻结果（留出 loss、权重相似度、样例对比） |
| 18:2x | 用户：「先这样就行了」→ 收尾确认、产物清单 |
| **2026-11-01 17:01** | 用户要求整理详细对话总结 → 生成本文档 |

---

## 十四、经验总结与后续建议

### 14.1 可复用的经验

1. **小显存也能从零训 LLM**：64M 模型用 bs32/seq340 在 12GB 笔记本上训练只需 ~8.5GB 显存，2.5 小时跑完 127 万条语料的 1 epoch。
2. **吞吐基准要先做**：batch/seq 组合存在异常慢路径（本机 bs32×seq768），盲目用官方默认在别的硬件上可能踩坑；正式训练前用 20 步计时 + GPU 采样确认配置。
3. **Windows 上稳定训练的三件事**：`num_workers=0`、`PYTHONUNBUFFERED=1`、`Start-Process` 重定向日志；再配合 `pf/1000 step` 存盘与看门狗。
4. **无人值守要有兜底**：定时巡检提醒 + 独立看门狗 + 自动评测 + 状态文件（`ALL DONE`），任何一层失效仍有下一层。
5. **关机/电源注意**：笔记本合盖动作（LIDACTION）默认可能是睡眠；用 `powercfg /qh` 确认 AC 行为，插电时设为「不采取任何操作」最稳妥。
6. **复刻要区分「权重级」与「效果级」**：LoRA 训练在数值上对 GPU/kernel 差异高度敏感，权重余弦相似度可能接近 0；用留出集 loss 与行为评测来判断是否复刻成功。

### 14.2 后续可做（脚本/数据基本现成）

1. **质量提升**：重跑 pretrain `--max_seq_len 768`（≈5.5h）或 `--epochs 2`（≈6.5h）。
2. **继续 RL 流程**：仓库自带 DPO/PPO/GRPO/Agent RL 脚本；需补下载 `rlaif.jsonl`（24MB）、`agent_rl.jsonl`（86MB）、`agent_rl_math.jsonl`（18MB）。
3. **LoRA 变体**：官方还有 `lora_identity`（自我认知）与 `lora_exam`（考试对齐），可同样复刻；医药 LoRA 可试 20 epochs / rank 32（每次约 25 分钟）以逼近官方医疗 loss。
4. **模型合并导出**：`scripts/convert_model.py` 的 `convert_merge_base_lora` 可把【基座 + LoRA】合并导出为独立权重，便于 llama.cpp/ollama 部署。
5. **部署服务**：`scripts/serve_openai_api.py`（OpenAI 兼容 API）、`scripts/web_demo.py`（Streamlit）、`scripts/chat_api.py`。
6. **清理**：确认不再续训后可删 `checkpoints/`（约 2.16GB）。

### 14.3 已知限制

- 自训 Zero 模型与官方 Zero 同量级，但事实准确率、身份记忆仍弱；不适合作为实用问答模型。
- 医药 LoRA 复刻达到官方效果的约 3/4（医疗 loss 1.311 vs 1.226），且权重不可比。
- 本次训练使用 1 epoch + seq 340（未采用 README 对 mini 数据推荐的 768），是质量差距的主要原因之一。
- 评测样本量小（8 条自动测试 + 6 条自定义 + 7 条医疗），结论仅供方向性参考。

---

## 附录：关键数值表与对话样例

### A. 关键数值速查

| 指标 | 值 |
|---|---|
| GPU | RTX 5070 Ti Laptop，12227MiB，sm_120，驱动 621.01 |
| Python / torch | 3.12.10（便携）/ 2.14.1+cu130 |
| 模型参数量 | 63.91M（hidden 768，8 层，8 头，4 KV 头，vocab 6400） |
| 预训练数据 | 1,270,238 条 / 1.184GB / 39,695 step / 耗时 2h26m / loss 7.52→2.01 |
| SFT 数据 | 905,718 条 / 1.659GB / 56,608 step / 耗时 4h06m / loss ~2.0→1.71 |
| 总训练 | 6h32m17s；GPU 98–99%、132–139W、76–78°C、8.0–8.5GB |
| 评测 | 8 条 prompt × 2 模型，2m02s，03:49:34 ALL DONE |
| 关机 | 04:56:20 `shutdown /s /t 300`，约 05:01 断电 |
| 推理速度 | 60–74 tokens/s（half，含 KV cache） |
| LoRA | 25,276 条 / 7,900 step / 10 epochs / 24min / final loss 1.2564 / 393,216 参数 |
| LoRA 留出 loss | 医疗：base 1.5553 / repro 1.3109 / official 1.2263；通用：base 0.8672 / repro 1.2935 / official 1.5823 |
| LoRA 权重相似度 | A 层 cos -0.0024，B 层 cos -0.0084 |

### B. 对话样例摘录

**自训 Zero（`logs/demo_ours.log`）**

> 💬 什么是机器学习？
> 🤖 机器学习是一种人工智能技术，它让计算机系统能够从数据中学习并自动改进任务的能力。这种技术在许多领域都有广泛的应用，例如计算机视觉、自然语言处理、决策制定、自动驾驶、医疗诊断等……（定义与分类基本正确，结构完整）

> 💬 1+1 等于几？
> 🤖 1+1等于2。解释：这是一个比较简单的数学问题，通常与"1"在数学中表示的是"1"或"1"……（首句正确，随后发散）

**官方 Zero（`logs/demo_official_zero.log`）**

> 💬 你好，请用一句话介绍你自己。
> 🤖 你好！我是由中国的个人开发者独立开发的智能助手minimind，有关模型和产品的详细内容请参考官方文档。（身份正确；随后出现 `</think>` 标签泄漏与重复）

> 💬 1+1 等于几？
> 🤖 要解决这个问题，我们首先需要知道1+1等于多少。题目中给出的分数和分数分别为3和4……（明显错误）

**复刻医药 LoRA（`logs/demo_med_repro.log`）**

> 💬 糖尿病患者可以吃水果吗？
> 🤖 糖尿病患者在饮食方面可能有所不同，但以下是一些常见的健康饮食建议：1. 水果和蔬菜……2. 全谷类食品……3. 低糖饮食……（医疗风格明显，结构完整，但仍受 64M 能力限制）

**官方医药 LoRA（`logs/demo_med_lora2.log`）**

> 💬 高血压患者在饮食上要注意什么？
> 🤖 高血压患者在饮食上需要特别注意以下几点：1. 饮食应以低盐、低脂肪、高纤维为主……（医疗风格，但存在"高盐饮食可以帮助血管扩张"这类事实错误）

### C. 重要文件路径速查

| 用途 | 路径 |
|---|---|
| 复刻总报告 | `D:\minimind\REPORT.md` |
| 复刻说明 | `D:\minimind\README.md` |
| 本文档 | `D:\minimind\CONVERSATION_SUMMARY.md` |
| 自训 Zero 模型 | `src\minimind-master\out\full_sft_768.pth` |
| 自训预训练权重 | `src\minimind-master\out\pretrain_768.pth` |
| 复刻医药 LoRA | `src\minimind-master\out\lora_medical_repro_768.pth` |
| 官方权重备份 | `D:\minimind\official\` |
| 训练日志 | `D:\minimind\logs\{pretrain,sft}.log`、`stages.log`、`watchdog.log` |
| 评测日志 | `D:\minimind\logs\eval_full_sft*.log`、`demo_*.log` |
| 依赖快照 | `D:\minimind\requirements-lock.txt` |
| 一键训练 | `D:\minimind\run_full_training.ps1` |
| 交互式聊天 | `D:\minimind\chat.cmd` |

---

> 文档结束。所有数据均来自本会话实测与 `D:\minimind` 下的真实产物/日志（2026-11-01 17:02 复核）。
