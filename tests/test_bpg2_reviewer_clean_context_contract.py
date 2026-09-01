from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


ROOT = Path(__file__).resolve().parents[1]
METHOD = ROOT / "docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
CODEX_SKILL = ROOT / "host-adapters/codex/public-skill/better-product-graph/SKILL.md"
CLAUDE_SKILL = ROOT / "host-adapters/claude/public-skill/better-product-graph/SKILL.md"
PROBLEM_REVIEW = ROOT / "src/core/atomic-skills/problem-quality-review/INSTRUCTIONS.md"
PRD_REVIEW = ROOT / "src/core/atomic-skills/prd-review/INSTRUCTIONS.md"
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ReviewerCleanContextContractTests(unittest.TestCase):
    def test_codex_skill_uses_none_for_every_formal_semantic_reviewer(self) -> None:
        text = read(CODEX_SKILL)
        for phrase in (
            'spawn_agent(..., fork_turns="none")',
            'Problem Review',
            'Decision Review',
            'PRD content Reviewer',
            'Writing Reviewer',
            'Internal Writing Reviewer evaluation',
            'never `fork_turns="all"` or a positive integer',
        ):
            self.assertIn(phrase, text)

    def test_codex_skill_limits_the_initial_task_to_exact_dispatched_refs(self) -> None:
        text = read(CODEX_SKILL)
        for phrase in (
            'exact frozen Candidate/ref',
            'installed Reviewer instruction and Review contract',
            'required read-only basis refs',
            'output contract and target',
            'author hidden reasoning',
            'mutable chat summary',
            'other first-pass Reviewer Findings',
            'undispatched workspace material',
        ):
            self.assertIn(phrase, text)

    def test_host_neutral_method_keeps_the_boundary_light_and_honest(self) -> None:
        text = read(METHOD)
        for phrase in (
            'Clean Reviewer Context',
            'spawn_agent(..., fork_turns="none")',
            '普通实现、研究或协作型子 Agent',
            '只隔离继承对话',
            '`HOST_SUBAGENT_ATTEMPT` 只能证明 Host 记录了一个不同尝试',
            '不新增 Runtime 校验、Schema、状态、Action、Gate 或 fork receipt',
        ):
            self.assertIn(phrase, text)

    def test_claude_skill_requires_equivalent_clean_context(self) -> None:
        text = read(CLAUDE_SKILL)
        for phrase in (
            'clean subagent/session with no inherited parent conversation',
            'formal semantic Reviewer',
            'exact frozen Candidate/ref',
            'undispatched workspace material',
            'does not prove filesystem or cryptographic isolation',
        ):
            self.assertIn(phrase, text)

    def test_reviewer_instructions_repeat_clean_context_custody(self) -> None:
        for path in (PROBLEM_REVIEW, PRD_REVIEW):
            with self.subTest(path=path):
                text = read(path)
                self.assertIn('spawn_agent(..., fork_turns="none")', text)
                self.assertIn('no inherited parent conversation', text)
                self.assertIn('undispatched workspace material', text)

    def test_built_host_packages_carry_the_clean_context_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for host in ("codex", "claude"):
                with self.subTest(host=host):
                    plugin = Path(directory) / host
                    build_plugin(ROOT, plugin, host=host)
                    skill_root = plugin / "skills/better-product-graph"
                    skill = read(skill_root / "SKILL.md")
                    self.assertIn('spawn_agent(..., fork_turns="none")', skill)
                    self.assertIn('Internal Writing Reviewer evaluation', skill)
                    self.assertIn('undispatched workspace material', skill)
                    method = read(
                        skill_root
                        / "references/alpha/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
                    )
                    self.assertIn("Clean Reviewer Context", method)
                    self.assertIn('fork_turns="none"', method)
                    for relative in (
                        "references/atomic-skills/problem-quality-review/INSTRUCTIONS.md",
                        "references/atomic-skills/prd-review/INSTRUCTIONS.md",
                    ):
                        instruction = read(skill_root / relative)
                        self.assertIn('spawn_agent(..., fork_turns="none")', instruction)
                        self.assertIn('no inherited parent conversation', instruction)


if __name__ == "__main__":
    unittest.main()
