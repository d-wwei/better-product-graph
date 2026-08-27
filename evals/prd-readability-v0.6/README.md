# PRD Readability Eval v0.6 — Frozen Scoring Alignment

这套九案例是已经批准的 v0.5 `cases/`、`assets/` 与 `fixture-review/` 的 byte-exact 自包含快照。v0.6 只建立新的 evaluator identity，使隐藏 scorer 与公开 v3.2 Reviewer 合同一致；它没有修改产品指令、Profile、Guide、Reviewer 资源或结果 Schema。

## 评分规则

- 负例必须只有一个 `verdict=FINDING` assessment；
- 结果声明的 primary diagnosis/repair pair 必须是该案例预登记的 pair；
- 两个 primary 值必须分别出现在该 Finding assessment 的 `issue_types` 和 `repair_techniques`；
- 同一个 Finding assessment 中允许相关、enum-valid 的次要 issue labels 或 repairs；
- 第二个 Finding assessment 必须失败；
- 正例必须 `PASS`、primary 字段为 `null`、reader failures 为空且没有 Finding assessment。

## 当前阶段与边界

- Fixture Review：沿用 byte-exact approved v0.5 review records；
- 预注册：`PREREGISTERED_BEFORE_RESULTS`；
- 选择规则：九案各三次，必须 `27/27`，`ALL_ATTEMPTS_NO_BEST_OF_N`；
- Agent Product Eval：`NOT_RUN`；
- 真实 PRD ordinary Review：`NOT_RUN`；
- 观察式真人阅读：`NOT_RUN`。

`expected.json`、`preregistration.json`、`score_results.py` 和 Fixture Review records 只在 evaluator custody 中，绝不进入 Agent workspace。Eval-only 结果为 `ADVISORY_ONLY`，没有 Product authority，不能进入 Product Review、Ready、Release 或 Handoff。

历史 v0.5 的外部 `22/27 FAIL` 证据保持冻结，不能用 v0.6 scorer 重算、解释或复用其 Runs。
