"""Node Result provenance rules; this module never performs product reasoning."""

from __future__ import annotations

from typing import Any


class PolicyViolation(ValueError):
    """A submitted result would cross the Agent/program authority boundary."""


SEMANTIC_NODES = frozenset(
    {
        "signal.prepare",
        "signal.classify",
        "incident.assess",
        "bug.baseline.check",
        "evidence.collect",
        "evidence.map",
        "problem.assumption.audit",
        "problem.learning.loop",
        "problem.synthesize",
        "problem.quality.review",
        "product.decision",
        "product.planning",
        "prd.generate",
        "review.parallel",
        "review.aggregate",
        "prd.optimize",
    }
)

MECHANICAL_NODES = frozenset(
    {
        "signal.ingest",
        "route.select",
        "problem.ready.gate",
        "plan.ready.gate",
        "review.finalize",
        "prd.ready.gate",
        "handoff.prepare",
        "handoff.dispatch",
    }
)


def _require_nonempty(result: dict[str, Any], field: str) -> None:
    value = result.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PolicyViolation(f"HOST_AGENT semantic result requires {field}")


def validate_node_result_producer(result: dict[str, Any]) -> dict[str, Any]:
    """Validate provenance without interpreting any semantic output."""

    node_id = result.get("node_id")
    if node_id not in SEMANTIC_NODES | MECHANICAL_NODES:
        raise PolicyViolation(f"unknown node_id: {node_id!r}")
    producer = result.get("producer")
    if not isinstance(producer, dict):
        raise PolicyViolation("Node Result requires producer identity")
    kind = producer.get("kind")
    has_semantic_output = "semantic_output" in result

    if has_semantic_output and kind != "HOST_AGENT":
        raise PolicyViolation("semantic_output must be produced by HOST_AGENT")
    if node_id in SEMANTIC_NODES and kind != "HOST_AGENT":
        raise PolicyViolation(f"{node_id} must be produced by HOST_AGENT")

    if kind == "HOST_AGENT":
        for field in ("attempt_id", "instruction_ref", "instruction_hash"):
            _require_nonempty(result, field)
        input_refs = result.get("input_refs")
        input_hashes = result.get("input_hashes")
        if not isinstance(input_refs, list) or not input_refs:
            raise PolicyViolation("HOST_AGENT semantic result requires input_refs")
        if not isinstance(input_hashes, dict) or set(input_hashes) != set(input_refs):
            raise PolicyViolation("HOST_AGENT semantic result requires exact input_hashes")
    elif kind == "DETERMINISTIC_PROGRAM":
        if node_id not in MECHANICAL_NODES:
            raise PolicyViolation(f"deterministic program cannot produce {node_id}")
        component = producer.get("component")
        if component not in {"state-controller", "host-adapter", "validator"}:
            raise PolicyViolation("deterministic program requires an allowlisted component")
        _require_nonempty(result, "attempt_id")
        if "mechanical_output" not in result:
            raise PolicyViolation("deterministic result requires mechanical_output")
    else:
        raise PolicyViolation(f"unsupported producer kind: {kind!r}")
    return result
