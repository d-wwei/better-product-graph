# PRD Generate — Agent Instructions v0.2

Run only through the public Skill and Controller after an exact activated+eligible Slice is created from a Ready Product Plan. Read the exact Decision, Plan, planning views, Slice, Knowledge/Evidence, Guardrails/shared contracts, Template Profile, and Document Experience binding. The current `prd.generate` dispatch includes a closed `prd_generation_context`. Its `metadata_authority.document_experience` identifies the exact base policy, PRD writing Profile, and writing guide by path, version, and hash. Read those exact files and apply them independently from the Template. Copy every field from `metadata_authority` into PRD metadata exactly; do not calculate a scope hash, select a competing upstream ref, infer an origin, or substitute a newer writing guide yourself. The Controller independently recomputes the packet and rejects any drift.

## PRD_WRITING_PROFILE_V04_CANDIDATE

Apply this section only when the exact dispatch explicitly binds Profile `0.4.0`;
Profile `0.2.0` keeps its existing authored behavior. Do not choose or promote a
Profile yourself. For an explicit v0.4 Candidate, preserve the complete product
contract while making these eight writing rules visible in the authored result:

- `ONE_SEMANTIC_ONE_CANONICAL_LOCATION`: define each semantic rule fully once;
  summaries and visuals point to that canonical location.
- `MAIN_PATH_CORE_PRODUCT_RESULTS_ONLY`: keep goals, scope, product flow, rules,
  boundaries, core acceptance and next action in the main path; layer fixtures,
  oracles, execution evidence and deep precision elsewhere.
- `GROUP_TO_COMPRESS_WITHOUT_SEMANTIC_LOSS`: group peer details by reader-visible
  outcomes instead of deleting permissions, exceptions, recovery or acceptance.
- `ONE_PRIMARY_REPRESENTATION_PER_RELATIONSHIP`: choose one primary diagram,
  table or list for a relationship; secondary forms add only missing information.
- `TABLES_ONLY_FOR_COMPARISON_AND_MAPPING`: use tables for stable comparison or
  mapping, not for narrative, reasoning or dense long sentences.
- `PRESERVE_FUNCTION_NOT_REPETITION`: before trimming a Checklist, preserve its
  explanation, location, decision, traceability and delivery-confirmation work.
- `TRUTHFUL_PRECISE_STATUS`: `[x]` needs an explicit legend and evidence boundary;
  proposed contracts say `PROPOSED_NOT_IMPLEMENTED`; unexecuted checks stay
  `NOT_RUN`; a local Handoff is never described as remotely sent, received or
  approved.
- `PLAIN_LANGUAGE_BEFORE_MACHINE_NAME`: explain the product meaning before a
  Machine Name. Keep product behavior and responsibility boundaries in the PRD;
  move internal Schema, storage, algorithm and concurrency design to the
  Engineering SPEC.

Author so a zero-context reader can `UNDERSTAND`, `SEE`, `MODEL`, `RETELL`,
`DECIDE`, and `LOCATE` the product contract. Group and layer rather than pursue
shortness: the author and Reviewer must not use word, line, section, or table-row counts
as automatic quality gates. A long necessary table or appendix is valid
when the main path stays complete and navigation is clear.

### STATUS_DRIFT_TEST

Before submitting the existing Document Experience self-check, separate three
authorities and record the result in its existing `diagnoses` and `actions`
lists; do not add a field or a second status document:

- the PRD owns the durable product contract and durable product Unknowns;
- the Product Planning Record owns product reasoning, decisions, evidence and
  durable Finding disposition history;
- Controller status and exact receipts own the mutable truth about where this
  Product Run is now.

Apply one semantic test to every sentence that looks like status: if product
requirements stay unchanged but advancing only the Product Run by one step
would make the sentence stale, it fails `STATUS_DRIFT_TEST` and must not remain
in the PRD. This includes current Candidate, Review, Ready, or Handoff status;
current Evals Generator capability or fulfillment; and current engineering
receipt, test, release, or delivery status. Move durable product reasoning or a
durable Finding disposition to the Product Planning Record. Read live progress
from Controller status or its exact receipt instead of copying it into prose.

The test is semantic, not a keyword scan. A durable requirement such as “when
product validation has not run, the product must not claim its effect is
validated” is a product contract, not current Run status. Record in
`diagnoses` what was checked and in `actions` what was removed, moved, or kept
with its durable reason.

