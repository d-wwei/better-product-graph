from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
METHOD = REPO_ROOT / "docs" / "architecture" / "BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
HOST_SKILLS = (
    REPO_ROOT / "host-adapters" / "codex" / "public-skill" / "better-product-graph" / "SKILL.md",
    REPO_ROOT / "host-adapters" / "claude" / "public-skill" / "better-product-graph" / "SKILL.md",
)
OUTCOMES = (
    "FIXED",
    "DISPROVED",
    "DOWNGRADED",
    "ACCEPTED_LIMITATION",
    "NEEDS_OWNER",
    "INVALIDATED_BY_UPSTREAM_CHANGE",
)


class BPG2R3FindingClosureContractTests(unittest.TestCase):
    def assert_agent_owned_closure(self, text: str) -> None:
        self.assertIn("historical Review", text)
        self.assertIn("immutable", text)
        self.assertIn("planning-record.md", text)
        self.assertIn("source Review ref", text)
        self.assertIn("Finding ID", text)
        self.assertIn("outcome", text)
        self.assertIn("evidence", text)
        self.assertIn("new independent Reviewer", text)
        self.assertIn("difference review", text)
        self.assertIn("whole-product regression", text)
        self.assertIn("remaining material product limitation", text)
        self.assertIn("must not become a Controller schema, state, action, or Ready gate", text)
        for outcome in OUTCOMES:
            self.assertIn(outcome, text)

    def test_method_keeps_history_immutable_and_closes_findings_in_planning_record(self) -> None:
        self.assert_agent_owned_closure(METHOD.read_text(encoding="utf-8"))

    def test_both_public_host_skills_expose_the_same_lightweight_recovery(self) -> None:
        texts = [path.read_text(encoding="utf-8") for path in HOST_SKILLS]
        for text in texts:
            self.assert_agent_owned_closure(text)

        codex_paragraph = next(
            paragraph
            for paragraph in texts[0].split("\n\n")
            if "historical Review" in paragraph
        )
        claude_paragraph = next(
            paragraph
            for paragraph in texts[1].split("\n\n")
            if "historical Review" in paragraph
        )
        self.assertEqual(codex_paragraph, claude_paragraph)

    def test_built_plugin_carries_the_alpha_method_and_host_skill_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            skill_root = plugin / "skills" / "better-product-graph"

            self.assert_agent_owned_closure(
                (skill_root / "SKILL.md").read_text(encoding="utf-8")
            )
            self.assert_agent_owned_closure(
                (
                    skill_root
                    / "references"
                    / "alpha"
                    / "BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
                ).read_text(encoding="utf-8")
            )


if __name__ == "__main__":
    unittest.main()
