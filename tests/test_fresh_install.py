from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.fresh_install_smoke import fresh_install_smoke
from scripts.package_plugin import package_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
CANDIDATE_VERSION = "2.0.2"


class FreshInstallTests(unittest.TestCase):
    def test_isolated_codex_home_install_contract_uninstall_and_rollback(self) -> None:
        if not CODEX.is_file():
            self.skipTest("bundled Codex CLI is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / f"better-product-graph-codex-{CANDIDATE_VERSION}.zip"
            package_report = package_plugin(REPO_ROOT, package)
            report = fresh_install_smoke(
                REPO_ROOT,
                package,
                codex_bin=CODEX,
                work_root=root / "smoke",
            )

            self.assertEqual(report["status"], "PASS")
            self.assertEqual(package_report["plugin"]["version"], CANDIDATE_VERSION)
            self.assertEqual(Path(report["package"]).name, package.name)
            self.assertEqual(report["isolated_codex_home"], True)
            self.assertTrue(report["installed_identity"]["valid"])
            self.assertEqual(report["plugin_contract_status"], "PASS")
            self.assertEqual(
                report["installed_entry_status"],
                "HOST_AGENT_ACTION_REQUIRED",
            )
            self.assertEqual(report["installed_default_runtime"], "BPG_2_0_ALPHA")
            self.assertEqual(report["installed_alpha_start_position"], "UNDERSTAND")
            self.assertEqual(report["uninstall_status"], "PASS")
            self.assertEqual(report["rollback_status"], "PASS")
            self.assertEqual(report["authenticated_host_agent_status"], "NOT_RUN")
            self.assertEqual(report["product_golden_agent_status"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
