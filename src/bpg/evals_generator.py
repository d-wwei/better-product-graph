"""Product-level Eval contracts and deterministic validation.

Semantic applicability judgment, Pack authoring, and Review findings belong to
the Host Agent and an independent Reviewer.  This module only validates exact
contracts, provenance, versioning, independence, and truthful state display.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .storage import assert_managed_path, read_json, sha256_file


class EvalsGeneratorError(ValueError):
    """A Product Evals contract violates the v1 product boundary."""


APPLICABILITY_VALUES = frozenset({"NOT_NEEDED", "RECOMMENDED", "REQUIRED"})
FULFILLMENT_VALUES = frozenset(
    {
        "NOT_STARTED",
        "GENERATING",
        "GENERATED_PENDING_REVIEW",
        "REVIEWED",
        "BLOCKED_MISSING_INPUT",
    }
)
CASE_CLASSES = frozenset({"NORMAL", "BOUNDARY", "FAILURE", "ADVERSARIAL"})
EXECUTION_ABSENCE = frozenset({"RUNTIME_EXECUTION", "TEST_EXECUTION", "VERDICT"})


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvalsGeneratorError(f"{label} must be an object")
    return value


def _nonempty_text(value: Any, label: str, *, explanatory: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvalsGeneratorError(f"{label} must be non-empty text")
    text = value.strip()
    if explanatory and len(text) < 8:
        raise EvalsGeneratorError(f"{label} must explain the product basis, not repeat a keyword")
    return text


def _nonempty_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise EvalsGeneratorError(f"{label} must be a non-empty list")
    return value


def _identity(value: Any, label: str) -> dict[str, str]:
    item = _object(value, label)
    if set(item) != {"kind", "id"}:
        raise EvalsGeneratorError(f"{label} must contain exactly kind and id")
    return {
        "kind": _nonempty_text(item.get("kind"), f"{label}.kind"),
        "id": _nonempty_text(item.get("id"), f"{label}.id"),
    }


def _exact_ref(
    project_root: Path,
    value: Any,
    label: str,
    *,
    require_file: bool = True,
) -> dict[str, Any]:
    ref = _object(value, label)
    if set(ref) != {"path", "hash", "version"}:
        raise EvalsGeneratorError(f"{label} must be one closed path/hash/version ref")
    path_value = _nonempty_text(ref.get("path"), f"{label}.path")
    digest = ref.get("hash")
    if (
        not isinstance(digest, str)
        or not digest.startswith("sha256:")
        or len(digest) != 71
        or any(character not in "0123456789abcdef" for character in digest[7:])
    ):
        raise EvalsGeneratorError(f"{label}.hash must be one sha256 digest")
    version = ref.get("version")
    if (
        isinstance(version, bool)
        or not isinstance(version, (str, int))
        or (isinstance(version, str) and not version.strip())
    ):
        raise EvalsGeneratorError(f"{label}.version must be a non-empty string or integer")
    if require_file:
        path = assert_managed_path(project_root, project_root / path_value)
        if not path.is_file() or path.is_symlink() or sha256_file(path) != digest:
            raise EvalsGeneratorError(f"{label} file/hash authority is invalid")
    return {"path": path_value, "hash": digest, "version": ref["version"]}


def _same_ref(left: Any, right: Any) -> bool:
    return isinstance(left, dict) and isinstance(right, dict) and all(
        left.get(key) == right.get(key) for key in ("path", "hash", "version")
    )


def _iso_datetime(value: Any, label: str) -> str:
    text = _nonempty_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise EvalsGeneratorError(f"{label} must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise EvalsGeneratorError(f"{label} must include a timezone")
    return text


def validate_applicability_assessment(
    assessment: Any,
    *,
    expected_candidate_ref: dict[str, Any],
) -> dict[str, Any]:
    """Validate an Agent-authored applicability judgment without making it."""

    item = _object(assessment, "Product Eval applicability assessment")
    required = {
        "schema_version",
        "candidate_ref",
        "decision",
        "existing_ac_sufficiency",
        "additional_judgment",
        "delivery_effect",
        "next_action",
        "missing_authority",
    }
    if set(item) != required:
        raise EvalsGeneratorError("Product Eval applicability must use the closed v1 contract")
    if item.get("schema_version") != "product-eval-applicability.v1":
        raise EvalsGeneratorError("Product Eval applicability schema_version is invalid")
    if not _same_ref(item.get("candidate_ref"), expected_candidate_ref):
        raise EvalsGeneratorError("Product Eval applicability does not bind the exact Candidate")
    decision = item.get("decision")
    if decision not in APPLICABILITY_VALUES:
        raise EvalsGeneratorError("Product Eval applicability decision is invalid")
    _nonempty_text(
        item.get("existing_ac_sufficiency"),
        "existing_ac_sufficiency",
        explanatory=True,
    )
    _nonempty_text(
        item.get("additional_judgment"),
        "additional_judgment",
        explanatory=True,
    )
    effect = _object(item.get("delivery_effect"), "delivery_effect")
    if set(effect) != {"blocking", "reason"} or not isinstance(effect.get("blocking"), bool):
        raise EvalsGeneratorError("delivery_effect must contain blocking boolean and reason")
    _nonempty_text(effect.get("reason"), "delivery_effect.reason", explanatory=True)
    if effect["blocking"] != (decision == "REQUIRED"):
        raise EvalsGeneratorError("Only REQUIRED applicability may block PRD Ready")
    action = _object(item.get("next_action"), "next_action")
    if set(action) != {"owner", "action"}:
        raise EvalsGeneratorError("next_action must contain exactly owner and action")
    _nonempty_text(action.get("owner"), "next_action.owner")
    _nonempty_text(action.get("action"), "next_action.action", explanatory=True)

    missing = item.get("missing_authority")
    fulfillment = "NOT_STARTED"
    if missing is not None:
        if decision != "REQUIRED":
            raise EvalsGeneratorError("Only REQUIRED may be blocked by missing authority")
        gap = _object(missing, "missing_authority")
        if set(gap) != {"owner", "required_input", "impact", "recovery"}:
            raise EvalsGeneratorError(
                "missing_authority must contain owner, required_input, impact, and recovery"
            )
        for field in ("owner", "required_input", "impact", "recovery"):
            _nonempty_text(gap.get(field), f"missing_authority.{field}")
        fulfillment = "BLOCKED_MISSING_INPUT"
    return {
        "applicability": decision,
        "fulfillment": fulfillment,
        "execution_status": "NOT_RUN",
        "freshness": "CURRENT",
        "reason": item["existing_ac_sufficiency"],
        "additional_judgment": item["additional_judgment"],
        "delivery_effect": dict(effect),
        "next_action": dict(action),
        "missing_authority": missing,
    }


def _validate_fixtures(
    project_root: Path,
    fixtures_ref: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    ref = _exact_ref(project_root, fixtures_ref, "fixtures_ref")
    payload = read_json(project_root / ref["path"])
    if payload.get("schema_version") != "product-eval-fixtures.v1":
        raise EvalsGeneratorError("fixtures must use product-eval-fixtures.v1")
    if payload.get("version") != ref["version"]:
        raise EvalsGeneratorError("fixtures version differs from its exact ref")
    fixtures = _nonempty_list(payload.get("fixtures"), "fixtures")
    indexed: dict[str, dict[str, Any]] = {}
    for fixture in fixtures:
        row = _object(fixture, "fixture")
        fixture_id = _nonempty_text(row.get("fixture_id"), "fixture.fixture_id")
        _nonempty_text(row.get("case_id"), "fixture.case_id")
        if fixture_id in indexed:
            raise EvalsGeneratorError("fixture_id must be unique")
        indexed[fixture_id] = row
    return ref, indexed


def validate_product_eval_pack(
    project_root: Path,
    pack: Any,
    *,
    expected_candidate_ref: dict[str, Any],
    expected_fixtures_ref: dict[str, Any],
    previous_pack_ref: dict[str, Any] | None = None,
    previous_version: int | None = None,
) -> dict[str, Any]:
    """Validate the complete, intentionally small Product Eval Pack v1."""

    item = _object(pack, "Product Eval Pack")
    required = {
        "schema_version",
        "version",
        "status",
        "candidate_ref",
        "applicability",
        "execution_status",
        "producer",
        "purpose",
        "scenarios",
        "rubric",
        "ground_truth_provenance",
        "coverage",
        "unknowns",
        "execution_handoff",
        "security",
        "evaluator_contract",
        "cases",
        "revision",
    }
    missing = required - set(item)
    if missing:
        raise EvalsGeneratorError(f"Product Eval Pack is incomplete: missing {sorted(missing)[0]}")
    extras = set(item) - required
    if extras:
        raise EvalsGeneratorError(
            f"Product Eval Pack closed contract has unsupported field {sorted(extras)[0]}"
        )
    if item.get("schema_version") != "product-eval-pack.v1":
        raise EvalsGeneratorError("Product Eval Pack schema_version is invalid")
    version = item.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise EvalsGeneratorError("Product Eval Pack version must be a positive integer")
    if item.get("status") != "SPECIFICATION_REVIEW_PENDING":
        raise EvalsGeneratorError("Product Eval Pack cannot claim Review or execution")
    if not _same_ref(item.get("candidate_ref"), expected_candidate_ref):
        raise EvalsGeneratorError("Product Eval Pack does not bind the exact Candidate")
    if item.get("applicability") not in {"RECOMMENDED", "REQUIRED"}:
        raise EvalsGeneratorError("NOT_NEEDED must not generate an empty Product Eval Pack")
    if item.get("execution_status") != "NOT_RUN":
        raise EvalsGeneratorError("Product Eval Pack cannot claim execution")
    _identity(item.get("producer"), "producer")

    purpose = _object(item.get("purpose"), "purpose")
    if set(purpose) != {"reason", "in_scope", "out_of_scope"}:
        raise EvalsGeneratorError("purpose must answer reason, in_scope, and out_of_scope")
    _nonempty_text(purpose.get("reason"), "purpose.reason", explanatory=True)
    _nonempty_list(purpose.get("in_scope"), "purpose.in_scope")
    if not isinstance(purpose.get("out_of_scope"), list):
        raise EvalsGeneratorError("purpose.out_of_scope must be a list")

    scenarios = _object(item.get("scenarios"), "scenarios")
    if set(scenarios) != {"normal", "boundary", "failure", "adversarial"}:
        raise EvalsGeneratorError("scenarios must cover normal, boundary, failure, and adversarial")
    for case_class in ("normal", "boundary", "failure", "adversarial"):
        _nonempty_list(scenarios.get(case_class), f"scenarios.{case_class}")

    rubric = _object(item.get("rubric"), "rubric")
    if set(rubric) != {"multiple_valid_outputs", "criteria", "unacceptable"}:
        raise EvalsGeneratorError("rubric must define quality boundaries")
    if not isinstance(rubric.get("multiple_valid_outputs"), bool):
        raise EvalsGeneratorError("rubric.multiple_valid_outputs must be boolean")
    for criterion in _nonempty_list(rubric.get("criteria"), "rubric.criteria"):
        row = _object(criterion, "rubric criterion")
        _nonempty_text(row.get("criterion"), "rubric criterion name")
        _nonempty_text(row.get("pass_condition"), "rubric pass_condition")
    _nonempty_list(rubric.get("unacceptable"), "rubric.unacceptable")

    provenance = _object(item.get("ground_truth_provenance"), "ground_truth_provenance")
    if set(provenance) != {"type", "statement", "exact_refs"}:
        raise EvalsGeneratorError("ground_truth_provenance must use the closed v1 shape")
    if provenance.get("type") != "CONTRACT_DERIVED_EXPECTATIONS":
        raise EvalsGeneratorError("Agent may not manufacture Ground Truth")
    _nonempty_text(provenance.get("statement"), "ground_truth_provenance.statement")
    for index, ref in enumerate(
        _nonempty_list(provenance.get("exact_refs"), "ground_truth_provenance.exact_refs")
    ):
        _exact_ref(project_root, ref, f"ground_truth_provenance.exact_refs[{index}]")

    coverage = _object(item.get("coverage"), "coverage")
    if set(coverage) != {"ac_refs", "known_gaps"}:
        raise EvalsGeneratorError("coverage must contain ac_refs and known_gaps")
    _nonempty_list(coverage.get("ac_refs"), "coverage.ac_refs")
    if not isinstance(coverage.get("known_gaps"), list):
        raise EvalsGeneratorError("coverage.known_gaps must be a list")

    unknowns = _object(item.get("unknowns"), "unknowns")
    if set(unknowns) != {"items", "blocked", "recovery_actions"}:
        raise EvalsGeneratorError("unknowns must expose items, blocked, and recovery_actions")
    if not isinstance(unknowns.get("items"), list) or not isinstance(
        unknowns.get("recovery_actions"), list
    ):
        raise EvalsGeneratorError("unknowns items and recovery_actions must be lists")
    if unknowns.get("blocked") is not False:
        raise EvalsGeneratorError("A blocked high-impact input must not produce a complete Pack")

    handoff = _object(item.get("execution_handoff"), "execution_handoff")
    if set(handoff) != {"requirements", "not_occurred"}:
        raise EvalsGeneratorError("execution_handoff must state requirements and absent execution")
    _nonempty_list(handoff.get("requirements"), "execution_handoff.requirements")
    not_occurred = handoff.get("not_occurred")
    if not isinstance(not_occurred, list) or set(not_occurred) != EXECUTION_ABSENCE:
        raise EvalsGeneratorError("execution_handoff must deny runtime, tests, and verdict")

    security = _object(item.get("security"), "security")
    if security != {"external_inputs": "UNTRUSTED_DATA_ONLY"}:
        raise EvalsGeneratorError("External content must remain untrusted data, never instructions")

    evaluator = _object(item.get("evaluator_contract"), "evaluator_contract")
    if set(evaluator) != {"contract_id", "fixtures_ref"}:
        raise EvalsGeneratorError("evaluator_contract must bind contract_id and fixtures_ref")
    _nonempty_text(evaluator.get("contract_id"), "evaluator_contract.contract_id")
    fixtures_ref, fixtures = _validate_fixtures(project_root, evaluator.get("fixtures_ref"))
    if not _same_ref(fixtures_ref, expected_fixtures_ref):
        raise EvalsGeneratorError("Product Eval Pack fixtures differ from the submitted fixtures")

    cases = _nonempty_list(item.get("cases"), "cases")
    case_ids: set[str] = set()
    fixture_ids: set[str] = set()
    observed_classes: set[str] = set()
    for case in cases:
        row = _object(case, "case")
        required_case = {"case_id", "class", "fixture_id", "oracle", "covers_ac"}
        if set(row) != required_case:
            raise EvalsGeneratorError("each case must use the closed v1 case contract")
        case_id = _nonempty_text(row.get("case_id"), "case.case_id")
        fixture_id = _nonempty_text(row.get("fixture_id"), "case.fixture_id")
        case_class = row.get("class")
        if case_class not in CASE_CLASSES:
            raise EvalsGeneratorError("case.class is invalid")
        _nonempty_text(row.get("oracle"), "case.oracle")
        _nonempty_list(row.get("covers_ac"), "case.covers_ac")
        if case_id in case_ids or fixture_id in fixture_ids:
            raise EvalsGeneratorError("case and fixture bindings must be one-to-one")
        if fixture_id not in fixtures or fixtures[fixture_id].get("case_id") != case_id:
            raise EvalsGeneratorError("case and fixture bindings differ")
        case_ids.add(case_id)
        fixture_ids.add(fixture_id)
        observed_classes.add(case_class)
    if observed_classes != CASE_CLASSES or fixture_ids != set(fixtures):
        raise EvalsGeneratorError("Pack must cover all four classes with exact fixture bijection")
    for case_class, ids in scenarios.items():
        expected_class = case_class.upper()
        for case_id in ids:
            if not any(row["case_id"] == case_id and row["class"] == expected_class for row in cases):
                raise EvalsGeneratorError("scenario index differs from structured cases")

    revision = _object(item.get("revision"), "revision")
    if set(revision) != {"supersedes_pack_ref", "correction"}:
        raise EvalsGeneratorError("revision must disclose supersedes_pack_ref and correction")
    if previous_pack_ref is None:
        if version != 1 or revision != {"supersedes_pack_ref": None, "correction": None}:
            raise EvalsGeneratorError("Initial Product Eval Pack must be version 1 without correction")
    else:
        if previous_version is None or version != previous_version + 1:
            raise EvalsGeneratorError("Corrected Product Eval Pack must create the next version")
        if not _same_ref(revision.get("supersedes_pack_ref"), previous_pack_ref):
            raise EvalsGeneratorError("Corrected Product Eval Pack must supersede the exact prior Pack")
        correction = _object(revision.get("correction"), "revision.correction")
        if set(correction) != {"actor", "reason", "changed_fields"}:
            raise EvalsGeneratorError("revision.correction must identify actor, reason, and fields")
        actor = _identity(correction.get("actor"), "revision.correction.actor")
        if actor["kind"] not in {"PRODUCT_MANAGER", "HOST_AGENT"}:
            raise EvalsGeneratorError("Pack correction actor is unauthorized")
        _nonempty_text(correction.get("reason"), "revision.correction.reason")
        _nonempty_list(correction.get("changed_fields"), "revision.correction.changed_fields")
    return item


def validate_pack_stage_submission(
    project_root: Path,
    submission: Any,
    *,
    expected_candidate_ref: dict[str, Any],
    expected_applicability: str,
    previous_pack_ref: dict[str, Any] | None = None,
    previous_version: int | None = None,
) -> dict[str, Any]:
    """Validate one Host-authored Pack before Controller staging."""

    item = _object(submission, "Product Eval Pack submission")
    required = {
        "schema_version",
        "candidate_ref",
        "build_attempt",
        "applicability_assessment",
        "eval_pack_ref",
        "fixtures_ref",
    }
    if set(item) != required:
        raise EvalsGeneratorError("Product Eval Pack submission must use the closed v1 contract")
    if item.get("schema_version") != "product-eval-pack-submission.v1":
        raise EvalsGeneratorError("Product Eval Pack submission schema_version is invalid")
    if not _same_ref(item.get("candidate_ref"), expected_candidate_ref):
        raise EvalsGeneratorError("Product Eval Pack submission does not bind the exact Candidate")
    builder = _identity(item.get("build_attempt"), "build_attempt")
    if builder["kind"] != "HOST_AGENT":
        raise EvalsGeneratorError("Product Eval Pack must be authored by the current HOST_AGENT")
    assessment = validate_applicability_assessment(
        item.get("applicability_assessment"),
        expected_candidate_ref=expected_candidate_ref,
    )
    if assessment["applicability"] != expected_applicability:
        raise EvalsGeneratorError("Applicability assessment differs from the exact Candidate metadata")
    if assessment["fulfillment"] == "BLOCKED_MISSING_INPUT":
        raise EvalsGeneratorError("Missing high-impact authority must remain blocked without a Pack")
    pack_ref = _exact_ref(project_root, item.get("eval_pack_ref"), "eval_pack_ref")
    fixtures_ref = _exact_ref(project_root, item.get("fixtures_ref"), "fixtures_ref")
    pack = read_json(project_root / pack_ref["path"])
    if pack.get("version") != pack_ref["version"]:
        raise EvalsGeneratorError("Product Eval Pack version differs from its exact ref")
    if pack.get("producer") != builder:
        raise EvalsGeneratorError("Product Eval Pack producer differs from build_attempt")
    if pack.get("applicability") != expected_applicability:
        raise EvalsGeneratorError("Product Eval Pack applicability differs from Candidate metadata")
    validate_product_eval_pack(
        project_root,
        pack,
        expected_candidate_ref=expected_candidate_ref,
        expected_fixtures_ref=fixtures_ref,
        previous_pack_ref=previous_pack_ref,
        previous_version=previous_version,
    )
    return {
        "assessment": assessment,
        "pack": pack,
        "pack_ref": pack_ref,
        "fixtures_ref": fixtures_ref,
        "build_identity": builder,
    }


def validate_assessment_submission(
    submission: Any,
    *,
    expected_candidate_ref: dict[str, Any],
    expected_applicability: str,
) -> dict[str, Any]:
    """Validate a blocked assessment without accepting a placeholder Pack."""

    item = _object(submission, "Product Eval assessment submission")
    required = {
        "schema_version",
        "candidate_ref",
        "build_attempt",
        "applicability_assessment",
    }
    if set(item) != required:
        raise EvalsGeneratorError("Product Eval assessment submission must use the closed v1 contract")
    if item.get("schema_version") != "product-eval-assessment-submission.v1":
        raise EvalsGeneratorError("Product Eval assessment submission schema_version is invalid")
    if not _same_ref(item.get("candidate_ref"), expected_candidate_ref):
        raise EvalsGeneratorError("Product Eval assessment does not bind the exact Candidate")
    builder = _identity(item.get("build_attempt"), "build_attempt")
    if builder["kind"] != "HOST_AGENT":
        raise EvalsGeneratorError("Product Eval assessment must be authored by the current HOST_AGENT")
    assessment = validate_applicability_assessment(
        item.get("applicability_assessment"),
        expected_candidate_ref=expected_candidate_ref,
    )
    if assessment["applicability"] != expected_applicability:
        raise EvalsGeneratorError("Applicability assessment differs from the exact Candidate metadata")
    if assessment["fulfillment"] != "BLOCKED_MISSING_INPUT":
        raise EvalsGeneratorError("Assessment-only staging is reserved for missing high-impact authority")
    return {"assessment": assessment, "build_identity": builder}


def validate_product_eval_review(
    project_root: Path,
    review: Any,
    *,
    expected_candidate_ref: dict[str, Any],
    expected_fixtures_ref: dict[str, Any],
    expected_pack_ref: dict[str, Any],
    producer: dict[str, Any],
) -> dict[str, Any]:
    """Validate an independently authored Product Eval Review v1."""

    item = _object(review, "Product Eval Review")
    required = {
        "schema_version",
        "status",
        "execution_status",
        "reviewer_role",
        "reviewer_authority",
        "reviewer",
        "reviewed_at",
        "subjects",
        "independence_receipt",
        "findings",
        "new_high_findings",
        "evidence_boundary",
    }
    if set(item) != required:
        raise EvalsGeneratorError("Product Eval Review must use the closed v1 contract")
    if item.get("schema_version") != "product-eval-review.v1":
        raise EvalsGeneratorError("Product Eval Review schema_version is invalid")
    if item.get("status") != "REVIEWED" or item.get("execution_status") != "NOT_RUN":
        raise EvalsGeneratorError("Product Eval Review may review only the specification")
    if item.get("reviewer_role") != "INDEPENDENT_TESTABILITY_REVIEWER":
        raise EvalsGeneratorError("Product Eval Review role is invalid")
    if item.get("reviewer_authority") != "ADVISORY_ONLY":
        raise EvalsGeneratorError("Product Eval Review cannot approve the product")
    reviewer = _identity(item.get("reviewer"), "reviewer")
    builder = _identity(producer, "producer")
    if reviewer == builder:
        raise EvalsGeneratorError("Product Eval Review requires an independent different instance")
    _iso_datetime(item.get("reviewed_at"), "reviewed_at")
    subjects = _object(item.get("subjects"), "subjects")
    if set(subjects) != {"prd_draft_ref", "fixtures_ref", "eval_pack_ref"}:
        raise EvalsGeneratorError("Product Eval Review subjects are incomplete")
    for name, expected in (
        ("prd_draft_ref", expected_candidate_ref),
        ("fixtures_ref", expected_fixtures_ref),
        ("eval_pack_ref", expected_pack_ref),
    ):
        if not _same_ref(subjects.get(name), expected):
            raise EvalsGeneratorError(f"Product Eval Review does not bind exact {name}")
        _exact_ref(project_root, subjects[name], f"subjects.{name}")
    independence = _object(item.get("independence_receipt"), "independence_receipt")
    expected_independence = {
        "different_instance",
        "isolated_context",
        "frozen_read_only_inputs",
        "first_round_findings_isolated",
    }
    if set(independence) != expected_independence or any(
        independence.get(field) is not True for field in expected_independence
    ):
        raise EvalsGeneratorError("Product Eval Review lacks an independent read-only receipt")
    findings = item.get("findings")
    if not isinstance(findings, list):
        raise EvalsGeneratorError("findings must be a list")
    finding_fields = {
        "finding_id",
        "severity",
        "location",
        "concern",
        "impact",
        "recommendation",
        "status",
        "disposition",
    }
    finding_ids: set[str] = set()
    for finding in findings:
        row = _object(finding, "finding")
        if set(row) != finding_fields:
            raise EvalsGeneratorError("Each Product Eval Finding must use the closed v1 contract")
        finding_id = _nonempty_text(row.get("finding_id"), "finding_id")
        if finding_id in finding_ids:
            raise EvalsGeneratorError("Product Eval finding_id must be unique")
        finding_ids.add(finding_id)
        if row.get("severity") not in {"LOW", "MEDIUM", "HIGH"}:
            raise EvalsGeneratorError("Product Eval Finding severity is invalid")
        for field in ("location", "concern", "impact", "recommendation", "disposition"):
            _nonempty_text(row.get(field), f"finding.{field}")
        if row.get("status") not in {"CLOSED", "DISPOSITIONED"}:
            raise EvalsGeneratorError("Every substantive Finding must be closed or dispositioned")
    if item.get("new_high_findings") != 0:
        raise EvalsGeneratorError("Product Eval Review cannot complete with new HIGH Findings")
    evidence = _object(item.get("evidence_boundary"), "evidence_boundary")
    expected_evidence = {
        "runtime_execution": "NOT_RUN",
        "test_execution": "NOT_RUN",
        "independent_reader_validation": "NOT_RUN",
    }
    if evidence != expected_evidence:
        raise EvalsGeneratorError("Product Eval Review must preserve the NOT_RUN evidence boundary")
    return item


def validate_execution_receipt(
    project_root: Path,
    receipt: Any,
    *,
    expected_pack_ref: dict[str, Any],
) -> dict[str, Any]:
    """Validate the future execution-side contract; BPG never produces it."""

    item = _object(receipt, "Product Eval execution receipt")
    required = {
        "schema_version",
        "status",
        "pack_ref",
        "executor",
        "execution_id",
        "executed_at",
        "observations",
        "verdict",
    }
    if set(item) != required:
        raise EvalsGeneratorError("Product Eval execution receipt must use the closed v1 contract")
    if item.get("schema_version") != "product-eval-execution-receipt.v1":
        raise EvalsGeneratorError("Product Eval execution receipt schema_version is invalid")
    if item.get("status") != "COMPLETED":
        raise EvalsGeneratorError("Product Eval execution receipt status is invalid")
    if not _same_ref(item.get("pack_ref"), expected_pack_ref):
        raise EvalsGeneratorError("Product Eval execution receipt does not bind the exact Pack")
    _exact_ref(project_root, item.get("pack_ref"), "pack_ref")
    executor = _object(item.get("executor"), "executor")
    if set(executor) != {"kind", "id", "authorization_ref"}:
        raise EvalsGeneratorError("executor requires explicit authorization_ref")
    if executor.get("kind") not in {"TEST_GRAPH", "AUTHORIZED_EXECUTOR"}:
        raise EvalsGeneratorError("BPG or a Product Agent cannot execute Product Evals")
    _nonempty_text(executor.get("id"), "executor.id")
    _exact_ref(project_root, executor.get("authorization_ref"), "executor.authorization_ref")
    _nonempty_text(item.get("execution_id"), "execution_id")
    _iso_datetime(item.get("executed_at"), "executed_at")
    observations = _nonempty_list(item.get("observations"), "observations")
    observation_fields = {
        "case_id",
        "fixture_id",
        "observed_output",
        "result",
        "evidence_refs",
    }
    observed_cases: set[str] = set()
    for observation in observations:
        row = _object(observation, "observation")
        if set(row) != observation_fields:
            raise EvalsGeneratorError("Each execution observation must use the closed v1 contract")
        case_id = _nonempty_text(row.get("case_id"), "observation.case_id")
        if case_id in observed_cases:
            raise EvalsGeneratorError("execution observations must contain one row per case")
        observed_cases.add(case_id)
        _nonempty_text(row.get("fixture_id"), "observation.fixture_id")
        if row.get("observed_output") is None:
            raise EvalsGeneratorError("observation.observed_output must record the actual output")
        if row.get("result") not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            raise EvalsGeneratorError("execution observation result is invalid")
        for index, ref in enumerate(
            _nonempty_list(row.get("evidence_refs"), "observation.evidence_refs")
        ):
            _exact_ref(project_root, ref, f"observation.evidence_refs[{index}]")
    if item.get("verdict") not in {"PASS", "FAIL", "INCONCLUSIVE"}:
        raise EvalsGeneratorError("execution verdict is invalid")
    return item


def derive_evals_status(
    preparation: Any,
    *,
    current_candidate_ref: dict[str, Any],
) -> dict[str, str]:
    """Render all four truth dimensions without inferring execution or delivery."""

    item = _object(preparation, "Product Evals preparation state")
    applicability = item.get("applicability")
    fulfillment = item.get("fulfillment")
    if applicability not in APPLICABILITY_VALUES:
        raise EvalsGeneratorError("Product Evals preparation applicability is invalid")
    if fulfillment not in FULFILLMENT_VALUES:
        raise EvalsGeneratorError("Product Evals preparation fulfillment is invalid")
    if item.get("execution_status") != "NOT_RUN":
        raise EvalsGeneratorError("BPG Product Evals preparation execution must remain NOT_RUN")
    freshness = "CURRENT" if _same_ref(item.get("candidate_ref"), current_candidate_ref) else "STALE"
    return {
        "applicability": applicability,
        "fulfillment": fulfillment,
        "execution": "NOT_RUN",
        "freshness": freshness,
        "delivery": "LOCAL_ONLY",
    }
