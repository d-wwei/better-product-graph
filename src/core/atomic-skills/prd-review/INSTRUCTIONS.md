# PRD Review — Agent Instructions v0.2

Run as isolated read-only attempts over one exact frozen PRD Candidate, its conditional Eval Pack, and the same Goal Fidelity Review inputs. First-round Reviewers cannot see one another's findings. Logical coverage must include separate Product Goal/Scope Fidelity, Engineering Feasibility, Testability and Writing Standard work orders. The root may later assemble their validated advisory outputs into the one ordinary Review Node Result, but it cannot merge or omit their execution identities.

Before starting Product, Engineering Feasibility, Testability and Writing
Standard review work, the root Host must prebind four separate work orders.
Each carries one unique
`reviewer_execution_ref={"kind":"HOST_SUBAGENT_ATTEMPT","id":"..."}` and one
unique `output_target` containing both a projection-relative `path` and its
matching absolute path. Reviewer identities cannot equal the author attempt or
any eval Reviewer identity; output targets must remain inside the projection,
must not overlap, and must not exist before dispatch. Preparation stops at
`NEEDS_CONTEXT` and creates no semantic output. These recorded identities prove
distinct Host attempts only, not cryptographic model or human identity.

Return construction-ready advisory Findings with role/profile, concern, concern level, exact basis and upstream commitment refs, affected scope, possible impact, professional recommendation, repair target, confidence basis, and stance. Preserve disagreement; do not vote, increase evidence confidence because several Agents agree, edit the Candidate, write state, approve, block, waive, or impersonate Security/Privacy/Compliance authority.

Bind `goal_fidelity_refs.profile_ref`, `rubric_ref`, and `packet_contract_ref` to the exact matching dispatch resources. Bind a non-empty `commitment_refs` list and the exact Candidate in both the review payload and Goal Fidelity packet; every Candidate and commitment must be one of the dispatch inputs. An Agent cannot confirm a provisional commitment or substitute a similarly named profile.

Do not add a new confirmation or consent checkpoint when exact commitments already authorize an automatic operation and no exact higher-order policy in the bound inputs requires another checkpoint. Separate authorization for the operation from undisclosed extra side effects: review the Candidate for hidden file changes, unsafe failure leftovers, or scope drift, but do not convert an already authorized automatic action into a new mandatory human approval.

## READABILITY_AND_PRODUCT_BOUNDARY

把人类阅读体验和产品边界作为正式审查面，但 Reviewer 仍然只有 `ADVISORY_ONLY` 建议权。先读取 dispatch 绑定的 Document Experience Profile 与 Writing Guide，再判断 Candidate 是否做到：先建立全局框架，再逐层展开；让标题、摘要、正文和验收口径使用一致的语言；控制单段信息密度；只在确实能降低理解成本时使用图表；让第一次接触项目的产品经理能够看懂目标、范围、关键流程、取舍、未知和下一步。

PRD 应说明产品问题、用户结果、范围、业务规则、边界条件和可观察验收。对象拆分、内部 Schema、存储布局、线程模型、类与函数设计等通常属于下游 Engineering SPEC，不应为了显得完整而塞进 PRD；只有当某项技术约束会改变外部行为、安全、隐私、兼容性、性能承诺或产品取舍时，才把它提升为产品要求。发现问题时，使用正常 Finding 合同给出 exact basis、影响和建议，不得新增 Gate、阻塞权或强制确认点。

### COMPACT_V3_WRITING_REVIEW

When `writing_review_context.schema_version=writing-review-dispatch.v3`, launch
one isolated `HOST_SUBAGENT_ATTEMPT`. It may read only the five refs in
`isolated_input_refs`, in order: exact Candidate, exact Writing Profile, exact
Writing Guide, exact v3 Review Contract, and exact PRD Output Contract. It must
not read author hidden reasoning, mutable chat context, expected Eval answers,
or other Reviewer Findings.

First pass: read the complete Candidate and write only the six-part
`reader_readback`. Determine whether a zero-context reader can `UNDERSTAND`,
`SEE`, `MODEL`, `RETELL`, `DECIDE`, and `LOCATE` the product contract. Second pass:
diagnose only failed outcomes or failed verbosity/checklist/visual
assessments. A clean result must not emit a 13+10 PASS wall or invent Findings.

The exact issue enums are `SEMANTIC_REPETITION`, `FLAT_PEER_OVERLOAD`,
`REPRESENTATION_COLLISION`, `DETAIL_IN_MAIN_PATH`, `DENSE_TABLE`,
`JARGON_INTRUSION`, `CHECKLIST_FUNCTION_LOSS`,
`COMPLETION_SEMANTICS_AMBIGUOUS`, `ARTIFACT_MATURITY_OVERCLAIM`,
`RAW_INLINE_SVG`, and `UNSAFE_OR_UNAVAILABLE_VISUAL`. The exact
repair enums are `REORDER`, `GROUP`, `EXPLAIN`, `EXAMPLE`, `VISUALIZE`, `LAYER`,
`MERGE`, `REFERENCE`, `MOVE`, `TRIM`, `RESTORE_FUNCTION`, and `BOUNDARY`.
Every failure binds exact Candidate line basis and one normal Review Finding.
The top-level Finding refs equal the union of outcome and assessment Findings.
Those Findings remain `ADVISORY_ONLY` and use the normal aggregate,
disposition, optimize, and re-review path.

