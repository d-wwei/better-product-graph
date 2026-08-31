# Changelog

## 2.0.0 — Unreleased — BPG 2.0 default single-PRD architecture

- Replace the legacy 0.x public route with the BPG 2.0 single-PRD runtime for every ordinary Better Product Graph request. The older `alpha` spelling remains only as a temporary alias and does not select a separate path.
- Restore the complete Candidate Review and Ready contract: immutable exact review bases, independent content and Writing Reviewer attempts, six explicit responsibility dispositions, stale-evidence rejection, difference review plus whole-product regression, and truthful multi-axis evidence.
- Move HTML generation out of Candidate Review and into Ready-after Handoff. Markdown plus assets remain the editable truth; `LOCAL_HTML` is an independent user-controlled switch that defaults on and can be disabled without blocking Local Handoff.
- Preserve the six decision outcomes, Owner authority, single-PRD Alpha scope, truthful Product Evals states, local-only Handoff, and post-Handoff retrospective. Multi-PRD, external delivery adapters, Product Eval execution, engineering implementation/tests, and product-effect validation remain unclaimed or `NOT_RUN`.
- Establish `2.0.0` as the new software identity for the replacement architecture. This source snapshot is published to the public repository before any Tag or GitHub Release; the latest frozen GitHub Release remains `0.2.20` until separately published.

## 0.2.20 — 2026-08-31 — Opt-in BPG 2.0 single-PRD internal Alpha

- Add an isolated `BPG_2_0_ALPHA` runtime for one complete single-PRD product-planning path: Signal & Route, one planning record, UNDERSTAND, DIAGNOSE & VALUE, frozen Problem/Decision/PRD Candidates, independent Reviews, six exact decision outcomes, whole-part-whole planning, one formal or experimental PRD, unique Ready, Local Handoff, and a post-handoff retrospective.
- Keep product meaning with the Host Agent and deterministic authority with the thin Controller. Enforce exact Run/Candidate/version refs, independent author and Reviewer attempts, at most two automatic revisions, difference review plus whole-product regression, explicit Owner choices, and narrowly preauthorized Agent `COMMIT_NOW`.
- Preserve truthful Product Evals applicability and execution states. Missing REQUIRED material blocks Ready; RECOMMENDED may remain `NOT_AVAILABLE / NOT_RUN`. Local Handoff never claims external delivery, engineering receipt, implementation tests, or product-effect validation.
- Add a dependency-free self-contained HTML reading view with Markdown plus assets as the editing truth, and expose the new runtime through one JSON-shaped installed runner operation.
- Expose BPG 2.0 only through the explicit `BPG 2.0 Alpha` / `$better-product-graph alpha` opt-in trigger. Ordinary BPG requests retain the 0.x path. Old Runs are not imported, migrated, aliased, or resumed by the Alpha.
- Verify the release-candidate development tree at `792/792 PASS`; the preceding Alpha branch and merged `main` each passed `791/791`. One real Codex Host Alpha Run reached `LOCAL_HANDOFF_COMPLETE` after independent Problem, Decision, and PRD Review. Human owner testing, external delivery, implementation, and product-effect validation remain separate and `NOT_RUN`.

## 0.2.19 — 2026-08-27 — Exact stale-Run recovery hotfix

- Add five exact, fail-closed recovery contracts for known `0.2.18` predecessor Runs while preserving the original Run ID, append-only attempts, events, receipts, and artifacts. Unknown stale combinations remain read-only `BLOCKED_STALE`.
- Retire only unconsumed, side-effect-free legacy dispatches and re-dispatch the current contract. Review/Ready recoveries return to a fresh isolated `review.parallel`; old findings and Ready receipts remain historical and cannot regain current authority.
- Restore one missing legacy Candidate only from an exact Git commit/tree/blob inventory under `artifacts/prds/archived`, with cooperative global locking, no-overwrite publication, exact mode/hash checks, and crash recovery.
- Make Ready receipts append-only across Ready attempts, and make natural-language Resume return the current Host work order after transaction reconciliation.
- Make concurrent Resume of an exact recovered `PAUSED` Run symmetric and idempotent for either winner: every caller binds the exact PAUSED basis before writing, and a CAS loser converges only when that basis is hash-bound to one Recovery event followed solely by the legal `PAUSED → ACTIVE` transition and, optionally, one complete current dispatch. Ordinary pauses and unrelated concurrent mutations still raise the original CAS conflict.
- Advance the durable Graph identity to `0.1.0-alpha.4`. The Writing Profile, Guide, Reviewer Instruction, Reviewer schemas, and frozen semantic Eval suites are byte-unchanged from `0.2.18`; no new Writing semantic claim is made by this compatibility hotfix.

