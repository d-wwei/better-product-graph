---
name: better-product-graph
description: Use when handling product ideas, user feedback, online issues, product discovery, product decisions, outcome-first planning, versioned PRDs, configuring a Better Product Graph Template Pack, or resuming/auditing a Better Product Graph run. The BPG 2.0 single-PRD runtime is the default; the legacy 0.x public route is removed. Do not use for simple PRD copy-editing, generic project management, or requests to bypass the governed workflow and invoke an internal action directly.
---

# Better Product Graph

Better Product Graph turns a raw product Signal into a responsible next action. A valid result can be STOP, WAIT, RESEARCH, EXPERIMENT, COMMIT NOW, or FUTURE ROADMAP; never force every Signal into a PRD.

## Runtime boundary

- You, the Host Agent, perform semantic product work: research, Evidence interpretation, guided interview, challenge, recommendation, Planning, PRD writing, and advisory Review.
- Deterministic scripts perform only exact identity, authority, state, Candidate, Review, Ready, Local Handoff, version, persistence, and recovery checks.
- Never ask Python to infer the problem, choose a product outcome, generate a Plan/PRD, judge quality, or invent a Reviewer Finding.
- Only the Controller may update formal state or promote an artifact. Agent recommendations and Reviewer concerns are proposals, not Gate results.

## Default public entry

Every ordinary `$better-product-graph <product task>` invocation and equivalent natural-language request uses the BPG 2.0 single-PRD runtime. The user does not need to type `alpha`, `new`, or any internal action name.

The legacy 0.x public route is removed. Never send an ordinary request to `HostRuntime.handle_entry`, the legacy stable-intent parser, or the legacy entry/dispatch/submit control plane. Never import, migrate, alias, or resume a pre-2.0 Run. If an old Run is mentioned, explain that it is historical and start a fresh BPG 2.0 Run only after the user asks to proceed.

The older `$better-product-graph alpha ...` spelling is accepted only as a temporary, non-required alias for the same default runtime. It must never select a distinct path or restore the 0.x route.

Map the user's goal to one BPG 2.0 action without exposing the action name unless debugging:

| User goal | Controller action | Boundary |
|---|---|---|
| Start a product task | `start` | Create one fresh `.better-product-graph/v2/` Run. |
| Check a Run | `status` | Read-only exact state. |
| Continue a Run | `resume` | Resume only the exact BPG 2.0 Run and valid safe point. |
| Pause a Run | `pause` | Persist one safe pause boundary. |
| Route non-PASS Findings | `review-route` | Lead Agent decision after Reviewer Findings; never a Reviewer command. |
| Prepare local delivery | `handoff` | Local Handoff only; never external delivery. |
| Record the planning retrospective | `retrospective` | Non-blocking post-Handoff record. |

If a request has no actionable product task and no exact Run to inspect, ask only for the smallest missing information and do not mutate state. Reject `$bpg`, `$prd-graph`, `review.gate`, legacy aliases, and internal action IDs as public entry points.

## Default BPG 2.0 single-PRD runtime

Before the first mutation, run installed self-check and read the complete installed `references/alpha/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.2.md`. That document owns product semantics; the BPG 2.0 Controller owns only exact identity, authority, state, Candidate, Review, Ready, and Local Handoff bindings.

The runtime always creates or resumes state under `.better-product-graph/v2/`. Drive the installed runner with one temporary JSON object per operation:

```text
python3 <installed-skill-root>/scripts/bpg_runner.py \
  --operation alpha \
  --payload-file <absolute-json-payload>
```

`--operation alpha` is an internal installed-runner identifier, not user syntax and not an opt-in product route.

The payload's `action` is one of `start`, `status`, `replace-record`, `freeze-candidate`, `review`, `review-route`, `decision-route`, `pause`, `resume`, `handoff`, or `retrospective`. Copy the exact `run_id`, `state_version`, Candidate ref, and operation basis returned by the immediately preceding Controller response. Use a fresh, stable `operation_id` for each intended state change; exact replay is idempotent, while reusing an ID with different content is forbidden.

