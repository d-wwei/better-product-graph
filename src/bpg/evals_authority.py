"""Deterministic authority checks for a reviewed Product Eval Pack."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .schema_runtime import SchemaRuntime, SchemaValidationError
from .storage import (
    IntegrityError,
    assert_managed_path,
    read_json,
    require_iso_datetime,
    sha256_file,
)


class EvalsAuthorityError(ValueError):
    """A claimed REVIEWED Eval Pack lacks exact, independent evidence."""


PACK_ROLES = frozenset({"eval_pack"})
REVIEW_ROLES = frozenset({"eval_pack_review"})
CANDIDATE_ROLES = frozenset({"prd_candidate", "prd_draft"})
FIXTURE_ROLES = frozenset({"eval_fixtures"})
PROVENANCE_ROLES = frozenset(
    {
        "acceptance_contract",
        "decision",
        "decision_record",
        "evidence",
        "knowledge",
        "product_plan",
        "roadmap",
        "shared_contract",
        "slice",
    }
)
PACK_SCHEMA_VERSIONS = frozenset(
    {"better-product-graph.eval-pack.v0.2", "better-product-graph.eval-pack.v1"}
)
REVIEW_SCHEMA_VERSIONS = frozenset(
    {
        "better-product-graph.eval-pack-review.v0.1",
        "better-product-graph.eval-pack-review.v1",
    }
)


def _ref_identity(ref: Any) -> tuple[Any, Any]:
    if not isinstance(ref, dict):
        return None, None
    return ref.get("path"), ref.get("hash")


def _same_ref(left: Any, right: Any) -> bool:
    if _ref_identity(left) != _ref_identity(right):
        return False
    left_version = left.get("version") if isinstance(left, dict) else None
    right_version = right.get("version") if isinstance(right, dict) else None
    return (
        left_version is not None
        and right_version is not None
        and left_version == right_version
    )


def _artifact_values(artifact_refs: Any) -> list[dict[str, Any]]:
    values: Iterable[Any]
    if isinstance(artifact_refs, dict):
        values = artifact_refs.values()
    elif isinstance(artifact_refs, list):
        values = artifact_refs
    else:
        values = ()
    return [item for item in values if isinstance(item, dict)]


def _require_role(
    ref: dict[str, Any],
    roles: frozenset[str],
    artifacts: list[dict[str, Any]],
    label: str,
    *,
    origin_nodes: frozenset[str] | None = None,
    committed_attempt_ids: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    matches = [
        item
        for item in artifacts
        if item.get("role") in roles and _same_ref(item, ref)
    ]
    canonical = {
        (item.get("path"), item.get("hash"), item.get("role"))
        for item in matches
    }
    if len(canonical) != 1:
        raise EvalsAuthorityError(
            f"{label} must have exactly one bound artifact role in {sorted(roles)}"
        )
    if origin_nodes is not None:
        typed = [
            item
            for item in matches
            if item.get("origin_node_id") in origin_nodes
            and isinstance(item.get("origin_attempt_id"), str)
            and bool(item["origin_attempt_id"])
            and item["origin_attempt_id"] in committed_attempt_ids
            and any(
                node_result.get("role") == "node_result"
                and node_result.get("node_id") == item["origin_node_id"]
                and node_result.get("attempt_id") == item["origin_attempt_id"]
                for node_result in artifacts
            )
        ]
        if not typed:
            raise EvalsAuthorityError(
                f"{label} lacks Controller-owned origin from {sorted(origin_nodes)}"
            )
        return typed[0]
    return matches[0]


def _resolve_exact_file(
    project_root: Path,
    ref: Any,
    dispatched_input_hashes: dict[str, str],
    label: str,
) -> Path:
    if (
        not isinstance(ref, dict)
        or not isinstance(ref.get("path"), str)
        or not isinstance(ref.get("hash"), str)
        or not isinstance(ref.get("version"), (str, int))
    ):
        raise EvalsAuthorityError(f"{label} exact path/hash/version ref is missing")
    if dispatched_input_hashes.get(ref["path"]) != ref["hash"]:
        raise EvalsAuthorityError(f"{label} is absent from exact dispatched inputs")
    if "resolved_hash" in ref and ref.get("resolved_hash") != ref["hash"]:
        raise EvalsAuthorityError(f"{label} resolved hash conflicts with its exact ref")
    try:
        path = assert_managed_path(project_root, Path(ref["path"]))
    except IntegrityError as error:
        raise EvalsAuthorityError(f"{label} path is not project-managed") from error
    if not path.is_file() or path.is_symlink() or sha256_file(path) != ref["hash"]:
        raise EvalsAuthorityError(f"{label} file/hash authority is invalid")
    return path


def _validate_candidate_binding(
    project_root: Path,
    candidate_ref: Any,
    expected_candidate_ref: dict[str, Any],
    artifacts: list[dict[str, Any]],
    dispatched_input_hashes: dict[str, str],
    label: str,
    committed_attempt_ids: frozenset[str],
) -> None:
    if (
        not isinstance(candidate_ref, dict)
        or candidate_ref.get("hash") != expected_candidate_ref.get("hash")
        or candidate_ref.get("version") != expected_candidate_ref.get("version")
    ):
        raise EvalsAuthorityError(f"{label} does not bind the exact Candidate hash/version")
    _require_role(
        candidate_ref,
        CANDIDATE_ROLES,
        artifacts,
        label,
        origin_nodes=frozenset({"prd.generate"}),
        committed_attempt_ids=committed_attempt_ids,
    )
    _resolve_exact_file(project_root, candidate_ref, dispatched_input_hashes, label)


def _validate_provenance(
    project_root: Path,
    provenance: Any,
    artifacts: list[dict[str, Any]],
    dispatched_input_hashes: dict[str, str],
) -> None:
    if (
        not isinstance(provenance, dict)
        or provenance.get("type") != "CONTRACT_DERIVED_EXPECTATIONS"
        or not isinstance(provenance.get("statement"), str)
        or not provenance["statement"].strip()
        or not isinstance(provenance.get("exact_refs"), list)
        or not provenance["exact_refs"]
    ):
        raise EvalsAuthorityError(
            "Ground Truth provenance must be structured CONTRACT_DERIVED_EXPECTATIONS"
        )
    for index, ref in enumerate(provenance["exact_refs"]):
        _resolve_exact_file(
            project_root,
            ref,
            dispatched_input_hashes,
            f"Ground Truth provenance ref {index}",
        )
        matches = [
            item
            for item in artifacts
            if item.get("role") in PROVENANCE_ROLES and _same_ref(item, ref)
        ]
        canonical = {
            (item.get("path"), item.get("hash"), item.get("version"), item.get("role"))
            for item in matches
        }
        if len(canonical) != 1:
            raise EvalsAuthorityError(
                "Ground Truth provenance refs require one allowlisted committed contract role"
            )


def _identity(value: Any, label: str) -> tuple[str, str]:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("kind"), str)
        or not value["kind"]
        or not isinstance(value.get("id"), str)
        or not value["id"]
    ):
        raise EvalsAuthorityError(f"{label} identity must contain kind and id")
    return value["kind"], value["id"]


def _all_findings_closed(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict)
        and isinstance(item.get("finding_id"), str)
        and item.get("status") == "CLOSED"
        for item in value
    )


def validate_reviewed_evals(
    project_root: Path,
    skill_root: Path,
    evals: dict[str, Any],
    *,
    expected_candidate_ref: dict[str, Any],
    artifact_refs: Any,
    dispatched_input_hashes: dict[str, str],
    committed_attempt_ids: frozenset[str],
) -> None:
    """Validate Pack/review specification consistency, never release authority."""

    if not isinstance(evals, dict) or evals.get("fulfillment") != "REVIEWED":
        raise EvalsAuthorityError("reviewed Evals metadata is missing")
    if evals.get("applicability") != "REQUIRED":
        raise EvalsAuthorityError("REVIEWED Evals are only valid when applicability is REQUIRED")
    if evals.get("execution_status") != "NOT_RUN":
        raise EvalsAuthorityError(
            "Product Eval Pack execution_status must remain NOT_RUN until downstream execution"
        )
    artifacts = _artifact_values(artifact_refs)
    pack_ref = evals.get("pack_ref")
    review_ref = evals.get("review_ref")
    _require_role(
        pack_ref,
        PACK_ROLES,
        artifacts,
        "Eval Pack",
        origin_nodes=frozenset({"prd.generate"}),
        committed_attempt_ids=committed_attempt_ids,
    )
    _require_role(
        review_ref,
        REVIEW_ROLES,
        artifacts,
        "Eval Pack review",
        origin_nodes=frozenset({"review.parallel"}),
        committed_attempt_ids=committed_attempt_ids,
    )
    pack_path = _resolve_exact_file(
        project_root, pack_ref, dispatched_input_hashes, "Eval Pack"
    )
    review_path = _resolve_exact_file(
        project_root, review_ref, dispatched_input_hashes, "Eval Pack review"
    )
    try:
        pack = read_json(pack_path)
        review = read_json(review_path)
        schemas = SchemaRuntime(skill_root)
        schemas.validate("eval-pack.schema.json", pack)
        schemas.validate("eval-pack-review.schema.json", review)
    except (IntegrityError, SchemaValidationError) as error:
        raise EvalsAuthorityError(f"Eval artifact schema is invalid: {error}") from error
    if pack.get("schema_version") not in PACK_SCHEMA_VERSIONS:
        raise EvalsAuthorityError("Eval Pack schema_version is not allowlisted")
    if review.get("schema_version") not in REVIEW_SCHEMA_VERSIONS:
        raise EvalsAuthorityError("Eval Pack review schema_version is not allowlisted")
    if pack.get("applicability") != "REQUIRED" or pack.get("execution_status") != "NOT_RUN":
        raise EvalsAuthorityError("Eval Pack applicability/execution boundary is invalid")
    cases = pack.get("cases")
    if (
        not isinstance(cases, list)
        or not cases
        or not all(
            isinstance(item, dict)
            and isinstance(item.get("case_id"), str)
            and bool(item["case_id"])
            and "expected_outcome" in item
            for item in cases
        )
    ):
        raise EvalsAuthorityError("Eval Pack must contain structured evaluator cases")
    if review.get("execution_status") != "NOT_RUN":
        raise EvalsAuthorityError("Eval Pack review cannot claim runtime execution")
    _validate_candidate_binding(
        project_root,
        pack.get("candidate_ref"),
        expected_candidate_ref,
        artifacts,
        dispatched_input_hashes,
        "Eval Pack Candidate",
        committed_attempt_ids,
    )
    _validate_provenance(
        project_root,
        pack.get("ground_truth_provenance"),
        artifacts,
        dispatched_input_hashes,
    )
    if evals.get("ground_truth_provenance") != pack.get("ground_truth_provenance"):
        raise EvalsAuthorityError("Evals metadata must preserve exact Pack Ground Truth provenance")
    producer = _identity(pack.get("producer"), "Eval Pack producer")
    reviewer = _identity(review.get("reviewer"), "Eval Pack reviewer")
    if producer == reviewer:
        raise EvalsAuthorityError("Eval Pack REVIEWED status requires an independent reviewer")
    try:
        require_iso_datetime(review.get("reviewed_at"), "Eval Pack reviewed_at")
    except IntegrityError as error:
        raise EvalsAuthorityError(str(error)) from error
    if (
        review.get("status") != "REVIEWED"
        or review.get("reviewer_role") != "INDEPENDENT_TESTABILITY_REVIEWER"
        or review.get("reviewer_authority") != "ADVISORY_ONLY"
        or review.get("new_high_findings") != 0
        or not _all_findings_closed(review.get("finding_closure"))
    ):
        raise EvalsAuthorityError("Eval Pack review conclusion/authority is invalid")
    subjects = review.get("subjects", {})
    if not _same_ref(subjects.get("eval_pack_ref"), pack_ref):
        raise EvalsAuthorityError("Eval Pack review does not bind the exact Pack")
    _validate_candidate_binding(
        project_root,
        subjects.get("prd_draft_ref"),
        expected_candidate_ref,
        artifacts,
        dispatched_input_hashes,
        "Eval review Candidate",
        committed_attempt_ids,
    )
    evaluator_contract = pack.get("evaluator_contract", {})
    fixtures_ref = evaluator_contract.get("fixtures_ref")
    if not _same_ref(subjects.get("fixtures_ref"), fixtures_ref):
        raise EvalsAuthorityError("Eval Pack review fixtures differ from Pack fixtures")
    _require_role(
        fixtures_ref,
        FIXTURE_ROLES,
        artifacts,
        "Eval fixtures",
        origin_nodes=frozenset({"prd.generate"}),
        committed_attempt_ids=committed_attempt_ids,
    )
    _resolve_exact_file(
        project_root, fixtures_ref, dispatched_input_hashes, "Eval fixtures"
    )
    boundary = review.get("evidence_boundary")
    if boundary != {
        "runtime_execution": "NOT_RUN",
        "test_execution": "NOT_RUN",
        "independent_reader_validation": "NOT_RUN",
    }:
        raise EvalsAuthorityError(
            "Eval review evidence boundary must state runtime/test/reader NOT_RUN"
        )
