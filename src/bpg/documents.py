"""Immutable PRD archive/release mechanics and cross-cutting document validation."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from functools import wraps
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from .prd_contract import AssembledPRD, PRDContractError, prd_stem, validate_final_markdown
from .locking import exclusive_file_lock
from .storage import (
    assert_managed_path,
    append_event,
    atomic_write_bytes,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
)
from .product_navigation import requirement_relationships, update_release_manifest
from .visual_assets import (
    VisualAssetError,
    inspect_reader_visible_visual_assets,
    validate_managed_visual_asset_tree,
)


ASSET_REF = re.compile(r"\]\(\./assets/([^)]+)\)")
EXTERNAL_SUCCESS = re.compile(r"(?<!未)(?:已发送|已接收|已批准|已通过外部审批)")
SUMMARY_HEADING = re.compile(
    r"^#{2,3}\s*(?:阅读摘要|执行摘要|摘要|概览|tl;dr|executive summary|summary)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
LEADING_DECISION = re.compile(
    r"(?:^|\n)\s*(?:[-*]\s*)?(?:\*\*)?(?:结论|当前判断|我们建议|recommendation)\b",
    re.IGNORECASE,
)
NEXT_ACTION = re.compile(
    r"(?:下一步|下一动作|建议动作|next\s+(?:step|action)|recommended\s+action)",
    re.IGNORECASE,
)

CONTROLLED_LIFECYCLE_LABELS = {
    "review": re.compile(r"(?:当前\s*)?(?:Review|审查)\s*状态", re.IGNORECASE),
    "eval_fulfillment": re.compile(
        r"(?:Product\s*)?Evals?\s*(?:准备|履行|fulfillment)\s*状态|Eval\s*Pack\s*状态",
        re.IGNORECASE,
    ),
    "eval_execution": re.compile(
        r"(?:Product\s*)?Evals?\s*(?:执行|execution)\s*状态", re.IGNORECASE
    ),
    "remote_handoff": re.compile(
        r"(?:远程交付|远程发送|remote\s*(?:delivery|handoff))\s*状态",
        re.IGNORECASE,
    ),
}


class ImmutableArtifactError(RuntimeError):
    """An immutable archive/release would be overwritten or is not self-contained."""


@dataclass(frozen=True)
class ArtifactSet:
    path: Path
    document_path: Path
    document_hash: str
    tree_hash: str
    prd_id: str
    version: str
    status: str
    short_title: str
    date: str
    review_path: Path
    review_hash: str


@dataclass(frozen=True)
class DocumentExperienceResult:
    status: str
    issues: list[str]


def _serialized_prd_mutation(function):
    @wraps(function)
    def wrapped(project_root: Path, *args, **kwargs):
        root = project_root.resolve()
        lock = assert_managed_path(
            root, root / ".better-product-graph" / "locks" / "prd-artifacts.lock"
        )
        with exclusive_file_lock(lock):
            return function(root, *args, **kwargs)

    return wrapped


def validate_document_experience(markdown: str, profile: str) -> DocumentExperienceResult:
    issues: list[str] = []
    if profile not in {
        "problem",
        "decision",
        "plan",
        "prd",
        "incident",
        "bug",
        "internal_review",
        "handoff",
    }:
        return DocumentExperienceResult("FAIL", ["unknown_profile"])
    first_lines = "\n".join(markdown.splitlines()[:20])
    if not (SUMMARY_HEADING.search(first_lines) or LEADING_DECISION.search(first_lines)):
        issues.append("conclusion_first")
    if not NEXT_ACTION.search(first_lines):
        issues.append("next_action_visible")
    if not any(token in markdown for token in ("证据", "Evidence", "evidence")):
        issues.append("evidence_boundary")
    if not any(token in markdown for token in ("未知", "Unknown", "unknown")):
        issues.append("unknown_boundary")
    if not any(token in markdown for token in ("Authority", "authority", "授权", "权限")):
        issues.append("authority_boundary")
    if not any(token in markdown for token in ("版本", " v0.", " v1.")):
        issues.append("version_visible")
    visible_headings = {
        line.lstrip("# ").strip().casefold()
        for line in markdown.splitlines()
        if line.lstrip().startswith("#")
    }
    prd_changelog_visible = "DOCUMENT_CHANGELOG" in markdown or bool(
        visible_headings
        & {
            "一、变更日志",
            "附录 c：文档变更日志",
            "附录 c: 文档变更日志",
            "changelog",
            "change log",
        }
    )
    if profile == "prd" and not prd_changelog_visible:
        issues.append("changelog_visible")
    if profile in {"handoff", "internal_review", "incident", "bug"} and EXTERNAL_SUCCESS.search(markdown):
        issues.append("external_claim_language")
    if profile in {"incident", "bug"} and len(markdown.splitlines()) > 40:
        issues.append("minimal_actionable_length")
    return DocumentExperienceResult("FAIL" if issues else "PASS", issues)


def validate_lifecycle_expression_reconciliation(
    markdown: str, *, authoritative: dict[str, Any]
) -> list[str]:
    """Compare only registered lifecycle statement rows with Controller facts."""

    controlled: dict[str, list[str]] = {key: [] for key in CONTROLLED_LIFECYCLE_LABELS}
    for line in markdown.splitlines():
        for key, label in CONTROLLED_LIFECYCLE_LABELS.items():
            if label.search(line):
                controlled[key].append(line)
    issues: list[str] = []
    if authoritative.get("review_status") == "FINALIZED" and any(
        re.search(r"REVIEW_PENDING|待\s*Review|待审查|尚未审查", line, re.IGNORECASE)
        for line in controlled["review"]
    ):
        issues.append("review_status_conflict")
    if authoritative.get("eval_fulfillment") == "REVIEWED" and any(
        re.search(
            r"REVIEW_PENDING|尚未生成|待生成|尚未开始|已生成待审|NOT_GENERATED",
            line,
            re.IGNORECASE,
        )
        for line in controlled["eval_fulfillment"]
    ):
        issues.append("eval_fulfillment_status_conflict")
    if authoritative.get("eval_execution_status") == "NOT_RUN" and any(
        re.search(r"(?<![A-Z_])(?:PASS|FAIL|PASSED|FAILED)(?![A-Z_])|已通过|未通过", line, re.IGNORECASE)
        for line in controlled["eval_execution"]
    ):
        issues.append("eval_execution_status_conflict")
    if authoritative.get("remote_handoff_status") not in {
        "SENT",
        "RECEIVED",
        "APPROVED",
    } and any(
        re.search(r"已发送|已接收|已批准|\bSENT\b|\bRECEIVED\b|\bAPPROVED\b", line, re.IGNORECASE)
        for line in controlled["remote_handoff"]
    ):
        issues.append("remote_handoff_status_conflict")
    return issues


def hash_tree(root: Path) -> str:
    records = [
        {
            "path": path.relative_to(root).as_posix(),
            "hash": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    return sha256_bytes(canonical_json_bytes(records))


def _safe_asset_name(name: str) -> PurePosixPath:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ImmutableArtifactError(f"unsafe asset name: {name}")
    return pure


def _visual_contract_enabled(metadata: dict[str, Any]) -> bool:
    document_experience = metadata.get("document_experience")
    if not isinstance(document_experience, dict):
        return False
    profile_ref = document_experience.get("profile_ref")
    if not isinstance(profile_ref, dict):
        return False
    version = profile_ref.get("version")
    if not isinstance(version, str):
        return False
    try:
        parts = tuple(int(item) for item in version.split("."))
    except ValueError:
        return False
    return len(parts) == 3 and parts >= (0, 4, 0)


def _validate_assets(
    markdown: str, assets: dict[str, bytes], *, metadata: dict[str, Any]
) -> None:
    referenced = set(ASSET_REF.findall(markdown))
    provided = set(assets)
    for name in provided:
        _safe_asset_name(name)
    missing = referenced - provided
    if missing:
        raise ImmutableArtifactError("missing referenced assets: " + ", ".join(sorted(missing)))
    if _visual_contract_enabled(metadata):
        try:
            validate_managed_visual_asset_tree(markdown, assets)
        except VisualAssetError as error:
            raise ImmutableArtifactError(str(error)) from error


def _append_changelog(project_root: Path, line: str) -> None:
    path = assert_managed_path(
        project_root, project_root / "artifacts" / "prds" / "DOCUMENT_CHANGELOG.md"
    )
    lock = assert_managed_path(
        project_root, project_root / ".better-product-graph" / "locks" / "document-changelog.lock"
    )
    with exclusive_file_lock(lock):
        existing = path.read_text(encoding="utf-8") if path.exists() else "# PRD Document Changelog\n\n"
        if line.rstrip() in existing.splitlines():
            return
        atomic_write_bytes(path, (existing.rstrip() + "\n" + line.rstrip() + "\n").encode())


def validate_archived_visual_delivery(
    project_root: Path, archived: ArtifactSet
) -> list[dict[str, Any]]:
    """Enforce the active Profile's visual delivery contract before Ready/Release."""

    metadata_paths = list(archived.path.glob("*.metadata.json"))
    if len(metadata_paths) != 1:
        raise ImmutableArtifactError("archived Candidate metadata is ambiguous")
    metadata = read_json(metadata_paths[0])
    if not _visual_contract_enabled(metadata):
        return []
    try:
        return inspect_reader_visible_visual_assets(
            project_root.resolve(), archived.document_path
        )
    except VisualAssetError as error:
        raise ImmutableArtifactError(str(error)) from error


