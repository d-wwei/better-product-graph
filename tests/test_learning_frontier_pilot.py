from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]


class LearningFrontierPilotContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.plugin = Path(cls.temporary.name) / "plugin"
        build_plugin(REPO_ROOT, cls.plugin)
        cls.instruction = (
            cls.plugin
            / "skills"
            / "better-product-graph"
            / "references"
            / "atomic-skills"
            / "problem-learning"
            / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def _pilot_contract(self) -> dict:
        match = re.search(
            r"<!-- learning-frontier-pilot-contract -->\s*```json\s*(\{.*?\})\s*```",
            self.instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(
            match,
            "installed problem.learning.loop instruction must expose the Pilot contract",
        )
        return json.loads(match.group(1))

    def test_installed_contract_keeps_the_pilot_inside_the_existing_learning_node(self) -> None:
        contract = self._pilot_contract()

        self.assertEqual(contract["schema_version"], "learning-frontier-pilot.v1")
        self.assertEqual(contract["phase"], "PROMPT_ONLY_PILOT")
        self.assertEqual(contract["first_step"], "LIGHT_SHORT_CIRCUIT")
        self.assertEqual(contract["complex_path"]["recomputation_limit_per_attempt"], 1)
        self.assertEqual(
            contract["complex_path"]["waiting_scope"],
            "SAME_UNSUBMITTED_HOST_ATTEMPT_ONLY",
        )
        self.assertEqual(
            contract["complex_path"]["no_progress_rule"],
            "STOP_RECOMPUTING_IF_NO_NEW_EXACT_EVIDENCE_OR_MVU_UNCHANGED",
        )
        self.assertEqual(
            contract["stop_rule"],
            "CURRENT_ACTION_SUFFICIENT_NOT_FRONTIER_EMPTY",
        )
        self.assertEqual(
            contract["architecture_invariants"],
            {
                "new_top_level_nodes": 0,
                "new_artifact_types": 0,
                "new_state_schemas": 0,
                "new_dedicated_agents": 0,
                "real_cross_submit_wait_resume": False,
                "real_parallel_fanout": False,
            },
        )

    def test_installed_contract_exposes_one_mvu_and_source_routing_without_a_question_wall(self) -> None:
        contract = self._pilot_contract()
        interaction = contract["complex_path"]["pm_interaction"]

        self.assertEqual(interaction["core_question_count"], 1)
        self.assertEqual(
            interaction["visible_elements"],
            [
                "CURRENT_JUDGMENT",
                "WHY_NOW",
                "ONE_CORE_QUESTION",
                "AGENT_RECOMMENDATION",
                "STRONGEST_COUNTERARGUMENT",
                "FLIP_CONDITION",
            ],
        )
        self.assertEqual(
            contract["complex_path"]["source_routes"],
            [
                "PROJECT_KNOWLEDGE",
                "DECISION_HISTORY",
                "PRODUCT_DATA",
                "EXTERNAL_RESEARCH",
                "PROFESSIONAL_OWNER",
                "PM_PRIVATE_CONTEXT_OR_JUDGMENT",
                "USER_RESEARCH_OR_EXPERIMENT",
            ],
        )
        self.assertFalse(contract["complex_path"]["show_internal_frontier_to_pm"])

    def test_golden_matrix_has_one_executable_oracle_for_every_case(self) -> None:
        cases = self._pilot_contract()["golden_cases"]

        self.assertEqual([case["id"] for case in cases], [f"G{i}" for i in range(1, 8)])
        for case in cases:
            self.assertTrue(case["frozen_input"])
            self.assertTrue(case["event_sequence"])
            self.assertTrue(case["pass_oracle"])
            self.assertTrue(case["reject"])

        g6 = next(case for case in cases if case["id"] == "G6")
        self.assertEqual(
            g6["event_sequence"],
            ["INTERVIEW_SKIP", "INJECT_EXACT_EVIDENCE", "INTERVIEW_RESUME"],
        )
        self.assertEqual(g6["resume_question_count"], 1)
        self.assertEqual(g6["resume_question"], "LATEST_HIGHEST_VALUE_UNRESOLVED")
        self.assertFalse(g6["claims_cross_submit_wait_resume"])

    def test_official_pilot_output_uses_only_the_existing_learning_result_fields(self) -> None:
        contract = self._pilot_contract()
        output = contract["output_boundary"]

        self.assertEqual(
            output["allowed_persisted_reason_paths"],
            ["next_actions[].reason", "reasoning_usage.selection_rationale"],
        )
        self.assertEqual(output["runtime_closed_world_enforcement"], "NOT_CLAIMED")
        self.assertEqual(
            output["forbidden_private_fields"],
            ["dependency", "WAITING", "invalidated", "superseded"],
        )
        self.assertEqual(
            set(output["official_semantic_output_keys"]),
            {
                "learning_disposition",
                "runtime_status",
                "material_challenges",
                "interaction_policy",
                "next_actions",
                "reasoning_usage",
            },
        )


if __name__ == "__main__":
    unittest.main()
