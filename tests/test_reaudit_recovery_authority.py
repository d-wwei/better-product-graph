from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.bpg.engine import HostEngine
from src.bpg.failpoints import (
    InjectedCrash,
    begin_node_call,
    crash_at,
    mark_dispatch_unknown,
    persist_node_dispatch,
)
from src.bpg.host_runtime import HostRuntime
from src.bpg.node_registry import NodeRegistry
from src.bpg.product_memory import persist_decision_proposal
from src.bpg.state_controller import StateController, TransitionRejected
from src.bpg.storage import (
    IntegrityError,
    _event_hash,
    append_event,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_file,
    verify_event_chain,
)
from tests.controller_fixtures import position_run_internal
from tests.test_owner_choice_routes import agent_draft, agent_submission, place_at_decision


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class PublicResumeAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        self.controller = StateController(self.project, GRAPH)
        self.engine = HostEngine(self.project, self.controller)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _planning_context_result(
        self,
        dispatch: dict,
        source_ref: dict,
    ) -> dict:
        return {
            "schema_version": "node-result.v1",
            "node_id": "planning.context.prepare",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "semantic_output": {
                "schema_version": "planning-context-preparation.v1",
                "status": "READY",
                "project_identity": {
                    "name": "source-freeze-test",
                    "root": ".",
                    "confidence": "HIGH",
                    "ambiguities": [],
                },
                "materials": [
                    {
                        "ref": source_ref,
                        "kind": "PROJECT_OVERVIEW",
                        "decision": "INCLUDE",
                        "reason": "提供当前项目方向",
                    }
                ],
                "unavailable_sources": [],
                "high_impact_gaps": [],
                "context_summary": {
                    "project_purpose": "验证规划来源冻结",
                    "current_direction": "使用冻结副本继续 Run",
                    "constraints": [],
                    "unknowns": [],
                },
                "review": {
                    "status": "CONFIRMED",
                    "reviewed_by": {"kind": "OWNER", "id": "tester"},
                },
                "limitations": [],
                "next_action": "evidence.collect",
            },
            "artifact_refs": [source_ref],
        }

    def test_planning_context_commit_freezes_live_source_for_following_nodes(self) -> None:
        runtime = HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core")
        run_id = "run-planning-source-freeze"
        runtime.controller.create_run(run_id, raw_signal="freeze planning context")
        position_run_internal(
            runtime.controller,
            run_id,
            "planning.context.prepare",
            ["evidence.collect"],
        )
        source = self.project / "README.md"
        source.write_text("original planning context\n", encoding="utf-8")
        source_ref = {
            "role": "planning_context_source",
            "path": "README.md",
            "hash": sha256_file(source),
            "version": 1,
        }
        dispatch = runtime.dispatch_current(run_id)

        advanced = runtime.submit_and_advance(
            run_id,
            self._planning_context_result(dispatch, source_ref),
            requested_node="evidence.collect",
        )

        state = runtime.controller.load_state(run_id)
        snapshots = [
            ref
            for ref in state["artifact_refs"].values()
            if ref.get("role") == "planning_context_snapshot"
        ]
        self.assertEqual(len(snapshots), 1)
        snapshot = snapshots[0]
        self.assertNotEqual(snapshot["path"], source_ref["path"])
        self.assertEqual(snapshot["hash"], source_ref["hash"])
        self.assertEqual(snapshot["source_ref"], source_ref)
        self.assertEqual(
            (self.project / snapshot["path"]).read_bytes(),
            b"original planning context\n",
        )
        self.assertIn(snapshot["path"], advanced["dispatch"]["input_refs"])
        self.assertNotIn(source_ref["path"], advanced["dispatch"]["input_refs"])

        source.write_text("later live project direction\n", encoding="utf-8")
        self.assertEqual(
            runtime.controller.authoritative_read_barrier(run_id)["status"],
            "ACTIVE",
        )

    def test_frozen_planning_context_tamper_still_blocks_authoritative_reads(self) -> None:
        runtime = HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core")
        run_id = "run-planning-snapshot-tamper"
        runtime.controller.create_run(run_id, raw_signal="detect frozen source tamper")
        position_run_internal(
            runtime.controller,
            run_id,
            "planning.context.prepare",
            ["evidence.collect"],
        )
        source = self.project / "README.md"
        source.write_text("trusted planning context\n", encoding="utf-8")
        source_ref = {
            "role": "planning_context_source",
            "path": "README.md",
            "hash": sha256_file(source),
            "version": 1,
        }
        dispatch = runtime.dispatch_current(run_id)
        runtime.submit_and_advance(
            run_id,
            self._planning_context_result(dispatch, source_ref),
            requested_node="evidence.collect",
        )
        snapshot = next(
            ref
            for ref in runtime.controller.load_state(run_id)["artifact_refs"].values()
            if ref.get("role") == "planning_context_snapshot"
        )
        (self.project / snapshot["path"]).write_text(
            "tampered snapshot\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(TransitionRejected, "planning_context_snapshot"):
            runtime.controller.authoritative_read_barrier(run_id)

    def test_completed_legacy_run_reports_source_drift_without_reopening_lifecycle(self) -> None:
        runtime = HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core")
        run_id = "run-completed-legacy-source"
        runtime.controller.create_run(run_id, raw_signal="legacy completed source drift")
        position_run_internal(
            runtime.controller,
            run_id,
            "planning.context.prepare",
            ["evidence.collect"],
        )
        source = self.project / ".assistant" / "project.md"
        source.parent.mkdir(parents=True)
        source.write_text("historical planning direction\n", encoding="utf-8")
        source_ref = {
            "role": "planning_context_source",
            "path": ".assistant/project.md",
            "hash": sha256_file(source),
            "version": 1,
        }
        planning_dispatch = runtime.dispatch_current(run_id)
        runtime.submit_and_advance(
            run_id,
            self._planning_context_result(planning_dispatch, source_ref),
            requested_node="evidence.collect",
        )
        active = runtime.controller.load_state(run_id)
        artifact_refs = {
            key: ref
            for key, ref in active["artifact_refs"].items()
            if ref.get("role") != "planning_context_snapshot"
        }
        legacy_ref = {
            **source_ref,
            "origin_node_id": "planning.context.prepare",
            "origin_attempt_id": planning_dispatch["attempt_id"],
        }
        artifact_refs["legacy-planning-source"] = legacy_ref
        position_run_internal(
            runtime.controller,
            run_id,
            "bug.baseline.check",
            ["handoff.prepare", "evidence.collect"],
            artifact_refs=artifact_refs,
        )
        dispatch = runtime.dispatch_current(run_id)
        baseline = self.project / "current-product-baseline.md"
        baseline.write_text("结算后总额必须持续可见。\n", encoding="utf-8")
        result = {
            "schema_version": "node-result.v1",
            "node_id": "bug.baseline.check",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "semantic_output": {
                "classification": "IMPLEMENTATION_DEVIATION",
                "baseline_ref": {
                    "path": str(baseline),
                    "hash": sha256_file(baseline),
                    "version": 1,
                },
                "expected": "结算后总额持续可见",
                "actual": "刷新后总额消失",
                "new_rule_required": False,
                "acceptance_criteria_decidable": True,
                "material_conflict": False,
                "next_action": "按已有基线修复并回归",
            },
            "artifact_refs": [],
        }
        completed = runtime.submit_and_advance(
            run_id,
            result,
            requested_node="handoff.prepare",
        )
        self.assertEqual(completed["status"], "COMPLETED")
        source.write_text("new unrelated project direction\n", encoding="utf-8")

        status = runtime.engine.handle(f"$better-product-graph status {run_id}")

        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["state"]["status"], "COMPLETED")
        self.assertEqual(status["historical_source_status"], "DEGRADED_SOURCE_DRIFT")
        self.assertEqual(
            status["historical_source_warnings"][0]["path"],
            legacy_ref["path"],
        )
        self.assertNotIn("resubmit", json.dumps(status["historical_source_warnings"]))

    def test_waiting_trigger_cannot_be_escaped_by_plain_public_resume(self) -> None:
        run_id = "run-wait-trigger"
        self.controller.create_run(run_id, raw_signal="wait for evidence")
        state = place_at_decision(self.controller, run_id)
        proposal = persist_decision_proposal(
            self.project, "decision-wait-trigger", run_id, agent_submission()
        )
        command = {
            "schema_version": "owner-choice-command.v1",
            "decision_id": proposal["decision_id"],
            "proposal_ref": proposal["proposal_ref"],
            "proposal_hash": proposal["proposal_ref"]["hash"],
            "actor": {"kind": "OWNER", "id": "reaudit-owner"},
            "expected_state_version": state["state_version"],
            "choice": "WAIT",
            "commit_timing": None,
            "outcome_details": {"WAIT": {"review_trigger": "new material evidence"}},
        }
        waited = self.controller.apply_owner_choice(run_id, command)

        resumed = self.engine.handle(f"$better-product-graph resume {run_id}")
        current = self.controller.load_state(run_id)

        self.assertEqual(waited["status"], "WAITING_TRIGGER")
        self.assertEqual(resumed["status"], "WAIT_TRIGGER_REQUIRED")
        self.assertEqual(current["status"], "WAITING_TRIGGER")
        self.assertEqual(current["waiting"]["kind"], "NEW_EVIDENCE")

    def test_waiting_trigger_status_tamper_to_active_is_rejected_by_event_authority(self) -> None:
        run_id = "run-wait-status-tamper"
        self.controller.create_run(run_id, raw_signal="wait status tamper")
        state = place_at_decision(self.controller, run_id)
        proposal = persist_decision_proposal(
            self.project, "decision-wait-status-tamper", run_id, agent_submission()
        )
        self.controller.apply_owner_choice(
            run_id,
            {
                "schema_version": "owner-choice-command.v1",
                "decision_id": proposal["decision_id"],
                "proposal_ref": proposal["proposal_ref"],
                "proposal_hash": proposal["proposal_ref"]["hash"],
                "actor": {"kind": "OWNER", "id": "reaudit-owner"},
                "expected_state_version": state["state_version"],
                "choice": "WAIT",
                "commit_timing": None,
                "outcome_details": {"WAIT": {"review_trigger": "new material evidence"}},
            },
        )
        tampered = self.controller.load_state(run_id)
        tampered["status"] = "ACTIVE"
        atomic_write_json(self.controller._state_path(run_id), tampered)

        resumed = self.engine.handle(f"$better-product-graph resume {run_id}")

        self.assertEqual(resumed["status"], "BLOCKED_STALE")
        self.assertTrue(
            any(
                "lifecycle" in item or "full state commitment" in item
                for item in resumed["blockers"]
            )
        )
        self.assertEqual(self.controller.load_state(run_id)["status"], "ACTIVE")

    def test_started_dispatch_binds_the_exact_authorized_state_version(self) -> None:
        runtime = HostRuntime(
            self.project,
            GRAPH,
            REPO_ROOT / "src" / "core",
        )
        activated = runtime.handle_entry("$better-product-graph new exact dispatch state version")
        state = runtime.controller.load_state(activated["run_id"])
        attempt = next(
            item
            for item in state["dispatch_attempts"]
            if item["attempt_id"] == activated["dispatch"]["attempt_id"]
        )

        self.assertEqual(attempt.get("authorized_state_version"), state["state_version"])

    def test_active_resume_is_idempotent_but_paused_resume_does_not_revive_old_dispatch(self) -> None:
        runtime = HostRuntime(
            self.project,
            GRAPH,
            REPO_ROOT / "src" / "core",
        )
        activated = runtime.handle_entry(
            "$better-product-graph new ordinary resume authority"
        )
        run_id = activated["run_id"]
        active = runtime.controller.load_state(run_id)
        active_events = verify_event_chain(runtime.controller._events_path(run_id))

        redundant = runtime.handle_entry(f"$better-product-graph resume {run_id}")

        self.assertEqual(redundant["status"], "RESUMED")
        self.assertEqual(redundant["state"], active)
        self.assertEqual(
            verify_event_chain(runtime.controller._events_path(run_id)),
            active_events,
        )

        paused = runtime.handle_entry(f"$better-product-graph pause {run_id}")
        resumed = runtime.handle_entry(f"$better-product-graph resume {run_id}")
        original_attempt = next(
            item
            for item in resumed["state"]["dispatch_attempts"]
            if item["attempt_id"] == activated["dispatch"]["attempt_id"]
        )

        self.assertEqual(paused["state"]["status"], "PAUSED")
        self.assertEqual(resumed["state"]["status"], "ACTIVE")
        self.assertNotEqual(
            original_attempt["authorized_state_version"],
            resumed["state"]["state_version"],
        )

    def _runtime_across_instruction_upgrade(
        self,
        *,
        declare_compatible_successor: bool,
    ) -> tuple[HostRuntime, str, str]:
        skill_root = self.project / "upgrade-skill"
        shutil.copytree(REPO_ROOT / "src" / "core", skill_root)
        graph = skill_root / "graph" / "manifest.json"
        instruction = skill_root / "atomic-skills" / "signal-intake" / "INSTRUCTIONS.md"
        current_bytes = instruction.read_bytes()
        instruction.write_bytes(current_bytes + b"\nLegacy instruction contract for upgrade test.\n")

        legacy = HostRuntime(self.project, graph, skill_root)
        activated = legacy.handle_entry(
            "$better-product-graph new resume across a compatible instruction upgrade"
        )
        legacy_hash = activated["dispatch"]["instruction_hash"]
        run_id = activated["run_id"]

        instruction.write_bytes(current_bytes)
        registry_path = graph.with_name("node-contracts.json")
        registry = read_json(registry_path)
        if declare_compatible_successor:
            for node_id in ("signal.ingest", "signal.prepare"):
                registry["nodes"][node_id]["compatible_instruction_hashes"] = [legacy_hash]
        atomic_write_json(registry_path, registry)
        return HostRuntime(self.project, graph, skill_root), run_id, legacy_hash

    def test_compatible_upgrade_keeps_consumed_history_and_current_dispatch_recoverable(self) -> None:
        upgraded, run_id, legacy_hash = self._runtime_across_instruction_upgrade(
            declare_compatible_successor=True
        )

        dispatch = upgraded.dispatch_current(run_id)
        state = upgraded.controller.load_state(run_id)
        consumed = [
            item for item in state["dispatch_attempts"]
            if item["attempt_id"] in state["consumed_attempts"]
        ]

        self.assertEqual(dispatch["node_id"], "signal.prepare")
        self.assertEqual(dispatch["instruction_hash"], legacy_hash)
        self.assertEqual(len(consumed), 1)
        self.assertEqual(consumed[0]["contract"]["instruction_hash"], legacy_hash)

    def test_undeclared_current_instruction_drift_remains_zero_write_blocked(self) -> None:
        upgraded, run_id, _ = self._runtime_across_instruction_upgrade(
            declare_compatible_successor=False
        )
        before = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }

        with self.assertRaisesRegex(TransitionRejected, "contract drifted"):
            upgraded.dispatch_current(run_id)

        after = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_started_unknown_side_effect_with_undeclared_instruction_drift_is_zero_write_blocked(self) -> None:
        upgraded, run_id, _ = self._runtime_across_instruction_upgrade(
            declare_compatible_successor=False
        )
        state = upgraded.controller.load_state(run_id)
        current = next(
            item
            for item in state["dispatch_attempts"]
            if item["node_id"] == state["current_node"]
            and item["status"] == "DISPATCHED"
        )
        mark_dispatch_unknown(upgraded.controller, run_id, current["attempt_id"])
        before = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }

        with self.assertRaisesRegex(
            TransitionRejected, "UNKNOWN_SIDE_EFFECT|contract drifted"
        ):
            upgraded.dispatch_current(run_id)

        after = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_prd_generate_declares_the_real_pre_schema_dispatch_as_compatible(self) -> None:
        registry = NodeRegistry(
            REPO_ROOT / "src" / "core",
            REPO_ROOT / "src" / "core" / "graph" / "manifest.json",
        )

        self.assertEqual(
            registry.instruction_compatibility(
                "prd.generate",
                "sha256:6432e9f737b73a33e09f4e6b39e61137a391ecaf9d41bdfd8054ab4159213283",
            ),
            "DECLARED_COMPATIBLE_SUCCESSOR",
        )

    def test_authoritative_barrier_rejects_attempt_and_state_version_tamper(self) -> None:
        for field in ("state_version", "dispatch_attempts"):
            with self.subTest(field=field):
                run_id = f"run-authority-{field.replace('_', '-')}"
                self.controller.create_run(run_id, raw_signal=f"tamper {field}")
                state = self.controller.load_state(run_id)
                if field == "state_version":
                    state["state_version"] += 7
                else:
                    state["dispatch_attempts"] = [
                        {
                            "attempt_id": "attempt-forged",
                            "node_id": "signal.ingest",
                            "state_version": state["state_version"],
                            "authorized_state_version": state["state_version"],
                            "authority_hash": self.controller._dispatch_authority_hash(state),
                            "status": "DISPATCHED",
                            "side_effect": "NONE",
                            "retryable": False,
                            "contract": self.controller.registry.dispatch_envelope(
                                "signal.ingest", "attempt-forged", [], {}
                            ),
                        }
                    ]
                atomic_write_json(self.controller._state_path(run_id), state)

                with self.assertRaisesRegex(TransitionRejected, "event authority"):
                    self.controller.authoritative_read_barrier(run_id)

    def test_public_operations_do_not_recover_result_while_state_commitment_is_tampered(self) -> None:
        runtime = HostRuntime(
            self.project,
            GRAPH,
            REPO_ROOT / "src" / "core",
        )
        for operation in ("status", "dispatch", "trigger", "resume"):
            with self.subTest(operation=operation):
                run_id = f"run-recovery-authority-{operation}"
                trigger_path: Path | None = None
                if operation == "trigger":
                    runtime.controller.create_run(run_id, raw_signal="typed trigger recovery")
                    state = place_at_decision(runtime.controller, run_id)
                    attempt_id = f"attempt-{operation}"
                    persist_node_dispatch(runtime.controller, run_id, attempt_id)
                    begin_node_call(runtime.controller, run_id, attempt_id)
                    state = runtime.controller.load_state(run_id)
                    dispatch = next(
                        item for item in state["dispatch_attempts"]
                        if item["attempt_id"] == attempt_id
                    )["contract"]
                    result = {
                        "schema_version": "node-result.v1",
                        "node_id": "product.decision",
                        "attempt_id": attempt_id,
                        "producer": {"kind": "HOST_AGENT"},
                        "instruction_ref": dispatch["instruction_ref"],
                        "instruction_hash": dispatch["instruction_hash"],
                        "input_refs": dispatch["input_refs"],
                        "input_hashes": dispatch["input_hashes"],
                        "semantic_output": agent_draft(),
                        "artifact_refs": [],
                    }
                    with self.assertRaises(InjectedCrash):
                        runtime.controller.submit_result(
                            run_id,
                            result,
                            failpoint=crash_at("after_result_persist"),
                        )
                    proposal = persist_decision_proposal(
                        self.project,
                        f"decision-{operation}",
                        run_id,
                        result,
                    )
                    state = runtime.controller.load_state(run_id)
                    waiting = runtime.controller.apply_owner_choice(
                        run_id,
                        {
                            "schema_version": "owner-choice-command.v1",
                            "decision_id": proposal["decision_id"],
                            "proposal_ref": proposal["proposal_ref"],
                            "proposal_hash": proposal["proposal_ref"]["hash"],
                            "actor": {"kind": "OWNER", "id": "eli"},
                            "expected_state_version": state["state_version"],
                            "choice": "WAIT",
                            "commit_timing": None,
                            "outcome_details": {
                                "WAIT": {"review_trigger": "new material evidence"}
                            },
                        },
                    )
                    evidence_path = self.project / f"evidence-{operation}.json"
                    atomic_write_json(evidence_path, {"status": "RECEIVED"})
                    trigger_path = self.project / f"trigger-{operation}.json"
                    atomic_write_json(
                        trigger_path,
                        {
                            "schema_version": "wait-trigger-command.v1",
                            "trigger_id": f"trigger-{operation}",
                            "trigger_type": "NEW_EVIDENCE",
                            "run_id": run_id,
                            "waiting_state_version": waiting["state_version"],
                            "waiting_condition": "new material evidence",
                            "evidence_ref": {
                                "path": evidence_path.relative_to(self.project).as_posix(),
                                "hash": sha256_file(evidence_path),
                                "version": 1,
                            },
                            "received_at": "2026-08-20T10:00:00+08:00",
                            "source": {"kind": "MANUAL", "actor": "eli"},
                        },
                    )
                else:
                    activated = runtime.handle_entry(
                        f"$better-product-graph new recovery authority {operation}"
                    )
                    run_id = activated["run_id"]
                    dispatch = activated["dispatch"]
                    result = {
                        "schema_version": "node-result.v1",
                        "node_id": "signal.prepare",
                        "attempt_id": dispatch["attempt_id"],
                        "producer": {"kind": "HOST_AGENT"},
                        "instruction_ref": dispatch["instruction_ref"],
                        "instruction_hash": dispatch["instruction_hash"],
                        "input_refs": dispatch["input_refs"],
                        "input_hashes": dispatch["input_hashes"],
                        "semantic_output": {"prepared_signal": "exact persisted result"},
                        "artifact_refs": [],
                    }
                    with self.assertRaises(InjectedCrash):
                        runtime.controller.submit_result(
                            run_id,
                            result,
                            failpoint=crash_at("after_result_persist"),
                        )

                state_path = runtime.controller._state_path(run_id)
                state = runtime.controller.load_state(run_id)
                state["future_runtime_authority"] = {
                    "authorized": True,
                    "route": "product.planning",
                }
                atomic_write_json(state_path, state)
                run_path = runtime.controller.run_path(run_id)
                before = {
                    path.relative_to(run_path).as_posix(): path.read_bytes()
                    for path in run_path.rglob("*")
                    if path.is_file()
                }

                if operation == "dispatch":
                    with self.assertRaises(TransitionRejected):
                        runtime.dispatch_current(run_id)
                else:
                    entry = (
                        f"$better-product-graph resume {run_id} "
                        f"trigger={trigger_path.relative_to(self.project).as_posix()}"
                        if trigger_path is not None
                        else f"$better-product-graph {operation} {run_id}"
                    )
                    response = runtime.engine.handle(entry)
                    self.assertEqual(response["status"], "BLOCKED_STALE")

                after = {
                    path.relative_to(run_path).as_posix(): path.read_bytes()
                    for path in run_path.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, before)

    def test_schema_valid_snapshot_position_tamper_blocks_public_resume(self) -> None:
        activated = self.engine.handle("$better-product-graph new state tamper fixture")
        run_id = activated["run_id"]
        state_path = self.controller._state_path(run_id)
        state = self.controller.load_state(run_id)
        state.update(
            {
                "current_node": "prd.ready.gate",
                "next_allowed_nodes": ["handoff.prepare"],
            }
        )
        atomic_write_json(state_path, state)

        resumed = self.engine.handle(f"$better-product-graph resume {run_id}")

        self.assertEqual(resumed["status"], "BLOCKED_STALE")
        self.assertTrue(
            any("snapshot" in blocker or "event" in blocker for blocker in resumed["blockers"])
        )
        self.assertEqual(self.controller.load_state(run_id)["current_node"], "prd.ready.gate")

    def test_public_resume_recovers_a_committed_transition_before_reporting_state(self) -> None:
        run_id = "run-transition-crash-public"
        self.controller.create_run(run_id, raw_signal="transition crash")
        attempt_id = "attempt-transition-crash-public"
        persist_node_dispatch(self.controller, run_id, attempt_id)
        begin_node_call(self.controller, run_id, attempt_id)
        self.controller.execute_mechanical_result(run_id, attempt_id)
        state = self.controller.load_state(run_id)
        with self.assertRaises(InjectedCrash):
            self.controller.transition(
                run_id,
                {
                    "requested_node": "signal.prepare",
                    "attempt_id": attempt_id,
                    "expected_state_version": state["state_version"],
                },
                failpoint=crash_at("after_transition"),
            )

        resumed = self.engine.handle(f"$better-product-graph resume {run_id}")

        self.assertEqual(resumed["status"], "RESUMED")
        self.assertEqual(resumed["state"]["current_node"], "signal.prepare")
        self.assertIn(attempt_id, resumed["state"]["consumed_attempts"])


