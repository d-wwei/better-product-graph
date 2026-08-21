# Better Product Graph 项目 Roadmap v0.12

状态：Frozen V1.4 distribution/eval alignment baseline / implementation pending
日期：2026-08-20
上一版本：`BETTER_PRODUCT_GRAPH_ROADMAP_v0.11.md`（已冻结）
依据：`PRD_GRAPH_v1.4.md` Frozen Distribution/Eval Implementation Contract Closeout、v0.11 的既有 Wave 顺序，以及三份 2026-08-20 best-practices 研究与 disposition

> 本文回答“接下来按什么顺序，把 Better Product Graph 从架构规划变成真正可运行、可验证、可扩展的产品”。它不是新的架构真源，也不替代各组件的详细设计。Wave 只负责项目级建设顺序；具体业务语义仍以对应架构版本和已确认 Node Review 为准。

> v0.12 只把 V1.4 的 distribution/eval 实现合同和研究建议落到既有 Wave 1—4 验收细化；**不改变 Wave 1→6 的顺序，不扩大一期产品范围，不新增业务 Node/Gate/Runtime**。所有新增条目均为实现/验证工作，当前仍 `implementation pending`。

## 1. 一句话结论

现在不应该继续无限扩写架构，也不应该同时建设所有 Graph 和 Connector。

最合理的顺序是：

```text
先做可在本地独立运行的 Better Product Graph
→ 跑通一条真实 Idea 到 PRD 的完整闭环
→ 补齐多路线、规划拆分和 Review–Optimize
→ 建立 Evals / 测试设计合同
→ 再建设共享知识维护 Graph
→ 最后由真实使用需求选择 Connector，并通过试点持续加固
```

一期必须允许以下能力全部缺席：研发 Graph、测试 Graph、Claude 审计、飞书提单、Issues Collector 和共享 Knowledge Maintenance Graph。缺少它们时，Core 仍应通过手动输入、本地知识快照、版本化本地 records/future source refs 和本地 Handoff 完整运行；KMG submission/ack/Impact sync 不作为一期前置。

## 2. 当前真实状态

| 对象 | 当前状态 | 已经有的证据 | 还不能声称什么 |
|---|---|---|---|
| Better Product Graph 架构 | V1.4 已冻结为 distribution/eval implementation contract closeout | V1.3 产品架构不变；唯一公开 Skill、Atomic Skill Modules、source→dist/identity、Product/Plugin Suite 与 legacy eval migration 已收敛 | 不能声称软件、安装候选、Suite 或 runtime 已实现/验证 |
| Better Product Graph 软件 | 尚未实现 | 当前仓库没有 `src/`、Plugin、State Controller 或可运行 Core | 不能声称任何业务节点能真正恢复、校验或交接 |
| Bootstrap | v0.1 Draft 设计稿 | 已描述项目配置、知识、权限、模板、Connector、教学与恢复 | 不能把设计稿当作已运行；现有方案需要先瘦身再实现 |
| 通用 PRD 模板 | v0.1 Draft / Bootstrap 候选 | 已从 Better-Product-Plan 去掉金融/券商/投教专属内容，保留多语言、兼容、数据、灰度、回滚等通用能力 | 不是正式 default 或 quality-complete 模板；当前只保留可配置接口与可用 fallback，内容优化另列 Roadmap |
| Product Graph 自身 Evals / Golden Cases | `evals/product-graph v0.1` 为 `LEGACY / DOCUMENT-ONLY / NOT A V1.4 ACCEPTANCE BASELINE`；v0.2 待建 | v0.1 可作为旧 `ProductSpecPackage`、Owner approval、Dev/Test accepted 语义的迁移输入；G01/G03/G04 是 future fixture 规格 | 没有 v0.2 migration baseline、fixture 或 runtime PASS；不得原位把 v0.1 伪装成当前验收基线 |
| Codex Plugin Contract Suite | 合同已冻结，runner/installed candidate 未实现 | 已定义 discovery、direct/indirect/follow-up/negative activation、intent parity、relative resources、唯一公开 Skill、内部入口防绕过与 installed identity | 不能用 source tree walkthrough 声称安装合同 PASS，也不能替代 Product Golden Suite |
| Product Eval Pack / evals-generator | 合同方向已讨论，generator 未实现 | 架构中已有适用性与履行状态边界 | 不能声称已有自动生成能力或 Evals 已执行 |
| Knowledge Maintenance Graph | v0.2 Draft 设计稿，文件已按版本规则冻结；输入需求仍待重新确认 | 已定义唯一发布者、快照、Proposal、冲突、权限、影响和恢复边界；已确认所有正式 Product Decision Record 都属于未来 Source Corpus 候选 | 尚未实现共享知识服务；也不能把 source coverage 直接等同于已冻结 submission contract，或让 KMG 成为本地 BPG 的启动硬依赖 |
| Planning Learning Loop / 自进化 | Future / 待设计与原型验证 | 已确定学习应分流到项目知识、项目规划经验和通用插件经验，并保持提议式升级 | 不是当前 Graph Node、Gate 或 HITL；不能声称插件会自动学习、自动改写 Skill 或自动向上游提交 PR |
| Reviewer 权限 | 当前与一期均为 advisory only | Reviewer 可输出可追溯的关注事项，并由 Review–Optimize 采纳或记录不采纳理由 | 关注等级不阻塞 Ready/Release；外置团队最终把关，BPG 不能宣称 Reviewer 已批准 PRD |
| Trusted Upstream Update Check | Future / 待原型 | 已确认应由 Host Adapter/Bootstrap/Plugin manager seam 只读检查可信正式发布，并用直白中文提醒用户 | 不是当前业务 Node/Gate/HITL，不自动下载或安装，也不要求常驻 daemon |
| Connectors | 只有 mount point 和边界设计 | 已定义输入、知识、外部审计、飞书、研发和反馈位置 | 当前没有真实 Connector 实现、认证或远端回执 |
| Host 适配 | 只确定 Codex-first | Host Adapter 和 future multi-Host seam 已设计 | 不能声称已适配 Claude 或其他 Host |

## 3. 为什么这样排序

### 3.1 先验证最小完整系统，不先做组件大全

Better Product Graph 的价值不是“有很多 Skill、Schema 或 Connector”，而是一次真实 Run 能否帮助 PM 从原始 Signal 走到负责任的产品行动，并生成研发可用的 PRD。最早的运行证据必须来自端到端闭环，而不是孤立组件完成数量。

### 3.2 本地独立运行先于共享平台

State Controller、版本、恢复、审计、模板和本地 Handoff 是产品成立的必要基础。共享 Knowledge Maintenance Graph、多用户权限和外部 Connector 很重要，但都可以在稳定合同之后接入；若先做，会把尚未验证的产品逻辑过早固化成平台。

### 3.3 规格先于自动生成器，真实消费者先于 Connector 数量

Eval Pack、Test Design Contract、Knowledge Snapshot 和 Handoff 都应先有一个被人和下游理解的最小合同，再实现自动生成或网络连接。Connector 只有出现真实消费者、明确权限和可验证回执时才建设；不为“以后可能会用”同时实现全部。

### 3.4 Wave 管项目顺序，Round 只管当前复杂工作

本文使用 Better-Work 的 Wave 原则：每个 Wave 只有一个主要目标、明确依赖和退出条件。当前 Wave 内部确实复杂时，可以使用少量有界 Rounds；简单工作保持一次完成。项目不复制 `TASK/MAP/WAVE/ROUND` 文件套件，也不另建第二套状态系统。

### 3.5 文档审查不能替代真实 Graph 运行

当前仍处于架构规划阶段，并不存在可运行的 Core Graph、Host Adapter 或 State Controller。G01、G03、G04 等 Golden Cases 现在只是 future implementation acceptance specs/fixtures，不是已经执行的测试。架构阶段可以做静态 walkthrough、职责重叠检查和 contradiction audit，但结果必须标记为 `DOCUMENT-ONLY`，不能写成系统验收或 runtime evidence。

真正端到端验证只能在 Wave 1 的最小 Core、Codex Host Adapter 和 State Controller 实现之后开始。届时通过真实 Run 验证：访谈与挑战是否有效、轻重路径是否正确、Plan + 多 PRD 是否可运行、Reviewer 噪声是否可控，以及 resume、版本、Git 和恢复是否真的成立。文档模拟可以提前发现矛盾，但不能替代这些运行证据。

## 4. Roadmap 总览

