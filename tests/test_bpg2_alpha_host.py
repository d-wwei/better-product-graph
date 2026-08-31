from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.alpha_runtime import BPG2AlphaController
from src.bpg.runner import apply_alpha
from tests.test_bpg2_alpha_runtime import (
    REVIEW_RESPONSIBILITY_IDS,
    STAGE4_ARTIFACT_IDS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class BPG2AlphaHostTests(unittest.TestCase):
    def test_public_entry_routes_ordinary_bpg_to_the_bpg2_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "plugin"
            project = root / "project"
            project.mkdir()
            build_plugin(REPO_ROOT, plugin)
            runner = (
                plugin
                / "skills"
                / "better-product-graph"
                / "scripts"
                / "bpg_runner.py"
            )
            signal = "让独立 Review 与真实 HTML 证据进入 Ready 合同"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--operation",
                    "entry",
                    "$better-product-graph",
                    signal,
                ],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["status"], "HOST_AGENT_ACTION_REQUIRED")
            self.assertEqual(receipt["runtime"], "BPG_2_0_ALPHA")
            self.assertEqual(receipt["entry"], "$better-product-graph")
            self.assertEqual(receipt["signal"], signal)
            self.assertEqual(receipt["instructions"]["mode"], "DEFAULT_SINGLE_PRD")
            self.assertEqual(receipt["instructions"]["legacy_public_route"], "REMOVED")
            self.assertFalse(receipt["instructions"]["alpha_keyword_required"])
            self.assertEqual(
                receipt["instructions"]["product_semantics_owner"],
                "AUTHENTICATED_HOST_AGENT",
            )
            self.assertTrue(receipt["instructions"]["silent_fallback_forbidden"])
            self.assertFalse((project / ".better-product-graph").exists())

    def test_public_entry_normalizes_the_old_alpha_spelling_to_the_same_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "plugin"
            project = root / "project"
            project.mkdir()
            build_plugin(REPO_ROOT, plugin)
            runner = plugin / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"

            ordinary = subprocess.run(
                [sys.executable, str(runner), "$better-product-graph", "整理版本入口"],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            aliased = subprocess.run(
                [sys.executable, str(runner), "$better-product-graph", "alpha", "整理版本入口"],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
            self.assertEqual(aliased.returncode, 0, aliased.stderr)
            ordinary_receipt = json.loads(ordinary.stdout)
            aliased_receipt = json.loads(aliased.stdout)
            self.assertEqual(ordinary_receipt["runtime"], "BPG_2_0_ALPHA")
            self.assertEqual(aliased_receipt["runtime"], ordinary_receipt["runtime"])
            self.assertEqual(aliased_receipt["signal"], ordinary_receipt["signal"])
            self.assertFalse(ordinary_receipt["alias_used"])
            self.assertTrue(aliased_receipt["alias_used"])
            self.assertEqual(ordinary_receipt["instructions"], aliased_receipt["instructions"])
            self.assertFalse((project / ".better-product-graph").exists())

    def test_alpha_adapter_rejects_the_ambiguous_update_record_alias(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unsupported"):
                apply_alpha(Path(directory), {"action": "update-record"})

    def test_installed_skill_exposes_bpg2_as_the_default_and_removes_legacy_routing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            skill = (
                plugin / "skills" / "better-product-graph" / "SKILL.md"
            ).read_text(encoding="utf-8")
            baseline = (
                plugin
                / "skills"
                / "better-product-graph"
                / "references"
                / "alpha"
                / "BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.2.md"
            )

            self.assertIn("Default BPG 2.0 single-PRD runtime", skill)
            self.assertIn("legacy 0.x public route is removed", skill)
            self.assertIn("does not need to type `alpha`", skill)
            self.assertIn("not user syntax and not an opt-in product route", skill)
            self.assertNotIn("## Stable intents", skill)
            self.assertNotIn("--operation submit", skill)
            self.assertNotIn("--operation prepare-evals", skill)
            self.assertIn("replace-record", skill)
            self.assertNotIn("`update-record`", skill)
            self.assertIn("document-experience-reader-review.v3", skill)
            self.assertIn("Do not generate, open or review HTML during Candidate Review", skill)
            self.assertIn("This Alpha implements only `LOCAL_HTML`", skill)
            self.assertIn("optional `delivery_options` object", skill)
            self.assertIn("`LOCAL_HTML` defaults to `true`", skill)
            self.assertTrue(baseline.is_file())
            self.assertTrue(
                (
                    plugin
                    / "skills"
                    / "better-product-graph"
                    / "references"
                    / "templates"
                    / "general"
                    / "PRD_OUTPUT_CONTRACT_v2.0-alpha.json"
                ).is_file()
            )

    def test_installed_runner_accepts_one_alpha_json_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "plugin"
            project = root / "project"
            project.mkdir()
            build_plugin(REPO_ROOT, plugin)
            payload = project / "command.json"
            payload.write_text(
                json.dumps(
                    {
                        "action": "start",
                        "signal": "用户需要一个可恢复的本地规划流程",
                        "route": {
                            "destination": "PRODUCT_PLANNING",
                            "attempt_id": "installed-route",
                        },
                        "operation_id": "installed-start",
                        "run_id": "bpg2-run-installed",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(
                        plugin
                        / "skills"
                        / "better-product-graph"
                        / "scripts"
                        / "bpg_runner.py"
                    ),
                    "--operation",
                    "alpha",
                    "--payload-file",
                    str(payload),
                ],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            state = json.loads(completed.stdout)
            self.assertEqual(state["runtime"], "BPG_2_0_ALPHA")
            self.assertEqual(state["run_id"], "bpg2-run-installed")
            self.assertEqual(state["position"], "UNDERSTAND")

    def test_host_adapter_runs_one_commit_prd_to_local_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            def call(action: str, **values):
                return apply_alpha(project, {"action": action, **values})

            controller = BPG2AlphaController(project)

            def replace(
                state: dict,
                *,
                operation_id: str,
                author_attempt_id: str,
                position: str,
                heading: str,
                body: str,
                next_position: str | None = None,
                stage4_dispositions: list[dict] | None = None,
            ) -> dict:
                record_path = controller.run_path(state["run_id"]) / "planning-record.md"
                markdown = (
                    record_path.read_text(encoding="utf-8").rstrip()
                    + f"\n\n## {heading}\n\n{body}\n"
                )
                return call(
                    "replace-record",
                    run_id=state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id=operation_id,
                    author_attempt_id=author_attempt_id,
                    position=position,
                    mode="REPLACE_FULL",
                    base_hash=state["planning_record_ref"]["hash"],
                    next_position=next_position,
                    markdown=markdown,
                    stage4_dispositions=stage4_dispositions,
                )

            def prd_review_evidence(state: dict) -> dict:
                requirements = state["current_review_requirements"]
                context = requirements["writing_review_context"]
                writer_id = "host-prd-writing-reviewer"
                content_id = "host-prd-reviewer"
                writing_review = {
                    "schema_version": "document-experience-reader-review.v3",
                    "authority": "ADVISORY_ONLY",
                    "candidate_ref": deepcopy(context["candidate_ref"]),
                    "candidate_tree_hash": context["candidate_tree_hash"],
                    "profile_ref": deepcopy(context["profile_ref"]),
                    "guide_ref": deepcopy(context["guide_ref"]),
                    "review_contract_ref": deepcopy(context["review_contract_ref"]),
                    "output_contract_ref": deepcopy(context["output_contract_ref"]),
                    "author_execution_ref": deepcopy(context["author_execution_ref"]),
                    "reviewer_execution_ref": {
                        "kind": "HOST_SUBAGENT_ATTEMPT",
                        "id": writer_id,
                    },
                    "reviewer_role": "writing_standard",
                    "isolated_input_refs": deepcopy(context["isolated_input_refs"]),
                    "reader_readback": {
                        "problem_and_outcome": "用户无法确认后台任务结果，产品需要展示真实且可恢复的状态。",
                        "primary_relationships": "任务状态决定用户看到的结果和恢复动作。",
                        "mental_model": [
                            {"name": "任务", "role": "承载用户提交"},
                            {"name": "状态", "role": "表达处理结果"},
                            {"name": "恢复", "role": "支持失败重试"},
                        ],
                        "main_path_and_recovery": "用户提交并观察结果；失败时查看原因并重试。",
                        "decision_conditions_and_risks": "状态可信时采用；核心风险是误报结果。",
                        "navigation_map": [
                            {"target": "PRODUCT_RULES", "location": "产品需求与业务规则"},
                            {"target": "ACCEPTANCE", "location": "验收标准与效果衡量"},
                            {"target": "RISKS_UNKNOWNS_NEXT", "location": "风险、依赖与未决事项"},
                        ],
                    },
                    "reader_outcome_failures": [],
                    "verbosity_assessment": {
                        "verdict": "PASS", "issue_types": [], "repair_techniques": [],
                        "basis_refs": [], "finding_refs": [], "reason": "主路径清楚且没有重复合同。"
                    },
                    "checklist_assessment": {
                        "verdict": "PASS", "issue_types": [], "repair_techniques": [],
                        "basis_refs": [], "finding_refs": [], "reason": "必要产品边界和验收信息完整。"
                    },
                    "visual_assessment": {
                        "verdict": "NOT_NEEDED", "observation_status": "NOT_NEEDED",
                        "visual_pair_refs": [], "issue_types": [], "repair_techniques": [],
                        "basis_refs": [], "finding_refs": [],
                        "reason": "关系简单，文字和必要图示足以表达。"
                    },
                    "finding_refs": [],
                    "claim_boundary": "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
                }
                review_dir = controller.run_path(state["run_id"]) / "work" / "review"
                review_dir.mkdir(parents=True, exist_ok=True)
                writing_path = review_dir / "writing-review.json"
                writing_path.write_text(
                    json.dumps(writing_review, ensure_ascii=False, sort_keys=True),
                    encoding="utf-8",
                )
                return {
                    "review_basis_refs": deepcopy(requirements["review_basis_refs"]),
                    "responsibility_coverage": [
                        {
                            "responsibility_id": responsibility_id,
                            "reviewer_attempt_id": (
                                writer_id if responsibility_id == "DOCUMENT_EXPERIENCE" else content_id
                            ),
                            "status": "PASS",
                            "rationale": f"{responsibility_id} 已对当前 Candidate 检查。",
                            "basis_refs": [
                                requirements["review_basis_refs"]["prd"],
                            ],
                            "finding_ids": [],
                        }
                        for responsibility_id in REVIEW_RESPONSIBILITY_IDS
                    ],
                    "writing_review_ref": {
                        **controller.file_ref(writing_path),
                        "version": 1,
                    },
                }

            state = call(
                "start",
                signal="用户无法确认后台任务是否完成",
                route={"destination": "PRODUCT_PLANNING", "attempt_id": "host-route"},
                operation_id="host-start",
                run_id="bpg2-run-host",
            )
            state = replace(
                state,
                operation_id="host-understand",
                author_attempt_id="host-author-understand",
                position="UNDERSTAND",
                heading="UNDERSTAND",
                body="背景、目标、用户、需求、现状、差距和未知。",
                next_position="DIAGNOSE_VALUE",
            )
            state = replace(
                state,
                operation_id="host-diagnose",
                author_attempt_id="host-author-diagnose",
                position="DIAGNOSE_VALUE",
                heading="DIAGNOSE & VALUE",
                body="H1/H2/H3、因果、价值与成功标准。",
            )
            state = call(
                "freeze-candidate",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-problem-freeze",
                kind="PROBLEM",
                author_attempt_id="host-problem-author",
            )
            state = call(
                "review",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-problem-review",
                candidate_ref=state["current_candidate"],
                reviewer_attempt_id="host-problem-reviewer",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "host-problem-reviewer",
                },
                verdict="PASS",
                findings=[],
            )
            state = replace(
                state,
                operation_id="host-solutions",
                author_attempt_id="host-author-solutions",
                position="DISCOVER_SOLUTIONS_DECIDE",
                heading="Decision Candidate",
                body="推荐 COMMIT NOW，保留最强替代与改判条件。",
            )
            state = call(
                "freeze-candidate",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-decision-freeze",
                kind="DECISION",
                author_attempt_id="host-decision-author",
            )
            state = call(
                "review",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-decision-review",
                candidate_ref=state["current_candidate"],
                reviewer_attempt_id="host-decision-reviewer",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "host-decision-reviewer",
                },
                verdict="PASS",
                findings=[],
            )
            state = call(
                "decision-route",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-route-commit",
                candidate_ref=state["current_candidate"],
                actor={"kind": "AGENT", "id": "codex-host"},
                outcome="COMMIT_NOW",
                decision_authorization={
                    "source_message_ref": {
                        "kind": "HOST_MESSAGE",
                        "id": "host-preauthorization-message",
                    },
                    "run_id": state["run_id"],
                    "candidate_ref": state["current_candidate"],
                    "allowed_outcome": "COMMIT_NOW",
                    "permission_scope": "LOCAL_PLANNING_ONLY",
                    "issued_at": "2026-08-31T00:00:00+00:00",
                },
                agent_assessment={
                    "planning_record_ref": state["planning_record_ref"],
                    "goals_unchanged": True,
                    "local_planning_only": True,
                    "low_risk": True,
                    "reversible": True,
                    "no_high_impact_unknowns": True,
                    "rationale": "只继续本地产品规划和 PRD 编写。",
                    "reconsideration_conditions": "目标、风险或未知变化时升级 Owner。",
                },
            )
            state = replace(
                state,
                operation_id="host-plan",
                author_attempt_id="host-plan-author",
                position="PLAN_PRODUCT_SYSTEM",
                heading="整体—局部—整体",
                body="整体框架、关键局部、整体回归与单 PRD 边界。",
                next_position="PRD_AUTHORING",
                stage4_dispositions=[
                    {
                        "artifact_id": artifact_id,
                        "status": "COMPLETE",
                        "rationale": f"{artifact_id} 已完成并在当前主记录中可追溯。",
                    }
                    for artifact_id in STAGE4_ARTIFACT_IDS
                ],
            )
            draft = project / ".better-product-graph" / "v2" / "runs" / state["run_id"] / "work" / "prd"
            draft.mkdir(parents=True)
            (draft / "PRD.md").write_text(
                "# 后台任务结果可见性\n\n## 产品概览（TL;DR）\n\n让用户看见真实结果。\n\n"
                "## 产品背景、目标与问题定义\n\n状态不透明。\n\n"
                "## 方案概述与需求范围\n\n只覆盖结果可见性。\n\n"
                "## 核心体验与产品逻辑\n\n处理中、成功、可恢复失败。\n\n"
                "## 产品需求与业务规则\n\n重复提交不产生重复结果。\n\n"
                "## 验收标准与效果衡量\n\n用户能观察并恢复。\n\n"
                "## 风险、依赖与未决事项\n\n产品效果验证 NOT_RUN。\n",
                encoding="utf-8",
            )
            state = call(
                "freeze-candidate",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-prd-freeze",
                kind="PRD",
                author_attempt_id="host-prd-author",
                source_dir=str(draft.relative_to(project)),
                evals={
                    "applicability": "NOT_NEEDED",
                    "reason": "确定性验收足够",
                    "generator_capability": "NOT_IMPLEMENTED",
                    "generator_invocation_status": "NOT_RUN",
                    "execution_status": "NOT_RUN",
                    "attachment_paths": [],
                },
                document_experience={
                    "schema_version": "bpg2-alpha-document-experience.v1",
                    "author_attempt_id": "host-prd-author",
                    "draft_ref": controller.file_ref(draft / "PRD.md"),
                    "profile_id": "prd-plain-language-zh-CN",
                    "profile_version": "0.5.0",
                    "guide_id": "prd-writing-guide-v0.5",
                    "guide_version": "0.5.0",
                    "diagnoses": ["检查了主阅读路径、术语与状态边界。"],
                    "actions": ["前置结论并删除重复表达。"],
                    "zero_context_reading_path": "TL;DR → 流程 → 规则 → 验收 → 风险。",
                    "split_assessment": {
                        "decision": "KEEP_SINGLE",
                        "rationale": "一个目标和一条核心流程适合保持为单一 PRD。",
                    },
                    "claim_boundary": "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL",
                },
            )
            state = call(
                "review",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-prd-review",
                candidate_ref=state["current_candidate"],
                reviewer_attempt_id="host-prd-reviewer",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "host-prd-reviewer",
                },
                verdict="PASS",
                findings=[],
                **prd_review_evidence(state),
            )
            self.assertEqual(state["status"], "READY")
            state = call(
                "handoff",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-handoff",
                delivery_options={"LOCAL_HTML": True},
            )

            self.assertEqual(state["status"], "LOCAL_HANDOFF_COMPLETE")
            self.assertEqual(state["external_delivery"], "NOT_RUN")
            self.assertTrue((project / state["handoff"]["path"] / "PRD.html").is_file())


if __name__ == "__main__":
    unittest.main()
