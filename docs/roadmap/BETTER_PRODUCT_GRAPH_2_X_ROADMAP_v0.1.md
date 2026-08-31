# Better Product Graph 2.x 产品 Roadmap v0.1

状态：CURRENT WORKING ROADMAP  
日期：2026-08-31  
产品代际：Better Product Graph 2.x  
上一份前向 Roadmap：`BETTER_PRODUCT_GRAPH_ROADMAP_v0.17.md`（旧 0.x 路线，冻结保留）  
权威产品方法：`docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.2.md`  
当前过渡发行：`0.2.20` Developer Alpha，内含显式启用的 BPG 2.0 单 PRD Alpha

> 本 Roadmap 取代 v0.17 作为新的前向规划入口，但不改写 v0.17、旧架构、旧 Run、旧 Release 或历史验收结论。

## 1. 一句话结论

BPG 2.0 先完成当前单 PRD Alpha 的真人测试和版本收敛，再依次交付 2.1 多 PRD、2.2 轻量 Evals Generator、2.3 产品形态知识包、2.4 条件配置与专业 Reviewer、2.5 增强交付与 `eli-me`；全部能力通过整体回归后，才进入正式 Release Candidate 和 `2.0.0` 稳定版判断。

## 2. 版本号从现在开始怎样使用

四种版本必须分开：

| 名称 | 用途 | 当前或下一身份 |
|---|---|---|
| 产品代际 | 表示核心架构与产品边界 | `BPG 2.x` |
| 能力里程碑 | 表示 Roadmap 顺序，不是公开包 SemVer | `2.1`—`2.5` |
| 插件发行版本 | 表示可安装、可校验的精确发行物 | 当前 `0.2.20`；后续 `2.0.0-alpha.N` |
| 文档与产物版本 | 表示某份 Roadmap、PRD、Profile、Schema 或 Review 的自身版本 | 各自在独立命名空间演进 |

公开包建议采用以下通道：

```text
当前过渡包 0.2.20
        ↓
2.0.0-alpha.N   内部主链和前半段能力仍在形成
        ↓
2.0.0-beta.N    2.1—2.5 已基本集成，开始整体产品验证
        ↓
2.0.0-rc.N      2.1—2.5 全部达到最低验收，候选冻结
        ↓
2.0.0           稳定发布门槛全部满足
```

规则：

- `0.2.20` 保持不可变，不重打 Tag，不覆盖 Release。
- 第一个重新编号的发行候选使用下一个未占用的 `2.0.0-alpha.N`，建议从 `alpha.1` 开始。
- `2.1`—`2.5` 不自动发布为 `2.1.0`—`2.5.0`；它们是 BPG 2.0 内部能力里程碑。
- Alpha、Beta、RC 都不得省略预发布后缀或冒充稳定版。
- 每个 Run 必须绑定精确插件版本、Runtime 身份、产品代际和 Artifact 引用；禁止用“latest”续跑。

## 3. 当前基线

### 3.1 已完成并有内部证据

- BPG 2.0 单 PRD 主链已经实现为独立 `BPG_2_0_ALPHA` Runtime。
- 一条真实 Codex Host Run 已从 Signal 走到 `LOCAL_HANDOFF_COMPLETE`。
- 已覆盖六类决策结果、Problem / Decision / PRD Candidate、独立 Review、最多两轮修订、Ready、Local Handoff 和暂停恢复。
- Markdown 与 assets 是编辑真源，自包含 HTML 是默认阅读视图。
- `0.2.20` 已作为过渡 Developer Alpha 发布并安装；BPG 2.0 仍需显式启用。

### 3.2 尚未完成

- Owner 在新任务中的真人产品测试和问题回收。
- 多个真实需求、多次中断恢复和跨项目适用性验证。
- 独立盲审下的 PRD 质量对比、产品经理重大纠偏、阅读体验、时间和 token 成本评估。
- 多 PRD、完整 Evals Generator、产品形态知识包、专业 Reviewer、DOCX / PDF、外部 Connector 和远程交付。
- 研发接收、实现、Test Graph 执行、上线结果和产品效果验证。

因此当前状态仍是 **Developer Alpha**，不是 BPG 2.0 正式完成。

## 4. 近期优先级：2.0 Alpha 收敛

在开始 2.1 前，先关闭当前 Alpha 的真实使用问题。

### 目标

