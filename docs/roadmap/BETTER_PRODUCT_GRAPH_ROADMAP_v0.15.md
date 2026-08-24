# Better Product Graph 项目 Roadmap v0.15

状态：RELEASED CURRENT-STATE ROADMAP  
日期：2026-08-24  
上一版本：`BETTER_PRODUCT_GRAPH_ROADMAP_v0.14.md`（冻结，不修改）  
架构基线：`docs/architecture/PRD_GRAPH_v1.4.md`

> v0.15 只重定义 Bootstrap 的产品定位和下一步验证方式，不扩张 Product Graph，也不把候选 PRD、Review 或尚未执行的实验表述为已交付能力。

## 1. 一句话结论

Bootstrap 的唯一主线任务是：**快速建立足以处理当前 Signal 的项目理解，减少用户搬运上下文的成本。**

它不是项目初始化向导、配置中心、权限系统、知识平台、迁移工具、教学系统或 Operational Readiness Gate。Agent 应先基于项目证据形成判断和建议，再由产品经理审核；只有缺口会实质改变当前判断时才提问。

当前先运行一个单项目、单 Signal、只读、可回滚的最小实验。实验未执行前，不进入完整实现，不宣称 Bootstrap 已经 Ready 或可发布。

后续顺序调整为：

```text
Developer Alpha：保持现有 Product Loop 可用
→ Bootstrap Context MVU：执行 1 次 Agent-first 最小实验
→ 根据 typed experiment result 作新的 Product Decision
→ 若 CONTINUE，再规划最小正式实现与多项目验证
→ 按独立需求建设 Settings / Connector / Knowledge / Permissions
```

研发 Graph 和测试 Graph 仍是下游可插拔系统，不属于 Better Product Graph。

## 2. 当前真实状态

### 2.1 已经成立

| 能力 | 当前结论 | 证据边界 |
|---|---|---|
| Product Graph Core | 已实现核心路径 | 支持 Signal、Problem、Decision、Plan、PRD、Review、状态、版本、审计和恢复 |
| 自然语言意图责任 | 已确认产品原则 | Host 应把普通用户表达映射到内部意图，不要求用户记忆 `new`、`capture` 或 `bootstrap` |
| Bootstrap 问题定义 | 已由 Owner 确认 | 目标是减少上下文搬运并提高当前 Signal 的项目相关性 |
| Bootstrap 交互责任 | 已由 Owner 确认 | Agent 先调查、判断、建议；产品经理审核纠偏；提问只作高影响缺口兜底 |
| Bootstrap 最小实验方向 | 已由 Owner 选择 | 当前 delivery intent 为 `EXPERIMENT`，范围为 1 个真实项目、1 条新 Signal、1 个干净会话 |

### 2.2 尚未成立

- Bootstrap 最小实验尚未执行，所有实验指标仍为 `NOT_RUN`。
- 尚无证据证明 Agent 在不同项目中都能选对来源、识别过期材料或形成足够准确的判断。
- 尚无证据证明产品经理审核初判的成本稳定低于重新讲述项目。
- 尚未决定正式产品形态是持久 Context Pack、动态检索、轻量索引还是它们的组合。
- 尚未进入默认启用、跨 Signal 持久化、多项目扩量或外部用户发布。

这些边界不得被 Candidate、schema PASS、Review 零 Finding 或本地文件存在所覆盖。

### 2.3 本次规划证据

- Run：`run-f9b68b8e69c7`。
- Owner Decision：`.better-product-graph/decisions/decision-f9b68b8e69c7/DECISION_v1.json`，`sha256:25ae4d2a33ed2e9c2aeb100f3de4ae22cdaf0a2930ef090894c516ca8288f6a2`。
- Product Plan：`.better-product-graph/runs/run-f9b68b8e69c7/artifacts/PRODUCT_PLAN_BOOTSTRAP_CONTEXT_MVU_v0.1.md`，`sha256:34fdfcecdadd72d97c6aa7da26d6c0f4be8b6c9f3714220c266f052f4fa16618`。
- PRD Candidate：`artifacts/prds/archived/BPG-PRD-BOOTSTRAP-CONTEXT-MVU-001_bootstrap-context-mvu_v0.1_2026-08-24/BPG-PRD-BOOTSTRAP-CONTEXT-MVU-001_bootstrap-context-mvu_v0.1_2026-08-24.md`，`sha256:fcd1a6d43b1c2f5f388cbb70de67fb4a44547921550630ef92fad00996bc02c3`。
- 当前边界：Review 已 finalize；PRD Ready receipt、Release 和实验结果均不存在，不能写成已就绪或已验证。

## 3. Bootstrap 产品定义

### 3.1 核心用户结果

