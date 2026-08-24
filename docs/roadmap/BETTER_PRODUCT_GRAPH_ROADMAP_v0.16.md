# Better Product Graph 项目 Roadmap v0.16

状态：RELEASED CURRENT-STATE ROADMAP
日期：2026-08-24
上一版本：`BETTER_PRODUCT_GRAPH_ROADMAP_v0.15.md`（冻结，不修改）
架构基线：`docs/architecture/PRD_GRAPH_v1.4.md`

> v0.16 修正 v0.15 对 Bootstrap PRD 生命周期的过期描述，并冻结下一版 PRD 的本地化命名合同。它不把“PRD 已 Ready / Released”误写成“Bootstrap 功能已实现或实验已通过”。

## 1. 一句话结论

Better Product Graph 已经完成 Bootstrap Context MVU 的产品规划、PRD Review、PRD Ready、不可变本地 Release 与 Handoff；但 Bootstrap 真实功能和最小实验仍是 `NOT_RUN`。

当前先发布唯一身份的插件 `0.2.6`，收敛文档台账和 PRD 命名体验；下一步仍是用干净 Host 会话运行一次真实 Bootstrap 实验，而不是继续扩写规划或宣称功能已经成立。

## 2. 当前真实状态

### 2.1 已经成立

| 范围 | 当前结论 | 证据边界 |
|---|---|---|
| Product Graph Core | 核心 Product Loop 可运行 | Signal、Problem、Decision、Plan、PRD、Review、Ready、Release、Handoff、恢复均已有本地运行证据 |
| Bootstrap 产品定义 | 已形成正式 PRD | `BPG-PRD-BOOTSTRAP-CONTEXT-MVU-001` v0.1 |
| Bootstrap PRD 生命周期 | 已完成 | Run `run-f9b68b8e69c7` 最终 `COMPLETED`；同一 Ready attempt 签发四张 Controller receipts，随后本地 Release 与 Handoff |
| Bootstrap Evals 设计 | 已绑定但未执行 | `applicability=REQUIRED`、`fulfillment=REVIEWED`、`execution_status=NOT_RUN` |
| 自然语言意图责任 | 已确认产品原则 | Host 应把用户自然语言映射到内部意图，不要求用户记忆 `new`、`capture` 或 `bootstrap` |
| Bootstrap 交互责任 | 已确认产品原则 | Agent 先调查、判断、给建议；PM 审核纠偏；只有会改变判断的缺口才提问 |
| PRD 本地化命名 | 本版冻结新合同 | 新 PRD 默认跟随用户工作语言，无法判断时回退中文；目录、Markdown 文件名和 H1 必须完全一致 |

### 2.2 尚未成立

- Bootstrap 功能尚未因 PRD Release 自动成为已实现能力。
- Bootstrap 最小实验尚未执行，所有真实用户结果指标仍为 `NOT_RUN`。
- `tests_executed`、`engineering_implemented` 和 `external_approval` 均未被 Ready assertion 声称。
- 尚无证据证明 Agent 在不同项目中都能选对来源、识别过期材料或减少产品经理的背景搬运。
- 尚未进入默认启用、跨 Signal 持久化、多项目扩量或外部用户发布。
- 依赖感知 Problem Learning 目前只有 Released PRD / Prompt-only Pilot 规划，不等于安装版行为已经实现或验证。

### 2.3 v0.15 的状态修正

v0.15 在生成时写道“PRD Ready receipt、Release 和实验结果均不存在”。之后同一 Run 经运行时修复完成了 Ready、Release 和本地 Handoff，因此该句已经过期。

本版只修正事实层级：

```text
PRD Candidate / Review
        ↓ 已完成
PRD Ready / 本地 Release / 本地 Handoff
        ↓ 不等于
Bootstrap 工程实现 / 真实实验 / 外部批准
        ↓ 仍为
NOT_RUN / NOT_CLAIMED
```

历史 v0.15 保持原字节，不原位覆盖。

## 3. Bootstrap Context MVU

### 3.1 用户结果

产品经理用自然语言给出一个项目和 Signal 后，不必先填写问卷、记忆内部命令或粘贴大段背景，就先看到 Agent 基于已授权项目证据形成的：

- 项目目的、当前目标与约束判断；
- 当前 Signal 与项目的关系；
- 依据、推断、未知、冲突与时效风险；
- Agent 的产品建议。

产品经理负责审核和纠偏，而不是替 Agent 完成背景调查。跳过 Bootstrap 时，原 Product Loop 仍可继续。

### 3.2 最小实验

实验保持单项目、单 Signal、干净会话、只读、可回滚：

1. 用户用自然语言提出真实 Signal。
2. Host 自行识别是否需要项目理解，不要求用户输入内部命令。
3. Agent 先调查可访问证据并输出初判。
4. PM 只做接受、轻微纠偏、重大纠偏或否决。
5. 只有一个缺口会实质改变当前行动时，Agent 才问一个最高价值问题。
6. 记录 typed experiment result：`CONTINUE / ADJUST / STOP / INCONCLUSIVE`。

### 3.3 观察指标

| Metric | 成功边界 | 当前状态 |
|---|---|---|
| 首次实质判断前用户复制的项目背景字符数 | `0` | `NOT_RUN` |
| 首次 Agent 判断前的通用背景问题数 | `0` | `NOT_RUN` |
| Owner 对核心项目语境的纠偏 | 不得为重大纠偏或否决 | `NOT_RUN` |
| 重要判断可追溯或明确标记不确定性 | `100%` | `NOT_RUN` |
| 跳过后 Product Loop 可继续 | 是 | `NOT_RUN` |

实验结果必须作为 exact、typed、immutable artifact 回到新的 Product Decision；不得由 Agent 把一次结果直接升级成长期产品承诺。