- 收集 Owner 在新任务中完整使用 BPG 2.0 的问题。
- 优先修复阻断、错误路线、状态不真实、恢复失败、PRD 明显退化和操作负担过高的问题。
- 把安装包、Runtime、产品代际和权威基线写成清晰、可机器验证的独立身份。
- 形成第一个 `2.0.0-alpha.N`，结束“插件 0.2.20 内嵌 BPG 2.0”的过渡命名。

### 不做

- 不趁测试修复提前加入多 PRD、完整 Evals Generator、专业 Reviewer 或 Connector。
- 不迁移或重新解释旧 Run。
- 不用更多 Schema、Gate 或状态机掩盖 Agent 产品判断问题。

### 退出条件

- Owner 能在全新任务中进入精确 BPG 2.0 Runtime，并完成、暂停、恢复或负责任地停止一次 Run。
- 已发现的 P0 / P1 问题关闭；其他问题有明确状态和后续归属。
- 完整回归、安装验证、精确身份和本地回滚路径通过。
- 发行说明继续如实保留外部交付、工程实现和产品效果 `NOT_RUN`。

## 5. 小迭代 2.1：多 PRD 与复杂产品系统

### 产品目标

让一个复杂产品需求可以拆成多份高内聚 PRD，同时保留完整产品叙事、共享目标、依赖和整体一致性。

### 核心范围

- 总 PRD 或产品总览文档。
- 多个 PRD sub-run。
- 横向模块与纵向迭代拆分。
- 共享背景、目标、契约和依赖。
- 兄弟 PRD、supersedes、invalidates 和 affected-scope 关系。
- 完整 PRD Release Set 的全局 Review 和整体回归。

### 最低验收

- 每份子 PRD 可以独立交付和验证，但不能丢失整体用户结果。
- 任一子 PRD 的实质修改会触发受影响关系和整体回归。
- 所有子稿分别 PASS 不能替代整套产品系统 PASS。
- 单 PRD Alpha 的路线、暂停恢复、Review 和 Ready 合同不得退化。

## 6. 小迭代 2.2：轻量化 Evals Generator

### 产品目标

让 `REQUIRED` Product Evals 可以形成最小完备、可追溯、可独立审查的 Eval Pack，同时不把 BPG 变成 Test Graph。

### 核心范围

- Agent-first 的适用性判断。
- 精确 Candidate 与 Eval Pack 绑定。
- Ground Truth、Rubric、输入、预期结果和执行要求。
- 独立规格 Review、新鲜度和 Ready 边界。
- 删除旧 Evals Generator 中没有不可替代价值的重复合同、状态和程序层。

### 最低验收

- `REQUIRED` Eval Pack 缺失时准确阻断 Ready。
- Ground Truth 或专业权威缺失时给出真实原因和恢复方式。
- `RECOMMENDED` 可以保留 `NOT_AVAILABLE / NOT_RUN` 而不默认阻断。
- BPG 永远不冒充 Test Graph 给出真实执行 PASS。

## 7. 小迭代 2.3：产品形态知识包

### 产品目标

让 Agent 能根据桌面端、iOS、Android、Web、Agent、本地、云端、API / SDK 和内部运维等不同产品形态，识别真正不同的用户路径、约束和边缘场景。

### 核心范围

- 可扩展的方法卡、适用信号和代表性场景。
- Agent 按任务组合调用，而不是机械运行完整 Checklist。
- 平台行为、离线/在线、韧性、权限、升级和失败体验差异。
- 知识包适用性与缺失状态的真实表达。

### 最低验收

- 同一需求在不同产品形态下能形成有意义的差异。
- 不适用内容不会污染 PRD。
- 缺少专属知识包时保留未知，不伪造确定性结论。
- 方法卡只帮助 Agent 判断，不成为新的刚性 Runtime 流程。

## 8. 小迭代 2.4：条件式配置与专业 Reviewer

### 产品目标

只在任务真正需要时加入语言、地区、市场、数据、安全、隐私、合规和无障碍等条件能力及专业审查。

### 核心范围

- Locale、Market、Data Collection、安全域和其他项目级配置。
- 必填、可选、禁用、敏感确认和平台差异。
- 语言精确性、产品文案、地区文化、安全、隐私、合规、无障碍等专业 Reviewer 能力合同。
- Reviewer 能力声明、输入合同、Finding 和聚合规则。

### 最低验收

- 条件式内容只在适用时出现。
- 项目配置不会被通用默认值静默覆盖。
- Reviewer 与作者保持独立，结论绑定精确 Candidate。
- 缺少合格专业 Reviewer 时显示 `NOT_RUN / NOT_AVAILABLE`，不能用通用 Agent 冒充专业结论。