## 0.2.18 — 2026-08-27 — PRD Writing Profile v0.5 source promotion

- Complete both preregistered semantic phases on the frozen v0.8 contract: RC5 `27/27 PASS` and the exact final public-candidate artifact `27/27 PASS`. The supported multi-root aggregator rederived both terminal results without rescoring, proved 54 fresh Reviewer identities with zero protected-identity overlap, and returned no cross-phase issue. Human-reader observation remains `NOT_RUN`.
- Complete a fresh ordinary Review of the immutable Evals Generator PRD v0.6 with four independent Reviewers and six advisory Findings. The Review finalized through the existing aggregate/disposition path, then Ready correctly failed closed on reader-visible raw inline SVG before any Ready receipt, Release, or Handoff; the reviewed PRD remains `NOT_READY / NOT_RELEASED` and is not claimed implemented or tested.
- Freeze the exact evaluated Codex and Claude ZIP bytes built from clean source `16d8ce48b999f85d34747afb94ff255d40220c78`. Both Hosts share Core fingerprint `sha256:20b8fe2e26ce0e49172e36c61ec014bbfac857d675644533aae08a86aa0840b5`; package publication and downloaded-artifact/global-install verification remain separate release operations.
- Add a repository-supported, read-only multi-root Release aggregator for the frozen RC5 and Final phase terminals. It binds each phase to an exact central root and installed Skill root, defines Work Order identity as root identity plus root-relative path plus Manifest-bound hash, verifies root containment and regular/non-symlink/single-link custody, preserves all other cross-phase freshness prohibitions, and binds the aggregation evidence to the exact aggregator file hash without rescoring or rewriting historical evidence.
- Promote the exact evaluated `prd-plain-language-zh-CN@0.5.0` Profile and Guide as the PRD default through the versioned registry; retain their frozen candidate bytes so Suite v0.8, RC5 and RC7 evidence remain reproducible. Registry lifecycle state is authoritative for this immutable-artifact promotion, while v0.2 remains the rollback Profile and v0.4 remains failed candidate history.
- Record RC5 Agent Eval `27/27 PASS` and the RC7 ordinary advisory Review as distinct evidence. The ordinary Review finalized eight Findings and dispositioned all eight as `DEFERRED_FUTURE_REVISION`; it did not modify or repair the immutable Evals Generator v0.6 PRD, and human-reader validation remains `NOT_RUN`.
- Preserve the Profile 0.5 Ready boundary: active raw inline SVG remains invalid for Ready/Release. The reviewed v0.6 PRD is `NOT_READY`, with zero Ready receipts and no Release.
- Advance the development source and both Host manifests to final source identity `0.2.18`. The final-artifact Eval and ordinary Review are recorded above; public push, tag, GitHub Release, downloaded-asset verification and global installation remain separately evidenced release operations.

## 0.2.18-rc.7 — 2026-08-27 — Source parser, final asset tree and Review custody closure

- Replace order-dependent regex masking with a source-ordered Markdown literal scanner: arbitrary-length fenced code, indented code, inline code spans and real HTML comments cannot hide or invent a later active raw SVG. Archive, Ready and Release share the corrected classification; Ready still writes zero receipts on rejection.
- Validate the complete strict-Profile visual asset tree, not only Markdown references. Every visual must be one referenced safe SVG plus its exact same-stem `@2x.png`; malicious and safe orphan pairs, missing partners, unknown visual formats, symlinks and unsafe bytes fail closed before archive and again before Ready/Release.
- Tighten `prd-asset-change-set.v1`: exact removals reject nonexistent targets, and `source_ref.version` accepts only a positive JSON integer or non-empty string. Any resulting Candidate tree change invalidates the prior tree-bound Review.
- Add a mechanical ordinary-Review projection contract that requires unique `HOST_SUBAGENT_ATTEMPT` identities and unique exact relative/absolute output targets for all four Reviewer roles, disjoint from author and eval identities, with every output absent before dispatch. RC6 preparation evidence is superseded and non-authoritative; no semantic Reviewer output is created by RC7 preparation.
- Preserve the exact released Evals Generator v0.6, frozen PRD readability v0.8 suite and RC5 report bytes. RC7 makes no global-install, publication or release claim.

## 0.2.18-rc.6 — 2026-08-27 — Source-only ordinary Review convergence

