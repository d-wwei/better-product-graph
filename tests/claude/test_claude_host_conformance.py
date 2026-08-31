from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from scripts.claude_fresh_install_smoke import claude_fresh_install_smoke
from scripts.package_plugin import package_plugin


REPO_ROOT = Path(__file__).resolve().parents[2]


def _claude_bin() -> Path | None:
    found = shutil.which("claude")
    return Path(found) if found else None


class ClaudeStaticHostConformanceTests(unittest.TestCase):
    """Static layer: the real Claude Code CLI accepts the built directory under --strict."""

    def setUp(self) -> None:
        self.claude = _claude_bin()
        if self.claude is None:
            self.skipTest("Claude Code CLI is unavailable")
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _validate(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.claude), "plugin", "validate", str(target), "--strict"],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_built_claude_directory_passes_strict_manifest_validation(self) -> None:
        output = self.root / "better-product-graph"
        build_plugin(REPO_ROOT, output, host="claude")

        completed = self._validate(output)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        # The CLI must have exercised our manifest, not merely scanned loose components.
        self.assertIn("Validating plugin manifest", completed.stdout)

    def test_default_codex_build_carries_no_claude_plugin_manifest(self) -> None:
        """Recorded W0 fact: CLI 2.1.237 validates a manifest-less component directory and
        exits 0, so `plugin validate` alone no longer separates the two host targets.
        Host identity is asserted structurally; the CLI only confirms it saw no manifest.
        """
        output = self.root / "codex-build"
        build_plugin(REPO_ROOT, output, host="codex")

        self.assertFalse((output / ".claude-plugin").exists())
        completed = self._validate(output)
        self.assertNotIn("Validating plugin manifest", completed.stdout)

    def test_strict_validation_actually_rejects_a_malformed_claude_manifest(self) -> None:
        """Guards the test above: prove the validator is a real gate, not a rubber stamp."""
        output = self.root / "broken"
        build_plugin(REPO_ROOT, output, host="claude")
        manifest_path = output / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["name"] = "Not A Valid Name!!"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        completed = self._validate(output)

        self.assertEqual(completed.returncode, 1, completed.stdout)

    def test_claude_cli_cannot_validate_a_zip_so_distribution_must_safe_extract_first(self) -> None:
        """Recorded W0 fact: `claude plugin validate` reads a manifest, never an archive."""
        package = self.root / "better-product-graph.zip"
        package_plugin(REPO_ROOT, package, host="claude")

        completed = subprocess.run(
            [str(self.claude), "plugin", "validate", str(package), "--strict"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)


class ClaudeDistributionHostConformanceTests(unittest.TestCase):
    """Distribution layer: real install into a disposable CLAUDE_CONFIG_DIR."""

    def test_isolated_claude_config_install_contract_and_remove_candidate_rollback(self) -> None:
        claude = _claude_bin()
        if claude is None:
            self.skipTest("Claude Code CLI is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "better-product-graph.zip"
            package_plugin(REPO_ROOT, package, host="claude")
            report = claude_fresh_install_smoke(
                REPO_ROOT,
                package,
                claude_bin=claude,
                work_root=root / "smoke",
            )

            self.assertEqual(report["status"], "PASS", report.get("error"))
            self.assertTrue(report["isolated_claude_config_dir"])
            self.assertTrue(report["installed_identity"]["valid"])
            self.assertEqual(report["strict_validate_status"], "PASS")
            self.assertEqual(report["plugin_contract_status"], "PASS")
            self.assertEqual(
                report["installed_entry_status"],
                "HOST_AGENT_ACTION_REQUIRED",
            )
            self.assertEqual(report["installed_default_runtime"], "BPG_2_0_ALPHA")
            self.assertEqual(report["installed_alpha_start_position"], "UNDERSTAND")
            self.assertEqual(report["state_location_status"], "PASS")
            self.assertEqual(report["uninstall_status"], "PASS")
            self.assertEqual(report["rollback_status"], "PASS")
            self.assertEqual(report["rollback_mode"], "REMOVE_CLAUDE_TARGET")
            self.assertEqual(report["project_state_preserved_status"], "PASS")
            self.assertEqual(report["codex_artifact_preserved_status"], "PASS")
            self.assertEqual(
                sum(
                    command["command"][1:3] == ["plugin", "install"]
                    for command in report["commands"]
                    if len(command.get("command", [])) >= 3
                ),
                1,
            )
            self.assertEqual(report["authenticated_host_agent_status"], "NOT_RUN")
            self.assertEqual(report["auto_selection_status"], "NOT_RUN")
            self.assertEqual(report["product_golden_agent_status"], "NOT_RUN")

    def test_installed_claude_copy_keeps_run_state_out_of_the_plugin_cache(self) -> None:
        claude = _claude_bin()
        if claude is None:
            self.skipTest("Claude Code CLI is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "better-product-graph.zip"
            package_plugin(REPO_ROOT, package, host="claude")
            report = claude_fresh_install_smoke(
                REPO_ROOT,
                package,
                claude_bin=claude,
                work_root=root / "smoke",
            )
            installed_root = Path(report["installed_path"])
            project = Path(report["work_root"]) / "project"

            self.assertTrue((project / ".better-product-graph").is_dir())
            for forbidden in (".better-product-graph", "artifacts"):
                self.assertEqual(list(installed_root.rglob(forbidden)), [])


if __name__ == "__main__":
    unittest.main()