def _stem(prd_id: str, short_title: str, version: str, document_date: str) -> str:
    try:
        return prd_stem(prd_id, short_title, version, document_date)
    except PRDContractError as error:
        raise ImmutableArtifactError(str(error)) from error


def _document_policy_ref() -> dict[str, Any]:
    module = Path(__file__).resolve()
    candidates = (
        module.parents[1] / "core" / "policies" / "document-experience.json",
        module.parents[2] / "references" / "policies" / "document-experience.json",
    )
    for path in candidates:
        if path.is_file() and not path.is_symlink():
            return {
                "path": "references/policies/document-experience.json",
                "hash": sha256_file(path),
                "version": "v1",
            }
    raise ImmutableArtifactError("Document Experience policy is missing")


def _upstream_refs(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    refs.extend({"kind": "decision", **ref} for ref in metadata["decision_refs"])
    mapping = (
        ("roadmap", "roadmap_snapshot_ref"),
        ("product_plan", "product_plan_ref"),
        ("slice", "slice_ref"),
        ("knowledge", "knowledge_snapshot_ref"),
    )
    refs.extend({"kind": kind, **metadata[field]} for kind, field in mapping)
    refs.extend({"kind": "evidence", **ref} for ref in metadata["evidence_refs"])
    return refs


def _review_companion(
    assembled: AssembledPRD,
    candidate_hash: str,
    supplied: dict[str, Any] | None,
) -> dict[str, Any]:
    companion = supplied or {
        "schema_version": "prd-review-companion.v1",
        "prd_id": assembled.metadata["prd_id"],
        "version": assembled.metadata["version"],
        "candidate_hash": candidate_hash,
        "status": "NOT_RUN",
        "authority": "ADVISORY_ONLY",
        "finding_count": 0,
    }
    if (
        not isinstance(companion, dict)
        or companion.get("schema_version") != "prd-review-companion.v1"
        or companion.get("prd_id") != assembled.metadata["prd_id"]
        or companion.get("version") != assembled.metadata["version"]
        or companion.get("candidate_hash") != candidate_hash
        or companion.get("authority") != "ADVISORY_ONLY"
        or not isinstance(companion.get("finding_count"), int)
    ):
        raise ImmutableArtifactError("Review companion must bind the exact PRD id/version/Candidate")
    return json.loads(canonical_json_bytes(companion))


def _asset_refs(root: Path, artifact_path: Path) -> list[dict[str, Any]]:
    assets = artifact_path / "assets"
    if not assets.is_dir():
        return []
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "hash": sha256_file(path),
        }
        for path in sorted(assets.rglob("*"))
        if path.is_file()
    ]


