# Changelog

## 0.2.6 — Unreleased — Unique build identity, current Roadmap, and localized PRD names

- Restore one-to-one release identity after two development artifacts were both labeled `0.2.5`; all new builds, isolated installs, and later repository syncs use `0.2.6` and bind one exact clean commit and artifact hash.
- Make new PRD titles follow the user's explicit or current working language, with `zh-CN` as the fallback, instead of defaulting to an English slug.
- Enforce one exact localized stem across the self-contained PRD directory, Markdown filename, and unique H1; reject unsafe path characters, invalid language tags, and identity drift before archive writes.
- Preserve already archived/released document names as immutable history; a title or naming change creates a new Candidate version rather than renaming old bytes.
- Release Roadmap v0.16, correcting the Bootstrap state to “PRD Ready / local Release / local Handoff complete” while keeping engineering implementation, actual Bootstrap experiment, executed tests, and external approval explicitly `NOT_RUN` or `NOT_CLAIMED`.

## 0.2.5 — 2026-08-24 — Superseded development identities

> Do not redistribute or rebuild under `0.2.5`: a public development lineage and a later local runtime-fix lineage used the same version with different commit and artifact hashes. `0.2.6` is the first converged successor identity.

- Add a reversible Prompt-only dependency-aware method inside the existing `problem.learning.loop`, with LIGHT-first short-circuiting, a temporary Ready Frontier, source routing, one PM-facing MVU, and action-relative sufficiency.
- Keep waiting and Evidence-driven recomputation honest and bounded: sequential work only inside one unsubmitted Host attempt, at most one recomputation, no claimed cross-submit WAIT / resume, and no claimed real fan-out.
- Publish a machine-readable G1—G7 installed contract, including the complete `interview skip → exact Evidence → interview resume` oracle, while retaining the existing Node Result fields and explicitly not claiming Controller closed-world enforcement.
- Preserve the frozen architecture: no new top-level Node, Artifact type, State schema, dedicated Grilling Agent, Owner checkpoint, or second source of truth.

- Publish the exact `semantic_output.structure_mode` enum in the installed `prd.generate` instruction instead of forcing the Host to infer a hidden field from source code.
- Honor the selected template output contract's declared `default_structure_mode` when a non-legacy submission omits the field, while retaining legacy heading detection.
- Declare the 0.2.2 `prd.generate` instruction hash as a compatible predecessor so its unfinished dispatch can resume without rewriting durable Run state.

- Reconstruct the Ready request from the exact current Candidate metadata, preserving a legal `experiment-contract.v1` through Required Evals fulfillment and joint re-review without weakening the shared Ready validator.
- Treat the immutable Ready audit snapshot as a verified event-chain prefix checkpoint so a retry after partial Controller receipt issuance can reuse the same Gate attempt instead of conflicting with later receipt events.
- Make redundant public `resume` on an already ACTIVE Run idempotent, and recover the original Ready attempt only when exact Controller transaction journals prove the legacy suffix was composed solely of ACTIVE-to-ACTIVE no-op resumes.
- Keep malformed Experiment contracts fail-closed, preserve `execution_status=NOT_RUN`, and retain the ordinary Review → Ready → immutable Release → local Handoff lifecycle with no Experiment fast lane.

## 0.2.4 — 2026-08-24 — Authoritative public Eval repair resume

- Make public `resume` return the typed `EVALS_FULFILLMENT_REQUIRED` contract whenever the exact active Run is stopped at `prd.ready.gate` with pending REQUIRED Evals, including compatible legacy-graph recovery and repeated resume.
- Expose the authoritative closed `{path,hash,version}` Candidate ref, `fulfill-evals` repair operation, `NOT_RUN` execution boundary, and `review.parallel` repair route at the runner top level so a Host can fulfill without guessing Controller internals.
- Preserve the existing COMMIT and EXPERIMENT Ready authority, distinct builder/reviewer validation, zero Ready receipts, zero Release, and ordinary Review re-entry.

## 0.2.3 — 2026-08-24 — Recoverable REQUIRED Eval fulfillment

- Keep EXPERIMENT and COMMIT on the same Product Planning → PRD → Review → Ready → Handoff pipeline while returning an explicit `EVALS_FULFILLMENT_REQUIRED` repair condition before any false Ready or Release claim.
- Bind an exact Agent-produced Eval Pack and fixtures plus a distinct independent testability review, preserve `execution_status=NOT_RUN`, and route the same Candidate back through ordinary joint Review before Ready is recalculated.
- Compatibly upgrade exact 0.2.2-era Runs already stuck at `prd.ready.gate`, without rebuilding the Candidate or weakening the COMMIT Required-Evals gate.

