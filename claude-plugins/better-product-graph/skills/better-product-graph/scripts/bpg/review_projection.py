"""Mechanical authority checks for isolated ordinary-review work orders."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .storage import canonical_json_bytes


class ReviewProjectionError(ValueError):
    """A reviewer identity or output custody boundary is ambiguous."""


_SAFE_EXECUTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")


def _execution_key(value: Any, label: str) -> tuple[str, str]:
    if not isinstance(value, dict) or set(value) != {"kind", "id"}:
        raise ReviewProjectionError(f"{label} must be one closed execution ref")
    kind = value.get("kind")
    identifier = value.get("id")
    if (
        not isinstance(kind, str)
        or not kind
        or not isinstance(identifier, str)
        or _SAFE_EXECUTION_ID.fullmatch(identifier) is None
    ):
        raise ReviewProjectionError(f"{label} is invalid")
    return kind, identifier


def _output_key(root: Path, value: Any, label: str) -> tuple[str, str]:
    if not isinstance(value, dict) or set(value) != {"path", "absolute_path"}:
        raise ReviewProjectionError(f"{label} must contain exact path and absolute target")
    raw_path = value.get("path")
    absolute_path = value.get("absolute_path")
    if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
        raise ReviewProjectionError(f"{label} must stay inside projection root")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ReviewProjectionError(f"{label} must stay inside projection root")
    if not isinstance(absolute_path, str) or not Path(absolute_path).is_absolute():
        raise ReviewProjectionError(f"{label} requires an absolute target")
    lexical = root.joinpath(*relative.parts)
    try:
        resolved_parent = lexical.parent.resolve()
        resolved_parent.relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise ReviewProjectionError(f"{label} must stay inside projection root") from error
    expected_absolute = (resolved_parent / lexical.name).absolute()
    if Path(absolute_path).absolute() != expected_absolute:
        raise ReviewProjectionError(f"{label} absolute target differs from its exact path")
    if lexical.exists() or lexical.is_symlink():
        raise ReviewProjectionError(f"{label} must not exist before reviewer dispatch")
    return relative.as_posix(), str(expected_absolute)


def validate_reviewer_work_orders(
    projection_root: Path,
    work_orders: Any,
    *,
    expected_roles: list[str],
    author_execution_ref: dict[str, Any],
    forbidden_execution_refs: Iterable[dict[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Validate distinct workers and write targets before any semantic dispatch."""

    root = projection_root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise ReviewProjectionError("projection root must be a regular non-symlink directory")
    if (
        not isinstance(expected_roles, list)
        or not expected_roles
        or len(expected_roles) != len(set(expected_roles))
        or any(not isinstance(role, str) or not role for role in expected_roles)
    ):
        raise ReviewProjectionError("expected roles must be a non-empty unique list")
    if not isinstance(work_orders, list) or len(work_orders) != len(expected_roles):
        raise ReviewProjectionError("work orders must cover every expected role exactly once")
    roles = [item.get("reviewer_role") if isinstance(item, dict) else None for item in work_orders]
    if roles != expected_roles:
        raise ReviewProjectionError("work orders must cover every expected role exactly once")

    author = _execution_key(author_execution_ref, "author execution")
    forbidden = {
        _execution_key(item, "forbidden execution")
        for item in forbidden_execution_refs
    }
    forbidden_ids = {identifier for _, identifier in forbidden}
    execution_keys: list[tuple[str, str]] = []
    output_keys: list[tuple[str, str]] = []
    for index, work_order in enumerate(work_orders):
        if not isinstance(work_order, dict):
            raise ReviewProjectionError(f"work_orders[{index}] must be an object")
        execution = _execution_key(
            work_order.get("reviewer_execution_ref"),
            f"work_orders[{index}].reviewer_execution_ref",
        )
        if execution[1] == author[1]:
            raise ReviewProjectionError("reviewer execution overlaps author execution")
        if execution[1] in forbidden_ids:
            raise ReviewProjectionError("reviewer execution overlaps forbidden execution")
        if execution[0] != "HOST_SUBAGENT_ATTEMPT":
            raise ReviewProjectionError(
                "reviewer execution kind must be HOST_SUBAGENT_ATTEMPT"
            )
        execution_keys.append(execution)
        output_keys.append(
            _output_key(
                root,
                work_order.get("output_target"),
                f"work_orders[{index}].output_target",
            )
        )
    if len(execution_keys) != len(set(execution_keys)):
        raise ReviewProjectionError("work orders require unique reviewer_execution_ref values")
    if len(output_keys) != len(set(output_keys)):
        raise ReviewProjectionError("work orders require unique output_target values")
    return json.loads(canonical_json_bytes(work_orders))
