from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin, verify_installed_identity


REPO_ROOT = Path(__file__).resolve().parents[1]


class ClaudeAdapterContractTests(unittest.TestCase):
    def test_builds_a_native_claude_plugin_with_the_shared_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "better-product-graph"
            manifest = build_plugin(REPO_ROOT, output, host="claude")

            plugin = json.loads(
                (output / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
            )
            self.assertEqual(plugin["name"], "better-product-graph")
            self.assertEqual(manifest["host"]["host_id"], "claude")
            self.assertTrue((output / "skills/better-product-graph/SKILL.md").is_file())
            self.assertTrue(verify_installed_identity(output)["valid"])


if __name__ == "__main__":
    unittest.main()
