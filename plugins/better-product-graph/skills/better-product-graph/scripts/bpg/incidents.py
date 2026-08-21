"""Incident contract validation and append-only local verification packets."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .contracts import PolicyViolation, validate_node_result_producer
from .storage import atomic_write_bytes, atomic_write_json, sha256_file


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class IncidentContractError(ValueError):
    """An Agent-submitted Incident assessment does not satisfy the local contract."""


def validate_incident_assessment(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("node_id") != "incident.assess":
        raise IncidentContractError("incident.assess Agent result is required")
    try:
        validate_node_result_producer(result)
    except PolicyViolation as error:
        raise IncidentContractError(str(error)) from error
    assessment = result.get("semantic_output")
    if not isinstance(assessment, dict):
        raise IncidentContractError("Agent incident assessment is required")
    for field in ("summary", "severity", "impact", "reproduction", "scope", "next_action"):
        if not isinstance(assessment.get(field), str) or not assessment[field].strip():
            raise IncidentContractError(f"Agent incident assessment requires {field}")
    if assessment.get("runtime_status") != "WAITING_ENGINEERING":
        raise IncidentContractError("Incident runtime_status must be WAITING_ENGINEERING")
    missing = assessment.get("missing_data", [])
    if not isinstance(missing, list) or not all(isinstance(item, str) for item in missing):
        raise IncidentContractError("missing_data must be a list")
    for field in missing:
        if assessment.get(field) != "NOT_AVAILABLE":
            raise IncidentContractError(f"missing Incident field {field} must be NOT_AVAILABLE")
    return assessment


def persist_incident_packet(
    project_root: Path, incident_id: str, result: dict[str, Any]
) -> dict[str, Any]:
    if SAFE_ID.fullmatch(incident_id) is None:
        raise IncidentContractError("incident_id must be path-safe")
    root = project_root.resolve()
    directory = root / ".better-product-graph" / "incidents" / incident_id
    packet_path = directory / "incident.verification.packet.v1.json"
    human_path = directory / "INCIDENT_v1.md"
    if packet_path.exists() or human_path.exists():
        raise IncidentContractError(f"incident packet already exists: {incident_id}")
    assessment = validate_incident_assessment(result)
    packet = {
        "schema_version": "incident.verification.packet.v1",
        "incident_id": incident_id,
        "runtime_status": "WAITING_ENGINEERING",
        "assessment": assessment,
        "provenance": {
            "attempt_id": result["attempt_id"],
            "instruction_ref": result["instruction_ref"],
            "instruction_hash": result["instruction_hash"],
            "input_refs": result["input_refs"],
            "input_hashes": result["input_hashes"],
        },
        "handoff": {"mode": "LOCAL_ONLY", "remote_status": "NOT_CONFIGURED"},
    }
    atomic_write_json(packet_path, packet)
    view = "\n".join(
        [
            f"# Incident {incident_id} v1",
            "",
            f"结论：{assessment['summary']}",
            f"影响：{assessment['impact']}（{assessment['severity']}）",
            f"复现：{assessment['reproduction']}",
            f"范围：{assessment['scope']}",
            f"下一步：{assessment['next_action']}",
            "状态：等待工程核验；未发送到任何远程系统。",
            "",
        ]
    )
    atomic_write_bytes(human_path, view.encode())
    return {
        **packet,
        "packet_ref": {
            "path": packet_path.relative_to(root).as_posix(),
            "hash": sha256_file(packet_path),
            "version": 1,
        },
        "human_view_path": str(human_path),
    }
