# Better Product Graph 2.0.1 安装指南 / Installation Guide

## 中文

`2.0.1` 是 BPG 2.0 Review、Ready 与 Handoff 完整性热修复。它保持单 PRD Developer Alpha 方法范围，不迁移或续跑旧 Run。

只有以下条件同时满足时，才把安装身份视为冻结：

1. `v2.0.1` Tag 与 GitHub Release 已发布；
2. Release 同时提供两个 Host ZIP 与 `SHA256SUMS`；
3. 下载文件通过 checksum；
4. 安装后 identity 与 `RELEASE_SOURCE.json` 一致。

### Codex Marketplace

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.1
codex plugin add better-product-graph@better-product-graph
```

### Claude Code Marketplace

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

### Release ZIP

正式 GitHub Release 应包含：

- `better-product-graph-codex-2.0.1.zip`
- `better-product-graph-claude-2.0.1.zip`
- `SHA256SUMS`

将三个文件放在同一空目录后运行：

```bash
shasum -a 256 -c SHA256SUMS
```

只有对应 Host ZIP 显示 `OK` 时才继续。安装后打开新任务或新会话，并确认：

- 只有一个 Better Product Graph 启用；
- Plugin version 为 `2.0.1`；
- build manifest 的 source commit 等于 `RELEASE_SOURCE.json` 中最终记录的 `artifact_build_source_commit`；
- build manifest 中 `dirty=false`；
- installed `self-check` 返回 `valid=true`；
- Host、artifact hash 与 Core fingerprint 和最终 Release 记录一致。

本版本不运行 Product Evals applicability、Pack generation 或 Eval Spec Review；这些未来 2.2 能力不阻断 BPG 2.0 Ready 或 Local Handoff。Product Evals 执行、外部交付、研发接收、实现测试和产品效果验证均不因安装而成立。

## English

`2.0.1` is an integrity hotfix for BPG 2.0 Review, Ready, and Handoff. It keeps the single-PRD Developer Alpha method scope and does not migrate or resume legacy Runs.

Treat an installation identity as frozen only when all of these are true:

1. the `v2.0.1` Tag and GitHub Release are published;
2. the Release contains both Host ZIPs and `SHA256SUMS`;
3. the downloaded files pass checksum verification; and
4. installed identity matches `RELEASE_SOURCE.json`.

Install Codex from the pinned marketplace ref:

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.1
codex plugin add better-product-graph@better-product-graph
```

For Claude Code:

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

The formal GitHub Release should contain `better-product-graph-codex-2.0.1.zip`, `better-product-graph-claude-2.0.1.zip`, and `SHA256SUMS`. Verify them with:

```bash
shasum -a 256 -c SHA256SUMS
```

After installation, open a new task/session and verify one enabled BPG Plugin, version `2.0.1`, the exact source commit recorded by `RELEASE_SOURCE.json`, `dirty=false`, `valid=true` from self-check, and the final Host artifact hash and Core fingerprint.

This version does not run Product Evals applicability, Pack generation, or Eval Spec Review; those future 2.2 capabilities do not block BPG 2.0 Ready or Local Handoff. Installation does not establish Product Evals execution, external delivery, engineering receipt, implementation tests, or product-effect validation.
