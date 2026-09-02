from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ATOMIC = ROOT / "src" / "core" / "atomic-skills"
PROBLEM_AUTHOR = ATOMIC / "problem-synthesize" / "INSTRUCTIONS.md"
DECISION_AUTHOR = ATOMIC / "product-decision" / "INSTRUCTIONS.md"
PRD_AUTHOR = ATOMIC / "prd-generate" / "INSTRUCTIONS.md"
PROBLEM_REVIEWER = ATOMIC / "problem-quality-review" / "INSTRUCTIONS.md"
PRD_REVIEWER = ATOMIC / "prd-review" / "INSTRUCTIONS.md"
HOST_SKILLS = (
    ROOT / "host-adapters/codex/public-skill/better-product-graph/SKILL.md",
    ROOT / "host-adapters/claude/public-skill/better-product-graph/SKILL.md",
)


def read(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class BPG2Issue1Issue6AgentContractTests(unittest.TestCase):
    def test_problem_author_runs_bounded_semantic_preflight_before_freeze(self) -> None:
        text = read(PROBLEM_AUTHOR)
        for phrase in (
            "Bounded author semantic preflight before Problem freeze",
            "`diagnoses`",
            "`actions`",
            "one core user/context/outcome/obstacle/impact frame",
            "evidence or observed fact distinct from inference, assumption",
            "without selecting a solution, mechanism, implementation",
            "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL",
            "independent Problem Reviewer remains required",
            "keyword scan, image inspection, hash comparison",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_decision_author_preflight_reuses_existing_agent_checks(self) -> None:
        text = read(DECISION_AUTHOR)
        for phrase in (
            "Bounded author semantic preflight before Decision freeze",
            "Solution Intelligence",
            "`diagnoses`",
            "`actions`",
            "at least one real nearest alternative",
            "material trade-off and flip condition",
            "sensitive-data, privacy, permission",
            "reversibility, rollback or stop behavior",
            "quantitative baseline",
            "Assumption or Unknown instead of fabricating precision",
            "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL",
            "independent Decision Reviewer",
            "keyword, image, or hash rules",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_prd_author_preflight_extends_existing_diagnoses_and_actions(self) -> None:
        text = read(PRD_AUTHOR)
        for phrase in (
            "BOUNDED_AUTHOR_SEMANTIC_PREFLIGHT",
            "same existing Document Experience self-check",
            "`diagnoses`",
            "matching `actions`",
            "different product meanings remain distinct",
            "one unambiguous user-visible behavior",
            "one canonical truth location",
            "`STATUS_DRIFT_TEST`",
            "explicitly `NOT_RUN` or Unknown",
            "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL",
            "Independent PRD Content and Writing Reviews remain required",
            "keyword scans, image analysis",
            "programmatic claim that product meaning stayed unchanged",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_author_preflight_does_not_extend_closed_outputs_or_governance(self) -> None:
        for path in (PROBLEM_AUTHOR, DECISION_AUTHOR, PRD_AUTHOR):
            with self.subTest(path=path):
                text = read(path)
                self.assertIn("Controller schema", text)
                self.assertIn("Gate", text)
                self.assertIn("Owner round", text)
                self.assertRegex(
                    text.lower(),
                    r"do not (?:add fields|create another checklist, payload field)",
                )

    def test_formal_reviewers_self_check_exact_output_once_before_return(self) -> None:
        for path in (PROBLEM_REVIEWER, PRD_REVIEWER):
            with self.subTest(path=path):
                text = read(path)
                for phrase in (
                    "Reviewer return-boundary structure self-check",
                    "exact output contract",
                    "at most one same-attempt",
                    "structure-only self-correction",
                    "REVIEW_RESULT_STRUCTURE_INVALID — HOST_REDISPATCH_REQUIRED",
                    "must not fill",
                    "ghostwrite Reviewer Findings",
                    "raw/corrected-output hashes",
                    "programmatic “meaning unchanged” check",
                    'spawn_agent(..., fork_turns="none")',
                    "no inherited parent conversation",
                ):
                    with self.subTest(path=path, phrase=phrase):
                        self.assertIn(phrase, text)

    def test_structure_repair_preserves_reviewer_semantics_and_authority(self) -> None:
        problem = read(PROBLEM_REVIEWER)
        for phrase in (
            "preserve the already-authored Finding set",
            "recommended disposition",
            "evidence meaning",
            "Never add, drop, merge, split, soften, strengthen",
            "writes no Run state",
            "reviewer_authority\": \"ADVISORY_ONLY",
        ):
            with self.subTest(reviewer="problem", phrase=phrase):
                self.assertIn(phrase, problem)

        prd = read(PRD_REVIEWER)
        for phrase in (
            "preserve the already-authored Finding set, Verdict/stance",
            "evidence meaning",
            "Never add, drop, merge, split, soften, strengthen",
            "never alter its basis, coverage judgment, or aggregate conclusion",
            "writes no Run state",
            "authority\": \"ADVISORY_ONLY",
        ):
            with self.subTest(reviewer="prd", phrase=phrase):
                self.assertIn(phrase, prd)

    def test_host_applies_author_preflight_to_every_alpha_candidate(self) -> None:
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = read(path)
                for phrase in (
                    "Before every Problem, Decision, or PRD freeze",
                    "bounded Agent semantic author preflight",
                    "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL",
                    "never replaces the independent Reviewer",
                    "keyword, image, or hash inference",
                ):
                    self.assertIn(phrase, text)

    def test_host_keeps_decision_reviewer_return_repair_agent_owned(self) -> None:
        for path in HOST_SKILLS:
            with self.subTest(path=path):
                text = read(path)
                for phrase in (
                    "every formal Problem, Decision, PRD content, or Writing Reviewer",
                    "at most one same-attempt structure-only correction",
                    "preserving every Finding, Verdict, basis, coverage judgment",
                    "REVIEW_RESULT_STRUCTURE_INVALID — HOST_REDISPATCH_REQUIRED",
                    "must not normalize or ghostwrite Reviewer semantics",
                    "not a new program validator, raw/corrected hash record",
                ):
                    self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
