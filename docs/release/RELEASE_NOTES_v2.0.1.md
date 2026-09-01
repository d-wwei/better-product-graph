# Better Product Graph 2.0.1 — Review, Ready, and Handoff Integrity Hotfix

`2.0.1` repairs integrity gaps in the BPG 2.0 single-PRD Developer Alpha without adding a new product capability or a second governance system.

## What changed

- Rebind all nine Stage 4 dispositions after a Planning Record change during PRD Authoring. Product changes that affect an earlier stage still return to that stage.
- Keep live Candidate, Review, Ready, Handoff, Product Evals, and engineering status in Controller projections and receipts instead of writing mutable workflow state into durable product truth.
- Preserve every historical Review and Finding. The Lead Agent records durable Finding dispositions in the Planning Record; a changed Candidate receives a new independent Review with difference review and whole-product regression.
- Keep `COMMIT_NOW` authorization judgment with the Host Agent. Optional message refs remain opaque traceability and do not become a Controller authorization receipt, signature, schema, state, or Gate.
- Require formal semantic Reviewers to start without inherited parent conversation and read only the exact dispatched immutable bases. This is a Host execution rule, not a machine-proven isolation claim.
- Keep the exact PRD Candidate source set to `PRD.md` with Mermaid source. SVG and optional HTML are generated only during Handoff after Ready; they are presentation artifacts, not Candidate or Review evidence.
- Make Handoff materialization and completion atomic and recoverable. Failed rendering does not publish a partial final target, and unrelated pre-existing user content is preserved.
- Add an Agent-owned Solution Intelligence check before Decision freeze, scaled to risk, novelty, reuse, and maintenance cost, without a fixed source quota or new Gate.

## Correction to v2.0.0 Product Evals wording

The v2.0.0 release notes incorrectly described BPG 2.0 as performing Product Evals applicability and blocking Ready when the result was `REQUIRED` but the Generator was unavailable.

That statement did not match the implemented BPG 2.0 method boundary. BPG 2.0 does **not**:

- perform Product Evals applicability assessment;
- generate or accept an Eval Pack for the Product Run;
- run independent Eval Spec Review; or
- use any of those future responsibilities to block Ready or Local Handoff.

Those capabilities enter through a later versioned 2.2 method/runtime. In `2.0.1`, Product Evals execution and product-effect validation remain `NOT_RUN` unless separately observed outside the Product Run. Ordinary acceptance and Review evidence must not be relabeled as Product Evals execution.

## Versioned resources

- Product planning method: `BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md`; v0.2 bytes remain preserved.
- Alpha PRD template/output contract: `2.0-alpha.3`; prior Alpha resource bytes remain preserved.
- Writing Reviewer contracts: `v3.1.1` for the Alpha path and `v3.2.1` for current general dispatch; prior v3.1/v3.2 resources and historical exact refs remain available.

## Verification and identity

The final exact development source commit, public snapshot verification, dual-Host artifact hashes, Core fingerprint, ZIP checksums, and installed-identity results are recorded in `RELEASE_SOURCE.json` and the published `SHA256SUMS`. A prepared but uncommitted snapshot, a local ZIP, or a successful source test alone is not the formal Release identity.

## Boundaries

- Multi-PRD planning remains a later architecture iteration.
- Existing legacy Runs are not imported, migrated, aliased, or resumed.
- Reviewers remain `ADVISORY_ONLY`; the product Owner retains decision responsibility.
- External delivery, engineering receipt, implementation tests, Product Evals execution, product-effect validation, and human-reader study remain `NOT_RUN` unless separately evidenced.
- The public snapshot excludes internal Template Packs, local Runs, project memory, audits, artifacts, construction plans, version-arena material, user drafts, caches, secrets, and developer-machine paths.
