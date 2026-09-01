# Document Experience Policy / Profile Changelog

## Writing Reviewer Contract v3.1.1 / v3.2.1 Candidate — 2026-09-01

- 状态：`CANDIDATE / NOT_YET_RELEASED`；新建 `prd-writing-reader-review-v3.1.1`（SHA-256 `sha256:9ce674879424a8948951f6946089fe88e134f351459695a8da1003e3d4ffce74`）与 `prd-writing-reader-review-v3.2.1`（SHA-256 `sha256:1c270ad0b582b47e2f73f806aa65cfdb6776118f5936b0e9fa4843d6739d1027`）。
- v3.1.1 supersedes v3.1 用于 BPG 2.0 Alpha：增加可变状态权威边界，并把视觉责任收敛为 `PRD.md` 中 Mermaid source 的语义与可读性；v3.2.1 supersedes v3.2 用于通用 v0.5 dispatch：增加同一状态权威边界，同时保留 source-visible visual scan 兼容语义。
- 旧 `prd-writing-reader-review-v3.1` 与 `v3.2` 继续保留，SHA-256 分别为 `sha256:5659ea767a7270e82343e273ad71c50a49f03b9e3d60b040ab60b608f0a881ef` 与 `sha256:ae17022d652d9486abdce8b253749185bd841271f6591021a13618260cbc65fe`；既有 Profile v0.5 内嵌的 v3.1 绑定不原位改写，历史 Run 不迁移。
- Catalog 同时登记旧版和新版；新 Alpha selector 使用 v3.1.1，新通用 selector 使用 v3.2.1。Agent Product Eval、真实 PRD ordinary Review 和观察式真人阅读均为 `NOT_RUN`。

## PRD Writing Profile v0.5.0 Default Promotion — 2026-08-27

- 当前默认：`prd-plain-language-zh-CN@0.5.0 / RELEASED_DEFAULT`；v0.2 调整为 `RELEASED_PREVIOUS`，继续作为可回滚版本，v0.4 保持失败候选历史。
- 为保持 Suite v0.8、RC5 与 RC7 普通审查的精确可复现性，Profile 与 Guide 的评测输入字节不改写：Profile 仍为 `sha256:a2e2e3f9e3a56e2c59898e404199660807096b781b0e7b02b0f8dca9d96faaa0`，Guide 仍为 `sha256:98e6f0883c243063405736ede0196aae09c851627cfbcee846bd89d5f2403962`。
- 当前激活生命周期由 `document-experience-profiles.json` 的唯一 `RELEASED_DEFAULT` 记录负责；Profile/Guide 内嵌的 Candidate 字样保留为评测时点的不可变来源元数据，不再作为当前默认选择真源。
- RC5 Agent Eval 为 `27/27 PASS`。RC7 普通 advisory Review 为 `FINALIZED`，共八项 Finding，全部处置为 `DEFERRED_FUTURE_REVISION`；这不表示 Evals Generator v0.6 已整改。
- 观察式真人阅读仍为 `NOT_RUN`。含活动态 raw inline SVG 的 v0.6 PRD 仍为 `NOT_READY / NOT_RELEASED`，没有 Ready 收据。

## PRD Writing Profile v0.5.0 Candidate — 2026-08-26

- 状态：`CANDIDATE / CANDIDATE_NON_DEFAULT`；默认 Profile 仍为 `prd-plain-language-zh-CN@0.2.0 / RELEASED_DEFAULT`。
- 写作规范：`PRD_WRITING_GUIDE_v0.5.md`，SHA-256 `sha256:98e6f0883c243063405736ede0196aae09c851627cfbcee846bd89d5f2403962`。
- Profile：`PRD_WRITING_PROFILE_v0.5.json`，SHA-256 `sha256:a2e2e3f9e3a56e2c59898e404199660807096b781b0e7b02b0f8dca9d96faaa0`。
- 保留 v0.4 的八条表达规则、六个读者结果、九类诊断和十二种修订手段；没有新增 Node、Gate、批准权或普通 Review 结果字段。
- 澄清 Writing Reviewer 只评估已陈述内容的清晰度与可定位性；实质内容完整性仍由 Product、Engineering Feasibility 与 Testability Reviewer 负责。
- 将视觉触发项明确为检查信号而非自动配图要求，并允许不同的、有证据支持的修订手段实现同一读者目标。
- 新 ordinary Reviewer 资源为 `prd-writing-reader-review-v3.1`，继续使用 `document-experience-reader-review.v3` 与 `ADVISORY_ONLY`；Agent Product Eval、真实 PRD ordinary Review 和观察式真人阅读均为 `NOT_RUN`。

