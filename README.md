![Better Product Graph — distilled from eli](assets/brand/eli-distillation-banner.jpeg)

# Better Product Graph

**Turn product signals into decisions worth making—and PRDs worth building.**

[![CI](https://github.com/d-wwei/better-product-graph/actions/workflows/ci.yml/badge.svg)](https://github.com/d-wwei/better-product-graph/actions/workflows/ci.yml)
[![Developer Alpha](https://img.shields.io/github/v/release/d-wwei/better-product-graph?include_prereleases&label=developer%20alpha)](https://github.com/d-wwei/better-product-graph/releases)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[中文](#中文) · [English](#english)

## 中文

Better Product Graph（BPG）是一个运行在 Codex 和 Claude Code 里的本地产品工作流。它接收产品想法、用户反馈和线上 Issue，帮助产品经理先把问题想清楚、做出明确决策，再形成完整规划、拆分小而解耦的 PRD，并生成可审计的本地研发交接包。

它不会把每个 Signal 都强行写成 PRD。合理的结果也可以是：立即处理线上事故、提交 Bug 核查包、继续研究、做可逆实验、等待条件成熟，或者明确停止。

> **当前正式版本：[`v2.0.2`](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.2) Developer Alpha。** 这是 BPG 2.0 的 Agent-first 质量、复审和交付成本修复；不迁移旧 Run，也不代表外部交付、研发接收、Product Evals 执行、实现或产品效果已验证。

### 来自对 eli 的蒸馏

Better Product Graph 来自对 **eli 的产品工作方式**的蒸馏：不要拿到需求就写方案；先区分现象、用户提出的解法和真正的问题；用证据挑战假设；审慎地做、大胆地停；规划时把系统想完整，落地时再做横向模块化和纵向小步迭代。

这不是 eli 的人格复制，也不是一个替产品负责人拍板的“AI 产品经理”。它把一套经过长期实践的提问、判断、规划和审查方法，变成可执行、可恢复、可追溯的 Graph。

### 它怎样工作

```text
Idea / 用户反馈 / 线上 Issue
              │
              ▼
      Signal & Route
              │
              ▼
 UNDERSTAND → DIAGNOSE & VALUE
              │
              ▼
  Problem Candidate → 独立 Review
              │
              ▼
 方案发现 → Decision Candidate → 独立 Review
              │
              ▼
 STOP / WAIT / RESEARCH / EXPERIMENT /
 COMMIT NOW / FUTURE ROADMAP
              │
              ▼
   PLAN THE PRODUCT SYSTEM
              │
              ▼
 一份正式或实验型 PRD → 内容与写作 Review
              │
              ▼
 Ready → 可选格式的 Local Handoff
```

最需要智能的工作——研究、访谈、质疑、问题定义、决策建议、规划和 PRD 写作——由 Host Agent 完成。Python Controller 只负责状态、权限、版本、证据引用、校验、恢复和确定性落盘，不假装会做产品判断。

### 为什么值得试

- **先决定，再写 PRD。** 用户原话、事实、推断、假设和未知不会混在一起。
- **AI 会反过来挑战 PM。** Better Question 和 20 个认知基座按当前最有价值的未知动态工作，不是固定 Checklist。
- **规划完整，交付克制。** 当前主链把完整产品系统规划收敛为一份高内聚 PRD；多 PRD 拆分属于后续 2.1。
- **审查不演戏。** 产品、UX、研发可行性、可测试性和合规 Reviewer 可以并行工作；它们只给建议，不冒充最终审批人。
- **中断后能继续。** Run、Evidence、Decision、版本、审查意见和 Handoff 都保存在项目本地，不依赖聊天记录维持记忆。
- **宿主可替换，Core 不复制。** Codex 与 Claude Code 使用不同 Host Adapter，但共享同一 Product Graph Core。

### 适合谁

它现在最适合：

- 希望 junior PM 获得更强问题澄清、反方挑战和规划指导的团队；
- 不想把一次聊天当成产品决策记录的产品负责人；
- 需要在进入研发前，把目标、边界、未知、验收和取舍交代清楚的项目；
- 愿意试用本地 Developer Alpha，并把问题反馈回来的 Agent Builder 和产品实践者。

它现在不适合：

- 期待零配置导入陌生项目全部知识；
- 需要飞书、Jira、Linear、研发 Graph 或测试 Graph 已经自动连通；
- 需要 Reviewer 自动阻塞发布，或要求无人值守生产级治理；
- 把 Schema PASS、多个模型一致或文档生成成功当成产品质量证明。

### 安装

冻结安装资产请使用 [`v2.0.2` GitHub Release](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.2)，并按 [2.0.2 安装指南](docs/release/INSTALL_v2.0.2.md) 校验下载资产与安装身份。

当前冻结 Release 的最快安装方式：

Codex：

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.2
codex plugin add better-product-graph@better-product-graph
```

Claude Code：

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

安装后请打开新任务/新会话。你可以直接用自然语言，也可以显式调用：

```text
$better-product-graph <产品想法、用户反馈或 Issue>
/better-product-graph:better-product-graph <product signal>
```

普通请求默认使用 BPG 2.0。用户可以直接开始、查看、继续、暂停或准备本地交接；内部 Controller action 不作为需要用户记忆的命令公开。

### 数据、权限与边界

- BPG 把运行状态写入当前项目的 `.better-product-graph/`，不会把产品数据上传到 BPG 自建服务；本项目也没有这类服务。
- Handoff 是本地交接包，不等于研发已接收、测试已通过或组织已批准。
- Reviewer 为 `ADVISORY_ONLY`；当前只有产品 Owner 对产品决策负责。
- 不保存模型隐藏 Chain-of-Thought，只保存 Evidence、结构化理由、假设、未知、建议、分歧、Decision 和 change history。
- 当前没有 MCP、数据库、队列、daemon、Web UI 或真实外部 Connector。

### 当前证据

- 当前 `2.0.2` 源码候选的完整测试结果为 `894/894 PASS`，覆盖 Issue #1–#7 修复、双 Host 构建、隔离安装、自检和 Plugin Contract。用于验证真实 PRD Run 时间、上下文、Token 与质量收益的可比 Golden Run 仍为 `NOT_RUN`；机械测试不能替代真实产品效果证据。
- 真实 Codex Host Alpha Run `bpg2-run-alpha-dogfood-20260829` 从 Signal 走到 `LOCAL_HANDOFF_COMPLETE`；Problem、Decision 和最终 PRD 都由独立 Reviewer 检查，最终 PRD v3 的差异复查与整体回归为 `PASS`。外部发送、研发接收、实现测试和产品效果验证仍为 `NOT_RUN`。
- `0.2.19` 的精确旧 Run 恢复能力继续保留；BPG 2.0 Alpha 与旧 Run 完全隔离，不导入、不迁移、不续跑。
- Writing Profile、Guide、Reviewer Instruction 和评测合同与 `0.2.18` 字节一致；冻结 RC5 与最终公开候选包的 PRD Writing Reviewer Agent Eval 均为 `27/27 PASS`，本热修复没有重跑或扩大该语义声明。
- 4 个独立 Reviewer 对 Evals Generator PRD v0.6 完成普通 Review 并记录 6 项关注；Ready 随后因 raw inline SVG 在零 receipt 状态 fail closed，因此该 PRD 不是 Ready、Released、已实现或已测试。
- 两个 Host 的确定性包、installed identity、隔离安装和共享 Core 一致性均进入发行检查；观察式真人读者验证仍为 `NOT_RUN`。
- Codex 的历史真实 Host Run 已从 Signal 走到本地 Release、Handoff 和 `COMPLETED`。
- Claude Code 的 `0.2.0` 真实 Host 试跑为 6/7：关键可写、权限、恢复和 Handoff 路径通过；只读 Help 没有 runner 调用证据，因此严格结果仍是 `PARTIAL`。
- 自然语言 Auto-selection 与真实 Product Golden Agent judgment 仍是 `NOT_RUN`，不会被机械测试冒充。

更多边界见 [BPG 2.x Roadmap](docs/roadmap/BETTER_PRODUCT_GRAPH_2_X_ROADMAP_v0.2.md)、[Roadmap v0.17](docs/roadmap/BETTER_PRODUCT_GRAPH_ROADMAP_v0.17.md) 与 [产品 PRD](docs/released/prd/BETTER_PRODUCT_GRAPH_PRD.md)。

### 反馈与贡献

- [报告 Bug](https://github.com/d-wwei/better-product-graph/issues/new?template=bug_report.yml)
- [提交产品反馈](https://github.com/d-wwei/better-product-graph/issues/new?template=product_feedback.yml)
- [报告安装问题](https://github.com/d-wwei/better-product-graph/issues/new?template=installation.yml)
- 贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 安全漏洞不要公开提交，请按 [SECURITY.md](SECURITY.md) 使用私密漏洞反馈。

项目采用 [Apache License 2.0](LICENSE)。

---

## English

Better Product Graph (BPG) is a local product workflow for Codex and Claude Code. It takes product ideas, user feedback, and production issues; helps a product manager understand the underlying problem and make an explicit decision; then produces an outcome-first plan, small decoupled PRDs, and an auditable local engineering handoff.

It does not force every signal into a PRD. A valid outcome may be an incident brief, a bug investigation packet, more research, a reversible experiment, a deliberate wait, or a recorded stop.

> **Current formal version: [`v2.0.2`](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.2) Developer Alpha.** This release repairs Agent-first quality, re-review, and delivery-cost boundaries in BPG 2.0. It does not migrate legacy Runs or claim external delivery, engineering receipt, Product Evals execution, implementation, or product-effect validation.

### Distilled from eli

Better Product Graph distills **eli’s product practice** into a working system: do not jump from a request to a feature; separate the symptom, the user’s proposed solution, and the underlying problem; challenge assumptions with evidence; be careful about starting and willing to stop; plan the whole system, then ship through modular boundaries and small iterations.

This is not a personality clone, and it is not an “AI product manager” that takes responsibility away from the product owner. It turns a practiced way of questioning, deciding, planning, and reviewing into an executable, recoverable, and auditable Graph.

### How it works

```text
Idea / feedback / production issue
                │
                ▼
          Signal & Route
                │
                ▼
    UNDERSTAND → DIAGNOSE & VALUE
                │
                ▼
    Problem Candidate → independent Review
                │
                ▼
 Solution discovery → Decision Candidate → Review
                │
                ▼
 STOP / WAIT / RESEARCH / EXPERIMENT /
 COMMIT NOW / FUTURE ROADMAP
                │
                ▼
       PLAN THE PRODUCT SYSTEM
                │
                ▼
 One formal or experimental PRD → content and writing Review
                │
                ▼
       Ready → optional-format Local Handoff
```

The Host Agent performs the work that needs judgment: research, interviews, challenge, problem framing, decision advice, planning, and PRD writing. The Python Controller handles state, permissions, versions, evidence references, validation, recovery, and deterministic persistence. It does not pretend to make product judgments.

### Why try it

- **Decide before writing.** User statements, facts, inferences, assumptions, and unknowns stay distinct.
- **The Agent may challenge the PM.** Better Question and twenty cognitive lenses are routed to the current most valuable unknown instead of becoming a fixed checklist.
- **Plan broadly, deliver narrowly.** The current main path turns a complete product-system plan into one cohesive PRD; multi-PRD decomposition is planned for 2.1.
- **Review without theater.** Product, UX, engineering-feasibility, testability, and compliance reviewers may run in parallel. They remain advisory and do not impersonate final approval.
- **Resume after interruption.** Runs, evidence, decisions, versions, review notes, and handoffs live in the project rather than disappearing with chat history.
- **Change the Host, not the Core.** Codex and Claude Code use different Host Adapters over the same Product Graph Core.

### Who it is for

The Developer Alpha is most useful for:

- teams that want stronger problem-framing, challenge, and guidance for junior PMs;
- product owners who do not want a transient chat to become the decision record;
- projects that need goals, boundaries, unknowns, acceptance, and trade-offs to be clear before engineering starts;
- Agent builders and product practitioners willing to test a local Alpha and report what breaks.

It is not yet a fit if you need:

- zero-configuration ingestion of all knowledge from an unfamiliar project;
- working Feishu, Jira, Linear, Development Graph, or Test Graph integrations;
- reviewers with automatic blocking authority or unattended production governance;
- schema success, model agreement, or document generation to count as product-quality proof.

### Install

Use the [`v2.0.2` GitHub Release](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.2) for frozen installation assets, and verify the downloaded assets and installed identity with the [2.0.2 installation guide](docs/release/INSTALL_v2.0.2.md).

The shortest frozen-Release path is:

Codex:

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.2
codex plugin add better-product-graph@better-product-graph
```

Claude Code:

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

Open a new task or session after installation. Use natural language or an explicit entry:

```text
$better-product-graph <product idea, feedback, or issue>
/better-product-graph:better-product-graph <product signal>
```

Ordinary requests use BPG 2.0 by default. Users can start, inspect, resume, pause, or prepare a local handoff directly; internal Controller actions are not user syntax.

### Data, authority, and boundaries

- BPG writes Run state under `.better-product-graph/` in the current project. It has no BPG-operated service that uploads your product data.
- A Handoff is a local package. It does not mean engineering accepted it, testing passed, or the organization approved it.
- Reviewers are `ADVISORY_ONLY`; the product Owner remains responsible for product decisions.
- BPG does not store hidden model chain-of-thought. It preserves evidence, structured rationale, assumptions, unknowns, recommendations, disagreements, decisions, and change history.
- This source line has no MCP, database, queue, daemon, web console, or real external Connector.

### Current evidence

- The current `2.0.2` source candidate passed `894/894` tests, covering the Issue #1–#7 repairs, dual-Host builds, isolated installation, self-check, and the Plugin Contract. A comparable Golden Run measuring real PRD Run time, context, token, and quality benefits remains `NOT_RUN`; mechanical tests do not substitute for product-effect evidence.
- Real Codex Host Alpha Run `bpg2-run-alpha-dogfood-20260829` reached `LOCAL_HANDOFF_COMPLETE`. Independent Reviewers checked the Problem, Decision, and final PRD; PRD v3 passed both difference review and whole-product regression. External delivery, engineering receipt, implementation tests, and product-effect validation remain `NOT_RUN`.
- The exact legacy-Run recovery from `0.2.19` remains available. BPG 2.0 Alpha is isolated and never imports, migrates, or resumes an old Run.
- The Writing Profile, Guide, Reviewer Instruction, and evaluation contracts are byte-identical to `0.2.18`. The frozen RC5 and final public-candidate Writing Reviewer Agent Eval phases remain `27/27 PASS`; this hotfix did not rerun or broaden that semantic claim.
- Four independent reviewers completed an ordinary Review of Evals Generator PRD v0.6 and recorded six concerns. Ready then failed closed on raw inline SVG with zero receipts, so that PRD is not Ready, Released, implemented, or tested.
- Deterministic dual-Host packages, installed identity, isolated installation, and shared-Core consistency are release-gated. Observed human-reader validation remains `NOT_RUN`.
- A historical real Codex Host Run completed the local path from Signal to Release, Handoff, and `COMPLETED`.
- The real Claude Code `0.2.0` trial scored 6/7: the tested writable, permission, recovery, and Handoff paths passed; read-only Help did not produce runner evidence, so the strict result remains `PARTIAL`.
- Natural-language auto-selection and real Product Golden Agent judgment remain `NOT_RUN`; mechanical tests do not substitute for them.

See the [BPG 2.x Roadmap](docs/roadmap/BETTER_PRODUCT_GRAPH_2_X_ROADMAP_v0.2.md), [Roadmap v0.17](docs/roadmap/BETTER_PRODUCT_GRAPH_ROADMAP_v0.17.md), and the [product PRD](docs/released/prd/BETTER_PRODUCT_GRAPH_PRD.md) for the exact scope.

### Feedback and contributions

- [Report a bug](https://github.com/d-wwei/better-product-graph/issues/new?template=bug_report.yml)
- [Share product feedback](https://github.com/d-wwei/better-product-graph/issues/new?template=product_feedback.yml)
- [Report an installation problem](https://github.com/d-wwei/better-product-graph/issues/new?template=installation.yml)
- Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.
- Do not disclose vulnerabilities in public Issues. Follow [SECURITY.md](SECURITY.md) and use private vulnerability reporting.

Licensed under the [Apache License 2.0](LICENSE).
