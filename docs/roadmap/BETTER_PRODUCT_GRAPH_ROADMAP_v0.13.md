# Better Product Graph 项目 Roadmap v0.13

状态：RELEASED CURRENT-STATE ROADMAP
日期：2026-08-21
上一版本：`BETTER_PRODUCT_GRAPH_ROADMAP_v0.12.md`（冻结，不修改）
架构基线：`docs/architecture/PRD_GRAPH_v1.4.md`

> v0.13 的目的不是继续扩写架构，而是把已经实现的能力、正在收敛的交付和真正的未来工作重新分开。v0.12 保留了完整的历史建设思路；本版是从今天开始排工作时使用的当前真源。

## 1. 一句话结论

Better Product Graph 已经从“只有规划”进入“Codex 本地产品闭环可运行”的阶段。下一步不应重做 Core，而应按以下顺序推进：

```text
收敛可配置 PRD 模板与第二 Host Adapter
→ 建设安全、轻量的项目 Bootstrap
→ 用多个真实项目校准 Product Loop
→ 建设 Evals Generator / 测试设计合同
→ 定义并实现 Knowledge Maintenance Graph
→ 按真实需求接入 Connector
→ 最后再考虑自进化、多 Agent 和无人值守治理
```

研发 Graph 和测试 Graph 仍是下游可插拔系统；它们不属于 Better Product Graph，也不是 Product Loop 独立运行的前置条件。

## 2. 当前真实状态

### 2.1 已经成立的基础