| Wave | 唯一主要目标 | 进入下一 Wave 的核心证据 |
|---|---|---|
| Wave 1 | 建成可恢复、可审计的本地运行基础 | Codex 中能创建/恢复 Run，状态、版本、审计和本地降级真实可用 |
| Wave 2 | 跑通一个 Idea 到一份 PRD 的完整产品闭环 | 真实 Idea 从 Signal 到 released PRD 和本地 Handoff 全程可回放 |
| Wave 3 | 证明不同输入和复杂规划不会把 Core 做重或做错 | Feedback、Incident、Bug、`EXPERIMENT` 运行意图、1..N PRD 和复杂度档位通过对抗案例 |
| Wave 4 | 建立产品侧可交给测试的验证合同 | Eval Pack 规格/模板、evals-generator 和 TDD-ready Test Design Contract 可生成、审查和交接 |
| Wave 5 | 建成独立的共享知识维护能力 | 多 PM/研发/测试可读取同一正式快照并通过 Proposal/发布/影响闭环协作 |
| Wave 6 | 用真实试点选择集成并完成发布加固 | 至少一个真实项目持续使用；所选 Connector 有真实回执；核心质量和恢复指标达到发布条件 |

Wave 按依赖推进，但允许不改变主目标的支线并行。例如 Wave 2 期间可以评审通用模板，Wave 3 期间可以起草 Eval Pack 规格；支线不能绕过当前 Wave Gate，也不能把未验证产物写成已完成能力。

### 4.1 PRD Ready 能力如何跨 Wave 演进

PRD Ready 的作用始终只有一个：判断 **当前 exact PRD Candidate 是否具备本地发布和交接条件**。它不是组织审批，也不证明研发完成或测试通过。以下六项是当前的**最小稳定基线**，不是“先做轻 Gate、以后默认做成更重 Gate”。未来只有真实项目、下游消费者或正式政策证明有必要时，才增加绑定具体场景的条件式检查。

| Wave | PRD Ready 在这一阶段做什么 | 状态边界 |
|---|---|---|
| Wave 2 | 实现六项本地基础检查；READY 后自动生成 local released PRD 和 Product Handoff | 当前最小稳定基线 |
| Wave 4 | 当 Evals 或产品侧 Test Design 被判定为必需时，检查对应合同是否完整、版本是否匹配 | Conditional / future implementation；不检查测试是否执行通过 |
| Wave 5 | Knowledge、Decision、Plan、规则或证据更新后，重算 freshness、impact、stale 和 revalidation | Conditional / future implementation；KMG 缺席不阻断本地 Core 启动 |
| Wave 6 | 在 advisory/shadow mode 收集项目专属 readiness policy/profile 与 false-ready / false-block 证据 | Pilot-driven；不预建 Checklist 大全，也不授予 Reviewer 正式阻断权 |

任何新增 Ready 检查都必须同时满足：有真实消费者或版本化政策；能够确定性校验；绑定明确的 action/scope；不重复 Reviewer 的语义判断；不增加默认人工审批。当前 Reviewer 的关注等级和建议不进入 Ready 阻塞条件。**外置组织审批、Connector 授权或可用性、研发完成、测试执行完成，永远不进入 PRD Ready Gate。** 未经原型或试点验证的扩展保持 `CONDITIONAL / FUTURE / PROTOTYPE / PILOT-DRIVEN`，不写成当前已完成能力或必做承诺。

---

## 5. Wave 1：本地可运行基础

### 主要目标

让 Better Product Graph 在没有任何外部 Connector、研发 Graph、测试 Graph 或共享知识服务时，也能在 Codex 中建立项目、保存和恢复 Run，并可靠管理状态与文档版本。

### 为什么现在做

当前已有大量架构设计，但没有运行时证据。继续完善所有节点再开始编码，会延长“文档正确、系统不存在”的阶段。Wave 1 只冻结最小实现所需合同；尚未完成 Node Review 的后续能力不进入本 Wave。

### 依赖

- 从 V1.4 中选出 Wave 1 使用的最小合同并形成可实现基线。
- 复用 V1.4 继承的设计态 HITL disposition；真实中断密度、访谈误跳过率和运行体验留到试点校准。
- 审查 Bootstrap v0.1，删除一期不产生直接价值的重量。

### 核心交付物

1. **Better Product Graph Core 骨架**
   - 一个 Host discoverable Orchestration Skill：安装路径固定为 `skills/better-product-graph/SKILL.md`。
   - Core Atomic Skill Modules 使用 `src/core/atomic-skills/<node>/INSTRUCTIONS.md`，构建到公开 Skill 的 `references/atomic-skills/`；不是可发现 Skills。
   - 最小 Graph Manifest 和节点登记。
   - Node Result、Run State、Audit Event 的 `v0alpha` 合同。
   - 本地 Artifact Registry、版本、current pointer 与 append-only Audit。

2. **Deterministic State Controller**
   - 只有程序可以写正式状态和执行边。
   - Agent/Skill/Reviewer 只提交结果或迁移请求。
   - 支持失败恢复、幂等、版本冲突和旧结果 stale。
   - 它是 Plugin 内的薄 module/library，不是 MCP、CLI、daemon 或独立服务。

3. **Codex Host Adapter**
   - 支持自然语言和 `$better-product-graph` 显式入口。
   - 映射文件、Skill、Subagent、恢复与模型能力。
   - 不把 Codex 特有结构写进 Core 合同。
   - 实作 source→dist allowlist 和唯一公开 Skill 检查；禁止内部目录整体镜像/链接到 dist `skills/`。
   - 自动生成 `build-manifest.json`，绑定 Plugin SemVer、exact Git commit/dirty、architecture baseline、Core/rules/schema/Host Adapter versions 或 execution fingerprint、inventory 与 artifact hash。
   - 建立 Host conformance smoke：fresh installed copy 的 discovery、relative resources、internal-entry rejection 与 installed identity；不以 source tree 代替安装副本。

4. **瘦身后的 Bootstrap**
   - 检测 exact project root；没有 Git 时静默 `git init -b main`，但不自动 add/commit/push/remote。
   - 建立最小 Project Profile、Owner、项目语言、模板选择和本地目录。
   - 读取一个本地 exact Knowledge Snapshot；没有共享 KMG 时使用 local snapshot + versioned local records，并保留 future source exact refs。
   - Connector 只登记 mount/status，可以全部缺席。
   - 准备本地 Handoff、恢复位置和“什么情况下不能宣布完成”的规则。
   - 不在一期要求知识迁移向导、组织 Registry、复杂四级 readiness 或完整教学系统。

5. **模板和文档基础**
   - 继续保留冻结的 Better-Product-Plan upstream 模板作为安全 fallback。
   - 将 `templates/prd/general/PRD_TEMPLATE_v0.1.md` 视为 Draft/Bootstrap 候选，不要求在架构阶段冻结为最终 default。
   - 实现可配置 Template Profile seam、项目选择和 exact 模板版本记录；当前只保证可用 fallback，详细内容优化进入 11.8 的独立演进项。
   - 实现 `archived/`、`released/` 和 append-only Changelog 的最小生命周期。

6. **最小本地降级**
   - 手动 Signal 输入。
   - 本地知识读取、future source refs 与 local-only 边界。
   - 本地 Handoff。
   - 所有缺席 Connector 都显示 `NOT_CONFIGURED / NOT_AVAILABLE`，不伪装远端成功。

### Wave 1 研究建议的验收细化

- 固定 `execution_contract_fingerprint` 的最小输入与测试向量，使同一 Plugin SemVer 下 Core/rules/schema/Host Adapter 改变可被识别；不要求规划稿逐文件人工 hash。
- 建立八类最小 crash/recovery matrix：node 调用前、结果落盘前、状态迁移前、状态迁移后、并行分支部分完成、timeout、late result、未知 side effect。每类都验证 exact attempt/state、幂等与不假完成。
- 把 fan-out plan 先持久化，再 dispatch；保存 cancel/timeout/late-result disposition，恢复后不能重复派发或让 late result 覆盖 current Candidate。
- 把 Product research 的完成语义建议前置成基础 negative tests：有文件、Exit 0 或格式通过均不等于产品完成；没有对应 state/evidence/receipt 时必须拒绝成功声明。
- 这些项目细化现有 State/Host/测试合同，不新增业务 Node、Gate、Runtime、MCP、CLI、Service、签名、SBOM 或远程 attestation。

### 明确不做

- 不实现完整 Product Loop 的所有节点。
- 不实现共享 KMG、数据库、队列、Web UI、MCP Server 或专用 CLI。
- 不实现 Claude、飞书、Issues Collector、研发/测试 Graph Connector。
- 不实现第二 Host Adapter。
- 不一次性冻结所有 Schema、Profile 和模板。

### 验证与退出条件

- 新项目无 Git 时自动初始化；已有父级 repo/worktree 时不创建嵌套仓库。
- 一个 Run 可以创建、暂停、关闭会话后恢复，并从正确节点继续。
- Agent 不能直接写正式状态，也不能在缺少必要证据时自报完成。
- dist 只有 `skills/better-product-graph/SKILL.md` 一个 discoverable Skill；所有安装内相对资源可解析，内部 Atomic Skill Modules 无法被直接激活或绕过 Controller。
- fresh installed copy 的 inventory/hash/identity 与自动 `build-manifest.json` 一致；dirty/commit/architecture/execution fingerprint 改变可被检测，源码工作区不可替代安装身份。
- crash matrix、persist-before-dispatch fan-out、cancel/timeout/late-result 和 Host conformance tests 产生真实运行证据；未运行时不得标 PASS。
- Material 文档修改产生新版本；冻结/引用版本不被覆盖。
- 没有任何 Connector 时，项目仍能达到“本地可运行”；界面不显示“已发送/已共享”。
- Core runtime 建成后，Bootstrap 能选择项目指定 Template Profile、记录 exact 版本，并在未配置时可靠使用 fallback；v0.1 只需通过最小渲染 smoke，不因此升级为 quality-complete default。
- Core runtime 建成后，才运行 Product Graph 自身 Evals 的最小 Smoke Set，验证合同、权限、版本和 false-ready 防护；当前文档 walkthrough 不计入。

