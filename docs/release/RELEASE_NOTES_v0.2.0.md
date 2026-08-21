# Better Product Graph 0.2.0 — Developer Alpha

Better Product Graph turns an idea, a piece of user feedback, or an online issue into a traceable product decision and an engineering-ready PRD.

This release is the first public Developer Alpha. It is meant for product builders who are comfortable evaluating an early local-first workflow and reporting where it helps—or gets in the way.

## What is included

- The end-to-end Product Graph from Signal Intake through local PRD handoff.
- Problem discovery that separates evidence, assumptions, and unknowns before solution writing.
- Product decisions that can commit, experiment, wait, stop, or escalate instead of forcing every signal into a PRD.
- Configurable PRD templates, parallel advisory review, bounded optimization, and auditable local state.
- Codex and Claude Code Host adapters built from one shared Core.
- Host-specific Marketplace ZIPs for pinned, reproducible installation.

## Distilled from eli

Better Product Graph comes from distilling eli's product-management practice: think broadly before committing, challenge the framing before polishing the solution, and then deliver in small, decoupled slices.

It is not a personality clone. It turns those working methods into explicit, inspectable product-development contracts that other product managers and agents can use, question, and improve.

## Developer Alpha boundaries

- Local-first only. There is no hosted control plane.
- Reviewers are advisory; final organizational approval remains outside the Graph.
- Development Graph and Test Graph are not included yet. The handoff contracts are reserved for them.
- Evals generation is not included yet. Required but unfulfilled Evals remain visibly not ready.
- Bootstrap is deliberately deferred to the next Developer Alpha.
- The Claude adapter is available for experimentation, but its authenticated Host path has less production evidence than the Codex path.

## Install

The repository is both a Codex and Claude Code Marketplace. See the bilingual [installation guide](INSTALL_v0.2.md) for direct installation, pinned ZIP installation, verification, updates, and removal.

## Feedback

This Alpha will improve through concrete usage reports. Please use the repository's issue forms for:

- reproducible bugs;
- installation problems;
- product workflow feedback;
- missing or confusing product-management guidance.

Security-sensitive reports should follow `SECURITY.md` instead of a public issue.

---

# Better Product Graph 0.2.0 — 开发者 Alpha

Better Product Graph 把一个产品想法、一条用户反馈或一个线上 Issue，逐步转化为可追溯的产品决策和可交付研发的 PRD。

这是第一个公开的 Developer Alpha，适合愿意实际试用早期本地工作流，并反馈它哪里有帮助、哪里造成阻碍的产品与研发人员。

## 本次包含什么

- 从 Signal Intake 到本地 PRD 交接的完整产品 Graph。
- 在设计方案之前，先区分证据、假设和未知的问题发现流程。
- 产品决策不再只有“做”：还可以实验、等待、停止或升级决策。
- 可配置 PRD 模板、并行建议型审查、有上限的优化循环，以及可审计的本地状态。
- 基于同一套 Core 构建的 Codex 与 Claude Code Host Adapter。
- 两种 Host 各自独立、可固定版本安装的 Marketplace ZIP。

## 来自对 eli 的蒸馏

Better Product Graph 来自对 eli 产品工作方法的蒸馏：承诺投入之前充分思考，打磨方案之前先质疑问题框架，进入落地后再拆成小而解耦的迭代。

它不是人格复制，而是把这些工作方法变成明确、可检查的产品研发契约，让其他产品经理和 Agent 能够使用、质疑并继续改进。

## Developer Alpha 的边界

- 当前只支持本地运行，没有托管控制面。
- Reviewer 只提供建议；正式团队审批仍然在 Graph 外部完成。
- 研发 Graph 和测试 Graph 尚未包含在本次发行中，但已经保留交接合同。
- Evals Generator 尚未实现；需要 Evals 但没有完成时，系统会如实保持 Not Ready。
- Bootstrap 明确放到下一个 Developer Alpha。
- Claude Adapter 可供实验，但它的真实 Host 证据还少于 Codex 路径。

## 安装

这个仓库同时是 Codex 和 Claude Code Marketplace。直接安装、固定 ZIP 安装、验证、升级和卸载方法，请阅读双语[安装指南](INSTALL_v0.2.md)。

## 反馈

这个 Alpha 最需要的是真实使用反馈。请通过仓库 Issue 表单提交：

- 可以复现的缺陷；
- 安装问题；
- 产品工作流反馈；
- 缺失、含混或不够专业的产品指导。

涉及安全的信息请按照 `SECURITY.md` 私下报告，不要提交公开 Issue。
