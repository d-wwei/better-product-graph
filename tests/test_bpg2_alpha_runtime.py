from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from src.bpg.alpha_html import MermaidRenderError
from src.bpg.alpha_runtime import AlphaContractError, BPG2AlphaController
from src.bpg.storage import atomic_write_json as storage_atomic_write_json
from tests.test_bpg2_alpha_html import ZERO_CONTEXT_HTML


PRD_MARKDOWN = """# 单 PRD Alpha

## 产品概览（TL;DR）

让用户以可恢复、可理解的方式完成一个核心任务。

## 产品背景、目标与问题定义

目标用户当前无法确认任务是否完成，目标是让结果状态清楚可见。

## 方案概述与需求范围

本次只交付单一核心流程，不包含外部发送或研发实现。

## 核心体验与产品逻辑

用户提交后看到处理中、成功或可恢复失败状态。

## 产品需求与业务规则

- PRD-REQ-001：重复提交不得产生重复产品结果。

## 验收标准与效果衡量

- AC-001：用户可以观察最终状态并在失败后安全重试。

## 风险、依赖与未决事项

产品效果验证尚未执行。
"""

STAGE4_ARTIFACT_IDS = (
    "SCOPE_REQUIREMENTS_MATRIX",
    "TARGET_EXPERIENCE_CORE_FLOW",
    "PRODUCT_EXPERIENCE_INFORMATION_STRUCTURE",
    "LOGICAL_PRODUCT_SYSTEM",
    "MODULE_MAP_AND_DETAILS",
    "GLOBAL_RULES_SHARED_CONTRACTS",
    "COMPLETE_SYSTEM_ITERATION_STRUCTURE",
    "COHERENCE_COVERAGE_TRACEABILITY",
    "DATA_COLLECTION_APPLICABILITY",
)

REVIEW_RESPONSIBILITY_IDS = (
    "PRODUCT_GOAL_AND_REQUIREMENTS",
    "USER_EXPERIENCE_AND_CONTENT",
    "PRODUCT_SYSTEM_COHERENCE",
    "ENGINEERING_FEASIBILITY",
    "ACCEPTANCE_AND_VALIDATION_BOUNDARY",
    "DOCUMENT_EXPERIENCE",
)

RETROSPECTIVE_CONFORMANCE_IDS = (
    "PLANNING_RECORD_REPLACEMENT_SAFETY",
    "STAGE4_DISPOSITIONS",
    "DOCUMENT_EXPERIENCE",
    "REVIEW_BASIS",
    "SIX_REVIEW_RESPONSIBILITIES",
    "WRITING_REVIEW",
    "HANDOFF_DELIVERY_RENDERING",
    "NOT_RUN_BOUNDARIES",
)


