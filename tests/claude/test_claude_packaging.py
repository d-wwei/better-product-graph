from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath

from scripts.package_plugin import package_plugin


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_RUNNER = REPO_ROOT / "evals" / "plugin-contract" / "run_contract.py"
CANDIDATE_VERSION = "2.0.2"


def _safe_extract(package: Path, destination: Path) -> None:
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if pure.is_absolute() or ".." in pure.parts or stat.S_IFMT(mode) == stat.S_IFLNK:
                raise ValueError(f"unsafe package member: {info.filename}")
        archive.extractall(destination)


class ClaudePackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_two_claude_packages_are_byte_identical_with_one_claude_plugin_root(self) -> None:
        first = self.root / f"better-product-graph-claude-{CANDIDATE_VERSION}-a.zip"
        second = self.root / f"better-product-graph-claude-{CANDIDATE_VERSION}-b.zip"
        first_report = package_plugin(REPO_ROOT, first, host="claude")
        second_report = package_plugin(REPO_ROOT, second, host="claude")

        self.assertEqual(first_report["plugin"]["version"], CANDIDATE_VERSION)
        self.assertEqual(second_report["plugin"]["version"], CANDIDATE_VERSION)
        self.assertEqual(Path(first_report["path"]).name, first.name)
        self.assertEqual(Path(second_report["path"]).name, second.name)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(first_report["sha256"], second_report["sha256"])
        self.assertEqual(first_report["host"], "claude")
        with zipfile.ZipFile(first) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            self.assertEqual(names, sorted(names))
            self.assertIn(".claude-plugin/plugin.json", names)
            self.assertIn("skills/better-product-graph/SKILL.md", names)
            self.assertFalse(any(name.startswith(".codex-plugin/") for name in names))
            self.assertFalse(any(name.startswith("better-product-graph/") for name in names))
            self.assertFalse(
                any("__pycache__" in name or name.endswith((".pyc", ".pyo")) for name in names)
            )
            self.assertTrue(all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in infos))
            self.assertTrue(
                all(stat.S_IFMT(item.external_attr >> 16) != stat.S_IFLNK for item in infos)
            )

    def test_codex_and_claude_packages_stay_distinct_artifacts(self) -> None:
        codex = self.root / "codex.zip"
        claude = self.root / "claude.zip"
        codex_report = package_plugin(REPO_ROOT, codex, host="codex")
        claude_report = package_plugin(REPO_ROOT, claude, host="claude")

        self.assertNotEqual(codex_report["sha256"], claude_report["sha256"])
        self.assertNotEqual(codex_report["artifact_hash"], claude_report["artifact_hash"])
        self.assertEqual(
            codex_report["core_tree_fingerprint"], claude_report["core_tree_fingerprint"]
        )

    def test_safe_extracted_claude_root_passes_the_installed_copy_contract(self) -> None:
        package = self.root / "claude.zip"
        package_plugin(REPO_ROOT, package, host="claude")
        extracted = self.root / "extracted"
        _safe_extract(package, extracted)

        completed = subprocess.run(
            [sys.executable, str(CONTRACT_RUNNER), "--plugin-root", str(extracted)],
            text=True,
            capture_output=True,
            check=False,
        )
        report = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(report["contract_status"], "PASS")
        self.assertEqual(report["host_id"], "claude")
        self.assertEqual(report["claude_host_runtime_status"], "NOT_RUN")
        self.assertEqual(report["product_golden_status"], "NOT_RUN")

    def test_installed_copy_contract_rejects_two_host_manifests_in_one_root(self) -> None:
        package = self.root / "claude.zip"
        package_plugin(REPO_ROOT, package, host="claude")
        extracted = self.root / "extracted"
        _safe_extract(package, extracted)
        codex_manifest = extracted / ".codex-plugin"
        codex_manifest.mkdir()
        (codex_manifest / "plugin.json").write_text(
            (extracted / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        completed = subprocess.run(
            [sys.executable, str(CONTRACT_RUNNER), "--plugin-root", str(extracted)],
            text=True,
            capture_output=True,
            check=False,
        )
        report = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report["contract_status"], "FAIL")
        self.assertIn("exactly one host plugin manifest", report["error"])

    def test_installed_copy_contract_rejects_build_manifest_host_label_tamper(self) -> None:
        package = self.root / "claude.zip"
        package_plugin(REPO_ROOT, package, host="claude")
        extracted = self.root / "extracted"
        _safe_extract(package, extracted)
        manifest_path = extracted / "build-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["host"]["host_id"] = "codex"
        manifest["host"]["manifest_dir"] = ".codex-plugin"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, str(CONTRACT_RUNNER), "--plugin-root", str(extracted)],
            text=True,
            capture_output=True,
            check=False,
        )
        report = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report["contract_status"], "FAIL")
        self.assertTrue(
            any("host manifest" in error for error in report["checks"]["installed_identity"]["errors"]),
            report,
        )

    def test_installed_copy_contract_rejects_tampered_code_before_importing_it(self) -> None:
        package = self.root / "claude.zip"
        package_plugin(REPO_ROOT, package, host="claude")
        extracted = self.root / "extracted"
        _safe_extract(package, extracted)
        intents = (
            extracted
            / "skills"
            / "better-product-graph"
            / "scripts"
            / "bpg"
            / "intents.py"
        )
        intents.write_text("raise RuntimeError('tampered installed code executed')\n", encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, str(CONTRACT_RUNNER), "--plugin-root", str(extracted)],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["contract_status"], "FAIL")
        self.assertEqual(report["checks"]["installed_identity"]["status"], "FAIL")
        self.assertNotIn("tampered installed code executed", completed.stderr)


if __name__ == "__main__":
    unittest.main()
