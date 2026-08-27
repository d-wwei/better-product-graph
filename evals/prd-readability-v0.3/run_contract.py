#!/usr/bin/env python3
"""Validate and stage PRD readability fixtures without faking Agent judgment."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.bpg.installed_identity import verify_installed_identity  # noqa: E402
from src.bpg.node_registry import NodeRegistry, NodeRegistryError  # noqa: E402
from src.bpg.storage import (  # noqa: E402
    IntegrityError,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_event_chain,
)
from src.bpg.writing_review import (  # noqa: E402
    WritingReviewError,
    validate_writing_review,
)


CASE_IDS = (
    "simple-linear-no-visual",
    "complex-flow-missing-visual",
    "misleading-visual",
    "verbose-repeated-contracts",
    "layered-svg-pass",
)
VISUAL_CASE_ASSETS = {
    "misleading-visual": "visual-001.svg",
    "layered-svg-pass": "visual-002.svg",
}
RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "case_id",
        "runtime_evidence_root",
        "run_id",
        "review_attempt_id",
        "preregistration_ref",
    }
)
SYNTHETIC_RESULT_FIELDS = RESULT_FIELDS - {"preregistration_ref"}
EXACT_REF_FIELDS = frozenset({"path", "hash", "version"})
PREREGISTRATION_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "case_id",
        "agent_case_id",
        "challenge",
        "evidence_class",
        "claim_boundary",
        "installed_build",
        "runtime_checkpoint",
    }
)
INSTALLED_BUILD_FIELDS = frozenset(
    {
        "installed_skill_root",
        "build_manifest_hash",
        "artifact_hash",
        "plugin_name",
        "plugin_version",
        "host_id",
        "git_commit",
        "git_dirty",
        "public_controller_ref",
    }
)
RUNTIME_CHECKPOINT_FIELDS = frozenset(
    {
        "runtime_evidence_root",
        "run_id",
        "review_attempt_id",
        "initial_state_version",
        "initial_event_count",
        "initial_event_head",
        "dispatch_hash",
        "dispatch_contract_hash",
        "candidate_ref",
        "profile_ref",
        "guide_ref",
        "output_contract_ref",
        "review_contract_ref",
    }
)


class EvalContractError(ValueError):
    """A readability fixture or recorded evaluation violates the suite contract."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvalContractError(f"unreadable JSON: {path}: {error}") from error
    if not isinstance(value, dict):
        raise EvalContractError(f"JSON root must be an object: {path}")
    return value


