#!/usr/bin/env python3
"""Drive real authenticated Claude Code sessions against one built Claude Plugin.

Evidence discipline: the Host Agent is only the actuator. Every verdict is decided
from deterministic facts -- the exact `tool_use` commands the session issued, the
session's recorded permission denials, and the Controller state read straight off
disk -- never from the model's prose.

Normal permission mode only. This harness never passes --dangerously-skip-permissions
and explicitly overrides an ambient bypassPermissions setting with --permission-mode
default, then proves that override held with a negative control step.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_NAME = "better-product-graph"
NAMESPACED_ENTRY = f"/{SKILL_NAME}:{SKILL_NAME}"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class TrialError(RuntimeError):
    """Raised when the trial cannot produce evidence at all."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# Deterministic Controller state, read without any model in the loop
# --------------------------------------------------------------------------- #


def _runner_call(runner: Path, project: Path, *arguments: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(runner), *arguments],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"status": "NON_JSON", "stdout": completed.stdout[:2000]}
    payload["_returncode"] = completed.returncode
    return payload


def _discover_runs(project: Path) -> list[str]:
    runs = project / ".better-product-graph" / "runs"
    if not runs.is_dir():
        return []
    return sorted(path.name for path in runs.iterdir() if path.is_dir())


def _read_state(runner: Path, project: Path, run_id: str) -> dict[str, Any]:
    payload = _runner_call(runner, project, "status", run_id)
    state = payload.get("state")
    if not isinstance(state, dict):
        return {"unavailable": True, "raw_status": payload.get("status")}
    return {
        "run_id": state.get("run_id"),
        "current_node": state.get("current_node"),
        "state_version": state.get("state_version"),
        "status": state.get("status"),
        "last_completed_node": state.get("last_completed_node"),
        "consumed_attempts": state.get("consumed_attempts"),
        "artifact_refs": state.get("artifact_refs"),
        "audit_event_hashes": _audit_event_hashes(project, run_id),
    }


def _audit_event_hashes(project: Path, run_id: str) -> list[str] | None:
    path = project / ".better-product-graph" / "runs" / run_id / "events.jsonl"
    if not path.is_file():
        return None
    hashes: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            event_hash = event.get("event_hash")
            if not isinstance(event_hash, str):
                return None
            hashes.append(event_hash)
    except (OSError, json.JSONDecodeError):
        return None
    return hashes


def _project_snapshot(project: Path, plugin_dir: Path) -> dict[str, Any]:
    return {
        "runs": _discover_runs(project),
        "state_root_exists": (project / ".better-product-graph").is_dir(),
        "plugin_dir_run_artifacts": sorted(
            path.relative_to(plugin_dir).as_posix()
            for name in (".better-product-graph", "artifacts")
            for path in plugin_dir.rglob(name)
        ),
    }


# --------------------------------------------------------------------------- #
# One authenticated Claude Code session
# --------------------------------------------------------------------------- #


def _session(
    *,
    claude_bin: Path,
    plugin_dir: Path,
    project: Path,
    model: str,
    prompt: str,
    allowed_tools: list[str],
    disallowed_tools: list[str],
) -> dict[str, Any]:
    command = [
        str(claude_bin),
        "--plugin-dir",
        str(plugin_dir),
        "--permission-mode",
        "default",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "-p",
        prompt,
    ]
    if allowed_tools:
        command += ["--allowedTools", *allowed_tools]
    if disallowed_tools:
        command += ["--disallowedTools", *disallowed_tools]

    started = time.monotonic()
    with open(os.devnull, "rb") as devnull:
        completed = subprocess.run(
            command,
            cwd=project,
            stdin=devnull,
            text=True,
            capture_output=True,
            check=False,
        )
    elapsed = round(time.monotonic() - started, 2)

    tool_uses: list[dict[str, Any]] = []
    result: dict[str, Any] = {}
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    tool_uses.append({"name": block.get("name"), "input": block.get("input")})
        elif event.get("type") == "result":
            result = event

    recorded_command = list(command)
    recorded_command[recorded_command.index(prompt)] = "<prompt>"
    return {
        "command": recorded_command,
        "prompt": prompt,
        "allowed_tools": allowed_tools,
        "disallowed_tools": disallowed_tools,
        "returncode": completed.returncode,
        "elapsed_seconds": elapsed,
        "tool_uses": tool_uses,
        "permission_denials": result.get("permission_denials", []),
        "is_error": result.get("is_error"),
        "subtype": result.get("subtype"),
        "final_text": (result.get("result") or "")[:1200],
        "session_id": result.get("session_id"),
        "stderr": completed.stderr[-800:] if completed.returncode != 0 else "",
    }


