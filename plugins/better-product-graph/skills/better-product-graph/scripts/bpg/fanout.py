"""Persisted bounded fan-out mechanics; workers are read-only semantic producers."""

from __future__ import annotations

import re
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from .state_controller import StateConflict, StateController, TransitionRejected
from .storage import append_event, atomic_write_json, read_json, sha256_file


Worker = Callable[[dict[str, Any]], dict[str, Any]]
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
TERMINAL_ATTEMPT_STATUSES = frozenset(
    {"ACCEPTED", "RESULT_PERSISTED", "FAILED", "TIMED_OUT", "CANCELLED"}
)


def _serialized(function):
    @wraps(function)
    def wrapped(controller: StateController, run_id: str, *args, **kwargs):
        with controller.mutation_lock(run_id):
            return function(controller, run_id, *args, **kwargs)

    return wrapped


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        raise ValueError(f"{label} must be a path-safe stable identifier")


def _fanout_root(controller: StateController, run_id: str, plan_id: str) -> Path:
    _validate_id(plan_id, "plan_id")
    return controller.run_path(run_id) / "fanout" / plan_id


def _plan_path(controller: StateController, run_id: str, plan_id: str) -> Path:
    return _fanout_root(controller, run_id, plan_id) / "plan.json"


def _status_path(controller: StateController, run_id: str, plan_id: str) -> Path:
    return _fanout_root(controller, run_id, plan_id) / "status.json"


def _with_path(plan: dict[str, Any], path: Path) -> dict[str, Any]:
    return {**plan, "plan_path": str(path.resolve())}


def _validate_roles(roles: list[str], required_roles: list[str]) -> None:
    if not roles or len(roles) != len(set(roles)):
        raise ValueError("roles must be a non-empty unique list")
    for role in roles:
        _validate_id(role, "role")
    if not set(required_roles).issubset(roles):
        raise ValueError("required_roles must be a subset of roles")


@_serialized
def persist_fanout_plan(
    controller: StateController,
    run_id: str,
    *,
    plan_id: str,
    candidate_hash: str,
    roles: list[str],
    required_roles: list[str] | None = None,
    timeout_seconds: float = 30.0,
    failpoint=None,
) -> dict[str, Any]:
    """Persist an immutable full plan and all PENDING identities before dispatch."""

    _validate_id(plan_id, "plan_id")
    required = list(required_roles if required_roles is not None else roles)
    _validate_roles(roles, required)
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    state = controller.load_state(run_id)
    candidate_ref = state.get("current_candidate_ref")
    if not isinstance(candidate_ref, dict) or candidate_ref.get("hash") != candidate_hash:
        raise TransitionRejected("fanout candidate hash must equal the exact current Candidate")
    path = _plan_path(controller, run_id, plan_id)
    status_path = _status_path(controller, run_id, plan_id)
    if path.exists():
        existing = read_json(path)
        expected = {
            "candidate_hash": candidate_hash,
            "roles": roles,
            "required_roles": required,
            "timeout_seconds": timeout_seconds,
        }
        actual = {key: existing[key] for key in expected}
        if actual != expected:
            raise StateConflict(f"fanout plan identity conflict: {plan_id}")
        registered = any(item["plan_id"] == plan_id for item in state["fanout_plans"])
        if not status_path.exists():
            if registered:
                raise StateConflict(f"registered fanout plan is missing its status ledger: {plan_id}")
            atomic_write_json(
                status_path,
                {
                    "schema_version": "fanout-status.v0alpha",
                    "plan_id": plan_id,
                    "attempts": existing["attempts"],
                },
            )
        if not registered:
            controller.register_fanout_plan(
                run_id,
                {
                    "plan_id": plan_id,
                    "path": path.relative_to(controller.project_root).as_posix(),
                    "hash": sha256_file(path),
                    "version": 1,
                    "candidate_hash": candidate_hash,
                },
                expected_state_version=state["state_version"],
                failpoint=failpoint,
            )
        return _with_path(existing, path)

    attempts = [
        {
            "attempt_id": f"{plan_id}-{index + 1}",
            "role": role,
            "required": role in required,
            "candidate_hash": candidate_hash,
            "status": "PENDING",
        }
        for index, role in enumerate(roles)
    ]
    plan = {
        "schema_version": "fanout-plan.v0alpha",
        "plan_id": plan_id,
        "run_id": run_id,
        "state_version": state["state_version"],
        "candidate_hash": candidate_hash,
        "roles": roles,
        "required_roles": required,
        "timeout_seconds": timeout_seconds,
        "created_at": datetime.now(UTC).isoformat(),
        "attempts": attempts,
    }
    atomic_write_json(path, plan)
    atomic_write_json(
        status_path,
        {
            "schema_version": "fanout-status.v0alpha",
            "plan_id": plan_id,
            "attempts": attempts,
        },
    )
    plan_ref = {
        "plan_id": plan_id,
        "path": path.relative_to(controller.project_root).as_posix(),
        "hash": sha256_file(path),
        "version": 1,
        "candidate_hash": candidate_hash,
    }
    controller.register_fanout_plan(
        run_id,
        plan_ref,
        expected_state_version=state["state_version"],
        failpoint=failpoint,
    )
    return _with_path(plan, path)


