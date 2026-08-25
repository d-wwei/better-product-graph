from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.bpg.documents import hash_tree, validate_lifecycle_expression_reconciliation
from src.bpg.host_runtime import HostRuntime
from src.bpg.storage import atomic_write_json, sha256_file
from src.bpg.writing_review import (
    WritingReviewError,
    load_and_validate_writing_coverage,
    validate_writing_coverage,
)
from tests.controller_fixtures import position_run_internal


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"
SKILL_ROOT = REPO_ROOT / "src" / "core"


CANDIDATE = {
    "path": "artifacts/prds/archived/EXAMPLE/EXAMPLE_v0.1.md",
    "hash": "sha256:candidate",
    "version": "v0.1",
}
PROFILE = {
    "path": "references/policies/prd-writing-profile-v0.2.json",
    "hash": "sha256:profile",
    "version": "0.2.0",
}
GUIDE = {
    "path": "references/policies/prd-writing-guide-v0.2.md",
    "hash": "sha256:guide",
    "version": "0.2.0",
}
OUTPUT_CONTRACT = {
    "path": "references/templates/contracts/prd-v0.2.json",
    "hash": "sha256:output-contract",
    "version": "better-product-graph.prd.general.0.2",
}
AUTHOR = {"kind": "HOST_AGENT_ATTEMPT", "id": "attempt-author"}
REVIEWER = {"kind": "HOST_SUBAGENT_ATTEMPT", "id": "attempt-writing-reviewer"}

RULE_IDS = [f"RULE-{index:02d}" for index in range(1, 14)]
CHECK_IDS = [f"CHECK-{index:02d}" for index in range(1, 11)]


def _basis() -> list[dict]:
    return [
        {
            "path": CANDIDATE["path"],
            "hash": CANDIDATE["hash"],
            "start_line": 1,
            "end_line": 2,
        }
    ]


def coverage() -> dict:
    return {
        "schema_version": "document-experience-coverage.v1",
        "candidate_ref": copy.deepcopy(CANDIDATE),
        "candidate_tree_hash": "sha256:candidate-tree",
        "profile_ref": copy.deepcopy(PROFILE),
        "guide_ref": copy.deepcopy(GUIDE),
        "output_contract_ref": copy.deepcopy(OUTPUT_CONTRACT),
        "author_execution_ref": copy.deepcopy(AUTHOR),
        "reviewer_execution_ref": copy.deepcopy(REVIEWER),
        "reviewer_role": "writing_standard",
        "isolated_input_refs": [
            copy.deepcopy(CANDIDATE),
            copy.deepcopy(PROFILE),
            copy.deepcopy(GUIDE),
            copy.deepcopy(OUTPUT_CONTRACT),
        ],
        "required_rule_results": [
            {
                "rule_id": rule_id,
                "verdict": "PASS",
                "basis_refs": _basis(),
                "reason": "候选稿中的对应段落提供了直接依据。",
            }
            for rule_id in RULE_IDS
        ],
        "delivery_check_results": [
            {
                "check_id": check_id,
                "verdict": "PASS",
                "basis_refs": _basis(),
                "reason": "零背景读者可以从候选稿直接回答。",
            }
            for check_id in CHECK_IDS
        ],
        "finding_refs": [],
    }


def validate(value: dict) -> dict:
    return validate_writing_coverage(
        value,
        expected_candidate_ref=CANDIDATE,
        expected_candidate_tree_hash="sha256:candidate-tree",
        expected_profile_ref=PROFILE,
        expected_guide_ref=GUIDE,
        expected_output_contract_ref=OUTPUT_CONTRACT,
        expected_author_execution_ref=AUTHOR,
        required_rule_ids=RULE_IDS,
        required_check_ids=CHECK_IDS,
        candidate_line_count=20,
        available_finding_ids=set(),
    )


