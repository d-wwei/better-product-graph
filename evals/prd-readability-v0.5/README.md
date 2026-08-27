# PRD Readability Eval v0.5 — Frozen Preregistration

这套九案例用于评估独立 Writing Reviewer 能否识别真正影响理解的表达问题，同时放过结构合理的大表、长附录和有用视觉。它是 v0.5 的全新候选身份；v0.4 / RC2 的 `5/9 FAIL` 历史保持不变，不能被本目录重算或覆盖。

## 当前阶段

本目录已经完成 Fixture 双审与 evaluator-only 预注册，但尚未运行语义 Reviewer：

- 九份 `cases/*.md` 是 Candidate-like 原始输入；
- `assets/reader-first-layered-prd.*` 是第九案实际给读者看的 SVG/PNG 等价视觉；导出时把 Candidate 引用规范化为 `./assets/...`，并只携带该案例实际引用的 exact SVG/PNG 对；
- Fixture Review：`APPROVED`；
- 预注册：`PREREGISTERED_BEFORE_RESULTS`；
- `expected.json`、`preregistration.json` 与 `score_results.py` 只在 evaluator custody 中，绝不进入 Agent workspace；
- Agent Product Eval：`NOT_RUN`；
- 真实 PRD ordinary Review：`NOT_RUN`；
- 观察式真人阅读：`NOT_RUN`。

`run_contract.py` 只验证冻结合同并导出匿名输入；合同 `PASS` 不能把任何语义状态升级为 PASS。

## 九个场景

前六案分别保留一种主要理解断点：同层平铺、重复定义、重复表达同一状态模型、删除 Checklist 功能、勾选语义不清、拟定合同伪装成已经落地。后三案是校准正例：必要的大型状态迁移表、主路径完整且附录较长、用真实视觉解释非平凡分流。

已完成的 Fixture Reviewer 只看到了九份案例、视觉、v0.5 Guide/Profile 和目标名称，没有接触 allowed pairs、expected、scorer 或未来语义输出；两位 Reviewer 也被禁止参与后续 27 次语义尝试。
