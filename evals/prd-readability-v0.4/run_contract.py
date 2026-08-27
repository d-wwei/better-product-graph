#!/usr/bin/env python3
"""Validate and stage v0.4 readability fixtures without faking Agent evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]

CASE_IDS = (
    "flat-18-acceptance-rows",
    "duplicate-eight-questions-and-blocks",
    "list-diagram-table-same-model",
    "trim-removes-useful-checklist",
    "checked-boxes-without-legend",
    "proposed-contract-looks-implemented",
    "large-necessary-state-table",
    "long-appendix-short-main-path",
    "reader-first-layered-prd",
)
EXPECTED_FINDINGS = {
    "flat-18-acceptance-rows": ("FLAT_PEER_OVERLOAD", "GROUP"),
    "duplicate-eight-questions-and-blocks": ("SEMANTIC_REPETITION", "REFERENCE"),
    "list-diagram-table-same-model": ("REPRESENTATION_COLLISION", "TRIM"),
    "trim-removes-useful-checklist": ("CHECKLIST_FUNCTION_LOSS", "RESTORE_FUNCTION"),
    "checked-boxes-without-legend": ("COMPLETION_SEMANTICS_AMBIGUOUS", "EXPLAIN"),
    "proposed-contract-looks-implemented": ("ARTIFACT_MATURITY_OVERCLAIM", "BOUNDARY"),
}
EVALUATOR_ONLY = ("evaluator/expected.json", "evaluator/preregistration.json")
EXACT_REF_FIELDS = frozenset({"path", "hash", "version"})
PROFILE_PATH = "policies/document-experience/PRD_WRITING_PROFILE_v0.4.json"
GUIDE_PATH = "policies/document-experience/PRD_WRITING_GUIDE_v0.4.md"
V04_VERSION = "0.4.0"
PROFILE_ID = "prd-plain-language-zh-CN"
RUNTIME_CHECKPOINT_REFS = (
    "suite_ref",
    "case_ref",
    "candidate_ref",
    "profile_ref",
    "guide_ref",
    "instruction_ref",
    "reviewer_resource_ref",
    "output_contract_ref",
    "installed_build_ref",
    "dispatch_ref",
)
READER_OUTCOMES = ("UNDERSTAND", "SEE", "MODEL", "RETELL", "DECIDE", "LOCATE")
DIAGNOSTIC_CATEGORIES = (
    "SEMANTIC_REPETITION",
    "FLAT_PEER_OVERLOAD",
    "REPRESENTATION_COLLISION",
    "DETAIL_IN_MAIN_PATH",
    "DENSE_TABLE",
    "JARGON_INTRUSION",
    "CHECKLIST_FUNCTION_LOSS",
    "COMPLETION_SEMANTICS_AMBIGUOUS",
    "ARTIFACT_MATURITY_OVERCLAIM",
)
REPAIR_TECHNIQUES = (
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
)
SUITE_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "status",
        "case_ids",
        "case_hashes",
        "agent_visible_case_file",
        "evaluator_only_files",
        "profile_ref",
        "guide_ref",
        "target_eval_schema",
        "reader_outcomes",
        "diagnostic_categories",
        "repair_techniques",
        "evidence_policy",
    }
)
EXPECTED_FIELDS = frozenset({"schema_version", "suite_id", "custody", "cases"})
PREREGISTRATION_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "status",
        "registered_at",
        "custody",
        "case_hashes",
        "expected_ref",
        "profile_ref",
        "guide_ref",
        "runtime_checkpoint_required_refs",
        "agent_runtime_status",
        "real_prd_review_status",
        "human_reader_validation",
    }
)


class EvalContractError(ValueError):
    """The committed Suite or emitted Agent input violates the v0.4 contract."""


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise EvalContractError(f"JSON input must be a regular non-symlink file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvalContractError(f"unreadable JSON: {path}: {error}") from error
    if not isinstance(value, dict):
        raise EvalContractError(f"JSON root must be an object: {path}")
    return value


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != EXACT_REF_FIELDS:
        raise EvalContractError(f"{label} must be a closed exact ref")
    if not isinstance(value["path"], str) or not value["path"]:
        raise EvalContractError(f"{label}.path must be non-empty")
    digest = value["hash"]
    if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
        raise EvalContractError(f"{label}.hash must be a full sha256 reference")
    try:
        int(digest.removeprefix("sha256:"), 16)
    except ValueError as error:
        raise EvalContractError(f"{label}.hash must be a full sha256 reference") from error
    version = value["version"]
    if isinstance(version, bool) or (
        not isinstance(version, (str, int))
        or (isinstance(version, str) and not version.strip())
        or (isinstance(version, int) and version < 1)
    ):
        raise EvalContractError(f"{label}.version must be a non-empty string or integer >= 1")
    return value


def _validate_repo_ref(value: Any, label: str) -> tuple[dict[str, Any], Path]:
    ref = _exact_ref(value, label)
    relative = PurePosixPath(ref["path"])
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != ref["path"]:
        raise EvalContractError(f"{label}.path must remain inside the repository")
    root = REPO_ROOT.resolve()
    candidate = root / ref["path"]
    if not candidate.is_file() or candidate.is_symlink():
        raise EvalContractError(f"{label} must bind an exact regular repository file")
    path = candidate.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise EvalContractError(f"{label}.path escapes the repository") from error
    if not path.is_file() or _sha256(path) != ref["hash"]:
        raise EvalContractError(f"{label} must bind an exact regular repository file")
    return ref, path


def _validate_profile_ref(value: Any, label: str) -> None:
    ref, path = _validate_repo_ref(value, label)
    if ref["path"] != PROFILE_PATH or ref["version"] != V04_VERSION:
        raise EvalContractError(f"{label} must bind the exact v0.4 Profile identity")
    profile = _load_json(path)
    expected = {
        "schema_version": "document-experience-profile.v1",
        "profile_id": PROFILE_ID,
        "profile_version": V04_VERSION,
        "status": "CANDIDATE",
        "artifact_type": "PRD",
        "language": "zh-CN",
        "runtime_status": "CANDIDATE_NON_DEFAULT",
        "validation_status": "POLICY_AUTHORED_AGENT_EVAL_NOT_RUN",
    }
    for field, expected_value in expected.items():
        if profile.get(field) != expected_value:
            raise EvalContractError(f"{label} Profile {field} identity mismatch")


def _guide_frontmatter(path: Path, label: str) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise EvalContractError(f"{label} Guide frontmatter is unreadable: {error}") from error
    if not lines or lines[0] != "---":
        raise EvalContractError(f"{label} Guide must begin with frontmatter")
    try:
        closing = lines.index("---", 1)
    except ValueError as error:
        raise EvalContractError(f"{label} Guide frontmatter is not closed") from error
    frontmatter: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip():
            continue
        if ":" not in line:
            raise EvalContractError(f"{label} Guide frontmatter line is invalid")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key or key in frontmatter:
            raise EvalContractError(f"{label} Guide frontmatter key is invalid or duplicated")
        frontmatter[key] = raw_value.strip()
    return frontmatter


def _validate_guide_ref(value: Any, label: str) -> None:
    ref, path = _validate_repo_ref(value, label)
    if ref["path"] != GUIDE_PATH or ref["version"] != V04_VERSION:
        raise EvalContractError(f"{label} must bind the exact v0.4 Guide identity")
    frontmatter = _guide_frontmatter(path, label)
    expected = {
        "document": "Better Product Graph PRD 写作规范",
        "policy_family": "document-experience",
        "profile_id": PROFILE_ID,
        "version": V04_VERSION,
        "status": "CANDIDATE",
        "runtime_status": "CANDIDATE_NON_DEFAULT",
        "language": "zh-CN",
        "template_independent": "true",
        "candidate_successor_to": "PRD_WRITING_GUIDE_v0.3.md",
        "validation_status": "POLICY_AUTHORED_AGENT_EVAL_NOT_RUN",
    }
    for field, expected_value in expected.items():
        if frontmatter.get(field) != expected_value:
            raise EvalContractError(f"{label} Guide {field} identity mismatch")


def _valid_iso8601_with_timezone(value: Any) -> bool:
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def contract_issues() -> list[str]:
    issues: list[str] = []
    try:
        suite = _load_json(ROOT / "suite.json")
        expected = _load_json(ROOT / "evaluator" / "expected.json")
        prereg = _load_json(ROOT / "evaluator" / "preregistration.json")
    except EvalContractError as error:
        return [str(error)]

    if suite.get("schema_version") != "prd-readability-suite.v0.4":
        issues.append("suite schema_version mismatch")
    if set(suite) != SUITE_FIELDS:
        issues.append("suite must be a closed object")
    if suite.get("suite_id") != "better-product-graph-prd-readability-v0.4":
        issues.append("suite_id mismatch")
    if suite.get("status") != "PREREGISTERED_AGENT_EVAL_NOT_RUN":
        issues.append("suite status must remain PREREGISTERED_AGENT_EVAL_NOT_RUN")
    if suite.get("agent_visible_case_file") != "candidate.md":
        issues.append("agent_visible_case_file must remain candidate.md")
    if tuple(suite.get("case_ids", [])) != CASE_IDS:
        issues.append("suite case_ids must match the exact ordered nine-case set")
    if tuple(suite.get("evaluator_only_files", [])) != EVALUATOR_ONLY:
        issues.append("suite must declare the exact evaluator-only files")
    if suite.get("target_eval_schema") != "document-experience-reader-eval.v3.1":
        issues.append("target_eval_schema mismatch")
    if tuple(suite.get("reader_outcomes", [])) != READER_OUTCOMES:
        issues.append("reader_outcomes mismatch")
    if tuple(suite.get("diagnostic_categories", [])) != DIAGNOSTIC_CATEGORIES:
        issues.append("diagnostic_categories mismatch")
    if tuple(suite.get("repair_techniques", [])) != REPAIR_TECHNIQUES:
        issues.append("repair_techniques mismatch")

    case_hashes = suite.get("case_hashes")
    if not isinstance(case_hashes, dict) or set(case_hashes) != set(CASE_IDS):
        issues.append("suite case_hashes must cover the exact nine cases")
        case_hashes = {}
    for case_id in CASE_IDS:
        path = ROOT / "cases" / f"{case_id}.md"
        if not path.is_file() or path.is_symlink():
            issues.append(f"missing regular case file: {case_id}")
            continue
        if case_hashes.get(case_id) != _sha256(path):
            issues.append(f"immutable case hash mismatch: {case_id}")
        try:
            visible = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            issues.append(f"unreadable case file {case_id}: {error}")
            continue
        leaked = ("expected.json", "preregistration.json", "required_primary_diagnosis")
        if any(marker in visible for marker in leaked):
            issues.append(f"evaluator-only expectation leaked into {case_id}")

    if expected.get("schema_version") != "prd-readability-expected-envelope.v0.4":
        issues.append("expected schema_version mismatch")
    if set(expected) != EXPECTED_FIELDS:
        issues.append("expected envelope must be a closed object")
    if expected.get("suite_id") != suite.get("suite_id"):
        issues.append("expected suite_id mismatch")
    if expected.get("custody") != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE":
        issues.append("expected custody mismatch")
    expected_cases = expected.get("cases")
    if not isinstance(expected_cases, dict) or set(expected_cases) != set(CASE_IDS):
        issues.append("expected envelope must cover the exact nine cases")
        expected_cases = {}
    opaque_ids: list[str] = []
    for index, case_id in enumerate(CASE_IDS, 1):
        envelope = expected_cases.get(case_id)
        if not isinstance(envelope, dict):
            issues.append(f"expected case must be an object: {case_id}")
            continue
        opaque_id = envelope.get("agent_case_id")
        if isinstance(opaque_id, str):
            opaque_ids.append(opaque_id)
        if opaque_id != f"case-{index:03d}":
            issues.append(f"unexpected opaque Agent case ID: {case_id}")
        if case_id in EXPECTED_FINDINGS:
            diagnosis, repair = EXPECTED_FINDINGS[case_id]
            required_fields = {
                "agent_case_id",
                "required_result",
                "required_primary_diagnosis",
                "required_repair_technique",
            }
            if set(envelope) != required_fields:
                issues.append(f"Finding expectation is not minimal and closed: {case_id}")
            if (
                envelope.get("required_result") != "FINDING"
                or envelope.get("required_primary_diagnosis") != diagnosis
                or envelope.get("required_repair_technique") != repair
            ):
                issues.append(f"Finding expectation mismatch: {case_id}")
        elif set(envelope) != {"agent_case_id", "required_result"} or envelope.get(
            "required_result"
        ) != "PASS":
            issues.append(f"PASS expectation must remain minimal and closed: {case_id}")
    if len(set(opaque_ids)) != len(CASE_IDS):
        issues.append("opaque Agent case IDs must be unique")

    if prereg.get("schema_version") != "prd-readability-preregistration.v0.4":
        issues.append("preregistration schema_version mismatch")
    if set(prereg) != PREREGISTRATION_FIELDS:
        issues.append("preregistration must be a closed object")
    if prereg.get("suite_id") != suite.get("suite_id"):
        issues.append("preregistration suite_id mismatch")
    if prereg.get("status") != "PREREGISTERED_BEFORE_RESULTS":
        issues.append("preregistration must explicitly precede results")
    if not _valid_iso8601_with_timezone(prereg.get("registered_at")):
        issues.append("preregistration registered_at must be timezone-aware ISO 8601")
    if prereg.get("custody") != "EVALUATOR_ONLY_DO_NOT_COPY_TO_AGENT_WORKSPACE":
        issues.append("preregistration custody mismatch")
    if prereg.get("case_hashes") != case_hashes:
        issues.append("preregistration must bind exact case hashes")
    try:
        expected_ref = _exact_ref(prereg.get("expected_ref"), "expected_ref")
        expected_path = ROOT / expected_ref["path"]
        if (
            expected_ref["path"] != "evaluator/expected.json"
            or not expected_path.is_file()
            or expected_path.is_symlink()
            or _sha256(expected_path) != expected_ref["hash"]
        ):
            issues.append("preregistration expected_ref mismatch")
        _validate_profile_ref(prereg.get("profile_ref"), "preregistration.profile_ref")
        _validate_guide_ref(prereg.get("guide_ref"), "preregistration.guide_ref")
        _validate_profile_ref(suite.get("profile_ref"), "suite.profile_ref")
        _validate_guide_ref(suite.get("guide_ref"), "suite.guide_ref")
    except EvalContractError as error:
        issues.append(str(error))
    if prereg.get("profile_ref") != suite.get("profile_ref"):
        issues.append("preregistration profile_ref mismatch")
    if prereg.get("guide_ref") != suite.get("guide_ref"):
        issues.append("preregistration guide_ref mismatch")
    if tuple(prereg.get("runtime_checkpoint_required_refs", [])) != RUNTIME_CHECKPOINT_REFS:
        issues.append("runtime checkpoint required refs mismatch")

    evidence = suite.get("evidence_policy")
    if not isinstance(evidence, dict) or evidence != {
        "contract_pass_implies_agent_runtime_pass": False,
        "fixture_pass_implies_real_prd_review_pass": False,
        "fixture_pass_implies_human_reader_validation": False,
        "agent_runtime_status": "NOT_RUN",
        "real_prd_review_status": "NOT_RUN",
        "human_reader_validation": "NOT_RUN",
        "required_installed_agent_eval_result": "9/9",
    }:
        issues.append("suite evidence policy must keep contract, Agent, real PRD, and human evidence separate")
    for field in ("agent_runtime_status", "real_prd_review_status", "human_reader_validation"):
        if prereg.get(field) != "NOT_RUN":
            issues.append(f"preregistration {field} must remain NOT_RUN")
    result_files = [
        path
        for path in (ROOT / "results").rglob("*")
        if path.is_file() and path.name != "README.md"
    ]
    if result_files:
        issues.append("Agent Eval results must not exist in the preregistration commit")
    return issues


def emit_agent_workspace(target: Path) -> None:
    issues = contract_issues()
    if issues:
        raise EvalContractError("; ".join(issues))
    if target.is_symlink():
        raise EvalContractError("agent workspace target must not be a symlink")
    for custody_root in (REPO_ROOT, ROOT):
        comparisons = (
            (target.absolute(), custody_root.absolute()),
            (target.resolve(), custody_root.resolve()),
        )
        for location, normalized_custody_root in comparisons:
            try:
                location.relative_to(normalized_custody_root)
            except ValueError:
                continue
            raise EvalContractError(
                "agent workspace target must remain outside the repository and Suite custody trees"
            )
    if target.exists() and not target.is_dir():
        raise EvalContractError("agent workspace target must be a directory")
    if target.exists() and any(target.iterdir()):
        raise EvalContractError("agent workspace target must be empty")
    target.mkdir(parents=True, exist_ok=True)
    expected = _load_json(ROOT / "evaluator" / "expected.json")
    suite = _load_json(ROOT / "suite.json")
    for case_id in CASE_IDS:
        opaque_id = expected["cases"][case_id]["agent_case_id"]
        case_root = target / opaque_id
        case_root.mkdir()
        candidate = case_root / "candidate.md"
        shutil.copyfile(ROOT / "cases" / f"{case_id}.md", candidate)
        manifest = {
            "schema_version": "prd-readability-agent-case.v0.4",
            "suite_id": suite["suite_id"],
            "case_id": opaque_id,
            "candidate_ref": {
                "path": "candidate.md",
                "hash": _sha256(candidate),
                "version": 1,
            },
            "target_eval_schema": suite["target_eval_schema"],
            "evaluator_files_included": False,
            "agent_runtime_status": "NOT_RUN",
            "claim_boundary": "Fixture staging is not Writing Reviewer execution or scoring.",
        }
        (case_root / "case-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def report() -> dict[str, Any]:
    issues = contract_issues()
    return {
        "schema_version": "prd-readability-contract-report.v0.4",
        "suite_id": "better-product-graph-prd-readability-v0.4",
        "contract_status": "PASS" if not issues else "FAIL",
        "case_count": 9,
        "issues": issues,
        "agent_runtime_status": "NOT_RUN",
        "real_prd_review_status": "NOT_RUN",
        "human_reader_validation": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-agent-workspace", type=Path)
    args = parser.parse_args()
    result = report()
    if result["contract_status"] != "PASS":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.emit_agent_workspace is not None:
        try:
            emit_agent_workspace(args.emit_agent_workspace)
        except EvalContractError as error:
            result["contract_status"] = "FAIL"
            result["issues"] = [str(error)]
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1
        result["agent_workspace"] = str(args.emit_agent_workspace.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
