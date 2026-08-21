# Product Graph Evals

Version: `0.1`

## Purpose

本 Eval Pack 用于判断 Product Graph 是否能把 Idea、用户反馈和线上 Issue 转化为有证据、可决策、可研发、可测试、可追溯的产品规格。

它不把“生成了多少份 PRD”或“文档像不像 PRD”当作核心质量指标。评测对象是一次完整的 Product Run：

```text
Signals + Project Knowledge Snapshot
→ Triage
→ Product Decision
→ ProductSpecPackage
→ Dev/Test Feedback
→ Released Outcome
```

## Package Structure

```text
evals/product-graph/
├── README.md
├── suite.yaml
├── cases/
│   ├── starter-adversarial.yaml
│   └── case-template.yaml
├── rubrics/
│   └── product-spec-rubric.yaml
└── schemas/
    ├── eval-case.schema.json
    └── eval-result.schema.json
```

- `suite.yaml`: 指标、Gate、运行频率和失败分类的机器配置。
- `starter-adversarial.yaml`: 10 个合成对抗案例，用于建立基础回归能力。
- `case-template.yaml`: 新增真实历史案例时使用。
- `product-spec-rubric.yaml`: 模型评审与人工校准共用的评分标准。
- `schemas/`: 约束 Eval Case 和 Eval Result 的格式。

## Evaluation Layers

### L0 — Contract and Integrity

确定性检查：

- Schema 是否有效。
- Requirement、Acceptance Rule 和 Evidence 引用是否闭合。
- 是否存在 orphan Requirement 或 orphan Acceptance Rule。
- 未确认结论是否被标为 provisional/assumption。
- Product Ready 是否满足 Gate。
- Dev/Test 缺席是否被正确记录为 not-connected。
- 是否发生越权读取或敏感信息泄露。

L0 是硬 Gate。严重完整性错误不能被模型评分抵消。

### L1 — Capability

分别评估：

- Signal 分类、路由和去重。
- 项目知识检索、时效、冲突和权限处理。
- most valuable unknown 识别。
- 产品决策、scope discipline 和 provisional 判断。
- Requirement、Acceptance Rule、NFR 和异常路径质量。

### L2 — Historical Replay

使用真实历史任务重放端到端 Product Run。标准答案不是一份固定 PRD，而是结构化 Oracle：

- 必须识别的 Signal 类型和路由。
- 必须使用的证据。
- 必须包含或排除的需求。
- 必须提出的问题或升级项。
- 允许的决策集合。
- 禁止出现的结论和错误状态。

### L3 — Downstream Acceptance

从研发和测试侧评估：

- 研发首次接收率。
- 研发/测试澄清次数。
- 因规格遗漏造成的返工率。
- Acceptance Rule → Test Case 覆盖率。
- 测试阶段发现的产品规格缺陷率。

### L4 — Outcome and Traceability

评估：

- 发布后的目标结果达成率。
- 线上问题是否可追溯到 Requirement/Acceptance Rule。
- 线上问题是否源于上下文、决策、需求或测试样例遗漏。
- 被推翻的产品假设是否回流为新的 Regression Case。

## Dataset Strategy

起步阶段建议建立 20–50 个真实历史案例，并保留本包中的 10 个合成对抗案例。

真实案例应覆盖：

- Idea、Feedback、Issue。
- 重复、冲突、噪声和信息不足。
- 过期知识、错误知识和权限受限知识。
- 跨平台、迁移、合规、安全和 AI 内容处理需求。
- 应接受、应延期、应拒绝和应升级人工判断的场景。

建议拆分：

- Development Set: 日常调试可见。
- Regression Set: 每次变更执行。
- Holdout Set: 仅在阶段验收时执行，避免过拟合。

真实用户反馈、内部 Issue 和受限知识不应直接写入公开案例文件。案例中保存受控 fixture ref、内容 hash 和脱敏摘要。

## Core Metrics

### Efficiency

- Signal → Triage latency：Median / P90。
- Triage → Product Decision latency：Median / P90。
- Decision → PRD Ready latency：Median / P90。
- 单次 Product Run 的人工介入次数、模型调用量和成本。

### Classification and Routing

- Signal Classification Macro-F1。
- Routing Accuracy。
- Critical Misroute Rate。
- Dedup Precision / Recall / F1。

### Evidence and Context

```text
Unsupported Claim Rate =
未引用证据且未标为假设的事实性结论数 / 全部事实性结论数
```

同时监控：

- Required Evidence Recall。
- 错误证据引用率。
- 过期知识使用率。
- 冲突识别率。
- Model Inference 被写成 Fact 的比例。
- Restricted Knowledge 越权读取次数。

### Product Spec

- Must Requirement Coverage。
- Traceability Closure。
- Requirement Ambiguity Rate。
- Acceptance Rule Coverage。
- Requirement Testability Rate。
- Happy/Empty/Error/Permission/Timeout/Dependency/Retry/Compatibility/Degradation 分支覆盖。

### Downstream

- Dev First-pass Acceptance Rate。
- Dev/Test Clarification Count。
- Spec-induced Rework Rate。
- Acceptance Rule → Test Case Coverage。
- Escaped Spec Defect Rate。

## Evaluation Methods

每个案例可组合三类检查：

1. `deterministic`: Schema、ID、引用、状态、覆盖率、权限和 provenance。
2. `model_judge`: 问题定义、证据匹配、决策、范围、可研发性和可测试性。
3. `human_calibration`: 产品、研发、测试对模型结论做抽样校准。

不能使用一个总分掩盖 P0 错误。报告应同时给出：

- 硬 Gate 结果。
- 分维度指标。
- Aggregate verdict。
- `max_claim_scope`。
- 失败发生的节点和证据。

## Run Policy

- 每次 Prompt、Model、Policy、Schema 或代码变更：运行 Smoke Set。
- 每个 PR：运行完整 Regression Set。
- 每周：执行历史案例和漂移检查。
- 每次研发退回、测试规格缺陷或线上事故：新增 Regression Case。
- 每月：复盘研发接收率、返工率和线上规格缺陷。

每次 Eval Result 必须绑定：

- Product Graph version。
- Model version。
- Prompt/Skill version。
- Knowledge snapshot。
- Policy version。
- ProductSpec schema version。

## Initial Promotion Rule

`suite.yaml` 中的阈值是 v0.1 初始假设，需要用真实团队基线校准。在以下条件未满足前，Product Graph 只能处于 pilot：

- 所有 L0 硬 Gate 通过。
- Critical Signal Recall = 100%。
- Critical Unsupported Claims = 0。
- False Ready = 0。
- Dev/Test 缺席状态判断准确率 = 100%。
- 模型 Judge 与人工关键结论一致率达到要求。

## Adding A Case

1. 复制 `cases/case-template.yaml`。
2. 为案例分配稳定 `case_id`。
3. 冻结输入 Signal、Knowledge Snapshot 和 Plugin Capability Snapshot。
4. 编写结构化 Oracle，不编写唯一标准 PRD。
5. 指明 deterministic、model judge 和 human review 的适用范围。
6. 使用 `schemas/eval-case.schema.json` 校验单个 case。
7. 将真实失败映射到 `suite.yaml` 中的 failure taxonomy。

