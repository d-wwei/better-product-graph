# Problem Learning — Agent Instructions v0.2

Run only through the public Skill and Controller. This version adds a **Prompt-only dependency-aware Pilot inside the existing `problem.learning.loop`**. It changes how the Host thinks and explains the next learning action; it does not add a Graph Node, Artifact type, State schema, dedicated Agent, true fan-out, or cross-submit WAIT / resume mechanism.

## 1. Start light; do not make every request pay the complexity cost

The first step is always a LIGHT short-circuit. Use the existing one-MVU behavior immediately when all are true:

- at most one unresolved item can materially change the current action;
- no unresolved prerequisite or material contradiction must be settled first;
- the best source is available without an external wait.

On this path, do not enumerate a dependency graph, expose a Frontier, or invent extra analysis just to demonstrate the Pilot. Preserve the current MVU and source route.

Use the complex path only when several unknowns, judgments, authorizations, sources, or waits can change one another's value.

## 2. Build only the minimum temporary dependency view

Inside the same unsubmitted Host attempt, consider only items that could change the next product action. A temporary relation may be one of:

- `REQUIRES_EVIDENCE`
- `REQUIRES_JUDGMENT`
- `REQUIRES_AUTHORIZATION`
- `INVALIDATED_BY`
- `SUPERSEDES`
- `INDEPENDENT_OF`

Do not persist this working view or turn it into a second source of truth. If the relations form a cycle, remain unstable for the same exact input, or do not help choose an action, state the conflict briefly and fall back to the existing one-MVU method.

The **Ready Frontier** is the temporary set of items whose prerequisites are satisfied now. Select the one item whose answer is most likely to change the problem frame, product decision, priority, boundary, or next action. The Frontier is internal: never display it as a question wall.

## 3. Route each item to the right source before asking the PM

Choose the source from the nature of the unknown, not from convenience:

- project rules and known context → Project Knowledge;
- prior commitments and reversals → Decision History;
- observed behavior and frequency → Product Data;
- public facts and external patterns → External Research;
- technical, testing, legal, security, or other professional facts → the responsible Professional Owner;
- private organizational context, value trade-off, or product judgment → PM / Decision Owner;
- causal user motivation or an unresolved real-world effect → User Research or an Experiment.

Resolve Agent-researchable facts before interrupting a Junior PM. A PM answer remains a claim or judgment; it is not automatically upgraded to user evidence.

## 4. Keep waiting local and honest

When one source is unavailable, continue only with items that are genuinely independent of it, and do so sequentially inside the same unsubmitted Host attempt. Keep the unavailable item unresolved.

Do not claim real parallel execution, a persisted WAIT, or cross-submit recovery. If an answer requires leaving the current attempt, use the existing Learning route and describe the limitation honestly. `interview resume` below is a user-interaction behavior; it is not evidence that an external WAIT / resume control plane exists.

## 5. Ask one high-value PM question and bring a professional view

When PM-only judgment is material and interaction is allowed, expose only:

1. the Agent's current judgment;
2. why this is the question that matters now;
3. one non-leading core question;
4. only the scaffolding needed to answer it;
5. the Agent's recommended answer or direction;
6. the strongest counterargument;
7. the evidence or condition that would flip the recommendation.

Do not ask the PM to recall facts available in Knowledge, History, Data, or research. Do not send a wall of open questions. Challenge at most once when a material contradiction exists; preserve Agent judgment, PM judgment, authority, evidence, disagreement, review / rollback conditions, and stop reason.

Honor `interview skip` immediately, including mid-interview: stop unanswered and future PM questions, retain the PM-only Unknown, and continue any alternate-source request. On `interview resume`, recompute against the newest exact Evidence and restore only the current highest-value unresolved PM-only Unknown; do not replay the old question list, solved questions, or invalidated questions.

## 6. Recompute once when exact Evidence changes the frame

Within the same Host attempt, exact new Evidence may weaken, invalidate, or supersede a premise and therefore change the selected MVU. When that happens:

- bind the rationale to the new exact source;
- stop presenting the stale question;
- recompute the temporary Frontier at most once.

If there is no new exact Evidence, or the selected MVU remains unchanged, treat this as no progress. Stop recomputing and continue, stop, or degrade through the existing Learning path. Rewording a claim, adding lenses, or obtaining Agent agreement is not new Evidence.

## 7. Stop when the current action is responsible, not when the world is fully known

The Frontier does not need to be empty. `READY_FOR_SYNTHESIS` is allowed when every remaining Unknown is unlikely to change:

- the current action or target user;
- a material or irreversible risk;
- the action's reversibility and rollback boundary;
- how success will be measured;
- the condition that would make the team stop or change direction.

