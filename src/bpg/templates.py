"""Exact Template Profile resolution, explicit pinning, and rollback."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .storage import atomic_write_json, read_json, sha256_file


class TemplateContractError(ValueError):
    """A Template Profile is missing, changed, or would migrate silently."""


@dataclass(frozen=True)
class TemplateSelection:
    profile_id: str
    version: str
    status: str
    path: Path
    sha256: str
    relative_path: str

    def pin_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        return payload


class TemplateRegistry:
    def __init__(self, templates_root: Path):
        self.templates_root = templates_root.resolve()
        self.registry = read_json(self.templates_root / "profiles.json")

    def _config_path(self, project_root: Path) -> Path:
        return project_root.resolve() / ".better-product-graph" / "template-profile.json"

    def _find(self, profile_id: str, version: str) -> TemplateSelection:
        matches = [
            item
            for item in self.registry.get("profiles", [])
            if item.get("id") == profile_id and item.get("version") == version
        ]
        if len(matches) != 1:
            raise TemplateContractError(f"Template Profile not found exactly once: {profile_id}@{version}")
        item = matches[0]
        path = (self.templates_root / item["path"]).resolve()
        try:
            path.relative_to(self.templates_root)
        except ValueError as error:
            raise TemplateContractError("Template path escapes registry root") from error
        actual_hash = sha256_file(path) if path.is_file() else None
        if actual_hash != item.get("sha256"):
            raise TemplateContractError(
                f"Template hash mismatch for {profile_id}@{version}: {actual_hash}"
            )
        return TemplateSelection(profile_id, version, item["status"], path, actual_hash, item["path"])

    def resolve(self, project_root: Path) -> TemplateSelection:
        config_path = self._config_path(project_root)
        if config_path.exists():
            config = read_json(config_path)
            active = config.get("active", {})
            selection = self._find(active.get("profile_id"), active.get("version"))
            if selection.sha256 != active.get("sha256"):
                raise TemplateContractError("Pinned Template hash no longer matches registry")
            return selection
        default = self.registry.get("default_profile", {})
        return self._find(default.get("id"), default.get("version"))

    def pin(self, project_root: Path, profile_id: str, version: str) -> TemplateSelection:
        selection = self._find(profile_id, version)
        config_path = self._config_path(project_root)
        history: list[dict[str, Any]] = []
        if config_path.exists():
            existing = read_json(config_path)
            history = list(existing.get("history", []))
        active = {
            "profile_id": selection.profile_id,
            "version": selection.version,
            "sha256": selection.sha256,
        }
        history.append(active)
        atomic_write_json(
            config_path,
            {
                "schema_version": "template-profile-pin.v1",
                "active": active,
                "history": history,
                "migration_policy": "EXPLICIT_ONLY",
            },
        )
        return selection

    def rollback(self, project_root: Path, target_hash: str) -> TemplateSelection:
        config_path = self._config_path(project_root)
        if not config_path.exists():
            raise TemplateContractError("No Template pin history exists")
        config = read_json(config_path)
        targets = [item for item in config.get("history", []) if item.get("sha256") == target_hash]
        if not targets:
            raise TemplateContractError("Rollback target hash is not in project pin history")
        target = targets[-1]
        return self.pin(project_root, target["profile_id"], target["version"])
