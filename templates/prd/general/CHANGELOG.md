# Better Product Graph 通用 PRD 模板 Changelog

## v0.3.0 Draft — Invalidated — 2026-08-24

- 状态：`INVALIDATED / NOT_REGISTERED`；未改变 `general@0.2.0 / RELEASED_DEFAULT`、default 或 general fallback。
- 撤回原因：错误地把 ELI5 表达规则与 PRD 模板版本耦合。模板应只管理栏目和产品语义承载；表达规范应作为独立 Document Experience Policy/Profile 版本化。
- `PRD_TEMPLATE_v0.3.md` 现在只保留撤回说明；原实验归档为 `experiments/PRD_TEMPLATE_v0.3_expression-coupled_INVALIDATED.md`。
- `OUTPUT_CONTRACT_v0.3.json` 仅作为未注册历史草案保留，不用于生成或校验新 PRD。
- 替代关系：结构继续使用 `PRD_TEMPLATE_v0.2.md`；表达规则迁移到 `policies/document-experience/PRD_WRITING_GUIDE_v0.1.md` 和 `PRD_WRITING_PROFILE_v0.1.json`。
- Skill / Host Agent 应读取并绑定确切 Template、Policy 和 Profile；不能把写作规范复制进每个模板，也不能只依赖 Agent 记忆。
- 本次撤回不修改、取代或迁移任何既有正式 PRD，也不声称可读性已通过真实用户验证。

## v0.2.0 Released Default — 2026-08-21

- 状态：`RELEASED_DEFAULT`；默认选择为 `general@0.2.0`。
- 模板 SHA-256：`sha256:c276e951bba16ff868f5b2cf7dacb1642adf5eac512fb2a3898f4ad825ad64a4`；Output Contract SHA-256：`sha256:33270d0d8c30bc384e5c6f9f2f9a5e59cacb06b2be27da2f3f5b20eeebfc08a0`。
- 将此前完成审查的 v0.2 Runtime Candidate 正式设为通用默认模板；冻结的 Better-Product-Plan 模板继续作为可显式选择和回滚的 legacy compatibility profile。
- 项目专属模板仍优先；仅在项目明确配置 `GENERAL_ON_UNAVAILABLE` 且属于“缺失 / 不适用”时回退到 `general@0.2.0`，完整性错误继续 fail closed。
- Output Contract 同时支持 `split`、`compact` 与旧 Run 的 `legacy` 兼容读取；新 PRD 应显式使用 `split` 或 `compact`，兼容模式不扩大新模板的推荐结构。
- 模板、Output Contract、项目选择、exact pin、rollback、Candidate metadata、Ready evidence 与 Controller receipt 均按 exact path/version/hash 绑定；首次 Run 会锁定当时模板，不随以后默认升级静默迁移。
- 本节 supersede 下方 v0.2 候选阶段的“默认激活 DEFERRED”结论；其余设计推导保留为历史记录。

## v0.2 — 2026-08-20

