from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE_ROOT = REPO_ROOT / "evals" / "product-golden-v0.2"
LEGACY_HASHES = {
    "README.md": "69d0073d28832b2ba4a8e144e0ab091a2e5d791f785e4bc5e74dff6ccd7a8e64",
    "suite.yaml": "f927eca8d81d48502b08db17ddc630a70c080782b3ecd2caa783e41080bcd7a2",
    "cases/case-template.yaml": "0ae1a26a56fdb24b895768ef5601eb4d06f2b35effb8953158f8bcf5a11704fb",
    "cases/starter-adversarial.yaml": "5484f354a3f2b8c6be7b5b17829f927dc3e648b9994732fd24b57348f4e6abe1",
    "rubrics/product-spec-rubric.yaml": "0f6630d3f27d88c37e8aaa4d8f45b8642a8662614a153ff69166f986a98776ae",
    "schemas/eval-case.schema.json": "881a8e8db13d4d04949fd41b42ece6892f091a52f0bb5eeea5b3af717772538c",
    "schemas/eval-result.schema.json": "085f7113a92100a6246c373ec5ca170fccd2d2a6e50a54032dae0a8a4d74b8cf",
}


def run_contract(*args: str) -> dict:
    completed = subprocess.run(
        ["python3", str(SUITE_ROOT / "run_contract.py"), *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


class ProductGoldenSuiteTests(unittest.TestCase):
    def test_legacy_v01_bytes_are_unchanged_and_explicitly_document_only(self) -> None:
        legacy = REPO_ROOT / "evals" / "product-graph"
        for relative, expected in LEGACY_HASHES.items():
            actual = hashlib.sha256((legacy / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)
        disposition = (legacy / "LEGACY_DISPOSITION_v0.2.md").read_text(encoding="utf-8")
        self.assertIn("LEGACY / DOCUMENT-ONLY", disposition)
        self.assertIn("NOT A V1.4 ACCEPTANCE BASELINE", disposition)
        self.assertIn("不得记录 PASS", disposition)

    def test_contract_fixtures_pass_but_product_judgment_remains_not_run(self) -> None:
        result = run_contract()
        self.assertEqual(result["contract_status"], "PASS")
        self.assertEqual(result["agent_runtime_status"], "NOT_RUN")
        self.assertEqual(result["product_judgment_status"], "NOT_RUN")
        self.assertEqual(result["evidence_level"], "CONTRACT_FIXTURE_ONLY")
        self.assertEqual(set(result["cases"]), {"G01", "G03", "G04"})
        self.assertTrue(
            all(case["fixture_status"] == "PASS" for case in result["cases"].values())
        )
        self.assertTrue(
            all(case["product_judgment_status"] == "NOT_RUN" for case in result["cases"].values())
        )

    def test_runner_never_accepts_a_fixture_only_product_pass_claim(self) -> None:
        result = run_contract()
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn('"product_judgment_status": "PASS"', encoded)
        self.assertNotIn('"agent_runtime_status": "PASS"', encoded)

    def test_agent_workspace_excludes_evaluator_only_oracles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run_contract("--emit-agent-workspace", temporary)
            self.assertEqual(result["contract_status"], "PASS")
            emitted = {
                path.relative_to(temporary).as_posix()
                for path in Path(temporary).rglob("*")
                if path.is_file()
            }
            self.assertEqual(
                emitted,
                {
                    f"{case}/{name}"
                    for case in ("G01", "G03", "G04")
                    for name in ("input.yaml", "knowledge-snapshot.yaml", "pm-response-bank.yaml")
                },
            )
            self.assertFalse(any("expected-envelope" in path or "rubric" in path for path in emitted))


if __name__ == "__main__":
    unittest.main()
