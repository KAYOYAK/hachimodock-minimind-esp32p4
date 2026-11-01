# 训练证据（Training Evidence）

> 本页所有数字与日志来自 `D:\minimind`（2026-10-28 ~ 2026-11-01 实测产物）。完整日志约 200 MB 未入库，这里保留**可复核的 excerpt、CSV 与曲线**。

## 1. 环境

| 项 | 值 |
|---|---|
| GPU | NVIDIA RTX 5070 Ti Laptop，12,227 MiB，sm_120 |
| 驱动 / CUDA | 621.01 / CUDA UMD 13.5 |
| Python | 3.12.10（便携 embeddable） |
| torch / transformers | 2.14.1+cu130 / 4.57.6 |
| 数据来源 | ModelScope `gongjy/minimind_dataset` |
| 权重基线 | ModelScope `gongjy/minimind-3-pytorch`（仅用于阶段三对拍，训练从零开始） |
| 训练方式 | 本地 RTX 5070 Ti Laptop 12GB，**不租服务器** |

## 2. 训练过程（stages.log 原始记录）

```
[2026-10-28 21:15:15] 开始 pretrain
[2026-10-28 23:41:18] 完成 pretrain      # 2h26m03s
[2026-10-28 23:41:18] 开始 sft
[2026-10-29 03:47:32] 完成 sft           # 4h06m14s
```

日志头（模型规格）：

```
Model Params: 63.91M
Trainable Params: 63.912M
```

| 阶段 | 数据 | 超参 | step | 耗时 | 最终 loss |
|---|---|---|---|---|---|
| pretrain | 1,270,238 条 / 1.184 GB | bs32 × accum8（有效 256）、seq340、lr 5e-4、bf16 | 39,695 | 2h26m | **2.0093** |
| sft | 905,718 条 / 1.659 GB | bs16 × accum1、seq768、lr 1e-5、bf16 | 56,608 | 4h06m | **1.7094** |
| 合计 | — | AdamW + cosine(0.1 floor)、grad clip 1.0 | — | **6h32m** | — |

## 3. Loss 曲线（日志逐行解析）

### 3.1 Pretrain（39,695 step，final 2.01）

![pretrain loss](assets/pretrain_loss.svg)

### 3.2 SFT（56,608 step，final 1.71）

![sft loss](assets/sft_loss.svg)

### 3.3 医药 LoRA 复刻（7,900 step，final 1.2564）

![lora loss](assets/lora_loss.svg)

> 原始逐 step 数据：`docs/assets/pretrain_loss.csv`、`sft_loss.csv`、`lora_loss.csv`。

## 4. 日志摘录（可 grep 复核）

**pretrain 首尾：**
```
Epoch:[1/1](100/39695), loss: 7.5222, ... lr: 0.00049999, epoch_time: 168.0min
...
Epoch:[1/1](39600/39695), loss: 2.1907, ... lr: 0.00005001, epoch_time: 0.0min
Epoch:[1/1](39695/39695), loss: 2.0093, ... lr: 0.00005000, epoch_time: 0.0min
```

**sft 首尾：**
```
Epoch:[1/1](100/56608), loss: 2.2259, ... lr: 0.00001000, epoch_time: 263.0min
...
Epoch:[1/1](56600/56608), loss: 1.8370, ... lr: 0.00000100, epoch_time: 0.0min
Epoch:[1/1](56608/56608), loss: 1.7094, ... lr: 0.00000100, epoch_time: 0.0min
```

**医药 LoRA（10 epochs）：**
```
Epoch:[10/10](780/790), loss: 1.3875, ...
Epoch:[10/10](790/790), loss: 1.2564, ...
```

## 5. 权重与 SHA256（D:\minimind\src\minimind-master\out）

| 文件 | 大小 | SHA256 |
|---|---|---|
| `pretrain_768.pth` | 137,684,407 B | `6629e6e87c5ab4f5a0458f7f609ebf7c1efd16c59cc8f721c9b996ce531d9a11` |
| `full_sft_768.pth`（自训 SFT） | 137,684,407 B | `308ab7ea3a7909e2c6e55f48b0af7d5554da91d00050ffce557b6f2f4f099ed8` |
| `full_sft_zero_768.pth` | 137,684,892 B | `7712add52ebd96be7df8dc69418a2638663f0621d8305196788483ac5e716b2a` |
| `lora_medical_repro_768.pth`（复刻 LoRA） | 797,949 B | `2dfae5f9f339df55b9a921911da3545098a952f9981aa90bae7857604143c4aa` |
| `lora_medical_768.pth`（官方 LoRA） | 797,242 B | `7a33b4c124f2593ebd37f64cf69a92dd4f62feddce02f8278575bb4d5a3d5d36` |
| `lora_identity_768.pth` | 797,278 B | `fdb10cf5f3215dbc4c993866267e30ad377ae321b2122d17b3f4fc0dfd8c5cb5` |
| `official_full_sft_768.pth`（官方基线） | 137,683,346 B | `5b8c49f6c9d965092e651cafeeaeb8705558632b3fd4ac8ab319cbc5a3cbc4a0` |

> 部署用的 q3e4 `model.kmcu` 由上述自训 SFT 权重经 HF 格式转换后量化得到；模型下载见 [Release v0.1.0](https://github.com/KAYOYAK/hachimodock-minimind-esp32p4/releases/tag/v0.1.0)。

## 6. 模型能力样例

**自训 SFT 模型（PC 端，71.95 tok/s）：**
```
用户：如果明天下雨，出门要注意什么？
模型：如果明天下雨，出门是为了避免可能的雨水污染……（列出 4 点建议，存在少量事实/逻辑瑕疵，符合 64M + 1 epoch 的预期）
```

**医药 LoRA 复刻（demo_med_repro）：**
```
6. 模型应用：将训练好的模型应用于新的数据，生成预测结果。
7. 模型应用：将模型应用于新的数据，生成新的预测结果。
机器学习的应用非常广泛……在医疗领域，机器学习可以帮助医生预测疾病……
```

**板端（q3e4，ESP32-P4）实测：**
```
[ai] 你好！我是一个AI助手，我是一个虚拟
```

## 7. 如何复核

```powershell
# 时间线
Get-Content D:\minimind\logs\stages.log
# loss 曲线数据（本仓库）
Get-Content docs\assets\pretrain_loss.csv -TotalCount 5
# 权重哈希
Get-FileHash D:\minimind\src\minimind-master\out\full_sft_768.pth -Algorithm SHA256
```

> 说明：完整训练日志（约 200MB）与 137MB 的 `.pth` 权重未放入仓库；如需可放 Release（pth 超过 GitHub 100MB 单文件限制，建议 Hugging Face 或分卷）。
