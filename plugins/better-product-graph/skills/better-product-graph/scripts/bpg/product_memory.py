"""Append-only product Decision Ledger and deterministic projections.

This module never makes a product choice. It preserves an Agent-authored proposal,
an independently authorized Owner command, and projections of those exact facts.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import wraps
from pathlib import Path
from typing import Any

from .contracts import PolicyViolation, validate_node_result_producer
from .decision_contract import DecisionContractError, route_owner_choice, validate_decision_draft
from .locking import exclusive_file_lock
from .storage import append_event, assert_managed_path, atomic_write_json, read_json, sha256_file


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _serialized(function):
    @wraps(function)
    def wrapped(project_root: Path, *args, **kwargs):
        root = project_root.resolve()
        lock = assert_managed_path(
            root, root / ".better-product-graph" / "locks" / "product-memory.lock"
        )
        with exclusive_file_lock(lock):
            return function(root, *args, **kwargs)

    return wrapped


def _safe_id(value: str, field: str) -> str:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        raise DecisionContractError(f"{field} must be path-safe")
    return value


def _exact_project_ref(root: Path, ref: dict[str, Any], *, label: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise DecisionContractError(f"{label} requires an exact path and hash")
    path = (root / ref["path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise DecisionContractError(f"{label} escapes project root") from error
    if not path.is_file() or path.is_symlink() or sha256_file(path) != ref.get("hash"):
        raise DecisionContractError(f"{label} hash does not match the exact file")
    return path, read_json(path)


def _next_version(directory: Path, stem: str) -> int:
    versions: list[int] = []
    for path in directory.glob(f"{stem}_v*.json"):
        suffix = path.stem.removeprefix(f"{stem}_v")
        if suffix.isdigit():
            versions.append(int(suffix))
    return max(versions, default=0) + 1


@_serialized
def persist_decision_proposal(
    project_root: Path,
    decision_id: str,
    run_id: str,
    submission: dict[str, Any],
) -> dict[str, Any]:
    """Persist an immutable Agent proposal without treating it as Owner authority."""

    decision_id = _safe_id(decision_id, "decision_id")
    run_id = _safe_id(run_id, "run_id")
    if submission.get("node_id") != "product.decision":
        raise DecisionContractError("product.decision Agent result is required")
    try:
        validate_node_result_producer(submission)
    except PolicyViolation as error:
        raise DecisionContractError(str(error)) from error
    draft = submission.get("semantic_output")
    if not isinstance(draft, dict):
        raise DecisionContractError("Agent Decision Draft is required")
    validation = validate_decision_draft(draft)
    if validation.status != "READY":
        raise DecisionContractError(
            "Decision Draft is not ready: " + ", ".join(validation.repair_targets)
        )
    root = project_root.resolve()
    directory = root / ".better-product-graph" / "decisions" / decision_id
    version = _next_version(directory, "PROPOSAL")
    proposal_path = directory / f"PROPOSAL_v{version}.json"
    proposal = {
        "schema_version": "product-decision-proposal.v1",
        "decision_id": decision_id,
        "run_id": run_id,
        "version": version,
        "agent_draft": deepcopy(draft),
        "agent_provenance": {
            "attempt_id": submission["attempt_id"],
            "instruction_ref": submission["instruction_ref"],
            "instruction_hash": submission["instruction_hash"],
            "input_refs": deepcopy(submission["input_refs"]),
            "input_hashes": deepcopy(submission["input_hashes"]),
        },
    }
    atomic_write_json(proposal_path, proposal)
    proposal_ref = {
        "path": proposal_path.relative_to(root).as_posix(),
        "hash": sha256_file(proposal_path),
        "version": version,
    }
    return {**proposal, "proposal_ref": proposal_ref}


def _write_projections(root: Path) -> None:
    decisions: list[dict[str, Any]] = []
    decisions_root = root / ".better-product-graph" / "decisions"
    if decisions_root.is_dir():
        for pointer_path in sorted(decisions_root.glob("*/current.json")):
            pointer = read_json(pointer_path)
            _, record = _exact_project_ref(root, pointer.get("record_ref", {}), label="current decision")
            decisions.append(
                {
                    "decision_id": record["decision_id"],
                    "version": record["version"],
                    "chosen_outcome": record["chosen_outcome"],
                    "route": record["route"],
                    "record_ref": pointer["record_ref"],
                }
            )
    memory = root / ".better-product-graph" / "product-memory"
    atomic_write_json(
        memory / "product-plan.json",
        {"schema_version": "product-plan-projection.v1", "decisions": decisions},
    )
    atomic_write_json(
        memory / "roadmap.json",
        {
            "schema_version": "product-roadmap-projection.v1",
            "items": [item for item in decisions if item["route"] == "ROADMAP_ONLY"],
        },
    )


@_serialized
def record_owner_decision(
    project_root: Path,
    proposal: dict[str, Any],
    command: dict[str, Any],
) -> dict[str, Any]:
    """Append one Owner-authorized Decision version and refresh exact projections."""

    root = project_root.resolve()
    _, stored_proposal = _exact_project_ref(
        root, proposal.get("proposal_ref", {}), label="proposal ref"
    )
    actor = command.get("actor")
    if not isinstance(actor, dict) or actor.get("kind") != "OWNER" or not actor.get("id"):
        raise DecisionContractError("Owner actor is required")
    choice = command.get("choice")
    timing = command.get("commit_timing")
    route = route_owner_choice(choice, commit_timing=timing)
    details = command.get("outcome_details")
    if not isinstance(details, dict) or set(details) != {choice}:
        raise DecisionContractError("Owner outcome_details must contain only the chosen outcome")
    decision_id = stored_proposal["decision_id"]
    directory = root / ".better-product-graph" / "decisions" / decision_id
    current_path = directory / "current.json"
    supersedes = None
    if current_path.exists():
        current = read_json(current_path)
        _, current_record = _exact_project_ref(
            root, current.get("record_ref", {}), label="superseded decision"
        )
        supersedes = current["record_ref"]
        if (
            current_record.get("proposal_ref") == proposal["proposal_ref"]
            and current_record.get("chosen_outcome") == choice
            and current_record.get("commit_timing") == timing
            and current_record.get("outcome_details") == details
            and current_record.get("owner_authority", {}).get("actor") == actor
        ):
            _write_projections(root)
            append_event(
                root / ".better-product-graph" / "product-memory" / "PRODUCT_CHANGELOG.jsonl",
                {
                    "event_id": f"product-decision:{decision_id}:v{current_record['version']}",
                    "event_type": "PRODUCT_DECISION_VERSION_RECORDED",
                    "actor": actor["id"],
                    "decision_id": decision_id,
                    "version": current_record["version"],
                    "chosen_outcome": choice,
                    "route": current_record["route"],
                    "proposal_ref": proposal["proposal_ref"],
                    "record_ref": supersedes,
                    "supersedes": current_record.get("supersedes"),
                },
            )
            return {**current_record, "record_ref": supersedes}
    version = 1 if supersedes is None else int(supersedes["version"]) + 1
    record_path = directory / f"DECISION_v{version}.json"
    if record_path.exists():
        raise DecisionContractError(f"Decision Record version already exists: {decision_id} v{version}")
    draft = stored_proposal["agent_draft"]
    record = {
        "schema_version": "product-decision-record.v1",
        "decision_id": decision_id,
        "run_id": stored_proposal["run_id"],
        "version": version,
        "chosen_outcome": choice,
        "commit_timing": timing,
        "route": route,
        "outcome_details": deepcopy(details),
        "owner_authority": {"actor": deepcopy(actor), "kind": "OWNER_CHOICE"},
        "proposal_ref": deepcopy(proposal["proposal_ref"]),
        "agent_recommendation": draft["recommendation"],
        "agent_draft": deepcopy(draft),
        "supersedes": deepcopy(supersedes),
    }
    atomic_write_json(record_path, record)
    record_ref = {
        "path": record_path.relative_to(root).as_posix(),
        "hash": sha256_file(record_path),
        "version": version,
    }
    atomic_write_json(
        current_path,
        {"schema_version": "product-decision-current.v1", "record_ref": record_ref},
    )
    _write_projections(root)
    append_event(
        root / ".better-product-graph" / "product-memory" / "PRODUCT_CHANGELOG.jsonl",
        {
            "event_id": f"product-decision:{decision_id}:v{version}",
            "event_type": "PRODUCT_DECISION_VERSION_RECORDED",
            "actor": actor["id"],
            "decision_id": decision_id,
            "version": version,
            "chosen_outcome": choice,
            "route": route,
            "proposal_ref": proposal["proposal_ref"],
            "record_ref": record_ref,
            "supersedes": supersedes,
        },
    )
    return {**record, "record_ref": record_ref}