def _closed(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvalContractError(f"{label} must be an object")
    unknown = sorted(set(value) - fields)
    if unknown:
        raise EvalContractError(f"{label}.{unknown[0]} is an unknown field")
    missing = sorted(fields - set(value))
    if missing:
        raise EvalContractError(f"{label}.{missing[0]} is required")
    return value


def _non_empty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvalContractError(f"{label} must be non-empty")
    return value


def _validate_sha256(value: Any, label: str) -> str:
    text = _non_empty(value, label)
    digest = text.removeprefix("sha256:")
    if not text.startswith("sha256:") or len(digest) != 64:
        raise EvalContractError(f"{label} must be a full sha256 reference")
    try:
        int(digest, 16)
    except ValueError as error:
        raise EvalContractError(f"{label} must be a full sha256 reference") from error
    return text


def _suite() -> dict[str, Any]:
    return _load_json(ROOT / "suite.json")


def _expected() -> dict[str, Any]:
    return _load_json(ROOT / "expected.json")


def _contract_issues() -> list[str]:
    issues: list[str] = []
    try:
        suite = _suite()
        expected = _expected()
    except EvalContractError as error:
        return [str(error)]
    if suite.get("schema_version") != "prd-readability-suite.v0.3":
        issues.append("suite schema_version mismatch")
    if tuple(suite.get("case_ids", [])) != CASE_IDS:
        issues.append("suite case_ids must match the exact ordered five-case set")
    if expected.get("suite_id") != suite.get("suite_id"):
        issues.append("expected suite_id mismatch")
    expected_cases = expected.get("cases")
    if not isinstance(expected_cases, dict) or set(expected_cases) != set(CASE_IDS):
        issues.append("expected envelope must cover the exact five cases")
        expected_cases = {}
    case_hashes = suite.get("case_hashes")
    if not isinstance(case_hashes, dict) or set(case_hashes) != set(CASE_IDS):
        issues.append("suite case_hashes must cover the exact five cases")
        case_hashes = {}
    visual_values = set(suite.get("visual_model_verdicts", []))
    category_values = set(suite.get("diagnostic_categories", []))
    repair_values = set(suite.get("repair_techniques", []))
    for case_id in CASE_IDS:
        case_path = ROOT / "cases" / f"{case_id}.md"
        if not case_path.is_file() or case_path.is_symlink():
            issues.append(f"missing regular case file: {case_id}")
            continue
        if case_hashes.get(case_id) != sha256_file(case_path):
            issues.append(f"immutable case hash mismatch: {case_id}")
        try:
            visible = case_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            issues.append(f"unreadable case file {case_id}: {error}")
            continue
        if "expected.json" in visible or "material_finding" in visible:
            issues.append(f"evaluator-only expectation leaked into {case_id}")
        envelope = expected_cases.get(case_id)
        if not isinstance(envelope, dict):
            issues.append(f"expected case must be an object: {case_id}")
            continue
        if envelope.get("visual_model") not in visual_values:
            issues.append(f"invalid visual_model expectation: {case_id}")
        opaque_id = envelope.get("agent_case_id")
        if (
            not isinstance(opaque_id, str)
            or not opaque_id.startswith("case-")
            or not opaque_id.removeprefix("case-").isdigit()
        ):
            issues.append(f"invalid evaluator-only opaque case ID: {case_id}")
        categories = envelope.get("categories", [])
        if not isinstance(categories, list) or any(item not in category_values for item in categories):
            issues.append(f"invalid diagnostic categories: {case_id}")
        allowed = envelope.get("allowed_repairs", [])
        if not isinstance(allowed, list) or any(item not in repair_values for item in allowed):
            issues.append(f"invalid allowed repairs: {case_id}")
        if categories:
            outcomes = envelope.get("acceptable_revision_outcomes")
            if not isinstance(outcomes, list) or len(outcomes) < 2 or len(allowed) < 2:
                issues.append(f"expected envelope is too prescriptive: {case_id}")
    source_asset_hashes = suite.get("source_asset_hashes")
    expected_asset_names = {
        asset_name
        for svg_name in VISUAL_CASE_ASSETS.values()
        for asset_name in (svg_name, f"{Path(svg_name).stem}@2x.png")
    }
    if (
        not isinstance(source_asset_hashes, dict)
        or set(source_asset_hashes) != expected_asset_names
    ):
        issues.append("suite source_asset_hashes must bind the exact visual fixtures")
        source_asset_hashes = {}
    for asset_name in expected_asset_names:
        asset_path = ROOT / "assets" / asset_name
        if not asset_path.is_file() or asset_path.is_symlink():
            issues.append(f"missing regular committed visual fixture: {asset_name}")
        elif source_asset_hashes.get(asset_name) != sha256_file(asset_path):
            issues.append(f"immutable visual fixture hash mismatch: {asset_name}")
    policy = suite.get("evidence_policy")
    if not isinstance(policy, dict) or (
        policy.get("contract_pass_implies_agent_runtime_pass") is not False
        or policy.get("fixture_pass_implies_full_agent_product_eval_pass") is not False
        or policy.get("synthetic_runtime_max_status") != "SYNTHETIC_CONTRACT_PASS"
        or policy.get("preregistered_controller_evidence_is_external_crypto_proof")
        is not False
        or policy.get("agent_runtime_status_before_real_prd_eval") != "NOT_RUN"
        or policy.get("human_reader_validation") != "NOT_RUN"
    ):
        issues.append("suite evidence policy must keep contract, Agent, and human evidence separate")
    return issues


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def emit_agent_workspace(target: Path) -> None:
    issues = _contract_issues()
    if issues:
        raise EvalContractError("; ".join(issues))
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise EvalContractError("agent workspace target must be empty")
    target.mkdir(parents=True, exist_ok=True)
    suite = _suite()
    expected_cases = _expected()["cases"]
    for case_id in CASE_IDS:
        opaque_id = expected_cases[case_id]["agent_case_id"]
        case_root = target / opaque_id
        case_root.mkdir()
        source = ROOT / "cases" / f"{case_id}.md"
        candidate = case_root / "candidate.md"
        shutil.copyfile(source, candidate)
        assets: list[dict[str, str]] = []
        asset_name = VISUAL_CASE_ASSETS.get(case_id)
        render_target = ""
        if asset_name is not None:
            assets_root = case_root / "assets"
            assets_root.mkdir()
            svg_target = assets_root / asset_name
            shutil.copyfile(ROOT / "assets" / asset_name, svg_target)
            png_target = assets_root / f"{Path(asset_name).stem}@2x.png"
            shutil.copyfile(ROOT / "assets" / png_target.name, png_target)
            assets = [
                {"path": f"assets/{path.name}", "hash": sha256_file(path)}
                for path in (svg_target, png_target)
            ]
            render_target = f"assets/{asset_name}"
        manifest = {
            "schema_version": "prd-readability-agent-case.v0.3",
            "suite_id": suite["suite_id"],
            "case_id": opaque_id,
            "candidate": {"path": "candidate.md", "hash": sha256_file(candidate)},
            "assets": assets,
            "render_target": render_target,
            "agent_runtime_status": "NOT_RUN",
            "evaluator_expectations_included": False,
            "claim_boundary": "Fixture preparation is not Writing Reviewer execution.",
        }
        _write_json(case_root / "case-manifest.json", manifest)


def _managed_exact_path(project_root: Path, ref: Any, label: str) -> tuple[dict[str, Any], Path]:
    exact = _closed(ref, EXACT_REF_FIELDS, label)
    raw_path = _non_empty(exact.get("path"), f"{label}.path")
    _validate_sha256(exact.get("hash"), f"{label}.hash")
    _validate_exact_ref_version(exact.get("version"), f"{label}.version")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != raw_path:
        raise EvalContractError(f"{label}.path must remain inside project_root")
    root = project_root.resolve()
    path = (root / raw_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise EvalContractError(f"{label}.path escapes project_root") from error
    if not path.is_file() or path.is_symlink() or sha256_file(path) != exact["hash"]:
        raise EvalContractError(f"{label} must bind an exact regular file")
    return exact, path


def _exact_ref_shape(ref: Any, label: str) -> dict[str, Any]:
    exact = _closed(ref, EXACT_REF_FIELDS, label)
    _non_empty(exact.get("path"), f"{label}.path")
    _validate_sha256(exact.get("hash"), f"{label}.hash")
    _validate_exact_ref_version(exact.get("version"), f"{label}.version")
    return exact


def _validate_exact_ref_version(version: Any, label: str) -> None:
    if isinstance(version, bool) or (
        not isinstance(version, (str, int))
        or (isinstance(version, str) and not version.strip())
        or (isinstance(version, int) and version < 1)
    ):
        raise EvalContractError(
            f"{label} must be a non-empty string or integer >= 1"
        )


def _validate_writing_eval_runtime_identity(
    state: dict[str, Any],
    events: list[dict[str, Any]],
    run_id: str,
    *,
    review_attempt_id: str | None = None,
    require_completed: bool,
) -> None:
    suite_id = _suite()["suite_id"]
    if (
        state.get("run_type") != "writing_eval"
        or state.get("evaluation_only") is not True
        or state.get("writing_eval_suite_id") != suite_id
    ):
        raise EvalContractError(
            "runtime evidence is not the exact evaluation-only Writing Eval suite"
        )
    prepared_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event_type") == "WRITING_EVAL_PREPARED"
        and event.get("run_id") == run_id
        and event.get("suite_id") == suite_id
        and event.get("bootstrap_hash") == state.get("writing_eval_bootstrap_hash")
    ]
    if (
        len(prepared_indexes) != 1
        or prepared_indexes[0] != 0
        or events[0].get("before_state_hash") is not None
    ):
        raise EvalContractError(
            "runtime evidence requires one exact WRITING_EVAL_PREPARED boundary"
        )
    commitments = [
        event
        for event in events
        if isinstance(event.get("after_state_hash"), str)
    ]
    previous_after = None
    for index, event in enumerate(commitments):
        if event.get("before_state_hash") != previous_after:
            raise EvalContractError(
                "runtime Writing Eval state commitment chain is invalid"
            )
        previous_after = event["after_state_hash"]
    if not commitments or previous_after != sha256_bytes(canonical_json_bytes(state)):
        raise EvalContractError(
            "runtime Writing Eval state differs from Controller event commitments"
        )
    dispatch_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event_type") == "NODE_DISPATCH_PLANNED"
        and event.get("run_id") == run_id
        and event.get("node_id") == "review.parallel"
    ]
    if len(dispatch_indexes) != 1 or prepared_indexes[0] >= dispatch_indexes[0]:
        raise EvalContractError(
            "WRITING_EVAL_PREPARED must precede the one review.parallel dispatch"
        )
    completed_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event_type") == "WRITING_EVAL_COMPLETED"
        and event.get("run_id") == run_id
        and event.get("suite_id") == suite_id
        and (
            review_attempt_id is None
            or event.get("review_attempt_id") == review_attempt_id
        )
    ]
    if not require_completed:
        if completed_indexes:
            raise EvalContractError(
                "pre-registration must occur before WRITING_EVAL_COMPLETED"
            )
        return
    result_ref = state.get("writing_eval_result_ref")
    if (
        state.get("status") != "COMPLETED"
        or state.get("current_node") != "review.aggregate"
        or len(completed_indexes) != 1
        or completed_indexes[0] != len(events) - 1
        or not isinstance(result_ref, dict)
        or result_ref.get("attempt_id") != review_attempt_id
        or events[completed_indexes[0]].get("result_ref") != result_ref
    ):
        raise EvalContractError(
            "runtime evidence requires the exact terminal WRITING_EVAL_COMPLETED boundary"
        )


