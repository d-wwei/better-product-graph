# PRD Writing Eval Review — installed evaluation-only contract

Use this instruction only when the Controller dispatch says:

- `node_id=writing-eval.review`;
- `validator=document_experience_reader_eval_v3_1`;
- `writing_eval_context.evaluation_only=true`;
- `writing_eval_context.review_schema=document-experience-reader-eval.v3.1`.

This is an internal product evaluation, not an ordinary Product Run Review. It cannot
approve a PRD, enter Review aggregate, Ready, Release, or Handoff. Its single terminal
effect is to close this exact Writing Eval Run after the Controller validates one
exact result.

## Custody and independence

Read only `writing_eval_context.isolated_input_refs`: the exact Candidate, v0.4
Profile, v0.4 Guide, this instruction, the eval-only Reviewer Contract, and the PRD
Output Contract. Do not read evaluator expected results, preregistration source
files, author reasoning, chat history, other Reviews, or source code. Your execution
must be a distinct `HOST_SUBAGENT_ATTEMPT`; its ID must differ from the author ID.
The Candidate ref is a Controller-owned immutable snapshot. Read and cite that exact
snapshot only; do not return to the mutable source Candidate, suite, or case files.

Before reading for problems, independently write the six-field reader readback. Then
record only observed reader-outcome failures. Length alone is never a failure. A
necessary large table or long appendix may pass. If content is repetitive or flat,
name the primary diagnosis and smallest repair from the dispatched enum set. Do not
manufacture a Finding to demonstrate effort.

## Closed enums and conditional rules

Use only these exact values. Never emit `FAIL` or `NOT_PROVIDED`; those are not
legal values in this result contract.

- `reader_outcome_failures[].outcome`: `UNDERSTAND | SEE | MODEL | RETELL | DECIDE | LOCATE`.
- `verbosity_assessment.verdict`: `PASS | FINDING`.
- `checklist_assessment.verdict`: `PASS | FINDING`.
- `visual_assessment.verdict`: `PASS | FINDING | NOT_NEEDED`.
- `visual_assessment.observation_status`: `OBSERVED | NOT_OBSERVED | NOT_NEEDED`.
- `result`: `PASS | FINDING`.
- Assessment `issue_types`: `SEMANTIC_REPETITION | FLAT_PEER_OVERLOAD |
  REPRESENTATION_COLLISION | DETAIL_IN_MAIN_PATH | DENSE_TABLE |
  JARGON_INTRUSION | CHECKLIST_FUNCTION_LOSS |
  COMPLETION_SEMANTICS_AMBIGUOUS | ARTIFACT_MATURITY_OVERCLAIM`.
- Assessment `repair_techniques`: `REORDER | GROUP | EXPLAIN | EXAMPLE |
  VISUALIZE | LAYER | MERGE | REFERENCE | MOVE | TRIM | RESTORE_FUNCTION |
  BOUNDARY`.

All objects are closed: do not add fields that are absent from the complete shapes
below. Every exact ref has exactly `path`, `hash`, and `version`. Every `basis_refs`
list is non-empty; each entry has exactly `path`, `hash`, `start_line`, and
`end_line`, binds the exact Candidate, and uses an in-range inclusive line span.

The readback and observed-failure structures are also hard contracts:

- `reader_readback` has exactly the six fields shown in the examples. Its four
  prose fields are non-empty.
- `mental_model` contains between three and five components. Every component
  has exactly `name` and `role`, both non-empty, and each component `name` must be unique.
- `navigation_map` contains exactly three entries, one for each required target:
  `PRODUCT_RULES`, `ACCEPTANCE`, and `RISKS_UNKNOWNS_NEXT`. Each target appears
  exactly once and each `location` is non-empty.
- Each `reader_outcome_failures[]` object has exactly `outcome`, `basis_refs`,
  and `reason`. The outcome uses the allowed enum above, `basis_refs` follows the
  exact Candidate-bound rule, and `reason` is non-empty. Each outcome may appear at most once.
- `issue_types` and `repair_techniques` are unique lists of only the allowed enum
  values; do not repeat a value.

