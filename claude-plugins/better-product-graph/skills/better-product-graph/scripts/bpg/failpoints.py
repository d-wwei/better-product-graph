"""Deterministic crash injection and conservative local recovery helpers."""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from .state_controller import StateConflict, StateController, TransitionRejected
from .storage import canonical_json_bytes, verify_event_chain


CRASH_PHASES = (
    "before_node_call",
    "before_result_persist",
    "after_result_persist",
    "after_receipt_persist",
    "after_receipt_ledger",
    "after_decision_record",
    "after_owner_event",
    "after_state_event",
    "before_transition",
    "after_transition",
    "partial_fanout",
    "timeout",
    "late_result",
    "unknown_side_effect",
    "after_archive_publish",
    "after_release_staged",
    "after_release_event",
    "after_release_state",
    "after_release_publish",
    "after_candidate_finalize_staged",
    "after_candidate_finalize_event",
    "after_candidate_finalize_state",
    "after_candidate_finalize_publish",
)


class InjectedCrash(RuntimeError):
    """A test-only crash at a named durable boundary."""


def _serialized(function):
    @wraps(function)
    def wrapped(controller: StateController, run_id: str, *args, **kwargs):
        with controller.mutation_lock(run_id):
            return function(controller, run_id, *args, **kwargs)

    return wrapped


def crash_at(target: str) -> Callable[[str], None]:
    if target not in CRASH_PHASES:
        raise ValueError(f"unknown crash phase: {target}")

    def inject(current: str) -> None:
        if current == target:
            raise InjectedCrash(target)

    return inject


def _replace_attempt(state: dict[str, Any], attempt_id: str, status: str) -> dict[str, Any]:
    next_state = json.loads(canonical_json_bytes(state))
    for attempt in next_state["dispatch_attempts"]:
        if attempt["attempt_id"] == attempt_id:
            attempt["status"] = status
            next_state["state_version"] += 1
            if status == "DISPATCHED":
                attempt["authorized_state_version"] = next_state["state_version"]
            return next_state
    raise TransitionRejected(f"dispatch attempt not found: {attempt_id}")


