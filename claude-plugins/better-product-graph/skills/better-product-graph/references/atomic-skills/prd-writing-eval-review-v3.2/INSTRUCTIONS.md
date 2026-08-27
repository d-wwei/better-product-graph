# PRD Writing Eval Review v3.2 — evaluation-only contract

Use this instruction only when the Controller dispatch says:

- `node_id=writing-eval.review`;
- `validator=document_experience_reader_eval_v3_1`;
- `writing_eval_context.evaluation_only=true`;
- `writing_eval_context.review_schema=document-experience-reader-eval.v3.1`;
- Profile version is `0.5.0` and Reviewer resource version is `v3.2`.

This is an isolated product evaluation, not an ordinary Product Run Review. It is
`ADVISORY_ONLY`, closes only this exact Writing Eval Run, and cannot enter Review
aggregate, Ready, Release, Handoff, or approve any product decision.

## Custody and method

Read only `writing_eval_context.isolated_input_refs`: the exact Candidate, v0.5
Profile, v0.5 Guide, this instruction, the v3.2 eval-only Reviewer Contract, and
the PRD Output Contract. Do not read author reasoning, mutable chat, other reviews,
source code, scoring files, hidden evaluator material, or any undispatched file.
Use a distinct `HOST_SUBAGENT_ATTEMPT`; its ID must differ from the author ID.

First produce the six-field reader readback. Then record only observed reader
outcome failures. Judge clarity and locatability of content that is actually stated;
Product, Engineering Feasibility, and Testability reviewers own substantive
completeness. Length, row count, section count, or a policy trigger alone is never
a Finding. A missing visual is a Finding only when prose or a table cannot
reasonably communicate the key relationship and a minimal visual would materially
reduce reader cost. More than one repair may validly serve the same reader need.

## Closed result rules

Use only these values:

- reader outcomes: `UNDERSTAND | SEE | MODEL | RETELL | DECIDE | LOCATE`;
- assessment verdicts: verbosity/checklist `PASS | FINDING`, visual
  `PASS | FINDING | NOT_NEEDED`;
- visual observation: `OBSERVED | NOT_OBSERVED | NOT_NEEDED`;
- result: `PASS | FINDING`;
- issue types: `SEMANTIC_REPETITION | FLAT_PEER_OVERLOAD |
  REPRESENTATION_COLLISION | DETAIL_IN_MAIN_PATH | DENSE_TABLE |
  JARGON_INTRUSION | CHECKLIST_FUNCTION_LOSS |
  COMPLETION_SEMANTICS_AMBIGUOUS | ARTIFACT_MATURITY_OVERCLAIM`;
- repairs: `REORDER | GROUP | EXPLAIN | EXAMPLE | VISUALIZE | LAYER |
  MERGE | REFERENCE | MOVE | TRIM | RESTORE_FUNCTION | BOUNDARY`.

All objects are closed. Copy every exact authority field and reference from the
dispatch. Each basis reference must bind the exact Candidate path/hash and an
inclusive in-range line span. The mental model has three to five uniquely named
components. The navigation map has exactly one entry for each of `PRODUCT_RULES`,
`ACCEPTANCE`, and `RISKS_UNKNOWNS_NEXT`. Each reader outcome may fail at most once.

`PASS` assessments have empty issue and repair lists. `FINDING` assessments have
at least one issue and one repair. Visual `NOT_NEEDED` uses `NOT_NEEDED` plus no
visual pairs. Visual `PASS` observes and copies every dispatched pair. Visual
`FINDING` copies every dispatched pair and uses `OBSERVED` when a pair exists or
`NOT_OBSERVED` when none exists. Aggregate `PASS` has no failures or Findings and
null primary fields. Aggregate `FINDING` requires an assessment Finding; its two
primary fields copy one issue and one repair from a Finding assessment.

