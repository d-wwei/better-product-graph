"""Deterministic authority checks for Ready upstream records.

These checks never decide whether a product claim is true. They only prove that
the referenced Decision or Evidence record was accepted through this Run's
existing Controller contracts.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .storage import (
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_event_chain,
)


class UpstreamAuthorityError(ValueError):
    """An upstream subject is exact bytes but not Controller-authoritative truth."""


EVIDENCE_PRODUCER_NODES = frozenset({"evidence.collect", "problem.learning.loop"})


def _exact_ref(ref: dict[str, Any]) -> dict[str, Any]:
    return {key: ref.get(key) for key in ("path", "hash", "version")}


def validate_ready_decision(
    project_root: Path,
    run_id: str,
    subject_ref: dict[str, Any],
    record: dict[str, Any],
) -> None:
    root = project_root.resolve()
    state = read_json(root / ".better-product-graph" / "runs" / run_id / "state.json")
    expected_ref = _exact_ref(subject_ref)
    owner = record.get("owner_authority")
    authoritative_refs = [
        _exact_ref(ref)
        for ref in state.get("artifact_refs", {}).values()
        if isinstance(ref, dict) and ref.get("role") == "decision_record"
    ]
    if (
        record.get("schema_version") != "product-decision-record.v1"
        or record.get("run_id") != run_id
        or record.get("version") != subject_ref.get("version")
        or record.get("chosen_outcome") not in {"EXPERIMENT", "COMMIT"}
        or record.get("route") not in {"PLAN_RUN_EXPERIMENT", "PLAN_RUN"}
        or not isinstance(owner, dict)
        or owner.get("kind") != "OWNER_CHOICE"
        or owner.get("actor", {}).get("kind") != "OWNER"
        or authoritative_refs.count(expected_ref) != 1
    ):
        raise UpstreamAuthorityError(
            "Decision is not the eligible Controller-authoritative Owner record for this Run"
        )
    try:
        decision_id = record["decision_id"]
        path = (root / subject_ref["path"]).resolve()
        path.relative_to(root / ".better-product-graph" / "decisions" / decision_id)
        pointer = read_json(path.parent / "current.json")
    except (KeyError, OSError, ValueError) as error:
        raise UpstreamAuthorityError(
            "Decision record is outside the Controller Decision ledger"
        ) from error
    if _exact_ref(pointer.get("record_ref", {})) != expected_ref:
        raise UpstreamAuthorityError("Decision is not the current Decision ledger record")
    events = verify_event_chain(
        root / ".better-product-graph" / "runs" / run_id / "events.jsonl"
    )
    matching = [
        event
        for event in events
        if event.get("event_type") == "OWNER_CHOICE_RECORDED"
        and _exact_ref(event.get("record_ref", {})) == expected_ref
        and event.get("chosen_outcome") == record.get("chosen_outcome")
        and event.get("route") == record.get("route")
    ]
    if len(matching) != 1:
        raise UpstreamAuthorityError(
            "Decision has no unique matching Controller Owner-choice event"
        )


def _parse_received_at(value: Any) -> None:
    if not isinstance(value, str):
        raise UpstreamAuthorityError("Evidence received_at must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise UpstreamAuthorityError("Evidence received_at must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise UpstreamAuthorityError("Evidence received_at requires a timezone")


def validate_ready_evidence(
    project_root: Path,
    run_id: str,
    subject_ref: dict[str, Any],
    record: dict[str, Any],
) -> None:
    root = project_root.resolve()
    producer = record.get("producer")
    source = record.get("source")
    content = record.get("content")
    _parse_received_at(record.get("received_at"))
    if (
        record.get("schema_version") != "evidence-record.v1"
        or record.get("kind") != "evidence"
        or record.get("version") != subject_ref.get("version")
        or record.get("run_id") != run_id
        or record.get("status") != "RECORDED"
        or record.get("authorized") is not True
        or not isinstance(source, dict)
        or not isinstance(source.get("kind"), str)
        or not source.get("kind")
        or not isinstance(producer, dict)
        or producer.get("node_id") not in EVIDENCE_PRODUCER_NODES
        or not isinstance(producer.get("attempt_id"), str)
        or not isinstance(content, dict)
        or record.get("content_hash") != sha256_bytes(canonical_json_bytes(content))
    ):
        raise UpstreamAuthorityError(
            "Evidence is FAIL, unauthorized, malformed, or unrelated to this Run"
        )
    attempt_id = producer["attempt_id"]
    producer_node = producer["node_id"]
    state = read_json(root / ".better-product-graph" / "runs" / run_id / "state.json")
    if attempt_id not in state.get("consumed_attempts", []):
        raise UpstreamAuthorityError("Evidence producer attempt is not consumed by this Run")
    result_path = (
        root
        / ".better-product-graph"
        / "runs"
        / run_id
        / "attempts"
        / attempt_id
        / "node-result.json"
    )
    receipt_path = result_path.with_name("result-receipt.json")
    if not result_path.is_file() or not receipt_path.is_file():
        raise UpstreamAuthorityError("Evidence producer result receipt is missing")
    result = read_json(result_path)
    receipt = read_json(receipt_path)
    expected_ref = _exact_ref(subject_ref)
    produced_refs = [
        _exact_ref(item)
        for item in result.get("artifact_refs", [])
        if isinstance(item, dict) and item.get("role") == "evidence"
    ]
    if (
        result.get("node_id") != producer_node
        or result.get("attempt_id") != attempt_id
        or result.get("producer", {}).get("kind") != "HOST_AGENT"
        or produced_refs.count(expected_ref) != 1
        or receipt.get("attempt_id") != attempt_id
        or receipt.get("node_id") != producer_node
        or receipt.get("result_hash") != sha256_file(result_path)
    ):
        raise UpstreamAuthorityError(
            "Evidence is not an exact committed evidence.collect artifact"
        )
    events = verify_event_chain(
        root / ".better-product-graph" / "runs" / run_id / "events.jsonl"
    )
    persisted = [
        event
        for event in events
        if event.get("event_type") in {"NODE_RESULT_PERSISTED", "NODE_RESULT_RECOVERED"}
        and event.get("attempt_id") == attempt_id
        and event.get("result_hash") == sha256_file(result_path)
    ]
    consumed = [
        event
        for event in events
        if event.get("event_type") == "NODE_TRANSITION_COMMITTED"
        and event.get("attempt_id") == attempt_id
        and event.get("from_node") == producer_node
    ]
    if len(persisted) != 1 or len(consumed) != 1:
        raise UpstreamAuthorityError(
            "Evidence has no unique persisted and consumed Controller event authority"
        )