@_serialized
def persist_node_dispatch(
    controller: StateController,
    run_id: str,
    attempt_id: str,
    *,
    side_effect: str = "NONE",
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one exact attempt before the Host invokes a node."""

    state = controller.load_state(run_id)
    if any(item["attempt_id"] == attempt_id for item in state["dispatch_attempts"]):
        raise StateConflict(f"dispatch attempt already exists: {attempt_id}")
    next_state = json.loads(canonical_json_bytes(state))
    next_state["state_version"] += 1
    if contract is None:
        hashes: dict[str, str] = {}
        for ref in state.get("artifact_refs", {}).values():
            path = ref["path"]
            if path in hashes and hashes[path] != ref["hash"]:
                raise TransitionRejected(
                    f"dispatch inputs bind conflicting hashes for {path}"
                )
            hashes[path] = ref["hash"]
        refs = list(hashes)
        contract = controller.registry.dispatch_envelope(
            state["current_node"], attempt_id, refs, hashes
        )
    attempt = {
        "attempt_id": attempt_id,
        "node_id": state["current_node"],
        "state_version": state["state_version"],
        "authority_hash": controller._dispatch_authority_hash(state),
        "status": "PLANNED",
            "side_effect": side_effect,
            "retryable": False,
        }
    attempt["contract"] = contract
    next_state["dispatch_attempts"].append(attempt)
    controller._commit_state_event(
        run_id,
        state,
        next_state,
        {
            "event_type": "NODE_DISPATCH_PLANNED",
            "actor": "state-controller",
            "run_id": run_id,
            "attempt_id": attempt_id,
            "node_id": state["current_node"],
            "state_version": next_state["state_version"],
        },
        transaction_id=f"dispatch-plan-{attempt_id}",
    )
    return next_state


@_serialized
def begin_node_call(
    controller: StateController,
    run_id: str,
    attempt_id: str,
    *,
    failpoint: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    if failpoint is not None:
        failpoint("before_node_call")
    state = controller.load_state(run_id)
    next_state = _replace_attempt(state, attempt_id, "DISPATCHED")
    for attempt in next_state["dispatch_attempts"]:
        if attempt["attempt_id"] == attempt_id:
            attempt["authority_hash"] = controller._dispatch_authority_hash(next_state)
    controller._commit_state_event(
        run_id,
        state,
        next_state,
        {
            "event_type": "NODE_CALL_STARTED",
            "actor": "state-controller",
            "run_id": run_id,
            "attempt_id": attempt_id,
            "state_version": next_state["state_version"],
        },
        transaction_id=f"dispatch-start-{attempt_id}",
    )
    return next_state


@_serialized
def mark_dispatch_unknown(
    controller: StateController, run_id: str, attempt_id: str
) -> dict[str, Any]:
    state = controller.load_state(run_id)
    next_state = _replace_attempt(state, attempt_id, "UNKNOWN_SIDE_EFFECT")
    controller._commit_state_event(
        run_id,
        state,
        next_state,
        {
            "event_type": "NODE_CALL_OUTCOME_UNKNOWN",
            "actor": "state-controller",
            "run_id": run_id,
            "attempt_id": attempt_id,
            "state_version": next_state["state_version"],
        },
        transaction_id=f"dispatch-unknown-{attempt_id}",
    )
    return next_state


def _repair_unapplied_transition(
    controller: StateController, run_id: str, state: dict[str, Any], events: list[dict[str, Any]]
) -> bool:
    """Reject legacy partial transition recovery; exact WAL recovery runs first."""

    commits = [event for event in events if event["event_type"] == "NODE_TRANSITION_COMMITTED"]
    if not commits:
        return False
    commit = commits[-1]
    if commit["after_state_version"] <= state["state_version"]:
        return False
    if commit["before_state_version"] != state["state_version"]:
        raise StateConflict("cannot reconcile non-adjacent transition commit")
    if commit["from_node"] != state["current_node"]:
        raise StateConflict("transition commit does not match current snapshot")
    raise StateConflict(
        "transition event is ahead of snapshot without its exact state transaction journal"
    )


def _repair_incomplete_result(
    controller: StateController, run_id: str, state: dict[str, Any]
) -> str | None:
    for attempt in reversed(state["dispatch_attempts"]):
        if attempt["node_id"] != state["current_node"]:
            continue
        attempt_id = attempt["attempt_id"]
        result_path = controller._result_path(run_id, attempt_id)
        receipt_path = result_path.with_name("result-receipt.json")
        if not result_path.is_file() or receipt_path.exists():
            continue
        controller.recover_result_receipt(run_id, attempt_id)
        return attempt_id
    return None


@_serialized
def recover_run(controller: StateController, run_id: str) -> dict[str, Any]:
    """Inspect exact durable facts; never invent success or blindly redispatch."""

    recovered_transactions = controller.recover_transactions(run_id)
    if recovered_transactions:
        return {
            "status": "RECOVERED_TRANSACTION",
            "run_id": run_id,
            "recovered_transactions": recovered_transactions,
        }
    events = verify_event_chain(controller._events_path(run_id))
    state = controller.load_state(run_id)
    state_blockers = controller._full_state_commitment_blockers(state, events)
    if state_blockers:
        raise TransitionRejected(
            "event authority barrier: " + "; ".join(state_blockers)
        )
    if _repair_unapplied_transition(controller, run_id, state, events):
        return {"status": "RECOVERED_COMMIT", "run_id": run_id}
    state = controller.load_state(run_id)
    recovered_attempt = _repair_incomplete_result(controller, run_id, state)
    if recovered_attempt is not None:
        return {
            "status": "RECOVERED_RESULT",
            "run_id": run_id,
            "attempt_id": recovered_attempt,
            "redispatch_allowed": False,
        }
    state = controller.load_state(run_id)
    for attempt in reversed(state["dispatch_attempts"]):
        if attempt["node_id"] != state["current_node"]:
            continue
        attempt_id = attempt["attempt_id"]
        if attempt["status"] == "UNKNOWN_SIDE_EFFECT":
            return {
                "status": "RECONCILE_REQUIRED",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "redispatch_allowed": False,
            }
        if controller._result_path(run_id, attempt_id).is_file():
            return {
                "status": "READY_TO_TRANSITION",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "redispatch_allowed": False,
            }
        if attempt["status"] == "DISPATCHED":
            return {
                "status": "WAITING_RESULT",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "redispatch_allowed": False,
            }
        if attempt["status"] == "PLANNED":
            return {
                "status": "READY_TO_DISPATCH",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "redispatch_allowed": True,
            }
    return {"status": "CONSISTENT", "run_id": run_id}
