from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.bpg.resume import build_resume_brief, inspect_resume
from src.bpg.failpoints import begin_node_call, mark_dispatch_unknown, persist_node_dispatch
from src.bpg.state_controller import StateController
from src.bpg.storage import atomic_write_json, sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class ResumeTests(unittest.TestCase):
    def test_resume_brief_uses_plain_sentences_and_exact_current_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            controller = StateController(project, GRAPH)
            controller.create_run("run-001", raw_signal="用户希望恢复误删草稿")

            inspection = inspect_resume(controller, "run-001")
            brief = build_resume_brief(inspection)

            self.assertEqual(inspection.status, "READY_TO_RESUME")
            self.assertIn("正在处理", brief)
            self.assertIn("signal.ingest", brief)
            self.assertIn("下一步", brief)
            self.assertNotEqual(brief.strip(), "READY_TO_RESUME")

    def test_changed_exact_input_blocks_blind_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            controller = StateController(project, GRAPH)
            controller.create_run("run-002", raw_signal="原始用户反馈")
            state = controller.load_state("run-002")
            raw_path = project / state["artifact_refs"]["raw_signal"]["path"]
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
            payload["raw_text"] = "被修改后的反馈"
            raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            inspection = inspect_resume(controller, "run-002")

            self.assertEqual(inspection.status, "BLOCKED_STALE")
            self.assertIn("raw_signal", inspection.blockers[0])

    def test_resume_revalidates_graph_candidate_fanout_dispatch_and_unknown_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            controller = StateController(project, GRAPH)
            controller.create_run("run-full", raw_signal="原始信号")
            candidate_path = controller.run_path("run-full") / "artifacts" / "candidate.md"
            candidate_path.write_text("candidate", encoding="utf-8")
            state = controller.load_state("run-full")
            controller.bind_candidate(
                "run-full",
                {
                    "path": candidate_path.relative_to(controller.project_root).as_posix(),
                    "hash": sha256_file(candidate_path),
                    "version": 1,
                },
                expected_state_version=state["state_version"],
            )
            persist_node_dispatch(controller, "run-full", "attempt-unknown")
            begin_node_call(controller, "run-full", "attempt-unknown")
            mark_dispatch_unknown(controller, "run-full", "attempt-unknown")
            state = controller.load_state("run-full")
            state["graph_manifest"]["hash"] = "sha256:" + "0" * 64
            state["fanout_plans"].append(
                {
                    "plan_id": "missing-plan",
                    "path": ".better-product-graph/runs/run-full/fanout/missing/plan.json",
                    "hash": "sha256:" + "1" * 64,
                    "version": 1,
                    "candidate_hash": state["current_candidate_ref"]["hash"],
                }
            )
            atomic_write_json(controller._state_path("run-full"), state)
            candidate_path.write_text("changed", encoding="utf-8")

            inspection = inspect_resume(controller, "run-full")

            self.assertEqual(inspection.status, "BLOCKED_STALE")
            joined = " | ".join(inspection.blockers)
            self.assertIn("graph manifest", joined)
            self.assertIn("current Candidate", joined)
            self.assertIn("fanout", joined)
            self.assertIn("UNKNOWN_SIDE_EFFECT", joined)

    def test_managed_run_parent_symlink_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            project = Path(temporary)
            managed = project / ".better-product-graph"
            managed.mkdir()
            (managed / "runs").symlink_to(Path(outside), target_is_directory=True)
            controller = StateController(project, GRAPH)

            with self.assertRaisesRegex(Exception, "symlink"):
                controller.create_run("run-escape", raw_signal="must stay local")
            self.assertFalse((Path(outside) / "run-escape").exists())


if __name__ == "__main__":
    unittest.main()