### 可并行支线

- Template Profile seam、版本 pinning 和 fallback 的原型；模板内容完善后置。
- Codex subagent 能力、隔离、并发和模型档位的只读原型。
- 从 legacy `evals/product-graph v0.1` 只提取迁移线索，不直接作为 Smoke acceptance；另建 v0.2 最小 Smoke fixture，runtime 出现前不标记 PASS。

### Wave 后续选择

- `PASS`：进入 Wave 2。
- `PARTIAL_PASS`：只允许不会依赖缺口的 Wave 2 小切片；缺口明确 carry-forward。
- 状态/版本/恢复不能成立：留在 Wave 1 修复，不能用更多业务 Skill 掩盖基础问题。

---

## 6. Wave 2：第一个完整 Product Loop

### 主要目标

用一个真实 Idea 跑通“先想清问题和产品决定，再形成规划与 PRD”的最小完整闭环，证明 Better Product Graph 是产品系统，不只是 PRD 写作模板。

### 依赖

- Wave 1 的 Core、State Controller、Codex Host Adapter、版本/审计、本地知识和本地 Handoff通过。
- 通用模板已有可用版本，或明确继续使用 exact upstream fallback。

### 核心交付物

- Signal ingest/prepare/classify/route 的最小路径。
- Evidence Map、Assumption Audit、Problem Learning、Problem Synthesis 和轻量 Problem Ready。
- 一个可恢复 `product.decision`，支持五种结果；本 Wave 主案例走 `COMMIT + NOW`。
- LIGHT Planning：目标结果、必要规划、`plan.slice / coverage.validate / reconcile` 和轻量 Plan Ready。
- 一个 `prd.generate`：内部组织产品内容、解析模板并由 Agent 写出同一份 PRD。
- Product / Engineering Feasibility / Testability Reviewer 的最小 advisory Review–Optimize，以及只负责汇总审查结果的 `review.finalize`；不实现 `review.gate`。
- 当前最小稳定基线的 PRD Ready；READY 后由 Controller 自动生成 local released PRD 和本地 Product Handoff。
- Decision、Roadmap、Product Changelog 和 Audit 的最小本地记录。

### PRD Ready 当前最小稳定基线

本 Wave 的 PRD Ready 只做六项本地检查：

1. 被检查对象是本次 Run 指向的 exact PRD Candidate。
2. 对当前 action/scope 计划执行的 Review 路线已经完成，或明确记录 `UNAVAILABLE / TIMEOUT`；所有可用结果绑定同一 Candidate 版本，路线状态不构成批准或否决。
3. `review.finalize` 已汇总每项 advisory concern 的 disposition：合理建议已纳入 exact Candidate，未采纳项保存理由；finalize 和关注等级都不构成 Gate 或阻塞 Ready。
4. Candidate 引用的上游 Decision、Plan、Slice、规则和证据仍是 current，没有已知 stale 引用。
5. 只有当 Evals 适用性被判定为 `REQUIRED` 时，才检查对应 Eval Pack 的要求是否已履行；`NOT_NEEDED / RECOMMENDED` 不被误当成缺失阻塞。
6. Template、Document Experience、文档版本和 Changelog 等机械完整性检查通过。

六项通过后，Controller 可以确定性地把 exact Candidate 提升为本地 `released` PRD，并创建对应 Handoff；没有真实 Connector 回执时，只声明“本地已生成、可交接”。PRD 阶段不再默认要求 Owner 做第二次确认。Problem、Product Decision 和 Product Plan 中已经确认的人类判断或 Owner 边界仍然保留，但它们是上游责任点，不在 PRD Ready 重复审批。

### 当前 Reviewer 的权限和外显结果

当前与一期的所有 BPG Reviewer 都是 **advisory only**；原 `review.gate` 已取消，使用 `review.finalize` 汇总审查结果。每项意见使用产品经理和研发能直接理解的语言，至少包含：关注事项、关注等级、绑定 exact Candidate 的 evidence/ref、可能影响和建议。关注等级只用于排序、聚焦和决定 Review–Optimize 先处理什么，不是 `BLOCK`，也不改变 Ready/Release 状态；`review.finalize` 也不是换名后的审批 Gate。

Review–Optimize 可以自动采纳合理建议，并在发生内容修改时生成新 Candidate 和对应的新审查记录；对于未采纳的 advisory concern，记录理由后继续，不建立内部审批。released PRD 或同源 Review Summary 必须向外置团队披露仍存在的关注事项、等级、证据、影响和 disposition。外置团队负责最终把关；BPG 只能说“已完成内部建议性审查并披露关注事项”，不能宣称“已批准”。

### 明确不做

- 不为一个案例实现全部 Incident、Bug、Experiment 和复杂项目规划。
- 不要求自动 evals-generator；本 Wave 只判断普通 AC 是否足够，并保留未来 Eval Pack seam。
- 不要求共享 KMG 或任何远端 Handoff。

### 验证与退出条件

- 一条真实 Idea 可从 Raw Signal 追溯到 exact Decision、Plan、Slice、PRD、Review、Ready、release 和 Handoff。
- Agent 先查本地知识和证据，不能把 PM 意见或 Sponsor 授权写成用户事实。
- 所有正式状态由 Controller 重算；旧 Reviewer 结果不能作为新 Candidate 的有效审查摘要。
- PRD 让产品、研发可行性和可测试性 Reviewer 都能理解目标、范围、规则、异常、AC、风险和未知。
- Owner 可以选择 STOP/WAIT/RESEARCH/EXPERIMENT；系统不会为了完成率强制产生 PRD。
- Review–Optimize 采纳合理建议时生成新候选版本并定向复审，不覆盖旧稿；未采纳建议保留 exact 理由并向外置团队披露。
- 本地 Handoff 只声明“已生成/可交接”，没有真实下游回执时不声明“研发已接收”。

### Wave 2 产品研究验收细化（P01—P07、P16）

- **P01 去方案锚定**：用“反馈直接给方案”的 fixture 验证 Agent 保留原话但重建用户目标/阻碍/损失，不把方案抄成需求。
- **P02 历史行为优先**：Evidence/Problem 阶段先查真实历史行为、现行规则与反例；不能只问主观偏好。
- **P03 方法匹配而非来源计数**：证据充分度说明所需证据方法、代表性与行动风险，不用固定来源数量替代判断。
- **P04 零不必要 PM 中断**：AI 可查信息自行查；只有 material PM-only unknown 才打断，并记录该问题会改变什么。
- **P05 Agent-first 决策支持**：每次关键选择先给首选、依据、最强反方与翻转条件，不把菜单甩给 Junior PM。
- **P06 一次实质挑战**：对 material 冲突作一次最高价值 challenge，保存分歧与 authority；不迎合，也不无限争辩。
- **P07 测 PM 理解而非满意度**：可理解性验收检查 PM 能否复述结论、证据边界、责任与下一步，不以“喜欢/满意”代替理解。
- **P16 Future-readable Decision Record**：隔离上下文的后来者只读 Record 与 refs，应能解释当时为何 STOP/WAIT/RESEARCH/EXPERIMENT/COMMIT、哪些未知会翻转决定，而不依赖原会话。

以上只细化现有 Discovery/Decision/Document Experience 验收，不增加新节点、问卷、固定轮次或批准 Gate。

### 可并行支线

- 以一名 Junior PM 做可理解性试用，记录 Agent 的辅导、挑战与中断负担。
- 起草 Product Eval Pack 通用规格，但不在本 Wave 实现 generator。

### Wave 后续选择

- 主闭环稳定：进入 Wave 3。
- 若主要失败来自模板过重，先调整 Renderer/Profile，不推翻 Core 产品语义。
- 若主要失败来自问题/决策质量，返回相应 Node Review 和 Skill，而不是增加更多状态层。

---

## 7. Wave 3：多路线与复杂度自适应

### 主要目标

证明同一个 Core 能正确处理 Idea、Feedback 和 Issue，也能对简单需求保持轻、对复杂项目按需加重。

### 依赖

- Wave 2 至少有一条完整真实 Run。
- Problem、Decision、Planning、PRD 的修复路径和版本链已经可回放。

### 核心交付物

