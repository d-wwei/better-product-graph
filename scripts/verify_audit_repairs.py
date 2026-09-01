#!/usr/bin/env python3
"""Run exact per-finding tests and emit structured observed evidence.

A finding passes only when every declared unittest ID is loaded, executed, not
skipped, and reported successful by unittest's result object. Console text and
a separate full-suite exit code are never used as finding evidence.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


def _id(module: str, case: str, method: str) -> str:
    return f"tests.{module}.{case}.{method}"


def _finding(assertion: str, *test_ids: str) -> dict[str, Any]:
    return {"disposition": "FIXED", "observed_assertion": assertion, "test_ids": list(test_ids)}


FINDINGS: dict[str, dict[str, Any]] = {
    "READY-H1": _finding(
        "Ready accepts an explicit empty EvidenceRecord list while retaining exact Decision, Roadmap, Product Plan, Slice, and Knowledge authority; present EvidenceRecords remain exact-bound and validated.",
        _id("test_reviews_ready", "ReviewsReadyTests", "test_ready_accepts_no_separate_evidence_record_when_other_upstreams_are_exact"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_ready_still_requires_at_least_one_decision_record"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_mechanical_receipt_binds_every_decision_and_evidence_ref"),
    ),
    "RUN-H1": _finding(
        "A compatible installed successor resumes a durable unfinished dispatch without rejudging consumed history, exposes both instruction identities to the Host, and keeps undeclared drift zero-write blocked.",
        _id("test_reaudit_recovery_authority", "PublicResumeAuthorityTests", "test_compatible_upgrade_keeps_consumed_history_and_current_dispatch_recoverable"),
        _id("test_reaudit_recovery_authority", "PublicResumeAuthorityTests", "test_undeclared_current_instruction_drift_remains_zero_write_blocked"),
        _id("test_installed_execution_spine", "InstalledExecutionSpineTests", "test_installed_runner_routes_ordinary_new_request_to_bpg2_without_mutation"),
        _id("test_installed_execution_spine", "InstalledExecutionSpineTests", "test_installed_host_context_exposes_declared_compatible_successor"),
    ),
    "ENG-V010-001": _finding(
        "The Candidate delivery contract is closed-world: only portable project workspace and product signal are Runtime-required, committed specification provenance remains traceability-only, nested or aliased lifecycle leakage fails closed, and only complete typed portable BPG dependencies are exempted.",
        _id("test_delivery_contract", "DeliveryContractTests", "test_fresh_project_runtime_readiness_needs_only_workspace_and_signal"),
        _id("test_delivery_contract", "DeliveryContractTests", "test_nested_spec_value_leak_is_rejected_even_under_a_forged_role"),
        _id("test_delivery_contract", "DeliveryContractTests", "test_complete_typed_bpg_exception_is_allowed_but_current_run_path_is_not"),
        _id("test_prd_contract", "PRDContractTests", "test_runtime_required_inputs_cannot_be_empty_or_leak_spec_provenance"),
        _id("test_prd_contract", "PRDContractTests", "test_runtime_contract_freezes_the_two_portable_minimum_inputs"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_rejects_nested_spec_ref_in_runtime_inputs_before_write"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_rejects_laundered_source_candidate_hash_before_write"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_rejects_committed_receipt_hash_alias_before_write"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_material_scope_route_rejects_runtime_leak_before_controller_write"),
    ),
    "PXR-V010-001": _finding(
        "Product Plans bind a stable planned PRD and canonical active Slice scope, same-scope Optimize preserves the Plan and creates an exact superseding Candidate, caller-forged scope claims are ignored, and material or ambiguous scope changes stop before any authoritative Candidate write.",
        _id("test_planning_contract", "PlanningContractTests", "test_plan_matrix_requires_stable_prd_id_and_forbids_candidate_version_pin"),
        _id("test_planning_contract", "PlanningContractTests", "test_candidate_version_pins_anywhere_in_plan_are_not_ready"),
        _id("test_delivery_contract", "DeliveryContractTests", "test_controller_derives_stable_scope_and_ignores_module_dependency_order"),
        _id("test_delivery_contract", "DeliveryContractTests", "test_every_authoritative_scope_field_changes_the_scope_hash"),
        _id("test_prd_contract", "PRDContractTests", "test_active_scope_ref_cannot_pin_candidate_version"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_archives_agent_vnext_and_rebinds_rereview"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_recomputes_scope_and_rejects_forged_hash_without_side_effects"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_routes_material_scope_change_before_candidate_write"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_reconciled_plan_regenerates_exact_vnext_and_clears_route"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_reconciled_plan_rejects_current_candidate_aliases_before_write"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_plan_gate_rejects_non_decision_authority"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_treats_unmapped_scope_fields_as_ambiguous"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_agent_instructions_expose_lifecycle_trace_roles"),
    ),
    "READY-V019": _finding(
        "Ready validates exact Controller-bound Graph-native Node Results and the Slice-bound Markdown Product Plan by role; legacy Host-crafted kind/version JSON, swapped node roles, and unbound Plans remain NOT_READY.",
        _id("test_reviews_ready", "ReviewsReadyTests", "test_mechanical_receipt_accepts_graph_native_upstreams_and_markdown_plan"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_mechanical_receipt_rejects_legacy_fake_kind_version_upstreams"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_mechanical_receipt_rejects_wrong_slice_node_role"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_mechanical_receipt_rejects_markdown_plan_not_bound_by_slice"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_v05_recommended_review_to_handoff_is_reachable"),
    ),
    "REL-H7": _finding(
        "Installed problem.ready.gate persists only closed-world READY or auditable NOT_READY calculations, never advances NOT_READY into Product Decision, exposes exact result/receipt refs, and recovers a result-first crash idempotently.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_ready_gate_executes_exact_validator_and_advances"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_ready_not_ready_is_durable_auditable_and_idempotent"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_ready_instruction_exposes_both_formal_outcomes"),
        _id("test_problem_ready_gate", "ProblemReadyGateContractTests", "test_problem_ready_mechanical_output_is_closed_world_and_status_exact"),
        _id("test_problem_ready_gate", "ProblemReadyGateContractTests", "test_problem_ready_after_result_crash_recovers_once_and_advances"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_review_instruction_contract_succeeds_on_first_submission"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_review_missing_field_is_rejected_before_state_progress"),
    ),
    "REL-H6": _finding(
        "Installed review.aggregate accepts an exact no-Finding outcome without fabrication, enforces the full collection cardinality matrix before Run writes, and preserves closed-world, Optimize, and REQUIRED-Evals controls.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_accepts_no_findings_without_fabrication"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_rejects_invalid_collection_cardinality_without_writes"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_instruction_is_complete_for_first_submission"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_rejects_unknown_fields_at_every_nested_boundary"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_v06_accepted_repair_rereviews_and_releases_with_no_disagreement"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_required_review_pending_is_honestly_not_ready"),
    ),
    "REL-H5": _finding(
        "Installed review.aggregate enforces a closed-world contract at every semantic, artifact, and artifact-ref mapping; unknown fields identify their exact path and leave the whole Run inventory unchanged while valid empty-disagreement and v0.6 repair lifecycles remain reachable.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_rejects_unknown_fields_at_every_nested_boundary"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_accepts_explicit_empty_disagreements"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_v06_accepted_repair_rereviews_and_releases_with_no_disagreement"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_required_review_pending_is_honestly_not_ready"),
    ),
    "REL-H4": _finding(
        "Installed review.aggregate accepts an explicit empty disagreement list, rejects missing, mistyped, or incomplete disagreement data before Run writes, and completes an accepted-repair v0.6 Optimize-to-Handoff lifecycle.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_accepts_explicit_empty_disagreements"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_rejects_invalid_disagreement_shape_without_side_effects"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_v06_accepted_repair_rereviews_and_releases_with_no_disagreement"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_required_review_pending_is_honestly_not_ready"),
    ),
    "REL-H3": _finding(
        "Installed Host submit validates exact artifacts and routes before publication, permits a corrected same-attempt retry without Run writes, preserves attempt identity after success, and retains valid artifact crash recovery plus Review-to-Handoff reachability.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_host_submit_invalid_artifact_is_zero_write_and_retryable"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_host_submit_preflight_rejects_malformed_artifact_refs_without_run_writes"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_host_submit_invalid_route_is_zero_write_and_retryable"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_synthesize_instruction_explains_hash_retry_boundary"),
        _id("test_crash_recovery", "CrashRecoveryTests", "test_valid_host_artifact_recovers_after_result_persist_and_transitions"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_rejects_invalid_authority_before_any_side_effect"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_v05_recommended_review_to_handoff_is_reachable"),
    ),
    "REL-H2": _finding(
        "Installed review.aggregate exposes the complete two-artifact contract, rejects incomplete or forged authority and unreachable Optimize routes before side effects, and completes the exact v0.5 RECOMMENDED Review-to-Handoff path.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_instruction_is_complete_for_first_submission"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_rejects_invalid_authority_before_any_side_effect"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_review_aggregate_rejects_unreachable_optimize_route_before_side_effects"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_v05_recommended_review_to_handoff_is_reachable"),
    ),
    "REL-H1": _finding(
        "Installed Problem Quality Review instruction exposes the complete validator contract; an instruction-derived result passes once, while a missing exact field fails before persistence with a repairable message.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_review_instruction_contract_succeeds_on_first_submission"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_problem_review_missing_field_is_rejected_before_state_progress"),
    ),
    "REL-C1": _finding(
        "Controller canonical Ready roles override but retain Candidate-declared metadata roles; v0.4 RECOMMENDED Evals release and handoff completes, while duplicate or missing upstream facts fail without Candidate side effects.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_v04_metadata_roles_are_non_authoritative_and_release_handoff_completes"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_duplicate_or_missing_upstream_fact_fails_before_candidate_side_effects"),
        _id("test_controller_receipt_authority", "ControllerReceiptAuthorityTests", "test_controller_refuses_duplicate_exact_subject_refs_without_side_effects"),
    ),
    "EVAL-C1": _finding(
        "Installed Optimize rejects fabricated REVIEWED Eval artifacts; allowlisted Pack/Review schemas validate exact Candidate, Ground Truth, and NOT_RUN specification consistency without granting release authority.",
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_rejects_dispatched_prd_and_aggregate_masquerading_as_reviewed_evals"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_keeps_required_evals_pending_for_future_independent_review"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_cannot_downgrade_required_evals_applicability"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_ready_rejects_wrong_role_artifacts_and_invented_reviewed_evals_before_release"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_controller_derives_typed_eval_origins_instead_of_trusting_artifact_claims"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_trial_and_v1_schema_pairs_validate_specification_consistency_only"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_role_schema_candidate_provenance_independence_and_execution_attacks_fail_closed"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_required_review_pending_is_honestly_not_ready"),
    ),
    "EVAL-C2": _finding(
        "BPG 2.0 rejects unbound future Product Evals metadata before Ready; dormant typed Pack/Review validation remains specification-only.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_bpg2_rejects_unbound_future_evals_metadata_before_ready"),
        _id("test_prd_contract", "PRDContractTests", "test_prd_generate_does_not_require_or_emit_evals_applicability"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_required_reviewed_is_not_ready_without_verifiable_fulfillment_authority"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_required_evals_cannot_reach_full_release_without_verifiable_fulfillment_authority"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_recommended_evals_can_complete_without_fulfillment_authority"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_keeps_required_evals_pending_for_future_independent_review"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_eval_provenance_exact_refs_require_versions"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_eval_provenance_rejects_raw_signal_as_contract_commitment"),
        _id("test_evals_authority", "ReviewedEvalsAuthorityTests", "test_eval_pack_and_review_exact_refs_require_versions"),
    ),
    "OPT-H1": _finding(
        "Installed PRD Optimize archives exact Agent-authored vNext, rejects stale/conflicting repairs without side effects, and recovers idempotently.",
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_archives_agent_vnext_and_rebinds_rereview"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_installed_optimize_rejects_stale_version_unclosed_and_metadata_tamper_without_side_effects"),
        _id("test_prd_optimize_runtime", "InstalledPRDOptimizeRuntimeTests", "test_optimize_recovers_exactly_once_across_archive_result_and_transition_crashes"),
    ),
    "C1": _finding(
        "Installed dispatch/submit progresses real nodes and keeps Owner choice separate.",
        _id("test_installed_execution_spine", "InstalledExecutionSpineTests", "test_installed_submit_progresses_multiple_nodes_and_executes_route_select"),
        _id("test_installed_execution_spine", "InstalledExecutionSpineTests", "test_installed_decision_submit_then_owner_choice_routes_independent_authority"),
    ),
    "C2": _finding(
        "Future schemas, empty results, and false instruction/input hashes fail before receipt.",
        _id("test_public_controller_enforcement", "PublicControllerEnforcementTests", "test_future_schema_and_empty_semantic_output_fail_before_result_receipt"),
        _id("test_public_controller_enforcement", "PublicControllerEnforcementTests", "test_fake_instruction_or_input_hash_fails_before_result_receipt"),
    ),
    "C3": _finding(
        "Ready receipts require Controller directory, ledger/state authority, and Candidate version.",
        _id("test_controller_receipt_authority", "ControllerReceiptAuthorityTests", "test_handwritten_receipt_outside_controller_owned_directory_is_rejected"),
        _id("test_controller_receipt_authority", "ControllerReceiptAuthorityTests", "test_copied_receipt_not_in_controller_ledger_or_state_is_rejected"),
        _id("test_controller_receipt_authority", "ControllerReceiptAuthorityTests", "test_candidate_v1_receipts_cannot_release_candidate_v2"),
    ),
    "C4": _finding(
        "Agent Decision payload cannot self-authorize and Owner choices create typed routes.",
        _id("test_owner_choice_routes", "OwnerChoiceRouteTests", "test_agent_decision_draft_cannot_self_authorize_owner_choice"),
        _id("test_owner_choice_routes", "OwnerChoiceRouteTests", "test_all_six_choice_variants_create_distinct_durable_routes"),
    ),
    "H1": _finding(
        "CAS, event append, and cross-process mutation serialize Run writers.",
        _id("test_controller_concurrency", "ControllerConcurrencyTests", "test_concurrent_cas_allows_only_one_writer_for_same_version"),
        _id("test_controller_concurrency", "ControllerConcurrencyTests", "test_event_append_obeys_lock_and_concurrent_chain_remains_valid"),
        _id("test_controller_concurrency", "ControllerConcurrencyTests", "test_run_mutation_obeys_cross_process_advisory_lock"),
    ),
    "H2": _finding(
        "Result, release, and Candidate-finalize crash boundaries recover idempotently and validate staged/archive inputs before publish moves.",
        _id("test_crash_recovery", "CrashRecoveryTests", "test_after_result_persist_recovers_receipt_and_event_idempotently"),
        _id("test_prd_release", "PRDReleaseTests", "test_archive_and_release_recover_publish_before_changelog_without_duplicate_entries"),
        _id("test_candidate_finalize_recovery", "CandidateFinalizeRecoveryTests", "test_candidate_finalize_recovers_every_staged_event_state_publish_boundary"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_release_recovers_every_staged_event_state_publish_boundary"),
        _id("test_candidate_finalize_recovery", "CandidateFinalizeRecoveryTests", "test_candidate_finalize_recovery_validates_stage_before_moving_current_candidate"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_release_recovery_validates_archive_before_publishing_staged_release"),
    ),
    "H3": _finding(
        "Resume revalidates graph, Candidate, fanout, dispatch, results, and unknown effects.",
        _id("test_resume", "ResumeTests", "test_resume_revalidates_graph_candidate_fanout_dispatch_and_unknown_side_effect"),
    ),
    "H4": _finding(
        "Fanout cannot join PENDING attempts or replace persisted findings.",
        _id("test_fanout", "FanoutTests", "test_pending_attempt_cannot_be_joined_before_dispatch_and_result_persistence"),
        _id("test_fanout", "FanoutTests", "test_join_uses_exact_persisted_worker_result_not_caller_replacement"),
    ),
    "H5": _finding(
        "Intake preserves each occurrence and repeated new creates distinct Runs.",
        _id("test_signal_occurrences", "SignalOccurrenceTests", "test_every_new_and_capture_appends_occurrence_before_content_dedup"),
        _id("test_installed_execution_spine", "InstalledExecutionSpineTests", "test_installed_repeated_new_same_content_creates_distinct_occurrence_bound_runs"),
    ),
    "H6": _finding(
        "Every state-changing entry runs Git preflight.",
        _id("test_signal_occurrences", "SignalOccurrenceTests", "test_state_changing_entry_automatically_runs_git_preflight"),
    ),
    "H7": _finding(
        "Handoff rejects forged lifecycle and accepts exact Released Ready artifacts.",
        _id("test_intents", "HostEngineSafetyTests", "test_forged_released_state_without_exact_artifact_set_cannot_handoff"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_ready_atomically_creates_immutable_release_and_local_handoff_never_claims_sent"),
    ),
    "H8": _finding(
        "Installed self-check recomputes identity and rejects byte tamper.",
        _id("test_installed_execution_spine", "InstalledExecutionSpineTests", "test_installed_self_check_recomputes_inventory_and_fails_after_tamper"),
    ),
    "H9": _finding(
        "Better Question/router and twenty cognitive bases retain exact provenance.",
        _id("test_internal_reference_catalog", "InternalReferenceCatalogTests", "test_source_catalog_has_better_question_router_and_exactly_twenty_non_discoverable_bases"),
        _id("test_internal_reference_catalog", "InternalReferenceCatalogTests", "test_source_extraction_manifest_rehashes_all_twenty_declared_cognitive_bases"),
    ),
    "H10": _finding(
        "Review binds Goal Fidelity profile, rubric, packet, and commitments.",
        _id("test_review_contract", "ReviewContractTests", "test_review_requires_exact_goal_profile_rubric_packet_and_commitment_refs"),
    ),
    "H11": _finding(
        "Decision evolution, projections, and changelog are append-only.",
        _id("test_product_memory", "ProductMemoryTests", "test_decisions_evolve_append_only_with_current_plan_roadmap_and_changelog"),
    ),
    "H12": _finding(
        "PRD stem, companion/assets, and changelog bind one version.",
        _id("test_prd_lifecycle_contract", "PRDLifecycleContractTests", "test_exact_stem_self_contained_companion_and_structured_changelog"),
    ),
    "H13": _finding(
        "Packages are byte-identical and isolated install rollback succeeds.",
        _id("test_packaging", "PackagingTests", "test_two_packages_are_byte_identical_and_have_canonical_plugin_root"),
        _id("test_fresh_install", "FreshInstallTests", "test_isolated_codex_home_install_contract_uninstall_and_rollback"),
    ),
    "H14": _finding(
        "Managed Run parents reject symlink escape before mutation.",
        _id("test_resume", "ResumeTests", "test_managed_run_parent_symlink_is_rejected_before_write"),
    ),
    "H15": _finding(
        "Result receipts rehash before consume and committed outputs become inputs.",
        _id("test_public_controller_enforcement", "PublicControllerEnforcementTests", "test_result_receipt_is_rehashed_immediately_before_transition"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_next_dispatch_binds_committed_result_and_declared_artifact"),
    ),
    "M1": _finding(
        "Eleven explicit/natural intents and interaction modifiers retain parity.",
        _id("test_intents", "IntentParserTests", "test_all_eleven_explicit_and_natural_entries_have_core_intent_parity"),
        _id("test_intents", "IntentParserTests", "test_new_and_resume_accept_no_pm_interview_without_polluting_signal_or_run_id"),
    ),
    "M2": _finding(
        "Caller Gate claims and receipt role gaps cannot promote state.",
        _id("test_state_controller", "StateControllerTests", "test_agent_claimed_gate_fields_are_rejected_without_state_change"),
        _id("test_controller_receipt_authority", "ControllerReceiptAuthorityTests", "test_controller_refuses_right_kind_with_wrong_or_missing_subject_roles"),
    ),
    "M3": _finding(
        "Required installed references fail closed when missing.",
        _id("test_plugin_contract_suite", "PluginContractSuiteTests", "test_missing_internal_reference_fails_relative_resource_contract"),
        _id("test_internal_reference_catalog", "InternalReferenceCatalogTests", "test_installed_catalog_fails_closed_when_one_reference_is_missing"),
    ),
    "M4": _finding(
        "Golden fixtures remain distinct from NOT_RUN Agent judgment.",
        _id("test_product_golden_suite", "ProductGoldenSuiteTests", "test_contract_fixtures_pass_but_product_judgment_remains_not_run"),
        _id("test_product_golden_suite", "ProductGoldenSuiteTests", "test_runner_never_accepts_a_fixture_only_product_pass_claim"),
    ),
    "RA-C1": _finding(
        "Installed submit cannot impersonate Gates; invalid PRD and unbound outputs fail.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_public_submit_cannot_claim_controller_identity_at_mechanical_nodes"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_invalid_agent_prd_cannot_advance_into_review"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_next_dispatch_binds_committed_result_and_declared_artifact"),
    ),
    "RA-C2": _finding(
        "FAIL subjects, unrelated Runs, and unauthorized upstreams cannot release.",
        _id("test_installed_reaudit_bypasses", "ReceiptAndReleaseReauditTests", "test_explicit_fail_audit_subject_cannot_receive_pass_receipt"),
        _id("test_installed_reaudit_bypasses", "ReceiptAndReleaseReauditTests", "test_explicit_fail_mechanical_subject_cannot_receive_pass_receipt"),
        _id("test_installed_reaudit_bypasses", "ReceiptAndReleaseReauditTests", "test_receipts_from_unrelated_signal_ingest_run_cannot_release_candidate"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_false_ready_rejects_unrelated_fail_decision"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_false_ready_rejects_unrelated_unauthorized_evidence"),
    ),
    "RA-H1": _finding(
        "WAIT, snapshot tamper, and transition crash resume paths fail closed or recover.",
        _id("test_reaudit_recovery_authority", "PublicResumeAuthorityTests", "test_waiting_trigger_cannot_be_escaped_by_plain_public_resume"),
        _id("test_reaudit_recovery_authority", "PublicResumeAuthorityTests", "test_schema_valid_snapshot_position_tamper_blocks_public_resume"),
        _id("test_reaudit_recovery_authority", "PublicResumeAuthorityTests", "test_public_resume_recovers_a_committed_transition_before_reporting_state"),
    ),
    "RA-H2": _finding(
        "A pre-pause dispatch cannot submit after lifecycle mutation.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_dispatch_started_before_pause_cannot_be_submitted_after_pause"),
    ),
    "RA-H3": _finding(
        "Fanout join consumes persisted result, not caller replacement.",
        _id("test_fanout", "FanoutTests", "test_join_uses_exact_persisted_worker_result_not_caller_replacement"),
    ),
    "RA-H4": _finding(
        "Audit append/replay execute schema and recorded_at validation.",
        _id("test_reaudit_recovery_authority", "AuditEventAuthorityTests", "test_schema_invalid_event_is_rejected_on_append_and_replay"),
        _id("test_reaudit_recovery_authority", "AuditEventAuthorityTests", "test_recorded_at_requires_strict_iso_string_on_append_and_replay"),
    ),
    "RA-H5": _finding(
        "Exact Released Run reaches one terminal without Host terminal result.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_exact_released_run_completes_terminal_without_host_result_submission"),
    ),
    "RA-M1": _finding(
        "Verifier rejects name-only, skipped, and absent evidence.",
        _id("test_audit_repair_verification", "AuditRepairVerificationTests", "test_structured_runner_fails_name_only_skip_and_missing_test_evidence"),
    ),
    "NEW-C1": _finding(
        "All public operations reject schema-valid snapshot tamper.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_public_operations_reject_schema_valid_snapshot_authority_tamper"),
    ),
    "VF-H1": _finding(
        "Installed resume consumes one exact typed trigger and rejects replay.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_wait_consumes_one_exact_typed_new_evidence_trigger"),
    ),
    "VF-M1": _finding(
        "Audit recorded_at rejects wrong type/format on append and replay.",
        _id("test_reaudit_recovery_authority", "AuditEventAuthorityTests", "test_recorded_at_requires_strict_iso_string_on_append_and_replay"),
    ),
    "VC5-C1": _finding(
        "Installed public operations reject complete-state tamper for WAIT, policy, Candidate/Decision, unbound artifacts, and unknown future fields; exact WAL recovery and normal paths remain valid.",
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_full_state_commitment_rejects_schema_valid_field_mutations"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_full_state_commitment_rejects_mutated_wait_condition_before_trigger"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_unbound_hash_correct_artifact_is_rejected_by_public_operations"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_public_authority_barrier_preserves_normal_operations"),
        _id("test_installed_reaudit_bypasses", "InstalledPublicReauditTests", "test_installed_wait_consumes_one_exact_typed_new_evidence_trigger"),
        _id("test_crash_recovery", "CrashRecoveryTests", "test_after_transition_event_recovers_exact_journal_snapshot_idempotently"),
        _id("test_candidate_finalize_recovery", "CandidateFinalizeRecoveryTests", "test_candidate_finalize_recovers_every_staged_event_state_publish_boundary"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_release_crash_after_state_commit_leaves_no_orphan_and_recovers_publish"),
    ),
    "B1-H1": _finding(
        "Status, dispatch, typed trigger, and resume reject complete-state tamper before recovering an incomplete result or writing any receipt/event.",
        _id("test_reaudit_recovery_authority", "PublicResumeAuthorityTests", "test_public_operations_do_not_recover_result_while_state_commitment_is_tampered"),
    ),
    "B2-H1": _finding(
        "Early-staged Candidate and Release recovery validates every publish input before committing its event/state, so stage/history/archive tamper is rejected without side effects.",
        _id("test_candidate_finalize_recovery", "CandidateFinalizeRecoveryTests", "test_candidate_finalize_early_recovery_rejects_tampered_publish_inputs_without_side_effects"),
        _id("test_reviews_ready", "ReviewsReadyTests", "test_release_early_recovery_rejects_tampered_publish_inputs_without_side_effects"),
    ),
}


class RecordingResult(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.successful_test_ids: list[str] = []

    def addSuccess(self, test: unittest.case.TestCase) -> None:  # noqa: N802
        super().addSuccess(test)
        self.successful_test_ids.append(test.id())


def _failure_rows(items: list[tuple[unittest.case.TestCase, str]]) -> list[dict[str, str]]:
    return [
        {"test_id": test.id(), "detail": detail.splitlines()[-1] if detail else "unknown"}
        for test, detail in items
    ]


def run_test_ids(repo_root: Path, test_ids: list[str]) -> dict[str, Any]:
    """Execute exact unittest IDs; test output is captured and never used as proof."""

    root = repo_root.resolve()
    requested = list(test_ids)
    original_path = list(sys.path)
    output = io.StringIO()
    try:
        sys.path.insert(0, str(root))
        if (root / "tests").is_dir():
            sys.path.insert(0, str(root / "tests"))
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            suite = unittest.defaultTestLoader.loadTestsFromNames(requested)
            result = RecordingResult()
            suite.run(result)
    finally:
        sys.path[:] = original_path
    failures = _failure_rows(result.failures)
    errors = _failure_rows(result.errors)
    skipped = [{"test_id": test.id(), "reason": reason} for test, reason in result.skipped]
    unexpected = [test.id() for test in result.unexpectedSuccesses]
    passed = (
        result.testsRun == len(requested)
        and sorted(result.successful_test_ids) == sorted(requested)
        and not failures
        and not errors
        and not skipped
        and not unexpected
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "requested_test_ids": requested,
        "tests_run": result.testsRun,
        "successful_test_ids": result.successful_test_ids,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "unexpected_successes": unexpected,
        "captured_output": output.getvalue()[-2000:],
    }


def _execute_finding(root: Path, finding: str, contract: dict[str, Any]) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--repo",
        str(root),
        "--child-test-ids",
        *contract["test_ids"],
    ]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command, cwd=root, env=environment, text=True, capture_output=True,
        check=False, timeout=300,
    )
    try:
        observation = json.loads(completed.stdout)
    except json.JSONDecodeError:
        observation = {
            "status": "FAIL", "requested_test_ids": contract["test_ids"], "tests_run": 0,
            "successful_test_ids": [], "failures": [],
            "errors": [{"test_id": finding, "detail": "child emitted non-JSON output"}],
            "skipped": [], "unexpected_successes": [],
            "captured_output": (completed.stdout + completed.stderr)[-2000:],
        }
    passed = completed.returncode == 0 and observation.get("status") == "PASS"
    return {
        "finding": finding,
        "candidate_disposition": contract["disposition"],
        "status": "PASS" if passed else "FAIL",
        "observed_assertion": contract["observed_assertion"],
        "command": command,
        "observation": observation,
        "child_returncode": completed.returncode,
        "child_stderr": completed.stderr[-2000:],
    }


def verify(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    results = [_execute_finding(root, finding, contract) for finding, contract in FINDINGS.items()]
    failed = [item["finding"] for item in results if item["status"] != "PASS"]
    return {
        "verification": "better-product-graph-per-finding-pre-release-repair-v2",
        "status": "PASS" if not failed else "FAIL",
        "historical_audit": {
            "initial_commit": "8d7dac9154fb8b0ea1b51b89c955a1c0af6b79e4",
            "reaudit_candidate_commit": "126a90f7f001f52522fc88739bba45da453cac6f",
            "reaudit_material_commit": "519bfeb7286fcabd3cee0b8aad4b9fd7e43b3101",
            "status": "REJECT_IMMUTABLE",
        },
        "findings": results,
        "failed": failed,
        "evidence_boundary": {
            "candidate_owned_contract_and_installed_counterexamples": "PASS" if not failed else "FAIL",
            "independent_reaudit_of_current_commit": "NOT_RUN",
            "authenticated_host_agent": "NOT_RUN",
            "product_golden_agent_judgment": "NOT_RUN",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--child-test-ids", nargs="+")
    args = parser.parse_args()
    if args.child_test_ids:
        observation = run_test_ids(args.repo, args.child_test_ids)
        print(json.dumps(observation, ensure_ascii=False, sort_keys=True))
        return 0 if observation["status"] == "PASS" else 1
    report = verify(args.repo)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
