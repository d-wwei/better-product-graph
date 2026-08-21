#!/usr/bin/env python3
"""Build a self-contained Better Product Graph Plugin through an explicit allowlist."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


class BuildError(RuntimeError):
    """Raised when source or installed Plugin violates the build contract."""


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _load_config(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config" / "plugin-build.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_baseline(repo_root: Path, baseline: dict[str, str]) -> None:
    actual = _sha256_file(repo_root / baseline["path"]).removeprefix("sha256:")
    if actual != baseline["sha256"]:
        raise BuildError(f"frozen baseline hash mismatch: {baseline['path']}")


def _git_identity(repo_root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=repo_root, check=True, capture_output=True, text=True
        )
        return completed.stdout.strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=all")),
    }


def _check_relative(path: str) -> None:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise BuildError(f"path escapes plugin root: {path}")


def _copy_file(source: Path, target: Path) -> None:
    if source.is_symlink():
        raise BuildError(f"symlink is not allowed: {source}")
    if not source.is_file():
        raise BuildError(f"required source file missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(0o755 if source.stat().st_mode & 0o111 else 0o644)


def _allowed(relative: Path, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relative.name, pattern) for pattern in patterns)


def _tree_files(source_root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(source_root.rglob("*")):
        relative = path.relative_to(source_root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise BuildError(f"symlink is not allowed: {path}")
        if path.is_dir():
            continue
        if not _allowed(relative, patterns):
            raise BuildError(f"source file is not allowlisted: {path}")
        if path.name == "SKILL.md":
            raise BuildError(f"internal SKILL.md is forbidden: {path}")
        files.append(path)
    return files


def _validate_public_source(repo_root: Path, config: dict[str, Any]) -> None:
    public_root = repo_root / "host-adapters" / "codex" / "public-skill" / "better-product-graph"
    declared = {
        str((repo_root / item["source"]).resolve())
        for item in config["exact_files"]
        if item["source"].startswith("host-adapters/codex/public-skill/")
    }
    for path in public_root.rglob("*"):
        if path.is_file() and str(path.resolve()) not in declared:
            raise BuildError(f"public Skill source file is not allowlisted: {path}")


def _inventory(plugin_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(plugin_root.rglob("*")):
        if path.is_symlink():
            raise BuildError(f"installed symlink is forbidden: {path}")
        relative_path = path.relative_to(plugin_root)
        if "__pycache__" in relative_path.parts and path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_file() and path.name != "build-manifest.json":
            relative = relative_path.as_posix()
            entries.append({"path": relative, "sha256": _sha256_file(path), "size": path.stat().st_size})
    return entries


def _source_fingerprint(repo_root: Path, sources: list[Path]) -> str:
    records = [
        {"path": path.relative_to(repo_root).as_posix(), "sha256": _sha256_file(path)}
        for path in sorted(set(sources))
    ]
    return _sha256_bytes(_canonical_json(records))


def _validate_node_contracts(output_root: Path) -> None:
    skill = output_root / "skills" / "better-product-graph"
    graph = json.loads((skill / "references" / "graph" / "manifest.json").read_text())
    registry = json.loads((skill / "references" / "graph" / "node-contracts.json").read_text())
    graph_nodes = {item["id"] for item in graph["nodes"]}
    contracts = registry.get("nodes", {})
    if set(contracts) != graph_nodes:
        raise BuildError("node contract registry must map every graph node exactly once")
    for node_id, contract in contracts.items():
        instruction = skill / contract["instruction_ref"]
        if instruction.is_symlink() or not instruction.is_file():
            raise BuildError(f"node instruction missing for {node_id}: {contract['instruction_ref']}")
        routes = sorted(edge["to"] for edge in graph["edges"] if edge["from"] == node_id)
        if sorted(contract.get("routes", [])) != routes:
            raise BuildError(f"node routes differ for {node_id}")
        compatible = contract.get("compatible_instruction_hashes", [])
        if (
            not isinstance(compatible, list)
            or len(compatible) != len(set(compatible))
            or any(
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
                for value in compatible
            )
        ):
            raise BuildError(f"invalid compatible instruction hashes for {node_id}")


def _validate_reference_catalog(output_root: Path) -> None:
    skill = output_root / "skills" / "better-product-graph"
    catalog_path = skill / "references" / "reasoning-catalog" / "reference-catalog-v0.1.json"
    if not catalog_path.is_file() or catalog_path.is_symlink():
        raise BuildError("required internal reference catalog is missing")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    extraction = catalog.get("extraction_manifest", {})
    refs = [
        *catalog.get("core_reasoning", []),
        *catalog.get("cognitive_bases", []),
        *catalog.get("reviewer_profiles", []),
        extraction,
    ]
    if (
        catalog.get("discoverable") is not False
        or len(catalog.get("cognitive_bases", [])) != 20
        or len({item.get("resource_id") for item in refs[:-1]}) != 26
    ):
        raise BuildError("internal reference catalog membership is invalid")
    for ref in refs:
        relative = ref.get("path")
        if not isinstance(relative, str) or "SKILL.md" in relative:
            raise BuildError("internal reference path is invalid")
        path = skill / relative
        if not path.is_file() or path.is_symlink() or _sha256_file(path) != ref.get("hash"):
            raise BuildError(f"internal reference missing or hash mismatch: {relative}")


def _apply_derived_transforms(output_root: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for transform in config.get("derived_transforms", []):
        _check_relative(transform["target"])
        target = output_root / transform["target"]
        if _sha256_file(target) != transform["source_sha256"]:
            raise BuildError(f"derived transform source hash mismatch: {transform['transform_id']}")
        text = target.read_text(encoding="utf-8")
        if text.count(transform["exact_text"]) != 1:
            raise BuildError(f"derived transform exact text mismatch: {transform['transform_id']}")
        target.write_text(
            text.replace(transform["exact_text"], transform["replacement_text"]),
            encoding="utf-8",
        )
        output_hash = _sha256_file(target)
        registry_path = output_root / transform["profile_registry_target"]
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        profiles = [
            item
            for item in registry["profiles"]
            if item.get("id") == transform["profile_id"]
            and item.get("version") == transform["profile_version"]
        ]
        if len(profiles) != 1 or profiles[0].get("sha256") != transform["source_sha256"]:
            raise BuildError(f"derived transform profile binding mismatch: {transform['transform_id']}")
        profiles[0]["source_sha256"] = transform["source_sha256"]
        profiles[0]["sha256"] = output_hash
        registry_path.write_bytes(_canonical_json(registry) + b"\n")
        records.append(
            {
                "transform_id": transform["transform_id"],
                "target": transform["target"],
                "source_sha256": transform["source_sha256"],
                "output_sha256": output_hash,
            }
        )
    return records


def build_plugin(repo_root: Path, output_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    config = _load_config(repo_root)
    _verify_baseline(repo_root, config["architecture_baseline"])
    _verify_baseline(repo_root, config["roadmap_baseline"])
    _validate_public_source(repo_root, config)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    fingerprint_sources: list[Path] = [repo_root / "config" / "plugin-build.json"]
    for item in config["exact_files"]:
        _check_relative(item["target"])
        source = repo_root / item["source"]
        _copy_file(source, output_root / item["target"])
        if item.get("fingerprint"):
            fingerprint_sources.append(source)

    plugin_manifest = json.loads(
        (output_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    if (
        plugin_manifest.get("name") != config["plugin_name"]
        or plugin_manifest.get("version") != config["plugin_version"]
    ):
        raise BuildError("Plugin manifest name/version differs from distribution config")

    for tree in config["trees"]:
        source_root = repo_root / tree["source"]
        if not source_root.exists():
            if tree.get("required"):
                raise BuildError(f"required source tree missing: {source_root}")
            continue
        for source in _tree_files(source_root, tree["allowed_names"]):
            relative = source.relative_to(source_root)
            target_relative = Path(tree["target"]) / relative
            _check_relative(target_relative.as_posix())
            _copy_file(source, output_root / target_relative)
            if tree.get("fingerprint"):
                fingerprint_sources.append(source)

    derived_transforms = _apply_derived_transforms(output_root, config)

    _validate_node_contracts(output_root)
    _validate_reference_catalog(output_root)

    skills = sorted(path.relative_to(output_root).as_posix() for path in output_root.glob("skills/*/SKILL.md"))
    if skills != ["skills/better-product-graph/SKILL.md"]:
        raise BuildError(f"expected exactly one discoverable SKILL.md, found {skills}")

    inventory = _inventory(output_root)
    build_manifest = {
        "schema_version": "build-manifest.v0alpha",
        "plugin": {"name": config["plugin_name"], "version": config["plugin_version"]},
        "git": _git_identity(repo_root),
        "architecture_baseline": config["architecture_baseline"],
        "roadmap_baseline": config["roadmap_baseline"],
        "execution_contract_fingerprint": _source_fingerprint(repo_root, fingerprint_sources),
        "derived_transforms": derived_transforms,
        "inventory": inventory,
        "artifact_hash": _sha256_bytes(_canonical_json(inventory)),
    }
    (output_root / "build-manifest.json").write_bytes(_canonical_json(build_manifest) + b"\n")
    return build_manifest


def verify_installed_identity(plugin_root: Path) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    manifest_path = plugin_root / "build-manifest.json"
    if not manifest_path.is_file():
        return {"valid": False, "errors": ["build-manifest.json missing"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_inventory = _inventory(plugin_root)
    errors: list[str] = []
    if actual_inventory != manifest.get("inventory"):
        errors.append("installed inventory differs from build manifest")
    actual_hash = _sha256_bytes(_canonical_json(actual_inventory))
    if actual_hash != manifest.get("artifact_hash"):
        errors.append("installed artifact hash mismatch")
    skills = sorted(path.relative_to(plugin_root).as_posix() for path in plugin_root.glob("skills/*/SKILL.md"))
    if skills != ["skills/better-product-graph/SKILL.md"]:
        errors.append("installed copy does not contain exactly one public Skill")
    return {"valid": not errors, "errors": errors, "artifact_hash": actual_hash}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = build_plugin(args.repo, args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
