from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


class AuditRepairVerificationTests(unittest.TestCase):
    def test_every_release_finding_has_executable_public_evidence(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        expected = {
            "REL-H1", "REL-H2", "REL-H3", "REL-H4", "REL-H5", "REL-H6", "REL-H7", "REL-C1",
            "EVAL-C1", "EVAL-C2", "OPT-H1", "C1", "C2", "C3", "C4",
            "H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8",
            "H9", "H10", "H11", "H12", "H13", "H14", "H15",
            "M1", "M2", "M3", "M4",
            "RA-C1", "RA-C2", "RA-H1", "RA-H2", "RA-H3", "RA-H4", "RA-H5", "RA-M1",
            "NEW-C1", "VF-H1", "VF-M1", "VC5-C1", "B1-H1", "B2-H1",
            "ENG-V010-001", "PXR-V010-001", "READY-V019", "READY-H1", "RUN-H1",
        }

        self.assertEqual(set(FINDINGS), expected)
        for finding, evidence in FINDINGS.items():
            self.assertEqual(evidence["disposition"], "FIXED", finding)
            self.assertGreaterEqual(len(evidence["test_ids"]), 1, finding)
            self.assertTrue(evidence["observed_assertion"], finding)
            self.assertTrue(
                all(test.startswith("tests.test_") and ".test_" in test for test in evidence["test_ids"]),
                finding,
            )

    def test_rel_h3_maps_retry_safety_identity_and_crash_recovery_controls(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["REL-H3"]["test_ids"]),
            {
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_host_submit_invalid_artifact_is_zero_write_and_retryable",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_host_submit_preflight_rejects_malformed_artifact_refs_without_run_writes",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_host_submit_invalid_route_is_zero_write_and_retryable",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_problem_synthesize_instruction_explains_hash_retry_boundary",
                "tests.test_crash_recovery.CrashRecoveryTests.test_valid_host_artifact_recovers_after_result_persist_and_transitions",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_rejects_invalid_authority_before_any_side_effect",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_v05_recommended_review_to_handoff_is_reachable",
            },
        )

    def test_run_h1_maps_compatible_upgrade_and_undeclared_drift_controls(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["RUN-H1"]["test_ids"]),
            {
                "tests.test_reaudit_recovery_authority.PublicResumeAuthorityTests.test_compatible_upgrade_keeps_consumed_history_and_current_dispatch_recoverable",
                "tests.test_reaudit_recovery_authority.PublicResumeAuthorityTests.test_undeclared_current_instruction_drift_remains_zero_write_blocked",
                "tests.test_installed_execution_spine.InstalledExecutionSpineTests.test_installed_runner_routes_ordinary_new_request_to_bpg2_without_mutation",
                "tests.test_installed_execution_spine.InstalledExecutionSpineTests.test_installed_host_context_exposes_declared_compatible_successor",
            },
        )

    def test_rel_h4_maps_empty_disagreement_and_full_repair_lifecycle(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["REL-H4"]["test_ids"]),
            {
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_accepts_explicit_empty_disagreements",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_rejects_invalid_disagreement_shape_without_side_effects",
                "tests.test_prd_optimize_runtime.InstalledPRDOptimizeRuntimeTests.test_installed_v06_accepted_repair_rereviews_and_releases_with_no_disagreement",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_required_review_pending_is_honestly_not_ready",
            },
        )

    def test_rel_h5_maps_closed_world_review_aggregate_boundaries(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["REL-H5"]["test_ids"]),
            {
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_rejects_unknown_fields_at_every_nested_boundary",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_accepts_explicit_empty_disagreements",
                "tests.test_prd_optimize_runtime.InstalledPRDOptimizeRuntimeTests.test_installed_v06_accepted_repair_rereviews_and_releases_with_no_disagreement",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_required_review_pending_is_honestly_not_ready",
            },
        )

    def test_rel_h6_maps_empty_finding_cardinality_and_existing_controls(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["REL-H6"]["test_ids"]),
            {
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_accepts_no_findings_without_fabrication",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_rejects_invalid_collection_cardinality_without_writes",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_instruction_is_complete_for_first_submission",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_review_aggregate_rejects_unknown_fields_at_every_nested_boundary",
                "tests.test_prd_optimize_runtime.InstalledPRDOptimizeRuntimeTests.test_installed_v06_accepted_repair_rereviews_and_releases_with_no_disagreement",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_required_review_pending_is_honestly_not_ready",
            },
        )

    def test_rel_h7_maps_formal_problem_ready_outcomes_and_recovery(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["REL-H7"]["test_ids"]),
            {
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_problem_ready_gate_executes_exact_validator_and_advances",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_problem_ready_not_ready_is_durable_auditable_and_idempotent",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_problem_ready_instruction_exposes_both_formal_outcomes",
                "tests.test_problem_ready_gate.ProblemReadyGateContractTests.test_problem_ready_mechanical_output_is_closed_world_and_status_exact",
                "tests.test_problem_ready_gate.ProblemReadyGateContractTests.test_problem_ready_after_result_crash_recovers_once_and_advances",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_problem_review_instruction_contract_succeeds_on_first_submission",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_problem_review_missing_field_is_rejected_before_state_progress",
            },
        )

    def test_vc5_c1_maps_every_full_state_attack_and_exact_recovery_control(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["VC5-C1"]["test_ids"]),
            {
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_full_state_commitment_rejects_schema_valid_field_mutations",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_full_state_commitment_rejects_mutated_wait_condition_before_trigger",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_unbound_hash_correct_artifact_is_rejected_by_public_operations",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_public_authority_barrier_preserves_normal_operations",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_wait_consumes_one_exact_typed_new_evidence_trigger",
                "tests.test_crash_recovery.CrashRecoveryTests.test_after_transition_event_recovers_exact_journal_snapshot_idempotently",
                "tests.test_candidate_finalize_recovery.CandidateFinalizeRecoveryTests.test_candidate_finalize_recovers_every_staged_event_state_publish_boundary",
                "tests.test_reviews_ready.ReviewsReadyTests.test_release_crash_after_state_commit_leaves_no_orphan_and_recovers_publish",
            },
        )

    def test_eval_c1_maps_both_public_bypasses_and_structured_controls(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["EVAL-C1"]["test_ids"]),
            {
                "tests.test_prd_optimize_runtime.InstalledPRDOptimizeRuntimeTests.test_installed_optimize_rejects_dispatched_prd_and_aggregate_masquerading_as_reviewed_evals",
                "tests.test_prd_optimize_runtime.InstalledPRDOptimizeRuntimeTests.test_installed_optimize_keeps_required_evals_pending_for_future_independent_review",
                "tests.test_prd_optimize_runtime.InstalledPRDOptimizeRuntimeTests.test_installed_optimize_cannot_downgrade_required_evals_applicability",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_ready_rejects_wrong_role_artifacts_and_invented_reviewed_evals_before_release",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_controller_derives_typed_eval_origins_instead_of_trusting_artifact_claims",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_trial_and_v1_schema_pairs_validate_specification_consistency_only",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_role_schema_candidate_provenance_independence_and_execution_attacks_fail_closed",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_required_review_pending_is_honestly_not_ready",
            },
        )

    def test_eval_c2_maps_self_attestation_fail_closed_and_positive_controls(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["EVAL-C2"]["test_ids"]),
            {
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_bpg2_rejects_unbound_future_evals_metadata_before_ready",
                "tests.test_prd_contract.PRDContractTests.test_prd_generate_does_not_require_or_emit_evals_applicability",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_required_reviewed_is_not_ready_without_verifiable_fulfillment_authority",
                "tests.test_reviews_ready.ReviewsReadyTests.test_required_evals_cannot_reach_full_release_without_verifiable_fulfillment_authority",
                "tests.test_installed_reaudit_bypasses.InstalledPublicReauditTests.test_installed_recommended_evals_can_complete_without_fulfillment_authority",
                "tests.test_prd_optimize_runtime.InstalledPRDOptimizeRuntimeTests.test_installed_optimize_keeps_required_evals_pending_for_future_independent_review",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_eval_provenance_exact_refs_require_versions",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_eval_provenance_rejects_raw_signal_as_contract_commitment",
                "tests.test_evals_authority.ReviewedEvalsAuthorityTests.test_eval_pack_and_review_exact_refs_require_versions",
            },
        )

    def test_b1_h1_maps_all_four_public_recovery_composition_attacks(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["B1-H1"]["test_ids"]),
            {
                "tests.test_reaudit_recovery_authority.PublicResumeAuthorityTests.test_public_operations_do_not_recover_result_while_state_commitment_is_tampered",
            },
        )

    def test_b2_h1_maps_all_four_early_staged_publish_input_attacks(self) -> None:
        from scripts.verify_audit_repairs import FINDINGS

        self.assertEqual(
            set(FINDINGS["B2-H1"]["test_ids"]),
            {
                "tests.test_candidate_finalize_recovery.CandidateFinalizeRecoveryTests.test_candidate_finalize_early_recovery_rejects_tampered_publish_inputs_without_side_effects",
                "tests.test_reviews_ready.ReviewsReadyTests.test_release_early_recovery_rejects_tampered_publish_inputs_without_side_effects",
            },
        )

    def test_structured_runner_fails_name_only_skip_and_missing_test_evidence(self) -> None:
        from scripts.verify_audit_repairs import run_test_ids

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "test_false_green_fixture.py").write_text(
                """
import unittest

class FalseGreenFixtures(unittest.TestCase):
    def test_prints_required_name_but_fails(self):
        print('test_required_counterexample')
        self.fail('counterexample still succeeds')

    @unittest.skip('not executed')
    def test_skipped_counterexample(self):
        self.fail('unreachable')

    def test_real_assertion(self):
        self.assertEqual(2 + 2, 4)
""".lstrip(),
                encoding="utf-8",
            )
            printed = run_test_ids(
                root,
                ["test_false_green_fixture.FalseGreenFixtures.test_prints_required_name_but_fails"],
            )
            skipped = run_test_ids(
                root,
                ["test_false_green_fixture.FalseGreenFixtures.test_skipped_counterexample"],
            )
            missing = run_test_ids(
                root,
                ["test_false_green_fixture.FalseGreenFixtures.test_missing_counterexample"],
            )
            passed = run_test_ids(
                root,
                ["test_false_green_fixture.FalseGreenFixtures.test_real_assertion"],
            )

        self.assertEqual(printed["status"], "FAIL")
        self.assertTrue(printed["failures"])
        self.assertEqual(skipped["status"], "FAIL")
        self.assertTrue(skipped["skipped"])
        self.assertEqual(missing["status"], "FAIL")
        self.assertTrue(missing["errors"])
        self.assertEqual(passed["status"], "PASS")
        self.assertEqual(passed["successful_test_ids"], passed["requested_test_ids"])


if __name__ == "__main__":
    unittest.main()