Follow the five semantic stages in the installed BPG 2.0 reference. Keep one continuously updated `planning-record.md`; freeze it as `PROBLEM`, then `DECISION`, and finally freeze exactly one `PRD` Release Set from the current Run's `work/prd/` directory. The Host Agent writes and revises product meaning. The Controller must not decide problem quality, value, risk, reversibility, return stage, Reviewer applicability, PRD quality, or Product Evals applicability.

`replace-record` is always a complete replacement, never an append. Copy the current `planning_record_ref.hash` into `base_hash`, set `mode=REPLACE_FULL`, and submit the complete new Markdown. The Controller rejects stale hashes and accidental removal of existing H2 sections before it writes any bytes. A deliberate section removal requires one exact upstream return basis; protected Signal/boundary content cannot be removed. Mechanical rejection creates no Candidate and consumes no semantic revision round. When advancing from `PLAN_PRODUCT_SYSTEM` to `PRD_AUTHORING`, include the exact nine Stage 4 dispositions returned by the method contract. Each is `COMPLETE`, `NOT_APPLICABLE` with a concrete rationale, or `BLOCKED` with missing input, owner and recovery. Any `BLOCKED` item prevents advancement.

Each Problem and Decision Review must run in a genuinely independent `HOST_SUBAGENT_ATTEMPT` over the frozen Candidate. The Reviewer submits only concrete Findings and a Verdict; it never supplies `return_target`. For every non-PASS Review, the lead Host Agent separately submits `review-route` with the exact Review and Finding refs, earliest affected stage, reason and scope. A revision uses a new Candidate, has at most two automatic rounds, and requires both difference review and whole-product regression. After a passing Decision Review, only the Owner may choose `STOP`, `WAIT`, `RESEARCH`, `EXPERIMENT`, or `FUTURE_ROADMAP`. Every Owner Choice and Agent `COMMIT_NOW` authorization must bind one real Host message, the exact current Run and Decision Candidate, the allowed outcome, permission scope and issued time. Agent `COMMIT_NOW` also requires all Controller checks; otherwise stop and return to the Owner.

Candidate storage is content-addressed inside the Run. The Controller stores identical bytes once and returns object refs; never create or copy a separate Work, Candidate and Handoff tree by hand. Handoff alone materializes the finalized delivery files once.

Before freezing a PRD, the author must submit the closed `bpg2-alpha-document-experience.v1` self-check over the exact draft. It records the current Writing Profile and Guide identity, diagnoses, actions, zero-context reading path and the reason a single PRD remains appropriate. It is author evidence, never independent approval.

The PRD freeze response contains `current_review_requirements`. Use it as the only PRD Review work order. It binds the exact Markdown PRD, Planning snapshot, accepted Decision and Review, Template, Output Contract/checklist, Writing Profile, Writing Guide, Writing Review Contract and applicable Product Eval attachments. Do not reconstruct, rename or substitute those refs. Candidate and Review contain no rendered delivery format.

PRD Review remains one existing Review node and one final Verdict, but requires two distinct read-only Host attempts. A content Reviewer covers the applicable product, experience, system, engineering and acceptance responsibilities. A separate `HOST_SUBAGENT_ATTEMPT` runs the installed `document-experience-reader-review.v3` Writing Review over exactly the five isolated refs in `writing_review_context`. The author, content Reviewer and Writing Reviewer IDs must differ. Do not use `writing-eval` as Product Run evidence.

Record all six `responsibility_ids` separately as `PASS`, `FINDING`, or `NOT_APPLICABLE` with rationale, exact basis refs and linked Finding IDs. The Writing Reviewer owns `DOCUMENT_EXPERIENCE`; empty Findings never substitute for coverage. It reviews content structure, readability, navigation logic and visual-source use in the exact Markdown Candidate. Any Candidate, Profile, Guide, contract or basis change makes prior Review evidence stale. Do not generate, open or review HTML during Candidate Review.

Use source-first visuals. Prefer a safe Mermaid source plus an already generated safe SVG preview for relationship diagrams; otherwise use a safe SVG source directly. Candidate Review validates the Mermaid/SVG source and preview. PNG is optional and generated only by a Handoff adapter that actually needs raster compatibility. Never require or generate PNG before Candidate content Review.

