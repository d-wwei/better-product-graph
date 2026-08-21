from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.bpg.failpoints import begin_node_call, persist_node_dispatch
from src.bpg.state_controller import StateConflict, StateController, TransitionRejected


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


def ingest_result(attempt_id: str = "attempt-ingest-1") -> dict:
    return {
        "schema_version": "node-result.v1",
        "node_id": "signal.ingest",
        "attempt_id": attempt_id,
        "producer": {"kind": "DETERMINISTIC_PROGRAM", "component": "host-adapter"},
        "mechanical_output": {"status": "COMPLETED"},
        "artifact_refs": [],
    }


class StateControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.controller = StateController(self.project, GRAPH)
        self.run_id = "decision-run-001"
        self.controller.create_run(self.run_id, raw_signal="用户反馈结算页无法提交")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _dispatch_and_submit(self, attempt_id: str = "attempt-ingest-1") -> Path:
        persist_node_dispatch(self.controller, self.run_id, attempt_id)
        begin_node_call(self.controller, self.run_id, attempt_id)
        return self.controller.execute_mechanical_result(self.run_id, attempt_id)

    def test_create_run_persists_exact_input_before_current_state(self) -> None:
        state = self.controller.load_state(self.run_id)
        raw_ref = state["artifact_refs"]["raw_signal"]
        raw_path = self.project / raw_ref["path"]

        self.assertTrue(raw_path.is_file())
        self.assertEqual(json.loads(raw_path.read_text(encoding="utf-8"))["raw_text"], "用户反馈结算页无法提交")
        self.assertTrue(raw_ref["hash"].startswith("sha256:"))
        self.assertEqual(state["current_node"], "signal.ingest")
        self.assertEqual(state["state_version"], 1)

    def test_agent_claimed_gate_fields_are_rejected_without_state_change(self) -> None:
        before = self.controller.load_state(self.run_id)
        request = {
            "expected_state_version": before["state_version"],
            "attempt_id": "invented",
            "requested_node": "signal.prepare",
            "gate_passed": True,
        }

        with self.assertRaisesRegex(TransitionRejected, "gate_passed"):
            self.controller.transition(self.run_id, request)

        self.assertEqual(self.controller.load_state(self.run_id), before)

    def test_result_is_durable_before_controller_commits_transition(self) -> None:
        result_path = self._dispatch_and_submit()
        before = self.controller.load_state(self.run_id)

        after = self.controller.transition(
            self.run_id,
            {
                "expected_state_version": before["state_version"],
                "attempt_id": "attempt-ingest-1",
                "requested_node": "signal.prepare",
            },
        )

        self.assertTrue(result_path.is_file())
        self.assertEqual(after["last_completed_node"], "signal.ingest")
        self.assertEqual(after["current_node"], "signal.prepare")
        self.assertEqual(after["state_version"], before["state_version"] + 1)

    def test_cas_conflict_rejects_transition_and_keeps_current_state(self) -> None:
        self._dispatch_and_submit()
        before = self.controller.load_state(self.run_id)

        with self.assertRaises(StateConflict):
            self.controller.transition(
                self.run_id,
                {
                    "expected_state_version": 0,
                    "attempt_id": "attempt-ingest-1",
                    "requested_node": "signal.prepare",
                },
            )

        self.assertEqual(self.controller.load_state(self.run_id), before)

    def test_exit_zero_or_existing_file_cannot_mark_run_complete(self) -> None:
        fake = self.controller.run_path(self.run_id) / "artifacts" / "pretty-prd.md"
        fake.parent.mkdir(parents=True, exist_ok=True)
        fake.write_text("# 看起来完整的 PRD\n", encoding="utf-8")

        state = self.controller.load_state(self.run_id)

        self.assertNotIn(state["status"], {"READY", "RELEASED", "COMPLETED"})
        self.assertEqual(state["current_node"], "signal.ingest")

    def test_consumed_or_old_attempt_cannot_advance_a_new_current_node(self) -> None:
        self._dispatch_and_submit()
        state = self.controller.load_state(self.run_id)
        self.controller.transition(
            self.run_id,
            {
                "expected_state_version": state["state_version"],
                "attempt_id": "attempt-ingest-1",
                "requested_node": "signal.prepare",
            },
        )
        current = self.controller.load_state(self.run_id)

        with self.assertRaisesRegex(TransitionRejected, "current node"):
            self.controller.transition(
                self.run_id,
                {
                    "expected_state_version": current["state_version"],
                    "attempt_id": "attempt-ingest-1",
                    "requested_node": "signal.classify",
                },
            )


if __name__ == "__main__":
    unittest.main()
