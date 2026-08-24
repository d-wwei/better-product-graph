# PRD Review — Agent Instructions v0.2

Run as an isolated read-only attempt over one exact frozen PRD Candidate, its conditional Eval Pack, and the same Goal Fidelity Review inputs. First-round Reviewers cannot see one another's findings. Logical coverage must include Product Goal/Scope Fidelity, Engineering Feasibility, and Testability; a LIGHT run may merge roles in one isolated attempt but cannot omit a role.

Return construction-ready advisory Findings with role/profile, concern, concern level, exact basis and upstream commitment refs, affected scope, possible impact, professional recommendation, repair target, confidence basis, and stance. Preserve disagreement; do not vote, increase evidence confidence because several Agents agree, edit the Candidate, write state, approve, block, waive, or impersonate Security/Privacy/Compliance authority.

Bind `goal_fidelity_refs.profile_ref`, `rubric_ref`, and `packet_contract_ref` to the exact matching dispatch resources. Bind a non-empty `commitment_refs` list and the exact Candidate in both the review payload and Goal Fidelity packet; every Candidate and commitment must be one of the dispatch inputs. An Agent cannot confirm a provisional commitment or substitute a similarly named profile.

Do not add a new confirmation or consent checkpoint when exact commitments already authorize an automatic operation and no exact higher-order policy in the bound inputs requires another checkpoint. Separate authorization for the operation from undisclosed extra side effects: review the Candidate for hidden file changes, unsafe failure leftovers, or scope drift, but do not convert an already authorized automatic action into a new mandatory human approval.

## READABILITY_AND_PRODUCT_BOUNDARY

把人类阅读体验和产品边界作为正式审查面，但 Reviewer 仍然只有 `ADVISORY_ONLY` 建议权。先读取 dispatch 绑定的 Document Experience Profile 与 Writing Guide，再判断 Candidate 是否做到：先建立全局框架，再逐层展开；让标题、摘要、正文和验收口径使用一致的语言；控制单段信息密度；只在确实能降低理解成本时使用图表；让第一次接触项目的产品经理能够看懂目标、范围、关键流程、取舍、未知和下一步。

PRD 应说明产品问题、用户结果、范围、业务规则、边界条件和可观察验收。对象拆分、内部 Schema、存储布局、线程模型、类与函数设计等通常属于下游 Engineering SPEC，不应为了显得完整而塞进 PRD；只有当某项技术约束会改变外部行为、安全、隐私、兼容性、性能承诺或产品取舍时，才把它提升为产品要求。发现问题时，使用正常 Finding 合同给出 exact basis、影响和建议，不得新增 Gate、阻塞权或强制确认点。

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

The `semantic_output` must equal the complete aggregate artifact plus the same `dispositions` array. The two `artifact_refs` must each contain exact `role`, `path`, `hash`, and `version`; paths may not leave the project and neither file may be a symlink. Do not submit until the Candidate path/hash/version, Reviewer attempt, Reviewer logical roles, Finding IDs, disposition coverage, JSON files, and hashes all agree. Missing or stale facts are a repair condition, not permission to continue to `review.finalize`.

`disagreements` is always present and is a JSON list. Use `[]` when no material disagreement exists. Every non-empty item must include a non-empty `topic_id` and a unique non-empty `finding_ids` (or generated `findings`) list that refers only to Findings preserved in this aggregate; if `stances` is present, it must cover those Finding refs one-for-one.

Collection cardinality is exact: `attempts` must contain at least one completed Reviewer attempt and every attempt must retain a non-empty `roles_covered`; `findings` must be present and may be `[]`; `dispositions` must be present and must be `[]` exactly when `findings` is `[]`, otherwise it must close every Finding ID exactly once; `disagreements` must be present and may be `[]`, while every non-empty reference must name an existing Finding. Missing, `null`, wrong-type, empty-when-required, duplicate, or unmatched collections are repair conditions.

This is a closed-world `review.aggregate` contract. Do not add extension or future-authority fields. The exact allowed keys are:

- `semantic_output`: `schema_version`, `authority`, `candidate_ref`, `attempts`, `findings`, `disagreements`, `dispositions`.
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
    ]
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
    "disagreements": []
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
    "dispositions": []
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
    "disagreements": []
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

Metadata must preserve upstream authority and the closed active-scope/trace/runtime contracts, declare exact `supersedes`, and include a `change_log` with the source Candidate, every repaired Finding ID, all unadopted dispositions unchanged, material delta, and re-review scope. Extend `spec_traceability` with the exact `source_candidate` and the committed `review_aggregate_result` from `optimize_context`; a Product Planning reconciliation carries those same two roles into its later `prd.generate`. A legal Evals specification update may be submitted, but in the current skills-only Host REQUIRED Evals must remain `REVIEW_PENDING`/`NOT_RUN` without active stale Pack/review refs; typed Pack/review consistency cannot prove independent fulfillment or grant release authority. Python validates and archives these Agent-authored bytes; it never generates the revision.

Stop at the bounded round/no-progress limit, record unadopted or external-review dispositions, render the same-version companion view, and let deterministic `review.finalize` check completeness before the single `prd.ready.gate`.
