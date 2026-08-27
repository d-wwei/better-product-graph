#!/usr/bin/env python3
"""Expose the v0.8 fixture-review gate without creating semantic evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
CASES_ROOT = ROOT / "cases"
ASSETS_ROOT = ROOT / "assets"
FIXTURE_REVIEW_ROOT = ROOT / "fixture-review"
REVIEW_PATHS = (
    FIXTURE_REVIEW_ROOT / "reviewer-a.json",
    FIXTURE_REVIEW_ROOT / "reviewer-b.json",
)
ADJUDICATION_PATH = FIXTURE_REVIEW_ROOT / "adjudication.json"
SUITE_PATH = ROOT / "suite.json"
EXPECTED_PATH = ROOT / "evaluator" / "expected.json"
PREREGISTRATION_PATH = ROOT / "evaluator" / "preregistration.json"
SCORER_PATH = ROOT / "evaluator" / "score_results.py"
EVIDENCE_READER_PATH = ROOT / "evaluator" / "evidence_reader.py"
FIXTURE_TREE_PATH = ROOT / "fixture-tree.json"
SUITE_ID = "better-product-graph-prd-readability-v0.8"
TREE_HASH = "sha256:da47036a8a805580542574f40d5c623ccd7a487aa15724a510001da840b69ef6"
FIXTURE_MANIFEST_HASH = "sha256:1efdd8bb1046f4b95cbdecc8a34f18c83df5e7a6650b83a04a57089f53fdc86a"
CASE_IDS = tuple(f"case-{index:03d}" for index in range(1, 10))
MANDATORY_PHASES = ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT")
PHASE_BUILD_VERSIONS = {
    "RC_CANDIDATE": "0.2.18-rc.5",
    "FINAL_PUBLIC_ARTIFACT": "0.2.18",
}
PHASE_SCORE_CONTRACT = {
    "schema_version": "prd-readability-v0.8-phase-score-contract.v1",
    "invocation_schema": "prd-readability-v0.8-score-invocation.v1",
    "invocation_fields": [
        "schema_version", "suite_id", "phase", "execution_manifest_ref",
        "batch_validation_receipt_ref", "scorer_ref", "evidence_snapshot",
    ],
    "evidence_snapshot_schema": "prd-readability-v0.8-score-evidence-snapshot.v1",
    "evidence_snapshot_attempt_fields": [
        "ordinal", "run_id", "attempt_id", "result_ref",
    ],
    "score_schema": "prd-readability-v0.8-phase-score.v1",
    "score_fields": [
        "schema_version", "suite_id", "phase", "status", "selection_policy",
        "score", "produced_output_count", "installed_build_ref", "issues",
        "attempts", "agent_runtime_status", "human_reader_validation",
    ],
    "score_attempt_fields": [
        "ordinal", "semantic_case_id", "repeat_index", "run_id", "attempt_id",
        "produced_output", "status", "issues",
    ],
    "receipt_schema": "prd-readability-v0.8-phase-score-receipt.v1",
    "receipt_fields": [
        "schema_version", "status", "suite_id", "phase", "terminal_outcome",
        "write_policy", "score_ref", "scorer_ref", "execution_manifest_ref",
        "batch_validation_receipt_ref", "evidence_snapshot",
        "evidence_snapshot_hash", "controller_invocation_ref",
        "terminal_transaction_id", "validation_digest",
    ],
    "controller_invocation_schema": "prd-readability-v0.8-controller-score-invocation.v1",
    "controller_invocation_fields": [
        "schema_version", "status", "suite_id", "phase", "invocation",
        "invocation_hash", "frozen_contract_refs",
    ],
    "terminal_transaction_schema": "prd-readability-v0.8-controller-score-transaction.v1",
    "terminal_transaction_fields": [
        "schema_version", "status", "suite_id", "phase", "transaction_id",
        "controller_invocation_ref", "invocation_hash", "frozen_contract_refs",
        "execution_manifest_ref", "batch_validation_receipt_ref",
        "evidence_snapshot", "evidence_snapshot_hash", "validation_digest",
        "score_ref", "receipt_ref", "controller_ledger_ref",
    ],
    "controller_ledger_schema": "prd-readability-v0.8-controller-score-ledger.v1",
    "controller_ledger_fields": [
        "schema_version", "status", "suite_id", "phase", "transaction_id",
        "invocation_hash", "frozen_contract_refs", "validation_digest",
        "score_hash",
    ],
    "frozen_contract_ref_fields": [
        "preregistration_ref", "expected_ref", "run_contract_ref", "scorer_ref",
        "evidence_reader_ref",
    ],
    "terminal_paths": {
        "score": ".better-product-graph/writing-evals/phase-scores/<PHASE>/score.json",
        "receipt": ".better-product-graph/writing-evals/phase-scores/<PHASE>/receipt.json",
        "controller_invocation": ".better-product-graph/writing-evals/phase-scores/<PHASE>/controller-invocation.json",
        "controller_transaction": ".better-product-graph/writing-evals/phase-scores/<PHASE>/controller-transaction.json",
        "controller_ledger": ".better-product-graph/writing-evals/score-ledger/<PHASE>.json",
    },
    "first_invocation_preconditions": [
        "EXACT_EXECUTION_MANIFEST_AND_BATCH_RECEIPT_EXIST",
        "ALL_27_DURABLE_RESULT_REFS_EXIST",
        "EXACT_SCORER_HASH_MATCHES_PREREGISTRATION",
    ],
    "early_score_policy": "REJECT_WITHOUT_TERMINAL_ARTIFACT",
    "first_completed_score_policy": "INTERNAL_DERIVATION_CAPABILITY_THEN_O_EXCL_LEDGER_INVOCATION_SCORE_RECEIPT_TRANSACTION_FIRST_FAIL_IS_TERMINAL",
    "repeat_policy": "VALIDATE_CANONICAL_FREEZE_LEDGER_AND_TRANSACTION_THEN_READ_ONLY_RECOMPUTE_EVERY_SCORE_FIELD_FROM_EXACT_BOUND_EVIDENCE",
    "partial_write_policy": "FAIL_CLOSED_NO_RECOMPUTE_MANUAL_AUDIT_REQUIRED",
    "release_aggregation_policy": "READ_ONLY_REDERIVE_BOTH_EXACT_PHASES_VERIFY_LEDGER_AND_TRANSACTION_NEVER_CREATE_OR_UPDATE_PHASE_SCORE",
    "trust_boundary": "FAIL_CLOSED_FOR_SUPPORTED_CODE_PATH_ACCIDENT_REPLAY_PARTIAL_AND_DIRECT_FABRICATION_NOT_CRYPTOGRAPHIC_RESISTANCE_TO_PRIVILEGED_LOCAL_CODE_AND_EVIDENCE_REWRITE",
}
INTENDED_OBJECTIVES = {
    "case-001": "MAKE_PEER_STRUCTURE_SCANNABLE",
    "case-002": "KEEP_ONE_CANONICAL_DEFINITION",
    "case-003": "REMOVE_REDUNDANT_REPRESENTATION",
    "case-004": "PRESERVE_CHECKLIST_FUNCTION",
    "case-005": "CLARIFY_COMPLETION_EVIDENCE_BOUNDARY",
    "case-006": "CLARIFY_ARTIFACT_MATURITY_BOUNDARY",
    "case-007": "NO_REPAIR_REQUIRED",
    "case-008": "NO_REPAIR_REQUIRED",
    "case-009": "NO_REPAIR_REQUIRED",
}
ALLOWED_PRIMARY_PAIRS = {
    "case-001": [["FLAT_PEER_OVERLOAD", "GROUP"], ["FLAT_PEER_OVERLOAD", "LAYER"]],
    "case-002": [["SEMANTIC_REPETITION", "REFERENCE"], ["SEMANTIC_REPETITION", "MERGE"]],
    "case-003": [["REPRESENTATION_COLLISION", "TRIM"], ["REPRESENTATION_COLLISION", "REFERENCE"], ["REPRESENTATION_COLLISION", "MERGE"]],
    "case-004": [["CHECKLIST_FUNCTION_LOSS", "RESTORE_FUNCTION"], ["CHECKLIST_FUNCTION_LOSS", "REFERENCE"]],
    "case-005": [["COMPLETION_SEMANTICS_AMBIGUOUS", "EXPLAIN"], ["COMPLETION_SEMANTICS_AMBIGUOUS", "BOUNDARY"]],
    "case-006": [["ARTIFACT_MATURITY_OVERCLAIM", "BOUNDARY"], ["ARTIFACT_MATURITY_OVERCLAIM", "EXPLAIN"]],
    "case-007": [],
    "case-008": [],
    "case-009": [],
}
CALIBRATION_CONTROL_ID = "paired-positive"
CALIBRATION_CONTROL_PATH = ROOT / "calibration" / "notification-priority-positive.md"
CALIBRATION_CLAIM_BOUNDARY = {
    "fixture_calibration_only": True,
    "agent_product_eval": "NOT_RUN",
    "ordinary_product_review": "NOT_RUN",
    "human_reader_validation": "NOT_RUN",
}
CALIBRATION_REVIEW_HASHES = {
    "reviewer-a.json": "sha256:496d2250f8bbee379a9195cd9222d87474c723374dc3a53fae9f0c747005166a",
    "reviewer-b.json": "sha256:b52e32fe827eeef784bc751f6b4b1543be47deb34dadaced504b3dbf26eb3a7a",
}
CALIBRATION_REVIEWER_IDS = {
    "reviewer-a.json": "fixture-review-v08-a2-20260826",
    "reviewer-b.json": "fixture-review-v08-b2-20260826",
}
CALIBRATION_SOURCE_PATHS = {
    **{case_id: CASES_ROOT / f"{case_id}.md" for case_id in CASE_IDS},
    CALIBRATION_CONTROL_ID: CALIBRATION_CONTROL_PATH,
}
CALIBRATION_SOURCE_ORDERS = {
    "reviewer-a.json": (
        "case-001", CALIBRATION_CONTROL_ID, "case-002", "case-003", "case-004",
        "case-005", "case-006", "case-007", "case-008", "case-009",
    ),
    "reviewer-b.json": (
        "case-006", "case-002", "case-008", CALIBRATION_CONTROL_ID, "case-001",
        "case-009", "case-004", "case-007", "case-003", "case-005",
    ),
}
CALIBRATION_EXPECTED_RESULTS = {
    **{case_id: "FINDING" for case_id in CASE_IDS[:6]},
    **{case_id: "PASS" for case_id in CASE_IDS[6:]},
    CALIBRATION_CONTROL_ID: "PASS",
}
CALIBRATION_REVIEW_FIELDS = frozenset(
    {
        "document_id", "result", "observed_reader_outcome", "primary_diagnosis",
        "primary_repair_technique", "exact_basis", "reason",
    }
)
CALIBRATION_BASIS_FIELDS = frozenset({"path", "hash", "start_line", "end_line"})
READER_OUTCOMES = frozenset({"SEE", "LOCATE", "RETELL", "DECIDE"})
AGENT_RESOURCE_EXPORTS = (
    ("profile_ref", "PRD_WRITING_PROFILE_v0.5.json"),
    ("guide_ref", "PRD_WRITING_GUIDE_v0.5.md"),
    ("instruction_ref", "INSTRUCTIONS_v3.2.md"),
    ("reviewer_resource_ref", "reviewer-resource-v3.2.json"),
    ("output_contract_ref", "output-contract.json"),
    ("result_schema_ref", "result-schema-v3.1.json"),
)
SOURCE_VISUAL_REF = re.compile(
    r"!\[[^\]\n]*\]\((?P<destination>\.\./assets/(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*\.svg))\)"
)
EXACT_REF_FIELDS = frozenset({"path", "hash", "version"})
EXECUTION_REF_FIELDS = frozenset({"kind", "id"})
MANIFEST_FIELDS = frozenset(
    {
        "schema_version", "status", "suite_id", "phase",
        "central_project_root", "installed_build_ref",
        "required_attempt_count", "result_ref_null_count_at_freeze",
        "agent_output_count_at_freeze", "entries",
    }
)
MANIFEST_ENTRY_FIELDS = frozenset(
    {
        "ordinal", "suite_id", "phase", "semantic_case_id", "agent_case_id",
        "repeat_index", "run_id", "attempt_id", "reviewer_execution_ref",
        "author_execution_ref", "preregistration_checkpoint_ref",
        "work_order_ref", "output_target", "central_project_root", "state_ref",
        "installed_build_ref",
    }
)
MECHANICAL_AUTHORITY_FIELDS = frozenset(
    {
        "schema_version", "evaluation_only", "authority", "suite_id", "case_id",
        "node_id", "attempt_id", "instruction_ref", "instruction_hash",
        "input_refs", "input_hashes", "preregistration_checkpoint_ref",
        "candidate_ref", "profile_ref", "guide_ref", "reviewer_resource_ref",
        "output_contract_ref", "author_execution_ref", "reviewer_execution_ref",
        "reviewer_role", "isolated_input_refs", "claim_boundary",
    }
)
EXPORT_MANIFEST_FIELDS = frozenset(
    {"schema_version", "suite_id", "case_id", "files", "evaluator_files_included"}
)
WORK_ORDER_FIELDS = frozenset(
    {
        "schema_version", "suite_id", "phase", "case_id", "repeat_index", "run_id",
        "attempt_id", "reviewer_execution_ref", "author_execution_ref",
        "preregistration_checkpoint_ref", "output_target", "instruction_ref",
        "instruction_hash", "input_refs", "input_hashes", "candidate_ref", "profile_ref",
        "guide_ref", "reviewer_resource_ref", "output_contract_ref", "isolated_input_refs",
        "reader_visible_visual_pairs", "claim_boundary",
    }
)


def _sha256(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _exact_source_asset(path: Path) -> tuple[bytes, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"visual fixture asset must be a regular non-symlink file: {path}")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(ASSETS_ROOT.resolve(strict=True))
    except ValueError as error:
        raise ValueError(f"visual fixture asset escapes the suite assets directory: {path}") from error
    content = resolved.read_bytes()
    return content, resolved.relative_to(REPO_ROOT.resolve()).as_posix()


def build_agent_case_payload(case_id: str) -> dict[str, Any]:
    """Prepare exact non-evaluator bytes for a future anonymous Agent workspace.

    This pure preparation step does not write or authorize a workspace. The public
    export stays fail-closed until fixture review and preregistration are complete.
    """

    if case_id not in CASE_IDS:
        raise ValueError(f"unknown v0.8 readability case: {case_id}")
    case_path = CASES_ROOT / f"{case_id}.md"
    if case_path.is_symlink() or not case_path.is_file():
        raise ValueError(f"case fixture must be a regular non-symlink file: {case_id}")
    markdown = case_path.read_text(encoding="utf-8")
    asset_payloads: dict[str, bytes] = {}
    asset_refs: list[dict[str, str]] = []
    for match in SOURCE_VISUAL_REF.finditer(markdown):
        svg_name = match.group("name")
        png_name = f"{svg_name[:-4]}@2x.png"
        for name in (svg_name, png_name):
            content, source_path = _exact_source_asset(ASSETS_ROOT / name)
            if name in asset_payloads:
                continue
            asset_payloads[name] = content
            asset_refs.append(
                {
                    "source_path": source_path,
                    "agent_path": f"assets/{name}",
                    "hash": _sha256(content),
                }
            )
        markdown = markdown.replace(
            match.group("destination"),
            f"./assets/{svg_name}",
        )
    return {
        "candidate_markdown": markdown,
        "asset_payloads": asset_payloads,
        "asset_refs": asset_refs,
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _load_evidence_reader() -> dict[str, Any]:
    prereg = _load_json(PREREGISTRATION_PATH)
    ref = prereg.get("evidence_reader_ref") if isinstance(prereg, dict) else None
    if (
        not isinstance(ref, dict)
        or set(ref) != EXACT_REF_FIELDS
        or ref.get("path") != "evaluator/evidence_reader.py"
        or EVIDENCE_READER_PATH.is_symlink()
        or not EVIDENCE_READER_PATH.is_file()
        or ref.get("hash") != _sha256(EVIDENCE_READER_PATH.read_bytes())
    ):
        raise ValueError("evidence_reader_ref differs from frozen preregistration")
    return runpy.run_path(str(EVIDENCE_READER_PATH))


def fixture_tree_identity() -> dict[str, Any]:
    """Return the exact scored cases, visual pair, and unscored control identity."""

    recorded = _load_json(FIXTURE_TREE_PATH)
    if recorded is None:
        raise ValueError("fixture-tree.json is missing or invalid")
    paths = [CASES_ROOT / f"{case_id}.md" for case_id in CASE_IDS]
    paths.extend(sorted(ASSETS_ROOT.iterdir(), key=lambda path: path.name))
    paths.append(CALIBRATION_CONTROL_PATH)
    files: list[dict[str, Any]] = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"fixture tree member must be a regular non-symlink file: {path}")
        content = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "hash": _sha256(content),
                "size": len(content),
            }
        )
    canonical = json.dumps(files, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    current = {
        "schema_version": "prd-readability-v0.8-fixture-tree.v1",
        "suite_id": SUITE_ID,
        "status": "BLIND_FIXTURE_CALIBRATION_PENDING",
        "tree_hash": _sha256(canonical.encode("utf-8")),
        "files": files,
    }
    if recorded != current:
        raise ValueError("fixture-tree.json differs from exact fixture bytes")
    return current


def _attempt_id(value: Any) -> str | None:
    identifier = value.get("id") if isinstance(value, dict) else None
    return identifier if isinstance(identifier, str) else None


def validate_fixture_review_gate(
    review_root: Path = FIXTURE_REVIEW_ROOT,
) -> tuple[bool, list[str]]:
    """Validate the exact A2/B2 blind results and their closed adjudication."""

    reasons: list[str] = []
    try:
        tree = fixture_tree_identity()
    except ValueError as error:
        return False, [str(error)]
    review_paths = (review_root / "reviewer-a.json", review_root / "reviewer-b.json")
    reviews = [_load_json(path) for path in review_paths]
    adjudication = _load_json(review_root / "adjudication.json")
    if any(review is None for review in reviews):
        reasons.append("two_current_review_records_required")
    if adjudication is None:
        reasons.append("adjudication_required")
    if reasons:
        return False, reasons
    typed_reviews = [review for review in reviews if isinstance(review, dict)]
    reviewer_ids: list[str] = []
    observed_by_source: list[dict[str, str]] = []
    review_paths = (review_root / "reviewer-a.json", review_root / "reviewer-b.json")
    for path, review in zip(review_paths, typed_reviews, strict=True):
        label = path.name
        if _sha256(path.read_bytes()) != CALIBRATION_REVIEW_HASHES[label]:
            reasons.append(f"{label}: exact_hash")
        if set(review) != {
            "schema_version", "suite_id", "reviewer_id", "claim_boundary", "reviews"
        }:
            reasons.append(f"{label}: closed_result")
        reviewer_id = review.get("reviewer_id")
        if reviewer_id != CALIBRATION_REVIEWER_IDS[label]:
            reasons.append(f"{label}: reviewer_id")
        elif isinstance(reviewer_id, str):
            reviewer_ids.append(reviewer_id)
        if (
            review.get("schema_version")
            != "prd-readability-v0.8-blind-calibration-review-result.v1"
            or review.get("suite_id") != SUITE_ID
            or review.get("claim_boundary") != CALIBRATION_CLAIM_BOUNDARY
        ):
            reasons.append(f"{label}: identity_or_boundary")
        items = review.get("reviews")
        source_order = CALIBRATION_SOURCE_ORDERS[label]
        if not isinstance(items, list) or len(items) != len(source_order):
            reasons.append(f"{label}: review_count")
            continue
        observed: dict[str, str] = {}
        for ordinal, (item, source_id) in enumerate(zip(items, source_order, strict=True), start=1):
            if not isinstance(item, dict) or set(item) != CALIBRATION_REVIEW_FIELDS:
                reasons.append(f"{label}: document-{ordinal:03d}: closed_review")
                continue
            source_path = CALIBRATION_SOURCE_PATHS[source_id]
            source_hash = _sha256(source_path.read_bytes())
            expected_result = CALIBRATION_EXPECTED_RESULTS[source_id]
            if (
                item.get("document_id") != f"document-{ordinal:03d}"
                or item.get("result") != expected_result
                or item.get("observed_reader_outcome") not in READER_OUTCOMES
                or not isinstance(item.get("reason"), str)
                or not item["reason"].strip()
            ):
                reasons.append(f"{label}: document-{ordinal:03d}: outcome")
            diagnosis = item.get("primary_diagnosis")
            repair = item.get("primary_repair_technique")
            if expected_result == "PASS":
                if diagnosis is not None or repair is not None:
                    reasons.append(f"{label}: document-{ordinal:03d}: pass_primary")
            elif [diagnosis, repair] not in ALLOWED_PRIMARY_PAIRS[source_id]:
                reasons.append(f"{label}: document-{ordinal:03d}: primary_pair")
            basis = item.get("exact_basis")
            if not isinstance(basis, list) or not basis:
                reasons.append(f"{label}: document-{ordinal:03d}: basis")
                continue
            line_count = len(source_path.read_text(encoding="utf-8").splitlines())
            for ref in basis:
                if (
                    not isinstance(ref, dict)
                    or set(ref) != CALIBRATION_BASIS_FIELDS
                    or ref.get("path") != f"documents/document-{ordinal:03d}.md"
                    or ref.get("hash") != source_hash
                    or isinstance(ref.get("start_line"), bool)
                    or not isinstance(ref.get("start_line"), int)
                    or isinstance(ref.get("end_line"), bool)
                    or not isinstance(ref.get("end_line"), int)
                    or not 1 <= ref["start_line"] <= ref["end_line"] <= line_count
                ):
                    reasons.append(f"{label}: document-{ordinal:03d}: exact_basis")
            observed[source_id] = item.get("result")
        if sum(result == "FINDING" for result in observed.values()) != 6:
            reasons.append(f"{label}: finding_count")
        if sum(result == "PASS" for result in observed.values()) != 4:
            reasons.append(f"{label}: pass_count")
        observed_by_source.append(observed)
    if len(reviewer_ids) != 2 or len(set(reviewer_ids)) != 2:
        reasons.append("distinct_reviewer_ids_required")
    if len(observed_by_source) != 2 or observed_by_source[0] != observed_by_source[1]:
        reasons.append("blind_review_outcome_disagreement")
    assert adjudication is not None
    expected_review_refs = [
        {
            "path": f"fixture-review/{path.name}",
            "hash": _sha256(path.read_bytes()),
            "reviewer_id": reviewer_id,
        }
        for path, reviewer_id in zip(review_paths, reviewer_ids, strict=False)
    ]
    if (
        adjudication.get("schema_version")
        != "prd-readability-v0.8-fixture-adjudication.v1"
        or adjudication.get("status") != "APPROVED_FOR_PREREGISTRATION"
        or adjudication.get("suite_id") != SUITE_ID
        or adjudication.get("approved_scored_case_ids") != list(CASE_IDS)
        or adjudication.get("review_refs") != expected_review_refs
        or adjudication.get("fixture_tree") != {
            "manifest_path": "fixture-tree.json",
            "manifest_file_sha256": FIXTURE_MANIFEST_HASH,
            "tree_hash": tree["tree_hash"],
        }
        or adjudication.get("agreement") != {
            "reviewers": 2,
            "finding_documents": 6,
            "pass_documents": 4,
            "outcome_disagreements": [],
        }
        or adjudication.get("calibration_only_document") != {
            "path": "calibration/notification-priority-positive.md",
            "result": "PASS",
            "included_in_scored_denominator": False,
        }
        or adjudication.get("current_concern_dispositions") != []
        or adjudication.get("superseded_calibration", {}).get("reused") is not False
    ):
        reasons.append("adjudication: identity_or_disposition")
    for field in (
        "semantic_evaluation_status",
        "agent_runtime_status",
        "real_prd_review_status",
        "human_reader_validation",
    ):
        if adjudication.get(field) != "NOT_RUN":
            reasons.append(f"adjudication: {field}")
    return not reasons, sorted(set(reasons))


def fixture_reviews_are_approved() -> bool:
    approved, _ = validate_fixture_review_gate()
    return approved


def _exact_ref_issues(
    value: Any,
    *,
    label: str,
    base: Path,
    expected_path: str,
) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"path", "hash", "version"}:
        return [f"{label}: closed_exact_ref"]
    if value.get("path") != expected_path:
        return [f"{label}: path"]
    relative = Path(expected_path)
    if relative.is_absolute() or ".." in relative.parts:
        return [f"{label}: path_escape"]
    path = base / relative
    if path.is_symlink() or not path.is_file():
        return [f"{label}: regular_file"]
    if value.get("hash") != _sha256(path.read_bytes()):
        return [f"{label}: hash"]
    version = value.get("version")
    if isinstance(version, bool) or not isinstance(version, (str, int)):
        return [f"{label}: version"]
    return []


def preregistration_issues() -> list[str]:
    approved, review_reasons = validate_fixture_review_gate()
    issues = list(review_reasons)
    if not approved and not issues:
        issues.append("fixture_review_required")
    suite = _load_json(SUITE_PATH)
    expected = _load_json(EXPECTED_PATH)
    prereg = _load_json(PREREGISTRATION_PATH)
    if suite is None:
        issues.append("suite_required")
    if expected is None:
        issues.append("expected_required")
    if prereg is None:
        issues.append("preregistration_required")
    if suite is None or expected is None or prereg is None:
        return sorted(set(issues))

    current_tree = fixture_tree_identity()
    expected_case_hashes = {
        item["path"].removeprefix("cases/").removesuffix(".md"): item["hash"]
        for item in current_tree["files"]
        if item["path"].startswith("cases/")
    }
    if (
        suite.get("schema_version") != "prd-readability-suite.v0.8"
        or suite.get("suite_id") != SUITE_ID
        or suite.get("status") != "PREREGISTERED_AGENT_EVAL_NOT_RUN"
        or suite.get("case_ids") != list(CASE_IDS)
        or suite.get("case_hashes") != expected_case_hashes
        or suite.get("fixture_tree_hash") != TREE_HASH
        or suite.get("evaluator_only_files")
        != [
            "evaluator/expected.json",
            "evaluator/preregistration.json",
            "evaluator/score_results.py",
            "evaluator/evidence_reader.py",
            "run_contract.py",
            "fixture-review/reviewer-a.json",
            "fixture-review/reviewer-b.json",
            "fixture-review/adjudication.json",
        ]
        or suite.get("target_eval_schema")
        != "document-experience-reader-eval.v3.1"
    ):
        issues.append("suite: identity")

    if (
        expected.get("schema_version")
        != "prd-readability-expected-envelope.v0.8"
        or expected.get("suite_id") != SUITE_ID
        or expected.get("custody")
        != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE_OR_REVIEWER_PROJECTION"
        or not isinstance(expected.get("cases"), dict)
        or set(expected["cases"]) != set(CASE_IDS)
    ):
        issues.append("expected: identity")
    for case_id in CASE_IDS:
        oracle = expected.get("cases", {}).get(case_id)
        required_result = (
            "PASS"
            if INTENDED_OBJECTIVES[case_id] == "NO_REPAIR_REQUIRED"
            else "FINDING"
        )
        if not isinstance(oracle, dict) or oracle != {
            "agent_case_id": case_id,
            "required_result": required_result,
            "primary_objective": INTENDED_OBJECTIVES[case_id],
            "allowed_primary_pairs": ALLOWED_PRIMARY_PAIRS[case_id],
        }:
            issues.append(f"expected:{case_id}")

    phase_gate = {
        "case_count": 9,
        "repeats_per_case": 3,
        "required_attempt_count": 27,
        "required_passed_attempt_count": 27,
        "required_passed_repeats_per_case": 3,
    }
    if (
        prereg.get("schema_version") != "prd-readability-preregistration.v0.8"
        or prereg.get("suite_id") != SUITE_ID
        or prereg.get("status") != "PREREGISTERED_BEFORE_RESULTS"
        or prereg.get("freeze_order_authority")
        != "PREREGISTRATION_GIT_COMMIT_PRECEDES_ALL_AGENT_OUTPUTS"
        or "registered_at" in prereg
        or prereg.get("custody")
        != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE_OR_REVIEWER_PROJECTION"
        or prereg.get("fixture_tree") != current_tree
        or prereg.get("mandatory_phases") != list(MANDATORY_PHASES)
        or prereg.get("phase_gate") != phase_gate
        or prereg.get("phase_installed_build_versions") != PHASE_BUILD_VERSIONS
        or prereg.get("cross_phase_fresh_identity_fields")
        != [
            "run_id", "attempt_id", "reviewer_execution_ref.id",
            "author_execution_ref.id", "preregistration_checkpoint_ref",
            "work_order_ref", "output_target", "state_ref", "installed_build_ref",
        ]
        or prereg.get("cross_phase_policy")
        != "BOTH_PHASES_PASS_NO_LATER_PHASE_RESCUE"
        or prereg.get("selection_policy")
        != "ALL_PRODUCED_ATTEMPTS_OCCUPY_DENOMINATOR_NO_BEST_OF_N_NO_REPLACEMENT"
        or prereg.get("threshold_change_after_first_output")
        != "FORBIDDEN_REQUIRES_SUITE_V0.9"
        or prereg.get("manifest_policy")
        != "ONE_CONTROLLER_BOUND_PHASE_MANIFEST_AFTER_27_PREPARES_AND_NULL_RESULTS_BEFORE_AGENT_OUTPUT"
        or prereg.get("manifest_receipt_policy")
        != "WRITE_ONCE_RECEIPT_PLUS_ALL_27_CONTROLLER_STATE_EVENT_TRANSACTION_BINDINGS_REQUIRED"
        or prereg.get("batch_validation_receipt_policy")
        != "ALL_27_ORIGINAL_RAW_BYTES_PUBLICLY_PREFLIGHTED_AND_ACCEPTED_RESULT_HASH_BOUND_BEFORE_FIRST_SUBMISSION"
        or prereg.get("phase_score_contract") != PHASE_SCORE_CONTRACT
        or prereg.get("mechanical_correction_policy")
        != "TWO_STAGE_PUBLIC_PREFLIGHT_SAME_ATTEMPT_AUTHORITY_COPY_FIELDS_ONLY_PRESERVE_ORIGINAL_RAW_BYTES_AND_IDENTICAL_SEMANTIC_PAYLOAD_HASH"
        or prereg.get("agent_runtime_status") != "NOT_RUN"
        or prereg.get("phase_runtime_status")
        != {phase: "NOT_RUN" for phase in MANDATORY_PHASES}
        or prereg.get("real_prd_review_status") != "NOT_RUN"
        or prereg.get("human_reader_validation") != "NOT_RUN"
    ):
        issues.append("preregistration: identity_or_gate")

    exact_suite_refs = {
        "suite_ref": "suite.json",
        "expected_ref": "evaluator/expected.json",
        "scorer_ref": "evaluator/score_results.py",
        "run_contract_ref": "run_contract.py",
        "evidence_reader_ref": "evaluator/evidence_reader.py",
        "fixture_adjudication_ref": "fixture-review/adjudication.json",
    }
    for field, path in exact_suite_refs.items():
        issues.extend(
            _exact_ref_issues(
                prereg.get(field),
                label=f"preregistration.{field}",
                base=ROOT,
                expected_path=path,
            )
        )
    review_refs = prereg.get("fixture_review_refs")
    if not isinstance(review_refs, list) or len(review_refs) != 2:
        issues.append("preregistration: fixture_review_refs")
    else:
        for ref, path in zip(
            review_refs,
            ("fixture-review/reviewer-a.json", "fixture-review/reviewer-b.json"),
            strict=True,
        ):
            issues.extend(
                _exact_ref_issues(
                    ref,
                    label=f"preregistration.{path}",
                    base=ROOT,
                    expected_path=path,
                )
            )
    repo_refs = {
        "profile_ref": "policies/document-experience/PRD_WRITING_PROFILE_v0.5.json",
        "guide_ref": "policies/document-experience/PRD_WRITING_GUIDE_v0.5.md",
        "instruction_ref": "src/core/atomic-skills/prd-writing-eval-review-v3.2/INSTRUCTIONS.md",
        "reviewer_resource_ref": "src/core/reviewer-profiles/prd-writing-eval-reader-review-v3.2.json",
        "output_contract_ref": "src/core/templates/contracts/prd-v0.2.json",
        "result_schema_ref": "src/core/schemas/document-experience-reader-eval-v3.1.schema.json",
    }
    for field, path in repo_refs.items():
        issues.extend(
            _exact_ref_issues(
                suite.get(field),
                label=f"suite.{field}",
                base=REPO_ROOT,
                expected_path=path,
            )
        )
        issues.extend(
            _exact_ref_issues(
                prereg.get(field),
                label=f"preregistration.{field}",
                base=REPO_ROOT,
                expected_path=path,
            )
        )
        if suite.get(field) != prereg.get(field):
            issues.append(f"resource_ref_mismatch: {field}")
    result_files = [
        path
        for path in (ROOT / "results").rglob("*")
        if path.is_file() and path.name != "README.md"
    ]
    if result_files:
        issues.append("semantic_results_exist_before_freeze")
    return sorted(set(issues))


def _ensure_safe_export_target(target: Path) -> None:
    if target.is_symlink():
        raise ValueError("Agent workspace target must not be a symlink")
    absolute = target.absolute()
    resolved = target.resolve()
    for custody in (REPO_ROOT, ROOT):
        for candidate, root in ((absolute, custody.absolute()), (resolved, custody.resolve())):
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            raise ValueError("Agent workspace must remain outside repository and evaluator custody")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("Agent workspace target must be an empty directory")


def _local_ref(path: Path, version: str | int) -> dict[str, Any]:
    return {"path": path.name, "hash": _sha256(path.read_bytes()), "version": version}


def emit_agent_workspace(target: Path) -> None:
    issues = preregistration_issues()
    if issues:
        raise ValueError("; ".join(issues))
    _ensure_safe_export_target(target)
    target.mkdir(parents=True, exist_ok=True)
    suite = _load_json(SUITE_PATH)
    expected = _load_json(EXPECTED_PATH)
    prereg = _load_json(PREREGISTRATION_PATH)
    assert suite is not None and expected is not None and prereg is not None
    for semantic_case_id in CASE_IDS:
        agent_case_id = expected["cases"][semantic_case_id]["agent_case_id"]
        case_root = target / agent_case_id
        case_root.mkdir()
        payload = build_agent_case_payload(semantic_case_id)
        candidate_path = case_root / "candidate.md"
        candidate_path.write_text(payload["candidate_markdown"], encoding="utf-8")
        for field, export_name in AGENT_RESOURCE_EXPORTS:
            source_ref = prereg[field]
            source = REPO_ROOT / source_ref["path"]
            destination = case_root / export_name
            shutil.copyfile(source, destination)
        if payload["asset_payloads"]:
            assets_root = case_root / "assets"
            assets_root.mkdir()
            for name, content in payload["asset_payloads"].items():
                (assets_root / name).write_bytes(content)
        manifest = {
            "schema_version": "prd-readability-agent-case.v0.4",
            "suite_id": suite["suite_id"],
            "case_id": agent_case_id,
            "candidate_ref": _local_ref(candidate_path, 1),
            "target_eval_schema": "document-experience-reader-eval.v3.1",
            "evaluator_files_included": False,
            "agent_runtime_status": "NOT_RUN",
            "claim_boundary": "Anonymous staging is not Writing Reviewer execution or scoring.",
        }
        (case_root / "case-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        export_files = []
        for path in sorted(case_root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            export_files.append(
                {
                    "path": path.relative_to(case_root).as_posix(),
                    "hash": _sha256(path.read_bytes()),
                    "size": path.stat().st_size,
                }
            )
        export_manifest = {
            "schema_version": "prd-readability-v0.8-canonical-export.v1",
            "suite_id": SUITE_ID,
            "case_id": agent_case_id,
            "files": export_files,
            "evaluator_files_included": False,
        }
        (case_root / "canonical-export-manifest.json").write_text(
            json.dumps(export_manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )


def _shape_ref_issues(value: Any, label: str) -> list[str]:
    if not isinstance(value, dict) or set(value) != EXACT_REF_FIELDS:
        return [f"{label}:closed_exact_ref"]
    issues: list[str] = []
    path = value.get("path")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
    ):
        issues.append(f"{label}:path")
    if (
        not isinstance(value.get("hash"), str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", value["hash"]) is None
    ):
        issues.append(f"{label}:hash")
    version = value.get("version")
    if isinstance(version, bool) or not isinstance(version, (str, int)):
        issues.append(f"{label}:version")
    return issues


def _shape_execution_ref_issues(value: Any, label: str, kind: str) -> list[str]:
    if (
        not isinstance(value, dict)
        or set(value) != EXECUTION_REF_FIELDS
        or value.get("kind") != kind
        or not isinstance(value.get("id"), str)
        or not value["id"].strip()
    ):
        return [label]
    return []


def execution_manifest_shape_issues(value: Any) -> list[str]:
    """Validate the closed, phase-bound 27-attempt manifest denominator."""

    if not isinstance(value, dict) or set(value) != MANIFEST_FIELDS:
        return ["closed_execution_manifest"]
    issues: list[str] = []
    if value.get("schema_version") != "prd-readability-v0.8-execution-manifest.v1":
        issues.append("schema_version")
    if value.get("status") != "FROZEN_BEFORE_AGENT_OUTPUT":
        issues.append("status")
    if value.get("suite_id") != SUITE_ID:
        issues.append("suite_id")
    phase = value.get("phase")
    if phase not in MANDATORY_PHASES:
        issues.append("phase")
    root_identity = value.get("central_project_root")
    if (
        not isinstance(root_identity, dict)
        or set(root_identity) != {"path", "device", "inode"}
        or not isinstance(root_identity.get("path"), str)
        or not isinstance(root_identity.get("device"), int)
        or not isinstance(root_identity.get("inode"), int)
    ):
        issues.append("central_project_root")
    build = value.get("installed_build_ref")
    issues.extend(_shape_ref_issues(build, "installed_build_ref"))
    if isinstance(build, dict) and build.get("version") != PHASE_BUILD_VERSIONS.get(phase):
        issues.append("phase_installed_build_version")
    if (
        value.get("required_attempt_count") != 27
        or value.get("result_ref_null_count_at_freeze") != 27
        or value.get("agent_output_count_at_freeze") != 0
    ):
        issues.append("freeze_counts")
    entries = value.get("entries")
    if not isinstance(entries, list) or len(entries) != 27:
        return sorted(set(issues + ["required_attempt_count"]))
    coverage: dict[str, list[int]] = {case_id: [] for case_id in CASE_IDS}
    unique_fields: dict[str, list[Any]] = {
        field: [] for field in ("run_id", "attempt_id", "output_target")
    }
    reviewer_ids: list[Any] = []
    author_ids: list[Any] = []
    exact_ref_paths: dict[str, list[Any]] = {
        field: []
        for field in (
            "preregistration_checkpoint_ref", "work_order_ref", "state_ref"
        )
    }
    for ordinal, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) != MANIFEST_ENTRY_FIELDS:
            issues.append(f"entry_{ordinal}:closed")
            continue
        case_id = entry.get("semantic_case_id")
        repeat = entry.get("repeat_index")
        if (
            entry.get("ordinal") != ordinal
            or entry.get("suite_id") != SUITE_ID
            or entry.get("phase") != phase
            or entry.get("agent_case_id") != case_id
            or case_id not in CASE_IDS
            or repeat not in {1, 2, 3}
        ):
            issues.append(f"entry_{ordinal}:identity")
        else:
            coverage[case_id].append(repeat)
        if entry.get("central_project_root") != root_identity:
            issues.append(f"entry_{ordinal}:central_project_root")
        if entry.get("installed_build_ref") != build:
            issues.append(f"entry_{ordinal}:installed_build_ref")
        issues.extend(
            _shape_execution_ref_issues(
                entry.get("reviewer_execution_ref"),
                f"entry_{ordinal}:reviewer_execution_ref",
                "HOST_SUBAGENT_ATTEMPT",
            )
        )
        issues.extend(
            _shape_execution_ref_issues(
                entry.get("author_execution_ref"),
                f"entry_{ordinal}:author_execution_ref",
                "HOST_AGENT_ATTEMPT",
            )
        )
        for field in (
            "preregistration_checkpoint_ref",
            "work_order_ref",
            "state_ref",
        ):
            issues.extend(_shape_ref_issues(entry.get(field), f"entry_{ordinal}:{field}"))
        for field in unique_fields:
            unique_fields[field].append(entry.get(field))
        reviewer = entry.get("reviewer_execution_ref")
        reviewer_ids.append(reviewer.get("id") if isinstance(reviewer, dict) else None)
        author = entry.get("author_execution_ref")
        author_ids.append(author.get("id") if isinstance(author, dict) else None)
        for field in exact_ref_paths:
            ref = entry.get(field)
            exact_ref_paths[field].append(
                ref.get("path") if isinstance(ref, dict) else None
            )
    for case_id, repeats in coverage.items():
        if sorted(repeats) != [1, 2, 3]:
            issues.append(f"repeat_coverage:{case_id}")
    for field, values in unique_fields.items():
        if (
            any(not isinstance(item, str) or not item for item in values)
            or len(values) != len(set(values))
        ):
            issues.append(f"duplicate_{field}")
    if len(reviewer_ids) != len(set(reviewer_ids)):
        issues.append("duplicate_reviewer_id")
    if len(author_ids) != len(set(author_ids)):
        issues.append("duplicate_author_id")
    for field, paths in exact_ref_paths.items():
        if len(paths) != len(set(paths)):
            issues.append(f"duplicate_{field}_path")
    return sorted(set(issues))


def cross_phase_freshness_issues(
    rc_manifest: Any, final_manifest: Any
) -> list[str]:
    """Require two valid phase manifests with 54 fresh execution identities."""

    issues = [
        f"RC_CANDIDATE:{issue}"
        for issue in execution_manifest_shape_issues(rc_manifest)
    ]
    issues.extend(
        f"FINAL_PUBLIC_ARTIFACT:{issue}"
        for issue in execution_manifest_shape_issues(final_manifest)
    )
    if not isinstance(rc_manifest, dict) or not isinstance(final_manifest, dict):
        return sorted(set(issues + ["cross_phase_manifest_shape"]))
    if rc_manifest.get("phase") != "RC_CANDIDATE" or final_manifest.get("phase") != "FINAL_PUBLIC_ARTIFACT":
        issues.append("cross_phase_phase_order")
    if rc_manifest.get("installed_build_ref") == final_manifest.get("installed_build_ref"):
        issues.append("cross_phase_build_identity_reuse")
    rc_entries = rc_manifest.get("entries", [])
    final_entries = final_manifest.get("entries", [])
    field_labels = {
        "run_id": "run_id",
        "attempt_id": "attempt_id",
        "output_target": "output_target",
    }
    for field, label in field_labels.items():
        rc_values = {entry.get(field) for entry in rc_entries if isinstance(entry, dict)}
        final_values = {entry.get(field) for entry in final_entries if isinstance(entry, dict)}
        if rc_values & final_values:
            issues.append(f"cross_phase_{label}_reuse")
    rc_reviewers = {
        entry.get("reviewer_execution_ref", {}).get("id")
        for entry in rc_entries
        if isinstance(entry, dict) and isinstance(entry.get("reviewer_execution_ref"), dict)
    }
    final_reviewers = {
        entry.get("reviewer_execution_ref", {}).get("id")
        for entry in final_entries
        if isinstance(entry, dict) and isinstance(entry.get("reviewer_execution_ref"), dict)
    }
    if rc_reviewers & final_reviewers:
        issues.append("cross_phase_reviewer_id_reuse")
    nested_fields = {
        "author_execution_ref": ("id", "author_id"),
        "preregistration_checkpoint_ref": ("path", "checkpoint_ref"),
        "work_order_ref": ("path", "work_order_ref"),
        "state_ref": ("path", "state_ref"),
    }
    for field, (member, label) in nested_fields.items():
        rc_values = {
            entry.get(field, {}).get(member)
            for entry in rc_entries
            if isinstance(entry, dict) and isinstance(entry.get(field), dict)
        }
        final_values = {
            entry.get(field, {}).get(member)
            for entry in final_entries
            if isinstance(entry, dict) and isinstance(entry.get(field), dict)
        }
        if rc_values & final_values:
            issues.append(f"cross_phase_{label}_reuse")
    return sorted(set(issues))


def _project_path(project_root: Path, relative: str, label: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"{label} must be a safe project-relative path")
    root = project_root.resolve(strict=True)
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes the central project root") from error
    return resolved


def _phase_manifest_path(project_root: Path, phase: str) -> Path:
    return (
        project_root.resolve(strict=True)
        / ".better-product-graph"
        / "writing-evals"
        / "execution-manifests"
        / f"{phase}.json"
    )


def _manifest_receipt_path(project_root: Path, phase: str) -> Path:
    return _phase_manifest_path(project_root, phase).with_name(
        f"{phase}.manifest-receipt.json"
    )


def _batch_receipt_path(project_root: Path, phase: str) -> Path:
    return _phase_manifest_path(project_root, phase).with_name(
        f"{phase}.batch-validation-receipt.json"
    )


def _write_once_receipt(path: Path, value: dict[str, Any], label: str) -> None:
    content = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ValueError(f"{label} write-once identity conflict")
        return
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _manifest_ref(project_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    path = _phase_manifest_path(project_root, manifest["phase"])
    return {
        "path": path.relative_to(project_root.resolve(strict=True)).as_posix(),
        "hash": _sha256(path.read_bytes()),
        "version": 1,
    }


def _bound_manifest_state(
    project_root: Path,
    manifest: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    """Read one post-bind state and prove its pre-bind state_ref/transition anchor."""

    root = project_root.resolve(strict=True)
    state_ref = entry["state_ref"]
    state_path = _project_path(root, state_ref["path"], "state_ref")
    if state_path.is_symlink() or not state_path.is_file():
        raise ValueError("bound state is missing or unsafe")
    state = _load_json(state_path)
    manifest_ref = _manifest_ref(root, manifest)
    if (
        not isinstance(state, dict)
        or state.get("run_id") != entry["run_id"]
        or state.get("status") != "ACTIVE"
        or state.get("result_ref") is not None
        or state.get("phase_manifest_binding")
        != {"phase": manifest["phase"], "manifest_ref": manifest_ref}
    ):
        raise ValueError("bound state differs from exact phase manifest")
    transition_path = (
        state_path.parent
        / "transactions"
        / (
            f"bind_manifest-{entry['attempt_id']}-"
            f"v{state_ref['version'] + 1}.json"
        )
    )
    if transition_path.is_symlink() or not transition_path.is_file():
        raise ValueError("Controller manifest-binding transition is missing")
    transition = _load_json(transition_path)
    base_state = json.loads(json.dumps(state))
    base_state["phase_manifest_binding"] = None
    base_state["state_version"] = state_ref["version"]
    base_bytes = (
        json.dumps(
            base_state,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    event = transition.get("target_event") if isinstance(transition, dict) else None
    if (
        not isinstance(transition, dict)
        or transition.get("schema_version") != "writing-eval-transition.v1"
        or transition.get("status") != "COMMITTED"
        or transition.get("kind") != "bind_manifest"
        or transition.get("run_id") != entry["run_id"]
        or transition.get("attempt_id") != entry["attempt_id"]
        or transition.get("base_state_hash") != _sha256(base_bytes[:-1])
        or transition.get("target_state") != state
        or transition.get("target_state_hash")
        != _sha256(
            json.dumps(
                state,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        or not isinstance(event, dict)
        or event.get("event_type") != "WRITING_EVAL_PHASE_MANIFEST_BOUND"
        or event.get("phase") != manifest["phase"]
        or event.get("manifest_ref") != manifest_ref
        or state_ref["hash"] != _sha256(base_bytes)
    ):
        raise ValueError("Controller manifest-binding transition is invalid")
    return state


def _freeze_manifest_receipt(project_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    receipt = {
        "schema_version": "prd-readability-v0.8-manifest-receipt.v1",
        "status": "WRITE_ONCE_LOCKED_BEFORE_AGENT_OUTPUT",
        "suite_id": SUITE_ID,
        "phase": manifest["phase"],
        "central_project_root": manifest["central_project_root"],
        "installed_build_ref": manifest["installed_build_ref"],
        "manifest_ref": _manifest_ref(project_root, manifest),
    }
    _write_once_receipt(
        _manifest_receipt_path(project_root, manifest["phase"]),
        receipt,
        "phase manifest receipt",
    )
    return receipt


def verify_phase_manifest_receipt(
    project_root: Path, manifest: dict[str, Any]
) -> list[str]:
    issues = execution_manifest_shape_issues(manifest)
    if issues:
        return [f"execution_manifest:{issue}" for issue in issues]
    root = project_root.resolve(strict=True)
    path = _phase_manifest_path(root, manifest["phase"])
    receipt_path = _manifest_receipt_path(root, manifest["phase"])
    if path.is_symlink() or not path.is_file():
        return ["phase_manifest_missing"]
    try:
        durable = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["phase_manifest_invalid_json"]
    if durable != manifest:
        issues.append("phase_manifest_argument_differs_from_durable")
    receipt = _load_json(receipt_path)
    expected = {
        "schema_version": "prd-readability-v0.8-manifest-receipt.v1",
        "status": "WRITE_ONCE_LOCKED_BEFORE_AGENT_OUTPUT",
        "suite_id": SUITE_ID,
        "phase": manifest["phase"],
        "central_project_root": manifest["central_project_root"],
        "installed_build_ref": manifest["installed_build_ref"],
        "manifest_ref": {
            "path": path.relative_to(root).as_posix(),
            "hash": _sha256(path.read_bytes()),
            "version": 1,
        },
    }
    if receipt != expected:
        issues.append("phase_manifest_receipt_hash_or_identity")
    return sorted(set(issues))


def freeze_execution_manifest(
    project_root: Path,
    phase: str,
    installed_build_ref: dict[str, Any],
    registrations: list[dict[str, Any]],
    *,
    runtime: Any,
) -> dict[str, Any]:
    """Write once after all 27 durable prepares and before any Agent output."""

    if preregistration_issues():
        raise ValueError("frozen suite contract is invalid")
    root = project_root.resolve(strict=True)
    if phase not in MANDATORY_PHASES:
        raise ValueError("phase is not preregistered")
    if _shape_ref_issues(installed_build_ref, "installed_build_ref"):
        raise ValueError("installed_build_ref is invalid")
    if not isinstance(registrations, list) or len(registrations) != 27:
        raise ValueError("all 27 registrations are required before manifest freeze")
    root_stat = root.stat()
    root_identity = {
        "path": str(root),
        "device": root_stat.st_dev,
        "inode": root_stat.st_ino,
    }
    entries: list[dict[str, Any]] = []
    required_registration_fields = {
        "semantic_case_id", "repeat_index", "run_id",
        "reviewer_execution_ref", "work_order_ref", "output_target",
    }
    for ordinal, registration in enumerate(registrations, 1):
        if not isinstance(registration, dict) or set(registration) != required_registration_fields:
            raise ValueError(f"registration {ordinal} is not closed")
        run_id = registration["run_id"]
        if not isinstance(run_id, str) or re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id
        ) is None:
            raise ValueError(f"registration {ordinal} run_id is invalid")
        state_path = (
            root / ".better-product-graph" / "writing-evals" / run_id / "state.json"
        )
        state = _load_json(state_path)
        if state is None:
            raise ValueError(f"registration {ordinal} durable state is missing")
        dispatch = state.get("dispatch")
        context = (
            dispatch.get("writing_eval_context") if isinstance(dispatch, dict) else None
        )
        if (
            state.get("run_id") != run_id
            or state.get("suite_id") != SUITE_ID
            or state.get("case_id") != registration.get("semantic_case_id")
            or state.get("status") != "ACTIVE"
            or state.get("result_ref") is not None
            or state.get("superseded_attempts") != []
            or not isinstance(dispatch, dict)
            or dispatch.get("status") != "DISPATCHED"
            or not isinstance(context, dict)
            or context.get("installed_build_ref") != installed_build_ref
        ):
            raise ValueError(
                f"registration {ordinal} was not one exact null-result prepare"
            )
        work_order_ref = registration["work_order_ref"]
        if _shape_ref_issues(work_order_ref, f"registration_{ordinal}.work_order_ref"):
            raise ValueError(f"registration {ordinal} work order ref is invalid")
        work_order_path = _project_path(root, work_order_ref["path"], "work_order_ref")
        if (
            work_order_path.is_symlink()
            or not work_order_path.is_file()
            or _sha256(work_order_path.read_bytes()) != work_order_ref["hash"]
        ):
            raise ValueError(f"registration {ordinal} work order is stale")
        work_order = _load_json(work_order_path)
        output_target = registration["output_target"]
        output_path = _project_path(root, output_target, "output_target")
        if output_path.exists() or output_path.is_symlink():
            raise ValueError(f"registration {ordinal} Agent output already exists")
        entry = {
            "ordinal": ordinal,
            "suite_id": SUITE_ID,
            "phase": phase,
            "semantic_case_id": registration["semantic_case_id"],
            "agent_case_id": state["case_id"],
            "repeat_index": registration["repeat_index"],
            "run_id": run_id,
            "attempt_id": dispatch["attempt_id"],
            "reviewer_execution_ref": registration["reviewer_execution_ref"],
            "author_execution_ref": state.get("prepare_payload", {}).get(
                "author_execution_ref"
            ),
            "preregistration_checkpoint_ref": state.get(
                "preregistration_checkpoint_ref"
            ),
            "work_order_ref": work_order_ref,
            "output_target": output_target,
            "central_project_root": root_identity,
            "state_ref": {
                "path": state_path.relative_to(root).as_posix(),
                "hash": _sha256(state_path.read_bytes()),
                "version": state.get("state_version"),
            },
            "installed_build_ref": installed_build_ref,
        }
        work_order_issues = _reviewer_work_order_issues(
            work_order, entry=entry, state=state
        )
        if work_order_issues:
            raise ValueError(
                f"registration {ordinal} closed reviewer work order is invalid: "
                + ",".join(work_order_issues)
            )
        entries.append(entry)
    manifest = {
        "schema_version": "prd-readability-v0.8-execution-manifest.v1",
        "status": "FROZEN_BEFORE_AGENT_OUTPUT",
        "suite_id": SUITE_ID,
        "phase": phase,
        "central_project_root": root_identity,
        "installed_build_ref": installed_build_ref,
        "required_attempt_count": 27,
        "result_ref_null_count_at_freeze": 27,
        "agent_output_count_at_freeze": 0,
        "entries": entries,
    }
    shape_issues = execution_manifest_shape_issues(manifest)
    if shape_issues:
        raise ValueError("execution manifest is invalid: " + ",".join(shape_issues))
    path = _phase_manifest_path(root, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ValueError("write-once execution manifest identity conflict")
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    manifest_ref = _manifest_ref(root, manifest)
    if not callable(getattr(runtime, "bind_phase_manifest", None)):
        raise ValueError("execution manifest requires Controller binding authority")
    for entry in manifest["entries"]:
        runtime.bind_phase_manifest(entry["run_id"], phase, manifest_ref)
    for entry in manifest["entries"]:
        bound_state = runtime.read_state(entry["run_id"])
        if bound_state.get("phase_manifest_binding") != {
            "phase": phase,
            "manifest_ref": manifest_ref,
        }:
            raise ValueError("all 27 Runs must bind the same exact phase manifest")
    _freeze_manifest_receipt(root, manifest)
    return manifest


def _copied_result_authority(
    state: dict[str, Any], entry: dict[str, Any]
) -> dict[str, Any]:
    dispatch = state["dispatch"]
    context = dispatch["writing_eval_context"]
    return {
        "schema_version": "document-experience-reader-eval.v3.1",
        "evaluation_only": True,
        "authority": "ADVISORY_ONLY",
        "suite_id": context["suite_id"],
        "case_id": context["case_id"],
        "node_id": "writing-eval.review",
        "attempt_id": dispatch["attempt_id"],
        "instruction_ref": dispatch["instruction_ref"],
        "instruction_hash": dispatch["instruction_hash"],
        "input_refs": dispatch["input_refs"],
        "input_hashes": dispatch["input_hashes"],
        "preregistration_checkpoint_ref": entry["preregistration_checkpoint_ref"],
        "candidate_ref": context["candidate_ref"],
        "profile_ref": context["profile_ref"],
        "guide_ref": context["guide_ref"],
        "reviewer_resource_ref": context["reviewer_resource_ref"],
        "output_contract_ref": context["output_contract_ref"],
        "author_execution_ref": context["author_execution_ref"],
        "reviewer_execution_ref": entry["reviewer_execution_ref"],
        "reviewer_role": "writing_standard",
        "isolated_input_refs": context["isolated_input_refs"],
        "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
    }


def _correction_paths(raw_path: Path) -> tuple[Path, Path, Path]:
    return (
        raw_path.with_name(raw_path.name + ".preflight-rejection.json"),
        raw_path.with_name(raw_path.name + ".corrected.json"),
        raw_path.with_name(raw_path.name + ".mechanical-correction.json"),
    )


def _path_ref(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": _sha256(path.read_bytes()),
        "version": 1,
    }


def preflight_raw_output_batch(
    project_root: Path,
    manifest: dict[str, Any],
) -> list[str]:
    """Publicly preflight all 27 bytes without submitting any result to a Run."""

    issues = execution_manifest_shape_issues(manifest)
    if issues:
        return [f"execution_manifest:{issue}" for issue in issues]
    root = project_root.resolve(strict=True)
    root_stat = root.stat()
    if manifest["central_project_root"] != {
        "path": str(root),
        "device": root_stat.st_dev,
        "inode": root_stat.st_ino,
    }:
        return ["central_project_root"]
    raw_paths = [
        _project_path(root, entry["output_target"], "output_target")
        for entry in manifest["entries"]
    ]
    if any(path.is_symlink() or not path.is_file() for path in raw_paths):
        return ["all_27_raw_outputs_required_before_first_submission"]
    evidence_reader = _load_evidence_reader()
    for entry, path in zip(manifest["entries"], raw_paths, strict=True):
        try:
            original_bytes = path.read_bytes()
            value = json.loads(original_bytes.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            issues.append(f"raw_output_invalid_json:{entry['ordinal']}")
            continue
        if not isinstance(value, dict):
            issues.append(f"raw_output_not_object:{entry['ordinal']}")
            continue
        try:
            state = _bound_manifest_state(root, manifest, entry)
            dispatch = state.get("dispatch")
            context = dispatch.get("writing_eval_context") if isinstance(dispatch, dict) else None
            if (
                state.get("run_id") != entry["run_id"]
                or state.get("status") != "ACTIVE"
                or state.get("result_ref") is not None
                or not isinstance(dispatch, dict)
                or dispatch.get("status") != "DISPATCHED"
                or dispatch.get("attempt_id") != entry["attempt_id"]
                or not isinstance(context, dict)
                or context.get("installed_build_ref") != entry["installed_build_ref"]
            ):
                raise ValueError("prepared state authority differs from manifest")
            durable_dispatch = dict(dispatch)
            durable_dispatch.pop("status", None)
            candidate_ref = context["candidate_ref"]
            candidate_path = _project_path(root, candidate_ref["path"], "candidate_ref")
            candidate_bytes = candidate_path.read_bytes()
            work_order_path = _project_path(
                root, entry["work_order_ref"]["path"], "work_order_ref"
            )
            if (
                work_order_path.is_symlink()
                or not work_order_path.is_file()
                or _sha256(work_order_path.read_bytes()) != entry["work_order_ref"]["hash"]
            ):
                raise ValueError("work_order_ref is stale")
            work_order_issues = _reviewer_work_order_issues(
                _load_json(work_order_path), entry=entry, state=state
            )
            if work_order_issues:
                raise ValueError(";".join(work_order_issues))
            rejection_path, corrected_path, correction_path = _correction_paths(path)
            try:
                validated = evidence_reader["validate_raw_result"](
                    value,
                    dispatch=durable_dispatch,
                    checkpoint_ref=entry["preregistration_checkpoint_ref"],
                    candidate_bytes=candidate_bytes,
                )
                if (
                    validated["reviewer_execution_ref"]
                    != entry["reviewer_execution_ref"]
                ):
                    raise ValueError(
                        "reviewer_execution_ref differs from manifest"
                    )
            except ValueError as raw_error:
                authority = _copied_result_authority(state, entry)
                if not isinstance(value, dict):
                    raise raw_error
                corrected_expected = json.loads(json.dumps(value))
                changed_values = {
                    field: expected
                    for field, expected in authority.items()
                    if corrected_expected.get(field) != expected
                }
                if not changed_values or any(
                    field not in MECHANICAL_AUTHORITY_FIELDS
                    for field in changed_values
                ):
                    raise raw_error
                for field, expected in changed_values.items():
                    corrected_expected[field] = expected
                expected_validated = evidence_reader["validate_raw_result"](
                    corrected_expected,
                    dispatch=durable_dispatch,
                    checkpoint_ref=entry["preregistration_checkpoint_ref"],
                    candidate_bytes=candidate_bytes,
                )
                if (
                    expected_validated["reviewer_execution_ref"]
                    != entry["reviewer_execution_ref"]
                ):
                    raise raw_error
                expected_corrected_bytes = (
                    json.dumps(
                        corrected_expected,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                    + b"\n"
                )
                expected_correction = mechanical_correction_record(
                    original_bytes, expected_corrected_bytes, changed_values
                )
                rejection = {
                    "schema_version": "prd-readability-v0.8-public-preflight-rejection.v1",
                    "status": "AUTHORITY_ONLY_REJECTED_NO_RUN_SUBMISSION",
                    "suite_id": SUITE_ID,
                    "phase": manifest["phase"],
                    "ordinal": entry["ordinal"],
                    "run_id": entry["run_id"],
                    "attempt_id": entry["attempt_id"],
                    "original_raw_ref": _path_ref(root, path),
                    "semantic_payload_hash": expected_correction[
                        "semantic_payload_hash_before"
                    ],
                    "copied_authority_values": changed_values,
                }
                _write_once_receipt(
                    rejection_path, rejection, "public preflight rejection"
                )
                if (
                    corrected_path.is_symlink()
                    or not corrected_path.is_file()
                    or correction_path.is_symlink()
                    or not correction_path.is_file()
                ):
                    issues.append(
                        f"mechanical_correction_required:{entry['ordinal']}"
                    )
                    continue
                corrected_bytes = corrected_path.read_bytes()
                corrected_value = json.loads(corrected_bytes.decode("utf-8"))
                corrected_validated = evidence_reader["validate_raw_result"](
                    corrected_value,
                    dispatch=durable_dispatch,
                    checkpoint_ref=entry["preregistration_checkpoint_ref"],
                    candidate_bytes=candidate_bytes,
                )
                if corrected_validated != expected_validated:
                    raise ValueError("mechanical correction semantic payload differs")
                expected_record = mechanical_correction_record(
                    original_bytes, corrected_bytes, changed_values
                )
                if (
                    expected_record["semantic_payload_hash_before"]
                    != rejection["semantic_payload_hash"]
                    or _load_json(correction_path) != expected_record
                    or _load_json(rejection_path) != rejection
                ):
                    raise ValueError("mechanical correction record is invalid")
            else:
                if any(
                    candidate.exists() or candidate.is_symlink()
                    for candidate in (rejection_path, corrected_path, correction_path)
                ):
                    raise ValueError(
                        "valid raw output cannot carry correction sidecars"
                    )
        except (KeyError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            issues.append(f"raw_result_contract:{entry['ordinal']}:{error}")
    return sorted(set(issues))


def validate_raw_output_batch_before_submission(
    project_root: Path,
    manifest: dict[str, Any],
) -> list[str]:
    """Compatibility name for the public non-submitting batch preflight."""

    return preflight_raw_output_batch(project_root, manifest)


def write_batch_validation_receipt(
    project_root: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Write once only after every full raw v3.1 result passes the frozen barrier."""

    receipt_issues = verify_phase_manifest_receipt(project_root, manifest)
    if receipt_issues:
        raise ValueError("phase manifest receipt invalid: " + ",".join(receipt_issues))
    batch_issues = validate_raw_output_batch_before_submission(project_root, manifest)
    if batch_issues:
        raise ValueError("raw output batch invalid: " + ",".join(batch_issues))
    root = project_root.resolve(strict=True)
    entries = []
    for entry in manifest["entries"]:
        path = _project_path(root, entry["output_target"], "output_target")
        rejection_path, corrected_path, correction_path = _correction_paths(path)
        corrected = rejection_path.is_file() and not rejection_path.is_symlink()
        accepted_path = corrected_path if corrected else path
        entries.append(
            {
                "ordinal": entry["ordinal"],
                "run_id": entry["run_id"],
                "attempt_id": entry["attempt_id"],
                "reviewer_execution_ref": entry["reviewer_execution_ref"],
                "original_raw_ref": _path_ref(root, path),
                "accepted_result_ref": _path_ref(root, accepted_path),
                "preflight_rejection_ref": (
                    _path_ref(root, rejection_path) if corrected else None
                ),
                "mechanical_correction_ref": (
                    _path_ref(root, correction_path) if corrected else None
                ),
            }
        )
    receipt = {
        "schema_version": "prd-readability-v0.8-batch-validation-receipt.v1",
        "status": "ALL_27_FULL_RAW_RESULTS_VALIDATED_BEFORE_FIRST_SUBMISSION",
        "suite_id": SUITE_ID,
        "phase": manifest["phase"],
        "manifest_ref": _manifest_ref(root, manifest),
        "required_attempt_count": 27,
        "entries": entries,
    }
    _write_once_receipt(
        _batch_receipt_path(root, manifest["phase"]),
        receipt,
        "batch-validation receipt",
    )
    return receipt


