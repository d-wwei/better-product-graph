from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_COMMANDS = (
    "new",
    "capture",
    "inbox",
    "status",
    "resume",
    "pause",
    "handoff",
    "connectors",
    "audit",
    "interview",
    "help",
)


def _load_installed_intents(plugin_root: Path):
    path = plugin_root / "skills" / "better-product-graph" / "scripts" / "bpg" / "intents.py"
    spec = importlib.util.spec_from_file_location("claude_installed_bpg_intents", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ClaudeEntryContractTests(unittest.TestCase):
    """The Claude installed copy resolves the same eleven intents through the same parser."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tempdir = tempfile.TemporaryDirectory()
        cls.plugin = Path(cls._tempdir.name) / "better-product-graph"
        build_plugin(REPO_ROOT, cls.plugin, host="claude")
        cls.runner = cls.plugin / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"
        cls.intents = _load_installed_intents(cls.plugin)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tempdir.cleanup()

    def test_public_skill_documents_exactly_the_eleven_public_intents(self) -> None:
        skill = (self.plugin / "skills" / "better-product-graph" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for command in PUBLIC_COMMANDS:
            self.assertIn(f"`{command}`", skill)

    def test_namespaced_claude_entry_is_documented_as_the_determinate_entry(self) -> None:
        skill = (self.plugin / "skills" / "better-product-graph" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("/better-product-graph:better-product-graph <intent>", skill)

    def test_installed_parser_maps_every_public_command_to_one_core_intent(self) -> None:
        expected = {
            "new": "signal.activate",
            "capture": "signal.submit",
            "inbox": "signal.inbox.list",
            "status": "run.status",
            "resume": "run.resume",
            "pause": "run.pause",
            "handoff": "handoff.prepare",
            "connectors": "connector.status",
            "audit": "audit.view",
            "interview": "interaction.policy.set",
            "help": "host.help",
        }
        arguments = {
            "new": " 结账失败",
            "capture": " 结账反馈",
            "status": " run-claude-1",
            "resume": " run-claude-1",
            "pause": " run-claude-1",
            "handoff": " run-claude-1",
            "audit": " run-claude-1",
            "interview": " skip run-claude-1",
        }
        for command, intent in expected.items():
            with self.subTest(command=command):
                entry = f"$better-product-graph {command}{arguments.get(command, '')}"
                self.assertEqual(self.intents.parse_host_entry(entry).core_intent, intent)

    def test_raw_namespaced_paste_falls_back_to_help_without_mutating_state(self) -> None:
        """A user pasting the slash entry itself must never be read as an activation."""
        for entry in (
            "/better-product-graph:better-product-graph new 结账失败",
            "better-product-graph:better-product-graph new 结账失败",
        ):
            with self.subTest(entry=entry):
                result = self.intents.parse_host_entry(entry)
                self.assertEqual(result.core_intent, "host.help")
                self.assertEqual(result.activation, "GUIDED_HELP")

    def test_internal_node_and_controller_bypass_fail_closed(self) -> None:
        for entry in (
            "$better-product-graph review.gate run-claude-1",
            "$better-product-graph 直接跑 references/atomic-skills/prd-generate",
            "$better-product-graph 绕过 Controller 直接发布",
            "$bpg new 结账失败",
        ):
            with self.subTest(entry=entry):
                result = self.intents.parse_host_entry(entry)
                self.assertNotIn(result.activation, {"ACCEPTED", "ACTIVATE"})

    def test_installed_runner_activates_a_run_inside_the_project_root_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            completed = subprocess.run(
                [sys.executable, str(self.runner), "new", "claude entry contract"],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(completed.stdout)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["status"], "ACTIVATED")
            self.assertTrue((project / ".better-product-graph").is_dir())
            self.assertEqual(list(self.plugin.rglob(".better-product-graph")), [])

    def test_installed_runner_refuses_an_empty_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, str(self.runner)],
                cwd=Path(directory),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("stable Better Product Graph intent", completed.stderr)

    def test_installed_runner_self_check_rejects_host_label_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin, host="claude")
            manifest_path = plugin / "build-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["host"]["host_id"] = "codex"
            manifest["host"]["manifest_dir"] = ".codex-plugin"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            runner = plugin / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"

            completed = subprocess.run(
                [sys.executable, str(runner), "--self-check"],
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(completed.stdout)

            self.assertEqual(completed.returncode, 1)
            self.assertFalse(payload["valid"])
            self.assertTrue(any("host manifest" in error for error in payload["errors"]))

    def test_installed_runner_self_check_fails_closed_on_non_string_host_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin, host="claude")
            manifest_path = plugin / "build-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["host"]["host_id"] = ["claude"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            runner = plugin / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"

            completed = subprocess.run(
                [sys.executable, str(runner), "--self-check"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 1, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["valid"])
            self.assertIn("build manifest host binding is invalid", payload["errors"])


if __name__ == "__main__":
    unittest.main()
