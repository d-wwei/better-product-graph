from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class BPG2R5R6LightweightReviewContractTests(unittest.TestCase):
    def test_agent_instructions_keep_review_semantic_and_visuals_mermaid_only(self) -> None:
        sources = [
            REPO_ROOT / "host-adapters/codex/public-skill/better-product-graph/SKILL.md",
            REPO_ROOT / "host-adapters/claude/public-skill/better-product-graph/SKILL.md",
            REPO_ROOT / "src/core/atomic-skills/prd-review/INSTRUCTIONS.md",
        ]
        for source in sources:
            with self.subTest(source=source):
                text = source.read_text(encoding="utf-8")
                self.assertIn("Mermaid", text)
                self.assertIn("difference review", text)
                self.assertIn("whole-product regression", text)
                self.assertIn("new Review", text)
                self.assertIn("component hash", text)
                self.assertIn("responsibility hash", text)
                self.assertNotIn("already generated safe SVG preview", text)

    def test_method_defers_svg_to_handoff_without_review_inheritance(self) -> None:
        method = (
            REPO_ROOT
            / "docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.4.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Candidate 阶段只保留 Mermaid source", method)
        self.assertIn("Handoff", method)
        self.assertIn("整体 Candidate", method)
        self.assertIn("component hash", method)
        self.assertIn("responsibility hash", method)
        self.assertIn("不得继承旧 Review", method)


if __name__ == "__main__":
    unittest.main()
