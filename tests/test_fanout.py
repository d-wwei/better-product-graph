from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from src.bpg.fanout import (
    cancel_fanout_attempt,
    execute_fanout,
    join_fanout,
    persist_fanout_plan,
    recover_fanout,
)
from src.bpg.failpoints import InjectedCrash, crash_at
from src.bpg.state_controller import StateController
from src.bpg.storage import atomic_write_json, read_json, sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class FanoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.controller = StateController(self.project, GRAPH)
        self.run_id = "fanout-run-001"
        self.controller.create_run(self.run_id, raw_signal="review this")
        self.candidate_v1 = self._bind_candidate("candidate-v1.md", "# Candidate v1\n")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _bind_candidate(self, name: str, content: str) -> dict:
        path = self.controller.run_path(self.run_id) / "artifacts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        state = self.controller.load_state(self.run_id)
        return self.controller.bind_candidate(
            self.run_id,
            {
                "path": path.relative_to(self.controller.project_root).as_posix(),
                "hash": sha256_file(path),
                "version": state.get("candidate_version", 0) + 1,
            },
            expected_state_version=state["state_version"],
        )

    def _plan(self, *, timeout_seconds: float = 1.0, failpoint=None) -> dict:
        return persist_fanout_plan(
            self.controller,
            self.run_id,
            plan_id="review-plan-1",
            candidate_hash=self.candidate_v1["current_candidate_ref"]["hash"],
            roles=["product", "engineering"],
            required_roles=["product"],
            timeout_seconds=timeout_seconds,
            failpoint=failpoint,
        )

    def test_plan_and_every_pending_attempt_exist_before_first_worker_call(self) -> None:
        plan = self._plan()
        observed: list[tuple[bool, list[str]]] = []

        def worker(attempt: dict) -> dict:
            stored = read_json(Path(plan["plan_path"]))
            observed.append(
                (
                    Path(plan["plan_path"]).is_file(),
                    sorted(item["status"] for item in stored["attempts"]),
                )
            )
            return {"findings": [{"summary": attempt["role"]}]}

        result = execute_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            {"product": worker, "engineering": worker},
            max_workers=2,
        )

        self.assertTrue(all(exists for exists, _ in observed))
        self.assertTrue(all(len(statuses) == 2 for _, statuses in observed))
        self.assertEqual(result["status"], "EXECUTED")

    def test_plan_file_survives_crash_before_state_registration_without_duplication(self) -> None:
        with self.assertRaises(InjectedCrash):
            self._plan(failpoint=crash_at("after_state_event"))
        plan_path = (
            self.controller.run_path(self.run_id) / "fanout" / "review-plan-1" / "plan.json"
        )
        self.assertTrue(plan_path.is_file())

        recovered = self._plan()

        registered = self.controller.load_state(self.run_id)["fanout_plans"]
        self.assertEqual(recovered["plan_id"], "review-plan-1")
        self.assertEqual(len(registered), 1)
        self.assertEqual(registered[0]["hash"], sha256_file(Path(recovered["plan_path"])))

    def test_read_only_workers_run_concurrently_and_parent_persists_results(self) -> None:
        plan = self._plan()
        lock = threading.Lock()
        active = 0
        maximum_active = 0

        def worker(attempt: dict) -> dict:
            nonlocal active, maximum_active
            with lock:
                active += 1
                maximum_active = max(maximum_active, active)
            time.sleep(0.04)
            with lock:
                active -= 1
            return {"findings": [{"role": attempt["role"], "concern": "ADVISORY"}]}

        executed = execute_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            {"product": worker, "engineering": worker},
            max_workers=2,
        )

        self.assertGreaterEqual(maximum_active, 2)
        self.assertEqual({item["status"] for item in executed["attempts"]}, {"RESULT_PERSISTED"})
        for item in executed["attempts"]:
            self.assertTrue((self.project / item["result_ref"]["path"]).is_file())

    def test_join_uses_exact_persisted_worker_result_not_caller_replacement(self) -> None:
        plan = self._plan()

        def worker(attempt: dict) -> dict:
            return {"findings": [{"summary": f"persisted {attempt['role']} finding"}]}

        executed = execute_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            {"product": worker, "engineering": worker},
            max_workers=2,
        )
        attempt = next(item for item in executed["attempts"] if item["role"] == "product")

        joined = join_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            [
                {
                    "attempt_id": attempt["attempt_id"],
                    "candidate_hash": plan["candidate_hash"],
                    "result_ref": attempt["result_ref"],
                    "findings": [{"summary": "substituted join finding"}],
                }
            ],
        )

        self.assertEqual(joined["results"][0]["status"], "RESULT_MISMATCH")
        self.assertEqual(joined["accepted_findings"], [])

    def test_partial_fanout_recovery_does_not_repeat_completed_attempt(self) -> None:
        plan = self._plan()
        product_attempt = next(item for item in plan["attempts"] if item["role"] == "product")
        status_path = Path(plan["plan_path"]).with_name("status.json")
        status = read_json(status_path)
        next(item for item in status["attempts"] if item["role"] == "product")["status"] = "RESULT_PERSISTED"
        atomic_write_json(status_path, status)
        joined = join_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            [
                {
                    "attempt_id": product_attempt["attempt_id"],
                    "candidate_hash": plan["candidate_hash"],
                    "findings": [{"summary": "keep exact finding"}],
                }
            ],
        )

        recovery = recover_fanout(self.controller, self.run_id, plan["plan_id"])

        self.assertEqual(joined["status"], "PARTIAL")
        self.assertEqual(recovery["status"], "WAITING_FANOUT")
        self.assertIn(product_attempt["attempt_id"], recovery["completed_attempt_ids"])
        self.assertNotIn(product_attempt["attempt_id"], recovery["dispatchable_attempt_ids"])

    def test_pending_attempt_cannot_be_joined_before_dispatch_and_result_persistence(self) -> None:
        plan = self._plan()
        pending = plan["attempts"][0]

        joined = join_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            [
                {
                    "attempt_id": pending["attempt_id"],
                    "candidate_hash": plan["candidate_hash"],
                    "findings": [{"summary": "must not bypass dispatch"}],
                }
            ],
        )

        self.assertEqual(joined["results"][0]["status"], "NOT_DISPATCHED")
        self.assertEqual(joined["accepted_findings"], [])
        self.assertFalse(
            (self.project / ".better-product-graph" / "runs" / self.run_id / "fanout" / plan["plan_id"] / "joined").exists()
        )

    def test_timeout_is_durable_and_late_result_is_not_accepted(self) -> None:
        plan = self._plan(timeout_seconds=0.01)

        def slow_worker(attempt: dict) -> dict:
            time.sleep(0.08)
            return {"findings": [{"summary": attempt["role"]}]}

        executed = execute_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            {"product": slow_worker, "engineering": slow_worker},
            max_workers=2,
        )
        timed_out = executed["attempts"][0]
        disposition = join_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            [
                {
                    "attempt_id": timed_out["attempt_id"],
                    "candidate_hash": plan["candidate_hash"],
                    "findings": [{"summary": "arrived too late"}],
                }
            ],
        )

        self.assertIn("TIMED_OUT", {item["status"] for item in executed["attempts"]})
        self.assertEqual(disposition["results"][0]["status"], "LATE_STALE")

    def test_late_result_cannot_replace_new_current_candidate(self) -> None:
        plan = self._plan()
        attempt = plan["attempts"][0]
        new_state = self._bind_candidate("candidate-v2.md", "# Candidate v2\n")

        disposition = join_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            [
                {
                    "attempt_id": attempt["attempt_id"],
                    "candidate_hash": plan["candidate_hash"],
                    "findings": [{"summary": "old candidate finding"}],
                }
            ],
        )

        self.assertEqual(disposition["results"][0]["status"], "LATE_STALE")
        self.assertEqual(
            self.controller.load_state(self.run_id)["current_candidate_ref"],
            new_state["current_candidate_ref"],
        )

    def test_cancel_is_durable_and_disagreement_is_preserved_without_confidence_boost(self) -> None:
        plan = self._plan()
        cancelled = plan["attempts"][1]
        cancel_fanout_attempt(self.controller, self.run_id, plan["plan_id"], cancelled["attempt_id"])
        executed = execute_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            {
                "product": lambda _: {
                    "findings": [{"summary": "ship", "concern": "LOW"}]
                }
            },
        )
        accepted = next(item for item in executed["attempts"] if item["role"] == "product")

        joined = join_fanout(
            self.controller,
            self.run_id,
            plan["plan_id"],
            [
                {
                    "attempt_id": accepted["attempt_id"],
                    "candidate_hash": plan["candidate_hash"],
                    "result_ref": accepted["result_ref"],
                },
                {
                    "attempt_id": cancelled["attempt_id"],
                    "candidate_hash": plan["candidate_hash"],
                    "findings": [{"summary": "do not ship", "concern": "HIGH"}],
                },
            ],
        )

        self.assertEqual([item["status"] for item in joined["results"]], ["ACCEPTED", "LATE_STALE"])
        self.assertEqual(joined["accepted_findings"], [[{"summary": "ship", "concern": "LOW"}]])
        self.assertNotIn("confidence", joined)
        self.assertNotIn("agreement", joined)


if __name__ == "__main__":
    unittest.main()
