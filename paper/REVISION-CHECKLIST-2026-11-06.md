# ESL 论文 · 模拟审稿意见修复清单（2026-11-06）

> 来源：用户提供的 8 份 AI 模拟审稿/审计意见（含 R1/R2/R3/F 团队汇总）。
> 原则：真实硬伤全修；模拟审稿人误读的项标注“不修”，避免过度改稿。
> 状态：☐ 未开始 ｜ ◐ 进行中 ｜ ☑ 完成

## P0 — 不需要新测量（先做，改 tex + 表格 + 引用）

### 精度判据与设备端分数
- ☑ **A1** 改 bound 语义：只有 q3e4 同时满足两项；mixed/mix42/mix432 写 "CE-pass, rule-fail"（不再说 satisfy the bound）
- ☑ **A2** q3e4 规则分双报：host 24/30 = 80%，device 22/30 = 73.3%；明确判据评估端点
- ☑ **A3** 增加 fp32 行（CE 6.9732，rule 24/30）；解释 q4 73.3% vs fp32 80% 与 q4 CE 反优（n=30 噪声）
- ☑ **A4** 补 q3 的 rule score（host；跑 `host_rules.py` 加 q3 profile）
- ☑ **A5** 把 "accuracy lower bound" 改名为 "well-formedness/degeneration score" 或明确五条规则；写进正文
- ☑ **A6** 预注册：补 commit 时间戳 + `paper/PRE-REGISTRATION.md`（阈值 1.15×/80% 固定于 2026-11-04/05，早于 q3e4 设备分）；否则降级为 "pre-specified"
- ◐ **A7**（已补公开 checkpoint 锚点 + 数据集名；标准 benchmark 仍缺） 限制/评测：正文注明无标准 benchmark、语料规模、prompt 构成（9 官方 + 21 自写）

### 速度/延迟/归因
- ☑ **B1** 统一最终 build：Table III q3e4 ms → 1,612；Table IV This work → 0.620；旧值只作中间 build 脚注
- ☑ **B2** 重写 Amdahl：r=0.988,s=2.13 → 2.10；baseline share f=0.9944 → 2.13；增量/累计分开
- ☑ **B3** 带宽统一：权重 10.98/13.5/18.2；含 KV 11.7/14.4/19.2；说明分母
- ☑ **B4** "end-to-end" → "decode"；结论补启动 20.6 s / prefill 逐 token / 单轮限制
- ☑ **B5** FP16 K/V：区分"上下文长度效应"与"FP16 精度效应"；"statistically unchanged" 改 "within run-to-run variation"
- ☑ **B6** 修正 CE 重复归因（6.66067 vs 6.66209 只归因一处；改 "within 0.0014"）

### 表格/数字/单位
- ☑ **C1** Table I 补一行 "other runtime PSRAM 209,860 B"（tokenizer/USB/heap 等），使行和闭合
- ☑ **C2** Intro 244/128 → **122 MiB FP16 / 61 MiB INT8**（244 为 FP32）
- ☑ **C3** Table III caption 标注 host CE/rule vs device ms；q3 rule 列补数
- ☑ **C4** Table IV caption 区分 "as reported" 与 "this work measured"；补 active params/quality 说明或删 tok/s 列
- ☑ **C5** Fig 1a：预算线画在**图像预算 ≈30.99 MB**（32 MiB − KV − runtime），或明确 33.55 MB 总量线 + 说明；q4* 定义
- ☑ **C6** Fig 1b：与正文统一（n=64 或标注 n=32 单独 run）；y 轴用全范围或标注放大
- ☑ **C7** PPL 1,107 → **1,112**
- ☑ **C8** Method KV "remain FP32" → 部署 FP16（96 FP32 为 fallback）
- ☑ **C9** "attention compressed less aggressively than FFN" → 改为 mixed 的描述
- ☑ **C10** 1.34× → **1.33×**（2152/1612=1.33499）；"2.13×1.23×1.33≈3.49"；MiB/MB 统一；"on-package PSRAM" → **on-board**（hex_psram A2 256Mbit）

### 归属/artifact/引用
- ☑ **D1** 引用 Kestrel-MCU（repo + [2]）；正文加 "reused / modified / new" 一句；解释 3-bit packed 为何不能直接用 PIE 展开
- ☑ **D2** 发 **v0.2.1 Release**：7 个镜像（q2/q3/q3e4/mixed/q4/mix42/mix432）+ tokenizer + 完整 SHA-256 + commit
- ☑ **D3** SHA-256 补全；"Every number in Tables I–IV" → "Tables I–III + Table IV This-work row"；补 commit/tag
- ☑ **D4** [13] ternaryvit 在正文引用或删除
- ◐ **D5** 全仓库旧数字清理（0.465、投稿准备中、5,622 标签）

### 模拟审稿人误读（不修，记录备查）
- ☒ Table II "rMB/s / 0.98810.98"：PDF 文本抽取假象
- ☒ Fig 1b "1.629 ms"：千位分隔符
- ☒ "Introduction 重复段落 / on a 26"：当前 PDF 不存在

## P1 — 需要板子/短测量

- ☑ **E1**（需板子：板子当前未连接，延后） 重建 float-dequant baseline（packed + 每权重浮点反量化）3 次 → 可辩护的 5,622 或新值；修正 Table II 标签
- ☐ **A4'** q3 的 host rule（已列 P0，此处仅提醒跑）
- ☑ **F1** UART（COM4）抓启动日志：packed weights PSRAM free / KV 后 free → Table I 差额拆解
- ☑ **F2** 同访问模式 read-only 对照或 PMU/CPI；cycles/weight（9.1）写进正文或 discussion
- ◐ **F3** 可选：192-window CE 重测；prompt 集扩到 ≥100 + Wilson CI；标准语料 held-out CE；能量
- ☐ **F4** 可选：q3e4 最终 build 的 FP32 vs FP16 KV 延迟对照（3 次）

## P2 — 改稿与回复

- ☑ **G1** tex v2：全部 P0/P1 修改，重编 **≤4 页**（必要时删 HachimoDock 集成段、压缩 Method）
- ☑ **G2** 图表重绘（Fig 1a 预算线、Fig 1b 统一数据）
- ☑ **G3** point-by-point response letter（按 R1/R2/R3/F 逐条：意见 → 修改 → 证据位置）
- ◐ **G4** 更新 `paper/`、`docs/`、README、Release 说明到 v2 一致

## 执行顺序

1. 先跑 P1 的 q3 rule、UART 日志（几分钟，不阻塞）
2. 改 tex 的 P0 文本/表格（分批，每批编译检查页数）
3. 发 v0.2.1、补 Kestrel 引用、清理仓库旧数字
4. 重建 baseline（可选，若时间允许）
5. 写 response letter