def _merged_plan(controller: StateController, run_id: str, plan_id: str) -> dict[str, Any]:
    path = _plan_path(controller, run_id, plan_id)
    plan = read_json(path)
    status = read_json(_status_path(controller, run_id, plan_id))
    return {**plan, "attempts": status["attempts"], "plan_path": str(path.resolve())}


def _persist_worker_result(
    controller: StateController,
    run_id: str,
    plan_id: str,
    attempt: dict[str, Any],
    output: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(output, dict):
        raise TransitionRejected("fanout worker must return a JSON object")
    path = _fanout_root(controller, run_id, plan_id) / "results" / f"{attempt['attempt_id']}.json"
    payload = {
        "schema_version": "fanout-result.v0alpha",
        "attempt_id": attempt["attempt_id"],
        "role": attempt["role"],
        "candidate_hash": attempt["candidate_hash"],
        "output": output,
    }
    atomic_write_json(path, payload)
    return {
        "path": path.relative_to(controller.project_root).as_posix(),
        "hash": sha256_file(path),
        "version": 1,
    }


@_serialized
def execute_fanout(
    controller: StateController,
    run_id: str,
    plan_id: str,
    workers: dict[str, Worker],
    *,
    max_workers: int = 3,
) -> dict[str, Any]:
    """Run bounded read-only workers; only this parent function writes returned values."""

    merged = _merged_plan(controller, run_id, plan_id)
    status_path = _status_path(controller, run_id, plan_id)
    dispatchable = [item for item in merged["attempts"] if item["status"] == "PENDING"]
    for attempt in dispatchable:
        if attempt["role"] not in workers:
            raise TransitionRejected(f"missing worker for role {attempt['role']}")
        attempt["status"] = "DISPATCHED"
    atomic_write_json(
        status_path,
        {
            "schema_version": "fanout-status.v0alpha",
            "plan_id": plan_id,
            "attempts": merged["attempts"],
        },
    )
    executor = ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(dispatchable) or 1)))
    future_to_attempt: dict[Future[dict[str, Any]], dict[str, Any]] = {
        executor.submit(workers[attempt["role"]], dict(attempt)): attempt
        for attempt in dispatchable
    }
    done, not_done = wait(future_to_attempt, timeout=float(merged["timeout_seconds"]))
    for future in done:
        attempt = future_to_attempt[future]
        try:
            output = future.result()
            attempt["result_ref"] = _persist_worker_result(
                controller, run_id, plan_id, attempt, output
            )
            attempt["status"] = "RESULT_PERSISTED"
        except Exception as error:  # worker errors are data, not parent crashes
            attempt["status"] = "FAILED"
            attempt["error"] = f"{type(error).__name__}: {error}"
    for future in not_done:
        attempt = future_to_attempt[future]
        attempt["status"] = "TIMED_OUT"
        future.cancel()
    executor.shutdown(wait=False, cancel_futures=True)
    atomic_write_json(
        status_path,
        {
            "schema_version": "fanout-status.v0alpha",
            "plan_id": plan_id,
            "attempts": merged["attempts"],
        },
    )
    append_event(
        controller._events_path(run_id),
        {
            "event_type": "FANOUT_EXECUTION_RECORDED",
            "actor": "state-controller",
            "run_id": run_id,
            "plan_id": plan_id,
            "attempt_statuses": {
                item["attempt_id"]: item["status"] for item in merged["attempts"]
            },
        },
    )
    return {**merged, "status": "EXECUTED"}


@_serialized
def cancel_fanout_attempt(
    controller: StateController, run_id: str, plan_id: str, attempt_id: str
) -> dict[str, Any]:
    merged = _merged_plan(controller, run_id, plan_id)
    for attempt in merged["attempts"]:
        if attempt["attempt_id"] == attempt_id:
            if attempt["status"] not in {"PENDING", "DISPATCHED"}:
                raise StateConflict(f"cannot cancel attempt in {attempt['status']}")
            attempt["status"] = "CANCELLED"
            break
    else:
        raise TransitionRejected(f"unknown fanout attempt: {attempt_id}")
    atomic_write_json(
        _status_path(controller, run_id, plan_id),
        {
            "schema_version": "fanout-status.v0alpha",
            "plan_id": plan_id,
            "attempts": merged["attempts"],
        },
    )
    return merged