- 用户反馈与“带着方案来的需求”路径；验证 Better Question、认知基座和 MVU 驱动学习。
- Incident 轻量核查包：优先给研发足够信息，不走重型 PRD 流程。
- Bug Baseline：区分 Implementation Deviation、Product Logic Defect 和 Spec Ambiguity。
- Product Decision outcome `EXPERIMENT`：作为统一 Product Planning → PRD → Review → Ready → Handoff pipeline 中的可逆实验运行意图，不建立独立 Fast Lane 或 Subgraph。
- STANDARD/PROJECT_SCALE Planning：Rounds、Waves、横向模块、纵向迭代和 1..N 独立 PRD Runs。
- bounded subagent 并行 Review/旁路研究和 disagreement-preserving join。
- 需求级 Downstream Feedback 的本地模拟和最早修复点路由。

### `EXPERIMENT` 如何复用统一 Product Pipeline

代码生产成本下降后，对于低风险、低成本、可逆、可观测且学习价值高的事项，真实实验可以替代一部分在规划阶段反复空转。因此，`EXPERIMENT` 可以适当缩短前期证据收集和方案完整度要求，但不能放松以下内容：

- 要验证的 key unknown。
- exposure：实验对象、范围、流量、时长或其他暴露边界。
- measurement：观察什么，以及如何知道实验是否产生有效学习。
- `continue / adjust / stop` 判断条件。
- 安全、合规、guardrails 和 rollback。
- 实验结果如何回到 Product Decision。

`EXPERIMENT` 不自动等于 `LIGHT`。复杂度与风险仍由同一 Router/Profile 判断；涉及高风险用户、不可逆数据、安全、隐私、合规或重大暴露的实验必须升档，必要时停止。实验 PRD 继续使用同一 Product Planning、PRD、Reviewer、PRD Ready、released 文档和 Handoff，不复制 Experiment Plan、Experiment PRD、Experiment Review、Experiment Ready 或 Experiment Handoff。

实验完成后，结果经统一 `signal.ingest` 进入系统，作为绑定原 Experiment Decision、PRD 版本和 exposure 的 typed result/evidence，再回到 Product Decision 做 `continue / adjust / stop / redesign`。它不是旁路反馈，也不允许仅凭“实验已上线”自动宣告成功。

**Superseded decision note：**此前 Roadmap 使用过“Experiment Fast Lane”表述，容易被理解为独立产线或独立 Subgraph。该设计意图已被本节取代；实现时不为旧 Fast Lane、重复 Artifact 或独立 Ready/Handoff 建兼容层。

### 明确不做

- 不把 Better-Work 全套文件或状态复制进产品。
- 不因复杂项目而默认建设多 Agent 平台。
- 不将研发/测试 Reviewer 误写成真实研发承诺或测试执行。
- 不建设独立 Experiment Fast Lane/Subgraph，也不复制 Planning、PRD、Review、Ready 或 Handoff。
- 不建设 Experiment Portfolio；只有未来出现并行实验规模、用户/指标相互干扰、暴露冲突或资源治理的真实证据时，才另行原型。

### 验证与退出条件

- 在真实 runtime 上执行 G01、G03、G04 和真实样本，能够接受条件式正确结果而不是只匹配一个标准答案；这些 fixture 在实现前不构成通过证据。
- LIGHT 不被重流程拖慢；复杂度增加时可以升到 STANDARD/PROJECT_SCALE，收敛后可审慎降级。
- 一个 Product Plan 能切出多份高内聚、低耦合、端到端可验证的 PRD；未来和等待项不会被提前生成。
- Incident/Bug 快路没有被 PRD 模板、默认 Reviewer 或可读性规则做重。
- `EXPERIMENT` 通过同一 pipeline 形成 exact PRD、Review、Ready 和 Handoff；高风险实验不会因 outcome 名称而自动走 `LIGHT`。
- 实验结果以绑定原 Decision/PRD/exposure 的 typed result/evidence 经统一 Signal Intake 回到 Product Decision。
- 并行 Reviewer 只读同一 exact Candidate；输出、失败、超时和分歧都被记录并披露，不被静默吞掉，也不被自动升级为正式阻断。
- 初步统计整条 Run 的 Human-in-the-Loop 次数，为最终密度审计提供数据。

### Wave 3 产品研究验收细化（P08—P11、P17）

- **P08 Activated Slice 证明产品增量**：每个 activated PRD Run 必须对应可独立观察的产品状态改变，而不是只完成技术层或文档片段。
- **P09 独立能力要真实成立**：切片独立性用真实依赖、发布/回滚和验证边界证明；不能靠改名或人为拆文件伪造低耦合。
- **P10 Coverage disposition 透明**：重要内容逐项落到 current/future/experiment/wait/stop/unresolved，并可追溯重复、冲突和未覆盖原因。
- **P11 LIGHT 必须实际轻**：以总步骤、HITL、等待和文档负担验证 LIGHT；保留质量底线但不运行无价值的重型 panel/文件套件。
- **P17 Roadmap 不是 feature inventory**：Plan/Roadmap 必须表达 outcome、依赖、学习/停止条件与暂不做事项；功能清单长度不构成规划完成。
- bounded fan-out 继续验证 persisted plan、cancel/timeout/late-result、disagreement-preserving join；任何 late result 只能作为带 exact attempt 的输入，不能静默覆盖 current。

这些验收使用现有 Planning/Profile/Review 能力，不制造新 Planning 节点、Gate 或独立实验路线。

### 可并行支线

- KMG 最小合同原型：仅 snapshot read、proposal submit、status 和 impact，不建设共享服务。
- 一个 Connector contract fake/dry-run，用于验证可缺席和副作用边界。

### Wave 后续选择

- 主要业务路线和复杂度机制通过：进入 Wave 4。
- 若某条路线缺少真实使用价值，可以保留合同而暂缓实现，不为“流程完整”强行补齐。

---

## 8. Wave 4：Evals 与 TDD-ready 测试设计合同

### 主要目标

把“如何判断产品做对了”变成可生成、可审查、可交给未来测试 Graph 的产品侧合同，同时保持测试工程职责边界。

### 依赖

- Wave 2/3 已有真实 PRD、AC、Review Finding 和至少一个概率性或多合理输出需求。
- Testability Reviewer 能读取同一 exact PRD Candidate。

### 核心交付物

1. **Product Eval Pack 通用规格与模板**
   - 评估目标和适用范围。
   - PRD 规则/AC 的 exact 映射。
   - happy、edge、failure、adversarial cases。
   - Rubric、Ground Truth、来源、版本和未知。
   - 成功、继续观察、停止和回归条件。

2. **可插拔 `evals-generator / evals.build`**
   - 内部原子能力为 `scope → generate → review`。
   - 可以由当前 Host 的 bounded subagent 实现，未来也可接入其他 Agent。
   - 生成的是候选 Eval Pack；专业 Ground Truth 不能由生成 Agent 自行批准。
   - 当实验 PRD 判定需要 Eval Pack 时，复用同一个 generator、适用性判断和版本合同；不建设 Experiment Evals 专线。

3. **TDD-ready Test Design Contract**
   - 在模型 Evals 之外，表达功能测试意图、主要场景、AC 映射、状态/权限、边界/异常、回归范围和可观察结果。
   - 能给测试团队或未来测试 Graph 作为测试设计输入。
   - 不声称 Better Product Graph 实施严格开发 TDD。
   - 只有当当前需求将 Eval Pack 或产品侧 Test Design 判定为 `REQUIRED` 时，PRD Ready 才条件式检查合同完整性、AC 映射和 exact 版本匹配；不检查测试执行结果。

4. **Better Product Graph 自身系统 Evals**
   - 先把 `evals/product-graph v0.1` 固定为 `LEGACY / DOCUMENT-ONLY / NOT A V1.4 ACCEPTANCE BASELINE`，逐项 disposition 旧 `ProductSpecPackage`、Owner approval、Dev/Test accepted 语义；不原位改写或伪装通过。
   - 另建 Product Golden Suite v0.2 migration baseline，把 G01/G03/G04 从 future specification 实作成可运行 Smoke/Regression；runtime 前保持 `NO PASS`。
   - 加入真实历史案例、下游澄清/返工和 false-ready 反馈。
   - 阈值用真实基线校准，不用文档中的初始百分比直接宣布达标。
   - 评估产品判断与 end state，不只检查中间 Artifact 存在或字段齐全。

5. **Plugin Contract Suite 与 Product Suite 分治**
   - Plugin Suite 继承 Wave 1 的 fresh-install checks，并覆盖 direct/indirect/follow-up/negative activation、intent parity、relative resource resolution、唯一公开 Skill、内部入口不可绕过与 installed-copy identity。
   - Product Golden Suite v0.2 只评价 G01/G03/G04 的产品判断/end state；Plugin PASS 不推出 Product PASS，反之亦然。
   - 两者都是系统验收套件，不注册业务 Node/Gate，也不并入某个 PRD Eval Pack。

### 职责边界

Better Product Graph 可以生成产品侧验证依据和候选测试设计规格；未来测试 Graph 才拥有：

