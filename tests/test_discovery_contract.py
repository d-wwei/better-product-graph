from __future__ import annotations

import unittest

from src.bpg.discovery_contract import (
    validate_assumption_checkpoint,
    validate_evidence_map,
    validate_learning_submission,
    validate_problem_ready,
)


class DiscoveryContractTests(unittest.TestCase):
    def test_sponsor_authority_does_not_upgrade_user_evidence(self) -> None:
        result = validate_evidence_map(
            {
                "claims": [
                    {
                        "id": "claim-1",
                        "role": "AUTHORIZATION",
                        "text": "老板要求做自动回复",
                        "source_ref": "evidence/sponsor-1",
                        "confidence": "VERIFIED_USER_FACT",
                    }
                ]
            }
        )
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("claims[0].confidence", result.repair_targets)
        self.assertEqual(result.generated_artifacts, [])

    def test_assumption_validator_requires_exactly_one_agent_selected_mvu_without_selecting_it(self) -> None:
        checkpoint = {
            "phenomenon": "observed",
            "impact": "material",
            "problem_hypothesis": "hypothesis",
            "desired_outcome": "outcome",
            "proposed_solution": "proposal",
            "credible_alternatives": ["alternative"],
            "no_action_counterfactual": "impact persists",
            "mvus": [],
        }
        result = validate_assumption_checkpoint(checkpoint)
        self.assertEqual(result.status, "NOT_READY")
        self.assertEqual(result.repair_targets, ["agent.exactly_one_selected_mvu"])
        self.assertEqual(result.generated_artifacts, [])
        self.assertNotIn("suggested_value", result.as_dict())

    def test_learning_status_is_separate_from_runtime_and_no_interview_policy_blocks_prompt(self) -> None:
        submission = {
            "learning_disposition": "READY_FOR_SYNTHESIS",
            "runtime_status": "COMPLETED",
            "interaction_policy": "NO_PM_INTERVIEW",
            "next_actions": [{"kind": "PROMPT_PM", "unknown_id": "u-1"}],
            "material_challenges": [],
        }
        result = validate_learning_submission(submission)
        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("interaction_policy.no_pm_prompt", result.repair_targets)
        self.assertNotIn("learning_disposition", result.repair_targets)

    def test_learning_declares_agent_selected_reasoning_resources_without_programmatic_selection(self) -> None:
        submission = {
            "learning_disposition": "READY_FOR_SYNTHESIS",
            "runtime_status": "COMPLETED",
            "interaction_policy": "ALLOW_PM_INTERVIEW",
            "next_actions": [],
            "material_challenges": [],
        }
        missing = validate_learning_submission(submission)
        self.assertEqual(missing.status, "NOT_READY")
        self.assertIn("reasoning_usage.used_resource_ids", missing.repair_targets)

        submission["reasoning_usage"] = {
            "used_resource_ids": ["better-question", "first-principles"],
            "selection_rationale": "The Agent used premise unbinding for the current uncertainty.",
        }
        validated = validate_learning_submission(submission)
        self.assertEqual(validated.status, "READY")
        self.assertEqual(validated.generated_artifacts, [])

    def test_problem_ready_is_mechanical_and_advisory_concern_does_not_veto(self) -> None:
        candidate = {
            "candidate_ref": {"path": "problem-v3.json", "hash": "sha256:current", "version": 3},
            "upstream_refs": [{"path": "map-v2.json", "hash": "sha256:map", "version": 2}],
        }
        review = {
            "candidate_hash": "sha256:current",
            "candidate_version": 3,
            "findings": [{"id": "f-1", "concern": "HIGH"}],
            "dispositions": [{"finding_id": "f-1", "status": "EXTERNAL_REVIEW"}],
        }
        result = validate_problem_ready(
            candidate,
            review,
            current_candidate_hash="sha256:current",
            available_ref_hashes={"problem-v3.json": "sha256:current", "map-v2.json": "sha256:map"},
        )
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.repair_targets, [])

    def test_problem_ready_rejects_stale_candidate_and_missing_disposition(self) -> None:
        result = validate_problem_ready(
            {
                "candidate_ref": {"path": "problem-v2.json", "hash": "sha256:old", "version": 2},
                "upstream_refs": [],
            },
            {
                "candidate_hash": "sha256:old",
                "candidate_version": 2,
                "findings": [{"id": "f-1", "concern": "LOW"}],
                "dispositions": [],
            },
            current_candidate_hash="sha256:new",
            available_ref_hashes={"problem-v2.json": "sha256:old"},
        )
        self.assertEqual(result.status, "NOT_READY")
        self.assertEqual(
            result.repair_targets,
            ["candidate.current_exact_ref", "review.finding_dispositions"],
        )


if __name__ == "__main__":
    unittest.main()
