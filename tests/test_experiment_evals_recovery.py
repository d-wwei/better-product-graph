from __future__ import annotations

import tempfile
import unittest
import shutil
from pathlib import Path

from src.bpg.evals_authority import EvalsAuthorityError, validate_reviewed_evals
from src.bpg.host_runtime import HostRuntime
from src.bpg.state_controller import StateController, TransitionRejected
from src.bpg.storage import atomic_write_json, read_json, sha256_file, verify_event_chain
from tests.test_candidate_finalize_recovery import prepare_review_finalize
from tests.test_prd_contract import REPO_ROOT, complete_experiment_contract, prd_submission


GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"
LEGACY_GRAPH = REPO_ROOT / "tests" / "fixtures" / "graph" / "manifest-0.1.0-alpha.1.json"


def required_submission(*, delivery_intent: str) -> dict:
    submission = prd_submission()
    metadata = submission["semantic_output"]["metadata"]
    metadata["delivery_intent"] = delivery_intent
    metadata["evals"] = {
        "applicability": "REQUIRED",
        "fulfillment": "REVIEW_PENDING",
        "execution_status": "NOT_RUN",
    }
    if delivery_intent == "EXPERIMENT":
        metadata["experiment_contract"] = complete_experiment_contract()
    return submission


class ExperimentEvalsRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _finalized_pending_run(
        self, run_id: str, *, delivery_intent: str, graph: Path = GRAPH
    ) -> tuple[HostRuntime, dict]:
        if graph == LEGACY_GRAPH:
            legacy_root = self.project / ".legacy-graph"
            legacy_root.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(graph, legacy_root / "manifest.json")
            registry = read_json(
                REPO_ROOT / "src" / "core" / "graph" / "node-contracts.json"
            )
            legacy_manifest = read_json(graph)
            legacy_nodes = {item["id"] for item in legacy_manifest["nodes"]}
            registry["nodes"] = {
                node_id: contract
                for node_id, contract in registry["nodes"].items()
                if node_id in legacy_nodes
            }
            legacy_routes = {
                node_id: sorted(
                    edge["to"]
                    for edge in legacy_manifest["edges"]
                    if edge["from"] == node_id
                )
                for node_id in legacy_nodes
            }
            for node_id, contract in registry["nodes"].items():
                contract["routes"] = legacy_routes[node_id]
                contract.pop("compatible_route_sets", None)
            ready_contract = registry["nodes"]["prd.ready.gate"]
            atomic_write_json(legacy_root / "node-contracts.json", registry)
            graph = legacy_root / "manifest.json"
        controller, _, attempt_id = prepare_review_finalize(
            self.project,
            run_id,
            submission=required_submission(delivery_intent=delivery_intent),
            graph=graph,
        )
        state = controller.load_state(run_id)
        controller.finalize_review_and_transition(
            run_id, attempt_id, expected_state_version=state["state_version"]
        )
        return HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core"), controller.load_state(run_id)

    def test_experiment_pending_required_evals_returns_exact_repair_without_ready_claims(self) -> None:
        runtime, before = self._finalized_pending_run(
            "run-experiment-evals-repair", delivery_intent="EXPERIMENT"
        )

        result = runtime.dispatch_current("run-experiment-evals-repair")
        state = runtime.controller.load_state("run-experiment-evals-repair")

        self.assertEqual(result["status"], "EVALS_FULFILLMENT_REQUIRED")
        self.assertEqual(result["execution_status"], "NOT_RUN")
        self.assertEqual(result["repair_operation"], "fulfill-evals")
        self.assertEqual(state["current_node"], "prd.ready.gate")
        self.assertEqual(state["next_allowed_nodes"], ["review.parallel"])
        self.assertEqual(state["ready_receipts"], [])
        self.assertIsNone(state["release_ref"])
        self.assertGreaterEqual(state["state_version"], before["state_version"])

    def test_commit_pending_required_evals_remains_not_ready(self) -> None:
        runtime, _ = self._finalized_pending_run(
            "run-commit-evals-repair", delivery_intent="COMMIT"
        )

        result = runtime.dispatch_current("run-commit-evals-repair")
        state = runtime.controller.load_state("run-commit-evals-repair")

        self.assertEqual(result["status"], "EVALS_FULFILLMENT_REQUIRED")
        self.assertEqual(state["ready_receipts"], [])
        self.assertIsNone(state["release_ref"])

    def test_legacy_stuck_experiment_run_migrates_without_rebuild(self) -> None:
        runtime, legacy_state = self._finalized_pending_run(
            "run-legacy-experiment-evals",
            delivery_intent="EXPERIMENT",
            graph=LEGACY_GRAPH,
        )
        self.assertEqual(legacy_state["next_allowed_nodes"], ["handoff.prepare"])

        result = runtime.dispatch_current("run-legacy-experiment-evals")
        migrated = runtime.controller.load_state("run-legacy-experiment-evals")

        self.assertEqual(result["status"], "EVALS_FULFILLMENT_REQUIRED")
        self.assertEqual(migrated["next_allowed_nodes"], ["review.parallel"])
        self.assertEqual(migrated["graph_manifest"]["version"], "0.1.0-alpha.3")
        self.assertEqual(migrated["current_candidate_ref"], legacy_state["current_candidate_ref"])
        self.assertEqual(migrated["ready_receipts"], [])
        self.assertIsNone(migrated["release_ref"])

    def test_public_resume_exposes_closed_legacy_eval_repair_contract_repeatedly(self) -> None:
        run_id = "run-legacy-resume-evals"
        runtime, legacy_state = self._finalized_pending_run(
            run_id,
            delivery_intent="EXPERIMENT",
            graph=LEGACY_GRAPH,
        )
        self.assertEqual(legacy_state["next_allowed_nodes"], ["handoff.prepare"])

        first = runtime.engine.handle(f"$better-product-graph resume {run_id}")
        first_state = runtime.controller.load_state(run_id)
        repeated = runtime.engine.handle(f"$better-product-graph resume {run_id}")
        repeated_state = runtime.controller.load_state(run_id)

        for result in (first, repeated):
            self.assertEqual(result["status"], "EVALS_FULFILLMENT_REQUIRED")
            self.assertEqual(result["repair_operation"], "fulfill-evals")
            self.assertEqual(result["execution_status"], "NOT_RUN")
            self.assertEqual(result["next_nodes"], ["review.parallel"])
            self.assertEqual(set(result["candidate_ref"]), {"path", "hash", "version"})
        self.assertEqual(first["candidate_ref"], repeated["candidate_ref"])
        self.assertEqual(first_state["current_node"], "prd.ready.gate")
        self.assertEqual(first_state["next_allowed_nodes"], ["review.parallel"])
        self.assertEqual(repeated_state["current_node"], "prd.ready.gate")
        self.assertEqual(repeated_state["next_allowed_nodes"], ["review.parallel"])
        self.assertEqual(repeated_state["ready_receipts"], [])
        self.assertIsNone(repeated_state["release_ref"])
        events = verify_event_chain(runtime.controller._events_path(run_id))
        self.assertEqual(
            sum(
                event["event_type"] == "EVALS_FULFILLMENT_REQUIRED"
                for event in events
            ),
            1,
        )

    def test_independent_eval_fulfillment_reenters_joint_review_without_release(self) -> None:
        run_id = "run-experiment-evals-fulfilled"
        runtime, _ = self._finalized_pending_run(run_id, delivery_intent="EXPERIMENT")
        pending = runtime.dispatch_current(run_id)
        candidate = pending["candidate_ref"]
        state = runtime.controller.load_state(run_id)
        provenance_ref = next(
            ref
            for ref in state["artifact_refs"].values()
            if ref.get("role") == "decision_record"
        )
        fixtures_ref = self._write_ref(
            "evals/fixtures.json",
            {"schema_version": "eval-fixtures.v1", "cases": ["continue", "stop"]},
        )
        pack = {
            "schema_version": "better-product-graph.eval-pack.v1",
            "status": "SPECIFICATION_REVIEW_PENDING",
            "candidate_ref": candidate,
            "applicability": "REQUIRED",
            "execution_status": "NOT_RUN",
            "ground_truth_provenance": {
                "type": "CONTRACT_DERIVED_EXPECTATIONS",
                "statement": "Expected outcomes derive only from the exact Decision and experiment contract.",
                "exact_refs": [
                    {key: provenance_ref[key] for key in ("path", "hash", "version")}
                ],
            },
            "producer": {"kind": "HOST_AGENT", "id": "eval-pack-builder"},
            "evaluator_contract": {
                "contract_id": "bootstrap-context-mvu",
                "fixtures_ref": fixtures_ref,
            },
            "cases": [
                {"case_id": "continue", "expected_outcome": "CONTINUE"},
                {"case_id": "stop", "expected_outcome": "STOP"},
            ],
        }
        pack_ref = self._write_ref("evals/eval-pack.json", pack)
        review = {
            "schema_version": "better-product-graph.eval-pack-review.v1",
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": "independent-eval-reviewer"},
            "reviewed_at": "2026-08-24T12:00:00+00:00",
            "subjects": {
                "prd_draft_ref": candidate,
                "fixtures_ref": fixtures_ref,
                "eval_pack_ref": pack_ref,
            },
            "finding_closure": [],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }
        review_ref = self._write_ref("evals/eval-pack-review.json", review)
        payload = {
            "schema_version": "evals-fulfillment-submission.v1",
            "candidate_ref": candidate,
            "build_attempt": {"kind": "HOST_AGENT", "id": "eval-pack-builder"},
            "review_attempt": {"kind": "SUBAGENT", "id": "independent-eval-reviewer"},
            "eval_pack_ref": pack_ref,
            "fixtures_ref": fixtures_ref,
            "review_ref": review_ref,
        }

        before_forgery = runtime.controller.load_state(run_id)
        forged = {**payload, "review_attempt": payload["build_attempt"]}
        with self.assertRaisesRegex(TransitionRejected, "builder and independent reviewer"):
            runtime.fulfill_evals(run_id, forged)
        self.assertEqual(runtime.controller.load_state(run_id), before_forgery)

        result = runtime.fulfill_evals(run_id, payload)
        updated = runtime.controller.load_state(run_id)
        metadata_path = next(
            (self.project / updated["current_candidate_ref"]["artifact_path"]).glob("*.metadata.json")
        )
        metadata = read_json(metadata_path)
        companion = read_json(self.project / updated["current_candidate_ref"]["review_path"])

        self.assertEqual(result["status"], "EVALS_FULFILLED_REVIEW_REQUIRED")
        self.assertEqual(updated["current_node"], "review.parallel")
        self.assertEqual(metadata["evals"]["fulfillment"], "REVIEWED")
        self.assertEqual(metadata["evals"]["execution_status"], "NOT_RUN")
        self.assertEqual(companion["status"], "NOT_RUN")
        self.assertEqual(updated["ready_receipts"], [])
        self.assertIsNone(updated["release_ref"])
        self.assertEqual(result["dispatch"]["node_id"], "review.parallel")

        receipt_path = self.project / result["receipt_ref"]["path"]
        atomic_write_json(receipt_path, {"tampered": True})
        input_hashes = {
            ref["path"]: ref["hash"]
            for ref in updated["artifact_refs"].values()
            if isinstance(ref.get("path"), str) and isinstance(ref.get("hash"), str)
        }
        with self.assertRaisesRegex(EvalsAuthorityError, "receipt"):
            validate_reviewed_evals(
                self.project,
                REPO_ROOT / "src" / "core",
                metadata["evals"],
                expected_candidate_ref=candidate,
                artifact_refs=updated["artifact_refs"],
                dispatched_input_hashes=input_hashes,
                committed_attempt_ids=frozenset(updated["consumed_attempts"]),
            )

    def _write_ref(self, relative: str, payload: dict) -> dict:
        path = self.project / relative
        atomic_write_json(path, payload)
        return {
            "path": path.relative_to(self.project).as_posix(),
            "hash": sha256_file(path),
            "version": 1,
        }


if __name__ == "__main__":
    unittest.main()
