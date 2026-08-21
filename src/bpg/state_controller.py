"""Deterministic formal-state writer for local Better Product Graph Runs."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .contracts import PolicyViolation, validate_node_result_producer
from .bugs import validate_bug_assessment
from .discovery_contract import build_problem_ready_output, validate_problem_ready
from .evals_authority import EvalsAuthorityError, validate_reviewed_evals
from .node_registry import NodeRegistry
from .node_validation import NodeValidationError, validate_node_output
from .product_memory import record_owner_decision
from .planning_contract import validate_plan
from .locking import exclusive_file_lock
from .receipts import (
    READY_RULES_VERSION,
    ReceiptError,
    build_receipt_payload,
    controller_subject_ref,
    evaluate_receipt_subjects,
    normalize_subject_refs,
    resolve_file_ref,
)
from .review_contract import (
    ReviewContractError,
    validate_review_aggregate_artifacts,
)
from .schema_runtime import SchemaRuntime, SchemaValidationError
from .storage import (
    IntegrityError,
    append_event,
    assert_managed_path,
    atomic_write_bytes,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_event_chain,
)
from .templates import TemplateContractError, TemplateRegistry, TemplateSelection


class StateConflict(RuntimeError):
    """Expected state version does not equal the current version."""


class TransitionRejected(RuntimeError):
    """A requested transition did not satisfy deterministic contracts."""


def serialized_run_mutation(method):
    """Serialize a StateController mutation by its first run_id argument."""

    @wraps(method)
    def wrapped(self, run_id: str, *args, **kwargs):
        with self.mutation_lock(run_id):
            return method(self, run_id, *args, **kwargs)

    return wrapped


FORBIDDEN_REQUEST_FIELDS = frozenset(
    {"gate_passed", "validator_passed", "all_reviewers_passed", "reviewers_approved"}
)
ACCEPTED_CURRENT_PRD_REPAIR = "ACCEPTED_CURRENT_PRD_REPAIR"

STATE_COMMIT_EVENT_VERSION_FIELDS = {
    "RUN_CREATED": "state_version",
    "RUN_PAUSED": "state_version",
    "RUN_RESUMED": "state_version",
    "OWNER_CHOICE_RECORDED": "state_version",
    "WAIT_TRIGGER_CONSUMED": "state_version",
    "INTERVIEW_SKIPPED": "state_version",
    "INTERVIEW_RESUMED": "state_version",
    "NODE_DISPATCH_PLANNED": "state_version",
    "NODE_CALL_STARTED": "state_version",
    "NODE_CALL_OUTCOME_UNKNOWN": "state_version",
    "CANDIDATE_BOUND": "state_version",
    "READY_EVIDENCE_BOUND": "state_version",
    "REVIEW_FINALIZE_COMMITTED": "state_version",
    "CONTROLLER_RECEIPT_ISSUED": "state_version",
    "FANOUT_PLAN_REGISTERED": "state_version",
    "PRD_RELEASE_COMMITTED": "state_version",
    "HANDOFF_LOCAL_COMMITTED": "state_version",
    "NODE_TRANSITION_COMMITTED": "after_state_version",
    "PLAN_RECONCILE_REQUIRED": "after_state_version",
}


class StateController:
    def __init__(self, project_root: Path, graph_manifest: Path, *, skill_root: Path | None = None):
        self.project_root = project_root.resolve()
        self.graph_path = graph_manifest.resolve()
        self.graph = read_json(self.graph_path)
        self.skill_root = (skill_root or self.graph_path.parent.parent).resolve()
        self.registry = NodeRegistry(self.skill_root, self.graph_path)
        self.schemas = SchemaRuntime(self.skill_root)
        self.nodes = {node["id"]: node for node in self.graph["nodes"]}
        self.edges: dict[str, list[str]] = {}
        for edge in self.graph["edges"]:
            self.edges.setdefault(edge["from"], []).append(edge["to"])

    def run_path(self, run_id: str) -> Path:
        if not run_id or "/" in run_id or ".." in run_id:
            raise ValueError("run_id must be a stable path-safe identifier")
        return assert_managed_path(
            self.project_root,
            self.project_root / ".better-product-graph" / "runs" / run_id,
        )

    def _template_selection(self) -> dict[str, Any]:
        selection = self._template_registry().resolve_for_runtime(self.project_root)
        return self._template_selection_payload(selection)

    def _template_registry(self) -> TemplateRegistry:
        source = self.skill_root / "templates"
        installed = self.skill_root / "references" / "templates"
        return TemplateRegistry(source if source.is_dir() else installed)

    def _run_created_template_pin_is_durable(
        self, run_id: str, selection: TemplateSelection
    ) -> bool:
        """Return true only for an exact recoverable run-created commitment to this pin."""

        journal_path = self._transaction_path(run_id, "run-created")
        if journal_path.is_symlink() or not journal_path.is_file():
            return False
        journal = read_json(journal_path)
        after_state = journal.get("after_state")
        event = journal.get("event")
        if not isinstance(after_state, dict) or not isinstance(event, dict):
            return False
        expected_pin = self._template_selection_payload(selection)
        return (
            journal.get("schema_version") == "state-transaction.v1"
            and journal.get("transaction_id") == "run-created"
            and journal.get("run_id") == run_id
            and journal.get("status") in {"PREPARED", "COMMITTED"}
            and event.get("event_type") == "RUN_CREATED"
            and event.get("run_id") == run_id
            and after_state.get("run_id") == run_id
            and after_state.get("template_profile_pin") == expected_pin
            and self._state_hash(after_state) == journal.get("after_state_hash")
            and event.get("after_state_hash") == journal.get("after_state_hash")
            and event.get("before_state_hash") == journal.get("before_state_hash")
        )

    @staticmethod
    def _template_selection_payload(selection: TemplateSelection) -> dict[str, Any]:
        return {
            "profile_id": selection.profile_id,
            "version": selection.version,
            "status": selection.status,
            "path": str(selection.path),
            "sha256": selection.sha256,
            "relative_path": selection.relative_path,
            "source_kind": selection.origin,
            "selection_source": selection.selection_source,
            "fallback_reason": selection.fallback_reason,
            "requested_profile_id": selection.requested_profile_id,
            "requested_version": selection.requested_version,
            "output_contract_path": str(selection.output_contract_path),
            "output_contract_sha256": selection.output_contract_sha256,
            "output_contract_version": selection.output_contract_version,
            "output_contract_relative_path": selection.output_contract_relative_path,
        }

    def _template_selection_from_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        source = self.skill_root / "templates"
        installed = self.skill_root / "references" / "templates"
        registry = TemplateRegistry(source if source.is_dir() else installed)
        try:
            selection = registry.selection_from_metadata(
                self.project_root, metadata.get("template_profile")
            )
        except TemplateContractError as error:
            raise TransitionRejected(f"Archived Template selection invalid: {error}") from error
        return self._template_selection_payload(selection)

    def _template_selection_from_candidate(
        self, candidate_ref: dict[str, Any]
    ) -> dict[str, Any]:
        candidate_root = (self.project_root / candidate_ref.get("artifact_path", "")).resolve()
        metadata_paths = list(candidate_root.glob("*.metadata.json"))
        if len(metadata_paths) != 1 or metadata_paths[0].is_symlink():
            raise TransitionRejected("Candidate Template selection metadata is not self-contained")
        return self._template_selection_from_metadata(read_json(metadata_paths[0]))

    def _template_selection_for_receipt(
        self,
        kind: str,
        candidate_ref: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        candidate_root = (self.project_root / candidate_ref.get("artifact_path", "")).resolve()
        metadata_paths = list(candidate_root.glob("*.metadata.json"))
        if kind in {"document_experience", "mechanical_contracts"} and len(metadata_paths) == 1:
            return self._template_selection_from_candidate(candidate_ref)
        pin = state.get("template_profile_pin")
        if isinstance(pin, dict) and pin:
            return pin
        return self._template_selection()

    @contextmanager
    def mutation_lock(self, run_id: str) -> Iterator[None]:
        if not run_id or "/" in run_id or ".." in run_id:
            raise ValueError("run_id must be a stable path-safe identifier")
        path = assert_managed_path(
            self.project_root,
            self.project_root / ".better-product-graph" / "locks" / f"{run_id}.lock",
        )
        with exclusive_file_lock(path):
            yield

    def _state_path(self, run_id: str) -> Path:
        return self.run_path(run_id) / "state.json"

    def _events_path(self, run_id: str) -> Path:
        return self.run_path(run_id) / "events.jsonl"

    def _transaction_path(self, run_id: str, transaction_id: str) -> Path:
        safe = transaction_id.replace(":", "--")
        if not safe or "/" in safe or ".." in safe:
            raise ValueError("transaction_id must be path-safe")
        return self.run_path(run_id) / "transactions" / f"{safe}.json"

    @staticmethod
    def _state_hash(state: dict[str, Any] | None) -> str | None:
        return sha256_bytes(canonical_json_bytes(state)) if state is not None else None

    def _state_commit_event(
        self,
        event: dict[str, Any],
        before: dict[str, Any] | None,
        after: dict[str, Any],
    ) -> dict[str, Any]:
        """Attach exact Controller-derived state commitments to one mutation event."""

        return {
            **event,
            "before_state_hash": self._state_hash(before),
            "after_state_hash": self._state_hash(after),
        }

    @staticmethod
    def _dispatch_authority_hash(state: dict[str, Any]) -> str:
        """Bind a dispatch to all mutable facts that can revoke its authority."""

        authority = {
            "run_id": state["run_id"],
            "state_version": state["state_version"],
            "status": state["status"],
            "current_node": state["current_node"],
            "artifact_refs": state.get("artifact_refs", {}),
            "current_candidate_ref": state.get("current_candidate_ref"),
            "interaction_policy": state.get("interaction_policy"),
            "waiting": state.get("waiting"),
            "release_ref": state.get("release_ref"),
        }
        return sha256_bytes(canonical_json_bytes(authority))

    def _commit_state_event(
        self,
        run_id: str,
        before: dict[str, Any] | None,
        after: dict[str, Any],
        event: dict[str, Any],
        *,
        transaction_id: str,
        failpoint: Callable[[str], None] | None = None,
        after_event_phase: str = "after_state_event",
    ) -> dict[str, Any]:
        """Write-ahead one exact state+event mutation for generic crash recovery."""

        event = self._state_commit_event(
            {"event_id": f"state-transaction:{run_id}:{transaction_id}", **event},
            before,
            after,
        )
        journal_path = self._transaction_path(run_id, transaction_id)
        expected = {
            "schema_version": "state-transaction.v1",
            "transaction_id": transaction_id,
            "run_id": run_id,
            "status": "PREPARED",
            "before_state_hash": self._state_hash(before),
            "after_state_hash": self._state_hash(after),
            "after_state": after,
            "event": event,
        }
        if journal_path.exists():
            journal = read_json(journal_path)
            comparable = {**journal, "status": "PREPARED"}
            if comparable != expected:
                raise StateConflict(f"state transaction identity conflict: {transaction_id}")
        else:
            atomic_write_json(journal_path, expected)
        append_event(self._events_path(run_id), event)
        if failpoint is not None:
            failpoint(after_event_phase)
        atomic_write_json(self._state_path(run_id), after)
        atomic_write_json(journal_path, {**expected, "status": "COMMITTED"})
        return after

    @serialized_run_mutation
    def recover_transactions(self, run_id: str) -> int:
        recovered = 0
        for path in sorted((self.run_path(run_id) / "transactions").glob("*.json")):
            journal = read_json(path)
            after_state = journal.get("after_state")
            event = journal.get("event")
            if (
                not isinstance(after_state, dict)
                or not isinstance(event, dict)
                or self._state_hash(after_state) != journal.get("after_state_hash")
                or event.get("before_state_hash") != journal.get("before_state_hash")
                or event.get("after_state_hash") != journal.get("after_state_hash")
            ):
                raise StateConflict(f"state transaction commitment invalid: {path.name}")
            if journal.get("status") == "COMMITTED":
                continue
            if journal.get("status") != "PREPARED" or journal.get("run_id") != run_id:
                raise StateConflict(f"invalid state transaction journal: {path.name}")
            state_path = self._state_path(run_id)
            current = read_json(state_path) if state_path.exists() else None
            current_hash = self._state_hash(current)
            if current_hash not in {
                journal.get("before_state_hash"),
                journal.get("after_state_hash"),
            }:
                raise StateConflict(f"state transaction cannot reconcile: {path.name}")
            release_publish = journal.get("release_publish")
            if isinstance(release_publish, dict):
                self._validate_release_transaction(journal)
            candidate_publish = journal.get("candidate_publish")
            if isinstance(candidate_publish, dict):
                self._validate_candidate_finalize_transaction(journal)
            if current_hash == journal.get("before_state_hash"):
                append_event(self._events_path(run_id), journal["event"])
                atomic_write_json(state_path, after_state)
                recovered += 1
            release_publish = journal.get("release_publish")
            if isinstance(release_publish, dict):
                self._publish_release_transaction(journal)
                if current_hash == journal.get("after_state_hash"):
                    recovered += 1
            candidate_publish = journal.get("candidate_publish")
            if isinstance(candidate_publish, dict):
                self._publish_candidate_finalize_transaction(journal)
                if current_hash == journal.get("after_state_hash"):
                    recovered += 1
            atomic_write_json(path, {**journal, "status": "COMMITTED"})
        return recovered

    def _result_path(self, run_id: str, attempt_id: str) -> Path:
        if not attempt_id or "/" in attempt_id or ".." in attempt_id:
            raise ValueError("attempt_id must be path-safe")
        return self.run_path(run_id) / "attempts" / attempt_id / "node-result.json"

    def _load_committed_result(
        self, run_id: str, state: dict[str, Any], expected_node: str
    ) -> dict[str, Any]:
        """Return the exact latest consumed result for one immediately prior Node."""

        for attempt_id in reversed(state.get("consumed_attempts", [])):
            result_path = self._result_path(run_id, attempt_id)
            receipt_path = result_path.with_name("result-receipt.json")
            if not result_path.is_file() or not receipt_path.is_file():
                raise TransitionRejected("committed upstream result or receipt is missing")
            result = read_json(result_path)
            if result.get("node_id") != expected_node:
                continue
            receipt = read_json(receipt_path)
            if (
                receipt.get("attempt_id") != attempt_id
                or receipt.get("node_id") != expected_node
                or receipt.get("result_hash") != sha256_file(result_path)
            ):
                raise TransitionRejected("committed upstream result receipt is invalid")
            return result
        raise TransitionRejected(f"no committed {expected_node} result is bound to this Run")

    @staticmethod
    def _available_artifact_hashes(state: dict[str, Any]) -> dict[str, str]:
        return {
            ref["path"]: ref["hash"]
            for ref in state.get("artifact_refs", {}).values()
            if isinstance(ref, dict)
            and isinstance(ref.get("path"), str)
            and isinstance(ref.get("hash"), str)
        }

    @staticmethod
    def _matching_dispatch(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in state["dispatch_attempts"]
                if item["attempt_id"] == result.get("attempt_id")
                and item["node_id"] == state["current_node"]
            ),
            None,
        )

    def _validate_goal_fidelity_bindings(
        self,
        result: dict[str, Any],
        contract: dict[str, Any],
    ) -> None:
        output = result["semantic_output"]
        expected_resources = {item["resource_id"]: item for item in contract["resource_refs"]}
        refs = output["goal_fidelity_refs"]
        fields = ("path", "hash", "version")
        mapping = {
            "profile_ref": "goal-fidelity-profile",
            "rubric_ref": "goal-fidelity-rubric",
            "packet_contract_ref": "goal-fidelity-packet-contract",
        }
        for field, resource_id in mapping.items():
            expected = {key: expected_resources[resource_id][key] for key in fields}
            if refs[field] != expected:
                raise TransitionRejected(f"Goal Fidelity {field} differs from exact dispatch resource")
        input_hashes = contract["input_hashes"]
        candidate_ref = output["candidate_ref"]
        if input_hashes.get(candidate_ref["path"]) != candidate_ref["hash"]:
            raise TransitionRejected("Goal Fidelity Candidate ref is not an exact dispatch input")
        for commitment in refs["commitment_refs"]:
            if input_hashes.get(commitment["path"]) != commitment["hash"]:
                raise TransitionRejected("Goal Fidelity commitment ref is not an exact dispatch input")

    def _validate_exact_dispatch_result(
        self,
        state: dict[str, Any],
        result: dict[str, Any],
        dispatch: dict[str, Any] | None = None,
    ) -> None:
        dispatch = dispatch or self._matching_dispatch(state, result)
        if dispatch is None:
            raise TransitionRejected("result has no durable dispatch plan for the current node")
        if dispatch["status"] != "DISPATCHED":
            raise TransitionRejected(f"result dispatch must be DISPATCHED, got {dispatch['status']}")
        if dispatch.get("authorized_state_version") != state["state_version"]:
            raise TransitionRejected(
                "result dispatch state version is stale for the current Run snapshot"
            )
        if dispatch.get("authority_hash") != self._dispatch_authority_hash(state):
            raise TransitionRejected("result dispatch authority is stale for the current Run state")
        contract = dispatch.get("contract")
        if not isinstance(contract, dict):
            raise TransitionRejected("result dispatch is missing its exact contract")
        if result["producer"]["kind"] != contract.get("producer_kind"):
            raise TransitionRejected("result producer differs from dispatch contract")
        if result["producer"]["kind"] != "HOST_AGENT":
            return
        current_contract = self.registry.dispatch_envelope(
            state["current_node"],
            result["attempt_id"],
            contract["input_refs"],
            contract["input_hashes"],
        )
        compatibility = self.registry.instruction_compatibility(
            state["current_node"], contract.get("instruction_hash")
        )
        if compatibility == "INCOMPATIBLE":
            raise TransitionRejected(
                "result instruction differs from the exact or declared compatible dispatch"
            )
        for field in ("instruction_ref", "input_refs", "input_hashes"):
            if result.get(field) != current_contract[field] or result.get(field) != contract.get(field):
                raise TransitionRejected(f"result {field.replace('_hash', '')} differs from exact dispatch")
        if result.get("instruction_hash") != contract.get("instruction_hash"):
            raise TransitionRejected("result instruction differs from exact dispatch")
        result_resources = result.get("resource_refs", [])
        if (
            result_resources != current_contract["resource_refs"]
            or result_resources != contract.get("resource_refs", [])
        ):
            raise TransitionRejected("result resource refs differ from exact dispatch")
        if state["current_node"] == "prd.optimize" and contract.get(
            "optimize_context"
        ) != self.prd_optimize_context(state["run_id"], state):
            raise TransitionRejected("PRD Optimize context differs from exact current repair authority")
        if (
            state["current_node"] == "prd.generate"
            and isinstance(state.get("scope_reconciliation"), dict)
            and contract.get("reconciliation_context")
            != self.reconciliation_generation_context(state["run_id"], state)
        ):
            raise TransitionRejected(
                "reconciled PRD generation context differs from exact current authority"
            )
        for relative, expected_hash in result["input_hashes"].items():
            path = (self.project_root / relative).resolve()
            try:
                path.relative_to(self.project_root)
            except ValueError as error:
                raise TransitionRejected("input ref escapes project root") from error
            if not path.is_file() or path.is_symlink() or sha256_file(path) != expected_hash:
                raise TransitionRejected(f"input ref missing or hash mismatch: {relative}")
        if state["current_node"] == "review.parallel":
            self._validate_goal_fidelity_bindings(result, contract)
        elif state["current_node"] == "problem.learning.loop":
            used = set(result["semantic_output"]["reasoning_usage"]["used_resource_ids"])
            available = {item["resource_id"] for item in contract["resource_refs"]}
            if not used.issubset(available):
                raise TransitionRejected("Agent-declared reasoning resource is not in exact dispatch")

    @serialized_run_mutation
    def create_run(
        self,
        run_id: str,
        *,
        raw_signal: str,
        run_type: str = "decision",
        source_signal_ref: dict[str, Any] | None = None,
        source_signal_id: str | None = None,
        source_occurrence_id: str | None = None,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        state_path = self._state_path(run_id)
        if state_path.exists():
            raise StateConflict(f"run already exists: {run_id}")
        run_path = self.run_path(run_id)
        raw_path = run_path / "artifacts" / "raw-signal-v1.json"
        raw_payload = {"schema_version": "raw-signal.v0alpha", "raw_text": raw_signal}
        if raw_path.exists():
            if read_json(raw_path) != raw_payload:
                raise StateConflict(f"raw signal identity conflict: {run_id}")
        if source_signal_ref is not None:
            self._validate_single_artifact_ref(source_signal_ref)
        with self._template_registry().runtime_selection_transaction(
            self.project_root,
            retain_new_pin_on_error=lambda selection: self._run_created_template_pin_is_durable(
                run_id, selection
            ),
        ) as selection:
            template_profile_pin = self._template_selection_payload(selection)
            if not raw_path.exists():
                atomic_write_json(raw_path, raw_payload)
            raw_ref = {
                "path": raw_path.relative_to(self.project_root).as_posix(),
                "hash": sha256_file(raw_path),
                "version": 1,
            }
            artifact_refs = {"raw_signal": raw_ref}
            if source_signal_ref is not None:
                artifact_refs["source_signal"] = source_signal_ref
            state = {
                "schema_version": "run-state.v1",
                "run_id": run_id,
                "run_type": run_type,
                "state_version": 1,
                "status": "ACTIVE",
                "current_node": "signal.ingest",
                "last_completed_node": None,
                "next_allowed_nodes": self.edges.get("signal.ingest", []),
                "artifact_refs": artifact_refs,
                "source_signal_id": source_signal_id,
                "source_occurrence_id": source_occurrence_id,
                "unresolved": [],
                "waiting": None,
                "pause": None,
                "interaction_policy": "ALLOW_PM_INTERVIEW",
                "dispatch_attempts": [],
                "fanout_plans": [],
                "consumed_attempts": [],
                "consumed_wait_triggers": [],
                "current_candidate_ref": None,
                "candidate_version": 0,
                "ready_receipts": [],
                "decision": None,
                "release_ref": None,
                "graph_manifest": {
                    "version": self.graph["version"],
                    "hash": sha256_file(self.graph_path),
                },
                "template_profile_pin": template_profile_pin,
            }
            return self._commit_state_event(
                run_id,
                None,
                state,
                {
                    "event_type": "RUN_CREATED",
                    "actor": "state-controller",
                    "run_id": run_id,
                    "state_version": 1,
                    "raw_signal_ref": raw_ref,
                },
                transaction_id="run-created",
                failpoint=failpoint,
            )

    def load_state(self, run_id: str) -> dict[str, Any]:
        state = read_json(self._state_path(run_id))
        try:
            self.schemas.validate("run-state.schema.json", state)
        except SchemaValidationError as error:
            from .storage import IntegrityError

            raise IntegrityError(f"run-state schema violation: {error}") from error
        return state

    def _full_state_commitment_blockers(
        self,
        state: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> list[str]:
        """Verify the complete snapshot against the append-only commitment chain."""

        blockers: list[str] = []
        previous_after: str | None = None
        found = False
        for event in events:
            if event.get("event_type") not in STATE_COMMIT_EVENT_VERSION_FIELDS:
                continue
            before_hash = event.get("before_state_hash")
            after_hash = event.get("after_state_hash")
            valid_before = before_hash is None or (
                isinstance(before_hash, str)
                and before_hash.startswith("sha256:")
                and len(before_hash) == 71
            )
            valid_after = (
                isinstance(after_hash, str)
                and after_hash.startswith("sha256:")
                and len(after_hash) == 71
            )
            if not valid_before or not valid_after:
                blockers.append(
                    f"full state commitment missing on {event.get('event_type')}"
                )
                continue
            if found and before_hash != previous_after:
                blockers.append(
                    f"full state commitment chain broke at {event.get('event_type')}"
                )
            elif not found and before_hash is not None:
                blockers.append("full state commitment chain has no creation origin")
            found = True
            previous_after = after_hash
        if not found:
            blockers.append("full state commitment authority is missing")
        elif previous_after != self._state_hash(state):
            blockers.append("full state commitment differs from current snapshot")
        return blockers

    def _event_authority_blockers(
        self,
        run_id: str,
        state: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> list[str]:
        """Compare one schema-valid snapshot with Controller event authority."""

        blockers: list[str] = []
        expected_node = "signal.ingest"
        expected_status = "ACTIVE"
        expected_state_version = 0
        attempt_events: dict[str, dict[str, Any]] = {}
        wait_trigger_events: list[dict[str, Any]] = []
        for event in events:
            event_type = event.get("event_type")
            version_field = STATE_COMMIT_EVENT_VERSION_FIELDS.get(event_type)
            if version_field is not None:
                version = event.get(version_field)
                if not isinstance(version, int) or version < expected_state_version:
                    blockers.append(
                        f"event authority has invalid {event_type} state version"
                    )
                else:
                    expected_state_version = version
            if event_type == "NODE_TRANSITION_COMMITTED":
                expected_node = event.get("to_node", expected_node)
            elif event_type == "PLAN_RECONCILE_REQUIRED":
                expected_node, expected_status = "product.planning", "ACTIVE"
            elif event_type == "OWNER_CHOICE_RECORDED":
                choice = event.get("chosen_outcome")
                route = event.get("route")
                if choice == "STOP":
                    expected_node, expected_status = "product.decision", "CLOSED"
                elif choice == "WAIT":
                    expected_node, expected_status = "product.decision", "WAITING_TRIGGER"
                elif choice == "RESEARCH":
                    expected_node, expected_status = "evidence.collect", "ACTIVE"
                elif choice in {"EXPERIMENT", "COMMIT"} and route != "ROADMAP_ONLY":
                    expected_node, expected_status = "product.planning", "ACTIVE"
                else:
                    expected_node, expected_status = "product.decision", "ROADMAP_ONLY"
            elif event_type == "REVIEW_FINALIZE_COMMITTED":
                expected_node, expected_status = "prd.ready.gate", "ACTIVE"
            elif event_type == "WAIT_TRIGGER_CONSUMED":
                expected_node, expected_status = "evidence.collect", "ACTIVE"
                consumed_ref = event.get("consumed_ref")
                if not isinstance(consumed_ref, dict):
                    blockers.append("event authority WAIT trigger binding is missing")
                else:
                    wait_trigger_events.append(consumed_ref)
            elif event_type == "PRD_RELEASE_COMMITTED":
                expected_node, expected_status = "handoff.prepare", "RELEASED"
            elif event_type == "HANDOFF_LOCAL_COMMITTED":
                expected_node, expected_status = "handoff.dispatch", "COMPLETED"
            elif event_type == "RUN_PAUSED":
                expected_status = "PAUSED"
            elif event_type == "RUN_RESUMED":
                expected_status = "ACTIVE"
            elif event_type == "NODE_DISPATCH_PLANNED":
                attempt_id = event.get("attempt_id")
                if not isinstance(attempt_id, str) or attempt_id in attempt_events:
                    blockers.append("event authority has ambiguous dispatch attempt")
                else:
                    attempt_events[attempt_id] = {
                        "node_id": event.get("node_id"),
                        "status": "PLANNED",
                    }
            elif event_type in {"NODE_CALL_STARTED", "NODE_CALL_OUTCOME_UNKNOWN"}:
                attempt_id = event.get("attempt_id")
                if attempt_id not in attempt_events:
                    blockers.append(
                        f"event authority has unplanned dispatch event {attempt_id}"
                    )
                else:
                    attempt_events[attempt_id]["status"] = (
                        "DISPATCHED"
                        if event_type == "NODE_CALL_STARTED"
                        else "UNKNOWN_SIDE_EFFECT"
                    )
        if state.get("state_version") != expected_state_version:
            blockers.append(
                "snapshot state version differs from event authority: "
                f"{state.get('state_version')} != {expected_state_version}"
            )
        if state.get("current_node") != expected_node:
            blockers.append(
                "snapshot current node differs from event authority: "
                f"{state.get('current_node')} != {expected_node}"
            )
        if state.get("status") != expected_status:
            blockers.append(
                "snapshot lifecycle differs from event authority: "
                f"{state.get('status')} != {expected_status}"
            )
        if state.get("consumed_wait_triggers", []) != wait_trigger_events:
            blockers.append("snapshot WAIT trigger ledger differs from event authority")
        for consumed_ref in wait_trigger_events:
            trigger_id = consumed_ref.get("trigger_id")
            exact_evidence = {
                "role": "wait_trigger_evidence",
                **consumed_ref.get("evidence_ref", {}),
            }
            if state.get("artifact_refs", {}).get(f"wait-trigger:{trigger_id}") != exact_evidence:
                blockers.append(f"snapshot WAIT trigger artifact {trigger_id} differs from event authority")

        attempts = state.get("dispatch_attempts", [])
        consumed_attempts = frozenset(state.get("consumed_attempts", []))
        attempt_ids = [item.get("attempt_id") for item in attempts if isinstance(item, dict)]
        if len(attempt_ids) != len(set(attempt_ids)):
            blockers.append("snapshot dispatch attempts are not unique")
        if set(attempt_ids) != set(attempt_events):
            blockers.append("snapshot dispatch attempts differ from event authority")
        for attempt in attempts:
            if not isinstance(attempt, dict):
                blockers.append("snapshot dispatch attempt is not an object")
                continue
            attempt_id = attempt.get("attempt_id")
            authority = attempt_events.get(attempt_id)
            if authority is None:
                continue
            if (
                attempt.get("node_id") != authority["node_id"]
                or attempt.get("status") != authority["status"]
            ):
                blockers.append(
                    f"dispatch {attempt_id} differs from event authority"
                )
            contract = attempt.get("contract")
            node_id = attempt.get("node_id")
            if not isinstance(contract, dict) or node_id not in self.registry.contracts:
                blockers.append(f"dispatch {attempt_id} contract is missing or unknown")
                continue
            current = self.registry.contracts[node_id]
            base_contract_invalid = (
                contract.get("schema_version") != "node-dispatch.v1"
                or contract.get("attempt_id") != attempt_id
                or contract.get("node_id") != node_id
                or not isinstance(contract.get("instruction_ref"), str)
                or not contract.get("instruction_ref")
                or not isinstance(contract.get("instruction_hash"), str)
                or not contract.get("instruction_hash", "").startswith("sha256:")
                or len(contract.get("instruction_hash", "")) != 71
                or contract.get("producer_kind") not in {
                    "HOST_AGENT", "DETERMINISTIC_PROGRAM"
                }
                or not isinstance(contract.get("validator"), str)
                or not contract.get("validator")
                or not isinstance(contract.get("routes"), list)
                or any(not isinstance(route, str) for route in contract.get("routes", []))
                or not isinstance(contract.get("input_refs"), list)
                or not isinstance(contract.get("input_hashes"), dict)
                or not isinstance(contract.get("resource_refs", []), list)
            )
            current_contract_invalid = False
            if attempt_id not in consumed_attempts:
                try:
                    compatibility = self.registry.instruction_compatibility(
                        node_id, contract.get("instruction_hash")
                    )
                except (OSError, KeyError, ValueError) as error:
                    blockers.append(
                        f"dispatch {attempt_id} instruction cannot resolve: {error}"
                    )
                    continue
                current_contract_invalid = (
                    compatibility == "INCOMPATIBLE"
                    or contract.get("instruction_ref") != current.get("instruction_ref")
                    or contract.get("producer_kind") != current.get("producer_kind")
                    or contract.get("validator") != current.get("validator")
                    or sorted(contract.get("routes", []))
                    != sorted(current.get("routes", []))
                )
            if base_contract_invalid or current_contract_invalid:
                blockers.append(f"dispatch {attempt_id} contract drifted")
            if attempt.get("authorized_state_version") == state.get("state_version") and (
                attempt.get("authority_hash") != self._dispatch_authority_hash(state)
            ):
                blockers.append(f"dispatch {attempt_id} authority hash drifted")
            result_path = self._result_path(run_id, str(attempt_id))
            if result_path.exists():
                receipt_path = result_path.with_name("result-receipt.json")
                if not receipt_path.is_file():
                    blockers.append(f"result {attempt_id} receipt is missing")
                else:
                    receipt = read_json(receipt_path)
                    if (
                        receipt.get("attempt_id") != attempt_id
                        or receipt.get("node_id") != node_id
                        or receipt.get("result_hash") != sha256_file(result_path)
                    ):
                        blockers.append(f"result {attempt_id} receipt differs from exact result")
        return blockers

    @serialized_run_mutation
    def authoritative_read_barrier(self, run_id: str) -> dict[str, Any]:
        """Recover safe journals, then reject snapshots not authorized by events."""

        from .documents import hash_tree
        from .failpoints import recover_run

        recovered_transactions = self.recover_transactions(run_id)
        state = self.load_state(run_id)
        try:
            events = verify_event_chain(self._events_path(run_id))
        except Exception as error:
            raise TransitionRejected(f"event authority audit integrity failed: {error}") from error
        pre_recovery_blockers = self._full_state_commitment_blockers(state, events)
        if recovered_transactions:
            recovery = {
                "status": "RECOVERED_TRANSACTION",
                "run_id": run_id,
                "recovered_transactions": recovered_transactions,
            }
        elif pre_recovery_blockers:
            recovery = {"status": "BLOCKED_STATE_AUTHORITY", "run_id": run_id}
        else:
            recovery = recover_run(self, run_id)
            state = self.load_state(run_id)
            try:
                events = verify_event_chain(self._events_path(run_id))
            except Exception as error:
                raise TransitionRejected(
                    f"event authority audit integrity failed: {error}"
                ) from error
        blockers = self._full_state_commitment_blockers(state, events)
        blockers.extend(self._event_authority_blockers(run_id, state, events))
        unknown_side_effect = any(
            isinstance(attempt, dict)
            and attempt.get("node_id") == state.get("current_node")
            and attempt.get("status") == "UNKNOWN_SIDE_EFFECT"
            for attempt in state.get("dispatch_attempts", [])
        )
        if recovery.get("status") == "RECONCILE_REQUIRED" or unknown_side_effect:
            blockers.append(
                "event authority dispatch is UNKNOWN_SIDE_EFFECT and requires reconciliation"
            )
        graph = state.get("graph_manifest", {})
        if (
            graph.get("version") != self.graph.get("version")
            or graph.get("hash") != sha256_file(self.graph_path)
        ):
            blockers.append("event authority graph manifest identity changed")
        for name, ref in state.get("artifact_refs", {}).items():
            try:
                self._validate_single_artifact_ref(ref)
            except TransitionRejected as error:
                blockers.append(f"event authority artifact {name}: {error}")
        candidate = state.get("current_candidate_ref")
        if isinstance(candidate, dict):
            try:
                self._current_candidate_artifact(state)
            except TransitionRejected as error:
                blockers.append(f"event authority Candidate: {error}")
        for plan in state.get("fanout_plans", []):
            path = self.project_root / plan.get("path", "")
            if (
                not path.is_file()
                or path.is_symlink()
                or sha256_file(path) != plan.get("hash")
                or not path.with_name("status.json").is_file()
            ):
                blockers.append(
                    f"event authority fanout plan {plan.get('plan_id')} is missing or changed"
                )
        handoff_ref = state.get("handoff_ref")
        is_bug_handoff = (
            state.get("status") == "COMPLETED"
            and isinstance(handoff_ref, dict)
            and handoff_ref.get("delivery_kind") == "BUG"
        )
        release_ref = state.get("release_ref")
        if state.get("status") == "RELEASED" or (
            state.get("status") == "COMPLETED" and not is_bug_handoff
        ):
            if not isinstance(release_ref, dict):
                blockers.append("event authority Released lifecycle has no exact release ref")
            else:
                try:
                    ready_path = self.project_root / release_ref["path"]
                    released_root = self.project_root / release_ref["artifact_path"]
                    if (
                        not ready_path.is_file()
                        or ready_path.is_symlink()
                        or sha256_file(ready_path) != release_ref.get("hash")
                        or not released_root.is_dir()
                        or released_root.is_symlink()
                        or hash_tree(released_root) != release_ref.get("candidate_tree_hash")
                    ):
                        blockers.append("event authority release ref is missing or changed")
                except (KeyError, OSError, ValueError):
                    blockers.append("event authority release ref is incomplete")
        elif is_bug_handoff and release_ref is not None:
            blockers.append("event authority Bug Handoff must not claim a PRD release ref")
        if state.get("status") == "COMPLETED":
            try:
                self._validate_single_artifact_ref(handoff_ref)
            except TransitionRejected as error:
                blockers.append(f"event authority Handoff: {error}")
            if is_bug_handoff:
                try:
                    self._validate_single_artifact_ref(state.get("bug_human_ref"))
                except TransitionRejected as error:
                    blockers.append(f"event authority Bug human view: {error}")
        if blockers:
            raise TransitionRejected("event authority barrier: " + "; ".join(blockers))
        return state

    @serialized_run_mutation
    def set_run_activity(
        self,
        run_id: str,
        action: str,
        *,
        expected_state_version: int,
    ) -> dict[str, Any]:
        if action not in {"pause", "resume"}:
            raise ValueError("run activity action must be pause or resume")
        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        if action == "pause" and state["status"] != "ACTIVE":
            raise TransitionRejected(
                f"pause requires ACTIVE Run, got {state['status']}"
            )
        if action == "resume" and state["status"] not in {"PAUSED", "ACTIVE"}:
            raise TransitionRejected(
                f"resume requires PAUSED or reconciled ACTIVE Run, got {state['status']}"
            )
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["status"] = "PAUSED" if action == "pause" else "ACTIVE"
        next_state["pause"] = (
            {"reason": "USER_REQUEST", "state_version": next_state["state_version"]}
            if action == "pause"
            else None
        )
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "RUN_PAUSED" if action == "pause" else "RUN_RESUMED",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
            },
            transaction_id=f"activity-{next_state['state_version']}-{action}",
        )

    @serialized_run_mutation
    def consume_wait_trigger(
        self,
        run_id: str,
        command: dict[str, Any],
        *,
        command_ref: dict[str, Any],
    ) -> dict[str, Any]:
        """Consume one exact typed NEW_EVIDENCE trigger and return to Evidence."""

        from .storage import require_iso_datetime

        try:
            self.schemas.validate("wait-trigger-command.schema.json", command)
        except SchemaValidationError as error:
            raise TransitionRejected(f"WAIT trigger command invalid: {error}") from error
        require_iso_datetime(command.get("received_at"), "WAIT trigger received_at")
        state = self.load_state(run_id)
        consumed = state.get("consumed_wait_triggers", [])
        if any(item.get("trigger_id") == command.get("trigger_id") for item in consumed):
            raise TransitionRejected("WAIT trigger was already consumed")
        if state.get("status") != "WAITING_TRIGGER" or state.get("current_node") != "product.decision":
            raise TransitionRejected("WAIT trigger requires the exact WAITING_TRIGGER lifecycle")
        if command.get("run_id") != run_id:
            raise TransitionRejected("WAIT trigger Run identity does not match")
        if command.get("waiting_state_version") != state.get("state_version"):
            raise TransitionRejected("WAIT trigger state version does not match the waiting Run")
        waiting = state.get("waiting")
        outcome_details = waiting.get("outcome_details") if isinstance(waiting, dict) else None
        wait_details = outcome_details.get("WAIT") if isinstance(outcome_details, dict) else None
        condition = wait_details.get("review_trigger") if isinstance(wait_details, dict) else None
        if waiting is None or waiting.get("kind") != "NEW_EVIDENCE" or not condition:
            raise TransitionRejected("WAIT state has no exact NEW_EVIDENCE condition")
        if command.get("waiting_condition") != condition:
            raise TransitionRejected("WAIT trigger condition does not match")
        self._validate_single_artifact_ref(command["evidence_ref"])
        evidence = read_json(self.project_root / command["evidence_ref"]["path"])
        if evidence.get("status") in {"FAIL", "REJECTED"} or evidence.get("authorized") is False:
            raise TransitionRejected("WAIT trigger Evidence is explicitly failed or unauthorized")
        self._validate_single_artifact_ref(command_ref)

        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["status"] = "ACTIVE"
        next_state["current_node"] = "evidence.collect"
        next_state["next_allowed_nodes"] = self.edges.get("evidence.collect", [])
        next_state["waiting"] = None
        consumed_ref = {
            "trigger_id": command["trigger_id"],
            "trigger_type": "NEW_EVIDENCE",
            "command_ref": command_ref,
            "evidence_ref": command["evidence_ref"],
            "waiting_state_version": state["state_version"],
        }
        next_state.setdefault("consumed_wait_triggers", []).append(consumed_ref)
        next_state["artifact_refs"][f"wait-trigger:{command['trigger_id']}"] = {
            "role": "wait_trigger_evidence",
            **command["evidence_ref"],
        }
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "WAIT_TRIGGER_CONSUMED",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "trigger_id": command["trigger_id"],
                "trigger_type": "NEW_EVIDENCE",
                "waiting_condition": condition,
                "received_at": command["received_at"],
                "source": command["source"],
                "command_ref": command_ref,
                "evidence_ref": command["evidence_ref"],
                "consumed_ref": consumed_ref,
            },
            transaction_id=f"wait-trigger-{command['trigger_id']}",
        )

    @serialized_run_mutation
    def apply_owner_choice(
        self,
        run_id: str,
        command: dict[str, Any],
        *,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Apply one typed Host-user command; an Agent payload cannot call itself Owner."""

        try:
            self.schemas.validate("owner-choice-command.schema.json", command)
        except SchemaValidationError as error:
            if "expected_state_version" in str(error):
                raise TransitionRejected(f"Owner choice state version invalid: {error}") from error
            raise TransitionRejected(f"Owner choice command invalid: {error}") from error
        state = self.load_state(run_id)
        if state["current_node"] != "product.decision":
            raise TransitionRejected("Owner choice is only valid at product.decision")
        if command["expected_state_version"] != state["state_version"]:
            raise TransitionRejected(
                f"Owner choice state version {command['expected_state_version']} "
                f"does not match {state['state_version']}"
            )
        actor = command["actor"]
        if actor.get("kind") != "OWNER" or not actor.get("id"):
            raise TransitionRejected("Owner actor identity is required")
        proposal_ref = command["proposal_ref"]
        if proposal_ref.get("hash") != command["proposal_hash"]:
            raise TransitionRejected("Owner choice proposal hash does not match proposal_ref")
        try:
            proposal_path = (self.project_root / proposal_ref["path"]).resolve()
            proposal_path.relative_to(self.project_root)
        except (KeyError, ValueError) as error:
            raise TransitionRejected("Owner choice proposal ref escapes the project") from error
        if (
            not proposal_path.is_file()
            or proposal_path.is_symlink()
            or sha256_file(proposal_path) != command["proposal_hash"]
        ):
            raise TransitionRejected("Owner choice proposal hash does not match exact proposal")
        proposal = read_json(proposal_path)
        if proposal.get("decision_id") != command["decision_id"] or proposal.get("run_id") != run_id:
            raise TransitionRejected("Owner choice proposal identity does not match this Run")
        authoritative_proposal = {**proposal, "proposal_ref": proposal_ref}
        try:
            record = record_owner_decision(self.project_root, authoritative_proposal, command)
        except ValueError as error:
            raise TransitionRejected(str(error)) from error
        if failpoint is not None:
            failpoint("after_decision_record")

        choice = record["chosen_outcome"]
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["decision"] = {
            "decision_id": record["decision_id"],
            "chosen_outcome": choice,
            "route": record["route"],
            "proposal_ref": record["proposal_ref"],
            "record_ref": record["record_ref"],
            "owner_actor": actor,
        }
        next_state["artifact_refs"][
            f"decision-record:{record['decision_id']}:v{record['record_ref']['version']}"
        ] = {
            "role": "decision_record",
            **record["record_ref"],
            "origin_node_id": "product.decision",
            "origin_attempt_id": proposal.get("agent_provenance", {}).get("attempt_id"),
        }
        if choice == "STOP":
            next_state.update({"status": "CLOSED", "current_node": "product.decision", "next_allowed_nodes": []})
        elif choice == "WAIT":
            next_state.update(
                {
                    "status": "WAITING_TRIGGER",
                    "current_node": "product.decision",
                    "next_allowed_nodes": [],
                }
            )
            next_state["waiting"] = {"kind": "NEW_EVIDENCE", "outcome_details": command["outcome_details"]}
        elif choice == "RESEARCH":
            next_state.update({"status": "ACTIVE", "current_node": "evidence.collect"})
            next_state["next_allowed_nodes"] = self.edges.get("evidence.collect", [])
            next_state["waiting"] = None
        elif choice in {"EXPERIMENT", "COMMIT"} and record["route"] != "ROADMAP_ONLY":
            next_state.update({"status": "ACTIVE", "current_node": "product.planning"})
            next_state["next_allowed_nodes"] = self.edges.get("product.planning", [])
            next_state["planning_intent"] = record["route"]
        else:
            next_state.update({"status": "ROADMAP_ONLY", "current_node": "product.decision", "next_allowed_nodes": []})
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_id": f"owner-choice:{run_id}:{command['proposal_hash']}",
                "event_type": "OWNER_CHOICE_RECORDED",
                "actor": actor["id"],
                "actor_kind": "OWNER",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "proposal_ref": proposal_ref,
                "record_ref": record["record_ref"],
                "chosen_outcome": choice,
                "route": record["route"],
            },
            transaction_id=f"owner-choice-{command['proposal_hash'].removeprefix('sha256:')}",
            failpoint=failpoint,
            after_event_phase="after_owner_event",
        )

    @serialized_run_mutation
    def set_interview_policy(
        self,
        run_id: str,
        action: str,
        *,
        expected_state_version: int,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if action not in {"skip", "resume"}:
            raise ValueError("interview policy action must be skip or resume")
        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["interaction_policy"] = (
            "NO_PM_INTERVIEW" if action == "skip" else "ALLOW_PM_INTERVIEW"
        )
        if action == "skip":
            next_state["current_interview_question"] = None
        unresolved = [
            item
            for item in next_state.get("unresolved", [])
            if item.get("owner") == "PM_ONLY" and item.get("status", "UNRESOLVED") == "UNRESOLVED"
        ]
        resume_target = None
        if action == "resume" and unresolved:
            resume_target = max(unresolved, key=lambda item: item.get("priority", 0)).get("id")
        next_state["interaction_resume_target"] = resume_target
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "INTERVIEW_SKIPPED" if action == "skip" else "INTERVIEW_RESUMED",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "resume_target": resume_target,
            },
            transaction_id=f"interview-{next_state['state_version']}-{action}",
            failpoint=failpoint,
        )

    @serialized_run_mutation
    def return_to_product_planning(
        self,
        run_id: str,
        *,
        attempt_id: str,
        submission_hash: str,
        source_candidate_ref: dict[str, Any],
        exact_delta: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Record one typed scope-reconciliation return without accepting a Candidate."""

        state = self.load_state(run_id)
        previous = state.get("scope_reconciliation")
        if isinstance(previous, dict) and previous.get("attempt_id") == attempt_id:
            if previous.get("submission_hash") != submission_hash:
                raise StateConflict(
                    f"scope reconciliation attempt identity conflict: {attempt_id}"
                )
            return state
        if state.get("current_node") != "prd.optimize":
            raise TransitionRejected(
                "PLAN_RECONCILE_REQUIRED is only valid from prd.optimize"
            )
        current = state.get("current_candidate_ref")
        if not isinstance(current, dict) or any(
            current.get(field) != source_candidate_ref.get(field)
            for field in ("path", "hash", "version")
        ):
            raise TransitionRejected(
                "PLAN_RECONCILE_REQUIRED source Candidate is not current"
            )
        if not exact_delta or any(
            not isinstance(item, dict)
            or set(item) != {"field", "planned", "proposed"}
            for item in exact_delta
        ):
            raise TransitionRejected(
                "PLAN_RECONCILE_REQUIRED exact scope delta is required"
            )
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["current_node"] = "product.planning"
        next_state["next_allowed_nodes"] = self.edges.get("product.planning", [])
        next_state["planning_intent"] = "PLAN_RECONCILE_REQUIRED"
        next_state["scope_reconciliation"] = {
            "schema_version": "scope-reconciliation.v1",
            "status": "PLAN_RECONCILE_REQUIRED",
            "attempt_id": attempt_id,
            "submission_hash": submission_hash,
            "source_candidate_ref": {
                field: source_candidate_ref[field]
                for field in ("path", "hash", "version")
            },
            "exact_delta": exact_delta,
            "route": {"from_node": "prd.optimize", "to_node": "product.planning"},
        }
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "PLAN_RECONCILE_REQUIRED",
                "actor": "state-controller",
                "run_id": run_id,
                "from_node": "prd.optimize",
                "to_node": "product.planning",
                "attempt_id": attempt_id,
                "source_candidate_ref": next_state["scope_reconciliation"][
                    "source_candidate_ref"
                ],
                "exact_delta": exact_delta,
                "before_state_version": state["state_version"],
                "after_state_version": next_state["state_version"],
            },
            transaction_id=f"scope-reconcile-{attempt_id}",
        )

    def _validate_result_contract(
        self,
        state: dict[str, Any],
        result: dict[str, Any],
        *,
        controller_owned: bool,
    ) -> None:
        producer_kind = result.get("producer", {}).get("kind")
        if controller_owned:
            if producer_kind != "DETERMINISTIC_PROGRAM":
                raise TransitionRejected("Controller-owned result must be deterministic")
        elif producer_kind != "HOST_AGENT":
            raise TransitionRejected(
                "Controller-only mechanical results cannot be supplied by a caller"
            )
        if state["status"] != "ACTIVE":
            raise TransitionRejected(
                f"Run must be ACTIVE to accept a Node Result, got {state['status']}"
            )
        try:
            self.schemas.validate("node-result.schema.json", result)
            validate_node_result_producer(result)
            validate_node_output(state["current_node"], result)
        except (PolicyViolation, SchemaValidationError, NodeValidationError, ValueError) as error:
            raise TransitionRejected(str(error)) from error
        if result["node_id"] != state["current_node"]:
            raise TransitionRejected(
                f"result node {result['node_id']} does not match current node {state['current_node']}"
            )
        self._validate_exact_dispatch_result(state, result)
        if not controller_owned:
            self._validate_artifact_refs(result)
        if state["current_node"] == "review.aggregate":
            self._review_aggregate_authority(state["run_id"], state, result)

    def preflight_agent_submission(
        self,
        run_id: str,
        result: dict[str, Any],
        requested_node: str | None,
    ) -> None:
        """Validate one public Host submission and route without writing Run authority."""

        state = self.load_state(run_id)
        self._validate_result_contract(state, result, controller_owned=False)
        node_id = state["current_node"]
        if node_id == "product.decision":
            if requested_node is not None:
                raise TransitionRejected(
                    "product.decision does not accept requested_node before Owner choice"
                )
            return
        allowed = self.edges.get(node_id, [])
        if requested_node not in allowed:
            raise TransitionRejected(
                f"{node_id} requested_node must be one of {allowed}"
            )
        if node_id == "review.aggregate":
            self.validate_review_aggregate_route(
                run_id, state, result, requested_node
            )

    def validate_agent_result(self, run_id: str, result: dict[str, Any]) -> None:
        """Read-only validation used before any PRD archive side effect."""

        self._validate_result_contract(
            self.load_state(run_id), result, controller_owned=False
        )

    def _persist_result(
        self,
        run_id: str,
        result: dict[str, Any],
        *,
        controller_owned: bool,
        failpoint: Callable[[str], None] | None = None,
    ) -> Path:
        state = self.load_state(run_id)
        self._validate_result_contract(state, result, controller_owned=controller_owned)
        result_path = self._result_path(run_id, result["attempt_id"])
        if result_path.exists():
            raise StateConflict(f"attempt already exists: {result['attempt_id']}")
        if failpoint is not None:
            failpoint("before_result_persist")
        atomic_write_json(result_path, result)
        if failpoint is not None:
            failpoint("after_result_persist")
        receipt_path = result_path.with_name("result-receipt.json")
        atomic_write_json(receipt_path, self._result_receipt_payload(result, result_path))
        append_event(
            self._events_path(run_id),
            {
                "event_type": "NODE_RESULT_PERSISTED",
                "actor": result["producer"]["kind"],
                "run_id": run_id,
                "node_id": result["node_id"],
                "attempt_id": result["attempt_id"],
                "result_hash": sha256_file(result_path),
            },
        )
        return result_path

    @staticmethod
    def _result_receipt_payload(
        result: dict[str, Any], result_path: Path
    ) -> dict[str, Any]:
        receipt = {
            "schema_version": "node-result-receipt.v1",
            "attempt_id": result["attempt_id"],
            "node_id": result["node_id"],
            "result_hash": sha256_file(result_path),
        }
        if result.get("node_id") == "problem.ready.gate":
            output = result["mechanical_output"]
            receipt.update(
                {
                    "outcome": output["status"],
                    "validator": output["validator"],
                    "rules_version": output["rules_version"],
                    "unmet_conditions": output["unmet_conditions"],
                }
            )
        return receipt

    @serialized_run_mutation
    def submit_result(
        self,
        run_id: str,
        result: dict[str, Any],
        *,
        failpoint: Callable[[str], None] | None = None,
    ) -> Path:
        """Persist a public Host-Agent result; caller-authored mechanics are forbidden."""

        return self._persist_result(
            run_id,
            result,
            controller_owned=False,
            failpoint=failpoint,
        )

    @serialized_run_mutation
    def execute_mechanical_result(
        self,
        run_id: str,
        attempt_id: str,
        *,
        route_destination: str | None = None,
        failpoint: Callable[[str], None] | None = None,
    ) -> Path:
        """Derive and persist one internal mechanical result from Controller state."""

        state = self.load_state(run_id)
        node_id = state["current_node"]
        if node_id == "signal.ingest":
            output = {"status": "COMPLETED"}
        elif node_id == "route.select":
            allowed = {"INCIDENT_ASSESS", "BUG_BASELINE_CHECK", "DISCOVERY_START"}
            if route_destination not in allowed:
                raise TransitionRejected("route.select requires an allowed Agent-authored route")
            output = {
                "status": "COMPLETED",
                "route_destination": route_destination,
            }
        elif node_id == "problem.ready.gate":
            review_result = self._load_committed_result(
                run_id, state, "problem.quality.review"
            )
            review = review_result["semantic_output"]
            candidate_ref = review.get("candidate_ref")
            validation = validate_problem_ready(
                {
                    "candidate_ref": candidate_ref,
                    "upstream_refs": review.get("upstream_refs", []),
                },
                review,
                current_candidate_hash=(candidate_ref or {}).get("hash", ""),
                available_ref_hashes=self._available_artifact_hashes(state),
            )
            output = build_problem_ready_output(
                validation,
                review,
                source_attempt_id=review_result["attempt_id"],
                available_ref_hashes=self._available_artifact_hashes(state),
            )
        elif node_id == "plan.ready.gate":
            plan_result = self._load_committed_result(
                run_id, state, "product.planning"
            )
            plan = plan_result["semantic_output"]
            validation = validate_plan(plan)
            decision_ref = plan.get("decision_ref", {})
            decision_matches = [
                item
                for item in state.get("artifact_refs", {}).values()
                if isinstance(item, dict)
                and item.get("role") == "decision_record"
                and item.get("origin_node_id") == "product.decision"
                and all(
                    item.get(field) == decision_ref.get(field)
                    for field in ("path", "hash", "version")
                )
            ]
            if validation.status != "READY" or len(decision_matches) != 1:
                repairs = list(validation.repair_targets)
                if len(decision_matches) != 1:
                    repairs.append("decision.exact_committed_authority")
                raise TransitionRejected(
                    "plan.ready.gate rejected exact committed Plan: "
                    + ", ".join(repairs)
                )
            output = {
                "status": "PASS",
                "validator": "plan_ready_gate",
                "source_attempt_id": plan_result["attempt_id"],
                "decision_ref": decision_ref,
            }
        elif node_id == "prd.ready.gate":
            required_kinds = {
                "audit_integrity",
                "document_experience",
                "mechanical_contracts",
                "review_finalize",
            }
            receipts = {
                item.get("kind"): item
                for item in state.get("ready_receipts", [])
                if item.get("attempt_id") == attempt_id
                and item.get("candidate_hash")
                == (state.get("current_candidate_ref") or {}).get("hash")
            }
            if set(receipts) != required_kinds:
                raise TransitionRejected(
                    "prd.ready.gate requires all exact Controller receipt kinds"
                )
            for kind, ref in receipts.items():
                try:
                    receipt = read_json(
                        resolve_file_ref(self.project_root, ref, f"{kind} Gate receipt")
                    )
                    from .receipts import verify_controller_receipt

                    verify_controller_receipt(
                        self.project_root,
                        ref,
                        kind,
                        receipt.get("subject_refs", []),
                        expected_run_id=run_id,
                        expected_node_id=node_id,
                        expected_attempt_id=attempt_id,
                        expected_candidate_ref=state["current_candidate_ref"],
                    )
                except ReceiptError as error:
                    raise TransitionRejected(
                        f"prd.ready.gate receipt is invalid: {error}"
                    ) from error
            output = {
                "status": "PASS",
                "validator": "prd_ready_gate",
                "controller_receipts": receipts,
                "rules_version": READY_RULES_VERSION,
            }
        else:
            raise TransitionRejected(
                f"mechanical node {node_id} has no Controller-owned executor"
            )
        result = {
            "schema_version": "node-result.v1",
            "node_id": node_id,
            "attempt_id": attempt_id,
            "producer": {
                "kind": "DETERMINISTIC_PROGRAM",
                "component": "state-controller",
            },
            "mechanical_output": output,
            "artifact_refs": [],
        }
        return self._persist_result(
            run_id,
            result,
            controller_owned=True,
            failpoint=failpoint,
        )

    @serialized_run_mutation
    def recover_result_receipt(self, run_id: str, attempt_id: str) -> Path:
        """Recover only a validated result that crashed before its Controller receipt."""

        state = self.load_state(run_id)
        result_path = self._result_path(run_id, attempt_id)
        receipt_path = result_path.with_name("result-receipt.json")
        if receipt_path.exists():
            return receipt_path
        if not result_path.is_file():
            raise TransitionRejected(f"persisted attempt not found: {attempt_id}")
        result = read_json(result_path)
        try:
            self.schemas.validate("node-result.schema.json", result)
            validate_node_result_producer(result)
            validate_node_output(state["current_node"], result)
        except (PolicyViolation, SchemaValidationError, NodeValidationError, ValueError) as error:
            raise TransitionRejected(f"incomplete result cannot recover: {error}") from error
        if result.get("node_id") != state["current_node"] or result.get("attempt_id") != attempt_id:
            raise TransitionRejected("incomplete result does not match current node and attempt")
        try:
            self._validate_exact_dispatch_result(state, result)
        except TransitionRejected as error:
            raise TransitionRejected(f"incomplete result differs from exact dispatch: {error}") from error
        if result.get("producer", {}).get("kind") == "HOST_AGENT":
            try:
                self._validate_artifact_refs(result)
            except TransitionRejected as error:
                raise TransitionRejected(
                    f"incomplete result artifact authority is invalid: {error}"
                ) from error
        if state["current_node"] == "review.aggregate":
            self._review_aggregate_authority(run_id, state, result)
        atomic_write_json(receipt_path, self._result_receipt_payload(result, result_path))
        append_event(
            self._events_path(run_id),
            {
                "event_type": "NODE_RESULT_RECOVERED",
                "actor": "state-controller",
                "run_id": run_id,
                "node_id": result["node_id"],
                "attempt_id": attempt_id,
                "result_hash": sha256_file(result_path),
            },
        )
        return receipt_path

    @serialized_run_mutation
    def bind_candidate(
        self,
        run_id: str,
        candidate_ref: dict[str, Any],
        *,
        expected_state_version: int,
    ) -> dict[str, Any]:
        """Bind an already-authored exact Candidate; never generate or interpret its content."""

        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        self._validate_single_artifact_ref(candidate_ref)
        expected_candidate_version = state.get("candidate_version", 0) + 1
        if candidate_ref.get("version") != expected_candidate_version:
            raise TransitionRejected(
                f"candidate version must be {expected_candidate_version}, got {candidate_ref.get('version')}"
            )
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["candidate_version"] = candidate_ref["version"]
        next_state["current_candidate_ref"] = candidate_ref
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "CANDIDATE_BOUND",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "candidate_ref": candidate_ref,
            },
            transaction_id=f"candidate-{candidate_ref['version']}",
        )

    @staticmethod
    def _artifact_record(artifact: Any) -> dict[str, Any]:
        return {
            "path": str(artifact.path),
            "document_path": str(artifact.document_path),
            "document_hash": artifact.document_hash,
            "tree_hash": artifact.tree_hash,
            "prd_id": artifact.prd_id,
            "version": artifact.version,
            "status": artifact.status,
            "short_title": artifact.short_title,
            "date": artifact.date,
            "review_path": str(artifact.review_path),
            "review_hash": artifact.review_hash,
        }

    @staticmethod
    def _artifact_from_record(record: dict[str, Any]) -> Any:
        from .documents import ArtifactSet

        return ArtifactSet(
            Path(record["path"]),
            Path(record["document_path"]),
            record["document_hash"],
            record["tree_hash"],
            record["prd_id"],
            record["version"],
            record["status"],
            record["short_title"],
            record["date"],
            Path(record["review_path"]),
            record["review_hash"],
        )

    def _current_candidate_artifact(self, state: dict[str, Any]) -> Any:
        from .documents import ArtifactSet, hash_tree

        ref = state.get("current_candidate_ref")
        if not isinstance(ref, dict):
            raise TransitionRejected("Run has no exact current Candidate")
        try:
            artifact_path = assert_managed_path(
                self.project_root, self.project_root / ref["artifact_path"]
            )
            document_path = assert_managed_path(
                self.project_root, self.project_root / ref["path"]
            )
            review_path = assert_managed_path(
                self.project_root, self.project_root / ref["review_path"]
            )
            artifact_path.relative_to(
                self.project_root / "artifacts" / "prds" / "archived"
            )
            document_path.relative_to(artifact_path)
            review_path.relative_to(artifact_path)
        except (KeyError, ValueError) as error:
            raise TransitionRejected("current Candidate escapes the managed archive") from error
        metadata_paths = list(artifact_path.glob("*.metadata.json"))
        if (
            artifact_path.is_symlink()
            or not document_path.is_file()
            or document_path.is_symlink()
            or not review_path.is_file()
            or review_path.is_symlink()
            or len(metadata_paths) != 1
            or sha256_file(document_path) != ref.get("hash")
            or sha256_file(review_path) != ref.get("review_hash")
            or hash_tree(artifact_path) != ref.get("tree_hash")
        ):
            raise TransitionRejected("current Candidate exact tree is missing or changed")
        metadata = read_json(metadata_paths[0])
        return ArtifactSet(
            artifact_path,
            document_path,
            ref["hash"],
            ref["tree_hash"],
            metadata["prd_id"],
            ref["version"],
            "CANDIDATE_ARCHIVED",
            metadata["short_title"],
            metadata["date"],
            review_path,
            ref["review_hash"],
        )

    @serialized_run_mutation
    def prepare_ready_gate_evidence(
        self,
        run_id: str,
        attempt_id: str,
        *,
        expected_state_version: int,
    ) -> tuple[Any, dict[str, Any], dict[str, list[dict[str, Any]]]]:
        """Materialize deterministic Ready facts and bind them to one Gate attempt."""

        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        current_attempts = [
            item
            for item in state.get("dispatch_attempts", [])
            if item.get("attempt_id") == attempt_id
            and item.get("node_id") == "prd.ready.gate"
            and item.get("status") == "DISPATCHED"
            and item.get("authorized_state_version") == state["state_version"]
            and item.get("authority_hash") == self._dispatch_authority_hash(state)
        ]
        if (
            state.get("status") != "ACTIVE"
            or state.get("current_node") != "prd.ready.gate"
            or len(current_attempts) != 1
        ):
            raise TransitionRejected("Ready evidence requires one exact current Gate attempt")
        archived = self._current_candidate_artifact(state)
        candidate = state["current_candidate_ref"]
        companion = read_json(archived.review_path)
        if (
            companion.get("status") != "FINALIZED"
            or companion.get("authority") != "ADVISORY_ONLY"
            or companion.get("candidate_hash") != archived.document_hash
            or companion.get("version") != archived.version
        ):
            raise TransitionRejected("Ready evidence requires exact FINALIZED companion")
        metadata_paths = list(archived.path.glob("*.metadata.json"))
        if len(metadata_paths) != 1:
            raise TransitionRejected("Ready evidence requires self-contained Candidate metadata")
        metadata = read_json(metadata_paths[0])
        evals = metadata.get("evals", {})
        if evals.get("applicability") == "REQUIRED":
            raise TransitionRejected(
                "REQUIRED Evals cannot enter Ready in the current skills-only Host: verifiable independent "
                "fulfillment authority is unavailable; keep REVIEW_PENDING/NOT_RUN"
            )
        if evals.get("fulfillment") == "REVIEWED":
            try:
                validate_reviewed_evals(
                    self.project_root,
                    self.skill_root,
                    evals,
                    expected_candidate_ref={
                        "path": candidate["path"],
                        "hash": archived.document_hash,
                        "version": archived.version,
                    },
                    artifact_refs=state.get("artifact_refs", {}),
                    dispatched_input_hashes=current_attempts[0]["contract"]["input_hashes"],
                    committed_attempt_ids=frozenset(state.get("consumed_attempts", [])),
                )
            except EvalsAuthorityError as error:
                raise TransitionRejected(f"REVIEWED Evals authority invalid: {error}") from error
        aggregate_ref = companion.get("aggregate_ref")
        dispositions_ref = companion.get("dispositions_ref")
        for ref in (aggregate_ref, dispositions_ref):
            self._validate_single_artifact_ref(ref)
        aggregate = read_json(self.project_root / aggregate_ref["path"])
        dispositions = read_json(self.project_root / dispositions_ref["path"])
        decision_refs = metadata.get("decision_refs")
        evidence_refs = metadata.get("evidence_refs")
        fixed_metadata_refs = {
            "roadmap": metadata.get("roadmap_snapshot_ref"),
            "product_plan": metadata.get("product_plan_ref"),
            "slice": metadata.get("slice_ref"),
            "knowledge": metadata.get("knowledge_snapshot_ref"),
        }
        missing_upstream = []
        if not isinstance(decision_refs, list) or not decision_refs:
            missing_upstream.append("decision_refs")
        if not isinstance(evidence_refs, list):
            missing_upstream.append("evidence_refs")
        missing_upstream.extend(
            field
            for field, ref in (
                ("roadmap_snapshot_ref", fixed_metadata_refs["roadmap"]),
                ("product_plan_ref", fixed_metadata_refs["product_plan"]),
                ("slice_ref", fixed_metadata_refs["slice"]),
                ("knowledge_snapshot_ref", fixed_metadata_refs["knowledge"]),
            )
            if not isinstance(ref, dict) or not ref
        )
        if missing_upstream:
            raise TransitionRejected(
                "Ready Candidate metadata is missing required upstream facts: "
                + ", ".join(missing_upstream)
            )
        if any(not isinstance(ref, dict) for ref in [*decision_refs, *evidence_refs]):
            raise TransitionRejected(
                "Ready Candidate metadata upstream facts must be exact ref objects"
            )
        upstream_refs = [
            *({"kind": "decision", **ref} for ref in decision_refs),
            *(
                {"kind": kind, **ref}
                for kind, ref in fixed_metadata_refs.items()
            ),
            *({"kind": "evidence", **ref} for ref in evidence_refs),
        ]
        identities: set[tuple[Any, Any, Any]] = set()
        for ref in upstream_refs:
            identity = (ref.get("path"), ref.get("hash"), ref.get("version"))
            if any(value in (None, "") for value in identity):
                raise TransitionRejected(
                    f"Ready upstream ref requires exact path/hash/version: {ref.get('kind')}"
                )
            if identity in identities:
                raise TransitionRejected(
                    f"Ready Candidate metadata has duplicate exact upstream ref: {ref['path']}"
                )
            identities.add(identity)
        authorized = {
            (ref.get("path"), ref.get("hash"))
            for ref in state.get("artifact_refs", {}).values()
            if isinstance(ref, dict)
        }
        for ref in upstream_refs:
            self._validate_single_artifact_ref(ref)
            if (ref["path"], ref["hash"]) not in authorized:
                raise TransitionRejected(
                    f"Ready upstream ref is not bound to this Run: {ref['path']}"
                )

        evidence_root = self.run_path(run_id) / "ready-evidence"
        selection = self._template_selection_from_metadata(metadata)
        evidence_payloads = {
            "template_profile": (
                evidence_root / "template-profile.json",
                {
                    "schema_version": "template-profile-evidence.v1",
                    "profile_id": selection["profile_id"],
                    "version": selection["version"],
                    "template_path": selection["relative_path"],
                    "template_hash": selection["sha256"],
                    "source_kind": selection["source_kind"],
                    "selection_source": selection["selection_source"],
                    "fallback_reason": selection["fallback_reason"],
                    "requested_profile_id": selection["requested_profile_id"],
                    "requested_version": selection["requested_version"],
                    "output_contract_path": selection["output_contract_relative_path"],
                    "output_contract_hash": selection["output_contract_sha256"],
                    "output_contract_version": selection["output_contract_version"],
                },
            ),
            "version_record": (
                evidence_root / "version-record.json",
                {
                    "schema_version": "document-version-record.v1",
                    "candidate_hash": archived.document_hash,
                    "version": archived.version,
                    "status": "CANDIDATE_ARCHIVED",
                },
            ),
            "mechanical_validation": (
                evidence_root / "mechanical-validation.json",
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
            ),
        }
        events = verify_event_chain(self._events_path(run_id))
        evidence_payloads["audit_snapshot"] = (
            evidence_root / "audit-snapshot.json",
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
        evidence_refs: dict[str, dict[str, Any]] = {}
        for role, (path, payload) in evidence_payloads.items():
            if path.exists():
                if read_json(path) != payload:
                    raise StateConflict(f"Ready evidence identity conflict: {role}")
            else:
                atomic_write_json(path, payload)
            evidence_refs[role] = {
                "role": role,
                "path": path.relative_to(self.project_root).as_posix(),
                "hash": sha256_file(path),
                "version": 1,
            }
        changelog_path = self.project_root / "artifacts" / "prds" / "DOCUMENT_CHANGELOG.md"
        if not changelog_path.is_file() or changelog_path.is_symlink():
            raise TransitionRejected("Ready document changelog is missing")
        changelog_snapshot = evidence_root / "document-changelog-snapshot.md"
        changelog_bytes = changelog_path.read_bytes()
        if changelog_snapshot.exists():
            if (
                not changelog_snapshot.is_file()
                or changelog_snapshot.is_symlink()
                or changelog_snapshot.read_bytes() != changelog_bytes
            ):
                raise StateConflict("Ready document changelog snapshot identity conflict")
        else:
            atomic_write_bytes(changelog_snapshot, changelog_bytes)
        evidence_refs["document_changelog"] = {
            "role": "document_changelog",
            "path": changelog_snapshot.relative_to(self.project_root).as_posix(),
            "hash": sha256_file(changelog_snapshot),
            "version": 1,
        }
        candidate_document = {
            "role": "candidate_document",
            "path": archived.document_path.relative_to(self.project_root).as_posix(),
            "hash": archived.document_hash,
        }
        review_companion = {
            "role": "review_companion",
            "path": archived.review_path.relative_to(self.project_root).as_posix(),
            "hash": archived.review_hash,
            "version": archived.version,
        }
        fixed_upstream: dict[str, list[dict[str, Any]]] = {}
        for ref in upstream_refs:
            fixed_upstream.setdefault(ref["kind"], []).append(ref)
        mechanical_subjects = [candidate_document]
        for kind in ("decision", "roadmap", "product_plan", "slice", "knowledge", "evidence"):
            items = fixed_upstream.get(kind, [])
            mechanical_subjects.extend(
                controller_subject_ref(
                    (
                        f"upstream_{kind}"
                        if len(items) == 1
                        else f"upstream_{kind}:{index}"
                    ),
                    item,
                )
                for index, item in enumerate(items)
            )
        mechanical_subjects.append(evidence_refs["mechanical_validation"])
        subjects = {
            "review_finalize": [
                candidate_document,
                review_companion,
                controller_subject_ref("review_aggregate", aggregate_ref),
                controller_subject_ref("review_dispositions", dispositions_ref),
            ],
            "document_experience": [
                candidate_document,
                controller_subject_ref("template_profile", evidence_refs["template_profile"]),
                controller_subject_ref("version_record", evidence_refs["version_record"]),
                evidence_refs["document_changelog"],
            ],
            "audit_integrity": [evidence_refs["audit_snapshot"]],
            "mechanical_contracts": mechanical_subjects,
        }
        all_evidence = [
            *evidence_refs.values(),
            review_companion,
            controller_subject_ref("review_aggregate", aggregate_ref),
            controller_subject_ref("review_dispositions", dispositions_ref),
        ]
        next_state = json.loads(canonical_json_bytes(state))
        changed = False
        for index, ref in enumerate(all_evidence):
            key = f"ready-evidence:{ref['role']}:{index}"
            exact = {key: value for key, value in ref.items() if key in {"role", "path", "hash", "version"}}
            if next_state["artifact_refs"].get(key) != exact:
                next_state["artifact_refs"][key] = exact
                changed = True
        if changed:
            next_state["state_version"] += 1
            for item in next_state["dispatch_attempts"]:
                if item["attempt_id"] == attempt_id:
                    item["authorized_state_version"] = next_state["state_version"]
                    item["authority_hash"] = self._dispatch_authority_hash(next_state)
            self._commit_state_event(
                run_id,
                state,
                next_state,
                {
                    "event_type": "READY_EVIDENCE_BOUND",
                    "actor": "state-controller",
                    "run_id": run_id,
                    "state_version": next_state["state_version"],
                    "attempt_id": attempt_id,
                    "evidence_refs": all_evidence,
                },
                transaction_id=f"ready-evidence-{attempt_id}",
            )
            state = next_state
        request = {
            "run_id": run_id,
            "candidate_ref": {
                "path": str(archived.path),
                "hash": archived.document_hash,
                "resolved_hash": archived.document_hash,
                "tree_hash": archived.tree_hash,
                "version": archived.version,
            },
            "review": {
                "candidate_hash": archived.document_hash,
                "candidate_version": archived.version,
                "attempts": [
                    {"role": role, "status": attempt.get("status")}
                    for attempt in aggregate.get("attempts", [])
                    for role in attempt.get("roles_covered", [])
                ],
                "findings": aggregate.get("findings", []),
                "dispositions": dispositions.get("dispositions", []),
                "companion_view_ref": {
                    "path": review_companion["path"],
                    "hash": review_companion["hash"],
                    "version": archived.version,
                    "candidate_hash": archived.document_hash,
                    "finding_count": companion["finding_count"],
                },
                "aggregate_ref": aggregate_ref,
                "dispositions_ref": dispositions_ref,
            },
            "upstream_refs": upstream_refs,
            "evals": metadata["evals"],
            "presentation": {
                "template_profile_ref": evidence_refs["template_profile"],
                "version_record_ref": evidence_refs["version_record"],
                "changelog_ref": evidence_refs["document_changelog"],
                "audit_snapshot_ref": evidence_refs["audit_snapshot"],
            },
            "mechanical_validation_ref": evidence_refs["mechanical_validation"],
            "delivery_intent": metadata["delivery_intent"],
        }
        return archived, request, subjects

    def prevalidate_ready_evals(self, run_id: str) -> None:
        """Reject false REVIEWED claims before planning a writable Ready attempt."""

        state = self.load_state(run_id)
        if state.get("status") != "ACTIVE" or state.get("current_node") != "prd.ready.gate":
            raise TransitionRejected("Ready Evals prevalidation requires the current Ready Gate")
        archived = self._current_candidate_artifact(state)
        metadata_paths = list(archived.path.glob("*.metadata.json"))
        if len(metadata_paths) != 1:
            raise TransitionRejected("Ready Evals require self-contained Candidate metadata")
        metadata = read_json(metadata_paths[0])
        evals = metadata.get("evals", {})
        if evals.get("applicability") == "REQUIRED":
            raise TransitionRejected(
                "REQUIRED Evals cannot enter Ready in the current skills-only Host: verifiable independent "
                "fulfillment authority is unavailable; keep REVIEW_PENDING/NOT_RUN"
            )
        if evals.get("fulfillment") != "REVIEWED":
            return
        input_hashes: dict[str, str] = {}
        for ref in state.get("artifact_refs", {}).values():
            if not isinstance(ref, dict):
                continue
            path = ref.get("path")
            digest = ref.get("hash")
            if not isinstance(path, str) or not isinstance(digest, str):
                continue
            if path in input_hashes and input_hashes[path] != digest:
                raise TransitionRejected(f"Ready Evals bind conflicting hashes for {path}")
            input_hashes[path] = digest
        try:
            validate_reviewed_evals(
                self.project_root,
                self.skill_root,
                evals,
                expected_candidate_ref={
                    "path": archived.document_path.relative_to(self.project_root).as_posix(),
                    "hash": archived.document_hash,
                    "version": archived.version,
                },
                artifact_refs=state.get("artifact_refs", {}),
                dispatched_input_hashes=input_hashes,
                committed_attempt_ids=frozenset(state.get("consumed_attempts", [])),
            )
        except EvalsAuthorityError as error:
            raise TransitionRejected(f"REVIEWED Evals authority invalid: {error}") from error

    def _review_aggregate_authority(
        self,
        run_id: str,
        state: dict[str, Any],
        result: dict[str, Any],
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ]:
        """Validate the complete read-only authority of one Agent aggregate."""

        output = result.get("semantic_output", {})
        if not isinstance(output, dict):
            raise TransitionRejected("review.aggregate semantic_output must be an object")
        refs = result.get("artifact_refs")
        if not isinstance(refs, list):
            raise TransitionRejected("review.aggregate artifact_refs must be a list")
        refs_by_role: dict[str, list[dict[str, Any]]] = {}
        for ref in refs:
            if isinstance(ref, dict):
                refs_by_role.setdefault(ref.get("role", ""), []).append(ref)
        required_roles = ("review_aggregate", "review_dispositions")
        if len(refs) != 2 or any(
            len(refs_by_role.get(role, [])) != 1 for role in required_roles
        ):
            raise TransitionRejected(
                "review.aggregate artifact_refs: include exactly one exact "
                "review_aggregate and one exact review_dispositions artifact"
            )
        aggregate_ref = refs_by_role["review_aggregate"][0]
        dispositions_ref = refs_by_role["review_dispositions"][0]
        for role, ref in zip(required_roles, (aggregate_ref, dispositions_ref), strict=True):
            if any(ref.get(field) in (None, "") for field in ("path", "hash", "version")):
                raise TransitionRejected(
                    f"review.aggregate {role} ref: provide exact role/path/hash/version"
                )
        aggregate_identity = tuple(
            aggregate_ref.get(field) for field in ("path", "hash", "version")
        )
        dispositions_identity = tuple(
            dispositions_ref.get(field) for field in ("path", "hash", "version")
        )
        if aggregate_identity == dispositions_identity:
            raise TransitionRejected(
                "review.aggregate artifacts: aggregate and dispositions must be distinct exact refs"
            )
        self._validate_single_artifact_ref(aggregate_ref)
        self._validate_single_artifact_ref(dispositions_ref)
        try:
            aggregate = read_json(self.project_root / aggregate_ref["path"])
            dispositions = read_json(self.project_root / dispositions_ref["path"])
        except (OSError, ValueError) as error:
            raise TransitionRejected(
                f"review.aggregate artifacts must be readable JSON: {error}"
            ) from error
        try:
            validate_review_aggregate_artifacts(aggregate, dispositions, refs)
        except ReviewContractError as error:
            raise TransitionRejected(str(error)) from error

        review_result = self._load_committed_result(run_id, state, "review.parallel")
        review_output = review_result.get("semantic_output", {})
        aggregate_dispatch = next(
            (
                item.get("contract")
                for item in state.get("dispatch_attempts", [])
                if isinstance(item, dict)
                and item.get("attempt_id") == result.get("attempt_id")
                and item.get("node_id") == "review.aggregate"
                and isinstance(item.get("contract"), dict)
            ),
            None,
        )
        if aggregate_dispatch is None:
            raise TransitionRejected("review.aggregate exact dispatch authority is missing")
        dispatch_hashes = aggregate_dispatch.get("input_hashes", {})
        review_result_path = self._result_path(
            run_id, review_result["attempt_id"]
        ).relative_to(self.project_root).as_posix()
        candidate = state.get("current_candidate_ref") or {}
        if (
            dispatch_hashes.get(review_result_path)
            != sha256_file(self.project_root / review_result_path)
            or dispatch_hashes.get(candidate.get("path")) != candidate.get("hash")
        ):
            raise TransitionRejected(
                "review.aggregate dispatch inputs must bind the exact Candidate and review.parallel result"
            )
        expected_attempts = [
            {
                "attempt_id": review_result["attempt_id"],
                "status": "COMPLETED",
                "roles_covered": review_output.get("roles_covered"),
            }
        ]
        expected_aggregate = {
            key: value for key, value in output.items() if key != "dispositions"
        }
        candidate_identity = {
            key: candidate.get(key) for key in ("path", "hash", "version")
        }
        if output.get("candidate_ref") != candidate_identity:
            raise TransitionRejected(
                "review.aggregate candidate_ref: copy the exact current Candidate path/hash/version"
            )
        if aggregate.get("candidate_ref") != candidate_identity:
            raise TransitionRejected(
                "review_aggregate artifact candidate_ref: copy the exact current Candidate path/hash/version"
            )
        if output.get("attempts") != expected_attempts or aggregate.get("attempts") != expected_attempts:
            raise TransitionRejected(
                "review.aggregate attempts: copy the exact completed review.parallel attempt and roles_covered"
            )
        if output.get("findings") != review_output.get("findings") or aggregate.get(
            "findings"
        ) != review_output.get("findings"):
            raise TransitionRejected(
                "review.aggregate findings: preserve the exact review.parallel Finding set"
            )
        finding_ids = [
            item.get("finding_id")
            for item in aggregate.get("findings", [])
            if isinstance(item, dict)
        ]
        disposition_items = dispositions.get("dispositions", [])
        disposition_ids = [
            item.get("finding_id")
            for item in disposition_items
            if isinstance(item, dict) and item.get("status")
        ]
        roles = {
            role
            for attempt in aggregate.get("attempts", [])
            if isinstance(attempt, dict) and attempt.get("status") == "COMPLETED"
            for role in attempt.get("roles_covered", [])
        }
        disagreements = aggregate.get("disagreements")
        disagreement_ids: list[str] = []
        if isinstance(disagreements, list):
            for disagreement in disagreements:
                if not isinstance(disagreement, dict):
                    disagreement_ids.append("")
                    continue
                ids = disagreement.get("finding_ids", disagreement.get("findings", []))
                if not isinstance(ids, list):
                    disagreement_ids.append("")
                    continue
                disagreement_ids.extend(ids)
        if (
            aggregate != expected_aggregate
            or aggregate.get("schema_version") != "review-aggregate.v1"
            or aggregate.get("authority") != "ADVISORY_ONLY"
            or not {"product", "engineering_feasibility", "testability"}.issubset(roles)
            or not isinstance(aggregate.get("findings"), list)
            or any(not finding_id for finding_id in finding_ids)
            or len(finding_ids) != len(set(finding_ids))
            or not isinstance(disagreements, list)
            or any(
                not finding_id or finding_id not in set(finding_ids)
                for finding_id in disagreement_ids
            )
            or dispositions.get("schema_version") != "review-dispositions.v1"
            or dispositions.get("candidate_hash") != candidate.get("hash")
            or dispositions.get("candidate_version") != candidate.get("version")
            or output.get("dispositions") != disposition_items
            or sorted(disposition_ids) != sorted(finding_ids)
            or len(disposition_ids) != len(set(disposition_ids))
        ):
            raise TransitionRejected(
                "review.aggregate contract is incomplete: require matching schemas, "
                "ADVISORY_ONLY authority, required Reviewer roles, unique Findings, "
                "and one disposition for every Finding"
            )
        return aggregate_ref, dispositions_ref, aggregate, dispositions

    def _review_finalize_inputs(
        self, run_id: str, state: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Revalidate exact aggregate authority before deterministic finalization."""

        prior = self._load_committed_result(run_id, state, "review.aggregate")
        aggregate_ref, dispositions_ref, aggregate, _ = self._review_aggregate_authority(
            run_id, state, prior
        )
        return prior, aggregate_ref, dispositions_ref, aggregate

    @staticmethod
    def _accepted_current_prd_repairs(
        aggregate: dict[str, Any],
        disposition_record: dict[str, Any],
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        findings = aggregate.get("findings", [])
        dispositions = disposition_record.get("dispositions", [])
        findings_by_id = {item["finding_id"]: item for item in findings}
        accepted = [
            item
            for item in dispositions
            if item.get("status") == ACCEPTED_CURRENT_PRD_REPAIR
        ]
        if not accepted:
            raise TransitionRejected(
                "prd.optimize route requires at least one accepted current-PRD repair"
            )
        for disposition in accepted:
            finding = findings_by_id[disposition["finding_id"]]
            if (
                finding.get("repair_target") != "CURRENT_PRD"
                or not isinstance(disposition.get("repair_scope"), list)
                or not disposition["repair_scope"]
            ):
                raise TransitionRejected(
                    "accepted current-PRD repair requires CURRENT_PRD target and repair_scope"
                )
        return findings_by_id, accepted

    def validate_review_aggregate_route(
        self,
        run_id: str,
        state: dict[str, Any],
        result: dict[str, Any],
        requested_node: str | None,
    ) -> None:
        """Fail before persistence when an otherwise valid aggregate cannot take its route."""

        allowed = self.edges.get("review.aggregate", [])
        if requested_node not in allowed:
            raise TransitionRejected(
                f"review.aggregate requested_node must be one of {allowed}"
            )
        _, _, aggregate, disposition_record = self._review_aggregate_authority(
            run_id, state, result
        )
        if requested_node == "prd.optimize":
            self._accepted_current_prd_repairs(aggregate, disposition_record)

    def prd_optimize_context(
        self, run_id: str, state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Derive the exact, read-only repair authority for one Optimize attempt."""

        from .prd_contract import next_prd_version

        state = state or self.load_state(run_id)
        if state.get("current_node") != "prd.optimize":
            raise TransitionRejected("PRD Optimize context requires current prd.optimize state")
        candidate = state.get("current_candidate_ref")
        if not isinstance(candidate, dict):
            raise TransitionRejected("PRD Optimize requires an exact current Candidate")
        prior = self._load_committed_result(run_id, state, "review.aggregate")
        aggregate_ref, dispositions_ref, aggregate, disposition_record = (
            self._review_aggregate_authority(run_id, state, prior)
        )
        dispositions = disposition_record.get("dispositions")
        findings_by_id, accepted_dispositions = self._accepted_current_prd_repairs(
            aggregate, disposition_record
        )
        accepted_ids = [item["finding_id"] for item in accepted_dispositions]
        source_candidate_ref = {
            key: candidate[key]
            for key in ("path", "hash", "version")
        }
        return {
            "source_candidate_ref": source_candidate_ref,
            "aggregate_ref": {
                key: aggregate_ref[key] for key in ("path", "hash", "version")
            },
            "dispositions_ref": {
                key: dispositions_ref[key] for key in ("path", "hash", "version")
            },
            "accepted_findings": [findings_by_id[item] for item in accepted_ids],
            "accepted_dispositions": accepted_dispositions,
            "unadopted_dispositions": [
                item for item in dispositions if item["finding_id"] not in set(accepted_ids)
            ],
            "repair_scope": sorted(
                {
                    scope
                    for item in accepted_dispositions
                    for scope in item["repair_scope"]
                }
            ),
            "next_version": next_prd_version(candidate["version"]),
        }

    def reconciliation_generation_context(
        self, run_id: str, state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Derive exact vNext authority after a typed return through Product Planning."""

        from .prd_contract import next_prd_version

        state = state or self.load_state(run_id)
        reconciliation = state.get("scope_reconciliation")
        candidate = state.get("current_candidate_ref")
        if not isinstance(reconciliation, dict) or not isinstance(candidate, dict):
            raise TransitionRejected("reconciled PRD generation context is unavailable")
        source = self._current_candidate_artifact(state)
        metadata_paths = list(source.path.glob("*.metadata.json"))
        if len(metadata_paths) != 1:
            raise TransitionRejected("reconciled source Candidate metadata is ambiguous")
        metadata = read_json(metadata_paths[0])
        return {
            "schema_version": "reconciliation-generation-context.v1",
            "source_candidate_ref": {
                key: candidate[key] for key in ("path", "hash", "version")
            },
            "prd_id": metadata["prd_id"],
            "next_version": next_prd_version(candidate["version"]),
            "scope_reconciliation": {
                "attempt_id": reconciliation["attempt_id"],
                "exact_delta": reconciliation["exact_delta"],
            },
        }

    def _prepare_candidate_finalize_stage(
        self,
        run_id: str,
        archived: Any,
        companion: dict[str, Any],
    ) -> tuple[Path, str, str]:
        from .documents import hash_tree

        stage = assert_managed_path(
            self.project_root,
            self.run_path(run_id) / "candidate-finalize-staging" / archived.path.name,
        )
        if stage.exists():
            review_path = stage / archived.review_path.name
            if (
                stage.is_symlink()
                or not review_path.is_file()
                or review_path.is_symlink()
                or read_json(review_path) != companion
                or sha256_file(stage / archived.document_path.name) != archived.document_hash
            ):
                raise StateConflict("review finalize stage identity conflict")
            return stage, hash_tree(stage), sha256_file(review_path)
        stage.parent.mkdir(parents=True, exist_ok=True)
        temporary = stage.parent / f".{stage.name}.tmp-{uuid4().hex}"
        try:
            shutil.copytree(archived.path, temporary)
            atomic_write_json(temporary / archived.review_path.name, companion)
            os.replace(temporary, stage)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return stage, hash_tree(stage), sha256_file(stage / archived.review_path.name)

    def _validate_candidate_finalize_transaction(
        self, journal: dict[str, Any]
    ) -> tuple[Path, Path, Path]:
        from .documents import hash_tree

        publish = journal["candidate_publish"]
        stage = assert_managed_path(self.project_root, Path(publish["stage_path"]))
        target = assert_managed_path(self.project_root, Path(publish["target_path"]))
        history = assert_managed_path(self.project_root, Path(publish["history_path"]))
        stage.relative_to(
            self.run_path(journal["run_id"]) / "candidate-finalize-staging"
        )
        target.relative_to(self.project_root / "artifacts" / "prds" / "archived")
        history.relative_to(self.run_path(journal["run_id"]) / "candidate-generations")
        if not (
            stage.name == target.name == history.name
            and isinstance(publish.get("before_tree_hash"), str)
            and isinstance(publish.get("after_tree_hash"), str)
        ):
            raise StateConflict("Candidate finalize transaction paths are not bound")
        target_hash = hash_tree(target) if target.is_dir() and not target.is_symlink() else None
        history_hash = (
            hash_tree(history) if history.is_dir() and not history.is_symlink() else None
        )
        stage_hash = hash_tree(stage) if stage.is_dir() and not stage.is_symlink() else None
        before_hash = publish["before_tree_hash"]
        after_hash = publish["after_tree_hash"]
        valid_before_publish = (
            target_hash == before_hash
            and not history.exists()
            and stage_hash == after_hash
        )
        valid_between_moves = (
            not target.exists()
            and history_hash == before_hash
            and stage_hash == after_hash
        )
        valid_published = target_hash == after_hash and history_hash == before_hash
        if not (valid_before_publish or valid_between_moves or valid_published):
            raise StateConflict("Candidate finalize transaction cannot reconcile")
        return stage, target, history

    def _publish_candidate_finalize_transaction(self, journal: dict[str, Any]) -> None:
        from .documents import hash_tree

        publish = journal["candidate_publish"]
        lock = assert_managed_path(
            self.project_root,
            self.project_root / ".better-product-graph" / "locks" / "prd-artifacts.lock",
        )
        with exclusive_file_lock(lock):
            stage, target, history = self._validate_candidate_finalize_transaction(journal)
            if target.is_dir() and hash_tree(target) == publish["after_tree_hash"]:
                return
            if target.exists():
                history.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, history)
            if not target.exists():
                os.replace(stage, target)
            if target.is_symlink() or hash_tree(target) != publish["after_tree_hash"]:
                raise StateConflict("finalized Candidate differs from transaction identity")
            if history.is_symlink() or hash_tree(history) != publish["before_tree_hash"]:
                raise StateConflict("prior Candidate generation was not preserved")

    @serialized_run_mutation
    def finalize_review_and_transition(
        self,
        run_id: str,
        attempt_id: str,
        *,
        expected_state_version: int,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Create the review companion as a recoverable same-version Candidate generation."""

        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        if state.get("status") != "ACTIVE" or state.get("current_node") != "review.finalize":
            raise TransitionRejected("review finalize requires ACTIVE review.finalize lifecycle")
        archived = self._current_candidate_artifact(state)
        current_companion = read_json(archived.review_path)
        if current_companion.get("status") != "NOT_RUN":
            raise TransitionRejected("review finalize requires the current NOT_RUN companion generation")
        prior, aggregate_ref, dispositions_ref, aggregate = self._review_finalize_inputs(
            run_id, state
        )
        companion = {
            "schema_version": "prd-review-companion.v1",
            "prd_id": archived.prd_id,
            "version": archived.version,
            "candidate_hash": archived.document_hash,
            "status": "FINALIZED",
            "authority": "ADVISORY_ONLY",
            "finding_count": len(aggregate["findings"]),
            "aggregate_ref": {
                key: aggregate_ref[key] for key in ("path", "hash", "version")
            },
            "dispositions_ref": {
                key: dispositions_ref[key] for key in ("path", "hash", "version")
            },
        }
        stage, after_tree_hash, review_hash = self._prepare_candidate_finalize_stage(
            run_id, archived, companion
        )
        generation = int((state.get("current_candidate_ref") or {}).get("generation", 1))
        history = (
            self.run_path(run_id)
            / "candidate-generations"
            / f"generation-{generation}"
            / archived.path.name
        )
        result = {
            "schema_version": "node-result.v1",
            "node_id": "review.finalize",
            "attempt_id": attempt_id,
            "producer": {
                "kind": "DETERMINISTIC_PROGRAM",
                "component": "state-controller",
            },
            "mechanical_output": {
                "status": "PASS",
                "validator": "review_finalize",
                "source_attempt_id": prior["attempt_id"],
                "finding_count": len(aggregate["findings"]),
            },
            "artifact_refs": [
                {
                    "role": "review_companion",
                    "path": archived.review_path.relative_to(self.project_root).as_posix(),
                    "hash": review_hash,
                    "version": archived.version,
                },
                controller_subject_ref("review_aggregate", aggregate_ref),
                controller_subject_ref("review_dispositions", dispositions_ref),
            ],
        }
        result_path = self._result_path(run_id, attempt_id)
        if result_path.exists():
            if read_json(result_path) != result:
                raise StateConflict("review finalize result identity conflict")
            receipt_path = result_path.with_name("result-receipt.json")
            if not receipt_path.is_file() or read_json(receipt_path).get("result_hash") != sha256_file(result_path):
                raise StateConflict("review finalize result receipt is incomplete")
        else:
            self._persist_result(run_id, result, controller_owned=True, failpoint=failpoint)

        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["last_completed_node"] = "review.finalize"
        next_state["current_node"] = "prd.ready.gate"
        next_state["next_allowed_nodes"] = self.edges.get("prd.ready.gate", [])
        next_state["consumed_attempts"].append(attempt_id)
        self._bind_committed_outputs(next_state, run_id, attempt_id, result)
        next_state["current_candidate_ref"] = {
            **state["current_candidate_ref"],
            "tree_hash": after_tree_hash,
            "review_hash": review_hash,
            "generation": generation + 1,
        }
        next_state["artifact_refs"]["prd-candidate"] = {
            **next_state["current_candidate_ref"]
        }
        transaction_id = f"review-finalize-{attempt_id}"
        event = self._state_commit_event({
            "event_id": f"state-transaction:{run_id}:{transaction_id}",
            "event_type": "REVIEW_FINALIZE_COMMITTED",
            "actor": "state-controller",
            "run_id": run_id,
            "state_version": next_state["state_version"],
            "attempt_id": attempt_id,
            "candidate_generation": generation + 1,
            "before_tree_hash": archived.tree_hash,
            "after_tree_hash": after_tree_hash,
        }, state, next_state)
        journal = {
            "schema_version": "state-transaction.v1",
            "transaction_id": transaction_id,
            "run_id": run_id,
            "status": "PREPARED",
            "before_state_hash": self._state_hash(state),
            "after_state_hash": self._state_hash(next_state),
            "after_state": next_state,
            "event": event,
            "candidate_publish": {
                "stage_path": str(stage),
                "target_path": str(archived.path),
                "history_path": str(history),
                "before_tree_hash": archived.tree_hash,
                "after_tree_hash": after_tree_hash,
            },
        }
        journal_path = self._transaction_path(run_id, transaction_id)
        if journal_path.exists() and read_json(journal_path) != journal:
            raise StateConflict("review finalize transaction identity conflict")
        if not journal_path.exists():
            atomic_write_json(journal_path, journal)
        self._validate_candidate_finalize_transaction(journal)
        if failpoint is not None:
            failpoint("after_candidate_finalize_staged")
        append_event(self._events_path(run_id), event)
        if failpoint is not None:
            failpoint("after_candidate_finalize_event")
        atomic_write_json(self._state_path(run_id), next_state)
        if failpoint is not None:
            failpoint("after_candidate_finalize_state")
        self._publish_candidate_finalize_transaction(journal)
        if failpoint is not None:
            failpoint("after_candidate_finalize_publish")
        atomic_write_json(journal_path, {**journal, "status": "COMMITTED"})
        return next_state

    def _verify_ready_release_authority(
        self,
        run_id: str,
        state: dict[str, Any],
        archived: Any,
        assertion: dict[str, Any],
    ) -> None:
        from .documents import hash_tree
        from .receipts import verify_controller_receipt

        candidate = state.get("current_candidate_ref")
        attempts = [
            item
            for item in state.get("dispatch_attempts", [])
            if item.get("node_id") == "prd.ready.gate"
            and item.get("status") == "DISPATCHED"
            and item.get("authorized_state_version") == state["state_version"]
        ]
        receipt_refs = assertion.get("controller_receipts")
        required_kinds = {
            "audit_integrity",
            "document_experience",
            "mechanical_contracts",
            "review_finalize",
        }
        if (
            state.get("status") != "ACTIVE"
            or state.get("current_node") != "prd.ready.gate"
            or len(attempts) != 1
            or not isinstance(candidate, dict)
            or archived.status != "CANDIDATE_ARCHIVED"
            or archived.path.is_symlink()
            or hash_tree(archived.path) != archived.tree_hash
            or candidate.get("path")
            != archived.document_path.relative_to(self.project_root).as_posix()
            or candidate.get("hash") != archived.document_hash
            or candidate.get("tree_hash") != archived.tree_hash
            or candidate.get("artifact_path")
            != archived.path.relative_to(self.project_root).as_posix()
            or candidate.get("review_path")
            != archived.review_path.relative_to(self.project_root).as_posix()
            or candidate.get("review_hash") != archived.review_hash
            or candidate.get("version") != archived.version
            or assertion.get("status") != "READY"
            or assertion.get("run_id") != run_id
            or assertion.get("gate_attempt_id") != attempts[0]["attempt_id"]
            or assertion.get("state_version") != state["state_version"]
            or assertion.get("rules_version") != READY_RULES_VERSION
            or assertion.get("candidate_hash") != archived.document_hash
            or assertion.get("candidate_tree_hash") != archived.tree_hash
            or assertion.get("review_companion_hash") != archived.review_hash
            or not isinstance(receipt_refs, dict)
            or set(receipt_refs) != required_kinds
        ):
            raise TransitionRejected(
                "release READY Assertion does not bind exact Run/Candidate/Gate authority"
            )
        attempt_id = attempts[0]["attempt_id"]
        result_path = self._result_path(run_id, attempt_id)
        result_receipt_path = result_path.with_name("result-receipt.json")
        if not result_path.is_file() or not result_receipt_path.is_file():
            raise TransitionRejected("release requires persisted Controller Gate result")
        result = read_json(result_path)
        result_receipt = read_json(result_receipt_path)
        if (
            result_receipt.get("result_hash") != sha256_file(result_path)
            or result.get("node_id") != "prd.ready.gate"
            or result.get("attempt_id") != attempt_id
            or result.get("producer", {}).get("kind") != "DETERMINISTIC_PROGRAM"
            or result.get("mechanical_output", {}).get("status") != "PASS"
            or result.get("mechanical_output", {}).get("validator") != "prd_ready_gate"
            or result.get("mechanical_output", {}).get("controller_receipts") != receipt_refs
        ):
            raise TransitionRejected("release Controller Gate result is missing, stale, or forged")
        self._validate_exact_dispatch_result(state, result, attempts[0])
        for kind in sorted(required_kinds):
            try:
                ref = receipt_refs[kind]
                path = resolve_file_ref(self.project_root, ref, f"{kind} release receipt")
                receipt = read_json(path)
                verified = verify_controller_receipt(
                    self.project_root,
                    ref,
                    kind,
                    receipt.get("subject_refs", []),
                    expected_run_id=run_id,
                    expected_node_id="prd.ready.gate",
                    expected_attempt_id=attempts[0]["attempt_id"],
                    expected_candidate_ref=candidate,
                )
                reevaluated = evaluate_receipt_subjects(
                    self.project_root,
                    kind,
                    verified["subject_refs"],
                    run_id=run_id,
                    node_id="prd.ready.gate",
                    attempt_id=attempts[0]["attempt_id"],
                    candidate_ref=candidate,
                    template_selection=self._template_selection_for_receipt(
                        kind, candidate, state
                    ),
                )
            except ReceiptError as error:
                raise TransitionRejected(f"{kind} release receipt invalid: {error}") from error
            if verified.get("evaluation") != reevaluated:
                raise TransitionRejected(f"{kind} receipt fact evaluation changed before release")

    def _prepare_release_stage(
        self, run_id: str, archived: Any, assertion: dict[str, Any]
    ) -> tuple[Path, str]:
        from .documents import hash_tree

        stage = assert_managed_path(
            self.project_root,
            self.run_path(run_id) / "release-staging" / archived.path.name,
        )
        if stage.exists():
            assertion_path = stage / "READY_ASSERTION.json"
            source_inventory = {
                path.relative_to(archived.path).as_posix(): sha256_file(path)
                for path in archived.path.rglob("*")
                if path.is_file()
            }
            stage_inventory = {
                path.relative_to(stage).as_posix(): sha256_file(path)
                for path in stage.rglob("*")
                if path.is_file() and path != assertion_path
            }
            if (
                stage.is_symlink()
                or not assertion_path.is_file()
                or assertion_path.is_symlink()
                or read_json(assertion_path) != assertion
                or stage_inventory != source_inventory
            ):
                raise StateConflict("release stage identity conflict")
            return stage, hash_tree(stage)
        stage.parent.mkdir(parents=True, exist_ok=True)
        temporary = stage.parent / f".{stage.name}.tmp-{uuid4().hex}"
        try:
            shutil.copytree(archived.path, temporary)
            atomic_write_json(temporary / "READY_ASSERTION.json", assertion)
            os.replace(temporary, stage)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return stage, hash_tree(stage)

    def _validate_release_transaction(
        self, journal: dict[str, Any]
    ) -> tuple[Path, Path, Any]:
        from .documents import hash_tree

        publish = journal["release_publish"]
        stage = assert_managed_path(self.project_root, Path(publish["stage_path"]))
        target = assert_managed_path(self.project_root, Path(publish["target_path"]))
        stage.relative_to(self.run_path(journal["run_id"]) / "release-staging")
        target.relative_to(self.project_root / "artifacts" / "prds" / "released")
        archived = self._artifact_from_record(publish["archived"])
        archive_path = assert_managed_path(self.project_root, archived.path)
        archive_path.relative_to(self.project_root / "artifacts" / "prds" / "archived")
        assertion = publish["ready_assertion"]
        after_state = journal["after_state"]
        release_ref = after_state.get("release_ref")
        assertion_source = (
            target / "READY_ASSERTION.json"
            if target.exists()
            else stage / "READY_ASSERTION.json"
        )
        if (
            not (stage.name == target.name == archive_path.name)
            or archived.document_path.parent != archive_path
            or archived.review_path.parent != archive_path
            or archived.status != "CANDIDATE_ARCHIVED"
            or not archive_path.is_dir()
            or archive_path.is_symlink()
            or hash_tree(archive_path) != archived.tree_hash
            or assertion.get("status") != "READY"
            or assertion.get("run_id") != journal["run_id"]
            or assertion.get("candidate_hash") != archived.document_hash
            or assertion.get("candidate_tree_hash") != archived.tree_hash
            or assertion.get("review_companion_hash") != archived.review_hash
            or assertion.get("rules_version") != READY_RULES_VERSION
            or assertion.get("state_version") != after_state.get("state_version", 0) - 1
            or assertion.get("gate_attempt_id") not in after_state.get("consumed_attempts", [])
            or not isinstance(release_ref, dict)
            or journal.get("event", {}).get("release_ref") != release_ref
            or release_ref.get("path")
            != (target / "READY_ASSERTION.json").relative_to(self.project_root).as_posix()
            or release_ref.get("candidate_hash") != archived.document_hash
            or release_ref.get("candidate_tree_hash") != publish.get("tree_hash")
            or release_ref.get("review_companion_hash") != archived.review_hash
            or release_ref.get("artifact_path")
            != target.relative_to(self.project_root).as_posix()
            or release_ref.get("version") != archived.version
            or not assertion_source.is_file()
            or assertion_source.is_symlink()
            or read_json(assertion_source) != assertion
            or release_ref.get("hash") != sha256_file(assertion_source)
        ):
            raise StateConflict("release transaction archive identity changed")
        if not target.exists():
            if not stage.is_dir() or stage.is_symlink() or hash_tree(stage) != publish["tree_hash"]:
                raise StateConflict("release transaction stage is missing or changed")
        elif target.is_symlink() or hash_tree(target) != publish["tree_hash"]:
            raise StateConflict("published release differs from transaction identity")
        return stage, target, archived

    def _publish_release_transaction(self, journal: dict[str, Any]) -> Any:
        from .documents import hash_tree, release_prd_candidate

        publish = journal["release_publish"]
        stage, target, archived = self._validate_release_transaction(journal)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage, target)
        if target.is_symlink() or hash_tree(target) != publish["tree_hash"]:
            raise StateConflict("published release differs from transaction identity")
        released = release_prd_candidate(
            self.project_root,
            archived,
            ready_assertion=publish["ready_assertion"],
        )
        if released.tree_hash != publish["tree_hash"]:
            raise StateConflict("published release tree changed during reconciliation")
        return released

    @serialized_run_mutation
    def commit_ready_release(
        self,
        run_id: str,
        archived: Any,
        assertion: dict[str, Any],
        *,
        expected_state_version: int,
        failpoint: Callable[[str], None] | None = None,
    ) -> Any:
        """Commit Ready state before atomically publishing one recoverable release."""

        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        transaction_id = f"ready-release-{archived.path.name}"
        journal_path = self._transaction_path(run_id, transaction_id)
        if journal_path.exists():
            journal = read_json(journal_path)
            publish = journal.get("release_publish", {})
            if (
                journal.get("run_id") != run_id
                or journal.get("transaction_id") != transaction_id
                or publish.get("archived") != self._artifact_record(archived)
                or publish.get("ready_assertion") != assertion
            ):
                raise StateConflict("release transaction identity conflict")
            current_hash = self._state_hash(state)
            if current_hash == journal.get("before_state_hash"):
                self._verify_ready_release_authority(run_id, state, archived, assertion)
                self._validate_release_transaction(journal)
                append_event(self._events_path(run_id), journal["event"])
                atomic_write_json(self._state_path(run_id), journal["after_state"])
            elif current_hash != journal.get("after_state_hash"):
                raise StateConflict("release transaction state authority changed")
            else:
                self._validate_release_transaction(journal)
            released = self._publish_release_transaction(journal)
            atomic_write_json(journal_path, {**journal, "status": "COMMITTED"})
            return released
        self._verify_ready_release_authority(run_id, state, archived, assertion)
        stage, released_tree_hash = self._prepare_release_stage(run_id, archived, assertion)
        target = assert_managed_path(
            self.project_root,
            self.project_root / "artifacts" / "prds" / "released" / archived.path.name,
        )
        assertion_path = target / "READY_ASSERTION.json"
        release_ref = {
            "path": assertion_path.relative_to(self.project_root).as_posix(),
            "hash": sha256_file(stage / "READY_ASSERTION.json"),
            "candidate_hash": archived.document_hash,
            "candidate_tree_hash": released_tree_hash,
            "review_companion_hash": archived.review_hash,
            "artifact_path": target.relative_to(self.project_root).as_posix(),
            "version": archived.version,
        }
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["status"] = "RELEASED"
        next_state["last_completed_node"] = "prd.ready.gate"
        next_state["current_node"] = "handoff.prepare"
        next_state["next_allowed_nodes"] = self.edges.get("handoff.prepare", [])
        next_state["release_ref"] = release_ref
        gate_attempt_id = assertion["gate_attempt_id"]
        if gate_attempt_id not in next_state["consumed_attempts"]:
            next_state["consumed_attempts"].append(gate_attempt_id)
            self._bind_committed_outputs(
                next_state,
                run_id,
                gate_attempt_id,
                read_json(self._result_path(run_id, gate_attempt_id)),
            )
        event = self._state_commit_event({
            "event_id": f"state-transaction:{run_id}:{transaction_id}",
            "event_type": "PRD_RELEASE_COMMITTED",
            "actor": "state-controller",
            "run_id": run_id,
            "state_version": next_state["state_version"],
            "release_ref": release_ref,
        }, state, next_state)
        journal = {
            "schema_version": "state-transaction.v1",
            "transaction_id": transaction_id,
            "run_id": run_id,
            "status": "PREPARED",
            "before_state_hash": self._state_hash(state),
            "after_state_hash": self._state_hash(next_state),
            "after_state": next_state,
            "event": event,
            "release_publish": {
                "stage_path": str(stage),
                "target_path": str(target),
                "tree_hash": released_tree_hash,
                "archived": self._artifact_record(archived),
                "ready_assertion": assertion,
            },
        }
        atomic_write_json(journal_path, journal)
        self._validate_release_transaction(journal)
        if failpoint is not None:
            failpoint("after_release_staged")
        append_event(self._events_path(run_id), event)
        if failpoint is not None:
            failpoint("after_release_event")
        atomic_write_json(self._state_path(run_id), next_state)
        if failpoint is not None:
            failpoint("after_release_state")
        released = self._publish_release_transaction(journal)
        if failpoint is not None:
            failpoint("after_release_publish")
        atomic_write_json(journal_path, {**journal, "status": "COMMITTED"})
        return released

    @serialized_run_mutation
    def complete_local_handoff(
        self,
        run_id: str,
        receipt_ref: dict[str, Any],
        *,
        expected_state_version: int,
    ) -> dict[str, Any]:
        """Verify one exact local-only packet and commit the Graph terminal."""

        state = self.load_state(run_id)
        try:
            packet_path = assert_managed_path(
                self.project_root, self.project_root / receipt_ref["path"]
            )
            packet_path.relative_to(
                self.project_root / ".better-product-graph" / "handoffs" / "local"
            )
        except (KeyError, ValueError, RuntimeError) as error:
            raise TransitionRejected("local Handoff receipt escapes Controller path") from error
        if (
            packet_path.name != f"handoff-{run_id}.json"
            or not packet_path.is_file()
            or packet_path.is_symlink()
            or sha256_file(packet_path) != receipt_ref.get("hash")
        ):
            raise TransitionRejected("local Handoff receipt is missing or changed")
        packet = read_json(packet_path)
        handoff_ref = {
            "path": packet_path.relative_to(self.project_root).as_posix(),
            "hash": sha256_file(packet_path),
            "version": 1,
            "delivery": "LOCAL_ONLY",
            "sent_remote": False,
        }
        if state.get("status") == "COMPLETED":
            if (
                state.get("current_node") != "handoff.dispatch"
                or state.get("handoff_ref") != handoff_ref
            ):
                raise StateConflict("Run is already completed by a different Handoff")
            return state
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        if (
            state.get("status") != "RELEASED"
            or state.get("current_node") != "handoff.prepare"
            or not isinstance(state.get("release_ref"), dict)
            or packet.get("id") != f"handoff-{run_id}"
            or packet.get("run_id") != run_id
            or packet.get("state_version") != state["state_version"]
            or packet.get("status") != "RELEASED"
            or packet.get("current_node") != "handoff.prepare"
            or packet.get("release_ref") != state["release_ref"]
            or packet.get("remote_delivery") != "NOT_CONFIGURED"
        ):
            raise TransitionRejected("local Handoff packet does not bind exact Released Run")
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["status"] = "COMPLETED"
        next_state["last_completed_node"] = "handoff.prepare"
        next_state["current_node"] = "handoff.dispatch"
        next_state["next_allowed_nodes"] = []
        next_state["handoff_ref"] = handoff_ref
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "HANDOFF_LOCAL_COMMITTED",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "handoff_ref": handoff_ref,
                "release_ref": state["release_ref"],
            },
            transaction_id="handoff-local-completed",
        )

    @serialized_run_mutation
    def complete_bug_handoff(
        self,
        run_id: str,
        bug_id: str,
        packet_ref: dict[str, Any],
        human_ref: dict[str, Any],
        *,
        expected_state_version: int,
    ) -> dict[str, Any]:
        """Verify one exact Bug Delivery Packet and commit the local terminal."""

        state = self.load_state(run_id)
        handoff_ref = {
            "role": "bug_delivery_packet",
            "path": packet_ref.get("path"),
            "hash": packet_ref.get("hash"),
            "version": packet_ref.get("version"),
            "delivery_kind": "BUG",
            "delivery": "LOCAL_ONLY",
            "sent_remote": False,
        }
        exact_human_ref = {
            "role": "bug_human_view",
            "path": human_ref.get("path"),
            "hash": human_ref.get("hash"),
            "version": human_ref.get("version"),
        }
        if state.get("status") == "COMPLETED":
            if (
                state.get("current_node") != "handoff.dispatch"
                or state.get("handoff_ref") != handoff_ref
                or state.get("bug_human_ref") != exact_human_ref
            ):
                raise StateConflict("Run is already completed by a different Handoff")
            return state
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        if (
            state.get("status") != "ACTIVE"
            or state.get("current_node") != "handoff.prepare"
            or state.get("last_completed_node") != "bug.baseline.check"
            or state.get("release_ref") is not None
        ):
            raise TransitionRejected(
                "Bug Handoff requires one active implementation-deviation Run at handoff.prepare"
            )
        expected_packet_path = (
            Path(".better-product-graph")
            / "bugs"
            / bug_id
            / "bug.delivery.packet.v1.json"
        ).as_posix()
        expected_human_path = (
            Path(".better-product-graph") / "bugs" / bug_id / "BUG_v1.md"
        ).as_posix()
        if (
            packet_ref.get("role") != "bug_delivery_packet"
            or packet_ref.get("path") != expected_packet_path
            or packet_ref.get("version") != 1
            or human_ref.get("role") != "bug_human_view"
            or human_ref.get("path") != expected_human_path
            or human_ref.get("version") != 1
        ):
            raise TransitionRejected("Bug Handoff refs do not bind the managed Bug packet")
        self._validate_single_artifact_ref(packet_ref)
        self._validate_single_artifact_ref(human_ref)
        result_refs = [
            ref
            for ref in state.get("artifact_refs", {}).values()
            if isinstance(ref, dict)
            and ref.get("role") == "node_result"
            and ref.get("node_id") == "bug.baseline.check"
            and ref.get("attempt_id") in state.get("consumed_attempts", [])
        ]
        if len(result_refs) != 1:
            raise TransitionRejected(
                "Bug Handoff requires one exact committed Bug Baseline result"
            )
        result_ref = result_refs[0]
        self._validate_single_artifact_ref(result_ref)
        result = read_json(self.project_root / result_ref["path"])
        assessment = validate_bug_assessment(result)
        if assessment.get("classification") != "IMPLEMENTATION_DEVIATION":
            raise TransitionRejected(
                "only IMPLEMENTATION_DEVIATION can use the lightweight Bug Handoff"
            )
        packet = read_json(self.project_root / packet_ref["path"])
        expected_provenance = {
            "attempt_id": result["attempt_id"],
            "instruction_ref": result["instruction_ref"],
            "instruction_hash": result["instruction_hash"],
            "input_refs": result["input_refs"],
            "input_hashes": result["input_hashes"],
        }
        if (
            packet.get("schema_version") != "bug.delivery.packet.v1"
            or packet.get("bug_id") != bug_id
            or packet.get("classification") != "IMPLEMENTATION_DEVIATION"
            or packet.get("delivery_profile") != "LIGHT"
            or packet.get("assessment") != assessment
            or packet.get("provenance") != expected_provenance
            or packet.get("handoff")
            != {"mode": "LOCAL_ONLY", "remote_status": "NOT_CONFIGURED"}
        ):
            raise TransitionRejected(
                "Bug Delivery Packet does not bind the exact committed Bug assessment"
            )
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["status"] = "COMPLETED"
        next_state["last_completed_node"] = "handoff.prepare"
        next_state["current_node"] = "handoff.dispatch"
        next_state["next_allowed_nodes"] = []
        next_state["handoff_ref"] = handoff_ref
        next_state["bug_human_ref"] = exact_human_ref
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "HANDOFF_LOCAL_COMMITTED",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "handoff_ref": handoff_ref,
                "bug_human_ref": exact_human_ref,
                "bug_result_ref": result_ref,
            },
            transaction_id="handoff-local-bug-completed",
        )

    @serialized_run_mutation
    def issue_controller_receipt(
        self,
        run_id: str,
        receipt_id: str,
        kind: str,
        subject_refs: list[dict[str, Any]],
        *,
        expected_state_version: int,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Issue one immutable kind-specific receipt and register it in state+ledger."""

        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        if state["status"] != "ACTIVE" or state["current_node"] != "prd.ready.gate":
            raise TransitionRejected(
                "Controller receipt lifecycle requires ACTIVE prd.ready.gate"
            )
        candidate_ref = state.get("current_candidate_ref")
        if not isinstance(candidate_ref, dict) or not all(
            candidate_ref.get(field)
            for field in ("path", "hash", "version", "artifact_path", "tree_hash")
        ):
            raise TransitionRejected("Controller receipt requires the exact current Candidate")
        attempts = [
            item
            for item in state["dispatch_attempts"]
            if item.get("node_id") == "prd.ready.gate"
            and item.get("status") == "DISPATCHED"
            and item.get("authorized_state_version") == state["state_version"]
        ]
        if len(attempts) != 1:
            raise TransitionRejected(
                "Controller receipt requires one exact current prd.ready.gate attempt"
            )
        attempt = attempts[0]
        try:
            normalized = normalize_subject_refs(self.project_root, kind, subject_refs)
            authorized = {
                (ref.get("path"), ref.get("hash"))
                for ref in state.get("artifact_refs", {}).values()
            }
            candidate_root = (self.project_root / candidate_ref["artifact_path"]).resolve()
            for subject in normalized:
                subject_path = (self.project_root / subject["path"]).resolve()
                if (
                    (subject["path"], subject["hash"]) not in authorized
                    and subject.get("role") != "candidate_document"
                    and candidate_root not in subject_path.parents
                ):
                    raise ReceiptError(
                        f"{kind} subject {subject['role']} is not an authorized current Run artifact"
                    )
            evaluation = evaluate_receipt_subjects(
                self.project_root,
                kind,
                normalized,
                run_id=run_id,
                node_id=state["current_node"],
                attempt_id=attempt["attempt_id"],
                candidate_ref=candidate_ref,
                template_selection=self._template_selection_for_receipt(
                    kind, candidate_ref, state
                ),
            )
        except ReceiptError as error:
            raise TransitionRejected(str(error)) from error
        path = self.run_path(run_id) / "receipts" / f"{receipt_id}.json"
        if path.exists():
            existing = read_json(path)
            expected_existing = {
                "schema_version": "controller-receipt.v1",
                "receipt_id": receipt_id,
                "run_id": run_id,
                "kind": kind,
                "issuer": "state-controller",
                "status": "PASS",
                "node_id": state["current_node"],
                "attempt_id": attempt["attempt_id"],
                "candidate_hash": candidate_ref["hash"],
                "candidate_version": candidate_ref["version"],
                "rules_version": READY_RULES_VERSION,
                "subject_refs": normalized,
                "evaluation": evaluation,
            }
            if (
                {key: value for key, value in existing.items() if key != "state_version"}
                != expected_existing
                or not isinstance(existing.get("state_version"), int)
                or existing["state_version"] > state["state_version"]
            ):
                raise StateConflict(f"receipt identity conflict: {receipt_id}")
        else:
            payload = build_receipt_payload(
                receipt_id,
                run_id,
                kind,
                normalized,
                node_id=state["current_node"],
                attempt_id=attempt["attempt_id"],
                state_version=state["state_version"],
                candidate_ref=candidate_ref,
                evaluation=evaluation,
            )
            atomic_write_json(path, payload)
            if failpoint is not None:
                failpoint("after_receipt_persist")
        receipt_ref = {
            "path": path.relative_to(self.project_root).as_posix(),
            "hash": sha256_file(path),
            "version": 1,
            "kind": kind,
            "run_id": run_id,
            "node_id": state["current_node"],
            "attempt_id": attempt["attempt_id"],
            "candidate_hash": candidate_ref["hash"],
            "candidate_version": candidate_ref["version"],
            "rules_version": READY_RULES_VERSION,
        }
        append_event(
            self.run_path(run_id) / "receipt-ledger.jsonl",
            {
                "event_id": f"controller-receipt-ledger:{run_id}:{receipt_id}",
                "event_type": "CONTROLLER_RECEIPT_ISSUED",
                "actor": "state-controller",
                "run_id": run_id,
                "receipt_ref": receipt_ref,
            },
        )
        if failpoint is not None:
            failpoint("after_receipt_ledger")
        exact = [
            item for item in state["ready_receipts"]
            if item.get("path") == receipt_ref["path"]
            and item.get("hash") == receipt_ref["hash"]
        ]
        if exact:
            if len(exact) != 1 or exact[0] != receipt_ref:
                raise StateConflict(f"receipt state identity conflict: {receipt_id}")
            return exact[0]
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["ready_receipts"].append(receipt_ref)
        for item in next_state["dispatch_attempts"]:
            if item["attempt_id"] == attempt["attempt_id"]:
                item["authorized_state_version"] = next_state["state_version"]
                item["authority_hash"] = self._dispatch_authority_hash(next_state)
        self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "CONTROLLER_RECEIPT_ISSUED",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "receipt_ref": receipt_ref,
            },
            transaction_id=f"receipt-{receipt_id}",
        )
        return receipt_ref

    @serialized_run_mutation
    def register_fanout_plan(
        self,
        run_id: str,
        plan_ref: dict[str, Any],
        *,
        expected_state_version: int,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Register an immutable dispatch plan after it is durable and before any call."""

        state = self.load_state(run_id)
        if expected_state_version != state["state_version"]:
            raise StateConflict(
                f"expected state version {expected_state_version}, current is {state['state_version']}"
            )
        self._validate_single_artifact_ref(plan_ref)
        if any(item["plan_id"] == plan_ref.get("plan_id") for item in state["fanout_plans"]):
            raise StateConflict(f"fanout plan already registered: {plan_ref.get('plan_id')}")
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["fanout_plans"].append(plan_ref)
        self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "FANOUT_PLAN_REGISTERED",
                "actor": "state-controller",
                "run_id": run_id,
                "state_version": next_state["state_version"],
                "plan_ref": plan_ref,
            },
            transaction_id=f"fanout-plan-{plan_ref['plan_id']}",
            failpoint=failpoint,
        )
        return next_state

    def _reject(self, run_id: str, reason: str, request: dict[str, Any]) -> None:
        append_event(
            self._events_path(run_id),
            {
                "event_type": "TRANSITION_REJECTED",
                "actor": "state-controller",
                "run_id": run_id,
                "reason": reason,
                "requested_node": request.get("requested_node"),
                "attempt_id": request.get("attempt_id"),
            },
        )
        raise TransitionRejected(reason)

    def _validate_artifact_refs(self, result: dict[str, Any]) -> None:
        refs = result.get("artifact_refs", [])
        if not isinstance(refs, list):
            raise TransitionRejected("artifact_refs must be a list")
        for ref in refs:
            version = ref.get("version") if isinstance(ref, dict) else None
            if (
                not isinstance(ref, dict)
                or not isinstance(ref.get("role"), str)
                or not ref["role"].strip()
                or not isinstance(ref.get("path"), str)
                or not ref["path"].strip()
                or not isinstance(ref.get("hash"), str)
                or not ref["hash"].startswith("sha256:")
                or isinstance(version, bool)
                or not (
                    isinstance(version, int) and version > 0
                    or isinstance(version, str) and bool(version.strip())
                )
            ):
                raise TransitionRejected(
                    "Node Result artifact ref requires exact non-empty "
                    "role/path/hash/version. Correct the payload and resubmit "
                    "the same attempt_id."
                )
            self._validate_single_artifact_ref(ref)

    def _validate_single_artifact_ref(self, ref: dict[str, Any]) -> None:
        repair = (
            "Compute hashes from the final artifact bytes, correct the payload, "
            "and resubmit the same attempt_id."
        )
        if (
            not isinstance(ref, dict)
            or not isinstance(ref.get("path"), str)
            or not ref["path"].strip()
            or not isinstance(ref.get("hash"), str)
            or not ref["hash"].startswith("sha256:")
        ):
            raise TransitionRejected(
                "artifact ref requires exact non-empty path/hash. " + repair
            )
        try:
            candidate = assert_managed_path(
                self.project_root, self.project_root / ref["path"]
            )
        except IntegrityError as error:
            raise TransitionRejected(
                f"artifact ref escapes project root or contains a symlink: {ref['path']}. "
                + repair
            ) from error
        if not candidate.is_file() or sha256_file(candidate) != ref["hash"]:
            raise TransitionRejected(
                f"artifact ref missing or hash mismatch: {ref['path']}. " + repair
            )

    def _validated_prd_candidate_ref(self, result: dict[str, Any]) -> dict[str, Any]:
        from .documents import hash_tree

        refs = [
            item
            for item in result.get("artifact_refs", [])
            if item.get("role") == "prd_candidate"
        ]
        if len(refs) != 1:
            raise TransitionRejected(
                "PRD authoring must commit exactly one Controller-archived Candidate ref"
            )
        ref = refs[0]
        try:
            document_path = assert_managed_path(
                self.project_root, self.project_root / ref["path"]
            )
            artifact_path = assert_managed_path(
                self.project_root, self.project_root / ref["artifact_path"]
            )
            review_path = assert_managed_path(
                self.project_root, self.project_root / ref["review_path"]
            )
            artifact_path.relative_to(
                self.project_root / "artifacts" / "prds" / "archived"
            )
            document_path.relative_to(artifact_path)
            review_path.relative_to(artifact_path)
        except (KeyError, ValueError) as error:
            raise TransitionRejected(
                "PRD Candidate is outside the managed archive"
            ) from error
        if (
            artifact_path.is_symlink()
            or not artifact_path.is_dir()
            or document_path.is_symlink()
            or review_path.is_symlink()
            or not document_path.is_file()
            or not review_path.is_file()
            or sha256_file(document_path) != ref.get("hash")
            or sha256_file(review_path) != ref.get("review_hash")
            or hash_tree(artifact_path) != ref.get("tree_hash")
        ):
            raise TransitionRejected("archived PRD Candidate hash set is invalid")
        output = result.get("semantic_output", {})
        if sha256_bytes(output.get("document_markdown", "").encode()) != ref["hash"]:
            raise TransitionRejected("PRD Candidate bytes differ from Agent output")
        metadata = output.get("metadata", {})
        review = read_json(review_path)
        if (
            metadata.get("version") != ref.get("version")
            or review.get("candidate_hash") != ref["hash"]
            or review.get("version") != ref.get("version")
            or review.get("authority") != "ADVISORY_ONLY"
            or review.get("status") != "NOT_RUN"
        ):
            raise TransitionRejected(
                "PRD Candidate version or review companion is not exact"
            )
        return json.loads(canonical_json_bytes(ref))

    def _bind_committed_outputs(
        self,
        state: dict[str, Any],
        run_id: str,
        attempt_id: str,
        result: dict[str, Any],
    ) -> None:
        """Make exact committed outputs authoritative inputs for following nodes."""

        result_path = self._result_path(run_id, attempt_id)
        result_ref = {
            "role": "node_result",
            "path": result_path.relative_to(self.project_root).as_posix(),
            "hash": sha256_file(result_path),
            "version": 1,
            "node_id": result["node_id"],
            "attempt_id": attempt_id,
        }
        state["artifact_refs"][f"node-result:{attempt_id}"] = result_ref
        for index, ref in enumerate(result.get("artifact_refs", [])):
            exact = json.loads(canonical_json_bytes(ref))
            exact["origin_node_id"] = result["node_id"]
            exact["origin_attempt_id"] = attempt_id
            key = f"node-output:{attempt_id}:{index}:{exact.get('role', 'artifact')}"
            state["artifact_refs"][key] = exact

    @serialized_run_mutation
    def transition(
        self,
        run_id: str,
        request: dict[str, Any],
        *,
        failpoint: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        forbidden = sorted(FORBIDDEN_REQUEST_FIELDS & set(request))
        if forbidden:
            self._reject(run_id, f"transition request contains forbidden field {forbidden[0]}", request)
        state = self.load_state(run_id)
        if request.get("expected_state_version") != state["state_version"]:
            raise StateConflict(
                f"expected state version {request.get('expected_state_version')}, current is {state['state_version']}"
            )
        attempt_id = request.get("attempt_id")
        result_path = self._result_path(run_id, attempt_id)
        if not result_path.is_file():
            self._reject(run_id, f"persisted attempt not found: {attempt_id}", request)
        result = read_json(result_path)
        receipt_path = result_path.with_name("result-receipt.json")
        if not receipt_path.is_file():
            self._reject(run_id, "Controller result receipt is missing", request)
        receipt = read_json(receipt_path)
        if receipt.get("result_hash") != sha256_file(result_path):
            self._reject(run_id, "result receipt hash mismatch", request)
        try:
            self.schemas.validate("node-result.schema.json", result)
            validate_node_result_producer(result)
            validate_node_output(state["current_node"], result)
            self._validate_exact_dispatch_result(state, result)
        except (
            SchemaValidationError,
            PolicyViolation,
            NodeValidationError,
            TransitionRejected,
            ValueError,
        ) as error:
            self._reject(run_id, f"persisted result invalid: {error}", request)
        if result["node_id"] != state["current_node"]:
            self._reject(
                run_id,
                f"attempt node {result['node_id']} does not match current node {state['current_node']}",
                request,
            )
        if attempt_id in state["consumed_attempts"]:
            self._reject(run_id, f"attempt already consumed: {attempt_id}", request)
        if (
            state["current_node"] == "problem.ready.gate"
            and result.get("mechanical_output", {}).get("status") != "READY"
        ):
            self._reject(
                run_id,
                "problem.ready.gate NOT_READY cannot advance to Product Decision; "
                "follow its exact deterministic repair target",
                request,
            )
        requested_node = request.get("requested_node")
        allowed = self.edges.get(state["current_node"], [])
        if requested_node not in allowed:
            self._reject(
                run_id,
                f"requested node {requested_node!r} is not allowed from {state['current_node']}",
                request,
            )
        if state["current_node"] == "review.aggregate":
            self.validate_review_aggregate_route(
                run_id, state, result, requested_node
            )
        verify_event_chain(self._events_path(run_id))
        self._validate_artifact_refs(result)
        candidate_ref = (
            self._validated_prd_candidate_ref(result)
            if state["current_node"] in {"prd.generate", "prd.optimize"}
            else None
        )
        if failpoint is not None:
            failpoint("before_transition")
        next_state = json.loads(canonical_json_bytes(state))
        next_state["state_version"] += 1
        next_state["last_completed_node"] = state["current_node"]
        next_state["current_node"] = requested_node
        next_state["next_allowed_nodes"] = self.edges.get(requested_node, [])
        next_state["consumed_attempts"].append(attempt_id)
        self._bind_committed_outputs(next_state, run_id, attempt_id, result)
        if candidate_ref is not None:
            next_state["candidate_version"] += 1
            next_state["current_candidate_ref"] = {
                **candidate_ref,
                "generation": next_state["candidate_version"],
            }
            next_state["artifact_refs"]["prd-candidate"] = {
                "role": "prd_candidate",
                **next_state["current_candidate_ref"],
            }
            if state["current_node"] == "prd.generate" and isinstance(
                next_state.get("scope_reconciliation"), dict
            ):
                next_state.pop("scope_reconciliation", None)
                next_state.pop("planning_intent", None)
        return self._commit_state_event(
            run_id,
            state,
            next_state,
            {
                "event_type": "NODE_TRANSITION_COMMITTED",
                "actor": "state-controller",
                "run_id": run_id,
                "from_node": state["current_node"],
                "to_node": requested_node,
                "attempt_id": attempt_id,
                "before_state_version": state["state_version"],
                "after_state_version": next_state["state_version"],
            },
            transaction_id=f"transition-{attempt_id}",
            failpoint=failpoint,
            after_event_phase="after_transition",
        )
