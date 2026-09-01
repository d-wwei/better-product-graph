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
from tests.test_visual_assets import png, svg


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
REVIEW_CONTRACT = {
    "path": "references/reviewer-profiles/prd-writing-reader-review-v3.json",
    "hash": "sha256:reader-review-v3",
    "version": "v3",
}
AUTHOR = {"kind": "HOST_AGENT_ATTEMPT", "id": "attempt-author"}
REVIEWER = {"kind": "HOST_SUBAGENT_ATTEMPT", "id": "attempt-writing-reviewer"}
VISUAL_PAIR = {
    "svg_ref": {
        "path": "artifacts/prds/archived/EXAMPLE/assets/main-flow.svg",
        "hash": "sha256:svg",
        "version": "reader-visual.v1",
    },
    "png_ref": {
        "path": "artifacts/prds/archived/EXAMPLE/assets/main-flow@2x.png",
        "hash": "sha256:png",
        "version": "reader-visual.v1",
    },
}

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


def reader_review() -> dict:
    return {
        "schema_version": "document-experience-reader-review.v3",
        "authority": "ADVISORY_ONLY",
        "candidate_ref": copy.deepcopy(CANDIDATE),
        "candidate_tree_hash": "sha256:candidate-tree",
        "profile_ref": {
            "path": "references/policies/prd-writing-profile-v0.4.json",
            "hash": "sha256:profile-v0.4",
            "version": "0.4.0",
        },
        "guide_ref": {
            "path": "references/policies/prd-writing-guide-v0.4.md",
            "hash": "sha256:guide-v0.4",
            "version": "0.4.0",
        },
        "review_contract_ref": copy.deepcopy(REVIEW_CONTRACT),
        "output_contract_ref": copy.deepcopy(OUTPUT_CONTRACT),
        "author_execution_ref": copy.deepcopy(AUTHOR),
        "reviewer_execution_ref": copy.deepcopy(REVIEWER),
        "reviewer_role": "writing_standard",
        "isolated_input_refs": [
            copy.deepcopy(CANDIDATE),
            {
                "path": "references/policies/prd-writing-profile-v0.4.json",
                "hash": "sha256:profile-v0.4",
                "version": "0.4.0",
            },
            {
                "path": "references/policies/prd-writing-guide-v0.4.md",
                "hash": "sha256:guide-v0.4",
                "version": "0.4.0",
            },
            copy.deepcopy(REVIEW_CONTRACT),
            copy.deepcopy(OUTPUT_CONTRACT),
        ],
        "reader_readback": {
            "problem_and_outcome": "高频用户需要快速识别必须处理的消息，产品要降低遗漏风险。",
            "primary_relationships": "消息按处理必要性分层，风险消息优先于普通通知。",
            "mental_model": [
                {"name": "信号", "role": "进入产品判断的原始材料"},
                {"name": "规则", "role": "决定消息优先级"},
                {"name": "结果", "role": "让用户先处理高风险消息"},
            ],
            "main_path_and_recovery": "系统分类后展示优先级；分类失败时保留原消息并允许重试。",
            "decision_conditions_and_risks": "只有分类可靠时采用；主要风险是错误降级风险消息。",
            "navigation_map": [
                {"target": "PRODUCT_RULES", "location": "第 4 节"},
                {"target": "ACCEPTANCE", "location": "第 6 节"},
                {"target": "RISKS_UNKNOWNS_NEXT", "location": "第 7 节"},
            ],
        },
        "reader_outcome_failures": [],
        "verbosity_assessment": {
            "verdict": "PASS",
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": [],
            "finding_refs": [],
            "reason": "主路径分层清楚，没有重复合同。",
        },
        "checklist_assessment": {
            "verdict": "PASS",
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": [],
            "finding_refs": [],
            "reason": "检查项的解释和追溯功能仍然保留。",
        },
        "visual_assessment": {
            "verdict": "NOT_NEEDED",
            "observation_status": "NOT_NEEDED",
            "visual_pair_refs": [],
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": [],
            "finding_refs": [],
            "reason": "当前关系简单，文字已经足够表达。",
        },
        "finding_refs": [],
        "claim_boundary": "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
    }


