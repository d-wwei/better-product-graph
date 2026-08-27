# Better Product Graph 0.2.19：旧 Run 精确恢复热修复

日期：2026-08-27

状态：SOURCE VERIFIED。本文记录的源码验证不自动代表 GitHub 发行、全局安装或真实产品执行；这些交付动作必须分别留下后续证据。

## 1. 为什么需要这次热修复

0.2.18 能正确拒绝合同已经变化的旧 Run，但五个已知旧 Run 只能得到
`BLOCKED_STALE`，没有受支持的恢复方法。用户明明保存了完整历史，却无法在
原 Run 上继续。

0.2.19 不增加通用的 `force` 或 `ignore-stale` 开关。它只为已经逐个审计的
五种旧状态登记精确恢复合同：旧 Graph、当前节点、完整状态与事件语义、
Instruction、Attempt 生命周期及 Artifact 引用必须同时匹配。任何未知或有
歧义的组合继续只读地返回 `BLOCKED_STALE`。

## 2. 用户会看到什么

用户仍只需说“继续这个 Run”或使用既有 `resume`。Host 不要求用户记忆修复
命令。已知旧状态恢复成功时返回 typed `STALE_RUN_RECOVERED`、中文说明及
当前工作单；崩溃后的重复 Resume 返回幂等的 `RESUMED` 和同一 Run 的当前
工作单。

恢复不会创建替代 Run，也不会删除、重写旧 Attempt、Event、Receipt 或
Artifact。旧工作单以 `RETIRED_STALE` 留在历史中；当前 Graph 在同一 Run 中
创建新的 Attempt。

## 3. 五个新恢复合同与一个既有迁移

| 旧状态 | 恢复动作 | 恢复后的当前工作 |
|---|---|---|
| `run-016…` 的两个错误 `signal.classify` dispatch | 退休错误绑定的 `route-select` 工作单 | 用当前 Signal Intake Host 合同重新派发 `signal.classify` |
| `run-f6…` 的 alpha.1 `signal.prepare` | 退休旧 deterministic dispatch | 在同一 Run 重派当前 `signal.prepare` |
| `run-efe…` 的旧 `review.parallel` | 不复用旧 Review authority | 派发隔离的当前 `review.parallel` |
| `run-ad2…` 的旧 Ready | 清空“当前有效” Ready 引用，但保留旧 Receipt 文件和 ledger | 回到当前 `review.parallel`，重新 Review 后再进入 Ready |
| `run-bc4…` 的缺失 Candidate | 从登记的 Git commit/tree/blob 精确恢复三文件 Candidate | 回到当前 `review.parallel` |

`run-74…` 不是第六个新恢复合同；它继续使用已经存在的 alpha.2 → 当前 Graph
兼容迁移。

## 4. 安全与恢复边界

- 匹配前验证完整 Event chain、State commitment 和历史 dispatch authority；
  只把已明确登记的合同漂移作为例外。
- 只有未消费、无副作用、没有 Result/Receipt/未知文件的旧 Attempt 可以退休。
- Recovery 使用 Run lock、全局 PRD Artifact lock、expected-state CAS、预写
  transaction journal 和 append-only typed event。
- 两个 Host 并发恢复同一个 `PAUSED` Run 时，每个调用都在写入前绑定精确
  PAUSED basis。无论 Recovery 调用方还是普通 Resume 调用方先完成，CAS 失败方
  只有在该 basis 被唯一 Recovery event/hash 绑定，且后续仅发生合法的
  `PAUSED → ACTIVE` 和至多一个完整当前 dispatch 时才幂等读回。普通暂停、
  访谈策略等任何无关并发变化仍保留原 CAS 冲突。
- Git 恢复只允许 `current_candidate_ref.artifact_path` 指向的
  `artifacts/prds/archived/` 子树；commit、closed-world inventory、path、mode、
  blob OID、文件 Hash 和 tree Hash 全部必须一致。
