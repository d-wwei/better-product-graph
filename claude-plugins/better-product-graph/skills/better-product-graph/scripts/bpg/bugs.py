"""Bug assessment validation and minimal local delivery packet mechanics."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .contracts import PolicyViolation, validate_node_result_producer
from .storage import atomic_write_bytes, atomic_write_json, sha256_file


BUG_CLASSIFICATIONS = frozenset(
    {"IMPLEMENTATION_DEVIATION", "PRODUCT_LOGIC_DEFECT", "SPEC_AMBIGUITY"}
)
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class BugContractError(ValueError):
    """An Agent-submitted Bug assessment is missing or internally inconsistent."""


def _validate_baseline_ref(ref: Any) -> None:
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise BugContractError("IMPLEMENTATION_DEVIATION requires an exact baseline_ref")
    path = Path(ref["path"]).expanduser().resolve()
    if not path.is_file() or sha256_file(path) != ref.get("hash"):
        raise BugContractError("baseline_ref is missing or its exact hash changed")
    if not isinstance(ref.get("version"), int):
        raise BugContractError("baseline_ref requires a version")


def validate_bug_assessment(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("node_id") != "bug.baseline.check":
        raise BugContractError("bug.baseline.check Agent result is required")
    try:
        validate_node_result_producer(result)
    except PolicyViolation as error:
        raise BugContractError(str(error)) from error
    assessment = result.get("semantic_output")
    if not isinstance(assessment, dict):
        raise BugContractError("Agent Bug assessment is required")
    classification = assessment.get("classification")
    if classification not in BUG_CLASSIFICATIONS:
        raise BugContractError("Agent classification is required and must use a supported exact value")
    if not isinstance(assessment.get("next_action"), str) or not assessment["next_action"].strip():
        raise BugContractError("Agent Bug assessment requires next_action")
    if classification == "IMPLEMENTATION_DEVIATION":
        _validate_baseline_ref(assessment.get("baseline_ref"))
        expected = assessment.get("expected")
        actual = assessment.get("actual")
        if not isinstance(expected, str) or not isinstance(actual, str) or expected == actual:
            raise BugContractError("IMPLEMENTATION_DEVIATION requires a decidable expected/actual difference")
        if assessment.get("new_rule_required") is not False:
            raise BugContractError("IMPLEMENTATION_DEVIATION cannot require a new product rule")
        if assessment.get("acceptance_criteria_decidable") is not True:
            raise BugContractError("IMPLEMENTATION_DEVIATION requires decidable acceptance criteria")
        if assessment.get("material_conflict") is not False:
            raise BugContractError("IMPLEMENTATION_DEVIATION cannot contain a material baseline conflict")
    return assessment


def persist_bug_packet(project_root: Path, bug_id: str, result: dict[str, Any]) -> dict[str, Any]:
    if SAFE_ID.fullmatch(bug_id) is None:
        raise BugContractError("bug_id must be path-safe")
    root = project_root.resolve()
    directory = root / ".better-product-graph" / "bugs" / bug_id
    packet_path = directory / "bug.delivery.packet.v1.json"
    human_path = directory / "BUG_v1.md"
    if packet_path.exists() or human_path.exists():
        raise BugContractError(f"Bug packet already exists: {bug_id}")
    assessment = validate_bug_assessment(result)
    packet = {
        "schema_version": "bug.delivery.packet.v1",
        "bug_id": bug_id,
        "classification": assessment["classification"],
        "delivery_profile": "LIGHT",
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
            f"# Bug {bug_id} v1",
            "",
            f"结论：{assessment['classification']}",
            f"差异：{assessment.get('expected', 'NOT_AVAILABLE')} → {assessment.get('actual', 'NOT_AVAILABLE')}",
            f"下一步：{assessment['next_action']}",
            "交付：LIGHT / LOCAL_ONLY；未发送到任何远程系统。",
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
