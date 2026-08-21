# Better Product Graph 项目 Roadmap v0.14

状态：RELEASED CURRENT-STATE ROADMAP
日期：2026-08-21
上一版本：`BETTER_PRODUCT_GRAPH_ROADMAP_v0.13.md`（冻结，不修改）
架构基线：`docs/architecture/PRD_GRAPH_v1.4.md`

> v0.14 记录 Better Product Graph 从内部本地交付进入公开 Developer Alpha 的决定。它不扩写 Product Graph，也不把尚未实现的能力包装成当前功能。

## 1. 一句话结论

当前 `0.2.0` 作为第一个公开 **Developer Alpha** 发布：开放源码，提供 Codex 与 Claude Code 两个宿主安装包、面向用户的安装说明、最小公开 CI 和 GitHub Issues 反馈入口。

Bootstrap 不再作为本次发布的前置条件；它是下一个 Developer Alpha 的首要产品能力。

后续顺序保持：

```text
Developer Alpha 0.2.0：公开当前可运行 Product Loop
→ 下一个 Alpha：项目 Bootstrap
→ 多项目真实试点
→ Evals Generator / 测试设计合同
→ Knowledge Maintenance Graph
→ 按真实需求接入 Connector
→ 有真实运行数据后再做自进化、多 Agent 和无人值守治理
```

研发 Graph 和测试 Graph 仍是下游可插拔系统，不属于 Better Product Graph。

## 2. 当前真实状态

### 2.1 已经可用