def _structured_changelog_event(
    root: Path,
    artifact: ArtifactSet,
    metadata: dict[str, Any],
    *,
    status: str,
    ready_ref: dict[str, Any] | None,
    lifecycle_refs: dict[str, Any] | None,
) -> dict[str, Any]:
    lifecycle_refs = lifecycle_refs or {}
    return {
        "event_id": f"product-document:{artifact.path.name}:{status}",
        "event_type": "PRODUCT_DOCUMENT_LIFECYCLE_RECORDED",
        "actor": "state-controller",
        "status": status,
        "prd_id": artifact.prd_id,
        "short_title": artifact.short_title,
        "version": artifact.version,
        "date": artifact.date,
        "artifact_ref": {
            "path": artifact.path.relative_to(root).as_posix(),
            "document_path": artifact.document_path.relative_to(root).as_posix(),
            "document_hash": artifact.document_hash,
            "tree_hash": artifact.tree_hash,
        },
        "upstream_refs": lifecycle_refs.get("upstream_refs") or _upstream_refs(metadata),
        "template_ref": lifecycle_refs.get("template_ref") or {
            "path": metadata["template_profile"]["path"],
            "hash": metadata["template_profile"]["sha256"],
            "version": metadata["template_profile"]["version"],
            "profile_id": metadata["template_profile"]["id"],
            "source_kind": metadata["template_profile"]["source_kind"],
            "selection_source": metadata["template_profile"]["selection_source"],
            "fallback_reason": metadata["template_profile"].get("fallback_reason"),
            "requested_profile_id": metadata["template_profile"].get(
                "requested_profile_id"
            ),
            "requested_version": metadata["template_profile"].get("requested_version"),
            "output_contract": metadata["template_profile"]["output_contract"],
        },
        "policy_ref": _document_policy_ref(),
        "document_experience_ref": metadata.get("document_experience"),
        "review_ref": lifecycle_refs.get("review_ref") or {
            "path": artifact.review_path.relative_to(root).as_posix(),
            "hash": artifact.review_hash,
            "version": artifact.version,
        },
        "ready_ref": ready_ref or {"status": "NOT_AVAILABLE_BEFORE_READY"},
        "asset_refs": _asset_refs(root, artifact.path),
        "supersedes": metadata.get("supersedes"),
        "requirement_relationships": requirement_relationships(metadata),
    }


