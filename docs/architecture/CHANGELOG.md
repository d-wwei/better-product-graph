# PRD Graph 架构文档版本台账

## BPG Product Planning Method v0.3 Candidate — 2026-09-01

- 状态：`CANDIDATE / NOT_YET_RELEASED`；文件 `BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md`，SHA-256 `e82ec004ca7dcf7b022e8d7915f4416d332529defb2a11a138fdb4221c2b6570`。
- Supersedes：`BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.2.md`；v0.2 保持不可变，SHA-256 `00059adeef0b95ca09c4c0398cd1b35a1a8259aad8a6dddde18e54be63d3db49`。
- 版本理由：新增 Solution Intelligence 适用性、Host 语义授权边界、Stage 4 disposition 重绑定、Clean Reviewer Context、Finding 闭环与 Product Evals 2.2 边界，并把 Alpha Candidate/Handoff 真源收敛为 `PRD.md` + Mermaid source；属于方法过程和责任边界的向前兼容新增，按 Minor 升级为 v0.3，而非覆盖已交付 v0.2。
- 新 Run 与公开 Host Skill 选择 v0.3；历史 Run、旧安装和旧精确引用不迁移。

## 当前版本

- Version: `v1.4`
- File: `PRD_GRAPH_v1.4.md`
- SHA-256: `f03ee71c0dde313b8227eaf5384d6ed3b20a0d906b66606fd5a0d28ee9007a29`
- Date: 2026-08-20
- Status: frozen distribution/eval implementation contract closeout / implementation pending
- Supersedes: `v1.3`

## 冻结版本

- Version: `v1.3`
- File: `PRD_GRAPH_v1.3.md`
- SHA-256: `909d693f091c43986910a07af88ad2b25d10544ba8511651c86b7f17ac6b6ac9`
- Status: superseded / immutable architecture consistency baseline

- Version: `v1.2`
- File: `PRD_GRAPH_v1.2.md`
- SHA-256: `1265601f31ef2375a9222d78d47254fa54627402859cf3054af750ffb940a352`
- Status: superseded / immutable working baseline

- Version: `v1.1`
- File: `PRD_GRAPH_v1.1.md`
- SHA-256: `9448095af39b6281639563c6e4fcbad9af1e1658f07b57766ed1f71d4194ef5d`
- Status: superseded / immutable review baseline

- Version: `v1.0`
- File: `PRD_GRAPH_v1.0.md`
- SHA-256: `97ab5cf6547c28033ba4cd73e716659e6e640db4b8313d8e0e0e3da03e7f6226`
- Status: superseded / immutable

- Version: `v0.9`
- File: `PRD_GRAPH_v0.9.md`
- SHA-256: `0fbcc505091a6b8edfb31999931506e42d402dacda8249af9a7adff7a64e4790`
- Status: superseded / immutable

- Version: `v0.8`
- File: `PRD_GRAPH_v0.8.md`
- SHA-256: `69c56764425c1ccd35e70ef2c5ffa0121a4ad8b53da3de21129573b2e8888264`
- Status: superseded / immutable

- Version: `v0.7`
- File: `PRD_GRAPH_v0.7.md`
- SHA-256: `6349c84c2340b5f956732578d6b6c99c374456c1075e9f4265decd0b68a63ff2`
- Status: superseded / immutable

- Version: `v0.6`
- File: `PRD_GRAPH_v0.6.md`
- SHA-256: `486e5d166405ab426107f905c6302bfe4838d5fb8b9a3b09a265c66c1ed027d7`
- Status: superseded / immutable

- Version: `v0.5`
- File: `PRD_GRAPH_v0.5.md`
- SHA-256: `dcff7508d62f42418c61bd29005a69c3967ddd65875540370e352c5c8c8701f2`
- Status: superseded / immutable

- Version: `v0.4`
- File: `PRD_GRAPH_v0.4.md`
- SHA-256: `5c0cdf81e5fd2ec507c6b64aee211165214ca9bbceb637c4b323e0b4afe8a068`
- Status: superseded / immutable

