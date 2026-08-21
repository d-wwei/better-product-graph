# Product Decision — Agent Instructions v0.2

Run only through the public Skill and Controller after programmatic Problem Ready. The Host Agent makes one advisory product recommendation; the Controller validates and persists it but never invents a recommendation. Only the authorized Product Decision Owner can choose the formal outcome.

## Human interaction

Lead with one clear Chinese recommendation, two or three key reasons, the largest current Unknown, the condition that would change the recommendation, and one concrete next action. Do not ask the Owner to interpret internal enums. In every user-facing brief and question, **不要向用户裸露** `COMMIT / NOW` or another bare machine code. Render the choices as complete sentences:

- `STOP`：现在不做，结束当前方向。
- `WAIT`：值得继续关注，但暂时不作承诺。
- `RESEARCH`：先补充关键信息，再决定是否投入。
- `EXPERIMENT`：先做小范围实验，用真实结果验证。
- `COMMIT` + now：现在进入产品规划。
- `COMMIT` + future：记录进 Roadmap，在约定时间或条件满足后启动。

The Owner may answer in ordinary language. Translate that answer into the exact Owner command only after the Agent proposal has been accepted. Do not put `owner_choice`, `owner_authorized`, or `commit_timing` in the Agent draft. If the Owner disagrees, make at most one substantive challenge and then preserve both positions without endless debate.

## Exact Agent submission contract

Submit the following object as `semantic_output`. Keep every key and value type shown below. Replace the example content with conclusions derived from the exact bound inputs; do not copy its product claim as fact.

<!-- PRODUCT_DECISION_SEMANTIC_OUTPUT_START -->
```json
{
  "recommendation": "COMMIT",
  "reasons": [
    "核心用户问题和目标结果已经明确",
    "剩余未知主要影响实现方式，不改变是否投入的判断"
  ],
  "mvu": "小范围上线后，目标用户能否稳定完成关键任务",
  "nearest_alternative": "EXPERIMENT",
  "flip_condition": "如果关键行为只能通过真实暴露验证，改为先做小范围实验",
  "next_action": "向 Owner 展示建议和风险边界，并等待其用自然语言作出选择",
  "epistemic_confidence": "MEDIUM",
  "action_risk": {
    "level": "R1",
    "basis": "建议先做有限范围、可观测且可回滚的产品增量",
    "reversible": true,
    "measurable": true,
    "rollback": "停止新增暴露并恢复上一版本的产品规则"
  },
  "non_waivable_policy_violations": [],
  "outcome_details": {
    "COMMIT": {
      "target": "进入产品规划，形成整体方案和分阶段 PRD"
    }
  }
}
```
<!-- PRODUCT_DECISION_SEMANTIC_OUTPUT_END -->

Contract rules:

- `recommendation` must be exactly one of `STOP`, `WAIT`, `RESEARCH`, `EXPERIMENT`, or `COMMIT`.
- `reasons` contains exactly two or three non-empty reasons. `mvu`, `nearest_alternative`, `flip_condition`, `next_action`, and `epistemic_confidence` are required.
- `action_risk` is the Agent's product-risk assessment. `level` is `R0`, `R1`, `R2`, or `R3`; always explain the basis and state whether the action is reversible and measurable plus the rollback/stop response. The Controller may enforce a higher minimum risk level but cannot lower it for the Owner.
- `non_waivable_policy_violations` lists only known hard violations supported by the exact bound inputs. `[]` **只表示在当前绑定材料中没有发现已知硬性违规**；它**不等于已经完成独立合规审计**，也 cannot turn an unavailable policy review into PASS. Any known item keeps the draft not ready and must be surfaced plainly.
- `outcome_details` must contain exactly one key, and that key must equal `recommendation`. It describes what happens if the Owner adopts this recommendation; it does not authorize the route. Do not add empty structures for unchosen outcomes.

After the Agent draft is accepted, the authorized Owner chooses one outcome. The program maps that exact choice deterministically: STOP→closed, WAIT→waiting trigger, RESEARCH→waiting evidence, EXPERIMENT→Plan Run with experiment intent, COMMIT now→Plan Run, COMMIT future→Roadmap only. The program never recommends or chooses an outcome, and the Agent must never describe a local proposal as approved.

## Exact Owner Choice command

After public submit returns `OWNER_CHOICE_REQUIRED`, show the Owner the plain-language options above. Only after the Owner answers, construct this separate command for `--operation owner-choice`. Copy `decision_id`, the entire `proposal_ref`, its hash, and `state.state_version` from that exact response. The Owner identity must be real; never reuse the Host Agent identity or infer consent from the recommendation.

<!-- OWNER_CHOICE_COMMAND_START -->
```json
{
  "schema_version": "owner-choice-command.v1",
  "decision_id": "COPY_EXACT_DECISION_ID",
  "proposal_ref": {
    "path": "COPY_EXACT_PROPOSAL_PATH",
    "hash": "COPY_EXACT_PROPOSAL_HASH",
    "version": "COPY_EXACT_PROPOSAL_VERSION"
  },
  "proposal_hash": "COPY_EXACT_PROPOSAL_HASH",
  "actor": {
    "kind": "OWNER",
    "id": "COPY_AUTHORIZED_OWNER_ID"
  },
  "expected_state_version": 1,
  "choice": "COMMIT",
  "commit_timing": "NOW",
  "outcome_details": {
    "COMMIT": {
      "target": "现在进入产品规划"
    }
  }
}
```
<!-- OWNER_CHOICE_COMMAND_END -->

For `STOP`, `WAIT`, `RESEARCH`, or `EXPERIMENT`, set `commit_timing` to `null`; for `COMMIT`, it must be `NOW` or `FUTURE`. `outcome_details` must contain exactly the chosen outcome. This command is not part of the Agent `semantic_output`.
