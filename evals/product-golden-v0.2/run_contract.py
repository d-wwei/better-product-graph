#!/usr/bin/env python3
"""Validate Product Golden fixtures without evaluating or faking Agent judgment."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REQUIRED_CASES = ("G01", "G03", "G04")
AGENT_VISIBLE = ("input.yaml", "knowledge-snapshot.yaml", "pm-response-bank.yaml")
EVALUATOR_ONLY = ("expected-envelope.yaml", "rubric.yaml")


def _load_json_yaml(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture root must be an object: {path}")
    return value


def _validate_case(case_id: str) -> list[str]:
    issues: list[str] = []
    case_root = ROOT / "cases" / case_id
    expected_files = set(AGENT_VISIBLE + EVALUATOR_ONLY)
    actual_files = {path.name for path in case_root.iterdir() if path.is_file()} if case_root.is_dir() else set()
    if actual_files != expected_files:
        issues.append(f"five-file package mismatch: {sorted(actual_files)}")
        return issues
    try:
        loaded = {name: _load_json_yaml(case_root / name) for name in expected_files}
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [f"invalid JSON-compatible YAML: {error}"]
    if loaded["input.yaml"].get("case_id") != case_id:
        issues.append("input case_id mismatch")
    if not loaded["input.yaml"].get("signal"):
        issues.append("input signal missing")
    if not isinstance(loaded["knowledge-snapshot.yaml"].get("evidence"), list):
        issues.append("knowledge evidence list missing")
    if not isinstance(loaded["pm-response-bank.yaml"].get("responses"), list):
        issues.append("PM response bank missing")
    envelope = loaded["expected-envelope.yaml"]
    if not envelope.get("acceptable_outcomes") or not envelope.get("critical_failures"):
        issues.append("evaluator outcome envelope incomplete")
    rubric = loaded["rubric.yaml"]
    if not rubric.get("dimensions") or not rubric.get("critical_failure_policy"):
        issues.append("evaluator rubric incomplete")
    for name in AGENT_VISIBLE:
        text = (case_root / name).read_text(encoding="utf-8")
        if "expected-envelope" in text or "rubric.yaml" in text or "evaluator_only" in text:
            issues.append(f"evaluator-only leakage marker in {name}")
    return issues


def _emit_agent_workspace(target: Path) -> None:
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise ValueError("agent workspace target must be empty")
    target.mkdir(parents=True, exist_ok=True)
    for case_id in REQUIRED_CASES:
        destination = target / case_id
        destination.mkdir()
        for name in AGENT_VISIBLE:
            shutil.copyfile(ROOT / "cases" / case_id / name, destination / name)


def run(emit_agent_workspace: Path | None = None) -> dict[str, Any]:
    suite = json.loads((ROOT / "suite.json").read_text(encoding="utf-8"))
    suite_issues: list[str] = []
    if tuple(suite.get("cases", [])) != REQUIRED_CASES:
        suite_issues.append("suite case list mismatch")
    if suite.get("evidence_policy", {}).get("fixture_contract_pass_implies_product_pass") is not False:
        suite_issues.append("fixture evidence policy must fail closed")
    case_results: dict[str, Any] = {}
    for case_id in REQUIRED_CASES:
        issues = _validate_case(case_id)
        case_results[case_id] = {
            "fixture_status": "FAIL" if issues else "PASS",
            "issues": issues,
            "agent_runtime_status": "NOT_RUN",
            "product_judgment_status": "NOT_RUN",
        }
    contract_status = "FAIL" if suite_issues or any(
        item["fixture_status"] == "FAIL" for item in case_results.values()
    ) else "PASS"
    if emit_agent_workspace is not None and contract_status == "PASS":
        _emit_agent_workspace(emit_agent_workspace)
    return {
        "suite_id": suite.get("suite_id"),
        "contract_status": contract_status,
        "evidence_level": "CONTRACT_FIXTURE_ONLY",
        "agent_runtime_status": "NOT_RUN",
        "product_judgment_status": "NOT_RUN",
        "suite_issues": suite_issues,
        "cases": case_results,
        "claim_boundary": "Fixture validation is not Agent product evaluation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-agent-workspace", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.emit_agent_workspace)
    except (OSError, ValueError) as error:
        result = {
            "contract_status": "FAIL",
            "evidence_level": "CONTRACT_FIXTURE_ONLY",
            "agent_runtime_status": "NOT_RUN",
            "product_judgment_status": "NOT_RUN",
            "error": str(error),
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["contract_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
