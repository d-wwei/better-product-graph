from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.bugs import BugContractError, persist_bug_packet, validate_bug_assessment
from src.bpg.connectors import LocalHandoffConnector, NullConnector
from src.bpg.incidents import IncidentContractError, persist_incident_packet
from src.bpg.storage import sha256_file


def host_agent_result(node_id: str, semantic_output: dict, attempt_id: str) -> dict:
    return {
        "node_id": node_id,
        "attempt_id": attempt_id,
        "producer": {"kind": "HOST_AGENT", "host": "codex"},
        "instruction_ref": f"references/atomic-skills/{node_id}/INSTRUCTIONS.md",
        "instruction_hash": "sha256:instructions",
        "input_refs": ["artifacts/raw-signal-v1.json"],
        "input_hashes": {"artifacts/raw-signal-v1.json": "sha256:raw"},
        "semantic_output": semantic_output,
        "artifact_refs": [],
    }


class IncidentAndBugTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_incident_packet_is_append_only_actionable_and_marks_missing_data(self) -> None:
        result = host_agent_result(
            "incident.assess",
            {
                "summary": "支付提交失败，需工程核验",
                "severity": "S1",
                "impact": "结算受阻",
                "reproduction": "NOT_AVAILABLE",
                "scope": "NOT_AVAILABLE",
                "missing_data": ["reproduction", "scope"],
                "next_action": "工程确认日志与影响范围",
                "runtime_status": "WAITING_ENGINEERING",
            },
            "incident-attempt-1",
        )
        packet = persist_incident_packet(self.project, "incident-001", result)

        self.assertEqual(packet["schema_version"], "incident.verification.packet.v1")
        self.assertEqual(packet["runtime_status"], "WAITING_ENGINEERING")
        self.assertEqual(packet["assessment"]["reproduction"], "NOT_AVAILABLE")
        self.assertLessEqual(len(Path(packet["human_view_path"]).read_text().splitlines()), 16)
        with self.assertRaisesRegex(IncidentContractError, "already exists"):
            persist_incident_packet(self.project, "incident-001", result)

    def test_null_connector_never_claims_remote_delivery_and_local_handoff_is_explicit(self) -> None:
        null = NullConnector("feishu")
        local = LocalHandoffConnector(self.project)
        null_result = null.dispatch({"id": "packet-1"})
        local_result = local.dispatch({"id": "packet-1", "summary": "local only"})

        self.assertEqual(null.status()["status"], "NOT_CONFIGURED")
        self.assertEqual(null_result["status"], "NOT_AVAILABLE")
        self.assertFalse(null_result["sent"])
        self.assertEqual(local_result["status"], "WRITTEN_LOCAL")
        self.assertFalse(local_result["sent_remote"])

    def test_implementation_deviation_requires_agent_submitted_complete_baseline_contract(self) -> None:
        baseline = self.project / "baseline.md"
        baseline.write_text("Expected: total remains visible\n", encoding="utf-8")
        ref = {"path": str(baseline), "hash": sha256_file(baseline), "version": 1}
        result = host_agent_result(
            "bug.baseline.check",
            {
                "classification": "IMPLEMENTATION_DEVIATION",
                "baseline_ref": ref,
                "expected": "total remains visible",
                "actual": "total disappears",
                "new_rule_required": False,
                "acceptance_criteria_decidable": True,
                "material_conflict": False,
                "next_action": "修复显示并跑回归",
            },
            "bug-attempt-1",
        )
        validated = validate_bug_assessment(result)
        packet = persist_bug_packet(self.project, "bug-001", result)

        self.assertEqual(validated["classification"], "IMPLEMENTATION_DEVIATION")
        self.assertEqual(packet["delivery_profile"], "LIGHT")

    def test_exact_bug_packet_retry_is_idempotent_but_conflicting_bytes_are_rejected(self) -> None:
        baseline = self.project / "baseline.md"
        baseline.write_text("Expected: total remains visible\n", encoding="utf-8")
        result = host_agent_result(
            "bug.baseline.check",
            {
                "classification": "IMPLEMENTATION_DEVIATION",
                "baseline_ref": {
                    "path": str(baseline),
                    "hash": sha256_file(baseline),
                    "version": 1,
                },
                "expected": "total remains visible",
                "actual": "total disappears",
                "new_rule_required": False,
                "acceptance_criteria_decidable": True,
                "material_conflict": False,
                "next_action": "修复显示并跑回归",
            },
            "bug-attempt-retry",
        )
        first = persist_bug_packet(self.project, "bug-retry", result)
        second = persist_bug_packet(self.project, "bug-retry", result)
        self.assertEqual(first["packet_ref"], second["packet_ref"])
        self.assertEqual(first["human_ref"], second["human_ref"])

        human = self.project / first["human_ref"]["path"]
        human.write_text("tampered\n", encoding="utf-8")
        packet_before = (self.project / first["packet_ref"]["path"]).read_bytes()
        with self.assertRaisesRegex(BugContractError, "different bytes"):
            persist_bug_packet(self.project, "bug-retry", result)
        self.assertEqual(
            (self.project / first["packet_ref"]["path"]).read_bytes(),
            packet_before,
        )

    def test_program_does_not_choose_bug_classification_or_fill_missing_semantics(self) -> None:
        result = host_agent_result(
            "bug.baseline.check",
            {
                "classification": None,
                "baseline_ref": None,
                "expected": None,
                "actual": None,
            },
            "bug-attempt-2",
        )
        with self.assertRaisesRegex(BugContractError, "Agent classification") as captured:
            validate_bug_assessment(result)
        self.assertNotIn("suggested", str(captured.exception).lower())

    def test_false_implementation_deviation_is_rejected_instead_of_reclassified(self) -> None:
        result = host_agent_result(
            "bug.baseline.check",
            {
                "classification": "IMPLEMENTATION_DEVIATION",
                "baseline_ref": None,
                "expected": "x",
                "actual": "x",
                "new_rule_required": True,
                "acceptance_criteria_decidable": False,
                "material_conflict": True,
                "next_action": "unknown",
            },
            "bug-attempt-3",
        )
        with self.assertRaises(BugContractError) as captured:
            validate_bug_assessment(result)
        self.assertNotIn("PRODUCT_LOGIC_DEFECT", str(captured.exception))
        self.assertNotIn("SPEC_AMBIGUITY", str(captured.exception))


if __name__ == "__main__":
    unittest.main()
