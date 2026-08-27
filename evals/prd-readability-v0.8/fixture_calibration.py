#!/usr/bin/env python3
"""Build two blind, self-contained Suite v0.8 fixture-calibration projections."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
SUITE_ID = "better-product-graph-prd-readability-v0.8"
CASE_IDS = tuple(f"case-{index:03d}" for index in range(1, 10))
CONTROL_PATH = ROOT / "calibration" / "notification-priority-positive.md"
FIXTURE_TREE_PATH = ROOT / "fixture-tree.json"
EXPECTED_FIXTURE_PATHS = tuple(
    [f"cases/{case_id}.md" for case_id in CASE_IDS]
    + [
        "assets/case-009-recovery-flow.svg",
        "assets/case-009-recovery-flow@2x.png",
        "calibration/notification-priority-positive.md",
    ]
)

CONTRACT_SOURCES = (
    ("profile.json", REPO_ROOT / "policies/document-experience/PRD_WRITING_PROFILE_v0.5.json", "0.5.0"),
    ("guide.md", REPO_ROOT / "policies/document-experience/PRD_WRITING_GUIDE_v0.5.md", "0.5.0"),
    ("instructions.md", REPO_ROOT / "src/core/atomic-skills/prd-writing-eval-review-v3.2/INSTRUCTIONS.md", "v3.2"),
    ("reviewer-resource.json", REPO_ROOT / "src/core/reviewer-profiles/prd-writing-eval-reader-review-v3.2.json", "v3.2"),
    ("output-contract.json", REPO_ROOT / "src/core/templates/contracts/prd-v0.2.json", "better-product-graph.prd.general.0.2"),
    ("result-schema.json", REPO_ROOT / "src/core/schemas/document-experience-reader-eval-v3.1.schema.json", "document-experience-reader-eval.v3.1"),
)

SOURCE_DOCUMENTS = {
    **{case_id: ROOT / "cases" / f"{case_id}.md" for case_id in CASE_IDS},
    "paired-positive": CONTROL_PATH,
}

REVIEWER_ORDERS = {
    "fixture-review-v08-a2-20260826": (
        "case-001", "paired-positive", "case-002", "case-003", "case-004",
        "case-005", "case-006", "case-007", "case-008", "case-009",
    ),
    "fixture-review-v08-b2-20260826": (
        "case-006", "case-002", "case-008", "paired-positive", "case-001",
        "case-009", "case-004", "case-007", "case-003", "case-005",
    ),
}


def _sha256(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _exact_ref(root: Path, path: Path, version: str | int) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": _sha256(path.read_bytes()),
        "version": version,
    }


def _require_regular(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular file")
    return path.read_bytes()


def validate_fixture_tree_identity(suite_root: Path = ROOT) -> dict[str, Any]:
    """Fail closed unless the exact complete fixture tree matches its manifest."""

    suite_root = Path(suite_root).resolve()
    actual_paths: list[str] = []
    for directory_name in ("cases", "assets", "calibration"):
        directory = suite_root / directory_name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f"v0.8 fixture directory is invalid: {directory_name}")
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"v0.8 fixture tree contains a symlink: {path}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f"v0.8 fixture tree contains a non-file: {path}")
            actual_paths.append(path.relative_to(suite_root).as_posix())
    if len(actual_paths) != len(EXPECTED_FIXTURE_PATHS) or set(actual_paths) != set(EXPECTED_FIXTURE_PATHS):
        raise ValueError("v0.8 fixture tree contains a missing or unmanifested file")

    tree_path = suite_root / "fixture-tree.json"
    try:
        tree = json.loads(_require_regular(tree_path, "fixture tree").decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("v0.8 fixture tree is not valid JSON") from error
    if not isinstance(tree, dict) or set(tree) != {
        "schema_version", "suite_id", "status", "tree_hash", "files"
    }:
        raise ValueError("v0.8 fixture tree must be a closed object")
    if (
        tree["schema_version"] != "prd-readability-v0.8-fixture-tree.v1"
        or tree["suite_id"] != SUITE_ID
        or tree["status"] != "BLIND_FIXTURE_CALIBRATION_PENDING"
    ):
        raise ValueError("v0.8 fixture tree is not the pending calibration identity")
    files = tree["files"]
    if not isinstance(files, list) or len(files) != len(EXPECTED_FIXTURE_PATHS):
        raise ValueError("v0.8 fixture tree must contain the exact expected file count")
    paths = [item.get("path") if isinstance(item, dict) else None for item in files]
    if paths != list(EXPECTED_FIXTURE_PATHS) or len(set(paths)) != len(paths):
        raise ValueError("v0.8 fixture tree path set, order, or uniqueness is invalid")

    verified: list[dict[str, Any]] = []
    for item in files:
        if set(item) != {"path", "hash", "size"}:
            raise ValueError("v0.8 fixture tree file entry must be closed")
        digest = item["hash"]
        if (
            not isinstance(digest, str)
            or len(digest) != 71
            or not digest.startswith("sha256:")
            or digest == "sha256:" + "0" * 64
            or any(character not in "0123456789abcdef" for character in digest[7:])
        ):
            raise ValueError(f"fixture tree hash is invalid: {item['path']}")
        path = suite_root / item["path"]
        content = _require_regular(path, item["path"])
        current = {"path": item["path"], "hash": _sha256(content), "size": len(content)}
        if item != current:
            raise ValueError(f"fixture tree member is stale: {item['path']}")
        verified.append(current)
    canonical = json.dumps(
        verified, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    expected_tree_hash = _sha256(canonical)
    if tree["tree_hash"] != expected_tree_hash or tree["tree_hash"] == "sha256:" + "0" * 64:
        raise ValueError("v0.8 fixture tree canonical hash is stale")
    return tree


def _validate_source_identity() -> dict[str, Any]:
    return validate_fixture_tree_identity(ROOT)


def _prepare_target(target: Path) -> Path:
    target = target.resolve()
    if target.exists():
        raise ValueError("blind calibration target must not already exist")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()
    return target


def emit_blind_fixture_calibration(target: Path) -> dict[str, Any]:
    """Emit two independently ordered projections and keep the source map outside both."""

    tree = _validate_source_identity()
    target = _prepare_target(Path(target))
    custody_documents: list[dict[str, Any]] = []
    reviewer_index: list[dict[str, Any]] = []

    for reviewer_id, source_order in REVIEWER_ORDERS.items():
        projection = target / reviewer_id
        documents_root = projection / "documents"
        contract_root = projection / "contract"
        assets_root = projection / "assets"
        documents_root.mkdir(parents=True)
        contract_root.mkdir()
        assets_root.mkdir()

        document_refs: list[dict[str, Any]] = []
        for ordinal, source_id in enumerate(source_order, start=1):
            source = SOURCE_DOCUMENTS[source_id]
            content = _require_regular(source, source_id)
            destination = documents_root / f"document-{ordinal:03d}.md"
            destination.write_bytes(content)
            document_ref = _exact_ref(projection, destination, 1)
            document_ref["document_id"] = f"document-{ordinal:03d}"
            document_refs.append(document_ref)
            custody_documents.append(
                {
                    "reviewer_id": reviewer_id,
                    "document_id": f"document-{ordinal:03d}",
                    "projection_ref": document_ref,
                    "source_path": source.relative_to(REPO_ROOT).as_posix(),
                    "source_hash": _sha256(content),
                }
            )

        visual_refs: list[dict[str, Any]] = []
        for name in ("case-009-recovery-flow.svg", "case-009-recovery-flow@2x.png"):
            source = ROOT / "assets" / name
            _require_regular(source, name)
            destination = assets_root / name
            shutil.copyfile(source, destination)
            visual_refs.append(_exact_ref(projection, destination, 1))

        contract_refs: list[dict[str, Any]] = []
        for export_name, source, version in CONTRACT_SOURCES:
            _require_regular(source, export_name)
            destination = contract_root / export_name
            shutil.copyfile(source, destination)
            contract_refs.append(_exact_ref(projection, destination, version))

        work_order = {
            "schema_version": "prd-readability-v0.8-blind-calibration-work-order.v1",
            "suite_id": SUITE_ID,
            "reviewer_id": reviewer_id,
            "purpose": "独立观察每份文档是否让目标读者理解、定位和执行产品规则。",
            "document_refs": document_refs,
            "contract_refs": contract_refs,
            "visual_refs": visual_refs,
            "review_contract": {
                "result_values": ["PASS", "FINDING"],
                "required_fields": [
                    "document_id",
                    "result",
                    "observed_reader_outcome",
                    "primary_diagnosis",
                    "primary_repair_technique",
                    "exact_basis",
                    "reason",
                ],
                "instructions": [
                    "先按 Profile、Guide 与公开 Reviewer Instruction 阅读，再独立判断文档的实际读者结果。",
                    "FINDING 只报告一个最主要且会影响理解、定位、复述或决策的写作问题；给出最小修复。",
                    "PASS 时 primary_diagnosis 与 primary_repair_technique 使用 null，并说明为什么读者不需要修复。",
                    "不要读取本目录之外的文件，不要与另一位 Reviewer 交换结果。",
                ],
            },
            "output_target": "review-result.json",
            "claim_boundary": {
                "fixture_calibration_only": True,
                "agent_product_eval": "NOT_RUN",
                "ordinary_product_review": "NOT_RUN",
                "human_reader_validation": "NOT_RUN",
            },
        }
        _write_json(projection / "work-order.json", work_order)
        manifest_files = [
            {
                "path": path.relative_to(projection).as_posix(),
                "hash": _sha256(path.read_bytes()),
                "size": len(path.read_bytes()),
            }
            for path in sorted(projection.rglob("*"))
            if path.is_file()
        ]
        manifest = {
            "schema_version": "prd-readability-v0.8-blind-calibration-projection.v1",
            "suite_id": SUITE_ID,
            "reviewer_id": reviewer_id,
            "fixture_tree_hash": tree["tree_hash"],
            "source_mapping_included": False,
            "private_evaluation_material_included": False,
            "files": manifest_files,
        }
        _write_json(projection / "projection-manifest.json", manifest)
        reviewer_index.append(
            {
                "reviewer_id": reviewer_id,
                "projection_path": reviewer_id,
                "work_order_path": f"{reviewer_id}/work-order.json",
                "output_target": f"{reviewer_id}/review-result.json",
            }
        )

    custody = {
        "schema_version": "prd-readability-v0.8-blind-calibration-custody.v1",
        "suite_id": SUITE_ID,
        "fixture_tree_hash": tree["tree_hash"],
        "documents": custody_documents,
        "reviewer_outputs": [item["output_target"] for item in reviewer_index],
        "claim_boundary": "MAPPING_ONLY_NOT_REVIEW_NOT_ORACLE_NOT_AGENT_EVAL",
    }
    _write_json(target / "custody-map.json", custody)
    index = {
        "schema_version": "prd-readability-v0.8-blind-calibration-index.v1",
        "suite_id": SUITE_ID,
        "status": "READY_FOR_TWO_FRESH_REVIEWERS",
        "fixture_tree_hash": tree["tree_hash"],
        "reviewers": reviewer_index,
        "agent_product_eval": "NOT_RUN",
        "ordinary_product_review": "NOT_RUN",
        "human_reader_validation": "NOT_RUN",
    }
    _write_json(target / "index.json", index)
    return index


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(emit_blind_fixture_calibration(arguments.target), ensure_ascii=False, indent=2))