def _bash_commands(session: dict[str, Any]) -> list[str]:
    return [
        str(use["input"].get("command", ""))
        for use in session["tool_uses"]
        if use.get("name") == "Bash" and isinstance(use.get("input"), dict)
    ]


def _runner_invoked(session: dict[str, Any], runner: Path, *, intent: str | None = None) -> bool:
    for command in _bash_commands(session):
        if str(runner) in command and (intent is None or intent in command):
            return True
    return False


def _namespaced_entry_observed(
    session: dict[str, Any], runner: Path, intent: str
) -> bool:
    """Require a real Host namespace input, not a prompt that supplies the runner path."""
    prompt = str(session.get("prompt", "")).strip()
    expected = f"{NAMESPACED_ENTRY} {intent}"
    return (
        (prompt == expected or prompt.startswith(expected + " "))
        and str(runner) not in prompt
        and _runner_invoked(session, runner, intent=intent)
    )


def _exact_recovery_position_preserved(
    before: dict[str, Any], after: dict[str, Any]
) -> bool:
    exact_fields = (
        "run_id",
        "current_node",
        "last_completed_node",
        "consumed_attempts",
        "artifact_refs",
    )
    if any(before.get(field) != after.get(field) for field in exact_fields):
        return False
    before_version = before.get("state_version")
    after_version = after.get("state_version")
    if not isinstance(before_version, int) or not isinstance(after_version, int):
        return False
    if after_version < before_version:
        return False
    before_audit = before.get("audit_event_hashes")
    after_audit = after.get("audit_event_hashes")
    return (
        isinstance(before_audit, list)
        and isinstance(after_audit, list)
        and after_audit[: len(before_audit)] == before_audit
    )


