from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.alpha_runtime import BPG2AlphaController


ROOT = Path(__file__).resolve().parents[1]


class BPG2R7PlanningStatusAuthorityContractTests(unittest.TestCase):
    def test_new_planning_record_omits_volatile_runtime_position(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            controller = BPG2AlphaController(project)
            state = controller.start_run(
                signal="梳理一个本地产品规划问题",
                route={"destination": "PRODUCT_PLANNING", "attempt_id": "route-r7"},
                operation_id="start-r7",
                run_id="bpg2-run-r7-status-authority",
            )

            planning_record = (
                controller.run_path(state["run_id"]) / "planning-record.md"
            ).read_text(encoding="utf-8")

            self.assertIn("原始 Signal：梳理一个本地产品规划问题", planning_record)
            self.assertIn("产品事实与分析真源", planning_record)
            self.assertNotIn("当前阶段：", planning_record)
            self.assertNotIn("UNDERSTAND", planning_record)
            self.assertEqual(state["position"], "UNDERSTAND")
            self.assertEqual(
                controller.load_run(state["run_id"])["position"], "UNDERSTAND"
            )

    def test_agent_contract_keeps_live_progress_out_of_planning_record(self) -> None:
        instruction = (
            ROOT / "src" / "core" / "atomic-skills" / "product-planning" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(instruction.split())

        self.assertIn("durable product reasoning", normalized)
        self.assertIn("durable validation and product-effect boundaries", normalized)
        self.assertNotIn("Product Evals applicability", normalized)
        self.assertNotIn("Eval Pack", normalized)
        self.assertIn("current runtime position", normalized)
        self.assertIn("existing Controller status and exact receipts", normalized)
        self.assertIn("second human status document", normalized)
        self.assertIn("rewrite the Planning Record merely", normalized)

    def test_method_and_public_host_skills_share_the_same_authority_boundary(self) -> None:
        method = (
            ROOT
            / "docs"
            / "architecture"
            / "BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
        ).read_text(encoding="utf-8")
        self.assertIn("易变运行状态由 Controller status 动态投影", method)
        self.assertIn("不由主 Agent 手写进《产品规划主记录》", method)

        for host in ("codex", "claude"):
            skill = (
                ROOT
                / "host-adapters"
                / host
                / "public-skill"
                / "better-product-graph"
                / "SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "Do not rewrite `planning-record.md` merely to mirror the current Candidate, Review status, or next action",
                skill,
            )
            self.assertIn("sole live authority", skill)


if __name__ == "__main__":
    unittest.main()
