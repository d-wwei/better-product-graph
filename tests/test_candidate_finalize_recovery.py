from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.documents import archive_prd_candidate, hash_tree
from src.bpg.failpoints import InjectedCrash, begin_node_call, crash_at, persist_node_dispatch, recover_run
from src.bpg.host_runtime import HostRuntime
from src.bpg.prd_contract import assemble_prd
from src.bpg.state_controller import StateConflict, StateController
from src.bpg.storage import atomic_write_json, read_json, sha256_file, verify_event_chain
from src.bpg.templates import TemplateRegistry
from tests.controller_fixtures import position_run_internal
from tests.test_prd_contract import REPO_ROOT, TEMPLATES, prd_submission
from tests.writing_review_fixtures import attach_zero_finding_writing_coverage


GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


def prepare_review_finalize(
    project: Path,
    run_id: str,
    *,
    submission: dict | None = None,
    graph: Path = GRAPH,
) -> tuple[StateController, object, str]:
    controller = StateController(project, graph, skill_root=REPO_ROOT / "src" / "core")
    controller.create_run(run_id, raw_signal="Candidate finalize recovery")
    assembled = assemble_prd(
        submission or prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
    )
    archived = archive_prd_candidate(project, assembled, assets={})
    candidate = {
        "path": archived.document_path.relative_to(project).as_posix(),
        "hash": archived.document_hash,
        "tree_hash": archived.tree_hash,
        "artifact_path": archived.path.relative_to(project).as_posix(),
        "version": archived.version,
        "review_path": archived.review_path.relative_to(project).as_posix(),
        "review_hash": archived.review_hash,
        "generation": 1,
    }
    commitment_path = project / "decision-commitment.json"
    atomic_write_json(commitment_path, {"kind": "decision", "version": 1})
    commitment = {
        "path": commitment_path.relative_to(project).as_posix(),
        "hash": sha256_file(commitment_path),
        "version": 1,
    }
    position_run_internal(
        controller,
        run_id,
        "review.parallel",
        ["review.aggregate"],
        artifact_refs={
            "prd-candidate": {"role": "prd_candidate", **candidate},
            "commitment": {"role": "decision_record", **commitment},
        },
        state_updates={"current_candidate_ref": candidate, "candidate_version": 1},
    )
    runtime = HostRuntime(project, graph, REPO_ROOT / "src" / "core")
    review_dispatch = runtime.dispatch_current(run_id)
    resources = {item["resource_id"]: item for item in review_dispatch["resource_refs"]}

    def exact(resource_id: str) -> dict:
        return {
            key: resources[resource_id][key]
            for key in ("path", "hash", "version")
        }

    candidate_identity = {
        key: candidate[key] for key in ("path", "hash", "version")
    }
    finding = {
        "finding_id": "finding-recovery",
        "topic_id": "candidate-finalize",
        "stance": "recoverable",
        "concern": "finalize must recover at every durable boundary",
        "concern_level": "KEY_ATTENTION",
        "basis_refs": [candidate["path"], commitment["path"]],
        "possible_impact": "orphaned or inconsistent Candidate generation",
        "professional_recommendation": "use the Controller transaction journal",
        "confidence": "high",
        "confidence_basis": "exact Candidate and commitment refs",
    }
    review_result = {
        "schema_version": "node-result.v1",
        "node_id": "review.parallel",
        "attempt_id": review_dispatch["attempt_id"],
        "producer": {"kind": "HOST_AGENT"},
        "instruction_ref": review_dispatch["instruction_ref"],
        "instruction_hash": review_dispatch["instruction_hash"],
        "input_refs": review_dispatch["input_refs"],
        "input_hashes": review_dispatch["input_hashes"],
        "resource_refs": review_dispatch["resource_refs"],
        "semantic_output": {
            "candidate_ref": candidate_identity,
            "reviewer_role": "combined-advisory-review",
            "reviewer_profile": "product-goal-fidelity-v0.1",
            "roles_covered": ["product", "engineering_feasibility", "testability"],
            "authority": "ADVISORY_ONLY",
            "goal_fidelity_refs": {
                "profile_ref": exact("goal-fidelity-profile"),
                "rubric_ref": exact("goal-fidelity-rubric"),
                "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                "commitment_refs": [commitment],
            },
            "goal_fidelity_packet": {
                "goal": "Preserve exact Candidate generation authority",
                "candidate_ref": candidate_identity,
                "commitment_refs": [commitment],
            },
            "findings": [finding],
        },
        "artifact_refs": [],
    }
    writing_ref = attach_zero_finding_writing_coverage(
        project, review_dispatch, review_result
    )
    aggregate_dispatch = runtime.submit_and_advance(
        run_id, review_result, requested_node="review.aggregate"
    )["dispatch"]
    aggregate = {
        "schema_version": "review-aggregate.v1",
        "authority": "ADVISORY_ONLY",
        "candidate_ref": candidate_identity,
        "attempts": [
            {
                "attempt_id": review_dispatch["attempt_id"],
                "status": "COMPLETED",
                "roles_covered": ["product", "engineering_feasibility", "testability"],
            }
        ],
        "findings": [finding],
        "disagreements": [
            {"topic_id": "candidate-finalize", "finding_ids": ["finding-recovery"]}
        ],
        "writing_coverage_ref": writing_ref,
    }
    dispositions = {
        "schema_version": "review-dispositions.v1",
        "candidate_hash": candidate["hash"],
        "candidate_version": candidate["version"],
        "dispositions": [{"finding_id": "finding-recovery", "status": "ADDRESSED"}],
    }
    aggregate_path = project / "review-aggregate.json"
    dispositions_path = project / "review-dispositions.json"
    atomic_write_json(aggregate_path, aggregate)
    atomic_write_json(dispositions_path, dispositions)
    aggregate_result = {
        "schema_version": "node-result.v1",
        "node_id": "review.aggregate",
        "attempt_id": aggregate_dispatch["attempt_id"],
        "producer": {"kind": "HOST_AGENT"},
        "instruction_ref": aggregate_dispatch["instruction_ref"],
        "instruction_hash": aggregate_dispatch["instruction_hash"],
        "input_refs": aggregate_dispatch["input_refs"],
        "input_hashes": aggregate_dispatch["input_hashes"],
        "resource_refs": aggregate_dispatch["resource_refs"],
        "semantic_output": {
            **aggregate,
            "dispositions": dispositions["dispositions"],
        },
        "artifact_refs": [
            {
                "role": "review_aggregate",
                "path": aggregate_path.relative_to(project).as_posix(),
                "hash": sha256_file(aggregate_path),
                "version": 1,
            },
            {
                "role": "review_dispositions",
                "path": dispositions_path.relative_to(project).as_posix(),
                "hash": sha256_file(dispositions_path),
                "version": 1,
            },
        ],
    }
    controller.submit_result(run_id, aggregate_result)
    state = controller.load_state(run_id)
    controller.transition(
        run_id,
        {
            "attempt_id": aggregate_dispatch["attempt_id"],
            "expected_state_version": state["state_version"],
            "requested_node": "review.finalize",
        },
    )
    state = controller.load_state(run_id)
    attempt_id = "attempt-review-finalize-recovery"
    refs = [ref["path"] for ref in state["artifact_refs"].values()]
    hashes = {ref["path"]: ref["hash"] for ref in state["artifact_refs"].values()}
    contract = controller.registry.dispatch_envelope(
        "review.finalize", attempt_id, refs, hashes
    )
    persist_node_dispatch(controller, run_id, attempt_id, contract=contract)
    begin_node_call(controller, run_id, attempt_id)
    return controller, archived, attempt_id


