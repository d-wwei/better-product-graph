from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.state_controller import StateConflict, StateController
from src.bpg.storage import atomic_write_json


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class InterviewPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.controller = StateController(self.project, GRAPH)
        self.run_id = "run-interview-001"
        state = self.controller.create_run(self.run_id, raw_signal="访谈策略")
        state["unresolved"] = [
            {"id": "u-ai", "owner": "AI_RESEARCH", "priority": 100, "status": "UNRESOLVED"},
            {"id": "u-low", "owner": "PM_ONLY", "priority": 2, "status": "UNRESOLVED"},
            {"id": "u-high", "owner": "PM_ONLY", "priority": 9, "status": "UNRESOLVED"},
        ]
        state["current_interview_question"] = {"unknown_id": "u-high", "text": "one question"}
        atomic_write_json(self.controller._state_path(self.run_id), state)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_skip_during_interview_stops_question_but_preserves_unknowns(self) -> None:
        before = self.controller.load_state(self.run_id)
        after = self.controller.set_interview_policy(
            self.run_id, "skip", expected_state_version=before["state_version"]
        )
        self.assertEqual(after["interaction_policy"], "NO_PM_INTERVIEW")
        self.assertIsNone(after["current_interview_question"])
        self.assertEqual(after["unresolved"], before["unresolved"])

    def test_resume_chooses_highest_priority_unresolved_pm_only_unknown(self) -> None:
        state = self.controller.load_state(self.run_id)
        skipped = self.controller.set_interview_policy(
            self.run_id, "skip", expected_state_version=state["state_version"]
        )
        resumed = self.controller.set_interview_policy(
            self.run_id, "resume", expected_state_version=skipped["state_version"]
        )
        self.assertEqual(resumed["interaction_policy"], "ALLOW_PM_INTERVIEW")
        self.assertEqual(resumed["interaction_resume_target"], "u-high")

    def test_stale_interview_policy_write_is_rejected_by_cas(self) -> None:
        state = self.controller.load_state(self.run_id)
        self.controller.set_interview_policy(
            self.run_id, "skip", expected_state_version=state["state_version"]
        )
        with self.assertRaises(StateConflict):
            self.controller.set_interview_policy(
                self.run_id, "resume", expected_state_version=state["state_version"]
            )


if __name__ == "__main__":
    unittest.main()
