---
name: better-product-graph
description: Use when handling product ideas, user feedback, online issues, product discovery, product decisions, outcome-first planning, versioned PRDs, configuring a Better Product Graph Template Pack, or resuming/auditing a Better Product Graph run. The BPG 2.0 single-PRD runtime is the default; the legacy 0.x public route is removed. Do not use for simple PRD copy-editing, generic project management, or requests to bypass the governed workflow and invoke an internal action directly.
---

# Better Product Graph

Better Product Graph turns a raw product Signal into a responsible next action. A valid result can be STOP, WAIT, RESEARCH, EXPERIMENT, COMMIT NOW, or FUTURE ROADMAP; never force every Signal into a PRD.

## Runtime boundary

- You, the Host Agent, perform semantic product work: research, Evidence interpretation, guided interview, challenge, recommendation, Planning, PRD writing, and advisory Review.
- Deterministic scripts perform only exact identity, state, Candidate, Review, Ready, Local Handoff, version, persistence, recovery, and submitted decision-source consistency checks.
- Never ask Python to infer the problem, choose a product outcome, generate a Plan/PRD, judge quality, or invent a Reviewer Finding.
- Only the Controller may update formal state or promote an artifact. Agent recommendations and Reviewer concerns are proposals, not Gate results.

## Default public entry

Every ordinary `/better-product-graph:better-product-graph <product task>` invocation and equivalent natural-language request uses the BPG 2.0 single-PRD runtime. The user does not need to type `alpha`, `new`, or any internal action name.

The legacy 0.x public route is removed. Never send an ordinary request to `HostRuntime.handle_entry`, the legacy stable-intent parser, or the legacy entry/dispatch/submit control plane. Never import, migrate, alias, or resume a pre-2.0 Run. If an old Run is mentioned, explain that it is historical and start a fresh BPG 2.0 Run only after the user asks to proceed.

The older `/better-product-graph:better-product-graph alpha ...` spelling is accepted only as a temporary, non-required alias for the same default runtime. It must never select a distinct path or restore the 0.x route.

Map the user's goal to one BPG 2.0 action without exposing the action name unless debugging:

| User goal | Controller action | Boundary |
|---|---|---|
| Start a product task | `start` | Create one fresh `.better-product-graph/v2/` Run. |
| Check a Run | `status` | Read-only exact state. |
| Continue a Run | `resume` | Resume only the exact BPG 2.0 Run and valid safe point. |
| Pause a Run | `pause` | Persist one safe pause boundary. |
| Route non-PASS Findings | `review-route` | Lead Agent decision after Reviewer Findings; never a Reviewer command. |
| Prepare local delivery | `handoff` | Local Handoff only; never external delivery. |
| Record the planning retrospective | `retrospective` | Optional non-blocking post-Handoff record when explicitly required. |

If a request has no actionable product task and no exact Run to inspect, ask only for the smallest missing information and do not mutate state. Reject `$bpg`, `$prd-graph`, `review.gate`, legacy aliases, and internal action IDs as public entry points.

## Default BPG 2.0 single-PRD runtime

Before the first mutation, run installed self-check and read the complete installed `references/alpha/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.4.md`. That document owns product semantics; the BPG 2.0 Controller owns only exact identity, state, Candidate, Review, Ready, Local Handoff, and submitted decision-source consistency bindings.

The runtime always creates or resumes state under `.better-product-graph/v2/`. Drive the installed runner with one temporary JSON object per operation:

```text
python3 ${CLAUDE_PLUGIN_ROOT}/skills/better-product-graph/scripts/bpg_runner.py \
  --operation alpha \
  --payload-file <absolute-json-payload>
```

`--operation alpha` is an internal installed-runner identifier, not user syntax and not an opt-in product route.

The payload's `action` is one of `start`, `status`, `replace-record`, `freeze-candidate`, `review`, `review-route`, `decision-route`, `pause`, `resume`, `handoff`, or `retrospective`. Copy the exact `run_id`, `state_version`, Candidate ref, and operation basis returned by the immediately preceding Controller response. Use a fresh, stable `operation_id` for each intended state change; exact replay is idempotent, while reusing an ID with different content is forbidden.

## Consume Returned State Directly

