---
template_id: better-product-graph.prd.general
template_version: 0.3.0-draft
template_status: INVALIDATED
language: zh-CN
predecessor_template: templates/prd/general/PRD_TEMPLATE_v0.2.md
predecessor_sha256: sha256:c276e951bba16ff868f5b2cf7dacb1642adf5eac512fb2a3898f4ad825ad64a4
invalidated_date: 2026-08-24
invalidated_reason: Expression policy must be versioned independently from PRD structure.
historical_experiment_path: templates/prd/general/experiments/PRD_TEMPLATE_v0.3_expression-coupled_INVALIDATED.md
replacement_template: templates/prd/general/PRD_TEMPLATE_v0.2.md
replacement_writing_profile: policies/document-experience/PRD_WRITING_PROFILE_v0.1.json
---

# PRD Template v0.3 Draft — Invalidated

这不是可用的 PRD 模板。

此前的 v0.3 草案把 ELI5 表达规则直接写进模板。这个设计会让“写哪些内容”和“怎样表达”一起版本化：更换模板时可能意外更换写作标准，更新表达规范时也会制造没有结构变化的模板版本。

该方向现已撤回：

- PRD 结构继续使用 `PRD_TEMPLATE_v0.2.md`。
- ELI5 表达规则迁移到独立的 `PRD_WRITING_GUIDE_v0.1.md`。
- 写作规范由 `PRD_WRITING_PROFILE_v0.1.json` 选择和绑定，可与不同模板组合。
- 原实验内容保存在 `experiments/PRD_TEMPLATE_v0.3_expression-coupled_INVALIDATED.md`，仅供审计，不得生成新 PRD。

本文件未注册 Runtime Profile，不 supersede v0.2，也不改变 default 或 fallback。
