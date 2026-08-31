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
from .visual_assets import VisualAssetError, scan_reader_visible_visual_source
from .writing_review import WritingReviewError, load_and_validate_writing_coverage


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
STAGE4_ARTIFACT_IDS = frozenset(
    {
        "SCOPE_REQUIREMENTS_MATRIX",
        "TARGET_EXPERIENCE_CORE_FLOW",
        "PRODUCT_EXPERIENCE_INFORMATION_STRUCTURE",
        "LOGICAL_PRODUCT_SYSTEM",
        "MODULE_MAP_AND_DETAILS",
        "GLOBAL_RULES_SHARED_CONTRACTS",
        "COMPLETE_SYSTEM_ITERATION_STRUCTURE",
        "COHERENCE_COVERAGE_TRACEABILITY",
        "DATA_COLLECTION_APPLICABILITY",
    }
)
REVIEW_RESPONSIBILITY_IDS = frozenset(
    {
        "PRODUCT_GOAL_AND_REQUIREMENTS",
        "USER_EXPERIENCE_AND_CONTENT",
        "PRODUCT_SYSTEM_COHERENCE",
        "ENGINEERING_FEASIBILITY",
        "ACCEPTANCE_AND_PRODUCT_EVALS",
        "DOCUMENT_EXPERIENCE",
    }
)
HANDOFF_DELIVERY_MODES = frozenset(
    {
        "LOCAL_HTML",
        "LOCAL_DOCUMENT",
        "FEISHU_DOCUMENT",
        "PROJECT_MANAGEMENT_MCP",
    }
)
IMPLEMENTED_HANDOFF_DELIVERY_MODES = frozenset({"LOCAL_HTML"})
DEFAULT_HANDOFF_DELIVERY_OPTIONS = {
    "LOCAL_HTML": True,
    "LOCAL_DOCUMENT": False,
    "FEISHU_DOCUMENT": False,
    "PROJECT_MANAGEMENT_MCP": False,
}
RETROSPECTIVE_CONFORMANCE_IDS = frozenset(
    {
        "PLANNING_RECORD_REPLACEMENT_SAFETY",
        "STAGE4_DISPOSITIONS",
        "DOCUMENT_EXPERIENCE",
        "REVIEW_BASIS",
        "SIX_REVIEW_RESPONSIBILITIES",
        "WRITING_REVIEW",
        "HANDOFF_DELIVERY_RENDERING",
        "NOT_RUN_BOUNDARIES",
    }
)
PROTECTED_PLANNING_SECTIONS = frozenset({"Signal 与当前边界"})
SECTION_REMOVAL_TARGETS = {
    "DIAGNOSE_VALUE": frozenset({"UNDERSTAND"}),
    "DISCOVER_SOLUTIONS_DECIDE": frozenset({"UNDERSTAND", "DIAGNOSE_VALUE"}),
    "PLAN_PRODUCT_SYSTEM": frozenset(
        {"UNDERSTAND", "DIAGNOSE_VALUE", "DISCOVER_SOLUTIONS_DECIDE"}
    ),
    "PRD_AUTHORING": frozenset(
        {
            "UNDERSTAND",
            "DIAGNOSE_VALUE",
            "DISCOVER_SOLUTIONS_DECIDE",
            "PLAN_PRODUCT_SYSTEM",
        }
    ),
    "RESEARCH": frozenset(
        {"UNDERSTAND", "DIAGNOSE_VALUE", "DISCOVER_SOLUTIONS_DECIDE"}
    ),
}
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


