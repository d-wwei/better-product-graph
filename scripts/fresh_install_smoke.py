#!/usr/bin/env python3
"""Install one package into a disposable CODEX_HOME and run local-only smoke gates."""

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
PLUGIN_ID = f"better-product-graph@{MARKETPLACE_NAME}"


def _run(
    command: list[str],
    *,
    codex_home: Path,
    cwd: Path | None = None,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(codex_home)
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


def _json_output(result: dict[str, Any], label: str) -> dict[str, Any]:
    if result["returncode"] != 0:
        raise RuntimeError(f"{label} failed: {result['stderr'] or result['stdout']}")
    try:
        value = json.loads(result["stdout"])
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{label} did not return JSON") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} did not return a JSON object")
    return value


def _extract_package(package: Path, plugin_root: Path) -> None:
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if (
                pure.is_absolute()
                or ".." in pure.parts
                or stat.S_IFMT(mode) == stat.S_IFLNK
            ):
                raise ValueError(f"unsafe package member: {info.filename}")
        archive.extractall(plugin_root)
    manifest = plugin_root / ".codex-plugin" / "plugin.json"
    if not manifest.is_file():
        raise ValueError("package root does not contain .codex-plugin/plugin.json")


def fresh_install_smoke(
    repo_root: Path,
    package: Path,
    *,
    codex_bin: Path,
    work_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    package = package.resolve()
    codex_bin = codex_bin.resolve()
    if not package.is_file() or not codex_bin.is_file():
        raise ValueError("package and Codex binary must exist")
    root = (
        work_root.resolve()
        if work_root is not None
        else Path(tempfile.mkdtemp(prefix="bpg-fresh-install-")).resolve()
    )
    if root.exists() and any(root.iterdir()):
        raise ValueError("fresh install work root must be empty")
    root.mkdir(parents=True, exist_ok=True)
    codex_home = root / "codex-home"
    marketplace = root / "marketplace"
    plugin_source = marketplace / "plugins" / "better-product-graph"
    project = root / "project"
    codex_home.mkdir()
    project.mkdir()
    plugin_source.mkdir(parents=True)
    _extract_package(package, plugin_source)
    marketplace_manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    marketplace_manifest.parent.mkdir(parents=True)
    marketplace_manifest.write_text(
        json.dumps(
            {
                "name": MARKETPLACE_NAME,
                "interface": {"displayName": "Better Product Graph Local Smoke"},
                "plugins": [
                    {
                        "name": "better-product-graph",
                        "source": {
                            "source": "local",
                            "path": "./plugins/better-product-graph",
                        },
                        "policy": {
                            "installation": "AVAILABLE",
                            "authentication": "ON_USE",
                        },
                        "category": "Productivity",
                    }
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence: list[dict[str, Any]] = []
    add_marketplace = _run(
        [str(codex_bin), "plugin", "marketplace", "add", str(marketplace), "--json"],
        codex_home=codex_home,
    )
    evidence.append(add_marketplace)
    _json_output(add_marketplace, "marketplace add")
    install = _run(
        [str(codex_bin), "plugin", "add", PLUGIN_ID, "--json"],
        codex_home=codex_home,
    )
    evidence.append(install)
    installed = _json_output(install, "plugin add")
    installed_root = Path(installed["installedPath"]).resolve()
    try:
        installed_root.relative_to(codex_home)
    except ValueError as error:
        raise RuntimeError("Codex installed outside the isolated CODEX_HOME") from error
    runner = installed_root / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"
    self_check = _run(
        [sys.executable, str(runner), "--self-check"], codex_home=codex_home
    )
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
        codex_home=codex_home,
    )
    evidence.append(contract)
    contract_result = _json_output(contract, "Plugin Contract")
    if contract_result.get("contract_status") != "PASS":
        raise RuntimeError("fresh installed Plugin Contract failed")
    entry = _run(
        [sys.executable, str(runner), "new", "fresh isolated install smoke"],
        codex_home=codex_home,
        cwd=project,
    )
    evidence.append(entry)
    entry_result = _json_output(entry, "installed entry")
    if entry_result.get("status") != "ACTIVATED":
        raise RuntimeError("installed entry did not activate a local Run")
    remove = _run(
        [str(codex_bin), "plugin", "remove", PLUGIN_ID, "--json"],
        codex_home=codex_home,
    )
    evidence.append(remove)
    _json_output(remove, "plugin remove")
    listed = _run(
        [str(codex_bin), "plugin", "list", "--json"], codex_home=codex_home
    )
    evidence.append(listed)
    listed_result = _json_output(listed, "plugin list after remove")
    uninstall_ok = not listed_result.get("installed") and not installed_root.exists()
    rollback = _run(
        [str(codex_bin), "plugin", "add", PLUGIN_ID, "--json"],
        codex_home=codex_home,
    )
    evidence.append(rollback)
    rolled_back = _json_output(rollback, "plugin rollback")
    rollback_root = Path(rolled_back["installedPath"]).resolve()
    rollback_check = _run(
        [
            sys.executable,
            str(rollback_root / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"),
            "--self-check",
        ],
        codex_home=codex_home,
    )
    evidence.append(rollback_check)
    rollback_identity = _json_output(rollback_check, "rollback self-check")
    rollback_ok = rollback_identity.get("valid") is True
    return {
        "status": "PASS" if uninstall_ok and rollback_ok else "FAIL",
        "package": str(package),
        "package_sha256": "sha256:" + hashlib.sha256(package.read_bytes()).hexdigest(),
        "work_root": str(root),
        "codex_home": str(codex_home),
        "isolated_codex_home": True,
        "installed_path": str(installed_root),
        "installed_identity": identity,
        "plugin_contract_status": contract_result["contract_status"],
        "installed_entry_status": entry_result["status"],
        "uninstall_status": "PASS" if uninstall_ok else "FAIL",
        "rollback_status": "PASS" if rollback_ok else "FAIL",
        "authenticated_host_agent_status": "NOT_RUN",
        "product_golden_agent_status": "NOT_RUN",
        "commands": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--codex-bin",
        type=Path,
        default=Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
    )
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = fresh_install_smoke(
            args.repo,
            args.package,
            codex_bin=args.codex_bin,
            work_root=args.work_root,
        )
    except Exception as error:
        result = {"status": "FAIL", "error": str(error)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