Do not fail a long document, large necessary table, long appendix, Checklist,
or visual merely because of size. Fail only the reader outcome or diagnosed
issue. Specifically detect accidental Checklist function loss and wording that
makes a proposed product contract look implemented, `NOT_RUN` look PASS/FAIL,
or local Handoff look remotely sent, received, or approved. Record the exact
claim boundary `AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN`; Agent
review is not an observed human-reader test.

The dispatch field `writing_review_context.visual_source_scan` is produced
before any visual renderer or rich-content inspector. When its status is
`REVIEWABLE_UNSAFE_NOT_RENDERED`, access mode is `SOURCE_TEXT_ONLY` and render
status is `NOT_RENDERED`; every Reviewer may inspect only the exact Candidate
source bytes. For `RAW_INLINE_SVG`, the Writing Reviewer must return a visual
`FINDING` with `observation_status=NOT_RENDERED`, issue type
`RAW_INLINE_SVG`, and the exact scan line basis. `PASS` and `NOT_NEEDED` are
invalid. The Finding remains advisory and follows the ordinary disposition,
optimize, and re-review lifecycle. Candidate path/hash/permission failures stop
dispatch instead of becoming a Finding.

The source scanner resolves Markdown literal boundaries before interpreting
HTML comments. Arbitrary-length backtick/tilde fences with valid info strings,
indented code and inline code spans remain literals; real HTML comments are
then excluded in source order. A literal unclosed `<!--` must never hide a
later active `<svg>`. Reviewers use the supplied exact scan and do not
reinterpret code/comment examples as rendered visuals.

The dispatch field `writing_review_context.reader_visible_visual_pairs` is the
Controller-validated complete list of Markdown-visible SVG plus same-stem
`@2x.png` pairs. Mechanical validation proves only local safety, pairing, and
exact bytes; it does not prove semantic usefulness. The SVG `viewBox` defines
coordinate space, not pixels. Its PNG fallback must instead have a short side
of at least 320 px, a long side of at least 640 px, and preserve the SVG aspect
ratio within 5%. The Controller validates the complete inert SVG/PNG byte
streams; the Reviewer alone attests that it actually observed the rendered
relationship. Reader-visible raw inline `<svg>` is forbidden even when it looks
inert: move it to the Candidate `assets/` directory and reference the managed
SVG plus same-stem PNG pair. Before Ready and Release the Controller validates
the entire final asset tree, including files not referenced in Markdown, and
rejects malicious or safe-but-unreferenced orphan pairs, unpaired extras,
unknown visual files, symlinks and hash/tree drift. Remote rendered images are
also invalid. When that
list is non-empty,
a visual `PASS` must use `"observation_status": "OBSERVED"` and copy every pair
unchanged into `"visual_pair_refs"`. A visual `FINDING` uses `OBSERVED` with the
same exact pairs when assets exist, or `NOT_OBSERVED` with an empty list when a
needed visual is absent; source-only unsafe visuals use `NOT_RENDERED` as
described above. `NOT_NEEDED` is legal only when the dispatch list and source
scan issues are empty, must use `"observation_status": "NOT_NEEDED"`, an empty
`"visual_pair_refs"`, and a concrete reason. Example of the additional exact
fields for a present visual:

```json
{"verdict": "PASS", "observation_status": "OBSERVED", "visual_pair_refs": [{"svg_ref": {"path": "<exact Candidate-tree SVG path>", "hash": "<exact SVG hash>", "version": "reader-visual.v1"}, "png_ref": {"path": "<exact Candidate-tree @2x PNG path>", "hash": "<exact PNG hash>", "version": "reader-visual.v1"}}]}
```

Compact complete zero-Finding example (replace every representative ref and
readback statement with exact dispatch-bound evidence):