产品经理在已有项目中用自然语言开始 BPG 工作并给出一条新 Signal 后，无需先填写表单、配置系统、记忆内部命令或粘贴大段背景，就能先看到 Agent 基于可访问项目证据形成的：

- 项目目的、当前目标与约束判断；
- 当前 Signal 与项目的关系；
- 支撑来源；
- 推断、未知、冲突和时效风险；
- Agent 的产品建议。

产品经理的主要动作是接受、轻微纠偏、重大纠偏或否决。审核后的理解用于当前 Signal；用户跳过 Bootstrap 时，原 Product Loop 仍可继续。

### 3.2 主线流程

```text
用户用自然语言给出项目与 Signal
→ Host 识别“需要项目理解”的意图
→ 用户可运行或跳过上下文加速
→ Agent 主动选择并读取当前已授权的项目证据
→ Agent 先给出项目理解、Signal 判断、依据、未知与建议
→ 产品经理审核纠偏
→ 只有高影响缺口才提出一个针对性问题，并说明问题会改变什么判断
→ 审核后的理解进入当前 Signal Product Loop
```

Bootstrap 的完成条件不是字段、文件或设置齐全，而是 Agent 是否已经具备在当前项目语境下处理当前 Signal 的可观察能力。

### 3.3 不可牺牲边界

- **Agent-first**：不得以连续提问、固定问卷或“请先补充项目背景”作为默认首屏。
- **Natural-language first**：用户不需要知道内部稳定意图名。
- **Optional**：运行、跳过、拒答或实验失败都不得阻断原 Product Loop。
- **Traceable**：重要事实绑定来源；推断、未知、冲突和过期风险必须可见。
- **Question as fallback**：只有缺口会改变当前判断时才提问，一次只问一个最高价值问题。
- **Scope firewall**：任何额外配置或治理能力都不得成为当前 Bootstrap 的前置依赖。
- **Local and read-only experiment**：当前实验不远端发送、不修改项目内容、不产生发布承诺。

安全、权限和秘密文件处理仍是 Host 的横向底线，但不能被包装成用户必须完成的 Bootstrap 主线步骤。

## 4. 当前最小实验

### 4.1 实验输入

- 产品 Owner：`eli`；
- 1 个真实本地项目；
- 1 条此前未处理的新 Signal；
- 1 个不携带历史聊天背景的干净会话；
- 固定项目输入与完整交互记录。

### 4.2 受控变化

只在原 Product Loop 前增加一个可跳过的 Agent-first 上下文加速：自然语言进入、Agent 主动理解、产品经理审核、审核后 handoff。其他产品规则保持不变。

### 4.3 观察指标

| Metric | 观察内容 | 当前成功边界 |
|---|---|---|
| METRIC-001 | 首次实质判断前用户复制的项目背景字符数 | `0` |
| METRIC-002 | 首次 Agent 判断前的通用背景问题数 | `0` |
| METRIC-003 | Owner 对项目目的、当前目标、非目标和 Signal 关系的纠偏等级 | 不得为重大纠偏或否决 |
| METRIC-004 | 重要判断可追溯或已标记不确定性的比例 | `100%` |
| METRIC-005 | 跳过后 Product Loop 是否仍可继续 | 是 |

### 4.4 结果映射

- `CONTINUE`：背景搬运和通用前置问题均为零，核心语境无重大纠偏，重要判断可追溯，跳过路径可继续。
- `ADJUST`：未触发伤害护栏，但来源选择、表达、审核或提问门槛存在可修正差距。
- `STOP`：触发伤害护栏，或核心项目语境出现重大误判/否决。
- `INCONCLUSIVE`：干净会话、固定输入、完整记录或 Owner 审核任一缺失。

实验结果必须以 typed、immutable、exact-ref artifact 返回新的 Product Decision；不得由 Agent 直接把一次结果提升为默认产品承诺。

## 5. Settings 与 Future 能力

以下事项有潜在价值，但全部从 Bootstrap 主线移除，只在出现独立需求和证据后通过单独入口或新 Signal 决策：

| 能力 | Roadmap disposition | 何时重审 |
|---|---|---|
| 自定义需求模板 | `Future settings` | 用户需要个性化输出，且不影响项目理解主线 |
| Connector | `Future settings / Platform` | 本地可访问材料被证明不足，并出现具体远端来源消费者 |
| Knowledge Graph | `Future phase` | 轻量来源选择无法应对项目规模、冲突或刷新问题 |
| 跨 Signal 持久化与刷新 | `Future phase` | 当前实验成功并出现第二条代表性 Signal |
| 多用户权限 | `Future phase` | 进入真实协作与共享项目场景前 |
| 迁移与教学 | `Future phase` | 形成独立用户需求、入口和可观察价值 |
| 身份、Git、运行门禁、激活 | `Stop / out of scope` | 只有独立问题证据成立时另立 Signal；不得重新并入 Bootstrap |

