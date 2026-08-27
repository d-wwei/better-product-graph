# Better Product Graph 0.2.19 — Developer Alpha

`0.2.19` 是 `0.2.18` 的兼容性热修复。它不改写作规范、Reviewer 语义或产品判断，只解决已审计的旧 Run 在合同升级后只能 `BLOCKED_STALE`、无法恢复的问题。

## 本版改了什么

- 为五种已审计的旧状态增加 exact allowlist 恢复合同；未登记的组合仍只读拒绝。
- 保留原 Run ID、Event、Attempt、Receipt 和 Artifact；旧的未消费工作单标记为 `RETIRED_STALE`，不删除也不改写。
- 只在完整状态指纹、事件链、历史 authority、Instruction 和 Artifact 同时精确匹配时恢复。
- 缺失的 Claude Adapter 候选稿只能从登记的 Git commit/tree/blob 恢复；路径、mode、Hash、symlink、覆盖和并发冲突全部 fail closed。
- Ready Receipt 改为 Attempt-scoped 新代际；旧固定路径 Receipt 保留但不能重新获得当前 authority。
- 同时 Resume 同一旧 Run 时，`ACTIVE` 与 `PAUSED` 的正反时序都只会得到一份当前有效工作单；不相关状态变化仍拒绝。

## 验证摘要

- 开发源码全量：`773 tests / OK`。
- 四种并发 Resume 时序：各 `50/50 PASS`。
- focused stale recovery：`12 tests × 10` 轮全部通过。
- 六个历史 Run 均在完整临时副本中保留原 Run ID 并到达当前合法工作单。
- Codex 与 Claude Code 确定性打包、隔离安装、self-check、合同、卸载与回滚门禁通过。
- Writing Profile、Guide、Reviewer Instruction、Schema 与冻结 Eval 合同字节未变；`0.2.18` 的两组 `27/27` 语义证据继续适用，本版没有重跑 Reviewer。

## 不应误解为

- 恢复成功不代表旧 PRD 已 Ready、已 Release、已实现或已测试。
- `0.2.19` 没有引入通用 `force` / `ignore-stale` 开关。
- 真人读者验证、认证 Host Agent 与真实 Product Golden 判断仍是 `NOT_RUN`。

详细技术边界见 [旧 Run 精确恢复热修复](../engineering/BETTER_PRODUCT_GRAPH_STALE_RUN_RECOVERY_v0.2.19.md)。

---

`0.2.19` is a compatibility hotfix for `0.2.18`. It adds exact, fail-closed recovery for five audited legacy Run states while preserving the same Run ID and append-only history. Unknown stale combinations remain blocked. The Writing Reviewer semantic contract is unchanged.

Verification includes `773/773` source tests, four concurrent Resume interleavings at `50/50` each, six historical Run copies, and deterministic Codex/Claude package and isolated-install gates. Recovery does not imply PRD Ready, implementation, testing, or external approval. Human-reader validation and Product Golden judgment remain `NOT_RUN`.
