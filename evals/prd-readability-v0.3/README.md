# PRD Readability Eval v0.3

这套案例用于检验独立 Writing Reviewer 能否发现会改变读者理解的表达问题。它不是写作风格打分表，也不把合同测试冒充 Agent 产品评测。

## 三种证据必须分开

- `CONTRACT_PASS`：五个 Fixture、隐藏预期、枚举和哈希合同完整。只说明评测材料可以运行。
- `AGENT_RUNTIME_PASS/FAIL`：独立 Reviewer 通过安装版公开 Host 路径真实审查，五个 Fixture 和至少一份真实 PRD 都达到预先阈值。
- `HUMAN_READER_VALIDATED`：真人在观察式研究中完成阅读任务。本 Suite 不产生这个结论，当前固定为 `NOT_RUN`。

`CONTRACT_PASS` 不能推出 Agent 已经运行；五个 Fixture 通过也不能推出完整 Agent Product Eval 通过，因为后者还需要至少一份真实 PRD。

## 文件边界

- `cases/*.md` 是不可变 Candidate-like 输入；`suite.json` 固定其 SHA-256。
- `expected.json` 只给评分方，不能交给 Reviewer。
- `assets/visual-*.svg` 与同名 `@2x.png` 是两个含图案例已经提交并固定哈希的等价视觉资产；运行时只复制 exact bytes，不临时生成空白回退图。
- `results/agent-product-eval-summary.json` 保存父流程基于 exact installed Host 证据形成的运行结论。当前记录为 `FAIL`：五个 Fixture 完成但只有 3/5 达到预注册阈值，真实 PRD Review 与真人阅读均为 `NOT_RUN`；因此不能晋级默认版本。该文件不能脱离对应 Run/attempt、hash 和评分证据手工改成 PASS。

## 合同检查与隔离输入

```bash
python3 evals/prd-readability-v0.3/run_contract.py
python3 evals/prd-readability-v0.3/run_contract.py \
  --emit-agent-workspace /tmp/bpg-prd-readability-agent-input
```

导出的目录只使用 `case-001` 一类无语义编号；资产只使用 `visual-001` 一类无语义文件名。每个目录只包含 `candidate.md`、可能存在的 `assets/` 和 `case-manifest.json`，不包含真实 Case ID、`expected.json`、其他 Reviewer 结果或作者隐藏推理。含图案例的 manifest 还会给出实际观察目标 `render_target`。真实 Case 映射只保留在 evaluator-side `expected.json`。目标目录必须为空。

## 后续真实 Agent Eval 的输入方式

1. 从 clean Candidate commit 构建 disposable Codex Plugin，并通过安装版 Better Product Graph 的公开 Host 入口创建各自独立的 Run/attempt。
2. 将导出的一个 Case 作为 exact PRD Candidate 输入。Reviewer 只能读取 dispatch 提供的 exact Candidate、Profile、Guide 和 Output Contract；不能读取本目录的 `expected.json`。
3. 通过安装版公开 Controller 创建并启动新的 `review.parallel` dispatch，但先不要让 Reviewer 提交结果。Reviewer 的 `HOST_SUBAGENT_ATTEMPT` 必须与作者的 `HOST_AGENT_ATTEMPT` 不同。
   使用安装包内唯一的评测 bootstrap；它不是新 Graph Node，也不能选择其他节点、Profile 或后续路线：

```bash
python3 /absolute/installed-plugin/skills/better-product-graph/scripts/bpg_runner.py \
  --operation prepare-writing-eval \
  --run-id run-writing-eval-001 \
  --payload-file /absolute/eval-project/writing-eval-bootstrap.json
```

   Payload 是 closed `writing-review-eval-bootstrap.v1`：

