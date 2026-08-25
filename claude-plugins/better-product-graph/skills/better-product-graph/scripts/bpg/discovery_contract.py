"""Validation-only contracts for Agent-authored Evidence and Problem Discovery outputs."""

from __future__ import annotations

from typing import Any

from .validation import ValidationResult


CLAIM_ROLES = frozenset(
    {
        "SOURCE_ASSERTION",
        "OBSERVATION",
        "VERIFIED_CLAIM",
        "INFERENCE",
        "ASSUMPTION",
        "PREFERENCE",
        "PROPOSAL",
        "UNKNOWN",
        "AUTHORIZATION",
    }
)
LEARNING_DISPOSITIONS = frozenset(
    {"READY_FOR_SYNTHESIS", "ROUTE_REEVALUATION_RECOMMENDED", "INSUFFICIENT_TO_PROCEED"}
)
PROBLEM_REVIEW_VERSION = "problem-quality-review.v0.1"
PROBLEM_REVIEW_RECOMMENDATIONS = frozenset(
    {
        "PROCEED_TO_DETERMINISTIC_READY_CHECK",
        "REVISE_SYNTHESIS",
        "RETURN_TO_LEARNING",
        "NEEDS_OWNER",
        "ROUTE_REEVALUATION",
    }
)
PROBLEM_READY_RULES_VERSION = "problem-ready.v1"
PROBLEM_READY_OUTPUT_FIELDS = frozenset(
    {
        "status",
        "validator",
        "rules_version",
        "source_attempt_id",
        "candidate_ref",
        "unmet_conditions",
    }
)
PROBLEM_READY_REF_FIELDS = frozenset({"role", "path", "hash", "version"})
PROBLEM_READY_UNMET_FIELDS = frozenset(
    {
        "condition",
        "affected_refs",
        "finding_ids",
        "repair_target",
        "resume_node",
    }
)
PROBLEM_READY_REPAIRS = {
    "candidate.current_exact_ref": "REBUILD_CANDIDATE",
    "review.finding_dispositions": "COMPLETE_REVIEW_DISPOSITION",
    "upstream.exact_refs": "REBIND_UPSTREAM_REF",
}


def validate_evidence_map(evidence_map: dict[str, Any]) -> ValidationResult:
    repairs: list[str] = []
    claims = evidence_map.get("claims")
    if not isinstance(claims, list):
        return ValidationResult("NOT_READY", ["claims"])
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            repairs.append(prefix)
            continue
        if claim.get("role") not in CLAIM_ROLES:
            repairs.append(f"{prefix}.role")
        if not isinstance(claim.get("source_ref"), str) or not claim["source_ref"].strip():
            repairs.append(f"{prefix}.source_ref")
        if claim.get("role") == "AUTHORIZATION" and claim.get("confidence") == "VERIFIED_USER_FACT":
            repairs.append(f"{prefix}.confidence")
    return ValidationResult("NOT_READY" if repairs else "READY", repairs)


def validate_assumption_checkpoint(checkpoint: dict[str, Any]) -> ValidationResult:
    repairs: list[str] = []
    for field in (
        "phenomenon",
        "impact",
        "problem_hypothesis",
        "desired_outcome",
        "proposed_solution",
        "no_action_counterfactual",
    ):
        if not isinstance(checkpoint.get(field), str) or not checkpoint[field].strip():
            repairs.append(f"agent.{field}")
    alternatives = checkpoint.get("credible_alternatives")
    if not isinstance(alternatives, list) or not alternatives:
        repairs.append("agent.credible_alternatives")
    mvus = checkpoint.get("mvus")
    selected = (
        [item for item in mvus if isinstance(item, dict) and item.get("selected") is True]
        if isinstance(mvus, list)
        else []
    )
    if len(selected) != 1:
        repairs.append("agent.exactly_one_selected_mvu")
    elif not isinstance(selected[0].get("best_source_ref"), str):
        repairs.append("agent.selected_mvu.best_source_ref")
    return ValidationResult("NOT_READY" if repairs else "READY", repairs)


