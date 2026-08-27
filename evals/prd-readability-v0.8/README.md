# PRD Readability Eval v0.8 — Preregistered Successor Suite

本目录是 Suite v0.7 / RC4 正式失败后的新身份，不能替换、重写或重新解释任何 v0.7 与 RC4 证据。

RC4 的三位 Reviewer 对旧 case-002 都给出 PASS；事后分析确认，旧稿只是让概览、流程和验收分别承担摘要、执行说明与可观察验证，没有形成会伤害读者的重复。问题在 fixture/oracle 不匹配，而不是 Reviewer 没有学会“看到重复就报错”。

v0.8 只把 case-002 替换为明确的竞争定义：多个位置都自称完整正式合同，并在贵宾例外与同一分钟决胜字段上给出会改变结果的冲突。另有一份同领域正向校准稿，保留简短概览、唯一产品规则引用和行为验收；它只参与盲校准，不进入九案与未来 27 次正式评分分母。

## 当前边界

- Fixture bytes：`FROZEN`
- Blind Fixture Calibration：`APPROVED`（A2/B2 均为 `6 FINDING + 4 PASS`）
- Oracle / Preregistration / Scorer：`FROZEN_BEFORE_AGENT_OUTPUT`
- Agent Product Eval：`NOT_RUN`
- 普通 Product Review：`NOT_RUN`
- 观察式真人阅读：`NOT_RUN`
- 新 RC 构建、安装、发布：`NOT_RUN`

`fixture_calibration.py` 生成了两份自包含、不同顺序的盲投影。Reviewer 只能看到十份匿名文档和六份公开合同，不能看到 intended objective、expected result、case role、scorer、adjudication、校准专用判断提示或另一位 Reviewer 的结果。A2 与 B2 的结果已经按精确哈希进入 `fixture-review/`，并在 `adjudication.json` 中完成处置；随后才创建 v0.8 oracle、preregistration、run contract、evidence reader 与 scorer。

正式 Agent Eval 仍未运行。`case-001` 至 `case-009` 才进入九案 × 三次的 27 次分母；同领域正向校准稿只证明“简短摘要 + 单一权威引用 + 行为验收”可以合理通过，永不进入正式分母。`0.2.18-rc.5` 尚未构建或安装。

评分不是可覆盖的报告查询。冻结合同要求 manifest、batch receipt 和 27 个 durable result ref 全部存在后才允许第一次评分；过早调用只拒绝，不生成终态。公开评分入口先用冻结 scorer 从精确证据内部派生报告，再把不可序列化的进程内 derivation capability 交给私有提交路径；提交路径不接受调用方自行构造的 report。第一次完整评分以 `O_EXCL` 写入独立 ledger entry、Controller invocation、score、receipt 和 terminal transaction，PASS 或 FAIL 都成为正常代码路径不可替换的终态。之后必须先验证完整冻结、ledger 和 transaction，再从绑定证据逐字段只读复算；跨阶段汇总也对两个阶段分别复算，只消费既有终态，不创建或更新阶段评分。

这里的可信边界是本地受控执行，不是密码学证明：它针对 BPG 支持代码路径中的误操作、重放、半写、直接伪造 bundle 和删除终态后重建而 fail closed；不声称能够抵抗可任意修改 scorer 代码、ledger 和全部证据文件的本地特权攻击者。出现原始文件或代码被特权重写的怀疑时，必须停止并做外部审计，不能把这些 JSON 文件称为“不可伪造权威”。

## 失效校准记录

基于提交 `2edac87a2bcb8eb08db688a2dcd8e1ea64a6dbcd` 生成的首轮投影已永久标记为 `SUPERSEDED_INVALID_FOR_CALIBRATION`。原因不是 Reviewer 结果好坏，而是 Reviewer 可见工单包含了同领域正向稿的专门判断提示，且若干非 case-002 文档相对 v0.7 出现了额外的评分导向文本；这会污染真正独立的读者判断。

该轮投影与输出保留为不可变审计记录，但不能进入校准、oracle、preregistration、评分或发布证据。有效校准只使用提交 `a89e496` 生成的新投影，以及 Reviewer A2/B2 的精确输出。