- 正式测试用例工程化。
- 自动化测试代码。
- Runner、环境、数据准备和执行编排。
- 执行结果、缺陷和最终测试 verdict。

因此“已生成 Test Design Contract / Eval Pack”永远不等于“已完成测试”或“测试已通过”。

### 明确不做

- 不在本 Wave 建设完整测试 Graph。
- 不让 evals-generator 同时生成案例并自行把答案提升为可信 Ground Truth。
- 不要求所有确定性需求都生成重型 Eval Pack。

### 验证与退出条件

- `NOT_NEEDED / RECOMMENDED / REQUIRED` 与 Fulfillment 状态在真实样本中保持正交。
- 复杂但确定性的需求可由 AC/Test Design Contract 支撑；概率性、多合理输出或分布依赖需求能生成可审查 Eval Pack。
- PRD 语义变化只使受影响 Evals/Test Design 部分 stale，不默认全量重跑。
- Testability/Domain Reviewer 能指出不可执行案例、伪 Ground Truth 和覆盖缺口。
- 一个模拟 Test Graph 能只凭 Handoff 合同理解要设计什么测试，以及哪些内容仍需专业确认。
- 条件式 Ready 检查只能证明产品侧验证合同可交接，不能输出“测试已执行”或“测试已通过”。
- Product Golden Suite v0.2 与 Plugin Contract Suite 分别报告 evidence、NOT_RUN/FAIL/PASS；任一未运行时不得从另一套或文档审查推导 PASS。
- v0.1 只在完整 legacy 标签与 migration provenance 下引用；G01/G03/G04 已落地并在真实 runtime 执行前继续是 future fixtures。

### Wave 4 产品研究验收细化（P12—P14）

- **P12 无会话下游消费**：隔离上下文的模拟研发/测试消费者只凭 exact Handoff、PRD/Eval/Test Design 与 refs，能说明要构建/验证什么、仍缺什么；不能依赖原聊天补课。
- **P13 双向追溯与定向 stale**：Decision/Plan/Slice/PRD/AC/Eval/Handoff 可正反追踪；一次语义变化只使受影响案例/字段 stale，纯排版不触发全量失效。
- **P14 概率性 eval 最低可信度**：样本/分布、Rubric、Ground Truth provenance、独立 review、失败解释与 stop/regression 条件齐全；案例数量或生成 Agent 自评不能替代可信度。
- architecture research 的 end-state eval 在此冻结为 runner 验收：既比较最终产品状态，也检查 false-ready、虚假授权、证据边界与停止纪律；不只评中间文本相似度。

至此 P01—P17 分布在 Wave 1—4 的既有验收中：Wave 1=P15；Wave 2=P01—P07/P16；Wave 3=P08—P11/P17；Wave 4=P12—P14。它们不改变 Wave 顺序、一期范围或节点图。

### 可并行支线

- 前端和 backend-service Template Profile 的需求研究；只有真实案例证明 general 不够时才创建。
- 外部 Claude 对 Eval Pack 的只读审计原型。

### Wave 后续选择

- 验证合同被真实测试消费者接受：进入 Wave 5。
- 若测试消费者只需要 PRD 内的轻量 Test Design section，则保持轻量，不为独立文件而独立文件。

---

## 9. Wave 5：独立 Knowledge Maintenance Graph 与团队共享

### 主要目标

先定义多 PM、研发和测试真正需要的 Knowledge Product 与 raw + derived consumer requirements，再把本地快照和 source candidates 接入版本化知识发布与影响闭环，同时不改变 Better Product Graph 的产品决策权责。

### 依赖

- BPG 的 `read snapshot / submit proposal / query status / consume impact` 边界已经通过本地实现验证；其中 exact 提交内容、触发时机和关联方式仍等待 Knowledge 产品需求反推。
- Product Decision Ledger 能提供 `STOP / WAIT / RESEARCH / EXPERIMENT / COMMIT` 的 exact 正式记录及 immutable evolution chain；是否、何时以及如何提交给 KMG 仍等待消费场景反推。
- 至少有两个真实角色或业务 Graph 需要共享同一项目知识。
- 先重新审查并瘦身 KMG v0.2；保留必要治理，避免直接实现完整企业知识平台。

### 实施前置：先定义 Knowledge 产品需求，再反推提交合同

此前曾把 Product Graph 的知识输出主要理解为“从 PRD/Run 中提取压缩后的可复用知识并提交”。这个理解不完整。未来 Knowledge Maintenance Graph 的输入至少要研究两层：

1. **Raw Data / Source Corpus（原始材料层）**：与产品事项有关、能够回到原文核验的材料，包括 PRD 本身、全部正式 Product Decision Record、原始 Signal/用户反馈、访谈与研究材料、Evidence、附件，以及相关执行、实验、研发和测试结果。这里的“raw”是相对于 Knowledge Graph 的来源角色而言；PRD 和 Decision Record 即使已经经过产品加工，进入 Knowledge Graph 时仍然可以是可追溯 source/raw data。
2. **Derived / Compressed Knowledge（派生与压缩知识层）**：从原始材料中提炼出的事实、规则、模式、约束、结论、冲突、不确定性和适用范围。它应能追溯到来源，但不能替代来源本身。

#### Product Decision Record 的 source coverage

未来 Source Corpus 必须覆盖所有正式 Product Decision outcome，而不是只收集最后产生 Released PRD 的 `COMMIT`：

- `STOP / WAIT`：保存为什么不做或暂时不做、当时证据与假设，以及重启、复查或翻转条件。否则团队失忆后，后续 PM 或研发可能重复讨论、重复研究甚至重复建设已经否决或后置的事项。
- `RESEARCH / EXPERIMENT`：保存当时的认知缺口、验证方法、暴露与测量设计，以及研究或实验结果如何回流 Decision。
- `COMMIT`：保存正式方向、适用范围和当时承诺的准确语义；Released PRD 是其后续落地产物，不能反向替代完整 Decision 依据。
- **Decision evolution**：旧 Record 保持 immutable；维持原决定、推翻原决定或新 Record `supersedes` 旧 Record 的变化链，都是项目认知如何演化的重要 raw source。Knowledge 消费者需要看到“当时为什么这样决定、后来什么变化使决定被维持或推翻”，不能只看到最终 PRD 或最终结论。

这是未来 Knowledge Requirements 的 **source coverage 结论**，不是当前 Product Graph → KMG submission contract。它不表示所有 Decision Record 必须全量复制或每次自动提交，也不预先决定引用、索引、同步、权限、去重、保留、采纳或 canonical publication。

正确建设顺序是：

```text
定义 Knowledge Base / Knowledge Maintenance Graph 的使用场景与产品需求
→ 明确检索、共享、权限、版本、provenance、原文与派生知识关系、更新、冲突、过期和跨角色协作要求
→ 由这些要求反推 BPG 应提交哪些 raw sources、哪些 derived knowledge、何时提交、如何关联、如何接收采纳状态
→ 最后才原型验证并冻结数据合同与实现策略
```

因此，当前**不冻结**材料是全量复制、引用还是索引，不冻结自动提交触发器、Schema、审批/采纳、去重、保留、权限或同步实现。Node Review 17（Knowledge impact + proposal）维持 `DEFERRED / PENDING KNOWLEDGE REQUIREMENTS`；现阶段只保留 Product Graph 读取知识、提交候选更新和接收状态/影响的边界，不把“仅提交压缩知识”升级为正式结论，也不允许 Product Graph 直接发布 canonical knowledge。

进入 KMG 实现前，至少要能够回答这些验收问题：

- PM、研发、测试分别在什么决策或工作场景下检索和共享知识？
- 用户如何从一条派生知识回到其原始材料、版本和完整 provenance？
- 系统如何区分来源事实、派生判断、冲突观点、不确定信息和已经过期的结论？
- 跨 PM、研发和测试共享时，哪些内容可见、可引用、可提议修改或必须隔离？
- 原始材料或规则更新后，如何识别冲突、过期和对 Decision/Plan/PRD/Eval/Handoff 的真实影响？
- 没有 Released PRD 的 `STOP / WAIT / RESEARCH` Decision，哪些角色会在什么场景下查询，它们需要看到哪些重启、复查或结果回流信息？
- 用户能否从当前 Decision 追溯到被维持、推翻或 supersede 的 immutable 旧 Record，并理解认知为什么发生变化？
- 基于上述需求，BPG 应提交哪些 raw sources 与 derived knowledge，何时提交，二者如何关联，并如何收到 `accepted / rejected / needs evidence / published` 等采纳状态？
- 哪些能力必须由 KMG 作为 canonical publisher 承担，而不能下放给 Product Graph？

### 核心交付物