def validate_learning_submission(submission: dict[str, Any]) -> ValidationResult:
    repairs: list[str] = []
    if submission.get("learning_disposition") not in LEARNING_DISPOSITIONS:
        repairs.append("learning_disposition")
    if submission.get("runtime_status") not in {"COMPLETED", "WAITING", "BLOCKED"}:
        repairs.append("runtime_status")
    challenges = submission.get("material_challenges", [])
    if not isinstance(challenges, list):
        repairs.append("material_challenges")
    elif any(not isinstance(challenge, str) or not challenge.strip() for challenge in challenges):
        repairs.append("material_challenges.items")
    elif len(challenges) != len(set(challenges)):
        repairs.append("material_challenges.distinct")
    actions = submission.get("next_actions", [])
    if submission.get("interaction_policy") == "NO_PM_INTERVIEW" and any(
        isinstance(action, dict) and action.get("kind") == "PROMPT_PM" for action in actions
    ):
        repairs.append("interaction_policy.no_pm_prompt")
    usage = submission.get("reasoning_usage")
    used = usage.get("used_resource_ids") if isinstance(usage, dict) else None
    if (
        not isinstance(used, list)
        or not used
        or len(used) != len(set(used))
        or any(not isinstance(resource_id, str) or not resource_id for resource_id in used)
    ):
        repairs.append("reasoning_usage.used_resource_ids")
    if (
        not isinstance(usage, dict)
        or not isinstance(usage.get("selection_rationale"), str)
        or not usage["selection_rationale"].strip()
    ):
        repairs.append("reasoning_usage.selection_rationale")
    return ValidationResult("NOT_READY" if repairs else "READY", repairs)


def validate_problem_quality_review(review: dict[str, Any]) -> ValidationResult:
    """Validate the advisory Review contract before it can advance to the Gate."""

    repairs: list[str] = []
    candidate_ref = review.get("candidate_ref")
    if not isinstance(candidate_ref, dict):
        repairs.append("candidate_ref: copy the exact dispatched Candidate ref")
        candidate_ref = {}
    if not isinstance(candidate_ref.get("path"), str) or not candidate_ref["path"].strip():
        repairs.append("candidate_ref.path: copy it from the exact Candidate ref")
    if not isinstance(candidate_ref.get("hash"), str) or not candidate_ref["hash"].strip():
        repairs.append("candidate_ref.hash: copy it from the exact Candidate ref")
    if not isinstance(candidate_ref.get("version"), (int, str)) or candidate_ref.get(
        "version"
    ) == "":
        repairs.append("candidate_ref.version: copy it from the exact Candidate ref")
    if candidate_ref.get("role") != "problem_definition_candidate":
        repairs.append(
            "candidate_ref.role: use problem_definition_candidate for the exact Candidate"
        )
    if review.get("candidate_hash") != candidate_ref.get("hash"):
        repairs.append("candidate_hash: copy candidate_ref.hash exactly")
    if review.get("candidate_version") != candidate_ref.get("version"):
        repairs.append("candidate_version: copy candidate_ref.version exactly")

    upstream_refs = review.get("upstream_refs")
    if not isinstance(upstream_refs, list):
        repairs.append("upstream_refs: provide a list of exact Candidate-bound refs")
        upstream_refs = []
    seen_roles: set[str] = set()
    seen_identities: set[tuple[Any, Any, Any]] = set()
    for index, ref in enumerate(upstream_refs):
        prefix = f"upstream_refs[{index}]"
        if not isinstance(ref, dict):
            repairs.append(f"{prefix}: provide role/path/hash/version")
            continue
        role = ref.get("role")
        if not isinstance(role, str) or not role.strip():
            repairs.append(f"{prefix}.role: identify the upstream artifact role")
        elif role in seen_roles:
            repairs.append(f"{prefix}.role: duplicate upstream role {role}")
        else:
            seen_roles.add(role)
        if not isinstance(ref.get("path"), str) or not ref["path"].strip():
            repairs.append(f"{prefix}.path: copy the exact dispatched ref value")
        if not isinstance(ref.get("hash"), str) or not ref["hash"].strip():
            repairs.append(f"{prefix}.hash: copy the exact dispatched ref value")
        if not isinstance(ref.get("version"), (int, str)) or ref.get("version") == "":
            repairs.append(f"{prefix}.version: copy the exact dispatched ref value")
        identity = (ref.get("path"), ref.get("hash"), ref.get("version"))
        if (
            isinstance(identity[0], str)
            and isinstance(identity[1], str)
            and isinstance(identity[2], (int, str))
            and all(item != "" for item in identity)
        ):
            if identity in seen_identities:
                repairs.append(f"{prefix}: duplicate exact upstream ref")
            seen_identities.add(identity)

    if review.get("review_version") != PROBLEM_REVIEW_VERSION:
        repairs.append(f"review_version: use {PROBLEM_REVIEW_VERSION}")
    findings = review.get("findings")
    if not isinstance(findings, list):
        repairs.append("findings: provide a list; use [] when no material concern exists")
        findings = []
    finding_ids: list[Any] = []
    for index, finding in enumerate(findings):
        finding_id = finding.get("id") if isinstance(finding, dict) else None
        if not isinstance(finding_id, str) or not finding_id.strip():
            repairs.append(f"findings[{index}].id: provide one stable Finding id")
        finding_ids.append(finding_id)
    valid_finding_ids = [item for item in finding_ids if isinstance(item, str) and item]
    if len(set(valid_finding_ids)) != len(valid_finding_ids):
        repairs.append("findings: Finding ids must be unique")

    dispositions = review.get("dispositions")
    if not isinstance(dispositions, list):
        repairs.append("dispositions: provide one status for every Finding id")
        dispositions = []
    disposition_ids = [
        item.get("finding_id")
        for item in dispositions
        if isinstance(item, dict)
        and isinstance(item.get("finding_id"), str)
        and item["finding_id"].strip()
        and isinstance(item.get("status"), str)
        and item["status"].strip()
    ]
    if (
        sorted(disposition_ids) != sorted(valid_finding_ids)
        or len(disposition_ids) != len(set(disposition_ids))
        or len(valid_finding_ids) != len(finding_ids)
    ):
        repairs.append("dispositions: cover every Finding id exactly once with a non-empty status")
    if review.get("recommended_disposition") not in PROBLEM_REVIEW_RECOMMENDATIONS:
        repairs.append(
            "recommended_disposition: use one documented advisory Review recommendation"
        )
    if review.get("reviewer_authority") != "ADVISORY_ONLY":
        repairs.append("reviewer_authority: must be ADVISORY_ONLY")
    if review.get("ready_claim") != "NOT_MADE":
        repairs.append("ready_claim: must be NOT_MADE because only the Controller declares Ready")
    return ValidationResult("NOT_READY" if repairs else "READY", repairs)


