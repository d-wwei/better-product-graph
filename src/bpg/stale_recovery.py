"""Exact allowlisted recovery contracts for durable legacy BPG Runs."""

from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from .storage import (
    IntegrityError,
    assert_managed_path,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_event_chain,
)


class StaleRecoveryError(ValueError):
    """A stale Run does not match one exact, safe recovery contract."""


REGISTRY_SCHEMA = "stale-run-recovery-registry.v1"
RECOVERY_STATUSES = frozenset({"ACTIVE", "PAUSED"})
RECOVERABLE_ATTEMPT_STATUSES = frozenset({"PLANNED", "DISPATCHED"})
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_OID_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _normalized_recovery_value(value: Any, replacements: list[tuple[str, str]]) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalized_recovery_value(item, replacements)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalized_recovery_value(item, replacements) for item in value]
    if isinstance(value, str):
        normalized = value
        for original, replacement in replacements:
            normalized = normalized.replace(original, replacement)
        return normalized
    return value


def _path_fact(path: Path, relative_to: Path) -> dict[str, Any]:
    relative = path.relative_to(relative_to).as_posix()
    if path.is_symlink():
        return {"path": relative, "kind": "SYMLINK"}
    if path.is_file():
        return {"path": relative, "kind": "REGULAR", "hash": sha256_file(path)}
    return {"path": relative, "kind": "OTHER"}