## 9. 小迭代 2.5：增强交付与 `eli-me`

### 产品目标

在不产生第二事实来源的前提下，增强正式阅读、交付和高强度产品质询体验。

### 核心范围

- 条件式 DOCX / PDF 输出。
- 资源内嵌、精确版本绑定和跨格式保真检查。
- 复杂图表、分页和中文排版。
- 独立 `eli-me` 命令，进入更严格的产品经理 Grilling 模式。

### 最低验收

- 所有派生格式都与同一 Markdown / assets 真源一致。
- DOCX / PDF 不形成可独立修改的第二真源。
- `eli-me` 能提高质询强度，但不绕过证据、Owner 权限、停止条件或正常 BPG Graph。
- 外部发送仍必须有真实 Connector、权限、幂等性和回执，不能把本地生成写成已交付。

## 10. BPG 2.0 Release Candidate 门槛

只有完成 2.1—2.5 且前序能力没有退化，才进入 `2.0.0-rc.N` 判断。

RC 至少需要：

- 多个不同类型真实需求的完整 Host E2E。
- 单 PRD与多 PRD、正式 PRD 与实验型 PRD的完整回归。
- 暂停恢复、幂等重试、Candidate 不可变、Reviewer 独立和精确 Owner 权限继续成立。
- 两个 Host 的确定性包、隔离安装、升级、回滚和 installed self-check。
- 独立盲审证明 PRD 质量不退化；同时记录产品经理时间、总耗时和 token 成本。
- 真实人类阅读与使用测试，问题全部有明确处置。
- 旧 0.x 默认入口的退役、保留或独立安装策略已经明确，不能与 BPG 2.0 静默混跑。
- README、安装文档、Release Notes 和构建清单中的产品代际、插件版本、Runtime 身份一致。
- 外部交付、研发接收、实现、测试执行和产品效果没有被虚假宣称。

## 11. `2.0.0` 稳定版门槛

`2.0.0` 不是“RC 没发现崩溃”即可发布。至少还需要：

- RC 期间没有未关闭的 P0 / P1 产品或运行问题。
- Owner 明确确认 BPG 2.0 的产品边界、默认入口和旧版本处置。
- 真实测试表明 BPG 在质量优先前提下提供可接受的时间与成本。
- 安装、升级、回滚、恢复和版本锁定均有可重复证据。
- 已知限制、`NOT_RUN` 和不支持项在用户入口可见。

若这些条件未满足，继续发布新的 Alpha、Beta 或 RC，不以日期倒逼稳定版本号。

## 12. 不进入 BPG 2.0 的范围

- 旧 Run 的迁移、转换、兼容别名或双写。
- Development Graph、Test Graph 或 Knowledge Maintenance Graph 的内部实现。
- 通用多 Agent 平台、数据库、队列、Daemon 或 Web 工作台。
- 用机械字段完整度、评分总分或多个模型一致性冒充产品质量。
- 未经 Owner 授权的自动发布、外部发送或不可逆操作。
- 静默自我修改、自动推广方法卡或未经验证的跨项目规则。

这些能力若未来出现真实需求，应作为 BPG 2.x 之后的独立产品决策，而不是提前塞进 2.0。

## 13. 衡量方式

质量优先，不把质量、成本和速度压成一个加权总分。

依次判断：

1. 是否定义了正确的问题并作出更好的产品决策。
2. PRD 是否经独立盲审证明更完整、清晰、可执行和可验证。
3. Owner 是否需要重大纠偏，纠偏能否被正确回流。
4. 在质量相当时，再比较产品经理投入时间、总耗时、token 和运行成本。
5. 状态真实性、恢复失败、错误权限或错误版本一律单独报告，不能被平均分掩盖。

## 14. 当前下一步

当前唯一前向任务是：

```text
等待 Owner 在新任务中测试 0.2.20 / BPG 2.0 Alpha
                    ↓
收集并分级真实问题
                    ↓
完成 Alpha 收敛、全量回归和身份整理
                    ↓
发布首个 2.0.0-alpha.N
                    ↓
再启动小迭代 2.1
```

Owner 测试期间不并行扩建 2.1—2.5，避免把当前主链问题和后续功能开发混在一起。

## 15. 后续文档规则

本文件交付后冻结。后续实质修改必须创建新版本，例如：

```text
BETTER_PRODUCT_GRAPH_2_X_ROADMAP_v0.2.md
```

不得原位修改本文件；新版本必须记录 supersedes 关系并保留历史文件。
