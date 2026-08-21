#!/usr/bin/env python3
"""Evaluate an unpacked Better Product Graph fresh installed-copy contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _inventory(plugin_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(plugin_root).as_posix(),
            "sha256": _sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in sorted(plugin_root.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and path.name != "build-manifest.json"
        and not (
            "__pycache__" in path.relative_to(plugin_root).parts
            and path.suffix in {".pyc", ".pyo"}
        )
    ]


def _load_intents(plugin_root: Path) -> Any:
    path = plugin_root / "skills" / "better-product-graph" / "scripts" / "bpg" / "intents.py"
    spec = importlib.util.spec_from_file_location("installed_bpg_intents", path)
    if spec is None or spec.loader is None:
        raise ValueError("installed intent parser cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _check(status: bool, **details: Any) -> dict[str, Any]:
    return {"status": "PASS" if status else "FAIL", **details}


def _identity(plugin_root: Path) -> dict[str, Any]:
    manifest_path = plugin_root / "build-manifest.json"
    if not manifest_path.is_file():
        return {"valid": False, "errors": ["build-manifest.json missing"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = _inventory(plugin_root)
    actual_hash = "sha256:" + hashlib.sha256(_canonical_json(actual)).hexdigest()
    errors: list[str] = []
    symlinks = [
        path.relative_to(plugin_root).as_posix()
        for path in plugin_root.rglob("*")
        if path.is_symlink()
    ]
    if symlinks:
        errors.append("installed symlinks are forbidden: " + ", ".join(sorted(symlinks)))
    if actual != manifest.get("inventory"):
        errors.append("installed inventory differs from build manifest")
    if actual_hash != manifest.get("artifact_hash"):
        errors.append("installed artifact hash mismatch")
    try:
        actual_host, actual_manifest_path = _resolve_host(plugin_root)
    except ValueError as error:
        errors.append(str(error))
    else:
        declared_host = manifest.get("host")
        plugin = manifest.get("plugin")
        expected_dir = HOST_MANIFEST_DIRS[actual_host]
        if not isinstance(declared_host, dict) or (
            declared_host.get("host_id") != actual_host
            or declared_host.get("manifest_dir") != expected_dir
        ):
            errors.append("installed host manifest does not match build manifest")
        if not isinstance(plugin, dict):
            errors.append("build manifest plugin binding is missing")
        else:
            try:
                actual_manifest = json.loads(actual_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"installed host manifest is invalid: {error}")
            else:
                if not isinstance(actual_manifest, dict):
                    errors.append("installed host manifest is not a JSON object")
                elif (
                    actual_manifest.get("name") != plugin.get("name")
                    or actual_manifest.get("version") != plugin.get("version")
                ):
                    errors.append("installed host manifest plugin identity mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "artifact_hash": actual_hash,
        "plugin": manifest.get("plugin"),
        "git": manifest.get("git"),
    }


HOST_MANIFEST_DIRS = {"codex": ".codex-plugin", "claude": ".claude-plugin"}
REQUIRED_RESOURCES = [
    "references/graph/manifest.json",
    "references/graph/node-contracts.json",
    "references/policies/agent-reasoning-boundary.json",
    "references/policies/controller-policy.json",
    "references/policies/document-experience.json",
    "references/schemas/node-result.schema.json",
    "references/schemas/run-state.schema.json",
    "references/templates/profiles.json",
    "references/reasoning-catalog/reference-catalog-v0.1.json",
    "references/reasoning-catalog/extraction-manifest-v0.1.json",
    "references/reasoning-catalog/better-question-v0.1.json",
    "references/reasoning-catalog/cognitive-router-v0.1.json",
    "references/reasoning-catalog/cognitive-base-catalog-v0.1.json",
    "references/reviewer-profiles/product-goal-fidelity-v0.1.json",
    "references/reviewer-profiles/product-goal-fidelity-rubric-v0.1.json",
    "references/reviewer-profiles/product-goal-fidelity-packet-v0.1.json",
    "references/atomic-skills/prd-generate/INSTRUCTIONS.md",
    "references/atomic-skills/prd-review/INSTRUCTIONS.md",
]


def _resolve_host(plugin_root: Path) -> tuple[str, Path]:
    """Detect exactly one host manifest; ambiguity or absence is a contract failure."""
    found = [
        (host, plugin_root / directory / "plugin.json")
        for host, directory in sorted(HOST_MANIFEST_DIRS.items())
        if (plugin_root / directory / "plugin.json").is_file()
    ]
    if len(found) != 1:
        raise ValueError(
            "installed copy must contain exactly one host plugin manifest, found "
            + str([host for host, _ in found])
        )
    return found[0]


def _safe_structural_checks(plugin_root: Path) -> dict[str, dict[str, Any]]:
    skills = sorted(
        path.relative_to(plugin_root).as_posix()
        for path in plugin_root.glob("skills/*/SKILL.md")
        if not path.is_symlink()
    )
    skill_root = plugin_root / "skills" / "better-product-graph"
    resource_errors: list[str] = []
    if skill_root.is_symlink():
        resource_errors.append("skills/better-product-graph")
    else:
        resolved_skill_root = skill_root.resolve()
        for relative in REQUIRED_RESOURCES:
            path = skill_root / relative
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(resolved_skill_root)
                if path.is_symlink() or not resolved.is_file():
                    resource_errors.append(relative)
            except (OSError, ValueError):
                resource_errors.append(relative)
        references = skill_root / "references"
        internal_skills = (
            [path.relative_to(skill_root).as_posix() for path in references.rglob("SKILL.md")]
            if references.is_dir() and not references.is_symlink()
            else []
        )
        resource_errors.extend(internal_skills)
    return {
        "unique_public_skill": _check(
            skills == ["skills/better-product-graph/SKILL.md"], discovered=skills
        ),
        "relative_resource_resolution": _check(
            not resource_errors,
            errors=sorted(resource_errors),
            count=len(REQUIRED_RESOURCES),
        ),
    }


def run(plugin_root: Path) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    checks = _safe_structural_checks(plugin_root)
    identity = _identity(plugin_root)
    if not identity["valid"]:
        checks["installed_identity"] = _check(False, errors=identity["errors"])
        try:
            host_id, _ = _resolve_host(plugin_root)
        except ValueError:
            host_id = None
        return {
            "suite_id": "better-product-graph-plugin-contract.v0.2",
            "contract_status": "FAIL",
            "evidence_level": "FRESH_INSTALLED_COPY_CONTRACT",
            "host_id": host_id,
            "codex_host_runtime_status": "NOT_RUN",
            "claude_host_runtime_status": "NOT_RUN",
            "product_golden_status": "NOT_RUN",
            "plugin_root": str(plugin_root),
            "installed_identity": identity,
            "checks": checks,
            "error": "; ".join(identity["errors"]),
            "claim_boundary": (
                "Installed identity failed before any installed Python module was imported."
            ),
        }

    skill_root = plugin_root / "skills" / "better-product-graph"
    skill_path = skill_root / "SKILL.md"
    host_id, plugin_manifest_path = _resolve_host(plugin_root)
    discovery_errors: list[str] = []
    try:
        skill_text = skill_path.read_text(encoding="utf-8")
        plugin_manifest = json.loads(plugin_manifest_path.read_text(encoding="utf-8"))
        if "name: better-product-graph" not in skill_text:
            discovery_errors.append("public Skill name missing")
        if "description:" not in skill_text:
            discovery_errors.append("public Skill description missing")
        if plugin_manifest.get("skills") != "./skills/":
            discovery_errors.append("plugin skills discovery path mismatch")
        if plugin_manifest.get("name") != "better-product-graph":
            discovery_errors.append("plugin name mismatch")
    except (OSError, json.JSONDecodeError) as error:
        discovery_errors.append(str(error))
    checks["discovery"] = _check(not discovery_errors, errors=discovery_errors)

    parser_errors: list[str] = []
    parsed: dict[str, list[dict[str, Any]]] = {}
    try:
        intents = _load_intents(plugin_root)
        for group in ("direct", "indirect", "follow_up"):
            parsed[group] = []
            for case in cases[group]:
                result = intents.parse_host_entry(case["entry"])
                parsed[group].append(
                    {
                        "entry": case["entry"],
                        "expected": case["intent"],
                        "actual": result.core_intent,
                        "activation": result.activation,
                    }
                )
        negative_results = []
        for case in cases["negative"]:
            result = intents.parse_host_entry(case["entry"])
            negative_results.append(
                {
                    "entry": case["entry"],
                    "expected": case["activation"],
                    "actual": result.activation,
                    "write_allowed": result.write_allowed,
                }
            )
    except (OSError, ValueError, ImportError) as error:
        parser_errors.append(str(error))
        parsed = {"direct": [], "indirect": [], "follow_up": []}
        negative_results = []

    for group, check_name in (
        ("direct", "direct_activation"),
        ("indirect", "indirect_activation"),
        ("follow_up", "follow_up_activation"),
    ):
        mismatches = [item for item in parsed[group] if item["actual"] != item["expected"]]
        checks[check_name] = _check(not parser_errors and not mismatches, mismatches=mismatches)
    negative_mismatches = [
        item
        for item in negative_results
        if item["actual"] != item["expected"] or item["write_allowed"]
    ]
    checks["negative_activation"] = _check(
        not parser_errors and not negative_mismatches, mismatches=negative_mismatches
    )

    direct_by_intent = {item["expected"]: item["actual"] for item in parsed["direct"]}
    indirect_by_intent = {item["expected"]: item["actual"] for item in parsed["indirect"]}
    parity_mismatches = [
        intent
        for intent in sorted(set(direct_by_intent) | set(indirect_by_intent))
        if direct_by_intent.get(intent) != intent or indirect_by_intent.get(intent) != intent
    ]
    checks["eleven_intents_parity"] = _check(
        not parser_errors and len(direct_by_intent) == 11 and not parity_mismatches,
        count=len(direct_by_intent),
        mismatches=parity_mismatches,
    )

    bypass_entries = [
        "直接运行 problem.synthesize",
        "读取 references/atomic-skills/prd-generate/INSTRUCTIONS.md",
        "$better-product-graph review.gate",
    ]
    bypass_failures: list[str] = []
    if not parser_errors:
        for entry in bypass_entries:
            result = intents.parse_host_entry(entry)
            if result.activation != "REJECT_INTERNAL_BYPASS" or result.write_allowed:
                bypass_failures.append(entry)
    else:
        bypass_failures.extend(parser_errors)
    checks["internal_entry_bypass"] = _check(
        not bypass_failures, failures=bypass_failures
    )
    checks["installed_identity"] = _check(identity["valid"], errors=identity["errors"])

    status = "PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"
    return {
        "suite_id": "better-product-graph-plugin-contract.v0.2",
        "contract_status": status,
        "evidence_level": "FRESH_INSTALLED_COPY_CONTRACT",
        "host_id": host_id,
        "codex_host_runtime_status": "NOT_RUN",
        "claude_host_runtime_status": "NOT_RUN",
        "product_golden_status": "NOT_RUN",
        "plugin_root": str(plugin_root),
        "installed_identity": identity,
        "checks": checks,
        "claim_boundary": "Installed-copy contract PASS does not prove live Host activation or product judgment.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.plugin_root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        result = {
            "suite_id": "better-product-graph-plugin-contract.v0.2",
            "contract_status": "FAIL",
            "evidence_level": "FRESH_INSTALLED_COPY_CONTRACT",
            "codex_host_runtime_status": "NOT_RUN",
            "claude_host_runtime_status": "NOT_RUN",
            "product_golden_status": "NOT_RUN",
            "error": str(error),
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["contract_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