<!-- writing-reader-review-v3-zero-finding-contract -->
```json
{
  "schema_version": "document-experience-reader-review.v3",
  "authority": "ADVISORY_ONLY",
  "candidate_ref": {"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "version": "v0.1"},
  "candidate_tree_hash": "sha256:candidate-tree",
  "profile_ref": {"path": "references/policies/prd-writing-profile-v0.4.json", "hash": "sha256:profile-v0.4", "version": "0.4.0"},
  "guide_ref": {"path": "references/policies/prd-writing-guide-v0.4.md", "hash": "sha256:guide-v0.4", "version": "0.4.0"},
  "review_contract_ref": {"path": "references/reviewer-profiles/prd-writing-reader-review-v3.json", "hash": "sha256:reader-review-v3", "version": "v3"},
  "output_contract_ref": {"path": "references/templates/contracts/prd-v0.2.json", "hash": "sha256:output-contract", "version": "better-product-graph.prd.general.0.2"},
  "author_execution_ref": {"kind": "HOST_AGENT_ATTEMPT", "id": "attempt-author"},
  "reviewer_execution_ref": {"kind": "HOST_SUBAGENT_ATTEMPT", "id": "attempt-writing-reviewer"},
  "reviewer_role": "writing_standard",
  "isolated_input_refs": [
    {"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "version": "v0.1"},
    {"path": "references/policies/prd-writing-profile-v0.4.json", "hash": "sha256:profile-v0.4", "version": "0.4.0"},
    {"path": "references/policies/prd-writing-guide-v0.4.md", "hash": "sha256:guide-v0.4", "version": "0.4.0"},
    {"path": "references/reviewer-profiles/prd-writing-reader-review-v3.json", "hash": "sha256:reader-review-v3", "version": "v3"},
    {"path": "references/templates/contracts/prd-v0.2.json", "hash": "sha256:output-contract", "version": "better-product-graph.prd.general.0.2"}
  ],
  "reader_readback": {
    "problem_and_outcome": "高频用户需要先看到必须处理的信息，产品要降低遗漏风险。",
    "primary_relationships": "风险消息优先于普通通知。",
    "mental_model": [
      {"name": "信号", "role": "提供待处理信息"},
      {"name": "规则", "role": "决定优先级"},
      {"name": "结果", "role": "先呈现高风险消息"}
    ],
    "main_path_and_recovery": "系统分类并展示优先级；分类失败时保留原消息并允许重试。",
    "decision_conditions_and_risks": "仅在分类可靠时采用；主要风险是错误降级风险消息。",
    "navigation_map": [
      {"target": "PRODUCT_RULES", "location": "第 4 节"},
      {"target": "ACCEPTANCE", "location": "第 6 节"},
      {"target": "RISKS_UNKNOWNS_NEXT", "location": "第 7 节"}
    ]
  },
  "reader_outcome_failures": [],
  "verbosity_assessment": {"verdict": "PASS", "issue_types": [], "repair_techniques": [], "basis_refs": [], "finding_refs": [], "reason": "主路径分层清楚，没有重复合同。"},
  "checklist_assessment": {"verdict": "PASS", "issue_types": [], "repair_techniques": [], "basis_refs": [], "finding_refs": [], "reason": "Checklist 功能保持完整。"},
  "visual_assessment": {"verdict": "NOT_NEEDED", "observation_status": "NOT_NEEDED", "visual_pair_refs": [], "issue_types": [], "repair_techniques": [], "basis_refs": [], "finding_refs": [], "reason": "关系简单，文字足够表达。"},
  "finding_refs": [],
  "claim_boundary": "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN"
}
```

Compact one-Finding example. The ordinary `semantic_output.findings` must also
contain the complete normal Finding `f-writing-001` with its concern level,
exact basis, impact, recommendation, repair target, confidence, role and
profile; the Writing Review only links that Finding:

<!-- writing-reader-review-v3-one-finding-contract -->
```json
{
  "schema_version": "document-experience-reader-review.v3",
  "authority": "ADVISORY_ONLY",
  "candidate_ref": {"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "version": "v0.1"},
  "candidate_tree_hash": "sha256:candidate-tree",
  "profile_ref": {"path": "references/policies/prd-writing-profile-v0.4.json", "hash": "sha256:profile-v0.4", "version": "0.4.0"},
  "guide_ref": {"path": "references/policies/prd-writing-guide-v0.4.md", "hash": "sha256:guide-v0.4", "version": "0.4.0"},
  "review_contract_ref": {"path": "references/reviewer-profiles/prd-writing-reader-review-v3.json", "hash": "sha256:reader-review-v3", "version": "v3"},
  "output_contract_ref": {"path": "references/templates/contracts/prd-v0.2.json", "hash": "sha256:output-contract", "version": "better-product-graph.prd.general.0.2"},
  "author_execution_ref": {"kind": "HOST_AGENT_ATTEMPT", "id": "attempt-author"},
  "reviewer_execution_ref": {"kind": "HOST_SUBAGENT_ATTEMPT", "id": "attempt-writing-reviewer"},
  "reviewer_role": "writing_standard",
  "isolated_input_refs": [
    {"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "version": "v0.1"},
    {"path": "references/policies/prd-writing-profile-v0.4.json", "hash": "sha256:profile-v0.4", "version": "0.4.0"},
    {"path": "references/policies/prd-writing-guide-v0.4.md", "hash": "sha256:guide-v0.4", "version": "0.4.0"},
    {"path": "references/reviewer-profiles/prd-writing-reader-review-v3.json", "hash": "sha256:reader-review-v3", "version": "v3"},
    {"path": "references/templates/contracts/prd-v0.2.json", "hash": "sha256:output-contract", "version": "better-product-graph.prd.general.0.2"}
  ],
  "reader_readback": {
    "problem_and_outcome": "高频用户需要先看到必须处理的信息，产品要降低遗漏风险。",
    "primary_relationships": "风险消息优先于普通通知。",
    "mental_model": [
      {"name": "信号", "role": "提供待处理信息"},
      {"name": "规则", "role": "决定优先级"},
      {"name": "结果", "role": "先呈现高风险消息"}
    ],
    "main_path_and_recovery": "系统分类并展示优先级；分类失败时保留原消息并允许重试。",
    "decision_conditions_and_risks": "仅在分类可靠时采用；主要风险是错误降级风险消息。",
    "navigation_map": [
      {"target": "PRODUCT_RULES", "location": "第 4 节"},
      {"target": "ACCEPTANCE", "location": "第 6 节"},
      {"target": "RISKS_UNKNOWNS_NEXT", "location": "第 7 节"}
    ]
  },
  "reader_outcome_failures": [
    {"outcome": "LOCATE", "basis_refs": [{"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "start_line": 20, "end_line": 28}], "reason": "风险和未知散落，无法直接定位。", "finding_id": "f-writing-001"}
  ],
  "verbosity_assessment": {"verdict": "FINDING", "issue_types": ["SEMANTIC_REPETITION"], "repair_techniques": ["REFERENCE"], "basis_refs": [{"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "start_line": 20, "end_line": 28}], "finding_refs": ["f-writing-001"], "reason": "同一风险规则在多处重复定义。"},
  "checklist_assessment": {"verdict": "PASS", "issue_types": [], "repair_techniques": [], "basis_refs": [], "finding_refs": [], "reason": "Checklist 功能保持完整。"},
  "visual_assessment": {"verdict": "NOT_NEEDED", "observation_status": "NOT_NEEDED", "visual_pair_refs": [], "issue_types": [], "repair_techniques": [], "basis_refs": [], "finding_refs": [], "reason": "关系简单，文字足够表达。"},
  "finding_refs": ["f-writing-001"],
  "claim_boundary": "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN"
}
```

The linked normal Review Finding is not implicit. Copy this complete Node Result
shape and replace every representative ref with the exact dispatch-bound value:

<!-- review-parallel-v3-one-finding-node-result-contract -->
```json
{
  "schema_version": "node-result.v1",
  "node_id": "review.parallel",
  "attempt_id": "attempt-review-example",
  "producer": {"kind": "HOST_AGENT"},
  "instruction_ref": "references/atomic-skills/prd-review/INSTRUCTIONS.md",
  "instruction_hash": "sha256:replace-with-dispatch-hash",
  "input_refs": ["product-commitment.json"],
  "input_hashes": {"product-commitment.json": "sha256:commitment"},
  "resource_refs": [],
  "semantic_output": {
    "candidate_ref": {"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "version": "v0.1"},
    "reviewer_role": "combined-independent-reviewer",
    "reviewer_profile": "LIGHT_COMBINED",
    "roles_covered": ["product", "engineering_feasibility", "testability"],
    "authority": "ADVISORY_ONLY",
    "goal_fidelity_refs": {
      "profile_ref": {"path": "references/reviewer-profiles/product-goal-fidelity-v0.1.json", "hash": "sha256:profile", "version": "v0.1"},
      "rubric_ref": {"path": "references/reviewer-profiles/product-goal-fidelity-rubric-v0.1.json", "hash": "sha256:rubric", "version": "v0.1"},
      "packet_contract_ref": {"path": "references/reviewer-profiles/product-goal-fidelity-packet-v0.1.json", "hash": "sha256:packet", "version": "v0.1"},
      "commitment_refs": [{"path": "product-commitment.json", "hash": "sha256:commitment", "version": 1}]
    },
    "goal_fidelity_packet": {
      "goal": "降低遗漏风险，并保持批准的范围和验收承诺。",
      "candidate_ref": {"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "version": "v0.1"},
      "commitment_refs": [{"path": "product-commitment.json", "hash": "sha256:commitment", "version": 1}]
    },
    "writing_coverage_ref": {"path": ".better-product-graph/runs/run-example/artifacts/writing-review-v3.json", "hash": "sha256:writing-review", "version": 3},
    "findings": [
      {
        "finding_id": "f-writing-001",
        "topic_id": "writing.locate",
        "stance": "REVISE",
        "concern": "风险与未知散落在多个位置，读者无法快速定位。",
        "concern_level": "MEDIUM",
        "basis_refs": [{"path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md", "hash": "sha256:candidate", "start_line": 20, "end_line": 28}],
        "upstream_commitment_refs": [{"path": "product-commitment.json", "hash": "sha256:commitment", "version": 1}],
        "affected_scope": ["风险、未知与下一步"],
        "possible_impact": "产品经理可能遗漏停止条件或误判当前成熟度。",
        "professional_recommendation": "保留一个权威位置，其余章节只引用该位置。",
        "confidence": "HIGH",
        "confidence_basis": "完整读回后仍无法从导航直接定位，且有精确行号依据。",
        "reviewer_role": "writing_standard",
        "reviewer_profile": "PRD_WRITING_READER_V3",
        "cross_check_status": "INDEPENDENT_FIRST_PASS",
        "repair_target": "CURRENT_PRD",
        "disposition": "PENDING"
      }
    ]
  },
  "artifact_refs": [
    {
      "role": "writing_coverage",
      "path": ".better-product-graph/runs/run-example/artifacts/writing-review-v3.json",
      "hash": "sha256:writing-review",
      "version": 3
    }
  ]
}
```

