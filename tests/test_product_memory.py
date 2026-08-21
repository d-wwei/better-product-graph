from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.bpg.product_memory import persist_decision_proposal, record_owner_decision
from tests.test_owner_choice_routes import agent_submission


class ProductMemoryTests(unittest.TestCase):
    def test_decisions_evolve_append_only_with_current_plan_roadmap_and_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            first_proposal = persist_decision_proposal(project, "decision-evolve", "run-evolve", agent_submission())
            first = record_owner_decision(project, first_proposal, {
                "actor": {"kind": "OWNER", "id": "eli"}, "choice": "WAIT", "commit_timing": None,
                "outcome_details": {"WAIT": {"review_trigger": "new evidence"}},
            })
            second_proposal = persist_decision_proposal(project, "decision-evolve", "run-evolve", agent_submission())
            second = record_owner_decision(project, second_proposal, {
                "actor": {"kind": "OWNER", "id": "eli"}, "choice": "RESEARCH", "commit_timing": None,
                "outcome_details": {"RESEARCH": {"question": "是否持续发生"}},
            })
            self.assertEqual(first["version"], 1)
            self.assertEqual(second["version"], 2)
            self.assertEqual(second["supersedes"]["hash"], first["record_ref"]["hash"])
            self.assertTrue((project / first["record_ref"]["path"]).is_file())
            current = json.loads((project / ".better-product-graph/decisions/decision-evolve/current.json").read_text())
            self.assertEqual(current["record_ref"]["hash"], second["record_ref"]["hash"])
            self.assertTrue((project / ".better-product-graph/product-memory/product-plan.json").is_file())
            self.assertTrue((project / ".better-product-graph/product-memory/roadmap.json").is_file())
            changelog = (project / ".better-product-graph/product-memory/PRODUCT_CHANGELOG.jsonl").read_text().splitlines()
            self.assertEqual(len(changelog), 2)


if __name__ == "__main__":
    unittest.main()
