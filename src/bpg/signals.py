"""Raw Signal normalization and validation of Agent-submitted route decisions."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import PolicyViolation, validate_node_result_producer
from .storage import append_event, atomic_write_json, read_json, sha256_bytes, sha256_file


ROUTE_DESTINATIONS = frozenset(
    {"INBOX_ONLY", "INCIDENT_ASSESS", "BUG_BASELINE_CHECK", "DISCOVERY_START"}
)


class RouteContractError(ValueError):
    """The Host Agent route submission is absent or structurally invalid."""


def normalize_signal(raw_text: str, *, source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("raw Signal text is required")
    if not isinstance(source, dict) or not source.get("kind"):
        raise ValueError("Signal source kind is required")
    return {
        "schema_version": "signal-envelope.v1",
        "raw_text": raw_text,
        "source": deepcopy(source),
        "trust": "UNTRUSTED_INPUT",
        "parsed_claims": [],
        "parsed_instructions": [],
    }


def record_signal_occurrence(
    project_root: Path,
    raw_text: str,
    *,
    source: dict[str, Any],
    permissions: dict[str, Any] | None = None,
    sensitivity: str = "UNCLASSIFIED",
    external_id: str | None = None,
) -> dict[str, Any]:
    """Append one occurrence before content dedup; never discard repeat observations."""

    envelope = normalize_signal(raw_text, source=source)
    root = project_root.resolve()
    content_hash = sha256_bytes(raw_text.encode())
    signal_id = "signal-" + content_hash.removeprefix("sha256:")[:12]
    signal_path = root / ".better-product-graph" / "signals" / "by-content" / f"{signal_id}.json"
    canonical = {
        "schema_version": "signal-content.v1",
        "raw_text": envelope["raw_text"],
        "trust": envelope["trust"],
        "parsed_claims": [],
        "parsed_instructions": [],
        "signal_id": signal_id,
        "content_hash": content_hash,
    }
    if signal_path.exists():
        if read_json(signal_path) != canonical:
            raise ValueError(f"Signal content identity conflict: {signal_id}")
    else:
        atomic_write_json(signal_path, canonical)
    occurrence_id = f"occurrence-{uuid4().hex}"
    occurrence = append_event(
        root / ".better-product-graph" / "signals" / "occurrences.jsonl",
        {
            "event_type": "SIGNAL_OCCURRENCE_RECORDED",
            "actor": "host-adapter",
            "occurrence_id": occurrence_id,
            "signal_id": signal_id,
            "source": deepcopy(source),
            "observed_at": datetime.now(UTC).isoformat(),
            "permissions": deepcopy(
                permissions
                or {"input": "USER_PROVIDED", "persistence": "LOCAL_PROJECT_ONLY"}
            ),
            "sensitivity": sensitivity,
            "external_id": external_id,
            "content_hash": content_hash,
            "dedup_relation": {"kind": "SAME_CONTENT", "canonical_signal_id": signal_id},
        },
    )
    return {
        "signal_id": signal_id,
        "signal_ref": {
            "path": signal_path.relative_to(root).as_posix(),
            "hash": sha256_file(signal_path),
            "version": 1,
        },
        "occurrence": occurrence,
    }


def validate_agent_route(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("node_id") != "signal.classify":
        raise RouteContractError("Agent route result for signal.classify is required")
    try:
        validate_node_result_producer(result)
    except PolicyViolation as error:
        raise RouteContractError(str(error)) from error
    output = result.get("semantic_output")
    if not isinstance(output, dict):
        raise RouteContractError("Agent route result requires semantic_output")
    destination = output.get("route_destination")
    if destination not in ROUTE_DESTINATIONS:
        raise RouteContractError("Agent route result has an unsupported exact destination")
    existing_links = output.get("existing_links", [])
    if not isinstance(existing_links, list) or not all(isinstance(item, dict) for item in existing_links):
        raise RouteContractError("existing_links must be a list of metadata objects")
    return {
        "route_destination": destination,
        "existing_links": deepcopy(existing_links),
        "parsed_claims": deepcopy(output.get("parsed_claims", [])),
        "parsed_instructions": deepcopy(output.get("parsed_instructions", [])),
    }
