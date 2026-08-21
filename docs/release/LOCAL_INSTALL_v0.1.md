# Better Product Graph Local Install v0.1

- Status: Candidate procedure
- Date: 2026-08-20
- Applies to: Plugin `better-product-graph` version `0.1.0`
- Supersedes: none

## 结论与下一步

本候选可从 clean exact commit 构建为确定性 ZIP，并安装到一次性、隔离的 `CODEX_HOME` 做 discovery、identity、contract、activation、卸载和回滚 smoke。默认流程不会接触用户的全局 Codex 安装，也不会发布到公共 marketplace。

先运行完整测试与 repair verifier，再在 clean worktree 上打包：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/verify_audit_repairs.py
git diff --check
git status --short
python3 scripts/package_plugin.py .assistant/work/release/better-product-graph-0.1.0-a.zip --require-clean --json
python3 scripts/package_plugin.py .assistant/work/release/better-product-graph-0.1.0-b.zip --require-clean --json
shasum -a 256 .assistant/work/release/better-product-graph-0.1.0-*.zip
```

两份 ZIP 必须 byte-identical。包根必须直接包含 `.codex-plugin/plugin.json`、`build-manifest.json`、`skills/better-product-graph/SKILL.md` 和 `assets/`；不能再包一层产品目录。

## 隔离 fresh install

```bash
python3 scripts/fresh_install_smoke.py \
  .assistant/work/release/better-product-graph-0.1.0-a.zip \
  --codex-bin /Applications/ChatGPT.app/Contents/Resources/codex \
  --work-root .assistant/work/fresh-install-v0.1 \
  --json
```

脚本创建本地 marketplace manifest，在 `.assistant/work/fresh-install-v0.1/codex-home` 内执行官方 Codex CLI 的 marketplace add、plugin add、plugin remove 和 rollback。所有子进程显式设置这个隔离 `CODEX_HOME`。安装后使用 packaged runner 重算 inventory/artifact identity，运行 Plugin Contract，并执行一次 `new` 激活。

若要重复 smoke，选择新的空 `--work-root`；脚本拒绝复用非空目录，以避免混入旧安装状态。

## 安装后入口

Host 通过唯一公开 Skill 调用内部 runner。面向 Host 的操作为：

- `entry`：解析 11 intents 并执行 preflight/activation。
- `dispatch`：返回当前 exact instruction、input/resource hashes 和 producer contract。
- `submit`：提交 Host-Agent Node Result，经 Controller validation 后 transition 并返回下一 dispatch。
- `owner-choice`：提交绑定 proposal hash、Owner actor 和 state version 的独立 choice command。

当下一节点是 deterministic Gate 时，runner 不向 Host 暴露可伪造的 `DETERMINISTIC_PROGRAM` submit。它在同一 surface 内部重取 exact committed result/refs，执行 Controller validator，持久化 Gate result，再继续到下一 Agent dispatch 或 local terminal。Review companion 由 `review.finalize` 的 recoverable Candidate-generation transaction 生成，不由 Host 写入。

这些是安装 Skill 的内部 Host API，不是另一个用户 CLI 或独立平台。

## 卸载与恢复

隔离 smoke 会先执行 `plugin remove` 并确认 installed path 消失，再从同一 local marketplace 安装同一 ZIP、复算 identity。这验证本地安装回滚，不创建 tag、remote、public release 或全局安装。

## 证据边界

`PASS` 只适用于命令实际验证的机械合同。Authenticated Host Agent trial 和真实 Product Golden judgment 不由此脚本执行，必须报告为 `NOT_RUN`。Connector 远程发送、接收与批准也不在本版本范围内。