| 能力 | 当前结论 | 证据边界 |
|---|---|---|
| Product Graph Core | 已实现 | 具备 Graph manifest、原子节点说明、Host runtime、确定性状态控制、版本、审计、恢复和本地 Handoff |
| Codex Host Adapter | 已实现并完成真实 Host 验收 | installed 0.1.20 的同一 Run 从 Signal 走到 `COMPLETED`，产出 immutable local Release 和 local Handoff |
| 产品决策与规划 | 已实现核心路径 | 支持 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT`，Owner choice 与 Agent 建议分离；Plan 支持模块和迭代拆分 |
| Problem Discovery | 已实现核心路径 | Evidence、Assumption Audit、Learning、Synthesis、Ready 可恢复；访谈是重要交互点，但可显式跳过并记录未知 |
| Review–Optimize | 已实现建议性审查 | Reviewer 无阻塞权；并行审查、聚合、disposition、修订和复审均绑定 exact Candidate |
| PRD Ready / Release | 已实现本地合同 | Ready 只判断 exact Candidate 的本地发布条件；不代表研发完成、测试通过或组织批准 |
| 安装与供应链边界 | 已实现一期本地版本 | allowlist build、installed identity、deterministic package、fresh install、uninstall/rollback 和 fail-closed 校验已有自动测试 |

Codex 0.1.20 的最终 Host 验收记录位于：

`audits/BETTER_PRODUCT_GRAPH_v0.1.20_FINAL_HOST_ACCEPTANCE_2026-08-21/FINAL_HOST_ACCEPTANCE_REPORT.md`

该 PASS 只证明本地 Product Graph 交付闭环，不证明远端发送、外部审批、研发完成、测试执行或 Product Golden 判断。

### 2.2 本次收敛的三条交付线

| 交付线 | 当前状态 | 本版处置 |
|---|---|---|
| 通用 PRD 模板 v0.2 | 独立候选已通过模板与全量测试，待最终集成 | 将 `general@0.2.0` 作为可配置默认模板；保留 frozen upstream fallback 和显式 rollback |
| Claude Host Adapter vNext | Static、Distribution、真实 CLI conformance 已通过，待最终集成与一次 authenticated Host trial | 保持薄 Adapter；不得复制 Core 或引入 Claude 专属业务语义 |
| Roadmap v0.13 | 本文件 | 用当前实施事实替换 v0.12 的 `implementation pending` 叙述，并重新排列后续建设顺序 |

只有最终集成候选完成构建、隔离安装和真实 Host 验证后，前两项才从“已验证独立候选”升级为“已交付集成能力”。

### 2.3 仍然没有的能力

- 没有项目 Bootstrap 的正式实现。
- 没有共享 Knowledge Maintenance Graph。
- 没有 evals-generator，也没有自动生成正式测试用例的 Test Graph。
- 没有飞书项目、Issues Collector、研发 Graph 或测试 Graph 的真实 Connector。
- 没有自动升级插件、自动改写 Skill、自动向上游提交经验的自进化机制。
- 没有无人值守场景下的 Reviewer 阻塞权、Policy/Waiver 或多 Agent 权限治理。

这些缺口不影响当前本地 Product Loop 使用，但决定了下一阶段的建设顺序。

## 3. 路线总览

| 阶段 | 主要目标 | 完成证据 |
|---|---|---|
| R0 当前收敛 | 模板 v0.2、Claude Adapter、Roadmap v0.13 合并为一个干净候选 | Codex/Claude 两类包可重复构建并隔离安装；唯一一次真实 Claude Host trial 有明确 PASS/FAIL/NOT_RUN 结果 |
| R1 Bootstrap | 让新项目安全、快速地具备 BPG 可运行上下文 | 新项目可完成 root/Git/模板/本地知识/Owner/Connector mount 初始化；不会读取秘密或越界写入 |
| R2 多项目试点 | 用真实使用校准 Product Loop，而不是继续靠文档假设 | 多个真实 Signal 产生 Decision、Plan、1..N PRD；记录访谈负担、false-ready、返工和恢复数据 |
| R3 Evals 与测试设计 | 建立产品规格到验证合同的桥梁 | 可生成、审查并交接 Eval Pack 与 Test Design Contract；不冒充测试已执行 |
| R4 Knowledge Graph | 建设独立、共享、可审计的知识维护系统 | 多 PM/研发/测试读取同一发布快照；BPG 只读并提交 Proposal，不直接改 canonical knowledge |
| R5 Connectors | 根据真实消费者选择外部集成 | 至少一个输入或输出 Connector 有认证、幂等、权限、失败恢复和真实回执 |
| R6 学习与治理 | 在有真实数据后建设自进化、多 Agent 和无人值守治理 | 学习提案可审计、可拒绝、可回滚；权限与成本边界经原型证明 |

## 4. R0：当前收敛

### 4.1 通用 PRD 模板 v0.2

目标不是做一份永远不变的“大而全模板”，而是建立可配置、可升级、可回滚的模板产品能力。

本阶段要求：

- `general@0.2.0` 是普通项目的默认 Template Profile。
- 项目可显式 pin 自己的模板 ID、版本和 hash。
- 一个 Run 首次选定模板后锁定 exact identity，不能静默切到 latest。
- 更新模板只影响新 Run；进行中 Run 继续使用其不可变副本或明确阻塞。
- frozen Better-Product-Plan 派生模板保留为兼容 fallback，不再称为默认体验。
- 人类 PRD 正文优先表达目标、范围、流程、规则、验收、风险和未知；机器追溯信息放入结构化 companion，不把正文变成内部账本。
- 模板细节仍可独立升级，不因本次发布而冻结成最终形态。

### 4.2 Claude Host Adapter vNext

Claude Adapter 只解决 Host 异构，不改变 Product Graph：

- Codex 与 Claude 共享相同 Core、Controller、Schema、Validator、Gate 和原子节点说明。
- Claude 专属内容限于 manifest、namespaced Skill 入口、构建 overlay、安装验证与 Host evidence harness。
- 每个 artifact 只能包含一个 Host manifest 和一个公开 Skill。
- 两个 Host 的 Core fingerprint 必须相同；Claude runner 与 Codex runner 保持字节一致。
- Authenticated Host、Auto-selection、Product Judgment 必须分别记录，不能用 Static/Distribution PASS 代替。

### 4.3 当前阶段退出条件

- 模板和 Claude 两条线合并后全量测试通过。
- Codex 与 Claude package 分别两次构建且各自 byte-identical。
- 两种 package 都通过 installed identity、Plugin Contract 和隔离安装/卸载。
- Claude 使用安装候选执行一次 authenticated Host trial；成功、失败、配额阻塞或模型未尝试都如实记录。
- 冻结架构 v1.4 和 Roadmap v0.12 的 hash 不变。

## 5. R1：项目 Bootstrap

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

暂不做组织 Registry、知识迁移向导、远端同步、复杂权限中心或实时后台守护进程。

## 6. R2：多项目真实试点

这一阶段的目标不是继续增加节点，而是确认现有节点在不同复杂度下是否真正帮助 PM。

优先试点场景：

- 一个普通 Idea，走完整 Problem Discovery → Decision → Plan → PRD。
- 一个简单需求，验证复杂度 Router 能否缩短前期讨论但不降低 PRD 质量。
- 一个大规划，验证横向模块拆分与纵向迭代拆分能否产出 Plan + 1..N PRD。
- 一个 Implementation Deviation Bug，验证轻量核查包而非重 PRD。
- 一个 Product Logic Defect，验证重新进入产品定义和 PRD。
- 一个 `WAIT` 或 `STOP` 决策，验证后续新证据可触发重新审视。

重点收集：

- PM 被打断次数、访谈跳过率和无效问题率。
- Problem Frame 实际发生变化的轮次与证据。
- Reviewer 建议的采纳率、噪声率和返工轮数。
- false-ready、false-block、手动修复和恢复失败。
- Plan 到 PRD 的遗漏、重复、耦合和超范围内容。
- 一个决策从 Signal 到最终产物的可审计完整度。

多项目数据出来之前，不增加默认人工确认点，不授予 Reviewer 阻塞权，也不把更多分析模型做成固定 Checklist。

## 7. R3：Evals Generator 与测试设计合同

产品 Graph 可以定义“怎样证明需求实现正确”，但不冒充测试团队执行了测试。

交付范围：

- `Eval Strategy`：判断普通 AC 是否足够，以及 Evals 为 `NOT_NEEDED / RECOMMENDED / REQUIRED`。
- `Eval Pack`：目标行为、Ground Truth、输入、预期、评分方式、边界与不可接受结果。
- `Test Design Contract`：功能场景、AC 映射、边界/异常、回归建议和下游 exact refs。
- `evals-generator`：从 Decision、Plan、PRD 和风险生成候选包；由独立 Reviewer 审查，不自我宣布履行完成。
- TDD-ready seam：未来测试 Graph 可把产品侧验证意图转成正式测试用例、测试代码、runner 和 verdict。

一期不建设完整测试执行平台。`NOT_RUN` 必须继续与 `PASS` 分开。

## 8. R4：Knowledge Maintenance Graph

知识库必须是独立 Graph；Better Product Graph 只做两件事：读取 exact 发布快照，以及提交候选更新。

在实现前先定义知识产品需求：

- 谁消费哪些知识，更新时效和可信度要求是什么？
- 哪些内容是 raw source，哪些是压缩后的 derived knowledge？
- Decision、Roadmap、PRD、Review、线上反馈、研发/测试结果如何关联？
- 谁能提案、审查、发布、撤回和标记过期？
- 多 PM、研发和测试如何共享同一 canonical snapshot？
- 新知识如何触发旧 Decision、Plan 或 PRD 的 Impact 提醒？

确认需求后再反推 BPG 的 submission contract。当前先保留两层候选：

1. 与 PRD/Decision/Plan 相关的 raw data 与 exact refs。
2. 从本次规划提炼出的 derived findings、assumptions、rules 和 reusable learnings。

任何正式 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` Decision Record 都是未来知识 Source Corpus 候选，不只提交 released PRD。