## PRD Writing Profile v0.4.0 Candidate — 2026-08-26

- 状态：`CANDIDATE / CANDIDATE_NON_DEFAULT`；默认 Profile 仍为 `prd-plain-language-zh-CN@0.2.0 / RELEASED_DEFAULT`。
- 写作规范：`PRD_WRITING_GUIDE_v0.4.md`，SHA-256 `sha256:b262531a455a31e9a5aa087808ca369f99ce65e488d17ff3af59998f649e3639`。
- Profile：`PRD_WRITING_PROFILE_v0.4.json`，SHA-256 `sha256:85d81248659d0fd0a74fd9fce679b4c5bda0445971a00329c379b76672705919`。
- 定义八条去重复、分组、主路径、表达选择、表格、Checklist 功能、状态真实性和人话优先规则；保留六个读者结果作为一级目标。
- 固定九类理解断点和十二种最小修订手段；禁止按字数、行数、章节数、表格行数或 Checklist 项数自动判错。
- 新 ordinary Reviewer 合同 `prd-writing-reader-review-v3` 当前标记 `PROPOSED_NOT_IMPLEMENTED`；Agent Product Eval、真实 PRD Review 和观察式真人阅读均为 `NOT_RUN`，不得据此晋级。

## PRD Writing Profile v0.3.0 Historical Candidate Import — 2026-08-26

- 从 `codex/prd-writing-reviewer-v04@33ef15099f26298aee19ed88eff566011486be48` 逐文件 `git show` 导入并冻结 v0.3 Guide、Profile、Eval Suite、hidden expected、结果和失败报告；未 merge 或 cherry-pick 旧分支。
- 导入清单：`docs/release/PRD_WRITING_REVIEWER_v0.3_IMPORT_MANIFEST.json`，SHA-256 `sha256:8c993237c5b8a0c316ca340c1a0ce8db946270f560d7611d6efb56a7739165e7`，逐文件记录 source/target、Git blob、SHA-256 和字节数。
- 历史结果保持 `3/5 FAIL`；真实 PRD Review 与观察式真人阅读保持 `NOT_RUN`；`promotion_eligible=false`。该导入不重算、不修正原始评分，也不改变 v0.2 默认身份。
- 历史 Guide SHA-256：`sha256:dafd119eac9c7274ebe26fd3c263e21bd8047f9404f50c4bbdca77725468a47f`；历史 Profile SHA-256：`sha256:2d58aff838e7fd071c4840e6fbbc23e324046a7fd27e8fd11cb5476070ba14dc`。

## PRD Writing Profile v0.1.0 — 2026-08-24

- 状态：`RELEASED / ACTIVE`；BPG 默认 PRD 表达 Profile 为 `prd-plain-language-zh-CN@0.1.0 / RELEASED_DEFAULT`。
- 写作规范：`PRD_WRITING_GUIDE_v0.1.md`，SHA-256 `sha256:2236d05d02cbe1901937a3365acb3a29f46ef7fb30c235c9df0c7865777360eb`。
- Profile：`PRD_WRITING_PROFILE_v0.1.json`，SHA-256 `sha256:a166a74d1ca0135f36efdfdc7e4a87b83a2125e7cefe4875e31b6b3d5e77bdd0`。
- 将 PRD 的 ELI5 表达规则从 `PRD_TEMPLATE_v0.3.md` 中解耦，形成独立写作规范与 Profile。
- 新增条件式内容处置：正文中真正不适用且不影响判断的内容直接省略；Checklist 保留检查项并记录“不适用”和具体理由；未知、未设计、未执行及必填语义不得借此省略。
- 模板继续决定栏目与产品语义承载位置；写作 Profile 独立决定受众、语言、表达密度、术语解释和必要配图要求。
- Skill / Host Agent 应读取确切 Policy、Profile 和 Template 后执行，不能只依赖模型记忆，也不能把规范全文复制进每个模板。
- 已生成逐字节一致的 Runtime Profile 与写作规范，并由 `document-experience-profiles.json` 记录默认版本和精确哈希；PRD 生成上下文必须单独绑定 Template 与 Document Experience。
- 没有真实产品经理阅读测试，不能宣称可读性已经验证通过。
