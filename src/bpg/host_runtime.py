"""Installed Host-Agent execution API over the deterministic Controller."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from .documents import ImmutableArtifactError, archive_prd_candidate
from .document_experience_profile import (
    DocumentExperienceProfileError,
    resolve_prd_document_experience,
)
from .delivery_contract import (
    DeliveryContractError,
    active_scope_projection_from_planning_result,
    canonical_active_scope_projection,
    derive_active_scope_ref,
    derive_spec_traceability,
    validate_candidate_delivery_contract,
)
from .engine import HostEngine
from .failpoints import begin_node_call, persist_node_dispatch
from .node_registry import NodeRegistry
from .prd_contract import PRDContractError, assemble_prd, markdown_h2_section
from .planning_contract import derive_prd_run_specs
from .planning_context import discover_planning_context
from .ready import PRDNotReady, ready_and_release
from .product_memory import persist_decision_proposal
from .state_controller import StateConflict, StateController, TransitionRejected
from .storage import canonical_json_bytes, read_json, sha256_bytes, sha256_file
from .templates import TemplateRegistry


class HostRuntime:
    def __init__(self, project_root: Path, graph_manifest: Path, skill_root: Path):
        self.controller = StateController(project_root, graph_manifest, skill_root=skill_root)
        self.engine = HostEngine(project_root, self.controller)
        self.registry = NodeRegistry(skill_root, graph_manifest)

    def _plan_dispatch(self, run_id: str) -> dict[str, Any]:
        with self.controller.mutation_lock(run_id):
            state = self.controller.load_state(run_id)
            if state["status"] != "ACTIVE":
                raise TransitionRejected(
                    f"Run must be ACTIVE to dispatch, got {state['status']}"
                )
            if state["current_node"] == "prd.ready.gate":
                state = self.controller.recover_redundant_ready_resume(
                    run_id,
                    expected_state_version=state["state_version"],
                )
            current = [
                item
                for item in state.get("dispatch_attempts", [])
                if item.get("node_id") == state["current_node"]
                and item.get("status") == "DISPATCHED"
                and item.get("authorized_state_version") == state["state_version"]
                and item.get("authority_hash")
                == self.controller._dispatch_authority_hash(state)
            ]
            if current:
                if len(current) != 1 or not isinstance(current[0].get("contract"), dict):
                    raise TransitionRejected("current Node has ambiguous dispatch authority")
                durable_contract = deepcopy(current[0]["contract"])
                if state["current_node"] == "prd.optimize":
                    expected_context = self.controller.prd_optimize_context(
                        run_id, state
                    )
                    durable_context = durable_contract.get("optimize_context")
                    if durable_context != expected_context:
                        compatibility = self.registry.instruction_compatibility(
                            "prd.optimize", durable_contract.get("instruction_hash")
                        )
                        if not (
                            compatibility == "DECLARED_COMPATIBLE_SUCCESSOR"
                            and self.controller._is_pre_trace_authority_optimize_context(
                                durable_context, expected_context
                            )
                        ):
                            raise TransitionRejected(
                                "current PRD Optimize dispatch context drifted"
                            )
                        durable_contract["optimize_context"] = expected_context
                return durable_contract
            attempt_id = f"attempt-{uuid4().hex}"
            hashes: dict[str, str] = {}
            for ref in state.get("artifact_refs", {}).values():
                path = ref["path"]
                if path in hashes and hashes[path] != ref["hash"]:
                    raise TransitionRejected(
                        f"dispatch inputs bind conflicting hashes for {path}"
                    )
                hashes[path] = ref["hash"]
            refs = list(hashes)
            envelope = self.registry.dispatch_envelope(
                state["current_node"], attempt_id, refs, hashes
            )
            if state["current_node"] == "prd.optimize":
                envelope["optimize_context"] = self.controller.prd_optimize_context(
                    run_id, state
                )
            elif state["current_node"] == "product.planning" and isinstance(
                state.get("scope_reconciliation"), dict
            ):
                generation = self.controller.reconciliation_generation_context(
                    run_id, state
                )
                envelope["reconciliation_context"] = {
                    "schema_version": "planning-reconciliation-context.v1",
                    "source_candidate_ref": generation["source_candidate_ref"],
                    "prd_id": generation["prd_id"],
                    "exact_delta": generation["scope_reconciliation"]["exact_delta"],
                }
            elif state["current_node"] == "prd.generate" and isinstance(
                state.get("scope_reconciliation"), dict
            ):
                envelope["reconciliation_context"] = (
                    self.controller.reconciliation_generation_context(run_id, state)
                )
            if state["current_node"] == "prd.generate":
                envelope["prd_generation_context"] = self._prd_generation_context(
                    run_id, state, refs
                )
            elif state["current_node"] == "planning.context.prepare":
                envelope["planning_context_discovery"] = discover_planning_context(
                    self.controller.project_root
                )
            elif state["current_node"] == "review.parallel":
                envelope["writing_review_context"] = self.controller.writing_review_context(
                    state, envelope["resource_refs"]
                )
            persist_node_dispatch(self.controller, run_id, attempt_id, contract=envelope)
            begin_node_call(self.controller, run_id, attempt_id)
            return envelope

    def dispatch_current(self, run_id: str) -> dict[str, Any]:
        state = self.controller.authoritative_read_barrier(run_id)
        if (
            state["status"] == "COMPLETED"
            and state["current_node"] == "handoff.dispatch"
            and isinstance(state.get("handoff_ref"), dict)
            and state["handoff_ref"].get("delivery_kind") == "BUG"
        ):
            return self.engine._prepare_handoff(run_id)
        if state["current_node"] == "handoff.prepare" and state["status"] in {
            "ACTIVE",
            "RELEASED",
        }:
            result = self.engine._prepare_handoff(run_id)
            if result.get("status") != "COMPLETED":
                raise TransitionRejected(
                    f"exact Run could not complete local Handoff: {result.get('reason')}"
                )
            return result
        contract = self.registry.contracts[state["current_node"]]
        if contract["producer_kind"] != "HOST_AGENT":
            if state["current_node"] in {"problem.ready.gate", "plan.ready.gate"}:
                return self._complete_validation_gate(run_id)
            if state["current_node"] == "review.finalize":
                return self._complete_review_finalize(run_id)
            if state["current_node"] == "prd.ready.gate":
                return self._complete_prd_ready(run_id)
            raise TransitionRejected(f"mechanical node {state['current_node']} has no Controller executor")
        return self._plan_dispatch(run_id)

    def fulfill_evals(
        self, run_id: str, submission: dict[str, Any], *, failpoint=None
    ) -> dict[str, Any]:
        """Bind one exact independent Eval repair and dispatch formal joint re-review."""

        state = self.controller.authoritative_read_barrier(run_id)
        fulfilled = self.controller.fulfill_required_evals(
            run_id,
            submission,
            expected_state_version=state["state_version"],
            failpoint=failpoint,
        )
        dispatch = self.dispatch_current(run_id)
        return {
            "status": "EVALS_FULFILLED_REVIEW_REQUIRED",
            "run_id": run_id,
            "state": self.controller.load_state(run_id),
            "execution_status": "NOT_RUN",
            "ready_status": "NOT_READY",
            "release_status": "NOT_RELEASED",
            "receipt_ref": fulfilled["receipt_ref"],
            "dispatch": dispatch,
        }

    def _complete_review_finalize(self, run_id: str) -> dict[str, Any]:
        dispatch = self._plan_dispatch(run_id)
        state = self.controller.load_state(run_id)
        self.controller.finalize_review_and_transition(
            run_id,
            dispatch["attempt_id"],
            expected_state_version=state["state_version"],
        )
        return self.dispatch_current(run_id)

    def _complete_prd_ready(self, run_id: str) -> dict[str, Any]:
        repair = self.engine._required_evals_repair_response(run_id)
        if repair is not None:
            return repair
        self.controller.prevalidate_ready_evals(run_id)
        dispatch = self._plan_dispatch(run_id)
        state = self.controller.load_state(run_id)
        archived, request, subjects = self.controller.prepare_ready_gate_evidence(
            run_id,
            dispatch["attempt_id"],
            expected_state_version=state["state_version"],
        )
        receipts: dict[str, dict[str, Any]] = {}
        for kind in (
            "audit_integrity",
            "review_finalize",
            "document_experience",
            "mechanical_contracts",
        ):
            state = self.controller.load_state(run_id)
            receipts[kind] = self.controller.issue_controller_receipt(
                run_id,
                kind.replace("_", "-"),
                kind,
                subjects[kind],
                expected_state_version=state["state_version"],
            )
        request["controller_receipts"] = receipts
        self.controller.execute_mechanical_result(run_id, dispatch["attempt_id"])
        try:
            ready_and_release(
                self.controller.project_root,
                archived,
                request,
                controller=self.controller,
                run_id=run_id,
            )
        except PRDNotReady as error:
            raise TransitionRejected(str(error)) from error
        result = self.engine._prepare_handoff(run_id)
        if result.get("status") != "COMPLETED":
            raise TransitionRejected(
                f"exact Released Run could not complete local Handoff: {result.get('reason')}"
            )
        return result

    def _complete_validation_gate(self, run_id: str) -> dict[str, Any]:
        state = self.controller.load_state(run_id)
        node_id = state["current_node"]
        if node_id == "problem.ready.gate":
            return self._complete_problem_ready_gate(run_id)
        targets = {
            "plan.ready.gate": "prd.generate",
        }
        if node_id not in targets:
            raise TransitionRejected(f"unsupported validation Gate: {node_id}")
        dispatch = self._plan_dispatch(run_id)
        self.controller.execute_mechanical_result(run_id, dispatch["attempt_id"])
        state = self.controller.load_state(run_id)
        self.controller.transition(
            run_id,
            {
                "requested_node": targets[node_id],
                "attempt_id": dispatch["attempt_id"],
                "expected_state_version": state["state_version"],
            },
        )
        return self.dispatch_current(run_id)

    def _complete_problem_ready_gate(self, run_id: str) -> dict[str, Any]:
        """Persist one formal READY/NOT_READY calculation and expose exact receipts."""

        dispatch = self._plan_dispatch(run_id)
        attempt_id = dispatch["attempt_id"]
        result_path = self.controller._result_path(run_id, attempt_id)
        if not result_path.is_file():
            self.controller.execute_mechanical_result(run_id, attempt_id)
        state = self.controller.load_state(run_id)
        result = read_json(result_path)
        self.controller._validate_result_contract(
            state, result, controller_owned=True
        )
        receipt_path = result_path.with_name("result-receipt.json")
        if not receipt_path.is_file():
            self.controller.recover_result_receipt(run_id, attempt_id)
        receipt = read_json(receipt_path)
        if receipt.get("result_hash") != sha256_file(result_path):
            raise TransitionRejected("problem.ready.gate result receipt hash mismatch")
        output = result["mechanical_output"]
        result_ref = {
            "role": "problem_ready_calculation",
            "path": result_path.relative_to(self.controller.project_root).as_posix(),
            "hash": sha256_file(result_path),
            "version": 1,
        }
        receipt_ref = {
            "role": "problem_ready_receipt",
            "path": receipt_path.relative_to(self.controller.project_root).as_posix(),
            "hash": sha256_file(receipt_path),
            "version": 1,
        }
        if output["status"] == "NOT_READY":
            return {
                "status": "NOT_READY",
                "run_id": run_id,
                "state": state,
                "gate_result": output,
                "gate_result_ref": result_ref,
                "gate_receipt_ref": receipt_ref,
                "dispatch": None,
            }
        self.controller.transition(
            run_id,
            {
                "requested_node": "product.decision",
                "attempt_id": attempt_id,
                "expected_state_version": state["state_version"],
            },
        )
        next_dispatch = self.dispatch_current(run_id)
        return {
            "status": "ADVANCED",
            "run_id": run_id,
            "state": self.controller.load_state(run_id),
            "gate_result": output,
            "gate_result_ref": result_ref,
            "gate_receipt_ref": receipt_ref,
            "dispatch": next_dispatch,
        }

    def _complete_ingest(self, run_id: str) -> dict[str, Any]:
        dispatch = self._plan_dispatch(run_id)
        if dispatch["node_id"] != "signal.ingest":
            raise RuntimeError("new Run must begin at signal.ingest")
        self.controller.execute_mechanical_result(run_id, dispatch["attempt_id"])
        state = self.controller.load_state(run_id)
        self.controller.transition(
            run_id,
            {
                "requested_node": "signal.prepare",
                "attempt_id": dispatch["attempt_id"],
                "expected_state_version": state["state_version"],
            },
        )
        return self.dispatch_current(run_id)

    def _complete_route_select(self, run_id: str, destination: str) -> dict[str, Any] | None:
        routes = {
            "INCIDENT_ASSESS": "incident.assess",
            "BUG_BASELINE_CHECK": "bug.baseline.check",
            "DISCOVERY_START": "planning.context.prepare",
        }
        if destination == "INBOX_ONLY":
            raise RuntimeError("an activated Run cannot route back to signal-scoped INBOX_ONLY")
        target = routes.get(destination)
        if target is None:
            raise RuntimeError("signal.classify returned an unsupported route destination")
        dispatch = self._plan_dispatch(run_id)
        if dispatch["node_id"] != "route.select":
            raise RuntimeError("route.select mechanical execution requires route.select state")
        self.controller.execute_mechanical_result(
            run_id,
            dispatch["attempt_id"],
            route_destination=destination,
        )
        state = self.controller.load_state(run_id)
        self.controller.transition(
            run_id,
            {
                "requested_node": target,
                "attempt_id": dispatch["attempt_id"],
                "expected_state_version": state["state_version"],
            },
        )
        return self.dispatch_current(run_id)

    def _template_root(self) -> Path:
        source = self.registry.skill_root / "templates"
        installed = self.registry.skill_root / "references" / "templates"
        return source if source.is_dir() else installed

    @staticmethod
    def _delivery_upstream_pairs(
        metadata: dict[str, Any],
        state: dict[str, Any],
        result: dict[str, Any],
    ) -> list[tuple[str, dict[str, Any]]]:
        pairs: list[tuple[str, dict[str, Any]]] = []
        for label, refs in (
            ("decision", metadata.get("decision_refs")),
            ("evidence", metadata.get("evidence_refs")),
        ):
            if isinstance(refs, list):
                pairs.extend(
                    (
                        label if len(refs) == 1 else f"{label}:{index}",
                        ref,
                    )
                    for index, ref in enumerate(refs)
                    if isinstance(ref, dict)
                )
        pairs.extend(
            (role, metadata[field])
            for role, field in (
                ("roadmap", "roadmap_snapshot_ref"),
                ("product_plan", "product_plan_ref"),
                ("slice", "slice_ref"),
                ("knowledge", "knowledge_snapshot_ref"),
            )
            if isinstance(metadata.get(field), dict)
        )
        artifacts = [
            item
            for item in state.get("artifact_refs", {}).values()
            if isinstance(item, dict)
        ]
        consumed_order = {
            attempt_id: index
            for index, attempt_id in enumerate(state.get("consumed_attempts", []))
            if isinstance(attempt_id, str)
        }

        def latest_node_result(node_id: str, *, dispatched_input_only: bool = False):
            candidates = [
                item
                for item in artifacts
                if item.get("role") == "node_result"
                and item.get("node_id", item.get("origin_node_id")) == node_id
                and (
                    not dispatched_input_only
                    or item.get("path") in result.get("input_refs", [])
                )
            ]
            return max(
                candidates,
                key=lambda item: consumed_order.get(
                    item.get("attempt_id", item.get("origin_attempt_id")), -1
                ),
                default=None,
            )

        problem_ready = latest_node_result("problem.ready.gate")
        if isinstance(problem_ready, dict):
            pairs.append(("problem_ready", problem_ready))
        reconciled_generate = (
            result.get("node_id") == "prd.generate"
            and isinstance(state.get("scope_reconciliation"), dict)
        )
        if result.get("node_id") == "prd.optimize" or reconciled_generate:
            current = state.get("current_candidate_ref")
            source_matches = [
                item
                for item in artifacts
                if item.get("role") == "prd_candidate"
                and isinstance(current, dict)
                and all(
                    item.get(field) == current.get(field)
                    for field in ("path", "hash", "version")
                )
                and item.get("origin_node_id") in {"prd.generate", "prd.optimize"}
            ]
            if len(source_matches) != 1:
                raise DeliveryContractError(
                    "spec_traceability source_candidate lacks unique committed origin"
                )
            pairs.append(("source_candidate", source_matches[0]))
            review_aggregate = latest_node_result(
                "review.aggregate", dispatched_input_only=True
            )
            if not isinstance(review_aggregate, dict):
                raise DeliveryContractError(
                    "spec_traceability review_aggregate_result lacks committed dispatch origin"
                )
            pairs.append(("review_aggregate_result", review_aggregate))
        return pairs

    @staticmethod
    def _exact_metadata_ref(ref: dict[str, Any]) -> dict[str, Any]:
        return {field: ref[field] for field in ("path", "hash", "version")}

    def _prd_generation_context(
        self,
        run_id: str,
        state: dict[str, Any],
        input_refs: list[str],
    ) -> dict[str, Any]:
        """Expose Controller-derived provenance that the Host must bind, not infer."""

        available_paths = set(input_refs)
        artifacts = [
            item
            for item in state.get("artifact_refs", {}).values()
            if isinstance(item, dict) and item.get("path") in available_paths
        ]
        consumed_order = {
            attempt_id: index
            for index, attempt_id in enumerate(state.get("consumed_attempts", []))
            if isinstance(attempt_id, str)
        }

        def origin(item: dict[str, Any]) -> tuple[Any, Any]:
            return (
                item.get("origin_node_id", item.get("node_id")),
                item.get("origin_attempt_id", item.get("attempt_id")),
            )

        def matching(
            *, roles: set[str], nodes: set[str]
        ) -> list[dict[str, Any]]:
            return [
                item
                for item in artifacts
                if item.get("role") in roles and origin(item)[0] in nodes
            ]

        def latest(
            label: str, *, roles: set[str], nodes: set[str]
        ) -> dict[str, Any]:
            candidates = matching(roles=roles, nodes=nodes)
            if not candidates:
                raise TransitionRejected(
                    f"PRD generation authority is missing committed {label}"
                )
            ranked = sorted(
                candidates,
                key=lambda item: (
                    consumed_order.get(origin(item)[1], -1),
                    item.get("path", ""),
                ),
            )
            winner = ranked[-1]
            winner_rank = consumed_order.get(origin(winner)[1], -1)
            tied = [
                item
                for item in ranked
                if consumed_order.get(origin(item)[1], -1) == winner_rank
                and item.get("path") != winner.get("path")
            ]
            if tied:
                raise TransitionRejected(
                    f"PRD generation authority has ambiguous committed {label}"
                )
            return winner

        decisions = matching(
            roles={"decision_record"}, nodes={"product.decision"}
        )
        if not decisions:
            raise TransitionRejected(
                "PRD generation authority is missing committed Product Decision"
            )
        decisions = sorted(decisions, key=lambda item: item["path"])
        roadmap = latest(
            "roadmap snapshot",
            roles={"node_result"},
            nodes={"evidence.collect"},
        )
        product_plan = latest(
            "Product Plan",
            roles={"product_plan"},
            nodes={"product.planning"},
        )
        planning_result = latest(
            "Product Planning Node Result",
            roles={"node_result"},
            nodes={"product.planning"},
        )
        knowledge = latest(
            "Knowledge Snapshot",
            roles={"node_result"},
            nodes={"evidence.map"},
        )
        evidence = matching(
            roles={"evidence"},
            nodes={"evidence.collect", "problem.learning.loop"},
        )
        reserved_upstream_identities = {
            (item["path"], item["hash"], item["version"])
            for item in (roadmap, product_plan, planning_result, knowledge, *decisions)
        }
        evidence = [
            item
            for item in evidence
            if (item["path"], item["hash"], item["version"])
            not in reserved_upstream_identities
        ]
        evidence = sorted(
            {
                (item["path"], item["hash"], item["version"]): item
                for item in evidence
            }.values(),
            key=lambda item: item["path"],
        )

        planning_payload = read_json(
            self.controller.project_root / planning_result["path"]
        )
        specs = derive_prd_run_specs(planning_payload.get("semantic_output", {}))
        reconciliation = state.get("scope_reconciliation")
        if isinstance(reconciliation, dict):
            generation = self.controller.reconciliation_generation_context(
                run_id, state
            )
            eligible = [
                item for item in specs if item["planned_prd_id"] == generation["prd_id"]
            ]
            version = generation["next_version"]
        else:
            eligible = specs
            version = "v0.1"
        if len(eligible) != 1:
            raise TransitionRejected(
                "PRD generation requires exactly one Controller-selected activated and "
                "eligible Slice in the current Run"
            )
        spec = eligible[0]

        policy_roots = (
            self.controller.skill_root / "references" / "policies",
            self.controller.skill_root / "policies",
        )
        policy_root = next(
            (path for path in policy_roots if path.is_dir() and not path.is_symlink()),
            None,
        )
        if policy_root is None:
            raise TransitionRejected("PRD Document Experience policy root is missing")
        try:
            document_experience = resolve_prd_document_experience(policy_root)
        except DocumentExperienceProfileError as error:
            raise TransitionRejected(
                f"PRD Document Experience binding is invalid: {error}"
            ) from error

        metadata: dict[str, Any] = {
            "prd_id": spec["planned_prd_id"],
            "delivery_intent": spec["delivery_intent"],
            "document_experience": document_experience,
            "decision_refs": [self._exact_metadata_ref(item) for item in decisions],
            "roadmap_snapshot_ref": self._exact_metadata_ref(roadmap),
            "product_plan_ref": self._exact_metadata_ref(product_plan),
            "slice_ref": self._exact_metadata_ref(planning_result),
            "knowledge_snapshot_ref": self._exact_metadata_ref(knowledge),
            "evidence_refs": [self._exact_metadata_ref(item) for item in evidence],
        }
        metadata["active_scope_ref"] = derive_active_scope_ref(
            planning_payload,
            metadata["product_plan_ref"],
            metadata["prd_id"],
        )
        pseudo_result = {"node_id": "prd.generate", "input_refs": input_refs}
        metadata["spec_traceability"] = derive_spec_traceability(
            self._delivery_upstream_pairs(metadata, state, pseudo_result),
            state.get("artifact_refs", {}),
        )
        return {
            "schema_version": "prd-generation-context.v1",
            "metadata_authority": metadata,
            "candidate_defaults": {
                "version": version,
                "status": "CANDIDATE",
            },
        }

    def _runtime_forbidden_values(
        self, run_id: str, state: dict[str, Any]
    ) -> set[str]:
        """Collect Controller-known specification lifecycle identities for Runtime isolation."""

        forbidden = {run_id}
        forbidden.update(
            attempt_id
            for attempt_id in state.get("consumed_attempts", [])
            if isinstance(attempt_id, str) and attempt_id
        )
        for dispatch in state.get("dispatch_attempts", []):
            if isinstance(dispatch, dict) and isinstance(dispatch.get("attempt_id"), str):
                forbidden.add(dispatch["attempt_id"])
        for attempt_id in state.get("consumed_attempts", []):
            if not isinstance(attempt_id, str) or not attempt_id:
                continue
            receipt_path = self.controller._result_path(
                run_id, attempt_id
            ).with_name("result-receipt.json")
            if receipt_path.is_file() and not receipt_path.is_symlink():
                forbidden.add(
                    receipt_path.relative_to(self.controller.project_root).as_posix()
                )
                forbidden.add(sha256_file(receipt_path))
        for ref in state.get("artifact_refs", {}).values():
            if not isinstance(ref, dict):
                continue
            for field in (
                "path",
                "hash",
                "origin_node_id",
                "origin_attempt_id",
                "node_id",
                "attempt_id",
            ):
                value = ref.get(field)
                if isinstance(value, str) and value:
                    forbidden.add(value)
            if ref.get("role") == "prd_candidate":
                forbidden.update(
                    value
                    for value in ref.values()
                    if isinstance(value, str) and value
                )
        return forbidden

    def _validate_product_planning_submission(
        self, run_id: str, result: dict[str, Any]
    ) -> None:
        """Keep Candidate identities out of Plan semantics and product-plan authority."""

        state = self.controller.load_state(run_id)
        candidate_values = {
            value
            for ref in state.get("artifact_refs", {}).values()
            if isinstance(ref, dict) and ref.get("role") == "prd_candidate"
            for value in ref.values()
            if isinstance(value, str) and value and value != "prd_candidate"
        }

        def strings(value: Any):
            if isinstance(value, str):
                yield value
            elif isinstance(value, list):
                for item in value:
                    yield from strings(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    yield str(key)
                    yield from strings(item)

        authored = {
            "semantic_output": result.get("semantic_output"),
            "artifact_refs": result.get("artifact_refs"),
        }
        if any(
            forbidden in authored_string
            for authored_string in strings(authored)
            for forbidden in candidate_values
        ):
            raise TransitionRejected(
                "Product Plan cannot depend on current Candidate provenance"
            )

        plan_refs = [
            ref
            for ref in result.get("artifact_refs", [])
            if isinstance(ref, dict) and ref.get("role") == "product_plan"
        ]
        for plan_ref in plan_refs:
            conflicts = [
                ref
                for ref in state.get("artifact_refs", {}).values()
                if isinstance(ref, dict)
                and ref.get("path") == plan_ref.get("path")
                and ref.get("hash") == plan_ref.get("hash")
                and ref.get("role") != "product_plan"
            ]
            if conflicts:
                raise TransitionRejected(
                    "Product Plan artifact identity conflicts with committed non-Plan authority"
                )

        if isinstance(state.get("scope_reconciliation"), dict):
            if len(plan_refs) != 1:
                raise TransitionRejected(
                    "reconciliation requires one exact new Product Plan artifact"
                )
            source = self.controller._current_candidate_artifact(state)
            metadata_paths = list(source.path.glob("*.metadata.json"))
            if len(metadata_paths) != 1:
                raise TransitionRejected(
                    "reconciled source Candidate metadata is ambiguous"
                )
            old_plan = read_json(metadata_paths[0]).get("product_plan_ref", {})
            if plan_refs[0].get("hash") == old_plan.get("hash"):
                raise TransitionRejected(
                    "reconciliation requires new Product Plan bytes, not a version-only alias"
                )

    def _validate_authoritative_delivery_contracts(
        self, run_id: str, result: dict[str, Any]
    ) -> None:
        metadata = result.get("semantic_output", {}).get("metadata")
        if not isinstance(metadata, dict):
            raise TransitionRejected("Agent PRD metadata is required")
        state = self.controller.load_state(run_id)
        if result.get("node_id") == "prd.generate":
            dispatch = self.controller._matching_dispatch(state, result)
            contract = dispatch.get("contract") if isinstance(dispatch, dict) else None
            expected_context = self._prd_generation_context(
                run_id, state, result.get("input_refs", [])
            )
            if (
                not isinstance(contract, dict)
                or contract.get("prd_generation_context") != expected_context
            ):
                raise TransitionRejected(
                    "PRD generation dispatch authority differs from Controller recomputation"
                )
            authority = expected_context["metadata_authority"]
            list_ref_fields = {"decision_refs", "evidence_refs"}
            single_ref_fields = {
                "roadmap_snapshot_ref",
                "product_plan_ref",
                "slice_ref",
                "knowledge_snapshot_ref",
            }
            for field, expected in authority.items():
                actual = metadata.get(field)
                if field in list_ref_fields and isinstance(actual, list):
                    actual = [self._exact_metadata_ref(item) for item in actual]
                elif field in single_ref_fields and isinstance(actual, dict):
                    actual = self._exact_metadata_ref(actual)
                if actual != expected:
                    raise TransitionRejected(
                        f"Agent PRD metadata {field} differs from exact dispatch authority"
                    )
        elif result.get("node_id") == "prd.optimize":
            expected_traceability = self.controller.prd_optimize_context(
                run_id, state
            )["metadata_authority"]["spec_traceability"]
            if metadata.get("spec_traceability") != expected_traceability:
                raise TransitionRejected(
                    "Agent PRD metadata spec_traceability differs from exact dispatch authority"
                )
        slice_ref = metadata.get("slice_ref")
        try:
            self.controller._validate_single_artifact_ref(slice_ref)
            planning_result = read_json(
                self.controller.project_root / slice_ref["path"]
            )
            expected_active_scope = derive_active_scope_ref(
                planning_result,
                metadata.get("product_plan_ref"),
                metadata.get("prd_id"),
            )
            expected_traceability = derive_spec_traceability(
                self._delivery_upstream_pairs(metadata, state, result),
                state.get("artifact_refs", {}),
            )
            validate_candidate_delivery_contract(
                metadata,
                expected_active_scope=expected_active_scope,
                expected_traceability=expected_traceability,
                forbidden_runtime_values=self._runtime_forbidden_values(run_id, state),
            )
        except (DeliveryContractError, KeyError, TypeError, ValueError) as error:
            raise TransitionRejected(f"Agent PRD delivery contract invalid: {error}") from error

    def _validate_reconciled_generate_submission(
        self, run_id: str, metadata: dict[str, Any]
    ) -> None:
        state = self.controller.load_state(run_id)
        if not isinstance(state.get("scope_reconciliation"), dict):
            return
        context = self.controller.reconciliation_generation_context(run_id, state)
        source = self.controller._current_candidate_artifact(state)
        metadata_paths = list(source.path.glob("*.metadata.json"))
        if len(metadata_paths) != 1:
            raise TransitionRejected("reconciled source Candidate metadata is ambiguous")
        source_metadata = read_json(metadata_paths[0])
        if (
            metadata.get("prd_id") != context["prd_id"]
            or metadata.get("version") != context["next_version"]
            or metadata.get("supersedes") != context["source_candidate_ref"]
        ):
            raise TransitionRejected(
                "reconciled prd.generate must use the stable prd_id, exact next version, "
                "and exact supersedes Candidate"
            )
        if (
            metadata.get("product_plan_ref", {}).get("hash")
            == source_metadata.get("product_plan_ref", {}).get("hash")
            or metadata.get("active_scope_ref", {}).get("scope_hash")
            == source_metadata.get("active_scope_ref", {}).get("scope_hash")
        ):
            raise TransitionRejected(
                "reconciled prd.generate must bind the new Product Plan and material active scope"
            )

    def _optimize_authority_and_scope(
        self,
        run_id: str,
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        state = self.controller.load_state(run_id)
        context = self.controller.prd_optimize_context(run_id, state)
        source = self.controller._current_candidate_artifact(state)
        source_metadata_paths = list(source.path.glob("*.metadata.json"))
        if len(source_metadata_paths) != 1:
            raise TransitionRejected("current Candidate metadata identity is ambiguous")
        source_metadata = read_json(source_metadata_paths[0])
        output = result["semantic_output"]
        source_ref = context["source_candidate_ref"]
        if output.get("source_candidate_ref") != source_ref:
            raise TransitionRejected("PRD Optimize source Candidate is stale")
        if output.get("candidate_ref") != {
            "prd_id": source.prd_id,
            "version": context["next_version"],
        }:
            raise TransitionRejected("PRD Optimize Candidate declaration conflicts with next version")
        if (
            metadata.get("prd_id") != source_metadata.get("prd_id")
            or metadata.get("status") != "CANDIDATE"
            or metadata.get("delivery_intent") != source_metadata.get("delivery_intent")
            or metadata.get("version") != context["next_version"]
            or metadata.get("supersedes") != source_ref
        ):
            raise TransitionRejected("PRD Optimize identity/version metadata differs from authority")
        stable_fields = (
            "decision_refs",
            "roadmap_snapshot_ref",
            "product_plan_ref",
            "slice_ref",
            "knowledge_snapshot_ref",
            "evidence_refs",
            "active_scope_ref",
            "document_experience",
        )
        if any(metadata.get(field) != source_metadata.get(field) for field in stable_fields):
            raise TransitionRejected("PRD Optimize cannot rewrite exact upstream authority")
        try:
            planning_result = read_json(
                self.controller.project_root / metadata["slice_ref"]["path"]
            )
            authoritative_projection, _ = active_scope_projection_from_planning_result(
                planning_result, metadata["prd_id"]
            )
            proposed_projection = output.get("proposed_scope_projection")
            if not isinstance(proposed_projection, dict):
                raise TransitionRejected(
                    "AMBIGUOUS_SCOPE_CHANGE: proposed_scope_projection is missing; "
                    "the current Owner must choose whether to retain the Slice or return to Product Planning"
                )
            proposed_projection = canonical_active_scope_projection(
                proposed_projection, require_closed=True
            )
        except DeliveryContractError as error:
            raise TransitionRejected(
                f"AMBIGUOUS_SCOPE_CHANGE: {error}; the current Owner must choose the route"
            ) from error
        return (
            context,
            source,
            source_metadata,
            source_ref,
            authoritative_projection,
            proposed_projection,
        )

    @staticmethod
    def _scope_delta(
        authoritative_projection: dict[str, Any], proposed_projection: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return [
            {
                "field": field,
                "planned": authoritative_projection[field],
                "proposed": proposed_projection[field],
            }
            for field in authoritative_projection
            if authoritative_projection[field] != proposed_projection[field]
        ]

    def _validate_optimize_submission(
        self,
        run_id: str,
        result: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, bytes]:
        (
            context,
            source,
            source_metadata,
            source_ref,
            authoritative_projection,
            proposed_projection,
        ) = self._optimize_authority_and_scope(run_id, result, metadata)
        output = result["semantic_output"]
        if proposed_projection != authoritative_projection:
            delta = self._scope_delta(authoritative_projection, proposed_projection)
            raise TransitionRejected(
                "PLAN_RECONCILE_REQUIRED: proposed scope differs from the exact Product "
                f"Planning Slice at {delta}; return to product.planning before creating a Candidate"
            )
        change_log = metadata.get("change_log")
        accepted_ids = [
            item["finding_id"] for item in context["accepted_dispositions"]
        ]
        if not isinstance(change_log, dict):
            raise TransitionRejected("metadata.change_log must be an object")
        allowed_change_log_fields = {
            "source_candidate_ref",
            "repaired_finding_ids",
            "unadopted_dispositions",
            "material_delta",
            "rereview_scope",
        }
        unknown_change_log_fields = sorted(set(change_log) - allowed_change_log_fields)
        if unknown_change_log_fields:
            raise TransitionRejected(
                "metadata.change_log contains unknown field "
                f"{unknown_change_log_fields[0]}"
            )
        if change_log.get("source_candidate_ref") != source_ref:
            raise TransitionRejected(
                "metadata.change_log.source_candidate_ref must equal "
                "optimize_context.source_candidate_ref"
            )
        if change_log.get("repaired_finding_ids") != accepted_ids:
            raise TransitionRejected(
                "metadata.change_log.repaired_finding_ids must equal every accepted "
                "disposition Finding ID in optimize_context order"
            )
        if change_log.get("unadopted_dispositions") != context["unadopted_dispositions"]:
            raise TransitionRejected(
                "metadata.change_log.unadopted_dispositions must copy "
                "optimize_context.unadopted_dispositions exactly"
            )
        for field in ("material_delta", "rereview_scope"):
            value = change_log.get(field)
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(item, str) or not item.strip() for item in value)
            ):
                raise TransitionRejected(
                    f"metadata.change_log.{field} must be a non-empty list of non-empty strings"
                )
        markdown = output["document_markdown"]
        if markdown == source.document_path.read_text(encoding="utf-8"):
            raise TransitionRejected("PRD Optimize did not produce a material Candidate change")
        template_mapping = output.get("template_mapping")
        visible_change_log_heading = (
            template_mapping.get("document_changelog", "版本与变更")
            if isinstance(template_mapping, dict)
            else "版本与变更"
        )
        visible_change_log = markdown_h2_section(
            markdown, visible_change_log_heading
        )
        if visible_change_log is None:
            raise TransitionRejected(
                "PRD Optimize template_mapping.document_changelog must bind an existing H2 section"
            )
        if (
            metadata["version"] not in visible_change_log
            or len(visible_change_log.strip()) <= len(metadata["version"]) + 8
        ):
            raise TransitionRejected(
                "PRD Optimize visible changelog must name the new version and explain its delta"
            )
        evals = metadata.get("evals", {})
        source_evals = source_metadata.get("evals", {})
        if (
            source_evals.get("applicability") == "REQUIRED"
            and evals.get("applicability") != "REQUIRED"
        ):
            raise TransitionRejected("PRD Optimize cannot downgrade REQUIRED Evals applicability")
        if evals.get("fulfillment") == "REVIEWED":
            raise TransitionRejected(
                "PRD Optimize cannot self-claim REVIEWED Evals; the optimized Candidate must enter independent Evals review"
            )
        if evals.get("applicability") == "REQUIRED" and (
            evals.get("fulfillment") != "REVIEW_PENDING"
            or evals.get("execution_status") != "NOT_RUN"
            or "pack_ref" in evals
            or "review_ref" in evals
        ):
            raise TransitionRejected(
                "optimized REQUIRED Evals must be REVIEW_PENDING/NOT_RUN without stale active Pack or review refs"
            )
        assets: dict[str, bytes] = {}
        assets_root = source.path / "assets"
        if assets_root.is_dir():
            for path in sorted(assets_root.rglob("*")):
                if path.is_symlink():
                    raise TransitionRejected("current Candidate assets cannot contain symlinks")
                if path.is_file():
                    assets[path.relative_to(assets_root).as_posix()] = path.read_bytes()
        return assets

    def _prepare_prd_candidate(
        self,
        run_id: str,
        result: dict[str, Any],
        *,
        failpoint=None,
    ) -> dict[str, Any]:
        """Validate Agent PRD semantics, then archive bytes without generating content."""

        self.controller.validate_agent_result(run_id, result)
        self._validate_authoritative_delivery_contracts(run_id, result)
        if result["node_id"] == "prd.generate":
            self._validate_reconciled_generate_submission(
                run_id, result["semantic_output"]["metadata"]
            )
        try:
            selection = TemplateRegistry(self._template_root()).resolve(
                self.controller.project_root
            )
            run_pin = self.controller.load_state(run_id).get("template_profile_pin", {})
            expected_pin = self.controller._template_selection_payload(selection)
            if any(
                run_pin.get(field) != expected_pin.get(field)
                for field in (
                    "profile_id",
                    "version",
                    "sha256",
                    "relative_path",
                    "source_kind",
                    "selection_source",
                    "fallback_reason",
                    "requested_profile_id",
                    "requested_version",
                    "output_contract_sha256",
                    "output_contract_version",
                    "output_contract_relative_path",
                )
            ):
                raise PRDContractError(
                    "Run Template pin differs from the exact current selection; migrate explicitly"
                )
            assembled = assemble_prd(
                result,
                selection,
            )
        except (PRDContractError, ValueError) as error:
            raise TransitionRejected(f"Agent PRD contract invalid: {error}") from error
        exact_inputs = result["input_hashes"]
        metadata = assembled.metadata
        assets = (
            self._validate_optimize_submission(run_id, result, metadata)
            if result["node_id"] == "prd.optimize"
            else {}
        )
        upstream_refs = [
            *metadata["decision_refs"],
            metadata["roadmap_snapshot_ref"],
            metadata["product_plan_ref"],
            metadata["slice_ref"],
            metadata["knowledge_snapshot_ref"],
            *metadata["evidence_refs"],
        ]
        for ref in upstream_refs:
            if exact_inputs.get(ref["path"]) != ref["hash"]:
                raise TransitionRejected(
                    f"PRD upstream ref is absent from exact dispatch inputs: {ref['path']}"
                )
        try:
            archived = archive_prd_candidate(
                self.controller.project_root,
                assembled,
                assets=assets,
                failpoint=failpoint,
            )
        except ImmutableArtifactError as error:
            raise TransitionRejected(f"PRD archive contract invalid: {error}") from error
        prepared = deepcopy(result)
        prepared["artifact_refs"] = [
            item for item in prepared.get("artifact_refs", [])
            if item.get("role") != "prd_candidate"
        ]
        prepared["artifact_refs"].append(
            {
                "role": "prd_candidate",
                "path": archived.document_path.relative_to(
                    self.controller.project_root
                ).as_posix(),
                "hash": archived.document_hash,
                "version": archived.version,
                "tree_hash": archived.tree_hash,
                "artifact_path": archived.path.relative_to(
                    self.controller.project_root
                ).as_posix(),
                "review_path": archived.review_path.relative_to(
                    self.controller.project_root
                ).as_posix(),
                "review_hash": sha256_file(archived.review_path),
            }
        )
        return prepared

    def _completed_optimize_retry(
        self, run_id: str, state: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Return the already-committed outcome for one exact public retry."""

        attempt_id = result.get("attempt_id")
        if (
            result.get("node_id") != "prd.optimize"
            or attempt_id not in state.get("consumed_attempts", [])
            or state.get("last_completed_node") != "prd.optimize"
            or state.get("current_node") != "review.parallel"
        ):
            return None
        result_path = self.controller._result_path(run_id, attempt_id)
        if not result_path.is_file():
            raise StateConflict("consumed PRD Optimize attempt has no persisted result")
        persisted = read_json(result_path)
        caller_refs = [
            item for item in result.get("artifact_refs", [])
            if item.get("role") != "prd_candidate"
        ]
        persisted_without_candidate = {
            **persisted,
            "artifact_refs": [
                item for item in persisted.get("artifact_refs", [])
                if item.get("role") != "prd_candidate"
            ],
        }
        if {**result, "artifact_refs": caller_refs} != persisted_without_candidate:
            raise StateConflict("PRD Optimize retry differs from the committed attempt")
        candidate_refs = [
            item for item in persisted.get("artifact_refs", [])
            if item.get("role") == "prd_candidate"
        ]
        current = state.get("current_candidate_ref") or {}
        if (
            len(candidate_refs) != 1
            or any(
                candidate_refs[0].get(key) != current.get(key)
                for key in ("path", "hash", "version", "tree_hash")
            )
        ):
            raise StateConflict("committed PRD Optimize retry is not the current Candidate")
        dispatch = self.dispatch_current(run_id)
        return {
            "status": "ADVANCED",
            "run_id": run_id,
            "state": self.controller.load_state(run_id),
            "dispatch": dispatch,
        }

    def submit_and_advance(
        self,
        run_id: str,
        result: dict[str, Any],
        *,
        requested_node: str | None,
        failpoint=None,
    ) -> dict[str, Any]:
        """Consume one Agent result and return the next installed Host dispatch."""

        with self.controller.mutation_lock(run_id):
            state = self.controller.authoritative_read_barrier(run_id)
            if requested_node is None and state["current_node"] != "product.decision":
                allowed = self.controller.edges.get(state["current_node"], [])
                if len(allowed) == 1:
                    requested_node = allowed[0]
            reconciliation = state.get("scope_reconciliation")
            if (
                isinstance(reconciliation, dict)
                and reconciliation.get("attempt_id") == result.get("attempt_id")
            ):
                submitted_hash = sha256_bytes(canonical_json_bytes(result))
                if reconciliation.get("submission_hash") != submitted_hash:
                    raise StateConflict(
                        f"scope reconciliation attempt identity conflict: {result.get('attempt_id')}"
                    )
                if requested_node != "product.planning":
                    raise StateConflict(
                        "scope reconciliation retry must retain product.planning route"
                    )
                return {
                    "status": "PLAN_RECONCILE_REQUIRED",
                    "run_id": run_id,
                    "state": state,
                    "route": {
                        **reconciliation["route"],
                        "exact_delta": reconciliation["exact_delta"],
                        "agent_recommendation": (
                            "Reconcile the exact Slice in Product Planning; keep the old "
                            "Candidate current until the new Plan is Ready."
                        ),
                    },
                }
            completed_retry = self._completed_optimize_retry(run_id, state, result)
            if completed_retry is not None:
                return completed_retry
            if state["status"] != "ACTIVE":
                raise TransitionRejected(
                    f"Run must be ACTIVE to submit, got {state['status']}"
                )
            if result.get("producer", {}).get("kind") != "HOST_AGENT":
                raise TransitionRejected(
                    "public Host submit accepts HOST_AGENT results only"
                )
            if state["current_node"] not in {"prd.generate", "prd.optimize"}:
                attempt_id = result.get("attempt_id")
                if (
                    isinstance(attempt_id, str)
                    and attempt_id
                    and "/" not in attempt_id
                    and ".." not in attempt_id
                ):
                    result_path = self.controller._result_path(run_id, attempt_id)
                    if result_path.is_file():
                        if read_json(result_path) != result:
                            raise StateConflict(
                                f"attempt identity conflict: {attempt_id}"
                            )
                        raise StateConflict(
                            f"attempt already exists: {attempt_id}"
                        )
            self.controller.preflight_agent_submission(
                run_id, result, requested_node
            )
            if state["current_node"] == "product.planning":
                self._validate_product_planning_submission(run_id, result)
            if state["current_node"] == "prd.optimize" and requested_node == "product.planning":
                metadata = result.get("semantic_output", {}).get("metadata")
                if not isinstance(metadata, dict):
                    raise TransitionRejected("Agent PRD metadata is required")
                self._validate_authoritative_delivery_contracts(run_id, result)
                (
                    _,
                    _,
                    _,
                    source_ref,
                    authoritative_projection,
                    proposed_projection,
                ) = self._optimize_authority_and_scope(run_id, result, metadata)
                exact_delta = self._scope_delta(
                    authoritative_projection, proposed_projection
                )
                if not exact_delta:
                    raise TransitionRejected(
                        "product.planning return requires a material canonical scope delta"
                    )
                submitted_hash = sha256_bytes(canonical_json_bytes(result))
                routed_state = self.controller.return_to_product_planning(
                    run_id,
                    attempt_id=result["attempt_id"],
                    submission_hash=submitted_hash,
                    source_candidate_ref=source_ref,
                    exact_delta=exact_delta,
                )
                return {
                    "status": "PLAN_RECONCILE_REQUIRED",
                    "run_id": run_id,
                    "state": routed_state,
                    "route": {
                        "from_node": "prd.optimize",
                        "to_node": "product.planning",
                        "exact_delta": exact_delta,
                        "agent_recommendation": (
                            "Reconcile the exact Slice in Product Planning; keep the old "
                            "Candidate current until the new Plan is Ready."
                        ),
                    },
                }
            if state["current_node"] in {"prd.generate", "prd.optimize"}:
                result = self._prepare_prd_candidate(
                    run_id, result, failpoint=failpoint
                )
            result_path = self.controller._result_path(run_id, result["attempt_id"])
            if result_path.is_file():
                if result["node_id"] not in {"prd.generate", "prd.optimize"}:
                    raise StateConflict(f"attempt already exists: {result['attempt_id']}")
                if read_json(result_path) != result:
                    raise StateConflict(
                        f"attempt identity conflict: {result['attempt_id']}"
                    )
            else:
                self.controller.submit_result(run_id, result, failpoint=failpoint)
            state = self.controller.load_state(run_id)
            if state["current_node"] == "product.decision":
                decision_id = f"decision-{run_id.removeprefix('run-')}"
                proposal = persist_decision_proposal(
                    self.controller.project_root, decision_id, run_id, result
                )
                return {
                    "status": "OWNER_CHOICE_REQUIRED",
                    "run_id": run_id,
                    "state": state,
                    "proposal": proposal,
                }
            updated = self.controller.transition(
                run_id,
                {
                    "requested_node": requested_node,
                    "attempt_id": result["attempt_id"],
                    "expected_state_version": state["state_version"],
                },
                failpoint=failpoint,
            )
            if updated["current_node"] == "route.select":
                dispatch = self._complete_route_select(
                    run_id, result["semantic_output"]["route_destination"]
                )
            else:
                dispatch = self.dispatch_current(run_id)
            if dispatch.get("status") in {
                "COMPLETED",
                "ADVANCED",
                "NOT_READY",
                "EVALS_FULFILLMENT_REQUIRED",
            }:
                return dispatch
            return {
                "status": "ADVANCED",
                "run_id": run_id,
                "state": self.controller.load_state(run_id),
                "dispatch": dispatch,
            }

    def apply_owner_choice(self, run_id: str, command: dict[str, Any]) -> dict[str, Any]:
        with self.controller.mutation_lock(run_id):
            self.controller.authoritative_read_barrier(run_id)
            state = self.controller.apply_owner_choice(run_id, command)
            dispatch = None
            if state["status"] == "ACTIVE":
                contract = self.registry.contracts[state["current_node"]]
                if contract["producer_kind"] == "HOST_AGENT":
                    dispatch = self.dispatch_current(run_id)
                    state = self.controller.load_state(run_id)
            return {
                "status": "OWNER_CHOICE_APPLIED",
                "run_id": run_id,
                "state": state,
                "dispatch": dispatch,
            }

    def handle_entry(self, entry: str) -> dict[str, Any]:
        result = self.engine.handle(entry)
        if result.get("status") == "ACTIVATED":
            dispatch = self._complete_ingest(result["run_id"])
            result["state"] = self.controller.load_state(result["run_id"])
            result["dispatch"] = dispatch
        return result
