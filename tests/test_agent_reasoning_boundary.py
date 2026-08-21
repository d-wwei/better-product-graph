from __future__ import annotations

import unittest

from src.bpg.contracts import PolicyViolation, validate_node_result_producer


class AgentReasoningBoundaryTests(unittest.TestCase):
    def test_semantic_result_requires_host_agent_and_exact_provenance(self) -> None:
        result = {
            "node_id": "product.decision",
            "attempt_id": "attempt-1",
            "producer": {"kind": "DETERMINISTIC_PROGRAM"},
            "semantic_output": {"recommendation": "COMMIT"},
        }

        with self.assertRaisesRegex(PolicyViolation, "HOST_AGENT"):
            validate_node_result_producer(result)

    def test_host_agent_semantic_result_requires_instruction_and_input_hashes(self) -> None:
        result = {
            "node_id": "problem.synthesize",
            "attempt_id": "attempt-2",
            "producer": {"kind": "HOST_AGENT"},
            "semantic_output": {"problem_definition": "用户无法恢复被误删的草稿"},
        }

        with self.assertRaisesRegex(PolicyViolation, "instruction_ref"):
            validate_node_result_producer(result)

    def test_mechanical_result_may_be_produced_by_controller(self) -> None:
        result = {
            "node_id": "prd.ready.gate",
            "attempt_id": "attempt-3",
            "producer": {"kind": "DETERMINISTIC_PROGRAM", "component": "state-controller"},
            "mechanical_output": {
                "status": "NOT_READY",
                "unmet_conditions": ["review.finalize missing"],
            },
        }

        validated = validate_node_result_producer(result)

        self.assertEqual(validated["producer"]["kind"], "DETERMINISTIC_PROGRAM")

    def test_program_cannot_hide_semantic_output_in_mechanical_node(self) -> None:
        result = {
            "node_id": "prd.ready.gate",
            "attempt_id": "attempt-4",
            "producer": {"kind": "DETERMINISTIC_PROGRAM", "component": "state-controller"},
            "mechanical_output": {"status": "READY"},
            "semantic_output": {"prd_content": "由程序生成的产品需求"},
        }

        with self.assertRaisesRegex(PolicyViolation, "semantic_output"):
            validate_node_result_producer(result)


if __name__ == "__main__":
    unittest.main()
