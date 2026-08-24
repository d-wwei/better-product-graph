from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.bpg.documents import validate_document_experience
from tests.test_prd_contract import prd_markdown


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "src" / "core" / "policies" / "document-experience.json"


class DocumentExperienceTests(unittest.TestCase):
    def test_policy_covers_eight_human_artifact_profiles_without_new_graph_nodes(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(
            set(policy["profiles"]),
            {"problem", "decision", "plan", "prd", "incident", "bug", "internal_review", "handoff"},
        )
        self.assertEqual(policy["graph_effect"], "CROSS_CUTTING_ONLY")

    def test_prd_conclusion_next_step_evidence_unknown_authority_version_are_visible(self) -> None:
        result = validate_document_experience(prd_markdown(), "prd")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.issues, [])

    def test_default_template_changelog_heading_is_accepted_without_machine_filename(self) -> None:
        markdown = prd_markdown().replace(
            "v0.1 首次形成候选；对应 DOCUMENT_CHANGELOG.md 将由版本机制维护。",
            "## 附录 C：文档变更日志\n\n"
            "| PRD 版本 | 日期 | 主要变更 |\n"
            "|---|---|---|\n"
            "| v0.1 | 2026-08-21 | 首次形成候选 PRD |",
        )

        result = validate_document_experience(markdown, "prd")

        self.assertEqual(result.status, "PASS")
        self.assertNotIn("changelog_visible", result.issues)

    def test_prd_reading_summary_does_not_require_the_literal_word_conclusion(self) -> None:
        markdown = prd_markdown().replace(
            "结论：本次只交付失败可见与安全重试闭环。",
            "## 阅读摘要\n\n我们建议本次只交付失败可见与安全重试闭环。",
        )

        result = validate_document_experience(markdown, "prd")

        self.assertEqual(result.status, "PASS")
        self.assertNotIn("conclusion_first", result.issues)

    def test_local_handoff_cannot_claim_remote_received_or_approved(self) -> None:
        bad = "# Handoff v1\n结论：已发送并已批准。\n下一步：无。\n证据：local。未知：无。Authority：无。\n"
        result = validate_document_experience(bad, "handoff")
        self.assertEqual(result.status, "FAIL")
        self.assertIn("external_claim_language", result.issues)


if __name__ == "__main__":
    unittest.main()