## 0.2.2 — 2026-08-24 — Public experiment contract and compatible resume

- Publish the complete closed `experiment-contract.v1` field, type and enum contract plus a legal installed example in the public `prd.generate` instruction.
- Return exact field-path errors for missing, mistyped, unknown or illegal experiment fields instead of the opaque `complete Agent-authored experiment_contract is required` message.
- Reuse the same validation at PRD assembly and Ready so the two boundaries cannot silently drift.
- Declare the 0.2.1 `prd.generate` instruction hash as a compatible predecessor, allowing its unfinished dispatch to resume under the installed successor contract without rewriting the durable attempt.

## 0.2.1 — 2026-08-23 — Bug contract and local Handoff repair

- Bind the Host-owned `signal.classify` node to the complete Signal Intake classification contract instead of the Controller-only Route Select instruction; keep `route.select` deterministic and reject the old misbound active dispatch as incompatible without rewriting its Run.
- Publish the complete installed `bug.baseline.check` semantic contract, including exact baseline identity, expected/actual behavior, implementation-deviation conditions, and explicit routes, so a Host no longer needs internal source code to satisfy the Validator.
- Execute the declared `IMPLEMENTATION_DEVIATION → handoff.prepare` path as a Controller-verified local Bug Delivery Packet plus human-readable Bug brief, without fabricating a Released PRD.
- Make exact Bug packet creation retry-safe, reject conflicting existing bytes, bind the packet and human view into Run authority, and allow completed Bug Handoffs to be retrieved or redispatched after recovery.

## 0.2.0 — 2026-08-21 — Developer Alpha

- Promote `general@0.2.0` to the configurable released default PRD template while preserving exact per-Run pins, project profile selection, rollback and the frozen upstream compatibility fallback.
- Add a thin Claude Host Adapter over the same Core, Controller, schemas and node instructions as Codex; Codex and Claude artifacts remain host-bound and share one Core fingerprint.
- Preserve Roadmap v0.13 as the integration baseline and add separate Codex/Claude packaging, validation and isolated-install paths.
- Record the one authorized Claude authenticated Host trial honestly as `PARTIAL 6/7`: all tested writable, recovery, permission and Handoff boundaries pass; read-only Help rendered without runner evidence. Auto-selection and Product Golden judgment remain `NOT_RUN`.
- Open the curated release repository under Apache-2.0 with a bilingual user README, eli distillation attribution, public installation guide, minimal CI, structured feedback forms, security reporting, and contribution guidance.
- Publish one GitHub pre-release with separate deterministic Codex and Claude Marketplace ZIPs plus `SHA256SUMS`; both artifacts share one Core fingerprint and carry their own Host manifest, license, notice, and build identity.
- Release Roadmap v0.14 and move Bootstrap to the next Developer Alpha instead of presenting it as a `0.2.0` capability or release blocker.

## 0.1.20 — 2026-08-21 — Optional EvidenceRecord Ready convergence

- Accept an explicit empty `evidence_refs` list when the Candidate still binds exact Decision, Roadmap, Product Plan, Slice, and Knowledge authority.
- Keep every present EvidenceRecord exact-bound and independently validated, and continue requiring at least one Decision Record.
- Preserve compatible-successor recovery so the same 0.1.17-origin Run can resume through Ready, release, and local handoff after installation.

## 0.1.19 — 2026-08-21 — Explicit compatible-upgrade Run recovery

- Keep completed historical Node dispatches bound to their durable state/event/result authority instead of rejudging them against later installed instruction bytes.
- Resume an unfinished dispatch only when its stored instruction hash is exact or explicitly allowlisted by the installed successor contract; arbitrary or undeclared drift remains zero-write blocked.
- Expose the durable dispatch hash, installed instruction hash, and `EXACT` or `DECLARED_COMPATIBLE_SUCCESSOR` status to the Host without rewriting the frozen dispatch contract.

## 0.1.18 — 2026-08-21 — Review disposition and commitment fidelity contract

- Publish the exact `ACCEPTED_CURRENT_PRD_REPAIR` status and non-empty `repair_scope` required to route an accepted `CURRENT_PRD` Finding into `prd.optimize`.
- Tell Reviewers not to invent a second consent checkpoint when exact bound commitments already authorize an automatic operation; review undisclosed extra side effects separately.
- Preserve the 0.1.17 human-readable PRD changelog contract and all existing Ready, release, authority, recovery, and REQUIRED-Evals fail-closed behavior.

