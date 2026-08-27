#!/usr/bin/env python3
"""Score the frozen v0.7 oracle from Controller-verified durable Runs only."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


SUITE_ID = "better-product-graph-prd-readability-v0.7"
REGISTRATION_FIELDS = frozenset({"semantic_case_id", "repeat_index", "run_id"})
ASSESSMENT_FIELDS = (
    "verbosity_assessment",
    "checklist_assessment",
    "visual_assessment",
)


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
        or value.get("schema_version") != "prd-readability-expected-envelope.v0.7"
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
        or value.get("schema_version") != "prd-readability-preregistration.v0.7"
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


def score_phase(
    project_root: Path,
    skill_root: Path,
    phase: str,
) -> dict[str, Any]:
    """Score one immutable 27-slot phase; another phase can never rescue it."""

    freeze_issues = _canonical_preregistration_issues()
    if freeze_issues:
        return {
            "schema_version": "prd-readability-v0.7-phase-score.v1",
            "suite_id": SUITE_ID,
            "phase": phase,
            "status": "FAIL",
            "selection_policy": "ALL_PRODUCED_ATTEMPTS_OCCUPY_DENOMINATOR_NO_BEST_OF_N_NO_REPLACEMENT",
            "score": {"passed": 0, "total": 0, "required": 27},
            "produced_output_count": 0,
            "installed_build_ref": None,
            "issues": [f"frozen_contract:{issue}" for issue in freeze_issues],
            "attempts": [],
            "agent_runtime_status": "NOT_RUN",
            "human_reader_validation": "NOT_RUN",
        }

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
        _load_json(ROOT / ref["path"])["reviewer_identity"]["id"]
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
        "schema_version": "prd-readability-v0.7-phase-score.v1",
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


def score_release_phases(
    project_root: Path,
    skill_roots: dict[str, Path],
) -> dict[str, Any]:
    """Require both mandatory phases independently; final cannot rescue RC."""

    preregistered_phases = _preregistration()["mandatory_phases"]
    contract = _contract()
    manifests = {
        phase: _load_json(_manifest_path(Path(project_root), phase))
        for phase in preregistered_phases
    }
    freshness_issues = contract["cross_phase_freshness_issues"](
        manifests["RC_CANDIDATE"], manifests["FINAL_PUBLIC_ARTIFACT"]
    )
    phases = [
        score_phase(project_root, skill_roots[phase], phase)
        for phase in preregistered_phases
    ]
    passed = not freshness_issues and all(
        item["status"] == "PASS"
        and item["score"] == {"passed": 27, "total": 27, "required": 27}
        for item in phases
    )
    return {
        "schema_version": "prd-readability-v0.7-release-score.v1",
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