Settings 入口可以帮助用户管理模板、来源或协作规则，但 Settings 是否配置完整与 Bootstrap 是否已经足以理解当前 Signal 是两个不同结论。

## 6. 实验后的决策顺序

只有 typed experiment result 返回后，才作下一次产品决策：

- `CONTINUE`：规划最小正式实现，并新增第二个代表性项目验证；不自动扩张到 Settings 或平台能力。
- `ADJUST`：只修正已观察到的行为差距，再运行同范围实验。
- `STOP`：结束当前方向或重新定义问题，不保留“Bootstrap 必须存在”的预设。
- `INCONCLUSIVE`：补足实验输入，不声明成功或失败。

## 7. R2：多项目真实试点

Bootstrap Context MVU 获得 `CONTINUE` 后，才进入多项目试点。重点验证：

- 不同成熟度项目中的来源选择与时效判断；
- 产品经理纠偏成本是否稳定低于重述背景；
- 第二条 Signal 是否需要持久化 Context Pack；
- 自然语言意图在不同表达下是否稳定；
- 跳过、拒答、材料不足和来源冲突是否仍能保持 Product Loop 连续。

一次成功不能证明跨项目普适性。

## 8. R3：Evals Generator 与测试设计合同

产品 Graph 可以定义“怎样证明需求实现正确”，但不冒充测试团队执行了测试。

- `Eval Strategy` 判断普通 AC 是否足够，以及 Evals 为 `NOT_NEEDED / RECOMMENDED / REQUIRED`。
- `Eval Pack` 定义目标行为、Ground Truth、输入、预期、评分、边界与不可接受结果。
- `Test Design Contract` 连接功能场景、AC、边界/异常、回归建议与下游 exact refs。
- `NOT_RUN` 必须继续与 `PASS` 分开。

实验型交付必须能在不伪造 PRD Ready、Release 或独立 Eval authority 的前提下返回实验结果；正式 `COMMIT` 交付的 Required Evals Gate 不得因此削弱。

## 9. R4—R6：Knowledge、Connectors 与治理

- Knowledge Maintenance Graph 继续作为独立 Graph；BPG 只读取 exact 发布快照并提交候选更新。
- Connector 只有出现真实消费者、认证方式和失败恢复要求时才进入实现。
- 规划学习先形成可审计、可拒绝、可回滚的提案，禁止静默自改。
- Reviewer 维持 `ADVISORY_ONLY`；多个 Agent 一致不自动提高事实置信度或形成批准。
- 跨 Host 多 Agent、无人值守治理和远端服务都不进入当前 Bootstrap 实验。

## 10. Developer Alpha 反馈与升级节奏

公开反馈继续分为 Bug、产品反馈和安装问题。以下问题进入阻塞级修复判断：

- 自然语言无法进入已表达的产品意图；
- Run 状态损坏、不可恢复或陷入无合法下一步；
- 错误 Ready、Release、权限或证据伪造；
- `EXPERIMENT` 被正式 Release Gate 永久阻断，或绕过 Gate 后被伪装成 Ready；
- Bootstrap 再次要求无关设置或连续背景问答；
- 无法产出 exact、typed experiment result 返回 Product Decision。

低等级文案和非阻塞一致性问题记录在 Issue/Release Notes，不自动触发热修版本。

## 11. 永久边界

- Better Product Graph 是完整产线中的产品部分，不包含研发 Graph 或测试 Graph。
- Agent 负责产品语义；程序负责状态、权限、完整性、版本和确定性迁移。
- 文档存在、Exit 0、Schema PASS、Review 零 Finding 或多个 Agent 一致，都不自动等于产品完成。
- 不保存模型隐藏 Chain-of-Thought；只保存可审计的 Evidence、理由、假设、未知、建议、分歧、Decision 和 change history。
- 本地 Core 在 Connector、共享知识服务和下游 Graph 缺席时仍可运行。
- Bootstrap 是否有价值必须通过减少上下文搬运和提高当前 Signal 判断质量来证明，不以配置数量、扫描文件数或完成速度替代。

## 12. 下次 Roadmap 更新条件

只有以下事项之一形成正式产品变化时才创建 v0.16：

- Bootstrap 最小实验返回 typed result 并触发新的 Product Decision；
- 第二个代表性项目改变 Context MVU 的范围或实现形态；
- Settings、Connector、Knowledge 或多用户能力形成独立消费者合同；
- Developer Alpha 的真实反馈改变 Product Loop、HITL 或 Reviewer 权限；
- 公开安装/发行形态发生实质变化。

普通实现进度和单个测试修复记录在 Git、Issue 或 Release Notes，不为每一处变化创建 Roadmap 版本。
