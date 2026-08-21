from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.fresh_install_smoke import fresh_install_smoke
from scripts.package_plugin import package_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")


class FreshInstallTests(unittest.TestCase):
    def test_isolated_codex_home_install_contract_uninstall_and_rollback(self) -> None:
        if not CODEX.is_file():
            self.skipTest("bundled Codex CLI is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "better-product-graph.zip"
            package_plugin(REPO_ROOT, package)
            report = fresh_install_smoke(
                REPO_ROOT,
                package,
                codex_bin=CODEX,
                work_root=root / "smoke",
            )

            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["isolated_codex_home"], True)
            self.assertTrue(report["installed_identity"]["valid"])
            self.assertEqual(report["plugin_contract_status"], "PASS")
            self.assertEqual(report["installed_entry_status"], "ACTIVATED")
            self.assertEqual(report["uninstall_status"], "PASS")
            self.assertEqual(report["rollback_status"], "PASS")
            self.assertEqual(report["authenticated_host_agent_status"], "NOT_RUN")
            self.assertEqual(report["product_golden_agent_status"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