### Legacy Profile v0.2 Writing Standard subreview

When `writing_review_context` supplies `required_rule_ids` and
`required_check_ids`, retain the existing `document-experience-coverage.v1`
contract below. Do not use this 13+10 legacy shape for the v3 path.

`review.parallel` 还必须在现有 Review 内启动一个独立 Writing Reviewer；这不是新 Node，也不产生新 Gate。主 Host 把 dispatch 返回的 `writing_review_context.isolated_input_refs` 原样交给一个新的 subagent execution。首轮 Writing Reviewer 只能读取这四项：exact Candidate、exact Writing Profile、exact Writing Guide、exact PRD Output Contract；不得读取作者隐藏推理、可变聊天上下文或其他 Reviewer Findings。

Writing Reviewer 必须逐项覆盖 `writing_review_context.required_rule_ids` 的 13 条规则和 `required_check_ids` 的 10 个交稿问题。每项只允许 `PASS`、`FINDING`、`NOT_APPLICABLE`，并必须给出 Candidate exact path/hash、有效起止行号和简短理由。`FINDING` 必须链接一个正常 Review Finding；该 Finding 使用 `reviewer_role=writing_standard`、`reviewer_profile=WRITING_STANDARD`，并继续遵守现有 Finding 严重级别、依据和最小修改建议合同。`NOT_APPLICABLE` 仍需具体理由。不能用 `findings=[]` 代替 13+10 的覆盖证据。

把完整覆盖保存为一个 project-local JSON 文件，计算最终字节 hash，并在 Node Result 中同时提交 `semantic_output.writing_coverage_ref` 与恰好一个同身份的 `artifact_refs[role=writing_coverage]`。覆盖文件采用以下 closed-world 合同：

```json
{
  "schema_version": "document-experience-coverage.v1",
  "candidate_ref": {"path": "<copy context>", "hash": "<copy context>", "version": "<copy context>"},
  "candidate_tree_hash": "<copy writing_review_context.candidate_tree_hash>",
  "profile_ref": {"path": "<copy context>", "hash": "<copy context>", "version": "<copy context>"},
  "guide_ref": {"path": "<copy context>", "hash": "<copy context>", "version": "<copy context>"},
  "output_contract_ref": {"path": "<copy context>", "hash": "<copy context>", "version": "<copy context>"},
  "author_execution_ref": {"kind": "HOST_AGENT_ATTEMPT", "id": "<copy context>"},
  "reviewer_execution_ref": {"kind": "HOST_SUBAGENT_ATTEMPT", "id": "<new distinct durable attempt id>"},
  "reviewer_role": "writing_standard",
  "isolated_input_refs": ["<copy the four context refs in exact order>"],
  "required_rule_results": [
    {
      "rule_id": "<each required rule id exactly once>",
      "verdict": "PASS | FINDING | NOT_APPLICABLE",
      "basis_refs": [{"path": "<Candidate path>", "hash": "<Candidate hash>", "start_line": 1, "end_line": 3}],
      "reason": "<short concrete reason>",
      "finding_id": "<required only for FINDING>"
    }
  ],
  "delivery_check_results": [
    {
      "check_id": "<CHECK-01 through CHECK-10 exactly once>",
      "verdict": "PASS | FINDING | NOT_APPLICABLE",
      "basis_refs": [{"path": "<Candidate path>", "hash": "<Candidate hash>", "start_line": 1, "end_line": 3}],
      "reason": "<short concrete reason>",
      "finding_id": "<required only for FINDING>"
    }
  ],
  "finding_refs": ["<every FINDING-linked writing Finding ID exactly once>"]
}
```

`reviewer_execution_ref` 证明的是 Host 记录了不同的 durable attempt，不是外部加密身份认证；不得把它夸大成模型身份或人员身份的强证明。Writing Finding 仍是 `ADVISORY_ONLY`，进入现有 aggregate 与 disposition；未处置不能 finalize，但 Reviewer 自己没有批准或阻塞权。

If the independent review finds no material issue, do not invent one. Use the
complete zero-Finding semantic shape below, replacing every representative ref
with its exact dispatched path/hash/version. A combined LIGHT attempt still
declares all three logical roles.