- Version: `v0.3`
- File: `PRD_GRAPH_v0.3.md`
- SHA-256: `f2982ee29b7eaf81f23d0d86e56581ccb620ba052eea9a42ce95c6431fa91077`
- Status: superseded / immutable

- Version: `v0.2`
- File: `PRD_GRAPH_v0.2.md`
- SHA-256: `3d99d9820956ac4bb1181dc18f57b42ff876290af1f9ff3aba49bcf400a706ca`
- Status: superseded / immutable

- Version: `v0.1`
- File: `PRD_GRAPH_V0.md`（历史文件名保留，不重命名）
- SHA-256: `f03dc09e00a1f859444220149f6f4112243b9db2c4eee3b9a270d0533db24d73`
- Status: superseded / immutable

## Version History

| Version | Date | Status | File | Supersedes | Summary |
|---|---|---|---|---|---|
| v0.1 | 2026-08-18 | superseded | `PRD_GRAPH_V0.md` | none | 明确 PRD Graph 仅为完整产线的产品部分，并展开内部 Product Loop |
| v0.2 | 2026-08-19 | superseded | `PRD_GRAPH_v0.2.md` | v0.1 | 恢复原始 Graph 主结构；明确研发/测试专业 Reviewer 属于 PRD Graph，而研发/测试 Graph 是独立下游 |
| v0.3 | 2026-08-19 | superseded | `PRD_GRAPH_v0.3.md` | v0.2 | 细化知识库持续更新与多人共享；把 Better Question、认知底座和 Product-Prd-Skill 融入问题定义—产品决策认知循环；列出 Skill 吸收边界 |
| v0.4 | 2026-08-19 | superseded | `PRD_GRAPH_v0.4.md` | v0.3 | 将 PRD 模板改为项目级可配置；当前启动默认锁定到 better-product-plan 模板；补充模板选择、映射、版本和失败处理规则 |
| v0.5 | 2026-08-19 | superseded | `PRD_GRAPH_v0.5.md` | v0.4 | 定义好 PRD；新增“规划要全、单份 PRD 要小”、Product Plan、规划覆盖、价值切片和一份规划对应多份独立 PRD |
| v0.6 | 2026-08-19 | superseded | `PRD_GRAPH_v0.6.md` | v0.5 | 将知识采集、审核、冲突和发布移出 PRD Graph；PRD Graph 只读固定快照、提交变更建议并等待知识库维护 Graph 处理 |
| v0.7 | 2026-08-19 | superseded | `PRD_GRAPH_v0.7.md` | v0.6 | Product Goal-Based Audit 第 1 轮优化：补齐发布/纳入、快照与重跑、Reviewer/Ready 失效、安全治理、证据/覆盖门槛、运行恢复和架构审计 Loop |
| v0.8 | 2026-08-19 | superseded | `PRD_GRAPH_v0.8.md` | v0.7 | 将当前产品形态收敛为 Graph Skill Pack：总编排 Skill + 原子 Skills + Graph 清单 + 运行账本；MCP、CLI、服务和数据库改为满足真实触发条件后再引入 |
| v0.9 | 2026-08-19 | superseded | `PRD_GRAPH_v0.9.md` | v0.8 | 将产品形态明确为宿主无关 Core + 薄 Host Plugin + 可选 Connector；新增 Host Adapter/Connector、Schema/Validator/Gate、状态权限、审计回放和可选扩展；后经用户授权原位删除顶层 Driver，并补充 Review–Optimize 循环、Graph 内置版本管理和 Connector 固定挂载点 |
| v1.0 | 2026-08-19 | superseded | `PRD_GRAPH_v1.0.md` | v0.9 | 确定父 Plan Run + 独立 PRD Runs、State Controller 重算 Gate、Incident/Bug/Discovery 三条真实路径、Problem Ready 三段式、知识 Proposal/Impact 闭环、正式 Handoff 合同和垂直切片建设顺序 |
| v1.1 | 2026-08-19 | superseded / immutable | `PRD_GRAPH_v1.1.md` | v1.0 | 将 Problem Discovery 明确为面向 Junior PM 的研究/访谈/辅导/挑战循环；接入 20 个认知基座目录与按需路由；把 Product Decision 改为审慎地做、大胆地停；定义条件式 Eval Strategy/Eval Pack 和未来 evals-generator 合同；加入逐节点 Review 机制 |
| v1.2 | 2026-08-20 | superseded / immutable working baseline | `PRD_GRAPH_v1.2.md` | v1.1 | 逐节点讨论并确认 Signal、Incident、Bug、Evidence、Problem、Decision、Planning、PRD、Review、Ready、Handoff、HITL、Git、模板、Evals 和扩展边界；保留部分后续被 V1.3 收敛的旧表述 |
| v1.3 | 2026-08-20 | frozen architecture consistency baseline / implementation pending | `PRD_GRAPH_v1.3.md` | v1.2 | 最终一致性收敛：移除重复人工确认和 Reviewer blocking/waiver，统一 Experiment pipeline，延后 KMG submission/Impact 细节，收窄 State/Audit 与兼容债务，明确模板可配置及 Golden Cases 未运行，并对齐 Node Review 状态 |
| v1.4 | 2026-08-20 | frozen distribution/eval implementation contract closeout / implementation pending | `PRD_GRAPH_v1.4.md` | v1.3 | 窄幅关闭 Codex 唯一公开 Skill 与内部 Atomic Skill Modules 分发冲突，冻结 source→dist allowlist/installed identity、Product/Plugin Suite 分工、legacy eval v0.1→v0.2 迁移边界，并消除 general 模板固定人工 promotion Gate 矛盾；不扩产品范围或新增 Runtime |

