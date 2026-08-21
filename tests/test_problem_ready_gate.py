from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.failpoints import InjectedCrash, crash_at, recover_run
from src.bpg.host_runtime import HostRuntime
from src.bpg.node_validation import NodeValidationError, validate_node_output
from src.bpg.state_controller import StateController
from src.bpg.storage import atomic_write_json, read_json, sha256_file
from tests.controller_fixtures import position_run_internal


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


def problem_ready_result(output: dict) -> dict:
    return {
        "schema_version": "node-result.v1",
        "node_id": "problem.ready.gate",
        "attempt_id": "attempt-ready",
        "producer": {
            "kind": "DETERMINISTIC_PROGRAM",
            "component": "state-controller",
        },
        "mechanical_output": output,
        "artifact_refs": [],
    }


def ready_output() -> dict:
    return {
        "status": "READY",
        "validator": "problem_ready_gate",
        "rules_version": "problem-ready.v1",
        "source_attempt_id": "review-attempt",
        "candidate_ref": {
            "role": "problem_definition_candidate",
            "path": "problem-candidate.json",
            "hash": "sha256:" + "1" * 64,
            "version": 1,
        },
        "unmet_conditions": [],
    }


class ProblemReadyGateContractTests(unittest.TestCase):
    def test_problem_ready_mechanical_output_is_closed_world_and_status_exact(self) -> None:
        validate_node_output("problem.ready.gate", problem_ready_result(ready_output()))
        not_ready = ready_output()
        not_ready["status"] = "NOT_READY"
        not_ready["unmet_conditions"] = [
            {
                "condition": "upstream.exact_refs",
                "affected_refs": [not_ready["candidate_ref"]],
                "finding_ids": [],
                "repair_target": "REBIND_UPSTREAM_REF",
                "resume_node": "problem.ready.gate",
            }
        ]
        validate_node_output("problem.ready.gate", problem_ready_result(not_ready))

        attacks = (
            ({**ready_output(), "status": "PASS"}, "READY or NOT_READY"),
            ({**ready_output(), "future_authority": "ACCEPT"}, "future_authority"),
            (
                {
                    **not_ready,
                    "unmet_conditions": [
                        {**not_ready["unmet_conditions"][0], "future_authority": "ACCEPT"}
                    ],
                },
                "future_authority",
            ),
            ({**ready_output(), "unmet_conditions": not_ready["unmet_conditions"]}, "READY"),
        )
        for output, error in attacks:
            with self.subTest(error=error):
                with self.assertRaisesRegex(NodeValidationError, error):
                    validate_node_output("problem.ready.gate", problem_ready_result(output))

    def test_problem_ready_after_result_crash_recovers_once_and_advances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            controller = StateController(project, GRAPH)
            runtime = HostRuntime(project, GRAPH, REPO_ROOT / "src" / "core")
            run_id = "problem-ready-crash"
            controller.create_run(run_id, raw_signal="Problem Ready crash")
            candidate_path = project / "problem-candidate.json"
            atomic_write_json(candidate_path, {"problem_definition": "恢复边界"})
            candidate_ref = {
                "role": "problem_definition_candidate",
                "path": candidate_path.relative_to(project).as_posix(),
                "hash": sha256_file(candidate_path),
                "version": 1,
            }
            refs = dict(controller.load_state(run_id)["artifact_refs"])
            refs["problem-candidate"] = candidate_ref
            position_run_internal(
                controller,
                run_id,
                "problem.quality.review",
                ["problem.ready.gate"],
                artifact_refs=refs,
            )
            review_dispatch = runtime._plan_dispatch(run_id)
            review = {
                "candidate_ref": candidate_ref,
                "candidate_hash": candidate_ref["hash"],
                "candidate_version": 1,
                "upstream_refs": [],
                "review_version": "problem-quality-review.v0.1",
                "findings": [{"id": "finding-1", "concern": "保留边界"}],
                "dispositions": [{"finding_id": "finding-1", "status": "ADDRESSED"}],
                "recommended_disposition": "PROCEED_TO_DETERMINISTIC_READY_CHECK",
                "reviewer_authority": "ADVISORY_ONLY",
                "ready_claim": "NOT_MADE",
            }
            review_result = {
                "schema_version": "node-result.v1",
                "node_id": "problem.quality.review",
                "attempt_id": review_dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": review_dispatch["instruction_ref"],
                "instruction_hash": review_dispatch["instruction_hash"],
                "input_refs": review_dispatch["input_refs"],
                "input_hashes": review_dispatch["input_hashes"],
                "resource_refs": review_dispatch["resource_refs"],
                "semantic_output": review,
                "artifact_refs": [],
            }
            controller.submit_result(run_id, review_result)
            state = controller.load_state(run_id)
            controller.transition(
                run_id,
                {
                    "requested_node": "problem.ready.gate",
                    "attempt_id": review_dispatch["attempt_id"],
                    "expected_state_version": state["state_version"],
                },
            )
            gate_dispatch = runtime._plan_dispatch(run_id)

            with self.assertRaises(InjectedCrash):
                controller.execute_mechanical_result(
                    run_id,
                    gate_dispatch["attempt_id"],
                    failpoint=crash_at("after_result_persist"),
                )

            recovered = recover_run(controller, run_id)
            self.assertEqual(recovered["status"], "RECOVERED_RESULT")
            result_path = controller._result_path(run_id, gate_dispatch["attempt_id"])
            self.assertEqual(read_json(result_path)["mechanical_output"]["status"], "READY")
            first = runtime.dispatch_current(run_id)
            self.assertEqual(first["status"], "ADVANCED")
            self.assertEqual(first["gate_result"]["status"], "READY")
            self.assertEqual(first["dispatch"]["node_id"], "product.decision")
            state = controller.load_state(run_id)
            self.assertEqual(state["current_node"], "product.decision")
            self.assertEqual(
                state["consumed_attempts"].count(gate_dispatch["attempt_id"]),
                1,
            )
