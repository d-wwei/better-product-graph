"""Atomic local storage and meaningful-event integrity helpers."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .locking import exclusive_file_lock


class IntegrityError(RuntimeError):
    """Stored state, artifact, or audit data does not match its exact identity."""


def assert_managed_path(root: Path, path: Path) -> Path:
    """Reject lexical escape and every existing symlink below a managed root."""

    managed_root = root.resolve()
    candidate = path if path.is_absolute() else managed_root / path
    try:
        relative = candidate.relative_to(managed_root)
    except ValueError as error:
        raise IntegrityError("managed path escapes project root") from error
    cursor = managed_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise IntegrityError(f"managed path contains symlink: {cursor}")
    try:
        candidate.resolve(strict=False).relative_to(managed_root)
    except ValueError as error:
        raise IntegrityError("managed path resolves outside project root") from error
    return candidate


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write_bytes(path: Path, value: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, canonical_json_bytes(value) + b"\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IntegrityError(f"cannot read valid JSON from {path}") from error
    if not isinstance(value, dict):
        raise IntegrityError(f"expected JSON object at {path}")
    return value


def _event_hash(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return sha256_bytes(canonical_json_bytes(payload))


def _validate_audit_event(event: dict[str, Any]) -> None:
    """Execute the exact packaged Audit Event schema in source and installed layouts."""

    from .schema_runtime import SchemaRuntime, SchemaValidationError

    module = Path(__file__).resolve()
    source_root = module.parents[1] / "core"
    skill_root = source_root if (source_root / "schemas").is_dir() else module.parents[2]
    try:
        SchemaRuntime(skill_root).validate("audit-event.schema.json", event)
    except SchemaValidationError as error:
        raise IntegrityError(f"audit event schema violation: {error}") from error
    require_iso_datetime(event.get("recorded_at"), "audit event recorded_at")


def require_iso_datetime(value: Any, label: str) -> datetime:
    """Require a timezone-aware ISO-8601 timestamp without external libraries."""

    if not isinstance(value, str):
        raise IntegrityError(f"{label} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise IntegrityError(f"{label} must be a valid ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise IntegrityError(f"{label} must include a timezone")
    return parsed


def append_event(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    lock_path = path.with_name(f".{path.name}.lock")
    with exclusive_file_lock(lock_path):
        events = verify_event_chain(path) if path.exists() else []
        requested_id = event.get("event_id")
        if requested_id is not None:
            matches = [item for item in events if item.get("event_id") == requested_id]
            if matches:
                existing = matches[0]
                if len(matches) != 1 or any(existing.get(key) != value for key, value in event.items()):
                    raise IntegrityError(f"event identity conflict: {requested_id}")
                return existing
        previous = events[-1]["event_hash"] if events else None
        complete = {
            "schema_version": "audit-event.v1",
            "event_id": event.get("event_id", str(uuid4())),
            "recorded_at": event.get("recorded_at", datetime.now(UTC).isoformat()),
            "previous_hash": previous,
            **event,
        }
        complete["event_hash"] = _event_hash(complete)
        _validate_audit_event(complete)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab") as handle:
            handle.write(canonical_json_bytes(complete) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        return complete


def verify_event_chain(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    previous: str | None = None
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise IntegrityError(f"invalid event JSON at line {index}") from error
        if not isinstance(event, dict):
            raise IntegrityError(f"event line {index} is not an object")
        _validate_audit_event(event)
        if event.get("previous_hash") != previous:
            raise IntegrityError(f"event hash chain mismatch at line {index}")
        if event.get("event_hash") != _event_hash(event):
            raise IntegrityError(f"event hash mismatch at line {index}")
        previous = event["event_hash"]
        events.append(event)
    return events
