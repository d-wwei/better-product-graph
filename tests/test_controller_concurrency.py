from __future__ import annotations

import fcntl
import multiprocessing
import queue
import tempfile
import unittest
from pathlib import Path

from src.bpg.state_controller import StateController
from src.bpg.storage import append_event, verify_event_chain


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


def _mutate_interview(project: str, run_id: str, started, completed) -> None:
    controller = StateController(Path(project), GRAPH)
    started.set()
    try:
        state = controller.load_state(run_id)
        controller.set_interview_policy(
            run_id, "skip", expected_state_version=state["state_version"]
        )
        completed.put("OK")
    except Exception as error:  # subprocess evidence must cross process boundary
        completed.put(f"{type(error).__name__}:{error}")


def _append_worker(path: str, index: int, started, completed) -> None:
    started.set()
    try:
        append_event(
            Path(path),
            {"event_type": "CONCURRENT", "actor": "test-worker", "index": index},
        )
        completed.put("OK")
    except Exception as error:
        completed.put(f"{type(error).__name__}:{error}")


class ControllerConcurrencyTests(unittest.TestCase):
    def test_run_mutation_obeys_cross_process_advisory_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            controller = StateController(project, GRAPH)
            controller.create_run("run-lock", raw_signal="lock")
            lock_path = project / ".better-product-graph" / "locks" / "run-lock.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            context = multiprocessing.get_context("fork")
            started = context.Event()
            completed = context.Queue()
            with lock_path.open("a+b") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                process = context.Process(
                    target=_mutate_interview,
                    args=(str(project), "run-lock", started, completed),
                )
                process.start()
                self.assertTrue(started.wait(2))
                with self.assertRaises(queue.Empty):
                    completed.get(timeout=0.2)
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            self.assertEqual(completed.get(timeout=2), "OK")
            process.join(2)
            self.assertEqual(process.exitcode, 0)

    def test_concurrent_cas_allows_only_one_writer_for_same_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            controller = StateController(project, GRAPH)
            initial = controller.create_run("run-cas", raw_signal="cas")
            context = multiprocessing.get_context("fork")
            start = context.Event()
            completed = context.Queue()

            def worker(action: str) -> None:
                child = StateController(project, GRAPH)
                start.wait(2)
                try:
                    child.set_interview_policy(
                        "run-cas", action,
                        expected_state_version=initial["state_version"],
                    )
                    completed.put("OK")
                except Exception as error:
                    completed.put(type(error).__name__)

            processes = [context.Process(target=worker, args=(action,)) for action in ("skip", "resume")]
            for process in processes:
                process.start()
            start.set()
            outcomes = [completed.get(timeout=3) for _ in processes]
            for process in processes:
                process.join(2)
            self.assertEqual(outcomes.count("OK"), 1)
            self.assertEqual(controller.load_state("run-cas")["state_version"], initial["state_version"] + 1)

    def test_event_append_obeys_lock_and_concurrent_chain_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            lock_path = path.with_name(".events.jsonl.lock")
            context = multiprocessing.get_context("fork")
            started = context.Event()
            completed = context.Queue()
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open("a+b") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                process = context.Process(
                    target=_append_worker,
                    args=(str(path), 0, started, completed),
                )
                process.start()
                self.assertTrue(started.wait(2))
                with self.assertRaises(queue.Empty):
                    completed.get(timeout=0.2)
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            self.assertEqual(completed.get(timeout=2), "OK")
            process.join(2)

            gate = context.Event()
            processes = [
                context.Process(target=_append_worker, args=(str(path), index, gate, completed))
                for index in range(1, 9)
            ]
            for child in processes:
                child.start()
            gate.set()
            self.assertEqual([completed.get(timeout=3) for _ in processes].count("OK"), 8)
            for child in processes:
                child.join(2)
            self.assertEqual(len(verify_event_chain(path)), 9)


if __name__ == "__main__":
    unittest.main()
