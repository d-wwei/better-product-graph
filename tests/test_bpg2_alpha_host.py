from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.runner import apply_alpha


REPO_ROOT = Path(__file__).resolve().parents[1]


class BPG2AlphaHostTests(unittest.TestCase):
    def test_installed_skill_exposes_only_an_explicit_alpha_entry_and_baseline(self) -> None:
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

            self.assertIn("Opt-in BPG 2.0 single-PRD Alpha", skill)
            self.assertIn("$better-product-graph alpha", skill)
            self.assertIn("Never silently route", skill)
            self.assertTrue(baseline.is_file())

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

            state = call(
                "start",
                signal="用户无法确认后台任务是否完成",
                route={"destination": "PRODUCT_PLANNING", "attempt_id": "host-route"},
                operation_id="host-start",
                run_id="bpg2-run-host",
                preauthorization={
                    "authorization_id": "host-auth",
                    "allowed_outcome": "COMMIT_NOW",
                    "scope": "LOCAL_PLANNING_ONLY",
                },
            )
            state = call(
                "update-record",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-understand",
                author_attempt_id="host-author-understand",
                position="UNDERSTAND",
                next_position="DIAGNOSE_VALUE",
                markdown="# 产品规划主记录\n\n## UNDERSTAND\n\n背景、目标、用户、需求、现状、差距和未知。\n",
            )
            state = call(
                "update-record",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-diagnose",
                author_attempt_id="host-author-diagnose",
                position="DIAGNOSE_VALUE",
                markdown="# 产品规划主记录\n\n## UNDERSTAND\n\n背景与目标。\n\n## DIAGNOSE & VALUE\n\nH1/H2/H3、因果、价值与成功标准。\n",
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
                verdict="PASS",
                findings=[],
            )
            state = call(
                "update-record",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-solutions",
                author_attempt_id="host-author-solutions",
                position="DISCOVER_SOLUTIONS_DECIDE",
                markdown="# 产品规划主记录\n\n## Decision Candidate\n\n推荐 COMMIT NOW，保留最强替代与改判条件。\n",
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
                authorization_id="host-auth",
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
            state = call(
                "update-record",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-plan",
                author_attempt_id="host-plan-author",
                position="PLAN_PRODUCT_SYSTEM",
                next_position="PRD_AUTHORING",
                markdown="# 产品规划主记录\n\n## 整体—局部—整体\n\n整体框架、关键局部、整体回归与单 PRD 边界。\n",
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
                    "generation_status": "NOT_AVAILABLE",
                    "execution_status": "NOT_RUN",
                    "attachment_paths": [],
                    "spec_review_status": "NOT_RUN",
                },
            )
            state = call(
                "review",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-prd-review",
                candidate_ref=state["current_candidate"],
                reviewer_attempt_id="host-prd-reviewer",
                verdict="PASS",
                findings=[],
            )
            self.assertEqual(state["status"], "READY")
            state = call(
                "handoff",
                run_id=state["run_id"],
                expected_state_version=state["state_version"],
                operation_id="host-handoff",
            )

            self.assertEqual(state["status"], "LOCAL_HANDOFF_COMPLETE")
            self.assertEqual(state["external_delivery"], "NOT_RUN")
            self.assertTrue((project / state["handoff"]["path"] / "PRD.html").is_file())


if __name__ == "__main__":
    unittest.main()