## 0.1.17 — 2026-08-21 — Human-readable PRD changelog contract

- Accept the default general template's visible `附录 C：文档变更日志` heading instead of requiring the undocumented machine token `DOCUMENT_CHANGELOG` inside human PRD prose.
- Keep legacy machine-token compatibility while recognizing explicit Chinese and English Markdown changelog headings only.
- Make the installed `prd.generate` instruction state the exact default-template heading so a real Host does not have to guess an internal validator token.

## 0.1.16 — 2026-08-21 — Controller-derived PRD generation authority

- Add a closed `prd_generation_context` to every `prd.generate` dispatch so the Host copies exact Decision, roadmap, Product Plan, Slice, Knowledge, Evidence, active-scope, and traceability authority instead of reverse-engineering Controller internals.
- Independently recompute that authority before Candidate persistence; guessed, incomplete, duplicated, or stale metadata is rejected with no Run mutation and can be corrected on the same attempt.
- Keep PRD prose, product rules, acceptance criteria, risks, and runtime-input design Agent-authored; the Controller supplies provenance only and does not generate product semantics.

## 0.1.15 — 2026-08-21 — Immutable installed-root execution boundary

- Return an exact absolute `instruction_path` and explicit working-directory rule with every Host dispatch so installed resources can be read without changing away from the user project.
- Reject the installed plugin tree as a project root before Git preflight, locks, or Graph state can write anything; a mistaken invocation is now fail-closed and byte-stable.
- Disable Python bytecode writes from the installed bootstrap so normal execution does not mutate the installed plugin inventory.

## 0.1.14 — 2026-08-21 — Product Planning shared-contract convergence

- Treat an embedded shared-contract definition in the exact committed Product Planning Node Result as authoritative for Slice dependency binding; an external `authoritative_ref` is optional rather than an undocumented prerequisite.
- Validate shared-contract IDs, consumers, and contract statements explicitly, and return a Slice-specific repair target when a dependency names an unknown contract.
- Expand the installed Product Planning contract with a real embedded shared contract and dependent Slice, closing the real Host failure at `product.planning` without inventing external files.

## 0.1.13 — 2026-08-21 — Standalone installed Host control plane

- Documented the exact installed Host submission command and general `node-result.v1` envelope in the public Skill.
- Removed the real Host's dependency on source code, memory, or historical sessions to discover `--operation submit`.
- Added complete unique semantic upstream roles to both Problem Quality Review examples, including the honest zero-Finding path.

## 0.1.12 — 2026-08-21 — Complete remaining delivery-stage Host contracts

- Added validator-ready installed semantic examples for Product Planning, PRD Generation, and zero-Finding parallel review.
- Closed the real Host failure where Product Planning had to guess hidden profile, module, iteration, dependency, Slice, and stable PRD identity fields.
- Kept all runtime authority, Ready, Evals, versioning, and local-only delivery boundaries unchanged.

## 0.1.11 — 2026-08-21 — Complete installed Host contracts

- Installed discovery instructions now publish parseable, validator-aligned contracts for Signal preparation, Evidence collection/mapping, Assumption Audit, Problem Learning, Problem Synthesis, zero-Finding Problem Review, and the separate typed Owner Choice command.
- A Host submission may omit `--requested-node` when the Controller has exactly one legal edge; ambiguous routes still require an explicit choice, and Product Decision still waits for independent Owner authority.
- Problem Quality Review now accepts honest `findings: []` plus `dispositions: []` instead of forcing a Reviewer to invent a defect.
- `--interaction=no-pm-interview` is an explicit supported form with a quoted-Signal-safe example, while the existing suffix remains compatible.
- A failed automatic `git init` leaves existing project files byte-identical; the sensitive `.gitignore` baseline is written only after repository initialization succeeds.
- V1.4 architecture, Roadmap v0.12, REQUIRED-Evals fail-closed behavior, and local-only Handoff boundaries remain unchanged.

## 0.1.10 — 2026-08-21 — Product Decision Host contract hotfix

- The installed `product.decision` instruction now publishes one complete, parseable `semantic_output` contract whose exact example passes the same public Validator without reading source code or guessing hidden fields.
- Human interaction keeps machine enums internal: the Host leads with plain Chinese recommendations and converts an Owner's ordinary-language choice into the typed command only after the advisory proposal is accepted.
- `action_risk` remains Agent-authored and Controller-validated. An empty `non_waivable_policy_violations` list is explicitly limited to “no known violation in the exact bound inputs” and never claims an independent compliance review ran.
- Distribution and the existing REQUIRED-Evals fail-closed boundary advance to candidate version 0.1.10; V1.4 architecture and Roadmap v0.12 remain byte-frozen.

