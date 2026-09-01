# PRD Status Authority Eval v0.1

This two-case suite is a preregistered semantic check for R2. It asks an
independent Writing Reviewer to distinguish mutable Product Run status from a
durable product contract without keyword scanning.

- `mutable-run-status` should return a normal Writing Finding with stance
  `REVISE`, using an existing completion or maturity diagnosis.
- `durable-product-rule` is the negative control. It should not produce a
  status-authority Finding merely because it mentions Candidate or Product
  Evals.

The fixtures and expected envelope are contract evidence only. No independent
Agent has executed this suite in this change, so Agent Review is `NOT_RUN`.
String-presence tests do not count as Agent performance evidence. A future run
must use an isolated Reviewer over the exact Candidate and exact installed
Profile, Guide, instruction, Reviewer Contract, and Output Contract, then retain
the unedited result before scoring.