def validate_reader(
    value: dict,
    findings: set[str] | None = None,
    *,
    visual_pairs: list[dict] | None = None,
) -> dict:
    return validate_writing_coverage(
        value,
        expected_candidate_ref=CANDIDATE,
        expected_candidate_tree_hash="sha256:candidate-tree",
        expected_profile_ref=reader_review()["profile_ref"],
        expected_guide_ref=reader_review()["guide_ref"],
        expected_review_contract_ref=REVIEW_CONTRACT,
        expected_output_contract_ref=OUTPUT_CONTRACT,
        expected_author_execution_ref=AUTHOR,
        required_rule_ids=[],
        required_check_ids=[],
        candidate_line_count=20,
        available_finding_ids=findings or set(),
        expected_visual_pairs=visual_pairs or [],
    )


def finding_reader_review() -> dict:
    value = reader_review()
    value["reader_outcome_failures"] = [
        {
            "outcome": "LOCATE",
            "basis_refs": _basis(),
            "reason": "风险与未知散落在多个位置，无法直接定位。",
            "finding_id": "f-reader",
        }
    ]
    value["verbosity_assessment"] = {
        "verdict": "FINDING",
        "issue_types": ["SEMANTIC_REPETITION"],
        "repair_techniques": ["REFERENCE"],
        "basis_refs": _basis(),
        "finding_refs": ["f-verbosity"],
        "reason": "同一规则在摘要与正文重复定义。",
    }
    value["finding_refs"] = ["f-reader", "f-verbosity"]
    return value