def _h2_sections(markdown: str) -> list[str]:
    """Return stable second-level Markdown headings without judging their meaning."""

    return [
        match.group(1).strip()
        for match in re.finditer(r"^##[ \t]+(.+?)[ \t]*$", markdown, flags=re.MULTILINE)
    ]


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
    def _core_reference_source(relative: str) -> Path:
        module = Path(__file__).resolve()
        candidates = (
            module.parents[1] / "core" / relative,
            module.parents[2] / "references" / relative,
        )
        source = next((path for path in candidates if path.is_file() and not path.is_symlink()), None)
        if source is None:
            raise AlphaContractError(f"BPG 2.0 Alpha reference is unavailable: {relative}")
        return source

    @classmethod
    def _template_source(cls) -> Path:
        return cls._core_reference_source("templates/general/PRD_TEMPLATE_v2.0-alpha.md")

    @classmethod
    def _review_authority_sources(cls) -> dict[str, tuple[Path, str]]:
        return {
            "output_contract": (
                cls._core_reference_source(
                    "templates/general/PRD_OUTPUT_CONTRACT_v2.0-alpha.json"
                ),
                "2.0-alpha.1",
            ),
            "writing_profile": (
                cls._core_reference_source("policies/prd-writing-profile-v0.5.json"),
                "0.5.0",
            ),
            "writing_guide": (
                cls._core_reference_source("policies/prd-writing-guide-v0.5.md"),
                "0.5.0",
            ),
            "writing_review_contract": (
                cls._core_reference_source(
                    "reviewer-profiles/prd-writing-reader-review-v3.1.json"
                ),
                "v3.1",
            ),
        }

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
        if (
            state.get("runtime") != RUNTIME
            or state.get("run_id") != run_id
            or state.get("schema_version") != "bpg2-alpha-run.v2"
        ):
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

    def versioned_file_ref(self, path: Path, version: int | str) -> dict[str, Any]:
        return {**self.file_ref(path), "version": version}

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
                "schema_version": "bpg2-alpha-run.v2",
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

    @staticmethod
    def _validate_stage4_dispositions(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise AlphaContractError("Stage 4 dispositions must be a complete list")
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in value:
            if not isinstance(raw, dict):
                raise AlphaContractError("each Stage 4 disposition must be an object")
            allowed = {"artifact_id", "status", "rationale"}
            if raw.get("status") == "BLOCKED":
                allowed.update({"missing_input", "owner", "recovery"})
            if set(raw) != allowed:
                raise AlphaContractError("Stage 4 disposition fields are incomplete or unknown")
            artifact_id = _nonempty(raw.get("artifact_id"), "Stage 4 artifact_id")
            if artifact_id not in STAGE4_ARTIFACT_IDS or artifact_id in seen:
                raise AlphaContractError("Stage 4 artifact coverage must be exact and unique")
            seen.add(artifact_id)
            status = raw.get("status")
            if status not in {"COMPLETE", "NOT_APPLICABLE", "BLOCKED"}:
                raise AlphaContractError("Stage 4 disposition status is invalid")
            _nonempty(raw.get("rationale"), "Stage 4 disposition rationale")
            if status == "BLOCKED":
                _nonempty(raw.get("missing_input"), "Stage 4 blocked missing_input")
                _nonempty(raw.get("owner"), "Stage 4 blocked owner")
                _nonempty(raw.get("recovery"), "Stage 4 blocked recovery")
            normalized.append(deepcopy(raw))
        if seen != STAGE4_ARTIFACT_IDS:
            missing = sorted(STAGE4_ARTIFACT_IDS - seen)
            raise AlphaContractError(f"Stage 4 dispositions are incomplete: {missing}")
        return normalized

    @staticmethod
    def _validate_removal_basis(
        value: Any,
        *,
        position: str,
        missing_sections: list[str],
    ) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != {
            "return_target",
            "reason",
            "removed_sections",
        }:
            raise AlphaContractError("section removal requires one closed upstream return basis")
        return_target = value.get("return_target")
        if return_target not in SECTION_REMOVAL_TARGETS.get(position, frozenset()):
            raise AlphaContractError("section removal return_target is not an earlier legal stage")
        _nonempty(value.get("reason"), "section removal reason")
        removed = value.get("removed_sections")
        if not isinstance(removed, list) or removed != missing_sections:
            raise AlphaContractError("section removal must name the exact removed sections")
        return deepcopy(value)

    def replace_planning_record(
        self,
        run_id: str,
        *,
        expected_state_version: int,
        operation_id: str,
        author_attempt_id: str,
        position: str,
        mode: str,
        base_hash: str,
        markdown: str,
        next_position: str | None = None,
        removal_basis: dict[str, Any] | None = None,
        stage4_dispositions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        author_attempt_id = _nonempty(author_attempt_id, "author_attempt_id")
        if mode != "REPLACE_FULL":
            raise AlphaContractError("planning record mode must be REPLACE_FULL")
        base_hash = _nonempty(base_hash, "base_hash")
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
            "replace_planning_record",
            author_attempt_id=author_attempt_id,
            position=position,
            mode=mode,
            base_hash=base_hash,
            markdown=markdown,
            next_position=next_position,
            removal_basis=removal_basis,
            stage4_dispositions=stage4_dispositions,
        )

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") != "ACTIVE" or state.get("position") != position:
                raise AlphaContractError("planning record replacement does not match the current position")
            path = self.run_path(run_id) / "planning-record.md"
            current_ref = self.file_ref(path)
            if state.get("planning_record_ref") != current_ref or base_hash != current_ref["hash"]:
                raise AlphaContractError("base_hash does not match the current Planning Record")
            current_markdown = path.read_text(encoding="utf-8")
            current_sections = _h2_sections(current_markdown)
            new_sections = set(_h2_sections(markdown))
            missing_sections = [item for item in current_sections if item not in new_sections]
            protected_missing = [
                item for item in missing_sections if item in PROTECTED_PLANNING_SECTIONS
            ]
            if protected_missing:
                raise AlphaContractError(
                    "full replacement cannot remove protected sections: "
                    + ", ".join(protected_missing)
                )
            normalized_removal = None
            if missing_sections:
                if removal_basis is None:
                    raise AlphaContractError(
                        "full replacement would remove existing sections: "
                        + ", ".join(missing_sections)
                    )
                if next_position is not None:
                    raise AlphaContractError(
                        "section removal cannot advance while returning to an earlier stage"
                    )
                normalized_removal = self._validate_removal_basis(
                    removal_basis,
                    position=position,
                    missing_sections=missing_sections,
                )
            elif removal_basis is not None:
                raise AlphaContractError("section removal basis is forbidden when no section is removed")

            normalized_stage4 = None
            if position == "PLAN_PRODUCT_SYSTEM" and next_position == "PRD_AUTHORING":
                normalized_stage4 = self._validate_stage4_dispositions(stage4_dispositions)
                if any(item["status"] == "BLOCKED" for item in normalized_stage4):
                    raise AlphaContractError("Stage 4 BLOCKED dispositions prevent PRD authoring")
            elif stage4_dispositions is not None:
                raise AlphaContractError(
                    "Stage 4 dispositions are accepted only when entering PRD authoring"
                )

            atomic_write_bytes(path, markdown.encode("utf-8"))
            new_ref = self.file_ref(path)
            state["planning_record_ref"] = new_ref
            state["last_author_attempt_id"] = author_attempt_id
            state["last_record_replacement"] = {
                "mode": "REPLACE_FULL",
                "old_hash": current_ref["hash"],
                "new_hash": new_ref["hash"],
                "removed_sections": missing_sections,
                "message": "submitted Markdown is the complete Planning Record truth source",
            }
            if normalized_stage4 is not None:
                state["stage4_dispositions"] = {
                    "record_ref": deepcopy(new_ref),
                    "author_attempt_id": author_attempt_id,
                    "items": normalized_stage4,
                }
            if normalized_removal is not None:
                state["position"] = normalized_removal["return_target"]
                state["candidate_required"] = True
                candidate = state.get("current_candidate")
                if isinstance(candidate, dict):
                    candidate["status"] = "STALE"
                state["upstream_return"] = normalized_removal
                state["ready"] = {"status": "NOT_EVALUATED", "unmet": []}
            elif next_position is not None:
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

    def _validate_document_experience(
        self,
        value: Any,
        *,
        source_dir: Path,
        author_attempt_id: str,
    ) -> dict[str, Any]:
        expected_fields = {
            "schema_version",
            "author_attempt_id",
            "draft_ref",
            "profile_id",
            "profile_version",
            "guide_id",
            "guide_version",
            "diagnoses",
            "actions",
            "zero_context_reading_path",
            "split_assessment",
            "claim_boundary",
        }
        if not isinstance(value, dict) or set(value) != expected_fields:
            raise AlphaContractError("PRD document experience evidence is incomplete")
        if value.get("schema_version") != "bpg2-alpha-document-experience.v1":
            raise AlphaContractError("PRD document experience schema is invalid")
        if value.get("author_attempt_id") != author_attempt_id:
            raise AlphaContractError("PRD document experience must bind the author attempt")
        expected_draft = self.file_ref(source_dir / "PRD.md")
        if value.get("draft_ref") != expected_draft:
            raise AlphaContractError("PRD document experience draft_ref is stale")
        if (
            value.get("profile_id") != "prd-plain-language-zh-CN"
            or value.get("profile_version") != "0.5.0"
            or value.get("guide_id") != "prd-writing-guide-v0.5"
            or value.get("guide_version") != "0.5.0"
        ):
            raise AlphaContractError("PRD document experience authority is stale")
        for field in ("diagnoses", "actions"):
            items = value.get(field)
            if (
                not isinstance(items, list)
                or not items
                or not all(isinstance(item, str) and item.strip() for item in items)
            ):
                raise AlphaContractError(f"PRD document experience {field} must be non-empty")
        _nonempty(value.get("zero_context_reading_path"), "zero-context reading path")
        split = value.get("split_assessment")
        if not isinstance(split, dict) or set(split) != {"decision", "rationale"}:
            raise AlphaContractError("PRD document experience split assessment is incomplete")
        if split.get("decision") != "KEEP_SINGLE":
            raise AlphaContractError("single-PRD Alpha cannot freeze a split-required document")
        _nonempty(split.get("rationale"), "single-PRD rationale")
        if value.get("claim_boundary") != "AUTHOR_SELF_CHECK_NOT_INDEPENDENT_APPROVAL":
            raise AlphaContractError("PRD document experience claim boundary is invalid")
        return deepcopy(value)

    def _write_prd_candidate(
        self,
        run_id: str,
        version: int,
        source_dir: Path,
        author_attempt_id: str,
        evals: dict[str, Any],
        document_experience: dict[str, Any],
        planning_record_ref: dict[str, Any],
        decision_candidate_ref: dict[str, Any],
        accepted_decision: dict[str, Any],
        decision_review_ref: dict[str, Any],
        delivery_intent: str,
    ) -> tuple[Path, dict[str, Any], dict[str, Any]]:
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
        for path in sorted(source_dir.rglob("*")):
            if path.is_symlink():
                raise AlphaContractError("PRD Release Set cannot contain symlinks")
            if path.is_file():
                relative = path.relative_to(source_dir)
                target = candidate_dir / relative
                atomic_write_bytes(target, path.read_bytes())
        machine_dir = candidate_dir / ".machine"
        planning_snapshot = machine_dir / "planning-record-snapshot.md"
        review_basis_dir = machine_dir / "review-basis"
        template_snapshot = review_basis_dir / "PRD_TEMPLATE_v2.0-alpha.md"
        atomic_write_bytes(
            planning_snapshot,
            (self.run_path(run_id) / "planning-record.md").read_bytes(),
        )
        atomic_write_bytes(template_snapshot, self._template_source().read_bytes())
        authority_sources = self._review_authority_sources()
        authority_targets = {
            "output_contract": review_basis_dir / "PRD_OUTPUT_CONTRACT_v2.0-alpha.json",
            "writing_profile": review_basis_dir / "prd-writing-profile-v0.5.json",
            "writing_guide": review_basis_dir / "prd-writing-guide-v0.5.md",
            "writing_review_contract": review_basis_dir
            / "prd-writing-reader-review-v3.1.json",
        }
        for role, target in authority_targets.items():
            atomic_write_bytes(target, authority_sources[role][0].read_bytes())
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
        candidate_tree_hash = sha256_bytes(canonical_json_bytes(files))
        prd_ref = self.versioned_file_ref(candidate_dir / "PRD.md", version)
        planning_snapshot_ref = self.versioned_file_ref(planning_snapshot, version)
        template_exact_ref = self.versioned_file_ref(template_snapshot, "2.0-alpha.1")
        authority_refs = {
            role: self.versioned_file_ref(target, authority_sources[role][1])
            for role, target in authority_targets.items()
        }
        decision_basis_ref = {
            key: deepcopy(decision_candidate_ref[key])
            for key in ("path", "hash", "version")
        }
        raw_decision_review_ref = decision_review_ref.get("review_ref")
        self._verify_file_ref(raw_decision_review_ref)
        decision_review_basis_ref = {
            **deepcopy(raw_decision_review_ref),
            "version": decision_candidate_ref["version"],
        }
        product_eval_refs = [
            self.versioned_file_ref(candidate_dir / relative, version)
            for relative in evals.get("attachment_paths", [])
        ]
        review_basis_refs = {
            "prd": prd_ref,
            "planning_record": planning_snapshot_ref,
            "decision_candidate": decision_basis_ref,
            "decision_review": decision_review_basis_ref,
            "template": template_exact_ref,
            "output_contract": authority_refs["output_contract"],
            "writing_profile": authority_refs["writing_profile"],
            "writing_guide": authority_refs["writing_guide"],
            "writing_review_contract": authority_refs["writing_review_contract"],
            "product_eval_attachments": product_eval_refs,
        }
        try:
            visual_source_scan = scan_reader_visible_visual_source(
                self.project_root,
                candidate_dir / "PRD.md",
                candidate_ref=prd_ref,
            )
        except VisualAssetError as error:
            raise AlphaContractError(
                f"PRD visual source is not reviewable: {error}"
            ) from error
        writing_review_context = {
            "schema_version": "writing-review-dispatch.v3",
            "candidate_ref": prd_ref,
            "candidate_tree_hash": candidate_tree_hash,
            "profile_ref": authority_refs["writing_profile"],
            "guide_ref": authority_refs["writing_guide"],
            "review_contract_ref": authority_refs["writing_review_contract"],
            "output_contract_ref": authority_refs["output_contract"],
            "author_execution_ref": {
                "kind": "HOST_AGENT_ATTEMPT",
                "id": author_attempt_id,
            },
            "isolated_input_refs": [
                prd_ref,
                authority_refs["writing_profile"],
                authority_refs["writing_guide"],
                authority_refs["writing_review_contract"],
                authority_refs["output_contract"],
            ],
            "reader_visible_visual_pairs": visual_source_scan["safe_visual_pairs"],
            "visual_source_scan": visual_source_scan,
        }
        review_requirements = {
            "schema_version": "bpg2-alpha-prd-review-requirements.v2",
            "candidate_tree_hash": candidate_tree_hash,
            "responsibility_ids": sorted(REVIEW_RESPONSIBILITY_IDS),
            "review_basis_refs": review_basis_refs,
            "writing_review_context": writing_review_context,
            "claim_boundary": (
                "CONTENT_AND_WRITING_REVIEW_REQUIRED_DELIVERY_RENDERING_DEFERRED"
            ),
        }
        document_experience = {
            **deepcopy(document_experience),
            "profile_ref": authority_refs["writing_profile"],
            "guide_ref": authority_refs["writing_guide"],
        }
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
            "schema_version": "bpg2-alpha-release-set.v3",
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
            "document_experience": document_experience,
            "candidate_tree_hash": candidate_tree_hash,
            "review_requirements": review_requirements,
            "editing_truth": "PRD.md + assets",
            "delivery_rendering": "DEFERRED_TO_HANDOFF",
            "files": files,
        }
        manifest_path = candidate_dir / "machine-manifest.json"
        atomic_write_json(manifest_path, manifest)
        return manifest_path, planning_record_ref, review_requirements

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
        document_experience: dict[str, Any] | None = None,
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
            document_experience=document_experience,
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
            review_requirements = None
            if kind == "PRD":
                if source_dir is None:
                    raise AlphaContractError("PRD Candidate requires a source directory")
                normalized_evals = self._validate_evals(evals, source_dir)
                normalized_document_experience = self._validate_document_experience(
                    document_experience,
                    source_dir=source_dir,
                    author_attempt_id=author_attempt_id,
                )
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
                target, planning_ref, review_requirements = self._write_prd_candidate(
                    run_id,
                    version,
                    source_dir,
                    author_attempt_id,
                    normalized_evals,
                    normalized_document_experience,
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
                state["current_review_requirements"] = review_requirements
            else:
                state.pop("current_review_requirements", None)

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
            if "PRD.md" not in inventory_paths or "PRD.html" in inventory_paths:
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

    def _verify_review_basis_refs(
        self,
        value: Any,
        *,
        expected: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(value, dict) or value != expected:
            raise AlphaContractError("Review basis refs do not match the frozen Candidate")
        for role, ref in value.items():
            if role == "product_eval_attachments":
                if not isinstance(ref, list):
                    raise AlphaContractError("Review basis Product Evals refs must be a list")
                for item in ref:
                    self._verify_file_ref(item)
            else:
                self._verify_file_ref(ref)
        return deepcopy(value)

    @staticmethod
    def _flatten_review_basis_refs(value: dict[str, Any]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for role, ref in value.items():
            if role == "product_eval_attachments":
                refs.extend(deepcopy(ref))
            else:
                refs.append(deepcopy(ref))
        return refs

    def _validate_responsibility_coverage(
        self,
        value: Any,
        *,
        review_basis_refs: dict[str, Any],
        available_finding_ids: set[str],
        author_attempt_id: str,
        content_reviewer_attempt_id: str,
        writing_reviewer_attempt_id: str,
    ) -> tuple[list[dict[str, Any]], set[str]]:
        if not isinstance(value, list):
            raise AlphaContractError("PRD Review responsibility coverage is required")
        allowed_basis = self._flatten_review_basis_refs(review_basis_refs)
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        covered_findings: set[str] = set()
        content_attempts: set[str] = set()
        for raw in value:
            if not isinstance(raw, dict) or set(raw) != {
                "responsibility_id",
                "reviewer_attempt_id",
                "status",
                "rationale",
                "basis_refs",
                "finding_ids",
            }:
                raise AlphaContractError("PRD Review responsibility fields are incomplete")
            responsibility_id = _nonempty(
                raw.get("responsibility_id"), "Review responsibility_id"
            )
            if responsibility_id not in REVIEW_RESPONSIBILITY_IDS or responsibility_id in seen:
                raise AlphaContractError("PRD Review responsibility coverage must be exact and unique")
            seen.add(responsibility_id)
            reviewer_id = _nonempty(
                raw.get("reviewer_attempt_id"), "responsibility reviewer_attempt_id"
            )
            if reviewer_id == author_attempt_id:
                raise AlphaContractError("responsibility Reviewer must be independent from the author")
            if responsibility_id == "DOCUMENT_EXPERIENCE":
                if reviewer_id != writing_reviewer_attempt_id:
                    raise AlphaContractError(
                        "Document Experience responsibility must bind the Writing Reviewer"
                    )
            else:
                if reviewer_id == writing_reviewer_attempt_id:
                    raise AlphaContractError(
                        "Writing Reviewer must remain independent from content responsibility attempts"
                    )
                content_attempts.add(reviewer_id)
            status = raw.get("status")
            if status not in {"PASS", "FINDING", "NOT_APPLICABLE"}:
                raise AlphaContractError("Review responsibility status is invalid")
            _nonempty(raw.get("rationale"), "Review responsibility rationale")
            basis_refs = raw.get("basis_refs")
            if not isinstance(basis_refs, list) or not basis_refs:
                raise AlphaContractError("Review responsibility requires exact basis refs")
            if any(ref not in allowed_basis for ref in basis_refs):
                raise AlphaContractError("Review responsibility basis differs from frozen authority")
            finding_ids = raw.get("finding_ids")
            if (
                not isinstance(finding_ids, list)
                or any(not isinstance(item, str) or not item for item in finding_ids)
                or len(finding_ids) != len(set(finding_ids))
                or not set(finding_ids).issubset(available_finding_ids)
            ):
                raise AlphaContractError("Review responsibility Finding refs are invalid")
            if status == "FINDING" and not finding_ids:
                raise AlphaContractError("FINDING responsibility requires a Review Finding")
            if status != "FINDING" and finding_ids:
                raise AlphaContractError("only FINDING responsibility may link Findings")
            covered_findings.update(finding_ids)
            normalized.append(deepcopy(raw))
        if seen != REVIEW_RESPONSIBILITY_IDS:
            missing = sorted(REVIEW_RESPONSIBILITY_IDS - seen)
            raise AlphaContractError(
                f"PRD Review responsibility coverage is incomplete: {missing}"
            )
        if content_reviewer_attempt_id not in content_attempts:
            raise AlphaContractError(
                "the formal content Reviewer attempt must cover a PRD responsibility"
            )
        if covered_findings != available_finding_ids:
            raise AlphaContractError(
                "every PRD Review Finding must belong to responsibility coverage"
            )
        return normalized, covered_findings

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
            requirements = state.get("current_review_requirements")
            if (
                review.get("schema_version") != "bpg2-alpha-review.v3"
                or not isinstance(requirements, dict)
                or review.get("review_basis_refs") != requirements.get("review_basis_refs")
            ):
                unmet.append("REVIEW_BASIS_STALE")
            coverage = review.get("responsibility_coverage")
            if (
                not isinstance(coverage, list)
                or {item.get("responsibility_id") for item in coverage if isinstance(item, dict)}
                != REVIEW_RESPONSIBILITY_IDS
            ):
                unmet.append("REVIEW_RESPONSIBILITY_COVERAGE")
            writing_ref = review.get("writing_review_ref")
            try:
                self._verify_file_ref(writing_ref)
                if not isinstance(review.get("writing_review"), dict):
                    raise AlphaContractError("missing Writing Review")
            except AlphaContractError:
                unmet.append("WRITING_REVIEW_REQUIRED")
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
            if not isinstance(manifest.get("document_experience"), dict):
                unmet.append("DOCUMENT_EXPERIENCE_EVIDENCE")
            if state.get("delivery_intent") == "COMMIT_NOW":
                stage4 = state.get("stage4_dispositions")
                if (
                    not isinstance(stage4, dict)
                    or stage4.get("record_ref") != candidate.get("planning_record_ref")
                    or len(stage4.get("items", [])) != len(STAGE4_ARTIFACT_IDS)
                    or any(
                        item.get("status") == "BLOCKED"
                        for item in stage4.get("items", [])
                        if isinstance(item, dict)
                    )
                ):
                    unmet.append("STAGE4_DISPOSITIONS")
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

    @staticmethod
    def _ready_evidence_summary(
        state: dict[str, Any],
        *,
        unmet: list[str],
    ) -> dict[str, str]:
        review = state.get("current_review")
        review_pass = isinstance(review, dict) and review.get("verdict") == "PASS"
        evals = state.get("product_evals")
        return {
            "contract_readiness": "PASS" if not unmet else "FAIL",
            "agent_review": "PASS" if review_pass else "NOT_RUN",
            "writing_review": (
                "PASS"
                if review_pass and isinstance(review.get("writing_review"), dict)
                else "NOT_RUN"
            ),
            "handoff_rendering": "NOT_RUN",
            "human_reader_validation": "NOT_RUN",
            "product_eval_execution": (
                evals.get("execution_status", "NOT_RUN")
                if isinstance(evals, dict)
                else "NOT_RUN"
            ),
            "external_delivery": state.get("external_delivery", "NOT_RUN"),
            "engineering_received": "NOT_RUN",
            "engineering_tests": "NOT_RUN",
            "product_effect_validation": "NOT_RUN",
        }

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
        review_basis_refs: dict[str, Any] | None = None,
        responsibility_coverage: list[dict[str, Any]] | None = None,
        writing_review_ref: dict[str, Any] | None = None,
        rendered_html_review: dict[str, Any] | None = None,
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
            review_basis_refs=review_basis_refs,
            responsibility_coverage=responsibility_coverage,
            writing_review_ref=writing_review_ref,
            rendered_html_review=rendered_html_review,
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
            normalized_review_basis = None
            normalized_responsibilities = None
            normalized_writing_ref = None
            normalized_writing_review = None
            if candidate.get("kind") == "PRD":
                requirements = state.get("current_review_requirements")
                if not isinstance(requirements, dict):
                    raise AlphaContractError("PRD Review requirements are unavailable")
                manifest = read_json(self.project_root / candidate["path"])
                if manifest.get("review_requirements") != requirements:
                    raise AlphaContractError("PRD Review requirements are stale")
                if rendered_html_review is not None:
                    raise AlphaContractError(
                        "rendered HTML evidence belongs to Handoff, not Candidate Review"
                    )
                normalized_review_basis = self._verify_review_basis_refs(
                    review_basis_refs,
                    expected=requirements["review_basis_refs"],
                )
                if not isinstance(writing_review_ref, dict):
                    raise AlphaContractError("Writing Review evidence is required")
                try:
                    normalized_writing_review = load_and_validate_writing_coverage(
                        self.project_root,
                        writing_review_ref,
                        context=requirements["writing_review_context"],
                        available_finding_ids={
                            finding["finding_id"] for finding in normalized_findings
                        },
                    )
                except WritingReviewError as error:
                    raise AlphaContractError(f"Writing Review evidence is invalid: {error}") from error
                normalized_writing_ref = deepcopy(writing_review_ref)
                writing_reviewer_attempt_id = normalized_writing_review[
                    "reviewer_execution_ref"
                ]["id"]
                if writing_reviewer_attempt_id == reviewer_attempt_id:
                    raise AlphaContractError(
                        "Writing Reviewer must be independent from the content Reviewer"
                    )
                normalized_responsibilities, _ = self._validate_responsibility_coverage(
                    responsibility_coverage,
                    review_basis_refs=normalized_review_basis,
                    available_finding_ids={
                        finding["finding_id"] for finding in normalized_findings
                    },
                    author_attempt_id=candidate["author_attempt_id"],
                    content_reviewer_attempt_id=reviewer_attempt_id,
                    writing_reviewer_attempt_id=writing_reviewer_attempt_id,
                )
                document_coverage = next(
                    item
                    for item in normalized_responsibilities
                    if item["responsibility_id"] == "DOCUMENT_EXPERIENCE"
                )
                expected_document_findings = set(
                    normalized_writing_review.get("finding_refs", [])
                )
                if set(document_coverage["finding_ids"]) != expected_document_findings:
                    raise AlphaContractError(
                        "Document Experience responsibility must bind Writing Review Findings"
                    )
            elif any(
                item is not None
                for item in (
                    review_basis_refs,
                    responsibility_coverage,
                    writing_review_ref,
                    rendered_html_review,
                )
            ):
                raise AlphaContractError("PRD Review evidence is forbidden for non-PRD Candidates")
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
                "schema_version": (
                    "bpg2-alpha-review.v3"
                    if candidate.get("kind") == "PRD"
                    else "bpg2-alpha-review.v1"
                ),
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
                "review_basis_refs": normalized_review_basis,
                "responsibility_coverage": normalized_responsibilities,
                "writing_review_ref": normalized_writing_ref,
                "writing_review": normalized_writing_review,
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
                        "evidence_summary": self._ready_evidence_summary(
                            state, unmet=unmet
                        ),
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
                state["stage4_requirements"] = {
                    "schema_version": "bpg2-alpha-stage4-dispositions.v1",
                    "artifact_ids": sorted(STAGE4_ARTIFACT_IDS),
                    "statuses": ["COMPLETE", "NOT_APPLICABLE", "BLOCKED"],
                    "claim_boundary": "AGENT_SEMANTICS_CONTROLLER_COMPLETENESS_ONLY",
                }

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
        delivery_options: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        normalized_delivery_options = deepcopy(DEFAULT_HANDOFF_DELIVERY_OPTIONS)
        if delivery_options is not None:
            if not isinstance(delivery_options, dict):
                raise AlphaContractError("Handoff delivery options must be an object")
            for mode, enabled in delivery_options.items():
                if mode not in HANDOFF_DELIVERY_MODES or type(enabled) is not bool:
                    raise AlphaContractError(
                        "Handoff delivery options require known modes and boolean values"
                    )
                normalized_delivery_options[mode] = enabled
        unavailable = sorted(
            mode
            for mode, enabled in normalized_delivery_options.items()
            if enabled and mode not in IMPLEMENTED_HANDOFF_DELIVERY_MODES
        )
        if unavailable:
            raise AlphaContractError(
                f"Handoff delivery mode {', '.join(unavailable)} is NOT_IMPLEMENTED"
            )
        payload = self._operation_payload(
            "prepare_local_handoff",
            delivery_options=normalized_delivery_options,
        )

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") != "READY" or state.get("ready", {}).get("status") != "READY":
                raise AlphaContractError("Local Handoff requires the unique Ready contract")
            current_unmet = self._ready_unmet(state)
            if current_unmet:
                raise AlphaContractError(
                    "Local Handoff Ready evidence is stale: " + ", ".join(current_unmet)
                )
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
            candidate_manifest = read_json(self.project_root / candidate["path"])
            if candidate_manifest.get("delivery_rendering") != "DEFERRED_TO_HANDOFF":
                raise AlphaContractError("PRD delivery rendering contract is invalid")
            source_truth_ref = candidate_manifest["review_requirements"][
                "review_basis_refs"
            ]["prd"]
            local_prd_ref = self.versioned_file_ref(
                target / "PRD.md", candidate["version"]
            )
            outputs = {
                mode: {
                    "enabled": enabled,
                    "implementation_status": (
                        "IMPLEMENTED"
                        if mode in IMPLEMENTED_HANDOFF_DELIVERY_MODES
                        else "NOT_IMPLEMENTED"
                    ),
                    "status": (
                        "PENDING"
                        if enabled
                        else (
                            "SKIPPED_BY_USER"
                            if mode in IMPLEMENTED_HANDOFF_DELIVERY_MODES
                            else "DISABLED"
                        )
                    ),
                    "output_ref": None,
                }
                for mode, enabled in normalized_delivery_options.items()
            }
            if normalized_delivery_options["LOCAL_HTML"]:
                assets = (
                    {
                        path.relative_to(target).as_posix(): path.read_bytes()
                        for path in sorted((target / "assets").rglob("*"))
                        if path.is_file()
                    }
                    if (target / "assets").is_dir()
                    else {}
                )
                html_bytes = render_self_contained_prd_html(
                    (target / "PRD.md").read_text(encoding="utf-8"), assets
                ).encode("utf-8")
                atomic_write_bytes(target / "PRD.html", html_bytes)
                outputs["LOCAL_HTML"] = {
                    **outputs["LOCAL_HTML"],
                    "status": "GENERATED",
                    "output_ref": self.versioned_file_ref(
                        target / "PRD.html", candidate["version"]
                    ),
                }
            evidence_summary = deepcopy(state["ready"]["evidence_summary"])
            evidence_summary["handoff_rendering"] = outputs["LOCAL_HTML"]["status"]
            primary_reading_ref = (
                outputs["LOCAL_HTML"]["output_ref"]
                if outputs["LOCAL_HTML"]["status"] == "GENERATED"
                else local_prd_ref
            )
            primary_reading_name = (
                "PRD.html"
                if outputs["LOCAL_HTML"]["status"] == "GENERATED"
                else "PRD.md"
            )
            option_lines = "".join(
                f"  - {mode}：{'ON' if option['enabled'] else 'OFF'} · "
                f"{option['status']}\n"
                for mode, option in outputs.items()
            )
            note = (
                "# Local Handoff\n\n"
                "本交接只包含当前精确 PRD Release Set 的本地文件。\n\n"
                f"- 默认阅读：{primary_reading_name}\n"
                "- 编辑真源：PRD.md 与 assets\n"
                "- Handoff 方式开关：\n"
                f"{option_lines}"
                f"- Contract Readiness：{evidence_summary['contract_readiness']}\n"
                f"- Agent Review：{evidence_summary['agent_review']}\n"
                f"- Writing Review：{evidence_summary['writing_review']}\n"
                f"- Handoff Rendering：{evidence_summary['handoff_rendering']}\n"
                f"- Human Reader Validation：{evidence_summary['human_reader_validation']}\n"
                f"- Product Eval Execution：{evidence_summary['product_eval_execution']}\n"
                f"- 外部发送：{evidence_summary['external_delivery']}\n"
                f"- 研发接收：{evidence_summary['engineering_received']}\n"
                f"- 工程测试：{evidence_summary['engineering_tests']}\n"
                f"- 产品效果验证：{evidence_summary['product_effect_validation']}\n"
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
            manifest = {
                "schema_version": "bpg2-alpha-local-handoff.v3",
                "run_id": run_id,
                "candidate_ref": self._candidate_ref(candidate),
                "ready_ref": deepcopy(state["ready"]),
                "prd_type": candidate_manifest["prd_type"],
                "delivery_options": deepcopy(normalized_delivery_options),
                "delivery": {
                    "source_truth_ref": source_truth_ref,
                    "selected_modes": sorted(
                        mode
                        for mode, enabled in normalized_delivery_options.items()
                        if enabled
                    ),
                    "primary_reading_ref": primary_reading_ref,
                    "outputs": outputs,
                },
                "delivery_capabilities": {
                    "implemented": sorted(IMPLEMENTED_HANDOFF_DELIVERY_MODES),
                    "not_implemented": [
                        "LOCAL_DOCUMENT",
                        "FEISHU_DOCUMENT",
                        "PROJECT_MANAGEMENT_MCP",
                    ],
                },
                "files": files,
                "local_only": True,
                "external_delivery": "NOT_RUN",
                "engineering_received": "NOT_RUN",
                "tests": "NOT_RUN",
                "product_effect_validation": "NOT_RUN",
                "evidence_summary": evidence_summary,
                "retrospective_requirements": {
                    "schema_version": "bpg2-alpha-retrospective-conformance.v1",
                    "check_ids": sorted(RETROSPECTIVE_CONFORMANCE_IDS),
                    "statuses": ["PASS", "FINDING", "NOT_APPLICABLE"],
                },
            }
            manifest_path = target / "HANDOFF_MANIFEST.json"
            atomic_write_json(manifest_path, manifest)
            state["handoff"] = {
                "status": "LOCAL_HANDOFF_COMPLETE",
                "path": target.relative_to(self.project_root).as_posix(),
                "manifest_ref": self.file_ref(manifest_path),
                "delivery_options": deepcopy(normalized_delivery_options),
                "delivery": deepcopy(manifest["delivery"]),
            }
            state["status"] = "LOCAL_HANDOFF_COMPLETE"
            state["external_delivery"] = "NOT_RUN"
            state["retrospective_status"] = "NOT_RUN"
            state["retrospective_requirements"] = deepcopy(
                manifest["retrospective_requirements"]
            )

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
        method_conformance: list[dict[str, Any]],
    ) -> dict[str, Any]:
        author_attempt_id = _nonempty(author_attempt_id, "retrospective author attempt")
        markdown = _nonempty(markdown, "retrospective")
        if not isinstance(method_conformance, list):
            raise AlphaContractError("retrospective method conformance must be a list")
        normalized_conformance: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in method_conformance:
            if not isinstance(raw, dict) or set(raw) != {"check_id", "status", "rationale"}:
                raise AlphaContractError("retrospective method conformance fields are incomplete")
            check_id = _nonempty(raw.get("check_id"), "method conformance check_id")
            if check_id not in RETROSPECTIVE_CONFORMANCE_IDS or check_id in seen:
                raise AlphaContractError("retrospective method conformance must be exact and unique")
            seen.add(check_id)
            if raw.get("status") not in {"PASS", "FINDING", "NOT_APPLICABLE"}:
                raise AlphaContractError("retrospective method conformance status is invalid")
            _nonempty(raw.get("rationale"), "method conformance rationale")
            normalized_conformance.append(deepcopy(raw))
        if seen != RETROSPECTIVE_CONFORMANCE_IDS:
            raise AlphaContractError("retrospective method conformance coverage is incomplete")
        payload = self._operation_payload(
            "record_retrospective",
            author_attempt_id=author_attempt_id,
            markdown=markdown,
            method_conformance=normalized_conformance,
        )

        def apply(state: dict[str, Any]) -> None:
            if state.get("status") != "LOCAL_HANDOFF_COMPLETE":
                raise AlphaContractError("planning retrospective follows Local Handoff")
            path = self.run_path(run_id) / "planning-retrospective.md"
            if path.exists():
                raise AlphaContractError("retrospective already exists outside idempotent replay")
            atomic_write_bytes(path, markdown.encode("utf-8"))
            has_findings = any(
                item["status"] == "FINDING" for item in normalized_conformance
            )
            state["retrospective_status"] = (
                "COMPLETED_WITH_FINDINGS" if has_findings else "COMPLETED"
            )
            state["retrospective_ref"] = self.file_ref(path)
            state["method_conformance_status"] = "FAIL" if has_findings else "PASS"
            state["method_conformance"] = normalized_conformance

        return self._mutate(
            run_id,
            expected_state_version=expected_state_version,
            operation_id=operation_id,
            payload=payload,
            mutate=apply,
        )
