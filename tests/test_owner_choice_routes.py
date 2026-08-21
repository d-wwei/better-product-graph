from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.decision_contract import validate_decision_draft
from src.bpg.failpoints import InjectedCrash, crash_at
from src.bpg.product_memory import persist_decision_proposal
from src.bpg.state_controller import StateController, TransitionRejected
from src.bpg.storage import verify_event_chain
from tests.controller_fixtures import position_run_internal


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


def agent_draft() -> dict:
    return {
        "recommendation": "COMMIT",
        "reasons": ["目标明确", "证据边界可接受"],
        "mvu": "用户是否持续遇到该阻碍",
        "nearest_alternative": "EXPERIMENT",
        "flip_condition": "关键风险无法控制",
        "next_action": "等待 Owner 独立选择",
        "epistemic_confidence": "MEDIUM",
        "action_risk": {
            "level": "R1", "basis": "reversible local exposure",
            "reversible": True, "measurable": True,
            "rollback": "restore prior local version",
        },
        "non_waivable_policy_violations": [],
        "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
    }


def agent_submission(draft: dict | None = None) -> dict:
    return {
        "schema_version": "node-result.v1", "node_id": "product.decision",
        "attempt_id": "decision-attempt-1", "producer": {"kind": "HOST_AGENT"},
        "instruction_ref": "references/atomic-skills/product-decision/INSTRUCTIONS.md",
        "instruction_hash": "sha256:instructions", "input_refs": ["problem-v3.json"],
        "input_hashes": {"problem-v3.json": "sha256:problem"},
        "semantic_output": draft or agent_draft(), "artifact_refs": [],
    }


def place_at_decision(controller: StateController, run_id: str) -> dict:
    return position_run_internal(
        controller,
        run_id,
        "product.decision",
        ["product.planning", "evidence.collect"],
    )


class OwnerChoiceRouteTests(unittest.TestCase):
    def test_agent_decision_draft_cannot_self_authorize_owner_choice(self) -> None:
        draft = agent_draft()
        draft.update({"owner_choice": "COMMIT", "owner_authorized": True})
        validation = validate_decision_draft(draft)
        self.assertEqual(validation.status, "NOT_READY")
        self.assertIn("authority.owner_fields_forbidden", validation.repair_targets)

    def test_owner_command_requires_exact_proposal_owner_actor_and_state_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            controller = StateController(project, GRAPH)
            controller.create_run("run-owner", raw_signal="test")
            state = place_at_decision(controller, "run-owner")
            proposal = persist_decision_proposal(project, "decision-owner", "run-owner", agent_submission())
            command = {
                "schema_version": "owner-choice-command.v1", "decision_id": "decision-owner",
                "proposal_ref": proposal["proposal_ref"], "proposal_hash": proposal["proposal_ref"]["hash"],
                "actor": {"kind": "OWNER", "id": "eli"},
                "expected_state_version": state["state_version"], "choice": "COMMIT",
                "commit_timing": "NOW", "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
            }
            with self.assertRaisesRegex(TransitionRejected, "Owner actor"):
                controller.apply_owner_choice("run-owner", {**command, "actor": {"kind": "HOST_AGENT", "id": "codex"}})
            with self.assertRaisesRegex(TransitionRejected, "state version"):
                controller.apply_owner_choice("run-owner", {**command, "expected_state_version": 0})
            with self.assertRaisesRegex(TransitionRejected, "proposal hash"):
                controller.apply_owner_choice("run-owner", {**command, "proposal_hash": "sha256:" + "0" * 64})

    def test_all_six_choice_variants_create_distinct_durable_routes(self) -> None:
        cases = [
            ("STOP", None, "CLOSED", "product.decision"),
            ("WAIT", None, "WAITING_TRIGGER", "product.decision"),
            ("RESEARCH", None, "ACTIVE", "evidence.collect"),
            ("EXPERIMENT", None, "ACTIVE", "product.planning"),
            ("COMMIT", "NOW", "ACTIVE", "product.planning"),
            ("COMMIT", "FUTURE", "ROADMAP_ONLY", "product.decision"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (choice, timing, status, node) in enumerate(cases, start=1):
                project = root / str(index); project.mkdir()
                controller = StateController(project, GRAPH); run_id = f"run-{index}"
                controller.create_run(run_id, raw_signal="test")
                state = place_at_decision(controller, run_id)
                proposal = persist_decision_proposal(project, f"decision-{index}", run_id, agent_submission())
                command = {
                    "schema_version": "owner-choice-command.v1", "decision_id": f"decision-{index}",
                    "proposal_ref": proposal["proposal_ref"], "proposal_hash": proposal["proposal_ref"]["hash"],
                    "actor": {"kind": "OWNER", "id": "eli"},
                    "expected_state_version": state["state_version"], "choice": choice,
                    "commit_timing": timing,
                    "outcome_details": {choice: {"review_trigger": "new material evidence"}},
                }
                updated = controller.apply_owner_choice(run_id, command)
                self.assertEqual(updated["status"], status)
                self.assertEqual(updated["current_node"], node)
                self.assertEqual(updated["decision"]["chosen_outcome"], choice)

    def test_owner_choice_recovers_record_or_event_before_state_without_new_version(self) -> None:
        for index, phase in enumerate(("after_decision_record", "after_owner_event"), start=1):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                controller = StateController(project, GRAPH)
                run_id = f"run-owner-crash-{index}"
                controller.create_run(run_id, raw_signal="test")
                state = place_at_decision(controller, run_id)
                proposal = persist_decision_proposal(
                    project, f"decision-crash-{index}", run_id, agent_submission()
                )
                command = {
                    "schema_version": "owner-choice-command.v1",
                    "decision_id": proposal["decision_id"],
                    "proposal_ref": proposal["proposal_ref"],
                    "proposal_hash": proposal["proposal_ref"]["hash"],
                    "actor": {"kind": "OWNER", "id": "eli"},
                    "expected_state_version": state["state_version"],
                    "choice": "WAIT",
                    "commit_timing": None,
                    "outcome_details": {"WAIT": {"review_trigger": "new evidence"}},
                }
                with self.assertRaises(InjectedCrash):
                    controller.apply_owner_choice(
                        run_id, command, failpoint=crash_at(phase)
                    )

                recovered = controller.apply_owner_choice(run_id, command)
                decisions = list(
                    (project / ".better-product-graph" / "decisions" / proposal["decision_id"]).glob("DECISION_v*.json")
                )
                product_events = verify_event_chain(
                    project / ".better-product-graph" / "product-memory" / "PRODUCT_CHANGELOG.jsonl"
                )
                run_events = verify_event_chain(controller._events_path(run_id))
                self.assertEqual(recovered["decision"]["record_ref"]["version"], 1)
                self.assertEqual(len(decisions), 1)
                self.assertEqual(len(product_events), 1)
                self.assertEqual(
                    len([event for event in run_events if event["event_type"] == "OWNER_CHOICE_RECORDED"]),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
