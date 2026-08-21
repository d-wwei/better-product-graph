"""Null and local-only connector seams; no remote side effects in this release."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .storage import atomic_write_json, canonical_json_bytes, read_json, sha256_file


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class NullConnector:
    def __init__(self, name: str):
        self.name = name

    def status(self) -> dict[str, Any]:
        return {"connector": self.name, "status": "NOT_CONFIGURED", "capability": "NONE"}

    def dispatch(self, packet: dict[str, Any]) -> dict[str, Any]:
        return {
            "connector": self.name,
            "packet_id": packet.get("id"),
            "status": "NOT_AVAILABLE",
            "sent": False,
            "receipt": None,
        }


class LocalHandoffConnector:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def status(self) -> dict[str, Any]:
        return {"connector": "local-handoff", "status": "AVAILABLE", "capability": "LOCAL_WRITE"}

    def dispatch(self, packet: dict[str, Any]) -> dict[str, Any]:
        packet_id = packet.get("id")
        if not isinstance(packet_id, str) or SAFE_ID.fullmatch(packet_id) is None:
            raise ValueError("local handoff packet requires a path-safe id")
        path = self.project_root / ".better-product-graph" / "handoffs" / "local" / f"{packet_id}.json"
        if path.exists():
            if path.is_symlink() or canonical_json_bytes(read_json(path)) != canonical_json_bytes(packet):
                raise FileExistsError(f"local handoff identity conflict: {packet_id}")
            return {
                "connector": "local-handoff",
                "packet_id": packet_id,
                "status": "EXISTING_LOCAL",
                "sent_remote": False,
                "receipt": {
                    "path": path.relative_to(self.project_root).as_posix(),
                    "hash": sha256_file(path),
                },
            }
        atomic_write_json(path, packet)
        return {
            "connector": "local-handoff",
            "packet_id": packet_id,
            "status": "WRITTEN_LOCAL",
            "sent_remote": False,
            "receipt": {
                "path": path.relative_to(self.project_root).as_posix(),
                "hash": sha256_file(path),
            },
        }