## 0.1.9 — 2026-08-21 — Delivery contract integrity

- Product Plans now bind each Slice to a stable `planned_prd_id`; the Controller recomputes `active-scope-ref.v1` from the exact committed `product.planning` Node Result, so same-Slice PRD revisions create immutable vNext Candidates without rewriting Plan bytes. Material scope changes create one typed Controller-owned `PLAN_RECONCILE_REQUIRED` route transaction before any Candidate write; resumed Planning receives the exact delta and can only regenerate the stable PRD as the exact superseding vNext.
- Every new Candidate has closed `spec-traceability.v1` and `product-runtime-inputs.v1` contracts. Committed Controller provenance determines trace origins; the portable runtime minimum is project workspace plus product signal, and direct, nested, aliased, mutable, machine-local, or Candidate-version specification leakage is rejected before persistence.
- `mechanical_contracts` now validates Graph-native upstream artifacts by role: `evidence.collect`, `product.planning`, and `evidence.map` Node Results plus the exact Markdown Product Plan bound by the Planning result. Legacy Host-shaped `{kind, version}` stand-ins are rejected without weakening exact refs, receipt authority, or the six Ready categories.
- Distribution remains skills-only, local-file-backed, single-Controller, and Reviewer `ADVISORY_ONLY`; V1.4 architecture and Roadmap v0.12 baselines remain byte-frozen.

## 0.1.8 — 2026-08-20 — Formal Problem Ready outcome hotfix

- `problem.ready.gate` now persists the architecture-defined `READY | NOT_READY` calculation instead of a generic `PASS` or a pre-result exception.
- `NOT_READY` preserves exact unmet conditions, affected refs/Finding IDs, deterministic repair targets and the Gate resume point without entering Product Decision; repeated public dispatch returns the same immutable result and receipt.
- The Controller-owned calculation is closed-world, exact refs are retained, READY crash recovery remains result-first and idempotent, and installed instructions expose both human-readable outcome shapes.

## 0.1.7 — 2026-08-20 — Empty-Finding aggregate hotfix

- `review.aggregate` now treats an explicit `findings: []` as a valid no-defect Review outcome instead of a missing field, so Reviewers never need to fabricate a Finding to finalize.
- The installed contract defines exact collection cardinality: Reviewer attempts and roles remain non-empty; Findings and disagreements may be empty; dispositions are empty exactly when Findings are empty and otherwise close every Finding once.
- Missing, null, mistyped, empty-required, duplicated, unmatched, and unknown-Finding-reference combinations fail before authoritative Run writes; closed-world fields and REQUIRED-Evals fail-closed remain unchanged.

## 0.1.6 — 2026-08-20 — Closed-world Review Aggregate hotfix

- `review.aggregate` now rejects unknown keys across its semantic output, exact aggregate/disposition JSON artifacts, Candidate/attempt/Finding/disagreement/disposition mappings, and artifact refs before authoritative Run writes.
- Errors identify the exact unknown-field path; the existing non-authoritative `declared_role` metadata remains supported without changing Controller-owned roles.
- Explicit empty disagreements, the accepted-repair v0.6 lifecycle, and REQUIRED-Evals fail-closed behavior remain unchanged.

## 0.1.5 — 2026-08-20 — Empty-disagreement contract hotfix

- `review.aggregate` now distinguishes a required-but-empty `disagreements: []` from a missing, null, or wrong-type field, matching the installed Host instruction.
- Non-empty disagreement entries must identify a topic and exact preserved Findings; malformed entries fail before authoritative Run writes.
- A fresh-installed v0.6 accepted-repair path now covers Optimize, no-disagreement re-review, Ready, Release, and local Handoff while REQUIRED Evals remain fail-closed.

## 0.1.4 — 2026-08-20 — Retry-safe Host submit hotfix

- Every public Host-Agent submission now completes schema, exact dispatch, node semantics, artifact role/path/hash/version, and requested-route preflight before publishing an authoritative result or receipt.
- Invalid artifacts and routes leave the Run authority inventory byte-identical, so the Host may correct the payload and resubmit the same attempt; an already-published attempt retains exact identity-conflict behavior.
- Recovery revalidates persisted Host artifact authority before creating a missing receipt, while valid result-first crash recovery and deterministic staged Candidate finalization remain unchanged.
- Installed instructions now state that hashes are computed from final artifact bytes and that a rejected validation can be retried with the same attempt ID.

