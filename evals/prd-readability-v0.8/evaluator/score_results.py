#!/usr/bin/env python3
"""Score the frozen v0.8 oracle from Controller-verified durable Runs only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


SUITE_ID = "better-product-graph-prd-readability-v0.8"
REGISTRATION_FIELDS = frozenset({"semantic_case_id", "repeat_index", "run_id"})
ASSESSMENT_FIELDS = (
    "verbosity_assessment",
    "checklist_assessment",
    "visual_assessment",
)
PHASES = ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT")
PHASE_SCORE_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "phase",
        "status",
        "selection_policy",
        "score",
        "produced_output_count",
        "installed_build_ref",
        "issues",
        "attempts",
        "agent_runtime_status",
        "human_reader_validation",
    }
)
PHASE_SCORE_ATTEMPT_FIELDS = frozenset(
    {
        "ordinal",
        "semantic_case_id",
        "repeat_index",
        "run_id",
        "attempt_id",
        "produced_output",
        "status",
        "issues",
    }
)


_DERIVATION_CAPABILITY = object()


class _ValidatedScoreDerivation:
    """Opaque in-process proof that the frozen scorer derived a phase report."""

    __slots__ = (
        "_capability",
        "_phase",
        "_skill_root",
        "_invocation_bytes",
        "_report_bytes",
    )

    def __init__(
        self,
        capability: object,
        phase: str,
        skill_root: Path,
        invocation: dict[str, Any],
        report: dict[str, Any],
    ) -> None:
        if capability is not _DERIVATION_CAPABILITY:
            raise ValueError("validated derivation capability is required")
        self._capability = capability
        self._phase = phase
        self._skill_root = Path(skill_root).resolve(strict=True)
        self._invocation_bytes = _canonical_bytes(invocation)
        self._report_bytes = _canonical_bytes(report)


def _load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"input must be a regular non-symlink file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_preregistration_issues() -> list[str]:
    """Use the suite's one canonical freeze validator before reading any Run."""

    contract = _contract()
    return list(contract["preregistration_issues"]())


def _expected() -> dict[str, Any]:
    value = _load_json(ROOT / "evaluator" / "expected.json")
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "suite_id", "custody", "cases"}
        or value.get("schema_version") != "prd-readability-expected-envelope.v0.8"
        or value.get("suite_id") != SUITE_ID
        or value.get("custody")
        != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE_OR_REVIEWER_PROJECTION"
        or not isinstance(value.get("cases"), dict)
    ):
        raise ValueError("frozen expected oracle is invalid")
    return value


def _preregistration() -> dict[str, Any]:
    value = _load_json(ROOT / "evaluator" / "preregistration.json")
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "prd-readability-preregistration.v0.8"
        or value.get("suite_id") != SUITE_ID
        or value.get("status") != "PREREGISTERED_BEFORE_RESULTS"
        or value.get("freeze_order_authority")
        != "PREREGISTRATION_GIT_COMMIT_PRECEDES_ALL_AGENT_OUTPUTS"
        or "registered_at" in value
    ):
        raise ValueError("frozen preregistration is invalid")
    return value


def _registration_issues(value: Any) -> list[str]:
    if not isinstance(value, dict) or set(value) != REGISTRATION_FIELDS:
        return ["closed_registration"]
    issues: list[str] = []
    for field in ("semantic_case_id", "run_id"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            issues.append(field)
    repeat = value.get("repeat_index")
    if isinstance(repeat, bool) or not isinstance(repeat, int):
        issues.append("repeat_index")
    return issues


def _semantic_issues(
    evidence: dict[str, Any], oracle: dict[str, Any]
) -> list[str]:
    """Apply only the preregistered oracle after Controller validation succeeds."""

    issues: list[str] = []
    result = evidence["result"]
    if evidence.get("suite_id") != SUITE_ID:
        issues.append("evidence_suite_id")
    if evidence.get("case_id") != oracle["agent_case_id"]:
        issues.append("evidence_case_id")
    if result.get("suite_id") != SUITE_ID:
        issues.append("result_suite_id")
    if result.get("case_id") != oracle["agent_case_id"]:
        issues.append("result_case_id")
    if result.get("attempt_id") != evidence.get("attempt_id"):
        issues.append("result_attempt_id")
    if result.get("reviewer_execution_ref") != evidence.get(
        "reviewer_execution_ref"
    ):
        issues.append("result_reviewer_execution_ref")
    if evidence.get("evaluation_only") is not True:
        issues.append("evidence_evaluation_only")
    if evidence.get("product_authority") != "NONE":
        issues.append("evidence_product_authority")

    finding_assessments: list[dict[str, Any]] = []
    for field in ASSESSMENT_FIELDS:
        assessment = result[field]
        if assessment["verdict"] == "FINDING":
            finding_assessments.append(assessment)

    required_result = oracle["required_result"]
    if result["result"] != required_result:
        issues.append("required_result")
    if required_result == "PASS":
        if result["primary_diagnosis"] is not None:
            issues.append("positive_primary_diagnosis")
        if result["primary_repair_technique"] is not None:
            issues.append("positive_primary_repair")
        if result["reader_outcome_failures"]:
            issues.append("positive_reader_outcome_failures")
        if finding_assessments:
            issues.append("positive_finding")
    else:
        pair = [
            result["primary_diagnosis"],
            result["primary_repair_technique"],
        ]
        if pair not in oracle["allowed_primary_pairs"]:
            issues.append("unregistered_primary_pair")
        if len(finding_assessments) != 1:
            issues.append("finding_assessment_count")
        elif pair[0] not in finding_assessments[0]["issue_types"]:
            issues.append("primary_diagnosis_missing_from_finding")
        if len(finding_assessments) == 1 and pair[1] not in finding_assessments[0][
            "repair_techniques"
        ]:
            issues.append("primary_repair_missing_from_finding")
    return issues


def _contract() -> dict[str, Any]:
    _verified_evaluator_path("evidence_reader_ref")
    path = _verified_evaluator_path("run_contract_ref")
    return runpy.run_path(str(path))


def _evidence_reader() -> dict[str, Any]:
    path = _verified_evaluator_path("evidence_reader_ref")
    return runpy.run_path(str(path))


def _verified_evaluator_path(field: str) -> Path:
    prereg = _preregistration()
    ref = prereg.get(field)
    if not isinstance(ref, dict) or set(ref) != {"path", "hash", "version"}:
        raise ValueError(f"{field} is not one frozen exact ref")
    relative = Path(ref.get("path", ""))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"{field} path is unsafe")
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{field} is missing or unsafe")
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != ref.get("hash"):
        raise ValueError(f"{field} hash differs from frozen preregistration")
    return path


