# Better Product Graph 0.2.20 安装指南 / Installation Guide

## 中文

`0.2.20` 是 Developer Alpha。只安装公开仓库 `v0.2.20` GitHub Release 的冻结资产，不要用同版本本地重建包替代。

### Codex

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.20
codex plugin add better-product-graph@better-product-graph
```

### Claude Code

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

### 下载 ZIP 安装

Release 包含：

- `better-product-graph-codex-0.2.20.zip`
- `better-product-graph-claude-0.2.20.zip`
- `SHA256SUMS`

把 ZIP 和 `SHA256SUMS` 放进同一个空目录，然后执行：

```bash
shasum -a 256 -c SHA256SUMS
```

只有对应 Host ZIP 显示 `OK` 时才继续。安装后打开新任务或新会话，并确认：

- 只有一个 Better Product Graph 启用；
- 版本为 `0.2.20`；
- installed self-check 返回 `valid=true`；
- build manifest 中 `dirty=false`，Host 类型与安装包一致。

普通 BPG 请求继续走 0.x 路径。要测试本版的新 Alpha，请在一个具体项目中明确输入：

```text
$better-product-graph alpha <一个真实产品需求、反馈或问题>
```

也可以直接说“请用 BPG 2.0 Alpha 处理这个产品问题：……”。Alpha 只创建新的 `.better-product-graph/v2/` Run，不会迁移或续跑旧 Run。

## English

`0.2.20` is a Developer Alpha. Install only the frozen assets attached to the public GitHub `v0.2.20` Release; do not substitute a local rebuild with the same version.

For Codex:

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.20
codex plugin add better-product-graph@better-product-graph
```

For Claude Code:

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

The Release contains both Host ZIPs and `SHA256SUMS`. Put them in one clean directory and run:

```bash
shasum -a 256 -c SHA256SUMS
```

Proceed only when the ZIP for your Host reports `OK`. Open a new task/session and verify one enabled BPG installation, version `0.2.20`, `dirty=false`, the correct Host identity, and `valid=true` from installed self-check.

Ordinary BPG requests keep using the 0.x path. To test the new Alpha in one specific project, explicitly enter:

```text
$better-product-graph alpha <a real product requirement, feedback item, or issue>
```

The Alpha creates only a fresh `.better-product-graph/v2/` Run and never migrates or resumes a legacy Run.
