"""Configure a project Template from a versioned external Pack."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .storage import read_json, sha256_file
from .templates import (
    TemplateContractError,
    TemplateRegistry,
    _is_exact_sha256,
    _validate_output_contract,
)


class TemplatePackError(ValueError):
    """A Template Pack is invalid, incompatible, unsafe, or would migrate silently."""


PACK_SCHEMA_VERSION = "bpg-template-pack.v1"
PACK_FIELDS = {
    "schema_version",
    "pack_id",
    "version",
    "requires_bpg",
    "profile_id",
    "template",
    "template_sha256",
    "output_contract",
    "output_contract_sha256",
    "fallback_policy",
    "applicable",
}
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
BPG_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|[A-Za-z-][0-9A-Za-z-]*))*)?$"
)
REQUIREMENT = re.compile(r"^(>=|<=|>|<|==)(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _semver(value: Any, label: str) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise TemplatePackError(f"{label} must be a stable semantic version")
    match = SEMVER.fullmatch(value)
    if match is None:
        raise TemplatePackError(f"{label} must be a stable semantic version")
    return tuple(int(part) for part in match.groups())


def _supports_bpg(requirement: Any, bpg_version: str) -> bool:
    if not isinstance(bpg_version, str):
        raise TemplatePackError("BPG version must be a semantic version")
    current_match = BPG_SEMVER.fullmatch(bpg_version)
    if current_match is None:
        raise TemplatePackError("BPG version must be a semantic version")
    # Template compatibility ranges intentionally compare the stable release core.
    # This lets an RC exercise the exact packs intended for its eventual release,
    # while pack identities themselves remain stable semantic versions.
    current = tuple(int(part) for part in current_match.groups()[:3])
    if not isinstance(requirement, str) or not requirement:
        raise TemplatePackError("Template Pack requires_bpg is required")
    clauses = requirement.split(",")
    if any(not clause or clause != clause.strip() for clause in clauses):
        raise TemplatePackError("Template Pack requires_bpg range is invalid")
    for clause in clauses:
        match = REQUIREMENT.fullmatch(clause)
        if match is None:
            raise TemplatePackError("Template Pack requires_bpg range is invalid")
        operator = match.group(1)
        expected = tuple(int(part) for part in match.groups()[1:])
        satisfied = {
            ">=": current >= expected,
            "<=": current <= expected,
            ">": current > expected,
            "<": current < expected,
            "==": current == expected,
        }[operator]
        if not satisfied:
            return False
    return True


def _pack_file(pack_root: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise TemplatePackError(f"Template Pack {label} path is required")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise TemplatePackError(f"Template Pack {label} path escapes the Pack root")
    candidate = pack_root.joinpath(*pure.parts)
    current = pack_root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise TemplatePackError(f"Template Pack {label} path contains a symlink")
    try:
        candidate.resolve(strict=False).relative_to(pack_root.resolve())
    except ValueError as error:
        raise TemplatePackError(f"Template Pack {label} path escapes the Pack root") from error
    if not candidate.is_file():
        raise TemplatePackError(f"Template Pack {label} is missing")
    return candidate


def _load_manifest(pack_root: Path, bpg_version: str) -> tuple[dict[str, Any], Path, Path]:
    root = pack_root.absolute()
    if root.is_symlink() or not root.is_dir():
        raise TemplatePackError("Template Pack root must be a regular directory, not a symlink")
    manifest_path = root / "pack.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise TemplatePackError("Template Pack pack.json is missing or is a symlink")
    try:
        manifest = read_json(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise TemplatePackError("Template Pack pack.json is invalid JSON") from error
    if (
        not isinstance(manifest, dict)
        or set(manifest) != PACK_FIELDS
        or manifest.get("schema_version") != PACK_SCHEMA_VERSION
    ):
        raise TemplatePackError("Template Pack manifest schema is invalid or ambiguous")
    for field in ("pack_id", "profile_id"):
        if not isinstance(manifest.get(field), str) or SAFE_ID.fullmatch(manifest[field]) is None:
            raise TemplatePackError(f"Template Pack {field} is invalid")
    _semver(manifest.get("version"), "Template Pack version")
    if not _supports_bpg(manifest.get("requires_bpg"), bpg_version):
        raise TemplatePackError(
            f"Template Pack requires BPG {manifest['requires_bpg']}; installed is {bpg_version}"
        )
    if manifest.get("fallback_policy") not in {"FAIL_CLOSED", "GENERAL_ON_UNAVAILABLE"}:
        raise TemplatePackError("Template Pack fallback policy is invalid")
    if not isinstance(manifest.get("applicable"), bool):
        raise TemplatePackError("Template Pack applicability must be explicit")
    if not _is_exact_sha256(manifest.get("template_sha256")):
        raise TemplatePackError("Template Pack exact template hash is required")
    if not _is_exact_sha256(manifest.get("output_contract_sha256")):
        raise TemplatePackError("Template Pack exact output contract hash is required")

    template = _pack_file(root, manifest["template"], "template")
    contract = _pack_file(root, manifest["output_contract"], "output contract")
    if sha256_file(template) != manifest["template_sha256"]:
        raise TemplatePackError("Template Pack template hash mismatch")
    if sha256_file(contract) != manifest["output_contract_sha256"]:
        raise TemplatePackError("Template Pack output contract hash mismatch")
    try:
        contract_payload = read_json(contract)
        contract_version = contract_payload.get("contract_version")
        if not isinstance(contract_version, str) or not contract_version:
            raise TemplateContractError("Output contract version is required")
        _validate_output_contract(
            contract,
            manifest["output_contract_sha256"],
            contract_version,
        )
    except (OSError, json.JSONDecodeError, TemplateContractError, ValueError) as error:
        raise TemplatePackError(f"Template Pack output contract is invalid: {error}") from error
    return manifest, template, contract


def _validate_existing_destination(
    destination: Path,
    *,
    template_sha256: str,
    output_contract_sha256: str,
) -> bool:
    if not destination.exists():
        return False
    if destination.is_symlink() or not destination.is_dir():
        raise TemplatePackError("Configured Template Pack version path is not a regular directory")
    entries = {path.name for path in destination.iterdir()}
    if entries != {"PRD_TEMPLATE.md", "OUTPUT_CONTRACT.json"}:
        raise TemplatePackError("Configured Template Pack version directory is ambiguous")
    template = destination / "PRD_TEMPLATE.md"
    contract = destination / "OUTPUT_CONTRACT.json"
    if template.is_symlink() or contract.is_symlink():
        raise TemplatePackError("Configured Template Pack version contains a symlink")
    if (
        not template.is_file()
        or not contract.is_file()
        or sha256_file(template) != template_sha256
        or sha256_file(contract) != output_contract_sha256
    ):
        raise TemplatePackError("Configured Template Pack version differs from the Pack identity")
    return True


def _remove_empty_parents(path: Path, stop: Path) -> None:
    current = path
    while current != stop and current.exists():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def configure_project_template(
    *,
    project_root: Path,
    templates_root: Path,
    pack_root: Path,
    bpg_version: str,
    allow_version_change: bool = False,
) -> dict[str, Any]:
    """Validate and activate one Pack version as project configuration, without a Run."""

    manifest, source_template, source_contract = _load_manifest(pack_root, bpg_version)
    project = project_root.resolve()
    registry = TemplateRegistry(templates_root)
    destination_relative = Path(
        ".better-product-graph",
        "templates",
        manifest["profile_id"],
        manifest["version"],
    )
    destination = registry._project_path(
        project,
        destination_relative.as_posix(),
        "Template Pack configuration",
    )
    destination_template = destination / "PRD_TEMPLATE.md"
    destination_contract = destination / "OUTPUT_CONTRACT.json"

    try:
        current = registry.resolve(project)
    except TemplateContractError as error:
        raise TemplatePackError(f"Current project Template configuration is invalid: {error}") from error
    same_active = (
        current.origin == "PROJECT"
        and current.profile_id == manifest["profile_id"]
        and current.version == manifest["version"]
        and current.sha256 == manifest["template_sha256"]
        and current.output_contract_sha256 == manifest["output_contract_sha256"]
    )
    if current.origin == "PROJECT" and not same_active and not allow_version_change:
        raise TemplatePackError(
            "An explicit version change is required to replace the active project Template"
        )

    destination_exists = _validate_existing_destination(
        destination,
        template_sha256=manifest["template_sha256"],
        output_contract_sha256=manifest["output_contract_sha256"],
    )
    if same_active:
        if not destination_exists:
            raise TemplatePackError("Active Template Pack files are unavailable")
        return {
            "status": "ALREADY_ACTIVE",
            "configuration_action": "PROJECT_TEMPLATE_CONFIGURE",
            "graph_run_created": False,
            "pack_id": manifest["pack_id"],
            "pack_version": manifest["version"],
            "requires_bpg": manifest["requires_bpg"],
            "bpg_version": bpg_version,
            "profile_id": current.profile_id,
            "profile_version": current.version,
            "template_path": current.relative_path,
            "template_sha256": current.sha256,
            "output_contract_path": current.output_contract_relative_path,
            "output_contract_sha256": current.output_contract_sha256,
            "output_contract_version": current.output_contract_version,
            "fallback_policy": manifest["fallback_policy"],
        }

    created_destination = False
    if not destination_exists:
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{manifest['version']}-", dir=destination.parent))
        try:
            shutil.copy2(source_template, stage / "PRD_TEMPLATE.md")
            shutil.copy2(source_contract, stage / "OUTPUT_CONTRACT.json")
            if (
                sha256_file(stage / "PRD_TEMPLATE.md") != manifest["template_sha256"]
                or sha256_file(stage / "OUTPUT_CONTRACT.json")
                != manifest["output_contract_sha256"]
            ):
                raise TemplatePackError("Template Pack copy verification failed")
            os.replace(stage, destination)
            created_destination = True
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    try:
        selection = registry.register_project_template(
            project,
            profile_id=manifest["profile_id"],
            version=manifest["version"],
            template_path=destination_template.relative_to(project),
            template_sha256=manifest["template_sha256"],
            output_contract_path=destination_contract.relative_to(project),
            output_contract_sha256=manifest["output_contract_sha256"],
            fallback_policy=manifest["fallback_policy"],
            applicable=manifest["applicable"],
        )
    except (OSError, TemplateContractError, ValueError) as error:
        if created_destination and destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
            _remove_empty_parents(
                destination.parent,
                project / ".better-product-graph",
            )
        raise TemplatePackError(f"Template Pack activation failed: {error}") from error

    return {
        "status": "CONFIGURED_AND_ACTIVE",
        "configuration_action": "PROJECT_TEMPLATE_CONFIGURE",
        "graph_run_created": False,
        "pack_id": manifest["pack_id"],
        "pack_version": manifest["version"],
        "requires_bpg": manifest["requires_bpg"],
        "bpg_version": bpg_version,
        "profile_id": selection.profile_id,
        "profile_version": selection.version,
        "template_path": selection.relative_path,
        "template_sha256": selection.sha256,
        "output_contract_path": selection.output_contract_relative_path,
        "output_contract_sha256": selection.output_contract_sha256,
        "output_contract_version": selection.output_contract_version,
        "fallback_policy": manifest["fallback_policy"],
    }
