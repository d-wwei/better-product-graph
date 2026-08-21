# Contributing to Better Product Graph

谢谢你愿意帮助 Better Product Graph。Thank you for helping improve Better Product Graph.

## Start with an Issue

For the Developer Alpha, please open the matching Issue form before proposing a behavior change:

- Bug: a reproducible failure, wrong Ready/Release, corrupted state, or broken recovery.
- Product feedback: workflow weight, poor questions, missing scenarios, confusing decisions, or PRD quality.
- Installation: Host version, command, operating system, checksum, and complete error output.

Please do not include customer data, credentials, private PRDs, or hidden model chain-of-thought.

## Pull requests

Small, focused pull requests are welcome after an Issue establishes the intended outcome.

1. Branch from `main`.
2. Keep one product or engineering concern per pull request.
3. Add a failing test before changing executable behavior.
4. Preserve the Agent/Controller boundary: Agents perform product judgment; deterministic code controls state, authority, validation, recovery, and release.
5. Do not weaken exact evidence, Ready, permission, or recovery checks to make a test pass.
6. Run:

```bash
python3 -m unittest discover -s tests -t . -v
python3 scripts/verify_audit_repairs.py
```

The public repository is a curated release repository. Maintainers may first port an accepted change into the development history, then publish the resulting release snapshot. This keeps release provenance auditable.

## Documentation

- Write Chinese-first when a document primarily serves product managers; keep machine IDs and enums exact.
- Explain why a node or rule exists, not only what it is called.
- Do not overwrite a frozen PRD, Roadmap, architecture document, or released artifact. Create a new version and update its changelog.
- Distinguish `PASS`, `FAIL`, `PARTIAL`, `NOT_RUN`, and `DOCUMENT-ONLY`.

## License

Unless you explicitly state otherwise, contributions submitted for inclusion are licensed under the project’s [Apache License 2.0](LICENSE).