def _available_assets(project_root: Path, candidate_path: Path) -> list[dict[str, str]]:
    assets_root = candidate_path.parent / "assets"
    if not assets_root.exists():
        return []
    if not assets_root.is_dir() or assets_root.is_symlink():
        raise EvalContractError("Candidate assets must be a regular directory")
    refs: list[dict[str, str]] = []
    for path in sorted(assets_root.rglob("*")):
        if path.is_dir() and not path.is_symlink():
            continue
        if not path.is_file() or path.is_symlink():
            raise EvalContractError("Candidate assets must be regular files")
        refs.append(
            {
                "path": path.relative_to(project_root).as_posix(),
                "hash": sha256_file(path),
            }
        )
    return refs


def _validate_findings(value: Any, review: dict[str, Any]) -> tuple[list[dict[str, Any]], set[str]]:
    raw_findings = value
    if not isinstance(raw_findings, list):
        raise EvalContractError("accepted review.parallel Findings must be a list")
    findings: list[dict[str, Any]] = []
    ids: list[str] = []
    for index, raw in enumerate(raw_findings):
        if not isinstance(raw, dict):
            raise EvalContractError(f"accepted Findings[{index}] must be an object")
        if raw.get("reviewer_role") != "writing_standard" and raw.get("reviewer_profile") != "WRITING_STANDARD":
            continue
        finding = raw
        finding_id = _non_empty(finding.get("finding_id"), f"accepted Findings[{index}].finding_id")
        _non_empty(finding.get("concern_level"), f"accepted Findings[{index}].concern_level")
        _non_empty(
            finding.get("professional_recommendation"),
            f"accepted Findings[{index}].professional_recommendation",
        )
        ids.append(finding_id)
        findings.append(finding)
    if len(ids) != len(set(ids)) or set(ids) != set(review.get("finding_refs", [])):
        raise EvalContractError("accepted Writing Findings must equal exact writing review finding_refs")
    return findings, set(ids)


def _safe_runtime_id(value: Any, label: str) -> str:
    text = _non_empty(value, label)
    if "/" in text or ".." in text or "\\" in text:
        raise EvalContractError(f"{label} must be path-safe")
    return text


