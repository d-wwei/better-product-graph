"""Exact built-in/project Template resolution, explicit pinning, and rollback."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from .locking import exclusive_file_lock
from .storage import (
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
)


class TemplateContractError(ValueError):
    """A Template Profile is invalid, changed, ambiguous, or would migrate silently."""


RELEASE_DEFAULT = ("general", "0.2.0")
RELEASE_DEFAULT_STATUS = "RELEASED_DEFAULT"
FALLBACK_REASONS = {
    "PROJECT_TEMPLATE_UNAVAILABLE",
    "PROJECT_TEMPLATE_NOT_APPLICABLE",
}
BUILTIN_SELECTION_SOURCES = {
    "BUILTIN_EXPLICIT_PIN",
    "REGISTRY_DEFAULT_PIN",
    "REGISTRY_DEFAULT_UNPINNED",
    "BPG_GENERAL_DEFAULT",
}
PROJECT_ACTIVE_FIELDS = {
    "kind",
    "profile_id",
    "version",
    "template_path",
    "template_sha256",
    "output_contract_path",
    "output_contract_sha256",
    "output_contract_version",
    "fallback_policy",
    "applicable",
}


def _is_exact_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )


@dataclass(frozen=True)
class TemplateSelection:
    profile_id: str
    version: str
    status: str
    path: Path
    sha256: str
    relative_path: str
    output_contract_path: Path
    output_contract_sha256: str
    output_contract_version: str
    output_contract_relative_path: str
    origin: str = "BUILTIN"
    selection_source: str = "BUILTIN_EXPLICIT_PIN"
    fallback_reason: str | None = None
    requested_profile_id: str | None = None
    requested_version: str | None = None

    @property
    def reference_path(self) -> str:
        if self.origin == "BUILTIN":
            return f"references/templates/{self.relative_path}"
        return self.relative_path

    @property
    def output_contract_reference_path(self) -> str:
        if self.origin == "BUILTIN":
            return f"references/templates/{self.output_contract_relative_path}"
        return self.output_contract_relative_path

    def pin_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        payload["output_contract_path"] = str(self.output_contract_path)
        return payload


def load_output_contract(selection: TemplateSelection) -> dict[str, Any]:
    """Load and revalidate the exact selected output contract."""

    return _validate_output_contract(
        selection.output_contract_path,
        selection.output_contract_sha256,
        selection.output_contract_version,
    )


def _validate_output_contract(path: Path, expected_hash: str, expected_version: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise TemplateContractError("Output contract is missing or is a symlink")
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise TemplateContractError(f"Output contract hash mismatch: {actual_hash}")
    try:
        contract = read_json(path)
    except Exception as error:
        raise TemplateContractError("Output contract JSON is invalid") from error
    modes = contract.get("allowed_structure_modes")
    structures = contract.get("structures")
    common_headings = contract.get("common_required_h2")
    common_semantics = contract.get("common_required_semantics")
    conditional = contract.get("conditional_sections")
    if (
        contract.get("schema_version") != "template-output-contract.v2"
        or contract.get("contract_version") != expected_version
        or not isinstance(modes, list)
        or not modes
        or any(not isinstance(mode, str) or not mode for mode in modes)
        or len(set(modes)) != len(modes)
        or contract.get("default_structure_mode") not in modes
        or not isinstance(structures, dict)
        or set(structures) != set(modes)
        or not isinstance(common_headings, list)
        or any(not isinstance(item, str) or not item for item in common_headings)
        or len(set(common_headings)) != len(common_headings)
        or not isinstance(common_semantics, dict)
        or not isinstance(conditional, dict)
        or any(
            not isinstance(heading, str)
            or policy not in {"OMIT_OR_EXPLAIN_NOT_APPLICABLE", "OMIT_WHEN_EMPTY"}
            for heading, policy in conditional.items()
        )
    ):
        raise TemplateContractError("Output contract schema is invalid or ambiguous")
    semantic_groups = [common_semantics]
    for mode in modes:
        shape = structures.get(mode)
        if (
            not isinstance(shape, dict)
            or not isinstance(shape.get("required_h2"), list)
            or not isinstance(shape.get("forbidden_h2"), list)
            or not isinstance(shape.get("required_semantics"), dict)
            or not isinstance(shape.get("h2_order"), list)
            or any(
                not isinstance(heading, str) or not heading
                for heading in [
                    *shape["required_h2"],
                    *shape["forbidden_h2"],
                    *shape["h2_order"],
                ]
            )
            or len(set(shape["h2_order"])) != len(shape["h2_order"])
            or not set(common_headings).issubset(shape["h2_order"])
            or not set(shape["required_h2"]).issubset(shape["h2_order"])
            or set(shape["required_h2"]) & set(shape["forbidden_h2"])
        ):
            raise TemplateContractError("Output contract structure definition is invalid")
        semantic_groups.append(shape["required_semantics"])
    for semantics in semantic_groups:
        for key, headings in semantics.items():
            if (
                not isinstance(key, str)
                or not key
                or not isinstance(headings, list)
                or not headings
                or any(not isinstance(heading, str) or not heading for heading in headings)
            ):
                raise TemplateContractError("Output contract semantic mapping is invalid")
    return contract


class TemplateRegistry:
    def __init__(self, templates_root: Path):
        self.templates_root = templates_root.resolve()
        self.registry = read_json(self.templates_root / "profiles.json")
        if self.registry.get("schema_version") not in {
            "template-profiles.v1",
            "template-profiles.v2",
        }:
            raise TemplateContractError("Template Profile registry schema is unsupported")
        identities = [
            (item.get("id"), item.get("version"))
            for item in self.registry.get("profiles", [])
        ]
        if any(not all(identity) for identity in identities) or len(set(identities)) != len(identities):
            raise TemplateContractError("Template Profile registry is ambiguous")

    def _pointer_identity(self, key: str) -> tuple[str, str]:
        pointer = self.registry.get(key)
        if not isinstance(pointer, dict) or set(pointer) != {"id", "version"}:
            raise TemplateContractError(f"Template registry governance pointer is invalid: {key}")
        identity = (pointer.get("id"), pointer.get("version"))
        if not all(isinstance(item, str) and item for item in identity):
            raise TemplateContractError(f"Template registry governance pointer is invalid: {key}")
        return identity

    def validate_release_governance(self) -> TemplateSelection:
        """Validate the released default and its fail-closed general fallback."""

        if self.registry.get("schema_version") != "template-profiles.v2":
            raise TemplateContractError("Released template governance requires template-profiles.v2")
        if self._pointer_identity("default_profile") != RELEASE_DEFAULT:
            raise TemplateContractError("Released template default must be general@0.2.0")
        if self._pointer_identity("general_fallback_profile") != RELEASE_DEFAULT:
            raise TemplateContractError("General fallback must use the released default")
        default = self._find(*RELEASE_DEFAULT)
        if default.status != RELEASE_DEFAULT_STATUS:
            raise TemplateContractError("Released template default status differs")
        return default

    @staticmethod
    def _project_control_path(project_root: Path, relative: str, label: str) -> Path:
        root = project_root.resolve()
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise TemplateContractError(f"{label} escapes the project root")
        current = root
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                raise TemplateContractError(f"{label} path contains a symlink")
        candidate = root.joinpath(*pure.parts)
        try:
            candidate.resolve(strict=False).relative_to(root)
        except ValueError as error:
            raise TemplateContractError(f"{label} escapes the project root") from error
        return candidate

    def _config_path(self, project_root: Path) -> Path:
        return self._project_control_path(
            project_root,
            ".better-product-graph/template-profile.json",
            "Project Template configuration",
        )

    def _config_lock_path(self, project_root: Path) -> Path:
        return self._project_control_path(
            project_root,
            ".better-product-graph/locks/template-profile.lock",
            "Project Template configuration lock",
        )

    @contextmanager
    def _config_lock(self, project_root: Path) -> Iterator[Path]:
        config_path = self._config_path(project_root)
        with exclusive_file_lock(self._config_lock_path(project_root)):
            # Recheck after waiting so an ancestor cannot be swapped for a symlink.
            yield self._config_path(project_root)

    @staticmethod
    def _assert_regular_contained(root: Path, relative: str, label: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise TemplateContractError(f"{label} path escapes its registry root")
        candidate = root.joinpath(*pure.parts)
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise TemplateContractError(f"{label} path escapes its registry root") from error
        current = root
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                raise TemplateContractError(f"{label} path contains a symlink")
        if not candidate.is_file():
            raise TemplateContractError(f"{label} is missing")
        return candidate

    def _find(
        self,
        profile_id: str,
        version: str,
        *,
        selection_source: str = "BUILTIN_EXPLICIT_PIN",
        fallback_reason: str | None = None,
    ) -> TemplateSelection:
        matches = [
            item
            for item in self.registry.get("profiles", [])
            if item.get("id") == profile_id and item.get("version") == version
        ]
        if len(matches) != 1:
            raise TemplateContractError(
                f"Template Profile not found exactly once: {profile_id}@{version}"
            )
        item = matches[0]
        path = self._assert_regular_contained(self.templates_root, item.get("path", ""), "Template")
        actual_hash = sha256_file(path)
        if actual_hash != item.get("sha256"):
            raise TemplateContractError(
                f"Template hash mismatch for {profile_id}@{version}: {actual_hash}"
            )
        contract_relative = item.get("output_contract_path")
        if not isinstance(contract_relative, str):
            raise TemplateContractError("Template Profile output contract path is required")
        contract_path = self._assert_regular_contained(
            self.templates_root, contract_relative, "Output contract"
        )
        contract_hash = item.get("output_contract_sha256")
        contract_version = item.get("output_contract_version")
        if not isinstance(contract_hash, str) or not isinstance(contract_version, str):
            raise TemplateContractError("Template Profile output contract binding is required")
        _validate_output_contract(contract_path, contract_hash, contract_version)
        return TemplateSelection(
            profile_id,
            version,
            item["status"],
            path,
            actual_hash,
            item["path"],
            contract_path,
            contract_hash,
            contract_version,
            contract_relative,
            "BUILTIN",
            selection_source,
            fallback_reason,
        )

    def _general_default(
        self,
        *,
        selection_source: str = "BPG_GENERAL_DEFAULT",
        fallback_reason: str | None = None,
    ) -> TemplateSelection:
        general_id, general_version = self._pointer_identity("general_fallback_profile")
        selection = self._find(
            general_id,
            general_version,
            selection_source=selection_source,
            fallback_reason=fallback_reason,
        )
        if selection.profile_id != "general":
            raise TemplateContractError("BPG general fallback profile is invalid")
        return selection

    def _registry_default(
        self,
        *,
        selection_source: str = "REGISTRY_DEFAULT_UNPINNED",
    ) -> TemplateSelection:
        default_id, default_version = self._pointer_identity("default_profile")
        selection = self._find(
            default_id,
            default_version,
            selection_source=selection_source,
        )
        self._validate_selection_semantics(selection)
        return selection

    def _is_general_fallback(self, selection: TemplateSelection) -> bool:
        return (selection.profile_id, selection.version) == self._pointer_identity(
            "general_fallback_profile"
        )

    def _validate_selection_semantics(self, selection: TemplateSelection) -> None:
        if selection.origin == "PROJECT":
            if (
                selection.selection_source != "PROJECT_TEMPLATE"
                or selection.fallback_reason is not None
                or selection.requested_profile_id != selection.profile_id
                or selection.requested_version != selection.version
            ):
                raise TemplateContractError("Project Template selection_source combination is invalid")
            return
        if selection.origin != "BUILTIN":
            raise TemplateContractError("Template selection source kind is invalid")
        if selection.selection_source == "GENERAL_FALLBACK":
            if (
                not self._is_general_fallback(selection)
                or selection.fallback_reason not in FALLBACK_REASONS
                or not isinstance(selection.requested_profile_id, str)
                or not selection.requested_profile_id
                or not isinstance(selection.requested_version, str)
                or not selection.requested_version
            ):
                raise TemplateContractError("General fallback selection identity or reason is invalid")
            return
        if selection.selection_source not in BUILTIN_SELECTION_SOURCES:
            raise TemplateContractError("Built-in Template selection_source is invalid")
        if any(
            value is not None
            for value in (
                selection.fallback_reason,
                selection.requested_profile_id,
                selection.requested_version,
            )
        ):
            raise TemplateContractError("Built-in Template selection cannot forge fallback context")
        if selection.selection_source == "BPG_GENERAL_DEFAULT" and not self._is_general_fallback(
            selection
        ):
            raise TemplateContractError("BPG general default selection differs from general profile")

    @staticmethod
    def _project_path(project_root: Path, relative: str, label: str) -> Path:
        root = project_root.resolve()
        if not isinstance(relative, str) or not relative:
            raise TemplateContractError(f"{label} path is required")
        pure = PurePosixPath(relative)
        trusted_parts = (".better-product-graph", "templates")
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or tuple(pure.parts[:2]) != trusted_parts
            or len(pure.parts) < 3
        ):
            raise TemplateContractError(f"{label} must stay in the trusted project template area")
        trusted = root / trusted_parts[0] / trusted_parts[1]
        current = root
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                raise TemplateContractError(
                    f"{label} must stay in the trusted project template area without symlinks"
                )
        resolved = (root / Path(*pure.parts)).resolve(strict=False)
        try:
            resolved.relative_to(trusted.resolve(strict=False))
        except ValueError as error:
            raise TemplateContractError(
                f"{label} must stay in the trusted project template area"
            ) from error
        return root / Path(*pure.parts)

    def _fallback_or_raise(
        self,
        policy: str,
        reason: str,
        *,
        requested_profile_id: str,
        requested_version: str,
    ) -> TemplateSelection:
        if reason not in FALLBACK_REASONS or policy != "GENERAL_ON_UNAVAILABLE":
            raise TemplateContractError(reason)
        selection = replace(
            self._general_default(
                selection_source="GENERAL_FALLBACK",
                fallback_reason=reason,
            ),
            requested_profile_id=requested_profile_id,
            requested_version=requested_version,
        )
        self._validate_selection_semantics(selection)
        return selection

    @staticmethod
    def _requested_active_sha256(active: dict[str, Any]) -> str:
        return sha256_bytes(canonical_json_bytes(active))

    def _validate_project_active_schema(
        self, project_root: Path, active: dict[str, Any]
    ) -> tuple[Path, Path]:
        """Validate every requested-project identity field without requiring availability."""

        if set(active) != PROJECT_ACTIVE_FIELDS or active.get("kind") != "PROJECT":
            raise TemplateContractError("Project Template configuration is ambiguous or incomplete")
        if active.get("fallback_policy") not in {"FAIL_CLOSED", "GENERAL_ON_UNAVAILABLE"}:
            raise TemplateContractError("Project Template fallback policy is invalid")
        if not isinstance(active.get("applicable"), bool):
            raise TemplateContractError("Project Template applicability must be explicit")
        if not isinstance(active.get("profile_id"), str) or not active["profile_id"]:
            raise TemplateContractError("Project Template id is required")
        if not isinstance(active.get("version"), str) or not active["version"]:
            raise TemplateContractError("Project Template version is required")
        expected_template_hash = active.get("template_sha256")
        contract_hash = active.get("output_contract_sha256")
        contract_version = active.get("output_contract_version")
        if not _is_exact_sha256(expected_template_hash):
            raise TemplateContractError("Project Template exact hash is required")
        if (
            not _is_exact_sha256(contract_hash)
            or not isinstance(contract_version, str)
            or not contract_version
        ):
            raise TemplateContractError("Project output contract exact binding is required")
        template = self._project_path(project_root, active["template_path"], "Project Template")
        contract = self._project_path(
            project_root, active["output_contract_path"], "Project output contract"
        )
        return template, contract

    def _resolve_project(self, project_root: Path, active: dict[str, Any]) -> TemplateSelection:
        template, contract = self._validate_project_active_schema(project_root, active)
        template_exists = template.is_file() and not template.is_symlink()
        contract_exists = contract.is_file() and not contract.is_symlink()
        expected_template_hash = active.get("template_sha256")
        contract_hash = active.get("output_contract_sha256")
        contract_version = active.get("output_contract_version")
        actual_hash = sha256_file(template) if template_exists else None
        if template_exists and actual_hash != expected_template_hash:
            raise TemplateContractError("Project Template hash mismatch")
        if contract_exists:
            _validate_output_contract(contract, contract_hash, contract_version)
        if not active["applicable"]:
            return self._fallback_or_raise(
                active["fallback_policy"],
                "PROJECT_TEMPLATE_NOT_APPLICABLE",
                requested_profile_id=active["profile_id"],
                requested_version=active["version"],
            )
        if not template_exists or not contract_exists:
            return self._fallback_or_raise(
                active["fallback_policy"],
                "PROJECT_TEMPLATE_UNAVAILABLE",
                requested_profile_id=active["profile_id"],
                requested_version=active["version"],
            )
        selection = TemplateSelection(
            active["profile_id"],
            active["version"],
            "PROJECT_ACTIVE",
            template,
            actual_hash,
            active["template_path"],
            contract,
            contract_hash,
            contract_version,
            active["output_contract_path"],
            "PROJECT",
            "PROJECT_TEMPLATE",
            None,
            active["profile_id"],
            active["version"],
        )
        self._validate_selection_semantics(selection)
        return selection

    def _selection_from_config(self, project_root: Path, config: dict[str, Any]) -> TemplateSelection:
        schema = config.get("schema_version")
        active = config.get("active")
        if not isinstance(active, dict):
            raise TemplateContractError("Pinned Template active selection is missing")
        if schema == "template-profile-pin.v1":
            selection = self._find(active.get("profile_id"), active.get("version"))
            if selection.sha256 != active.get("sha256"):
                raise TemplateContractError("Pinned Template hash no longer matches registry")
            self._validate_selection_semantics(selection)
            return selection
        if schema != "template-profile-pin.v2" or config.get("migration_policy") != "EXPLICIT_ONLY":
            raise TemplateContractError("Pinned Template configuration schema is invalid")
        allowed_top = {
            "schema_version",
            "active",
            "history",
            "migration_policy",
            "fallback_lock",
        }
        if set(config) - allowed_top:
            raise TemplateContractError("Pinned Template configuration is ambiguous")
        fallback_lock = config.get("fallback_lock")
        if fallback_lock is not None:
            if not isinstance(fallback_lock, dict):
                raise TemplateContractError("Pinned fallback lock is invalid")
            self._validate_project_active_schema(project_root, active)
            allowed_lock = {
                "requested_profile_id",
                "requested_version",
                "requested_active_sha256",
                "selected_profile_id",
                "selected_version",
                "template_sha256",
                "selected_template_relative_path",
                "output_contract_sha256",
                "selected_output_contract_relative_path",
                "selected_output_contract_version",
                "reason_code",
            }
            if set(fallback_lock) != allowed_lock:
                raise TemplateContractError("Pinned fallback lock is ambiguous")
            expected_reason = (
                "PROJECT_TEMPLATE_NOT_APPLICABLE"
                if active["applicable"] is False
                else "PROJECT_TEMPLATE_UNAVAILABLE"
            )
            if (
                active.get("kind") != "PROJECT"
                or
                fallback_lock.get("reason_code") not in FALLBACK_REASONS
                or fallback_lock.get("reason_code") != expected_reason
                or fallback_lock.get("requested_profile_id") != active.get("profile_id")
                or fallback_lock.get("requested_version") != active.get("version")
                or fallback_lock.get("requested_active_sha256")
                != self._requested_active_sha256(active)
                or (
                    fallback_lock.get("selected_profile_id"),
                    fallback_lock.get("selected_version"),
                )
                != self._pointer_identity("general_fallback_profile")
            ):
                raise TemplateContractError("Pinned fallback reason or general identity is invalid")
            selected = self._find(
                fallback_lock.get("selected_profile_id"),
                fallback_lock.get("selected_version"),
                selection_source="GENERAL_FALLBACK",
                fallback_reason=fallback_lock.get("reason_code"),
            )
            if (
                selected.sha256 != fallback_lock.get("template_sha256")
                or selected.relative_path
                != fallback_lock.get("selected_template_relative_path")
                or selected.output_contract_sha256
                != fallback_lock.get("output_contract_sha256")
                or selected.output_contract_relative_path
                != fallback_lock.get("selected_output_contract_relative_path")
                or selected.output_contract_version
                != fallback_lock.get("selected_output_contract_version")
            ):
                raise TemplateContractError("Pinned fallback Template or contract identity changed")
            selection = replace(
                selected,
                requested_profile_id=fallback_lock.get("requested_profile_id"),
                requested_version=fallback_lock.get("requested_version"),
            )
            self._validate_selection_semantics(selection)
            return selection
        if active.get("kind") == "PROJECT":
            return self._resolve_project(project_root, active)
        allowed = {
            "kind",
            "profile_id",
            "version",
            "template_sha256",
            "template_relative_path",
            "output_contract_sha256",
            "output_contract_relative_path",
            "output_contract_version",
            "selection_source",
        }
        if set(active) != allowed or active.get("kind") != "BUILTIN":
            raise TemplateContractError("Pinned built-in Template configuration is ambiguous")
        selection = self._find(
            active.get("profile_id"),
            active.get("version"),
            selection_source=active.get("selection_source"),
        )
        if (
            selection.sha256 != active.get("template_sha256")
            or selection.relative_path != active.get("template_relative_path")
            or selection.output_contract_sha256 != active.get("output_contract_sha256")
            or selection.output_contract_relative_path
            != active.get("output_contract_relative_path")
            or selection.output_contract_version != active.get("output_contract_version")
        ):
            raise TemplateContractError("Pinned Template or output contract identity changed")
        self._validate_selection_semantics(selection)
        return selection

    def resolve(self, project_root: Path) -> TemplateSelection:
        config_path = self._config_path(project_root)
        if not config_path.exists():
            return self._registry_default()
        with self._config_lock(project_root) as config_path:
            if config_path.exists():
                if config_path.is_symlink() or not config_path.is_file():
                    raise TemplateContractError("Pinned Template configuration is not a regular file")
                config = read_json(config_path)
                selection = self._selection_from_config(project_root, config)
                if selection.selection_source == "GENERAL_FALLBACK" and "fallback_lock" not in config:
                    config["fallback_lock"] = self._fallback_lock_payload(
                        selection, config["active"]
                    )
                    atomic_write_json(config_path, config)
                return selection
            return self._registry_default()

    @staticmethod
    def _built_in_active(selection: TemplateSelection, source: str) -> dict[str, Any]:
        return {
            "kind": "BUILTIN",
            "profile_id": selection.profile_id,
            "version": selection.version,
            "template_sha256": selection.sha256,
            "template_relative_path": selection.relative_path,
            "output_contract_sha256": selection.output_contract_sha256,
            "output_contract_relative_path": selection.output_contract_relative_path,
            "output_contract_version": selection.output_contract_version,
            "selection_source": source,
        }

    @staticmethod
    def _fallback_lock_payload(
        selection: TemplateSelection, requested_active: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "requested_profile_id": selection.requested_profile_id,
            "requested_version": selection.requested_version,
            "requested_active_sha256": TemplateRegistry._requested_active_sha256(
                requested_active
            ),
            "selected_profile_id": selection.profile_id,
            "selected_version": selection.version,
            "template_sha256": selection.sha256,
            "selected_template_relative_path": selection.relative_path,
            "output_contract_sha256": selection.output_contract_sha256,
            "selected_output_contract_relative_path": selection.output_contract_relative_path,
            "selected_output_contract_version": selection.output_contract_version,
            "reason_code": selection.fallback_reason,
        }

    def _config_payload(
        self,
        config_path: Path,
        active: dict[str, Any],
        selection: TemplateSelection | None = None,
    ) -> dict[str, Any]:
        history: list[dict[str, Any]] = []
        if config_path.exists():
            if config_path.is_symlink() or not config_path.is_file():
                raise TemplateContractError("Pinned Template configuration is not a regular file")
            existing = read_json(config_path)
            self._selection_from_config(config_path.parents[1], existing)
            history = list(existing.get("history", []))
        history.append(active)
        payload = {
            "schema_version": "template-profile-pin.v2",
            "active": active,
            "history": history,
            "migration_policy": "EXPLICIT_ONLY",
        }
        if selection is not None and selection.selection_source == "GENERAL_FALLBACK":
            payload["fallback_lock"] = self._fallback_lock_payload(selection, active)
        return payload

    def _write_active(
        self,
        project_root: Path,
        active: dict[str, Any],
        selection: TemplateSelection | None = None,
    ) -> None:
        with self._config_lock(project_root) as config_path:
            atomic_write_json(
                config_path,
                self._config_payload(config_path, active, selection),
            )

    def resolve_for_runtime(self, project_root: Path) -> TemplateSelection:
        """Resolve once at runtime and lock an unconfigured project to exact hashes."""

        with self.runtime_selection_transaction(project_root) as selection:
            return selection

    @contextmanager
    def runtime_selection_transaction(
        self,
        project_root: Path,
        *,
        retain_new_pin_on_error: Callable[[TemplateSelection], bool] | None = None,
    ) -> Iterator[TemplateSelection]:
        """Lock the first default; remove it only when no exact durable caller binding exists."""

        with self._config_lock(project_root) as config_path:
            if config_path.exists():
                if config_path.is_symlink() or not config_path.is_file():
                    raise TemplateContractError("Pinned Template configuration is not a regular file")
                yield self._selection_from_config(project_root, read_json(config_path))
                return
            selection = self._registry_default(selection_source="REGISTRY_DEFAULT_PIN")
            active = self._built_in_active(selection, "REGISTRY_DEFAULT_PIN")
            payload = self._config_payload(config_path, active)
            atomic_write_json(config_path, payload)
            pinned_bytes = config_path.read_bytes()
            try:
                yield selection
            except BaseException:
                retain_pin = False
                if retain_new_pin_on_error is not None:
                    try:
                        retain_pin = retain_new_pin_on_error(selection)
                    except Exception:
                        # An unreadable durability record is not proof that deleting the pin is safe.
                        retain_pin = True
                if (
                    not retain_pin
                    and config_path.is_file()
                    and not config_path.is_symlink()
                    and config_path.read_bytes() == pinned_bytes
                ):
                    config_path.unlink()
                raise

    def pin(self, project_root: Path, profile_id: str, version: str) -> TemplateSelection:
        selection = self._find(
            profile_id, version, selection_source="BUILTIN_EXPLICIT_PIN"
        )
        self._write_active(
            project_root,
            self._built_in_active(selection, "BUILTIN_EXPLICIT_PIN"),
        )
        return selection

    def register_project_template(
        self,
        project_root: Path,
        *,
        profile_id: str,
        version: str,
        template_path: Path,
        template_sha256: str,
        output_contract_path: Path,
        output_contract_sha256: str,
        fallback_policy: str = "FAIL_CLOSED",
        applicable: bool = True,
    ) -> TemplateSelection:
        if not profile_id or not version:
            raise TemplateContractError("Project Template id and version are required")
        if fallback_policy not in {"FAIL_CLOSED", "GENERAL_ON_UNAVAILABLE"}:
            raise TemplateContractError("Project Template fallback policy is invalid")
        if not isinstance(applicable, bool):
            raise TemplateContractError("Project Template applicability must be explicit")
        template_relative = template_path.as_posix()
        contract_relative = output_contract_path.as_posix()
        template = self._project_path(project_root, template_relative, "Project Template")
        contract = self._project_path(project_root, contract_relative, "Project output contract")
        if not template.is_file() or not contract.is_file():
            raise TemplateContractError("Project Template and output contract must exist to register")
        if sha256_file(template) != template_sha256:
            raise TemplateContractError("Project Template hash mismatch")
        contract_payload = read_json(contract)
        contract_version = contract_payload.get("contract_version")
        if not isinstance(contract_version, str):
            raise TemplateContractError("Project output contract version is required")
        _validate_output_contract(contract, output_contract_sha256, contract_version)
        active = {
            "kind": "PROJECT",
            "profile_id": profile_id,
            "version": version,
            "template_path": template_relative,
            "template_sha256": template_sha256,
            "output_contract_path": contract_relative,
            "output_contract_sha256": output_contract_sha256,
            "output_contract_version": contract_version,
            "fallback_policy": fallback_policy,
            "applicable": applicable,
        }
        selection = self._resolve_project(project_root, active)
        self._write_active(project_root, active, selection)
        return selection

    def selection_from_metadata(
        self, project_root: Path, template_profile: dict[str, Any]
    ) -> TemplateSelection:
        """Reconstruct and verify the exact selection archived with a Candidate."""

        if not isinstance(template_profile, dict):
            raise TemplateContractError("Archived Template selection metadata is missing")
        contract_ref = template_profile.get("output_contract")
        if not isinstance(contract_ref, dict):
            raise TemplateContractError("Archived output contract metadata is missing")
        source_kind = template_profile.get("source_kind")
        if source_kind == "BUILTIN":
            selection = self._find(
                template_profile.get("id"),
                template_profile.get("version"),
                selection_source=template_profile.get("selection_source"),
                fallback_reason=template_profile.get("fallback_reason"),
            )
            if (
                template_profile.get("path") != selection.reference_path
                or template_profile.get("sha256") != selection.sha256
                or contract_ref.get("path") != selection.output_contract_reference_path
                or contract_ref.get("sha256") != selection.output_contract_sha256
                or contract_ref.get("version") != selection.output_contract_version
            ):
                raise TemplateContractError("Archived built-in Template selection changed")
            selection = replace(
                selection,
                requested_profile_id=template_profile.get("requested_profile_id"),
                requested_version=template_profile.get("requested_version"),
            )
            self._validate_selection_semantics(selection)
            return selection
        if source_kind != "PROJECT":
            raise TemplateContractError("Archived Template source kind is invalid")
        template_relative = template_profile.get("path")
        contract_relative = contract_ref.get("path")
        if not isinstance(template_relative, str) or not isinstance(contract_relative, str):
            raise TemplateContractError("Archived project Template paths are invalid")
        template = self._project_path(project_root, template_relative, "Project Template")
        contract = self._project_path(project_root, contract_relative, "Project output contract")
        if not template.is_file() or sha256_file(template) != template_profile.get("sha256"):
            raise TemplateContractError("Archived Project Template hash mismatch")
        contract_hash = contract_ref.get("sha256")
        contract_version = contract_ref.get("version")
        if not isinstance(contract_hash, str) or not isinstance(contract_version, str):
            raise TemplateContractError("Archived project output contract binding is invalid")
        _validate_output_contract(contract, contract_hash, contract_version)
        selection = TemplateSelection(
            template_profile.get("id"),
            template_profile.get("version"),
            template_profile.get("status"),
            template,
            template_profile.get("sha256"),
            template_relative,
            contract,
            contract_hash,
            contract_version,
            contract_relative,
            "PROJECT",
            template_profile.get("selection_source"),
            template_profile.get("fallback_reason"),
            template_profile.get("requested_profile_id"),
            template_profile.get("requested_version"),
        )
        self._validate_selection_semantics(selection)
        return selection

    def rollback(self, project_root: Path, target_hash: str) -> TemplateSelection:
        with self._config_lock(project_root) as config_path:
            if not config_path.exists():
                raise TemplateContractError("No Template pin history exists")
            config = read_json(config_path)
            self._selection_from_config(project_root, config)
            targets = [
                item
                for item in config.get("history", [])
                if item.get("template_sha256", item.get("sha256")) == target_hash
            ]
            if not targets:
                raise TemplateContractError("Rollback target hash is not in project pin history")
            target = targets[-1]
            if target.get("kind") == "PROJECT":
                selection = self._resolve_project(project_root, target)
                self._write_active(project_root, target, selection)
                return selection
            return self.pin(project_root, target["profile_id"], target["version"])
