"""Exact-ref receipt contracts; only StateController performs issuance."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .contracts import PolicyViolation, validate_node_result_producer
from .delivery_contract import DeliveryContractError, derive_active_scope_ref
from .documents import (
    hash_tree,
    validate_document_experience,
    validate_lifecycle_expression_reconciliation,
)
from .document_experience_profile import (
    DocumentExperienceProfileError,
    resolve_prd_document_experience,
)
from .node_validation import NodeValidationError, validate_node_output
from .prd_contract import PRDContractError, assemble_prd
from .storage import IntegrityError, read_json, sha256_file, verify_event_chain
from .templates import TemplateSelection
from .upstream_authority import (
    UpstreamAuthorityError,
    validate_ready_decision,
    validate_ready_evidence,
)


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ReceiptError(ValueError):
    """A receipt or one of its exact subject refs is invalid."""


REQUIRED_SUBJECT_ROLES = {
    "review_finalize": frozenset(
        {
            "candidate_document",
            "review_companion",
            "review_aggregate",
            "review_dispositions",
            "writing_coverage",
        }
    ),
    "document_experience": frozenset(
        {
            "candidate_document",
            "review_companion",
            "template_profile",
            "version_record",
            "document_changelog",
        }
    ),
    "audit_integrity": frozenset({"audit_snapshot"}),
    "mechanical_contracts": frozenset(
        {
            "candidate_document",
            "upstream_product_plan",
            "upstream_roadmap",
            "upstream_slice",
            "upstream_knowledge",
            "mechanical_validation",
        }
    ),
}

READY_RULES_VERSION = "prd-ready.v1.4-delivery-contracts.v2"


def controller_subject_ref(role: str, ref: dict[str, Any]) -> dict[str, Any]:
    """Apply a Controller-owned role after retaining a caller's declared role."""

    subject = dict(ref) if isinstance(ref, dict) else {}
    declared_role = subject.pop("role", None)
    subject.pop("declared_role", None)
    subject["role"] = role
    if isinstance(declared_role, str) and declared_role and declared_role != role:
        subject["declared_role"] = declared_role
    return subject


def resolve_file_ref(project_root: Path, ref: dict[str, Any], label: str) -> Path:
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise ReceiptError(f"{label} exact file ref is missing")
    root = project_root.resolve()
    raw = Path(ref["path"])
    path = (raw if raw.is_absolute() else root / raw).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ReceiptError(f"{label} ref escapes project root") from error
    if not path.is_file() or path.is_symlink():
        raise ReceiptError(f"{label} exact file ref is missing")
    if sha256_file(path) != ref.get("hash"):
        raise ReceiptError(f"{label} hash mismatch")
    return path


