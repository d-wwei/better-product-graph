# Decision document changelog

## 2026-08-21

- 新增 `ADR-007_DUAL_REPOSITORY_RELEASE_MODEL_v0.1.md`，确认私有研发仓库为唯一研发真源，正式仓库只接受单向生成的发布快照。
- 正式仓库不继承研发历史；每次发布必须记录来源研发 commit、产品版本、生成日期和发布文件清单。
- 本地运行状态、Host 缓存、临时 Worktree、锁文件、凭证和可重复生成内容不因研发仓库私有而进入 Git。

## 2026-08-20

- 新增 `ADR-006_REVIEW_COMPANION_CANDIDATE_GENERATIONS_v0.1.md`，记录同 PRD 版本的 copy-on-write Candidate generation、Controller-owned companion finalization、恢复事务，以及多 Decision/Evidence exact-ref 全量绑定。
- 新增 `ADR-005_PRE_RELEASE_ENFORCEMENT_REPAIR_v0.1.md`，记录 installed execution spine、Controller/receipt authority、Agent/Owner 分权、事务恢复、确定性分发及历史审计 pin 边界。
- `ADR-005` 明确 Python 不得实现 Discovery/Decision/Planning/PRD/Review 的产品语义；fixture PASS 不等于真实 Agent PASS。
- `ADR-005` 无上一版本，不覆盖 `ADR-001` 至 `ADR-004`，也不修改冻结 V1.4/Roadmap v0.12。
- 新增 `ADR-003_AGENT_PROPOSAL_OWNER_CHOICE_v0.1.md`，将 Agent proposal 与 typed Owner choice 分权，记录 installed runner 操作面、六种确定性路线、append-only Decision Ledger 和纯投影边界。
- 新增 `ADR-002_FROZEN_TEMPLATE_PUBLIC_DERIVATION_v0.1.md`，记录 exact upstream fallback 中绝对作者路径与 public validator 的冲突，以及唯一、具名、双 hash 可审计的 source→dist 派生。
- 新增 `ADR-001_LOCAL_PLUGIN_RUNTIME_v0.1.md`，状态为 `Accepted for implementation`。
- 记录 skills-only 本地候选、Python/JSON/JSONL、原子持久化、installed identity 与可替换边界。
- 明确 Host Agent 独占产品语义工作；程序只执行合同、状态、验证、路由和文件机械约束。
- 无上一版本；本文不修改或取代冻结的 V1.4 架构与 Roadmap v0.12。