Every successful alpha state-changing operation returns the complete new state. The Host must directly consume the just-returned state and next-work material instead of rediscovering them: PRD freeze returns the exact `current_review_requirements`, and a PASS Review already advances Ready and the next position. Do not immediately call `status` after a successful operation. Use `status` only for recovery, re-entry after context loss, or explicit diagnostics.

Do not add a compound Controller API or merge durable events, semantic steps, or external side effects to reduce calls. Preserve the existing operation, receipt, idempotency and recovery boundaries. At the first next step that needs new Agent work, an independent Reviewer, an Owner decision, or an external side effect, stop automatic serial execution and handle that step explicitly through its existing boundary.

Follow the five semantic stages in the installed BPG 2.0 reference. Keep one continuously updated `planning-record.md`; freeze it as `PROBLEM`, then `DECISION`, and finally freeze exactly one `PRD` Release Set from the current Run's `work/prd/` directory. The Host Agent writes and revises product meaning. The Controller must not decide problem quality, value, risk, reversibility, return stage, Reviewer applicability, or PRD quality. BPG 2.0 does not run Product Evals applicability, Pack generation, or Eval Spec Review; those enter the versioned method and runtime in 2.2.

## Long-Run Context Discipline

Reuse the existing `planning_context.context_summary` and the continuously maintained `planning-record.md` as the compact, traceable stage fact summary for the current Run. The former seeds confirmed project background; the latter carries forward accepted product facts, reasoning, uncertainty, decisions and durable Finding dispositions. Neither replaces canonical sources, frozen Candidates, Reviews, or exact Controller refs.

For each subsequent semantic stage, carry forward only the current planning summary, the current Candidate, when one exists, the exact change from its immediate predecessor when revision context is needed, unresolved Findings, and the rules and contract refs required by the current stage. Do not repeatedly carry the complete chat history, every old Candidate, closed Findings, full source excerpts, search logs, or rules unrelated to the present work. Resolve a detail from its canonical exact refs when it becomes material instead of depending on remembered chat or repasting the source body.

If the useful material no longer fits reasonable context, the Agent must say what it trimmed and why, preserve conclusions, uncertainty, disagreements and unresolved risk in the current summary or Planning Record, and return to canonical exact refs for detail. Never silently drop a material fact. This is an Agent-owned context practice: do not create an Evidence Digest schema or artifact, a hash budget, a Controller Gate, or another state/action to enforce it.

Report input, cached-input, output, or reasoning usage only when the Host or platform actually exposes those values. Label unavailable measurements honestly, keep observed totals distinct from inference, and do not translate cached tokens directly into billed cost. Do not claim a token reduction until a comparable run has actually measured it.

`replace-record` is always a complete replacement, never an append. Copy the current `planning_record_ref.hash` into `base_hash`, set `mode=REPLACE_FULL`, and submit the complete new Markdown. The Controller rejects stale hashes and accidental removal of existing H2 sections before it writes any bytes. A deliberate section removal requires one exact upstream return basis; protected Signal/boundary content cannot be removed. Mechanical rejection creates no Candidate and consumes no semantic revision round. When advancing from `PLAN_PRODUCT_SYSTEM` to `PRD_AUTHORING`, include the exact nine Stage 4 dispositions returned by the method contract. Each is `COMPLETE`, `NOT_APPLICABLE` with a concrete rationale, or `BLOCKED` with missing input, owner and recovery. Any `BLOCKED` item prevents advancement. Do not rewrite `planning-record.md` merely to mirror the current Candidate, Review status, or next action; those volatile facts come from the Controller status projection. If product meaning changes in `PRD_AUTHORING`, the Lead Agent must reassess the nine dispositions. In `PRD_AUTHORING`, submit the complete nine Stage 4 dispositions again with the complete current Planning Record to bind them to its exact ref. Never use this reconfirmation to hide a change that requires the existing return to Decision, Problem, or another earlier affected stage.

Before every Problem, Decision, or PRD freeze, run the bounded Agent semantic author preflight defined by that stage's installed instruction. Reuse the mutable Planning Record or the PRD's existing `document_experience.diagnoses` and `document_experience.actions`; do not create a new checklist artifact, schema, state, action, Gate, or Owner round. Repair a material ambiguity before freeze, and label the result `AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL`. This self-check never replaces the independent Reviewer. Product meaning remains an Agent judgment: do not turn solution leakage, evidence boundaries, alternatives, trade-offs, Unknown behavior, acceptance truth, or status drift into keyword, image, or hash inference.

