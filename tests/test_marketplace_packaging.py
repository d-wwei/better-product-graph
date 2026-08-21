from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_plugin import verify_installed_identity
from scripts.package_marketplace import package_marketplace


REPO_ROOT = Path(__file__).resolve().parents[1]


class MarketplacePackagingTests(unittest.TestCase):
    def _two_packages(self, root: Path, host: str) -> tuple[Path, Path, dict, dict]:
        first = root / f"{host}-a.zip"
        second = root / f"{host}-b.zip"
        first_report = package_marketplace(REPO_ROOT, first, host=host)
        second_report = package_marketplace(REPO_ROOT, second, host=host)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(first_report["sha256"], second_report["sha256"])
        return first, second, first_report, second_report

    def test_codex_marketplace_is_deterministic_and_installable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, _, report, _ = self._two_packages(root, "codex")
            extracted = root / "extracted"
            with zipfile.ZipFile(package) as archive:
                archive.extractall(extracted)
                names = set(archive.namelist())
            manifest = json.loads(
                (extracted / ".agents" / "plugins" / "marketplace.json").read_text()
            )
            plugin_root = extracted / "plugins" / "better-product-graph"

            self.assertEqual(manifest["name"], "better-product-graph")
            self.assertEqual(
                manifest["plugins"][0]["source"]["path"],
                "./plugins/better-product-graph",
            )
            self.assertIn("LICENSE", names)
            self.assertIn("NOTICE", names)
            self.assertIn("plugins/better-product-graph/.codex-plugin/plugin.json", names)
            self.assertNotIn("plugins/better-product-graph/.claude-plugin/plugin.json", names)
            self.assertTrue(verify_installed_identity(plugin_root)["valid"])
            self.assertEqual(report["plugin_path"], "plugins/better-product-graph")

    def test_claude_marketplace_is_deterministic_and_installable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, _, report, _ = self._two_packages(root, "claude")
            extracted = root / "extracted"
            with zipfile.ZipFile(package) as archive:
                archive.extractall(extracted)
                names = set(archive.namelist())
            manifest = json.loads(
                (extracted / ".claude-plugin" / "marketplace.json").read_text()
            )
            plugin_root = extracted / "claude-plugins" / "better-product-graph"

            self.assertEqual(manifest["name"], "better-product-graph")
            self.assertEqual(
                manifest["plugins"][0]["source"],
                "./claude-plugins/better-product-graph",
            )
            self.assertIn("LICENSE", names)
            self.assertIn("NOTICE", names)
            self.assertIn("claude-plugins/better-product-graph/.claude-plugin/plugin.json", names)
            self.assertNotIn("claude-plugins/better-product-graph/.codex-plugin/plugin.json", names)
            self.assertTrue(verify_installed_identity(plugin_root)["valid"])
            self.assertEqual(report["plugin_path"], "claude-plugins/better-product-graph")

    def test_both_hosts_share_one_core_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex = package_marketplace(REPO_ROOT, root / "codex.zip", host="codex")
            claude = package_marketplace(REPO_ROOT, root / "claude.zip", host="claude")
            self.assertEqual(codex["core_tree_fingerprint"], claude["core_tree_fingerprint"])
            self.assertNotEqual(codex["artifact_hash"], claude["artifact_hash"])


if __name__ == "__main__":
    unittest.main()
