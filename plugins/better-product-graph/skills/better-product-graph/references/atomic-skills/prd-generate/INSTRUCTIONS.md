# PRD Generate — Agent Instructions v0.2

Run only through the public Skill and Controller after an exact activated+eligible Slice is created from a Ready Product Plan. Read the exact Decision, Plan, planning views, Slice, Knowledge/Evidence, Guardrails/shared contracts, Template Profile, and Document Experience policy. The current `prd.generate` dispatch includes a closed `prd_generation_context`. Copy every field from its `metadata_authority` into PRD metadata exactly; do not calculate a scope hash, select a competing upstream ref, or infer an origin yourself. The Controller independently recomputes the packet and rejects any drift.

The Host Agent must author the full PRD product content. Begin with the independently deliverable user outcome and next action; preserve evidence, assumptions, Unknowns, authority and scope boundaries. Bind exact version/hash refs; never use `latest/current`, raw `TBD`, unfilled `{{...}}`, empty tables, or make up facts to fill a template. Include observable acceptance, dependencies, abnormal/recovery paths, risk/rollback, version/change visibility, and conditional Eval applicability/fulfillment without claiming tests ran. For the default general template, keep a visible Markdown heading named `## 附录 C：文档变更日志` and a concrete version row; a human-readable heading is the contract, so do not insert an internal filename merely to satisfy validation. In the current skills-only Host, REQUIRED Evals must remain `REVIEW_PENDING`/`NOT_RUN`: the Host cannot prove independent fulfillment, so neither `prd.generate` nor `prd.optimize` may claim `REVIEWED`.

Choose the PRD's human title in the user's working language: use an explicit
language preference when present, otherwise use the language the user is using
in the current interaction, and fall back to `zh-CN` only when neither is
available. Record that choice in `metadata.document_language`. The
`metadata.short_title` is a short human-readable title in that language, not a
hidden English slug. Keep the stable PRD ID, version, and date machine-readable.
The immutable directory stem, Markdown filename stem, and the document's only
H1 must be exactly the same string:

```text
<prd_id>_<localized short_title>_<version>_<date>
```

For example: `BPG-PRD-BOOTSTRAP-001_项目上下文快速理解_v0.1_2026-08-24`.
Derived DOCX/PDF exports, when requested, reuse that exact stem. Never rename an
already archived or released PRD in place; a naming or title change creates the
next immutable Candidate version.

Metadata must keep specification provenance and future product runtime inputs separate:

- `active_scope_ref` is the closed `active-scope-ref.v1` projection supplied by `prd_generation_context.metadata_authority`. It binds the exact Markdown `plan_ref`, stable `slice_id`, `active-scope-projection.v1`, and Controller-recomputed `scope_hash`; copy it exactly and never add a Candidate version.
- `spec_traceability` is the closed `spec-traceability.v1` supplied by `prd_generation_context.metadata_authority`. It already contains the complete Controller-selected Decision, roadmap, Product Plan, Slice, Knowledge, Evidence, optional Problem Ready (`problem_ready`), and any authorized replacement origins (`source_candidate`, `review_aggregate_result`). Copy it exactly; never invent, alias, remove, or independently select an origin.
- `product_runtime_inputs` is closed `product-runtime-inputs.v1` with non-empty `required` and separate `optional`. Required inputs always include `project_workspace` (`PROJECT_WORKSPACE`, `HOST_PROJECT_ROOT`, `PROJECT`, `project-workspace.v1`, `FAIL_CLOSED`) and `product_signal` (`RAW_SIGNAL_OR_EXACT_OCCURRENCE`, `SIGNAL_INTAKE`, `INVOCATION_OR_PROJECT_INBOX`, `signal-contract.v1`, `REQUEST_SIGNAL`). Planning Run/Attempt/Candidate identities, Ready receipts, specification refs, machine paths, and `current/latest` are provenance, never required runtime inputs. A genuine runtime BPG artifact needs the complete typed exception defined by the delivery contract and still cannot point into the current specification Run.

For `EXPERIMENT`, use the same PRD pipeline and include the complete closed
`experiment-contract.v1` object below. Do not create an Experiment-only pipeline
or lower Ready standards. Every listed property is required; unknown properties
are rejected.

Exact public field contract:

- `schema_version`: literal string enum `experiment-contract.v1`.
- `key_unknown`, `hypothesis`, `audience_exposure`, `specific_change`,
  `observable_measurement`, `monitoring`, `kill_rollback`, `owner`: non-empty strings.
- `end_time`: ISO calendar date string (`YYYY-MM-DD`).
- `harm_guardrails`: non-empty array of non-empty strings.
- `result_mapping`: object containing exactly the four enum keys `CONTINUE`,
  `ADJUST`, `STOP`, `INCONCLUSIVE`; every value is a non-empty condition string.
