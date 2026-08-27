#!/usr/bin/env python3
"""Score the frozen v0.5 oracle from Controller-verified durable Runs only."""

from __future__ import annotations

import argparse
import json
import runpy
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.bpg.writing_eval import WritingEvalError, WritingEvalRuntime


SUITE_ID = "better-product-graph-prd-readability-v0.5"
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

    contract = runpy.run_path(str(ROOT / "run_contract.py"))
    return list(contract["preregistration_issues"]())


def _expected() -> dict[str, Any]:
    value = _load_json(ROOT / "evaluator" / "expected.json")
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "suite_id", "custody", "cases"}
        or value.get("schema_version") != "prd-readability-expected-envelope.v0.5"
        or value.get("suite_id") != SUITE_ID
        or value.get("custody") != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE"
        or not isinstance(value.get("cases"), dict)
    ):
        raise ValueError("frozen expected oracle is invalid")
    return value


def _preregistration() -> dict[str, Any]:
    value = _load_json(ROOT / "evaluator" / "preregistration.json")
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "prd-readability-preregistration.v0.5"
        or value.get("suite_id") != SUITE_ID
        or value.get("status") != "PREREGISTERED_BEFORE_RESULTS"
        or value.get("freeze_order_authority")
        != "PREREGISTRATION_GIT_COMMIT_PRECEDES_RESULTS"
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
    all_issue_types: list[str] = []
    all_repairs: list[str] = []
    for field in ASSESSMENT_FIELDS:
        assessment = result[field]
        if assessment["verdict"] == "FINDING":
            finding_assessments.append(assessment)
            all_issue_types.extend(assessment["issue_types"])
            all_repairs.extend(assessment["repair_techniques"])

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
        if all_issue_types != [pair[0]]:
            issues.append("issue_count_or_primary_mismatch")
        if all_repairs != [pair[1]]:
            issues.append("repair_count_or_primary_mismatch")
    return issues


