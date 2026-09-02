from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]


class BPG2ZeroContextHTMLContractTests(unittest.TestCase):
    def test_both_hosts_require_agent_authored_zero_context_html(self) -> None:
        required = (
            "references/policies/prd-reader-html-guide-v1.md",
            "html_source_ref",
            "AGENT_AUTHORED_ZERO_CONTEXT_VIEW",
            "1440px",
            "390px",
            "`PRD.md` remains the editing truth",
        )
        for host in ("codex", "claude"):
            with self.subTest(host=host):
                skill = (
                    REPO_ROOT
                    / "host-adapters"
                    / host
                    / "public-skill"
                    / "better-product-graph"
                    / "SKILL.md"
                ).read_text(encoding="utf-8")
                for phrase in required:
                    self.assertIn(phrase, skill)

    def test_built_plugin_contains_the_reader_html_guide(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            guide = (
                plugin
                / "skills"
                / "better-product-graph"
                / "references"
                / "policies"
                / "prd-reader-html-guide-v1.md"
            )

            self.assertTrue(guide.is_file())
            content = guide.read_text(encoding="utf-8")
            self.assertIn("30 秒摘要", content)
            self.assertIn('data-bpg-reader-view="zero-context-v1"', content)
            self.assertIn('href="PRD.md"', content)
            self.assertIn("真实浏览器", content)


if __name__ == "__main__":
    unittest.main()
