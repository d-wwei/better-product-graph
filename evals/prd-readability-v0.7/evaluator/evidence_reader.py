#!/usr/bin/env python3
"""Frozen stdlib-only durable evidence verifier for Suite v0.7."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any


RESULT_FIELDS = frozenset(
    {
        "schema_version", "evaluation_only", "authority", "suite_id", "case_id",
        "node_id", "attempt_id", "instruction_ref", "instruction_hash", "input_refs",
        "input_hashes", "preregistration_checkpoint_ref", "candidate_ref", "profile_ref",
        "guide_ref", "reviewer_resource_ref", "output_contract_ref",
        "author_execution_ref", "reviewer_execution_ref", "reviewer_role",
        "isolated_input_refs", "reader_readback", "reader_outcome_failures",
        "verbosity_assessment", "checklist_assessment", "visual_assessment", "result",
        "primary_diagnosis", "primary_repair_technique", "claim_boundary",
    }
)
READBACK_FIELDS = frozenset(
    {
        "problem_and_outcome", "primary_relationships", "mental_model",
        "main_path_and_recovery", "decision_conditions_and_risks", "navigation_map",
    }
)
MENTAL_MODEL_FIELDS = frozenset({"name", "role"})
NAVIGATION_FIELDS = frozenset({"target", "location"})
NAVIGATION_TARGETS = frozenset({"PRODUCT_RULES", "ACCEPTANCE", "RISKS_UNKNOWNS_NEXT"})
BASIS_FIELDS = frozenset({"path", "hash", "start_line", "end_line"})
FAILURE_FIELDS = frozenset({"outcome", "basis_refs", "reason"})
ASSESSMENT_FIELDS = frozenset(
    {"verdict", "issue_types", "repair_techniques", "basis_refs", "reason"}
)
VISUAL_ASSESSMENT_FIELDS = ASSESSMENT_FIELDS | frozenset(
    {"observation_status", "visual_pair_refs"}
)
VISUAL_PAIR_FIELDS = frozenset({"svg_ref", "png_ref"})
EXACT_REF_FIELDS = frozenset({"path", "hash", "version"})
EXECUTION_REF_FIELDS = frozenset({"kind", "id"})
STATE_FIELDS = frozenset(
    {
        "schema_version", "run_id", "run_type", "evaluation_only", "suite_id", "case_id",
        "prepare_identity_hash", "prepare_payload", "snapshot_refs", "state_version",
        "generation", "status", "current_node", "dispatch",
        "preregistration_checkpoint_ref", "superseded_attempts", "result_ref",
        "phase_manifest_binding",
    }
)
DISPATCH_FIELDS = frozenset(
    {
        "schema_version", "node_id", "attempt_id", "producer_kind", "validator",
        "instruction_ref", "instruction_hash", "input_refs", "input_hashes",
        "resource_refs", "writing_eval_context",
    }
)
CONTEXT_FIELDS = frozenset(
    {
        "schema_version", "evaluation_only", "suite_id", "case_id", "candidate_ref",
        "profile_ref", "guide_ref", "reviewer_resource_ref", "output_contract_ref",
        "installed_build_ref", "author_execution_ref", "isolated_input_refs",
        "reader_visible_visual_pairs", "expected_custody", "review_schema",
    }
)
TRANSACTION_FIELDS = frozenset(
    {
        "schema_version", "status", "transition_id", "kind", "run_id", "attempt_id",
        "base_state_hash", "target_state", "target_state_hash", "base_event_head",
        "target_event", "target_event_hash", "result_ref", "result_value",
        "snapshot_identity",
        "base_state",
    }
)
INIT_FIELDS = frozenset(
    {
        "schema_version", "run_id", "prepare_identity_hash", "prepare_payload",
        "attempt_id", "generation", "bindings",
    }
)
READER_OUTCOMES = frozenset({"UNDERSTAND", "SEE", "MODEL", "RETELL", "DECIDE", "LOCATE"})
DIAGNOSTIC_CATEGORIES = frozenset(
    {
        "SEMANTIC_REPETITION", "FLAT_PEER_OVERLOAD", "REPRESENTATION_COLLISION",
        "DETAIL_IN_MAIN_PATH", "DENSE_TABLE", "JARGON_INTRUSION",
        "CHECKLIST_FUNCTION_LOSS", "COMPLETION_SEMANTICS_AMBIGUOUS",
        "ARTIFACT_MATURITY_OVERCLAIM",
    }
)
REPAIR_TECHNIQUES = frozenset(
    {
        "REORDER", "GROUP", "EXPLAIN", "EXAMPLE", "VISUALIZE", "LAYER", "MERGE",
        "REFERENCE", "MOVE", "TRIM", "RESTORE_FUNCTION", "BOUNDARY",
    }
)


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _closed(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} must be a closed object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    ref = _closed(value, EXACT_REF_FIELDS, label)
    path = ref.get("path")
    digest = ref.get("hash")
    version = ref.get("version")
    if (
        not isinstance(path, str)
        or not path
        or PurePosixPath(path).is_absolute()
        or ".." in PurePosixPath(path).parts
        or PurePosixPath(path).as_posix() != path
    ):
        raise ValueError(f"{label}.path is invalid")
    if (
        not isinstance(digest, str)
        or len(digest) != 71
        or not digest.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in digest[7:])
    ):
        raise ValueError(f"{label}.hash is invalid")
    if isinstance(version, bool) or not isinstance(version, (str, int)):
        raise ValueError(f"{label}.version is invalid")
    return ref


def _execution_ref(value: Any, label: str) -> dict[str, str]:
    ref = _closed(value, EXECUTION_REF_FIELDS, label)
    _text(ref.get("kind"), f"{label}.kind")
    _text(ref.get("id"), f"{label}.id")
    return ref


def _project_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("durable evidence path escapes project root") from error
    return path


def _read_ref(root: Path, value: Any, label: str) -> tuple[dict[str, Any], bytes]:
    ref = _exact_ref(value, label)
    path = _project_path(root, ref["path"])
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is missing or unsafe")
    content = path.read_bytes()
    if sha256_bytes(content) != ref["hash"]:
        raise ValueError(f"{label} hash is stale")
    return ref, content


def _read_json_bytes(content: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _basis_refs(value: Any, label: str, candidate_ref: dict[str, Any], line_count: int) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be non-empty")
    for raw in value:
        basis = _closed(raw, BASIS_FIELDS, label)
        start = basis.get("start_line")
        end = basis.get("end_line")
        if (
            basis.get("path") != candidate_ref["path"]
            or basis.get("hash") != candidate_ref["hash"]
            or isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 1
            or end < start
            or end > line_count
        ):
            raise ValueError(f"{label} is outside the exact Candidate")


def _enum_list(value: Any, allowed: frozenset[str], label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) != len(set(value))
        or any(not isinstance(item, str) or item not in allowed for item in value)
    ):
        raise ValueError(f"{label} is invalid")
    return value


def _assessment(
    value: Any,
    *,
    label: str,
    candidate_ref: dict[str, Any],
    line_count: int,
    expected_visual_pairs: list[dict[str, Any]],
) -> tuple[set[str], set[str], bool]:
    visual = label == "visual_assessment"
    item = _closed(
        value, VISUAL_ASSESSMENT_FIELDS if visual else ASSESSMENT_FIELDS, label
    )
    verdict = item.get("verdict")
    if verdict not in ({"PASS", "FINDING", "NOT_NEEDED"} if visual else {"PASS", "FINDING"}):
        raise ValueError(f"{label}.verdict is invalid")
    _text(item.get("reason"), f"{label}.reason")
    _basis_refs(item.get("basis_refs"), f"{label}.basis_refs", candidate_ref, line_count)
    issues = set(_enum_list(item.get("issue_types"), DIAGNOSTIC_CATEGORIES, label))
    repairs = set(_enum_list(item.get("repair_techniques"), REPAIR_TECHNIQUES, label))
    if (verdict == "FINDING") != bool(issues and repairs):
        raise ValueError(f"{label} diagnosis/repair does not match verdict")
    if visual:
        raw_pairs = item.get("visual_pair_refs")
        if not isinstance(raw_pairs, list):
            raise ValueError("visual_pair_refs must be a list")
        pairs = []
        for raw in raw_pairs:
            pair = _closed(raw, VISUAL_PAIR_FIELDS, "visual_pair_ref")
            pairs.append(
                {
                    "svg_ref": copy.deepcopy(_exact_ref(pair.get("svg_ref"), "svg_ref")),
                    "png_ref": copy.deepcopy(_exact_ref(pair.get("png_ref"), "png_ref")),
                }
            )
        observation = item.get("observation_status")
        if verdict == "NOT_NEEDED":
            valid = observation == "NOT_NEEDED" and not pairs and not expected_visual_pairs
        elif verdict == "PASS":
            valid = observation == "OBSERVED" and pairs == expected_visual_pairs and bool(pairs)
        else:
            valid = pairs == expected_visual_pairs and observation == (
                "OBSERVED" if expected_visual_pairs else "NOT_OBSERVED"
            )
        if not valid:
            raise ValueError("visual assessment differs from exact visual authority")
    return issues, repairs, verdict == "FINDING"


def validate_raw_result(
    value: Any,
    *,
    dispatch: dict[str, Any],
    checkpoint_ref: dict[str, Any],
    candidate_bytes: bytes,
) -> dict[str, Any]:
    """Validate the full closed v3.1 result and every copied dispatch authority."""

    result = _closed(value, RESULT_FIELDS, "writing_eval_result")
    context = dispatch.get("writing_eval_context")
    if not isinstance(context, dict):
        raise ValueError("dispatch writing_eval_context is missing")
    exact_values = {
        "schema_version": "document-experience-reader-eval.v3.1",
        "evaluation_only": True,
        "authority": "ADVISORY_ONLY",
        "suite_id": context.get("suite_id"),
        "case_id": context.get("case_id"),
        "node_id": "writing-eval.review",
        "attempt_id": dispatch.get("attempt_id"),
        "instruction_ref": dispatch.get("instruction_ref"),
        "instruction_hash": dispatch.get("instruction_hash"),
        "input_refs": dispatch.get("input_refs"),
        "input_hashes": dispatch.get("input_hashes"),
        "preregistration_checkpoint_ref": checkpoint_ref,
        "candidate_ref": context.get("candidate_ref"),
        "profile_ref": context.get("profile_ref"),
        "guide_ref": context.get("guide_ref"),
        "reviewer_resource_ref": context.get("reviewer_resource_ref"),
        "output_contract_ref": context.get("output_contract_ref"),
        "author_execution_ref": context.get("author_execution_ref"),
        "reviewer_role": "writing_standard",
        "isolated_input_refs": context.get("isolated_input_refs"),
        "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
    }
    for field, expected in exact_values.items():
        if result.get(field) != expected:
            raise ValueError(f"writing_eval_result.{field} differs from exact dispatch authority")
    candidate_ref = _exact_ref(result.get("candidate_ref"), "candidate_ref")
    if not isinstance(candidate_bytes, bytes) or sha256_bytes(candidate_bytes) != candidate_ref["hash"]:
        raise ValueError("Candidate bytes differ from exact dispatch authority")
    try:
        line_count = max(1, len(candidate_bytes.decode("utf-8").splitlines()))
    except UnicodeError as error:
        raise ValueError("Candidate is not UTF-8") from error
    author = _execution_ref(result.get("author_execution_ref"), "author_execution_ref")
    reviewer = _execution_ref(result.get("reviewer_execution_ref"), "reviewer_execution_ref")
    if reviewer["kind"] != "HOST_SUBAGENT_ATTEMPT" or reviewer["id"] == author["id"]:
        raise ValueError("reviewer identity is not independent")

    readback = _closed(result.get("reader_readback"), READBACK_FIELDS, "reader_readback")
    for field in (
        "problem_and_outcome", "primary_relationships", "main_path_and_recovery",
        "decision_conditions_and_risks",
    ):
        _text(readback.get(field), f"reader_readback.{field}")
    mental = readback.get("mental_model")
    if not isinstance(mental, list) or not 3 <= len(mental) <= 5:
        raise ValueError("mental_model requires three to five components")
    names = []
    for raw in mental:
        item = _closed(raw, MENTAL_MODEL_FIELDS, "mental_model")
        names.append(_text(item.get("name"), "mental_model.name"))
        _text(item.get("role"), "mental_model.role")
    if len(names) != len(set(names)):
        raise ValueError("mental_model names must be unique")
    navigation = readback.get("navigation_map")
    if not isinstance(navigation, list):
        raise ValueError("navigation_map must be a list")
    targets = []
    for raw in navigation:
        item = _closed(raw, NAVIGATION_FIELDS, "navigation_map")
        targets.append(_text(item.get("target"), "navigation_map.target"))
        _text(item.get("location"), "navigation_map.location")
    if len(targets) != len(set(targets)) or set(targets) != NAVIGATION_TARGETS:
        raise ValueError("navigation_map must cover all targets once")

    failures = result.get("reader_outcome_failures")
    if not isinstance(failures, list):
        raise ValueError("reader_outcome_failures must be a list")
    failure_outcomes = []
    for raw in failures:
        item = _closed(raw, FAILURE_FIELDS, "reader_outcome_failure")
        if item.get("outcome") not in READER_OUTCOMES:
            raise ValueError("reader outcome is invalid")
        failure_outcomes.append(item["outcome"])
        _text(item.get("reason"), "reader_outcome_failure.reason")
        _basis_refs(item.get("basis_refs"), "reader_outcome_failure.basis_refs", candidate_ref, line_count)
    if len(failure_outcomes) != len(set(failure_outcomes)):
        raise ValueError("reader outcomes must be unique")

    diagnoses: set[str] = set()
    repairs: set[str] = set()
    finding = False
    for field in ("verbosity_assessment", "checklist_assessment", "visual_assessment"):
        found_diagnoses, found_repairs, is_finding = _assessment(
            result.get(field),
            label=field,
            candidate_ref=candidate_ref,
            line_count=line_count,
            expected_visual_pairs=context.get("reader_visible_visual_pairs", []),
        )
        diagnoses.update(found_diagnoses)
        repairs.update(found_repairs)
        finding = finding or is_finding
    verdict = result.get("result")
    if verdict == "PASS":
        if failures or finding or result.get("primary_diagnosis") is not None or result.get("primary_repair_technique") is not None:
            raise ValueError("PASS cannot carry failures or primary repair")
    elif verdict == "FINDING":
        if not (failures or finding):
            raise ValueError("FINDING requires an observed failure")
        if result.get("primary_diagnosis") not in diagnoses or result.get("primary_repair_technique") not in repairs:
            raise ValueError("FINDING primary pair must come from assessments")
    else:
        raise ValueError("result must be PASS or FINDING")
    return copy.deepcopy(result)


def _verify_event_chain(
    content: bytes, run_id: str, attempt_id: str, result_ref: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    previous = None
    events = []
    completion_events = []
    for line in content.splitlines():
        event = _read_json_bytes(line, "event")
        claimed = event.get("event_hash")
        payload = {key: value for key, value in event.items() if key != "event_hash"}
        if event.get("previous_hash") != previous or sha256_bytes(canonical_json_bytes(payload)) != claimed:
            raise ValueError("event chain hash is invalid")
        previous = claimed
        events.append(event)
        if event.get("event_type") == "WRITING_EVAL_COMPLETED":
            if event.get("run_id") != run_id or event.get("attempt_id") != attempt_id or event.get("result_ref") != result_ref:
                raise ValueError("completion event authority is invalid")
            completion_events.append(event)
    if len(completion_events) != 1:
        raise ValueError("one completion event is required")
    return events, completion_events[0]


def _verify_snapshot_identity(root: Path, value: Any) -> None:
    if value is None:
        return
    expected_fields = {"path", "hash", "device", "inode", "size", "mtime_ns"}
    if not isinstance(value, list) or not value:
        raise ValueError("snapshot_identity is invalid")
    for item in value:
        if not isinstance(item, dict) or set(item) != expected_fields:
            raise ValueError("snapshot_identity item is invalid")
        path = _project_path(root, item["path"])
        current = os.lstat(path)
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_dev != item["device"]
            or current.st_ino != item["inode"]
            or current.st_size != item["size"]
            or current.st_mtime_ns != item["mtime_ns"]
            or sha256_bytes(path.read_bytes()) != item["hash"]
        ):
            raise ValueError("snapshot_identity is stale")


def _verify_transition_semantics(
    transaction: dict[str, Any], expected_run_id: str
) -> None:
    """Bind every journal identity and kind to its exact v0.7 state delta."""

    kind = transaction["kind"]
    base = transaction["base_state"]
    target = transaction["target_state"]
    event = transaction["target_event"]
    attempt_id = transaction["attempt_id"]
    base_dispatch = base.get("dispatch")
    target_dispatch = target.get("dispatch")
    base_attempt = (
        base_dispatch.get("attempt_id") if isinstance(base_dispatch, dict) else None
    )
    target_attempt = (
        target_dispatch.get("attempt_id")
        if isinstance(target_dispatch, dict)
        else None
    )
    common_event_fields = {
        "schema_version", "event_id", "recorded_at", "previous_hash",
        "event_type", "actor", "run_id", "attempt_id", "event_hash",
    }
    event_fields = {
        "dispatch": common_event_fields,
        "revoke": common_event_fields | {
            "successor_attempt_id", "predecessor_instruction_hash",
            "successor_instruction_hash",
        },
        "bind_manifest": common_event_fields | {"phase", "manifest_ref"},
        "complete": common_event_fields | {
            "result_ref", "result", "human_reader_observation",
        },
    }
    event_types = {
        "dispatch": "WRITING_EVAL_REVIEW_DISPATCHED",
        "revoke": "WRITING_EVAL_UNSTARTED_DISPATCH_REVOKED",
        "bind_manifest": "WRITING_EVAL_PHASE_MANIFEST_BOUND",
        "complete": "WRITING_EVAL_COMPLETED",
    }
    if (
        set(base) != STATE_FIELDS
        or set(target) != STATE_FIELDS
        or set(event) != event_fields[kind]
        or not isinstance(base_dispatch, dict)
        or not isinstance(target_dispatch, dict)
        or transaction.get("run_id") != expected_run_id
        or base.get("run_id") != expected_run_id
        or target.get("run_id") != expected_run_id
        or event.get("run_id") != expected_run_id
        or event.get("schema_version") != "audit-event.v1"
        or event.get("event_id")
        != f"writing-eval-transition-{transaction['transition_id']}"
        or event.get("event_type") != event_types[kind]
        or event.get("actor") != "writing-eval-controller"
        or not isinstance(base.get("state_version"), int)
        or target.get("state_version") != base["state_version"] + 1
        or transaction.get("transition_id")
        != f"{kind}-{attempt_id}-v{target.get('state_version')}"
    ):
        raise ValueError("transition kind or identity semantics are invalid")

    if kind == "revoke":
        unchanged = STATE_FIELDS - {
            "state_version", "generation", "dispatch",
            "preregistration_checkpoint_ref", "superseded_attempts",
        }
        expected_superseded = list(base.get("superseded_attempts", [])) + [
            {
                "attempt_id": base_attempt,
                "instruction_hash": base_dispatch.get("instruction_hash"),
                "status": "REVOKED_UNSTARTED",
            }
        ]
        valid = (
            attempt_id == target_attempt
            and event.get("attempt_id") == base_attempt
            and event.get("successor_attempt_id") == target_attempt
            and event.get("predecessor_instruction_hash")
            == base_dispatch.get("instruction_hash")
            and event.get("successor_instruction_hash")
            == target_dispatch.get("instruction_hash")
            and base_dispatch.get("status") in {"PLANNED", "DISPATCHED"}
            and target_dispatch.get("status") == "PLANNED"
            and target.get("generation") == base.get("generation") + 1
            and target.get("superseded_attempts") == expected_superseded
            and all(target.get(field) == base.get(field) for field in unchanged)
        )
    else:
        valid = (
            attempt_id == base_attempt == target_attempt
            and event.get("attempt_id") == attempt_id
        )
        expected = copy.deepcopy(base)
        expected["state_version"] += 1
        if kind == "dispatch":
            expected["dispatch"]["status"] = "DISPATCHED"
            valid = valid and base_dispatch.get("status") == "PLANNED"
        elif kind == "bind_manifest":
            binding = {
                "phase": event.get("phase"),
                "manifest_ref": event.get("manifest_ref"),
            }
            expected["phase_manifest_binding"] = binding
            valid = (
                valid
                and base.get("phase_manifest_binding") is None
                and target.get("phase_manifest_binding") == binding
            )
        else:
            expected["status"] = "COMPLETED"
            expected["dispatch"]["status"] = "COMPLETED"
            expected["result_ref"] = transaction.get("result_ref")
            valid = (
                valid
                and base.get("status") == "ACTIVE"
                and base_dispatch.get("status") == "DISPATCHED"
                and base.get("result_ref") is None
                and event.get("result_ref") == transaction.get("result_ref")
                and event.get("result")
                == (
                    transaction.get("result_value", {}).get("result")
                    if isinstance(transaction.get("result_value"), dict)
                    else None
                )
                and event.get("human_reader_observation") == "NOT_RUN"
            )
        valid = valid and target == expected
    if not valid:
        raise ValueError("transition state delta provenance is invalid")


def _verify_full_provenance(
    root: Path,
    run_root: Path,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    entry: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    init_path = run_root / "init-transaction.json"
    if init_path.is_symlink() or not init_path.is_file():
        raise ValueError("prepare identity provenance is missing")
    init = _read_json_bytes(init_path.read_bytes(), "init transaction")
    _closed(init, INIT_FIELDS, "init transaction")
    prepare_payload = init.get("prepare_payload")
    prepare_event_fields = {
        "schema_version", "event_id", "recorded_at", "previous_hash",
        "event_type", "actor", "run_id", "suite_id", "case_id",
        "prepare_identity_hash", "snapshot_refs_hash", "attempt_id", "event_hash",
    }
    if (
        init.get("schema_version") != "writing-eval-init-transaction.v1"
        or init.get("run_id") != state["run_id"]
        or not isinstance(prepare_payload, dict)
        or init.get("prepare_identity_hash")
        != sha256_bytes(canonical_json_bytes(prepare_payload))
        or init.get("generation") != 1
        or not events
        or set(events[0]) != prepare_event_fields
        or events[0].get("schema_version") != "audit-event.v1"
        or events[0].get("event_type") != "WRITING_EVAL_PREPARED"
        or events[0].get("actor") != "writing-eval-controller"
        or events[0].get("run_id") != state["run_id"]
        or events[0].get("suite_id") != state["suite_id"]
        or events[0].get("case_id") != state["case_id"]
        or events[0].get("previous_hash") is not None
        or events[0].get("attempt_id") != init.get("attempt_id")
        or events[0].get("prepare_identity_hash")
        != init.get("prepare_identity_hash")
    ):
        raise ValueError("prepare identity provenance is invalid")
    transactions_root = run_root / "transactions"
    if transactions_root.is_symlink() or not transactions_root.is_dir():
        raise ValueError("transition provenance is missing")
    transactions: list[tuple[Path, dict[str, Any]]] = []
    for path in transactions_root.glob("*.json"):
        if path.is_symlink() or not path.is_file():
            raise ValueError("transition provenance is unsafe")
        transaction = _read_json_bytes(path.read_bytes(), "transaction")
        _closed(transaction, TRANSACTION_FIELDS, "transaction")
        target = transaction.get("target_state")
        target_event = transaction.get("target_event")
        event_payload = (
            {key: value for key, value in target_event.items() if key != "event_hash"}
            if isinstance(target_event, dict)
            else {}
        )
        if (
            transaction.get("schema_version") != "writing-eval-transition.v1"
            or transaction.get("status") != "COMMITTED"
            or transaction.get("kind")
            not in {"dispatch", "revoke", "bind_manifest", "complete"}
            or not isinstance(transaction.get("base_state"), dict)
            or transaction.get("base_state_hash")
            != sha256_bytes(canonical_json_bytes(transaction["base_state"]))
            or not isinstance(target, dict)
            or transaction.get("target_state_hash")
            != sha256_bytes(canonical_json_bytes(target))
            or not isinstance(target_event, dict)
            or transaction.get("target_event_hash")
            != target_event.get("event_hash")
            or transaction.get("target_event_hash")
            != sha256_bytes(canonical_json_bytes(event_payload))
            or path.name != f"{transaction.get('transition_id')}.json"
        ):
            raise ValueError("transition provenance journal is invalid")
        _verify_transition_semantics(transaction, state["run_id"])
        transactions.append((path, transaction))
    transactions.sort(key=lambda item: item[1]["target_state"]["state_version"])
    if (
        not transactions
        or len(events) != len(transactions) + 1
        or [item[1]["target_state"]["state_version"] for item in transactions]
        != list(range(2, state["state_version"] + 1))
        or sum(
            item[1].get("kind") == "bind_manifest" for item in transactions
        ) != 1
    ):
        raise ValueError("transition provenance is incomplete")
    binding = next(
        item[1] for item in transactions if item[1]["kind"] == "bind_manifest"
    )
    binding_base = binding["base_state"]
    binding_dispatch = binding_base.get("dispatch")
    expected_state_ref = {
        "path": (run_root / "state.json").relative_to(root).as_posix(),
        "hash": sha256_bytes(canonical_json_bytes(binding_base) + b"\n"),
        "version": binding_base.get("state_version"),
    }
    if (
        entry.get("state_ref") != expected_state_ref
        or binding_base.get("status") != "ACTIVE"
        or not isinstance(binding_dispatch, dict)
        or binding_dispatch.get("status") != "DISPATCHED"
        or binding_dispatch.get("attempt_id") != entry.get("attempt_id")
        or binding_base.get("result_ref") is not None
        or binding.get("attempt_id") != entry.get("attempt_id")
    ):
        raise ValueError("manifest transition base state is not frozen")
    predecessor = transactions[0][1]["base_state"]
    invariant = {
        "schema_version": "writing-eval-state.v1",
        "run_id": state["run_id"],
        "run_type": "writing_eval",
        "evaluation_only": True,
        "suite_id": state["suite_id"],
        "case_id": state["case_id"],
        "prepare_identity_hash": init["prepare_identity_hash"],
        "prepare_payload": init["prepare_payload"],
        "snapshot_refs": state["snapshot_refs"],
        "current_node": "writing-eval.review",
    }
    if (
        set(predecessor) != STATE_FIELDS
        or predecessor.get("state_version") != 1
        or predecessor.get("generation") != 1
        or predecessor.get("status") != "ACTIVE"
        or predecessor.get("dispatch", {}).get("status") != "PLANNED"
        or predecessor.get("phase_manifest_binding") is not None
        or predecessor.get("result_ref") is not None
        or any(predecessor.get(key) != value for key, value in invariant.items())
        or events[0].get("snapshot_refs_hash")
        != sha256_bytes(canonical_json_bytes(predecessor["snapshot_refs"]))
    ):
        raise ValueError("prepared state provenance is invalid")
    event_head = events[0]["event_hash"]
    for index, (_path, transaction) in enumerate(transactions, 1):
        target = transaction["target_state"]
        if (
            transaction["base_state"] != predecessor
            or transaction["base_event_head"] != event_head
            or transaction["target_event"] != events[index]
            or target.get("state_version") != predecessor.get("state_version") + 1
            or any(target.get(key) != value for key, value in invariant.items())
        ):
            raise ValueError("transition predecessor provenance is invalid")
        _verify_snapshot_identity(root, transaction.get("snapshot_identity"))
        predecessor = target
        event_head = events[index]["event_hash"]
    completion_path, completion = transactions[-1]
    if predecessor != state or completion.get("kind") != "complete":
        raise ValueError("completion provenance does not reach durable state")
    return completion_path, completion


def read_completed_evidence(
    project_root: Path,
    skill_root: Path,
    entry: dict[str, Any],
) -> dict[str, Any]:
    """Read one exact immutable manifest entry without importing live product code."""

    root = project_root.resolve(strict=True)
    run_id = entry["run_id"]
    run_root = _project_path(root, f".better-product-graph/writing-evals/{run_id}")
    state_path = run_root / "state.json"
    if state_path.is_symlink() or not state_path.is_file():
        raise ValueError("durable state is missing")
    state = _read_json_bytes(state_path.read_bytes(), "state")
    _closed(state, STATE_FIELDS, "state")
    phase = entry["phase"]
    manifest_path = (
        root
        / ".better-product-graph"
        / "writing-evals"
        / "execution-manifests"
        / f"{phase}.json"
    )
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("bound phase manifest is missing")
    manifest_bytes = manifest_path.read_bytes()
    manifest = _read_json_bytes(manifest_bytes, "phase manifest")
    manifest_ref = {
        "path": manifest_path.relative_to(root).as_posix(),
        "hash": sha256_bytes(manifest_bytes),
        "version": 1,
    }
    if (
        manifest.get("schema_version")
        != "prd-readability-v0.7-execution-manifest.v1"
        or manifest.get("phase") != phase
        or not isinstance(manifest.get("entries"), list)
        or len(manifest["entries"]) != 27
        or sum(item == entry for item in manifest["entries"]) != 1
        or state.get("phase_manifest_binding")
        != {"phase": phase, "manifest_ref": manifest_ref}
    ):
        raise ValueError("durable state lacks exact phase manifest binding")
    dispatch = state.get("dispatch")
    context = dispatch.get("writing_eval_context") if isinstance(dispatch, dict) else None
    if (
        state.get("schema_version") != "writing-eval-state.v1"
        or state.get("run_id") != run_id
        or state.get("run_type") != "writing_eval"
        or state.get("evaluation_only") is not True
        or state.get("suite_id") != entry["suite_id"]
        or state.get("case_id") != entry["agent_case_id"]
        or state.get("status") != "COMPLETED"
        or state.get("current_node") != "writing-eval.review"
        or state.get("superseded_attempts") != []
        or not isinstance(dispatch, dict)
        or dispatch.get("status") != "COMPLETED"
        or dispatch.get("attempt_id") != entry["attempt_id"]
        or not isinstance(context, dict)
        or context.get("installed_build_ref") != entry["installed_build_ref"]
        or context.get("author_execution_ref") != entry["author_execution_ref"]
        or state.get("preregistration_checkpoint_ref") != entry["preregistration_checkpoint_ref"]
    ):
        raise ValueError("durable state differs from execution manifest")
    plugin_manifest = skill_root.resolve().parents[1] / entry["installed_build_ref"]["path"]
    if plugin_manifest.is_symlink() or not plugin_manifest.is_file() or sha256_bytes(plugin_manifest.read_bytes()) != entry["installed_build_ref"]["hash"]:
        raise ValueError("installed build differs from manifest")

    checkpoint_ref, checkpoint_bytes = _read_ref(root, entry["preregistration_checkpoint_ref"], "checkpoint_ref")
    checkpoint = _read_json_bytes(checkpoint_bytes, "checkpoint")
    checkpoint_fields = {
        "schema_version", "status", "run_id", "attempt_id", "suite_id", "case_id",
        "evaluation_only", "expected_custody", "refs", "claim_boundary",
    }
    expected_checkpoint_refs = {
        "source_suite_ref", "source_case_ref", "source_candidate_ref", "suite_ref",
        "case_ref", "candidate_ref", "profile_ref", "guide_ref", "instruction_ref",
        "reviewer_resource_ref", "output_contract_ref", "installed_build_ref",
        "dispatch_ref",
    }
    if (
        set(checkpoint) != checkpoint_fields
        or checkpoint.get("schema_version")
        != "writing-eval-preregistration-checkpoint.v1"
        or checkpoint.get("status") != "PREREGISTERED_BEFORE_RESULT"
        or checkpoint.get("run_id") != run_id
        or checkpoint.get("attempt_id") != entry["attempt_id"]
        or checkpoint.get("suite_id") != entry["suite_id"]
        or checkpoint.get("case_id") != entry["agent_case_id"]
        or checkpoint.get("evaluation_only") is not True
        or checkpoint.get("expected_custody") != "EVALUATOR_ONLY_EXCLUDED"
        or not isinstance(checkpoint.get("refs"), dict)
        or set(checkpoint["refs"]) != expected_checkpoint_refs
        or checkpoint["refs"].get("installed_build_ref")
        != entry["installed_build_ref"]
    ):
        raise ValueError("checkpoint differs from manifest")
    dispatch_ref, dispatch_bytes = _read_ref(root, checkpoint.get("refs", {}).get("dispatch_ref"), "dispatch_ref")
    durable_dispatch = copy.deepcopy(dispatch)
    durable_dispatch.pop("status", None)
    _closed(durable_dispatch, DISPATCH_FIELDS, "dispatch")
    _closed(context, CONTEXT_FIELDS, "writing_eval_context")
    if _read_json_bytes(dispatch_bytes, "dispatch") != durable_dispatch:
        raise ValueError("dispatch differs from durable state")
    result_ref, result_bytes = _read_ref(root, state.get("result_ref"), "result_ref")
    result = _read_json_bytes(result_bytes, "result")
    candidate_ref = context.get("candidate_ref")
    _, candidate_bytes = _read_ref(root, candidate_ref, "candidate_ref")
    validated = validate_raw_result(
        result,
        dispatch=durable_dispatch,
        checkpoint_ref=checkpoint_ref,
        candidate_bytes=candidate_bytes,
    )
    if validated.get("reviewer_execution_ref") != entry["reviewer_execution_ref"]:
        raise ValueError("reviewer differs from execution manifest")
    _, events_bytes = _read_ref(
        root,
        {
            "path": f".better-product-graph/writing-evals/{run_id}/events.jsonl",
            "hash": sha256_bytes((run_root / "events.jsonl").read_bytes()),
            "version": 1,
        },
        "events_ref",
    )
    events, completion_event = _verify_event_chain(
        events_bytes, run_id, entry["attempt_id"], result_ref
    )
    transaction_path, transaction = _verify_full_provenance(
        root, run_root, state, events, entry
    )
    target_event = transaction.get("target_event")
    if not isinstance(target_event, dict):
        raise ValueError("completion transaction target event is invalid")
    target_event_payload = {
        key: value for key, value in target_event.items() if key != "event_hash"
    }
    if (
        transaction.get("schema_version") != "writing-eval-transition.v1"
        or transaction.get("status") != "COMMITTED"
        or transaction.get("kind") != "complete"
        or transaction.get("run_id") != run_id
        or transaction.get("attempt_id") != entry["attempt_id"]
        or transaction.get("target_state") != state
        or transaction.get("result_ref") != result_ref
        or transaction.get("result_value") != validated
        or transaction.get("target_state_hash") != sha256_bytes(canonical_json_bytes(state))
        or transaction.get("target_event") != completion_event
        or transaction.get("target_event_hash") != completion_event.get("event_hash")
        or sha256_bytes(canonical_json_bytes(target_event_payload))
        != transaction.get("target_event_hash")
        or transaction_path.name != f"{transaction.get('transition_id')}.json"
    ):
        raise ValueError("completion transaction authority is invalid")
    return {
        "schema_version": "writing-eval-controller-evidence.v1",
        "run_id": run_id,
        "suite_id": state["suite_id"],
        "case_id": state["case_id"],
        "attempt_id": entry["attempt_id"],
        "reviewer_execution_ref": copy.deepcopy(validated["reviewer_execution_ref"]),
        "installed_build_ref": copy.deepcopy(entry["installed_build_ref"]),
        "controller_refs": {
            "state_ref": {
                "path": state_path.relative_to(root).as_posix(),
                "hash": sha256_bytes(state_path.read_bytes()),
                "version": state.get("state_version"),
            },
            "result_ref": result_ref,
            "events_ref": {
                "path": (run_root / "events.jsonl").relative_to(root).as_posix(),
                "hash": sha256_bytes(events_bytes),
                "version": 1,
            },
            "transaction_ref": {
                "path": transaction_path.relative_to(root).as_posix(),
                "hash": sha256_bytes(transaction_path.read_bytes()),
                "version": 1,
            },
            "dispatch_ref": dispatch_ref,
            "checkpoint_ref": checkpoint_ref,
        },
        "dispatch": durable_dispatch,
        "preregistration_checkpoint_ref": checkpoint_ref,
        "candidate_bytes": candidate_bytes,
        "reader_visible_visual_pairs": copy.deepcopy(context.get("reader_visible_visual_pairs", [])),
        "result": validated,
        "evaluation_only": True,
        "product_authority": "NONE",
    }