<!-- review-parallel-zero-finding-contract -->
```json
{
  "candidate_ref": {
    "path": "artifacts/prds/archived/EXAMPLE/v0.1/EXAMPLE_v0.1.md",
    "hash": "sha256:prd",
    "version": "v0.1"
  },
  "reviewer_role": "combined-independent-reviewer",
  "reviewer_profile": "LIGHT_COMBINED",
  "roles_covered": ["product", "engineering_feasibility", "testability"],
  "authority": "ADVISORY_ONLY",
  "goal_fidelity_refs": {
    "profile_ref": {
      "path": "references/reviewer-profiles/product-goal-fidelity-v0.1.json",
      "hash": "sha256:profile",
      "version": "v0.1"
    },
    "rubric_ref": {
      "path": "references/reviewer-profiles/product-goal-fidelity-rubric-v0.1.json",
      "hash": "sha256:rubric",
      "version": "v0.1"
    },
    "packet_contract_ref": {
      "path": "references/reviewer-profiles/product-goal-fidelity-packet-v0.1.json",
      "hash": "sha256:packet",
      "version": "v0.1"
    },
    "commitment_refs": [
      {"path": ".better-product-graph/decisions/decision-example/DECISION_v1.json", "hash": "sha256:decision", "version": 1}
    ]
  },
  "goal_fidelity_packet": {
    "goal": "Preserve the exact approved product outcome, scope, guardrails, and acceptance commitments.",
    "candidate_ref": {
      "path": "artifacts/prds/archived/EXAMPLE/v0.1/EXAMPLE_v0.1.md",
      "hash": "sha256:prd",
      "version": "v0.1"
    },
    "commitment_refs": [
      {"path": ".better-product-graph/decisions/decision-example/DECISION_v1.json", "hash": "sha256:decision", "version": 1}
    ]
  },
  "writing_coverage_ref": {
    "path": ".better-product-graph/runs/<run-id>/artifacts/writing-coverage-v1.json",
    "hash": "sha256:writing-coverage",
    "version": 1
  },
  "findings": []
}
```

## Aggregate and dispositions

When `node_id=review.aggregate`, use only the exact current Candidate and the committed `review.parallel` result in the dispatch inputs. Do not summarize away, add, rename, or silently drop Findings. Before submitting, write two distinct project-local JSON artifacts and compute their real hashes:

1. `review_aggregate`: the exact aggregate object below, including the exact completed Reviewer attempt and its `roles_covered` set.
2. `review_dispositions`: one explicit non-empty status for every Finding ID, exactly once, bound to the same Candidate hash and version. If all Reviewers return no Finding, keep both `findings` and `dispositions` present as `[]`; never invent a Finding just to make the aggregate non-empty.

Disposition routing is exact and must not be guessed. To adopt a Finding for the
current PRD and route to `prd.optimize`, the Finding itself must declare
`repair_target`: `CURRENT_PRD`, and its matching disposition must use exact
`status`: `ACCEPTED_CURRENT_PRD_REPAIR`; `repair_scope` must be a non-empty JSON list naming the sections to revise. Any other non-empty status records an
unadopted or externally retained advisory disposition and does not authorize
`prd.optimize`; route that complete aggregate to `review.finalize` instead. The
Controller will reject an Optimize request that lacks this exact accepted repair
before persisting the aggregate.

The `semantic_output` must equal the complete aggregate artifact plus the same `dispositions` array. Both must preserve the exact committed `writing_coverage_ref`; do not summarize or replace it. The two aggregate `artifact_refs` must each contain exact `role`, `path`, `hash`, and `version`; paths may not leave the project and neither file may be a symlink. Do not submit until the Candidate path/hash/version, Reviewer attempt, Reviewer logical roles, Writing Coverage, Finding IDs, disposition coverage, JSON files, and hashes all agree. Missing or stale facts are a repair condition, not permission to continue to `review.finalize`.

`disagreements` is always present and is a JSON list. Use `[]` when no material disagreement exists. Every non-empty item must include a non-empty `topic_id` and a unique non-empty `finding_ids` (or generated `findings`) list that refers only to Findings preserved in this aggregate; if `stances` is present, it must cover those Finding refs one-for-one.

Collection cardinality is exact: `attempts` must contain at least one completed Reviewer attempt and every attempt must retain a non-empty `roles_covered`; `findings` must be present and may be `[]`; `dispositions` must be present and must be `[]` exactly when `findings` is `[]`, otherwise it must close every Finding ID exactly once; `disagreements` must be present and may be `[]`, while every non-empty reference must name an existing Finding. Missing, `null`, wrong-type, empty-when-required, duplicate, or unmatched collections are repair conditions.

This is a closed-world `review.aggregate` contract. Do not add extension or future-authority fields. The exact allowed keys are:

- `semantic_output`: `schema_version`, `authority`, `candidate_ref`, `attempts`, `findings`, `disagreements`, `dispositions`, `writing_coverage_ref`.
- `review_aggregate` artifact: the same keys except `dispositions`.
- `candidate_ref`: `path`, `hash`, `version`; each attempt: `attempt_id`, `status`, `roles_covered`.
- each Finding: `finding_id`, `topic_id`, `stance`, `concern`, `concern_level`, `basis_refs`, `upstream_commitment_refs`, `affected_scope`, `possible_impact`, `professional_recommendation`, `confidence`, `confidence_basis`, `reviewer_role`, `reviewer_profile`, `cross_check_status`, `repair_target`, `disposition`.
- each disagreement: `topic_id`, exactly one of `finding_ids` or generated `findings`, and optional `stances`.
- `review_dispositions` artifact: `schema_version`, `candidate_hash`, `candidate_version`, `dispositions`; each disposition: `finding_id`, `status`, and only when applicable `repair_scope` or `reason`.
- each of the two aggregate `artifact_refs`: `role`, `path`, `hash`, `version`; an existing non-authoritative `declared_role` may be retained, but it never changes the Controller-owned role.

An unknown key at any of these paths is a repair condition. Remove it, recompute the final artifact hash, and resubmit the same unconsumed attempt. The general Node Result envelope remains governed separately by `node-result.v1`.

<!-- review-aggregate-semantic-output-contract -->
```json
{
  "semantic_output": {
    "schema_version": "review-aggregate.v1",
    "authority": "ADVISORY_ONLY",
    "candidate_ref": {
      "path": "<exact current Candidate path from dispatch>",
      "hash": "<exact current Candidate hash from dispatch>",
      "version": "<exact current Candidate version>"
    },
    "attempts": [
      {
        "attempt_id": "<exact committed review.parallel attempt_id>",
        "status": "COMPLETED",
        "roles_covered": ["product", "engineering_feasibility", "testability"]
      }
    ],
    "findings": ["<copy each complete review.parallel Finding object exactly>"],
    "disagreements": [],
    "dispositions": [
      {
        "finding_id": "<exact CURRENT_PRD Finding ID>",
        "status": "ACCEPTED_CURRENT_PRD_REPAIR",
        "repair_scope": ["<exact PRD section to revise>"]
      }
    ],
    "writing_coverage_ref": {"path": "<exact committed path>", "hash": "<exact committed hash>", "version": 1}
  },
  "aggregate_artifact": {
    "schema_version": "review-aggregate.v1",
    "authority": "ADVISORY_ONLY",
    "candidate_ref": {
      "path": "<same exact Candidate path>",
      "hash": "<same exact Candidate hash>",
      "version": "<same exact Candidate version>"
    },
    "attempts": [
      {
        "attempt_id": "<same review.parallel attempt_id>",
        "status": "COMPLETED",
        "roles_covered": ["product", "engineering_feasibility", "testability"]
      }
    ],
    "findings": ["<same complete Finding objects>"],
    "disagreements": [],
    "writing_coverage_ref": {"path": "<same exact path>", "hash": "<same exact hash>", "version": 1}
  },
  "disposition_artifact": {
    "schema_version": "review-dispositions.v1",
    "candidate_hash": "<same exact Candidate hash>",
    "candidate_version": "<same exact Candidate version>",
    "dispositions": [
      {
        "finding_id": "<same exact CURRENT_PRD Finding ID>",
        "status": "ACCEPTED_CURRENT_PRD_REPAIR",
        "repair_scope": ["<same exact PRD section to revise>"]
      }
    ]
  },
  "artifact_refs": [
    {
      "role": "review_aggregate",
      "path": "<project-local aggregate JSON path>",
      "hash": "<sha256 of exact aggregate JSON bytes>",
      "version": 1
    },
    {
      "role": "review_dispositions",
      "path": "<project-local dispositions JSON path>",
      "hash": "<sha256 of exact dispositions JSON bytes>",
      "version": 1
    }
  ]
}
```

When the exact committed Reviewer result contains no Findings, use this complete collection shape in both semantic output and artifacts:

<!-- review-aggregate-no-finding-example -->
```json
{
  "semantic_output": {
    "schema_version": "review-aggregate.v1",
    "authority": "ADVISORY_ONLY",
    "candidate_ref": {"path": "<exact path>", "hash": "<exact hash>", "version": "<exact version>"},
    "attempts": [
      {
        "attempt_id": "<exact committed review.parallel attempt_id>",
        "status": "COMPLETED",
        "roles_covered": ["product", "engineering_feasibility", "testability"]
      }
    ],
    "findings": [],
    "disagreements": [],
    "dispositions": [],
    "writing_coverage_ref": {"path": "<exact committed path>", "hash": "<exact committed hash>", "version": 1}
  },
  "aggregate_artifact": {
    "schema_version": "review-aggregate.v1",
    "authority": "ADVISORY_ONLY",
    "candidate_ref": {"path": "<same exact path>", "hash": "<same exact hash>", "version": "<same exact version>"},
    "attempts": [
      {
        "attempt_id": "<same review.parallel attempt_id>",
        "status": "COMPLETED",
        "roles_covered": ["product", "engineering_feasibility", "testability"]
      }
    ],
    "findings": [],
    "disagreements": [],
    "writing_coverage_ref": {"path": "<same exact path>", "hash": "<same exact hash>", "version": 1}
  },
  "disposition_artifact": {
    "schema_version": "review-dispositions.v1",
    "candidate_hash": "<same exact Candidate hash>",
    "candidate_version": "<same exact Candidate version>",
    "dispositions": []
  }
}
```