Every assessment needs a non-empty Candidate-bound `basis_refs` list and a short
`reason`. Apply these coupled rules exactly:

- An assessment with `verdict=PASS` has empty `issue_types` and
  `repair_techniques`.
- An assessment with `verdict=FINDING` has at least one allowed `issue_types`
  value and at least one allowed `repair_techniques` value. A problem must have `verdict=FINDING`;
  do not represent it with a `FAIL` value.
- `visual_assessment` with no reader-visible visual and no visual Finding uses
  `verdict=NOT_NEEDED`, `observation_status=NOT_NEEDED`, and
  `visual_pair_refs=[]`.
- A visual `PASS` has `observation_status=OBSERVED` and lists every exact
  dispatched reader-visible SVG/PNG pair in `visual_pair_refs`. Each pair is a
  closed object with exactly `svg_ref` and `png_ref`; each ref has exactly
  `path`, `hash`, and `version` copied from the dispatch.
- A visual `FINDING` lists every exact dispatched reader-visible SVG/PNG pair.
  Its `observation_status` is `OBSERVED` when such pairs exist and
  `NOT_OBSERVED` when none exist. Missing visuals that are themselves a Finding
  therefore use `FINDING + NOT_OBSERVED + []`, never `NOT_PROVIDED`.
- `result=PASS` requires no reader-outcome failures, no assessment Finding, and
  both primary fields set to `null`.
- `result=FINDING` requires at least one reader-outcome failure or assessment
  with `verdict=FINDING`. `primary_diagnosis` and
  `primary_repair_technique` must copy exact enum values from a Finding
  assessment. Therefore a reader-outcome failure alone is insufficient for a
  valid aggregate Finding: also record the evidence-backed assessment Finding
  that supplies those primary values.

## Closed result

Copy every exact authority field from the dispatch and its returned
`preregistration_checkpoint_ref`. Basis lines must point to the exact Candidate
path/hash and stay within the document. Use this complete zero-Finding shape:

