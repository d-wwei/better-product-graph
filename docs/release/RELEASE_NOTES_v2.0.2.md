# Better Product Graph 2.0.2 — Agent-first Quality, Review, and Delivery-cost Repairs

`2.0.2` is the patch release for seven accepted BPG 2.0 GitHub Issues. It keeps the single-PRD Developer Alpha architecture and strengthens Agent execution without adding another governance system.

## Issue #1 — Candidate author preflight

Before freezing a Problem, Decision, or PRD Candidate, the author performs a bounded semantic self-check using the existing Planning Record or Document Experience diagnoses/actions. It checks material ambiguity while product meaning is still editable. The result is explicitly `AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL`; independent Review remains required, and no new checklist artifact, schema, state, Gate, or Owner round is added.

## Issue #2 — Bounded long-run context

The Host reuses `planning_context.context_summary` and the continuously maintained Planning Record as the compact stage fact summary. It carries only the current summary, current Candidate, immediate revision basis when needed, unresolved Findings, and current-stage contracts, resolving details from canonical exact refs on demand. It does not introduce an Evidence Digest artifact, hash budget, Controller Gate, or unsupported Token-cost claim.

## Issue #3 — Exact revised-Candidate Review work order

Revised Candidates receive a Controller-projected `current_rereview_work_order` binding the source and current Candidate refs, prior Review and Finding refs when available, the Planning Record repair basis, focused scope, and a bounded whole-product regression checklist. The independent Reviewer derives the semantic difference from those exact refs; BPG does not create a separate diff artifact or programmatic meaning classifier.

## Issue #4 — Fewer redundant Controller round trips

Successful state-changing operations already return the complete new state and next-work material. The Host now consumes that response directly and uses `status` only for recovery, re-entry after context loss, or explicit diagnostics. This does not create a compound Controller API or merge durable events, semantic steps, independent Review, Owner decisions, or external side effects.

## Issue #5 — Minimal Local Handoff by default

Local Handoff now defaults to the exact Markdown source only. `LOCAL_HTML` and `LOCAL_RENDERED_VISUALS` default to `false`; HTML and rendered Mermaid SVGs are produced only when explicitly requested after Ready. Mermaid source remains in the Markdown truth source, and Retrospective is optional rather than an automatic post-Handoff requirement.

## Issue #6 — Reviewer return-boundary repair

Every formal Reviewer still starts with no inherited parent conversation (`fork_turns="none"`) and reads only the exact dispatched immutable basis. Before returning, the Reviewer compares its result with the exact output contract and may perform at most one same-attempt structure-only correction while preserving every Finding, Verdict, basis, coverage judgment, and evidence meaning. A correction requiring semantic reconsideration returns `REVIEW_RESULT_STRUCTURE_INVALID — HOST_REDISPATCH_REQUIRED` for a fresh independent dispatch.

## Issue #7 — Benefits remain to be measured

The implementation removes redundant status calls, avoids repeatedly carrying accumulated history, and makes optional output work opt-in. The development source passed `894/894` tests. Those checks do not prove lower elapsed time, smaller context, lower Token cost, or better PRD quality. A comparable real Product Golden Run measuring those outcomes remains `NOT_RUN`, so no efficiency or quality gain is claimed from this release.

## Agent/program boundary

Agents continue to own semantic analysis, author preflight, context selection, Candidate comparison, Review Findings, severity, and product judgment. Deterministic code remains limited to exact identities and refs, legal state transitions, versioned work orders, persistence, recovery, and explicitly requested delivery materialization.

## Verification and release boundary

- Current source verification: `894/894 PASS`.
- Product Evals execution and product-effect validation: `NOT_RUN` unless separately observed.
- Comparable Issue #7 Product Golden Run: `NOT_RUN`.
- Human-reader study, external delivery, engineering receipt, and implementation tests: `NOT_RUN` unless separately evidenced.
- The formal release must bind one clean development commit, one filtered public snapshot commit, the annotated `v2.0.2` Tag, the exact Codex and Claude Marketplace ZIPs, `SHA256SUMS`, remote readback, and downloaded-asset verification.
