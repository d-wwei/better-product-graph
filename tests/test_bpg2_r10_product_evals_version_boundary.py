from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


ROOT = Path(__file__).resolve().parents[1]


class BPG2ProductEvalsVersionBoundaryTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_method_keeps_evals_generator_out_of_2_0_ready(self) -> None:
        method = self.read(
            "docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
        )
        self.assertIn("2.0 不运行 Product Evals 适用性判断", method)
        self.assertIn("Ready 与 Local Handoff", method)
        self.assertIn("Product Evals 执行", method)
        self.assertIn("`NOT_RUN`", method)
        self.assertNotIn("`REQUIRED` 因此阻断 Ready", method)
        self.assertNotIn("`REQUIRED` 可以继续形成 PRD Candidate，但不能进入 Ready", method)

    def test_public_host_skills_do_not_request_future_evals_work(self) -> None:
        for host in ("codex", "claude"):
            with self.subTest(host=host):
                skill = self.read(
                    f"host-adapters/{host}/public-skill/better-product-graph/SKILL.md"
                )
                self.assertIn("BPG 2.0 does not run Product Evals applicability", skill)
                self.assertIn("Product Eval execution and product-effect validation", skill)
                self.assertIn("`NOT_RUN`", skill)
                self.assertNotIn("`REQUIRED` therefore blocks Ready", skill)
                self.assertNotIn("applicable Product Eval attachments", skill)

    def test_author_and_reviewer_work_orders_exclude_eval_pack(self) -> None:
        author = self.read("src/core/atomic-skills/prd-generate/INSTRUCTIONS.md")
        reviewer = self.read("src/core/atomic-skills/prd-review/INSTRUCTIONS.md")
        self.assertIn("BPG 2.0 does not perform Product Evals applicability", author)
        self.assertIn("does not receive or review an Eval Pack", reviewer)
        self.assertNotIn("one exact frozen PRD Candidate, its conditional Eval Pack", reviewer)
        self.assertNotIn('"evals": {', author)
        self.assertNotIn("benefit from a future Eval Pack", author)

    def test_template_and_output_contract_use_the_2_0_validation_boundary(self) -> None:
        template = self.read(
            "src/core/templates/general/PRD_TEMPLATE_v2.0-alpha.3.md"
        )
        contract = json.loads(
            self.read(
                "src/core/templates/general/PRD_OUTPUT_CONTRACT_v2.0-alpha.3.json"
            )
        )

        self.assertIn("可观察的验收", template)
        self.assertIn("尚未执行", template)
        self.assertIn("不得声称", template)
        self.assertNotIn("Product Evals 附件", template)
        self.assertIn(
            "ACCEPTANCE_AND_VALIDATION_BOUNDARY", contract["required_checklist"]
        )
        self.assertNotIn(
            "ACCEPTANCE_AND_PRODUCT_EVALS", contract["required_checklist"]
        )

    def test_runtime_has_no_2_0_evals_ready_blocker_or_eval_review_role(self) -> None:
        runtime = self.read("src/bpg/alpha_runtime.py")
        prd_contract = self.read("src/bpg/prd_contract.py")
        self.assertNotIn('unmet.append("PRODUCT_EVALS_APPLICABILITY")', runtime)
        self.assertNotIn('unmet.append("REQUIRED_PRODUCT_EVALS")', runtime)
        self.assertNotIn('"ACCEPTANCE_AND_PRODUCT_EVALS"', runtime)
        self.assertIn('"ACCEPTANCE_AND_VALIDATION_BOUNDARY"', runtime)
        self.assertNotIn("Eval Applicability contract is required", prd_contract)
        self.assertNotIn("allow_controller_reviewed_evals", prd_contract)

    def test_built_plugin_carries_the_repaired_2_0_author_contract(self) -> None:
        relatives = (
            Path("atomic-skills/prd-generate/INSTRUCTIONS.md"),
            Path("templates/general/PRD_TEMPLATE_v2.0-alpha.3.md"),
            Path("templates/general/PRD_OUTPUT_CONTRACT_v2.0-alpha.3.json"),
        )
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(ROOT, plugin)
            installed = plugin / "skills" / "better-product-graph" / "references"
            for relative in relatives:
                with self.subTest(relative=relative.as_posix()):
                    self.assertEqual(
                        (installed / relative).read_bytes(),
                        (ROOT / "src" / "core" / relative).read_bytes(),
                    )


if __name__ == "__main__":
    unittest.main()
