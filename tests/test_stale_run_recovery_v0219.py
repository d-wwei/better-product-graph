from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.bpg.host_runtime import HostRuntime
from src.bpg.state_controller import StateConflict
from src.bpg.stale_recovery import (
    StaleRecoveryError,
    prepare_git_restoration,
    recovery_match_fingerprint,
)
from src.bpg.storage import (
    IntegrityError,
    atomic_write_json,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from tests.controller_fixtures import position_run_internal


REPO_ROOT = Path(__file__).resolve().parents[1]


class StaleRunRecoveryV0219Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        self.skill = self.project / "installed-skill"
        shutil.copytree(REPO_ROOT / "src" / "core", self.skill)
        self.graph = self.skill / "graph" / "manifest.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _stale_signal_prepare_runtime(
        self,
        *,
        register: bool,
        result_authority: bool = False,
        paused: bool = False,
    ) -> tuple[HostRuntime, str, str]:
        legacy = HostRuntime(self.project, self.graph, self.skill)
        activated = legacy.handle_entry("$better-product-graph new legacy recovery fixture")
        run_id = activated["run_id"]
        old_dispatch = activated["dispatch"]
        if paused:
            current = legacy.controller.load_state(run_id)
            legacy.controller.set_run_activity(
                run_id,
                "pause",
                expected_state_version=current["state_version"],
            )
        state = legacy.controller.load_state(run_id)
        old_graph = dict(state["graph_manifest"])
        old_instruction_hash = old_dispatch["instruction_hash"]

        if result_authority:
            attempt_root = (
                self.project
                / ".better-product-graph"
                / "runs"
                / run_id
                / "attempts"
                / old_dispatch["attempt_id"]
            )
            result_path = attempt_root / "node-result.json"
            atomic_write_json(result_path, {"unexpected": "durable result"})
            atomic_write_json(
                attempt_root / "result-receipt.json",
                {
                    "attempt_id": old_dispatch["attempt_id"],
                    "node_id": "signal.prepare",
                    "result_hash": sha256_file(result_path),
                },
            )

        instruction = self.skill / "atomic-skills" / "signal-intake" / "INSTRUCTIONS.md"
        instruction.write_bytes(instruction.read_bytes() + b"\nCurrent successor contract.\n")
        manifest = json.loads(self.graph.read_text(encoding="utf-8"))
        manifest["version"] = "0.1.0-alpha.test-successor"
        manifest["compatible_predecessors"] = []
        manifest["stale_recovery_contracts_ref"] = {
            "path": "graph/stale-recovery-contracts.json",
            "schema_version": "stale-run-recovery-registry.v1",
        }
        atomic_write_json(self.graph, manifest)

        registry = {
            "schema_version": "stale-run-recovery-registry.v1",
            "contracts": [],
        }
        if register:
            registry["contracts"].append(
                {
                    "recovery_id": "test-signal-prepare-v1",
                    "from_graph": old_graph,
                    "status": state["status"],
                    "current_node": "signal.prepare",
                    "state_fingerprint": recovery_match_fingerprint(
                        self.project, state
                    ),
                    "retire_dispatches": [
                        {
                            "node_id": "signal.prepare",
                            "instruction_hash": old_instruction_hash,
                            "status": "DISPATCHED",
                            "count": 1,
                            "result_authority": "ABSENT",
                        }
                    ],
                    "resume_node": "signal.prepare",
                    "resume_last_completed_node": "signal.ingest",
                    "clear_ready_receipts": False,
                    "git_restore": None,
                    "message_zh": "旧版信号准备合同已安全退休，正在同一个 Run 重新派发。",
                }
            )
        registry_path = self.skill / "graph" / "stale-recovery-contracts.json"
        atomic_write_json(registry_path, registry)
        manifest = json.loads(self.graph.read_text(encoding="utf-8"))
        manifest["stale_recovery_contracts_ref"]["hash"] = sha256_file(registry_path)
        atomic_write_json(self.graph, manifest)
        return HostRuntime(self.project, self.graph, self.skill), run_id, old_dispatch["attempt_id"]

    def _project_bytes(self) -> dict[str, bytes]:
        return {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }

    def test_public_resume_retires_allowlisted_stale_dispatch_and_freshly_redispatches_same_run(self) -> None:
        runtime, run_id, old_attempt_id = self._stale_signal_prepare_runtime(
            register=True
        )

        resumed = runtime.handle_entry(f"$better-product-graph resume {run_id}")

        self.assertEqual(resumed["status"], "STALE_RUN_RECOVERED")
        self.assertEqual(resumed["run_id"], run_id)
        self.assertEqual(resumed["recovery_operation"], "recover-stale-run")
        self.assertIn("同一个 Run", resumed["message_zh"])
        self.assertEqual(resumed["dispatch"]["node_id"], "signal.prepare")
        self.assertNotEqual(resumed["dispatch"]["attempt_id"], old_attempt_id)
        self.assertEqual(
            resumed["dispatch"]["instruction_hash"],
            sha256_file(
                self.skill / "atomic-skills" / "signal-intake" / "INSTRUCTIONS.md"
            ),
        )
        state = runtime.controller.load_state(run_id)
        old = next(
            item for item in state["dispatch_attempts"]
            if item["attempt_id"] == old_attempt_id
        )
        self.assertEqual(old["status"], "RETIRED_STALE")
        self.assertEqual(state["run_id"], run_id)
        self.assertEqual(state["last_completed_node"], "signal.ingest")
        self.assertEqual(state["graph_manifest"]["version"], "0.1.0-alpha.test-successor")

    def test_unknown_stale_combination_remains_blocked_and_zero_write(self) -> None:
        runtime, run_id, _old_attempt_id = self._stale_signal_prepare_runtime(
            register=False
        )
        before = self._project_bytes()

        blocked = runtime.handle_entry(f"$better-product-graph resume {run_id}")

        self.assertEqual(blocked["status"], "BLOCKED_STALE")
        self.assertEqual(self._project_bytes(), before)

    def test_stale_recovery_cas_loss_is_zero_write(self) -> None:
        runtime, run_id, _old_attempt_id = self._stale_signal_prepare_runtime(
            register=True
        )
        context = runtime.controller.stale_recovery_context(run_id)
        assert context is not None
        before = self._project_bytes()

        with self.assertRaises(StateConflict):
            runtime.controller.recover_stale_run(
                run_id,
                recovery_id=context["recovery_id"],
                expected_state_version=context["state_version"] + 1,
            )

        self.assertEqual(self._project_bytes(), before)

    def test_allowlisted_dispatch_with_result_authority_remains_blocked_and_zero_write(self) -> None:
        runtime, run_id, _old_attempt_id = self._stale_signal_prepare_runtime(
            register=True,
            result_authority=True,
        )
        before = self._project_bytes()

        blocked = runtime.handle_entry(f"继续 {run_id}")

        self.assertEqual(blocked["status"], "BLOCKED_STALE")
        self.assertIn("result authority", " ".join(blocked["blockers"]))
        self.assertEqual(self._project_bytes(), before)

    def test_fresh_review_dispatch_projection_excludes_all_old_review_authority(self) -> None:
        candidate = {
            "role": "prd_candidate",
            "path": "artifacts/prds/archived/current/prd.md",
            "hash": "sha256:" + "1" * 64,
        }
        state = {
            "current_node": "review.parallel",
            "current_candidate_ref": candidate,
            "artifact_refs": {
                "candidate": candidate,
                "old_candidate": {
                    "role": "prd_candidate",
                    "path": "artifacts/prds/archived/old/prd.md",
                    "hash": "sha256:" + "2" * 64,
                },
                "aggregate": {
                    "role": "review_aggregate",
                    "path": "old/aggregate.json",
                    "hash": "sha256:" + "3" * 64,
                },
                "dispositions": {
                    "role": "review_dispositions",
                    "path": "old/dispositions.json",
                    "hash": "sha256:" + "4" * 64,
                },
                "writing": {
                    "role": "writing_coverage",
                    "path": "old/writing.json",
                    "hash": "sha256:" + "5" * 64,
                },
                "ready": {
                    "role": "audit_snapshot",
                    "path": "old/ready.json",
                    "hash": "sha256:" + "6" * 64,
                },
                "upstream": {
                    "role": "problem_definition",
                    "path": "upstream/problem.json",
                    "hash": "sha256:" + "7" * 64,
                },
            },
        }

        projected = HostRuntime._dispatch_artifact_refs(state)

        self.assertEqual(
            {(item["role"], item["hash"]) for item in projected},
            {
                ("prd_candidate", candidate["hash"]),
                ("problem_definition", "sha256:" + "7" * 64),
            },
        )

    def test_natural_language_resume_after_reconciled_crash_returns_fresh_work_order(self) -> None:
        runtime, run_id, old_attempt_id = self._stale_signal_prepare_runtime(
            register=True
        )
        context = runtime.controller.stale_recovery_context(run_id)
        assert context is not None

        def crash_after_event(phase: str) -> None:
            if phase == "after_state_event":
                raise RuntimeError("simulated crash")

        with self.assertRaisesRegex(RuntimeError, "simulated crash"):
            runtime.controller.recover_stale_run(
                run_id,
                recovery_id=context["recovery_id"],
                expected_state_version=context["state_version"],
                failpoint=crash_after_event,
            )

        restarted = HostRuntime(self.project, self.graph, self.skill)
        resumed = restarted.handle_entry(f"继续 {run_id}")

        self.assertEqual(resumed["status"], "RESUMED")
        self.assertEqual(resumed["dispatch"]["node_id"], "signal.prepare")
        self.assertNotEqual(resumed["dispatch"]["attempt_id"], old_attempt_id)
        events = (self.project / ".better-product-graph" / "runs" / run_id / "events.jsonl").read_text(encoding="utf-8")
        self.assertEqual(events.count('"event_type":"STALE_RUN_RECOVERY_COMMITTED"'), 1)

    def test_concurrent_natural_language_resume_recovers_once_and_returns_one_current_dispatch(self) -> None:
        first, run_id, old_attempt_id = self._stale_signal_prepare_runtime(
            register=True
        )
        second = HostRuntime(self.project, self.graph, self.skill)

        recovery_committed = threading.Event()
        second_read_stale_active_state = threading.Event()
        winner_dispatched = threading.Event()
        first_engine_handle = first.engine.handle
        first_dispatch = first.dispatch_current
        second_barrier = second.controller.authoritative_read_barrier

        def hold_winner_after_recovery(entry: str) -> dict:
            result = first_engine_handle(entry)
            if result.get("status") == "STALE_RUN_RECOVERED":
                recovery_committed.set()
                self.assertTrue(second_read_stale_active_state.wait(timeout=5))
            return result

        def mark_winner_dispatch(run: str) -> dict:
            result = first_dispatch(run)
            winner_dispatched.set()
            return result

        def hold_second_after_authority_read(run: str) -> dict:
            state = second_barrier(run)
            if recovery_committed.is_set():
                second_read_stale_active_state.set()
                self.assertTrue(winner_dispatched.wait(timeout=5))
            return state

        first.engine.handle = hold_winner_after_recovery
        first.dispatch_current = mark_winner_dispatch
        second.controller.authoritative_read_barrier = hold_second_after_authority_read

        with ThreadPoolExecutor(max_workers=2) as executor:
            winner = executor.submit(first.handle_entry, f"继续 {run_id}")

            def resume_after_exact_recovery() -> dict:
                self.assertTrue(recovery_committed.wait(timeout=5))
                return second.handle_entry(f"继续 {run_id}")

            loser = executor.submit(resume_after_exact_recovery)
            results = [winner.result(), loser.result()]

        self.assertEqual(
            {item["status"] for item in results},
            {"STALE_RUN_RECOVERED", "RESUMED"},
        )
        state = first.controller.load_state(run_id)
        current = [
            item
            for item in state["dispatch_attempts"]
            if item.get("node_id") == "signal.prepare"
            and item.get("attempt_id") != old_attempt_id
            and item.get("attempt_id") not in set(state["consumed_attempts"])
            and item.get("authorized_state_version") == state["state_version"]
        ]
        self.assertEqual(len(current), 1)
        events = (
            self.project
            / ".better-product-graph"
            / "runs"
            / run_id
            / "events.jsonl"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            events.count('"event_type":"STALE_RUN_RECOVERY_COMMITTED"'), 1
        )

    def test_concurrent_resume_of_paused_stale_run_treats_exact_legal_activation_as_idempotent(self) -> None:
        first, run_id, old_attempt_id = self._stale_signal_prepare_runtime(
            register=True,
            paused=True,
        )
        second = HostRuntime(self.project, self.graph, self.skill)

        first_reached_resume_write = threading.Event()
        second_finished_activation_and_dispatch = threading.Event()
        original_first_activity = first.controller.set_run_activity

        def hold_first_stale_resume_write(
            run: str,
            action: str,
            *,
            expected_state_version: int,
        ) -> dict:
            if action == "resume":
                first_reached_resume_write.set()
                self.assertTrue(
                    second_finished_activation_and_dispatch.wait(timeout=5)
                )
            return original_first_activity(
                run,
                action,
                expected_state_version=expected_state_version,
            )

        first.controller.set_run_activity = hold_first_stale_resume_write

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(first.handle_entry, f"继续 {run_id}")

            def resume_after_first_recovered_but_before_its_activation() -> dict:
                self.assertTrue(first_reached_resume_write.wait(timeout=5))
                try:
                    return second.handle_entry(f"继续 {run_id}")
                finally:
                    second_finished_activation_and_dispatch.set()

            second_future = executor.submit(
                resume_after_first_recovered_but_before_its_activation
            )
            results = [first_future.result(), second_future.result()]

        self.assertEqual(
            {item["status"] for item in results},
            {"STALE_RUN_RECOVERED", "RESUMED"},
        )
        state = first.controller.load_state(run_id)
        self.assertEqual(state["status"], "ACTIVE")
        self.assertIsNone(state["pause"])
        current = [
            item
            for item in state["dispatch_attempts"]
            if item.get("node_id") == "signal.prepare"
            and item.get("attempt_id") != old_attempt_id
            and item.get("status") == "DISPATCHED"
            and item.get("authorized_state_version") == state["state_version"]
            and item.get("authority_hash")
            == first.controller._dispatch_authority_hash(state)
        ]
        self.assertEqual(len(current), 1)
        events = (
            self.project
            / ".better-product-graph"
            / "runs"
            / run_id
            / "events.jsonl"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            events.count('"event_type":"STALE_RUN_RECOVERY_COMMITTED"'), 1
        )
        self.assertEqual(events.count('"event_type":"RUN_RESUMED"'), 1)

    def test_ordinary_resume_losing_to_recovery_activation_uses_same_exact_basis_proof(self) -> None:
        recovery_winner, run_id, old_attempt_id = (
            self._stale_signal_prepare_runtime(register=True, paused=True)
        )
        ordinary_loser = HostRuntime(self.project, self.graph, self.skill)

        recovery_reached_resume_write = threading.Event()
        ordinary_read_same_paused_basis = threading.Event()
        recovery_dispatched = threading.Event()
        original_recovery_activity = recovery_winner.controller.set_run_activity
        original_ordinary_activity = ordinary_loser.controller.set_run_activity
        original_recovery_dispatch = recovery_winner.dispatch_current

        def let_ordinary_capture_basis_before_recovery_activation(
            run: str,
            action: str,
            *,
            expected_state_version: int,
        ) -> dict:
            if action == "resume":
                recovery_reached_resume_write.set()
                self.assertTrue(ordinary_read_same_paused_basis.wait(timeout=5))
            return original_recovery_activity(
                run,
                action,
                expected_state_version=expected_state_version,
            )

        def hold_ordinary_write_until_recovery_dispatches(
            run: str,
            action: str,
            *,
            expected_state_version: int,
        ) -> dict:
            if action == "resume":
                ordinary_read_same_paused_basis.set()
                self.assertTrue(recovery_dispatched.wait(timeout=5))
            return original_ordinary_activity(
                run,
                action,
                expected_state_version=expected_state_version,
            )

        def mark_recovery_dispatch(run: str) -> dict:
            result = original_recovery_dispatch(run)
            recovery_dispatched.set()
            return result

        recovery_winner.controller.set_run_activity = (
            let_ordinary_capture_basis_before_recovery_activation
        )
        ordinary_loser.controller.set_run_activity = (
            hold_ordinary_write_until_recovery_dispatches
        )
        recovery_winner.dispatch_current = mark_recovery_dispatch

        with ThreadPoolExecutor(max_workers=2) as executor:
            winner = executor.submit(recovery_winner.handle_entry, f"继续 {run_id}")

            def ordinary_resume_after_recovery_commit() -> dict:
                self.assertTrue(recovery_reached_resume_write.wait(timeout=5))
                return ordinary_loser.handle_entry(f"继续 {run_id}")

            loser = executor.submit(ordinary_resume_after_recovery_commit)
            results = [winner.result(), loser.result()]

        self.assertEqual(
            {item["status"] for item in results},
            {"STALE_RUN_RECOVERED", "RESUMED"},
        )
        state = recovery_winner.controller.load_state(run_id)
        current = [
            item
            for item in state["dispatch_attempts"]
            if item.get("node_id") == "signal.prepare"
            and item.get("attempt_id") != old_attempt_id
            and item.get("status") == "DISPATCHED"
            and item.get("authorized_state_version") == state["state_version"]
            and item.get("authority_hash")
            == recovery_winner.controller._dispatch_authority_hash(state)
        ]
        self.assertEqual(len(current), 1)
        events = (
            self.project
            / ".better-product-graph"
            / "runs"
            / run_id
            / "events.jsonl"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            events.count('"event_type":"STALE_RUN_RECOVERY_COMMITTED"'), 1
        )
        self.assertEqual(events.count('"event_type":"RUN_RESUMED"'), 1)

    def test_paused_recovery_resume_cas_loss_rejects_unrelated_concurrent_change(self) -> None:
        first, run_id, _old_attempt_id = self._stale_signal_prepare_runtime(
            register=True,
            paused=True,
        )
        second = HostRuntime(self.project, self.graph, self.skill)
        original_first_activity = first.controller.set_run_activity

        def inject_unrelated_change_before_stale_resume(
            run: str,
            action: str,
            *,
            expected_state_version: int,
        ) -> dict:
            if action == "resume":
                current = second.controller.load_state(run)
                current = second.controller.set_run_activity(
                    run,
                    "resume",
                    expected_state_version=current["state_version"],
                )
                second.controller.set_interview_policy(
                    run,
                    "skip",
                    expected_state_version=current["state_version"],
                )
            return original_first_activity(
                run,
                action,
                expected_state_version=expected_state_version,
            )

        first.controller.set_run_activity = inject_unrelated_change_before_stale_resume

        with self.assertRaises(StateConflict):
            first.handle_entry(f"继续 {run_id}")

        state = first.controller.load_state(run_id)
        self.assertEqual(state["status"], "ACTIVE")
        self.assertEqual(state["interaction_policy"], "NO_PM_INTERVIEW")
        self.assertFalse(
            any(
                item.get("node_id") == "signal.prepare"
                and item.get("status") == "DISPATCHED"
                and item.get("authorized_state_version") == state["state_version"]
                for item in state["dispatch_attempts"]
            )
        )

    def test_ordinary_paused_resume_without_recovery_event_does_not_gain_idempotent_bypass(self) -> None:
        first = HostRuntime(self.project, self.graph, self.skill)
        activated = first.handle_entry("$better-product-graph new ordinary paused fixture")
        run_id = activated["run_id"]
        state = first.controller.load_state(run_id)
        first.controller.set_run_activity(
            run_id,
            "pause",
            expected_state_version=state["state_version"],
        )
        second = HostRuntime(self.project, self.graph, self.skill)
        original_first_activity = first.controller.set_run_activity

        def let_an_ordinary_resume_win_before_stale_write(
            run: str,
            action: str,
            *,
            expected_state_version: int,
        ) -> dict:
            if action == "resume":
                current = second.controller.load_state(run)
                second.controller.set_run_activity(
                    run,
                    "resume",
                    expected_state_version=current["state_version"],
                )
            return original_first_activity(
                run,
                action,
                expected_state_version=expected_state_version,
            )

        first.controller.set_run_activity = (
            let_an_ordinary_resume_win_before_stale_write
        )

        with self.assertRaises(StateConflict):
            first.handle_entry(f"继续 {run_id}")

    def test_git_restoration_is_closed_world_and_validates_mode_blob_hash_and_target_absence(self) -> None:
        repository = self.project / "git-project"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        subprocess.run(["git", "config", "user.name", "BPG Test"], cwd=repository, check=True)
        subprocess.run(["git", "config", "user.email", "bpg@example.test"], cwd=repository, check=True)
        target = repository / "artifacts" / "prds" / "archived" / "候选稿" / "需求 文档.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"exact candidate\n")
        target.chmod(0o644)
        subprocess.run(["git", "add", "--", target.relative_to(repository).as_posix()], cwd=repository, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repository, check=True)
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
            stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        blob = subprocess.run(
            ["git", "rev-parse", f"HEAD:{target.relative_to(repository).as_posix()}"],
            cwd=repository, check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()
        expected_hash = sha256_file(target)
        target.unlink()
        base = {
            "commit": commit,
            "tree_hash": "sha256:" + "0" * 64,
            "files": [{
                "path": target.relative_to(repository).as_posix(),
                "hash": expected_hash,
                "git_blob_oid": blob,
                "mode": "100644",
            }],
        }

        prepared = prepare_git_restoration(repository, base)
        self.assertEqual(prepared[0]["content"], b"exact candidate\n")

        cases = {
            "wrong mode": {**base, "files": [{**base["files"][0], "mode": "100755"}]},
            "wrong hash": {**base, "files": [{**base["files"][0], "hash": sha256_bytes(b"wrong")}]},
            "missing blob": {**base, "files": [{**base["files"][0], "git_blob_oid": "0" * 40}]},
            "missing commit": {**base, "commit": "0" * 40},
        }
        for label, restore in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(StaleRecoveryError):
                    prepare_git_restoration(repository, restore)
                self.assertFalse(target.exists())

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"conflict\n")
        with self.assertRaisesRegex(StaleRecoveryError, "target is not missing"):
            prepare_git_restoration(repository, base)
        target.unlink()
        os.symlink(repository / "outside", target)
        with self.assertRaises((IntegrityError, StaleRecoveryError, OSError)):
            prepare_git_restoration(repository, base)


if __name__ == "__main__":
    unittest.main()