Keep the residual Unknowns visible and explain why they do not block the current action. If an unresolved item could change any boundary above, do not declare sufficiency merely because the document looks complete.

Return exactly one learning disposition: `READY_FOR_SYNTHESIS`, `ROUTE_REEVALUATION_RECOMMENDED`, or `INSUFFICIENT_TO_PROCEED`, separately from runtime status.

Return `reasoning_usage.used_resource_ids` and a short `selection_rationale`. IDs must come from the exact `resource_refs` in this dispatch. Use `next_actions[].reason` and `reasoning_usage.selection_rationale` for the brief visible explanation. This is an Agent-authored record of which references informed the result; it does not authorize the program to choose lenses or infer product meaning.

## 8. Persist only the existing public result contract

The Pilot's dependency view, Frontier, waiting isolation, invalidation, and supersession are temporary reasoning methods. The controlled Host's official output must not add private `dependency`, `WAITING`, `invalidated`, or `superseded` fields. The current Controller does not claim closed-world rejection of arbitrary extra `semantic_output` keys; runtime hard enforcement would require a later versioned Validator / Schema change.

Use the Better Question techniques and cognitive-lens catalog only when they add information gain: one primary lens, and only a few supporting lenses that test different risks. They are internal reasoning aids, not extra Nodes, checklists, facts, or confidence multipliers.

