"""Installed-copy identity verification with no source-checkout dependency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HOST_MANIFEST_DIRS = {"codex": ".codex-plugin", "claude": ".claude-plugin"}


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _inventory(plugin_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(plugin_root.rglob("*")):
        relative = path.relative_to(plugin_root)
        if path.is_symlink():
            raise ValueError(f"installed symlink is forbidden: {relative.as_posix()}")
        if "__pycache__" in relative.parts and path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_file() and path.name != "build-manifest.json":
            content = path.read_bytes()
            entries.append(
                {"path": relative.as_posix(), "sha256": _sha256_bytes(content), "size": len(content)}
            )
    return entries


def verify_installed_identity(plugin_root: Path) -> dict[str, Any]:
    root = plugin_root.resolve()
    manifest_path = root / "build-manifest.json"
    if not manifest_path.is_file():
        return {"valid": False, "errors": ["build-manifest.json missing"], "artifact_hash": None}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        inventory = _inventory(root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return {"valid": False, "errors": [str(error)], "artifact_hash": None}
    artifact_hash = _sha256_bytes(_canonical_json(inventory))
    errors: list[str] = []
    if inventory != manifest.get("inventory"):
        errors.append("installed inventory differs from build manifest")
    if artifact_hash != manifest.get("artifact_hash"):
        errors.append("installed artifact hash mismatch")
    host = manifest.get("host")
    plugin = manifest.get("plugin")
    if not isinstance(host, dict):
        errors.append("build manifest host binding is missing")
    else:
        host_id = host.get("host_id")
        manifest_dir = host.get("manifest_dir")
        expected_dir = HOST_MANIFEST_DIRS.get(host_id) if isinstance(host_id, str) else None
        if expected_dir is None or manifest_dir != expected_dir:
            errors.append("build manifest host binding is invalid")
        found = [
            candidate
            for candidate, directory in HOST_MANIFEST_DIRS.items()
            if (root / directory / "plugin.json").is_file()
        ]
        if found != [host_id]:
            errors.append(
                "installed host manifest does not match build manifest: " + str(found)
            )
        elif isinstance(plugin, dict):
            try:
                host_manifest = json.loads(
                    (root / expected_dir / "plugin.json").read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"installed host manifest is invalid: {error}")
            else:
                if not isinstance(host_manifest, dict):
                    errors.append("installed host manifest is not a JSON object")
                elif (
                    host_manifest.get("name") != plugin.get("name")
                    or host_manifest.get("version") != plugin.get("version")
                ):
                    errors.append("installed host manifest plugin identity mismatch")
        else:
            errors.append("build manifest plugin binding is missing")
    return {"valid": not errors, "errors": errors, "artifact_hash": artifact_hash}