def _manifest_path(project_root: Path, phase: str) -> Path:
    return (
        project_root.resolve()
        / ".better-product-graph"
        / "writing-evals"
        / "execution-manifests"
        / f"{phase}.json"
    )


def _raw_output_issues(
    *,
    project_root: Path,
    entry: dict[str, Any],
    evidence: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    """A produced raw output owns its slot even when Controller validation rejects it."""

    path = project_root.resolve() / entry["output_target"]
    if path.is_symlink() or not path.is_file():
        return False, ["agent_output_not_produced"]
    issues: list[str] = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raw = None
        issues.append("produced_raw_output_invalid_json")
    if evidence is None:
        issues.append("controller_rejected_produced_output")
        return True, issues
    if raw != evidence["result"]:
        corrected_path = path.with_name(path.name + ".corrected.json")
        record_path = path.with_name(path.name + ".mechanical-correction.json")
        if (
            corrected_path.is_symlink()
            or not corrected_path.is_file()
            or record_path.is_symlink()
            or not record_path.is_file()
        ):
            issues.append("raw_output_differs_without_mechanical_correction")
            return True, issues
        try:
            corrected_bytes = corrected_path.read_bytes()
            corrected = json.loads(corrected_bytes.decode("utf-8"))
            record = _load_json(record_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            issues.append("mechanical_correction_invalid")
            return True, issues
        if corrected != evidence["result"] or not isinstance(raw, dict):
            issues.append("mechanical_correction_not_submitted_result")
            return True, issues
        changed = sorted(field for field in raw if raw.get(field) != corrected.get(field))
        authority_values = {field: corrected[field] for field in changed if field in corrected}
        try:
            expected_record = _contract()["mechanical_correction_record"](
                path.read_bytes(), corrected_bytes, authority_values
            )
        except ValueError:
            issues.append("mechanical_correction_semantic_change")
        else:
            if record != expected_record:
                issues.append("mechanical_correction_record_mismatch")
    return True, issues


def _document_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _project_path(root: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} path is missing")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} path is unsafe")
    path = root / candidate
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"{label} path contains a symlink")
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes project root") from error
    return path


def _exact_project_ref(
    root: Path,
    path: Path,
    *,
    version: str | int = 1,
) -> dict[str, Any]:
    candidate = path
    try:
        relative_candidate = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("score evidence path escapes project root") from error
    cursor = root
    for part in relative_candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("score evidence path contains a symlink")
    resolved = candidate.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("score evidence path escapes project root") from error
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"score evidence must be a regular non-symlink file: {path}")
    return {
        "path": relative.as_posix(),
        "hash": _sha256(path.read_bytes()),
        "version": version,
    }


def _read_exact_project_ref(
    root: Path,
    ref: Any,
    label: str,
) -> bytes:
    if (
        not isinstance(ref, dict)
        or set(ref) != {"path", "hash", "version"}
        or not isinstance(ref.get("hash"), str)
        or not ref["hash"].startswith("sha256:")
        or isinstance(ref.get("version"), bool)
        or not isinstance(ref.get("version"), (str, int))
    ):
        raise ValueError(f"{label} is not one exact ref")
    path = _project_path(root, ref["path"], label)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-symlink file")
    content = path.read_bytes()
    if _sha256(content) != ref["hash"]:
        raise ValueError(f"{label} hash conflict")
    return content


def _phase_score_paths(project_root: Path, phase: str) -> tuple[Path, Path]:
    if phase not in PHASES:
        raise ValueError("phase is not preregistered")
    root = Path(project_root).resolve(strict=True)
    phase_root = (
        root
        / ".better-product-graph"
        / "writing-evals"
        / "phase-scores"
        / phase
    )
    return phase_root / "score.json", phase_root / "receipt.json"


def _phase_score_authority_paths(
    project_root: Path,
    phase: str,
) -> tuple[Path, Path]:
    score_path, _receipt_path = _phase_score_paths(project_root, phase)
    return (
        score_path.with_name("controller-invocation.json"),
        score_path.with_name("controller-transaction.json"),
    )


def _phase_score_ledger_path(project_root: Path, phase: str) -> Path:
    if phase not in PHASES:
        raise ValueError("phase is not preregistered")
    root = Path(project_root).resolve(strict=True)
    return (
        root
        / ".better-product-graph"
        / "writing-evals"
        / "score-ledger"
        / f"{phase}.json"
    )


def _suite_ref(path: Path, relative: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"frozen suite ref must be a regular non-symlink file: {relative}")
    if path.resolve() != (ROOT / relative).resolve():
        raise ValueError(f"frozen suite ref path differs: {relative}")
    return {"path": relative, "hash": _sha256(path.read_bytes()), "version": 1}


def _frozen_contract_refs() -> dict[str, dict[str, Any]]:
    prereg = _preregistration()
    refs = {
        "preregistration_ref": _suite_ref(
            ROOT / "evaluator" / "preregistration.json",
            "evaluator/preregistration.json",
        ),
        "expected_ref": prereg.get("expected_ref"),
        "run_contract_ref": prereg.get("run_contract_ref"),
        "scorer_ref": prereg.get("scorer_ref"),
        "evidence_reader_ref": prereg.get("evidence_reader_ref"),
    }
    for field in (
        "expected_ref",
        "run_contract_ref",
        "scorer_ref",
        "evidence_reader_ref",
    ):
        _verified_evaluator_path(field)
        if refs[field] != prereg[field]:
            raise ValueError(f"frozen contract ref differs: {field}")
    return refs


