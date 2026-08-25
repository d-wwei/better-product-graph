from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from src.bpg.storage import atomic_write_json, sha256_file


def attach_zero_finding_writing_coverage(
    project_root: Path,
    dispatch: dict[str, Any],
    result: dict[str, Any],
    *,
    reviewer_attempt_id: str | None = None,
) -> dict[str, Any]:
    """Attach complete 13+10 test evidence to an existing review.parallel result."""

    context = dispatch["writing_review_context"]
    candidate = context["candidate_ref"]
    basis = [
        {
            "path": candidate["path"],
            "hash": candidate["hash"],
            "start_line": 1,
            "end_line": 1,
        }
    ]
    payload = {
        "schema_version": "document-experience-coverage.v1",
        "candidate_ref": deepcopy(candidate),
        "candidate_tree_hash": context["candidate_tree_hash"],
        "profile_ref": deepcopy(context["profile_ref"]),
        "guide_ref": deepcopy(context["guide_ref"]),
        "output_contract_ref": deepcopy(context["output_contract_ref"]),
        "author_execution_ref": deepcopy(context["author_execution_ref"]),
        "reviewer_execution_ref": {
            "kind": "HOST_SUBAGENT_ATTEMPT",
            "id": reviewer_attempt_id or f"writing-{dispatch['attempt_id']}",
        },
        "reviewer_role": "writing_standard",
        "isolated_input_refs": deepcopy(context["isolated_input_refs"]),
        "required_rule_results": [
            {
                "rule_id": rule_id,
                "verdict": "PASS",
                "basis_refs": deepcopy(basis),
                "reason": "测试夹具确认候选稿存在对应依据。",
            }
            for rule_id in context["required_rule_ids"]
        ],
        "delivery_check_results": [
            {
                "check_id": check_id,
                "verdict": "PASS",
                "basis_refs": deepcopy(basis),
                "reason": "测试夹具确认读者可从候选稿直接判断。",
            }
            for check_id in context["required_check_ids"]
        ],
        "finding_refs": [],
    }
    root = project_root.resolve()
    path = (
        root
        / ".better-product-graph"
        / "test-writing-coverage"
        / f"{dispatch['attempt_id']}.json"
    )
    atomic_write_json(path, payload)
    ref = {
        "path": path.relative_to(root).as_posix(),
        "hash": sha256_file(path),
        "version": 1,
    }
    result["semantic_output"]["writing_coverage_ref"] = deepcopy(ref)
    result.setdefault("artifact_refs", []).append(
        {"role": "writing_coverage", **ref}
    )
    return ref
