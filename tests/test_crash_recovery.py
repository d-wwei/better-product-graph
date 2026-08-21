from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.failpoints import (
    CRASH_PHASES,
    InjectedCrash,
    begin_node_call,
    crash_at,
    mark_dispatch_unknown,
    persist_node_dispatch,
    recover_run,
)
from src.bpg.host_runtime import HostRuntime
from src.bpg.state_controller import StateController, TransitionRejected
from src.bpg.storage import atomic_write_json, read_json, sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


def ingest_result(attempt_id: str) -> dict:
    return {
        "schema_version": "node-result.v1",
        "node_id": "signal.ingest",
        "attempt_id": attempt_id,
        "producer": {"kind": "DETERMINISTIC_PROGRAM", "component": "host-adapter"},
        "mechanical_output": {"status": "COMPLETED"},
        "artifact_refs": [],
    }


class CrashRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.controller = StateController(self.project, GRAPH)
        self.run_id = "recovery-run-001"
        self.controller.create_run(self.run_id, raw_signal="恢复测试")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_matrix_names_all_required_crash_and_recovery_phases(self) -> None:
        self.assertEqual(
            CRASH_PHASES,
            (
                "before_node_call",
                "before_result_persist",
                "after_result_persist",
                "after_receipt_persist",
                "after_receipt_ledger",
                "after_decision_record",
                "after_owner_event",
                "after_state_event",
                "before_transition",
                "after_transition",
                "partial_fanout",
                "timeout",
                "late_result",
                "unknown_side_effect",
                "after_archive_publish",
                "after_release_staged",
                "after_release_event",
                "after_release_state",
                "after_release_publish",
                "after_candidate_finalize_staged",
                "after_candidate_finalize_event",
                "after_candidate_finalize_state",
                "after_candidate_finalize_publish",
            ),
        )

    def test_before_node_call_keeps_durable_plan_ready_once(self) -> None:
        persist_node_dispatch(self.controller, self.run_id, "attempt-1")

        with self.assertRaises(InjectedCrash):
            begin_node_call(
                self.controller,
                self.run_id,
                "attempt-1",
                failpoint=crash_at("before_node_call"),
            )

        first = recover_run(self.controller, self.run_id)
        second = recover_run(self.controller, self.run_id)
        self.assertEqual(first["status"], "READY_TO_DISPATCH")
        self.assertEqual(first, second)
        self.assertEqual(first["attempt_id"], "attempt-1")

    def test_unplanned_result_is_rejected_before_persistence(self) -> None:
        with self.assertRaisesRegex(TransitionRejected, "durable dispatch"):
            self.controller.execute_mechanical_result(self.run_id, "unplanned")

        self.assertFalse(self.controller._result_path(self.run_id, "unplanned").exists())

    def test_before_result_persist_never_redispatches_started_attempt(self) -> None:
        persist_node_dispatch(self.controller, self.run_id, "attempt-2")
        begin_node_call(self.controller, self.run_id, "attempt-2")

        with self.assertRaises(InjectedCrash):
            self.controller.execute_mechanical_result(
                self.run_id,
                "attempt-2",
                failpoint=crash_at("before_result_persist"),
            )

        recovery = recover_run(self.controller, self.run_id)
        self.assertEqual(recovery["status"], "WAITING_RESULT")
        self.assertFalse(recovery["redispatch_allowed"])

    def test_before_transition_recovers_exact_persisted_attempt(self) -> None:
        persist_node_dispatch(self.controller, self.run_id, "attempt-3")
        begin_node_call(self.controller, self.run_id, "attempt-3")
        self.controller.execute_mechanical_result(self.run_id, "attempt-3")
        state = self.controller.load_state(self.run_id)

        with self.assertRaises(InjectedCrash):
            self.controller.transition(
                self.run_id,
                {
                    "expected_state_version": state["state_version"],
                    "attempt_id": "attempt-3",
                    "requested_node": "signal.prepare",
                },
                failpoint=crash_at("before_transition"),
            )

        recovery = recover_run(self.controller, self.run_id)
        self.assertEqual(recovery["status"], "READY_TO_TRANSITION")
        self.assertEqual(recovery["attempt_id"], "attempt-3")
        self.assertEqual(self.controller.load_state(self.run_id)["current_node"], "signal.ingest")

    def test_after_result_persist_recovers_receipt_and_event_idempotently(self) -> None:
        persist_node_dispatch(self.controller, self.run_id, "attempt-result-crash")
        begin_node_call(self.controller, self.run_id, "attempt-result-crash")

        with self.assertRaises(InjectedCrash):
            self.controller.execute_mechanical_result(
                self.run_id,
                "attempt-result-crash",
                failpoint=crash_at("after_result_persist"),
            )

        first = recover_run(self.controller, self.run_id)
        second = recover_run(self.controller, self.run_id)
        result_path = self.controller._result_path(self.run_id, "attempt-result-crash")
        self.assertEqual(first["status"], "RECOVERED_RESULT")
        self.assertEqual(second["status"], "READY_TO_TRANSITION")
        self.assertTrue(result_path.with_name("result-receipt.json").is_file())

    def test_valid_host_artifact_recovers_after_result_persist_and_transitions(self) -> None:
        runtime = HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core")
        activated = runtime.handle_entry(
            "$better-product-graph new Host artifact crash recovery"
        )
        run_id = activated["run_id"]
        dispatch = activated["dispatch"]
        artifact_path = self.project / "prepared-signal-v1.json"
        atomic_write_json(
            artifact_path,
            {"schema_version": "prepared-signal.v1", "summary": "可恢复提交"},
        )
        result = {
            "schema_version": "node-result.v1",
            "node_id": "signal.prepare",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": {"prepared_signal": {"summary": "可恢复提交"}},
            "artifact_refs": [
                {
                    "role": "prepared_signal",
                    "path": artifact_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(artifact_path),
                    "version": 1,
                }
            ],
        }

        with self.assertRaises(InjectedCrash):
            runtime.submit_and_advance(
                run_id,
                result,
                requested_node="signal.classify",
                failpoint=crash_at("after_result_persist"),
            )

        recovered = recover_run(runtime.controller, run_id)
        self.assertEqual(recovered["status"], "RECOVERED_RESULT")
        state = runtime.controller.load_state(run_id)
        advanced = runtime.controller.transition(
            run_id,
            {
                "expected_state_version": state["state_version"],
                "attempt_id": dispatch["attempt_id"],
                "requested_node": "signal.classify",
            },
        )
        self.assertEqual(advanced["current_node"], "signal.classify")
        self.assertIn(dispatch["attempt_id"], advanced["consumed_attempts"])

    def test_after_transition_event_recovers_exact_journal_snapshot_idempotently(self) -> None:
        persist_node_dispatch(self.controller, self.run_id, "attempt-4")
        begin_node_call(self.controller, self.run_id, "attempt-4")
        self.controller.execute_mechanical_result(self.run_id, "attempt-4")
        state = self.controller.load_state(self.run_id)

        with self.assertRaises(InjectedCrash):
            self.controller.transition(
                self.run_id,
                {
                    "expected_state_version": state["state_version"],
                    "attempt_id": "attempt-4",
                    "requested_node": "signal.prepare",
                },
                failpoint=crash_at("after_transition"),
            )

        journal = read_json(
            self.controller._transaction_path(self.run_id, "transition-attempt-4")
        )
        self.assertEqual(journal["status"], "PREPARED")
        self.assertEqual(
            journal["event"]["after_state_hash"], journal["after_state_hash"]
        )
        recovered = recover_run(self.controller, self.run_id)
        again = recover_run(self.controller, self.run_id)
        self.assertEqual(recovered["status"], "RECOVERED_TRANSACTION")
        self.assertEqual(again["status"], "CONSISTENT")
        state = self.controller.load_state(self.run_id)
        self.assertEqual(state, journal["after_state"])
        self.assertEqual(state["current_node"], "signal.prepare")
        self.assertEqual(state["consumed_attempts"].count("attempt-4"), 1)
        self.assertEqual(self.controller.authoritative_read_barrier(self.run_id), state)

    def test_generic_state_event_transaction_recovers_exact_snapshot(self) -> None:
        before = self.controller.load_state(self.run_id)
        with self.assertRaises(InjectedCrash):
            self.controller.set_interview_policy(
                self.run_id,
                "skip",
                expected_state_version=before["state_version"],
                failpoint=crash_at("after_state_event"),
            )

        recovered = recover_run(self.controller, self.run_id)
        state = self.controller.load_state(self.run_id)
        self.assertEqual(recovered["status"], "RECOVERED_TRANSACTION")
        self.assertEqual(state["state_version"], before["state_version"] + 1)
        self.assertEqual(state["interaction_policy"], "NO_PM_INTERVIEW")

    def test_unknown_side_effect_requires_query_reconcile_and_no_retry(self) -> None:
        persist_node_dispatch(
            self.controller,
            self.run_id,
            "attempt-side-effect",
            side_effect="LOCAL_HANDOFF_WRITE",
        )
        begin_node_call(self.controller, self.run_id, "attempt-side-effect")
        mark_dispatch_unknown(self.controller, self.run_id, "attempt-side-effect")

        recovery = recover_run(self.controller, self.run_id)

        self.assertEqual(recovery["status"], "RECONCILE_REQUIRED")
        self.assertEqual(recovery["attempt_id"], "attempt-side-effect")
        self.assertFalse(recovery["redispatch_allowed"])


if __name__ == "__main__":
    unittest.main()
