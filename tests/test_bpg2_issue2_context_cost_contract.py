from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOST_SKILLS = (
    ROOT / "host-adapters/codex/public-skill/better-product-graph/SKILL.md",
    ROOT / "host-adapters/claude/public-skill/better-product-graph/SKILL.md",
)
PLANNING_CONTEXT = (
    ROOT / "src/core/atomic-skills/planning-context-prepare/INSTRUCTIONS.md"
)


class BPG2Issue2ContextCostContractTests(unittest.TestCase):
    def test_both_hosts_reuse_existing_agent_owned_stage_summary(self) -> None:
        paragraphs = []
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in (
                    "Long-Run Context Discipline",
                    "existing `planning_context.context_summary`",
                    "continuously maintained `planning-record.md`",
                    "compact, traceable stage fact summary",
                    "current planning summary",
                    "current Candidate, when one exists",
                    "exact change from its immediate predecessor",
                    "unresolved Findings",
                    "rules and contract refs required by the current stage",
                ):
                    self.assertIn(phrase, text)

                paragraphs.append(
                    next(
                        paragraph
                        for paragraph in text.split("\n\n")
                        if "compact, traceable stage fact summary" in paragraph
                    )
                )

        self.assertEqual(paragraphs[0], paragraphs[1])

    def test_both_hosts_exclude_accumulated_history_and_trim_explicitly(self) -> None:
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in (
                    "complete chat history",
                    "every old Candidate",
                    "closed Findings",
                    "full source excerpts",
                    "say what it trimmed and why",
                    "canonical exact refs",
                    "Never silently drop a material fact",
                ):
                    self.assertIn(phrase, text)

    def test_both_hosts_keep_usage_claims_observable_and_avoid_new_harness(self) -> None:
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in (
                    "only when the Host or platform actually exposes those values",
                    "Do not claim a token reduction",
                    "Evidence Digest schema or artifact",
                    "hash budget",
                    "Controller Gate",
                ):
                    self.assertIn(phrase, text)

    def test_planning_context_summary_is_the_run_local_compaction_seed(self) -> None:
        text = PLANNING_CONTEXT.read_text(encoding="utf-8")
        for phrase in (
            "`context_summary` 是当前 Run 的紧凑、可追溯阶段事实摘要",
            "持续维护的 `planning-record.md`",
            "canonical exact refs",
            "不得把完整来源正文或长段源码摘录复制进摘要",
            "必须说明裁剪了什么以及为什么",
            "不得静默丢弃会改变判断的事实",
            "不新增 Evidence Digest",
        ):
            self.assertIn(phrase, text)

    def test_formal_reviewer_isolation_and_exact_dispatch_refs_remain_intact(self) -> None:
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn('spawn_agent(..., fork_turns="none")', text)
                self.assertIn("exact frozen Candidate/ref", text)
                self.assertIn("required read-only basis refs", text)
                self.assertIn("undispatched workspace material", text)

    def test_issue4_hosts_consume_returned_state_without_a_status_round_trip(self) -> None:
        paragraphs = []
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in (
                    "Consume Returned State Directly",
                    "Every successful alpha state-changing operation returns the complete new state",
                    "directly consume the just-returned state and next-work material",
                    "`current_review_requirements`",
                    "PASS Review already advances Ready and the next position",
                    "Do not immediately call `status`",
                    "`status` only for recovery, re-entry after context loss, or explicit diagnostics",
                ):
                    self.assertIn(phrase, text)

                paragraphs.append(
                    next(
                        paragraph
                        for paragraph in text.split("\n\n")
                        if "directly consume the just-returned state" in paragraph
                    )
                )

        self.assertEqual(paragraphs[0], paragraphs[1])

    def test_issue4_hosts_do_not_compound_semantics_or_side_effects(self) -> None:
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in (
                    "Do not add a compound Controller API",
                    "merge durable events, semantic steps, or external side effects",
                    "stop automatic serial execution",
                    "new Agent work",
                    "independent Reviewer",
                    "Owner decision",
                    "external side effect",
                ):
                    self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
