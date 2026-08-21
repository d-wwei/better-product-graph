# ADR-003: Agent proposal 与 Owner choice 分权 v0.1

状态：Accepted for local candidate
日期：2026-08-20
依据：`PRD_GRAPH_v1.4.md`、`BETTER_PRODUCT_GRAPH_ROADMAP_v0.12.md`、implementation audit C1/C4/H11
上一版本：无

## 结论

`product.decision` 的 Host Agent Node Result 只能形成 `Agent Decision Proposal`，不能携带或伪造 Owner 授权。Owner choice 是独立的 typed Host-user command，必须绑定 exact proposal path/hash、`actor.kind=OWNER`、actor id、Run id、decision id 与 expected state version。只有 State Controller 能消费该命令并改变正式状态。

已安装的唯一公开 Skill 通过同一内部 runner API 暴露 `entry`、`dispatch`、`submit` 和 `owner-choice` 操作。该 API 是 Host Agent 的执行面，不增加用户可发现 Skill、独立 CLI、第二 Host 或远程平台。

## 路由

程序只路由 Owner 已明确选择的值，不选择产品结果：

- `STOP` → `CLOSED`
- `WAIT` → `WAITING_TRIGGER`
- `RESEARCH` → `evidence.collect`
- `EXPERIMENT` → `product.planning`，保留 experiment planning intent
- `COMMIT + NOW` → `product.planning`
- `COMMIT + FUTURE` → `ROADMAP_ONLY`

这些是状态/路线映射，不是语义判断，也不新增 Owner 重复确认 Node。

## Decision Ledger 与投影

每次 Owner choice 生成不可变 `DECISION_vN.json`，绑定 Agent proposal 与 Owner actor，并以 exact `supersedes` ref 连接上一版本。`current.json` 只是可替换指针。Product Plan、Roadmap 与 Product Changelog 是当前 Decision records 的确定性投影；它们不得扩写、改写或推断产品语义。新 Evidence 可以形成新 proposal 和新 Decision 版本，从而重审旧 `STOP/WAIT`。

## 不可突破边界

Agent 按公开 Skill 与原子 `INSTRUCTIONS.md` 完成 Product Discovery、Assumption Audit、Product Decision 建议、Planning、PRD 和 Review。Python 只做输入规范化、schema/validator、权限、exact refs/hashes、CAS、状态、既定路由、版本、持久化、机械节点与投影。合同/fixture 通过不等于真实 Agent 产品判断通过；没有 authenticated Host Agent trial 时该证据仍为 `NOT_RUN`。

## 明确不表示

本 ADR 不修改冻结的 V1.4/Roadmap，不引入签名服务、数据库或外部身份系统，也不把本地 `actor.kind=OWNER` 声明夸大为企业级认证。