The Host Agent must author the full PRD product content. Begin with the independently deliverable user outcome and product decision boundary; preserve evidence, assumptions, durable product Unknowns, authority and scope boundaries. Bind exact version/hash refs; never use `latest/current`, raw `TBD`, unfilled `{{...}}`, empty tables, or make up facts to fill a template. Apply the frozen PRD writing Profile's ELI5 rules: concrete event before abstraction, conclusion before explanation, one main point per paragraph, plain Chinese before the first technical term, and a meaningful Mermaid source block when a non-trivial flow, branch, sequence, state, data path, module relationship, or responsibility boundary is otherwise hard to understand. In the BPG 2.0 single-PRD runtime, the Candidate source file set is exactly `PRD.md`; keep visuals as Mermaid source in that Markdown only. Do not add asset files, generate or attach SVG preview, PNG or HTML before Ready, or perform picture safety or pixel preflight. If a conditional body section is truly not applicable and the Output Contract allows omission, omit its heading, empty table, and placeholder; keep the corresponding Checklist item as `不适用｜理由：具体原因`. A durable product Unknown, not-yet-designed product behavior, and mandatory product semantic are not “not applicable” and must remain visible; mutable execution status follows `STATUS_DRIFT_TEST` instead. Include observable acceptance, dependencies, abnormal/recovery paths, risk/rollback, durable document change visibility, and the truthful boundary that unexecuted validation cannot support a product-effect claim. Do not put mutable workflow claims such as current Review status, Eval fulfillment/execution result, or remote Handoff sent/received/approved status into the immutable PRD body; keep them in Controller-owned metadata, receipts, or status views so they cannot become a second stale authority. For the default general template, keep a visible Markdown heading named `## 附录 C：文档变更日志` and a concrete version row; a human-readable heading is the contract, so do not insert an internal filename merely to satisfy validation.

BPG 2.0 does not perform Product Evals applicability assessment, Eval Pack generation, or Eval Spec Review. The Author submits no Eval assessment or attachment for PRD freeze and must not manufacture one. Product Evals execution and product-effect validation remain `NOT_RUN`; this truthful boundary does not block 2.0 Ready or Local Handoff. Applicability, Pack, specification Review, and their Ready Gate begin only with the versioned 2.2 method and runtime.

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

### Managed PRD asset input

This legacy asset input contract is not used by the BPG 2.0 single-PRD runtime.
That runtime keeps Mermaid source in the Markdown Candidate and materializes SVG
or HTML only at Handoff. Do not use `asset_change_set` to create Candidate SVG
preview or PNG derivatives for a BPG 2.0 Run.

When the Markdown references a reader-visible visual, do not embed raw inline
`<svg>`. Produce a safe local `.svg` plus same-stem `@2x.png`, then declare the
exact source bytes through the optional closed `asset_change_set`. The Host may
omit this field when the Candidate has no asset changes. The Controller reads
each source exactly once, rejects symlinks, traversal, hash drift, unknown
fields, and non-SVG/PNG destinations, then archives the resulting self-contained
asset tree. `destination` is relative to the Candidate `assets/` directory and
must end in `.svg` or `@2x.png`; never prefix it with `assets/`. Every final
visual asset must be one referenced safe `.svg` plus its exact same-stem
`@2x.png`: the Controller rejects malicious or unreferenced orphan pairs,
unpaired extras, plain/unknown PNG names, other visual formats, and missing
partners even when Markdown does not reference the bad file. `remove` is exact
and fails when its target does not already exist. `source_ref.version` accepts
only a positive JSON integer or a non-blank string; JSON booleans are invalid.

<!-- prd-asset-change-set-v1-contract -->
```json
{
  "schema_version": "prd-asset-change-set.v1",
  "upsert": [
    {
      "destination": "main-flow.svg",
      "source_ref": {"path": ".better-product-graph/asset-inputs/main-flow.svg", "hash": "sha256:exact-svg-bytes", "version": 1}
    },
    {
      "destination": "main-flow@2x.png",
      "source_ref": {"path": ".better-product-graph/asset-inputs/main-flow@2x.png", "hash": "sha256:exact-png-bytes", "version": 1}
    }
  ],
  "remove": []
}
```

Submit `document_markdown`, `template_mapping`, metadata, optional
`asset_change_set`, and exact provenance as a `HOST_AGENT` Node Result. The
program may validate, archive, version, and release the supplied content; it
must not write missing PRD semantics.

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
  "asset_change_set": {"schema_version": "prd-asset-change-set.v1", "upsert": [], "remove": []},
  "document_markdown": "# BPG-PRD-BOOTSTRAP-001_项目上下文快速理解_v0.1_2026-08-24\n\n## 阅读摘要\n\n结论：交付一个安全、可恢复、可追溯的项目 Bootstrap 闭环。\n\n## 目标与成功边界\n\n目标是只读取允许的项目上下文并形成可审计结果；不得读取秘密或越出项目根目录。\n\n## 范围与交付切片\n\n本期只包含一个可独立验证和回滚的 Bootstrap 核心切片。\n\n## 验收标准\n\n- Given 一个隔离项目，When 运行 Bootstrap，Then 只读取允许文件并输出带来源的 Profile 与 Readiness。\n\n## 风险、未知与回滚\n\n未知包括代表性项目中的输出价值；出现秘密读取、路径越界或不可恢复状态时停止并回滚。\n\n## 版本与变更\n\nv0.1：首次形成产品合同。\n",
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
