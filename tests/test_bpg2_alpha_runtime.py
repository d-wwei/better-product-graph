from __future__ import annotations

import json
import tempfile
import unittest
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


class BPG2AlphaRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.controller = BPG2AlphaController(self.project)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def start(self, *, preauthorization: dict | None = None, suffix: str = "1") -> dict:
        return self.controller.start_run(
            signal="用户无法确认异步任务是否已经完成",
            route={"destination": "PRODUCT_PLANNING", "attempt_id": f"route-{suffix}"},
            operation_id=f"start-{suffix}",
            run_id=f"bpg2-run-{suffix}",
            preauthorization=preauthorization,
        )

    def update_record(
        self,
        state: dict,
        *,
        position: str,
        next_position: str | None = None,
        suffix: str,
    ) -> dict:
        return self.controller.update_planning_record(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"record-{suffix}",
            author_attempt_id=f"author-{suffix}",
            position=position,
            markdown=(
                "# 产品规划主记录\n\n"
                f"当前位置：{position}\n\n"
                "## 当前事实与分析\n\n"
                f"{suffix}：事实、推断、未知与当前结论保持可区分。\n"
            ),
            next_position=next_position,
        )

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

    def pass_review(self, state: dict, candidate: dict, *, suffix: str) -> dict:
        return self.controller.submit_review(
            state["run_id"],
            expected_state_version=state["state_version"],
            operation_id=f"review-pass-{suffix}",
            candidate_ref=candidate,
            reviewer_attempt_id=f"reviewer-{suffix}",
            verdict="PASS",
            findings=[],
        )

    def reach_decision_route(
        self, *, preauthorization: dict | None = None, suffix: str = "1"
    ) -> tuple[dict, dict]:
        state = self.start(preauthorization=preauthorization, suffix=suffix)
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
        authorization_id: str | None = None,
        agent_assessment: dict | None = None,
    ) -> dict:
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
            authorization_id=authorization_id,
            agent_assessment=agent_assessment,
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
        (draft / "assets").mkdir(parents=True, exist_ok=True)
        (draft / "PRD.md").write_text(PRD_MARKDOWN, encoding="utf-8")
        (draft / "assets" / "flow.png").write_bytes(b"\x89PNG\r\n\x1a\nalpha")
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

    @staticmethod
    def evals(status: str, *, generated: bool = False) -> dict:
        attachments = (
            ["product-evals.md", "product-evals-review.json"] if generated else []
        )
        return {
            "applicability": status,
            "reason": "Agent 基于产品质量的可确定验收程度作出的轻量判断",
            "generation_status": "GENERATED" if generated else "NOT_AVAILABLE",
            "execution_status": "NOT_RUN",
            "attachment_paths": attachments,
            "spec_review_status": "PASS" if generated else "NOT_RUN",
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
        )

    def reach_prd_authoring(
        self, *, intent: str, suffix: str, preauthorized: bool = False
    ) -> dict:
        preauthorization = (
            {
                "authorization_id": f"auth-{suffix}",
                "allowed_outcome": "COMMIT_NOW",
                "scope": "LOCAL_PLANNING_ONLY",
            }
            if preauthorized
            else None
        )
        state, candidate = self.reach_decision_route(
            preauthorization=preauthorization, suffix=suffix
        )
        state = self.choose(
            state,
            candidate,
            outcome=intent,
            actor_kind="AGENT" if preauthorized else "OWNER",
            authorization_id=f"auth-{suffix}" if preauthorized else None,
            agent_assessment=self.agent_assessment(state) if preauthorized else None,
            suffix=suffix,
        )
        if intent == "COMMIT_NOW":
            state = self.update_record(
                state,
                position="PLAN_PRODUCT_SYSTEM",
                next_position="PRD_AUTHORING",
                suffix=f"{suffix}-plan",
            )
        return state

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
                verdict="PASS",
                findings=[],
            )

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
            verdict="REVISE",
            findings=[
                {
                    "finding_id": "F-1",
                    "severity": "MAJOR",
                    "status": "OPEN",
                    "evidence": "问题与目标链未闭合",
                }
            ],
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
            verdict="REVISE",
            findings=[],
            return_target="DIAGNOSE_VALUE",
            return_reason="仍需修复价值因果",
            affected_scope=["价值因果"],
            review_mode="DIFF_AND_REGRESSION",
            diff_base_candidate_ref=candidate,
            global_regression="PASS",
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
            verdict="REVISE",
            findings=[],
            return_target="RESEARCH",
            return_reason="证据不足，不能继续自动修订",
            affected_scope=["H1", "H2"],
            review_mode="DIFF_AND_REGRESSION",
            diff_base_candidate_ref=revised,
            global_regression="PASS",
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

    def test_agent_commit_requires_exact_preauthorization_and_other_routes_require_owner(self) -> None:
        state, candidate = self.reach_decision_route(suffix="no-auth")
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            actor_kind="AGENT",
            suffix="no-auth",
        )
        self.assertEqual(state["status"], "OWNER_CHOICE_REQUIRED")
        self.assertIsNone(state.get("decision"))

        state, candidate = self.reach_decision_route(
            preauthorization={
                "authorization_id": "auth-missing-assessment",
                "allowed_outcome": "COMMIT_NOW",
                "scope": "LOCAL_PLANNING_ONLY",
            },
            suffix="missing-assessment",
        )
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            actor_kind="AGENT",
            authorization_id="auth-missing-assessment",
            suffix="missing-assessment",
        )
        self.assertEqual(state["status"], "OWNER_CHOICE_REQUIRED")
        self.assertIsNone(state.get("decision"))

        state, candidate = self.reach_decision_route(
            preauthorization={
                "authorization_id": "auth-exact",
                "allowed_outcome": "COMMIT_NOW",
                "scope": "LOCAL_PLANNING_ONLY",
            },
            suffix="auth",
        )
        state = self.choose(
            state,
            candidate,
            outcome="COMMIT_NOW",
            actor_kind="AGENT",
            authorization_id="auth-exact",
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
        fulfilled = self.freeze_prd(
            fulfilled,
            applicability="REQUIRED",
            generated=True,
            suffix="fulfilled",
        )
        fulfilled = self.pass_review(
            fulfilled, fulfilled["current_candidate"], suffix="fulfilled-prd"
        )
        self.assertEqual(fulfilled["status"], "READY")
        self.assertEqual(fulfilled["product_evals"]["execution_status"], "NOT_RUN")

        recommended = self.reach_prd_authoring(intent="COMMIT_NOW", suffix="recommended")
        recommended = self.freeze_prd(
            recommended, applicability="RECOMMENDED", suffix="recommended"
        )
        recommended = self.pass_review(
            recommended, recommended["current_candidate"], suffix="recommended-prd"
        )
        self.assertEqual(recommended["status"], "READY")
        self.assertEqual(recommended["product_evals"]["generation_status"], "NOT_AVAILABLE")
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
        candidate_dir = self.project / state["current_candidate"]["artifact_path"]
        self.assertTrue((candidate_dir / manifest["template_ref"]["path"]).is_file())
        self.assertTrue(
            (candidate_dir / manifest["planning_record_snapshot_ref"]["path"]).is_file()
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
        )
        self.assertEqual(state["status"], "LOCAL_HANDOFF_COMPLETE")
        self.assertEqual(state["retrospective_status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