def verify_batch_validation_receipt(
    project_root: Path, manifest: dict[str, Any]
) -> list[str]:
    issues = verify_phase_manifest_receipt(project_root, manifest)
    if issues:
        return issues
    root = project_root.resolve(strict=True)
    receipt = _load_json(_batch_receipt_path(root, manifest["phase"]))
    if not isinstance(receipt, dict):
        return ["batch_validation_receipt_missing"]
    if (
        set(receipt)
        != {
            "schema_version", "status", "suite_id", "phase", "manifest_ref",
            "required_attempt_count", "entries",
        }
        or receipt.get("schema_version")
        != "prd-readability-v0.8-batch-validation-receipt.v1"
        or receipt.get("status")
        != "ALL_27_FULL_RAW_RESULTS_VALIDATED_BEFORE_FIRST_SUBMISSION"
        or receipt.get("suite_id") != SUITE_ID
        or receipt.get("phase") != manifest["phase"]
        or receipt.get("manifest_ref") != _manifest_ref(root, manifest)
        or receipt.get("required_attempt_count") != 27
        or not isinstance(receipt.get("entries"), list)
        or len(receipt["entries"]) != 27
    ):
        return ["batch_validation_receipt_identity"]
    by_ordinal = {
        item.get("ordinal"): item for item in receipt["entries"] if isinstance(item, dict)
    }
    if len(by_ordinal) != 27:
        return ["batch_validation_receipt_coverage"]
    for entry in manifest["entries"]:
        item = by_ordinal.get(entry["ordinal"])
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "ordinal", "run_id", "attempt_id", "reviewer_execution_ref",
                "original_raw_ref", "accepted_result_ref",
                "preflight_rejection_ref", "mechanical_correction_ref",
            }
            or item.get("run_id") != entry["run_id"]
            or item.get("attempt_id") != entry["attempt_id"]
            or item.get("reviewer_execution_ref") != entry["reviewer_execution_ref"]
        ):
            issues.append(f"batch_validation_receipt_entry:{entry['ordinal']}")
            continue
        raw_ref = item.get("original_raw_ref")
        if (
            not isinstance(raw_ref, dict)
            or raw_ref.get("path") != entry["output_target"]
            or _shape_ref_issues(raw_ref, "raw_output_ref")
        ):
            issues.append(f"batch_validation_original_raw_ref:{entry['ordinal']}")
            continue
        raw_path = _project_path(root, raw_ref["path"], "raw_output_ref")
        if raw_path.is_symlink() or not raw_path.is_file() or _sha256(raw_path.read_bytes()) != raw_ref["hash"]:
            issues.append(f"batch_validation_original_raw_hash:{entry['ordinal']}")
            continue
        accepted_ref = item.get("accepted_result_ref")
        if _shape_ref_issues(accepted_ref, "accepted_result_ref"):
            issues.append(f"batch_validation_accepted_ref:{entry['ordinal']}")
            continue
        accepted_path = _project_path(
            root, accepted_ref["path"], "accepted_result_ref"
        )
        if (
            accepted_path.is_symlink()
            or not accepted_path.is_file()
            or _sha256(accepted_path.read_bytes()) != accepted_ref["hash"]
        ):
            issues.append(f"batch_validation_accepted_hash:{entry['ordinal']}")
            continue
        rejection_ref = item.get("preflight_rejection_ref")
        correction_ref = item.get("mechanical_correction_ref")
        if accepted_ref == raw_ref:
            if rejection_ref is not None or correction_ref is not None:
                issues.append(f"batch_validation_unexpected_correction:{entry['ordinal']}")
        else:
            expected_rejection_path, expected_corrected_path, expected_correction_path = (
                _correction_paths(raw_path)
            )
            if accepted_path != expected_corrected_path:
                issues.append(f"batch_validation_corrected_path:{entry['ordinal']}")
            for label, ref in (
                ("preflight_rejection", rejection_ref),
                ("mechanical_correction", correction_ref),
            ):
                if _shape_ref_issues(ref, label):
                    issues.append(f"batch_validation_{label}_ref:{entry['ordinal']}")
                    continue
                ref_path = _project_path(root, ref["path"], label)
                expected_ref_path = (
                    expected_rejection_path
                    if label == "preflight_rejection"
                    else expected_correction_path
                )
                if (
                    ref_path != expected_ref_path
                    or
                    ref_path.is_symlink()
                    or not ref_path.is_file()
                    or _sha256(ref_path.read_bytes()) != ref["hash"]
                ):
                    issues.append(f"batch_validation_{label}_hash:{entry['ordinal']}")
    return sorted(set(issues))


