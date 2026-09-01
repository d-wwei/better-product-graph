from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE = REPO_ROOT / "src" / "core"
EVAL_ROOT = REPO_ROOT / "evals" / "prd-status-authority-v0.1"


class BPG2R2StatusAuthorityContractTests(unittest.TestCase):
    def test_author_instruction_defines_three_authorities_and_status_drift_self_check(self) -> None:
        instruction = (
            CORE / "atomic-skills" / "prd-generate" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("STATUS_DRIFT_TEST", instruction)
        self.assertIn("Product Planning Record", instruction)
        self.assertIn("Controller status", instruction)
        self.assertIn("diagnoses", instruction)
        self.assertIn("actions", instruction)
        self.assertIn("current Candidate, Review, Ready, or Handoff status", instruction)
        self.assertIn("current Evals Generator capability or fulfillment", instruction)
        self.assertIn("product validation has not run", instruction)
        self.assertIn("must not claim its effect is", instruction)
        self.assertNotIn("REQUIRED Eval Pack must bind the final Candidate", instruction)
        self.assertIn("not a keyword scan", instruction)

    def test_writing_reviewer_owns_mutable_status_boundary_without_new_diagnosis(self) -> None:
        instruction = (
            CORE / "atomic-skills" / "prd-review" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")
        contract = json.loads(
            (
                CORE
                / "reviewer-profiles"
                / "prd-writing-reader-review-v3.1.1.json"
            ).read_text(encoding="utf-8")
        )

        self.assertIn("STATUS_DRIFT_TEST", instruction)
        self.assertIn("DOCUMENT_EXPERIENCE", instruction)
        self.assertIn("second mutable workflow truth", instruction)
        self.assertIn("stance=`REVISE`", instruction)
        self.assertIn("COMPLETION_SEMANTICS_AMBIGUOUS", instruction)
        self.assertIn("ARTIFACT_MATURITY_OVERCLAIM", instruction)
        self.assertIn("must not scan or fail keywords", instruction)

        boundary = contract["status_authority_boundary"]
        self.assertEqual(boundary["responsibility_id"], "DOCUMENT_EXPERIENCE")
        self.assertEqual(boundary["owner"], "WRITING_REVIEWER")
        self.assertEqual(
            boundary["diagnostic_categories"],
            ["COMPLETION_SEMANTICS_AMBIGUOUS", "ARTIFACT_MATURITY_OVERCLAIM"],
        )
        self.assertEqual(boundary["finding_stance"], "REVISE")
        self.assertEqual(boundary["keyword_scanning"], "FORBIDDEN")

    def test_eval_suite_pairs_mutable_status_failure_with_durable_rule_control(self) -> None:
        suite = json.loads((EVAL_ROOT / "suite.json").read_text(encoding="utf-8"))
        expected = json.loads((EVAL_ROOT / "expected.json").read_text(encoding="utf-8"))

        self.assertEqual(suite["schema_version"], "prd-status-authority-suite.v0.1")
        self.assertEqual(suite["agent_review_execution"], "NOT_RUN")
        self.assertIn("not Agent performance evidence", suite["claim_boundary"])
        self.assertEqual(
            [case["case_id"] for case in suite["cases"]],
            ["mutable-run-status", "durable-product-rule"],
        )
        self.assertEqual(
            expected["mutable-run-status"]["expected_review_stance"], "REVISE"
        )
        self.assertEqual(
            expected["durable-product-rule"]["expected_review_stance"], "PASS"
        )
        self.assertEqual(
            expected["mutable-run-status"]["allowed_diagnostic_categories"],
            ["COMPLETION_SEMANTICS_AMBIGUOUS", "ARTIFACT_MATURITY_OVERCLAIM"],
        )

        mutable = (EVAL_ROOT / "cases" / "mutable-run-status.md").read_text(
            encoding="utf-8"
        )
        durable = (EVAL_ROOT / "cases" / "durable-product-rule.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("当前 Candidate 写作稿", mutable)
        self.assertIn("待独立 Review", mutable)
        self.assertIn("本 Run 不能 Ready", mutable)
        self.assertIn("正式 Review 必须绑定最终 Candidate", durable)
        self.assertIn("未执行产品效果验证时不得声称效果已验证", durable)
        self.assertNotIn("本 Run", durable)

    def test_built_plugin_contains_the_same_author_reviewer_and_contract_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            installed = plugin / "skills" / "better-product-graph" / "references"

            for relative in (
                Path("atomic-skills/prd-generate/INSTRUCTIONS.md"),
                Path("atomic-skills/prd-review/INSTRUCTIONS.md"),
                Path("reviewer-profiles/prd-writing-reader-review-v3.1.1.json"),
            ):
                self.assertEqual(
                    (installed / relative).read_bytes(), (CORE / relative).read_bytes()
                )


if __name__ == "__main__":
    unittest.main()
