"""Validation, lossless join, and bounded-loop mechanics for advisory Agent Reviews."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .contracts import PolicyViolation, validate_node_result_producer


REQUIRED_LOGICAL_ROLES = frozenset({"product", "engineering_feasibility", "testability"})
AGGREGATE_SEMANTIC_FIELDS = frozenset(
    {
        "schema_version",
        "authority",
        "candidate_ref",
        "attempts",
        "findings",
        "disagreements",
        "dispositions",
    }
)
AGGREGATE_ARTIFACT_FIELDS = AGGREGATE_SEMANTIC_FIELDS - {"dispositions"}
CANDIDATE_REF_FIELDS = frozenset({"path", "hash", "version"})
REVIEW_ATTEMPT_FIELDS = frozenset({"attempt_id", "status", "roles_covered"})
REVIEW_FINDING_FIELDS = frozenset(
    {
        "finding_id",
        "topic_id",
        "stance",
        "concern",
        "concern_level",
        "basis_refs",
        "upstream_commitment_refs",
        "affected_scope",
        "possible_impact",
        "professional_recommendation",
        "confidence",
        "confidence_basis",
        "reviewer_role",
        "reviewer_profile",
        "cross_check_status",
        "repair_target",
        "disposition",
    }
)
DISAGREEMENT_FIELDS = frozenset({"topic_id", "finding_ids", "findings", "stances"})
DISPOSITION_ARTIFACT_FIELDS = frozenset(
    {"schema_version", "candidate_hash", "candidate_version", "dispositions"}
)
DISPOSITION_FIELDS = frozenset({"finding_id", "status", "repair_scope", "reason"})
AGGREGATE_ARTIFACT_REF_FIELDS = frozenset(
    {"role", "path", "hash", "version", "declared_role"}
)


class ReviewContractError(ValueError):
    """A Reviewer attempt crosses authority or exact-version boundaries."""


def _closed_mapping(value: Any, allowed: frozenset[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewContractError(f"{path} must be an object")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ReviewContractError(f"{path}.{unknown[0]} is an unknown field")
    return value


def _closed_mapping_list(value: Any, allowed: frozenset[str], path: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ReviewContractError(f"{path} must be a list")
    return [
        _closed_mapping(item, allowed, f"{path}[{index}]")
        for index, item in enumerate(value)
    ]


def _required_closed_mapping_list(
    container: dict[str, Any],
    field: str,
    allowed: frozenset[str],
    path: str,
) -> list[dict[str, Any]]:
    if field not in container:
        raise ReviewContractError(f"{path} is required")
    return _closed_mapping_list(container[field], allowed, path)


def _validate_aggregate_collection_cardinality(
    *,
    attempts: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    disagreements: list[dict[str, Any]],
    dispositions: list[dict[str, Any]],
    attempts_path: str,
    findings_path: str,
    disagreements_path: str,
    dispositions_path: str,
) -> None:
    """Enforce the aggregate collection matrix without inventing a Finding."""

    if not attempts:
        raise ReviewContractError(f"{attempts_path} must be a non-empty list")
    for index, attempt in enumerate(attempts):
        attempt_path = f"{attempts_path}[{index}]"
        if not isinstance(attempt.get("attempt_id"), str) or not attempt["attempt_id"]:
            raise ReviewContractError(f"{attempt_path}.attempt_id must be non-empty")
        if not isinstance(attempt.get("status"), str) or not attempt["status"]:
            raise ReviewContractError(f"{attempt_path}.status must be non-empty")
        roles = attempt.get("roles_covered")
        if (
            not isinstance(roles, list)
            or not roles
            or any(not isinstance(role, str) or not role for role in roles)
            or len(roles) != len(set(roles))
        ):
            raise ReviewContractError(
                f"{attempt_path}.roles_covered must be a unique non-empty role list"
            )

    finding_ids: list[str] = []
    for index, finding in enumerate(findings):
        finding_id = finding.get("finding_id")
        if not isinstance(finding_id, str) or not finding_id:
            raise ReviewContractError(
                f"{findings_path}[{index}].finding_id must be non-empty"
            )
        finding_ids.append(finding_id)
    if len(finding_ids) != len(set(finding_ids)):
        raise ReviewContractError(f"{findings_path} must contain unique Finding IDs")

    disposition_ids: list[str] = []
    for index, disposition in enumerate(dispositions):
        disposition_path = f"{dispositions_path}[{index}]"
        finding_id = disposition.get("finding_id")
        if not isinstance(finding_id, str) or not finding_id:
            raise ReviewContractError(f"{disposition_path}.finding_id must be non-empty")
        if not isinstance(disposition.get("status"), str) or not disposition["status"]:
            raise ReviewContractError(f"{disposition_path}.status must be non-empty")
        disposition_ids.append(finding_id)

    if not finding_ids and disposition_ids:
        raise ReviewContractError(
            f"{dispositions_path} must be [] when {findings_path} is []"
        )
    if finding_ids and (
        len(disposition_ids) != len(set(disposition_ids))
        or sorted(disposition_ids) != sorted(finding_ids)
    ):
        raise ReviewContractError(
            f"{dispositions_path} must close every {findings_path} ID exactly once"
        )

    known_findings = set(finding_ids)
    for index, disagreement in enumerate(disagreements):
        refs = disagreement.get("finding_ids", disagreement.get("findings", []))
        unknown = [finding_id for finding_id in refs if finding_id not in known_findings]
        if unknown:
            raise ReviewContractError(
                f"{disagreements_path}[{index}] references unknown Finding {unknown[0]}"
            )


def validate_review_aggregate_semantic(value: Any) -> dict[str, Any]:
    """Validate closed-world Host semantics before any artifact or Run write."""

    output = _closed_mapping(value, AGGREGATE_SEMANTIC_FIELDS, "semantic_output")
    _closed_mapping(output.get("candidate_ref"), CANDIDATE_REF_FIELDS, "semantic_output.candidate_ref")
    attempts = _required_closed_mapping_list(
        output, "attempts", REVIEW_ATTEMPT_FIELDS, "semantic_output.attempts"
    )
    findings = _required_closed_mapping_list(
        output, "findings", REVIEW_FINDING_FIELDS, "semantic_output.findings"
    )
    if "disagreements" not in output:
        raise ReviewContractError("semantic_output.disagreements is required")
    disagreements = validate_aggregate_disagreements(
        output["disagreements"], path="semantic_output.disagreements"
    )
    dispositions = _required_closed_mapping_list(
        output, "dispositions", DISPOSITION_FIELDS, "semantic_output.dispositions"
    )
    _validate_aggregate_collection_cardinality(
        attempts=attempts,
        findings=findings,
        disagreements=disagreements,
        dispositions=dispositions,
        attempts_path="semantic_output.attempts",
        findings_path="semantic_output.findings",
        disagreements_path="semantic_output.disagreements",
        dispositions_path="semantic_output.dispositions",
    )
    return output


def validate_review_aggregate_artifacts(
    aggregate: Any,
    dispositions: Any,
    artifact_refs: Any,
) -> None:
    """Validate both exact JSON payloads and their Host-provided refs as closed mappings."""

    aggregate_payload = _closed_mapping(
        aggregate, AGGREGATE_ARTIFACT_FIELDS, "review_aggregate"
    )
    _closed_mapping(
        aggregate_payload.get("candidate_ref"),
        CANDIDATE_REF_FIELDS,
        "review_aggregate.candidate_ref",
    )
    attempts = _required_closed_mapping_list(
        aggregate_payload,
        "attempts",
        REVIEW_ATTEMPT_FIELDS,
        "review_aggregate.attempts",
    )
    findings = _required_closed_mapping_list(
        aggregate_payload,
        "findings",
        REVIEW_FINDING_FIELDS,
        "review_aggregate.findings",
    )
    if "disagreements" not in aggregate_payload:
        raise ReviewContractError("review_aggregate.disagreements is required")
    disagreement_items = validate_aggregate_disagreements(
        aggregate_payload["disagreements"], path="review_aggregate.disagreements"
    )

    disposition_payload = _closed_mapping(
        dispositions, DISPOSITION_ARTIFACT_FIELDS, "review_dispositions"
    )
    disposition_items = _required_closed_mapping_list(
        disposition_payload,
        "dispositions",
        DISPOSITION_FIELDS,
        "review_dispositions.dispositions",
    )
    _validate_aggregate_collection_cardinality(
        attempts=attempts,
        findings=findings,
        disagreements=disagreement_items,
        dispositions=disposition_items,
        attempts_path="review_aggregate.attempts",
        findings_path="review_aggregate.findings",
        disagreements_path="review_aggregate.disagreements",
        dispositions_path="review_dispositions.dispositions",
    )
    _closed_mapping_list(
        artifact_refs, AGGREGATE_ARTIFACT_REF_FIELDS, "artifact_refs"
    )


def validate_aggregate_disagreements(
    value: Any, *, path: str = "review.aggregate disagreements"
) -> list[dict[str, Any]]:
    """Accept an explicit empty set, while rejecting incomplete disagreement claims."""

    if not isinstance(value, list):
        raise ReviewContractError(f"{path} must be a list")
    for index, disagreement in enumerate(value):
        disagreement_path = f"{path}[{index}]"
        disagreement = _closed_mapping(
            disagreement, DISAGREEMENT_FIELDS, disagreement_path
        )
        if (
            not isinstance(disagreement.get("topic_id"), str)
            or not disagreement["topic_id"]
        ):
            raise ReviewContractError(
                f"{disagreement_path} requires topic_id"
            )
        if "finding_ids" in disagreement and "findings" in disagreement:
            raise ReviewContractError(
                f"{disagreement_path} cannot contain both finding_ids and findings"
            )
        finding_refs = disagreement.get(
            "finding_ids", disagreement.get("findings")
        )
        if (
            not isinstance(finding_refs, list)
            or not finding_refs
            or any(not isinstance(item, str) or not item for item in finding_refs)
            or len(finding_refs) != len(set(finding_refs))
        ):
            raise ReviewContractError(
                f"{disagreement_path} requires unique non-empty Finding refs"
            )
        stances = disagreement.get("stances")
        if stances is not None and (
            not isinstance(stances, list)
            or len(stances) != len(finding_refs)
            or any(not isinstance(item, str) or not item for item in stances)
        ):
            raise ReviewContractError(
                f"{disagreement_path}.stances must cover every Finding ref"
            )
    return value


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or not value.get("path")
        or not value.get("hash")
        or value.get("version") is None
    ):
        raise ReviewContractError(f"Goal Fidelity {label} requires an exact ref")
    return value


def validate_review_submission(submission: dict[str, Any]) -> dict[str, Any]:
    if submission.get("node_id") != "review.parallel":
        raise ReviewContractError("review.parallel HOST_AGENT submission is required")
    try:
        validate_node_result_producer(submission)
    except PolicyViolation as error:
        raise ReviewContractError(str(error)) from error
    output = submission.get("semantic_output")
    if not isinstance(output, dict):
        raise ReviewContractError("Agent Review semantic_output is required")
    if output.get("authority") != "ADVISORY_ONLY":
        raise ReviewContractError("Reviewer authority must be ADVISORY_ONLY")
    candidate = output.get("candidate_ref")
    if (
        not isinstance(candidate, dict)
        or not candidate.get("path")
        or not candidate.get("hash")
        or candidate.get("version") is None
    ):
        raise ReviewContractError("Reviewer requires an exact Candidate ref")
    roles = output.get("roles_covered")
    if not isinstance(roles, list) or not roles:
        raise ReviewContractError("Reviewer must declare logical roles_covered")
    goal_refs = output.get("goal_fidelity_refs")
    if not isinstance(goal_refs, dict):
        raise ReviewContractError("Goal Fidelity exact refs are required")
    expected_paths = {
        "profile_ref": "references/reviewer-profiles/product-goal-fidelity-v0.1.json",
        "rubric_ref": "references/reviewer-profiles/product-goal-fidelity-rubric-v0.1.json",
        "packet_contract_ref": "references/reviewer-profiles/product-goal-fidelity-packet-v0.1.json",
    }
    for field, expected_path in expected_paths.items():
        exact = _exact_ref(goal_refs.get(field), field)
        if exact["path"] != expected_path:
            raise ReviewContractError(f"Goal Fidelity {field} path is not canonical")
    commitment_refs = goal_refs.get("commitment_refs")
    if not isinstance(commitment_refs, list) or not commitment_refs:
        raise ReviewContractError("Goal Fidelity commitment refs are required")
    for commitment in commitment_refs:
        _exact_ref(commitment, "commitment")
    packet = output.get("goal_fidelity_packet")
    if not isinstance(packet, dict) or not packet.get("goal"):
        raise ReviewContractError("Goal Fidelity packet is required")
    if packet.get("candidate_ref") != candidate:
        raise ReviewContractError("Goal Fidelity packet Candidate ref differs")
    if packet.get("commitment_refs") != commitment_refs:
        raise ReviewContractError("Goal Fidelity packet commitment refs differ")
    findings = output.get("findings")
    if not isinstance(findings, list):
        raise ReviewContractError("Reviewer findings must be a list")
    required = (
        "finding_id",
        "topic_id",
        "stance",
        "concern",
        "concern_level",
        "basis_refs",
        "possible_impact",
        "professional_recommendation",
        "confidence",
        "confidence_basis",
    )
    for finding in findings:
        if not isinstance(finding, dict) or any(not finding.get(field) for field in required):
            raise ReviewContractError("Reviewer Finding is missing its advisory construction contract")
    return output


def aggregate_reviews(
    candidate_ref: dict[str, Any], submissions: list[dict[str, Any]]
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    topics: dict[str, list[dict[str, Any]]] = {}
    for submission in submissions:
        output = validate_review_submission(submission)
        if output["candidate_ref"] != candidate_ref:
            raise ReviewContractError("Reviewer attempts must bind the same exact Candidate")
        attempts.append(
            {
                "attempt_id": submission["attempt_id"],
                "reviewer_role": output["reviewer_role"],
                "roles_covered": list(output["roles_covered"]),
                "status": "COMPLETED",
            }
        )
        for finding in output["findings"]:
            retained = deepcopy(finding)
            retained["reviewer_role"] = output["reviewer_role"]
            findings.append(retained)
            topics.setdefault(retained["topic_id"], []).append(retained)
    disagreements = [
        {
            "topic_id": topic_id,
            "findings": [item["finding_id"] for item in items],
            "stances": [item["stance"] for item in items],
        }
        for topic_id, items in sorted(topics.items())
        if len({item["stance"] for item in items}) > 1
    ]
    return {
        "candidate_ref": deepcopy(candidate_ref),
        "attempts": attempts,
        "findings": findings,
        "disagreements": disagreements,
        "authority": "ADVISORY_ONLY",
    }


def finalize_review(
    candidate_ref: dict[str, Any],
    submissions: list[dict[str, Any]],
    aggregate: dict[str, Any],
    dispositions: list[dict[str, Any]],
    *,
    companion_view_ref: dict[str, Any],
) -> dict[str, Any]:
    if aggregate.get("candidate_ref") != candidate_ref:
        raise ReviewContractError("Aggregate binds a different Candidate")
    roles: set[str] = set()
    for submission in submissions:
        output = validate_review_submission(submission)
        if output["candidate_ref"] != candidate_ref:
            raise ReviewContractError("Review attempt binds a different Candidate")
        roles.update(output["roles_covered"])
    if not REQUIRED_LOGICAL_ROLES.issubset(roles):
        raise ReviewContractError("required logical Reviewer roles are incomplete")
    finding_ids = {item["finding_id"] for item in aggregate.get("findings", [])}
    disposed = {
        item.get("finding_id")
        for item in dispositions
        if isinstance(item, dict) and item.get("status")
    }
    if finding_ids != disposed:
        raise ReviewContractError("every Finding requires one explicit disposition")
    if (
        companion_view_ref.get("candidate_hash") != candidate_ref.get("hash")
        or companion_view_ref.get("finding_count") != len(finding_ids)
    ):
        raise ReviewContractError("internal Review companion view is stale or incomplete")
    return {
        "status": "FINALIZED",
        "candidate_ref": deepcopy(candidate_ref),
        "finding_count": len(finding_ids),
        "disclosed_concern_count": len(finding_ids),
        "companion_view_ref": deepcopy(companion_view_ref),
        "authority": "ADVISORY_ONLY",
    }


def next_review_action(
    candidate_hash_history: list[str], *, agent_requested_optimize: bool, max_rounds: int = 3
) -> str:
    if len(candidate_hash_history) >= 2 and candidate_hash_history[-1] == candidate_hash_history[-2]:
        return "NO_PROGRESS_STOP"
    if len(candidate_hash_history) >= max_rounds:
        return "ROUND_LIMIT_STOP"
    if agent_requested_optimize:
        return "AWAIT_AGENT_CANDIDATE"
    return "FINALIZE"
