"""Derived product-document navigation and human lifecycle views.

These files help people find the exact forward implementation target. They are
explicitly non-authoritative: immutable PRD, Ready Assertion, Run state and
Controller receipts remain the product truth.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .storage import atomic_write_bytes, atomic_write_json, read_json, sha256_file


def requirement_relationships(metadata: dict[str, Any]) -> dict[str, Any]:
    relationships = metadata.get("requirement_relationships")
    if relationships is None:
        return {
            "schema_version": "requirement-relationships.v1",
            "supersedes_forward_delivery_target": [],
            "invalidates": [],
        }
    if not isinstance(relationships, dict):
        raise ValueError("requirement_relationships must be an object")
    allowed = {"schema_version", "supersedes_forward_delivery_target", "invalidates"}
    unknown = sorted(set(relationships) - allowed)
    if unknown:
        raise ValueError("requirement_relationships has unknown fields: " + ", ".join(unknown))
    if relationships.get("schema_version") != "requirement-relationships.v1":
        raise ValueError("requirement_relationships.schema_version must be requirement-relationships.v1")
    targets = relationships.get("supersedes_forward_delivery_target")
    invalidates = relationships.get("invalidates")
    if not isinstance(targets, list) or not isinstance(invalidates, list):
        raise ValueError("requirement_relationships targets and invalidates must be lists")
    for index, target in enumerate(targets):
        if not isinstance(target, dict) or set(target) != {
            "prd_id", "version", "document_ref", "preserve_historical_status"
        }:
            raise ValueError(f"requirement_relationships target[{index}] is not closed-world")
        ref = target.get("document_ref")
        if (
            not isinstance(target.get("prd_id"), str)
            or not target["prd_id"].strip()
            or not isinstance(target.get("version"), str)
            or not target["version"].strip()
            or target.get("preserve_historical_status") is not True
            or not isinstance(ref, dict)
            or not isinstance(ref.get("path"), str)
            or not isinstance(ref.get("hash"), str)
            or not ref["hash"].startswith("sha256:")
        ):
            raise ValueError(f"requirement_relationships target[{index}] is incomplete")
    if any(not isinstance(item, str) or not item.strip() for item in invalidates):
        raise ValueError("requirement_relationships.invalidates must contain non-empty strings")
    return deepcopy(relationships)


def _document_ref(project_root: Path, released) -> dict[str, Any]:
    return {
        "path": released.document_path.relative_to(project_root).as_posix(),
        "hash": released.document_hash,
        "version": released.version,
    }


def update_release_manifest(
    project_root: Path,
    released,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Project exact release relationships into a non-authoritative index."""

    root = project_root.resolve()
    path = root / "artifacts" / "prds" / "RELEASE_MANIFEST.json"
    relationships = requirement_relationships(metadata)
    entry_path = (
        root
        / "artifacts"
        / "prds"
        / "manifests"
        / f"{released.path.name}.release-manifest.json"
    )
    entry = {
        "schema_version": "prd-release-entry.v1",
        "authority": "DERIVED_NAVIGATION_ONLY",
        "prd_id": released.prd_id,
        "version": released.version,
        "document_ref": _document_ref(root, released),
        "supersedes": metadata.get("supersedes"),
        "requirement_relationships": relationships,
    }
    if entry_path.exists():
        if entry_path.is_symlink() or read_json(entry_path) != entry:
            raise ValueError("immutable release manifest identity conflict")
    else:
        atomic_write_json(entry_path, entry)
    manifest = (
        read_json(path)
        if path.is_file() and not path.is_symlink()
        else {
            "schema_version": "prd-release-manifest.v1",
            "authority": "DERIVED_NAVIGATION_ONLY",
            "forward_implementation_targets": [],
            "historical_targets": [],
        }
    )
    if (
        manifest.get("schema_version") != "prd-release-manifest.v1"
        or manifest.get("authority") != "DERIVED_NAVIGATION_ONLY"
        or not isinstance(manifest.get("forward_implementation_targets"), list)
        or not isinstance(manifest.get("historical_targets"), list)
    ):
        raise ValueError("existing RELEASE_MANIFEST.json is not a supported exact manifest")

    new_ref = _document_ref(root, released)
    replaced_ids = {
        item["prd_id"] for item in relationships["supersedes_forward_delivery_target"]
    }
    kept: list[dict[str, Any]] = []
    history = list(manifest["historical_targets"])
    for item in manifest["forward_implementation_targets"]:
        if item.get("prd_id") == released.prd_id:
            if item.get("document_ref") != new_ref:
                history.append({
                    **item,
                    "forward_status": "SUPERSEDED_BY_NEW_VERSION",
                    "replaced_by": new_ref,
                })
        elif item.get("prd_id") in replaced_ids:
            history.append({
                **item,
                "forward_status": "SUPERSEDED_BY_NEW_REQUIREMENT_IDENTITY",
                "replaced_by": new_ref,
            })
        else:
            kept.append(item)

    existing_history_refs = {
        (item.get("prd_id"), str(item.get("version")), str(item.get("document_ref")))
        for item in history
    }
    for target in relationships["supersedes_forward_delivery_target"]:
        identity = (target["prd_id"], target["version"], str(target["document_ref"]))
        if identity not in existing_history_refs:
            history.append({
                "prd_id": target["prd_id"],
                "version": target["version"],
                "document_ref": target["document_ref"],
                "preserve_historical_status": True,
                "forward_status": "SUPERSEDED_BY_NEW_REQUIREMENT_IDENTITY",
                "replaced_by": new_ref,
            })

    kept.append({
        "prd_id": released.prd_id,
        "version": released.version,
        "document_ref": new_ref,
        "forward_status": "CURRENT_EXACT_TARGET",
        "requirement_relationships": relationships,
    })
    output = {
        "schema_version": "prd-release-manifest.v1",
        "authority": "DERIVED_NAVIGATION_ONLY",
        "forward_implementation_targets": sorted(kept, key=lambda item: item["prd_id"]),
        "historical_targets": sorted(
            history, key=lambda item: (item.get("prd_id", ""), str(item.get("version", "")))
        ),
    }
    atomic_write_json(path, output)
    return {
        "path": entry_path.relative_to(root).as_posix(),
        "hash": sha256_file(entry_path),
        "version": 1,
        "authority": "DERIVED_NAVIGATION_ONLY",
    }