class AuditEventAuthorityTests(unittest.TestCase):
    def test_recorded_at_requires_strict_iso_string_on_append_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            invalid = {
                "event_id": "invalid-recorded-at",
                "event_type": "TEST",
                "actor": "test",
                "recorded_at": 7,
            }
            with self.assertRaisesRegex(IntegrityError, "recorded_at|schema"):
                append_event(path, invalid)
            with self.assertRaisesRegex(IntegrityError, "recorded_at|ISO"):
                append_event(path, {**invalid, "recorded_at": "not-a-timestamp"})

            valid = append_event(
                path,
                {**invalid, "recorded_at": "2026-08-20T10:00:00+08:00"},
            )
            mutated = {**valid, "recorded_at": 7}
            mutated["event_hash"] = _event_hash(mutated)
            path.write_bytes(canonical_json_bytes(mutated) + b"\n")
            with self.assertRaisesRegex(IntegrityError, "recorded_at|schema"):
                verify_event_chain(path)

    def test_schema_invalid_event_is_rejected_on_append_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            with self.assertRaisesRegex(IntegrityError, "schema|actor"):
                append_event(path, {"event_type": "MISSING_ACTOR"})

            forged = {
                "schema_version": "audit-event.v1",
                "event_id": "forged-no-actor",
                "recorded_at": "2026-08-20T00:00:00+00:00",
                "event_type": "MISSING_ACTOR",
                "previous_hash": None,
            }
            forged["event_hash"] = _event_hash(forged)
            path.write_bytes(canonical_json_bytes(forged) + b"\n")

            with self.assertRaisesRegex(IntegrityError, "schema|actor"):
                verify_event_chain(path)


if __name__ == "__main__":
    unittest.main()