def _append_structured_changelog(
    root: Path,
    artifact: ArtifactSet,
    metadata: dict[str, Any],
    *,
    status: str,
    ready_ref: dict[str, Any] | None = None,
    lifecycle_refs: dict[str, Any] | None = None,
) -> None:
    append_event(
        root / "artifacts" / "prds" / "PRODUCT_DOCUMENT_CHANGELOG.jsonl",
        _structured_changelog_event(
            root,
            artifact,
            metadata,
            status=status,
            ready_ref=ready_ref,
            lifecycle_refs=lifecycle_refs,
        ),
    )


@_serialized_prd_mutation
def archive_prd_candidate(
    project_root: Path,
    assembled: AssembledPRD,
    *,
    assets: dict[str, bytes],
    review_companion: dict[str, Any] | None = None,
    failpoint=None,
) -> ArtifactSet:
    final_issues = validate_final_markdown(
        assembled.markdown,
        assembled.metadata,
        require_stem_identity=True,
    )
    if final_issues:
        raise ImmutableArtifactError("Final PRD Markdown invalid: " + ", ".join(final_issues))
    experience = validate_document_experience(assembled.markdown, "prd")
    if experience.status != "PASS":
        raise ImmutableArtifactError("Document Experience failed: " + ", ".join(experience.issues))
    _validate_assets(assembled.markdown, assets, metadata=assembled.metadata)
    root = project_root.resolve()
    prd_id = assembled.metadata["prd_id"]
    short_title = assembled.metadata["short_title"]
    version = assembled.metadata["version"]
    document_date = assembled.metadata["date"]
    stem = _stem(prd_id, short_title, version, document_date)
    parent = assert_managed_path(root, root / "artifacts" / "prds" / "archived")
    target = assert_managed_path(root, parent / stem)
    document = target / f"{stem}.md"
    metadata_path = target / f"{stem}.metadata.json"
    review_path = target / f"{stem}.review.json"
    candidate_hash = sha256_bytes(assembled.markdown.encode())
    companion = _review_companion(assembled, candidate_hash, review_companion)
    if target.exists():
        expected_assets = {f"assets/{name}" for name in assets}
        actual_assets = {
            path.relative_to(target).as_posix()
            for path in target.rglob("*")
            if path.is_file() and path not in {document, metadata_path, review_path}
        }
        if (
            not document.is_file()
            or document.read_text(encoding="utf-8") != assembled.markdown
            or not metadata_path.is_file()
            or read_json(metadata_path) != assembled.metadata
            or not review_path.is_file()
            or read_json(review_path) != companion
            or actual_assets != expected_assets
            or any((target / "assets" / name).read_bytes() != content for name, content in assets.items())
        ):
            raise ImmutableArtifactError(f"archive identity conflict: {target}")
        artifact = ArtifactSet(
            target, document, sha256_file(document), hash_tree(target), prd_id, version,
            "CANDIDATE_ARCHIVED", short_title, document_date, review_path, sha256_file(review_path),
        )
        _append_changelog(
            root,
            f"- {document_date} | {prd_id} {version} | CANDIDATE_ARCHIVED | "
            f"`{target.relative_to(root)}` | supersedes: "
            f"{assembled.metadata.get('supersedes', 'none')}",
        )
        _append_structured_changelog(root, artifact, assembled.metadata, status="CANDIDATE_ARCHIVED")
        return artifact
    parent.mkdir(parents=True, exist_ok=True)
    temporary = parent / f".{stem}.tmp-{uuid4().hex}"
    try:
        temporary.mkdir()
        document = temporary / f"{stem}.md"
        atomic_write_bytes(document, assembled.markdown.encode())
        atomic_write_json(temporary / f"{stem}.metadata.json", assembled.metadata)
        atomic_write_json(temporary / f"{stem}.review.json", companion)
        if assets:
            for name, content in assets.items():
                asset_path = temporary / "assets" / _safe_asset_name(name)
                atomic_write_bytes(asset_path, content)
        os.replace(temporary, target)
        if failpoint is not None:
            failpoint("after_archive_publish")
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    document = target / f"{stem}.md"
    artifact = ArtifactSet(
        target,
        document,
        sha256_file(document),
        hash_tree(target),
        prd_id,
        version,
        "CANDIDATE_ARCHIVED",
        short_title,
        document_date,
        target / f"{stem}.review.json",
        sha256_file(target / f"{stem}.review.json"),
    )
    _append_changelog(
        root,
        f"- {document_date} | {prd_id} {version} | CANDIDATE_ARCHIVED | "
        f"`{target.relative_to(root)}` | supersedes: "
        f"{assembled.metadata.get('supersedes', 'none')}",
    )
    _append_structured_changelog(root, artifact, assembled.metadata, status="CANDIDATE_ARCHIVED")
    return artifact


