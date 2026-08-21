from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "evals" / "plugin-contract" / "run_contract.py"


class PluginContractSuiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plugin = self.root / "installed" / "better-product-graph"
        subprocess.run(
            ["python3", "scripts/build_plugin.py", "--output", str(self.plugin)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_suite(self, *, check: bool = True) -> tuple[int, dict]:
        completed = subprocess.run(
            ["python3", str(RUNNER), "--plugin-root", str(self.plugin)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            self.fail(completed.stderr or completed.stdout)
        return completed.returncode, json.loads(completed.stdout)

    def test_fresh_installed_copy_contract_passes_with_honest_host_evidence_scope(self) -> None:
        code, result = self.run_suite()
        self.assertEqual(code, 0)
        self.assertEqual(result["contract_status"], "PASS")
        self.assertEqual(result["evidence_level"], "FRESH_INSTALLED_COPY_CONTRACT")
        self.assertEqual(result["codex_host_runtime_status"], "NOT_RUN")
        self.assertTrue(result["installed_identity"]["valid"])
        required = {
            "discovery",
            "direct_activation",
            "indirect_activation",
            "follow_up_activation",
            "negative_activation",
            "eleven_intents_parity",
            "relative_resource_resolution",
            "unique_public_skill",
            "internal_entry_bypass",
            "installed_identity",
        }
        self.assertEqual(set(result["checks"]), required)
        self.assertTrue(all(value["status"] == "PASS" for value in result["checks"].values()))

    def test_all_eleven_direct_and_indirect_entries_resolve_to_same_core_intent(self) -> None:
        _, result = self.run_suite()
        parity = result["checks"]["eleven_intents_parity"]
        self.assertEqual(parity["count"], 11)
        self.assertEqual(parity["mismatches"], [])

    def test_repeated_contract_check_stays_valid_after_parser_bytecode_cache(self) -> None:
        first_code, first = self.run_suite()
        second_code, second = self.run_suite()
        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        self.assertEqual(first["contract_status"], "PASS")
        self.assertEqual(second["contract_status"], "PASS")
        self.assertTrue(second["installed_identity"]["valid"])

    def test_added_internal_skill_is_detected_as_a_failed_installed_contract(self) -> None:
        internal = self.plugin / "skills" / "internal-bypass" / "SKILL.md"
        internal.parent.mkdir(parents=True)
        internal.write_text("---\nname: internal-bypass\ndescription: forbidden\n---\n", encoding="utf-8")
        code, result = self.run_suite(check=False)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["contract_status"], "FAIL")
        self.assertEqual(result["checks"]["unique_public_skill"]["status"], "FAIL")
        self.assertEqual(result["checks"]["installed_identity"]["status"], "FAIL")

    def test_installed_identity_rejects_symlink_even_when_target_bytes_match(self) -> None:
        installed = (
            self.plugin
            / "skills"
            / "better-product-graph"
            / "scripts"
            / "bpg"
            / "intents.py"
        )
        external = self.root / "same-intents.py"
        external.write_bytes(installed.read_bytes())
        installed.unlink()
        installed.symlink_to(external)

        code, result = self.run_suite(check=False)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["contract_status"], "FAIL")
        self.assertEqual(result["checks"]["installed_identity"]["status"], "FAIL")

    def test_missing_internal_reference_fails_relative_resource_contract(self) -> None:
        required = (
            self.plugin
            / "skills"
            / "better-product-graph"
            / "references"
            / "reviewer-profiles"
            / "product-goal-fidelity-v0.1.json"
        )
        required.unlink()

        code, result = self.run_suite(check=False)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["checks"]["relative_resource_resolution"]["status"], "FAIL")
        self.assertEqual(result["checks"]["installed_identity"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
