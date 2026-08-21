from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import BuildError, build_plugin, verify_installed_identity


REPO_ROOT = Path(__file__).resolve().parents[2]
class MutableRepo:
    """One disposable copy of the exact source tree, so overlay defects fail in isolation."""

    def __init__(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name) / "repo"
        shutil.copytree(
            REPO_ROOT,
            self.root,
            ignore=shutil.ignore_patterns(
                ".git",
                "__pycache__",
                "artifacts",
                "audits",
                ".better-product-graph",
                ".product-audit",
                ".better-work",
                ".assistant",
            ),
        )

    def read_overlay(self) -> dict:
        return json.loads((self.root / "config" / "plugin-build.claude.json").read_text(encoding="utf-8"))

    def write_overlay(self, overlay: dict) -> None:
        (self.root / "config" / "plugin-build.claude.json").write_text(
            json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def cleanup(self) -> None:
        self._directory.cleanup()


class ClaudeBuildTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.output = Path(self.tempdir.name) / "better-product-graph"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_claude_target_builds_one_claude_manifest_and_one_public_skill(self) -> None:
        manifest = build_plugin(REPO_ROOT, self.output, host="claude")

        self.assertEqual(manifest["host"]["host_id"], "claude")
        self.assertEqual(manifest["host"]["manifest_dir"], ".claude-plugin")
        self.assertTrue((self.output / ".claude-plugin" / "plugin.json").is_file())
        self.assertFalse((self.output / ".codex-plugin").exists())
        self.assertEqual(
            sorted(path.relative_to(self.output).as_posix() for path in self.output.glob("skills/*/SKILL.md")),
            ["skills/better-product-graph/SKILL.md"],
        )
        plugin_manifest = json.loads(
            (self.output / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(plugin_manifest["name"], "better-product-graph")
        self.assertEqual(plugin_manifest["version"], manifest["plugin"]["version"])
        self.assertEqual(plugin_manifest["skills"], "./skills/")
        self.assertNotIn("interface", plugin_manifest)
        self.assertTrue(verify_installed_identity(self.output)["valid"])

    def test_both_hosts_share_one_core_tree_fingerprint(self) -> None:
        codex_output = Path(self.tempdir.name) / "codex"
        codex = build_plugin(REPO_ROOT, codex_output, host="codex")
        claude = build_plugin(REPO_ROOT, self.output, host="claude")

        self.assertEqual(codex["core_tree_fingerprint"], claude["core_tree_fingerprint"])
        self.assertNotEqual(codex["artifact_hash"], claude["artifact_hash"])

    def test_default_host_stays_codex_and_is_byte_stable_for_the_same_source(self) -> None:
        default_manifest = build_plugin(REPO_ROOT, self.output)
        repeated = build_plugin(REPO_ROOT, Path(self.tempdir.name) / "codex-repeat")

        self.assertEqual(default_manifest["host"]["host_id"], "codex")
        self.assertEqual(default_manifest["artifact_hash"], repeated["artifact_hash"])

    def test_claude_public_skill_is_the_declared_delta_over_the_default_host(self) -> None:
        overlay = json.loads(
            (REPO_ROOT / "config" / "plugin-build.claude.json").read_text(encoding="utf-8")
        )
        parity = overlay["host"]["public_skill_parity"]
        baseline = (REPO_ROOT / parity["baseline_source"]).read_text(encoding="utf-8")
        target = (REPO_ROOT / parity["target_source"]).read_text(encoding="utf-8")

        expected = baseline
        for substitution in parity["substitutions"]:
            expected = expected.replace(substitution["from"], substitution["to"])
        self.assertEqual(target, expected)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", target)
        self.assertIn("/better-product-graph:better-product-graph", target)
        self.assertIn("description: Use when ", target)

    def test_claude_runner_stays_byte_identical_to_the_default_host_runner(self) -> None:
        codex_runner = (
            REPO_ROOT / "host-adapters" / "codex" / "public-skill" / "better-product-graph" / "scripts" / "bpg_runner.py"
        ).read_bytes()
        claude_runner = (
            REPO_ROOT / "host-adapters" / "claude" / "public-skill" / "better-product-graph" / "scripts" / "bpg_runner.py"
        ).read_bytes()

        self.assertEqual(codex_runner, claude_runner)

    def test_runner_drift_fails_the_claude_build_closed(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        runner = (
            repo.root / "host-adapters" / "claude" / "public-skill" / "better-product-graph" / "scripts" / "bpg_runner.py"
        )
        runner.write_text(runner.read_text(encoding="utf-8") + "\n# host-only drift\n", encoding="utf-8")

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("byte-identical", str(raised.exception))

    def test_public_skill_drift_beyond_declared_substitutions_fails_closed(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        skill = repo.root / "host-adapters" / "claude" / "public-skill" / "better-product-graph" / "SKILL.md"
        skill.write_text(
            skill.read_text(encoding="utf-8").replace(
                "Better Product Graph turns a raw product Signal",
                "Claude Better Product Graph turns a raw product Signal",
            ),
            encoding="utf-8",
        )

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("declared substitutions", str(raised.exception))

    def test_overlay_that_declares_a_shared_key_fails_closed(self) -> None:
        for shared_key, value in (
            ("trees", []),
            ("derived_transforms", []),
            ("plugin_version", "9.9.9"),
            ("architecture_baseline", {"path": "x", "version": "x", "sha256": "x"}),
        ):
            with self.subTest(shared_key=shared_key):
                repo = MutableRepo()
                self.addCleanup(repo.cleanup)
                overlay = repo.read_overlay()
                overlay[shared_key] = value
                repo.write_overlay(overlay)

                with self.assertRaises(BuildError) as raised:
                    build_plugin(repo.root, self.output, host="claude")
                self.assertIn("shared keys", str(raised.exception))

    def test_overlay_that_declares_an_unknown_host_key_fails_closed(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        overlay = repo.read_overlay()
        overlay["host"]["extra_trees"] = ["src/core"]
        repo.write_overlay(overlay)

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("unknown host keys", str(raised.exception))

    def test_overlay_cannot_claim_another_host_identity_or_foreign_source_tree(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        overlay = repo.read_overlay()
        overlay["host"]["host_id"] = "codex"
        repo.write_overlay(overlay)
        with self.assertRaises(BuildError):
            build_plugin(repo.root, self.output, host="claude")

        overlay = repo.read_overlay()
        overlay["host"]["host_id"] = "claude"
        overlay["host"]["exact_files"][0]["source"] = (
            "host-adapters/codex/manifest/.codex-plugin/plugin.json"
        )
        repo.write_overlay(overlay)
        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("exact host adapter", str(raised.exception))

    def test_overlay_source_paths_cannot_escape_into_the_default_host(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        overlay = repo.read_overlay()
        host = overlay["host"]
        host["public_skill_source_root"] = (
            "host-adapters/claude/../codex/public-skill/better-product-graph"
        )
        host["exact_files"][1]["source"] = (
            "host-adapters/claude/public-skill/../../codex/"
            "public-skill/better-product-graph/SKILL.md"
        )
        host["exact_files"][2]["source"] = (
            "host-adapters/claude/public-skill/../../codex/"
            "public-skill/better-product-graph/scripts/bpg_runner.py"
        )
        repo.write_overlay(overlay)

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("path escapes", str(raised.exception))

    def test_overlay_source_paths_cannot_follow_an_intermediate_symlink(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        outside_directory = tempfile.TemporaryDirectory()
        self.addCleanup(outside_directory.cleanup)
        outside = Path(outside_directory.name)
        source_manifest = (
            repo.root
            / "host-adapters"
            / "claude"
            / "manifest"
            / ".claude-plugin"
            / "plugin.json"
        )
        (outside / "plugin.json").write_bytes(source_manifest.read_bytes())
        escape = repo.root / "host-adapters" / "claude" / "external-manifest"
        escape.symlink_to(outside, target_is_directory=True)
        overlay = repo.read_overlay()
        overlay["host"]["exact_files"][0]["source"] = (
            "host-adapters/claude/external-manifest/plugin.json"
        )
        repo.write_overlay(overlay)

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("symlink", str(raised.exception))

    def test_installed_identity_rejects_manifest_host_label_tamper(self) -> None:
        build_plugin(REPO_ROOT, self.output, host="codex")
        manifest_path = self.output / "build-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["host"]["host_id"] = "claude"
        manifest["host"]["manifest_dir"] = ".claude-plugin"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        identity = verify_installed_identity(self.output)

        self.assertFalse(identity["valid"])
        self.assertTrue(
            any("host manifest" in error for error in identity["errors"]),
            identity["errors"],
        )

    def test_missing_overlay_fails_closed_instead_of_falling_back_to_the_default_host(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        (repo.root / "config" / "plugin-build.claude.json").unlink()

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("overlay is missing", str(raised.exception))

    def test_unsupported_host_target_is_rejected(self) -> None:
        with self.assertRaises(BuildError):
            build_plugin(REPO_ROOT, self.output, host="gemini")

    def test_built_plugin_carries_no_build_machine_absolute_path(self) -> None:
        for host in ("codex", "claude"):
            with self.subTest(host=host):
                output = Path(self.tempdir.name) / f"scan-{host}"
                build_plugin(REPO_ROOT, output, host=host)
                for path in output.rglob("*"):
                    if path.is_file():
                        content = path.read_bytes()
                        self.assertNotIn(str(REPO_ROOT).encode(), content, path)
                        self.assertNotIn(b"/Users/", content, path)

    def test_os_metadata_files_never_break_or_enter_the_build(self) -> None:
        """Finder or Explorer visiting a source tree must not break either host build."""
        baseline = build_plugin(
            REPO_ROOT, Path(self.tempdir.name) / "noise-free-baseline"
        )["artifact_hash"]
        for noise in (
            REPO_ROOT / "src" / "core" / "graph" / "Thumbs.db",
            REPO_ROOT / "host-adapters" / "claude" / "public-skill" / "better-product-graph" / ".DS_Store",
        ):
            if noise.exists():
                continue
            noise.write_bytes(b"\x00os-metadata")
            self.addCleanup(noise.unlink)

        for host in ("codex", "claude"):
            with self.subTest(host=host):
                output = Path(self.tempdir.name) / f"noise-{host}"
                manifest = build_plugin(REPO_ROOT, output, host=host)
                built = {entry["path"] for entry in manifest["inventory"]}
                self.assertFalse(any(name.endswith((".DS_Store", "Thumbs.db")) for name in built))
        self.assertEqual(
            build_plugin(REPO_ROOT, Path(self.tempdir.name) / "noise-baseline")["artifact_hash"],
            baseline,
        )

    def test_an_undeclared_source_file_still_fails_the_build_closed(self) -> None:
        """Skipping OS noise must not weaken the allowlist for real unexpected files."""
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        (repo.root / "src" / "core" / "graph" / "stowaway.txt").write_text("x", encoding="utf-8")

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("not allowlisted", str(raised.exception))

    def test_leaked_source_absolute_path_fails_the_build_closed(self) -> None:
        repo = MutableRepo()
        self.addCleanup(repo.cleanup)
        leaked = repo.root / "src" / "core" / "policies" / "controller-policy.json"
        policy = json.loads(leaked.read_text(encoding="utf-8"))
        policy["leaked_source_root"] = "/Users/example/checkout"
        leaked.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        with self.assertRaises(BuildError) as raised:
            build_plugin(repo.root, self.output, host="claude")
        self.assertIn("absolute path", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