Each Problem and Decision Review must run in a genuinely independent `HOST_SUBAGENT_ATTEMPT` over the frozen Candidate. The Reviewer submits only concrete Findings and a Verdict; it never supplies `return_target`. For every non-PASS Review, the lead Host Agent separately submits `review-route` with the exact Review and Finding refs, earliest affected stage, reason and scope. A revision uses a new Candidate, has at most two automatic rounds, and requires both difference review and whole-product regression. After a passing Decision Review, only the Owner may choose `STOP`, `WAIT`, `RESEARCH`, `EXPERIMENT`, or `FUTURE_ROADMAP`. The Host Agent uses the current conversation semantics to decide whether the Owner chose a route or whether the narrow Agent `COMMIT_NOW` authorization applies; if the meaning or scope is ambiguous, ask the Owner. Agent `COMMIT_NOW` is limited to low-risk, reversible local product planning and never extends to implementation, publication, external operations, or other real side effects. Keep the exact current Run, Decision Candidate, submitted outcome, declared scope and issued time consistent. `source_message_ref` is optional; if the Host supplies it, persist it as opaque traceability metadata. The Controller does not validate its shape, verify message authenticity, or independently prove semantic authorization. Do not add message-digest checks, authorization receipts, cryptography, schemas, gates, actions or states for this judgment.

Every formal semantic Reviewer dispatch—Problem Review, Decision Review, PRD content Reviewer, Writing Reviewer, and Internal Writing Reviewer evaluation—must start without inherited parent conversation. On Codex, use `spawn_agent(..., fork_turns="none")`; never `fork_turns="all"` or a positive integer. A Host without that parameter must start a clean subagent/session with no inherited parent conversation. This rule is specific to formal Reviewers and does not constrain implementation, research, or ordinary collaboration subagents. The initial task message contains only the exact frozen Candidate/ref, installed Reviewer instruction and Review contract, Controller-dispatched required read-only basis refs, and the output contract and target. The Reviewer reads those exact refs itself. Do not pass author hidden reasoning, a mutable chat summary, other first-pass Reviewer Findings, or undispatched workspace material. For a revised Candidate, dispatch the returned `current_rereview_work_order`; it contains the exact source/current Candidate refs, prior Review and Finding refs when available, Planning Record repair basis, focused scope, and the bounded whole-product regression checklist. The Reviewer derives the semantic difference from those exact Candidate refs. Do not create a separate diff artifact or programmatic change classifier.

Before returning, every formal Problem, Decision, PRD content, or Writing Reviewer compares its final result with the exact dispatched output contract. If the intended legal representation is unambiguous, it may make at most one same-attempt structure-only correction while preserving every Finding, Verdict, basis, coverage judgment, and evidence meaning. If a legal result would require semantic reconsideration, return `REVIEW_RESULT_STRUCTURE_INVALID — HOST_REDISPATCH_REQUIRED`; the Host re-dispatches an independent Reviewer and must not normalize or ghostwrite Reviewer semantics. This is a read-only Agent self-check, not a new program validator, raw/corrected hash record, Controller action, state, receipt, or Gate.

`fork_turns="none"` isolates inherited conversation only; Reviewer subagents still share the workspace and it does not prove filesystem or cryptographic isolation. `HOST_SUBAGENT_ATTEMPT` proves only that the Host recorded a distinct attempt, not that the Host call or independence was machine-verified. Do not add a Runtime check, schema, state, action, Gate, or fork receipt for this Host behavior.

Never rewrite a historical Review or its `OPEN` Finding; that historical Review remains immutable evidence of what the Reviewer found at the time. When revising the existing `planning-record.md`, the Lead Agent records one durable mapping for every routed Finding: its source Review ref, Finding ID, outcome, reason and evidence, plus the affected current planning content or new Candidate. The outcome is exactly `FIXED`, `DISPROVED`, `DOWNGRADED`, `ACCEPTED_LIMITATION`, `NEEDS_OWNER`, or `INVALIDATED_BY_UPSTREAM_CHANGE`. A new independent Reviewer must verify each disposition and any claimed actual repair against the new Candidate with both difference review and whole-product regression. Put any remaining material product limitation that affects engineering understanding, acceptance, or risk ownership into the final PRD; do not put the ordinary review process there. This Agent-owned semantic history must not become a Controller schema, state, action, or Ready gate.