class BPG2AlphaRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.controller = BPG2AlphaController(self.project)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def start(self, *, suffix: str = "1") -> dict:
        return self.controller.start_run(
            signal="用户无法确认异步任务是否已经完成",
            route={"destination": "PRODUCT_PLANNING", "attempt_id": f"route-{suffix}"},
            operation_id=f"start-{suffix}",
            run_id=f"bpg2-run-{suffix}",
        )

    def update_record(
        self,
        state: dict,
        *,
        position: str,
        next_position: str | None = None,
        suffix: str,
        stage4_dispositions: list[dict] | None = None,
    ) -> dict:
        record_path = self.controller.run_path(state["run_id"]) / "planning-record.md"
        current = record_path.read_text(encoding="utf-8")
        markdown = (
            current.rstrip()
            + "\n\n"
            + f"## {position} · {suffix}\n\n"
            + f"{suffix}：事实、推断、未知与当前结论保持可区分。\n"
        )
        return self.controller.replace_planning_record(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"record-{suffix}",
            author_attempt_id=f"author-{suffix}",
            position=position,
            mode="REPLACE_FULL",
            base_hash=state["planning_record_ref"]["hash"],
            markdown=markdown,
            next_position=next_position,
            stage4_dispositions=stage4_dispositions,
        )

    @staticmethod
    def complete_stage4_dispositions() -> list[dict]:
        return [
            {
                "artifact_id": artifact_id,
                "status": "COMPLETE",
                "rationale": f"{artifact_id} 已在当前产品规划主记录中完成并保持可追溯。",
            }
            for artifact_id in STAGE4_ARTIFACT_IDS
        ]

    @staticmethod
    def complete_retrospective_conformance() -> list[dict]:
        return [
            {
                "check_id": check_id,
                "status": "PASS",
                "rationale": f"{check_id} 已基于当前 Run 的精确证据核对。",
            }
            for check_id in RETROSPECTIVE_CONFORMANCE_IDS
        ]

    def reach_problem_review(self, *, suffix: str = "1") -> tuple[dict, dict]:
        state = self.start(suffix=suffix)
        state = self.update_record(
            state, position="UNDERSTAND", next_position="DIAGNOSE_VALUE", suffix=f"{suffix}-u"
        )
        state = self.update_record(
            state, position="DIAGNOSE_VALUE", suffix=f"{suffix}-d"
        )
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"freeze-problem-{suffix}",
            kind="PROBLEM",
            author_attempt_id=f"problem-author-{suffix}",
        )
        return state, state["current_candidate"]

    def reach_problem_rereview_authoring(
        self, *, suffix: str
    ) -> tuple[dict, dict, dict]:
        state, candidate = self.reach_problem_review(suffix=suffix)
        state = self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"review-revise-{suffix}",
            candidate_ref=candidate,
            reviewer_attempt_id=f"reviewer-{suffix}",
            reviewer_execution_ref={
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": f"reviewer-{suffix}",
            },
            verdict="REVISE",
            findings=[
                {
                    "finding_id": f"F-{suffix}",
                    "claim": "问题定义与成功标准需要修正。",
                    "evidence_refs": [candidate],
                    "severity": "MAJOR",
                    "affected_scope": ["问题定义", "成功标准"],
                    "invalidated_assumptions_or_artifacts": ["Problem Candidate"],
                    "local_revision_sufficiency": "SUFFICIENT",
                    "status": "OPEN",
                }
            ],
        )
        review = deepcopy(state["current_review"])
        state = self.controller.submit_review_route(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"route-revise-{suffix}",
            review_ref=review["review_ref"],
            lead_agent_attempt_id=f"lead-{suffix}",
            finding_refs=[f"F-{suffix}"],
            return_target="DIAGNOSE_VALUE",
            return_reason="修正问题定义与成功标准。",
            affected_scope=["问题定义", "成功标准"],
        )
        state = self.update_record(
            state,
            position="DIAGNOSE_VALUE",
            suffix=f"{suffix}-revision",
        )
        return state, deepcopy(candidate), review

    def pass_review(
        self,
        state: dict,
        candidate: dict,
        *,
        suffix: str,
        review_overrides: dict | None = None,
        visual_source_reviewed: bool = False,
    ) -> dict:
        values = {
            "candidate_ref": candidate,
            "reviewer_attempt_id": f"reviewer-{suffix}",
            "reviewer_execution_ref": {
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": f"reviewer-{suffix}",
            },
            "verdict": "PASS",
            "findings": [],
        }
        if candidate["kind"] == "PRD":
            values.update(
                self.prd_review_evidence(
                    state,
                    suffix=suffix,
                    visual_source_reviewed=visual_source_reviewed,
                )
            )
        if review_overrides:
            values.update(review_overrides)
        return self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"review-pass-{suffix}",
            **values,
        )

    def reach_decision_route(self, *, suffix: str = "1") -> tuple[dict, dict]:
        state = self.start(suffix=suffix)
        state = self.update_record(
            state, position="UNDERSTAND", next_position="DIAGNOSE_VALUE", suffix=f"{suffix}-u"
        )
        state = self.update_record(state, position="DIAGNOSE_VALUE", suffix=f"{suffix}-d")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"freeze-problem-{suffix}",
            kind="PROBLEM",
            author_attempt_id=f"problem-author-{suffix}",
        )
        state = self.pass_review(state, state["current_candidate"], suffix=f"problem-{suffix}")
        state = self.update_record(
            state,
            position="DISCOVER_SOLUTIONS_DECIDE",
            suffix=f"{suffix}-s",
        )
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"freeze-decision-{suffix}",
            kind="DECISION",
            author_attempt_id=f"decision-author-{suffix}",
        )
        state = self.pass_review(state, state["current_candidate"], suffix=f"decision-{suffix}")
        return state, state["current_candidate"]

    def choose(
        self,
        state: dict,
        candidate: dict,
        *,
        outcome: str,
        actor_kind: str = "OWNER",
        suffix: str,
        return_target: str | None = None,
        wait_condition: dict | None = None,
        cognition_change: dict | None = None,
        agent_assessment: dict | None = None,
        include_source_message_ref: bool = True,
        source_message_ref: object | None = None,
    ) -> dict:
        exact_candidate = {
            key: deepcopy(candidate[key])
            for key in (
                "candidate_id",
                "kind",
                "path",
                "hash",
                "version",
                "author_attempt_id",
                "revision_round",
                "artifact_path",
                "supersedes",
                "status",
            )
            if key in candidate
        }
        decision_authorization = {
            "run_id": state["run_id"],
            "candidate_ref": exact_candidate,
            "allowed_outcome": outcome,
            "permission_scope": (
                "LOCAL_PLANNING_ONLY"
                if actor_kind == "AGENT"
                else "RUN_DECISION_ONLY"
            ),
            "issued_at": "2026-08-31T00:00:00+00:00",
        }
        if include_source_message_ref:
            decision_authorization["source_message_ref"] = (
                source_message_ref
                if source_message_ref is not None
                else {
                    "kind": "HOST_MESSAGE",
                    "id": f"decision-message-{suffix}",
                }
            )
        return self.controller.submit_decision_route(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"decision-route-{suffix}",
            candidate_ref=candidate,
            actor={"kind": actor_kind, "id": "eli" if actor_kind == "OWNER" else "codex"},
            outcome=outcome,
            return_target=return_target,
            wait_condition=wait_condition,
            cognition_change=cognition_change,
            agent_assessment=agent_assessment,
            decision_authorization=decision_authorization,
        )

    @staticmethod
    def agent_assessment(state: dict) -> dict:
        return {
            "planning_record_ref": state["planning_record_ref"],
            "goals_unchanged": True,
            "local_planning_only": True,
            "low_risk": True,
            "reversible": True,
            "no_high_impact_unknowns": True,
            "rationale": "只继续本地 PRD 编写，不形成研发、资源、发布或外部承诺。",
            "reconsideration_conditions": "目标、风险或未知变化时重新 Review 并升级 Owner。",
        }

    def write_prd_draft(self, run_id: str, *, with_evals: bool = False) -> Path:
        draft = self.controller.prd_draft_path(run_id)
        draft.mkdir(parents=True, exist_ok=True)
        (draft / "PRD.md").write_text(PRD_MARKDOWN, encoding="utf-8")
        if with_evals:
            (draft / "product-evals.md").write_text(
                "# Product Evals\n\n规格已生成；执行状态：NOT_RUN。\n",
                encoding="utf-8",
            )
            (draft / "product-evals-review.json").write_text(
                json.dumps(
                    {
                        "verdict": "PASS",
                        "author_attempt_id": "eval-author",
                        "reviewer_attempt_id": "eval-reviewer",
                        "execution_status": "NOT_RUN",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        return draft

    def document_experience(self, state: dict, draft: Path, *, suffix: str) -> dict:
        return {
            "schema_version": "bpg2-alpha-document-experience.v1",
            "author_attempt_id": f"prd-author-{suffix}",
            "draft_ref": self.controller.file_ref(draft / "PRD.md"),
            "profile_id": "prd-plain-language-zh-CN",
            "profile_version": "0.5.0",
            "guide_id": "prd-writing-guide-v0.5",
            "guide_version": "0.5.0",
            "diagnoses": ["已检查主路径、信息密度、术语和状态边界。"],
            "actions": ["前置结论，压缩重复内容，并校验 TL;DR 与正文。"],
            "zero_context_reading_path": "标题与 TL;DR → 核心流程 → 规则 → 验收 → 风险。",
            "split_assessment": {
                "decision": "KEEP_SINGLE",
                "rationale": "单一目标、单一核心流程和共享规则需要保持同一叙事。",
            },
            "claim_boundary": "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL",
        }

    @staticmethod
    def evals(status: str, *, generated: bool = False) -> dict:
        attachments = (
            ["product-evals.md", "product-evals-review.json"] if generated else []
        )
        return {
            "applicability": status,
            "reason": "Agent 基于产品质量的可确定验收程度作出的轻量判断",
            "generator_capability": "SIMULATED" if generated else "NOT_IMPLEMENTED",
            "generator_invocation_status": "GENERATED" if generated else "NOT_RUN",
            "execution_status": "NOT_RUN",
            "attachment_paths": attachments,
        }

    def freeze_prd(
        self,
        state: dict,
        *,
        applicability: str = "NOT_NEEDED",
        generated: bool = False,
        suffix: str,
    ) -> dict:
        draft = self.write_prd_draft(state["run_id"], with_evals=generated)
        return self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"freeze-prd-{suffix}",
            kind="PRD",
            author_attempt_id=f"prd-author-{suffix}",
            source_dir=draft,
            evals=self.evals(applicability, generated=generated),
            document_experience=self.document_experience(state, draft, suffix=suffix),
        )

    def write_writing_review(
        self,
        state: dict,
        *,
        suffix: str,
        visual_source_reviewed: bool = False,
    ) -> tuple[dict, str]:
        context = state["current_review_requirements"]["writing_review_context"]
        writer_id = f"writing-reviewer-{suffix}"
        review = {
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
                "problem_and_outcome": "用户需要确认任务结果，产品要让真实状态可见并可恢复。",
                "primary_relationships": "提交产生任务，任务状态决定结果展示和恢复动作。",
                "mental_model": [
                    {"name": "任务", "role": "承载一次用户提交"},
                    {"name": "状态", "role": "表达处理中、成功或失败"},
                    {"name": "恢复", "role": "让失败任务能够安全重试"},
                ],
                "main_path_and_recovery": "用户提交并观察结果；失败时保留原因并安全重试。",
                "decision_conditions_and_risks": "只有状态可信时采用；主要风险是结果状态误报。",
                "navigation_map": [
                    {"target": "PRODUCT_RULES", "location": "产品需求与业务规则"},
                    {"target": "ACCEPTANCE", "location": "验收标准与效果衡量"},
                    {"target": "RISKS_UNKNOWNS_NEXT", "location": "风险、依赖与未决事项"},
                ],
            },
            "reader_outcome_failures": [],
            "verbosity_assessment": {
                "verdict": "PASS",
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": "主阅读路径紧凑且没有重复合同。",
            },
            "checklist_assessment": {
                "verdict": "PASS",
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": "必要边界与验收信息保持完整。",
            },
            "visual_assessment": {
                "verdict": "NOT_NEEDED",
                "observation_status": "NOT_NEEDED",
                "visual_pair_refs": [],
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": "关系简单，正文与必要图示已足够表达。",
            },
            "finding_refs": [],
            "claim_boundary": "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
        }
        if visual_source_reviewed:
            review["visual_assessment"] = {
                "verdict": "PASS",
                "observation_status": "SOURCE_REVIEWED",
                "visual_pair_refs": [],
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": "已直接审查 Mermaid source 的关系、标签、方向与阅读顺序。",
            }
        review_dir = self.controller.run_path(state["run_id"]) / "work" / "review"
        review_dir.mkdir(parents=True, exist_ok=True)
        path = review_dir / f"writing-review-{suffix}.json"
        path.write_text(json.dumps(review, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return {**self.controller.file_ref(path), "version": 1}, writer_id

    def prd_review_evidence(
        self,
        state: dict,
        *,
        suffix: str,
        visual_source_reviewed: bool = False,
    ) -> dict:
        requirements = state["current_review_requirements"]
        writing_ref, writer_id = self.write_writing_review(
            state,
            suffix=suffix,
            visual_source_reviewed=visual_source_reviewed,
        )
        content_id = f"reviewer-{suffix}"
        responsibilities = []
        for responsibility_id in REVIEW_RESPONSIBILITY_IDS:
            basis = [requirements["review_basis_refs"]["prd"]]
            reviewer_id = content_id
            if responsibility_id == "DOCUMENT_EXPERIENCE":
                reviewer_id = writer_id
            responsibilities.append(
                {
                    "responsibility_id": responsibility_id,
                    "reviewer_attempt_id": reviewer_id,
                    "status": "PASS",
                    "rationale": f"{responsibility_id} 已对当前冻结 Candidate 独立检查。",
                    "basis_refs": basis,
                    "finding_ids": [],
                }
            )
        return {
            "review_basis_refs": deepcopy(requirements["review_basis_refs"]),
            "responsibility_coverage": responsibilities,
            "writing_review_ref": writing_ref,
        }

    def reach_prd_authoring(
        self, *, intent: str, suffix: str, preauthorized: bool = False
    ) -> dict:
        state, candidate = self.reach_decision_route(suffix=suffix)
        state = self.choose(
            state,
            candidate,
            outcome=intent,
            actor_kind="AGENT" if preauthorized else "OWNER",
            agent_assessment=self.agent_assessment(state) if preauthorized else None,
            suffix=suffix,
        )
        if intent == "COMMIT_NOW":
            state = self.update_record(
                state,
                position="PLAN_PRODUCT_SYSTEM",
                next_position="PRD_AUTHORING",
                suffix=f"{suffix}-plan",
                stage4_dispositions=self.complete_stage4_dispositions(),
            )
        return state

    def test_planning_record_requires_explicit_full_replace_current_hash_and_section_preservation(self) -> None:
        state = self.start(suffix="replace")
        record_path = self.controller.run_path(state["run_id"]) / "planning-record.md"
        original = record_path.read_bytes()

        with self.assertRaisesRegex(AlphaContractError, "REPLACE_FULL"):
            self.controller.replace_planning_record(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="replace-missing-mode",
                author_attempt_id="replace-author",
                position="UNDERSTAND",
                mode="APPEND",
                base_hash=state["planning_record_ref"]["hash"],
                markdown="# 产品规划主记录\n\n## 新片段\n\n只有一个阶段。\n",
            )

        with self.assertRaisesRegex(AlphaContractError, "base_hash"):
            self.controller.replace_planning_record(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="replace-stale-base",
                author_attempt_id="replace-author",
                position="UNDERSTAND",
                mode="REPLACE_FULL",
                base_hash="sha256:stale",
                markdown="# 产品规划主记录\n\n## Signal 与当前边界\n\n完整稿。\n",
            )

        with self.assertRaisesRegex(AlphaContractError, "Signal 与当前边界"):
            self.controller.replace_planning_record(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="replace-fragment",
                author_attempt_id="replace-author",
                position="UNDERSTAND",
                mode="REPLACE_FULL",
                base_hash=state["planning_record_ref"]["hash"],
                markdown="# 产品规划主记录\n\n## DIAGNOSE & VALUE\n\n阶段片段。\n",
            )

        self.assertEqual(record_path.read_bytes(), original)
        self.assertEqual(self.controller.load_run(state["run_id"])["state_version"], state["state_version"])
        self.assertFalse(state["automatic_revision_exhausted"])

        replaced = self.update_record(
            state,
            position="UNDERSTAND",
            next_position="DIAGNOSE_VALUE",
            suffix="replace-success",
        )
        self.assertEqual(replaced["last_record_replacement"]["mode"], "REPLACE_FULL")
        self.assertEqual(replaced["last_record_replacement"]["old_hash"], state["planning_record_ref"]["hash"])
        self.assertEqual(replaced["last_record_replacement"]["new_hash"], replaced["planning_record_ref"]["hash"])

    def test_stage4_dispositions_are_complete_and_blocked_items_stop_prd_authoring(self) -> None:
        state, candidate = self.reach_decision_route(suffix="stage4")
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            suffix="stage4",
        )
        self.assertEqual(
            set(state["stage4_requirements"]["artifact_ids"]),
            set(STAGE4_ARTIFACT_IDS),
        )

        missing = self.complete_stage4_dispositions()[:-1]
        with self.assertRaisesRegex(AlphaContractError, "Stage 4"):
            self.update_record(
                state,
                position="PLAN_PRODUCT_SYSTEM",
                next_position="PRD_AUTHORING",
                suffix="stage4-missing",
                stage4_dispositions=missing,
            )

        blocked = self.complete_stage4_dispositions()
        blocked[-1] = {
            "artifact_id": "DATA_COLLECTION_APPLICABILITY",
            "status": "BLOCKED",
            "rationale": "缺少项目数据采集政策。",
            "missing_input": "项目数据采集政策",
            "owner": "PRODUCT_OWNER",
            "recovery": "补充政策后重新提交完整 Planning Record。",
        }
        with self.assertRaisesRegex(AlphaContractError, "BLOCKED"):
            self.update_record(
                state,
                position="PLAN_PRODUCT_SYSTEM",
                next_position="PRD_AUTHORING",
                suffix="stage4-blocked",
                stage4_dispositions=blocked,
            )

        advanced = self.update_record(
            state,
            position="PLAN_PRODUCT_SYSTEM",
            next_position="PRD_AUTHORING",
            suffix="stage4-complete",
            stage4_dispositions=self.complete_stage4_dispositions(),
        )
        self.assertEqual(advanced["position"], "PRD_AUTHORING")
        self.assertEqual(
            len(advanced["stage4_dispositions"]["items"]), len(STAGE4_ARTIFACT_IDS)
        )

    def test_prd_authoring_does_not_auto_rebind_stage4_after_record_change(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="stage4-stale")
        bound_ref = deepcopy(state["stage4_dispositions"]["record_ref"])

        changed = self.update_record(
            state,
            position="PRD_AUTHORING",
            suffix="stage4-stale-prd",
        )

        self.assertEqual(changed["stage4_dispositions"]["record_ref"], bound_ref)
        self.assertNotEqual(
            changed["stage4_dispositions"]["record_ref"],
            changed["planning_record_ref"],
        )

        changed = self.freeze_prd(changed, suffix="stage4-stale")
        changed = self.pass_review(
            changed,
            changed["current_candidate"],
            suffix="stage4-stale-prd",
        )
        self.assertEqual(changed["ready"]["status"], "NOT_READY")
        self.assertIn("STAGE4_RECORD_REF_STALE", changed["ready"]["unmet"])
        self.assertNotIn("STAGE4_DISPOSITIONS", changed["ready"]["unmet"])
        stale = next(
            item
            for item in changed["ready"]["unmet_details"]
            if item["reason"] == "STAGE4_RECORD_REF_STALE"
        )
        self.assertEqual(
            stale["expected_current_hash"],
            changed["current_candidate"]["planning_record_ref"]["hash"],
        )
        self.assertEqual(stale["actual_bound_hash"], bound_ref["hash"])
        self.assertIn("replace-record", stale["recovery"])
        self.assertIn("PRD_AUTHORING", stale["recovery"])
        self.assertIn("nine Stage 4 dispositions", stale["recovery"])

    def test_stage4_stale_ready_recovers_through_new_record_candidate_and_review(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="stage4-recovery")
        state = self.update_record(
            state,
            position="PRD_AUTHORING",
            suffix="stage4-recovery-change",
        )
        state = self.freeze_prd(state, suffix="stage4-recovery-old")
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="stage4-recovery-old-prd",
        )

        old_candidate = deepcopy(state["current_candidate"])
        old_review = deepcopy(state["current_review"])
        old_review_count = len(state["reviews"])
        self.assertEqual(state["ready"]["status"], "NOT_READY")
        self.assertIn("STAGE4_RECORD_REF_STALE", state["ready"]["unmet"])
        self.assertEqual(state["status"], "ACTIVE")
        self.assertEqual(state["position"], "PRD_AUTHORING")
        self.assertTrue(state["candidate_required"])
        self.assertEqual(state["current_candidate"]["status"], "STALE")
        self.assertEqual(state["current_review"]["verdict"], "PASS")

        state = self.update_record(
            state,
            position="PRD_AUTHORING",
            suffix="stage4-recovery-reconfirm",
            stage4_dispositions=self.complete_stage4_dispositions(),
        )
        self.assertEqual(state["current_candidate"], old_candidate)
        self.assertEqual(state["current_review"], old_review)
        self.assertEqual(
            state["stage4_dispositions"]["record_ref"],
            state["planning_record_ref"],
        )

        state = self.freeze_prd(state, suffix="stage4-recovery-new")
        new_candidate = state["current_candidate"]
        self.assertNotEqual(new_candidate["hash"], old_candidate["hash"])
        self.assertEqual(new_candidate["version"], old_candidate["version"] + 1)
        self.assertTrue(new_candidate["supersedes"])
        work_order = state["current_rereview_work_order"]
        self.assertEqual(work_order["source_candidate_ref"], new_candidate["supersedes"])
        self.assertEqual(
            work_order["current_candidate_ref"],
            {
                key: new_candidate[key]
                for key in ("candidate_id", "kind", "path", "hash", "version")
            },
        )
        self.assertEqual(work_order["review_ref"], old_review["review_ref"])
        self.assertEqual(work_order["finding_refs"], [])
        self.assertEqual(work_order["planning_record_ref"], state["planning_record_ref"])
        self.assertEqual(work_order["rereview_scope"], ["FULL_CANDIDATE"])
        self.assertEqual(
            work_order["scope_basis"], "BROAD_FALLBACK_NO_REVIEW_ROUTE"
        )
        self.assertEqual(
            state["current_review_requirements"]["rereview_work_order"],
            work_order,
        )
        self.assertEqual(
            self.controller.load_run(state["run_id"])["current_rereview_work_order"],
            work_order,
        )
        state = self.pass_review(
            state,
            new_candidate,
            suffix="stage4-recovery-new-prd",
            review_overrides={
                "review_mode": "DIFF_AND_REGRESSION",
                "diff_base_candidate_ref": new_candidate["supersedes"],
                "global_regression": "PASS",
            },
        )

        self.assertEqual(state["status"], "READY")
        self.assertEqual(state["position"], "READY")
        self.assertEqual(state["ready"]["status"], "READY")
        self.assertFalse(state["candidate_required"])
        self.assertNotIn("STAGE4_RECORD_REF_STALE", state["ready"]["unmet"])
        self.assertEqual(len(state["reviews"]), old_review_count + 1)
        self.assertIn(old_review, state["reviews"])

    def test_prd_authoring_explicit_stage4_reconfirmation_rebinds_current_record(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="stage4-reconfirm")
        stale_ref = deepcopy(state["stage4_dispositions"]["record_ref"])
        state = self.update_record(
            state,
            position="PRD_AUTHORING",
            suffix="stage4-reconfirm-change",
        )

        reconfirmed = self.update_record(
            state,
            position="PRD_AUTHORING",
            suffix="stage4-reconfirm-final",
            stage4_dispositions=self.complete_stage4_dispositions(),
        )

        self.assertNotEqual(reconfirmed["stage4_dispositions"]["record_ref"], stale_ref)
        self.assertEqual(
            reconfirmed["stage4_dispositions"]["record_ref"],
            reconfirmed["planning_record_ref"],
        )
        reconfirmed = self.freeze_prd(reconfirmed, suffix="stage4-reconfirm")
        reconfirmed = self.pass_review(
            reconfirmed,
            reconfirmed["current_candidate"],
            suffix="stage4-reconfirm-prd",
        )
        self.assertEqual(reconfirmed["ready"]["status"], "READY")
        self.assertNotIn("STAGE4_RECORD_REF_STALE", reconfirmed["ready"]["unmet"])

    def test_candidate_and_review_status_do_not_rewrite_the_planning_record(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="status-projection")
        planning_ref = deepcopy(state["planning_record_ref"])
        stage4_ref = deepcopy(state["stage4_dispositions"]["record_ref"])

        state = self.freeze_prd(state, suffix="status-projection")
        self.assertEqual(state["planning_record_ref"], planning_ref)
        self.assertEqual(state["stage4_dispositions"]["record_ref"], stage4_ref)

        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="status-projection-prd",
        )
        self.assertEqual(state["status"], "READY")
        self.assertEqual(state["planning_record_ref"], planning_ref)
        self.assertEqual(state["stage4_dispositions"]["record_ref"], stage4_ref)

    def test_prd_authoring_stage4_reconfirmation_rejects_incomplete_or_blocked_items(self) -> None:
        state = self.reach_prd_authoring(
            intent="COMMIT_NOW", suffix="stage4-reconfirm-invalid"
        )
        original_ref = deepcopy(state["planning_record_ref"])

        with self.assertRaisesRegex(AlphaContractError, "Stage 4"):
            self.update_record(
                state,
                position="PRD_AUTHORING",
                suffix="stage4-reconfirm-missing",
                stage4_dispositions=self.complete_stage4_dispositions()[:-1],
            )

        blocked = self.complete_stage4_dispositions()
        blocked[-1] = {
            "artifact_id": "DATA_COLLECTION_APPLICABILITY",
            "status": "BLOCKED",
            "rationale": "缺少项目数据采集政策。",
            "missing_input": "项目数据采集政策",
            "owner": "PRODUCT_OWNER",
            "recovery": "补充政策后重新提交完整 Planning Record。",
        }
        with self.assertRaisesRegex(AlphaContractError, "BLOCKED"):
            self.update_record(
                state,
                position="PRD_AUTHORING",
                suffix="stage4-reconfirm-blocked",
                stage4_dispositions=blocked,
            )

        current = self.controller.load_run(state["run_id"])
        self.assertEqual(current["planning_record_ref"], original_ref)
        self.assertEqual(
            current["stage4_dispositions"]["record_ref"],
            state["stage4_dispositions"]["record_ref"],
        )

    def test_prd_freeze_requires_document_experience_and_returns_exact_review_requirements(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="freeze-review-basis")
        draft = self.write_prd_draft(state["run_id"])
        with self.assertRaisesRegex(AlphaContractError, "document experience"):
            self.controller.freeze_candidate(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="freeze-without-document-experience",
                kind="PRD",
                author_attempt_id="prd-author-freeze-review-basis",
                source_dir=draft,
                evals=self.evals("NOT_NEEDED"),
            )

        frozen = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-with-document-experience",
            kind="PRD",
            author_attempt_id="prd-author-freeze-review-basis",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="freeze-review-basis"
            ),
        )
        requirements = frozen["current_review_requirements"]
        self.assertEqual(set(requirements["responsibility_ids"]), set(REVIEW_RESPONSIBILITY_IDS))
        self.assertEqual(
            requirements["writing_review_context"]["candidate_ref"],
            requirements["review_basis_refs"]["prd"],
        )
        self.assertNotIn("html", requirements["review_basis_refs"])
        profile_ref = requirements["review_basis_refs"]["writing_profile"]
        review_contract_ref = requirements["review_basis_refs"][
            "writing_review_contract"
        ]
        profile = json.loads(
            (self.project / profile_ref["path"]).read_text(encoding="utf-8")
        )
        review_contract = json.loads(
            (self.project / review_contract_ref["path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            profile["review_contract_id"],
            "prd-writing-reader-review-v3.1",
        )
        self.assertEqual(
            review_contract["resource_id"],
            "prd-writing-reader-review-v3.1.1",
        )
        self.assertEqual(
            requirements["writing_review_context"]["review_contract_ref"],
            requirements["review_basis_refs"]["writing_review_contract"],
        )
        self.assertEqual(
            requirements["review_basis_refs"]["writing_review_contract"]["version"],
            "v3.1.1",
        )
        exact_contract_ref = requirements["writing_review_context"][
            "review_contract_ref"
        ]
        self.assertEqual(
            self.controller.file_ref(self.project / exact_contract_ref["path"]),
            {
                "path": exact_contract_ref["path"],
                "hash": exact_contract_ref["hash"],
            },
        )
        exact_contract = json.loads(
            (self.project / exact_contract_ref["path"]).read_bytes()
        )
        self.assertIn("status_authority_boundary", exact_contract)
        manifest = json.loads(
            (self.project / frozen["current_candidate"]["path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], "bpg2-alpha-release-set.v3")
        self.assertEqual(
            manifest["document_experience"]["claim_boundary"],
            "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL",
        )

    def test_prd_freeze_defers_html_rendering_until_handoff(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="deferred-html")
        frozen = self.freeze_prd(state, suffix="deferred-html")

        requirements = frozen["current_review_requirements"]
        self.assertNotIn("current_rereview_work_order", frozen)
        self.assertNotIn("rereview_work_order", requirements)
        manifest = json.loads(
            (self.project / frozen["current_candidate"]["path"]).read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn("PRD.html", {item["path"] for item in manifest["files"]})
        self.assertFalse(
            (self.controller.run_path(state["run_id"]) / "candidates").exists()
        )
        self.assertNotIn("html", requirements["review_basis_refs"])
        self.assertNotIn("html_review_check_ids", requirements)
        self.assertEqual(manifest["delivery_rendering"], "DEFERRED_TO_HANDOFF")

    def test_mermaid_only_candidate_review_needs_no_rendered_visual(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="mermaid-source")
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n## 核心关系图\n\n"
            + "```mermaid\nflowchart LR\n  提交 --> 状态\n  状态 --> 恢复\n```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")

        frozen = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-mermaid-source",
            kind="PRD",
            author_attempt_id="prd-author-mermaid-source",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="mermaid-source"
            ),
        )
        context = frozen["current_review_requirements"]["writing_review_context"]
        self.assertNotIn("reader_visible_visual_pairs", context)
        self.assertNotIn("visual_source_scan", context)
        self.assertNotIn("visual_asset_refs", context)

        manifest = json.loads(
            (self.project / frozen["current_candidate"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual({item["path"] for item in manifest["files"]}, {"PRD.md"})
        self.assertEqual(manifest["editing_truth"], "PRD.md")
        prd_object_ref = manifest["files"][0]["object_ref"]
        self.assertEqual(manifest["review_requirements"]["review_basis_refs"]["prd"], prd_object_ref)
        self.assertEqual(context["isolated_input_refs"][0], prd_object_ref)
        self.assertTrue(manifest["candidate_tree_hash"].startswith("sha256:"))
        serialized = json.dumps(manifest, ensure_ascii=False)
        self.assertNotIn("component_hash", serialized)
        self.assertNotIn("responsibility_hash", serialized)

        reviewed = self.pass_review(
            frozen,
            frozen["current_candidate"],
            suffix="mermaid-source",
            visual_source_reviewed=True,
        )
        self.assertEqual(reviewed["ready"]["status"], "READY")

    @patch(
        "src.bpg.alpha_runtime.render_mermaid_svgs",
        return_value=[
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text x="1" y="5">flow</text></svg>'
        ],
    )
    def test_handoff_materializes_ready_mermaid_as_svg_and_html(
        self, render_mermaid: object
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="mermaid-handoff")
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n## 核心关系图\n\n"
            + "```mermaid\nflowchart LR\n  A --> B\n```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-mermaid-handoff",
            kind="PRD",
            author_attempt_id="prd-author-mermaid-handoff",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="mermaid-handoff"
            ),
        )
        manifest = json.loads(
            (self.project / state["current_candidate"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(any(item["path"].endswith(".svg") for item in manifest["files"]))
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="mermaid-handoff",
            visual_source_reviewed=True,
        )

        handoff = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-mermaid",
            delivery_options={
                "LOCAL_HTML": True,
                "LOCAL_RENDERED_VISUALS": True,
            },
        )
        handoff_dir = self.project / handoff["handoff"]["path"]
        generated_svg = handoff_dir / "assets" / "generated" / "mermaid-001.svg"
        self.assertTrue(generated_svg.is_file())
        html = (handoff_dir / "PRD.html").read_text(encoding="utf-8")
        self.assertIn("data:image/svg+xml;base64,", html)
        self.assertNotIn('<code class="language-mermaid">', html)
        render_mermaid.assert_called_once_with(markdown)
        manifest = json.loads(
            (handoff_dir / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["delivery"]["selected_modes"],
            ["LOCAL_HTML", "LOCAL_RENDERED_VISUALS"],
        )
        rendered_output = manifest["delivery"]["outputs"][
            "LOCAL_RENDERED_VISUALS"
        ]
        self.assertEqual(rendered_output["status"], "GENERATED")
        self.assertEqual(len(rendered_output["output_refs"]), 1)
        self.assertEqual(rendered_output["output_ref"], rendered_output["output_refs"][0])

    @patch(
        "src.bpg.alpha_runtime.render_self_contained_prd_html",
        side_effect=AssertionError("default Handoff must not render HTML"),
    )
    @patch(
        "src.bpg.alpha_runtime.render_mermaid_svgs",
        side_effect=MermaidRenderError("mmdc is NOT_IMPLEMENTED"),
    )
    def test_default_mermaid_handoff_needs_no_renderer_or_derived_output(
        self,
        render_mermaid: object,
        render_html: object,
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="minimal-mermaid")
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n```mermaid\nflowchart LR\n  A --> B\n```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-minimal-mermaid",
            kind="PRD",
            author_attempt_id="prd-author-minimal-mermaid",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="minimal-mermaid"
            ),
        )
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="minimal-mermaid",
            visual_source_reviewed=True,
        )

        handoff = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-minimal-mermaid",
        )
        replayed = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-minimal-mermaid",
        )

        handoff_dir = self.project / handoff["handoff"]["path"]
        self.assertEqual(replayed, handoff)
        self.assertEqual(handoff["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertEqual((handoff_dir / "PRD.md").read_text(encoding="utf-8"), markdown)
        self.assertFalse((handoff_dir / "PRD.html").exists())
        self.assertFalse((handoff_dir / "assets").exists())
        render_mermaid.assert_not_called()
        render_html.assert_not_called()

    @patch(
        "src.bpg.alpha_runtime.render_mermaid_svgs",
        side_effect=MermaidRenderError("mmdc is NOT_IMPLEMENTED"),
    )
    def test_legacy_local_html_option_remains_valid_without_rendered_visuals(
        self, render_mermaid: object
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="legacy-html")
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n```mermaid\nflowchart LR\n  A --> B\n```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-legacy-html",
            kind="PRD",
            author_attempt_id="prd-author-legacy-html",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="legacy-html"
            ),
        )
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="legacy-html",
            visual_source_reviewed=True,
        )

        handoff = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-legacy-html",
            delivery_options={"LOCAL_HTML": True},
        )

        handoff_dir = self.project / handoff["handoff"]["path"]
        html = (handoff_dir / "PRD.html").read_text(encoding="utf-8")
        manifest = json.loads(
            (handoff_dir / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertIn('<code class="language-mermaid">', html)
        self.assertFalse((handoff_dir / "assets").exists())
        self.assertEqual(manifest["delivery"]["selected_modes"], ["LOCAL_HTML"])
        self.assertEqual(
            manifest["delivery"]["outputs"]["LOCAL_HTML"]["status"], "GENERATED"
        )
        self.assertEqual(
            manifest["delivery"]["outputs"]["LOCAL_RENDERED_VISUALS"]["status"],
            "SKIPPED_NOT_SELECTED",
        )
        render_mermaid.assert_not_called()

    @patch(
        "src.bpg.alpha_runtime.render_self_contained_prd_html",
        side_effect=AssertionError("agent-authored HTML must not use Markdown fallback"),
    )
    def test_handoff_publishes_exact_agent_authored_zero_context_html(
        self, render_html: object
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="reader-html")
        state = self.freeze_prd(state, suffix="reader-html")
        state = self.pass_review(
            state, state["current_candidate"], suffix="reader-html"
        )
        source = (
            self.controller.run_path(state["run_id"])
            / "work"
            / "handoff"
            / "PRD.zero-context.html"
        )
        source.parent.mkdir(parents=True)
        source.write_text(ZERO_CONTEXT_HTML, encoding="utf-8")
        source_ref = self.controller.versioned_file_ref(
            source, state["current_candidate"]["version"]
        )

        handoff = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-reader-html",
            delivery_options={"LOCAL_HTML": True},
            html_source_ref=source_ref,
        )

        handoff_dir = self.project / handoff["handoff"]["path"]
        self.assertEqual(
            (handoff_dir / "PRD.html").read_text(encoding="utf-8"),
            ZERO_CONTEXT_HTML,
        )
        manifest = json.loads(
            (handoff_dir / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["delivery"]["html_generation"],
            {
                "schema_version": "bpg2-html-generation.v1",
                "mode": "AGENT_AUTHORED_ZERO_CONTEXT_VIEW",
                "input_ref": source_ref,
            },
        )
        self.assertEqual(
            manifest["delivery"]["source_truth_ref"]["hash"],
            self.controller.file_ref(handoff_dir / "PRD.md")["hash"],
        )
        render_html.assert_not_called()

    def test_handoff_rejects_invalid_agent_authored_html_without_partial_output(
        self,
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="bad-reader-html")
        state = self.freeze_prd(state, suffix="bad-reader-html")
        state = self.pass_review(
            state, state["current_candidate"], suffix="bad-reader-html"
        )
        source = (
            self.controller.run_path(state["run_id"])
            / "work"
            / "handoff"
            / "PRD.zero-context.html"
        )
        source.parent.mkdir(parents=True)
        source.write_text(
            ZERO_CONTEXT_HTML.replace(
                "</body>", "<script>console.log('x')</script></body>"
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(AlphaContractError, "zero-context HTML"):
            self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-bad-reader-html",
                delivery_options={"LOCAL_HTML": True},
                html_source_ref=self.controller.versioned_file_ref(
                    source, state["current_candidate"]["version"]
                ),
            )

        self.assertFalse(
            (self.controller.run_path(state["run_id"]) / "handoff" / "local").exists()
        )

    def test_handoff_rejects_reader_html_outside_run_work_or_wrong_version(
        self,
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="reader-ref")
        state = self.freeze_prd(state, suffix="reader-ref")
        state = self.pass_review(
            state, state["current_candidate"], suffix="reader-ref"
        )
        source = self.project / "outside-reader.html"
        source.write_text(ZERO_CONTEXT_HTML, encoding="utf-8")
        escaped_source = self.controller.run_path(state["run_id"]) / "outside-reader.html"
        escaped_source.write_text(ZERO_CONTEXT_HTML, encoding="utf-8")
        run_source = self.controller.run_path(state["run_id"]) / "work" / "reader.html"
        run_source.write_text(ZERO_CONTEXT_HTML, encoding="utf-8")
        escaped_ref = self.controller.file_ref(escaped_source)
        escaped_path = PurePosixPath(escaped_ref["path"])

        invalid_refs = {
            "outside work": self.controller.versioned_file_ref(
                source, state["current_candidate"]["version"]
            ),
            "lexical work escape": {
                "path": (
                    escaped_path.parent / "work" / ".." / escaped_path.name
                ).as_posix(),
                "hash": escaped_ref["hash"],
                "version": state["current_candidate"]["version"],
            },
            "wrong version": {
                **self.controller.file_ref(run_source),
                "version": state["current_candidate"]["version"] + 1,
            },
        }

        for label, source_ref in invalid_refs.items():
            with self.subTest(label=label):
                with self.assertRaises(AlphaContractError):
                    self.controller.prepare_local_handoff(
                        state["run_id"],
                        expected_state_version=state["state_version"],
                        operation_id=f"handoff-reader-ref-{label}",
                        delivery_options={"LOCAL_HTML": True},
                        html_source_ref=source_ref,
                    )

    def test_handoff_materializes_indented_uppercase_mermaid_when_html_is_off(
        self,
    ) -> None:
        state = self.reach_prd_authoring(
            intent="COMMIT_NOW", suffix="mermaid-indented-uppercase"
        )
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n## 核心关系图\n\n"
            + "   ```Mermaid\nflowchart LR\n  A --> B\n   ```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-mermaid-indented-uppercase",
            kind="PRD",
            author_attempt_id="prd-author-mermaid-indented-uppercase",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="mermaid-indented-uppercase"
            ),
        )
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="mermaid-indented-uppercase",
            visual_source_reviewed=True,
        )

        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><text>flow</text></svg>'

        def fake_mmdc(
            command: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            output_path = Path(command[command.index("--output") + 1])
            output_path.write_bytes(svg)
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch("src.bpg.alpha_html.shutil.which", return_value="/fake/mmdc"), patch(
            "src.bpg.alpha_html.subprocess.run", side_effect=fake_mmdc
        ):
            handoff = self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-mermaid-indented-uppercase",
                delivery_options={"LOCAL_RENDERED_VISUALS": True},
            )

        handoff_dir = self.project / handoff["handoff"]["path"]
        self.assertEqual(handoff["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertFalse((handoff_dir / "PRD.html").exists())
        self.assertEqual(
            (handoff_dir / "assets/generated/mermaid-001.svg").read_bytes(), svg
        )
        manifest = json.loads(
            (handoff_dir / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest["delivery"]["selected_modes"], ["LOCAL_RENDERED_VISUALS"]
        )
        self.assertEqual(
            manifest["delivery"]["outputs"]["LOCAL_RENDERED_VISUALS"]["status"],
            "GENERATED",
        )

    @patch(
        "src.bpg.alpha_runtime.render_mermaid_svgs",
        side_effect=MermaidRenderError("mmdc is NOT_IMPLEMENTED"),
    )
    def test_rendered_visuals_are_not_applicable_without_mermaid_source(
        self, render_mermaid: object
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="no-mermaid")
        state = self.freeze_prd(state, suffix="no-mermaid")
        state = self.pass_review(
            state, state["current_candidate"], suffix="no-mermaid"
        )

        handoff = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-no-mermaid",
            delivery_options={"LOCAL_RENDERED_VISUALS": True},
        )

        handoff_dir = self.project / handoff["handoff"]["path"]
        manifest = json.loads(
            (handoff_dir / "HANDOFF_MANIFEST.json").read_text(encoding="utf-8")
        )
        rendered_output = manifest["delivery"]["outputs"][
            "LOCAL_RENDERED_VISUALS"
        ]
        self.assertEqual(rendered_output["status"], "NOT_APPLICABLE")
        self.assertIsNone(rendered_output["output_ref"])
        self.assertEqual(rendered_output["output_refs"], [])
        self.assertFalse((handoff_dir / "assets").exists())
        render_mermaid.assert_not_called()

    @patch("src.bpg.alpha_runtime.render_mermaid_svgs", return_value=[])
    def test_handoff_rejects_mermaid_source_svg_count_mismatch_without_partial_output(
        self, _render_mermaid: object
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="mermaid-count")
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n```Mermaid\nflowchart LR\n  A --> B\n```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-mermaid-count",
            kind="PRD",
            author_attempt_id="prd-author-mermaid-count",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="mermaid-count"
            ),
        )
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="mermaid-count",
            visual_source_reviewed=True,
        )

        with self.assertRaisesRegex(
            AlphaContractError, "source count 1 differs from generated SVG count 0"
        ):
            self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-mermaid-count",
                delivery_options={"LOCAL_RENDERED_VISUALS": True},
            )
        self.assertFalse(
            (self.controller.run_path(state["run_id"]) / "handoff" / "local").exists()
        )

    @patch(
        "src.bpg.alpha_runtime.render_mermaid_svgs",
        side_effect=MermaidRenderError("mmdc is NOT_IMPLEMENTED"),
    )
    def test_handoff_fails_explicitly_without_mermaid_renderer(
        self, _render_mermaid: object
    ) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="mermaid-missing")
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n```mermaid\nflowchart LR\n  A --> B\n```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-mermaid-missing",
            kind="PRD",
            author_attempt_id="prd-author-mermaid-missing",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="mermaid-missing"
            ),
        )
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="mermaid-missing",
            visual_source_reviewed=True,
        )

        with self.assertRaisesRegex(
            AlphaContractError, "Mermaid rendering failed.*NOT_IMPLEMENTED"
        ):
            self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-mermaid-missing",
                delivery_options={"LOCAL_RENDERED_VISUALS": True},
            )
        self.assertFalse(
            (self.controller.run_path(state["run_id"]) / "handoff" / "local").exists()
        )

    def test_handoff_html_failure_leaves_no_final_target_and_can_retry(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="handoff-atomic")
        state = self.freeze_prd(state, suffix="handoff-atomic")
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="handoff-atomic-prd",
        )
        run_path = self.controller.run_path(state["run_id"])
        target = run_path / "handoff" / "local"
        handoff_before = deepcopy(state.get("handoff"))

        with patch(
            "src.bpg.alpha_runtime.render_self_contained_prd_html",
            side_effect=ValueError("simulated HTML renderer failure"),
        ):
            with self.assertRaisesRegex(ValueError, "simulated HTML renderer failure"):
                self.controller.prepare_local_handoff(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id="handoff-atomic-fails",
                    delivery_options={"LOCAL_HTML": True},
                )

        unchanged = self.controller.load_run(state["run_id"])
        self.assertEqual(unchanged["state_version"], state["state_version"])
        self.assertEqual(unchanged["status"], "READY")
        self.assertEqual(unchanged.get("handoff"), handoff_before)
        self.assertFalse(target.exists())
        self.assertFalse(
            any(
                path.name.startswith(".local-staging-")
                for path in (run_path / "handoff").iterdir()
            )
        )

        target.mkdir()
        sentinel = target / "user-owned.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        with self.assertRaisesRegex(AlphaContractError, "target already exists"):
            self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-atomic-preexisting",
            )
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
        sentinel.unlink()
        target.rmdir()

        completed = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-atomic-retry",
            delivery_options={"LOCAL_HTML": True},
        )
        self.assertEqual(completed["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertTrue(target.is_dir())

    def test_handoff_state_commit_failure_recovers_exact_published_target(self) -> None:
        state = self.reach_prd_authoring(
            intent="COMMIT_NOW", suffix="handoff-state-atomic"
        )
        state = self.freeze_prd(state, suffix="handoff-state-atomic")
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="handoff-state-atomic-prd",
        )
        run_path = self.controller.run_path(state["run_id"])
        state_path = run_path / "run.json"
        target = run_path / "handoff" / "local"
        handoff_before = deepcopy(state.get("handoff"))

        def fail_run_state_write(path: Path, value: object) -> None:
            if path == state_path:
                raise OSError("simulated run.json commit failure")
            storage_atomic_write_json(path, value)

        with patch(
            "src.bpg.alpha_runtime.atomic_write_json",
            side_effect=fail_run_state_write,
        ):
            with self.assertRaisesRegex(OSError, "run.json commit failure"):
                self.controller.prepare_local_handoff(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id="handoff-state-atomic-fails",
                )

        unchanged = self.controller.load_run(state["run_id"])
        self.assertEqual(unchanged["state_version"], state["state_version"])
        self.assertEqual(unchanged["status"], "READY")
        self.assertEqual(unchanged.get("handoff"), handoff_before)
        self.assertTrue((target / "HANDOFF_MANIFEST.json").is_file())
        self.assertFalse(
            any(
                path.name.startswith(".local-staging-")
                for path in (run_path / "handoff").iterdir()
            )
        )

        completed = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-state-atomic-retry",
        )
        self.assertEqual(completed["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertEqual(completed["handoff"]["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertEqual(
            completed["handoff"]["manifest_ref"],
            self.controller.file_ref(target / "HANDOFF_MANIFEST.json"),
        )

    @patch(
        "src.bpg.alpha_runtime.render_mermaid_svgs",
        return_value=[
            b'<svg xmlns="http://www.w3.org/2000/svg"><text>one</text></svg>',
            b'<svg xmlns="http://www.w3.org/2000/svg"><text>two</text></svg>',
        ],
    )
    def test_optional_handoff_recovers_exact_html_and_ordered_visual_refs(
        self, render_mermaid: object
    ) -> None:
        state = self.reach_prd_authoring(
            intent="COMMIT_NOW", suffix="handoff-optional-recovery"
        )
        draft = self.write_prd_draft(state["run_id"])
        markdown = (
            (draft / "PRD.md").read_text(encoding="utf-8")
            + "\n```mermaid\nflowchart LR\n  A --> B\n```\n"
            + "\n```mermaid\nsequenceDiagram\n  A->>B: done\n```\n"
        )
        (draft / "PRD.md").write_text(markdown, encoding="utf-8")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-handoff-optional-recovery",
            kind="PRD",
            author_attempt_id="prd-author-handoff-optional-recovery",
            source_dir=draft,
            evals=self.evals("NOT_NEEDED"),
            document_experience=self.document_experience(
                state, draft, suffix="handoff-optional-recovery"
            ),
        )
        state = self.pass_review(
            state,
            state["current_candidate"],
            suffix="handoff-optional-recovery-prd",
            visual_source_reviewed=True,
        )
        run_path = self.controller.run_path(state["run_id"])
        state_path = run_path / "run.json"
        target = run_path / "handoff" / "local"
        options = {"LOCAL_HTML": True, "LOCAL_RENDERED_VISUALS": True}

        def fail_run_state_write(path: Path, value: object) -> None:
            if path == state_path:
                raise OSError("simulated optional run.json commit failure")
            storage_atomic_write_json(path, value)

        with patch(
            "src.bpg.alpha_runtime.atomic_write_json",
            side_effect=fail_run_state_write,
        ):
            with self.assertRaisesRegex(OSError, "optional run.json commit failure"):
                self.controller.prepare_local_handoff(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id="handoff-optional-recovery",
                    delivery_options=options,
                )

        unchanged = self.controller.load_run(state["run_id"])
        self.assertEqual(unchanged["state_version"], state["state_version"])
        self.assertEqual(unchanged["status"], "READY")
        self.assertTrue(target.is_dir())

        completed = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-optional-recovery",
            delivery_options=options,
        )
        outputs = completed["handoff"]["delivery"]["outputs"]
        self.assertEqual(completed["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertEqual(
            outputs["LOCAL_HTML"]["output_refs"],
            [
                self.controller.versioned_file_ref(
                    target / "PRD.html", state["current_candidate"]["version"]
                )
            ],
        )
        self.assertEqual(
            outputs["LOCAL_RENDERED_VISUALS"]["output_refs"],
            [
                self.controller.file_ref(target / "assets/generated/mermaid-001.svg"),
                self.controller.file_ref(target / "assets/generated/mermaid-002.svg"),
            ],
        )
        render_mermaid.assert_called_once_with(markdown)

    @patch(
        "src.bpg.alpha_runtime.render_mermaid_svgs",
        return_value=[b'<svg xmlns="http://www.w3.org/2000/svg"><text>flow</text></svg>'],
    )
    def test_optional_handoff_recovery_rejects_swapped_or_wrong_output_paths(
        self, render_mermaid: object
    ) -> None:
        for mutation in ("swapped", "wrong-source-files"):
            with self.subTest(mutation=mutation):
                suffix = f"handoff-ref-{mutation}"
                state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix=suffix)
                draft = self.write_prd_draft(state["run_id"])
                markdown = (
                    (draft / "PRD.md").read_text(encoding="utf-8")
                    + "\n```mermaid\nflowchart LR\n  A --> B\n```\n"
                )
                (draft / "PRD.md").write_text(markdown, encoding="utf-8")
                state = self.controller.freeze_candidate(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id=f"freeze-{suffix}",
                    kind="PRD",
                    author_attempt_id=f"prd-author-{suffix}",
                    source_dir=draft,
                    evals=self.evals("NOT_NEEDED"),
                    document_experience=self.document_experience(
                        state, draft, suffix=suffix
                    ),
                )
                state = self.pass_review(
                    state,
                    state["current_candidate"],
                    suffix=f"{suffix}-prd",
                    visual_source_reviewed=True,
                )
                run_path = self.controller.run_path(state["run_id"])
                state_path = run_path / "run.json"
                target = run_path / "handoff" / "local"
                options = {"LOCAL_HTML": True, "LOCAL_RENDERED_VISUALS": True}

                def fail_run_state_write(path: Path, value: object) -> None:
                    if path == state_path:
                        raise OSError("simulated ref run.json commit failure")
                    storage_atomic_write_json(path, value)

                with patch(
                    "src.bpg.alpha_runtime.atomic_write_json",
                    side_effect=fail_run_state_write,
                ):
                    with self.assertRaisesRegex(OSError, "ref run.json commit failure"):
                        self.controller.prepare_local_handoff(
                            state["run_id"],
                            expected_state_version=state["state_version"],
                            operation_id=f"handoff-{suffix}",
                            delivery_options=options,
                        )

                manifest_path = target / "HANDOFF_MANIFEST.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                outputs = manifest["delivery"]["outputs"]
                if mutation == "swapped":
                    html_ref = deepcopy(outputs["LOCAL_HTML"]["output_ref"])
                    visual_ref = deepcopy(
                        outputs["LOCAL_RENDERED_VISUALS"]["output_ref"]
                    )
                    outputs["LOCAL_HTML"]["output_ref"] = visual_ref
                    outputs["LOCAL_HTML"]["output_refs"] = [visual_ref]
                    outputs["LOCAL_RENDERED_VISUALS"]["output_ref"] = html_ref
                    outputs["LOCAL_RENDERED_VISUALS"]["output_refs"] = [html_ref]
                else:
                    false_html_ref = self.controller.versioned_file_ref(
                        target / "PRD.md", state["current_candidate"]["version"]
                    )
                    false_visual_ref = self.controller.file_ref(target / "HANDOFF.md")
                    outputs["LOCAL_HTML"]["output_ref"] = false_html_ref
                    outputs["LOCAL_HTML"]["output_refs"] = [false_html_ref]
                    outputs["LOCAL_RENDERED_VISUALS"][
                        "output_ref"
                    ] = false_visual_ref
                    outputs["LOCAL_RENDERED_VISUALS"]["output_refs"] = [
                        false_visual_ref
                    ]
                manifest["delivery"]["primary_reading_ref"] = outputs["LOCAL_HTML"][
                    "output_ref"
                ]
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                    encoding="utf-8",
                )

                state_before = state_path.read_bytes()
                with self.assertRaisesRegex(AlphaContractError, "target already exists"):
                    self.controller.prepare_local_handoff(
                        state["run_id"],
                        expected_state_version=state["state_version"],
                        operation_id=f"handoff-{suffix}",
                        delivery_options=options,
                    )
                self.assertEqual(state_path.read_bytes(), state_before)
                self.assertEqual(
                    self.controller.load_run(state["run_id"])["status"], "READY"
                )

    def test_prd_review_v3_fails_closed_without_complete_independent_evidence(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="review-v3-negative")
        state = self.freeze_prd(state, suffix="review-v3-negative")
        candidate = state["current_candidate"]

        with self.assertRaisesRegex(AlphaContractError, "Review basis"):
            self.controller.submit_review(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="review-v3-missing-evidence",
                candidate_ref=candidate,
                reviewer_attempt_id="content-reviewer-negative",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "content-reviewer-negative",
                },
                verdict="PASS",
                findings=[],
            )

        complete = self.prd_review_evidence(state, suffix="review-v3-negative")
        missing_responsibility = deepcopy(complete)
        missing_responsibility["responsibility_coverage"] = missing_responsibility[
            "responsibility_coverage"
        ][:-1]
        with self.assertRaisesRegex(AlphaContractError, "responsibility"):
            self.controller.submit_review(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="review-v3-missing-responsibility",
                candidate_ref=candidate,
                reviewer_attempt_id="reviewer-review-v3-negative",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "reviewer-review-v3-negative",
                },
                verdict="PASS",
                findings=[],
                **missing_responsibility,
            )

        same_writer = deepcopy(complete)
        for item in same_writer["responsibility_coverage"]:
            if item["responsibility_id"] == "DOCUMENT_EXPERIENCE":
                item["reviewer_attempt_id"] = "reviewer-review-v3-negative"
        with self.assertRaisesRegex(AlphaContractError, "Document Experience.*Writing Reviewer"):
            self.controller.submit_review(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="review-v3-same-writer",
                candidate_ref=candidate,
                reviewer_attempt_id="reviewer-review-v3-negative",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "reviewer-review-v3-negative",
                },
                verdict="PASS",
                findings=[],
                **same_writer,
            )

        premature_render_review = deepcopy(complete)
        premature_render_review["rendered_html_review"] = {}
        with self.assertRaisesRegex(AlphaContractError, "belongs to Handoff"):
            self.controller.submit_review(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="review-v3-premature-render-review",
                candidate_ref=candidate,
                reviewer_attempt_id="reviewer-review-v3-negative",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "reviewer-review-v3-negative",
                },
                verdict="PASS",
                findings=[],
                **premature_render_review,
            )

        stale_basis = deepcopy(complete)
        stale_basis["review_basis_refs"]["writing_profile"]["hash"] = "sha256:stale"
        with self.assertRaisesRegex(AlphaContractError, "Review basis"):
            self.controller.submit_review(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="review-v3-stale-basis",
                candidate_ref=candidate,
                reviewer_attempt_id="reviewer-review-v3-negative",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "reviewer-review-v3-negative",
                },
                verdict="PASS",
                findings=[],
                **stale_basis,
            )

        stale_writing = deepcopy(complete)
        writing_path = self.project / stale_writing["writing_review_ref"]["path"]
        writing_payload = json.loads(writing_path.read_text(encoding="utf-8"))
        writing_payload["profile_ref"]["hash"] = "sha256:stale"
        writing_path.write_text(
            json.dumps(writing_payload, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        stale_writing["writing_review_ref"] = {
            **self.controller.file_ref(writing_path),
            "version": 1,
        }
        with self.assertRaisesRegex(AlphaContractError, "Writing Review evidence is invalid"):
            self.controller.submit_review(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="review-v3-stale-writing",
                candidate_ref=candidate,
                reviewer_attempt_id="reviewer-review-v3-negative",
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": "reviewer-review-v3-negative",
                },
                verdict="PASS",
                findings=[],
                **stale_writing,
            )

    def test_default_handoff_is_minimal_and_preserves_not_run_boundaries(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="review-v3-ready")
        state = self.freeze_prd(state, suffix="review-v3-ready")
        state = self.pass_review(
            state, state["current_candidate"], suffix="review-v3-ready"
        )
        self.assertEqual(state["status"], "READY")
        summary = state["ready"]["evidence_summary"]
        self.assertEqual(summary["contract_readiness"], "PASS")
        self.assertEqual(summary["agent_review"], "PASS")
        self.assertEqual(summary["writing_review"], "PASS")
        self.assertEqual(summary["handoff_rendering"], "NOT_RUN")
        self.assertEqual(summary["human_reader_validation"], "NOT_RUN")
        self.assertEqual(summary["product_eval_execution"], "NOT_RUN")
        self.assertEqual(summary["external_delivery"], "NOT_RUN")
        self.assertEqual(summary["engineering_received"], "NOT_RUN")
        self.assertEqual(summary["engineering_tests"], "NOT_RUN")
        self.assertEqual(summary["product_effect_validation"], "NOT_RUN")

        handoff = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="review-v3-ready-handoff",
        )
        manifest = json.loads(
            (self.project / handoff["handoff"]["manifest_ref"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            manifest["evidence_summary"]["handoff_rendering"],
            "SKIPPED_NOT_SELECTED",
        )
        self.assertEqual(manifest["delivery"]["selected_modes"], [])
        self.assertEqual(
            manifest["delivery"]["outputs"]["LOCAL_HTML"]["status"],
            "SKIPPED_NOT_SELECTED",
        )
        self.assertEqual(
            manifest["delivery"]["outputs"]["LOCAL_RENDERED_VISUALS"]["status"],
            "SKIPPED_NOT_SELECTED",
        )
        self.assertEqual(manifest["delivery_options"]["LOCAL_HTML"], False)
        self.assertEqual(
            manifest["delivery_options"]["LOCAL_RENDERED_VISUALS"], False
        )
        self.assertEqual(
            manifest["delivery_capabilities"]["implemented"],
            ["LOCAL_HTML", "LOCAL_RENDERED_VISUALS"],
        )
        self.assertEqual(
            manifest["delivery_capabilities"]["not_implemented"],
            ["LOCAL_DOCUMENT", "FEISHU_DOCUMENT", "PROJECT_MANAGEMENT_MCP"],
        )
        handoff_dir = self.project / handoff["handoff"]["path"]
        self.assertEqual(
            sorted(
                path.relative_to(handoff_dir).as_posix()
                for path in handoff_dir.rglob("*")
                if path.is_file()
            ),
            ["HANDOFF.md", "HANDOFF_MANIFEST.json", "PRD.md"],
        )
        note = (handoff_dir / "HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("Writing Review：PASS", note)
        self.assertIn("Handoff Rendering：SKIPPED_NOT_SELECTED", note)
        self.assertIn("Human Reader Validation：NOT_RUN", note)
        self.assertIn("Product Eval Execution：NOT_RUN", note)
        self.assertEqual(handoff["retrospective_status"], "NOT_RUN")
        self.assertEqual(
            set(handoff["retrospective_requirements"]["check_ids"]),
            set(RETROSPECTIVE_CONFORMANCE_IDS),
        )

    def test_local_handoff_rechecks_writing_evidence_freshness(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="handoff-freshness")
        state = self.freeze_prd(state, suffix="handoff-freshness")
        state = self.pass_review(
            state, state["current_candidate"], suffix="handoff-freshness"
        )
        writing_ref = state["current_review"]["writing_review_ref"]
        writing_path = self.project / writing_ref["path"]
        writing_path.write_bytes(b"changed-after-review")
        with self.assertRaisesRegex(AlphaContractError, "Ready evidence is stale"):
            self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-with-stale-writing-evidence",
            )

    def test_local_handoff_can_disable_html_generation(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="handoff-no-html")
        state = self.freeze_prd(state, suffix="handoff-no-html")
        output_contract_ref = state["current_review_requirements"]["review_basis_refs"][
            "output_contract"
        ]
        output_contract = json.loads(
            (self.project / output_contract_ref["path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(output_contract_ref["version"], "2.0-alpha.3")
        self.assertEqual(output_contract["editing_truth"], "PRD.md")
        self.assertEqual(
            output_contract["default_reading_view"],
            {
                "selection_stage": "HANDOFF",
                "when_local_html_enabled": "PRD.html",
                "when_local_html_disabled": "PRD.md",
                "authoritative_ref": "HANDOFF_MANIFEST.json#delivery.primary_reading_ref",
            },
        )
        state = self.pass_review(
            state, state["current_candidate"], suffix="handoff-no-html"
        )

        handoff = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-no-html",
            delivery_options={"LOCAL_HTML": False},
        )
        handoff_dir = self.project / handoff["handoff"]["path"]
        manifest = json.loads(
            (self.project / handoff["handoff"]["manifest_ref"]["path"]).read_text(
                encoding="utf-8"
            )
        )

        self.assertFalse((handoff_dir / "PRD.html").exists())
        self.assertTrue((handoff_dir / "PRD.md").is_file())
        self.assertEqual(manifest["delivery_options"]["LOCAL_HTML"], False)
        self.assertEqual(
            manifest["delivery_options"]["LOCAL_RENDERED_VISUALS"], False
        )
        self.assertEqual(
            manifest["delivery"]["outputs"]["LOCAL_HTML"]["status"],
            "SKIPPED_NOT_SELECTED",
        )
        self.assertEqual(
            manifest["delivery"]["primary_reading_ref"]["path"],
            (handoff_dir / "PRD.md").relative_to(self.project).as_posix(),
        )
        self.assertEqual(
            manifest["evidence_summary"]["handoff_rendering"],
            "SKIPPED_NOT_SELECTED",
        )

    def test_local_handoff_rejects_enabled_unimplemented_delivery_mode(self) -> None:
        state = self.reach_prd_authoring(
            intent="COMMIT_NOW", suffix="handoff-unimplemented"
        )
        state = self.freeze_prd(state, suffix="handoff-unimplemented")
        state = self.pass_review(
            state, state["current_candidate"], suffix="handoff-unimplemented"
        )

        with self.assertRaisesRegex(
            AlphaContractError, "FEISHU_DOCUMENT.*NOT_IMPLEMENTED"
        ):
            self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-unimplemented",
                delivery_options={"FEISHU_DOCUMENT": True},
            )
        self.assertFalse(
            (self.controller.run_path(state["run_id"]) / "handoff" / "local").exists()
        )

    def test_local_handoff_delivery_options_are_closed_booleans(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="handoff-options")
        state = self.freeze_prd(state, suffix="handoff-options")
        state = self.pass_review(
            state, state["current_candidate"], suffix="handoff-options"
        )

        for index, options in enumerate(
            (
                {"LOCAL_HTML": "false"},
                {"LOCAL_RENDERED_VISUALS": "true"},
                {"UNKNOWN_DELIVERY": False},
            ),
            start=1,
        ):
            with self.subTest(options=options), self.assertRaisesRegex(
                AlphaContractError, "delivery options"
            ):
                self.controller.prepare_local_handoff(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id=f"handoff-invalid-options-{index}",
                    delivery_options=options,
                )

    def test_start_creates_new_v2_run_and_is_idempotent_without_importing_old_run(self) -> None:
        old = self.project / ".better-product-graph" / "runs" / "run-old"
        old.mkdir(parents=True)
        (old / "state.json").write_text("{}", encoding="utf-8")

        state = self.start()
        repeated = self.start()

        self.assertEqual(state, repeated)
        self.assertEqual(state["runtime"], "BPG_2_0_ALPHA")
        self.assertEqual(state["position"], "UNDERSTAND")
        self.assertEqual(state["status"], "ACTIVE")
        self.assertTrue((self.controller.run_path(state["run_id"]) / "planning-record.md").is_file())
        self.assertIn("用户无法确认", (self.controller.run_path(state["run_id"]) / "planning-record.md").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(AlphaContractError, "BPG 2.0"):
            self.controller.load_run("run-old")

    def test_same_operation_id_with_changed_payload_is_rejected(self) -> None:
        self.start()
        with self.assertRaisesRegex(AlphaContractError, "operation identity conflict"):
            self.controller.start_run(
                signal="另一个 Signal",
                route={"destination": "PRODUCT_PLANNING", "attempt_id": "route-1"},
                operation_id="start-1",
                run_id="bpg2-run-1",
            )

    def test_candidate_is_immutable_and_reviewer_attempt_must_be_independent(self) -> None:
        state, candidate = self.reach_problem_review()
        candidate_path = self.project / candidate["path"]
        with self.assertRaisesRegex(AlphaContractError, "independent"):
            self.controller.submit_review(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="same-attempt-review",
                candidate_ref=candidate,
                reviewer_attempt_id=candidate["author_attempt_id"],
                reviewer_execution_ref={
                    "kind": "HOST_SUBAGENT_ATTEMPT",
                    "id": candidate["author_attempt_id"],
                },
                verdict="PASS",
                findings=[],
            )

        candidate_path.chmod(0o600)
        candidate_path.write_text(candidate_path.read_text(encoding="utf-8") + "\n静默修改\n", encoding="utf-8")
        with self.assertRaisesRegex(AlphaContractError, "Candidate.*changed"):
            self.pass_review(state, candidate, suffix="tampered")

    def test_rereview_work_order_build_rejects_missing_or_changed_exact_basis_without_writes(
        self,
    ) -> None:
        cases = (
            ("candidate", "missing"),
            ("candidate", "changed"),
            ("review", "missing"),
            ("review", "changed"),
            ("planning", "missing"),
            ("planning", "changed"),
        )
        for target_name, damage in cases:
            suffix = f"build-{target_name}-{damage}"
            with self.subTest(target=target_name, damage=damage):
                state, candidate, review = self.reach_problem_rereview_authoring(
                    suffix=suffix
                )
                target_ref = {
                    "candidate": candidate,
                    "review": review["review_ref"],
                    "planning": state["planning_record_ref"],
                }[target_name]
                target = self.project / target_ref["path"]
                original = target.read_bytes()
                original_mode = target.stat().st_mode & 0o777
                if damage == "missing":
                    target.unlink()
                else:
                    target.chmod(0o600)
                    target.write_bytes(original + b"\ntampered\n")

                run_path = self.controller.run_path(state["run_id"])
                state_path = run_path / "run.json"
                state_before = state_path.read_bytes()
                objects_before = sorted(
                    path.relative_to(run_path).as_posix()
                    for path in (run_path / "objects").rglob("*")
                    if path.is_file()
                )
                operation_id = f"freeze-revision-{suffix}"
                with self.assertRaisesRegex(
                    AlphaContractError, "re-review.*missing or changed"
                ):
                    self.controller.freeze_candidate(
                        state["run_id"],
                        expected_state_version=state["state_version"],
                        operation_id=operation_id,
                        kind="PROBLEM",
                        author_attempt_id=f"problem-author-revision-{suffix}",
                    )

                self.assertEqual(state_path.read_bytes(), state_before)
                self.assertEqual(
                    sorted(
                        path.relative_to(run_path).as_posix()
                        for path in (run_path / "objects").rglob("*")
                        if path.is_file()
                    ),
                    objects_before,
                )
                self.assertNotIn(
                    "current_rereview_work_order",
                    self.controller.load_run(state["run_id"]),
                )

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original)
                target.chmod(original_mode)
                retried = self.controller.freeze_candidate(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id=operation_id,
                    kind="PROBLEM",
                    author_attempt_id=f"problem-author-revision-{suffix}",
                )
                self.assertIn("current_rereview_work_order", retried)

    def test_rereview_submission_revalidates_exact_basis_without_partial_review(
        self,
    ) -> None:
        cases = (
            ("candidate", "missing"),
            ("candidate", "changed"),
            ("review", "missing"),
            ("review", "changed"),
            ("planning", "missing"),
            ("planning", "changed"),
        )
        for target_name, damage in cases:
            suffix = f"submit-{target_name}-{damage}"
            with self.subTest(target=target_name, damage=damage):
                state, candidate, review = self.reach_problem_rereview_authoring(
                    suffix=suffix
                )
                state = self.controller.freeze_candidate(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id=f"freeze-revision-{suffix}",
                    kind="PROBLEM",
                    author_attempt_id=f"problem-author-revision-{suffix}",
                )
                revised = deepcopy(state["current_candidate"])
                target_ref = {
                    "candidate": candidate,
                    "review": review["review_ref"],
                    "planning": state["planning_record_ref"],
                }[target_name]
                target = self.project / target_ref["path"]
                original = target.read_bytes()
                original_mode = target.stat().st_mode & 0o777
                if damage == "missing":
                    target.unlink()
                else:
                    target.chmod(0o600)
                    target.write_bytes(original + b"\ntampered\n")

                run_path = self.controller.run_path(state["run_id"])
                state_path = run_path / "run.json"
                state_before = state_path.read_bytes()
                reviews_before = sorted(
                    path.relative_to(run_path).as_posix()
                    for path in (run_path / "reviews").rglob("*")
                    if path.is_file()
                )
                operation_id = f"review-revision-{suffix}"
                review_args = {
                    "candidate_ref": revised,
                    "reviewer_attempt_id": f"reviewer-revision-{suffix}",
                    "reviewer_execution_ref": {
                        "kind": "HOST_SUBAGENT_ATTEMPT",
                        "id": f"reviewer-revision-{suffix}",
                    },
                    "verdict": "PASS",
                    "findings": [],
                    "review_mode": "DIFF_AND_REGRESSION",
                    "diff_base_candidate_ref": candidate,
                    "global_regression": "PASS",
                }
                with self.assertRaisesRegex(
                    AlphaContractError, "re-review.*missing or changed"
                ):
                    self.controller.submit_review(
                        state["run_id"],
                        expected_state_version=state["state_version"],
                        operation_id=operation_id,
                        **review_args,
                    )

                self.assertEqual(state_path.read_bytes(), state_before)
                self.assertEqual(
                    sorted(
                        path.relative_to(run_path).as_posix()
                        for path in (run_path / "reviews").rglob("*")
                        if path.is_file()
                    ),
                    reviews_before,
                )

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original)
                target.chmod(original_mode)
                retried = self.controller.submit_review(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id=operation_id,
                    **review_args,
                )
                self.assertEqual(retried["current_review"]["verdict"], "PASS")

    def test_revision_requires_diff_review_and_stops_after_two_rounds_by_reason(self) -> None:
        state, candidate = self.reach_problem_review()
        self.assertNotIn("current_rereview_work_order", state)
        state = self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="problem-revise-0",
            candidate_ref=candidate,
            reviewer_attempt_id="reviewer-r0",
            reviewer_execution_ref={
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": "reviewer-r0",
            },
            verdict="REVISE",
            findings=[
                {
                    "finding_id": "F-1",
                    "claim": "问题与目标链未闭合。",
                    "evidence_refs": [candidate],
                    "severity": "MAJOR",
                    "affected_scope": ["问题定义", "成功标准"],
                    "invalidated_assumptions_or_artifacts": ["Problem Candidate"],
                    "local_revision_sufficiency": "SUFFICIENT",
                    "status": "OPEN",
                }
            ],
        )
        state = self.controller.submit_review_route(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="problem-route-0",
            review_ref=state["current_review"]["review_ref"],
            lead_agent_attempt_id="lead-r0",
            finding_refs=["F-1"],
            return_target="DIAGNOSE_VALUE",
            return_reason="问题诊断需要修正",
            affected_scope=["问题定义", "成功标准"],
        )
        original = (self.project / candidate["path"]).read_bytes()
        state = self.update_record(state, position="DIAGNOSE_VALUE", suffix="revision-1")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-problem-r1",
            kind="PROBLEM",
            author_attempt_id="problem-author-r1",
        )
        revised = state["current_candidate"]
        self.assertEqual(revised["revision_round"], 1)
        self.assertEqual((self.project / candidate["path"]).read_bytes(), original)
        work_order = state["current_rereview_work_order"]
        self.assertEqual(work_order["source_candidate_ref"], revised["supersedes"])
        self.assertEqual(
            work_order["current_candidate_ref"],
            {
                key: revised[key]
                for key in ("candidate_id", "kind", "path", "hash", "version")
            },
        )
        self.assertEqual(work_order["review_ref"], state["review_routes"][-1]["review_ref"])
        self.assertEqual(work_order["finding_refs"], ["F-1"])
        self.assertEqual(work_order["lead_agent_attempt_id"], "lead-r0")
        self.assertEqual(work_order["return_reason"], "问题诊断需要修正")
        self.assertEqual(work_order["planning_record_ref"], state["planning_record_ref"])
        self.assertEqual(work_order["rereview_scope"], ["问题定义", "成功标准"])
        self.assertEqual(work_order["scope_basis"], "REVIEW_ROUTE")
        self.assertEqual(
            work_order["global_regression_checklist"],
            [
                "SCOPE",
                "AUTHORITY",
                "ACCEPTANCE",
                "STATUS_DRIFT",
                "CROSS_SECTION_CONTRADICTION",
                "DOCUMENT_NAVIGATION",
            ],
        )
        self.assertNotIn("diff_ref", work_order)
        self.assertEqual(
            self.controller.load_run(state["run_id"])["current_rereview_work_order"],
            work_order,
        )

        with self.assertRaisesRegex(AlphaContractError, "difference.*regression"):
            self.pass_review(state, revised, suffix="missing-diff")

        state = self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="problem-revise-1",
            candidate_ref=revised,
            reviewer_attempt_id="reviewer-r1",
            reviewer_execution_ref={
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": "reviewer-r1",
            },
            verdict="REVISE",
            findings=[
                {
                    "finding_id": "F-2",
                    "claim": "价值因果仍未闭合。",
                    "evidence_refs": [revised],
                    "severity": "MAJOR",
                    "affected_scope": ["价值因果"],
                    "invalidated_assumptions_or_artifacts": ["Problem Candidate"],
                    "local_revision_sufficiency": "SUFFICIENT",
                    "status": "OPEN",
                }
            ],
            review_mode="DIFF_AND_REGRESSION",
            diff_base_candidate_ref=candidate,
            global_regression="PASS",
        )
        state = self.controller.submit_review_route(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="problem-route-1",
            review_ref=state["current_review"]["review_ref"],
            lead_agent_attempt_id="lead-r1",
            finding_refs=["F-2"],
            return_target="DIAGNOSE_VALUE",
            return_reason="仍需修复价值因果",
            affected_scope=["价值因果"],
        )
        state = self.update_record(state, position="DIAGNOSE_VALUE", suffix="revision-2")
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-problem-r2",
            kind="PROBLEM",
            author_attempt_id="problem-author-r2",
        )
        revised_twice = state["current_candidate"]
        self.assertEqual(revised_twice["revision_round"], 2)

        state = self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="problem-exhausted-research",
            candidate_ref=revised_twice,
            reviewer_attempt_id="reviewer-r2",
            reviewer_execution_ref={
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": "reviewer-r2",
            },
            verdict="REVISE",
            findings=[
                {
                    "finding_id": "F-3",
                    "claim": "现有证据不足以继续本地修订。",
                    "evidence_refs": [revised_twice],
                    "severity": "MAJOR",
                    "affected_scope": ["H1", "H2"],
                    "invalidated_assumptions_or_artifacts": ["价值证据"],
                    "local_revision_sufficiency": "INSUFFICIENT",
                    "status": "OPEN",
                }
            ],
            review_mode="DIFF_AND_REGRESSION",
            diff_base_candidate_ref=revised,
            global_regression="PASS",
        )
        state = self.controller.submit_review_route(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="problem-route-2",
            review_ref=state["current_review"]["review_ref"],
            lead_agent_attempt_id="lead-r2",
            finding_refs=["F-3"],
            return_target="RESEARCH",
            return_reason="证据不足，不能继续自动修订",
            affected_scope=["H1", "H2"],
        )
        self.assertEqual(state["position"], "RESEARCH")
        self.assertTrue(state["automatic_revision_exhausted"])
        with self.assertRaisesRegex(AlphaContractError, "two automatic revision"):
            self.controller.freeze_candidate(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="forbidden-third-revision",
                kind="PROBLEM",
                author_attempt_id="problem-author-r3",
            )

    def test_decision_revision_exposes_route_based_rereview_work_order(self) -> None:
        state, candidate = self.reach_problem_review(suffix="decision-rereview")
        state = self.pass_review(
            state, candidate, suffix="decision-rereview-problem"
        )
        state = self.update_record(
            state,
            position="DISCOVER_SOLUTIONS_DECIDE",
            suffix="decision-rereview-initial",
        )
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-decision-rereview-initial",
            kind="DECISION",
            author_attempt_id="decision-author-rereview-initial",
        )
        initial = deepcopy(state["current_candidate"])
        self.assertNotIn("current_rereview_work_order", state)
        state = self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="review-decision-rereview-initial",
            candidate_ref=initial,
            reviewer_attempt_id="decision-reviewer-rereview-initial",
            reviewer_execution_ref={
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": "decision-reviewer-rereview-initial",
            },
            verdict="REVISE",
            findings=[
                {
                    "finding_id": "F-DECISION-REREVIEW",
                    "claim": "方案边界与验收关系需要修正。",
                    "evidence_refs": [initial],
                    "severity": "MAJOR",
                    "affected_scope": ["方案边界", "验收关系"],
                    "invalidated_assumptions_or_artifacts": ["Decision Candidate"],
                    "local_revision_sufficiency": "SUFFICIENT",
                    "status": "OPEN",
                }
            ],
        )
        state = self.controller.submit_review_route(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="route-decision-rereview-initial",
            review_ref=state["current_review"]["review_ref"],
            lead_agent_attempt_id="decision-lead-rereview",
            finding_refs=["F-DECISION-REREVIEW"],
            return_target="DISCOVER_SOLUTIONS_DECIDE",
            return_reason="修正方案边界与验收关系。",
            affected_scope=["方案边界", "验收关系"],
        )
        state = self.update_record(
            state,
            position="DISCOVER_SOLUTIONS_DECIDE",
            suffix="decision-rereview-revision",
        )
        state = self.controller.freeze_candidate(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="freeze-decision-rereview-revision",
            kind="DECISION",
            author_attempt_id="decision-author-rereview-revision",
        )

        work_order = state["current_rereview_work_order"]
        self.assertEqual(work_order["source_candidate_ref"], state["current_candidate"]["supersedes"])
        self.assertEqual(work_order["review_ref"], state["review_routes"][-1]["review_ref"])
        self.assertEqual(work_order["finding_refs"], ["F-DECISION-REREVIEW"])
        self.assertEqual(work_order["rereview_scope"], ["方案边界", "验收关系"])
        self.assertEqual(work_order["planning_record_ref"], state["planning_record_ref"])

    def test_six_decision_outcomes_form_distinct_states(self) -> None:
        cases = {
            "STOP": ("COMPLETED_STOP", "DECISION_ROUTE"),
            "WAIT": ("WAITING_TRIGGER", "DECISION_ROUTE"),
            "RESEARCH": ("ACTIVE", "UNDERSTAND"),
            "EXPERIMENT": ("ACTIVE", "PRD_AUTHORING"),
            "COMMIT_NOW": ("ACTIVE", "PLAN_PRODUCT_SYSTEM"),
            "FUTURE_ROADMAP": ("COMPLETED_FUTURE_ROADMAP", "DECISION_ROUTE"),
        }
        observed = set()
        for index, (outcome, expected) in enumerate(cases.items(), start=1):
            with self.subTest(outcome=outcome):
                state, candidate = self.reach_decision_route(suffix=str(index))
                kwargs = {}
                if outcome == "WAIT":
                    kwargs["wait_condition"] = {
                        "condition_id": "wait-for-evidence",
                        "description": "等待新的用户证据",
                        "return_target": "DIAGNOSE_VALUE",
                    }
                if outcome == "RESEARCH":
                    kwargs["return_target"] = "UNDERSTAND"
                state = self.choose(
                    state, candidate, outcome=outcome, suffix=str(index), **kwargs
                )
                self.assertEqual((state["status"], state["position"]), expected)
                self.assertEqual(state["decision"]["outcome"], outcome)
                observed.add((state["status"], state["position"], outcome))
        self.assertEqual(len(observed), 6)

    def test_agent_commit_uses_exact_bindings_and_assessment_not_message_trace(self) -> None:
        state, candidate = self.reach_decision_route(suffix="no-message-ref")
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            actor_kind="AGENT",
            agent_assessment=self.agent_assessment(state),
            suffix="no-message-ref",
            include_source_message_ref=False,
        )
        self.assertEqual(state["position"], "PLAN_PRODUCT_SYSTEM")
        self.assertNotIn("source_message_ref", state["decision"]["authorization"])

        state, candidate = self.reach_decision_route(suffix="opaque-message-ref")
        opaque_trace = ["host-owned", {"unverified": True}]
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            actor_kind="AGENT",
            agent_assessment=self.agent_assessment(state),
            suffix="opaque-message-ref",
            source_message_ref=opaque_trace,
        )
        self.assertEqual(state["position"], "PLAN_PRODUCT_SYSTEM")
        self.assertEqual(
            state["decision"]["authorization"]["source_message_ref"], opaque_trace
        )

        state, candidate = self.reach_decision_route(suffix="missing-assessment")
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            actor_kind="AGENT",
            suffix="missing-assessment",
        )
        self.assertEqual(state["status"], "OWNER_CHOICE_REQUIRED")
        self.assertIsNone(state.get("decision"))

        state, candidate = self.reach_decision_route(suffix="auth")
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            actor_kind="AGENT",
            agent_assessment=self.agent_assessment(state),
            suffix="auth",
        )
        self.assertEqual(state["position"], "PLAN_PRODUCT_SYSTEM")
        self.assertEqual(state["decision"]["source"], "AGENT_PREAUTHORIZED")
        self.assertTrue(state["decision"]["agent_assessment"]["reversible"])

        state, candidate = self.reach_decision_route(suffix="agent-wait")
        with self.assertRaisesRegex(AlphaContractError, "Owner"):
            self.choose(
                state,
                candidate,
                outcome="WAIT",
                actor_kind="AGENT",
                suffix="agent-wait",
                wait_condition={
                    "condition_id": "x",
                    "description": "x",
                    "return_target": "UNDERSTAND",
                },
            )

    def test_owner_choice_does_not_require_or_validate_message_trace(self) -> None:
        state, candidate = self.reach_decision_route(suffix="owner-no-message-ref")
        state = self.choose(
            state,
            candidate,
            outcome="STOP",
            suffix="owner-no-message-ref",
            include_source_message_ref=False,
        )
        self.assertEqual(state["status"], "COMPLETED_STOP")
        self.assertNotIn("source_message_ref", state["decision"]["authorization"])

        state, candidate = self.reach_decision_route(suffix="owner-opaque-message-ref")
        opaque_trace = {"host_metadata": ["not", "controller", "validated"]}
        state = self.choose(
            state,
            candidate,
            outcome="FUTURE_ROADMAP",
            suffix="owner-opaque-message-ref",
            source_message_ref=opaque_trace,
        )
        self.assertEqual(state["status"], "COMPLETED_FUTURE_ROADMAP")
        self.assertEqual(
            state["decision"]["authorization"]["source_message_ref"], opaque_trace
        )

    def test_wait_requires_matching_trigger_while_pause_resumes_from_safe_point(self) -> None:
        state, candidate = self.reach_decision_route(suffix="wait")
        state = self.choose(
            state,
            candidate,
            outcome="WAIT",
            suffix="wait",
            wait_condition={
                "condition_id": "evidence-arrives",
                "description": "等待一份新的用户证据",
                "return_target": "DIAGNOSE_VALUE",
            },
        )
        with self.assertRaisesRegex(AlphaContractError, "WAIT.*Trigger"):
            self.controller.resume_run(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="plain-wait-resume",
            )

        evidence = self.project / "evidence.md"
        evidence.write_text("新的用户证据", encoding="utf-8")
        state = self.controller.resume_run(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="triggered-resume",
            trigger={
                "trigger_id": "trigger-1",
                "condition_id": "evidence-arrives",
                "evidence_ref": self.controller.file_ref(evidence),
            },
        )
        self.assertEqual((state["status"], state["position"]), ("ACTIVE", "DIAGNOSE_VALUE"))

        paused = self.controller.pause_run(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="pause-1",
        )
        resumed = self.controller.resume_run(
            paused["run_id"],
            expected_state_version=paused["state_version"],
            operation_id="resume-1",
        )
        self.assertEqual((resumed["status"], resumed["position"]), ("ACTIVE", "DIAGNOSE_VALUE"))

    def test_owner_cognition_change_returns_upstream_and_requires_new_candidate(self) -> None:
        state, candidate = self.reach_decision_route(suffix="change")
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            suffix="change",
            cognition_change={
                "kind": "GOAL",
                "return_target": "UNDERSTAND",
                "reason": "Owner 改变了目标和价值权重",
            },
        )
        self.assertEqual(state["position"], "UNDERSTAND")
        self.assertTrue(state["candidate_required"])
        self.assertEqual(state["current_candidate"]["status"], "STALE")

    def test_research_uses_agent_supplied_earliest_affected_stage(self) -> None:
        state, candidate = self.reach_decision_route(suffix="research")
        state = self.choose(
            state,
            candidate,
            outcome="RESEARCH",
            suffix="research",
            return_target="DIAGNOSE_VALUE",
        )
        self.assertEqual(state["position"], "DIAGNOSE_VALUE")

    def test_commit_and_experiment_deliver_distinct_prd_types(self) -> None:
        for index, outcome in enumerate(("COMMIT_NOW", "EXPERIMENT"), start=1):
            with self.subTest(outcome=outcome):
                state = self.reach_prd_authoring(intent=outcome, suffix=f"prd-{index}")
                state = self.freeze_prd(state, suffix=f"prd-{index}")
                state = self.pass_review(
                    state, state["current_candidate"], suffix=f"prd-final-{index}"
                )
                self.assertEqual(state["status"], "READY")
                state = self.controller.prepare_local_handoff(
                    state["run_id"],
                    expected_state_version=state["state_version"],
                    operation_id=f"handoff-{index}",
                )
                manifest = json.loads(
                    (self.project / state["handoff"]["manifest_ref"]["path"]).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(
                    manifest["prd_type"],
                    "FORMAL_PRD" if outcome == "COMMIT_NOW" else "EXPERIMENT_PRD",
                )
                self.assertEqual(state["status"], "LOCAL_HANDOFF_COMPLETE")
                self.assertEqual(state["external_delivery"], "NOT_RUN")
                self.assertNotIn("RELEASED", json.dumps(state))

    def test_2_0_skips_future_product_evals_gate_but_preserves_not_run_truth(self) -> None:
        no_assessment = self.reach_prd_authoring(
            intent="EXPERIMENT", suffix="no-evals-assessment"
        )
        draft = self.write_prd_draft(no_assessment["run_id"])
        no_assessment = self.controller.freeze_candidate(
            no_assessment["run_id"],
            expected_state_version=no_assessment["state_version"],
            operation_id="freeze-prd-no-evals-assessment",
            kind="PRD",
            author_attempt_id="prd-author-no-evals-assessment",
            source_dir=draft,
            document_experience=self.document_experience(
                no_assessment, draft, suffix="no-evals-assessment"
            ),
        )
        self.assertNotIn(
            "product_eval_attachments",
            no_assessment["current_review_requirements"]["review_basis_refs"],
        )
        no_assessment = self.pass_review(
            no_assessment,
            no_assessment["current_candidate"],
            suffix="no-evals-assessment-prd",
        )
        self.assertEqual(no_assessment["status"], "READY")
        self.assertEqual(
            no_assessment["ready"]["evidence_summary"]["product_eval_execution"],
            "NOT_RUN",
        )
        self.assertEqual(
            no_assessment["ready"]["evidence_summary"]["product_effect_validation"],
            "NOT_RUN",
        )
        no_assessment = self.controller.prepare_local_handoff(
            no_assessment["run_id"],
            expected_state_version=no_assessment["state_version"],
            operation_id="handoff-no-evals-assessment",
            delivery_options={"LOCAL_HTML": False},
        )
        self.assertEqual(no_assessment["status"], "LOCAL_HANDOFF_COMPLETE")
        handoff_note = (
            self.project / no_assessment["handoff"]["path"] / "HANDOFF.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Product Eval Execution：NOT_RUN", handoff_note)
        self.assertIn("产品效果验证：NOT_RUN", handoff_note)

        legacy_required = self.reach_prd_authoring(
            intent="EXPERIMENT", suffix="legacy-required"
        )
        legacy_required = self.freeze_prd(
            legacy_required,
            applicability="REQUIRED",
            suffix="legacy-required",
        )
        legacy_required = self.pass_review(
            legacy_required,
            legacy_required["current_candidate"],
            suffix="legacy-required-prd",
        )
        self.assertEqual(legacy_required["ready"]["status"], "READY")
        self.assertNotIn("REQUIRED_PRODUCT_EVALS", legacy_required["ready"]["unmet"])
        self.assertNotIn("applicability", legacy_required["product_evals"])

        fulfilled = self.reach_prd_authoring(intent="EXPERIMENT", suffix="fulfilled")
        with self.assertRaisesRegex(AlphaContractError, "NOT_IMPLEMENTED|cannot generate"):
            self.freeze_prd(
                fulfilled,
                applicability="REQUIRED",
                generated=True,
                suffix="fulfilled",
            )

        recommended = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="recommended")
        recommended = self.freeze_prd(
            recommended, applicability="RECOMMENDED", suffix="recommended"
        )
        recommended = self.pass_review(
            recommended, recommended["current_candidate"], suffix="recommended-prd"
        )
        self.assertEqual(recommended["status"], "READY")
        self.assertEqual(
            recommended["product_evals"]["generator_capability"],
            "NOT_IMPLEMENTED",
        )
        self.assertEqual(
            recommended["product_evals"]["generator_invocation_status"],
            "NOT_RUN",
        )
        self.assertEqual(recommended["product_evals"]["execution_status"], "NOT_RUN")

    def test_new_general_template_is_single_prd_and_bound_to_candidate(self) -> None:
        template = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "core"
            / "templates"
            / "general"
            / "PRD_TEMPLATE_v2.0-alpha.3.md"
        )
        content = template.read_text(encoding="utf-8")
        for heading in (
            "## 产品背景、目标与问题定义",
            "## 方案概述与需求范围",
            "## 核心体验与产品逻辑",
            "## 产品需求与业务规则",
            "## 验收标准与效果衡量",
            "## 风险、依赖与未决事项",
        ):
            self.assertIn(heading, content)
        self.assertNotIn("Engineering SPEC", content)
        self.assertNotIn("子 PRD", content)

        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="template")
        state = self.freeze_prd(state, suffix="template")
        manifest = json.loads(
            (self.project / state["current_candidate"]["path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["template_ref"]["version"], "2.0-alpha.1")
        self.assertTrue(manifest["template_ref"]["hash"].startswith("sha256:"))
        self.assertTrue((self.project / manifest["template_ref"]["path"]).is_file())
        self.assertTrue(
            (self.project / manifest["planning_record_snapshot_ref"]["path"]).is_file()
        )
        self.assertTrue(
            all("/objects/sha256/" in item["object_ref"]["path"] for item in manifest["files"])
        )
        self.assertEqual(manifest["accepted_decision"]["outcome"], "COMMIT_NOW")
        self.assertEqual(manifest["accepted_decision"]["source"], "OWNER_CHOICE")
        self.assertEqual(
            manifest["accepted_decision"]["candidate_ref"]["candidate_id"],
            "decision-candidate-v1",
        )
        self.assertEqual(manifest["decision_review_ref"]["verdict"], "PASS")
        self.assertNotIn(
            "planning_record_ref",
            manifest["accepted_decision"]["candidate_ref"],
        )

    def test_ready_requires_exact_release_set_and_only_handoff_can_follow(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="ready")
        state = self.freeze_prd(state, suffix="ready")
        candidate = state["current_candidate"]
        planning_record = self.controller.run_path(state["run_id"]) / "planning-record.md"
        planning_record.write_text(
            planning_record.read_text(encoding="utf-8") + "\n未冻结的新变化\n",
            encoding="utf-8",
        )
        state = self.pass_review(state, candidate, suffix="stale-planning")
        self.assertEqual(state["ready"]["status"], "NOT_READY")
        self.assertIn("PLANNING_RECORD_STALE", state["ready"]["unmet"])
        with self.assertRaisesRegex(AlphaContractError, "Ready"):
            self.controller.prepare_local_handoff(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="handoff-too-early",
            )

    def test_retrospective_is_after_and_does_not_block_local_handoff(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="retro")
        state = self.freeze_prd(state, suffix="retro")
        state = self.pass_review(state, state["current_candidate"], suffix="retro-prd")
        state = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-retro",
        )
        self.assertEqual(state["retrospective_status"], "NOT_RUN")
        state = self.controller.record_retrospective(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="retro-1",
            author_attempt_id="retro-author",
            markdown="# 规划复盘\n\n有效方法、返工原因与方法增量。\n",
            method_conformance=self.complete_retrospective_conformance(),
        )
        self.assertEqual(state["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertEqual(state["retrospective_status"], "COMPLETED")
        self.assertEqual(
            set(state["retrospective_requirements"]), {"check_ids", "statuses"}
        )

    def test_retrospective_requires_method_conformance_and_preserves_findings_without_rewriting_handoff(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="retro-conformance")
        state = self.freeze_prd(state, suffix="retro-conformance")
        state = self.pass_review(
            state, state["current_candidate"], suffix="retro-conformance"
        )
        state = self.controller.prepare_local_handoff(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="handoff-retro-conformance",
        )
        ready_before = deepcopy(state["ready"])
        handoff_before = deepcopy(state["handoff"])

        with self.assertRaisesRegex(AlphaContractError, "method conformance"):
            self.controller.record_retrospective(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="retro-conformance-missing",
                author_attempt_id="retro-conformance-author",
                markdown="# 规划复盘\n\n缺少方法履行核对。\n",
                method_conformance=[],
            )

        conformance = self.complete_retrospective_conformance()
        conformance[-1] = {
            "check_id": "NOT_RUN_BOUNDARIES",
            "status": "FINDING",
            "rationale": "交接说明需要继续强调 Human Reader Study 尚未执行。",
        }
        completed = self.controller.record_retrospective(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="retro-conformance-finding",
            author_attempt_id="retro-conformance-author",
            markdown="# 规划复盘\n\n发现一项方法表达缺口，但不改写历史。\n",
            method_conformance=conformance,
        )
        self.assertEqual(completed["retrospective_status"], "COMPLETED_WITH_FINDINGS")
        self.assertEqual(completed["method_conformance_status"], "FAIL")
        self.assertEqual(completed["ready"], ready_before)
        self.assertEqual(completed["handoff"], handoff_before)

    def test_run_binds_runtime_fingerprint_and_minimal_operation_facts(self) -> None:
        state = self.start(suffix="repair-identity")

        self.assertTrue(state["runtime_fingerprint"].startswith("sha256:"))
        self.assertEqual(state["capabilities"]["evals_generator"], "NOT_IMPLEMENTED")

        operation = state["operations"]["start-repair-identity"]
        self.assertEqual(operation["action"], "start_run")
        self.assertEqual(operation["outcome"], "SUCCESS")
        self.assertEqual(operation["state_version_before"], 0)
        self.assertEqual(operation["state_version_after"], 1)
        self.assertTrue(operation["started_at"])
        self.assertTrue(operation["completed_at"])
        self.assertIsNone(operation["error_code_or_return_reason"])
        self.assertFalse((self.controller.run_path(state["run_id"]) / "operations").exists())

        state_path = self.controller.run_path(state["run_id"]) / "run.json"
        persisted = json.loads(state_path.read_text(encoding="utf-8"))
        persisted["runtime_fingerprint"] = "sha256:different-runtime"
        state_path.write_text(json.dumps(persisted), encoding="utf-8")
        with self.assertRaisesRegex(AlphaContractError, "recovery is stopped"):
            self.controller.load_run(state["run_id"])

    def test_candidate_freeze_uses_run_object_store_without_candidate_copy(self) -> None:
        state, candidate = self.reach_problem_review(suffix="repair-object-store")

        self.assertIn("/objects/sha256/", candidate["path"])
        self.assertFalse((self.controller.run_path(state["run_id"]) / "candidates").exists())
        self.assertEqual(
            (self.project / candidate["path"]).read_bytes(),
            (self.controller.run_path(state["run_id"]) / "planning-record.md").read_bytes(),
        )

    def test_prd_candidate_rejects_any_extra_asset_before_candidate_write(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="repair-png")
        draft = self.write_prd_draft(state["run_id"])
        assets = draft / "assets"
        assets.mkdir()
        (assets / "main-flow@2x.png").write_bytes(b"not-a-candidate-format")
        history_before = deepcopy(state["candidate_history"])
        current_before = deepcopy(state["current_candidate"])
        object_root = self.controller.run_path(state["run_id"]) / "objects" / "sha256"
        objects_before = {path.name for path in object_root.iterdir()}

        with self.assertRaisesRegex(AlphaContractError, "exactly PRD.md"):
            self.controller.freeze_candidate(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="freeze-prd-repair-png",
                kind="PRD",
                author_attempt_id="prd-author-repair-png",
                source_dir=draft,
                evals=self.evals("NOT_NEEDED"),
                document_experience=self.document_experience(
                    state, draft, suffix="repair-png"
                ),
            )

        unchanged = self.controller.load_run(state["run_id"])
        self.assertEqual(unchanged["state_version"], state["state_version"])
        self.assertEqual(unchanged["candidate_history"], history_before)
        self.assertEqual(unchanged["current_candidate"], current_before)
        self.assertEqual({path.name for path in object_root.iterdir()}, objects_before)

    def test_decision_authorization_rejects_wrong_run_binding(self) -> None:
        state, candidate = self.reach_decision_route(suffix="repair-auth")
        exact_candidate = self.controller._candidate_ref(candidate)
        with self.assertRaisesRegex(AlphaContractError, "exact scope"):
            self.controller.submit_decision_route(
                state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="decision-route-repair-auth",
                candidate_ref=candidate,
                actor={"kind": "OWNER", "id": "eli"},
                outcome="COMMIT_NOW",
                decision_authorization={
                    "source_message_ref": {
                        "kind": "HOST_MESSAGE",
                        "id": "owner-message-repair-auth",
                    },
                    "run_id": "bpg2-run-another",
                    "candidate_ref": exact_candidate,
                    "allowed_outcome": "COMMIT_NOW",
                    "permission_scope": "RUN_DECISION_ONLY",
                    "issued_at": "2026-08-31T00:00:00+00:00",
                },
            )

    def test_unimplemented_evals_generator_cannot_be_simulated_by_attachments(self) -> None:
        state = self.reach_prd_authoring(intent="EXPERIMENT", suffix="repair-evals")

        with self.assertRaisesRegex(AlphaContractError, "NOT_IMPLEMENTED|cannot generate"):
            self.freeze_prd(
                state,
                applicability="REQUIRED",
                generated=True,
                suffix="repair-evals",
            )

    def test_non_pass_reviewer_reports_findings_then_lead_agent_routes(self) -> None:
        state, candidate = self.reach_problem_review(suffix="repair-route")
        state = self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="review-findings-repair-route",
            candidate_ref=candidate,
            reviewer_attempt_id="reviewer-repair-route",
            reviewer_execution_ref={
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": "reviewer-repair-route",
            },
            verdict="REVISE",
            findings=[
                {
                    "finding_id": "F-REPAIR-ROUTE",
                    "claim": "问题定义与成功标准之间缺少可验证关系。",
                    "evidence_refs": [candidate],
                    "severity": "MAJOR",
                    "affected_scope": ["问题定义", "成功标准"],
                    "invalidated_assumptions_or_artifacts": ["Problem Candidate"],
                    "local_revision_sufficiency": "SUFFICIENT",
                    "status": "OPEN",
                }
            ],
        )
        self.assertEqual(state["status"], "REVIEW_ROUTE_REQUIRED")
        self.assertNotIn("return_target", state["current_review"])

        state = self.controller.submit_review_route(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id="lead-route-repair-route",
            review_ref=state["current_review"]["review_ref"],
            lead_agent_attempt_id="lead-repair-route",
            finding_refs=["F-REPAIR-ROUTE"],
            return_target="DIAGNOSE_VALUE",
            return_reason="Finding 使问题诊断层失效。",
            affected_scope=["问题定义", "成功标准"],
        )
        self.assertEqual((state["status"], state["position"]), ("ACTIVE", "DIAGNOSE_VALUE"))
        self.assertEqual(state["review_routes"][-1]["decided_by"], "LEAD_AGENT")

    def test_review_result_binds_minimal_host_execution_facts(self) -> None:
        state, candidate = self.reach_problem_review(suffix="repair-review-binding")
        state = self.pass_review(
            state, candidate, suffix="repair-review-binding"
        )

        binding = state["current_review"]["execution_binding"]
        self.assertEqual(
            binding["host_attempt_ref"],
            {
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": "reviewer-repair-review-binding",
            },
        )
        self.assertEqual(binding["candidate_hash"], candidate["hash"])
        self.assertTrue(binding["review_result_hash"].startswith("sha256:"))
        self.assertEqual(binding["completion_status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
