from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import claude_authenticated_host_trial as trial


class ClaudeAuthenticatedTrialContractTests(unittest.TestCase):
    def test_session_evidence_redacts_prompt_without_duplicating_print_flag(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"type": "result", "result": "ok"}) + "\n",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            trial.subprocess, "run", return_value=completed
        ):
            result = trial._session(
                claude_bin=Path("/tmp/claude"),
                plugin_dir=Path("/tmp/plugin"),
                project=Path(directory),
                model="test-model",
                prompt=f"{trial.NAMESPACED_ENTRY} help",
                allowed_tools=["Bash(*)"],
                disallowed_tools=[],
            )

        self.assertEqual(result["command"].count("-p"), 1)
        self.assertEqual(result["command"][result["command"].index("-p") + 1], "<prompt>")

    def test_runner_only_instruction_is_not_namespaced_entry_evidence(self) -> None:
        runner = Path("/tmp/plugin/skills/better-product-graph/scripts/bpg_runner.py")
        command = f"python3 {runner} help"
        direct_python = {
            "prompt": f"Execute exactly:\n{command}",
            "tool_uses": [{"name": "Bash", "input": {"command": command}}],
        }
        namespaced = {
            "prompt": f"{trial.NAMESPACED_ENTRY} help",
            "tool_uses": [{"name": "Bash", "input": {"command": command}}],
        }

        self.assertFalse(trial._namespaced_entry_observed(direct_python, runner, "help"))
        self.assertTrue(trial._namespaced_entry_observed(namespaced, runner, "help"))

    def test_exact_recovery_position_requires_refs_attempts_and_audit_prefix(self) -> None:
        before = {
            "run_id": "run-1",
            "current_node": "signal.prepare",
            "last_completed_node": "signal.ingest",
            "state_version": 6,
            "consumed_attempts": ["attempt-1"],
            "artifact_refs": {"raw_signal": {"hash": "sha256:a"}},
            "audit_event_hashes": ["sha256:e1", "sha256:e2"],
        }
        after = {
            **before,
            "state_version": 8,
            "audit_event_hashes": ["sha256:e1", "sha256:e2", "sha256:e3"],
        }
        self.assertTrue(trial._exact_recovery_position_preserved(before, after))

        changed_refs = {**after, "artifact_refs": {"raw_signal": {"hash": "sha256:other"}}}
        rewritten_audit = {**after, "audit_event_hashes": ["sha256:forged", "sha256:e2"]}
        self.assertFalse(trial._exact_recovery_position_preserved(before, changed_refs))
        self.assertFalse(trial._exact_recovery_position_preserved(before, rewritten_audit))

    def test_permission_recovery_retries_the_exact_denied_resume(self) -> None:
        runner = Path("/tmp/plugin/skills/better-product-graph/scripts/bpg_runner.py")
        denied, regranted = trial._permission_recovery_prompts(runner, "run-1")
        exact_command = f"python3 {runner} resume run-1"

        self.assertIn(exact_command, denied)
        self.assertIn(exact_command, regranted)
        self.assertNotIn("second Better Product Graph run", denied)

    def test_permission_denial_requires_a_real_paused_resume_position(self) -> None:
        paused = {
            "run_id": "run-1",
            "current_node": "signal.prepare",
            "last_completed_node": "signal.ingest",
            "state_version": 9,
            "status": "PAUSED",
            "consumed_attempts": ["attempt-1"],
            "artifact_refs": {"raw_signal": {"hash": "sha256:a"}},
            "audit_event_hashes": ["sha256:e1"],
        }
        self.assertTrue(
            trial._permission_denial_preserved(
                {"status": "PAUSED"}, paused, dict(paused)
            )
        )
        active = {**paused, "status": "ACTIVE"}
        self.assertFalse(
            trial._permission_denial_preserved(
                {"status": "ACTIVE"}, active, dict(active)
            )
        )


if __name__ == "__main__":
    unittest.main()
