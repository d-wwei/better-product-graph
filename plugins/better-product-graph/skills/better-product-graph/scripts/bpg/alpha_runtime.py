"""Thin BPG 2.0 Iteration-One controller.

The Host Agent owns every product-semantic judgment. This module only binds one
exact Run, immutable Candidates, independent Reviews, explicit authority,
idempotent state transitions, the single Ready contract, and Local Handoff.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .alpha_html import render_self_contained_prd_html
from .locking import exclusive_file_lock
from .storage import (
    assert_managed_path,
    atomic_write_bytes,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
)


class AlphaContractError(RuntimeError):
    """An operation would violate the BPG 2.0 Alpha deterministic boundary."""


class AlphaStateConflict(AlphaContractError):
    """The caller attempted to mutate a stale state version."""


RUNTIME = "BPG_2_0_ALPHA"
RUN_ID = re.compile(r"^bpg2-run-[A-Za-z0-9._-]+$")
DECISION_OUTCOMES = frozenset(
    {"STOP", "WAIT", "RESEARCH", "EXPERIMENT", "COMMIT_NOW", "FUTURE_ROADMAP"}
)
POSITIONS = frozenset(
    {
        "UNDERSTAND",
        "DIAGNOSE_VALUE",
        "PROBLEM_REVIEW",
        "DISCOVER_SOLUTIONS_DECIDE",
        "DECISION_REVIEW",
        "DECISION_ROUTE",
        "PLAN_PRODUCT_SYSTEM",
        "PRD_AUTHORING",
        "PRD_REVIEW",
        "READY",
        "RESEARCH",
        "OWNER",
    }
)
REVIEW_TARGETS = frozenset(
    {
        "UNDERSTAND",
        "DIAGNOSE_VALUE",
        "DISCOVER_SOLUTIONS_DECIDE",
        "PLAN_PRODUCT_SYSTEM",
        "PRD_AUTHORING",
        "RESEARCH",
        "WAIT",
        "OWNER",
    }
)
CANDIDATE_POSITION = {
    "PROBLEM": ("DIAGNOSE_VALUE", "PROBLEM_REVIEW"),
    "DECISION": ("DISCOVER_SOLUTIONS_DECIDE", "DECISION_REVIEW"),
    "PRD": ("PRD_AUTHORING", "PRD_REVIEW"),
}
PASS_POSITION = {
    "PROBLEM": "DISCOVER_SOLUTIONS_DECIDE",
    "DECISION": "DECISION_ROUTE",
}
LOCAL_REVISION_TARGET = {
    "PROBLEM": "DIAGNOSE_VALUE",
    "DECISION": "DISCOVER_SOLUTIONS_DECIDE",
    "PRD": "PRD_AUTHORING",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AlphaContractError(f"{label} must be a non-empty string")
    return value.strip()


def _payload_hash(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _same_ref(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    keys = {"candidate_id", "kind", "path", "hash", "version"}
    return all(left.get(key) == right.get(key) for key in keys)


class BPG2AlphaController:
    """Minimal single-PRD Controller; no product meaning is inferred here."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        if self.project_root == Path("/") or self.project_root == Path.home().resolve():
            raise AlphaContractError("project root must be a specific workspace")
        self.root = self.project_root / ".better-product-graph" / "v2"

    def _validate_run_id(self, run_id: str) -> str:
        if RUN_ID.fullmatch(run_id) is None:
            raise AlphaContractError("BPG 2.0 Run id is invalid")
        return run_id

    @staticmethod
    def _template_source() -> Path:
        module = Path(__file__).resolve()
        candidates = (
            module.parents[1] / "core" / "templates" / "general" / "PRD_TEMPLATE_v2.0-alpha.md",
            module.parents[2] / "references" / "templates" / "general" / "PRD_TEMPLATE_v2.0-alpha.md",
        )
        template = next((path for path in candidates if path.is_file() and not path.is_symlink()), None)
        if template is None:
            raise AlphaContractError("BPG 2.0 Alpha general PRD template is unavailable")
        return template

    def run_path(self, run_id: str) -> Path:
        return self.root / "runs" / self._validate_run_id(run_id)

    def prd_draft_path(self, run_id: str) -> Path:
        return self.run_path(run_id) / "work" / "prd"

    def _state_path(self, run_id: str) -> Path:
        return self.run_path(run_id) / "run.json"

    def _lock_path(self, run_id: str) -> Path:
        return self.run_path(run_id) / ".run.lock"

    def load_run(self, run_id: str) -> dict[str, Any]:
        path = self._state_path(run_id)
        if not path.is_file():
            raise AlphaContractError(
                "BPG 2.0 Run does not exist; old BPG Runs are never imported, migrated, or resumed"
            )
        state = read_json(path)
        if state.get("runtime") != RUNTIME or state.get("run_id") != run_id:
            raise AlphaContractError("BPG 2.0 Run identity is invalid")
        return state

    def file_ref(self, path: Path) -> dict[str, Any]:
        managed = assert_managed_path(self.project_root, path.resolve(strict=False))
        if not managed.is_file() or managed.is_symlink():
            raise AlphaContractError("file reference must bind one regular project file")
        return {
            "path": managed.relative_to(self.project_root).as_posix(),
            "hash": sha256_file(managed),
        }

    def _verify_file_ref(self, ref: Any) -> Path:
        if not isinstance(ref, dict):
            raise AlphaContractError("exact file reference is required")
        relative = _nonempty(ref.get("path"), "file ref path")
        path = assert_managed_path(self.project_root, Path(relative))
        if not path.is_file() or path.is_symlink() or sha256_file(path) != ref.get("hash"):
            raise AlphaContractError("exact file reference is missing or changed")
        return path

    @staticmethod
    def _operation_payload(action: str, **values: Any) -> dict[str, Any]:
        return {"action": action, **values}

    def _mutate(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        payload: dict[str, Any],
        mutate: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        _nonempty(operation_id, "operation_id")
        fingerprint = _payload_hash(payload)
        with exclusive_file_lock(self._lock_path(run_id)):
            state = self.load_run(run_id)
            existing = state.get("operations", {}).get(operation_id)
            if existing is not None:
                if existing.get("payload_hash") != fingerprint:
                    raise AlphaContractError("operation identity conflict")
                return state
            if state.get("state_version") != expected_state_version:
                raise AlphaStateConflict(
                    f"expected state version {expected_state_version}, current is {state.get('state_version')}"
                )
            updated = deepcopy(state)
            mutate(updated)
            updated["state_version"] = expected_state_version + 1
            updated["updated_at"] = _now()
            updated.setdefault("operations", {})[operation_id] = {
                "payload_hash": fingerprint,
                "committed_state_version": updated["state_version"],
            }
            atomic_write_json(self._state_path(run_id), updated)
            return updated

    def start_run(
        self,
        *,
        signal: str,
        route: dict[str, Any],
        operation_id: str,
        run_id: str | None = None,
        preauthorization: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        signal = _nonempty(signal, "signal")
        if not isinstance(route, dict) or route.get("destination") != "PRODUCT_PLANNING":
            raise AlphaContractError("Signal & Route requires an Agent-selected PRODUCT_PLANNING route")
        _nonempty(route.get("attempt_id"), "route attempt_id")
        if preauthorization is not None:
            if (
                not isinstance(preauthorization, dict)
                or not preauthorization.get("authorization_id")
                or preauthorization.get("allowed_outcome") != "COMMIT_NOW"
                or preauthorization.get("scope") != "LOCAL_PLANNING_ONLY"
            ):
                raise AlphaContractError("preauthorization must be exact and local-planning-only")
        resolved_run_id = self._validate_run_id(run_id or f"bpg2-run-{uuid4().hex[:12]}")
        payload = self._operation_payload(
            "start_run",
            signal=signal,
            route=route,
            preauthorization=preauthorization,
            run_id=resolved_run_id,
        )
        fingerprint = _payload_hash(payload)
        run_path = self.run_path(resolved_run_id)
        with exclusive_file_lock(self.root / ".create.lock"):
            if self._state_path(resolved_run_id).exists():
                state = self.load_run(resolved_run_id)
                existing = state.get("operations", {}).get(operation_id)
                if existing and existing.get("payload_hash") == fingerprint:
                    return state
                raise AlphaContractError("operation identity conflict")
            run_path.mkdir(parents=True, exist_ok=False)
            planning_record = (
                "# 产品规划主记录\n\n"
                "## Signal 与当前边界\n\n"
                f"原始 Signal：{signal}\n\n"
                "当前阶段：UNDERSTAND\n\n"
                "本记录是当前 Run 的产品事实与分析真源；正式 Review 只读取冻结 Candidate。\n"
            )
            record_path = run_path / "planning-record.md"
            atomic_write_bytes(record_path, planning_record.encode("utf-8"))
            created = _now()
            state: dict[str, Any] = {
                "runtime": RUNTIME,
                "schema_version": "bpg2-alpha-run.v1",
                "run_id": resolved_run_id,
                "status": "ACTIVE",
                "position": "UNDERSTAND",
                "state_version": 1,
                "created_at": created,
                "updated_at": created,
                "signal": signal,
                "route": deepcopy(route),
                "planning_record_ref": self.file_ref(record_path),
                "preauthorization": deepcopy(preauthorization),
                "current_candidate": None,
                "candidate_history": [],
                "reviews": [],
                "decision": None,
                "decision_candidate_ref": None,
                "delivery_intent": None,
                "product_evals": None,
                "ready": {"status": "NOT_EVALUATED", "unmet": []},
                "handoff": None,
                "external_delivery": "NOT_RUN",
                "retrospective_status": "NOT_RUN",
                "candidate_required": False,
                "automatic_revision_exhausted": False,
                "used_trigger_ids": [],
                "operations": {
                    operation_id: {"payload_hash": fingerprint, "committed_state_version": 1}
                },
            }
            atomic_write_json(self._state_path(resolved_run_id), state)
            return state

    def update_planning_record(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        author_attempt_id: str,
        position: str,
        markdown: str,
        next_position: str | None = None,
    ) -> dict[str, Any]:
        author_attempt_id = _nonempty(author_attempt_id, "author_attempt_id")
        markdown = _nonempty(markdown, "planning record")
        legal_next = {
            "UNDERSTAND": {None, "DIAGNOSE_VALUE"},
            "DIAGNOSE_VALUE": {None},
            "DISCOVER_SOLUTIONS_DECIDE": {None},
            "PLAN_PRODUCT_SYSTEM": {None, "PRD_AUTHORING"},
            "PRD_AUTHORING": {None},
            "RESEARCH": {None, "UNDERSTAND", "DIAGNOSE_VALUE", "DISCOVER_SOLUTIONS_DECIDE"},
        }
        if position not in legal_next or next_position not in legal_next[position]:
            raise AlphaContractError("planning record transition is not legal")
        payload = self._operation_payload(
            "update_planning_record",
            author_attempt_id=author_attempt_id,
            position=position,
            markdown=markdown,
            next_position=next_position,
        )

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") != "ACTIVE" or state.get("position") != position:
                raise AlphaContractError("planning record update does not match the current position")
            path = self.run_path(run_id) / "planning-record.md"
            atomic_write_bytes(path, markdown.encode("utf-8"))
            state["planning_record_ref"] = self.file_ref(path)
            state["last_author_attempt_id"] = author_attempt_id
            if next_position is not None:
                state["position"] = next_position

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )

    def _candidate_ref(self, candidate: dict[str, Any]) -> dict[str, Any]:
        return {
            key: deepcopy(candidate[key])
            for key in (
                "candidate_id",
                "kind",
                "path",
                "hash",
                "version",
                "author_attempt_id",
                "revision_round",
                "artifact_path",
                "supersedes",
                "status",
            )
            if key in candidate
        }

    def _write_record_candidate(
        self,
        run_id: str,
        kind: str,
        version: int,
    ) -> tuple[Path, dict[str, Any]]:
        source = self.run_path(run_id) / "planning-record.md"
        target = self.run_path(run_id) / "candidates" / f"{kind.lower()}-candidate-v{version}.md"
        if target.exists():
            raise AlphaContractError("immutable Candidate path already exists")
        atomic_write_bytes(target, source.read_bytes())
        return target, self.file_ref(source)

    def _validate_evals(self, evals: Any, source_dir: Path) -> dict[str, Any]:
        if not isinstance(evals, dict):
            raise AlphaContractError("Agent Product Evals applicability assessment is required")
        applicability = evals.get("applicability")
        if applicability not in {"NOT_NEEDED", "RECOMMENDED", "REQUIRED"}:
            raise AlphaContractError("Product Evals applicability is invalid")
        _nonempty(evals.get("reason"), "Product Evals reason")
        if evals.get("execution_status") not in {"NOT_RUN", "NOT_AVAILABLE"}:
            raise AlphaContractError("Product Evals execution must preserve a true non-executed status")
        attachments = evals.get("attachment_paths")
        if not isinstance(attachments, list) or not all(isinstance(item, str) for item in attachments):
            raise AlphaContractError("Product Evals attachment_paths must be a list")
        for relative in attachments:
            path = assert_managed_path(source_dir, Path(relative))
            if not path.is_file() or path.is_symlink():
                raise AlphaContractError("Product Evals attachment is missing")
        if evals.get("generation_status") == "GENERATED":
            if not attachments or evals.get("spec_review_status") != "PASS":
                raise AlphaContractError("generated Product Evals require attachments and independent spec Review")
            review_paths = [item for item in attachments if item.endswith("review.json")]
            if not review_paths:
                raise AlphaContractError("generated Product Evals require a spec Review artifact")
            review = json.loads((source_dir / review_paths[0]).read_text(encoding="utf-8"))
            if review.get("author_attempt_id") == review.get("reviewer_attempt_id"):
                raise AlphaContractError("Product Evals spec Reviewer must be independent")
            if review.get("execution_status") != "NOT_RUN":
                raise AlphaContractError("Product Evals spec Review cannot claim execution")
        return deepcopy(evals)

    def _write_prd_candidate(
        self,
        run_id: str,
        version: int,
        source_dir: Path,
        evals: dict[str, Any],
        planning_record_ref: dict[str, Any],
        decision_candidate_ref: dict[str, Any],
        accepted_decision: dict[str, Any],
        decision_review_ref: dict[str, Any],
        delivery_intent: str,
    ) -> tuple[Path, dict[str, Any]]:
        decision_candidate_ref = self._candidate_ref(decision_candidate_ref)
        expected_source = self.prd_draft_path(run_id).resolve()
        if source_dir.resolve() != expected_source or source_dir.is_symlink():
            raise AlphaContractError("PRD draft must use the current Run work directory")
        markdown_path = source_dir / "PRD.md"
        if not markdown_path.is_file() or markdown_path.is_symlink():
            raise AlphaContractError("PRD draft requires PRD.md as the editing truth source")
        candidate_dir = self.run_path(run_id) / "candidates" / f"prd-release-set-v{version}"
        if candidate_dir.exists():
            raise AlphaContractError("immutable Candidate path already exists")
        candidate_dir.mkdir(parents=True)
        source_files: list[Path] = []
        for path in sorted(source_dir.rglob("*")):
            if path.is_symlink():
                raise AlphaContractError("PRD Release Set cannot contain symlinks")
            if path.is_file():
                source_files.append(path)
                relative = path.relative_to(source_dir)
                target = candidate_dir / relative
                atomic_write_bytes(target, path.read_bytes())
        assets = {
            path.relative_to(source_dir).as_posix(): path.read_bytes()
            for path in source_files
            if path.relative_to(source_dir).as_posix().startswith("assets/")
        }
        html_bytes = render_self_contained_prd_html(
            markdown_path.read_text(encoding="utf-8"), assets
        ).encode("utf-8")
        atomic_write_bytes(candidate_dir / "PRD.html", html_bytes)
        machine_dir = candidate_dir / ".machine"
        planning_snapshot = machine_dir / "planning-record-snapshot.md"
        template_snapshot = machine_dir / "PRD_TEMPLATE_v2.0-alpha.md"
        atomic_write_bytes(
            planning_snapshot,
            (self.run_path(run_id) / "planning-record.md").read_bytes(),
        )
        atomic_write_bytes(template_snapshot, self._template_source().read_bytes())
        files = []
        for path in sorted(candidate_dir.rglob("*")):
            if path.is_file():
                files.append(
                    {
                        "path": path.relative_to(candidate_dir).as_posix(),
                        "hash": sha256_file(path),
                        "size": path.stat().st_size,
                    }
                )
        assessment = deepcopy(accepted_decision.get("agent_assessment"))
        if isinstance(assessment, dict):
            assessment.pop("planning_record_ref", None)
            assessment["decision_basis_ref"] = deepcopy(decision_candidate_ref)
        manifest_decision = {
            "outcome": accepted_decision.get("outcome"),
            "source": accepted_decision.get("source"),
            "actor": deepcopy(accepted_decision.get("actor")),
            "authorization_id": accepted_decision.get("authorization_id"),
            "candidate_ref": deepcopy(decision_candidate_ref),
            "agent_assessment": assessment,
        }
        manifest = {
            "schema_version": "bpg2-alpha-release-set.v1",
            "prd_type": "FORMAL_PRD" if delivery_intent == "COMMIT_NOW" else "EXPERIMENT_PRD",
            "template_ref": {
                "path": template_snapshot.relative_to(candidate_dir).as_posix(),
                "hash": sha256_file(template_snapshot),
                "version": "2.0-alpha.1",
            },
            "planning_record_snapshot_ref": {
                "path": planning_snapshot.relative_to(candidate_dir).as_posix(),
                "hash": sha256_file(planning_snapshot),
            },
            "planning_record_source_ref": planning_record_ref,
            "decision_candidate_ref": decision_candidate_ref,
            "accepted_decision": manifest_decision,
            "decision_review_ref": deepcopy(decision_review_ref),
            "product_evals": evals,
            "editing_truth": "PRD.md + assets",
            "default_reading_view": "PRD.html",
            "files": files,
        }
        manifest_path = candidate_dir / "machine-manifest.json"
        atomic_write_json(manifest_path, manifest)
        return manifest_path, planning_record_ref

    def freeze_candidate(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        kind: str,
        author_attempt_id: str,
        source_dir: Path | None = None,
        evals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        kind = _nonempty(kind, "Candidate kind").upper()
        if kind not in CANDIDATE_POSITION:
            raise AlphaContractError("Candidate kind is not supported in the single-PRD Alpha")
        author_attempt_id = _nonempty(author_attempt_id, "author_attempt_id")
        payload = self._operation_payload(
            "freeze_candidate",
            kind=kind,
            author_attempt_id=author_attempt_id,
            source_dir=str(source_dir.resolve()) if source_dir is not None else None,
            evals=evals,
        )

        def apply(state: dict[str, Any]) -> None:
            previous = state.get("current_candidate")
            if isinstance(previous, dict) and previous.get("kind") == kind:
                revision_round = int(previous.get("revision_round", 0)) + 1
                version = int(previous["version"]) + 1
                if revision_round > 2:
                    raise AlphaContractError("two automatic revision rounds are the maximum")
                supersedes = {
                    key: previous[key]
                    for key in ("candidate_id", "kind", "path", "hash", "version")
                }
            else:
                revision_round = 0
                version = 1
                supersedes = None
            if revision_round > 2:
                raise AlphaContractError("two automatic revision rounds are the maximum")
            expected_position, review_position = CANDIDATE_POSITION[kind]
            if state.get("status") != "ACTIVE" or state.get("position") != expected_position:
                if isinstance(previous, dict) and previous.get("revision_round", 0) >= 2:
                    raise AlphaContractError("two automatic revision rounds are the maximum")
                raise AlphaContractError("Candidate freeze does not match the current position")
            planning_ref = self.file_ref(self.run_path(run_id) / "planning-record.md")
            normalized_evals = None
            if kind == "PRD":
                if source_dir is None:
                    raise AlphaContractError("PRD Candidate requires a source directory")
                normalized_evals = self._validate_evals(evals, source_dir)
                decision_ref = state.get("decision_candidate_ref")
                accepted_decision = state.get("decision")
                decision_review_ref = state.get("decision_review_ref")
                if not isinstance(decision_review_ref, dict) and isinstance(
                    decision_ref, dict
                ):
                    persisted = next(
                        (
                            review
                            for review in reversed(state.get("reviews", []))
                            if isinstance(review, dict)
                            and review.get("verdict") == "PASS"
                            and _same_ref(review.get("candidate_ref"), decision_ref)
                        ),
                        None,
                    )
                    if isinstance(persisted, dict):
                        decision_review_ref = {
                            "verdict": "PASS",
                            "candidate_ref": self._candidate_ref(decision_ref),
                            "reviewer_attempt_id": persisted.get("reviewer_attempt_id"),
                            "review_ref": deepcopy(persisted.get("review_ref")),
                        }
                if (
                    not isinstance(decision_ref, dict)
                    or not isinstance(accepted_decision, dict)
                    or not isinstance(decision_review_ref, dict)
                ):
                    raise AlphaContractError("PRD Candidate requires the accepted Decision Candidate")
                target, planning_ref = self._write_prd_candidate(
                    run_id,
                    version,
                    source_dir,
                    normalized_evals,
                    planning_ref,
                    decision_ref,
                    accepted_decision,
                    decision_review_ref,
                    state.get("delivery_intent"),
                )
                artifact_path = target.parent.relative_to(self.project_root).as_posix()
            else:
                target, planning_ref = self._write_record_candidate(run_id, kind, version)
                artifact_path = target.relative_to(self.project_root).as_posix()
            candidate = {
                "candidate_id": f"{kind.lower()}-candidate-v{version}",
                "kind": kind,
                "path": target.relative_to(self.project_root).as_posix(),
                "hash": sha256_file(target),
                "version": version,
                "author_attempt_id": author_attempt_id,
                "revision_round": revision_round,
                "artifact_path": artifact_path,
                "planning_record_ref": planning_ref,
                "supersedes": supersedes,
                "status": "FROZEN",
            }
            state["current_candidate"] = candidate
            state.setdefault("candidate_history", []).append(deepcopy(candidate))
            state["position"] = review_position
            state["candidate_required"] = False
            state["automatic_revision_exhausted"] = False
            if normalized_evals is not None:
                state["product_evals"] = normalized_evals
                state["ready"] = {"status": "NOT_EVALUATED", "unmet": []}

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )

    def _verify_candidate(self, candidate: dict[str, Any]) -> None:
        try:
            path = self._verify_file_ref(
                {"path": candidate.get("path"), "hash": candidate.get("hash")}
            )
        except AlphaContractError as error:
            raise AlphaContractError("Candidate has changed since it was frozen") from error
        if candidate.get("kind") == "PRD":
            manifest = read_json(path)
            candidate_dir = path.parent
            files = manifest.get("files")
            if not isinstance(files, list):
                raise AlphaContractError("PRD Release Set file inventory is missing")
            inventory_paths = {
                ref.get("path") for ref in files if isinstance(ref, dict)
            }
            if not {"PRD.md", "PRD.html"}.issubset(inventory_paths):
                raise AlphaContractError("PRD Release Set is incomplete")
            for ref in files:
                relative = ref.get("path") if isinstance(ref, dict) else None
                file_path = assert_managed_path(candidate_dir, Path(relative or ""))
                if (
                    not file_path.is_file()
                    or file_path.is_symlink()
                    or sha256_file(file_path) != ref.get("hash")
                ):
                    raise AlphaContractError("PRD Release Set Candidate file changed")
            for name in ("template_ref", "planning_record_snapshot_ref"):
                ref = manifest.get(name)
                if not isinstance(ref, dict):
                    raise AlphaContractError(f"PRD Release Set {name} is missing")
                local_path = assert_managed_path(candidate_dir, Path(ref.get("path", "")))
                if (
                    not local_path.is_file()
                    or local_path.is_symlink()
                    or sha256_file(local_path) != ref.get("hash")
                ):
                    raise AlphaContractError(f"PRD Release Set {name} changed")
            source_ref = manifest.get("planning_record_source_ref")
            snapshot_ref = manifest.get("planning_record_snapshot_ref")
            if (
                not isinstance(source_ref, dict)
                or source_ref.get("hash") != snapshot_ref.get("hash")
            ):
                raise AlphaContractError("PRD Release Set planning snapshot binding is invalid")
            decision_ref = manifest.get("decision_candidate_ref")
            accepted = manifest.get("accepted_decision")
            review_binding = manifest.get("decision_review_ref")
            if (
                not isinstance(decision_ref, dict)
                or not isinstance(accepted, dict)
                or not _same_ref(accepted.get("candidate_ref"), decision_ref)
                or accepted.get("outcome") not in {"COMMIT_NOW", "EXPERIMENT"}
                or manifest.get("prd_type")
                != (
                    "FORMAL_PRD"
                    if accepted.get("outcome") == "COMMIT_NOW"
                    else "EXPERIMENT_PRD"
                )
                or not isinstance(review_binding, dict)
                or review_binding.get("verdict") != "PASS"
                or not _same_ref(review_binding.get("candidate_ref"), decision_ref)
            ):
                raise AlphaContractError("PRD Release Set accepted Decision binding is invalid")
            self._verify_candidate(decision_ref)
            review_path = self._verify_file_ref(review_binding.get("review_ref"))
            persisted_review = read_json(review_path)
            if (
                persisted_review.get("verdict") != "PASS"
                or not _same_ref(persisted_review.get("candidate_ref"), decision_ref)
            ):
                raise AlphaContractError("PRD Release Set Decision Review binding is invalid")

    @staticmethod
    def _validate_findings(findings: Any) -> list[dict[str, Any]]:
        if not isinstance(findings, list):
            raise AlphaContractError("Review findings must be a list")
        normalized = []
        seen = set()
        for finding in findings:
            if not isinstance(finding, dict):
                raise AlphaContractError("each Review Finding must be an object")
            finding_id = _nonempty(finding.get("finding_id"), "Finding id")
            if finding_id in seen:
                raise AlphaContractError("Finding ids must be unique")
            seen.add(finding_id)
            if finding.get("severity") not in {"BLOCKER", "MAJOR", "IMPROVEMENT"}:
                raise AlphaContractError("Finding severity must be Reviewer-declared")
            if finding.get("status") not in {
                "OPEN",
                "FIXED",
                "NOT_VALID",
                "DOWNGRADED",
                "ACCEPTED_LIMITATION",
                "NEEDS_OWNER",
                "STALE",
            }:
                raise AlphaContractError("Finding status is invalid")
            _nonempty(finding.get("evidence"), "Finding evidence")
            normalized.append(deepcopy(finding))
        return normalized

    def _apply_return_target(
        self,
        state: dict[str, Any],
        target: str,
        *,
        wait_condition: dict[str, Any] | None,
    ) -> None:
        if target == "OWNER":
            state["status"] = "OWNER_ACTION_REQUIRED"
            state["position"] = "OWNER"
        elif target == "WAIT":
            if not isinstance(wait_condition, dict):
                raise AlphaContractError("WAIT return requires an explicit Trigger condition")
            _nonempty(wait_condition.get("condition_id"), "WAIT condition id")
            _nonempty(wait_condition.get("description"), "WAIT condition description")
            return_target = wait_condition.get("return_target")
            if return_target not in {"UNDERSTAND", "DIAGNOSE_VALUE", "DISCOVER_SOLUTIONS_DECIDE"}:
                raise AlphaContractError("WAIT return target is invalid")
            state["status"] = "WAITING_TRIGGER"
            state["position"] = "DECISION_ROUTE"
            state["waiting"] = deepcopy(wait_condition)
        else:
            state["status"] = "ACTIVE"
            state["position"] = target

    def _ready_unmet(self, state: dict[str, Any]) -> list[str]:
        unmet: list[str] = []
        candidate = state.get("current_candidate")
        review = state.get("current_review")
        if not isinstance(candidate, dict) or candidate.get("kind") != "PRD":
            return ["CURRENT_PRD_RELEASE_SET"]
        try:
            self._verify_candidate(candidate)
        except AlphaContractError:
            unmet.append("CURRENT_PRD_RELEASE_SET")
        if (
            not isinstance(review, dict)
            or review.get("verdict") != "PASS"
            or not _same_ref(review.get("candidate_ref"), candidate)
        ):
            unmet.append("PRD_REVIEW_PASS")
        if isinstance(review, dict):
            for finding in review.get("findings", []):
                if finding.get("severity") in {"BLOCKER", "MAJOR"} and finding.get("status") in {
                    "OPEN",
                    "NEEDS_OWNER",
                }:
                    unmet.append("OPEN_BLOCKER_OR_MAJOR")
                    break
            if any(item.get("status") != "RESOLVED" for item in review.get("disagreements", [])):
                unmet.append("OPEN_REVIEW_DISAGREEMENT")
            if any(
                item.get("required") is True and item.get("status") != "PASS"
                for item in review.get("professional_reviews", [])
            ):
                unmet.append("REQUIRED_PROFESSIONAL_REVIEW")
        evals = state.get("product_evals")
        if not isinstance(evals, dict):
            unmet.append("PRODUCT_EVALS_APPLICABILITY")
        elif evals.get("applicability") == "REQUIRED" and not (
            evals.get("generation_status") == "GENERATED"
            and evals.get("spec_review_status") == "PASS"
            and bool(evals.get("attachment_paths"))
            and evals.get("execution_status") == "NOT_RUN"
        ):
            unmet.append("REQUIRED_PRODUCT_EVALS")
        planning_ref = candidate.get("planning_record_ref", {})
        try:
            self._verify_file_ref(planning_ref)
        except AlphaContractError:
            unmet.append("PLANNING_RECORD_STALE")
        decision_ref = state.get("decision_candidate_ref")
        try:
            if not isinstance(decision_ref, dict):
                raise AlphaContractError("missing Decision Candidate")
            self._verify_candidate(decision_ref)
        except AlphaContractError:
            unmet.append("DECISION_CANDIDATE_STALE")
        if not isinstance(state.get("decision"), dict):
            unmet.append("ACCEPTED_DECISION")
        elif "CURRENT_PRD_RELEASE_SET" in unmet:
            unmet.append("ACCEPTED_DECISION")
        else:
            manifest = read_json(self.project_root / candidate["path"])
            accepted = manifest.get("accepted_decision")
            decision = state["decision"]
            if (
                not isinstance(accepted, dict)
                or accepted.get("outcome") != decision.get("outcome")
                or accepted.get("source") != decision.get("source")
                or accepted.get("authorization_id") != decision.get("authorization_id")
                or not _same_ref(accepted.get("candidate_ref"), decision_ref)
            ):
                unmet.append("ACCEPTED_DECISION")
        return list(dict.fromkeys(unmet))

    def submit_review(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        candidate_ref: dict[str, Any],
        reviewer_attempt_id: str,
        verdict: str,
        findings: list[dict[str, Any]],
        return_target: str | None = None,
        return_reason: str | None = None,
        affected_scope: list[str] | None = None,
        review_mode: str = "FULL",
        diff_base_candidate_ref: dict[str, Any] | None = None,
        global_regression: str | None = None,
        disagreements: list[dict[str, Any]] | None = None,
        professional_reviews: list[dict[str, Any]] | None = None,
        wait_condition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        reviewer_attempt_id = _nonempty(reviewer_attempt_id, "reviewer_attempt_id")
        if verdict not in {"PASS", "REVISE", "NEEDS_OWNER"}:
            raise AlphaContractError("Review Verdict must be PASS, REVISE, or NEEDS_OWNER")
        normalized_findings = self._validate_findings(findings)
        if verdict != "PASS":
            if return_target not in REVIEW_TARGETS:
                raise AlphaContractError("non-PASS Review requires a legal return_target")
            _nonempty(return_reason, "return_reason")
            if not isinstance(affected_scope, list) or not affected_scope or not all(
                isinstance(item, str) and item.strip() for item in affected_scope
            ):
                raise AlphaContractError("non-PASS Review requires affected_scope")
        payload = self._operation_payload(
            "submit_review",
            candidate_ref=candidate_ref,
            reviewer_attempt_id=reviewer_attempt_id,
            verdict=verdict,
            findings=normalized_findings,
            return_target=return_target,
            return_reason=return_reason,
            affected_scope=affected_scope,
            review_mode=review_mode,
            diff_base_candidate_ref=diff_base_candidate_ref,
            global_regression=global_regression,
            disagreements=disagreements or [],
            professional_reviews=professional_reviews or [],
            wait_condition=wait_condition,
        )

        def apply(state: dict[str, Any]) -> None:
            candidate = state.get("current_candidate")
            if not _same_ref(candidate, candidate_ref):
                raise AlphaContractError("Review must bind the exact current Candidate")
            self._verify_candidate(candidate)
            if reviewer_attempt_id == candidate.get("author_attempt_id"):
                raise AlphaContractError("Reviewer attempt must be independent from the author attempt")
            if candidate.get("status") != "FROZEN":
                raise AlphaContractError("Candidate has already received a formal Review")
            if candidate.get("revision_round", 0) > 0:
                if (
                    review_mode != "DIFF_AND_REGRESSION"
                    or not _same_ref(diff_base_candidate_ref, candidate.get("supersedes"))
                    or global_regression not in {"PASS", "FAIL"}
                ):
                    raise AlphaContractError(
                        "revised Candidate requires difference review and whole-product regression"
                    )
                if verdict == "PASS" and global_regression != "PASS":
                    raise AlphaContractError("PASS requires a declared passing whole-product regression")
            review = {
                "schema_version": "bpg2-alpha-review.v1",
                "review_id": f"review-{candidate['candidate_id']}",
                "candidate_ref": self._candidate_ref(candidate),
                "reviewer_attempt_id": reviewer_attempt_id,
                "verdict": verdict,
                "findings": normalized_findings,
                "return_target": return_target,
                "return_reason": return_reason,
                "affected_scope": affected_scope or [],
                "review_mode": review_mode,
                "diff_base_candidate_ref": diff_base_candidate_ref,
                "global_regression": global_regression,
                "disagreements": deepcopy(disagreements or []),
                "professional_reviews": deepcopy(professional_reviews or []),
                "recorded_at": _now(),
            }
            review_path = self.run_path(run_id) / "reviews" / f"{candidate['candidate_id']}.json"
            if review_path.exists():
                raise AlphaContractError("immutable Review path already exists")
            atomic_write_json(review_path, review)
            review["review_ref"] = self.file_ref(review_path)
            state["current_review"] = review
            state.setdefault("reviews", []).append(deepcopy(review))
            candidate["status"] = f"REVIEWED_{verdict}"
            if candidate.get("kind") == "DECISION" and verdict == "PASS":
                state["decision_candidate_ref"] = self._candidate_ref(candidate)
                state["decision_review_ref"] = {
                    "verdict": "PASS",
                    "candidate_ref": self._candidate_ref(candidate),
                    "reviewer_attempt_id": reviewer_attempt_id,
                    "review_ref": review["review_ref"],
                }
            if verdict == "PASS":
                if candidate["kind"] == "PRD":
                    unmet = self._ready_unmet(state)
                    state["ready"] = {
                        "status": "READY" if not unmet else "NOT_READY",
                        "candidate_ref": self._candidate_ref(candidate),
                        "review_ref": review["review_ref"],
                        "unmet": unmet,
                    }
                    if not unmet:
                        state["status"] = "READY"
                        state["position"] = "READY"
                else:
                    state["position"] = PASS_POSITION[candidate["kind"]]
                return
            if verdict == "NEEDS_OWNER":
                state["status"] = "OWNER_ACTION_REQUIRED"
                state["position"] = "OWNER"
                state["candidate_required"] = True
                return
            if candidate.get("revision_round", 0) >= 2:
                if return_target == LOCAL_REVISION_TARGET[candidate["kind"]]:
                    raise AlphaContractError(
                        "two automatic revision rounds are exhausted; route by the declared reason"
                    )
                state["automatic_revision_exhausted"] = True
            state["candidate_required"] = True
            self._apply_return_target(state, return_target, wait_condition=wait_condition)

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )

    def submit_decision_route(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        candidate_ref: dict[str, Any],
        actor: dict[str, Any],
        outcome: str,
        return_target: str | None = None,
        wait_condition: dict[str, Any] | None = None,
        cognition_change: dict[str, Any] | None = None,
        authorization_id: str | None = None,
        agent_assessment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if outcome not in DECISION_OUTCOMES:
            raise AlphaContractError("Decision outcome is not one of the six BPG 2.0 routes")
        if not isinstance(actor, dict) or actor.get("kind") not in {"OWNER", "AGENT"}:
            raise AlphaContractError("Decision route requires an OWNER or AGENT actor")
        _nonempty(actor.get("id"), "decision actor id")
        if actor["kind"] == "AGENT" and outcome != "COMMIT_NOW":
            raise AlphaContractError("Owner must choose STOP, WAIT, RESEARCH, EXPERIMENT, or FUTURE_ROADMAP")
        payload = self._operation_payload(
            "submit_decision_route",
            candidate_ref=candidate_ref,
            actor=actor,
            outcome=outcome,
            return_target=return_target,
            wait_condition=wait_condition,
            cognition_change=cognition_change,
            authorization_id=authorization_id,
            agent_assessment=agent_assessment,
        )

        def apply(state: dict[str, Any]) -> None:
            candidate = state.get("current_candidate")
            if (
                state.get("position") != "DECISION_ROUTE"
                or not _same_ref(candidate, candidate_ref)
                or candidate.get("kind") != "DECISION"
                or candidate.get("status") != "REVIEWED_PASS"
            ):
                raise AlphaContractError("Decision route requires the exact PASS Decision Candidate")
            self._verify_candidate(candidate)
            if cognition_change is not None:
                if not isinstance(cognition_change, dict):
                    raise AlphaContractError("cognition_change must be explicit")
                target = cognition_change.get("return_target")
                if target not in {"UNDERSTAND", "DIAGNOSE_VALUE", "DISCOVER_SOLUTIONS_DECIDE"}:
                    raise AlphaContractError("cognition change return target is invalid")
                _nonempty(cognition_change.get("reason"), "cognition change reason")
                candidate["status"] = "STALE"
                state["status"] = "ACTIVE"
                state["position"] = target
                state["candidate_required"] = True
                state["owner_cognition_change"] = deepcopy(cognition_change)
                return
            source = "OWNER_CHOICE"
            if actor["kind"] == "AGENT":
                authorization = state.get("preauthorization")
                review = state.get("current_review")
                has_needs_owner = isinstance(review, dict) and any(
                    finding.get("status") == "NEEDS_OWNER"
                    for finding in review.get("findings", [])
                    if isinstance(finding, dict)
                )
                has_open_disagreement = isinstance(review, dict) and any(
                    disagreement.get("status") != "RESOLVED"
                    for disagreement in review.get("disagreements", [])
                    if isinstance(disagreement, dict)
                )
                assessment_flags = (
                    "goals_unchanged",
                    "local_planning_only",
                    "low_risk",
                    "reversible",
                    "no_high_impact_unknowns",
                )
                assessment_bound = (
                    isinstance(agent_assessment, dict)
                    and agent_assessment.get("planning_record_ref")
                    == state.get("planning_record_ref")
                    and all(agent_assessment.get(key) is True for key in assessment_flags)
                    and isinstance(agent_assessment.get("rationale"), str)
                    and bool(agent_assessment["rationale"].strip())
                    and isinstance(agent_assessment.get("reconsideration_conditions"), str)
                    and bool(agent_assessment["reconsideration_conditions"].strip())
                )
                if not (
                    isinstance(authorization, dict)
                    and authorization.get("authorization_id") == authorization_id
                    and authorization.get("allowed_outcome") == "COMMIT_NOW"
                    and authorization.get("scope") == "LOCAL_PLANNING_ONLY"
                    and isinstance(review, dict)
                    and review.get("verdict") == "PASS"
                    and _same_ref(review.get("candidate_ref"), candidate)
                    and not has_needs_owner
                    and not has_open_disagreement
                    and assessment_bound
                ):
                    state["status"] = "OWNER_CHOICE_REQUIRED"
                    state["owner_requirement"] = "AGENT_AUTO_COMMIT_CONTRACT_UNMET"
                    return
                source = "AGENT_PREAUTHORIZED"
            decision = {
                "outcome": outcome,
                "source": source,
                "actor": deepcopy(actor),
                "candidate_ref": self._candidate_ref(candidate),
                "authorization_id": authorization_id,
                "agent_assessment": deepcopy(agent_assessment),
                "recorded_at": _now(),
            }
            state["decision"] = decision
            state["decision_candidate_ref"] = self._candidate_ref(candidate)
            state["candidate_required"] = False
            if outcome == "STOP":
                state["status"] = "COMPLETED_STOP"
            elif outcome == "FUTURE_ROADMAP":
                state["status"] = "COMPLETED_FUTURE_ROADMAP"
            elif outcome == "WAIT":
                if not isinstance(wait_condition, dict):
                    raise AlphaContractError("WAIT requires an explicit Trigger condition")
                _nonempty(wait_condition.get("condition_id"), "WAIT condition id")
                _nonempty(wait_condition.get("description"), "WAIT condition description")
                if wait_condition.get("return_target") not in {
                    "UNDERSTAND",
                    "DIAGNOSE_VALUE",
                    "DISCOVER_SOLUTIONS_DECIDE",
                }:
                    raise AlphaContractError("WAIT return target is invalid")
                state["status"] = "WAITING_TRIGGER"
                state["waiting"] = deepcopy(wait_condition)
            elif outcome == "RESEARCH":
                if return_target not in {
                    "UNDERSTAND",
                    "DIAGNOSE_VALUE",
                    "DISCOVER_SOLUTIONS_DECIDE",
                }:
                    raise AlphaContractError("RESEARCH requires the Agent-declared earliest affected stage")
                state["status"] = "ACTIVE"
                state["position"] = return_target
            elif outcome == "EXPERIMENT":
                state["status"] = "ACTIVE"
                state["position"] = "PRD_AUTHORING"
                state["delivery_intent"] = "EXPERIMENT"
            elif outcome == "COMMIT_NOW":
                state["status"] = "ACTIVE"
                state["position"] = "PLAN_PRODUCT_SYSTEM"
                state["delivery_intent"] = "COMMIT_NOW"

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )

    def pause_run(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
    ) -> dict[str, Any]:
        payload = self._operation_payload("pause_run")

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") != "ACTIVE" or state.get("position") not in POSITIONS:
                raise AlphaContractError("Run can pause only at an active safe boundary")
            state["resume_position"] = state["position"]
            state["status"] = "PAUSED"

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )

    def resume_run(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        trigger: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._operation_payload("resume_run", trigger=trigger)

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") == "PAUSED":
                if trigger is not None:
                    raise AlphaContractError("PAUSE resume does not consume a Product WAIT Trigger")
                state["status"] = "ACTIVE"
                state["position"] = state.pop("resume_position")
                return
            if state.get("status") != "WAITING_TRIGGER":
                raise AlphaContractError("Run is not paused or waiting")
            if not isinstance(trigger, dict):
                raise AlphaContractError("WAIT cannot resume without a matching Trigger")
            waiting = state.get("waiting")
            if trigger.get("condition_id") != waiting.get("condition_id"):
                raise AlphaContractError("WAIT Trigger condition does not match")
            trigger_id = _nonempty(trigger.get("trigger_id"), "trigger_id")
            if trigger_id in state.get("used_trigger_ids", []):
                raise AlphaContractError("WAIT Trigger has already been consumed")
            self._verify_file_ref(trigger.get("evidence_ref"))
            state.setdefault("used_trigger_ids", []).append(trigger_id)
            state["status"] = "ACTIVE"
            state["position"] = waiting["return_target"]
            state["consumed_trigger"] = deepcopy(trigger)
            state.pop("waiting", None)

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )

    def prepare_local_handoff(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
    ) -> dict[str, Any]:
        payload = self._operation_payload("prepare_local_handoff")

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") != "READY" or state.get("ready", {}).get("status") != "READY":
                raise AlphaContractError("Local Handoff requires the unique Ready contract")
            candidate = state["current_candidate"]
            self._verify_candidate(candidate)
            source_dir = self.project_root / candidate["artifact_path"]
            target = self.run_path(run_id) / "handoff" / "local"
            if target.exists():
                raise AlphaContractError("Local Handoff target already exists outside idempotent replay")
            target.mkdir(parents=True)
            for path in sorted(source_dir.rglob("*")):
                if path.is_file():
                    relative = path.relative_to(source_dir)
                    atomic_write_bytes(target / relative, path.read_bytes())
            note = (
                "# Local Handoff\n\n"
                "本交接只包含当前精确 PRD Release Set 的本地文件。\n\n"
                "- 默认阅读：PRD.html\n"
                "- 编辑真源：PRD.md 与 assets\n"
                "- 外部发送：NOT_RUN\n"
                "- 研发接收：NOT_RUN\n"
                "- 测试与产品效果验证：NOT_RUN\n"
            )
            atomic_write_bytes(target / "HANDOFF.md", note.encode("utf-8"))
            files = []
            for path in sorted(target.rglob("*")):
                if path.is_file() and path.name != "HANDOFF_MANIFEST.json":
                    files.append(
                        {
                            "path": path.relative_to(target).as_posix(),
                            "hash": sha256_file(path),
                            "size": path.stat().st_size,
                        }
                    )
            candidate_manifest = read_json(self.project_root / candidate["path"])
            manifest = {
                "schema_version": "bpg2-alpha-local-handoff.v1",
                "run_id": run_id,
                "candidate_ref": self._candidate_ref(candidate),
                "ready_ref": deepcopy(state["ready"]),
                "prd_type": candidate_manifest["prd_type"],
                "files": files,
                "local_only": True,
                "external_delivery": "NOT_RUN",
                "engineering_received": "NOT_RUN",
                "tests": "NOT_RUN",
                "product_effect_validation": "NOT_RUN",
            }
            manifest_path = target / "HANDOFF_MANIFEST.json"
            atomic_write_json(manifest_path, manifest)
            state["handoff"] = {
                "status": "LOCAL_HANDOFF_COMPLETE",
                "path": target.relative_to(self.project_root).as_posix(),
                "manifest_ref": self.file_ref(manifest_path),
            }
            state["status"] = "LOCAL_HANDOFF_COMPLETE"
            state["external_delivery"] = "NOT_RUN"
            state["retrospective_status"] = "NOT_RUN"

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )

    def record_retrospective(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        author_attempt_id: str,
        markdown: str,
    ) -> dict[str, Any]:
        author_attempt_id = _nonempty(author_attempt_id, "retrospective author attempt")
        markdown = _nonempty(markdown, "retrospective")
        payload = self._operation_payload(
            "record_retrospective",
            author_attempt_id=author_attempt_id,
            markdown=markdown,
        )

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") != "LOCAL_HANDOFF_COMPLETE":
                raise AlphaContractError("planning retrospective follows Local Handoff")
            path = self.run_path(run_id) / "planning-retrospective.md"
            if path.exists():
                raise AlphaContractError("retrospective already exists outside idempotent replay")
            atomic_write_bytes(path, markdown.encode("utf-8"))
            state["retrospective_status"] = "COMPLETED"
            state["retrospective_ref"] = self.file_ref(path)

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )
