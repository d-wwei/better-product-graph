from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from src.bpg.documents import archive_prd_candidate, hash_tree
from src.bpg.delivery_contract import derive_active_scope_ref
from src.bpg.failpoints import InjectedCrash, begin_node_call, crash_at, persist_node_dispatch, recover_run
from src.bpg.handoff import prepare_local_handoff
from src.bpg.host_runtime import HostRuntime
from src.bpg.prd_contract import assemble_prd
from src.bpg.product_memory import persist_decision_proposal
from src.bpg.receipts import READY_RULES_VERSION
from src.bpg.ready import PRDNotReady, calculate_prd_ready, ready_and_release
from src.bpg.state_controller import StateConflict, StateController, TransitionRejected
from src.bpg.storage import (
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_event_chain,
)
from src.bpg.templates import TemplateRegistry
from tests.controller_fixtures import position_run_internal
from tests.test_planning_contract import complete_plan
from tests.test_prd_contract import (
    REPO_ROOT,
    TEMPLATES,
    complete_experiment_contract,
    prd_submission,
)


GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


def finalized_review_companion(assembled) -> dict:
    return {
        "schema_version": "prd-review-companion.v1",
        "prd_id": assembled.metadata["prd_id"],
        "version": assembled.metadata["version"],
        "candidate_hash": sha256_bytes(assembled.markdown.encode()),
        "status": "FINALIZED",
        "authority": "ADVISORY_ONLY",
        "finding_count": 1,
    }


def complete_ready_input(candidate_ref: dict) -> dict:
    return {
        "candidate_ref": {
            **candidate_ref,
            "resolved_hash": candidate_ref["hash"],
            "current": True,
            "materially_valid": True,
            "archived": True,
        },
        "review": {
            "candidate_hash": candidate_ref["hash"],
            "candidate_version": candidate_ref["version"],
            "attempts": [
                {"role": "product", "status": "COMPLETED"},
                {"role": "engineering_feasibility", "status": "COMPLETED"},
                {"role": "testability", "status": "COMPLETED"},
            ],
            "aggregate_complete": True,
            "finalized": True,
            "findings": [
                {"finding_id": "f-1", "concern_level": "CRITICAL", "legacy_label": "BLOCK_RECOMMENDED"}
            ],
            "dispositions": [{"finding_id": "f-1", "status": "EXTERNAL_REVIEW"}],
            "companion_view_ref": {
                "candidate_hash": candidate_ref["hash"],
                "finding_count": 1,
                "hash": "sha256:companion",
                "resolved_hash": "sha256:companion",
            },
        },
        "upstream_refs": [
            {
                "kind": kind,
                "path": (
                    "product-plan-v1.md"
                    if kind == "product_plan"
                    else f"{kind}-v1.json"
                ),
                "hash": f"sha256:{kind}",
                "resolved_hash": f"sha256:{kind}",
                "version": 1,
                "current": True,
                "stale": False,
            }
            for kind in ("decision", "roadmap", "product_plan", "slice", "knowledge", "evidence")
        ],
        "evals": {"applicability": "NOT_NEEDED", "reason": "deterministic AC"},
        "presentation": {
            "template_profile_ref": {
                "hash": "sha256:template",
                "resolved_hash": "sha256:template",
                "version": "upstream-frozen",
            },
            "document_experience": "PASS",
            "version_record_ref": {"hash": "sha256:version", "resolved_hash": "sha256:version"},
            "changelog_ref": {"hash": "sha256:changelog", "resolved_hash": "sha256:changelog"},
            "audit_valid": True,
        },
        "mechanical_contracts": "PASS",
        "delivery_intent": "COMMIT",
    }