def _score_validation_digest(
    phase: str,
    invocation: dict[str, Any],
    frozen_contract_refs: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> str:
    return _sha256(
        _canonical_bytes(
            {
                "schema_version": "prd-readability-v0.8-score-validation.v1",
                "suite_id": SUITE_ID,
                "phase": phase,
                "invocation": invocation,
                "frozen_contract_refs": frozen_contract_refs,
                "score": report,
            }
        )
    )


def _ensure_score_directory(root: Path, phase: str) -> Path:
    if phase not in PHASES:
        raise ValueError("phase is not preregistered")
    current = root
    for component in (
        ".better-product-graph",
        "writing-evals",
        "phase-scores",
        phase,
    ):
        current = current / component
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise ValueError("terminal score directory must be a real directory")
        else:
            current.mkdir(mode=0o700)
    return current


def _write_exclusive(path: Path, content: bytes) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError(f"terminal score path already exists: {path.name}") from error
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise
    if path.is_symlink() or not path.is_file():
        raise ValueError("exclusive terminal score write did not create a regular file")
    if path.stat().st_nlink != 1:
        raise ValueError("exclusive terminal score write created a multiply-linked file")


def _ensure_score_ledger_directory(root: Path) -> Path:
    current = root
    for component in (
        ".better-product-graph",
        "writing-evals",
        "score-ledger",
    ):
        current = current / component
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise ValueError("terminal score ledger directory must be real")
        else:
            current.mkdir(mode=0o700)
    return current


def _validate_score_invocation(
    root: Path,
    phase: str,
    invocation: Any,
) -> None:
    expected_fields = {
        "schema_version",
        "suite_id",
        "phase",
        "execution_manifest_ref",
        "batch_validation_receipt_ref",
        "scorer_ref",
        "evidence_snapshot",
    }
    if (
        not isinstance(invocation, dict)
        or set(invocation) != expected_fields
        or invocation.get("schema_version")
        != "prd-readability-v0.8-score-invocation.v1"
        or invocation.get("suite_id") != SUITE_ID
        or invocation.get("phase") != phase
    ):
        raise ValueError("score invocation object identity is invalid")
    _read_exact_project_ref(
        root, invocation["execution_manifest_ref"], "execution_manifest_ref"
    )
    _read_exact_project_ref(
        root,
        invocation["batch_validation_receipt_ref"],
        "batch_validation_receipt_ref",
    )
    expected_manifest_path = (
        f".better-product-graph/writing-evals/execution-manifests/{phase}.json"
    )
    expected_batch_path = (
        ".better-product-graph/writing-evals/execution-manifests/"
        f"{phase}.batch-validation-receipt.json"
    )
    if invocation["execution_manifest_ref"].get("path") != expected_manifest_path:
        raise ValueError("execution_manifest_ref path differs from frozen contract")
    if invocation["batch_validation_receipt_ref"].get("path") != expected_batch_path:
        raise ValueError("batch_validation_receipt_ref path differs from frozen contract")
    manifest = json.loads(
        _read_exact_project_ref(
            root,
            invocation["execution_manifest_ref"],
            "execution_manifest_ref",
        ).decode("utf-8")
    )
    manifest_entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if (
        not isinstance(manifest, dict)
        or manifest.get("suite_id") != SUITE_ID
        or manifest.get("phase") != phase
        or not isinstance(manifest_entries, list)
        or len(manifest_entries) != 27
    ):
        raise ValueError("execution manifest identity is invalid for score invocation")
    batch_receipt = json.loads(
        _read_exact_project_ref(
            root,
            invocation["batch_validation_receipt_ref"],
            "batch_validation_receipt_ref",
        ).decode("utf-8")
    )
    if (
        not isinstance(batch_receipt, dict)
        or batch_receipt.get("suite_id") != SUITE_ID
        or batch_receipt.get("phase") != phase
        or batch_receipt.get("manifest_ref")
        != invocation["execution_manifest_ref"]
    ):
        raise ValueError("batch-validation receipt differs from execution manifest")
    preregistered_scorer_ref = _preregistration().get("scorer_ref")
    if invocation.get("scorer_ref") != preregistered_scorer_ref:
        raise ValueError("score invocation scorer_ref differs from preregistration")
    _verified_evaluator_path("scorer_ref")
    snapshot = invocation.get("evidence_snapshot")
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != {"schema_version", "suite_id", "phase", "attempts"}
        or snapshot.get("schema_version")
        != "prd-readability-v0.8-score-evidence-snapshot.v1"
        or snapshot.get("suite_id") != SUITE_ID
        or snapshot.get("phase") != phase
        or not isinstance(snapshot.get("attempts"), list)
        or len(snapshot["attempts"]) != 27
    ):
        raise ValueError("score evidence snapshot is invalid")
    seen_runs: set[str] = set()
    seen_attempts: set[str] = set()
    seen_result_paths: set[str] = set()
    for ordinal, item in enumerate(snapshot["attempts"], 1):
        if (
            not isinstance(item, dict)
            or set(item) != {"ordinal", "run_id", "attempt_id", "result_ref"}
            or item.get("ordinal") != ordinal
            or not isinstance(item.get("run_id"), str)
            or not item["run_id"]
            or not isinstance(item.get("attempt_id"), str)
            or not item["attempt_id"]
        ):
            raise ValueError(f"score evidence attempt {ordinal} is invalid")
        if item["run_id"] in seen_runs or item["attempt_id"] in seen_attempts:
            raise ValueError("score evidence contains duplicate Run or attempt")
        manifest_entry = manifest_entries[ordinal - 1]
        if (
            not isinstance(manifest_entry, dict)
            or manifest_entry.get("ordinal") != ordinal
            or manifest_entry.get("run_id") != item["run_id"]
            or manifest_entry.get("attempt_id") != item["attempt_id"]
        ):
            raise ValueError("score evidence differs from execution manifest")
        seen_runs.add(item["run_id"])
        seen_attempts.add(item["attempt_id"])
        result_path = item["result_ref"].get("path") if isinstance(item.get("result_ref"), dict) else None
        if result_path in seen_result_paths:
            raise ValueError("score evidence contains duplicate result_ref path")
        seen_result_paths.add(result_path)
        _read_exact_project_ref(root, item["result_ref"], f"result_ref:{ordinal}")


