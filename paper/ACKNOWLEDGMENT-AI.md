# IEEE ESL — AI 使用披露草稿（必须放入 Acknowledgments）

> 依据：IEEE 关于 AI 生成内容的政策 + ESL 作者指南。AI 不能列为作者；披露需覆盖
> 工具名、涉及章节、使用程度；缺失披露可能初审直接拒稿。
> 纯语法润色可豁免，但本文按“最稳妥做法”一并披露。

## 需要你确认的清单

在最终定稿前，请确认实际用过的 AI 工具与范围（勾选/补充）：

- [ ] DeepSeek Harness AI coding agent（DeepSeek 模型）——本项目的固件实现、量化工具、实验自动化、论文文字
- [ ] ChatGPT / GPT-5 等 —— 是否使用？用于哪些章节？
- [ ] Codex / Cursor / Copilot —— 是否用于代码？
- [ ] Grammarly / 其他润色工具 —— 是否用于语言润色？
- [ ] 其他：__________

> 论文中“训练”部分是在另一个 AI 会话（同一 DeepSeek Harness 系统）中由 AI 代理执行、作者监督完成。
> 按 IEEE 政策，这属于“AI 生成内容（代码/实验执行）”，建议在披露中覆盖。

## 英文草稿（4 句，放 Conclusion 之后、References 之前）

```
ACKNOWLEDGMENTS

The author used the DeepSeek Harness AI coding agent (DeepSeek model) throughout this
work: to assist with the ESP32-P4 firmware implementation (model loading, packed-weight
GEMV kernels, and the USB host protocol bridge), with quantization and measurement
tooling (Sections II–III), and with experiment automation and manuscript editing. The AI
system is not an author. The author independently verified all generated code, measurements,
and text and takes full responsibility for the accuracy, originality, and integrity of this
work. [Optional: Language editing assistance was provided by <tool>.]
```

## 若审稿人/编辑追问时的补充说明（可放 response letter，不必进正文）

- AI 的具体角色：代码实现与调试、实验脚本与串口自动化、文本起草与润色；
- 人类作者的角色：研究问题、实验设计、结果验证、结论与全部学术责任；
- 可复现性：所有代码与模型在 GitHub 开源（链接），审稿人可独立复核；
- 未使用 AI 生成任何实验数据：所有测量来自真实硬件；AI 仅辅助工具链与文本。

## 插入位置与篇幅

- 位置：Conclusion（或 Discussion）之后、References 之前；
- 篇幅：4–6 行（4 页限制内），不要展开成段落；
- 若期刊模板要求 “Acknowledgments” 单独段落，可使用上面的英文草稿原文。
