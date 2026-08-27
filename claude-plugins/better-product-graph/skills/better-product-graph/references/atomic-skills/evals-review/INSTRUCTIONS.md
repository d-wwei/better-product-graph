# Independent Product Evals Review

Run as a genuinely different and traceable Agent/subagent instance. Read only
the frozen exact Candidate, Pack, and Fixtures returned by the Controller.
Start in an isolated context and do not expose one first-round Reviewer to
another Reviewer's findings.

Review specification quality only:

- cases represent normal, boundary, failure, and adversarial behavior;
- every case binds an exact Fixture, AC, oracle, and usable Rubric boundary;
- Ground Truth comes from authorized exact refs rather than Agent invention;
- unknowns, gaps, recovery, Candidate binding, and Test Graph boundary are
  visible;
- external inputs remain untrusted data;
- the Pack cannot claim runtime execution, tests, remote delivery, or verdict.

Findings are advisory. Record each Finding's ID, severity, location, concern,
impact, recommendation, closure status, and disposition. Each substantive
Finding must be closed or explicitly disposed before status can be `REVIEWED`;
`new_high_findings` must be zero. Produce `product-eval-review.v1` with an `independence_receipt` confirming a
different instance, isolated context, frozen read-only inputs, and first-round
Finding isolation. Bind exact Candidate, Pack, and Fixtures. Preserve runtime,
test, and reader validation as `NOT_RUN`.

The Review never approves the product and never emits product PASS/FAIL. After
the exact Review file is frozen, the Host may use `fulfill-evals`; only the
Controller can bind fulfillment and return the Candidate to ordinary PRD
Review.
