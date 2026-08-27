# PRD Readability Eval v0.4

这套九案例用于检验独立 Writing Reviewer 是否能识别真正影响读者理解的表达问题，同时避免“文档长、表格大、附录多就自动判错”。它是新的 Candidate 评测身份，不重算、覆盖或美化 v0.3 的 `3/5 FAIL` 历史。

## 九个预注册结果

- 六个对抗案例分别要求识别：同层条目过载、语义重复、表达方式撞车、删掉 Checklist 功能、勾选语义不清和拟定合同伪装成已实现。
- 三个正例分别证明：必要的大状态表、主路径短而附录长、以及读者优先的分层 PRD 都可以通过。
- 隐藏预期只固定 `PASS/FINDING`、一个必要主诊断和一个必要修订方向，不预写 Reviewer 的自然语言答案。

v0.3 中含图案例的视觉合同和正例质量存在冲突。本版不复用那些资产：`list-diagram-table-same-model` 故意用列表、文字图和表格重复同一关系，评测的是表达方式撞车；`reader-first-layered-prd` 是重新编写的无图正例，不再依赖有争议的视觉资产来获得 PASS。

## 文件与保管边界

- `cases/*.md`：Candidate-like 原始输入，`suite.json` 固定 exact SHA-256。
- `evaluator/expected.json`：只给评分方，不能进入 Agent workspace。
- `evaluator/preregistration.json`：结果产生前提交的静态预注册，固定九案例、隐藏预期、Profile、Guide 和运行时 checkpoint 必须绑定的身份字段。
- `run_contract.py`：只检查评测材料完整性并导出匿名 Agent 输入；它不执行 Agent，也不评分。

静态预注册不能替代运行时 checkpoint。后续 Eval-only runtime 必须在每个 Reviewer 结果产生前，另行绑定 exact Candidate、Profile、Guide、instruction、Reviewer resource、output contract、installed build 和 dispatch。缺任何一项都不能形成有效 Agent Eval 证据。

## 合同检查与匿名输入

```bash
python3 evals/prd-readability-v0.4/run_contract.py
python3 evals/prd-readability-v0.4/run_contract.py \
  --emit-agent-workspace /tmp/bpg-prd-readability-v04-agent-input
```

导出目录只包含 `case-001` 至 `case-009`。每个目录只有 `candidate.md` 与 `case-manifest.json`，不包含真实 Case ID、预期、预注册、评分规则、其他 Reviewer 结果或作者隐藏推理。目标目录必须为空。

## 证据边界

当前只能声明 Suite contract 完整：

- Agent Product Eval：`NOT_RUN`
- 真实 PRD ordinary Review：`NOT_RUN`
- 观察式真人阅读：`NOT_RUN`

只有安装版公开路径完成九个独立 Reviewer、评分达到 `9/9`，并另有一份真实 PRD 走完 ordinary Review，v0.4 才有资格晋级。合同 PASS 不能推导这些运行结果。