## Complete legal PASS example

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
    "version": "0.5.0"
  },
  "guide_ref": {
    "path": "COPY_EXACT_CONTEXT_GUIDE_PATH",
    "hash": "COPY_EXACT_CONTEXT_GUIDE_HASH",
    "version": "0.5.0"
  },
  "reviewer_resource_ref": {
    "path": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_PATH",
    "hash": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_HASH",
    "version": "v3.2"
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
    {"path": "COPY_PROFILE", "hash": "COPY_HASH", "version": "0.5.0"},
    {"path": "COPY_GUIDE", "hash": "COPY_HASH", "version": "0.5.0"},
    {"path": "COPY_INSTRUCTION", "hash": "COPY_HASH", "version": "v3.2"},
    {"path": "COPY_REVIEWER_RESOURCE", "hash": "COPY_HASH", "version": "v3.2"},
    {"path": "COPY_OUTPUT_CONTRACT", "hash": "COPY_HASH", "version": "COPY_VERSION"}
  ],
  "reader_readback": {
    "problem_and_outcome": "用自己的话复述问题与用户结果",
    "primary_relationships": "复述主要对象、顺序和依赖",
    "mental_model": [
      {"name": "对象一", "role": "承担第一项职责"},
      {"name": "对象二", "role": "承担第二项职责"},
      {"name": "对象三", "role": "承担第三项职责"}
    ],
    "main_path_and_recovery": "复述主路径、异常和恢复路径",
    "decision_conditions_and_risks": "复述决策条件、风险和未知",
    "navigation_map": [
      {"target": "PRODUCT_RULES", "location": "产品规则所在章节"},
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
    "reason": "未观察到影响读者理解或定位的表达冗余"
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
    "verdict": "NOT_NEEDED",
    "observation_status": "NOT_NEEDED",
    "visual_pair_refs": [],
    "issue_types": [],
    "repair_techniques": [],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "当前文字已能低成本表达关键关系"
  },
  "result": "PASS",
  "primary_diagnosis": null,
  "primary_repair_technique": null,
  "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN"
}
```

## Complete legal FINDING example

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
    "version": "0.5.0"
  },
  "guide_ref": {
    "path": "COPY_EXACT_CONTEXT_GUIDE_PATH",
    "hash": "COPY_EXACT_CONTEXT_GUIDE_HASH",
    "version": "0.5.0"
  },
  "reviewer_resource_ref": {
    "path": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_PATH",
    "hash": "COPY_EXACT_CONTEXT_REVIEWER_RESOURCE_HASH",
    "version": "v3.2"
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
    {"path": "COPY_PROFILE", "hash": "COPY_HASH", "version": "0.5.0"},
    {"path": "COPY_GUIDE", "hash": "COPY_HASH", "version": "0.5.0"},
    {"path": "COPY_INSTRUCTION", "hash": "COPY_HASH", "version": "v3.2"},
    {"path": "COPY_REVIEWER_RESOURCE", "hash": "COPY_HASH", "version": "v3.2"},
    {"path": "COPY_OUTPUT_CONTRACT", "hash": "COPY_HASH", "version": "COPY_VERSION"}
  ],
  "reader_readback": {
    "problem_and_outcome": "用自己的话复述问题与用户结果",
    "primary_relationships": "复述主要对象、顺序和依赖",
    "mental_model": [
      {"name": "对象一", "role": "承担第一项职责"},
      {"name": "对象二", "role": "承担第二项职责"},
      {"name": "对象三", "role": "承担第三项职责"}
    ],
    "main_path_and_recovery": "复述主路径、异常和恢复路径",
    "decision_conditions_and_risks": "复述决策条件、风险和未知",
    "navigation_map": [
      {"target": "PRODUCT_RULES", "location": "产品规则所在章节"},
      {"target": "ACCEPTANCE", "location": "验收所在章节"},
      {"target": "RISKS_UNKNOWNS_NEXT", "location": "风险与下一步所在章节"}
    ]
  },
  "reader_outcome_failures": [
    {
      "outcome": "LOCATE",
      "basis_refs": [
        {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
      ],
      "reason": "同级规则过多，读者无法快速定位目标项"
    }
  ],
  "verbosity_assessment": {
    "verdict": "FINDING",
    "issue_types": ["FLAT_PEER_OVERLOAD"],
    "repair_techniques": ["GROUP"],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "同级条目缺少分组，扫描和定位成本过高"
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
    "verdict": "NOT_NEEDED",
    "observation_status": "NOT_NEEDED",
    "visual_pair_refs": [],
    "issue_types": [],
    "repair_techniques": [],
    "basis_refs": [
      {"path": "COPY_CANDIDATE", "hash": "COPY_HASH", "start_line": 1, "end_line": 3}
    ],
    "reason": "分组即可降低成本，不需要新增视觉模型"
  },
  "result": "FINDING",
  "primary_diagnosis": "FLAT_PEER_OVERLOAD",
  "primary_repair_technique": "GROUP",
  "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN"
}
```

Human-reader observation remains `NOT_RUN`; this output is Agent evaluation
evidence only.
