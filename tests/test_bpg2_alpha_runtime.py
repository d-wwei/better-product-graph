from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.bpg.alpha_runtime import AlphaContractError, BPG2AlphaController


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
    "ACCEPTANCE_AND_PRODUCT_EVALS",
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

    def pass_review(
        self,
        state: dict,
        candidate: dict,
        *,
        suffix: str,
        review_overrides: dict | None = None,
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
            values.update(self.prd_review_evidence(state, suffix=suffix))
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
        authorize: bool = True,
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
        decision_authorization = (
            {
                "source_message_ref": {
                    "kind": "HOST_MESSAGE",
                    "id": f"decision-message-{suffix}",
                },
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
            if authorize
            else None
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

    def write_writing_review(self, state: dict, *, suffix: str) -> tuple[dict, str]:
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
        review_dir = self.controller.run_path(state["run_id"]) / "work" / "review"
        review_dir.mkdir(parents=True, exist_ok=True)
        path = review_dir / f"writing-review-{suffix}.json"
        path.write_text(json.dumps(review, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return {**self.controller.file_ref(path), "version": 1}, writer_id

    def prd_review_evidence(self, state: dict, *, suffix: str) -> dict:
        requirements = state["current_review_requirements"]
        writing_ref, writer_id = self.write_writing_review(state, suffix=suffix)
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
        self.assertEqual(profile["review_contract_id"], review_contract["resource_id"])
        self.assertEqual(
            requirements["writing_review_context"]["review_contract_ref"],
            requirements["review_basis_refs"]["writing_review_contract"],
        )
        self.assertEqual(
            requirements["review_basis_refs"]["writing_review_contract"]["version"],
            "v3.1",
        )
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

    def test_prd_review_v3_ready_summary_separates_review_and_handoff_rendering(self) -> None:
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
        self.assertEqual(manifest["evidence_summary"]["handoff_rendering"], "GENERATED")
        self.assertEqual(manifest["delivery"]["selected_modes"], ["LOCAL_HTML"])
        self.assertEqual(
            manifest["delivery"]["outputs"]["LOCAL_HTML"]["status"], "GENERATED"
        )
        self.assertEqual(manifest["delivery_options"]["LOCAL_HTML"], True)
        self.assertEqual(
            manifest["delivery_capabilities"]["not_implemented"],
            ["LOCAL_DOCUMENT", "FEISHU_DOCUMENT", "PROJECT_MANAGEMENT_MCP"],
        )
        self.assertTrue(
            (self.project / handoff["handoff"]["path"] / "PRD.html").is_file()
        )
        note = (self.project / handoff["handoff"]["path"] / "HANDOFF.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Writing Review：PASS", note)
        self.assertIn("Handoff Rendering：GENERATED", note)
        self.assertIn("Human Reader Validation：NOT_RUN", note)
        self.assertIn("Product Eval Execution：NOT_RUN", note)
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
        self.assertEqual(output_contract_ref["version"], "2.0-alpha.2")
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
            manifest["delivery"]["outputs"]["LOCAL_HTML"]["status"],
            "SKIPPED_BY_USER",
        )
        self.assertEqual(
            manifest["delivery"]["primary_reading_ref"]["path"],
            (handoff_dir / "PRD.md").relative_to(self.project).as_posix(),
        )
        self.assertEqual(
            manifest["evidence_summary"]["handoff_rendering"],
            "SKIPPED_BY_USER",
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
            ({"LOCAL_HTML": "false"}, {"UNKNOWN_DELIVERY": False}), start=1
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

    def test_revision_requires_diff_review_and_stops_after_two_rounds_by_reason(self) -> None:
        state, candidate = self.reach_problem_review()
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

    def test_agent_commit_requires_message_bound_authorization_and_assessment(self) -> None:
        state, candidate = self.reach_decision_route(suffix="no-auth")
        with self.assertRaisesRegex(AlphaContractError, "source message|authorization"):
            self.choose(
                state,
                candidate,
                outcome="COMMIT_NOW",
                actor_kind="AGENT",
                suffix="no-auth",
                authorize=False,
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

    def test_required_evals_block_ready_recommended_preserves_truth_without_blocking(self) -> None:
        required = self.reach_prd_authoring(intent="EXPERIMENT", suffix="required")
        required = self.freeze_prd(required, applicability="REQUIRED", suffix="required")
        required = self.pass_review(
            required, required["current_candidate"], suffix="required-prd"
        )
        self.assertEqual(required["ready"]["status"], "NOT_READY")
        self.assertIn("REQUIRED_PRODUCT_EVALS", required["ready"]["unmet"])

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
            / "PRD_TEMPLATE_v2.0-alpha.md"
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

    def test_prd_candidate_rejects_pre_generated_png(self) -> None:
        state = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="repair-png")
        draft = self.write_prd_draft(state["run_id"])
        assets = draft / "assets"
        assets.mkdir()
        (assets / "main-flow@2x.png").write_bytes(b"not-a-candidate-format")

        with self.assertRaisesRegex(AlphaContractError, "Handoff-only"):
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