| 能力 | 当前结论 | 证据边界 |
|---|---|---|
| Product Graph Core | 已实现 | Graph manifest、原子节点说明、确定性状态控制、版本、审计、恢复和本地 Handoff 可运行 |
| Codex Host Adapter | 已实现 | 已有同一 Run 从 Signal 到 local Release、local Handoff 和 `COMPLETED` 的真实 Host 证据 |
| Claude Host Adapter | 已实现为薄适配 | 与 Codex 共享 Core；已验证关键可写、权限、恢复和 Handoff 路径；只读 Help 的 runner 证据仍不完整 |
| Problem Discovery | 已实现核心路径 | Evidence、Assumption Audit、Learning、Synthesis、Ready 可恢复；访谈可显式跳过并保留未知 |
| Product Decision 与 Planning | 已实现核心路径 | 支持 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT`，并支持模块拆分与迭代拆分 |
| PRD 与 Review–Optimize | 已实现核心路径 | 可配置模板、版本化 PRD、建议性并行审查、disposition、修订和复审绑定 exact Candidate |
| Ready / Release / Handoff | 已实现本地合同 | 只证明本地产物就绪与交接包生成，不代表研发完成、测试通过或组织批准 |
| 本地发行工程 | 已实现一期 | allowlist build、installed identity、deterministic package、隔离安装、卸载/回滚和 fail-closed 校验已有自动测试 |

### 2.2 本次 Developer Alpha 新增的公开交付

- 正式开源许可证：`Apache-2.0`。
- 中英双语 README，明确产品用途、适用对象、限制和“来自对 eli 产品方法的蒸馏”。
- 面向使用者的 Codex / Claude Code 安装、验证、升级与卸载说明。
- 一个 GitHub Release，附两个宿主专用、可独立安装的 Marketplace ZIP 和 `SHA256SUMS`。
- 最小公开 CI：运行测试、修复验证器、双 Host 构建、身份校验和确定性发行包检查。
- GitHub Issues 表单：Bug、产品反馈、安装问题；安全问题走私密漏洞反馈而不是公开 Issue。
- 公开仓库继续保持“正式成果仓库”边界；完整研发历史和过程材料留在私有研发仓库。

### 2.3 仍然没有

- 没有项目 Bootstrap 的正式实现。
- 没有共享 Knowledge Maintenance Graph。
- 没有 evals-generator，也没有测试 Graph。
- 没有飞书项目、Issues Collector、研发 Graph 或测试 Graph 的真实 Connector。
- 没有自动升级、自我改写 Skill 或自动向上游提交经验的机制。
- 没有无人值守 Reviewer 阻塞权、多 Agent 权限治理或远端服务。

这些能力不能在 README、Release Notes 或 Issue 回复中被描述为已交付。

## 3. Developer Alpha 发布合同

### 3.1 版本与命名

- Plugin 版本：`0.2.0`。
- GitHub tag：`v0.2.0`。
- Release 标题：`Better Product Graph 0.2.0 — Developer Alpha`。
- GitHub Release 类型：Pre-release。
- 当前 Alpha 面向愿意阅读限制、保留本地证据并反馈问题的开发者和产品实践者，不承诺生产级稳定性。

### 3.2 为什么是一个 Release、两个 ZIP

Codex 与 Claude Code 共享同一 Product Graph Core，但宿主要求的 manifest、公开 Skill 入口和安装目录不同。单个插件 artifact 混装两个 manifest 会破坏宿主发现与身份边界。

因此本次发布：

```text
Better Product Graph 0.2.0 — Developer Alpha
├── better-product-graph-codex-0.2.0.zip
├── better-product-graph-claude-0.2.0.zip
└── SHA256SUMS
```

两个 ZIP 必须：

- 来自同一个 clean source commit；
- 具有相同 `core_tree_fingerprint`；
- 分别只包含一个宿主 manifest；
- 带有自己的 build identity 和 `LICENSE`；
- 可从解压后的本地 Marketplace 安装；
- SHA-256 与 GitHub Release 中的 `SHA256SUMS` 一致。

### 3.3 公开仓库边界

公开仓库包含：

- 当前可安装产品源码与双 Host Marketplace 快照；
- 必要测试、构建脚本、正式 PRD、Roadmap 和已采纳 ADR；
- README、安装说明、许可证、贡献与安全说明、Issue 模板和 CI；
- `RELEASE_SOURCE.json`，绑定私有研发来源 commit 和公开发行身份。

公开仓库不包含：

- 本地 Run 状态、用户项目数据、原始聊天、秘密和凭据；
- `.better-work/`、`.assistant/`、原始审计探针和施工过程文档；
- 被 supersede 的大量过程稿和未采纳方案；
- 研发仓库的完整分支与提交历史。

## 4. R1：下一个 Alpha — 项目 Bootstrap

Bootstrap 是 Host-level 公共入口/子流程，不是 Product Graph 业务节点，也不需要 MCP、服务、数据库或常驻进程。

最小范围：

1. 解析并展示 requested project root、resolved project root 和 repository root。
2. 没有 Git 时自动 `git init -b main`；只允许 `.git/**` 变化，不自动 add、commit、push、remote 或改写 `.gitignore`。
3. 通过受限 scanner 读取明确允许的项目文件；拒绝 symlink、秘密目录、巨型/二进制文件、BPG 输出树和越界路径。
4. 把项目文件视为不可信内容，文档中的指令不能覆盖 Host/System/Plugin policy。
5. 生成最小 Project Profile、Owner、语言、模板选择、本地 Knowledge Snapshot 和 Connector mount 状态。
6. Snapshot 绑定实际读取文件的 path/hash、scanner policy、Plugin、模板和 schema 版本；输入变化时生成 superseding Snapshot，不原地覆盖。
7. 首个 Signal 通过 idempotent handoff packet 绑定 exact Bootstrap Snapshot；重试不重复创建 occurrence/Run。
8. 扫描超限时进入 `PARTIAL/PAUSED`，保留可恢复位置，不假装完成。

Bootstrap 进入下一个 Alpha 前，至少要通过秘密文件、symlink、路径越界、父仓库、重复 resume、输入 drift 和首个 Signal exactly-once 原型验证。

## 5. R2：多项目真实试点

目标不是继续增加节点，而是确认现有 Product Loop 是否真正帮助不同经验水平的 PM。

优先试点：

- 普通 Idea：完整走 Problem Discovery → Decision → Plan → PRD。
- 简单需求：验证复杂度 Router 能否减少前期讨论但不降低 PRD 质量。
- 大规划：验证横向模块拆分与纵向迭代拆分能否产出 Plan + 1..N PRD。
- Implementation Deviation Bug：生成轻量核查包而不是重 PRD。
- Product Logic Defect：重新进入产品定义与 PRD。
- `WAIT` / `STOP`：验证新证据能否触发重新审视。

重点记录访谈打断次数、无效问题率、Problem Frame 改变、Reviewer 噪声、返工轮数、false-ready、恢复失败和 Plan→PRD 遗漏。

## 6. R3：Evals Generator 与测试设计合同

产品 Graph 可以定义“怎样证明需求实现正确”，但不冒充测试团队执行了测试。

交付范围：

- `Eval Strategy`：判断普通 AC 是否足够，以及 Evals 为 `NOT_NEEDED / RECOMMENDED / REQUIRED`。
- `Eval Pack`：目标行为、Ground Truth、输入、预期、评分、边界与不可接受结果。
- `Test Design Contract`：功能场景、AC 映射、边界/异常、回归建议和下游 exact refs。
- `evals-generator`：从 Decision、Plan、PRD 和风险生成候选包；由独立 Reviewer 审查。
- TDD-ready seam：让未来测试 Graph 转成正式测试用例、测试代码、runner 和 verdict。

`NOT_RUN` 必须继续与 `PASS` 分开。

## 7. R4：Knowledge Maintenance Graph

知识库是独立 Graph；Better Product Graph 只读取 exact 发布快照并提交候选更新，不直接改 canonical knowledge。

实现前先确认：知识消费者、raw source 与 derived knowledge 的边界、更新时效、可信度、提案/审查/发布权限、Decision/Plan/PRD/Review/研发测试结果的关联，以及新知识如何触发旧决策 Impact 提醒。

正式 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` Decision Record 与 released PRD 都是未来 Knowledge Source Corpus 候选。

## 8. R5：Connectors

所有外部输入先进入统一 `signal.intake`。Connector 只保留原始内容、来源、外部引用和已知关联，不提前替 Router 判定路线。

候选包括：Issues Collector、用户反馈、飞书项目、DOCX/飞书文档、研发 Graph Handoff、测试 Graph 反馈和独立 Agent Reviewer。只有出现真实消费者、认证方式和失败恢复要求时才进入实现。

## 9. R6：学习、多 Agent 与无人值守治理

- 规划学习先形成可审计、可拒绝、可回滚的提案，禁止静默自改或无授权 push/PR。
- 当前优先使用同一 Host 内的 sub-agent 做并行、对抗或旁路任务；跨 Host 多 Agent 协作要等身份、权限、冻结输入和分歧保留机制成立。
- Reviewer 当前始终 `ADVISORY_ONLY`。只有真正进入无人值守研发并出现政策或事故证据，才评估正式阻塞权。

## 10. Developer Alpha 反馈与升级节奏

公开反馈分三类：

- Bug：安装失败、状态损坏、不可恢复、错误 Ready/Release、权限或证据伪造。
- 产品反馈：流程过重、提问无效、决策建议质量、PRD 可读性、遗漏场景。
- 安装问题：宿主版本、命令输出、操作系统、包 checksum 和可复现步骤。

低等级命名、文档可读性和非阻塞一致性问题进入 Issue/Roadmap，不自动触发连续热修版本。真正阻塞错误发布、错误 Ready、权限/证据伪造、数据损坏、Run 不可恢复或无法产出/交接 PRD 的问题，才进入紧急修复判断。

## 11. 永久边界

- Better Product Graph 是完整产线中的产品部分，不包含研发 Graph 或测试 Graph。
- Agent 负责产品语义；程序负责状态、权限、完整性、版本和确定性迁移。
- 文档存在、Exit 0、Schema PASS 或多个 Agent 一致，都不自动等于产品完成或事实成立。
- Reviewer 默认只给建议；外置团队审核与远端 Connector 回执不属于 PRD Ready。
- 不保存模型隐藏 Chain-of-Thought；只保存 Evidence、结构化理由、假设、未知、建议、分歧、Decision 和 change history。
- 本地 Core 在 Connector、共享知识服务和下游 Graph 缺席时仍可运行。

## 12. 下次 Roadmap 更新条件

只有以下事项之一形成正式产品变化时才创建 v0.15：

- Bootstrap 完成设计冻结、原型验证或进入实现。
- Developer Alpha 的真实反馈改变 Product Loop、HITL 或 Reviewer 权限。
- Evals、Knowledge 或 Connector 的 consumer contract 被确认。
- 公开安装/发行形态发生实质变化。
- 项目优先级或资源约束发生重大变化。

普通实现进度、低等级文案和单个测试修复记录在 Git、Issue 或 Release Notes，不再为每一处变化创建 Roadmap 版本。