- 独立 KMG 的最小可运行 Graph：接收、来源核验、去重/冲突、Owner 审核、版本发布、Snapshot 和 Impact。
- 多 PM、研发、测试读取同一 named snapshot；不同角色通过最小权限提交 Proposal。
- `SUBMITTED → REVIEWING → ACCEPTED → PUBLISHED` 与 `NEEDS_EVIDENCE / CONFLICT / REJECTED` 的真实状态。
- Snapshot 版本、来源、freshness、权限和 omitted/denied/unavailable 边界。
- 所有正式 Product Decision outcome 及其演化链可作为可追溯 source 被消费，同时 Product Decision Ledger 仍是正式 Decision 真源。
- 基于已确认 consumer requirements 选择并验证 submission 机制（可能是 Outbox，也可能是 Connector/reference/index）、首次同步、幂等、冲突、supersedes 和消费者 acknowledgement。
- 新知识影响 exact Decision/Plan/PRD/Eval/Handoff 时的定向复审，而不是静默覆盖或全量重跑。
- Knowledge、Decision、Plan、规则或证据更新后，对相关 PRD 重算 freshness、impact、stale 和 revalidation；只让受影响 Candidate 重新进入必要检查。

### 明确不做

- 不建设包罗所有公司的通用知识平台。
- 不让 KMG 重做 Product Owner 已经作出的产品决定。
- 不让业务 Graph 直接发布 canonical knowledge。
- 不在 Knowledge 产品需求和真实使用场景明确前，把“只提交压缩知识”固化为唯一输入合同。
- 不提前冻结 raw source 的复制/引用/索引方式，以及触发器、Schema、审批、去重、保留、权限或同步方案。
- 不因为 KMG 暂时不可用而让本地 BPG 整体停机；只有明确依赖最新团队正式知识的危险 action 受约束。
- 不在没有真实权限模型前开放跨项目共享。

### 验证与退出条件

- 两个以上角色读取同一 exact snapshot，权限不同但不会泄漏被拒绝内容。
- BPG 提交的 Proposal 在 PUBLISHED 前不会被当成正式知识。
- 一个没有 Released PRD 的 `STOP` 或 `WAIT` Record 仍能被授权消费者检索其理由和重启条件；新 Decision 不覆盖 immutable 旧 Record，而是通过 `supersedes` 保留演化链。
- 并发修改不会 last-write-wins；旧 Snapshot 和历史决定不被覆盖。
- KMG 离线时 BPG 使用可接受的固定快照并排队 Proposal；恢复后幂等对账。
- 新 Snapshot 只使实际受影响产物进入 REVIEW_REQUIRED/INVALIDATED，并保留旧版本与原因。
- 团队共享和发布没有制造第二套 Decision/Roadmap 真源。
- KMG 缺席时，本地 Core 仍可用固定快照运行；只有 action/scope 明确要求最新正式知识时，才按政策限制对应 Ready，而不是阻断 Core 启动。

### 可并行支线

- Knowledge Connector 的本地与远端实现对照测试。
- 选取最有价值的 1—2 个真实知识源进行只读采集原型；不同时接入全部文档系统。

### Wave 后续选择

- 共享价值和治理成本被验证：进入 Wave 6。
- 如果单团队本地模式已经满足真实需求，可推迟共享服务，Core Roadmap 不因此停滞。

---

## 10. Wave 6：真实试点、选择性 Connector 与发布加固

### 主要目标

让 Better Product Graph 在真实项目中持续运行，用真实使用证据选择必要集成、修复质量和恢复问题，并形成可发布版本。

### 依赖

- 至少 Wave 1—4 的本地闭环通过。
- 若试点需要团队共享知识，则 Wave 5 对应能力通过；否则继续 local-only 并明确限制。

### Connector 建设顺序

先稳定统一的 Connector seam：exact input/output、权限、幂等、超时、未知结果、receipt、重试与审计。之后按真实价值一次选一个实现：

1. **Input：Issue / Feedback Collector**
   挂在 `signal.ingest`，默认只进 Inbox，不直接创建完整 Run。

2. **External Audit：Claude / 其他 Agent**
   挂在固定 Candidate Review 点，只读 exact snapshot，返回 advisory concern；不能写正式状态、阻塞 Ready/Release 或替代外置团队把关。

3. **Output：Feishu Project 提单**
   挂在 `handoff.dispatch`，只有相应 Ready/轻量检查和明确副作用授权后写入；必须保存远端 ID/receipt。

4. **Knowledge Maintenance Graph Connector**
   在 Knowledge Requirements 和接口版本确认后连接 snapshot、submission、status 和 impact；KMG 未连接时继续 local snapshot + versioned local records。

5. **Development Graph Connector**
   交付 Product（包含 `EXPERIMENT` 运行意图）/Incident/Bug Fix 合同，并接收需求级退回。

6. **Test Graph Connector**
   交付 Eval Pack/Test Design Contract，接收规格缺陷与验证结果；测试执行权仍在测试 Graph。

这里是价值排序，不是强制所有项目都按同一顺序安装。某项目若飞书提单是最早真实痛点，可以先实现飞书；但 Connector seam 与副作用合同必须先通过，且不能同时全量并行建设所有 Connector。

### 核心交付物

- 至少一个真实项目、多个真实 Signal 和连续多次恢复/修改/交付。
- 根据试点选择并实现至少一个高价值 Connector；其他保持可缺席合同。
- 真实 PM、研发和测试消费者反馈；将返工、错误路由、假 Ready 和规格缺陷转成 Regression Cases。
- 性能、成本、失败恢复、权限、隐私、prompt injection、并发写入和 Connector 未知结果加固。
- Codex Host Adapter 的稳定发布包和安装/升级/回滚说明。
- 是否需要第二 Host Adapter 的证据；没有真实 Host 需求时不实现。
- 根据真实项目与下游政策，在 advisory/shadow mode 原型少量项目专属 readiness policy/profile，例如安全、隐私、合规、数据迁移或专业领域约束；只收集试点确实需要的证据，不改变当前 Release 决策。
- 用外置团队的真实放行、退回和后续风险结果估算 false-ready / false-block；若检查不能证明净收益，则删除或保持项目可选，不提前授予机器阻断权。

### 明确不做

- 不以 Connector 数量作为成熟度指标。
- 不在真实需求出现前建设多租户平台、跨 Host Multi-Agent 协作平台或统一 Web 工作台。
- 不因为单次演示成功就宣布稳定发布。

### 验证与退出条件

- System Acceptance Baseline、核心 Golden Cases、Smoke/Regression 和真实历史案例通过当前发布 Gate。
- false-ready、越权、历史覆盖、Connector 假成功和关键错误路线为零或按正式政策达到不可接受即阻塞的标准。
- 至少一个真实下游消费者能理解 Handoff，并给出可追踪 receipt/反馈。
- 真实 PM 能从暂停点恢复，并能理解为什么系统建议停止、等待、研究、实验或投入。
- 完成全 Graph **Human-in-the-Loop Interaction Density Audit**，对每个中断给出保留、合并、自动化或按风险触发 disposition。
- 完成架构与 Roadmap 总体 Review、Product Goal-Based Audit、独立外部审计（若可用）和试点反馈 disposition。
- 冻结发布版本、迁移说明和 Changelog；仍未验证的能力保持 Draft/Future，不随发布自动升级。
- 项目专属 Ready Profile 的每项 shadow 检查都能追溯到真实消费者或版本化政策，且没有演变为通用 Checklist 大全、当前正式阻断或新增默认人工审批。

### 后续选择

- 达到发布条件：冻结第一个可用版本并进入持续迭代。
- 某一 Connector 失败：回退本地路径，不阻断 Core；按真实价值决定修复或放弃。
- 第二 Host 或跨 Agent 协作需求得到证据：另开增量 Roadmap，不把它们偷塞进当前发布。

---

## 11. 必要基础、并行支线与未来扩展

### 11.1 必要基础

- 可运行 Core、Codex Host Adapter、唯一公开 Orchestration Skill 与内部 Atomic Skill Modules。
- Deterministic State Controller、Registry、版本、恢复和 Audit。
- 手动 Signal、本地知识快照/records、本地 Handoff。
- 一份由 exact Template Profile 配置选中的可用 default/fallback PRD 模板。
- System Acceptance Baseline、Smoke/Regression 和真实试点。

### 11.2 可并行支线

- 通用模板 Review 和轻量化。
- Product Eval Pack/Test Design Contract 规格。
- Codex subagent 能力与 External Audit dry-run。
- KMG 的本地合同 fake/prototype。
- Connector seam 的无副作用 contract test。

### 11.3 可选扩展

- Issues/Feedback Collector。
- Claude/其他 Agent 外部审计。
- Feishu Project 提单。
- Development/Test Graph 真连接。
- 前端、backend-service 或领域 Template Profiles。

### 11.4 未来研究

- 第二 Host Adapter。
- 跨独立 Host/provider 的 Multi-Agent Collaboration。
- 共享服务、数据库、队列、Web 工作台。
- 更复杂的组织权限、跨项目知识和多租户治理。
- Experiment Portfolio：仅当并行实验规模、用户或指标相互干扰、暴露冲突或资源治理出现真实证据时再原型；不作为统一实验 pipeline 的默认组成。
- 严格开发 TDD 或完整测试 Graph；它们不是 Better Product Graph 当前产品职责。

