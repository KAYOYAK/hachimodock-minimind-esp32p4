# NOTICE — 原创归属、衍生关系与许可证

本仓库是一个**非商业、学习研究性质**的集成项目。它把三个来源不同的组件组合成一个完全离线的桌面 AI 宠物，必须明确各自的原创归属。

---

## 0. 原创 / 复刻 / 衍生 分类（速查）

| 类别 | 内容 | 归属 |
|---|---|---|
| **原创（上游）** | HachimoDock 硬件/固件/客户端/协议；MiniMind 架构/训练代码/数据；Kestrel-MCU 内核；ESP-IDF 等 | 各自原作者，本项目不主张版权 |
| **复刻（本人完成）** | 哈基米机整机（官方 BOM + 官方固件）；MiniMind 训练链路（官方配方+公开数据，自训权重）；医药 LoRA（官方数据+超参，效果级） | 本人，按上游公开资料复刻 |
| **原创（本人）** | 自训练/量化权重；KMCU 混合量化与工具链；ESP32-P4 端侧部署优化；CH343 4M USB Host 协议桥；三者集成方案 | 本人，Apache-2.0 |
| **不包含** | 官方 HachimoDock 固件/客户端/素材；MiniMind 官方权重 | 遵守上游许可证，不再分发 |

## 1. 上游原创项目

### HachimoDock / 哈基米机
- 仓库：https://github.com/YizhengWw/HachimoDock
- 原创：小米技术委创新产品团队
- 许可：**HachimoDock Project License v1.0**（个人非商业复刻/修改允许；禁止转售、商用）
- 本仓库：**不包含** HachimoDock 的官方固件、官方客户端、官方素材；设备端保持官方固件不动，我们的代码只作为 USB Host 侧替代 PC 客户端。

### MiniMind
- 仓库：https://github.com/jingyaogong/minimind
- 原创：MiniMind 原作者
- 许可：遵循上游仓库 LICENSE
- 本仓库：**不重新分发** MiniMind 官方权重；模型产物为你在上游架构基础上的训练 / LoRA 微调 / 量化结果（见 `docs/MODEL.md`）。

### Kestrel-MCU
- 仓库：https://github.com/m13253246268-ship-it/kestrel-llm-mcu
- 许可：Apache-2.0
- 本仓库：在 `firmware/` 中保留其版权与 NOTICE，并附带我们的修改（QK-norm、打包 GEMV、int16 加速）。

### 其他
- ESP-IDF（Apache-2.0）、WCH CH343 文档与 Linux 驱动语义、TinyUSB（MIT）等，遵循各自许可证。

## 2. 本仓库原创贡献

以下工作由本项目作者完成，以 **Apache-2.0** 发布：

1. **模型训练与 LoRA 微调**：在 MiniMind 架构上完成全流程训练 / 低秩适配（配置见 `docs/MODEL.md`）。
2. **自定义混合位宽量化**：q3e4 KMCU 格式（embed q4 / attn+FFN q3），以及量化工具链。
3. **ESP32-P4 端侧部署**：qk-norm 修复、打包权重零拷贝 GEMV、int16 激活量化整数点积、内存/任务规划。
4. **USB Host 协议桥**：在 ESP32-P4 上实现 CH343 主机驱动与 HachimoDock 官方 JSONL 协议，替代官方 PC 客户端。
5. **CH343 运行时逆向结论**：4 Mbaud、`0xA1/0xA4` vendor 初始化、DTR/RTS 与 EN/GPIO35 的对应关系（见 `docs/PROTOCOL.md`）。
6. **集成方案**：把上述三者组合成完全离线、无 PC、无网络的桌面 AI 宠物。

## 3. 模型权重声明

- `model.kmcu`（q3e4，28,632,448 B）是作者本人基于自训练 / LoRA 权重所做的量化产物；
- 发布方式建议：GitHub Release Assets 或 Hugging Face，仓库内只保留 SHA256；
- 使用时请遵守：**仅供学习研究，禁止商业转售**；不得冒充上游官方发布。

## 4. 商标与命名

- "HachimoDock / 哈基米机" 为小米相关项目的名称与商标，本项目仅作事实性引用；
- "MiniMind" 为上游项目名称；
- 本仓库不代表、也不隶属于上述任何一方。
