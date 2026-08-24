"""Validate one bounded Host/subagent Eval fulfillment repair submission."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .evals_authority import EvalsAuthorityError, validate_reviewed_evals
from .storage import assert_managed_path, read_json, sha256_file


class EvalsFulfillmentError(ValueError):
    """A Ready repair submission lacks exact independent Eval authority."""


SUBMISSION_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_ref",
        "build_attempt",
        "review_attempt",
        "eval_pack_ref",
        "fixtures_ref",
        "review_ref",
    }
)


def _identity(value: Any, label: str) -> tuple[str, str]:
    if (
        not isinstance(value, dict)
        or set(value) != {"kind", "id"}
        or not isinstance(value.get("kind"), str)
        or not value["kind"]
        or not isinstance(value.get("id"), str)
        or not value["id"]
    ):
        raise EvalsFulfillmentError(f"{label} must contain exactly non-empty kind and id")
    return value["kind"], value["id"]


def _exact_ref(project_root: Path, value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "hash", "version"}
        or not isinstance(value.get("path"), str)
        or not isinstance(value.get("hash"), str)
        or value.get("version") is None
    ):
        raise EvalsFulfillmentError(f"{label} must be one closed exact path/hash/version ref")
    path = assert_managed_path(project_root, project_root / value["path"])
    if not path.is_file() or path.is_symlink() or sha256_file(path) != value["hash"]:
        raise EvalsFulfillmentError(f"{label} file/hash authority is invalid")
    return dict(value)


def validate_evals_fulfillment_submission(
    project_root: Path,
    skill_root: Path,
    submission: Any,
    *,
    expected_candidate_ref: dict[str, Any],
    artifact_refs: dict[str, Any],
) -> dict[str, Any]:
    """Return REVIEWED/NOT_RUN metadata only after exact independent validation."""

    if not isinstance(submission, dict) or set(submission) != SUBMISSION_FIELDS:
        raise EvalsFulfillmentError("Eval fulfillment submission must use the closed v1 contract")
    if submission.get("schema_version") != "evals-fulfillment-submission.v1":
        raise EvalsFulfillmentError("Eval fulfillment schema_version is invalid")
    candidate_ref = submission.get("candidate_ref")
    if candidate_ref != expected_candidate_ref:
        raise EvalsFulfillmentError("Eval fulfillment does not bind the exact current Candidate")
    build_identity = _identity(submission.get("build_attempt"), "build_attempt")
    review_identity = _identity(submission.get("review_attempt"), "review_attempt")
    if build_identity[0] != "HOST_AGENT":
        raise EvalsFulfillmentError("Eval Pack builder must be the current HOST_AGENT")
    if build_identity == review_identity:
        raise EvalsFulfillmentError("Eval Pack builder and independent reviewer must differ")
    pack_ref = _exact_ref(project_root, submission.get("eval_pack_ref"), "eval_pack_ref")
    fixtures_ref = _exact_ref(project_root, submission.get("fixtures_ref"), "fixtures_ref")
    review_ref = _exact_ref(project_root, submission.get("review_ref"), "review_ref")
    pack = read_json(project_root / pack_ref["path"])
    review = read_json(project_root / review_ref["path"])
    if pack.get("producer") != submission["build_attempt"]:
        raise EvalsFulfillmentError("Eval Pack producer differs from build_attempt")
    if review.get("reviewer") != submission["review_attempt"]:
        raise EvalsFulfillmentError("Eval review identity differs from review_attempt")

    build_attempt_id = f"evals-build:{build_identity[0]}:{build_identity[1]}"
    review_attempt_id = f"evals-review:{review_identity[0]}:{review_identity[1]}"
    virtual = list(artifact_refs.values()) + [
        {
            "role": "prd_candidate",
            **expected_candidate_ref,
            "origin_node_id": "evals.build",
            "origin_attempt_id": build_attempt_id,
        },
        {
            "role": "eval_pack",
            **pack_ref,
            "origin_node_id": "evals.build",
            "origin_attempt_id": build_attempt_id,
        },
        {
            "role": "eval_fixtures",
            **fixtures_ref,
            "origin_node_id": "evals.build",
            "origin_attempt_id": build_attempt_id,
        },
        {
            "role": "eval_pack_review",
            **review_ref,
            "origin_node_id": "evals.review",
            "origin_attempt_id": review_attempt_id,
        },
        {"role": "node_result", "node_id": "evals.build", "attempt_id": build_attempt_id},
        {"role": "node_result", "node_id": "evals.review", "attempt_id": review_attempt_id},
    ]
    input_hashes = {
        ref["path"]: ref["hash"]
        for ref in virtual
        if isinstance(ref, dict)
        and isinstance(ref.get("path"), str)
        and isinstance(ref.get("hash"), str)
    }
    evals = {
        "applicability": "REQUIRED",
        "fulfillment": "REVIEWED",
        "execution_status": "NOT_RUN",
        "pack_ref": pack_ref,
        "review_ref": review_ref,
        "ground_truth_provenance": pack.get("ground_truth_provenance"),
    }
    try:
        validate_reviewed_evals(
            project_root,
            skill_root,
            evals,
            expected_candidate_ref=expected_candidate_ref,
            artifact_refs=virtual,
            dispatched_input_hashes=input_hashes,
            committed_attempt_ids=frozenset({build_attempt_id, review_attempt_id}),
        )
    except EvalsAuthorityError as error:
        raise EvalsFulfillmentError(str(error)) from error
    return {
        "evals": evals,
        "pack_ref": pack_ref,
        "fixtures_ref": fixtures_ref,
        "review_ref": review_ref,
        "build_attempt_id": build_attempt_id,
        "review_attempt_id": review_attempt_id,
        "build_identity": submission["build_attempt"],
        "review_identity": submission["review_attempt"],
    }
