from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.delivery_contract import derive_active_scope_ref, derive_spec_traceability
from src.bpg.documents import archive_prd_candidate, hash_tree
from src.bpg.failpoints import begin_node_call, persist_node_dispatch
from src.bpg.prd_contract import assemble_prd
from src.bpg.receipts import READY_RULES_VERSION
from src.bpg.ready import PRDNotReady, ready_and_release
from src.bpg.state_controller import StateController, TransitionRejected
from src.bpg.storage import (
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_event_chain,
)
from src.bpg.templates import TemplateRegistry
from tests.test_prd_contract import REPO_ROOT, TEMPLATES, prd_submission
from tests.test_planning_contract import complete_plan
from tests.test_reviews_ready import (
    complete_ready_input,
    finalized_review_companion,
    materialize_ready_evidence,
)
from tests.controller_fixtures import position_run_internal


GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"
_DEFAULT_DISAGREEMENTS = object()


class InstalledPublicReauditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plugin = self.root / "plugin"
        self.project = (self.root / "project").resolve()
        self.project.mkdir()
        build_plugin(REPO_ROOT, self.plugin)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @property
    def runner(self) -> Path:
        return self.plugin / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.runner), *arguments],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )

    def _ok(self, *arguments: str) -> dict:
        completed = self._run(*arguments)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def _payload(self, name: str, value: dict) -> Path:
        path = self.project / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def _run_files(self, run_id: str) -> dict[str, bytes]:
        run_root = self.project / ".better-product-graph" / "runs" / run_id
        return {
            path.relative_to(run_root).as_posix(): path.read_bytes()
            for path in run_root.rglob("*")
            if path.is_file()
        }

    def _run_inventory(self, run_id: str) -> dict[str, tuple[str, object]]:
        run_root = self.project / ".better-product-graph" / "runs" / run_id
        observed: dict[str, tuple[str, object]] = {}
        for path in sorted(run_root.rglob("*")):
            relative = path.relative_to(run_root).as_posix()
            if path.is_symlink():
                observed[relative] = ("symlink", os.readlink(path))
            elif path.is_dir():
                observed[relative] = ("dir", None)
            elif path.is_file():
                observed[relative] = ("file", path.read_bytes())
            else:
                observed[relative] = ("other", None)
        return observed

    def _assert_full_state_blocked(
        self, completed: subprocess.CompletedProcess[str]
    ) -> None:
        if completed.returncode == 0:
            response = json.loads(completed.stdout)
            self.assertEqual(response.get("status"), "BLOCKED_STALE")
            message = "; ".join(response.get("blockers", []))
        else:
            message = completed.stderr
        self.assertIn("full state commitment", message)

    def _waiting_run(self, fixture: str) -> dict:
        run_id = self._ok("new", f"VC5-C1 waiting fixture {fixture}")["run_id"]
        self._force_node(
            run_id,
            "product.decision",
            ["product.planning", "evidence.collect"],
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        decision_result = {
            "schema_version": "node-result.v1",
            "node_id": "product.decision",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": {
                "recommendation": "WAIT",
                "reasons": ["等待新的可核验证据", "不越过当前未知"],
                "mvu": "新证据是否改变问题判断",
                "nearest_alternative": "RESEARCH",
                "flip_condition": "收到新的材料证据",
                "next_action": "等待 exact NEW_EVIDENCE trigger",
                "epistemic_confidence": "LOW",
                "action_risk": {
                    "level": "R1",
                    "basis": "no irreversible action",
                    "reversible": True,
                    "measurable": True,
                    "rollback": "remain waiting",
                },
                "non_waivable_policy_violations": [],
                "outcome_details": {
                    "WAIT": {"review_trigger": "new material evidence"}
                },
            },
            "artifact_refs": [],
        }
        proposed = self._ok(
            "--operation",
            "submit",
            "--run-id",
            run_id,
            "--payload-file",
            str(self._payload(f"{fixture}-decision.json", decision_result)),
        )
        waited = self._ok(
            "--operation",
            "owner-choice",
            "--run-id",
            run_id,
            "--payload-file",
            str(
                self._payload(
                    f"{fixture}-owner-choice.json",
                    {
                        "schema_version": "owner-choice-command.v1",
                        "decision_id": proposed["proposal"]["decision_id"],
                        "proposal_ref": proposed["proposal"]["proposal_ref"],
                        "proposal_hash": proposed["proposal"]["proposal_ref"]["hash"],
                        "actor": {"kind": "OWNER", "id": "eli"},
                        "expected_state_version": proposed["state"]["state_version"],
                        "choice": "WAIT",
                        "commit_timing": None,
                        "outcome_details": {
                            "WAIT": {"review_trigger": "new material evidence"}
                        },
                    },
                )
            ),
        )
        return {
            "run_id": run_id,
            "state": waited["state"],
            "state_path": (
                self.project
                / ".better-product-graph"
                / "runs"
                / run_id
                / "state.json"
            ),
        }

    def _wait_trigger(
        self,
        fixture: str,
        run_id: str,
        waiting_version: int,
        evidence_ref: dict,
        *,
        condition: str = "new material evidence",
    ) -> Path:
        return self._payload(
            f"{fixture}-trigger.json",
            {
                "schema_version": "wait-trigger-command.v1",
                "trigger_id": f"trigger-{fixture}",
                "trigger_type": "NEW_EVIDENCE",
                "run_id": run_id,
                "waiting_state_version": waiting_version,
                "waiting_condition": condition,
                "evidence_ref": evidence_ref,
                "received_at": "2026-08-20T10:00:00+08:00",
                "source": {"kind": "MANUAL", "actor": "eli"},
            },
        )

    def _force_node(
        self,
        run_id: str,
        node_id: str,
        routes: list[str],
        *,
        artifact_refs: dict[str, dict] | None = None,
    ) -> Path:
        """Internal-only Controller fixture; public tests never edit snapshot alone."""

        state_path = self.project / ".better-product-graph" / "runs" / run_id / "state.json"
        controller = StateController(self.project, GRAPH)
        position_run_internal(
            controller,
            run_id,
            node_id,
            routes,
            artifact_refs=artifact_refs,
        )
        return state_path

    def _problem_synthesis_submission(self, fixture: str) -> tuple[str, dict, Path, dict]:
        run_id = self._ok("new", f"submit preflight {fixture}")["run_id"]
        self._force_node(
            run_id,
            "problem.synthesize",
            ["problem.quality.review"],
        )
        dispatch = self._ok(
            "--operation", "dispatch", "--run-id", run_id
        )["dispatch"]
        candidate_path = self.project / f"{fixture}-problem-definition-v1.json"
        atomic_write_json(
            candidate_path,
            {
                "schema_version": "problem-definition.v1",
                "version": 1,
                "problem_definition": "用户无法判断失败结算能否安全恢复。",
            },
        )
        candidate_ref = {
            "role": "problem_definition_candidate",
            "path": candidate_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(candidate_path),
            "version": 1,
        }
        result = {
            "schema_version": "node-result.v1",
            "node_id": "problem.synthesize",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": {
                "candidate_ref": candidate_ref,
                "problem_definition": "用户无法判断失败结算能否安全恢复。",
            },
            "artifact_refs": [candidate_ref],
        }
        return run_id, dispatch, candidate_path, result

    def test_installed_host_submit_invalid_artifact_is_zero_write_and_retryable(self) -> None:
        run_id, dispatch, _candidate_path, result = self._problem_synthesis_submission(
            "retry-same-attempt"
        )
        bad_ref = {
            **result["artifact_refs"][0],
            "hash": "sha256:" + "0" * 64,
        }
        bad_result = json.loads(json.dumps(result))
        bad_result["artifact_refs"] = [bad_ref]
        bad_result["semantic_output"]["candidate_ref"] = bad_ref
        before = self._run_files(run_id)

        rejected = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-synthesize-bad-hash.json", bad_result)),
            "--requested-node", "problem.quality.review",
        )

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("final artifact bytes", rejected.stderr)
        self.assertIn("same attempt", rejected.stderr)
        self.assertEqual(self._run_files(run_id), before)
        attempt_root = (
            self.project / ".better-product-graph" / "runs" / run_id
            / "attempts" / dispatch["attempt_id"]
        )
        self.assertFalse((attempt_root / "node-result.json").exists())
        self.assertFalse((attempt_root / "result-receipt.json").exists())

        corrected = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-synthesize-corrected.json", result)),
            "--requested-node", "problem.quality.review",
        )

        self.assertEqual(corrected["status"], "ADVANCED")
        self.assertEqual(corrected["dispatch"]["node_id"], "problem.quality.review")
        state = corrected["state"]
        self.assertEqual(state["current_node"], "problem.quality.review")
        self.assertIn(dispatch["attempt_id"], state["consumed_attempts"])

        after_success = self._run_files(run_id)
        conflicting = json.loads(json.dumps(result))
        conflicting["semantic_output"]["problem_definition"] = "冲突的第二份结果"
        conflict = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-synthesize-conflict.json", conflicting)),
            "--requested-node", "problem.quality.review",
        )
        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn("attempt identity conflict", conflict.stderr)
        self.assertEqual(self._run_files(run_id), after_success)

        identical = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-synthesize-identical.json", result)),
            "--requested-node", "problem.quality.review",
        )
        self.assertNotEqual(identical.returncode, 0)
        self.assertIn("attempt already exists", identical.stderr)
        self.assertEqual(self._run_files(run_id), after_success)

    def test_installed_host_submit_preflight_rejects_malformed_artifact_refs_without_run_writes(self) -> None:
        attacks = {
            "missing": lambda ref: {**ref, "path": "missing-problem-definition.json"},
            "escape": lambda ref: {**ref, "path": "../../problem-definition.json"},
            "role": lambda ref: {**ref, "role": ""},
            "version": lambda ref: {key: value for key, value in ref.items() if key != "version"},
        }
        for attack, mutate in attacks.items():
            with self.subTest(attack=attack):
                run_id, _dispatch, _candidate_path, result = (
                    self._problem_synthesis_submission(f"invalid-{attack}")
                )
                attacked = json.loads(json.dumps(result))
                bad_ref = mutate(attacked["artifact_refs"][0])
                attacked["artifact_refs"] = [bad_ref]
                attacked["semantic_output"]["candidate_ref"] = bad_ref
                before = self._run_files(run_id)

                rejected = self._run(
                    "--operation", "submit", "--run-id", run_id,
                    "--payload-file", str(self._payload(f"problem-synthesize-{attack}.json", attacked)),
                    "--requested-node", "problem.quality.review",
                )

                self.assertNotEqual(rejected.returncode, 0)
                self.assertEqual(self._run_files(run_id), before)

    def test_installed_host_submit_invalid_route_is_zero_write_and_retryable(self) -> None:
        run_id, _dispatch, _candidate_path, result = self._problem_synthesis_submission(
            "retry-invalid-route"
        )
        before = self._run_files(run_id)
        payload = self._payload("problem-synthesize-invalid-route.json", result)

        rejected = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(payload),
            "--requested-node", "product.decision",
        )

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("requested_node", rejected.stderr)
        self.assertEqual(self._run_files(run_id), before)

        corrected = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(payload),
            "--requested-node", "problem.quality.review",
        )
        self.assertEqual(corrected["dispatch"]["node_id"], "problem.quality.review")

    def test_installed_problem_synthesize_instruction_explains_hash_retry_boundary(self) -> None:
        instruction = (
            self.plugin
            / "skills"
            / "better-product-graph"
            / "references"
            / "atomic-skills"
            / "problem-synthesize"
            / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("final artifact bytes", instruction)
        self.assertIn("same attempt_id", instruction)

    def _tamper_snapshot_to_product_decision(self, run_id: str, operation: str) -> Path:
        """Preserve the independent audit payload without touching events or Plugin bytes."""

        state_path = self.project / ".better-product-graph" / "runs" / run_id / "state.json"
        state = read_json(state_path)
        state.update(
            {
                "status": "ACTIVE",
                "current_node": "product.decision",
                "last_completed_node": "problem.ready.gate",
                "next_allowed_nodes": [],
                "dispatch_attempts": [],
            }
        )
        atomic_write_json(state_path, state)
        atomic_write_json(
            self.project / f"reaudit-payload-new-c1-{operation}.json",
            state,
        )
        return state_path

    def test_installed_public_operations_reject_schema_valid_snapshot_authority_tamper(self) -> None:
        operations = {
            "status": ("entry", ("status",)),
            "dispatch": ("dispatch", ()),
            "submit": ("submit", ()),
            "pause": ("entry", ("pause",)),
            "resume": ("entry", ("resume",)),
            "interview": ("entry", ("interview", "skip")),
            "owner-choice": ("owner-choice", ()),
            "handoff": ("entry", ("handoff",)),
            "audit": ("entry", ("audit",)),
        }
        for operation, (surface, entry) in operations.items():
            with self.subTest(operation=operation):
                activated = self._ok("new", f"NEW-C1 snapshot authority {operation}")
                run_id = activated["run_id"]
                state_path = self._tamper_snapshot_to_product_decision(run_id, operation)
                tampered = read_json(state_path)
                before_files = set((state_path.parent / "attempts").glob("**/*"))
                if surface == "entry":
                    completed = self._run(*entry, run_id)
                elif surface == "dispatch":
                    completed = self._run("--operation", "dispatch", "--run-id", run_id)
                else:
                    payload = {
                        "schema_version": "node-result.v1",
                        "node_id": "product.decision",
                        "attempt_id": "attempt-new-c1-forged",
                        "producer": {"kind": "HOST_AGENT"},
                        "semantic_output": {"recommendation": "COMMIT"},
                        "artifact_refs": [],
                    }
                    if surface == "owner-choice":
                        payload = {
                            "schema_version": "owner-choice-command.v1",
                            "decision_id": "decision-new-c1-forged",
                        }
                    payload_path = self._payload(
                        f"reaudit-command-new-c1-{operation}.json", payload
                    )
                    completed = self._run(
                        "--operation", surface, "--run-id", run_id,
                        "--payload-file", str(payload_path),
                    )

                if completed.returncode == 0:
                    response = json.loads(completed.stdout)
                    self.assertEqual(response.get("status"), "BLOCKED_STALE")
                    self.assertNotIn("state", response)
                    self.assertTrue(
                        any("event authority" in item for item in response.get("blockers", []))
                    )
                else:
                    self.assertIn("event authority", completed.stderr)
                self.assertEqual(read_json(state_path), tampered)
                self.assertEqual(
                    set((state_path.parent / "attempts").glob("**/*")), before_files
                )
                self.assertFalse(
                    any(
                        (self.project / ".better-product-graph" / "decisions").glob("**/*")
                    )
                )

    def test_installed_public_authority_barrier_preserves_normal_operations(self) -> None:
        activated = self._ok("new", "normal public authority path")
        run_id = activated["run_id"]

        status = self._ok("status", run_id)
        audit = self._ok("audit", run_id)
        handoff = self._ok("handoff", run_id)
        paused = self._ok("pause", run_id)
        resumed = self._ok("resume", run_id)
        interview = self._ok("interview", "skip", run_id)

        self.assertEqual(status["state"]["current_node"], "signal.prepare")
        self.assertTrue(audit["events"])
        self.assertEqual(handoff["status"], "NOT_READY")
        self.assertEqual(paused["state"]["status"], "PAUSED")
        self.assertEqual(resumed["state"]["status"], "ACTIVE")
        self.assertEqual(interview["state"]["interaction_policy"], "NO_PM_INTERVIEW")

    def test_installed_full_state_commitment_rejects_schema_valid_field_mutations(self) -> None:
        cases = ("waiting", "interaction_policy", "candidate_decision", "future_field")
        for case in cases:
            with self.subTest(case=case):
                if case in {"waiting", "candidate_decision"}:
                    fixture = self._waiting_run(f"full-state-{case}")
                    run_id = fixture["run_id"]
                    state_path = fixture["state_path"]
                else:
                    run_id = self._ok("new", f"VC5-C1 full state {case}")["run_id"]
                    state_path = (
                        self.project
                        / ".better-product-graph"
                        / "runs"
                        / run_id
                        / "state.json"
                    )
                state = read_json(state_path)
                if case == "waiting":
                    state["waiting"]["outcome_details"]["WAIT"]["review_trigger"] = (
                        "forged replacement evidence"
                    )
                elif case == "interaction_policy":
                    state["interaction_policy"] = "NO_PM_INTERVIEW"
                elif case == "candidate_decision":
                    state["candidate_version"] += 1
                    state["decision"]["chosen_outcome"] = "COMMIT"
                    state["decision"]["route"] = "DELIVERY_NOW"
                else:
                    state["future_runtime_authority"] = {
                        "authorized": True,
                        "route": "product.planning",
                    }
                atomic_write_json(state_path, state)
                before = self._run_files(run_id)

                completed = self._run("status", run_id)

                self._assert_full_state_blocked(completed)
                self.assertEqual(self._run_files(run_id), before)

    def test_installed_full_state_commitment_rejects_mutated_wait_condition_before_trigger(self) -> None:
        fixture = self._waiting_run("wait-condition-mutation")
        run_id = fixture["run_id"]
        state_path = fixture["state_path"]
        state = read_json(state_path)
        state["waiting"]["outcome_details"]["WAIT"]["review_trigger"] = (
            "forged replacement evidence"
        )
        evidence_path = self.project / "wait-condition-evidence.json"
        atomic_write_json(evidence_path, {"kind": "evidence", "status": "RECEIVED"})
        evidence_ref = {
            "path": evidence_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(evidence_path),
            "version": 1,
        }
        atomic_write_json(state_path, state)
        trigger = self._wait_trigger(
            "wait-condition-mutation",
            run_id,
            state["state_version"],
            evidence_ref,
            condition="forged replacement evidence",
        )
        before = self._run_files(run_id)

        completed = self._run("resume", run_id, "--trigger-file", trigger.name)

        self._assert_full_state_blocked(completed)
        self.assertEqual(self._run_files(run_id), before)

    def test_installed_unbound_hash_correct_artifact_is_rejected_by_public_operations(self) -> None:
        for operation in ("status", "dispatch", "trigger"):
            with self.subTest(operation=operation):
                if operation == "trigger":
                    fixture = self._waiting_run(f"unbound-{operation}")
                    run_id = fixture["run_id"]
                    state_path = fixture["state_path"]
                else:
                    run_id = self._ok("new", f"VC5-C1 unbound artifact {operation}")["run_id"]
                    state_path = (
                        self.project
                        / ".better-product-graph"
                        / "runs"
                        / run_id
                        / "state.json"
                    )
                artifact_path = self.project / f"unbound-{operation}-evidence.json"
                atomic_write_json(
                    artifact_path,
                    {
                        "kind": "evidence",
                        "status": "RECEIVED",
                        "authorized": True,
                        "operation": operation,
                    },
                )
                artifact_ref = {
                    "role": "evidence",
                    "path": artifact_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(artifact_path),
                    "version": 1,
                }
                state = read_json(state_path)
                state["artifact_refs"][f"forged-unbound-{operation}"] = artifact_ref
                atomic_write_json(state_path, state)
                before = self._run_files(run_id)

                if operation == "status":
                    completed = self._run("status", run_id)
                elif operation == "dispatch":
                    completed = self._run("--operation", "dispatch", "--run-id", run_id)
                else:
                    trigger = self._wait_trigger(
                        "unbound-trigger",
                        run_id,
                        state["state_version"],
                        {
                            key: artifact_ref[key]
                            for key in ("path", "hash", "version")
                        },
                    )
                    completed = self._run(
                        "resume", run_id, "--trigger-file", trigger.name
                    )

                self._assert_full_state_blocked(completed)
                self.assertEqual(self._run_files(run_id), before)

    def test_public_submit_cannot_claim_controller_identity_at_mechanical_nodes(self) -> None:
        cases = {
            "problem.ready.gate": "product.decision",
            "plan.ready.gate": "prd.generate",
            "review.finalize": "prd.ready.gate",
            "prd.ready.gate": "handoff.prepare",
        }
        for index, (node_id, requested_node) in enumerate(cases.items()):
            with self.subTest(node_id=node_id):
                activated = self._ok("new", f"mechanical bypass {index}")
                run_id = activated["run_id"]
                state_path = self._force_node(run_id, node_id, [requested_node])
                dispatched = self._run("--operation", "dispatch", "--run-id", run_id)
                if dispatched.returncode != 0:
                    self.assertEqual(read_json(state_path)["current_node"], node_id)
                    continue
                dispatch = json.loads(dispatched.stdout)["dispatch"]
                forged = {
                    "schema_version": "node-result.v1",
                    "node_id": node_id,
                    "attempt_id": dispatch["attempt_id"],
                    "producer": {
                        "kind": "DETERMINISTIC_PROGRAM",
                        "component": "state-controller",
                    },
                    "mechanical_output": {"status": "PASS", "forged": True},
                    "artifact_refs": [],
                }
                completed = self._run(
                    "--operation",
                    "submit",
                    "--run-id",
                    run_id,
                    "--payload-file",
                    str(self._payload(f"forged-{index}.json", forged)),
                    "--requested-node",
                    requested_node,
                )

                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(
                    json.loads(state_path.read_text(encoding="utf-8"))["current_node"],
                    node_id,
                )

    def test_invalid_agent_prd_cannot_advance_into_review(self) -> None:
        activated = self._ok("new", "missing PRD authority must not reach Review")
        run_id = activated["run_id"]
        state_path = self._force_node(run_id, "prd.generate", ["review.parallel"])
        dispatched = self._run("--operation", "dispatch", "--run-id", run_id)
        self.assertNotEqual(dispatched.returncode, 0)
        self.assertIn("missing committed Product Decision", dispatched.stderr)
        self.assertEqual(read_json(state_path)["current_node"], "prd.generate")

    def test_next_dispatch_binds_committed_result_and_declared_artifact(self) -> None:
        activated = self._ok("new", "propagate exact committed output")
        run_id = activated["run_id"]
        dispatch = activated["dispatch"]
        artifact = self.project / "prepared-signal.json"
        atomic_write_json(artifact, {"prepared_signal": "exact"})
        artifact_ref = {
            "role": "prepared_signal",
            "path": artifact.relative_to(self.project).as_posix(),
            "hash": sha256_file(artifact),
            "version": 1,
        }
        result = {
            "schema_version": "node-result.v1",
            "node_id": "signal.prepare",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "semantic_output": {"prepared_signal": "exact"},
            "artifact_refs": [artifact_ref],
        }
        advanced = self._ok(
            "--operation",
            "submit",
            "--run-id",
            run_id,
            "--payload-file",
            str(self._payload("prepare-propagate.json", result)),
            "--requested-node",
            "signal.classify",
        )

        next_refs = advanced["dispatch"]["input_refs"]
        self.assertIn(artifact_ref["path"], next_refs)
        self.assertTrue(any(path.endswith("/node-result.json") for path in next_refs))
        self.assertEqual(advanced["dispatch"]["input_hashes"][artifact_ref["path"]], artifact_ref["hash"])

    def test_installed_problem_ready_gate_executes_exact_validator_and_advances(self) -> None:
        run_id = self._ok("new", "problem gate execution")["run_id"]
        candidate_path = self.project / "problem-candidate.json"
        atomic_write_json(candidate_path, {"problem_definition": "结算恢复不透明"})
        candidate_ref = {
            "role": "problem_definition_candidate",
            "path": candidate_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(candidate_path),
            "version": 1,
        }
        controller = StateController(self.project, GRAPH)
        artifact_refs = dict(controller.load_state(run_id)["artifact_refs"])
        artifact_refs["problem-candidate"] = {
            "role": "problem_candidate",
            **candidate_ref,
        }
        state_path = self._force_node(
            run_id,
            "problem.quality.review",
            ["problem.ready.gate"],
            artifact_refs=artifact_refs,
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        review = {
            "candidate_ref": candidate_ref,
            "candidate_hash": candidate_ref["hash"],
            "candidate_version": candidate_ref["version"],
            "upstream_refs": [],
            "review_version": "problem-quality-review.v0.1",
            "findings": [{"id": "finding-1", "concern": "证据边界需保留"}],
            "dispositions": [{"finding_id": "finding-1", "status": "ADDRESSED"}],
            "recommended_disposition": "PROCEED_TO_DETERMINISTIC_READY_CHECK",
            "reviewer_authority": "ADVISORY_ONLY",
            "ready_claim": "NOT_MADE",
        }
        result = {
            "schema_version": "node-result.v1",
            "node_id": "problem.quality.review",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": review,
            "artifact_refs": [],
        }
        advanced = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-review.json", result)),
            "--requested-node", "problem.ready.gate",
        )

        self.assertEqual(advanced["dispatch"]["node_id"], "product.decision")
        state = read_json(state_path)
        self.assertEqual(state["last_completed_node"], "problem.ready.gate")
        gate_results = list(
            (self.project / ".better-product-graph" / "runs" / run_id / "attempts").glob(
                "*/node-result.json"
            )
        )
        self.assertTrue(
            any(read_json(path).get("mechanical_output", {}).get("validator") == "problem_ready_gate" for path in gate_results)
        )
        gate_result_path = next(
            path
            for path in gate_results
            if read_json(path).get("node_id") == "problem.ready.gate"
        )
        gate_result = read_json(gate_result_path)
        self.assertEqual(gate_result["mechanical_output"]["status"], "READY")
        self.assertEqual(advanced["gate_result"], gate_result["mechanical_output"])
        self.assertEqual(
            advanced["gate_result_ref"]["hash"],
            sha256_file(gate_result_path),
        )
        gate_receipt_path = self.project / advanced["gate_receipt_ref"]["path"]
        receipt = read_json(gate_receipt_path)
        self.assertEqual(receipt["outcome"], "READY")
        self.assertEqual(receipt["validator"], "problem_ready_gate")
        self.assertEqual(receipt["rules_version"], "problem-ready.v1")
        self.assertEqual(receipt["unmet_conditions"], [])

    def _public_problem_ready_not_ready_fixture(self):
        run_id = self._ok("new", "problem gate formal NOT_READY")['run_id']
        candidate_path = self.project / "problem-candidate-not-ready.json"
        upstream_path = self.project / "problem-upstream-unbound.json"
        atomic_write_json(candidate_path, {"problem_definition": "结算恢复不透明"})
        atomic_write_json(upstream_path, {"claims": [{"role": "OBSERVATION"}]})
        candidate_ref = {
            "role": "problem_definition_candidate",
            "path": candidate_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(candidate_path),
            "version": 1,
        }
        unbound_upstream_ref = {
            "role": "problem_evidence_map",
            "path": upstream_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(upstream_path),
            "version": 1,
        }
        controller = StateController(self.project, GRAPH)
        artifact_refs = dict(controller.load_state(run_id)["artifact_refs"])
        artifact_refs["problem-candidate"] = candidate_ref
        state_path = self._force_node(
            run_id,
            "problem.quality.review",
            ["problem.ready.gate"],
            artifact_refs=artifact_refs,
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        review = {
            "candidate_ref": candidate_ref,
            "candidate_hash": candidate_ref["hash"],
            "candidate_version": candidate_ref["version"],
            "upstream_refs": [unbound_upstream_ref],
            "review_version": "problem-quality-review.v0.1",
            "findings": [{"id": "finding-1", "concern": "证据边界需保留"}],
            "dispositions": [{"finding_id": "finding-1", "status": "ADDRESSED"}],
            "recommended_disposition": "PROCEED_TO_DETERMINISTIC_READY_CHECK",
            "reviewer_authority": "ADVISORY_ONLY",
            "ready_claim": "NOT_MADE",
        }
        result = {
            "schema_version": "node-result.v1",
            "node_id": "problem.quality.review",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": review,
            "artifact_refs": [],
        }
        completed = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-review-not-ready.json", result)),
            "--requested-node", "problem.ready.gate",
        )
        return completed, run_id, state_path, unbound_upstream_ref

    def test_installed_problem_ready_not_ready_is_durable_auditable_and_idempotent(self) -> None:
        completed, run_id, state_path, upstream_ref = (
            self._public_problem_ready_not_ready_fixture()
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = json.loads(completed.stdout)
        self.assertEqual(response["status"], "NOT_READY")
        self.assertEqual(response["state"]["current_node"], "problem.ready.gate")
        self.assertEqual(read_json(state_path)["current_node"], "problem.ready.gate")
        gate = response["gate_result"]
        self.assertEqual(gate["status"], "NOT_READY")
        self.assertEqual(gate["validator"], "problem_ready_gate")
        self.assertEqual(
            gate["unmet_conditions"],
            [
                {
                    "condition": "upstream.exact_refs",
                    "affected_refs": [upstream_ref],
                    "finding_ids": [],
                    "repair_target": "REBIND_UPSTREAM_REF",
                    "resume_node": "problem.ready.gate",
                }
            ],
        )
        result_path = self.project / response["gate_result_ref"]["path"]
        receipt_path = self.project / response["gate_receipt_ref"]["path"]
        self.assertEqual(sha256_file(result_path), response["gate_result_ref"]["hash"])
        self.assertEqual(sha256_file(receipt_path), response["gate_receipt_ref"]["hash"])
        receipt = read_json(receipt_path)
        self.assertEqual(receipt["outcome"], "NOT_READY")
        self.assertEqual(receipt["unmet_conditions"], gate["unmet_conditions"])

        before = self._run_inventory(run_id)
        repeated = self._ok("--operation", "dispatch", "--run-id", run_id)
        self.assertEqual(repeated["status"], "NOT_READY")
        self.assertEqual(repeated["gate_result_ref"], response["gate_result_ref"])
        self.assertEqual(repeated["gate_receipt_ref"], response["gate_receipt_ref"])
        self.assertEqual(self._run_inventory(run_id), before)

    def test_installed_problem_ready_instruction_exposes_both_formal_outcomes(self) -> None:
        instruction = (
            self.plugin
            / "skills"
            / "better-product-graph"
            / "references"
            / "atomic-skills"
            / "problem-quality-review"
            / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("<!-- problem-ready-ready-result-contract -->", instruction)
        self.assertIn("<!-- problem-ready-not-ready-result-contract -->", instruction)
        self.assertIn("The Controller returns only `READY` or `NOT_READY`", instruction)
        self.assertIn("exact result and receipt refs", instruction)
        ready_match = re.search(
            r"<!-- problem-ready-ready-result-contract -->\s*```json\s*(.*?)\s*```",
            instruction,
            flags=re.DOTALL,
        )
        not_ready_match = re.search(
            r"<!-- problem-ready-not-ready-result-contract -->\s*```json\s*(.*?)\s*```",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(ready_match)
        self.assertIsNotNone(not_ready_match)
        self.assertEqual(json.loads(ready_match.group(1))["status"], "READY")
        not_ready = json.loads(not_ready_match.group(1))
        self.assertEqual(not_ready["status"], "NOT_READY")
        self.assertGreaterEqual(len(not_ready["unmet_conditions"]), 1)

    def test_installed_problem_review_instruction_contract_succeeds_on_first_submission(self) -> None:
        run_id = self._ok("new", "instruction-complete problem review")['run_id']
        candidate_path = self.project / "problem-candidate-instruction.json"
        upstream_path = self.project / "problem-evidence-map-v1.json"
        atomic_write_json(candidate_path, {"problem_definition": "结算恢复不透明"})
        atomic_write_json(upstream_path, {"claims": [{"role": "OBSERVATION"}]})
        candidate_ref = {
            "role": "problem_definition_candidate",
            "path": candidate_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(candidate_path),
            "version": 1,
        }
        upstream_ref = {
            "role": "problem_evidence_map",
            "path": upstream_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(upstream_path),
            "version": 1,
        }
        controller = StateController(self.project, GRAPH)
        artifact_refs = dict(controller.load_state(run_id)["artifact_refs"])
        artifact_refs["problem-candidate"] = candidate_ref
        artifact_refs["problem-evidence-map"] = upstream_ref
        state_path = self._force_node(
            run_id,
            "problem.quality.review",
            ["problem.ready.gate"],
            artifact_refs=artifact_refs,
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        instruction = (
            self.plugin
            / "skills"
            / "better-product-graph"
            / dispatch["instruction_ref"]
        ).read_text(encoding="utf-8")
        match = re.search(
            r"<!-- problem-quality-review-semantic-output-contract -->\s*```json\s*(.*?)\s*```",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "installed instruction must expose one exact JSON contract")
        review = json.loads(match.group(1))
        review.update(
            {
                "candidate_ref": candidate_ref,
                "candidate_hash": candidate_ref["hash"],
                "candidate_version": candidate_ref["version"],
                "upstream_refs": [upstream_ref],
                "findings": [
                    {
                        "id": "PQR-001",
                        "concern": "证据边界需保留",
                        "repair_path": "REVISE_SYNTHESIS",
                    }
                ],
                "dispositions": [
                    {
                        "finding_id": "PQR-001",
                        "status": "CARRY_FORWARD",
                    }
                ],
            }
        )
        result = {
            "schema_version": "node-result.v1",
            "node_id": "problem.quality.review",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": review,
            "artifact_refs": [],
        }

        advanced = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-review-from-instruction.json", result)),
            "--requested-node", "problem.ready.gate",
        )

        self.assertEqual(advanced["dispatch"]["node_id"], "product.decision")
        self.assertEqual(read_json(state_path)["last_completed_node"], "problem.ready.gate")

    def test_installed_problem_review_missing_field_is_rejected_before_state_progress(self) -> None:
        run_id = self._ok("new", "repairable problem review error")["run_id"]
        candidate_path = self.project / "problem-candidate-missing-field.json"
        atomic_write_json(candidate_path, {"problem_definition": "结算恢复不透明"})
        candidate_ref = {
            "role": "problem_definition_candidate",
            "path": candidate_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(candidate_path),
            "version": 1,
        }
        controller = StateController(self.project, GRAPH)
        artifact_refs = dict(controller.load_state(run_id)["artifact_refs"])
        artifact_refs["problem-candidate"] = candidate_ref
        state_path = self._force_node(
            run_id,
            "problem.quality.review",
            ["problem.ready.gate"],
            artifact_refs=artifact_refs,
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        before = read_json(state_path)
        result = {
            "schema_version": "node-result.v1",
            "node_id": "problem.quality.review",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": {
                "candidate_ref": candidate_ref,
                "candidate_version": 1,
                "upstream_refs": [],
                "review_version": "problem-quality-review.v0.1",
                "findings": [{"id": "PQR-001", "concern": "保留证据边界"}],
                "dispositions": [{"finding_id": "PQR-001", "status": "CARRY_FORWARD"}],
                "recommended_disposition": "PROCEED_TO_DETERMINISTIC_READY_CHECK",
                "reviewer_authority": "ADVISORY_ONLY",
                "ready_claim": "NOT_MADE",
            },
            "artifact_refs": [],
        }

        completed = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("problem-review-missing-hash.json", result)),
            "--requested-node", "problem.ready.gate",
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("candidate_hash", completed.stderr)
        self.assertIn("candidate_ref.hash", completed.stderr)
        self.assertEqual(read_json(state_path), before)
        self.assertFalse(
            (
                self.project / ".better-product-graph" / "runs" / run_id
                / "attempts" / dispatch["attempt_id"] / "node-result.json"
            ).exists()
        )

    def test_installed_plan_ready_gate_revalidates_plan_and_returns_prd_dispatch(self) -> None:
        run_id = self._ok("new", "plan gate execution")["run_id"]
        decision_path = self.project / "decision-v1.json"
        atomic_write_json(decision_path, {"decision": "COMMIT", "version": 1})
        decision_ref = {
            "path": decision_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(decision_path),
            "version": 1,
        }
        controller = StateController(self.project, GRAPH)
        artifact_refs = dict(controller.load_state(run_id)["artifact_refs"])
        artifact_refs["decision"] = {
            "role": "decision_record",
            **decision_ref,
            "origin_node_id": "product.decision",
            "origin_attempt_id": "attempt-plan-gate-decision",
        }
        evidence_path = self.project / "evidence-collect-result-v1.json"
        atomic_write_json(
            evidence_path,
            {
                "schema_version": "node-result.v1",
                "node_id": "evidence.collect",
                "attempt_id": "attempt-plan-gate-evidence",
                "producer": {"kind": "HOST_AGENT"},
                "semantic_output": {"sources": []},
                "artifact_refs": [],
            },
        )
        evidence_ref = {
            "path": evidence_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(evidence_path),
            "version": 1,
        }
        artifact_refs["roadmap-and-evidence"] = {
            "role": "node_result",
            **evidence_ref,
            "node_id": "evidence.collect",
            "attempt_id": "attempt-plan-gate-evidence",
        }
        evidence_record_path = self.project / "evidence-record-v1.json"
        atomic_write_json(
            evidence_record_path,
            {"schema_version": "evidence-record.v1", "summary": "exact evidence"},
        )
        artifact_refs["evidence"] = {
            "role": "evidence",
            "path": evidence_record_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(evidence_record_path),
            "version": 1,
            "origin_node_id": "evidence.collect",
            "origin_attempt_id": "attempt-plan-gate-evidence",
        }
        knowledge_path = self.project / "evidence-map-result-v1.json"
        atomic_write_json(
            knowledge_path,
            {
                "schema_version": "node-result.v1",
                "node_id": "evidence.map",
                "attempt_id": "attempt-plan-gate-knowledge",
                "producer": {"kind": "HOST_AGENT"},
                "semantic_output": {"claims": []},
                "artifact_refs": [],
            },
        )
        artifact_refs["knowledge"] = {
            "role": "node_result",
            "path": knowledge_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(knowledge_path),
            "version": 1,
            "node_id": "evidence.map",
            "attempt_id": "attempt-plan-gate-knowledge",
        }
        state_path = self._force_node(
            run_id,
            "product.planning",
            ["plan.ready.gate"],
            artifact_refs=artifact_refs,
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        plan = complete_plan()
        plan["decision_ref"] = decision_ref
        plan_path = self.project / "product-plan-v1.json"
        atomic_write_json(plan_path, plan)
        result = {
            "schema_version": "node-result.v1",
            "node_id": "product.planning",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": plan,
            "artifact_refs": [{"role": "product_plan", **{
                "path": plan_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(plan_path),
                "version": 1,
            }}],
        }
        advanced = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("product-plan.json", result)),
            "--requested-node", "plan.ready.gate",
        )

        self.assertEqual(advanced["dispatch"]["node_id"], "prd.generate")
        self.assertEqual(read_json(state_path)["last_completed_node"], "plan.ready.gate")
        context = advanced["dispatch"]["prd_generation_context"]
        self.assertEqual(context["schema_version"], "prd-generation-context.v1")
        authority = context["metadata_authority"]
        self.assertEqual(authority["prd_id"], "PRD-CHECKOUT-001")
        self.assertEqual(context["candidate_defaults"]["version"], "v0.1")
        self.assertEqual(authority["delivery_intent"], "COMMIT")
        self.assertEqual(
            {item["role"].split(":", 1)[0] for item in authority["spec_traceability"]["refs"]},
            {"decision", "roadmap", "product_plan", "slice", "knowledge", "evidence"},
        )

        submission = prd_submission()
        submission["semantic_output"]["metadata"].update(authority)
        submission["semantic_output"]["metadata"].update(context["candidate_defaults"])
        submission.update(
            {
                "schema_version": "node-result.v1",
                "attempt_id": advanced["dispatch"]["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": advanced["dispatch"]["instruction_ref"],
                "instruction_hash": advanced["dispatch"]["instruction_hash"],
                "input_refs": advanced["dispatch"]["input_refs"],
                "input_hashes": advanced["dispatch"]["input_hashes"],
                "resource_refs": advanced["dispatch"]["resource_refs"],
            }
        )
        tampered = json.loads(json.dumps(submission))
        tampered["semantic_output"]["metadata"]["active_scope_ref"][
            "scope_hash"
        ] = "sha256:host-guessed-scope"
        before = self._run_inventory(run_id)
        rejected = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("guessed-context-prd.json", tampered)),
            "--requested-node", "review.parallel",
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("differs from exact dispatch authority", rejected.stderr)
        self.assertEqual(self._run_inventory(run_id), before)

        generated = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("context-bound-prd.json", submission)),
            "--requested-node", "review.parallel",
        )
        self.assertEqual(generated["dispatch"]["node_id"], "review.parallel")

    def test_installed_plan_gate_rejects_non_decision_authority(self) -> None:
        run_id = self._ok("new", "only a Decision can authorize Planning")["run_id"]
        evidence_path = self.project / "evidence-masquerading-as-decision.json"
        atomic_write_json(evidence_path, {"kind": "evidence", "version": 1})
        masquerade_ref = {
            "path": evidence_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(evidence_path),
            "version": 1,
        }
        controller = StateController(self.project, GRAPH)
        artifact_refs = dict(controller.load_state(run_id)["artifact_refs"])
        artifact_refs["evidence"] = {
            "role": "evidence",
            **masquerade_ref,
            "origin_node_id": "evidence.collect",
            "origin_attempt_id": "attempt-evidence",
        }
        state_path = self._force_node(
            run_id,
            "product.planning",
            ["plan.ready.gate"],
            artifact_refs=artifact_refs,
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        plan = complete_plan()
        plan["decision_ref"] = masquerade_ref
        plan_path = self.project / "wrong-authority-product-plan.md"
        plan_path.write_text("# Invalid authority Product Plan\n", encoding="utf-8")
        result = {
            "schema_version": "node-result.v1",
            "node_id": "product.planning",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": plan,
            "artifact_refs": [
                {
                    "role": "product_plan",
                    "path": plan_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(plan_path),
                    "version": 1,
                }
            ],
        }

        rejected = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("candidate-backed-plan.json", result)),
            "--requested-node", "plan.ready.gate",
        )

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("decision.exact_committed_authority", rejected.stderr)
        self.assertEqual(read_json(state_path)["current_node"], "plan.ready.gate")

    def test_dispatch_started_before_pause_cannot_be_submitted_after_pause(self) -> None:
        activated = self._ok("new", "pause invalidates old dispatch")
        run_id = activated["run_id"]
        dispatch = activated["dispatch"]
        self._ok("pause", run_id)
        result = {
            "schema_version": "node-result.v1",
            "node_id": "signal.prepare",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "semantic_output": {"prepared_signal": "late"},
            "artifact_refs": [],
        }
        completed = self._run(
            "--operation",
            "submit",
            "--run-id",
            run_id,
            "--payload-file",
            str(self._payload("stale-after-pause.json", result)),
            "--requested-node",
            "signal.classify",
        )

        self.assertNotEqual(completed.returncode, 0)
        status = self._ok("status", run_id)["state"]
        self.assertEqual(status["status"], "PAUSED")
        self.assertEqual(status["current_node"], "signal.prepare")

    def test_installed_wait_consumes_one_exact_typed_new_evidence_trigger(self) -> None:
        run_id = self._ok("new", "wait for typed evidence trigger")["run_id"]
        self._force_node(
            run_id,
            "product.decision",
            ["product.planning", "evidence.collect"],
        )
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        decision_result = {
            "schema_version": "node-result.v1",
            "node_id": "product.decision",
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "resource_refs": dispatch["resource_refs"],
            "semantic_output": {
                "recommendation": "WAIT",
                "reasons": ["需要新的真实行为证据", "当前行动不应越过未知"],
                "mvu": "用户是否持续遇到该阻碍",
                "nearest_alternative": "RESEARCH",
                "flip_condition": "收到新的材料证据",
                "next_action": "等待 exact NEW_EVIDENCE trigger",
                "epistemic_confidence": "LOW",
                "action_risk": {
                    "level": "R1",
                    "basis": "no irreversible action",
                    "reversible": True,
                    "measurable": True,
                    "rollback": "remain waiting",
                },
                "non_waivable_policy_violations": [],
                "outcome_details": {
                    "WAIT": {"review_trigger": "new material evidence"}
                },
            },
            "artifact_refs": [],
        }
        proposed = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("wait-decision.json", decision_result)),
        )
        waited = self._ok(
            "--operation", "owner-choice", "--run-id", run_id,
            "--payload-file",
            str(
                self._payload(
                    "wait-owner-choice.json",
                    {
                        "schema_version": "owner-choice-command.v1",
                        "decision_id": proposed["proposal"]["decision_id"],
                        "proposal_ref": proposed["proposal"]["proposal_ref"],
                        "proposal_hash": proposed["proposal"]["proposal_ref"]["hash"],
                        "actor": {"kind": "OWNER", "id": "eli"},
                        "expected_state_version": proposed["state"]["state_version"],
                        "choice": "WAIT",
                        "commit_timing": None,
                        "outcome_details": {
                            "WAIT": {"review_trigger": "new material evidence"}
                        },
                    },
                )
            ),
        )
        waiting_version = waited["state"]["state_version"]
        evidence_path = self.project / "incoming-wait-evidence.json"
        atomic_write_json(
            evidence_path,
            {
                "kind": "evidence",
                "status": "RECEIVED",
                "authorized": True,
                "summary": "New observed checkout failures",
            },
        )
        evidence_ref = {
            "path": evidence_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(evidence_path),
            "version": 1,
        }

        def command(name: str, **changes) -> Path:
            payload = {
                "schema_version": "wait-trigger-command.v1",
                "trigger_id": "trigger-new-evidence-1",
                "trigger_type": "NEW_EVIDENCE",
                "run_id": run_id,
                "waiting_state_version": waiting_version,
                "waiting_condition": "new material evidence",
                "evidence_ref": evidence_ref,
                "received_at": "2026-08-20T10:00:00+08:00",
                "source": {"kind": "MANUAL", "actor": "eli"},
            }
            payload.update(changes)
            return self._payload(name, payload)

        wrong_type = self._run(
            "resume", run_id,
            "--trigger-file", command('wrong-type-trigger.json', trigger_type='TIMER').name,
        )
        self.assertNotEqual(wrong_type.returncode, 0)
        self.assertIn("trigger_type", wrong_type.stderr)
        wrong_run = self._run(
            "resume", run_id,
            "--trigger-file", command('wrong-run-trigger.json', run_id='run-wrong-target').name,
        )
        self.assertNotEqual(wrong_run.returncode, 0)
        self.assertIn("Run", wrong_run.stderr)
        wrong_condition = self._run(
            "resume", run_id,
            "--trigger-file", command('wrong-condition-trigger.json', waiting_condition='different evidence').name,
        )
        self.assertNotEqual(wrong_condition.returncode, 0)
        self.assertIn("condition", wrong_condition.stderr)
        changed_hash = self._run(
            "resume", run_id,
            "--trigger-file",
            command('changed-hash-trigger.json', evidence_ref={**evidence_ref, 'hash': 'sha256:' + '0' * 64}).name,
        )
        self.assertNotEqual(changed_hash.returncode, 0)
        self.assertIn("hash mismatch", changed_hash.stderr)
        self.assertEqual(self._ok("status", run_id)["state"]["state_version"], waiting_version)

        trigger_path = command("matching-trigger.json")
        consumed = self._ok("resume", run_id, "--trigger-file", trigger_path.name)
        self.assertEqual(consumed["status"], "TRIGGER_CONSUMED")
        self.assertEqual(consumed["state"]["status"], "ACTIVE")
        self.assertEqual(consumed["state"]["current_node"], "evidence.collect")
        self.assertEqual(
            consumed["state"]["consumed_wait_triggers"][0]["trigger_id"],
            "trigger-new-evidence-1",
        )
        self.assertEqual(
            consumed["state"]["artifact_refs"]["wait-trigger:trigger-new-evidence-1"]["hash"],
            evidence_ref["hash"],
        )
        trigger_events = [
            event
            for event in verify_event_chain(
                self.project / ".better-product-graph" / "runs" / run_id / "events.jsonl"
            )
            if event["event_type"] == "WAIT_TRIGGER_CONSUMED"
        ]
        self.assertEqual(len(trigger_events), 1)
        self.assertEqual(trigger_events[0]["waiting_condition"], "new material evidence")
        self.assertEqual(trigger_events[0]["evidence_ref"], evidence_ref)
        self.assertEqual(trigger_events[0]["received_at"], "2026-08-20T10:00:00+08:00")
        self.assertEqual(trigger_events[0]["source"], {"kind": "MANUAL", "actor": "eli"})

        replay = self._run("resume", run_id, "--trigger-file", trigger_path.name)
        self.assertNotEqual(replay.returncode, 0)
        self.assertRegex(replay.stderr, "already consumed|WAITING_TRIGGER")

        state_path = self.project / ".better-product-graph" / "runs" / run_id / "state.json"
        tampered = read_json(state_path)
        tampered["consumed_wait_triggers"] = []
        atomic_write_json(state_path, tampered)
        blocked = self._ok("status", run_id)
        self.assertEqual(blocked["status"], "BLOCKED_STALE")
        self.assertTrue(any("WAIT trigger ledger" in item for item in blocked["blockers"]))

    def test_invalid_handoff_path_is_not_exposed_as_public_mechanical_dispatch(self) -> None:
        activated = self._ok("new", "no release cannot handoff")
        run_id = activated["run_id"]
        self._force_node(run_id, "handoff.prepare", ["handoff.dispatch"])

        completed = self._run("--operation", "dispatch", "--run-id", run_id)

        self.assertNotEqual(completed.returncode, 0)

    def test_exact_released_run_completes_terminal_without_host_result_submission(self) -> None:
        assembled = assemble_prd(
            prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        )
        archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={},
            review_companion=finalized_review_companion(assembled),
        )
        candidate = {
            "path": str(archived.path),
            "hash": archived.document_hash,
            "tree_hash": archived.tree_hash,
            "version": archived.version,
        }
        request, archived = materialize_ready_evidence(
            self.project,
            complete_ready_input(candidate),
            archived,
        )
        run_id = request["run_id"]
        controller = StateController(self.project, GRAPH)
        ready_and_release(
            self.project,
            archived,
            request,
            controller=controller,
            run_id=run_id,
        )

        completed = self._ok("--operation", "dispatch", "--run-id", run_id)

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["state"]["status"], "COMPLETED")
        self.assertEqual(completed["state"]["current_node"], "handoff.dispatch")
        self.assertNotIn("dispatch", completed)

    def _complete_happy_installed_review_cycle(
        self,
        run_id: str,
        review_dispatch: dict,
        candidate_ref: dict,
        decision_ref: dict,
        *,
        suffix: str,
    ) -> dict:
        resources = {
            item["resource_id"]: item for item in review_dispatch["resource_refs"]
        }

        def exact(resource_id: str) -> dict:
            return {
                key: resources[resource_id][key]
                for key in ("path", "hash", "version")
            }

        candidate_identity = {
            key: candidate_ref[key] for key in ("path", "hash", "version")
        }
        review_result = {
            "schema_version": "node-result.v1",
            "node_id": "review.parallel",
            "attempt_id": review_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": review_dispatch["instruction_ref"],
            "instruction_hash": review_dispatch["instruction_hash"],
            "input_refs": review_dispatch["input_refs"],
            "input_hashes": review_dispatch["input_hashes"],
            "resource_refs": review_dispatch["resource_refs"],
            "semantic_output": {
                "candidate_ref": candidate_identity,
                "reviewer_role": "combined-advisory-review",
                "reviewer_profile": "product-goal-fidelity-v0.1",
                "roles_covered": [
                    "product",
                    "engineering_feasibility",
                    "testability",
                ],
                "authority": "ADVISORY_ONLY",
                "goal_fidelity_refs": {
                    "profile_ref": exact("goal-fidelity-profile"),
                    "rubric_ref": exact("goal-fidelity-rubric"),
                    "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                    "commitment_refs": [decision_ref],
                },
                "goal_fidelity_packet": {
                    "goal": "Preserve exact product commitments",
                    "candidate_ref": candidate_identity,
                    "commitment_refs": [decision_ref],
                },
                "findings": [],
            },
            "artifact_refs": [],
        }
        aggregate_dispatch = self._ok(
            "--operation",
            "submit",
            "--run-id",
            run_id,
            "--payload-file",
            str(self._payload(f"review-{suffix}.json", review_result)),
            "--requested-node",
            "review.aggregate",
        )["dispatch"]
        aggregate = {
            "schema_version": "review-aggregate.v1",
            "authority": "ADVISORY_ONLY",
            "candidate_ref": candidate_identity,
            "attempts": [
                {
                    "attempt_id": review_dispatch["attempt_id"],
                    "status": "COMPLETED",
                    "roles_covered": [
                        "product",
                        "engineering_feasibility",
                        "testability",
                    ],
                }
            ],
            "findings": [],
            "disagreements": [],
        }
        dispositions = {
            "schema_version": "review-dispositions.v1",
            "candidate_hash": candidate_ref["hash"],
            "candidate_version": candidate_ref["version"],
            "dispositions": [],
        }
        aggregate_path = self.project / f"review-aggregate-{suffix}.json"
        dispositions_path = self.project / f"review-dispositions-{suffix}.json"
        atomic_write_json(aggregate_path, aggregate)
        atomic_write_json(dispositions_path, dispositions)
        aggregate_result = {
            "schema_version": "node-result.v1",
            "node_id": "review.aggregate",
            "attempt_id": aggregate_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": aggregate_dispatch["instruction_ref"],
            "instruction_hash": aggregate_dispatch["instruction_hash"],
            "input_refs": aggregate_dispatch["input_refs"],
            "input_hashes": aggregate_dispatch["input_hashes"],
            "resource_refs": aggregate_dispatch["resource_refs"],
            "semantic_output": {**aggregate, "dispositions": []},
            "artifact_refs": [
                {
                    "role": "review_aggregate",
                    "path": aggregate_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(aggregate_path),
                    "version": 1,
                },
                {
                    "role": "review_dispositions",
                    "path": dispositions_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(dispositions_path),
                    "version": 1,
                },
            ],
        }
        return self._ok(
            "--operation",
            "submit",
            "--run-id",
            run_id,
            "--payload-file",
            str(self._payload(f"aggregate-{suffix}.json", aggregate_result)),
            "--requested-node",
            "review.finalize",
        )

    def _run_installed_review_finalize_lifecycle(
        self,
        *,
        upstream_payloads: dict[str, dict] | None = None,
        forged_reviewed_evals: bool = False,
        self_reviewed_typed_evals: bool = False,
        recommended_evals: bool = False,
        required_evals_repair: bool = False,
        metadata_declared_roles: bool = False,
        candidate_version: str = "v0.1",
        duplicate_decision_ref: bool = False,
        omit_upstream_kind: str | None = None,
        aggregate_attack: str | None = None,
        aggregate_declared_role_metadata: bool = False,
        aggregate_requested_node: str = "review.finalize",
        aggregate_disagreements: object = _DEFAULT_DISAGREEMENTS,
        no_findings: bool = False,
        aggregate_cardinality_attack: str | None = None,
        expect_success: bool = True,
    ):
        run_id = self._ok("new", "real review companion lifecycle")["run_id"]
        upstream_refs = []
        with self.subTest(upstream_authority="real public lifecycle"):
            self._force_node(
                run_id,
                "product.decision",
                ["product.planning", "evidence.collect"],
            )
            decision_dispatch = self._ok(
                "--operation", "dispatch", "--run-id", run_id
            )["dispatch"]
            draft = {
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
            }
            decision_result = {
                "schema_version": "node-result.v1",
                "node_id": "product.decision",
                "attempt_id": decision_dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": decision_dispatch["instruction_ref"],
                "instruction_hash": decision_dispatch["instruction_hash"],
                "input_refs": decision_dispatch["input_refs"],
                "input_hashes": decision_dispatch["input_hashes"],
                "resource_refs": decision_dispatch["resource_refs"],
                "semantic_output": draft,
                "artifact_refs": [],
            }
            proposed = self._ok(
                "--operation", "submit", "--run-id", run_id,
                "--payload-file", str(self._payload("review-decision.json", decision_result)),
            )
            command = {
                "schema_version": "owner-choice-command.v1",
                "decision_id": proposed["proposal"]["decision_id"],
                "proposal_ref": proposed["proposal"]["proposal_ref"],
                "proposal_hash": proposed["proposal"]["proposal_ref"]["hash"],
                "actor": {"kind": "OWNER", "id": "eli"},
                "expected_state_version": proposed["state"]["state_version"],
                "choice": "COMMIT",
                "commit_timing": "NOW",
                "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
            }
            chosen = self._ok(
                "--operation", "owner-choice", "--run-id", run_id,
                "--payload-file", str(self._payload("review-owner-choice.json", command)),
            )
            decision_ref = chosen["state"]["decision"]["record_ref"]
            upstream_refs.append({"kind": "decision", **decision_ref})

            self._force_node(run_id, "evidence.collect", ["evidence.map"])
            evidence_dispatch = self._ok(
                "--operation", "dispatch", "--run-id", run_id
            )["dispatch"]
            evidence_content = {"summary": "Controller-bound local evidence"}
            evidence = {
                "schema_version": "evidence-record.v1",
                "kind": "evidence",
                "version": 1,
                "run_id": run_id,
                "status": "RECORDED",
                "authorized": True,
                "received_at": "2026-08-20T00:00:00+00:00",
                "source": {"kind": "MANUAL"},
                "producer": {
                    "node_id": "evidence.collect",
                    "attempt_id": evidence_dispatch["attempt_id"],
                },
                "content": evidence_content,
                "content_hash": sha256_bytes(canonical_json_bytes(evidence_content)),
            }
            evidence_path = self.project / "evidence-review-lifecycle-v1.json"
            atomic_write_json(evidence_path, evidence)
            evidence_ref = {
                "path": evidence_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(evidence_path),
                "version": 1,
            }
            evidence_result = {
                "schema_version": "node-result.v1",
                "node_id": "evidence.collect",
                "attempt_id": evidence_dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": evidence_dispatch["instruction_ref"],
                "instruction_hash": evidence_dispatch["instruction_hash"],
                "input_refs": evidence_dispatch["input_refs"],
                "input_hashes": evidence_dispatch["input_hashes"],
                "resource_refs": evidence_dispatch["resource_refs"],
                "semantic_output": {"sources": [{"kind": "MANUAL", "ref": evidence_ref}]},
                "artifact_refs": [{"role": "evidence", **evidence_ref}],
            }
            self._ok(
                "--operation", "submit", "--run-id", run_id,
                "--payload-file", str(self._payload("review-evidence.json", evidence_result)),
                "--requested-node", "evidence.map",
            )
            upstream_refs.append({"kind": "evidence", **evidence_ref})

        fixed_origins = {
            "roadmap": ("evidence.collect", "attempt-roadmap-review-lifecycle"),
            "product_plan": ("product.planning", "attempt-slice-review-lifecycle"),
            "slice": ("product.planning", "attempt-slice-review-lifecycle"),
            "knowledge": ("evidence.map", "attempt-knowledge-review-lifecycle"),
        }
        fixed_roles = {
            "roadmap": "node_result",
            "product_plan": "product_plan",
            "slice": "node_result",
            "knowledge": "node_result",
        }
        for kind in ("roadmap", "product_plan", "slice", "knowledge"):
            path = self.project / (
                "product-plan-review-lifecycle-v1.md"
                if kind == "product_plan"
                else f"{kind}-review-lifecycle-v1.json"
            )
            if kind == "product_plan":
                path.write_text(
                    "# Checkout Recovery Product Plan\n\n## Stable Slice\n\n"
                    "PRD-CHECKOUT-001 is bound to slice-1 without a Candidate version.\n",
                    encoding="utf-8",
                )
            else:
                node_id = {
                    "roadmap": "evidence.collect",
                    "slice": "product.planning",
                    "knowledge": "evidence.map",
                }[kind]
                semantic_output = {
                    "roadmap": {"sources": [{"kind": "PROJECT", "ref": "signal-v1.json"}]},
                    "knowledge": {"claims": []},
                }.get(kind)
                artifact_refs = []
                if kind == "slice":
                    semantic_output = complete_plan()
                    semantic_output["decision_ref"] = {
                        key: upstream_refs[0][key] for key in ("path", "hash", "version")
                    }
                    semantic_output["prd_matrix"][0]["planned_prd_id"] = "PRD-CHECKOUT-001"
                    plan_ref = next(
                        item for item in upstream_refs if item["kind"] == "product_plan"
                    )
                    artifact_refs = [
                        {
                            "role": "product_plan",
                            **{
                                key: plan_ref[key] for key in ("path", "hash", "version")
                            },
                        }
                    ]
                atomic_write_json(
                    path,
                    {
                        "schema_version": "node-result.v1",
                        "node_id": node_id,
                        "attempt_id": fixed_origins[kind][1],
                        "producer": {"kind": "HOST_AGENT"},
                        "instruction_ref": f"references/atomic-skills/{kind}/INSTRUCTIONS.md",
                        "instruction_hash": "sha256:native-instruction",
                        "input_refs": ["signal-v1.json"],
                        "input_hashes": {"signal-v1.json": "sha256:signal"},
                        "semantic_output": semantic_output,
                        "artifact_refs": artifact_refs,
                    },
                )
            upstream_refs.append(
                {
                    "kind": kind,
                    "role": fixed_roles[kind],
                    "path": path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(path),
                    "version": 1,
                    "origin_node_id": fixed_origins[kind][0],
                    "origin_attempt_id": fixed_origins[kind][1],
                }
            )
        if upstream_payloads is not None:
            for kind in ("decision", "evidence"):
                if kind not in upstream_payloads:
                    continue
                path = self.project / f"invalid-{kind}-review-lifecycle-v1.json"
                atomic_write_json(path, upstream_payloads[kind])
                replacement = {
                    "kind": kind,
                    "path": path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(path),
                    "version": 1,
                }
                upstream_refs = [
                    replacement if item["kind"] == kind else item
                    for item in upstream_refs
                ]
        by_kind = {item["kind"]: item for item in upstream_refs}
        submission = prd_submission()
        metadata = submission["semantic_output"]["metadata"]
        if candidate_version != metadata["version"]:
            submission["semantic_output"]["document_markdown"] = submission[
                "semantic_output"
            ]["document_markdown"].replace(metadata["version"], candidate_version)
            metadata["version"] = candidate_version

        def metadata_ref(kind: str) -> dict:
            ref = {
                key: by_kind[kind][key] for key in ("path", "hash", "version")
            }
            if metadata_declared_roles:
                ref["role"] = {
                    "decision": "decision_record",
                    "roadmap": "roadmap_snapshot",
                    "product_plan": "product_plan",
                    "slice": "delivery_slice",
                    "knowledge": "knowledge_snapshot",
                    "evidence": "evidence_record",
                }[kind]
            return ref

        metadata["decision_refs"] = [
            metadata_ref("decision")
        ]
        if duplicate_decision_ref:
            metadata["decision_refs"].append(dict(metadata["decision_refs"][0]))
        for field, kind in (
            ("roadmap_snapshot_ref", "roadmap"),
            ("product_plan_ref", "product_plan"),
            ("slice_ref", "slice"),
            ("knowledge_snapshot_ref", "knowledge"),
        ):
            metadata[field] = metadata_ref(kind)
        metadata["evidence_refs"] = [
            metadata_ref("evidence")
        ]
        omitted_fields = {
            "decision": "decision_refs",
            "roadmap": "roadmap_snapshot_ref",
            "product_plan": "product_plan_ref",
            "slice": "slice_ref",
            "knowledge": "knowledge_snapshot_ref",
            "evidence": "evidence_refs",
        }
        if omit_upstream_kind is not None:
            metadata.pop(omitted_fields[omit_upstream_kind])
        if forged_reviewed_evals:
            masquerading_ref = {
                key: by_kind["product_plan"][key]
                for key in ("path", "hash", "version")
            }
            metadata["evals"] = {
                "applicability": "REQUIRED",
                "fulfillment": "REVIEWED",
                "execution_status": "PASSED",
                "pack_ref": {**masquerading_ref, "resolved_hash": masquerading_ref["hash"]},
                "review_ref": masquerading_ref,
                "ground_truth_provenance": "invented by optimizer",
            }
        if recommended_evals:
            metadata["evals"] = {
                "applicability": "RECOMMENDED",
                "fulfillment": "NOT_STARTED",
                "execution_status": "NOT_RUN",
                "reason": "useful downstream specification, not a release condition",
            }
        if required_evals_repair:
            metadata["delivery_intent"] = "EXPERIMENT"
            metadata["evals"] = {
                "applicability": "REQUIRED",
                "fulfillment": "REVIEW_PENDING",
                "execution_status": "NOT_RUN",
            }
        submission["input_refs"] = [item["path"] for item in upstream_refs]
        submission["input_hashes"] = {item["path"]: item["hash"] for item in upstream_refs}
        state = StateController(self.project, GRAPH).load_state(run_id)
        artifact_refs = dict(state["artifact_refs"])
        existing_paths = {ref["path"] for ref in artifact_refs.values()}
        for index, ref in enumerate(upstream_refs):
            if ref["path"] not in existing_paths:
                artifact_refs[f"upstream:{index}"] = ref
                existing_paths.add(ref["path"])
        if "slice_ref" in metadata and "product_plan_ref" in metadata:
            metadata["active_scope_ref"] = derive_active_scope_ref(
                read_json(self.project / metadata["slice_ref"]["path"]),
                metadata["product_plan_ref"],
                metadata["prd_id"],
            )
        trace_pairs = []
        for label, refs in (
            ("decision", metadata.get("decision_refs")),
            ("evidence", metadata.get("evidence_refs")),
        ):
            if isinstance(refs, list):
                trace_pairs.extend(
                    (
                        label if len(refs) == 1 else f"{label}:{index}",
                        ref,
                    )
                    for index, ref in enumerate(refs)
                )
        trace_pairs.extend(
            (role, metadata[field])
            for role, field in (
                ("roadmap", "roadmap_snapshot_ref"),
                ("product_plan", "product_plan_ref"),
                ("slice", "slice_ref"),
                ("knowledge", "knowledge_snapshot_ref"),
            )
            if field in metadata
        )
        try:
            metadata["spec_traceability"] = derive_spec_traceability(
                trace_pairs, artifact_refs
            )
        except ValueError:
            # Negative fixtures intentionally preserve an uncommitted ref so the
            # installed Controller can reject it before Candidate persistence.
            pass
        state_path = self._force_node(
            run_id,
            "prd.generate",
            ["review.parallel"],
            artifact_refs=artifact_refs,
        )
        requested_metadata = json.loads(json.dumps(metadata))
        dispatch = self._ok("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        metadata.update(dispatch["prd_generation_context"]["metadata_authority"])
        if upstream_payloads is not None:
            for kind, field in (
                ("decision", "decision_refs"),
                ("evidence", "evidence_refs"),
            ):
                if kind in upstream_payloads:
                    metadata[field] = requested_metadata[field]
        if duplicate_decision_ref:
            metadata["decision_refs"].append(dict(metadata["decision_refs"][0]))
        if omit_upstream_kind is not None:
            metadata.pop(omitted_fields[omit_upstream_kind], None)
        if metadata_declared_roles:
            for ref in metadata["decision_refs"]:
                ref["role"] = "decision_record"
            for field, role in (
                ("roadmap_snapshot_ref", "roadmap_snapshot"),
                ("product_plan_ref", "product_plan"),
                ("slice_ref", "delivery_slice"),
                ("knowledge_snapshot_ref", "knowledge_snapshot"),
            ):
                metadata[field]["role"] = role
            for ref in metadata["evidence_refs"]:
                ref["role"] = "evidence_record"
        typed_eval_review_ref = None
        typed_prd_artifact_refs = []
        if self_reviewed_typed_evals:
            draft_path = self.project / "forged-evals" / "candidate-draft-v0.1.md"
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            draft_path.write_text(
                submission["semantic_output"]["document_markdown"], encoding="utf-8"
            )
            draft_ref = {
                "path": draft_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(draft_path),
                "version": metadata["version"],
            }
            fixtures_path = self.project / "forged-evals" / "fixtures-v1.json"
            atomic_write_json(
                fixtures_path,
                {"fixtures": [{"input": "same Host", "expected": "claim independent"}]},
            )
            fixtures_ref = {
                "path": fixtures_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(fixtures_path),
                "version": 1,
            }
            raw_ref = {
                **read_json(state_path)["artifact_refs"]["raw_signal"],
                "version": 1,
            }
            provenance = {
                "type": "CONTRACT_DERIVED_EXPECTATIONS",
                "statement": "The same Host labels an arbitrary Raw Signal as a contract.",
                "exact_refs": [raw_ref],
            }
            pack_path = self.project / "forged-evals" / "eval-pack-v1.json"
            pack = {
                "schema_version": "better-product-graph.eval-pack.v1",
                "status": "SPECIFICATION_REVIEW_PENDING",
                "candidate_ref": draft_ref,
                "applicability": "REQUIRED",
                "execution_status": "NOT_RUN",
                "ground_truth_provenance": provenance,
                "producer": {"kind": "SUBAGENT", "id": "planner-claimed-by-host"},
                "evaluator_contract": {
                    "contract_id": "same-host-forgery-v1",
                    "fixtures_ref": fixtures_ref,
                },
                "cases": [
                    {
                        "case_id": "same-host-review",
                        "expected_outcome": "independent fulfillment claimed without proof",
                    }
                ],
            }
            atomic_write_json(pack_path, pack)
            pack_ref = {
                "path": pack_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(pack_path),
                "version": 1,
            }
            review_path = self.project / "forged-evals" / "eval-pack-review-v1.json"
            review = {
                "schema_version": "better-product-graph.eval-pack-review.v1",
                "status": "REVIEWED",
                "execution_status": "NOT_RUN",
                "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
                "reviewer_authority": "ADVISORY_ONLY",
                "reviewer": {"kind": "SUBAGENT", "id": "reviewer-claimed-by-same-host"},
                "reviewed_at": "2026-08-20T12:00:00+08:00",
                "subjects": {
                    "prd_draft_ref": draft_ref,
                    "fixtures_ref": fixtures_ref,
                    "eval_pack_ref": pack_ref,
                },
                "finding_closure": [],
                "new_high_findings": 0,
                "evidence_boundary": {
                    "runtime_execution": "NOT_RUN",
                    "test_execution": "NOT_RUN",
                    "independent_reader_validation": "NOT_RUN",
                },
            }
            atomic_write_json(review_path, review)
            typed_eval_review_ref = {
                "path": review_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(review_path),
                "version": 1,
            }
            metadata["evals"] = {
                "applicability": "REQUIRED",
                "fulfillment": "REVIEWED",
                "execution_status": "NOT_RUN",
                "pack_ref": {**pack_ref, "resolved_hash": pack_ref["hash"]},
                "review_ref": {
                    **typed_eval_review_ref,
                    "resolved_hash": typed_eval_review_ref["hash"],
                },
                "ground_truth_provenance": provenance,
            }
            typed_prd_artifact_refs = [
                {"role": "raw_signal", **raw_ref},
                {"role": "prd_draft", **draft_ref},
                {"role": "eval_fixtures", **fixtures_ref},
                {"role": "eval_pack", **pack_ref},
            ]
        prd_result = json.loads(json.dumps(submission))
        prd_result.update(
            {
                "schema_version": "node-result.v1",
                "attempt_id": dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": dispatch["instruction_ref"],
                "instruction_hash": dispatch["instruction_hash"],
                "input_refs": dispatch["input_refs"],
                "input_hashes": dispatch["input_hashes"],
                "resource_refs": dispatch["resource_refs"],
                "artifact_refs": typed_prd_artifact_refs,
            }
        )
        generate_payload = self._payload("prd-generate-result.json", prd_result)
        generate_guard = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }
        generate_process = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(generate_payload),
            "--requested-node", "review.parallel",
        )
        if generate_process.returncode != 0:
            if not expect_success:
                self._last_generate_guard = generate_guard
                return generate_process, run_id, None, None
            self.fail(generate_process.stderr)
        review_dispatch = json.loads(generate_process.stdout)["dispatch"]
        state = read_json(state_path)
        candidate_ref = state["current_candidate_ref"]
        archived_path = self.project / candidate_ref["artifact_path"]
        review_path = self.project / candidate_ref["review_path"]
        self.assertEqual(read_json(review_path)["status"], "NOT_RUN")
        original_tree_hash = candidate_ref["tree_hash"]

        if required_evals_repair:
            decision_ref = {
                key: by_kind["decision"][key] for key in ("path", "hash", "version")
            }
            pending = self._complete_happy_installed_review_cycle(
                run_id,
                review_dispatch,
                candidate_ref,
                decision_ref,
                suffix="before-evals",
            )
            self.assertEqual(pending["status"], "EVALS_FULFILLMENT_REQUIRED")
            resumed = self._ok("resume", run_id)
            self.assertEqual(resumed["status"], "EVALS_FULFILLMENT_REQUIRED")
            self.assertEqual(resumed["repair_operation"], "fulfill-evals")
            self.assertEqual(resumed["execution_status"], "NOT_RUN")
            self.assertEqual(resumed["next_nodes"], ["review.parallel"])
            candidate_identity = resumed["candidate_ref"]
            self.assertEqual(candidate_identity, pending["candidate_ref"])
            self.assertEqual(
                set(candidate_identity), {"path", "hash", "version"}
            )
            fixtures_path = self.project / "required-evals" / "fixtures.json"
            atomic_write_json(
                fixtures_path,
                {"schema_version": "eval-fixtures.v1", "cases": ["continue", "stop"]},
            )
            fixtures_ref = {
                "path": fixtures_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(fixtures_path),
                "version": 1,
            }
            pack_path = self.project / "required-evals" / "eval-pack.json"
            pack = {
                "schema_version": "better-product-graph.eval-pack.v1",
                "status": "SPECIFICATION_REVIEW_PENDING",
                "candidate_ref": candidate_identity,
                "applicability": "REQUIRED",
                "execution_status": "NOT_RUN",
                "ground_truth_provenance": {
                    "type": "CONTRACT_DERIVED_EXPECTATIONS",
                    "statement": "Expected outcomes derive from the exact Decision contract.",
                    "exact_refs": [decision_ref],
                },
                "producer": {"kind": "HOST_AGENT", "id": "eval-pack-builder"},
                "evaluator_contract": {
                    "contract_id": "required-evals-lifecycle",
                    "fixtures_ref": fixtures_ref,
                },
                "cases": [
                    {"case_id": "continue", "expected_outcome": "CONTINUE"},
                    {"case_id": "stop", "expected_outcome": "STOP"},
                ],
            }
            atomic_write_json(pack_path, pack)
            pack_ref = {
                "path": pack_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(pack_path),
                "version": 1,
            }
            eval_review_path = self.project / "required-evals" / "eval-review.json"
            atomic_write_json(
                eval_review_path,
                {
                    "schema_version": "better-product-graph.eval-pack-review.v1",
                    "status": "REVIEWED",
                    "execution_status": "NOT_RUN",
                    "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
                    "reviewer_authority": "ADVISORY_ONLY",
                    "reviewer": {"kind": "SUBAGENT", "id": "eval-reviewer"},
                    "reviewed_at": "2026-08-24T12:00:00+00:00",
                    "subjects": {
                        "prd_draft_ref": candidate_identity,
                        "fixtures_ref": fixtures_ref,
                        "eval_pack_ref": pack_ref,
                    },
                    "finding_closure": [],
                    "new_high_findings": 0,
                    "evidence_boundary": {
                        "runtime_execution": "NOT_RUN",
                        "test_execution": "NOT_RUN",
                        "independent_reader_validation": "NOT_RUN",
                    },
                },
            )
            eval_review_ref = {
                "path": eval_review_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(eval_review_path),
                "version": 1,
            }
            fulfillment = self._ok(
                "--operation",
                "fulfill-evals",
                "--run-id",
                run_id,
                "--payload-file",
                str(
                    self._payload(
                        "required-evals-fulfillment.json",
                        {
                            "schema_version": "evals-fulfillment-submission.v1",
                            "candidate_ref": candidate_identity,
                            "build_attempt": {
                                "kind": "HOST_AGENT",
                                "id": "eval-pack-builder",
                            },
                            "review_attempt": {
                                "kind": "SUBAGENT",
                                "id": "eval-reviewer",
                            },
                            "eval_pack_ref": pack_ref,
                            "fixtures_ref": fixtures_ref,
                            "review_ref": eval_review_ref,
                        },
                    )
                ),
            )
            completed = self._complete_happy_installed_review_cycle(
                run_id,
                fulfillment["dispatch"],
                fulfillment["state"]["current_candidate_ref"],
                decision_ref,
                suffix="after-evals",
            )
            state = completed["state"]
            metadata_path = next(
                (self.project / state["current_candidate_ref"]["artifact_path"]).glob(
                    "*.metadata.json"
                )
            )
            evals = read_json(metadata_path)["evals"]
            self.assertEqual(completed["status"], "COMPLETED")
            self.assertEqual(state["current_node"], "handoff.dispatch")
            self.assertEqual(evals["fulfillment"], "REVIEWED")
            self.assertEqual(evals["execution_status"], "NOT_RUN")
            self.assertIsNotNone(state["release_ref"])
            ready_assertion = read_json(self.project / state["release_ref"]["path"])
            self.assertEqual(ready_assertion["tests_executed"], "NOT_CLAIMED")
            return completed, run_id, archived_path, review_path

        resources = {item["resource_id"]: item for item in review_dispatch["resource_refs"]}

        def exact(resource_id: str) -> dict:
            return {
                key: resources[resource_id][key]
                for key in ("path", "hash", "version")
            }

        candidate_identity = {
            key: candidate_ref[key] for key in ("path", "hash", "version")
        }
        decision_ref = {
            key: by_kind["decision"][key] for key in ("path", "hash", "version")
        }
        finding = {
            "finding_id": "finding-1",
            "topic_id": "recovery",
            "stance": "boundary-visible",
            "concern": "show recovery boundary",
            "concern_level": "KEY_ATTENTION",
            "basis_refs": [candidate_ref["path"], decision_ref["path"]],
            "possible_impact": "unclear recovery",
            "professional_recommendation": "retain explicit evidence boundary",
            "confidence": "high",
            "confidence_basis": "exact Candidate and Decision refs",
        }
        if aggregate_attack == "unknown_finding_field":
            finding["future_authority"] = "ACCEPT"
        review_result = {
            "schema_version": "node-result.v1",
            "node_id": "review.parallel",
            "attempt_id": review_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": review_dispatch["instruction_ref"],
            "instruction_hash": review_dispatch["instruction_hash"],
            "input_refs": review_dispatch["input_refs"],
            "input_hashes": review_dispatch["input_hashes"],
            "resource_refs": review_dispatch["resource_refs"],
            "semantic_output": {
                "candidate_ref": candidate_identity,
                "reviewer_role": "combined-advisory-review",
                "reviewer_profile": "product-goal-fidelity-v0.1",
                "roles_covered": ["product", "engineering_feasibility", "testability"],
                "authority": "ADVISORY_ONLY",
                "goal_fidelity_refs": {
                    "profile_ref": exact("goal-fidelity-profile"),
                    "rubric_ref": exact("goal-fidelity-rubric"),
                    "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                    "commitment_refs": [decision_ref],
                },
                "goal_fidelity_packet": {
                    "goal": "保持已确认产品目标与范围承诺",
                    "candidate_ref": candidate_identity,
                    "commitment_refs": [decision_ref],
                },
                "findings": [] if no_findings else [finding],
            },
            "artifact_refs": (
                [{"role": "eval_pack_review", **typed_eval_review_ref}]
                if typed_eval_review_ref is not None
                else []
            ),
        }
        aggregate_dispatch = self._ok(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._payload("review-parallel-result.json", review_result)),
            "--requested-node", "review.aggregate",
        )["dispatch"]

        aggregate = {
            "schema_version": "review-aggregate.v1",
            "authority": "ADVISORY_ONLY",
            "candidate_ref": candidate_identity,
            "attempts": [
                {
                    "attempt_id": review_dispatch["attempt_id"],
                    "status": "COMPLETED",
                    "roles_covered": ["product", "engineering_feasibility", "testability"],
                },
            ],
            "findings": [] if no_findings else [finding],
            "disagreements": (
                []
                if no_findings
                else [{"topic_id": "recovery", "finding_ids": ["finding-1"]}]
            ),
        }
        if aggregate_disagreements is not _DEFAULT_DISAGREEMENTS:
            aggregate["disagreements"] = aggregate_disagreements
        dispositions = {
            "schema_version": "review-dispositions.v1",
            "candidate_hash": candidate_ref["hash"],
            "candidate_version": candidate_ref["version"],
            "dispositions": (
                []
                if no_findings
                else [{"finding_id": "finding-1", "status": "ADDRESSED"}]
            ),
        }
        aggregate_path = self.project / "review-aggregate-lifecycle.json"
        dispositions_path = self.project / "review-dispositions-lifecycle.json"
        atomic_write_json(aggregate_path, aggregate)
        atomic_write_json(dispositions_path, dispositions)
        result = {
            "schema_version": "node-result.v1",
            "node_id": "review.aggregate",
            "attempt_id": aggregate_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": aggregate_dispatch["instruction_ref"],
            "instruction_hash": aggregate_dispatch["instruction_hash"],
            "input_refs": aggregate_dispatch["input_refs"],
            "input_hashes": aggregate_dispatch["input_hashes"],
            "resource_refs": aggregate_dispatch["resource_refs"],
            "semantic_output": {**aggregate, "dispositions": dispositions["dispositions"]},
            "artifact_refs": [
                {
                    "role": "review_aggregate",
                    "path": aggregate_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(aggregate_path),
                    "version": 1,
                },
                {
                    "role": "review_dispositions",
                    "path": dispositions_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(dispositions_path),
                    "version": 1,
                },
            ],
        }
        if aggregate_declared_role_metadata:
            result["artifact_refs"][0]["declared_role"] = "review_dispositions"
            result["artifact_refs"][1]["declared_role"] = "review_aggregate"
        if aggregate_attack == "missing_artifacts":
            result["artifact_refs"] = []
        elif aggregate_attack == "duplicate_aggregate":
            result["artifact_refs"].append(dict(result["artifact_refs"][0]))
        elif aggregate_attack == "stale_candidate":
            result["semantic_output"]["candidate_ref"] = {
                **candidate_identity,
                "version": "v0.4",
            }
        elif aggregate_attack == "forged_findings":
            result["semantic_output"]["findings"] = [
                {**finding, "finding_id": "forged-finding"}
            ]
        elif aggregate_attack == "path_escape":
            result["artifact_refs"][0] = {
                **result["artifact_refs"][0],
                "path": "../../review-aggregate-lifecycle.json",
            }
        elif aggregate_attack == "missing_version":
            result["artifact_refs"][1].pop("version")
        elif aggregate_attack == "missing_disagreements":
            result["semantic_output"].pop("disagreements")
        elif aggregate_attack == "unknown_top_level_field":
            aggregate["future_authority"] = "ACCEPT"
            result["semantic_output"]["future_authority"] = "ACCEPT"
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_disagreement_field":
            value = [
                {
                    "topic_id": "recovery",
                    "finding_ids": ["finding-1"],
                    "future_authority": "ACCEPT",
                }
            ]
            aggregate["disagreements"] = value
            result["semantic_output"]["disagreements"] = value
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_attempt_field":
            aggregate["attempts"][0]["future_authority"] = "ACCEPT"
            result["semantic_output"]["attempts"] = aggregate["attempts"]
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_candidate_field":
            aggregate["candidate_ref"]["future_authority"] = "ACCEPT"
            result["semantic_output"]["candidate_ref"] = aggregate["candidate_ref"]
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_disposition_field":
            dispositions["dispositions"][0]["future_authority"] = "ACCEPT"
            result["semantic_output"]["dispositions"] = dispositions["dispositions"]
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        elif aggregate_attack == "unknown_disposition_artifact_field":
            dispositions["future_authority"] = "ACCEPT"
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        elif aggregate_attack == "unknown_artifact_ref_field":
            result["artifact_refs"][0]["future_authority"] = "ACCEPT"
        elif aggregate_attack == "unknown_aggregate_artifact_field":
            aggregate["future_authority"] = "ACCEPT"
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_aggregate_artifact_attempt_field":
            semantic_output = json.loads(json.dumps(result["semantic_output"]))
            aggregate["attempts"][0]["future_authority"] = "ACCEPT"
            result["semantic_output"] = semantic_output
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_aggregate_artifact_finding_field":
            semantic_output = json.loads(json.dumps(result["semantic_output"]))
            aggregate["findings"][0]["future_authority"] = "ACCEPT"
            result["semantic_output"] = semantic_output
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_aggregate_artifact_disagreement_field":
            semantic_output = json.loads(json.dumps(result["semantic_output"]))
            aggregate["disagreements"][0]["future_authority"] = "ACCEPT"
            result["semantic_output"] = semantic_output
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_aggregate_artifact_candidate_field":
            semantic_output = json.loads(json.dumps(result["semantic_output"]))
            aggregate["candidate_ref"]["future_authority"] = "ACCEPT"
            result["semantic_output"] = semantic_output
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_attack == "unknown_disposition_artifact_item_field":
            semantic_output = json.loads(json.dumps(result["semantic_output"]))
            dispositions["dispositions"][0]["future_authority"] = "ACCEPT"
            result["semantic_output"] = semantic_output
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        if aggregate_cardinality_attack == "findings_missing":
            result["semantic_output"].pop("findings")
        elif aggregate_cardinality_attack == "findings_null":
            result["semantic_output"]["findings"] = None
        elif aggregate_cardinality_attack == "findings_wrong_type":
            result["semantic_output"]["findings"] = {"finding-1": finding}
        elif aggregate_cardinality_attack == "empty_findings_nonempty_dispositions":
            value = [{"finding_id": "invented-finding", "status": "ADDRESSED"}]
            dispositions["dispositions"] = value
            result["semantic_output"]["dispositions"] = value
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        elif aggregate_cardinality_attack == "nonempty_findings_empty_dispositions":
            dispositions["dispositions"] = []
            result["semantic_output"]["dispositions"] = []
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        elif aggregate_cardinality_attack == "nonempty_findings_missing_dispositions":
            dispositions.pop("dispositions")
            result["semantic_output"].pop("dispositions")
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        elif aggregate_cardinality_attack == "nonempty_findings_duplicate_dispositions":
            value = [
                {"finding_id": "finding-1", "status": "ADDRESSED"},
                {"finding_id": "finding-1", "status": "ADDRESSED"},
            ]
            dispositions["dispositions"] = value
            result["semantic_output"]["dispositions"] = value
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        elif aggregate_cardinality_attack == "nonempty_findings_unmatched_disposition":
            value = [{"finding_id": "finding-other", "status": "ADDRESSED"}]
            dispositions["dispositions"] = value
            result["semantic_output"]["dispositions"] = value
            atomic_write_json(dispositions_path, dispositions)
            result["artifact_refs"][1]["hash"] = sha256_file(dispositions_path)
        elif aggregate_cardinality_attack == "attempts_empty":
            aggregate["attempts"] = []
            result["semantic_output"]["attempts"] = []
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_cardinality_attack == "roles_empty":
            aggregate["attempts"][0]["roles_covered"] = []
            result["semantic_output"]["attempts"] = aggregate["attempts"]
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        elif aggregate_cardinality_attack == "disagreement_unknown_finding":
            value = [{"topic_id": "recovery", "finding_ids": ["finding-other"]}]
            aggregate["disagreements"] = value
            result["semantic_output"]["disagreements"] = value
            atomic_write_json(aggregate_path, aggregate)
            result["artifact_refs"][0]["hash"] = sha256_file(aggregate_path)
        result_payload = self._payload("review-aggregate-result.json", result)
        self._last_aggregate_guard = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }
        self._last_aggregate_run_guard = self._run_inventory(run_id)
        completed_process = self._run(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(result_payload),
            "--requested-node", aggregate_requested_node,
        )
        if not expect_success:
            return completed_process, run_id, archived_path, review_path
        self.assertEqual(completed_process.returncode, 0, completed_process.stderr)
        completed = json.loads(completed_process.stdout)

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["state"]["status"], "COMPLETED")
        current = completed["state"]["current_candidate_ref"]
        self.assertEqual(current["hash"], candidate_ref["hash"])
        self.assertEqual(current["version"], candidate_ref["version"])
        self.assertEqual(current["generation"], 2)
        self.assertNotEqual(current["tree_hash"], original_tree_hash)
        finalized = read_json(review_path)
        self.assertEqual(finalized["status"], "FINALIZED")
        self.assertEqual(finalized["candidate_hash"], candidate_ref["hash"])
        history = (
            self.project / ".better-product-graph" / "runs" / run_id
            / "candidate-generations" / "generation-1" / archived_path.name
        )
        self.assertEqual(read_json(history / review_path.name)["status"], "NOT_RUN")
        released = self.project / "artifacts" / "prds" / "released" / archived_path.name
        self.assertEqual(read_json(released / review_path.name)["status"], "FINALIZED")
        return completed, run_id, archived_path, review_path

    def test_installed_review_finalize_creates_same_version_controller_companion(self) -> None:
        self._run_installed_review_finalize_lifecycle()

    def test_installed_review_aggregate_accepts_explicit_empty_disagreements(self) -> None:
        completed, _run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                recommended_evals=True,
                candidate_version="v0.6",
                aggregate_disagreements=[],
            )
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertTrue(
            (self.project / "artifacts" / "prds" / "released" / archived_path.name).is_dir()
        )

    def test_installed_review_aggregate_accepts_no_findings_without_fabrication(self) -> None:
        completed, _run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                recommended_evals=True,
                candidate_version="v0.17",
                no_findings=True,
            )
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["state"]["current_node"], "handoff.dispatch")
        self.assertTrue(
            (self.project / "artifacts" / "prds" / "released" / archived_path.name).is_dir()
        )

    def test_required_evals_repair_reaches_original_ready_release_and_handoff(self) -> None:
        completed, _run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                required_evals_repair=True,
                candidate_version="v0.203",
            )
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertTrue(
            (self.project / "artifacts" / "prds" / "released" / archived_path.name).is_dir()
        )

    def test_installed_review_aggregate_rejects_invalid_collection_cardinality_without_writes(self) -> None:
        cases = (
            ("findings_missing", "v0.171", False, "findings"),
            ("findings_null", "v0.172", False, "findings"),
            ("findings_wrong_type", "v0.173", False, "findings"),
            (
                "empty_findings_nonempty_dispositions",
                "v0.174",
                True,
                "dispositions",
            ),
            (
                "nonempty_findings_empty_dispositions",
                "v0.175",
                False,
                "disposition",
            ),
            (
                "nonempty_findings_missing_dispositions",
                "v0.176",
                False,
                "dispositions",
            ),
            (
                "nonempty_findings_duplicate_dispositions",
                "v0.177",
                False,
                "disposition",
            ),
            (
                "nonempty_findings_unmatched_disposition",
                "v0.178",
                False,
                "disposition",
            ),
            ("attempts_empty", "v0.179", False, "attempts"),
            ("roles_empty", "v0.180", False, "roles"),
            (
                "disagreement_unknown_finding",
                "v0.181",
                False,
                "Finding",
            ),
        )
        for attack, version, no_findings, expected_error in cases:
            with self.subTest(attack=attack):
                completed, run_id, _archived_path, _review_path = (
                    self._run_installed_review_finalize_lifecycle(
                        recommended_evals=True,
                        candidate_version=version,
                        no_findings=no_findings,
                        aggregate_cardinality_attack=attack,
                        expect_success=False,
                    )
                )

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected_error.lower(), completed.stderr.lower())
                self.assertEqual(
                    self._run_inventory(run_id),
                    self._last_aggregate_run_guard,
                )

    def test_installed_review_aggregate_rejects_invalid_disagreement_shape_without_side_effects(self) -> None:
        cases = (
            ("missing", "v0.61", _DEFAULT_DISAGREEMENTS, "disagreements"),
            ("null", "v0.62", None, "disagreements"),
            ("wrong-type", "v0.63", "none", "disagreements"),
            (
                "incomplete-entry",
                "v0.64",
                [{"topic_id": "recovery"}],
                "disagreement",
            ),
        )
        for label, candidate_version, disagreement_value, expected_error in cases:
            with self.subTest(label=label):
                if label == "missing":
                    disagreement_value = _DEFAULT_DISAGREEMENTS
                completed, run_id, _archived_path, _review_path = (
                    self._run_installed_review_finalize_lifecycle(
                        recommended_evals=True,
                        candidate_version=candidate_version,
                        aggregate_disagreements=disagreement_value,
                        aggregate_attack=(
                            "missing_disagreements" if label == "missing" else None
                        ),
                        expect_success=False,
                    )
                )

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected_error, completed.stderr.lower())
                after = {
                    path.relative_to(self.project).as_posix(): path.read_bytes()
                    for path in self.project.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, self._last_aggregate_guard)
                state = read_json(
                    self.project
                    / ".better-product-graph"
                    / "runs"
                    / run_id
                    / "state.json"
                )
                self.assertEqual(state["current_node"], "review.aggregate")

    def test_installed_review_aggregate_rejects_unknown_fields_at_every_nested_boundary(self) -> None:
        cases = (
            ("unknown_top_level_field", "v0.81", "semantic_output.future_authority"),
            (
                "unknown_disagreement_field",
                "v0.82",
                "semantic_output.disagreements[0].future_authority",
            ),
            ("unknown_attempt_field", "v0.83", "semantic_output.attempts[0].future_authority"),
            ("unknown_finding_field", "v0.84", "semantic_output.findings[0].future_authority"),
            (
                "unknown_disposition_field",
                "v0.85",
                "semantic_output.dispositions[0].future_authority",
            ),
            (
                "unknown_candidate_field",
                "v0.86",
                "semantic_output.candidate_ref.future_authority",
            ),
            (
                "unknown_disposition_artifact_field",
                "v0.87",
                "review_dispositions.future_authority",
            ),
            (
                "unknown_artifact_ref_field",
                "v0.88",
                "artifact_refs[0].future_authority",
            ),
            (
                "unknown_aggregate_artifact_field",
                "v0.89",
                "review_aggregate.future_authority",
            ),
            (
                "unknown_aggregate_artifact_attempt_field",
                "v0.90",
                "review_aggregate.attempts[0].future_authority",
            ),
            (
                "unknown_aggregate_artifact_finding_field",
                "v0.91",
                "review_aggregate.findings[0].future_authority",
            ),
            (
                "unknown_aggregate_artifact_disagreement_field",
                "v0.92",
                "review_aggregate.disagreements[0].future_authority",
            ),
            (
                "unknown_aggregate_artifact_candidate_field",
                "v0.93",
                "review_aggregate.candidate_ref.future_authority",
            ),
            (
                "unknown_disposition_artifact_item_field",
                "v0.94",
                "review_dispositions.dispositions[0].future_authority",
            ),
        )
        for attack, candidate_version, expected_path in cases:
            with self.subTest(attack=attack):
                completed, run_id, _archived_path, _review_path = (
                    self._run_installed_review_finalize_lifecycle(
                        recommended_evals=True,
                        candidate_version=candidate_version,
                        aggregate_attack=attack,
                        expect_success=False,
                    )
                )

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected_path, completed.stderr)
                self.assertEqual(
                    self._run_inventory(run_id),
                    self._last_aggregate_run_guard,
                )
                state = read_json(
                    self.project
                    / ".better-product-graph"
                    / "runs"
                    / run_id
                    / "state.json"
                )
                self.assertEqual(state["current_node"], "review.aggregate")

    def test_installed_review_aggregate_instruction_is_complete_for_first_submission(self) -> None:
        instruction = (
            self.plugin
            / "skills"
            / "better-product-graph"
            / "references"
            / "atomic-skills"
            / "prd-review"
            / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("<!-- review-aggregate-semantic-output-contract -->", instruction)
        contract_match = re.search(
            r"<!-- review-aggregate-semantic-output-contract -->\s*```json\s*(.*?)\s*```",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(contract_match)
        contract = json.loads(contract_match.group(1))
        self.assertEqual(
            contract["semantic_output"]["schema_version"],
            "review-aggregate.v1",
        )
        self.assertEqual(contract["semantic_output"]["disagreements"], [])
        self.assertIn("Use `[]` when no material disagreement exists", instruction)
        self.assertIn("never invent a Finding", instruction)
        self.assertIn(
            "Do not add a new confirmation or consent checkpoint when exact commitments already authorize an automatic operation",
            instruction,
        )
        self.assertIn(
            "authorization for the operation from undisclosed extra side effects",
            instruction,
        )
        self.assertIn("Collection cardinality is exact", instruction)
        self.assertIn("closed-world `review.aggregate` contract", instruction)
        self.assertIn("An unknown key at any of these paths is a repair condition", instruction)
        self.assertIn('`status`: `ACCEPTED_CURRENT_PRD_REPAIR`', instruction)
        self.assertIn('`repair_target`: `CURRENT_PRD`', instruction)
        self.assertIn('`repair_scope` must be a non-empty JSON list', instruction)
        self.assertIn(
            '"status": "ACCEPTED_CURRENT_PRD_REPAIR"',
            instruction,
        )
        self.assertEqual(
            [item["role"] for item in contract["artifact_refs"]],
            ["review_aggregate", "review_dispositions"],
        )
        for required in (
            '"schema_version": "review-aggregate.v1"',
            '"candidate_ref"',
            '"attempts"',
            '"findings"',
            '"disagreements"',
            '"dispositions"',
            '"role": "review_aggregate"',
            '"role": "review_dispositions"',
            '"candidate_hash"',
            '"candidate_version"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, instruction)

        no_finding_match = re.search(
            r"<!-- review-aggregate-no-finding-example -->\s*```json\s*(.*?)\s*```",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(no_finding_match)
        no_finding = json.loads(no_finding_match.group(1))
        self.assertEqual(no_finding["semantic_output"]["findings"], [])
        self.assertEqual(no_finding["semantic_output"]["dispositions"], [])
        self.assertEqual(no_finding["semantic_output"]["disagreements"], [])
        self.assertGreaterEqual(len(no_finding["semantic_output"]["attempts"]), 1)

    def test_installed_review_aggregate_rejects_invalid_authority_before_any_side_effect(self) -> None:
        cases = (
            ("missing_artifacts", "v0.5", "review_aggregate"),
            ("duplicate_aggregate", "v0.6", "exactly one"),
            ("stale_candidate", "v0.7", "Candidate"),
            ("forged_findings", "v0.8", "findings"),
            ("path_escape", "v0.9", "escapes project root"),
            ("missing_version", "v1.0", "role/path/hash/version"),
        )
        for attack, candidate_version, expected_error in cases:
            with self.subTest(attack=attack):
                completed, run_id, archived_path, review_path = (
                    self._run_installed_review_finalize_lifecycle(
                        recommended_evals=True,
                        candidate_version=candidate_version,
                        aggregate_attack=attack,
                        expect_success=False,
                    )
                )

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected_error, completed.stderr)
                after = {
                    path.relative_to(self.project).as_posix(): path.read_bytes()
                    for path in self.project.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, self._last_aggregate_guard)
                state = read_json(
                    self.project
                    / ".better-product-graph"
                    / "runs"
                    / run_id
                    / "state.json"
                )
                self.assertEqual(state["current_node"], "review.aggregate")
                self.assertNotIn(
                    self._ok(
                        "--operation", "dispatch", "--run-id", run_id
                    )["dispatch"]["attempt_id"],
                    state["consumed_attempts"],
                )
                self.assertIsNotNone(archived_path)
                self.assertIsNotNone(review_path)

    def test_installed_v05_recommended_review_to_handoff_is_reachable(self) -> None:
        completed, _run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                recommended_evals=True,
                candidate_version="v0.5",
                aggregate_declared_role_metadata=True,
            )
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["state"]["current_node"], "handoff.dispatch")
        self.assertTrue(
            (self.project / "artifacts" / "prds" / "released" / archived_path.name).is_dir()
        )
        finalize_results = []
        for result_path in (
            self.project / ".better-product-graph" / "runs" / completed["state"]["run_id"]
        ).glob("attempts/*/node-result.json"):
            result = read_json(result_path)
            if result.get("node_id") == "review.finalize":
                finalize_results.append(result)
        self.assertEqual(len(finalize_results), 1)
        finalized_refs = finalize_results[0]["artifact_refs"]
        self.assertEqual(
            {
                item["role"]
                for item in finalized_refs
                if item["role"].startswith("review_")
            },
            {"review_companion", "review_aggregate", "review_dispositions"},
        )
        self.assertTrue(
            all("declared_role" not in item for item in finalized_refs)
        )

    def test_installed_review_aggregate_rejects_unreachable_optimize_route_before_side_effects(self) -> None:
        completed, run_id, _archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                recommended_evals=True,
                candidate_version="v0.5",
                aggregate_requested_node="prd.optimize",
                expect_success=False,
            )
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("accepted current-PRD repair", completed.stderr)
        after = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, self._last_aggregate_guard)
        state = read_json(
            self.project / ".better-product-graph" / "runs" / run_id / "state.json"
        )
        self.assertEqual(state["current_node"], "review.aggregate")

    def test_installed_recommended_evals_can_complete_without_fulfillment_authority(self) -> None:
        completed, _run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(recommended_evals=True)
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertTrue(
            (self.project / "artifacts" / "prds" / "released" / archived_path.name).is_dir()
        )

    def test_installed_v04_metadata_roles_are_non_authoritative_and_release_handoff_completes(self) -> None:
        completed, run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                recommended_evals=True,
                metadata_declared_roles=True,
                candidate_version="v0.4",
            )
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["state"]["current_node"], "handoff.dispatch")
        self.assertTrue(
            (self.project / "artifacts" / "prds" / "released" / archived_path.name).is_dir()
        )
        receipt = read_json(
            self.project
            / ".better-product-graph"
            / "runs"
            / run_id
            / "receipts"
            / "mechanical-contracts.json"
        )
        upstream = [
            item for item in receipt["subject_refs"]
            if item["role"].startswith("upstream_")
        ]
        self.assertEqual(
            {item["role"] for item in upstream},
            {
                "upstream_decision",
                "upstream_roadmap",
                "upstream_product_plan",
                "upstream_slice",
                "upstream_knowledge",
                "upstream_evidence",
            },
        )
        self.assertEqual(
            {item["declared_role"] for item in upstream},
            {
                "decision_record",
                "roadmap_snapshot",
                "product_plan",
                "delivery_slice",
                "knowledge_snapshot",
                "evidence_record",
            },
        )

    def test_installed_duplicate_or_missing_upstream_fact_fails_before_candidate_side_effects(self) -> None:
        cases = (
            ({"duplicate_decision_ref": True}, "decision_refs differs from exact dispatch authority"),
            ({"omit_upstream_kind": "knowledge"}, "knowledge_snapshot_ref"),
        )
        for options, expected_error in cases:
            with self.subTest(options=options):
                completed, run_id, archived_path, review_path = (
                    self._run_installed_review_finalize_lifecycle(
                        recommended_evals=True,
                        expect_success=False,
                        **options,
                    )
                )

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected_error, completed.stderr)
                self.assertIsNone(archived_path)
                self.assertIsNone(review_path)
                after = {
                    path.relative_to(self.project).as_posix(): path.read_bytes()
                    for path in self.project.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, self._last_generate_guard)
                state = read_json(
                    self.project / ".better-product-graph" / "runs" / run_id / "state.json"
                )
                self.assertEqual(state["current_node"], "prd.generate")

    def test_installed_ready_rejects_wrong_role_artifacts_and_invented_reviewed_evals_before_release(self) -> None:
        completed, run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                forged_reviewed_evals=True,
                expect_success=False,
            )
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertRegex(completed.stderr, "Eval|role|schema|provenance|NOT_RUN")
        state = read_json(
            self.project / ".better-product-graph" / "runs" / run_id / "state.json"
        )
        self.assertNotIn(state["status"], {"RELEASED", "COMPLETED"})
        released_root = self.project / "artifacts" / "prds" / "released"
        self.assertFalse(released_root.exists() and any(released_root.iterdir()))
        self.assertFalse(
            (self.project / ".better-product-graph" / "runs" / run_id / "ready-evidence").exists()
        )
        self.assertFalse(
            any(
                item.get("node_id") == "prd.ready.gate"
                for item in state.get("dispatch_attempts", [])
            )
        )
        receipt_root = (
            self.project / ".better-product-graph" / "runs" / run_id / "receipts"
        )
        self.assertFalse(receipt_root.exists() and any(receipt_root.iterdir()))

    def test_installed_same_host_cannot_self_attest_required_evals_and_release(self) -> None:
        completed, run_id, archived_path, _review_path = (
            self._run_installed_review_finalize_lifecycle(
                self_reviewed_typed_evals=True,
                expect_success=False,
            )
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertRegex(
            completed.stderr,
            "REQUIRED|fulfillment authority|independent|Raw Signal|provenance",
        )
        state = read_json(
            self.project / ".better-product-graph" / "runs" / run_id / "state.json"
        )
        self.assertNotIn(state["status"], {"RELEASED", "COMPLETED"})
        released_root = self.project / "artifacts" / "prds" / "released"
        self.assertFalse(released_root.exists() and any(released_root.iterdir()))
        self.assertFalse(
            (self.project / ".better-product-graph" / "runs" / run_id / "ready-evidence").exists()
        )
        if archived_path is None:
            candidate_root = self.project / "artifacts" / "prds" / "archived"
            self.assertFalse(candidate_root.exists() and any(candidate_root.iterdir()))
            after = {
                path.relative_to(self.project).as_posix(): path.read_bytes()
                for path in self.project.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, self._last_generate_guard)

    def _assert_false_ready_rejected(self, invalid_kind: str, payload: dict) -> None:
        completed, run_id, archived_path, review_path = self._run_installed_review_finalize_lifecycle(
            upstream_payloads={invalid_kind: payload},
            expect_success=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertRegex(
            completed.stderr,
            "Decision|Evidence|authoritative|mechanical|spec_traceability|committed provenance",
        )
        state = read_json(
            self.project / ".better-product-graph" / "runs" / run_id / "state.json"
        )
        self.assertNotIn(state["status"], {"RELEASED", "COMPLETED"})
        self.assertIsNone(archived_path)
        self.assertIsNone(review_path)
        self.assertEqual(state["current_node"], "prd.generate")
        released_root = self.project / "artifacts" / "prds" / "released"
        self.assertFalse(released_root.exists() and any(released_root.iterdir()))
        receipt_root = (
            self.project / ".better-product-graph" / "runs" / run_id / "receipts"
        )
        if receipt_root.exists():
            self.assertFalse(
                any(
                    read_json(path).get("kind") == "mechanical_contracts"
                    for path in receipt_root.glob("*.json")
                )
            )

    def test_installed_false_ready_rejects_unrelated_fail_decision(self) -> None:
        self._assert_false_ready_rejected(
            "decision",
            {
                "schema_version": "product-decision-record.v1",
                "kind": "decision",
                "version": 1,
                "run_id": "run-unrelated-independent-audit",
                "status": "FAIL",
                "authorized": False,
            },
        )

    def test_installed_false_ready_rejects_unrelated_unauthorized_evidence(self) -> None:
        self._assert_false_ready_rejected(
            "evidence",
            {
                "schema_version": "evidence-record.v1",
                "kind": "evidence",
                "version": 1,
                "run_id": "run-unrelated-independent-audit",
                "status": "FAIL",
                "authorized": False,
            },
        )


class ReceiptAndReleaseReauditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        self.controller = StateController(self.project, GRAPH)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _file(self, relative: str, value: dict | str) -> dict:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, dict):
            atomic_write_json(path, value)
        else:
            path.write_text(value, encoding="utf-8")
        return {
            "path": path.relative_to(self.project).as_posix(),
            "hash": sha256_file(path),
            "version": 1,
        }

    def _place_at_ready_gate(
        self,
        run_id: str,
        candidate: dict,
        authorized: list[dict],
        *,
        attempt_id: str,
    ) -> dict:
        self.controller.create_run(run_id, raw_signal="receipt evaluator fixture")
        state = self.controller.load_state(run_id)
        state.update(
            {
                "status": "ACTIVE",
                "current_node": "prd.ready.gate",
                "next_allowed_nodes": ["handoff.prepare"],
                "current_candidate_ref": {
                    **candidate,
                    "artifact_path": str(Path(candidate["path"]).parent),
                    "tree_hash": hash_tree(self.project / Path(candidate["path"]).parent),
                    "version": candidate.get("version", "v0.1"),
                },
            }
        )
        for index, ref in enumerate(authorized):
            state["artifact_refs"][f"receipt-fixture:{index}"] = {
                key: ref[key] for key in ("path", "hash", "version") if key in ref
            }
        atomic_write_json(self.controller._state_path(run_id), state)
        persist_node_dispatch(self.controller, run_id, attempt_id)
        begin_node_call(self.controller, run_id, attempt_id)
        return self.controller.load_state(run_id)

    def test_explicit_fail_audit_subject_cannot_receive_pass_receipt(self) -> None:
        run_id = "run-fail-audit"
        candidate = self._file("candidate/fail-audit-prd.md", "# Candidate\n")
        attempt_id = "attempt-fail-audit"
        failed = self._file(
            "evidence/fail-audit.json",
            {
                "schema_version": "audit-integrity-snapshot.v1",
                "status": "FAIL",
                "run_id": run_id,
                "node_id": "prd.ready.gate",
                "attempt_id": attempt_id,
                "candidate_hash": candidate["hash"],
                "candidate_version": "v0.1",
                "rules_version": READY_RULES_VERSION,
                "event_count": 1,
                "event_head_hash": "sha256:" + "0" * 64,
            },
        )
        state = self._place_at_ready_gate(
            run_id,
            {**candidate, "version": "v0.1"},
            [failed],
            attempt_id=attempt_id,
        )

        with self.assertRaisesRegex(TransitionRejected, "FAIL|PASS|audit"):
            self.controller.issue_controller_receipt(
                run_id,
                "fail-audit",
                "audit_integrity",
                [{"role": "audit_snapshot", **failed}],
                expected_state_version=state["state_version"],
            )

    def test_receipt_issuance_requires_the_matching_current_gate_and_attempt(self) -> None:
        run_id = "run-wrong-receipt-lifecycle"
        state = self.controller.create_run(run_id, raw_signal="wrong lifecycle")
        audit = self._file(
            "evidence/pass-audit.json",
            {
                "status": "PASS",
                "run_id": run_id,
                "candidate_hash": "sha256:" + "a" * 64,
                "candidate_version": "v0.1",
                "rules_version": READY_RULES_VERSION,
            },
        )

        with self.assertRaisesRegex(TransitionRejected, "node|attempt|lifecycle"):
            self.controller.issue_controller_receipt(
                run_id,
                "wrong-lifecycle",
                "audit_integrity",
                [{"role": "audit_snapshot", **audit}],
                expected_state_version=state["state_version"],
            )

    def test_receipt_payload_binds_current_attempt_candidate_and_rules(self) -> None:
        run_id = "run-bound-receipt"
        self.controller.create_run(run_id, raw_signal="bound receipt")
        candidate = self._file("candidate/bound-prd.md", "# Bound Candidate\n")
        attempt_id = "attempt-prd-ready-bound"
        events = verify_event_chain(self.controller._events_path(run_id))
        audit = self._file(
            "evidence/bound-audit.json",
            {
                "schema_version": "audit-integrity-snapshot.v1",
                "status": "PASS",
                "run_id": run_id,
                "node_id": "prd.ready.gate",
                "attempt_id": attempt_id,
                "candidate_hash": candidate["hash"],
                "candidate_version": "v0.1",
                "rules_version": READY_RULES_VERSION,
                "event_count": len(events),
                "event_head_hash": events[-1]["event_hash"],
            },
        )
        state = self.controller.load_state(run_id)
        state.update(
            {
                "current_node": "prd.ready.gate",
                "next_allowed_nodes": ["handoff.prepare"],
                "current_candidate_ref": {
                    **candidate,
                    "artifact_path": "candidate",
                    "tree_hash": hash_tree(self.project / "candidate"),
                    "version": "v0.1",
                },
            }
        )
        state["artifact_refs"]["bound-audit"] = audit
        atomic_write_json(self.controller._state_path(run_id), state)
        persist_node_dispatch(self.controller, run_id, attempt_id)
        begin_node_call(self.controller, run_id, attempt_id)
        state = self.controller.load_state(run_id)

        receipt_ref = self.controller.issue_controller_receipt(
            run_id,
            "bound-audit",
            "audit_integrity",
            [{"role": "audit_snapshot", **audit}],
            expected_state_version=state["state_version"],
        )
        receipt = read_json(self.project / receipt_ref["path"])

        self.assertEqual(receipt.get("node_id"), "prd.ready.gate")
        self.assertEqual(receipt.get("attempt_id"), attempt_id)
        self.assertEqual(receipt.get("candidate_hash"), candidate["hash"])
        self.assertEqual(receipt.get("candidate_version"), "v0.1")
        self.assertEqual(receipt.get("rules_version"), READY_RULES_VERSION)

    def test_explicit_fail_mechanical_subject_cannot_receive_pass_receipt(self) -> None:
        run_id = "run-fail-mechanical"
        candidate = self._file("candidate/prd.md", "# Candidate\n")
        subjects = [{"role": "candidate_document", **candidate}]
        for role in (
            "upstream_decision",
            "upstream_product_plan",
            "upstream_roadmap",
            "upstream_slice",
            "upstream_knowledge",
            "upstream_evidence",
        ):
            subjects.append(
                {
                    "role": role,
                    **self._file(f"evidence/{role}.json", {"status": "PASS"}),
                }
            )
        subjects.append(
            {
                "role": "mechanical_validation",
                **self._file(
                    "evidence/mechanical.json",
                    {
                        "schema_version": "mechanical-validation.v1",
                        "status": "FAIL",
                        "run_id": run_id,
                        "candidate_hash": candidate["hash"],
                    },
                ),
            }
        )
        state = self._place_at_ready_gate(
            run_id,
            {**candidate, "version": "v0.1"},
            subjects,
            attempt_id="attempt-fail-mechanical",
        )

        with self.assertRaisesRegex(TransitionRejected, "FAIL|PASS|mechanical"):
            self.controller.issue_controller_receipt(
                run_id,
                "fail-mechanical",
                "mechanical_contracts",
                subjects,
                expected_state_version=state["state_version"],
            )

    def test_receipts_from_unrelated_signal_ingest_run_cannot_release_candidate(self) -> None:
        assembled = assemble_prd(
            prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        )
        archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={},
            review_companion=finalized_review_companion(assembled),
        )
        candidate = {
            "path": str(archived.path),
            "hash": archived.document_hash,
            "tree_hash": archived.tree_hash,
            "version": archived.version,
        }
        request, archived = materialize_ready_evidence(
            self.project, complete_ready_input(candidate), archived
        )

        unrelated_run = "run-unrelated-ready"
        unrelated_controller = StateController(self.project, GRAPH)
        unrelated_controller.create_run(unrelated_run, raw_signal="unrelated Ready run")
        unrelated_state = unrelated_controller.load_state(unrelated_run)
        source_state = unrelated_controller.load_state(request["run_id"])
        unrelated_state.update(
            {
                "status": "ACTIVE",
                "current_node": "prd.ready.gate",
                "last_completed_node": "review.finalize",
                "next_allowed_nodes": ["handoff.prepare"],
                "current_candidate_ref": source_state["current_candidate_ref"],
                "candidate_version": source_state["candidate_version"],
                "artifact_refs": source_state["artifact_refs"],
            }
        )
        atomic_write_json(unrelated_controller._state_path(unrelated_run), unrelated_state)
        persist_node_dispatch(
            unrelated_controller, unrelated_run, "attempt-unrelated-prd-ready"
        )
        begin_node_call(
            unrelated_controller, unrelated_run, "attempt-unrelated-prd-ready"
        )

        with self.assertRaisesRegex(PRDNotReady, "another Run|registered|receipt"):
            ready_and_release(
                self.project,
                archived,
                request,
                controller=unrelated_controller,
                run_id=unrelated_run,
            )

        released = self.project / "artifacts" / "prds" / "released" / archived.path.name
        self.assertFalse(released.exists())


class ControllerCapabilityReauditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        self.controller = StateController(self.project, GRAPH)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_caller_cannot_submit_a_controller_result_directly(self) -> None:
        run_id = "run-direct-controller-forgery"
        self.controller.create_run(run_id, raw_signal="direct forgery")
        attempt_id = "attempt-direct-controller-forgery"
        persist_node_dispatch(self.controller, run_id, attempt_id)
        begin_node_call(self.controller, run_id, attempt_id)
        forged = {
            "schema_version": "node-result.v1",
            "node_id": "signal.ingest",
            "attempt_id": attempt_id,
            "producer": {"kind": "DETERMINISTIC_PROGRAM", "component": "host-adapter"},
            "mechanical_output": {"status": "COMPLETED", "forged": True},
            "artifact_refs": [],
        }

        with self.assertRaisesRegex(TransitionRejected, "Controller-only|HOST_AGENT|mechanical"):
            self.controller.submit_result(run_id, forged)


if __name__ == "__main__":
    unittest.main()
