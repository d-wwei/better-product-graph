from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.bpg.review_projection import (
    ReviewProjectionError,
    validate_reviewer_work_orders,
)


ROLES = ["product", "engineering_feasibility", "testability", "writing_standard"]
AUTHOR = {"kind": "HOST_AGENT_ATTEMPT", "id": "attempt-author-v06-exact"}
EVAL = {"kind": "HOST_SUBAGENT_ATTEMPT", "id": "v08-reviewer-001"}


def work_orders(root: Path) -> list[dict]:
    return [
        {
            "reviewer_role": role,
            "reviewer_execution_ref": {
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": f"ordinary-review-rc7-{index + 1:02d}-{role}",
            },
            "output_target": {
                "path": f"outputs/{role}/review-result.json",
                "absolute_path": str(
                    (root / f"outputs/{role}/review-result.json").resolve()
                ),
            },
        }
        for index, role in enumerate(ROLES)
    ]


class ReviewProjectionTests(unittest.TestCase):
    def test_four_roles_prebind_unique_execution_refs_and_absent_exact_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            validated = validate_reviewer_work_orders(
                root,
                work_orders(root),
                expected_roles=ROLES,
                author_execution_ref=AUTHOR,
                forbidden_execution_refs=[EVAL],
            )

            self.assertEqual([item["reviewer_role"] for item in validated], ROLES)
            self.assertEqual(
                len({item["reviewer_execution_ref"]["id"] for item in validated}),
                4,
            )
            self.assertTrue(
                all(not Path(item["output_target"]["absolute_path"]).exists() for item in validated)
            )

    def test_identity_overlap_target_overlap_and_existing_output_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases: dict[str, list[dict]] = {}
            duplicate_identity = work_orders(root)
            duplicate_identity[1]["reviewer_execution_ref"] = deepcopy(
                duplicate_identity[0]["reviewer_execution_ref"]
            )
            cases["unique reviewer_execution_ref"] = duplicate_identity
            author_overlap = work_orders(root)
            author_overlap[0]["reviewer_execution_ref"] = deepcopy(AUTHOR)
            cases["author execution"] = author_overlap
            eval_overlap = work_orders(root)
            eval_overlap[0]["reviewer_execution_ref"] = deepcopy(EVAL)
            cases["forbidden execution"] = eval_overlap
            wrong_execution_kind = work_orders(root)
            wrong_execution_kind[0]["reviewer_execution_ref"]["kind"] = "HOST_AGENT_ATTEMPT"
            cases["HOST_SUBAGENT_ATTEMPT"] = wrong_execution_kind
            duplicate_target = work_orders(root)
            duplicate_target[1]["output_target"] = deepcopy(
                duplicate_target[0]["output_target"]
            )
            cases["unique output_target"] = duplicate_target
            mismatched_absolute = work_orders(root)
            mismatched_absolute[0]["output_target"]["absolute_path"] = str(
                (root / "elsewhere.json").resolve()
            )
            cases["absolute target"] = mismatched_absolute
            traversal = work_orders(root)
            traversal[0]["output_target"] = {
                "path": "../outside.json",
                "absolute_path": str((root.parent / "outside.json").resolve()),
            }
            cases["inside projection root"] = traversal

            for expected, value in cases.items():
                with self.subTest(expected=expected), self.assertRaisesRegex(
                    ReviewProjectionError, expected
                ):
                    validate_reviewer_work_orders(
                        root,
                        value,
                        expected_roles=ROLES,
                        author_execution_ref=AUTHOR,
                        forbidden_execution_refs=[EVAL],
                    )

            existing = work_orders(root)
            path = Path(existing[0]["output_target"]["absolute_path"])
            path.parent.mkdir(parents=True)
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ReviewProjectionError, "must not exist"):
                validate_reviewer_work_orders(
                    root,
                    existing,
                    expected_roles=ROLES,
                    author_execution_ref=AUTHOR,
                    forbidden_execution_refs=[EVAL],
                )


if __name__ == "__main__":
    unittest.main()