def mechanical_correction_record(
    original_raw_bytes: bytes,
    corrected_raw_bytes: bytes,
    copied_authority_values: dict[str, Any],
) -> dict[str, Any]:
    """Prove a same-attempt correction changed only copied authority fields."""

    try:
        original = json.loads(original_raw_bytes.decode("utf-8"))
        corrected = json.loads(corrected_raw_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("mechanical correction raw bytes must be JSON objects") from error
    if (
        not isinstance(original, dict)
        or not isinstance(corrected, dict)
        or set(original) != set(corrected)
    ):
        raise ValueError("mechanical correction must preserve the closed payload shape")
    changed = sorted(field for field in original if original[field] != corrected[field])
    if not changed:
        raise ValueError("mechanical correction must change an authority field")
    if any(field not in MECHANICAL_AUTHORITY_FIELDS for field in changed):
        raise ValueError("mechanical correction changed semantic payload")
    if set(copied_authority_values) != set(changed) or any(
        corrected[field] != copied_authority_values[field] for field in changed
    ):
        raise ValueError("mechanical correction does not equal copied authority fields")
    semantic_before = {
        field: value
        for field, value in original.items()
        if field not in MECHANICAL_AUTHORITY_FIELDS
    }
    semantic_after = {
        field: value
        for field, value in corrected.items()
        if field not in MECHANICAL_AUTHORITY_FIELDS
    }
    before_hash = _sha256(
        json.dumps(
            semantic_before,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    after_hash = _sha256(
        json.dumps(
            semantic_after,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    if before_hash != after_hash:
        raise ValueError("mechanical correction changed semantic payload")
    return {
        "schema_version": "prd-readability-v0.8-mechanical-correction.v1",
        "status": "AUTHORITY_COPY_ONLY",
        "changed_fields": changed,
        "original_raw_hash": _sha256(original_raw_bytes),
        "corrected_raw_hash": _sha256(corrected_raw_bytes),
        "semantic_payload_hash_before": before_hash,
        "semantic_payload_hash_after": after_hash,
        "original_raw_bytes_preservation": "REQUIRED",
        "same_attempt_only": True,
    }


def build_reviewer_work_order(
    state: dict[str, Any],
    *,
    phase: str,
    repeat_index: int,
    reviewer_execution_ref: dict[str, str],
    output_target: str,
) -> dict[str, Any]:
    """Copy only public dispatch authority into one closed reviewer work order."""

    if phase not in MANDATORY_PHASES or repeat_index not in {1, 2, 3}:
        raise ValueError("reviewer work order phase or repeat is invalid")
    dispatch = state.get("dispatch")
    context = dispatch.get("writing_eval_context") if isinstance(dispatch, dict) else None
    if (
        state.get("status") != "ACTIVE"
        or not isinstance(dispatch, dict)
        or dispatch.get("status") != "DISPATCHED"
        or not isinstance(context, dict)
        or _shape_execution_ref_issues(
            reviewer_execution_ref,
            "reviewer_execution_ref",
            "HOST_SUBAGENT_ATTEMPT",
        )
    ):
        raise ValueError("reviewer work order requires one prepared durable Run")
    order = {
        "schema_version": "prd-readability-v0.8-reviewer-work-order.v1",
        "suite_id": state["suite_id"],
        "phase": phase,
        "case_id": state["case_id"],
        "repeat_index": repeat_index,
        "run_id": state["run_id"],
        "attempt_id": dispatch["attempt_id"],
        "reviewer_execution_ref": reviewer_execution_ref,
        "author_execution_ref": context["author_execution_ref"],
        "preregistration_checkpoint_ref": state["preregistration_checkpoint_ref"],
        "output_target": output_target,
        "instruction_ref": dispatch["instruction_ref"],
        "instruction_hash": dispatch["instruction_hash"],
        "input_refs": dispatch["input_refs"],
        "input_hashes": dispatch["input_hashes"],
        "candidate_ref": context["candidate_ref"],
        "profile_ref": context["profile_ref"],
        "guide_ref": context["guide_ref"],
        "reviewer_resource_ref": context["reviewer_resource_ref"],
        "output_contract_ref": context["output_contract_ref"],
        "isolated_input_refs": context["isolated_input_refs"],
        "reader_visible_visual_pairs": context["reader_visible_visual_pairs"],
        "claim_boundary": "REVIEWER_INPUT_ONLY_EXPECTED_ORACLE_AND_SCORER_EXCLUDED",
    }
    if set(order) != WORK_ORDER_FIELDS:
        raise ValueError("closed reviewer work order construction failed")
    return order


def _reviewer_work_order_issues(
    value: Any,
    *,
    entry: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> list[str]:
    if not isinstance(value, dict) or set(value) != WORK_ORDER_FIELDS:
        return ["closed reviewer work order"]
    expected = {
        "schema_version": "prd-readability-v0.8-reviewer-work-order.v1",
        "suite_id": entry["suite_id"],
        "phase": entry["phase"],
        "case_id": entry["agent_case_id"],
        "repeat_index": entry["repeat_index"],
        "run_id": entry["run_id"],
        "attempt_id": entry["attempt_id"],
        "reviewer_execution_ref": entry["reviewer_execution_ref"],
        "author_execution_ref": entry["author_execution_ref"],
        "preregistration_checkpoint_ref": entry["preregistration_checkpoint_ref"],
        "output_target": entry["output_target"],
        "claim_boundary": "REVIEWER_INPUT_ONLY_EXPECTED_ORACLE_AND_SCORER_EXCLUDED",
    }
    issues = [f"work_order:{field}" for field, expected_value in expected.items() if value.get(field) != expected_value]
    if state is not None:
        dispatch = state["dispatch"]
        context = dispatch["writing_eval_context"]
        dispatch_values = {
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "candidate_ref": context["candidate_ref"],
            "profile_ref": context["profile_ref"],
            "guide_ref": context["guide_ref"],
            "reviewer_resource_ref": context["reviewer_resource_ref"],
            "output_contract_ref": context["output_contract_ref"],
            "isolated_input_refs": context["isolated_input_refs"],
            "reader_visible_visual_pairs": context["reader_visible_visual_pairs"],
        }
        issues.extend(
            f"work_order:{field}"
            for field, expected_value in dispatch_values.items()
            if value.get(field) != expected_value
        )
    return sorted(set(issues))


def _canonical_export_files(case_root: Path, case_id: str) -> dict[str, dict[str, Any]]:
    manifest_path = case_root / "canonical-export-manifest.json"
    manifest = _load_json(manifest_path)
    if (
        manifest is None
        or set(manifest) != EXPORT_MANIFEST_FIELDS
        or manifest.get("schema_version") != "prd-readability-v0.8-canonical-export.v1"
        or manifest.get("suite_id") != SUITE_ID
        or manifest.get("case_id") != case_id
        or manifest.get("evaluator_files_included") is not False
        or not isinstance(manifest.get("files"), list)
    ):
        raise ValueError("canonical export manifest is invalid")
    declared: dict[str, dict[str, Any]] = {}
    for ref in manifest["files"]:
        if (
            not isinstance(ref, dict)
            or set(ref) != {"path", "hash", "size"}
            or not isinstance(ref.get("path"), str)
            or Path(ref["path"]).is_absolute()
            or ".." in Path(ref["path"]).parts
            or ref["path"] in declared
        ):
            raise ValueError("canonical export manifest file ref is invalid")
        path = case_root / ref["path"]
        if (
            path.is_symlink()
            or not path.is_file()
            or len(path.read_bytes()) != ref["size"]
            or _sha256(path.read_bytes()) != ref["hash"]
        ):
            raise ValueError("canonical export manifest file is stale")
        declared[ref["path"]] = ref
    actual = {
        path.relative_to(case_root).as_posix()
        for path in case_root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual != set(declared):
        raise ValueError("canonical export manifest does not close the case tree")
    return declared


def emit_reviewer_projection(
    manifest: dict[str, Any],
    reviewer_id: str,
    anonymous_workspace: Path,
    target: Path,
) -> None:
    """Project one bound attempt without evaluator files or another reviewer's work."""

    if execution_manifest_shape_issues(manifest):
        raise ValueError("execution manifest is invalid")
    selected = [
        entry
        for entry in manifest["entries"]
        if entry["reviewer_execution_ref"]["id"] == reviewer_id
    ]
    if len(selected) != 1:
        raise ValueError("reviewer projection requires one exact manifest entry")
    _ensure_safe_export_target(target)
    entry = selected[0]
    source = anonymous_workspace / entry["agent_case_id"]
    if source.is_symlink() or not source.is_dir():
        raise ValueError("anonymous case projection source is missing")
    export_files = _canonical_export_files(source, entry["agent_case_id"])
    central_root = Path(manifest["central_project_root"]["path"]).resolve(strict=True)
    root_stat = central_root.stat()
    if manifest["central_project_root"] != {
        "path": str(central_root),
        "device": root_stat.st_dev,
        "inode": root_stat.st_ino,
    }:
        raise ValueError("reviewer projection central project root is stale")
    state = _bound_manifest_state(central_root, manifest, entry)
    dispatch = state.get("dispatch") if isinstance(state, dict) else None
    context = (
        dispatch.get("writing_eval_context") if isinstance(dispatch, dict) else None
    )
    if (
        not isinstance(state, dict)
        or state.get("run_id") != entry["run_id"]
        or state.get("suite_id") != entry["suite_id"]
        or state.get("case_id") != entry["agent_case_id"]
        or state.get("status") != "ACTIVE"
        or state.get("result_ref") is not None
        or state.get("preregistration_checkpoint_ref")
        != entry["preregistration_checkpoint_ref"]
        or not isinstance(dispatch, dict)
        or dispatch.get("status") != "DISPATCHED"
        or dispatch.get("attempt_id") != entry["attempt_id"]
        or not isinstance(context, dict)
        or context.get("author_execution_ref") != entry["author_execution_ref"]
        or context.get("installed_build_ref") != entry["installed_build_ref"]
    ):
        raise ValueError("reviewer projection durable state differs from manifest")
    target.mkdir(parents=True, exist_ok=False)
    projection_paths = ["candidate.md"] + sorted(
        path for path in export_files if path.startswith("assets/")
    )
    for relative in projection_paths:
        if relative not in export_files:
            raise ValueError("canonical export manifest lacks frozen reviewer input")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, destination)
    work_order_ref = entry["work_order_ref"]
    work_order_source = _project_path(
        central_root, work_order_ref["path"], "work_order_ref"
    )
    if (
        work_order_source.is_symlink()
        or not work_order_source.is_file()
        or _sha256(work_order_source.read_bytes()) != work_order_ref["hash"]
    ):
        raise ValueError("reviewer work order is missing or stale")
    work_order_bytes = work_order_source.read_bytes()
    try:
        work_order = json.loads(work_order_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("closed reviewer work order is invalid JSON") from error
    work_order_issues = _reviewer_work_order_issues(
        work_order, entry=entry, state=state
    )
    if work_order_issues:
        raise ValueError("closed reviewer work order is invalid: " + ",".join(work_order_issues))
    candidate_hash = export_files["candidate.md"]["hash"]
    if work_order["candidate_ref"].get("hash") != candidate_hash:
        raise ValueError("closed reviewer work order Candidate differs from frozen export")
    (target / "work-order.json").write_bytes(work_order_bytes)
    sources_by_hash: dict[str, list[Path]] = {}
    for relative, file_ref in export_files.items():
        sources_by_hash.setdefault(file_ref["hash"], []).append(source / relative)
    isolated_refs = work_order["isolated_input_refs"]
    if not isinstance(isolated_refs, list) or len(isolated_refs) != 6:
        raise ValueError("reviewer projection requires all six isolated refs")
    isolated_paths: list[str] = []
    for index, isolated_ref in enumerate(isolated_refs):
        if _shape_ref_issues(isolated_ref, f"isolated_input_refs[{index}]"):
            raise ValueError("reviewer projection isolated ref is invalid")
        candidates = sources_by_hash.get(isolated_ref["hash"], [])
        if len(candidates) != 1:
            raise ValueError("reviewer projection isolated ref lacks one frozen source")
        relative = Path(isolated_ref["path"])
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError("reviewer projection isolated ref path is unsafe")
        destination = target / relative
        resolved_destination = destination.resolve()
        try:
            resolved_destination.relative_to(target.resolve(strict=True))
        except ValueError as error:
            raise ValueError("reviewer projection isolated ref escapes target") from error
        if destination.exists() or destination.is_symlink():
            if (
                not destination.is_file()
                or destination.is_symlink()
                or _sha256(destination.read_bytes()) != isolated_ref["hash"]
            ):
                raise ValueError("reviewer projection isolated ref collides")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidates[0], destination)
        isolated_paths.append(relative.as_posix())
    instruction_matches = [
        ref
        for ref in isolated_refs
        if ref["path"] == work_order["instruction_ref"]
        and ref["hash"] == work_order["instruction_hash"]
    ]
    for field in (
        "candidate_ref", "profile_ref", "guide_ref", "reviewer_resource_ref",
        "output_contract_ref",
    ):
        if work_order[field] not in isolated_refs:
            raise ValueError(f"reviewer projection isolated refs omit {field}")
    if len(instruction_matches) != 1:
        raise ValueError("reviewer projection isolated refs omit exact Instruction")
    declared_paths = sorted(
        set(projection_paths + isolated_paths + ["work-order.json"])
    )
    declared_files = [
        {
            "path": relative,
            "hash": _sha256((target / relative).read_bytes()),
            "size": (target / relative).stat().st_size,
        }
        for relative in declared_paths
    ]
    projection = {
        "schema_version": "prd-readability-v0.8-reviewer-projection.v1",
        "suite_id": SUITE_ID,
        "phase": entry["phase"],
        "case_id": entry["agent_case_id"],
        "run_id": entry["run_id"],
        "attempt_id": entry["attempt_id"],
        "reviewer_execution_ref": entry["reviewer_execution_ref"],
        "author_execution_ref": entry["author_execution_ref"],
        "preregistration_checkpoint_ref": entry[
            "preregistration_checkpoint_ref"
        ],
        "work_order_ref": entry["work_order_ref"],
        "output_target": entry["output_target"],
        "installed_build_ref": entry["installed_build_ref"],
        "files": declared_files,
        "evaluator_files_included": False,
    }
    (target / "reviewer-projection.json").write_text(
        json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def contract_payload(*, export_requested: bool) -> dict[str, Any]:
    issues = preregistration_issues()
    payload: dict[str, Any] = {
        "schema_version": "prd-readability-v0.8-contract-report.v1",
        "contract_status": "PASS" if not issues else "FAIL",
        "fixture_review_status": "APPROVED" if not issues else "INVALID_OR_STALE",
        "preregistration_status": "PREREGISTERED_BEFORE_RESULTS" if not issues else "INVALID_OR_STALE",
        "issues": issues,
        "agent_runtime_status": "NOT_RUN",
        "phase_runtime_status": {phase: "NOT_RUN" for phase in MANDATORY_PHASES},
        "real_prd_review_status": "NOT_RUN",
        "human_reader_validation": "NOT_RUN",
    }
    if export_requested:
        payload["workspace_export_status"] = "REFUSED" if issues else "PENDING"
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-agent-workspace", type=Path)
    args = parser.parse_args(argv)
    export_requested = args.emit_agent_workspace is not None
    payload = contract_payload(export_requested=export_requested)
    if payload["contract_status"] != "PASS":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    if args.emit_agent_workspace is not None:
        try:
            emit_agent_workspace(args.emit_agent_workspace)
        except (OSError, ValueError) as error:
            payload["contract_status"] = "FAIL"
            payload["workspace_export_status"] = "REFUSED"
            payload["issues"] = [str(error)]
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            return 1
        payload["workspace_export_status"] = "EMITTED_NOT_RUN"
        payload["agent_workspace"] = str(args.emit_agent_workspace.resolve())
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