@_serialized
def join_fanout(
    controller: StateController,
    run_id: str,
    plan_id: str,
    submitted_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Join exact persisted worker results; callers only select durable attempts."""

    merged = _merged_plan(controller, run_id, plan_id)
    state = controller.load_state(run_id)
    current_ref = state.get("current_candidate_ref")
    current_hash = current_ref.get("hash") if isinstance(current_ref, dict) else None
    attempts = {item["attempt_id"]: item for item in merged["attempts"]}
    dispositions: list[dict[str, Any]] = []
    accepted_findings: list[list[dict[str, Any]]] = []
    join_root = _fanout_root(controller, run_id, plan_id) / "joined"
    for index, result in enumerate(submitted_results, start=1):
        attempt_id = result.get("attempt_id")
        attempt = attempts.get(attempt_id)
        if attempt is None:
            dispositions.append({"attempt_id": attempt_id, "status": "INVALID_ATTEMPT"})
            continue
        stale = (
            current_hash != merged["candidate_hash"]
            or result.get("candidate_hash") != merged["candidate_hash"]
            or attempt["status"] in {"TIMED_OUT", "CANCELLED", "ACCEPTED"}
        )
        if stale:
            dispositions.append({"attempt_id": attempt_id, "status": "LATE_STALE"})
            continue
        if attempt["status"] in {"PENDING", "DISPATCHED"}:
            dispositions.append({"attempt_id": attempt_id, "status": "NOT_DISPATCHED"})
            continue
        if attempt["status"] != "RESULT_PERSISTED":
            dispositions.append({"attempt_id": attempt_id, "status": "INVALID_RESULT"})
            continue
        result_ref = attempt.get("result_ref")
        if result.get("result_ref") != result_ref or not isinstance(result_ref, dict):
            dispositions.append({"attempt_id": attempt_id, "status": "RESULT_REF_MISMATCH"})
            continue
        try:
            result_path = (controller.project_root / result_ref["path"]).resolve()
            result_path.relative_to(controller.project_root)
        except (KeyError, ValueError):
            dispositions.append({"attempt_id": attempt_id, "status": "INVALID_RESULT"})
            continue
        if (
            result_path.is_symlink()
            or not result_path.is_file()
            or sha256_file(result_path) != result_ref.get("hash")
        ):
            dispositions.append({"attempt_id": attempt_id, "status": "RESULT_HASH_MISMATCH"})
            continue
        persisted = read_json(result_path)
        if (
            persisted.get("attempt_id") != attempt_id
            or persisted.get("role") != attempt.get("role")
            or persisted.get("candidate_hash") != merged["candidate_hash"]
        ):
            dispositions.append({"attempt_id": attempt_id, "status": "INVALID_RESULT"})
            continue
        findings = persisted.get("output", {}).get("findings")
        if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
            dispositions.append({"attempt_id": attempt_id, "status": "INVALID_RESULT"})
            continue
        if "findings" in result and result["findings"] != findings:
            dispositions.append({"attempt_id": attempt_id, "status": "RESULT_MISMATCH"})
            continue
        path = join_root / f"{index:03d}-{attempt_id}.json"
        atomic_write_json(
            path,
            {
                "schema_version": "fanout-join.v1",
                "attempt_id": attempt_id,
                "candidate_hash": merged["candidate_hash"],
                "result_ref": result_ref,
            },
        )
        attempt["status"] = "ACCEPTED"
        attempt["joined_ref"] = {
            "path": path.relative_to(controller.project_root).as_posix(),
            "hash": sha256_file(path),
            "version": 1,
        }
        accepted_findings.append(findings)
        dispositions.append({"attempt_id": attempt_id, "status": "ACCEPTED"})
    atomic_write_json(
        _status_path(controller, run_id, plan_id),
        {
            "schema_version": "fanout-status.v0alpha",
            "plan_id": plan_id,
            "attempts": merged["attempts"],
        },
    )
    nonterminal = [
        item for item in merged["attempts"] if item["status"] not in TERMINAL_ATTEMPT_STATUSES
    ]
    required_unaccepted = [
        item for item in merged["attempts"] if item["required"] and item["status"] != "ACCEPTED"
    ]
    status = "PARTIAL" if nonterminal else ("INCOMPLETE" if required_unaccepted else "JOINED")
    append_event(
        controller._events_path(run_id),
        {
            "event_type": "FANOUT_JOIN_RECORDED",
            "actor": "state-controller",
            "run_id": run_id,
            "plan_id": plan_id,
            "status": status,
            "dispositions": dispositions,
        },
    )
    return {
        "plan_id": plan_id,
        "status": status,
        "results": dispositions,
        "accepted_findings": accepted_findings,
    }


@_serialized
def recover_fanout(
    controller: StateController, run_id: str, plan_id: str
) -> dict[str, Any]:
    merged = _merged_plan(controller, run_id, plan_id)
    completed = [
        item["attempt_id"]
        for item in merged["attempts"]
        if item["status"] in TERMINAL_ATTEMPT_STATUSES
    ]
    dispatchable = [
        item["attempt_id"] for item in merged["attempts"] if item["status"] == "PENDING"
    ]
    waiting = [
        item["attempt_id"]
        for item in merged["attempts"]
        if item["status"] in {"PENDING", "DISPATCHED"}
    ]
    return {
        "status": "WAITING_FANOUT" if waiting else "FANOUT_TERMINAL",
        "plan_id": plan_id,
        "completed_attempt_ids": completed,
        "dispatchable_attempt_ids": dispatchable,
        "waiting_attempt_ids": waiting,
    }
