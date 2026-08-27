from __future__ import annotations

import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_plugin import package_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_VERSION = "0.2.19"


class PackagingTests(unittest.TestCase):
    def test_rc4_release_metadata_preserves_failed_rc3_harness_without_semantic_pass(self) -> None:
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn(
            "## 0.2.18-rc.4 — 2026-08-26 — PRD Writing Reviewer v0.7 candidate",
            changelog,
        )
        rc4_section = changelog.split("## 0.2.18-rc.4", 1)[1].split(
            "## 0.2.18-rc.3", 1
        )[0]
        self.assertIn("Suite v0.7", rc4_section)
        self.assertIn("central durable project root", rc4_section)
        self.assertIn("`0.2.18-rc.3`", rc4_section)
        self.assertIn("`INVALID_HARNESS`", rc4_section)
        self.assertIn("Agent Eval remains `NOT_RUN`", rc4_section)
        self.assertIn("human-reader validation remains `NOT_RUN`", rc4_section)
        self.assertNotIn("Agent Eval PASS", rc4_section)

    def test_packaging_script_is_directly_executable_from_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "better-product-graph.zip"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "package_plugin.py"),
                    str(output),
                    "--repo",
                    str(REPO_ROOT),
                    "--json",
                ],
                cwd=Path(directory),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output.is_file())

    def test_two_packages_are_byte_identical_and_have_canonical_plugin_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / f"better-product-graph-codex-{CANDIDATE_VERSION}-a.zip"
            second = root / f"better-product-graph-codex-{CANDIDATE_VERSION}-b.zip"
            first_report = package_plugin(REPO_ROOT, first)
            second_report = package_plugin(REPO_ROOT, second)

            self.assertEqual(first_report["plugin"]["version"], CANDIDATE_VERSION)
            self.assertEqual(second_report["plugin"]["version"], CANDIDATE_VERSION)
            self.assertEqual(Path(first_report["path"]).name, first.name)
            self.assertEqual(Path(second_report["path"]).name, second.name)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_report["sha256"], second_report["sha256"])
            with zipfile.ZipFile(first) as archive:
                infos = archive.infolist()
                names = [item.filename for item in infos]
                self.assertEqual(names, sorted(names))
                self.assertIn(".codex-plugin/plugin.json", names)
                self.assertIn("LICENSE", names)
                self.assertIn("NOTICE", names)
                self.assertIn("skills/better-product-graph/SKILL.md", names)
                self.assertFalse(any(name.startswith("better-product-graph/") for name in names))
                self.assertFalse(any("__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in names))
                self.assertTrue(all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in infos))
                runner = archive.getinfo("skills/better-product-graph/scripts/bpg_runner.py")
                self.assertEqual((runner.external_attr >> 16) & 0o777, 0o755)
                self.assertTrue(all(stat.S_IFMT(item.external_attr >> 16) != stat.S_IFLNK for item in infos))


if __name__ == "__main__":
    unittest.main()
