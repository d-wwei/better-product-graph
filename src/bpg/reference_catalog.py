"""Exact, non-discoverable Agent reference catalog resolution."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .storage import read_json, sha256_file


class ReferenceCatalogError(ValueError):
    """An installed or source reference catalog is incomplete or has drifted."""


class ReferenceCatalog:
    def __init__(self, skill_root: Path):
        self.skill_root = skill_root.resolve()
        catalog_path = self._catalog_path()
        try:
            catalog = read_json(catalog_path)
        except Exception as error:
            raise ReferenceCatalogError(f"reference catalog missing or invalid: {catalog_path}") from error
        if (
            catalog.get("schema_version") != "internal-reference-catalog.v1"
            or catalog.get("discoverable") is not False
        ):
            raise ReferenceCatalogError("reference catalog must be versioned and non-discoverable")
        extraction_ref = catalog.get("extraction_manifest")
        if not isinstance(extraction_ref, dict) or not extraction_ref.get("path") or not extraction_ref.get("hash"):
            raise ReferenceCatalogError("reference extraction manifest is required")
        extraction_path = self.resolve(extraction_ref["path"])
        if sha256_file(extraction_path) != extraction_ref["hash"]:
            raise ReferenceCatalogError("reference extraction manifest hash mismatch")
        self.extraction_manifest = read_json(extraction_path)
        self.core_reasoning = self._category(catalog, "core_reasoning")
        self.cognitive_bases = self._category(catalog, "cognitive_bases")
        self.reviewer_profiles = self._category(catalog, "reviewer_profiles")
        resources = self.core_reasoning + self.cognitive_bases + self.reviewer_profiles
        ids = [item["resource_id"] for item in resources]
        if len(ids) != len(set(ids)):
            raise ReferenceCatalogError("reference resource IDs must be unique")
        if {item["resource_id"] for item in self.core_reasoning} != {
            "better-question",
            "cognitive-router",
            "cognitive-base-catalog",
        }:
            raise ReferenceCatalogError("core reasoning reference set is incomplete")
        if len(self.cognitive_bases) != 20:
            raise ReferenceCatalogError("exactly 20 cognitive bases are required")
        if {item["resource_id"] for item in self.reviewer_profiles} != {
            "goal-fidelity-profile",
            "goal-fidelity-rubric",
            "goal-fidelity-packet-contract",
        }:
            raise ReferenceCatalogError("Goal Fidelity reviewer reference set is incomplete")
        self._validate_cognitive_base_selectors()
        self._validate_extraction_manifest()

    def _catalog_path(self) -> Path:
        installed = self.skill_root / "references" / "reasoning-catalog" / "reference-catalog-v0.1.json"
        source = self.skill_root / "reasoning-catalog" / "reference-catalog-v0.1.json"
        if installed.is_file() and not installed.is_symlink():
            return installed
        if source.is_file() and not source.is_symlink():
            return source
        raise ReferenceCatalogError("reference catalog missing")

    def _category(self, catalog: dict[str, Any], name: str) -> list[dict[str, Any]]:
        entries = catalog.get(name)
        if not isinstance(entries, list) or not entries:
            raise ReferenceCatalogError(f"reference catalog category missing: {name}")
        validated: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict) or any(
                not entry.get(field) for field in ("resource_id", "kind", "version", "path", "hash")
            ):
                raise ReferenceCatalogError(f"invalid reference entry in {name}")
            if "SKILL.md" in entry["path"]:
                raise ReferenceCatalogError("internal references must not be discoverable Skills")
            resolved = self.resolve(entry["path"])
            if sha256_file(resolved) != entry["hash"]:
                raise ReferenceCatalogError(f"reference hash mismatch: {entry['resource_id']}")
            validated.append(deepcopy(entry))
        return validated

    def resolve(self, relative_path: str) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ReferenceCatalogError(f"reference path escapes skill root: {relative_path}")
        candidates = [self.skill_root / relative]
        if relative.parts[:1] == ("references",):
            candidates.append(self.skill_root / Path(*relative.parts[1:]))
        for candidate in candidates:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(self.skill_root)
            except ValueError:
                continue
            if candidate.is_file() and not candidate.is_symlink():
                return resolved
        raise ReferenceCatalogError(f"reference missing: {relative_path}")

    def _validate_cognitive_base_selectors(self) -> None:
        catalog_ref = next(
            item for item in self.core_reasoning if item["resource_id"] == "cognitive-base-catalog"
        )
        catalog = read_json(self.resolve(catalog_ref["path"]))
        available = {
            item.get("id") for item in catalog.get("bases", []) if isinstance(item, dict)
        }
        selected = {item.get("selector") for item in self.cognitive_bases}
        if None in selected or selected != available:
            raise ReferenceCatalogError("cognitive base selectors do not match the catalog")

    def _validate_extraction_manifest(self) -> None:
        entries = self.extraction_manifest.get("entries")
        if (
            self.extraction_manifest.get("schema_version") != "reference-extraction-manifest.v1"
            or self.extraction_manifest.get("source_root_id") != "upstream:cognitive-bases"
            or not isinstance(entries, list)
            or len(entries) != 20
        ):
            raise ReferenceCatalogError("reference extraction manifest is invalid")
        declared = {
            item.get("resource_id"): item.get("source_sha256")
            for item in entries
            if isinstance(item, dict)
            and isinstance(item.get("source_relative_path"), str)
            and ".." not in Path(item["source_relative_path"]).parts
        }
        catalog_ref = next(
            item for item in self.core_reasoning if item["resource_id"] == "cognitive-base-catalog"
        )
        cognitive = read_json(self.resolve(catalog_ref["path"]))
        extracted = {
            item.get("id"): item.get("source_sha256")
            for item in cognitive.get("bases", [])
            if isinstance(item, dict)
        }
        if len(declared) != 20 or declared != extracted:
            raise ReferenceCatalogError("reference extraction provenance differs from catalog")

    def core_reasoning_resources(self) -> list[dict[str, Any]]:
        return deepcopy(self.core_reasoning)

    def learning_resources(self) -> list[dict[str, Any]]:
        return deepcopy(self.core_reasoning + self.cognitive_bases)

    def review_resources(self) -> list[dict[str, Any]]:
        return deepcopy(self.reviewer_profiles)

    def all_resource_refs(self) -> list[dict[str, Any]]:
        return deepcopy(self.core_reasoning + self.cognitive_bases + self.reviewer_profiles)
