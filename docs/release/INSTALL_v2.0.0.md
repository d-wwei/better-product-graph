# Better Product Graph 2.0.0 安装指南 / Installation Guide

## 中文

`2.0.0` 是 BPG 新架构的首个正式 Developer Alpha Release。普通 Better Product Graph 请求默认进入 BPG 2.0 单 PRD 主链路；旧 0.x 入口已移除。

### Codex

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.0
codex plugin add better-product-graph@better-product-graph
```

### Claude Code

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

### 下载 ZIP 安装

GitHub Release 包含：

- `better-product-graph-codex-2.0.0.zip`
- `better-product-graph-claude-2.0.0.zip`
- `SHA256SUMS`

把三个文件放在同一空目录后校验：

```bash
shasum -a 256 -c SHA256SUMS
```

只有对应 Host ZIP 显示 `OK` 时才继续。安装后请打开新任务或新会话，并确认：

- 只有一个 Better Product Graph 启用；
- Plugin version 为 `2.0.0`；
- source commit 为 `c79eaff4ba59de74bb8d9e572d6bc800eec77720`；
- build manifest 中 `dirty=false`；
- installed `self-check` 返回 `valid=true`。

本版不迁移或续跑旧 Run。多 PRD、完整 Product Evals Generator、外部交付、研发接收、实现测试和产品效果验证不属于本 Release 的已完成声明。

## English

`2.0.0` is the first formal Developer Alpha Release of the replacement BPG architecture. Ordinary Better Product Graph requests now enter the BPG 2.0 single-PRD path by default; the legacy 0.x entry has been removed.

Install Codex from the `v2.0.0` marketplace ref:

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.0
codex plugin add better-product-graph@better-product-graph
```

For Claude Code:

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

The GitHub Release contains both Host ZIPs and `SHA256SUMS`. Verify them with:

```bash
shasum -a 256 -c SHA256SUMS
```

After installation, open a new task/session and verify one enabled BPG Plugin, version `2.0.0`, source commit `c79eaff4ba59de74bb8d9e572d6bc800eec77720`, `dirty=false`, and `valid=true` from installed self-check.

This Release does not migrate legacy Runs and does not claim multi-PRD planning, a complete Product Evals Generator, external delivery, engineering receipt, implementation tests, or product-effect validation.