- 状态：`DRAFT / RUNTIME CANDIDATE / IN REVIEW`；默认激活 `NOT_RUN / DEFERRED`
- 文件：`PRD_TEMPLATE_v0.2.md`
- 上一版本：`PRD_TEMPLATE_v0.1.md`
- Supersedes：`PENDING_REVIEW`
- 变更：创建独立的 v0.2 工作版本；更新模板版本元数据与草案说明，并开始逐项语义修订。
- 文件命名：正式 PRD 的 Markdown 文件名仅去除最后一个 `.md` 扩展名后，必须与唯一 H1 标题逐字符完全一致；保留既有 `<PRD-ID>_<short-title>_v<version>_<YYYY-MM-DD>` 文件名主体合同。assemble 与 archive 已双层校验，并拒绝模板占位、裸 `TBD` 和可靠可判定的空 Markdown 表。
- Metadata 边界：删除正文 `0. 文档信息与来源`；系统身份、上游追溯和生命周期 refs 改由 frontmatter、sidecar 或 manifest 维护，适用范围、发布目标和当前行动只保留在各自的自然正文位置。
- 变更记录：`阅读摘要` 只显示当前版本 delta，完整 append-only 历史继续以 `附录 C：文档变更日志` 为唯一正文来源。
- 问题与目标：第 1 节调整为“问题、目标与价值”，兼容用户、商业、内部运营 / 团队效率、风险 / 合规及平台 / 技术演进等多类驱动；定性目标必填，定量目标条件式填写且禁止编造数字。
- 价值与时机：用户价值、商业价值、团队 / 内部组织价值改为三项必查视角，允许基于具体理由标记不适用；将“值得做”的价值与“为什么现在做”的时机、延迟成本和确切依据分开。
- 目标对象规模与单位价值：阅读摘要将“主要对象与场景”升级为“主要对象、规模与场景”的一句话结论；第 1.1 节新增结构化分析，支持用户、客户、商户、员工、团队、业务实体、系统、设备、交易及风险暴露单位等对象，记录当前受影响规模、本期覆盖规模、统计口径、来源和状态，并分别分析单个对象获得的价值及其对业务 / 组织的单位价值。禁止编造人数、TAM、覆盖率或单位价值；规模与单位价值只作为优先级、第 1.2 节目标和第 1.3 节三层价值的输入，证据不足或口径不一致时不得机械相乘。未来 Validator 只在适用时检查字段完整性、口径、来源和状态，不强制虚假量化。
- 本期范围：第 2.1 节取消“可后置”，仅接受带 SCOPE-ID 的本期确定交付项；不交付内容进入第 2.2 节，后续方向进入第 2.5 节或上游 Roadmap。第 3.2 节模块以 MOD-ID 标识，本期角色限定为“本期交付 / 复用既有 / 外部依赖”，不把未来模块伪装为本期模块。
- 最小追溯：新增 GOAL、SCOPE、MOD、DEP、METRIC、RISK、ASM、UNK、OPEN、LEGAL 等稳定 ID，保留既有 RULE-ID 与 AC-ID；第 5.1 节新增一张最小验收追溯表连接目标 / 范围、模块 / 规则、AC 与 Eval / Test ref。第 8 节的数据事件和分析通过 METRIC-ID 连接第 1.2.2 节，模块依赖通过 DEP-ID 连接第 2.4 节，附录 D 只引用正文 ID / ref。
- 证据与行动边界：第 1.4 节仅承载问题 / 目标 / 价值的 Evidence boundary；第 11.2 节仅登记仍影响本期交付的 ASM / UNK，第 11.3 节仅登记需 Owner / 有效来源在时点前行动的 OPEN，并引用来源 ID，避免复制同一结论。
- 定量目标唯一来源：删除原 `8.1 成功指标`，将第 8 节更名为“数据上报与分析影响”，原 `8.2`、`8.3` 重编号为 `8.1`、`8.2`。指标、基线、目标、观察窗口、数据来源和状态统一在 `1.2.2 定量目标（条件式）` 维护；有依据且可验证的假设目标标记为“假设待验证”，缺有权事实的数字标记“待确认”。第 8 节只引用 METRIC-ID 并定义上报、校验、分析与消费方式，测量设计发现目标问题时必须回到第 1.2.2 节修订。
- 演进脉络：新增条件式 `2.5 后续规划与演进脉络`，只呈现与当前切片直接相关的已确认、条件触发或尚未承诺方向及必要兼容边界；不复制 Roadmap、不扩大本期承诺，也不允许以未来可能性推动推测性过度设计。
- 方案可视化：第 3.2 节在多模块或模块边界、关系、依赖不直观时建议增加模块结构图，并保留模块表作为可检索、可 diff 的文字补充；第 3.3 节更名为“关键流程与交互视图”，按问题选择流程图、时序图、数据流图、用例图、状态图或项目支持的其他图型。非平凡行为至少提供一张合适的可视化图，可用多图回答不同问题但不得重复信息；每张图需标明标题、目的和范围，保留可编辑 / 可复现来源和文字摘要，并与对应详细规则一致。仅纯简单、少步骤、单一主要参与者、严格串行且无复杂性信号的行为可只用编号文字。
- 方案与功能结构：第 3、4 节新增条件式二选一结构。多模块、跨模块关系 / 共享规则、多流程或全局视角与施工细节分工明确时使用标准拆分模式；仅一个可独立交付、高内聚模块 / 切片且一个主导场景、拆分主要造成重复时，可合并为 `3. 方案与功能规则` 并删除独立第 4 节。合并不以字数为依据，且必须保留两节全部适用语义；可视化与模块依赖规则在两种模式下同样有效。新增独立、exact-hash 绑定的 output contract，Validator 接受 `split | compact` 任一合法结构、禁止两组标题混用，并要求两种结构映射相同核心语义。
- 模块级可视化：新增条件式 `4.x.2 模块级可视化`。当模块内部存在多组件、复杂状态、交互时序、数据流、关键分支或跨边界交接时，按问题选择模块结构 / 组件关系、局部流程、时序、数据流、状态、用例或其他项目支持的图；简单模块可删除整节。模块图只解释内部机制和边界，第 3 节已覆盖时引用图标题 / Exact ref 并补充局部差异，不重复绘制；每张图保留标题、目的、范围、可编辑 / 可复现来源及文字摘要 / 替代说明，并与模块规则、状态权限、依赖、异常恢复和 AC 一致。紧凑合并模式同样保留该条件式语义；未来 Validator 检查适用性、一致性和引用完整性，不机械要求每模块有图。
- 模块依赖：在模块骨架中保留条件式依赖并顺延为 `4.x.5 依赖关系`，同时覆盖本模块的上游依赖和对下游消费者的反向依赖；第 2.4 节以 DEP-ID 作为全局 / 跨 PRD / 共享合同总览，模块级内容必须通过 DEP-ID 引用已有全局依赖，纯模块内局部依赖可标明无全局 ID。无模块专属依赖时删除整个小节和空表，分支与异常、验收标准相应顺延为 `4.x.6`、`4.x.7`。
- Evals 与实验：第 5.2 节改为“Product Evals 适用性（必查）与准备状态（适用时）”，每份 PRD 必须判断适用性，普通 AC 足够时准备状态和 Eval Pack 统一写不适用理由。新增 `5.3 实验型交付合同`，仅 `delivery intent = EXPERIMENT` 时保留，通过 ASM / UNK、SCOPE、METRIC、护栏 / 回滚与 Decision ref 定义受控变化、观测窗口和结果返回；原测试设计参考顺延为第 5.4 节。明确 Product Evals 与产品实验不同且可同时适用。
- 交付覆盖索引：将附录 D 从扁平“条件项检查摘要”重构为“通用交付 Check / 项目专属 Check / 法律、合规与权利 Check”三类索引；实质要求只写在自然正文位置，索引统一记录结论、正文 / 证据、Owner / 有效来源及未完成影响 / 动作，`待确认` 不得缺少责任与影响，`已考虑` 不再视为完成或批准。
- 项目与专业边界：项目专属 Check 只能从已配置 Profile / Knowledge 和已确认项目事实生成，不引入公司、券商、金融或教育专属固定项。第 10.1 节改为以 LEGAL-ID 承载司法辖区 / 对象、严格状态、实质要求、专业 Owner / 有效 ref 与交付动作的结构化正文；附录 D.3 只保留分类覆盖并引用 LEGAL-ID / 外部专业 ref。法律合规结论限定为“不涉及 / 可能涉及 / 待专业确认 / 已取得专业结论（附 ref）”，Agent 与产品 Owner 无权自行批准。
- 一致性清理：保留“用户结果 / 用户如何 / 用户故事 / 用户操作 / 老用户”等自然表达，不做机械泛化；英文不适用缩写统一改为 `不适用｜理由：...`，统一未决格式与 Owner / 有效来源写法，区分“待确认”和“待验证”，并明确条件式内容默认规则与局部删除整节规则的优先级。阅读摘要的状态、版本变化、下一步分别标注为优先由 metadata、附录 C、当前 Run 派生；renderer 仍未实现。
- Stage 1 promotion：顶层模板与 `OUTPUT_CONTRACT_v0.2.json` 成为人类源，通过 `scripts/promote_prd_template.py` exact-byte 同步到 runtime；build 校验 parity / hash，并实际执行 Template Registry、output-contract schema、Stage 1 default / fallback / candidate 指针和 Candidate status 校验，同时把人类源纳入 fingerprint。`general@0.2.0-draft` 已注册为显式 Runtime Candidate，模板 hash 为 `sha256:c276e951bba16ff868f5b2cf7dacb1642adf5eac512fb2a3898f4ad825ad64a4`，output-contract hash 为 `sha256:937076b04eeaf8e48efa39d900c7d41aabbcfb352d72c9791b1b3aaca5062efa`。
- 项目模板与回退：支持 project-relative、trusted-area、拒绝 symlink、显式版本与 template / contract exact hash 的项目模板。缺失 / 暂不可用或显式不适用只有配置 `GENERAL_ON_UNAVAILABLE` 时回退并写 requested / selected / reason 与 exact fallback lock；路径、hash、schema、冲突等完整性错误及通用模板错误均 fail closed。
- 生命周期绑定：Template source kind、selected id/version/path/hash、output-contract path/version/hash、selection source、fallback reason 与 requested project profile 已贯穿 Candidate metadata、归档 sidecar、Ready evidence、Controller receipt 复算与 READY exact ref。首次 Run 创建会锁定当时有效默认；显式迁移与 rollback 继续按 exact hash。
- Golden 与默认边界：checked-in 本地 Golden 覆盖简单 compact、多模块 split 与 EXPERIMENT / 高合规 split，并走真实 assemble/archive 机械路径；证据类型仅为 `LOCAL_HOST_AGENT_AUTHORED_FIXTURE`。真实 authenticated installed Host Agent 生成仍为 `NOT_RUN`，Stage 2 default activation 未执行，Stage 1 默认继续保持 upstream compatibility profile，避免未 pin 老项目静默迁移。
- Promotion 复审加固：当前 Stage 2 激活入口无条件 fail closed，伪造全 PASS JSON 也只能得到 `DEFERRED / NOT_RUN`；project missing 不再掩盖另一侧 hash / schema 篡改；built-in 与 fallback lock 完整绑定 template / contract relative path、version 与 hash，严格限制 selection source 和两种 fallback reason。Profile status 明确为治理标签而非迁移身份。
- 配置与事务：`.better-product-graph`、配置 / lock 路径统一拒绝 symlink / escape；Template Profile read-modify-write 使用项目级 exclusive lock，无配置的 read-only resolve 不创建控制目录或 lock，注册在写前完成全部校验。首次 `create_run` 在同一 lock 内持有新 default pin：preflight / raw-write 或其他 durable journal 前失败时按 exact config bytes 撤销；精确 `run-created` journal 已绑定完整 pin 后保留 pin，由 `recover_transactions` 恢复，即使 registry default 随后变化也不迁移。仅有无关 journal 文件不能保留 pin。
- Fallback requested identity：fallback lock 新增 canonical requested-active SHA-256，并在每次 resolve 前严格验证 active kind、id/version、template path/hash、contract path/version/hash、policy、applicable 与未知字段。Reason 与 active 语义一一对应：`applicable=false` 仅允许 `PROJECT_TEMPLATE_NOT_APPLICABLE`，`applicable=true` 仅允许 `PROJECT_TEMPLATE_UNAVAILABLE`，枚举互换也 fail closed。锁定后任何 active 篡改均 fail closed；文件恢复不自动切回，显式重新注册才清除 lock。
- Markdown 与条件章节：H1 / H2 / 空表扫描忽略反引号和波浪号 fenced code；出现的条件章节必须有实质内容，裸“无 / 不适用”、空 fence 和空 `OMIT_WHEN_EMPTY` 均拒绝，非空 Mermaid / JSON / code fence 可作为实质内容。Structured changelog 新增 requested profile id/version。
- 实施证据：聚焦模板 / PRD / Ready / State 为 `86 / 86 PASS`，相关 build / package / fresh-install / recovery 为 `48 / 48 PASS`；分支全量 `271` 项中 `267 PASS / 4 FAIL`，干净 HEAD `3e2763a` 有同名同错误的 `4 FAIL`，本轮未越界修复这些基线问题。Promotion check、build、package、隔离 fresh install / uninstall / rollback 为 PASS；authenticated Host Agent 与 Product Golden 仍为 `NOT_RUN`。
- 目的：在不覆盖 v0.1 的前提下，共同 review BPG 通用模板的核心结构、条件章节、重复信息和项目模板 fallback 语义。

## v0.1 — 2026-08-19

- 状态：`FROZEN DRAFT / BASELINE`
- 文件：`PRD_TEMPLATE_v0.1.md`
- 上一版本：无
- 变更：从 Better-Product-Plan 模板派生第一版领域无关的 BPG 通用 PRD 模板草案。
