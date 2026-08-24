from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.bpg.prd_contract import PRDContractError, assemble_prd, prd_stem
from src.bpg.templates import TemplateRegistry


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "src" / "core" / "templates"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "prd-v0.2-golden"


def prd_markdown() -> str:
    return """# PRD-CHECKOUT-001_结算恢复体验_v0.1_2026-08-20

版本：v0.1｜状态：CANDIDATE

## 阅读摘要

结论：本次只交付失败可见与安全重试闭环。
下一步：进入独立产品、工程可行性和可测试性审查。

## 目标与成功边界

目标是让用户知道结算结果并安全恢复。证据：绑定 exact Decision 与 Plan。不能牺牲不重复扣款。

## 范围与交付切片

当前范围只含状态反馈与幂等重试；未来自动补偿不在本期。

## 验收标准

- AC-1: Given 首次提交失败，When 用户重试，Then 只产生一次有效结算且看到最终状态。

## 风险、未知与回滚

未知：边缘网络下状态传播时延。Authority：Owner 只授权当前 Slice。回滚：恢复旧入口并停止重试。

## 版本与变更

v0.1 首次形成候选；对应 DOCUMENT_CHANGELOG.md 将由版本机制维护。
"""


def prd_submission(markdown: str | None = None) -> dict:
    product_plan_ref = {"path": "plan-v1.md", "hash": "sha256:plan", "version": 1}
    slice_ref = {"path": "slice-v1.json", "hash": "sha256:slice", "version": 1}
    return {
        "node_id": "prd.generate",
        "attempt_id": "prd-attempt-1",
        "producer": {"kind": "HOST_AGENT", "host": "codex"},
        "instruction_ref": "references/atomic-skills/prd-generate/INSTRUCTIONS.md",
        "instruction_hash": "sha256:instructions",
        "input_refs": ["decision-v1.json", "plan-v1.json", "slice-v1.json"],
        "input_hashes": {
            "decision-v1.json": "sha256:decision",
            "plan-v1.json": "sha256:plan",
            "slice-v1.json": "sha256:slice",
        },
        "semantic_output": {
            "document_markdown": prd_markdown() if markdown is None else markdown,
            "template_mapping": {
                "summary": "阅读摘要",
                "goal": "目标与成功边界",
                "scope": "范围与交付切片",
                "acceptance": "验收标准",
                "risk": "风险、未知与回滚",
            },
            "metadata": {
                "prd_id": "PRD-CHECKOUT-001",
                "short_title": "结算恢复体验",
                "document_language": "zh-CN",
                "version": "v0.1",
                "date": "2026-08-20",
                "status": "CANDIDATE",
                "delivery_intent": "COMMIT",
                "decision_refs": [
                    {"path": "decision-v1.json", "hash": "sha256:decision", "version": 1}
                ],
                "roadmap_snapshot_ref": {
                    "path": "roadmap-v1.json",
                    "hash": "sha256:roadmap",
                    "version": 1,
                },
                "product_plan_ref": product_plan_ref,
                "slice_ref": slice_ref,
                "active_scope_ref": {
                    "schema_version": "active-scope-ref.v1",
                    "plan_ref": product_plan_ref,
                    "slice_id": "slice-1",
                    "projection_version": "active-scope-projection.v1",
                    "scope_hash": "sha256:scope",
                },
                "spec_traceability": {
                    "schema_version": "spec-traceability.v1",
                    "refs": [
                        {
                            "role": "product_plan",
                            **product_plan_ref,
                            "origin_node_id": "product.planning",
                            "origin_attempt_id": "attempt-plan-1",
                        },
                        {
                            "role": "slice",
                            **slice_ref,
                            "origin_node_id": "product.planning",
                            "origin_attempt_id": "attempt-plan-1",
                        },
                    ],
                },
                "product_runtime_inputs": {
                    "schema_version": "product-runtime-inputs.v1",
                    "required": [
                        {
                            "input_id": "project_workspace",
                            "kind": "PROJECT_WORKSPACE",
                            "resolver": "HOST_PROJECT_ROOT",
                            "binding_scope": "PROJECT",
                            "version_policy": "project-workspace.v1",
                            "on_missing": "FAIL_CLOSED",
                        },
                        {
                            "input_id": "product_signal",
                            "kind": "RAW_SIGNAL_OR_EXACT_OCCURRENCE",
                            "resolver": "SIGNAL_INTAKE",
                            "binding_scope": "INVOCATION_OR_PROJECT_INBOX",
                            "version_policy": "signal-contract.v1",
                            "on_missing": "REQUEST_SIGNAL",
                        },
                    ],
                    "optional": [],
                },
                "knowledge_snapshot_ref": {
                    "path": "knowledge-v1.json",
                    "hash": "sha256:knowledge",
                    "version": 1,
                },
                "evidence_refs": [
                    {"path": "evidence-v1.json", "hash": "sha256:evidence", "version": 1}
                ],
                "evals": {"applicability": "NOT_NEEDED", "reason": "确定性行为由 AC 覆盖"},
            },
        },
        "artifact_refs": [],
    }


