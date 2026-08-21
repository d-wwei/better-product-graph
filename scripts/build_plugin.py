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
import sys
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.promote_prd_template import sync_prd_template_v02


class BuildError(RuntimeError):
    """Raised when source or installed Plugin violates the build contract."""


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


DEFAULT_HOST = "codex"
SUPPORTED_HOSTS = ("codex", "claude")
HOST_MANIFEST_DIRS = {host: f".{host}-plugin" for host in SUPPORTED_HOSTS}

OVERLAY_TOP_LEVEL_KEYS = frozenset({"overlay_schema_version", "host"})
HOST_KEYS = frozenset(
    {
        "host_id",
        "manifest_dir",
        "public_skill_source_root",
        "exact_files",
        "validator",
        "public_skill_parity",
        "byte_identical_sources",
    }
)


def _overlay_path(repo_root: Path, host: str) -> Path:
    return repo_root / "config" / f"plugin-build.{host}.json"


def _load_config(repo_root: Path, host: str = DEFAULT_HOST) -> tuple[dict[str, Any], list[Path]]:
    """Load the shared base contract, then mechanically merge one exact host overlay."""
    if host not in SUPPORTED_HOSTS:
        raise BuildError(f"unsupported host target: {host}")
    base_path = repo_root / "config" / "plugin-build.json"
    config = json.loads(base_path.read_text(encoding="utf-8"))
    sources = [base_path]
    if config.get("host", {}).get("host_id") != DEFAULT_HOST:
        raise BuildError("base build config must carry the default host target")
    if host != DEFAULT_HOST:
        overlay_path = _overlay_path(repo_root, host)
        if not overlay_path.is_file():
            raise BuildError(f"host overlay is missing: {overlay_path}")
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        shared_keys = sorted(set(overlay) - OVERLAY_TOP_LEVEL_KEYS)
        if shared_keys:
            raise BuildError(f"host overlay must not declare shared keys: {shared_keys}")
        host_overlay = overlay.get("host")
        if not isinstance(host_overlay, dict):
            raise BuildError("host overlay must declare exactly one host block")
        unknown = sorted(set(host_overlay) - HOST_KEYS)
        if unknown:
            raise BuildError(f"host overlay declares unknown host keys: {unknown}")
        if host_overlay.get("host_id") != host:
            raise BuildError("host overlay identity differs from the requested host target")
        config["host"] = host_overlay
        sources.append(overlay_path)
    _validate_host_block(config["host"])
    return config, sources


def _validate_host_block(host: dict[str, Any]) -> None:
    for key in ("host_id", "manifest_dir", "public_skill_source_root", "exact_files"):
        if key not in host:
            raise BuildError(f"host block is missing required key: {key}")
    unknown = sorted(set(host) - HOST_KEYS)
    if unknown:
        raise BuildError(f"host block declares unknown keys: {unknown}")
    manifest_dir = host["manifest_dir"]
    if manifest_dir != f".{host['host_id']}-plugin":
        raise BuildError("host manifest directory must match the host identity")
    _check_relative(manifest_dir)
    _check_relative(host["public_skill_source_root"])
    if not host["public_skill_source_root"].startswith(f"host-adapters/{host['host_id']}/"):
        raise BuildError("public Skill source root must live under the exact host adapter")
    for item in host["exact_files"]:
        _check_relative(item["source"])
        _check_relative(item["target"])
        if not item["source"].startswith(f"host-adapters/{host['host_id']}/"):
            raise BuildError(f"host file must live under the exact host adapter: {item['source']}")
    parity = host.get("public_skill_parity")
    if parity is not None:
        _check_relative(parity["baseline_source"])
        _check_relative(parity["target_source"])
    for pair in host.get("byte_identical_sources", []):
        _check_relative(pair["baseline"])
        _check_relative(pair["target"])


def _verify_baseline(repo_root: Path, baseline: dict[str, str]) -> None:
    actual = _sha256_file(_source_path(repo_root, baseline["path"])).removeprefix("sha256:")
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


