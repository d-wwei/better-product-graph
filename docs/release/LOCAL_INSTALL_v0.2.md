# Better Product Graph Local Install v0.2

- Status: Released dual-host procedure
- Date: 2026-08-21
- Applies to: `better-product-graph` 0.2.0
- Supersedes: `LOCAL_INSTALL_v0.1.md`

## Codex

```bash
python3 scripts/package_plugin.py better-product-graph-codex-0.2.0.zip --host codex --require-clean --json
python3 scripts/fresh_install_smoke.py better-product-graph-codex-0.2.0.zip --work-root /tmp/bpg-codex-smoke --json
```

Smoke 使用隔离 `CODEX_HOME`，验证 marketplace add、install、installed identity、Plugin Contract、`new`、uninstall 和 rollback，不修改全局安装。

## Claude Code

```bash
python3 scripts/package_plugin.py better-product-graph-claude-0.2.0.zip --host claude --require-clean --json
python3 scripts/claude_fresh_install_smoke.py better-product-graph-claude-0.2.0.zip --work-root /tmp/bpg-claude-smoke
```

Smoke 使用隔离 `CLAUDE_CONFIG_DIR`，验证 `plugin validate --strict`、install、installed identity、Plugin Contract、`new`、uninstall 和 rollback，不修改全局安装。

两个 Host 必须分别打包；单个 artifact 不能同时包含 `.codex-plugin` 与 `.claude-plugin`。同一 source commit 的两个包应具有相同 `core_tree_fingerprint`。

## 证据边界

隔离安装 PASS 只证明安装与机械合同。Authenticated Host、自然语言 Auto-selection 和 Product Judgment 必须单独运行并单独报告，不能从 smoke 推断。
