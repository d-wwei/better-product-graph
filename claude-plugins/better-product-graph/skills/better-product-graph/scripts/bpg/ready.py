"""Programmatic PRD Ready calculation over six V1.4 mechanical categories."""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
from typing import Any

from .documents import ArtifactSet
from .evals_authority import EvalsAuthorityError, validate_reviewed_evals
from .prd_contract import validate_experiment_contract
from .receipts import (
    READY_RULES_VERSION,
    ReceiptError,
    controller_subject_ref,
    resolve_file_ref,
    verify_controller_receipt,
)
from .state_controller import StateConflict, StateController, TransitionRejected
from .storage import read_json, sha256_file


class PRDNotReady(RuntimeError):
    """Release was requested for a Candidate with deterministic unmet conditions."""


@dataclass(frozen=True)
class ReadyResult:
    status: str
    unmet: list[dict[str, Any]]


def _unmet(
    category: str, affected_ref: Any, repair_target: str, resume_point: str
) -> dict[str, Any]:
    return {
        "category": category,
        "affected_ref": affected_ref,
        "repair_target": repair_target,
        "resume_point": resume_point,
    }


def calculate_prd_ready(request: dict[str, Any]) -> ReadyResult:
    unmet: list[dict[str, Any]] = []
    candidate = request.get("candidate_ref")
    if (
        not isinstance(candidate, dict)
        or candidate.get("current") is not True
        or candidate.get("materially_valid") is not True
        or candidate.get("archived") is not True
        or not candidate.get("hash")
        or candidate.get("resolved_hash") != candidate.get("hash")
        or candidate.get("version") is None
    ):
        unmet.append(
            _unmet("CURRENT_CANDIDATE", candidate, "REBIND_CURRENT_ARCHIVED_CANDIDATE", "prd.generate")
        )

    review = request.get("review")
    review_valid = isinstance(review, dict) and isinstance(candidate, dict)
    if review_valid:
        roles = {
            item.get("role")
            for item in review.get("attempts", [])
            if isinstance(item, dict) and item.get("status") in {"COMPLETED", "UNAVAILABLE_RECORDED"}
        }
        finding_ids = {
            item.get("finding_id") for item in review.get("findings", []) if isinstance(item, dict)
        }
        disposed = {
            item.get("finding_id")
            for item in review.get("dispositions", [])
            if isinstance(item, dict) and item.get("status")
        }
        companion = review.get("companion_view_ref", {})
        review_valid = (
            review.get("candidate_hash") == candidate.get("hash")
            and review.get("candidate_version") == candidate.get("version")
            and {"product", "engineering_feasibility", "testability"}.issubset(roles)
            and review.get("aggregate_complete") is True
            and review.get("finalized") is True
            and finding_ids == disposed
            and companion.get("candidate_hash") == candidate.get("hash")
            and companion.get("finding_count") == len(finding_ids)
            and bool(companion.get("hash"))
            and companion.get("resolved_hash") == companion.get("hash")
        )
    if not review_valid:
        unmet.append(
            _unmet("REVIEW_FINALIZE", review, "COMPLETE_SAME_VERSION_REVIEW_FINALIZE", "review.finalize")
        )

    upstream = request.get("upstream_refs")
    required_kinds = {"decision", "roadmap", "product_plan", "slice", "knowledge"}
    upstream_valid = isinstance(upstream, list)
    if upstream_valid:
        kinds = {item.get("kind") for item in upstream if isinstance(item, dict)}
        upstream_valid = required_kinds.issubset(kinds) and all(
            isinstance(item, dict)
            and item.get("path")
            and item.get("hash")
            and item.get("resolved_hash") == item.get("hash")
            and item.get("version") is not None
            and item.get("current") is True
            and item.get("stale") is False
            for item in upstream
        )
    if not upstream_valid:
        unmet.append(
            _unmet("UPSTREAM_REFS", upstream, "REBIND_CURRENT_UPSTREAM_REFS", "prd.generate")
        )

    evals = request.get("evals")
    evals_valid = isinstance(evals, dict) and evals.get("applicability") in {
        "NOT_NEEDED",
        "RECOMMENDED",
        "REQUIRED",
    }
    evals_repair_target = "FULFILL_EVAL_POLICY"
    if evals_valid and evals["applicability"] == "NOT_NEEDED":
        evals_valid = bool(evals.get("reason"))
    elif evals_valid and evals["applicability"] == "REQUIRED":
        evals_valid = (
            evals.get("fulfillment") == "REVIEWED"
            and evals.get("fulfillment_authority") == "CONTROLLER_BOUND"
            and evals.get("execution_status") == "NOT_RUN"
            and isinstance(evals.get("pack_ref"), dict)
            and isinstance(evals.get("review_ref"), dict)
            and isinstance(evals.get("ground_truth_provenance"), dict)
        )
        evals_repair_target = "WAIT_FOR_VERIFIABLE_EVAL_FULFILLMENT"
    if not evals_valid:
        unmet.append(_unmet("EVALS", evals, evals_repair_target, "evals.build"))

    presentation = request.get("presentation")
    presentation_valid = isinstance(presentation, dict) and (
        isinstance(presentation.get("template_profile_ref"), dict)
        and bool(presentation["template_profile_ref"].get("hash"))
        and presentation["template_profile_ref"].get("resolved_hash")
        == presentation["template_profile_ref"].get("hash")
        and presentation.get("document_experience") == "PASS"
        and isinstance(presentation.get("version_record_ref"), dict)
        and bool(presentation["version_record_ref"].get("hash"))
        and presentation["version_record_ref"].get("resolved_hash")
        == presentation["version_record_ref"].get("hash")
        and isinstance(presentation.get("changelog_ref"), dict)
        and bool(presentation["changelog_ref"].get("hash"))
        and presentation["changelog_ref"].get("resolved_hash")
        == presentation["changelog_ref"].get("hash")
        and presentation.get("audit_valid") is True
    )
    if not presentation_valid:
        unmet.append(
            _unmet(
                "PRESENTATION_VERSION",
                presentation,
                "REPAIR_TEMPLATE_DOCUMENT_VERSION_CHANGELOG",
                "review.finalize",
            )
        )

    if request.get("mechanical_contracts") != "PASS":
        unmet.append(
            _unmet(
                "MECHANICAL_CONTRACTS",
                request.get("mechanical_contracts"),
                "REPAIR_MECHANICAL_CONTRACT",
                "prd.generate",
            )
        )

    if request.get("delivery_intent") == "EXPERIMENT":
        experiment = request.get("experiment_contract")
        experiment_issues = validate_experiment_contract(experiment)
        if experiment_issues:
            unmet.append(
                _unmet(
                    "EXPERIMENT_CONTRACT",
                    {"issues": experiment_issues},
                    "COMPLETE_EXPERIMENT_CONTROL_CONTRACT",
                    "prd.generate",
                )
            )
    return ReadyResult("NOT_READY" if unmet else "READY", unmet)


