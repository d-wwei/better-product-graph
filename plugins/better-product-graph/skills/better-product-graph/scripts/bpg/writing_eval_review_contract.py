"""Closed mechanical validator for the evaluation-only Writing Reviewer result."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .storage import IntegrityError, assert_managed_path, sha256_bytes


class WritingEvalReviewError(ValueError):
    """The Writing Eval result is incomplete, stale, or crosses authority."""


SCHEMA_VERSION = "document-experience-reader-eval.v3.1"
EXACT_REF_FIELDS = frozenset({"path", "hash", "version"})
EXECUTION_REF_FIELDS = frozenset({"kind", "id"})
RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "evaluation_only",
        "authority",
        "suite_id",
        "case_id",
        "node_id",
        "attempt_id",
        "instruction_ref",
        "instruction_hash",
        "input_refs",
        "input_hashes",
        "preregistration_checkpoint_ref",
        "candidate_ref",
        "profile_ref",
        "guide_ref",
        "reviewer_resource_ref",
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
        "result",
        "primary_diagnosis",
        "primary_repair_technique",
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
BASIS_FIELDS = frozenset({"path", "hash", "start_line", "end_line"})
FAILURE_FIELDS = frozenset({"outcome", "basis_refs", "reason"})
ASSESSMENT_FIELDS = frozenset(
    {"verdict", "issue_types", "repair_techniques", "basis_refs", "reason"}
)
VISUAL_ASSESSMENT_FIELDS = ASSESSMENT_FIELDS | frozenset(
    {"observation_status", "visual_pair_refs"}
)
VISUAL_PAIR_FIELDS = frozenset({"svg_ref", "png_ref"})
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


def _closed(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        missing = sorted(fields - set(value)) if isinstance(value, dict) else []
        extra = sorted(set(value) - fields) if isinstance(value, dict) else []
        detail = f" missing={missing} extra={extra}" if missing or extra else ""
        raise WritingEvalReviewError(f"{label} must be a closed object{detail}")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WritingEvalReviewError(f"{label} must be non-empty text")
    return value


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    ref = _closed(value, EXACT_REF_FIELDS, label)
    path = ref.get("path")
    digest = ref.get("hash")
    version = ref.get("version")
    if not isinstance(path, str) or not path:
        raise WritingEvalReviewError(f"{label}.path must be non-empty")
    if (
        not isinstance(digest, str)
        or len(digest) != 71
        or not digest.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in digest[7:])
    ):
        raise WritingEvalReviewError(f"{label}.hash must be an exact lowercase sha256")
    if isinstance(version, bool) or (
        not isinstance(version, (str, int))
        or (isinstance(version, str) and not version.strip())
        or (isinstance(version, int) and version < 1)
    ):
        raise WritingEvalReviewError(
            f"{label}.version must be a non-empty string or integer >= 1"
        )
    return ref


def _execution_ref(value: Any, label: str) -> dict[str, str]:
    ref = _closed(value, EXECUTION_REF_FIELDS, label)
    for field in EXECUTION_REF_FIELDS:
        _text(ref.get(field), f"{label}.{field}")
    return ref


def _enum_list(value: Any, allowed: frozenset[str], label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or item not in allowed for item in value)
        or len(value) != len(set(value))
    ):
        raise WritingEvalReviewError(f"{label} must be a unique allowed enum list")
    return value


def _basis_refs(
    value: Any,
    *,
    label: str,
    candidate_ref: dict[str, Any],
    line_count: int,
) -> None:
    if not isinstance(value, list) or not value:
        raise WritingEvalReviewError(f"{label} must be a non-empty exact list")
    for index, raw in enumerate(value):
        basis = _closed(raw, BASIS_FIELDS, f"{label}[{index}]")
        if (
            basis.get("path") != candidate_ref["path"]
            or basis.get("hash") != candidate_ref["hash"]
        ):
            raise WritingEvalReviewError(
                f"{label}[{index}] must bind the exact current Candidate"
            )
        start = basis.get("start_line")
        end = basis.get("end_line")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 1
            or end < start
            or end > line_count
        ):
            raise WritingEvalReviewError(
                f"{label}[{index}] line range is outside the Candidate"
            )


def _assessment(
    value: Any,
    *,
    label: str,
    candidate_ref: dict[str, Any],
    line_count: int,
    expected_visual_pairs: list[dict[str, Any]],
) -> tuple[set[str], set[str], bool]:
    visual = label == "visual_assessment"
    item = _closed(
        value,
        VISUAL_ASSESSMENT_FIELDS if visual else ASSESSMENT_FIELDS,
        label,
    )
    verdicts = {"PASS", "FINDING", "NOT_NEEDED"} if visual else {"PASS", "FINDING"}
    verdict = item.get("verdict")
    if verdict not in verdicts:
        raise WritingEvalReviewError(f"{label}.verdict is invalid")
    _text(item.get("reason"), f"{label}.reason")
    _basis_refs(
        item.get("basis_refs"),
        label=f"{label}.basis_refs",
        candidate_ref=candidate_ref,
        line_count=line_count,
    )
    issues = set(
        _enum_list(item.get("issue_types"), DIAGNOSTIC_CATEGORIES, f"{label}.issue_types")
    )
    repairs = set(
        _enum_list(
            item.get("repair_techniques"), REPAIR_TECHNIQUES, f"{label}.repair_techniques"
        )
    )
    if verdict == "FINDING" and (not issues or not repairs):
        raise WritingEvalReviewError(
            f"{label} FINDING requires diagnosis and repair technique"
        )
    if verdict != "FINDING" and (issues or repairs):
        raise WritingEvalReviewError(
            f"{label} non-Finding cannot declare diagnosis or repair technique"
        )
    if visual:
        pairs = item.get("visual_pair_refs")
        if not isinstance(pairs, list):
            raise WritingEvalReviewError("visual_pair_refs must be a list")
        validated_pairs: list[dict[str, Any]] = []
        for index, raw in enumerate(pairs):
            pair = _closed(raw, VISUAL_PAIR_FIELDS, f"visual_pair_refs[{index}]")
            validated_pairs.append(
                {
                    "svg_ref": deepcopy(_exact_ref(pair.get("svg_ref"), "svg_ref")),
                    "png_ref": deepcopy(_exact_ref(pair.get("png_ref"), "png_ref")),
                }
            )
        observation = item.get("observation_status")
        if verdict == "NOT_NEEDED":
            if observation != "NOT_NEEDED" or validated_pairs or expected_visual_pairs:
                raise WritingEvalReviewError(
                    "visual NOT_NEEDED requires no reader-visible visual pair"
                )
        elif verdict == "PASS":
            if (
                not expected_visual_pairs
                or validated_pairs != expected_visual_pairs
                or observation != "OBSERVED"
            ):
                raise WritingEvalReviewError(
                    "visual PASS must observe every exact reader-visible visual pair"
                )
        else:
            expected_observation = (
                "OBSERVED" if expected_visual_pairs else "NOT_OBSERVED"
            )
            if (
                validated_pairs != expected_visual_pairs
                or observation != expected_observation
            ):
                raise WritingEvalReviewError(
                    "visual FINDING must truthfully bind observed or missing visuals"
                )
    return issues, repairs, verdict == "FINDING"


def validate_writing_eval_review(
    project_root: Path,
    value: Any,
    *,
    dispatch: dict[str, Any],
    checkpoint_ref: dict[str, Any],
    expected_visual_pairs: list[dict[str, Any]],
    candidate_bytes: bytes,
) -> dict[str, Any]:
    """Validate exact authority and shape without judging whether prose is good."""

    result = _closed(value, RESULT_FIELDS, "writing_eval_result")
    context = dispatch["writing_eval_context"]
    exact_values = {
        "schema_version": SCHEMA_VERSION,
        "evaluation_only": True,
        "authority": "ADVISORY_ONLY",
        "suite_id": context["suite_id"],
        "case_id": context["case_id"],
        "node_id": "writing-eval.review",
        "attempt_id": dispatch["attempt_id"],
        "instruction_ref": dispatch["instruction_ref"],
        "instruction_hash": dispatch["instruction_hash"],
        "input_refs": dispatch["input_refs"],
        "input_hashes": dispatch["input_hashes"],
        "preregistration_checkpoint_ref": checkpoint_ref,
        "candidate_ref": context["candidate_ref"],
        "profile_ref": context["profile_ref"],
        "guide_ref": context["guide_ref"],
        "reviewer_resource_ref": context["reviewer_resource_ref"],
        "output_contract_ref": context["output_contract_ref"],
        "author_execution_ref": context["author_execution_ref"],
        "reviewer_role": "writing_standard",
        "isolated_input_refs": context["isolated_input_refs"],
        "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
    }
    for field, expected in exact_values.items():
        if result.get(field) != expected:
            raise WritingEvalReviewError(
                f"writing_eval_result.{field} differs from exact dispatch authority"
            )
    candidate_ref = _exact_ref(result.get("candidate_ref"), "candidate_ref")
    try:
        assert_managed_path(
            project_root.resolve(), project_root.resolve() / candidate_ref["path"]
        )
    except IntegrityError as error:
        raise WritingEvalReviewError("Candidate path escapes the Eval workspace") from error
    if (
        not isinstance(candidate_bytes, bytes)
        or sha256_bytes(candidate_bytes) != candidate_ref["hash"]
    ):
        raise WritingEvalReviewError("Candidate bytes no longer match exact dispatch")
    try:
        line_count = max(1, len(candidate_bytes.decode("utf-8").splitlines()))
    except UnicodeError as error:
        raise WritingEvalReviewError("Candidate is not readable exact UTF-8 Markdown") from error

    author = _execution_ref(result.get("author_execution_ref"), "author_execution_ref")
    reviewer = _execution_ref(
        result.get("reviewer_execution_ref"), "reviewer_execution_ref"
    )
    if reviewer["kind"] != "HOST_SUBAGENT_ATTEMPT" or reviewer["id"] == author["id"]:
        raise WritingEvalReviewError(
            "Writing Eval requires a distinct HOST_SUBAGENT_ATTEMPT reviewer"
        )

    readback = _closed(result.get("reader_readback"), READBACK_FIELDS, "reader_readback")
    for field in (
        "problem_and_outcome",
        "primary_relationships",
        "main_path_and_recovery",
        "decision_conditions_and_risks",
    ):
        _text(readback.get(field), f"reader_readback.{field}")
    mental_model = readback.get("mental_model")
    if not isinstance(mental_model, list) or not 3 <= len(mental_model) <= 5:
        raise WritingEvalReviewError("mental_model requires three to five components")
    names: list[str] = []
    for index, raw in enumerate(mental_model):
        item = _closed(raw, MENTAL_MODEL_FIELDS, f"mental_model[{index}]")
        names.append(_text(item.get("name"), f"mental_model[{index}].name"))
        _text(item.get("role"), f"mental_model[{index}].role")
    if len(names) != len(set(names)):
        raise WritingEvalReviewError("mental_model component names must be unique")
    navigation = readback.get("navigation_map")
    if not isinstance(navigation, list):
        raise WritingEvalReviewError("navigation_map must be a list")
    targets: list[str] = []
    for index, raw in enumerate(navigation):
        item = _closed(raw, NAVIGATION_FIELDS, f"navigation_map[{index}]")
        targets.append(_text(item.get("target"), f"navigation_map[{index}].target"))
        _text(item.get("location"), f"navigation_map[{index}].location")
    if len(targets) != len(set(targets)) or set(targets) != NAVIGATION_TARGETS:
        raise WritingEvalReviewError("navigation_map must cover all three targets once")

    failures = result.get("reader_outcome_failures")
    if not isinstance(failures, list):
        raise WritingEvalReviewError("reader_outcome_failures must be a list")
    failure_outcomes: list[str] = []
    for index, raw in enumerate(failures):
        item = _closed(raw, FAILURE_FIELDS, f"reader_outcome_failures[{index}]")
        if item.get("outcome") not in READER_OUTCOMES:
            raise WritingEvalReviewError(f"reader_outcome_failures[{index}].outcome is invalid")
        failure_outcomes.append(item["outcome"])
        _text(item.get("reason"), f"reader_outcome_failures[{index}].reason")
        _basis_refs(
            item.get("basis_refs"),
            label=f"reader_outcome_failures[{index}].basis_refs",
            candidate_ref=candidate_ref,
            line_count=line_count,
        )
    if len(failure_outcomes) != len(set(failure_outcomes)):
        raise WritingEvalReviewError("reader_outcome_failures must be unique")

    diagnosis: set[str] = set()
    repairs: set[str] = set()
    finding_assessments = False
    for field in ("verbosity_assessment", "checklist_assessment", "visual_assessment"):
        found_issues, found_repairs, is_finding = _assessment(
            result.get(field),
            label=field,
            candidate_ref=candidate_ref,
            line_count=line_count,
            expected_visual_pairs=expected_visual_pairs,
        )
        diagnosis.update(found_issues)
        repairs.update(found_repairs)
        finding_assessments = finding_assessments or is_finding
    verdict = result.get("result")
    if verdict not in {"PASS", "FINDING"}:
        raise WritingEvalReviewError("result must be PASS or FINDING")
    primary_diagnosis = result.get("primary_diagnosis")
    primary_repair = result.get("primary_repair_technique")
    has_failure = bool(failure_outcomes or finding_assessments)
    if verdict == "PASS":
        if has_failure or primary_diagnosis is not None or primary_repair is not None:
            raise WritingEvalReviewError("PASS cannot carry failures or primary repair")
    else:
        if not has_failure:
            raise WritingEvalReviewError("FINDING requires at least one observed failure")
        if primary_diagnosis not in diagnosis or primary_repair not in repairs:
            raise WritingEvalReviewError(
                "FINDING primary diagnosis and repair must come from its assessments"
            )
    return deepcopy(result)