## 用户授权的原位修订

| Date | Version | Before SHA-256 | After SHA-256 | Authorization | Change |
|---|---|---|---|---|---|
| 2026-08-19 | v0.9 | `a8a42ebf069756f58f8ee1dc92f5f2a3648a5c3cd2239b8cb354454e0bdd3aa0` | `d6a91c02bae0d9385c5712b447984989c185ec6cac93e87459b12a4032c14c6e` | 用户明确要求“这个点你直接在V0.9上改吧” | 删除顶层 Connector + Driver 双层设计；顶层只保留 Host Adapter 和 Connector，协议与供应商作为 Connector 内部实现 |
| 2026-08-19 | v0.9 | `d6a91c02bae0d9385c5712b447984989c185ec6cac93e87459b12a4032c14c6e` | `0fbcc505091a6b8edfb31999931506e42d402dacda8249af9a7adff7a64e4790` | 用户明确要求“把这个点的修改在当前版本加进去”，并要求把版本管理内置进 Graph、解释 Connector 位置 | 将 Reviewer 改为受控 Review–Optimize 循环；正式产物不可覆盖并绑定版本/哈希；新增 Connector mount point 规则、Issues Collector 输入端和 Feishu Project 输出端约束 |

## Next Version Rule

下一次修改必须创建新文件，例如：

```text
PRD_GRAPH_v1.5.md
```

不得再编辑 `PRD_GRAPH_V0.md`、`PRD_GRAPH_v0.2.md`、`PRD_GRAPH_v0.3.md`、`PRD_GRAPH_v0.4.md`、`PRD_GRAPH_v0.5.md`、`PRD_GRAPH_v0.6.md`、`PRD_GRAPH_v0.7.md`、`PRD_GRAPH_v0.8.md`、`PRD_GRAPH_v0.9.md`、`PRD_GRAPH_v1.0.md`、`PRD_GRAPH_v1.1.md`、`PRD_GRAPH_v1.2.md`、`PRD_GRAPH_v1.3.md` 或 `PRD_GRAPH_v1.4.md`；后续修改必须新建版本。
