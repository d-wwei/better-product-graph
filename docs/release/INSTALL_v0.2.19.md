# Better Product Graph 0.2.19 安装指南 / Installation Guide

## 中文

`0.2.19` 是 Developer Alpha。只安装 GitHub 公开仓库中 `v0.2.19` Release 里的冻结资产，不要用同版本本地重建包替代。

### Codex

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.19
codex plugin add better-product-graph@better-product-graph
```

### Claude Code

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

### 下载 ZIP 安装

Release 包含：

- `better-product-graph-codex-0.2.19.zip`
- `better-product-graph-claude-0.2.19.zip`
- `SHA256SUMS`

把 ZIP 和 `SHA256SUMS` 放到同一个空目录，先执行：

```bash
shasum -a 256 -c SHA256SUMS
```

只有对应 Host ZIP 显示 `OK` 时才继续。解压到新目录，再让 Host 从该目录安装；不要覆盖一个旧插件目录。

安装后打开新任务/新会话，检查：

- 只有一个 Better Product Graph 启用。
- 版本为 `0.2.19`。
- installed self-check 返回 `valid=true`。
- build manifest 中 `dirty=false`，且 Host 类型与安装包一致。

如果项目中已有旧 Run，直接说“继续 `<run-id>`”。只有精确命中登记恢复合同的旧状态才会原地恢复；其他组合仍返回 `BLOCKED_STALE`。

## English

`0.2.19` is a Developer Alpha. Install only the frozen assets attached to the public GitHub `v0.2.19` Release; do not substitute a local rebuild with the same version.

For Codex:

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.19
codex plugin add better-product-graph@better-product-graph
```

For Claude Code:

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

The Release contains Host-specific ZIPs and `SHA256SUMS`. Put them in one clean directory and run:

```bash
shasum -a 256 -c SHA256SUMS
```

Proceed only when the ZIP for your Host reports `OK`. Install from a newly extracted directory, open a new task/session, and verify one enabled BPG installation, version `0.2.19`, `dirty=false`, the correct Host identity, and `valid=true` from installed self-check.

For a legacy Run, ask the Host to continue its existing Run ID. Only an exact registered recovery contract can resume in place; every unknown stale combination remains `BLOCKED_STALE`.
