"""Validation and assembly metadata for Agent-authored PRDs; never writes product content."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from .contracts import PolicyViolation, validate_node_result_producer
from .delivery_contract import DeliveryContractError, validate_candidate_delivery_contract
from .templates import TemplateSelection, load_output_contract


EXPERIMENT_FIELDS = (
    "key_unknown",
    "hypothesis",
    "audience_exposure",
    "specific_change",
    "observable_measurement",
    "result_mapping",
    "monitoring",
    "kill_rollback",
    "owner",
    "end_time",
    "harm_guardrails",
)
SAFE_SHORT_TITLE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(r"^v\d+\.\d+(?:\.\d+)?$")
SAFE_STEM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$")
TABLE_DELIMITER_CELL = re.compile(r"^:?-{3,}:?$")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
H1 = re.compile(r"^ {0,3}# (.+?)\s*$")
H2 = re.compile(r"^ {0,3}## (.+?)\s*$")


class PRDContractError(ValueError):
    """An Agent PRD submission is missing exact content or mechanical bindings."""


@dataclass(frozen=True)
class AssembledPRD:
    markdown: str
    metadata: dict[str, Any]

    def with_markdown(self, markdown: str) -> "AssembledPRD":
        return replace(self, markdown=markdown)


def _validate_ref(ref: Any, label: str, issues: list[str]) -> None:
    if not isinstance(ref, dict):
        issues.append(f"{label} exact ref is required")
        return
    path = ref.get("path")
    if not isinstance(path, str) or not path.strip():
        issues.append(f"{label} path is required")
    elif any(
        part.lower().split(".", 1)[0] in {"latest", "current"}
        for part in path.replace("\\", "/").split("/")
    ):
        issues.append(f"{label} cannot use latest/current")
    if not isinstance(ref.get("hash"), str) or not ref["hash"].startswith("sha256:"):
        issues.append(f"{label} hash is required")
    if not isinstance(ref.get("version"), (int, str)):
        issues.append(f"{label} version is required")


def _validate_distinct_upstream_refs(refs: list[Any], issues: list[str]) -> None:
    seen: set[tuple[Any, Any, Any]] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        identity = (ref.get("path"), ref.get("hash"), ref.get("version"))
        if any(value in (None, "") for value in identity):
            continue
        if identity in seen:
            issues.append(f"duplicate exact upstream ref: {identity[0]}")
        seen.add(identity)


def next_prd_version(version: str) -> str:
    """Return the one exact visible version allowed for the next material Candidate."""

    if VERSION.fullmatch(version) is None:
        raise PRDContractError("source Candidate version is not a visible semantic version")
    parts = [int(part) for part in version.removeprefix("v").split(".")]
    parts[-1] += 1
    return "v" + ".".join(str(part) for part in parts)


def prd_stem(prd_id: str, short_title: str, version: str, document_date: str) -> str:
    """Return the one immutable Markdown filename stem for a PRD identity."""

    visible_version = version.removeprefix("v")
    stem = f"{prd_id}_{short_title}_v{visible_version}_{document_date}"
    if SAFE_STEM.fullmatch(stem) is None:
        raise PRDContractError("PRD identity does not form a safe immutable filename stem")
    return stem


def _markdown_lines_outside_fences(markdown: str) -> list[str]:
    visible: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in markdown.splitlines():
        if fence_character is not None:
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            run = len(stripped) - len(stripped.lstrip(fence_character))
            if indent <= 3 and run >= fence_length and not stripped[run:].strip():
                fence_character = None
                fence_length = 0
            continue
        opening = FENCE_OPEN.match(line)
        if opening is not None:
            marker = opening.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        visible.append(line)
    return visible


def _h1_titles(markdown: str) -> list[str]:
    return [match.group(1).strip() for line in _markdown_lines_outside_fences(markdown) if (match := H1.match(line))]


def _h2_titles(markdown: str) -> list[str]:
    return [match.group(1).strip() for line in _markdown_lines_outside_fences(markdown) if (match := H2.match(line))]


def _table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _has_empty_markdown_table(markdown: str) -> bool:
    lines = _markdown_lines_outside_fences(markdown)
    for index in range(1, len(lines)):
        header = _table_cells(lines[index - 1])
        delimiter = _table_cells(lines[index])
        if (
            not header
            or not delimiter
            or len(header) != len(delimiter)
            or not all(TABLE_DELIMITER_CELL.fullmatch(cell) for cell in delimiter)
        ):
            continue
        rows: list[list[str]] = []
        cursor = index + 1
        while cursor < len(lines):
            cells = _table_cells(lines[cursor])
            if cells is None:
                break
            rows.append(cells)
            cursor += 1
        if not rows or not any(any(cell for cell in row) for row in rows):
            return True
    return False


def _section_bodies(markdown: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    fence_character: str | None = None
    fence_length = 0
    for line in markdown.splitlines():
        if fence_character is not None:
            if current is not None:
                sections[current].append(line)
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            run = len(stripped) - len(stripped.lstrip(fence_character))
            if indent <= 3 and run >= fence_length and not stripped[run:].strip():
                fence_character = None
                fence_length = 0
            continue
        opening = FENCE_OPEN.match(line)
        if opening is not None:
            if current is not None:
                sections[current].append(line)
            marker = opening.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        heading = H2.match(line)
        if heading is not None:
            current = heading.group(1).strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return sections


def _has_substantive_section_content(lines: list[str], policy: str) -> bool:
    visible: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    fenced_content = False
    for line in lines:
        if fence_character is not None:
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            run = len(stripped) - len(stripped.lstrip(fence_character))
            if indent <= 3 and run >= fence_length and not stripped[run:].strip():
                fence_character = None
                fence_length = 0
            elif line.strip():
                fenced_content = True
            continue
        opening = FENCE_OPEN.match(line)
        if opening is not None:
            marker = opening.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        visible.append(line)
    if fenced_content:
        return True
    body = "\n".join(visible)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    body = re.sub(r"^[ \t]*(?:[-*_][ \t]*){3,}$", "", body, flags=re.MULTILINE)
    body = re.sub(r"[`*_>#\[\]()]", "", body)
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", body).lower()
    if not normalized:
        return False
    if policy == "OMIT_OR_EXPLAIN_NOT_APPLICABLE" and normalized in {
        "不适用",
        "无",
        "暂无",
        "na",
        "none",
        "notapplicable",
    }:
        return False
    return True


def _validate_conditional_sections(
    markdown: str, conditional: dict[str, str], issues: list[str]
) -> None:
    sections = _section_bodies(markdown)
    for heading, policy in conditional.items():
        if heading in sections and not _has_substantive_section_content(sections[heading], policy):
            issues.append(
                f"conditional section has no substantive content and should be omitted: {heading}"
            )


def validate_final_markdown(
    markdown: str,
    metadata: dict[str, Any],
    *,
    require_stem_identity: bool = True,
) -> list[str]:
    """Validate byte-level rules that must hold at assembly and again at archive."""

    issues: list[str] = []
    if "{{" in markdown or "}}" in markdown or "TBD" in markdown:
        issues.append("template placeholder remains in Agent-authored PRD")
    identity = [metadata.get(key) for key in ("prd_id", "short_title", "version", "date")]
    if require_stem_identity and all(isinstance(value, str) and value for value in identity):
        try:
            expected = prd_stem(*identity)
        except PRDContractError as error:
            issues.append(str(error))
        else:
            titles = _h1_titles(markdown)
            if titles != [expected]:
                issues.append(
                    "unique Markdown H1 identity must exactly equal archive filename stem"
                )
    if _has_empty_markdown_table(markdown):
        issues.append("empty Markdown table remains in Agent-authored PRD")
    return issues


def _validate_output_shape(
    markdown: str,
    mapping: Any,
    structure_mode: Any,
    template: TemplateSelection,
    issues: list[str],
) -> str | None:
    contract = load_output_contract(template)
    modes = contract["allowed_structure_modes"]
    if structure_mode is None:
        visible_headings = set(_h2_titles(markdown))
        legacy_required = {
            "阅读摘要",
            "目标与成功边界",
            "范围与交付切片",
            "验收标准",
            "风险、未知与回滚",
            "版本与变更",
        }
        if "legacy" in modes and legacy_required.issubset(visible_headings):
            structure_mode = "legacy"
        elif modes == ["legacy"]:
            structure_mode = "legacy"
    if structure_mode not in modes:
        issues.append("structure_mode is not allowed by the exact output contract")
        return None
    headings = _h2_titles(markdown)
    duplicates = sorted({heading for heading in headings if headings.count(heading) > 1})
    if duplicates:
        issues.append("duplicate H2 headings are not allowed: " + ", ".join(duplicates))
    shape = contract["structures"][structure_mode]
    required = [*contract["common_required_h2"], *shape["required_h2"]]
    for heading in required:
        if headings.count(heading) != 1:
            issues.append(f"required heading missing or duplicated: {heading}")
    for heading in shape["forbidden_h2"]:
        if heading in headings:
            issues.append(f"heading forbidden for structure_mode={structure_mode}: {heading}")
    order = shape.get("h2_order")
    if isinstance(order, list):
        known = [heading for heading in headings if heading in order]
        if known != [heading for heading in order if heading in headings]:
            issues.append("H2 heading order differs from the exact output contract")
        unknown = [heading for heading in headings if heading not in order]
        if unknown:
            issues.append("H2 heading is not declared by the exact output contract: " + ", ".join(unknown))
    _validate_conditional_sections(markdown, contract["conditional_sections"], issues)
    semantics = {
        **contract["common_required_semantics"],
        **shape["required_semantics"],
    }
    if not isinstance(mapping, dict) or not mapping:
        issues.append("Agent template_mapping is required")
    else:
        for key, allowed_headings in semantics.items():
            mapped = mapping.get(key)
            if mapped not in allowed_headings or mapped not in headings:
                issues.append(f"template_mapping.{key} does not bind a required output heading")
        for key, mapped in mapping.items():
            if not isinstance(key, str) or not isinstance(mapped, str) or mapped not in headings:
                issues.append("template_mapping points to a missing Agent-authored heading")
                break
    return structure_mode


def assemble_prd(submission: dict[str, Any], template: TemplateSelection) -> AssembledPRD:
    node_id = submission.get("node_id")
    if node_id not in {"prd.generate", "prd.optimize"}:
        raise PRDContractError("prd.generate or prd.optimize HOST_AGENT submission is required")
    try:
        validate_node_result_producer(submission)
    except PolicyViolation as error:
        raise PRDContractError(str(error)) from error
    output = submission.get("semantic_output")
    if not isinstance(output, dict):
        raise PRDContractError("Agent-authored semantic_output is required")
    markdown = output.get("document_markdown")
    issues: list[str] = []
    if not isinstance(markdown, str) or not markdown.strip():
        issues.append("Agent-authored document_markdown is required")
        markdown = ""
    mapping = output.get("template_mapping")
    metadata = output.get("metadata")
    if not isinstance(metadata, dict):
        issues.append("Agent PRD metadata is required")
        metadata = {}
    for field in ("prd_id", "short_title", "version", "date", "status", "delivery_intent"):
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            issues.append(f"metadata.{field} is required")
    if isinstance(metadata.get("short_title"), str) and SAFE_SHORT_TITLE.fullmatch(metadata["short_title"]) is None:
        issues.append("metadata.short_title must be a path-safe lowercase slug")
    if isinstance(metadata.get("version"), str) and VERSION.fullmatch(metadata["version"]) is None:
        issues.append("metadata.version must be a visible v-prefixed semantic version")
    if isinstance(metadata.get("date"), str):
        try:
            if date.fromisoformat(metadata["date"]).isoformat() != metadata["date"]:
                raise ValueError
        except ValueError:
            issues.append("metadata.date must be an ISO calendar date")
    structure_mode = _validate_output_shape(
        markdown,
        mapping,
        output.get("structure_mode"),
        template,
        issues,
    )
    issues.extend(
        validate_final_markdown(
            markdown,
            metadata,
            require_stem_identity=structure_mode != "legacy",
        )
    )
    if metadata.get("status") != "CANDIDATE":
        issues.append("Agent PRD status must be CANDIDATE before Ready")
    if metadata.get("delivery_intent") not in {"COMMIT", "EXPERIMENT"}:
        issues.append("delivery_intent must be COMMIT or EXPERIMENT")
    decision_refs = metadata.get("decision_refs")
    if not isinstance(decision_refs, list) or not decision_refs:
        issues.append("decision_refs are required")
    else:
        for index, ref in enumerate(decision_refs):
            _validate_ref(ref, f"decision_refs[{index}]", issues)
    for field in (
        "roadmap_snapshot_ref",
        "product_plan_ref",
        "slice_ref",
        "knowledge_snapshot_ref",
    ):
        _validate_ref(metadata.get(field), field, issues)
    evidence_refs = metadata.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        issues.append("evidence_refs must be a list")
    else:
        for index, ref in enumerate(evidence_refs):
            _validate_ref(ref, f"evidence_refs[{index}]", issues)
    _validate_distinct_upstream_refs(
        [
            *(decision_refs if isinstance(decision_refs, list) else []),
            metadata.get("roadmap_snapshot_ref"),
            metadata.get("product_plan_ref"),
            metadata.get("slice_ref"),
            metadata.get("knowledge_snapshot_ref"),
            *(evidence_refs if isinstance(evidence_refs, list) else []),
        ],
        issues,
    )
    evals = metadata.get("evals")
    if not isinstance(evals, dict) or evals.get("applicability") not in {
        "NOT_NEEDED",
        "RECOMMENDED",
        "REQUIRED",
    }:
        issues.append("Eval Applicability contract is required")
    elif node_id == "prd.generate" and evals.get("fulfillment") == "REVIEWED":
        issues.append(
            "prd.generate cannot self-claim REVIEWED Evals; verifiable fulfillment authority "
            "is unavailable in the current release, so REQUIRED Evals must remain "
            "REVIEW_PENDING/NOT_RUN"
        )
    if metadata.get("delivery_intent") == "EXPERIMENT":
        experiment = metadata.get("experiment_contract")
        if not isinstance(experiment, dict) or any(not experiment.get(field) for field in EXPERIMENT_FIELDS):
            issues.append("complete Agent-authored experiment_contract is required")
    try:
        validate_candidate_delivery_contract(metadata)
    except DeliveryContractError as error:
        issues.append(str(error))
    if issues:
        raise PRDContractError("; ".join(issues))
    assembled_metadata = {
        **metadata,
        "structure_mode": structure_mode,
        "template_mapping": mapping,
        "template_profile": {
            "id": template.profile_id,
            "version": template.version,
            "status": template.status,
            "source_kind": template.origin,
            "path": template.reference_path,
            "sha256": template.sha256,
            "selection_source": template.selection_source,
            "fallback_reason": template.fallback_reason,
            "requested_profile_id": template.requested_profile_id,
            "requested_version": template.requested_version,
            "output_contract": {
                "path": template.output_contract_reference_path,
                "sha256": template.output_contract_sha256,
                "version": template.output_contract_version,
            },
        },
        "provenance": {
            "attempt_id": submission["attempt_id"],
            "instruction_ref": submission["instruction_ref"],
            "instruction_hash": submission["instruction_hash"],
            "input_refs": submission["input_refs"],
            "input_hashes": submission["input_hashes"],
        },
    }
    return AssembledPRD(markdown, assembled_metadata)