class WritingCoverageTests(unittest.TestCase):
    def test_missing_one_of_thirteen_rules_is_rejected(self) -> None:
        value = coverage()
        value["required_rule_results"].pop()

        with self.assertRaisesRegex(WritingReviewError, "required_rule_results"):
            validate(value)

    def test_missing_one_of_ten_delivery_checks_is_rejected(self) -> None:
        value = coverage()
        value["delivery_check_results"].pop()

        with self.assertRaisesRegex(WritingReviewError, "delivery_check_results"):
            validate(value)

    def test_missing_exact_basis_is_rejected(self) -> None:
        value = coverage()
        value["required_rule_results"][0]["basis_refs"] = []

        with self.assertRaisesRegex(WritingReviewError, "basis_refs"):
            validate(value)

    def test_candidate_hash_mismatch_is_rejected(self) -> None:
        value = coverage()
        value["candidate_ref"]["hash"] = "sha256:other-candidate"

        with self.assertRaisesRegex(WritingReviewError, "exact current Candidate"):
            validate(value)

    def test_author_and_reviewer_execution_must_differ(self) -> None:
        value = coverage()
        value["reviewer_execution_ref"] = copy.deepcopy(AUTHOR)

        with self.assertRaisesRegex(WritingReviewError, "must differ"):
            validate(value)

    def test_not_applicable_requires_a_concrete_reason(self) -> None:
        value = coverage()
        value["required_rule_results"][0].update(
            {"verdict": "NOT_APPLICABLE", "reason": ""}
        )

        with self.assertRaisesRegex(WritingReviewError, "reason"):
            validate(value)

    def test_complete_thirteen_plus_ten_zero_finding_coverage_passes(self) -> None:
        validated = validate(coverage())

        self.assertEqual(len(validated["required_rule_results"]), 13)
        self.assertEqual(len(validated["delivery_check_results"]), 10)
        self.assertEqual(validated["finding_refs"], [])

    def test_exact_regular_coverage_artifact_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            candidate = project / "candidate.md"
            candidate.write_text("# PRD\n\n正文。\n", encoding="utf-8")
            candidate_ref = {
                "path": "candidate.md",
                "hash": sha256_file(candidate),
                "version": "v0.1",
            }
            profile_path = SKILL_ROOT / "policies" / "prd-writing-profile-v0.2.json"
            guide_path = SKILL_ROOT / "policies" / "prd-writing-guide-v0.2.md"
            contract_path = (
                SKILL_ROOT
                / "reviewer-profiles"
                / "prd-writing-standard-coverage-v1.json"
            )
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            profile_ref = {
                "path": "references/policies/prd-writing-profile-v0.2.json",
                "hash": sha256_file(profile_path),
                "version": "0.2.0",
            }
            guide_ref = {
                "path": "references/policies/prd-writing-guide-v0.2.md",
                "hash": sha256_file(guide_path),
                "version": "0.2.0",
            }
            output_path = SKILL_ROOT / "templates" / "contracts" / "prd-v0.2.json"
            output_ref = {
                "path": "references/templates/contracts/prd-v0.2.json",
                "hash": sha256_file(output_path),
                "version": "better-product-graph.prd.general.0.2",
            }
            value = {
                "schema_version": "document-experience-coverage.v1",
                "candidate_ref": candidate_ref,
                "candidate_tree_hash": "sha256:tree",
                "profile_ref": profile_ref,
                "guide_ref": guide_ref,
                "output_contract_ref": output_ref,
                "author_execution_ref": AUTHOR,
                "reviewer_execution_ref": REVIEWER,
                "reviewer_role": "writing_standard",
                "isolated_input_refs": [candidate_ref, profile_ref, guide_ref, output_ref],
                "required_rule_results": [
                    {
                        "rule_id": rule_id,
                        "verdict": "PASS",
                        "basis_refs": [
                            {
                                "path": candidate_ref["path"],
                                "hash": candidate_ref["hash"],
                                "start_line": 1,
                                "end_line": 1,
                            }
                        ],
                        "reason": "有对应依据。",
                    }
                    for rule_id in profile["required_expression_rules"]
                ],
                "delivery_check_results": [
                    {
                        "check_id": item["check_id"],
                        "verdict": "PASS",
                        "basis_refs": [
                            {
                                "path": candidate_ref["path"],
                                "hash": candidate_ref["hash"],
                                "start_line": 1,
                                "end_line": 1,
                            }
                        ],
                        "reason": "有对应依据。",
                    }
                    for item in contract["delivery_checks"]
                ],
                "finding_refs": [],
            }
            coverage_path = project / "writing-coverage.json"
            atomic_write_json(coverage_path, value)
            coverage_ref = {
                "path": "writing-coverage.json",
                "hash": sha256_file(coverage_path),
                "version": 1,
            }
            context = {
                "candidate_ref": candidate_ref,
                "candidate_tree_hash": "sha256:tree",
                "profile_ref": profile_ref,
                "guide_ref": guide_ref,
                "output_contract_ref": output_ref,
                "coverage_contract_ref": {
                    "path": "references/reviewer-profiles/prd-writing-standard-coverage-v1.json",
                    "hash": sha256_file(contract_path),
                    "version": "v1",
                },
                "author_execution_ref": AUTHOR,
                "required_rule_ids": profile["required_expression_rules"],
                "required_check_ids": [item["check_id"] for item in contract["delivery_checks"]],
            }

            validated = load_and_validate_writing_coverage(
                project,
                coverage_ref,
                context=context,
                available_finding_ids=set(),
            )
            self.assertEqual(validated["candidate_ref"], candidate_ref)

            coverage_path.unlink()
            coverage_path.symlink_to(candidate)
            with self.assertRaisesRegex(WritingReviewError, "regular"):
                load_and_validate_writing_coverage(
                    project,
                    coverage_ref,
                    context=context,
                    available_finding_ids=set(),
                )