The new Reviewer reads both exact Candidate refs, the prior Findings and the Planning Record repair basis from `current_rereview_work_order`, performs its own semantic comparison, focuses review on affected content, then applies the supplied short whole-product regression checklist and records one new Review for the exact current Candidate. When no Review route exists, the work order broadens scope to the full Candidate rather than guessing a narrow change. Never inherit the old Review. Whole-Candidate content hashes only bind Review evidence to the bytes reviewed; they never decide whether meaning changed. Do not add a separate diff artifact, component hash, responsibility hash, Review receipt inheritance or a programmatic diff classifier.

Before freezing a Decision Candidate, perform one semantic Solution Intelligence self-check. Platform or environment facts establish feasibility or constraints; they do not by themselves constitute Solution Intelligence, and Agent-generated alternatives are not external or adjacent-practice evidence. Explain which truly relevant direct products, industry or adjacent practices, failure cases or anti-patterns informed the proposed mechanism and what transfers, or record a concrete `NOT_APPLICABLE` rationale. Scale depth to risk, novelty, reuse, and maintenance cost. The independent Decision Reviewer applies the same semantic question: for a high-reuse, high-maintenance, or novel system, platform facts plus self-generated options without practice evidence or a concrete rationale require one normal advisory Finding. The Planning Record keeps only conclusions and key evidence, not a search log. Do not require a fixed source count, force online research, or add a schema, checklist, or Gate.

Candidate storage is content-addressed inside the Run. The Controller stores identical bytes once and returns object refs; never create or copy a separate Work, Candidate and Handoff tree by hand. Handoff alone materializes the finalized delivery files once.

Before freezing a PRD, the author must submit the closed `bpg2-alpha-document-experience.v1` self-check over the exact draft. It records the current Writing Profile and Guide identity, diagnoses, actions, zero-context reading path and the reason a single PRD remains appropriate. It is author evidence, never independent approval.

Before freeze, run a semantic `STATUS_DRIFT_TEST` over the exact draft and record it in the existing `document_experience.diagnoses` and `document_experience.actions`; do not add a field or another status document. The PRD keeps only the durable product contract and durable product Unknowns. `planning-record.md` keeps product reasoning, decisions, and durable Finding disposition history. Controller state and exact receipts are the sole live authority for current Candidate, Review, Ready, Handoff, Product Evals, and engineering status. If advancing only the Product Run would make a sentence stale while product requirements stay unchanged, remove it from the PRD or move its durable meaning to the Planning Record. Never implement this as a keyword scan: durable product rules may use the same terms without becoming live status.

The PRD freeze response contains `current_review_requirements`. Use it as the only PRD Review work order. It binds the exact Markdown PRD, Planning snapshot, accepted Decision and Review, Template, Output Contract/checklist, Writing Profile, Writing Guide, and Writing Review Contract. For a revised PRD it also projects the exact `rereview_work_order` returned for the current Candidate. BPG 2.0 supplies no Product Eval Pack or Eval Spec Review input. Do not reconstruct, rename or substitute those refs. Candidate and Review contain no rendered delivery format.

PRD Review remains one existing Review node and one final Verdict, but requires two distinct read-only Host attempts. A content Reviewer covers the applicable product, experience, system, engineering and acceptance responsibilities. A separate `HOST_SUBAGENT_ATTEMPT` runs the installed `document-experience-reader-review.v3` Writing Review over exactly the five isolated refs in `writing_review_context`. The author, content Reviewer and Writing Reviewer IDs must differ. Do not use `writing-eval` as Product Run evidence.

Record all six `responsibility_ids` separately as `PASS`, `FINDING`, or `NOT_APPLICABLE` with rationale, exact basis refs and linked Finding IDs. The Writing Reviewer owns `DOCUMENT_EXPERIENCE`; empty Findings never substitute for coverage. It reviews content structure, readability, navigation logic and visual-source use in the exact Markdown Candidate. Any Candidate, Profile, Guide, contract or basis change makes prior Review evidence stale. Do not generate, open or review HTML during Candidate Review.

