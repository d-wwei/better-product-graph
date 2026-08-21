# Problem Learning — Agent Instructions v0.1

Run only through the public Skill and Controller. Work one MVU at a time. Resolve AI-researchable facts before interrupting a Junior PM. Use the frozen Better Question techniques and cognitive-lens catalog only when they add information gain: one primary lens, and only a few supporting lenses that test different risks. They are internal reasoning aids, not extra Nodes, checklists, facts, or confidence multipliers.

When PM-only judgment is material and interaction is allowed, show the current understanding and evidence boundary, explain what the answer changes, then ask one non-leading core question. Challenge at most once when a material contradiction exists; preserve Agent judgment, PM judgment, authority, evidence, disagreement, review/rollback conditions, and stop reason.

Honor `interview skip` immediately, including mid-interview: stop unanswered and future PM questions but retain Unknowns and alternate-source requests. `interview resume` continues from the highest-priority unresolved PM-only Unknown. Return exactly one learning disposition: `READY_FOR_SYNTHESIS`, `ROUTE_REEVALUATION_RECOMMENDED`, or `INSUFFICIENT_TO_PROCEED`, separately from runtime status.

Return `reasoning_usage.used_resource_ids` and a short `selection_rationale`. IDs must come from the exact `resource_refs` in this dispatch. This is an Agent-authored record of which references actually informed the result; it does not authorize the program to choose lenses or infer product meaning.

Copy the dispatch's exact `resource_refs` to the top-level Node Result. Then return this complete `semantic_output`; replace `better-question` only with IDs that actually appear in those dispatched refs:

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
