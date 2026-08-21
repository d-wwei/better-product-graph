"""Deterministic PRD delivery identity and runtime-input boundary contracts."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import PurePath
from typing import Any, Iterable

from .contracts import PolicyViolation, validate_node_result_producer
from .planning_contract import validate_plan
from .storage import canonical_json_bytes, sha256_bytes


ACTIVE_SCOPE_FIELDS = (
    "id",
    "user_outcome",
    "modules",
    "iteration",
    "dependencies",
    "validation",
    "split_reason",
    "delivery_intent",
)
EXACT_REF_FIELDS = ("path", "hash", "version")
RUNTIME_INPUT_FIELDS = (
    "input_id",
    "kind",
    "resolver",
    "binding_scope",
    "version_policy",
    "on_missing",
)
PORTABLE_REQUIRED_INPUTS = {
    "project_workspace": {
        "input_id": "project_workspace",
        "kind": "PROJECT_WORKSPACE",
        "resolver": "HOST_PROJECT_ROOT",
        "binding_scope": "PROJECT",
        "version_policy": "project-workspace.v1",
        "on_missing": "FAIL_CLOSED",
    },
    "product_signal": {
        "input_id": "product_signal",
        "kind": "RAW_SIGNAL_OR_EXACT_OCCURRENCE",
        "resolver": "SIGNAL_INTAKE",
        "binding_scope": "INVOCATION_OR_PROJECT_INBOX",
        "version_policy": "signal-contract.v1",
        "on_missing": "REQUEST_SIGNAL",
    },
}
_MUTABLE_SEGMENT = re.compile(
    r"(?:^|[^A-Za-z0-9])(current|latest)(?:$|[^A-Za-z0-9])",
    re.IGNORECASE,
)
_LIFECYCLE_TOKEN = re.compile(r"^(?:run|attempt)-[A-Za-z0-9._-]+$")
_LIFECYCLE_KEY = re.compile(
    r"(?:^|_)(?:run_id|attempt_id|candidate_version|problem_ready|ready_receipt)(?:$|_)",
    re.IGNORECASE,
)


class DeliveryContractError(ValueError):
    """A Candidate crossed stable identity or runtime dependency boundaries."""


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DeliveryContractError(f"{label} exact ref is required")
    exact = {field: value.get(field) for field in EXACT_REF_FIELDS}
    if not isinstance(exact["path"], str) or not exact["path"]:
        raise DeliveryContractError(f"{label}.path is required")
    if not isinstance(exact["hash"], str) or not exact["hash"].startswith("sha256:"):
        raise DeliveryContractError(f"{label}.hash is required")
    if not isinstance(exact["version"], (int, str)) or exact["version"] == "":
        raise DeliveryContractError(f"{label}.version is required")
    return exact


def _sortable_identity(value: Any) -> tuple[str, bytes]:
    if isinstance(value, str):
        return value, canonical_json_bytes(value)
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return value["id"], canonical_json_bytes(value)
    return "", canonical_json_bytes(value)


def canonical_active_scope_projection(
    slice_value: Any, *, require_closed: bool = False
) -> dict[str, Any]:
    if not isinstance(slice_value, dict):
        raise DeliveryContractError("active scope Slice must be an object")
    if require_closed and set(slice_value) != set(ACTIVE_SCOPE_FIELDS):
        extra = sorted(set(slice_value) - set(ACTIVE_SCOPE_FIELDS))
        missing = sorted(set(ACTIVE_SCOPE_FIELDS) - set(slice_value))
        detail = extra[0] if extra else missing[0]
        raise DeliveryContractError(
            f"proposed scope projection is not closed at {detail}"
        )
    missing = [field for field in ACTIVE_SCOPE_FIELDS if field not in slice_value]
    if missing:
        raise DeliveryContractError(f"active scope Slice is missing {missing[0]}")
    projection = {field: deepcopy(slice_value[field]) for field in ACTIVE_SCOPE_FIELDS}
    for field in ("modules", "dependencies"):
        values = projection[field]
        if not isinstance(values, list) or any(
            not isinstance(item, (str, dict)) for item in values
        ):
            raise DeliveryContractError(f"active scope {field} must be a list of stable IDs")
        projection[field] = sorted(values, key=_sortable_identity)
    for field in (
        "id",
        "user_outcome",
        "iteration",
        "validation",
        "split_reason",
        "delivery_intent",
    ):
        if not isinstance(projection[field], str) or not projection[field].strip():
            raise DeliveryContractError(f"active scope {field} is required")
    if projection["delivery_intent"] not in {"COMMIT", "EXPERIMENT"}:
        raise DeliveryContractError("active scope delivery_intent is invalid")
    return projection


def derive_active_scope_ref(
    planning_result: dict[str, Any],
    product_plan_ref: dict[str, Any],
    prd_id: str,
) -> dict[str, Any]:
    """Recompute stable scope only from one exact Product Planning Node Result."""

    if planning_result.get("schema_version") != "node-result.v1":
        raise DeliveryContractError("slice_ref must resolve to a node-result.v1 Node Result")
    if planning_result.get("node_id") != "product.planning":
        raise DeliveryContractError("slice_ref must resolve to product.planning")
    try:
        validate_node_result_producer(planning_result)
    except PolicyViolation as error:
        raise DeliveryContractError(f"product.planning provenance is invalid: {error}") from error
    exact_plan = _exact_ref(product_plan_ref, "product_plan_ref")
    plan_bindings = [
        _exact_ref(ref, "product.planning product_plan artifact")
        for ref in planning_result.get("artifact_refs", [])
        if isinstance(ref, dict) and ref.get("role") == "product_plan"
    ]
    if plan_bindings != [exact_plan]:
        raise DeliveryContractError(
            "product.planning Node Result must bind the exact Markdown Product Plan"
        )
    projection, slice_id = active_scope_projection_from_planning_result(
        planning_result, prd_id
    )
    return {
        "schema_version": "active-scope-ref.v1",
        "plan_ref": exact_plan,
        "slice_id": slice_id,
        "projection_version": "active-scope-projection.v1",
        "scope_hash": sha256_bytes(canonical_json_bytes(projection)),
    }


def active_scope_projection_from_planning_result(
    planning_result: dict[str, Any], prd_id: str
) -> tuple[dict[str, Any], str]:
    """Select the one Plan-owned Slice for a stable PRD identity."""

    plan = planning_result.get("semantic_output")
    if not isinstance(plan, dict):
        raise DeliveryContractError("product.planning semantic_output is required")
    validation = validate_plan(plan)
    if validation.status != "READY":
        raise DeliveryContractError(
            "product.planning semantic_output is not Ready: "
            + ", ".join(validation.repair_targets)
        )
    matrix = plan.get("prd_matrix")
    matches = [
        item
        for item in matrix if isinstance(item, dict) and item.get("planned_prd_id") == prd_id
    ] if isinstance(matrix, list) else []
    if len(matches) != 1 or not isinstance(matches[0].get("slice_id"), str):
        raise DeliveryContractError(
            "Product Plan prd_matrix must bind one stable planned_prd_id to a Slice"
        )
    slice_id = matches[0]["slice_id"]
    slices = plan.get("slices")
    selected = [
        item for item in slices if isinstance(item, dict) and item.get("id") == slice_id
    ] if isinstance(slices, list) else []
    if len(selected) != 1:
        raise DeliveryContractError("Product Plan stable Slice identity is missing or ambiguous")
    if selected[0].get("activated") is not True or selected[0].get("eligible") is not True:
        raise DeliveryContractError(
            "Product Plan stable Slice must be activated=true and eligible=true"
        )
    return canonical_active_scope_projection(selected[0]), slice_id


def _artifact_candidates(authoritative: Any) -> list[dict[str, Any]]:
    values = authoritative.values() if isinstance(authoritative, dict) else authoritative
    return [item for item in values if isinstance(item, dict)] if isinstance(values, Iterable) else []


def derive_spec_traceability(
    upstream_refs: list[tuple[str, dict[str, Any]]],
    authoritative_artifacts: Any,
) -> dict[str, Any]:
    """Bind trace origins from committed State artifacts, never caller aliases."""

    artifacts = _artifact_candidates(authoritative_artifacts)
    refs: list[dict[str, Any]] = []
    for role, proposed in upstream_refs:
        exact = _exact_ref(proposed, role)
        matches = [
            item
            for item in artifacts
            if all(item.get(field) == exact[field] for field in EXACT_REF_FIELDS)
        ]
        role_root = role.split(":", 1)[0]
        allowed_authority = {
            "decision": ({"decision_record"}, {"product.decision"}),
            "evidence": ({"evidence"}, {"evidence.collect", "problem.learning.loop"}),
            "roadmap": ({"node_result"}, {"evidence.collect"}),
            "product_plan": ({"product_plan"}, {"product.planning"}),
            "slice": ({"node_result"}, {"product.planning"}),
            "knowledge": ({"node_result"}, {"evidence.map"}),
            "problem_ready": ({"node_result"}, {"problem.ready.gate"}),
            "source_candidate": ({"prd_candidate"}, {"prd.generate", "prd.optimize"}),
            "review_aggregate_result": ({"node_result"}, {"review.aggregate"}),
        }.get(role_root)
        if allowed_authority is None:
            raise DeliveryContractError(
                f"spec_traceability {role} has no committed role/origin policy"
            )
        allowed_roles, allowed_nodes = allowed_authority
        matches = [
            item
            for item in matches
            if item.get("role") in allowed_roles
            and item.get("origin_node_id", item.get("node_id")) in allowed_nodes
        ]
        authoritative_origins = {
            (
                item.get("origin_node_id", item.get("node_id")),
                item.get("origin_attempt_id", item.get("attempt_id")),
            )
            for item in matches
            if isinstance(item.get("origin_node_id", item.get("node_id")), str)
            and isinstance(item.get("origin_attempt_id", item.get("attempt_id")), str)
        }
        if len(authoritative_origins) != 1:
            raise DeliveryContractError(
                f"spec_traceability {role} is not uniquely bound to its committed role/origin"
            )
        node_id, attempt_id = next(iter(authoritative_origins))
        if not isinstance(node_id, str) or not node_id:
            raise DeliveryContractError(
                f"spec_traceability {role} committed origin_node_id is missing"
            )
        if not isinstance(attempt_id, str) or not attempt_id:
            raise DeliveryContractError(
                f"spec_traceability {role} committed origin_attempt_id is missing"
            )
        refs.append(
            {
                "role": role,
                **exact,
                "origin_node_id": node_id,
                "origin_attempt_id": attempt_id,
            }
        )
    return {
        "schema_version": "spec-traceability.v1",
        "refs": sorted(refs, key=lambda item: item["role"]),
    }


def _recursive_strings(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(prefix, value)]
    if isinstance(value, list):
        return [
            found
            for index, item in enumerate(value)
            for found in _recursive_strings(item, f"{prefix}[{index}]")
        ]
    if isinstance(value, dict):
        return [
            found
            for key, item in value.items()
            for found in (
                [
                    (
                        f"{prefix}.<key>" if prefix else "<key>",
                        str(key),
                    )
                ]
                + _recursive_strings(
                    item, f"{prefix}.{key}" if prefix else str(key)
                )
            )
        ]
    return []


def _validate_traceability(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "refs"}:
        raise DeliveryContractError("spec_traceability must be closed spec-traceability.v1")
    if value.get("schema_version") != "spec-traceability.v1":
        raise DeliveryContractError("spec_traceability schema_version is invalid")
    refs = value.get("refs")
    if not isinstance(refs, list) or not refs:
        raise DeliveryContractError("spec_traceability.refs must be non-empty")
    normalized: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict) or set(ref) != {
            "role",
            *EXACT_REF_FIELDS,
            "origin_node_id",
            "origin_attempt_id",
        }:
            raise DeliveryContractError(f"spec_traceability.refs[{index}] is not closed")
        exact = _exact_ref(ref, f"spec_traceability.refs[{index}]")
        for field in ("role", "origin_node_id", "origin_attempt_id"):
            if not isinstance(ref.get(field), str) or not ref[field]:
                raise DeliveryContractError(f"spec_traceability.refs[{index}].{field} is required")
        normalized.append({"role": ref["role"], **exact, "origin_node_id": ref["origin_node_id"], "origin_attempt_id": ref["origin_attempt_id"]})
    return {"schema_version": "spec-traceability.v1", "refs": normalized}


def _validate_active_scope(value: Any) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "plan_ref",
        "slice_id",
        "projection_version",
        "scope_hash",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise DeliveryContractError(
            "active_scope_ref must be closed and cannot contain Candidate version"
        )
    if value.get("schema_version") != "active-scope-ref.v1":
        raise DeliveryContractError("active_scope_ref schema_version is invalid")
    if value.get("projection_version") != "active-scope-projection.v1":
        raise DeliveryContractError("active_scope_ref projection_version is invalid")
    if not isinstance(value.get("slice_id"), str) or not value["slice_id"]:
        raise DeliveryContractError("active_scope_ref.slice_id is required")
    if not isinstance(value.get("scope_hash"), str) or not value["scope_hash"].startswith("sha256:"):
        raise DeliveryContractError("active_scope_ref.scope_hash is required")
    return {**value, "plan_ref": _exact_ref(value.get("plan_ref"), "active_scope_ref.plan_ref")}


def _validate_runtime_inputs(
    value: Any,
    *,
    traceability: dict[str, Any],
    candidate_version: Any,
    forbidden_runtime_values: Iterable[str] = (),
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "required", "optional"}:
        raise DeliveryContractError(
            "product_runtime_inputs must be closed product-runtime-inputs.v1"
        )
    if value.get("schema_version") != "product-runtime-inputs.v1":
        raise DeliveryContractError("product_runtime_inputs schema_version is invalid")
    required = value.get("required")
    optional = value.get("optional")
    if not isinstance(required, list) or not required:
        raise DeliveryContractError("product_runtime_inputs.required must be non-empty")
    if not isinstance(optional, list):
        raise DeliveryContractError("product_runtime_inputs.optional must be a list")
    items = [*required, *optional]
    ids: list[str] = []
    for index, item in enumerate(items):
        label = "required" if index < len(required) else "optional"
        local_index = index if label == "required" else index - len(required)
        if not isinstance(item, dict):
            raise DeliveryContractError(
                f"product_runtime_inputs.{label}[{local_index}] must be an object"
            )
        missing = [field for field in RUNTIME_INPUT_FIELDS if not isinstance(item.get(field), str) or not item[field]]
        if missing:
            raise DeliveryContractError(
                f"product_runtime_inputs.{label}[{local_index}].{missing[0]} is required"
            )
        ids.append(item["input_id"])
        if item.get("kind") == "BPG_ARTIFACT":
            exception = item.get("bpg_artifact_exception")
            required_exception = {
                "business_reason",
                "portable_resolver",
                "project_binding",
                "version_policy",
                "on_unavailable",
            }
            if not isinstance(exception, dict) or set(exception) != required_exception or any(
                not isinstance(exception.get(field), str) or not exception[field]
                for field in required_exception
            ):
                raise DeliveryContractError(
                    f"product_runtime_inputs.{label}[{local_index}] requires a complete typed BPG artifact exception"
                )
            if exception["project_binding"] != "PROJECT":
                raise DeliveryContractError("BPG artifact exception must use project-level binding")
            if (
                item["resolver"] != exception["portable_resolver"]
                or item["binding_scope"] != exception["project_binding"]
                or item["version_policy"] != exception["version_policy"]
                or item["on_missing"] != exception["on_unavailable"]
            ):
                raise DeliveryContractError(
                    "BPG artifact exception must match the runtime item's portable "
                    "resolver, project binding, version policy, and unavailable behavior"
                )
    if len(ids) != len(set(ids)):
        raise DeliveryContractError("product_runtime_inputs input_id values must be unique")
    by_id = {item["input_id"]: item for item in required}
    for input_id, frozen in PORTABLE_REQUIRED_INPUTS.items():
        actual = by_id.get(input_id)
        if actual is None:
            raise DeliveryContractError(
                f"product_runtime_inputs.required is missing portable {input_id}"
            )
        if any(actual.get(field) != expected for field, expected in frozen.items()):
            raise DeliveryContractError(
                f"product_runtime_inputs.required {input_id} portable contract differs"
            )

    forbidden_exact: set[str] = set()
    forbidden_tokens: set[str] = set()
    for ref in traceability["refs"]:
        for field in ("path", "hash", "origin_node_id", "origin_attempt_id"):
            value_at_field = ref.get(field)
            if isinstance(value_at_field, str) and value_at_field:
                forbidden_exact.add(value_at_field)
        for part in PurePath(ref["path"]).parts:
            if _LIFECYCLE_TOKEN.fullmatch(part):
                forbidden_tokens.add(part)
    if isinstance(candidate_version, str):
        forbidden_exact.add(candidate_version)
    forbidden_exact.update(
        value for value in forbidden_runtime_values if isinstance(value, str) and value
    )
    for path, string in _recursive_strings(items, "inputs"):
        if (
            string.startswith(("/", "~/"))
            or string.lower().startswith("file://")
            or re.match(r"^[A-Za-z]:[\\/]", string)
        ):
            raise DeliveryContractError(
                f"product_runtime_inputs.{path} must use a portable project-level resolver"
            )
        if _MUTABLE_SEGMENT.search(string):
            raise DeliveryContractError(
                f"product_runtime_inputs.{path} cannot use current/latest"
            )
        if path.endswith("<key>") and _LIFECYCLE_KEY.search(string):
            raise DeliveryContractError(
                f"LIFECYCLE_REF_IN_RUNTIME_INPUTS at product_runtime_inputs.{path}: {string}"
            )
        if any(value and value in string for value in forbidden_exact | forbidden_tokens):
            raise DeliveryContractError(
                f"SPEC_REF_IN_RUNTIME_INPUTS at product_runtime_inputs.{path}"
            )
    return deepcopy(value)


def validate_candidate_delivery_contract(
    metadata: dict[str, Any],
    *,
    expected_active_scope: dict[str, Any] | None = None,
    expected_traceability: dict[str, Any] | None = None,
    forbidden_runtime_values: Iterable[str] = (),
) -> None:
    active = _validate_active_scope(metadata.get("active_scope_ref"))
    trace = _validate_traceability(metadata.get("spec_traceability"))
    if expected_active_scope is not None and active != expected_active_scope:
        raise DeliveryContractError("active_scope_ref differs from Controller recomputation")
    if expected_traceability is not None and trace != expected_traceability:
        raise DeliveryContractError("spec_traceability differs from committed Controller origin")
    if active["plan_ref"] != _exact_ref(
        metadata.get("product_plan_ref"), "product_plan_ref"
    ):
        raise DeliveryContractError("active_scope_ref plan_ref differs from product_plan_ref")
    plan_ref = metadata.get("product_plan_ref")
    if not isinstance(plan_ref, dict) or not set(plan_ref).issubset(
        {"path", "hash", "version", "role", "declared_role"}
    ):
        raise DeliveryContractError(
            "product_plan_ref cannot contain Candidate version or mutable identity"
        )
    active_plan_ref = metadata.get("active_scope_ref", {}).get("plan_ref")
    if not isinstance(active_plan_ref, dict) or not set(active_plan_ref).issubset(
        {"path", "hash", "version", "role", "declared_role"}
    ):
        raise DeliveryContractError(
            "active_scope_ref.plan_ref cannot contain Candidate version or mutable identity"
        )
    scope_forbidden = {
        value
        for value in (
            active.get("slice_id"),
            active.get("projection_version"),
            active.get("scope_hash"),
            *active.get("plan_ref", {}).values(),
        )
        if isinstance(value, str) and value
    }
    _validate_runtime_inputs(
        metadata.get("product_runtime_inputs"),
        traceability=trace,
        candidate_version=metadata.get("version"),
        forbidden_runtime_values={*forbidden_runtime_values, *scope_forbidden},
    )


def evaluate_runtime_input_readiness(
    contract: dict[str, Any], available_inputs: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate only availability; Candidate validation owns schema and provenance."""

    required = contract.get("required") if isinstance(contract, dict) else None
    if not isinstance(required, list):
        raise DeliveryContractError("product_runtime_inputs.required must be a list")
    missing = [
        {"input_id": item["input_id"], "on_missing": item["on_missing"]}
        for item in required
        if isinstance(item, dict)
        and available_inputs.get(item.get("input_id")) in (None, "")
    ]
    return {"status": "NOT_READY" if missing else "READY", "missing": missing}
