"""Closed writing-review coverage validation; never judges prose semantics."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .storage import IntegrityError, assert_managed_path, read_json, sha256_file
from .visual_assets import VisualAssetError, scan_reader_visible_visual_source


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
READER_REVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "authority",
        "candidate_ref",
        "candidate_tree_hash",
        "profile_ref",
        "guide_ref",
        "review_contract_ref",
        "output_contract_ref",
        "author_execution_ref",
        "reviewer_execution_ref",
        "reviewer_role",
        "isolated_input_refs",
        "reader_readback",
        "reader_outcome_failures",
        "verbosity_assessment",
        "checklist_assessment",
        "visual_assessment",
        "finding_refs",
        "claim_boundary",
    }
)
READBACK_FIELDS = frozenset(
    {
        "problem_and_outcome",
        "primary_relationships",
        "mental_model",
        "main_path_and_recovery",
        "decision_conditions_and_risks",
        "navigation_map",
    }
)
MENTAL_MODEL_FIELDS = frozenset({"name", "role"})
NAVIGATION_FIELDS = frozenset({"target", "location"})
NAVIGATION_TARGETS = frozenset(
    {"PRODUCT_RULES", "ACCEPTANCE", "RISKS_UNKNOWNS_NEXT"}
)
ASSESSMENT_FIELDS = frozenset(
    {
        "verdict",
        "issue_types",
        "repair_techniques",
        "basis_refs",
        "finding_refs",
        "reason",
    }
)
VISUAL_ASSESSMENT_FIELDS = ASSESSMENT_FIELDS | frozenset(
    {"observation_status", "visual_pair_refs"}
)
VISUAL_PAIR_FIELDS = frozenset({"svg_ref", "png_ref"})
OUTCOME_FAILURE_FIELDS = frozenset(
    {"outcome", "basis_refs", "reason", "finding_id"}
)
READER_OUTCOMES = frozenset(
    {"UNDERSTAND", "SEE", "MODEL", "RETELL", "DECIDE", "LOCATE"}
)
DIAGNOSTIC_CATEGORIES = frozenset(
    {
        "SEMANTIC_REPETITION",
        "FLAT_PEER_OVERLOAD",
        "REPRESENTATION_COLLISION",
        "DETAIL_IN_MAIN_PATH",
        "DENSE_TABLE",
        "JARGON_INTRUSION",
        "CHECKLIST_FUNCTION_LOSS",
        "COMPLETION_SEMANTICS_AMBIGUOUS",
        "ARTIFACT_MATURITY_OVERCLAIM",
        "RAW_INLINE_SVG",
        "UNSAFE_OR_UNAVAILABLE_VISUAL",
    }
)
REPAIR_TECHNIQUES = frozenset(
    {
        "REORDER",
        "GROUP",
        "EXPLAIN",
        "EXAMPLE",
        "VISUALIZE",
        "LAYER",
        "MERGE",
        "REFERENCE",
        "MOVE",
        "TRIM",
        "RESTORE_FUNCTION",
        "BOUNDARY",
    }
)


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


def _non_empty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WritingReviewError(f"{label} must be non-empty text")
    return value


def _unique_enum_list(
    value: Any, allowed: frozenset[str], label: str
) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or item not in allowed for item in value)
        or len(value) != len(set(value))
    ):
        raise WritingReviewError(f"{label} must be a unique allowed enum list")
    return value


def _validate_basis_refs(
    value: Any,
    *,
    label: str,
    candidate_ref: dict[str, Any],
    candidate_line_count: int,
    required: bool,
) -> None:
    if not isinstance(value, list) or (required and not value):
        qualifier = "a non-empty exact list" if required else "an exact list"
        raise WritingReviewError(f"{label} must be {qualifier}")
    for index, raw_basis in enumerate(value):
        basis_path = f"{label}[{index}]"
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


def _validate_reader_failures(
    value: Any,
    *,
    candidate_ref: dict[str, Any],
    candidate_line_count: int,
    available_finding_ids: set[str],
) -> set[str]:
    if not isinstance(value, list):
        raise WritingReviewError("reader_outcome_failures must be a list")
    outcomes: list[str] = []
    linked: set[str] = set()
    for index, raw in enumerate(value):
        label = f"reader_outcome_failures[{index}]"
        item = _closed_mapping(raw, OUTCOME_FAILURE_FIELDS, label)
        outcome = item.get("outcome")
        if outcome not in READER_OUTCOMES:
            raise WritingReviewError(f"{label}.outcome is invalid")
        outcomes.append(outcome)
        _non_empty_text(item.get("reason"), f"{label}.reason")
        _validate_basis_refs(
            item.get("basis_refs"),
            label=f"{label}.basis_refs",
            candidate_ref=candidate_ref,
            candidate_line_count=candidate_line_count,
            required=True,
        )
        finding_id = item.get("finding_id")
        if not isinstance(finding_id, str) or finding_id not in available_finding_ids:
            raise WritingReviewError(
                f"{label}.finding_id is not an available Review Finding"
            )
        linked.add(finding_id)
    if len(outcomes) != len(set(outcomes)):
        raise WritingReviewError("reader_outcome_failures must contain unique outcomes")
    return linked


def _validate_assessment(
    value: Any,
    *,
    label: str,
    candidate_ref: dict[str, Any],
    candidate_line_count: int,
    available_finding_ids: set[str],
    expected_visual_pairs: list[dict[str, Any]],
    expected_visual_source_scan: dict[str, Any] | None,
) -> set[str]:
    is_visual = label == "visual_assessment"
    item = _closed_mapping(
        value, VISUAL_ASSESSMENT_FIELDS if is_visual else ASSESSMENT_FIELDS, label
    )
    allowed_verdicts = (
        {"PASS", "FINDING", "NOT_NEEDED"}
        if label == "visual_assessment"
        else {"PASS", "FINDING"}
    )
    verdict = item.get("verdict")
    if verdict not in allowed_verdicts:
        raise WritingReviewError(f"{label}.verdict is invalid")
    source_issues = (
        expected_visual_source_scan.get("issues", [])
        if is_visual and isinstance(expected_visual_source_scan, dict)
        else []
    )
    required_source_issue_types = {
        issue.get("issue_type")
        for issue in source_issues
        if isinstance(issue, dict)
        and issue.get("issue_type") in {
            "RAW_INLINE_SVG",
            "UNSAFE_OR_UNAVAILABLE_VISUAL",
        }
    }
    if required_source_issue_types and verdict != "FINDING":
        issue = sorted(required_source_issue_types)[0]
        raise WritingReviewError(
            f"visual_assessment must record a FINDING for {issue}"
        )
    _non_empty_text(item.get("reason"), f"{label}.reason")
    if is_visual:
        raw_pairs = item.get("visual_pair_refs")
        if not isinstance(raw_pairs, list):
            raise WritingReviewError("visual_assessment.visual_pair_refs must be a list")
        pairs: list[dict[str, Any]] = []
        for index, raw_pair in enumerate(raw_pairs):
            pair = _closed_mapping(
                raw_pair, VISUAL_PAIR_FIELDS, f"visual_assessment.visual_pair_refs[{index}]"
            )
            pairs.append(
                {
                    "svg_ref": _exact_ref(
                        pair.get("svg_ref"),
                        f"visual_assessment.visual_pair_refs[{index}].svg_ref",
                    ),
                    "png_ref": _exact_ref(
                        pair.get("png_ref"),
                        f"visual_assessment.visual_pair_refs[{index}].png_ref",
                    ),
                }
            )
        observation = item.get("observation_status")
        if verdict == "NOT_NEEDED":
            if observation != "NOT_NEEDED" or pairs or expected_visual_pairs:
                raise WritingReviewError(
                    "visual_assessment NOT_NEEDED requires no Candidate visual pair"
                )
        elif verdict == "PASS":
            if (
                observation != "OBSERVED"
                or not expected_visual_pairs
                or pairs != expected_visual_pairs
            ):
                raise WritingReviewError(
                    "visual_assessment PASS must bind every exact safe visual pair as OBSERVED"
                )
        elif verdict == "FINDING":
            expected_observation = (
                "NOT_RENDERED"
                if required_source_issue_types
                else ("OBSERVED" if expected_visual_pairs else "NOT_OBSERVED")
            )
            if observation != expected_observation or pairs != expected_visual_pairs:
                raise WritingReviewError(
                    "visual_assessment FINDING observation must bind the exact safe visual pairs"
                )
    issue_types = _unique_enum_list(
        item.get("issue_types"), DIAGNOSTIC_CATEGORIES, f"{label}.issue_types"
    )
    techniques = _unique_enum_list(
        item.get("repair_techniques"), REPAIR_TECHNIQUES, f"{label}.repair_techniques"
    )
    finding_refs = item.get("finding_refs")
    if (
        not isinstance(finding_refs, list)
        or any(not isinstance(ref, str) or not ref for ref in finding_refs)
        or len(finding_refs) != len(set(finding_refs))
    ):
        raise WritingReviewError(f"{label}.finding_refs must be a unique string list")
    if verdict == "FINDING":
        if not issue_types or not techniques or not finding_refs:
            raise WritingReviewError(
                f"{label} FINDING requires issue_types, repair_techniques and finding_refs"
            )
        _validate_basis_refs(
            item.get("basis_refs"),
            label=f"{label}.basis_refs",
            candidate_ref=candidate_ref,
            candidate_line_count=candidate_line_count,
            required=True,
        )
        if required_source_issue_types:
            if not required_source_issue_types.issubset(set(issue_types)):
                missing = sorted(required_source_issue_types - set(issue_types))[0]
                raise WritingReviewError(
                    f"visual_assessment FINDING must diagnose {missing}"
                )
            required_bases = [
                basis
                for issue in source_issues
                if isinstance(issue, dict)
                and issue.get("issue_type") in required_source_issue_types
                for basis in issue.get("basis_refs", [])
            ]
            if item.get("basis_refs") != required_bases:
                raise WritingReviewError(
                    "visual_assessment FINDING must bind the exact visual source scan basis"
                )
        unknown = [ref for ref in finding_refs if ref not in available_finding_ids]
        if unknown:
            raise WritingReviewError(
                f"{label}.finding_refs references an unavailable Review Finding"
            )
        return set(finding_refs)
    if issue_types or techniques or finding_refs:
        raise WritingReviewError(
            f"{label} passing assessment cannot declare Finding diagnosis"
        )
    _validate_basis_refs(
        item.get("basis_refs"),
        label=f"{label}.basis_refs",
        candidate_ref=candidate_ref,
        candidate_line_count=candidate_line_count,
        required=False,
    )
    return set()


def _validate_reader_review_v3(
    value: Any,
    *,
    expected_candidate_ref: dict[str, Any],
    expected_candidate_tree_hash: str,
    expected_profile_ref: dict[str, Any],
    expected_guide_ref: dict[str, Any],
    expected_review_contract_ref: dict[str, Any] | None,
    expected_output_contract_ref: dict[str, Any],
    expected_author_execution_ref: dict[str, str],
    candidate_line_count: int,
    available_finding_ids: set[str],
    expected_visual_pairs: list[dict[str, Any]],
    expected_visual_source_scan: dict[str, Any] | None,
) -> dict[str, Any]:
    review = _closed_mapping(value, READER_REVIEW_FIELDS, "writing_review")
    if review.get("schema_version") != "document-experience-reader-review.v3":
        raise WritingReviewError("writing_review.schema_version is invalid")
    if review.get("authority") != "ADVISORY_ONLY":
        raise WritingReviewError("writing_review.authority must be ADVISORY_ONLY")
    candidate_ref = _exact_ref(review.get("candidate_ref"), "candidate_ref")
    if candidate_ref != expected_candidate_ref:
        raise WritingReviewError("writing review does not bind the exact current Candidate")
    if review.get("candidate_tree_hash") != expected_candidate_tree_hash:
        raise WritingReviewError("writing review Candidate tree hash is stale")
    for field, expected in (
        ("profile_ref", expected_profile_ref),
        ("guide_ref", expected_guide_ref),
        ("output_contract_ref", expected_output_contract_ref),
    ):
        if _exact_ref(review.get(field), field) != expected:
            raise WritingReviewError(f"writing review {field} differs from exact authority")
    review_contract_ref = _exact_ref(
        review.get("review_contract_ref"), "review_contract_ref"
    )
    if (
        expected_review_contract_ref is None
        or review_contract_ref != expected_review_contract_ref
    ):
        raise WritingReviewError(
            "writing review review_contract_ref differs from exact authority"
        )
    author = _execution_ref(review.get("author_execution_ref"), "author_execution_ref")
    reviewer = _execution_ref(
        review.get("reviewer_execution_ref"), "reviewer_execution_ref"
    )
    if author != expected_author_execution_ref:
        raise WritingReviewError("writing review author execution differs from Candidate provenance")
    if author["id"] == reviewer["id"]:
        raise WritingReviewError(
            "PRD author and Writing Reviewer execution ids must differ"
        )
    if reviewer.get("kind") != "HOST_SUBAGENT_ATTEMPT":
        raise WritingReviewError("Writing Reviewer must use a HOST_SUBAGENT_ATTEMPT")
    if review.get("reviewer_role") != "writing_standard":
        raise WritingReviewError("Writing Reviewer role must be writing_standard")
    isolated = review.get("isolated_input_refs")
    if isolated != [
        expected_candidate_ref,
        expected_profile_ref,
        expected_guide_ref,
        review_contract_ref,
        expected_output_contract_ref,
    ]:
        raise WritingReviewError("Writing Reviewer isolated_input_refs are not exact")

    readback = _closed_mapping(review.get("reader_readback"), READBACK_FIELDS, "reader_readback")
    for field in (
        "problem_and_outcome",
        "primary_relationships",
        "main_path_and_recovery",
        "decision_conditions_and_risks",
    ):
        _non_empty_text(readback.get(field), f"reader_readback.{field}")
    mental_model = readback.get("mental_model")
    if not isinstance(mental_model, list) or not 3 <= len(mental_model) <= 5:
        raise WritingReviewError("reader_readback.mental_model requires three to five components")
    component_names: list[str] = []
    for index, raw in enumerate(mental_model):
        item = _closed_mapping(raw, MENTAL_MODEL_FIELDS, f"reader_readback.mental_model[{index}]")
        component_names.append(
            _non_empty_text(
                item.get("name"), f"reader_readback.mental_model[{index}].name"
            )
        )
        _non_empty_text(item.get("role"), f"reader_readback.mental_model[{index}].role")
    if len(component_names) != len(set(component_names)):
        raise WritingReviewError(
            "reader_readback.mental_model component names must be unique"
        )
    navigation = readback.get("navigation_map")
    if not isinstance(navigation, list) or not navigation:
        raise WritingReviewError("reader_readback.navigation_map must be non-empty")
    navigation_targets: list[str] = []
    for index, raw in enumerate(navigation):
        item = _closed_mapping(raw, NAVIGATION_FIELDS, f"reader_readback.navigation_map[{index}]")
        navigation_targets.append(
            _non_empty_text(
                item.get("target"), f"reader_readback.navigation_map[{index}].target"
            )
        )
        _non_empty_text(item.get("location"), f"reader_readback.navigation_map[{index}].location")
    if (
        len(navigation_targets) != len(set(navigation_targets))
        or set(navigation_targets) != NAVIGATION_TARGETS
    ):
        raise WritingReviewError(
            "reader_readback.navigation_map must cover rules, acceptance and risks exactly once"
        )

    linked_findings = _validate_reader_failures(
        review.get("reader_outcome_failures"),
        candidate_ref=candidate_ref,
        candidate_line_count=candidate_line_count,
        available_finding_ids=available_finding_ids,
    )
    for field in ("verbosity_assessment", "checklist_assessment", "visual_assessment"):
        linked_findings.update(
            _validate_assessment(
                review.get(field),
                label=field,
                candidate_ref=candidate_ref,
                candidate_line_count=candidate_line_count,
                available_finding_ids=available_finding_ids,
                expected_visual_pairs=expected_visual_pairs,
                expected_visual_source_scan=expected_visual_source_scan,
            )
        )
    finding_refs = review.get("finding_refs")
    if (
        not isinstance(finding_refs, list)
        or any(not isinstance(ref, str) or not ref for ref in finding_refs)
        or len(finding_refs) != len(set(finding_refs))
        or set(finding_refs) != linked_findings
    ):
        raise WritingReviewError(
            "writing_review.finding_refs must equal every FINDING-linked Review Finding"
        )
    if review.get("claim_boundary") != "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN":
        raise WritingReviewError("writing_review.claim_boundary is invalid")
    return deepcopy(review)


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
    expected_review_contract_ref: dict[str, Any] | None = None,
    expected_visual_pairs: list[dict[str, Any]] | None = None,
    expected_visual_source_scan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate exact 13+10 coverage and recorded subagent separation."""

    if (
        isinstance(value, dict)
        and value.get("schema_version") == "document-experience-reader-review.v3"
    ):
        return _validate_reader_review_v3(
            value,
            expected_candidate_ref=expected_candidate_ref,
            expected_candidate_tree_hash=expected_candidate_tree_hash,
            expected_profile_ref=expected_profile_ref,
            expected_guide_ref=expected_guide_ref,
            expected_review_contract_ref=expected_review_contract_ref,
            expected_output_contract_ref=expected_output_contract_ref,
            expected_author_execution_ref=expected_author_execution_ref,
            candidate_line_count=candidate_line_count,
            available_finding_ids=available_finding_ids,
            expected_visual_pairs=expected_visual_pairs or [],
            expected_visual_source_scan=expected_visual_source_scan,
        )

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
    if author["id"] == reviewer["id"]:
        raise WritingReviewError(
            "PRD author and Writing Reviewer execution ids must differ"
        )
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
        schema_version = coverage.get("schema_version")
        dispatch_schema = context.get("schema_version")
        profile_ref = context.get("profile_ref")
        profile_version = (
            profile_ref.get("version") if isinstance(profile_ref, dict) else None
        )
        if dispatch_schema == "writing-review-dispatch.v3":
            if (
                profile_version not in {"0.4.0", "0.5.0"}
                or schema_version != "document-experience-reader-review.v3"
            ):
                raise WritingReviewError(
                    "v0.4/v0.5 Writing Review requires the exact v3 coverage schema"
                )
        elif schema_version != "document-experience-coverage.v1":
            raise WritingReviewError(
                "legacy Writing Review requires the exact v1 coverage schema"
            )
        visual_source_scan = (
            scan_reader_visible_visual_source(
                root, candidate_path, candidate_ref=candidate
            )
            if schema_version == "document-experience-reader-review.v3"
            else None
        )
        visual_pairs = (
            visual_source_scan["safe_visual_pairs"]
            if isinstance(visual_source_scan, dict)
            else []
        )
    except (OSError, UnicodeError, ValueError, VisualAssetError) as error:
        raise WritingReviewError(f"Writing Coverage artifact is unreadable: {error}") from error
    if (
        schema_version == "document-experience-reader-review.v3"
        and (
            context.get("reader_visible_visual_pairs") != visual_pairs
            or context.get("visual_source_scan") != visual_source_scan
        )
    ):
        raise WritingReviewError(
            "Writing Review visual pairs differ from exact dispatch authority"
        )
    return validate_writing_coverage(
        coverage,
        expected_candidate_ref=candidate,
        expected_candidate_tree_hash=context.get("candidate_tree_hash"),
        expected_profile_ref=context.get("profile_ref"),
        expected_guide_ref=context.get("guide_ref"),
        expected_review_contract_ref=context.get("review_contract_ref"),
        expected_output_contract_ref=context.get("output_contract_ref"),
        expected_author_execution_ref=context.get("author_execution_ref"),
        required_rule_ids=context.get("required_rule_ids", []),
        required_check_ids=context.get("required_check_ids", []),
        candidate_line_count=line_count,
        available_finding_ids=available_finding_ids,
        expected_visual_pairs=visual_pairs,
        expected_visual_source_scan=visual_source_scan,
    )
