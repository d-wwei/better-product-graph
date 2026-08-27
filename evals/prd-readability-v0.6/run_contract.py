#!/usr/bin/env python3
"""Expose the v0.6 fixture-review gate without creating semantic evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
CASE_IDS = (
    "flat-18-acceptance-rows",
    "duplicate-eight-questions-and-blocks",
    "list-diagram-table-same-model",
    "trim-removes-useful-checklist",
    "checked-boxes-without-legend",
    "proposed-contract-looks-implemented",
    "large-necessary-state-table",
    "long-appendix-short-main-path",
    "reader-first-layered-prd",
)
INTENDED_OBJECTIVES = {
    "flat-18-acceptance-rows": "MAKE_PEER_STRUCTURE_SCANNABLE",
    "duplicate-eight-questions-and-blocks": "KEEP_ONE_CANONICAL_DEFINITION",
    "list-diagram-table-same-model": "REMOVE_REDUNDANT_REPRESENTATION",
    "trim-removes-useful-checklist": "PRESERVE_CHECKLIST_FUNCTION",
    "checked-boxes-without-legend": "CLARIFY_COMPLETION_EVIDENCE_BOUNDARY",
    "proposed-contract-looks-implemented": "CLARIFY_ARTIFACT_MATURITY_BOUNDARY",
    "large-necessary-state-table": "NO_REPAIR_REQUIRED",
    "long-appendix-short-main-path": "NO_REPAIR_REQUIRED",
    "reader-first-layered-prd": "NO_REPAIR_REQUIRED",
}
ALLOWED_PRIMARY_PAIRS = {
    "flat-18-acceptance-rows": [["FLAT_PEER_OVERLOAD", "GROUP"], ["FLAT_PEER_OVERLOAD", "LAYER"]],
    "duplicate-eight-questions-and-blocks": [["SEMANTIC_REPETITION", "REFERENCE"], ["SEMANTIC_REPETITION", "MERGE"]],
    "list-diagram-table-same-model": [["REPRESENTATION_COLLISION", "TRIM"], ["REPRESENTATION_COLLISION", "REFERENCE"], ["REPRESENTATION_COLLISION", "MERGE"]],
    "trim-removes-useful-checklist": [["CHECKLIST_FUNCTION_LOSS", "RESTORE_FUNCTION"], ["CHECKLIST_FUNCTION_LOSS", "REFERENCE"]],
    "checked-boxes-without-legend": [["COMPLETION_SEMANTICS_AMBIGUOUS", "EXPLAIN"], ["COMPLETION_SEMANTICS_AMBIGUOUS", "BOUNDARY"]],
    "proposed-contract-looks-implemented": [["ARTIFACT_MATURITY_OVERCLAIM", "BOUNDARY"], ["ARTIFACT_MATURITY_OVERCLAIM", "EXPLAIN"]],
    "large-necessary-state-table": [],
    "long-appendix-short-main-path": [],
    "reader-first-layered-prd": [],
}
AGENT_RESOURCE_EXPORTS = (
    ("profile_ref", "PRD_WRITING_PROFILE_v0.5.json"),
    ("guide_ref", "PRD_WRITING_GUIDE_v0.5.md"),
    ("instruction_ref", "INSTRUCTIONS_v3.2.md"),
    ("reviewer_resource_ref", "reviewer-resource-v3.2.json"),
    ("output_contract_ref", "output-contract.json"),
    ("result_schema_ref", "result-schema-v3.1.json"),
)
FIXTURE_REVIEW_EXCLUSIONS = (
    "allowed_pairs",
    "expected",
    "preregistration",
    "scorer",
    "semantic_results",
    "other_reviewer_findings",
)
EXPECTED_SUPERSEDED_REVIEWS = {
    "reviewer-a-superseded-001.json": {
        "hash": "sha256:4be9a565c7274303837aab8f4a22c1ab293c26218d5118d4b664eee20ac9b289",
        "reviewer_id": "fixture-review-a-20260826",
        "record_status": "SUPERSEDED_BY_FIXTURE_CHANGE",
        "verdict": "FINDING",
        "concern_ids": {"A-CASE9-MISSING-TIMEOUT-BRANCH"},
    },
    "reviewer-b-superseded-001.json": {
        "hash": "sha256:65d52146094f4ed6fa9b590f61073007ef55f1fc525eb99510abe6b1330d4aa1",
        "reviewer_id": "fixture-review-b-20260826",
        "record_status": "SUPERSEDED_BY_FIXTURE_CHANGE",
        "verdict": "APPROVED",
        "concern_ids": set(),
    },
}
SOURCE_VISUAL_REF = re.compile(
    r"!\[[^\]\n]*\]\((?P<destination>\.\./assets/(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*\.svg))\)"
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
        raise ValueError(f"unknown v0.6 readability case: {case_id}")
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


def fixture_tree_identity() -> dict[str, Any]:
    """Return the exact cases/assets identity reviewed before oracle freezing."""

    paths = [CASES_ROOT / f"{case_id}.md" for case_id in CASE_IDS]
    paths.extend(sorted(ASSETS_ROOT.iterdir(), key=lambda path: path.name))
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
    return {
        "schema_version": "prd-readability-v0.5-fixture-tree.v1",
        "tree_hash": _sha256(canonical.encode("utf-8")),
        "files": files,
    }


def _valid_attempt_identity(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"kind", "id"}
        and value.get("kind") == "HOST_SUBAGENT_ATTEMPT"
        and isinstance(value.get("id"), str)
        and bool(value["id"].strip())
    )


def _attempt_id(value: Any) -> str | None:
    identifier = value.get("id") if isinstance(value, dict) else None
    return identifier if isinstance(identifier, str) else None


def _review_record_reasons(
    review: dict[str, Any],
    *,
    label: str,
    current_tree: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    fixture_hashes = {
        item["path"]: item["hash"]
        for item in current_tree["files"]
    }
    reviewer = review.get("reviewer_identity")
    author = review.get("fixture_author_identity")
    if review.get("schema_version") != "prd-readability-v0.5-fixture-review.v1":
        reasons.append(f"{label}: schema_version")
    if review.get("review_status") != "CURRENT":
        reasons.append(f"{label}: review_status")
    if not _valid_attempt_identity(reviewer):
        reasons.append(f"{label}: reviewer_identity")
    if not _valid_attempt_identity(author):
        reasons.append(f"{label}: fixture_author_identity")
    if _valid_attempt_identity(reviewer) and reviewer == author:
        reasons.append(f"{label}: self_review")
    if review.get("fixture_tree") != current_tree:
        reasons.append(f"{label}: stale_fixture_tree")
    if review.get("excluded_inputs") != list(FIXTURE_REVIEW_EXCLUSIONS):
        reasons.append(f"{label}: excluded_inputs")
    if review.get("prior_verdict_reused") is not False:
        reasons.append(f"{label}: prior_verdict_reused")

    cases = review.get("cases")
    if not isinstance(cases, list):
        reasons.append(f"{label}: cases")
        cases = []
    case_ids = [
        case.get("case_id")
        for case in cases
        if isinstance(case, dict) and isinstance(case.get("case_id"), str)
    ]
    if len(cases) != len(CASE_IDS) or set(case_ids) != set(CASE_IDS) or len(set(case_ids)) != len(CASE_IDS):
        reasons.append(f"{label}: case_coverage")
    for case in cases:
        if not isinstance(case, dict):
            reasons.append(f"{label}: case_record")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str):
            reasons.append(f"{label}: case_id")
            continue
        if case_id not in INTENDED_OBJECTIVES:
            continue
        if case.get("intended_objective") != INTENDED_OBJECTIVES[case_id]:
            reasons.append(f"{label}:{case_id}: intended_objective")
        if case.get("single_primary_capability") is not True:
            reasons.append(f"{label}:{case_id}: single_primary_capability")
        if case.get("unintended_material_issue") is not None:
            reasons.append(f"{label}:{case_id}: unintended_material_issue")
        if not isinstance(case.get("basis"), str) or not case["basis"].strip():
            reasons.append(f"{label}:{case_id}: basis")
        expected_positive = True if INTENDED_OBJECTIVES[case_id] == "NO_REPAIR_REQUIRED" else None
        if case.get("positive_fixture_complete") is not expected_positive:
            reasons.append(f"{label}:{case_id}: positive_fixture_complete")
        observation = case.get("visual_observation")
        if case_id == "reader-first-layered-prd":
            if not isinstance(observation, dict):
                reasons.append(f"{label}:{case_id}: visual_observation")
            elif (
                observation.get("actually_viewed") is not True
                or observation.get("rendered_svg_observed") is not True
                or observation.get("rendered_png_observed") is not True
                or observation.get("assessment") != "OBSERVED_USEFUL"
                or observation.get("svg_hash") != fixture_hashes["assets/reader-first-layered-prd.svg"]
                or observation.get("png_hash") != fixture_hashes["assets/reader-first-layered-prd@2x.png"]
                or not isinstance(observation.get("notes"), str)
                or not observation["notes"].strip()
            ):
                reasons.append(f"{label}:{case_id}: rendered_visual_not_observed")
        elif observation != "NOT_APPLICABLE":
            reasons.append(f"{label}:{case_id}: visual_observation")

    concerns = review.get("concerns")
    if not isinstance(concerns, list):
        reasons.append(f"{label}: concerns")
        concerns = []
    concern_ids: list[str] = []
    for concern in concerns:
        if not isinstance(concern, dict):
            reasons.append(f"{label}: concern_record")
            continue
        concern_id = concern.get("concern_id")
        if not isinstance(concern_id, str) or not concern_id.strip():
            reasons.append(f"{label}: concern_id")
        else:
            concern_ids.append(concern_id)
        if concern.get("case_id") not in CASE_IDS:
            reasons.append(f"{label}: concern_case_id")
        if not isinstance(concern.get("summary"), str) or not concern["summary"].strip():
            reasons.append(f"{label}: concern_summary")
    if len(concern_ids) != len(set(concern_ids)):
        reasons.append(f"{label}: duplicate_concern_id")
    if review.get("verdict") != "APPROVED":
        reasons.append(f"{label}: verdict")
    return reasons


def _superseded_history_reasons(
    review_root: Path,
    adjudication: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    refs = adjudication.get("superseded_review_refs")
    if not isinstance(refs, list):
        return ["adjudication: superseded_review_refs"]

    discovered = sorted(path.name for path in review_root.glob("reviewer-*-superseded-*.json"))
    ref_names = [
        ref["path"]
        for ref in refs
        if isinstance(ref, dict) and isinstance(ref.get("path"), str)
    ]
    if len(refs) != len(ref_names) or len(set(ref_names)) != len(ref_names) or sorted(ref_names) != discovered:
        reasons.append("adjudication: superseded_review_refs")
    expected_names = sorted(EXPECTED_SUPERSEDED_REVIEWS)
    if discovered != expected_names or sorted(ref_names) != expected_names:
        reasons.append("adjudication: frozen_superseded_review_set")

    refs_by_path = {
        ref["path"]: ref
        for ref in refs
        if isinstance(ref, dict) and isinstance(ref.get("path"), str)
    }
    for relative_path, expected in EXPECTED_SUPERSEDED_REVIEWS.items():
        path = review_root / relative_path
        ref = refs_by_path.get(relative_path)
        if path.is_symlink() or not path.is_file():
            continue
        exact_hash = _sha256(path.read_bytes())
        if exact_hash != expected["hash"] or not isinstance(ref, dict) or ref.get("hash") != expected["hash"]:
            reasons.append("adjudication: frozen_superseded_review_hash")
        record = _load_json(path)
        if record is None:
            continue
        if (
            _attempt_id(record.get("reviewer_identity")) != expected["reviewer_id"]
            or not isinstance(ref, dict)
            or ref.get("reviewer_id") != expected["reviewer_id"]
            or record.get("record_status") != expected["record_status"]
            or ref.get("status") != expected["record_status"]
        ):
            reasons.append("adjudication: frozen_superseded_review_identity")
        case_ids = [
            case.get("case_id")
            for case in record.get("cases", [])
            if isinstance(case, dict) and isinstance(case.get("case_id"), str)
        ]
        if len(case_ids) != len(CASE_IDS) or set(case_ids) != set(CASE_IDS):
            reasons.append("adjudication: frozen_superseded_case_coverage")
        concerns = record.get("concerns")
        concern_ids = (
            {
                concern["concern_id"]
                for concern in concerns
                if isinstance(concern, dict) and isinstance(concern.get("concern_id"), str)
            }
            if isinstance(concerns, list)
            else set()
        )
        if record.get("verdict") != expected["verdict"] or concern_ids != expected["concern_ids"]:
            reasons.append("adjudication: frozen_superseded_review_semantics")

    historical_concerns: set[tuple[str, str]] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            reasons.append("adjudication: superseded_review_ref")
            continue
        relative_path = ref.get("path")
        if (
            not isinstance(relative_path, str)
            or Path(relative_path).name != relative_path
            or not re.fullmatch(r"reviewer-[ab]-superseded-\d{3}\.json", relative_path)
        ):
            reasons.append("adjudication: superseded_review_ref_path")
            continue
        path = review_root / relative_path
        if path.is_symlink() or not path.is_file():
            reasons.append("adjudication: superseded_review_file")
            continue
        record = _load_json(path)
        if record is None:
            reasons.append("adjudication: superseded_review_file")
            continue
        reviewer_id = _attempt_id(record.get("reviewer_identity"))
        if (
            record.get("schema_version") != "prd-readability-v0.5-fixture-review.v1"
            or not _valid_attempt_identity(record.get("reviewer_identity"))
        ):
            reasons.append("adjudication: superseded_review_record")
        if (
            ref.get("hash") != _sha256(path.read_bytes())
            or ref.get("reviewer_id") != reviewer_id
            or ref.get("status") != "SUPERSEDED_BY_FIXTURE_CHANGE"
        ):
            reasons.append("adjudication: superseded_review_ref")
        if record.get("record_status") != "SUPERSEDED_BY_FIXTURE_CHANGE":
            reasons.append("adjudication: superseded_review_status")
        concerns = record.get("concerns")
        if not isinstance(concerns, list):
            reasons.append("adjudication: superseded_review_concerns")
            continue
        concern_ids: set[str] = set()
        for concern in concerns:
            concern_id = concern.get("concern_id") if isinstance(concern, dict) else None
            if not isinstance(concern_id, str) or not concern_id.strip() or reviewer_id is None:
                reasons.append("adjudication: superseded_review_concern")
                continue
            if concern_id in concern_ids:
                reasons.append("adjudication: duplicate_superseded_review_concern")
                continue
            concern_ids.add(concern_id)
            historical_concerns.add((reviewer_id, concern_id))

    dispositions = adjudication.get("superseded_concern_dispositions")
    if not isinstance(dispositions, list):
        return reasons + ["adjudication: superseded_concern_dispositions"]
    disposition_keys: list[tuple[str, str]] = []
    for item in dispositions:
        if not isinstance(item, dict):
            reasons.append("adjudication: invalid_superseded_concern_disposition")
            continue
        reviewer_id = item.get("reviewer_id")
        concern_id = item.get("concern_id")
        if not isinstance(reviewer_id, str) or not isinstance(concern_id, str):
            reasons.append("adjudication: invalid_superseded_concern_disposition")
            continue
        disposition_keys.append((reviewer_id, concern_id))
        if (
            item.get("disposition") not in {"ACCEPTED_NO_FIX_REQUIRED", "FIXED_BEFORE_APPROVAL"}
            or not isinstance(item.get("rationale"), str)
            or not item["rationale"].strip()
        ):
            reasons.append("adjudication: invalid_superseded_concern_disposition")
    if len(disposition_keys) != len(set(disposition_keys)):
        reasons.append("adjudication: duplicate_superseded_concern_disposition")
    if set(disposition_keys) != historical_concerns:
        reasons.append("adjudication: superseded_concern_coverage")
    return reasons


def validate_fixture_review_gate(review_root: Path = FIXTURE_REVIEW_ROOT) -> tuple[bool, list[str]]:
    """Mechanically validate independent records; never invent semantic review content."""

    current_tree = fixture_tree_identity()
    review_paths = (review_root / "reviewer-a.json", review_root / "reviewer-b.json")
    adjudication_path = review_root / "adjudication.json"
    reviews = [_load_json(path) for path in review_paths]
    adjudication = _load_json(adjudication_path)
    reasons: list[str] = []
    if any(review is None for review in reviews):
        reasons.append("two_review_records_required")
    if adjudication is None:
        reasons.append("adjudication_required")
    if reasons:
        return False, reasons
    assert all(review is not None for review in reviews)
    assert adjudication is not None
    typed_reviews = [review for review in reviews if review is not None]
    for label, review in zip(("reviewer-a", "reviewer-b"), typed_reviews, strict=True):
        reasons.extend(_review_record_reasons(review, label=label, current_tree=current_tree))

    reviewer_ids = [_attempt_id(review.get("reviewer_identity")) for review in typed_reviews]
    author_identities = [review.get("fixture_author_identity") for review in typed_reviews]
    if len(set(reviewer_ids)) != 2:
        reasons.append("distinct_reviewer_ids_required")
    if author_identities[0] != author_identities[1]:
        reasons.append("fixture_author_identity_mismatch")

    if adjudication.get("schema_version") != "prd-readability-v0.5-fixture-adjudication.v1":
        reasons.append("adjudication: schema_version")
    if adjudication.get("fixture_tree") != current_tree:
        reasons.append("adjudication: stale_fixture_tree")
    if adjudication.get("fixture_author_identity") != author_identities[0]:
        reasons.append("adjudication: fixture_author_identity")
    if adjudication.get("status") != "APPROVED_FOR_PREREGISTRATION":
        reasons.append("adjudication: status")
    if adjudication.get("approved_case_ids") != list(CASE_IDS):
        reasons.append("adjudication: approved_case_ids")
    if adjudication.get("semantic_evaluation_status") != "NOT_RUN":
        reasons.append("adjudication: semantic_evaluation_status")
    if adjudication.get("agent_runtime_status") != "NOT_RUN":
        reasons.append("adjudication: agent_runtime_status")
    if adjudication.get("real_prd_review_status") != "NOT_RUN":
        reasons.append("adjudication: real_prd_review_status")
    if adjudication.get("human_reader_validation") != "NOT_RUN":
        reasons.append("adjudication: human_reader_validation")
    if adjudication.get("reviewers_prohibited_from_semantic_eval") != reviewer_ids:
        reasons.append("adjudication: semantic_eval_reviewer_exclusion")
    if adjudication.get("both_reviewers_observed_rendered_visual") is not True:
        reasons.append("adjudication: rendered_visual_observation")
    reasons.extend(_superseded_history_reasons(review_root, adjudication))

    expected_review_refs = [
        {
            "path": path.name,
            "hash": _sha256(path.read_bytes()),
            "reviewer_id": reviewer_id,
        }
        for path, reviewer_id in zip(review_paths, reviewer_ids, strict=True)
    ]
    if adjudication.get("review_refs") != expected_review_refs:
        reasons.append("adjudication: review_refs")

    expected_concerns = {
        (reviewer_id, concern["concern_id"])
        for reviewer_id, review in zip(reviewer_ids, typed_reviews, strict=True)
        for concern in review.get("concerns", [])
        if isinstance(concern, dict) and isinstance(concern.get("concern_id"), str)
    }
    dispositions = adjudication.get("concern_dispositions")
    if not isinstance(dispositions, list):
        reasons.append("adjudication: concern_dispositions")
        dispositions = []
    actual_concerns: set[tuple[str, str]] = set()
    for item in dispositions:
        if not isinstance(item, dict):
            reasons.append("adjudication: invalid_concern_disposition")
            continue
        reviewer_id = item.get("reviewer_id")
        concern_id = item.get("concern_id")
        if isinstance(reviewer_id, str) and isinstance(concern_id, str):
            actual_concerns.add((reviewer_id, concern_id))
        else:
            reasons.append("adjudication: invalid_concern_identity")
    if actual_concerns != expected_concerns or len(dispositions) != len(expected_concerns):
        reasons.append("adjudication: concern_coverage")
    for item in dispositions:
        if (
            not isinstance(item, dict)
            or item.get("disposition") not in {"ACCEPTED_NO_FIX_REQUIRED", "FIXED_BEFORE_APPROVAL"}
            or not isinstance(item.get("rationale"), str)
            or not item["rationale"].strip()
        ):
            reasons.append("adjudication: invalid_concern_disposition")
            break
    return not reasons, reasons


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
    if issues or suite is None or expected is None or prereg is None:
        return issues

    if suite.get("schema_version") != "prd-readability-suite.v0.6":
        issues.append("suite: schema_version")
    if suite.get("suite_id") != "better-product-graph-prd-readability-v0.6":
        issues.append("suite: suite_id")
    if suite.get("status") != "PREREGISTERED_AGENT_EVAL_NOT_RUN":
        issues.append("suite: status")
    if suite.get("case_ids") != list(CASE_IDS):
        issues.append("suite: case_ids")
    current_tree = fixture_tree_identity()
    if suite.get("fixture_tree_hash") != current_tree["tree_hash"]:
        issues.append("suite: fixture_tree_hash")
    expected_case_hashes = {
        item["path"].removeprefix("cases/").removesuffix(".md"): item["hash"]
        for item in current_tree["files"]
        if item["path"].startswith("cases/")
    }
    if suite.get("case_hashes") != expected_case_hashes:
        issues.append("suite: case_hashes")
    if suite.get("target_eval_schema") != "document-experience-reader-eval.v3.1":
        issues.append("suite: target_eval_schema")

    if expected.get("schema_version") != "prd-readability-expected-envelope.v0.6":
        issues.append("expected: schema_version")
    if expected.get("suite_id") != suite.get("suite_id"):
        issues.append("expected: suite_id")
    if expected.get("custody") != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE":
        issues.append("expected: custody")
    expected_cases = expected.get("cases")
    if not isinstance(expected_cases, dict) or set(expected_cases) != set(CASE_IDS):
        issues.append("expected: case_coverage")
        expected_cases = {}
    for index, case_id in enumerate(CASE_IDS, 1):
        oracle = expected_cases.get(case_id)
        required_result = "PASS" if INTENDED_OBJECTIVES[case_id] == "NO_REPAIR_REQUIRED" else "FINDING"
        if not isinstance(oracle, dict) or set(oracle) != {
            "agent_case_id", "required_result", "primary_objective", "allowed_primary_pairs"
        }:
            issues.append(f"expected:{case_id}: closed_oracle")
            continue
        if oracle.get("agent_case_id") != f"case-{index:03d}":
            issues.append(f"expected:{case_id}: agent_case_id")
        if oracle.get("required_result") != required_result:
            issues.append(f"expected:{case_id}: required_result")
        if oracle.get("primary_objective") != INTENDED_OBJECTIVES[case_id]:
            issues.append(f"expected:{case_id}: primary_objective")
        if oracle.get("allowed_primary_pairs") != ALLOWED_PRIMARY_PAIRS[case_id]:
            issues.append(f"expected:{case_id}: allowed_primary_pairs")

    if prereg.get("schema_version") != "prd-readability-preregistration.v0.6":
        issues.append("preregistration: schema_version")
    if prereg.get("suite_id") != suite.get("suite_id"):
        issues.append("preregistration: suite_id")
    if prereg.get("status") != "PREREGISTERED_BEFORE_RESULTS":
        issues.append("preregistration: status")
    if (
        prereg.get("freeze_order_authority")
        != "PREREGISTRATION_GIT_COMMIT_PRECEDES_RESULTS"
    ):
        issues.append("preregistration: freeze_order_authority")
    if "registered_at" in prereg:
        issues.append("preregistration: registered_at_is_not_freeze_authority")
    if prereg.get("custody") != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE":
        issues.append("preregistration: custody")
    if prereg.get("fixture_tree") != current_tree:
        issues.append("preregistration: fixture_tree")
    required_gate = {
        "repeats_per_case": 3,
        "case_count": 9,
        "required_attempt_count": 27,
        "required_passed_attempt_count": 27,
        "required_passed_repeats_per_case": 3,
        "selection_policy": "ALL_ATTEMPTS_NO_BEST_OF_N",
        "threshold_change_after_first_result": "FORBIDDEN",
        "negative_attempt_policy": "EXACTLY_ONE_FINDING_ASSESSMENT_REGISTERED_PRIMARY_PAIR_PRESENT_SECONDARY_LABELS_AND_REPAIRS_ALLOWED_NO_SECOND_FINDING",
        "positive_attempt_policy": "PASS_NULL_PRIMARY_ZERO_FAILURES_ZERO_FINDINGS",
        "installed_build_policy": "ONE_EXACT_BUILD_REF_ALL_27_ATTEMPTS",
    }
    for field, expected_value in required_gate.items():
        if prereg.get(field) != expected_value:
            issues.append(f"preregistration: {field}")
    for field in ("agent_runtime_status", "real_prd_review_status", "human_reader_validation"):
        if prereg.get(field) != "NOT_RUN":
            issues.append(f"preregistration: {field}")

    exact_suite_refs = {
        "suite_ref": "suite.json",
        "expected_ref": "evaluator/expected.json",
        "scorer_ref": "evaluator/score_results.py",
        "fixture_adjudication_ref": "fixture-review/adjudication.json",
    }
    for field, path in exact_suite_refs.items():
        issues.extend(
            _exact_ref_issues(prereg.get(field), label=f"preregistration.{field}", base=ROOT, expected_path=path)
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
                _exact_ref_issues(ref, label=f"preregistration.{path}", base=ROOT, expected_path=path)
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
        issues.extend(_exact_ref_issues(suite.get(field), label=f"suite.{field}", base=REPO_ROOT, expected_path=path))
        issues.extend(_exact_ref_issues(prereg.get(field), label=f"preregistration.{field}", base=REPO_ROOT, expected_path=path))
        if suite.get(field) != prereg.get(field):
            issues.append(f"resource_ref_mismatch: {field}")
    result_files = [
        path
        for path in (ROOT / "results").rglob("*")
        if path.is_file() and path.name != "README.md"
    ]
    if result_files:
        issues.append("semantic_results_exist_before_freeze")
    return issues


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


def contract_payload(*, export_requested: bool) -> dict[str, Any]:
    issues = preregistration_issues()
    payload: dict[str, Any] = {
        "schema_version": "prd-readability-v0.6-contract-report.v1",
        "contract_status": "PASS" if not issues else "FAIL",
        "fixture_review_status": "APPROVED" if not issues else "INVALID_OR_STALE",
        "preregistration_status": "PREREGISTERED_BEFORE_RESULTS" if not issues else "INVALID_OR_STALE",
        "issues": issues,
        "agent_runtime_status": "NOT_RUN",
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