def ready_and_release(
    project_root: Path,
    archived: ArtifactSet,
    request: dict[str, Any],
    *,
    controller: StateController | None = None,
    run_id: str | None = None,
    failpoint=None,
) -> ArtifactSet:
    if controller is None or not run_id or controller.project_root != project_root.resolve():
        raise PRDNotReady("Ready/release requires exact Controller and Run lifecycle authority")
    state = controller.load_state(run_id)
    if state.get("status") == "RELEASED" and state.get("current_node") == "handoff.prepare":
        try:
            assertion = read_json(project_root.resolve() / state["release_ref"]["path"])
            if (
                assertion.get("controller_receipts") != request.get("controller_receipts")
                or assertion.get("candidate_hash") != archived.document_hash
            ):
                raise PRDNotReady("release retry differs from committed Ready authority")
            return controller.commit_ready_release(
                run_id,
                archived,
                assertion,
                expected_state_version=state["state_version"],
            )
        except (KeyError, StateConflict, TransitionRejected) as error:
            raise PRDNotReady(f"release retry cannot reconcile: {error}") from error
    current_candidate = state.get("current_candidate_ref")
    if (
        state.get("status") != "ACTIVE"
        or state.get("current_node") != "prd.ready.gate"
        or not isinstance(current_candidate, dict)
        or current_candidate.get("path")
        != archived.document_path.relative_to(project_root.resolve()).as_posix()
        or current_candidate.get("hash") != archived.document_hash
        or current_candidate.get("tree_hash") != archived.tree_hash
        or current_candidate.get("artifact_path")
        != archived.path.relative_to(project_root.resolve()).as_posix()
        or current_candidate.get("version") != archived.version
    ):
        raise PRDNotReady("Ready/release Candidate does not match the exact current Run lifecycle")
    current_attempts = [
        item
        for item in state["dispatch_attempts"]
        if item.get("node_id") == "prd.ready.gate"
        and item.get("status") == "DISPATCHED"
        and item.get("authorized_state_version") == state["state_version"]
    ]
    if len(current_attempts) != 1:
        raise PRDNotReady("Ready/release requires one exact current Gate attempt")
    attempt_id = current_attempts[0]["attempt_id"]
    evals = request.get("evals", {})
    if (
        evals.get("applicability") == "REQUIRED"
        and (
            evals.get("fulfillment") != "REVIEWED"
            or evals.get("fulfillment_authority") != "CONTROLLER_BOUND"
        )
    ):
        raise PRDNotReady(
            "REQUIRED Evals cannot release before exact Controller-bound fulfillment"
        )
    if evals.get("fulfillment") == "REVIEWED":
        try:
            validate_reviewed_evals(
                project_root,
                controller.skill_root,
                evals,
                expected_candidate_ref={
                    "path": archived.document_path.relative_to(project_root.resolve()).as_posix(),
                    "hash": archived.document_hash,
                    "version": archived.version,
                },
                artifact_refs=state.get("artifact_refs", {}),
                dispatched_input_hashes=current_attempts[0]["contract"]["input_hashes"],
                committed_attempt_ids=frozenset(state.get("consumed_attempts", [])),
            )
        except EvalsAuthorityError as error:
            raise PRDNotReady(f"REVIEWED Evals authority invalid: {error}") from error
    candidate = request.get("candidate_ref")
    try:
        candidate_path = Path(candidate["path"]).resolve()
    except (KeyError, TypeError, ValueError):
        candidate_path = None
    if (
        not isinstance(candidate, dict)
        or candidate_path != archived.path.resolve()
        or candidate.get("hash") != archived.document_hash
        or candidate.get("resolved_hash") != archived.document_hash
        or candidate.get("tree_hash") != archived.tree_hash
        or candidate.get("version") != archived.version
    ):
        raise PRDNotReady("Ready request is not bound to the exact archived Candidate")
    try:
        if (
            not archived.document_path.is_file()
            or archived.document_hash != sha256_file(archived.document_path)
        ):
            raise ReceiptError("Candidate document hash mismatch")
        candidate_document_ref = {
            "role": "candidate_document",
            "path": archived.document_path.relative_to(project_root.resolve()).as_posix(),
            "hash": archived.document_hash,
        }
        review = request.get("review", {})
        presentation = request.get("presentation", {})
        receipts = request.get("controller_receipts")
        if not isinstance(receipts, dict):
            raise ReceiptError("Controller receipts are missing")
        upstream_by_kind: dict[str, list[dict[str, Any]]] = {}
        for item in request.get("upstream_refs", []):
            if isinstance(item, dict) and isinstance(item.get("kind"), str):
                upstream_by_kind.setdefault(item["kind"], []).append(item)

        def upstream_subjects(kind: str) -> list[dict[str, Any]]:
            values = upstream_by_kind.get(kind, [])
            return [
                controller_subject_ref(
                    f"upstream_{kind}" if len(values) == 1 else f"upstream_{kind}:{index}",
                    item,
                )
                for index, item in enumerate(values)
            ]
        expected_subjects = {
            "review_finalize": [
                candidate_document_ref,
                controller_subject_ref("review_companion", review.get("companion_view_ref", {})),
                controller_subject_ref("review_aggregate", review.get("aggregate_ref", {})),
                controller_subject_ref("review_dispositions", review.get("dispositions_ref", {})),
            ],
            "document_experience": [
                candidate_document_ref,
                controller_subject_ref("template_profile", presentation.get("template_profile_ref", {})),
                controller_subject_ref("version_record", presentation.get("version_record_ref", {})),
                controller_subject_ref("document_changelog", presentation.get("changelog_ref", {})),
            ],
            "audit_integrity": [
                controller_subject_ref("audit_snapshot", presentation.get("audit_snapshot_ref", {}))
            ],
            "mechanical_contracts": [
                candidate_document_ref,
                *upstream_subjects("decision"),
                *upstream_subjects("roadmap"),
                *upstream_subjects("product_plan"),
                *upstream_subjects("slice"),
                *upstream_subjects("knowledge"),
                *upstream_subjects("evidence"),
                controller_subject_ref("mechanical_validation", request.get("mechanical_validation_ref", {})),
            ],
        }
        for kind, subjects in expected_subjects.items():
            verify_controller_receipt(
                project_root,
                receipts.get(kind, {}),
                kind,
                subjects,
                expected_run_id=run_id,
                expected_node_id="prd.ready.gate",
                expected_attempt_id=attempt_id,
                expected_candidate_ref=current_candidate,
            )
        for item in request.get("upstream_refs", []):
            resolve_file_ref(project_root, item, f"upstream {item.get('kind', 'unknown')}")
        companion_path = resolve_file_ref(
            project_root, review.get("companion_view_ref", {}), "Review companion"
        )
        companion = read_json(companion_path)
        if (
            companion_path != archived.review_path.resolve()
            or sha256_file(companion_path) != archived.review_hash
            or companion.get("candidate_hash") != archived.document_hash
            or companion.get("version") != archived.version
            or companion.get("status") != "FINALIZED"
            or companion.get("authority") != "ADVISORY_ONLY"
        ):
            raise ReceiptError("Review companion is not the exact finalized same-version archive companion")
        for field in ("template_profile_ref", "version_record_ref", "changelog_ref", "audit_snapshot_ref"):
            resolve_file_ref(project_root, presentation.get(field, {}), field)
        resolve_file_ref(project_root, request.get("mechanical_validation_ref", {}), "mechanical_validation_ref")
        evals = request.get("evals", {})
        if evals.get("applicability") == "REQUIRED":
            resolve_file_ref(project_root, evals.get("pack_ref", {}), "Eval Pack")
    except ReceiptError as error:
        raise PRDNotReady(str(error)) from error
    effective = deepcopy(request)
    effective["candidate_ref"].update(
        {"resolved_hash": archived.document_hash, "current": True, "materially_valid": True, "archived": True}
    )
    effective["review"].update({"aggregate_complete": True, "finalized": True})
    effective["review"]["companion_view_ref"]["resolved_hash"] = effective["review"]["companion_view_ref"]["hash"]
    for item in effective["upstream_refs"]:
        item.update({"resolved_hash": item["hash"], "current": True, "stale": False})
    effective["presentation"].update({"document_experience": "PASS", "audit_valid": True})
    for field in ("template_profile_ref", "version_record_ref", "changelog_ref"):
        effective["presentation"][field]["resolved_hash"] = effective["presentation"][field]["hash"]
    effective["mechanical_contracts"] = "PASS"
    result = calculate_prd_ready(effective)
    if result.status != "READY":
        raise PRDNotReady("PRD is NOT_READY: " + ", ".join(item["category"] for item in result.unmet))
    template_ref = deepcopy(effective["presentation"]["template_profile_ref"])
    template_evidence = read_json(project_root / template_ref["path"])
    template_ref["requested_profile_id"] = template_evidence.get("requested_profile_id")
    template_ref["requested_version"] = template_evidence.get("requested_version")
    assertion = {
        "schema_version": "prd-ready-assertion.v1",
        "status": "READY",
        "candidate_hash": archived.document_hash,
        "candidate_tree_hash": archived.tree_hash,
        "review_companion_hash": archived.review_hash,
        "upstream_refs": deepcopy(effective["upstream_refs"]),
        "template_ref": template_ref,
        "review_ref": {
            **deepcopy(effective["review"]["companion_view_ref"]),
            "version": archived.version,
        },
        "run_id": run_id,
        "gate_attempt_id": attempt_id,
        "state_version": state["state_version"],
        "controller_receipts": deepcopy(request["controller_receipts"]),
        "rules_version": READY_RULES_VERSION,
        "checks": [
            "CURRENT_CANDIDATE",
            "REVIEW_FINALIZE",
            "UPSTREAM_REFS",
            "EVALS",
            "PRESENTATION_VERSION",
            "MECHANICAL_CONTRACTS",
        ],
        "delivery_intent": request.get("delivery_intent"),
        "external_approval": "NOT_CLAIMED",
        "engineering_implemented": "NOT_CLAIMED",
        "tests_executed": "NOT_CLAIMED",
    }
    try:
        released = controller.commit_ready_release(
            run_id,
            archived,
            assertion,
            expected_state_version=state["state_version"],
            failpoint=failpoint,
        )
    except (TransitionRejected, StateConflict) as error:
        raise PRDNotReady(f"Controller release authority rejected: {error}") from error
    return released
