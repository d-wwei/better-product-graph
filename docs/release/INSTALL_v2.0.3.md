# Better Product Graph 2.0.3 安装指南 / Installation Guide

## 中文

`v2.0.3` 是 BPG 2.0 的正式发行身份元数据修正版，并已 supersede `v2.0.2` 作为当前安装身份。`v2.0.2` Tag、Release 和资产保持不可变；其 ZIP、运行内容及 ZIP 内 `build-manifest.json` 正确，错误仅存在于公开 `RELEASE_SOURCE.json` 的两个 Host-specific execution-contract fingerprint 字段。

冻结的 `v2.0.2` 正确边界为：

- 共同 Core：`sha256:a97027f2c614f9f97cef7640a3b3a4d8284e8f10bd0fc486f666712a562b14ec`
- Codex execution contract：`sha256:8bab78b78923e75f659e1a7a3020f573379a6466dc24693ec1a9239d95e4d46d`
- Claude execution contract：`sha256:a58a6ef878f75051addbd923da06c73ae8ffdfe98b83ad8790fca63087964abc`

正式发行入口是 [`v2.0.3`](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.3)。只有以下条件同时满足时，才把本地安装视为该冻结发行身份：

1. 公开仓存在 annotated `v2.0.3` Tag，且 peeled target 等于精确公开快照提交；
2. GitHub Release 已发布且不是 Draft；
3. Release 同时提供两个 Host ZIP 与 `SHA256SUMS`；
4. 全新下载的三个文件通过 checksum，且与发行记录一致；
5. 两个 ZIP 内 `build-manifest.json` 的版本均为 `2.0.3`、`dirty=false`，共同 `core_tree_fingerprint` 相同，Host-specific `execution_contract_fingerprint` 分别匹配各自 Host 且彼此不同；
6. 安装后的 Host、artifact hash、开发源码身份、自检 `valid=true` 和 Plugin Contract 均与发行记录一致。

### 正式 Release 资产

正式 `v2.0.3` GitHub Release 包含：

- `better-product-graph-codex-2.0.3.zip`
- `better-product-graph-claude-2.0.3.zip`
- `SHA256SUMS`

把三个重新下载的文件放在同一个空目录后运行：

```bash
shasum -a 256 -c SHA256SUMS
```

### Codex Marketplace

完成上述校验后使用：

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.3
codex plugin add better-product-graph@better-product-graph
```

### Claude Code Marketplace

完成上述校验后使用：

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

本修正版不改变运行语义、Agent-first 内容或 Issue #1–#7 结论。不要把 `v2.0.2` 资产改名或重新标记为 `v2.0.3`；安装身份验证也不能替代 Product Evals、研发测试或产品效果验证。

## English

`v2.0.3` is the formal BPG 2.0 release identity metadata correction and supersedes `v2.0.2` as the current install identity. The `v2.0.2` Tag, Release, and assets remain immutable. Its ZIPs, runtime content, and embedded `build-manifest.json` files are correct; only the two Host-specific execution-contract fingerprint fields in the public `RELEASE_SOURCE.json` are wrong.

The correct frozen `v2.0.2` boundary is:

- shared Core: `sha256:a97027f2c614f9f97cef7640a3b3a4d8284e8f10bd0fc486f666712a562b14ec`
- Codex execution contract: `sha256:8bab78b78923e75f659e1a7a3020f573379a6466dc24693ec1a9239d95e4d46d`
- Claude execution contract: `sha256:a58a6ef878f75051addbd923da06c73ae8ffdfe98b83ad8790fca63087964abc`

The formal release entry is [`v2.0.3`](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.3). Treat a local installation as that frozen release identity only after verifying the annotated Tag and peeled public snapshot target, published non-draft GitHub Release, both Host ZIPs, `SHA256SUMS`, fresh-download checksums, and the installed identity.

The formal asset set is `better-product-graph-codex-2.0.3.zip`, `better-product-graph-claude-2.0.3.zip`, and `SHA256SUMS`. Verify freshly downloaded files with:

```bash
shasum -a 256 -c SHA256SUMS
```

Verify both embedded `build-manifest.json` files: version `2.0.3`; `dirty=false`; Host and artifact hash match the Release record; `core_tree_fingerprint` is shared; `execution_contract_fingerprint` matches its own Host and differs across Hosts; installed self-check returns `valid=true`; and the Plugin Contract passes.

After verification, install Codex from the pinned ref:

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.3
codex plugin add better-product-graph@better-product-graph
```

For Claude Code:

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

This correction does not change runtime semantics, Agent-first content, or the Issue #1–#7 conclusions. Do not rename or relabel `v2.0.2` assets as `v2.0.3`; installation identity checks do not substitute for Product Evals, engineering tests, or product-effect validation.