def _exact_state_unchanged(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return (
        _exact_recovery_position_preserved(before, after)
        and before.get("state_version") == after.get("state_version")
        and before.get("status") == after.get("status")
        and before.get("audit_event_hashes") == after.get("audit_event_hashes")
    )


def _permission_recovery_prompts(runner: Path, run_id: str) -> tuple[str, str]:
    exact_command = f"python3 {runner} resume {run_id}"
    denied = (
        f"Use the {NAMESPACED_ENTRY} skill to resume run {run_id}. "
        "Attempt this exact Bash command and report whether permission was denied:\n"
        f"{exact_command}"
    )
    regranted = (
        f"Permission is granted now. Retry the exact same {NAMESPACED_ENTRY} action:\n"
        f"{exact_command}\n"
        "Then report the current node."
    )
    return denied, regranted


def _permission_denial_preserved(
    pause_setup: dict[str, Any],
    before_denial: dict[str, Any],
    after_denial: dict[str, Any],
) -> bool:
    return (
        pause_setup.get("status") == "PAUSED"
        and before_denial.get("status") == "PAUSED"
        and _exact_state_unchanged(before_denial, after_denial)
    )


# --------------------------------------------------------------------------- #
# Trial
# --------------------------------------------------------------------------- #


def _verdict(passed: bool, *, partial: bool = False) -> str:
    if partial:
        return "PARTIAL"
    return "PASS" if passed else "FAIL"


def _denial_verdict(attempted: bool, denied: bool, executed: bool, state_held: bool) -> str:
    """A permission claim is only evidence when a real attempt was really denied.

    If the Host Agent never attempted the command, nothing was denied and unchanged
    state proves nothing -- that is INCONCLUSIVE, never PASS.
    """
    if not attempted:
        return "INCONCLUSIVE"
    if executed:
        return "FAIL"
    if not denied:
        return "INCONCLUSIVE"
    return "PASS" if state_held else "FAIL"


def run_trial(
    repo_root: Path,
    plugin_dir: Path,
    *,
    claude_bin: Path,
    model: str = DEFAULT_MODEL,
    work_root: Path | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    plugin_dir = plugin_dir.resolve()
    claude_bin = claude_bin.resolve()
    manifest_path = plugin_dir / "build-manifest.json"
    if not manifest_path.is_file():
        raise TrialError(f"plugin directory has no build manifest: {plugin_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("host", {}).get("host_id") != "claude":
        raise TrialError("authenticated trial requires a Claude host build")

    runner = plugin_dir / "skills" / SKILL_NAME / "scripts" / "bpg_runner.py"
    if not runner.is_file():
        raise TrialError(f"installed runner is missing: {runner}")
    installed_identity = _runner_call(runner, repo_root, "--self-check")
    if installed_identity.get("valid") is not True or installed_identity.get("_returncode") != 0:
        raise TrialError("authenticated trial requires a valid installed Claude artifact")
    allow = [f"Bash(python3 {runner}:*)"]

    root = (
        work_root.resolve()
        if work_root is not None
        else Path(tempfile.mkdtemp(prefix="bpg-claude-host-trial-")).resolve()
    )
    if root.exists() and any(root.iterdir()):
        raise TrialError("trial work root must be empty")
    root.mkdir(parents=True, exist_ok=True)
    project = root / "project"
    project.mkdir()

    steps: list[dict[str, Any]] = []

    def session(prompt: str, *, allowed: list[str] | None = None, denied: list[str] | None = None):
        return _session(
            claude_bin=claude_bin,
            plugin_dir=plugin_dir,
            project=project,
            model=model,
            prompt=prompt,
            allowed_tools=allowed if allowed is not None else allow,
            disallowed_tools=denied or [],
        )

    # -- T0 negative control: prove normal permission mode is actually in force ----
    # Phrased as a plain task. Priming the model with "even if blocked" makes it skip
    # the attempt entirely, which yields an inconclusive control rather than evidence.
    control = None
    for _ in range(2):
        control = session(
            "Run this Bash command and report the HTTP status code it prints:\n"
            "curl -s -o /dev/null -w '%{http_code}' https://example.com",
            allowed=[],
        )
        if any("curl" in command for command in _bash_commands(control)):
            break
    assert control is not None
    curl_attempted = any("curl" in command for command in _bash_commands(control))
    curl_denied = bool(control["permission_denials"])
    curl_executed = curl_attempted and not curl_denied
    control_verdict = _denial_verdict(curl_attempted, curl_denied, curl_executed, True)
    steps.append(
        {
            "id": "T0",
            "name": "normal-permission negative control",
            "proves": "the ambient bypassPermissions setting is overridden for this trial",
            "verdict": control_verdict,
            "curl_attempted": curl_attempted,
            "curl_denied": curl_denied,
            "curl_executed": curl_executed,
            "permission_denials": control["permission_denials"],
            "session": control,
        }
    )

    # -- T1 direct namespaced help reaches the installed runner -------------------
    before_help = _project_snapshot(project, plugin_dir)
    help_session = session(f"{NAMESPACED_ENTRY} help")
    after_help = _project_snapshot(project, plugin_dir)
    help_ok = (
        _namespaced_entry_observed(help_session, runner, "help")
        and after_help["runs"] == before_help["runs"]
        and not after_help["plugin_dir_run_artifacts"]
    )
    steps.append(
        {
            "id": "T1",
            "name": "namespaced direct entry reaches the installed runner",
            "proves": "PRD AC-01",
            "verdict": _verdict(help_ok),
            "namespaced_entry_observed": _namespaced_entry_observed(
                help_session, runner, "help"
            ),
            "runner_invoked": _runner_invoked(help_session, runner, intent="help"),
            "read_only": after_help["runs"] == before_help["runs"],
            "bash_commands": _bash_commands(help_session),
            "session": help_session,
        }
    )

    # -- T2 new creates a governed Run inside the project root only ---------------
    new_session = session(f"{NAMESPACED_ENTRY} new 结账失败率上升")
    after_new = _project_snapshot(project, plugin_dir)
    run_ids = after_new["runs"]
    new_ok = (
        _namespaced_entry_observed(new_session, runner, "new")
        and len(run_ids) == 1
        and after_new["state_root_exists"]
        and not after_new["plugin_dir_run_artifacts"]
    )
    steps.append(
        {
            "id": "T2",
            "name": "new activates a Run in the project root, not the plugin root",
            "proves": "PRD AC-02, AC-09",
            "verdict": _verdict(new_ok),
            "namespaced_entry_observed": _namespaced_entry_observed(
                new_session, runner, "new"
            ),
            "runs_created": run_ids,
            "plugin_dir_run_artifacts": after_new["plugin_dir_run_artifacts"],
            "bash_commands": _bash_commands(new_session),
            "session": new_session,
        }
    )
    if not run_ids:
        return _report(
            manifest, claude_bin, model, project, root, steps, plugin_dir,
            installed_identity=installed_identity,
            aborted="T2 created no Run",
        )
    run_id = run_ids[0]
    state_after_new = _read_state(runner, project, run_id)

    # -- T3 status -> pause -> resume keeps one exact position --------------------
    lifecycle_session = session(
        f"Use the {NAMESPACED_ENTRY} skill on run {run_id}. Execute exactly these three "
        "commands in order, and report each returned status:\n"
        f"python3 {runner} status {run_id}\n"
        f"python3 {runner} pause {run_id}\n"
        f"python3 {runner} resume {run_id}"
    )
    state_after_lifecycle = _read_state(runner, project, run_id)
    lifecycle_ok = (
        all(
            _runner_invoked(lifecycle_session, runner, intent=intent)
            for intent in ("status", "pause", "resume")
        )
        and state_after_lifecycle["current_node"] == state_after_new["current_node"]
        and state_after_lifecycle["run_id"] == run_id
        and state_after_lifecycle["status"] == "ACTIVE"
        and _exact_recovery_position_preserved(state_after_new, state_after_lifecycle)
    )
    steps.append(
        {
            "id": "T3",
            "name": "status -> pause -> resume preserves node, run id and refs",
            "proves": "PRD AC-04",
            "verdict": _verdict(lifecycle_ok),
            "state_before": state_after_new,
            "state_after": state_after_lifecycle,
            "bash_commands": _bash_commands(lifecycle_session),
            "session": lifecycle_session,
        }
    )

    # -- T4 a brand new OS process resumes the exact same node --------------------
    before_reopen = _read_state(runner, project, run_id)
    reopen_session = session(
        f"This is a fresh Claude Code process. Use the {NAMESPACED_ENTRY} skill to resume "
        f"run {run_id} by executing exactly:\n"
        f"python3 {runner} resume {run_id}\n"
        "Then report the current node it returned."
    )
    after_reopen = _read_state(runner, project, run_id)
    reopen_ok = (
        _runner_invoked(reopen_session, runner, intent="resume")
        and _exact_recovery_position_preserved(before_reopen, after_reopen)
        and after_reopen["status"] == "ACTIVE"
    )
    steps.append(
        {
            "id": "T4",
            "name": "new process resume keeps the exact node without re-consuming attempts",
            "proves": "PRD AC-05",
            "verdict": _verdict(reopen_ok),
            "state_before": before_reopen,
            "state_after": after_reopen,
            "session": reopen_session,
        }
    )

    # -- T5 a denied permission must not advance formal state ---------------------
    pause_setup = _runner_call(runner, project, "pause", run_id)
    before_denial = _read_state(runner, project, run_id)
    denial_prompt, regrant_prompt = _permission_recovery_prompts(runner, run_id)
    denial_session = None
    for _ in range(2):
        denial_session = session(
            denial_prompt,
            # No allow rule, and NOT --disallowedTools: removing the tool would be tool
            # absence, not a denied permission request, and never reaches
            # permission_denials. A normal-mode denial is the faithful instrument.
            allowed=[],
        )
        if _runner_invoked(denial_session, runner, intent="resume"):
            break
    assert denial_session is not None
    after_denial = _read_state(runner, project, run_id)
    denial_attempted = _runner_invoked(denial_session, runner, intent="resume")
    denial_recorded = bool(denial_session["permission_denials"])
    state_held = _permission_denial_preserved(pause_setup, before_denial, after_denial)
    denial_executed = denial_attempted and not state_held
    steps.append(
        {
            "id": "T5",
            "name": "denied permission leaves formal state untouched",
            "proves": "PRD AC-08",
            "verdict": _denial_verdict(
                denial_attempted, denial_recorded, denial_executed, state_held
            ),
            "attempted": denial_attempted,
            "denial_recorded": denial_recorded,
            "state_held": state_held,
            "pause_setup_status": pause_setup.get("status"),
            "permission_denials": denial_session["permission_denials"],
            "state_before": before_denial,
            "state_after": after_denial,
            "session": denial_session,
        }
    )

    # -- T5b after re-authorization the Run resumes from the same node ------------
    regrant_session = session(regrant_prompt)
    after_regrant = _read_state(runner, project, run_id)
    regrant_ok = (
        _runner_invoked(regrant_session, runner, intent="resume")
        and _exact_recovery_position_preserved(before_denial, after_regrant)
        and before_denial.get("status") == "PAUSED"
        and after_regrant["status"] == "ACTIVE"
        and after_regrant["state_version"] > before_denial["state_version"]
    )
    steps.append(
        {
            "id": "T5b",
            "name": "re-authorized run resumes from the same node",
            "proves": "PRD AC-08 recovery half",
            "verdict": _verdict(regrant_ok),
            "state_after": after_regrant,
            "session": regrant_session,
        }
    )

    # -- T6 handoff with unmet conditions must not claim completion ---------------
    before_handoff = _read_state(runner, project, run_id)
    handoff_probe = _runner_call(runner, project, "handoff", run_id)
    handoff_session = session(
        f"Use the {NAMESPACED_ENTRY} skill to prepare a handoff for run {run_id} by executing "
        f"exactly:\n"
        f"python3 {runner} handoff {run_id}\n"
        "Then report verbatim what it returned. Do not claim anything was sent, received or approved."
    )
    after_handoff = _read_state(runner, project, run_id)
    claimed_sent = any(
        phrase in handoff_session["final_text"]
        for phrase in ("已发送", "已接收", "已批准", "has been sent", "was approved")
    )
    handoff_ok = (
        handoff_probe.get("status") == "NOT_READY"
        and _runner_invoked(handoff_session, runner, intent="handoff")
        and after_handoff["state_version"] == before_handoff["state_version"]
        and not claimed_sent
    )
    steps.append(
        {
            "id": "T6",
            "name": "unmet handoff returns unmet conditions without completion language",
            "proves": "PRD AC-06",
            "verdict": _verdict(handoff_ok),
            "runner_status": handoff_probe.get("status"),
            "runner_reason": handoff_probe.get("reason"),
            "claimed_external_completion": claimed_sent,
            "state_before": before_handoff,
            "state_after": after_handoff,
            "session": handoff_session,
        }
    )

    return _report(
        manifest,
        claude_bin,
        model,
        project,
        root,
        steps,
        plugin_dir,
        installed_identity=installed_identity,
    )


def _report(
    manifest: dict[str, Any],
    claude_bin: Path,
    model: str,
    project: Path,
    root: Path,
    steps: list[dict[str, Any]],
    plugin_dir: Path,
    *,
    installed_identity: dict[str, Any] | None = None,
    aborted: str | None = None,
) -> dict[str, Any]:
    version = subprocess.run(
        [str(claude_bin), "--version"], text=True, capture_output=True, check=False
    ).stdout.strip()
    verdicts = [step["verdict"] for step in steps]
    if aborted or "FAIL" in verdicts:
        status = "FAIL"
    elif "PARTIAL" in verdicts or "INCONCLUSIVE" in verdicts:
        status = "PARTIAL"
    else:
        status = "PASS"
    control = next((step for step in steps if step["id"] == "T0"), None)
    if control is not None and control["verdict"] != "PASS" and status == "PASS":
        # Without a real denial in the control, no permission claim here is trustworthy.
        status = "PARTIAL"
    return {
        "status": status,
        "evidence_level": "AUTHENTICATED_HOST_TRIAL",
        "host_id": "claude",
        "aborted": aborted,
        "timestamp": _now(),
        "claude_cli_version": version,
        "model": model,
        "permission_mode": "default",
        "dangerous_skip_permissions_used": False,
        "plugin_dir": str(plugin_dir),
        "artifact_hash": manifest.get("artifact_hash"),
        "core_tree_fingerprint": manifest.get("core_tree_fingerprint"),
        "plugin": manifest.get("plugin"),
        "installed_identity": installed_identity,
        "project_root": str(project),
        "work_root": str(root),
        "auto_selection_status": "NOT_RUN",
        "product_golden_status": "NOT_RUN",
        "claim_boundary": (
            "This trial proves exact namespaced Host inputs reached the installed runner, "
            "plus state location, lifecycle and "
            "permission behaviour under one exact Claude Code version and model. It does not "
            "prove natural-language auto-selection, nor product judgment quality."
        ),
        "steps": steps,
    }


def _default_claude_bin() -> Path:
    found = shutil.which("claude")
    return Path(found) if found else Path("claude")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin_dir", type=Path, help="a built Claude host plugin directory")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--claude-bin", type=Path, default=_default_claude_bin())
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--out", type=Path, help="write the full evidence JSON here")
    args = parser.parse_args()
    try:
        report = run_trial(
            args.repo,
            args.plugin_dir,
            claude_bin=args.claude_bin,
            model=args.model,
            work_root=args.work_root,
        )
    except Exception as error:  # noqa: BLE001 - every failure is reported as evidence
        report = {"status": "FAIL", "evidence_level": "AUTHENTICATED_HOST_TRIAL", "error": str(error)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        key: report.get(key)
        for key in ("status", "claude_cli_version", "model", "artifact_hash", "auto_selection_status", "error")
        if report.get(key) is not None
    }
    summary["steps"] = [
        {"id": step["id"], "verdict": step["verdict"], "name": step["name"]}
        for step in report.get("steps", [])
    ]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
