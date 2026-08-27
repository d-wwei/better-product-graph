# Better Product Graph 0.2.18 — Developer Alpha

## 这次发布解决什么

`0.2.18` 把 PRD 写作规范审查正式接入现有并行 Review，而没有新增 Graph Node 或审批 Gate。Writing Standard Reviewer 与 PRD 作者使用不同执行实例，逐项核对 Writing Profile、Writing Guide 和精确 Candidate；Finding 继续进入现有 aggregate、disposition、优化与复审流程。

本版同时收紧了视觉资产和审查证据边界：不安全或不可渲染的视觉内容可以先进入 `SOURCE_TEXT_ONLY` 普通审查，但 Profile v0.5 的 Ready/Release 仍要求受管、安全且成对的 SVG 与 `@2x` PNG。Candidate 的资产增删改会形成新的 tree identity，并使旧 Review 失效。

## 已验证证据

- 冻结 RC5 Agent Eval：`27/27 PASS`。
- 最终公开候选包 Agent Eval：`27/27 PASS`。
- 两阶段共 54 个 Reviewer 身份；Run、attempt、Reviewer、author、output、checkpoint、state 与 result hash 的跨阶段重叠均为 0。
- 仓库内多根只读聚合：两个阶段均为 `27/27 PASS`，cross-phase issues 为 `[]`，没有重跑阶段评分。
- 最终普通 Product Review：4 个相互独立的 Reviewer，6 项 Finding，全部进入现有 disposition，Review 为 `FINALIZED`。
- 同一普通 Review 随后在 Ready 前因 reader-visible raw inline SVG fail closed：Ready receipts 为 0，`release_ref=null`，`handoff_ref=null`。
- 最终开发树测试：`761/761 PASS`。
- 观察式真人读者验证：`NOT_RUN`。

上述普通 Review 针对的是不可改写的 Evals Generator PRD v0.6。它的 Review 已完成，但该 PRD**不是** Ready、Released、已实现或已测试；本版也没有把 Agent Review 冒充真人读者观察。

## 冻结发行资产

发行资产复用最终评测时的 exact bytes，不重新构建：

| Host | 文件 | ZIP SHA-256 | Installed artifact SHA-256 |
|---|---|---|---|
| Codex | `better-product-graph-codex-0.2.18-a.zip` | `163d6c3f65047af4e514d864eead60f49e816a5112fc1be15200f1520b1bf9f5` | `5f5f9e68cbccab58726381ae2e145356d7ce995d054286639e4aacc279bfa737` |
| Claude Code | `better-product-graph-claude-0.2.18-a.zip` | `4c73c3a38f77fa6e6610cbc56abcbad8e9f65e445b6290415da24ad042f28919` | `37d39b5dab0f95d58be47a93b9f7e7e3ce9e8e63764ae01185e07ef32aac93f8` |

- Artifact build source commit: `16d8ce48b999f85d34747afb94ff255d40220c78`
- Source dirty at build: `false`
- Shared Core fingerprint: `20b8fe2e26ce0e49172e36c61ec014bbfac857d675644533aae08a86aa0840b5`
- Release channel: `Developer Alpha`
- Intended tag: `v0.2.18`

两个 Host 包共享同一 Core，但 Host Adapter、manifest 和 execution-contract fingerprint 不同，不能互换安装。

## 已知边界

- Human-reader observation 仍为 `NOT_RUN`；Agent Eval 不能替代真人可读性验证。
- Writing Reviewer 是 `ADVISORY_ONLY`，不拥有产品批准或发布阻塞权；Ready 仍由现有机械合同决定。
- 本地 Eval 证据对受支持路径中的意外变更、重放和不完整写入 fail closed，但不声称可以抵御能够同时改写代码和全部本地证据的特权攻击者。
- Evals Generator PRD v0.6 的 6 项关注及 raw inline SVG 仍未修复；本次发布不改变该 PRD 的生命周期状态。
- GitHub 发布、下载后复验和全局安装是独立的发行步骤；只有对应证据实际存在时才能宣称完成。

安装方法与校验值见 [INSTALL_v0.2.18.md](INSTALL_v0.2.18.md)。