## 4. PRD 本地化命名合同

### 4.1 语言选择顺序

新生成或新优化版本按以下顺序选择 `metadata.document_language`：

1. 用户明确指定的语言；
2. 当前交互中用户正在使用的语言；
3. 无法判断时回退 `zh-CN`。

`metadata.short_title` 必须是该语言中的简短人类标题，不再默认生成隐藏英文 slug。稳定 PRD ID、版本号与日期继续保持机器可读。

### 4.2 唯一可见身份

每个新 PRD 版本只有一个可见 stem：

```text
<prd_id>_<本地化短标题>_<version>_<YYYY-MM-DD>
```

例如：

```text
BPG-PRD-BOOTSTRAP-001_项目上下文快速理解_v0.1_2026-08-24/
└── BPG-PRD-BOOTSTRAP-001_项目上下文快速理解_v0.1_2026-08-24.md
```

Markdown 的唯一 H1 必须也是：

```text
# BPG-PRD-BOOTSTRAP-001_项目上下文快速理解_v0.1_2026-08-24
```

如需派生 DOCX/PDF，也沿用同一 stem。程序拒绝路径分隔符、控制字符、非法语言标签、过长文件名及目录/文件/H1 不一致。

### 4.3 历史文件边界

- 不重命名已经 archived 或 released 的历史 PRD。
- 标题或命名发生变化时，创建下一个 immutable Candidate version。
- 本合同从 `0.2.6` 生成的新 Candidate 起生效。
- 历史英文 slug 只作为已有版本身份保留，不再作为新文档默认值。

## 5. 0.2.6 发行收敛

### 5.1 为什么必须使用新版本

开发过程中曾出现两个都标记为 `0.2.5`、但 commit 与 artifact hash 不同的构建：公开 Developer Alpha lineage 与本地 Runtime 修复 lineage。继续复用 `0.2.5` 会让安装缓存、升级判断和复现证据失去唯一性。

因此：

- 后续构建、安装与同步统一使用 `0.2.6`；
- 不覆盖或伪装任一历史 `0.2.5` artifact；
- `0.2.6` manifest 必须绑定 exact clean commit、Roadmap v0.16 与唯一 artifact hash；
- 本轮完成前不发布新的 GitHub Release，除非另行授权。

### 5.2 0.2.6 最小交付

- 保留 0.2.5 Runtime 修复：Bug Handoff、公开 Experiment 合同、Required Evals repair、Ready retry/recovery。
- 增加本地化 PRD title/filename contract。
- 修正文档状态台账并纳入 Bootstrap Released PRD。
- 保持研发 Graph、测试 Graph、Knowledge Graph、Connector 和 Bootstrap 正式实现不扩张。

## 6. 后续 Roadmap

### R1：真实 Bootstrap 实验

用安装版、干净 Host 会话和固定输入执行一次真实试验。只有观察到的交互、来源和 Owner 纠偏可作为结果，文档/Schema/Ready/Release 不代替产品行为证据。

### R2：多项目试点

只有 R1 返回 `CONTINUE` 后，才验证第二个代表性项目、第二条 Signal、来源时效与是否需要跨 Signal Context 持久化。

### R3：Evals Generator 与测试设计合同

BPG 定义目标行为、Ground Truth、输入、预期、评分、边界和不可接受结果；Test Graph 决定正式测试用例、代码、runner 和 verdict。`NOT_RUN` 与 `PASS` 永久分开。

### R4：Knowledge Maintenance Graph

先定义 raw source corpus 与 derived knowledge 的消费需求，再反推 BPG 应提交哪些原始资料、压缩信息、Decision 与 Roadmap 记录；BPG 不直接发布 canonical knowledge。

### R5：Connectors 与共享

只有出现真实消费者、认证方式和失败恢复要求时，才实现飞书项目、Issue Collector、Development/Test Graph Handoff 或共享服务。

### R6：规划学习与多 Agent

规划结束后可形成项目知识、项目规划经验和通用插件改进提案，但不得静默自改或未经授权向上游提交。对抗审查、可并行 Review 与旁路研究优先使用受控 sub-agent；跨 Host 多 Agent 协作等待真实需求。

## 7. 永久边界

- Better Product Graph 是完整产线中的产品部分，不包含研发 Graph 或测试 Graph。
- Agent 负责产品语义；确定性程序负责状态、权限、完整性、版本和迁移。
- 文档存在、Exit 0、Schema PASS、Review 零 Finding 或多个 Agent 一致，都不自动等于产品完成。
- Reviewer 保持 `ADVISORY_ONLY`；外置团队继续承担最终汇总审批。
- 不保存模型隐藏 Chain-of-Thought；只保存可审计的 Evidence、结构化理由、假设、未知、建议、分歧、Decision 和 change history。
- 本地 Core 在 Connector、共享知识服务和下游 Graph 缺席时仍可运行。
- 低等级文案、状态命名和非阻塞一致性问题进入 Roadmap/Issue，不再自动触发热修循环。

## 8. 下一次 Roadmap 更新条件

只有以下事项之一形成正式产品变化时才创建 v0.17：

- Bootstrap 最小实验返回 typed result 并触发新的 Product Decision；
- 第二个代表性项目改变 Context MVU 范围；
- 依赖感知 Prompt-only Pilot 获得实施授权并产生真实运行证据；
- Evals Generator、Knowledge、Connector 或多用户能力形成独立消费者合同；
- Developer Alpha 反馈改变 Product Loop、HITL、Reviewer 权限或公开发行形态。

普通实现进度和单个测试修复记录在 Git、Issue 或 Release Notes，不为每一处变化创建 Roadmap 版本。
