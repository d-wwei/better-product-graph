from __future__ import annotations

import unittest

from src.bpg.planning_contract import derive_prd_run_specs, validate_plan


def complete_plan() -> dict:
    return {
        "profile": {"id": "STANDARD", "reason": "跨两个产品模块且有共享状态依赖"},
        "decision_ref": {"path": "decision-v1.json", "hash": "sha256:decision", "version": 1},
        "target_operating_outcome": "用户能完成结算并看见可恢复状态",
        "observable_evidence": ["成功提交率与恢复成功率"],
        "non_sacrificable_guardrails": ["不重复扣款"],
        "current_iteration_outcome": "先完成失败可见与安全重试闭环",
        "modules": [
            {"id": "checkout", "responsibility": "提交与结果反馈"},
            {"id": "recovery", "responsibility": "幂等恢复"},
        ],
        "iterations": [
            {
                "id": "iteration-1",
                "outcome": "失败用户可安全重试并知道结果",
                "end_to_end": True,
                "validation": "端到端行为与指标",
                "stop_condition": "出现重复扣款",
            }
        ],
        "dependencies": [{"from": "checkout", "to": "recovery"}],
        "shared_contracts": [
            {
                "id": "payment-state-v1",
                "consumers": ["checkout", "recovery"],
                "contract": "The submission state has one stable identity and an explicit recovery outcome.",
            }
        ],
        "material_items": [{"id": "item-submit"}, {"id": "item-future"}],
        "coverage": [
            {
                "item_id": "item-submit",
                "disposition": "CURRENT:slice-1",
                "owner": "product",
                "impact": "当前闭环",
                "review_trigger": "scope changes",
            },
            {
                "item_id": "item-future",
                "disposition": "FUTURE:phase-2",
                "owner": "product",
                "impact": "后续体验优化",
                "review_trigger": "phase-2 activation",
            },
        ],
        "slices": [
            {
                "id": "slice-1",
                "activated": True,
                "eligible": True,
                "user_outcome": "失败用户可安全重试并知道结果",
                "modules": ["checkout", "recovery"],
                "iteration": "iteration-1",
                "dependencies": ["payment-state-v1"],
                "validation": "端到端 AC",
                "split_reason": "可独立交付、验证和回滚的产品闭环",
                "delivery_intent": "COMMIT",
            },
            {
                "id": "slice-future",
                "activated": False,
                "eligible": True,
                "user_outcome": "后续优化",
                "modules": ["checkout"],
                "iteration": "iteration-1",
                "dependencies": [],
                "validation": "future",
                "split_reason": "尚未激活",
                "delivery_intent": "COMMIT",
            },
        ],
        "prd_matrix": [
            {
                "slice_id": "slice-1",
                "planned_prd_id": "PRD-CHECKOUT-001",
                "primary_module": "checkout",
                "iteration": "iteration-1",
            },
            {
                "slice_id": "slice-future",
                "planned_prd_id": "PRD-CHECKOUT-FUTURE",
                "primary_module": "checkout",
                "iteration": "iteration-1",
            },
        ],
    }


