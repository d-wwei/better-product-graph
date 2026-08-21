# ADR-001: Local skills-only Plugin runtime v0.1

状态：Accepted for implementation
日期：2026-08-20
依据：`PRD_GRAPH_v1.4.md`、`BETTER_PRODUCT_GRAPH_ROADMAP_v0.12.md`、2026-08-20 implementation tooling disposition
上一版本：无

## 结论

第一个 Better Product Graph 本地候选采用一个 skills-only Codex Plugin、一个公开 Skill、Python 3 标准库确定性本地 module/library、JSON current state snapshot 和 JSONL meaningful event stream。构建从显式 allowlist 生成 self-contained Plugin；运行不需要 MCP、App、Service、数据库、队列、daemon、独立 CLI、第二 Host 或真实 Connector。

## Agent 与程序的不可突破边界

Host Agent 负责所有语义产品工作：研究、Evidence 解释、Assumption Audit、PM 访谈与质疑、Product Decision 建议、Planning 内容、PRD 正文和专业 Review Finding。原子 `INSTRUCTIONS.md` 定义这些任务与 Node Result。

Python 只负责输入规范化、合同与 exact ref 校验、权限、State Controller、CAS、schema/validator/gate、已确认 outcome 的确定性路由、版本、持久化、恢复、只读并发 attempt 的 durable plan/join、模板装配、文件落盘和可检查的硬约束。程序不得推断问题、选择 MVU/产品结果、生成 Plan/PRD 内容或发明 Reviewer Finding。含语义输出的 Node Result 必须绑定 `producer.kind=HOST_AGENT`、当前 instruction/input hashes 和 attempt identity；程序生成的语义输出必须被拒绝。

Product Golden fixture/contract 执行只证明合同可运行。只有真实 Host Agent trial 才能产生产品判断的 `PASS/FAIL`；没有真实 trial 时该层必须是 `NOT_RUN`。

## 状态与恢复

每个 Run 只有一个 current state snapshot 和一条 append-only meaningful event stream。状态写入使用同目录临时文件、flush/fsync 和 atomic replace；事件使用 canonical JSON 和前向 hash chain。Git 保存文档内容历史，Run State 保存当前位置/有效 refs/等待/副作用，Audit Event 保存重要变化的原因，不互相复制。

## Host enforcement

一期 Codex Adapter 声明 `detect_only`：Controller、正式入口、审计和测试能拒绝或发现绕过，但不宣称具有操作系统级隔离。高风险外部写入没有 Null/local 之外的实现。

## 构建身份

`build-manifest.json` 自动绑定 Plugin SemVer、Git commit/dirty、冻结架构与 Roadmap hash、execution contract fingerprint、稳定 inventory 和 artifact hash。artifact hash 基于除 build manifest 自身外的安装文件清单；安装验证只读取 installed copy。

## 可替换边界

- JSON/JSONL 文件可在未来真实并发或团队需求出现后替换，Core 合同不依赖数据库 API。
- Codex Host mapping 留在 `host-adapters/codex/`；第二 Host 出现前不抽象通用框架。
- Connector 只有 Null/local interface；真实身份、权限、回执和消费者出现后再选择 transport。
- Python 标准库是第一版最小依赖；新增依赖需要具体能力、离线与供应链收益证明。

## 明确不表示

Accepted ADR 不表示 runtime、Plugin Contract、Product Golden、Agent 产品判断或 fresh install 已经 PASS；证据状态由后续测试与 release verification 单独记录。
