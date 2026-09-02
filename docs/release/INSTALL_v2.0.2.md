# Better Product Graph 2.0.2 安装指南 / Installation Guide

## 中文

`2.0.2` 是 BPG 2.0 的正式补丁 Release。只有以下条件同时满足时，才把本地安装视为该冻结发行身份：

1. 公开仓存在 annotated `v2.0.2` Tag，且 peeled target 等于精确公开快照提交；
2. GitHub Release 已发布且不是 Draft；
3. Release 同时提供两个 Host ZIP 与 `SHA256SUMS`；
4. 全新下载的三个文件通过 checksum，且与发行前冻结字节一致；
5. 安装后的版本、开发源码提交、Host、artifact hash、Core fingerprint、`dirty=false` 和 self-check `valid=true` 均与发行记录一致。

正式发行入口是 [`v2.0.2`](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.2)。本地源码或未校验的 ZIP 不能替代该 Release 身份。

### 正式 Release 资产

正式 `v2.0.2` GitHub Release 应包含且仅使用发行前已冻结、已验证的以下资产：

- `better-product-graph-codex-2.0.2.zip`
- `better-product-graph-claude-2.0.2.zip`
- `SHA256SUMS`

把三个重新下载的文件放在同一个空目录后运行：

```bash
shasum -a 256 -c SHA256SUMS
```

### Codex Marketplace

完成上述校验后使用：

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.2
codex plugin add better-product-graph@better-product-graph
```

### Claude Code Marketplace

完成上述校验后使用：

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

安装后打开新任务或新会话，并确认：只有一个 Better Product Graph 启用；版本为 `2.0.2`；build manifest 绑定精确开发提交且 `dirty=false`；Host、artifact hash 与 Core fingerprint 匹配；installed self-check 返回 `valid=true`；Plugin Contract 通过。

本补丁默认只生成 Markdown Local Handoff。HTML 与 Mermaid SVG 只有在显式启用 `LOCAL_HTML` 或 `LOCAL_RENDERED_VISUALS` 后才生成。正式 Reviewer 继续使用无继承父对话的独立上下文并读取精确 dispatch refs。`894/894 PASS` 不证明 Issue #7 的实际时间、上下文、Token 或 PRD 质量收益；可比 Golden Run 仍为 `NOT_RUN`。

## English

`2.0.2` is a formal BPG 2.0 patch Release. Treat a local installation as that frozen release identity only after all of the following are verified:

1. the public repository contains an annotated `v2.0.2` Tag whose peeled target is the exact public snapshot commit;
2. the GitHub Release is published and is not a draft;
3. the Release contains both Host ZIPs and `SHA256SUMS`;
4. freshly downloaded assets pass checksum verification and are byte-identical to the pre-release frozen assets; and
5. installed version, development source commit, Host, artifact hash, Core fingerprint, `dirty=false`, and self-check `valid=true` all match the release record.

The formal release entry is [`v2.0.2`](https://github.com/d-wwei/better-product-graph/releases/tag/v2.0.2). Local source or an unverified ZIP does not replace that Release identity.

The formal Release asset set is `better-product-graph-codex-2.0.2.zip`, `better-product-graph-claude-2.0.2.zip`, and `SHA256SUMS`. Verify freshly downloaded files with:

```bash
shasum -a 256 -c SHA256SUMS
```

After verification, install Codex from the pinned ref:

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v2.0.2
codex plugin add better-product-graph@better-product-graph
```

For Claude Code:

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

Open a new task or session after installation. Verify exactly one enabled BPG Plugin, version `2.0.2`, the exact clean development source identity, Host-specific artifact hash, shared Core fingerprint, installed self-check, and Plugin Contract.

This patch defaults Local Handoff to Markdown only. HTML and Mermaid SVG outputs are opt-in through `LOCAL_HTML` and `LOCAL_RENDERED_VISUALS`. Formal Reviewers continue to run without inherited parent conversation and consume exact dispatched refs. The `894/894 PASS` source result does not establish Issue #7 elapsed-time, context, Token-cost, or PRD-quality benefits; a comparable Golden Run remains `NOT_RUN`.
