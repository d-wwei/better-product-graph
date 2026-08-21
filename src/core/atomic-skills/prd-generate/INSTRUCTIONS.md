# PRD Generate — Agent Instructions v0.1

Run only through the public Skill and Controller after an exact activated+eligible Slice is created from a Ready Product Plan. Read the exact Decision, Plan, planning views, Slice, Knowledge/Evidence, Guardrails/shared contracts, Template Profile, and Document Experience policy. The current `prd.generate` dispatch includes a closed `prd_generation_context`. Copy every field from its `metadata_authority` into PRD metadata exactly; do not calculate a scope hash, select a competing upstream ref, or infer an origin yourself. The Controller independently recomputes the packet and rejects any drift.

The Host Agent must author the full PRD product content. Begin with the independently deliverable user outcome and next action; preserve evidence, assumptions, Unknowns, authority and scope boundaries. Bind exact version/hash refs; never use `latest/current`, raw `TBD`, unfilled `{{...}}`, empty tables, or make up facts to fill a template. Include observable acceptance, dependencies, abnormal/recovery paths, risk/rollback, version/change visibility, and conditional Eval applicability/fulfillment without claiming tests ran. For the default general template, keep a visible Markdown heading named `## 附录 C：文档变更日志` and a concrete version row; a human-readable heading is the contract, so do not insert an internal filename merely to satisfy validation. In 0.1.20, REQUIRED Evals must remain `REVIEW_PENDING`/`NOT_RUN`: this skills-only Host cannot prove independent fulfillment, so neither `prd.generate` nor `prd.optimize` may claim `REVIEWED`.

Metadata must keep specification provenance and future product runtime inputs separate:

- `active_scope_ref` is the closed `active-scope-ref.v1` projection supplied by `prd_generation_context.metadata_authority`. It binds the exact Markdown `plan_ref`, stable `slice_id`, `active-scope-projection.v1`, and Controller-recomputed `scope_hash`; copy it exactly and never add a Candidate version.
- `spec_traceability` is the closed `spec-traceability.v1` supplied by `prd_generation_context.metadata_authority`. It already contains the complete Controller-selected Decision, roadmap, Product Plan, Slice, Knowledge, Evidence, optional Problem Ready (`problem_ready`), and any authorized replacement origins (`source_candidate`, `review_aggregate_result`). Copy it exactly; never invent, alias, remove, or independently select an origin.
- `product_runtime_inputs` is closed `product-runtime-inputs.v1` with non-empty `required` and separate `optional`. Required inputs always include `project_workspace` (`PROJECT_WORKSPACE`, `HOST_PROJECT_ROOT`, `PROJECT`, `project-workspace.v1`, `FAIL_CLOSED`) and `product_signal` (`RAW_SIGNAL_OR_EXACT_OCCURRENCE`, `SIGNAL_INTAKE`, `INVOCATION_OR_PROJECT_INBOX`, `signal-contract.v1`, `REQUEST_SIGNAL`). Planning Run/Attempt/Candidate identities, Ready receipts, specification refs, machine paths, and `current/latest` are provenance, never required runtime inputs. A genuine runtime BPG artifact needs the complete typed exception defined by the delivery contract and still cannot point into the current specification Run.

For `EXPERIMENT`, use the same PRD pipeline and add key unknown/hypothesis, audience/exposure, specific change, observable measurement, continue/adjust/stop mapping, monitoring, kill/rollback, Owner, end time, harm Guardrails, and typed-result return binding. Do not create an Experiment-only pipeline or lower Ready standards.

Submit `document_markdown`, `template_mapping`, metadata, and exact provenance as a `HOST_AGENT` Node Result. The program may validate, archive, version, and release the supplied content; it must not write missing PRD semantics.

Use the complete semantic shape below as the minimum assembly contract. The
values are representative only: copy every exact ref, origin, stable PRD ID,
Slice ID, version, date, and scope hash from the current dispatch/Controller
context. Keep `active_scope_ref`, `spec_traceability`, and
`product_runtime_inputs` closed; do not add aliases or omit fields because the
same fact appears in the Markdown.

<!-- prd-generate-semantic-output-contract -->
```json
{
  "document_markdown": "# Bootstrap PRD\n\n版本：v0.1｜状态：CANDIDATE\n\n## 阅读摘要\n\n结论：交付一个安全、可恢复、可追溯的项目 Bootstrap 闭环。\n\n## 目标与成功边界\n\n目标是只读取允许的项目上下文并形成可审计结果；不得读取秘密或越出项目根目录。\n\n## 范围与交付切片\n\n本期只包含一个可独立验证和回滚的 Bootstrap 核心切片。\n\n## 验收标准\n\n- Given 一个隔离项目，When 运行 Bootstrap，Then 只读取允许文件并输出带来源的 Profile 与 Readiness。\n\n## 风险、未知与回滚\n\n未知包括代表性项目中的输出价值；出现秘密读取、路径越界或不可恢复状态时停止并回滚。\n\n## 版本与变更\n\nv0.1：首次形成候选；测试执行与远程交付均未在本步骤发生。\n",
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
    "short_title": "bootstrap-core",
    "version": "v0.1",
    "date": "2026-08-21",
    "status": "CANDIDATE",
    "delivery_intent": "COMMIT",
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
    }
  }
}
```
