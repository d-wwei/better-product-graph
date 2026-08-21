# Better Product Graph Plugin Contract Suite v0.2

Status: `DRAFT / LOCAL RC`

This standard-library runner evaluates an unpacked, fresh installed copy. It checks installed identity, the one-public-Skill discovery surface, direct/indirect/follow-up/negative entry behavior, all eleven intent mappings, relative resources, and internal-entry bypass rejection.

`contract_status: PASS` is scoped to `FRESH_INSTALLED_COPY_CONTRACT`. The runner does not invoke the real Codex Host discovery/router, so `codex_host_runtime_status` remains `NOT_RUN`; it does not imply Product Golden PASS.

Run:

```text
python3 evals/plugin-contract/run_contract.py --plugin-root /absolute/path/to/unpacked/plugin
```

Next action: after deterministic packaging, extract one package into an isolated local install root and rerun this exact command against that copy.