## 9. R5：Connectors

所有外部输入先进入统一 `signal.intake`。Connector 只负责保留原始内容、来源、外部引用和已知关联，不在入口提前判定 Bug、Incident 或规划路线。

按实际需求选择实现顺序：

- 输入类：Issues Collector、用户反馈、飞书项目、人工粘贴。
- 输出类：飞书项目提单、飞书原生文档、DOCX 导入、研发 Graph Handoff。
- 审计类：Claude 或其他独立 Agent Reviewer。
- 反馈类：研发/测试 Graph 的结果重新进入同一个 Signal Intake。

每个 Connector 必须声明挂载位置、输入/输出合同、权限、幂等、回执、失败恢复和未配置降级。没有真实权限时，DOCX 导入作为飞书文档的可用 fallback；原生飞书创建能力保持待验证。

## 10. R6：学习、多 Agent 与无人值守治理

### 10.1 Planning Learning Loop

每次规划结束后，系统可以形成三类提案：项目事实、项目规划经验、通用插件改进。提案进入显式队列，经人类或独立审查后再被知识库、项目配置或上游仓库采纳。

禁止：静默改写 Skill、自动把一次经验推广为通用规则、无授权 push/PR、用模型自评代替真实验证。

### 10.2 Multi-Agent Collaboration