Use Mermaid source only for Candidate visuals. The BPG 2.0 Candidate source file set is exactly `PRD.md`; reject any additional source file or asset as a deterministic file-set boundary, without inspecting picture content or meaning. The Author and Reviewers judge the product meaning, relationships, labels and readability expressed by the Mermaid block in the exact Markdown Candidate. Do not generate, attach, open or review SVG preview, PNG or HTML before Ready, and do not run SVG path/style/class/safety preflight in Candidate or Ready. At Handoff, keep the already Ready Mermaid source in `PRD.md`. SVG files are generated only when `LOCAL_RENDERED_VISUALS` is explicitly enabled; that selection must fail explicitly if the Host lacks a working Mermaid renderer. HTML is an independent option and may preserve the Mermaid source when rendered visuals are not selected. Generated delivery views prove only that output was generated; they do not re-judge product semantics or become Candidate/Review evidence. Do not add a second SVG validator.

For PRD delivery, BPG 2.0 does not run Product Evals applicability, Pack generation, or Eval Spec Review and none of them may block Ready or Local Handoff. Do not author or attach a simulated Eval Pack. Ready means only that the exact Markdown PRD and its required content and writing Reviews are final for local handoff; it does not mean that the product was tested or validated. Product Eval execution and product-effect validation remain exactly `NOT_RUN` unless separately observed outside this Product Run. The 2.2 versioned method and runtime will introduce applicability, Pack, independent specification Review, freshness, and the corresponding Ready Gate when that capability actually exists.

Translate the user's natural-language Handoff preference into the optional `delivery_options` object. Each delivery mode owns an independent boolean switch. `LOCAL_HTML` defaults to `false`; `LOCAL_RENDERED_VISUALS` defaults to `false`. No explicit delivery option means Markdown-only local delivery: produce only `PRD.md` plus the minimum Handoff evidence. This default does not call the Mermaid renderer. Generate `PRD.html` only when `LOCAL_HTML` is explicitly enabled; HTML may preserve the Mermaid source when rendered visuals are not selected. SVG files are generated only when `LOCAL_RENDERED_VISUALS` is explicitly enabled. This Alpha implements `LOCAL_HTML` and `LOCAL_RENDERED_VISUALS`; `LOCAL_DOCUMENT`, `FEISHU_DOCUMENT`, and `PROJECT_MANAGEMENT_MCP` remain reserved and `NOT_IMPLEMENTED`. Enabling an unimplemented mode must fail explicitly, with no simulated external side effect. Do not make the user write JSON or ask about switches when their false defaults already match the request.

When `LOCAL_HTML` is requested, do not use raw Markdown-to-HTML conversion as
the normal path. Read the exact Ready `PRD.md` and
`references/policies/prd-reader-html-guide-v1.md`, then author a separate
zero-context reading view. Write it inside the current Run's `work/` directory,
create an exact `html_source_ref` with `path`, `hash`, and the current Candidate
`version`, and submit that ref with the `handoff` action. The resulting
`html_generation.mode` must be `AGENT_AUTHORED_ZERO_CONTEXT_VIEW`.

The HTML is a non-authoritative reading projection. It may reorder, explain,
group and visually compare material, but it must not change product meaning,
invent evidence, or turn a proposed/not-run state into implementation or
validation. `PRD.md` remains the editing truth. Before reporting completion,
check the generated page in a real browser at 1440px and 390px as specified by
the guide; if browser access is unavailable, report that validation as
`NOT_RUN`.

Retrospective is optional and non-blocking. Continue to `retrospective` only when the user or project policy explicitly requires it; otherwise leave its status truthful as `NOT_RUN` and finish the task. It does not block Local Handoff completion or task end. Later audits are ordinary append-only documents; they do not add a Controller action or rewrite a historical Review. Report Human Reader validation, Product Eval execution, external delivery, engineering receipt/tests, and product-effect validation as `NOT_RUN` unless separately observed. Never call this path multi-PRD, production-ready, externally delivered, or backward compatible with pre-2.0 Runs.

For `resume`, the runtime fingerprint must exactly match the Run. If it differs, stop recovery and explain the mismatch; this Alpha does not implement predecessor compatibility or version migration.

## Project Template configuration

Natural-language requests such as “为这个项目启用内部产品模板” are the complete user-facing interaction. Treat them as project configuration, not a Graph action. Do not ask the user to run a command, calculate hashes, copy files, or edit `template-profile.json`. Resolve the independently distributed Pack root from the available project/workspace context; ask one targeted location question only when no unique Pack can be resolved.

