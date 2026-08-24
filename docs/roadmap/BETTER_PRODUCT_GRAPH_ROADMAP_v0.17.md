# Better Product Graph 项目 Roadmap v0.17

状态：RELEASED CURRENT-STATE ROADMAP
日期：2026-08-24
上一版本：`BETTER_PRODUCT_GRAPH_ROADMAP_v0.16.md`（冻结，不修改）
架构基线：`docs/architecture/PRD_GRAPH_v1.4.md`

> v0.17 把当前前向实现目标从旧 Project Bootstrap 修正为轻量“规划上下文准备”，并冻结 Document Experience v0.2 与需求关系导航的交付边界。旧 Bootstrap PRD、Roadmap v0.16 和历史 Run 保留原状态与原字节。

## 1. 一句话结论

Better Product Graph 当前应先帮助产品经理在每次 Product Loop 开始时快速了解可访问的项目背景，再进入 Evidence 与 Problem Discovery；它不在本期建设共享 Snapshot、Refresh、并行 Run 同步或 Knowledge Maintenance Graph。

插件 `0.2.7` 的本地开发目标是：新增 Run 内 `planning.context.prepare`、自包含发布 PRD 写作规范 v0.2、修正关键词式可读性校验，并让 Release/Handoff 能明确指出当前应该实现哪份 PRD以及“文档已发布不等于功能已完成”。

## 2. 当前前向实现依据

### 2.1 当前 Product PRD

- PRD：`BPG-PRD-PLANNING-CONTEXT-001_规划上下文准备_v0.1_2026-08-24`
- 文档状态：PRD Ready / Released
- 产品能力状态：开发中；真实产品效果验证 `NOT_RUN`
- 目标：先发现当前 Host 已授权、可访问的项目材料，再向用户展示找到什么、缺什么和哪些内容需要确认。

### 2.2 被取代的前向目标

`BPG-PRD-PROJECT-BOOTSTRAP-001 v0.3` 继续作为历史 Released PRD 保存，但不再是当前前向实现目标。本期明确取消四项旧假设：

1. 首期必须生成项目级共享上下文版本；
2. Product Loop 必须固定读取某个共享上下文版本；
3. Refresh 属于当前 Project Bootstrap 首期；
4. 首期必须解决 Handoff 后更新与并行 Run 同步。

这些能力如有真实消费者，统一进入未来 Knowledge Maintenance Graph 需求定义，不从旧 Bootstrap 设计倒推实现。

## 3. 0.2.7 当前交付

### 3.1 Planning Context Preparation

新 Product Loop 的 Discovery 路径为：

```text
Signal Intake
    ↓
Route Select
    ↓
Planning Context Preparation
「先利用现有项目资料建立本次规划背景」
    ↓
Evidence Collect
```

一期行为：

- 自动发现 README、项目记忆、Released PRD、Roadmap、架构和 Graph manifest 等明确资料；
- 默认拒绝秘密文件、凭证目录、symlink、越界路径、二进制和超限文件；
- 只把 exact path/hash/version 的已采用材料绑定进当前 Run；
- 支持 `READY / LIMITED / SKIPPED`，背景有限时可以带着明确限制继续；
- 暂停、恢复与旧 Graph migration 使用现有 State Controller 权威链；
- 不声称跨 Run 共享、自动 Refresh 或 canonical project knowledge。

### 3.2 Document Experience v0.2

PRD 模板仍是 `general@0.2.0`；写作 Profile 独立升级为 `prd-plain-language-zh-CN@0.2.0`。v0.1 保持历史 Released Previous，不覆盖。

v0.2 增加：

- 先建立全局框架，再逐层展开；
- 控制信息密度与重复内容，不设简单总字数门槛；
- 简单流程不强制配图，复杂分支/状态/责任关系应使用真正有用的视觉表达；
- PRD 负责产品问题、用户结果、范围、业务规则和可观察验收；内部 Schema、存储、对象拆分和线程模型默认交给 Engineering SPEC；
- 机械 Validator 只检查稳定结构，不再用单个“结论”关键词冒充语义可读性；
- 语义可读性由现有 Reviewer 以 `ADVISORY_ONLY` Finding 审查，不新增 Node、Gate 或阻塞权。

### 3.3 需求关系与人类状态视图

新 Release 投影三类信息：

1. 同一 PRD ID 的新版本通过 exact `supersedes` 形成版本演化；
2. 新 PRD ID 通过 `requirement_relationships.supersedes_forward_delivery_target` 取代旧身份作为前向实现目标；
3. `invalidates` 明确记录被取消的旧假设，但不改写旧文档历史状态。

派生导航 `RELEASE_MANIFEST.json` 只提供 exact refs，标记为 `DERIVED_NAVIGATION_ONLY`，不能用 `latest` 代替正式权威。Handoff 同时携带 exact requirement relationships。人类状态页分别显示：

