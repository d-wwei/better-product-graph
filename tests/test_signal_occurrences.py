from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.bpg.engine import HostEngine
from src.bpg.state_controller import StateController
from src.bpg.storage import verify_event_chain


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class SignalOccurrenceTests(unittest.TestCase):
    def test_every_new_and_capture_appends_occurrence_before_content_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            engine = HostEngine(project, StateController(project, GRAPH))

            first = engine.handle("$better-product-graph capture 同一条反馈")
            second = engine.handle("$better-product-graph capture 同一条反馈")
            activated = engine.handle("$better-product-graph new 同一条反馈")

            ledger = verify_event_chain(
                project / ".better-product-graph" / "signals" / "occurrences.jsonl"
            )
            self.assertEqual(len(ledger), 3)
            self.assertEqual(first["signal_id"], second["signal_id"])
            self.assertEqual({event["signal_id"] for event in ledger}, {first["signal_id"]})
            self.assertEqual(len({event["occurrence_id"] for event in ledger}), 3)
            for event in ledger:
                self.assertEqual(event["event_type"], "SIGNAL_OCCURRENCE_RECORDED")
                self.assertEqual(event["source"]["kind"], "MANUAL")
                self.assertIn("observed_at", event)
                self.assertIn("permissions", event)
                self.assertIn("sensitivity", event)
                self.assertIn("external_id", event)
                self.assertTrue(event["content_hash"].startswith("sha256:"))
            self.assertEqual(activated["source_signal_id"], first["signal_id"])
            source_ref = activated["state"]["artifact_refs"]["source_signal"]
            self.assertIn("/signals/by-content/", "/" + source_ref["path"])
            self.assertTrue((project / source_ref["path"]).is_file())
            self.assertEqual(activated["state"]["source_signal_id"], first["signal_id"])
            self.assertEqual(activated["state"]["source_occurrence_id"], activated["occurrence_id"])

    def test_state_changing_entry_automatically_runs_git_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            engine = HostEngine(project, StateController(project, GRAPH))

            result = engine.handle("$better-product-graph capture 自动执行 preflight")

            self.assertEqual(result["git_preflight"]["status"], "READY")
            self.assertTrue(result["git_preflight"]["initialized"])
            self.assertTrue((project / ".git").is_dir())


if __name__ == "__main__":
    unittest.main()
