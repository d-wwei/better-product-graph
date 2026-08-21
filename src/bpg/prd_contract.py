"""Validation and assembly metadata for Agent-authored PRDs; never writes product content."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from .contracts import PolicyViolation, validate_node_result_producer
from .delivery_contract import DeliveryContractError, validate_candidate_delivery_contract
from .templates import TemplateSelection


REQUIRED_HEADINGS = (
    "阅读摘要",
    "目标与成功边界",
    "范围与交付切片",
    "验收标准",
    "风险、未知与回滚",
    "版本与变更",
)
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
    if "{{" in markdown or "}}" in markdown or "TBD" in markdown:
        issues.append("template placeholder remains in Agent-authored PRD")
    for heading in REQUIRED_HEADINGS:
        if f"## {heading}" not in markdown:
            issues.append(f"required heading missing: {heading}")
    mapping = output.get("template_mapping")
    if not isinstance(mapping, dict) or not mapping:
        issues.append("Agent template_mapping is required")
    elif any(f"## {heading}" not in markdown for heading in mapping.values()):
        issues.append("template_mapping points to a missing Agent-authored heading")
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
            "is unavailable in 0.1.20, so REQUIRED Evals must remain REVIEW_PENDING/NOT_RUN"
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
        "template_mapping": mapping,
        "template_profile": {
            "id": template.profile_id,
            "version": template.version,
            "status": template.status,
            "path": f"references/templates/{template.relative_path}",
            "sha256": template.sha256,
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