当前优先使用同一 Host 内的 sub-agent 完成可并行、对抗性或旁路任务。未来可以让 Claude 负责策划、Codex/其他 Agent 独立审计，或反过来；但必须具备独立上下文、冻结输入、身份/权限、标准 Finding 合同和 disagreement-preserving join。

### 10.3 Reviewer Governance

当前 Reviewer 始终 advisory only。只有进入真正无人值守研发、并有真实政策或事故证据时，才评估 formal blocking、Domain Owner、Policy/Waiver 和审批授权。

## 11. 已接受并收敛的历史候选

| 候选 | 处置 | 当前结论 |
|---|---|---|
| 规格生命周期引用与未来 Runtime 输入分离 | 接受，合同层已实现；继续真实项目验证 | Runtime inputs 不再携带当前 Run 的 Decision/Plan/PRD 规格来源；追溯关系留在 traceability/provenance |
| 稳定 PRD identity 与 Candidate version 解耦 | 接受，已实现 | Product Plan 绑定 stable `prd_id + slice_ref`；Candidate version/supersedes 由文档生命周期维护 |
| `PRD Increment` 人类可读定义 | 接受，进入模板持续优化 | 外显用“本次交付新增了什么、相对上版改变了什么”，不强迫读者理解内部术语 |
| `NO_PM_INTERVIEW` 与默认策略分开 | 接受，进入试点校准 | 它是本次 Run 的显式 override，不是项目永久默认；访谈中也可强制跳过并保留未知 |
| HITL 密度复核 | 接受，进入 R2 | 设计态只保留访谈和 Owner 决策等必要责任点；运行态以真实中断数据调整 |
| `PASS / READY` 命名统一 | 接受，非阻塞 | 先改善人类文案，不改变已经验证的状态与权限语义 |
| exact source 进入 Evidence Map | 接受，进入知识合同验证 | 跨 Run 信息必须以 exact source ref 进入 Evidence，不把记忆摘要当事实 |

## 12. 低优先级 Parking Lot

- 自动检查可信上游 release；发现更新时提醒用户，但不自动下载或安装。
- 针对前端、后端服务、数据/算法等产品类型的专用模板 Profile。
- Product Roadmap 作为 BPG 的正式人类产物和机器 companion，而不只是项目内部规划文件。
- 按 Most Valuable Unknown 路由外部行业研究；不是每个需求默认广泛搜索。
- Experiment Portfolio；只有并行实验数量和资源冲突真实出现后再建设。
- 插件彩蛋。内容、触发和实现时点保持开放，不进入任何 Gate。

## 13. 永久边界

- Better Product Graph 是完整产线中的产品部分，不包含研发 Graph 或测试 Graph。
- Knowledge Maintenance Graph 独立维护 canonical knowledge；BPG 不直接发布知识。
- Agent 负责产品语义；程序负责状态、权限、完整性、版本和确定性迁移。
- 文档存在、Exit 0、Schema PASS 或多个 Agent 一致，都不自动等于产品完成或事实成立。
- Reviewer 建议默认不阻塞；外置团队审核与远端 Connector 回执不属于 PRD Ready。
- 不保存模型隐藏 Chain-of-Thought；只保存 Evidence、结构化理由、假设、未知、建议、分歧、Decision 和 change history。
- 本地 Core 在所有 Connector、共享知识服务和下游 Graph 缺席时仍可运行。

## 14. 下次 Roadmap 更新条件

只有出现以下任一情况才创建 v0.14，不为日常微调快速膨胀版本号：

- R0 最终集成结论发生实质变化。
- Bootstrap 完成设计冻结或进入实现。
- 真实项目试点改变 Product Loop、HITL 或 Reviewer 权限。
- Evals、Knowledge 或 Connector 的 consumer contract 被正式确认。
- 项目优先级或资源约束发生重大变化。

普通实现进度、低等级文案问题和单个测试修复记录在 Git、Issue 或 release notes 中，不再为每一处变化新建 Roadmap 版本。
