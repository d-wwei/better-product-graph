# Assumption Audit — Agent Instructions v0.1

Run only through the public Skill and Controller. Separate phenomenon, impact, problem hypothesis, desired outcome, and proposed solution. Test credible alternative explanations and the no-action counterfactual. Do not accept a preselected feature as the problem definition.

Choose exactly one current Most Valuable Unknown (MVU), explain why it has the highest decision impact now, list possible answers and how each changes the next action, and bind its best available source. This semantic selection is the Host Agent's responsibility; the program only validates cardinality and refs. Do not prompt the PM from this module.

Return this complete `semantic_output`. Exactly one MVU must have `selected: true`, and that item must bind a non-empty `best_source_ref`:

<!-- problem-assumption-audit-semantic-output-contract -->
```json
{
  "phenomenon": "用户在失败后无法判断交易是否完成",
  "impact": "用户可能重复操作或放弃任务",
  "problem_hypothesis": "结果状态和下一步行动缺少可信解释",
  "desired_outcome": "用户能判断当前状态并安全采取下一步",
  "proposed_solution": "原始 Signal 提出了增加失败解释",
  "no_action_counterfactual": "如果不处理，重复操作和支持咨询可能继续发生",
  "credible_alternatives": [
    "问题可能来自状态更新延迟，而不是解释文案不足"
  ],
  "mvus": [
    {
      "question": "用户最需要判断的是最终状态还是安全的下一步行动？",
      "decision_impact": "答案会改变问题边界和优先方案",
      "possible_answers": ["最终状态", "下一步行动", "两者都需要"],
      "best_source_ref": "COPY_EXACT_BEST_AVAILABLE_SOURCE_REF",
      "selected": true
    }
  ]
}
```