For PRD delivery, preserve truthful Product Evals status: applicability is `NOT_NEEDED / RECOMMENDED / REQUIRED`, while this Alpha's Evals Generator capability and invocation are exactly `NOT_IMPLEMENTED / NOT_RUN`. Do not author or attach a simulated Eval Pack. `REQUIRED` therefore blocks Ready; `RECOMMENDED` preserves the recommendation without blocking by default. Eval Spec and Eval Pack structure belongs to the later Evals Generator iteration. Ready means the Markdown PRD and content Review are final; delivery rendering is still `NOT_RUN`. Handoff then selects delivery adapters and derives outputs from that exact finalized Markdown and assets.

Translate the user's natural-language Handoff preference into the optional `delivery_options` object. Each delivery mode owns an independent boolean switch. `LOCAL_HTML` defaults to `true`; the user may turn it off, in which case Local Handoff still completes with Markdown/assets and does not create `PRD.html`. Unspecified future modes default to `false`. This Alpha implements only `LOCAL_HTML`; `LOCAL_DOCUMENT`, `FEISHU_DOCUMENT`, and `PROJECT_MANAGEMENT_MCP` switches are reserved but `NOT_IMPLEMENTED`. Enabling any unimplemented mode must fail explicitly, with no simulated external side effect. Do not make the user write JSON or ask about the switch when the default already matches the request.

Handoff is followed by a non-blocking planning retrospective that dispositions the method checks returned by the current Run. Later audits are ordinary append-only documents; they do not add a Controller action or rewrite a historical Review. Report Human Reader validation, Product Eval execution, external delivery, engineering receipt/tests, and product-effect validation as `NOT_RUN` unless separately observed. Never call this path multi-PRD, production-ready, externally delivered, or backward compatible with pre-2.0 Runs.

For `resume`, the runtime fingerprint must exactly match the Run. If it differs, stop recovery and explain the mismatch; this Alpha does not implement predecessor compatibility or version migration.

## Project Template configuration

Natural-language requests such as “为这个项目启用内部产品模板” are the complete user-facing interaction. Treat them as project configuration, not a Graph action. Do not ask the user to run a command, calculate hashes, copy files, or edit `template-profile.json`. Resolve the independently distributed Pack root from the available project/workspace context; ask one targeted location question only when no unique Pack can be resolved.

Then, without exposing implementation syntax unless the user asks for debugging or recovery details, use this internal Host control action:

```text
python3 <installed-skill-root>/scripts/bpg_runner.py \
  --operation configure-template \
  --pack-path <absolute-template-pack-root>
```

The action validates the Pack schema, its declared BPG compatibility, exact Template and output-contract hashes, trusted destination, and symlink boundary before materializing the exact files under `.better-product-graph/templates/`. It creates no Run. Reconfiguring the same exact version is idempotent. An upgrade, downgrade, or switch from another active project Template requires the user's explicit version-change authorization and `--allow-version-change`.

## Execution sequence

1. Resolve and validate the exact project root. Reject HOME, filesystem root, or a broad workspace collection.
2. Run installed self-check before a state-changing request. Resolve all paths relative to the installed Skill, never the source checkout.
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
python3 <installed-skill-root>/scripts/bpg_runner.py \
  --operation writing-eval.prepare \
  --run-id <exact-eval-run-id> \
  --payload-file <project-relative-writing-eval-prepare.json>
```

The Controller returns the exact `writing-eval.review` dispatch and a dynamic preregistration checkpoint created before any result. The independent subagent reads only the returned Controller-owned immutable snapshot, isolated inputs, and installed instruction, produces the closed `document-experience-reader-eval.v3.1` result, and submits it through:

```text
python3 <installed-skill-root>/scripts/bpg_runner.py \
  --operation writing-eval.review \
  --run-id <exact-eval-run-id> \
  --payload-file <project-relative-writing-eval-result.json>
```

Completion means only that one Agent evaluation result was recorded. Evaluator scoring and human reader observation are separate evidence; human reader validation remains `NOT_RUN` unless actually performed.

## Completion language

- Say “本地已生成、可交接” only when the exact local Handoff validates.
- Never turn local generation into “已发送”, Reviewer advice into approval/blocking authority, or a generated Eval attachment into executed tests.
- If a required Agent evaluation, external receipt, professional decision, engineering test, or product-effect observation is absent, report `NOT_RUN`, `NOT_AVAILABLE`, or the exact unmet state.