<!-- learning-frontier-pilot-contract -->
```json
{
  "schema_version": "learning-frontier-pilot.v1",
  "phase": "PROMPT_ONLY_PILOT",
  "first_step": "LIGHT_SHORT_CIRCUIT",
  "complex_path": {
    "temporary_relations": [
      "REQUIRES_EVIDENCE",
      "REQUIRES_JUDGMENT",
      "REQUIRES_AUTHORIZATION",
      "INVALIDATED_BY",
      "SUPERSEDES",
      "INDEPENDENT_OF"
    ],
    "source_routes": [
      "PROJECT_KNOWLEDGE",
      "DECISION_HISTORY",
      "PRODUCT_DATA",
      "EXTERNAL_RESEARCH",
      "PROFESSIONAL_OWNER",
      "PM_PRIVATE_CONTEXT_OR_JUDGMENT",
      "USER_RESEARCH_OR_EXPERIMENT"
    ],
    "waiting_scope": "SAME_UNSUBMITTED_HOST_ATTEMPT_ONLY",
    "recomputation_limit_per_attempt": 1,
    "no_progress_rule": "STOP_RECOMPUTING_IF_NO_NEW_EXACT_EVIDENCE_OR_MVU_UNCHANGED",
    "show_internal_frontier_to_pm": false,
    "pm_interaction": {
      "core_question_count": 1,
      "visible_elements": [
        "CURRENT_JUDGMENT",
        "WHY_NOW",
        "ONE_CORE_QUESTION",
        "AGENT_RECOMMENDATION",
        "STRONGEST_COUNTERARGUMENT",
        "FLIP_CONDITION"
      ]
    }
  },
  "stop_rule": "CURRENT_ACTION_SUFFICIENT_NOT_FRONTIER_EMPTY",
  "output_boundary": {
    "allowed_persisted_reason_paths": [
      "next_actions[].reason",
      "reasoning_usage.selection_rationale"
    ],
    "runtime_closed_world_enforcement": "NOT_CLAIMED",
    "forbidden_private_fields": [
      "dependency",
      "WAITING",
      "invalidated",
      "superseded"
    ],
    "official_semantic_output_keys": [
      "learning_disposition",
      "runtime_status",
      "material_challenges",
      "interaction_policy",
      "next_actions",
      "reasoning_usage"
    ]
  },
  "architecture_invariants": {
    "new_top_level_nodes": 0,
    "new_artifact_types": 0,
    "new_state_schemas": 0,
    "new_dedicated_agents": 0,
    "real_cross_submit_wait_resume": false,
    "real_parallel_fanout": false
  },
  "golden_cases": [
    {
      "id": "G1",
      "frozen_input": "ONE_ACTION_CHANGING_UNKNOWN_NO_CONFLICT_NO_WAIT",
      "event_sequence": ["CLASSIFY_LIGHT", "PRESERVE_EXISTING_MVU_ROUTE"],
      "pass_oracle": "NO_DEPENDENCY_ENUMERATION_AND_NO_EXTRA_PM_QUESTION",
      "reject": "NEW_NODE_ARTIFACT_STATE_OR_QUESTION"
    },
    {
      "id": "G2",
      "frozen_input": "USER_PROPOSES_SOLUTION_BEFORE_PROBLEM_FRAME_IS_PROVEN",
      "event_sequence": ["SEPARATE_CLAIM_FROM_PROBLEM", "SELECT_FRAME_CHANGING_MVU"],
      "pass_oracle": "ONE_MVU_WITH_RECOMMENDATION_COUNTERARGUMENT_AND_FLIP",
      "reject": "DOWNSTREAM_SOLUTION_DESIGN_OR_USER_CLAIM_AS_FACT"
    },
    {
      "id": "G3",
      "frozen_input": "HISTORY_DATA_PROFESSIONAL_FACT_AND_PM_CONTEXT_ARE_UNKNOWN",
      "event_sequence": ["READ_HISTORY", "READ_DATA", "ROUTE_PROFESSIONAL_FACT", "SELECT_PM_JUDGMENT"],
      "pass_oracle": "SELF_SERVICE_FACTS_FIRST_AND_ONE_PM_QUESTION",
      "reject": "ASK_ALL_ITEMS_TO_PM_OR_INVENT_PROFESSIONAL_FACT"
    },
    {
      "id": "G4",
      "frozen_input": "PROFESSIONAL_OWNER_UNAVAILABLE_BUT_TWO_SOURCES_ARE_INDEPENDENT",
      "event_sequence": ["KEEP_OWNER_ITEM_UNRESOLVED", "RUN_INDEPENDENT_SOURCE_ONE", "RUN_INDEPENDENT_SOURCE_TWO"],
      "pass_oracle": "SEQUENTIAL_PROGRESS_INSIDE_ONE_UNSUBMITTED_ATTEMPT",
      "reject": "GLOBAL_STOP_FAKE_PARALLEL_OR_PERSISTED_WAIT"
    },
    {
      "id": "G5",
      "frozen_input": "INITIAL_MVU_DEPENDS_ON_A_TARGET_USER_PREMISE",
      "event_sequence": ["INJECT_EXACT_CONTRADICTING_EVIDENCE", "RECOMPUTE_ONCE"],
      "pass_oracle": "STALE_MVU_REMOVED_AND_NEW_MVU_BINDS_EXACT_EVIDENCE",
      "reject": "REPEAT_STALE_QUESTION_OR_RECOMPUTE_MORE_THAN_ONCE"
    },
    {
      "id": "G6",
      "frozen_input": "Q1_IS_PM_ONLY_AND_ALTERNATE_SOURCE_EXISTS",
      "event_sequence": ["INTERVIEW_SKIP", "INJECT_EXACT_EVIDENCE", "INTERVIEW_RESUME"],
      "pass_oracle": "RESTORE_ONLY_Q2_AS_THE_LATEST_HIGHEST_VALUE_UNRESOLVED_QUESTION",
      "reject": "REPLAY_Q1_RESTORE_ALL_OR_TREAT_SKIP_AS_ANSWER",
      "resume_question_count": 1,
      "resume_question": "LATEST_HIGHEST_VALUE_UNRESOLVED",
      "claims_cross_submit_wait_resume": false
    },
    {
      "id": "G7",
      "frozen_input": "PAIRED_REVERSIBLE_ACTION_AND_MATERIAL_RISK_COUNTEREXAMPLE",
      "event_sequence": ["EVALUATE_ACTION_RELATIVE_SUFFICIENCY", "PRESERVE_RESIDUAL_UNKNOWNS"],
      "pass_oracle": "REVERSIBLE_CASE_SYNTHESIZES_AND_MATERIAL_RISK_CASE_DOES_NOT",
      "reject": "FRONTIER_EMPTY_REQUIREMENT_OR_FALSE_READY_FROM_DOCUMENT_COMPLETENESS"
    }
  ]
}
```

Copy the dispatch's exact `resource_refs` to the top-level Node Result. Then return this complete `semantic_output`; replace `better-question` only with IDs that actually appear in those dispatched refs:

material_challenges 可保留零项或多项彼此不同的重大挑战。它不是 PM 问题列表，不能因为一次只问一个问题就删掉其他不同风险；保持简洁并去重即可。

<!-- problem-learning-semantic-output-contract -->
```json
{
  "learning_disposition": "READY_FOR_SYNTHESIS",
  "runtime_status": "COMPLETED",
  "material_challenges": [],
  "interaction_policy": "NO_PM_INTERVIEW",
  "next_actions": [
    {
      "kind": "SYNTHESIZE_PROBLEM",
      "reason": "当前不存在会改变问题框架的高价值未知"
    }
  ],
  "reasoning_usage": {
    "used_resource_ids": ["better-question"],
    "selection_rationale": "用最少的提问框架检查当前未知是否会改变产品判断"
  }
}
```

When the Run allows PM interviewing, set `interaction_policy` to the exact dispatched policy. Under `NO_PM_INTERVIEW`, `next_actions` must never contain `PROMPT_PM`; use research, an external Owner, an explicit Unknown, or a stopped/waiting disposition instead.
