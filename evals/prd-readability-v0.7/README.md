# PRD Readability Eval v0.7 — Frozen Holdout Contract

本目录是 `better-product-graph-prd-readability-v0.7` 的已冻结 holdout 合同。九份 Candidate 与读者可见视觉均为新字节；它们不复用 v0.4、v0.5 或 v0.6 的 Candidate/asset，也不迁移任何历史 Run、Reviewer、输出或评分证据。

## 当前阶段

- Fixture corpus：`FROZEN`
- Fixture Review：`APPROVED`
- Adjudication：`APPROVED_FOR_PREREGISTRATION`
- Expected envelope：`FROZEN_EVALUATOR_ONLY`
- Preregistration：`PREREGISTERED_BEFORE_RESULTS`
- Agent Product Eval：`NOT_RUN`
- 真实 PRD ordinary Review：`NOT_RUN`
- 观察式真人阅读：`NOT_RUN`

`fixture-tree.json` 绑定本轮九份 Candidate 与一对 SVG/PNG 的 exact bytes。A2/B2 已独立批准 replacement tree；expected、preregistration、scorer 与 review records 留在 evaluator custody，不得进入匿名 Agent workspace 或 Reviewer projection。机械合同 PASS 不能推导语义 PASS/FAIL。

## 资产边界

只有 `case-009` 引用读者可见视觉。SVG 是语义源，匹配的 `@2x.png` 由本机可信 `sips` 渲染生成；两者必须同时通过真实视觉资产校验器。其余八案不携带图片。

结果目录仍只保留本边界说明。两个强制阶段 `RC_CANDIDATE` 与 `FINAL_PUBLIC_ARTIFACT` 都是 `NOT_RUN`；本次没有 execution manifest、Agent 输出、语义评分或 ordinary PRD Review 结果。