class CandidateFinalizeRecoveryTests(unittest.TestCase):
    def test_candidate_finalize_early_recovery_rejects_tampered_publish_inputs_without_side_effects(self) -> None:
        attacks = ("stage", "history")
        for index, attack in enumerate(attacks, start=1):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as directory:
                project = Path(directory).resolve()
                run_id = f"run-candidate-finalize-early-{index}"
                controller, _, attempt_id = prepare_review_finalize(project, run_id)
                state = controller.load_state(run_id)

                with self.assertRaises(InjectedCrash):
                    controller.finalize_review_and_transition(
                        run_id,
                        attempt_id,
                        expected_state_version=state["state_version"],
                        failpoint=crash_at("after_candidate_finalize_staged"),
                    )

                journal_path = controller._transaction_path(
                    run_id, f"review-finalize-{attempt_id}"
                )
                journal = read_json(journal_path)
                tamper_root = Path(journal["candidate_publish"][f"{attack}_path"])
                tamper_root.mkdir(parents=True, exist_ok=True)
                (tamper_root / "tampered-after-staged.txt").write_text(
                    "tampered", encoding="utf-8"
                )
                before = {
                    path.relative_to(project).as_posix()
                    + ("/" if path.is_dir() else ""): (
                        None if path.is_dir() else path.read_bytes()
                    )
                    for path in project.rglob("*")
                }

                with self.assertRaises(StateConflict):
                    controller.authoritative_read_barrier(run_id)

                after = {
                    path.relative_to(project).as_posix()
                    + ("/" if path.is_dir() else ""): (
                        None if path.is_dir() else path.read_bytes()
                    )
                    for path in project.rglob("*")
                }
                self.assertEqual(after, before)
                self.assertEqual(read_json(journal_path)["status"], "PREPARED")

    def test_candidate_finalize_recovery_validates_stage_before_moving_current_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            run_id = "run-candidate-finalize-tampered-stage"
            controller, archived, attempt_id = prepare_review_finalize(project, run_id)
            before_tree_hash = hash_tree(archived.path)
            state = controller.load_state(run_id)

            with self.assertRaises(InjectedCrash):
                controller.finalize_review_and_transition(
                    run_id,
                    attempt_id,
                    expected_state_version=state["state_version"],
                    failpoint=crash_at("after_candidate_finalize_state"),
                )

            journal = read_json(
                controller._transaction_path(run_id, f"review-finalize-{attempt_id}")
            )
            stage = Path(journal["candidate_publish"]["stage_path"])
            history = Path(journal["candidate_publish"]["history_path"])
            (stage / "tampered-after-crash.txt").write_text("tampered", encoding="utf-8")

            with self.assertRaises(StateConflict):
                controller.authoritative_read_barrier(run_id)

            self.assertTrue(archived.path.is_dir())
            self.assertEqual(hash_tree(archived.path), before_tree_hash)
            self.assertFalse(history.exists())

    def test_candidate_finalize_recovers_every_staged_event_state_publish_boundary(self) -> None:
        phases = (
            "after_candidate_finalize_staged",
            "after_candidate_finalize_event",
            "after_candidate_finalize_state",
            "after_candidate_finalize_publish",
        )
        for index, phase in enumerate(phases, start=1):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                project = Path(directory).resolve()
                run_id = f"run-candidate-finalize-{index}"
                controller, archived, attempt_id = prepare_review_finalize(project, run_id)
                before_document = archived.document_path.read_bytes()
                before_version = archived.version
                state = controller.load_state(run_id)

                with self.assertRaises(InjectedCrash):
                    controller.finalize_review_and_transition(
                        run_id,
                        attempt_id,
                        expected_state_version=state["state_version"],
                        failpoint=crash_at(phase),
                    )

                recover_run(controller, run_id)
                recover_run(controller, run_id)
                recovered = controller.authoritative_read_barrier(run_id)
                companion = read_json(archived.review_path)
                history = (
                    controller.run_path(run_id)
                    / "candidate-generations"
                    / "generation-1"
                    / archived.path.name
                )
                events = verify_event_chain(controller._events_path(run_id))

                self.assertEqual(archived.document_path.read_bytes(), before_document)
                self.assertEqual(recovered["current_candidate_ref"]["version"], before_version)
                self.assertEqual(recovered["current_candidate_ref"]["generation"], 2)
                self.assertEqual(recovered["current_node"], "prd.ready.gate")
                self.assertEqual(companion["status"], "FINALIZED")
                self.assertEqual(read_json(history / archived.review_path.name)["status"], "NOT_RUN")
                self.assertEqual(hash_tree(archived.path), recovered["current_candidate_ref"]["tree_hash"])
                self.assertEqual(
                    sum(event["event_type"] == "REVIEW_FINALIZE_COMMITTED" for event in events),
                    1,
                )


if __name__ == "__main__":
    unittest.main()
