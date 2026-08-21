# Better Product Graph 0.2.0 安装指南 / Installation Guide

- Release channel: Developer Alpha
- Hosts: Codex, Claude Code
- License: Apache-2.0
- Verified locally: macOS, Python 3, Git
- Not yet claimed: Windows/Linux runtime verification, production stability, automatic Bootstrap

## 中文

### 1. 安装前

你需要：

- Git；
- Python 3；
- 已安装并登录的 Codex CLI 或 Claude Code；
- 一个准备保存产品规划产物的 Git 项目目录。

本版本不会自动 Bootstrap 项目。请先进入正确的项目根目录，再开始 Better Product Graph Run。

### 2. Codex：从公开 Marketplace 安装

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.0
codex plugin add better-product-graph@better-product-graph
```

完成后打开一个新的 Codex 任务，直接说：

```text
用 Better Product Graph 分析这个产品想法：……
```

也可以使用显式入口：

```text
$better-product-graph new <你的产品信号>
```

### 3. Claude Code：从公开 Marketplace 安装

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

完成后启动一个新的 Claude Code 会话，直接描述需求，或使用：

```text
/better-product-graph:better-product-graph new <你的产品信号>
```

### 4. 从 GitHub Release ZIP 固定安装

如果你需要固定 `0.2.0`，下载对应 Host ZIP 和 `SHA256SUMS`，然后校验：

```bash
shasum -a 256 -c SHA256SUMS
```

Codex：

```bash
mkdir -p bpg-codex-0.2.0
unzip better-product-graph-codex-0.2.0.zip -d bpg-codex-0.2.0
codex plugin marketplace add "$PWD/bpg-codex-0.2.0"
codex plugin add better-product-graph@better-product-graph
```

Claude Code：

```bash
mkdir -p bpg-claude-0.2.0
unzip better-product-graph-claude-0.2.0.zip -d bpg-claude-0.2.0
claude plugin marketplace add "$PWD/bpg-claude-0.2.0" --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

请选择与当前 Host 对应的 ZIP。即使两个包共享 Core，也不能把其中一个当成另一个 Host 的安装包。

### 5. 检查是否安装成功

```bash
codex plugin list
# 或
claude plugin list
```

列表中应出现 `better-product-graph@better-product-graph`。安装或升级后请使用新任务/新会话，让 Host 重新加载 Skill。

### 6. 更新与卸载

Codex：

```bash
codex plugin marketplace upgrade better-product-graph
codex plugin add better-product-graph@better-product-graph

codex plugin remove better-product-graph@better-product-graph
codex plugin marketplace remove better-product-graph
```

Claude Code：

```bash
claude plugin marketplace update better-product-graph
claude plugin update better-product-graph@better-product-graph --scope user

claude plugin uninstall better-product-graph@better-product-graph --scope user
claude plugin marketplace remove better-product-graph --scope user
```

卸载插件不会自动删除项目中的 `.better-product-graph/`。这里保存 Run、证据、Decision、PRD 版本和本地 Handoff；请在确认不再需要审计或恢复后自行归档或删除。

### 7. Developer Alpha 的已知边界

- Bootstrap 将在下一个 Alpha 提供；本版不会自动理解一个陌生项目的完整上下文。
- Handoff 是本地交接包，不代表研发已接收、组织已批准或测试已通过。
- Reviewer 只提供建议，不拥有阻塞权。
- Claude Code 的关键可写、权限、恢复和 Handoff 路径已有真实 Host 证据；只读 Help 的 runner 证据仍不完整。
- 自然语言自动选择和真实 Product Judgment 还需要更多公开试点校准。

遇到问题，请使用仓库中的 Bug、产品反馈或安装问题 Issue 表单。安全漏洞不要公开提交，请使用 GitHub 的私密漏洞反馈入口。

---

## English

### 1. Prerequisites

You need:

- Git;
- Python 3;
- an installed and authenticated Codex CLI or Claude Code;
- a Git project directory where Better Product Graph may keep its planning artifacts.

This release does not bootstrap an unfamiliar project automatically. Enter the intended project root before starting a Run.

### 2. Install for Codex from the public marketplace

```bash
codex plugin marketplace add d-wwei/better-product-graph --ref v0.2.0
codex plugin add better-product-graph@better-product-graph
```

Start a new Codex task and say:

```text
Use Better Product Graph to analyze this product idea: ...
```

Or use the explicit entry:

```text
$better-product-graph new <your product signal>
```

### 3. Install for Claude Code from the public marketplace

```bash
claude plugin marketplace add d-wwei/better-product-graph --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

Start a new Claude Code session and describe the need, or use:

```text
/better-product-graph:better-product-graph new <your product signal>
```

### 4. Install the pinned GitHub Release ZIP

Download the ZIP for your Host together with `SHA256SUMS`, then verify it:

```bash
shasum -a 256 -c SHA256SUMS
```

Codex:

```bash
mkdir -p bpg-codex-0.2.0
unzip better-product-graph-codex-0.2.0.zip -d bpg-codex-0.2.0
codex plugin marketplace add "$PWD/bpg-codex-0.2.0"
codex plugin add better-product-graph@better-product-graph
```

Claude Code:

```bash
mkdir -p bpg-claude-0.2.0
unzip better-product-graph-claude-0.2.0.zip -d bpg-claude-0.2.0
claude plugin marketplace add "$PWD/bpg-claude-0.2.0" --scope user
claude plugin install better-product-graph@better-product-graph --scope user
```

Choose the ZIP for your Host. The bundles share one Core, but neither bundle can be installed as the other Host’s plugin.

### 5. Verify the installation

```bash
codex plugin list
# or
claude plugin list
```

The list should include `better-product-graph@better-product-graph`. Open a new task or session after installation or upgrade so the Host reloads the Skill.

### 6. Update or uninstall

Codex:

```bash
codex plugin marketplace upgrade better-product-graph
codex plugin add better-product-graph@better-product-graph

codex plugin remove better-product-graph@better-product-graph
codex plugin marketplace remove better-product-graph
```

Claude Code:

```bash
claude plugin marketplace update better-product-graph
claude plugin update better-product-graph@better-product-graph --scope user

claude plugin uninstall better-product-graph@better-product-graph --scope user
claude plugin marketplace remove better-product-graph --scope user
```

Uninstalling the plugin does not delete `.better-product-graph/` from your project. That directory contains Runs, evidence, decisions, PRD versions, and local handoffs. Archive or remove it only when you no longer need audit or recovery.

### 7. Developer Alpha boundaries

- Bootstrap is planned for the next Alpha. This release does not automatically build complete context for an unfamiliar project.
- A Handoff is a local package. It does not mean engineering accepted it, the organization approved it, or testing passed.
- Reviewers are advisory only.
- Claude Code has real Host evidence for the tested writable, permission, recovery, and Handoff paths. Runner evidence for read-only Help is still incomplete.
- Natural-language auto-selection and real Product Judgment need broader public trials.

Use the repository’s Bug, product-feedback, or installation Issue forms for support. Do not disclose vulnerabilities in a public Issue; use GitHub’s private vulnerability-reporting entry instead.