## 0.1.3 — 2026-08-20 — Review aggregate recovery hotfix

- Installed `review.aggregate` instructions now expose the complete first-submission contract for exact aggregate and disposition artifacts, Candidate identity, Reviewer set, Finding preservation, and disposition closure.
- Invalid, stale, duplicated, forged, or path-escaping aggregate artifacts fail before result persistence, attempt consumption, state/event progress, or deterministic finalization.
- `review.finalize` revalidates the same exact authority and applies Controller-owned canonical artifact roles; a v0.5 Candidate with RECOMMENDED Evals can complete Ready, Release, and local Handoff.
- An aggregate may route to `prd.optimize` only when at least one exact current-PRD repair and repair scope is accepted, preventing another post-transition stranded Run.

## 0.1.2 — 2026-08-20 — Installed Ready contract hotfix

- Installed Problem Quality Review instructions now expose the complete first-submission contract used by validation and Problem Ready, including exact Candidate/upstream refs, review version, Finding dispositions, and advisory-only authority declarations.
- Incomplete Problem Review results fail before persistence or state progress with field-level repair guidance instead of stranding the Run inside the mechanical Gate.
- PRD Ready receipts now preserve caller-declared artifact roles as non-authoritative metadata while applying Controller-owned canonical roles last, so legitimate v0.4 Candidates can release without allowing role escalation.
- Duplicate or missing exact upstream facts fail before Candidate or Ready side effects; REQUIRED Evals remain fail-closed and RECOMMENDED Evals remain releasable.

## 0.1.1 — 2026-08-20 — PRD Optimize lifecycle hotfix

- `prd.optimize` now archives the Host Agent's complete revised PRD as a new immutable Candidate before targeted re-review.
- Exact source Candidate, accepted review dispositions, repair scope, next version, changelog and unchanged advisory items are enforced by the local Controller boundary.
- Stale/conflicting submissions fail before state advance; exact retries recover across archive, result and transition crash boundaries.
- Distribution identity is bumped independently of the frozen V1.4 architecture and v0.12 Roadmap baselines.

## 0.1.0 — 2026-08-20 — Local candidate

- 建立唯一公开 Codex Skill、版本化 Graph/node contract registry，以及 installed Host runner 的 `entry`、`dispatch`、`submit`、`owner-choice` 执行面。
- 接入 executable schemas、node-specific validators、exact result/Controller receipts、programmatic Ready、immutable release 与 exact local Handoff。
- Installed runner 现在自动执行 Controller-owned Problem/Plan/PRD Ready Gates；`review.finalize` 从真实 persisted Review 生成同 PRD 版本的新 Candidate generation，保留旧树并禁止 Host 自报 FINALIZED。
- Mechanical Ready receipt 全量绑定并重算 Candidate metadata 中的所有 Decision/Evidence refs，不再只验证首项。
- 增加 occurrence-first Signal ledger、Git preflight、CAS/跨进程锁、事务恢复、fanout/late-result 安全边界和 tamper-evident installed identity。
- 实现 Incident、Bug、Discovery/Assumption/Learning/Synthesis/Decision、Outcome-first Planning、PRD、advisory Review 和 Decision/Product memory 的本地合同。
- 打包非 discoverable Better Question、20 个认知基座与 Product Goal Fidelity references，并验证来源/安装完整性。
- 增加 Product Golden v0.2 contract fixtures、Plugin Contract、确定性 ZIP、隔离安装/卸载/回滚 smoke 和 rejected-audit repair verifier。
- 所有 public Run 操作现在先经过 event-authoritative read barrier；每次 Controller state commit 都把 canonical full-state before/after hash 写入 WAL 与事件权威，schema-valid snapshot 任意字段篡改、伪 artifact、过期 dispatch、WAIT 绕过和未恢复事务均 fail closed。
- Ready 现在只接受同 Run 的 Controller-authoritative Decision/Evidence，Evidence producer 合同覆盖 `evidence.collect` 与后续 `problem.learning.loop`；false upstream、跨 Run receipt 和未绑定 release 均拒绝。
- 增加 recoverable Candidate review-companion generation、typed `NEW_EVIDENCE` WAIT trigger、严格 audit timestamp，以及含 `VC5-C1` 的 35 项逐 finding 结构化 repair verifier。
- 保持真实 authenticated Host Agent 与 Product Golden Agent judgment 为 `NOT_RUN`；未 public publish、push、tag 或 global install。
