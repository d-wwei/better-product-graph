# Better Product Graph

这是 Better Product Graph 的正式成果仓库。研发过程、审计原始材料、施工文档、实验 Adapter 和完整分支历史保存在私有研发仓库；本仓库只接收经过选择的单向发布快照。

当前仓库内容：

- Codex Plugin 本地候选版本：`0.1.20`
- 当前正式产品 PRD：[Better Product Graph 产品需求文档 v1.5](docs/released/prd/BETTER_PRODUCT_GRAPH_PRD.md)
- 冻结实施 Roadmap 基线：[Roadmap v0.12](docs/roadmap/BETTER_PRODUCT_GRAPH_ROADMAP_v0.12.md)
- 核心设计决策：[docs/decisions](docs/decisions)
- 发布来源与研发 commit：[RELEASE_SOURCE.json](RELEASE_SOURCE.json)

Roadmap v0.12 的状态表是 2026-08-20 的冻结规划快照，不代表 0.1.20 的当前实现状态；新版 Roadmap 尚未由产品负责人确认，因此没有在这里冒充正式版本。

Better Product Graph 是一个 local-first、skills-only 的 Codex Plugin。它把 Idea、用户反馈和 online Issue 组织成可追溯的 Evidence、产品判断、Outcome-first Plan、版本化 PRD，以及 exact local Handoff；它不会强迫每个 Signal 都进入 PRD。

当前版本是本地候选 `0.1.20`，只有一个 Host 可发现入口：`skills/better-product-graph/SKILL.md`。内部 Atomic Instructions、Better Question、20 个认知基座和 Product Goal Fidelity reviewer 合同只作为该 Skill 的 non-discoverable references 安装。

## 仓库目录

- `config/`：插件装配配置。
- `src/`：Graph 运行程序和内置产品工作规则。
- `scripts/`：构建、打包、隔离安装和验证工具。
- `host-adapters/codex/`：Codex Host 的公开入口与插件清单。
- `evals/`、`tests/`：发布所需的机械合同、产品夹具和回归测试。
- `docs/`：当前正式 PRD、冻结 Roadmap、必要构建基线和已采纳核心决策。

## 关键边界

- Host Agent 负责研究、访谈、质疑、Problem/Decision/Planning/PRD/Review 的产品语义。
- Python 只负责规范化、权限、Schema/Validator/Gate、exact refs、状态、CAS/恢复、并发 join、版本、模板装配和本地文件落盘；它不代替 Agent 做产品判断。
- Owner choice 是独立 typed Host-user command，不能由 Agent payload 自我授权。
- Reviewer 为 `ADVISORY_ONLY`；没有 `review.gate`、Reviewer block/waiver 或重复 Owner 确认。
- 没有 MCP、App、服务、数据库、队列、daemon、Web UI 或真实外部 Connector。Handoff 只生成 local packet，不声称已发送、接收或批准。

## 本地验证与打包

要求 Python 3、Git 和 Codex Desktop 自带的 Codex CLI。产品运行时只使用 Python 标准库。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/package_plugin.py .assistant/work/release/better-product-graph-0.1.20.zip --require-clean --json
python3 scripts/fresh_install_smoke.py .assistant/work/release/better-product-graph-0.1.20.zip --work-root .assistant/work/fresh-install --json
```

研发仓库内部还维护逐历史 finding 的审计验证器。它依赖未公开的上游来源与研发审计材料，不属于正式发布快照；本仓库只保留可独立运行的功能、权限、恢复、打包和安装测试。

`fresh_install_smoke.py` 只使用隔离 `CODEX_HOME`，验证本地 marketplace add、install、installed identity、Plugin Contract、`new` 激活、uninstall 和 rollback；它不会修改全局 Codex 安装。完整说明见 [LOCAL_INSTALL_v0.1.md](docs/release/LOCAL_INSTALL_v0.1.md)。

## 使用入口

显式 `$better-product-graph` 与等价自然语言入口使用同一 parser，支持 11 个 intents：`new`、`capture`、`inbox`、`status`、`resume`、`pause`、`handoff`、`connectors`、`audit`、`interview`、`help`。

`new` 和 `resume` 支持显式参数 `--interaction=no-pm-interview`（也兼容原有后缀写法）；访谈过程中可用 `interview skip <run-id>` 暂停提问，并用 `interview resume <run-id>` 恢复。该选项只停止 PM interview，不绕过 Evidence、Product Decision、Ready 或 authority checks。

Owner `WAIT` 会保持 `WAITING_TRIGGER`。已有 `resume` intent 可用 `resume <run-id> --trigger-file <project-relative-command.json>`（也接受 `trigger=...`）消费一次 typed `NEW_EVIDENCE` trigger；command 必须绑定当前 Run/state version/waiting condition 与 exact Evidence ref，错误或重放会 fail closed，并回到既有 `evidence.collect`，不会新增第十二个 intent 或业务 Node。

## 证据状态

- Product Golden v0.2 的 G01/G03/G04 fixture/contract 可以 `PASS`，但这不等于真实 Agent 产品判断通过。
- Plugin Contract `PASS` 证明 installed-copy 的 discovery、intent、resource、identity 等机械合同；不等于认证 Host Agent 端到端产品质量。
- 真实 authenticated Host Agent trial 与 Product Golden Agent judgment 在本地候选中保持 `NOT_RUN`，由集成任务安装后独立执行。
- `evals/product-graph` v0.1 仅为 `LEGACY / DOCUMENT-ONLY` 迁移输入，不是 V1.4 acceptance baseline。