def _prepare_score_invocation(project_root: Path, phase: str) -> dict[str, Any]:
    """Bind the complete first-score evidence set before semantic scoring."""

    root = Path(project_root).resolve(strict=True)
    prereg = _preregistration()
    if phase not in prereg["mandatory_phases"]:
        raise ValueError("phase is not preregistered")
    manifest_path = _manifest_path(root, phase)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("scoring precondition failed: exact execution manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("scoring precondition failed: execution manifest is invalid") from error
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or len(entries) != 27:
        raise ValueError("scoring precondition failed: execution manifest must bind 27 entries")
    batch_path = manifest_path.with_name(f"{phase}.batch-validation-receipt.json")
    if batch_path.is_symlink() or not batch_path.is_file():
        raise ValueError("scoring precondition failed: batch-validation receipt is missing")
    attempts: list[dict[str, Any]] = []
    for ordinal, entry in enumerate(entries, 1):
        if (
            not isinstance(entry, dict)
            or entry.get("ordinal") != ordinal
            or not isinstance(entry.get("run_id"), str)
            or not isinstance(entry.get("attempt_id"), str)
        ):
            raise ValueError(f"scoring precondition failed: manifest entry {ordinal}")
        state_path = (
            root
            / ".better-product-graph"
            / "writing-evals"
            / entry["run_id"]
            / "state.json"
        )
        if state_path.is_symlink() or not state_path.is_file():
            raise ValueError(f"scoring precondition failed: state {ordinal} is missing")
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"scoring precondition failed: state {ordinal} is invalid") from error
        result_ref = state.get("result_ref") if isinstance(state, dict) else None
        try:
            _read_exact_project_ref(root, result_ref, f"result_ref:{ordinal}")
        except ValueError as error:
            raise ValueError(
                f"scoring precondition failed: all 27 durable result refs are required ({ordinal})"
            ) from error
        attempts.append(
            {
                "ordinal": ordinal,
                "run_id": entry["run_id"],
                "attempt_id": entry["attempt_id"],
                "result_ref": result_ref,
            }
        )
    invocation = {
        "schema_version": "prd-readability-v0.8-score-invocation.v1",
        "suite_id": SUITE_ID,
        "phase": phase,
        "execution_manifest_ref": _exact_project_ref(root, manifest_path),
        "batch_validation_receipt_ref": _exact_project_ref(root, batch_path),
        "scorer_ref": prereg["scorer_ref"],
        "evidence_snapshot": {
            "schema_version": "prd-readability-v0.8-score-evidence-snapshot.v1",
            "suite_id": SUITE_ID,
            "phase": phase,
            "attempts": attempts,
        },
    }
    _validate_score_invocation(root, phase, invocation)
    return invocation


def _validate_phase_score_report(report: Any, phase: str) -> None:
    if (
        not isinstance(report, dict)
        or set(report) != PHASE_SCORE_FIELDS
        or report.get("schema_version") != "prd-readability-v0.8-phase-score.v1"
        or report.get("suite_id") != SUITE_ID
        or report.get("phase") != phase
        or report.get("status") not in {"PASS", "FAIL"}
        or report.get("selection_policy")
        != "ALL_PRODUCED_ATTEMPTS_OCCUPY_DENOMINATOR_NO_BEST_OF_N_NO_REPLACEMENT"
        or not isinstance(report.get("issues"), list)
        or not isinstance(report.get("attempts"), list)
        or len(report["attempts"]) != 27
        or report.get("human_reader_validation") != "NOT_RUN"
    ):
        raise ValueError("terminal score object conflicts with frozen result contract")
    score = report.get("score")
    if (
        not isinstance(score, dict)
        or set(score) != {"passed", "total", "required"}
        or isinstance(score.get("passed"), bool)
        or not isinstance(score.get("passed"), int)
        or score.get("total") != 27
        or score.get("required") != 27
        or not 0 <= score["passed"] <= 27
        or isinstance(report.get("produced_output_count"), bool)
        or not isinstance(report.get("produced_output_count"), int)
        or not 0 <= report["produced_output_count"] <= 27
    ):
        raise ValueError("terminal score totals conflict with frozen result contract")
    passed_attempts = 0
    for ordinal, attempt in enumerate(report["attempts"], 1):
        if (
            not isinstance(attempt, dict)
            or set(attempt) != PHASE_SCORE_ATTEMPT_FIELDS
            or attempt.get("ordinal") != ordinal
            or attempt.get("status") not in {"PASS", "FAIL"}
            or not isinstance(attempt.get("issues"), list)
        ):
            raise ValueError("terminal attempt conflicts with frozen result contract")
        passed_attempts += int(attempt["status"] == "PASS")
    if score["passed"] != passed_attempts:
        raise ValueError("terminal score total differs from attempt objects")
    should_pass = (
        score == {"passed": 27, "total": 27, "required": 27}
        and report["produced_output_count"] == 27
        and not report["issues"]
    )
    if (report["status"] == "PASS") != should_pass:
        raise ValueError("terminal score status conflicts with frozen threshold")


