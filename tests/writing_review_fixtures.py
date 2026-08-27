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
    """Attach exact zero-Finding evidence for the Candidate-bound review contract."""

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
    if context.get("schema_version") == "writing-review-dispatch.v3":
        visual_pairs = deepcopy(context.get("reader_visible_visual_pairs", []))
        payload = {
            "schema_version": "document-experience-reader-review.v3",
            "authority": "ADVISORY_ONLY",
            "candidate_ref": deepcopy(candidate),
            "candidate_tree_hash": context["candidate_tree_hash"],
            "profile_ref": deepcopy(context["profile_ref"]),
            "guide_ref": deepcopy(context["guide_ref"]),
            "review_contract_ref": deepcopy(context["review_contract_ref"]),
            "output_contract_ref": deepcopy(context["output_contract_ref"]),
            "author_execution_ref": deepcopy(context["author_execution_ref"]),
            "reviewer_execution_ref": {
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": reviewer_attempt_id or f"writing-{dispatch['attempt_id']}",
            },
            "reviewer_role": "writing_standard",
            "isolated_input_refs": deepcopy(context["isolated_input_refs"]),
            "reader_readback": {
                "problem_and_outcome": "测试读者能够说明问题和目标结果。",
                "primary_relationships": "测试读者能够说明主要关系。",
                "mental_model": [
                    {"name": "输入", "role": "提供产品信号"},
                    {"name": "判断", "role": "形成产品选择"},
                    {"name": "交付", "role": "形成可审查产物"},
                ],
                "main_path_and_recovery": "测试读者能够复述主路径和恢复路径。",
                "decision_conditions_and_risks": "测试读者能够定位条件、风险和改判点。",
                "navigation_map": [
                    {"target": "PRODUCT_RULES", "location": "候选稿产品规则章节"},
                    {"target": "ACCEPTANCE", "location": "候选稿验收章节"},
                    {"target": "RISKS_UNKNOWNS_NEXT", "location": "候选稿风险与下一步章节"},
                ],
            },
            "reader_outcome_failures": [],
            "verbosity_assessment": {
                "verdict": "PASS",
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": "测试夹具声明主路径没有重复定义。",
            },
            "checklist_assessment": {
                "verdict": "PASS",
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": "测试夹具声明 Checklist 功能保持完整。",
            },
            "visual_assessment": {
                "verdict": "PASS" if visual_pairs else "NOT_NEEDED",
                "observation_status": "OBSERVED" if visual_pairs else "NOT_NEEDED",
                "visual_pair_refs": visual_pairs,
                "issue_types": [],
                "repair_techniques": [],
                "basis_refs": [],
                "finding_refs": [],
                "reason": (
                    "测试夹具声明独立 Reviewer 已查看 exact 安全视觉资产。"
                    if visual_pairs
                    else "测试夹具声明当前关系无需额外视觉表达。"
                ),
            },
            "finding_refs": [],
            "claim_boundary": "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
        }
    else:
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
