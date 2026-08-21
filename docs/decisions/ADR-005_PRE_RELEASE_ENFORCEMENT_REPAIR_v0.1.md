# ADR-005: Pre-release Enforcement Repair v0.1

- Status: Accepted for local candidate
- Date: 2026-08-20
- Scope: repairs after the independent rejection of commit `8d7dac9`
- Supersedes: none; complements ADR-001 through ADR-004

## Decision

Better Product Graph 保持一个 public Codex Skill 和一个 installed Host runtime surface。唯一 node-contract registry 将每个 Graph node 绑定到 exact installed instruction/hash、producer、validator、resource refs 和合法 routes。Host Agent 通过同一 surface 执行 `entry`、`dispatch`、`submit`、`owner-choice`；不增加独立 CLI、第二 Host 或服务。

Controller 及其受控 helpers 是唯一正式 mutation authority。每个 Run 使用跨线程/进程锁、真实 CAS、hash-chained meaningful events 和可恢复 transaction records。Node Result 在 persist 前验证 packaged Schema、instruction/input/resource hashes 与 node-specific contract，在 transition 消费前重新验证 Controller result receipt。

每次 Controller state commit 必须在同一 WAL 中保存 exact canonical `after_state`，并把 Controller-derived `before_state_hash` / `after_state_hash` 写入对应 append-only event。所有 public operations 先恢复 PREPARED transaction，再要求完整 commitment chain 连续且最新 `after_state_hash` 等于当前 `state.json` 全量 canonical hash；event-derived node/status/attempt replay 只作为额外语义交叉校验。这样 waiting、interaction policy、artifact refs、Candidate/Decision projection、未知未来字段都自动进入撤权边界，不依赖逐字段补丁。Transition、Owner choice、Candidate finalize、Ready release 与 Handoff 必须使用这一个事务权威；缺少 exact WAL 的 event-ahead snapshot 不做部分字段推测恢复。

Ready 不接受调用者自报 boolean。Controller receipt 必须位于受控 receipts 目录、登记在 append-only ledger/state authority 中、具有 kind-specific subject roles，并 exact 绑定 Candidate、companion、template、policy、version、changelog、upstream、Review、assets 等 Ready facts。Receipt 是不可变且 exact-idempotent 的；Candidate v1 receipt 不能用于 v2。

Agent Decision Draft 与 Owner choice 分权。Agent 只能提交 recommendation/proposal；Owner choice 是绑定 proposal hash、Owner actor 与 state version 的独立 typed command。Controller 只路由已授权的 STOP、WAIT、RESEARCH、EXPERIMENT、COMMIT NOW/FUTURE，不新增重复确认 node。

## Semantic authority boundary

Problem Discovery、Assumption Audit、Product Decision、Planning、PRD 与 Review 的智能内容只能由 Host Agent 按 Atomic Instructions 生成。Python 不选择问题、MVU、证据意义、认知基座、产品 outcome、Plan slice、PRD 内容或 Reviewer Finding；它只验证 Agent/Owner 已明确提交的 typed values、hard constraints 和 exact provenance，并执行已授权的 deterministic route。

Product Golden fixture/contract PASS 只证明 harness 与 fixture 边界。未运行真实 Agent 时，Agent runtime/product judgment 必须保持 `NOT_RUN`。

## Distribution and provenance

构建从明确 allowlist 复制必需 trees，拒绝 symlink、额外 public Skill、缺失/变更 reference。Build manifest 绑定 plugin version、Git commit/dirty、V1.4/Roadmap hashes、execution fingerprint、排序 inventory 和 artifact hash。Package 使用固定 ZIP 时间、排序 entries 和稳定 permissions；隔离 install/rollback 使用 disposable `CODEX_HOME`。

Better Question、Cognitive Router、20 个认知基座和 Product Goal Fidelity reviewer 作为 versioned non-discoverable references 安装。Source workspace 可重算 declared extraction hashes；installed copy 只依赖 checked-in relative provenance/catalog 与 packaged hashes，不依赖用户绝对路径。

## Historical audit pin

独立 `audit.py` 是对 exact commit `8d7dac9` 的不可变拒绝证据，包含旧的 expected HEAD 与测试数。修改它使新候选显示 PASS 会破坏审计含义。新候选改用 `scripts/verify_audit_repairs.py` 运行当前 public/official-path regressions，并逐项处置 C1–C4、H1–H15、M1–M4 及后续独立 finding；历史 REJECT 与候选 repair evidence 同时保留。候选自证中的 `VC5-C1` PASS 不替代独立 re-audit，后者在实际复验前保持 `NOT_RUN`。

## Rejected alternatives

- 用签名服务或数据库认证 receipts：超出 local-first 候选需求。
- 用 deterministic Python 规则替代 Agent 产品判断：违反语义 authority 边界。
- 复制 20 个 public Skills 或增加 cognitive Graph Nodes：破坏唯一入口与冻结 Graph。
- 修改历史 audit 适配新 HEAD：会把历史证据变成可漂移测试。
