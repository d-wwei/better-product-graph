from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.bpg.host_runtime import HostRuntime
from src.bpg.state_controller import StateController, TransitionRejected
from src.bpg.storage import IntegrityError, atomic_write_json


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"
CORE = REPO_ROOT / "src" / "core"


class PublicControllerEnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.runtime = HostRuntime(self.project, GRAPH, CORE)
        activated = self.runtime.handle_entry(
            "$better-product-graph new 用户无法理解结算失败原因"
        )
        self.run_id = activated["run_id"]
        self.dispatch = activated["dispatch"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _semantic_result(self, **changes: object) -> dict:
        result = {
            "schema_version": "node-result.v1",
            "node_id": "signal.prepare",
            "attempt_id": self.dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": self.dispatch["instruction_ref"],
            "instruction_hash": self.dispatch["instruction_hash"],
            "input_refs": self.dispatch["input_refs"],
            "input_hashes": self.dispatch["input_hashes"],
            "semantic_output": {"prepared_signal": {"summary": "结算失败解释不足"}},
            "artifact_refs": [],
        }
        result.update(changes)
        return result

    def test_future_schema_and_empty_semantic_output_fail_before_result_receipt(self) -> None:
        with self.assertRaisesRegex(TransitionRejected, "schema_version"):
            self.runtime.controller.submit_result(
                self.run_id, self._semantic_result(schema_version="node-result.v999")
            )
        with self.assertRaisesRegex(TransitionRejected, "semantic_output"):
            self.runtime.controller.submit_result(
                self.run_id, self._semantic_result(semantic_output={})
            )

    def test_fake_instruction_or_input_hash_fails_before_result_receipt(self) -> None:
        with self.assertRaisesRegex(TransitionRejected, "instruction"):
            self.runtime.controller.submit_result(
                self.run_id, self._semantic_result(instruction_hash="sha256:" + "0" * 64)
            )
        fake_inputs = dict(self.dispatch["input_hashes"])
        fake_inputs[self.dispatch["input_refs"][0]] = "sha256:" + "1" * 64
        with self.assertRaisesRegex(TransitionRejected, "input"):
            self.runtime.controller.submit_result(
                self.run_id, self._semantic_result(input_hashes=fake_inputs)
            )

    def test_result_receipt_is_rehashed_immediately_before_transition(self) -> None:
        result_path = self.runtime.controller.submit_result(
            self.run_id, self._semantic_result()
        )
        persisted = json.loads(result_path.read_text(encoding="utf-8"))
        persisted["semantic_output"]["prepared_signal"]["summary"] = "篡改后内容"
        atomic_write_json(result_path, persisted)
        state = self.runtime.controller.load_state(self.run_id)

        with self.assertRaisesRegex(TransitionRejected, "receipt hash"):
            self.runtime.controller.transition(
                self.run_id,
                {
                    "requested_node": "signal.classify",
                    "attempt_id": self.dispatch["attempt_id"],
                    "expected_state_version": state["state_version"],
                },
            )

    def test_invalid_run_state_schema_fails_on_load(self) -> None:
        state_path = self.runtime.controller._state_path(self.run_id)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["state_version"] = "future"
        state["interaction_policy"] = "IGNORE_PM"
        atomic_write_json(state_path, state)

        with self.assertRaisesRegex(IntegrityError, "run-state"):
            self.runtime.controller.load_state(self.run_id)


if __name__ == "__main__":
    unittest.main()