### 11.5 Future：Planning Learning Loop / Better Product Graph 自进化

状态：`FUTURE / PROTOTYPE REQUIRED / 非当前 Wave 验收项`。

长期目标是让 Better Product Graph 每完成一次规划，都有机会同时积累项目知识和规划方法经验；但“学到东西”必须表现为**有来源、可审查、可验证、可回滚的候选改进**，而不是隐藏地自我改写。本节只记录未来能力方向，不新增当前 Graph Node、Gate 或 HITL。

#### 三层学习去向

| 学习去向 | 典型内容 | 正确落点与边界 |
|---|---|---|
| 项目事实 / 产品知识 | PRD、全部正式 Product Decision Record 及其 immutable/supersedes 演化链、Signal、反馈、访谈、Evidence、附件、执行/实验/研发/测试结果，以及由其提炼的事实、规则、约束、结论与不确定性 | 保留 raw source + derived knowledge 两层候选，走未来 Knowledge Maintenance Graph；依赖 Knowledge Requirements，不由 Product Graph 直接发布 canonical knowledge |
| 项目级规划经验 | 本项目有效的提问方式、模板差异、常见遗漏、决策/拆分/审查规则和领域习惯 | 形成 project-local learning / protocol / policy proposal；一次偶然成功或失败不能自动升级为硬规则 |
| 通用插件经验 | 可跨项目复用的 Skill、workflow、template、validator、router/policy 改进 | 进入 upstream improvement queue；证据充分后生成可审查的 patch、branch 或 PR proposal。不得静默修改已安装核心 Skill，也不得未经授权 push 或创建远端 PR |

#### 建议的未来闭环

```text
每次规划结束：轻量 incremental reflection
→ 多次运行累计，或出现重复失败、用户纠正、高价值模式：cross-run reflection
→ 提取学习候选
→ 按 project-specific / generic，以及 knowledge / method / execution 两个维度分流
→ 检查证据、反例、冲突、退化、重复、权限、敏感信息与提示注入风险
→ 生成可审查 proposal
→ 项目层或上游层按风险审查并吸收
→ 用后续 Run / Eval 验证是否真正改善规划质量
→ 保留、修订或回滚
```

增量反思解决“这一次有什么值得记住”；跨历史反思解决“多个 Run 是否出现稳定模式”。重复观察可以提高调查优先级，但不自动证明因果，也不能仅凭一次成功把通用规则推广到所有项目。

#### 每个学习候选的最小追溯

未来原型至少要记录：

- 来源 Run 和 exact Artifact。
- 可观察事实与 Agent 解释，两者分开保存。
- 建议适用范围和明确不适用范围。
- 支持证据、反例和仍未知的信息。
- 建议落点：项目知识、项目本地方法，或通用上游能力。
- 风险、当前状态和责任/权限边界。
- 后续 Run/Eval 的验证结果。
- `supersedes`、修订和 revert 关系。

不保存模型 hidden chain-of-thought，也不把秘密、无授权的跨项目内容或敏感原文混入通用升级候选。保存的是可审计的观察、结构化理由、证据、反例、建议和验证结果。

#### 从 better-test 吸收、但不照搬的机制

- 保留“每次工作后的增量反思 + 多次历史后的跨 Run 反思”两层节奏，不照搬测试专属目录和固定阈值。
- 保留 project-specific 与 generic 分流，避免把单项目技巧污染通用插件。
- 为通用改进建立可去重、可陈化、可对账的 upstream improvement queue；队列状态必须与仓库真实状态一致。
- 高风险核心规则、Router/Validator/Policy 变化需要人审或对抗审计；低风险文字建议也先形成 proposal，不直接自我改写。
- 获准 promotion 时，在有授权的上游工作流内把 patch、queue status、tests-or-eval、Changelog 和本地 commit 作为一次原子 promotion 完整处理；任何一步失败都不能留下“代码已改但队列仍 pending”或相反的半完成状态。
- 吸收后必须通过后续真实 Run 或 Eval 证明规划结果有所改善；“文件已经修改”不等于学习有效。

#### 与现有 Waves 的依赖关系

这是一张依赖图，不改变任何 Wave 的退出条件：

| 现有阶段 | 为未来 Learning Loop 提供什么 | 是否新增当前承诺 |
|---|---|---|
| Wave 1—3 | Bootstrap、exact Run history、Artifact/Audit、版本和本地 Git，为反思提供可追溯材料 | 否，只是前置基础 |
| Wave 4 | Evals 和真实下游反馈，为“规划是否改善”提供比较方法 | 否，测量方案仍待原型 |
| Wave 5 | Knowledge Requirements、raw/derived 边界和 KMG，承接项目事实/产品知识候选 | 否，不能绕过 KMG 发布权 |
| Wave 6 或后续增量 Roadmap | 在真实试点中原型 incremental/cross-run reflection、项目本地 proposal 和 upstream queue；按需接 Git/upstream Connector | Future / pilot-driven，不进入当前发布 Gate |

#### 待后续设计和原型验证

- incremental 与 cross-run reflection 的触发条件、频率和停止条件。
- project-local memory、项目级 planning protocol/policy 与 Knowledge Graph 的边界。
- 学习候选的最小 Schema，以及 knowledge / method / execution 分类是否足够。
- 风险分级、自动吸收上限，以及哪些变化必须人审或对抗审计。
- 上游仓库权限、branch/patch/PR 授权流程和失败恢复。
- 不同 Host Adapter 对 subagent、Git 和上游提议的能力差异。
- 如何用 Evals、真实返工和下游反馈衡量规划质量改善，而不是只测格式变化。
- 如何防止错误经验放大、知识污染、提示注入和项目隐私泄漏。
- 队列的去重、陈化、关闭、重开、账实对账和长期维护成本。

只有这些问题通过真实原型得到答案，Planning Learning Loop 才能进入后续正式架构和实施 Roadmap。

### 11.6 Future Trigger-Based：Formal Review Gate + Reviewer Governance

状态：`FUTURE / TRIGGER-BASED / PROTOTYPE REQUIRED / 非当前 Wave 验收项`。

当前外置团队仍逐项审核并最终把关，因此 BPG 内部没有必要复制一套审批系统。真正的 Review Gate 与 Formal Reviewer Governance 是同一项未来治理能力，不另建重复 Wave 或平行路线。只有真正出现以下变化时，才评估 `review.gate`、Reviewer formal blocking、Domain Owner、Policy 和 Waiver：

- 外置团队不再逐项审核，原有最终人工把关发生实质转移。
- BPG 开始无人值守地驱动研发或发布，机器建议会直接转化为高影响 action。
- 真实风险事件，或监管、安全和责任政策明确要求机器在执行前阻断。

触发条件出现后，也不能因为 Agent 被命名为“安全 Reviewer”“Domain Owner”或“合规专家”就自动获得权力。Future Review Gate 必须与真实治理权一起原型，至少需要：

- 可验证的真实身份、专业资质或组织授权。
- 只对明确 action/scope 生效的 block，不能用一个意见阻断无关产物或后续版本。
- 可追溯、版本化的 policy provenance，并明确何时生效、适用于谁。
- Waiver authority、适用 scope、理由、expiry 和撤销条件。
- Candidate 版本、exposure 或政策变化后的重验证。
- 全量 Audit，以及误阻塞、漏阻塞和绕过行为的评估。

该原型必须依赖可用 Evals、真实权限/身份系统、不可抵赖 Audit、正式组织 policy 和独立安全审计。未满足这些依赖前保持 advisory only；即使满足，也先以 shadow mode 比较机器建议与外置团队结果，再决定是否授予 action-scoped formal authority。它不新增当前 Node、Gate 或 HITL，也不扩大一期。

### 11.7 Future UX / Maintenance：Trusted Upstream Update Check

状态：`FUTURE / PROTOTYPE REQUIRED / 非 Product Graph 业务节点`。

未来使用 Better Product Graph 时，可由 Host Adapter、Bootstrap 或宿主 Plugin manager seam 只读检查：可信 canonical upstream 的正式 release/manifest 是否比本地安装版本更新。发现正式新版时，Agent 用直白中文提醒用户，至少展示：

- 当前安装版本和可用新版本。
- 经验证的 canonical 来源。
- 主要更新内容，以及已知兼容性或迁移提示。
- 用户可以执行的明确更新方式。

检查本身不得自动下载、安装、切换 Git 分支或修改当前项目；只有用户明确授权后，才调用宿主支持的更新流程。若宿主已经提供插件更新机制，优先集成该机制，不重复建设下载器或安装器。

离线、超时、上游不可达或无权限时，不阻断 Product Run，只记录简短的 `UNKNOWN` 和 `last checked`。系统需要缓存和冷却策略，避免每次调用反复骚扰用户；具体采用每 session、每日还是版本窗口检查，等待原型验证，不在本 Roadmap 冻结。

#### 最小安全与隐私边界

