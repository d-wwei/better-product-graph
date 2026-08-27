# Better Product Graph 0.2.18 安装指南 / Installation Guide

- Release channel: Developer Alpha
- Intended tag: `v0.2.18`
- Hosts: Codex, Claude Code
- License: Apache-2.0
- Artifact build source: `16d8ce48b999f85d34747afb94ff255d40220c78` (`dirty=false`)

> 只有 GitHub 上的 `v0.2.18` Tag、对应 Release 和下列 exact ZIP 同时存在时，才按本指南安装。不要用同版本的本地重建包替代冻结发行资产。

## 中文

### 1. 下载并校验

从 `d-wwei/better-product-graph` 的 `v0.2.18` Release 下载与你的 Host 对应的 ZIP 和 `SHA256SUMS`。

冻结资产：

```text
163d6c3f65047af4e514d864eead60f49e816a5112fc1be15200f1520b1bf9f5  better-product-graph-codex-0.2.18-a.zip
4c73c3a38f77fa6e6610cbc56abcbad8e9f65e445b6290415da24ad042f28919  better-product-graph-claude-0.2.18-a.zip
```

校验：

```bash
shasum -a 256 -c SHA256SUMS
```

任何 checksum 不一致都应停止安装，不要继续解压或覆盖现有版本。

### 2. Codex

从公开 Marketplace 安装固定 Tag：

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.18
codex plugin add better-product-graph@better-product-graph
```

或安装已校验的 Release ZIP：

```bash
mkdir -p bpg-codex-0.2.18
unzip better-product-graph-codex-0.2.18-a.zip -d bpg-codex-0.2.18
codex plugin marketplace add "$PWD/bpg-codex-0.2.18"
codex plugin add better-product-graph@better-product-graph
```

### 3. Claude Code

从公开 Marketplace 安装：

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

或安装已校验的 Release ZIP：

```bash
mkdir -p bpg-claude-0.2.18
unzip better-product-graph-claude-0.2.18-a.zip -d bpg-claude-0.2.18
claude plugin marketplace add "$PWD/bpg-claude-0.2.18" --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

### 4. 安装后验证

安装或升级后请打开一个新任务/新会话，让 Host 重新加载 Skill。

```bash
codex plugin list
# 或
claude plugin list
```

列表应包含 `better-product-graph@better-product-graph`。安装副本的 self-check 还应显示：

```text
version: 0.2.18
source commit: 16d8ce48b999f85d34747afb94ff255d40220c78
Codex artifact: sha256:5f5f9e68cbccab58726381ae2e145356d7ce995d054286639e4aacc279bfa737
Claude artifact: sha256:37d39b5dab0f95d58be47a93b9f7e7e3ce9e8e63764ae01185e07ef32aac93f8
shared Core: sha256:20b8fe2e26ce0e49172e36c61ec014bbfac857d675644533aae08a86aa0840b5
```

请选择与你当前 Host 对应的 artifact identity。两个 ZIP 共享 Core，但不能互换。

### 5. 使用与边界

直接用自然语言描述产品想法、用户反馈或线上 Issue；也可以使用显式入口：

```text
$better-product-graph new <你的产品信号>
/better-product-graph:better-product-graph new <你的产品信号>
```

Better Product Graph 会在项目内保存 `.better-product-graph/` Run、证据和版本化产物。卸载插件不会自动删除这些资料。

本版本仍是 Developer Alpha。Agent Eval 已通过，但观察式真人读者验证为 `NOT_RUN`；本地 Handoff 不代表研发已接收、测试已通过或组织已批准。

---

## English

Install only when the public `v0.2.18` tag, its GitHub Release, and the exact ZIP for your Host all exist. Do not replace the gated bytes with a local rebuild under the same version.

### 1. Download and verify

Download the Host ZIP and `SHA256SUMS` from the `v0.2.18` Release of `d-wwei/better-product-graph`, then run:

```bash
shasum -a 256 -c SHA256SUMS
```

Expected ZIP hashes:

```text
163d6c3f65047af4e514d864eead60f49e816a5112fc1be15200f1520b1bf9f5  better-product-graph-codex-0.2.18-a.zip
4c73c3a38f77fa6e6610cbc56abcbad8e9f65e445b6290415da24ad042f28919  better-product-graph-claude-0.2.18-a.zip
```

Stop if any checksum differs.

### 2. Codex

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.18
codex plugin add better-product-graph@better-product-graph
```

Or install the verified ZIP:

```bash
mkdir -p bpg-codex-0.2.18
unzip better-product-graph-codex-0.2.18-a.zip -d bpg-codex-0.2.18
codex plugin marketplace add "$PWD/bpg-codex-0.2.18"
codex plugin add better-product-graph@better-product-graph
```

### 3. Claude Code

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

Or install the verified ZIP:

```bash
mkdir -p bpg-claude-0.2.18
unzip better-product-graph-claude-0.2.18-a.zip -d bpg-claude-0.2.18
claude plugin marketplace add "$PWD/bpg-claude-0.2.18" --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

### 4. Verify

Open a new task or session after installation, then run `codex plugin list` or `claude plugin list`. The installed self-check must bind version `0.2.18`, build source `16d8ce48b999f85d34747afb94ff255d40220c78`, the Host-specific artifact hash above, and shared Core fingerprint `20b8fe2e26ce0e49172e36c61ec014bbfac857d675644533aae08a86aa0840b5`.

This remains a Developer Alpha. Agent Eval passed, but observed human-reader validation is `NOT_RUN`. A local Handoff does not mean engineering accepted it, tests passed, or organizational approval was granted.
