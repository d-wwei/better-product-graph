"""Installed-Skill callable entry; this is a Host adapter, not a standalone platform."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .git_preflight import GitPreflight, preflight_project, validate_project_root
from .host_runtime import HostRuntime
from .storage import read_json
from .template_packs import install_template_pack as install_pack


def _plugin_root(skill_root: Path) -> Path:
    return skill_root.resolve().parents[1]


def _validate_project_boundary(project_root: Path, skill_root: Path) -> None:
    validate_project_root(
        project_root,
        forbidden_roots=(_plugin_root(skill_root),),
    )


def _preflight(project_root: Path, skill_root: Path) -> GitPreflight:
    checked = preflight_project(
        project_root,
        forbidden_roots=(_plugin_root(skill_root),),
    )
    if checked.status != "READY":
        raise RuntimeError(f"Git preflight failed: {checked.reason or checked.status}")
    return checked


def _with_preflight(checked: GitPreflight, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "git_preflight": {
            "status": checked.status,
            "project_root": str(checked.project_root),
            "repository_root": str(checked.repository_root) if checked.repository_root else None,
            "initialized": checked.initialized,
            "reason": checked.reason,
        },
    }


def handle_entry(
    project_root: Path,
    graph_manifest: Path,
    entry: str,
    *,
    skill_root: Path | None = None,
) -> dict[str, Any]:
    resolved_skill_root = skill_root or graph_manifest.resolve().parent.parent
    _validate_project_boundary(project_root, resolved_skill_root)
    return HostRuntime(project_root, graph_manifest, resolved_skill_root).handle_entry(entry)


def dispatch(
    project_root: Path,
    graph_manifest: Path,
    run_id: str,
    *,
    skill_root: Path | None = None,
) -> dict[str, Any]:
    resolved_skill_root = skill_root or graph_manifest.resolve().parent.parent
    checked = _preflight(project_root, resolved_skill_root)
    runtime = HostRuntime(project_root, graph_manifest, resolved_skill_root)
    envelope = runtime.dispatch_current(run_id)
    if envelope.get("status") in {
        "COMPLETED",
        "ADVANCED",
        "NOT_READY",
        "EVALS_FULFILLMENT_REQUIRED",
    }:
        return _with_preflight(checked, envelope)
    return _with_preflight(checked, {
        "status": "DISPATCHED",
        "run_id": run_id,
        "state": runtime.controller.load_state(run_id),
        "dispatch": envelope,
    })


def submit(
    project_root: Path,
    graph_manifest: Path,
    run_id: str,
    result: dict[str, Any],
    *,
    requested_node: str | None = None,
    skill_root: Path | None = None,
) -> dict[str, Any]:
    resolved_skill_root = skill_root or graph_manifest.resolve().parent.parent
    checked = _preflight(project_root, resolved_skill_root)
    return _with_preflight(
        checked,
        HostRuntime(project_root, graph_manifest, resolved_skill_root).submit_and_advance(
            run_id, result, requested_node=requested_node
        ),
    )


def owner_choice(
    project_root: Path,
    graph_manifest: Path,
    run_id: str,
    command: dict[str, Any],
    *,
    skill_root: Path | None = None,
) -> dict[str, Any]:
    resolved_skill_root = skill_root or graph_manifest.resolve().parent.parent
    checked = _preflight(project_root, resolved_skill_root)
    return _with_preflight(
        checked,
        HostRuntime(project_root, graph_manifest, resolved_skill_root).apply_owner_choice(
            run_id, command
        ),
    )


def fulfill_evals(
    project_root: Path,
    graph_manifest: Path,
    run_id: str,
    submission: dict[str, Any],
    *,
    skill_root: Path | None = None,
) -> dict[str, Any]:
    resolved_skill_root = skill_root or graph_manifest.resolve().parent.parent
    checked = _preflight(project_root, resolved_skill_root)
    return _with_preflight(
        checked,
        HostRuntime(project_root, graph_manifest, resolved_skill_root).fulfill_evals(
            run_id, submission
        ),
    )


def install_template_pack(
    project_root: Path,
    pack_root: Path,
    *,
    allow_version_change: bool = False,
    skill_root: Path,
) -> dict[str, Any]:
    """Install and activate external Template content as a project configuration action."""

    checked = _preflight(project_root, skill_root)
    manifest = read_json(_plugin_root(skill_root) / "build-manifest.json")
    plugin = manifest.get("plugin")
    if not isinstance(plugin, dict) or not isinstance(plugin.get("version"), str):
        raise RuntimeError("Installed BPG version binding is missing")
    return _with_preflight(
        checked,
        install_pack(
            project_root=project_root,
            templates_root=skill_root / "references" / "templates",
            pack_root=pack_root,
            bpg_version=plugin["version"],
            allow_version_change=allow_version_change,
        ),
    )