def complete_experiment_contract() -> dict:
    return {
        "schema_version": "experiment-contract.v1",
        "key_unknown": "受控提示是否减少结算失败后的重复提交",
        "hypothesis": "向小范围用户解释状态并提供安全重试，会减少重复提交且不增加重复扣款",
        "audience_exposure": "仅向已进入结算失败恢复页的 5% 白名单用户展示",
        "specific_change": "展示结算状态解释和一个幂等重试入口",
        "observable_measurement": "重复提交率下降，同时重复扣款保持为零",
        "result_mapping": {
            "CONTINUE": "主指标改善且所有伤害护栏未触发",
            "ADJUST": "主指标方向正确但需要调整文案或曝光范围",
            "STOP": "触发任一伤害护栏或重复扣款不为零",
            "INCONCLUSIVE": "样本不足或数据质量无法支持判断",
        },
        "monitoring": "Owner 每日检查主指标、重复扣款与退出率",
        "kill_rollback": "触发 STOP 条件后立即停止曝光并恢复旧入口",
        "owner": "checkout-product-owner",
        "end_time": "2026-09-20",
        "harm_guardrails": ["重复扣款必须为零", "用户可以立即退出实验"],
        "typed_result_return": {
            "schema_version": "experiment-result-binding.v1",
            "ingress_node": "signal.ingest",
            "outcome_enum": ["CONTINUE", "ADJUST", "STOP", "INCONCLUSIVE"],
        },
    }


class PRDContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.selection = TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)

    def test_agent_authored_prd_is_validated_and_not_rewritten(self) -> None:
        submission = prd_submission()
        assembled = assemble_prd(submission, self.selection)
        self.assertEqual(assembled.markdown, submission["semantic_output"]["document_markdown"])
        self.assertEqual(assembled.metadata["template_profile"]["sha256"], self.selection.sha256)
        self.assertEqual(assembled.metadata["prd_id"], "PRD-CHECKOUT-001")
        self.assertEqual(
            assembled.metadata["document_experience"]["profile_ref"]["id"],
            "prd-plain-language-zh-CN",
        )
        self.assertEqual(
            assembled.metadata["document_experience"]["profile_ref"]["version"],
            "0.2.0",
        )

    def test_agent_cannot_substitute_a_different_document_experience_binding(self) -> None:
        submission = prd_submission()
        submission["semantic_output"]["metadata"]["document_experience"] = {
            "schema_version": "prd-document-experience-binding.v1",
            "profile_ref": {
                "id": "unregistered-profile",
                "version": "latest",
                "path": "latest",
                "hash": "sha256:untrusted",
            },
        }

        with self.assertRaisesRegex(PRDContractError, "Document Experience binding"):
            assemble_prd(submission, self.selection)

    def test_missing_structure_mode_uses_exact_template_default(self) -> None:
        submission = json.loads(
            (FIXTURES / "multi-module-split.json").read_text(encoding="utf-8")
        )
        submission["semantic_output"].pop("structure_mode")

        assembled = assemble_prd(submission, self.selection)

        self.assertEqual(assembled.metadata["structure_mode"], "split")

    def test_program_cannot_generate_prd_or_fill_missing_agent_content(self) -> None:
        submission = prd_submission()
        submission["producer"] = {"kind": "DETERMINISTIC_PROGRAM", "component": "validator"}
        submission["semantic_output"]["document_markdown"] = None
        with self.assertRaisesRegex(PRDContractError, "HOST_AGENT|Agent-authored"):
            assemble_prd(submission, self.selection)

    def test_template_placeholders_and_mutable_latest_refs_are_rejected(self) -> None:
        submission = prd_submission(prd_markdown() + "\n{{fill me}}\n")
        submission["semantic_output"]["metadata"]["product_plan_ref"]["path"] = "plan/latest.json"
        with self.assertRaises(PRDContractError) as captured:
            assemble_prd(submission, self.selection)
        self.assertIn("placeholder", str(captured.exception))
        self.assertIn("latest", str(captured.exception))

    def test_experiment_prd_requires_agent_authored_control_contract(self) -> None:
        submission = prd_submission()
        submission["semantic_output"]["metadata"]["delivery_intent"] = "EXPERIMENT"
        with self.assertRaisesRegex(PRDContractError, "experiment_contract"):
            assemble_prd(submission, self.selection)

    def test_experiment_prd_reports_exact_missing_type_and_enum_fields(self) -> None:
        cases = (
            ("missing key", lambda value: value.pop("key_unknown"),
             "experiment_contract.key_unknown must be a non-empty string"),
            ("wrong guardrail type", lambda value: value.__setitem__("harm_guardrails", "none"),
             "experiment_contract.harm_guardrails must be a non-empty array of non-empty strings"),
            ("missing result outcome", lambda value: value["result_mapping"].pop("STOP"),
             "experiment_contract.result_mapping must contain exactly CONTINUE, ADJUST, STOP, INCONCLUSIVE"),
            ("wrong ingress enum", lambda value: value["typed_result_return"].__setitem__("ingress_node", "product.decision"),
             "experiment_contract.typed_result_return.ingress_node must be 'signal.ingest'"),
        )
        for label, mutate, expected in cases:
            with self.subTest(label=label):
                submission = prd_submission()
                metadata = submission["semantic_output"]["metadata"]
                metadata["delivery_intent"] = "EXPERIMENT"
                metadata["experiment_contract"] = complete_experiment_contract()
                mutate(metadata["experiment_contract"])

                with self.assertRaises(PRDContractError) as captured:
                    assemble_prd(submission, self.selection)

                self.assertIn(expected, str(captured.exception))

    def test_complete_experiment_contract_is_accepted(self) -> None:
        submission = prd_submission()
        metadata = submission["semantic_output"]["metadata"]
        metadata["delivery_intent"] = "EXPERIMENT"
        metadata["experiment_contract"] = complete_experiment_contract()

        assembled = assemble_prd(submission, self.selection)

        self.assertEqual(
            assembled.metadata["experiment_contract"]["schema_version"],
            "experiment-contract.v1",
        )

    def test_prd_identity_requires_agent_authored_short_title_and_iso_date(self) -> None:
        submission = prd_submission()
        submission["semantic_output"]["metadata"].pop("short_title")
        submission["semantic_output"]["metadata"]["date"] = "today"
        with self.assertRaises(PRDContractError) as captured:
            assemble_prd(submission, self.selection)
        self.assertIn("short_title", str(captured.exception))
        self.assertIn("date", str(captured.exception))

    def test_localized_prd_title_forms_the_exact_directory_filename_and_h1_stem(self) -> None:
        submission = prd_submission()
        metadata = submission["semantic_output"]["metadata"]
        metadata["document_language"] = "zh-CN"
        metadata["short_title"] = "结算恢复体验"
        expected = "PRD-CHECKOUT-001_结算恢复体验_v0.1_2026-08-20"
        submission["semantic_output"]["document_markdown"] = prd_markdown()

        assembled = assemble_prd(submission, self.selection)

        self.assertEqual(
            prd_stem(
                metadata["prd_id"],
                metadata["short_title"],
                metadata["version"],
                metadata["date"],
            ),
            expected,
        )
        self.assertEqual(assembled.metadata["document_language"], "zh-CN")
        self.assertEqual(assembled.markdown.splitlines()[0], f"# {expected}")

    def test_legacy_structure_cannot_bypass_exact_h1_and_filename_identity(self) -> None:
        submission = prd_submission()
        submission["semantic_output"]["document_markdown"] = prd_markdown().replace(
            "# PRD-CHECKOUT-001_结算恢复体验_v0.1_2026-08-20",
            "# 结算恢复体验 PRD",
            1,
        )

        with self.assertRaisesRegex(
            PRDContractError,
            "unique Markdown H1 identity must exactly equal archive filename stem",
        ):
            assemble_prd(submission, self.selection)

    def test_localized_prd_identity_rejects_unsafe_paths_and_invalid_language_tags(self) -> None:
        cases = (
            ("path separator", "结算/恢复", "zh-CN", "safe immutable filename stem"),
            ("control character", "结算\n恢复", "zh-CN", "safe immutable filename stem"),
            ("invalid language", "结算恢复", "中文", "BCP-47 language tag"),
        )
        for label, short_title, language, expected in cases:
            with self.subTest(label=label):
                submission = prd_submission()
                metadata = submission["semantic_output"]["metadata"]
                metadata["short_title"] = short_title
                metadata["document_language"] = language
                with self.assertRaisesRegex(PRDContractError, expected):
                    assemble_prd(submission, self.selection)

    def test_prd_generate_cannot_self_claim_required_evals_are_reviewed(self) -> None:
        submission = prd_submission()
        submission["semantic_output"]["metadata"]["evals"] = {
            "applicability": "REQUIRED",
            "fulfillment": "REVIEWED",
            "fulfillment_authority": "CONTROLLER_BOUND",
            "execution_status": "NOT_RUN",
            "pack_ref": {"path": "pack.json", "hash": "sha256:pack", "version": 1},
            "review_ref": {"path": "review.json", "hash": "sha256:review", "version": 1},
            "ground_truth_provenance": {
                "type": "CONTRACT_DERIVED_EXPECTATIONS",
                "statement": "self-attested",
                "exact_refs": [],
            },
        }

        with self.assertRaisesRegex(
            PRDContractError, "REVIEWED|fulfillment authority|REVIEW_PENDING"
        ):
            assemble_prd(submission, self.selection)

    def test_closed_delivery_contracts_are_required(self) -> None:
        for field in ("active_scope_ref", "spec_traceability", "product_runtime_inputs"):
            with self.subTest(field=field):
                submission = prd_submission()
                submission["semantic_output"]["metadata"].pop(field)
                with self.assertRaisesRegex(PRDContractError, field):
                    assemble_prd(submission, self.selection)

    def test_runtime_required_inputs_cannot_be_empty_or_leak_spec_provenance(self) -> None:
        invalid_required = (
            [],
            [
                {
                    "input_id": "renamed_internal_input",
                    "kind": "PROJECT_FILE",
                    "resolver": "PROJECT_RELATIVE",
                    "binding_scope": "PROJECT",
                    "version_policy": "fixed.v1",
                    "on_missing": "FAIL_CLOSED",
                    "configuration": {
                        "alias": "plan-v1.md",
                        "nested": {"source": "attempt-plan-1"},
                    },
                }
            ],
            [
                {
                    "input_id": "machine_path",
                    "kind": "PROJECT_FILE",
                    "resolver": "/Users/example/Documents/spec.json",
                    "binding_scope": "PROJECT",
                    "version_policy": "current",
                    "on_missing": "FAIL_CLOSED",
                }
            ],
        )
        for required in invalid_required:
            with self.subTest(required=required):
                submission = prd_submission()
                submission["semantic_output"]["metadata"]["product_runtime_inputs"][
                    "required"
                ] = required
                with self.assertRaisesRegex(
                    PRDContractError,
                    "product_runtime_inputs|required|SPEC_REF_IN_RUNTIME_INPUTS|portable",
                ):
                    assemble_prd(submission, self.selection)

    def test_runtime_contract_freezes_the_two_portable_minimum_inputs(self) -> None:
        submission = prd_submission()
        required = submission["semantic_output"]["metadata"]["product_runtime_inputs"][
            "required"
        ]
        required.pop()
        with self.assertRaisesRegex(PRDContractError, "product_signal"):
            assemble_prd(submission, self.selection)

    def test_active_scope_ref_cannot_pin_candidate_version(self) -> None:
        submission = prd_submission()
        submission["semantic_output"]["metadata"]["active_scope_ref"][
            "candidate_version"
        ] = "v0.1"
        with self.assertRaisesRegex(PRDContractError, "active_scope_ref|Candidate version"):
            assemble_prd(submission, self.selection)

        plan_alias = prd_submission()
        plan_alias["semantic_output"]["metadata"]["product_plan_ref"][
            "candidate_version"
        ] = "v0.1"
        with self.assertRaisesRegex(PRDContractError, "Candidate|candidate"):
            assemble_prd(plan_alias, self.selection)

        nested_alias = prd_submission()
        nested_alias["semantic_output"]["metadata"]["product_plan_ref"][
            "extensions"
        ] = {"candidate_version": "v0.1"}
        with self.assertRaisesRegex(PRDContractError, "Candidate|candidate"):
            assemble_prd(nested_alias, self.selection)


if __name__ == "__main__":
    unittest.main()
