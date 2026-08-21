# Product Golden Suite v0.2

Status: `DRAFT / LOCAL RC`

Evidence status: `CONTRACT_FIXTURE_ONLY`; Agent runtime and product judgment are `NOT_RUN` until a real Host Agent harness supplies isolated case runs and evaluator evidence.

This suite installs G01, G03, and G04 as five-file case packages. `run_contract.py` validates fixture shape and can emit an Agent-readable workspace containing only `input.yaml`, `knowledge-snapshot.yaml`, and `pm-response-bank.yaml`. It never gives `expected-envelope.yaml` or `rubric.yaml` to the tested Agent.

The runner does not infer a product answer. A contract PASS proves only that the migration fixtures and isolation boundary are mechanically usable. It cannot produce Product Golden PASS, score Agent reasoning, or replace a real Agent/evaluator harness.

All `.yaml` fixtures use the JSON-compatible subset of YAML so the contract runner remains standard-library-only and offline.

Next action: execute the isolated Agent inputs through a real Codex Host Agent harness, then let an evaluator with exclusive access to each outcome envelope and rubric judge the final decision/end state.