def score_controller_runs(
    project_root: Path,
    skill_root: Path,
    registrations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score all 27 durable Runs; no completion/build claim comes from the caller."""

    freeze_issues = _canonical_preregistration_issues()
    if freeze_issues:
        return {
            "schema_version": "prd-readability-v0.5-score-summary.v1",
            "suite_id": SUITE_ID,
            "status": "FAIL",
            "selection_policy": "ALL_ATTEMPTS_NO_BEST_OF_N",
            "score": {"passed": 0, "total": 0, "required": 27},
            "installed_build_ref": None,
            "issues": [f"frozen_contract:{issue}" for issue in freeze_issues],
            "attempts": [],
            "agent_runtime_status": "NOT_RUN",
            "human_reader_validation": "NOT_RUN",
        }

    expected = _expected()["cases"]
    prereg = _preregistration()
    global_issues: list[str] = []
    if (
        not isinstance(registrations, list)
        or len(registrations) != prereg["required_attempt_count"]
    ):
        global_issues.append("required_attempt_count")
    registrations = registrations if isinstance(registrations, list) else []

    runtime = WritingEvalRuntime(Path(project_root), Path(skill_root))
    coverage: dict[str, list[int]] = defaultdict(list)
    scored: list[dict[str, Any]] = []
    evidences: list[dict[str, Any]] = []
    durable_started = False
    fixture_reviewer_ids = {
        _load_json(ROOT / ref["path"])["reviewer_identity"]["id"]
        for ref in prereg["fixture_review_refs"]
    }

    for ordinal, registration in enumerate(registrations, 1):
        local_issues = _registration_issues(registration)
        semantic_case_id = (
            registration.get("semantic_case_id")
            if isinstance(registration, dict)
            else None
        )
        run_id = registration.get("run_id") if isinstance(registration, dict) else None
        repeat = (
            registration.get("repeat_index")
            if isinstance(registration, dict)
            else None
        )
        oracle = expected.get(semantic_case_id)
        evidence: dict[str, Any] | None = None
        if not isinstance(oracle, dict):
            local_issues.append("semantic_case_id")
        durable_status = "NOT_RUN"
        if isinstance(run_id, str) and run_id.strip():
            try:
                durable_status = runtime.probe_durable_run(run_id)
            except (OSError, ValueError, WritingEvalError) as error:
                durable_started = True
                local_issues.append(f"controller_probe:{error}")
            else:
                durable_started = durable_started or durable_status != "NOT_RUN"
                if durable_status == "NOT_RUN":
                    local_issues.append("controller_evidence:durable Run does not exist")
        if not local_issues:
            try:
                evidence = runtime.read_completed_evidence(run_id)
            except (OSError, ValueError, WritingEvalError) as error:
                local_issues.append(f"controller_evidence:{error}")
            else:
                evidences.append(evidence)
                local_issues.extend(_semantic_issues(evidence, oracle))
                coverage[semantic_case_id].append(repeat)
                if evidence["reviewer_execution_ref"]["id"] in fixture_reviewer_ids:
                    local_issues.append("fixture_reviewer_reused_for_semantic_eval")
        status = "PASS" if not local_issues else "FAIL"
        scored.append(
            {
                "ordinal": ordinal,
                "semantic_case_id": semantic_case_id,
                "run_id": run_id,
                "attempt_id": evidence.get("attempt_id") if evidence else None,
                "status": status,
                "issues": local_issues,
            }
        )

    for case_id in expected:
        if sorted(coverage.get(case_id, [])) != list(
            range(1, prereg["repeats_per_case"] + 1)
        ):
            global_issues.append(f"repeat_coverage:{case_id}")

    def duplicate(values: list[Any]) -> bool:
        return len(values) != len(set(values))

    run_ids = [
        item["run_id"]
        for item in registrations
        if isinstance(item, dict) and isinstance(item.get("run_id"), str)
    ]
    attempt_ids = [item["attempt_id"] for item in evidences]
    reviewer_ids = [item["reviewer_execution_ref"]["id"] for item in evidences]
    build_identities = {
        json.dumps(item["installed_build_ref"], sort_keys=True) for item in evidences
    }
    if duplicate(run_ids):
        global_issues.append("duplicate_run_id")
    if duplicate(attempt_ids):
        global_issues.append("duplicate_attempt_id")
    if duplicate(reviewer_ids):
        global_issues.append("duplicate_reviewer_id")
    if len(build_identities) != 1 or len(evidences) != len(registrations):
        global_issues.append("one_exact_installed_build_all_attempts")

    passed = sum(item["status"] == "PASS" for item in scored)
    case_passes = Counter(
        item["semantic_case_id"]
        for item in scored
        if item["status"] == "PASS" and item["semantic_case_id"] in expected
    )
    if any(
        case_passes[case_id] != prereg["required_passed_repeats_per_case"]
        for case_id in expected
    ):
        global_issues.append("required_passed_repeats_per_case")
    status = (
        "PASS"
        if not global_issues
        and passed == prereg["required_passed_attempt_count"]
        and len(scored) == prereg["required_attempt_count"]
        else "FAIL"
    )
    installed_build_ref = (
        evidences[0]["installed_build_ref"]
        if len(build_identities) == 1 and evidences
        else None
    )
    return {
        "schema_version": "prd-readability-v0.5-score-summary.v1",
        "suite_id": SUITE_ID,
        "status": status,
        "selection_policy": "ALL_ATTEMPTS_NO_BEST_OF_N",
        "score": {
            "passed": passed,
            "total": len(scored),
            "required": prereg["required_passed_attempt_count"],
        },
        "installed_build_ref": installed_build_ref,
        "issues": sorted(set(global_issues)),
        "attempts": scored,
        "agent_runtime_status": (
            "COMPLETED"
            if len(registrations) == prereg["required_attempt_count"]
            and len(evidences) == prereg["required_attempt_count"]
            else "STARTED_OR_INVALID"
            if durable_started
            else "NOT_RUN"
        ),
        "human_reader_validation": "NOT_RUN",
    }


def load_run_registrations(path: Path) -> list[dict[str, Any]]:
    value = _load_json(path)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "suite_id", "registrations"}
        or value.get("schema_version")
        != "prd-readability-v0.5-run-registration.v1"
        or value.get("suite_id") != SUITE_ID
        or not isinstance(value.get("registrations"), list)
    ):
        raise ValueError("run registration envelope is invalid")
    return value["registrations"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--skill-root", required=True, type=Path)
    parser.add_argument("--registrations", required=True, type=Path)
    args = parser.parse_args()
    try:
        freeze_issues = _canonical_preregistration_issues()
        if freeze_issues:
            print(
                json.dumps(
                    {
                        "status": "FAIL",
                        "issues": [
                            f"frozen_contract:{issue}" for issue in freeze_issues
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        registrations = load_run_registrations(args.registrations)
        report = score_controller_runs(
            args.project_root, args.skill_root, registrations
        )
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