def release_manifest_ref(project_root: Path, release_stem: str) -> dict[str, Any]:
    root = project_root.resolve()
    path = (
        root
        / "artifacts"
        / "prds"
        / "manifests"
        / f"{release_stem}.release-manifest.json"
    )
    if not path.is_file() or path.is_symlink():
        raise ValueError("exact immutable release manifest is missing")
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": sha256_file(path),
        "version": 1,
        "authority": "DERIVED_NAVIGATION_ONLY",
    }


def write_human_lifecycle_view(
    project_root: Path,
    *,
    run_id: str,
    released_path: Path,
    release_ref: dict[str, Any],
    metadata: dict[str, Any],
    review: dict[str, Any],
    delivery_status: str,
) -> dict[str, Any]:
    """Render a short human view without changing immutable released PRD bytes."""

    root = project_root.resolve()
    stem = released_path.name
    path = root / "artifacts" / "prds" / "status" / f"{stem}.status.md"
    evals = metadata.get("evals") if isinstance(metadata.get("evals"), dict) else {}
    eval_status = evals.get("execution_status") or "NOT_RUN"
    finding_count = review.get("finding_count", 0)
    content = f"""# {metadata.get('short_title', metadata.get('prd_id', stem))}｜交付状态

## 一眼看懂

- 需求文档：RELEASED
- Reviewer 遗留关注：{finding_count}
- 代码实现：{release_ref.get('engineering_implemented', 'NOT_CLAIMED')}
- 测试 / Evals：{eval_status}
- 本地交接：{delivery_status}
- 远程发送：NOT_CONFIGURED

## 证据与边界

- PRD：`{release_ref.get('artifact_path')}`
- Ready Assertion：`{release_ref.get('path')}`
- Run：`{run_id}`
- Authority：本页是 `NON_AUTHORITATIVE` 人类视图；不可替代 PRD、Ready Assertion、Run State 或 Controller receipt。
- 未知：代码实现、真实测试和外部审批只有在下游返回确切证据后才能更新。

## 下一步

研发与测试从 Handoff 中的 exact refs 开始；文档发布只说明需求基线成立，不代表代码和测试已经完成。
"""
    atomic_write_bytes(path, content.encode("utf-8"))
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": sha256_file(path),
        "version": 1,
        "authority": "NON_AUTHORITATIVE",
    }
