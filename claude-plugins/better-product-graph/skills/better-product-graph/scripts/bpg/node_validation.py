"""Node-specific validation over already-authored outputs; never produces semantics."""

from __future__ import annotations

from typing import Any

from .bugs import validate_bug_assessment
from .decision_contract import validate_decision_draft
from .discovery_contract import (
    validate_problem_ready_output,
    validate_assumption_checkpoint,
    validate_evidence_map,
    validate_learning_submission,
    validate_problem_quality_review,
)
from .incidents import validate_incident_assessment
from .planning_contract import validate_plan
from .review_contract import (
    validate_review_aggregate_semantic,
    validate_review_submission,
)
from .signals import validate_agent_route


class NodeValidationError(ValueError):
    """The current node's submitted output is structurally incomplete."""


def _require_fields(output: dict[str, Any], fields: tuple[str, ...], node_id: str) -> None:
    missing = [field for field in fields if field not in output or output[field] in (None, "", [])]
    if missing:
        raise NodeValidationError(f"{node_id} semantic_output requires {missing[0]}")


def validate_node_output(node_id: str, result: dict[str, Any]) -> None:
    if result["producer"]["kind"] == "DETERMINISTIC_PROGRAM":
        output = result.get("mechanical_output")
        if not isinstance(output, dict) or not output:
            raise NodeValidationError(f"{node_id} mechanical_output must be a non-empty object")
        if node_id == "problem.ready.gate":
            try:
                validate_problem_ready_output(output)
            except ValueError as error:
                raise NodeValidationError(str(error)) from error
            return
        expected_validators = {
            "plan.ready.gate": "plan_ready_gate",
            "review.finalize": "review_finalize",
            "prd.ready.gate": "prd_ready_gate",
        }
        if node_id in expected_validators and (
            output.get("status") != "PASS"
            or output.get("validator") != expected_validators[node_id]
        ):
            raise NodeValidationError(
                f"{node_id} mechanical_output must be Controller-derived PASS for "
                f"{expected_validators[node_id]}"
            )
        if node_id in {"signal.ingest", "route.select"} and output.get("status") != "COMPLETED":
            raise NodeValidationError(f"{node_id} mechanical_output must be COMPLETED")
        return
    output = result.get("semantic_output")
    if not isinstance(output, dict) or not output:
        raise NodeValidationError(f"{node_id} semantic_output must be a non-empty object")
    if node_id == "signal.prepare":
        _require_fields(output, ("prepared_signal",), node_id)
    elif node_id == "signal.classify":
        validate_agent_route(result)
    elif node_id == "incident.assess":
        validate_incident_assessment(result)
    elif node_id == "bug.baseline.check":
        validate_bug_assessment(result)
    elif node_id == "evidence.collect":
        _require_fields(output, ("sources",), node_id)
    elif node_id == "evidence.map":
        validation = validate_evidence_map(output)
        if validation.status != "READY":
            raise NodeValidationError("evidence.map: " + ", ".join(validation.repair_targets))
    elif node_id == "problem.assumption.audit":
        validation = validate_assumption_checkpoint(output)
        if validation.status != "READY":
            raise NodeValidationError(
                "problem.assumption.audit: " + ", ".join(validation.repair_targets)
            )
    elif node_id == "problem.learning.loop":
        validation = validate_learning_submission(output)
        if validation.status != "READY":
            raise NodeValidationError(
                "problem.learning.loop: " + ", ".join(validation.repair_targets)
            )
    elif node_id == "problem.synthesize":
        _require_fields(output, ("candidate_ref", "problem_definition"), node_id)
    elif node_id == "problem.quality.review":
        validation = validate_problem_quality_review(output)
        if validation.status != "READY":
            raise NodeValidationError(
                "problem.quality.review: " + "; ".join(validation.repair_targets)
            )
    elif node_id == "product.decision":
        validation = validate_decision_draft(output)
        if validation.status != "READY":
            raise NodeValidationError("product.decision: " + ", ".join(validation.repair_targets))
    elif node_id == "product.planning":
        validation = validate_plan(output)
        if validation.status != "READY":
            raise NodeValidationError("product.planning: " + ", ".join(validation.repair_targets))
    elif node_id == "prd.generate":
        _require_fields(output, ("document_markdown", "template_mapping", "metadata"), node_id)
    elif node_id == "review.parallel":
        validate_review_submission(result)
    elif node_id == "review.aggregate":
        _require_fields(output, ("candidate_ref",), node_id)
        validate_review_aggregate_semantic(output)
    elif node_id == "prd.optimize":
        _require_fields(
            output,
            (
                "candidate_ref",
                "document_markdown",
                "source_candidate_ref",
                "template_mapping",
                "metadata",
            ),
            node_id,
        )