def validate_problem_ready(
    candidate: dict[str, Any],
    review: dict[str, Any],
    *,
    current_candidate_hash: str,
    available_ref_hashes: dict[str, str],
) -> ValidationResult:
    """Calculate action-relative readiness without scoring semantic concern severity."""

    repairs: list[str] = []
    candidate_ref = candidate.get("candidate_ref")
    if (
        not isinstance(candidate_ref, dict)
        or candidate_ref.get("hash") != current_candidate_hash
        or review.get("candidate_hash") != current_candidate_hash
        or review.get("candidate_version") != candidate_ref.get("version")
    ):
        repairs.append("candidate.current_exact_ref")
    findings = review.get("findings", [])
    dispositions = review.get("dispositions", [])
    disposed_ids = {
        item.get("finding_id") for item in dispositions if isinstance(item, dict) and item.get("status")
    }
    finding_ids = {item.get("id") for item in findings if isinstance(item, dict)}
    if finding_ids != disposed_ids:
        repairs.append("review.finding_dispositions")
    refs = [candidate_ref, *candidate.get("upstream_refs", [])]
    for ref in refs:
        if not isinstance(ref, dict) or available_ref_hashes.get(ref.get("path")) != ref.get("hash"):
            repairs.append("upstream.exact_refs")
            break
    return ValidationResult("NOT_READY" if repairs else "READY", repairs)


