from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.decision_contract import (
    route_owner_choice,
    validate_decision_draft,
)
from src.bpg.product_memory import persist_decision_proposal, record_owner_decision


REPO_ROOT = Path(__file__).resolve().parents[1]


def complete_draft() -> dict:
    return {
        "recommendation": "COMMIT",
        "reasons": ["目标明确", "证据边界可接受"],
        "mvu": "用户是否持续遇到该阻碍",
        "nearest_alternative": "EXPERIMENT",
        "flip_condition": "关键风险无法控制",
        "next_action": "Owner 作出选择",
        "epistemic_confidence": "MEDIUM",
        "action_risk": {
            "level": "R1",
            "basis": "limited reversible local exposure",
            "reversible": True,
            "measurable": True,
            "rollback": "restore prior local version",
        },
        "non_waivable_policy_violations": [],
        "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
    }


class DecisionContractTests(unittest.TestCase):
    def test_installed_instruction_publishes_one_complete_first_submit_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            instruction = (
                plugin
                / "skills"
                / "better-product-graph"
                / "references"
                / "atomic-skills"
                / "product-decision"
                / "INSTRUCTIONS.md"
            ).read_text(encoding="utf-8")
        match = re.search(
            r"<!-- PRODUCT_DECISION_SEMANTIC_OUTPUT_START -->\s*"
            r"```json\s*(\{.*?\})\s*```\s*"
            r"<!-- PRODUCT_DECISION_SEMANTIC_OUTPUT_END -->",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(
            match,
            "installed Product Decision instruction must publish one exact JSON example",
        )
        draft = json.loads(match.group(1))
        validation = validate_decision_draft(draft)
        self.assertEqual(validation.status, "READY", validation.repair_targets)
        self.assertNotIn("owner_choice", draft)
        self.assertNotIn("owner_authorized", draft)
        self.assertIn("只表示在当前绑定材料中没有发现已知硬性违规", instruction)
        self.assertIn("不等于已经完成独立合规审计", instruction)
        self.assertIn("不要向用户裸露", instruction)

        owner_match = re.search(
            r"<!-- OWNER_CHOICE_COMMAND_START -->\s*"
            r"```json\s*(\{.*?\})\s*```\s*"
            r"<!-- OWNER_CHOICE_COMMAND_END -->",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(
            owner_match,
            "installed Product Decision instruction must publish the exact Owner command",
        )
        owner_command = json.loads(owner_match.group(1))
        self.assertEqual(
            set(owner_command),
            {
                "schema_version", "decision_id", "proposal_ref", "proposal_hash",
                "actor", "expected_state_version", "choice", "commit_timing",
                "outcome_details",
            },
        )
        self.assertEqual(owner_command["schema_version"], "owner-choice-command.v1")

    def test_validator_reports_missing_semantics_without_choosing_values(self) -> None:
        result = validate_decision_draft({"recommendation": None})
        self.assertEqual(result.status, "NOT_READY")
        self.assertEqual(result.repair_targets[0], "agent.recommendation")
        self.assertEqual(result.generated_artifacts, [])
        self.assertNotIn("suggested_value", result.as_dict())

    def test_agent_draft_cannot_include_owner_authority(self) -> None:
        draft = complete_draft()
        draft["owner_choice"] = "COMMIT"
        draft["owner_authorized"] = True
        result = validate_decision_draft(draft)
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("authority.owner_fields_forbidden", result.repair_targets)
        self.assertIsNone(result.route)

    def test_five_owner_choices_map_only_to_legal_deterministic_routes(self) -> None:
        cases = {
            ("STOP", None): "CLOSED",
            ("WAIT", None): "WAITING_TRIGGER",
            ("RESEARCH", None): "WAITING_EVIDENCE",
            ("EXPERIMENT", None): "PLAN_RUN_EXPERIMENT",
            ("COMMIT", "NOW"): "PLAN_RUN",
            ("COMMIT", "FUTURE"): "ROADMAP_ONLY",
        }
        self.assertEqual(
            {key: route_owner_choice(key[0], commit_timing=key[1]) for key in cases},
            cases,
        )

    def test_validator_keeps_only_chosen_outcome_details_and_never_recommends(self) -> None:
        draft = complete_draft()
        draft["outcome_details"]["EXPERIMENT"] = {"hypothesis": "extra"}
        result = validate_decision_draft(draft)
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("outcome_details.recommendation_only", result.repair_targets)
        self.assertNotIn("recommended_route", result.as_dict())

    def test_owner_authority_cannot_downgrade_policy_risk_or_waive_hard_violation(self) -> None:
        draft = complete_draft()
        draft["action_risk"]["level"] = "R0"
        draft["non_waivable_policy_violations"] = ["privacy.consent_missing"]
        result = validate_decision_draft(draft, minimum_risk_level="R2")
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("action_risk.minimum_policy", result.repair_targets)
        self.assertIn("policy.non_waivable_violations", result.repair_targets)
        self.assertNotIn("waiver", result.as_dict())

    def test_persisted_record_binds_agent_provenance_and_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            draft = complete_draft()
            submission = {
                "schema_version": "node-result.v1",
                "node_id": "product.decision",
                "attempt_id": "decision-attempt-1",
                "producer": {"kind": "HOST_AGENT", "host": "codex"},
                "instruction_ref": "references/atomic-skills/product-decision/INSTRUCTIONS.md",
                "instruction_hash": "sha256:instructions",
                "input_refs": ["problem-v3.json"],
                "input_hashes": {"problem-v3.json": "sha256:problem"},
                "semantic_output": draft,
                "artifact_refs": [],
            }
            proposal = persist_decision_proposal(root, "decision-001", "run-001", submission)
            record = record_owner_decision(
                root,
                proposal,
                {
                    "actor": {"kind": "OWNER", "id": "eli"},
                    "choice": "COMMIT",
                    "commit_timing": "NOW",
                    "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
                },
            )
            self.assertEqual(record["chosen_outcome"], "COMMIT")
            self.assertEqual(record["route"], "PLAN_RUN")
            self.assertEqual(set(record["outcome_details"]), {"COMMIT"})
            self.assertEqual(record["owner_authority"]["actor"]["kind"], "OWNER")
            self.assertNotEqual(record["owner_authority"], record["agent_draft"]["epistemic_confidence"])
            self.assertTrue((root / record["record_ref"]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