Then, without exposing implementation syntax unless the user asks for debugging or recovery details, use this internal Host control action:

```text
python3 ${CLAUDE_PLUGIN_ROOT}/skills/better-product-graph/scripts/bpg_runner.py \
  --operation configure-template \
  --pack-path <absolute-template-pack-root>
```

The action validates the Pack schema, its declared BPG compatibility, exact Template and output-contract hashes, trusted destination, and symlink boundary before materializing the exact files under `.better-product-graph/templates/`. It creates no Run. Reconfiguring the same exact version is idempotent. An upgrade, downgrade, or switch from another active project Template requires the user's explicit version-change authorization and `--allow-version-change`.

## Execution sequence

1. Resolve and validate the exact project root. Reject HOME, filesystem root, or a broad workspace collection.
2. Run `${CLAUDE_PLUGIN_ROOT}/skills/better-product-graph/scripts/bpg_runner.py --self-check` before a state-changing request. Resolve every path from `${CLAUDE_PLUGIN_ROOT}`, never the source checkout.
3. Treat an ordinary BPG request as BPG 2.0 by default. Strip an optional legacy `alpha` alias without changing runtime selection.
4. Read the complete installed BPG 2.0 method before the first mutation, then create the exact `start` payload or load the exact current BPG 2.0 Run.
5. Copy all exact state, Candidate, Review, and operation bases from the immediately preceding Controller response. Never reconstruct them from memory or another Run.
6. Perform product semantics as the Host Agent; use the installed runner only for deterministic authority and persistence.
7. Render conclusions and next steps first. Separate evidence, inference, unknowns, authority, external status, and local completion.

### Internal Writing Reviewer product evaluation

`writing-eval.prepare` and `writing-eval.review` are evaluator-harness operations, not user-facing product actions and not Product Graph nodes. Use them only for an explicit installed Writing Reviewer evaluation whose Agent workspace excludes all expected/scoring files. They create state only under `.better-product-graph/writing-evals/`; they never create a Product Run or enter Ready or Handoff.

The evaluator first supplies one closed `writing-eval-prepare.v1` payload containing only an Agent-visible suite manifest, opaque case manifest, exact Candidate, and anonymous author-attempt identity:

<!-- writing-eval-prepare-contract -->
```json
{
  "schema_version": "writing-eval-prepare.v1",
  "suite_id": "better-product-graph-prd-readability-v0.4",
  "case_id": "case-001",
  "suite_ref": {"path": "agent-suite.json", "hash": "sha256:<exact>", "version": 1},
  "case_ref": {"path": "case-001/case-manifest.json", "hash": "sha256:<exact>", "version": 1},
  "candidate_ref": {"path": "case-001/candidate.md", "hash": "sha256:<exact>", "version": 1},
  "author_execution_ref": {"kind": "HOST_AGENT_ATTEMPT", "id": "anon-author-case-001"}
}
```

```text
python3 ${CLAUDE_PLUGIN_ROOT}/skills/better-product-graph/scripts/bpg_runner.py \
  --operation writing-eval.prepare \
  --run-id <exact-eval-run-id> \
  --payload-file <project-relative-writing-eval-prepare.json>
```

The Controller returns the exact `writing-eval.review` dispatch and a dynamic preregistration checkpoint created before any result. The independent subagent reads only the returned Controller-owned immutable snapshot, isolated inputs, and installed instruction, produces the closed `document-experience-reader-eval.v3.1` result, and submits it through:

```text
python3 ${CLAUDE_PLUGIN_ROOT}/skills/better-product-graph/scripts/bpg_runner.py \
  --operation writing-eval.review \
  --run-id <exact-eval-run-id> \
  --payload-file <project-relative-writing-eval-result.json>
```

Completion means only that one Agent evaluation result was recorded. Evaluator scoring and human reader observation are separate evidence; human reader validation remains `NOT_RUN` unless actually performed.

## Completion language

- Say “本地已生成、可交接” only when the exact local Handoff validates.
- Never turn local generation into “已发送”, Reviewer advice into approval/blocking authority, or a generated Eval attachment into executed tests.
- If a required Agent evaluation, external receipt, professional decision, engineering test, or product-effect observation is absent, report `NOT_RUN`, `NOT_AVAILABLE`, or the exact unmet state.
