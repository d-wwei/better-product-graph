from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
METHOD = (
    REPO_ROOT
    / "docs"
    / "architecture"
    / "BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
)
HOST_SKILLS = (
    REPO_ROOT
    / "host-adapters"
    / "codex"
    / "public-skill"
    / "better-product-graph"
    / "SKILL.md",
    REPO_ROOT
    / "host-adapters"
    / "claude"
    / "public-skill"
    / "better-product-graph"
    / "SKILL.md",
)


class BPG2R8SolutionIntelligenceContractTests(unittest.TestCase):
    def assert_host_semantic_boundary(self, text: str) -> None:
        required = (
            "Platform or environment facts establish feasibility or constraints",
            "do not by themselves constitute Solution Intelligence",
            "Agent-generated alternatives are not external or adjacent-practice evidence",
            "direct products, industry or adjacent practices, failure cases or anti-patterns",
            "concrete `NOT_APPLICABLE` rationale",
            "high-reuse, high-maintenance, or novel system",
            "normal advisory Finding",
            "Planning Record keeps only conclusions and key evidence, not a search log",
            "Do not require a fixed source count, force online research, or add a schema, checklist, or Gate",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_method_distinguishes_platform_facts_from_solution_practice(self) -> None:
        method = METHOD.read_text(encoding="utf-8")
        required = (
            "平台或环境事实只能证明可行性与约束",
            "不能单独充当方案情报",
            "Agent 自己枚举出多个方案也只算替代方案生成",
            "真正相关的直接产品、行业或相邻实践、失败案例或反模式",
            "具体的 `NOT_APPLICABLE` 理由",
            "高复用、高维护成本或新型系统",
            "普通 advisory Finding",
            "只保留结论和关键证据，不堆积搜索流水",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, method)

    def test_both_public_host_skills_share_the_same_agent_owned_check(self) -> None:
        texts = [path.read_text(encoding="utf-8") for path in HOST_SKILLS]
        for text in texts:
            self.assert_host_semantic_boundary(text)

        codex_paragraph = next(
            paragraph
            for paragraph in texts[0].split("\n\n")
            if "Platform or environment facts establish" in paragraph
        )
        claude_paragraph = next(
            paragraph
            for paragraph in texts[1].split("\n\n")
            if "Platform or environment facts establish" in paragraph
        )
        self.assertEqual(codex_paragraph, claude_paragraph)
        self.assertNotIn("Controller", codex_paragraph)

    def test_built_plugin_carries_the_r8_semantic_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            skill_root = plugin / "skills" / "better-product-graph"

            self.assert_host_semantic_boundary(
                (skill_root / "SKILL.md").read_text(encoding="utf-8")
            )
            installed_method = (
                skill_root
                / "references"
                / "alpha"
                / "BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
            ).read_text(encoding="utf-8")
            self.assertIn("平台或环境事实只能证明可行性与约束", installed_method)
            self.assertIn("高复用、高维护成本或新型系统", installed_method)


if __name__ == "__main__":
    unittest.main()
