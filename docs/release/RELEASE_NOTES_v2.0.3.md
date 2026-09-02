# Better Product Graph 2.0.3 — Release Identity Metadata Correction

`v2.0.3` is the current formal release identity and supersedes `v2.0.2`. It corrects a public release-record error and makes no runtime semantic change.

The existing `v2.0.2` Tag, Release, and assets remain immutable and must not be moved, deleted, or rebuilt. Its Codex and Claude ZIPs, embedded `build-manifest.json` files, and runtime content are correct; only the public release record mapped two Host-specific fingerprints incorrectly.

## What was wrong in v2.0.2

The public `RELEASE_SOURCE.json` incorrectly copied the shared `core_tree_fingerprint` into both Host-specific `execution_contract_fingerprint` fields.

The frozen `v2.0.2` identities are:

| Identity | Correct value |
|---|---|
| Shared `core_tree_fingerprint` | `sha256:a97027f2c614f9f97cef7640a3b3a4d8284e8f10bd0fc486f666712a562b14ec` |
| Codex `execution_contract_fingerprint` | `sha256:8bab78b78923e75f659e1a7a3020f573379a6466dc24693ec1a9239d95e4d46d` |
| Claude `execution_contract_fingerprint` | `sha256:a58a6ef878f75051addbd923da06c73ae8ffdfe98b83ad8790fca63087964abc` |

The shared Core value proves both Host artifacts contain the same Product Graph Core. Each execution-contract fingerprint additionally binds its Host Adapter and Host manifest, so the Codex and Claude values are intentionally different.

## Correction in v2.0.3

- Advance the Plugin and both Host manifest versions to `2.0.3`; no `v2.0.2` asset is relabeled.
- Record each Host's execution-contract fingerprint from that Host's own built manifest while recording the shared Core fingerprint separately.
- Add a packaging regression assertion that the two Host artifacts share one Core fingerprint but have distinct execution-contract fingerprints.
- Preserve the BPG Product Planning Method v0.4, Agent-first runtime boundary, templates, schemas, and the Issue #1–#7 product conclusions unchanged.

## Evidence boundary

- `v2.0.2` full source verification remains the historical `894/894 PASS` result.
- The exact `v2.0.3` development commit, filtered public snapshot, annotated Tag, Release assets, checksums, Host fingerprints, remote readback, and fresh-download verification are bound by the `v2.0.3` release record; they do not rewrite `v2.0.2` evidence.
- Issue #7 comparable Product Golden Run: `NOT_RUN`.
- Product Evals execution, external delivery, engineering receipt/tests, product-effect validation, and human-reader study remain `NOT_RUN` unless separately observed.

Installation identity verification does not substitute for Product Evals, engineering tests, or product-effect validation.