- Allow an exact imperfect or legacy PRD with active raw inline SVG, an unsafe managed visual, or an unavailable visual to enter ordinary advisory Review through a mechanically classified `SOURCE_TEXT_ONLY` path. The scanner runs before any visual consumer, binds exact Candidate bytes and line basis, emits `NOT_RENDERED`, and preserves path/hash/permission failures as dispatch blockers.
- Require the independent Writing Reviewer to create a normal advisory Finding for `RAW_INLINE_SVG`; `PASS` and `NOT_NEEDED` are rejected. Findings continue through the existing aggregate, disposition, optimize and re-review lifecycle without a new Node or Gate.
- Enforce the visual delivery contract for Profile 0.5.0 and future applicable versions before Ready receipts and again before Release. Managed safe SVG/PNG pairs remain strict; Profile 0.2 historical documents retain their original legitimacy.
- Add the optional closed `prd-asset-change-set.v1` producer input so Generate/Optimize can add, replace or remove exact managed SVG/PNG bytes. The Controller validates regular non-symlink sources, traversal, extension, hash and final self-contained pairing; a replacement Candidate receives a new tree identity and old Review evidence is stale.
- Preserve the exact released Evals Generator v0.6, frozen PRD readability v0.8 suite and RC5 report bytes. RC6 does not reinterpret the passed RC5 semantic evaluation and makes no global-install, publication or release claim.

## 0.2.18-rc.5 — 2026-08-27 — PRD Writing Reviewer v0.8 candidate

- Preserve the exact Suite v0.7 and RC4 `24/27 FAIL` evidence instead of rerunning, replacing or rescoring any failed attempt.
- Start a new Suite v0.8 fixture identity because old `case-002` did not contain the competing canonical definitions its frozen oracle assumed; three fresh Reviewers reasonably treated its concise overview/process/AC restatement as functional.
- Keep the public Writing contract and scorer semantics unchanged. The replacement negative contains consequential competing definitions, while a same-domain positive calibration document proves concise summary, canonical reference and behavior AC remain valid.
- Valid A2/B2 blind fixture calibration is `APPROVED`: exact outputs independently agree on six FINDING documents and four PASS documents; the same-domain paired positive remains outside the scored nine.
- Freeze the new v0.8 oracle, preregistration, run contract, evidence reader and scorer only after that agreement. This unique RC5 source identity is now cut; Agent Eval, ordinary Product Review, promotion, publication, release and installation remain `NOT_RUN`.
- Preserve the first v0.8 calibration projection and Reviewer outputs as `SUPERSEDED_INVALID_FOR_CALIBRATION`: its work order leaked a calibration-specific positive hint and some non-case-002 fixtures carried scoring-oriented additions. They remain audit evidence only and cannot contribute to any future denominator.
- Reblind under a new fixture tree and new Reviewer identities only after mechanically proving exact tree completeness, hint-free visible inputs, semantic equivalence for every case except replacement case-002, and no historical output reuse.
- Preserve Profile/Guide v0.5, Instruction/Reviewer v3.2 and Result Schema v3.1 semantics; formal evaluation remains exactly nine cases × three attempts with all produced attempts occupying the denominator and no retry, replacement or best-of-N selection.
- Make v0.8 phase scoring terminal on supported local code paths: derive reports internally behind a non-serializable capability, reserve an independent `O_EXCL` ledger entry, reject caller-supplied reports and partial/replayed bundles, and rederive every phase score from exact evidence before stored replay or Release aggregation. Explicitly limit the claim to fail-closed local workflow integrity rather than cryptographic resistance to privileged code-and-evidence rewriting.

## 0.2.18-rc.4 — 2026-08-26 — PRD Writing Reviewer v0.7 candidate

- Supersede `0.2.18-rc.3` after its Suite v0.6 execution was frozen as `INVALID_HARNESS`: the 27 Runs did not share one central durable project root, so the preregistered scorer could not read one valid denominator and semantic scoring remained `NOT_RUN`.
- Bind this unique RC4 candidate to frozen Suite v0.7, which prepares all 27 Runs under one central durable project root while keeping each Reviewer projection isolated and self-contained; RC1, RC2, and RC3 evidence remains immutable historical evidence and cannot be reused.
- Agent Eval remains `NOT_RUN` at identity cut; this candidate claims no semantic PASS, ordinary PRD Review result, Profile v0.5 promotion, release, publication, or global installation, and human-reader validation remains `NOT_RUN`.