def _installed_exact_path(
    skill_root: Path, ref: Any, label: str
) -> tuple[dict[str, Any], Path]:
    exact = _exact_ref_shape(ref, label)
    relative = PurePosixPath(exact["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise EvalContractError(f"{label}.path must remain inside installed Skill")
    path = (skill_root / relative.as_posix()).resolve()
    try:
        path.relative_to(skill_root)
    except ValueError as error:
        raise EvalContractError(f"{label}.path escapes installed Skill") from error
    if not path.is_file() or path.is_symlink() or sha256_file(path) != exact["hash"]:
        raise EvalContractError(f"{label} must bind an exact installed regular file")
    return exact, path


def _installed_build_identity(skill_root: Path) -> dict[str, Any]:
    skill_root = skill_root.resolve()
    try:
        plugin_root = skill_root.parents[1]
        skill_relative = skill_root.relative_to(plugin_root).as_posix()
    except (IndexError, ValueError) as error:
        raise EvalContractError("installed Skill root layout is invalid") from error
    if skill_relative != "skills/better-product-graph":
        raise EvalContractError("installed Skill root must be skills/better-product-graph")
    manifest_path = plugin_root / "build-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise EvalContractError("installed build manifest must be one regular file")
    identity = verify_installed_identity(plugin_root)
    if identity.get("valid") is not True:
        raise EvalContractError(
            "installed build identity is invalid: " + "; ".join(identity.get("errors", []))
        )
    manifest = _load_json(manifest_path)
    git = manifest.get("git")
    plugin = manifest.get("plugin")
    host = manifest.get("host")
    if (
        not isinstance(git, dict)
        or git.get("dirty") is not False
        or not isinstance(git.get("commit"), str)
        or not git["commit"]
        or not isinstance(plugin, dict)
        or plugin.get("name") != "better-product-graph"
        or not isinstance(plugin.get("version"), str)
        or not isinstance(host, dict)
        or not isinstance(host.get("host_id"), str)
    ):
        raise EvalContractError("pre-registration requires an exact clean installed BPG build")
    public_controller = skill_root / "scripts" / "bpg_runner.py"
    if not public_controller.is_file() or public_controller.is_symlink():
        raise EvalContractError("installed public Controller entry is missing")
    inventory = manifest.get("inventory")
    expected_inventory_ref = next(
        (
            item
            for item in inventory
            if isinstance(item, dict)
            and item.get("path")
            == "skills/better-product-graph/scripts/bpg_runner.py"
        ),
        None,
    ) if isinstance(inventory, list) else None
    if (
        not isinstance(expected_inventory_ref, dict)
        or expected_inventory_ref.get("sha256") != sha256_file(public_controller)
    ):
        raise EvalContractError("installed public Controller differs from build inventory")
    return {
        "installed_skill_root": skill_root.as_posix(),
        "build_manifest_hash": sha256_file(manifest_path),
        "artifact_hash": identity["artifact_hash"],
        "plugin_name": plugin["name"],
        "plugin_version": plugin["version"],
        "host_id": host["host_id"],
        "git_commit": git["commit"],
        "git_dirty": False,
        "public_controller_ref": {
            "path": public_controller.relative_to(plugin_root).as_posix(),
            "hash": sha256_file(public_controller),
            "version": plugin["version"],
        },
    }


def _runtime_dispatch_snapshot(
    project_root: Path,
    installed_skill_root: Path,
    run_id: str,
    attempt_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    run_root = project_root / ".better-product-graph" / "runs" / run_id
    state_path = run_root / "state.json"
    events_path = run_root / "events.jsonl"
    if (
        not state_path.is_file()
        or state_path.is_symlink()
        or not events_path.is_file()
        or events_path.is_symlink()
    ):
        raise EvalContractError("pre-registration requires regular Run state and events")
    try:
        state = read_json(state_path)
        events = verify_event_chain(events_path)
    except IntegrityError as error:
        raise EvalContractError(f"pre-registration Run evidence is invalid: {error}") from error
    if state.get("run_id") != run_id:
        raise EvalContractError("pre-registration Run identity differs")
    _validate_writing_eval_runtime_identity(
        state,
        events,
        run_id,
        review_attempt_id=attempt_id,
        require_completed=False,
    )
    dispatches = [
        item
        for item in state.get("dispatch_attempts", [])
        if isinstance(item, dict)
        and item.get("attempt_id") == attempt_id
        and item.get("node_id") == "review.parallel"
    ]
    if len(dispatches) != 1:
        raise EvalContractError("pre-registration requires one exact review.parallel dispatch")
    dispatch = dispatches[0]
    contract = dispatch.get("contract")
    context = contract.get("writing_review_context") if isinstance(contract, dict) else None
    if (
        dispatch.get("status") != "DISPATCHED"
        or not isinstance(contract, dict)
        or not isinstance(context, dict)
        or contract.get("schema_version") != "node-dispatch.v1"
        or contract.get("node_id") != "review.parallel"
        or contract.get("attempt_id") != attempt_id
        or contract.get("instruction_variant") != "writing_eval"
        or contract.get("validator") != "writing_eval_review_parallel"
    ):
        raise EvalContractError("pre-registration dispatch contract is incomplete")
    graph_path = installed_skill_root / "references" / "graph" / "manifest.json"
    try:
        registry = NodeRegistry(installed_skill_root, graph_path)
        expected_dispatch = registry.dispatch_envelope(
            "review.parallel",
            attempt_id,
            contract.get("input_refs", []),
            contract.get("input_hashes", {}),
            instruction_variant="writing_eval",
        )
    except (NodeRegistryError, IntegrityError, KeyError, OSError, ValueError) as error:
        raise EvalContractError(f"installed public dispatch contract is invalid: {error}") from error
    if {key: value for key, value in contract.items() if key != "writing_review_context"} != expected_dispatch:
        raise EvalContractError("Run dispatch differs from exact installed public Controller contract")
    candidate_ref, _candidate_path = _managed_exact_path(
        project_root, context.get("candidate_ref"), "dispatch.candidate_ref"
    )
    installed_refs: dict[str, dict[str, Any]] = {}
    for field in ("profile_ref", "guide_ref", "output_contract_ref", "review_contract_ref"):
        installed_refs[field], _ = _installed_exact_path(
            installed_skill_root, context.get(field), f"dispatch.{field}"
        )
    resource_exact_refs = [
        {key: item.get(key) for key in ("path", "hash", "version")}
        for item in contract.get("resource_refs", [])
        if isinstance(item, dict)
    ]
    for field in ("profile_ref", "guide_ref", "review_contract_ref"):
        if resource_exact_refs.count(installed_refs[field]) != 1:
            raise EvalContractError(f"dispatch {field} lacks one exact installed resource binding")
    return state, events, dispatch, {
        "candidate_ref": candidate_ref,
        **installed_refs,
    }


def _write_private_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise EvalContractError("pre-registration checkpoint root must be a regular directory")
    path.parent.chmod(0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise EvalContractError("pre-registration checkpoint is one-time and cannot be overwritten") from error
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(payload) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        path.chmod(0o600)
    except Exception:
        if path.exists():
            path.unlink()
        raise


def preregister_runtime(
    project_root: Path,
    installed_skill_root: Path,
    checkpoint_root: Path,
    case_id: str,
    run_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    """Capture evaluator-private Controller evidence before the Reviewer can submit."""

    if case_id not in CASE_IDS:
        raise EvalContractError("pre-registration case_id is not in the immutable suite")
    project_root = project_root.resolve()
    installed_skill_root = installed_skill_root.resolve()
    checkpoint_root = checkpoint_root.resolve()
    try:
        checkpoint_root.relative_to(project_root)
    except ValueError as error:
        raise EvalContractError("checkpoint root must remain inside the evaluator project") from error
    if checkpoint_root == project_root / ".better-product-graph" or (
        project_root / ".better-product-graph"
    ) in checkpoint_root.parents:
        raise EvalContractError("checkpoint root must remain outside runtime evidence")
    run_id = _safe_runtime_id(run_id, "pre-registration.run_id")
    attempt_id = _safe_runtime_id(attempt_id, "pre-registration.review_attempt_id")
    installed_build = _installed_build_identity(installed_skill_root)
    state, events, dispatch, refs = _runtime_dispatch_snapshot(
        project_root, installed_skill_root, run_id, attempt_id
    )
    if (
        state.get("current_node") != "review.parallel"
        or attempt_id in state.get("consumed_attempts", [])
        or not isinstance(state.get("state_version"), int)
    ):
        raise EvalContractError("pre-registration must occur before review.parallel is consumed")
    run_root = project_root / ".better-product-graph" / "runs" / run_id
    result_path = run_root / "attempts" / attempt_id / "node-result.json"
    receipt_path = result_path.with_name("result-receipt.json")
    if result_path.exists() or receipt_path.exists():
        raise EvalContractError("pre-registration cannot occur after Reviewer result materialization")
    if not events or (
        events[-1].get("event_type") != "NODE_CALL_STARTED"
        or events[-1].get("attempt_id") != attempt_id
    ):
        raise EvalContractError("pre-registration must capture the exact started Reviewer frontier")
    challenge = "challenge-" + secrets.token_hex(24)
    runtime_checkpoint = {
        "runtime_evidence_root": ".better-product-graph",
        "run_id": run_id,
        "review_attempt_id": attempt_id,
        "initial_state_version": state["state_version"],
        "initial_event_count": len(events),
        "initial_event_head": events[-1]["event_hash"],
        "dispatch_hash": sha256_bytes(canonical_json_bytes(dispatch)),
        "dispatch_contract_hash": sha256_bytes(canonical_json_bytes(dispatch["contract"])),
        **refs,
    }
    payload = {
        "schema_version": "prd-readability-preregistration.v1",
        "suite_id": _suite()["suite_id"],
        "case_id": case_id,
        "agent_case_id": _expected()["cases"][case_id]["agent_case_id"],
        "challenge": challenge,
        "evidence_class": "EVALUATOR_PREREGISTERED_CONTROLLER_EVIDENCE",
        "claim_boundary": "Evaluator-held local checkpoint; not external cryptographic proof.",
        "installed_build": installed_build,
        "runtime_checkpoint": runtime_checkpoint,
    }
    checkpoint_path = checkpoint_root / f"{challenge}.json"
    candidate_path = (project_root / PurePosixPath(refs["candidate_ref"]["path"])).resolve()
    if checkpoint_root == candidate_path.parent or candidate_path.parent in checkpoint_root.parents:
        raise EvalContractError("checkpoint root must remain outside the Reviewer workspace")
    _write_private_checkpoint(checkpoint_path, payload)
    checkpoint_ref = {
        "path": checkpoint_path.relative_to(project_root).as_posix(),
        "hash": sha256_file(checkpoint_path),
        "version": 1,
    }
    return {
        "status": "PREREGISTERED",
        "evidence_class": payload["evidence_class"],
        "checkpoint_ref": checkpoint_ref,
        "evaluation_record_seed": {
            "schema_version": "prd-readability-agent-result.v2",
            "case_id": case_id,
            "runtime_evidence_root": ".better-product-graph",
            "run_id": run_id,
            "review_attempt_id": attempt_id,
            "preregistration_ref": checkpoint_ref,
        },
        "claim_boundary": payload["claim_boundary"],
    }


def _load_preregistration(
    project_root: Path, record: dict[str, Any], case_id: str
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    checkpoint_ref, checkpoint_path = _managed_exact_path(
        project_root,
        record.get("preregistration_ref"),
        "evaluation_record.preregistration_ref",
    )
    if stat.S_IMODE(checkpoint_path.stat().st_mode) != 0o600:
        raise EvalContractError("pre-registration checkpoint must remain evaluator-private mode 0600")
    checkpoint = _closed(
        _load_json(checkpoint_path), PREREGISTRATION_FIELDS, "preregistration"
    )
    if (
        checkpoint.get("schema_version") != "prd-readability-preregistration.v1"
        or checkpoint.get("suite_id") != _suite()["suite_id"]
        or checkpoint.get("case_id") != case_id
        or checkpoint.get("agent_case_id")
        != _expected()["cases"][case_id]["agent_case_id"]
        or checkpoint.get("evidence_class")
        != "EVALUATOR_PREREGISTERED_CONTROLLER_EVIDENCE"
        or checkpoint.get("claim_boundary")
        != "Evaluator-held local checkpoint; not external cryptographic proof."
    ):
        raise EvalContractError("pre-registration checkpoint identity is invalid")
    challenge = _non_empty(checkpoint.get("challenge"), "preregistration.challenge")
    if not challenge.startswith("challenge-") or len(challenge) != 58:
        raise EvalContractError("pre-registration challenge format is invalid")
    installed = _closed(
        checkpoint.get("installed_build"),
        INSTALLED_BUILD_FIELDS,
        "preregistration.installed_build",
    )
    current_installed = _installed_build_identity(
        Path(_non_empty(installed.get("installed_skill_root"), "installed_skill_root"))
    )
    if current_installed != installed:
        raise EvalContractError("installed build identity changed after pre-registration")
    runtime = _closed(
        checkpoint.get("runtime_checkpoint"),
        RUNTIME_CHECKPOINT_FIELDS,
        "preregistration.runtime_checkpoint",
    )
    if (
        runtime.get("runtime_evidence_root") != record.get("runtime_evidence_root")
        or runtime.get("run_id") != record.get("run_id")
        or runtime.get("review_attempt_id") != record.get("review_attempt_id")
    ):
        raise EvalContractError("pre-registration does not bind the evaluation Run/attempt")
    for field in (
        "candidate_ref",
        "profile_ref",
        "guide_ref",
        "output_contract_ref",
        "review_contract_ref",
    ):
        _exact_ref_shape(runtime.get(field), f"preregistration.runtime_checkpoint.{field}")
    return checkpoint, checkpoint_ref, checkpoint_path


def _runtime_attempt_evidence(
    project_root: Path,
    record: dict[str, Any],
    preregistration: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path, list[dict[str, Any]], dict[str, Any]]:
    if record.get("runtime_evidence_root") != ".better-product-graph":
        raise EvalContractError("runtime evidence root must be exact .better-product-graph")
    run_id = _safe_runtime_id(record.get("run_id"), "evaluation_record.run_id")
    attempt_id = _safe_runtime_id(
        record.get("review_attempt_id"), "evaluation_record.review_attempt_id"
    )
    runtime_root = project_root / ".better-product-graph"
    run_root = runtime_root / "runs" / run_id
    if (
        not runtime_root.is_dir()
        or runtime_root.is_symlink()
        or not run_root.is_dir()
        or run_root.is_symlink()
    ):
        raise EvalContractError("runtime evidence Run is absent from .better-product-graph")
    state_path = run_root / "state.json"
    events_path = run_root / "events.jsonl"
    if (
        not state_path.is_file()
        or state_path.is_symlink()
        or not events_path.is_file()
        or events_path.is_symlink()
    ):
        raise EvalContractError("runtime evidence requires regular state.json and events.jsonl")
    try:
        state = read_json(state_path)
        events = verify_event_chain(events_path)
    except IntegrityError as error:
        raise EvalContractError(f"runtime evidence chain is invalid: {error}") from error
    if state.get("run_id") != run_id:
        raise EvalContractError("runtime evidence state Run identity differs")
    if preregistration is not None:
        _validate_writing_eval_runtime_identity(
            state,
            events,
            run_id,
            review_attempt_id=attempt_id,
            require_completed=True,
        )
    if attempt_id not in state.get("consumed_attempts", []):
        raise EvalContractError("review.parallel attempt is not consumed by runtime state")
    dispatches = [
        item
        for item in state.get("dispatch_attempts", [])
        if isinstance(item, dict)
        and item.get("attempt_id") == attempt_id
        and item.get("node_id") == "review.parallel"
    ]
    if len(dispatches) != 1:
        raise EvalContractError("runtime evidence lacks one exact review.parallel dispatch")
    dispatch = dispatches[0]
    contract = dispatch.get("contract")
    context = contract.get("writing_review_context") if isinstance(contract, dict) else None
    if (
        not isinstance(contract, dict)
        or contract.get("schema_version") != "node-dispatch.v1"
        or contract.get("attempt_id") != attempt_id
        or contract.get("node_id") != "review.parallel"
        or dispatch.get("status") != "DISPATCHED"
        or not isinstance(context, dict)
    ):
        raise EvalContractError("runtime review.parallel dispatch contract is incomplete")
    if preregistration is not None:
        checkpoint = preregistration["runtime_checkpoint"]
        initial_count = checkpoint.get("initial_event_count")
        initial_version = checkpoint.get("initial_state_version")
        if (
            isinstance(initial_count, bool)
            or not isinstance(initial_count, int)
            or initial_count < 1
            or len(events) <= initial_count
            or events[initial_count - 1].get("event_hash")
            != checkpoint.get("initial_event_head")
            or isinstance(initial_version, bool)
            or not isinstance(initial_version, int)
            or not isinstance(state.get("state_version"), int)
            or state["state_version"] <= initial_version
        ):
            raise EvalContractError(
                "runtime event chain does not strictly extend the pre-registered frontier"
            )
        if (
            sha256_bytes(canonical_json_bytes(dispatch)) != checkpoint.get("dispatch_hash")
            or sha256_bytes(canonical_json_bytes(contract))
            != checkpoint.get("dispatch_contract_hash")
        ):
            raise EvalContractError("review.parallel dispatch changed after pre-registration")
        for field in (
            "candidate_ref",
            "profile_ref",
            "guide_ref",
            "output_contract_ref",
            "review_contract_ref",
        ):
            if context.get(field) != checkpoint.get(field):
                raise EvalContractError(
                    f"review.parallel {field} differs from pre-registration"
                )
    for field in (
        "candidate_ref",
        "profile_ref",
        "guide_ref",
        "output_contract_ref",
        "review_contract_ref",
        "author_execution_ref",
    ):
        if not isinstance(context.get(field), dict):
            raise EvalContractError(f"runtime Writing Review context lacks {field}")
    for field in (
        "candidate_ref",
        "profile_ref",
        "guide_ref",
        "output_contract_ref",
        "review_contract_ref",
    ):
        _exact_ref_shape(context[field], f"runtime Writing Review context {field}")
    result_path = run_root / "attempts" / attempt_id / "node-result.json"
    receipt_path = result_path.with_name("result-receipt.json")
    if (
        not result_path.is_file()
        or result_path.is_symlink()
        or not receipt_path.is_file()
        or receipt_path.is_symlink()
    ):
        raise EvalContractError("runtime evidence requires exact Node Result and Controller receipt")
    try:
        result = read_json(result_path)
        receipt = read_json(receipt_path)
    except IntegrityError as error:
        raise EvalContractError(f"runtime result evidence is invalid: {error}") from error
    result_hash = sha256_file(result_path)
    if (
        result.get("node_id") != "review.parallel"
        or result.get("attempt_id") != attempt_id
        or result.get("producer", {}).get("kind") != "HOST_AGENT"
        or receipt.get("schema_version") != "node-result-receipt.v1"
        or receipt.get("attempt_id") != attempt_id
        or receipt.get("node_id") != "review.parallel"
        or receipt.get("result_hash") != result_hash
    ):
        raise EvalContractError("runtime Node Result receipt does not prove accepted review.parallel bytes")

    def unique_event(event_types: set[str], **fields: Any) -> dict[str, Any]:
        matches = [
            event
            for event in events
            if event.get("event_type") in event_types
            and all(event.get(key) == value for key, value in fields.items())
        ]
        if len(matches) != 1:
            raise EvalContractError(
                "runtime evidence lacks one exact " + "/".join(sorted(event_types)) + " event"
            )
        return matches[0]

    unique_event(
        {"NODE_DISPATCH_PLANNED"},
        run_id=run_id,
        attempt_id=attempt_id,
        node_id="review.parallel",
    )
    unique_event({"NODE_CALL_STARTED"}, run_id=run_id, attempt_id=attempt_id)
    unique_event(
        {"NODE_RESULT_PERSISTED", "NODE_RESULT_RECOVERED"},
        run_id=run_id,
        attempt_id=attempt_id,
        result_hash=result_hash,
    )
    unique_event(
        {"NODE_TRANSITION_COMMITTED"},
        run_id=run_id,
        attempt_id=attempt_id,
        from_node="review.parallel",
    )
    return result, result_path, events, context


def _score_case(
    project_root: Path,
    results_root: Path,
    case_id: str,
    expected: dict[str, Any],
    suite: dict[str, Any],
    *,
    require_preregistration: bool,
) -> dict[str, Any]:
    record_path = results_root / case_id / "evaluation-record.json"
    if not record_path.exists():
        return {"status": "NOT_RUN", "issues": ["evaluation-record.json is absent"]}
    issues: list[str] = []
    refs: dict[str, Any] = {}
    try:
        fields = RESULT_FIELDS if require_preregistration else SYNTHETIC_RESULT_FIELDS
        record = _closed(_load_json(record_path), fields, "evaluation_record")
        expected_schema = (
            "prd-readability-agent-result.v2"
            if require_preregistration
            else "prd-readability-agent-result.v1"
        )
        if record.get("schema_version") != expected_schema:
            raise EvalContractError("evaluation_record.schema_version is invalid")
        if record.get("case_id") != case_id:
            raise EvalContractError("evaluation_record.case_id mismatch")
        preregistration = None
        checkpoint_ref = None
        checkpoint_path = None
        if require_preregistration:
            preregistration, checkpoint_ref, checkpoint_path = _load_preregistration(
                project_root, record, case_id
            )
        result, result_path, events, context = _runtime_attempt_evidence(
            project_root, record, preregistration
        )
        candidate_ref, candidate_path = _managed_exact_path(
            project_root, context.get("candidate_ref"), "dispatch.candidate_ref"
        )
        if candidate_ref["hash"] != suite["case_hashes"][case_id]:
            raise EvalContractError("candidate_ref does not bind the immutable suite Case")
        if checkpoint_path is not None and (
            checkpoint_path.parent == candidate_path.parent
            or candidate_path.parent in checkpoint_path.parents
        ):
            raise EvalContractError(
                "pre-registration checkpoint must remain outside Reviewer workspace"
            )
        output = result.get("semantic_output")
        if not isinstance(output, dict):
            raise EvalContractError("accepted review.parallel semantic_output is missing")
        review_ref = output.get("writing_coverage_ref")
        artifact_refs = [
            {key: item.get(key) for key in ("path", "hash", "version")}
            for item in result.get("artifact_refs", [])
            if isinstance(item, dict) and item.get("role") == "writing_coverage"
        ]
        if len(artifact_refs) != 1 or artifact_refs[0] != review_ref:
            raise EvalContractError(
                "accepted review.parallel result does not bind one exact Writing Review"
            )
        review_ref, review_path = _managed_exact_path(
            project_root, review_ref, "accepted.writing_review_ref"
        )
        refs = {
            "candidate_ref": candidate_ref,
            "writing_review_ref": review_ref,
            "runtime_result_ref": {
                "path": result_path.relative_to(project_root).as_posix(),
                "hash": sha256_file(result_path),
                "version": 1,
            },
            "runtime_event_head": events[-1]["event_hash"],
        }
        if checkpoint_ref is not None:
            refs["preregistration_ref"] = checkpoint_ref
        review = _load_json(review_path)
        if preregistration is not None:
            challenge = preregistration["challenge"]
            if challenge in json.dumps(
                {"dispatch": context, "result": result, "review": review},
                ensure_ascii=False,
                sort_keys=True,
            ):
                raise EvalContractError(
                    "evaluator-private challenge leaked into Reviewer inputs or outputs"
                )
        findings, finding_ids = _validate_findings(output.get("findings"), review)
        if any(
            review.get(field) != context.get(field)
            for field in (
                "candidate_ref",
                "candidate_tree_hash",
                "profile_ref",
                "guide_ref",
                "output_contract_ref",
                "author_execution_ref",
                "isolated_input_refs",
            )
        ):
            raise EvalContractError(
                "Writing Review Candidate/Profile/Guide/Contract authority differs from accepted dispatch"
            )
        validate_writing_review(
            review,
            context=context,
            candidate_line_count=max(1, len(candidate_path.read_text(encoding="utf-8").splitlines())),
            available_asset_refs=_available_assets(project_root, candidate_path),
            available_finding_ids=finding_ids,
        )
        if context.get("candidate_asset_refs", []) != _available_assets(
            project_root, candidate_path
        ):
            raise EvalContractError(
                "Candidate asset refs differ from the accepted review.parallel dispatch"
            )
        actual_visual = review["visual_model"]["verdict"]
        if actual_visual != expected.get("visual_model"):
            issues.append(f"visual_model mismatch: expected {expected.get('visual_model')}, got {actual_visual}")
        categories = {
            category
            for diagnosis in review.get("diagnoses", [])
            for category in diagnosis.get("categories", [])
        }
        missing_categories = sorted(set(expected.get("categories", [])) - categories)
        if missing_categories:
            issues.append(f"missing diagnosis categories: {missing_categories}")
        allowed_repairs = set(expected.get("allowed_repairs", []))
        expected_categories = set(expected.get("categories", []))
        primary_diagnoses = [
            diagnosis
            for diagnosis in review.get("diagnoses", [])
            if expected_categories
            and expected_categories <= set(diagnosis.get("categories", []))
        ]
        primary_repairs = {
            diagnosis.get("primary_repair", {}).get("technique")
            for diagnosis in primary_diagnoses
        }
        if allowed_repairs and (
            not primary_repairs or not primary_repairs <= allowed_repairs
        ):
            issues.append(
                "primary repairs for the expected main problem are outside expected envelope: "
                f"{sorted(primary_repairs)}"
            )
        material_levels = set(suite["material_concern_levels"])
        material = any(item["concern_level"] in material_levels for item in findings)
        expected_material = expected.get("material_finding")
        if isinstance(expected_material, bool) and material is not expected_material:
            issues.append(f"material Finding mismatch: expected {expected_material}, got {material}")
    except (EvalContractError, WritingReviewError, OSError, UnicodeError, ValueError) as error:
        issues.append(str(error))
    return {
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
        **refs,
    }


def score_results(project_root: Path, results_root: Path) -> dict[str, Any]:
    contract_issues = _contract_issues()
    if contract_issues:
        raise EvalContractError("; ".join(contract_issues))
    project_root = project_root.resolve()
    results_root = results_root.resolve()
    suite = _suite()
    expected_cases = _expected()["cases"]
    cases = {
        case_id: _score_case(
            project_root,
            results_root,
            case_id,
            expected_cases[case_id],
            suite,
            require_preregistration=True,
        )
        for case_id in CASE_IDS
    }
    statuses = {item["status"] for item in cases.values()}
    if statuses == {"NOT_RUN"}:
        evidence_status = "NOT_RUN"
    elif statuses == {"PASS"}:
        evidence_status = "PASS"
    else:
        evidence_status = "FAIL"
    for item in cases.values():
        if item["status"] == "PASS":
            item["status"] = "EVALUATOR_PREREGISTERED_CONTROLLER_EVIDENCE_PASS"
    return {
        "suite_id": suite["suite_id"],
        "contract_status": "CONTRACT_PASS",
        "evaluator_preregistered_controller_evidence_status": evidence_status,
        "agent_runtime_status": "NOT_RUN",
        "human_reader_validation": "NOT_RUN",
        "promotion_eligible": False,
        "cases": cases,
        "claim_boundary": (
            "EVALUATOR_PREREGISTERED_CONTROLLER_EVIDENCE is an evaluator-held local "
            "checkpoint, not external cryptographic proof. Five-fixture scoring cannot "
            "promote v0.3; live evaluator custody, one real PRD independent review, and "
            "the parent promotion audit are still required."
        ),
    }


def score_synthetic_contract(project_root: Path, results_root: Path) -> dict[str, Any]:
    """TEST_ONLY: exercise scorer structure without producing Agent evidence."""

    contract_issues = _contract_issues()
    if contract_issues:
        raise EvalContractError("; ".join(contract_issues))
    project_root = project_root.resolve()
    results_root = results_root.resolve()
    suite = _suite()
    expected_cases = _expected()["cases"]
    cases = {
        case_id: _score_case(
            project_root,
            results_root,
            case_id,
            expected_cases[case_id],
            suite,
            require_preregistration=False,
        )
        for case_id in CASE_IDS
    }
    raw_statuses = {item["status"] for item in cases.values()}
    if raw_statuses == {"NOT_RUN"}:
        synthetic_status = "NOT_RUN"
    elif raw_statuses == {"PASS"}:
        synthetic_status = "SYNTHETIC_CONTRACT_PASS"
    else:
        synthetic_status = "SYNTHETIC_CONTRACT_FAIL"
    for item in cases.values():
        if item["status"] == "PASS":
            item["status"] = "SYNTHETIC_CONTRACT_PASS"
    return {
        "suite_id": suite["suite_id"],
        "contract_status": "CONTRACT_PASS",
        "synthetic_contract_status": synthetic_status,
        "agent_runtime_status": "NOT_RUN",
        "human_reader_validation": "NOT_RUN",
        "promotion_eligible": False,
        "cases": cases,
        "claim_boundary": (
            "TEST_ONLY synthetic trees exercise contract wiring and cannot produce "
            "Agent Product Eval evidence."
        ),
    }


def run() -> dict[str, Any]:
    issues = _contract_issues()
    suite_id = None
    try:
        suite_id = _suite().get("suite_id")
    except EvalContractError:
        pass
    return {
        "suite_id": suite_id,
        "contract_status": "CONTRACT_FAIL" if issues else "CONTRACT_PASS",
        "agent_runtime_status": "NOT_RUN",
        "human_reader_validation": "NOT_RUN",
        "issues": issues,
        "cases": {case_id: {"agent_runtime_status": "NOT_RUN"} for case_id in CASE_IDS},
        "claim_boundary": "Fixture contract validation is not Agent Product Eval.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-agent-workspace", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--score-results", type=Path)
    parser.add_argument("--preregister-case", choices=CASE_IDS)
    parser.add_argument("--installed-skill-root", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--review-attempt-id")
    parser.add_argument("--checkpoint-root", type=Path)
    args = parser.parse_args()
    try:
        if args.preregister_case is not None:
            required = {
                "--project-root": args.project_root,
                "--installed-skill-root": args.installed_skill_root,
                "--run-id": args.run_id,
                "--review-attempt-id": args.review_attempt_id,
                "--checkpoint-root": args.checkpoint_root,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                raise EvalContractError(
                    ", ".join(missing) + " required with --preregister-case"
                )
            if args.score_results is not None or args.emit_agent_workspace is not None:
                raise EvalContractError(
                    "--preregister-case cannot be combined with emit or score"
                )
            report = preregister_runtime(
                args.project_root,
                args.installed_skill_root,
                args.checkpoint_root,
                args.preregister_case,
                args.run_id,
                args.review_attempt_id,
            )
            report["contract_status"] = "CONTRACT_PASS"
            report["agent_runtime_status"] = "NOT_RUN"
            report["human_reader_validation"] = "NOT_RUN"
        elif args.score_results is not None:
            if args.project_root is None:
                raise EvalContractError("--project-root is required with --score-results")
            if any(
                value is not None
                for value in (
                    args.installed_skill_root,
                    args.run_id,
                    args.review_attempt_id,
                    args.checkpoint_root,
                )
            ):
                raise EvalContractError(
                    "pre-registration arguments are only valid with --preregister-case"
                )
            report = score_results(args.project_root, args.score_results)
        else:
            if any(
                value is not None
                for value in (
                    args.project_root,
                    args.installed_skill_root,
                    args.run_id,
                    args.review_attempt_id,
                    args.checkpoint_root,
                )
            ):
                raise EvalContractError(
                    "project/runtime arguments require score or pre-registration"
                )
            if args.emit_agent_workspace is not None:
                emit_agent_workspace(args.emit_agent_workspace)
            report = run()
    except EvalContractError as error:
        report = {
            "contract_status": "CONTRACT_FAIL",
            "agent_runtime_status": "NOT_RUN",
            "human_reader_validation": "NOT_RUN",
            "error": str(error),
        }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("contract_status") == "CONTRACT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