- 发布使用 no-overwrite hard link。重试时，已存在目标必须与同一 journal 的
  staged blob 共享文件身份；相同字节但来源不明的外部文件也不会被接受。
- Review 恢复保留历史 Artifact refs，但新 Reviewer 工作单只暴露当前
  Candidate、当前 Profile/Guide/Review 合同及必要上游事实；旧 Aggregate、
  Disposition、Writing Coverage、Companion 和 Ready evidence 不会进入首轮输入。
- Ready Receipt 采用 Attempt-scoped 新代际；固定旧路径继续保留，不能覆盖或
  重新获得当前 authority。

## 5. 六个真实 Run 的临时副本验收

验收只在主项目完整临时副本执行，未修改原始 Run：

| Run | 结果 |
|---|---|
| `run-016a9cba2674` | 同 Run 到达当前 `signal.classify` work order |
| `run-f6d4ea87d4c2` | 同 Run 到达当前 `signal.prepare` work order |
| `run-efe040ea8811` | 同 Run 到达隔离的当前 `review.parallel` work order |
| `run-ad2ec7712339` | 同 Run 到达隔离的当前 `review.parallel`；旧 Receipt 保留 |
| `run-bc4bac0f4c21` | 三文件 Candidate 恢复为登记的 `d297357…` tree，并到达隔离的当前 Review |
| `run-74b3c86967e4` | 既有 migration 后到达当前 `evidence.collect` work order |

`run-ad2…` 继续走到新 Ready 后，新的 Audit、Review Finalize 和 Document
Experience Receipt 均以当前 Attempt 代际成功签发，未出现旧固定 Receipt 的
identity conflict。随后旧 PRD 被当前 PRD Schema 的真实内容缺陷拦截为
`NOT_READY`；这证明恢复链不再卡在 Receipt 冲突，但不把旧文档误报为 Ready。

`run-bc4…` 还分别在 `after_recovery_staged`、`after_state_event`、
`after_recovery_state`、`after_recovery_publish` 四处模拟崩溃。重启后只说“继续”
均在原 Run 返回一个当前 Review work order；每个副本都只有一条 recovery event
和一个当前未消费 dispatch。

## 6. 机械验证证据

- 完整源码测试：`773 tests / OK`。
- stale recovery focused tests：`12 tests / OK`，覆盖 allowlist、unknown
  zero-write、Result authority、CAS zero-write、并发 Resume、崩溃续派、Review
  输入隔离、`PAUSED` 恢复竞态及无关并发变化 fail-closed，以及 Git
  commit/blob/mode/hash/target/symlink 失败。
- 原主项目 Run 文件指纹：
  `fecc5d1b51008d465b8ae6c05aa981126b0be277ab3b9da3e246dd342527b946`。
- 原主项目 Run symlink 指纹：
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。

最终提交后还必须从 clean commit 生成 Codex/Claude 各两份 deterministic
package，完成隔离安装、self-check、合同测试、卸载与 rollback。这些
post-commit 证据不写入自引用的源码提交，由交付报告单独记录。

## 7. Writing 语义证据边界

本热修复没有修改 Writing Profile v0.5、Writing Guide v0.5、PRD Review
Instruction、Reader Review v3.1/v3.2、对应 Eval contracts/schema 或冻结套件。
因此 0.2.18 的两组 `27/27` 语义证据仍适用于这些未变字节；本次没有重跑
Reviewer，也没有产生新的 Writing 质量声明。真实人工阅读继续是 `NOT_RUN`。

## 8. 明确保留的限制

- 只恢复登记过的五种历史指纹；其他 stale Run 仍需单独审计。
- 恢复只解决合同与 authority 迁移，不自动修复旧 PRD 的内容质量或当前 Schema
  缺陷。
- Reviewer `{kind,id}` 独立性仍是现有 Host identity model，不是外部加密身份
  证明。
- 本文证明的是 Run 可恢复与当前工作单可达，不代表 PRD Ready、功能实现、测试
  执行、外部批准或真实产品效果。