- 只请求版本比较所需的最小 release/manifest 元数据；不上传项目内容、Signal、PRD、凭证或遥测。
- canonical origin 使用 allowlist；需要验证 release/tag/manifest 来源，并为 checksum/signature、HTTPS 和可靠版本比较预留能力。具体校验机制必须通过实现与供应链安全验证后才能冻结。
- Planning Learning Loop 产生的 upstream improvement proposal、branch 或 PR 不是可安装 release，不能触发“发现新版”提示。只有经过 canonical 发布流程的正式 release/manifest 才参与比较。
- 未来原型首先适配 Codex Host Adapter；Claude 等其他 Adapter 复用同一个 Core update metadata contract。Host 差异留在 Adapter 层，不污染 Product Graph Core。

该能力依赖本地安装版本可识别、可信 upstream 元数据合同和宿主更新能力，但不要求常驻 daemon。它不属于 Product Graph 的业务 Node、Gate 或 HITL，也不成为任何当前 Wave 的退出条件；与 Planning Learning Loop 的关系只发生在“被采纳的上游改进最终发布为正式版本”之后。

### 11.8 Future Maintenance：Configurable PRD Template Evolution

状态：`FUTURE / INCREMENTAL ROADMAP / 非当前架构冻结项`。

PRD 模板是可配置、可随时升级的 Template Profile，不需要在当前架构规划阶段把最终内容一次性写完或冻结。当前 `templates/prd/general/PRD_TEMPLATE_v0.1.md` 仅作为 Draft/Bootstrap 候选；一期只保留可配置接口、exact 版本记录和一个可用 fallback，不以模板内容是否“最终完美”阻塞 Core 建设。

未来模板演进至少需要覆盖：

- **项目覆盖优先**：项目显式选择或 override 优先于插件携带的通用 default；更细的解析优先级等待原型验证。
- **版本与升级提示**：知道项目 active profile、候选新版本及差异，不静默替换。
- **语义 mapping 兼容校验**：模板字段变化仍能映射 Product Spec、AC、Evals、Review Summary 和 Handoff；不只检查 Markdown 标题是否存在。
- **迁移与回滚**：允许项目明确选择升级、继续 pin 旧版本或回退；失败不会让已有 Run 无法恢复。
- **按真实需求增加 Profile**：只有 frontend、backend-service 或专业领域案例证明 general 不够时才新增，不预建模板大全。
- **Document Experience + Evals**：同时验证人类可读性、信息重点、机械完整性和下游可消费性。
- **历史不可变**：默认模板升级不能覆盖历史 PRD，也不能改变旧 Run 依据 exact 模板版本进行复现的结果。

Trusted Upstream Update Check 只说明插件有新的正式 release；该 release 可以携带模板新版，但“插件更新”不等于“项目 active Template Profile 已迁移”。是否迁移必须由明确选择和兼容/迁移策略决定，不能因为安装新版插件就静默改写项目模板、历史 PRD 或正在运行的 Candidate。

该能力是模板维护与兼容性工作，不新增 Product Graph 业务 Node、Gate 或 HITL，也不改变当前 Wave 的退出条件。

### 11.9 Optional Delight / Parking Lot

- **插件内置彩蛋**：`OPEN / 未定义 / 非当前承诺`。目前只记录“未来可能加入一个彩蛋”的想法；彩蛋内容、触发方式、适用场景和实现时点均未决定。它不绑定任何现有 Wave 或一期验收，不新增 Graph Node、Connector、Gate、权限或实现合同。只有未来形成明确用户价值、不会干扰核心工作且不引入安全或信任风险时，才另行讨论是否进入正式 Roadmap。

## 12. 项目级风险与开放决定

只记录会改变建设顺序或范围的风险：

| 风险 / 开放决定 | 为什么重要 | 当前处理 |
|---|---|---|
| V1.4 已冻结 distribution/eval closeout，但实现仍 pending | 把唯一公开 Skill、allowlist、identity 或 Suite 文档合同误读为已安装/PASS 会制造假证据 | Wave 1 实作 fresh-install Plugin Contract，Wave 4 实作 Product Golden v0.2；其余由真实 Slice 证据校准 |
| Human-in-the-Loop 可能过密 | 多次 Owner/PM/Review 确认可能拖慢 Junior PM | 试点记录真实中断，Wave 6 做全局密度审计；此前不盲删安全必要确认 |
| 通用 PRD 模板可能过重或升级破坏兼容 | 过早冻结模板会拖慢 Core；静默升级又可能改变历史 PRD、旧 Run 或下游 mapping | Wave 1 只实现可配置 seam、exact version 和 fallback；内容、迁移、回滚与兼容验证进入 11.8，不先建模板大全 |
| KMG v0.2 治理过重、权限高风险 | 直接实现完整设计会变成企业知识平台，也可能泄漏跨项目信息 | Wave 5 先瘦身，只在真实共享需求出现后实现最小能力 |
| KMG 输入与 Knowledge Proposal 尚未完成需求反推 | 只保存压缩知识会丢失原文与 provenance；未经需求验证就全量复制又会制造成本、权限和保留风险 | Node Review 17 保持 `DEFERRED / PENDING KNOWLEDGE REQUIREMENTS`；先定义使用场景和产品需求，再决定 raw/derived 输入、提交时机与实现合同 |
| 自进化放大错误经验或泄露项目知识 | 反思如果直接改写 Skill，会把偶然相关性、提示注入或敏感项目内容扩散到后续项目 | 只生成可审查候选；project-specific/generic 分流；高风险升级需人审/对抗审计，并由后续 Run/Eval 验证和支持回滚 |
| 过早授予 Reviewer 正式阻断权 | AI 角色名称不等于真实授权；在外置团队仍最终把关时复制审批会加重流程，并可能制造误阻塞或责任错位 | 当前与一期保持 advisory only；只有无人值守执行、人工把关退出或真实政策要求出现后，才按 11.6 的依赖和 shadow 验证原型 |
| 上游更新提醒被供应链攻击或制造噪音 | 伪造 release、错误版本比较或高频提醒会诱导安装恶意/不兼容版本，也会打断 Product Run | 只读最小元数据、canonical allowlist 和 release/manifest 验证；失败不阻断，频率/cache 与 checksum/signature 等机制先原型再冻结 |
| Eval Ground Truth 不可靠 | 生成 Agent 可能自问自答并制造虚假基准 | Ground Truth 保留 provenance、专业 Owner 和独立 Review；未知不伪装完成 |
| Connector 有外部副作用 | 重试、超时或未知结果可能重复提单、通知或交付 | 先做 seam、幂等/查询/receipt；未知结果不盲重试 |
| Host 结构异构 | Codex、Claude 等 Host 的 Skill/Plugin/Subagent 能力不同 | Core 合同保持 Host-independent；一期只实现并验证 Codex Adapter |
| 架构 Evals 初始阈值缺少真实基线 | 文档阈值可能过严、过松或优化错误目标 | 先作为 pilot 假设，用真实历史和下游反馈校准后再冻结 |

## 13. 当前下一步

Roadmap 获得负责人确认后，立即启动 **Wave 1：本地可运行基础**，而不是继续新增大段架构。

首个建设批次只做五件事：

1. 从 V1.4 提取 Wave 1 最小 Graph/State/Audit/Host/distribution 合同，包括唯一公开 Skill、Atomic Skill Modules、allowlist 与自动安装身份。
2. 对 Bootstrap v0.1 做一次“保留/删除/后置”瘦身，形成可实现的最小 Bootstrap Profile。
3. 建立 Core + Codex Host Adapter + State Controller 的可运行骨架。
4. 接入手动 Signal、本地 snapshot/records、本地 Handoff 和版本化文档目录；不提前实现未定义的 KMG submission contract。
5. 在 fresh installed 最小 runtime 上执行一个恢复案例、Plugin Contract Smoke 和 v0.2 Smoke fixture，取得第一批真实证据：能创建、暂停、恢复、拒绝假完成，唯一公开入口/相对资源/installed identity 成立，并且没有 Connector 也能运行；此前文档检查保持 `DOCUMENT-ONLY / NO PASS`，legacy v0.1 不充当验收基线。

这五项通过后才进入 Wave 2 的真实 Idea → PRD 闭环。任何未通过项都应回到对应实现或最小合同修复，不通过增加架构术语掩盖。

## 14. Roadmap 管理规则

- 同一时刻只声明一个当前 Wave；并行支线必须服务当前或下一个已知 Gate。
- 每个 Wave 开始前记录 exact 输入版本、主要目标、明确不做、依赖与退出条件。
- Wave 结束只能选择：通过、部分通过并显式 carry-forward、返工、重排、拆分或停止。
- 新的大 Unknown 不静默塞进当前 Wave；进入风险/决定记录后再判断当前处理或后置。
- Roadmap 只记录项目级顺序，不复制 Node、Run、Decision、Risk 或 Audit 的详细状态。
- 本 v0.12 交付后冻结；任何后续改变顺序、边界或 Gate 的修改创建新版本并更新 `docs/roadmap/CHANGELOG.md`。