class PlanningContractTests(unittest.TestCase):
    def test_missing_slices_are_not_generated_by_python(self) -> None:
        plan = complete_plan()
        plan["slices"] = []
        plan["prd_matrix"] = []
        result = validate_plan(plan)
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("agent.slices", result.repair_targets)
        self.assertEqual(result.generated_artifacts, [])
        self.assertNotIn("suggested_value", result.as_dict())

    def test_outcome_first_horizontal_vertical_and_coverage_contract_is_ready(self) -> None:
        result = validate_plan(complete_plan())
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.repair_targets, [])

    def test_shared_contract_defined_inside_exact_plan_is_authoritative_for_slice(self) -> None:
        plan = complete_plan()
        self.assertNotIn("authoritative_ref", plan["shared_contracts"][0])

        result = validate_plan(plan)

        self.assertEqual(result.status, "READY", result.repair_targets)

    def test_unknown_slice_dependency_returns_the_exact_slice_repair_target(self) -> None:
        plan = complete_plan()
        plan["slices"][0]["dependencies"].append("missing-contract-v1")

        result = validate_plan(plan)

        self.assertEqual(result.status, "NOT_READY")
        self.assertIn(
            "slices.slice-1.dependencies.exact_refs",
            result.repair_targets,
        )

    def test_profile_requires_agent_reason_and_light_keeps_core_product_contract(self) -> None:
        plan = complete_plan()
        plan["profile"] = {"id": "LIGHT", "reason": ""}
        plan["observable_evidence"] = []
        result = validate_plan(plan)
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("agent.profile_reason", result.repair_targets)
        self.assertIn("agent.observable_evidence", result.repair_targets)
        self.assertNotIn("selected_profile", result.as_dict())

    def test_dependency_cycle_is_rejected_without_reordering_modules(self) -> None:
        plan = complete_plan()
        plan["dependencies"].append({"from": "recovery", "to": "checkout"})
        result = validate_plan(plan)
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("dependencies.cycle", result.repair_targets)
        self.assertEqual(result.generated_artifacts, [])

    def test_every_material_item_requires_exactly_one_transparent_disposition(self) -> None:
        plan = complete_plan()
        plan["coverage"].append(
            {
                "item_id": "item-submit",
                "disposition": "WAIT:owner",
                "owner": "product",
                "impact": "duplicate",
                "review_trigger": "later",
            }
        )
        result = validate_plan(plan)
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("coverage.exactly_once", result.repair_targets)

    def test_only_activated_and_eligible_end_to_end_slices_create_prd_run_specs(self) -> None:
        specs = derive_prd_run_specs(complete_plan())
        self.assertEqual([item["slice_id"] for item in specs], ["slice-1"])
        self.assertEqual(specs[0]["delivery_intent"], "COMMIT")
        self.assertEqual(specs[0]["planned_prd_id"], "PRD-CHECKOUT-001")
        self.assertEqual(specs[0]["parent_decision_ref"]["hash"], "sha256:decision")

        invalid = complete_plan()
        invalid["slices"][0]["activated"] = "yes"
        self.assertIn("slices.end_to_end_contract", validate_plan(invalid).repair_targets)

    def test_candidate_version_pins_anywhere_in_plan_are_not_ready(self) -> None:
        attacks = {
            "slice_version": lambda plan: plan["slices"][0].update(
                {"candidate_version": "v0.1"}
            ),
            "slice_current_ref": lambda plan: plan["slices"][0].update(
                {"current_candidate_ref": {"path": "candidate.md", "version": "v0.1"}}
            ),
            "top_level_current_ref": lambda plan: plan.update(
                {"current_candidate_ref": {"path": "candidate.md", "version": "v0.1"}}
            ),
            "coverage_version": lambda plan: plan["coverage"][0].update(
                {"candidate_version": "v0.1"}
            ),
            "compound_planned_id": lambda plan: plan["prd_matrix"][0].update(
                {"planned_prd_id": "PRD-CHECKOUT-v0.1"}
            ),
            "candidate_planned_id": lambda plan: plan["prd_matrix"][0].update(
                {"planned_prd_id": "candidate/v0.1"}
            ),
            "aliased_candidate_ref": lambda plan: plan.update(
                {
                    "baseline_spec_ref": {
                        "path": "artifacts/prds/archived/PRD-X_v0.1.md",
                        "hash": "sha256:old",
                        "version": "v0.1",
                    }
                }
            ),
        }

        for attack, mutate in attacks.items():
            with self.subTest(attack=attack):
                plan = complete_plan()
                mutate(plan)
                result = validate_plan(plan)
                self.assertEqual(result.status, "NOT_READY")
                self.assertIn("prd_matrix.candidate_version", result.repair_targets)

        legitimate_domain = complete_plan()
        legitimate_domain["prd_matrix"][0]["planned_prd_id"] = (
            "PRD-CANDIDATE-MANAGEMENT-001"
        )
        self.assertEqual(validate_plan(legitimate_domain).status, "READY")

    def test_plan_matrix_requires_stable_prd_id_and_forbids_candidate_version_pin(self) -> None:
        missing = complete_plan()
        missing["prd_matrix"][0].pop("planned_prd_id")
        self.assertIn("prd_matrix.stable_prd_identity", validate_plan(missing).repair_targets)

        pinned = complete_plan()
        pinned["prd_matrix"][0]["candidate_version"] = "v0.1"
        self.assertIn("prd_matrix.candidate_version", validate_plan(pinned).repair_targets)

        aliases = (
            {"planned_prd_version": "v0.1"},
            {"latest_candidate": {"version": "v0.1"}},
            {"release": "v0.1"},
        )
        for alias in aliases:
            with self.subTest(alias=alias):
                pinned = complete_plan()
                pinned["prd_matrix"][0].update(alias)
                self.assertIn(
                    "prd_matrix.candidate_version",
                    validate_plan(pinned).repair_targets,
                )


if __name__ == "__main__":
    unittest.main()
