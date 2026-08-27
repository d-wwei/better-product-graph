#!/usr/bin/env python3
"""Read-only multi-root release aggregation for PRD Readability Suite v0.8.

The two phase scorers remain frozen and terminal.  This tool rederives their
existing terminal scores from two explicitly bound central roots, qualifies a
Work Order by ``root identity + relative path + manifest-bound hash``, and
applies the frozen cross-phase freshness contract to every other identity.
It never invokes phase scoring and never rewrites an execution manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import stat
import sys
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE_ROOT = REPO_ROOT / "evals" / "prd-readability-v0.8"
SUITE_ID = "better-product-graph-prd-readability-v0.8"
PHASES = ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT")
EXPECTED_PHASE_SCORE = {"passed": 27, "total": 27, "required": 27}


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _regular_single_link_bytes(path: Path, label: str) -> tuple[bytes, os.stat_result]:
    if path.is_symlink():
        raise ValueError(f"{label} must be a regular non-symlink file")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label} must be a regular non-symlink file")
        if metadata.st_nlink != 1:
            raise ValueError(f"{label} must be a single-link file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), metadata
    finally:
        os.close(descriptor)


def _root_file(root: Path, relative: str, label: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        raise ValueError(f"{label} must be a safe root-relative path")
    candidate = root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError(f"{label} must not traverse a symlink")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes the exact central project root") from error
    return resolved


def _read_exact_root_ref(
    root: Path, ref: Any, label: str
) -> tuple[bytes, Path, os.stat_result]:
    if (
        not isinstance(ref, dict)
        or set(ref) != {"path", "hash", "version"}
        or not isinstance(ref.get("path"), str)
        or not isinstance(ref.get("hash"), str)
    ):
        raise ValueError(f"{label} must be one exact closed ref")
    path = _root_file(root, ref["path"], label)
    data, metadata = _regular_single_link_bytes(path, label)
    if _sha256(data) != ref["hash"]:
        raise ValueError(f"{label} hash differs from its manifest-bound hash")
    return data, path, metadata


def _root_identity(root: Path) -> dict[str, int | str]:
    metadata = root.stat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("central_project_root must be a directory")
    return {
        "path": str(root),
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
    }


def _aggregator_ref() -> dict[str, int | str]:
    path = Path(__file__).resolve(strict=True)
    data, _metadata = _regular_single_link_bytes(path, "release aggregator")
    try:
        relative = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        relative = str(path)
    return {"path": relative, "hash": _sha256(data), "version": 1}


def _load_suite_namespaces(
    suite_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    suite = Path(suite_root).resolve(strict=True)
    return (
        runpy.run_path(str(suite / "evaluator" / "score_results.py")),
        runpy.run_path(str(suite / "run_contract.py")),
    )


def _phase_context(
    *,
    phase: str,
    binding: dict[str, Any],
    scorer: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    if set(binding) != {"central_project_root", "skill_root"}:
        raise ValueError(f"{phase} requires exact central_project_root and skill_root")
    root = Path(binding["central_project_root"]).resolve(strict=True)
    skill_root = Path(binding["skill_root"]).resolve(strict=True)
    if not skill_root.is_dir():
        raise ValueError(f"{phase} skill_root must be a directory")
    identity = _root_identity(root)

    # This is the only score operation: validate and deterministically rederive
    # an already-persisted terminal.  Never call score_phase here.
    score = scorer["_load_terminal_score"](root, skill_root, phase)
    if score is None:
        raise ValueError(f"{phase} terminal phase score is required")
    bundle = scorer["_phase_score_bundle"](root, phase)
    if bundle is None or len(bundle) != 5:
        raise ValueError(f"{phase} authoritative terminal bundle is required")
    stored, receipt, controller_invocation, _transaction, _ledger = bundle
    if stored != score:
        raise ValueError(f"{phase} terminal score read-back differs from rederivation")

    manifest_ref = receipt.get("execution_manifest_ref")
    manifest_bytes, manifest_path, _manifest_stat = _read_exact_root_ref(
        root, manifest_ref, f"{phase}.execution_manifest_ref"
    )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{phase} execution manifest is invalid JSON") from error
    manifest_issues = contract["execution_manifest_shape_issues"](manifest)
    if manifest_issues:
        raise ValueError(
            f"{phase} execution manifest is invalid: " + ",".join(manifest_issues)
        )
    if manifest.get("phase") != phase:
        raise ValueError(f"{phase} execution manifest phase differs")
    if manifest.get("central_project_root") != identity:
        raise ValueError(f"{phase} central_project_root identity differs")

    invocation = controller_invocation.get("invocation")
    snapshot = invocation.get("evidence_snapshot") if isinstance(invocation, dict) else None
    result_attempts = snapshot.get("attempts") if isinstance(snapshot, dict) else None
    if not isinstance(result_attempts, list) or len(result_attempts) != 27:
        raise ValueError(f"{phase} terminal evidence snapshot must bind 27 results")
    result_hashes: list[str] = []
    for attempt in result_attempts:
        ref = attempt.get("result_ref") if isinstance(attempt, dict) else None
        if (
            not isinstance(ref, dict)
            or set(ref) != {"path", "hash", "version"}
            or not isinstance(ref.get("hash"), str)
        ):
            raise ValueError(f"{phase} terminal result identity is invalid")
        result_hashes.append(ref["hash"])
    if len(result_hashes) != len(set(result_hashes)):
        raise ValueError(f"{phase} reuses a terminal result hash internally")

    return {
        "phase": phase,
        "root": root,
        "root_identity": identity,
        "skill_root": skill_root,
        "score": score,
        "manifest": manifest,
        "manifest_ref": {
            "path": manifest_ref["path"],
            "hash": _sha256(manifest_bytes),
            "version": manifest_ref["version"],
        },
        "manifest_absolute_path": str(manifest_path),
        "result_hashes": result_hashes,
    }


def _qualify_work_orders(context: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    qualified = deepcopy(context["manifest"])
    verifications: list[dict[str, Any]] = []
    for entry in qualified["entries"]:
        ref = entry["work_order_ref"]
        data, absolute, metadata = _read_exact_root_ref(
            context["root"], ref, f"{context['phase']}.work_order_ref[{entry['ordinal']}]"
        )
        identity_object = {
            "root_identity": context["root_identity"],
            "relative_path": ref["path"],
            "manifest_bound_hash": ref["hash"],
        }
        identity_hash = _sha256(_canonical_bytes(identity_object))
        verifications.append(
            {
                "phase": context["phase"],
                "ordinal": entry["ordinal"],
                **identity_object,
                "identity_hash": identity_hash,
                "absolute_path": str(absolute),
                "actual_hash": _sha256(data),
                "regular": True,
                "non_symlink": True,
                "link_count": metadata.st_nlink,
            }
        )
        entry["work_order_ref"]["path"] = (
            "root-qualified-work-orders/"
            + identity_hash.removeprefix("sha256:")
            + ".json"
        )
    return qualified, verifications


def _values(manifest: dict[str, Any], field: str) -> set[str]:
    return {entry[field] for entry in manifest["entries"]}


def _nested_values(manifest: dict[str, Any], field: str, member: str) -> set[str]:
    return {entry[field][member] for entry in manifest["entries"]}


def _identity_overlap_counts(
    rc: dict[str, Any],
    final: dict[str, Any],
    work_orders: dict[str, set[str]],
) -> dict[str, int]:
    rc_manifest = rc["manifest"]
    final_manifest = final["manifest"]
    return {
        "run_id": len(_values(rc_manifest, "run_id") & _values(final_manifest, "run_id")),
        "attempt_id": len(_values(rc_manifest, "attempt_id") & _values(final_manifest, "attempt_id")),
        "reviewer_id": len(
            _nested_values(rc_manifest, "reviewer_execution_ref", "id")
            & _nested_values(final_manifest, "reviewer_execution_ref", "id")
        ),
        "author_id": len(
            _nested_values(rc_manifest, "author_execution_ref", "id")
            & _nested_values(final_manifest, "author_execution_ref", "id")
        ),
        "output_target": len(
            _values(rc_manifest, "output_target")
            & _values(final_manifest, "output_target")
        ),
        "checkpoint_path": len(
            _nested_values(rc_manifest, "preregistration_checkpoint_ref", "path")
            & _nested_values(final_manifest, "preregistration_checkpoint_ref", "path")
        ),
        "state_path": len(
            _nested_values(rc_manifest, "state_ref", "path")
            & _nested_values(final_manifest, "state_ref", "path")
        ),
        "result_hash": len(set(rc["result_hashes"]) & set(final["result_hashes"])),
        "work_order_identity": len(
            work_orders[PHASES[0]] & work_orders[PHASES[1]]
        ),
    }


def aggregate_release_phases(
    phase_bindings: dict[str, dict[str, Any]],
    *,
    suite_root: Path = DEFAULT_SUITE_ROOT,
    _scorer: dict[str, Any] | None = None,
    _contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rederive and aggregate two terminal phase scores from exact roots."""

    if not isinstance(phase_bindings, dict) or set(phase_bindings) != set(PHASES):
        raise ValueError("exact bindings for both mandatory phases are required")
    if _scorer is None or _contract is None:
        loaded_scorer, loaded_contract = _load_suite_namespaces(suite_root)
        scorer = loaded_scorer if _scorer is None else _scorer
        contract = loaded_contract if _contract is None else _contract
    else:
        scorer, contract = _scorer, _contract

    contexts = {
        phase: _phase_context(
            phase=phase,
            binding=phase_bindings[phase],
            scorer=scorer,
            contract=contract,
        )
        for phase in PHASES
    }
    qualified: dict[str, dict[str, Any]] = {}
    work_order_evidence: list[dict[str, Any]] = []
    work_order_ids: dict[str, set[str]] = {}
    for phase in PHASES:
        qualified[phase], evidence = _qualify_work_orders(contexts[phase])
        work_order_evidence.extend(evidence)
        work_order_ids[phase] = {item["identity_hash"] for item in evidence}

    overlap_counts = _identity_overlap_counts(
        contexts[PHASES[0]], contexts[PHASES[1]], work_order_ids
    )
    issues = contract["cross_phase_freshness_issues"](
        qualified[PHASES[0]], qualified[PHASES[1]]
    )
    if overlap_counts["result_hash"]:
        issues.append("cross_phase_result_hash_reuse")
    if overlap_counts["work_order_identity"]:
        issues.append("cross_phase_work_order_identity_reuse")
    issues = sorted(set(issues))

    phase_scores = [contexts[phase]["score"] for phase in PHASES]
    passed = not issues and all(
        score.get("status") == "PASS"
        and score.get("score") == EXPECTED_PHASE_SCORE
        for score in phase_scores
    )
    aggregator_ref = _aggregator_ref()
    release_score = {
        "schema_version": "prd-readability-v0.8-multi-root-release-score.v1",
        "suite_id": SUITE_ID,
        "status": "PASS" if passed else "FAIL",
        "cross_phase_policy": "BOTH_PHASES_PASS_NO_LATER_PHASE_RESCUE",
        "issues": issues,
        "phases": phase_scores,
        "aggregator_ref": aggregator_ref,
        "human_reader_validation": "NOT_RUN",
    }
    evidence = {
        "schema_version": "prd-readability-v0.8-multi-root-release-evidence.v1",
        "suite_id": SUITE_ID,
        "status": release_score["status"],
        "aggregation_mode": "READ_ONLY_REDERIVE_EXISTING_TERMINALS_ACROSS_EXACT_ROOTS",
        "phase_score_invocations_added": 0,
        "aggregator_ref": aggregator_ref,
        "phase_bindings": {
            phase: {
                "central_project_root": contexts[phase]["root_identity"],
                "skill_root": str(contexts[phase]["skill_root"]),
                "execution_manifest_ref": contexts[phase]["manifest_ref"],
                "execution_manifest_absolute_path": contexts[phase]["manifest_absolute_path"],
            }
            for phase in PHASES
        },
        "work_order_identity_contract": "ROOT_IDENTITY_PLUS_RELATIVE_PATH_PLUS_MANIFEST_BOUND_HASH",
        "work_order_identities": work_order_evidence,
        "identity_overlap_counts": overlap_counts,
        "cross_phase_issues": issues,
        "boundaries": {
            "phase_scores_created_or_updated": False,
            "execution_manifests_modified": False,
            "semantic_reviewers_rerun": False,
            "human_reader_validation": "NOT_RUN",
        },
    }
    return {"release_score": release_score, "evidence": evidence}


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ValueError("aggregation output must be a regular single-link file")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rc-project-root", required=True, type=Path)
    parser.add_argument("--rc-skill-root", required=True, type=Path)
    parser.add_argument("--final-project-root", required=True, type=Path)
    parser.add_argument("--final-skill-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    bindings = {
        PHASES[0]: {
            "central_project_root": args.rc_project_root,
            "skill_root": args.rc_skill_root,
        },
        PHASES[1]: {
            "central_project_root": args.final_project_root,
            "skill_root": args.final_skill_root,
        },
    }
    try:
        result = aggregate_release_phases(bindings)
        output_dir = args.output_dir.resolve()
        score_path = output_dir / "release-aggregation.json"
        evidence_path = output_dir / "release-aggregation-evidence.json"
        score_bytes = _canonical_bytes(result["release_score"])
        evidence = deepcopy(result["evidence"])
        evidence["release_score_ref"] = {
            "path": str(score_path),
            "hash": _sha256(score_bytes),
            "version": 1,
        }
        evidence_bytes = _canonical_bytes(evidence)
        _write_once(score_path, score_bytes)
        _write_once(evidence_path, evidence_bytes)
        summary = {
            "status": result["release_score"]["status"],
            "release_score_ref": evidence["release_score_ref"],
            "evidence_ref": {
                "path": str(evidence_path),
                "hash": _sha256(evidence_bytes),
                "version": 1,
            },
            "aggregator_ref": result["evidence"]["aggregator_ref"],
            "phase_score_invocations_added": 0,
        }
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "FAIL", "issues": [str(error)]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
