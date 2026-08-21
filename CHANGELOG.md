# Changelog

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