class ReaderReviewV3Tests(unittest.TestCase):
    def test_complete_readback_without_thirteen_plus_ten_pass_wall_is_accepted(self) -> None:
        value = reader_review()

        validated = validate_writing_coverage(
            value,
            expected_candidate_ref=CANDIDATE,
            expected_candidate_tree_hash="sha256:candidate-tree",
            expected_profile_ref=value["profile_ref"],
            expected_guide_ref=value["guide_ref"],
            expected_review_contract_ref=REVIEW_CONTRACT,
            expected_output_contract_ref=OUTPUT_CONTRACT,
            expected_author_execution_ref=AUTHOR,
            required_rule_ids=[],
            required_check_ids=[],
            candidate_line_count=20,
            available_finding_ids=set(),
            expected_visual_pairs=[],
        )

        self.assertEqual(validated["schema_version"], "document-experience-reader-review.v3")
        self.assertNotIn("required_rule_results", validated)
        self.assertNotIn("delivery_check_results", validated)

    def test_review_contract_must_match_dispatch_authority(self) -> None:
        value = reader_review()
        value["review_contract_ref"]["hash"] = "sha256:forged"
        value["isolated_input_refs"][3] = copy.deepcopy(value["review_contract_ref"])

        with self.assertRaisesRegex(WritingReviewError, "review_contract_ref"):
            validate_writing_coverage(
                value,
                expected_candidate_ref=CANDIDATE,
                expected_candidate_tree_hash="sha256:candidate-tree",
                expected_profile_ref=value["profile_ref"],
                expected_guide_ref=value["guide_ref"],
                expected_review_contract_ref=REVIEW_CONTRACT,
                expected_output_contract_ref=OUTPUT_CONTRACT,
                expected_author_execution_ref=AUTHOR,
                required_rule_ids=[],
                required_check_ids=[],
                candidate_line_count=20,
                available_finding_ids=set(),
                expected_visual_pairs=[],
            )

    def test_findings_bind_failed_outcomes_and_diagnosis_to_normal_findings(self) -> None:
        value = finding_reader_review()

        validated = validate_reader(value, {"f-reader", "f-verbosity"})

        self.assertEqual(
            set(validated["finding_refs"]), {"f-reader", "f-verbosity"}
        )

    def test_observed_visual_pass_binds_every_exact_safe_pair(self) -> None:
        value = reader_review()
        value["visual_assessment"] = {
            "verdict": "PASS",
            "observation_status": "OBSERVED",
            "visual_pair_refs": [copy.deepcopy(VISUAL_PAIR)],
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": [],
            "finding_refs": [],
            "reason": "独立 Reviewer 已查看这张图；机械合同仅证明它安全且绑定准确。",
        }

        validated = validate_reader(value, visual_pairs=[VISUAL_PAIR])

        self.assertEqual(
            validated["visual_assessment"]["observation_status"], "OBSERVED"
        )
        self.assertEqual(
            validated["claim_boundary"],
            "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
        )

    def test_observed_visual_rejects_mismatched_or_stale_asset_hash(self) -> None:
        value = reader_review()
        stale = copy.deepcopy(VISUAL_PAIR)
        stale["svg_ref"]["hash"] = "sha256:stale"
        value["visual_assessment"] = {
            "verdict": "PASS",
            "observation_status": "OBSERVED",
            "visual_pair_refs": [stale],
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": [],
            "finding_refs": [],
            "reason": "已查看。",
        }

        with self.assertRaisesRegex(WritingReviewError, "exact safe visual pair"):
            validate_reader(value, visual_pairs=[VISUAL_PAIR])

    def test_not_needed_requires_concrete_reason_and_candidate_without_visual_pair(self) -> None:
        value = reader_review()
        validate_reader(value, visual_pairs=[])

        with self.assertRaisesRegex(WritingReviewError, "NOT_NEEDED"):
            validate_reader(value, visual_pairs=[VISUAL_PAIR])

    def test_finding_without_visual_binds_normal_review_finding(self) -> None:
        value = reader_review()
        value["visual_assessment"] = {
            "verdict": "FINDING",
            "observation_status": "NOT_OBSERVED",
            "visual_pair_refs": [],
            "issue_types": ["REPRESENTATION_COLLISION"],
            "repair_techniques": ["VISUALIZE"],
            "basis_refs": _basis(),
            "finding_refs": ["f-visual"],
            "reason": "复杂分支没有可观察的视觉表达。",
        }
        value["finding_refs"] = ["f-visual"]

        validated = validate_reader(value, {"f-visual"}, visual_pairs=[])

        self.assertEqual(validated["finding_refs"], ["f-visual"])

    def test_missing_readback_is_rejected(self) -> None:
        value = reader_review()
        value["reader_readback"]["main_path_and_recovery"] = ""

        with self.assertRaisesRegex(WritingReviewError, "main_path_and_recovery"):
            validate_reader(value)

    def test_readback_mental_model_requires_unique_component_names(self) -> None:
        value = reader_review()
        value["reader_readback"]["mental_model"][1]["name"] = value[
            "reader_readback"
        ]["mental_model"][0]["name"]

        with self.assertRaisesRegex(WritingReviewError, "component names"):
            validate_reader(value)

    def test_readback_navigation_covers_rules_acceptance_and_risks(self) -> None:
        value = reader_review()
        value["reader_readback"]["navigation_map"].pop()

        with self.assertRaisesRegex(WritingReviewError, "navigation_map"):
            validate_reader(value)

    def test_illegal_outcome_enum_is_rejected(self) -> None:
        value = finding_reader_review()
        value["reader_outcome_failures"][0]["outcome"] = "ELOQUENT"

        with self.assertRaisesRegex(WritingReviewError, "outcome"):
            validate_reader(value, {"f-reader", "f-verbosity"})

    def test_finding_requires_exact_basis(self) -> None:
        value = finding_reader_review()
        value["verbosity_assessment"]["basis_refs"] = []

        with self.assertRaisesRegex(WritingReviewError, "basis_refs"):
            validate_reader(value, {"f-reader", "f-verbosity"})

    def test_finding_basis_must_be_inside_exact_candidate(self) -> None:
        value = finding_reader_review()
        value["reader_outcome_failures"][0]["basis_refs"][0]["end_line"] = 21

        with self.assertRaisesRegex(WritingReviewError, "outside the Candidate"):
            validate_reader(value, {"f-reader", "f-verbosity"})

    def test_finding_refs_must_equal_union_of_failures_and_assessments(self) -> None:
        value = finding_reader_review()
        value["finding_refs"] = ["f-reader"]

        with self.assertRaisesRegex(WritingReviewError, "equal every"):
            validate_reader(value, {"f-reader", "f-verbosity"})

    def test_finding_must_reference_existing_normal_review_finding(self) -> None:
        value = finding_reader_review()

        with self.assertRaisesRegex(WritingReviewError, "available Review Finding"):
            validate_reader(value, {"f-reader"})

    def test_same_author_and_reviewer_execution_is_rejected(self) -> None:
        value = reader_review()
        value["reviewer_execution_ref"] = copy.deepcopy(AUTHOR)

        with self.assertRaisesRegex(WritingReviewError, "must differ"):
            validate_reader(value)

    def test_same_execution_id_is_rejected_even_when_kinds_differ(self) -> None:
        value = reader_review()
        value["reviewer_execution_ref"] = {
            "kind": "HOST_SUBAGENT_ATTEMPT",
            "id": value["author_execution_ref"]["id"],
        }

        with self.assertRaisesRegex(WritingReviewError, "execution id"):
            validate_reader(value)

    def test_stale_candidate_tree_is_rejected(self) -> None:
        value = reader_review()
        value["candidate_tree_hash"] = "sha256:stale"

        with self.assertRaisesRegex(WritingReviewError, "tree hash is stale"):
            validate_reader(value)

    def test_profile_and_guide_mismatch_are_rejected(self) -> None:
        for field in ("profile_ref", "guide_ref"):
            with self.subTest(field=field):
                value = reader_review()
                value[field]["hash"] = "sha256:forged"
                value["isolated_input_refs"][1 if field == "profile_ref" else 2] = copy.deepcopy(
                    value[field]
                )
                with self.assertRaisesRegex(WritingReviewError, field):
                    validate_reader(value)

    def test_output_contract_mismatch_is_rejected(self) -> None:
        value = reader_review()
        value["output_contract_ref"]["hash"] = "sha256:forged"
        value["isolated_input_refs"][4] = copy.deepcopy(value["output_contract_ref"])

        with self.assertRaisesRegex(WritingReviewError, "output_contract_ref"):
            validate_reader(value)

    def test_v05_ordinary_review_reuses_v3_result_schema_with_v321_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            candidate = project / "candidate.md"
            candidate.write_text("# PRD\n\n正文。\n", encoding="utf-8")
            candidate_ref = {
                "path": "candidate.md",
                "hash": sha256_file(candidate),
                "version": "v0.1",
            }
            profile_ref = {
                "path": "references/policies/prd-writing-profile-v0.5.json",
                "hash": "sha256:profile-v0.5",
                "version": "0.5.0",
            }
            guide_ref = {
                "path": "references/policies/prd-writing-guide-v0.5.md",
                "hash": "sha256:guide-v0.5",
                "version": "0.5.0",
            }
            review_contract_ref = {
                "path": "references/reviewer-profiles/prd-writing-reader-review-v3.2.1.json",
                "hash": "sha256:reader-review-v3.2.1",
                "version": "v3.2.1",
            }
            value = reader_review()
            value.update(
                {
                    "candidate_ref": candidate_ref,
                    "candidate_tree_hash": "sha256:candidate-tree",
                    "profile_ref": profile_ref,
                    "guide_ref": guide_ref,
                    "review_contract_ref": review_contract_ref,
                    "isolated_input_refs": [
                        candidate_ref,
                        profile_ref,
                        guide_ref,
                        review_contract_ref,
                        OUTPUT_CONTRACT,
                    ],
                }
            )
            review_path = project / "writing-review.json"
            atomic_write_json(review_path, value)
            review_ref = {
                "path": "writing-review.json",
                "hash": sha256_file(review_path),
                "version": 3,
            }

            try:
                validated = load_and_validate_writing_coverage(
                    project,
                    review_ref,
                    context={
                        "schema_version": "writing-review-dispatch.v3",
                        "candidate_ref": candidate_ref,
                        "candidate_tree_hash": "sha256:candidate-tree",
                        "profile_ref": profile_ref,
                        "guide_ref": guide_ref,
                        "review_contract_ref": review_contract_ref,
                        "output_contract_ref": OUTPUT_CONTRACT,
                        "author_execution_ref": AUTHOR,
                        "reader_visible_visual_pairs": [],
                        "visual_source_scan": {
                            "schema_version": "visual-source-scan.v1",
                            "status": "REVIEWABLE_SAFE_NOT_RENDERED",
                            "candidate_access_mode": "SOURCE_TEXT_ONLY",
                            "candidate_ref": candidate_ref,
                            "issues": [],
                            "safe_visual_pairs": [],
                            "render_status": "NOT_RENDERED",
                        },
                    },
                    available_finding_ids=set(),
                )
            except WritingReviewError as error:
                self.fail(str(error))

            self.assertEqual(
                validated["schema_version"],
                "document-experience-reader-review.v3",
            )
            self.assertNotIn("primary_objective", validated)


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

    def test_v1_same_execution_id_is_rejected_even_when_kinds_differ(self) -> None:
        value = coverage()
        value["reviewer_execution_ref"] = {
            "kind": "HOST_SUBAGENT_ATTEMPT",
            "id": value["author_execution_ref"]["id"],
        }

        with self.assertRaisesRegex(WritingReviewError, "execution id"):
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
            candidate.write_text(
                "# PRD\n\n正文。\n\n![legacy remote](https://example.com/legacy.png)\n",
                encoding="utf-8",
            )
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
    def test_explicit_v05_candidate_dispatches_exact_v321_ordinary_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            runtime = HostRuntime(project, GRAPH, SKILL_ROOT)
            run_id = "run-writing-dispatch-v05"
            runtime.controller.create_run(run_id, raw_signal="审查 v0.5 写作规范")
            candidate_root = project / "artifacts" / "prds" / "archived" / "V05"
            candidate_root.mkdir(parents=True)
            candidate = candidate_root / "V05_v0.1.md"
            candidate.write_text(
                "# 示例 PRD\n\n## 阅读摘要\n\n"
                '<svg viewBox="0 0 10 10"><text>legacy</text></svg>\n',
                encoding="utf-8",
            )
            profile_path = SKILL_ROOT / "policies" / "prd-writing-profile-v0.5.json"
            guide_path = SKILL_ROOT / "policies" / "prd-writing-guide-v0.5.md"
            self.assertTrue(profile_path.is_file(), "v0.5 runtime Profile must exist")
            self.assertTrue(guide_path.is_file(), "v0.5 runtime Guide must exist")
            output_path = SKILL_ROOT / "templates" / "contracts" / "prd-v0.2.json"
            metadata = candidate_root / "V05_v0.1.metadata.json"
            atomic_write_json(
                metadata,
                {
                    "prd_id": "V05",
                    "short_title": "示例",
                    "date": "2026-08-26",
                    "provenance": {"attempt_id": "attempt-author-v05"},
                    "document_experience": {
                        "profile_ref": {
                            "path": "references/policies/prd-writing-profile-v0.5.json",
                            "hash": sha256_file(profile_path),
                            "version": "0.5.0",
                        },
                        "writing_guide_ref": {
                            "path": "references/policies/prd-writing-guide-v0.5.md",
                            "hash": sha256_file(guide_path),
                            "version": "0.5.0",
                        },
                    },
                    "template_profile": {
                        "output_contract": {
                            "path": "references/templates/contracts/prd-v0.2.json",
                            "sha256": sha256_file(output_path),
                            "version": "better-product-graph.prd.general.0.2",
                        }
                    },
                },
            )
            review = candidate_root / "V05_v0.1.review.json"
            atomic_write_json(review, {"status": "NOT_RUN"})
            commitment = project / "product-commitment.json"
            atomic_write_json(commitment, {"goal": "降低遗漏风险"})
            commitment_ref = {
                "path": commitment.relative_to(project).as_posix(),
                "hash": sha256_file(commitment),
                "version": 1,
            }
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
                artifact_refs={
                    "prd-candidate": candidate_ref,
                    "product-commitment": commitment_ref,
                },
                state_updates={"current_candidate_ref": candidate_ref},
            )

            dispatch = runtime.dispatch_current(run_id)
            context = dispatch["writing_review_context"]
            dispatched_resource_ids = {
                item["resource_id"] for item in dispatch["resource_refs"]
            }

            self.assertEqual(context["schema_version"], "writing-review-dispatch.v3")
            self.assertEqual(context["profile_ref"]["version"], "0.5.0")
            self.assertEqual(
                context["review_contract_ref"]["path"],
                "references/reviewer-profiles/prd-writing-reader-review-v3.2.1.json",
            )
            self.assertEqual(context["review_contract_ref"]["version"], "v3.2.1")
            self.assertEqual(
                context["visual_source_scan"]["status"],
                "REVIEWABLE_UNSAFE_NOT_RENDERED",
            )
            self.assertEqual(
                context["visual_source_scan"]["candidate_access_mode"],
                "SOURCE_TEXT_ONLY",
            )
            self.assertEqual(
                context["visual_source_scan"]["candidate_ref"]["hash"],
                candidate_ref["hash"],
            )
            self.assertEqual(
                context["visual_source_scan"]["issues"][0]["basis_refs"][0]["start_line"],
                5,
            )
            self.assertEqual(context["visual_source_scan"]["render_status"], "NOT_RENDERED")
            self.assertEqual(len(context["isolated_input_refs"]), 5)
            self.assertTrue(
                {
                    "prd-writing-reader-review-v3.2.1",
                    "prd-writing-profile-v0.5",
                    "prd-writing-guide-v0.5",
                }.issubset(dispatched_resource_ids)
            )
            self.assertTrue(
                {
                    "writing-standard-coverage-contract",
                    "prd-writing-profile-v0.2",
                    "prd-writing-guide-v0.2",
                    "prd-writing-reader-review-v3",
                    "prd-writing-profile-v0.4",
                    "prd-writing-guide-v0.4",
                }.isdisjoint(dispatched_resource_ids)
            )

    def test_explicit_v04_candidate_dispatches_compact_v3_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            runtime = HostRuntime(project, GRAPH, SKILL_ROOT)
            run_id = "run-writing-dispatch-v04"
            runtime.controller.create_run(run_id, raw_signal="审查 v0.4 写作规范")
            candidate_root = project / "artifacts" / "prds" / "archived" / "V04"
            candidate_root.mkdir(parents=True)
            candidate = candidate_root / "V04_v0.1.md"
            candidate.write_text(
                "# 示例 PRD\n\n## 阅读摘要\n\n![消息主流程](./assets/main-flow.svg)\n",
                encoding="utf-8",
            )
            assets = candidate_root / "assets"
            assets.mkdir()
            (assets / "main-flow.svg").write_bytes(svg())
            (assets / "main-flow@2x.png").write_bytes(png())
            profile_path = SKILL_ROOT / "policies" / "prd-writing-profile-v0.4.json"
            guide_path = SKILL_ROOT / "policies" / "prd-writing-guide-v0.4.md"
            output_path = SKILL_ROOT / "templates" / "contracts" / "prd-v0.2.json"
            metadata = candidate_root / "V04_v0.1.metadata.json"
            atomic_write_json(
                metadata,
                {
                    "prd_id": "V04",
                    "short_title": "示例",
                    "date": "2026-08-26",
                    "provenance": {"attempt_id": "attempt-author-v04"},
                    "document_experience": {
                        "profile_ref": {
                            "path": "references/policies/prd-writing-profile-v0.4.json",
                            "hash": sha256_file(profile_path),
                            "version": "0.4.0",
                        },
                        "writing_guide_ref": {
                            "path": "references/policies/prd-writing-guide-v0.4.md",
                            "hash": sha256_file(guide_path),
                            "version": "0.4.0",
                        },
                    },
                    "template_profile": {
                        "output_contract": {
                            "path": "references/templates/contracts/prd-v0.2.json",
                            "sha256": sha256_file(output_path),
                            "version": "better-product-graph.prd.general.0.2",
                        }
                    },
                },
            )
            review = candidate_root / "V04_v0.1.review.json"
            atomic_write_json(review, {"status": "NOT_RUN"})
            commitment = project / "product-commitment.json"
            atomic_write_json(commitment, {"goal": "降低遗漏风险"})
            commitment_ref = {
                "path": commitment.relative_to(project).as_posix(),
                "hash": sha256_file(commitment),
                "version": 1,
            }
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
                artifact_refs={
                    "prd-candidate": candidate_ref,
                    "product-commitment": commitment_ref,
                },
                state_updates={"current_candidate_ref": candidate_ref},
            )

            dispatch = runtime.dispatch_current(run_id)
            context = dispatch["writing_review_context"]

            self.assertEqual(context["schema_version"], "writing-review-dispatch.v3")
            self.assertEqual(
                context["review_contract_ref"]["path"],
                "references/reviewer-profiles/prd-writing-reader-review-v3.json",
            )
            self.assertEqual(context["profile_ref"]["version"], "0.4.0")
            self.assertEqual(len(context["isolated_input_refs"]), 5)
            self.assertEqual(len(context["reader_visible_visual_pairs"]), 1)
            self.assertEqual(
                context["reader_visible_visual_pairs"][0]["svg_ref"]["path"],
                "artifacts/prds/archived/V04/assets/main-flow.svg",
            )
            self.assertNotIn("required_rule_ids", context)
            self.assertNotIn("required_check_ids", context)
            dispatched_resource_ids = {
                item["resource_id"] for item in dispatch["resource_refs"]
            }
            self.assertTrue(
                {
                    "prd-writing-reader-review-v3",
                    "prd-writing-profile-v0.4",
                    "prd-writing-guide-v0.4",
                }.issubset(dispatched_resource_ids)
            )
            self.assertTrue(
                {
                    "writing-standard-coverage-contract",
                    "prd-writing-profile-v0.2",
                    "prd-writing-guide-v0.2",
                }.isdisjoint(dispatched_resource_ids)
            )

            payload = reader_review()
            for field in (
                "candidate_ref",
                "candidate_tree_hash",
                "profile_ref",
                "guide_ref",
                "review_contract_ref",
                "output_contract_ref",
                "author_execution_ref",
                "isolated_input_refs",
            ):
                payload[field] = copy.deepcopy(context[field])
            payload["visual_assessment"] = {
                "verdict": "PASS",
                "observation_status": "OBSERVED",
                "visual_pair_refs": copy.deepcopy(
                    context["reader_visible_visual_pairs"]
                ),
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": "独立 Reviewer 已观察 exact 安全视觉资产。",
            }
            writing_path = project / "writing-review-v3.json"
            atomic_write_json(writing_path, payload)
            writing_ref = {
                "path": writing_path.relative_to(project).as_posix(),
                "hash": sha256_file(writing_path),
                "version": 3,
            }
            resources = {
                item["resource_id"]: item for item in dispatch["resource_refs"]
            }

            def exact(resource_id: str) -> dict:
                return {
                    key: resources[resource_id][key]
                    for key in ("path", "hash", "version")
                }

            result = {
                "schema_version": "node-result.v1",
                "node_id": "review.parallel",
                "attempt_id": dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": dispatch["instruction_ref"],
                "instruction_hash": dispatch["instruction_hash"],
                "input_refs": dispatch["input_refs"],
                "input_hashes": dispatch["input_hashes"],
                "resource_refs": dispatch["resource_refs"],
                "semantic_output": {
                    "candidate_ref": candidate_ref,
                    "reviewer_role": "product",
                    "roles_covered": [
                        "product",
                        "engineering_feasibility",
                        "testability",
                    ],
                    "authority": "ADVISORY_ONLY",
                    "goal_fidelity_refs": {
                        "profile_ref": exact("goal-fidelity-profile"),
                        "rubric_ref": exact("goal-fidelity-rubric"),
                        "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                        "commitment_refs": [commitment_ref],
                    },
                    "goal_fidelity_packet": {
                        "goal": "降低遗漏风险",
                        "candidate_ref": candidate_ref,
                        "commitment_refs": [commitment_ref],
                    },
                    "writing_coverage_ref": writing_ref,
                    "findings": [],
                },
                "artifact_refs": [{"role": "writing_coverage", **writing_ref}],
            }

            self.assertTrue(runtime.controller.submit_result(run_id, result).is_file())

    def test_review_dispatch_resolves_exact_project_output_contract(self) -> None:
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
            builtin_output_contract = (
                SKILL_ROOT / "templates" / "contracts" / "prd-v0.2.json"
            )
            output_contract = (
                project
                / ".better-product-graph"
                / "templates"
                / "test-product"
                / "1.0.0"
                / "OUTPUT_CONTRACT.json"
            )
            output_contract.parent.mkdir(parents=True)
            output_contract.write_bytes(builtin_output_contract.read_bytes())
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
                            "path": output_contract.relative_to(project).as_posix(),
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
            self.assertEqual(
                context["output_contract_ref"]["path"],
                output_contract.relative_to(project).as_posix(),
            )
            dispatched_resource_ids = {
                item["resource_id"] for item in dispatch["resource_refs"]
            }
            self.assertTrue(
                {
                    "writing-standard-coverage-contract",
                    "prd-writing-profile-v0.2",
                    "prd-writing-guide-v0.2",
                }.issubset(dispatched_resource_ids)
            )
            self.assertTrue(
                {
                    "prd-writing-reader-review-v3",
                    "prd-writing-profile-v0.4",
                    "prd-writing-guide-v0.4",
                }.isdisjoint(dispatched_resource_ids)
            )


if __name__ == "__main__":
    unittest.main()
