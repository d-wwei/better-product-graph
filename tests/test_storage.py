from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.bpg.storage import IntegrityError, append_event, atomic_write_json, verify_event_chain


class StorageTests(unittest.TestCase):
    def test_atomic_json_write_leaves_complete_canonical_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"

            atomic_write_json(path, {"z": 1, "a": ["证据", 2]})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": ["证据", 2], "z": 1})
            self.assertTrue(path.read_bytes().endswith(b"\n"))
            self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_event_chain_detects_rewritten_meaningful_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            append_event(path, {"event_type": "RUN_CREATED", "actor": "controller"})
            append_event(path, {"event_type": "NODE_COMPLETED", "actor": "controller"})
            lines = path.read_text(encoding="utf-8").splitlines()
            changed = json.loads(lines[0])
            changed["event_type"] = "RUN_RELEASED"
            lines[0] = json.dumps(changed, ensure_ascii=False, sort_keys=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(IntegrityError, "event hash"):
                verify_event_chain(path)


if __name__ == "__main__":
    unittest.main()