- `typed_result_return`: object containing exactly `schema_version`, `ingress_node`,
  and `outcome_enum`. The schema version is the literal
  `experiment-result-binding.v1`; `ingress_node` is the literal `signal.ingest`;
  `outcome_enum` is exactly `["CONTINUE", "ADJUST", "STOP", "INCONCLUSIVE"]`.

Legal standalone example:

<!-- experiment-contract-v1-example -->
```json
{
  "schema_version": "experiment-contract.v1",
  "key_unknown": "受控提示是否减少失败后的重复提交",
  "hypothesis": "状态解释与安全重试会减少重复提交且不增加重复扣款",
  "audience_exposure": "仅向进入恢复页的 5% 白名单用户展示",
  "specific_change": "展示结算状态解释和一个幂等重试入口",
  "observable_measurement": "重复提交率下降，同时重复扣款保持为零",
  "result_mapping": {
    "CONTINUE": "主指标改善且所有伤害护栏未触发",
    "ADJUST": "方向正确但需要调整文案或曝光范围",
    "STOP": "触发任一伤害护栏或重复扣款不为零",
    "INCONCLUSIVE": "样本不足或数据质量无法支持判断"
  },
  "monitoring": "Owner 每日检查主指标、重复扣款与退出率",
  "kill_rollback": "触发 STOP 条件后立即停止曝光并恢复旧入口",
  "owner": "checkout-product-owner",
  "end_time": "2026-09-20",
  "harm_guardrails": ["重复扣款必须为零", "用户可以立即退出实验"],
  "typed_result_return": {
    "schema_version": "experiment-result-binding.v1",
    "ingress_node": "signal.ingest",
    "outcome_enum": ["CONTINUE", "ADJUST", "STOP", "INCONCLUSIVE"]
  }
}
```

Submit `document_markdown`, `template_mapping`, metadata, and exact provenance as a `HOST_AGENT` Node Result. The program may validate, archive, version, and release the supplied content; it must not write missing PRD semantics.

Use the complete semantic shape below as the minimum assembly contract. The
values are representative only: copy every exact ref, origin, stable PRD ID,
Slice ID, version, date, and scope hash from the current dispatch/Controller
context. Keep `active_scope_ref`, `spec_traceability`, and
`product_runtime_inputs` closed; do not add aliases or omit fields because the
same fact appears in the Markdown. Set top-level `structure_mode` to exactly one
of `split`, `compact`, or `legacy`. The current general template defaults to
`split` when the field is omitted; state it explicitly whenever the Host chooses
a structure so that the submitted shape remains visible and auditable.