<!-- writing-eval-result-contract -->
```json
{
  "schema_version": "document-experience-reader-eval.v3.1",
  "evaluation_only": true,
  "authority": "ADVISORY_ONLY",
  "suite_id": "COPY_EXACT_CONTEXT_SUITE_ID",
  "case_id": "COPY_EXACT_CONTEXT_CASE_ID",
  "node_id": "writing-eval.review",
  "attempt_id": "COPY_EXACT_DISPATCH_ATTEMPT_ID",
  "instruction_ref": "COPY_EXACT_DISPATCH_INSTRUCTION_REF",
  "instruction_hash": "COPY_EXACT_DISPATCH_INSTRUCTION_HASH",
  "input_refs": ["COPY_EVERY_EXACT_DISPATCH_INPUT_REF"],
  "input_hashes": {"COPY_EXACT_INPUT_PATH": "COPY_EXACT_INPUT_HASH"},
  "preregistration_checkpoint_ref": {
    "path": "COPY_RETURNED_CHECKPOINT_PATH",
    "hash": "COPY_RETURNED_CHECKPOINT_HASH",
    "version": 1
  },
  "candidate_ref": {
    "path": "COPY_EXACT_CONTEXT_CANDIDATE_PATH",
    "hash": "COPY_EXACT_CONTEXT_CANDIDATE_HASH",
    "version": 1
  },
  "profile_ref": {
    "path": "COPY_EXACT_CONTEXT_PROFILE_PATH",
    "hash": "COPY_EXACT_CONTEXT_PROFILE_HASH",
    "version": "0.4.0"
  },
  "guide_ref": {
    "path": "COPY_EXACT_CONTEXT_GUIDE_PATH",
    "hash": "COPY_EXACT_CONTEXT_GUIDE_HASH",
    "version": "0.4.0"
  },
  "reviewer_resource_ref": {
    "path": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_PATH",
    "hash": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_HASH",
    "version": "v3.1"
  },
  "output_contract_ref": {
    "path": "COPY_EXACT_CONTEXT_OUTPUT_CONTRACT_PATH",
    "hash": "COPY_EXACT_CONTEXT_OUTPUT_CONTRACT_HASH",
    "version": "COPY_EXACT_CONTEXT_OUTPUT_CONTRACT_VERSION"
  },
  "author_execution_ref": {
    "kind": "HOST_AGENT_ATTEMPT",
    "id": "COPY_EXACT_CONTEXT_AUTHOR_ID"
  },
  "reviewer_execution_ref": {
    "kind": "HOST_SUBAGENT_ATTEMPT",
    "id": "THIS_DISTINCT_REVIEWER_ATTEMPT_ID"
  },
  "reviewer_role": "writing_standard",
  "isolated_input_refs": [
    {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "version": 1},
    {"path": "COPY_PROFILE", "hash": "COPY_HASH", "version": "0.4.0"},
    {"path": "COPY_GUIDE", "hash": "COPY_HASH", "version": "0.4.0"},
    {"path": "COPY_INSTRUCTION", "hash": "COPY_HASH", "version": "v1"},
    {"path": "COPY_REVIEWER_RESOURCE", "hash": "COPY_HASH", "version": "v3.1"},
    {"path": "COPY_OUTPUT_CONTRACT", "hash": "COPY_HASH", "version": "COPY_VERSION"}
  ],
  "reader_readback": {
    "problem_and_outcome": "用自己的话复述问题与结果",
    "primary_relationships": "复述主要关系",
    "mental_model": [
      {"name": "对象一", "role": "它负责什么"},
      {"name": "对象二", "role": "它负责什么"},
      {"name": "对象三", "role": "它负责什么"}
    ],
    "main_path_and_recovery": "复述主路径与恢复路径",
    "decision_conditions_and_risks": "复述决策条件与风险",
    "navigation_map": [
      {"target": "PRODUCT_RULES", "location": "规则所在章节"},
      {"target": "ACCEPTANCE", "location": "验收所在章节"},
      {"target": "RISKS_UNKNOWNS_NEXT", "location": "风险与下一步所在章节"}
    ]
  },
  "reader_outcome_failures": [],
  "verbosity_assessment": {
    "verdict": "PASS",
    "issue_types": [],
    "repair_techniques": [],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "简短观察理由"
  },
  "checklist_assessment": {
    "verdict": "PASS",
    "issue_types": [],
    "repair_techniques": [],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "简短观察理由"
  },
  "visual_assessment": {
    "verdict": "NOT_NEEDED",
    "observation_status": "NOT_NEEDED",
    "visual_pair_refs": [],
    "issue_types": [],
    "repair_techniques": [],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "为什么该文档不需要视觉模型"
  },
  "result": "PASS",
  "primary_diagnosis": null,
  "primary_repair_technique": null,
  "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN"
}
```

Here is a complete legal one-Finding shape. This example says that a visual model
was needed but no reader-visible visual existed. The important differences from the
PASS example are `visual_assessment.verdict=FINDING`,
`observation_status=NOT_OBSERVED`, non-empty diagnosis/repair lists, the aggregate
`result=FINDING`, and matching primary values.

