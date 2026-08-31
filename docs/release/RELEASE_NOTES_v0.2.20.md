# Better Product Graph 0.2.20 — Developer Alpha

`0.2.20` adds an explicitly opt-in BPG 2.0 internal Alpha for one complete single-PRD product-planning path. The existing 0.x path remains the default.

## What is new

- Start a fresh, isolated BPG 2.0 Run from a Signal and Agent-selected product-planning route.
- Maintain one Product Planning Record across UNDERSTAND, DIAGNOSE & VALUE, DISCOVER SOLUTIONS & DECIDE, PLAN THE PRODUCT SYSTEM, and single-PRD delivery.
- Freeze and independently Review exact Problem, Decision, and PRD Candidates.
- Support six distinct outcomes: `STOP`, `WAIT`, `RESEARCH`, `EXPERIMENT`, `COMMIT_NOW`, and `FUTURE_ROADMAP`.
- Keep product `WAIT` separate from runtime `PAUSE / RESUME`.
- Allow Agent `COMMIT_NOW` only under exact local-planning preauthorization and a passing Decision Review; the other five outcomes remain Owner choices.
- Produce one formal or experimental PRD, with Markdown plus assets as editing truth and a self-contained HTML reading view.
- Preserve truthful Product Evals applicability and non-execution states; missing REQUIRED material blocks Ready.
- Create only a Local Handoff, then record a non-blocking planning retrospective.

## Verification

- Release-candidate development tree: `792/792 PASS`.
- Alpha branch before merge: `791/791 PASS`.
- Merged `main` before release metadata: `791/791 PASS`.
- Real Codex Host Alpha Run `bpg2-run-alpha-dogfood-20260829`: `LOCAL_HANDOFF_COMPLETE`.
- Independent Problem, Decision, and PRD Reviews were exercised; the final PRD v3 passed difference review and whole-product regression.
- Deterministic Codex and Claude marketplace packages, isolated install checks, installed identity, and public-snapshot CI are release gates.

## Boundaries

- BPG 2.0 Alpha runs only when explicitly requested with `BPG 2.0 Alpha` or `$better-product-graph alpha`.
- It does not import, migrate, alias, or resume an old BPG Run.
- It does not implement multi-PRD planning, the full Evals Generator, product-form Profiles, professional Reviewer packs, external Connectors, or remote delivery.
- Local Handoff is not external delivery, engineering receipt, implementation, test completion, or product-effect proof.
- Human owner testing, external delivery, implementation, and product-effect validation remain `NOT_RUN` until separately performed.

---

`0.2.20` introduces an explicit BPG 2.0 single-PRD internal Alpha while keeping the 0.x workflow as the default. It binds one planning record, immutable Candidates, independent Reviews, six decision routes, one formal or experimental PRD, truthful Product Evals status, unique Ready, and Local Handoff. It never migrates legacy Runs and makes no external-delivery, implementation, testing, or product-effect claim.
