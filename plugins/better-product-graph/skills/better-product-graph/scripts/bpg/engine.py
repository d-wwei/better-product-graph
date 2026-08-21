"""Thin Codex Host orchestration over deterministic Core mechanics."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .bugs import BugContractError, persist_bug_packet
from .connectors import LocalHandoffConnector, NullConnector
from .git_preflight import GitPreflight, preflight_project
from .intents import HostIntent, parse_host_entry
from .resume import inspect_resume
from .signals import record_signal_occurrence
from .state_controller import StateController, TransitionRejected
from .storage import assert_managed_path, atomic_write_json, read_json, sha256_file, verify_event_chain


HELP = {
    "status": "HELP",
    "entry": "$better-product-graph",
    "commands": [
        "new",
        "capture",
        "inbox",
        "status",
        "resume",
        "pause",
        "handoff",
        "connectors",
        "audit",
        "interview skip|resume",
        "help",
    ],
}


class HostEngine:
    def __init__(self, project_root: Path, controller: StateController):
        self.project_root = project_root.resolve()
        self.controller = controller

    @staticmethod
    def _stable_id(prefix: str, value: str) -> str:
        digest = hashlib.sha256(value.encode()).hexdigest()[:12]
        return f"{prefix}-{digest}"

    def _capture(self, parsed: HostIntent) -> dict[str, Any]:
        recorded = record_signal_occurrence(
            self.project_root,
            parsed.argument,
            source={"kind": "MANUAL", "entry": parsed.raw_entry},
        )
        signal_id = recorded["signal_id"]
        path = self.project_root / ".better-product-graph" / "inbox" / f"{signal_id}.json"
        if not path.exists():
            atomic_write_json(
                path,
                {
                    "schema_version": "signal-inbox-link.v1",
                    "signal_id": signal_id,
                    "signal_ref": recorded["signal_ref"],
                    "activation": "INBOX_ONLY",
                },
            )
        return {
            "status": "CAPTURED",
            "signal_id": signal_id,
            "occurrence_id": recorded["occurrence"]["occurrence_id"],
            "path": str(path),
        }

    def _activate(self, parsed: HostIntent) -> dict[str, Any]:
        recorded = record_signal_occurrence(
            self.project_root,
            parsed.argument,
            source={"kind": "MANUAL", "entry": parsed.raw_entry},
        )
        run_id = self._stable_id("run", recorded["occurrence"]["occurrence_id"])
        state_path = self.controller._state_path(run_id)
        if state_path.exists():
            return {
                "status": "EXISTING",
                "run_id": run_id,
                "state": read_json(state_path),
                "source_signal_id": recorded["signal_id"],
                "occurrence_id": recorded["occurrence"]["occurrence_id"],
            }
        state = self.controller.create_run(
            run_id,
            raw_signal=parsed.argument,
            source_signal_ref=recorded["signal_ref"],
            source_signal_id=recorded["signal_id"],
            source_occurrence_id=recorded["occurrence"]["occurrence_id"],
        )
        if parsed.interaction_policy == "NO_PM_INTERVIEW":
            state = self.controller.set_interview_policy(
                run_id, "skip", expected_state_version=state["state_version"]
            )
        return {
            "status": "ACTIVATED",
            "run_id": run_id,
            "state": state,
            "source_signal_id": recorded["signal_id"],
            "occurrence_id": recorded["occurrence"]["occurrence_id"],
        }

    def _prepare_handoff(self, run_id: str) -> dict[str, Any]:
        state = self.controller.load_state(run_id)
        handoff_ref = state.get("handoff_ref")
        if (
            state.get("status") == "COMPLETED"
            and state.get("current_node") == "handoff.dispatch"
            and isinstance(handoff_ref, dict)
            and handoff_ref.get("delivery_kind") == "BUG"
        ):
            packet_ref = {
                key: handoff_ref[key]
                for key in ("role", "path", "hash", "version")
            }
            return {
                "status": "COMPLETED",
                "delivery_kind": "BUG",
                "delivery_status": "WRITTEN_LOCAL",
                "sent_remote": False,
                "run_id": run_id,
                "bug_packet_ref": packet_ref,
                "bug_human_ref": state["bug_human_ref"],
                "handoff_ref": handoff_ref,
                "state": state,
            }
        if (
            state.get("status") == "ACTIVE"
            and state.get("current_node") == "handoff.prepare"
            and state.get("last_completed_node") == "bug.baseline.check"
        ):
            result_refs = [
                ref
                for ref in state.get("artifact_refs", {}).values()
                if isinstance(ref, dict)
                and ref.get("role") == "node_result"
                and ref.get("node_id") == "bug.baseline.check"
                and ref.get("attempt_id") in state.get("consumed_attempts", [])
            ]
            if len(result_refs) != 1:
                return {
                    "status": "NOT_READY",
                    "run_id": run_id,
                    "reason": "EXACT_BUG_BASELINE_RESULT_REQUIRED",
                }
            result_ref = result_refs[0]
            try:
                self.controller._validate_single_artifact_ref(result_ref)
                result = read_json(self.project_root / result_ref["path"])
                bug_id = f"bug-{run_id.removeprefix('run-')}"
                packet = persist_bug_packet(self.project_root, bug_id, result)
                completed = self.controller.complete_bug_handoff(
                    run_id,
                    bug_id,
                    packet["packet_ref"],
                    packet["human_ref"],
                    expected_state_version=state["state_version"],
                )
            except (BugContractError, KeyError, OSError, ValueError) as error:
                raise TransitionRejected(
                    f"Bug Handoff packet could not be prepared: {error}"
                ) from error
            return {
                "status": "COMPLETED",
                "delivery_kind": "BUG",
                "delivery_status": "WRITTEN_LOCAL",
                "sent_remote": False,
                "run_id": run_id,
                "bug_packet_ref": packet["packet_ref"],
                "bug_human_ref": packet["human_ref"],
                "handoff_ref": completed["handoff_ref"],
                "state": completed,
            }
        release_ref = state.get("release_ref")
        if state.get("status") != "RELEASED" or not isinstance(release_ref, dict):
            return {"status": "NOT_READY", "run_id": run_id, "reason": "EXACT_RELEASED_READY_REQUIRED"}
        try:
            ready_path = self.project_root / release_ref["path"]
            ready = read_json(ready_path)
        except Exception:
            return {"status": "NOT_READY", "run_id": run_id, "reason": "READY_ASSERTION_MISSING"}
        from .storage import sha256_file
        from .documents import hash_tree

        if (
            not ready_path.is_file()
            or ready_path.is_symlink()
            or sha256_file(ready_path) != release_ref.get("hash")
            or ready.get("status") != "READY"
            or ready.get("candidate_hash") != release_ref.get("candidate_hash")
        ):
            return {"status": "NOT_READY", "run_id": run_id, "reason": "READY_ASSERTION_MISMATCH"}
        try:
            artifact_path = (self.project_root / release_ref["artifact_path"]).resolve()
            artifact_path.relative_to(
                self.project_root / "artifacts" / "prds" / "released"
            )
            documents = list(artifact_path.glob("*.md"))
            companions = list(artifact_path.glob("*.review.json"))
        except (KeyError, ValueError):
            artifact_path = self.project_root
            documents = []
            companions = []
        if (
            not artifact_path.is_dir()
            or artifact_path.is_symlink()
            or hash_tree(artifact_path) != release_ref.get("candidate_tree_hash")
            or len(documents) != 1
            or documents[0].is_symlink()
            or sha256_file(documents[0]) != release_ref.get("candidate_hash")
            or len(companions) != 1
            or companions[0].is_symlink()
            or sha256_file(companions[0]) != release_ref.get("review_companion_hash")
        ):
            return {
                "status": "NOT_READY",
                "run_id": run_id,
                "reason": "RELEASED_ARTIFACT_MISMATCH",
            }
        connector = LocalHandoffConnector(self.project_root)
        packet_id = f"handoff-{run_id}"
        receipt = connector.dispatch(
            {
                "id": packet_id,
                "run_id": run_id,
                "state_version": state["state_version"],
                "status": state["status"],
                "current_node": state["current_node"],
                "release_ref": release_ref,
                "remote_delivery": "NOT_CONFIGURED",
            }
        )
        completed = self.controller.complete_local_handoff(
            run_id,
            receipt["receipt"],
            expected_state_version=state["state_version"],
        )
        return {
            "status": "COMPLETED",
            "delivery_status": receipt["status"],
            "sent_remote": False,
            "run_id": run_id,
            "release_ref": release_ref,
            "handoff_ref": completed["handoff_ref"],
            "state": completed,
        }

    @staticmethod
    def _preflight_payload(preflight: GitPreflight) -> dict[str, Any]:
        return {
            "status": preflight.status,
            "project_root": str(preflight.project_root),
            "repository_root": str(preflight.repository_root) if preflight.repository_root else None,
            "initialized": preflight.initialized,
            "reason": preflight.reason,
        }

    def handle(self, entry: str) -> dict[str, Any]:
        parsed = parse_host_entry(entry)
        if parsed.activation == "REJECT_INTERNAL_BYPASS":
            return {"status": "REJECTED", "reason": "INTERNAL_BYPASS_FORBIDDEN"}
        if parsed.activation == "GUIDED_HELP" or parsed.core_intent == "host.help":
            return dict(HELP)
        if parsed.run_id:
            try:
                self.controller.authoritative_read_barrier(parsed.run_id)
            except TransitionRejected as error:
                return {
                    "status": "BLOCKED_STALE",
                    "run_id": parsed.run_id,
                    "blockers": [str(error)],
                }
        preflight = preflight_project(self.project_root) if parsed.write_allowed else None

        def finish(payload: dict[str, Any]) -> dict[str, Any]:
            if preflight is not None:
                payload = {**payload, "git_preflight": self._preflight_payload(preflight)}
            return payload

        if preflight is not None and preflight.status != "READY":
            return finish({"status": "PREFLIGHT_FAILED", "reason": preflight.reason})

        if parsed.core_intent == "signal.submit":
            return finish(self._capture(parsed))
        if parsed.core_intent == "signal.activate":
            return finish(self._activate(parsed))
        if parsed.core_intent == "signal.inbox.list":
            root = self.project_root / ".better-product-graph" / "inbox"
            return {
                "status": "OK",
                "items": [str(path) for path in sorted(root.glob("*.json"))] if root.exists() else [],
            }
        if parsed.core_intent == "run.status":
            return {"status": "OK", "state": self.controller.load_state(parsed.run_id or "")}
        if parsed.core_intent == "run.pause":
            state = self.controller.load_state(parsed.run_id or "")
            return finish({
                "status": "PAUSED",
                "state": self.controller.set_run_activity(
                    parsed.run_id or "", "pause", expected_state_version=state["state_version"]
                ),
            })
        if parsed.core_intent == "run.resume":
            if parsed.trigger_file is not None:
                trigger_path = assert_managed_path(
                    self.project_root,
                    self.project_root / parsed.trigger_file,
                )
                if not trigger_path.is_file() or trigger_path.is_symlink():
                    raise TransitionRejected("WAIT trigger file is missing or unsafe")
                command = read_json(trigger_path)
                state = self.controller.consume_wait_trigger(
                    parsed.run_id or "",
                    command,
                    command_ref={
                        "path": trigger_path.relative_to(self.project_root).as_posix(),
                        "hash": sha256_file(trigger_path),
                        "version": 1,
                    },
                )
                return finish({"status": "TRIGGER_CONSUMED", "state": state})
            inspection = inspect_resume(self.controller, parsed.run_id or "")
            if inspection.status != "READY_TO_RESUME":
                return finish({"status": inspection.status, "blockers": inspection.blockers})
            state = self.controller.load_state(parsed.run_id or "")
            if parsed.interaction_policy == "NO_PM_INTERVIEW" and state["interaction_policy"] != "NO_PM_INTERVIEW":
                state = self.controller.set_interview_policy(
                    parsed.run_id or "", "skip", expected_state_version=state["state_version"]
                )
            return finish({
                "status": "RESUMED",
                "state": self.controller.set_run_activity(
                    parsed.run_id or "", "resume", expected_state_version=state["state_version"]
                ),
            })
        if parsed.core_intent == "handoff.prepare":
            return finish(self._prepare_handoff(parsed.run_id or ""))
        if parsed.core_intent == "connector.status":
            return {
                "status": "OK",
                "connectors": [
                    LocalHandoffConnector(self.project_root).status(),
                    NullConnector("feishu").status(),
                    NullConnector("kmg").status(),
                    NullConnector("dev-test").status(),
                ],
            }
        if parsed.core_intent == "audit.view":
            events = verify_event_chain(self.controller._events_path(parsed.run_id or ""))
            return {"status": "OK", "events": events}
        if parsed.core_intent == "interaction.policy.set":
            state = self.controller.load_state(parsed.run_id or "")
            updated = self.controller.set_interview_policy(
                parsed.run_id or "",
                parsed.action or "",
                expected_state_version=state["state_version"],
            )
            return finish({"status": "UPDATED", "state": updated})
        return dict(HELP)