def materialize_authoritative_ready_upstreams(
    project: Path,
    request: dict,
) -> tuple[StateController, str]:
    """Build deterministic Decision/Evidence authority without making semantics."""

    controller = StateController(project, GRAPH)
    run_id = "run-ready-receipts"
    controller.create_run(run_id, raw_signal="Ready receipt authority")
    decision_items = [item for item in request["upstream_refs"] if item["kind"] == "decision"]
    for index, decision_item in enumerate(decision_items, start=1):
        position_run_internal(
            controller,
            run_id,
            "product.decision",
            ["product.planning", "evidence.collect"],
        )
        decision_submission = {
            "schema_version": "node-result.v1",
            "node_id": "product.decision",
            "attempt_id": f"decision-ready-fixture-{index}",
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": "references/atomic-skills/product-decision/INSTRUCTIONS.md",
            "instruction_hash": "sha256:fixture-instruction",
            "input_refs": ["problem-ready-fixture.json"],
            "input_hashes": {"problem-ready-fixture.json": "sha256:fixture-problem"},
            "semantic_output": {
                "recommendation": "COMMIT",
                "reasons": ["目标明确", "证据边界可接受"],
                "mvu": "用户是否持续遇到该阻碍",
                "nearest_alternative": "EXPERIMENT",
                "flip_condition": "关键风险无法控制",
                "next_action": "等待 Owner 独立选择",
                "epistemic_confidence": "MEDIUM",
                "action_risk": {
                    "level": "R1",
                    "basis": "reversible local exposure",
                    "reversible": True,
                    "measurable": True,
                    "rollback": "restore prior local version",
                },
                "non_waivable_policy_violations": [],
                "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
            },
            "artifact_refs": [],
        }
        proposal = persist_decision_proposal(
            project,
            f"decision-ready-receipts-{Path(decision_item['path']).stem}",
            run_id,
            decision_submission,
        )
        decision_state = controller.load_state(run_id)
        chosen = controller.apply_owner_choice(
            run_id,
            {
                "schema_version": "owner-choice-command.v1",
                "decision_id": proposal["decision_id"],
                "proposal_ref": proposal["proposal_ref"],
                "proposal_hash": proposal["proposal_ref"]["hash"],
                "actor": {"kind": "OWNER", "id": "ready-fixture-owner"},
                "expected_state_version": decision_state["state_version"],
                "choice": "COMMIT",
                "commit_timing": "NOW",
                "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
            },
        )
        decision_item.update(chosen["decision"]["record_ref"])
        decision_item["resolved_hash"] = decision_item["hash"]

    evidence_items = [item for item in request["upstream_refs"] if item["kind"] == "evidence"]
    for index, evidence_item in enumerate(evidence_items, start=1):
        position_run_internal(controller, run_id, "evidence.collect", ["evidence.map"])
        attempt_id = f"attempt-evidence-ready-receipts-{index}"
        persist_node_dispatch(controller, run_id, attempt_id)
        dispatched = begin_node_call(controller, run_id, attempt_id)
        contract = next(
            item["contract"]
            for item in dispatched["dispatch_attempts"]
            if item["attempt_id"] == attempt_id
        )
        content = {"summary": f"Controller-bound Ready fixture evidence {index}"}
        evidence = {
            "schema_version": "evidence-record.v1",
            "kind": "evidence",
            "version": 1,
            "run_id": run_id,
            "status": "RECORDED",
            "authorized": True,
            "received_at": "2026-08-20T00:00:00+00:00",
            "source": {"kind": "TEST_FIXTURE"},
            "producer": {"node_id": "evidence.collect", "attempt_id": attempt_id},
            "content": content,
            "content_hash": sha256_bytes(canonical_json_bytes(content)),
        }
        evidence_path = project / f"authoritative-{Path(evidence_item['path']).name}"
        atomic_write_json(evidence_path, evidence)
        evidence_ref = {
            "path": evidence_path.relative_to(project).as_posix(),
            "hash": sha256_file(evidence_path),
            "version": 1,
        }
        controller.submit_result(
            run_id,
            {
                "schema_version": "node-result.v1",
                **{
                    key: contract[key]
                    for key in (
                        "node_id",
                        "attempt_id",
                        "instruction_ref",
                        "instruction_hash",
                        "input_refs",
                        "input_hashes",
                        "resource_refs",
                    )
                },
                "producer": {"kind": "HOST_AGENT"},
                "semantic_output": {"sources": [{"kind": "TEST_FIXTURE", "ref": evidence_ref}]},
                "artifact_refs": [{"role": "evidence", **evidence_ref}],
            },
        )
        state = controller.load_state(run_id)
        controller.transition(
            run_id,
            {
                "attempt_id": attempt_id,
                "expected_state_version": state["state_version"],
                "requested_node": "evidence.map",
            },
        )
        evidence_item.update(evidence_ref)
        evidence_item["resolved_hash"] = evidence_ref["hash"]
    return controller, run_id


