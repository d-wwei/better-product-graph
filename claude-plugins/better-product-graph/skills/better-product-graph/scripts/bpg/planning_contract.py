"""Validation-only Outcome-first Planning contracts and eligible-slice routing."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

from .validation import ValidationResult


PLANNING_PROFILES = frozenset({"LIGHT", "STANDARD", "PROJECT_SCALE"})
COVERAGE_PREFIXES = frozenset({"CURRENT", "FUTURE", "EXPERIMENT", "WAIT", "STOP", "UNRESOLVED"})
_CANDIDATE_VERSION = re.compile(r"^v\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?$")
_EMBEDDED_CANDIDATE_VERSION = re.compile(
    r"(?:^|[^A-Za-z0-9])v\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?(?:$|[^A-Za-z0-9])",
    re.IGNORECASE,
)
_MUTABLE_IDENTITY_TOKEN = re.compile(
    r"(?:^|[^A-Za-z0-9])(?:current|latest)(?:$|[^A-Za-z0-9])",
    re.IGNORECASE,
)


def _pins_candidate_version(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            if "candidate" in normalized or normalized in {
                "version", "prd_version", "planned_prd_version", "current", "latest"
            }:
                return True
            if _pins_candidate_version(nested):
                return True
        return False
    if isinstance(value, list):
        return any(_pins_candidate_version(item) for item in value)
    return isinstance(value, str) and _CANDIDATE_VERSION.fullmatch(value) is not None


def _plan_contains_candidate_pin(
    value: Any, *, stable_exact_ref: bool = False
) -> bool:
    if isinstance(value, list):
        return any(_plan_contains_candidate_pin(item) for item in value)
    if not isinstance(value, dict):
        return False
    exact_artifact_ref = {"path", "hash", "version"}.issubset(value)
    for key, nested in value.items():
        normalized = str(key).lower()
        if "candidate" in normalized or normalized in {
            "current", "latest", "prd_version", "planned_prd_version"
        }:
            return True
        if (
            normalized == "version"
            and (not exact_artifact_ref or not stable_exact_ref)
            and isinstance(nested, str)
            and _CANDIDATE_VERSION.fullmatch(nested)
        ):
            return True
        if _plan_contains_candidate_pin(
            nested,
            stable_exact_ref=(normalized == "decision_ref"),
        ):
            return True
    return False


def _has_cycle(edges: list[dict[str, Any]], known_nodes: set[str]) -> bool:
    graph = {node: [] for node in known_nodes}
    indegree = {node: 0 for node in known_nodes}
    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")
        if source not in graph or target not in graph:
            continue
        graph[source].append(target)
        indegree[target] += 1
    ready = [node for node, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        node = ready.pop()
        visited += 1
        for target in graph[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return visited != len(known_nodes)


def validate_plan(plan: dict[str, Any]) -> ValidationResult:
    repairs: list[str] = []
    profile = plan.get("profile")
    if not isinstance(profile, dict) or profile.get("id") not in PLANNING_PROFILES:
        repairs.append("agent.profile")
    if not isinstance(profile, dict) or not isinstance(profile.get("reason"), str) or not profile["reason"].strip():
        repairs.append("agent.profile_reason")
    decision_ref = plan.get("decision_ref")
    if (
        not isinstance(decision_ref, dict)
        or not isinstance(decision_ref.get("path"), str)
        or not isinstance(decision_ref.get("hash"), str)
        or not isinstance(decision_ref.get("version"), int)
    ):
        repairs.append("decision.exact_ref")
    for field in ("target_operating_outcome", "current_iteration_outcome"):
        if not isinstance(plan.get(field), str) or not plan[field].strip():
            repairs.append(f"agent.{field}")
    for field in ("observable_evidence", "non_sacrificable_guardrails"):
        value = plan.get(field)
        if not isinstance(value, list) or not value:
            repairs.append(f"agent.{field}")

    modules = plan.get("modules")
    if not isinstance(modules, list) or not modules:
        repairs.append("agent.horizontal_modules")
        modules = []
    module_ids = {
        item.get("id") for item in modules if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if len(module_ids) != len(modules) or any(not item.get("responsibility") for item in modules):
        repairs.append("modules.contract")

    iterations = plan.get("iterations")
    if not isinstance(iterations, list) or not iterations:
        repairs.append("agent.vertical_iterations")
        iterations = []
    iteration_ids = {
        item.get("id")
        for item in iterations
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if len(iteration_ids) != len(iterations) or any(
        item.get("end_to_end") is not True
        or not item.get("outcome")
        or not item.get("validation")
        or not item.get("stop_condition")
        for item in iterations
    ):
        repairs.append("iterations.end_to_end_contract")

    dependencies = plan.get("dependencies", [])
    if not isinstance(dependencies, list):
        repairs.append("dependencies.contract")
        dependencies = []
    elif any(
        not isinstance(item, dict)
        or item.get("from") not in module_ids
        or item.get("to") not in module_ids
        for item in dependencies
    ):
        repairs.append("dependencies.refs")
    if _has_cycle(dependencies, module_ids):
        repairs.append("dependencies.cycle")

    material_items = plan.get("material_items", [])
    material_ids = [item.get("id") for item in material_items if isinstance(item, dict)]
    coverage = plan.get("coverage", [])
    coverage_ids = [item.get("item_id") for item in coverage if isinstance(item, dict)]
    if Counter(material_ids) != Counter(coverage_ids) or any(count != 1 for count in Counter(coverage_ids).values()):
        repairs.append("coverage.exactly_once")
    if any(
        not isinstance(item.get("disposition"), str)
        or item["disposition"].split(":", 1)[0] not in COVERAGE_PREFIXES
        or not item.get("owner")
        or not item.get("impact")
        or not item.get("review_trigger")
        for item in coverage
        if isinstance(item, dict)
    ):
        repairs.append("coverage.transparent_disposition")

    slices = plan.get("slices")
    if not isinstance(slices, list) or not slices:
        repairs.append("agent.slices")
        slices = []
    slice_ids = {
        item.get("id") for item in slices if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    shared_contracts = plan.get("shared_contracts", [])
    if not isinstance(shared_contracts, list):
        repairs.append("shared_contracts.contract")
        shared_contracts = []
    shared_ids = {
        item.get("id")
        for item in shared_contracts
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip()
    }
    if len(shared_ids) != len(shared_contracts) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("contract"), str)
        or not item["contract"].strip()
        or not isinstance(item.get("consumers"), list)
        or not item["consumers"]
        or not set(item["consumers"]).issubset(module_ids)
        or (
            "authoritative_ref" in item
            and (
                not isinstance(item["authoritative_ref"], str)
                or not item["authoritative_ref"].strip()
            )
        )
        for item in shared_contracts
    ):
        repairs.append("shared_contracts.contract")
    if len(slice_ids) != len(slices) or any(
        not item.get("user_outcome")
        or not isinstance(item.get("activated"), bool)
        or not isinstance(item.get("eligible"), bool)
        or not set(item.get("modules", [])).issubset(module_ids)
        or item.get("iteration") not in iteration_ids
        or not item.get("validation")
        or not item.get("split_reason")
        or item.get("delivery_intent") not in {"COMMIT", "EXPERIMENT"}
        for item in slices
    ):
        repairs.append("slices.end_to_end_contract")
    for item in slices:
        if not isinstance(item, dict):
            continue
        dependencies_value = item.get("dependencies")
        if (
            not isinstance(dependencies_value, list)
            or any(not isinstance(dependency, str) for dependency in dependencies_value)
            or not set(dependencies_value or []).issubset(shared_ids)
        ):
            slice_id = item.get("id") if isinstance(item.get("id"), str) else "unknown"
            repairs.append(f"slices.{slice_id}.dependencies.exact_refs")
    matrix = plan.get("prd_matrix")
    matrix_ids = {
        item.get("slice_id") for item in matrix if isinstance(item, dict)
    } if isinstance(matrix, list) else set()
    if matrix_ids != slice_ids:
        repairs.append("prd_matrix.slice_binding")
    matrix_items = [item for item in matrix if isinstance(item, dict)] if isinstance(matrix, list) else []
    planned_prd_ids = [item.get("planned_prd_id") for item in matrix_items]
    if (
        len(matrix_items) != len(slices)
        or any(not isinstance(item, str) or not item.strip() for item in planned_prd_ids)
        or len(set(planned_prd_ids)) != len(planned_prd_ids)
    ):
        repairs.append("prd_matrix.stable_prd_identity")
    if (
        _plan_contains_candidate_pin(plan)
        or any(_pins_candidate_version(item) for item in matrix_items)
        or any(
            isinstance(planned_id, str)
            and (
                _EMBEDDED_CANDIDATE_VERSION.search(planned_id)
                or _MUTABLE_IDENTITY_TOKEN.search(planned_id)
            )
            for planned_id in planned_prd_ids
        )
    ):
        repairs.append("prd_matrix.candidate_version")
    return ValidationResult("NOT_READY" if repairs else "READY", repairs)


def derive_prd_run_specs(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Filter already-authored eligible slices; never create or enrich a semantic slice."""

    validation = validate_plan(plan)
    if validation.status != "READY":
        raise ValueError("Plan is not ready: " + ", ".join(validation.repair_targets))
    decision_ref = plan["decision_ref"]
    return [
        {
            "slice_id": item["id"],
            "planned_prd_id": next(
                row["planned_prd_id"]
                for row in plan["prd_matrix"]
                if row["slice_id"] == item["id"]
            ),
            "delivery_intent": item["delivery_intent"],
            "parent_decision_ref": decision_ref,
            "modules": list(item["modules"]),
            "iteration": item["iteration"],
            "dependencies": list(item["dependencies"]),
            "user_outcome": item["user_outcome"],
        }
        for item in plan["slices"]
        if item["activated"] is True and item["eligible"] is True
    ]
