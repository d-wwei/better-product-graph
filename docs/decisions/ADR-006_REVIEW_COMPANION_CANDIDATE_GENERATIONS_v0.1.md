# ADR-006: Review Companion Candidate Generations v0.1

- Status: Accepted for local candidate
- Date: 2026-08-20
- Scope: Controller-owned `review.finalize` and exact Ready inputs
- Supersedes: none; complements ADR-005

## Decision

`prd.generate` archives the Agent-authored PRD with a same-version `NOT_RUN` advisory Review companion. A Host cannot submit a `FINALIZED` companion or a deterministic `review.finalize` result.

After one exact `review.parallel` result is persisted and consumed, the Agent authors a lossless `review.aggregate` plus explicit Finding dispositions. The Controller verifies that aggregate attempt, roles and Findings exactly equal the persisted Review result, verifies every Finding has one disposition, and only then derives the companion view.

Finalization is a copy-on-write Candidate generation transaction:

1. Stage the current archived Candidate tree and replace only the companion with the Controller-derived `FINALIZED` view.
2. Persist the Controller Gate result and a write-ahead transaction binding old/new tree hashes, Run, attempt and state version.
3. Commit state/event authority, atomically preserve the prior tree under the Run's `candidate-generations/generation-N/`, and publish the staged tree as generation `N+1`.
4. Recovery reconciles the same journal idempotently. A changed, duplicate or escaping tree fails closed.

The PRD document bytes, PRD version and stem do not change for a no-content-change Review attempt. The current Candidate tree/review hashes and generation do change. Released trees are never mutated. If Agent-authored PRD content changes, it must use the existing PRD optimize/version policy rather than this mechanism.

## Exact Ready binding

The finalized companion binds the exact aggregate and disposition refs. Review Finalize receipts revalidate the companion, required advisory roles, Finding/disposition equality and current Candidate generation. Mechanical Contract receipts enumerate and rehash every Decision and Evidence ref in Candidate metadata using indexed subject roles when more than one ref exists.

## Semantic authority boundary

The Controller does not invent Reviewer Findings, dispositions, product meaning or approval. It performs lossless equality checks, exact-ref/hash validation, state transitions, deterministic companion projection, persistence and recovery. Agent/Product judgment remains outside Python and authenticated Agent/Product Golden evidence remains `NOT_RUN` until separately executed.

## Rejected alternatives

- Mutate the archived tree in place without a generation/journal: loses crash recovery and prior evidence.
- Bump the PRD content version for companion-only finalization: falsely implies product-content change.
- Accept a Host-authored `FINALIZED` companion: recreates the forged Gate/receipt authority bypass.
- Store only the first Decision/Evidence ref in a receipt: permits unvalidated metadata inputs.