def _phase_score_bundle(
    project_root: Path,
    phase: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
] | None:
    root = Path(project_root).resolve(strict=True)
    score_path, receipt_path = _phase_score_paths(root, phase)
    invocation_path, transaction_path = _phase_score_authority_paths(root, phase)
    ledger_path = _phase_score_ledger_path(root, phase)
    paths = {
        "controller ledger entry": ledger_path,
        "controller invocation": invocation_path,
        "score": score_path,
        "receipt": receipt_path,
        "controller transaction": transaction_path,
    }
    existence = {
        label: path.exists() or path.is_symlink() for label, path in paths.items()
    }
    if any(existence.values()) and not all(existence.values()):
        raise ValueError(
            "partial or preseeded terminal score transaction: fail closed; manual audit required"
        )
    if not any(existence.values()):
        return None
    for label, path in paths.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"terminal {label} must be a regular non-symlink file")
        if path.stat().st_nlink != 1:
            raise ValueError(f"terminal {label} must not have multiple hard links")
    invocation_bytes = invocation_path.read_bytes()
    score_bytes = score_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    transaction_bytes = transaction_path.read_bytes()
    ledger_bytes = ledger_path.read_bytes()
    try:
        ledger = json.loads(ledger_bytes.decode("utf-8"))
        controller_invocation = json.loads(invocation_bytes.decode("utf-8"))
        score = json.loads(score_bytes.decode("utf-8"))
        receipt = json.loads(receipt_bytes.decode("utf-8"))
        transaction = json.loads(transaction_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("terminal scoring authority contains invalid JSON") from error
    for label, value, content in (
        ("controller ledger entry", ledger, ledger_bytes),
        ("controller invocation", controller_invocation, invocation_bytes),
        ("score", score, score_bytes),
        ("receipt", receipt, receipt_bytes),
        ("controller transaction", transaction, transaction_bytes),
    ):
        if _document_bytes(value) != content:
            raise ValueError(f"terminal {label} bytes are non-canonical")
    _validate_phase_score_report(score, phase)
    receipt_fields = {
        "schema_version",
        "status",
        "suite_id",
        "phase",
        "terminal_outcome",
        "write_policy",
        "score_ref",
        "scorer_ref",
        "execution_manifest_ref",
        "batch_validation_receipt_ref",
        "evidence_snapshot",
        "evidence_snapshot_hash",
        "controller_invocation_ref",
        "terminal_transaction_id",
        "validation_digest",
    }
    if (
        not isinstance(receipt, dict)
        or set(receipt) != receipt_fields
        or receipt.get("schema_version")
        != "prd-readability-v0.8-phase-score-receipt.v1"
        or receipt.get("status") != "TERMINAL_WRITE_ONCE"
        or receipt.get("suite_id") != SUITE_ID
        or receipt.get("phase") != phase
        or receipt.get("terminal_outcome") != score["status"]
        or receipt.get("write_policy")
        != "FIRST_COMPLETED_SCORE_IS_IMMUTABLE_CONTROLLER_TRANSACTION_REQUIRED"
    ):
        raise ValueError("terminal receipt object conflicts with score")
    expected_score_ref = {
        "path": score_path.relative_to(root).as_posix(),
        "hash": _sha256(score_bytes),
        "version": 1,
    }
    if receipt.get("score_ref") != expected_score_ref:
        raise ValueError("terminal score hash or object conflict")
    invocation = {
        "schema_version": "prd-readability-v0.8-score-invocation.v1",
        "suite_id": SUITE_ID,
        "phase": phase,
        "execution_manifest_ref": receipt.get("execution_manifest_ref"),
        "batch_validation_receipt_ref": receipt.get(
            "batch_validation_receipt_ref"
        ),
        "scorer_ref": receipt.get("scorer_ref"),
        "evidence_snapshot": receipt.get("evidence_snapshot"),
    }
    _validate_score_invocation(root, phase, invocation)
    snapshot_hash = _sha256(_canonical_bytes(invocation["evidence_snapshot"]))
    if receipt.get("evidence_snapshot_hash") != snapshot_hash:
        raise ValueError("terminal evidence snapshot hash conflict")
    frozen_contract_refs = _frozen_contract_refs()
    invocation_hash = _sha256(_canonical_bytes(invocation))
    invocation_fields = {
        "schema_version",
        "status",
        "suite_id",
        "phase",
        "invocation",
        "invocation_hash",
        "frozen_contract_refs",
    }
    if (
        not isinstance(controller_invocation, dict)
        or set(controller_invocation) != invocation_fields
        or controller_invocation.get("schema_version")
        != "prd-readability-v0.8-controller-score-invocation.v1"
        or controller_invocation.get("status") != "AUTHORIZED_PRE_TERMINAL_WRITE"
        or controller_invocation.get("suite_id") != SUITE_ID
        or controller_invocation.get("phase") != phase
        or controller_invocation.get("invocation") != invocation
        or controller_invocation.get("invocation_hash") != invocation_hash
        or controller_invocation.get("frozen_contract_refs") != frozen_contract_refs
    ):
        raise ValueError("controller scoring invocation authority is invalid")
    expected_invocation_ref = {
        "path": invocation_path.relative_to(root).as_posix(),
        "hash": _sha256(invocation_bytes),
        "version": 1,
    }
    if receipt.get("controller_invocation_ref") != expected_invocation_ref:
        raise ValueError("receipt differs from controller scoring invocation")
    validation_digest = _score_validation_digest(
        phase, invocation, frozen_contract_refs, score
    )
    if receipt.get("validation_digest") != validation_digest:
        raise ValueError("terminal validation digest conflicts with exact score")
    expected_receipt_ref = {
        "path": receipt_path.relative_to(root).as_posix(),
        "hash": _sha256(receipt_bytes),
        "version": 1,
    }
    transaction_fields = {
        "schema_version",
        "status",
        "suite_id",
        "phase",
        "transaction_id",
        "controller_invocation_ref",
        "invocation_hash",
        "frozen_contract_refs",
        "execution_manifest_ref",
        "batch_validation_receipt_ref",
        "evidence_snapshot",
        "evidence_snapshot_hash",
        "validation_digest",
        "score_ref",
        "receipt_ref",
        "controller_ledger_ref",
    }
    transaction_id = "score-" + invocation_hash.removeprefix("sha256:")[:32]
    expected_transaction = {
        "schema_version": "prd-readability-v0.8-controller-score-transaction.v1",
        "status": "COMMITTED_TERMINAL",
        "suite_id": SUITE_ID,
        "phase": phase,
        "transaction_id": transaction_id,
        "controller_invocation_ref": expected_invocation_ref,
        "invocation_hash": invocation_hash,
        "frozen_contract_refs": frozen_contract_refs,
        "execution_manifest_ref": invocation["execution_manifest_ref"],
        "batch_validation_receipt_ref": invocation[
            "batch_validation_receipt_ref"
        ],
        "evidence_snapshot": invocation["evidence_snapshot"],
        "evidence_snapshot_hash": snapshot_hash,
        "validation_digest": validation_digest,
        "score_ref": expected_score_ref,
        "receipt_ref": expected_receipt_ref,
        "controller_ledger_ref": {
            "path": ledger_path.relative_to(root).as_posix(),
            "hash": _sha256(ledger_bytes),
            "version": 1,
        },
    }
    if (
        not isinstance(transaction, dict)
        or set(transaction) != transaction_fields
        or transaction != expected_transaction
        or receipt.get("terminal_transaction_id") != transaction_id
    ):
        raise ValueError("controller terminal scoring transaction authority is invalid")
    ledger_fields = {
        "schema_version",
        "status",
        "suite_id",
        "phase",
        "transaction_id",
        "invocation_hash",
        "frozen_contract_refs",
        "validation_digest",
        "score_hash",
    }
    expected_ledger = {
        "schema_version": "prd-readability-v0.8-controller-score-ledger.v1",
        "status": "TERMINAL_RESERVED",
        "suite_id": SUITE_ID,
        "phase": phase,
        "transaction_id": transaction_id,
        "invocation_hash": invocation_hash,
        "frozen_contract_refs": frozen_contract_refs,
        "validation_digest": validation_digest,
        "score_hash": _sha256(score_bytes),
    }
    if (
        not isinstance(ledger, dict)
        or set(ledger) != ledger_fields
        or ledger != expected_ledger
    ):
        raise ValueError("controller score ledger ancestry is invalid")
    return score, receipt, controller_invocation, transaction, ledger


def _load_terminal_score(
    project_root: Path,
    skill_root: Path,
    phase: str,
) -> dict[str, Any] | None:
    bundle = _phase_score_bundle(project_root, phase)
    if bundle is None:
        return None
    stored, _receipt, controller_invocation, transaction, _ledger = bundle
    derivation = _derive_phase_score(
        Path(project_root),
        Path(skill_root),
        phase,
        expected_invocation=controller_invocation["invocation"],
    )
    invocation, recomputed, _derived_skill_root = _unpack_validated_derivation(
        derivation, phase
    )
    expected_digest = _score_validation_digest(
        phase, invocation, _frozen_contract_refs(), recomputed
    )
    if (
        recomputed != stored
        or transaction.get("validation_digest") != expected_digest
    ):
        raise ValueError(
            "stored score is not derivable from exact frozen evidence and scorer"
        )
    return stored


def _unpack_validated_derivation(
    derivation: Any,
    phase: str,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    if (
        type(derivation) is not _ValidatedScoreDerivation
        or derivation._capability is not _DERIVATION_CAPABILITY
        or derivation._phase != phase
    ):
        raise ValueError(
            "caller-supplied score is forbidden; validated derivation is required"
        )
    try:
        invocation = json.loads(derivation._invocation_bytes.decode("utf-8"))
        report = json.loads(derivation._report_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("validated derivation is corrupt") from error
    if _canonical_bytes(invocation) != derivation._invocation_bytes:
        raise ValueError("validated derivation invocation is non-canonical")
    if _canonical_bytes(report) != derivation._report_bytes:
        raise ValueError("validated derivation report is non-canonical")
    return invocation, report, derivation._skill_root


def _derive_phase_score(
    project_root: Path,
    skill_root: Path,
    phase: str,
    *,
    expected_invocation: dict[str, Any] | None = None,
) -> _ValidatedScoreDerivation:
    """Derive one score from exact evidence and mint an in-process capability."""

    root = Path(project_root).resolve(strict=True)
    resolved_skill_root = Path(skill_root).resolve(strict=True)
    invocation = _prepare_score_invocation(root, phase)
    if expected_invocation is not None and invocation != expected_invocation:
        raise ValueError("stored scoring invocation differs from exact current evidence")
    report = _compute_phase_score(root, resolved_skill_root, phase)
    _validate_phase_score_report(report, phase)
    if _prepare_score_invocation(root, phase) != invocation:
        raise ValueError("score evidence changed during deterministic derivation")
    return _ValidatedScoreDerivation(
        _DERIVATION_CAPABILITY,
        phase,
        resolved_skill_root,
        invocation,
        report,
    )


def _commit_terminal_score(
    project_root: Path,
    phase: str,
    derivation: Any,
    caller_supplied_invocation: Any = None,
) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=True)
    if caller_supplied_invocation is not None:
        raise ValueError(
            "caller-supplied report/invocation is forbidden; validated derivation is required"
        )
    invocation, report, skill_root = _unpack_validated_derivation(
        derivation, phase
    )
    _validate_score_invocation(root, phase, invocation)
    _validate_phase_score_report(report, phase)
    frozen_contract_refs = _frozen_contract_refs()
    invocation_hash = _sha256(_canonical_bytes(invocation))
    transaction_id = "score-" + invocation_hash.removeprefix("sha256:")[:32]
    score_bytes = _document_bytes(report)
    score_root = _ensure_score_directory(root, phase)
    score_path = score_root / "score.json"
    receipt_path = score_root / "receipt.json"
    invocation_path = score_root / "controller-invocation.json"
    transaction_path = score_root / "controller-transaction.json"
    ledger_root = _ensure_score_ledger_directory(root)
    ledger_path = ledger_root / f"{phase}.json"
    if (
        invocation_path.exists()
        or invocation_path.is_symlink()
        or score_path.exists()
        or score_path.is_symlink()
        or receipt_path.exists()
        or receipt_path.is_symlink()
        or transaction_path.exists()
        or transaction_path.is_symlink()
        or ledger_path.exists()
        or ledger_path.is_symlink()
    ):
        raise ValueError(
            "terminal score or ledger ancestry already exists; recomputation is forbidden"
        )
    controller_invocation = {
        "schema_version": "prd-readability-v0.8-controller-score-invocation.v1",
        "status": "AUTHORIZED_PRE_TERMINAL_WRITE",
        "suite_id": SUITE_ID,
        "phase": phase,
        "invocation": invocation,
        "invocation_hash": invocation_hash,
        "frozen_contract_refs": frozen_contract_refs,
    }
    invocation_bytes = _document_bytes(controller_invocation)
    controller_invocation_ref = {
        "path": invocation_path.relative_to(root).as_posix(),
        "hash": _sha256(invocation_bytes),
        "version": 1,
    }
    validation_digest = _score_validation_digest(
        phase, invocation, frozen_contract_refs, report
    )
    receipt = {
        "schema_version": "prd-readability-v0.8-phase-score-receipt.v1",
        "status": "TERMINAL_WRITE_ONCE",
        "suite_id": SUITE_ID,
        "phase": phase,
        "terminal_outcome": report["status"],
        "write_policy": "FIRST_COMPLETED_SCORE_IS_IMMUTABLE_CONTROLLER_TRANSACTION_REQUIRED",
        "score_ref": {
            "path": score_path.relative_to(root).as_posix(),
            "hash": _sha256(score_bytes),
            "version": 1,
        },
        "scorer_ref": invocation["scorer_ref"],
        "execution_manifest_ref": invocation["execution_manifest_ref"],
        "batch_validation_receipt_ref": invocation[
            "batch_validation_receipt_ref"
        ],
        "evidence_snapshot": invocation["evidence_snapshot"],
        "evidence_snapshot_hash": _sha256(
            _canonical_bytes(invocation["evidence_snapshot"])
        ),
        "controller_invocation_ref": controller_invocation_ref,
        "terminal_transaction_id": transaction_id,
        "validation_digest": validation_digest,
    }
    receipt_bytes = _document_bytes(receipt)
    ledger = {
        "schema_version": "prd-readability-v0.8-controller-score-ledger.v1",
        "status": "TERMINAL_RESERVED",
        "suite_id": SUITE_ID,
        "phase": phase,
        "transaction_id": transaction_id,
        "invocation_hash": invocation_hash,
        "frozen_contract_refs": frozen_contract_refs,
        "validation_digest": validation_digest,
        "score_hash": _sha256(score_bytes),
    }
    ledger_bytes = _document_bytes(ledger)
    controller_ledger_ref = {
        "path": ledger_path.relative_to(root).as_posix(),
        "hash": _sha256(ledger_bytes),
        "version": 1,
    }
    transaction = {
        "schema_version": "prd-readability-v0.8-controller-score-transaction.v1",
        "status": "COMMITTED_TERMINAL",
        "suite_id": SUITE_ID,
        "phase": phase,
        "transaction_id": transaction_id,
        "controller_invocation_ref": controller_invocation_ref,
        "invocation_hash": invocation_hash,
        "frozen_contract_refs": frozen_contract_refs,
        "execution_manifest_ref": invocation["execution_manifest_ref"],
        "batch_validation_receipt_ref": invocation[
            "batch_validation_receipt_ref"
        ],
        "evidence_snapshot": invocation["evidence_snapshot"],
        "evidence_snapshot_hash": receipt["evidence_snapshot_hash"],
        "validation_digest": validation_digest,
        "score_ref": receipt["score_ref"],
        "receipt_ref": {
            "path": receipt_path.relative_to(root).as_posix(),
            "hash": _sha256(receipt_bytes),
            "version": 1,
        },
        "controller_ledger_ref": controller_ledger_ref,
    }
    _write_exclusive(ledger_path, ledger_bytes)
    _write_exclusive(invocation_path, invocation_bytes)
    _write_exclusive(score_path, score_bytes)
    _write_exclusive(receipt_path, receipt_bytes)
    _write_exclusive(transaction_path, _document_bytes(transaction))
    frozen_bundle = _phase_score_bundle(root, phase)
    frozen = None if frozen_bundle is None else frozen_bundle[0]
    if frozen != report:
        raise ValueError("terminal score read-back differs from committed report")
    return frozen


def _compute_phase_score(
    project_root: Path,
    skill_root: Path,
    phase: str,
) -> dict[str, Any]:
    """Compute a candidate report after write-once preconditions are bound."""

    contract = _contract()
    prereg = _preregistration()
    if phase not in prereg["mandatory_phases"]:
        raise ValueError("phase is not preregistered")
    manifest_path = _manifest_path(Path(project_root), phase)
    manifest = _load_json(manifest_path)
    manifest_issues = contract["execution_manifest_shape_issues"](manifest)
    manifest_issues.extend(
        contract["verify_batch_validation_receipt"](Path(project_root), manifest)
    )
    if manifest.get("phase") != phase:
        manifest_issues.append("manifest_phase")
    current_root = Path(project_root).resolve(strict=True)
    root_stat = current_root.stat()
    expected_root = {
        "path": str(current_root),
        "device": root_stat.st_dev,
        "inode": root_stat.st_ino,
    }
    if manifest.get("central_project_root") != expected_root:
        manifest_issues.append("central_project_root")
    evidence_reader = _evidence_reader()
    expected = _expected()["cases"]
    fixture_reviewer_ids = {
        _load_json(ROOT / ref["path"])["reviewer_id"]
        for ref in prereg["fixture_review_refs"]
    }
    scored: list[dict[str, Any]] = []
    coverage: dict[str, list[int]] = defaultdict(list)
    produced_count = 0
    global_issues = list(manifest_issues)

    for entry in manifest.get("entries", []):
        local_issues: list[str] = []
        evidence: dict[str, Any] | None = None
        try:
            evidence = evidence_reader["read_completed_evidence"](
                current_root, Path(skill_root), entry
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            controller_error = str(error)
        else:
            controller_error = None
        produced, raw_issues = _raw_output_issues(
            project_root=current_root,
            entry=entry,
            evidence=evidence,
        )
        produced_count += int(produced)
        local_issues.extend(raw_issues)
        if evidence is not None:
            if (
                evidence.get("suite_id") != SUITE_ID
                or evidence.get("case_id") != entry["agent_case_id"]
                or evidence.get("attempt_id") != entry["attempt_id"]
                or evidence.get("reviewer_execution_ref")
                != entry["reviewer_execution_ref"]
                or evidence.get("installed_build_ref")
                != entry["installed_build_ref"]
                or evidence.get("preregistration_checkpoint_ref")
                != entry["preregistration_checkpoint_ref"]
                or evidence.get("dispatch", {})
                .get("writing_eval_context", {})
                .get("author_execution_ref")
                != entry["author_execution_ref"]
            ):
                local_issues.append("manifest_authority_mismatch")
            oracle = expected.get(entry["semantic_case_id"])
            if not isinstance(oracle, dict):
                local_issues.append("semantic_case_id")
            else:
                local_issues.extend(_semantic_issues(evidence, oracle))
            if evidence["reviewer_execution_ref"]["id"] in fixture_reviewer_ids:
                local_issues.append("fixture_reviewer_reused_for_semantic_eval")
        elif produced and controller_error:
            local_issues.append("controller_validation_rejection_preserved")
        if not local_issues:
            coverage[entry["semantic_case_id"]].append(entry["repeat_index"])
        scored.append(
            {
                "ordinal": entry.get("ordinal"),
                "semantic_case_id": entry.get("semantic_case_id"),
                "repeat_index": entry.get("repeat_index"),
                "run_id": entry.get("run_id"),
                "attempt_id": entry.get("attempt_id"),
                "produced_output": produced,
                "status": "PASS" if not local_issues else "FAIL",
                "issues": sorted(set(local_issues)),
            }
        )

    for case_id in expected:
        if sorted(coverage.get(case_id, [])) != [1, 2, 3]:
            global_issues.append(f"repeat_coverage:{case_id}")
    passed = sum(item["status"] == "PASS" for item in scored)
    if produced_count != 27:
        global_issues.append("all_27_outputs_must_be_produced_before_submission")
    status = (
        "PASS"
        if not global_issues and passed == 27 and len(scored) == 27
        else "FAIL"
    )
    return {
        "schema_version": "prd-readability-v0.8-phase-score.v1",
        "suite_id": SUITE_ID,
        "phase": phase,
        "status": status,
        "selection_policy": "ALL_PRODUCED_ATTEMPTS_OCCUPY_DENOMINATOR_NO_BEST_OF_N_NO_REPLACEMENT",
        "score": {"passed": passed, "total": len(scored), "required": 27},
        "produced_output_count": produced_count,
        "installed_build_ref": manifest.get("installed_build_ref"),
        "issues": sorted(set(global_issues)),
        "attempts": scored,
        "agent_runtime_status": (
            "COMPLETED"
            if len(scored) == 27 and produced_count == 27
            else "STARTED_OR_INVALID"
            if produced_count
            else "NOT_RUN"
        ),
        "human_reader_validation": "NOT_RUN",
    }


def score_phase(
    project_root: Path,
    skill_root: Path,
    phase: str,
) -> dict[str, Any]:
    """Create one immutable phase score, or verify and return its stored bytes."""

    root = Path(project_root).resolve(strict=True)
    freeze_issues = _canonical_preregistration_issues()
    if freeze_issues:
        raise ValueError(
            "frozen score contract is invalid: " + ",".join(freeze_issues)
        )
    stored = _load_terminal_score(root, Path(skill_root), phase)
    if stored is not None:
        return stored
    derivation = _derive_phase_score(root, Path(skill_root), phase)
    return _commit_terminal_score(root, phase, derivation)


def score_release_phases(
    project_root: Path,
    skill_roots: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Read-only rederive and aggregate two already-frozen phase terminals."""

    freeze_issues = _canonical_preregistration_issues()
    if freeze_issues:
        raise ValueError(
            "frozen score contract is invalid: " + ",".join(freeze_issues)
        )
    preregistered_phases = _preregistration()["mandatory_phases"]
    if (
        not isinstance(skill_roots, dict)
        or set(skill_roots) != set(preregistered_phases)
    ):
        raise ValueError("exact skill_root for both frozen phases is required")
    contract = _contract()
    root = Path(project_root).resolve(strict=True)
    bundles = {
        phase: _phase_score_bundle(root, phase) for phase in preregistered_phases
    }
    if any(bundle is None for bundle in bundles.values()):
        raise ValueError("both frozen phase score receipts are required")
    phases_by_id = {
        phase: _load_terminal_score(root, Path(skill_roots[phase]), phase)
        for phase in preregistered_phases
    }
    if any(report is None for report in phases_by_id.values()):
        raise ValueError("both deterministically derived phase scores are required")
    phases = [phases_by_id[phase] for phase in preregistered_phases]
    manifests = {
        phase: json.loads(
            _read_exact_project_ref(
                root,
                bundles[phase][1]["execution_manifest_ref"],  # type: ignore[index]
                f"{phase}.execution_manifest_ref",
            ).decode("utf-8")
        )
        for phase in preregistered_phases
    }
    freshness_issues = contract["cross_phase_freshness_issues"](
        manifests["RC_CANDIDATE"], manifests["FINAL_PUBLIC_ARTIFACT"]
    )
    passed = not freshness_issues and all(
        item["status"] == "PASS"
        and item["score"] == {"passed": 27, "total": 27, "required": 27}
        for item in phases
    )
    return {
        "schema_version": "prd-readability-v0.8-release-score.v1",
        "suite_id": SUITE_ID,
        "status": "PASS" if passed else "FAIL",
        "cross_phase_policy": "BOTH_PHASES_PASS_NO_LATER_PHASE_RESCUE",
        "issues": freshness_issues,
        "phases": phases,
        "human_reader_validation": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--skill-root", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT"))
    args = parser.parse_args()
    try:
        report = score_phase(args.project_root, args.skill_root, args.phase)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {"status": "FAIL", "issues": [str(error)]},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