<!-- writing-eval-finding-example -->
```json
{
  "schema_version": "document-experience-reader-eval.v3.1",
  "evaluation_only": true,
  "authority": "ADVISORY_ONLY",
  "suite_id": "COPY_EXACT_CONTEXT_SUITE_ID",
  "case_id": "COPY_EXACT_CONTEXT_CASE_ID",
  "node_id": "writing-eval.review",
  "attempt_id": "COPY_EXACT_DISPATCH_ATTEMPT_ID",
  "instruction_ref": "COPY_EXACT_DISPATCH_INSTRUCTION_REF",
  "instruction_hash": "COPY_EXACT_DISPATCH_INSTRUCTION_HASH",
  "input_refs": ["COPY_EVERY_EXACT_DISPATCH_INPUT_REF"],
  "input_hashes": {"COPY_EXACT_INPUT_PATH": "COPY_EXACT_INPUT_HASH"},
  "preregistration_checkpoint_ref": {
    "path": "COPY_RETURNED_CHECKPOINT_PATH",
    "hash": "COPY_RETURNED_CHECKPOINT_HASH",
    "version": 1
  },
  "candidate_ref": {
    "path": "COPY_EXACT_CONTEXT_CANDIDATE_PATH",
    "hash": "COPY_EXACT_CONTEXT_CANDIDATE_HASH",
    "version": 1
  },
  "profile_ref": {
    "path": "COPY_EXACT_CONTEXT_PROFILE_PATH",
    "hash": "COPY_EXACT_CONTEXT_PROFILE_HASH",
    "version": "0.4.0"
  },
  "guide_ref": {
    "path": "COPY_EXACT_CONTEXT_GUIDE_PATH",
    "hash": "COPY_EXACT_CONTEXT_GUIDE_HASH",
    "version": "0.4.0"
  },
  "reviewer_resource_ref": {
    "path": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_PATH",
    "hash": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_HASH",
    "version": "v3.1"
  },
  "output_contract_ref": {
    "path": "COPY_EXACT_CONTEXT_OUTPUT_CONTRACT_PATH",
    "hash": "COPY_EXACT_CONTEXT_OUTPUT_CONTRACT_HASH",
    "version": "COPY_EXACT_CONTEXT_OUTPUT_CONTRACT_VERSION"
  },
  "author_execution_ref": {
    "kind": "HOST_AGENT_ATTEMPT",
    "id": "COPY_EXACT_CONTEXT_AUTHOR_ID"
  },
  "reviewer_execution_ref": {
    "kind": "HOST_SUBAGENT_ATTEMPT",
    "id": "THIS_DISTINCT_FINDING_REVIEWER_ATTEMPT_ID"
  },
  "reviewer_role": "writing_standard",
  "isolated_input_refs": [
    {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "version": 1},
    {"path": "COPY_PROFILE", "hash": "COPY_HASH", "version": "0.4.0"},
    {"path": "COPY_GUIDE", "hash": "COPY_HASH", "version": "0.4.0"},
    {"path": "COPY_INSTRUCTION", "hash": "COPY_HASH", "version": "v1"},
    {"path": "COPY_REVIEWER_RESOURCE", "hash": "COPY_HASH", "version": "v3.1"},
    {"path": "COPY_OUTPUT_CONTRACT", "hash": "COPY_HASH", "version": "COPY_VERSION"}
  ],
  "reader_readback": {
    "problem_and_outcome": "用自己的话复述问题与结果",
    "primary_relationships": "复述主要关系",
    "mental_model": [
      {"name": "对象一", "role": "它负责什么"},
      {"name": "对象二", "role": "它负责什么"},
      {"name": "对象三", "role": "它负责什么"}
    ],
    "main_path_and_recovery": "复述主路径与恢复路径",
    "decision_conditions_and_risks": "复述决策条件与风险",
    "navigation_map": [
      {"target": "PRODUCT_RULES", "location": "规则所在章节"},
      {"target": "ACCEPTANCE", "location": "验收所在章节"},
      {"target": "RISKS_UNKNOWNS_NEXT", "location": "风险与下一步所在章节"}
    ]
  },
  "reader_outcome_failures": [],
  "verbosity_assessment": {
    "verdict": "PASS",
    "issue_types": [],
    "repair_techniques": [],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "主路径简洁，未观察到表达冗余"
  },
  "checklist_assessment": {
    "verdict": "PASS",
    "issue_types": [],
    "repair_techniques": [],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "未观察到清单功能损失"
  },
  "visual_assessment": {
    "verdict": "FINDING",
    "observation_status": "NOT_OBSERVED",
    "visual_pair_refs": [],
    "issue_types": ["REPRESENTATION_COLLISION"],
    "repair_techniques": ["VISUALIZE"],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "这里存在必须同时比较的关系，但没有读者可见的视觉模型"
  },
  "result": "FINDING",
  "primary_diagnosis": "REPRESENTATION_COLLISION",
  "primary_repair_technique": "VISUALIZE",
  "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN"
}
```

This result is Agent evaluation evidence only; human reader validation remains
`NOT_RUN`.