def _problem_ready_exact_ref(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an exact ref object")
    unknown = sorted(set(value) - PROBLEM_READY_REF_FIELDS)
    if unknown:
        raise ValueError(f"{path}.{unknown[0]} is an unknown field")
    if set(value) != PROBLEM_READY_REF_FIELDS:
        missing = sorted(PROBLEM_READY_REF_FIELDS - set(value))
        raise ValueError(f"{path}.{missing[0]} is required")
    if (
        not isinstance(value["role"], str)
        or not value["role"]
        or not isinstance(value["path"], str)
        or not value["path"]
        or not isinstance(value["hash"], str)
        or not value["hash"].startswith("sha256:")
        or isinstance(value["version"], bool)
        or not isinstance(value["version"], (int, str))
        or value["version"] == ""
    ):
        raise ValueError(f"{path} requires exact role/path/hash/version")
    return value


def validate_problem_ready_output(value: Any) -> dict[str, Any]:
    """Validate the one closed-world Controller-owned Problem Ready calculation."""

    if not isinstance(value, dict):
        raise ValueError("problem.ready.gate mechanical_output must be an object")
    unknown = sorted(set(value) - PROBLEM_READY_OUTPUT_FIELDS)
    if unknown:
        raise ValueError(f"mechanical_output.{unknown[0]} is an unknown field")
    missing = sorted(PROBLEM_READY_OUTPUT_FIELDS - set(value))
    if missing:
        raise ValueError(f"mechanical_output.{missing[0]} is required")
    if value.get("status") not in {"READY", "NOT_READY"}:
        raise ValueError("problem.ready.gate status must be READY or NOT_READY")
    if value.get("validator") != "problem_ready_gate":
        raise ValueError("problem.ready.gate validator must be problem_ready_gate")
    if value.get("rules_version") != PROBLEM_READY_RULES_VERSION:
        raise ValueError(
            f"problem.ready.gate rules_version must be {PROBLEM_READY_RULES_VERSION}"
        )
    if not isinstance(value.get("source_attempt_id"), str) or not value["source_attempt_id"]:
        raise ValueError("problem.ready.gate source_attempt_id must be non-empty")
    _problem_ready_exact_ref(value.get("candidate_ref"), "mechanical_output.candidate_ref")
    unmet = value.get("unmet_conditions")
    if not isinstance(unmet, list):
        raise ValueError("mechanical_output.unmet_conditions must be a list")
    if value["status"] == "READY" and unmet:
        raise ValueError("READY problem.ready.gate must have no unmet_conditions")
    if value["status"] == "NOT_READY" and not unmet:
        raise ValueError("NOT_READY problem.ready.gate requires exact unmet_conditions")

    seen_conditions: set[str] = set()
    for index, item in enumerate(unmet):
        path = f"mechanical_output.unmet_conditions[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{path} must be an object")
        unknown_item = sorted(set(item) - PROBLEM_READY_UNMET_FIELDS)
        if unknown_item:
            raise ValueError(f"{path}.{unknown_item[0]} is an unknown field")
        missing_item = sorted(PROBLEM_READY_UNMET_FIELDS - set(item))
        if missing_item:
            raise ValueError(f"{path}.{missing_item[0]} is required")
        condition = item.get("condition")
        if condition not in PROBLEM_READY_REPAIRS:
            raise ValueError(f"{path}.condition is not a Problem Ready rule")
        if condition in seen_conditions:
            raise ValueError(f"{path}.condition is duplicated")
        seen_conditions.add(condition)
        if item.get("repair_target") != PROBLEM_READY_REPAIRS[condition]:
            raise ValueError(f"{path}.repair_target does not match {condition}")
        if item.get("resume_node") != "problem.ready.gate":
            raise ValueError(f"{path}.resume_node must be problem.ready.gate")
        affected_refs = item.get("affected_refs")
        if not isinstance(affected_refs, list):
            raise ValueError(f"{path}.affected_refs must be a list")
        for ref_index, ref in enumerate(affected_refs):
            _problem_ready_exact_ref(ref, f"{path}.affected_refs[{ref_index}]")
        finding_ids = item.get("finding_ids")
        if (
            not isinstance(finding_ids, list)
            or any(not isinstance(finding_id, str) or not finding_id for finding_id in finding_ids)
            or len(finding_ids) != len(set(finding_ids))
        ):
            raise ValueError(f"{path}.finding_ids must be a unique string list")
    return value


def build_problem_ready_output(
    validation: ValidationResult,
    review: dict[str, Any],
    *,
    source_attempt_id: str,
    available_ref_hashes: dict[str, str],
) -> dict[str, Any]:
    """Render exact mechanical failures into deterministic, auditable repairs."""

    candidate_ref = {
        field: review["candidate_ref"][field]
        for field in ("role", "path", "hash", "version")
    }
    findings = review.get("findings", [])
    dispositions = review.get("dispositions", [])
    finding_ids = {
        item.get("id") for item in findings if isinstance(item, dict) and item.get("id")
    }
    disposed_ids = {
        item.get("finding_id")
        for item in dispositions
        if isinstance(item, dict) and item.get("finding_id") and item.get("status")
    }
    all_refs = [candidate_ref, *review.get("upstream_refs", [])]
    invalid_refs = [
        {
            field: ref[field]
            for field in ("role", "path", "hash", "version")
        }
        for ref in all_refs
        if isinstance(ref, dict)
        and set(("role", "path", "hash", "version")).issubset(ref)
        and available_ref_hashes.get(ref.get("path")) != ref.get("hash")
    ]
    unmet: list[dict[str, Any]] = []
    for condition in validation.repair_targets:
        if condition == "candidate.current_exact_ref":
            affected_refs = [candidate_ref]
            affected_findings: list[str] = []
        elif condition == "review.finding_dispositions":
            affected_refs = [candidate_ref]
            affected_findings = sorted(finding_ids.symmetric_difference(disposed_ids))
        else:
            affected_refs = invalid_refs
            affected_findings = []
        unmet.append(
            {
                "condition": condition,
                "affected_refs": affected_refs,
                "finding_ids": affected_findings,
                "repair_target": PROBLEM_READY_REPAIRS[condition],
                "resume_node": "problem.ready.gate",
            }
        )
    output = {
        "status": validation.status,
        "validator": "problem_ready_gate",
        "rules_version": PROBLEM_READY_RULES_VERSION,
        "source_attempt_id": source_attempt_id,
        "candidate_ref": candidate_ref,
        "unmet_conditions": unmet,
    }
    return validate_problem_ready_output(output)
