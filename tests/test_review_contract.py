from __future__ import annotations

import unittest

from src.bpg.review_contract import (
    ReviewContractError,
    aggregate_reviews,
    finalize_review,
    next_review_action,
    validate_aggregate_disagreements,
    validate_review_submission,
)


CANDIDATE = {"path": "prd-v0.1.md", "hash": "sha256:prd", "version": "v0.1"}


def review_submission(role: str, finding_id: str, stance: str) -> dict:
    return {
        "node_id": "review.parallel",
        "attempt_id": f"review-{role}",
        "producer": {"kind": "HOST_AGENT", "host": "codex"},
        "instruction_ref": "references/atomic-skills/prd-review/INSTRUCTIONS.md",
        "instruction_hash": "sha256:review-instructions",
        "input_refs": ["prd-v0.1.md"],
        "input_hashes": {"prd-v0.1.md": "sha256:prd"},
        "semantic_output": {
            "candidate_ref": CANDIDATE,
            "reviewer_role": role,
            "reviewer_profile": role,
            "roles_covered": [role],
            "authority": "ADVISORY_ONLY",
            "goal_fidelity_refs": {
                "profile_ref": {"path": "references/reviewer-profiles/product-goal-fidelity-v0.1.json", "hash": "sha256:profile", "version": "v0.1"},
                "rubric_ref": {"path": "references/reviewer-profiles/product-goal-fidelity-rubric-v0.1.json", "hash": "sha256:rubric", "version": "v0.1"},
                "packet_contract_ref": {"path": "references/reviewer-profiles/product-goal-fidelity-packet-v0.1.json", "hash": "sha256:packet", "version": "v0.1"},
                "commitment_refs": [
                    {"path": "decision-v1.json", "hash": "sha256:decision", "version": 1}
                ],
            },
            "goal_fidelity_packet": {
                "goal": "保持已确认产品目标与范围承诺",
                "candidate_ref": CANDIDATE,
                "commitment_refs": [
                    {"path": "decision-v1.json", "hash": "sha256:decision", "version": 1}
                ],
            },
            "findings": [
                {
                    "finding_id": finding_id,
                    "topic_id": "scope-risk",
                    "stance": stance,
                    "concern": f"{role} concern",
                    "concern_level": "KEY_ATTENTION",
                    "basis_refs": ["prd-v0.1.md", "decision-v1.json"],
                    "possible_impact": "scope impact",
                    "professional_recommendation": "外置团队关注",
                    "confidence": "high",
                    "confidence_basis": "direct exact refs",
                }
            ],
        },
        "artifact_refs": [],
    }


class ReviewContractTests(unittest.TestCase):
    def test_disagreement_aliases_are_unambiguous(self) -> None:
        with self.assertRaisesRegex(ReviewContractError, "both finding_ids and findings"):
            validate_aggregate_disagreements(
                [
                    {
                        "topic_id": "scope-risk",
                        "finding_ids": ["f-1"],
                        "findings": ["f-1"],
                    }
                ]
            )

    def test_review_requires_exact_goal_profile_rubric_packet_and_commitment_refs(self) -> None:
        for missing in ("profile_ref", "rubric_ref", "packet_contract_ref", "commitment_refs"):
            with self.subTest(missing=missing):
                submission = review_submission("product", "f-goal", "concern")
                submission["semantic_output"]["goal_fidelity_refs"].pop(missing)
                with self.assertRaisesRegex(ReviewContractError, "Goal Fidelity|commitment"):
                    validate_review_submission(submission)

    def test_program_or_reviewer_block_authority_is_rejected(self) -> None:
        submission = review_submission("product", "f-1", "concern")
        submission["semantic_output"]["authority"] = "BLOCK"
        with self.assertRaisesRegex(ReviewContractError, "ADVISORY_ONLY"):
            validate_review_submission(submission)
        submission = review_submission("product", "f-2", "concern")
        submission["producer"] = {"kind": "DETERMINISTIC_PROGRAM", "component": "validator"}
        with self.assertRaisesRegex(ReviewContractError, "HOST_AGENT"):
            validate_review_submission(submission)

    def test_aggregate_preserves_disagreement_and_never_boosts_evidence_confidence(self) -> None:
        aggregated = aggregate_reviews(
            CANDIDATE,
            [
                review_submission("product", "f-product", "scope-expanded"),
                review_submission("engineering_feasibility", "f-eng", "scope-feasible"),
                review_submission("testability", "f-test", "measurement-weak"),
            ],
        )
        self.assertEqual(len(aggregated["findings"]), 3)
        self.assertEqual(aggregated["disagreements"][0]["topic_id"], "scope-risk")
        self.assertNotIn("confidence", aggregated)
        self.assertNotIn("majority", aggregated)

    def test_finalize_checks_roles_dispositions_and_companion_version_not_approval(self) -> None:
        submissions = [
            review_submission("product", "f-product", "a"),
            review_submission("engineering_feasibility", "f-eng", "b"),
            review_submission("testability", "f-test", "c"),
        ]
        aggregated = aggregate_reviews(CANDIDATE, submissions)
        dispositions = [
            {"finding_id": item["finding_id"], "status": "EXTERNAL_REVIEW"}
            for item in aggregated["findings"]
        ]
        result = finalize_review(
            CANDIDATE,
            submissions,
            aggregated,
            dispositions,
            companion_view_ref={"candidate_hash": "sha256:prd", "finding_count": 3},
        )
        self.assertEqual(result["status"], "FINALIZED")
        self.assertNotIn("approved", result)

    def test_review_optimize_stops_on_no_progress_or_round_limit_without_generating_content(self) -> None:
        self.assertEqual(
            next_review_action(["sha256:v1", "sha256:v1"], agent_requested_optimize=True),
            "NO_PROGRESS_STOP",
        )
        self.assertEqual(
            next_review_action(["sha256:v1", "sha256:v2", "sha256:v3"], agent_requested_optimize=True),
            "ROUND_LIMIT_STOP",
        )
        self.assertEqual(
            next_review_action(["sha256:v1"], agent_requested_optimize=True),
            "AWAIT_AGENT_CANDIDATE",
        )


if __name__ == "__main__":
    unittest.main()