The main Host Agent decides which advisory repairs to adopt. When `node_id=prd.optimize`, read the exact `optimize_context`: revise only its accepted current-PRD Findings, use its exact source Candidate and `next_version`, and author the complete replacement PRD rather than a patch. Submit `source_candidate_ref`, the declared `{prd_id, version}` Candidate identity, the canonical `proposed_scope_projection`, full `document_markdown`, `template_mapping`, and metadata. Preserve the user's explicit/current working language (fallback `zh-CN`) in `metadata.document_language`; use a short human title in that language rather than introducing a hidden English slug. Recompute the immutable `<prd_id>_<short_title>_<version>_<date>` stem for the new version, and make the directory, Markdown filename, and unique H1 exact matches. Never rename the source Candidate in place. The projection contains exactly the Plan-owned Slice fields `id`, `user_outcome`, sorted `modules`, `iteration`, sorted `dependencies`, `validation`, `split_reason`, and `delivery_intent`. Caller claims such as `scope_changed=false` do not decide the route: the Controller recomputes the exact Plan projection. A mismatch returns `PLAN_RECONCILE_REQUIRED` before Candidate persistence; an unclassifiable or missing projection returns `AMBIGUOUS_SCOPE_CHANGE` for the current Owner, never a Reviewer Gate.

`prd.optimize` may also include the exact closed `prd-asset-change-set.v1`
defined in PRD Generate. `upsert` adds or replaces managed `.svg`/`@2x.png`
bytes from exact regular non-symlink source refs; `remove` deletes names from
the copied source Candidate asset tree. Unknown fields, traversal, hash drift,
unsafe payloads, or an incomplete visible pair fail before archive. The new
Candidate tree invalidates the prior Review and re-enters `review.parallel`.

Metadata must preserve upstream authority and the closed active-scope/trace/runtime contracts, declare exact `supersedes`, and include a `change_log` with the source Candidate, every repaired Finding ID, all unadopted dispositions unchanged, material delta, and re-review scope. `optimize_context.metadata_authority.spec_traceability` is the complete closed `spec-traceability.v1` selected by the Controller, including the exact current `source_candidate` and committed `review_aggregate_result` origins. Copy it byte-for-byte into `metadata.spec_traceability`; do not extend, replace, infer, reorder, or retain superseded trace roles yourself. A Product Planning reconciliation carries those same two roles into its later `prd.generate`. A legal Evals specification update may be submitted, but in the current skills-only Host REQUIRED Evals must remain `REVIEW_PENDING`/`NOT_RUN` without active stale Pack/review refs; typed Pack/review consistency cannot prove independent fulfillment or grant release authority. Python validates and archives these Agent-authored bytes; it never generates the revision.

The `metadata.change_log` contract is closed-world. Copy `source_candidate_ref` and `unadopted_dispositions` byte-for-byte from `optimize_context`. Build `repaired_finding_ids` from every `accepted_dispositions[].finding_id` in the same order; do not use only the Findings mentioned in prose. `material_delta` and `rereview_scope` are non-empty lists of non-empty human-readable strings. Do not add private closure flags or rename these keys.

<!-- prd-optimize-change-log-contract -->
```json
{
  "schema_version": "prd-optimize-change-log.v1",
  "allowed_keys": [
    "source_candidate_ref",
    "repaired_finding_ids",
    "unadopted_dispositions",
    "material_delta",
    "rereview_scope"
  ],
  "valid_example": {
    "source_candidate_ref": {
      "path": "<copy optimize_context.source_candidate_ref.path>",
      "hash": "<copy optimize_context.source_candidate_ref.hash>",
      "version": "<copy optimize_context.source_candidate_ref.version>"
    },
    "repaired_finding_ids": [
      "<copy every optimize_context.accepted_dispositions[].finding_id in order>"
    ],
    "unadopted_dispositions": [
      "<copy every complete optimize_context.unadopted_dispositions[] object exactly>"
    ],
    "material_delta": [
      "<what materially changed in this PRD revision>"
    ],
    "rereview_scope": [
      "<which revised PRD sections the next reviewers must check>"
    ]
  }
}
```

Stop at the bounded round/no-progress limit, record unadopted or external-review dispositions, render the same-version companion view, and let deterministic `review.finalize` check completeness before the single `prd.ready.gate`.