def materialize_ready_evidence(
    project: Path,
    request: dict,
    archived,
    *,
    upstream_shape: str = "graph_native",
    issue_receipts: bool = True,
) -> tuple[dict, object]:
    if upstream_shape not in {
        "graph_native",
        "graph_wrong_slice_node",
        "graph_unbound_plan",
        "legacy_fake",
    }:
        raise AssertionError(f"unsupported upstream_shape: {upstream_shape}")
    evidence_root = project / ".better-product-graph" / "ready-inputs"
    evidence_root.mkdir(parents=True, exist_ok=True)
    controller, run_id = materialize_authoritative_ready_upstreams(project, request)
    by_kind = {item["kind"]: item for item in request["upstream_refs"]}
    for item in request["upstream_refs"]:
        path = project / item["path"]
        if item["kind"] not in {"decision", "evidence"}:
            if upstream_shape == "legacy_fake":
                atomic_write_json(path, {"kind": item["kind"], "version": item["version"]})
            elif item["kind"] == "product_plan":
                path.write_text(
                    "# Checkout Recovery Product Plan\n\n"
                    "## Stable Slice\n\n"
                    "The Plan binds PRD-CHECKOUT-001 to slice-1 without a Candidate version.\n",
                    encoding="utf-8",
                )
            else:
                node_ids = {
                    "roadmap": "evidence.collect",
                    "slice": "product.planning",
                    "knowledge": "evidence.map",
                }
                semantic_outputs = {
                    "roadmap": {"sources": [{"kind": "PROJECT", "ref": "signal-v1.json"}]},
                    "knowledge": {"claims": []},
                }
                if item["kind"] == "slice":
                    plan = complete_plan()
                    plan["decision_ref"] = {
                        key: by_kind["decision"][key]
                        for key in ("path", "hash", "version")
                    }
                    plan["prd_matrix"][0]["planned_prd_id"] = "PRD-CHECKOUT-001"
                    semantic_outputs["slice"] = plan
                artifact_refs = []
                if item["kind"] == "slice":
                    plan_path = project / by_kind["product_plan"]["path"]
                    artifact_refs = [
                        {
                            "role": "product_plan",
                            "path": plan_path.relative_to(project).as_posix(),
                            "hash": sha256_file(plan_path),
                            "version": by_kind["product_plan"]["version"],
                        }
                    ]
                    if upstream_shape == "graph_unbound_plan":
                        artifact_refs[0]["hash"] = "sha256:" + "0" * 64
                resolved_node_id = node_ids[item["kind"]]
                if (
                    item["kind"] == "slice"
                    and upstream_shape == "graph_wrong_slice_node"
                ):
                    resolved_node_id = "evidence.map"
                atomic_write_json(
                    path,
                    {
                        "schema_version": "node-result.v1",
                        "node_id": resolved_node_id,
                        "attempt_id": f"attempt-native-{item['kind']}",
                        "producer": {"kind": "HOST_AGENT"},
                        "instruction_ref": f"references/atomic-skills/{item['kind']}/INSTRUCTIONS.md",
                        "instruction_hash": "sha256:native-instruction",
                        "input_refs": ["signal-v1.json"],
                        "input_hashes": {"signal-v1.json": "sha256:signal"},
                        "semantic_output": semantic_outputs[item["kind"]],
                        "artifact_refs": artifact_refs,
                    },
                )
        item["hash"] = sha256_file(path)
        item["resolved_hash"] = item["hash"]

    metadata_path = archived.path / f"{archived.path.name}.metadata.json"
    metadata = read_json(metadata_path)
    upstream: dict[str, list[dict]] = {}
    for item in request["upstream_refs"]:
        upstream.setdefault(item["kind"], []).append(item)
    metadata["decision_refs"] = [
        {key: item[key] for key in ("path", "hash", "version")}
        for item in upstream["decision"]
    ]
    for field, kind in (
        ("roadmap_snapshot_ref", "roadmap"),
        ("product_plan_ref", "product_plan"),
        ("slice_ref", "slice"),
        ("knowledge_snapshot_ref", "knowledge"),
    ):
        metadata[field] = {key: upstream[kind][0][key] for key in ("path", "hash", "version")}
    metadata["evidence_refs"] = [
        {key: item[key] for key in ("path", "hash", "version")}
        for item in upstream.get("evidence", [])
    ]
    metadata["active_scope_ref"]["plan_ref"] = metadata["product_plan_ref"]
    metadata["spec_traceability"] = {
        "schema_version": "spec-traceability.v1",
        "refs": [
            {
                "role": "product_plan",
                **metadata["product_plan_ref"],
                "origin_node_id": "product.planning",
                "origin_attempt_id": "attempt-native-slice",
            },
            {
                "role": "slice",
                **metadata["slice_ref"],
                "origin_node_id": "product.planning",
                "origin_attempt_id": "attempt-native-slice",
            },
        ],
    }
    if upstream_shape == "graph_native":
        slice_result = read_json(project / metadata["slice_ref"]["path"])
        metadata["active_scope_ref"] = derive_active_scope_ref(
            slice_result, metadata["product_plan_ref"], metadata["prd_id"]
        )
        for ref in metadata["spec_traceability"]["refs"]:
            ref["origin_attempt_id"] = slice_result["attempt_id"]
    metadata["provenance"]["input_refs"] = [item["path"] for item in request["upstream_refs"]]
    metadata["provenance"]["input_hashes"] = {
        item["path"]: item["hash"] for item in request["upstream_refs"]
    }
    atomic_write_json(metadata_path, metadata)
    archived = replace(archived, tree_hash=hash_tree(archived.path))
    request["candidate_ref"]["tree_hash"] = archived.tree_hash

    companion = archived.review_path
    request["review"]["companion_view_ref"].update(
        {
            "path": companion.relative_to(project).as_posix(),
            "hash": sha256_file(companion),
            "resolved_hash": sha256_file(companion),
        }
    )
    changelog_source = project / "artifacts" / "prds" / "DOCUMENT_CHANGELOG.md"
    changelog_snapshot = evidence_root / "document-changelog-snapshot.md"
    changelog_snapshot.write_bytes(changelog_source.read_bytes())
    presentation_paths = {
        "template_profile_ref": evidence_root / "template-profile.json",
        "version_record_ref": evidence_root / "version-record.json",
        "changelog_ref": changelog_snapshot,
    }
    archived_metadata = read_json(
        archived.path / f"{archived.path.name}.metadata.json"
    )
    selection = TemplateRegistry(TEMPLATES).selection_from_metadata(
        project, archived_metadata["template_profile"]
    )
    presentation_payloads = {
        "template_profile_ref": {
            "schema_version": "template-profile-evidence.v1",
            "profile_id": selection.profile_id,
            "version": selection.version,
            "template_path": selection.relative_path,
            "template_hash": selection.sha256,
            "source_kind": selection.origin,
            "selection_source": selection.selection_source,
            "fallback_reason": selection.fallback_reason,
            "requested_profile_id": selection.requested_profile_id,
            "requested_version": selection.requested_version,
            "output_contract_path": selection.output_contract_relative_path,
            "output_contract_hash": selection.output_contract_sha256,
            "output_contract_version": selection.output_contract_version,
        },
        "version_record_ref": {
            "schema_version": "document-version-record.v1",
            "candidate_hash": archived.document_hash,
            "version": archived.version,
            "status": "CANDIDATE_ARCHIVED",
        },
    }
    for field, path in presentation_paths.items():
        if not path.exists() and field != "changelog_ref":
            atomic_write_json(path, presentation_payloads[field])
        request["presentation"][field].update(
            {
                "path": path.relative_to(project).as_posix(),
                "hash": sha256_file(path),
                "resolved_hash": sha256_file(path),
            }
        )
    candidate_document_ref = {
        "role": "candidate_document",
        "path": archived.document_path.relative_to(project).as_posix(),
        "hash": archived.document_hash,
    }
    companion_ref = {
        "role": "review_companion",
        "path": companion.relative_to(project).as_posix(),
        "hash": sha256_file(companion),
    }
    finding_count = read_json(companion)["finding_count"]
    findings = [{"finding_id": f"f-{index + 1}"} for index in range(finding_count)]
    dispositions_payload = [
        {"finding_id": item["finding_id"], "status": "EXTERNAL_REVIEW"}
        for item in findings
    ]
    request["review"]["findings"] = findings
    request["review"]["dispositions"] = dispositions_payload
    request["review"]["companion_view_ref"]["finding_count"] = finding_count
    aggregate = evidence_root / "review-aggregate.json"
    atomic_write_json(
        aggregate,
        {
            "schema_version": "review-aggregate.v1",
            "authority": "ADVISORY_ONLY",
            "candidate_ref": {
                "path": candidate_document_ref["path"],
                "hash": archived.document_hash,
                "version": archived.version,
            },
            "attempts": [
                {"attempt_id": "review-product", "status": "COMPLETED", "roles_covered": ["product"]},
                {"attempt_id": "review-engineering", "status": "COMPLETED", "roles_covered": ["engineering_feasibility"]},
                {"attempt_id": "review-testability", "status": "COMPLETED", "roles_covered": ["testability"]},
            ],
            "findings": findings,
            "disagreements": [],
        },
    )
    dispositions = evidence_root / "review-dispositions.json"
    atomic_write_json(
        dispositions,
        {
            "schema_version": "review-dispositions.v1",
            "candidate_hash": archived.document_hash,
            "candidate_version": archived.version,
            "dispositions": dispositions_payload,
        },
    )
    request["review"]["aggregate_ref"] = {
        "path": aggregate.relative_to(project).as_posix(),
        "hash": sha256_file(aggregate),
        "version": 1,
    }
    request["review"]["dispositions_ref"] = {
        "path": dispositions.relative_to(project).as_posix(),
        "hash": sha256_file(dispositions),
        "version": 1,
    }
    companion_payload = read_json(companion)
    companion_payload["aggregate_ref"] = {
        key: request["review"]["aggregate_ref"][key]
        for key in ("path", "hash", "version")
    }
    companion_payload["dispositions_ref"] = {
        key: request["review"]["dispositions_ref"][key]
        for key in ("path", "hash", "version")
    }
    atomic_write_json(companion, companion_payload)
    archived = replace(
        archived,
        review_hash=sha256_file(companion),
        tree_hash=hash_tree(archived.path),
    )
    request["candidate_ref"]["tree_hash"] = archived.tree_hash
    request["review"]["companion_view_ref"].update(
        {"hash": archived.review_hash, "resolved_hash": archived.review_hash}
    )
    companion_ref["hash"] = archived.review_hash
    attempt_id = "attempt-prd-ready-receipts"
    events = verify_event_chain(controller._events_path(run_id))
    audit_snapshot = evidence_root / "audit-snapshot.json"
    atomic_write_json(
        audit_snapshot,
        {
            "schema_version": "audit-integrity-snapshot.v1",
            "status": "PASS",
            "run_id": run_id,
            "node_id": "prd.ready.gate",
            "attempt_id": attempt_id,
            "candidate_hash": archived.document_hash,
            "candidate_version": archived.version,
            "rules_version": READY_RULES_VERSION,
            "event_count": len(events),
            "event_head_hash": events[-1]["event_hash"],
        },
    )
    request["presentation"]["audit_snapshot_ref"] = {
        "path": audit_snapshot.relative_to(project).as_posix(),
        "hash": sha256_file(audit_snapshot),
        "version": 1,
    }
    mechanical = evidence_root / "mechanical-validation.json"
    atomic_write_json(
        mechanical,
        {
            "schema_version": "mechanical-validation.v1",
            "status": "PASS",
            "run_id": run_id,
            "node_id": "prd.ready.gate",
            "attempt_id": attempt_id,
            "candidate_hash": archived.document_hash,
            "candidate_version": archived.version,
            "rules_version": READY_RULES_VERSION,
            "checks": ["CURRENT_CANDIDATE", "UPSTREAM_REFS", "SCHEMA", "HASHES"],
        },
    )
    request["mechanical_validation_ref"] = {
        "path": mechanical.relative_to(project).as_posix(),
        "hash": sha256_file(mechanical),
        "version": 1,
    }
    state = controller.load_state(run_id)
    candidate_state_ref = {
        "role": "prd_candidate",
        "path": archived.document_path.relative_to(project).as_posix(),
        "hash": archived.document_hash,
        "tree_hash": archived.tree_hash,
        "artifact_path": archived.path.relative_to(project).as_posix(),
        "version": archived.version,
        "review_path": archived.review_path.relative_to(project).as_posix(),
        "review_hash": archived.review_hash,
    }
    authorized_refs = [
        *request["upstream_refs"],
        request["presentation"]["template_profile_ref"],
        request["presentation"]["version_record_ref"],
        request["presentation"]["changelog_ref"],
        request["presentation"]["audit_snapshot_ref"],
        request["mechanical_validation_ref"],
        request["review"]["companion_view_ref"],
        request["review"]["aggregate_ref"],
        request["review"]["dispositions_ref"],
    ]
    artifact_refs = dict(state["artifact_refs"])
    for index, ref in enumerate(authorized_refs):
        artifact_refs[f"ready-evidence:{index}"] = {
            key: ref[key] for key in ("path", "hash", "version") if key in ref
        }
    position_run_internal(
        controller,
        run_id,
        "prd.ready.gate",
        ["handoff.prepare"],
        artifact_refs=artifact_refs,
        state_updates={
            "current_candidate_ref": candidate_state_ref,
            "candidate_version": 1,
        },
    )
    persist_node_dispatch(controller, run_id, attempt_id)
    begin_node_call(controller, run_id, attempt_id)

    def issue(receipt_id: str, kind: str, subjects: list[dict]) -> dict:
        state = controller.load_state(run_id)
        return controller.issue_controller_receipt(
            run_id,
            receipt_id,
            kind,
            subjects,
            expected_state_version=state["state_version"],
        )

    if issue_receipts:
        request["controller_receipts"] = {
            "audit_integrity": issue(
                "audit-integrity",
                "audit_integrity",
                [{"role": "audit_snapshot", **request["presentation"]["audit_snapshot_ref"]}],
            ),
            "review_finalize": issue(
                "review-finalize",
                "review_finalize",
                [
                    candidate_document_ref,
                    companion_ref,
                    {"role": "review_aggregate", **request["review"]["aggregate_ref"]},
                    {"role": "review_dispositions", **request["review"]["dispositions_ref"]},
                ],
            ),
            "document_experience": issue(
                "document-experience",
                "document_experience",
                [
                    candidate_document_ref,
                    {"role": "template_profile", **request["presentation"]["template_profile_ref"]},
                    {"role": "version_record", **request["presentation"]["version_record_ref"]},
                    {"role": "document_changelog", **request["presentation"]["changelog_ref"]},
                ],
            ),
            "mechanical_contracts": issue(
                "mechanical-contracts",
                "mechanical_contracts",
                [
                    candidate_document_ref,
                    *[
                        {
                            "role": (
                                f"upstream_{kind}"
                                if len(items) == 1
                                else f"upstream_{kind}:{index}"
                            ),
                            **item,
                        }
                        for kind, items in upstream.items()
                        for index, item in enumerate(items)
                    ],
                    {"role": "mechanical_validation", **request["mechanical_validation_ref"]},
                ],
            ),
        }
        controller.execute_mechanical_result(run_id, attempt_id)
    request["run_id"] = run_id
    return request, archived


class ReviewsReadyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        assembled = assemble_prd(
            prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        )
        self.archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={},
            review_companion=finalized_review_companion(assembled),
        )
        self.candidate_ref = {
            "path": str(self.archived.path),
            "hash": self.archived.document_hash,
            "tree_hash": self.archived.tree_hash,
            "version": "v0.1",
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_reviewer_block_label_cannot_block_mechanically_complete_candidate(self) -> None:
        result = calculate_prd_ready(complete_ready_input(self.candidate_ref))
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.unmet, [])

    def test_required_evals_cannot_reach_full_release_without_verifiable_fulfillment_authority(self) -> None:
        request = complete_ready_input(self.candidate_ref)
        request, archived = materialize_ready_evidence(self.project, request, self.archived)
        request["evals"] = {
            "applicability": "REQUIRED",
            "fulfillment": "REVIEWED",
            "execution_status": "NOT_RUN",
            "pack_ref": {
                "path": archived.document_path.relative_to(self.project).as_posix(),
                "hash": archived.document_hash,
                "resolved_hash": archived.document_hash,
                "version": archived.version,
            },
            "review_ref": {
                "path": archived.review_path.relative_to(self.project).as_posix(),
                "hash": archived.review_hash,
                "resolved_hash": archived.review_hash,
                "version": archived.version,
            },
            "ground_truth_provenance": {
                "type": "CONTRACT_DERIVED_EXPECTATIONS",
                "statement": "self-attested same Host review",
                "exact_refs": [],
            },
        }
        controller = StateController(self.project, GRAPH)
        before_state = controller.load_state(request["run_id"])
        released = self.project / "artifacts" / "prds" / "released" / archived.path.name

        with self.assertRaisesRegex(PRDNotReady, "REQUIRED|fulfillment authority"):
            ready_and_release(
                self.project,
                archived,
                request,
                controller=controller,
                run_id=request["run_id"],
            )

        self.assertEqual(controller.load_state(request["run_id"]), before_state)
        self.assertFalse(released.exists())

    def test_six_mechanical_categories_return_exact_repair_targets(self) -> None:
        request = complete_ready_input(self.candidate_ref)
        request["candidate_ref"]["current"] = False
        request["review"]["finalized"] = False
        request["upstream_refs"][0]["stale"] = True
        request["evals"] = {"applicability": "REQUIRED", "fulfillment": "BLOCKED_MISSING_INPUT"}
        request["presentation"]["document_experience"] = "FAIL"
        request["mechanical_contracts"] = "FAIL"
        result = calculate_prd_ready(request)
        self.assertEqual(result.status, "NOT_READY")
        self.assertEqual(
            {item["category"] for item in result.unmet},
            {"CURRENT_CANDIDATE", "REVIEW_FINALIZE", "UPSTREAM_REFS", "EVALS", "PRESENTATION_VERSION", "MECHANICAL_CONTRACTS"},
        )
        self.assertTrue(all(item["repair_target"] and item["resume_point"] for item in result.unmet))

    def test_experiment_missing_measurement_and_rollback_cannot_release(self) -> None:
        request = complete_ready_input(self.candidate_ref)
        request["delivery_intent"] = "EXPERIMENT"
        request["experiment_contract"] = {"key_unknown": "conversion"}
        result = calculate_prd_ready(request)
        self.assertEqual(result.status, "NOT_READY")
        self.assertEqual(result.unmet[0]["category"], "EXPERIMENT_CONTRACT")

    def test_ready_evidence_retry_reuses_audit_checkpoint_and_preserves_exact_experiment_contract(self) -> None:
        submission = prd_submission()
        contract = complete_experiment_contract()
        submission["semantic_output"]["document_markdown"] = submission[
            "semantic_output"
        ]["document_markdown"].replace("v0.1", "v0.2")
        submission["semantic_output"]["metadata"]["version"] = "v0.2"
        submission["semantic_output"]["metadata"]["delivery_intent"] = "EXPERIMENT"
        submission["semantic_output"]["metadata"]["experiment_contract"] = contract
        assembled = assemble_prd(
            submission, TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        )
        archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={},
            review_companion=finalized_review_companion(assembled),
        )
        candidate_ref = {
            "path": str(archived.path),
            "hash": archived.document_hash,
            "tree_hash": archived.tree_hash,
            "version": archived.version,
        }
        _request, archived = materialize_ready_evidence(
            self.project,
            complete_ready_input(candidate_ref),
            archived,
            issue_receipts=False,
        )
        controller = StateController(self.project, GRAPH)
        runtime = HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core")
        with patch(
            "src.bpg.host_runtime.ready_and_release",
            side_effect=PRDNotReady("injected post-receipt Ready failure"),
        ):
            with self.assertRaisesRegex(
                TransitionRejected, "injected post-receipt Ready failure"
            ):
                runtime.dispatch_current("run-ready-receipts")
        partial_state = controller.load_state("run-ready-receipts")
        self.assertEqual(len(partial_state["ready_receipts"]), 4)
        self.assertIsNone(partial_state["release_ref"])
        ready_result_path = (
            self.project
            / ".better-product-graph"
            / "runs"
            / "run-ready-receipts"
            / "attempts"
            / "attempt-prd-ready-receipts"
            / "node-result.json"
        )
        first_ready_result_hash = sha256_file(ready_result_path)
        ready_receipt_path = ready_result_path.with_name("result-receipt.json")
        for label, path in (
            ("result", ready_result_path),
            ("receipt", ready_receipt_path),
        ):
            with self.subTest(symlinked_ready_authority=label):
                backup = path.with_name(path.name + ".regular-backup")
                path.replace(backup)
                path.symlink_to(backup)
                with self.assertRaisesRegex(
                    StateConflict,
                    "persisted Ready result differs from exact Controller retry",
                ):
                    controller.execute_mechanical_result(
                        "run-ready-receipts",
                        "attempt-prd-ready-receipts",
                    )
                path.unlink()
                backup.replace(path)
        first_snapshot = read_json(
            self.project
            / ".better-product-graph"
            / "runs"
            / "run-ready-receipts"
            / "ready-evidence"
            / "audit-snapshot.json"
        )
        tampered_snapshot = dict(first_snapshot)
        tampered_snapshot["event_head_hash"] = "sha256:" + "0" * 64
        snapshot_path = (
            self.project
            / ".better-product-graph"
            / "runs"
            / "run-ready-receipts"
            / "ready-evidence"
            / "audit-snapshot.json"
        )
        atomic_write_json(snapshot_path, tampered_snapshot)
        state = controller.load_state("run-ready-receipts")
        with self.assertRaisesRegex(
            StateConflict, "Ready evidence identity conflict: audit_snapshot"
        ):
            controller.prepare_ready_gate_evidence(
                "run-ready-receipts",
                "attempt-prd-ready-receipts",
                expected_state_version=state["state_version"],
            )
        atomic_write_json(snapshot_path, first_snapshot)

        before_resume = controller.load_state("run-ready-receipts")
        before_resume_event_count = len(
            verify_event_chain(controller._events_path("run-ready-receipts"))
        )
        resumed = runtime.handle_entry(
            "$better-product-graph resume run-ready-receipts"
        )
        self.assertEqual(resumed["status"], "RESUMED")
        self.assertEqual(resumed["state"], before_resume)
        self.assertEqual(
            len(verify_event_chain(controller._events_path("run-ready-receipts"))),
            before_resume_event_count,
        )

        # Reproduce the exact 0.2.4 state already persisted by a redundant
        # ACTIVE -> ACTIVE public resume before that operation became idempotent.
        legacy_resumed = read_json(
            controller._state_path("run-ready-receipts")
        )
        legacy_resumed["state_version"] += 1
        legacy_resume_version = legacy_resumed["state_version"]
        controller._commit_state_event(
            "run-ready-receipts",
            before_resume,
            legacy_resumed,
            {
                "event_type": "RUN_RESUMED",
                "actor": "state-controller",
                "run_id": "run-ready-receipts",
                "state_version": legacy_resumed["state_version"],
            },
            transaction_id=f"activity-{legacy_resume_version}-resume",
        )
        resume_journal = controller._transaction_path(
            "run-ready-receipts",
            f"activity-{legacy_resume_version}-resume",
        )
        journal_backup = resume_journal.with_suffix(".missing")
        resume_journal.replace(journal_backup)
        with self.assertRaisesRegex(
            TransitionRejected,
            "Ready retry authority changed by more than a redundant ACTIVE resume",
        ):
            runtime.dispatch_current("run-ready-receipts")
        journal_backup.replace(resume_journal)
        completed = runtime.dispatch_current("run-ready-receipts")
        completed_state = controller.load_state("run-ready-receipts")

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed_state["current_node"], "handoff.dispatch")
        self.assertIsNotNone(completed_state["release_ref"])
        self.assertEqual(len(completed_state["ready_receipts"]), 4)
        self.assertEqual(
            [
                item["attempt_id"]
                for item in completed_state["dispatch_attempts"]
                if item["node_id"] == "prd.ready.gate"
            ],
            ["attempt-prd-ready-receipts"],
        )
        self.assertEqual(read_json(snapshot_path), first_snapshot)
        self.assertEqual(sha256_file(ready_result_path), first_ready_result_hash)
        released_metadata = read_json(
            next(
                (
                    self.project
                    / "artifacts"
                    / "prds"
                    / "released"
                    / archived.path.name
                ).glob("*.metadata.json")
            )
        )
        self.assertEqual(released_metadata["experiment_contract"], contract)

    def test_declared_hash_without_matching_resolution_cannot_ready(self) -> None:
        request = complete_ready_input(self.candidate_ref)
        request["candidate_ref"].pop("resolved_hash")
        request["review"]["companion_view_ref"]["resolved_hash"] = "sha256:changed"
        request["upstream_refs"][0]["resolved_hash"] = "sha256:changed"
        request["presentation"]["template_profile_ref"].pop("resolved_hash")
        result = calculate_prd_ready(request)
        self.assertEqual(result.status, "NOT_READY")
        self.assertEqual(
            {item["category"] for item in result.unmet},
            {"CURRENT_CANDIDATE", "REVIEW_FINALIZE", "UPSTREAM_REFS", "PRESENTATION_VERSION"},
        )

    def test_mechanical_receipt_binds_every_decision_and_evidence_ref(self) -> None:
        request = complete_ready_input(self.candidate_ref)
        for kind, suffix in (("decision", "second"), ("evidence", "second")):
            request["upstream_refs"].append(
                {
                    "kind": kind,
                    "path": f"{kind}-{suffix}-v1.json",
                    "hash": f"sha256:{kind}-{suffix}",
                    "resolved_hash": f"sha256:{kind}-{suffix}",
                    "version": 1,
                    "current": True,
                    "stale": False,
                }
            )
        request, archived = materialize_ready_evidence(self.project, request, self.archived)
        second = next(
            item for item in request["upstream_refs"]
            if item["kind"] == "evidence" and "second" in item["path"]
        )
        path = self.project / second["path"]
        atomic_write_json(path, {"kind": "evidence", "version": 1, "tampered": True})

        with self.assertRaisesRegex(PRDNotReady, "mechanical_contracts|hash mismatch"):
            ready_and_release(
                self.project,
                archived,
                request,
                controller=StateController(self.project, GRAPH),
                run_id=request["run_id"],
            )

    def test_mechanical_receipt_accepts_graph_native_upstreams_and_markdown_plan(self) -> None:
        request, archived = materialize_ready_evidence(
            self.project,
            complete_ready_input(self.candidate_ref),
            self.archived,
            upstream_shape="graph_native",
        )

        released = ready_and_release(
            self.project,
            archived,
            request,
            controller=StateController(self.project, GRAPH),
            run_id=request["run_id"],
        )

        self.assertEqual(released.version, "v0.1")

    def test_ready_accepts_no_separate_evidence_record_when_other_upstreams_are_exact(self) -> None:
        request = complete_ready_input(self.candidate_ref)
        request["upstream_refs"] = [
            item for item in request["upstream_refs"] if item["kind"] != "evidence"
        ]
        request, archived = materialize_ready_evidence(
            self.project,
            request,
            self.archived,
            upstream_shape="graph_native",
        )

        released = ready_and_release(
            self.project,
            archived,
            request,
            controller=StateController(self.project, GRAPH),
            run_id=request["run_id"],
        )

        self.assertEqual(released.version, "v0.1")
        metadata = read_json(archived.path / f"{archived.path.name}.metadata.json")
        self.assertEqual(metadata["evidence_refs"], [])

    def test_ready_still_requires_at_least_one_decision_record(self) -> None:
        request = complete_ready_input(self.candidate_ref)
        request["upstream_refs"] = [
            item for item in request["upstream_refs"] if item["kind"] != "decision"
        ]

        result = calculate_prd_ready(request)

        self.assertEqual(result.status, "NOT_READY")
        self.assertIn("UPSTREAM_REFS", {item["category"] for item in result.unmet})

    def test_mechanical_receipt_rejects_legacy_fake_kind_version_upstreams(self) -> None:
        before = {
            path.relative_to(self.project).as_posix(): sha256_file(path)
            for path in self.project.rglob("*")
            if path.is_file()
        }
        with self.assertRaisesRegex(
            TransitionRejected, "Node Result|Product Plan|upstream"
        ):
            materialize_ready_evidence(
                self.project,
                complete_ready_input(self.candidate_ref),
                self.archived,
                upstream_shape="legacy_fake",
            )
        self.assertFalse((self.project / "artifacts" / "prds" / "released").exists())
        self.assertNotEqual(before, {})

    def test_mechanical_receipt_rejects_wrong_slice_node_role(self) -> None:
        with self.assertRaisesRegex(
            (TransitionRejected, ValueError), "product.planning|Slice|node"
        ):
            materialize_ready_evidence(
                self.project,
                complete_ready_input(self.candidate_ref),
                self.archived,
                upstream_shape="graph_wrong_slice_node",
            )

    def test_mechanical_receipt_rejects_markdown_plan_not_bound_by_slice(self) -> None:
        with self.assertRaisesRegex(
            (TransitionRejected, ValueError), "Product Plan|bind|artifact"
        ):
            materialize_ready_evidence(
                self.project,
                complete_ready_input(self.candidate_ref),
                self.archived,
                upstream_shape="graph_unbound_plan",
            )

    def test_matching_caller_claims_for_nonexistent_refs_cannot_release(self) -> None:
        request = complete_ready_input(self.candidate_ref)

        with self.assertRaisesRegex(PRDNotReady, "lifecycle authority"):
            ready_and_release(self.project, self.archived, request)

        self.assertFalse(
            (self.project / "artifacts" / "prds" / "released" / self.archived.path.name).exists()
        )

    def test_ready_atomically_creates_immutable_release_and_local_handoff_never_claims_sent(self) -> None:
        request, self.archived = materialize_ready_evidence(
            self.project, complete_ready_input(self.candidate_ref), self.archived
        )
        released = ready_and_release(
            self.project,
            self.archived,
            request,
            controller=StateController(self.project, GRAPH),
            run_id=request["run_id"],
        )
        handoff = prepare_local_handoff(released)
        self.assertTrue(released.path.is_dir())
        self.assertEqual(handoff["status"], "LOCAL_READY")
        self.assertFalse(handoff["sent"])
        self.assertEqual(handoff["external_approval"], "NOT_CLAIMED")
        self.assertEqual(handoff["connector_status"], "NOT_CONFIGURED")
        release_event = verify_event_chain(
            self.project / "artifacts" / "prds" / "PRODUCT_DOCUMENT_CHANGELOG.jsonl"
        )[-1]
        expected_upstream = {
            (item["kind"], item["path"], item["hash"], item["version"])
            for item in request["upstream_refs"]
        }
        actual_upstream = {
            (item["kind"], item["path"], item["hash"], item["version"])
            for item in release_event["upstream_refs"]
        }
        self.assertEqual(actual_upstream, expected_upstream)
        self.assertEqual(
            release_event["template_ref"]["hash"],
            request["presentation"]["template_profile_ref"]["hash"],
        )
        self.assertEqual(
            release_event["review_ref"]["hash"],
            request["review"]["companion_view_ref"]["hash"],
        )

    def test_release_crash_after_state_commit_leaves_no_orphan_and_recovers_publish(self) -> None:
        request, self.archived = materialize_ready_evidence(
            self.project, complete_ready_input(self.candidate_ref), self.archived
        )
        controller = StateController(self.project, GRAPH)
        released_path = self.project / "artifacts" / "prds" / "released" / self.archived.path.name

        with self.assertRaises(InjectedCrash):
            ready_and_release(
                self.project,
                self.archived,
                request,
                controller=controller,
                run_id=request["run_id"],
                failpoint=crash_at("after_release_state"),
            )

        self.assertFalse(released_path.exists())
        recovered = recover_run(controller, request["run_id"])
        self.assertEqual(recovered["status"], "RECOVERED_TRANSACTION")
        self.assertTrue(released_path.is_dir())
        self.assertEqual(controller.load_state(request["run_id"])["status"], "RELEASED")

    def test_release_early_recovery_rejects_tampered_publish_inputs_without_side_effects(self) -> None:
        attacks = ("archive", "stage")
        for attack in attacks:
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as directory:
                project = Path(directory).resolve()
                assembled = assemble_prd(
                    prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
                )
                archived = archive_prd_candidate(
                    project,
                    assembled,
                    assets={},
                    review_companion=finalized_review_companion(assembled),
                )
                candidate_ref = {
                    "path": str(archived.path),
                    "hash": archived.document_hash,
                    "tree_hash": archived.tree_hash,
                    "version": "v0.1",
                }
                request, archived = materialize_ready_evidence(
                    project, complete_ready_input(candidate_ref), archived
                )
                controller = StateController(project, GRAPH)

                with self.assertRaises(InjectedCrash):
                    ready_and_release(
                        project,
                        archived,
                        request,
                        controller=controller,
                        run_id=request["run_id"],
                        failpoint=crash_at("after_release_staged"),
                    )

                journal_path = controller._transaction_path(
                    request["run_id"], f"ready-release-{archived.path.name}"
                )
                journal = read_json(journal_path)
                if attack == "archive":
                    archived.document_path.write_text(
                        "tampered after staged", encoding="utf-8"
                    )
                else:
                    stage = Path(journal["release_publish"]["stage_path"])
                    (stage / "tampered-after-staged.txt").write_text(
                        "tampered", encoding="utf-8"
                    )
                before = {
                    path.relative_to(project).as_posix()
                    + ("/" if path.is_dir() else ""): (
                        None if path.is_dir() else path.read_bytes()
                    )
                    for path in project.rglob("*")
                }

                with self.assertRaises(StateConflict):
                    controller.authoritative_read_barrier(request["run_id"])

                after = {
                    path.relative_to(project).as_posix()
                    + ("/" if path.is_dir() else ""): (
                        None if path.is_dir() else path.read_bytes()
                    )
                    for path in project.rglob("*")
                }
                self.assertEqual(after, before)
                self.assertEqual(read_json(journal_path)["status"], "PREPARED")

    def test_release_recovers_every_staged_event_state_publish_boundary(self) -> None:
        phases = (
            "after_release_staged",
            "after_release_event",
            "after_release_state",
            "after_release_publish",
        )
        for index, phase in enumerate(phases, start=1):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                project = Path(directory).resolve()
                assembled = assemble_prd(
                    prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
                )
                archived = archive_prd_candidate(
                    project,
                    assembled,
                    assets={},
                    review_companion=finalized_review_companion(assembled),
                )
                candidate_ref = {
                    "path": str(archived.path),
                    "hash": archived.document_hash,
                    "tree_hash": archived.tree_hash,
                    "version": "v0.1",
                }
                request, archived = materialize_ready_evidence(
                    project, complete_ready_input(candidate_ref), archived
                )
                controller = StateController(project, GRAPH)

                with self.assertRaises(InjectedCrash):
                    ready_and_release(
                        project,
                        archived,
                        request,
                        controller=controller,
                        run_id=request["run_id"],
                        failpoint=crash_at(phase),
                    )

                recover_run(controller, request["run_id"])
                recover_run(controller, request["run_id"])
                recovered = controller.authoritative_read_barrier(request["run_id"])
                released_path = (
                    project / "artifacts" / "prds" / "released" / archived.path.name
                )
                events = verify_event_chain(controller._events_path(request["run_id"]))

                self.assertTrue(released_path.is_dir())
                self.assertEqual(recovered["status"], "RELEASED")
                self.assertEqual(recovered["current_node"], "handoff.prepare")
                self.assertEqual(
                    sum(event["event_type"] == "PRD_RELEASE_COMMITTED" for event in events),
                    1,
                )

    def test_release_recovery_validates_archive_before_publishing_staged_release(self) -> None:
        request, self.archived = materialize_ready_evidence(
            self.project, complete_ready_input(self.candidate_ref), self.archived
        )
        controller = StateController(self.project, GRAPH)
        released_path = (
            self.project / "artifacts" / "prds" / "released" / self.archived.path.name
        )

        with self.assertRaises(InjectedCrash):
            ready_and_release(
                self.project,
                self.archived,
                request,
                controller=controller,
                run_id=request["run_id"],
                failpoint=crash_at("after_release_state"),
            )

        self.archived.document_path.write_text("tampered after crash", encoding="utf-8")

        with self.assertRaises(StateConflict):
            controller.authoritative_read_barrier(request["run_id"])

        self.assertFalse(released_path.exists())

    def test_ready_release_transaction_is_exactly_idempotent(self) -> None:
        request, self.archived = materialize_ready_evidence(
            self.project, complete_ready_input(self.candidate_ref), self.archived
        )
        controller = StateController(self.project, GRAPH)
        first = ready_and_release(
            self.project,
            self.archived,
            request,
            controller=controller,
            run_id=request["run_id"],
        )
        second = ready_and_release(
            self.project,
            self.archived,
            request,
            controller=controller,
            run_id=request["run_id"],
        )
        self.assertEqual(second.tree_hash, first.tree_hash)
        events = [
            item
            for item in verify_event_chain(controller._events_path(request["run_id"]))
            if item.get("event_type") == "PRD_RELEASE_COMMITTED"
        ]
        self.assertEqual(len(events), 1)

    def test_release_rejects_ready_request_bound_to_a_different_candidate(self) -> None:
        request, self.archived = materialize_ready_evidence(
            self.project, complete_ready_input(self.candidate_ref), self.archived
        )
        request["candidate_ref"].update(
            {
                "hash": "sha256:different-candidate",
                "resolved_hash": "sha256:different-candidate",
            }
        )
        request["review"]["candidate_hash"] = "sha256:different-candidate"
        request["review"]["companion_view_ref"]["candidate_hash"] = (
            "sha256:different-candidate"
        )

        with self.assertRaisesRegex(PRDNotReady, "exact archived Candidate"):
            ready_and_release(
                self.project,
                self.archived,
                request,
                controller=StateController(self.project, GRAPH),
                run_id=request["run_id"],
            )

        self.assertFalse(
            (self.project / "artifacts" / "prds" / "released" / self.archived.path.name).exists()
        )


if __name__ == "__main__":
    unittest.main()