@_serialized_prd_mutation
def release_prd_candidate(
    project_root: Path,
    archived: ArtifactSet,
    *,
    ready_assertion: dict[str, Any],
    failpoint=None,
) -> ArtifactSet:
    if archived.status != "CANDIDATE_ARCHIVED" or hash_tree(archived.path) != archived.tree_hash:
        raise ImmutableArtifactError("archived Candidate identity changed")
    if ready_assertion.get("status") != "READY" or ready_assertion.get("candidate_hash") != archived.document_hash:
        raise ImmutableArtifactError("release requires READY Assertion for exact Candidate")
    if ready_assertion.get("review_companion_hash") not in {None, archived.review_hash}:
        raise ImmutableArtifactError("release READY Assertion binds a different Review companion")
    root = project_root.resolve()
    metadata_paths = list(archived.path.glob("*.metadata.json"))
    if len(metadata_paths) != 1:
        raise ImmutableArtifactError("archived Candidate metadata is ambiguous")
    metadata = read_json(metadata_paths[0])
    validate_archived_visual_delivery(root, archived)
    parent = assert_managed_path(root, root / "artifacts" / "prds" / "released")
    target = assert_managed_path(root, parent / archived.path.name)
    if target.exists():
        assertion_path = target / "READY_ASSERTION.json"
        document = target / archived.document_path.name
        source_inventory = {
            path.relative_to(archived.path).as_posix(): sha256_file(path)
            for path in archived.path.rglob("*") if path.is_file()
        }
        released_inventory = {
            path.relative_to(target).as_posix(): sha256_file(path)
            for path in target.rglob("*")
            if path.is_file() and path != assertion_path
        }
        if (
            not assertion_path.is_file()
            or read_json(assertion_path) != ready_assertion
            or source_inventory != released_inventory
            or not document.is_file()
        ):
            raise ImmutableArtifactError(f"release identity conflict: {target}")
        review_path = target / archived.review_path.name
        released = ArtifactSet(
            target, document, sha256_file(document), hash_tree(target), archived.prd_id,
            archived.version, "RELEASED", archived.short_title, archived.date,
            review_path, sha256_file(review_path),
        )
        _append_changelog(
            root,
            f"- {released.date} | {released.prd_id} {released.version} | RELEASED | "
            f"`{target.relative_to(root)}` | source: "
            f"`{archived.path.relative_to(root)}`",
        )
        _append_structured_changelog(
            root,
            released,
            metadata,
            status="RELEASED",
            ready_ref={
                "path": assertion_path.relative_to(root).as_posix(),
                "hash": sha256_file(assertion_path),
                "version": ready_assertion.get("rules_version", "v1"),
            },
            lifecycle_refs=ready_assertion,
        )
        update_release_manifest(root, released, metadata)
        return released
    parent.mkdir(parents=True, exist_ok=True)
    temporary = parent / f".{archived.path.name}.tmp-{uuid4().hex}"
    try:
        shutil.copytree(archived.path, temporary)
        atomic_write_json(temporary / "READY_ASSERTION.json", ready_assertion)
        os.replace(temporary, target)
        if failpoint is not None:
            failpoint("after_release_publish")
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    document = target / archived.document_path.name
    released = ArtifactSet(
        target,
        document,
        sha256_file(document),
        hash_tree(target),
        archived.prd_id,
        archived.version,
        "RELEASED",
        archived.short_title,
        archived.date,
        target / archived.review_path.name,
        sha256_file(target / archived.review_path.name),
    )
    _append_changelog(
        root,
        f"- {released.date} | {released.prd_id} {released.version} | RELEASED | "
        f"`{target.relative_to(root)}` | source: "
        f"`{archived.path.relative_to(root)}`",
    )
    assertion_path = target / "READY_ASSERTION.json"
    _append_structured_changelog(
        root,
        released,
        metadata,
        status="RELEASED",
        ready_ref={
            "path": assertion_path.relative_to(root).as_posix(),
            "hash": sha256_file(assertion_path),
            "version": ready_assertion.get("rules_version", "v1"),
        },
        lifecycle_refs=ready_assertion,
    )
    update_release_manifest(root, released, metadata)
    return released
