# Better Product Graph

这是 Better Product Graph 的正式成果仓库。研发分支、原始审计、项目记忆、施工文档和实验过程保存在私有研发仓库；这里发布从研发真源生成的可安装快照。

当前正式内容：

- Better Product Graph 双 Host 本地发行版：`0.2.0`
- 当前产品 PRD：[Better Product Graph 产品需求文档 v1.5](docs/released/prd/BETTER_PRODUCT_GRAPH_PRD.md)
- 当前 Roadmap：[Roadmap v0.13](docs/roadmap/BETTER_PRODUCT_GRAPH_ROADMAP_v0.13.md)
- 默认 PRD Template Profile：`general@0.2.0`
- 核心设计决策：[docs/decisions](docs/decisions)
- 发布来源与研发 commit：[RELEASE_SOURCE.json](RELEASE_SOURCE.json)

Better Product Graph 是一个 local-first、skills-only 的产品规划插件。它把 Idea、用户反馈和 online Issue 组织成可追溯的 Evidence、产品判断、Outcome-first Plan、版本化 PRD，以及 exact local Handoff；它不会强迫每个 Signal 都进入 PRD。

## 双 Host 结构

Codex 与 Claude Code 使用同一个 Product Graph Core、Controller、Schema、Validator、Gate 和原子节点说明，只在 Host manifest、公开入口和安装方式上有薄适配。每个包只包含一个 Host：

- Codex：`host-adapters/codex/`
- Claude Code：`host-adapters/claude/`

两个 Host 的安装包必须具有相同 `core_tree_fingerprint`，但各自的 artifact hash 和 ZIP hash 不同。

## 仓库目录

- `config/`：双 Host 构建与发布配置。
- `src/`：Graph 运行程序和内置产品工作规则。
- `scripts/`：构建、打包、模板同步、隔离安装和 Host 验证工具。
- `host-adapters/`：Codex 与 Claude 的薄 Host 入口。
- `templates/`：当前正式通用 PRD 模板与输出合同。
- `evals/`、`tests/`：正式机械合同、产品夹具和回归测试。
- `docs/`：当前正式 PRD、Roadmap、实施基线和已采纳核心决策。

## 本地验证

要求 Python 3、Git，以及需要验证的 Host CLI。产品运行时只使用 Python 标准库。

```bash
python3 -m unittest discover -s tests -t . -v

python3 scripts/package_plugin.py better-product-graph-codex-0.2.0.zip --host codex --require-clean --json
python3 scripts/fresh_install_smoke.py better-product-graph-codex-0.2.0.zip --work-root /tmp/bpg-codex-smoke --json

python3 scripts/package_plugin.py better-product-graph-claude-0.2.0.zip --host claude --require-clean --json
python3 scripts/claude_fresh_install_smoke.py better-product-graph-claude-0.2.0.zip --work-root /tmp/bpg-claude-smoke
```

完整安装说明见 [LOCAL_INSTALL_v0.2.md](docs/release/LOCAL_INSTALL_v0.2.md)。

## 使用入口

两个 Host 都支持同一组 11 个 intents：`new`、`capture`、`inbox`、`status`、`resume`、`pause`、`handoff`、`connectors`、`audit`、`interview`、`help`。

- Codex：`$better-product-graph <intent>`
- Claude：`/better-product-graph:better-product-graph <intent>`

## 关键边界

- Host Agent 负责研究、访谈、质疑和产品语义；Python 只负责规范化、权限、验证、状态、恢复、版本和本地落盘。
- Reviewer 为 `ADVISORY_ONLY`；没有 Reviewer 阻塞权或重复 Owner 确认。
- Handoff 只生成 local packet，不声称研发已接收、测试已通过或组织已批准。
- 没有 MCP、服务、数据库、队列、daemon、真实外部 Connector 或 public marketplace 发布。
- Claude `0.2.0` 的唯一一次 authenticated Host trial 为 6/7：关键可写、权限、恢复和 Handoff 路径通过；只读 Help 没有调用 runner，因此完整 Host 状态是 `PARTIAL`，不是 PASS。
- Auto-selection 与 Product Golden Agent judgment 仍为 `NOT_RUN`。