```json
{
  "schema_version": "writing-review-eval-bootstrap.v1",
  "suite_id": "better-product-graph-prd-readability-v0.3",
  "run_id": "run-writing-eval-001",
  "candidate_ref": {
    "path": "artifacts/prds/archived/readability-eval/case-001/candidate.md",
    "hash": "sha256:<exact-candidate-hash>",
    "version": 1
  },
  "asset_refs": [],
  "author_execution_id": "fixture-author-case-001"
}
```

   Candidate 必须是 project 内 regular Markdown；资产必须是同一源 Candidate 的 `assets/` 后代，并逐个提供 exact path/hash/version。Controller 会调用 v0.3 视觉校验，将 exact bytes 复制到 `artifacts/prds/archived/` 下的不可变自包含评测 Candidate，固定绑定安装版 v0.3 Profile、Guide、Reader Review v2 Contract 与当前 Output Contract，然后创建 `run_type=writing_eval` 的真实 dispatch。该 Run 只允许消费这次 `review.parallel`；正常 Result/receipt/transition 后即标记 `COMPLETED`，不会进入 aggregate、Ready、Release 或 Handoff。

4. 由评测方在 Reviewer workspace 之外预注册这个已启动的 dispatch：

```bash
python3 evals/prd-readability-v0.3/run_contract.py \
  --preregister-case simple-linear-no-visual \
  --project-root /absolute/eval-project \
  --installed-skill-root /absolute/installed-plugin/skills/better-product-graph \
  --run-id run-... \
  --review-attempt-id attempt-... \
  --checkpoint-root /absolute/eval-project/evaluator-private/preregistrations
```

预注册会复用 installed identity verifier 和 NodeRegistry，核对 clean build、public Controller inventory、exact dispatch/contract 及 Candidate/Profile/Guide/Output/Review refs。它只允许在事件头为该 attempt 的 `NODE_CALL_STARTED` 且 result/receipt 尚不存在时运行，并以 `O_EXCL` 创建不可覆盖的随机 challenge checkpoint；目录权限为 `0700`，文件权限为 `0600`。把返回的 `evaluation_record_seed` 保存成 evaluator-side `evaluation-record.json`，不要把 checkpoint、challenge 或真实 Case 映射放入 Reviewer workspace。

5. 按安装版公开 `review.parallel` 合同提交完整 `document-experience-review.v2` 和正常 Writing Findings。先让 Controller 接受 Node Result，再评分；不得绕过 Controller 直接把模型文本当成通过证据。
6. 运行五案例评分：

```bash
python3 evals/prd-readability-v0.3/run_contract.py \
  --project-root /absolute/eval-project \
  --score-results /absolute/eval-project/eval-results
```

评分器直接读取该 Run 的 `state.json`、`events.jsonl`、dispatch contract、`node-result.json` 和 `result-receipt.json`，调用现有 event-chain 验证，并要求同一事件链严格从预注册的 initial head 延伸。它还会核对 checkpoint exact hash、同一 attempt 已消费、唯一 dispatch/start/persist/transition 事件、result/receipt hash、Writing Review hash，以及 Candidate/Profile/Guide/Review Contract/Output Contract/Reviewer identity 均来自同一 accepted attempt。缺少 checkpoint、晚于 result 才调用官方预注册、build/dispatch/checkpoint 不匹配或只有一棵自造运行树都会失败。

允许 Reviewer 同时发现合理的次要问题。评分时，`allowed_repairs` 只约束包含预期主问题全部 categories 的 primary diagnosis，不会因为另一个次要 Finding 使用了其他修订方法而误判。

测试内的 synthetic tree 只能得到 `SYNTHETIC_CONTRACT_PASS`，不能得到 Agent PASS。现场五案例最多形成 `EVALUATOR_PREREGISTERED_CONTROLLER_EVIDENCE`；总体 `agent_runtime_status` 仍为 `NOT_RUN`，直到父流程现场创建并保管 checkpoints、完成独立 Reviewer，并另行完成至少一份真实 PRD 的独立 Review。

Run state、event chain、Node Result 和 Controller result receipt 是运行证据，evaluator-private checkpoint 固定执行前的观察前沿。这个设计仍是本地、无签名的 `EVALUATOR_PREREGISTERED_CONTROLLER_EVIDENCE`，不是外部密码学证明，可靠性依赖评测方现场创建、隔离并保管 checkpoint。`render_observation=OBSERVED` 也仍只是 Reviewer attestation，不是 Controller perception proof。

## Expected envelope 为什么不是唯一答案

隐藏预期只固定必须识别的理解断点和允许的修订方向。例如啰嗦案例可以分层、合并、移动或删减重复表达；只要理解成本下降且产品合同不丢失，就不要求写成同一份文案。