def normalize_subject_refs(
    project_root: Path,
    kind: str,
    subject_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    required = REQUIRED_SUBJECT_ROLES.get(kind)
    if required is None:
        raise ReceiptError(f"unsupported receipt kind: {kind}")
    if not isinstance(subject_refs, list) or not subject_refs:
        raise ReceiptError(f"{kind} receipt subject refs cannot be empty")
    roles = [item.get("role") for item in subject_refs if isinstance(item, dict)]
    exact_roles = set(roles)
    roles_valid = exact_roles == required
    if kind == "mechanical_contracts":
        variable_patterns = {
            "decision": (re.compile(r"^upstream_decision(?::([0-9]+))?$"), True),
            "evidence": (re.compile(r"^upstream_evidence(?::([0-9]+))?$"), False),
        }
        fixed = required
        roles_valid = fixed.issubset(exact_roles)
        for label, (pattern, required_nonempty) in variable_patterns.items():
            matches = [role for role in roles if isinstance(role, str) and pattern.fullmatch(role)]
            if required_nonempty and not matches:
                roles_valid = False
                continue
            unindexed = [role for role in matches if role == f"upstream_{label}"]
            indexed = [role for role in matches if role != f"upstream_{label}"]
            if (unindexed and indexed) or len(unindexed) > 1:
                roles_valid = False
            if indexed:
                indices = sorted(int(pattern.fullmatch(role).group(1)) for role in indexed)
                if indices != list(range(len(indices))):
                    roles_valid = False
        allowed_variable = {
            role
            for role in roles
            if isinstance(role, str)
            and any(pattern.fullmatch(role) for pattern, _ in variable_patterns.values())
        }
        if exact_roles - fixed - allowed_variable:
            roles_valid = False
    if len(roles) != len(subject_refs) or len(set(roles)) != len(roles) or not roles_valid:
        raise ReceiptError(
            f"{kind} receipt subject roles do not exactly cover required facts"
        )
    root = project_root.resolve()
    normalized: list[dict[str, Any]] = []
    seen_identities: set[tuple[str, str, Any]] = set()
    for ref in subject_refs:
        role = ref["role"]
        path = resolve_file_ref(root, ref, f"{kind} subject {role}")
        exact = {
            "role": role,
            "path": path.relative_to(root).as_posix(),
            "hash": sha256_file(path),
        }
        if "version" in ref:
            if not isinstance(ref["version"], (int, str)) or ref["version"] == "":
                raise ReceiptError(f"{kind} subject {role} version is invalid")
            exact["version"] = ref["version"]
        identity = (exact["path"], exact["hash"], exact.get("version"))
        if identity in seen_identities:
            raise ReceiptError(f"{kind} receipt has duplicate exact subject ref: {exact['path']}")
        seen_identities.add(identity)
        if isinstance(ref.get("declared_role"), str) and ref["declared_role"]:
            exact["declared_role"] = ref["declared_role"]
        normalized.append(exact)
    return sorted(normalized, key=lambda item: item["role"])


def evaluate_receipt_subjects(
    project_root: Path,
    kind: str,
    normalized_subjects: list[dict[str, Any]],
    *,
    run_id: str,
    node_id: str,
    attempt_id: str,
    candidate_ref: dict[str, Any],
    template_selection: dict[str, Any],
) -> dict[str, Any]:
    """Recompute the exact fact named by a receipt kind."""

    root = project_root.resolve()
    subjects = {item["role"]: item for item in normalized_subjects}
    candidate = subjects.get("candidate_document")
    if candidate is not None and (
        candidate.get("path") != candidate_ref.get("path")
        or candidate.get("hash") != candidate_ref.get("hash")
    ):
        raise ReceiptError(f"{kind} Candidate subject differs from current Run Candidate")

    candidate_root = (root / candidate_ref.get("artifact_path", "")).resolve()
    if (
        not candidate_root.is_dir()
        or candidate_root.is_symlink()
        or hash_tree(candidate_root) != candidate_ref.get("tree_hash")
    ):
        raise ReceiptError(f"{kind} current Candidate artifact tree is missing or changed")

    metadata: dict[str, Any] = {}
    if kind == "document_experience":
        metadata_paths = list(candidate_root.glob("*.metadata.json"))
        if len(metadata_paths) != 1:
            raise ReceiptError(f"{kind} Candidate metadata is not self-contained")
        metadata = read_json(metadata_paths[0])

    def json_subject(role: str) -> dict[str, Any]:
        try:
            return read_json(root / subjects[role]["path"])
        except (KeyError, OSError, IntegrityError) as error:
            raise ReceiptError(f"{kind} subject {role} is not valid JSON") from error

    if kind == "review_finalize":
        companion = json_subject("review_companion")
        aggregate = json_subject("review_aggregate")
        dispositions = json_subject("review_dispositions")
        writing_coverage = json_subject("writing_coverage")
        attempts = aggregate.get("attempts", [])
        roles = {
            role
            for attempt in attempts
            if isinstance(attempt, dict) and attempt.get("status") == "COMPLETED"
            for role in attempt.get("roles_covered", [])
        }
        findings = aggregate.get("findings", [])
        finding_ids = [
            item.get("finding_id") for item in findings if isinstance(item, dict)
        ]
        writing_finding_ids = {
            item.get("finding_id")
            for item in findings
            if isinstance(item, dict)
            and (
                item.get("reviewer_role") == "writing_standard"
                or item.get("reviewer_profile") == "WRITING_STANDARD"
            )
        }
        disposition_items = dispositions.get("dispositions", [])
        disposition_ids = [
            item.get("finding_id")
            for item in disposition_items
            if isinstance(item, dict) and item.get("status")
        ]
        if (
            companion.get("schema_version") != "prd-review-companion.v1"
            or companion.get("status") != "FINALIZED"
            or companion.get("authority") != "ADVISORY_ONLY"
            or companion.get("candidate_hash") != candidate_ref.get("hash")
            or companion.get("version") != candidate_ref.get("version")
            or not isinstance(companion.get("finding_count"), int)
            or subjects["review_companion"].get("path") != candidate_ref.get("review_path")
            or subjects["review_companion"].get("hash") != candidate_ref.get("review_hash")
            or companion.get("aggregate_ref") != {
                key: subjects["review_aggregate"].get(key) for key in ("path", "hash", "version")
            }
            or companion.get("dispositions_ref") != {
                key: subjects["review_dispositions"].get(key) for key in ("path", "hash", "version")
            }
            or companion.get("writing_coverage_ref")
            != {
                key: subjects["writing_coverage"].get(key)
                for key in ("path", "hash", "version")
            }
            or aggregate.get("schema_version") != "review-aggregate.v1"
            or aggregate.get("authority") != "ADVISORY_ONLY"
            or aggregate.get("candidate_ref", {}).get("path") != candidate_ref.get("path")
            or aggregate.get("candidate_ref", {}).get("hash") != candidate_ref.get("hash")
            or aggregate.get("candidate_ref", {}).get("version") != candidate_ref.get("version")
            or not {"product", "engineering_feasibility", "testability"}.issubset(roles)
            or not isinstance(findings, list)
            or any(not item for item in finding_ids)
            or len(set(finding_ids)) != len(finding_ids)
            or dispositions.get("schema_version") != "review-dispositions.v1"
            or dispositions.get("candidate_hash") != candidate_ref.get("hash")
            or dispositions.get("candidate_version") != candidate_ref.get("version")
            or sorted(disposition_ids) != sorted(finding_ids)
            or len(disposition_ids) != len(set(disposition_ids))
            or companion.get("finding_count") != len(finding_ids)
            or aggregate.get("writing_coverage_ref")
            != {
                key: subjects["writing_coverage"].get(key)
                for key in ("path", "hash", "version")
            }
            or writing_coverage.get("schema_version")
            != "document-experience-coverage.v1"
            or writing_coverage.get("candidate_ref", {}).get("path")
            != candidate_ref.get("path")
            or writing_coverage.get("candidate_ref", {}).get("hash")
            != candidate_ref.get("hash")
            or writing_coverage.get("candidate_ref", {}).get("version")
            != candidate_ref.get("version")
            or len(writing_coverage.get("required_rule_results", [])) != 13
            or len(writing_coverage.get("delivery_check_results", [])) != 10
            or set(writing_coverage.get("finding_refs", [])) != writing_finding_ids
        ):
            raise ReceiptError(
                "review_finalize Finding/disposition evidence is not an exact finalized advisory review"
            )
        observed = {"review_status": "FINALIZED", "finding_count": companion["finding_count"]}
    elif kind == "document_experience":
        document = (root / subjects["candidate_document"]["path"]).read_text(encoding="utf-8")
        experience = validate_document_experience(document, "prd")
        try:
            expected_document_experience = resolve_prd_document_experience()
        except DocumentExperienceProfileError as error:
            raise ReceiptError(
                f"document_experience runtime binding is invalid: {error}"
            ) from error
        template = json_subject("template_profile")
        version = json_subject("version_record")
        companion = json_subject("review_companion")
        changelog = (root / subjects["document_changelog"]["path"]).read_text(encoding="utf-8")
        if experience.status != "PASS":
            raise ReceiptError("document_experience Candidate failed: " + ", ".join(experience.issues))
        if metadata.get("document_experience") != expected_document_experience:
            raise ReceiptError(
                "document_experience Candidate does not bind the exact released writing profile"
            )
        if (
            companion.get("status") != "FINALIZED"
            or companion.get("candidate_hash") != candidate_ref.get("hash")
            or subjects["review_companion"].get("path")
            != candidate_ref.get("review_path")
            or subjects["review_companion"].get("hash")
            != candidate_ref.get("review_hash")
        ):
            raise ReceiptError(
                "document_experience lifecycle authority is not the exact finalized companion"
            )
        if (
            template.get("schema_version") != "template-profile-evidence.v1"
            or template.get("profile_id") != template_selection.get("profile_id")
            or template.get("version") != template_selection.get("version")
            or template.get("template_path") != template_selection.get("relative_path")
            or template.get("template_hash") != template_selection.get("sha256")
            or template.get("source_kind") != template_selection.get("source_kind")
            or template.get("selection_source") != template_selection.get("selection_source")
            or template.get("fallback_reason") != template_selection.get("fallback_reason")
            or template.get("requested_profile_id")
            != template_selection.get("requested_profile_id")
            or template.get("requested_version") != template_selection.get("requested_version")
            or template.get("output_contract_path")
            != template_selection.get("output_contract_relative_path")
            or template.get("output_contract_hash")
            != template_selection.get("output_contract_sha256")
            or template.get("output_contract_version")
            != template_selection.get("output_contract_version")
            or metadata.get("template_profile", {}).get("id") != template_selection.get("profile_id")
            or metadata.get("template_profile", {}).get("version") != template_selection.get("version")
            or metadata.get("template_profile", {}).get("source_kind")
            != template_selection.get("source_kind")
            or metadata.get("template_profile", {}).get("path")
            != (
                f"references/templates/{template_selection.get('relative_path')}"
                if template_selection.get("source_kind") == "BUILTIN"
                else template_selection.get("relative_path")
            )
            or metadata.get("template_profile", {}).get("sha256") != template_selection.get("sha256")
            or metadata.get("template_profile", {}).get("selection_source")
            != template_selection.get("selection_source")
            or metadata.get("template_profile", {}).get("fallback_reason")
            != template_selection.get("fallback_reason")
            or metadata.get("template_profile", {}).get("requested_profile_id")
            != template_selection.get("requested_profile_id")
            or metadata.get("template_profile", {}).get("requested_version")
            != template_selection.get("requested_version")
            or metadata.get("template_profile", {}).get("output_contract")
            != {
                "path": (
                    f"references/templates/{template_selection.get('output_contract_relative_path')}"
                    if template_selection.get("source_kind") == "BUILTIN"
                    else template_selection.get("output_contract_relative_path")
                ),
                "sha256": template_selection.get("output_contract_sha256"),
                "version": template_selection.get("output_contract_version"),
            }
        ):
            raise ReceiptError("document_experience Template registry evidence is not exact")
        if (
            version.get("schema_version") != "document-version-record.v1"
            or version.get("candidate_hash") != candidate_ref.get("hash")
            or version.get("version") != candidate_ref.get("version")
            or version.get("status") != "CANDIDATE_ARCHIVED"
        ):
            raise ReceiptError("document_experience version record is not exact")
        if candidate_ref.get("version") not in changelog or candidate_ref.get("artifact_path", "") not in changelog:
            raise ReceiptError("document_experience changelog does not bind Candidate version/path")
        lifecycle_issues = validate_lifecycle_expression_reconciliation(
            document,
            authoritative={
                "review_status": companion.get("status"),
                "eval_fulfillment": metadata.get("evals", {}).get("fulfillment"),
                "eval_execution_status": metadata.get("evals", {}).get(
                    "execution_status", "NOT_RUN"
                ),
                "remote_handoff_status": "NOT_SENT",
            },
        )
        if lifecycle_issues:
            raise ReceiptError(
                "document_experience lifecycle claims conflict with authority: "
                + ", ".join(lifecycle_issues)
            )
        observed = {
            "document_experience": "PASS",
            "version_visible": candidate_ref["version"],
            "writing_profile_id": expected_document_experience["profile_ref"]["id"],
            "writing_profile_version": expected_document_experience["profile_ref"]["version"],
        }
    elif kind == "audit_integrity":
        audit = json_subject("audit_snapshot")
        events = verify_event_chain(root / ".better-product-graph" / "runs" / run_id / "events.jsonl")
        covered_count = audit.get("event_count")
        expected_head = (
            events[covered_count - 1]["event_hash"]
            if isinstance(covered_count, int) and 0 < covered_count <= len(events)
            else None
        )
        if (
            audit.get("schema_version") != "audit-integrity-snapshot.v1"
            or audit.get("status") != "PASS"
            or audit.get("run_id") != run_id
            or audit.get("node_id") != node_id
            or audit.get("attempt_id") != attempt_id
            or audit.get("candidate_hash") != candidate_ref.get("hash")
            or audit.get("candidate_version") != candidate_ref.get("version")
            or audit.get("rules_version") != READY_RULES_VERSION
            or not isinstance(covered_count, int)
            or covered_count <= 0
            or covered_count > len(events)
            or audit.get("event_head_hash") != expected_head
        ):
            raise ReceiptError("audit_integrity subject is FAIL, stale, or not exact")
        observed = {"audit_integrity": "PASS", "event_head_hash": expected_head}
    elif kind == "mechanical_contracts":
        mechanical = json_subject("mechanical_validation")
        if (
            mechanical.get("schema_version") != "mechanical-validation.v1"
            or mechanical.get("status") != "PASS"
        ):
            raise ReceiptError("mechanical_contracts subject is FAIL or not Controller-valid PASS")
        metadata_paths = list(candidate_root.glob("*.metadata.json"))
        if len(metadata_paths) != 1:
            raise ReceiptError("mechanical_contracts Candidate metadata is not self-contained")
        metadata = read_json(metadata_paths[0])
        selection = TemplateSelection(
            profile_id=template_selection["profile_id"],
            version=template_selection["version"],
            status=template_selection["status"],
            path=Path(template_selection["path"]),
            sha256=template_selection["sha256"],
            relative_path=template_selection["relative_path"],
            output_contract_path=Path(template_selection["output_contract_path"]),
            output_contract_sha256=template_selection["output_contract_sha256"],
            output_contract_version=template_selection["output_contract_version"],
            output_contract_relative_path=template_selection[
                "output_contract_relative_path"
            ],
            origin=template_selection["source_kind"],
            selection_source=template_selection["selection_source"],
            fallback_reason=template_selection.get("fallback_reason"),
            requested_profile_id=template_selection.get("requested_profile_id"),
            requested_version=template_selection.get("requested_version"),
        )
        provenance = metadata.get("provenance", {})
        submitted_metadata = {
            key: value
            for key, value in metadata.items()
            if key
            not in {
                "structure_mode",
                "template_mapping",
                "template_profile",
                "provenance",
            }
        }
        reconstructed = {
            "node_id": "prd.generate",
            "attempt_id": provenance.get("attempt_id"),
            "producer": {"kind": "HOST_AGENT", "host": "receipt-validator"},
            "instruction_ref": provenance.get("instruction_ref"),
            "instruction_hash": provenance.get("instruction_hash"),
            "input_refs": provenance.get("input_refs"),
            "input_hashes": provenance.get("input_hashes"),
            "semantic_output": {
                "document_markdown": (root / candidate_ref["path"]).read_text(encoding="utf-8"),
                "structure_mode": metadata.get("structure_mode"),
                "template_mapping": metadata.get("template_mapping"),
                "metadata": submitted_metadata,
            },
            "artifact_refs": [],
        }
        try:
            assembled = assemble_prd(
                reconstructed,
                selection,
                # Ready separately verifies the exact Controller fulfillment
                # receipt and Eval authority. This reconstructs the enriched
                # Candidate without weakening authored prd.generate inputs.
                allow_controller_reviewed_evals=(
                    metadata.get("evals", {}).get("fulfillment") == "REVIEWED"
                    and metadata.get("evals", {}).get("fulfillment_authority")
                    == "CONTROLLER_BOUND"
                ),
            )
        except (PRDContractError, KeyError, TypeError, ValueError) as error:
            raise ReceiptError(f"mechanical_contracts SCHEMA check failed: {error}") from error
        role_to_metadata = {
            "upstream_roadmap": metadata.get("roadmap_snapshot_ref"),
            "upstream_product_plan": metadata.get("product_plan_ref"),
            "upstream_slice": metadata.get("slice_ref"),
            "upstream_knowledge": metadata.get("knowledge_snapshot_ref"),
        }
        for prefix, values in (
            ("upstream_decision", metadata.get("decision_refs")),
            ("upstream_evidence", metadata.get("evidence_refs")),
        ):
            if not isinstance(values, list) or (prefix == "upstream_decision" and not values):
                raise ReceiptError(f"mechanical_contracts {prefix} metadata refs are missing")
            role_names = [
                prefix if len(values) == 1 else f"{prefix}:{index}"
                for index in range(len(values))
            ]
            if any(role not in subjects for role in role_names):
                raise ReceiptError(f"mechanical_contracts {prefix} subject coverage is incomplete")
            unexpected = [
                role for role in subjects
                if role == prefix or role.startswith(prefix + ":")
            ]
            if set(unexpected) != set(role_names):
                raise ReceiptError(f"mechanical_contracts {prefix} subject coverage differs from metadata")
            role_to_metadata.update(zip(role_names, values, strict=True))
        upstream_valid = True
        for role, expected_ref in role_to_metadata.items():
            subject = subjects.get(role, {})
            exact = {
                key: subject.get(key) for key in ("path", "hash", "version")
            }
            if not isinstance(expected_ref, dict) or exact != {
                key: expected_ref.get(key) for key in ("path", "hash", "version")
            }:
                upstream_valid = False
                break
            expected_kind = role.removeprefix("upstream_").split(":", 1)[0]
            try:
                if expected_kind == "decision":
                    payload = json_subject(role)
                    validate_ready_decision(root, run_id, subject, payload)
                elif expected_kind == "evidence":
                    payload = json_subject(role)
                    validate_ready_evidence(root, run_id, subject, payload)
                elif expected_kind == "product_plan":
                    plan_path = root / subject["path"]
                    if plan_path.suffix.lower() != ".md":
                        raise ReceiptError(
                            "mechanical_contracts Product Plan must be a Markdown artifact"
                        )
                    try:
                        plan_markdown = plan_path.read_text(encoding="utf-8")
                    except (OSError, UnicodeError) as error:
                        raise ReceiptError(
                            "mechanical_contracts Product Plan is not readable UTF-8 Markdown"
                        ) from error
                    if not plan_markdown.startswith("# ") or "\x00" in plan_markdown:
                        raise ReceiptError(
                            "mechanical_contracts Product Plan Markdown contract is invalid"
                        )
                else:
                    expected_nodes = {
                        "roadmap": "evidence.collect",
                        "slice": "product.planning",
                        "knowledge": "evidence.map",
                    }
                    payload = json_subject(role)
                    if (
                        payload.get("schema_version") != "node-result.v1"
                        or payload.get("node_id") != expected_nodes.get(expected_kind)
                    ):
                        raise ReceiptError(
                            f"mechanical_contracts {role} must be the exact "
                            f"{expected_nodes.get(expected_kind)} Node Result"
                        )
                    validate_node_result_producer(payload)
                    validate_node_output(payload["node_id"], payload)
            except (UpstreamAuthorityError, PolicyViolation, NodeValidationError) as error:
                raise ReceiptError(str(error)) from error
        if upstream_valid:
            slice_payload = json_subject("upstream_slice")
            try:
                active_scope = derive_active_scope_ref(
                    slice_payload,
                    metadata["product_plan_ref"],
                    metadata["prd_id"],
                )
            except DeliveryContractError as error:
                raise ReceiptError(
                    f"mechanical_contracts stable Product Plan/Slice identity failed: {error}"
                ) from error
            if metadata.get("active_scope_ref") != active_scope:
                raise ReceiptError(
                    "mechanical_contracts active_scope_ref differs from exact Product Planning Slice"
                )
        if (
            mechanical.get("schema_version") != "mechanical-validation.v1"
            or mechanical.get("status") != "PASS"
            or mechanical.get("run_id") != run_id
            or mechanical.get("node_id") != node_id
            or mechanical.get("attempt_id") != attempt_id
            or mechanical.get("candidate_hash") != candidate_ref.get("hash")
            or mechanical.get("candidate_version") != candidate_ref.get("version")
            or mechanical.get("rules_version") != READY_RULES_VERSION
            or set(mechanical.get("checks", []))
            != {"CURRENT_CANDIDATE", "UPSTREAM_REFS", "SCHEMA", "HASHES"}
            or assembled.metadata != metadata
            or not upstream_valid
        ):
            raise ReceiptError(
                "mechanical_contracts CURRENT_CANDIDATE/UPSTREAM_REFS/SCHEMA/HASHES recomputation failed"
            )
        observed = {"mechanical_contracts": "PASS", "checks": sorted(mechanical["checks"])}
    else:  # normalize_subject_refs already rejects unsupported kinds
        raise ReceiptError(f"unsupported receipt kind: {kind}")
    return {"status": "PASS", "observed": observed}


def build_receipt_payload(
    receipt_id: str,
    run_id: str,
    kind: str,
    normalized_subjects: list[dict[str, Any]],
    *,
    node_id: str,
    attempt_id: str,
    state_version: int,
    candidate_ref: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    if SAFE_ID.fullmatch(receipt_id) is None or SAFE_ID.fullmatch(run_id) is None:
        raise ReceiptError("receipt_id and run_id must be path-safe")
    return {
        "schema_version": "controller-receipt.v1",
        "receipt_id": receipt_id,
        "run_id": run_id,
        "kind": kind,
        "issuer": "state-controller",
        "status": "PASS",
        "node_id": node_id,
        "attempt_id": attempt_id,
        "state_version": state_version,
        "candidate_hash": candidate_ref["hash"],
        "candidate_version": candidate_ref["version"],
        "rules_version": READY_RULES_VERSION,
        "subject_refs": normalized_subjects,
        "evaluation": evaluation,
    }


def verify_controller_receipt(
    project_root: Path,
    ref: dict[str, Any],
    expected_kind: str,
    expected_subject_refs: list[dict[str, Any]],
    *,
    expected_run_id: str,
    expected_node_id: str,
    expected_attempt_id: str,
    expected_candidate_ref: dict[str, Any],
) -> dict[str, Any]:
    root = project_root.resolve()
    path = resolve_file_ref(root, ref, f"{expected_kind} receipt")
    run_id = ref.get("run_id")
    if not isinstance(run_id, str) or SAFE_ID.fullmatch(run_id) is None:
        raise ReceiptError(f"{expected_kind} receipt has no controlled Run identity")
    if run_id != expected_run_id:
        raise ReceiptError(f"{expected_kind} receipt belongs to another Run")
    controlled = root / ".better-product-graph" / "runs" / run_id / "receipts"
    try:
        path.relative_to(controlled.resolve())
    except ValueError as error:
        raise ReceiptError(f"{expected_kind} receipt is outside the Controller-owned path") from error
    receipt = read_json(path)
    if (
        receipt.get("schema_version") != "controller-receipt.v1"
        or receipt.get("issuer") != "state-controller"
        or receipt.get("status") != "PASS"
        or receipt.get("kind") != expected_kind
        or receipt.get("run_id") != expected_run_id
        or receipt.get("node_id") != expected_node_id
        or receipt.get("attempt_id") != expected_attempt_id
        or receipt.get("candidate_hash") != expected_candidate_ref.get("hash")
        or receipt.get("candidate_version") != expected_candidate_ref.get("version")
        or receipt.get("rules_version") != READY_RULES_VERSION
        or receipt.get("evaluation", {}).get("status") != "PASS"
    ):
        raise ReceiptError(f"{expected_kind} receipt is not Controller-issued PASS")
    expected = normalize_subject_refs(root, expected_kind, expected_subject_refs)
    if receipt.get("subject_refs") != expected:
        raise ReceiptError(f"{expected_kind} receipt subject roles or hashes do not match Ready facts")
    state = read_json(root / ".better-product-graph" / "runs" / run_id / "state.json")
    registered = [
        item
        for item in state.get("ready_receipts", [])
        if item.get("path") == ref.get("path")
        and item.get("hash") == ref.get("hash")
        and item.get("kind") == expected_kind
    ]
    if len(registered) != 1:
        raise ReceiptError(f"{expected_kind} receipt is not registered by state authority")
    ledger_path = root / ".better-product-graph" / "runs" / run_id / "receipt-ledger.jsonl"
    ledger = verify_event_chain(ledger_path)
    ledger_matches = [
        event
        for event in ledger
        if event.get("event_type") == "CONTROLLER_RECEIPT_ISSUED"
        and event.get("receipt_ref", {}).get("path") == ref.get("path")
        and event.get("receipt_ref", {}).get("hash") == ref.get("hash")
    ]
    if len(ledger_matches) != 1:
        raise ReceiptError(f"{expected_kind} receipt is absent from append-only Controller ledger")
    return receipt