def _source_path(repo_root: Path, relative: str) -> Path:
    """Resolve one declared source without lexical or symlink escape from the checkout."""

    _check_relative(relative)
    candidate = repo_root
    for part in PurePosixPath(relative).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise BuildError(f"source path crosses a symlink: {relative}")
    try:
        candidate.resolve(strict=False).relative_to(repo_root.resolve())
    except ValueError as error:
        raise BuildError(f"source path escapes repository root: {relative}") from error
    return candidate


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


# OS/interpreter noise that can never be a legitimate build input. Everything else
# outside the allowlist still fails the build closed.
IGNORED_SOURCE_NAMES = frozenset({".DS_Store", "Thumbs.db", ".directory"})


def _tree_files(source_root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(source_root.rglob("*")):
        relative = path.relative_to(source_root)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.name in IGNORED_SOURCE_NAMES:
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
    host = config["host"]
    public_root = _source_path(repo_root, host["public_skill_source_root"])
    if not public_root.is_dir():
        raise BuildError(f"public Skill source root is missing: {public_root}")
    prefix = f"host-adapters/{host['host_id']}/public-skill/"
    declared = {
        str(_source_path(repo_root, item["source"]).resolve())
        for item in host["exact_files"]
        if item["source"].startswith(prefix)
    }
    for path in public_root.rglob("*"):
        if "__pycache__" in path.relative_to(public_root).parts:
            continue
        if path.name in IGNORED_SOURCE_NAMES:
            continue
        if path.is_file() and str(path.resolve()) not in declared:
            raise BuildError(f"public Skill source file is not allowlisted: {path}")


def _validate_host_parity(repo_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Prove that host-specific public sources stay a declared delta over the default host."""
    host = config["host"]
    records: dict[str, Any] = {"byte_identical": [], "public_skill_parity": None}
    for pair in host.get("byte_identical_sources", []):
        baseline = _source_path(repo_root, pair["baseline"])
        target = _source_path(repo_root, pair["target"])
        baseline_hash = _sha256_file(baseline)
        if baseline_hash != _sha256_file(target):
            raise BuildError(f"host file must stay byte-identical to {pair['baseline']}")
        records["byte_identical"].append({**pair, "sha256": baseline_hash})
    parity = host.get("public_skill_parity")
    if parity is not None:
        baseline_text = _source_path(repo_root, parity["baseline_source"]).read_text(
            encoding="utf-8"
        )
        expected = baseline_text
        for substitution in parity["substitutions"]:
            if expected.count(substitution["from"]) != 1:
                raise BuildError("public Skill parity substitution source is not unique")
            expected = expected.replace(substitution["from"], substitution["to"])
        actual = _source_path(repo_root, parity["target_source"]).read_text(encoding="utf-8")
        if actual != expected:
            raise BuildError(
                "host public Skill differs from the default host beyond its declared substitutions"
            )
        records["public_skill_parity"] = {
            "baseline_source": parity["baseline_source"],
            "baseline_sha256": _sha256_bytes(baseline_text.encode()),
            "target_sha256": _sha256_bytes(actual.encode()),
            "substitutions": len(parity["substitutions"]),
        }
    return records


def _validate_no_source_absolute_paths(repo_root: Path, output_root: Path) -> None:
    """No built file may leak a build-machine absolute path."""
    needles = [str(repo_root).encode(), str(repo_root.home()).encode(), b"/Users/", b"/home/"]
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        content = path.read_bytes()
        for needle in needles:
            if needle in content:
                relative = path.relative_to(output_root).as_posix()
                raise BuildError(f"built file leaks a source absolute path: {relative}")


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


def _output_fingerprint(output_root: Path, relative_targets: list[str]) -> str:
    """Host-independent fingerprint over exactly the shared Core trees in one built Plugin."""
    records = [
        {"path": relative, "sha256": _sha256_file(output_root / relative)}
        for relative in sorted(set(relative_targets))
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


def build_plugin(
    repo_root: Path, output_root: Path, *, host: str = DEFAULT_HOST
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    config, config_sources = _load_config(repo_root, host)
    host_block = config["host"]
    template_promotion = sync_prd_template_v02(repo_root, check=True)
    _verify_baseline(repo_root, config["architecture_baseline"])
    _verify_baseline(repo_root, config["roadmap_baseline"])
    _validate_public_source(repo_root, config)
    host_parity = _validate_host_parity(repo_root, config)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    fingerprint_sources: list[Path] = [
        *config_sources,
        *(
            _source_path(repo_root, path)
            for path in config.get("template_source_provenance", [])
        ),
    ]
    for item in config.get("shared_exact_files", []):
        _check_relative(item["source"])
        _check_relative(item["target"])
        source = _source_path(repo_root, item["source"])
        _copy_file(source, output_root / item["target"])
        if item.get("fingerprint"):
            fingerprint_sources.append(source)
    for item in host_block["exact_files"]:
        _check_relative(item["target"])
        source = _source_path(repo_root, item["source"])
        _copy_file(source, output_root / item["target"])
        if item.get("fingerprint"):
            fingerprint_sources.append(source)

    plugin_manifest = json.loads(
        (output_root / host_block["manifest_dir"] / "plugin.json").read_text(encoding="utf-8")
    )
    if (
        plugin_manifest.get("name") != config["plugin_name"]
        or plugin_manifest.get("version") != config["plugin_version"]
    ):
        raise BuildError("Plugin manifest name/version differs from distribution config")

    core_targets: list[str] = []
    for tree in config["trees"]:
        source_root = _source_path(repo_root, tree["source"])
        if not source_root.exists():
            if tree.get("required"):
                raise BuildError(f"required source tree missing: {source_root}")
            continue
        for source in _tree_files(source_root, tree["allowed_names"]):
            relative = source.relative_to(source_root)
            target_relative = Path(tree["target"]) / relative
            _check_relative(target_relative.as_posix())
            _copy_file(source, output_root / target_relative)
            core_targets.append(target_relative.as_posix())
            if tree.get("fingerprint"):
                fingerprint_sources.append(source)

    derived_transforms = _apply_derived_transforms(output_root, config)

    _validate_node_contracts(output_root)
    _validate_reference_catalog(output_root)
    _validate_no_source_absolute_paths(repo_root, output_root)

    skills = sorted(path.relative_to(output_root).as_posix() for path in output_root.glob("skills/*/SKILL.md"))
    if skills != ["skills/better-product-graph/SKILL.md"]:
        raise BuildError(f"expected exactly one discoverable SKILL.md, found {skills}")

    inventory = _inventory(output_root)
    build_manifest = {
        "schema_version": "build-manifest.v0alpha",
        "plugin": {"name": config["plugin_name"], "version": config["plugin_version"]},
        "host": {
            "host_id": host_block["host_id"],
            "manifest_dir": host_block["manifest_dir"],
            "parity": host_parity,
        },
        "core_tree_fingerprint": _output_fingerprint(output_root, core_targets),
        "git": _git_identity(repo_root),
        "architecture_baseline": config["architecture_baseline"],
        "roadmap_baseline": config["roadmap_baseline"],
        "template_promotion": template_promotion,
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
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"valid": False, "errors": [str(error)]}
    actual_inventory = _inventory(plugin_root)
    errors: list[str] = []
    if actual_inventory != manifest.get("inventory"):
        errors.append("installed inventory differs from build manifest")
    actual_hash = _sha256_bytes(_canonical_json(actual_inventory))
    if actual_hash != manifest.get("artifact_hash"):
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
            if (plugin_root / directory / "plugin.json").is_file()
        ]
        if found != [host_id]:
            errors.append(
                "installed host manifest does not match build manifest: " + str(found)
            )
        elif isinstance(plugin, dict):
            try:
                host_manifest = json.loads(
                    (plugin_root / expected_dir / "plugin.json").read_text(encoding="utf-8")
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
    skills = sorted(path.relative_to(plugin_root).as_posix() for path in plugin_root.glob("skills/*/SKILL.md"))
    if skills != ["skills/better-product-graph/SKILL.md"]:
        errors.append("installed copy does not contain exactly one public Skill")
    return {"valid": not errors, "errors": errors, "artifact_hash": actual_hash}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--host", choices=SUPPORTED_HOSTS, default=DEFAULT_HOST)
    args = parser.parse_args()
    result = build_plugin(args.repo, args.output, host=args.host)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
