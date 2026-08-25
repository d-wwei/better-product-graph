"""Closed writing-review coverage validation; never judges prose semantics."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .storage import IntegrityError, assert_managed_path, read_json, sha256_file


class WritingReviewError(ValueError):
    """Writing-review evidence is incomplete, stale, or crosses authority."""


EXACT_REF_FIELDS = frozenset({"path", "hash", "version"})
EXECUTION_REF_FIELDS = frozenset({"kind", "id"})
COVERAGE_FIELDS = frozenset(
    {
        "schema_version",
        "candidate_ref",
        "candidate_tree_hash",
        "profile_ref",
        "guide_ref",
        "output_contract_ref",
        "author_execution_ref",
        "reviewer_execution_ref",
        "reviewer_role",
        "isolated_input_refs",
        "required_rule_results",
        "delivery_check_results",
        "finding_refs",
    }
)
RESULT_FIELDS = frozenset(
    {"rule_id", "check_id", "verdict", "basis_refs", "reason", "finding_id"}
)
BASIS_FIELDS = frozenset({"path", "hash", "start_line", "end_line"})
VERDICTS = frozenset({"PASS", "FINDING", "NOT_APPLICABLE"})


def _closed_mapping(value: Any, allowed: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WritingReviewError(f"{label} must be an object")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise WritingReviewError(f"{label}.{unknown[0]} is an unknown field")
    return value


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    ref = _closed_mapping(value, EXACT_REF_FIELDS, label)
    if any(ref.get(field) in (None, "") for field in EXACT_REF_FIELDS):
        raise WritingReviewError(f"{label} requires exact path/hash/version")
    return ref


def _execution_ref(value: Any, label: str) -> dict[str, str]:
    ref = _closed_mapping(value, EXECUTION_REF_FIELDS, label)
    if any(not isinstance(ref.get(field), str) or not ref[field] for field in EXECUTION_REF_FIELDS):
        raise WritingReviewError(f"{label} requires non-empty kind and id")
    return ref


def _validate_result_set(
    value: Any,
    *,
    id_field: str,
    expected_ids: Iterable[str],
    label: str,
    candidate_ref: dict[str, Any],
    candidate_line_count: int,
    available_finding_ids: set[str],
) -> set[str]:
    if not isinstance(value, list):
        raise WritingReviewError(f"{label} must be a list")
    expected = list(expected_ids)
    actual: list[str] = []
    linked_findings: set[str] = set()
    for index, raw in enumerate(value):
        path = f"{label}[{index}]"
        item = _closed_mapping(raw, RESULT_FIELDS, path)
        item_id = item.get(id_field)
        if not isinstance(item_id, str) or not item_id:
            raise WritingReviewError(f"{path}.{id_field} must be non-empty")
        other_id = "check_id" if id_field == "rule_id" else "rule_id"
        if other_id in item:
            raise WritingReviewError(f"{path}.{other_id} is not allowed")
        actual.append(item_id)
        verdict = item.get("verdict")
        if verdict not in VERDICTS:
            raise WritingReviewError(f"{path}.verdict must be PASS/FINDING/NOT_APPLICABLE")
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise WritingReviewError(f"{path}.reason must be non-empty")
        basis_refs = item.get("basis_refs")
        if not isinstance(basis_refs, list) or not basis_refs:
            raise WritingReviewError(f"{path}.basis_refs must be a non-empty exact list")
        for basis_index, raw_basis in enumerate(basis_refs):
            basis_path = f"{path}.basis_refs[{basis_index}]"
            basis = _closed_mapping(raw_basis, BASIS_FIELDS, basis_path)
            if (
                basis.get("path") != candidate_ref["path"]
                or basis.get("hash") != candidate_ref["hash"]
            ):
                raise WritingReviewError(f"{basis_path} must bind the exact current Candidate")
            start = basis.get("start_line")
            end = basis.get("end_line")
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or start < 1
                or end < start
                or end > candidate_line_count
            ):
                raise WritingReviewError(f"{basis_path} line range is outside the Candidate")
        finding_id = item.get("finding_id")
        if verdict == "FINDING":
            if not isinstance(finding_id, str) or not finding_id:
                raise WritingReviewError(f"{path}.finding_id is required for FINDING")
            if finding_id not in available_finding_ids:
                raise WritingReviewError(f"{path}.finding_id is not an available Review Finding")
            linked_findings.add(finding_id)
        elif finding_id is not None:
            raise WritingReviewError(f"{path}.finding_id is only allowed for FINDING")
    if len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise WritingReviewError(
            f"{label} must cover the exact unique required ID set"
        )
    return linked_findings


def validate_writing_coverage(
    value: Any,
    *,
    expected_candidate_ref: dict[str, Any],
    expected_candidate_tree_hash: str,
    expected_profile_ref: dict[str, Any],
    expected_guide_ref: dict[str, Any],
    expected_output_contract_ref: dict[str, Any],
    expected_author_execution_ref: dict[str, str],
    required_rule_ids: Iterable[str],
    required_check_ids: Iterable[str],
    candidate_line_count: int,
    available_finding_ids: set[str],
) -> dict[str, Any]:
    """Validate exact 13+10 coverage and recorded subagent separation."""

    coverage = _closed_mapping(value, COVERAGE_FIELDS, "writing_coverage")
    if coverage.get("schema_version") != "document-experience-coverage.v1":
        raise WritingReviewError("writing_coverage.schema_version is invalid")
    candidate_ref = _exact_ref(coverage.get("candidate_ref"), "candidate_ref")
    if candidate_ref != expected_candidate_ref:
        raise WritingReviewError("writing coverage does not bind the exact current Candidate")
    if coverage.get("candidate_tree_hash") != expected_candidate_tree_hash:
        raise WritingReviewError("writing coverage Candidate tree hash is stale")
    expected_refs = (
        ("profile_ref", expected_profile_ref),
        ("guide_ref", expected_guide_ref),
        ("output_contract_ref", expected_output_contract_ref),
    )
    for field, expected in expected_refs:
        if _exact_ref(coverage.get(field), field) != expected:
            raise WritingReviewError(f"writing coverage {field} differs from exact authority")
    author = _execution_ref(coverage.get("author_execution_ref"), "author_execution_ref")
    reviewer = _execution_ref(
        coverage.get("reviewer_execution_ref"), "reviewer_execution_ref"
    )
    if author != expected_author_execution_ref:
        raise WritingReviewError("writing coverage author execution differs from Candidate provenance")
    if author == reviewer:
        raise WritingReviewError("PRD author and Writing Reviewer execution must differ")
    if reviewer.get("kind") != "HOST_SUBAGENT_ATTEMPT":
        raise WritingReviewError("Writing Reviewer must use a HOST_SUBAGENT_ATTEMPT")
    if coverage.get("reviewer_role") != "writing_standard":
        raise WritingReviewError("Writing Reviewer role must be writing_standard")
    isolated = coverage.get("isolated_input_refs")
    allowed_inputs = [
        expected_candidate_ref,
        expected_profile_ref,
        expected_guide_ref,
        expected_output_contract_ref,
    ]
    if isolated != allowed_inputs:
        raise WritingReviewError("Writing Reviewer isolated_input_refs are not exact")
    linked = _validate_result_set(
        coverage.get("required_rule_results"),
        id_field="rule_id",
        expected_ids=required_rule_ids,
        label="required_rule_results",
        candidate_ref=candidate_ref,
        candidate_line_count=candidate_line_count,
        available_finding_ids=available_finding_ids,
    )
    linked.update(
        _validate_result_set(
            coverage.get("delivery_check_results"),
            id_field="check_id",
            expected_ids=required_check_ids,
            label="delivery_check_results",
            candidate_ref=candidate_ref,
            candidate_line_count=candidate_line_count,
            available_finding_ids=available_finding_ids,
        )
    )
    finding_refs = coverage.get("finding_refs")
    if (
        not isinstance(finding_refs, list)
        or any(not isinstance(item, str) or not item for item in finding_refs)
        or len(finding_refs) != len(set(finding_refs))
        or set(finding_refs) != linked
    ):
        raise WritingReviewError(
            "writing_coverage.finding_refs must equal every FINDING-linked Review Finding"
        )
    return deepcopy(coverage)


def load_and_validate_writing_coverage(
    project_root: Path,
    coverage_ref: dict[str, Any],
    *,
    context: dict[str, Any],
    available_finding_ids: set[str],
) -> dict[str, Any]:
    """Load one managed immutable coverage artifact and validate exact authority."""

    root = project_root.resolve()
    ref = _exact_ref(coverage_ref, "writing_coverage_ref")
    try:
        coverage_path = assert_managed_path(root, root / ref["path"])
    except IntegrityError as error:
        raise WritingReviewError("Writing Coverage must be an exact regular file") from error
    if (
        not coverage_path.is_file()
        or coverage_path.is_symlink()
        or sha256_file(coverage_path) != ref["hash"]
    ):
        raise WritingReviewError("Writing Coverage must be an exact regular file")
    candidate_ref = context.get("candidate_ref")
    candidate = _exact_ref(candidate_ref, "writing_review_context.candidate_ref")
    try:
        candidate_path = assert_managed_path(root, root / candidate["path"])
    except IntegrityError as error:
        raise WritingReviewError(
            "Writing Coverage Candidate must be an exact regular file"
        ) from error
    if (
        not candidate_path.is_file()
        or candidate_path.is_symlink()
        or sha256_file(candidate_path) != candidate["hash"]
    ):
        raise WritingReviewError("Writing Coverage Candidate must be an exact regular file")
    try:
        coverage = read_json(coverage_path)
        line_count = max(1, len(candidate_path.read_text(encoding="utf-8").splitlines()))
    except (OSError, UnicodeError, ValueError) as error:
        raise WritingReviewError(f"Writing Coverage artifact is unreadable: {error}") from error
    return validate_writing_coverage(
        coverage,
        expected_candidate_ref=candidate,
        expected_candidate_tree_hash=context.get("candidate_tree_hash"),
        expected_profile_ref=context.get("profile_ref"),
        expected_guide_ref=context.get("guide_ref"),
        expected_output_contract_ref=context.get("output_contract_ref"),
        expected_author_execution_ref=context.get("author_execution_ref"),
        required_rule_ids=context.get("required_rule_ids", []),
        required_check_ids=context.get("required_check_ids", []),
        candidate_line_count=line_count,
        available_finding_ids=available_finding_ids,
    )
