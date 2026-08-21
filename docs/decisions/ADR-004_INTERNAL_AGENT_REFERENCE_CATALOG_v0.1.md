# ADR-004: Internal Agent Reference Catalog v0.1

- Status: Accepted
- Date: 2026-08-20
- Scope: Better Product Graph local Plugin candidate

## Decision

Better Question, the Cognitive Router, twenty cognitive bases, and the Product Goal Fidelity reviewer contract ship as versioned JSON references inside the one public Skill. They are not public Skills, Graph Nodes, gates, checklists, or programmatic product-decision rules.

The Host dispatches exact paths and hashes. The Agent chooses which reasoning references it actually uses and records those IDs and its rationale. Python only validates that declared IDs were present in the exact dispatch; it does not select lenses, formulate questions, judge evidence, decide product direction, author PRDs, or perform Review reasoning.

Review attempts bind one exact Candidate, exact commitment inputs, and the installed Goal Fidelity profile, rubric, and packet contract. Reviewer authority remains `ADVISORY_ONLY`.

## Provenance and installation boundary

The checked-in extraction manifest records a logical source root, relative source paths, and hashes for all twenty cognitive bases. A source-workspace test may rehash the locally available upstream collection. Installed copies do not depend on an author-machine absolute path: they validate the checked-in extraction manifest, catalog membership, selectors, and every packaged reference hash.

The catalog is intentionally replaceable. A future version may change reference content only by producing new versioned files, provenance, aggregate hashes, tests, and changelog evidence; it must not silently migrate an active Run.