## 0.2.18-rc.3 — 2026-08-26 — PRD Writing Reviewer v0.6 candidate

- Supersede RC2 because frozen Suite v0.6 aligns evaluator scoring with the already-public product contract: one Finding assessment may contain related secondary issue labels or repair techniques while retaining one registered primary diagnosis and primary repair.
- Preserve `0.2.18-rc.1` and `0.2.18-rc.2` as failed historical identities. Neither may be rebuilt, released, installed, reused, or reinterpreted as RC3 evidence.
- Agent Eval remains `NOT_RUN`; this unique RC3 identity claims no semantic evaluation PASS, ordinary PRD Review result, Profile v0.5 promotion, release, publication, or global installation.

## 0.2.18-rc.2 — 2026-08-26 — PRD Writing Reviewer v0.5 candidate

- Replace the invalid `0.2.18-rc.1` candidate identity after its anonymous v0.5 case exporter emitted a private `prd-readability-agent-case.v0.5` envelope and resource-ref fields that the installed Writing Eval runtime correctly rejected.
- Keep the shared, closed `prd-readability-agent-case.v0.4` transport envelope unchanged and make the v0.5 exporter emit that exact installed-runtime contract without changing any fixture, oracle, preregistration, or reviewer semantics.
- Treat `0.2.18-rc.1` as failed historical evidence. It must not be rebuilt, released, installed, or used for semantic evaluation; all candidate gates restart from this unique `0.2.18-rc.2` identity.

## 0.2.18-rc.1 — 2026-08-26 — PRD Writing Reviewer v0.5 candidate

- Cut a new release-candidate identity for the preregistered PRD Writing Reviewer v0.5 evaluation and ordinary Review gates; Profile v0.5 remains a non-default candidate until those gates pass.
- Preserve `0.2.17-rc.2@c9eb267c0857fecd03585fc192ce0bc4c59d5c89` as a failed historical RC. Its result bundle is not upgrade-compatible evidence for this candidate and must not be reused or reinterpreted as v0.5 evidence.
- Keep the immutable v0.4 / RC2 `5/9 FAIL` record and human-reader observation `NOT_RUN`; this candidate identity alone does not claim semantic evaluation, release, publication, or installation success.
- Superseded before semantic execution: its anonymous export contract did not match the installed Writing Eval runtime and therefore could not enter `writing-eval.prepare` through the public built path.

## 0.2.16 — Unreleased — Product Evals Generator local loop

- Add explanatory `NOT_NEEDED / RECOMMENDED / REQUIRED` applicability handling, exact Candidate-bound Product Eval Pack staging, immutable correction history, and truthful applicability/fulfillment/execution/freshness status.
- Package independent `product-eval-pack.v1`, `product-eval-review.v1`, and future execution-receipt schemas while keeping semantic Pack authoring in the Host and real execution/verdict outside BPG.
- Require a genuinely separate, isolated Reviewer before Controller-bound fulfillment; preserve `NOT_RUN`, rerun ordinary PRD Review, and reject empty Packs, invented Ground Truth, false PASS/FAIL, unstaged Pack substitution, and missing authority concealment.
- Expose installed `prepare-evals`, `stage-evals`, and existing `fulfill-evals` control actions for both Codex and Claude hosts without adding a Graph node, public intent, remote connector, or RULE-206 template migration.

## 0.2.15 — Unreleased — Immutable planning-context source history

- Freeze every accepted planning-context source into content-addressed Run-local storage before it becomes an input to later nodes, while retaining the original live ref only as provenance in the committed Node Result.
- Keep completed legacy Runs `COMPLETED` when a formerly accepted live planning source later changes; expose `DEGRADED_SOURCE_DRIFT` as a historical audit warning instead of instructing callers to resubmit an already consumed attempt.
- Continue to fail closed for active Runs, malformed legacy provenance, changed frozen snapshots, and all Candidate, Release, Handoff, receipt, and event-authority drift.

## 0.2.14 — Unreleased — Unique external Template Pack contract identity

- Advance to one new distributable identity after two local/public development artifacts used `0.2.13` with different commits and artifact hashes; do not redistribute or rebuild either `0.2.13` artifact as the team baseline.
- Preserve the external Template Pack configuration capability while binding the project output-contract resolution and required Checklist row/status validation repairs from exact commit `636a546660d91166183b20ec93138a1ded147f71`.

## 0.2.13 — 2026-08-25 — Superseded development identities

