#!/usr/bin/env python3
"""Install one package into a disposable CLAUDE_CONFIG_DIR and run local-only smoke gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


MARKETPLACE_NAME = "better-product-graph-local-smoke"
PLUGIN_NAME = "better-product-graph"
PLUGIN_ID = f"{PLUGIN_NAME}@{MARKETPLACE_NAME}"


def _run(
    command: list[str],
    *,
    config_dir: Path,
    cwd: Path | None = None,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["CLAUDE_CONFIG_DIR"] = str(config_dir)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _require(result: dict[str, Any], label: str) -> dict[str, Any]:
    if result["returncode"] != 0:
        raise RuntimeError(f"{label} failed: {result['stderr'] or result['stdout']}")
    return result


def _json_output(result: dict[str, Any], label: str) -> Any:
    _require(result, label)
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{label} did not return JSON") from error


def _tree_fingerprint(root: Path) -> str:
    records: list[dict[str, Any]] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                content = path.read_bytes()
                records.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "size": len(content),
                    }
                )
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _extract_package(package: Path, plugin_root: Path) -> None:
    """Reject traversal, absolute members, and symlinks before writing anything."""
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if pure.is_absolute() or ".." in pure.parts or stat.S_IFMT(mode) == stat.S_IFLNK:
                raise ValueError(f"unsafe package member: {info.filename}")
        archive.extractall(plugin_root)
    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        raise ValueError("package root does not contain .claude-plugin/plugin.json")


def _write_marketplace(marketplace: Path) -> None:
    manifest = marketplace / ".claude-plugin" / "marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "name": MARKETPLACE_NAME,
                "description": "Disposable local marketplace for Better Product Graph install smoke.",
                "owner": {"name": "Better Product Graph contributors"},
                "plugins": [
                    {
                        "name": PLUGIN_NAME,
                        "source": f"./{PLUGIN_NAME}",
                        "description": "Better Product Graph local smoke build.",
                    }
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _installed_entry(config_dir: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    listed = _run([_claude(config_dir), "plugin", "list", "--json"], config_dir=config_dir)
    entries = _json_output(listed, "plugin list")
    if not isinstance(entries, list):
        raise RuntimeError("plugin list did not return a JSON array")
    match = next((item for item in entries if item.get("id") == PLUGIN_ID), None)
    return match, listed


_CLAUDE_BIN: dict[Path, str] = {}


def _claude(config_dir: Path) -> str:
    return _CLAUDE_BIN[config_dir]


def claude_fresh_install_smoke(
    repo_root: Path,
    package: Path,
    *,
    claude_bin: Path,
    work_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    package = package.resolve()
    claude_bin = claude_bin.resolve()
    if not package.is_file():
        raise ValueError("package must exist")
    if not claude_bin.is_file():
        raise ValueError("Claude Code binary must exist")
    root = (
        work_root.resolve()
        if work_root is not None
        else Path(tempfile.mkdtemp(prefix="bpg-claude-fresh-install-")).resolve()
    )
    if root.exists() and any(root.iterdir()):
        raise ValueError("fresh install work root must be empty")
    root.mkdir(parents=True, exist_ok=True)
    config_dir = root / "claude-config"
    marketplace = root / "marketplace"
    plugin_source = marketplace / PLUGIN_NAME
    project = root / "project"
    config_dir.mkdir()
    project.mkdir()
    plugin_source.mkdir(parents=True)
    _CLAUDE_BIN[config_dir] = str(claude_bin)

    _extract_package(package, plugin_source)
    _write_marketplace(marketplace)

    evidence: list[dict[str, Any]] = []

    codex_before = _run(
        [
            sys.executable,
            str(repo_root / "scripts" / "build_plugin.py"),
            "--repo",
            str(repo_root),
            "--host",
            "codex",
            "--output",
            str(root / "codex-before"),
        ],
        config_dir=config_dir,
        cwd=repo_root,
    )
    evidence.append(codex_before)
    codex_before_manifest = _json_output(codex_before, "Codex artifact before Claude install")

    strict_extracted = _run(
        [str(claude_bin), "plugin", "validate", str(plugin_source), "--strict"],
        config_dir=config_dir,
    )
    evidence.append(strict_extracted)
    _require(strict_extracted, "strict validate of safe-extracted plugin root")

    strict_marketplace = _run(
        [str(claude_bin), "plugin", "validate", str(marketplace), "--strict"],
        config_dir=config_dir,
    )
    evidence.append(strict_marketplace)
    _require(strict_marketplace, "strict validate of local marketplace")

    add_marketplace = _run(
        [str(claude_bin), "plugin", "marketplace", "add", str(marketplace)],
        config_dir=config_dir,
    )
    evidence.append(add_marketplace)
    _require(add_marketplace, "marketplace add")

    install = _run(
        [str(claude_bin), "plugin", "install", PLUGIN_ID, "--scope", "user"],
        config_dir=config_dir,
    )
    evidence.append(install)
    _require(install, "plugin install")

    installed, listed = _installed_entry(config_dir)
    evidence.append(listed)
    if installed is None:
        raise RuntimeError("plugin list does not report the freshly installed Plugin")
    installed_root = Path(installed["installPath"]).resolve()
    try:
        installed_root.relative_to(config_dir)
    except ValueError as error:
        raise RuntimeError("Claude installed outside the isolated CLAUDE_CONFIG_DIR") from error

    runner = installed_root / "skills" / PLUGIN_NAME / "scripts" / "bpg_runner.py"
    self_check = _run([sys.executable, str(runner), "--self-check"], config_dir=config_dir)
    evidence.append(self_check)
    identity = _json_output(self_check, "installed self-check")
    if not identity.get("valid"):
        raise RuntimeError("installed identity is invalid")

    contract = _run(
        [
            sys.executable,
            str(repo_root / "evals" / "plugin-contract" / "run_contract.py"),
            "--plugin-root",
            str(installed_root),
        ],
        config_dir=config_dir,
    )
    evidence.append(contract)
    contract_result = _json_output(contract, "Plugin Contract")
    if contract_result.get("contract_status") != "PASS":
        raise RuntimeError("fresh installed Plugin Contract failed")
    if contract_result.get("host_id") != "claude":
        raise RuntimeError("fresh installed copy did not resolve as the Claude host target")

    entry = _run(
        [sys.executable, str(runner), "fresh isolated claude install smoke"],
        config_dir=config_dir,
        cwd=project,
    )
    evidence.append(entry)
    entry_result = _json_output(entry, "installed entry")
    if (
        entry_result.get("status") != "HOST_AGENT_ACTION_REQUIRED"
        or entry_result.get("runtime") != "BPG_2_0_ALPHA"
        or entry_result.get("instructions", {}).get("legacy_public_route") != "REMOVED"
    ):
        raise RuntimeError("installed entry did not select the default BPG 2.0 runtime")
    alpha_payload = project / "bpg2-start.json"
    alpha_payload.write_text(
        json.dumps(
            {
                "action": "start",
                "signal": "fresh isolated claude install smoke",
                "route": {
                    "destination": "PRODUCT_PLANNING",
                    "attempt_id": "fresh-claude-install-route",
                },
                "operation_id": "fresh-claude-install-start",
                "run_id": "bpg2-run-fresh-claude-install-smoke",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    alpha_start = _run(
        [
            sys.executable,
            str(runner),
            "--operation",
            "alpha",
            "--payload-file",
            str(alpha_payload),
        ],
        config_dir=config_dir,
        cwd=project,
    )
    evidence.append(alpha_start)
    alpha_result = _json_output(alpha_start, "installed BPG 2.0 start")
    if (
        alpha_result.get("runtime") != "BPG_2_0_ALPHA"
        or alpha_result.get("position") != "UNDERSTAND"
    ):
        raise RuntimeError("installed BPG 2.0 runtime did not start a fresh Run")

    state_in_project = (project / ".better-product-graph").is_dir()
    state_in_cache = any(
        path.name == ".better-product-graph" for path in installed_root.rglob(".better-product-graph")
    )
    state_location_ok = state_in_project and not state_in_cache
    project_state_before_rollback = _tree_fingerprint(project / ".better-product-graph")

    remove = _run(
        [str(claude_bin), "plugin", "uninstall", PLUGIN_ID],
        config_dir=config_dir,
    )
    evidence.append(remove)
    _require(remove, "plugin uninstall")
    after_remove, listed_after = _installed_entry(config_dir)
    evidence.append(listed_after)
    uninstall_ok = after_remove is None

    project_state_after_rollback = _tree_fingerprint(project / ".better-product-graph")
    project_state_preserved = project_state_after_rollback == project_state_before_rollback
    codex_after = _run(
        [
            sys.executable,
            str(repo_root / "scripts" / "build_plugin.py"),
            "--repo",
            str(repo_root),
            "--host",
            "codex",
            "--output",
            str(root / "codex-after"),
        ],
        config_dir=config_dir,
        cwd=repo_root,
    )
    evidence.append(codex_after)
    codex_after_manifest = _json_output(codex_after, "Codex artifact after Claude removal")
    codex_artifact_preserved = (
        codex_after_manifest.get("artifact_hash")
        == codex_before_manifest.get("artifact_hash")
    )
    rollback_ok = uninstall_ok and project_state_preserved and codex_artifact_preserved

    passed = uninstall_ok and rollback_ok and state_location_ok
    return {
        "status": "PASS" if passed else "FAIL",
        "host_id": "claude",
        "package": str(package),
        "package_sha256": "sha256:" + hashlib.sha256(package.read_bytes()).hexdigest(),
        "work_root": str(root),
        "claude_config_dir": str(config_dir),
        "isolated_claude_config_dir": True,
        "claude_cli_version": _run(
            [str(claude_bin), "--version"], config_dir=config_dir
        )["stdout"].strip(),
        "installed_path": str(installed_root),
        "installed_identity": identity,
        "strict_validate_status": "PASS",
        "plugin_contract_status": contract_result["contract_status"],
        "installed_entry_status": entry_result["status"],
        "installed_default_runtime": entry_result["runtime"],
        "installed_alpha_start_position": alpha_result["position"],
        "state_location_status": "PASS" if state_location_ok else "FAIL",
        "uninstall_status": "PASS" if uninstall_ok else "FAIL",
        "rollback_status": "PASS" if rollback_ok else "FAIL",
        "rollback_mode": "REMOVE_CLAUDE_TARGET",
        "project_state_before_rollback": project_state_before_rollback,
        "project_state_after_rollback": project_state_after_rollback,
        "project_state_preserved_status": "PASS" if project_state_preserved else "FAIL",
        "codex_artifact_before_rollback": codex_before_manifest.get("artifact_hash"),
        "codex_artifact_after_rollback": codex_after_manifest.get("artifact_hash"),
        "codex_artifact_preserved_status": "PASS" if codex_artifact_preserved else "FAIL",
        "authenticated_host_agent_status": "NOT_RUN",
        "auto_selection_status": "NOT_RUN",
        "product_golden_agent_status": "NOT_RUN",
        "claim_boundary": (
            "Distribution PASS does not prove authenticated Claude Host activation, "
            "normal-permission direct invocation, or product judgment."
        ),
        "commands": evidence,
    }


def _default_claude_bin() -> Path:
    found = shutil.which("claude")
    return Path(found) if found else Path("claude")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--claude-bin", type=Path, default=_default_claude_bin())
    parser.add_argument("--work-root", type=Path)
    args = parser.parse_args()
    try:
        result = claude_fresh_install_smoke(
            args.repo,
            args.package,
            claude_bin=args.claude_bin,
            work_root=args.work_root,
        )
    except Exception as error:  # noqa: BLE001 - smoke reports every failure as evidence
        result = {"status": "FAIL", "host_id": "claude", "error": str(error)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
