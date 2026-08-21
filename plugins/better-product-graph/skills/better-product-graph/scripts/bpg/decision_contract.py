"""Validation for Agent Decision Drafts and deterministic Owner-choice routing."""

from __future__ import annotations

from typing import Any

from .validation import ValidationResult


DECISION_OUTCOMES = frozenset({"STOP", "WAIT", "RESEARCH", "EXPERIMENT", "COMMIT"})
RISK_LEVELS = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
class DecisionContractError(ValueError):
    """An Agent draft or typed Owner choice violates the decision contract."""


def route_owner_choice(choice: str, *, commit_timing: str | None = None) -> str:
    if choice == "STOP":
        return "CLOSED"
    if choice == "WAIT":
        return "WAITING_TRIGGER"
    if choice == "RESEARCH":
        return "WAITING_EVIDENCE"
    if choice == "EXPERIMENT":
        return "PLAN_RUN_EXPERIMENT"
    if choice == "COMMIT":
        if commit_timing == "NOW":
            return "PLAN_RUN"
        if commit_timing == "FUTURE":
            return "ROADMAP_ONLY"
        raise DecisionContractError("COMMIT requires exact commit_timing NOW or FUTURE")
    raise DecisionContractError("Owner choice must use one of the five confirmed outcomes")


def validate_decision_draft(
    draft: dict[str, Any], *, minimum_risk_level: str | None = None
) -> ValidationResult:
    repairs: list[str] = []
    recommendation = draft.get("recommendation")
    if recommendation not in DECISION_OUTCOMES:
        repairs.append("agent.recommendation")
    if "owner_choice" in draft or "owner_authorized" in draft or "commit_timing" in draft:
        repairs.append("authority.owner_fields_forbidden")
    reasons = draft.get("reasons")
    if not isinstance(reasons, list) or not 2 <= len(reasons) <= 3 or not all(
        isinstance(item, str) and item.strip() for item in reasons
    ):
        repairs.append("agent.reasons_2_or_3")
    for field in ("mvu", "nearest_alternative", "flip_condition", "next_action"):
        if not isinstance(draft.get(field), str) or not draft[field].strip():
            repairs.append(f"agent.{field}")
    if not isinstance(draft.get("epistemic_confidence"), str):
        repairs.append("epistemic_confidence")
    risk = draft.get("action_risk")
    if (
        not isinstance(risk, dict)
        or risk.get("level") not in RISK_LEVELS
        or not isinstance(risk.get("basis"), str)
        or not isinstance(risk.get("reversible"), bool)
        or not isinstance(risk.get("measurable"), bool)
        or not isinstance(risk.get("rollback"), str)
    ):
        repairs.append("action_risk.contract")
    elif minimum_risk_level is not None:
        if minimum_risk_level not in RISK_LEVELS:
            raise ValueError("minimum_risk_level must be R0, R1, R2, or R3")
        if RISK_LEVELS[risk["level"]] < RISK_LEVELS[minimum_risk_level]:
            repairs.append("action_risk.minimum_policy")
    violations = draft.get("non_waivable_policy_violations")
    if not isinstance(violations, list):
        repairs.append("policy.non_waivable_violations")
    elif violations:
        repairs.append("policy.non_waivable_violations")
    details = draft.get("outcome_details")
    if recommendation in DECISION_OUTCOMES and (
        not isinstance(details, dict) or set(details) != {recommendation}
    ):
        repairs.append("outcome_details.recommendation_only")
    return ValidationResult("NOT_READY" if repairs else "READY", repairs)
