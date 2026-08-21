from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.bpg.evals_authority import (
    EvalsAuthorityError,
    _validate_provenance,
    validate_reviewed_evals,
)
from src.bpg.ready import calculate_prd_ready
from src.bpg.state_controller import StateController
from src.bpg.storage import atomic_write_json, sha256_file
from tests.test_reviews_ready import complete_ready_input


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class ReviewedEvalsAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _json(self, relative: str, payload: dict) -> dict:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, payload)
        return {
            "path": path.relative_to(self.project).as_posix(),
            "hash": sha256_file(path),
            "version": 1,
        }

    def _fixture(self, *, pack_schema: str = "better-product-graph.eval-pack.v0.2", review_schema: str = "better-product-graph.eval-pack-review.v0.1") -> dict:
        draft_path = self.project / "drafts" / "candidate-v0.2.md"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text("# Exact Candidate v0.2\n", encoding="utf-8")
        candidate_ref = {
            "path": draft_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(draft_path),
            "version": "v0.2",
        }
        decision_ref = self._json(
            "authority/decision.json", {"kind": "decision", "status": "COMMIT"}
        )
        fixtures_ref = self._json(
            "evals/fixtures.json", {"fixtures": [{"input": "retry", "expected": "one result"}]}
        )
        provenance = {
            "type": "CONTRACT_DERIVED_EXPECTATIONS",
            "statement": "Expected outcomes are derived from the committed Decision.",
            "exact_refs": [decision_ref],
        }
        pack = {
            "schema_version": pack_schema,
            "status": "SPECIFICATION_REVIEW_PENDING",
            "candidate_ref": candidate_ref,
            "applicability": "REQUIRED",
            "execution_status": "NOT_RUN",
            "ground_truth_provenance": provenance,
            "producer": {"kind": "AGENT", "id": "planner-agent"},
            "evaluator_contract": {
                "contract_id": "checkout-recovery-v1",
                "fixtures_ref": fixtures_ref,
            },
            "cases": [
                {"case_id": "retry-once", "expected_outcome": "one committed result"}
            ],
        }
        pack_ref = self._json("evals/eval-pack.json", pack)
        review = {
            "schema_version": review_schema,
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": "testability-reviewer"},
            "reviewed_at": "2026-08-20T12:00:00+08:00",
            "subjects": {
                "prd_draft_ref": candidate_ref,
                "fixtures_ref": fixtures_ref,
                "eval_pack_ref": pack_ref,
            },
            "finding_closure": [{"finding_id": "eval-f-1", "status": "CLOSED"}],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }
        review_ref = self._json("evals/eval-pack-review.json", review)
        artifacts = [
            {
                "role": "node_result",
                "node_id": "prd.generate",
                "attempt_id": "attempt-prd-generate",
            },
            {
                "role": "node_result",
                "node_id": "review.parallel",
                "attempt_id": "attempt-review-parallel",
            },
            {
                "role": "prd_draft",
                **candidate_ref,
                "origin_node_id": "prd.generate",
                "origin_attempt_id": "attempt-prd-generate",
            },
            {"role": "decision", **decision_ref},
            {
                "role": "eval_fixtures",
                **fixtures_ref,
                "origin_node_id": "prd.generate",
                "origin_attempt_id": "attempt-prd-generate",
            },
            {
                "role": "eval_pack",
                **pack_ref,
                "origin_node_id": "prd.generate",
                "origin_attempt_id": "attempt-prd-generate",
            },
            {
                "role": "eval_pack_review",
                **review_ref,
                "origin_node_id": "review.parallel",
                "origin_attempt_id": "attempt-review-parallel",
            },
        ]
        inputs = {
            item["path"]: item["hash"]
            for item in artifacts
            if "path" in item and "hash" in item
        }
        evals = {
            "applicability": "REQUIRED",
            "fulfillment": "REVIEWED",
            "execution_status": "NOT_RUN",
            "pack_ref": pack_ref,
            "review_ref": review_ref,
            "ground_truth_provenance": provenance,
        }
        return {
            "candidate_ref": candidate_ref,
            "pack": pack,
            "pack_ref": pack_ref,
            "review": review,
            "review_ref": review_ref,
            "artifacts": artifacts,
            "inputs": inputs,
            "evals": evals,
        }

    def _validate(self, fixture: dict) -> None:
        validate_reviewed_evals(
            self.project,
            REPO_ROOT / "src" / "core",
            fixture["evals"],
            expected_candidate_ref={
                "hash": fixture["candidate_ref"]["hash"],
                "version": fixture["candidate_ref"]["version"],
            },
            artifact_refs=fixture["artifacts"],
            dispatched_input_hashes=fixture["inputs"],
            committed_attempt_ids=frozenset(
                {"attempt-prd-generate", "attempt-review-parallel"}
            ),
        )

    def _rewrite(self, fixture: dict, kind: str, payload: dict) -> None:
        ref_key = f"{kind}_ref"
        ref = fixture[ref_key]
        path = self.project / ref["path"]
        atomic_write_json(path, payload)
        new_hash = sha256_file(path)
        old_hash = ref["hash"]
        ref["hash"] = new_hash
        fixture["inputs"][ref["path"]] = new_hash
        for artifact in fixture["artifacts"]:
            if artifact.get("path") == ref["path"] and artifact.get("hash") == old_hash:
                artifact["hash"] = new_hash
        fixture["evals"][ref_key]["hash"] = new_hash

    def test_trial_and_v1_schema_pairs_validate_specification_consistency_only(self) -> None:
        trial = self._fixture()
        trial["artifacts"].append(deepcopy(trial["artifacts"][3]))
        trial["artifacts"].append(deepcopy(trial["artifacts"][5]))
        self._validate(trial)
        self._validate(
            self._fixture(
                pack_schema="better-product-graph.eval-pack.v1",
                review_schema="better-product-graph.eval-pack-review.v1",
            )
        )

    def test_controller_derives_typed_eval_origins_instead_of_trusting_artifact_claims(self) -> None:
        controller = StateController(self.project, GRAPH)
        run_id = "run-eval-origin"
        controller.create_run(run_id, raw_signal="typed Eval authority")
        state = controller.load_state(run_id)
        pack_ref = self._json("evals/origin-pack.json", {"pack": "bytes"})
        attempt_id = "attempt-prd-origin"
        result = {
            "node_id": "prd.generate",
            "artifact_refs": [
                {
                    "role": "eval_pack",
                    **pack_ref,
                    "origin_node_id": "attacker-node",
                    "origin_attempt_id": "attacker-attempt",
                }
            ],
        }
        atomic_write_json(controller._result_path(run_id, attempt_id), result)

        controller._bind_committed_outputs(state, run_id, attempt_id, result)

        bound = state["artifact_refs"][f"node-output:{attempt_id}:0:eval_pack"]
        self.assertEqual(bound["origin_node_id"], "prd.generate")
        self.assertEqual(bound["origin_attempt_id"], attempt_id)

    def test_required_review_pending_is_honestly_not_ready(self) -> None:
        request = complete_ready_input(
            {"path": "candidate", "hash": "sha256:candidate", "version": "v0.2"}
        )
        request["evals"] = {
            "applicability": "REQUIRED",
            "fulfillment": "REVIEW_PENDING",
            "execution_status": "NOT_RUN",
            "reason": "awaiting future independent Eval fulfillment",
        }

        result = calculate_prd_ready(request)

        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("EVALS", {item["category"] for item in result.unmet})

    def test_required_reviewed_is_not_ready_without_verifiable_fulfillment_authority(self) -> None:
        fixture = self._fixture()
        request = complete_ready_input(
            {
                "path": fixture["candidate_ref"]["path"],
                "hash": fixture["candidate_ref"]["hash"],
                "version": fixture["candidate_ref"]["version"],
            }
        )
        request["evals"] = {
            **fixture["evals"],
            "pack_ref": {
                **fixture["pack_ref"],
                "resolved_hash": fixture["pack_ref"]["hash"],
            },
            "review_ref": {
                **fixture["review_ref"],
                "resolved_hash": fixture["review_ref"]["hash"],
            },
        }

        result = calculate_prd_ready(request)

        self.assertEqual(result.status, "NOT_READY")
        eval_unmet = next(item for item in result.unmet if item["category"] == "EVALS")
        self.assertEqual(
            eval_unmet["repair_target"], "WAIT_FOR_VERIFIABLE_EVAL_FULFILLMENT"
        )

    def test_recommended_evals_do_not_require_unavailable_fulfillment_authority(self) -> None:
        request = complete_ready_input(
            {"path": "candidate", "hash": "sha256:candidate", "version": "v0.2"}
        )
        request["evals"] = {
            "applicability": "RECOMMENDED",
            "fulfillment": "NOT_STARTED",
            "execution_status": "NOT_RUN",
            "reason": "useful downstream but not a release condition",
        }

        result = calculate_prd_ready(request)

        self.assertEqual(result.status, "READY")

    def test_eval_provenance_exact_refs_require_versions(self) -> None:
        fixture = self._fixture()
        provenance = deepcopy(fixture["evals"]["ground_truth_provenance"])
        provenance["exact_refs"][0].pop("version")

        with self.assertRaisesRegex(EvalsAuthorityError, "version|contract|provenance"):
            _validate_provenance(
                self.project,
                provenance,
                fixture["artifacts"],
                fixture["inputs"],
            )

    def test_eval_provenance_rejects_raw_signal_as_contract_commitment(self) -> None:
        fixture = self._fixture()
        fixture["artifacts"][3]["role"] = "raw_signal"

        with self.assertRaisesRegex(EvalsAuthorityError, "contract|provenance|role"):
            _validate_provenance(
                self.project,
                fixture["evals"]["ground_truth_provenance"],
                fixture["artifacts"],
                fixture["inputs"],
            )

    def test_eval_pack_and_review_exact_refs_require_versions(self) -> None:
        for ref_name in ("pack_ref", "review_ref"):
            with self.subTest(ref_name=ref_name):
                fixture = self._fixture()
                fixture["evals"][ref_name].pop("version")

                with self.assertRaisesRegex(EvalsAuthorityError, "version|exact|role"):
                    self._validate(fixture)

    def test_role_schema_candidate_provenance_independence_and_execution_attacks_fail_closed(self) -> None:
        mutations = {
            "pack-role": lambda value: value["artifacts"][5].update({"role": "prd_candidate"}),
            "pack-origin": lambda value: value["artifacts"][5].update(
                {"origin_node_id": "review.aggregate"}
            ),
            "pack-schema": lambda value: self._rewrite(
                value,
                "pack",
                {**value["pack"], "schema_version": "invented.eval-pack.v9"},
            ),
            "candidate-binding": lambda value: self._rewrite(
                value,
                "pack",
                {
                    **value["pack"],
                    "candidate_ref": {
                        **value["pack"]["candidate_ref"],
                        "version": "v0.1",
                    },
                },
            ),
            "provenance": lambda value: value["evals"].update(
                {"ground_truth_provenance": "invented by optimizer"}
            ),
            "same-reviewer": lambda value: self._rewrite(
                value,
                "review",
                {
                    **value["review"],
                    "reviewer": {"kind": "AGENT", "id": "planner-agent"},
                },
            ),
            "review-origin": lambda value: value["artifacts"][6].update(
                {"origin_node_id": "prd.optimize"}
            ),
            "pack-subject": lambda value: self._rewrite(
                value,
                "review",
                {
                    **value["review"],
                    "subjects": {
                        **value["review"]["subjects"],
                        "eval_pack_ref": value["candidate_ref"],
                    },
                },
            ),
            "open-high": lambda value: self._rewrite(
                value,
                "review",
                {
                    **value["review"],
                    "finding_closure": [{"finding_id": "eval-f-1", "status": "OPEN"}],
                    "new_high_findings": 1,
                },
            ),
            "claimed-execution": lambda value: value["evals"].update(
                {"execution_status": "PASSED"}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                fixture = self._fixture()
                mutate(fixture)
                with self.assertRaises(EvalsAuthorityError):
                    self._validate(fixture)


if __name__ == "__main__":
    unittest.main()
