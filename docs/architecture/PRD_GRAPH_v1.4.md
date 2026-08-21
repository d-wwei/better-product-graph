# Better Product Graph 架构说明 v1.4

状态：Frozen Distribution/Eval Implementation Contract Closeout / implementation pending
日期：2026-08-20
上一版本：`PRD_GRAPH_v1.3.md`（已冻结架构一致性基线）
依据：V1.3、三份 2026-08-20 best-practices 研究及 `audits/PRD_GRAPH_v1.4_RESEARCH_DISPOSITION_2026-08-20.md`

正式产品名：**Better Product Graph**。`BPG` 仅用于内部字段或说明，不作为公开 Skill 名或用户别名。V1.0/V1.1 中的 **PRD Graph** 是旧称；两个冻结版本及现有文件、目录、仓库路径本次不回改、不无痕重命名，迁移计划另行制定。

> V1.4 是在 V1.3 产品架构不扩域前提下完成的 **distribution/eval implementation contract closeout**：只收敛 Codex 安装包唯一公开 Skill、内部 Atomic Skill Modules、最小 source→dist 与安装身份合同、两类系统评测的分工、旧 eval 基线迁移和模板 promotion 边界。它仍是 `implementation pending`，不表示 Plugin、Core、Host Adapter、Golden Cases 或任何 runtime 已实现/运行/PASS；没有新增 MCP、CLI、Service、Runtime、业务 Node 或 Gate。

## 阅读入口：第一次接触 Better Product Graph 的产品经理先看这里

### 一句话说明

Better Product Graph 接收 Idea、用户反馈和线上 Issue，帮助产品经理先弄清楚问题、再决定采取什么行动；只有确实值得进入建设的方向，才继续形成 Product Plan、一个或多个 PRD，以及可以交给研发的产品侧交接包。

它不会把每条输入都变成 PRD。合理的结果还包括收进待办箱、交研发紧急核查、按既有产品规则修复 Bug、补证据、做受控实验、以后再做，或者明确停止。

### 完整产线和系统边界

```text
Idea / 用户反馈 / 线上 Issue
              │
              ▼
┌────────────────────────────┐
│ Better Product Graph       │
│ 产品部分：把信号变成       │
│ 负责任的产品行动与交付合同 │
└─────────────┬──────────────┘
              │ Product / Incident / Bug Fix Handoff
              ▼
┌────────────────────────────┐
│ 研发 Graph                 │
│ 技术方案、实现、构建和研发验证 │
└─────────────┬──────────────┘
              │ Build Handoff
              ▼
┌────────────────────────────┐
│ 测试 Graph                 │
│ 测试设计、执行和发布质量判断 │
└────────────────────────────┘

       ┌──────────────────────────────────────────────┐
       │ Knowledge Maintenance Graph                  │
       │ 横向服务三张 Graph：发布版本化项目知识；      │
       │ Snapshot ──▶ Product / Development / Test    │
       │ Future Proposal ◀── Product / Development / Test │
       │ Better Product Graph 当前只读快照；未来提交合同待定义 │
       └──────────────────────────────────────────────┘
```

Better Product Graph 是完整产线中的**产品部分**，不是完整产线本身。研发可行性和可测试性 Reviewer 属于 PRD 专业审查能力；它们不会调用或替代研发 Graph、测试 Graph。Knowledge Maintenance Graph 也不是第四道生产工序，而是三张业务 Graph 共用的横向知识系统。

### 产品部分用大白话怎么运行

```text
收到一个信号
→ 保留原话并判断应该走哪条路
→ 紧急线上问题先交研发核查；明确实现偏差按 Bug 快线修复
→ 新问题先搞清楚“我们知道什么”
→ 检查“我们是不是从一开始就想错了”
→ AI 自己查资料，必要时再访谈、质疑和帮助 PM 补证
→ 把探索收敛成清晰的问题定义
→ 决定停止、等待、研究、实验，还是正式投入
→ 正式投入后做完整规划，并横向拆模块、纵向拆迭代
→ 为每个可独立交付的增量生成 PRD 和必要的 Eval Pack
→ 先检查 PRD 是否忠实于上游，再专业审查、优化并通过程序化 Ready
→ 形成 BPG Released 交付物；是否自动写入飞书/研发系统由 Connector 副作用政策决定
```

这条业务主线见 §6；机器节点、状态、Schema 和 Gate 的精确实现见 §14—§24。读者不需要先理解这些技术合同，才能理解 Product Loop 为什么存在。

### 推荐阅读路径

- **产品经理第一次阅读**：本节 → §1 产品目标与边界 → §6 Product Loop 业务总览 → §8 三条输入路径 → §9 认知核心 → §10 产品决策 → §11—§13 规划与 PRD。
- **准备实现 Core 的工程人员**：先读上述业务路径，再读 §7 原子化规则、§14—§21 实现合同和 §23—§24 验收。
- **审核设计理由的人**：读 §2 ADR 索引、各节点附近的“为什么”、§25 Skills 吸收边界、§27 版本变化和 §28 待验证事项。
- **只想确认当前状态的人**：本文已冻结为架构一致性基线，但软件仍未实现；§30 的 Node Review 状态区分已确认产品边界、待实现合同、待原型事项与延后能力。

### 关键业务节点三层速查

下表服务于人类理解；已经存在的 Machine Name 使用当前文档中的确切 ID，尚未完成 Node Review 的阶段只列当前节点组并显式标记 `PENDING`，不为提高可读性发明稳定 ID。内部 Validator、Audit Event 和 Schema 字段不强行套用三层命名。

| Machine Name / 当前节点组 | 中文名称 | 一句大白话 |
|---|---|---|
| `signal.ingest / prepare / relate / classify` | 信号接收与整理 | 先保住用户原话，再把它整理成可以判断、但没有被 AI 偷改的输入。 |
| `route.select` | 路线选择 | 判断这条信号现在最应该进待办箱、事故核查、Bug 基线核查，还是问题发现。 |
| `INCIDENT_ASSESS` | 线上问题快速核查 | 可能正在伤害用户时，先凑齐研发能开始核查的最少信息，别为了写文档耽误处理。 |
| `BUG_BASELINE_CHECK` | Bug 产品基线核查 | 先确认产品本来应该怎样运行，再判断是实现错了、产品规则错了，还是规则根本没说清楚。 |
| `evidence.collect` | 证据收集 | 先找到原始材料和来源，不让摘要、猜测或转述冒充证据。 |
| `evidence.map` | 证据地图 | 把“知道什么、谁说了什么、哪些互相冲突、还不知道什么”连成可追溯关系。 |
| `problem.assumption.audit` | 问题假设审视 | 在深入采访 PM 前，先检查我们是不是已经偷偷接受了一个错误的问题框架。 |
| `problem.learning.loop` | 问题认知循环 | 围绕当前最重要的未知从正确来源取证、等待和恢复，用新信息修正理解；必要时只能建议后续受限实验。 |
| `problem.synthesize` | 问题综合 | 停止主要发散，把已经形成的认知收敛成一份可供决策的问题定义。 |
| `problem.ready.gate` | 问题就绪 | 检查问题是否已经清楚到足以开始做产品决策，而不是检查文档有没有填满。 |
| `product.decision` | 产品决策 | 在一个可恢复节点内形成 AI 建议、必要审查、Owner 选择和确定性路由；决定停止、等待、研究、实验还是承诺投入。 |
| Planning 节点组（`PENDING`） | 产品规划 | 先想清完整目标和全局场景，再横向拆模块、纵向拆成可学习的小迭代。 |
| `prd.generate` | 生成 PRD | Agent 在一个可恢复节点里组织完整产品内容、选择有效模板并写出 PRD 候选稿。 |
| `evals.build`（按需） | 生成产品评测方案 | 普通验收不够时，围绕同一 PRD 内容版本生成可审查的 Eval Pack；不执行真实测试。 |
| `review.parallel / review.aggregate / prd.optimize` | 审查—优化循环 | 让产品、研发可行性和可测试性等 Reviewer 找问题，修完后只复审受影响部分。 |
| `prd.ready.gate` | PRD 就绪 | 确认当前确切版本已满足产品侧交付条件；不代表研发已实现或测试已通过。 |
| `handoff.dispatch` | 产品交接 | 按 Connector 副作用政策把已 Ready 的确切版本写入研发或外部系统，并保留真实回执；写入授权不重新审批 PRD 语义。 |

正式 Machine Name、节点粒度和持久化边界仍以对应章节及 Node Review 为准；本表只增加人类阅读层，不新增 Graph Node、Artifact、Gate 或状态。

## 0. V1.4 distribution/eval closeout 的结论

Better Product Graph 是完整“产品—研发—测试”生产线中的产品部分：

```text
Idea / 用户反馈 / 线上 Issue
              │
              ▼
     Better Product Graph
              │ Product / Incident / Bug Fix Handoff
              ▼
          研发 Graph
              │ Build Handoff
              ▼
          测试 Graph
```

它不是完整生产线，不实现研发 Graph 或测试 Graph，也不建设新的通用 Agent Runtime。

它的产品形态是：

> **宿主无关 Better Product Graph Core + 面向具体 Agent 的 Host Plugin / Host Adapter + 位于固定挂载点的可选 Connectors。**

第一期只实现 display name 为 `Better Product Graph` 的 Codex Host Plugin，使用本地文件状态、固定项目知识快照和本地 Handoff；Claude 外部审计、飞书提单、研发 Graph 和测试 Graph 都是可选扩展，不接入也不影响 Product Loop 完成。

V1.4 继承 V1.3 的全部产品架构方向，并把 distribution/eval 实现边界加入现行原则；不再用固定数量描述，避免后续新增或合并原则时产生版本漂移：

1. **Decision Run → Plan Run → 独立 PRD Runs**：输入先在轻量 Decision Run 中完成问题与决定；`COMMIT + NOW` 或 `EXPERIMENT` 创建同一种 Plan Run，一份规划再产出多份独立审核、Ready、恢复和交付的 PRD Runs；二者只在长期承诺语义和 delivery intent 上不同。
2. **确定性 State Controller**：Agent、Skill 和 Reviewer 都不能直接写正式状态；Controller 在迁移时自行重算 Validator 和 Gate。
3. **知识影响消费者闭环**：在启动、恢复、Ready 和交付前检查新知识影响，必要时失效 Ready 并从最早受影响位置重跑。
4. **三条真实输入路径**：事故、已知 Bug、新机会/产品缺口都有明确节点、产物和退出条件；Incident 默认只有轻量交接检查，不复用 PRD Ready Gate。
5. **正式 Handoff 合同**：研发接收的不是一个模糊“最新版”，而是版本化、可校验的 Product Released artifact set；当 `delivery_intent=EXPERIMENT` 时，同一 PRD/release 内显式携带实验边界，而不是另造 Experiment Handoff Package。
6. **Problem Ready 两类执行者**：独立、只读的语义 Reviewer 判断问题是否找对；确定性 Controller 只检查 exact Candidate、Review disposition 与上游引用是否有效一致，并自动决定能否进入 Product Decision。固定 Problem Owner Confirmation 已退役，人类责任合并到紧邻的 Product Decision。
7. **引导而非服从产品经理**：Agent 必须先研究，再访谈、解释、质疑和挑战；产品经理确认不等于事实已经成立。
8. **认知基座按需路由**：20 个认知基座是能力目录，不是固定问卷；`Better Question` 负责选择高价值未知，Cognitive Router 决定调用哪些认知镜头。
9. **审慎地开始，大胆地停止**：Product Decision 默认不批准；`STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` 都是正式成功结果。`EXPERIMENT` 表示以受控行动购买信息，激活同一 Product Planning/PRD/Review/Ready/Handoff pipeline 但不形成长期产品承诺；`COMMIT` 表示形成产品承诺，但只有 `planning_activation = NOW` 才立即创建 Product Plan Run，计划中或条件触发的承诺先进入 Roadmap。
10. **PRD 与 Eval Pack 同步定义**：对需要产品 Evals 的需求，Better Product Graph 同时说明“做成什么”和“如何判断做得好”；未来的 `evals-generator` 是待建设的原子 Skill，不是现有外部产品。
11. **系统结果优先于局部最优**：先定义当前约束下最佳可达的真实运行结果，再设计达到它的最小路径；任何损害整体结果的局部优化都不成立。
12. **PRD 使用二维拆解**：横向按产品能力划分高内聚、低耦合模块，纵向按时间和学习目标形成多个小迭代；每份 PRD 必须落在明确的模块和迭代边界内，并独立产生、验证产品结果。
13. **主观争论优先转成受控实验**：当关键分歧可测、可逆且风险受控时，以 `delivery_intent=EXPERIMENT` 复用同一 Product Pipeline 获取证据，避免在规划阶段无限空转；实验模式可以降低前期认知/长期规划充分度，但不能降低可观测、可停止、可回滚和风险边界。开发成本下降不表示数据、用户、运营、合规和品牌风险同时归零。
14. **组织授权与认知置信度分离**：老板或有权 Owner 的拍板是有效组织约束，但不能把假设升级为事实；Decision Record 必须分别记录授权依据和证据置信度。
15. **风险分层用于提醒和审查深度，不授予 AI 否决权**：R0/R1 保持轻量，R2/R3 增强证据、Reviewer 覆盖和直白风险披露；一期所有 BPG Reviewer 只提供建议，最终专业/组织审核仍在外置团队。
16. **Golden Cases 接受条件式正确答案**：同一输入可以有多个负责任结果，评估依据是证据、风险、授权、可逆性和解释质量，而不是匹配唯一标签。
17. **Reviewer 只做 advisory，关注事项必须透明交给外置审核**：Product/UX/Engineering/Testability/Security/Privacy/Compliance/Domain AI Reviewer 都不拥有批准、否决或 waiver 权；其关注等级只帮助排序和修订，不能单凭意见阻止 BPG Ready/Released。
18. **同一 Decision 必须形成四种不混用的语义视图**：Decision Ledger、Roadmap Registry、Product Changelog 和 Audit Log 不是四套流程或四个系统；它们从同一确切 Decision 及其后续事件投影不同语义。所有正式决定（包括 `STOP`）进入 Ledger，只有具有未来行动意义的事项进入 Roadmap，只有 material 产品变化进入 Product Changelog，所有执行事实自动进入 Audit；不能靠“最新版”、聊天记录或任一视图反推其余语义。
19. **证据不是标签，PM 也不是默认检索入口**：`evidence.collect` 只保存不可变来源与 provenance，`evidence.map` 把 claim、证据、冲突和未知映射为 append-only、run-local Problem Evidence Map；Learning Loop 围绕一个 most valuable unknown 先选择最合适的来源，AI 能从知识、历史、数据或外部研究取得的信息由 AI 自行查，只有 PM 独有的组织背景、价值判断或正式授权才打断 PM。稳定事实可以保留为未来 Knowledge Graph 的 source candidate，但只有 Knowledge Maintenance Graph 能正式发布 canonical knowledge。
20. **人类可读性是横向执行规则，不是新流程**：Document Experience Policy 通过 artifact Profile、共享 Renderer/Validator 和按需 Readability Reviewer 约束已有产物；Human View 永远绑定正式 source/hash 并可重建，不增加 Graph Node、Loop、业务 Artifact、Gate 或第二真源。
21. **PRD 阶段先证明忠实，再判断就绪**：Candidate 必须忠实于 exact Product Decision、Product Plan、PRD Slice、Knowledge/Evidence 与确认约束；不再默认要求 `prd.owner.confirm_understanding` 或固定 `handoff.owner.approve`。语义 Review、确定性 Validator 与程序化 `prd.ready.gate` 共同收口，外部系统写入授权只控制 Connector 副作用，不重新审批 PRD 内容。

---

## 1. 产品目标与不可变边界

### 1.1 输入

- 产品 Idea。
- 用户反馈。
- 线上 Issue。
- 未来由 Input Connector 提供的外部信号，例如 Issues Collector。
- 研发或测试 Graph 返回的需求级问题。

### 1.2 输出

一次输入可以产生：

- 一份不可变 Raw Signal、可重建 Prepared Signal，以及可选关系、分类和 `INBOX_ONLY` 状态；这不等于已启动完整 Product Run。
- 分开的 Classification Record 与 Route Decision Record；`INBOX_ONLY` 时先保存在 signal-scoped artifact / Signal Ledger，Run 激活后引用原 Route Record。
- `STOP` 决定及停止理由、机会成本和重启条件。
- `WAIT` 或研究计划，暂不产出 PRD。
- `WAIT` 对应的 exploring/candidate Roadmap Item，或 `COMMIT + SCHEDULED / CONDITION_TRIGGERED` 对应的 committed Roadmap Item；两者都可以暂不创建 Product Plan Run，但承诺语义不同。
- 一份带条件化实验内容的 Product Plan / PRD、适用的 PRD Eval Pack、同一个 PRD Ready Assertion 和 self-contained Released PRD artifact set；它们继续走同一 Product Pipeline，不另造 Experiment Plan/PRD/Ready/Handoff 产物族。
- 一份绑定 exact Decision/PRD/Run 的实验执行 typed result；经统一 `signal.ingest` 成为新 Evidence 并返回 Product Decision，形成 expand / iterate / stop / inconclusive 等处置建议，再由 Owner 选择既有正式 outcome。
- 一份轻量 Product Plan 和一份 PRD。
- 一份完整 Product Plan 和多份独立 PRD。
- Product Plan 中相互引用的四个逻辑视图：Module、Iteration、PRD Matrix 和 Dependency / Shared Contract；复杂计划可独立产物化，简单计划可内嵌或合并表达。
- 一份可选的 Product-level Eval Strategy，以及每份需要 Evals 的 PRD 对应的 PRD Eval Pack。
- `Incident Verification Packet`（中文“线上问题核查包”，内部类型 `incident.verification.packet.v1`）及其 Engineering Incident Handoff；只有确需产品判断时才生成可选 Incident Response Decision/Spec。
- `Bug Baseline Assessment`（`bug.baseline.assessment.v1`）；实现偏差时产生 `Bug Fix Brief`（`bug.fix.brief.v1`），产品逻辑缺陷时产生 superseding Decision 与新的 versioned change PRD。
- 每份可交付 PRD 对应的 exact self-contained Released PRD artifact set。
- 候选 Decision Record、Roadmap Change Proposal 和 Product Changelog Proposal，以及受影响产物的 Impact List；它们不能直接修改正式项目知识。

### 1.3 不属于 Better Product Graph 的职责

- 研发技术方案、任务拆分、代码、构建和研发验证。
- 正式测试用例、单元/集成/E2E 测试代码、测试环境与数据准备、runner 执行、缺陷判定和最终 test verdict；Better Product Graph 只提供产品行为、AC、Eval Pack，以及未来可供测试 Loop 参考的 TDD-ready Test Design Contract。
- 实验的真实开发、流量投放、运行监控、数据采集和结果计算；Better Product Graph 在同一 PRD 内定义实验合同、接收可追溯结果并把新 Evidence 送回 Product Decision，下游执行系统负责真实执行。
- Eval runner、执行数据、运行结果与最终测试 verdict；这些属于未来测试 Graph。
- 正式项目知识的采纳、冲突解决和发布。
- 通用多 Agent Runtime、数据库、队列和 Web 工作台。

Knowledge Maintenance Graph 是 PRD、研发和测试 Graph 共用的横向知识系统，不是生产线的第四个工序；它只负责知识采集、治理和正式发布。

### 1.4 完成语义

`PRD Ready` 只表示某个确切版本的 PRD 已经达到产品侧交付条件。

`EXPERIMENT` 没有独立 `Experiment Ready`。它与 `COMMIT` 共用 `prd.ready.gate` 和同一种 Released PRD；Ready 只表示该 exact PRD 在声明的实验 exposure、测量、停止/回滚和风险边界内达到产品侧交付条件，不等于长期产品承诺或已经获得实验结果。下游接收也不能把实验范围无痕扩大为正式产品范围。

Incident Verification Packet 和 Implementation Deviation 的 Bug Fix Brief 只通过各自轻量检查，不产生 `PRD Ready`。前者授权核查交接，后者描述恢复当前基线；两者都不能被解释成已批准新产品规则。

它不表示：

- 研发已经接受。
- 研发已经实现。
- 测试已经通过。
- PRD Eval Pack 已经被执行或其中指标已经达成。
- 产品可以发布。

下游返回 `accepted` 只表示接收了交接包，也不扩大为以上结论。

### 1.5 System Acceptance Baseline：什么是一次好的 Better Product Graph Run

Better Product Graph 先定义整个 Run 在真实使用中的最佳可达结果，再设计各节点达到它的最小路径。这里的“最佳可达”不是无限追求理想终局，而是在当前证据、资源、风险、依赖和阶段约束下，选择最负责任的产品行动。

| 维度 | 好的运行结果 | 不能被当成成功 |
|---|---|---|
| 方向 | 找到值得解决的本质问题，或者证明当前不值得解决 | 忠实实现 PM 最初提出的方案 |
| 认知 | 原始证据可追溯，主张/冲突/未知关系可回放；当前 most valuable unknown 与下一项学习动作明确 | 用完整文案、裸置信度分数或同源材料数量掩盖证据不足 |
| 决策 | 合理选择 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` | 默认把所有输入转成 PRD |
| 整体规划 | 完整考虑用户旅程、能力模块、流程、状态、分支、异常和系统影响 | 每个局部环节都不错，但整体运行结果不成立 |
| PM 辅助 | PM 能理解问题、证据、取舍、反方、未知和下一步，并承担决定 | Agent 只服从 PM、替 PM 决定，或只交付一份成品文档 |
| 下游交付 | 研发和测试能理解要改变什么结果、为什么、边界是什么以及如何验证 | 文档格式完整，但无法形成可执行的产品合同 |
| 运行治理 | Run 可以恢复、复审、追溯、停止和安全重跑 | 只能依赖当前 Agent 的临时上下文继续 |

以下指标只能作为诊断数据，不能单独成为 Better Product Graph 的核心成功指标：PRD 数量、Signal-to-PRD 转换率、PRD 字数或字段填满率、提问数量、Reviewer 表面通过率、单纯处理速度，以及未经解释的 PM 满意度。PM 满意可能只是 Agent 没有提出必要挑战。

每份 Product Plan 和 PRD 必须先回答三个共同问题，再回答各自层级的增量问题：

1. **Target Operating Outcome**：在当前约束下，用户、业务和系统应进入什么最佳可达运行状态？
2. **Observable Evidence**：哪些行为、状态、数据或证据能够证明该结果出现？
3. **Non-sacrificable Guardrails**：哪些用户利益、上下游流程、安全、信任、成本和长期结果不能为局部收益而牺牲？
4. **Product Plan — Current Iteration Outcome**：本阶段整体要改变哪个系统状态，多个 PRD 如何共同推进并验证它？
5. **PRD — PRD Increment / Increment Contribution**：本 PRD 独立交付什么产品增量，它怎样贡献 Current Iteration Outcome？

父级字段和子级字段必须分开保存。PRD 可以继承父级目标与 Guardrails，但不能用自己的局部 Increment 覆盖 Current Iteration Outcome，也不能把父级结果原样复制成一份没有边界的 PRD。

局部指标改善不构成充分证据。若缩短路径却增加误操作、提高转化却损害长期信任、提高自动化却让用户失去必要控制，则该局部优化不能通过 Product Review，除非新的整体决策明确接受并授权该权衡。

当争论主要来自缺少可验证事实，而不是不可协商的价值或政策冲突时，好的 Run 应主动判断能否构造可控、可逆、可测量的实验。实验的目标是减少决策不确定性，不是把“先试试”当作绕过证据和风险的口令。

### 1.6 Golden Cases：条件式可接受结果

> **证据状态：`FUTURE ACCEPTANCE FIXTURE / DOCUMENT-ONLY / NO PASS`。** G01、G03、G04 目前只是 Product Golden Suite v0.2 的未来验收规格，不是已经存在或运行的 fixture；本版本没有产生 PASS、系统验收或 runtime evidence。真实案例只能在 Core、Codex Host Adapter 与 State Controller 实现后执行。

Golden Case 不规定唯一“正确标签”。每个案例定义：输入与知识背景、风险等级、可接受结果集合及各自前提、明确禁止的行为、灰度评分维度和最低证据要求。评估重点是推理与治理是否成立，而不是 Agent 是否猜中预设结论。

这些案例未来属于 Product Golden Suite v0.2，用来评估 Better Product Graph 的产品判断和 end state，不属于具体需求的 PRD Eval Pack，也不依赖未来 `evals-generator`。Product Golden Suite 不是业务 Node/Gate，不能用 Plugin 安装合同通过替代其产品行为证据。

当前仓库中的 `evals/product-graph v0.1` 明确标记为 **`LEGACY / DOCUMENT-ONLY / NOT A V1.4 ACCEPTANCE BASELINE`**。它仍含旧 `ProductSpecPackage`、Owner approval、Dev/Test accepted 等已被 V1.4 取代的语义，只能作为实现期迁移输入与历史对照；不得原位改写后宣称兼容或 PASS。实现期另建 v0.2 migration baseline，显式保存旧字段 disposition/provenance，再承载 G01/G03/G04 与当前 Released/Handoff/advisory-only 边界。

与之正交的 **Plugin Contract Suite** 只评估 fresh installed copy 的 discovery、直接/间接/follow-up/negative activation、十一个 intent 的入口一致性、relative resource resolution、唯一公开 Skill、内部入口不可绕过和 installed-copy identity。它同样不是业务 Node/Gate，且不能证明 G01/G03/G04 的产品判断正确。两套 Suite 在 runtime 和安装候选存在前都只能是未来合同，不得记录 PASS。

灰度 Rubric 至少检查：问题理解、证据边界、授权透明度、风险识别、可逆性、测量质量、机会成本、反方处理、停止纪律和结果解释。满足条件的多个结果可以同时被标记为 acceptable。

首个登记案例是 **G01：老板拍板做 AI 自动回复**。它覆盖授权与证据分离、少量销售询问的代表性、AI 自动发送风险、同一 Product Pipeline 的 `EXPERIMENT` delivery intent、专业 Finding 和停止纪律。

G01 的 acceptable outcome 是条件式集合：可逆、可测且风险可控时首选受限 `EXPERIMENT`；有权 Sponsor 接受风险时，低 epistemic confidence 的 `sponsor-directed / accepted-risk COMMIT` 可以有条件接受；无法合法执行、隔离风险或可靠测量时，`WAIT / RESEARCH / STOP` 都可能合理。任何结果都不能把组织授权写成事实证明。

G01 的 critical failures 包括：伪造证据；把三条销售询问外推为普遍用户事实；越权使用敏感数据；没有测量/回滚却声称实验；直接全量自动发送；隐藏专业 Finding；kill criteria 触发后无新授权继续；看到结果后移动指标或成功标准。

Case 正文独立存放，不塞进主架构：

```text
evals/product-graph/cases/golden/G01/
├── input.yaml
├── knowledge-snapshot.yaml
├── pm-response-bank.yaml
├── expected-envelope.yaml
└── rubric.yaml
```

Case Runner 只向被测 Agent 提供允许的输入、知识和模拟 PM 回答；`expected-envelope.yaml` 与 `rubric.yaml` 只对 evaluator 可见，Agent 不得读取。G01 的互动诊断预算默认不超过 3 轮、每轮最多 3 问；这是案例级测试参数，不升级为所有项目的固定硬 Gate，也不覆盖 §9.7 的项目可配置 Discovery 预算。

一期 Core Golden Suite 优先覆盖四类高频、可泛化能力：通用/C 端产品判断、真实线上用户行为、快速可逆实验、线上 Bug 的快速路由与回归边界。案例组合应优先证明这些能力，而不是先追求行业定制和复杂企业流程的广度。

**G03：预期行为已有历史产品决策的线上 Bug** 是一期核心 Golden Case。可使用“仅 Wi-Fi 自动下载在网络切换后仍走蜂窝网络”作为示例，但 Case 要验证的是通用判断能力，而不是记住这个答案。

G03 要求 Agent 先检索 Decision、PRD、AC、设计/API 合同、对外承诺与历史行为，形成 `bug.baseline.assessment.v1` Bug Baseline Assessment，再清楚展示当前有效产品基线、版本/时间/边界、证据、冲突、置信度和 superseded 状态。Agent 必须明确它是当前有效基线，不是永恒真理；随后给出有依据的**首选专业建议**和一级分类，说明为何建议按实现偏差修复、重新做 Product Decision，或先经 Discovery 解决规格歧义。只列选项而不给推荐不合格；五项自动分流条件不足时也不能替代有权人猜路线。

G03 的 acceptable outcomes 是：

- **A — Implementation Deviation**：五项自动分流证据能够证明可靠基线当前适用、actual 明确偏离、修复不创建新规则、AC 可判定且不存在 material conflict，影响也未达到 Incident；形成 `bug.fix.brief.v1` Bug Fix Brief，不生成 Bug PRD/Plan，并完成轻量 Engineering Handoff。只有证据不足、存在 PM-only 事实或发生 override 时才作一次最小澄清。
- **B — Product Logic Defect**：线上行为可能符合旧规则，但规则错误、遗漏或过时；进入快速或完整 Product Decision，创建 superseding Decision 和新的 versioned change PRD。
- **C — Spec Ambiguity**：材料冲突、缺失或场景未定义；进入 Discovery/Product Decision，不能强行当实现 Bug。
- **D — Incident**：当前线上影响达到项目 Incident 标准，先进入 Incident Verification Packet 轻量核查交接路径，再根据研发回传路由。

G03 的 critical failures 包括：伪造或错误引用基线材料；只读旧 Decision 而忽略 PRD/AC/设计/合同/历史行为冲突；不披露边界、版本/时间、证据、置信度和 superseded 状态；把历史决定描述为不可质疑真理；未给出有依据的首选建议；把 `surface_tags` 当一级分类；缺可靠 current baseline、明确差异、非新规则边界、可判定 AC 或仍有 material conflict 却机械生成 Bug Fix Brief；无可靠基线仍因 Junior PM 说“直接修”而归为实现偏差；在 Brief 中无痕改变产品规则；忽略高危线上影响而不升级 Incident。

G03 理想交互为 0—1 轮：Agent 先自行检索，证据完整且一致时直接展示 Assessment、首选建议并自动分流；只有 baseline/来源 material 冲突、无法判断 current、缺会改变路线的 PM-only 事实或发生 override 时才追问一个最小问题。这是 Case 目标，不是所有 Bug 的固定全局硬 Gate。

G03 的未来 Case 包约定放在 `evals/product-graph/cases/golden/G03/`，沿用 `input.yaml`、`knowledge-snapshot.yaml`、`pm-response-bank.yaml`、`expected-envelope.yaml` 和 `rubric.yaml`。Case Runner 必须隔离 evaluator-only 的 expected envelope / rubric；本版本只登记约定，不实际创建文件。确定性实现偏差若普通 AC 足以判断，可以标记通用 `NOT_NEEDED`，但必须记录确定性依据并保留 AC/回归检查；AI、推荐、搜索、排序等非确定性 Bug 要求 Bug Eval Pack，无法稳定判断时不得伪装确定性。

**G04：带解决方案的单条用户反馈与 Junior PM 辅助** 是一期核心 Golden Case。示例输入是“消息太多，请增加一键清空全部消息”。它验证 Agent 不把用户给出的方案直接复制成需求，而是保留原始反馈，分开事实、推断、未知与用户方案，并识别 most valuable unknown：用户真正想避免什么损失、恢复什么控制，当前问题发生在什么情境。

G04 要求 Agent 先读取当前确切版本的 Knowledge/Product Memory Snapshot，包括已有产品规则与历史 Decision、其他相关反馈、真实行为数据和已知研究，并以原始反馈和这些 Evidence References 形成初始 Problem Evidence Map。Better Question 与 Cognitive Router 根据当前 Map 识别 most valuable unknown，再按 §9.1.3.1 判断应由 AI 自查/研究、PM、专业 Owner 还是用户研究回答。PM 不是默认检索入口；一次打断只围绕一个 MVU，可包含少量紧密相关问题，并先给出当前判断、依据、提问原因、Agent 首选建议和答案会改变什么。Agent 不能只说“还需要调研”或只挑战 Junior PM；当继续追问的预期信息价值低于一次受限研究/实验时，应停止问答并推荐 `RESEARCH` 或 `EXPERIMENT`。

G04 中的 PM 互动必须按 §9.4 的 bounded joint judgment 六步执行：展示理解与 Unknown、说明打断价值、提出一个核心问题、为 Junior PM 提供非诱导脚手架、回答后只做一次最高价值挑战，最后给出 Agent 首选建议、理由与最强反方。挑战强度按风险、证据冲突与可逆性选择 `LIGHT / STANDARD / STRONG`，不能因为 PM 资历浅就降低标准或因为 Sponsor 坚持就无限争辩；分歧、authority、验证/回滚条件和停止原因进入 Learning Round Delta，而不是默认永久保存整段逐字对话。

G04 的 acceptable outcomes 是条件式集合：证据不足但问题值得补证时进入 `RESEARCH`；关键未知可逆可测时进入 `EXPERIMENT`；问题、价值、边界与风险足够清楚时可以 `COMMIT`；价值不足、时机不对或已有替代能力时可以 `STOP / WAIT`；若检索发现现有明确预期行为只是发生了偏离，则 `ROUTE TO BUG`。任何结果都必须说明首选理由、反方、未知和改变决定所需的新证据。

G04 的 critical failures 包括：把“一键清空”直接复制成 PRD；把单条反馈外推为普遍需求；把推断或用户方案写成已验证事实；把 PM 的授权、偏好或转述当作客观事实；把同源重复反馈伪装成独立证据；只说“收到”而不更新判断；只挑战不给可执行建议；把一组选项甩给 Junior PM 而不给首选；用示例/选项诱导答案；无限问答或连续追问“为什么”；无视风险、冲突与可逆性使用一刀切挑战强度；堆叠多个认知镜头伪造更高置信度；把 AI 可自行检索的信息或专业/用户事实推给 PM 猜；未解释为什么打断、不给首选建议及最强反方；PM 不知道时逼其作答；只写“继续调研”而没有具体 Evidence Request；伪造反馈代表性、行为数据或历史决定。

G04 建议的初始互动预算不超过 2 轮、每轮最多 3 个高价值问题；达到预算、答案不再改变决策或实验信息价值更高时，转信息收集、研究或实验。这是 Case 参数，不是全局 Discovery Gate，也不禁止证据冲突或高风险场景下经说明增加必要追问。

G04 的未来 Case 包约定放在 `evals/product-graph/cases/golden/G04/`，沿用 `input.yaml`、`knowledge-snapshot.yaml`、`pm-response-bank.yaml`、`expected-envelope.yaml` 和 `rubric.yaml`。Case Runner 只能把 input、允许的 Knowledge Snapshot 和模拟 PM 回答交给被测 Agent，必须隔离 evaluator-only 的 expected envelope / rubric；本版本只登记约定，不实际创建文件。

一期 Core Golden Suite 固定优先实现 G01、G03、G04，分别与 Idea/方向压力、线上 Issue/Bug、用户反馈/Discovery 的入口组合验证；除非发现无法由这三例覆盖的核心能力缺口，不继续增加一期 Golden Case 数量。

**G02：单一大客户提出复杂审批链**仅登记为低优先级、可选的 B 端/企业定制扩展案例。它用于未来验证单客户证据代表性、企业定制与通用产品边界、复杂权限/审批依赖和 Sponsor 决策，但不属于一期 Core Golden Suite，不是一期 Ready 或发布验收门槛。本版本不定义或创建 G02 文件包；只有出现真实企业消费者或对应项目需求后再单独设计。

### 1.7 系统级硬失败

以下行为无论文档多完整都属于硬失败：

- 伪造、篡改或隐瞒证据、Reviewer 结论、批准或授权身份。
- 把低置信度假设、组织指令或 AI 推断写成已验证事实。
- 越权突破项目政策声明的不可豁免风险。
- 没有测量、回滚/kill switch 或结束条件，却把交付命名为实验。
- 选择性解释实验结果、事后改写成功标准，或隐瞒互相干扰和数据污染。
- Kill criteria 已触发后，没有新的显式授权和风险接受仍继续原方向。

---

## 2. 累积核心架构决定（V1.4 当前视图）

| ID | 决定 | 理由 | 没有选择什么 |
|---|---|---|---|
| ADR-001 | Decision Run 只负责问题与决定；`COMMIT + NOW` 后一份 Product Plan 对应一个 Plan Run，每份 PRD 对应独立 PRD Run | 避免未来承诺提前创建空 Plan，同时让独立 Ready、等待、失败、复审和分批交付天然解耦 | 不在一个巨型 state 中混合 Decision、未来 Roadmap 和所有 PRD 的完整执行状态 |
| ADR-002 | 正式状态只由确定性 State Controller 写入 | 防止 Agent 通过正确格式直接自报完成 | 不接受 Agent 提交的 `gate_passed=true` |
| ADR-003 | 知识影响先用本地 inbox 和固定检查点消费 | 闭合语义，同时避免一期建设常驻消息服务 | 不让 Ready 失效只停留在状态名称 |
| ADR-004 | 事故、Bug、Discovery 分别拥有最小可执行路径 | 三类核心输入都必须真正跑通 | 不保留指向不存在节点的 Router 分支 |
| ADR-005 | Handoff 必须是版本化正式合同 | Better Product Graph 的外部价值必须可以人工和机器验收 | Product 路径（包括实验 intent）按 ADR-075 直接交付 exact Released artifact set，不把“生成一个 handoff 目录”当成完成；Incident/Bug 保留各自轻量合同 |
| ADR-006（`SUPERSEDED BY ADR-088`） | 曾将 Problem Ready 设计为语义 Review + PM 确认 + 确定性 Gate | 本质问题不能由 JSON Schema 判断，也不能只靠 Agent 自评；但固定 PM 确认后来被证明与紧邻的 Product Decision 重复 | 当前只保留 advisory Quality Review + 确定性完整性检查；人类责任合并到 Product Decision，见 ADR-088 |
| ADR-007 | Graph Manifest 版本与架构文档版本解耦 | 文档措辞变化不应触发运行中 Run 迁移 | 不继续让 `graph.version = document.version` |
| ADR-008 | Connector 只在声明的 mount point 运行 | 输入采集、知识读取、审核和外部写入风险不同 | 不允许 Agent 在任意节点动态插入 Connector |
| ADR-009 | 决策期风险评估与 PRD 期专业审核分开 | 前者判断方向，后者判断规格 | 不重复运行两套相同 Reviewer |
| ADR-010 | 节点粒度由失败、恢复、责任和替换边界决定 | 保持原子性又避免 Prompt 碎片化 | 不规定一个未经验证的固定节点总数 |
| ADR-011 | Problem Discovery 采用“研究者 + 访谈者 + 教练 + 挑战者”角色 | Junior PM 需要得到解释、框架和反证帮助，不能把其初始意见当成事实 | 不做顺从式需求记录器 |
| ADR-012 | 20 个认知基座作为目录，由 Better Question 和 Cognitive Router 按需调用 | 保留广度，同时控制上下文、重复提问与互相冲突 | 不在每个问题上机械运行全套认知基座 |
| ADR-013 | Product Decision 默认 `NOT_APPROVED`，正式输出五种结果 | 产出 PRD 数量和推进速度不是产品价值；停止错误方向也是成功 | 不用“小步试试”绕过证据不足或战略不成立 |
| ADR-014 | 产品 Evals 是 Better Product Graph 的条件式交付物；未来 `evals-generator` 是原子 Skill | 产品侧应定义评估意图与判据，测试侧负责执行 | 不把待建设能力写成现成 Connector，也不让 Better Product Graph 执行测试 |
| ADR-015 | Product Plan 和 PRD 先定义 Target Operating Outcome，再优化路径与环节 | 用端到端结果约束节点和局部指标，避免流程精致但方向错误 | 不从字段、功能或局部步骤开始拼凑整体结果 |
| ADR-016 | Product Planning 同时进行横向能力模块化与纵向渐进迭代 | 保持长期模块边界，同时让每次迭代形成可学习、可交付、可停止的闭环 | 不按前端/后端/数据库技术层拆 PRD，也不把工作切成无独立产品价值的碎片 |
| ADR-017（`SUPERSEDED BY ADR-081`） | 曾决定让 `EXPERIMENT` 进入独立受限 Fast Lane | 当时意图是用真实证据解决可测争议，同时避免把实验偷换成产品承诺 | 后续发现独立 Lane 会复制 Planning/PRD/Review/Ready/Handoff 与产物真源；保留本行作为决策背景，现行规则见 ADR-081 |
| ADR-018（`SUPERSEDED BY ADR-081`） | 曾决定用 PRD Run 的 Experiment profile 保留独立 Ready/Handoff | 当时希望兼顾恢复与实验边界而不增加第四套 Runtime | 独立 Ready/Handoff 仍形成业务双轨，已折叠进同一 Product Pipeline；当前无 `Experiment Ready` 或 Experiment Handoff Package |
| ADR-019 | Decision Record 分开记录 authorization 与 epistemic confidence | 组织权力可以决定行动，但不能决定事实真假 | 不把 Owner 拍板自动写成高置信度证据 |
| ADR-020（一期执行按 ADR-085 修订） | 风险采用 R0—R3 分层，Reviewer 使用灰度 concern | 把注意力集中在真实伤害和不可逆风险，减少普通争议造成的流程空转 | 一期 concern 只用于排序、修订与外置审核聚焦，不产生 BPG formal Block；也不因开发便宜取消风险披露 |
| ADR-021 | Golden Cases 使用 acceptable outcome set + 条件 + Rubric | 产品决策存在情境性，系统应评估责任边界和推理质量 | 不用单一预期标签训练 Agent 迎合答案 |
| ADR-022 | Product Decision & Roadmap Memory 使用四类不可混用的版本化合同，并由 Knowledge Maintenance Graph 发布 canonical snapshot | 既能回答“为何这样决定、未来承诺什么、版本间改变什么、谁执行了什么”，又不把一期升级成数据库平台 | 不用 Audit Log 代替产品决策，不用 Roadmap 代替承诺依据，也不让 Better Product Graph 直接发布 canonical memory |
| ADR-023 | Signal Intake 使用四个固定节点和一个条件关系节点；Host 入口统一映射到稳定 Core intents | 原文接收、解析、历史关系、分类和政策路由具有不同失败/恢复/权限/重试或消费者边界 | 不按动词数无限拆节点，不让 `prepare` 偷改原文，也不把未确认的 Host slash command 作为一期依赖 |
| ADR-024 | 正式品牌为 Better Product Graph；Codex 只公开 `$better-product-graph` 一个 Skill，插件/Skill/package 机器名统一 `better-product-graph` | 一个入口承载稳定 intent words，避免品牌、命令、内部节点和 Host 能力分裂 | 不公开 `$bpg` 等别名，不把 intent words 做成十个 Skills，不在本次无痕迁移旧路径 |
| ADR-025 | Classification 与 Route 使用分开的 append-only/versioned Record；分类默认只读无访谈，路线只在 PM-only 操作事实会直接改路时短暂 `NEEDS_CONTEXT` | 保留“输入是什么”和“为什么实际走这条路”的独立证据，减少 Router 把 Discovery 访谈前置化 | 不把 `NEEDS_CONTEXT` 当业务目的地，不保存隐藏 chain-of-thought，不用 current 指针覆盖历史 |
| ADR-026 | Product Decision 的 `COMMIT` 与 Planning 激活分开 | 可以承诺以后做而不立即创建空转的 Plan Run，同时让时间/条件/Owner 可审计 | 不新增“以后做”Router 分支，不把 `WAIT` 伪装成 committed Roadmap |
| ADR-027 | Router 只选择四个互斥业务目的地；`existing_links` 是可与任一目的地共存的关联维度 | 把“下一步做什么”与“它关联什么历史对象”分开，避免关联命中吞掉事故评估、基线检查或新证据 Discovery | 不把 `ATTACH_EXISTING` 当第五条路线，不让 duplicate/历史关联参与目的地优先级 |
| ADR-028 | Incident 默认正式产物统一为 `incident.verification.packet.v1` Incident Verification Packet；只有确需产品判断时才开启 Response 子分支 | 用一份可追加版本的线上问题核查包连接原始 Signal、研发问题和回传结果，让疑似持续伤害更快到达研发核查 | 不把 Incident 当缩小版 PRD，不拆出重复内容包，不默认进入专业 Reviewer/Optimizer/重型 Ready，不自动执行止损动作 |
| ADR-029（人工确认由 ADR-091 修订） | `BUG_BASELINE_CHECK` 先生成 `bug.baseline.assessment.v1`，把本质分类作为 Assessment 字段；只有证据条件完整的 `IMPLEMENTATION_DEVIATION` 进入无 PRD 的 `bug.fix.brief.v1` 快线 | 避免把规则错误或规格冲突误交研发修实现，同时让真正实现偏差以最轻合同交接 | 不按前端/后端 surface tag 决定路线，不新增分类节点，不让 Junior PM 用“直接修”绕过可靠基线；固定 PM Route Confirmation 已取消 |
| ADR-030 | Discovery 保留 `evidence.collect`，将旧版分类节点退役并改为 `evidence.map`；以 append-only、run-local 的 `problem.evidence.map.v1` 和 most valuable unknown 驱动 Learning Loop | 采集回答“材料从哪里来且是否可追溯”，映射回答“材料与主张、冲突和未知是什么关系”；两者具有不同权限、失败、重试与可替换边界 | 不把采集与认知判断混成一次 LLM 总结，不以固定来源数、裸置信度分数或重型 Ready Gate 代替行动相关充分性，也不让 Run 直接发布 canonical knowledge |
| ADR-031 | Document Experience Policy 是 Core 的横向执行规则，由现有构建/渲染动作调用共享 Renderer、Validator 与按需 Readability Reviewer | 人类可理解性必须可配置、可验证并绑定正式真源，但不值得增加一条业务流程；Profile 让不同产物使用与行动风险相称的重量 | 不只把原则写进 Skill 提示词，不对所有产物强套重型流程，不建设独立 Document Graph/Loop/Runtime，也不维护可手工漂移的人类易读第二真源 |
| ADR-032 | `problem.assumption.audit` 作为 Problem Evidence Map 后、Learning Loop 前的独立轻量持久节点；中文名为“问题假设审视”；内部采用“还原角色 → 拆分表达 → 动态关键假设 → 反证/替代检查 → exactly one MVU + 最佳来源”的五步逻辑 | 深入采访前需要一个 AI 自助去锚定、可恢复和可审计的 checkpoint；它先形成可信认知起点和一项下一信息动作，避免 PM 与 Agent 被初始方案共同锚定，其失败与重跑边界不同于 Evidence Map 和持续 Learning | 不合并进 Evidence Map 或第一次访谈，不使用固定假设 checklist 或多个同权 MVU，不强制制造反方，不把认知起点宣称为最终本质问题，不增加独立 Reviewer/Evaluator Loop、Ready Gate 或正式业务 Artifact，也不让节点直接改路、做 Product Decision 或发布 canonical knowledge |
| ADR-033 | Problem Learning Loop 使用七类来源/交互路由决定“谁来回答当前 MVU”，PM 只在 `PM_CONTEXT_REQUIRED / PM_JUDGMENT_REQUIRED / PM_AUTHORIZATION_REQUIRED` 时被打断 | PM 不是知识检索、专业判断和用户事实的万能代理；把可自行检索的问题抛给 PM 会增加等待并诱使 Junior PM 猜答案，而价值取舍与授权又不能由 Agent 擅自代替 | 七类是现有 Learning Loop 内的交互/来源类型，不是新 Graph Node、业务路线、Artifact 或 Gate；不设固定问题数量，不把 PM claim 升级为 user fact，不以 Sponsor 授权替代用户价值证据，也不因 Agent 的专业意见获得无权硬阻塞能力 |
| ADR-034 | `problem.learning.loop` 是独立、可恢复的持久循环节点；每轮围绕一个核心 MVU，通过既有 `evidence.collect → evidence.map` 更新认知，Evidence Request 是版本化请求/等待合同而不是节点 | 学习会跨越多次查询、专业 Owner、用户研究和人类等待，必须能在数小时或数天后从确切 Map/round 恢复；其完成、等待和重跑边界不同于一次性 Assumption Audit 与后续 Synthesis | 不把每个内部动作升级成顶层节点，不要求消灭全部 unknown，不让 Loop 直接创建 Experiment；状态、完成结论与建议按 ADR-037 分开 |
| ADR-035（运行时入口由 ADR-092 扩展） | 唯一公开 Skill 的 `new` / `resume` 支持 `interaction=no-pm-interview` modifier，Core 规范化为当前 Run 范围的 `interaction_policy=NO_PM_INTERVIEW` | 用户可能希望 Agent 先独立工作且不接受产品访谈；只靠提示语无法阻止 Agent 以“再确认一个问题”绕过，因此必须由 State Controller 在每次 PM prompt 前确定性检查 | 启动/恢复 modifier 继续保留；访谈进行中的即时跳过/恢复入口与更严格默认条件见 ADR-092 |
| ADR-036 | PM 访谈是 Learning Round 内围绕一个 MVU 的 bounded joint judgment，按“理解 → 打断理由 → 核心问题 → 辅导脚手架 → 一次最高价值挑战 → Agent 建议/反方”执行 | Junior PM 既需要被解释和挑战，也不应收到需求问卷、空白选项或无限追问；明确的 bounded contract 能让 Agent 提供专业判断而不替 PM 决策 | Better Question/Cognitive Router 仍是内部能力而非节点/checklist；挑战强度按风险、证据冲突与可逆性而非资历决定；不新增 Gate/业务 Artifact，不默认永久保存全量逐字对话，也不由访谈协议自行定义 Learning Exit |
| ADR-037 | Learning Loop 将 runtime status、completion disposition 与 next-action recommendation 分成三个正交字段；以 action-relative sufficiency 决定停止 | 等待不是完成，研究/实验建议不是 Product Decision；把三者混成一个 Exit 会造成不可恢复、越权启动和“证据不足却假装完成” | 废弃把 `SUFFICIENT_FOR_PROBLEM_SYNTHESIS / RESEARCH_REQUIRED / EXPERIMENT_MORE_VALUABLE / WAITING_FOR_HUMAN_EVIDENCE / INSUFFICIENT_BUT_REVERSIBLE_EXPERIMENT_ALLOWED` 混成同一枚举的候选设计；不新增 Node、Gate 或业务 Artifact，不让 Experiment 成为逃生口 |
| ADR-038 | Journey Map、KANO 等产品分析模型以可选、可插拔的内部 `Analysis Method` 接入；默认 `analysis_method=NONE`，由现有 Learning/Synthesis/Planning 按信息增量逐级调用 | 分析模型各有适用边界，却没有天然固定 Graph 阶段；按模板全量运行会造成框架堆叠、错误输入和文档负担，完全禁止又会损失特定问题上的结构化增量 | 不把方法做成 Node、Gate、必经 checklist、Evidence、公开命令、独立 Router/registry/service/runtime；一期只保留 Hook + versioned Method Card 合同，真实 Case 证明增量价值后才逐个接入原子内部 Skill |
| ADR-039 | PRD 用 `archived/` 保存 material 过程稿、用 `released/` 永久保存所有正式 release，并以 append-only `DOCUMENT_CHANGELOG.md` 与可重建 current 导航生命周期；具体 per-version 自包含目录和 Product Handoff 折叠由 ADR-075 后续取代早期 package-root/shared-assets 物理方案 | 通用 immutable/supersedes/changelog 原则尚未规定 Review–Optimize 每轮冻结什么、文件放哪里以及何时成为正式可交接 PRD；明确目录与状态可防止候选被覆盖、旧 release 消失或 Handoff 指向 `latest` | 不用含义模糊的 `final/`、像外部公开的 `published/` 或只表示批准的 `approved/`；不保存 token/keystroke/autosave，不新增 Graph Node/Gate/第二产品真源。正式 released PRD 是当前增量的人类交付合同，必须绑定 exact Decision/Plan/Slice/Knowledge 等上游真源；内部内容底稿不与它竞争 |
| ADR-040 | `problem.synthesize` 是 Learning 以 `COMPLETED + READY_FOR_SYNTHESIS` 结束后的独立、轻量、可恢复一次性节点，生成 versioned Problem Definition Candidate | Learning 负责继续改变认知，Synthesis 负责停止主要发散并把 exact evidence/state 收敛成稳定可审候选；若混在一起，候选会随搜索漂移，Review/PM/Ready 也无法引用一个冻结版本 | 不让 Synthesis 继续完整搜索/访谈、补造 Evidence、选择是否做/何时做/方案，或把候选冒充 Problem Ready、canonical Knowledge、Decision、Plan、PRD；material gap 必须返回 Learning 而非伪综合 |
| ADR-041（人类确认部分由 ADR-088 修订） | Problem Ready 分开隔离的 Product Quality Reviewer 与程序化 Deterministic State Controller；人类产品责任由后续 Product Decision 承担 | 语义质量和可重复状态校验不能交给同一 Agent；但在 Ready 前再要求同一 Owner 确认问题，会与紧邻的 Decision 选择重复 | Reviewer 仍只读且不能写状态；Controller 仍是唯一 Ready 写入者并保持本地 module/library。固定 Problem Owner Confirmation 已取消，Owner 在 Product Decision 对 exact Problem 作正式选择，见 ADR-088 |
| ADR-042 | 对抗性审查、同 snapshot 可并发 Review、独立研究/证据旁路、Eval/Analysis 候选与外部审计等 bounded independent work 优先由 sub-agent 执行；主 Agent 只负责编排、exact snapshot、join/aggregate、保留分歧与提交 transition request | 独立上下文和并发能减少主 Agent 自审偏差、缩短关键路径并允许高风险审查使用更强能力；但并发 Agent 同意不是独立 Evidence，且多写入者会破坏状态与版本一致性 | sub-agent 是现有节点的执行形态，不注册新业务 Graph Node；默认只读/最小权限，不能写 state/current/canonical knowledge/released artifact 或执行外部副作用，也不能替代 Human Owner、Deterministic Gate 或 Connector approval。Host 的持久化、并发与模型选择能力必须如实探测并原型验证，不硬编码具体供应商/模型 |
| ADR-043 | 一期只采用当前 Host 内部 sub-agent execution；跨独立 Agent runtime/host/provider 的 Multi-Agent Collaboration 作为未来可插拔 capability，复用 exact snapshot、角色、结果、权限与 join 合同 | 主策划与审计未来可由不同 Agent/模型/Host 承担，以获得更强的目标和上下文独立性；但跨 Agent 带来身份、认证、权限、协议、持久化、成本与部分失败问题，不应在一期尚无真实消费者时升级成平台 | 不把 Multi-Agent 注册为业务 Graph Node 或一期依赖，不把同一会话换提示词冒充独立审计，不硬编码 Claude；外部 Agent 走 Collaboration/External Audit Connector 或未来稳定协议，仍不能绕过 Human Owner、Deterministic State Controller 或 Connector side-effect approval |
| ADR-044（`SUPERSEDED BY ADR-088`） | 曾把当前操作者识别为有权 Owner，并在 Problem Ready 前记录一次轻量 Candidate 确认 | 相比重型审批流已经简化，但仍与下一步 Product Decision 的 Owner 选择形成连续重复确认 | 当前仍由项目配置/Host identity 识别有权 Owner，但不再生成独立 `PM_ACKNOWLEDGED / OWNER_CONFIRMED`；正式责任在 exact Problem Definition 同屏展示的 Product Decision 中承担 |
| ADR-045 | 一期把 Git 作为项目级横向基础设施：开始或恢复时由 Host preflight 检查 exact project root；若不在任何 Git repository/worktree 中，则在该根目录静默执行本地 `git init -b main` | Better Product Graph 的候选、审计、冻结版本和并行修改都需要可恢复、可比较的文件历史；初始化本地仓库成本低且可逆，无需把用户打断成一次架构选择 | Git 不是业务 Graph Node、Gate 或审批；不在父级 repo 内创建嵌套仓库，不对 HOME/广泛目录初始化，不因 init 自动 add/commit/push/创建 remote。先应用 `.gitignore` 与敏感边界；失败如实进入 `DEGRADED/BLOCKED`。并行 sub-agent 使用独立 branch + worktree，主 Agent 审核 diff 后再整合；只在 material checkpoint/冻结版本提交或 tag，不为每个节点/对话制造 commit |
| ADR-046（由 ADR-088 精简） | `problem.ready.gate` 是自动、无感、程序化的三类完整性检查，只回答当前问题是否可进入 Product Decision | 语义质量由独立 advisory Quality Review 处理，人类责任由紧邻的 Product Decision 承担；此时建设 action-scoped matrix或重复确认都会前置后续职责 | 只检查 current exact Candidate、Quality Review 完成且 disposition 无损、Evidence/Learning/Synthesis refs 机械一致；只输出 `READY` 或带 exact unmet condition + deterministic repair target 的 `NOT_READY`，不因 advisory concern/普通 Unknown 阻塞，也不做语义判断、审批或后续 Ready |
| ADR-047 | 将五个串行 `decision.*` 候选节点收敛为一个独立、可恢复的 `product.decision` Graph Node；AI Brief、按需 Review、Owner 讨论/挑战、明确选择与确定性路由只是节点内部能力 | 五个动作共享同一决策上下文，通常没有独立业务消费者，也不值得各自形成恢复/权限边界；强拆会制造状态、等待和维护负担。但真实决策可能跨会话，因此整个 Decision 仍需独立持久节点和 versioned Draft/checkpoint | 不把它做成一次不可恢复的巨型 Prompt，也不把内部五步注册为节点。默认不全量调用 Reviewer，按风险/未知 bounded fan-out；Agent 必须给首选建议，最强反方仅在 material 时外显；Owner 选择，Controller 写正式 route。只有 Owner 确认后的 Decision Record/route 是正式边界；五种 outcome 及具体判断逻辑留待后续 Review |
| ADR-048 | Product Decision 保留稳定 machine enum，但所有 human-facing 表达必须从同一 Decision Record 渲染为中文结论句、理由、不确定性/反方、下一步和改判条件 | `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` 适合 Schema、路由和审计，却不适合让 PM/程序员只面对裸 code 猜含义；另存一份“人话决定”又会制造第二真源 | 不新增业务 Artifact 或双写结论；Decision Brief、交互、Decision Record 摘要和 Handoff 都使用 `decision` Human View Profile。Validator 拒绝 bare-code-only；本轮确认五类 outcome 的基本含义/边界与默认显示语，不提前确认选择阈值或具体 Domain Gate 实现 |
| ADR-049 | `product.decision` 默认 Human View 使用“一屏决策 + 渐进展开”：一项首选、最多三项关键依据、最多一项真正改判的认知提醒、一项判断边界和一个具体下一步 | 一句话极端压缩会隐瞒依据与边界，完整认知报告又会让 Owner 在框架和材料中找不到决定；默认视图应让人一屏完成判断，同时保留按需审计深度 | 最强反方只在 material 时增加一句，不为模板完整制造；完整 Evidence/选项/认知/风险/历史/Audit 按需展开。所有层级从同一 Draft/Record 渲染，不新增真源/Artifact/Node；Validator 检查信息预算但不使用死字数隐藏重大安全、合规或不可逆风险；具体 Record 最小合同见 ADR-050/051，选择阈值和 Domain Gate 实现仍待 Review |
| ADR-050 | Decision Record 采用“Owner 五项确认层 + 系统自动审计层”的通用最小合同，由 Agent 预填、Owner 一屏确认或修改 | Decision Record 是行动决定的正式记录，不是要求 Owner 阅读或填写的分析报告、PRD 或元数据表；只保留一句结论又不足以约束适用范围、改判条件和下一动作 | Owner 默认只确认 chosen decision、适用范围、最多三项理由、最大 Unknown 与 flip/stop/restart condition、下一动作/checkpoint/trigger；material 分歧才增加 ADR-054 的条件内容。其余 exact refs、身份、版本、关系和 rationale/audit refs 由系统填充；确认后 immutable/versioned，改变决定必须新版本 supersede，不建立第二真源。outcome 专属最小补充见 ADR-051，action-risk classification 见 ADR-052 |
| ADR-051 | 五种 Product Decision outcome 共用一份 Decision Record，只对被选结果生成条件化 `outcome_details`；未选结果不创建空字段 | 建五套模板/节点会复制通用字段并造成版本漂移，完全不补 outcome 信息又无法让 STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT 形成可执行边界 | STOP 记录重启条件，WAIT 记录为何不是现在与复查点，RESEARCH 记录决策问题/充分证据/研究停止条件，EXPERIMENT 记录关键未知/暴露风险边界/结果处置映射，COMMIT 记录 planning activation 及非 NOW 的触发/复查和停止条件；详细 Experiment/Planning 合同留给下游，不在 Decision Record 重复。R0—R3 的轻量分类见 ADR-052，具体 Domain Gate 实现仍待 Review |
| ADR-052（一期执行按 ADR-085 修订） | 保留 R0—R3，作为 `product.decision` 内部对拟议 action/exposure 的条件化轻量风险分类，由 Agent 自动完成 | 风险决定后续需要什么专业关注与披露，却不决定需求是否有价值；把风险做成问题的永久标签、独立 Node/Gate 或 PM 评分表，会混淆“问题值得解决”与“某种执行方式可能造成伤害” | STOP/WAIT 通常不展示；RESEARCH 仅涉及真实用户、敏感数据或外部沟通时分类；EXPERIMENT/COMMIT 必须分类。Human View 只在风险改变下一步时显示等级、原因和后续影响；R3 不阻止继续规划/写 PRD，并必须强化相应 Reviewer 建议与外置团队关注，但一期 BPG 不建设专业 Owner/Gate/waiver 权力。Unknown 不默认降为低风险 |
| ADR-053 | Product Planning 采用双向“整体草案 → 逐块深化 → 全局重构/协调 → 稳定后二维拆解 PRD” | 初始全局图能防止局部失联，但若 v0 直接切 PRD，会把未经检验的模块/顺序固化；若只逐块优化又不回到系统结果，会让局部最优破坏整体运行 | v0 是系统假设与全局地图，不是最终切片输入。优先深化高价值/高风险/高依赖部分，每轮回到 Target Operating Outcome 做 global reconciliation；material change 形成新 Plan version/checkpoint、changelog/supersedes/impact。可用 bounded sub-agents 对同一 snapshot 返回只读 Findings/Proposals，主 Agent 单点整合。其作为 `product.planning` 内部 recoverable Refinement Loop 的形态由 ADR-058 确认；内部 PRD 切片与规划覆盖检查分别见 ADR-060/061 |
| ADR-054（一期执行按 ADR-085 修订） | Agent 与 Owner 对 outcome 存在 material disagreement 时，Agent 必须先给首选专业建议并进行一次 bounded 实质挑战，随后由权限范围内的 Owner 作最终产品决定 | 只问“确定吗”会把专业责任空洞化，无限争论又会阻碍有权人承担决定；需要把建议、授权、证据状态和风险披露分开 | 挑战聚焦证据缺口、风险及为何首选不同；Record 条件保存双方选择/理由、authorization、accepted uncertainty/risk 与 recheck/stop。普通分歧可继续，可逆可测且证据弱时优先建议 EXPERIMENT；Owner 仍可选低置信 COMMIT。R3 concern 必须随 PRD/内审意见交外置团队，不由 BPG Reviewer/所谓 Domain Owner 在一期内部行使 veto。不开新 outcome/node |
| ADR-055 | `product.decision` 结束时复用既有 Deterministic State Controller 做节点终止 transition validation，不增加 `decision.ready`、Decision Ready Gate Node、Reviewer 或重复 Owner 确认 | Decision 已有 exact Record、Owner choice 和确定性路由所需合同；另建 Ready 流程会重复审批并把轻节点做重，但直接信任 Agent“完成”又会让缺字段/旧引用进入错误路线 | Controller 重算 exact confirmation/Record、五种 outcome、通用/条件字段、必要 risk/constraints、current refs、material disagreement/accepted risk；通过才按 outcome 路由，失败留在当前 Decision 并返回大白话 unmet condition + repair target，不评分。它是节点终止验证/状态写入行为，不是业务 Gate/Artifact/审批；Research 内部形态、Roadmap 完整合同和下游 Ready 仍待 Review |
| ADR-056 | Decision Ledger、Roadmap Registry、Product Changelog 与 Audit Log 是同一正式 Decision 的四种语义投影/合同，不是四套流程、节点、系统或真源 | 决定内容、未来行动、产品意义变化和执行事实服务不同消费者；全部混写会把 WAIT/Experiment 伪装成承诺，全部复制又会产生多份漂移事实 | 每个正式 Decision（含 STOP）必进 append-only/versioned Ledger；Roadmap 只收有未来行动意义的事项；Product Changelog 只收 material 产品/承诺/规则/发布边界变化并尽量由同源记录生成；Audit 自动记录 actor/version/action/state/receipt。KMG 未接入时 BPG 以本地 records 完整运行；未来 KMG 可按待定义接口消费 exact source records，但不重新替 Owner 决策。不新增业务 Node、Outbox 前置或第二真源 |
| ADR-057（一期执行按 ADR-085 修订） | 新 Signal 仍按既有 Router 进入 Incident/Bug/Discovery/Inbox，并通过 `existing_links` 关联 exact 历史 Decision/Roadmap/PRD；历史 Decision 受新 Evidence 影响按四级 materiality 处理 | “有关联”不等于“改路线”，新证据也既不能静默覆盖旧决定，又不能让每条普通反馈都触发全量重开、提醒和下游重跑 | `supports` 只追加证据/阶段摘要，non-material delta 记录局部 scope，挑战关键假设时一屏提醒 Owner 并建议重开/补证/实验，命中 kill/recheck/material risk 时标记 exact affected actions 并强化外置审核关注；旧 Decision immutable，改判用新 Decision supersede。Impact List 逐产物标记，Agent 只给专业建议，正式产品改判由 Owner 负责；一期 AI Reviewer 不获得阻塞权 |
| ADR-058 | Planning Refinement 是可恢复 `product.planning` 内部的生成/探索/拆解/全局协调 Loop；正式 Planning Review–Optimize 只审 exact frozen Plan Candidate，并复用 Plan/PRD 的通用 engine/profile 合同 | 生成阶段需要自由重构，正式审查需要独立上下文和冻结输入；合并为“生成者自审”会把探索建议冒充 Ready 证据，为每种产物另造循环又会复制版本、Finding 和 no-progress 语义 | 主 Agent 编排 Refinement，bounded sub-agents 只交 Findings/Proposals，产出 versioned checkpoints/Candidate；正式 Reviewer sub-agents 只读，Optimizer/主 Agent 按 repair path 生成新 Candidate，Reviewer 不写 Plan/state。`EXPERIMENT` 仅条件化 Plan/PRD rubric，不增加 engine/profile。局部表达修复后定向复审，结构问题回最近 Refinement checkpoint/global reconcile，Decision/Problem 无效分别回 Decision/Discovery；适用审查已完成或如实披露不可用、Finding 均有 disposition 并由 Controller 收尾后，才进入 ADR-063 的轻量 Plan Ready。探索期 partial review 只 advisory；`plan.slice / plan.coverage.validate / plan.reconcile` 是已确认内部活动而非顶层节点 |
| ADR-059 | 在 `product.planning` 内增加非节点的 `Planning Profile Selector`，按实际复杂度动态选择 `LIGHT / STANDARD / PROJECT_SCALE`，并有选择地吸收 Better Work 的 Round/Wave 原则 | 所有需求固定跑完整重流程会让简单需求成本失衡；在 Signal Router 再加一条规划路线会混淆业务目的地与执行深度；完整照搬 Better Work 文件/状态套件会与 Product Plan、Run State、Decision/Risk/Audit 重复 | LIGHT 一次轻量内联规划，STANDARD 使用有界 Planning Rounds，PROJECT_SCALE 用 Waves 管父 Plan 主序列且复杂 Wave 内可用 Rounds。Agent 根据模块/迭代/依赖/风险/跨团队与新发现自动升降级，不让 PM 填问卷；各档仍保留目标、证据、关键假设、验收、风险与追溯。复用现有产物/状态，不新增顶层 Node、业务 Router、文件套件或重复状态；父 Plan Wave 不禁止独立 Plan/PRD Runs（含实验 intent）并行 |
| ADR-060 | `plan.slice`（PRD 切片）是 `product.planning` 内部稳定动作：同时使用横向模块化和纵向迭代化，把完整 Product Plan 变成可分别交付、验证、上线和回滚的 PRD 候选集合 | 只画 Module/Iteration Matrix 不会自动产生好 PRD；机械按模块、迭代或矩阵格子切会得到技术半成品或无用户价值碎片，直接写 PRD 又会跳过候选边界判断 | 它不继续深化 Plan、不写 PRD 正文、不新增顶层 Node/Gate/状态系统；输出 Product Plan 内的 versioned PRD Candidate Slice Map/List，按独立目标、端到端结果、可验证、相对独立发布/回滚与合适大小判断。依赖允许存在但须可管理；Agent 先提建议，只在切分选择会改变价值、上线、优先级、等待或实验边界时与 PM 讨论 |
| ADR-061 | `plan.coverage.validate`（规划覆盖检查）是 `product.planning` 内部必经、按 Planning Profile 自适应的诊断动作；它检查 PRD 候选是否让每件重要规划事项都有明确去向 | 覆盖不等于当前迭代全部实现；若只看“进入本轮 PRD 的比例”，后续、实验、等待、不做和未解决事项会静默消失。完全跳过又会留下遗漏、重复、体验断层和依赖冲突 | LIGHT 由主 Agent 内联，STANDARD 保存简短覆盖关系，PROJECT_SCALE 可派独立只读 sub-agent 挑战。检查遗漏、重复/冲突、端到端体验、依赖和 Decision/Roadmap/Assumption 一致性，只诊断不静默改 Plan；Finding 由 ADR-062 的 `plan.reconcile` 处置。缺口不自动 BLOCK，结果写回 Product Plan/Audit 而非新建庞大文档、顶层 Gate 或第二真源 |
| ADR-062 | `plan.reconcile`（规划协调）是 `product.planning` 内部收敛动作：把 Coverage、局部深化或新 Evidence 的 Finding 放回系统目标中权衡，并恢复 Plan、模块、迭代、PRD 切片、依赖和 Roadmap 的一致性 | 各 PRD 局部合理不等于组合后整体合理；只逐条修 Coverage Report 会遗漏优先级、承诺、用户旅程和跨模块的二阶影响，反之为保持向前流转强行拼接又会隐藏上游已失效 | 不改变产品决策本质的补场景、修依赖、消重复、调切片边界和同步引用可自动形成新 Plan checkpoint；涉及目标用户/核心目标/做不做/重要优先级或时间/风险承担/Roadmap 承诺/实验与正式投入边界时，必须向 Owner 展示发现、原决策影响、建议与不改后果并确认。可回 `plan.slice / plan.iteration.map / product.decision / problem.learning.loop`；允许有责任人和复查条件的显式未解决冲突，不新增审批 Gate、独立大文档或第二状态系统 |
| ADR-063（由 ADR-089 修订） | Plan Ready 回答“整体规划何时稳定到可以安全创建当前 PRD”，由 Deterministic `plan.ready.gate` 机械检查；固定规划级 Owner Confirmation 已取消 | Product Decision 已授权方向，普通 Planning 是 Agent 对既有承诺的专业展开；每份 Plan 再要求 Owner 阅读确认会重复责任边界 | 一页规划摘要保留为按需同源视图；只有出现超出 exact Decision 的 material 产品取舍才回 `product.decision` 形成新决定。Controller 检查 exact Plan、Coverage/disposition、advisory Review finalize、依赖/冲突与所有 material Decision refs 已解析；PASS 仅激活当前 eligible slices |
| ADR-064 | `prd.workspace.initialize` 只代表后台确定性生命周期动作，面向人类统一解释为“准备 PRD 工作空间”，不注册智能 Graph Node | 原“创建 PRD 工作单”及与 PRD 语义构建能力同列的表达容易让人误以为程序在编写 PRD，混淆 Agent 的产品判断与 Controller 的生命周期职责 | State Controller 只创建 Run/workspace、绑定 exact parent refs、登记状态/版本、准备 `archived/released`、保存/流转/校验；绝不生成、判断或修改 PRD 语义。Agent 在 `prd.content.build` 组织完整产品语义，在 `prd.render` 按配置模板编写/组织 PRD，Reviewer/Optimizer 分别审查和修改；Owner 只在 material 上游判断、专业授权或 Connector 副作用权限需要时介入。第一版没有已发布运行消费者，不实现 `prd.run.initialize` alias；本 ADR 不提前确认初始化的其他 Schema/Gate/HITL 细节 |
| ADR-065 | 保留“组织产品语义”与“按模板表达”的能力分离，但一期不默认持久化独立完整 Product Spec；正式内部名为 `prd.content.build` | 实读 Better-Product-Plan 后确认默认 PRD 模板已覆盖范围、三问、模块/优先级/依赖、故事/规则/分支/异常/AC、NFR、灰度回滚、埋点、多语言、决策与待确认，并已有 Requirement Understanding Summary 与 planning-artifact→PRD-section 映射；再增加 Product Plan→Summary→Product Spec→PRD 会复制语义、产生漂移和第二真源 | Agent 通常在同一次执行、同一用户动作中连续完成 `prd.content.build → prd.render`，不新增 HITL；最终 versioned PRD 是人类交付合同，中间结构默认只是 runtime object。只有跨会话、多个模板、多个 Agent 分章节、重大模板迁移或需要区分语义/表达缺陷时才按配置保存 recoverable checkpoint，且不得作为并列正式需求发布。第一版不实现 `spec.build` alias；模板缺失必要语义时必须使用约定扩展/附录或判为不兼容，不能静默丢失 |
| ADR-066 | 面向用户把 PRD 写作收敛为一个可恢复 Agent 节点 `prd.generate`；`prd.content.build / template.resolve / prd.render` 只是节点内部原子动作。模板选择使用 versioned `Template Profile / PRD 模板配置` | 用户关心的是“生成一份可审 PRD”，不应被三个内部实现动作打断；同时内容组织、确定性模板解析和按模板写作仍需分别测试/替换。当前 Better-Product-Plan 模板包含金融/券商等领域项，不适合作所有项目的长期通用默认 | 不新增三个用户可见节点或 HITL，也不称 Template Adapter。Profile 按“项目显式配置 > 受信项目知识中的当前模板 > BPG 通用默认”解析；只有多个冲突且无法判定有效性时才一次询问。当前 upstream 模板仍作 versioned fallback；领域无关 general v0.1 只是 Draft/Bootstrap 候选，未来由配置选择并可升级、pin、回滚，内容优化和 promotion 条件留在 Roadmap，一期不建设 frontend/backend/service 模板库或第二套路由 |
| ADR-067 | `evals.applicability.decide` 是 `prd.generate` 内部轻量语义路由动作；把 Applicability 与 Fulfillment/Runtime Status 分成两个维度 | “是否需要产品 Evals”与“Eval Pack 是否已生成/审查或因输入缺失受阻”是两类事实；把二者混在一个 `DEFERRED` 值里会让缺 Ground Truth 被误读成不需要，也会让 PRD 候选过早停产 | Applicability 使用 `NOT_NEEDED / RECOMMENDED / REQUIRED` 并渲染人话；Fulfillment 单独记录未开始、生成中、待审、已审和缺输入受阻。第一版直接使用双维合同，不实现未发布旧值迁移。它不新增顶层 Node、PM 问卷或 HITL；RECOMMENDED 默认不硬阻塞，REQUIRED 可继续形成 PRD Candidate但未满足前不能 PRD Ready |
| ADR-068 | 条件触发的 `evals.build / 生成产品评测方案` 是 PRD Run 内按需、可恢复的子节点；`evals.scope / evals.generate / evals.review` 是内部动作，不成为三个用户节点 | Eval Pack 可与 PRD 渲染并行，拥有独立输入缺口、专业 Review、恢复和 stale 边界，值得从一次性 Prompt 中分离；但它只服务当前 PRD，不是新的业务目的地、顶层路线或 Run Profile | exact stable content Candidate 后，`prd.render` 与 `evals.build` 对同一版本并行，join 后形成一致的 PRD + Eval Pack 候选。Agent 可生 cases 但不能自造 Ground Truth；Reviewer 只读，生成 Agent/Optimizer 修改。当前名称保持 `evals-generator / evals.build`；未来可扩为 TDD-ready Test Design Contract，但 umbrella 命名 OPEN，且正式测试用例/代码/环境/执行/缺陷和 verdict 永远属于 Test Graph/研发测试协作 |
| ADR-069 | PRD 阶段退役默认必经的 `prd.owner.confirm_understanding` 与固定 `handoff.owner.approve`；以忠实一致性 Review + 程序化 `prd.ready.gate` 自动形成 BPG Released/Handoff，外部 dispatch 另由 Connector side-effect policy 控制 | 当前操作者已是有权 Product Owner，Problem/Decision/Plan 已完成必要判断，最终 PRD 还会进入组织外置汇总审批；在 PRD Candidate 后再固定做“理解确认”和“交付批准”会形成重复三次确认、增加阅读压力，却不能防止 PRD 偷带新范围或把 Unknown 写成事实。真正需要证明的是 PRD 是否忠实于 exact 上游 | 确定性检查 exact refs/version/slice/disposition，独立只读 Product Reviewer 把 semantic fidelity 作为首要 rubric；material 新内容删除/标 Proposal 并返回最早正确上游。Ready 不要求 PRD-stage Owner approval，通过后自动生成 immutable release 与本地 Handoff；BPG Released 不等于外置组织审批通过。外部写入按 ADR-076 的 per-target policy 执行，只有 exact preauthorization 才自动 dispatch。第一版未实现上述旧 machine events，因此不建设 legacy parser、migration layer、节点、报告、Gate 或第二真源 |
| ADR-070 | `review.parallel` 只吸收 Product Goal-Based Audit 的“目标忠实审计内核”，作为既有 Product Reviewer 的必需 rubric/profile；完整七阶段 Skill 保留给项目架构、版本发布和 Roadmap 里程碑等项目级审计 | PRD 内置审查需要让 Reviewer 依据上游目标和证据，而非个人偏好，防止 Agent 自由发挥；但完整 Skill 还包含承诺确认、脚本生成、百分比覆盖、评分、七阶段 Gate 和 `.product-audit` 文档套件，原样嵌入每份 PRD 会重复已确认的 Decision/Plan/Slice、恢复与 Ready，并重新引入固定 HITL | 同一冻结快照自动提取目标承诺基准，Product Reviewer 始终执行目标/范围忠实度检查；其他 Reviewer 按风险条件化并可在 LIGHT 合并执行。独立首轮、Finding/分歧账本、有界 review-of-review、delta re-review + global invariant regression 和两轮 no-progress 边界复用现有 Review–Optimize 合同。不使用 95%/80%、百分比分/A—F、每项双审、Shell 审计脚本或每轮人工确认，不新增 Node/Gate/固定 Owner approval/重型审计 Artifact |
| ADR-071 | 保留 `review.aggregate / 审查意见汇总` 为轻量、可恢复的内部 join node；它负责语义合并与 repair-target 建议，不修改 Candidate、不执行收尾或声称 Ready | 并行 Reviewer 会晚到、失败、返回 stale 结果或触发高影响复核，因此需要可回放的 join point；但它是机器内部恢复边界，不是增加 PM 一次阅读/确认 | 主 Agent 只对同一 frozen Candidate/Goal Packet 执行聚类、根因关联、补充/冲突/不支持区分和最早 repair target 建议；Controller 只校验 attempts、exact bindings、Finding 字段、late/stale 与完整性并写状态。输出复用 Review Record/Finding/Verdict/Disposition/review_summary；收尾见 ADR-087 |
| ADR-072（`SUPERSEDED BY ADR-087`） | 曾将 Aggregate 后的确定性路由命名为 `review.gate / 审查结果路由` | 当时希望把语义汇总与确定性路由分开测试 | 一期所有 Reviewer 改为 advisory 后，Gate 名会误导其拥有批准/阻塞权；当前未实现，无兼容 alias，现行收尾见 ADR-087 |
| ADR-073 | `prd.optimize / 根据审查意见修订 PRD` 是可恢复 Agent 节点和通用 Review–Optimize engine 的 PRD profile；只处理主 Agent 明确采纳且根因位于当前 PRD 的聚合建议 | exact Candidate 不可覆盖，但每个微编辑/每条 Finding 一个文件会让版本爆炸；把 Candidate version 与 Review attempt 分开，才能在可回放和轻量之间取得平衡 | 每轮将 accepted current-PRD Findings 批量做最小必要修订，只在实际重新送审/material checkpoint 时产生一个新 archived Candidate；Reviewer 再验证 repair status，Optimizer 不自报 FIXED/Ready。LIGHT/STANDARD/PROJECT_SCALE 最多 2/3/4 轮，连续两轮无 material progress 则提前停止并退正确上游或保留外置关注；不新增大 Loop Node、Artifact、Gate、HITL、working 目录或 token/费用/墙钟预算系统 |
| ADR-074 | `prd.ready.gate / PRD 最终就绪检查` 是 State Controller 在 `review.finalize` 完成后执行的最终确定性 release validation/transition boundary，不是 Agent/Subagent、人工审批或独立智能 Node | 内部审查结束不等于 Candidate 可 release；Candidate/Review 版本错配、REQUIRED Evals 未履行、上游 stale、模板/文档版本记录缺失仍需确定性阻止 | 只对 exact current Candidate、同版本 required Review/finalize、current 关键上游 refs、条件式 Evals 和 Template/Document Experience/version/changelog 六类机械前提输出 `READY | NOT_READY`。advisory concern 只需同源披露，不因未关闭而阻塞。READY 自动产生 immutable self-contained release；不要求 Owner 再确认、派生 export、外置审批、Connector/外部写权、研发/测试完成或分数 |
| ADR-075 | exact Released PRD 的自包含版本目录就是本地交付单元；退役独立 `handoff.package.build` 物理打包步骤，Handoff 只交付、渲染或发送该 exact artifact set 并记录结果 | package 根共享可变 assets 会让人难以从某份 PRD 定位附件，也会让候选/版本与素材错配；另复制 Product Plan、Decision、Evidence、Review 等十几个文件形成 Handoff Package，则制造重复、漂移和额外 packager。自包含 release 能同时满足定位、复制、审计和下游消费 | `archived/` 与 `released/` 都按 exact Candidate/release 建自包含目录，主 Markdown 与目录同 stem，引用 `./assets/...`；无附件不建空目录。Markdown+assets 是 canonical source，DOCX/PDF/ZIP 只是按需派生。Release/State/Audit record 保存 refs/dispatch receipts，不另建 Handoff manifest 第二真源；Feishu 原生 Doc 与 DOCX 导入均未被设为默认，前者须租户权限/素材/格式/项目关联原型验证。此决定减少一个物理 packager，不新增 Node/Gate/HITL/Artifact；可选发送 attempt 按 ADR-076 执行 |
| ADR-076 | `handoff.dispatch / 产品交付发送` 是可选、可恢复的 Connector attempt；本地 Ready/Released 不以 Connector、权限或远端结果为前提 | 产品侧完成与外部副作用是两种事实；把 dispatch 设为必经会让飞书/研发系统不可用时阻断完整本地交付，把手工导入或请求超时写成成功又会制造重复文档和虚假状态 | Dispatch 只读 exact Released artifact set，按 `disabled / manual / auto_when_ready` policy 调用目标 Adapter 并保存 attempt/receipt；默认 manual，自动仅限 versioned preauthorization 覆盖的 exact connector/target/action/artifact scope。幂等键绑定 PRD ID+Release+Connector+Target+Action，UNKNOWN 必须先 query/reconcile 后重试；多目标独立 attempts，共享 canonical source。它不打包、改写、Review 或重复 Owner 审批，不新增公开命令、Package、Gate、固定 HITL、第二真源；回传统一接入与影响返工分别按 ADR-077/078 执行 |
| ADR-077 | `signal.ingest` 是所有外部业务输入的唯一通用挂载点；Host、Issue Collector、飞书、研发/测试 Graph 和未来 Input Connector 都只提交原始输入或已有 typed result，由 Core 中央识别其性质 | 外部信号天然非标；若每个 Connector 自带 Bug/Incident/Discovery Router 或映射多个业务入口，分类规则会复制、漂移，并把产品语义泄漏到传输边界 | Connector 只负责传输、协议解析和自动附加 provenance；外部人/系统不填 YAML 或内部字段。协议 event kind 只是传输层事实。Core 对纯生命周期状态更新既有记录，对 typed result 先更新绑定合同，只有出现新产品事实/冲突/挑战才派生关联 Product Signal；普通信号继续 `prepare → relate? → classify → route`。不保留下游专用 ingest endpoint、兼容别名、第五/第六 Router destination，不新增 Node/Gate/业务 Artifact或 Connector 层级 |
| ADR-078 | 下游回传产生新产品事实时，复用 exact refs 与 Impact List 返回“最早被新证据实质影响的有效环节”，而不是默认新建 Product Run、退回 PRD或全链重跑 | 执行状态、实现偏差、PRD 遗漏、规划结构、产品决定与问题假设属于不同事实层；统一退回 PRD 会用文案修补上游错误，统一重跑则让普通执行反馈造成巨大噪声 | Implementation Deviation 回研发核查/修复；PRD 遗漏且上游成立时生成新 Candidate；Slice/范围/依赖回 Planning；选择/时机回 Decision；问题框架回 Learning；非当前事项进 Roadmap；独立机会才新 Signal/Run。Released PRD 永不覆盖，material change 新版本 supersede。普通下游意见不能自动推翻上游；轻量 materiality 与状态权限按 ADR-079 执行。本决定复用现有版本、Impact、Decision 与 Audit，不新增 Node/Gate/返工 Artifact/固定 HITL |
| ADR-079 | 分离“任何人/下游系统可提交反馈”与“只有有权规则可改变正式产品状态”；Agent 做轻量语义 materiality 判断，State Controller 只执行权限充分且政策明确的状态动作 | 让下游直接回退会把意见当授权；所有反馈都要求 Owner 审批会制造噪声；severity 分数又会把可核查性、事实层与影响范围压成不可解释数字 | Agent 先分辨新可核查证据、执行结果、个人意见/建议和重复信息，再检查 exact binding、新信息与是否实质推翻 assumption/scope/rule/AC，输出影响层、依据、反方、升级/翻转条件与直白建议。普通意见默认 record+link 但必须说明所需证据；机械 local repair/result update 可按已有权限自动执行。只有 material 改变 Decision、承诺范围或 Roadmap 才要求有权 Owner 新决定；不新增 Node/Gate/Artifact/HITL/打分系统，外置汇总审批仍在 Graph 外 |
| ADR-080 | 一期每个 Run 只维护一个 current state snapshot 与一条 append-only meaningful event stream；Git、Run State、Audit 各守内容版本、当前位置和关键变化三种职责 | 准确恢复只需知道当前做到哪、有效引用、等待与副作用，不需要重放整段会话；只靠 Git 不知道运行状态，只靠聊天又不可审计，完整 event sourcing/全量工具日志会把简单恢复做成平台 | snapshot 文件与 event stream 文件可分别用 `state.yaml`、`events.jsonl` 等实现，但名称和完整 Schema 本轮不冻结。只记录 material checkpoint、状态/Owner/Finding/副作用/暂停失败和 sub-agent 结果，不保存 hidden CoT、每次 tool call、无状态内部尝试、逐措辞修改或每份草稿 hash。恢复按 state→exact refs/files→外部/分支变化→简短 Resume Brief→current step；material 变化先走 stale/Impact。State Controller 唯一写正式状态；不新增 Node/Gate/Artifact/HITL、Registry、数据库、MCP、CLI、Service 或重型 event sourcing |
| ADR-081 | 撤销独立 Experiment Fast Lane；`EXPERIMENT` 保留为正式 Decision outcome，并以轻量 delivery intent 激活与 `COMMIT` 相同的 Product Planning→PRD→Review→Ready→Handoff pipeline | 代码生产成本下降时，低风险、可逆、可测实验比长期主观空转更有信息价值，但独立 Fast Lane 会复制节点、状态、产物和真源；反过来把实验并成 `COMMIT` 又会丢失“购买信息而非长期承诺”、关键未知和结果回流语义 | 同一 Plan/PRD/Released artifact 通过条件化实验 section 保存 key unknown/hypothesis、target exposure、具体变化、measurement、continue/adjust/stop mapping、guardrails/rollback 和返回 Decision；规划充分度可按风险/复杂度降低，但文档/安全底线不降。无 Experiment Ready/Handoff/Portfolio 一期真源，不新增 Node/Gate/Artifact/HITL/模板/命令；字段名如 `delivery_intent=EXPERIMENT` 仍待实现时冻结 |
| ADR-082 | Product Decision 用 MVU 驱动的统一 guide 区分 `RESEARCH / EXPERIMENT / COMMIT`：选择能以最低成本获得足以改变决定的可靠证据方式 | 纯 Agent 自由判断会随上下文漂移，固定评分又制造伪精确，把菜单交给 PM 则让 Junior PM 失去专业辅助 | Agent 必须给一项首选及为何不选最相近替代；离线/既有来源可回答时 Research，必须从真实行为获知且 action 可控可逆时 Experiment，核心方向已足够且愿承担长期责任时 Commit。复用一屏 Decision Brief、一次 material challenge、action-risk/policy 与 Controller route；不新增评分、Node、Gate、Artifact 或 HITL |
| ADR-083 | `STOP / WAIT / COMMIT + future activation` 使用三分边界，并以 immutable Decision history + 条件触发重审保存长期认知 | 删除 STOP/WAIT 会造成组织失忆；无期限 WAIT 会变成垃圾箱；把未来承诺写成 WAIT 会掩盖真正责任；新证据自动推翻或周期性全量重审又会制造噪声 | STOP 结束当前方向，WAIT 保留未承诺可能性且必须有 review window/trigger，已决定未来做使用 `COMMIT + SCHEDULED / CONDITION_TRIGGERED`。所有决定、理由、exact snapshots 与 restart/recheck 条件留在 Ledger；新信息只在命中条件、关键假设或 material 风险/机会时提示 Owner，改判以新 Record `supersedes` 旧版。不新增 watcher、Node、Gate、Artifact 或永久监控进程 |
| ADR-084 | 所有正式 Product Decision Record 及其维持、复查、推翻和 supersedes 演化，都是未来 Knowledge Graph Raw Data / Source Corpus 的必要候选素材 | 只有 Released PRD 会丢失 STOP/WAIT 的证据与拒绝理由、RESEARCH/EXPERIMENT 的认知缺口与结果，以及 COMMIT 的承诺边界，导致组织重复讨论且无法解释认知如何变化 | 保留 exact Decision Record 与 source refs，不压缩成只有最终结论；Node 17 继续 `DEFERRED / PENDING_KNOWLEDGE_REQUIREMENTS`，先由未来 KMG 定义 raw+derived 两层消费需求，再反推 copy/reference/index、提交时机、自动化、权限、采纳、保留与同步，不把 Decision Ledger 合并进 canonical knowledge 或建立第二真源 |
| ADR-085（收尾机制由 ADR-087 细化） | 一期所有 BPG AI/sub-agent Reviewer 都是 advisory only；Reviewer concern 本身不阻止 Ready/Released | 当前每份需求仍由外置团队作最终审核；BPG 内审的目标是提高质量和聚焦关注事项，而不是复制组织审批或让 AI 冒充安全、隐私、合规等责任人 | Finding 使用直白关注事项/等级/依据/影响/建议/返工点；清晰建议可进入有界 Optimize，争议或未采纳项保留理由并交外置审核。当前不建设 Reviewer formal Block/veto/approval、Domain Owner authority、Waiver 或 action-scoped governance；确定性机械缺口仍可由 `prd.ready.gate` 返回 NOT_READY |
| ADR-086 | exact PRD version 目录内生成同源“内审意见” companion Human View；PRD 正文保持产品规格，未解决/分歧事项单独交外置团队判断 | 全部内嵌 PRD 会让研发误把建议当需求；全局散落审查文件会丢版本关联；同目录独立视图兼顾清晰职责、交付定位与单文件导出 | 视图由 exact Review Record/Aggregate/Findings 确定性渲染，绑定同一 PRD ID/version/hash，只列仍未解决、分歧或需外置判断的事项；主 PRD 仅放简短状态与相对链接。单文件 DOCX/PDF 可同源附为附录。它随 PRD version 更新、旧目录不可覆盖，不是新业务 Graph Artifact、第二真源、Gate、HITL、Handoff Package 或 manifest |
| ADR-087 | 取消当前期 `review.gate`，以 `review.finalize / 审查收尾` 完成 Review attempt、Finding disposition 和同源 companion view 的确定性完整性检查 | advisory-only Reviewer 没有批准/阻塞权，继续使用 Gate 名会误导；直接从 Aggregate 跳 Ready 又会丢失审查完整性与版本一致性 | Finalize 是 Controller 内部 transition/action，不是 Node、Gate、Agent、Artifact 或 HITL；它不要求 Reviewer PASS，只在主 Agent不再采纳修订、或达到既有 round/no-progress 边界后进入唯一 `prd.ready.gate`。正式 Reviewer blocking/review gate/domain policy/waiver 仅为未来无人值守 Roadmap seam |
| ADR-088 | 取消固定 `problem.owner.confirm`，把 Owner 对问题的责任合并到同屏展示 exact Problem Definition 的 `product.decision` | 原链路让同一 Owner 连续确认问题、再选择 outcome；第二次点击没有增加证据、权限或责任，而增加认知负担 | `problem.ready.gate` 只机械检查 Candidate、advisory Quality Review disposition 和上游 refs。Owner 选择五种 outcome 即表示以该 exact Problem 为依据；若认为问题 material 错误，必须返回 Synthesis/Learning 生成新 Candidate，不得在 Decision 中静默改写 |
| ADR-089 | 取消固定 `plan.owner.confirm`；忠实 Planning 由 Agent 展开，只有新 material 产品取舍才返回 `product.decision` 由 Owner 决定 | Product Decision 已授权方向，普通模块/迭代/依赖/切片展开不产生新责任边界；每份 Plan 再要求确认会重复阅读和点击 | `plan.ready.gate` 只机械检查 exact Plan、Coverage/disposition、advisory Review finalize、依赖/冲突和 material Decision refs。按需一页摘要不是审批；改变用户/结果、核心承诺、重要优先级/时间、风险承担或 COMMIT/EXPERIMENT 边界必须创建/amend Decision 后再继续 Planning |
| ADR-090 | 正常 Discovery/Product 路径只保留 `product.decision` 一处固定人类语义责任边界；清晰自然语言 Owner 意图可直接成为 choice，不再追加确认 UI | 五种 outcome 都影响资源、机会、用户暴露或组织承诺，Agent不能替 Owner 决定；但“必须有明确意图”不等于先听到决定再问一次“是否确认” | Decision Brief、一次必要 material challenge 与 Owner choice 均在同一节点。supports/non-material Evidence 不重问；改变既有 Decision、Planning 出现新 material 取舍才回同一节点。Problem/Plan/PRD/Handoff 固定内容确认均取消或条件化，Connector 写入授权不是内容确认，外置审批在 Graph 外 |
| ADR-091 | 取消 Bug Baseline 每单固定 `PM Route Confirmation`；可靠 Assessment 由 Controller 按证据条件自动分流，仅在 baseline 冲突、PM-only事实、material 路线差异或 override 时最小澄清 | 分类事实可由 exact baseline 与 actual/expected 证据确定时，再问 PM 只是重复点击；但无可靠 baseline 时自动交研发会让实现修复偷改产品规则 | 自动 Implementation Deviation 必须同时满足 current baseline、差异明确、不创建新规则、AC可判定、无 material conflict。否则走 Discovery/Decision/Incident 或提出一个能改变路线的最小问题。保留 Agent recommendation 与 Owner override Audit，不保留未实现 confirmation alias/event |
| ADR-092 | 唯一公开 Skill 增加一个稳定 `interview` intent，以 `skip / resume` action 让用户在访谈进行中立即禁止或恢复当前 Run 的 PM 访谈；启动/恢复 modifier 继续保留 | 只允许在 `new/resume` 时设置，会迫使已进入访谈的用户退出、重启或继续被提问，违背可控交互；同时，简单、赶时间或 Agent 自信不应成为自动跳过高价值访谈的理由 | `interview` 是第十一个 intent word，不是第二个 Skill、Graph Node、Gate、Artifact 或审批。Skip 只禁止向 PM 发问，不表示 Evidence 足够或保证生成 PRD；完整 Discovery 原则上至少一次实质 PM 访谈/等价当前对话，除非无 material PM-only unknown 且继续提问信息增益低，或用户显式 skip |
| ADR-093 | Codex 安装包只允许一个宿主可发现 Agent Skill：`skills/better-product-graph/SKILL.md`；内部原子能力改称 Core **Atomic Skill Modules** | 把源码中的节点指令镜像到 Plugin `skills/` 会让宿主 discovery 将内部节点误判为可直接调用的 Skills，从而绕过 Orchestrator/Controller | 内部模块保留原子性、独立测试与节点级加载，源码位于 `src/core/atomic-skills/<node>/INSTRUCTIONS.md`，构建到公开 Skill 的 `references/atomic-skills/`；只有 Orchestrator/Controller 可按当前节点加载。禁止把整个内部目录镜像或链接到 `dist/**/skills/`；不新增 MCP、CLI、Service 或 Runtime |
| ADR-094 | 冻结最小 source→dist allowlist 与安装候选身份合同，由构建自动生成并检查 | 源码正确不等于安装副本正确；缺少 inventory、版本与 artifact identity 时，无法证明用户实际运行的是哪份 Core/规则/Adapter | 安装候选绑定 Plugin SemVer、exact Git commit 与 dirty state、architecture baseline、Core/rules/schema/Host Adapter versions 或等价 execution fingerprint、文件 inventory 与 artifact hash；相对资源必须在安装副本可解析。当前不要求人为给每份规划稿计算 hash，也不建设签名、SBOM 或远程 attestations |
| ADR-095 | Product Golden Suite 与 Plugin Contract Suite 是两套正交系统验收套件，均不是业务 Node/Gate | 产品判断是否正确与 Plugin 安装/激活/资源/身份合同是否正确属于不同失败面；混成一套会让包装通过冒充产品通过，或反之 | Product Golden Suite 评估 G01/G03/G04 的判断与 end state；Plugin Contract Suite 在 fresh installed copy 检查 discovery、直接/间接/follow-up/negative activation、intent parity、relative resources、唯一公开 Skill、内部入口不可绕过与 installed-copy identity。两套均须 runtime evidence 才能 PASS |
| ADR-096 | 现有 `evals/product-graph v0.1` 固定标记为 `LEGACY / DOCUMENT-ONLY / NOT A V1.4 ACCEPTANCE BASELINE`；实现期另建 v0.2 迁移基线 | v0.1 含旧 `ProductSpecPackage`、Owner approval、Dev/Test accepted 语义，与当前 V1.4 Released/Handoff/advisory-only/外置团队边界冲突；原位改名或伪装通过会破坏证据 | v0.1 只作迁移输入和历史回归对照，不产生 V1.4 PASS；v0.2 必须显式映射/替换旧字段并保留 provenance。G01/G03/G04 仍是 future fixtures，runtime 前没有 PASS |
| ADR-097 | V1.4 不把“general 模板必须经人工 Review 后才可成为默认”冻结为当前硬条件 | 模板 promotion 是配置、兼容性与真实消费者证据问题；提前设固定人工 Gate 会与已确认的可配置 Template Profile 边界冲突 | 当前只冻结 profile 可配置、exact version、fallback、pin/rollback 与不静默迁移；general v0.1 继续是 Draft/Bootstrap 候选。具体 promotion criteria 与时点留 Roadmap，不新增模板 Gate、固定 HITL 或默认审批 |

---

## 3. 实现结构视图：Host、Core 与 Connector 如何组合

本节回答“Better Product Graph 在 Agent 宿主里怎样被组装和执行”，不是完整业务产线图。完整 Product → Development → Test 边界和 Knowledge Maintenance 横向关系见文首“阅读入口”；产品信号如何一步步变成产品行动和交付物见 §6。

```text
┌──────────────────────────────────────────────────────────────────────┐
│                         Host Agent                                   │
│    自然语言 / $better-product-graph / 未来 Host 命令映射             │
│                    Codex（一期）/ 其他宿主（未来）                    │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │ Better Product Graph  │
                    │ Plugin + Host Adapter │
                    └───────────┬───────────┘
                                │ Stable Host Contract
┌───────────────────────────────▼──────────────────────────────────────┐
│                  Better Product Graph Core                          │
│                                                                      │
│  Orchestrator ──▶ Graph Manifest ──▶ Atomic Skills                  │
│       │                                                              │
│       ├──▶ Bounded Sub-agent Attempts / Join-Aggregate               │
│       ├──▶ Deterministic State Controller                            │
│       ├──▶ Schemas / Validators / Gate Policies                      │
│       ├──▶ Decision Runs / Plan Runs / Child PRD Runs                 │
│       ├──▶ Audit Ledger / Artifact Versions                          │
│       ├──▶ Product Decision / Roadmap Memory Contracts & Refs         │
│       ├──▶ Document Experience Policy / Profiles / Renderer          │
│       └──▶ Connector Mount Map                                       │
└───────────┬────────────┬──────────────┬──────────────┬──────────────┘
            │            │              │              │
      Input Source    Knowledge    External Audit   Handoff/Downstream
       Connector      Connector      Connector         Connectors
```

逻辑分层不代表多套服务。第一期以上组件都可以在一个 Codex Plugin 中由 Skill、YAML、JSON Schema、小型脚本和本地目录实现。这里的技术组件不应被误读成新的业务阶段：Host Adapter 负责适配宿主，Connector 只在固定挂载点连接外部能力，Document Experience 只为已有产物提供横向呈现约束，真正的产品流程仍由 Core 中的 Product Loop 决定。

### 3.1 横向 Sub-agent Execution Policy

Sub-agent 是**现有节点/attempt 的执行形态**，不是新的业务 Graph Node、Router 或 Runtime。只要工作能绑定同一冻结 snapshot、边界清楚、结果可独立验证且不需要共享可变状态，Orchestrator 应优先 fan-out 给 sub-agent，而不是让主 Agent 串行完成后再串行自审。典型适用项包括：

- 对抗性 Product Quality Review、外推/因果/反证检查。
- 同一 exact snapshot 上可并发的 Product、Engineering Feasibility、Testability、UX 和项目配置 Domain Review。
- 独立研究、证据检索或来源核验旁路；它们只返回 Evidence proposal/reference candidate，不能直接发布事实。
- Eval 候选、Analysis Method 候选、独立方案比较和 bounded external audit preparation。

主 Agent 的职责收敛为：冻结并分发 exact input refs/hashes；声明 subtask role、Skill/policy、权限、预算和完成合同；等待并 join；聚合 Finding/Proposal 而不抹平冲突；向 State Controller 提交 transition request。主 Agent 不应为了“确认一下”串行重做完整 subtask；若需要质检，只验证合同、来源、冲突和是否满足 join 条件。

每个 sub-agent 默认只读、最小权限，输入和输出至少遵守：

```yaml
subagent_attempt:
  parent_run_ref: exact
  parent_attempt_ref: exact
  subtask_role: versioned
  input_refs_and_hashes: exact
  skill_and_policy_versions: exact
  permission_profile: read_only_or_minimum
  model_profile: BEST_AVAILABLE | BALANCED | FAST
  bounds:
    max_fan_out: project_policy
    concurrency: host_capability
    budget: project_policy
    timeout: project_policy
    retry: bounded
  output_contract: NodeResult | Finding | Proposal
  denied_writes:
    - state
    - current_pointer
    - canonical_knowledge
    - released_artifact
    - external_side_effect
```

Host Adapter 只接收能力/成本意图，不硬编码具体供应商或模型：高风险、对抗性或关键审计可以请求 `BEST_AVAILABLE`，常规工作使用 `BALANCED`，机械/低风险旁路可使用 `FAST`；Host 负责把 profile 映射为当时真实可用的 provider/model/version，并如实记录实际选择或降级。若 Host 不支持 sub-agent 持久化、指定模型或并发，必须报告 `NOT_AVAILABLE / DEGRADED_TO_SEQUENTIAL`，不能伪装已执行。Claude 等外部系统若通过网络/Connector 调用，属于 External Audit Connector，不冒充 Plugin 内部 sub-agent。

fan-out 必须受 versioned policy 的并发、预算、超时和有限重试约束。required Reviewer/subtask 失败或超时，只让其对应 action 保持未满足；optional 分支可以标 `NOT_AVAILABLE` 并披露，不阻断无关路径。任何 sub-agent 都不能替代 `product.decision` 的 Owner choice、Deterministic Gate 或条件式 Connector side-effect authorization，也不能并发写 current state snapshot、可变 current pointer、canonical knowledge、released artifacts 或外部系统。

join/aggregate 保留每个 Finding、证据和分歧：多个 Agent 得出同一结论不自动提高 Evidence confidence，因为它们可能共享模型、输入或来源；跨 Agent 冲突不能用多数票或流畅摘要静默消失。Audit 至少记录 parent Run/attempt、subtask role、实际 provider/model/version、input refs/hashes、Skill/policy、权限、开始/结束、result hash、status、timeout/retry 与可得 cost，不保存 hidden Chain-of-Thought。

### 3.2 未来演进：Multi-Agent Collaboration

一期执行边界明确为**当前 Host 内部 sub-agent**：由一个 Host/Orchestrator 创建和回收 bounded worker attempt，共享同一正式 Run 与 State Controller，适合并行 Review、旁路研究和候选生成。它不要求建设跨 Agent 协作平台。

未来的 **Multi-Agent Collaboration** 是不同层级的能力：跨独立 Agent runtime、Host 或 provider，以协议化方式协作；参与者可以拥有不同身份、上下文、模型、权限和生命周期。例如一个独立 Agent 实例承担主策划，另一个独立 Agent 实例承担审计；两者可以恰好都由 Claude 承担，也可以来自不同 Agent/provider。架构只声明角色与 capability，不把 Claude 或任何具体模型写死。

真正的主策划/审计独立性必须至少来自独立实例、隔离上下文、不同任务目标、冻结输入和可审计输出；同一会话中只替换提示词、角色名或要求“现在反驳自己”，仍属于自审，不得标记为独立 Multi-Agent Audit。

未来协议继续复用现有稳定合同：exact snapshot/ref/hash、participant role、Skill/policy version、capability/model/provider metadata、read-only/minimum permission、`Finding / Proposal / NodeResult` 输出、result hash，以及保留分歧的 join/aggregate。外部参与者通过可插拔 Collaboration Connector、External Audit Connector 或未来稳定协议接入；其结果仍只是候选/审计输入，不能直接写正式状态、canonical knowledge、released artifact 或执行外部副作用。

Multi-Agent 不改变责任边界：Human Owner 仍在 `product.decision` 对产品方向作出 choice，Deterministic State Controller 仍唯一计算并写正式迁移，条件式 Connector side-effect authorization 仍控制外部动作。跨 Agent 身份与认证、权限委派、协议版本、幂等/重放、跨天持久化、成本结算、超时/部分失败、撤销与审计保留均需真实原型；在这些问题解决前只保留 future capability seam，不进入一期验收。

---

## 4. 产品形态与源码真源

Codex Host Plugin 的 display name 是 `Better Product Graph`；Plugin、唯一公开 Skill 和 package 的机器名统一为 `better-product-graph`，公开调用名为 `$better-product-graph`。`BPG` 只允许出现在内部字段/说明，不注册 `$bpg` 或其他公开别名。

本节代码块中的 `prd-graph/`、`dist/prd-graph-codex/` 及全文已有 `.prd-graph/`、`evals/product-graph/` 等路径是当前工作路径或历史路径引用。本版本不对真实文件夹、仓库和历史文档路径执行改名；它们迁移到新机器名的映射、兼容期和回滚方式另行制定，不能通过直接替换文字制造“已经迁移”的假象。

### 4.1 唯一源码结构

```text
prd-graph/
├── src/
│   ├── core/
│   │   ├── graph/
│   │   ├── state/
│   │   ├── contracts/
│   │   ├── atomic-skills/             # Core Atomic Skill Modules；不是 Host discoverable Skills
│   │   │   └── <node>/
│   │   │       └── INSTRUCTIONS.md
│   │   ├── policies/
│   │   │   └── document-experience/   # versioned Core policy + artifact Profiles
│   │   ├── renderers/
│   │   │   └── human-views/            # shared source-bound Renderer；不是独立 Runtime
│   │   ├── validators/
│   │   │   └── document-experience/   # shared deterministic validator；不是新 Gate
│   │   ├── gates/
│   │   ├── audit/
│   │   └── product-memory/            # 四类合同、版本索引、引用与 Impact；不是数据库服务
│   │
│   └── connectors/
│       ├── local-input/
│       ├── local-knowledge/
│       ├── local-handoff/
│       └── local-downstream-feedback/
│
├── host-adapters/
│   └── codex/
│       └── public-skill/
│           └── better-product-graph/
│               ├── SKILL.md           # 唯一 Agent Skill 源入口
│               └── references/        # 公开 Skill 自身的源 references
│
├── templates/
│   └── human-views/                 # 默认视图模板；项目模板可覆盖展示但不能降级最低理解项
├── tests/
├── examples/
└── dist/                          # 生成物，不是源码真源
    └── prd-graph-codex/
```

Document Experience 的计划源码位置明确为：`src/core/policies/document-experience/`、`src/core/renderers/human-views/`、`src/core/validators/document-experience/`、`templates/human-views/`；按需语义 Reviewer 使用相应 `src/core/atomic-skills/<reviewer-node>/INSTRUCTIONS.md`。这些是同一 Core/Plugin 内的目录边界，不代表新增部署单元，也不会被 Codex Plugin Skill discovery 扫描为独立入口。

### 4.2 Codex Plugin 是构建产物

```text
dist/prd-graph-codex/
├── .codex-plugin/plugin.json
├── build-manifest.json             # 自动生成的安装候选身份与 inventory
└── skills/
    └── better-product-graph/       # 唯一 Host discoverable Skill 目录
        ├── SKILL.md
        ├── references/
        │   ├── atomic-skills/      # 从 Core 内部模块编译/复制；仍非公开 Skill 入口
        │   │   └── <node>/INSTRUCTIONS.md
        │   ├── graph/
        │   ├── schemas/
        │   ├── policies/
        │   └── templates/
        ├── scripts/                # 仅公开 Skill 使用的确定性运行资源
        └── connectors/             # 仅打包启用的本地实现；不是 Skill
```

无论构建产物暂时位于哪个历史目录，manifest 与公开入口使用同一身份：

```yaml
plugin:
  display_name: Better Product Graph
  machine_name: better-product-graph
package:
  name: better-product-graph
public_skill:
  name: better-product-graph
  invocation: $better-product-graph
  path: skills/better-product-graph/SKILL.md
```

`src/` 与 `host-adapters/codex/public-skill/` 是受版本控制的源码真源，`dist/` 可以删除并重建。Core 被打包进 Codex Plugin 不代表 Core 依赖 Codex；任何 Codex 特有 manifest、路径和生命周期只能存在于 `host-adapters/codex/` 与构建配置中。

source→dist 构建采用最小 allowlist，不允许目录级隐式复制：

| Source allowlist | Dist target | 自动检查 |
|---|---|---|
| `host-adapters/codex/public-skill/better-product-graph/SKILL.md` | `skills/better-product-graph/SKILL.md` | 安装包中唯一 discoverable `SKILL.md`，manifest 只指向该目录 |
| `host-adapters/codex/public-skill/better-product-graph/references/**` | `skills/better-product-graph/references/**` | 每个相对引用在 fresh installed copy 内可解析 |
| `src/core/atomic-skills/<node>/INSTRUCTIONS.md` | `skills/better-product-graph/references/atomic-skills/<node>/INSTRUCTIONS.md` | 不生成额外 `SKILL.md`；不能被直接 activation 或绕过 Controller |
| allowlisted Core rules/schemas/scripts 与已启用 local connectors | 公开 Skill 内相应 `references/`、`scripts/`、`connectors/` | inventory 与 allowlist 一致，无未声明文件、绝对源码路径或越界 symlink |

禁止把任何内部源码目录整体镜像或链接到 `dist/prd-graph-codex/skills/`。构建失败条件包括：出现第二个 discoverable Skill、relative resource 逃逸或缺失、内部模块可被宿主直接激活、inventory 有非 allowlisted 文件、安装副本依赖源码工作区。

`build-manifest.json` 由构建自动生成，最小身份字段为：Plugin SemVer；exact Git commit 与 dirty state；architecture baseline（至少版本与文档 hash）；Core、rules、schema、Codex Host Adapter 的版本，或覆盖这些输入的等价 `execution_contract_fingerprint`；排序稳定的文件 inventory；候选 artifact hash。安装与 Plugin Contract Suite 必须从 **installed copy** 读取并核对这些字段，不能读取源码目录后推断安装成功。该合同保持最小：不要求人工给每份规划稿逐一算 hash，不在 V1.4 建设签名、SBOM、远程 attestations 或新发布服务。

### 4.3 当前不建设的产品

- 独立 Better Product Graph MCP Server。
- 专用 CLI 产品。
- Web 工作台。
- 后台状态服务。
- 数据库和分布式队列。
- 多租户权限中心。
- 跨 Host/Runtime Multi-Agent Collaboration 平台；一期只保留 future capability seam。
- 第二个 Host Adapter 的完整实现。
- 自动化 `evals-generator` 实现；当前只定义未来合同、PRD Run 内 `evals.build` 子节点位置与 bounded sub-agent seam。
- Driver 层。

### 4.4 命名与路径迁移说明

本版本只冻结**新身份**，不执行**旧路径迁移**：

- V1.0/V1.1 和其中的旧称保持原样，作为冻结历史证据。
- 新建 Plugin manifest、Skill metadata、package metadata 和 Graph Manifest 一律使用机器名 `better-product-graph`；用户只看到 display name `Better Product Graph` 和 `$better-product-graph`。
- 当前仓库名、工作目录、`PRD_GRAPH_v*.md`、`.prd-graph/`、`evals/product-graph/`、构建输出目录等是否迁移，要先形成独立路径清单、消费者影响、兼容映射、回滚和完成证据，再在后续版本实施。
- 迁移期间也不通过公开双别名保持兼容；若真实消费者要求旧机器名兼容，必须作为版本化 Host/package migration adapter 单独评审，而不是静默注册 `$bpg` 或旧 Skill 名。

---

## 5. Decision、Plan、PRD Run 层级与 Delivery Intent

### 5.1 为什么不把多份 PRD 塞进一个 Run

`new` 激活后先创建轻量 Decision Run；`COMMIT + NOW` 或 `EXPERIMENT` 才激活同一 Product Planning pipeline，一份 Product Plan 再可能切出多份 PRD。区别不在另一套节点，而在承诺语义和条件化内容：

```text
Decision Run decision-001
└── COMMIT + NOW 或 EXPERIMENT
    └── Plan Run plan-001
        ├── PRD Run prd-001：READY
        ├── PRD Run prd-002：BLOCKED
        └── PRD Run prd-003：WAITING_HUMAN
```

每份 PRD 有自己的问题范围、产物版本、Reviewer、优化循环、Ready 和交付节奏。让它们成为独立子 Run，可以直接复用单 Run 的状态和恢复规则，而不需要在一个巨大 state 中维护并行节点栈。

Decision/Plan/PRD 是同一通用 Run State 的不同 profile 和层级，不表示建设三套 Runtime。`EXPERIMENT` 不是第四套 Runtime、独立 subgraph 或独立 PRD profile；它只给同一 Plan/PRD Run 携带轻量 delivery intent（候选表达 `delivery_intent=EXPERIMENT`，字段名与 Schema 留待实现冻结），并条件化 Review/Ready 所需的实验边界。

### 5.2 Decision Run 负责什么

- 保存原始信号和路线。
- 完成 Problem Discovery 与 Product Decision。
- 在 `STOP / WAIT / RESEARCH` 时保存正式 Decision Record，并允许 Decision Run 在没有 Plan Run 的情况下结束、等待或进入学习回路；`WAIT` 可提出 exploring/candidate Roadmap Proposal。
- 在 `EXPERIMENT` 时创建同一种 Plan Run，并把实验意图、关键未知和 action/exposure constraints 作为 exact input；后续使用同一 Planning、PRD、Review、Ready、release 与 dispatch。实验执行结果通过统一 Intake 返回同一 Decision Run 的 Product Decision。
- 在 `COMMIT + SCHEDULED / CONDITION_TRIGGERED` 时创建 committed Roadmap Proposal 和 activation 条件，但不创建 Plan Run。
- 只有 `EXPERIMENT`、`COMMIT + NOW` 或后续合法 Planning Activation Event 才创建 Plan Run，并把确切 Decision、delivery intent、Signal、Route 和 Knowledge references 传给它。`EXPERIMENT` 不因此变成 committed product。

### 5.3 Plan Run 负责什么

- 绑定触发自己的 Decision Run，以及 `COMMIT` Decision + Planning Activation Event 或 `EXPERIMENT` Decision + delivery intent。
- 形成完整 Product Plan；未激活的 committed Roadmap Item 不能占位创建空 Plan Run。
- 明确 Target Operating Outcome、Observable Evidence、Non-sacrificable Guardrails 和 **Current Iteration Outcome**。
- 建立 Module、Iteration、PRD Matrix、Dependency / Shared Contract 四个逻辑视图，以及 Planning Items 的覆盖关系。
- 在横向模块和纵向迭代的交点上形成一份或多份 PRD Slice；跨模块闭环默认由父计划协调，只有客观上不能独立发布时才增加交付 Batch。
- 只为 Plan Ready 后当前 activated + eligible 的 Slice 创建独立 PRD Run；未来和等待项保持各自去向。若当前 Plan 的 intent 是 `EXPERIMENT`，这些 Slice/PRD 仍走同一创建方式，不另建实验子 Run 类型。
- 汇总子 Run 状态，但不代替子 Run 做 Ready。

### 5.4 PRD Run 负责什么

- 绑定一个 `prd_id`、父 Plan 版本、主 Module、Iteration、Matrix Cell/跨模块 Batch 和 Slice 版本。
- 由 State Controller 在后台准备 Run/workspace、exact parent Decision/Plan/Slice/Knowledge refs、状态/版本与文档目录；这个生命周期动作不创作或判断 PRD 内容。
- 说明本 PRD 的 **PRD Increment / Increment Contribution**，并明确它如何贡献父 Plan 的 Current Iteration Outcome；两者不能使用同一字段互相覆盖。
- 由 Agent 在单一可恢复 `prd.generate` 节点内先组织完整产品语义，再按项目 Template Profile 编写/组织 PRD；`prd.content.build / template.resolve / prd.render` 只是内部动作，不增加用户打断。中间结构默认只是 runtime object，确定性程序只辅助解析模板、校验映射和版本。
- 判断本 PRD 是否需要 Product Evals；需要时形成 Eval Plan、Eval Cases、Rubric 和 Ground-truth/Provenance 声明。
- 先以 exact 上游为基准运行忠实一致性检查，再执行所需专业 Reviewer 和优化循环；任何 material 新内容返回最早正确上游，不能在 PRD 阶段随手批准。
- 由程序化 `prd.ready.gate` 生成 Ready Assertion，并自动形成 immutable self-contained Released PRD artifact set；不再默认要求 PRD-stage Owner 理解确认、固定交付批准或物理 Handoff 打包。
- 按每个 Connector+Target 的 `disabled/manual/auto_when_ready` policy 决定不发送、等待 exact 外部写入授权或自动 dispatch；该权限不重新审核 PRD 内容，也不影响本地 Ready/Released。
- 独立等待、恢复、失效、复审和交付。

### 5.5 `EXPERIMENT` Delivery Intent 负责什么

`EXPERIMENT` 继续是正式 Product Decision outcome，但其运行形态只是同一 Product Pipeline 的受控实验模式：

- Plan/PRD Run 与 `COMMIT` 使用相同 `run_type`、节点、State Controller、版本、Review–Optimize、`prd.ready.gate`、released directory 和 dispatch；只额外携带极轻量 delivery intent。
- 它表达“用受控行动购买信息”，不表达长期产品承诺。Problem/长期方案/未来分支可以保留更多显式 Unknown，但不能把未知伪装成已确认事实。
- 同一 PRD 必须条件化写清 key unknown/hypothesis、target population/exposure、具体变化、observable evidence/measurement、continue/adjust/stop mapping、risk guardrails、stop/rollback，以及结果返回 Product Decision 的绑定；不建立另一份 Experiment PRD/template/artifact。
- Planning Profile 仍按 intent、风险和真实复杂度选择 `LIGHT / STANDARD / PROJECT_SCALE`；`EXPERIMENT` 不自动等于 LIGHT。不可逆、高 blast radius 或安全/隐私/合规/资金敏感 action 必须升档并继承适用专业约束。
- 下游 typed result 先绑定 exact Decision/PRD/Run，经 `signal.ingest` 成为新 Evidence，再回 `product.decision`。expand / iterate / stop / inconclusive 是对结果的解释与建议，不是绕过 Owner 的新正式 outcome 或自动扩大范围。

本决定撤销独立 Experiment Planning、Experiment Review、Experiment Ready、Experiment Handoff 和 Experiment Portfolio 的一期产品线；减少重复而不降低实验合同底线。

### 5.6 父子状态示例

本节 YAML 只示意父子层级、current/next 与 exact artifact refs 的关系，不冻结 ADR-080 所述 current state snapshot 的文件名、完整字段或存储 Schema；实际实现仍以“恢复所需的最小信息”为界。

以下 Plan Run 示例只在 Planning 已合法激活后存在：

```yaml
run_id: plan-run-001
run_type: plan
project_id: project-a
source_decision_run_id: decision-run-001
planning_activation_event_ref: activation-001@v1
graph_manifest_version: better-product-graph/0.1.0-alpha
state_version: 18
status: PARTIALLY_READY

input_ref: artifacts/signal-v1.json
knowledge_snapshot_ref: knowledge/snapshot-17.json

product_plan:
  artifact_id: plan-001
  version: 3
  hash: sha256:...

prd_children:
  - prd_id: prd-001
    child_run_id: prd-run-001
    slice_ref: artifacts/slices/prd-001-v1.yaml
    status: READY
    ready_assertion_ref: prd-run-001/artifacts/ready-v2.yaml
  - prd_id: prd-002
    child_run_id: prd-run-002
    slice_ref: artifacts/slices/prd-002-v1.yaml
    status: BLOCKED
    blocker_count: 1
  - prd_id: prd-003
    child_run_id: prd-run-003
    slice_ref: artifacts/slices/prd-003-v1.yaml
    status: WAITING_HUMAN
  - prd_id: prd-004
    child_run_id: prd-run-004
    slice_ref: artifacts/slices/prd-004-v1.yaml
    delivery_intent: EXPERIMENT # 候选字段名；不冻结 Schema
    status: READY
```

PRD Run：

```yaml
run_id: prd-run-002
run_type: prd
project_id: project-a
parent_run_id: plan-run-001
parent_plan_ref:
  artifact_id: plan-001
  version: 3
  hash: sha256:...
prd_id: prd-002
state_version: 7
status: BLOCKED
current_node: review.aggregate
resume_from: prd.optimize
current_attempt: 2
input_ref: artifacts/slices/prd-002-v1.yaml
knowledge_snapshot_ref: knowledge/snapshot-17.json
evals:
  applicability: REQUIRED
  eval_pack_ref: artifacts/evals/prd-002-eval-pack-v1.yaml
```

### 5.7 独立交付与父级汇总

- PRD-1 Ready 后可以立即交付，不等待 PRD-2、PRD-3。
- 每个 Released PRD artifact set 只对应一份 PRD increment，并通过 Release/State/Audit refs 绑定父 Product Plan 的确切版本。
- 父 Plan Run 只在确有共同发布约束时生成 Batch Manifest，列出本批 PRD、尚未完成分支、不能独立发布的理由、共同回滚/停止条件和引入的耦合风险；Batch 不是默认交付方式。
- 父 Plan 发生实质变化时，按影响范围使相关子 Run 进入 `REVIEW_REQUIRED`；不影响的子 Run 保持有效。

---

## 6. V1.4 Product Loop 总览

### 6.1 面向产品经理的业务视图

先看业务目的，再看机器节点。一个信号进入 Better Product Graph 后，首先只做必要的保存、理解和路线判断；不同类型的问题不会被强行塞进同一条 PRD 流程。

```text
Idea / 用户反馈 / 线上 Issue
              │
              ▼
     接收、保留原话、理解和关联历史
              │
              ▼
        选择现在最合适的处理路线
        ├── 只收进待办箱
        │     「现在只记录，不启动完整分析」
        │
        ├── 线上问题快速核查
        │     「先把研发核查所需的最少信息交出去」
        │     └── 研发结果返回后再决定 Bug / Discovery / Decision / Close
        │
        ├── Bug 产品基线核查
        │     「先弄清本来应该怎样运行」
        │     ├── 实现偏差 → Bug 修复说明 → 研发核查修复
        │     ├── 产品逻辑缺陷 → 新的产品决策与 change PRD
        │     └── 规格不清 → 回到问题发现/产品决策
        │
        └── 新机会 / 产品缺口
              │
              ▼
     证据循环：「搞清楚我们知道什么」
              │
              ▼
     问题假设审视：「检查我们是不是想错了」
              │
              ▼
     问题认知循环：「先找正确来源；需要 PM 时围绕一个未知共同判断、辅导并挑战」
              │
              ▼
     问题综合与问题就绪：「形成问题定义，并判断是否足以决策」
              │
              ▼
     产品决策：「停止 / 等待 / 研究 / 实验 / 承诺投入」
              │
              ├── 停止、等待或研究 → 留下决定和重启条件
              └── 实验或承诺且现在启动
                       │
                       ▼
              完整产品规划：「全局想完整，横向拆模块，纵向拆迭代」
                       │
                       ▼
              1..N 份独立 PRD：「每份只承担一个清楚的产品增量」
                       │
                       ▼
              忠实一致性检查 → 专业审查 ↔ 优化 → 程序化 Ready
                       → BPG Released / 本地 Handoff
                       → Connector 政策允许后写入研发系统
                       → 实验结果经 signal.ingest 返回产品决策
```

这张图表达业务选择，不等于所有框都是持久节点。哪些动作值得独立保存、恢复和审计，仍由 §7 的原子化规则及 §30 的逐节点 Review 决定。

### 6.2 机器精确执行视图

下面保留 Machine Name、状态和分支，用于实现、恢复和验收。它与上面的业务视图表达同一套已确认逻辑，不是第二条 Product Loop。

```text
自然语言 / $better-product-graph / 手动粘贴 / Issue Collector / 飞书 / 研发或测试 Graph / 未来 Input Connector
        │
        ▼
Host Adapter ──▶ stable Core intent
        │
        ▼
signal.ingest（唯一外部业务输入挂载点；先保全原文与 provenance）
        │
        ├── 纯投递/接收/生命周期状态 ──▶ 更新既有 dispatch / external status
        ├── 已有合同的 typed result ──▶ 缺关联时 signal.relate ──▶ 更新绑定结果记录
        │                              └── 含新产品事实/挑战时派生关联 Product Signal
        └── 普通信号 / 派生 Product Signal
                └──▶ signal.prepare → signal.relate? → signal.classify → route.select
                                                                  ├──▶ existing_links
                                                                  │    并行关联 Signal / Run /
                                                                  │    Decision / Roadmap / Incident
                                                                  │
                                                                  ├──▶ NEEDS_CONTEXT
                                                                  │    临时 suspension；补一个
                                                                  │    PM-only 操作事实后重算
                                                                  │
                                                                  └──▶ destination（四选一）
        ├── INBOX_ONLY（外部采集默认，不启动完整 Product Run）     │
        │                                                         │
        ├── INCIDENT_ASSESS ──▶ 线上问题核查包 ──▶ Engineering Incident Handoff
        │                              │                  │
        │                              │                  ▼
        │                              │             等待研发回传
        │                              │                  │
        │                              │                  └──▶ Close / Bug / Discovery / Product Decision
        │                              │
        │                              └──▶ 可选 Incident Product Response
        │                                   （仅确需产品判断时）
        │
        ├── BUG_BASELINE_CHECK ──▶ Bug Baseline Assessment                  │
        │                              ├── Implementation Deviation          │
        │                              │    └──▶ Bug Fix Brief ──▶ Handoff  │
        │                              ├── Product Logic Defect ──▶ Decision│
        │                              └── Spec Ambiguity ──▶ Discovery     │
        │                                                                   │
        └── DISCOVERY_START ──▶ Problem Discovery Loop                      │
                                      │                                    │
                                      ▼                                    │
                         Signal + exact Knowledge Snapshot                  │
                                      │                                    │
                                      ▼                                    │
                       evidence.collect → evidence.map v1                  │
                                      │                                    │
                                      ▼                                    │
                          problem.assumption.audit                         │
                         ├── RETURN_TO_EVIDENCE ──▶ collect/map            │
                         ├── ROUTE_REEVALUATION_RECOMMENDED ──▶ route.select（建议）│
                         └── READY_FOR_LEARNING                            │
                                      │                                    │
                                      ▼                                    │
                   Credible starting frame + exactly one MVU              │
                         + best source / information request               │
                                      │                                    │
                         ├── more learning ──▶ query / Evidence Request     │
                         │                         │                        │
                         │                         ▼                        │
                         │             evidence.collect → evidence.map vN+1│
                         │                         │                        │
                         │◀──── update assumptions / MVU ─────────────────┘│
                         │                                                 │
                         └── Learning completion                           │
                              ├── READY_FOR_SYNTHESIS ──▶ Problem Synthesis│
                              │                              │              │
                              │                              ▼              │
                              │       Independent advisory Quality Review
                              │                              │              │
                              │                              ▼              │
                              │                    Problem Ready Gate      │
                              │                              │              │
                              │                              ▼              │
                              │                    product.decision        │
                              ├── ROUTE_REEVALUATION_RECOMMENDED ──▶ route.select（建议）
                              └── INSUFFICIENT_TO_PROCEED ──▶ 记录缺口/重启条件
                  ┌──────────────┬──────────────┬──────────────┐            │
                  ▼              ▼              ▼              ▼            │
             STOP / WAIT      RESEARCH      EXPERIMENT       COMMIT         │
          结束/候选 Roadmap    补证后返回     同一 Product Pipeline   planning_activation
                                                │              ├── NOW ────┤
                                  delivery_intent=EXPERIMENT   │            │
                                                │              └── SCHEDULED / CONDITION_TRIGGERED
                                                │                    committed Roadmap；无 Plan Run
                                                └──────────────┐             │
                                                               ▼             │
                                  Outcome-first Product Planning           │
                     Planning Profile Selector（内部；不是 Router/Node）    │
                           LIGHT / STANDARD / PROJECT_SCALE                │
                         Initial Plan v0 → deepen ↔ reconcile              │
                              稳定后 Module × Iteration Shaping            │
                                                        │                  │
                                      plan.slice（PRD 候选切片）           │
                                                        │                  │
                                      coverage.validate → reconcile       │
                                                        │                  │
                            只为 activated + eligible slices 创建 PRD Runs ─┤
                                                                           ▼
                                                                 独立 PRD Run(s)
                                                                           │
                                                                           ▼
                                               PRD + 条件式 Eval Pack
                                                                           │
                                                                           ▼
                                                忠实一致性优先的 Review–Optimize Loop
                                                                           │
                                                                           ▼
                                                     Programmatic PRD Ready
                                                                           │
                                                                           ▼
                                         BPG Released Artifact Set
                                                                           │
                                               Connector policy 允许才 dispatch
                                                                           ▼
                                                Feishu / Development Handoff
                                                                           │
                                  状态、typed result 或新反馈 ──────────────┘
                                  统一回到 signal.ingest；按 §17.6 更新/派生/影响判断
```

`signal.relate?` 表示条件节点：有历史 Signal、Decision 或索引能力时执行；能力不可用时显式记录 `NOT_AVAILABLE` 后继续，不让一期基本运行依赖历史库。`NEEDS_CONTEXT` 只是 `route.select` 的临时 suspension，不是新的业务路线。Router 的业务目的地只有 `INBOX_ONLY / INCIDENT_ASSESS / BUG_BASELINE_CHECK / DISCOVERY_START`；已有 Signal、Run、Decision、Roadmap 或 Incident 只通过并行的 `existing_links` 关联，不增加路线，也不能把一条新事故证据吸收到旧记录后停止评估。Incident 默认尽快形成一份可追加版本的线上问题核查包并交接研发，不生成缩小版 PRD；Bug Baseline Check 先形成 Assessment：只有实现偏差走无 PRD 的 Bug Fix Brief 快线，产品逻辑缺陷进入 Product Decision，规格歧义进入 Discovery/Decision。

图中的 Planning Profile Selector 只在 `COMMIT + NOW` 已合法创建 Plan Run 后决定 Planning 的内部执行重量，不重新判断 Signal 去 Incident/Bug/Discovery/Inbox，也不是第二套业务 Router 或新 Graph Node。Profile 可随真实复杂度证据动态升降级，不能在 Signal Intake 时永久锁死。

Discovery 中的 `evidence.collect → evidence.map` 不是一次性前处理：初始 Signal 与确切 Knowledge Snapshot 形成 `problem.evidence.map.v1`，随后每轮按 most valuable unknown 获取最有决策价值的新证据并形成 vN+1。Loop 分开记录 runtime status、completion disposition 和 next-action recommendation；停止取决于更多学习是否仍可能改变当前拟议行动及其风险/可逆/可测/回滚判断，不取决于收集了多少条材料。只有 `READY_FOR_SYNTHESIS` 进入 Problem Synthesis；`WAITING_FOR_EVIDENCE` 只是可恢复状态，研究/实验建议也不等于正式 Product Decision。完整 Discovery 不保证产出正式 PRD：`STOP / WAIT / RESEARCH` 可以不创建交付 Run；`EXPERIMENT` 激活同一 Product Planning/PRD pipeline，但语义是受控购买信息而非长期承诺；`COMMIT` 形成正式承诺，只有 `planning_activation = NOW` 立即进入 Product Planning。

`problem.assumption.audit` 是 Discovery 内 Evidence Map 后、Learning Loop 前的一次轻量持久 checkpoint：默认不采访 PM，先由 AI 还原原话与来源角色，拆开现象、影响、问题假设、期望结果和提出方案，动态检查会改变方向的假设、反证与替代解释，再选出 **exactly one** 当前 MVU 及最合适的信息来源。它通常只运行一次，只有 material input change 或 fundamental reframe 才重跑；Incident 和已确认 Implementation Deviation 不进入。它的完成语义只是形成可信认知起点和下一项信息动作，不是找到最终“本质问题”；它只能建议补证、进入学习或重新评估路线，不能自行改路、做 Product Decision、发布 canonical knowledge 或增加独立 Gate。

Document Experience Policy 横跨上图已有的 Decision、Planning、PRD、Evidence、Review、Incident、Bug、Audit 和 Handoff 产物，但**不在图中增加节点、循环或 Gate**。每个现有构建/渲染动作在输出人类视图时解析对应 Profile、项目 policy/template，调用共享 Renderer 与 Validator；必要时调用 Readability Reviewer，结果仍由原有 Ready/Handoff Gate 消费。正式结构化 Artifact 始终是真源，人类视图只是绑定 exact source/hash 的可重建展示。

PRD Candidate 生成后的第一项审查目标不是继续发挥或美化，而是证明它没有偏离 exact Product Decision、Product Plan、PRD Slice、Knowledge/Evidence 与已确认约束。通过 `prd.ready.gate` 后，Controller 自动冻结 self-contained release；该 exact Released artifact set 就是本地 Handoff 单元，这只表示 **BPG 产品侧 Ready/Released**。组织外置汇总审批仍在 BPG 之外，飞书或研发系统写入则由独立的 versioned Connector side-effect policy 决定，三者不能混写成一个“已批准”。

---

## 7. 节点类型与原子化规则

### 7.1 节点类型

| Type | 作用 | 是否调用 LLM | 是否能写正式状态 |
|---|---|---:|---:|
| `skill` | 完成语义任务并提交候选产物 | 可能 | 否 |
| `semantic_reviewer` | 对语义质量给出 findings 与 verdict | 通常 | 否 |
| `deterministic_validator` | 计算 Schema、覆盖、依赖和政策规则 | 否 | 否 |
| `gate` | 基于当前证据、policy 和 action/scope 计算允许、受限与禁止的边 | 否 | 否；由 State Controller 执行 |
| `human_approval` | 一期只承载 `product.decision` 的 Owner choice，或条件式 Connector 外部副作用授权；未来专业 Domain approval/waiver 另行设计 | 否 | 否 |
| `connector_action` | 在固定挂载点读写外部系统 | 否或外部 | 否 |
| `state_controller` | 重算 Gate、追加事件、提升产物和原子更新状态 | 否 | 是，唯一写入者 |

### 7.2 什么才值得成为持久节点

一个动作至少满足以下一项，才需要独立持久节点：

- 有独立失败或等待语义。
- 需要不同责任人或权限。
- 需要独立重试、恢复或审计。
- 产物会被下游独立引用。
- 实现需要独立替换。

纯文件写入、配置读取、覆盖率计算和依赖环检测默认属于确定性实现或节点内部步骤，不因为“原子化”就独立占用一次 Agent 调用。

### 7.3 原子 Skill 合同

```yaml
node_id: problem.assumption.audit
node_type: skill
version: 1.0.0
human_name: 问题假设审视
goal: 在深入采访 PM 前自助去锚定，形成可信认知起点并选出 exactly one 当前 MVU、最佳来源与下一信息动作

inputs:
  - raw_signal_ref
  - current_route_record_ref
  - knowledge_snapshot_ref
  - problem_evidence_map_ref

outputs:
  - assumption_audit_checkpoint       # run-local / versioned / recoverable；非正式业务 Artifact
  - next_recommendation:
      enum:
        - RETURN_TO_EVIDENCE
        - READY_FOR_LEARNING
        - ROUTE_REEVALUATION_RECOMMENDED

checkpoint_fields:
  - checkpoint_version_and_supersedes
  - input_refs_and_hashes
  - node_skill_model_policy_versions
  - source_statement_role_separation
  - phenomenon_impact_problem_hypothesis_desired_outcome_proposed_solution
  - direction_changing_assumptions
  - counterevidence_alternatives_history_no_action_symptom_cause
  - exactly_one_most_valuable_unknown
  - recommended_information_source
  - next_learning_information_request
  - structured_rationale
  - next_recommendation_and_reason

interaction:
  default: NO_PM_INTERVIEW
rerun_policy:
  default: ONCE
  triggers: [MATERIAL_INPUT_CHANGE, FUNDAMENTAL_REFRAME]

permissions:
  allow: [knowledge.read]
  deny: [state.write, external.write, canonical_knowledge.write, product_decision.write, route.write]

allowed_results:
  - COMPLETED
  - FAILED
```

### 7.4 可恢复 Learning Loop 节点合同

```yaml
node_id: problem.learning.loop
node_type: skill
execution: resumable_loop
version: 1.0.0
goal: 围绕一个核心 MVU 从正确来源获取信息，并通过既有 evidence.collect/evidence.map 更新问题认知和下一动作建议

inputs:
  - current_problem_evidence_map_ref
  - assumption_audit_checkpoint_ref
  - exact_knowledge_snapshot_ref
  - prior_learning_state_ref?       # 恢复时使用

round_invariants:
  - exactly_one_core_mvu
  - few_tightly_related_requests_allowed
  - source_resolution_type_recorded
  - allowed_pm_interview_follows_bounded_joint_judgment
  - at_most_one_highest_value_challenge_after_pm_answer
  - new_material_must_flow_through_evidence_collect_and_map
  - round_delta_and_continue_or_stop_reason_recorded

internal_state:
  - last_completed_round_ref
  - current_evidence_map_ref
  - active_evidence_request_refs
  - runtime_status:
      enum: [ACTIVE, WAITING_FOR_EVIDENCE, PAUSED, COMPLETED, CANCELLED]

completion:
  disposition:
    enum:
      - READY_FOR_SYNTHESIS
      - ROUTE_REEVALUATION_RECOMMENDED
      - INSUFFICIENT_TO_PROCEED
  required_when_runtime_status: COMPLETED
  forbidden_when_runtime_status: [ACTIVE, WAITING_FOR_EVIDENCE, PAUSED]

next_action_recommendation:
  type: open_recommendation_object
  fields:
    - recommended_action_and_scope
    - evidence_and_remaining_unknowns
    - risk_reversibility_measurability_and_rollback
    - reason_and_strongest_counterargument
    - required_owner_or_authorization
  authority: ADVISORY_ONLY

round_delta:
  - new_evidence_refs
  - assumptions_supported_weakened_or_falsified
  - problem_frame_change
  - agent_recommendation_change
  - mvu_change
  - interrupt_reason_and_core_question
  - tightly_related_clarifications_if_any
  - pm_claim_type_and_challenge_intensity
  - challenge_content_and_basis
  - agent_recommendation_and_strongest_counterargument
  - agreement_disagreement_and_authority
  - validation_re_review_and_rollback_conditions_if_disputed
  - continue_or_stop_reason
  - action_relative_sufficiency_assessment
  - structured_rationale             # 不含 hidden Chain-of-Thought

permissions:
  allow: [knowledge.read, evidence.request, evidence.collect, evidence.map]
  deny: [experiment.create, product_decision.write, route.write, canonical_knowledge.write]
```

Evidence Request 复用版本化 request/wait 合同，至少绑定 Run、Learning Round、当前 MVU、`source_resolution_type`、目标人/来源、所需信息、有效证据、决策影响、权限/敏感性、期限或停止条件、当前状态和 `supersedes`。任意外部来源尚未返回时，Loop 可以进入 `WAITING_FOR_EVIDENCE`；该状态不限于 human evidence，也不等于 Loop 已完成。Evidence Request 本身不是 Graph Node、独立 Agent 或新的业务路线。Learning Round Delta 以及三维状态/结论/建议都是 Learning State 内的 versioned internal section，不是独立业务 Artifact 或顶层节点。

State Controller 分开执行三件事：`runtime_status` 回答 Loop 当前是否运行、等待、暂停、完成或取消；`completion.disposition` 只在 `COMPLETED` 时回答为何结束；`next_action_recommendation` 记录 Agent 建议，但不能写 Product Decision、创建 Research/Experiment、给予授权或推进外部动作。`WAITING_FOR_EVIDENCE`、`PAUSED` 不得伪装成 completion disposition；`READY_FOR_SYNTHESIS` 也不等于 Problem Ready。人工 override 的确切权限合同仍待后续 Review，但不能破坏这三个字段的语义分离。

### 7.4.1 Problem Synthesis 节点合同

```yaml
node_id: problem.synthesize
node_type: skill
execution: one_shot_recoverable
version: 1.0.0
goal: 停止主要发散，把 exact Discovery inputs 收敛成稳定可审的 Problem Definition Candidate

precondition:
  learning_runtime_status: COMPLETED
  learning_completion_disposition: READY_FOR_SYNTHESIS

inputs:
  - raw_signal_ref_and_hash
  - knowledge_snapshot_ref_and_hash
  - product_memory_snapshot_ref_and_hash
  - problem_evidence_map_ref_and_hash
  - assumption_audit_checkpoint_ref_and_hash
  - learning_state_ref_and_hash
  - learning_round_delta_refs_and_hashes
  - recorded_disagreement_refs_and_hashes

outputs:
  - problem_definition_candidate:
      lifecycle: versioned_run_candidate
      fields:
        - user_scenario_goal_obstacle_impact_desired_change
        - evidence_boundary
        - assumptions_and_unknowns
        - scope_and_explicit_non_problems
        - proposed_solution_relationship_to_problem
        - exact_input_bindings
        - version_hash_and_supersedes

results:
  - COMPLETED
  - RETURN_TO_LEARNING
  - FAILED

permissions:
  allow: [knowledge.read_exact, artifact.write_new_version]
  deny: [evidence.fabricate, canonical_knowledge.write, product_decision.write, plan.write, prd.write, external.write]
```

`RETURN_TO_LEARNING` 必须说明 material gap、它为什么可能根本改变问题方向，并形成新的 MVU/恢复引用；它不能直接改写旧 Learning State 或 Candidate。节点恢复时从 exact input refs 和最后成功 checkpoint 重建；输入未变不得重复搜索，任一 source version/hash 变化则旧 attempt/candidate 标记 stale，并以新版本 `supersedes` 旧候选。

### 7.5 Run Interaction Policy

```yaml
interaction_policy:
  value: ALLOW_PM_INTERVIEW | NO_PM_INTERVIEW
  scope: CURRENT_RUN
  changed_by: new_or_resume_modifier | interview_intent | natural_language_equivalent
  enforced_by: state_controller_before_every_pm_prompt
  runtime_actions: interview.skip | interview.resume
  reserved_not_implemented: NON_INTERACTIVE
```

`ALLOW_PM_INTERVIEW / NO_PM_INTERVIEW` 是是否允许 PM 产品访谈的权限政策，与 `GUIDED / STANDARD / COMPACT` 交互展示风格分开。`interaction=guided` 恢复时同时设置 `interaction_policy=ALLOW_PM_INTERVIEW` 和 `interaction_style=GUIDED`。

`NO_PM_INTERVIEW` 只禁止当前 Run 中面向 PM 的产品探索/访谈 prompt，包括 `PM_CONTEXT_REQUIRED` 和 Learning 阶段的 `PM_JUDGMENT_REQUIRED` 追问；它不禁止 AI 自查、授权数据/外部研究、用户研究、专业 Owner Evidence Request 或正式 approval/authorization。`PM_AUTHORIZATION_REQUIRED` 仍按原批准流程执行，因为批准是权限动作而不是产品访谈。State Controller 必须在任何 PM prompt 发出前检查当前 policy；Agent、Skill 或 Host 不能以“只再确认一个问题”绕过。用户可在启动/恢复时使用 `interaction=no-pm-interview`，也可在访谈进行中使用同一公开 Skill 的 `interview skip` action：Controller 必须原子停止当前尚未回答的问题和后续 PM 访谈，并只对目标 `CURRENT_RUN` 生效。多个活跃 Run 无法判定目标时才允许一次最小 Run 澄清，不把它扩展成项目/用户全局偏好。

已回答内容继续作为带来源类型的 PM claim/context 保存；当前未回答问题和后续候选问题记录为 skipped，不得伪造成回答。Agent 先把信息请求重新路由到 Knowledge、Data、History、User Research、External/Domain Owner 或可逆 Experiment 建议等更合适来源。PM-only unknown 继续保留为 Unknown，并形成 Evidence Request/跳过影响记录，不因禁止访谈而伪装成已解决。证据足够时可继续 Synthesis；低风险、可逆、可测时可建议受限实验但不能自行创建或授权；仍存在会改变方向的 PM-only unknown 时，可以合法进入 WAIT、建议 Research/Experiment，或保持 NOT_READY，并用直白语言展示 skipped-interview impact、Unknown、影响、Agent 建议及 allowed vs not allowed。Skip 不跳过 Evidence、Problem Ready、Product Decision、外部写入授权，也不承诺系统必须产出 PRD。

同一 Run 的 `interview resume` 或 `interaction=guided` 将政策恢复为 `ALLOW_PM_INTERVIEW + GUIDED`。恢复后从当前最有价值、仍未解决的 PM-only unknown 继续，不机械重放全部旧问题。每次 skip/resume 都记录 actor、Run、`scope=CURRENT_RUN`、时间、current MVU、被跳过问题、替代来源、对行动的影响和恢复点；只存结构化理由，不保存隐藏 CoT 或默认保存全量逐字对话。

默认政策也随本决定收紧：完整 Discovery 原则上至少发生一次有实质内容的 PM 访谈，或当前对话已经完成的等价共同判断。只有 Agent 能用 exact Evidence 说明不存在 material PM-only unknown 且继续提问的信息增益很低，或用户显式执行 skip，才可以不另访谈；“需求简单”“赶时间”或“Agent 已很有把握”都不是自动跳过理由。Incident、证据可靠的 Implementation Deviation、纯 status/receipt 处理，以及当前对话已经构成等价访谈的情况可以不另开访谈。该原则约束默认行为，但不把“完成一次访谈”变成独立 Ready Gate 或勾选表。

`NON_INTERACTIVE` 只保留未来扩展位置，当前解析器不得把它静默映射为 `NO_PM_INTERVIEW`，也不得声称已支持。

---

## 8. 统一 Signal Intake 后的三类业务处理

### 8.1 通用输入处理

**阅读卡——信号接收与路线选择**

- **做什么**：所有外部业务输入先经同一个 `signal.ingest` 保存原始内容和来源；Core 再判断它是普通产品信号、已有合同结果还是纯生命周期状态。只有产品信号才继续形成可重建的理解、历史关系、分类和业务路线。
- **为什么**：接收、传输层事件识别、产品语义理解、关联历史和选择行动具有不同的失败、权限与重试边界；让每个 Connector 自带业务 Router 会复制规则、产生判断漂移，并让产品语义泄漏到边界层。
- **AI 做什么**：从授权来源补足可以自行查询的信息，生成 Prepared Signal、关系、Classification 与路线建议。
- **人做什么**：通常不需要介入；只有一个 AI 无法获得、且会直接改变当前路线的 PM-only 操作事实缺失时，才回答最少澄清。人工改路必须留下理由和权限。
- **主要产物与完成**：Raw/Prepared Signal、可选 Relationship Set、Classification Record 和 Route Decision Record 均有版本引用；Router 选出且只选出一个业务目的地，或明确暂挂为 `NEEDS_CONTEXT`。

```text
所有外部业务输入
→ signal.ingest
→ Core ingress discrimination（现有节点内部动作，不是新节点）
   ├── lifecycle/status update → 更新绑定的 dispatch / external status
   ├── typed result → 缺关联时 signal.relate → 追加绑定结果记录
   │                 → 如有新产品事实则派生关联 Product Signal
   └── ordinary/new Product Signal
           → signal.prepare
           → signal.relate?（有历史/索引能力时）
           → signal.classify
           → route.select
```

对**普通产品信号和从 typed result 派生的新产品事实**，四个节点 `signal.ingest / signal.prepare / signal.classify / route.select` 是固定流程；`signal.relate` 是显式条件节点，不是隐藏在 `prepare` 中的可选动作。完整产品信号次序始终表达为 `ingest → prepare → relate? → classify → route`。纯生命周期更新和没有新产品事实的 typed result 在中央接入判断后写回已有记录，不为凑流程进入 Product Router。

**`signal.ingest`：确定性、不可变的唯一外部接收事务。**自然语言/显式 Skill、Issue Collector、飞书 Connector、Development/Test Graph Connector 和未来 Input Connector 都只能从这里提交自然原文、原生事件或已有合同的 typed result。外部人员和下游系统不需要填写 YAML、Signal Schema 或内部 route 字段；Host/Connector 自动附加来源系统、external object/event ID、来源/接收时间、raw payload、权限/敏感性和当前上下文可得的 exact PRD/Decision/Incident/Bug/Experiment refs。`signal.ingest` 本身不调用 LLM、不做产品判断；State Controller 在同一个原子接收事务中原样保存：

- 原始内容与附件引用，不做摘要、纠错或改写。
- 来源类型、来源定位、权限/可见范围和敏感性标签。
- 来源时间、接收时间、external ID（存在时）。
- 原始内容和附件的 hash、接收 actor/connector 与幂等信息。

来源协议已经明确声明的 machine event kind 可以由 Connector 作为 **protocol-level fact** 一并传递，但它不能声称“这是产品 Bug/Incident/Discovery”。Core 可依据已版本化协议做确定性快分流；非标准自然语言由 Agent 识别。该动作属于现有 intake/prepare/classify 内部能力或 State Controller 行为，不注册新顶层节点。

普通输入和派生 Product Signal 写入不可变 Signal artifact 与 Signal Inbox/Run 索引；纯生命周期状态或 typed result 也必须保全 raw payload/provenance，再写入已有绑定记录。事务任一必需写入失败时不得留下“已接收但找不到原文或绑定结果”的正式状态。用户在对话中粘贴一次性链接属于**手动 Signal**，链接只是原始内容或来源引用；它不会因此变成已安装、可定期拉取和对账的 Connector。

**`signal.prepare`：从不可变原文生成可重建解析视图。**它只能读取 `raw_signal_ref`，执行格式/编码规范化、主张拆分，并区分观察事实、外部主张、Agent 推断、未知、用户偏好和用户提出的解决方案。每个解析项要回指原文位置或片段 hash；`prepare` 产生新版本 Prepared Signal，绝不能修改、覆盖或“清洗后替代”原文，也不再承担来源和原文保存。

**`signal.relate`：统一关系和历史关联。**当历史 Signal、Decision Ledger 或检索索引可用时，它建立带依据、方法和置信度的 `duplicate_of / related_to / same_origin_as / cluster_member_of / supports / contradicts` 等关系，并补足下游回传缺失的 exact artifact/Run 关联。对 STOP/WAIT 等历史 Decision，它还可标记新信息是否命中既有 restart/recheck condition、关键 assumption 或 material risk/opportunity，供 §10.2.3/§10.7 影响判断使用；这只是关联输入，不会自动重开或推翻 Decision。关系只增加图边，不删除 Signal、不把多条 Signal 无痕合并成一条，也不因判为 duplicate 丢失各自来源、时间和权限。历史/索引能力不存在时，节点返回显式 `NOT_AVAILABLE` 并跳过；基础分类和路由继续运行。只有关联仍无法确定且会实质影响绑定结果或后续处理时，才由正确节点向人类做一次最小澄清；可由系统推断或不影响行动的关联不能反问外部提交者。

**`signal.classify`：只读地描述输入，不决定行动。**它默认没有用户交互，不访谈、不提问、不修改正式状态。它读取不可变 Raw Signal、Prepared Signal、可用 relationships 和固定 Knowledge/Product Memory Snapshot；AI 能从授权来源查询的信息必须自行查询，不能为了省工具调用反问 PM。输出是独立 Classification Record，包含类型、可能影响、紧急度/严重度、证据充分度、分类置信度，以及明确分开的 known / unknown / conflicts，例如 incident candidate、known bug candidate、feedback/idea/gap 或 downstream return。它允许多标签和不确定分类，但不能自行选择 Product Route。

**`route.select`：结合项目政策选择下一条边。**它读取 Classification Record、relationships、用户/Connector activation source、固定 Knowledge Snapshot、项目 Router Policy 和已有 Signal/Run/Decision/Roadmap/Incident，形成 Agent 首选目的地、备选目的地和独立的 `existing_links`，再由 State Controller 依据 policy 执行转换。分类相同的 Signal 可以因风险阈值、来源权限、是否已有可信历史行为基线或用户是否明确启动分析而走不同路线，因此 classify 与 route 不合并。

`route.select` 的上下文规则是：

1. 默认基于已有记录做首选推荐，不把 Router 变成前置访谈。
2. 只有缺少**一个会直接改变路线、且 AI 无法从授权来源获取的 PM-only 操作事实**时，才进入临时 `NEEDS_CONTEXT` suspension，提出最少、聚焦的问题；回答后创建新 Route attempt 并重算。`NEEDS_CONTEXT` 不是业务目的地，也不能成为无限问答入口。
3. 用户本质、价值、使用场景、需求代表性或“该不该做”的未知进入 Discovery，由 Problem Discovery 负责访谈和挑战，不在 Router 中提前解决。
4. 可能存在持续用户/数据/资金/安全伤害且信息不足时，先走 `INCIDENT_ASSESS`，不能为了等完整上下文把止损延后。
5. “值得做但以后做”不新增 Router 分支：已有有效 Decision/Roadmap 时通过 `existing_links` 关联，仍按下述优先级决定本次新 Signal 是进入 Inbox、事故评估、Bug 基线检查还是 Discovery；是否承诺、何时激活 Planning 由 Product Decision 决定。

Router 只允许四个互斥业务目的地：`INBOX_ONLY / INCIDENT_ASSESS / BUG_BASELINE_CHECK / DISCOVERY_START`。`existing_links` 是独立 association/disposition 维度，可以同时指向 Signal、Run、Decision、Roadmap Item 和 Incident，并与任一目的地共存；它不是 `ATTACH_EXISTING` 路线。命中已有 Incident 的新证据必须既建立关联，又继续进入 `INCIDENT_ASSESS`，不能因“已经有记录”而停止影响评估。

目的地按以下顺序计算，关联关系并行产生且不参与互斥排序：

1. 可能存在持续重大伤害时，先进入 `INCIDENT_ASSESS`。
2. 否则先尊重 activation intent：`capture`、默认 Input Connector 或其他明确 Inbox-only 请求进入 `INBOX_ONLY`；`new` 表示用户已授权开始低风险分析，继续判断后续目的地，但不表示已经作出产品承诺。
3. 已激活 Signal 若声称现有产品行为偏离某个候选规则/承诺/历史行为，或提供了可追溯的 candidate baseline refs，进入 `BUG_BASELINE_CHECK`；Router 只判断“值得核查基线”，不预先宣布该基线可靠或当前适用。
4. 其余已激活 Signal 进入 `DISCOVERY_START`。

`NEEDS_CONTEXT` 只表示路由选择暂挂。尚无 Run 时由 Signal Ledger 记录 `route_status=NEEDS_CONTEXT`；已有 Intake/Run 上下文时使用等待状态并标记 `suspension_reason=ROUTE_NEEDS_CONTEXT`，回答后回到 `route.select`，不增加业务结果枚举。所有目的地都允许后续 re-route；每次重算都创建新的 Route Decision Record 并 `supersedes` 旧记录，保留 Agent 原推荐、实际选择和人工变化。

人工改路仍受证据和权限约束：PM 可以在 `INBOX_ONLY ↔ DISCOVERY_START` 之间改变激活选择，也可以把 `BUG_BASELINE_CHECK` 升级到 `DISCOVERY_START`；把 `DISCOVERY_START` 改成 `BUG_BASELINE_CHECK` 前至少要有可追溯 candidate baseline ref 或明确 expected-vs-actual 主张，随后仍由 Assessment 判断其是否可靠。把 `INCIDENT_ASSESS` 降级前必须完成最低影响评估，并记录证据、责任人和降级理由。任何人都不能通过 override 跳过 Bug Baseline Assessment；人工 override 必须产生新 Record，保存 actor、理由、新 Evidence/authorization 和影响，不能无痕改写旧 Assessment/Route。

目的地只授权对应的低风险产品分析范围：`new` 不授权产品承诺、外部写入或交付；`INCIDENT_ASSESS` 可以自动做最低影响评估和提醒，但不自动授权止损动作；`BUG_BASELINE_CHECK` 可以自动查询历史。可靠 Assessment 满足 §8.3.1 五项条件时由 Controller 自动分流；产品规则变化仍只能进入唯一 `product.decision`，外部 dispatch 权限另按 Connector policy 处理。

Issue Collector 等采集型 Input Connector 默认把每条外部 Issue 放入 Signal Inbox，并以 `INBOX_ONLY` 完成轻量 Intake，不为每条记录自动创建完整 Decision/Plan/PRD Run。研发/测试/飞书回传也不因来源身份默认启动新 Product Run：先按 §17.6 更新绑定状态/结果，只有新产品事实、冲突或挑战才派生关联 Product Signal。命中项目高危规则时，`route.select` 必须进入 `INCIDENT_ASSESS` 并提醒有权 Owner；这允许自动评估和提醒，不等于自动获得止损或外部动作授权。普通 Signal 可在人工选择、批量筛选或其他明确触发后再启动完整 Product Run。任一 Connector 不可用时，自然语言或显式 Skill 的人工输入仍走同一 Core 流程。

这些边界来自独立的失败、恢复、权限、重试和消费者需求，而不是动词数量：`ingest` 要保证原文事务完整和权限边界；`prepare` 可在不重收原文的情况下反复解析；`relate` 依赖可选历史索引并可独立降级；`classify` 可随分类模型重算；`route.select` 受版本化项目政策和激活权限约束。规范化、主张拆分等内部动作不因“原子化”继续膨胀为更多持久节点。

#### 8.1.1 Classification 与 Route 的版本化记录

Classification Record 与 Route Decision Record 是两份独立、append-only、versioned 的正式产物。Classifier 重算或 Router reroute 只能创建新版本并记录 `supersedes`；`current-classification` / `current-route` 只是导航指针。

Classification Record 至少绑定 Raw/Prepared Signal、Relationship Set、Knowledge Snapshot、分类 taxonomy、Skill/model 版本和 hash，并保存 labels、影响/紧急度、known、unknown、conflicts、confidence、创建者与时间。它没有访谈内容、路线选择或状态写入字段。

Route Decision Record 至少保存：

- Signal、相关 claim、Classification Record、Knowledge Snapshot、Router Policy、Skill/model 版本的确切引用和 hash。
- Agent 首选目的地、备选目的地、并行 `existing_links`、结构化依据、证据引用、关键未知和 activation source。
- `NEEDS_CONTEXT` 时的最少澄清问题与回答；不得保存或暴露模型隐藏 chain-of-thought。
- 实际选择目的地；人工 override 的 actor、reason、authority、最低影响评估/历史基线引用（适用时）和被覆盖推荐。
- 选择前后状态、创建时间、内容 hash、`supersedes` / reroute 链。

Route Contract 的稳定语义先收敛为：

```yaml
destination: INBOX_ONLY | INCIDENT_ASSESS | BUG_BASELINE_CHECK | DISCOVERY_START
existing_links:
  - target_ref: signal-or-run-or-decision-or-roadmap-or-incident@version
    relationship_type: ...
    disposition: ...
    evidence_refs: [...]
    confidence: ...
suspension: null | NEEDS_CONTEXT
activation_source: natural-language | explicit-skill | connector | policy | manual-reroute
supersedes: null | route-record@version
```

`existing_links[].disposition` 只描述本 Signal 与历史对象如何处置或解释，不获得状态写权限，也不能改变 `destination` 枚举。Route Validator 必须拒绝多于一个 destination、把 link 当 destination、缺失必要 Incident 降级证据、`BUG_BASELINE_CHECK` 缺 candidate baseline/expected-vs-actual 依据，或没有 `supersedes` 的 reroute。

`INBOX_ONLY` 没有 Product Run，因此 Classification/Route Records 先保存在 signal-scoped artifact 和 Signal Ledger；Signal 被 `new`、批量筛选或 policy 激活后，新 Run 必须引用 source Classification/Route 的确切版本，不能复制成失去来源的新记录。

Audit Ledger 追加 `CLASSIFICATION_CREATED / ROUTE_RECOMMENDED / ROUTE_ASSOCIATIONS_RECORDED / ROUTE_CLARIFICATION_REQUESTED / ROUTE_CLARIFICATION_ANSWERED / ROUTE_SELECTED / ROUTE_OVERRIDDEN / ROUTE_REROUTED / ROUTE_SUPERSEDED` 等事件。Audit Event 证明动作和版本链，Classification/Route Record 保存业务语义；两者不能互相替代。

普通 reroute、override 或分类修正只进入 Audit Ledger 和 Route history。只有变化同时改变正式 Product Decision、committed Roadmap 或产品行为，才生成 Product Changelog Proposal；不能把每次 Router 调整都膨胀为产品 Changelog。

### 8.2 Incident：轻量核查交接路径

**阅读卡——线上问题快速核查**

- **做什么**：在可能持续伤害用户时，尽快把研发开始核查所需的最小充分信息交出去。
- **为什么**：事故路径的首要价值是缩短识别和核查时间；把它做成缩小版 PRD、完整 Reviewer Loop 或重型 Ready，会让流程本身延误处理。
- **AI 做什么**：整理事实、影响、证据、未知和研发问题，能补则补，不能获得的非关键字段明确写 `NOT_AVAILABLE`。
- **人做什么**：报告人补充只有其掌握的关键信息；有权人只在通知、提单或产品应急动作需要授权时介入。Agent 不能自行回滚、降级、修数据、赔付或对外沟通。
- **主要产物与完成**：一个可追加版本的 Incident Verification Packet 通过三项轻量机械检查并获得可验证交接；随后等待研发回传，而不是宣称事故已经解决。

`INCIDENT_ASSESS` 的产品语义不是让 Better Product Graph 接管事故管理，也不是生成一份缩小版 PRD。它用于识别疑似正在发生的线上问题、判断影响与紧急度，并尽快收集研发核查/修复所需的**最小充分信息**。

默认主线是：

```text
INCIDENT_ASSESS
→ Incident Verification Packet v1（incident.verification.packet.v1）
→ 轻量机械检查
→ Engineering Incident Handoff
   ├── Development Graph Connector（已接入且获准）
   └── 人工/其他 Connector 交接（研发 Graph 未接入）
→ WAITING_ENGINEERING_FEEDBACK
→ 研发回传追加为 Packet v2/v3
→ Bug Fix / Product Decision / Discovery / Incident Product Response / Close
```

默认正式产物统一命名为 **Incident Verification Packet**，中文为**线上问题核查包**，内部类型固定为 `incident.verification.packet.v1`。它不是 PRD、产品方案或事故复盘，而是一份单一结构化、append-only versioned 的研发核查交接记录，回答三个问题：**发生了什么、影响多大、研发需要核查什么**。Engineering Incident Handoff 是发送这个确切 Packet 版本的动作/信封，不是第二份内容重复的正式产物。

线上问题核查包至少覆盖：

- 原始 Signal、来源和来源时间。
- 可观察现象。
- 期望行为与实际行为。
- 已知受影响用户、数量/范围、分布与当前紧急度。
- 发生时间、产品版本和运行环境。
- 可复现步骤，或明确标记“尚不可复现/当前不可复现”。
- 截图、日志、监控、相关 Issue 和其他证据引用。
- 近期相关变更。
- 已尝试动作及其结果。
- 分开的事实、推断和未知。
- 希望研发核查的问题。
- 当前负责人、核查状态和交接目标。
- 与历史 Decision、Roadmap、Incident 及其他 Signal/Run 的 `existing_links`。

研发回传不另起一份脱离来源的文档，而是追加到同一 Packet 的后续版本/结果区。允许的核查结果至少包括：`DEFECT_CONFIRMED / NOT_REPRODUCIBLE / WORKS_AS_CURRENT_RULE / HISTORICAL_DECISION_STALE / NEEDS_MORE_INFORMATION`，并可附根因、影响修正、处理建议、证据和实际已采取动作。结果再明确路由到 `BUG_FIX / PRODUCT_DECISION / DISCOVERY / INCIDENT_PRODUCT_RESPONSE / CLOSE`；研发回传本身不能直接改写产品规则或替有权 PM 做 Product Decision。

Packet v1 可以先交接当前最小信息；v2/v3 追加新证据、补齐字段和研发结论。每个版本都绑定上一版本、变更摘要、内容 hash、作者/来源和时间，旧版本不可覆盖。单项不可获得时允许明确标记 `NOT_AVAILABLE`、原因和补充责任人。严重或持续伤害信号优先完成交接与升级，剩余信息可以并行补充；不能为了把表填满而延迟紧急交接。

默认路径不生成 PRD，不进入专业 Reviewer 循环或 Evaluator–Optimizer，也不设置重型 Ready Gate。业务层轻量机械检查只有三项：原始 Signal 与证据没有被改写；事实、推断和未知已经分离；研发能够明确知道需要核查什么。通用的版本/hash、接收方权限和审计检查仍适用，但不能被扩张成语义 Review 或填表 Gate。

在权限允许、来源可访问且 Connector 已配置时，Agent 可以自动读取、整理、去重、补充已有证据，向报告人追问最少必要的核查信息，生成交接包并通知/提单。它不得自动执行回滚、降级、功能开关、数据修复、赔付或对外沟通；这些动作需要真实执行系统及匹配其风险的有权人授权，`INCIDENT_ASSESS` 或一次提单都不是动作授权。

只有事故处理确实需要产品判断，例如降级策略、临时体验、回滚取舍、补偿、沟通口径或数据修复边界，才开启可选的 **Incident Product Response** 子分支：

```text
incident.product-judgment.required
→ lightweight Response Decision / Response Spec
→ 按 action 风险请求有权 Owner 确认
→ 交给真实执行方
```

这个子分支不是默认必经，也不能把核查交接拖成完整 Product Planning。任何临时产品措施都必须记录 Owner、TTL、退出/回滚条件和作用范围；研发反馈或临时措施结束后，Incident 必须落到 `BUG_BASELINE_CHECK / DISCOVERY_START / Product Decision / Close` 之一，不能长期停留在“应急处理中”。

### 8.3 Bug Baseline Check 与 Bug Fix Quick Path

**阅读卡——Bug 产品基线核查**

- **做什么**：先重建当前有效产品规则，再比较 expected 与 actual，判断问题本质。
- **为什么**：只有实现偏离既有规则时才应直接修；产品规则错误或规格冲突若也按普通 Bug 交给研发，会让研发替产品做决定或无痕改变规则。
- **AI 做什么**：检索 Decision、PRD、验收标准、设计/API 合同、对外承诺和历史行为，展示冲突并给出首选专业建议。
- **人做什么**：通常不介入；只有 baseline 冲突、PM-only 事实、material 路线差异或人工纠错/override 时回答一个最小问题。产品规则变化仍进入 Product Decision。
- **主要产物与完成**：Bug Baseline Assessment 明确 `cause_class`、证据边界和推荐；实现偏差才继续形成 Bug Fix Brief，其他类型转入 Decision 或 Discovery。

`BUG_BASELINE_CHECK` 不是“看到异常就直接写修复 PRD”，而是先判断当前产品基线是什么、线上行为究竟偏离了实现还是暴露了产品规则问题。其正式输出是 **Bug Baseline Assessment**，内部类型为 `bug.baseline.assessment.v1`。

此前统一产出“Bug Quick PRD”不准确，也过重：同一个“按钮点了没反应”可能是实现没有遵守已批准交互，也可能是已批准交互本身设计错误，还可能根本找不到一致规则。把三者都写成 PRD，会让纯实现修复重复走产品规划；把三者都当研发 Bug，又会让产品规则变化绕过 Product Decision 和版本治理。

第一性判断是：**是否需要 PRD，取决于是否要改变产品规则，而不是问题出现在哪个技术层。**恢复已经批准的当前基线只需要精确修复合同；改变、补充或取代产品规则才需要 Decision/PRD。前端、后端、数据、API 或 AI 只是问题表面和专业风险提示，不能决定业务路线。

考虑过但拒绝的替代方案：

| 方案 | 为什么拒绝 |
|---|---|
| 所有 Bug 都生成 PRD | 对纯实现偏差重复描述已批准规则，增加 PM、Reviewer 和版本维护成本，还容易在“修 Bug”名义下无痕改规则 |
| 所有 Bug 都不生成 PRD | 产品逻辑错误、规则过时和遗漏场景无法形成 superseding Decision/change PRD，下游不知道产品合同已经变化 |
| 把“前端交互”设为第三条一级路线 | 同一个前端现象也可能分别属于实现偏差、产品逻辑缺陷或规格歧义；按技术表面分类会混淆原因和责任 |

因此采用两维模型：`cause_class` 决定业务分流和正式产物，`surface_tags` 只标记问题涉及的领域、检索范围和可能需要的专业风险能力。这个模型避免为了“分类动作”再增加持久节点；它们都是同一 Bug Baseline Assessment 的字段。

```text
BUG_BASELINE_CHECK
→ Bug Baseline Assessment
→ Agent 首选专业建议 + Controller evidence-conditioned route
   ├── IMPLEMENTATION_DEVIATION ──▶ Bug Fix Brief ──▶ 轻量检查 ──▶ Engineering Handoff
   ├── PRODUCT_LOGIC_DEFECT ──────▶ Product Decision ──▶ versioned change PRD
   ├── SPEC_AMBIGUITY ────────────▶ Discovery / Product Decision
   └── 严重或持续伤害 ───────────▶ INCIDENT_ASSESS
```

#### 8.3.1 Bug Baseline Assessment

Assessment 必须先检索项目知识和历史产物，重建**当前有效产品基线**，不能只读一条旧 Decision。候选基线至少包括 Decision、PRD、Acceptance Criteria、设计稿/交互说明、API 合同、对外承诺和可验证历史行为；每项都要记录确切版本/hash、形成时间、适用用户/场景/边界、证据、冲突、置信度、是否被 superseded，以及为何仍被认为当前有效。然后对比 actual vs expected，披露关键未知并形成 Agent 有依据的首选建议。

固定 `PM Route Confirmation` 已取消。只有同时满足以下五项，Controller 才能自动把 `IMPLEMENTATION_DEVIATION` 送入 Bug Fix Brief/Engineering Handoff：exact baseline refs current 且有效；expected vs actual 差异明确；修复不会创建新产品规则；AC 可判定；来源之间没有 unresolved material conflict。其余情况不得猜测或因 PM 一句“直接修”快速交研发：符合旧 PRD但规则受质疑时进 `product.decision`；规格冲突/未定义时进 Discovery；持续伤害/高危时优先 Incident。

只有多份 PRD/AC/design/history 冲突、无法确定哪个 baseline current、缺 PM-only 业务事实、修复现有规则与改变规则会造成 material 不同影响，或 Agent 与 PM 存在实质分歧/人工 override 时才打断人。Agent 必须先展示专业判断、依据、缺口和建议，只问一个会改变路线的最小问题；不把 Junior PM 丢进空白分类菜单。Owner 可纠正 route，但 override 创建新 versioned record，不能改写旧 Assessment；若纠正涉及新规则，仍进入唯一 Product Decision。

Assessment 的一级本质分类固定为且只能为下列一种；这是同一产物中的字段，不新增持久 Graph 节点：

- `IMPLEMENTATION_DEVIATION`：基线清楚且当前实现疑似偏离已经批准的行为。
- `PRODUCT_LOGIC_DEFECT`：线上实现可能符合旧 PRD/设计，但产品规则本身错误、遗漏或已经过时。
- `SPEC_AMBIGUITY`：PRD、设计、历史决定、合同或历史行为相互冲突，关键场景缺失，无法建立可靠 expected behavior。

Assessment 的最小合同可以表达为：

```yaml
artifact_type: bug.baseline.assessment.v1
source_refs: [signal-or-incident-packet@version]
baseline_sources:
  - {ref: ..., kind: decision-or-prd-or-ac-or-design-or-api-or-commitment-or-behavior, valid_at: ..., scope: ..., superseded: ..., confidence: ...}
conflicts: [...]
expected_behavior: ...
actual_behavior: ...
cause_class: IMPLEMENTATION_DEVIATION | PRODUCT_LOGIC_DEFECT | SPEC_AMBIGUITY
surface_tags: [...]
agent_recommendation: {preferred_route: ..., reasons: [...], alternatives: [...], risks: [...]}
controller_route: {destination: ..., evidence_conditions: [...], rules_version: ...}
clarification_or_override_ref: null
```

`surface_tags` 是与一级分类正交的领域标签，不是业务路线，也不替代本质分类。至少支持 `FRONTEND_INTERACTION / BACKEND_LOGIC / DATA / API / AI_BEHAVIOR / PERFORMANCE / SECURITY`，可多选。例如前端交互中：已批准交互规则正确但实现偏离，属于 `IMPLEMENTATION_DEVIATION`；实现忠实符合设计稿、但设计中的交互规则本身错误，属于 `PRODUCT_LOGIC_DEFECT`；没有明确规则或材料互相冲突，属于 `SPEC_AMBIGUITY`。

严重或持续伤害始终优先 reroute `INCIDENT_ASSESS`。Agent 应先检索，再向 PM 展示基线、冲突、分类和首选建议；理想交互是 0—1 轮。只有 AI 无法获得且会改变分类/路线的 PM-only 事实才追问。

Junior PM 往往只能看到现象或交付压力，并不一定掌握历史决定、合同优先级和规则变更权限；“直接修”是行动偏好，不是 expected behavior 的证据。Agent 必须先完成检索和冲突分析，给出带依据的首选建议与反方；五项证据条件齐全时由 Controller 自动分流，只有 material 缺口或人工纠错才最小打断。它不能盲从，也不能替有权 PM 创建新规则。没有可靠、当前有效的基线时，即使 PM 坚持，也不能把问题记录成 `IMPLEMENTATION_DEVIATION`。

#### 8.3.2 Implementation Deviation：Bug Fix Brief

`IMPLEMENTATION_DEVIATION` 默认不生成 Product Plan、PRD 或多 Reviewer/Evaluator–Optimizer Loop。它生成 **Bug Fix Brief**，中文“Bug 修复说明”，内部类型 `bug.fix.brief.v1`，经轻量检查后通过 Development Graph、Feishu Connector 或人工方式完成 Engineering Handoff。

Bug Fix Brief 至少包含：

- 来源 Signal 或 Incident Verification Packet 的确切版本引用。
- Bug Baseline Assessment 与所有确切 baseline refs。
- expected / actual，以及影响范围和严重度。
- 复现步骤或观察证据。
- 需要恢复到的行为边界。
- 明确 non-goals 和“不得改变既有产品规则”。
- 可判定 Acceptance Criteria。
- 回归面、兼容范围及测试/Eval 要求。
- 依赖、风险、Owner 和交接目标。

如果 Incident Verification Packet 已经保存相同事实、证据或影响信息，Bug Fix Brief 必须引用其确切版本或在其上提供追加视图，不能复制出第二份可独立漂移的“正式事实”。

Bug Fix Quick Path 的业务轻量检查只确认：当前基线有确切有效版本；actual 疑似偏离；修复不引入新产品规则；AC 可判定；回归面已识别。只有安全、隐私、资金、不可逆数据/数据修复等风险命中项目政策时才增加相应专业 Reviewer concern；只有真实 dispatch 或修复副作用需要权限时，才对该 exact action 请求授权，不默认运行 Evaluator–Optimizer 或固定专业 Owner 审批。

确定性 Bug 可以在 Bug Fix Brief 中使用通用 Eval Applicability 的 `NOT_NEEDED`，但必须记录确定性理由，并保留 AC 和回归检查。`AI_BEHAVIOR`、推荐、搜索、排序等非确定性 Bug 默认需要 Bug Eval Pack；无法稳定判断确定性时不得为了走快线伪装为确定性问题。第一版没有已发布运行消费者，不实现旧值 alias 或迁移解析器。

#### 8.3.3 Product Logic Defect 与 Spec Ambiguity

`PRODUCT_LOGIC_DEFECT` 进入 Product Decision。新决定必须显式 supersede 旧 Decision，并创建新的、版本化的 change PRD、Product Changelog Proposal 和受影响产物 Impact List；旧 PRD/Decision 永久保留，不能原位改写。证据清楚且改动很小时允许快速 Product Decision，并在合法 `COMMIT + NOW` 后用轻量 Plan 承载一份 change PRD，不强制完整 Discovery；跨模块或跨多个迭代时走正常 Product Planning 并形成 1..N PRDs。

`SPEC_AMBIGUITY` 进入 Discovery / Product Decision，先解决冲突、补齐缺失场景并建立可审计基线，不能强行归为实现 Bug。无论 PM 多么确信“这就是研发问题”，State Controller 都不能在缺可靠 current baseline、明确 expected-vs-actual、非新规则边界、可判定 AC 或仍有 material source conflict 时创建 Bug Fix Brief Handoff。

这条路径与相邻能力的边界是：Incident 先回答是否存在需要优先核查/升级的持续伤害；Bug Baseline Assessment 回答当前基线和本质原因；Product Decision/Discovery 只在规则需要改变或仍无法建立时介入；Evals 决定修复结果如何稳定判断；Engineering Handoff 只接收已经明确恢复边界、不得改规则的 Implementation Deviation，或接收 Product Decision 后的新 change PRD。这样研发不会被要求替产品决定规则，产品也不会介入每一个纯实现修复。

权限也随分支不同：Implementation Deviation 的自动分流只说明五项证据条件满足，真实 dispatch/修复仍受 Handoff policy 和研发权限约束；Product Logic Defect 必须由有权 Product Decision Owner 决定新规则；Spec Ambiguity 只允许继续补证/决策，不能授权研发任选一种解释；Incident 的紧急交接仍不能自动授权回滚、数据修复或对外动作。

### 8.4 New Opportunity / Product Gap Route

新机会、用户提出的方案和未知产品缺口进入完整 Discovery。单条反馈不能自动当成普遍需求；证据必须标注覆盖范围、样本性质和代表性限制。

---

## 9. Problem Discovery 与 Problem Ready

### 9.1 Discovery 的职责与主流程

Problem Discovery 不是把产品经理说的话整理成需求。Agent 在这里同时承担：

- **研究者**：先读项目知识、历史决定、已有 PRD、反馈和 Issue。
- **访谈者**：通过少量高价值问题逐轮外化产品经理掌握的默会信息。
- **教练**：解释为什么某个问题重要，提供例子、反例和可使用的分析框架。
- **挑战者**：主动识别方案偏见、确认偏误、单例外推、局部最优，以及把 KPI、竞品动作或领导要求伪装成用户问题。
- **整理者**：持续区分观察、事实、引文、推断、偏好、方案和未知，并维护证据与置信度。

产品经理是重要信息源和责任人，但不是事实真源。对 Junior PM 默认采用 `guided` 交互 style，提供更多解释、示例和挑战；项目可以选择 `standard` 或 `compact`，但所有 style 使用同一套证据、Reviewer 和 Gate 标准，不能把“更资深”当作降低标准的理由。style 与 §7.5 Run Interaction Policy 分开：`NO_PM_INTERVIEW` 会跳过实际 PM 产品访谈，但仍必须生成 Junior PM 可理解的 skipped-interview impact。

允许 PM 访谈时，Agent 也不能自由展开问卷。每个 Learning Round 只围绕一个 MVU，按 §9.4 的 bounded joint judgment 合同完成解释、提问、非诱导辅导、一次最高价值挑战和专业建议；挑战强度由风险、证据冲突与可逆性决定。这样既不盲从 Junior PM，也不把产品判断从 PM 手中夺走。

```text
Signal + exact Knowledge Snapshot
→ evidence.collect
→ evidence.map ──▶ Problem Evidence Map v1
→ problem.assumption.audit
     ├── RETURN_TO_EVIDENCE ──▶ evidence.collect / evidence.map vN+1
     ├── ROUTE_REEVALUATION_RECOMMENDED ──▶ route.select（只建议，重新留档）
     └── READY_FOR_LEARNING
              │
              ▼
→ problem.learning.loop ──────────────────────────────┐
     │                                                │
     ├──选择 most_valuable_unknown                    │
     ├──AI 查询 / Evidence Request / 受限研究         │
     └──evidence.collect → evidence.map vN+1 ─────────┘
→ problem.synthesize
→ problem.quality.review
→ problem.ready.gate
→ product.decision（同屏展示 exact Problem Definition，Owner 作一次 outcome 选择）
```

`problem.learning.loop` 本身是独立、可恢复的持久循环节点，共享一份版本化 Learning State 和当前 Problem Evidence Map。循环不是“不断访谈 PM”，而是每轮选择一个最值得降低的核心 MVU，再判断应由 Agent 检索、PM/Owner 补充、外部研究还是用户研究回答；新材料必须经过既有 `evidence.collect → evidence.map` 显式 loop-back。选择 MVU、来源路由、获取/请求、更新认知和继续/停止判断是节点内部原子动作：它们留下事件，但除已有 Collect/Map 外，不因动词数量升级成顶层持久节点。Evidence Request 是可版本化、可等待、可恢复的请求合同，不是 Graph Node。

#### 9.1.1 认知核心六步分别解决什么

这六步不是把同一次“分析”换六个名字，而是在不同阶段回答不同问题：

| 阶段 | 大白话问题 | 与前一步的区别 | 主要结果 |
|---|---|---|---|
| Evidence Collect / Map | 我们到底知道什么，证据支持或反对什么？ | 先处理材料和证据关系，不急着接受某种问题框架 | 当前 Problem Evidence Map |
| 问题假设审视（Assumption Audit） | 我们是不是已经在用一个错误前提理解这些材料？ | 不增加证据数量，而是还原来源角色、拆分表达并审视框架、方向性假设、反证和可信替代 | 可信认知起点、exactly one 当前 MVU、最佳来源与下一信息动作 |
| Problem Learning Loop | 哪个新信息最可能改变判断，应该从哪里获得？ | 不停留在第一次审计；用新证据持续修正问题理解 | 新版 Evidence Map、Learning State 和认知变化记录 |
| Problem Synthesis | 现在能够怎样稳定、清楚地描述问题？ | 停止主要发散，把当前认知整理成 Problem Definition | Problem Definition candidate |
| Problem Ready | 这份问题定义是否已经足以支持下一阶段决策？ | 不再生成问题定义；由 advisory 语义 Review 和确定性机械检查判断是否可前进，不重复要求 Owner 确认 | Ready verdict / 确切返工路线 |
| Product Decision | 基于这个问题，我们采取什么产品行动？ | 不再证明问题有没有写清，而是决定 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` | Decision Record 和后续路线 |

最重要的相邻边界是：**Evidence Map 回答“知道什么”，问题假设审视（Assumption Audit）回答“可能想错什么”；Learning Loop 允许问题理解继续变化，Synthesis 负责停止主要发散；Ready 判断是否足以决策，Decision 才选择行动。**

#### 9.1.2 问题假设审视：先检查是不是把问题想错了

> **CONFIRMED NODE DECISION**：`problem.assumption.audit` 是独立、轻量、可恢复的内部持久节点；中文名为“问题假设审视”。本节确认节点目标、边界和三类下一建议；相邻 Learning Loop 的节点/恢复边界、Evidence Request 等待语义和三维完成合同已在 §9.1.3 确认，人工 override 和全部 Schema 字段仍待讨论。

如果一个 Signal 说“消息太多，需要一键清空”，直接问“一键清空放在哪里、是否二次确认、清空哪些消息”，实际上已经接受“真正的问题就是缺少清空按钮”。这个节点存在，是为了让 AI 在深度访谈 PM 前先独立做一次框架检查，减少 PM 与 Agent 共同被初始方案锚定的风险。省略它的典型失败是：访谈和 PRD 都很完整，却只是在优化一个未经审视的用户方案。

**为什么是独立持久节点**：Evidence Map 保存“有什么材料、支持或反对什么”；问题假设审视检查“我们正用什么框架解释这些材料”。Learning Loop 则在初始框架和 MVU 已显式化后持续获取新信息。问题假设审视拥有独立 checkpoint、恢复点、审计和重跑触发条件；若把它塞进 Map，来源关系与解释框架会混在一起；若塞进第一次 PM 访谈，AI 和 PM 会在去锚定前共同进入方案细节。这些边界满足 §7.2 的独立恢复、审计和可替换条件，但不意味着每轮学习都再次运行它。

考虑过但拒绝的方案：

| 方案 | 拒绝理由 |
|---|---|
| 合并进 `evidence.map` | Evidence 的 provenance/claim 关系与“解释框架是否错误”具有不同失败和重算原因，合并后容易把推断写成证据 |
| 合并进 Learning Loop 第一次访谈 | 去锚定发生得太晚，提问本身已经围绕 PM/用户给出的方案展开，恢复时也无法定位初始 frame 在何处形成 |
| 每轮 Learning 都强制重跑 | 大多数轮次只是补证；重复全量审视增加成本并制造框架漂移，只有 material input change 或 fundamental reframe 才值得重跑 |
| 用固定几十项假设 checklist 保证“全面” | 完整清单会把与当前方向无关的项目抬成同等重要，增加成本却不提高决策信息价值；应根据当前 Signal、Map、历史与行动动态选择会改变方向的假设 |
| 输出全部未知或十几个同权问题 | 这是把取舍留给 Junior PM，不是辅助决策；checkpoint 必须只选 exactly one 当前 MVU，其余未知保留在 Map |
| 要求本节点一次找出最终“本质问题” | 初始证据尚未经过定向学习，过早宣称最终答案会制造虚假确定性；此处只形成可信认知起点和下一项信息动作 |
| 强制生成反方观点 | 为“显得严谨”制造稻草人会降低信噪比；没有可信替代时应诚实记录已主动检查但未发现 |
| 给它独立 Reviewer/Evaluator Loop 或 Ready Gate | 这是进入学习前的轻量 checkpoint，不是最终 Problem Definition、产品决定或可交付业务合同 |

节点读取 Raw Signal、当前有效 Route Record、确切 Knowledge Snapshot、当前 Problem Evidence Map，以及其中引用的历史 Decision/PRD。默认不采访 PM；AI 先用已有授权上下文自助完成以下五步：

1. **还原原话与事实角色**：保留用户原话及其来源，不用更流畅的摘要覆盖原意；分别标明用户直接陈述、PM 的转述或判断、Sponsor 的组织授权、Agent inference。记录“某人说了什么”不等于证明“内容为真”，Sponsor 授权也不等于 user-value evidence。
2. **拆分初始表达**：分别写出现象、影响、问题假设、期望结果和提出方案；缺失项明确为 unknown。用户说“消息太多，请一键清空”同时包含现象与方案，但尚未证明用户受到了何种影响、真正希望恢复什么结果，或清空就是正确问题定义。
3. **动态寻找会改变方向的关键假设**：只选择一旦被推翻就可能改变问题框架、下一信息来源、路线或行动的假设；不执行几十项固定 checklist，也不把普通措辞偏好、无关完整性项目或所有可能假设堆成同权清单。
4. **主动查反证与可信替代解释**：检查现有反证、历史 Decision/PRD、可能的替代解释、什么都不做的 counterfactual，以及当前描述究竟是症状还是原因。不为批判而抬杠，不强制制造反方；主动检查后没有可信替代时，记录检查范围、依据和为什么当前 frame 仍然成立。
5. **只选一个当前 MVU**：选择 **exactly one most valuable unknown**，说明它为何最可能改变方向，并推荐当前最合适的信息来源。其余未知可以保留在 Map，但不能同时输出十几个同优先级“关键问题”逃避取舍。

基于这一个 MVU，节点生成明确的 `next_learning_information_request`，至少说明：要降低的未知、为什么会改变方向、优先找哪个来源、需要检索或观察什么、什么算有效信息，以及不同答案可能如何改变下一步。它只是 Assumption Audit checkpoint 交给 Learning Loop 的内部 handoff payload；除 §9.1.3.1 已确认的来源选择/PM 打断规则外，不等于已经确认 Learning Loop 或正式 Evidence Request 的完整字段、Owner、循环退出和持久化合同。若最佳来源只能是 PM 的私有背景或组织事实，本节点仍不直接采访 PM，而是把明确请求交给后续 Learning Loop。

输出是 `assumption_audit_checkpoint`：一个 run-local、versioned、recoverable、auditable 的内部 attempt checkpoint，绑定输入版本/hash、节点/Skill/model/policy 版本和 `supersedes`。它保存原话/事实角色分离、现象/影响/问题假设/期望结果/提出方案拆分、方向性关键假设、反证与替代检查、exactly one MVU、推荐信息来源、下一信息请求、下一建议及**结构化理由**，不保存或要求模型 hidden Chain-of-Thought。它不是新的正式业务 Artifact，不能被外部 Handoff 当作产品结论，也不能直接写 canonical knowledge。

本节点的完成语义是：形成一个可信、可审计的**认知起点**，并明确一项下一步信息动作。它不要求穷尽全部假设，不要求一次找到最终“本质问题”，也不等于 Problem Definition、Problem Ready 或 Product Decision。

Run 恢复时，输入绑定未变化且 checkpoint 完整即可继续使用；checkpoint 缺失/校验失败或命中合法重跑触发时创建新 attempt/version。恢复不能让 Agent 根据聊天摘要事后补造旧 rationale，也不能用 `current` 指针覆盖确切历史版本。

节点只产生三类下一建议：

| 下一建议 | 适用条件 | 实际执行边界 |
|---|---|---|
| `RETURN_TO_EVIDENCE` | 当前 Map 缺少一个可由授权来源补得、且会决定框架/MVU 的基础材料，或证据冲突尚未被正确映射 | 回到 `evidence.collect → evidence.map`；本节点不补写证据或自行提升 claim |
| `READY_FOR_LEARNING` | 初始框架、关键假设和 MVU 已足以开始定向学习，即使仍有明确未知 | 进入 `problem.learning.loop`；不等于 Problem Ready 或 Product Decision |
| `ROUTE_REEVALUATION_RECOMMENDED` | 新发现表明当前信号可能属于 Incident、可信基线偏离或其他与当前 destination 不一致的路线 | 只向 Orchestrator/State Controller 建议重新调用 `route.select`；实际改路必须生成新的 Route Record 并 `supersedes` 旧记录 |

节点通常只运行一次。只有输入发生 material change、Evidence Map 出现会推翻初始 frame 的新证据，或 Learning Loop 形成 fundamental reframe 时才创建新的 checkpoint 版本；普通补证、换措辞或 PM 轻微偏好变化不触发重跑。重跑保留旧版本和差异，不原位覆盖。

Incident 路径和已确认的 `IMPLEMENTATION_DEVIATION` 不进入该节点：前者优先核查/交接持续伤害，后者已有可靠基线且只需恢复实现。若 Discovery 中发现疑似误路，只输出 route re-evaluation 建议，不能直接改写 destination。节点也不负责最终 Problem Definition、Product Decision、canonical knowledge 发布、PM 授权收集或专业风险裁决。

当分歧可控、可逆、可测时，节点可以在结构化理由中建议“受限实验可能比继续争论更有信息价值”；它不能自行创建 Experiment、把分歧升级成硬阻塞，或用组织授权替代用户价值证据。真正的实验选择仍由后续 Learning/Product Decision 和既有风险政策完成。

#### 9.1.3 问题认知循环：用新信息修正理解

> **CONFIRMED NODE DECISION**：`problem.learning.loop` 是独立、可恢复的持久循环节点，Evidence Request 是版本化 request/wait 合同而不是节点；§9.1.3.1 的来源选择与 PM 打断规则同时确认。Loop 的 runtime status、completion disposition 与 next-action recommendation 已按三维分离，停止采用 action-relative sufficiency。人工 override、完整 Schema 字段和物理存储仍为 `PENDING REVIEW`。

Learning Loop 循环的不是“提问次数”，而是**当前认知 → 最有价值未知 → 最合适的信息来源 → 新证据 → 更新后的认知**：

```text
读取当前 Evidence Map + Learning State
              │
              ▼
选择当前 Most Valuable Unknown
              │
              ▼
决定答案应该来自哪里
├── 项目知识 / 历史 Decision / PRD
├── 产品数据或日志
├── 外部研究
├── PM / Sponsor / 专业 Owner
├── 用户研究
└── 已有或另行授权的实验结果
              │
              ▼
获得新材料 → evidence.collect → evidence.map vN+1
              │
              ▼
更新问题框架、假设、反证、MVU 和 Agent 首选建议
              │
              ├── 仍有高信息价值的 Loop 内学习 → 再来一轮
              ├── 外部证据未返回 → WAITING_FOR_EVIDENCE（可恢复状态）
              └── 停止当前 Loop → completion disposition + 独立 next-action recommendation
```

**为什么是独立持久节点**：一次问题学习可能包含即时知识查询，也可能等待研发 Owner、用户研究或 PM 数小时到数天。系统必须知道最后完成了哪一轮、等待哪份 Evidence Request、新证据应追加到哪个 Map，以及恢复后为什么继续或停止。Assumption Audit 只形成初始认知起点，Synthesis 只在学习停止后整理问题；两者都不能替代这个跨轮次的恢复边界。

考虑过但拒绝的方案：

| 方案 | 拒绝理由 |
|---|---|
| 把 Learning 合并进 Assumption Audit | Audit 通常只运行一次并负责去锚定；Learning 会反复获取新证据和外部等待，合并后重跑与恢复边界混乱 |
| 把选择 MVU、来源路由、请求、更新和 exit 各做一个顶层节点 | 这些动作共享一轮状态，多数没有独立消费者或权限边界；全部持久化会让 Graph 变成工作流碎片，而非可维修的业务节点 |
| 把每份 Evidence Request 做成 Graph Node | Request 是“缺什么、向谁要、何时恢复”的版本化等待合同，不是自主执行者；将其节点化会为每个等待动态改 Graph |
| 持续学习直到所有 Unknown 消失 | 现实中未知不会归零，会制造无限研究；停止应取决于更多学习是否还可能改变当前风险/可逆性下的下一动作 |
| 允许 Learning Loop 直接创建 Experiment | Loop 可以判断实验信息价值更高，但实验是带风险与授权的 Product Decision outcome，并会激活正式 Product Pipeline；不能由认知循环越权启动 |
| 把“等待、完成结论、研究/实验建议”放进一个 Exit 枚举 | 等待是可恢复运行状态，完成结论回答 Loop 为何停止，建议只表达下一动作偏好；混用会让系统在仍等待时宣称完成，或把建议误当授权 |

每个 Learning Round 只选一个核心 MVU，可以为同一 MVU产生少量紧密相关的查询或 Evidence Requests。每轮必须保存：新增 Evidence References；哪些假设被支持、削弱或推翻；Problem Frame、Agent 首选建议和 MVU 如何变化；以及为什么继续学习或停止。保存的是结构化变化和依据，不是模型 hidden Chain-of-Thought。选择 MVU、来源路由、获取/请求、Map 更新与 status/completion 判断留下 Audit Events，但不全部升级为顶层节点。

外部答案不能立即取得时，Loop 进入可恢复的 `WAITING_FOR_EVIDENCE`，绑定确切 Evidence Request、最后完整 round 和 Map 版本。这里的“外部”包括 PM、专业 Owner、用户研究、异步数据任务、研发回传或其他授权来源，不限 human。恢复时只处理新返回材料并经 `evidence.collect → evidence.map` 创建新版本，不重做已经完成且输入未变的轮次；请求不可得、到期或答复不充分时保留 Unknown，记录原因，并重新选择来源、继续或以明确 disposition 完成。

停止原则不是“问题已经没有未知”，而是：**相对于当前拟采取的行动，进一步学习是否仍有合理可能改变行动。** 每次停止判断至少检查：目标用户、发生场景、期望结果、关键阻碍和影响是否已达到该行动所需的理解；是否仍有会改变方向的证据冲突；remaining unknown 会不会改变行动或伤害判断；动作的风险、可逆性、可测量性和回滚能力；以及下一轮信息的预期价值是否高于成本与等待。

低风险、可逆、可测且有真实指标/回滚的场景，可以保留更多 Unknown 并建议后续受限实验；高风险、不可逆、外部承诺、重大用户伤害或数据/资金动作需要更直接、更新鲜、独立且可复核的证据。实验不是“证据不足也先做”的逃生口：缺少测量、流量/范围、kill criteria、回滚或伤害护栏时，不能借“可逆”降低充分性门槛。

Loop 中普通的材料查询、数据读取和授权范围内外部资料研究继续作为 `AI_SELF_SERVICE / AI_CAN_RESEARCH` 完成，不因为出现“研究”一词就结束。只有需要正式资源投入、用户研究项目、跨团队研究或带风险 Experiment 时，Loop 才在停止后给出 next-action recommendation；正常情况下仍先以 `READY_FOR_SYNTHESIS` 进入 Problem Synthesis，再由轻量 Problem Ready 检查 Candidate、advisory Review disposition 与上游引用是否有效一致，最终由 Product Decision 判断现有证据是否足以选择 `RESEARCH / EXPERIMENT / WAIT / STOP / COMMIT` 等行动。Loop 不能越权创建这些 Run 或授权动作。

三个 completion dispositions 的语义是：

| completion disposition | 何时使用 | 后续边界 |
|---|---|---|
| `READY_FOR_SYNTHESIS` | 当前材料足以形成一份忠实包含 Unknown 的 Problem Definition，剩余 Unknown 可被清楚呈现给后续 Product Decision | 进入 Synthesis；不表示 Problem Ready 已通过，也不表示应做或可 COMMIT |
| `ROUTE_REEVALUATION_RECOMMENDED` | 新证据表明当前 destination 可能不再适用，例如应优先 Incident/Bug Baseline | 只建议 `route.select` 重评；新 Route Record 才能改变路线 |
| `INSUFFICIENT_TO_PROCEED` | 已无合理的当前获取路径/预算/权限，且缺口使 Synthesis 或任何当前允许的下一行动都可能误导 | 不伪造 Problem Definition、PRD 或 Decision；记录已尝试、证据缺口、无法继续原因、Agent 建议和 restart condition，Run 保持可恢复的合法终点 |

next-action recommendation 与 disposition 正交。例如 `READY_FOR_SYNTHESIS` 可以建议“在 Decision 阶段优先考虑受限实验”，`INSUFFICIENT_TO_PROCEED` 可以建议“获得某数据权限后恢复”，但两者都不等于正式 `RESEARCH / EXPERIMENT / COMMIT` Decision 或授权。State Controller 只根据有效状态迁移和有权节点写正式行动。

##### 9.1.3.1 已确认子规则：先找正确来源，再决定是否打断 PM

第一性原则是：**PM 不是默认检索入口，也不是所有事实的代理人。** 每轮只围绕一个当前 MVU，先判断谁最有资格、最低成本且最可信地回答，再决定是否需要人类交互。Learning State 为该轮记录一个 `source_resolution_type`；以下七类是交互/来源类型，不是七个新节点、Router destination、Artifact 或 Gate：

| `source_resolution_type` | 何时使用 | 系统动作 |
|---|---|---|
| `AI_SELF_SERVICE` | 答案可从当前授权的 Knowledge Snapshot、Decision/PRD/Roadmap、历史反馈/Issue、产品数据、日志或已有研究取得 | Agent 自行查询、记录 query scope/provenance 并回到 `evidence.collect → evidence.map`；不打断 PM |
| `AI_CAN_RESEARCH` | 内部来源不足，但 Agent 可在权限、成本和时效边界内查询公开或获准的外部资料 | Agent 自行研究并保存来源、新鲜度和适用范围；不把搜索工作转嫁给 PM |
| `PM_CONTEXT_REQUIRED` | 只有 PM 掌握尚未沉淀的组织背景、项目来龙去脉、私有客户上下文或内部约束 | 在提供当前判断和建议后，向 PM 请求该上下文；PM 的回答先记为 `PM_PROVIDED_CONTEXT/CLAIM`，不自动成为 user fact |
| `PM_JUDGMENT_REQUIRED` | 需要有责任的产品价值取舍、优先级、目标或机会成本判断，而不是查询一个客观事实 | Agent 先给首选专业建议、依据、反方与影响，再请 PM 做判断；不能用“请 PM 决定”逃避分析 |
| `PM_AUTHORIZATION_REQUIRED` | 下一步需要有权 Product Owner/PM 的正式批准、风险接受或承诺 | 请求确切 action/scope 的授权并记录 actor/authority；若当前 PM 无权，转有权 Owner，不把口头偏好伪装成批准 |
| `EXTERNAL_OWNER_REQUIRED` | 问题属于研发、安全、隐私、法务、合规、财务、运营等专业事实或约束 | 向对应 Domain/Engineering Owner 形成具体 Evidence Request；不能要求 PM 猜专业答案，也不能由 Agent 扮演专家签发组织结论 |
| `USER_RESEARCH_REQUIRED` | MVU 是用户需求、行为、损失、理解或偏好等用户事实，现有数据不足 | 优先读取行为数据或已有研究；仍不足时向真实用户/研究渠道发起研究请求，不把 PM 对用户的印象当作用户事实 |

只有 `PM_CONTEXT_REQUIRED / PM_JUDGMENT_REQUIRED / PM_AUTHORIZATION_REQUIRED` 默认允许打断 PM。一次打断可以包含少量、彼此紧密相关、共同回答**同一个 MVU**的问题，以减少来回等待；不设置全局固定题数。项目或 Golden Case 可以配置互动预算，但预算只是效率与诊断参数，不能迫使 Agent 在问题尚未理解时宣称 Ready。

打断 PM 前，Agent 必须先展示：

- 当前判断和仍然存在的 unknown。
- 支持、反对或限制该判断的 Evidence References 与证据边界。
- 为什么现在必须问 PM，以及为何不能由 AI、专业 Owner、数据或用户研究回答。
- Agent 的首选专业建议，而不是只列选项。
- 不同答案会改变哪个问题框架、信息动作、路线、实验或产品决定。

PM 回答“不知道”是有效结果：保留 `UNKNOWN`，并转为指向正确来源、有效证据和停止条件的 Evidence Request，不通过追问逼 PM 猜。PM 的回答即使非常确定，也先作为 PM-provided context/claim、judgment 或 authorization 记录；只有经过相应证据验证的内容才能提升为 user/product fact。

证据与 PM/Sponsor 说法冲突时，Agent 必须明确列出差异、各自能证明什么、当前不确定性和自己的首选专业建议，不能静默迎合。Sponsor/老板的有效授权可以改变**允许采取的动作**，不能提高用户价值主张的真实性；若方向可逆、可测且风险可控，可以建议缩小范围、明确指标和 kill criteria、设置回滚并运行受限实验。Agent 既不能以“老板说了”掩盖低置信度，也不能在没有 policy/Domain Owner 权限时自行硬阻塞。

- **AI 做什么**：先从授权来源自助检索；说明当前未知为什么会改变决定；选择合适来源；吸收新证据后明确哪些假设被确认、削弱或推翻，并给出自己的专业建议和最强反方。
- **人做什么**：PM 只提供独有上下文、价值判断或其权限内的授权；专业 Owner 提供专业事实/约束，用户或研究渠道提供用户事实。任何人不知道答案时，都可以保留 Unknown 并转具体 Evidence Request，而不是被迫猜测。
- **主要结果与完成**：每轮形成可回放的 Evidence Map/Learning State 版本变化、Evidence Request/等待引用及继续/停止理由。运行中使用 `ACTIVE / WAITING_FOR_EVIDENCE / PAUSED`，结束时以 `COMPLETED + READY_FOR_SYNTHESIS / ROUTE_REEVALUATION_RECOMMENDED / INSUFFICIENT_TO_PROCEED` 表达完成结论，并独立记录仅供后续有权节点参考的 next-action recommendation；`CANCELLED` 表示取消而非完成。

#### 9.1.4 Problem Synthesis、Problem Ready 与 Product Decision 的边界

> **CONFIRMED NODE DECISION（Synthesis）**：`problem.synthesize` 是独立、轻量、可恢复的一次性节点。相邻 Problem Ready 由独立 advisory Reviewer 与确定性 Controller 两类执行者完成；固定 Problem Owner Confirmation 已退役，人类产品责任由紧邻的 Product Decision 承担。Product Decision 的核心五结果、Owner choice 与确定性路由已确认，剩余领域治理细节保持开放。

Learning 的职责是让问题认知继续变化；Synthesis 的职责是**停止主要发散**，把已经形成的认知整理成一个冻结、稳定、可被 Reviewer、Product Decision 和 Ready 精确引用的版本。若没有这道边界，Review 期间继续搜索会让审查对象漂移；若把 Synthesis 与 Ready 合并，Agent 又会把“写得稳定”误报成“已经足以行动”。

考虑过但拒绝的方案：

| 方案 | 拒绝理由 |
|---|---|
| Learning 最后一轮直接输出 Problem Definition | 学习状态仍可继续变化，缺少独立冻结候选、恢复点和 stale 边界 |
| Synthesis 同时继续搜索、完整访谈和补证 | 与 Learning 职责重叠，候选无法稳定，失败后也不能定位应退回哪里 |
| Synthesis 直接判断是否做、何时做或选择方案 | 这是 Product Decision/Planning 的责任，会把问题描述偷换成决策 |
| 为追求完整删除小 Unknown，或 material gap 也先写完 | 前者制造虚假确定性，后者让下游基于错误问题优化 |

节点只接受 `problem.learning.loop` 的 `COMPLETED + READY_FOR_SYNTHESIS`，并绑定 exact Raw Signal、Knowledge Snapshot、Product Memory Snapshot、Problem Evidence Map、Assumption Audit checkpoint、Learning State、Round Deltas 与已记录分歧的 version/hash；不得读取 `latest/current`。输出是 versioned **Problem Definition Candidate** 正式 Run candidate，至少清楚表达：

- 谁遇到问题、发生在哪个场景、试图达成什么目标。
- 当前关键阻碍、造成的影响和期望改变。
- 哪些主张由什么 Evidence 支持/限制/反驳，以及证据适用边界。
- 仍成立的 Assumptions、Unknown 与其对拟议行动的影响。
- 问题范围、明确非问题和不应被误解为本问题的相邻事项。
- 用户/PM 提出的方案与问题之间的关系：方案是输入或假设，不是问题本身，也不是已选方向。
- exact input refs/hash、本候选 version/hash 和 `supersedes`。

默认不继续搜索、不发起完整 PM 访谈、不补造 Evidence、不解决未知，也不决定是否做、何时做或采用什么方案。小 Unknown 可以原样保留；若发现一个 material gap 可能根本改变用户、场景、目标、阻碍、影响或问题边界，节点必须返回 `RETURN_TO_LEARNING`，说明缺口并形成新 MVU，不能生成伪综合。

`COMPLETED` 只表示形成了**稳定可审候选**，不等于 Problem Ready 或已经作出产品决定。Candidate 也不是 canonical Knowledge、Decision、Plan、PRD 或 solution。质量 Reviewer、Ready Calculation 与后续 Product Decision 必须引用 exact candidate version/hash。

节点可从 exact inputs 与最后成功 checkpoint 恢复；同一输入失败重试不得重新做无关搜索。任何 source version/hash 变化都会使旧 attempt/candidate stale，重算时生成新 Candidate 并 `supersedes` 旧版本，不原位覆盖。

- **Problem Ready / 问题就绪（已确认）**：只判断当前 Candidate、advisory Quality Review disposition 与上游 exact refs 是否完整有效到可以进入 Product Decision；不要求 Owner 在这里再次确认，也不要求“所有 Unknown 都弄清”，更不提前判断某个拟议行动是否 Ready。Research/Experiment/Commit 等行动的证据、风险和交付 Ready 由 Product Decision 及后续阶段判断。
- **Product Decision / 产品决策（部分已确认）**：基于已就绪的问题选择产品行动；单节点形态、五种结果/人类表达、Record 最小合同、MVU 驱动的 `RESEARCH/EXPERIMENT/COMMIT` guide、`STOP/WAIT/future COMMIT` 边界与 action-risk classification 已确认；完整领域治理和剩余 materiality 细节仍等待顺序 8b Review。

#### 9.1.5 “一键清空消息”认知演化示例（非规范）

以下数据和访谈内容仅为说明而虚构，用来展示认知为何变化；它们不是项目真实证据。`工作视图 v1/v2/v3` 是从 Evidence Map 与 Learning State 渲染的人类示例，不表示本版本已经确认名为 `Problem Inquiry Record` 的正式 Artifact。

**工作视图 v1：只收到原始反馈**

| 类型 | 内容 |
|---|---|
| User quote | “消息太多，请增加一键清空全部消息。” |
| User proposal | 增加“一键清空”能力。 |
| Evidence | 已证实一名用户说过这句话；尚不能证明多数用户存在同一问题。 |
| Inference | 用户可能感到消息管理失控。 |
| Assumption | 消息数量本身可能是核心问题；所有消息可能都能安全清理。 |
| Problem frame | 用户缺少快速处理大量消息的能力。 |
| MVU | 用户真正想减少的是消息数量，还是处理消息的认知负担？ |
| Agent recommendation | 暂不设计“一键清空”；先查消息类型、用户行为和投诉场景。 |

**为什么进入 v2**：AI 查询了项目允许访问的反馈和使用数据示例，而不是让 PM 回忆可以自行检索的信息。

**工作视图 v2：出现了能削弱原假设的新证据**

| 类型 | 内容 |
|---|---|
| New evidence | 示例数据表明，投诉集中在营销和低价值系统通知；同一批用户仍频繁查看成交与风险消息。 |
| Assumption change | “消息总量就是根因”被削弱；“所有消息都可安全清理”出现直接反例。 |
| New problem frame | 高价值和低价值消息缺少可信的优先级区分，用户需要花费过多注意力筛选。 |
| New MVU | 用户是否能够稳定判断哪些消息必须处理、哪些可以安全忽略？ |
| Agent recommendation | 优先研究分类、过滤和优先级，而不是删除全部消息。 |

**为什么进入 v3**：示例用户访谈回答了当前 MVU，并暴露出删除方案可能带来的损失。

**工作视图 v3：问题从“删除”转向“可信处理”**

| 类型 | 内容 |
|---|---|
| New evidence | 示例访谈显示，用户担心遗漏风险消息，因此即使消息很多也不敢批量清理。 |
| Rejected frame | “给用户更快删除消息的按钮”不足以解决问题，并可能增加不可恢复损失。 |
| Current problem frame | 用户缺少一种可信机制，帮助自己迅速识别必须处理的信息和可以安全忽略的信息。 |
| Remaining unknown | 哪种优先级机制最容易被用户理解和信任，仍需研究或受控实验。 |
| Agent recommendation | 不优先做“一键清空”；先探索消息优先级、过滤和可信处理机制，并定义可逆验证。 |

真正有审计价值的不只是 v3 文案，而是 v1 → v2 → v3 的**版本差异**：新增了什么 Evidence、哪个 Assumption 被削弱、Problem Frame 和 MVU 为什么改变、Agent 推荐如何变化。保存的是这些结构化事实、依据、替代解释和变化记录，不是模型隐藏 Chain-of-Thought。

### 9.2 Evidence Collect、Evidence Map 与证据边界

**阅读卡——证据循环**

- **做什么**：Collect 保存可追溯的原始材料，Map 说明这些材料支持、反对或最多只能证明哪些主张，并指出冲突和未知。
- **为什么**：如果采集和解释混在一起，AI 的摘要可能替代原文；如果只贴“事实/观点”标签，又无法知道同一材料究竟证明了多大范围。
- **AI 做什么**：先查授权来源，区分八类认知对象，解释置信依据并选出当前 MVU。
- **人做什么**：只在信息确实只能由人提供时响应具体 Evidence Request；PM 的授权、偏好和转述不会自动成为用户事实。
- **主要产物与完成**：形成可追加版本的 Problem Evidence Map；完成意味着材料与当前判断可追溯，并已选择下一项最有价值的学习动作，不意味着所有未知都被消灭。

#### 9.2.1 为什么保留两个节点，但把 classify 改为 map

旧名 `evidence.classify`（**RETIRED，仅用于解释迁移**）容易让人理解为给材料贴一个“事实/观点”标签后就完成。实际工作是把多个主张、证据、冲突和未知建立成可追踪关系；同一条材料可能支持一个 claim、反驳另一个 claim，并且只证明一个很窄的范围。因此活动节点统一为 `evidence.map`。

第一性判断是：**证据材料、对材料的解释、以及组织授权是三类不同事实**。材料必须可以原样追溯；解释必须允许在同一材料上重新计算、反驳和 supersede；授权只能决定谁可以采取什么动作，不能改变材料内容或提高主张真实性。把三者混在一个“证据结论”里，系统就无法可靠恢复、质疑或审计。

`evidence.collect` 与 `evidence.map` 仍然分开，因为两者有不同的失败、权限和重试边界：Collect 负责取得不可变材料、权限和 provenance；Map 负责可重算的语义关系与认知判断。来源暂时不可访问时可以单独等待或重试 Collect；映射模型、taxonomy 或新证据变化时可以重跑 Map，而不重新抓取或改写原始证据。

考虑过但拒绝的方案：

| 方案 | 拒绝理由 |
|---|---|
| 把 collect 和 map 合成一个 LLM 节点 | 容易把摘要当原文、丢失权限/provenance，也无法在语义映射变化时复用固定证据 |
| 保留旧分类命名并只贴标签 | 标签不能表达一证多用、相互冲突、证据只覆盖局部范围或什么新信息会改变判断 |
| 为 Evidence 增加独立重型 Ready Gate | 信息充分性取决于下一步行动、风险和可逆性；统一 Gate 会阻塞低风险学习，或对高风险行动过松 |
| 规定每个问题至少 N 个来源 | 来源数量不等于独立性或质量，同源转载/重复反馈会制造虚假充分性 |
| 让 Discovery 直接更新 canonical knowledge | Run-local 推断尚未经过跨项目冲突、权限和发布治理，会制造双重真源 |

#### 9.2.2 `evidence.collect`：只采集 Evidence References

初次进入 Discovery 时，Collect 先读取不可变 Signal 和**确切版本** Knowledge Snapshot，再按缺口扩展来源。它只产生不可变 Evidence References/provenance，不对内容真假做最终判断，也不得把摘要、翻译、推断或 Agent 生成文本伪装成原始证据。

每条 Evidence Reference 至少记录：

- source identity/type、原始定位和采集方式。
- source time、采集时间、内容/查询版本和 query scope。
- 原文/原始数据引用、内容 hash；摘要另存且回指原文。
- permission、可见范围、sensitivity 和保留限制。
- freshness / 有效期判断依据。
- 与其他来源的 independence/共同上游关系。

来源覆盖 Signal、Knowledge Snapshot、Decision/Roadmap/PRD/Evals、反馈/Issue/Incident、行为数据/实验、产品合同/API/帮助文档；只有内部授权来源不足以回答当前 MVU，且权限/成本允许时才进行外部研究。外部搜索结果、竞品页面或新闻同样只是带 provenance 的来源，不能因“公开可见”自动升级为真理。

#### 9.2.3 `evidence.map`：生成 Problem Evidence Map

`evidence.map` 读取 Evidence References，生成 append-only、versioned、run-local 的 **Problem Evidence Map**，内部类型为 `problem.evidence.map.v1`。它不能直接发布 canonical knowledge，也不能覆盖旧版本。

Map 中的 claim/认知类型至少包括：

- `OBSERVATION`：直接观察或测量到、作用域清楚的现象。
- `SOURCE_ASSERTION`：某个来源确实表达过的内容；只证明“该来源这样说”。
- `VERIFIED_CLAIM`：在声明范围内得到足够直接、独立且可复核支持的主张，不表示永恒真理。
- `INFERENCE`：从证据推导出的解释。
- `ASSUMPTION`：当前继续思考暂时依赖、但尚未验证的前提。
- `PREFERENCE`：用户、PM、Owner 或组织的价值偏好。
- `PROPOSAL`：候选方案或行动建议。
- `UNKNOWN`：会影响问题/决定、当前尚无充分答案的未知。

Map 必须显式记录 `supports / contradicts / only_proves / may_change` 关系：某证据支持/反驳什么，最多只能证明什么范围，以及什么新证据可能改变当前判断。可信度不能只给一个模型百分数；必须解释来源可靠性、直接性、新鲜度、代表性、独立性、可复现性和已知反证。若仍保留数值分数，它只能作为附属排序信号，不能代替这些理由。

最小合同示意：

```yaml
artifact_type: problem.evidence.map.v1
run_id: ...
version: 1
supersedes: null
signal_ref: signal@version
knowledge_snapshot_ref: knowledge@version+hash
evidence_refs: [...]
claims:
  - {claim_id: c1, type: SOURCE_ASSERTION, statement: ..., scope: ..., confidence_rationale: ...}
relations:
  - {evidence_ref: e1, relation: only_proves, claim_id: c1, boundary: ...}
conflicts: [...]
unknowns: [...]
most_valuable_unknown:
  question: ...
  why_important: ...
  possible_answers:
    - {answer: ..., next_action: ...}
  best_sources: [...]
  collection_cost: ...
  decision_impact: ...
```

“某人说过”必须与“内容为真”分开。PM 发言要分别记录为事实提供、转述、判断、授权或偏好：PM 说“客户都需要”首先证明 PM 作出了该陈述，不自动证明所有客户事实；PM 有权拍板只改变授权，不提高 epistemic confidence。竞品采用某功能只证明竞品行为，不证明本项目用户价值；历史行为可能是惯性或遗留缺陷，不自动证明设计意图；十条来自同一工单模板、同一客户或转载链的信号仍可能只有一个独立来源。

#### 9.2.4 MVU、Evidence Request 与循环退出

每个 Map 版本都必须记录 `most_valuable_unknown`、它为何现在最重要、可能答案及各自 next action、best source、collection cost 和 decision impact。Learning Loop 每轮按当前 MVU 执行：

```text
选择 MVU
→ 选择最低成本且可信的答案来源
→ evidence.collect / Evidence Request / 受限研究
→ evidence.map 新版本
→ 更新 assumptions、confidence、冲突和下一个 MVU
→ 继续 / 综合问题 / 研究 / 实验 / 等待
```

AI 必须先按 §9.1.3.1 的七类 `source_resolution_type` 选择正确来源：知识、历史、数据和可授权外部研究由 AI 自行查询；专业事实找对应 Owner；用户事实找行为数据、已有研究或真实用户，不让 PM 猜。只有 PM 独有组织背景、价值取舍或其权限内正式授权才打断 PM。需要任何人补证时，必须形成具体 **Evidence Request**，至少包含：未知是什么、会改变哪个决定、找谁查什么、什么算有效证据、不同答案分别进入什么动作、成本/期限和停止条件；不得只写“继续调研”。

信息充分性是**相对于拟议下一行动**的判断，不是宣称已经知道全部事实，也不设全局固定来源数。每次停止前必须回答：用户/场景/目标/阻碍/影响是否足以支持该行动；是否仍有会改方向的冲突；remaining unknown 会怎样影响行动；风险、可逆性、可测量性和回滚边界是什么；下一轮信息价值是否仍高于成本。低风险、可逆、可测且有回滚的行动可以保留更多透明 Unknown；高风险、不可逆或外部承诺需要更强证据。实验只有在最低测量、范围、伤害护栏和回滚条件可能成立时才可被建议，不能成为证据不足的逃生口。

此前把 `SUFFICIENT_FOR_PROBLEM_SYNTHESIS / RESEARCH_REQUIRED / EXPERIMENT_MORE_VALUABLE / WAITING_FOR_HUMAN_EVIDENCE / INSUFFICIENT_BUT_REVERSIBLE_EXPERIMENT_ALLOWED` 放入同一个候选 Exit 枚举的设计现已废弃。它混淆了三种不同问题：Loop 是否仍在运行、Loop 为什么完成、Agent 建议后面做什么。

当前合同固定为三维分离：

1. **Runtime status**：`ACTIVE / WAITING_FOR_EVIDENCE / PAUSED / COMPLETED / CANCELLED`。`WAITING_FOR_EVIDENCE` 是可恢复状态，来源不限 human；普通 AI 查询/资料研究仍在 `ACTIVE` 的 Loop 内完成。
2. **Completion disposition**：仅在 `COMPLETED` 时选择 `READY_FOR_SYNTHESIS / ROUTE_REEVALUATION_RECOMMENDED / INSUFFICIENT_TO_PROCEED`。`INSUFFICIENT_TO_PROCEED` 必须记录已尝试来源、关键缺口、无法继续原因、Agent 建议和 restart condition，不得生成伪 Problem Definition/PRD。
3. **Next-action recommendation**：独立保存行动建议、适用范围、证据/Unknown、风险/可逆/可测/回滚、所需 Owner/授权和最强反方。它只是 advisory，不等于 Product Decision、Research path、带实验 intent 的 Product Run 或授权。

`READY_FOR_SYNTHESIS` 允许 Synthesis 忠实保留 Unknown。后续 Problem Quality Review 与确定性 Ready Gate 已分别确认：前者只给 advisory Finding，后者只判断问题是否清楚到足以进入 Product Decision，不按尚未选择的行动建立不同 Ready 门槛。`RESEARCH / EXPERIMENT / COMMIT` 所需证据、风险与执行约束由 Product Decision 及后续对应合同判断；若拟议行动暴露出会改变问题定义的 material gap，再返回 Learning/Synthesis，而不是复用一个虚假的低门槛结论。

Run-local Evidence Map 中出现稳定、可复用的新事实时，必须保留 Map 版本、原始 Evidence References、作用域和冲突，使其可以成为未来 Knowledge Graph 的 raw source candidate；当前不冻结 Knowledge Change Proposal 的提交格式或状态。只有 Knowledge Maintenance Graph 审核并发布后，内容才能成为 canonical Knowledge Snapshot。

#### 9.2.5 对下游和系统重量的影响

Problem Synthesis、Quality Review 和 Product Decision 引用当前 Map 版本，不各自重新发明一套“事实清单”；Experiment 从 Map 中取得假设、未知和验证边界，结果再作为新 Evidence Reference 回到下一版 Map；Product Eval 可以复用 claim、反证和适用范围来定义判据；未来 Knowledge Graph 只消费带作用域和 provenance 的候选素材。这样增加了 Evidence Reference、Map 和 Request 三类轻量 artifact，但避免在每个下游文档复制证据、让冲突无痕消失或让 PM 口头授权变成事实真源。一期用版本化文件和结构化索引实现，不因此引入数据库、常驻进程、Outbox 或独立 Evidence 服务。

在询问产品经理前，Agent 必须：

- 读取不可变 Signal 和确切 Knowledge Snapshot，并完成首版 Evidence Map。
- 查找历史决定、已有 PRD、反馈、Issue、数据和适用规则。
- 区分 Map 中八类认知对象及 supports/contradicts/only-proves/may-change 关系。
- 识别矛盾、隐藏假设和当前 most valuable unknown。
- 判断答案应来自材料、数据、用户、专家还是实验。

Agent 自己可以查到的问题不得直接抛给产品经理。由 Agent 推断出的“潜在用户意图”只能作为待验证假设，不能升级成事实或伪造用户证据。

### 9.3 Better Question 与 Cognitive Router

大白话说，**Better Question 决定“现在最值得问清什么、应该去哪里找答案、怎样问才不诱导、何时停止问”，Cognitive Router 决定“用哪种思考镜头检查这个未知”**。Better Question 是选题、来源、措辞和停止能力，不是新持久 Graph Node、固定问题库或 checklist；Cognitive Router 也是 `problem.learning.loop` 内部可替换能力。两者都不能独立写状态、发布知识或宣布 Problem Ready。

20 个认知基座是工具箱，不是二十项打勾清单。已确认规则是：每轮围绕一个 MVU 动态选择 **1 个主镜头**，只有辅助镜头能检查不同风险、反证或二阶影响时才增加少量辅助镜头；不设全局固定数量，也不能为了显得全面堆叠框架。认知镜头只能改变检查角度和问题措辞，不能创造事实、替代 Evidence References，或因为多个框架得出相似结论就叠加 evidence confidence。

两者不是同一层能力：

```text
Problem Evidence Map vN
已知 / 冲突 / assumptions / most_valuable_unknown
          │
          ▼
Better Question：选择当前价值最高的未知、答案来源、问法和停止点
          │
          ▼
Cognitive Router：为这个未知选择 1 个主镜头 + 少量必要辅助镜头
          │
          ▼
研究 / 访谈 / 挑战 / 反例
          │
          ▼
evidence.collect → evidence.map vN+1
更新假设、可信度理由、MVU 和下一步
```

Better Question 不替代 Evidence Reference 采集；Cognitive Router 不因套用了框架、多个镜头相互同意或输出更强语气就提高 claim 可信度。所有新材料仍须回到 `evidence.collect → evidence.map`，所有推断仍须与来源事实分开。

20 个认知基座是可路由的能力目录，不是每轮必须执行的清单：

| 路由组 | 认知基座 | 常见用途 |
|---|---|---|
| 元认知保险 | 认知协议（cognitive-protocol）、正心诚意、认知自由 | 检查当前思考过程、动机偏差和对既有观点的依附 |
| Discovery 核心 | 默会知识、主要矛盾、框架审计、第一性原理、概率思维、以终为始、知彼 | 外化隐性信息，找到本质问题，检查框架，校准证据与用户/利益相关者认知 |
| 条件式分析 | 矛盾论、二阶思维、逆向思考、双环思考、系统思维、跨学科连接、和时间做朋友 | 处理冲突、后果、失败路径、底层假设、系统反馈和阶段性 |
| 决策与实验塑形 | 知行合一、以约求变 | 把认识转成行动，并利用约束设计可落地实验或切口 |
| 仅显式调用 | 信念驱动 | 只在有权负责人明确要求、惯例而非物理约束、实验可逆且风险承担者知情时使用 |

`信念驱动` 不参与普通 Problem Discovery，也不能提高事实置信度、压过第一性原理或概率证据、绕过 Problem Ready / PRD Ready。若显式启用，只能在 Product Decision 之后帮助塑造可逆实验，并预先定义反证与停止条件；出现相反证据后必须退出。

#### 9.3.1 可选产品分析方法：Analysis Method Hook

Journey Map、KANO 等产品分析方法**不是没有适用场景，而是没有固定 Graph 阶段**：同一方法可能在 Learning 中帮助解释未知、在 Synthesis 中组织问题、在 Planning 中检查体验或优先级；若把它固定成必经步骤，输入不满足时就会退化为模板填表，多个框架叠加还会增加文档重量和虚假确定性。

本版选择轻量 **Analysis Method Hook**：它是现有 `problem.learning.loop`、`problem.synthesize` 和 Planning 内部可调用的扩展缝，不是新 Node、Router、Gate、Artifact、Service、Registry 或 Runtime。默认 `analysis_method=NONE`；只有方法相对更简单分析能带来明确增量时才升级重量：

| Level | 含义 | 使用边界 |
|---|---|---|
| `0 NONE` | 不调用产品分析模型 | 默认；当前 MVU 可由直接证据、简单比较或认知镜头回答 |
| `1 LIGHTWEIGHT_LENS` | 借用方法中的一个轻量视角 | 不生成完整模板，只检查一个明确问题 |
| `2 STRUCTURED_ANALYSIS` | 按 Method Card 运行结构化分析 | required inputs 基本具备，输出会实质改变理解、综合或规划 |
| `3 FORMAL_RESEARCH_RECOMMENDATION` | 建议正式研究以补齐方法所需输入 | 只形成 advisory recommendation；不由 Hook 创建研究、实验或授权 |

每次调用前回答五问：当前 MVU 或决策问题是什么；Method Card 的 required inputs 是否真实存在；预期 information gain / decision impact 是什么；相对 `NONE` 或更轻方法有什么独有增量；成本、限制与误用风险是否值得。任一项答不清时保持 `NONE` 或降级；缺输入时形成具体 Evidence Request，不用模型补造用户阶段、偏好或满意度。

每个方法由 versioned **Method Card** 描述，最小字段为：`method_id`、`question_answered`、`applicability`、`non_applicability`、`required_inputs`、`output`、`limitations`、`cost`、`skill_version`。Method Card 是内部能力配置合同，不是业务 Artifact 或集中 Registry。每轮默认最多一个主方法；确需多个时，必须说明各自回答的不同问题与不可替代增量，不能用“多个模型结论一致”提升 evidence confidence。

方法输出一律标为 analysis/inference，引用其输入 Evidence References，并明确限制；它不能创造 Evidence、覆盖 Evidence Map 冲突或替代 Product Decision。Agent 应向 PM 说明为什么使用、将改变什么；即使 PM 点名某方法，输入或适用性不足时也可以拒绝，并推荐 `NONE` 或更轻 Level。未来真实 Golden Case / 运行证据证明某方法有增量价值后，再将 Journey Map、KANO 等逐个实现为内部 Atomic Skill Module；不注册公开命令。

| 方法 | 适用示例 | 误用示例 |
|---|---|---|
| Journey Map | 已有跨步骤/跨渠道用户行为、触点和痛点证据，需要找出端到端体验断点或模块依赖 | 单一确定性 Bug、没有用户阶段证据时凭想象填写情绪曲线，或用漂亮旅程图替代真实行为证据 |
| KANO | 有足够且具作用域的用户研究/偏好输入，需要分析不同能力对满意与不满意的非对称影响，辅助优先级判断 | 根据一条反馈把功能永久归为“基本型/魅力型”，把分类外推到所有用户，或用 KANO 标签直接证明用户价值与 COMMIT |

一期只保留 Hook 与 versioned Method Card 合同，不批量内置任何方法，也不把方法使用列为核心 Golden Suite 验收项。

### 9.4 引导式访谈与挑战协议

本节只在当前 Run 的 `interaction_policy=ALLOW_PM_INTERVIEW` 时产生 PM 产品访谈 prompt；`NO_PM_INTERVIEW` 下仍执行分析、来源路由和 skipped-interview impact，但由 State Controller 阻止实际提问。Guided/Standard/Compact 是表达与辅导风格，不得覆盖 Run Interaction Policy。

这是 **已确认的 Learning Round 内部交互合同**：访谈是围绕一个 MVU 的 **bounded joint judgment（有边界的共同判断）**，不是收集功能列表的需求问卷，也不是让 PM 独自交作业。它复用现有 `problem.learning.loop`、Learning Round Delta 和 Audit Event，不新增 Graph Node、Gate 或正式业务 Artifact；Loop 的 status/disposition/recommendation 由 §9.1.3 与 ADR-037 统一约束。

第一性目的不是“问得更多”，而是让人和 Agent 共同完成一个会改变下一动作的判断，同时保留证据与责任边界。讨论过但拒绝的替代方式如下：

| 替代方式 | 为什么不采用 |
|---|---|
| 固定需求问卷或一轮问完全部问题 | 它按字段而非信息价值提问，容易接受预设方案、跨多个 MVU，并把 AI 可查信息转嫁给 PM |
| 完全自由、没有轮次边界的教练式对话 | 难以恢复和审计，容易无限追问、重复立场并扩大时间成本 |
| Agent 只解释和列选项，不给专业首选 | 对 Junior PM 看似中立，实际把最困难的判断重新甩回给信息更少的人 |
| 每轮都强烈反驳或因 Junior 身份提高挑战强度 | 把挑战变成表演，制造无依据反方；资历不是风险或证据质量的代理变量 |
| PM 坚持后 Agent 立即服从或一直争辩 | 前者混淆授权与事实，后者越过责任人并阻塞行动；正确做法是记录分歧和条件，交给有权 Decision/Owner |

每次允许打断 PM 的 Learning Round 按以下六步执行：

1. **展示当前理解**：先用可核查语言说明当前现象、问题假设、Evidence References、证据边界与仍未解决的 Unknown/MVU；不得把 PM 授权、偏好或转述写成用户事实。
2. **说明为何打断**：明确为什么这个答案只能或最适合由 PM 提供，以及不同答案会改变哪项问题框架、风险判断或下一动作；如果 AI、数据、用户或专业 Owner 才是正确来源，则不打断 PM。
3. **提出一个核心问题**：每轮只围绕一个核心 MVU，可附带少量共同影响同一判断的紧密澄清；全局不设僵硬题数，项目/Case 可以配置互动预算，不能借“追问”跨多个 MVU 倾倒问卷。
4. **提供非诱导脚手架**：对 Junior PM 解释概念、给出正反例、可能的取舍维度、答案结构或非穷尽选项，帮助其理解怎样判断；示例必须标明只是示例并保留开放答案，不得把 Agent 期待的结论写进问题、用选项暗示“正确答案”，也不能因资历较浅降低证据和风险标准。
5. **只做一次最高价值挑战**：消化 PM 回答后，只对最可能改变决定的假设、矛盾或遗漏提出一次有证据的挑战；若没有可信反证或替代解释，明确记录“本轮未发现值得挑战的新依据”，不能为了显得严格而抬杠、连续追问“为什么”。
6. **给出 Agent 判断**：收束为明确的首选建议、理由、适用边界和最强反方意见，说明双方是否达成一致、当前答案改变了什么，以及下一信息动作；不能只列选项把判断责任重新甩给 Junior PM。

Better Question 在这六步中负责选题、来源、非诱导措辞和停止时机，不是额外 Node、固定问卷或 checklist。Cognitive Router 只为当前 MVU 选择一个主镜头和少量能检查不同风险的辅助镜头；多个镜头重复同一观点不能创造事实或叠加 evidence confidence。

挑战强度由 **动作风险、证据冲突和可逆性** 决定，不由 PM 的资历、职位或表达自信决定：

| 强度 | 适用情形 | 行为边界 |
|---|---|---|
| `LIGHT` | 风险低、证据大体一致且动作易回滚 | 点明边界或一个遗漏，快速确认是否影响下一动作 |
| `STANDARD` | 决定有实质影响、仍有关键缺口或中等证据冲突 | 直接检验最关键假设/取舍，要求说明证据或验证方式 |
| `STRONG` | 高风险、强反证、不可逆动作或外部承诺 | 清楚展示冲突和潜在伤害，给出更安全替代、升级 Owner 或推进条件 |

Junior PM 获得更多解释、示例和选择框架，但面对同等风险时适用同一挑战强度与质量标准；资深 PM 或 Sponsor 也不能因身份自动降低挑战。

若 PM 在一次挑战后仍坚持，Agent 不进入无限争辩。Learning Round 必须分别记录 Agent 判断、PM 判断、分歧点、各自依据、PM 的 authority、风险，以及建议的重审、验证和回滚条件。有权负责人坚持且项目 policy 允许时，可以把分歧透明带入后续正式 Product Decision；Learning Loop 本身不能替其写入决定或把授权提升为事实。PM 无相应权限时，坚持不能修改正式决定、跨过 Domain Owner 或突破 policy。

出现以下任一情况即停止当前访谈轮：MVU 已被充分回答；PM 明确不知道；答案应来自数据、用户或专业 Owner；双方只是在重复既有立场；可逆实验的信息价值高于继续讨论；或问题已经需要进入正式 Product Decision。实验只能作为下一步建议返回有权节点，不能由 Learning Loop 创建或授权。

Learning Round 至少保存：`interrupt_reason`、当前 MVU、核心问题与必要澄清、PM claim type、挑战内容与 `LIGHT / STANDARD / STRONG`、Agent 首选建议与最强反方、agreement/disagreement、authority、假设/frame 变化和 next action/stop reason。保存的是可复核的 structured rationale，不是模型 hidden Chain-of-Thought；默认不永久保存全量逐字对话，只在项目 policy、权限、同意与保留期限都允许时保存必要原句。PM 的确认只表示当前表达忠实反映其理解和责任判断，不表示问题已经被客观证明。

### 9.5 Problem Quality Reviewer

> **CONFIRMED NODE DECISION**：`problem.quality.review` 默认由 Better Product Graph 内部独立的 **Product Quality Reviewer Agent** 以独立 attempt 执行。它只读 exact frozen Problem Definition Candidate，以及该 Candidate 绑定的 Evidence Map/References、Learning State/Round Deltas、Knowledge Snapshot、Product Memory Snapshot、Assumption checkpoint 和已记录分歧，使用专门的 review Skill；可以与主 Agent 使用同一模型，但必须采用隔离上下文，不能继承“把自己的候选判为正确”的会话目标。未来可以通过 Connector 选用 Claude 或其他外部 Agent，但外部模型不是一期正确性的前提，也不改变 Finding 合同。

Reviewer 只能输出 versioned advisory Finding 与审查建议；它没有 Candidate 编辑、Owner 代签、Run State 写入、Ready 宣告、批准或阻塞权限。需要法律、安全、隐私等专业事实时可以形成 Evidence Request，交真实外置专业团队判断；它不是 Development Graph、Test Graph，也不能把角色扮演成专业责任人。Reviewer 结论用于修订和聚焦外置审核，不代替 Owner 的 Product Decision，也不因关注等级阻止进入该决定。

独立 attempt 不是为了增加一个模型调用，而是为了避免四类结构性冲突：同一生成上下文倾向维护原答案；上游内容或提示注入可能说服 Reviewer 跳过规则；概率性输出无法保证同输入同结论；Agent 自评难以形成稳定回归测试。隔离 Reviewer 可以改善语义独立性，但仍是概率判断，所以只能提供结构化输入给后续程序化 Gate，不能成为最终状态写入者。

Reviewer 重点检查：

- 用户、场景、目标、阻碍、影响和期望改变是否相互一致，是否足以让下一步理解“谁在什么情况下遇到什么问题”。
- 问题陈述是否描述用户/业务结果，而不是把用户、PM、Sponsor 或 Agent 提出的方案偷渡为问题或既定方向。
- 关键主张是否回指当前 `problem.evidence.map.v1` 版本及 Evidence References，或明确标记 Unknown/Assumption；Review 不能补造缺失 Evidence。
- SOURCE_ASSERTION、授权、偏好和 VERIFIED_CLAIM 是否被错误混用；同源重复是否被伪装成独立交叉验证。
- 单例反馈、特定版本、局部行为或特定角色结论是否被越过适用范围外推；scope/non-problems 是否清楚。
- 症状、相关性与因果是否被混淆；当前“阻碍”是否只是尚未证明的根因解释。
- 反证、替代解释和最强反方是否被认真处理，而不是为了形式制造稻草人。
- Unknown 是否被隐藏、弱化或错误消除；remaining Unknown 是否会改变拟议下一行动。
- Candidate 对当前拟议 action 是否 relevant，是否应先返回补证、升级 Owner、重新评估路线或重新综合，而不是直接进入决策。
- 是否存在确认偏误、局部最优、虚假战略紧迫性或只优化文案却未修复认知缺口。

它复用通用 advisory Finding 合同。每条 versioned Finding 至少包含：命中的检查维度、直白 concern/关注等级、exact Candidate/Evidence refs、结构化依据与不确定性、可能影响，以及建议 `repair_path`：

- `REVISE_SYNTHESIS`：Evidence/问题框架没有 material change，只需基于同一 exact inputs 生成新的 Candidate 版本；Reviewer 不直接编辑。
- `RETURN_TO_LEARNING`：缺口或新反证可能改变用户/场景/目标/阻碍/影响，携新 MVU 返回 Learning。
- `NEEDS_OWNER`：产品取舍回 Product Decision；专业事实或判断保留给外置专业团队。
- `ROUTE_REEVALUATION`：现有 destination 可能不再适用，只提交 route re-evaluation recommendation，不能由 Reviewer 直接改路。

Finding 与建议都绑定具体 action/scope；Reviewer 不能直接写状态，也不能把“重点关注”扩大成整个 Run 的阻塞。普通分歧优先形成 Finding 和明确建议；未解决项在同源内审意见中披露给外置团队，不在一期升级成 BPG formal Block。

首次 Review 对完整 Candidate 和全局不变量做 full review；Optimizer/Synthesis 产生新版本后，后续 attempt 以 material delta 和未解决 Finding 为重点，但仍必须回归检查方案未偷渡、Evidence/Unknown/范围边界等全局不变量，不能因“只看 diff”漏掉系统性回归。每轮冻结 Candidate、Review refs、Finding disposition 和修复 delta，不原位覆盖。

若连续 Review–repair 没有解决 material Finding、只改变措辞、Finding 在相同原因上反复出现，Reviewer 返回 `NO_PROGRESS` 诊断并建议 `RETURN_TO_LEARNING` 或 `NEEDS_OWNER`；不得无限执行文案 Review–Optimize 循环。面向 Junior PM 的默认 Review Summary 先展示少量关键 Finding、为什么重要、影响哪个动作、Agent 首选修复建议和下一步；完整 Finding/证据/版本链仍可展开审计，不能只抛术语或一整页问题清单。

### 9.6 Problem Ready 与 Product Decision 的单一责任边界

> **CONFIRMED HITL SIMPLIFICATION**：固定 `problem.owner.confirm` 已取消，不保留未实现的兼容 alias、独立 acknowledgement/confirmation record 或 legacy event。原链路让同一 Owner 先确认 Problem Definition、紧接着再在 Product Decision 选择 outcome；前一次点击没有增加新的证据、权限或责任。

当前链路是：Problem Definition Candidate → 独立 advisory Product Quality Review／必要修订 → `problem.ready.gate` → `product.decision`。Decision Brief 在同一屏从 exact Problem Definition Candidate 渲染问题摘要；Owner 选择 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT`，即表示这项选择以该 exact Problem Definition 为决策依据，不再弹“我已理解/确认问题”。`NO_PM_INTERVIEW` 仍只禁止探索期 PM 访谈；Product Decision 的 Owner choice 是正式产品决定，不是访谈，不能被跳过。

若 Owner 在 Decision 交互中认为用户、场景、目标、阻碍、期望结果或 scope materially 错误，Agent 不能在 Decision Draft 中静默改写 Problem Definition。它必须返回 `problem.synthesize`；若需要新 Evidence 或重构问题框架，则返回 `problem.learning.loop`，形成新 Candidate、重新完成受影响 Review/Ready 后再进入 Decision。纯格式或不改变语义的表述澄清可按既有 format-only 规则重渲染，不制造新确认。

`problem.ready.gate` 仍由 Deterministic State Controller 自动、无感执行，只回答“当前问题是否足以进入 Product Decision”。它只检查三类机械条件：

1. exact Problem Definition Candidate 是 current/materially valid，未 stale、invalidated 或 superseded，ref/hash 可解析。
2. exact Product Quality Review attempt 已完成，所有 advisory Finding 都有无损 disposition 与 repair path；关注等级、未采纳 concern 或普通 Unknown 本身不阻塞，只有 Review attempt/记录缺失或 Candidate 版本错配使 Gate 失败。
3. Candidate 绑定的 Evidence Map、Learning State、Synthesis Result、Knowledge/Product Memory 等 required refs、状态和 version/hash 一致可解析；Learning 必须是 `COMPLETED + READY_FOR_SYNTHESIS`，不能读取可变 `current/latest` 推断。

输出只有 `READY` 与 `NOT_READY`。`READY` 原子写入状态/Audit 并进入 Product Decision；`NOT_READY` 必须列 exact unmet condition 和 deterministic repair target，例如 `REBUILD_CANDIDATE / COMPLETE_REVIEW_DISPOSITION / REBIND_UPSTREAM_REF`，不打分、不增加确认 UI，也不把 Reviewer 建议冒充 veto。Unknown/证据不足可以透明进入 Product Decision，因为 Owner 可合法选择 Research、Experiment、Wait 或 Stop；此 Gate 不检查 action、PRD、研发、上线或发布 Ready。

当前操作者仍由项目配置/Host identity 识别为有权 Product/Decision Owner；Agent、Reviewer、subagent 和 Connector 不能冒充 Owner。外置汇总审批继续在 Graph 外，BPG 的 Product Decision 不等于组织最终批准。未来若出现无权 Junior PM，再根据真实身份与消费者设计 escalation；一期不提前建设。

### 9.7 Discovery 循环预算

```yaml
loops:
  discovery_learning:
    max_interview_rounds: 5
    no_progress_rounds: 2
  review_optimize:
    max_rounds: 3
    no_progress_rounds: 2
  knowledge_rebase:
    max_rebases_per_run: 3
```

达到预算不自动构成完成。已有 Evidence Request 仍有合理返回路径时进入 `WAITING_FOR_EVIDENCE`；负责人主动暂停时进入 `PAUSED`；若继续学习已无可行路径且关键缺口阻止任何当前允许的行动，则以 `COMPLETED + INSUFFICIENT_TO_PROCEED` 结束，并记录已尝试、缺口、原因、建议和 restart condition。不得因预算耗尽伪造 `READY_FOR_SYNTHESIS`，也不得用“建议 Experiment”绕过证据、测量或回滚底线。预算限制交互和执行成本，不规定必须收集多少来源。

项目可以覆盖默认值，但必须记录理由。总尝试安全上限默认为 `4 × 当前 Run 可达节点数`；达到上限进入 `BLOCKED_BUDGET`，由负责人决定缩小范围、增加预算或终止。人类等待时间不计入模型执行预算。

模型调用数、活跃执行时长、等待时长和上下文用量必须记录；前三个真实项目用于调整预算，不在文档阶段声称成本已经验证。

---

## 10. Product Decision

**阅读卡——产品决策（`product.decision`；节点形态、结果/记录最小合同、MVU 驱动的选择 guide、STOP/WAIT/future COMMIT 边界、action-risk classification 与节点终止路由已 `CONFIRMED`；完整领域治理与剩余 materiality 细节仍 `PENDING REVIEW`）**

- **做什么**：在问题已经足以被决策后，选择 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT`，并说明承诺是否现在激活规划。
- **为什么**：理解一个真实问题不等于应该立即建设；还需要比较价值、时机、机会成本、风险、证据和组织授权。
- **AI 做什么**：先形成 Decision Brief，给出首选建议、关键依据、判断边界和什么新信息会改变决定；最强反方只在 material 时外显，只在风险或关键未知需要时编排 bounded adversarial/domain sub-agent Review。
- **人做什么**：有权 Product Decision Owner 承担选择和风险接受；其授权不能把低置信度假设变成事实，也不能越过不可豁免政策。
- **主要产物与完成**：节点运行中可保存 versioned Decision Draft/checkpoint 以跨会话恢复；只有 Owner 明确选择后形成的 Decision Record 和 Controller transition validation 后写入的 route 是正式边界。五种结果、通用/结果专属最小记录、MVU guide、STOP/WAIT/future COMMIT、R0—R3 轻量 action-risk classification 与终止路由已确认；完整领域治理和剩余 materiality 扩展仍为 `PENDING REVIEW`。

Product Decision 的原则是：

> **审慎地做，大胆地停。**

默认状态是 `NOT_APPROVED`。Graph 的成功指标不是生成了多少份 PRD、把多少信号转成需求或推进得多快；避免一个不值得做的项目，或者在证据失效时及时停止，同样是完整且有价值的产品结果。

### 10.1 风险分层，以及授权与事实分离

> **CONFIRMED ACTION-RISK CLASSIFICATION**：R0—R3 是 `product.decision` 内部、条件化、由 Agent 自动完成的轻量分类，不是独立 Graph Node、Gate、PM 表格，也不判断问题价值。风险绑定的是**当前拟议 action 及 exposure**，不是问题的永久标签；同一问题在内部原型、小流量实验和全量执行时可以分别属于不同等级。

风险等级按最坏可信伤害、暴露范围、可逆性、数据与用户影响确定，而不是按代码行数或开发成本确定：

| 等级 | 拟议 action / exposure 的典型范围 | 对后续行动的最小含义 |
|---|---|---|
| `R0` | 仅内部验证、离线模拟，无真实用户、敏感数据或外部承诺 | 可继续内部分析/原型；不把“内部”外推为可上线 |
| `R1` | 受控低风险、小范围、伤害上限清楚且可回滚 | 可进入受限执行准备，并在下游补齐范围、监控与回滚 |
| `R2` | 定价、关键流程、真实数据、公开承诺或其他重要用户/业务影响 | 增强证据、Review 覆盖与直白风险披露，供当前 Owner 和外置审核聚焦 |
| `R3` | 安全、隐私、合规、资金、不可逆数据、重大品牌/人身等高关注领域 | 继续思考、比较和写 PRD，但必须将高关注事项、依据、影响与专业建议清楚带入 Released companion review view 和外置团队审核；一期 BPG 不自行批准或否决 |

条件化执行规则是：`STOP / WAIT` 通常不展示风险等级；`RESEARCH` 只有在会接触真实用户、敏感数据或外部沟通时才分类；`EXPERIMENT / COMMIT` 必须运行轻量判断。Human View 只在风险会改变下一步时，用大白话展示等级、原因和对后续的影响，不展示复杂分数或要求 PM 填表。Agent 无法判断时显式记录 `RISK_PENDING / UNKNOWN`，不得默认降为低风险；只有缺失信息会改变风险等级或当前 allowed action 时才打断用户，否则保留 Unknown 并交下游检查。

代码生成和实现成本下降，只降低了部分开发成本，并不自动降低用户伤害、错误决策、数据污染、运维、合规、品牌和机会成本。风险分类必须引用拟议 action/exposure 及依据，不能由 Agent 为了走快线自行降级。R3 不自动阻止 Problem Definition、Product Decision、Product Planning、PRD Ready 或本地 Released；它提高内审覆盖、披露和外置审核关注度。当前 BPG Reviewer 无权把自己的专业建议升级为组织批准/否决。一期也不建设 Domain Owner Gate 或 Waiver；只有未来进入无人值守研发/发布且外置团队不再承担最终责任时，才根据真实组织身份和责任另行设计。

Decision Record 必须把两条轴分开记录：

```yaml
authorization:
  basis: sponsor_directed | product_owner | policy | delegated
  owner: role-and-identity-ref
  scope: allowed-action-and-exposure
  expires_or_recheck_at: ...
epistemic_status:
  confidence: LOW | MEDIUM | HIGH
  evidence_refs: [...]
  evidence_gaps: [...]
  disputed_claims: [...]
```

有权 Owner 可以接受不确定性并作出产品选择，但授权不能修改 `epistemic_status`、把假设升级为事实，或让高风险 concern 从内审/外置审核材料中消失。Sponsor-directed `COMMIT` 是一种组织决定 profile，不是“证据已经充分”的别名；BPG 内的 Owner choice 也不等于外置团队审核或发布批准。

### 10.2 五种正式结果

> **CONFIRMED OUTCOME & HUMAN EXPRESSION CONTRACT**：内部 Schema、状态、路由和审计继续使用稳定 machine enum；但所有面向 PM/程序员的 Decision Brief、交互、Decision Record 摘要、人类视图和 Handoff 都不得只返回裸 code/单词。本轮已确认五种结果的基本含义、默认显示语、§10.2.2 的 MVU guide、§10.2.3 的 STOP/WAIT/future COMMIT 边界、§10.3.1 通用最小合同、下表被选结果的最小补充及 §10.1 轻量 action-risk classification；完整领域治理和剩余 materiality 细节仍待后续 Review。

| Machine enum | 默认中文 display label / 大白话结论 | 基本边界 | 被选结果的 `outcome_details` 最小补充（`CONFIRMED`） | 是否进入 Product Planning |
|---|---|---|---|---:|
| `STOP` | **现在不做，结束当前方向。** | 当前方向终止；有新证据或重启条件满足后才能重新决定 | `restart_condition`；当前没有可信重启条件时显式记录 `NO_CURRENT_RESTART_CONDITION` | 否 |
| `WAIT` | **值得继续关注，但暂时不作承诺。** | 可以保持 exploring/candidate，但不得冒充 committed | `why_not_now` + `review_time_or_trigger`，不得用复查安排伪装 committed 承诺 | 否 |
| `RESEARCH` | **先补充关键信息，再决定是否投入。** | 只授权补证/研究，不等于已决定建设 | `decision_question` + `sufficient_evidence_condition` + `research_stop_condition`，防止无限研究 | 否 |
| `EXPERIMENT` | **先做小范围实验，用真实结果验证。** | 以受控行动购买信息，不等于长期产品承诺；复用同一 Product Pipeline | `key_unknown` + `exposure_and_risk_boundary` + `result_to_continue_iterate_stop_mapping`；详细实验内容进入同一 Plan/PRD 的条件化 section | 是；以实验 delivery intent 进入，结果作为新 Evidence 返回 Decision |
| `COMMIT` | **正式决定要做，并确定何时开始。** | 形成产品承诺，但是否立即 Planning 由 `planning_activation` 决定 | `planning_activation`；非 `NOW` 另记 time/trigger/recheck，所有 COMMIT 记录 stop/review condition；详细规划留给 Product Planning | `NOW` 才进入；其余进入 committed Roadmap |

每个 human-facing 结果必须同时回答：**为什么是这个选择、判断边界/最大不确定性是什么、接下来会发生什么、什么条件会让决定改变**。推荐不能退化为五个按钮或一句“请选择”：默认完整建议句为“我的首选是『中文结论』，因为……；当前判断边界是……；下一步是……；如果……，建议改判为……”。最强反方只有 material 时才补一句。这是一种可审计的结构化表达，不要求暴露 hidden Chain-of-Thought。

`COMMIT` 的 `planning_activation` 只有三种；human view 同样不得只显示裸 code：

- `NOW`：**正式决定要做，现在开始进入产品规划。**当前授权、资源和依赖允许启动；创建父 Product Plan Run。
- `SCHEDULED`：**正式决定要做，但按约定时间重新确认后再开始。**形成 committed Roadmap Item，记录时间范围、Owner、依赖和重新检查点；到期不自动启动，必须验证条件并形成 activation event/新版本。
- `CONDITION_TRIGGERED`：**正式决定要做，满足约定条件并重新确认后再开始。**形成 committed Roadmap Item，记录可验证触发条件、Owner、依赖和超时/失效条件；触发前不创建 Plan Run。

Machine enum 仍可在 human view 中作为辅助标识，例如“现在不做，结束当前方向（`STOP`）”，便于研发、日志和 API 对照；但 code 不能替代结论。Human Renderer 必须从同一个 exact Decision Record 生成这些表达，不单独保存第二份“人话决定”，也不能让翻译或模板改变正式 outcome。

#### 10.2.1 默认“一屏决策”与渐进展开

默认 Human View 不是极端压缩的一句话，也不是把完整 Evidence Map、认知分析和风险报告全部铺给 Owner。它使用下面的一屏信息预算：

1. **一个明确首选建议**：使用 §10.2 的直白中文结论，不让用户先从五个选项里猜 Agent 倾向。
2. **最多三个真正关键依据**：只保留会支撑当前选择的最高价值依据；不是把全部 Evidence 改写成摘要。
3. **最多一个真正改变结论的认知提醒**：例如显式标注“框架审计：我们此前把症状当成原因”；只有 materially changed decision 时才展示，不输出认知框架清单。
4. **一个判断边界**：用定性 confidence 加“最大 Unknown”或“翻转条件”表达；不使用裸百分数伪装精度。
5. **一个具体下一步**：说明谁接下来做什么，以及当前选择会进入哪条路径。

最强反方只在 material 时增加一句；没有可信且会影响责任边界的反方时不为模板完整强制制造。完整 Evidence、其他合法选项、完整 Cognitive Analysis、风险/反方、历史 Decision/Roadmap 与 Audit 作为按需展开层，默认一屏可以定位并打开，但不重复保存内容。

认知基座和 Analysis Method 在内部可以运行得更重；默认只外显 **一个确实改变决定** 的发现。其余可审计内容保存为结构化 rationale、引用与事件，不保存或重建 hidden Chain-of-Thought。默认视图、展开层和 Audit View 都从同一个 exact Decision Draft/Record 与引用渲染，不创建新的业务 Artifact、Graph Node 或第二真源。

`decision` Profile 的 Validator 检查上述关键项、数量预算、展开入口和 source binding，但不使用僵硬字数上限。重大安全、合规、资金、隐私或不可逆风险必须在默认层清楚披露；当必要披露超过一屏时，风险透明优先于版面预算，不能以“保持简洁”为理由折叠关键伤害、硬约束或 Owner 责任。

“值得做但以后做”由 `COMMIT + SCHEDULED / CONDITION_TRIGGERED` 表达，不新增 Router 业务分支。`WAIT` 可以把问题放入 exploring/candidate Roadmap 并记录重启条件，但它不是交付承诺，不能显示为 committed。“最小价值切口”属于 `COMMIT + NOW` 或后续合法激活之后的 Planning / Shaping，不是证明一个方向值得做的证据。`EXPERIMENT` 可以用于获取关键证据，但不能用“先小范围试试”绕过不可控风险、不可测问题，或已经明确不可执行、不可豁免的法律与项目政策约束；R3 只强化披露和外置关注，不构成一期内部 Reviewer Gate。

#### 10.2.2 `RESEARCH / EXPERIMENT / COMMIT` 的统一判断 guide

> **CONFIRMED DECISION GUIDE**：不使用固定分数或机械阈值，也不允许 Agent 凭感觉漂移。先识别当前 **Most Valuable Unknown（MVU）**，再选择能以最低总成本取得、且可靠程度足以改变当前决定的证据方式。

| 候选结果 | 何时是首选 | 必须守住的边界 | 为什么不选最相近替代 |
|---|---|---|---|
| `RESEARCH` | 关键未知可以由现有知识、行为数据、访谈、外部研究或离线验证回答，不需要把变化真实暴露给用户 | 必须写清 `decision_question`、`sufficient_evidence_condition` 和 `research_stop_condition`；普通授权检索仍留在 Learning，不为显得正式而升级 | 若可靠答案必须来自真实用户行为/运行结果，Research 不足；若核心方向已足够，继续研究只是拖延 |
| `EXPERIMENT` | 关键答案必须从真实行为或运行结果获得，且 action 可控、可观测、可停止、可回滚，继续主观讨论的信息价值更低 | 复用同一 Product Pipeline；必须能说明验证什么、如何观察、伤害如何受限及如何停止/回滚。实质不可逆或无法限制严重伤害的 action 不能伪装成实验 | 若离线证据已足以回答，应先 Research；若核心价值/方向已经足够且剩余 Unknown 只影响实现，继续实验可能是在回避承诺 |
| `COMMIT` | 核心用户价值和方向证据已足够；remaining Unknown 不会改变“是否做”，主要影响实现、范围或迭代方式；团队愿意承担长期维护、机会成本和持续责任 | 代码生成便宜不等于产品总成本为零；仍需显式承诺范围、action risk、停止/复查条件和后续 Planning activation | 若最关键价值判断仍需真实行为验证，应先 Experiment；若可由离线信息回答，应先 Research |

Agent 必须形成**一项首选建议**，不能先把五个结果作为菜单交给 PM。默认一屏 Human View 复用 §10.2.1：直白首选、二至三个关键依据、当前 MVU、为何当前不选最相近替代、建议成立/翻转条件和一个具体下一步。认知基座与 Better Question 可以内部检查隐藏预设、no-action counterfactual、二阶影响和主要矛盾，但只外显真正改变选择的一项发现；固定框架 checklist 或多个 lens 同意都不能提高 Evidence confidence。

Owner 可以接受或选择其他 outcome；material 不同时复用 §10.3.2 的一次 bounded substantive challenge，而不无限争论或静默迎合。证据充分度、研究/实验信息价值、市场窗口和实现成本都是 advisory 判断。`EXPERIMENT` 的确定性产品合同仍要求说明验证问题、可观察结果、exposure、停止/回滚和伤害边界；缺项时相应 PRD 尚不完整，但这不是 Reviewer 的 veto。安全/隐私/合规等 Reviewer 对高风险 action 只形成重点 concern 并交外置团队最终审核，不能把自己的角色建议扩张成整个 Run 的 blanket block。

考虑过但拒绝三种做法：纯 Agent 自由判断会随模型和上下文漂移；固定评分把不完整证据包装成伪精确；让 PM 直接自选菜单会放弃 Better Product Graph 对 Junior PM 的专业辅助。本 guide 复用 Decision Record、action-risk、disagreement 与 Controller route，不新增 Node、Gate、Artifact、HITL、评分器或第二模板。

#### 10.2.3 `STOP / WAIT / future COMMIT` 与长期重审

> **CONFIRMED COMMITMENT BOUNDARY**：`STOP`、`WAIT` 和“已经决定未来做”必须严格分开。

- `STOP`：**现在不做，结束当前方向。**停止继续消耗主动注意力；Record 保存 restart condition，或明确 `NO_CURRENT_RESTART_CONDITION`。
- `WAIT`：**价值仍可能成立，但现在不作承诺。**必须至少有 review time/window 或可验证 re-evaluation trigger。两者都给不出时，Agent 应首选建议 `STOP`，不能把“以后再说”伪装成 Roadmap；有权 Owner 仍可选择 WAIT，但必须记录理由和接受的不确定性。
- **未来承诺**：已经决定未来做必须使用 `COMMIT + SCHEDULED` 或 `COMMIT + CONDITION_TRIGGERED`，承担相应 Owner、时间/触发、依赖与复查责任，不能写成 WAIT。

`STOP` 和 `WAIT` 都必须进入 immutable Decision Record/Ledger。除 §10.3 的共同字段外，系统保留当时 exact Problem/Evidence/Knowledge snapshot refs、关键 assumptions、选择理由、Agent recommendation/最强 material 反方、Owner choice、scope、机会成本、被拒 alternatives、restart/review condition、监控 signal（如有）与 next action。它们是对当时认知和责任边界的完整记录，不是“没做所以不记录”。STOP 新事项通常不占 active Roadmap；WAIT 只投影为未承诺的 `exploring / candidate`；只有未来 COMMIT 才进入 `committed`。

外部环境、Knowledge、typed result 或新 Signal 到来时，仍通过统一 `signal.ingest` 与 `signal.relate`/`existing_links` 关联 exact historical Decision。只有新信息命中 restart/recheck condition、可信挑战 key assumption，或形成 material risk/opportunity 时，才给 Owner 展示一屏重审提醒：“当时为什么停/等、什么条件会触发、现在出现了什么、Agent 是否建议改判”。普通支持性信息进入阶段摘要，不周期性无差别唤醒全部 STOP/WAIT，避免 alert fatigue。

重审永不改写旧 Record。Owner 维持原决定时追加 review result、理由与下一条件；改变时创建新的 immutable Decision Record/version，显式 `supersedes` 旧决定，并更新 Decision Ledger、Roadmap、Product Changelog 与 exact Impact。新结果仍可为五种 outcome 中任一种。Core 一期不建设常驻 watcher/service：无 Connector 时由自然语言/显式 Skill、`status/resume` 或人工 inspection 带入新信息；未来 scheduler/Connector 只能提交 Signal 或触发检查，不能自动推翻决定。

拒绝四种替代：删除 STOP 历史会制造组织失忆；无期限无触发 WAIT 会变成垃圾箱；新证据自动推翻会越过 Owner；周期性全量重审会制造提醒噪声。本规则复用现有 Decision/Roadmap/Impact/Changelog/Audit，不新增 Node、Gate、Artifact、固定 HITL 或永久监控进程。

### 10.3 执行结构与 Decision Record

> **CONFIRMED NODE SHAPE**：`product.decision` 是一个独立、可恢复的 Graph Node。此前候选设计中的五个串行节点

```text
decision.risk.review
→ decision.options.compare
→ decision.challenge
→ decision.owner.confirm
→ decision.outcome.route
```

不再注册到 Graph Manifest，也不各自拥有独立状态、重试、Ready 或恢复边界。它们收敛为 `product.decision` 内部可编排能力：

1. **AI Decision Brief**：绑定 exact Problem Definition Candidate、Evidence/Unknown、Knowledge/Product Memory、历史 Decision/Roadmap 与当前约束，形成 Agent 首选建议、关键依据、判断边界和会改变建议的信息；最强反方只在 material 时外显，不能只罗列选项。
2. **按需 Review**：仅当风险、关键未知或专业域政策需要时，向 bounded adversarial/domain sub-agent fan-out；默认不全量调用 Product/Engineering/Testability/UX/Domain Reviewer，也不把 Reviewer 数量当作决策质量。
3. **Owner 讨论与挑战**：主 Agent 用 Brief 和 Review Finding 与当前有权 Owner 讨论、解释和挑战，保留分歧；Agent 不替 Owner 选择。
4. **Owner 明确选择**：有权 Product Decision Owner 在 Agent 先按 §10.2.2 给出首选并按需完成一次 §10.3.2 challenge 后，明确选择五种结果之一；Controller 不替代 Owner。
5. **确定性路由**：State Controller 校验 exact Decision Record、Owner identity/authorization、适用 policy/constraint 与目标边后，唯一写入正式状态和 route；Agent、Reviewer 或 Draft 不能自行路由。

这些是内部动作/能力，不是新的 Graph Node。节点可把 AI Brief、Reviewer 结果、讨论分歧和未完成选择保存为 versioned、run-local `Decision Draft/checkpoint`，在通用 Run State 声明的等待、暂停或可重试失败状态下跨会话恢复；checkpoint 必须绑定 exact inputs、版本/hash 和 supersedes，但不是正式 Decision Record、承诺或 route。只有 Owner 明确选择后冻结的最终 Decision Record，以及 Controller 基于该 exact Record 写入的 route，构成正式持久边界。

价值、可用性、可行性和商业合理性仍可作为内部风险/方向透镜，评估的是**待选方向**，不是审核 PRD 文档。是否调用某个透镜或专业 Reviewer 由当前风险和未知驱动，不固定为全量流水线。五种结果、MVU guide、STOP/WAIT/future COMMIT、Decision Record 通用最小合同和 outcome 最小补充已经确认；完整领域治理与剩余 materiality 扩展仍待后续确认。

在给出推荐前，Agent 至少必须回答：

- 如果什么都不做，会发生什么？
- 为什么必须是现在，而不是更早或更晚？
- 与当前候选事项相比，它为什么优先级更高？为此放弃了什么？
- 哪些前提必须为真，当前证据和置信度是什么？
- 当前授权依据、授权范围和 epistemic confidence 分别是什么？
- 什么新证据会让我们停止或改判？
- 当前推动力是否主要来自沉没成本、领导要求、竞品动作或交付惯性？
- 风险能否通过研究或可逆实验回答，而不是直接承诺建设？

#### 10.3.1 Decision Record 通用最小合同

> **CONFIRMED MINIMUM CONTRACT**：Decision Record 记录“Owner 决定了什么、适用于哪里、为什么、何时改判、接下来做什么”。它不是分析报告、PRD 或让 PM 手填的系统元数据表。

Agent 先根据 exact Decision Draft 预填，Owner 在一屏中确认或修改。Owner 对 exact outcome/scope 的清晰自然语言表达本身即可构成 choice；系统据此冻结 Record，不再追加第二次“是否确认”点击。Owner 默认只需关注五项：

1. **Chosen decision**：用 §10.2 的直白中文明确当前选择，同时保留 machine enum 供审计。
2. **Applicability scope**：明确适用的 product、user、scenario 与 boundary，防止把局部决定外推成全局规则。
3. **最多三个关键理由**：只保留真正支撑 Owner 选择的理由，不把完整分析搬进确认页。
4. **最大 Unknown 与改判边界**：记录最大未知，以及对应的 flip / stop / restart condition；不同 outcome 的必要补充见下文。
5. **具体下一动作**：明确 next action 及相应 checkpoint 或 trigger。

当 Agent recommendation 与 Owner choice **materially 不同**时，确认页才按 §10.3.2 额外显示 disagreement；没有 material 分歧时不为了模板整齐占用默认视图。§10.2.1 的“一屏决策”是推荐/讨论层的信息预算；本节是 Owner 最终确认层，必须优先呈现 applicability scope 和 exact chosen decision。二者都从同一 Decision Draft/Record 渲染，不是两份产品决定。

以下字段由系统从 exact inputs、Host identity、Controller 事件与下游引用自动填充，不要求 PM 重复录入：

- Decision ID、version、timestamp、actor identity。
- exact Problem Definition Candidate、Problem Evidence Map、Knowledge Snapshot 和 Review refs/hashes。
- Agent recommendation 与 Owner result；有 material 分歧时绑定 §10.3.2 的 challenge 与完整条件字段。
- 按 §10.1 适用性自动形成的 action-risk classification：拟议 action/exposure、`R0—R3 | RISK_PENDING`、理由、证据引用与对 allowed next action 的影响；不适用时不生成空表。
- `supersedes` 与 `superseded_by` 关系：新 Record 写入 `supersedes`；旧 Record 的反向 `superseded_by` 由 append-only Ledger/关系索引解析，不原位修改旧内容。
- Roadmap、Experiment、Product Plan 与 PRD downstream refs。
- 完整 cognitive rationale 与 Audit refs；只保存结构化理由和引用，不保存 hidden Chain-of-Thought。

Owner 清楚表达 choice 后，系统生成 immutable、versioned Decision Record，不再要求一次重复确认。任何会改变 chosen decision、适用范围、关键理由、判断边界、下一动作或 outcome 最小补充的 material change，都必须创建新版本并显式 `supersedes` 旧版，不能原位覆盖。默认 Human View、渐进展开和 Audit View 都从这一个 Record 及其 exact refs 渲染；视图不是第二真源。

#### 10.3.2 Agent–Owner material disagreement

> **CONFIRMED DISAGREEMENT CONTRACT**：原则是**不迎合，也不阻挠**。Agent 保留专业意见，Owner 承担权限范围内的最终产品决定，Record 保留真实证据状态与责任边界。

Agent 必须先给出明确首选及理由。Owner 选择 materially different outcome 时，Agent 只进行**一次 bounded、实质性的挑战**：指出最关键的证据缺口或风险，解释为什么专业首选不同，以及当前选择会把什么不确定性或责任带到下一步。只问“你确定吗”不算挑战；同一证据下反复换措辞、争论或阻塞也不允许。挑战完成后，有权 Owner 可以坚持其选择；无权角色的坚持不能改变正式 Decision。

仅在 material disagreement 时，Decision Record/Human View 条件保存并展示：

- Agent recommendation 与理由。
- Owner decision 与理由。
- disagreement 的实质差异。
- authorization basis 与范围，包括适用的 `sponsor_directed`。
- Owner 明确接受的 uncertainty/risk。
- recheck / stop condition，以及仍有效的 execution constraints。

组织授权本身是事实，但不得因此提升 epistemic confidence、抹去 evidence gap，或被写成用户价值证据。普通、可承担的产品分歧可以继续推进；证据不足但行动可逆、可测时，Agent 应优先推荐 `EXPERIMENT`。若有权 Owner 仍选择 `COMMIT`，Record 必须保留低置信度、accepted uncertainty/risk 和改判条件，不能把 Owner 选择渲染成“已验证”。

R3 或其他专业高关注边界下，Agent 必须把 concern、Evidence、可能影响、专业建议和 Owner 接受的不确定性随 Decision、Plan/PRD、内审意见与 Handoff 继续传递，供外置团队最终审核；不能因 Owner 坚持或 Reviewer 复审而无痕消失。一期 BPG 不让 Security/Privacy/Compliance/Finance AI Reviewer 或所谓 Domain Owner 在内部行使批准、否决或 waiver 权。这里不新增 `OVERRIDE`、`SPONSOR_COMMIT` outcome、Graph Node 或第二套决定；未来无人值守治理另进 Roadmap。

#### 10.3.3 被选 outcome 的条件化最小补充

五种结果共用同一个 Decision Record 和上述通用字段，不建立五套模板、五个子节点或五份并行记录。系统只为 **chosen outcome** 生成一个条件化 `outcome_details`；未选择结果的字段不得以空对象、`null` 清单或占位章节污染 Record/Human View。

- `STOP`：记录 `restart_condition`；若当前确实没有可信重启条件，明确 `NO_CURRENT_RESTART_CONDITION`，不伪造未来理由。
- `WAIT`：记录 `why_not_now` 与 `review_time_or_trigger`；复查安排不等于 committed Roadmap，也不能被显示成“已决定要做”。
- `RESEARCH`：记录要回答的 `decision_question`、何种证据足以重新决策的 `sufficient_evidence_condition`，以及防止无限研究的 `research_stop_condition`。
- `EXPERIMENT`：记录 `key_unknown`、`exposure_and_risk_boundary`，以及结果如何对应 continue / adjust / stop 的最小 mapping；详细变化、测量、流量、kill switch/回滚等由 §10.4 规定进入同一 Product Plan/PRD 的条件化实验内容，不在 Decision Record 重复维护。
- `COMMIT`：记录 `planning_activation=NOW | SCHEDULED | CONDITION_TRIGGERED` 与 `stop_or_review_condition`；非 `NOW` 还必须记录 time/trigger/recheck。模块、迭代、依赖与详细范围由 §11 Product Planning 形成，不在 Decision Record 预写一份缩小版 Plan。

Human View 只展示被选 outcome 的附加信息；机器合同和 Audit 仍指向同一 Decision Record。上述是 outcome 专属**最小补充**，不代表各 Domain Gate 的具体实现、Experiment 完整合同或 downstream Planning 已经在本节点确认。

#### 10.3.4 按 materiality/risk 扩展（候选，待后续 Review）

以下是此前累积的扩展候选。它们不是 Owner 通用五项确认表，也不是所有微小决定的强制字段；哪些由 materiality、risk 或具体 outcome 触发，仍待后续 Review：

- 状态、完整影响范围和当前结果的扩展解释。
- 选择的方向、决定理由和被拒绝方向及其未选理由。
- 证据、epistemic confidence、evidence gaps 和争议主张。
- 事实、假设和仍待验证前提。
- authorization basis、Owner、范围、有效期/复查条件，以及 sponsor-directed / accepted-risk profile（如适用）。
- 风险等级、判断依据、可逆性、适用硬 Gate 和风险接受记录。
- 机会成本、被牺牲的候选项和“什么都不做”的后果。
- 关联 Eval 和其他受影响对象的确切版本引用；Plan、PRD、Experiment 与 Roadmap 的通用 downstream refs 已由系统自动维护。
- `COMMIT` 时的 `planning_activation`；若为 `SCHEDULED / CONDITION_TRIGGERED`，记录时间/触发条件、Owner、依赖、复查、超时和失效条件。
- 预先定义的 kill criteria、停止负责人和停止后的处置。
- 超出通用最小合同的重审、失效和跨对象影响条件。

#### 10.3.5 节点结束与确定性路由

> **CONFIRMED COMPLETION BOUNDARY**：不新增独立 `decision.ready`、Decision Ready Gate Node、Reviewer 或 Owner 二次确认。`product.decision` 结束时，由既有 Deterministic State Controller 对 transition request 做节点终止验证；这是正式状态写入前的确定性校验，不是新的业务 Gate、Artifact 或审批。

Controller 只基于 exact records/versioned rules 重算：

1. 当前有权 Owner 的确认绑定 exact、immutable Decision Record。
2. `chosen_outcome` 恰好是 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` 之一。
3. §10.3.1 的通用五项完整且 source binding 有效。
4. §10.3.3 仅存在 chosen outcome 的条件化最小字段，未选项无空合同。
5. §10.1 要求时 action-risk classification 已完成，`RISK_PENDING`、R2/R3 或其他 action-scoped execution constraints 被如实保留。
6. Problem Definition、Evidence、Knowledge/Product Memory、Review/历史 Decision refs current、exact、可解析且没有 material stale/contradiction。
7. material disagreement 已按 §10.3.2 完成一次实质挑战并记录；适用 accepted uncertainty/risk、authorization 和 recheck/stop condition 完整。

全部满足后，Controller 才写入确定性 route；否则 Run 保持在当前 `product.decision`，不创建下游 Run/承诺，并用直白语言列出每项 **unmet condition + deterministic repair target**。不能只返回裸 `NOT_READY`，也不使用分数、概率或“总体差不多”判完成。修复后复用同一节点重新提交 transition request，不增加 Reviewer 或要求 Owner 对未变化的 exact choice 重复确认；material Record change 仍按版本规则重确认。

路由语义固定为：

- `STOP`：结束当前 Decision Run，保留 restart condition / `NO_CURRENT_RESTART_CONDITION`。
- `WAIT`：结束当前主动决策，按既有边界形成 exploring/candidate Roadmap 提议或记录，不得伪装 committed。
- `RESEARCH`：产生后续 research request/path，完成后返回 Product Decision；具体 Research 内部节点形态仍待 Review。
- `EXPERIMENT`：按 §10.4 激活同一 Product Planning→PRD→Review→`prd.ready.gate`→Released/Handoff pipeline，并携带实验 delivery intent；不能绕过同一 Ready 或 action-scoped 风险约束。
- `COMMIT + NOW`：创建 Product Plan Run。
- `COMMIT + SCHEDULED / CONDITION_TRIGGERED`：写入 committed Roadmap proposal/item，不创建 Plan Run；后续仍需合法 recheck/activation event。

Agent 负责推荐、反方和证据，不替代负责人承担决定；Controller 不重新进行语义分析，也不替外置 PRD 汇总审批提前批准组织交付。Product Decision & Roadmap Memory 的完整发布合同、Research 内部形态和所有下游 Ready 继续由各自章节/后续 Review 负责。

### 10.4 `EXPERIMENT`：同一 Product Pipeline 的可逆实验模式

**本节修订并取代 ADR-017/018 的独立 Fast Lane 方案。** `EXPERIMENT` 保留为 Product Decision 的合法 outcome，因为它表达的承诺是“以受控行动购买信息”，不是“长期维护这个产品方案”。但它不再拥有另一条 Experiment Planning/PRD/Review/Ready/Handoff 生产线；Decision 通过后直接激活与 `COMMIT` 相同的 Product Planning、PRD generation、Evals、Review–Optimize、`prd.ready.gate`、self-contained release 和可选 dispatch。

代码生产成本下降使低风险、可逆、可测实验比长期主观空转更有价值，但它没有消除用户伤害、数据污染、运营、合规、品牌、回滚或解释成本。实验模式因此只允许调整**进入实施前的认知与长期规划充分度**：问题细节可以尚未完全确定，长期方案和未来扩展可以未规划，部分分支可以留待学习，团队也不必先形成主观完全共识；所有 Unknown 必须显式保留。它不能把 PRD 简单做薄，也不能降低本次 action 的可执行与安全边界。

同一 Product Plan/PRD 必须条件化表达以下内容；这些 section 是当前正式文档的一部分，不是独立 Experiment Artifact、模板或第二真源：

- exact key unknown / hypothesis，以及本次 action 要回答的 Decision 问题。
- target population、纳入/排除条件、traffic/exposure 上限与 blast radius。
- 这次具体改变什么，明确不改变什么。
- observable evidence / measurement、数据来源、样本/时长、成功/失败/无结论解释边界。
- 结果到 continue / adjust / stop 的预先 mapping；扩大、长期投入或改变方向仍须返回 Product Decision。
- monitoring、risk guardrails、kill/stop criteria、rollback/撤销路径、Owner 和结束时间。

没有明确测量、可观察结果、受控 exposure、停止/回滚或结束条件时，不得把 action 声称为实验；这些缺口由同一个 PRD Review 和 `prd.ready.gate` 阻止对应 release/Handoff，而不是另建 `experiment.ready.gate`。Planning Profile 根据 intent、风险、依赖和复杂度选择：低风险简单实验可以使用 LIGHT；跨模块、R2/R3、不可逆或安全/隐私/合规/资金敏感 action 必须升档并应用相应专业约束。`EXPERIMENT` 本身从不自动等于 LIGHT。

逻辑运行路径是：

```text
EXPERIMENT Decision
→ same Product Planning / PRD generation（delivery intent = EXPERIMENT）
→ conditional measurement + stop / rollback content
→ same Review–Optimize + prd.ready.gate
→ same self-contained Released PRD + optional dispatch
→ downstream typed result → signal.ingest
→ bind exact Decision / PRD / Run → new Evidence
→ return product.decision
```

结果可以被解释为 expand / iterate / stop / inconclusive，但这些只是回到 Decision 的 result disposition/建议，不是新的正式 Decision enum：expand 仍需 Owner 选择 `COMMIT` 或新的受限 `EXPERIMENT`；iterate 需要新的 Decision/PRD version 且不能移动旧成功标准；stop 保留停止原因；inconclusive 不能包装成软成功。Better Product Graph 不执行实验、流量投放或测试 runner，也不能用下游 result 自动改写 Decision。

考虑过但拒绝两个极端。保留独立 Fast Lane 会复制节点、状态、Ready、Handoff 和产物真源；把 `EXPERIMENT` 直接并入 `COMMIT` 则会抹去非长期承诺、学习目标、受控 exposure 和结果回流语义。最终只保留 outcome 与 delivery intent 差异，运行管线完全复用。

### 10.5 并行实验治理：未来能力

一期不建设 Experiment Portfolio，也不把它作为 Roadmap、Decision 或运行状态之外的正式业务真源。单个或少量实验使用既有 Decision、Plan/PRD、Run State、Audit、exposure/measurement/stop 条件与 exact links 即可。

只有真实运行出现足够多的并行实验，并证明受众重叠、互相干扰、共享指标污染、资源冲突或 Zombie 实验无法由现有 Run/Roadmap 关系管理时，才进入 `PROTOTYPE_REQUIRED`：先用真实 Case 明确消费者、最小关系视图和 Owner，再决定是否需要 Roadmap 内视图或独立能力。本版本不预建 Portfolio Schema、Service、Registry、Node、Gate 或第二状态系统。

Kill criteria 仍必须在 action 开始前进入同一 PRD。触发后，Agent 应明确推荐停止，不得通过移动目标、降低成功标准、增加功能或无限延长观察来维持项目；继续需要新的显式 Product Decision，并保留旧版本、触发证据、继续理由与授权，且不能覆盖不可豁免边界。

### 10.6 Product Decision & Roadmap Memory

**本节分工已确认。**这是一组跨节点基础合同，不是一项新的产品工序，也不要求一期引入数据库、事件服务或独立常驻进程。四类记录是**同一份确切 Decision 及其后续事件的不同语义投影**，不是四套审批、四个 Graph Node、四个系统或四份可以分别改写的真源。它们可以存放在同一个文件包/索引中，但不能因为都与“历史”有关就混用：

| 记忆类型 | 回答的问题 | 必须包含 | 不能替代 |
|---|---|---|---|
| **Decision Ledger** | 正式决定了什么、为什么、适用于哪里、谁作出决定、证据/Unknown 是什么、为何/何时可能改判 | 每个正式 Decision（包括 `STOP`）的 exact immutable/versioned Decision Record；通用最小合同见 §10.3，另保存 Agent/Owner 分歧、授权、重审条件、`supersedes` 和下游 exact refs | Roadmap、Product Changelog、Audit Log |
| **Roadmap Registry** | 哪些事项仍具有未来行动意义，当前承诺到什么程度 | 问题/目标结果、`exploring / candidate / committed / in_progress / done / paused / stopped`、优先级理由、时间/触发、依赖/风险、Decision 引用与停止/重启边界 | 决策依据、并行实验组合治理或执行日志 |
| **Product Changelog** | 相对上一具名产品状态，哪些 material 产品意义、承诺、规则或发布边界发生了变化 | material 新增/改变/延期/暂停/停止、理由与 source Decision/Roadmap/release refs、批准者、影响对象和是否需要复审/re-ready | 文档 CHANGELOG、全部 Decision 的副本或执行日志 |
| **Audit Log / Audit Ledger** | 谁在何时用什么版本执行了什么动作、状态如何变化、外部是否真的接收 | 自动追加 Actor、时间、动作、输入/输出哈希、工具/权限、状态迁移和 receipt | 前三类的产品语义、理由或承诺 |

四类视图的 outcome 投影固定如下；这张表决定“写到哪里”，不新增五条流程：

| 正式 outcome | Decision Ledger | Roadmap / 邻接合同 | 不能误写成 |
|---|---|---|---|
| `STOP` | 必须记录，包括理由与 restart condition | 新事项通常不进 Roadmap；若本决定停止的是既有 Item，则把该 exact Item 更新为 `stopped` | “没做所以没有 Decision”或新建虚假未来事项 |
| `WAIT` | 必须记录 | 可选进入 `exploring / candidate`，带复查/重启条件 | `committed` 或已排期承诺 |
| `RESEARCH` | 必须记录 | 通常进入 Research Request/研究路径；除非另有独立未来行动理由，否则不形成 Roadmap 承诺 | `committed` 产品、已批准实施或已获得结论 |
| `EXPERIMENT` | 必须记录 | 激活同一 Product Planning/PRD pipeline 并携带实验 intent；可关联已有 Roadmap Item，但不因此成为 `committed product`，一期无 Experiment Portfolio 真源 | 正式产品承诺、独立实验生产线或实验已成功 |
| `COMMIT + NOW` | 必须记录 | 先由 Controller 创建真实 Plan Run，成功后才进入 `in_progress` | 仅凭 Decision 把尚未创建的工作写成执行中 |
| `COMMIT + SCHEDULED / CONDITION_TRIGGERED` | 必须记录 | 进入 `committed`，记录时间/触发与复查条件；暂不创建 Plan Run | `in_progress` 或已经交付 |

这里的 Product Changelog 记录用户行为、产品规则、路线图承诺和交付/发布边界的 **material 产品意义变化**，不等于本仓库 `docs/architecture/CHANGELOG.md`，也不复制每条 Decision。它应尽量从 exact Decision、Roadmap transition 与 released artifact 自动生成 Proposal/entry，人工只补充“为什么这对产品有意义”，避免四处重复录入。普通 Classification 修正、reroute、澄清、证据追加或执行重试只进各自 history/Audit；只有它同时改变正式 Decision、Roadmap 承诺、产品规则或发布边界时才进入 Product Changelog。

Audit Ledger 继续承担 §20 的运行审计并由 Host/Controller/Connector 自动追加；它可以证明某个 Decision Record 被谁在何时批准、使用哪个版本、状态怎样变化以及是否收到外部 receipt，却不能仅凭一条 `approved` 事件恢复决定内容、理由、未来承诺或产品变化。反过来，Decision/Roadmap/Changelog 也不能替代执行回放。

**所有产品决策都必须记录，但记录重量随影响与风险扩展。**共同最小合同统一使用 §10.3.1 与 §10.3.3，material disagreement 另按 §10.3.2：Owner 只确认五项与 chosen-outcome 补充；系统自动维护 ID/版本/状态/actor、authorization 与 epistemic 边界、exact evidence/knowledge/review refs、recommendation/result、关联对象、supersession 和 rationale/audit refs。“维持现状”等完整备选、机会成本和专业 Risk/Domain Review 属于 materiality/risk 触发的扩展，不强塞进每次 Owner 确认。微小、局部、易逆的决定可以使用紧凑 Decision Record 并内嵌在所属产物中；跨模块、外部承诺、高风险、改变既有规则或影响多个交付物的决定必须扩展完整备选分析、Risk/Domain Review、Roadmap/Product Changelog Proposal 和 Impact List。是否扩展由版本化 materiality/risk policy 判断，不由 Agent 为省事自行降级。

分级只决定扩展字段和 Review 重量，不决定“记不记录”：`local/reversible` 使用最小记录；`material/cross-artifact` 增加完整影响、路线图和产品变化说明；`critical/high-risk` 强化恢复方案、advisory 专业审查和外置团队关注。所有已确认 Decision Record（包括 `STOP`）都立即进入 BPG 本地 append-only/versioned Ledger；低 materiality 项可以批量进入团队共享发布，但不能因不阻塞而被省略。一期不在此引入专业 Owner approval、Waiver 或 Reviewer 硬 Gate。

Roadmap 状态表达承诺阶段，不表达事实置信度：`committed` 必须引用有效 `COMMIT` Decision 及 `planning_activation`；`SCHEDULED / CONDITION_TRIGGERED` 在合法 activation event 前保持 committed、不得伪装成 `in_progress`；`in_progress` 必须另有真实 Plan Run/执行依据，`done` 必须引用达成证据。`WAIT` 只能形成 `exploring / candidate` Item 和重启条件，不能被下游解释为已承诺。时间范围是可审计 horizon，不把未经批准的日期伪装成对外承诺；Router 的 `existing_links` 只增加来源 Signal 与确切历史对象的引用，不改变原 Item 的承诺阶段，也不代替当前 Signal 选择业务目的地。

普通 Classification 修正、reroute、澄清或人工 override 保存在 Classification/Route history 与 Audit Ledger；Product Changelog 不承担 Router 调试日志。

生命周期规则复用 §20.5 的 `artifact.version.guard`：

1. 草稿在负责人确认、被其他产物引用或交付前可以原位修改。
2. 一旦批准、被 Plan/PRD/Eval 或带实验 intent 的下游 Run 引用或交付，版本立即冻结。
3. 修改只能创建新版本或新的 Decision，并显式记录 `supersedes`、变更理由、前后哈希和影响对象；旧版本永久保留。
4. `current` 只是指向某个确切版本的导航指针，不是历史真源，也不能覆盖或删除旧记录。

每份 PRD 必须绑定确切的 `decision_refs`、`roadmap_snapshot_ref`、`product_plan_ref` 和 `knowledge_snapshot_ref`，包含版本与内容哈希；使用“当前决定”“最新路线图”或可变链接不能通过 Ready。Decision 或 Roadmap 变化必须生成可审计 Impact List，逐项列出受影响的 Plan、PRD（含其 delivery intent）、Eval、Ready Assertion 和 Handoff。语义 Agent 推荐影响范围，确定性 Controller 验证引用、记录状态并执行 Gate；不得用一次全量重跑掩盖不准确的影响判断。历史 Decision 受新 Evidence 影响的已确认分级见 §10.7；新证据冲突如何合并、Impact 如何跨团队传播的实现细节仍待后续 Review。

一期用版本化 YAML/Markdown 文件、不可覆盖 artifact 目录、`current` 指针和结构化索引实现四类语义投影。**Knowledge Maintenance Graph 未接入时，BPG 仍可在项目本地完整运行**：保存完整 Decision Ledger、Roadmap、Product Changelog 和 Audit records，并把可供未来 KMG 消费的 raw source exact refs 保留下来；Connector 缺失本身不能让本地 Decision、Planning 或 PRD 生成瘫痪。未来接入后，Knowledge Maintenance Graph 负责团队共享、治理和发布，但不能重新替 Owner 作决定、改写其 outcome 或无痕生成第二份事实。四类视图始终用 exact refs/hash 同源关联；Audit Ledger 记录实际发生的提交、发布、消费和失效事实，但不替代产品语义。提交、Impact 和同步合同仍待 Knowledge Requirements 反推。

### 10.7 历史 Decision 受新 Evidence 影响

**本节规则已确认；它不新增 Router destination。**新 Signal 仍先执行现有 Intake/Router：可能持续重大伤害进入 `INCIDENT_ASSESS`，有可信行为基线且疑似偏离进入 `BUG_BASELINE_CHECK`，其余按 activation 进入 `INBOX_ONLY` 或 `DISCOVERY_START`。同时，`existing_links` 可以关联 exact historical Decision、Roadmap Item、PRD（含实验 intent）或 Incident；“命中历史对象”只建立关系和后续影响输入，不能吞掉本次路线判断。

Agent 将新 Evidence 对 exact historical Decision 的影响分为四类：

| 影响类别 | 含义 | 默认动作 |
|---|---|---|
| `SUPPORTS` | 在原 scope 内支持原决定，没有改变关键假设、风险或执行边界 | 以 append-only evidence link/阶段摘要关联原 Decision，不修改旧 Record、不打断 Owner |
| `NON_MATERIAL_DELTA` | 增加局部信息或缩小/补充某个边界，但不足以改变当前 outcome/action | 记录 exact scope 与局部影响，必要时更新摘要；不重开 Decision、不全量重跑 |
| `CHALLENGES_KEY_ASSUMPTION` | 对原决定依赖的关键假设、适用范围或翻转条件形成可信挑战 | 给 Owner 一屏提醒，并由 Agent明确首选建议：重开 Product Decision、先补证或做受限实验之一；不能只报告“有冲突” |
| `HITS_KILL_RECHECK_OR_MATERIAL_RISK` | 命中既定 kill/recheck condition，或使即将执行的动作出现 material/高关注领域风险 | 标记 exact affected actions/artifacts；Agent 给出暂停、停止、缩小或重决策的首选建议，Owner 决定产品方向，并把重点 concern 交外置团队最终审核。疑似持续伤害仍优先 Incident |

一屏提醒只在新信息可能改变核心假设、scope、预设 trigger、material risk 或即将执行内容时主动出现；普通支持性证据和非 material 聚合进入阶段摘要，避免 alert fatigue。提醒默认展示：原决定及 exact version、当时关键依据、新信息与 provenance、究竟改变了什么、Agent 首选建议，以及 exact affected Plan/PRD（含 delivery intent）/Eval/Ready/Handoff。授权与 Evidence 继续分开：Owner 说“维持原决定”是有效决定，不会把冲突证据变成无效。

Owner 可以选择：维持原决定、补充 Evidence、设计受限 Experiment、创建新 Decision supersede 旧版，或缩小 action/scope。若在 material challenge 下维持，必须记录理由、accepted uncertainty/risk 和下一 recheck/stop condition。旧 Decision 永久 immutable；改判只能创建新 version/Decision 并显式 `supersedes`，不能回写历史依据让旧决定“看起来一直正确”。

Impact List 绑定 exact new Evidence、historical Decision 和 affected artifact hashes，只标真正受影响对象，最小状态语义为 `UNAFFECTED / REVIEW_REQUIRED / INVALIDATED / PAUSED / WAITING_DECISION`；不得因一个新 Signal 默认全量重跑，也不得把受影响的已派发 Handoff 隐藏在 Run 级总状态中。新 Evidence 若形成可复用项目事实，应保留为带 provenance 的未来 Knowledge source candidate；在 Knowledge Maintenance Graph 审核/发布前不能静默覆盖 canonical Snapshot。具体提交格式、证据冲突合并、跨团队 Impact delivery/ack 和批量提醒阈值保留到后续原型，不在本轮提前冻结。

对历史 STOP/WAIT 的重审另受 §10.2.3 约束：只有命中 restart/recheck condition、可信挑战 key assumption 或形成 material risk/opportunity 才主动提醒；维持原决定只追加 review result 与理由，改判则新建 immutable Decision Record 并 `supersedes` 旧版。Core 不周期性全量重审，也不让 future scheduler/Connector 自动改写 outcome。

---

## 11. Outcome-first Product Planning、二维拆解与 Coverage

**阅读卡——产品规划（双向深化原则 `CONFIRMED`；当前 Planning 活动/节点组及持久 Machine Name `PENDING NODE REVIEW`）**

- **做什么**：先定义本阶段最佳可达运行结果和 Product Plan v0 全局草案，再对高影响部分逐块深化、回到全局重构协调；边界基本稳定后，才正式横向拆能力模块、纵向拆渐进迭代，以 `plan.slice` 形成 PRD 候选并经 `plan.coverage.validate → plan.reconcile` 收敛。
- **为什么**：只追求小 PRD 容易得到互不衔接的碎片；只追求完整规划又容易形成一次性交付的大包。父 Product Plan 负责全局完整，子 PRD 负责边界内完整。
- **AI 做什么**：把 v0 当作可推翻的系统假设，优先深化高价值/高风险/高依赖部分，整合 bounded sub-agent Findings/Proposals；每轮回到系统最佳运行结果协调模块、顺序、依赖和 Unknown，再先提出 PRD 切片，诊断覆盖缺口并把处置同步回整体 Plan。
- **人做什么**：Owner 已在 Product Decision 选择目标方向；Planning 中只有出现超出该 Decision 的 material 目标、边界、取舍、风险或阶段变化时，才返回同一个 Product Decision 重新判断。语义 Reviewer 只给模块、迭代和切片建议。
- **主要产物与完成**：material 规划变化留下 versioned Product Plan checkpoint/changelog/supersedes/impact；内部 Refinement 稳定后，Module/Iteration/Dependency 视角、PRD Candidate Slice Map/List、Coverage dispositions 与 Reconciliation change 共同进入 exact Plan Candidate，再由独立 formal Review–Optimize 审查；Review 已收尾且轻量 Plan Ready 的机械合同满足后，只为当前 activated+eligible slices 创建 1..N 个独立 PRD Runs。一页摘要是按需 Human View，不是 Owner Confirmation。三个 `plan.*` 是 `product.planning` 内部动作，不新增顶层节点。

### 11.1 先定义最佳可达运行结果

只有当前版本 Product Decision 为 `EXPERIMENT`、`COMMIT + NOW`，或一个 `SCHEDULED / CONDITION_TRIGGERED` 承诺经过重新验证并产生合法 activation event，才能启动本阶段。仅有 committed Roadmap Item、日期已到或触发条件被非授权主体声称满足，都不能创建 Plan Run。Planning 不从功能清单或 PRD 字段开始，而是先把 §1.5 的共同系统结果和父级增量问题转成正式 Product Plan 内容；`EXPERIMENT` 复用同一流程但允许把长期方案和非关键未来分支保留为显式 Unknown，不能降低当前 action 的测量、停止、回滚与风险边界。

- **Target Operating Outcome**：当前约束下，用户、业务和系统应进入的最佳可达运行状态。
- **Observable Evidence**：证明该状态出现的行为、状态、数据和证据。
- **Non-sacrificable Guardrails**：不能为局部收益牺牲的用户、系统、上下游、安全、信任、成本和长期结果。
- **Current Iteration Outcome**：当前阶段整体最值得改变的系统状态，以及这一阶段如何推进目标结果。

规划的逻辑顺序是：

```text
Target Operating Outcome + Evidence + Guardrails
→ Initial Product Plan v0（系统假设 / 全局地图）
→ 优先级逐块深化 ↔ Global Reconciliation（可拆、并、删、重排或返回决策）
→ 稳定的完整 Planning Inventory
→ Module Map（横向能力模块）
→ Iteration Map（纵向渐进迭代）
→ Dependency / Shared Contract Map
→ PRD Matrix（模块 × 迭代视角，不机械按格切）
→ plan.slice（PRD 候选切片）
→ plan.coverage.validate（规划覆盖检查，只诊断）
→ plan.reconcile（规划协调，必要时返回上游）
→ stable Product Plan Candidate + Semantic Planning Review
→ plan.ready.gate
```

这描述必须完成的规划活动和产物，不预先决定每项活动是否成为独立持久节点；节点边界仍按 §7.2 和逐节点 Review 决定。

Product Plan 负责全局完整性：

- 目标与非目标，以及 Target Operating Outcome、Observable Evidence、Non-sacrificable Guardrails 和 Current Iteration Outcome。
- 用户、场景和完整用户旅程。
- 主流程、分支、异常和状态。
- 产品能力模块、模块责任、共享合同、权限、数据和约束。
- 纵向迭代、学习目标、独立价值、验收、反馈和停止条件。
- 依赖、风险、指标和阶段。
- 跨 PRD 的评估目标、基线、共享数据/Persona、安全护栏、实验条件和 kill criteria（需要时形成 Product-level Eval Strategy）。
- Current Iteration Outcome、各 PRD Increment Contribution、后续阶段、实验和拒绝项。

#### 11.1.1 双向深化与全局协调

> **CONFIRMED PLANNING PRINCIPLE**：Product Plan v0 是用于发现矛盾的**系统假设与全局地图**，不是直接切 PRD 的最终输入。规划不是一次“先写完整，再机械拆分”，而是双向运行：`整体草案 → 逐块深化 → 全局重构/协调 → 稳定后二维拆解 PRD`。

主 Agent 先按价值、风险和依赖选择需要优先深化的模块、流程或候选迭代；低影响、低依赖部分可以保留较轻表达，不要求全量同等深度。每个被选部分至少检查：

- 它对 Target Operating Outcome、Observable Evidence 与 Guardrails 的真实贡献。
- 产品责任、模块边界，以及是否应横向拆分、合并或删除。
- 用户流程、关键场景、分支、异常和状态是否能形成端到端结果。
- 依赖、共享合同、Owner、数据/权限边界和耦合风险。
- 关键 Assumption、Unknown、风险，以及当前更适合规划、Research 还是 Experiment。
- 纵向迭代是否能形成小而完整的学习/交付闭环，顺序是否应改变。

局部深化不是为 v0 找论据。新发现可以拆/并/删模块、改变顺序与范围、把事项转为 Research/Experiment、请求重新 Product Decision，或推翻初稿。每轮结束必须执行 **global reconciliation**：回到最佳可达运行结果，检查局部选择是否破坏其他模块、用户旅程、Guardrail、依赖、共享合同或后续阶段；主 Agent 统一整合并明确保留尚未解决的分歧，不能把多个局部 PASS 当成全局正确。

同一 exact Product Plan snapshot 可交给 bounded sub-agents 并行检查不同模块/流程/迭代；它们只返回 Findings/Proposals 和 exact refs，不并发写正式 Plan、current pointer 或 state。主 Agent join 后保留分歧并生成统一候选；涉及文件修改时复用 ADR-045 的独立 branch + worktree 和主 Agent diff review。多个 sub-agent 同意不自动提高 Evidence confidence。

material change 必须创建新的 Product Plan version/checkpoint，记录 change summary、reason、`supersedes`、受影响模块/迭代/依赖/候选 PRD 与 downstream Impact；旧版本不可覆盖。生命周期尽量复用 §20.5 的 immutable/version guard 和 §12.3 的 material checkpoint/archived 原则，但结构化 Product Plan 仍是唯一规划真源，不另存一份可漂移的“深化报告”。

可以进入正式二维拆解与 Plan Ready 的停止条件是：

- 高价值、高风险和高依赖部分已经达到与当前行动相称的深化程度。
- 主要模块边界、用户流程、依赖和共享合同基本稳定，无明显全局冲突。
- 重大分歧已解决，或已显式转为 Research、Experiment、Product Decision/route re-evaluation。
- remaining Unknown 不妨碍首批小迭代形成有价值、可验证、可停止的端到端闭环。
- 已足以形成一致的 Horizontal Module Map、Iterative Map、PRD Matrix 与 Dependency/Shared Contract Map。

已有稳定 Product Plan 的小改动只对 affected area 做 deep review，再运行一次 global impact check；不因存在深化原则而全量重跑。**Planning Refinement 已确认属于可恢复 `product.planning` 内部 Loop**，不再注册为独立持久 Graph Node；它以 Product Plan checkpoint 和 Candidate 保存恢复边界，不另建“深化报告”或第二真源。`plan.slice / plan.coverage.validate / plan.reconcile` 已确认是这个 Loop 内的稳定动作和恢复语义，不注册为三个新的顶层 Graph Nodes；Module/Iteration/PRD Matrix 的物理表达仍按真实消费者继续 Review，Plan Ready 基础合同见 §11.6。

#### 11.1.2 Planning Refinement 与正式 Review–Optimize

二者都可能产生 Finding，却承担不同责任，不能合并成生成者自审：

| 阶段 | 目的与执行者 | 输入/输出 | 权限与完成语义 |
|---|---|---|---|
| **Planning Refinement** | 主 Agent 生成、探索、拆解和 global reconciliation；bounded sub-agents 对选定部分给 Findings/Proposals | 从 exact v0/最近 checkpoint 产生 versioned checkpoints，稳定后冻结 Product Plan Candidate | sub-agent 不写正式 Plan/state；允许推翻结构。结束只表示形成 stable Candidate，不是 Review PASS/Plan Ready |
| **Formal Planning Review–Optimize** | 独立、只读 Reviewer sub-agents 对 exact frozen Candidate 按 `product-plan` profile 审查；Optimizer/主 Agent 按 repair path 修复 | Finding/Verdict 绑定 candidate version/hash；每次修复生成新的 Candidate 并保留 delta/supersedes | Reviewer 不编辑 Plan、不写 state；适用 attempt 已完成或如实标记不可用、Finding 均有 disposition 且 Review 已确定性收尾后，才交给既有 Plan Ready 流程 |

探索阶段可以按模块/流程调用 advisory partial review 帮助决定下一步 Refinement，但这些结果不能冒充 formal verdict。正式 Review 必须在 stable frozen Candidate 上运行；若 Candidate material change，旧 verdict 立即 stale。

Finding 按最早正确修复点路由：

```text
local expression / omission，且不改变结构
  → targeted optimizer → new Candidate → targeted re-review + global invariant check
module / dependency / iteration / system structural issue
  → 最近有效 Planning Refinement checkpoint → global reconciliation → new Candidate
invalid Product Decision
  → Product Decision
invalid Problem Definition / Evidence
  → Discovery
review finalized / Ready mechanical contract eligible
  → 既有 Plan Ready 流程
```

连续循环若只改措辞、重复同一根因或没有 material progress，必须返回正确上游 checkpoint/Decision/Discovery/Owner，不能靠继续 Optimizer 消耗轮次。该机制复用一套通用 Review–Optimize engine：`product-plan / prd` 使用不同 Reviewer 组合、rubric 和 repair policy；`EXPERIMENT` 只是相同 PRD profile 上的条件化检查，不增加独立 profile。它们共享冻结输入、Finding/Verdict、版本/delta、repair routing、定向复审、global invariant regression 和 no-progress 合同，不新增多套 runtime、业务 Node 或 Gate。

#### 11.1.3 Planning Profile Selector：按真实复杂度加重

**本节决策已确认。**业务 Router 回答“这个 Signal 接下来走 Incident、Bug、Discovery 还是 Inbox”；内部 `Planning Profile Selector` 只回答“已经进入 `product.planning` 后，需要多重的规划执行方式”。后者不新增顶层 Graph Node、业务路线或第二套状态机，只在现有 Plan Run State/Audit 中保存 `planning_profile`、选择依据、版本和变更事件。这里的 `LIGHT / STANDARD` 属于 `planning_profile` 命名空间，与 PM 访谈挑战强度或其他同名显示值无关。

| Machine profile | 面向人的直白说法 | 适用形态 | 内部运行方式 |
|---|---|---|---|
| `LIGHT` | **简单需求，一次轻量规划** | 单一或极少能力边界、依赖低、范围窄、通常一个迭代可闭环 | 在一次 bounded planning pass 中完成；Module/Iteration/Dependency 等逻辑可内联，不强制拆文档、Wave 或多 Round |
| `STANDARD` | **标准需求，分几轮把关键问题想清楚** | 有限模块/依赖/Unknown，需要多次深化但没有项目级阶段编排 | 使用少量有界 Planning Rounds；每轮只解决一个主要目标并留下 checkpoint，再 global reconcile |
| `PROJECT_SCALE` | **项目级规划，按阶段推进** | 多模块、多迭代、跨团队、跨会话或顺序/集成代价显著 | 条件启用 Waves 管父 Plan 的阶段主序列；只有当前 Wave 本身复杂时再在其中使用 Rounds |

Selector 由 Agent 根据当前 exact Decision、Product Plan v0、模块/迭代数量和耦合、依赖面、风险/Unknown、跨团队/跨会话需要及真实深化结果提出选择，再由现有 policy/Controller 记录合法 profile transition。它不要求 PM 填复杂度问卷，也不能在 Signal Intake 时永久决定；规划开始后如果发现依赖扩大、出现多个阶段或跨团队协调，可 `LIGHT → STANDARD → PROJECT_SCALE`，范围被验证为更小或复杂性被移除时也可降级。每次 material 升降级记录触发证据、对 checkpoint/Review/后续工作的影响和继续点，不能为了省步骤静默降级。

从 Better Work 吸收的只是以下执行原则：

- 小任务保持轻量，结构成本不能超过工作本身。
- 一个 Planning Round 只有一个主要目标，并明确 in/out scope、依赖、成功/停止条件、所需 Evidence 和恢复 checkpoint。
- Round 管当前边界内的“思考 → 规划动作 → 验证/调整”；完成一轮不表示整个 Plan Ready。
- Wave 管一个大型 Plan Run 的项目阶段顺序、依赖、carry-forward 与下一阶段选择；复杂 Wave 内可以有多个 Rounds，Round 不能改写父 Plan mandate。
- 新的大 Unknown、依赖或风险不能悄悄塞入当前 Round/Wave，必须进入现有 Unknown/Risk/Decision/Audit 合同并触发重划边界、升档或返回上游。

**不照搬 Better Work 的文件套件。**BPG 不新增 `TASK.md / MAP.md / WAVE.md / ROUND.md / DECISIONS.md / RISKS.md` 及其 JSON 状态副本，也不建设重复的 gate/state system。目标、Module/Dependency Map、阶段/Wave、Round checkpoint、Decision、Risk、Evidence、状态与审计分别复用现有 Product Plan、Planning Views、Decision Ledger、Risk/Reviewer Policy、Run State、Artifact Version 和 Audit Ledger；Wave/Round 只是 Plan 内部可恢复 section/checkpoint 和执行语义，不成为第二真源。

三个 profile 的重量不同，质量底线不变。`LIGHT` 仍必须能定位 Target Operating Outcome/当前增量、Observable Evidence、关键 Assumption/Unknown、范围与依赖、Acceptance/验证、风险/Guardrail、Owner/Decision refs 和审计链；它只是把步骤一次完成或内联、减少非必要 Reviewer/交互，不得跳过会导致错误交付的核心内容或正式 Review/Ready 约束。

PROJECT_SCALE 的“一次只推进一个当前 Wave”只约束**同一个父 Plan Run 的阶段主序列**，不是全项目并发锁。只要依赖、共享资源、受众/指标干扰和 Ready policy 允许，多个独立 Plan/PRD Run（包括带 `EXPERIMENT` intent 的 Run）可以并行；父 Plan 必须记录其关系、冲突面和 join/checkpoint，不能借 Wave 禁止合理并行，也不能借并行绕过父序列依赖。并行实验的跨 Run Portfolio 治理仍是 §10.5 的未来原型，不是一期开跑前置。

考虑过但拒绝的方案：所有需求固定跑全流程，会让简单需求被文档/Review 开销淹没；另建顶层 Planning Router，会把业务去向与执行深度混在一起并制造状态分叉；完整照搬 Better Work，会复制 BPG 已有 Product Plan、Decision/Risk/Audit/Run State。当前决定固定 Profile/动态选择和 Round/Wave 语义；ADR-060—063 另行确认内部切片、覆盖、协调与轻量 Ready，但仍不提前冻结各 profile 的精确轮数/阈值或 Module/Iteration Map 的独立节点形态。

### 11.2 本项目的二维拆解术语

为避免“纵向切片”在不同团队中的含义冲突，Better Product Graph 固定使用以下术语：

- **横向拆解 / Horizontal Decomposition**：按长期稳定的产品能力和责任边界进行模块化；目标是高内聚、低耦合。
- **纵向拆解 / Iterative Decomposition**：按时间、风险和学习目标把完整规划分成多个渐进迭代；目标是小步交付、快速获得真实反馈，而不是一次完成所有事情。
- **端到端闭环 / End-to-end Loop**：每个纵向迭代必须满足的结果要求；它不是第三种拆解方式。

横向模块应聚合同一产品责任所需的规则、状态和行为，具有清楚输入输出、Owner 和共享合同，模块内部可以持续演进而不频繁牵动其他模块。不得按前端、后端、数据库或测试等技术层分别拆成 PRD；这些层通常不能独立产生用户结果，且会把同一产品责任拆散。

纵向迭代必须产生真实、可观察的用户或业务价值，回答一个明确产品问题或降低一个关键不确定性，并具有独立验收、反馈、灰度/回滚和停止条件。即使后续迭代不再继续，当前迭代也应作为一个可理解、可运行的产品状态成立。

Product Plan 必须形成四个相互引用的**逻辑规划视图/合同**：

1. **Module Map**：横向能力模块、产品责任、Owner、输入输出与边界。
2. **Iteration Map**：纵向阶段、每期结果、学习目标、验证方式和停止条件。
3. **PRD Matrix**：模块 × 迭代的候选产品增量及其 PRD 归属。
4. **Dependency / Shared Contract Map**：跨模块依赖、共享规则、版本合同、交付顺序和禁止的循环依赖。

“四个视图”不等于每次 Run 必须生成四份独立重文档：

- 复杂、多模块、多迭代计划可以把视图独立产物化，分别版本化和引用。
- 快速 Product Decision 后的单一 change PRD、单模块单迭代或其他简单计划可以在轻量 Product Plan 中内嵌、合并表达，并由一个 `planning_views_ref` 统一定位；`IMPLEMENTATION_DEVIATION` 的 Bug Fix Brief 不进入 Product Planning，因此不要求这些规划视图。
- 无论物理表达如何，四类语义、引用一致性、验证规则和审计证据都不能丢失；`N/A` 必须有理由，不能用“轻量”隐藏依赖或共享规则。

一份 PRD 通常对应“一个主要模块 × 一个明确迭代 × 一个可独立验证的产品结果”，但不能机械要求矩阵一格一份 PRD：

- 一个端到端结果必须跨多个模块时，由父 Product Plan 定义共同 Current Iteration Outcome，并用多份模块 PRD 协调贡献关系；这本身不要求 Batch。
- 只有多个 PRD 客观上不能独立发布时，才组成交付 Batch；必须记录不能独立发布的理由、共同回滚/停止条件、耦合风险和解耦计划，同时保留各自模块边界、Owner、合同和验收。
- 若拆分制造重复规则、临时接口、循环依赖或高于收益的协调成本，应重新塑造边界，不能为了 PRD 数量强拆。
- 若一个碎片不能独立产生产品价值、降低关键不确定性或形成必要的端到端闭环，则它不能被包装成独立 PRD。

#### 11.2.1 `plan.slice`：PRD 切片

**中文名：PRD 切片。大白话：把完整思考过的整体产品规划，拆成可以分别交付、验证、上线和回滚的 PRD 候选集合。**它是 `product.planning` 内部稳定动作，不是继续做 Product Plan，也不是开始写 PRD 正文；它只决定“应该生成几份 PRD、每份负责什么”，其输出仍是候选边界。

`plan.slice` 同时读取 Module Map、Iteration Map、Dependency/Shared Contract Map 和矩阵视角，但不把任何单一视图当成切割线：

- **横向模块化**用于识别高内聚、低耦合的产品能力与责任；**纵向迭代化**用于识别逐步产生用户价值或有效学习的小迭代。
- 不机械采用“一模块一 PRD”“一迭代一 PRD”，更不把“模块 × 迭代”的每个格子变成一份 PRD。一个端到端用户结果可以跨越多个产品模块；反过来，一个大模块也可以在不同阶段形成多个有意义的 PRD。
- 不把前端、后端、接口、数据库或测试层分别包装成产品 PRD。技术任务可以在研发 Graph 中拆分，但 Product PRD 必须能够解释端到端产品结果。

每个候选切片默认检查以下判断标准；它们帮助比较方案，不是脱离情境的一票否决 checklist：

1. 有独立、清楚的目标或问题边界。
2. 能形成端到端用户/业务结果或有效学习，而不是技术半成品。
3. 能独立验证；行为非确定时说明对应 Evals 需要。
4. 能相对独立发布、灰度、停止或回滚。
5. 大小适合当前 Planning Profile、风险和团队交付能力。

“相对独立”不等于零依赖。数据、共享规则、平台能力或先后顺序可以存在，但必须被明确、可管理，且不能让候选在很长时间内只有成本、没有可验证结果。若多个切片客观上必须原子发布，才按既有 Batch 规则解释共同回滚、停止和解耦计划。

输出是 Product Plan 中 versioned 的 **PRD Candidate Slice Map/List**，每项至少包含：目标/问题、预期用户结果、所属规划阶段、涉及产品模块、依赖、验证方式、切分/合并理由及 source Plan/view refs。它不是最终 PRD 或 PRD Run；后续 `plan.coverage.validate` 检查候选之间及其与整体 Plan 的遗漏、重复、断层和依赖冲突。

交互遵循 Agent-first：Agent 必须先自行读取完整 Plan 和视图并提出推荐切片，不让 PM 手工填整张拆解图。只有某个合并/拆分选择会实质改变用户价值、上线策略、用户优先级、依赖等待，或“先实验”与“正式交付”的边界时，才向 PM 展示首选、影响和替代方案并请求判断。

例如“消息治理”同时涉及高风险消息识别、风险优先级与用户端展示。若三者共同构成“用户能识别并处置高风险消息”的一次端到端结果，可以跨模块形成一份候选 PRD；不得机械拆成“识别模型”“一个接口”“前端样式”三份无法独立验证用户价值的半成品。后续迭代仍可在同一能力上继续降低误判或扩大覆盖。

考虑过但拒绝的方案：按模块一刀切会忽略跨模块用户旅程；按迭代一刀切会把同一阶段的多个独立结果绑成大包；矩阵每格一 PRD 会放大协调成本和无价值碎片；直接开始写 PRD 会在边界尚未比较时固化方案；按技术层拆会把产品责任交给研发结构。当前仅确认 `plan.slice` 的内部动作、判断边界与候选合同，不新增顶层 Node、Gate、第二状态系统，也不把候选冒充正式 PRD。

### 11.3 `plan.coverage.validate`：规划覆盖检查

**中文名：规划覆盖检查。大白话：检查 PRD 候选切片是否把整体规划里的重要事情安排清楚，是否有遗漏、重复、冲突、体验断层或无法落地的依赖。**它是 `product.planning` 内部必经检查，而不是沉重的顶层 Gate；LIGHT 可与切片/协调内联执行，复杂 Plan 可把结果保存为 Product Plan checkpoint 的一部分以支持恢复。

核心原则是：**覆盖完整不等于本轮全部实现，而是每件重要事情都有明确去向。**未进入当前 PRD 不得静默消失；每个 Planning Item 使用稳定 ID，并有一个当前 disposition：

```text
PRD:<prd_id>
LATER_PHASE:<phase_id>
EXPERIMENT:<experiment_id>
WAITING_CONDITION:<condition_id>
OUT_OF_SCOPE:<reason_id>
REJECTED:<decision_id>
UNRESOLVED:<owner_or_question_id>
```

对应的人类语义是：本轮实现、后续迭代、先实验、等待明确条件、明确不在范围、已决定不做、尚未解决。`UNRESOLVED` 不是丢弃箱，必须附 Owner、影响、临时处理和复查/触发条件；disposition 改变需通过 `plan.reconcile` 形成新 Plan version，而非覆盖旧记录。

检查分五类：

1. **遗漏**：重要用户、场景、规则、异常、Guardrail 或 Planning Item 是否没有去向。
2. **重复/冲突**：多个候选是否重复负责、给出冲突规则或竞争同一共享状态。
3. **端到端体验完整性**：拆分后用户是否仍能完成闭环，阶段间是否出现不可理解的体验断层。
4. **依赖可落地性**：先后顺序、缺失前置、循环依赖、共享合同和 Owner 是否明确。
5. **上游一致性**：切片是否仍符合 exact Product Decision、Roadmap 承诺及待验证 Assumption，而没有把实验偷换成正式投入。

检查重量随 Planning Profile 自适应：`LIGHT` 由主 Agent在同一 bounded pass 内快速内联；`STANDARD` 形成简短的 item→disposition/依赖关系并检查遗漏；`PROJECT_SCALE` 可对 exact Plan Candidate 派独立只读 sub-agent 做覆盖挑战。任何档位都不要求每次召集完整 Reviewer 组。

`plan.coverage.validate` 只诊断和记录 Finding，不静默修改 Product Plan、切片或 Roadmap，也不因发现缺口自动输出 BLOCK。关键是每个 material Finding 有明确影响、建议去向、责任与后续 `plan.reconcile` 处置；检查结果优先内嵌在 Product Plan/版本 delta/Audit 中，不新造庞大独立 Coverage 文档或第二真源。例如发现“高风险消息 PRD 缺少误判处理”时，本动作只说明遗漏、影响用户和命中的候选；是否加入当前 PRD、放到后续迭代或先实验，由协调动作决定。

必要的结构化覆盖摘要可以输出：

```yaml
total_items: 42
judged_necessary: 36
dropped_as_unnecessary: 6
assigned_exactly_once: 42
orphan_items: 0
duplicate_assignments: 0
unresolved_items: 2
```

所有 `dropped_as_unnecessary` 项必须列出理由、判定人和 Evidence/Decision ref；Agent 不能通过缩小分母自证 100%。但数字不是 Gate 分数，`unresolved_items > 0` 也不自动 BLOCK；真正标准是去向、影响、责任和复查条件透明，且不会使当前候选建立在失效或自相矛盾的 Plan 上。

考虑过但拒绝的方案：强制本轮实现全部事项会把迭代重新变成大包；每次召集完整 Reviewer 会让简单需求失去轻量性；让 Validator 发现后直接修 Plan 会混淆诊断与决策权限；完全跳过则无法证明大规划到小 PRD 没有静默丢失。具体缺口如何协调由下一节处理，覆盖检查本身不扩张为审批。

### 11.4 `plan.reconcile`：规划协调

**中文名：规划协调。大白话：将覆盖检查、局部深化或新证据发现的问题重新放回整体规划权衡，使 Product Plan、模块、迭代、PRD 切片、依赖和 Roadmap 重新一致。**它解决的是“局部 PRD 各自看起来合理，组合后整体不合理”，不是逐条把 Coverage Finding 勾成已修复。

`plan.reconcile` 接受 `plan.coverage.validate` Findings、Planning Refinement 的局部发现和新 Evidence/Impact，重新对照 Target Operating Outcome、Guardrails、exact Product Decision 与 Roadmap。它区分两类处置权限：

- **不改变产品决策本质的协调**：补充遗漏场景、修正依赖顺序、消除重复、调整候选 PRD 边界、同步引用和版本关系，可由 Agent 自动整合为新的 Product Plan checkpoint，并记录 delta、理由和影响。
- **改变产品决策本质的协调**：若会改变目标用户、核心目标、做/不做、重要优先级/时间、风险承担、Roadmap 重要承诺，或 Experiment 与正式投入边界，Agent 不得静默修改。它必须用“发现 → 对原 Decision/承诺的影响 → 首选建议 → 不改的后果”呈现给当前 Owner；确认后再通过既有 Decision Ledger、Product Plan changelog、Product Changelog Proposal（适用时）和 Audit 落账。

协调不为保持向前流转而强行拼接。根据根因，它可以确定性建议返回：

```text
切片边界或候选责任错误      → plan.slice
迭代顺序/阶段结果错误       → plan.iteration.map
做不做/承诺/风险本质动摇    → product.decision
问题理解或关键 Evidence 动摇 → problem.learning.loop
```

这些是已有 Plan Run 内的 repair route 或既有上游 route，不注册四个新审批。回到上游后生成 exact new version/supersedes/Impact，再重新执行受影响的切片、覆盖与协调；不得把旧 Review/finalize 结果搬到新 material version。

允许灰度收敛：不要求所有 Unknown 和冲突在 Planning 阶段消失。暂不能解决但不使当前行动失真的冲突可以保留，前提是记录临时处理、影响、风险承担者、复查时间/条件，以及什么新 Evidence 会触发调整；material 冲突不得被隐藏为“以后再说”。按 Profile，`LIGHT` 可与覆盖检查在一次 pass 中完成，`STANDARD` 在每轮关键 Planning Refinement 后协调，`PROJECT_SCALE` 在 Wave 边界、重大切片变化或新 Evidence 出现时协调；复杂档可让只读 sub-agents 提供不同方案，但只有主 Agent整合，新的 material 产品取舍必须返回 `product.decision`，Controller/版本守卫再写正式记录。

例如 Coverage 发现“高风险消息 PRD 缺少误判处理”。协调需要回到端到端体验与风险：如果只是漏写已决定的人工申诉场景，可补进当前切片；如果处理能力依赖尚未建设，可明确放到后续迭代并限制首期流量；如果误判率本身未知且决定是否适合正式上线，则应先转 Experiment；如果由此动摇“全量自动处理”的既有承诺，则返回 Product Decision。不能只在 Coverage Report 写一句“已处理”。

考虑过但拒绝的方案：让 Coverage Validator 直接修复会让诊断者越权且无法解释为什么改；逐 Finding 局部打补丁会制造组合后矛盾；所有变化都要求 Owner 审批会让非语义同步过重；发现上游失效仍强行推进会把错误固化到 PRD。`plan.reconcile` 只更新既有 Product Plan version、PRD 候选关系、变更记录和必要 repair route，不创建独立大文档、第二状态系统或新的审批 Gate。具体自动/Owner materiality 阈值和 `plan.iteration.map` 内部合同继续以真实运行验证，不在本轮扩张。

### 11.5 Deterministic Validators 与 Semantic Planning Review

确定性 Validators 检查：

- current Product Plan Candidate 绑定 exact v0/前序 checkpoint、material change summary、`supersedes` 和 impact refs；不存在并发写入或从可变 `latest` 推断 source。
- 每个 Planning Item 恰好一个去向，`orphan_items = 0` 且 `duplicate_assignments = 0`。
- 每个 PRD 声明确切主模块、迭代、Target Outcome、验收结果和依赖。
- PRD、模块、迭代和共享合同引用存在且版本一致。
- PRD 与模块之间无循环依赖；每个已声明的 `shared_rule_id` 恰好引用一个权威定义。
- 父计划、Matrix、Slice、Batch 和子 Run 引用版本一致。

Semantic Planning Review 判断：

- 高价值、高风险、高依赖部分是否已经过与当前行动相称的深化；最近一轮是否真正回到 Target Operating Outcome 做 global reconciliation，而不是把多个局部意见直接拼接。
- Target Operating Outcome 是否是当前约束下的整体运行结果，而不是局部指标或预设方案。
- 模块是否具有清楚产品责任、内部高内聚、外部低耦合，而不是技术分层。
- 每个迭代是否形成端到端价值或学习闭环，并具有独立验证和停止条件。
- Candidate PRD 是否是一个有意义的产品增量，而不是无用户价值的小碎片或一次完成全部内容的大包。
- 局部收益是否损害 Non-sacrificable Guardrails 或其他模块、阶段与长期结果。

`plan.ready.gate` 只能按 §11.6 检查所需 Validator、formal Semantic Planning Review/finalize、Coverage/disposition、依赖冲突与 material Decision refs 是否齐全并绑定当前版本；它不替代语义判断，也不要求 Owner 再确认整份 Plan。正式 Semantic Planning Review 按 §11.1.2 由独立只读 Reviewer sub-agent/attempt 针对 exact frozen Planning Candidate 执行；探索期 advisory review、主 Agent 自审或绑定旧 Candidate 的结果都不能冒充当前审查已完成。本轮不新增独立 Review Graph Node；已确认的 `plan.slice / plan.coverage.validate / plan.reconcile` 仍是 Planning 内部动作而非三个新 Gate。

### 11.6 Plan Ready：什么时候可以安全创建当前 PRD

Plan Ready 的业务问题不是“规划是否已经完美”，而是：**整体规划是否已经稳定到可以安全创建当前要做的 PRD，而不会把尚未解决的整体矛盾复制到多个子 Run。**它不要求所有未来事项都成熟，也不把 Planning 变成第二套组织审批。

Human Renderer 可从同一 exact Product Plan Candidate 按需生成一页规划摘要：

1. 本阶段要达成的结果与 Guardrails。
2. 当前拟激活的 PRD 候选及各自用户结果。
3. 顺序、关键依赖和共同合同。
4. 后置、实验、等待、不做和尚未解决事项的去向。
5. 重要 Unknown/风险、Agent 首选建议及不推进/改判条件。

该摘要不是审批、acknowledgement 或 Ready 前提，Owner 无需逐字段打勾。固定 `plan.owner.confirm` 已取消，不保留未实现 alias/event。只要 Planning 忠实展开 exact Product Decision，Agent 可以自动完成模块/迭代拆分、普通依赖、切片、已确认规则的场景/异常/AC 补全，以及不改变产品承诺本质的协调。

只有 Planning 发现新的 material 产品取舍才打断 Owner：改变目标用户或目标结果；删除/推迟已承诺核心能力；改变重要优先级、时间或 Roadmap 承诺；接受明显新风险/体验损失；改变 `COMMIT / EXPERIMENT` 边界；或其他超出 exact Decision 授权范围的选择。此时不是“确认整份 Plan”，而是从 `plan.reconcile` 或 Planning Finding 返回 `product.decision`，展示“发现 → 受影响承诺 → Agent 首选 → 不改后果/最强反方/翻转条件”，由 Owner 形成 Decision amendment 或新 Decision version 后再回 Planning。普通忠实展开不得包装成新 Owner 选择。

程序化 Deterministic State Controller 随后执行 `plan.ready.gate`。它只重算以下确定性条件，不做语义产品判断，也不替代 Reviewer 或 Product Decision：

- 当前 exact Product Plan Candidate/version/hash 可解析、current 且 material-valid。
- `plan.coverage.validate` 已对当前 slice set 完成；重要 Planning Items 均有显式 disposition，未静默消失。
- Planning Profile 要求的 advisory formal Review 已完成、`review.finalize` 已记录 disposition，并绑定当前 exact Plan version；LIGHT 可以更轻，但不能拿旧 Review 或主 Agent 自审冒充完成。
- 无法形成有效子 Run 的机械依赖/引用冲突已由 `plan.reconcile` 处置；所有会改变产品方向、承诺、重要优先级/时间、风险承担或 delivery intent 的 material choice 都有 current exact Decision ref，且未 stale。普通 advisory concern/Unknown 可透明携带。

Gate 输出 `READY` 或带 exact unmet condition + deterministic repair target 的 `NOT_READY`，不评分、不发明第二次确认。按 Planning Profile 只调整 Refinement/Review/Coverage 的执行深度，三档共用同一基础 Ready 合同。

允许可控 Unknown 随当前切片进入 PRD：拟议动作小流量、可回滚、可观察，风险承担者知情，且不存在不可逆损失或不可豁免专业风险。若 Target Operating Outcome、目标受众、如何判断有效、关键依赖、停止/回滚边界仍不清楚到会使子 PRD 建立在错误 Plan 上，则不伪装 Ready，按 Finding 返回 Planning/Product Decision；Experiment 不能成为缺少测量和回滚时的逃生口。

`plan.ready.gate` 通过后，State Controller **只为当前已 activation 且 eligible 的 PRD Candidate Slices** 创建 PRD Runs，记录 exact parent Plan、`planning_views_ref`、slice version/hash、delivery intent、依赖和 carried Unknown/constraints。未来阶段继续留在 Roadmap/LATER disposition，等待条件项保持等待；`EXPERIMENT` slice 使用同一种 PRD Run 并继承实验条件，不创建 Experiment Run。不得为全部未来 Roadmap 预生成容易失效的 PRD。v0、单个局部深化结果、未完成 Coverage/Reconciliation 的候选，以及未获当前 activation 的 slice 都不能创建 PRD Run。

考虑过但拒绝的方案：要求“所有规划完全确定”会阻止可逆迭代；完全省略 Ready 会把全局矛盾复制到子 PRD；固定要求 Owner 阅读一页摘要并确认会重复 Product Decision 与外部审批，却不提供新的责任边界；为所有未来事项先写 PRD 会制造版本债务。待原型验证的重点是 LIGHT 是否仍能稳定发现机械冲突、material choice 是否可靠返回同一 Product Decision、Unknown 边界与 eligible activation 计算是否可重复；本节不扩写后续 PRD Run 内部逻辑。

---

## 12. PRD Run 与 Review–Optimize Loop

**阅读卡——PRD 内容、模板与审查优化**

- **做什么**：`prd.content.build / prd.render` 先组织一个确定增量的完整产品语义，再按项目模板写成同一份 PRD；随后先检查它是否忠实于 exact 上游，再由 `review.parallel / review.aggregate / prd.optimize` 反复审查、修复和定向复审。
- **为什么**：PRD 阶段的首要风险不是“写得不够漂亮”，而是把 future 偷带入本期、增加未经决定的规则、隐藏 Unknown 或遗漏护栏。当前操作者已是有权 Owner，且存在外置汇总审批，再固定增加理解确认和交付批准只会重复打断。
- **AI 做什么**：生成候选 PRD/Eval Pack；用独立只读 Reviewer 检查语义忠实性和专业质量；聚合 Finding、定位最早修复位置并生成新版本；复杂 Run 才按配置保存内部内容 checkpoint。
- **人做什么**：只在 material ambiguity/上游产品决定、不可替代的专业 Domain 授权，或 Connector policy 要求外部写权限时介入；不为每份 PRD 固定确认理解或重复批准内容。
- **主要产物与完成**：当前 PRD、必要 Eval Pack、Fidelity Findings 和 Review 结果绑定同一 exact 候选版本及上游 Decision/Plan/Slice/Knowledge refs；程序化 PRD Ready 通过后自动形成 self-contained BPG Released artifact set，直接作为本地交付单元。它不等于组织外置审批已通过、Connector 已发送、研发已接收或测试通过。

### 12.1 PRD Run 主流程

面向产品经理和实现者，起点应读成一个用户动作和一个后台动作：

```text
后台准备 PRD 工作空间（State Controller 自动；非智能节点）
→ 生成 PRD（可恢复 Agent 节点：prd.generate）
   └── prd.content.build：组织 exact stable content Candidate
       ├── template.resolve → prd.render：按模板组织/编写 PRD
       └── evals.applicability.decide → evals.build?：按需并行生成产品评测方案
   → join：同一 content version 的 PRD + 条件式 Eval Pack
```

一句话：**Agent 是作者和产品专家，程序是文档管理与流程登记员。**前者负责理解问题、方案设计、场景/流程/状态/异常、取舍、回应审查与优化；后者负责防止覆盖、引用错版本、丢失恢复点、未审自报完成和并发写冲突。

完整 PRD Run 业务流程从单一 `prd.generate` 节点开始：

```text
prd.generate（内部运行 evals.applicability.decide）
   ├── 普通验收标准足够（NOT_NEEDED）────▶ 记录理由；只完成 prd.render
   ├── 建议增加 Evals（RECOMMENDED）─────▶ 按配置/Owner选择可并行 evals.build；默认不硬阻塞
   └── 必须提供 Evals（REQUIRED）────────▶ 并行 evals.build
                                                ├── evals.scope
                                                ├── evals.generate
                                                └── evals.review
→ join exact PRD Candidate + 条件式 Eval Pack
→ 忠实一致性检查（现有 Review 的首要 rubric；非新增节点）
→ review.parallel
→ review.aggregate（审查意见汇总）
→ review.finalize（审查收尾；Controller 立即确定性执行）
→ prd.optimize（必要时循环）
→ 一页最终摘要 Human View（按需查看；非审批/非 Gate）
→ prd.ready.gate
→ release promotion（自包含 Released artifact set 即本地交付单元）
→ 可选 handoff.dispatch policy
   ├── disabled → 本地已完成，未请求发送
   ├── manual → READY_TO_DISPATCH；明确外部写入授权后发送
   └── auto_when_ready + exact preauthorization → handoff.dispatch
```

Applicability 不承担运行状态。Eval Pack 尚未开始、正在生成、已生成待审、已审查，或因数据/Ground Truth/专业 Owner 等输入缺失而受阻，都记录在独立 Fulfillment/Runtime Status 中；`REQUIRED + BLOCKED_MISSING_INPUT` 仍允许 `prd.generate` 保存 PRD Candidate 和继续补齐内容，只在 PRD Ready 时阻止虚假完成。

进入 `prd.generate` 前，State Controller 在后台执行“准备 PRD 工作空间”的确定性生命周期动作，内部 action/event ID 为 `prd.workspace.initialize`，不在 Graph Manifest 或人类 Overview 中与 `prd.generate` 并列为智能产品节点。该动作只允许：创建 Run/workspace，绑定 exact parent Plan/Slice/Decision/Knowledge refs，登记状态与版本，准备 `archived/`、`released/` 及恢复位置，以及执行必要的保存、流转与机械校验。它**绝不生成、判断、补写或修改** PRD 的语义内容。第一版没有已发布运行消费者，不实现旧名 alias。

`prd.generate` 是独立、可恢复的 Agent 节点，内部按需保存 attempt/checkpoint，但不把三个动作注册成三个用户可见 Graph 节点。`prd.content.build` 在不依赖具体排版顺序的情况下组织完整产品语义；确定性 `template.resolve` 解析 project Template Profile；`prd.render` 再由 Agent 按模板编写与组织 PRD。对简单需求，三个动作通常在**同一次 Agent attempt、同一用户动作**中连续完成，不增加一次确认或新的 HITL；内部能力可分开测试，不代表必须产生多个节点或多份正式文档。第一版直接使用这些正式 machine names，不实现 `spec.build` alias。

一期不默认持久化与 PRD 同等完整的独立 Product Spec。`prd.content.build` 的中间结构默认只是当前 attempt 的 runtime object；最终 frozen/released PRD 才是面向研发的人类交付合同。只有复杂跨会话写作、同一语义需输出多个模板、多个 Agent 分章节协作、模板发生重大迁移，或必须区分“产品语义错了”与“模板表达错了”时，项目才可按配置保存 versioned recoverable content checkpoint。该 checkpoint 必须绑定 exact parent refs 和 PRD candidate，不能进入 `released/`、不能单独 Handoff，也不能被发布为与 PRD 竞争的第二份正式需求。

这个决定是在读取 Better-Product-Plan 的实际材料后修正了原建议。默认模板已经包含需求范围、产品三问、模块/优先级/依赖、用户故事、触发、规则、分支、异常、Acceptance Criteria、NFR、安全/兼容、灰度/回滚、埋点、多语言、决策日志与待确认事项；其 `templates.md` 还定义了 Requirement Understanding Summary，以及 planning artifacts 到 PRD 背景、概览、模块详情、NFR、埋点、多语言和附录的映射。因此 `Product Plan → Requirement Understanding Summary → 完整 Product Spec → PRD` 默认会重复同一语义并扩大漂移面。这里保留的是“先组织语义、再按模板表达”的**能力分离**，不保留“默认双文档”的**产物分离**。

`template.resolve` 是 `prd.generate` 内的确定性步骤，不独立成为 LLM 节点。`prd.generate` 首次完成时把 versioned PRD Candidate 写入 `archived/`；之后沿用 Review–Optimize、Ready 与 release promotion，使通过的 exact 版本进入 `released/`。§12.4.4 的 `<PRD-ID>_<需求短名称>_v<版本>_<YYYY-MM-DD>` 目录/主文件同 stem 规则是已确认的人类定位合同；示例中的具体 ID、标题、日期和 v0.x/v1.x 递增方式不是唯一值。不可变、self-contained、exact refs/hashes 与 Candidate→release 生命周期同样是强约束。

本轮只确认上述职责纠正、正式 machine names 与产物边界；`prd.render` 的完整内部写作逻辑、初始化的完整字段、失败状态和重试策略仍随 PRD Run 实现设计讨论，不因命名自动冻结为新 Schema、Gate 或 HITL。

#### 12.1.1 PRD 忠实一致性：先证明没有偏离上游

历史设计曾在 Candidate 后安排 `prd.owner.confirm_understanding`，在 Handoff 前安排 `handoff.owner.approve`。这会让同一个有权操作者在 Problem、Decision、Plan、PRD 和外置汇总审批之间反复确认，却没有直接回答更关键的问题：**Agent 写出的 PRD 是否仍然是上游已经决定和规划的那个增量。**因此这两个未实现事件从一期当前流程删除，不注册 alias、兼容记录或迁移解析器，也不能反推成当前 Ready 仍需重复批准。

忠实一致性检查绑定同一冻结 PRD Candidate、条件式 Eval Pack，以及 exact Product Decision、Product Plan、PRD Slice、Knowledge/Evidence、共享合同和确认约束，重点寻找：

- scope creep，或把 `future / later / waiting` 内容偷带入本期实现。
- 新增未经 Product Decision/Plan/Slice 决定的产品规则、方案或承诺。
- 虚构用户事实、指标、OKR、埋点 ID、Ground Truth 或专业结论。
- 把 `ASSUMPTION / UNKNOWN / VERIFY` 改写成 `CONFIRMED`。
- 遗漏 Guardrail、依赖、Shared Contract、回滚/停止条件或 REQUIRED Eval 要求。
- 与历史 Decision、当前 Knowledge 或上游规则冲突。
- 无依据扩大用户、市场、平台、地域或场景范围。

Agent 可以做不改变语义的清晰化，也可以把已确认的规则展开为必要场景、分支、异常和可判定 AC；这些属于忠实展开。任何 material 新内容都必须从当前 Candidate 删除或显式标为 `PROPOSAL`，并按最早正确修复点返回 Product Plan/Slice、Product Decision 或 Problem Learning。**PRD 阶段的 Owner 不能用一次随手确认把未决规则变成正式决定。**

实现保持轻量：Validator 确定性检查 exact refs/hash、source validity、slice membership、Planning disposition、模板映射与遗漏的结构化约束；Product Reviewer 把 semantic fidelity/alignment 作为首要 rubric，优先由绑定同一 exact snapshot 的独立只读 sub-agent 执行。它只输出既有 Finding/Verdict/delta 并进入 Review/Audit，不新增顶层 Node、独立报告、固定人工确认或第二真源。Reviewer 发现 material deviation 时必须给出对应最早 repair path，Optimizer 只修允许在当前 PRD 修复的表达/遗漏，不能把越界内容合理化。

Review–Optimize 收敛后，Human View Renderer 可以从同一 exact Candidate/Review/Audit refs 生成一页最终摘要，默认只展示：最终交付是什么、相对上游/上一版本有哪些 material 变化、关键 Review 修复、残余风险/Unknown，以及下一去向。它不是审批记录、第二真源或“必须读完才能 Ready”的新 Gate；用户可在需要时查看，source 变化后按既有 stale 规则重渲染。

### 12.2 Product Evals 与未来 evals-generator

这里的 Product Evals 不是 `evals/product-graph` 中用于验证 Better Product Graph 自身的回归测试。它是某个 Product Plan 或 PRD 随交付一起定义的评估合同，用来回答：“产品实现以后，我们用什么证据判断它真的达到了目标？”

输出分两层：

```text
Product Plan
├── Product-level Eval Strategy（按需）
└── 1..N [PRD + PRD Eval Pack]
```

Product-level Eval Strategy 说明跨 PRD 的结果指标、基线、共享数据集或 Persona、安全护栏、实验/停止条件和组合评估。PRD Eval Pack 至少可以包含：

- 能力与结果判据。
- 确定性验收项。
- 定性或概率性 Rubric。
- happy path、边界、失败和对抗性案例。
- Ground truth、来源、版本、适用范围与不确定性。
- Owner、Gate、运行频率和回归等级。

`evals.applicability.decide` 是 `prd.generate` 内部的轻量语义判断/路由动作，不是顶层 Graph Node、PM 问卷或新 HITL。Agent 综合当前产品行为、父 Product Plan/当前 PRD 的 Eval Strategy 和 versioned Project Eval Policy；确定性 policy 可以提高最低要求，但普通 PM 不需要填写“评测复杂度表”。

必须分开记录两个维度。

**Applicability / 是否需要：**

| Machine enum | 面向人类的直白结论 | 判断原则 | 默认 Ready 影响 |
|---|---|---|---|
| `NOT_NEEDED` | 普通验收标准足够 | 确定性行为可由明确 AC/测试用例稳定判断 | 记录理由后可继续 |
| `RECOMMENDED` | 建议增加 Evals | Evals 会显著增强回归、质量比较或风险可见性，但当前政策不要求 | 默认不作为硬 Gate；Human View 说明建议和放弃影响 |
| `REQUIRED` | 必须提供 Evals | 行为本身或风险需要样本、Rubric、分布或专业 Ground Truth 才能判断 | Pack 未满足可继续形成 PRD Candidate，但不能 PRD Ready |

AI/Agent/RAG/生成式内容，搜索、推荐、排序、个性化，多种输出都可能合理、必须用 Rubric 判断、结果依赖数据分布，或需要样本验证安全、偏见、内容、合规风险时，通常为 `REQUIRED`。**复杂性本身不是触发器**：复杂但完全确定的审批、状态机或计算流程，若 AC/测试用例足以稳定判定，可以是 `NOT_NEEDED`；反过来，看似简单的一句生成内容也可能必须 Evals。无法判断时不能默认降级，只有缺失信息会改变适用性或允许动作时才按既有交互规则请求正确 Owner/来源。

**Fulfillment / Runtime Status：**

| Machine status | 人类含义 |
|---|---|
| `NOT_STARTED` | 尚未开始生成 |
| `GENERATING` | 正在形成 Eval Pack |
| `GENERATED_PENDING_REVIEW` | 已生成，等待适用 Reviewer |
| `REVIEWED` | 当前 exact Pack 已完成所需审查 |
| `BLOCKED_MISSING_INPUT` | 因数据、Ground Truth、专业 Owner、政策或其他必要输入缺失而受阻 |

缺输入不是“不需要”，也不是第四种 Applicability。第一版直接使用 `NOT_NEEDED / RECOMMENDED / REQUIRED` 与独立 fulfillment status；缺输入进入 `BLOCKED_MISSING_INPUT`，不实现未发布旧值的 alias 或迁移解析器。`RECOMMENDED` 默认不硬阻塞；只有 versioned policy/有权 Owner 将当前 action 提升为必须时才转 `REQUIRED`。

最小状态示例（不是完整 `evals.generate` Schema）：

```yaml
evals:
  applicability:
    code: REQUIRED
    display: "必须提供 Evals"
    reason: "推荐结果存在多个合理输出，需样本与 Rubric 判断"
    source_refs: ["prd:...#hash", "eval-policy:...#hash"]
  fulfillment:
    status: BLOCKED_MISSING_INPUT
    missing_inputs: ["domain_ground_truth"]
    owner: "domain-owner-ref"
    ready_effect: "PRD candidate may continue; PRD Ready is not allowed"
```

考虑过但拒绝：继续使用三值混合枚举会把“缺输入”和“不适用”混淆；让所有复杂需求自动 REQUIRED 会把确定性流程做重；让 PM 填问卷会把专业判断和可检索信息推给人；`REQUIRED` 一出现就禁止继续写 PRD，又会让缺口无法在具体候选中被定位。最终边界是允许 Candidate 继续成熟，同时禁止在必须 Eval Pack 未满足时自称 Ready 或把缺口隐藏到测试 Graph。

#### 12.2.1 `evals.build`：按需生成产品评测方案

`evals.build` 是 PRD Run 内部按需、可恢复的子节点，不是第五条业务路线，也不是独立 Run Profile。选择子节点而非一次 Prompt 的理由是：它有独立的缺输入/等待、专业 Review、版本恢复和 stale 边界，并能与 PRD 模板写作并行；但它没有脱离当前 PRD 的独立产品目标，所以不升级为顶层 Graph Node/Route。

当 `prd.content.build` 形成 exact stable content Candidate 后，PRD Run 冻结该 source version/hash，然后允许 `template.resolve → prd.render` 与条件触发的 `evals.build` 并行读取同一版本。`evals.build` 内部依次编排 `evals.scope / evals.generate / evals.review`，但三者不显示为三个用户节点，也不增加三次 HITL。两支 join 时必须证明 PRD 与 Eval Pack 都绑定同一 source content version；产品语义变化按 Impact 使相关 case/rubric/traceability stale，纯措辞、排版或不影响判断的模板变化不触发 Eval Pack 全量重做。

最小 Eval Pack 语义应足以让未来执行者知道“验证什么、怎样判断、边界在哪里”，至少覆盖：

- 被评估的能力与预期产品结果，以及普通 AC 为什么不足。
- normal、boundary、failure、adversarial cases。
- 每个 case 的 input/context、expected judgment 与适用 Rubric。
- success/fail/continue/stop 判据。
- Ground Truth 的 provenance、version、scope、confidence 与限制。
- dataset/persona/language/scenario coverage。
- 到 exact PRD rule/AC 的 traceability。
- unresolved verification gaps、影响和正确 Owner/来源。

本轮不把上述语义展开成庞大冻结 Schema，也不以 case 数量作为质量指标。停止条件是与当前风险相称地覆盖核心结果、主路径、关键边界和会改变发布判断的风险；更多低价值 case 不构成继续生成的理由。

Agent 可以生成 candidate cases、Rubric 草案和 synthetic samples，但不能自造 Ground Truth：正式规则/合同可作为有版本的基准；历史数据或人工标注必须带来源、版本、样本边界与代表性；专业、安全、隐私、合规判断必须由相应 Reviewer/Owner 确认；self-generated synthetic data 必须显式标 `CANDIDATE / SYNTHETIC`，多 Agent 重复生成也不会自动提高可信度。Review 按风险由 Product、Testability、Domain、Safety、Privacy、Compliance 等只读 sub-agents 并行；它们只给 Finding/Verdict，生成 Agent/Optimizer 才能修改并产出新版本。

内部 `evals.review` 只负责 Eval Pack 自身的判据、Ground Truth 与覆盖质量；两支 join 后，后续 formal PRD Review 仍检查“PRD 说要做的”和“Eval Pack 说要判断的”是否一致。两者使用不同 profile/rubric，不重复伪造两次同一审查，也不能用 pack-level PASS 代替 joint Candidate 的 Ready-eligible Review。

未来的 `evals-generator` 是我们后续要建设的 Better Product Graph **内部原子能力实现**，不是现有产品、顶层 Graph Node 或 Connector；一期可以由主 Agent 冻结 exact PRD/content snapshot、派发 bounded sub-agent 生成候选并聚合结果，再由现有 Review/权限边界处置。下列只保留候选输入输出边界，不在本轮提前冻结完整生成逻辑：

```yaml
inputs:
  - prd_candidate
  - prd_content_checkpoint_optional
  - product_eval_strategy_optional
  - risk_profile
  - acceptance_rules
  - knowledge_snapshot_ref
  - eval_policy
outputs:
  - eval_plan
  - eval_cases
  - eval_rubrics
  - ground_truth_and_provenance
  - unresolved_verification_markers
```

如果未来由 Claude 或其他外部 Agent 执行生成，外部调用可以通过 Connector，但 Core 中的 `evals.generate` 内部能力合同和 Ready 语义不改变。V1.4 只冻结合同和挂载位置，不声称 `evals-generator` 已存在；在它完成前，项目可以用人工/通用 Agent 按同一合同产出候选 Eval Pack。`REQUIRED` 且 fulfillment 未到 `REVIEWED` 时可以继续改 PRD/Eval 内容，但 PRD Ready 必须失败并返回 exact 缺口。

AI 生成的 Eval Cases 和 Ground truth 都只是候选产物。Junior PM 不能单独批准专业领域 Ground truth；Product、Domain、Testability、Security、Privacy 或 Compliance Reviewer 按风险参与。所有 `[VERIFY]` 和未知 Ground truth 必须在 Ready 前解决。

Better Product Graph 负责定义评估目标、输入、判据和证据要求；未来测试 Graph 负责 Eval runner、真实执行、结果、缺陷和最终测试 verdict。未接入测试 Graph 时，Better Product Graph 仍能本地生成并交付 Eval Pack，但不得声称已经通过测试。

#### 12.2.2 TDD-ready 长期扩展边界

长期方向是让当前能力扩展为更广义的 **TDD-ready Test Design Contract**：除了模型/概率性 Evals，还可从产品侧输出功能测试意图、场景、AC 映射、状态/分支/异常/边界与回归建议，供未来 Test Graph 和研发测试协作参考。这里的 “TDD-ready” 只表示产品行为与判断依据足够结构化、可追溯、可被下游转成工程测试，不表示 Better Product Graph 自己完成严格工程 TDD。

正式测试用例、单元/集成/E2E 测试代码、测试环境与数据准备、runner 执行、缺陷判定和最终 test verdict 仍属于未来 Test Graph/研发测试协作。当前一期名称继续使用 `evals-generator / evals.build`；扩展后的 umbrella name 保持 `OPEN`，不能仅因愿景扩大就现在无依据重命名或声称 Roadmap 已完成。独立 Roadmap Draft 完成并经人工 Review 前，本节只记录扩展目标、责任边界和 future seam。

### 12.3 默认 Reviewer 与项目扩展

> **PHASE-ONE ADVISORY CONTRACT**：所有 Product、UX、Engineering Feasibility、Testability、Security、Privacy、Compliance、Domain、AI Behavior Reviewer 都是内部建议者。它们只读同一 frozen Candidate，指出 concern、依据、影响和建议；不拥有 formal BLOCK、veto、approval、waiver authority，也不冒充真实专业责任人。当前每份需求仍由外置团队最终审核，BPG 内审的任务是提高质量并让外置团队快速聚焦。

通用逻辑覆盖基线：

- Product Reviewer 的产品目标与范围忠实度 profile：每次 PRD formal review 都必须逻辑存在。
- Engineering Feasibility Reviewer：正常交付 PRD 默认存在；LIGHT 且低风险、确定性、边界清楚时可与其他角色合并执行。
- Testability Reviewer：正常交付 PRD 默认存在；同样允许在 LIGHT 合并，但可测试性判断和角色归属不能消失。

当 Eval Pack 为 `REQUIRED` 时，Testability Reviewer 同时检查其可执行性；Graph 再按领域和 §10.1 风险等级增加 UX、Domain、AI Behavior、Security、Privacy 或 Compliance Reviewer。R0/R1 优先保持轻量，R2/R3 增加相应 concern coverage 和披露深度，但不因此产生 BPG 内部审批或否决。角色选择决定逻辑覆盖和执行 attempt，不要求一个角色名永远对应一个 sub-agent。Reviewer 始终审同一个 frozen“PRD + 条件式 Eval Pack”候选；当 intent 为 `EXPERIMENT` 时，实验 section 与 measurement/stop/rollback 也在这份候选中，不能拆成失配的另一套合同。

项目根据风险配置：

- UX Reviewer。
- Security Reviewer。
- Privacy Reviewer。
- Compliance Reviewer。
- External Audit Reviewer。

Reviewer 属于 Better Product Graph 的 PRD 专业审核能力，不是研发 Graph 或测试 Graph。

#### 12.3.1 Product Goal-Based Audit 的内核吸收：产品目标与范围忠实度

**背景与取舍。** Product Goal-Based Audit 的强项，是先从目标与承诺建立审查基准，再让独立专业角色以证据审查、保留分歧、复核高影响结论，并在修复后检查回归。这正好解决 PRD Reviewer 容易按个人偏好“建议更多功能”、或让 Agent 在写作中自由扩张的问题。但该 Skill 的完整七阶段流程还包括重新确认承诺、生成审计脚本、覆盖率与评分、审计自审、诊断和处方，以及 `.product-audit/` 文件套件；这些适合项目架构、版本发布、Roadmap 里程碑或专项审计，不适合作为每份 PRD 的内置必经流程。

因此 `review.parallel` 只吸收**目标忠实审计内核**，并把它实现为既有 Product Reviewer 的必需 rubric/profile，而不是增加一名永远独立运行的 Reviewer、一个 Graph Node 或第二套 Audit–Optimize Runtime。它与 §12.1.1 Fidelity/Alignment 是同一职责：前者给出可施工的并行审查合同，后者说明 PRD 阶段为什么先证明忠实。

**同源目标承诺基准。** 每次 formal review 由 Orchestrator 从同一冻结快照自动构造 `Goal Fidelity Review Packet`（执行输入包，不是新业务 Artifact）：

- exact Product Decision 与 chosen outcome/scope/Guardrails。
- exact Product Plan、Target Operating Outcome、Current Iteration Outcome 与 activated scope。
- 当前 PRD Slice、用户结果、Module/Iteration/Dependency/Shared Contract 与 disposition。
- exact Evidence/Knowledge refs、Assumption/Unknown 和适用 System Acceptance Baseline。
- 当前 frozen PRD Candidate、条件式 Eval Pack、Template/Profile/Policy versions 与 content hashes。

上述目标已经在 Problem/Decision/Plan 阶段由有权 Owner 决定，Reviewer 不再要求 Owner 逐项确认“这是不是目标”。任何 source 只提供 `current/latest`、hash 不一致或无法解析时，当前 Review 不能伪装成可信目标基准，应返回 exact ref repair；这仍不是新增 Owner HITL。

**Reviewer panel 自适应。** 每次 PRD formal review 必须逻辑上包含“产品目标与范围忠实度 Reviewer”，但默认把它作为 Product Reviewer 的首要 profile，不为一个名称无理由增加强制 sub-agent 数量。正常交付 PRD 默认还检查 Engineering Feasibility 与 Testability；LIGHT 且低风险、确定性、边界清楚时，Host 可以让一个隔离的只读 sub-agent 合并这些逻辑角色并分别输出 role/profile 字段。UX、Security、Privacy、Compliance、Domain、AI Behavior 等只在 Candidate、风险政策、数据/权限、产品行为或 Eval applicability 命中时增加。角色合并和减少 fan-out 不能省略目标忠实检查，也不能让生成 Candidate 的主上下文自报 Review complete、Ready 或正式状态。

目标忠实 profile 至少判断：是否实现上游目标而不是替换目标；是否遗漏关键用户/场景/Guardrail/共享合同；是否偷改 Product Decision 或扩大当前 Slice；是否把 Assumption/Unknown/偏好写成事实；是否添加无上游依据的功能；以及 AC/Eval/Observable Evidence 是否真的能证明当前目标。无上游依据的“建议增加某功能”只能记录为 future suggestion/open lead，并标明它需要哪个上游决策；不能自动进入当前 Candidate、Finding repair 或 Optimizer patch。

**独立首轮与 join。** 所有 reviewer/sub-agent 接收完全相同的 frozen Candidate、Goal Fidelity Review Packet、Evidence/Knowledge snapshot 和 output contract。首轮结果提交前不得互看其他角色的结论；Reviewer 只读，不能编辑 Candidate、state、current pointer 或 released Artifact。Host 不支持物理并行时可以隔离上下文顺序执行，但必须分别保存首轮结果，主 Agent 只能在所有 required 首轮结果返回或按 policy 明确失败后开始 aggregate。这样得到的是审查独立性，不是“多 Agent 同意就提升 Evidence confidence”。

**Finding 最小施工合同。** 在复用 §12.5 Finding/Verdict/Disposition 的前提下，PRD goal-fidelity profile 至少填充以下真正影响修复和路由的字段；不为字段完整制造空值：

```yaml
finding_id: PRD-FID-001
reviewer_role: product
reviewer_profile: product_goal_scope_fidelity
concern: "当前 PRD 把后续全量自动发送偷带入本期小流量实验"
concern_level: KEY_ATTENTION
basis_refs: ["prd-candidate@v0.3#...", "decision@v2#...", "plan@v4#..."]
upstream_commitment_refs: ["slice:S-03@v2#...", "guardrail:G-07@v1#..."]
affected_scope: ["automatic-send", "public-launch"]
possible_impact: "会把已决定的小流量验证扩大为未经决定的全量产品行为"
professional_recommendation: "删除全量发送范围；若确需扩大，先返回 Product Decision"
confidence: high
confidence_basis: "PRD Candidate 直接写明全量自动发送，而同一当前 Decision/Plan 只授权小流量；三个 exact refs 当前、直接且无冲突"
cross_check_status: conflicted
repair_target: product.decision # 也可为 current_prd / plan.slice / product.planning / problem.learning.loop / external_review
disposition: RETURN_UPSTREAM_PROPOSED
```

关注等级只用于阅读排序和外置团队聚焦，推荐机器层使用稳定三档并由 Human View 显示直白中文，例如 `KEY_ATTENTION / GENERAL_ATTENTION / OPTIONAL_IMPROVEMENT` 对应“重点关注 / 一般关注 / 可选优化”；最终 label 可在实现时冻结，但不得只显示裸 code。它不赋予 Reviewer 状态权、不能自动阻止 Ready/Released，也不能被多数低关注项抵消或稀释。第一版直接使用 `concern_level`，不实现未发布 `severity` 的兼容输入。

`confidence` 必须由 `confidence_basis` 对 evidence directness、freshness 和 conflict 给出简短可审计解释；该字段只记录支撑等级的关键依据，不是重复 Finding 的长推理。Validator 必须拒绝没有可解析 `confidence_basis` 的非空 `confidence`，也不得依据模型自信、Reviewer 数量或多数一致提高置信度。最小人类输出必须能一眼看懂：具体 concern、关注等级、exact 依据、可能影响、专业建议/建议返工点和当前 disposition。

**分歧与交叉验证。** Aggregate 可以在机器层使用以下既有 Skill 语义，但 Human View 必须显示直白中文：

| Internal status | 人类视图 | 处置 |
|---|---|---|
| `confirmed` | 多个角色独立发现同一问题或有更强证据支持 | 合并 Finding，保留每个角色和全部 evidence refs |
| `complemented` | 另一角色补充了影响范围、原因或条件 | 关联 Findings，更新 affected scope，不抹平差异 |
| `conflicted` | 对是否存在、关注程度、范围或解释有实质分歧 | 进入 disagreement ledger，保留各自依据并交 Agent/外置团队判断 |
| `unique` | 只有一个角色发现，但直接证据充分 | 保留角色归属；高影响项触发有界复核 |
| `unsupported` | 当前没有足够证据支持或无法复现 | 不作为 Ready 依据或自动修复；降为 open evidence gap/lead |

分歧不按多数投票。直接、可复现、当前、面向用户承诺和关键路径的 evidence 优先；仍无法裁决时保留冲突、说明可能影响和 Agent 首选建议，供外置团队审核。Aggregate 不能把所有合法建议都塞进 PRD，也不能以“多数未发现问题”抹去一项 material Goal/Scope concern。

**有界 review-of-review。** 仅在下列情况复核审查本身：重点 concern 可能改变产品方向或范围；required roles 对关键项冲突；“未发现问题”的结论只依赖弱、陈旧、间接或单一来源；高影响判断只由一个 Reviewer 提出。复核只检查高影响 Finding、证据和适用范围，不重跑完整 panel。默认一轮；只有首轮结果可能 materially 改变 concern level、affected scope、修复建议或外置团队所需关注时允许第二轮；最多两轮。它只提高建议质量，不把共识升级为 Evidence 或批准，也不注册新顶层节点或 `.product-audit` 重型报告套件。

**行动结果与修复验证。** Human View 不显示百分比分、A—F 或加权总分，而是从 Finding disposition 与 repair target 渲染直白建议：**建议按当前版本继续，并披露关注事项**；**建议修改当前 PRD**；**建议退回正确上游**；**证据或专业判断不足，保留给外置团队判断**。这些都是 advisory，不是四个 Gate 枚举；Agent 可以采纳当前 PRD 范围内的清晰建议并触发 Optimize，也可以保留争议/未采纳项及理由后继续完成内部审查。Reviewer 不能因为自己的建议未被采纳而无限占住 Run。

Optimizer 每次生成新 Candidate 后，优先只复审 material delta 和未解决 Findings，同时回归全局目标、范围、Guardrail、Shared Contract、AC/Eval 等关键不变量。每个上一轮 Finding 记录：`FIXED`（已解决）、`IMPROVED_BUT_OPEN`（有改善但仍未关闭）、`PERSISTENT`（仍存在）、`REGRESSED`（修复引入或加重问题）、`INSUFFICIENT_EVIDENCE`（证据仍不足）；Human View 分别显示“已解决 / 有改善但未关闭 / 仍存在 / 出现回归 / 证据不足”。连续两轮只改措辞、没有 material progress 或同一根因反复出现时，停止机械重写，显示卡点；Agent 可建议返回 Plan/Slice/Decision/Learning，或把未解决 concern 与理由保留给外置团队。不得无限优化，也不得因 Reviewer 不满意而重启轮次预算。

**明确不吸收。** 每份 PRD 不运行完整七阶段 Product Goal-Based Audit；不重新要求人类确认上游承诺；不采用 95%/80% 覆盖率目标、百分比分、加权分或 A—F；不创建每 PRD `.product-audit/` 文件套件；不默认生成 Shell 审计脚本；不要求每条 Finding 双审、每轮人工确认或无限优化。完整 Skill 继续用于 §20.7 的架构/版本/里程碑级审计，其结果仍需 Disposition，不能自动成为 PRD 修改指令。

### 12.4 Review–Optimize Loop

Review–Optimize 是一套可复用 engine/profile 机制，不是 PRD、Product Plan、Experiment 各自复制的一套 Runtime。不同 profile 可以使用不同 Reviewer 与 rubric，但一期全部 Reviewer 都是 advisory。流程仍必须冻结 exact Candidate；独立只读 Reviewer 只交 Finding/建议；Optimizer/主 Agent 才生成新版本；后续定向复审同时回归全局不变量；no-progress 停止机械重写。Product Plan 的 Refinement/正式 Review 边界见 §11.1.2；PRD 与 Experiment 进入本节流程时也不能让生成它们的同一上下文自报审查完成。

```text
冻结 Review Candidate vN（PRD + 条件式 Eval Pack；实验 intent 仍是同一候选）
          │
          ▼
PRD profile：先运行忠实一致性检查；其他 profile 使用各自首要 rubric
          │
          ▼
并行或逻辑并行 Reviewer
          │
          ▼
review.aggregate（汇总/保留分歧/建议 repair target）
          │
          ▼
review.finalize（审查 attempt/disposition/同源内审意见收尾；Controller 内部 action）
   ├──不再采纳修订/达到停止边界────▶ 一页最终摘要（按需）→ prd.ready.gate
   └──Agent 已采纳修复建议─────────▶ 定位最早修复位置
                         │
                         ▼
                  Optimizer 生成 vN+1
                         │
                         ▼
                   影响范围计算
                         │
                         ▼
                   定向复审 ──▶ aggregate
```

宿主不支持物理并行时可以顺序执行，但所有 Reviewer 必须绑定同一个 `artifact_id + version + hash + knowledge_snapshot`。晚到结果绑定旧版本时标为 `STALE`。

#### 12.4.1 `review.aggregate / 审查意见汇总`

**为什么保留独立 join point。** `review.parallel` 可能产生并行、逻辑并行、晚到、失败、`STALE` 或外部审计结果，高影响 Finding 还可能触发§12.3.1 的 bounded review-of-review。若不保留一个可恢复的汇总边界，主 Agent 在中断后就难以证明已收到哪些结果、哪些无效、哪些尚未返回。因此保留 `review.aggregate`作为轻量内部节点/聚合 join point；中文名为“审查意见汇总”。LIGHT 可在同一用户动作中自动完成，但仍保存可恢复的 aggregate attempt/record。这是机器内部恢复边界，不是 PM 交互步骤。

**严格职责链。**

```text
review.parallel   独立发现 Finding/Verdict
      ↓
review.aggregate  聚类、保留分歧、建议最早 repair target
      ↓
review.finalize   检查审查完整性、disposition 和 companion view 版本
      ↓
prd.optimize / 正确上游   生成新 Candidate 或上游新版本
```

Aggregate 只提交合法汇总结果；不修改 PRD/Eval Pack，不生成新 Candidate，不写 current state snapshot/current pointer，不执行 Gate/授权，也不得宣布 `READY`。`review.finalize` 如何检查完整性并进入唯一 `prd.ready.gate`，见§12.4.2；两者不得合并成“Agent 汇总并自行批准”。

**语义聚合与确定性校验分工。**

- 主 Agent 负责语义聚类、同根因关联、`confirmed / complemented / conflicted / unique / unsupported` 判断、unsupported future lead 隔离，以及最早 `repair_target` 建议。它不能为了显得完整而把不同问题强行合并，也不能把无上游承诺的建议放入当前修复清单。
- Deterministic State Controller 只检查 required reviewer attempts 已齐全或按 policy 明确失败，所有有效结果绑定同一 frozen Candidate/Goal Fidelity Review Packet，Finding 最小字段可解析，late/stale 已标识，原 Reviewer Finding 均在聚合结果中有可追溯处置，然后原子写入 attempt/state/audit。程序不判断哪个专业观点更正确。
- required 首轮结果未齐时，可以保存“等待/部分到达”恢复点，但主 Agent 不得完成语义 aggregate；绑定旧 Candidate 的晚到结果保留为 `STALE`，不混入新版本。

**恢复与输出。** Aggregate 结果是现有 Review Record 中的 versioned aggregate attempt/section，引用现有 Finding、Verdict、Disposition、disagreement ledger 与 Audit Event；`review_summary` 只是它的按需 Human View，不是新业务 Artifact 或第二真源。最小可恢复记录需绑定：

- `aggregate_attempt_id/version/status` 与上一 attempt/ref。
- exact `candidate_ref + hash` 与 `goal_fidelity_packet_ref + hash`。
- required/optional reviewer attempt refs，以及 completed/failed/late/stale 分类。
- 每个原 Finding 到 finding cluster、disagreement、unsupported lead 或其他 disposition 的无损引用。
- 按 Finding/cluster 绑定的 concern level、建议 `repair_target`、当前 disposition，以及是否需 bounded review-of-review。

Audit 按实际发生追加 `REVIEW_AGGREGATE_STARTED / REVIEW_AGGREGATE_PARTIAL_SAVED / REVIEW_RESULT_MARKED_STALE / REVIEW_AGGREGATE_COMPLETED / REVIEW_AGGREGATE_REJECTED` 或等价事件，并绑定 aggregate attempt、exact inputs、reviewer attempt refs、结果 hash 与规则版本；事件只证明汇总生命周期，不替代 `review.finalize` 结果或 Ready。

Human View 按需只显示：总体建议、重点关注、存在的分歧、建议返回的上游、不属当前范围的建议，以及下一修复位置。机器 Record 仍保留完整 exact refs；摘要不能通过省略消灭 Finding 或分歧。Aggregate 默认不打断 PM；真正需要上游产品判断时由既有 Product Decision/Planning 节点处理，未解决专业 concern 则进入同源内审意见供外置团队审核，不在 Aggregate 增加 HITL。

失败包括：静默丢失 Finding；把不同问题错误合并；把所有建议塞入 PRD；用 Reviewer 数量/多数票裁决分歧或提高 Evidence confidence；把 unsupported lead 变成当前修复；在 required 首轮未齐且未明确记录不可用时完成 aggregate；读取不同/可变 Candidate；修改 Candidate/state（除向 Controller 提交合法结果）；或声称批准/Ready。高影响 `unique / conflicted / weak-no-concern` 继续按§12.3.1 触发有界 review-of-review，不在 Aggregate 内用多数投票快速“消除分歧”。

#### 12.4.2 `review.finalize / 审查收尾`

**形态与取舍。** 当前期退役 `review.gate`：Reviewer 全部 advisory 后继续保留 Gate 名会误导其拥有批准或阻塞权；但把 Aggregate 直接折叠进 Ready 又会丢失审查 attempt、Finding disposition 和 companion view 的完整性。因此使用 `review.finalize / 审查收尾`，由 Deterministic State Controller 在合法 Aggregate 后立即执行。它是轻量内部 transition/action，不是业务 Graph Node、Gate、Agent、Artifact 或 HITL，也不重做语义审查。

Finalize 只做四项确定性检查：

1. 本轮配置为适用/required 的 Review attempts 已完成；确实不可用的 attempt 已明确记录 `NOT_AVAILABLE`、原因和影响，而不是伪装成完成。
2. 每条 Finding 都有无损 disposition：`accepted + fixed`、`not accepted + reason`，或 `unresolved for external review`；Reviewer concern level、数量或不满意本身不决定状态。
3. Aggregate、Finding、disposition 和 repair delta 都绑定当前 exact Candidate/hash；旧版或 stale 结果不能混入。
4. 由同源 Review Record 渲染的“内审意见” companion view 已生成并绑定同一 PRD ID/version/hash；主 PRD 的相对链接和关注项数量与之相符。

若主 Agent 决定采纳的 current-PRD 修改仍未完成，Finalize 把控制交回 `prd.optimize`；若主 Agent接受某项上游修复建议，则走现有最早 repair target。若没有 Agent 决定继续采纳的修改、其余 concern 均已有处置，或已达到既有 round/no-progress 上限，Finalize 以人话记录“内部审查已完成”或“内部审查已完成，并保留 N 项关注供外置团队判断”，然后进入唯一 `prd.ready.gate`。它不要求所有 Reviewer PASS，也不因 Reviewer unavailable、unresolved concern 或关注等级阻塞；同 exact inputs/rules 必须给出同一完成结果。

Finalize 不能修改 Candidate、裁决专业观点、批准内容、解释模糊建议、创建新修复，或把外置团队尚未审核写成“已通过”。输入 stale/missing、Finding 丢失、disposition 缺失或 companion view 版本不一致时，只返回 exact process unmet condition + repair target；这属于审查记录完整性失败，不是 Reviewer veto。

`prd.ready.gate` 随后只检查既有确定性产品合同、refs、version、template、REQUIRED Eval、Document Experience 和 changelog 等机械条件。Reviewer 指出的缺口只有被独立 Validator 证明违反既定合同，才因该合同缺失返回 NOT_READY；原因是 Validator 规则，不是 Reviewer 权力。正式 Reviewer Block/Review Gate/Domain Policy/Waiver 仅保留为未来无人值守研发/发布的 Roadmap seam，本期不定义实现。

#### 12.4.3 `prd.optimize / 根据审查意见修订 PRD`

**形态与启动边界。** `prd.optimize` 保留为可恢复 Agent 节点，是既有通用 Review–Optimize engine 的 PRD profile，不是程序写 PRD，也不是可以重写一切的“自由优化”。只有主 Agent 对 Aggregate 中某项 current-PRD 建议作出“采纳并修复”的 disposition 时才能启动；根因在 Problem/Evidence、Product Decision 或 Plan/Slice 时，必须返回最早正确上游，禁止在 PRD 里用更流畅的文案“圆回来”。未采纳或有争议的 advisory concern 保留理由并进入内审意见，不要求继续改到 Reviewer 满意。

**exact 输入与产出。** 每个 optimize attempt 只读 exact Candidate，已聚合且由主 Agent disposition 为 current-PRD repair 的 Findings，各 Finding 的 Evidence/affected scope/repair requirements，以及 exact Decision/Plan/Slice/Guardrails、Template/Eval refs。一轮批量修订完成时输出：

- 一个新的 versioned PRD Candidate，不覆盖旧版。
- 简短 material delta 和 `finding_id → change/ref` mapping。
- 未修改项、理由及建议的正确上游/等待点。
- 因 delta 需 stale/重审的 PRD 章节、Eval 和 Reviewer scope。

Optimizer 只能提交 `claimed repair`，不得把自己的修订标成 `FIXED`、PASS 或 Ready。后续独立 Reviewer 通过 targeted re-review 正式记录 `FIXED / IMPROVED_BUT_OPEN / PERSISTENT / REGRESSED / INSUFFICIENT_EVIDENCE`，并同时回归目标、范围、Guardrail、Shared Contract、AC/Eval 等全局不变量。

**最小必要修订。** 一轮只修已确认 Finding 及不可避免受影响的内容，不得顺手增加功能、用户、平台、商业模式、范围或没有上游依据的“优化”；结构性错误不能靠润色文案掩盖。默认由主 Agent 将一批修复单点整合。只当复杂修复互不依赖时，才可以让 bounded subagents 提交只读 patch/proposal；它们不并发写正式 Candidate，主 Agent 仍是唯一合并者。

**有界子图与轮次。** Review–Optimize 是 Orchestrator 编排的既有有界子图，不另注册一个“大 Loop Node”：

```text
Candidate vN
  → review.parallel → review.aggregate → disposition
      ├─→ review.finalize → prd.ready.gate
      ├─→ accepted upstream repair proposal
      └─→ prd.optimize → Candidate vN+1
                  → targeted re-review + global invariant regression
                  → aggregate → disposition/finalize → ...
```

一轮精确定义为“Aggregate 一批 Findings → 统一修订一个 Candidate → 定向复审一次”，不按 Reviewer 数量或 Finding 数量计数。LIGHT 最多 2 轮修订，STANDARD 默认最多 3 轮，PROJECT_SCALE/高风险最多 4 轮；只有上一轮仍有 material progress 且余下问题确实能在当前 PRD 修复时，才允许第 4 轮。State Controller 维护 `loop_id / round / current_candidate_ref+hash / profile_budget / no_progress_count / legal_transition`，Agent 不得通过节点改名、重启 attempt 或生成新 loop ID 规避预算。一期不建 token、费用或墙钟预算系统。

**提前停止和恢复。** 连续两轮无 material progress，包括只换措辞、同根因反复、重点 concern 未减少、同类回归，或事实证明根因在上游，必须提前停止，不等硬上限。达到上限或 no-progress 不得宣称“全部解决”；保存最新 Candidate/恢复点，直白显示已用轮次、已解决/未解决项、停止理由、Agent 的上游建议和保留给外置团队的 concern，并复用现有 `NO_PROGRESS / RETURN_UPSTREAM / WAIT` 语义，不新增业务路由或无必要枚举。

**Candidate version 与 Review Attempt 必须分开。** Agent 在一轮中的 scratch/临时工作过程不版本化；只有批量修订完成且实际重新送审，或形成被引用的 material checkpoint 时，才在 `archived/` 产生一个新 Candidate。每次 Review/re-review 使用独立 round/attempt 记录并引用 Candidate，不复制 PRD 文件。同一 Candidate 只新增 Reviewer/复核/disposition/证据且内容未变时，只增 Review Attempt，不增 PRD 版本。

`archived/` 只保留首次完整送审 Candidate、每轮批量修订后的实际送审 Candidate、human material edit Candidate，以及 release 前实际引用的 material checkpoint；不保存每个 Reviewer 稿、每条 Finding 中间稿、autosave、排版缓存或无内容变化复审稿，也不新增 `working/` 目录。正常 Run 目标出现 2—4 份过程稿是实践预期，不是 Gate 数量限制。

问题必须退回最早修复位置：

```text
问题定义/Evidence失效 → Decision Run / Problem Discovery
产品方向/Decision失效 → Decision Run / Product Decision
规划结构与切片错误   → Parent Plan Run / Planning Refinement checkpoint + global reconciliation
规格表达或规则缺失 → 当前 PRD Run / Spec
评估判据或案例错误 → 当前 PRD Run / Evals
实验 section 或测量错误 → 同一 PRD/Eval；若动摇 key unknown/action 则回 Product Decision
```

#### 12.4.4 PRD package 的文档生命周期与目录

现有 §20.5 已规定正式产物 immutable、变更必须新版本并记录 `supersedes`，但还缺少 PRD Review–Optimize 的具体保存点、附件定位和 release 生命周期。ADR-039 的早期物理方案让每个 PRD package 根共享一份 `assets/`，并让 `archived/`、`released/` 只保存 Markdown；这会使人无法从某个 exact PRD 直接定位附件，也会让兄弟版本共享可变素材。ADR-075 只取代它的物理目录/打包方式，继续保留 immutable、Document Changelog、supersedes 与 exact Handoff 语义。V1.4 的当前合同是 **每个 Candidate/release 都是自包含目录**：

```text
artifacts/prds/
├── DOCUMENT_CHANGELOG.md                  # append-only；按 prd_id 记录文档版本/状态事件
├── archived/
│   └── BPG-PRD-0042_消息中心优先级_v0.3_2026-08-20/
│       ├── BPG-PRD-0042_消息中心优先级_v0.3_2026-08-20.md
│       ├── BPG-PRD-0042_消息中心优先级_v0.3_内审意见.md # formal review finalize 后生成
│       └── assets/                         # 仅在 Markdown 实际引用附件时存在
│           └── message-flow-draft.png
└── released/
    └── BPG-PRD-0042_消息中心优先级_v1.0_2026-08-20/
        ├── BPG-PRD-0042_消息中心优先级_v1.0_2026-08-20.md
        ├── BPG-PRD-0042_消息中心优先级_v1.0_内审意见.md
        ├── assets/
        │   ├── message-flow.png
        │   ├── interaction-demo.mp4
        │   └── data-contract.xlsx
        └── exports/                        # 按需；无导出时不建
            ├── BPG-PRD-0042_消息中心优先级_v1.0_2026-08-20.docx
            └── BPG-PRD-0042_消息中心优先级_v1.0_2026-08-20.pdf
```

目录与主文件的稳定命名是 `<PRD-ID>_<需求短名称>_v<版本>_<YYYY-MM-DD>`；派生 export 使用同一 stem，不使用 `prd.md / final.md / 最新版.md`。同源内审意见使用 `<PRD-ID>_<需求短名称>_v<版本>_内审意见.md`，并通过视图头部绑定 exact 主 PRD ref/hash 和日期；它随 PRD version 更新，不单独快速递增版本。PRD ID 在版本和标题微调间保持稳定；只有范围已经成为新的独立产品增量时才分配新 ID。

过程目录采用 `archived/`；正式目录采用 `released/`。不使用 `final/`，因为 release 后仍可能产生 v1.1；不使用 `published/`，因为 PRD 可正式交接但未对外公开；不使用 `approved/`，因为批准本身不代表 Ready、文档验证和 Handoff 条件全部成立。`released` 的唯一语义是：该版本已绑定所需忠实一致性/专业 Review、Ready 与 Document Experience validation，成为可被正式 Handoff 精确引用的不可变 BPG PRD artifact set。它不表示组织外置汇总审批已经通过，也不表示 Connector 已发送。

`archived/` 保存 material checkpoints：首次完整送审 Candidate、每轮 Optimizer 批量修订后实际重新送审的 Candidate、人类 material edit，以及模板/policy/profile 迁移后实际被 release/Review 引用的 Candidate。候选引用附件时使用与 release 相同的 per-candidate 自包含目录；formal review finalize 后，同目录生成与该 exact Candidate 绑定的内审意见视图。无附件或导出时不创建空目录。它不保存每个 Reviewer 稿、每条 Finding 中间稿、token、keystroke、autosave、排版缓存或无内容变化的复审稿。

`released/` 保存**所有**正式 release，通常从 v1.0、v1.1 递增，不是“只放最新版”。每个 release 目录必须能独立复制、发送、归档和定位，不依赖兄弟版本共享可变素材；主 Markdown 只用 `./assets/...` 相对路径，已经被 release 引用的 Markdown、内审意见和 assets 都不得覆盖。每个 release 只渲染一份当前内审摘要：默认只列仍未解决、存在分歧或需外置团队判断的 concern，包含关注等级、具体事项、exact basis/ref、可能影响、Agent 建议和 disposition/未处理原因；完整 Findings、已修复项和 attempts 留在 Review/Audit/Changelog。旧 release 后续被 `SUPERSEDED / INVALIDATED / REVOKED` 时仍留在 `released/`，不移动到 `archived/`、不删除、不改写。

主 PRD 正文不复制详细 concern，只保留相对链接和短状态，例如“内部审查已完成，尚有 N 项重点关注；详见同目录内审意见；外置团队审核尚未完成”。没有遗留项时写“截至当前版本，内部审查未保留需要外置团队特别判断的未解决事项”，不能写“无风险/已批准”。单文件 export profile 可以把同源内审意见附在 PRD 末尾；canonical Markdown 职责仍分离，合并导出不是第二份手写真源。

`artifacts/prds/DOCUMENT_CHANGELOG.md` 是 append-only PRD 文档生命周期账本，以 `prd_id` 区分各 PRD 的事件；它不被复制进 release/Handoff。它**不同于**记录产品语义变化的 Product Changelog，也不同于仓库架构版本的 `docs/architecture/CHANGELOG.md`。每个 material version 至少记录：

- `prd_id / document_id / version / lifecycle_status`。
- `created_at / created_by`。
- exact `source_prd_candidate_ref + hash`、parent Decision/Plan/Slice/Knowledge refs、可选 `source_content_checkpoint_ref + hash`，以及 template/policy/profile exact versions。
- `supersedes` 或 `source_draft_ref + hash`。
- `change_type / change_summary / reason`。
- Review、忠实一致性 Finding/disposition、Ready 和 Document Experience validation refs；若历史或条件式流程实际发生 Owner/Domain/Connector authorization，则记录对应 exact event/ref，不把它写成当前默认前置。
- 主 Markdown 的 `content_hash`，以及该 Candidate/release 实际引用的 assets 与可选派生 export 的 exact refs/hashes；派生 export 还要回指 source Markdown+assets hashes。

状态变化用新事件/新记录追加，不能修改历史行。既有可变 manifest/current 导航如果实现，必须能由不可变目录、Changelog 和 Audit Ledger 重建；它们不能创造产品事实或成为第二真源，也不会被复制成一份独立 Handoff manifest。

Review–Optimize 每一轮按以下方式落档：

1. 将本轮送审内容及其引用 assets 冻结为 `archived/` 中的 exact self-contained review Candidate directory，并让所有 Reviewer/Findings 引用其 version/hashes。
2. `review.aggregate` 保存本轮 Review Attempt refs；`prd.optimize` 基于 exact candidate 统一修订该批 Findings。只在修订后的内容实际送入下轮 Review 或成为被引用的 material checkpoint 时，才生成一个新 archived version，记录 finding→change、unchanged+reason、delta、`source_draft_ref`、stale/re-review scope；不得改写旧候选。
3. 人类对范围、规则、AC 或其他 material 内容的编辑也必须先返回正确上游形成合法新语义，再生成新 archived candidate，并按影响使旧 verdict/Ready stale；不能在 PRD 阶段用临时批准替代上游 Decision/Plan/Slice 变更。
4. 只有 exact Candidate 的忠实一致性结果、所需 Review disposition、PRD Ready 和 Document Experience validation 全部有效时，才从它生成 immutable self-contained released directory；release 必须绑定 `source_draft_ref + hash`。
5. Handoff 只消费 exact released artifact set；“候选已生成”“已批准”“Ready 计算中”或“导出文件已生成”都不能被写成 released/已交接。

文档呈现变化与产品语义变化必须分开：模板、排版、术语或可读性修订即使不改变产品语义，也创建新的 released version 并保留旧版；若范围、产品规则、流程、AC、Eval 语义或承诺发生变化，必须创建新的 archived PRD Candidate；若变化还改变上游 Decision、Plan、Slice 或共享合同，应先生成相应的新版本/变更记录与 Impact，再重新 Review/Ready/release，不能只改 released Markdown。**本地/Git canonical truth 是 exact released Markdown + 该 Markdown 引用的 assets**；同 stem DOCX/PDF/ZIP 仅由 Renderer/Export Adapter 按需派生，不要求每个 release 全部生成、不改变产品语义、也不成为 Ready 默认条件或第二真源。

本节复用现有 `prd.render / review.aggregate / prd.optimize / artifact.version.guard / prd.ready.gate`。第一版直接把 exact release 作为本地交付单元，不注册 `handoff.package.build`、物理复制、独立 packager、manifest、兼容事件、Graph Node、Gate、HITL 或第二真源。

### 12.5 Reviewer advisory-only 与外置审核边界

**一期合同已确认。** 所有 BPG Reviewer 都只提供建议：它们可以是 Product、UX、Engineering Feasibility、Testability、AI Behavior、Security、Privacy、Compliance、Legal、Finance 或其他 Domain 逻辑角色，也可以由 internal sub-agent 执行；但没有任何 Reviewer formal `BLOCK`、veto、approval、waiver authority，也不因为使用了“专业 Reviewer”名称就冒充真实组织责任人。当前每份需求仍有外置团队最终审核，BPG 的职责是提高候选质量、保存分歧并把关注事项清楚交过去。

Finding 的最小人类合同只有：直白 concern、关注等级、exact basis/ref、可能影响、专业建议/建议返工点和 disposition；结构化细节见 §12.3.1。关注等级只用于排序，不赋权。旧 `PASS / PASS_WITH_CONDITIONS / NEEDS_OWNER / BLOCK_RECOMMENDED`、`severity`、`blocked_actions/still_allowed` 或 Waiver 字段若出现在历史设计/记录中，只保留为历史解释，不进入一期 current-state routing、Ready 或 release 条件。

主 Agent 对每项建议作出透明 disposition：

- **采纳并修复**：建议清晰、有上游依据且最早修复点在当前 PRD 时，进入有界 `prd.optimize`；Reviewer 后续复审 repair status。
- **建议返回上游**：确实动摇 Problem/Decision/Plan/Slice 时，Agent 提出最早返工点；是否形成 material 产品改变仍由对应 Owner/节点决定，不由 Reviewer 直接改状态。
- **不采纳并记录理由**：建议不适用、证据不足、超出当前 scope 或会引入无依据功能时，保留原 concern 与 Agent 理由。
- **保留给外置团队判断**：存在合理分歧、专业事实不足或达到 no-progress/轮次上限时，停止机械改写，在同源“内审意见”视图中披露。

Reviewer 冲突不按多数投票，多 Agent 同意也不增加 Evidence confidence。Bounded review-of-review 只帮助澄清高影响 concern，不产生批准。`review.finalize` 只检查 attempts、disposition、exact version 和 companion view 完整；`prd.ready.gate` 只执行独立确定性产品合同检查。未解决 advisory concern 必须披露，但本身不是 NOT_READY 原因，也不能让 Reviewer 无限占住 Run。

考虑过在一期就配置 Project Policy、Domain Owner、formal Block、action scope 与 Waiver/expiry，但这会复制现有外置审核并把 AI 建议错误升级为组织权力，故明确不建设。未来只有真正进入无人值守研发/发布、且外置团队不再承担最终责任时，才在 Roadmap 中基于真实身份、权限、责任、失效与重验证需求设计 autonomy governance；当前文档不预先定义其 Schema 或实现。

### 12.6 PRD 阶段的人类介入与外部写入授权

一期当前流程不把 `prd.owner.confirm_understanding` 或 `handoff.owner.approve` 注册为每份 PRD 的固定步骤、事件、alias 或迁移输入；只有 `product.decision` 的 Owner choice 与条件式 Connector side-effect authorization 保留人类责任语义。

PRD 阶段只在两类情况打断人：material ambiguity 或上游产品决定必须由 Product Owner 判断；versioned Connector side-effect policy 要求对外部写入取得一次权限。前者返回相应上游形成新决定，后者只授权 exact Connector、target、artifact version/hash 与 action，不重新审核 PRD 语义。安全/隐私/合规/资金等 AI Reviewer 的意见进入内审意见并交外置团队，不在 BPG 内另建 Domain Owner approval。

因此 self-contained BPG Released artifact set 可以在 `prd.ready.gate` 通过后自动形成并直接作为本地交付单元。`handoff.dispatch` 若命中有效预授权则自动执行；未命中时按 §18.1 的 dispatch policy 停在相应状态并显示所需外部写入权限。无 Connector 时本地交付物仍然完整可用。无论哪种情况，BPG `READY / RELEASED / READY_TO_DISPATCH / SENT` 都不得被渲染成组织外置汇总审批已经通过。

---

## 13. 什么是好的 PRD

好的 PRD 是：

> **在明确产品能力模块和迭代边界内，高内聚、低耦合、能够独立产生并验证一个产品结果的增量产品合同。**

这里的“增量”不表示越小越好。不能再拆的标准是：继续拆分会损害产品价值、模块内聚性、端到端闭环、可验证性，或带来不合理的重复规则和协调成本。PRD 也不追求一次覆盖完整终局；它只承担当前 Iteration 中一个边界清楚、可以交付、学习和停止的产品增量。

必须满足：

1. 追溯到原始信号、问题定义、证据和产品决定。
2. 以确切版本和内容哈希绑定 `decision_refs`、`roadmap_snapshot_ref`、`product_plan_ref` 和 `knowledge_snapshot_ref`，并关联 Module Map、Iteration Map、PRD Matrix 和 Slice；不接受仅指向“current/latest”的可变引用。
3. 明确自己的主要产品能力模块、产品责任和外部共享合同，内部高内聚、外部低耦合。
4. 明确所属迭代及其 Target Operating Outcome、Observable Evidence、Non-sacrificable Guardrails、父级 Current Iteration Outcome 和本 PRD 的 PRD Increment / Increment Contribution。
5. 只有一个主要产品结果，可以独立产生、观察和验证价值；若属于跨模块闭环，则明确父级 Current Iteration Outcome、必要 Batch 和其他模块 PRD 的边界。
6. 范围、非目标、依赖、共享规则和后续迭代清楚，不把未来完整规划塞入当前实现范围。
7. 用户流程、状态、规则、分支和异常在本增量边界内完整。
8. 与需求有关的权限、数据、性能、安全、兼容、灰度和回滚要求明确。
9. 关键需求有可观察、可判断的验收标准。
10. 指标、埋点、成功和停止条件明确；需要 Product Evals 时，PRD 与 Eval Pack 对同一结果使用一致定义。
11. 未确认事项、负责人和影响公开。
12. Authorization、epistemic confidence/evidence gaps、风险等级和 action constraints 分开披露，Owner 拍板没有被写成事实证明。
13. 适用 Reviewer attempts 已完成或明确记录不可用；所有 Finding 都有 disposition，未解决/分歧 concern 已在同源内审意见中披露。关注等级与 Reviewer 建议不构成 BPG 批准或阻塞，外置团队审核仍独立。
14. Evals Applicability 与 Fulfillment 分开且都有直白 Human View；`NOT_NEEDED` 理由成立，`RECOMMENDED` 的建议/放弃影响透明，`REQUIRED` 时 exact Eval Pack 已完成所需 Review，不存在被旧 `DEFERRED` 隐藏的 `BLOCKED_MISSING_INPUT`。
15. 可以通过 exact self-contained Released artifact set 独立交付；只有客观上不能独立发布时才作为 Batch 中边界独立的成员交付，并披露共同回滚/停止条件与耦合风险。
16. 忠实一致性检查证明当前 PRD 没有超出 exact Decision/Plan/Slice、偷带 future、编造事实或遗漏关键约束；任何 material Proposal 已返回正确上游，而不是靠 PRD 阶段临时批准变成正式规则。

### 13.1 模板可配置

Core 由 `prd.content.build` 先组织完整产品语义，再由 `prd.render` 按项目模板组织表达；两项能力默认连续完成并产生一份 PRD candidate，而不是两份并列正式文档。

V1.4 不把“领域无关 general 模板必须先通过人工 Review 才能成为默认”冻结为当前硬前置。当前 active/fallback 由 versioned Template Profile 配置解析；在配置尚未明确 promotion 其他候选时，一期可继续使用以下 exact upstream fallback：

```text
source: references/upstream-skills/better-product-plan
revision: 6a7b5439b236bad19122ae9c7d625425b8756966
template: references/upstream-skills/better-product-plan/references/product-prd-template.md
```

对实际模板的审计确认，它本身已经覆盖范围、产品三问、模块/优先级/依赖、用户故事、触发、规则、分支、异常、Acceptance Criteria、NFR、安全/兼容、灰度/回滚、埋点、多语言、决策日志与待确认事项；Better-Product-Plan 还已有 Requirement Understanding Summary 与 planning artifacts→PRD section mapping。这些已有承载面是一期不默认另造完整 Product Spec 的直接依据。

`template.resolve` 使用 versioned **Template Profile / PRD 模板配置**，不使用易与 Host Adapter、Connector 混淆的“Template Adapter”。选择优先级固定为：

1. 项目显式配置的当前 Template Profile。
2. 从受信项目知识中可确定识别的当前模板及版本。
3. Better Product Graph 通用默认模板。

只要 exact 有效模板可确定，Agent 就不能询问 PM。只有多个候选互相冲突、且通过项目配置、知识版本和有效期仍无法判断哪个当前有效时，才允许一次聚焦询问；该询问属于 `prd.generate` 的恢复上下文，不增加独立 HITL 节点或模板 Router。

项目可以换模板，但不能降低 Ready 标准。每个 Template Profile 必须声明必要产品语义到模板 section/field 的显式 mapping；模板没有对应栏目时，按 Profile 把内容放入约定扩展/附录，默认直接渲染进同一主 Markdown。第一版不实现未发布 `ready-supplement.md` 的兼容输入；只有确实无法表达/绑定必要语义时才由 Validator 判定模板不兼容，不能因为栏目名不同就拒绝，也不能静默丢失。

模板是表达容器，不是事实生成器。Agent 不得为了填满栏目编造 OKR、埋点 ID、性能指标、合规结论或 Owner；未确定内容必须标为“待确认”，并绑定建议 owner/source、对当前 PRD 的影响和解决条件。若缺口会改变方案、范围、价值判断或承诺，`prd.generate` 必须返回 Planning/Product Decision 的正确修复点，而不是在 PRD 中用占位文案掩盖。

一期对当前过渡 Better-Product-Plan fallback 只补足以下通用合同，不另造一份完整 Spec：父 Product Plan/Slice/Decision exact refs、PRD Increment / Increment Contribution、`CONFIRMED / ASSUMPTION / UNKNOWN / VERIFY` 边界、Shared Contract/跨 PRD 依赖、Evals applicability/Eval Pack ref，以及文档 version/Review/release status。模板字段可以使用不同名称或编排顺序，但仍须映射 Target Operating Outcome、Observable Evidence、Non-sacrificable Guardrails、Current Iteration Outcome、Module 和 Iteration。Futu、moomoo、券商、投教等项目专属 checklist 继续属于 project configuration/profile，不升级为通用产品语义底座。

#### 13.1.1 通用模板候选与演进 seam

当前 Better-Product-Plan 实模板具备很强的完整性，但其中 Futu、moomoo、象象银行、券商、投教、金融监管等专业字段与所有项目的默认入口耦合。长期把它直接作为 BPG 通用默认，会迫使非金融项目处理无关栏目，也容易让项目 checklist 被误当 Core 语义。因此仓库已从它派生**领域无关的 general PRD Template Profile v0.1 Draft**，删除上述专业项，同时保留并通用化多语言、版本兼容/老用户影响、数据上报/分析、性能、安全、隐私、灰度/回滚和跨团队同步等跨项目能力。

该 general 模板目前只是 Draft/Bootstrap 候选，不是 quality-complete 或已经激活的通用默认。V1.4 只冻结 Template Profile 可配置、exact version、fallback、项目 override、pin/rollback 与不静默丢语义的边界；模板内容优化、版本升级提示、migration、何时 promotion/取代 upstream fallback，以及未来是否增加 frontend、backend/service Profile，都留在 Roadmap 单独推进。promotion 可使用实现期兼容性与真实消费者证据，但当前不设置固定人工 Review Gate。模板升级通过配置发生，不新增 Graph Node、模板 Router 或每份 PRD 的固定人工确认。

### 13.2 Document Experience Policy：从表达原则到横向执行机制

#### 13.2.1 背景与第一性边界

正式结构化 Artifact 解决机器可验证、恢复和审计问题，却不自动保证产品经理、研发或测试能迅速理解当前结论、证据边界、责任和下一步。反过来，单独维护一份“写得很好”的文档又会制造第二真源。第一性边界因此是：**业务事实只保存一次，人类视图必须从确切正式 Artifact 可重建；理解质量要能执行和校验，但不能把呈现本身升级成新的业务流程。**

Document Experience Policy 是 Core 的横向执行规则，不是新的 Graph Node、Loop、正式业务 Artifact、Gate、状态、Runtime、Service、MCP 或 CLI。它复用已有构建/渲染动作、Validator、Reviewer 和 Ready/Handoff Gate；Human View Metadata 只嵌入视图头部，validation result 只是呈现合同的检查结果，二者都不进入产品事实真源。

考虑过但拒绝的方案：

| 方案 | 拒绝理由 |
|---|---|
| 只把可读性原则写进 Skill 提示词 | Agent 可以遗漏、使用过期模板或自行宣布完成；State Controller 无法重算是否绑定了正确 source/policy/profile/template |
| 所有产物统一经过同一套重型文档流程 | Incident、Bug 和机器记录会被无关篇幅与 Reviewer 延迟；重量必须由用途、风险和受众决定 |
| 新建 Document Graph / Document Loop | 它没有独立业务状态、Owner 或交付目标，只会复制现有节点、恢复与 Gate 语义 |
| 把人类易读副本当作可独立编辑的正式产物 | 同一事实会在结构化 Artifact 与文档间漂移，审计无法判断哪份为准 |

#### 13.2.2 只保留四个概念

| 概念 | 职责 | 不是 |
|---|---|---|
| **Document Experience Policy** | Core 提供的共同最低理解边界及版本化执行规则 | 新业务 Gate 或统一长文模板 |
| **artifact-specific Profile** | 按 artifact 用途、受众、行动风险决定展示重点、密度和是否需要语义 Review | 新 Run profile、Graph 分支或产品 Artifact |
| **Human View Renderer** | 从正式 Artifact 与确切配置生成可重建的人类视图，并嵌入 Human View Metadata | 新真源或允许手工漂移的副本 |
| **Document Experience Validator / 按需 Readability Reviewer** | 前者确定性检查最低理解项、绑定和新鲜度；后者在 profile/risk 需要时提出 advisory findings | Reviewer 自行批准/阻塞，或一套新的 Ready 状态机 |

默认 Policy 由 Core 提供。项目可以配置 `language`、section order、display density、template 和加强要求，但不得删除最低理解项。**模板决定怎么排，Policy 决定至少让人理解什么**；Profile 决定某类产物用多重的表达。每次渲染必须记录 policy、profile 和 template 的 exact version，不能只引用 `current/latest`。

共同最低理解项是：当前结论、适用范围、evidence boundary/关键依据与 unknown、Owner/authority、当前 status、正式 source 的 exact version/hash、下一允许动作。某项确实不适用时使用 `NOT_APPLICABLE` 并说明理由；源材料确实不可得时按业务合同使用 `NOT_AVAILABLE`，不能静默省略或由 Renderer 编造。

#### 13.2.3 映射现有环节，而不是增加持久节点

| 已有生产/查看环节 | Human View Profile | 重点 |
|---|---|---|
| Product Decision | `decision` | 默认一屏：一个中文首选、最多三个关键依据、最多一个 material 认知提醒、一个定性判断边界、一个具体下一步；material 最强反方可加一句，完整证据/选项/分析/风险/历史/Audit 渐进展开 |
| Product Planning | `product_plan` | 运行结果、模块/迭代、依赖、覆盖、Owner 和承诺边界 |
| `prd.render` | `prd` | 产品增量、范围/非目标、规则/流程、AC/Eval、风险、exact 上游绑定与 Handoff 边界；Review 收敛后可从同一 source 渲染按需一页最终摘要 |
| `evidence.map` 的 human view | `evidence` | provenance、claim/冲突/unknown、MVU 和版本变化 |
| `review.aggregate / review.finalize` | `review_summary / internal_review` | 完整机器记录的按需摘要，以及与 exact PRD 同目录的未解决/分歧/外置判断 concern companion view；不复制成手写第二真源 |
| Incident Verification Packet | `incident` | 发生什么、影响、未知、研发核查问题、Owner 和紧急下一步 |
| Bug Fix Brief | `bug_fix` | 当前基线、expected/actual、恢复边界、non-goals、AC/回归面 |
| `audit.view` | `audit` | exact event/artifact chain、结构化理由、override、变化与权限过滤 |
| `handoff.dispatch` 准备的视图 | `handoff` | 交付对象、exact source、边界、约束、所需动作与真实回执状态 |

Run State、Schema、Audit Event 和内部索引等纯 machine records 保持原始 JSON/YAML，不为可读性扩写真源；用户有权限且确有解释需要时，才通过 `audit` 或对应 on-demand human view 呈现。`audit.view` 仍读取原 Audit Ledger，不复制第二份账本。

#### 13.2.4 可执行链与不可绕过性

```text
正式结构化 Artifact / Review Record（唯一业务真源）
  → resolve artifact Profile + project policy/template
  → existing build/render node 调用共享 Human View Renderer
  → document.experience.validate（确定性共享 Validator）
  → 按 profile/risk 调用 Readability Reviewer
  → 现有 Ready / Handoff 边界消费结果
```

这里没有新增持久节点：例如 `prd.render` 在原 attempt 内完成 PRD human view，Decision/Planning/Incident/Bug/Handoff 由各自已有 build/prepare 动作调用同一组件；`document.experience.validate` 是共享 Validator 名称，不是 Graph node ID。Orchestrator 必须向调用传入 `artifact_type / profile_id / profile_version / policy_version / template_version / audience / language / source_artifact_ref+hash`，Agent 不能自行省略或降级 Profile。State Controller 在相关 Ready/Handoff 迁移时重新解析绑定并运行 Validator；Agent、Renderer 或 Reviewer 都不能自报“可读性已完成”。

`decision` Profile 还必须确定性检查 human-facing output 不是 bare-code-only，并执行 §10.2.1 的默认信息预算：一项结论、最多三项关键依据、最多一项 material 认知提醒、一项定性边界和一个具体下一步；material 最强反方按需一句，`COMMIT` activation 使用直白句子。Owner confirmation view 另按 §10.3.1/§10.3.3 检查五项、系统字段自动绑定与 chosen-outcome-only `outcome_details`；material disagreement 时再按 §10.3.2 检查双方 outcome/理由、authorization、accepted uncertainty/risk、recheck/stop、execution constraints 和一次 bounded substantive challenge 记录，无分歧时不得生成占位块。当 §10.1 action-risk classification 会改变下一步时，视图必须用直白语言说明等级、原因和后续影响；`RISK_PENDING` 不得被渲染成低风险。缺最低项、无按需展开入口或无 source binding 时 `document.experience.validate` 失败。数量是默认层级预算而非死字数：重大安全、合规、资金、隐私或不可逆风险必须在默认视图充分披露，即使超过一屏。Renderer 只能从同一个 exact Decision Draft/Record 及其引用、enum/activation/risk 字段渲染，不能创建或手改第二份产品决定真源。

`prd` Profile 的一页最终摘要不是 Owner approval view。Renderer 只能从 exact PRD Candidate、上游 refs、Review Findings/delta 与 Audit 生成最终交付、material changes、关键修复、残余风险/Unknown 和下一去向；它按需查看，不是 `prd.ready.gate` 的阅读确认项。`internal_review` companion view 从同一 Review Record/Aggregate/Findings 确定性渲染，只保留未解决、分歧或需外置团队判断的 concern，并绑定 exact PRD ID/version/hash；主 PRD 只生成相对链接与短状态，单文件 export 可同源附录。Validator 检查二者 exact version/count/link 一致，且不得把 BPG `READY/RELEASED`、`READY_TO_DISPATCH` 或 Connector `SENT` 写成组织外置审批通过，也不能用漂亮摘要隐藏 REQUIRED Eval 缺口。

Validator 确定性检查：最低理解项是否存在；source/policy/profile/template 是否绑定 exact version/hash 且仍为当前允许版本；Human View 是否因 source 或依赖变化而 stale；结论、范围、evidence boundary/unknown、Owner/authority、status、next action 是否可定位；Handoff 是否区分“已生成/待发送/已发送/已接收”。缺少会导致读者执行错误动作的最低理解项时，结果可以让**原有**对应 Ready/Handoff Gate 不通过；这不是第五种概念或新增 Gate。

Readability Reviewer 只检查确定性规则不能判断的语义问题，例如术语堆叠、结论埋藏、文本流畅但隐藏未知、重复导致边界模糊、授权被写成事实、面向错误受众。它只产生 advisory Finding/建议，不能批准、否决或阻止 Ready；真正可执行的当前期约束只来自已确认的确定性 Document Experience/Artifact 合同并由 State Controller 重算，专业责任留给外置团队。

#### 13.2.5 重量、真源和版本规则

- Product Plan、PRD 和重大 Decision 默认运行语义 Readability Review；PRD 的 Product Reviewer 还必须优先检查 semantic fidelity/alignment。低影响 Decision 可由 Profile 降为确定性检查。
- Evidence、Review Summary 和 Audit 的人类视图重点展示来源、冲突、变化和结构化理由，不用散文复制全部正式记录。
- Incident 与 Bug Fix 默认只做最小行动性结构检查；非关键缺失允许 `NOT_AVAILABLE`，不得因文风、章节顺序或补齐长文延迟紧急交接。只有理解项缺失会直接导致错误行动时，原有 Handoff 才能被相应阻止。
- Machine records 只提供按权限 on-demand view，不改写或扩写原始 JSON/YAML。

每个人类视图头部都嵌入：`source_artifact_ref/hash`、`policy_version`、`profile_id`、`profile_version`、`template_version`、`rendered_at`。source、policy、profile、template 或其声明依赖的版本变化后，旧视图立即标记 `STALE/INVALID`，并从新绑定生成新的 rendered version；旧视图保留用于审计，不得被原位手工修改来掩盖漂移。人类注释若需要保留，必须作为回指 source/view 的独立反馈或 Finding，不改变视图和正式 Artifact。

PRD 的项目可配置模板仍默认使用 §13.1 的 `better-product-plan` 冻结模板，但必须映射 `prd` Profile 最低理解项；承载不了的内容进入同一 PRD 的逻辑 Supplement，并默认渲染为主 Markdown 的扩展/附录。其他产物也允许项目模板覆盖展示方式，不允许删除最低理解项或改变业务 Schema。

第一期只保证有真实消费者的最小 Profile 集：`product_plan / prd / internal_review / decision / incident / bug_fix / handoff / audit`。其中 `product_plan` 只先支持 §11.6 的按需一页规划摘要及 exact source binding，不借此冻结全部规划展示模板；`internal_review` 是 Review Record 的 companion Human View，不是业务 Artifact。`evidence / review_summary` 等映射继续保留稳定语义，随着对应真实生产者和消费者成熟再冻结合同。不能为了架构完整一次性冻结所有 Profile，也不因此增加独立 Runtime、Service、MCP 或 CLI。

---

## 14. Core Contracts 与 Schema

> **实现与验证参考层导航**：§14—§21 说明机器合同、State Controller、Knowledge/Handoff/Connector、Ready、Audit 和 Host 适配；§22—§24 说明一期范围、建设切片和验收。它们用于实现与验证，不是第一次理解 Product Loop 的必读前置。产品经理可以先读文首、§6、§8—§13，再按需要回到本层查精确合同。

### 14.1 第一期先落地的三个逻辑合同

- Node Result。
- Run State（Decision / Plan / PRD 三个 profile；`EXPERIMENT` 只是 Plan/PRD 的 delivery intent，不增加 profile）。
- Audit Event。

三个逻辑合同从 `v0alpha` 开始，通过真实端到端实现切片后再冻结兼容规则；这不等于每个 Run 保存三套机器账本。按 ADR-080，一期每个 Run 的持久机器记录只有 current state snapshot 与 meaningful event stream 两类；Node Result 是原子能力提交给 Controller 的执行合同，被消费后只引用正式 Artifact、更新 snapshot 或形成必要 Audit Event，不另建全量永久流水。文件名与完整字段仍待实现，不把示例 `state.yaml/state.json/events.jsonl` 冻结成 Schema。

### 14.2 随业务实现成熟的合同

- Raw Signal Envelope / Prepared Signal / Signal Relationship Set / Classification Record / Route Decision Record / `existing_links` / Signal Ledger / current-route pointer；Raw Envelope 由 Host/Connector 根据自然原文或原生结果自动构建并附 provenance，不是要求外部人员填写的 YAML 表单。Route Contract 只接受四个互斥 destination，关联维度或下游 result kind 不得伪装成第五条路线。
- Evidence Reference / Problem Evidence Map（`problem.evidence.map.v1`）/ Learning State / Learning Round Delta / Evidence Request / Learning runtime status / completion disposition / next-action recommendation；Evidence Reference 保存不可变 provenance，Map 保存 append-only 的 run-local 关系判断，两者不得互相替代。Learning Round Delta 是 Learning State 内部 checkpoint section；Evidence Request 是绑定 Run/Round/MVU/来源/有效证据/决策影响/等待与恢复条件的版本化 request/wait 合同，二者都不是新的顶层 Graph Node 或正式业务 Artifact。Learning State 将 `ACTIVE / WAITING_FOR_EVIDENCE / PAUSED / COMPLETED / CANCELLED`、`READY_FOR_SYNTHESIS / ROUTE_REEVALUATION_RECOMMENDED / INSUFFICIENT_TO_PROCEED` 和 advisory next-action recommendation 分开；只有 `COMPLETED` 可有 completion disposition。七类 `source_resolution_type` 以及 PM 访谈的 interrupt reason、核心问题/必要澄清、claim type、挑战强度、Agent 建议/最强反方、agreement/disagreement、authority、假设变化和 next action/stop reason 都复用 Learning State/Round Delta，不升格为新 Artifact、Graph Node 或业务路线；默认不把全量逐字对话当作合同必填。人工 override 的完整权限合同仍待 Review。
- Analysis Method Hook / versioned Method Card：只作为 Learning/Synthesis/Planning 内部扩展合同；Card 至少声明 `method_id / question_answered / applicability / non_applicability / required_inputs / output / limitations / cost / skill_version`，调用记录绑定 Level、五问结果、输入 Evidence refs 和方法版本。它不是业务 Artifact、Evidence、Graph Node、Gate 或集中 Registry。
- Run Interaction Policy：`interaction_policy=ALLOW_PM_INTERVIEW | NO_PM_INTERVIEW`、独立 `interaction_style`、`scope=CURRENT_RUN`、actor/time/source、policy version 和 State Controller check result；它属于 Run State/Audit 字段，不是业务 Artifact、Graph Node 或新 Gate。`NON_INTERACTIVE` 仅为 unsupported reserved value。
- Assumption Audit Checkpoint：只作为 `problem.assumption.audit` 的 versioned run-local internal checkpoint，保存输入绑定、原话/来源角色分离、五类初始表达拆分、动态关键假设、反证/替代检查、exactly one MVU、推荐信息来源、下一信息请求、结构化理由和下一建议；不提升为正式业务 Artifact、Problem Definition 或 canonical knowledge，`next_learning_information_request` 也不替代 Learning State 的三维完成合同、override 或 Evidence Request 全部字段。
- Problem Definition Candidate / Synthesis Result：`problem.synthesize` 只接受 exact Learning State=`COMPLETED` 且 completion disposition=`READY_FOR_SYNTHESIS`，并绑定 Raw Signal、Knowledge Snapshot、Product Memory Snapshot、Problem Evidence Map、Assumption Audit checkpoint、Learning State、Round Deltas 与已记录分歧的确切 version/hash。versioned Candidate 至少保存用户、场景、目标、阻碍、影响、期望改变、Evidence boundary、Assumption/Unknown、scope/non-problems，以及用户提出方案与问题的关系；Result 只能是 `COMPLETED / RETURN_TO_LEARNING / FAILED`，同时保存 source bindings、output version/hash、stale/supersedes。它是正式 Run candidate，不是 canonical Knowledge、Decision、Plan、PRD、solution 或 Problem Ready；`RETURN_TO_LEARNING` 必须携带 material gap 与新 MVU，但不能伪装成已完成的新 Learning Round。
- Problem Quality Review Attempt / Finding / Disposition / Problem Ready Calculation：Review attempt 只读 exact frozen Candidate 及绑定的 Evidence/Learning/Knowledge/Product Memory，与生成上下文隔离；首次 full review，后续 delta-targeted 且回归全局不变量。Finding 保存 evidence refs、关注事项/等级/影响与 `REVISE_SYNTHESIS / RETURN_TO_LEARNING / NEEDS_OWNER / ROUTE_REEVALUATION` advisory repair path；不编辑或写状态。固定 `problem.owner.confirm`、`PM_ACKNOWLEDGED` 与 `OWNER_CONFIRMED` 已取消。Ready Calculation 只绑定 current exact Candidate、exact Review attempt/dispositions、上游 Evidence/Learning/Synthesis refs、rules version、`READY | NOT_READY`、unmet conditions、deterministic repair targets、transition 和 Audit ref，仅可由程序化 State Controller 正式写入。Owner 产品责任由随后同屏展示 exact Problem 的 `product.decision` choice 承担；Agent 模拟 Gate 只能为 `ADVISORY_ONLY`。
- Sub-agent Attempt / Join-Aggregate Contract：绑定 parent Run/attempt、subtask role、exact input refs/hashes、Skill/policy、最小 permission profile、requested/actual model profile/provider/version、fan-out/concurrency/budget/timeout/retry 和统一 `NodeResult / Finding / Proposal` result hash/status。sub-agent 不得写 state/current/canonical knowledge/released artifact 或外部副作用；required 失败只使相关 action 未满足，optional 失败可 `NOT_AVAILABLE`。Join 保留分歧和每份原始结果，多 Agent 同意不提升 Evidence confidence；它是现有节点执行合同，不是新业务 Artifact/Graph Node。
- Review Finalize Result：`review.finalize` 的 versioned Controller transition 绑定 exact aggregate attempt/hash、Candidate ref/hash、适用/required attempts 及 unavailable reasons、每条 Finding disposition、同源 `internal_review` view ref/hash、rules version、未完成的 accepted repair/upstream target 与 audit ref。它是现有 Review Record/Run transition 的收尾记录，不是新 Artifact、Gate 或节点；stale/missing、Finding 丢失、disposition 缺失或 companion version 不一致时保持当前状态并列 exact process repair target。Reviewer concern level 不进入 blocking 计算。
- PRD Optimize Loop/Attempt：复用 Run State、Review Record 与 Document Changelog，保存 `loop_id / planning_profile / round / round_limit / no_progress_count / current_candidate_ref+hash`、允许 current-PRD repair 的 aggregate/finding refs、claimed repair 的 finding→change mapping、material delta、unchanged+reason、stale/re-review scope、new candidate ref/hash 和 stop/resume/repair route。Review Attempt 独立引用 Candidate，不复制 PRD；Agent scratch 不记版本，每轮实际送审的批量修订才生成一个 archived Candidate。这些是现有 engine/state 的恢复字段，不是新业务 Artifact 或 Loop Node。
- PRD Ready Calculation/Assertion：绑定 exact archived Candidate/hash、同版本 required Review/Aggregate/`review.finalize`、同源内审意见 view、current 关键 upstream refs、Eval Applicability/Fulfillment/Pack refs、Template/Document Experience/version/changelog validation、rules version 与 `READY | NOT_READY`。advisory concern 可披露但不因未关闭而阻塞；若 Reviewer 指出机械缺口，只有 Validator 独立命中既定合同才返回 NOT_READY。`NOT_READY` 保存 exact unmet condition、affected ref/version、repair target 和 resume point；`READY` 原子关联 release promotion 与 exact self-contained Released artifact set ref。
- Product Plan / Target Operating Outcome / Current Iteration Outcome / Planning Item / Product Plan Candidate；同一 Product Plan 合同按版本承载 v0、`planning_profile` 及选择/变更理由、可选 Wave/Round checkpoint、material Refinement/reconciliation checkpoint、stable frozen Candidate、change summary、`supersedes` 和 impact refs，不另建可漂移的“深化报告”Artifact。Refinement 是 `product.planning` 内部 recoverable Loop；formal Review attempt 绑定 exact Candidate/hash 并复用通用 Review–Optimize engine/profile，Reviewer 只读、Optimizer 生成新 Candidate。
- Planning Views / Internal Action Contract：Module / Iteration / PRD Matrix / Dependency & Shared Contract 可独立或内嵌；`plan.slice` 在同一 Product Plan version 中保存 PRD Candidate Slice Map/List（goal/problem、user outcome、phase、modules、dependencies、verification、split rationale、source refs），不冒充 PRD；`plan.coverage.validate` 保存 item disposition、五类 Finding、profile/mode 与责任/repair refs；`plan.reconcile` 保存处置、materiality、Decision refs、Plan delta、上游 repair route 与 unresolved conflict 条件。Plan Ready Calculation 只保存 exact Plan/activation set、Coverage/dispositions、advisory Review finalize、依赖/冲突、material Decision refs、rules version、`READY | NOT_READY`、repair target 与 created child refs，不要求 Owner 确认 Plan。按需一页摘要只是同源 Human View。前三者可在 LIGHT 内联，但 exact source/output version/hash 和审计语义不能丢失。
- `EXPERIMENT` 条件化内容不形成独立 Artifact 合同：它复用 Product Plan、PRD Candidate/release、PRD Eval Pack、Review/Ready/Dispatch 与 typed-result binding，并在同一正式产物内携带 §10.4 的 key unknown、exposure、measurement、mapping、guardrail、stop/rollback 和 result-return refs。一期不建立 Experiment Plan/PRD/Eval/Ready/Handoff/Portfolio 产物族。
- Product Decision Draft/checkpoint / Decision Record / Planning Activation Event / Decision Ledger / Roadmap Registry Snapshot / Research Request / Roadmap Change Proposal / Product Changelog Proposal / Product Memory Impact List；Draft/checkpoint 是 `product.decision` 的 versioned run-local 恢复合同，绑定 exact inputs、AI Brief、按需 Review refs、分歧、Owner discussion state 与 supersedes，不是正式决定、承诺或 route。Decision Record 的确认层固定为 chosen decision、applicability scope、最多三个关键理由、最大 Unknown + flip/stop/restart condition、next action + checkpoint/trigger；material 分歧时才增加双方 outcome/理由、disagreement、authorization basis、accepted uncertainty/risk、recheck/stop 和 execution constraints，并证明已完成一次 bounded substantive challenge。系统层自动维护 identity/timestamp、exact Problem/Evidence/Knowledge/Review refs、recommendation/result、supersession、downstream refs 与 rationale/audit refs，并按适用性内嵌 action/exposure-scoped `R0—R3 | RISK_PENDING` 分类、理由和 allowed-action effect；该分类不是独立 Artifact/Node/Gate。只生成 chosen outcome 的条件化 `outcome_details`，不产生五套模板或未选项空字段。节点结束复用 State Controller transition validation 并将 pass/reject 记入既有 Audit Event；该计算不是 `decision.ready`、业务 Artifact 或新 Gate。只有 Owner exact choice 后的 immutable/versioned Decision Record 与 Controller route 是正式边界。Ledger/Roadmap/Changelog/Audit 从这份 Record 和后续 exact events 产生不同语义投影，不复制 outcome 真源；新 Evidence 对历史 Decision 的分类和逐产物 Impact List 绑定 exact evidence/decision/artifact refs。
- PRD Candidate / released PRD，以及可选的 PRD Content Checkpoint：Candidate/released PRD 是同一交付合同的生命周期版本；Content Checkpoint 仅在配置命中复杂恢复场景时保存，绑定 exact parent refs/candidate/hash，不进入 `released/`、不单独 Handoff，也不成为正式业务真源。PRD Review 合同把 Fidelity/Alignment 作为 Product Reviewer 首要 rubric，并由确定性检查绑定 Decision/Plan/Slice/Knowledge/Evidence/constraint exact refs、slice membership 与 disposition；结果继续使用既有 Finding/Verdict/delta/Audit，不生成独立 Fidelity Report。第一版只使用 `prd.content.build`，不注册旧名 alias。
- PRD Template Profile：保存 `profile_id/version`、template exact source/version/hash、选择来源与优先级、可信知识/项目配置 refs、适用/不适用范围、必要语义到 section/field/extension 的 mapping、incompatibility reason 和 resolved_at；它是 `prd.generate` 的配置/解析合同，不是 Template Adapter、业务 Artifact、Graph Node 或模板 Router。general v0.1 保持 Draft/Bootstrap 候选；何时升级为 active default 由未来 versioned 配置与 Roadmap 决定，不在 V1.4 冻结人工 promotion Gate。
- Document Experience Policy / artifact-specific Profile / Human View Metadata / Document Experience Validation Result；它们只属于呈现与验证合同，不写入或替代 PRD、Decision、Evidence、Incident、Bug、Handoff 等业务 Artifact。
- Eval Applicability Decision / Eval Fulfillment State / Product Eval Strategy / PRD Eval Pack：Decision 绑定 exact PRD/Plan/Eval Policy refs、`NOT_NEEDED | RECOMMENDED | REQUIRED`、人类结论与理由；Fulfillment 独立记录 `NOT_STARTED | GENERATING | GENERATED_PENDING_REVIEW | REVIEWED | BLOCKED_MISSING_INPUT`、missing inputs/owner/repair 与 exact Pack/Review refs。`evals.build` 另绑定 exact stable content source、scope/generate/review attempt、Pack version/hash、PRD-rule/AC traceability、coverage/gap、stale impact 和 join result，但内部三动作不注册顶层节点；最小语义见 §12.2.1，不在本期冻结庞大 Schema。第一版不实现未发布旧值的兼容迁移。TDD-ready Test Design Contract 只是 future extension，正式测试用例/代码/执行/verdict 不进入该合同。
- Reviewer Finding / Finding Disposition：PRD goal-fidelity profile 复用同一 advisory Finding，并补 `reviewer_role/profile / concern / concern_level / basis_refs / upstream_commitment_refs / affected_scope / possible_impact / professional_recommendation / confidence / confidence_basis / cross_check_status / repair_target / disposition`；cross-check 使用 `confirmed / complemented / conflicted / unique / unsupported`，repair verification 使用 `FIXED / IMPROVED_BUT_OPEN / PERSISTENT / REGRESSED / INSUFFICIENT_EVIDENCE`。关注等级只排序，不赋权；这些是既有 Review/Audit 字段，不生成独立审计 Artifact、分数或 Gate。
- Versioned Reviewer configuration / future autonomy governance seam；一期不实现 Reviewer Block、Domain Owner authority 或 Waiver。
- Knowledge Snapshot / Impact。
- Bug Baseline Assessment（`bug.baseline.assessment.v1`）/ Bug Route Recommendation / Controller Route / conditional clarification-or-override record / Bug Fix Brief（`bug.fix.brief.v1`）/ Bug Eval Pack；固定 PM Route Confirmation 已退役。
- Ready Assertion。
- Product Released Artifact Set / Incident Verification Packet（`incident.verification.packet.v1`）/ Connector Side-effect Authorization：所有 PRD（包括 `EXPERIMENT` intent）在同一个 PRD Ready 后直接使用 self-contained release，不另行构建 Product/Experiment Handoff Package；Authorization 只绑定 exact connector/target/action/artifact version+hash/policy/actor/expiry，决定能否 dispatch，不重新判断 PRD 语义。线上问题核查包使用 append-only 内容版本与轻量机械检查，不复用 Ready Assertion。
- Dispatch Attempt / Receipt（复用 State/Audit record，不新增业务 Artifact）：至少保存 attempt ID、policy/version、`PRD ID + Released Version + Connector + Target + Action` 幂等 identity、exact source directory/Markdown/assets hashes、actor/preauthorization、开始/结束时间、`PENDING / SUCCEEDED / UNKNOWN / FAILED`、远端 ID/URL/revision/receipt、query/reconcile/retry refs，以及 source 后续 invalidated/superseded 的 Impact link。Receipt 只证明该目标的可验证远端动作，不能替代 PRD（含实验 intent）、Incident/Bug 语义合同或外置审批。
- 外部回传不定义独立的通用 Feedback Artifact：纯生命周期状态复用 Dispatch/External Status，typed result 先绑定已有 Incident/Bug/Handoff、带 `EXPERIMENT` intent 的 exact Decision/PRD/Run 或未来 Test Result 记录；只有新的产品事实、冲突或挑战才派生带 exact refs 的 Product Signal。研发 Incident 回传仍追加为同一 Packet 的后续版本，返工影响复用现有 Impact List、Decision supersession 与 Audit。

“需要版本化”不等于“一期第一天全部冻结”。每个合同只有在有真实生产者和消费者后才进入稳定版本。

### 14.3 Node Result 示例

```json
{
  "node_id": "problem.synthesize",
  "node_version": "1.0.0",
  "status": "COMPLETED",
  "attempt_ref": "attempts/problem.synthesize/003",
  "artifacts": [
    {
      "artifact_id": "problem-definition-candidate",
      "version": 2,
      "path": "artifacts/problem-definition-candidate-v2.yaml",
      "hash": "sha256:..."
    }
  ],
  "evidence_refs": ["E-017"],
  "recommended_transition": "problem.quality.review"
}
```

`recommended_transition` 只是建议，State Controller 不接受它作为 Gate 结论。

---

## 15. Deterministic State Controller

### 15.1 唯一正式状态写入者

Orchestrator、原子 Skill、Reviewer、Connector 和人类 approval 都只能提交候选结果或事件，不能直接写 current state snapshot 或提升正式产物。

唯一写入者是 Plugin 中的确定性 State Controller。

一期它只是 Better Product Graph Plugin 内的本地 module/library，维护每个 Run 的 current state snapshot、append-only meaningful event stream 和独立版本化 artifacts；`state.yaml` / `state.json`、`events.jsonl` 只是可选实现示例，文件名和完整字段本轮不冻结。它不是独立 Service、MCP、CLI、daemon 或常驻进程。它的“确定性”来自 versioned rules、明确输入、纯规则计算、CAS/原子写入和自动化测试，不来自“代码天然正确”；规则版本、测试和迁移行为必须与有审计价值的状态事件一起可追溯。

若早期原型暂时用 Agent 模拟 Controller 计算，输出必须显式标为 `ADVISORY_ONLY`，不得写正式 Ready、提升 Artifact 或授权 Handoff；正式 Handoff 前必须由程序化约束重算。subagent 不能替代正式 Controller：模型有概率波动，可能被当前上下文或注入内容说服，既生成又自审存在职责冲突，并且难以让同一输入在回归测试中稳定得到同一状态迁移。

### 15.2 迁移请求

```json
{
  "run_id": "prd-run-002",
  "expected_state_version": 7,
  "attempt_ref": "attempts/review.aggregate/002",
  "requested_transition": "REVIEW_TO_READY",
  "graph_manifest_version": "better-product-graph/0.1.0-alpha",
  "gate_policy_version": "prd-ready/0.1.0-alpha"
}
```

迁移请求禁止包含：

- `gate_passed`。
- `validator_passed`。
- `all_reviewers_passed`。
- 任何要求 Controller 信任外部判定结果的布尔字段。

### 15.3 Controller 的确定性执行顺序

```text
1. 读取当前 state、Graph、policy 和 expected_state_version
2. CAS 检查；版本不匹配则拒绝
3. 校验 attempt 路径、Schema、产物哈希和引用版本
4. 执行 audit.verify
5. 重新执行 Structural Validators
6. 重新执行 Policy Validators
7. 按当前 transition 运行对应确定性检查：Review finalize 检查 attempts/dispositions/companion；Ready 检查 exact refs、Evals、template/document/version 合同；Decision/Router 检查各自已确认规则
8. 不通过：追加 transition.rejected 事件，不改变正式状态并给 exact repair target
9. 通过：追加事件、提升产物、原子更新 state
```

Controller 自己不做产品语义判断；它只检查当前规则要求的 exact artifacts、Review attempts/Finding dispositions、版本/hash、Validator 结果、Owner Decision 或 Connector side-effect authorization 是否齐全有效。Reviewer concern 不进入一期 blocking 计算；未来 autonomy governance 不得以占位字段偷渡到当前规则。

Problem Ready 时，Controller 只执行 §9.6 的三类机械规则：Problem Definition Candidate exact/current/materially valid；同版本 advisory Quality Review 已完成且所有 Finding 有明确 disposition；上游 Evidence/Learning/Synthesis/Knowledge/Product Memory refs、状态、version/hash 一致可解析。它不再检查 `problem.owner.confirm`、`PM_ACKNOWLEDGED` 或 `OWNER_CONFIRMED`，也不重新阅读文案、“凭感觉判断是否是好问题”或评估尚未选择的 action。结果只有 `READY`（自动进入 Product Decision）或带 exact unmet condition + deterministic repair target 的 `NOT_READY`；Reviewer concern 等级、普通 Unknown 或未采纳建议本身不阻塞。Owner 在随后 Product Decision 对同屏 exact Problem Definition 作 outcome choice，material 纠错必须先返回 Synthesis/Learning。

Product Decision 结束时，Controller 复用同一迁移顺序执行 §10.3.5，不调用 `decision.ready` 或第二个审批流程：重算 exact Owner-confirmed Record、合法 outcome、通用/结果专属字段、适用 action-risk/constraints、current upstream/history refs 和 material disagreement/accepted risk。通过才按 STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT 语义原子写 route；失败保持当前 Decision state，记录具体 unmet condition/repair target 并渲染为大白话，不打分、不创建下游 Run，也不要求未变化选择重复确认。Controller 不决定 Research 的内部节点形态、canonical Roadmap 发布或任何下游 Ready。

### 15.4 对抗性要求

以下请求必须被拒绝并留下事件：

- Schema 合法但缺 Reviewer 记录的 Ready 请求。
- Reviewer 绑定旧 PRD 版本的 Ready 请求。
- AI Reviewer 试图把 concern、旧 `BLOCK_RECOMMENDED` 或关注等级直接写成正式 Block/approval/waiver，或仅凭 Reviewer 意见要求阻塞整个 Run。
- 以 Sponsor 授权替代证据、提高 epistemic confidence 或移除 evidence gaps 的请求。
- Agent 为了推进而自行降低 action-risk 等级、隐藏专业关注或把外置审核呈现为已通过的 Ready 请求。
- `delivery_intent=EXPERIMENT` 却缺少测量、可观察结果、kill switch/回滚或结束条件的 PRD Ready 请求。
- 在扩流、改指标/Guardrail 或改变 action scope 后无 Impact 检查地复用原 PRD Ready/release 的请求。
- 实验 typed result 未绑定原 Decision/PRD/Run 与数据版本、成功标准被事后改写，或只提交选择性结果却要求扩大范围的迁移。
- 知识影响未处理或快照不足时的 Ready 请求。
- PRD（包括实验 intent）只引用 `current/latest`，缺少确切 Decision、Roadmap、Product Plan 或 Knowledge snapshot 版本/哈希的 Ready 请求。
- 已批准/引用/交付的 Decision/Roadmap/Product Changelog 被原位覆盖，或 material Product Memory Impact 尚为 `IMPACT_PENDING / REVIEW_REQUIRED` 却请求受影响 action 继续的迁移。
- Evals Applicability 为 `REQUIRED`，但 Fulfillment 未到 `REVIEWED`、缺有效 Eval Pack/Ground Truth provenance/必要 Reviewer，或用旧 `DEFERRED` 单值掩盖 `BLOCKED_MISSING_INPUT` 的 Ready 请求。
- Connector 在未声明 mount point 的外部写入请求。
- Product Quality Reviewer、主 Agent 或临时 subagent 直接写 `problem_ready=true`、修改 Candidate 后沿用旧 Review，或用自然语言声称“已经 Ready”的请求。
- 缺项目配置/Host identity 的操作者或 Agent 被当作 Product Decision Owner，`NO_PM_INTERVIEW` 被用来跳过正式 Decision choice，或 Graph 内 Decision 被当作外置组织审批结论的请求。
- 使用 Agent 模拟 Gate 却未标 `ADVISORY_ONLY`，或在没有程序化重算的情况下请求正式 Handoff。

### 15.5 PM Prompt 前的 Interaction Policy 强制检查

PM prompt 不是由 Agent 自由发送的旁路。Orchestrator 每次准备发出 PM 产品访谈问题时，必须把 Run、当前 MVU、prompt 目的、`source_resolution_type` 和问题集合提交给 State Controller；Controller 读取当前 Run 的 exact `interaction_policy`：

- `ALLOW_PM_INTERVIEW`：按 §9.1.3.1 和 §9.4 的来源/打断规则允许或拒绝该 prompt；交互文案再由独立的 `GUIDED / STANDARD / COMPACT` style 决定。
- `NO_PM_INTERVIEW`：拒绝 PM 产品访谈 prompt，返回结构化 skip result；Agent 必须转 AI 自查、正确 Owner/用户来源、Evidence Request、继续 Synthesis 或合法等待/未就绪状态之一。

该检查是现有权限与状态控制的一条确定性规则，不是新的 Ready Gate。它不拦截正式 approval/authorization，也不允许跳过原有 Gate。Junior PM 可见的 `skipped-interview impact` 是从 Run State/Audit 渲染的简短状态视图，不是新业务 Artifact；它至少展示：本次未询问什么、保留了哪些 Unknown、对下一动作有什么影响、Agent 首选建议、当前 allowed actions 与 not allowed actions。Agent 不得在随后回合改写问题措辞再次尝试绕过。

### 15.6 轻量 Run Resume、Audit 与 Git 分工

**目标是准确继续工作，不是重放整段会话。**一期每个 Run 只需要两个最小机器记录：一个 current state snapshot，以及一条 append-only meaningful event stream。`state.yaml`、`events.jsonl` 只是便于讨论的例子；具体文件名和完整 Schema 留到实现时按真实消费者确定，不在架构阶段扩张成 Run Registry、数据库或事件平台。业务 Artifacts、PRD archived/released 文件仍按各自版本合同保存，不算第三份 Run 状态副本。

current state snapshot 只需让恢复过程回答：

- **正在做什么**：Run/事项、来源 Signal 和当前目标。
- **走到哪里**：current step、last completed step、next allowed step。
- **以什么为准**：当前有效 Decision/Plan/PRD/Eval/Review 等 exact refs 与 versions。
- **还缺什么**：未解决项、等待对象、pause/failure 原因和恢复条件。
- **已经对外做过什么**：Connector side effect、attempt/receipt 和 UNKNOWN/reconcile 状态，防止重复执行。
- **在哪里继续修改**：仅在并行文件工作实际需要时保存 branch/worktree identity；不为此建立重型 registry。

event stream 只追加**有审计价值、会影响恢复或责任判断**的变化：node enter/complete、formal Candidate 或 material checkpoint、Owner 决定/material disagreement、重要 Finding open/close、外部 side effect/receipt、pause/failure/stop，以及 sub-agent dispatch/result/failure。它不记录 hidden chain-of-thought、每次 tool call、没有状态变化的内部尝试、每次措辞编辑、autosave 或每份工作草稿 hash。Node Result 是被 Controller 消费的执行合同，可按需引用 Artifact 或形成上述 meaningful event；它不是每个 Run 的第三条永久流水。

三类记录不得互相复制：

| 机制 | 只回答什么 | 不替代什么 |
|---|---|---|
| Git | 文档内容如何变化、在哪个 branch/worktree、如何比较/合并/回滚 | 当前 Run 到哪一步、在等谁、外部动作是否已执行 |
| Run State | 现在到哪里、下一步是什么、哪些 exact refs 当前有效、等待什么 | 文档内容历史、关键状态为什么改变 |
| Audit Events | 哪个有意义的状态为何改变、由谁/什么规则触发、外部 receipt 是什么 | Product Decision/PRD 内容或完整 Git diff |

恢复顺序固定但保持轻量：

```text
读取 current state
→ 验证 exact refs / files / current versions 可解析
→ 检查新的 external result、文件变化和 branch/worktree 变化
→ 渲染一份简短 Resume Brief
→ 从 current step 继续
```

Resume Brief 面向人必须用完整直白句说明“正在处理什么、已经完成到哪里、在等什么、建议下一步是什么、哪些变化可能阻止直接继续”，不能只显示 machine enum。若 exact Decision/Plan/PRD、外部结果或工作分支发生 material 变化，Controller 不得盲目沿旧 `next` 继续，必须先调用既有 stale/Impact/conflict 处理；纯格式变化不得无故重跑全部节点。Machine enum 可以保持稳定，但 Agent 只提出语义状态和下一步建议，State Controller 才能原子追加 meaningful event、更新 snapshot 和宣布节点完成。

考虑过但拒绝的方案包括：只靠 Git 恢复，因为 Git 不知道等待与副作用；保存全量对话/工具调用，因为噪声大且可能泄漏 hidden reasoning；完整 event sourcing，因为一期没有跨服务重放消费者；为 branch/worktree 建独立 Registry，因为现有 Run State 加必要 identity 足够。本设计复用 Git preflight、Artifact Version、Audit Event 和 Sub-agent Policy，不新增业务 Node、Gate、Artifact、HITL、数据库、MCP、CLI、Service 或 daemon。

---

## 16. 知识快照、影响与 Rebase

### 16.1 共同合同

> **CONFIRMED SOURCE COVERAGE / DEFERRED INTERFACE**：未来 Knowledge Graph 的 Raw Data / Source Corpus 必须把**所有正式 Product Decision Record 及其演化**列为必要候选素材，而不只是 Released PRD。`STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` 的原始 Record、exact source refs，以及后续维持、复查、推翻和 `supersedes` 关系都要可被未来 KMG 消费：STOP/WAIT 保留证据、假设、拒绝理由和 restart/review condition，防止组织失忆；RESEARCH/EXPERIMENT 保留认知缺口、验证路径与结果；COMMIT 保留承诺和 scope；Decision evolution 则说明项目认知如何改变。不能先压缩成只有“最终结论”的摘要再冒充完整来源。

这只确认 **source coverage requirement**，不确认 Product Graph 的 submission Schema。Node 17 继续 `DEFERRED / PENDING_KNOWLEDGE_REQUIREMENTS`：未来应先定义 KMG 对 raw source corpus + derived/compressed knowledge 两层的真实消费、权限和治理需求，再反推 copy vs reference vs index、何时提交、自动化、采纳/发布、保留/去重/同步。Decision Ledger 仍是 BPG 的产品决定真源，不能与 canonical Knowledge store 合并或复制出第二真源；本节不新增 Node、Gate、Artifact 或 HITL。

### 16.2 当前冻结的最小合同

一期只冻结四项边界：

1. Better Product Graph 可以读取项目配置指定的 exact、versioned、只读 Knowledge Snapshot；快照缺失或陈旧时必须披露对当前判断的影响，不能编造 canonical knowledge。
2. Better Product Graph 可以在本地保存 Decision、Plan、PRD、Evidence 与原始材料的 exact refs；这些都是未来 Knowledge Graph 的 source corpus 候选，但不是已经提交或发布的共享知识。
3. Better Product Graph 永远不能直接发布 canonical knowledge；未来只允许向 Knowledge Maintenance Graph 提交候选素材或变更建议，是否采纳、压缩、冲突处理和发布由后者负责。
4. Knowledge Maintenance Graph 未接入时，Better Product Graph 仍以本地 snapshot 和 records 独立运行，并明确 `local-only / not team-published`；它不能把“未共享发布”误写成“没有产品决定”，也不能把本地记录伪装成 KMG receipt。

Snapshot 完整度的精确状态、raw copy/reference/index 方式、Proposal/Impact Schema、Connector 方法、Outbox/Inbox 目录、检查时机、rebase/ack、离线同步与跨团队权限均留在 Roadmap 的 Knowledge Requirements 工作中。等真实 KMG 消费者需求明确后，再创建独立版本设计并回写 BPG Connector 合同；V1.4 不把这些历史草案当作一期实现要求或 Ready Gate。

---

## 17. Handoff Contracts：Product Released Artifact Set、Incident Packet 与 Bug Fix Brief

**阅读卡——交接（`handoff.dispatch`）**

- **做什么**：Ready 后 exact self-contained Released PRD directory 直接成为本地交付单元；再按每个 Connector+Target policy 决定不发送、等待人工外部写权或自动写入研发/飞书，并记录真实 attempt/receipt。
- **为什么**：本地生成文件不等于外部已经收到；不同路线也需要不同重量的交接合同，不能用 PRD Ready 强套 Incident 或 Implementation Deviation。
- **AI 做什么**：准备和校验交接内容、解释缺项、调用获准 Connector，并在结果未知时停止盲重试。
- **人做什么**：只在 side-effect policy 没有预授权外部写入、或专业 Domain/Incident/Bug policy 明确要求时授权 exact action；不重新审批 PRD 语义。任何交接授权都不能外推为自动回滚、数据修复或对外沟通。
- **主要产物与完成**：Product 交付 exact Released PRD artifact set；实验 intent 复用同一 Plan/PRD/Ready/Released/Handoff，只在同一 PRD 中增加条件化实验内容；Incident/Bug 发送其确切 Packet/Brief 版本。BPG Ready/Released 只证明产品侧交付物成立；只有远端 receipt 或人工确认才能声明已发送/接收，外置组织审批仍有自己的状态。

供人阅读的 Handoff View 必须按 §13.2 从同一 Released PRD、Release/State/Audit refs 按需渲染；它不产生包内副本或新增 Handoff 业务 Artifact。`handoff` Profile 必须把 `GENERATED / READY_TO_DISPATCH / SENT / RECEIVED / RESULT_RETURNED` 以及独立外置组织审批状态分开，Renderer 不得根据“文件/导出已生成”“BPG Released”或“Connector 已发送”写成“下游已接收/组织已批准”。source 或依赖版本变化后，旧视图 stale 并重新渲染和校验。

### 17.1 每份 PRD 的本地交付单元

```text
artifacts/prds/released/
└── BPG-PRD-0042_消息中心优先级_v1.0_2026-08-20/
    ├── BPG-PRD-0042_消息中心优先级_v1.0_2026-08-20.md
    ├── BPG-PRD-0042_消息中心优先级_v1.0_内审意见.md
    ├── assets/                                              # 仅有引用附件时存在
    │   ├── message-flow.png
    │   ├── interaction-demo.mp4
    │   └── data-contract.xlsx
    └── exports/                                             # 按需派生；无导出时不建
        └── BPG-PRD-0042_消息中心优先级_v1.0_2026-08-20.docx
```

Ready 后不再复制 Product Plan、Decision、Evidence、Review 等十几个文件组成另一套物理 Handoff Package，也不创建独立 Handoff manifest。现有 Release/State/Audit records 直接保存 exact released directory、主 Markdown/assets hashes、同源内审意见 ref/hash、`source_draft_ref/hash`、上游 material refs、派生视图和每个 dispatch attempt/receipt。需要审计时按 exact refs 展开原记录；不把它们复制成第二份真相。

`READY_TO_DISPATCH` 只表示这个 exact Released PRD artifact set 已可供某个 Connector、Export Adapter 或人工流程消费，不表示“物理打包完成”、已发送、已导入或已接收。同一 release 发往多个目标时复用同一 canonical source；每个目标只生成独立 dispatch attempt/receipt，不复制 canonical 内容目录。Handoff 不读取 `current/latest` 猜版本；release 后被 invalidated/revoked 时原目录保留，状态、Impact、替代关系和后续 dispatch 通过 records 表达。

第一版不实现 `handoff.package.build`、旧多文件 package 目录、legacy event 或兼容回放；Product Plan/Decision/Evidence/Review refs 供外置汇总审批按 Release/State/Audit records 读取。外部审批的结论、会签和组织责任由其自身系统记录，Better Product Graph 不复制该审批流。Incident Verification Packet 与 Bug Fix Brief 仍保留各自轻量正式交接合同，本决定不把它们并入 PRD release。

### 17.2 `EXPERIMENT` Intent 的同一 Released PRD 交付

`EXPERIMENT` 不生成独立 Handoff Package、manifest 或目录。它使用 §17.1 相同的 self-contained Released PRD directory；主 Markdown 的条件化实验 section 和 Release/State/Audit refs 明确标示 key unknown、exposure、measurement、结束时间、kill/rollback、Guardrails、Owner 与 result-return binding。接收方只在这些 exact 边界内执行。

同一个 release 可以发送给多个目标，但仍复用同一 canonical Markdown+assets，只增加各目标 dispatch attempt/receipt。任何扩流、延期、改变成功/无结论标准、取消 Guardrail、扩大用户范围或把学习性 action 转为长期产品，都属于 material change：必须返回 Product Decision，并生成新的 Plan/PRD/release version；不能通过 Connector 参数或下游口头确认无痕改变。

### 17.3 Incident Verification Packet 与 Engineering Handoff

Incident 默认只有一份正式内容产物：线上问题核查包。内部合同类型是 `incident.verification.packet.v1`；某个 Incident 自身的内容版本使用 `v1 / v2 / v3` 递增，两种版本不能混为一谈。最小结构如下：

```yaml
artifact_type: incident.verification.packet.v1
packet_id: incident-001
version: 1
supersedes: null
raw_signal: {ref: ..., source: ..., source_time: ...}
observation:
  phenomenon: ...
  expected: ...
  actual: ...
  occurred_at: ...
  product_version: ...
  environment: ...
  reproduction: ... # 或 NOT_AVAILABLE
impact: {affected_users: ..., scope: ..., urgency: ...}
evidence_refs: [screenshot-or-log-or-monitoring-or-issue-ref]
recent_changes: [...]
attempted_actions: [...]
analysis: {facts: [...], inferences: [...], unknowns: [...]}
engineering_questions: [...]
ownership: {owner: ..., status: ..., handoff_target: ...}
existing_links: [decision-or-roadmap-or-incident-or-signal-or-run-ref]
engineering_result: null # 后续版本追加核查结果、根因、建议和证据
```

Engineering Incident Handoff 只发送一个确切 Packet 版本及 transport envelope，不拆出一组重复内容文件。业务层机械检查只验证三项：原始 Signal/证据未被改写；事实/推断/未知分离；`engineering_questions` 让接收方明确知道核查什么。通用传输边界另外检查版本/hash、接收方和权限，但不是专业 Reviewer 或 Ready Gate。

严重/持续伤害场景允许 v1 带 `NOT_AVAILABLE` 先交接；v2/v3 继续追加证据、补全字段和研发结论，任何版本都不得原位覆盖。`incident` Profile 只检查会影响核查行动的最小理解项，不得因为文风、章节顺序或非关键缺失触发语义长文 Review、延迟紧急交接。Connector 未接入时同一 Packet 用于人工交接，状态保持 `WAITING_ENGINEERING_FEEDBACK`；已发送、接收或回传必须有真实回执，不能由 Agent 推断。

### 17.4 Bug Fix Brief Engineering Handoff

`IMPLEMENTATION_DEVIATION` 使用 `bug.fix.brief.v1` 作为正式交接内容，不包装成 Product Plan/PRD。Handoff envelope 至少引用：当前 Bug Baseline Assessment、Agent Route Recommendation、Controller Route、必要 clarification/override record、Bug Fix Brief、适用的 Bug Eval Pack 或 `NOT_NEEDED` 理由、版本/hash、接收方/权限与回传合同。来自 Incident 的事实和证据继续引用 Incident Verification Packet 的确切版本，不复制为第二份真源。

dispatch 前只运行 §8.3.2 的五项业务轻量检查与通用版本/权限/审计检查；`bug_fix` Profile 只补充最小行动性 Document Experience Validator，不把 Brief 扩成 PRD 或重型长文。只有项目 Risk Policy 命中的安全、隐私、资金、不可逆数据/数据修复等专业风险才追加相应 Reviewer/Owner；不得为了沿用普通 PRD 流程而默认要求 Product/Engineering/Testability 三 Review、Evaluator–Optimizer、通用 Readability Review 或 PRD Ready Assertion。

### 17.5 必要时的分批交付

父 Plan Run 可以生成：

```yaml
batch_id: batch-2026-08-19-001
parent_plan_ref: plan-001@v3
why_not_independently_releasable: ...
coupling_risks: [...]
shared_rollback_and_stop_conditions: [...]
included_prds:
  - prd-001@v3
  - prd-003@v2
remaining_children:
  - prd_id: prd-002
    status: BLOCKED
```

Batch 不是默认聚合方式。只有存在被证据支持的共同发布约束时才允许创建；分批交付不会把未完成子 Run 伪装成已完成，也不能用 Batch 消除各 PRD 的独立边界和 Ready 状态。

### 17.6 统一回传接入与最早受影响点返工

下游人员或系统只需提交自然原文或已有协议的原生结果，不填写 BPG YAML、内部 route 或返工节点。研发 Graph、测试 Graph、飞书和人工回传都先进入唯一 `signal.ingest`；Connector 自动附加来源系统、external object/event ID、时间、raw payload、身份/权限，以及当前上下文中可得的 PRD/Decision/Incident/Bug/Experiment exact refs。缺少关联时先由 `signal.relate` 推断；只有仍无法确定且会实质改变绑定或处理时才做一次最小澄清。

```text
外部回传 → signal.ingest（保留原文/原生结果 + provenance）
                  │
                  ├── 纯投递、接收或生命周期状态
                  │       └── 更新绑定 dispatch / external status
                  │
                  ├── 已有合同的 typed result
                  │       └── 追加绑定 Incident / Bug / Experiment / Handoff /
                  │           future Test Result 记录
                  │               └── 若含新产品事实、冲突或挑战，派生关联 Product Signal
                  │
                  └── 普通反馈或新产品问题
                          └── prepare → relate? → classify → route.select
```

来源协议明确声明的 event kind 是可验证的传输层事实，Core 可以确定性识别“这是某个 dispatch receipt 或某份 Incident Result”；它不授权 Connector 把内容判断成 Bug、Incident、Discovery 或 Planning 问题。普通自然语言由 Agent 识别。纯状态和没有新产品事实的执行结果不创建 Product Signal、不启动新 Product Run，也不进入 `route.select`；typed result 包含新的产品事实、冲突或挑战时，Graph 才创建一条引用原 result 与 exact 上游合同的关联 Product Signal。Router 仍只有四个业务 destination，不增加“研发退回”或“测试失败”路线。

**影响判断不是“默认退 PRD”。**Agent 先把输入区分为新可核查证据、执行结果、个人意见/建议或重复信息，并给出专业判断：它是否影响既有结论、最早影响哪一层、依据和最强反方是什么、什么新证据会升级或翻转。轻量 materiality 至少回答：

1. 能否绑定 exact PRD / Decision / AC / result；
2. 是否包含新的可核查信息，而不只是偏好、重复或无来源建议；
3. 是否实质推翻显式 assumption、scope、product rule 或 AC。

不使用加权分数。Human View 必须从同一 Result/Impact 记录渲染完整句子，例如：“已记录，但现有证据不足以修改结论；若补充 X 将重新评估”“这是执行结果，只更新任务状态”“只需修订当前 PRD，不影响上游决定”“新证据可能推翻原规划/决定，建议 Owner 重决”“这是独立新问题，建议创建新产品事项”。机器可以保存稳定 enum，但不得只显示 code 让人猜。普通意见默认 record+link，不自动 reopen；Agent 也不能消极归档，必须说明首选专业建议和升级所需证据。

当存在 material 产品影响时，返回**最早被新证据实质影响、且当前仍有效的环节**：

| 新证据真正改变的层 | 处理位置 | 不允许的捷径 |
|---|---|---|
| Implementation Deviation | 研发核查/修复，引用 Bug Fix Brief/Incident Packet | 不改 PRD 来掩盖实现偏差 |
| PRD 遗漏/歧义，但 Decision、Plan、Slice 仍成立 | 生成新 archived PRD Candidate，定向 Review 后以新 release supersede | 不覆盖 Released PRD，不全链重跑 |
| Slice、范围、依赖或迭代安排 | `product.planning` 的相关 Refinement/Reconcile | 不在 PRD 文案里私改规划 |
| 原选择、投入时机或承诺被挑战 | `product.decision`，向 Owner 展示原决定、当时依据、新证据和 Agent 建议 | 不由下游或 Connector 直接改 Decision/Roadmap |
| 问题框架或关键假设被推翻 | `problem.learning.loop` | 不为保持向前而硬拼旧问题定义 |
| 值得做但不属于当前增量 | Roadmap 相应状态/重启条件 | 不偷带进当前 PRD |
| 与当前事项相对独立的新机会 | 新的关联 Product Signal；由现有 activation 规则决定是否新 Run | 不因“来自下游”自动启动完整 Run |

返回上游不是由普通意见自动触发。任何人和下游系统都可以提交反馈，但不能直接把 Decision/Plan/PRD/Roadmap 标为 invalid、reopened 或自行选择返工点。Agent 负责专业语义判断；State Controller 只按 versioned policy、exact refs 和已有权限执行状态动作。机械且边界清楚的 result update/local repair 可自动执行；只有 material 改变既有 Product Decision、承诺范围或 Roadmap 时，才需要当前有权 Owner 形成新决定。当前一期操作者按 ADR-044 视为 Owner，外置汇总审批仍在 BPG 之外；本节不新增内部审批 Gate。更加细化的领域 materiality policy 仍需真实回传样本验证，不能由 Connector 私有实现。

Audit Ledger 复用现有事件合同，至少能追溯 `EXTERNAL_INPUT_RECEIVED / LIFECYCLE_STATUS_UPDATED / TYPED_RESULT_BOUND / PRODUCT_SIGNAL_DERIVED / IMPACT_ASSESSED / STATE_CHANGE_APPLIED` 的 actor、exact source/result/artifact refs、判断与规则版本、建议、Owner 决定（若需要）和 Controller transition；事件只证明发生了什么，不替代 Result、Decision、Impact List 或 Product Signal 的业务语义。

所有已 Released PRD 都不可原位覆盖。material PRD 变化必须形成新 archived Candidate 和新的 superseding release，保留旧版本、change reason、触发它的下游输入/结果、Impact List、受影响范围和 downstream refs。未改变产品事实的发送状态、执行状态、重复信息或普通意见不使全部 Decision/Plan/PRD/Eval/Handoff stale，也不触发全链重跑。

Incident Feedback 必须追加为同一 Incident Verification Packet 的新版本，绑定上一版本、研发核查结论、实际影响、复现/根因状态、已采取动作、处理建议和证据。核查结果至少支持确认缺陷、无法复现、符合既有规则、历史决定已不适用和需要补信息，再按上表进入 Bug Fix、Product Decision、Discovery/Problem Learning、Incident Product Response 或 Close；研发回传本身不能无痕改变产品规则。

Bug Fix 结果必须绑定 Bug Fix Brief、Baseline Assessment、实际修改范围、AC/回归或 Bug Eval 结果和未解决风险。研发发现修复必须改变产品规则时必须拒绝当前 Brief 并返回 Product Decision/Discovery，不能自行扩大实现范围；验证通过只关闭该 Implementation Deviation，不等于旧产品规则永远正确。

带 `EXPERIMENT` intent 的执行结果以 typed result 进入统一 `signal.ingest`，先绑定 exact Decision/Released PRD/Run、Eval 版本、实际受众/流量、运行窗口、数据版本、Guardrail/kill 事件和已知干扰；再成为新 Evidence，并由适用 Reviewer 检查完整性与解释后返回 Product Decision。Connector 或执行方不能直接写 expand/`COMMIT`，也不能用一次结果无痕覆盖原 PRD/Decision。

---

## 18. Connector 挂载规则

| Connector | Mount Point | 作用 | 前置条件 |
|---|---|---|---|
| 所有入站 Connector（Issue Collector、飞书、Development/Test Graph、未来 Input Connector） | `signal.ingest` | 传输/解析原生协议，提交自然原文或 typed result，并自动附加 provenance | Connector identity/permission、raw payload、source system、external object/event ID、time、hash/幂等信息和可得 exact refs；外部提交者不填 BPG 内部 Schema，Connector 不作产品分类/路由 |
| Knowledge | `context.snapshot.load`（一期）；未来提交/影响接口待 Knowledge Requirements 反推 | 读取项目配置指定的 exact、versioned、只读 Knowledge Snapshot | BPG 不发布 canonical knowledge；raw/derived 提交、Impact、ack、离线同步与权限合同保持 deferred |
| External Audit | `review.external.request` | 请求 Claude 等 Agent 审计固定版本 | 返回结果经本地 Validator，不能写状态 |
| Feishu Project | `handoff.dispatch` | 创建或更新产品需求（包括实验 intent）、线上问题核查单或 Bug 修复单 | PRD 对应同一个 Ready；Incident/Bug Fix Brief 对应各自轻量检查；versioned side-effect policy 预授权或 exact 外部写入授权；profile、幂等/去重策略和回执 |
| Development/Test Graph | `handoff.dispatch` | 提交 Product Released artifact set（可含实验 intent）、Incident Verification Packet 或 Bug Fix Brief | PRD 对应同一个 Ready；Incident/Bug 分别对应三项/五项业务轻量检查；versioned side-effect policy 预授权或 exact 外部写入授权；通用版本/权限检查 |

Connector 不可用时：

- 任一入站 Connector 不可用时可降级为自然语言或显式 Skill 的手动输入，Core Intake 和后续 Product Run 仍可运行。
- 一期 External Audit 始终是 advisory；不可用时记录 `NOT_AVAILABLE`、原因和影响，不因其意见形成语义阻塞。Blocking profile 只属于未来无人值守治理。
- Feishu/Development Connector 不可用时保留 exact Released PRD artifact set；可手工传递或按需生成 DOCX 后人工导入，但没有远端 receipt/人工可验证证据时不得声称已发送、已导入或已接收。
- Knowledge Connector 未接入时使用项目本地 exact snapshot 并标记 `local-only / not team-published`；snapshot 缺失、陈旧或与当前行动明显冲突时，按现有 Evidence/Unknown/Decision 规则披露影响或返回补证，不能假装已完成 KMG Impact 检查。严重或持续伤害的 Incident Verification Packet 仍按轻量政策优先交接。

所有入站 Connector 都只拥有在 `signal.ingest` 传输原文/原生结果、解析协议和附加 provenance 的权限，不能直接创建 Decision/Plan/PRD Run、声明产品语义、选择路线或使上游产物失效。协议 event kind 只用于中央 Intake 的确定性快分流；产品判断仍由 Core 单一策略完成。采集型 Signal 默认 activation intent=`INBOX_ONLY`；高危提醒/升级由 `signal.classify → route.select` 根据项目 policy 决定。typed result 和生命周期状态按 §17.6 先更新绑定记录，只有新的产品事实才派生 Product Signal。用户临时粘贴 URL 即使触发一次授权读取，也仍属于手动 Signal，不获得 Connector 的周期拉取、游标、来源身份或对账语义。

有副作用的 Connector 必须解析 versioned side-effect policy。Policy 至少将 connector、target/project、action、artifact type/version/hash、授权 identity/capability、有效期、幂等与 receipt 要求绑定在一起；Product dispatch 的默认/自动规则见 §18.1。该授权只允许相应外部写动作，不提高 PRD 的语义置信度，不替代 Domain Owner，也不代表组织外置汇总审批通过。Connector 未安装或不可用时，本地 Released artifact set 仍然完整，状态不得伪装成 `SENT`。

### 18.1 `handoff.dispatch / 产品交付发送`

`handoff.dispatch` 是现有 `handoff.dispatch` mount 上的**可选、可恢复 Connector boundary attempt**，不是 Product Loop 本地完成的必经节点。无 Connector、Connector=`disabled` 或权限不可用时，exact Released PRD+assets 仍是完整本地交付物，可人工传递或使用 §18.2 的 DOCX fallback；外部能力不得撤销或阻止 `READY / RELEASED`。

Dispatch 不打包、不重新生成或改写 PRD、不做语义 Review，也不重复 Owner 内容审批。它只消费 exact self-contained Released artifact set，经目标 Adapter 执行必要的渲染/写入，并把 attempt、远端结果和 receipt 追加到现有 State/Audit records。Development/Test Graph Connector 同样不能回写 canonical Product artifact。

每个 `connector + target` 配置一个 versioned dispatch policy：

| Policy | 直白含义 | 行为 |
|---|---|---|
| `disabled` | 不向这个目标发送 | 保留本地 release；不创建外部副作用 |
| `manual` | 可以发送，但每次需明确外部写入授权 | 首次或未配置时默认；自然语言“把这个需求提到飞书”可触发 exact manual attempt |
| `auto_when_ready` | 本地 Ready 后可自动发送 | 仅当项目级 versioned preauthorization 明确覆盖 exact connector、target、action、artifact type/scope、identity 和有效期时成立 |

人工授权或预授权只赋予外部写入权限，不提高内容置信度、不代表外置组织审批，也不恢复固定 PRD Owner 内容确认。公开 `$better-product-graph handoff [run_id]` 仍只准备/校验/展示 Handoff；本决定不新增 command/alias，真实 dispatch 由明确自然语言意图或有效 policy 触发。

每个 attempt 的幂等 identity 至少稳定绑定 `PRD ID + Released Version + Connector + Target + Action`。调用前先记录 pending attempt；明确成功时必须保存远端 ID/URL/revision/receipt 或人工可验证的等价证据。超时、连接断开或响应不确定时状态为 `UNKNOWN`，必须先 query/reconcile 远端状态，再决定是否重试；无法查询时保持等待，禁止盲重试制造重复飞书文档或项目单。具体 API 幂等能力须在 Connector 原型阶段验证，通用 Graph 不假设飞书一定支持客户端幂等键。

人类视图必须用直白句子区分：

- 本地 PRD 已完成，尚未请求发送；
- 已可发送，但缺 Connector 或外部写权限；
- 正在发送；
- 远端已确认创建或更新；
- 结果未知，等待查询且暂不重试；
- 发送失败，但本地 PRD 仍有效；
- 已发送，但接收、采用和外置组织审批仍是独立状态。

`SENT` 只由远端 receipt/ID/URL/revision 或人工可验证等价证据支持，不得外推为 `RECEIVED / ACCEPTED / APPROVED`。同一 release 向多个目标发送时复用同一 canonical source，每个目标分别保存 attempt/receipt；一个目标失败或 UNKNOWN 不影响其他目标和本地 Ready。source 后续被 invalidated/superseded 时，原 attempt/receipt 不删除；任何外部状态/结果回传统一由 `signal.ingest` 接收，并按 §17.6 更新绑定记录、派生 Product Signal 和计算 Impact，Dispatch 自身不选择返工点。

### 18.2 飞书原生文档与派生导出的验证边界

当前不把“直接写入飞书原生 Doc”设为默认交付路径，状态明确为 `PROTOTYPE_REQUIRED / PENDING_PERMISSION_VALIDATION`。必须在真实目标租户验证：

- 文档创建、更新和 revision/receipt 能力；
- 图片、视频、表格等素材上传和相对引用转换；
- 文档、空间、项目的身份/权限和可撤销授权；
- 与飞书项目需求单的关联能力；
- 复杂 Markdown、表格、附件和媒体降级后的可读性与语义保真。

现实 fallback 是从 exact released Markdown+assets 按需派生同 stem DOCX，由人手工导入飞书。DOCX 不是 canonical truth，生成 DOCX 只说明 `EXPORT_GENERATED`；除非用户或远端返回可验证链接、ID、revision 或等价确认，否则不能标为 `SENT / IMPORTED / RECEIVED`。后续 Feishu Connector 与 Export Adapter 都必须从同一 canonical source 派生，不能反向改写 Released PRD；当前只记录合同和验证点，不实现 Connector、Exporter 或新的 Handoff packager。

---

## 19. Reviewer、Validator、Gate 与 Ready

**阅读卡——就绪判断（`problem.ready.gate / plan.ready.gate / prd.ready.gate`）**

- **做什么**：针对确切产物版本检查审查记录、结构规则、Evals、引用、模板和版本前提是否完整；PRD Ready 不要求固定的人类内容确认。
- **为什么**：Agent 生成一份格式正确的文档，不等于它绑定了正确上游、当前 Eval 或 release 记录；但 Reviewer concern 也不应被误读成 BPG 批准/阻塞权。
- **AI 做什么**：Reviewer 提交 advisory Finding、证据和建议，不能自行写正式状态或宣布批准/阻塞。
- **人做什么**：material 产品判断返回唯一 `product.decision`；外部副作用按 Connector policy 条件授权。State Controller 是唯一正式状态写入者。
- **主要产物与完成**：`review.finalize` 收尾审查完整性，`PRD Ready` 检查本地 release 机械合同；两者都不表示研发实现、测试通过、外置审批或可以上线。

### 19.1 权责关系

```text
Reviewer：提交 advisory Finding、证据和专业建议
Validator：检查结构和确定规则
Owner：只在 product.decision 对 material 产品取舍负责
外置团队：在 Graph 外承担最终专业/组织审核
State Controller：在写状态时重算 Validator/finalize/Ready 并执行迁移
```

Reviewer 主观意见不会成为当前 BPG Gate。关注等级只帮助修订和外置团队聚焦；未解决项必须在同源内审意见披露，但不能因此阻止本地 Ready/Released。正式 Reviewer blocking、Domain Owner、Waiver 与 action-scoped governance 只保留为未来无人值守阶段的 Roadmap seam。

Document Experience 不增加一类 Gate。共享 Validator 与按需 Readability Reviewer 把结果提交给现有 Problem/PRD/Handoff 边界；实验 intent 仍由 PRD Ready 消费。State Controller 重新解析 exact source、policy/profile/template binding 并重算确定性结果。Readability finding 只是 advisory；只有 Validator 独立命中既定最低合同缺口时，相应 Ready 才因该机械缺口失败。

### 19.2 PRD Ready 条件

`prd.ready.gate / PRD 最终就绪检查` 是 State Controller 的最终确定性 validation/transition boundary。它在 `review.finalize` 完成后立即执行，不是 Agent/Subagent、人工审批，也不是需要另外等待/恢复的独立智能 Graph Node。Finalize 只保证审查 attempts/dispositions/companion view 完整；Ready 只确认即将成为 self-contained release/Handoff 单元的 exact PRD Candidate 及引用是否机械有效，不重新做语义 Review。

一期只检查六类必要前提：

1. **current exact Candidate**：当前对象是 `archived/` 中不可变、materially valid 的 exact Candidate/version/hash，不是 scratch、`current/latest` 推测或尚未生成的 release。
2. **同版本 Review 与收尾**：适用 Review attempts、Aggregate 和 `review.finalize` 都完成、有效且绑定该 Candidate；每条 Finding 有 disposition，同源内审意见 view/ref/hash 与主 PRD 一致。旧版结果不可复用。
3. **Reviewer 与机械合同分离**：advisory concern 即使未解决也只需披露，不阻塞本地 release/Handoff；若 concern 指向必需字段、exact ref 或模板映射缺失，必须由对应 Validator 独立复现该既定机械缺口后才使 Ready 失败。
4. **关键上游 exact refs 可解析且 current/non-stale**：Decision、Product Plan、activated Slice、Knowledge/Evidence 及适用的 Roadmap/Planning/Guardrail/Shared Contract refs 与 Candidate 语义一致；material Product Memory Impact 已有合法 disposition。
5. **Evals 按 Applicability 履行**：`NOT_NEEDED` 有可审计理由时不受影响，`RECOMMENDED` 默认不硬阻塞但披露影响；`REQUIRED` 时 exact Eval Pack 与必需 Review/Ground Truth provenance 必须达到当前 policy 要求并绑定同一 stable content version，`BLOCKED_MISSING_INPUT` 或 stale Pack 不能 Ready。
6. **呈现与版本机械合法**：Template Profile/mapping/Supplement、Document Experience validation、Artifact version record/hash、`DOCUMENT_CHANGELOG.md`、Audit 与 Ready Policy 检查通过；必要语义无法承载时不得静默丢失。适用项可使用 `N/A + 理由 + policy/profile 依据`，字段填满率不是 Gate。

本 Gate **不检查或要求** PRD-stage Owner 再确认、组织外置汇总审批、Connector 可用性/外部写入授权、研发或测试已完成、所有 advisory 建议关闭，或任何百分比/加权分数。按需一页最终摘要如已渲染则必须绑定同一 source，但用户是否打开/阅读不是 Gate 条件。

机器结果保持 `READY | NOT_READY`。`NOT_READY` 必须列出 exact unmet condition、受影响 artifact/ref/version/finding、deterministic repair target 和 resume point，不得只输出“请完善 PRD”。同一 exact inputs/hash + rules/policy version 必须得到同一结果。

`READY` 后，State Controller 无需 Owner 二次确认，自动执行 §12.4.4 的 release promotion：从 exact archived Candidate 生成 immutable self-contained Released PRD directory，追加 Document Changelog/Release/State/Audit 与 current 导航记录。该 exact artifact set 直接成为本地交付单元，不再构建独立 Handoff Package。若 Candidate/hash、关键 refs、Review/route、Eval、Template/Document Experience 或 version record 变化，旧计算失效并重算。随后是否 dispatch 只按 §18.1 的目标 policy/预授权决定；无 Connector 或未授权不阻止本地 `READY/RELEASED`。BPG Ready/Released 不等于组织外置审批、研发实现或测试通过。

### 19.3 `EXPERIMENT` Intent 的 PRD Ready 附加检查

本节不是 `Experiment Ready`、第二个 Gate 或另一类 Assertion；它只是 §19.2 `prd.ready.gate` 在当前 PRD 的 delivery intent 为 `EXPERIMENT` 时执行的条件化检查：

1. Product Decision 明确为 `EXPERIMENT`，授权与 epistemic confidence/evidence gaps 分开，并绑定 exact Decision、Plan/PRD 与 Knowledge refs。
2. 同一 PRD 已写清 key unknown/hypothesis、目标人群/暴露上限、具体变化、observable measurement、continue/adjust/stop mapping、监控、kill/rollback、Owner、结束时间和伤害 Guardrails。
3. 风险等级、未知与 concern 已如实披露；R2/R3 等高关注 action 进入内审意见和外置团队审核，不由 BPG AI Reviewer 自行放行或否决。
4. Evals Applicability/Fulfillment 与本次测量相符，数据来源、Ground Truth/解释限制和已知干扰已披露；不能用普通 AC 假装完成真实行为验证。
5. applicable Review 对同一 Candidate 检查了忠实性、可观测、可停止/回滚、scope/exposure 与风险，Finding 已有 disposition 并在需要时披露；Reviewer concern 本身不是 Ready block。

满足这些条件后仍只生成普通 PRD Ready Assertion 和同一个 self-contained Released PRD directory。范围、流量、时长、指标、Guardrail、风险或长期承诺发生 material change 时，旧 PRD Ready/release 按既有 Impact/version 规则失效或需要复审；不得创建 Experiment Ready 来旁路。

### 19.4 Ready Assertion 绑定

- 普通 PRD profile：`archived/` exact review candidate、可选 PRD Content Checkpoint、Supplement、确切 `decision_refs`、`roadmap_snapshot_ref`、`product_plan_ref`、`knowledge_snapshot_ref`、Target Operating Outcome、`planning_views_ref`、Slice、适用 Batch 和 Eval Pack 的版本及哈希；Ready PASS 后的 release record 再引用该 Assertion 与 candidate hash，不原位修改 Assertion。
- 当 `delivery_intent=EXPERIMENT` 时，同一 PRD Ready binding 额外包含确切 Decision/Knowledge refs、key unknown/hypothesis、受众/暴露、具体变化、测量/解释边界、风险/授权、监控/停止/回滚和 typed-result return binding；不生成另一份 Experiment Ready Assertion。
- Graph Manifest、Skill、Schema、Validator 和 Gate policy 版本。
- 知识快照、Document Experience Policy、artifact Profile 和项目模板的 exact versions；适用 human view 的 source hash、rendered_at 和 Validation Result。
- authorization、epistemic status、risk classification、advisory Finding/disposition、同源内审意见，以及实际发生的 Connector side-effect authorization records；PRD 内容审批不得成为当前 Ready 隐性前置。
- Audit Ledger head hash 与 enforcement mode。

---

## 20. Audit Ledger、回放与版本管理

### 20.1 Audit Event

Audit Ledger 是 §10.6 四类记忆中的执行事实层，只回答谁在何时对哪个确切版本执行了什么。它必须引用 Decision/Roadmap/Product Changelog artifact，却不能用 `approved`、`updated` 等事件名代替这些产物的产品语义。

V1.4 的当前合同是**轻量、有意义事件流**：current state snapshot 是恢复当前状态的唯一真源；Audit 只追加会改变恢复、责任、正式版本、Review disposition、外部副作用或失败判断的事件，并解释重要状态为何改变。它不记录每次工具调用、每次无状态 attempt、每个措辞草稿、每项 Validator 细节或隐藏 Chain-of-Thought，也不承诺用事件完整重建所有中间 state。事件足够时可以校验迁移历史并辅助修复损坏 snapshot，但不能成为第二状态真源。

最低事件类别只有：节点/路线的重要迁移；material artifact checkpoint、release 与 supersedes；Owner Decision 与 material disagreement；Review attempt/finding disposition/finalize；等待、暂停、失败和恢复；Connector side effect/receipt；以及实际使用的 sub-agent dispatch/result/failure。每条只保存 exact refs、actor/rule、结构化理由、前后状态和必要 receipt；具体 event name 与完整 Schema 留到实现时按真实恢复消费者冻结。

<details>
<summary>V1.2 事件名设计清单（已退为非规范设计历史，不属于一期实现要求）</summary>

以下清单只记录此前考虑过的事件语义，不能覆盖上面的轻量合同，也不能被实现者解释为“每个 attempt 都必须记录全部字段”。

每个 signal-scoped Intake 或 Run attempt 曾考虑记录：

- Run、节点、attempt、Host 和会话标识。
- Graph、Skill、Schema、Validator 和 policy 版本。
- 输入、知识快照、输出和哈希。
- 工具、Connector、权限和 approval。
- Reviewer attempts、advisory Findings、concern level、Finding disposition、分歧和同源内审意见引用；未来 autonomy policy/waiver 不写入一期 current-state 路由。
- Validator/Gate 逐项结果。
- 状态迁移、重试、错误和外部回执。

分类与路由至少使用 `CLASSIFICATION_CREATED / ROUTE_RECOMMENDED / ROUTE_ASSOCIATIONS_RECORDED / ROUTE_CLARIFICATION_REQUESTED / ROUTE_CLARIFICATION_ANSWERED / ROUTE_SELECTED / ROUTE_OVERRIDDEN / ROUTE_REROUTED / ROUTE_SUPERSEDED` 事件，并引用对应 Record 版本/hash。事件和 Record 只保存结构化理由、证据、未知、政策命中和授权，不请求、保存或通过 `audit.view` 暴露模型隐藏 chain-of-thought。

Discovery Evidence 路径至少使用 `LEARNING_ROUND_STARTED / EVIDENCE_REFERENCE_CAPTURED / PROBLEM_EVIDENCE_MAP_CREATED / MVU_UPDATED / EVIDENCE_REQUESTED / LEARNING_STATUS_CHANGED / LEARNING_WAITING_FOR_EVIDENCE / LEARNING_RESUMED / LEARNING_ROUND_COMPLETED / LEARNING_COMPLETION_DISPOSITION_RECORDED / LEARNING_NEXT_ACTION_RECOMMENDED / KNOWLEDGE_PROPOSAL_SUBMITTED`（按实际发生使用）。事件必须引用 Learning Round/State、Evidence Reference、`problem.evidence.map.v1`、Evidence Request、Knowledge Snapshot 与 Proposal 的确切版本/hash，并记录查询范围、权限与敏感性。Status event 保存 before/after 与原因；completion event 只有在 status=`COMPLETED` 时才保存三类 disposition；recommendation event 明确 `ADVISORY_ONLY`、action scope、剩余 Unknown、风险/可逆/可测/回滚和所需 Owner/授权。Round completion 还引用新增证据、假设支持/削弱/推翻、frame/Agent recommendation/MVU 变化、action-relative sufficiency 及继续/停止理由；它证明何时发生采集、映射、等待、恢复和选择，不用事件名代替 Map 内的 claim-evidence 关系，也不记录隐藏 chain-of-thought。

Learning attempt 还应在现有 Audit Event/State 中记录 `LEARNING_SOURCE_RESOLUTION_SELECTED / PM_INTERRUPT_REQUESTED / HUMAN_RESPONSE_RECORDED / LEARNING_CHALLENGE_RECORDED / SOURCE_RESOLUTION_SUPERSEDED`（按实际发生使用），并引用当前 MVU、七类 `source_resolution_type`、选择依据、证据、是否打断、interrupt reason、一个核心问题与必要澄清、PM claim type、`LIGHT / STANDARD / STRONG` 挑战及选择依据、Agent 首选建议与最强反方、agreement/disagreement、authority、假设/frame 变化和 next action/stop reason。事件不能把 PM context/claim、judgment 或 authorization 改写为 user fact，也不能用 Sponsor 授权覆盖冲突证据；`audit.view` 只按权限呈现这些结构化依据及必要原句，不能重建或补写隐藏思维链。默认不永久保存全量逐字对话；这些事件只是现有 Learning Loop 的审计语义，不创建新持久节点或独立 Artifact。

Run interaction policy 变化必须追加 `INTERACTION_POLICY_CHANGED`，记录 actor、Run、`scope=CURRENT_RUN`、时间、变更前后值、入口来源（`new/resume` modifier、`interview skip|resume` 或自然语言等价）、恢复点和当时 current MVU（如已有）。`NO_PM_INTERVIEW` 实际跳过 prompt 时追加 `PM_INTERVIEW_SKIPPED_BY_POLICY`（或同等稳定事件），引用同一 policy change、当前 MVU、已回答内容 refs、当前未回答及后续 skipped questions、替代来源路由、保留 Unknown、skipped-interview impact、Agent 建议，以及对 allowed/not-allowed actions 的影响。Resume 只更新 policy 和恢复点，不伪造或重放旧回答。两类事件合起来必须可回放 actor/run/scope/time/MVU/skipped questions/alternative source/unknown/allowed-action effect。正式 approval/authorization 仍单独记录，不能因 policy 名称而被误记为“访谈已跳过”。

问题假设审视至少追加 `ASSUMPTION_AUDIT_CHECKPOINT_CREATED / ASSUMPTION_AUDIT_RERUN / ASSUMPTION_AUDIT_RECOMMENDATION_SELECTED`，引用 Raw Signal、Route Record、Knowledge Snapshot、Problem Evidence Map、checkpoint 与 supersedes 的确切版本/hash。事件引用 checkpoint 中的原话/事实角色、现象/影响/问题假设/期望结果/提出方案、动态关键假设、反证/替代/历史/no-action/症状原因检查、exactly one MVU、推荐信息来源、下一信息请求、三类下一建议及结构化理由，不保存 hidden Chain-of-Thought；route re-evaluation recommendation 不能冒充实际 `ROUTE_REROUTED`。

问题综合按实际发生追加 `PROBLEM_SYNTHESIS_STARTED / PROBLEM_DEFINITION_CANDIDATE_CREATED / PROBLEM_SYNTHESIS_RETURNED_TO_LEARNING / PROBLEM_DEFINITION_CANDIDATE_STALE / PROBLEM_DEFINITION_CANDIDATE_SUPERSEDED`，绑定全部 exact input refs/hashes、node/Skill/model/policy versions、Candidate version/hash、Result 和结构化原因。`RETURN_TO_LEARNING` 记录 material gap 与 exactly one 新 MVU，但只有后续 Learning State/Round Event 才能证明学习已真正恢复；事件不得补写 Evidence 或隐藏思维链。Candidate 创建或 `COMPLETED` 事件只证明稳定可审候选已形成，不能冒充 Quality Review、PM Confirmation 或 Problem Ready 已通过。

Problem Ready 至少形成 `PROBLEM_QUALITY_REVIEW_STARTED / PROBLEM_QUALITY_REVIEW_COMPLETED / PROBLEM_REVIEW_NO_PROGRESS / PROBLEM_READY_CALCULATED / PROBLEM_READY_TRANSITION_REJECTED / PROBLEM_READY_TRANSITION_COMMITTED`（按实际发生使用）。Review 事件绑定独立 attempt、隔离上下文声明、专门 Skill/model version、exact frozen Candidate 及 Evidence/Learning/Knowledge/Product Memory refs、full/delta mode、全局不变量回归、advisory Finding/repair path 与 disposition。Ready calculation 只绑定 current exact Candidate、同版本 Quality Review disposition、Evidence/Learning/Synthesis refs 和 rules version；`NOT_READY` 追加 exact mechanical unmet condition 与 deterministic repair target，`READY` 自动提交进入 Product Decision 的迁移。新 Run 不产生 `PM_ACKNOWLEDGED / OWNER_CONFIRMED / OWNER_CONFIRMATION_INVALIDATED` Problem 事件；Owner 责任由紧邻的 Product Decision choice 承担。Agent 模拟只能追加 `ADVISORY_ONLY`，不得生成正式 transition；一期不产生评分、第二次确认、action-scoped matrix、低风险 `NOT_REQUIRED` 或 Junior PM escalation event。

`product.decision` 按实际发生记录 `PRODUCT_DECISION_STARTED / DECISION_DRAFT_CHECKPOINT_SAVED / DECISION_REVIEW_DISPATCHED / DECISION_OWNER_CHOICE_RECORDED / DECISION_DISAGREEMENT_CHALLENGED / DECISION_RECORD_CONFIRMED / DECISION_TRANSITION_REJECTED / DECISION_ROUTE_COMMITTED` 等价事件。Draft checkpoint 事件绑定 exact inputs、AI Brief、Review refs、分歧、Owner discussion state、版本/hash 与 supersedes；它不能产生正式 outcome/route。material disagreement 的 challenge 事件只记录一次 bounded 实质挑战的 evidence gap、risk、Agent preference reason、Owner response 与仍有效 constraint，不保存 hidden CoT，也不能用重复事件无限争论。Record-confirmed 事件还绑定 Owner 五项确认、条件化 disagreement/双方理由/authorization/accepted uncertainty-risk/recheck-stop、chosen-outcome-only details、适用 action-risk classification、系统自动 refs/identity/version 与 final hash。Controller transition validation 失败时，reject 事件保存 exact unmet condition/repair target 并保持当前 Decision state；通过后才追加 route committed。两者是既有 Controller/Audit 语义，不产生 Decision Ready Artifact/Gate。后续改判必须新 Record + supersedes，不能修改旧事件/Record。内部风险、比较、挑战和确认动作保留在同一 Node attempt/事件链中，不借事件名重新注册五个 Graph Nodes。

Product Planning 可按实际发生记录 `PRODUCT_PLAN_V0_CREATED / PLANNING_PROFILE_SELECTED / PLANNING_PROFILE_CHANGED / PLANNING_ROUND_STARTED / PLANNING_ROUND_COMPLETED / PLANNING_WAVE_SELECTED / PLANNING_WAVE_ADVANCED / PLAN_BLOCK_DEEPENING_STARTED / PLAN_FINDING_OR_PROPOSAL_RECORDED / PLAN_SLICE_STARTED / PRD_SLICE_CANDIDATES_CREATED / PLAN_COVERAGE_VALIDATED / PLAN_RECONCILIATION_STARTED / PLAN_RECONCILIATION_COMPLETED / PLAN_REPAIR_ROUTED / PRODUCT_PLAN_CHECKPOINT_CREATED / PRODUCT_PLAN_SUPERSEDED / PLAN_REFINEMENT_STOPPED` 等价事件。这些都是已确认 `product.planning` 内部 Loop/动作的审计语义，不把 Profile、Round、Wave、Slice、Coverage 或 Reconcile 重新注册成顶层 Graph Node。每个事件绑定 exact Plan snapshot/hash、Planning Profile、适用 Wave/Round、目标 block、候选 slice/coverage disposition、Findings/Proposals、处置/materiality/Owner、保留分歧、全局影响、change summary、`supersedes` 和 downstream impact refs；LIGHT 内联时可合并 attempt 但不能丢 exact bindings。sub-agent 事件仍复用下段通用合同。事件名不能代替 Product Plan 内容，也不能让多个 writer 并发更新正式 Plan。

Plan Ready 按实际发生追加 `PLAN_REVIEW_FINALIZED / PLAN_READY_CALCULATED / PLAN_READY_TRANSITION_REJECTED / PLAN_READY_TRANSITION_COMMITTED / PRD_RUN_CREATED` 等价事件。Gate Calculation 绑定 current exact Plan、Coverage/dispositions、advisory Review finalize、依赖/冲突处置、所有 material Decision refs 和 rules version；按需一页 Plan 摘要是同源 Human View，不产生 confirmation event。若 Planning 出现超出 exact Decision 的 material 产品取舍，`PLAN_REPAIR_ROUTED` 返回 `product.decision`，新 Decision 后再继续。`PRD_RUN_CREATED` 必须逐项引用 activated+eligible slice 与 delivery intent；未来或等待 disposition 不得借同一 Ready 事件创建 Run，`EXPERIMENT` 也不得创建第二种 Run 类型。这是既有 Controller/Audit 行为，不新增人工审批 Node或第二 Gate。

PRD Run 可在进入 `prd.generate` 前追加一次等价 `PRD_WORKSPACE_INITIALIZED` 生命周期事件；正式内部调用名是 `prd.workspace.initialize`。事件只证明 workspace、exact parent refs、state/version 和目录/恢复位置已准备，不证明 PRD 已生成、被理解、审查或 Ready；其余初始化字段仍待 PRD Run Review。`prd.generate` 按实际发生追加 `PRD_GENERATION_STARTED / TEMPLATE_PROFILE_RESOLVED / PRD_GENERATION_CHECKPOINT_SAVED / PRD_CANDIDATE_ARCHIVED` 等价事件，绑定 exact inputs、Profile/template/mapping、内部动作版本、可选 checkpoint、candidate path/version/hash 与恢复点；内部三个动作不能借事件名注册为三个节点。第一版尚无已发布运行消费者，因此不实现旧名 alias、迁移 parser 或兼容事件。

PRD Review/Release 按实际发生追加 `PRD_FIDELITY_CHECKED / PRD_REVIEW_DISPATCHED / PRD_REVIEW_CROSS_CHECKED / PRD_REVIEW_OF_REVIEW_COMPLETED / PRD_OPTIMIZE_STARTED / PRD_OPTIMIZED_CANDIDATE_ARCHIVED / PRD_OPTIMIZE_NO_PROGRESS / PRD_REPAIR_VERIFIED / PRD_REVIEW_COMPLETED / PRD_REVIEW_FINALIZED / INTERNAL_REVIEW_VIEW_RENDERED / PRD_FINAL_SUMMARY_RENDERED / PRD_READY_CALCULATED / PRD_RELEASED / HANDOFF_READY_TO_DISPATCH / HANDOFF_DISPATCH_AUTHORIZED / HANDOFF_DISPATCH_STARTED / HANDOFF_DISPATCH_UNKNOWN / HANDOFF_DISPATCH_RECONCILED / HANDOFF_DISPATCH_FAILED / HANDOFF_DISPATCHED` 等价事件。Fidelity/dispatch 事件绑定 current Candidate、自动提取的 Goal Fidelity Review Packet、Decision/Plan/Slice/Knowledge/Evidence/constraint exact refs、deterministic results、Reviewer role/profile/attempt、首轮隔离、Findings/cross-check/disagreement、限定 self-review rounds、repair status/delta/target 与 global-invariant regression；Optimize 事件只在一轮批量修订真正开始/形成新送审 Candidate/no-progress 时追加，绑定 loop/round/budget、source+new Candidate、Aggregate/Findings、claimed repair/delta 和 re-review scope；无内容变化的 Review Attempt 不伪造 optimized Candidate 事件。`PRD_REVIEW_FINALIZED` 只证明 applicable attempts、Finding dispositions、exact Candidate 和同源内审意见视图完整一致；它不是 Gate、批准或 Ready。`PRD_READY_CALCULATED` 绑定六类 exact 检查、rules/policy version 和 `READY | NOT_READY`；`NOT_READY` 必须含 unmet/affected ref/repair/resume，`READY` 与 self-contained release promotion 连续原子记录。未触发 review-of-review 时不制造占位事件。最终摘要事件只引用同一 source/Review/Audit，不证明用户阅读或批准。Ready/Released 事件是 Controller 生命周期事实，不能被写成组织外置汇总审批通过；dispatch attempt 必须绑定 policy version、idempotency identity、exact Connector/target/action/artifact refs+hashes、actor/preauthorization、result/remote receipt 和必要 reconcile refs，并与 semantic approval 分离。第一版不实现从未发布过的旧 Package/approval 事件迁移。

当前尚无已发布运行版本，因此第一版不建设旧 Owner approval event 的兼容回放。若项目 side-effect policy 需要一次人工授权，只记录新的 exact Connector authorization，不创建或复用内容审批事件。

Evals 按实际发生追加 `EVAL_APPLICABILITY_DECIDED / EVAL_FULFILLMENT_CHANGED / EVALS_BUILD_STARTED / EVAL_SCOPE_DEFINED / EVAL_GENERATION_DISPATCHED / EVAL_REVIEWED / EVAL_PACK_STALE / EVAL_PACK_JOINED` 等价事件，分别绑定 exact PRD/Plan/Eval Policy/content refs、Applicability、人类结论/理由、Fulfillment、missing inputs/owner、scope、Pack/Review refs、sub-agent attempt、Impact/stale reason 与 join hash。旧 `NOT_REQUIRED / DEFERRED` 事件原样保留并追加 migration record；不得重写成仿佛历史上已经使用双维合同。Applicability decision 属于 `prd.generate` 内部动作，`evals.build` 是 PRD Run 内按需可恢复子节点；scope/generate/review 事件都不能借事件名注册成用户可见顶层节点。生成 sub-agent 只交候选，不能自报 Ground Truth、`REVIEWED` 或 PRD Ready。

任何横向 sub-agent attempt 至少记录 `SUBAGENT_DISPATCHED / SUBAGENT_COMPLETED / SUBAGENT_FAILED / SUBAGENT_TIMED_OUT / SUBAGENT_RESULT_JOINED` 的等价事件，并保存 parent Run/attempt、subtask role、requested model profile、实际 provider/model/version、exact input refs/hashes、Skill/policy versions、permission profile、开始/结束、result hash/status、timeout/retry 和可得 cost。Host 不支持时记录 `NOT_AVAILABLE / DEGRADED_TO_SEQUENTIAL`，不能伪造并发。Join event 必须引用所有 required/optional 结果、未满足 action 和未消解分歧；多个 Agent 同意不产生新的 Evidence confidence，Audit 不保存 hidden Chain-of-Thought。

Bug 路径至少追加 `BUG_BASELINE_ASSESSED / BUG_ROUTE_RECOMMENDED / BUG_ROUTE_AUTO_SELECTED / BUG_ROUTE_CLARIFIED / BUG_ROUTE_OVERRIDDEN / BUG_FIX_BRIEF_CREATED / BUG_HANDOFF_DISPATCHED`（按实际发生使用）；Product Logic Defect 继续使用正式 Decision/Changelog/Impact 事件。事件必须引用 Assessment、Brief、baseline refs、五项自动分流条件、Controller rules/version、必要 clarification/override 和适用 Eval 的确切版本/hash，不能只记录一个“已判为 Bug”的标签。新 Run 不产生固定 `BUG_ROUTE_CONFIRMED` 事件。

Document Experience 复用 Audit Event Schema，至少可记录 `HUMAN_VIEW_RENDERED / DOCUMENT_EXPERIENCE_VALIDATED / HUMAN_VIEW_STALE_DETECTED / READABILITY_REVIEWED`，并引用 source hash、policy/profile/template versions、audience/language、validation result 和适用 finding。它们是现有 attempt 内的呈现执行事件，不是新的业务 Artifact、节点、Gate 或第二份 Audit Ledger。

</details>

### 20.2 强制验证时机

`audit.verify` 至少在以下时机强制执行：

- Attempt 产物提升为正式版本前。
- Run 恢复时。
- Plan Ready、Problem Ready、PRD Ready 前；实验 intent 的附加条件在同一 PRD Ready 内完成。
- Handoff dispatch 前。

失败时进入 `AUDIT_INTEGRITY_BLOCKED`，不得继续正式流转。

### 20.3 哈希链的真实能力

本地哈希链可以检测单点、意外或未同步重写，不能防止拥有全部写权限的主体重写全部事件并重算全链。

V1.4 不声称本地 Ledger 不可抵赖。需要强防篡改时引入受保护远端、签名或宿主外的 append-only anchor。

### 20.4 回放

- 状态恢复：读取 current state snapshot，并用 meaningful events 校验关键迁移历史；事件足够时可以辅助修复 snapshot，但不承诺完整 event sourcing 或从事件重建所有中间状态。
- 规则复核：用固定 Validator/policy 重查历史证据。
- 模型复现：不保证逐字相同。
- 外部副作用：默认只验证 receipt，不重新执行。

### 20.5 正式产物不可覆盖

- 当前 Attempt 内的工作草稿可以修改。
- 一旦被 Reviewer、Gate、负责人或 Connector 引用，产物版本冻结。
- Optimizer 生成新版本，旧版本和旧 verdict 永久保留。
- `current` 只是可变指针，不能代替历史版本。
- 获授权原位例外必须记录操作者、原因、前后哈希和影响。

上一条通用“获授权原位例外”不适用于 PRD package 中已落盘/引用/分享的 `archived/` checkpoint 或任何 `released/` 文件；这些文件没有原位修改例外。PRD 只有尚未成为 material checkpoint、未被引用/分享的当前 scratch buffer 可以原位编辑。

文档、Decision Record、Roadmap snapshot/proposal、Product Changelog、计划、PRD、审计报告和运行合同一旦被批准、对外提交或被其他产物引用，后续修改必须创建新版本，并记录 `supersedes`、变更理由和新哈希；Graph 不允许用“最新版”覆盖历史证据。

State Controller 在正式产物写入前执行 `artifact.version.guard`：未被引用的当前 Attempt 草稿可以原位更新；已交付、已审核、已批准、已进入 Gate 或已被下游引用的产物只能创建新版本。新版本必须带上一版本引用、变更摘要、创建原因和内容哈希；Decision 还必须维护显式 `supersedes` 链。旧版本 hash 在发布新版本前后都要复核。项目级 `CHANGELOG`、Product Changelog 和可变 `current` 指针只提供不同语义下的导航或变化摘要，都不具有覆盖或删除历史的权限。

PRD 文档进一步遵循 §12.4.4：material 过程稿进入 `artifacts/prds/archived/` 的 self-contained Candidate directory，正式可交接版本进入 `artifacts/prds/released/` 的 self-contained release directory；既有 `DOCUMENT_CHANGELOG.md` / Release / State / Audit records 追加版本与状态。失效/撤销 release 原目录继续保留；Handoff 只能消费 exact released directory/Markdown/assets hashes。该文档账本不能替代 Product Changelog、架构 `CHANGELOG.md`、上游 Decision/Plan/Slice/Knowledge 记录或 Audit Ledger；可选 PRD Content Checkpoint 也没有该替代能力。

Product Plan 深化复用相同的 immutable material-checkpoint 原则和可审计 changelog/supersedes/impact 语义：v0、每次 material reconciliation checkpoint、正式 PRD Slice/Coverage/Reconciliation 的 material checkpoint、formal Review Candidate 与进入 Plan Ready 的版本都不可被后续版本覆盖。它不因此复刻一份 PRD package，Slice/Coverage/Reconciliation 也只是同一 Product Plan 的 versioned section/view/result，不另建“深化报告”、Coverage 大文档或第二真源；Planning Refinement 固定为 `product.planning` 内部 recoverable Loop，正式 Review 绑定 frozen Candidate。具体物理目录及 Module/Iteration Map 的内嵌/独立表达继续留待真实实现和 Node Review。

### 20.6 权限、不可信输入与隐私边界

- 节点和 Connector 使用 deny-by-default allowlist，只获得当前动作需要的项目、资源和操作权限。
- Issue、用户反馈、网页、知识材料和外部审计结果都视为不可信数据；其中的文字不能改变 Graph、Skill 指令、权限、Gate、工具选择或批准政策。
- Signal 必须保留原文与来源，同时把解析后的主张、引用和指令分区存放；Reviewer 可以引用内容，不能执行内容中的命令。
- 外部写入 Connector 必须再次检查 mount point、对应 profile 的 Ready、versioned side-effect policy/预授权或 exact 写入授权、Project Policy、action constraint、项目作用域和目标 allowlist；`still_allowed` 不得被解释成对其他 action 的授权。
- 项目配置必须定义敏感字段脱敏、最小化收集、保留期、删除/封存和派生产物处理规则；审计所需最小证据与隐私删除发生冲突时，记录 tombstone 和授权依据，而不是无痕改写历史。
- Break-glass 只能由项目政策显式启用，必须限时、限作用域、记录操作者与理由，并且不能赋予 Better Product Graph 发布正式知识的权限。

这些约束在 `detect_only` Host 上主要由正式状态入口、Connector 前置检查和审计发现绕过；V1.4 不把它表述为操作系统级物理隔离。

### 20.7 架构自身的 Audit–Optimize Loop

Better Product Graph 的规划和架构变更也必须践行目标导向审计：

```text
冻结候选版本
→ 提取目标、承诺和可验证期望
→ 独立语义审计 + 确定性结构检查
→ 审计结果自审与 Disposition
→ 根因诊断
→ 只修复被接受的问题并生成新版本
→ 用原期望重新审计并做回归对比
→ 达到停止条件或明确标记未验证风险
```

审计脚本、期望和目标在看到结果后不得被原位修改来制造 PASS；目标真的变化时，创建新的审计基线并说明差异。文档结构通过只表示“设计已明确”，不得写成权限、并发、外部 API 或下游接收已经在运行时验证。

本节是完整 Product Goal-Based Audit 的保留位置，适用于 Better Product Graph 架构、版本发布、Roadmap 里程碑或其他大范围对象；它可以按任务运行完整阶段、审计自审与独立报告。单份 PRD 的内置 `review.parallel` 只使用 §12.3.1 的目标忠实 profile，不生成这里的项目级脚本、评分和文档套件，也不重新要求 Owner 确认已经版本化的上游承诺。

---

## 21. Host Plugin 与 Host Adapter

### 21.1 关系

- Host Plugin：面向用户安装的包。
- Host Adapter：Plugin 内部把宿主能力映射到 Core 的实现。

### 21.2 最小 Host Contract

```yaml
host_adapter:
  identity: get_host_and_session_identity
  project_root: resolve_and_validate_exact_project_root
  preflight: detect_or_initialize_local_git_and_report_status
  skills: discover_and_invoke_skill
  intents: map_host_entry_to_core_intent
  interaction: map_run_modifier_and_request_prompt_permission
  execution: invoke_bounded_subagent_or_declare_unavailable_or_sequential
  task_capability: report_subagent_persistence_concurrency_and_isolation
  model_profile: map_best_available_balanced_fast_and_report_actual
  context: provide_declared_context
  approvals: request_human_approval
  capabilities: report_host_capabilities
  enforcement: report_enforcement_mode
  progress: emit_progress_and_waiting_state
```

`enforcement_mode`：

- `enforce`：宿主能够强制所声明的权限边界。
- `detect_only`：只能通过状态入口和审计检测绕过，不能物理阻止磁盘写入。

Ready Assertion 必须记录该模式。`detect_only` 不自动让本地 Product Ready 失败，但高风险外部写入必须有明确人类批准，并由 Connector 再检查前置条件。

一期只实现 Codex。第二个 Host Adapter 出现前，不建设通用基类或复杂并发 Runtime；除 Skill 可发现、等待可恢复、无法强制时如实报告外，还要对 sub-agent 的隔离、持久化、并发、模型 profile 和降级方式做 capability report。当前规划不宣称 Codex 已可靠支持所有这些能力：不支持时返回 `NOT_AVAILABLE / DEGRADED_TO_SEQUENTIAL`，并保留同一业务 Node/Result 合同；不得用主 Agent 串行执行后伪报成 sub-agent 并发。`BEST_AVAILABLE / BALANCED / FAST` 只是 task capability intent，实际 provider/model/version 由 Host 映射并写审计。

### 21.3 一期用户入口与稳定 Core intents

Codex Host Plugin 的 display name 是 `Better Product Graph`，只公开一个显式 Skill：`$better-product-graph`。自然语言 implicit invocation 与这个显式 Skill 必须进入同一个 Host intent parser 和相同 Core intents，不得形成两套 Graph、Schema 或状态语义。

`$better-product-graph` 后的稳定 intent words 是：

| Intent word | 显式 Skill 示例 | 自然语言等价示例 | Core intent 映射 | 边界 |
|---|---|---|---|---|
| `new` | `$better-product-graph new <Signal>` | “分析这个产品想法，并启动一个新的产品 Run” | `signal.submit` + `signal.activate` | 授权低风险分析，不是产品承诺；仍经过 Intake、Router、Validator 和 Gate |
| `capture` | `$better-product-graph capture <Signal>` | “先把这条反馈收进待处理箱，不要开始分析” | `signal.submit`，`activation_intent=INBOX_ONLY` | 只入 Inbox，不启动完整 Run |
| `inbox` | `$better-product-graph inbox [filter]` | “列出最近未处理的高优先级 Signal” | `signal.inbox.list` | 只读；筛选不改变正式状态 |
| `status` | `$better-product-graph status [run_id]` | “这个 Run 现在到哪一步了？” | `run.status` | 只读当前版本、等待和下一允许动作 |
| `resume` | `$better-product-graph resume [run_id]` | “从已保存位置继续这个 Run” | `run.resume` | 先校验 current state、exact refs/files、外部/分支变化与 stale/Impact，再展示简短直白 Resume Brief；不是重放整段会话 |
| `pause` | `$better-product-graph pause [run_id]` | “保存现场并暂停这个 Run” | `run.pause` | 只在可安全暂停边界生效并写审计事件 |
| `handoff` | `$better-product-graph handoff [run_id]` | “检查并展示这个 Run 的交接包” | `handoff.prepare` + `handoff.validate` | 只准备、校验和展示；不等于 `handoff.dispatch` |
| `connectors` | `$better-product-graph connectors` | “当前有哪些 Connector 可用？” | `connector.status` | 只报告能力/状态；一期 Input Connector 未配置时如实返回 `NOT_AVAILABLE` |
| `audit` | `$better-product-graph audit [run_id\|signal_id]` | “告诉我这条 Signal 为什么实际走了这条路线” | `audit.view` | 只读且按权限过滤；不写状态、不 reroute |
| `interview` | `$better-product-graph interview skip [run_id]` / `interview resume [run_id]` | “跳过当前及后续 PM 访谈” / “恢复引导式访谈” | `interaction.policy.set` | 一个 intent 下的两个运行时 action；只改目标 Run 的 PM 访谈政策，不表示信息充分或授权继续 |
| `help` | `$better-product-graph help` | “Better Product Graph 能做什么、下一步怎么用？” | `host.help` | 只展示入口、边界和当前可用能力 |

`new` 与 `resume` 继续支持同一个稳定 modifier；访谈已经开始时使用上表的 `interview skip|resume`，无需退出或重启 Run：

| 用户表达 | Host 规范化 | 作用域与效果 |
|---|---|---|
| `$better-product-graph new interaction=no-pm-interview <Signal>` | `interaction_policy=NO_PM_INTERVIEW` | 新 Run，`scope=CURRENT_RUN`；禁止 PM 产品访谈 |
| `$better-product-graph resume <run_id> interaction=no-pm-interview` | `interaction_policy=NO_PM_INTERVIEW` | 从当前 Run 恢复点继续并立即应用 |
| “先把这个需求独立分析完，不要采访我” / “继续这个 Run，但不要问我产品问题” | 与上述相同 | 自然语言等价入口，仍需明确目标 Run |
| `$better-product-graph interview skip [run_id]` / “跳过当前及后续 PM 访谈” | `interaction_policy=NO_PM_INTERVIEW` | 立即停止目标 Run 当前尚未回答的问题及后续 PM 访谈 |
| `$better-product-graph interview resume [run_id]` / `$better-product-graph resume <run_id> interaction=guided` / “恢复引导式访谈” | `interaction_policy=ALLOW_PM_INTERVIEW` + `interaction_style=GUIDED` | 从当前最高价值的未解决 PM-only unknown 继续，不重放全部旧问题 |

未指定 modifier 时默认 `interaction_policy=ALLOW_PM_INTERVIEW`，交互 style 继续使用项目配置；显式 `interaction=guided` 同时恢复允许访谈和 Guided style。每次变更只作用于当前 Run，不静默写入项目或用户全局偏好。Host Adapter 必须把 modifier、actor、目标 Run 和自然语言/显式来源传给 Core；State Controller 原子更新 policy 后才可继续。未来可能存在更强的 `NON_INTERACTIVE`，但一期只保留 unsupported 扩展位置：不得接受该值、不得将其等同 `NO_PM_INTERVIEW`，也不得暗示所有人类审批都被关闭。

调用 `$better-product-graph` 但没有 intent word，或自然语言意图仍不明确时，进入 guided/default prompt，向用户展示建议动作和所需最少信息；不得猜测为 `new`、不得启动外部 Connector、不得静默执行任何外部写入。

以上是**一个公开 Skill 后的十一个稳定 intent words**。`interview` 是一个 intent，`skip/resume` 是其 action，不是两个平行命令或第二个 Skill；启动时的 `interaction=...` 仍是 `new/resume` modifier。它们不是十一个独立 Skills，也不是 Codex 自定义 slash commands。当前没有证据确认 Codex Plugin 可以可靠注册自定义 slash command，因此 slash command 不属于一期入口或验收依赖；未来 Host command 只能映射这些稳定 Core intents，不能改变其权限语义。公开入口不注册 `$bpg`、`$prd-graph` 或其他别名。

`audit.view` 展示授权范围内的原文/claims、Classification Record、evidence/knowledge/policy 引用、Agent 推荐与实际 destination、并行 `existing_links`、澄清、override、reroute、版本和 hash；Discovery 路径展示 Evidence Reference provenance、Problem Evidence Map 版本链，以及问题假设审视 checkpoint 的原话/事实角色、现象/影响/问题假设/期望结果/提出方案、方向性关键假设、反证/可信替代/历史/no-action/症状原因检查、exactly one MVU、推荐信息来源、下一信息请求、三类下一建议和版本差异；再分别展示后续 Evidence Request、Learning runtime status history、completion disposition、advisory next-action recommendation、action-relative sufficiency 与 Knowledge Proposal 引用。Bug 路径还展示 Baseline Assessment、cause class/surface tags、Agent Route Recommendation、Controller Route、必要澄清/override、Brief/Eval 与 Handoff 引用。它读取 signal-scoped Signal Ledger 或 Run Audit Ledger，不保存、不生成也不暴露模型隐藏 chain-of-thought；缺少结构化理由时应显示审计缺口，不能让模型事后编造“思考过程”。

Discovery 的 `audit.view` 还应按权限显示 Learning Round 链、`source_resolution_type`、等待/恢复、Round Delta 与继续/停止理由，以及 `interaction_policy` 变更和 skipped-interview impact。实际发生 PM 访谈时，它展示已保存的 interrupt reason、MVU、核心问题/必要澄清、PM claim type、挑战强度/依据、Agent 首选/最强反方、agreement/disagreement、authority 和下一动作，但不默认展示全量逐字对话。它只能展示已保存的结构化事件，不能为缺失的提问理由、被跳过问题或 Agent 建议事后编造内容。

`handoff` 命令本身不是外部写入授权。Product 的 self-contained Released artifact set 在 Ready 后已经是完整本地交付物；带实验 intent 的 PRD 使用同一 released source，并在内容中保留其受控边界。`handoff` 只准备、校验和展示 exact source，不能静默触发副作用；真实 `handoff.dispatch` 必须按 §18.1 的目标 policy 执行。未授权时只能展示“本地已完成”或“可发送但缺 Connector/权限”，不能再次要求 Owner 审批 PRD 语义。Incident Verification Packet 与 Bug Fix Brief 的 Engineering Handoff 不要求 PRD Ready，但分别必须通过 §17.3/§17.4 的轻量检查，并具有显式批准或版本化 policy 对“通知/提单”这一具体动作的预授权；Bug Brief 还必须绑定可靠 Baseline Assessment、Agent Route Recommendation、Controller Route 与必要的 clarification/override record。该授权不能外推为改变产品规则、回滚、降级、数据修复、赔付或外部沟通授权。无 Connector 时仍能展示完整本地交付物，不得声称已发送。

### 21.4 公开 Skill 与内部 Atomic Skill Modules 的边界

Graph 的 `signal.prepare`、`problem.synthesize`、`prd.render`、Reviewer 等能力是 Core 的 **Atomic Skill Modules**：它们保持单一职责、节点级指令、可独立测试和按需加载，但不是 Host discoverable Agent Skills。源码使用 `src/core/atomic-skills/<node>/INSTRUCTIONS.md`，构建时只进入唯一公开 Skill 的 `references/atomic-skills/`；文件名不使用 `SKILL.md`，路径不位于 Plugin discovery 的 sibling `skills/<name>/` 入口。

Plugin manifest 只导出 `skills/better-product-graph/SKILL.md` 与 `$better-product-graph`。Orchestrator/Controller 根据当前 Run 的 `current_node`、Graph Manifest、权限、输入版本和允许边，解析公开 Skill 内的相对路径并加载对应内部模块；内部模块不能自行被 activation。用户直接点名内部模块、构造 node ID、引用 `references/atomic-skills/` 或调用底层脚本，均不能跳过上游产物、Validator、Gate、审批、状态写入或审计。构建/安装检查必须证明没有整目录镜像、越界 symlink 或第二个 discoverable Skill。

### 21.5 项目 Git Preflight

> **CONFIRMED PHASE-ONE RULE**：Git 是项目级横向版本基础设施和 Host preflight，不是业务 Graph Node、Gate、审批或新的运行服务。

每次开始或恢复项目时，Host 先解析并校验 **exact project root**，再检查它是否已经位于 Git repository/worktree 中。若 `git rev-parse --show-toplevel` 能解析到当前目录或其父级仓库，就复用该 repository/worktree，不创建嵌套 repo；若完全不在 Git 中，则默认直接在 exact project root 执行本地 `git init -b main`，不为这一步打断用户。Host 必须拒绝把 HOME、工作区集合根或其他未明确的广泛目录当作项目根。

初始化前先确定 `.gitignore` 与敏感文件边界；任何后续 add/commit 都必须遵守该边界。自动 init **不等于**自动 add、commit、push 或创建 remote，也不授予外部副作用权限。日常节点、对话、autosave 和机械状态变化不制造 commit；只有 material checkpoint、正式冻结/发布版本或明确的集成点才可以在相应授权/项目策略下提交，冻结版本可使用可追溯 tag。

Git 不可用、项目目录只读或初始化失败时，preflight 必须保存真实原因和状态：基础分析仍可安全运行时为 `DEGRADED`，但不得声称已有 Git 版本保证；当前动作依赖可版本化冻结、并行隔离或正式交付而无法满足时为 `BLOCKED`。Agent 不得伪造初始化、commit、tag 或 remote 成功。

并行 sub-agent 涉及文件修改时必须使用彼此隔离的 branch + worktree；sub-agent 不能并发写主 worktree、current pointer 或 released artifacts。主 Agent 在 exact base 上审查每个 diff、处理冲突并整合，仍由既有 State Controller、Owner 与 Handoff 规则决定正式状态。该规则只约束执行隔离，不把 branch/worktree 注册成业务节点。

---

## 22. 第一期范围

### 22.1 必须实现

- Codex Host Plugin / Adapter：display name `Better Product Graph`；Plugin/Skill/package machine name `better-product-graph`。
- Codex distribution allowlist：manifest 只发现 `skills/better-product-graph/SKILL.md`；Core Atomic Skill Modules 从 `src/core/atomic-skills/<node>/INSTRUCTIONS.md` 构建到该公开 Skill 的 `references/atomic-skills/`，不得把内部目录整体镜像/链接到 dist `skills/`，不得出现第二个 discoverable Skill。
- 自动生成并校验最小 `build-manifest.json`：绑定 Plugin SemVer、exact Git commit/dirty、architecture baseline、execution contract versions/fingerprint、稳定 inventory 与 artifact hash；在 fresh installed copy 验证 relative resources、allowlist、identity 与源码工作区隔离。当前不要求签名、SBOM、远程 attestations 或规划稿逐文件人工 hash。
- Host project preflight：解析并校验 exact project root；复用已有父级 repository/worktree，否则在项目根静默执行本地 `git init -b main`。先落实 `.gitignore`/敏感边界，不自动 add/commit/push/remote；失败如实记录 `DEGRADED/BLOCKED`，不新增业务节点或 Gate。
- Host Adapter 的 bounded sub-agent capability/model profile 合同与 Core Sub-agent Execution Policy：一期仅采用当前 Host 内部 sub-agent；对抗 Review、可并发 Reviewer、独立研究/Eval/Analysis 候选优先使用只读最小权限 worker attempt，支持 exact snapshot、统一结果、join 保留分歧和 `BEST_AVAILABLE / BALANCED / FAST` 意图。宿主不支持持久化、并发或模型选择时必须如实降级，不把能力写成已实现事实。
- Plugin 内本地 Deterministic State Controller module/library：基于 versioned rules/tests、exact records/hashes 和 CAS，原子维护每个 Run 的 current state snapshot 与 append-only meaningful event stream，并引用独立版本化 artifacts；`state.yaml/state.json/events.jsonl` 只是未冻结的文件名示例。不使用 LLM/subagent 作为正式 Gate，不建设 Registry、数据库、Service、MCP、CLI 或 daemon。
- Decision Run → Plan Run → PRD Run 层级，以及复用同一 Run State Schema 的 profile 模型。
- Node Result、Run State、Audit Event 三个 `v0alpha` 逻辑合同；持久化仍只有 state snapshot + meaningful event stream 两类机器记录，Node Result 不成为第三条账本。
- Core 内 versioned Document Experience Policy/Profile resolver、共享 Human View Renderer、`document.experience.validate`、`templates/human-views/` 与内部按需 Readability Reviewer；它们由现有节点调用，不注册新 Graph Node、Loop、Gate、Runtime 或公开 Skill。
- 第一期只保证 `product_plan / prd / decision / incident / bug_fix / handoff / audit / internal_review` 八类真实消费者；`product_plan` 首期范围只覆盖按需一页摘要，`internal_review` 只渲染 exact PRD 的遗留/分歧 concern。所有视图绑定 source/policy/profile/template exact versions，PRD 默认继续使用 §13.1 的 `better-product-plan` 模板和现有 Supplement 机制。
- 本地轻量恢复：读取 current state，验证 exact refs/files/versions，检查 external result 与 branch/worktree 变化，渲染简短 Resume Brief 后从 current step 继续；material 变化先进入既有 stale/Impact/conflict。Git 管内容版本，Run State 管当前位置，Audit Events 管关键变化，不互相复制。
- PRD 文档生命周期：`artifacts/prds/archived|released/<PRD-ID>_<短标题>_v<版本>_<日期>/` 使用 per-version self-contained directory；主 Markdown 与目录同 stem、相对引用本目录 assets、无附件不建空目录。沿用 append-only `DOCUMENT_CHANGELOG.md`、可重建 current 导航与 version guard；Ready 后 exact release 直接成为本地交付单元，不再 build 独立 Handoff Package。Markdown+assets 是 canonical source，exports 按需派生。
- Product Decision & Roadmap Memory 的本地版本化文件、结构化索引、精确引用和 `current` 导航指针；同一 Decision 投影为职责分明的 Ledger/Roadmap/Product Changelog/Audit，不建设四套流程或数据库服务。KMG 未接入时，本地 records 足以完整运行；未来接入后才增加团队共享/canonical 发布语义。
- 独立可恢复 `product.decision` 节点：内部编排 AI Decision Brief、按风险/未知触发的 bounded adversarial/domain sub-agent Review、Owner 讨论/挑战与明确选择、Controller deterministic route；允许 versioned run-local Draft/checkpoint 跨会话恢复，但不把五项内部动作注册为 Graph Node，默认不全量调用 Reviewer。只有最终 Owner-chosen Decision Record/route 是正式边界。五种 machine outcome、基本边界、Decision Record 通用五项、chosen-outcome 最小补充、R0—R3 轻量 action-risk classification 与 material disagreement 的一次实质挑战均已确认；Agent 不迎合也不无限阻挠，Owner 在权限内最终选择。清晰自然语言 outcome/scope 经结构化和必要一次 challenge 可直接构成 choice，不再追加确认 UI。Decision Brief/交互/摘要/Handoff 从同一 Draft/Record 渲染，Record 确认后 immutable。
- `product.decision` 终止时复用现有 State Controller transition validation：检查 exact Owner confirmation/Record、合法 outcome、通用/结果专属字段、必要 risk/constraints、current refs 和 disagreement/accepted risk；通过后按结果确定性路由，失败留在当前节点并输出直白 unmet condition + repair target。不建设 `decision.ready`、Decision Ready Gate/Artifact/Reviewer、Owner 二次确认，也不把外置 PRD 汇总审批搬入此处；Research 内部形态、Roadmap canonical 合同和下游 Ready 仍待后续 Review。
- Codex 自然语言 implicit invocation 与唯一显式 Skill `$better-product-graph`，共同映射 `new / capture / inbox / status / resume / pause / handoff / connectors / audit / interview / help` 十一个稳定 Core intents；`interview skip|resume` 可在进行中即时修改当前 Run，`new/resume` modifier 继续支持。不新增第二 Skill/alias，不依赖自定义 slash command。
- Atomic Skill Modules 仅作为 Graph 内部能力，由 Orchestrator/State Controller 按当前 Run 允许节点加载，不能作为用户命令或 Host discoverable Skill 绕过 Validator、Gate 或状态。
- 手动 Signal 输入、本地 Signal Inbox，以及作为所有自然语言/Skill/Issue Collector/飞书/研发/测试/未来 Input Connector 唯一入站挂载点的 `signal.ingest`；Connector 只自动附加 provenance，不要求外部填写内部 Schema，也不执行产品路由。普通/派生 Product Signal 继续 `signal.prepare → signal.relate? → signal.classify → route.select`；没有历史索引时 `signal.relate = NOT_AVAILABLE`，不阻断基础运行。
- 分开的 append-only Classification/Route Records、signal-scoped Signal Ledger、Router Audit Events、临时 `NEEDS_CONTEXT`、四个互斥 destination、并行 `existing_links`、受约束人工改路和只读 `audit.view`。
- 本地只读 Knowledge/Product Memory Snapshot，以及正式本地 Decision Ledger、条件化 Roadmap/Research Request 投影、material Product Changelog 和逐产物 Impact List。新 Signal 通过 `existing_links` 关联 historical Decision/PRD，不新增 Router destination，并按 §10.7 四级影响规则选择摘要、提醒或 exact action 处置。向 KMG 提交 raw source、derived knowledge、接收影响通知与同步确认的合同，等待 Knowledge Requirements 反推后再定义；Experiment Portfolio 仅是未来原型风险，不是一期真源。
- Discovery Evidence 基础合同：`evidence.collect → evidence.map`、不可变 Evidence References、append-only/run-local `problem.evidence.map.v1`、独立可恢复 `problem.learning.loop`、Learning Round Delta、版本化 Evidence Request、MVU 驱动循环，以及从 Map 提交 Knowledge Change Proposal 的边界。Learning State 明确分开五种 runtime status、三种 completion disposition 与 advisory next-action recommendation；`WAITING_FOR_EVIDENCE` 可恢复且不限 human，停止采用 action-relative sufficiency。Learning Loop 内部支持七类 `source_resolution_type` 和已确认的 PM bounded joint judgment 六步：一个 MVU/核心问题、Junior PM 非诱导脚手架、一次最高价值挑战、明确 Agent 首选与最强反方、风险/冲突/可逆性驱动的挑战强度，以及分歧/authority/停止记录；这些内部动作复用 Learning State/Audit，不增加顶层节点、Gate、业务 Artifact 或业务路线，人工 override 仍待讨论。
- Analysis Method Hook 与 versioned Method Card 最小合同：复用现有 Learning/Synthesis/Planning 内部调用点，默认 `analysis_method=NONE`，支持 Level 0—3 渐进重量与调用五问；本期只验证合同和无方法时正常运行，不内置具体产品分析模型。
- 独立轻量 `problem.assumption.audit` 节点：Evidence Map 后、Learning Loop 前按五步逻辑生成 versioned run-local checkpoint，默认零 PM 访谈；动态选择方向性假设，只选 exactly one MVU、最佳来源与一项下一信息请求，完成语义仅为可信认知起点；输出三类下一建议并按 material input/fundamental reframe 重跑，不创建正式业务 Artifact、Reviewer Loop 或 Ready Gate，也不替代 Learning Loop 的三维完成合同或人工 override。
- 独立轻量 `problem.synthesize` 节点：只在 Learning=`COMPLETED + READY_FOR_SYNTHESIS` 后，读取 exact Discovery inputs 并一次性生成 versioned Problem Definition Candidate；支持失败恢复、material gap 携新 MVU 返回 Learning、source stale 重算和 supersedes。Candidate 完成只表示稳定可审，不表示 Problem Ready 或 Owner choice。
- Problem Ready 只保留两类执行者：隔离上下文/独立 attempt 的内部 Product Quality Reviewer Agent 只读 exact Candidate 并输出 advisory Finding；程序化 State Controller 重算 Candidate、同版本 Review disposition 与上游 exact refs 三类机械条件，输出 `READY | NOT_READY` 并唯一写状态。固定 `problem.owner.confirm` 已折叠到紧邻的 Product Decision，不建设 action-scoped Problem Ready matrix、Junior PM escalation 或低风险 `NOT_REQUIRED`。
- `problem.quality.review` 完整节点合同：exact frozen Candidate + Evidence/Learning/Knowledge/Product Memory 输入；用户/场景/目标/阻碍/影响、方案偷渡、追溯/外推/因果/反证/Unknown/action relevance 检查；action-scoped Finding/Verdict 与四类 repair path；首次 full review、后续 delta-targeted + global invariant regression；no-progress 返回 Learning/Owner；Junior PM 优先关键 Finding/原因/建议。Reviewer 始终只读，不编辑 Candidate 或写状态。
- Run Interaction Policy：默认 `ALLOW_PM_INTERVIEW`，与 Guided/Standard/Compact style 分离；用户可在 `new/resume` 设置，也可在进行中使用 `interview skip|resume` 原子变更当前 Run。Controller 每个 PM prompt 前强制执行；skip 保留已答、记录未答/替代来源/影响，不代表信息充分或授权继续。完整 Discovery 原则上至少一次实质访谈/等价对话，除非无 material PM-only unknown 且继续提问信息增益低，或用户显式 skip；未来 `NON_INTERACTIVE` 不实现。
- Discovery、Problem Ready、Decision、Outcome-first Planning、四个逻辑规划视图和 PRD Run；Evidence 路径不增加独立重型 Ready Gate。`product.planning` 内部 recoverable Refinement Loop 支持 v0、逐块深化、global reconciliation、material checkpoint/supersedes/impact 与 stable Candidate；正式 advisory Review 后按 repair path 返回。`plan.slice → plan.coverage.validate → plan.reconcile` 形成候选、诊断和协调。固定 `plan.owner.confirm` 已取消；普通忠实 Planning 直接进入机械 `plan.ready.gate`，只有 material 新产品取舍回同一 Product Decision。PASS 只为 current activated/eligible slices 创建 PRD Runs。
- `COMMIT` 的 `NOW / SCHEDULED / CONDITION_TRIGGERED` Planning activation；后两者只形成 committed Roadmap，`WAIT` 只形成 exploring/candidate Roadmap。
- 同一 Product Pipeline 的 `EXPERIMENT` delivery intent：最低条件化实验内容、同一 PRD/Eval/Review/Ready/Released/Handoff、typed result 统一回到 Intake/Decision；无独立 Fast Lane、Experiment profile/Ready/Handoff/Portfolio。
- `product.decision` 内部条件化 R0—R3 action-risk classification；不新增节点/Gate/PM 表格，不把问题永久标风险。一期只强化 disclosure、advisory Review 与外置团队关注，正式专业 blocking/waiver 延后到真正无人值守阶段。
- 条件式 Golden Case / Rubric 基线：至少跑通 G01、G03 与 G04；把 Idea/方向压力、线上 Issue/Bug、带方案的用户反馈/Discovery 组合成一期核心入口覆盖，不继续用新增 Case 数量代替能力深度。
- `prd.generate` 内部 Evals Applicability 判断、独立 Fulfillment State，以及 PRD Run 内按需可恢复 `evals.build` 子节点 seam：stable content Candidate 后与 `prd.render` 并行，bounded sub-agent 可按 scope/generate/review 合同形成候选，join 同一 exact version；`REQUIRED` 未满足时只阻止 Ready、不阻止 Candidate 继续成熟。不增加顶层业务路线、Run Profile、PM 问卷或 HITL，也不要求自动化 generator 已完成。
- PRD Fidelity/Alignment 作为现有 Product Review 的首要 rubric：确定性 Validator 检查 exact refs/version/slice/disposition，独立只读 Product Reviewer 检查 scope creep、future 偷带、新规则/虚构事实/Unknown 升级、Guardrail/依赖/回滚/Eval 遗漏和上游冲突。material 新内容返回最早正确上游；不新增节点、固定 Owner confirm、独立报告或第二真源。Review 收敛后可按需渲染同源一页最终摘要。
- `review.parallel` 的 Product Goal Fidelity profile：自动构造同源 frozen goal packet；目标忠实逻辑必需，Engineering/Testability 默认且 LIGHT 可合并，UX/Domain/AI Behavior/Security/Privacy/Compliance 按风险增加；首轮互不可见、只读、主 Agent 后聚合；Finding 使用 exact upstream commitment/evidence/scope、`concern_level`、confidence + confidence_basis、cross-check、repair target 与 disposition；只对高影响项最多两轮 review-of-review；delta repair status 与全局目标/范围/不变量回归可审计。不要实现完整七阶段、分数/等级、覆盖率阈值、`.product-audit` 或 Shell 脚本。
- 轻量可恢复 `review.aggregate / 审查意见汇总`：LIGHT 可同一用户动作自动运行但仍留 attempt。主 Agent 聚类、保留分歧/unsupported并建议最早 repair target；Controller 只校验 attempts、同一 exact Candidate/Goal Packet、Finding 字段、late/stale 与无损追溯。
- `review.finalize / 审查收尾`：Controller 内部确定性 action，只检查 attempts、Finding dispositions、exact Candidate 与同源内审意见。它不裁决 Reviewer、不要求 PASS、不因 concern 阻塞、不注册 Node/Gate/HITL；主 Agent采纳的修订进入 optimize，其余遗留透明交外置团队。
- 可恢复 `prd.optimize / 根据审查意见修订 PRD`：只处理主 Agent采纳且可在当前 PRD 修的聚合建议，批量做最小必要修订，生成一个新 archived Candidate + delta/finding mapping。Candidate version 与 Review Attempt 分开；轮次 2/3/4，两轮无 material progress 提前停止。
- `prd.ready.gate / PRD 最终就绪检查`：Controller 在 finalize 后重算 exact Candidate、同版本 Review/finalize/内审意见、current refs、REQUIRED Evals、Template/Document Experience/version/changelog 与既定机械合同，只输出 `READY | NOT_READY`。Advisory concern 本身不阻塞；READY 无人工二次确认自动生成 self-contained release。
- 轻量 Incident 核查交接路径与 Bug Baseline/Fix Quick Path；Incident 默认只形成 `incident.verification.packet.v1` 线上问题核查包、Engineering Handoff 和同一 Packet 的研发回传版本，可选 Product Response 仅在确需产品判断时开启。
- `bug.baseline.assessment.v1`、三种一级分类与正交 `surface_tags`、五项证据条件下自动分流、条件式最小澄清/override、无 PRD 的 `bug.fix.brief.v1` 与非确定性 Bug Eval Pack。
- Product、Engineering、Testability 等 advisory PRD Reviewer；按风险加入 UX/Security/Privacy/Compliance/Domain 等逻辑角色。它们不拥有当前期 approval/veto/waiver，也不自动套用到 Incident Packet 或可靠 Implementation Deviation Brief。
- Product self-contained Released artifact set（包括实验 intent）、Incident Verification Packet 与 Bug Fix Brief Handoff；PRD Ready 后不打包，`handoff.dispatch` 作为可选可恢复 Connector attempt，按每目标 `disabled/manual/auto_when_ready` policy、幂等 identity、UNKNOWN reconcile 和 receipt 规则执行。无 Connector/权限不影响本地完成，也不新增公开命令、内容审批或第二真源。
- 本地统一回传模拟：纯生命周期状态更新绑定 status，typed Incident/Bug/Experiment/Handoff 结果追加到已有记录；只有新的产品事实/冲突/挑战才派生关联 Product Signal，并以“最早被新证据实质影响的有效环节”生成 Impact/返工建议。普通意见不自动 reopen，material Decision/承诺/Roadmap 变化仍需有权 Owner 新决定。

### 22.2 合同保留但默认不实现

- 入站 Connector 的真实外部来源、周期拉取、回传订阅与对账实现，包括 Issue Collector、飞书和 Development/Test Graph；仅保留统一 `signal.ingest` mount、provenance/typed event 合同、采集型 Inbox 默认语义和高危 policy 升级合同。
- Claude External Audit Connector。
- Feishu Project Connector 与原生 Doc direct render；保留 `handoff.dispatch` mount、manual/auto policy、attempt/receipt 和 DOCX fallback 合同，但真实租户的创建/编辑、素材上传、权限、项目关联、格式降级与远端 reconcile 均需 `PROTOTYPE_REQUIRED / PENDING_PERMISSION_VALIDATION`，一期不设默认路径。
- Development/Test Graph 真实 Connector。
- G02“单一大客户提出复杂审批链”等 B 端/企业定制 Golden Case 完整包；仅保留可选扩展位置，不作为一期验收依赖。
- 自动化 `evals-generator` 原子 Skill 实现；本版本只冻结 `evals.build` 子节点位置、最小语义和 bounded sub-agent seam，不冻结庞大 generate Schema。
- TDD-ready Test Design Contract 的完整扩展、umbrella 命名、正式 Roadmap、功能测试意图的稳定 Schema，以及 frontend/backend/service 等测试类型库；独立 Roadmap Draft 与人工 Review 完成前不得声称这些已交付。
- UX/Security/Privacy/Compliance 独立 Reviewer 实现。
- 第二 Host Adapter。
- `evidence / review_summary` 等尚无稳定真实消费者的 Document Experience Profile 全量模板与兼容冻结，以及 `product_plan` 除 Plan Ready 一页摘要外的完整展示模板；保留 §13.2 映射，随生产者/消费者成熟逐项实现。
- Journey Map、KANO 等具体 Analysis Method 原子 Skill；只有真实 Golden Case / 运行证据证明增量价值后才逐个实现，不作为一期核心验收依赖。
- 跨独立 Agent runtime/Host/provider 的 Multi-Agent Collaboration：只保留角色、exact snapshot、capability/model metadata、最小权限、统一结果与 disagreement-preserving join 的协议 seam；未来经 Collaboration/External Audit Connector 或稳定协议接入，不作为一期依赖。

### 22.3 明确不做

- Better Product Graph MCP Server、CLI 产品和 Web 工作台。
- 独立 State Controller Service、MCP、CLI 或 daemon；一期只实现 Plugin 内本地 module/library。
- 数据库、队列、共享状态服务和多租户权限中心。
- 常驻知识收集进程。
- Driver 层。
- 物理不可绕过的操作系统级隔离。
- 独立 Document Graph/Loop、Document Runtime/Service、Human View 数据库或可脱离 source 手工编辑的第二真源。
- Analysis Method 专用 Router、Registry、Service、Runtime、Graph Node、Gate、公开 Skill/命令，以及全模型必经 checklist。
- 一期 Multi-Agent orchestration platform、跨 Host Agent registry/identity service 或把 Multi-Agent 注册成业务 Graph Node。
- 独立 Planning Router、Planning Profile Service，或照搬 Better Work 的 `TASK/MAP/WAVE/ROUND` 文件与重复状态系统；Profile/Wave/Round 复用现有 Product Plan/Run State/Audit。
- 为 `plan.slice / plan.coverage.validate / plan.reconcile` 新建顶层 Graph Nodes、独立大文档或人工审批层；它们是 `product.planning` 内部动作/事件，Plan Ready 仍由既有 State Controller 执行。固定 `plan.owner.confirm` 不实现。

---

## 23. 建设顺序：端到端实现切片先行

本节的 `Slice` 指 Better Product Graph 自身的端到端实现与验证批次，不等于 §11.2 中产品规划的“纵向拆解”。

### Slice 0：最小运行骨架

1. 唯一源码树和 Codex 构建产物。
2. Node Result / Run State / Audit Event 三个 `v0alpha` 逻辑合同；每个 Run 只持久化 current state snapshot + append-only meaningful event stream，Node Result 不另成第三条账本，文件名/完整字段暂不冻结。
3. State Controller、CAS、Attempt 和轻量 Audit Ledger；事件只覆盖 material checkpoint、正式状态/Owner/Finding/副作用/暂停失败/sub-agent 结果，不保存 hidden CoT、逐 tool call 或逐草稿 hash。
4. 一个最小 Graph Manifest。
5. Plugin manifest 使用 display name `Better Product Graph` 和 machine name `better-product-graph`，且只导出 `$better-product-graph` 一个公开 Skill；历史目录路径只登记迁移待办，不在该 Slice 无痕改名。
6. 一个 Host intent parser，把自然语言和十一个 intent words 映射到稳定 Core intents；除 `new/resume` 的 `interaction=no-pm-interview|guided` modifier 外，还支持同一公开 Skill 下的 `interview skip|resume [run_id]` 运行时 action。它只原子更新目标 Run 的 Interaction Policy，不注册第二个 Skill、slash command、业务节点或全局偏好；未识别或无 intent 时进入 guided/default prompt。
7. 一份 versioned Document Experience Core Policy、首批八个 artifact Profiles（`product_plan / prd / decision / incident / bug_fix / handoff / audit / internal_review`）、一个 Profile/项目配置 resolver、共享 Human View Renderer 和确定性 Validator；全部作为现有节点可调用组件，不写入 Graph Manifest 的持久节点清单。
8. `templates/human-views/`、Human View Metadata 与 validation result 呈现合同；验证 source 变化后 stale/re-render，但不新建业务 Artifact、Gate、Runtime、Service、MCP 或 CLI。
9. Host Adapter sub-agent capability/model profile 探测与最小 dispatcher/join：exact inputs、只读权限、bounded timeout/retry、统一结果和审计；不支持并发/模型选择时如实 `NOT_AVAILABLE / DEGRADED_TO_SEQUENTIAL`，不建设独立多 Agent Runtime。
10. 项目 Git preflight：校验 exact project root，复用已有 repository/worktree 或在非 Git 项目根静默 `git init -b main`；应用 `.gitignore`/敏感边界，覆盖失败降级与并行 branch + worktree/diff review，不自动 add/commit/push/remote。
11. 最小 Resume：读取 state、验证 exact refs/files/current versions、检查 external result 与 branch/worktree 变化、渲染直白 Resume Brief 并从 current step 继续；material 变化先走 stale/Impact，不通过全量会话重放恢复。

### Slice 1：一个 Idea → 一份 PRD → 本地 Handoff

先用真实 Idea 跑通：

```text
signal → evidence.collect → evidence.map v1..N → problem → decision → plan → one PRD
→ advisory review → review.finalize → Ready → local handoff
```

该案例进入 Discovery 后，先以不可变 Signal 和确切 Knowledge Snapshot 形成 `problem.evidence.map.v1`，由 `problem.assumption.audit` 生成首个 versioned checkpoint，并在 `READY_FOR_LEARNING` 后至少跑通一次补证据、Map 新版本、`COMPLETED + READY_FOR_SYNTHESIS` 和独立 next-action recommendation。随后调用 `problem.synthesize`，从 exact Raw Signal、Knowledge/Product Memory、Map、Assumption checkpoint、Learning State/Round Deltas/分歧冻结一份可保留 Unknown 的 versioned Problem Definition Candidate；分别验证一次正常 `COMPLETED`，以及一次发现会根本改变方向的 material gap 后携新 MVU `RETURN_TO_LEARNING`。进入 Planning 后先形成 Target Operating Outcome、Observable Evidence、Non-sacrificable Guardrails 与 Product Plan v0；Selector 对简单 Case 选择 `LIGHT`，在 `product.planning` 内部 Refinement Loop 一次内联完成必要深化和 global reconciliation，但仍保留目标、证据、关键假设、验收、风险与追溯。`plan.slice` 先提出 end-to-end PRD 候选，`plan.coverage.validate` 证明每项重要内容有显式 disposition，`plan.reconcile` 处置 Finding 并生成 current Plan Candidate。另用扩大依赖的 delta 验证动态升级到 `STANDARD`、Round checkpoint 和旧版不可覆盖；sub-agent 只交 Proposal、主 Agent 统一整合。达到 §11.1.1 停止条件后，独立只读 Reviewer sub-agents 对 exact frozen Candidate 做 advisory Review；局部/结构/Decision/Problem Finding 各回正确 repair path，Reviewer 不写 Plan/state。Review finalize 后，Controller 对 exact Plan/Coverage/disposition/Review/conflict/material Decision refs 执行 `plan.ready.gate`，不要求 Owner 阅读或确认整份 Plan；只有新 material 产品取舍才返回 `product.decision`。PASS 只为当前 activated/eligible slice 创建 PRD Run，未来/实验/等待项分别保留在其去向。已有稳定 Plan 的小改动另测 affected-area review + global impact check。

同一 Slice 用 exact Candidate 验证 Problem Ready 的两类执行边界：独立 Reviewer attempt 在隔离上下文中只读审查并产生 advisory Finding/Verdict；本地程序化 State Controller 只重算 current/materially valid Candidate、同版本 Review/disposition 与上游 exact refs，输出 `READY` 后无感进入 Product Decision，或输出带 unmet condition + repair target 的 `NOT_READY`。普通 Unknown、关注等级与未采纳建议可透明携带；Review/refs stale 或 Finding 无 disposition 才按机械合同返回修复点。固定 `problem.owner.confirm`、`PM_ACKNOWLEDGED` 与 `OWNER_CONFIRMED` 不存在；Decision Brief 同屏展示 exact Problem，Owner outcome choice 承担唯一固定责任。Reviewer/Agent 自报 Ready、修改 Candidate 后复用旧 Review、`NO_PM_INTERVIEW` 跳过 Decision 或模拟结果直接 Handoff 都被拒绝。

随后用同一个 Decision Run 验证 `product.decision` 可在 AI Brief 后暂停并从 exact Draft/checkpoint 恢复；低风险且未知较少时不 fan-out 全量 Reviewer，高风险/专业未知命中时只调度必要 bounded sub-agent。Agent 必须给首选建议，Owner 明确选择，Controller 才能基于 exact Decision Record 写 route。五个内部动作不得出现在 Graph Manifest 的节点清单中；Draft、Reviewer 或 Agent recommendation 不能冒充最终 Decision/route。分别渲染五种 outcome 和三种 `planning_activation`，确认推荐层遵守 §10.2.1 信息预算，Owner choice 只需通用五项且由系统填充 identity/exact refs/version/audit。再让 Owner 选择 materially different outcome，验证 Agent 只做一次聚焦 evidence gap/risk/preference reason 的实质挑战，而后由有权 Owner 决定；Record 条件保存双方理由、authorization、accepted uncertainty/risk、recheck/stop 与 execution constraints。逐一验证 chosen outcome 只生成对应 `outcome_details`，未选项无空字段；正式 Record 不可覆盖，改判生成 superseding version。再让同一问题分别拟议内部原型、小流量实验与全量执行，验证风险等级随 action/exposure 改变；STOP/WAIT 不被迫展示风险，EXPERIMENT/COMMIT 必有判断，`RISK_PENDING` 不默认为低风险，R3 仍可写 Plan/PRD，但专业 concern 与执行约束必须披露给外置审核。最后逐项破坏 Owner choice、outcome field、risk/constraint、upstream ref 和 disagreement record，确认 Controller 留在当前 Decision 并返回具体 repair target；修复后分别路由 STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT 三种 activation，且 Manifest 中没有 `decision.ready`。另用重大风险 Case 验证一屏预算不会隐藏安全、合规或不可逆风险。本 Slice 不冻结 Research 内部节点、Roadmap canonical 合同、结果选择阈值、未来无人值守 Domain governance 或下游 Ready。

Problem Quality Review 首轮覆盖完整 Candidate 与全部审查维度；分别构造方案偷渡、单例外推、因果误判、隐藏 Unknown 和 action 不匹配 Finding，验证四类 repair path 不直接写状态。修复后第二轮只重点读取 material delta/未解决 Finding，但重新检查全局不变量；用连续纯措辞修订验证 `NO_PROGRESS` 返回 Learning/Owner，而不是无限循环。默认 Junior PM 视图只先展示关键 Finding、原因、影响和首选修复建议。若宿主可用，Quality Review 作为 `BEST_AVAILABLE` sub-agent attempt；不可用则如实记录降级，不能伪造并发或把外部 Claude Connector 当内部 sub-agent。

同一 Slice 用 `decision / prd / handoff / audit` 四个首批 Profile 跑通端到端视图链：结构化 Artifact → renderer → Validator → 按需 Readability Reviewer → 原有 Ready/Handoff。至少验证字段齐全但术语不可读、文本流畅却隐藏 unknown、Owner 授权被写成用户事实、旧 source 视图 stale，以及“包已生成”不能呈现为“下游已接收”。

同一案例同时跑通一个最小 Decision Record：Owner 确认前允许修改，确认后冻结；PRD 与 Handoff 必须绑定确切 Decision、Roadmap、Product Plan 和 Knowledge snapshot 版本/哈希，不能只引用 `current`。

再将五种 outcome 逐一投影到同一组本地记录：每项都进入 Decision Ledger；新 `STOP` 不制造 Roadmap Item、停止已有事项则变为 `stopped`；`WAIT` 只可 exploring/candidate；`RESEARCH` 进入 Research Request；`EXPERIMENT` 创建带 delivery intent 的同类 Plan/PRD Run 但不成为 committed product、不进入一期 Portfolio；`COMMIT + NOW` 只有真实 Plan Run 创建后才 `in_progress`，非 NOW 只进入 `committed`。只对 material 产品/承诺/规则/发布边界变化生成 Product Changelog，所有 actor/version/action/state/receipt 自动进 Audit。当前只验证 KMG 未配置时本地能够完整运行并保留 future source refs；共享发布与 submission/Impact sync 留到 KMG consumer requirements 明确后的后续 Slice。

入口先分别用自然语言和 `$better-product-graph new` 验证相同 `signal.submit + signal.activate` intents；再用 `capture / inbox / status / resume / pause / handoff / connectors / audit / interview / help` 跑通十一个入口词，确认 `capture` 不启动完整 Run、`handoff` 不 dispatch、未配置 Input Connector 时 `connectors = NOT_AVAILABLE`、`audit` 只读且不暴露隐藏 chain-of-thought。访谈中调用 `interview skip [run_id]` 必须立即停止当前未答问题与后续 PM 访谈、保留已答内容并记录替代来源/影响/恢复点；`interview resume` 只从最高价值未解 PM-only Unknown 继续，不重放旧问题。Signal Intake 必须原子保存不可变原文与接收元数据；自然语言、Issue Collector、飞书和模拟 Development/Test 回传都进入同一 `signal.ingest`，外部提交者不填内部 YAML。普通/派生 Product Signal 再完成 prepare/classify/route；纯 status 只更新绑定记录，typed result 先追加原合同。没有历史索引时 `signal.relate` 明确返回 `NOT_AVAILABLE` 但流程继续；用模拟采集 Connector 验证默认只写 Signal Inbox、不自动创建完整 Product Run，高危输入才按 policy 提醒或升级。

同一 Slice 使用对抗输入验证：Classifier 自行读取授权知识且不向用户提问；只有一个 PM-only 操作事实会直接改变路线时才 `NEEDS_CONTEXT`；用户价值问题直接进入 Discovery；潜在持续伤害先 `INCIDENT_ASSESS`；已激活且含 candidate baseline/expected-vs-actual 主张的疑似偏离进入 `BUG_BASELINE_CHECK`，由 Assessment 再判断基线是否可靠，其余进入 `DISCOVERY_START`；命中现有对象时并行产生 `existing_links`，但不改变目的地优先级。每次分类、推荐、澄清、选择、re-route 和 override 都形成独立版本与 Audit Event，`audit [signal_id]` 可以从 Signal Ledger 回放结构化理由而不泄露隐藏思维链。另验证 `new` 只授权低风险分析、Incident 自动评估/提醒不执行止损；Bug 五项证据条件齐全时 Controller 自动分流，存在 baseline 冲突、PM-only事实或 material路线差异时才提出一个最小澄清，人工 override 必须留痕。

### Slice 2：一份计划 → 三份独立 PRD Runs

以 `STANDARD` 和 `PROJECT_SCALE` 两档验证：Module、Iteration、PRD Matrix 与 Dependency / Shared Contract 四个视角经 `plan.slice` 形成三份而非“每格一份”的 end-to-end 候选；`plan.coverage.validate` 检查遗漏/重复/体验/依赖/上游一致性，`plan.reconcile` 能把局部修复、切片重做、迭代重排、返回 Decision/Learning 分开。消息治理案例应把高风险识别+优先级+展示视为一个可验证结果，并对“误判处理缺失”分别演示加入当前、后置或先实验。最终仅对 activation+eligible 的一份 Ready、一份受 action constraint 限制切片创建 PRD Runs；Waiting 与未来切片不得提前创建。PROJECT_SCALE 的父 Wave 不阻止无冲突的独立 Plan/PRD Run（含实验 intent）并行，只有证明确实不能独立发布时才创建 Batch。另用三份 `COMMIT` 验证 `NOW` 创建 Plan Run，而 `SCHEDULED / CONDITION_TRIGGERED` 只进入 committed Roadmap；触发后仍需重新验证和 activation event。

### Slice 3：用户反馈与证据代表性

使用一期核心 G04（“消息太多，请增加一键清空全部消息”）验证：保留原始反馈，初始读取确切 Knowledge Snapshot 后生成 append-only、run-local `problem.evidence.map.v1`；区分 `SOURCE_ASSERTION / OBSERVATION / VERIFIED_CLAIM / INFERENCE / ASSUMPTION / PREFERENCE / PROPOSAL / UNKNOWN`，显式记录支持、冲突、只证明什么和什么会改变判断。PM 的转述、判断、授权和偏好不得被提升为用户事实，重复同源反馈不得被计算成独立代表性。

在首次 PM 访谈前运行一次问题假设审视：Agent 先保真还原用户原话，并把用户事实、PM 转述/判断、Sponsor 授权和 Agent inference 分开；再拆出“消息多”的现象、尚待验证的影响与问题假设、用户期望结果以及“一键清空”方案。它动态识别会改变方向的关键假设，检查反证、历史 Decision、替代解释、no-action counterfactual 和症状/原因，最后只选一个当前 MVU，推荐最合适的信息来源，并形成一项明确的下一信息请求和 run-local checkpoint。分别验证 `RETURN_TO_EVIDENCE / READY_FOR_LEARNING / ROUTE_REEVALUATION_RECOMMENDED`；第三种只能产生重新路由建议和后续新 Route Record，不能由该节点直接改 destination。已有框架充分的对照样本允许记录“主动检查后未发现可信替代”及依据，不能为通过测试制造稻草人。

同一 Case 验证普通补证不会重复运行问题假设审视；只有 material evidence change 或 fundamental reframe 才生成带 `supersedes` 的新 checkpoint。节点全程默认不问 PM；若 PM 是最佳信息来源，只把一项明确请求交给后续 Learning Loop。完成只代表“可信认知起点 + 下一信息动作”，不输出最终本质问题、Problem Definition/Decision，不写 canonical knowledge、不调用 Reviewer/Evaluator Loop 或独立 Gate；Sponsor 授权与用户价值证据分开，可建议后续受限实验但不能硬阻塞。

该 Slice 至少跑通两轮 `collect → map → update assumptions/MVU`，并覆盖七类 `source_resolution_type` 的代表样本：AI 能自查/研究的信息不反问 PM，专业事实找 Owner，用户事实找数据/用户；只有 PM 独有背景、价值判断或正式授权才打断。打断前给出当前判断、证据边界、为什么问、首选建议和答案影响；PM 不知道时保留 Unknown 并生成包含决策影响、正确来源、有效证据、答案分支和停止条件的 Evidence Request。每轮只围绕一个 MVU，可批量询问少量紧密相关问题，但不设全局硬数量。分别验证低风险可逆实验可以在弱但透明的证据下被建议，而高风险/不可逆动作需要更强证据；Sponsor 授权与用户价值证据分离，可用缩小范围、指标、kill criteria 和回滚塑造建议。继续问答信息价值较低时分别验证 `READY_FOR_SYNTHESIS`、`ROUTE_REEVALUATION_RECOMMENDED` 与 `INSUFFICIENT_TO_PROCEED`，并独立记录研究/实验/恢复等 next-action recommendation；建议不能自动创建 Research/Experiment。稳定新事实只在本地保留为带 exact provenance 的 future Knowledge source candidate，不能由该 Run 直接改 canonical Snapshot；如何提交等待 Knowledge Requirements 反推。

同一 Slice 还要逐步断言 §9.4 的六步协议：先展示理解/证据/Unknown，再说明打断理由和答案影响，只问一个核心 MVU，为 Junior PM 提供非诱导解释与示例，回答后最多做一次最高价值挑战，最后明确给出 Agent 首选、理由和最强反方。用相同 PM 回答分别在低风险可逆、明显证据冲突和高风险不可逆三种情境下验证 `LIGHT / STANDARD / STRONG` 由风险/冲突/可逆性驱动，而不是由 PM 资历驱动；另验证 PM 坚持后会形成分歧、authority、验证/重审/回滚条件和停止原因记录，不会无限争辩、盲从或默认保存全量逐字对话。

同一 Slice 分别通过显式 modifier 和自然语言设置 `NO_PM_INTERVIEW`：验证 State Controller 在每个 PM prompt 前强制拒绝，Agent 不以“再确认一个问题”重试；AI/Owner/用户研究和正式 approval 仍可用，PM-only unknown 被保留并进入版本化 Evidence Request/合法等待。每次跳过显示简短 skipped-interview impact。随后用 `interaction=guided` 恢复同一 Run，确认只改变当前 Run、不新增 command，也不把未来 `NON_INTERACTIVE` 当作已支持能力。

Case Runner 隔离 expected envelope / rubric，以初始不超过 2 轮、每轮最多 3 问作为 G04 参数而非全局 Gate；不用复杂企业定制替代基础能力验证。

### Slice 4：`EXPERIMENT` Delivery Intent、Risk Policy 与 G01

使用独立 G01 Case（老板拍板做 AI 自动回复、现有信号仅含三条销售询问）验证：在不同风险、可逆性、测量和授权条件下，可以得到多个符合条件的结果；被测 Agent 看不到 expected envelope / rubric。`EXPERIMENT` 必须与 `COMMIT` 跑同一 Product Planning→PRD→Eval→Review→`prd.ready.gate`→self-contained release→optional dispatch pipeline，只通过 delivery intent 与条件化实验 section 表达非长期承诺、关键未知、exposure、测量、continue/adjust/stop、Guardrail 和 rollback。低风险简单 Case 可 LIGHT，但高风险/不可逆 Case 必须升档；缺测量或回滚不能 Ready。下游 typed result 统一进入 `signal.ingest`、绑定 exact Decision/PRD/Run、形成 Evidence 并返回 Product Decision；expand/iterate/stop/inconclusive 不能自动改 Decision。验证 AI concern 或旧 `BLOCK_RECOMMENDED` 只能形成 advisory Finding 与外置审核关注，不能自行写 formal Block/approval/waiver；机械合同缺口仍由 Validator/Ready 独立发现。并行 Portfolio 不作为本 Slice 一期 Gate，只保留未来真实规模触发的原型问题。

### Slice 5：Incident 轻量交接与 Bug Baseline/Fix Quick Path

使用一期核心 G03 验证：Agent 先检索 Decision/PRD/AC/设计/API 合同/对外承诺/历史行为，形成 `bug.baseline.assessment.v1`，明确当前基线而非永恒真理，并给出有依据的首选专业建议。分别跑通 `IMPLEMENTATION_DEVIATION / PRODUCT_LOGIC_DEFECT / SPEC_AMBIGUITY`，验证 `surface_tags` 不改变本质分类；前端交互用三个对照样本覆盖实现偏离、规则错误与无明确规则。

Implementation Deviation 只生成 `bug.fix.brief.v1`、五项轻量检查和 Engineering Handoff，不创建 Product Plan/PRD 或默认 Reviewer Loop；Product Logic Defect 生成 superseding Decision 和新 versioned change PRD；Spec Ambiguity 返回 Discovery/Product Decision。另验证 Junior PM 要求“直接修”不能覆盖可靠 baseline、expected/actual、不创建新规则、可判定 AC 与无 material conflict 五项条件；条件齐全时零确认自动分流，不齐全时只作一次能改变路线的最小澄清。确定性 Bug 可标记 `NOT_NEEDED`，非确定性 AI/推荐/搜索/排序 Bug 生成 Bug Eval Pack。Case Runner 必须隔离 expected envelope / rubric。

另用持续伤害与信息不完整的线上信号验证 Incident 默认路径：先生成类型为 `incident.verification.packet.v1`、内容版本 v1 且可含 `NOT_AVAILABLE` 的线上问题核查包，完成三项轻量机械检查和 `incident` Profile 最小行动性检查后通过模拟 Development Connector 或人工方式交接，并进入 `WAITING_ENGINEERING_FEEDBACK`；缺截图、日志、稳定复现或非关键文案项不能阻塞紧急交接。研发反馈必须追加成同一 Packet 的 v2/v3，覆盖确认缺陷、无法复现、符合既有规则、历史决定不再适用和需补信息等结果，再进入 Bug Fix/Product Decision/Discovery/Incident Product Response/Close。默认不生成 PRD、不进入专业 Reviewer/Optimizer/重型 Ready；`bug_fix` Profile 也不能把 Brief 膨胀成 PRD 或长文。只有引入降级策略、临时体验、回滚取舍等产品判断时才开启 Response 子分支并按动作风险确认。验证通知/提单不会被外推为自动回滚等执行权限，临时措施具有 Owner/TTL/退出条件。

### Slice 6：知识影响、统一回传与最早返工点

验证新知识或 canonical Decision/Roadmap snapshot 影响、PARTIAL/INSUFFICIENT、逐产物 Impact List、`IMPACT_PENDING / REVIEW_REQUIRED`、Ready 失效和定向重跑。再让研发/测试/飞书分别经同一 `signal.ingest` 返回：纯 dispatch status、绑定 Incident/Bug/带实验 intent 的 PRD typed result、无新证据的个人意见、PRD 遗漏、Plan/Slice 冲突、Decision 关键假设反证和独立新机会。断言前两类先更新绑定记录，只有产品新事实才派生关联 Signal；Agent 区分 evidence/result/opinion/duplicate，给影响层、依据/反方与翻转条件，Controller 不让 Connector/提交者直接 reopen 或选择返工点。

返工分别落到 Engineering repair、current PRD new Candidate、Planning、Product Decision、Problem Learning、Roadmap 或新 Signal/Run；未改变产品事实的反馈不全链重跑。至少用一次 superseding Decision 和一次 superseding PRD release 验证旧版本不被覆盖，并保留 trigger、reason、Impact 和 downstream refs。material Decision/承诺/Roadmap 变化由当前有权 Owner 新决定；普通意见只 record+link，但 Human View 必须说明 Agent 首选建议和升级所需证据。当前 Slice 只要求本地 records 与 local-only 边界真实可审计，不把 KMG 发布状态设为 Ready/Handoff 前置；未来 shared-canonical policy、submission、ack 与 Impact sync 必须在 KMG contract 原型中另行验证。Audit Log 只记录动作而不替代产品语义；本 Slice 不冻结更细领域 materiality policy。

### Slice 7：Product Evals 合同

验证 Applicability 三条直白分支 `NOT_NEEDED / RECOMMENDED / REQUIRED` 与 Fulfillment 五态正交：复杂但确定的状态机只需 AC，多合理输出/分布依赖/AI-RAG-生成/搜索推荐排序及需样本验证的安全偏见内容风险通常 REQUIRED；RECOMMENDED 默认不硬阻塞。分别验证 `REQUIRED + BLOCKED_MISSING_INPUT` 仍可保存/继续修改 PRD Candidate、但不能 PRD Ready，也不能把缺口推给测试 Graph；验证旧 `NOT_REQUIRED` 与 `DEFERRED` 的显式迁移、人工/通用 Agent候选 Eval Pack、Ground Truth/provenance、专业 Owner、联合 Review 和 Human View 不只显示 code。

同一 Slice 还要验证 `prd.content.build` 冻结 exact stable content 后，`prd.render` 与按需 `evals.build` 可并行并在 join 时绑定同一 source hash；语义变化只使受影响 cases/rubric/traceability stale，纯排版不全量重做。Eval Pack 覆盖 core outcome、normal/boundary/failure/adversarial、input/context/judgment、Rubric、结果处置、Ground Truth、coverage、traceability 和 unresolved gaps；案例数量不能替代风险覆盖。Agent synthetic data 保持 `CANDIDATE/SYNTHETIC`，专业 Ground Truth 未经 Owner/Reviewer 不得升级；只读 Reviewer不能改 Pack，生成 Agent/Optimizer 才能出新版本。此 Slice 不要求自动化 `evals-generator` 已实现，只验证 bounded sub-agent seam，不提前冻结完整 generate 合同；也不要求 TDD-ready umbrella 或 Test Graph 已实现。

### Slice 8：可选 Connector

只有出现真实消费者后，选择一种 Input Connector、Claude、Feishu 或 Development Graph 中的一个接入，不同时实现全部。

---

## 24. 验收与对抗测试

### 24.0 两类系统 Suite 的职责与证据门槛

| Suite | 评估对象 | V1.4 必需覆盖 | 当前证据状态 |
|---|---|---|---|
| Product Golden Suite v0.2 | 产品判断、过程约束与 end state | G01/G03/G04 的 acceptable envelope、critical failures、真实/模拟 PM 互动与最终 action state | `FUTURE FIXTURE / NO RUNTIME PASS` |
| Plugin Contract Suite | fresh installed Codex Plugin copy | discovery；直接、间接、follow-up 与 negative activation；自然语言/显式调用 intent parity；relative resource resolution；唯一公开 Skill；内部入口不可绕过；`build-manifest.json` installed-copy identity | `IMPLEMENTATION CONTRACT / NO INSTALLED PASS` |

两者都不是业务 Node、Gate 或 PRD Eval Pack。Product Suite 不能用源码文档审阅替代真实运行；Plugin Suite 必须对安装候选而非 source tree 执行。任一 Suite 未运行时只能记录 `NOT_RUN / DOCUMENT_ONLY`，不能从另一 Suite 的结果推导 PASS。

现有 `evals/product-graph v0.1` 只允许在报告中以完整标签 **`LEGACY / DOCUMENT-ONLY / NOT A V1.4 ACCEPTANCE BASELINE`** 出现。实现期先建立不覆盖 v0.1 的 v0.2 migration baseline，逐项处置旧 `ProductSpecPackage`、Owner approval、Dev/Test accepted 语义，再创建并运行 G01/G03/G04 fixture。任何把 v0.1 原位改成绿色、将 future fixture 记为 PASS、或用旧 accepted 字段证明当前 Handoff/外置团队状态的做法均失败。

### 24.1 核心路径

- Idea、用户反馈、线上 Issue 都能完成各自路径。
- Codex Plugin 显示名为 `Better Product Graph`，Plugin/Skill/package machine name 均为 `better-product-graph`，manifest 只发现 `skills/better-product-graph/SKILL.md` 并只公开 `$better-product-graph`；没有 `$bpg`、旧品牌别名、第二个 `SKILL.md` 或十一个独立公开 Skills。安装副本中的所有 relative resources 可解析，Atomic Skill Modules 只能由 Orchestrator/Controller 加载。
- 构建只复制 source→dist allowlist；没有内部目录镜像/链接、越界 symlink、非 allowlisted inventory 或源码工作区依赖。fresh installed copy 的 `build-manifest.json` 能核对 Plugin SemVer、exact Git commit/dirty、architecture baseline、execution contract versions/fingerprint、文件 inventory 与 artifact hash；源码目录的 identity 不能替代 installed-copy identity。
- 开始/恢复时能从 exact project root 检测 Git：已有父级 repository/worktree 时复用且没有嵌套 `.git`；非 Git 项目在通过广泛目录与敏感边界检查后静默初始化 `main`。init 后没有自动 staged files、commit、remote 或 push；Git 不可用/只读/失败时按当前交付影响显示 `DEGRADED/BLOCKED`。
- 每个 Run 的 current state 能用直白 Resume Brief 回答事项/目标、current/last/next、exact artifact refs、未解决项/等待/暂停原因、已发生外部副作用/receipt，以及必要的 branch/worktree identity；缺任一会导致重复动作或错误续跑的最小信息时不得声称可安全恢复。
- Resume 必须先解析 exact refs/files/current versions 并检查新 external result 与 branch/worktree 变化；Decision/Plan/PRD 等 material 改变后沿旧 next 盲续失败，纯格式变化却全链重跑也失败。Machine enum 可以保留，但只显示裸 code、不说明当前状态和下一步不通过人类可读性验收。
- meaningful event stream 记录 node enter/complete、formal/material checkpoint、Owner 决定/分歧、重要 Finding、side effect/receipt、pause/failure/stop 和 sub-agent dispatch/result/failure。保存 hidden CoT、每次 tool call、无状态内部尝试、逐措辞/autosave/每份草稿 hash，或为了恢复重放整段对话，均违反轻量审计边界。
- Git、Run State 和 Audit Events 不能互相复制：Git 不承担等待/receipt，State 不复制文档 diff，Audit 不替代 Product Decision/PRD 内容。为此新增 Run Registry、数据库、event-sourcing Service、MCP、CLI 或额外人工确认也不符合一期范围。
- 同一手动 Signal 通过自然语言 implicit invocation 或 `$better-product-graph new` 进入时映射为相同 `signal.submit + signal.activate` intents，并产生相同 Signal/Run 合同；一期不需要 slash command 也能完成、恢复和交付。
- `new / capture / inbox / status / resume / pause / handoff / connectors / audit / interview / help` 分别映射 §21.3 的 Core intents；`interview` 只含 `skip/resume` 两个 action。无 intent/歧义输入进入 guided/default prompt，不能静默启动 Run 或外部写入。
- 完整前置流程可见为 `signal.ingest → signal.prepare → signal.relate? → signal.classify → route.select`；无历史能力时关系节点显式 `NOT_AVAILABLE`，不阻断分类与路由。
- `signal.classify` 默认零用户交互、只读 Raw/Prepared/Relationships/Knowledge，并生成含 known/unknown/conflicts 的独立 Classification Record；授权来源可查的信息由 AI 自行查询。
- `route.select` 只有在一个 PM-only 操作事实会直接改变路线时才短暂 `NEEDS_CONTEXT`；它只输出 `INBOX_ONLY / INCIDENT_ASSESS / BUG_BASELINE_CHECK / DISCOVERY_START` 四个互斥 destination，价值/场景问题进入 Discovery，潜在持续伤害先 Incident Assess。
- `existing_links` 与 destination 分开，可同时关联 Signal/Run/Decision/Roadmap/Incident；命中旧 Incident 的新证据仍进入 Incident Assess。`new` 只授权低风险分析，不等于产品承诺；Incident 自动评估/提醒不等于授权止损，Bug 自动查历史不等于获准生成 Bug Fix Brief。
- `$better-product-graph audit [run_id|signal_id]` 能只读展示原文/claims、分类、证据/policy、推荐与实际路线、澄清、override、reroute、版本/hash，不返回隐藏 chain-of-thought。
- Discovery 的活动节点名和调用链为 `evidence.collect → evidence.map`；Collect 只保存不可变 Evidence Reference 与 source/time/version/query scope/hash/permission/sensitivity/freshness/independence provenance，Map 产生 append-only、run-local `problem.evidence.map.v1`，新版本用 `supersedes` 保留完整历史。
- Problem Evidence Map 能区分八类 claim，表达 `supports / contradicts / only-proves / may-change` 关系，解释来源、直接性、新鲜度、代表性、独立性、可复现性与反证；裸模型百分数不能单独构成置信依据。“某人说过”与“内容为真”、PM 的事实提供/转述/判断/授权/偏好、竞品行为、历史行为和同源重复信号都被分开处理。
- `problem.assumption.audit` 在当前 Map 后、Learning Loop 前独立完成并可恢复；默认零 PM 访谈，checkpoint 绑定 exact inputs/versions/hash，保真区分用户事实、PM 转述/判断、Sponsor 授权与 Agent inference，拆分现象/影响/问题假设/期望结果/提出方案，记录动态关键假设、反证/历史/no-action/症状原因与可信替代或主动检查未发现，选出 exactly one MVU、推荐信息来源和一项下一信息请求，并保存结构化理由和三类下一建议，不包含 hidden Chain-of-Thought。
- Assumption Audit 的完成只表示形成可信认知起点和下一信息动作，不表示找到最终本质问题；若最佳来源是 PM，本节点只把请求交给后续 Learning Loop。Learning Loop 节点/恢复边界、Evidence Request 等待语义以及 status/disposition/recommendation 三维合同已确认；人工 override 和全部 Schema 字段不因此被冻结。
- `RETURN_TO_EVIDENCE` 回到 collect/map，`READY_FOR_LEARNING` 只授权进入当前 Learning Loop，`ROUTE_REEVALUATION_RECOMMENDED` 只触发受审计的 route re-evaluation；Incident 和已确认 Implementation Deviation 不运行该节点，普通补证不重跑，material input change/fundamental reframe 才创建 superseding checkpoint。
- 每版 Map 有一个明确 MVU、决策影响、可能答案及各自 next action、最佳来源和采集成本；每轮从七类 `source_resolution_type` 选择一类或记录 supersede，知识/历史/数据/可授权外部资料由 AI 自查，专业事实找 Owner，用户事实找数据/用户。只有 `PM_CONTEXT_REQUIRED / PM_JUDGMENT_REQUIRED / PM_AUTHORIZATION_REQUIRED` 才默认打断 PM。
- PM 打断前必须展示当前判断、Evidence References/证据边界、为何必须问 PM、Agent 首选建议和答案影响；一次只围绕一个 MVU，可询问少量紧密相关问题但无全局硬数量。PM 不知道时保留 Unknown 并转具体 Evidence Request；PM 回答按 context/claim、judgment 或 authorization 记录，不自动成为 user fact。
- 每次 PM 访谈 Round 完整执行 bounded joint judgment 六步：当前理解/Unknown、打断理由/答案影响、一个核心问题、Junior PM 非诱导脚手架、一次最高价值挑战、明确的 Agent 首选/理由/最强反方。挑战强度按风险、证据冲突与可逆性选择 `LIGHT / STANDARD / STRONG`；Junior PM 可以获得更多解释，但不降低判断标准。
- Better Question 只负责当前 MVU 的选题、来源、措辞与停止，Cognitive Router 只选一个主镜头和少量检查不同风险的辅助镜头；两者都不成为节点/checklist，也不以框架数量提升证据置信度。PM 坚持时保留 Agent/PM 判断、分歧、依据、authority、风险及验证/重审/回滚条件，并在已回答、不知道、来源转移、立场重复、实验信息价值更高或进入正式 Decision 时停止当前轮。
- Analysis Method 默认 `NONE`；调用前通过 MVU/问题、required inputs、information gain/decision impact、相对轻方法增量、成本/限制五问，并按 Level 0—3 选择重量。每轮默认最多一个主方法，输出标为 inference/analysis 且回指 Evidence；缺输入形成 Evidence Request。PM 点名 Journey Map/KANO 但不适用时，Agent 能说明理由并拒绝或降级。
- 证据与 PM/Sponsor 说法冲突时，Agent 清楚展示差异并给出专业首选建议；有效 Sponsor 授权只改变允许动作。可逆可测方向可用缩小范围、指标、kill criteria 和回滚进入受限实验，但不得静默迎合、伪造用户价值证据或无权硬阻塞。
- Learning Loop 每轮保存新增证据、假设支持/削弱/推翻、frame/Agent 建议/MVU 变化和继续/停止理由；任意外部来源等待进入 `WAITING_FOR_EVIDENCE` 并可从确切 Round/Map 恢复。Runtime status、completion disposition 与 next-action recommendation 分开；只有 `COMPLETED` 可选择 `READY_FOR_SYNTHESIS / ROUTE_REEVALUATION_RECOMMENDED / INSUFFICIENT_TO_PROCEED`。停止按拟议行动的用户/场景/目标/阻碍/影响、方向性冲突、remaining unknown、风险/可逆/可测/回滚和下一轮信息价值判断，不要求消灭 Unknown，也不设独立重型 Evidence Ready Gate。
- Learning Loop 可以建议受限实验但不能直接创建或授权 Experiment；低风险可逆可测允许较早提出建议，高风险/不可逆需要更强证据。选择 MVU、来源路由、获取/请求、更新和 status/completion 判断留下事件但不全部升级为顶层节点，Evidence Request 也不被注册为节点。
- `problem.synthesize` 只接受确切 Learning=`COMPLETED + READY_FOR_SYNTHESIS`，并从 exact Raw Signal、Knowledge/Product Memory snapshots、Problem Evidence Map、Assumption checkpoint、Learning State/Round Deltas 与分歧记录生成 versioned Problem Definition Candidate。Candidate 能保留 Unknown，并清楚表达用户/场景/目标/阻碍/影响/期望改变、Evidence boundary、Assumption/Unknown、scope/non-problems 和用户方案与问题的关系；完成只表示稳定可审候选，不等于 Problem Ready。
- Synthesis 默认不继续搜索、完整访谈、补造 Evidence 或选择是否做/何时做/具体方案。小 Unknown 保留；发现会根本改变方向的 material gap 时必须带新 MVU `RETURN_TO_LEARNING`。source version/hash 变化后旧 Candidate 标为 stale，新候选显式 supersedes；后续 Quality Review、Problem Ready 与 Product Decision 只能引用 exact Candidate，不得读取 `latest/current`。
- Problem Quality Reviewer 以独立 attempt 和隔离上下文只读 exact Candidate/Evidence，使用专门 review Skill 形成 versioned Finding/Verdict；同模型可以担任 Reviewer，但不得继承生成会话、自行编辑 Candidate、代签 Owner 或写 Run State。外部 Reviewer Connector 未配置时内部 Reviewer 仍能运行；需要专业事实时转 Domain Owner，而不是冒充研发/测试 Graph 或专业 Owner。
- Problem Quality Review 首次完整检查用户/场景/目标/阻碍/影响、方案偷渡、Evidence 追溯、范围外推、因果、反证/替代、Unknown 与 action relevance；每条 Finding 绑定 evidence、受影响/仍允许 action、修复条件和四类 repair path。后续 Review 聚焦 material delta/未解决 Finding，同时回归全局不变量；连续只改措辞而无 material progress 时返回 Learning/Owner。Junior PM 默认先看到关键 Finding、原因、影响与首选修复建议。
- 对抗审查、同 snapshot 可并发 Reviewer、独立研究/Eval/Analysis 候选优先以 bounded sub-agent attempts 执行；主 Agent 只冻结 exact inputs、编排、join、保留分歧并提交 transition request。每个 attempt 使用最小权限与统一结果；关键审计可请求 `BEST_AVAILABLE`，但实际模型/provider/version 由 Host 映射并审计。Host 不支持时明确 `NOT_AVAILABLE / DEGRADED_TO_SEQUENTIAL`，不伪造并发能力。
- sub-agent required 分支失败只让相关 action 未满足，optional 分支可 `NOT_AVAILABLE` 而不阻塞无关路径；join 不以多数票消除冲突，也不因多个 Agent 同意提高 Evidence confidence。任何 sub-agent 都不能写 state/current/canonical knowledge/released artifact、执行外部副作用，或代替 Human Owner、Deterministic Gate、Connector approval；外部 Claude 是 Connector 而非内部 sub-agent。
- 一期项目配置/Host identity 仍识别当前操作者为有权 Product/Decision Owner，但固定 `problem.owner.confirm` 已移除。Decision Brief 同屏展示 exact Problem Definition；Owner 选择 STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT 就表示以该版本作为决策依据，不再弹“是否确认问题”。若 Owner 指出用户、场景、目标、阻碍、结果或范围 material 错误，必须返回 Synthesis/Learning 形成新 Candidate；不能在 Decision 中静默改写。
- `problem.ready.gate` 由 Plugin 内程序化 Deterministic State Controller 只重算三类条件：current/materially valid exact Candidate；同版本 advisory Quality Review 已完成且 Finding disposition 无损；上游 Evidence/Learning/Synthesis refs/state/version/hash 可解析且一致。Reviewer 的关注等级或未采纳 concern 不阻塞；只有既定机械合同缺口才 `NOT_READY`。
- Gate 只输出 `READY`（自动进入 Product Decision）或 `NOT_READY`（exact unmet condition + deterministic repair target），不打分、不增加确认/UI。普通 Unknown/证据不足可透明携带，由 Product Decision 选择 Research/Experiment/Wait/Stop/Commit；Problem Ready 不绑定尚未选择的 action，也不检查 PRD、研发、上线或发布 Ready。Product Decision 是正常 Discovery/Product 路径唯一固定的人类语义责任点，且明确自然语言 choice 不再追加确认 UI。
- `product.decision` 作为一个独立可恢复节点运行；AI Brief、按需 adversarial/domain Review、Owner 讨论/挑战、Owner choice 和 deterministic route 都是内部能力而非五个 Graph Nodes。Draft/checkpoint 可跨会话恢复但不产生正式决定；Agent 给首选建议，material 时才补最强反方；Owner 明确选择后才生成 final Decision Record，Controller 才写 route。普通场景不因架构存在 Review 能力而全量 fan-out。五种 outcome 和三种 activation 的 human view 均有中文结论句、why、判断边界、next consequence/action 与 change condition，machine code 只作可追溯对照。
- Agent 能从 exact Draft 预填 Decision Record；Owner 默认只确认 chosen decision、applicability scope、最多三个关键理由、最大 Unknown + flip/stop/restart condition、next action + checkpoint/trigger。identity/version/timestamp、exact Problem/Evidence/Knowledge/Review refs、recommendation/result、supersession、downstream 和 rationale/audit refs 由系统自动维护；只有 material recommendation/choice 分歧才额外显示 disagreement + Owner reason。
- 五种 outcome 共用一个 Record。每次只生成 chosen outcome 对应的 `outcome_details`：STOP 有 restart condition，WAIT 有 why-not-now + review time/trigger，RESEARCH 有 decision question + sufficient evidence + research stop，EXPERIMENT 有 key unknown + exposure/risk boundary + result mapping，COMMIT 有 activation + 必要 time/trigger/recheck + stop/review condition。未选项无空字段；详细 Experiment/Planning 合同只在下游生成。
- Product Decision 先识别一个当前 MVU，再给出一个首选而非五项菜单：离线/既有来源可可靠回答时首选 RESEARCH，答案必须来自真实行为且 action 可控可测可停可回滚时首选 EXPERIMENT，核心价值/方向证据已足够且 remaining Unknown 只影响实现、团队接受长期责任时才首选 COMMIT。Decision Brief 同时说明为何不选最相近替代、翻转条件和下一步；不得使用固定总分或用多个认知 lens 的一致来提高 Evidence confidence。
- STOP、WAIT 与未来承诺严格分开：STOP 结束当前主动方向，WAIT 必须有 review window/trigger 且不承诺，已经决定未来做必须是 `COMMIT + SCHEDULED / CONDITION_TRIGGERED`。STOP/WAIT 进入 immutable Ledger；只有新信息命中 restart/recheck、关键假设或 material risk/opportunity 才主动重审。维持只追加 review result，改判新建 `supersedes` Record；不得删除历史、无期限 WAIT、自动推翻或全量周期提醒。
- R0—R3 由 Agent 只针对拟议 action/exposure 条件化分类：STOP/WAIT 通常不展示，涉及真实用户/敏感数据/外部沟通的 RESEARCH 才分类，EXPERIMENT/COMMIT 必须分类。同一问题在内部原型、小流量和全量执行可以得到不同级别；`RISK_PENDING` 不自动降级，Human View 仅在影响下一步时展示等级、原因与后续约束。R3 允许继续 Product Planning/PRD，但危险动作不得绕过专业 Owner/Gate。
- `new/resume interaction=no-pm-interview` 可在启动/恢复时设置；访谈中 `$better-product-graph interview skip [run_id]` 立即停止当前未回答和后续 PM 访谈，`interview resume` 或 `interaction=guided` 从最高价值未解决 PM-only unknown 恢复。唯一公开 Skill 现在有十一个 intent words；skip 不表示 Evidence 足够、不能跳过 Decision/Ready/外部授权，并必须记录 skipped-interview impact。完整 Discovery 默认至少一次实质访谈/等价当前对话，除非无 material PM-only unknown 且继续提问信息增益低，或用户显式 skip；`NON_INTERACTIVE` 仍 unsupported。
- 低风险可逆实验可在证据较弱但边界透明时推进，高风险/不可逆动作需要更强证据。Run-local Map 中的稳定新事实只保留为带 exact provenance 的 future Knowledge source candidate；在 Knowledge Maintenance Graph 发布前不成为 canonical Knowledge Snapshot，具体提交合同仍延后。
- 模拟 Input Connector 的普通外部 Issue 默认只进入 Signal Inbox，不自动创建完整 Product Run；命中高危 policy 时能提醒/升级，Connector 不可用时人工输入继续运行。
- `INCIDENT_ASSESS` 默认产出 `incident.verification.packet.v1` 线上问题核查包并执行 Engineering Incident Handoff；它明确回答发生了什么、影响多大、研发核查什么。字段不可得时显式 `NOT_AVAILABLE`，严重/持续伤害时不因缺少完整文档而延迟交接；研发结论以同一 Packet 新版本追加。默认没有 PRD、专业 Reviewer/Optimizer 或重型 Ready，只有确需产品判断时才开启受风险约束的 Incident Product Response。
- `BUG_BASELINE_CHECK` 产出 `bug.baseline.assessment.v1`，基线覆盖 Decision/PRD/AC/设计/API 合同/对外承诺/历史行为及版本、边界、冲突、置信度和 superseded 状态；一级 `cause_class` 只有三种，`surface_tags` 不参与业务分流。
- `IMPLEMENTATION_DEVIATION` 只生成 `bug.fix.brief.v1` 和轻量 Engineering Handoff，不生成 Plan/PRD/默认 Reviewer Loop；`PRODUCT_LOGIC_DEFECT` 生成 superseding Decision 与新 versioned change PRD；`SPEC_AMBIGUITY` 返回 Discovery/Product Decision。严重/持续伤害先 Incident。
- Bug Fix Brief 有确切 baseline refs、expected/actual、恢复边界、non-goals、AC、回归面、测试/Eval、依赖/风险/Owner/目标；来自 Incident Packet 的重复事实只引用/追加视图。确定性 Bug 可标记 `NOT_NEEDED`，非确定性 AI/推荐/搜索/排序 Bug 有 Bug Eval Pack。
- Product Decision 的 `STOP / WAIT / RESEARCH` 能作为有审计记录的正式终点；`EXPERIMENT` 与 `COMMIT + NOW` 都创建同一种 Product Plan Run，但前者携带非长期承诺的实验 intent，后者形成正式产品承诺；`COMMIT + SCHEDULED / CONDITION_TRIGGERED` 只形成 committed Roadmap，`WAIT` 最多形成 exploring/candidate Item。
- Product Plan 在功能清单前明确 Target Operating Outcome、Observable Evidence、Non-sacrificable Guardrails 和 Current Iteration Outcome；PRD 另行明确 PRD Increment / Increment Contribution。
- 组织授权与 epistemic confidence 分开记录；Sponsor-directed / accepted-risk 决定不会把低置信度主张升级为事实。
- 每个产品决定至少形成符合 §10.3.1 与 §10.3.3 的紧凑 Decision Record；material disagreement 另按 §10.3.2。Owner 确认后 Record immutable/versioned，任何 material 改判以新版本 supersede 旧版。重大或跨产物决定再按 materiality/risk 扩展备选、Review、Roadmap/Product Changelog Proposal 和 Impact List，微小决定不会被迫走同等重量流程。
- material Agent–Owner disagreement 中，Agent 先给首选并进行一次 evidence/risk-based challenge；有权 Owner 仍可选择不同 outcome。Record 保留双方理由、authorization、accepted uncertainty/risk、recheck/stop 与 execution constraints，但授权不改变 epistemic confidence。可逆可测且证据弱时 Agent 优先建议 EXPERIMENT；低置信 COMMIT 不得被渲染成已验证，R3 约束持续传递到专业执行 Gate。
- Decision 节点结束不经过第二个 Ready 流程：State Controller 对 exact confirmation/Record、五种 outcome、通用/条件字段、必要 risk/constraints、current upstream/history refs 和 disagreement/accepted risk 重算。满足时按 STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT 确定性路由；不满足时保持当前 Decision，并返回大白话 unmet condition + repair target，不打分、不重复 Owner 确认。
- Decision Ledger、Roadmap Registry、Product Changelog 与 Audit Log 能分别回答决定依据、承诺阶段、产品意义变化和执行事实；任一项缺失时不能用另一项推断替代。
- 每个正式 Decision（含 `STOP`）都进入 append-only/versioned Ledger；Roadmap 只收未来行动。新 STOP 通常不建 Item、WAIT 不承诺、RESEARCH 默认进入 Research Request、EXPERIMENT 激活同一 Product Pipeline但不是 committed product、COMMIT+NOW 仅在真实 Plan Run 后 `in_progress`，非 NOW 只 `committed`。一期没有 Experiment Portfolio 真源。Product Changelog 只覆盖 material 产品意义变化并可追溯 source refs，Audit 自动保留 actor/version/action/state/receipt。
- KMG 未接入时，本地 Decision/Roadmap/Changelog/Audit records 足以完成 BPG 本地 Run，且不会伪称团队已共享/canonical 发布；未来接入后，KMG 只负责共享、治理和发布，不重新替 Owner 选择 outcome。具体提交、确认和影响同步合同仍待 Knowledge Requirements 反推。
- 新 Signal 继续从四个 Router destination 中选择，同时以 `existing_links` 绑定 exact historical Decision/Roadmap/PRD。支持性与 non-material Evidence 只追加 link/摘要；挑战关键假设时一屏提醒并给首选建议；命中 kill/recheck/material risk 时只约束 exact affected actions。旧 Decision 不可覆盖，改判创建 superseding Decision；Impact List 逐项区分 `UNAFFECTED / REVIEW_REQUIRED / INVALIDATED / PAUSED / WAITING_DECISION`。
- G01 能按风险、授权、可逆性和可测量性接受多个条件式结果，而不是匹配唯一标签；三条销售询问不会被外推成普遍用户事实，被测 Agent 无法读取 evaluator 的 expected envelope / rubric。
- G03 能完整重建跨 Decision/PRD/AC/设计/合同/历史行为的当前基线，给出有依据的一级分类与首选建议；满足五项证据条件时 Controller 自动分流，冲突/PM-only事实/material路线差异或 override 时才最小澄清。Junior PM 的“直接修”不能覆盖基线证据，被测 Agent 无法读取 evaluator 的 expected envelope / rubric。
- G04 不把带方案的单条反馈复制成 PRD 或外推为普遍事实；Agent 先检索可得信息并形成 Problem Evidence Map，以 most valuable unknown 驱动 Map 迭代或具体 Evidence Request，只问能改变决定的问题。发生 PM 打断时完整执行六步协议、提供不诱导的 Junior PM 脚手架、最多一次最高价值挑战，并给出首选建议与最强反方；继续问答价值较低时按风险/可逆性转研究或实验。被测 Agent 无法读取 evaluator 的 expected envelope / rubric。
- 一期 Golden Suite 以 G01 + G03 + G04 覆盖 Idea、用户反馈、线上 Issue 三类入口以及通用/C 端判断、线上行为、快速实验和 Bug 路由；没有 G02 企业定制 Case 不影响一期验收结果，也不以继续增加 Case 数量作为通过条件。
- 当一个局部指标提升会损害已声明 Guardrail 或整体运行结果时，Product Review 能阻止其凭局部收益通过。
- Product Planning 不从 v0 直接切 PRD：高价值/高风险/高依赖部分先逐块深化，每轮回到 Target Operating Outcome 做 global reconciliation；material 变化形成 immutable version/checkpoint、changelog/supersedes/impact。并行 sub-agents 只读同一 exact snapshot 并返回 Findings/Proposals，由主 Agent 保留分歧后统一整合；已有稳定 Plan 的小改动只 deep-review affected area 并做 global impact check。
- Planning Refinement 在可恢复 `product.planning` 内部运行并产生 versioned checkpoints/stable Plan Candidate；formal Review–Optimize 只审 exact frozen Candidate，独立 Reviewer sub-agents 只写 Finding/Verdict，Optimizer/主 Agent 才能生成新 Candidate。局部表达问题定向修复/复审，结构问题回最近 Refinement checkpoint/global reconcile，Decision/Problem 失效回对应上游；Review 已完成/不可用已披露、Finding 均有 disposition 并完成确定性收尾后才进入既有 Plan Ready。探索期 partial review 永远 advisory；`product-plan / prd` 复用同一 engine 合同但使用各自 profile/rubric，实验 intent 只条件化 PRD rubric。
- Business Router 与 Planning Profile Selector 可被审计地区分；Agent 不在 Signal Intake 永久锁档，也不让 PM 填复杂度问卷。LIGHT 在一次内联 pass 保留目标/Evidence/Assumption/验收/风险/追溯，STANDARD 使用有界 Rounds，PROJECT_SCALE 只在需要时使用 Waves；新依赖/风险可触发升档，范围收敛可受审计降档。一个父 Plan 的 Wave 不成为全项目 Plan/PRD Runs（含实验 intent）的并发锁。
- `plan.slice` 从 exact Module/Iteration/Dependency 视角先提出 PRD Candidate Slice Map/List；候选含目标/问题、用户结果、阶段、模块、依赖、验证和拆分理由。端到端结果可以跨模块，Matrix 不按格生成 PRD，前端/后端/API 不被包装成独立产品 PRD；Agent 先建议，只在 material 切分取舍时询问 PM。
- `plan.coverage.validate` 能区分遗漏、重复/冲突、端到端体验断层、依赖和上游一致性，并让本轮、后续、Experiment、等待、不做和 unresolved 都有显式 disposition。LIGHT 内联、STANDARD 简表、PROJECT_SCALE 可用只读 sub-agent；Finding 只诊断，不静默改 Plan或自动 BLOCK。
- `plan.reconcile` 把 Coverage/局部深化/新 Evidence Finding 放回整体结果协调；非语义补漏/依赖/重复/引用可自动生成新 checkpoint，改变目标用户、核心目标、做不做、重要优先级/时间、风险承担、Roadmap 承诺或 Experiment/Commit 边界时必须给 Owner 展示发现→Decision 影响→建议→不改后果。切片/迭代/Decision/Problem 根因分别返回正确上游，显式未解决冲突包含风险承担者和复查条件。
- 固定 `plan.owner.confirm` 已移除。一页 Plan 摘要按需同源渲染，不是审批；忠实模块/迭代/依赖/切片展开由 Agent 自动完成。只有超出 exact Decision 的 material 产品取舍才从 Planning 返回同一 `product.decision`。程序化 `plan.ready.gate` 只重算 current exact Plan、Coverage/dispositions、advisory Review finalize、依赖/冲突和所有 material Decision refs，并对 unmet condition 给 deterministic repair target；PASS 只为当前 activated+eligible slices 创建 PRD Runs。
- PRD Run 启动时，后台 `prd.workspace.initialize` 只创建 workspace、绑定 exact refs、登记状态/版本并准备 `archived/released`；Graph/human flow 不把它渲染为“程序创建/编写 PRD”的智能节点。一个可恢复 `prd.generate` Agent 节点通常在同一 attempt 连续执行 `prd.content.build → template.resolve → prd.render` 并把首个 versioned candidate 写入 `archived/`。Review subagents 只读审查，Optimizer/Agent 修订，Controller 只做版本、证据与发布状态检查；Owner 只处理 material 上游判断、专业授权或 Connector 副作用权限，不固定确认每份 PRD。
- `template.resolve` 能按“项目显式配置 > 受信项目知识 > BPG 配置的当前 fallback/default”确定 exact Template Profile；可确定时不问 PM，只有冲突且有效性不可判定时一次询问。当前 fallback 精确解析 `references/upstream-skills/better-product-plan/references/product-prd-template.md`；general v0.1 仍是 Draft/Bootstrap 候选。无论选择哪份模板，都验证父 Plan/Slice/Decision refs、当前增量贡献、Confirmed/Assumption/Unknown/Verify、Shared Contract/跨 PRD 依赖、Evals refs 和版本/Review/release 状态的 mapping 或约定扩展。
- 模板缺字段时能进入 Profile 扩展/附录或明确 `TEMPLATE_INCOMPATIBLE`，不静默丢失；Agent 不为填模板编造 OKR、埋点 ID、性能指标或 Owner，会改变方案的缺口返回 Planning/Decision。领域无关 general 模板只有在人审通过后才成为默认，项目专属 Futu/moomoo/象象银行/券商/投教/监管 checklist 不得被硬编码为通用必填；frontend/backend/service Profiles 不属于一期验收。
- 简单 PRD Run 不生成一份与 PRD 同等完整的独立 Product Spec；只有配置命中跨会话、多模板、多 Agent 分章节、重大模板迁移或语义/表达故障隔离时才保存 versioned internal content checkpoint，并证明它不能独立 Handoff、不能进入 `released/` 或成为第二正式需求。
- PRD Candidate 的首轮 Product Review 能逐项证明其忠实于 exact Decision/Plan/Slice/Knowledge/Evidence/constraints：发现 scope creep、future 偷带、新产品规则、虚构事实/指标/OKR/Ground Truth、Assumption/Unknown 升级、Guardrail/依赖/共享合同/回滚/Eval 遗漏、上游冲突或无依据扩展用户/市场/平台时形成 Finding 和最早 repair path。非 material 清晰化及已确认规则的场景/分支/异常/AC 展开可在当前 PRD 修复；material 新内容必须删除/标 Proposal 并返回 Plan/Slice/Decision/Learning。
- 同一 frozen Candidate 的 Product/Engineering/Testability 逻辑角色读取相同 Goal Fidelity Review Packet，首轮结论相互隔离；LIGHT 可以合并为较少 sub-agent，但目标忠实 profile 必须留下独立 role/profile 输出。按风险加入 UX/Domain/AI Behavior/Security/Privacy/Compliance，未命中角色有明确 deferred reason，不为 panel 完整默认全量 fan-out。
- Findings 能以 `confirmed/complemented/conflicted/unique/unsupported` 保留支持、补充和分歧；每个非空 `confidence` 都有简短、可解析的 `confidence_basis`，且不使用模型自信、Reviewer 数量或多数一致抬高等级。CRITICAL 偏离不被多个小项 PASS 抵消，无依据功能建议保持 future lead。触发高影响复核时只审目标项，默认一轮、最多两轮；Review Human View 只给直白行动结果，不显示百分比/A—F。
- `review.aggregate` 能从部分到达处恢复，但只有 required 首轮齐全/明确失败、所有有效结果绑定同一 frozen Candidate/Goal Packet、每个原 Finding 都有无损处置时才可完成。late/stale 不混入新版，disagreement/unsupported lead 不被静默删除；输出复用 Review Record/review_summary/Finding/Verdict/Disposition，不生成新 Candidate 或 Ready。
- `review.finalize` 对同一 exact Aggregate/Candidate/rules 必须产生同一审查收尾结果：适用 Review attempt 完成或不可用已披露，每个 Finding 有 disposition，所有 refs 绑定当前 Candidate，同源内审意见版本一致。它不裁决专业观点、不要求 Reviewer PASS、不因 concern level 阻塞，也不把外置审核写成已通过；需要采纳的 current-PRD 修改先进入 optimize，上游问题回最早修复点，其余透明关注随同 release。
- `prd.optimize` 只接受绑定 exact Candidate 且允许 current-PRD repair 的 Aggregate Findings；一轮只产生一个批量修订 Candidate，可回放 finding→change、未修项/理由、stale/re-review scope，且只由后续 Reviewer 宣布正式 repair status。无内容变化的新 Reviewer/复核只新增 Review Attempt，不增 PRD 文件；轮次按“批量 Finding→一 Candidate→一次复审”计数，到上限或连续两轮无 material progress 时不自动 PASS，而是保存恢复点并回正确上游/WAIT。
- Optimizer 新版用 `FIXED / IMPROVED_BUT_OPEN / PERSISTENT / REGRESSED / INSUFFICIENT_EVIDENCE` 回写旧 Finding，delta re-review 同时回归目标/范围/Guardrail/Shared Contract/AC/Eval。不连续机械重写；连续两轮无 material progress 时停止、保留 concern/disposition，并路由正确上游或交外置团队判断。
- 一个父 Plan Run 能产生三个不同状态的 PRD Runs。
- 每份 Ready PRD 生成一个可独立复制/交付的 self-contained release directory：目录与主 Markdown 同 stem，Markdown 只相对引用本目录 `./assets/...`；无附件不建空目录，共享可变 package-root assets 不得被 release 引用。
- `prd.ready.gate` 只有六类一期必要检查：current exact Candidate；适用 Review/`review.finalize` 与同源内审意见绑定同版本且记录完整；Decision/Plan/Slice/Knowledge/Evidence 等关键 refs current/non-stale；`REQUIRED` Eval Pack 已按 policy 履行；Template/Document Experience/version record/`DOCUMENT_CHANGELOG.md` 机械通过；既定必填合同/Validator 无机械缺口。合法 `N/A+理由` 不因填满率失败；同 exact inputs/rules 必须同结果。未解决 advisory concern 必须披露，但本身不是 NOT_READY 条件。
- `prd.ready.gate` 不读取 `prd.owner.confirm_understanding` 或 `handoff.owner.approve` 作为前置，不重做语义 Review，也不要求外置组织审批、Connector/外部写入授权、派生 export、研发/测试完成、advisory 全关闭或百分比分数。`NOT_READY` 列 exact unmet + affected ref/version/finding + repair target + resume point；`READY` 自动生成 immutable self-contained release，该目录即本地 Handoff 单元。按需一页最终摘要绑定同一 source，用户未打开它不阻塞 Ready；BPG Released 不被呈现为外置组织审批通过。
- 每个 Connector+Target 默认 `manual`，只有 exact versioned preauthorization 才可 `auto_when_ready`；`disabled` 不发送。Dispatch 幂等 identity 绑定 PRD ID+Release+Connector+Target+Action；UNKNOWN 必须 query/reconcile，不能盲重试。多目标复用同一 canonical release 并保留独立 attempt/receipt；没有可验证 receipt 只能说本地完成/可发送/结果未知，不能声称 `SENT/IMPORTED/RECEIVED/ACCEPTED/APPROVED`。
- `artifacts/prds/archived/` 保留 immutable self-contained material Candidate directories，`artifacts/prds/released/` 保留全部 self-contained 正式版本；每轮 Review/Optimize 的 Candidate、review refs、delta 和 supersedes 可回放。Ready 后只能从 exact Candidate 生成 release，Handoff 绑定 exact directory/Markdown/assets hashes；旧 release 失效或被取代后仍可审计。同 stem DOCX/PDF/ZIP 是按需派生，不是 canonical truth 或 Ready 前置。
- `product_plan / prd / decision / incident / bug_fix / handoff / audit / internal_review` 八个一期 Profile 能由已有节点调用同一 Renderer/Validator；每个 Human View 头部都有 exact `source_artifact_ref/hash`、`policy_version`、`profile_id`、`profile_version`、`template_version` 和 `rendered_at`，source 变化后自动 stale 并重渲染。`product_plan` 必须至少稳定渲染 Plan Ready 一页摘要，`internal_review` 必须与 exact PRD version 同源绑定。
- PRD/重大 Decision 可以按需经过 Readability Reviewer；Incident/Bug 保持最小行动性检查，纯 machine record 能按权限 on-demand 解释而不改写原 JSON/YAML。未实现 `evidence/review_summary` 或 `product_plan` 其他完整展示模板不阻止一期验收。
- PRD 数量、字段填满率、Signal-to-PRD 转换率、提问数量或单纯处理速度都不能单独使 Run 或 Ready Gate 通过。

### 24.2 强制执行

- Host 对 HOME、工作区集合根或未解析的广泛目录执行 `git init`，在已有父级 repository/worktree 内创建嵌套 repo，未先应用 `.gitignore`/敏感边界就 add/commit，或把 init 冒充 commit/push/remote 成功时失败。并行写入任务共用主 worktree、绕过主 Agent diff review，或为每个节点/对话制造 commit，也失败。
- `$better-product-graph handoff` 只能 prepare/validate/display；缺 Ready 或 Connector side-effect policy/授权时不得 dispatch，但不得把缺外部写权限说成 PRD 内容未批准。`connectors` 对未配置的一期 Input Connector 必须返回 `NOT_AVAILABLE`，不能伪造可用能力。
- `$better-product-graph audit` 必须只读、按权限过滤并引用已保存 Record/Event；试图写状态、触发 reroute、暴露/补写隐藏 chain-of-thought 或事后编造结构化理由时失败。
- 把后台 `prd.workspace.initialize` 与 `prd.generate` 同等呈现为会创作 PRD 的 Agent Node，或 Controller 在初始化/保存/校验时生成、判断、改写 PRD 语义，失败。反过来由 Agent 绕过 Controller 自建目录、覆盖已引用版本、移动 current/released 指针、自报 Review/Ready 完成或并发写正式产物，也失败；同一 Run 若发生两次初始化或两条不一致状态同样失败。
- 把 `prd.content.build / template.resolve / prd.render` 注册为三个用户可见节点、增加三次 HITL，或让简单 Run 同时生成完整 Product Spec 与内容重复的 PRD，失败。Template Profile 选择跳过更高优先级 exact 配置、可确定时仍询问 PM、未声明必要语义 mapping、无法承载却静默丢字段、为填模板编造 OKR/埋点/性能/Owner、可选 content checkpoint 被单独发布/Handoff，或把项目专属券商/投教 checklist 提升为所有项目通用 Gate，也失败。
- `review.parallel` 让各 Reviewer 读取不同/mutable Candidate 或不同目标基准、首轮互看结论、Reviewer 写 Candidate/state、主 Agent 在 required 首轮完成前开始 aggregate，或用多数票/模型数量提升 Evidence confidence，均失败。LIGHT 省略目标忠实检查、所有 PRD 默认全量专业 panel，或把一个逻辑 role 强制等同一个 sub-agent，也不符合自适应合同。
- Aggregate 静默丢 Finding/分歧，错并不同问题，把全部建议塞进 PRD 或把 unsupported lead 升级为当前修复，读取不同/可变 Candidate，在 required 首轮未齐前完成，或修改 Candidate/state/声称 Ready，均失败。Controller 用确定性规则裁决专业观点，或主 Agent 绕过 Controller 自行写 aggregate completion/state，也失败。
- `review.finalize` 丢失 Finding/disposition、把 stale/mismatched Review 绑定当前 Candidate、未生成同源内审意见却声称完成、以 Reviewer concern level/数量阻塞，或把外置审核写成“已批准”，均失败。Finalize 裁决专业观点、修改 Candidate、自报 Ready，或把自己重新实现成 `review.gate`/人工步骤/业务 Node，也失败。
- `prd.optimize` 绕过 Aggregate disposition 修上游问题，顺手新增无依据功能/用户/平台/商业模式/范围，用文案润色掩盖结构缺陷，自报 Finding `FIXED`/PASS/Ready，或让 subagents 并发写正式 Candidate，均失败。每条 Finding/微编辑/无内容变化复审都生成 PRD 文件，一轮生成多个 Candidate，把 Review Attempt 复制成 PRD，新建 `working/`，或通过改名/重启绕过 2/3/4 轮和两轮 no-progress，也失败。
- Finding 缺 exact evidence/upstream commitment/affected scope/repair target，Severity 只有数字或未解释行动影响，`unsupported` 建议被自动写入当前 PRD，CRITICAL Goal/Scope 偏离被多个 LOW PASS 抵消，或冲突在 aggregate 中消失，均失败。
- 每份 PRD 重跑 Product Goal-Based Audit 完整七阶段、重新要求 Owner 确认目标、设置 95%/80% 覆盖率、计算百分比分/A—F、创建 `.product-audit` 文件套件/默认 Shell 脚本、所有 Finding 强制双审、每轮人工确认或无限优化，均属于过度吸收。review-of-review 超过两轮、无触发仍全量复审，或连续两轮无 progress 仍只改措辞，同样失败。
- 把 general Template Draft 冒充已经完成质量验证的冻结模板，或一期提前建设 frontend/backend/service 模板库、Template Adapter/Router/新节点，失败。当前 default/fallback 必须由 exact versioned 配置决定，并允许未来升级、pin 与回滚；具体 promotion 流程留 Roadmap。PRD 目录/主文件必须遵守已确认的同 stem 命名模式，但不得把示例中的具体 PRD ID、短标题、日期或 v0.x/v1.x 数值硬编码成唯一合法值。
- 问题假设审视在深入访谈前要求 PM 先回答，未先还原原话，或把 PM 转述/判断、Sponsor 授权、Agent inference 当成用户事实时失败；把用户/PM 方案直接当作问题、把组织授权提升为用户价值证据、强制制造无证据反方，或保存/暴露 hidden Chain-of-Thought 时同样失败。
- `problem.assumption.audit` 使用固定几十项假设 checklist 代替动态判断，输出十几个同权假设/MVU/问题而不选择 exactly one MVU，未推荐最合适的信息来源，只写“继续调研”，或自己采访 PM 而不是把明确请求交给后续 Learning Loop 时失败。
- Assumption checkpoint 把“可信认知起点”宣称为最终本质问题、Problem Definition 或 Problem Ready，或遗漏现象/影响/问题假设/期望结果/提出方案中的已知与 unknown 边界时失败。
- `problem.assumption.audit` 直接写 Route/State/canonical knowledge、生成 Problem Definition/Product Decision、调用独立 Reviewer/Evaluator Loop/Ready Gate，或把内部 checkpoint 当作正式业务 Artifact/Handoff 时失败。
- Assumption checkpoint 被原位覆盖、缺 exact input refs/hash/structured rationale，普通补证触发无意义全量重跑，material reframe 却复用旧 checkpoint，或 `ROUTE_REEVALUATION_RECOMMENDED` 被当成实际 reroute 而没有新 Route Record 时失败。
- Incident 或已确认 `IMPLEMENTATION_DEVIATION` 被强制送入问题假设审视，或节点因产品分歧直接硬阻塞而不允许后续补证/可逆实验建议时失败。
- Learning Loop 把 PM 当默认搜索框、把 AI 可查的知识/历史/数据/外部资料交给 PM，要求 PM 猜专业 Owner 或用户才能回答的事实，或未记录七类 `source_resolution_type` 与选择依据时失败。
- 打断 PM 前没有当前判断、证据边界、提问必要性、Agent 首选建议和答案影响，跨多个 MVU 批量倾倒问题，或用固定题数替代信息价值判断时失败。PM 回答“不知道”后继续逼猜，而不是保留 Unknown 并转正确 Evidence Request，也失败。
- PM 访谈退化为需求问卷，只说“收到”而不更新判断，把选项和责任甩给 Junior PM，用示例/选项诱导预期答案，或不给清楚首选、理由与最强反方时失败。回答后连续挑战、无限追问“为什么”，或者没有可信反证仍强行抬杠，也失败。
- 挑战强度按 PM 资历一刀切，而不是依据风险、证据冲突和可逆性；Cognitive Router 堆叠多个同义镜头伪造更高置信度；Better Question 被注册成新 Node、固定问卷或 checklist，均失败。
- 默认运行自动套用 Journey Map/KANO 等模板、没有五问记录却升级 Level、required inputs 缺失时编造用户阶段/情绪/偏好，或把方法输出当 Evidence/事实时失败。多个方法结论一致不能提升 evidence confidence。
- PM 点名方法后 Agent 明知不适用仍机械执行，只列方法名不说明 information gain/decision impact，或每轮堆叠多个主方法却不说明不同增量时失败。把 Hook/Method Card 实现成新 Router/Registry/Service/Runtime/Graph Node/Gate/公开命令，或把具体方法列为一期核心验收依赖，也失败。
- PM 坚持后未记录 Agent/PM 判断、分歧、证据、authority、风险及验证/重审/回滚条件，继续无限争辩，或允许无权者靠坚持改变正式决定时失败。已满足停止条件却继续采访，或由 Learning Loop 直接创建/授权实验，也失败。
- Learning Round 默认永久保存全量逐字对话、保存 hidden Chain-of-Thought，或反过来没有保存 interrupt reason、MVU、问题/claim type、挑战、Agent 建议/反方、agreement/disagreement、假设变化与 next action 的最小可审计记录时失败。
- PM/Sponsor claim 与证据冲突时静默迎合，把授权升级为 user-value evidence；或反过来由 advisory Reviewer/Agent 用自己的意见硬阻塞，均失败。受限实验若被建议，必须明确缩小范围、指标、kill criteria 和回滚，不能用“老板批准”省略安全边界。
- `problem.learning.loop` 被实现为不可恢复的一次长 Prompt，等待外部证据后重做已完成 Round，Evidence Request 被注册为顶层 Graph Node，或 Round 未保存新增证据、假设/frame/建议/MVU 变化与继续/停止理由时失败。保存 hidden Chain-of-Thought、要求清空所有 Unknown 才停止，或由 Loop 直接创建/授权 Experiment，也失败。
- `WAITING_FOR_EVIDENCE` 未绑定确切 Evidence Request、Round 和 Map 版本，恢复后把旧 Map 原位覆盖，或把它限制为 human evidence，均失败。请求到期/不可得时丢弃 Unknown 并假装完成也失败。
- 把 runtime status、completion disposition 和 next-action recommendation 合成一个 Exit 字段，在 `ACTIVE / WAITING / PAUSED` 时写 completion disposition，或在 `COMPLETED` 时缺 disposition，均失败。旧五项候选 Exit 被重新作为活动枚举也失败。
- `READY_FOR_SYNTHESIS` 被解释成统一 Problem Ready、Product Decision 或 COMMIT 授权，Synthesis 为显得完整而删除 Unknown，或低风险 Research/Experiment scope 的充分性被复用于更高风险/不可逆行动时失败。
- `problem.synthesize` 接受 `ACTIVE / WAITING_FOR_EVIDENCE / PAUSED` 或非 `READY_FOR_SYNTHESIS` 输入，从 `latest/current` 推断 source，继续搜索/完整访谈，补写不存在的 Evidence，删除 Unknown，或自行选择产品行动/方案时失败。Candidate 被冒充 canonical Knowledge、Decision、Plan、PRD、solution、Quality Review 或 Problem Ready 也失败。
- 已发现会改变方向的 material gap 却仍返回 `COMPLETED`，或 `RETURN_TO_LEARNING` 缺 material gap、exactly one 新 MVU 和结构化原因时失败；返回事件不得直接篡改旧 Learning State 或声称新 Learning Round 已发生。source 变化后继续复用 stale Candidate、原位覆盖旧 Candidate，或下游引用可变 `current/latest` 而非 exact Candidate version/hash，同样失败。
- Product Quality Reviewer 与生成者共享未隔离会话、读取 `latest/current`、编辑 Candidate、代签 Owner、直接写 State/Ready，或把外部模型名称当作可信保证时失败；同一模型不是失败，但必须有独立 attempt、专门 Skill、exact inputs 和隔离上下文。
- Problem Quality Review 漏查用户/场景/目标/阻碍/影响、方案偷渡、Evidence 追溯、范围/因果、反证/替代、Unknown 或 action relevance，Finding 缺 evidence/action scope/repair condition/repair path，或 Reviewer 直接修改 Candidate/route/state 时失败。后续只看 delta 而不回归全局不变量、纯文案循环没有 `NO_PROGRESS`、或向 Junior PM 倾倒 Finding 清单但不给原因和首选建议，也失败。
- 主 Agent 串行重做所有可独立对抗审查却声称使用 sub-agent，并发 attempts 读取不同/mutable snapshot，或任何 sub-agent 并发写 state/current/canonical knowledge/released artifact/外部系统时失败。sub-agent 也不能替代 Owner、Gate 或 side-effect approval。
- Host 把 `BEST_AVAILABLE / BALANCED / FAST` 硬编码为特定供应商/模型、未记录实际 provider/model/version和降级，超出 fan-out/budget/timeout/retry，required 失败仍放行相关 action，或 optional 失败阻塞无关路径时失败。aggregate 用多数票抹掉分歧、多个 Agent 同意便提升 Evidence confidence，或保存 hidden CoT，同样失败。
- 当前操作者没有匹配的项目配置/Host identity 却被当作 Product Decision Owner，Agent/subagent 代替 Owner choice，或 `NO_PM_INTERVIEW` 被用于跳过 Product Decision，均失败。反过来，在 Problem、Plan、PRD、Handoff 再增加固定内容确认，同样违反 HITL 精简。
- BPG 的 Product Decision、Ready/Released 或内部 Review 被呈现为最终组织审批通过，或内部重复实现外置会签/升级流程，均失败。Handoff 必须携带 exact Decision/Plan/PRD/Review/Ready/material refs 供外置汇总审批使用，但不复制新的确认记录。
- 以 LLM/subagent 的“看起来通过”代替程序化 `problem.ready.gate`，Controller 读取可变指针、同输入/规则版本得到不同状态迁移、未原子写 state/audit，或把主观判断硬编码为无来源布尔值时失败。Gate 重新做语义审查/评分/审批、增加第二次确认，把普通 Unknown 自动阻塞，或提前检查 action/PRD/研发/上线/发布 Ready，也失败。`NOT_READY` 缺 exact unmet condition/repair target，Agent 模拟原型未标 `ADVISORY_ONLY`，或未经过程序化重算就正式 Handoff，同样失败。
- 把 AI Brief、风险审查、选项比较、挑战、Owner 确认或 route 分别注册为串行 Graph Nodes，或反过来把 `product.decision` 做成无法暂停恢复的一次巨型 Prompt，均失败。默认全量调用 Reviewer、Agent 只列选项不给首选、material 反方被隐藏、非 material 场景为模板完整强造反方、Draft/Reviewer 替 Owner 选择、Owner choice 未冻结 exact Decision Record 就路由，或 Agent/subagent 直接写正式 route，也失败。
- Decision Brief、交互、Decision Record 摘要或 Handoff 只显示 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT / NOW / SCHEDULED / CONDITION_TRIGGERED` 裸 code，缺中文结论、why、最大 unknown/反方、下一步或改判条件时，`document.experience.validate` 必须失败。Renderer 另存或手改一份“人话决定”、翻译改变 machine outcome，或 Agent 只抛五个按钮让 Owner 自己猜含义，也失败。
- Owner 被要求手填 identity、版本、exact refs、supersession、downstream 或 audit 元数据，确认页在无必要时超出通用五项，material Agent/Owner 分歧被隐藏，或无分歧时仍强制生成 disagreement/Owner reason，均不符合 Decision Record 最小合同。默认视图倾倒完整 cognitive report、没有渐进展开，或反过来借“一屏”隐藏重大风险，也失败。
- material disagreement 时 Agent 没有首选、只问“确定吗”、静默迎合，或在一次实质挑战后仍无限争论/阻塞有权 Owner，均失败。Record 缺双方理由/authorization/accepted uncertainty-risk/recheck-stop，把 sponsor-directed 授权写成高 epistemic confidence/用户价值证据，或为了表达分歧新增 `OVERRIDE / SPONSOR_COMMIT` outcome/node，也失败。R3 constraint 被普通 Product Owner 的坚持清除，或未随 Plan/PRD/Handoff 传递时同样失败。
- 新增 `decision.ready`、Decision Ready Gate/Artifact/Reviewer/重复 Owner confirm，或 Agent 自报完成后绕过 Controller 路由，均失败。transition validation 只返回裸 `NOT_READY`/分数、不列 exact unmet condition + repair target，失败后错误退出当前 Decision/创建下游 Run，或把 Research path、Roadmap 写入/下游 Ready 当作已在此验证，同样失败。
- STOP 缺 restart、WAIT 被写成 committed、RESEARCH 不形成返回 Decision 的后续路径、EXPERIMENT 创建独立 Fast Lane/绕过同一 Planning/PRD Ready/Handoff、`COMMIT + NOW` 未创建 Plan Run，或 SCHEDULED/CONDITION_TRIGGERED 提前创建 Plan Run，均属于 Decision route conformance 失败。
- 为五种 outcome 建五套 Record/节点/模板，生成未选 outcome 的空字段，STOP 无 restart condition/明确无条件，WAIT 无 why-not-now 或复查点，RESEARCH 无充分证据/停止条件，EXPERIMENT 无关键未知/暴露风险边界/结果处置映射，COMMIT 无 activation/停止复查条件，均失败。Decision Record 重复下游 Experiment 指标/Plan/PRD 或 Product Planning 细节也不符合边界。
- Owner 确认后的 Decision Record 被原位覆盖，改判没有新版本和 `supersedes`，Handoff/Audit 从另存“人话决定”而非同一 Record 渲染，或为补 `superseded_by` 修改旧 Record 内容，均失败。
- 把 R0—R3 做成独立节点/Gate、PM 评分表、需求价值分或问题永久标签，均失败。EXPERIMENT/COMMIT 未分类、未知风险默认判 R0/R1、只因实现便宜而降级，或缺失信息并不改变等级/allowed action 却打断用户，也失败。R3 被用于阻止写 PRD/继续规划，或反过来由普通 Product Owner 代专业 Owner 放行真实危险动作，同样失败。
- 任一正式 outcome（尤其 `STOP`）没有进入 Decision Ledger，或用 Audit Event/聊天记录替代 Decision Record，失败。把所有 Decision 复制进 Product Changelog、把新 STOP 强制建成未来 Roadmap、把 WAIT/RESEARCH/EXPERIMENT 记成 committed product、在 Plan Run 创建前把 COMMIT+NOW 标为 `in_progress`，或为 non-NOW COMMIT 提前创建 Plan Run，也失败。
- KMG 未配置就阻止全部本地 Decision/Planning/PRD Run，或把本地 future source candidate 伪装成已共享/canonical receipt，失败。KMG 接入后重新替 Owner 决策、改写原 outcome，或四类视图各存一份可独立修改的事实，同样失败。
- 新 Signal 因命中历史 Decision 而跳过既有 Incident/Bug/Discovery/Inbox destination，或静默改写旧 Decision，失败。普通支持证据频繁打断 Owner、单条 non-material delta 触发全量重跑、material challenge 没有 Agent 首选建议/exact affected artifacts，或不可豁免专业风险被普通 Owner 放行危险动作，也失败。Owner 在 material challenge 下维持原决定却没有理由、accepted uncertainty/risk 和 recheck/stop condition时，影响处置不完整。
- `INSUFFICIENT_TO_PROCEED` 缺已尝试来源、证据缺口、无法继续原因、Agent 建议或 restart condition，却生成 Problem Definition/PRD，均失败。普通授权资料检索被误升级成正式 Research 决策，或 next-action recommendation 自动创建 Research/Experiment，也失败。
- 以“实验可逆”为由忽略测量、范围、kill criteria、伤害护栏或回滚，把 Experiment 当作证据不足逃生口时失败；Experiment recommendation 必须保持 advisory 并返回有权 Product Decision。
- `NO_PM_INTERVIEW` 下仍发出 PM 产品访谈、换措辞重试、静默扩大到项目/其他 Run，或反过来跳过 Product Decision、外部写入授权、Evidence、Ready/风险门槛时失败。高风险缺关键判断却继续推进，或没有展示 Unknown、影响、建议和 allowed/not-allowed actions，也失败。
- `interview skip` 不能在进行中的访谈立即生效、丢失已回答内容、把未回答问题伪造成答案、默认写入项目/用户全局，或 `resume` 机械重放全部旧问题，均失败。系统若把 `interview skip/resume` 拆成多个公开 Skills/平行顶层命令，缺 `INTERACTION_POLICY_CHANGED`/skip 审计，无法恢复 Guided 模式，或把未实现的 `NON_INTERACTIVE` 映射为 `NO_PM_INTERVIEW`，也失败。
- 完整 Discovery 因“简单/赶时间/Agent 自信”自动跳过实质访谈，且无法证明无 material PM-only unknown、继续提问信息增益低，也失败；用户显式 skip、当前对话已等价完成、Incident、可靠 Implementation Deviation 与 status/receipt 路径不被强制制造一次访谈。
- Human View 字段齐全但术语堆叠、结论埋藏或不面向声明 audience 时，确定性 Schema 通过不能替代按 Profile 要求的 Readability finding/disposition；unknown/evidence boundary 被直接省略时 `document.experience.validate` 失败，被流畅文案弱化或误导时 Readability Reviewer 必须提出 finding/condition，不能以“可读”掩盖事实缺口。
- Renderer 把 PM/Owner 授权写成用户事实，或删掉 authorization 与 epistemic confidence 的边界时失败；Readability Reviewer 只能给 finding/advisory/condition，不能自行写 HARD_BLOCK。
- Human View 绑定旧 source hash、旧 policy/profile/template，缺 metadata，或 source/依赖变化后仍标有效时，State Controller 必须在原 Ready/Handoff 迁移中判为 `STALE/INVALID` 并要求重渲染；Agent 不能自行宣布通过。
- Incident 因非关键文风、章节或 `NOT_AVAILABLE` 项被错误阻塞，或 Bug Fix Brief 被 `bug_fix` Profile 强制扩写成 Product Plan/PRD/重型长文时失败；只有缺失会导致错误核查/修复行动的最低理解项才能约束相应 Handoff。
- Run State、Schema、Audit Event 等 machine record 无法按权限生成 on-demand 解释视图，或为此改写/扩写原始 JSON/YAML 时失败。`audit.view` 复制第二份可编辑账本也失败。
- Handoff 人类视图把“本地 release 已完成/可发送/导出已生成”写成“已发送/已导入/已接收/已采用/已批准/已实现/测试通过”，或没有远端/人工可验证 receipt 就提升状态时失败。
- 项目模板删除 Policy 最低理解项、只引用 `current/latest`、或不能承载 `prd` Profile 却跳过现有 Supplement 时失败；项目可以加强 Policy，不能降低 Core minimum。
- Document Experience 被注册为新 Graph Node/Loop/Gate、业务 Artifact、独立 Runtime/Service/MCP/CLI，或 Human View 可脱离 source 手工漂移时，不符合 V1.4 架构。
- 活动 Manifest、合同或 Review Card 仍调用已退役的旧 Evidence 分类节点，或把 Collect/Map 合并后无法独立恢复来源权限失败与语义重算时，不通过 Discovery conformance。
- Collect 把摘要、翻译、推断或 Agent 生成内容伪装成原始证据，缺 provenance/hash/查询范围/权限，或 Map 原位覆盖旧版本时失败。Problem Evidence Map 直接写 canonical knowledge、把 current 指针当历史真源，或 future Knowledge source candidate 缺确切 Map/Evidence refs、范围与冲突时失败。
- Map 只贴“事实/观点”标签而不建立 claim-evidence-conflict-unknown 关系，用裸百分比声称置信度，把 PM 授权/偏好/转述、竞品行为、历史行为或重复同源信号提升为已验证且独立的用户事实时失败。
- 以固定来源数代替行动相关充分性、没有 MVU 就继续漫无目的搜集、把 AI 可检索信息推给 PM、只写“继续调研”而不给具体 Evidence Request，或达到互动预算后强行声称 Problem Ready 时失败。
- 在缺少测量/回滚边界时用“低风险”放行实验，或对高风险/不可逆动作使用与低风险实验相同的弱证据充分性标准时失败；相反，已满足可逆实验最低合同时，不能只因未达到任意来源数量而机械阻塞。
- 用户直接调用内部 Atomic Skill Module、node ID 或底层脚本以跳过当前 Run 节点、Validator/Gate/审批/状态时必须被拒绝并记入 Audit；公开 manifest 导出多个 Skills 或 `$bpg` 等别名也不通过一期 conformance。
- `signal.ingest` 未在同一事务保存原文、来源、权限/敏感性、时间、external ID（如有）和 hash 时不得产生正式 Signal；接收后的原始 artifact 被 `prepare` 改写时完整性检查失败。
- `signal.relate` 判定 duplicate/cluster 时仍保留每条原始 Signal 和来源；删除或无痕合并会触发失败。分类结果不能直接替代受项目 policy 约束的 `route.select`。
- Classifier 为获取 AI 可从授权来源查询的信息而询问 PM、进行价值访谈或写状态时失败；Router 用 `NEEDS_CONTEXT` 追问多个开放问题、追问用户本质/价值问题，增加第五条 destination，或在潜在持续伤害下等待完整信息而不 `INCIDENT_ASSESS` 时失败。
- Classification/Route Record 被原位覆盖、`current-route` 被当成历史真源、INBOX_ONLY 缺 signal-scoped Record，或 re-route/人工 override 未创建带 `supersedes` 的新记录时失败。
- 把 `existing_links` 当作 destination、因关联到已有 Incident 而跳过新证据影响评估、让关联关系参与目的地互斥排序，或用 `ATTACH_EXISTING` 吞掉本次路由时失败。
- PM 可在 Inbox/Discovery 间改路并可把 Bug Baseline 升级到 Discovery；反向改成 Bug Baseline 却没有 candidate baseline/expected-vs-actual 依据，Incident 未完成最低影响评估就被降级，或 override 缺 actor/reason/authority/必要证据时失败。Assessment 可以得出 Spec Ambiguity，但任何 override 都不能跳过 Assessment、五项自动分流证据检查或必要 clarification record。
- `new` 被解释成产品承诺/外部动作授权、Incident Assess 自动执行止损，或 Bug Baseline 在 current baseline、差异、不新增规则、AC、无冲突五项不完整时自动生成 Bug Fix Brief，均失败。
- Assessment 未检查 Decision/PRD/AC/设计/合同/历史行为，缺版本/边界/conflicts/confidence/superseded，新增第四种 cause class，把 `surface_tags` 当路线，或因“前端问题”直接判为实现偏差时失败。
- 无可靠基线仍服从 Junior PM“直接修”、Implementation Deviation 默认创建 Plan/PRD/三 Review、Bug Fix Brief 缺恢复边界/non-goals/AC/回归面，或复制 Incident Packet 事实形成双真源时失败。
- Product Logic Defect 原位覆盖旧 Decision/PRD、未创建 superseding Decision/change PRD，或 Spec Ambiguity 被强行归为实现 Bug 时失败。
- 非确定性 AI/推荐/搜索/排序 Bug 缺 Bug Eval Pack，或无法稳定判断时仍标记 `NOT_NEEDED`，不得通过 Bug 轻量检查。
- Incident 因缺少非关键截图/日志/稳定复现而阻塞严重问题交接、把默认核查路径升级成 PRD/专业 Reviewer/重型 Ready、改写原始 Signal/证据、未分开事实/推断/未知、没有明确研发核查问题、伪造 `NOT_AVAILABLE` 信息，或交接后不等待可验证研发回传时失败。
- 研发回传脱离原 Packet 另起无来源结论、原位覆盖 v1、缺少 `supersedes`/hash，或没有把核查结果路由到 Bug Fix/Product Decision/Discovery/Incident Product Response/Close 时失败。
- 自动通知/提单被外推为回滚、降级、开关、数据修复、赔付或对外沟通授权时失败；可选 Incident Product Response 缺有权确认，或临时措施缺 Owner、TTL、作用范围及退出/回滚条件时失败。
- `SCHEDULED / CONDITION_TRIGGERED` 在未重新验证时间/触发条件、依赖和授权且没有 activation event 时不得创建 Plan Run；`WAIT` Item 不得标成 committed。
- 普通 reroute 被错误写成 Product Changelog，或正式 Decision/Roadmap/产品行为变化却没有 Product Changelog Proposal 时，产品记忆一致性检查失败。
- 任一 Issue Collector、飞书、Development/Test Graph 或未来 Input Connector 试图绕过 `signal.ingest`、直接启动 Plan/PRD Run、自行选择产品路线或使上游产物失效时必须被拒绝；用户粘贴一次性链接不得被登记为具备周期拉取/对账权限的 Connector。要求下游人员填写内部 YAML/route 字段，或让不同 Connector 分别维护 Bug/Incident/Discovery Router，也不通过。
- 纯 dispatch/lifecycle 状态被错误派生为 Product Signal，typed result 未先更新其绑定 Incident/Bug/Experiment/Handoff 记录，或 typed result 中的新产品事实没有带 exact result/upstream refs 进入关联 Signal 时失败。协议 event kind 可以触发中央确定性快分流，但不得被 Connector 外推为产品业务结论；Router 仍必须只有四个 destination。
- 下游提交者或 Connector 直接把 Decision/Plan/PRD/Roadmap 标为 invalid/reopened、Agent 只按 severity 分数决定返工、所有普通意见都要求 Owner 审批，或普通意见被消极归档而没有专业建议/升级所需证据，均失败。Human View 只显示裸 enum、不说明当前结论、影响层、依据、下一动作和翻转条件，也失败。
- 下游回传默认退 PRD或启动新 Product Run、Implementation Deviation 通过改 PRD 处理、上游 Planning/Decision/Problem 错误被 PRD 文案圆回、未改变产品事实的状态/重复信息触发全链重跑，均失败。material PRD 变化必须生成 superseding Candidate/release；material Decision/承诺/Roadmap 变化必须由有权 Owner 形成新决定，但不得为此新增固定审批 Gate。
- Schema 合法但缺 Reviewer 的 Ready 请求被 State Controller 拒绝。
- 旧版本 verdict 不能用于新 PRD Ready。
- `prd.ready.gate` 对旧/非 current Candidate、不同版本 Review/route、stale upstream refs、`REQUIRED + BLOCKED_MISSING_INPUT` Eval、缺失 Template/Document Experience/version/changelog 任一情况返回 `READY`，或 `NOT_READY` 只说“请完善”而无 exact ref/repair/resume，均失败。Gate 重做产品语义审查、按字段填满率/分数放行，或要求 Owner 二次确认、外置审批、Connector 授权、研发/测试完成或所有 advisory 关闭，也失败。
- 当前期若 AI/sub-agent Reviewer 被赋予 formal veto、approval、waiver 或冒充外置专业责任人，失败。
- 未处理知识影响或 `INSUFFICIENT` 快照不能 Ready。
- PRD 使用可变 `current/latest` 而未绑定确切 `decision_refs`、`roadmap_snapshot_ref`、`product_plan_ref` 和 `knowledge_snapshot_ref` 时不能 Ready。
- 已批准/引用/交付的 Decision、Roadmap 或 Product Changelog 被原位修改，或新决定缺少 `supersedes` 链时，`artifact.version.guard` 必须拒绝提升。
- 已保存/引用/分享的 archived Candidate 或附件被原位覆盖，Review 结果未绑定 exact Candidate+asset hashes，Optimizer 未生成新 archived version/delta，或把 token/keystroke/autosave 全量塞入 `archived/`，均不符合 PRD 文档生命周期。
- `released/` 只保留最新目录、把 superseded/invalidated/revoked release 移到 archived/或删除、覆盖已引用 Markdown/assets、让 release 依赖 package-root/兄弟目录共享可变 assets、状态变化改写 Changelog 历史行，或 current pointer 被当成历史真源，均失败。无附件的简单 PRD 被强制创建空 assets 目录不是硬失败，但不应成为生成器默认。
- 未经 Fidelity/required Review、Ready 和 Document Experience validation 就写入 `released/`，Handoff 通过 `latest/current` 猜版本，未绑定 exact directory/Markdown/assets hashes/source draft，主文件仍叫 `prd.md/final.md/最新版.md`，或把 DOCX/PDF/ZIP 当 canonical truth/Ready 必填，均失败。反过来，继续强制 `prd.owner.confirm_understanding` / `handoff.owner.approve` 才允许 Ready/release，同样违反当前 HITL 简化。`final/published/approved` 目录不能替代规定的 `released/` 语义。
- 产品范围、规则、流程、AC/Eval 语义发生变化却只修改 released Markdown，没有创建新的 archived PRD candidate，并在影响上游承诺时更新所需 Decision/Plan/Slice/change PRD，必须失败；纯呈现修订也不能原位覆盖旧 release，而应创建新的 released version。
- `DOCUMENT_CHANGELOG.md` 被用来替代 Product Changelog、架构 CHANGELOG、上游 Decision/Plan/Slice/Knowledge 或 Audit Ledger，可选 content checkpoint 被用来取代正式 PRD，或 manifest/current pointer 创造了文件和追加记录中不存在的事实，均失败。
- 当前一期不以 KMG submission、ack、shared-canonical publication 或跨团队 Impact sync 作为 Ready/Handoff 前置；未接入 KMG 的项目必须以 local-only records 正常运行并披露边界，也不能伪称已共享发布。未来若项目 policy 确实要求 shared canonical，必须先在 KMG contract 中定义 exact action scope、receipt、失败恢复与无关 action 隔离，再决定是否形成对应约束。
- PRD（包括实验 intent）的 Feishu/Development Connector 在 Ready 前不能调用；Ready 后也必须按每目标 `disabled/manual/auto_when_ready` policy 执行。默认自动、预授权未覆盖 exact target/scope 仍发送、外部写权被复用为 PRD 语义审批、已预授权却重复要求固定 Owner 内容确认，或把 BPG Released/Connector Sent 写成组织审批通过，均失败。UNKNOWN 结果盲重试、多个目标共用同一 receipt、Connector 回写 canonical PRD、手工 DOCX 导入无验证却标 `SENT/IMPORTED`，也失败。Incident Verification Packet/Bug Fix Brief 分别通过对应轻量检查、权限与批准后可以交接，但不得伪装成 Product Ready。
- AI/sub-agent Reviewer concern、旧 `BLOCK_RECOMMENDED` 值或 concern level 不能直接写 formal Block、阻止本地 Ready/Released 或获得 waiver authority；它们必须以 advisory/disposition/内审意见交外置团队。未来无人值守阶段的专业 blocking/policy/waiver 仍只是 Roadmap seam。
- G03 中伪造/错误引用基线、忽略材料冲突、把旧决定写成不可质疑事实、未给首选建议、五项证据不全仍自动生成 Bug Fix Brief、无基线盲从“直接修”、把 surface tag 当本质分类、在 Brief 中改变产品规则，或遗漏应升级的 Incident，都会触发硬失败。
- G04 中直抄用户方案、单条外推、把假设写成事实、伪造代表性、只说“收到”不形成判断、只挑战不给行动、把选项甩给 Junior PM、诱导回答、把可检索信息推给 PM、不给首选建议/最强反方、挑战强度一刀切、认知镜头堆叠置信或无限问答，都会触发 Case critical failure。
- Kill criteria 已触发但未生成新授权 Decision Record 时，原方向不能继续流转。
- 伪造批准/证据、授权升级事实、越过不可豁免风险、无测量/回滚却称实验、选择性解释结果都会触发硬失败。
- 未解决 advisory concern 未被同源内审意见透明披露，或外置团队审核尚未完成却写成“无风险/已批准”，失败。

### 24.3 规划完整性

- Product Plan v0 被直接作为 PRD Matrix/子 Run 输入，局部深化没有回到系统最佳运行结果协调，多个局部 PASS 被拼成全局通过，或尚未满足 §11.1.1 停止条件就 Plan Ready，均失败。
- 把 Planning Refinement 注册成独立持久 Node、与 formal Review 合并成主 Agent 自审、让 advisory partial review 成为 Ready 证据、Reviewer 直接修改 Plan/state，或 formal verdict 没有绑定 exact frozen Candidate/hash，均失败。local omission 被无谓送回 Discovery、系统结构 Finding 只改措辞、失效 Decision/Problem 没有回正确上游、no-progress 仍无限 Optimizer，或为 Product Plan/PRD/实验 intent 复制不兼容 Review–Optimize runtime，也失败。
- 深化发现只能给 v0 找支持、不能拆/并/删/重排或返回 Research/Experiment/Product Decision，material Plan 变化原位覆盖旧版、缺 changelog/supersedes/impact，或另建可漂移“深化报告”成为第二真源，均失败。
- 并行 sub-agents 读取不同/mutable Plan snapshot、并发写正式 Plan/current/state、aggregate 抹掉分歧或绕过 branch+worktree/diff review 时失败；已有稳定 Plan 的局部小改动被无理由强制全量重跑也不符合本期原则。
- 所有需求固定跑 PROJECT_SCALE、简单需求被迫生成完整 Wave/Round 文件套件，或另建顶层 Planning Router/第二状态系统，失败；反过来 LIGHT 省略目标、Evidence、关键 Assumption、验收、风险或追溯也失败。Profile 在 Signal Intake 永久锁死、要求 PM 填复杂度问卷、无证据静默降档，或父 Wave 禁止无冲突 Plan/PRD Runs（含实验 intent）并行，同样失败。
- `plan.slice` 按“一模块一 PRD”“一迭代一 PRD”或矩阵每格一 PRD 机械拆分，把前端/后端/API/数据库分别写成不能验证用户结果的产品 PRD，直接生成 PRD 正文而没有候选边界，或要求 PM 手工填完整拆解图，失败。候选缺目标/用户结果/阶段/模块/依赖/验证/拆分理由，把“相对独立”误作零依赖硬 Gate，或消息治理被拆成识别/接口/样式半成品，也失败。
- 规划项必须有一个显式当前去向；未进当前 PRD 的后续、Experiment、等待、不做或 unresolved 事项不得静默消失。`UNRESOLVED` 缺 Owner/影响/临时处理/复查触发时不能作为合法藏匿处。
- `plan.coverage.validate` 只数“本轮实现率”、强迫本轮全覆盖、每次召集完整 Reviewer、发现 Finding 后静默改 Plan，或完全跳过遗漏/重复/体验/依赖/上游一致性任一类，失败。缺口被一律 HARD_BLOCK、Coverage 另存为可漂移第二真源，或 Agent 通过缩小分母自证完整，也失败。
- `plan.reconcile` 只逐条勾掉 Coverage Finding、不回到 Target Outcome/Guardrails/Decision/Roadmap，或为向前推进强行拼接局部合理但整体冲突的 PRDs，失败。改变目标用户/核心目标/做不做/重要优先级时间/风险承担/承诺/Experiment边界却未让 Owner确认并落既有账本，或本可自动修引用却强制审批，也失败；根因在 Slice/Iteration/Decision/Learning 却只改措辞、不返回上游，同样失败。
- 循环依赖、孤儿项和重复分配被确定性 Validator 发现。
- Module 逻辑视图使技术分层式 PRD、责任重复、低内聚和不必要耦合显性化，并形成可处置 Finding。
- Iteration Map 中每次迭代都有独立结果、学习目标、验证与停止条件；无用户价值或无关键学习价值的小碎片不能成为独立 PRD。
- 跨模块端到端闭环由父 Current Iteration Outcome 协调；Batch 不是默认，确需 Batch 时必须验证不能独立发布的理由、共同回滚/停止条件和耦合风险。
- 即使后续迭代全部停止，当前 Ready 迭代仍是可理解、可运行、可验证的产品状态。
- 简单 Run 可以把四个逻辑视图合并内嵌，复杂 Run 可以独立产物化；两种表达都通过同一语义与引用验证。
- Plan Owner 被迫逐字段打勾、被要求固定确认整份 Plan、相邻确认被复制成独立审批 Node、Agent 冒充 Owner，或按需一页摘要被宣称为外置汇总审批通过，失败。忠实 Planning 的 material 新取舍未回 `product.decision`，或 `plan.ready.gate` 做语义产品判断/评分、读取旧 Review、忽略致命冲突/material Decision refs，只返回裸 NOT_READY 无 repair target，也失败。
- Plan Ready 要求消灭全部 Unknown、反过来在目标结果/受众/有效性/关键依赖/停止回滚仍不清楚时放行，均失败。PASS 后为未 activation、未来 Roadmap 或 WAITING_CONDITION 项提前创建 PRD Runs，或把 `EXPERIMENT` 创建成另一种 Run/Profile，或继续采用“为每个 Slice 无差别创建”的逻辑，同样失败。

### 24.4 `EXPERIMENT` Delivery Intent

- `EXPERIMENT` 必须复用同一 Product Planning/PRD/Eval/Review/Ready/Released/Handoff pipeline；出现独立 Fast Lane、Experiment Plan/PRD/Ready/Handoff/template/profile 即失败。
- 同一 PRD 缺 key unknown/hypothesis、受众/exposure、具体变化、observable measurement、continue/adjust/stop mapping、监控、kill/rollback、Owner、结束时间或伤害 Guardrail 时，`prd.ready.gate` 必须拒绝对应 release。
- R0/R1 可以按真实复杂度选择 LIGHT；R2/R3、不可逆或专业敏感 action 必须升档并应用 action-scoped constraints。`EXPERIMENT` 自动降为 LIGHT 或把 PRD 仅仅写薄均失败。
- 扩流、延期、改指标/成功标准、取消 Guardrail 或转长期承诺会使旧 PRD/release 进入 material Impact/复审；不能靠 Connector 参数绕过新 Decision/版本。
- 下游 typed result 必须经 `signal.ingest` 绑定 exact Decision/PRD/Run 并成为新 Evidence。expand 不自动 `COMMIT`，iterate 产生新版本，inconclusive 不能解释成软成功，所有处置返回 Product Decision。
- 一期不要求或维护 Experiment Portfolio；若无真实并行干扰证据却预建 Portfolio Schema/Service/Registry/业务真源，失败。

### 24.5 Reviewer advisory-only 与外置审核

- 当前期所有 Product/UX/Engineering/Testability/Security/Privacy/Compliance/Domain AI/sub-agent Reviewer 都只能形成 advisory Finding，不拥有 formal Block、veto、approval 或 waiver authority，也不能冒充外置专业责任人。
- Finding 的人类视图至少给出直白关注事项、关注等级、exact evidence/ref、可能影响、专业建议和最早返工点；等级只用于排序与外置团队聚焦，不能单凭等级阻止 BPG Ready/Released。
- 每条 Finding 必须有 disposition：采纳并修复、不采纳并说明理由，或保留供外置团队判断。Reviewer 数量/一致不能提升 Evidence confidence，单个 concern 也不能无限占住 Run。
- `review.finalize` 只验证 Review attempt、Finding/disposition、exact Candidate 与同源内审意见的机械完整性；它不是批准或 Gate。未解决 concern 透明披露后可以进入唯一 `prd.ready.gate`。
- `prd.ready.gate` 只因既定产品合同、版本、refs、REQUIRED Evals、Template/Document Experience/changelog 等机械缺口返回 NOT_READY；若 Reviewer 恰好指出同一机械缺口，权威来源仍是 Validator 合同，不是 Reviewer。
- 正式 Reviewer blocking、专业身份、Project Policy、Domain Owner authority、waiver、action scope 和到期/重验证机制只保留为未来无人值守研发/发布的 Roadmap seam，不属于一期实现或验收。

### 24.6 Product Evals

- 确定性能力在普通 AC/测试用例足以稳定判断时可以判为“普通验收标准足够（`NOT_NEEDED`）”，但必须记录可审计理由；复杂性本身不能把它自动升级为 REQUIRED。
- G03 的确定性 Implementation Deviation 只有在 AC 足以稳定判断，且记录确定性依据与回归检查时，才能使用 `NOT_NEEDED`。
- `AI_BEHAVIOR`、推荐、搜索、排序等非确定性 Bug 默认要求 Bug Eval Pack；无法稳定判断确定性时不能以轻量快线为理由省略。
- AI/Agent/RAG/生成式内容、搜索/推荐/排序/个性化、多合理输出、Rubric/数据分布依赖或需样本验证的安全偏见内容合规风险通常为“必须提供 Evals（`REQUIRED`）”；缺 Eval Pack 时可以继续生成/修改 PRD Candidate，但不能 Ready。
- “建议增加 Evals（`RECOMMENDED`）”默认不硬阻塞，但必须披露建议、理由和不采用的影响；确定性 policy 可以提高最低等级，Agent/PM 不能无痕降级。
- 缺 Ground Truth、数据或专业 Owner 时记录独立 `BLOCKED_MISSING_INPUT`，Applicability 仍保持 `REQUIRED`；不得继续写旧 `DEFERRED` 混合值或伪装成测试阶段再补。
- Applicability Human View 不能只显示 machine code；普通 PM 不填评测问卷，Agent 从行为、Plan/PRD Strategy 与 Policy 先判断。专业 Ground Truth 缺失时必须如实进入相应 Fulfillment 缺口并交外置专业团队判断，不能由 AI Reviewer 自我批准或 waiver。
- AI 生成的 Ground Truth 只能标 synthetic/candidate；未获得可信规则、标注数据或可验证专业来源时，不能满足 REQUIRED Eval Pack 的 Ground Truth 合同。
- `evals.build` 在没有 exact stable content source/hash 时不得启动；`prd.render` 与 Eval 分支绑定不同 content versions、join 静默选最新版，或语义变化后继续复用受影响 Pack，均失败。纯排版变化触发全量 Eval 重做也属于错误的 impact 粒度。
- Joint Fidelity Review 必须同时检查 Eval Pack 没有引入 PRD/Decision/Plan 未决定的产品规则、成功标准或 Ground Truth，也没有遗漏上游明确要求的 Eval/Guardrail。发现 material mismatch 时返回 Eval、PRD 或更早上游，不能通过固定 PRD Owner 确认把两者强行对齐。
- Eval Pack 只堆案例数量却缺核心结果、主路径、关键边界、发布风险、Rubric、Ground Truth provenance、coverage 或 PRD rule/AC traceability，不得以“生成很多”通过 Review。Synthetic/candidate data 冒充 Ground Truth、多 Agent 共识提升真值置信度、只读 Reviewer 直接改 Pack，均失败。
- Better Product Graph 输出正式测试用例/单元集成E2E代码、准备环境数据、运行 runner、判缺陷或给 final test verdict，或仅凭 TDD-ready 愿景宣称完成工程 TDD，均越权失败。
- 未接入测试 Graph 时可以交付 Eval Pack，但不能产生“测试已通过”结论。

### 24.7 恢复与版本

- 关闭会话后仅凭 Graph、state、Ledger、产物和知识快照恢复。
- Reviewer 优化生成新版本，不覆盖旧版本。
- `current` 指针损坏或改变时，仍能凭版本化 Decision Ledger/Roadmap snapshot、明确引用和哈希恢复；`current` 本身不作为事实来源。
- superseding Decision 或 Roadmap snapshot 变化生成逐产物 Impact List，只使受影响的 Plan/PRD（含 delivery intent）/Eval/Ready/Handoff 进入相应状态。
- Knowledge impact 只重跑受影响节点。
- 父 Plan 变化只失效受影响子 Run。
- Experiment 合同或风险作用域变化只失效受影响 profile/动作，但扩流不得复用旧 Ready。

### 24.8 审计与副作用

- 单点事件或正式产物篡改可被发现。
- 只有 Audit Event 而没有 Decision Record/Roadmap/Product Changelog 语义时，系统不得声称已经恢复产品决定、承诺或变化理由。
- `audit.verify` 在规定检查点实际运行。
- Handoff 未知结果不会盲重试。
- 回放不会重新创建远端单据。

### 24.9 原型指标

每个端到端实现切片记录：

- 节点和模型调用次数。
- 活跃执行时间与人类等待时间。
- 每次恢复需要加载的上下文量。
- 哪些节点经常一起失败或一起重跑。
- Reviewer 重复发现和冲突率。
- PRD 被研发人工拒收的原因。
- Evidence Reference provenance 完整率、权限/新鲜度失败率，以及 Collect 与 Map 独立重试后避免重复抓取的比例。
- Problem Evidence Map 的 claim/关系/冲突人工修正率、同源误判率、MVU 连续多轮不变率、每个 MVU 的信息获取成本与实际决策影响。
- Evidence Request 被目标来源理解并获得有效证据的比例、按来源类型的等待时延，以及 action-relative completion 在事后结果下的过早推进/过度研究率。
- 七类 `source_resolution_type` 的选择/人工纠正分布、AI 自助解决率、无必要 PM 打断率、专业/用户事实被错误问给 PM 的比例，以及打断前置说明对 PM 回答质量的影响。
- PM 访谈六步完成率、一个 MVU/一个核心问题遵守率、脚手架被人工判为诱导的比例、Junior PM 对问题/取舍/Agent 建议的正确复述率，以及只说“收到”或只列选项的人工修正率。
- `LIGHT / STANDARD / STRONG` 与风险/证据冲突/可逆性的匹配和人工纠正分布、一次最高价值挑战的决策影响、PM 分歧后无限争辩/静默迎合率、验证/回滚条件可执行率，以及最小 Round 记录足以回放但未默认保存全量逐字对话的比例。
- Learning Round 恢复成功率、重复查询/重复 Map 更新率、`WAITING_FOR_EVIDENCE` 按来源的时延与超时处置、Round Delta 可复述率，以及停止后新信息实际改变动作的比例；另记录 status/disposition/recommendation 混淆率、三类 disposition 人工修正率、`INSUFFICIENT_TO_PROCEED` restart 成功率和建议被误当授权的次数。
- `problem.synthesize` 的 `COMPLETED / RETURN_TO_LEARNING / FAILED` 分布、material gap 捕获与误判率、Candidate 字段/Unknown/非问题人工修正率、方案泄漏率、exact source binding 与 stale 检出率、恢复成功率，以及 Candidate 被误当 Problem Ready 或被下游以 `current/latest` 引用的次数。
- Product Quality Reviewer 独立 attempt/上下文隔离遵守率、同模型与外部模型 Finding 一致性和人工纠正率、Reviewer 编辑/状态写入越权拦截率；Problem Ready 与 Product Decision 重复人类确认次数应为零；Controller 同输入/规则版本确定性、CAS/原子恢复成功率，以及 `ADVISORY_ONLY` 被误当正式 Gate 的次数。
- Problem Quality Review 各检查维度漏报/误报、四类 repair path 人工纠正率、delta Review 全局回归漏检率、no-progress 触发轮数/有效性、Junior PM 对关键 Finding/原因/建议的正确复述率。
- PRD `review.parallel` 的 Goal Fidelity Review Packet 是否全部绑定同一 exact snapshot/hash，目标/范围忠实度 Finding 的漏报、误报和人工纠正率；LIGHT 合并角色是否丢失该逻辑检查，条件 Reviewer 触发与首轮隔离是否符合合同。
- `confirmed / complemented / conflicted / unique / unsupported` 的交叉核查分布、高影响 review-of-review 触发率与轮数、严重单一 Reviewer 意见的人工处置，以及多数票/多 Agent 一致被误当证据或抵消致命偏离的次数。
- `FIXED / IMPROVED_BUT_OPEN / PERSISTENT / REGRESSED / INSUFFICIENT_EVIDENCE` 的人工纠正、delta re-review 后的目标/范围/关键不变量回归漏检、两轮 no-progress 停止效果，以及无 upstream commitment 的“建议加功能”被错写入当前 PRD 的比例、Review 延迟与成本。
- `review.finalize` 同 exact input/rules 的重放一致率、stale/missing/丢 Finding/缺 disposition 拦截率、同源内审意见版本错配率，以及 finalize 被误实现成 Reviewer approval/Gate 或与 `prd.ready.gate` 重复检查的次数。
- `prd.optimize` 的平均/分 profile 修订轮次、两轮 no-progress 早停率和人工纠正率、finding→change 可追溯率、claimed repair 被 Reviewer 判为 `FIXED/REGRESSED/PERSISTENT` 的分布、current-PRD repair 误改上游语义的次数，以及每 Run archived Candidate 数/Review Attempt 数和无内容变化误生 PRD 文件次数。
- `prd.ready.gate` 同 exact input/rules 的重放一致率、六类检查分类与 repair target 人工纠正率、旧 Candidate/Review/route 错配拦截率、REQUIRED Eval/stale upstream/template-version 缺口漏放率，以及外置审批/Connector/研发测试状态被误当本地 Ready 前提的次数。
- 可并行任务 sub-agent 使用率、关键路径时延改善、主 Agent 重做率、required/optional 超时与降级分布、`BEST_AVAILABLE / BALANCED / FAST` 实际映射和成本、权限越界拦截率、snapshot/hash 不一致率、join 分歧保留率，以及多 Agent 同意被错误提升为 Evidence confidence 的次数。
- `NO_PM_INTERVIEW` 的 prompt 拦截与绕过检测率、进行中 `interview skip` 生效时延、skipped-interview impact 可理解率、合法继续/等待分布、`interview resume`/`interaction=guided` 恢复成功率，以及是否误跳过 Product Decision/外部写入授权或错误降低风险门槛。另记录完整 Discovery 未访谈的原因分布和“无 material PM-only unknown + 低信息增益”人工纠正率。
- 问题假设审视对方案锚定和来源角色混淆的发现率、PM 首次访谈前完成率、exactly one MVU 后续实际改变行动的比例、最佳来源命中率、下一信息请求可执行率、三类下一建议分布、checkpoint 重跑率，以及“固定 checklist / 多个同权问题 / 强行制造反方”与漏掉可信替代的人工复核率。
- 各 Profile 的确定性 validation 失败率、Readability finding/disposition、首读者正确复述结论/未知/下一步的比例，以及 source 变化后 stale 检出与重渲染时延。
- Document Experience 对 PRD/Decision 阅读时间和下游误解的改善，以及对 Incident/Bug 交接时延、文档长度和无关阻塞的副作用。
- Target Operating Outcome 的达成证据、Guardrail 违背情况和决策结果分布。
- PM 是否能复述问题、证据、关键未知、取舍、父级 Current Iteration Outcome 与 PRD Increment Contribution；该项用于评估辅助效果，不替代有权人的正式批准。
- Experiment 的启动数、按时结束率、`INCONCLUSIVE` 率、Guardrail/kill 触发、Zombie 数、相互干扰和结果处置时延。
- Finding 关注等级与 disposition 分布、遗留 concern 在同源内审意见中的披露完整率、外置团队采纳/拒绝/补充率，以及 AI concern 被错误当作 BPG formal Block/approval 的次数。

这些指标决定后续节点合并、合同冻结和是否引入基础设施，不使用未经验证的固定节点总数。

---

## 25. 已有 Skills 的吸收边界

| Skill | 吸收 | 不照搬 |
|---|---|---|
| `better-product-plan` | 前期规划、资源约束、阶段、默认 PRD 模板 | 不把完整计划变成一份巨大 PRD |
| `Product-Prd-Skill` | AI 先理解、反复 PM 访谈、理解校准、质量 Rubric；将其学习循环拆成可版本化的 Evidence Map、Assumption/MVU 更新与 bounded joint judgment Round，并要求给 Junior PM 脚手架后仍由 Agent 提供专业首选 | 不保留一体化不可恢复流程，不把 PM 回答直接升级成已验证事实，不增加独立 Problem 确认，也不把访谈变成问卷、无限争辩或全量逐字对话真源 |
| `better-question` | 作为学习循环的“查询规划器”：读取当前 Problem Evidence Map/MVU，排序未知、选择最佳来源，决定 AI query 或 PM 核心问题的非诱导措辞、必要澄清与停止点，并生成具体 Evidence Request | 不让它代替 Evidence Reference 采集、Evidence Map 关系判断或 Cognitive Router，不注册成新节点/固定 checklist，不批量生成低价值问卷，也不以问题数量代表学习质量 |
| 20 个认知基座目录 | 经 Cognitive Router 按需调用；覆盖元认知保险、Discovery 核心、条件式分析、决策与实验塑形 | 不把 20 个能力做成固定问卷；`信念驱动` 不进入常规 Discovery，也不能覆盖概率证据和 Gate |
| `product-goal-based-audit` | 在 `review.parallel` 中只吸收目标忠实内核：从 exact Decision/Plan/Slice/Evidence/Knowledge/Guardrails/System Acceptance/Candidate 自动构造同源审查包；Product Reviewer 固定执行目标/范围忠实 profile；按风险选择独立角色首轮、Finding matrix、分歧账本、高影响 bounded review-of-review、delta repair verification 与 global invariant regression。完整七阶段仍用于架构/发布/Roadmap 里程碑级审计 | 不在每份 PRD 重跑承诺确认、完整七阶段、95%/80% 覆盖率、百分比/A—F、`.product-audit` 套件、Shell 脚本、每项双审、每轮人工确认或无限优化；审计建议无上游依据时只能作 future lead，不能自动成为当前 PRD 修改指令 |
| `better-test` | Exit 0 不等于 PASS、需求—Gate—证据追踪 | 不在 Better Product Graph 执行真实测试 Graph |
| `better-work` | 选择性吸收“小任务轻量、每轮一个主要目标、范围/依赖/成功与停止条件/Evidence/checkpoint”，以及“Wave 管项目阶段主序列、Round 管当前范围思考—动作—验证”的语义，用于 LIGHT/STANDARD/PROJECT_SCALE 自适应 Planning | 不照搬 `TASK/MAP/WAVE/ROUND` 文件套件、重复状态/Gate，也不把 Wave 变成全项目并发锁；继续复用 Product Plan、Decision/Risk、Run State 与 Audit |

`evals-generator` 不在这张“已有 Skills”表中，因为它尚不存在。V1.4 只冻结未来原子能力的职责、输入输出、适用性、Reviewer 和 Gate 边界；后续建设时再单独设计、实现和审计。

---

## 26. Claude Findings 的 V1.4 当前处置

本表保留原 Claude 审计的追踪关系，但以 V1.4 继承并收敛的后续决定为准。它不是把旧 Finding 原样恢复为当前合同：

| Finding | V1.4 当前处置 |
|---|---|
| C1 | 上游 Decision Run、合法激活后的父 Plan Run 与独立 PRD Runs，支持独立状态与分批交付 |
| C2 | State Controller 在写入时自行重算 Validator/Gate |
| C3 | 角色、冲突和失效证据保留；一期 Waiver Policy 已被 Reviewer advisory-only 决策取代，正式 blocking/waiver 仅为未来无人值守治理 seam |
| C4 | Knowledge 读取 exact snapshot 与本地影响追踪保留；KMG submission/ack/Impact sync 详细合同按最新决定延后到 Knowledge Requirements 反推后设计 |
| C5 | Incident、Bug、Discovery 三条真实路径 |
| H1 / M6 | 后续决策已把 Product 多文件 Handoff Package 折叠进 self-contained Released artifact set；必要 Supplement 成为同一 release 的扩展/附录并由 Release/State/Audit refs 追溯。Experiment/Incident/Bug 仍用各自合同 |
| H2 | Problem Quality Review + programmatic Ready 分工保留；固定 human Owner Confirmation 已被 ADR-088 取消，人类责任合并到紧邻的 Product Decision |
| H3 | 三数覆盖报告、唯一去向和 Product Review |
| H4 / H5 | 不固定节点数；垂直切片记录成本，Discovery 增加预算 |
| H6 | 恢复 `COMPLETE/PARTIAL/INSUFFICIENT` |
| H7 | 后续架构决策已取代原处置：当前 Product PRD dispatch 由 Ready + versioned Connector side-effect policy/预授权控制；不恢复固定内容审批。第一版没有已发布消费者，不实现旧事件兼容层 |
| M1 / M2 | 收窄哈希声明，规定 `audit.verify` 触发点 |
| M3 | 拒绝“配置字段等于 Driver 层复活”的结论 |
| M4 | Core 位于 `src/`，Codex 唯一公开 Skill 位于 `host-adapters/codex/public-skill/`；二者经 V1.4 allowlist 生成可删除重建的 `dist/`，安装身份由自动 manifest 证明 |
| M5 | 决策风险与 PRD Review 明确对象不同 |
| M7 | pending-before-call、未知结果查询或人工确认 |
| M8 | 顺序降级 + enforcement mode；第二宿主前不建复杂抽象 |
| M9 | 显式绑定 Knowledge Maintenance v0.2 共同合同 |
| M10 | 后续 ADR-077—079 以唯一 `signal.ingest` 承接下游回传：status/result 先更新绑定记录，新产品事实才派生 Signal，并按 exact Impact 返回最早受影响点；不保留下游专用入口 |
| L1 | 恢复 project/input；completed nodes 只做可重建投影 |
| L2 | Graph Manifest 与文档版本解耦 |
| L3 | Emergency policy 项目配置，通用 Graph 不默认事后补批 |
| L4 | 节点目录和合同显式声明 type |

---

## 27. V1.4 收敛范围与历史修改索引

### 27.1 V1.4 相对 V1.3 的窄变更

1. Codex distribution 只允许 `skills/better-product-graph/SKILL.md` 一个 Host discoverable Agent Skill；内部原子节点改称 Core Atomic Skill Modules，源码与构建路径避开 Plugin Skill discovery。
2. 冻结最小 source→dist allowlist、relative resource resolution、唯一公开 Skill 与 installed-copy identity 自动检查；安装候选绑定 SemVer、Git commit/dirty、architecture baseline、execution contract versions/fingerprint、inventory 和 artifact hash。
3. 分离 Product Golden Suite 与 Plugin Contract Suite；前者评估 G01/G03/G04 的产品判断/end state，后者评估安装、激活、intent、资源、唯一入口、不可绕过和身份。两者都不是业务 Node/Gate。
4. 将现有 `evals/product-graph v0.1` 固定为 `LEGACY / DOCUMENT-ONLY / NOT A V1.4 ACCEPTANCE BASELINE`；实现期另建 v0.2 migration baseline，不覆盖旧证据、不在 runtime 前宣称 PASS。
5. 消除模板 promotion 矛盾：只冻结可配置 profile、exact version、fallback、pin/rollback；general v0.1 仍为 Draft/Bootstrap 候选，何时 promotion 留 Roadmap，不设当前固定人工 Review Gate。
6. 没有改变 Graph/Wave 顺序、一期产品范围、业务 Node/Gate，也没有新增 MCP、CLI、Service、Runtime、签名、SBOM 或远程 attestation。

### 27.2 V1.2 相对 V1.1 的修改与 V1.3 后续收敛

本节是 V1.2 形成过程及其在 V1.3 被进一步收敛的决策追踪索引，不是 Product Loop 的另一份说明。第一次阅读可以跳过；需要回答“为什么变成现在这样”时，再从条目跳回对应业务章节。

1. **增加 System Acceptance Baseline**：先定义一次好的 Better Product Graph Run 在方向、认知、决策、整体规划、PM 辅助、下游交付和运行治理上的结果，并明确不能用 PRD 数量、字段完整率或单纯速度自证成功。
2. **把 Outcome-first 提升为核心原则**：父 Product Plan 先定义 Target Operating Outcome、Observable Evidence、Non-sacrificable Guardrails 和 Current Iteration Outcome；单份 PRD 定义 PRD Increment / Increment Contribution；损害整体结果的局部优化不能通过 Product Review。
3. **把 PRD 拆解升级为二维模型**：横向形成高内聚、低耦合的产品能力模块，纵向形成按时间和学习目标渐进的小迭代。
4. **增加四个逻辑规划视图**：Module、Iteration、PRD Matrix、Dependency / Shared Contract 成为 Plan、Slice、Ready 和 Handoff 的正式合同；简单 Run 可内嵌合并，复杂 Run 可独立产物化。
5. **修正“最小 PRD”措辞**：不再追求越小越好，而是在明确模块和迭代边界内形成可独立产生并验证产品结果的增量合同。
6. **分开确定性与语义规划检查**：Validator 检查引用、唯一归属、版本和循环依赖；Semantic Planning Review 判断整体结果、内聚耦合、迭代闭环和切片价值。
7. **历史方案：增加 Experiment Fast Lane（已由第 73 项撤销）**：当时让 `EXPERIMENT` 生成独立 Plan/PRD/Eval/Ready/Handoff，以保留学习与风险边界；后续发现它复制 Product Pipeline 和产物真源，现只保留为 superseded 决策背景。
8. **历史方案：复用 Experiment Profile（已由第 73 项撤销）**：当时虽复用 PRD Run Runtime，仍保留独立 Ready/Handoff 语义；现已进一步折叠为同一 Plan/PRD profile 上的 delivery intent。
9. **区分授权与认知**：Decision Record 分开保存 authorization basis/owner/scope 与 epistemic confidence/evidence gaps；Sponsor-directed 决定不再被误写成已验证事实。
10. **增加 R0—R3 风险分层**：代码便宜不等于总风险低；风险用于调整证据、审查与外置关注，不给一期 AI Reviewer 授予阻塞权。
11. **把一期 Reviewer 收敛为 advisory only**：所有内部 Reviewer 只给 finding、建议和返工点；concern 透明进入同源内审意见，由仍然存在的外置团队作最终审核。正式专业 blocking/policy/waiver 只留未来 seam。
12. **分开 Finding、disposition 与外置关注**：不按多数票，不删除 Finding；采纳修复、不采纳理由和遗留外置判断各自可追溯，不再建设一期 Waiver 合同。
13. **增加条件式 Golden Cases**：G01 允许多个满足前提的结果，以灰度 Rubric 评价证据、风险、授权和实验质量。
14. **限制一期 Golden Suite 范围**：优先通用/C 端、线上行为、快速实验和线上 Bug；G02 企业复杂审批仅作低优先级可选扩展，不扩大一期门槛。
15. **增加 G03 当前产品基线判断**：把已有历史材料的线上 Bug 纳入一期核心 Golden Suite；Agent 必须跨 Decision/PRD/AC/设计/合同/历史行为重建当前基线、给出本质分类与首选建议。五项证据充分时 Controller 自动分流，只有冲突/PM-only事实/material路线差异或 override 才最小澄清。
16. **增加 Product Decision & Roadmap Memory**：用不可混用但同源的 Decision Ledger、Roadmap Registry、Product Changelog 和 Audit Log 保存产品上下文；所有 PRD 绑定确切版本引用。BPG 本地 records 支持无 KMG 完整运行，Knowledge Maintenance Graph 负责接入后的团队 shared/canonical 发布；V1.3 进一步把 Proposal/Outbox/Impact sync 详细合同延后到 Knowledge Requirements 反推后定义。
17. **增加 G04 反馈与 Junior PM 辅助基线**：把带解决方案的单条用户反馈纳入一期核心 Golden Suite；Agent 必须先检索、拆分事实/推断/未知、识别 most valuable unknown、提出少量高价值问题并给出首选建议，不能把用户方案直接复制成 PRD。
18. **重构 Signal Intake 与一期入口**：固定 `ingest / prepare / classify / route`，按能力插入 `relate?`；接收事务保存不可变原文，解析、历史关系、分类与政策路由各守边界；Codex 自然语言和 `$better-product-graph` 映射稳定 Core intents，Input Connector 默认只写 Inbox，不依赖未确认的 slash command。
19. **冻结 Better Product Graph 命名与单 Skill 表面**：正式品牌与 display name 为 Better Product Graph，Plugin/Skill/package 机器名统一 `better-product-graph`；只公开 `$better-product-graph` 和十一个 intent words，内部 Atomic Skill Modules 不作为用户命令，历史路径迁移另行版本化执行。
20. **收敛 Router、路由审计与 Planning 激活**：Classifier 默认只读无访谈；Router 只为一个 PM-only 路由事实短暂 `NEEDS_CONTEXT`，并把四个互斥 destination 与并行 `existing_links` 分开；Classification/Route Records 独立版本化并可由 `audit` 只读查看；`COMMIT` 与 `NOW / SCHEDULED / CONDITION_TRIGGERED` 激活分开。
21. **把 Incident 收敛为轻量核查交接**：默认正式产物统一为 `Incident Verification Packet`（线上问题核查包，内部类型 `incident.verification.packet.v1`）；Engineering Handoff 发送确切版本，研发回传追加为同一 Packet 的 v2/v3。它不生成 PRD 或进入专业 Review/重型 Ready，只有确需产品判断时才开启受风险约束的 Response 子分支。
22. **把统一 Bug Quick PRD 拆成基线判断与差异化分流**：`bug.baseline.assessment.v1` 使用 cause class + surface tags 两维模型；纯实现偏差用无 PRD 的 `bug.fix.brief.v1`，产品逻辑缺陷生成 superseding Decision/change PRD，规格歧义进入 Discovery/Decision，风险 Reviewer 和 Bug Eval 按需触发。
23. **把 Evidence 标签步骤重构为可审计学习循环**：保留 `evidence.collect` 的不可变 provenance 边界，将旧分类节点退役为 `evidence.map`，用 append-only、run-local `problem.evidence.map.v1` 建立 claim/evidence/conflict/unknown 关系；每版以 MVU、具体 Evidence Request 和行动风险/可逆性决定下一轮与退出，稳定事实只经 Knowledge Change Proposal 进入 Knowledge Maintenance Graph。
24. **把 Document Experience 从原则升级为 Core 横向执行规则**：不新增 Graph Node/Loop/Artifact/Gate；已有构建/渲染动作按 artifact Profile 解析 versioned Policy 和项目 template，调用共享 Renderer、确定性 Validator 与按需 Readability Reviewer。Human View 绑定 exact source/hash 且可重建，不成为第二真源；一期保证七个真实消费者 Profile，其中 `product_plan` 仅先覆盖 Plan Ready 一页摘要。
25. **确认问题假设审视为独立轻量节点，并收敛其五步内部逻辑**：`problem.assumption.audit` 位于 Evidence Map 后、Learning Loop 前，默认由 AI 在 PM 深访前自助去锚定：还原原话与事实角色，拆分现象/影响/问题假设/期望结果/提出方案，动态识别方向性假设，检查反证/历史/no-action/症状原因与可信替代，最后只选一个 MVU、最佳信息来源和下一信息请求，并保存 versioned run-local checkpoint。它只形成可信认知起点，建议返回证据、进入学习或重新评估路线；不强制制造反方，不做最终问题/产品决定，不发布 canonical knowledge，也不增加 Reviewer/Evaluator Loop、Ready Gate 或正式业务 Artifact。
26. **确认 Learning Loop 的持久边界、来源路由与停止原则**：`problem.learning.loop` 是独立可恢复循环节点，每轮围绕一个核心 MVU，经七类来源路由和既有 collect/map 更新证据与认知；内部原子动作留事件但不全变节点。Evidence Request 是版本化 wait/resume 合同；每轮保存认知 Delta 和继续/停止理由，停止取决于新信息是否仍可能改变当前拟议行动。Loop 只能建议实验，人工 override 继续待 Review。
27. **增加当前 Run 范围的强制跳过/恢复 PM 访谈能力**：启动/恢复可用 `interaction=no-pm-interview`；访谈中可用唯一公开 Skill 的 `interview skip|resume` 即时变更当前 Run。Controller 在每个 PM prompt 前强制检查，保留已答、记录未答/替代来源/影响。Skip 不表示信息充分，也不跳过 Evidence、Decision、Ready 或外部写权；完整 Discovery 默认至少一次实质访谈/等价对话，除非低信息增益无 material PM-only unknown 或用户显式 skip。
28. **确认 PM 访谈/辅导/挑战为 bounded joint judgment 合同**：每个允许打断 PM 的 Learning Round 围绕一个 MVU，依次展示理解、解释打断价值、提出一个核心问题、提供非诱导脚手架、进行一次最高价值挑战，并给出 Agent 首选、理由与最强反方。挑战强度按风险/证据冲突/可逆性而非资历选择；PM 坚持时记录分歧、authority 与验证/回滚条件并及时停止，不新增节点、Gate、业务 Artifact 或默认全量逐字对话。Learning Loop 的完成语义另由 ADR-037 约束。
29. **把 Learning Exit 收敛为三维合同**：废弃把等待、完成原因与研究/实验建议混为五项候选枚举的设计；Learning State 分开记录五种 runtime status、三种 completion disposition 与 advisory next-action recommendation。停止按拟议行动的证据充分性判断；`WAITING_FOR_EVIDENCE` 可恢复且不限 human，`READY_FOR_SYNTHESIS` 不等于统一 Problem Ready，`INSUFFICIENT_TO_PROCEED` 不伪造 Problem Definition/PRD，研究/实验仍由 Product Decision 决定。
30. **把产品分析模型收敛为可选 Analysis Method Hook**：Journey Map、KANO 等没有固定 Graph 阶段，默认 `NONE`，按调用五问和 Level 0—3 渐进加重；Method Card 声明适用性、输入、输出、限制和成本，输出只算 inference/analysis。第一期只保留 Hook/合同，不新增节点、Gate、Router、Registry、Service、公开命令或批量内置方法。
31. **补齐 PRD Review–Optimize 文档生命周期**：每个 PRD package 固定 `archived/` material candidates 与保存全部正式版本的 `released/`，根目录使用 append-only `DOCUMENT_CHANGELOG.md` 和可重建导航指针；每轮冻结 candidate/review/delta，Ready 后从 exact candidate 生成 release，Handoff 只引用 exact release/hash。文档呈现修订和产品语义变更分流，released PRD 是当前增量的人类交付合同并绑定 exact 上游真源，内部内容底稿不与其竞争。
32. **确认 Problem Synthesis 为独立轻量收敛节点**：`problem.synthesize` 只在 Learning=`COMPLETED + READY_FOR_SYNTHESIS` 后读取 exact Discovery inputs，冻结 versioned Problem Definition Candidate；它保留 Evidence/Assumption/Unknown、范围/non-problems 和用户方案关系，不继续搜索、决策或生成方案。material gap 携新 MVU 返回 Learning，source 变化后 stale 并以新版本 supersedes；`COMPLETED` 只表示稳定可审候选，不表示 Review、PM Confirmation 或 Problem Ready。
33. **确认 Problem Ready 的语义/确定性分工**：内部 Product Quality Reviewer Agent 以独立 attempt/隔离上下文只读 exact Candidate 并输出 advisory Finding；Plugin 内程序化 State Controller 基于 exact records 和 versioned rules 重算并唯一写 state/audit。固定 Problem Owner confirm 后续被移除，人类责任合并到 Product Decision，见第 36、38、77 项。
34. **确认 Problem Quality Review 节点与横向 Sub-agent Execution Policy**：Quality Reviewer 对 exact frozen Candidate 运行首次 full、后续 delta-targeted + global-invariant Review，输出 action-scoped Finding/Verdict、四类 repair path，并在无 material progress 时返回 Learning/Owner。对抗审查、可并发 Reviewer、独立研究/Eval/Analysis 候选优先由 bounded、最小权限 sub-agent 执行；主 Agent 只编排/join/保留分歧，Host 以 capability/model profile 映射实际能力。sub-agent 不新增业务节点、不写正式状态或外部副作用，也不替代 Owner/Gate/Connector approval。
35. **分开一期 Sub-agent 与未来 Multi-Agent Collaboration**：一期只依赖当前 Host 内部 bounded worker attempt；未来允许不同 Agent/runtime/Host/provider 协议化分工主策划与审计，但独立性必须来自独立实例、上下文、目标和冻结输入输出审计，不接受同会话换提示词冒充。Multi-Agent 复用 exact snapshot/role/result/permission/join 合同，经可插拔 Connector/稳定协议接入，不新增业务节点、不硬编码 Claude，也不改变 Owner、Controller 和副作用批准边界。
36. **历史简化随后进一步折叠**：曾把 Problem Owner Confirmation 简化为一次确认，但仍与下一步 Product Decision 重复；现按第 77 项取消，不再产生 `PM_ACKNOWLEDGED + OWNER_CONFIRMED` Problem 事件。
37. **把 Git 收敛为一期 Host Preflight**：开始/恢复时校验 exact project root，复用已有 repository/worktree；非 Git 项目默认本地 `git init -b main`，但不自动 add/commit/push/remote。`.gitignore`/敏感边界先行，失败如实 `DEGRADED/BLOCKED`；并行 sub-agent 使用独立 branch + worktree，由主 Agent 审核 diff 后整合，只在 material checkpoint/冻结版本提交或 tag。Git 不进入业务 Graph、Gate 或审批。
38. **确认轻量 Problem Ready Gate**：State Controller 自动检查 current/materially valid Candidate、同版本 advisory Quality Review/disposition 和一致可解析的上游 exact refs。只输出 `READY` 自动进入 Product Decision，或 `NOT_READY` + exact mechanical unmet condition/repair target；不评分、不做 Owner confirmation、不因 advisory concern/普通 Unknown 阻塞，并明确取消 action-scoped Problem Ready matrix。
39. **把 Product Decision 收敛为一个可恢复节点**：`product.decision` 内部编排 AI Decision Brief、按需 bounded adversarial/domain Review、Owner 讨论/挑战与明确选择、Controller deterministic route；原五个 `decision.*` 动作不注册 Graph Node。Draft/checkpoint 只用于跨会话恢复，Owner-confirmed Decision Record/route 才是正式边界；默认不全量 Review，Agent 给首选，material 时才外显最强反方。后续第 74—75 项确认 MVU guide 与 STOP/WAIT/future COMMIT，完整领域治理和剩余 materiality 仍待 Review。
40. **分开 Product Decision 的 machine enum 与人类表达**：五种 outcome 的基本边界及中文 display label 已确认；`COMMIT` 的三种 activation 也必须给直白句子。Decision Brief、交互、摘要和 Handoff 必须说明 why、最大 unknown/反方、下一步及改判条件，不能只抛 code/按钮；Renderer 从同一 Decision Record 生成视图，Validator 阻止 bare-code-only，不建立第二真源。MVU guide 与 STOP/WAIT/future COMMIT 见第 74—75 项。
41. **把默认 Decision Human View 收敛为一屏决策**：默认只展示一个直白首选、最多三个关键依据、最多一个 material 认知提醒、一个定性判断边界和一个具体下一步；最强反方仅 material 时一句，完整 Evidence/选项/认知/风险/历史/Audit 渐进展开。所有层级共用 exact Draft/Record，Validator 检查信息预算但不以死字数隐藏重大安全、合规或不可逆风险。
42. **确认 Decision Record 通用最小合同**：Owner 只确认 chosen decision、applicability scope、最多三个关键理由、最大 Unknown/改判边界和下一动作；material 分歧才显示 Owner reason。系统自动填身份、版本、exact refs、关系与 audit，确认后 immutable/versioned，改判新版本 supersede；Human/Audit View 共用同一 Record。
43. **确认 chosen-outcome 最小补充**：五种结果共用一份 Record，只生成被选 outcome 的条件化 `outcome_details`；STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT 分别记录最小可执行边界，未选项不留空模板，详细 Experiment/Planning 合同不在 Decision Record 重复。
44. **确认 Product Decision 轻量 action-risk classification**：R0—R3 绑定拟议 action/exposure、由 Agent 条件化完成，不是价值评分、问题永久标签、节点、Gate 或 PM 表格；Unknown 不默认低风险，R3 允许继续 Plan/PRD，并把高关注事项透明交给外置团队。正式专业阻塞/waiver 只属于未来无人值守治理或项目外部既有政策，不在一期 BPG 内建设。
45. **确认 Product Planning 双向深化原则**：先形成可推翻的 Plan v0，再优先逐块深化并每轮回到整体结果协调，稳定后才进行横向模块 × 纵向迭代拆分。material 变化用 version/checkpoint/changelog/supersedes/impact；sub-agent 只交 Proposal、主 Agent 单点整合；小改动 affected-area review。其 `product.planning` 内部 Refinement Loop 形态由第 50 项确认，切片/覆盖/协调由第 52—54 项确认。
46. **确认 Agent–Owner disagreement 合同**：Agent 必须先给首选；Owner 选不同 outcome 时只做一次基于证据缺口、风险和首选理由的 bounded 实质挑战，再由有权 Owner 决定。material 分歧条件保存双方理由、authorization、accepted uncertainty/risk、recheck/stop 和 execution constraints；授权不改变置信度，高关注事项必须随产物进入外置审核，不新增 outcome/node。
47. **确认 Product Decision 结束规则**：节点终止复用现有 State Controller transition validation，不新增 `decision.ready`、Gate/Artifact/Reviewer/Owner 二次确认。Controller 重算 exact Record/confirmation、outcome、字段、risk/constraints、refs 与 disagreement/accepted risk；通过后按五种结果确定性路由，失败留在 Decision 并返回直白 unmet condition + repair target。Research/Roadmap/下游 Ready 细节仍待各自 Review。
48. **确认 Product Memory 四类职责投影**：每个正式 Decision（含 STOP）进入 Ledger；只有未来行动进入 Roadmap，RESEARCH 使用 Research Request，EXPERIMENT 通过同一 Plan/PRD pipeline 表达受控行动而不偷换承诺或创建 Portfolio 真源；Product Changelog 只记录 material 产品意义变化；Audit 自动记录执行事实。四者同源引用而非四套流程/真源；KMG 未接入时本地完整运行，未来接入只增加共享/发布且不重新替 Owner 决策，具体 submission/Impact 合同待 Knowledge Requirements 反推。
49. **确认历史 Decision 受新 Evidence 影响规则**：新 Signal 保留既有 Router destination 并通过 `existing_links` 关联 exact historical artifacts；按 supports、non-material delta、challenge key assumption、hit kill/recheck/material risk 分级，只有 material 项主动提醒/逐 action 处置。旧 Decision immutable，改判以新 Decision supersede；Impact List 只标真正受影响对象，不默认全量重跑。冲突合并与跨团队 Impact 实现细节仍待后续 Review。
50. **确认 Planning Refinement 与 formal Review–Optimize 分工**：Refinement 是 `product.planning` 内部可恢复生成/探索/拆解/全局协调 Loop，主 Agent 单点整合并产出 checkpoints/Candidate；formal Review 由独立只读 Reviewer sub-agents 审 exact frozen Candidate，Optimizer/主 Agent按 repair path 生成新版本。局部修复定向复审，结构问题回 Refinement，失效 Decision/Problem 回对应上游；Review attempts 完成或不可用已披露、Finding 均有 disposition 并完成确定性收尾后，才进入 Plan Ready。Plan/PRD 复用同一 engine/profile 合同，实验 intent 只条件化 rubric，不把 advisory partial review 当 Ready 证据。
51. **确认 Planning Profile Selector 与渐进重量**：业务 Router 只定业务目的地，非节点 Selector 只定 `product.planning` 内执行深度；LIGHT 一次轻量规划、STANDARD 有界 Rounds、PROJECT_SCALE 条件 Waves+Rounds，可随真实复杂度升降级且不让 PM 填问卷。选择性吸收 Better Work 的轻任务/单轮目标/范围依赖/成功停止/Evidence/checkpoint 和 Wave/Round 语义，但不复制文件、Gate或状态；父 Wave 不阻止独立 Plan/PRD Runs（含实验 intent）并行。
52. **确认 `plan.slice` PRD 切片**：同时使用横向模块化与纵向迭代化，从完整 Plan 产生可分别交付/验证/上线/回滚的 PRD Candidate Slice Map/List；不按模块、迭代、矩阵格或前后端机械拆，也不写 PRD 正文。Agent 先提出含目标/结果/阶段/模块/依赖/验证/理由的建议，只在 material 合并/拆分取舍时打断 PM。
53. **确认 `plan.coverage.validate` 规划覆盖检查**：覆盖是每件重要事项有明确去向，不是本轮全部实现；检查遗漏、重复/冲突、端到端体验、依赖和 Decision/Roadmap/Assumption 一致性。按 Profile 内联/简表/只读挑战，只诊断不静默修 Plan、不自动 BLOCK，Finding 交 `plan.reconcile`。
54. **确认 `plan.reconcile` 规划协调**：将 Coverage、局部深化和新 Evidence Finding 放回整体结果，恢复 Plan/Module/Iteration/Slice/Dependency/Roadmap 一致。非决策本质调整可自动形成 checkpoint；material Decision/承诺/风险变化须 Owner确认并写既有账本，可回 Slice/Iteration/Decision/Learning；允许带责任人和复查条件的显式灰度，不建审批 Gate或第二真源。
55. **确认轻量 Plan Ready，随后移除固定 Plan 确认**：程序化 `plan.ready.gate` 只检查 current Plan、Coverage/disposition、advisory Review finalize、依赖/冲突与 material Decision refs。按需一页摘要不是审批；只有新 material 产品取舍回 Product Decision。PASS 仅为 current activated+eligible slices 创建 PRD Runs。
56. **纠正 PRD Workspace Initialization 的职责表达**：后台确定性生命周期动作正式命名为 `prd.workspace.initialize`，面向人统一叫“准备 PRD 工作空间”；不作为与 PRD 语义构建/模板编写能力并列的智能 Graph Node。Controller 只创建/绑定/登记/保存/流转/校验，Agent 才组织产品语义、按模板编写 PRD、回应审查并优化；第一版无已发布消费者，因此不实现曾讨论过的旧名兼容层，也不提前冻结初始化的完整 Schema、Gate 或 HITL。
57. **根据 Better-Product-Plan 实模板取消默认双文档**：实际模板和 planning-artifact mapping 已能承载完整 PRD 语义，因此保留 `prd.content.build → prd.render` 的能力分离，不默认持久化完整 Product Spec。简单 Run 同一次 Agent attempt 直接形成 PRD candidate，复杂跨会话/多模板/多 Agent/模板迁移场景才可保存内部 checkpoint。过渡 fallback 使用仓库 exact path，并补映射父 Plan/Slice/Decision、增量贡献、证据状态、Shared Contract/Evals 和文档生命周期；不兼容模板必须扩展或失败，不能静默丢字段，也不把项目 checklist 通用化；第一版不实现曾讨论过的 `spec.build` 兼容 alias。
58. **把 PRD 生成收敛为单一可恢复节点与 Template Profile**：用户只看到 `prd.generate / 生成 PRD`，内部连续运行 content build、确定性 template resolve 和 Agent render，不增加节点/HITL。模板按项目配置、受信知识、BPG 当前配置的 default/fallback 优先级解析；缺项进入扩展/附录或判不兼容，不编造事实。当前 upstream 模板作 exact versioned fallback，领域无关 general Draft 只是 Bootstrap 候选；未来由配置升级、pin、回滚，具体内容与 promotion 另行优化。一期不建 frontend/backend/service 模板库或 Template Router。
59. **把 Evals 适用性与履行状态拆成双维合同**：`evals.applicability.decide` 收进 `prd.generate` 内部，输出“普通 AC 足够 / 建议增加 / 必须提供”及 `NOT_NEEDED / RECOMMENDED / REQUIRED`；生成/待审/已审/缺输入受阻另记 Fulfillment。旧 `NOT_REQUIRED/DEFERRED` 显式迁移且保留历史。复杂性不自动触发，概率性/多合理输出/分布或样本风险通常 REQUIRED；RECOMMENDED 默认不硬阻塞，REQUIRED 缺 Pack 可继续 Candidate 但不能 Ready。未来 generator 是适合 bounded sub-agent 的内部原子能力，Test Graph 才执行 runner 与测试 verdict。
60. **确认按需可恢复 `evals.build` 与 TDD-ready 扩展边界**：PRD Run 在 stable content 后并行 render 与 Eval build，内部 scope/generate/review 不暴露成三节点，join 绑定同一 exact version并按 impact 失效。Pack 以核心结果/主路径/关键边界/发布风险覆盖为止，Agent 不自造 Ground Truth，专业 Reviewer 只读。未来可扩为功能测试意图/场景/AC/状态分支异常/回归建议，但正式测试用例/代码/环境/执行/缺陷/verdict 仍归 Test Graph；当前名称不改，Roadmap/umbrella name 未完成。
61. **把 PRD 阶段收敛为 Fidelity-first + Programmatic Ready**：退役默认 `prd.owner.confirm_understanding` 与固定 `handoff.owner.approve`，旧事件只保留兼容解释；Product Reviewer 首先证明 Candidate 忠实于 exact Decision/Plan/Slice/Knowledge/Evidence/constraints，material 新内容返回最早上游。Review 收敛后的一页摘要按需同源渲染；Controller Ready 后自动形成 self-contained release，本地 Handoff 不再物理打包，Connector policy 另决定 dispatch。BPG Released、Connector Sent 和组织外置汇总审批保持三种不同事实，不新增 Node/Gate/固定 HITL/第二真源。
62. **将 Product Goal-Based Audit 的目标忠实内核嵌入 `review.parallel`**：从同一冻结 Decision/Plan/Slice/Evidence/Knowledge/Guardrails/System Acceptance/Candidate 生成 Goal Fidelity Review Packet，始终由既有 Product Reviewer 逻辑 profile 检查目标与范围忠实度；其他角色条件化，LIGHT 可合并执行却不可丢失该检查。独立首轮、可施工 Finding/分歧合同、最多两轮高影响 review-of-review、delta + global regression 和两轮 no-progress 复用现有 Review–Optimize；完整七阶段、重复 Owner 承诺确认、分数/覆盖率、`.product-audit`、Shell 脚本与每轮人工确认明确不吸收。完整 Skill 仅保留给项目架构、版本发布和 Roadmap 里程碑级审计，本决定不新增 Node/Gate/固定 HITL/重型 Artifact。
63. **确认 `review.aggregate / 审查意见汇总` 的轻量可恢复 join 边界**：它保存 reviewer 到达/失败/stale 与高影响复核上下文，主 Agent 聚类、保留分歧/不支持建议并提出最早 repair target，Controller 只检查 required attempts、exact bindings、Finding 合同与无损追溯后写状态。LIGHT 可同一用户动作自动完成，但仍留恢复记录。Aggregate 不修改/生成 Candidate、不自报 Ready，复用现有 Review Record/Finding/Verdict/Disposition/review_summary，不新增 Artifact/Gate/HITL/第二真源。
64. **退役 `review.gate`，采用轻量 `review.finalize`**：advisory Reviewer 没有批准/阻塞权，Gate 名会误导。Controller 只检查 attempts、Finding dispositions、exact Candidate 与同源内审意见；不裁决专业观点、不要求 PASS、不因 concern level 阻塞。未完成的主 Agent采纳修订进 optimize，上游根因返回上游，其余 concern 披露后进入唯一 Ready。
65. **确认 `prd.optimize` 与有界 Review–Optimize 子图**：只对主 Agent采纳且根因位于 current PRD 的聚合建议做一轮批量最小必要修订，产生一个新 archived Candidate、delta、finding→change 和 re-review scope；根因在上游时必须返回，不在 PRD 圆回来。Optimizer 只提 claimed repair，独立 Reviewer 才确认 status。Candidate version 与 Review Attempt 分离；LIGHT/STANDARD/PROJECT_SCALE 上限 2/3/4 轮，连续两轮 no-progress 提前停止且不自动 PASS。
66. **确认 `prd.ready.gate / PRD 最终就绪检查` 的一期基线**：它是 Controller 在 Review Finalize 后执行的最终确定性 release boundary，只查 current exact Candidate、同版本 Review/finalize/内审意见、current 关键 refs、REQUIRED Evals、Template/Document Experience/version/changelog 与既定机械合同。advisory concern 披露但不阻塞。仅输出 `READY | NOT_READY`；通过无 Owner 二次确认自动生成 self-contained release。
67. **以自包含 Released PRD 取代独立物理 Handoff Package**：`archived/` 与 `released/` 中每个 exact version 使用 `<PRD-ID>_<短标题>_v<版本>_<日期>/` 目录，主 Markdown 同 stem 并只相对引用本目录 assets；无附件不建空目录。Ready 后 exact Markdown+assets 直接成为 canonical 本地交付单元，DOCX/PDF/ZIP 按需派生。第一版不实现曾讨论过的独立 `handoff.package.build`、legacy event 或迁移 parser，不再复制十几个上游文件或生成独立 manifest/packager；Feishu 原生 Doc 路径保持权限/素材/格式/项目关联原型验证。
68. **确认可选可恢复 `handoff.dispatch / 产品交付发送`**：它只读 exact Released artifact set，按目标 `disabled/manual/auto_when_ready` policy 调用 Adapter；默认 manual，自动需要 exact versioned preauthorization。幂等 identity 绑定 PRD ID+Release+Connector+Target+Action，UNKNOWN 先 query/reconcile，多目标独立 attempts/receipts 且共享 source。无 Connector/权限不影响本地 Ready/Released；receipt 只证明对应远端动作，不等于 Received/Accepted/Approved。无新 Package、内容审批、公开命令、固定 HITL 或第二真源；统一回传与影响处理见第 69—71 项。
69. **统一所有外部业务输入到 `signal.ingest`**：自然语言/Skill、Issue Collector、飞书、研发/测试 Graph 和未来 Input Connector 只传输原文/原生结果并自动附加 provenance；Core 中央区分 status、typed result 与 Product Signal。外部不填内部 Schema，Connector 不作产品分类/路由；普通/派生 Signal 才进入 prepare/relate/classify/route，Router 不增加目的地，也不保留下游专用入口或兼容别名。
70. **确认下游回传按最早受影响点返工**：状态/执行结果先更新绑定记录，新产品事实才派生关联 Signal；Implementation Deviation、PRD、Planning、Decision、Problem Learning、Roadmap 与独立新机会分别回到最早被证据实质影响的有效层。普通执行反馈不全链重跑，Released PRD 不覆盖，material 修改以新 Candidate/release 或 Decision supersede 并保留 Impact/downstream refs。
71. **分离反馈提交、语义 materiality 与状态权限**：任何来源可提交，但不得直接 reopen/invalid 上游或选返工点；Agent 以 exact binding、新可核查信息、是否推翻 assumption/scope/rule/AC 做无分数的轻量判断，说明影响层、依据/反方、建议和翻转条件；Controller 只执行 policy/权限明确的动作。普通意见 record+link，机械 result/local repair 可自动，material Decision/承诺/Roadmap 变化才需有权 Owner 新决定，不新增审批 Gate。
72. **把 Run Resume/Audit 收敛为两个最小机器记录**：每个 Run 只持久化 current state snapshot 与 append-only meaningful event stream；前者保存 current/last/next、exact refs、等待/暂停与 side-effect receipt，后者只记 material checkpoint、正式状态/Owner/Finding/副作用/暂停失败/sub-agent 结果。恢复按 state→refs/files→外部/分支变化→直白 Resume Brief→current step，material change 先走 stale/Impact。Git 管内容，State 管位置，Audit 管关键变化；不冻结示例文件名/完整 Schema，不保存 hidden CoT、逐 tool call/措辞/草稿 hash，不新增 Registry/数据库/Service/MCP/CLI/Node/Gate/HITL。
73. **把独立 Experiment Fast Lane 折叠进同一 Product Pipeline**：保留 `EXPERIMENT` 作为“以受控行动购买信息”的正式 outcome，但 Decision 后复用 Product Planning/PRD/Evals/Review/`prd.ready.gate`/Released/Handoff；同一 PRD 条件化保存关键未知、exposure、变化、测量、结果 mapping、Guardrail/stop/rollback。规划充分度可按 intent/风险调整，文档与安全底线不降；结果统一进入 `signal.ingest` 并返回 Decision。一期无 Experiment Profile/Plan/PRD/Ready/Handoff/Portfolio，不新增 Node/Gate/Artifact/HITL/模板/命令。
74. **确认 MVU 驱动的 `RESEARCH / EXPERIMENT / COMMIT` guide**：先找当前最有价值未知，再选择最低成本的可靠证据方式；离线来源能回答则 Research，必须来自真实行为且 action 可控可测可停可回滚则 Experiment，核心方向已足够且团队愿承担长期责任才 Commit。Agent 必须给一个首选、为何不选相邻替代和翻转条件；拒绝自由漂移、固定评分和 PM 自选菜单，不新增 Node/Gate/Artifact/HITL。
75. **固定 STOP/WAIT/future COMMIT 与历史重审边界**：STOP 结束当前主动方向，WAIT 保留未承诺可能性且必须有 review window/trigger，已决定未来做使用 `COMMIT + SCHEDULED / CONDITION_TRIGGERED`。所有 Record、exact snapshots 与条件不可覆盖；新信息仅在命中条件/关键假设/material 风险机会时提醒，维持追加结果，改判以新 Record supersede；不建 watcher 或全量周期重审。
76. **确认 Knowledge source coverage、继续推迟 Node 17 接口**：所有正式 Decision 及其维持/复查/推翻/supersedes 都是未来 KMG Raw Source Corpus 必要候选，不能只存 Released PRD 或压缩最终结论。具体 copy/reference/index、提交时机、权限、自动化、采纳/保留/同步仍由未来 raw+derived Knowledge requirements 反推；当前不新增合同、真源或节点。
77. **合并 Problem Owner 责任到 Product Decision**：固定 `problem.owner.confirm` 退役；Problem Ready 只做 advisory Review 完整性与 exact refs 机械检查。Decision Brief 同屏展示 exact Problem，Owner outcome choice 承担责任；material 问题纠正返回 Synthesis/Learning。
78. **移除固定 Plan Owner Confirmation**：忠实 Planning 自动完成，按需一页摘要不是审批；只有超出 exact Decision 的 material 新取舍回到同一 Product Decision，Plan Ready 不再检查确认记录。
79. **完成 HITL Density Audit 当前 disposition**：正常 Discovery/Product 路径只保留 Product Decision 一处固定人类产品责任点；其余仅为高价值信息获取、material choice 或外部副作用授权。可靠 Implementation Deviation 可零内容确认，外置团队审批在 Graph 外。
80. **取消 Bug 固定 Route Confirmation**：可靠 Assessment 满足五项证据条件时 Controller 自动分流；只有冲突、PM-only事实、material路线差异或人工纠错才最小澄清，override 留审计但不改旧 Assessment。
81. **把一期 Reviewer 全部收敛为 advisory 并生成同源内审意见**：未解决/分歧 concern 与 exact PRD 同目录独立展示，主 PRD 只放短状态/相对链接；Review 不再拥有 Block/approval/waiver，外置团队保留最终审核。
82. **增加进行中访谈的运行时控制并收紧默认跳过**：单一公开 Skill 增加 `interview skip|resume`，总计十一个 intent words；完整 Discovery 默认至少一次实质访谈/等价对话，除非无 material PM-only unknown 且低信息增益，或用户显式 skip。

V1.1 关于 Problem Discovery、认知路由、五种 Product Decision、Product Evals、父子 Run、State Controller、知识边界、模板配置、Host Adapter / Connector 两分、无 Driver 层和轻量一期形态继续有效。

---

## 28. 仍需原型验证的事项

以下内容不是 V1.4 已证明事实：

V1.4 distribution/eval closeout 后仍优先 OPEN：

- Codex `plugin.json` 的最终字段形态、真实 discovery 行为、安装位置与 symlink 处理仍需 Host conformance prototype；唯一公开 Skill/allowlist 是要求，不是已验证事实。
- `build-manifest.json` 的最终 Schema、artifact hash 归一化算法、dirty tree 候选政策和 `execution_contract_fingerprint` 输入集合要在 Wave 1 实现并固定测试向量。
- Plugin Contract Suite 的 runner 与 direct/indirect/follow-up/negative activation 样本尚未实现；必须在 fresh installed copy 上运行。
- Product Golden Suite v0.2 的 migration mapping、fixture、evaluator 与阈值尚未实现；G01/G03/G04 继续 `FUTURE / NO PASS`，v0.1 只作 legacy 输入。
- general v0.1 的 promotion criteria、兼容性证据和具体时点仍属 Roadmap；V1.4 只取消固定人工 Review 前置，不自动激活该模板。

为避免把长清单误读成 156 个同等优先级的新需求，可按主题定位：1—15 主要是 Core/Host/Reviewer/Evals 基础假设，16—34 是规划、实验和产品记忆，35—50 是 Signal Intake、用户入口与 Router，51—57 是 Incident/Bug，58—64 是 Evidence 与 Learning，65—71 是 Document Experience，72—77 是问题假设审视，78—83 是 Learning Loop 恢复、来源路由与 Interaction Policy，84—87 是 PM 访谈/辅导/挑战协议，88—90 是 Learning completion 三维合同，91—94 是可选 Analysis Method，95—98 是 PRD 文档生命周期，99—102 是 Problem Synthesis 收敛、版本和恢复，103—106 是 Problem Ready 执行者隔离、Owner 权限和确定性 Controller，107—110 是 Problem Quality Review 收敛，111—114 是横向 sub-agent 执行/Host 能力，115—119 是未来 Multi-Agent Collaboration 协议和治理，120 是项目 Git preflight 与并行 worktree 边界，121—131 是 Product Decision、风险、Memory 与新 Evidence，132—137 是 Planning/PRD Slice/Coverage/Reconcile/Plan Ready，138—153 是 PRD generation/Evals/Review/Ready/Handoff/统一 Intake/Resume，154—156 是 MVU 决策 guide、STOP/WAIT 条件重审与未来 Knowledge source coverage。具体优先级仍由 §30 的 Node Review 和 Slice 1—8 的真实证据决定；本节只保存风险，不把风险自动升级为实现承诺。

1. 最合理的持久节点数量和合并方式。
2. Discovery 五轮默认预算是否合适。
3. Codex `detect_only` 模式对真实误操作的检测效果。
4. 第二 Host Adapter 是否需要扩展当前 Host Contract。
5. 真实研发消费者需要的 Handoff 字段和拒收原因。
6. 飞书真实租户的文档创建/更新、素材上传、权限、项目关联、复杂格式降级、查询/reconcile 和幂等能力。
7. PARTIAL 快照的项目级豁免是否过严或过松。
8. 父计划变化的影响分析能否足够准确地只失效相关子 Run。
9. Reviewer 默认组合是否适合不同项目风险。
10. Guided / Standard / Compact 三种 PM 交互模式的实际辅导效果、耗时和退出条件。
11. Cognitive Router 的选择准确性、上下文成本和不同认知基座之间的冲突处理。
12. `implementation-plan-v2.md` 声明 20 个认知基座，但当前本地实现中没有找到独立的 `cognitive-protocol` Skill；目录、命名和实现真源需要在建设前对齐。
13. 哪些项目/PRD 必须生成 Product Eval Strategy 与 PRD Eval Pack，默认 Applicability Policy 是否过严或过松。
14. Eval Pack 的最小合同、Ground truth 治理和研发/测试真实消费者是否接受。
15. 自动化 `evals-generator / evals.build` 的生成质量、成本、可维护性、并行 join/stale 精度，以及何时需要外部 Agent Connector；TDD-ready Test Design Contract 的稳定边界、umbrella 命名和 Test Graph 消费方式仍待独立 Roadmap 设计，V1.4 不声称这些能力已经实现。
16. Module Map 的合适粒度、模块内聚/耦合 Rubric 以及不同项目类型的边界差异。
17. Iteration Map 是否能稳定形成既小步又端到端成立的增量，避免无价值碎片和隐性大爆炸交付。
18. 跨模块 Batch 的最小合同、原子发布边界和依赖失败时的降级方式。
19. Target Operating Outcome 与 Non-sacrificable Guardrails 能否被 Reviewer 稳定理解，且不会退化成宽泛愿景和口号。
20. 四个逻辑规划视图在轻量内嵌与独立产物化之间的切换规则，是否既不丢语义又不过度增加文档负担。
21. `EXPERIMENT` 作为同一 Plan/PRD delivery intent 是否能让 PM、Reviewer、研发和 Connector 清楚区分“购买信息”与“长期承诺”，同时避免再次演化成独立 Profile/Ready/Handoff。
22. R0—R3 的项目默认阈值、升级规则和跨域风险合并方式。
23. Sponsor-directed / accepted-risk `COMMIT` 的使用频率、误用风险和真实组织接受度。
24. 一期 advisory concern 是否会被实现或人类误读为 BPG formal Block/approval；内审意见能否让外置团队快速聚焦而不把建议误当正式需求。
25. 未来若外置审核被真正无人值守流程替代，何时才有足够证据启动专业身份、policy、action-scoped blocking 与 waiver 的独立设计；当前不得预建。
26. 未来真实并行实验规模是否会出现受众重叠、指标污染、资源冲突或 Zombie 管理需求，并证明现有 Decision/Plan/PRD/Run/Roadmap 关系不足；在此之前不得预建 Experiment Portfolio 真源、Schema、Registry 或 Service。
27. 带实验 intent 的 typed result 经统一 Intake 绑定 exact Decision/PRD/Run 后，其数据完整性、选择性解释检测和 inconclusive 校准能否可靠支持回到 Product Decision，而不形成第二条 result-return Graph。
28. 外置团队对遗留 concern 的采纳/拒绝/补证回传能否与 exact Review Record 对账，而不生成第二真源。
29. Golden Case Runner 能否可靠隔离 evaluator-only 文件，以及 `pm-response-bank` 在不同 Host 上是否产生可比的互动轨迹。
30. G03 的 Bug Baseline Assessment 能否跨 Decision/PRD/AC/设计/API 合同/对外承诺/历史行为可靠识别当前有效基线、优先级、冲突与 superseded 状态；证据完整时 0—1 轮是否既高效又不会压低必要追问。
31. 产品决定的 materiality 分级能否让微小决定保持轻量，同时防止 Agent 把重大决定降级为紧凑记录。
32. Decision/Roadmap 变化的逐产物 Impact List 是否具有足够准确率，避免漏掉失效对象或无差别触发全量复审。
33. Better Product Graph Proposal 与 Knowledge Maintenance Graph canonical 发布之间的延迟、冲突和 supersedes 对账，是否会造成不可接受的等待或双重真源。
34. Roadmap 承诺阶段、时间 horizon 与 epistemic confidence 能否在不同 PM/Host 上保持一致理解，且 Product Changelog 是否能稳定捕获真正具有产品意义的变化。
35. G04 的“初始 2 轮 × 每轮 3 问”是否能在常见 Junior PM 场景中兼顾认知质量与效率；most valuable unknown、AI 可自行检索边界及“何时停止追问转实验”能否被稳定判断。
36. 自然语言与显式 Skill 在 Codex Host Adapter 上能否稳定映射同一 Core intent，未来 Host 命令能力是否需要扩展而非改变现有合同。
37. `signal.ingest` 的原子接收、幂等和敏感性元数据能否覆盖粘贴文本、附件、一次性链接与外部 Connector payload，而不产生半接收 Signal。
38. `signal.relate` 在历史索引可用时的 duplicate/cluster/contradiction 准确率、权限过滤和成本，以及 `NOT_AVAILABLE` 降级是否会影响后续路由质量。
39. Input Connector 的 Inbox 默认策略、高危提醒阈值、批量激活和噪声控制能否避免“每条 Issue 启一个 Run”与“重大事故淹没在 Inbox”两个极端。
40. 自然语言 implicit invocation 与十一个 intent words 的解析歧义、缺参提示和 guided/default prompt，特别是 `interview skip|resume` 目标 Run 解析，能否避免误启动 Run、误停其他 Run 或误判外部写入意图。
41. 单一 `$better-product-graph` Skill 是否能保持易发现性；`handoff` 被误解为 dispatch、`capture` 被误解为 new 等风险能否通过反馈与确认边界控制。
42. 现有仓库/目录/文档路径向 `better-product-graph` 迁移时的消费者清单、兼容窗口、回滚和旧链接保留方式；当前文档尚未验证任何物理迁移。
43. Classifier 零交互并自行查询授权信息的准确率、成本和延迟；Knowledge 不完整时 known/unknown/conflicts 是否能被稳定区分。
44. Router 能否准确识别“唯一 PM-only 操作事实”，避免 `NEEDS_CONTEXT` 过度追问、误把 Discovery 问题前置，或在持续伤害下错误等待。
45. `existing_links` 对 Signal/Run/Decision/Roadmap/Incident 的匹配准确率、版本有效性和权限过滤，以及 association 与 destination 分离后能否避免把新问题错误挂到过时对象或吞掉新证据评估。
46. `SCHEDULED / CONDITION_TRIGGERED` 的时间/触发验证、Owner 响应、依赖变化、过期清理和 activation event 是否会产生僵尸 committed Item 或误启动 Plan Run。
47. signal-scoped Classification/Route history 与 `audit.view` 的权限、隐私、体积和可理解性；只保存结构化依据而不保存 chain-of-thought 是否足以支持真实问责和调试。
48. 普通 reroute 与 Product Changelog Proposal 的 materiality 边界是否会造成变更噪声或遗漏正式产品行为变化。
49. 四目的地优先级、activation intent 和持续伤害判断能否在噪声输入下稳定收敛，避免重大事故落 Inbox、普通反馈误升 Incident 或可信 Bug 基线被漏掉。
50. 人工改路规则能否既允许 PM 纠正激活/产品判断，又防止无 candidate evidence 进入 Bug Check、无可靠 baseline 归为实现偏差、未评估降级 Incident，以及通过 override 绕过 Assessment 和五项自动分流证据条件。
51. Incident Verification Packet、`NOT_AVAILABLE` 和三项轻量机械检查能否在不牺牲证据/权限边界的前提下缩短持续伤害信号的交接时间，并避免低质量空包淹没研发。
52. Development Graph 未接入时的人工/Connector Incident 交接、研发回传对账和 `WAITING_ENGINEERING_FEEDBACK` 恢复能否可靠运行，且可选 Product Response 不会膨胀成默认事故管理流程。
53. `IMPLEMENTATION_DEVIATION / PRODUCT_LOGIC_DEFECT / SPEC_AMBIGUITY` 的分类准确率、冲突校准和人工 override 规则，能否防止产品缺陷被误交研发或实现偏差被过度规划。
54. 多份基线材料的权威性优先级、版本有效性和历史行为证据门槛如何项目化配置，避免 Agent 用最容易检索的材料冒充当前真源。
55. 快速 Product Decision 适用的“证据清楚/改动小”阈值，以及何时必须升级正常 Planning + 1..N PRDs，仍需真实 change case 验证。
56. Bug Fix Brief 的五项轻量检查、advisory 风险 Reviewer 触发阈值和研发消费者接受度，能否在不过度加重流程的同时阻止规则漂移并把高风险 concern 透明交给外置团队。
57. `NOT_NEEDED` 与 Bug Eval Pack 的 applicability 能否稳定区分确定性和非确定性行为，特别是 AI、推荐、搜索、排序及难复现问题。
58. `evidence.collect` 与 `evidence.map` 的边界能否在真实权限失败、来源更新和模型重算时减少重复抓取，同时不会让 provenance 记录重到阻碍 PM 使用。
59. `OBSERVATION / SOURCE_ASSERTION / VERIFIED_CLAIM / INFERENCE / ASSUMPTION / PREFERENCE / PROPOSAL / UNKNOWN` 及四类关系能否覆盖常见材料；Agent 是否会过度授予 `VERIFIED_CLAIM`，或用语言流畅度掩盖冲突和范围限制。
60. 同源识别、来源独立性、代表性、新鲜度和反证说明能否被稳定校准，尤其是重复反馈、转述链、历史行为、竞品材料和 PM 口头信息。
61. MVU 选择是否真正降低决策不确定性，还是在多轮中不变、频繁漂移或被最易获取的信息劫持；“实验的信息价值高于继续讨论”如何在不同产品类型中判断。
62. Evidence Request 的字段和语言能否让 Junior PM 清楚知道找谁、查什么、什么算有效以及何时停止，同时不把 AI 本可查询的工作转嫁给人类。
63. 按拟议行动、风险、可逆性、可测量性和回滚判断证据充分性能否既允许低风险学习，又防止高风险行动被“可逆实验”话术降级；人工 override 如何在不破坏 status/disposition/recommendation 分离的前提下设计，仍需后续讨论和原型验证。
64. Run-local Evidence Map 到 Knowledge Change Proposal 的去重、冲突、适用范围、新鲜度和发布延迟，是否会产生重复 Proposal、长期 pending 或把局部事实错误推广成跨项目 canonical knowledge。
65. Core 最低理解项是否能覆盖不同项目、语言与受众，同时避免变成抽象口号或迫使所有产物使用同等重量。
66. artifact Profile 解析能否稳定识别用途、受众与风险，防止重大 Decision 跳过语义 Review，也防止 Incident/Bug 被错误套用重型 Profile。
67. Human View Renderer 能否在不引入事实、隐藏 unknown 或丢失作用域的前提下生成真正可读的视图；结构化 source 与自然语言间的语义保真仍需真实样本验证。
68. Validator 对 source/policy/profile/template stale、最低理解项和 Handoff 状态的误报/漏报率，以及依赖链变化后的重渲染成本是否可接受。
69. Readability Reviewer 对术语堆叠、结论埋藏、流畅但误导和重复的判断一致性、成本与时延，能否在不被误读为 formal Block 的前提下改善理解。
70. 项目模板与 Profile 最低项映射、`better-product-plan` 默认模板和 Supplement 是否会产生重复、章节错位或新的易读副本漂移。
71. 八个一期 Profile（含 Plan Ready 一页摘要 `product_plan` 与 PRD companion `internal_review`）是否覆盖最小真实消费者；on-demand machine view 的权限过滤、审计可解释性，以及后续 Profile 逐项冻结的兼容策略仍需原型验证。
72. 独立问题假设审视是否比合并进 Map/Learning 更早发现方案锚定并改善后续访谈，同时其额外节点、checkpoint 和模型调用成本是否合理。
73. 动态识别方向性关键假设、反证、历史决定、no-action counterfactual 和症状/原因的准确率，能否避免退化成固定 checklist、为了“有反方”制造稻草人，或在熟悉框架下漏掉真实替代。
74. 问题假设审视能否稳定只选一个真正改变后续信息来源、问题框架、路线或行动的 MVU，并推荐最合适的来源与可执行信息请求；它与 Evidence Map 当前 MVU 的继承/覆盖边界，以及如何避免十几个同权问题，仍需原型验证。
75. `MATERIAL_INPUT_CHANGE / FUNDAMENTAL_REFRAME` 重跑触发能否避免普通补证反复重算，同时在根本框架变化时及时创建 superseding checkpoint。
76. `ROUTE_REEVALUATION_RECOMMENDED` 的误报率、route.select 回接与审计体验，能否避免建议被误当实际 reroute，或让错误路线因责任边界过严而未被修正。
77. structured rationale 是否足以支持恢复、复核和 Junior PM 辅助而不泄露 hidden Chain-of-Thought；run-local checkpoint 是否会被误用为正式 Problem Definition、知识真源或 Handoff 内容。
78. Learning Round、Evidence Request 与 `WAITING_FOR_EVIDENCE` 能否在 PM、Owner、用户研究、异步数据任务等不同来源的跨天等待、部分答复、超时、来源切换和知识变化时准确恢复，避免重复查询或漏掉新证据。
79. 每轮 exactly one core MVU 与少量紧密相关请求能否平衡焦点和效率；内部动作只记事件、不升顶层节点是否仍有足够可观测性与维修边界。
80. 七类 `source_resolution_type` 的区分准确率，尤其是 AI 可查、PM 私有背景、专业 Owner 和用户研究之间的误路率，以及重新选择来源的 supersede 体验。
81. “进一步学习是否仍可能改变当前拟议行动”的 action-relative 停止判断能否避免无限研究和过早收敛；用户/场景/目标/阻碍/影响、冲突、remaining unknown 与信息价值检查在不同项目是否稳定。
82. `NO_PM_INTERVIEW` 在 Codex Host/State Controller 中能否真正拦截改写后的 PM prompt，同时不误拦 Product Decision、外部写入授权、专业信息来源或用户研究；skipped-interview impact 对 Junior PM 是否足够清楚。
83. `interaction=no-pm-interview` 与 `interview skip|resume` 的自然语言解析、CURRENT_RUN 作用域、进行中原子停止、最高价值 Unknown 恢复和审计能否避免误应用到其他 Run；完整 Discovery 的默认访谈例外能否稳定判断，未来 `NON_INTERACTIVE` 保留位是否造成能力误报。
84. bounded joint judgment 六步能否在不显著增加打断时长的情况下改善 Junior PM 的判断质量；解释、示例和选项脚手架是否会无意诱导答案，或让 Agent 以“辅导”为名植入偏好。
85. `LIGHT / STANDARD / STRONG` 能否依据风险、证据冲突和可逆性稳定校准，并对资深/Junior PM 使用同一质量标准；模型是否会把表达自信、职位或资历错误当作强度依据。
86. “回答后只做一次最高价值挑战”能否在避免无限争辩的同时揭示关键反证；PM 坚持后的分歧、authority、验证/重审/回滚条件是否足以防止静默迎合、无权推进和过早结束。
87. Learning Round 的最小结构化记录能否同时支持恢复、复核和责任边界，又不默认保存全量逐字对话或泄露 hidden Chain-of-Thought；必要原句的同意、权限与保留期限需要真实项目 policy 验证。
88. State Controller 能否稳定阻止 status/disposition/recommendation 混写，尤其是 WAITING/PAUSED 误标完成、COMPLETED 缺 disposition，以及建议被 Host/Connector 误当授权。
89. `INSUFFICIENT_TO_PROCEED` 的已尝试、缺口、原因、建议和 restart condition 是否足以支持以后恢复，又不会让系统为追求结束率滥用该 disposition 或伪造 Synthesis。
90. Problem Quality Review 的 advisory Finding 与机械 Candidate/ref 不一致能否稳定分开：Controller 不因 concern level 阻止 Product Decision，但必须拦截 stale/missing/mismatched Candidate、Review disposition 或上游 refs；repair target 映射仍需实现测试。
91. 调用五问与 Level 0—3 能否让 Agent 在默认 `NONE` 下稳定识别方法的真实增量，避免因“显得专业”过度调用或因成本估计不准错过有价值分析。
92. Method Card 的 applicability/required inputs/limitations 能否充分约束不同项目语境；卡片版本变化、Skill 版本绑定和旧分析复核方式仍需原型验证。
93. Journey Map/KANO 的输入完整性、适用范围和作用域外推能否被可靠检测，尤其是虚构情绪旅程、单条反馈 KANO 分类和把方法输出提升为 Evidence。
94. 多方法的“不同增量”说明能否阻止框架堆叠和虚假置信；未来真实 Golden Case 应如何证明某方法值得接入内部 Atomic Skill Module，尚需运行证据。
95. `archived/` material checkpoint 阈值能否既保留 Review/人工编辑/模板迁移证据，又避免 autosave 噪声和过高存储/阅读成本。
96. Ready 后从 exact candidate 生成 release 的原子性、崩溃恢复和并发 CAS 能否避免“Ready 已通过但 release/Changelog/current 只写了一半”。
97. 文档呈现变化与产品语义变化能否被可靠区分，防止把规则/AC 变化伪装成排版修订，或让纯文案改动触发不必要的完整 Product Decision。
98. invalidated/revoked release、current pointer、已有 Handoff 与 replacement/restart reason 的对账能否在真实知识影响和多次 release 后保持一致，且不删除历史文件。
99. Synthesis 对 material direction-changing gap 的识别能否避免假完成和无意义返回：既不过早冻结错误 frame，也不把可保留的小 Unknown 反复送回 Learning。
100. exact Discovery input binding、stale detection、失败恢复与 supersedes 能否在 Map/Learning/Knowledge 更新后稳定重算 Candidate，避免读取 `latest/current`、原位覆盖或重复搜索。
101. Problem Definition Candidate 能否以足够清楚的用户/场景/目标/阻碍/影响/期望改变、Evidence/Assumption/Unknown、scope/non-problems 和用户方案关系支持复核，同时避免方案泄漏、补造 Evidence 或为了完整删除 Unknown。
102. Synthesis checkpoint 的恢复成本和下游 exact Candidate 引用能否保持轻量；Quality Review、Problem Ready 与 Product Decision 是否会误把 `COMPLETED`、Candidate 或 Synthesis Audit Event 当作已经完成 Owner choice。
103. 同模型不同隔离上下文能否让 Product Quality Reviewer 显著降低自审偏差和提示注入影响；专门 review Skill、独立 attempt 与外部 Reviewer Connector 的一致性、成本和故障降级需要真实 Case 验证。
104. 一期项目配置/Host identity 能否稳定识别当前 Product Decision Owner，避免身份缺失或跨项目误认；自然语言 outcome/scope 能否可靠结构化为一次 choice 而不重复确认；Handoff refs 是否足以支持外置汇总审批且不被误呈现为组织最终批准。未来无权 Junior PM、代理授权和角色升级出现后再单独验证 escalation policy。
105. 本地程序化 State Controller 的 versioned rules/tests、CAS、崩溃恢复和相同输入确定性，能否防止 Agent 自报 Ready、旧记录复用及 state/event/artifact 部分写入；代码规则本身的错误与迁移兼容仍需验证。
106. 原型阶段 `ADVISORY_ONLY` Agent 模拟结果能否被界面和 Host 清楚区分于正式 Gate；正式 Handoff 前的程序化重算是否存在被遗漏、重复执行或错误升级的路径。
107. Quality Reviewer 对用户/场景/目标/阻碍/影响、方案偷渡、Evidence 追溯、范围/因果、反证/Unknown 和 action relevance 的漏报/误报率，专门 Skill 是否能在不同产品类型下保持一致。
108. 四类 repair path 是否能把问题送回最早正确修复点，避免把 Learning 缺口误判为文案修订、把 Owner/Route 问题变成无效 Optimizer 循环，或由 Reviewer 越权执行建议。
109. 首次 full review、后续 delta-targeted + global-invariant regression 能否兼顾成本与回归发现率；Candidate 变化幅度多大时应重新 full review 仍需原型确定。
110. `NO_PROGRESS` 是否能及时识别只改措辞的循环并返回 Learning/正确上游或保留外置 concern，同时避免合理多轮修复过早停止；Junior PM 关键 Finding 视图能否减少认知负担而不隐藏重要风险。
111. Host 对 sub-agent 隔离、持久化、并发、取消、timeout/retry 的真实能力边界；Codex 一期若只能部分支持，`NOT_AVAILABLE / DEGRADED_TO_SEQUENTIAL` 是否足够保留业务语义与恢复性。
112. `BEST_AVAILABLE / BALANCED / FAST` 的 provider/model 映射、可得性、成本与结果质量如何校准；关键任务请求最强能力时的降级/等待 policy 需要真实运行数据，不能从文档假定。
113. bounded fan-out、budget、timeout、retry 与 required/optional join 规则能否在缩短关键路径的同时避免任务爆炸、重复研究、僵尸 sub-agent 和 optional 失败误阻塞。
114. 多 Agent 共享模型/来源导致的相关错误、aggregate 静默抹平分歧、同意被误当独立 Evidence，以及最小权限仍被 Host 文件能力绕过等风险，需要 Golden Case 和权限对抗测试验证。
115. 跨 Agent runtime/Host/provider 的 participant identity、认证和不可冒充性如何建立；同一会话换提示词、共享隐藏上下文或复用身份被误标为独立审计的检测方式仍需验证。
116. Collaboration/External Audit 协议如何版本化 exact snapshot、role、Skill/policy、capability/model metadata、权限和 `Finding/Proposal/NodeResult`，以及不同 Host Schema/生命周期如何协商兼容。
117. 跨 Agent 最小权限、项目/产物访问授权、敏感数据隔离、凭据委派和撤销如何实现，且不让外部 Agent 绕过 Human Owner、Controller 或 side-effect approval。
118. 跨天持久化、幂等/重放、超时、部分失败、离线参与者、结果晚到和 join 冲突如何处理；required/optional 语义能否避免整条 Run 被外部 Agent 可用性绑架。
119. 不同 provider/model 的成本、配额、计费证据、质量/延迟权衡、审计留存和供应商替换如何治理；何时真实收益足以从 future seam 升级为实现仍需原型数据。
120. exact project root 解析、父级 repository/worktree 复用和 HOME/广泛目录拒绝能否在不同 Host/多工作区环境稳定工作；`.gitignore`/敏感边界、Git 不可用或只读时的 `DEGRADED/BLOCKED`、并行 branch + worktree 清理/冲突整合，以及 material checkpoint/tag 粒度仍需实现测试。
121. `product.decision` 的 Draft/checkpoint 能否跨会话精确恢复而不被误当正式 Decision/route；按风险/未知选择 Reviewer 是否会漏掉必要专业审查或退化为默认全量 fan-out；Owner choice 到 Controller route 的原子性、失败恢复和五个内部动作不泄漏成伪节点，需要 Slice 1 原型验证。
122. `decision` Renderer/Validator 能否在中文及未来多语言下稳定生成自然、非术语化又不改变 machine outcome 的结论；why/反方/下一步/改判条件最低项能否避免裸 code 而不膨胀成模板文；Decision Brief、摘要和 Handoff 是否始终绑定同一 source/hash、杜绝手工第二真源，需要首批 Profile 验证。
123. 一屏决策的“三项依据/一项认知提醒/一项边界/一步行动”预算能否提高首读决策效率而不丢失 material 信息；认知提醒是否只外显真正改判发现、渐进展开是否可发现，以及高风险披露能否稳定覆盖默认预算而不被简洁模板隐藏，需要真实 Owner 复述和对抗测试。
124. Decision Record 的 Owner 五项确认层与系统自动审计层能否既减少 PM 填表负担，又稳定保留 exact refs/authorization/epistemic/supersession；material disagreement 判定和反向 `superseded_by` 索引不修改旧 Record 的实现需原型验证。
125. chosen-outcome-only `outcome_details` 能否在五种路线中稳定拒绝未选项空字段，同时让 RESEARCH 有停止边界、WAIT 不伪装承诺、EXPERIMENT/COMMIT 不与下游合同双写，需要 Schema/Renderer 对抗测试。
126. Agent 对 action/exposure 的 R0—R3 分类能否避免把问题永久贴标签、把 `RISK_PENDING` 静默降级或过度打断 Owner；同一问题在原型/实验/全量执行的重分类、Human View 条件显示与外置审核关注映射需要原型验证。
127. Product Planning 的高影响选择、深化停止条件、global reconciliation 与 affected-area review 能否在真实项目中既发现跨模块冲突又避免全量重跑；已确认的内部 Refinement Loop 如何稳定恢复，以及 Module/Iteration/Matrix 的内嵌/独立表达，应由真实消费者证据决定。
128. material disagreement 的识别和“一次实质挑战”能否稳定避免静默迎合与无限争论；低置信 COMMIT 的显示、sponsor-directed authorization 与 epistemic 分离、accepted risk/constraint 向下游及外置审核传递，需要 Golden Case 与权限测试。
129. Decision transition validation 的 versioned rules、五种 route 原子写入、reject/repair 后恢复，以及 STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT activation 的幂等性需要原型验证；尤其要证明不建 Decision Ready 仍能阻止旧 refs/缺字段流转，且不会把 Research/Roadmap/下游 Ready 职责偷渡进本节点。
130. 四类语义投影能否在本地文件实现中稳定保持 exact refs 而不复制真源；STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT 的 Roadmap/Research Request/Plan-PRD intent 投影、自动 Changelog/Audit、KMG 未接入的 local-only 标识及首次同步幂等性需要真实 Case 验证。
131. 新 Evidence 四级 materiality 分类能否避免 alert fatigue、漏报 kill/recheck 风险和无差别全量重跑；一屏提醒、Owner 维持决定记录、逐 artifact Impact 准确率，以及 KMG 冲突合并、跨团队 delivery/ack 和批量摘要阈值仍需原型验证。
132. Planning Refinement 与 formal Review 的 exact Candidate 隔离、结构/表达/Decision/Discovery repair routing、partial advisory 与 Ready-eligible verdict 区分、跨 product-plan/PRD profile 复用、实验 intent 条件化 rubric 和 no-progress 退出是否可靠，需要端到端原型验证。
133. Planning Profile Selector 能否稳定区分 LIGHT/STANDARD/PROJECT_SCALE、在新依赖/风险出现时正确升档并在范围收敛后审慎降档；LIGHT 是否真正减少开销却不丢质量底线，Wave/Round checkpoint 与独立 Plan/PRD Runs（含实验 intent）并发是否会产生双写或错误全局锁，需要真实运行验证。
134. `plan.slice` 能否在不依赖僵硬矩阵规则的情况下稳定形成大小合适、端到端、可验证且相对独立的候选；Agent-first 建议是否减少 PM 填表且只在 material 取舍时打断，消息治理等跨模块结果和 Evals 需要能否被正确表达，需要 Slice 1/2 对抗样本验证。
135. `plan.coverage.validate` 的五类检查和多种 disposition 能否既发现静默遗漏/重复/体验断层/循环依赖，又避免“本轮全实现”与无差别 BLOCK；LIGHT 内联、STANDARD 简表、PROJECT_SCALE 只读挑战的质量/成本，以及 unresolved 不被滥用为垃圾箱，需要真实 Plan 比较。
136. `plan.reconcile` 对非语义自动调整与 material Owner Decision 的区分能否稳定；返回 Slice/Iteration/Decision/Learning 的根因路由、灰度冲突的责任/复查、多个 sub-agent 方案的主 Agent join，以及新 Plan checkpoint/Impact 是否保持同源，需要端到端恢复测试。
137. 按需 Plan one-page summary 是否足以让 Owner/外置读者正确复述当前结果、激活切片、后置项和风险；取消固定确认后，`plan.ready.gate` 对 exact Coverage/advisory Review finalize/conflict/material Decision refs 的重算、可控 Unknown 边界和 activated+eligible PRD Run 创建幂等性，需要 LIGHT 与 PROJECT_SCALE Case 验证。
138. `prd.workspace.initialize` 能否在状态恢复和 Audit 中保持唯一语义；Controller 是否能稳定只准备 workspace/refs/version/directories 而绝不触碰 PRD 语义，以及 Agent/Reviewer/Optimizer/Owner 与程序化保存/校验之间的写权限隔离，需要 PRD Run 实现测试。完整初始化字段、失败/重试仍待节点 Review。
139. `prd.content.build → prd.render` 在简单 Run 中能否同一次完成而不丢语义，在复杂 Run 中是否能按条件保存最小可恢复 checkpoint 而不形成第二正式需求；Better-Product-Plan exact template mapping、Supplement/不兼容判定、模板迁移和项目 checklist 隔离，需要真实 PRD、模板替换与恢复测试。
140. `prd.generate` 的内部三动作能否在失败后从 exact checkpoint 恢复且不暴露为伪节点；Template Profile 优先级、冲突时一次询问、必要语义扩展/不兼容、事实不编造和 archived→released 生命周期能否稳定执行；general Draft 的领域清理是否误删通用多语言/兼容/数据/安全/隐私/灰度/跨团队能力，必须经独立人审和真实非金融项目验证后才允许激活默认。
141. `NOT_NEEDED / RECOMMENDED / REQUIRED` 与 Fulfillment 五态能否在恢复、版本变更和旧 `NOT_REQUIRED/DEFERRED` 数据迁移中保持正交；复杂确定性与简单概率性样本的误判率、RECOMMENDED 被错误硬阻塞或忽略率、REQUIRED Candidate 可继续但 Ready 必须拒绝的边界，以及 bounded sub-agent generator 与未来 Test Graph receipt 分工，需要 Slice 7 原型验证。
142. `evals.build` 子节点的恢复、与 `prd.render` 同源并行 join、语义 delta→局部 stale 和纯排版不重跑能否稳定；最小风险覆盖是否避免 case 数量膨胀，synthetic/专业 Ground Truth 边界与并行 Reviewer 权限是否可靠；TDD-ready 输出能否被 Test Graph 消费而不越权生成工程测试或 verdict，需独立 Roadmap、Golden Cases 和下游原型验证。
143. PRD Fidelity 的 deterministic ref/slice/disposition 检查与 semantic Reviewer 能否稳定区分“忠实展开”与 material 新规则，避免既漏掉 scope creep/future 偷带/Unknown 升级，又把合理场景、分支、异常和 AC 扩写误退上游；退役两项固定确认后，Controller 自动 release 的原子性、按需最终摘要、Connector policy/dispatch 以及 BPG/外置审批状态隔离，需真实 PRD 与 Feishu/本地无 Connector 对照验证。
144. `review.parallel` 的 Goal Fidelity Review Packet 是否能在所有 Reviewer 间稳定绑定同一 exact Candidate/目标承诺/Evidence snapshot；LIGHT 合并角色是否仍保留目标忠实度，条件 panel 是否漏触发专业风险；首轮隔离、Finding/cross-check 字段、最多两轮 review-of-review、五类 repair verification 和两轮 no-progress 能否抑制多数票抵消致命偏离、unsupported feature 混入及无限改写，需真实 PRD、冲突 Reviewer 和弱证据 PASS 样本对照验证。
145. `review.aggregate` 的可恢复 attempt 能否稳定处理 required/optional reviewer 晚到、失败、stale 与外部结果，并证明每个原 Finding 都未丢失；语义聚类/根因关联/最早 repair target 的人工纠正率，Controller 确定性完整性检查的拦截率，以及 LIGHT 自动 join 是否既减少开销又没把 aggregate 偷换成 Gate/Ready/新 HITL，需用错并问题、丢 Finding、旧 Candidate 晚到和 required reviewer 失败样本验证。
146. `review.finalize` 能否对同 exact Aggregate/Candidate/rules 稳定重放，可靠拦截 missing attempt、丢 Finding、缺 disposition、stale binding 与内审意见错版，同时不因 Reviewer unavailable/concern level 阻塞、不裁决专业观点、不与 `prd.ready.gate` 重复，需要外置关注、旧 Candidate 和 no-progress 样本验证。
147. `prd.optimize` 的 finding→change 可追溯率、无依据范围漂移/文案掩盖结构问题的拦截率、targeted re-review 与全局不变量回归漏检、Candidate version/Review Attempt 分离准确率，以及 2/3/4 轮和两轮 no-progress 能否在不过早停止有效修订的前提下抑制文件/循环爆炸，需用多 Finding 批处理、新 Reviewer 无内容变化、上游根因和连续回归样本验证。
148. `prd.ready.gate` 的六类检查是否足以阻止 Candidate/Review/finalize/内审意见错版、REQUIRED Eval 缺失、上游 stale 和 Template/version/changelog 缺口，同时不把语义 Review、Owner 二次确认、外置审批、Connector 可用/写权、研发/测试完成或 advisory concern 关闭偷渡为前提；`N/A+理由`、`NOT_READY` exact repair/resume、同输入重放和 READY→release/Handoff 原子性需验证。
149. Self-contained Candidate/release directory 能否在标题改名、多版本 assets、相对媒体引用、大文件/Git 边界和独立复制时稳定保持 exact hashes；Markdown→DOCX/PDF/ZIP 的语义与媒体保真、无附件轻量路径，以及真实飞书租户的文档创建/编辑、素材上传、权限、项目关联和格式降级均需原型验证。Feishu native Doc 状态保持 `PROTOTYPE_REQUIRED / PENDING_PERMISSION_VALIDATION`，DOCX 手工导入只是 fallback，不是已发送事实。
150. `handoff.dispatch` 的 target policy 解析、默认 manual、防越权 auto、幂等 identity、UNKNOWN query/reconcile、并发多目标隔离和 receipt 状态映射需真实 Connector 原型验证；尤其要证明外部失败不撤销本地 Ready、同一 release 不被复制成多份 canonical content、手工导入不会无证据升级 SENT/IMPORTED，且 source invalidation 能正确触发后续 Impact 而不改写历史 attempt。
151. 统一 `signal.ingest` 能否在 Issue Collector、飞书、研发/测试 Graph 的自然语言、协议事件和 typed result 中稳定保全 raw/provenance、确定性识别 protocol kind，并在 status/result/Product Signal 三类处理间无损分流；缺失 exact refs 时 `signal.relate` 的关联准确率、最小澄清率，以及中央策略避免 Connector-local Router 漂移的效果需真实回传验证。
152. Agent 的无分数 materiality 判断能否稳定区分 evidence/result/opinion/duplicate，并定位 PRD/Planning/Decision/Learning/Roadmap/新事项的最早受影响点；具体领域中谁可触发何种状态动作、哪些证据足以推翻 assumption/scope/rule/AC，以及普通意见噪声、误 reopen、漏报 material challenge 和版本/Impact 扩散率，仍需真实样本校准。当前只确认轻量边界，不冻结复杂领域 policy。
153. current state snapshot 与 meaningful event stream 能否在暂停、跨会话、sub-agent 失败、UNKNOWN Connector result 和 branch/worktree 变化后稳定生成足够但不过载的 Resume Brief；需验证 exact ref/stale 检出、重复 side effect 防护、事件噪声比、纯格式变化误重跑率，以及 Git/State/Audit 不互相复制。不得以此扩张全量 event sourcing、Registry 或完整会话重放。
154. MVU guide 能否稳定区分“离线来源足以回答”“必须从真实行为获知”和“核心方向已足够”，既避免 Agent 随上下文漂移、固定评分伪精确和把五项菜单甩给 PM，也避免因代码成本低而忽略长期维护/机会成本；需用相邻 RESEARCH/EXPERIMENT/COMMIT Case 校准。
155. STOP/WAIT/future COMMIT 是否能阻止无期限候选和伪 Roadmap，同时让真正的新 Evidence 命中 restart/recheck/key assumption/material opportunity 时及时提醒；需验证条件匹配、提醒噪声、维持决定的追加记录、supersedes 与未来 scheduler/Connector 不越权。
156. 未来 KMG 能否在不复制 Decision Ledger 或丢失 exact provenance 的前提下消费所有正式 Decision/evolution 作为 raw source，并同时建设 derived knowledge；copy/reference/index、权限、保留、去重和同步必须由真实 KMG consumer requirements 原型决定，不能由当前 BPG 预设。

这些问题通过 Slice 1—8 和逐节点原型的运行证据回答，不继续通过增加架构措辞回答。

---

## 29. V1.4 与 V1.3 的关系

V1.4 是 V1.3 的 distribution/eval implementation contract closeout，不改变已冻结的产品架构、Graph 顺序或一期范围。它关闭的是安装包公开面、Core Atomic Skill Modules 的物理边界、最小构建/身份检查、Product/Plugin 两类 Suite 分工、旧 eval migration 标签与模板 promotion 矛盾；所有 runtime 仍为 implementation pending。

以下保留 V1.3 与 V1.2 的历史关系，作为继承依据：

V1.3 是对 V1.2 逐节点讨论结果的**一致性收敛版**，不是又一次扩大范围。它保留 V1.2 已确认的 Better Product Graph 系统边界、Outcome-first、横向模块化 × 纵向迭代化、单一 `signal.ingest`、同一 Product Pipeline、advisory Reviewer、自包含 PRD release、可选 Connector、轻量 State/Audit/Git 与 Knowledge Maintenance 权责边界。

V1.3 主要删除或降级了讨论过程中残留的旧设计：固定 Problem/Plan/PRD/Handoff/Bug 人工确认、Reviewer blocking/waiver、独立 Experiment lane/package、未有消费者却提前建设的 legacy alias、过细的 KMG Proposal/Impact 实现合同，以及把 Audit Event 写成第二状态真源的倾向。模板只冻结可配置、可升级、可 pin/回滚和 exact fallback 的 seam；general v0.1 仍是 Draft/Bootstrap 候选。Golden Cases 仍是未来实现验收规格，尚未运行。

因此 V1.3 可以冻结为“已确认产品架构与设计决策的一致性基线”，但不等于全部实现合同已定稿，更不等于软件、Connector、Golden Case 或 runtime behavior 已经验证。`evals-generator`、Claude/多 Agent、Feishu、研发 Graph、测试 Graph、Knowledge Maintenance submission/Impact sync 与具体模板优化仍按 Roadmap 分期建设。

---

## 30. 逐节点 Review 机制

V1.4 冻结 V1.3 已确认的系统结果、产品行为和职责边界，并增加本版窄分发/评测合同；未被真实实现验证的内部合同继续用 Node Review Card 标记为部分确认、待原型或延后，不用文档完整度冒充运行证据。

### 30.1 每个节点必须回答的八个问题

1. **目标**：这个节点如何推进 Target Operating Outcome 或降低关键不确定性？它要改变什么认知或业务状态，为什么不能省略？是否可能局部优化却损害整体结果？
2. **输入**：需要哪些信号、证据、知识快照、上游产物和配置？哪些输入不可信？
3. **Agent 逻辑**：使用哪些原子 Skill、认知镜头和确定性规则？哪些内容不能交给 LLM 判断？
4. **人机交互**：何时询问、解释、举例、挑战或等待人类？谁有权确认或签发 Domain constraint，确认的授权语义和 epistemic 语义分别是什么？
5. **输出合同**：必须产出什么 Schema/文档/证据引用？如何表示未知、不适用和置信度？
6. **边与停止条件**：什么算完成、条件式推进、action-scoped block、等待、失败、停止或转向？哪些更安全动作仍允许，谁都不能自行宣布哪些结果？
7. **恢复与返工**：从哪里恢复；问题发生时退回哪个最早修复点；如何避免重做无关部分？
8. **审计与权限**：记录什么版本、哈希、依据、工具、批准和副作用；节点允许读写什么？

### 30.2 Review 状态

- `UNREVIEWED`：仅有架构占位。
- `IN_REVIEW`：正在和产品负责人讨论。
- `CONFIRMED`：当前逻辑已确认，可以进入实现设计。
- `PARTIALLY_CONFIRMED`：产品行为和系统边界已确认，但完整实现合同或运行阈值仍待设计/原型。
- `NEEDS_REVISION`：目标或内部逻辑需要修改。
- `PROTOTYPE_REQUIRED`：不能仅靠讨论确定，需用真实例子验证。

一个动作只有在拥有独立的失败/等待、Owner/权限、重试/恢复、正式产物或可替换实现边界时，才保留为持久节点；否则作为相邻节点内部原子步骤。节点 Review 可以合并或拆分节点，但必须记录原因，不追求固定节点数量。

### 30.3 Review 队列

| 顺序 | 节点组 | 当前状态 | 重点问题 |
|---:|---|---|---|
| 1 | `signal.ingest` / `signal.prepare` / `signal.relate?` | `PARTIALLY_CONFIRMED` | 原子接收与不可变原文；统一外部挂载/回传识别、Connector 边界与关联澄清已确认；其余完整节点合同仍待实现设计 |
| 1a | Unified External Intake / typed result binding | `CONFIRMED` | 所有外部业务输入只进 `signal.ingest`；Connector 只传输/解析协议/附加 provenance，外部不填内部 Schema。Core 中央分 status、typed result、Product Signal；result 先更新绑定记录，新产品事实才派生关联 Signal；协议 kind 不等于产品判断；无下游专用入口/兼容别名/新 Router destination/新 Gate/Artifact |
| 2 | `signal.classify` / `route.select` / Signal Ledger / Input Connector | `PARTIALLY_CONFIRMED` | Classifier 零交互与自行查询、四个 destination、并行 existing_links、PM-only NEEDS_CONTEXT、受约束 override、审计和 Connector 无产品路由权已确认；阈值和完整实现合同待原型 |
| 3 | Incident Verification Packet / Engineering Handoff / 可选 Product Response | `PARTIALLY_CONFIRMED` | 轻量单一 Packet、NOT_AVAILABLE、v1/v2/v3 追加、紧急交接不因非关键缺口阻塞、研发结果回流与产品判断按需触发已确认；字段细节、TTL 和跨团队实现待原型 |
| 4 | Bug Baseline Assessment / Bug Fix Brief / Product Logic & Ambiguity 分流 | `CONFIRMED` | exact baseline、cause class + surface tags、五项自动分流条件、Agent-first Junior PM 辅助、条件式一个最小澄清/override、Bug Brief/Decision/Discovery/Incident 分流及 Eval/Handoff 边界已确认；固定 PM Route Confirmation 退役 |
| 5 | `evidence.collect` / `evidence.map` / Problem Evidence Map | `PARTIALLY_CONFIRMED` | 不可变 provenance、MVU 驱动收集、语义映射、run-local 版本与 canonical knowledge 隔离已确认；标签校准、阈值和真实来源失败处理待原型 |
| 6 | `problem.assumption.audit`（问题假设审视） | `CONFIRMED` | Evidence Map 后、Learning Loop 前的独立轻量节点；默认 AI 自助/零 PM 深访；原话与事实角色分离；现象/影响/问题假设/期望结果/提出方案；动态方向性假设与反证/历史/no-action/症状原因检查；exactly one MVU + 最佳来源 + 下一信息请求；只完成可信认知起点；run-local versioned checkpoint；三类下一建议；material reframe 重跑；无独立 Reviewer/Gate/正式业务 Artifact |
| 6a | `problem.learning.loop` / Evidence Request | `CONFIRMED` | 已确认独立可恢复 Loop 边界；每 Round 一个核心 MVU + 少量紧密相关请求；七类来源路由；PM 访谈采用 bounded joint judgment 六步，Junior PM 获得非诱导脚手架但标准不降，挑战强度按风险/证据冲突/可逆性选择 `LIGHT / STANDARD / STRONG`，一次最高价值挑战后记录分歧并及时停止；collect/map loop-back；Learning Round Delta 使用最小 structured rationale 而非默认全量逐字对话；Evidence Request 是 versioned wait/resume 合同而非节点；五种 runtime status、三种 completion disposition、advisory next-action recommendation 三维分离；`WAITING_FOR_EVIDENCE` 不限 human 且可恢复；停止采用 action-relative sufficiency；普通资料研究留在 Loop，正式 Research/Experiment 只能建议并交 Product Decision。人工 override 和完整 Schema 仍待讨论 |
| 7 | `problem.synthesize` | `CONFIRMED` | Learning=`COMPLETED + READY_FOR_SYNTHESIS` 后的独立轻量 one-shot；绑定 exact Discovery inputs；生成 versioned Problem Definition Candidate；保留 Unknown/non-problems/用户方案关系；material gap 携新 MVU 返回 Learning；source stale 重算并 supersedes；不搜索、访谈、补证、决策或选方案，`COMPLETED` 不等于 Problem Ready |
| 7a | Problem Ready 语义 Review 与确定性状态边界 | `CONFIRMED` | 独立/隔离 Product Quality Reviewer Agent 只读 exact Candidate 并输出 advisory Finding；程序化 State Controller 只重算 exact Candidate、Review disposition、上游 refs 并唯一原子写状态。固定人类确认已按 7c 折叠到 Product Decision；Agent 模拟只可 `ADVISORY_ONLY` |
| 7b | `problem.quality.review` | `CONFIRMED` | exact frozen Candidate + Evidence/Learning/Knowledge/Product Memory；完整质量维度；只读独立 attempt；action-scoped Finding/Verdict；`REVISE_SYNTHESIS / RETURN_TO_LEARNING / NEEDS_OWNER / ROUTE_REEVALUATION`；首次 full、后续 delta-targeted + global invariant regression；no-progress 返回 Learning/Owner；Junior PM 关键 Finding/原因/首选建议 |
| 7c | `problem.owner.confirm` | `RETIRED / FOLDED_INTO_PRODUCT_DECISION` | 不再固定确认 Problem Candidate。Decision Brief 同屏展示 exact Problem，Owner outcome choice 即承担责任；若 material 错误则返回 Synthesis/Learning。无 alias、legacy event、审批层或第二摘要真源 |
| 7d | `problem.ready.gate` 轻量确定性 policy | `CONFIRMED` | 自动无感；只查 exact/current/materially valid Candidate、同版本 advisory Quality Review/disposition、上游 Evidence/Learning/Synthesis refs/state/version/hash 一致可解析；`READY` 自动进入 Product Decision，`NOT_READY` 列 exact mechanical unmet + repair target；无 Owner Confirmation、无语义审查/审批，不因 concern/普通 Unknown 阻塞，不检查后续 Ready |
| 8 | `product.decision` 节点形态 | `CONFIRMED` | 一个独立可恢复节点；AI Decision Brief、按需 bounded adversarial/domain sub-agent Review、Owner 讨论/挑战与明确选择、Controller deterministic route 均为内部能力而非节点；versioned run-local Draft/checkpoint 可恢复但不等于正式决定；Agent 给首选、material 时才外显最强反方，Owner 选择、Controller 写 route；默认不全量 Reviewer |
| 8a | Product Decision 五种结果基本边界与人类表达 | `CONFIRMED` | 稳定 machine enum `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT`；默认中文分别为“现在不做，结束当前方向 / 值得继续关注，但暂时不作承诺 / 先补充关键信息，再决定是否投入 / 先做小范围实验，用真实结果验证 / 正式决定要做，并确定何时开始”；NOW/SCHEDULED/CONDITION_TRIGGERED 同样用直白句子；所有 human view 含 why、最大 unknown/反方、下一步与改判条件，禁止 bare-code-only，Renderer 不建第二真源 |
| 8b | Product Decision 完整选择与专业治理逻辑 | `PARTIALLY_CONFIRMED` | 已确认：MVU 驱动的 RESEARCH/EXPERIMENT/COMMIT guide、Agent 单一首选/相邻替代/翻转条件、STOP/WAIT/future COMMIT、条件重审和无固定评分。剩余 materiality、自动化扩大后的专业治理与其他领域 policy 待真实运行后设计 |
| 8c | Product Decision 默认一屏呈现 | `CONFIRMED` | 一项直白首选、最多三项关键依据、最多一个 material 认知提醒、一项定性 confidence + 最大 unknown/翻转条件、一个具体下一步；最强反方仅 material 时一句；完整 Evidence/其他选项/认知/风险/历史/Audit 渐进展开；同一 Draft/Record 真源，无 hidden CoT；重大风险披露可突破预算，不用死字数 |
| 8d | Decision Record 通用最小合同 | `CONFIRMED` | Owner 一屏确认 chosen decision、applicability scope、最多三项理由、最大 Unknown + flip/stop/restart condition、next action + checkpoint/trigger；material 分歧才显示 disagreement + Owner reason；系统自动填 exact refs/identity/version/关系/audit；immutable/versioned + supersedes；同一 Record 渲染，无第二真源 |
| 8e | Chosen-outcome 条件化最小补充 | `CONFIRMED` | 共用一份 Decision Record，只生成 chosen outcome 的 `outcome_details`：STOP restart；WAIT why-not-now/review；RESEARCH question/sufficient evidence/stop；EXPERIMENT unknown/exposure-risk/result mapping；COMMIT activation/time-trigger-recheck/stop-review；未选项无空字段，下游合同不重复 |
| 8f | Product Decision action-risk classification | `CONFIRMED` | R0—R3 是内部、Agent 自动、action/exposure-scoped 轻量分类，不是节点/Gate/价值评分/问题标签；STOP/WAIT 通常不显示，特定 RESEARCH 才分类，EXPERIMENT/COMMIT 必分类；RISK_PENDING 不默认低；R3 可继续 Plan/PRD并强化披露/外置关注。一期无 AI Reviewer formal Gate，未来 autonomy governance 延后 |
| 8g | Agent–Owner material disagreement | `CONFIRMED` | Agent 先给首选；Owner 选不同 outcome 时一次 bounded substantive challenge，聚焦 evidence gap/risk/首选理由，不只问“确定吗”也不无限争论；有权 Owner 最终决定；条件保存双方理由/authorization/accepted uncertainty-risk/recheck-stop/execution constraints；授权不提升置信度；可逆可测弱证据优先建议 EXPERIMENT；R3 concern 随下游/外置审核传递，无新 outcome/node |
| 8h | Product Decision 节点终止与路由 | `CONFIRMED` | 不新增 `decision.ready`/Gate/Artifact/Reviewer/二次确认；Controller 重算 exact Owner choice/Record、合法 outcome、通用/结果字段、必要 risk/constraints、current refs、disagreement/accepted risk；通过后确定性路由，失败留在 Decision 并给直白 unmet + repair target；Research/Roadmap/下游 Ready 未提前确认 |
| 9 | Product Decision & Roadmap Memory | `PARTIALLY_CONFIRMED` | 四类语义分工、outcome 投影、本地/KMG 边界和新 Evidence 分级已确认；KMG 提交、ack、跨团队 Impact 与批量提醒合同延后到 Knowledge Requirements 反推 |
| 9a | Decision/Roadmap/Changelog/Audit 分工 | `CONFIRMED` | 同一 Decision 的四种语义投影，不是四套流程/节点/真源；所有正式 Decision 含 STOP 进 Ledger；Roadmap 只收未来行动；RESEARCH 进 Request，EXPERIMENT 进同一 Plan/PRD pipeline 且不形成 committed product/Portfolio 真源；Changelog 只收 material 产品意义变化；Audit 自动记录执行；KMG 未接入时本地完整运行，接入后共享/发布但不重做 Owner 决策，提交合同仍延后 |
| 9b | 历史 Decision 受新 Evidence 影响 | `CONFIRMED` | 新 Signal 保留四 destination 并以 existing_links 关联 exact history；supports/non-material 只追加/摘要，challenge key assumption 一屏提醒并给首选，kill/recheck/material risk 逐 action 约束；STOP/WAIT 仅在 restart/recheck/key assumption/material opportunity 命中时主动重审；Owner 可维持/补证/实验/supersede/缩范围；旧 Decision immutable，Impact List 只标受影响对象；冲突合并/跨团队实现仍待 Review |
| 10 | 独立 Experiment Fast Lane / Portfolio / Result Return | `RETIRED / FOLDED_INTO_STANDARD_PIPELINE` | ADR-017/018 的独立 Planning/PRD/Review/Ready/Handoff 与 Portfolio 产品线已撤销；不作为实现节点组或一期真源，历史理由保留在 ADR-081 |
| 10a | `EXPERIMENT` Delivery Intent（同一 Product Pipeline） | `CONFIRMED` | 保留“受控购买信息而非长期承诺”；复用同一 Plan/PRD/Eval/Review/Ready/release/dispatch。PRD 条件化保存 key unknown、exposure、具体变化、measurement、continue/adjust/stop、Guardrail/rollback/result return；结果经统一 Intake 回 Decision，不新增 Node/Gate/Artifact/HITL/模板/命令 |
| 10b | Experiment intent 的 Planning Profile 阈值与并行治理 | `PROTOTYPE_REQUIRED / FUTURE` | `EXPERIMENT` 不自动 LIGHT，按风险/复杂度升降档；精确阈值待真实 Case。只有并行规模/干扰/资源冲突证明确有需要时才原型 Roadmap 关系视图或 Portfolio 能力，一期不建设正式 Portfolio |
| 11 | Outcome-first Planning / 四个逻辑规划视图 | `PARTIALLY_CONFIRMED` | 最佳可达结果、双向 Refinement/formal Review、复杂度自适应、PRD Slice、Coverage、Reconcile 与轻量 Plan Ready 已确认；Module/Iteration Map 的完整内部合同与内嵌/独立表达仍待原型 |
| 11a | Product Planning 双向深化原则 | `CONFIRMED` | Product Plan v0 是系统假设/全局地图；按价值/风险/依赖逐块深化，每轮 global reconciliation；允许拆并删/重排/转 Research/Experiment/Decision；同 exact snapshot bounded sub-agents 只交 Proposal、主 Agent 单点整合；material version/checkpoint/changelog/supersedes/impact；停止后才二维拆 PRD；稳定 Plan 小改动只 affected-area review + global impact check；Refinement 属于 `product.planning` 内部 Loop，不建第二真源 |
| 11b | Planning Refinement 与 formal Review–Optimize | `CONFIRMED` | Refinement 在 `product.planning` 内生成/探索/拆解/协调并产出 versioned checkpoints/stable Candidate；formal Review 由独立只读 Reviewer attempts 审 exact frozen Candidate，Optimizer/主 Agent修复。local omission 定向优化，结构问题回 Refinement，Decision/Problem 失效回对应上游；attempt/disposition/finalize 完整后进 Plan Ready，partial review 只 advisory；Plan/PRD 复用通用 engine/profile，实验 intent 只条件化 rubric |
| 11c | Planning Profile Selector（内部能力，不是 Router/Node） | `CONFIRMED` | LIGHT 一次轻量、STANDARD 有界 Rounds、PROJECT_SCALE 条件 Waves+Rounds；Agent 按真实复杂度升降级，不让 PM 填问卷；各档保留质量底线；选择性吸收 Better Work 语义、不复制文件/状态；父 Wave 不禁止独立 Run 并行，精确阈值待原型 |
| 11d | `plan.slice`（PRD 切片） | `CONFIRMED` | 同时用横向模块化+纵向迭代化生成 PRD Candidate Slice Map/List；检查独立目标、端到端结果、验证、相对发布/回滚和大小；不按矩阵格/技术层机械拆，不写 PRD；Agent-first，material 切分取舍才问 PM |
| 11e | `plan.coverage.validate`（规划覆盖检查） | `CONFIRMED` | 每项重要内容有本轮/后续/Experiment/等待/不做/unresolved 明确去向；检查遗漏、重复冲突、体验、依赖、上游一致；按 Profile 内联/简表/只读挑战；只诊断不静默改 Plan或自动 BLOCK，结果回同一 Plan/Audit |
| 11f | `plan.reconcile`（规划协调） | `CONFIRMED` | 把 Coverage/深化/新 Evidence Finding 放回整体权衡；非决策调整可自动 checkpoint，material 目标/承诺/风险变化由 Owner确认并写既有账本；可回 Slice/Iteration/Decision/Learning；允许带责任与复查条件的显式冲突，不建审批 Gate/第二状态 |
| 11g | `plan.owner.confirm` + `plan.ready.gate` | `CONFIRMED / CONFIRM RETIRED` | 固定 Plan confirm 已折叠为条件式 Product Decision：普通忠实 Planning 自动完成，按需摘要不是审批；material 新取舍回 Decision。Controller 只查 exact Plan、Coverage/dispositions、advisory Review finalize、依赖/冲突和 material Decision refs；PASS 只创建 current activated+eligible PRD Runs |
| 12 | `prd.content.build` / `prd.render` | `PARTIALLY_CONFIRMED` | 完整产品语义组织与模板表达的能力边界已确认；`prd.render` 的完整内部写作、优化与恢复逻辑仍待实现设计 |
| 12a | PRD Workspace Initialization 职责边界（非智能 Graph Node） | `CONFIRMED` | 面向人称“准备 PRD 工作空间”；正式内部名为 `prd.workspace.initialize`。Controller 只建 Run/workspace、绑 exact refs、登记状态/版本、准备目录和机械保存/流转/校验；Agent 才在 content/render 创作语义，Reviewer/Optimizer 各守职责，Owner 只在条件式 material/专业/副作用权限时介入；第一版不建旧名兼容层，也不因此冻结完整初始化 Schema/Gate/HITL |
| 12b | PRD 内容/模板产物边界 | `CONFIRMED` | 实读 Better-Product-Plan 后取消默认独立完整 Product Spec。简单 Run 同一 attempt 直接生成一份 PRD candidate；复杂场景才可配置内部 checkpoint且不得正式发布。过渡 exact template、必要语义 mapping/扩展/不兼容处理和项目 checklist 隔离已确认，不新增 HITL或旧名 alias；完整 render 逻辑未提前确认 |
| 12c | `prd.generate` 节点形态与 Template Profile | `CONFIRMED` | 一个可恢复 Agent 节点内含 content build、确定性 profile resolve、Agent render，不注册三节点/HITL；Profile 按项目配置→受信知识→BPG 当前配置的 fallback/default，冲突不可判定才一次问；首个 candidate 进 archived，Ready 后 exact release；general v0.1 是可配置、可升级的 Draft/Bootstrap 候选，内容/promotion 优化留 Roadmap，一期不建产品类型模板库。具体 render 写作/优化逻辑仍待实现设计 |
| 13 | Evals Applicability / Plan / Generate / Review | `PARTIALLY_CONFIRMED` | Applicability 双维边界已确认；Eval Pack 完整合同、具体 generator 内部逻辑、Ground Truth 治理与 Test Graph 消费仍待实现设计 |
| 13a | `evals.applicability.decide`（`prd.generate` 内部动作） | `CONFIRMED` | Applicability=`NOT_NEEDED/RECOMMENDED/REQUIRED` + 直白人话，Fulfillment 五态单独记录；复杂性不触发、概率/多解/Rubric/分布/样本风险通常 REQUIRED；RECOMMENDED 默认不硬 Gate，REQUIRED 缺 Pack 可继续 Candidate但不能 Ready；第一版直接使用当前合同，无 PM 问卷/HITL/顶层 Node |
| 13b | `evals.build`（PRD Run 内按需可恢复子节点） | `CONFIRMED` | stable content 后与 render 同源并行；scope/generate/review 是内部动作；join exact PRD+Pack，semantic impact 局部 stale、排版不全量重做；最小 Pack、Ground Truth、只读 Reviewer/生成者修改边界已确认。TDD-ready future seam 已登记，umbrella 名/完整 Schema/Test Graph 实现与独立 Roadmap仍 OPEN |
| 14 | Reviewer advisory-only / future autonomy governance | `CONFIRMED / FUTURE DEFERRED` | 一期全部 AI/sub-agent Reviewer 只给 concern/建议/返工点，不拥有 Block/veto/approval/waiver；遗留项同源披露给外置团队。真实专业身份、policy、blocking、waiver 只在未来无人值守研发/发布时另行设计 |
| 15 | PRD Review–Optimize / Ready | `PARTIALLY_CONFIRMED` | 忠实一致性、目标忠实内核、`review.aggregate`、`review.finalize`、`prd.optimize`、内审意见 companion、HITL 精简与 Ready/dispatch 已确认；其余具体 Reviewer rubric 待实现设计。文档版本管理已确认 archived/released、Candidate/Attempt 分离与 exact release Handoff |
| 15a | Review–Optimize 通用 engine/profile 边界 | `CONFIRMED` | product-plan/prd 共享 frozen Candidate、只读 Reviewer、Finding/Verdict、repair routing、new version/delta、定向复审+全局不变量和 no-progress 合同；`EXPERIMENT` 只条件化 PRD rubric，不增加 profile/Ready。不同 artifact 使用各自 Reviewer/rubric/policy，不复制 Runtime，也不让生成上下文自报 Review complete、Ready 或正式状态 |
| 15b | PRD Fidelity / HITL / Ready / Dispatch 边界 | `CONFIRMED` | Product Reviewer 首先证明 Candidate 忠实于 exact Decision/Plan/Slice/Knowledge/Evidence/constraints；material 新内容返回最早上游。退役默认 `prd.owner.confirm_understanding` 与固定 `handoff.owner.approve`，第一版不建旧事件兼容层；Controller Ready 后自动生成 self-contained release，本地 BPG Released 不等于外置审批；Connector policy 另决定 dispatch。一页最终摘要按需同源渲染，不是审批/Gate/第二真源 |
| 15c | `review.parallel` 目标忠实内核 | `CONFIRMED` | 自动从同一 frozen Decision/Plan/Slice/Evidence/Knowledge/Guardrails/System Acceptance/Candidate 生成执行 Packet；既有 Product Reviewer 逻辑 profile 必做目标/范围忠实检查，其他 panel 条件化，LIGHT 可合并不可丢失。同 snapshot 独立只读首轮后才 aggregate；Finding/cross-check、最多两轮高影响复核、五类 repair verification 和两轮 no-progress 已确认。不引入完整七阶段、评分/覆盖率、重型文件/脚本、重复 Owner 确认或新 Node/Gate/HITL |
| 15d | `review.aggregate / 审查意见汇总` | `CONFIRMED` | 轻量可恢复内部 join node；LIGHT 可同一用户动作自动完成但仍留 attempt。主 Agent 聚类/根因/分歧/unsupported/最早 repair target，Controller 只查 required attempts、同 snapshot、Finding fields、late/stale/无损追溯并写状态。复用 Review Record/Finding/Verdict/Disposition/review_summary；不修改/生成 Candidate、不执行 Gate/授权、不自报 Ready、不增 Artifact/HITL；正式路由见 15e |
| 15e | `review.gate` → `review.finalize / 审查收尾` | `RETIRED / REPLACED + CONFIRMED` | 当前未实现的 Review Gate 退役；Finalize 是 Controller 内部确定性 action，只查 attempts、Finding dispositions、exact Candidate 与同源内审意见。它不是 Node/Gate/Agent/HITL，不要求 PASS、不因 advisory concern 阻塞 |
| 15f | `prd.optimize / 根据审查意见修订 PRD` 与有界 Loop | `CONFIRMED` | 可恢复 Agent 节点/PRD profile；只修主 Agent采纳且位于 current PRD 的建议，批量最小必要修订，产生一个新 Candidate+delta+finding mapping，只报 claimed repair；Reviewer 验证 status。Candidate version 与 Review Attempt 分离；2/3/4 轮、两轮 no-progress 早停 |
| 15g | `prd.ready.gate / PRD 最终就绪检查` | `CONFIRMED` | Controller 最终确定性 boundary，只查 current Candidate、same-version Review/finalize/内审意见、current refs、REQUIRED Eval、Template/Document Experience/version/changelog/机械合同；advisory concern 本身不阻塞。通过自动 release/local Handoff，不要求 Owner 二次确认或外置审批 |
| 15h | PRD Released directory / package 简化 | `CONFIRMED` | archived/released 每个 exact version 使用自包含同 stem 目录，Markdown+相对 assets 是 canonical source，exports 按需派生且不阻塞 Ready。Ready release 即本地交付单元；第一版不建设独立 package action、legacy event 或迁移 parser，也不影响 Incident/Bug 合同 |
| 16 | Handoff / downstream feedback | `PARTIALLY_CONFIRMED` | Product self-contained release、`handoff.dispatch`、统一回传接入、轻量 materiality 和最早受影响点返工已确认；具体领域 materiality policy、跨团队执行和下游完整 typed result schemas 仍待原型 |
| 16a | `handoff.dispatch / 产品交付发送` | `CONFIRMED` | 可选可恢复 Connector attempt，不是本地完成必经。每 target policy=`disabled/manual/auto_when_ready`，默认 manual；自动需 exact preauthorization。只读 exact release，幂等 identity、UNKNOWN query/reconcile、多目标独立 receipt；不打包/改写/Review/重复 Owner 审批，无 Connector 不阻止 Ready，receipt 不外推为 accepted/approved。Feishu native Doc 仍需权限原型，DOCX import 仅 fallback |
| 16b | Unified downstream return / earliest affected repair | `CONFIRMED` | 回传统一进入 `signal.ingest`；status/result 先更新绑定记录，新产品事实才派生 exact-linked Signal。Agent 以 binding/new verifiable info/assumption-scope-rule-AC impact 做轻量无分数判断，给直白建议/反方/翻转条件；Controller 按 policy/权限写状态。返工到 Engineering/PRD/Planning/Decision/Learning/Roadmap/new item 最早有效层，release 不覆盖、普通意见不自动 reopen、material Decision/承诺/Roadmap 才需 Owner 新决定；不新增 Node/Gate/Artifact/HITL |
| 17 | Knowledge impact / proposal | `DEFERRED / PENDING_KNOWLEDGE_REQUIREMENTS` | 仅 source coverage 已确认：所有正式 Decision（五种 outcome）及其维持/复查/推翻/supersedes evolution 都是未来 Raw Source Corpus 必要候选，连同 PRD 与相关原始材料保留 exact refs；提交合同仍不冻结。未来 KMG 必须先定义 raw + derived 两层消费需求，再反推 copy/reference/index、时机、自动化、权限、采纳/保留/同步；不只提交压缩认知，不合并 Ledger/canonical store |
| 18 | State Controller / Audit / Versioning | `PARTIALLY_CONFIRMED` | State Snapshot 唯一恢复真源、Controller 唯一写状态、轻量 Run Resume、meaningful Audit Events 与 Git 分工已确认；完整 State/Event Schema、保留策略、CAS 与崩溃恢复待实现设计 |
| 18a | Lightweight Run Resume / Audit / Git split（横向运行规则，不是 Graph Node） | `CONFIRMED` | 每个 Run 只持久化 current state snapshot + append-only meaningful event stream；snapshot 覆盖 current/last/next、exact refs、等待/暂停与 side-effect receipts，events 只记 material checkpoint、正式状态/Owner/Finding/副作用/暂停失败/sub-agent 结果。Git 管内容版本，State 管当前位置，Audit 管关键变化；恢复先校验 refs/files/external/branch change，再给直白 Resume Brief。Controller 唯一写状态；示例文件名/完整 Schema 未冻结，不新增 Node/Gate/Artifact/HITL/Registry/数据库/Service/MCP/CLI/重型 event sourcing |
| 19 | Better Product Graph Host Plugin / Public Skill | `CONTRACT_CONFIRMED / IMPLEMENTATION_PENDING` | 品牌/机器名、唯一公开 `skills/better-product-graph/SKILL.md`、Atomic Skill Modules 非 discovery 路径、source→dist allowlist、最小 installed identity、十一个 intent words 与 Plugin Contract Suite 边界已确认；真实 Codex discovery、fresh-install conformance、持久化能力与其他 Host Adapter 待实现/原型 |
| 20 | Document Experience 横向规则（不是 Graph Node） | `PROTOTYPE_REQUIRED` | Policy/Profile 最低项、Renderer 保真、Validator stale/绑定重算、Readability Reviewer 灰度、模板/Supplement、Incident/Bug 轻量性、八个一期 Profile（含 `product_plan` Plan Ready 摘要与 `internal_review` companion view）与第二真源防护 |
| 21 | Analysis Method Hook 横向内部能力（不是 Graph Node） | `PROTOTYPE_REQUIRED` | 默认 NONE、五问选择、Level 0—3、Method Card 合同、Evidence/inference 边界、每轮一个主方法；Journey Map/KANO 仅在真实 Case 证明增量后逐个接入 |
| 22 | Sub-agent Execution Policy 横向执行形态（不是 Graph Node） | `CONFIRMED` | 对抗/可并发/独立旁路优先 bounded sub-agent；主 Agent 只编排/join/保留分歧；exact snapshot、最小权限、统一结果、无正式写入/副作用；Host model profile 与实际映射审计；required/optional 失败边界；具体 Codex 持久化、并发和模型选择能力仍 `PROTOTYPE_REQUIRED` |
| 23 | Multi-Agent Collaboration future capability（不是 Graph Node） | `PROTOTYPE_REQUIRED` | 一期只用当前 Host 内部 sub-agent；未来跨独立 Agent runtime/Host/provider 协作。独立实例/上下文/目标/输入输出审计；复用 exact snapshot/role/result/permission/join；Collaboration/External Audit Connector；身份、认证、协议、持久化、成本和失败治理尚未实现，不作为一期验收依赖 |
| 24 | Project Git Preflight 横向基础设施（不是 Graph Node/Gate） | `CONFIRMED` | 开始/恢复校验 exact project root；复用父级 repository/worktree，否则本地静默 `git init -b main`；拒绝 HOME/广泛目录和嵌套 repo；`.gitignore`/敏感边界先行；不自动 add/commit/push/remote；失败真实 `DEGRADED/BLOCKED`；并行 sub-agent 独立 branch + worktree、主 Agent review diff 后整合；material checkpoint/冻结版本才提交或 tag |

第 18a、20—24 行借用同一 Review Card 机制审查横向能力，不把它们登记为 Graph Manifest 节点，也不改变前 19 组业务/运行节点的顺序。

V1.4 继承 V1.3 已完成的产品层逐项处置，并关闭 distribution/eval 文档合同冲突；尚未由实现或真实 Run 证明的部分统一标记为 `PARTIALLY_CONFIRMED / PROTOTYPE_REQUIRED / DEFERRED / IMPLEMENTATION_PENDING`。其中精确 Planning Profile 阈值、具体领域 materiality、下游完整 result schemas、State/Event 完整 Schema、CAS/崩溃恢复、`prd.render` 细节、Eval generator、Module/Iteration Map 表达、Codex Host conformance、Plugin Contract Suite、Product Golden v0.2、KMG submission/Impact sync、Multi-Agent 和 Git worktree 生命周期仍需实现或原型证据。Problem Ready 不保留 action-scoped matrix；正式专业身份、blocking policy 与 waiver 只属于未来无人值守治理。V1.4 的冻结不把这些开放项伪装成已经验证，也不新增 Node/Gate/Artifact/HITL。

### 30.4 Human-in-the-Loop Interaction Density Audit disposition

> **CURRENT DISPOSITION COMPLETE；访谈自动跳过阈值仍需运行校准。** 当前核心只保留 `product.decision` 一处固定人类产品责任点。它要求明确 Owner intent，但自然语言已经清楚表达 exact outcome/scope 时不再追加“是否确认”UI。其他人工交互只有三类正当理由：降低一个会改变行动的高价值 Unknown；解决一个 material 产品取舍并回到同一 Product Decision；授权一次真实外部副作用。

| 处置 | 交互 | 当前规则 |
|---|---|---|
| 保留 | `product.decision` Owner choice | 正常 Discovery/Product 路径唯一固定语义责任点；Incident 与可靠 Implementation Deviation 不因此进入 Decision |
| 移除/合并 | `problem.owner.confirm`、`plan.owner.confirm`、`prd.owner.confirm_understanding`、`handoff.owner.approve`、Bug `PM Route Confirmation` | 分别折叠进 Product Decision、条件式 Decision、程序化 Ready/外置审核、Connector side-effect policy、证据条件自动分流 |
| 自动化 | Signal classify/router、Assumption Audit、Evidence 自助检索/map、Problem Synthesis/Ready、普通 Planning/slice/reconcile、PRD generate、advisory Review/Optimize/Finalize、PRD Ready/local Release、Git preflight/state/resume | Agent/Controller 按各自边界运行；Evidence Learning 仍可从 PM 获取无法自助且高价值的信息 |
| 按条件触发 | Signal 关联/关键上下文一次最小澄清、Problem Learning PM 访谈、Planning material choice→Decision、Template 冲突、Eval/Ground Truth/专业输入等待、`handoff.dispatch` 无预授权时的 exact side-effect authorization | 不得包装成每份产物固定确认；每次先说明当前判断、为何需要人、答案/授权改变什么 |
| Graph 外 | 团队最终汇总审批 | BPG 交付 exact Released PRD、同源内审意见与审计 refs，但不声称外置审批已通过 |

交互目标因此是：正常 Idea/feedback 路径通常只有一次固定 Owner 打断；可靠 Implementation Deviation 路径可以零内容确认；Bug 转产品逻辑时只进入一次 Product Decision。Signal clarification、PM interview、Template/Ground Truth 信息请求是条件式信息获取；Connector dispatch authorization 是条件式副作用权限，不计作内容确认。

访谈是人类参与中最重要的信息获取环节，不能为了追求“一个固定触点”而自动省略。§7.5 已确认显式 `interview skip|resume` 与更严格默认：完整 Discovery 原则上至少一次实质访谈/等价当前对话，除非 Agent 能证明没有 material PM-only unknown 且继续提问信息增益低，或用户显式 skip。此规则仍需用真实 Run 校准误跳过率、打断密度和 LIGHT/STANDARD/PROJECT_SCALE 交互预算，但不新增 Gate、Artifact 或审批。

逐节点确认产生的新结论先记录在 Review Card；若改变已经交付或被冻结的架构正文，则创建下一文档版本，不原位覆盖历史版本。V1.3 继续冻结为架构一致性基线，V1.4 冻结为 distribution/eval implementation contract closeout；后续变化创建新版本，运行验证结果进入 Evals/Audit，不回写冻结正文。