def recovery_match_payload(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Return a Run-id-independent exact legacy-state and authority snapshot."""

    project_root = project_root.resolve()
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise StaleRecoveryError("legacy Run has no stable run_id")
    attempts = state.get("dispatch_attempts")
    if not isinstance(attempts, list):
        raise StaleRecoveryError("legacy Run has no dispatch attempt ledger")
    attempt_ids = [
        item.get("attempt_id")
        for item in attempts
        if isinstance(item, dict) and isinstance(item.get("attempt_id"), str)
    ]
    if len(attempt_ids) != len(attempts) or len(attempt_ids) != len(set(attempt_ids)):
        raise StaleRecoveryError("legacy dispatch attempt identities are ambiguous")
    replacements = [(run_id, "$RUN_ID")]
    replacements.extend(
        (attempt_id, f"$ATTEMPT_{index:03d}")
        for index, attempt_id in enumerate(attempt_ids, start=1)
    )
    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)

    normalized_state_source = deepcopy(state)
    run_root = assert_managed_path(
        project_root,
        project_root / ".better-product-graph" / "runs" / run_id,
    )
    transaction_root = assert_managed_path(
        project_root, run_root / "transactions"
    )
    historical_states: dict[int, dict[str, Any]] = {}
    if transaction_root.is_dir() and not transaction_root.is_symlink():
        for journal_path in sorted(transaction_root.glob("*.json")):
            if not journal_path.is_file() or journal_path.is_symlink():
                raise StaleRecoveryError("legacy transaction journal is unsafe")
            journal = read_json(journal_path)
            after_state = journal.get("after_state")
            version = after_state.get("state_version") if isinstance(after_state, dict) else None
            if (
                journal.get("status") != "COMMITTED"
                or not isinstance(version, int)
                or sha256_bytes(canonical_json_bytes(after_state))
                != journal.get("after_state_hash")
                or version in historical_states
            ):
                raise StaleRecoveryError("legacy transaction history is ambiguous")
            historical_states[version] = after_state

    for attempt in normalized_state_source["dispatch_attempts"]:
        authority_version = attempt.get("authorized_state_version")
        if not isinstance(authority_version, int):
            authority_version = attempt.get("state_version")
        authority_state = historical_states.get(authority_version)
        if not isinstance(authority_state, dict):
            raise StaleRecoveryError("legacy dispatch authority state is unavailable")
        authority_payload = {
            "run_id": authority_state["run_id"],
            "state_version": authority_state["state_version"],
            "status": authority_state["status"],
            "current_node": authority_state["current_node"],
            "artifact_refs": authority_state.get("artifact_refs", {}),
            "current_candidate_ref": authority_state.get("current_candidate_ref"),
            "interaction_policy": authority_state.get("interaction_policy"),
            "waiting": authority_state.get("waiting"),
            "release_ref": authority_state.get("release_ref"),
        }
        if sha256_bytes(canonical_json_bytes(authority_payload)) != attempt.get(
            "authority_hash"
        ):
            raise StaleRecoveryError("legacy dispatch authority hash is invalid")
        normalized_authority = _normalized_recovery_value(
            authority_payload, replacements
        )
        attempt["authority_hash"] = {
            "status": "VALIDATED_HISTORICAL_AUTHORITY",
            "normalized_payload_hash": sha256_bytes(
                canonical_json_bytes(normalized_authority)
            ),
        }

    authority_files: list[dict[str, Any]] = []
    for attempt_id in attempt_ids:
        attempt_root = assert_managed_path(
            project_root, run_root / "attempts" / attempt_id
        )
        if not attempt_root.exists():
            continue
        for path in sorted(attempt_root.rglob("*")):
            if path.is_file() or path.is_symlink():
                fact = _path_fact(path, project_root)
                authority_files.append(
                    _normalized_recovery_value(fact, replacements)
                )
    for receipt in state.get("ready_receipts", []):
        if not isinstance(receipt, dict) or not isinstance(receipt.get("path"), str):
            continue
        path = assert_managed_path(project_root, project_root / receipt["path"])
        if path.exists() or path.is_symlink():
            authority_files.append(
                _normalized_recovery_value(_path_fact(path, project_root), replacements)
            )

    events = verify_event_chain(run_root / "events.jsonl")
    semantic_events = []
    for event in events:
        semantic = {
            key: value
            for key, value in event.items()
            if key
            not in {
                "event_hash",
                "previous_hash",
                "recorded_at",
                "before_state_hash",
                "after_state_hash",
            }
        }
        semantic_events.append(_normalized_recovery_value(semantic, replacements))
    normalized_state = _normalized_recovery_value(
        normalized_state_source, replacements
    )
    return {
        "schema_version": "stale-run-recovery-match.v1",
        "state": normalized_state,
        "authority_files": sorted(
            authority_files,
            key=lambda item: (item["path"], item["kind"]),
        ),
        "event_count": len(events),
        "event_semantic_hash": sha256_bytes(canonical_json_bytes(semantic_events)),
        "event_tip": semantic_events[-1] if semantic_events else None,
    }


def recovery_match_fingerprint(project_root: Path, state: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(recovery_match_payload(project_root, state)))


def _resolve_registry_path(
    skill_root: Path, graph: dict[str, Any], graph_path: Path
) -> Path | None:
    ref = graph.get("stale_recovery_contracts_ref")
    if ref is None:
        return None
    if not isinstance(ref, dict):
        raise StaleRecoveryError("stale recovery registry ref must be an object")
    if set(ref) != {"path", "schema_version", "hash"}:
        raise StaleRecoveryError("stale recovery registry ref is not closed-world")
    if ref.get("schema_version") != REGISTRY_SCHEMA:
        raise StaleRecoveryError("stale recovery registry schema is unsupported")
    expected_hash = ref.get("hash")
    if not isinstance(expected_hash, str) or not SHA256_PATTERN.fullmatch(expected_hash):
        raise StaleRecoveryError("stale recovery registry hash is invalid")
    relative = Path(str(ref.get("path", "")))
    candidate = assert_managed_path(skill_root, skill_root / relative)
    if not candidate.is_file() and relative.parts[:1] == ("references",):
        candidate = assert_managed_path(
            skill_root, skill_root / Path(*relative.parts[1:])
        )
    if not candidate.is_file() or candidate.is_symlink():
        raise StaleRecoveryError("stale recovery registry is missing or unsafe")
    if sha256_file(candidate) != expected_hash:
        raise StaleRecoveryError("stale recovery registry hash changed")
    return candidate


def load_stale_recovery_contracts(
    skill_root: Path, graph: dict[str, Any], graph_path: Path
) -> list[dict[str, Any]]:
    path = _resolve_registry_path(skill_root.resolve(), graph, graph_path.resolve())
    if path is None:
        return []
    registry = read_json(path)
    if set(registry) != {"schema_version", "contracts"}:
        raise StaleRecoveryError("stale recovery registry is not closed-world")
    if registry.get("schema_version") != REGISTRY_SCHEMA:
        raise StaleRecoveryError("stale recovery registry schema is unsupported")
    contracts = registry.get("contracts")
    if not isinstance(contracts, list):
        raise StaleRecoveryError("stale recovery contracts must be a list")
    identities: set[str] = set()
    for contract in contracts:
        if not isinstance(contract, dict):
            raise StaleRecoveryError("stale recovery contract must be an object")
        required = {
            "recovery_id",
            "from_graph",
            "status",
            "current_node",
            "state_fingerprint",
            "retire_dispatches",
            "resume_node",
            "resume_last_completed_node",
            "clear_ready_receipts",
            "git_restore",
            "message_zh",
        }
        if set(contract) != required:
            raise StaleRecoveryError("stale recovery contract is not closed-world")
        recovery_id = contract.get("recovery_id")
        if not isinstance(recovery_id, str) or not recovery_id or recovery_id in identities:
            raise StaleRecoveryError("stale recovery identity is missing or duplicated")
        identities.add(recovery_id)
        graph_ref = contract.get("from_graph")
        if (
            not isinstance(graph_ref, dict)
            or set(graph_ref) != {"version", "hash"}
            or not isinstance(graph_ref.get("version"), str)
            or not SHA256_PATTERN.fullmatch(str(graph_ref.get("hash", "")))
        ):
            raise StaleRecoveryError(f"invalid from_graph for {recovery_id}")
        if contract.get("status") not in RECOVERY_STATUSES:
            raise StaleRecoveryError(f"invalid legacy status for {recovery_id}")
        for field in ("current_node", "resume_node", "message_zh"):
            if not isinstance(contract.get(field), str) or not contract[field]:
                raise StaleRecoveryError(f"invalid {field} for {recovery_id}")
        if contract.get("resume_last_completed_node") is not None and not isinstance(
            contract.get("resume_last_completed_node"), str
        ):
            raise StaleRecoveryError(
                f"invalid resume_last_completed_node for {recovery_id}"
            )
        if not SHA256_PATTERN.fullmatch(str(contract.get("state_fingerprint", ""))):
            raise StaleRecoveryError(f"invalid state fingerprint for {recovery_id}")
        if not isinstance(contract.get("clear_ready_receipts"), bool):
            raise StaleRecoveryError(f"invalid Ready reset flag for {recovery_id}")
        retire = contract.get("retire_dispatches")
        if not isinstance(retire, list) or not retire:
            raise StaleRecoveryError(f"retirement list is empty for {recovery_id}")
        for item in retire:
            if (
                not isinstance(item, dict)
                or set(item)
                != {
                    "node_id",
                    "instruction_hash",
                    "status",
                    "count",
                    "result_authority",
                }
                or item.get("status") not in RECOVERABLE_ATTEMPT_STATUSES
                or item.get("result_authority") != "ABSENT"
                or isinstance(item.get("count"), bool)
                or not isinstance(item.get("count"), int)
                or item["count"] < 1
                or not isinstance(item.get("node_id"), str)
                or not SHA256_PATTERN.fullmatch(str(item.get("instruction_hash", "")))
            ):
                raise StaleRecoveryError(f"invalid retirement contract for {recovery_id}")
        restore = contract.get("git_restore")
        if restore is not None:
            _validate_git_restore_contract(restore, recovery_id)
    return contracts


def find_stale_recovery_contract(
    project_root: Path,
    state: dict[str, Any],
    contracts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    fingerprint = recovery_match_fingerprint(project_root, state)
    matches = [
        contract
        for contract in contracts
        if contract["from_graph"] == state.get("graph_manifest")
        and contract["status"] == state.get("status")
        and contract["current_node"] == state.get("current_node")
        and contract["state_fingerprint"] == fingerprint
    ]
    if len(matches) > 1:
        raise StaleRecoveryError("legacy Run matches multiple recovery contracts")
    return deepcopy(matches[0]) if matches else None


def _validate_git_restore_contract(restore: Any, recovery_id: str) -> None:
    if (
        not isinstance(restore, dict)
        or set(restore) != {"commit", "tree_hash", "files"}
        or not GIT_OID_PATTERN.fullmatch(str(restore.get("commit", "")))
        or not SHA256_PATTERN.fullmatch(str(restore.get("tree_hash", "")))
        or not isinstance(restore.get("files"), list)
        or not restore["files"]
    ):
        raise StaleRecoveryError(f"invalid Git restoration for {recovery_id}")
    seen: set[str] = set()
    for item in restore["files"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "hash", "git_blob_oid", "mode"}
            or not isinstance(item.get("path"), str)
            or not item["path"]
            or item["path"] in seen
            or not SHA256_PATTERN.fullmatch(str(item.get("hash", "")))
            or not GIT_OID_PATTERN.fullmatch(str(item.get("git_blob_oid", "")))
            or item.get("mode") not in {"100644", "100755"}
        ):
            raise StaleRecoveryError(f"invalid Git restoration file for {recovery_id}")
        seen.add(item["path"])


def prepare_git_restoration(
    project_root: Path, restore: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Read and verify every exact Git blob before allowing any project write."""

    if restore is None:
        return []
    project_root = project_root.resolve()
    commit = restore["commit"]
    try:
        resolved = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--verify", f"{commit}^{{commit}}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.decode().strip()
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as error:
        raise StaleRecoveryError("exact Git restoration commit is unavailable") from error
    if resolved != commit:
        raise StaleRecoveryError("exact Git restoration commit identity changed")

    roots = {str(Path(item["path"]).parent) for item in restore["files"]}
    if len(roots) != 1:
        raise StaleRecoveryError("Git restoration files must share one artifact root")
    artifact_root = next(iter(roots))
    try:
        raw_tree = subprocess.run(
            ["git", "-C", str(project_root), "ls-tree", "-r", "-z", commit, "--", artifact_root],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        records = [item for item in raw_tree.split(b"\0") if item]
        tree_entries: dict[str, tuple[str, str]] = {}
        for record in records:
            header, encoded_path = record.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split(" ", 2)
            path = encoded_path.decode("utf-8")
            if kind != "blob" or path in tree_entries:
                raise StaleRecoveryError("Git restoration tree is not a closed blob set")
            tree_entries[path] = (mode, oid)
    except StaleRecoveryError:
        raise
    except (
        OSError,
        subprocess.CalledProcessError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        raise StaleRecoveryError("exact Git restoration tree is unavailable") from error
    expected_paths = {item["path"] for item in restore["files"]}
    if set(tree_entries) != expected_paths:
        raise StaleRecoveryError("Git restoration inventory differs from exact commit tree")

    prepared: list[dict[str, Any]] = []
    for item in restore["files"]:
        target = assert_managed_path(project_root, project_root / item["path"])
        if target.exists() or target.is_symlink():
            raise StaleRecoveryError(
                f"Git restoration target is not missing: {item['path']}"
            )
        try:
            content = subprocess.run(
                ["git", "-C", str(project_root), "cat-file", "blob", item["git_blob_oid"]],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as error:
            raise StaleRecoveryError(
                f"Git restoration blob is unavailable: {item['path']}"
            ) from error
        if (
            tree_entries[item["path"]]
            != (item["mode"], item["git_blob_oid"])
            or sha256_bytes(content) != item["hash"]
        ):
            raise StaleRecoveryError(
                f"Git restoration blob identity changed: {item['path']}"
            )
        prepared.append({**item, "content": content})
    return prepared


def validate_restored_tree(project_root: Path, restore: dict[str, Any] | None) -> None:
    if restore is None:
        return
    from .documents import hash_tree

    roots = {str(Path(item["path"]).parent) for item in restore["files"]}
    if len(roots) != 1:
        raise StaleRecoveryError("Git restoration files must share one exact artifact root")
    root = assert_managed_path(project_root, project_root / next(iter(roots)))
    if not root.is_dir() or root.is_symlink() or hash_tree(root) != restore["tree_hash"]:
        raise StaleRecoveryError("restored Git artifact tree hash changed")