- 需求文档 Candidate / Ready / Released；
- Reviewer 遗留关注；
- 代码实现；
- 测试 / Evals；
- 本地交接；
- 远程发送。

状态页是 `NON_AUTHORITATIVE` 派生视图，不修改冻结 PRD bytes，也不把 Released 误写成工程实现或测试通过。

## 4. 当前明确不做

- 不恢复旧 Bootstrap 的共享 Snapshot、materialization commit 或 Refresh 合同；
- 不新增独立 Planning Context Graph、Reviewer Gate 或强制人工确认；
- 不让 BPG 直接更新 canonical 知识库；
- 不把 `plain-talk` 作为运行依赖；
- 不把 PRD 内部实现建议升级为研发必须采用的 Engineering SPEC；
- 不用 mutable `current/latest` 指针替代 exact document ref；
- 不声称产品经理阅读效果、真实项目收益或外部交付已经验证。

## 5. 当前验证边界

### 5.1 本地工程验收

0.2.7 在交付前必须通过：

- Planning Context 正常、背景有限、安全拒绝和 installed public path 测试；
- Graph predecessor migration 与暂停/恢复回归；
- Document Experience v0.2 source/runtime byte identity、默认 pin 和 tamper fail-closed；
- Release manifest、requirement relationships、Handoff 与人类生命周期视图；
- 全量源代码测试、确定性双包构建和隔离安装 self-check。

### 5.2 仍为 NOT_RUN

- 零背景产品经理是否真的更快理解项目；
- 首屏发现内容是否准确、充分且不过载；
- Readability Reviewer 是否稳定降低阅读成本；
- 多项目、多语言和外部 Connector 行为；
- 真实研发与测试 Graph 消费 Handoff 的效果。

安装、Schema、测试或 Review PASS 不能替代这些产品结果。

## 6. 后续 Roadmap

### R1：Planning Context 真实试点

在一个真实项目、一个真实 Signal 和干净 Host 会话中验证：是否先利用现有资料、是否减少重复背景搬运、Owner 是否需要重大纠偏，以及背景有限时是否能安全继续。

### R2：Document Experience 用户测试

用零背景中文产品经理测试首屏摘要、信息层级、术语负担、图表价值和 PRD/SPEC 边界。运行结果决定 v0.2 是否继续作为默认 Profile。

### R3：Knowledge Maintenance Graph

先定义共享知识产品的消费者、raw corpus、derived knowledge、更新提案、采纳、版本和权限，再反推 BPG 应提交哪些 PRD、Decision、Roadmap、Review 与原始证据。BPG 当前只读知识并提交更新建议。

### R4：Evals Generator 与 Test Graph

BPG 生成产品级 Eval Contract 与测试设计参考；未来 Evals Generator 生成可验证 Pack，Test Graph 负责正式功能测试、runner 和 verdict。`NOT_RUN` 永远不能渲染为 PASS。

### R5：Connectors 与下游 Graph

按真实位置接入 Issue Collector、飞书项目、研发 Graph、测试 Graph 和远程 Handoff。Connector 只适配外部系统，不承担产品分类和决策。

### R6：规划学习、自进化与多 Agent

规划结束后形成项目知识提案、规划经验和插件改进建议；不得静默自改或未经授权向上游提交。对抗审查和并行 Review 可继续使用受控 sub-agent，跨 Host 多 Agent 等真实需求出现后再设计。

## 7. 永久原则

- Better Product Graph 是产品部分，研发 Graph 和测试 Graph 是可插拔下游。
- Agent 负责产品语义；确定性程序负责状态、权限、完整性、版本和恢复。
- Planning 追求全局完整，单份 PRD 追求高内聚、低耦合和小步交付。
- Reviewer 当前仅提供建议和关注等级；外置团队继续承担最终汇总审批。
- 所有 Decision、WAIT、STOP、COMMIT、Roadmap 和 PRD 都是未来知识库的候选素材。
- 不保存隐藏 Chain-of-Thought，只保存 Evidence、结构化理由、假设、未知、建议、分歧、决定和变更历史。
- 历史版本不可覆盖；修正通过新版本、exact refs 和 changelog 表达。

## 8. 下一次 Roadmap 更新条件

只有以下事项形成正式产品变化时才创建新版本：

- Planning Context 真实试点返回 typed result 并改变范围；
- Document Experience 用户测试改变默认 Profile；
- Knowledge Maintenance、Evals Generator、Connector 或下游 Graph 形成独立消费者合同；
- 多用户共享、权限或无人值守运行改变 Reviewer/Gate 权限；
- Developer Alpha 反馈改变 Product Loop 或公开发行形态。

普通实现进度、低等级文案问题和单个测试修复进入 Git、Issue 或 Release Notes，不为每一处变化创建 Roadmap 版本。