> Do not redistribute or rebuild under `0.2.13`: the public/local development lineage and the later project Template contract repair used the same version with different commit and artifact hashes. `0.2.14` is the unique successor identity.

- Let users configure an independently versioned external Template Pack by asking the Host Agent in natural language; do not expose an installer as a product concept or add a Graph Node, public Graph intent, service, daemon, or second source of truth.
- Keep one internal configuration action that validates Pack schema, BPG compatibility, exact Template and output-contract hashes, trusted project paths, symlink safety, and explicit version changes before activation; failed validation remains zero-write and same-version configuration is idempotent.
- Route both installed Host Skills through the existing project Template registry while preserving exact per-Run Template pins, fallback policy, rollback history, and ordinary PRD lifecycle authority.
- Resolve a Run-pinned project Template output contract from the trusted project template area during Writing Review instead of incorrectly forcing it through the installed-skill reference catalog; retain exact Hash and symlink checks.
- Allow an output contract to declare required Markdown table rows, legal status values, and reason-required statuses so Generate and Optimize can fail closed on omitted business Checklist content before Candidate archive and Ready.

## 0.2.12 — Unreleased — Compatible in-flight Optimize context upgrade

- Enrich an exact declared-compatible predecessor `prd.optimize` dispatch at read time with the new Controller-derived trace authority while preserving its attempt ID, input bindings, and historical durable contract.
- Accept submission from that same predecessor attempt only when its durable Optimize context is the exact predecessor shape whose sole difference is the additive `metadata_authority`; all other context drift remains fail-closed.

## 0.2.11 — Unreleased — Public PRD Optimize trace authority

- Publish the complete Controller-derived `optimize_context.metadata_authority.spec_traceability` so an installed Host can copy the exact current Candidate and review aggregate origins without guessing hidden validator state.
- Require byte-for-byte trace copying, reject tampered origins before Candidate persistence, and retain the 0.2.10 review instruction hash for exact in-flight Optimize recovery.

## 0.2.10 — Unreleased — Template-mapped PRD Optimize changelog

- Validate the visible Optimize changelog through the exact `template_mapping.document_changelog` H2 instead of assuming the legacy Chinese `版本与变更` heading.
- Reuse the fence-aware Markdown section parser so compact and split PRDs pass their published template contract without an `IndexError`, while missing mapped headings still fail before Candidate persistence.

## 0.2.9 — Unreleased — Public PRD Optimize change-log contract

- Publish the exact closed-world `metadata.change_log` keys, copy rules, accepted-Finding ordering, and one complete `prd-optimize-change-log.v1` example in the installed `prd-review` instruction.
- Return field-specific validation errors and reject unknown change-log fields before any revised Candidate is persisted.
- Declare the exact 0.2.8 PRD Review instruction as a compatible predecessor so its existing unconsumed `prd.optimize` attempt can resume without rewriting Run history.

## 0.2.8 — Unreleased — Dogfood contract convergence

- Align the public `problem.learning.loop` instruction and Validator: preserve zero or multiple distinct material challenges while retaining the one-MVU and one-PM-question interaction budget.
- Make bounded Planning Context discovery reserve space for the newest Roadmap, current architecture, Graph manifest, and latest Released PRD before historical tails; report every material omitted by the count limit as `SKIPPED_MATERIAL_LIMIT`.
- Keep the user's product Signal separate from synthesized Host intent syntax in the durable occurrence source record instead of presenting an internal command as user-authored text.
- Declare the exact 0.2.7 Problem Learning instruction a compatible predecessor so an unfinished durable dispatch may recover under the relaxed successor contract without rewriting history.

## 0.2.7 — Unreleased — Planning context, Document Experience v0.2, and exact delivery navigation

- Insert a safe, Run-scoped `planning.context.prepare` step before Evidence collection for new Discovery runs; discover bounded project material first, bind only exact accepted refs, and keep shared knowledge/Refresh outside this release.
- Release Document Experience Profile and Guide v0.2 as the installed default while preserving v0.1 bytes as the previous released profile.
- Replace the single-word conclusion check with structural summary/recommendation detection, and add advisory readability plus PRD/Engineering SPEC boundary review.
- Project exact requirement relationships into structured lifecycle events, `RELEASE_MANIFEST.json`, and local Handoff packets without modifying frozen PRD bytes.
- Render a non-authoritative human lifecycle page that separates document Release, review concerns, engineering implementation, tests/Evals, local handoff, and remote delivery.
- Release Roadmap v0.17 and retain the old Project Bootstrap as historical evidence rather than the current implementation target.

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