class LifecycleExpressionReconciliationTests(unittest.TestCase):
    def test_review_pending_conflicts_with_finalized_review(self) -> None:
        issues = validate_lifecycle_expression_reconciliation(
            "# PRD\n\n- **当前 Review 状态**：待 Review\n",
            authoritative={
                "review_status": "FINALIZED",
                "eval_fulfillment": "REVIEWED",
                "eval_execution_status": "NOT_RUN",
                "remote_handoff_status": "NOT_CONFIGURED",
            },
        )

        self.assertIn("review_status_conflict", issues)

    def test_not_run_cannot_be_claimed_as_executed_pass_or_fail(self) -> None:
        for claim in ("PASS", "FAIL"):
            with self.subTest(claim=claim):
                issues = validate_lifecycle_expression_reconciliation(
                    f"# PRD\n\n| Product Evals 执行状态 | {claim} |\n",
                    authoritative={
                        "review_status": "FINALIZED",
                        "eval_fulfillment": "REVIEWED",
                        "eval_execution_status": "NOT_RUN",
                        "remote_handoff_status": "NOT_CONFIGURED",
                    },
                )
                self.assertIn("eval_execution_status_conflict", issues)

    def test_unrelated_stable_product_status_is_not_misread_as_lifecycle(self) -> None:
        issues = validate_lifecycle_expression_reconciliation(
            "# PRD\n\n| 任务执行状态 | PASS / FAIL |\n",
            authoritative={
                "review_status": "FINALIZED",
                "eval_fulfillment": "REVIEWED",
                "eval_execution_status": "NOT_RUN",
                "remote_handoff_status": "NOT_CONFIGURED",
            },
        )

        self.assertEqual(issues, [])


class WritingReviewDispatchTests(unittest.TestCase):
    def test_review_dispatch_exposes_exact_isolated_writing_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            runtime = HostRuntime(project, GRAPH, SKILL_ROOT)
            run_id = "run-writing-dispatch"
            runtime.controller.create_run(run_id, raw_signal="审查写作规范")
            candidate_root = project / "artifacts" / "prds" / "archived" / "EXAMPLE"
            candidate_root.mkdir(parents=True)
            candidate = candidate_root / "EXAMPLE_v0.1.md"
            candidate.write_text("# 示例 PRD\n\n## 阅读摘要\n", encoding="utf-8")
            metadata = candidate_root / "EXAMPLE_v0.1.metadata.json"
            output_contract = SKILL_ROOT / "templates" / "contracts" / "prd-v0.2.json"
            atomic_write_json(
                metadata,
                {
                    "prd_id": "EXAMPLE",
                    "short_title": "示例",
                    "date": "2026-08-25",
                    "provenance": {"attempt_id": "attempt-author"},
                    "document_experience": {
                        "profile_ref": {
                            "path": "references/policies/prd-writing-profile-v0.2.json",
                            "hash": sha256_file(
                                SKILL_ROOT / "policies" / "prd-writing-profile-v0.2.json"
                            ),
                            "version": "0.2.0",
                        },
                        "writing_guide_ref": {
                            "path": "references/policies/prd-writing-guide-v0.2.md",
                            "hash": sha256_file(
                                SKILL_ROOT / "policies" / "prd-writing-guide-v0.2.md"
                            ),
                            "version": "0.2.0",
                        },
                    },
                    "template_profile": {
                        "output_contract": {
                            "path": "references/templates/contracts/prd-v0.2.json",
                            "sha256": sha256_file(output_contract),
                            "version": "better-product-graph.prd.general.0.2",
                        }
                    },
                },
            )
            review = candidate_root / "EXAMPLE_v0.1.review.json"
            atomic_write_json(review, {"status": "NOT_RUN"})
            candidate_ref = {
                "role": "prd_candidate",
                "path": candidate.relative_to(project).as_posix(),
                "hash": sha256_file(candidate),
                "version": "v0.1",
                "artifact_path": candidate_root.relative_to(project).as_posix(),
                "tree_hash": hash_tree(candidate_root),
                "review_path": review.relative_to(project).as_posix(),
                "review_hash": sha256_file(review),
                "generation": 1,
            }
            position_run_internal(
                runtime.controller,
                run_id,
                "review.parallel",
                ["review.aggregate"],
                artifact_refs={"prd-candidate": candidate_ref},
                state_updates={"current_candidate_ref": candidate_ref},
            )

            dispatch = runtime.dispatch_current(run_id)
            context = dispatch["writing_review_context"]

            self.assertEqual(context["candidate_ref"]["hash"], candidate_ref["hash"])
            self.assertEqual(context["candidate_tree_hash"], candidate_ref["tree_hash"])
            self.assertEqual(
                context["author_execution_ref"],
                {"kind": "HOST_AGENT_ATTEMPT", "id": "attempt-author"},
            )
            self.assertEqual(len(context["required_rule_ids"]), 13)
            self.assertEqual(len(context["required_check_ids"]), 10)
            self.assertEqual(len(context["isolated_input_refs"]), 4)


if __name__ == "__main__":
    unittest.main()