<!-- prd-generate-semantic-output-contract -->
```json
{
  "structure_mode": "legacy",
  "document_markdown": "# BPG-PRD-BOOTSTRAP-001_项目上下文快速理解_v0.1_2026-08-24\n\n版本：v0.1｜状态：CANDIDATE\n\n## 阅读摘要\n\n结论：交付一个安全、可恢复、可追溯的项目 Bootstrap 闭环。\n\n## 目标与成功边界\n\n目标是只读取允许的项目上下文并形成可审计结果；不得读取秘密或越出项目根目录。\n\n## 范围与交付切片\n\n本期只包含一个可独立验证和回滚的 Bootstrap 核心切片。\n\n## 验收标准\n\n- Given 一个隔离项目，When 运行 Bootstrap，Then 只读取允许文件并输出带来源的 Profile 与 Readiness。\n\n## 风险、未知与回滚\n\n未知包括代表性项目中的输出价值；出现秘密读取、路径越界或不可恢复状态时停止并回滚。\n\n## 版本与变更\n\nv0.1：首次形成候选；测试执行与远程交付均未在本步骤发生。\n",
  "template_mapping": {
    "summary": "阅读摘要",
    "goal": "目标与成功边界",
    "scope": "范围与交付切片",
    "acceptance": "验收标准",
    "risk": "风险、未知与回滚",
    "version": "版本与变更"
  },
  "metadata": {
    "prd_id": "BPG-PRD-BOOTSTRAP-001",
    "short_title": "项目上下文快速理解",
    "document_language": "zh-CN",
    "version": "v0.1",
    "date": "2026-08-24",
    "status": "CANDIDATE",
    "delivery_intent": "EXPERIMENT",
    "decision_refs": [
      {"path": ".better-product-graph/decisions/decision-example/DECISION_v1.json", "hash": "sha256:decision", "version": 1}
    ],
    "roadmap_snapshot_ref": {
      "path": ".better-product-graph/runs/run-example/attempts/attempt-roadmap/node-result.json",
      "hash": "sha256:roadmap",
      "version": 1
    },
    "product_plan_ref": {
      "path": ".better-product-graph/runs/run-example/artifacts/product-plan-v1.md",
      "hash": "sha256:plan",
      "version": 1
    },
    "slice_ref": {
      "path": ".better-product-graph/runs/run-example/attempts/attempt-planning/node-result.json",
      "hash": "sha256:slice",
      "version": 1
    },
    "active_scope_ref": {
      "schema_version": "active-scope-ref.v1",
      "plan_ref": {
        "path": ".better-product-graph/runs/run-example/artifacts/product-plan-v1.md",
        "hash": "sha256:plan",
        "version": 1
      },
      "slice_id": "slice-bootstrap-core",
      "projection_version": "active-scope-projection.v1",
      "scope_hash": "sha256:scope"
    },
    "spec_traceability": {
      "schema_version": "spec-traceability.v1",
      "refs": [
        {"role": "decision", "path": ".better-product-graph/decisions/decision-example/DECISION_v1.json", "hash": "sha256:decision", "version": 1, "origin_node_id": "product.decision", "origin_attempt_id": "attempt-decision"},
        {"role": "roadmap", "path": ".better-product-graph/runs/run-example/attempts/attempt-roadmap/node-result.json", "hash": "sha256:roadmap", "version": 1, "origin_node_id": "evidence.collect", "origin_attempt_id": "attempt-roadmap"},
        {"role": "product_plan", "path": ".better-product-graph/runs/run-example/artifacts/product-plan-v1.md", "hash": "sha256:plan", "version": 1, "origin_node_id": "product.planning", "origin_attempt_id": "attempt-planning"},
        {"role": "slice", "path": ".better-product-graph/runs/run-example/attempts/attempt-planning/node-result.json", "hash": "sha256:slice", "version": 1, "origin_node_id": "product.planning", "origin_attempt_id": "attempt-planning"},
        {"role": "knowledge", "path": ".better-product-graph/runs/run-example/attempts/attempt-knowledge/node-result.json", "hash": "sha256:knowledge", "version": 1, "origin_node_id": "evidence.map", "origin_attempt_id": "attempt-knowledge"},
        {"role": "evidence", "path": ".better-product-graph/runs/run-example/attempts/attempt-evidence/node-result.json", "hash": "sha256:evidence", "version": 1, "origin_node_id": "evidence.collect", "origin_attempt_id": "attempt-evidence"}
      ]
    },
    "product_runtime_inputs": {
      "schema_version": "product-runtime-inputs.v1",
      "required": [
        {"input_id": "project_workspace", "kind": "PROJECT_WORKSPACE", "resolver": "HOST_PROJECT_ROOT", "binding_scope": "PROJECT", "version_policy": "project-workspace.v1", "on_missing": "FAIL_CLOSED"},
        {"input_id": "product_signal", "kind": "RAW_SIGNAL_OR_EXACT_OCCURRENCE", "resolver": "SIGNAL_INTAKE", "binding_scope": "INVOCATION_OR_PROJECT_INBOX", "version_policy": "signal-contract.v1", "on_missing": "REQUEST_SIGNAL"}
      ],
      "optional": []
    },
    "knowledge_snapshot_ref": {
      "path": ".better-product-graph/runs/run-example/attempts/attempt-knowledge/node-result.json",
      "hash": "sha256:knowledge",
      "version": 1
    },
    "evidence_refs": [
      {"path": ".better-product-graph/runs/run-example/attempts/attempt-evidence/node-result.json", "hash": "sha256:evidence", "version": 1}
    ],
    "evals": {
      "applicability": "RECOMMENDED",
      "reason": "Behavior includes safety and recovery claims that benefit from a future Eval Pack.",
      "fulfillment": "NOT_STARTED",
      "execution_status": "NOT_RUN"
    },
    "experiment_contract": {
      "schema_version": "experiment-contract.v1",
      "key_unknown": "受控提示是否减少失败后的重复提交",
      "hypothesis": "状态解释与安全重试会减少重复提交且不增加重复扣款",
      "audience_exposure": "仅向进入恢复页的 5% 白名单用户展示",
      "specific_change": "展示结算状态解释和一个幂等重试入口",
      "observable_measurement": "重复提交率下降，同时重复扣款保持为零",
      "result_mapping": {
        "CONTINUE": "主指标改善且所有伤害护栏未触发",
        "ADJUST": "方向正确但需要调整文案或曝光范围",
        "STOP": "触发任一伤害护栏或重复扣款不为零",
        "INCONCLUSIVE": "样本不足或数据质量无法支持判断"
      },
      "monitoring": "Owner 每日检查主指标、重复扣款与退出率",
      "kill_rollback": "触发 STOP 条件后立即停止曝光并恢复旧入口",
      "owner": "checkout-product-owner",
      "end_time": "2026-09-20",
      "harm_guardrails": ["重复扣款必须为零", "用户可以立即退出实验"],
      "typed_result_return": {
        "schema_version": "experiment-result-binding.v1",
        "ingress_node": "signal.ingest",
        "outcome_enum": ["CONTINUE", "ADJUST", "STOP", "INCONCLUSIVE"]
      }
    }
  }
}
```
