"""Independent, evaluation-only Writing Reviewer runtime.

This module intentionally does not use Product Run state or Product Graph edges.
"""

from __future__ import annotations

import json
import os
import re
import stat
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from .locking import exclusive_file_lock
from .reference_catalog import ReferenceCatalog, ReferenceCatalogError
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
from .templates import TemplateRegistry, TemplateContractError
from .visual_assets import VisualAssetError, inspect_reader_visible_visual_assets
from .writing_eval_review_contract import (
    WritingEvalReviewError,
    validate_writing_eval_review,
)


class WritingEvalError(RuntimeError):
    """The evaluation-only Run is stale, ambiguous, or violates custody."""


PREPARE_SCHEMA = "writing-eval-prepare.v1"
STATE_SCHEMA = "writing-eval-state.v1"
INIT_SCHEMA = "writing-eval-init-transaction.v1"
TRANSITION_SCHEMA = "writing-eval-transition.v1"
DISPATCH_SCHEMA = "writing-eval-dispatch.v1"
CHECKPOINT_SCHEMA = "writing-eval-preregistration-checkpoint.v1"
SUITE_SCHEMA = "prd-readability-agent-suite.v0.4"
CASE_SCHEMA = "prd-readability-agent-case.v0.4"
RESULT_SCHEMA = "document-experience-reader-eval.v3.1"
NODE_ID = "writing-eval.review"
SUITE_BINDINGS = {
    "better-product-graph-prd-readability-v0.4": {
        "instruction_ref": "references/atomic-skills/prd-writing-eval-review/INSTRUCTIONS.md",
        "instruction_version": "v1",
        "profile_resource_id": "prd-writing-profile-v0.4",
        "guide_resource_id": "prd-writing-guide-v0.4",
        "review_resource_id": "prd-writing-eval-reader-review-v3.1",
    },
    "better-product-graph-prd-readability-v0.5": {
        "instruction_ref": "references/atomic-skills/prd-writing-eval-review-v3.2/INSTRUCTIONS.md",
        "instruction_version": "v3.2",
        "profile_resource_id": "prd-writing-profile-v0.5",
        "guide_resource_id": "prd-writing-guide-v0.5",
        "review_resource_id": "prd-writing-eval-reader-review-v3.2",
    },
    "better-product-graph-prd-readability-v0.6": {
        "instruction_ref": "references/atomic-skills/prd-writing-eval-review-v3.2/INSTRUCTIONS.md",
        "instruction_version": "v3.2",
        "profile_resource_id": "prd-writing-profile-v0.5",
        "guide_resource_id": "prd-writing-guide-v0.5",
        "review_resource_id": "prd-writing-eval-reader-review-v3.2",
    },
    "better-product-graph-prd-readability-v0.7": {
        "instruction_ref": "references/atomic-skills/prd-writing-eval-review-v3.2/INSTRUCTIONS.md",
        "instruction_version": "v3.2",
        "profile_resource_id": "prd-writing-profile-v0.5",
        "guide_resource_id": "prd-writing-guide-v0.5",
        "review_resource_id": "prd-writing-eval-reader-review-v3.2",
    },
    "better-product-graph-prd-readability-v0.8": {
        "instruction_ref": "references/atomic-skills/prd-writing-eval-review-v3.2/INSTRUCTIONS.md",
        "instruction_version": "v3.2",
        "profile_resource_id": "prd-writing-profile-v0.5",
        "guide_resource_id": "prd-writing-guide-v0.5",
        "review_resource_id": "prd-writing-eval-reader-review-v3.2",
    },
}
WRITING_EVAL_RESOURCE_IDS = frozenset(
    resource_id
    for bundle in SUITE_BINDINGS.values()
    for resource_id in (
        bundle["profile_resource_id"],
        bundle["guide_resource_id"],
        bundle["review_resource_id"],
    )
)
KNOWN_UNSTARTED_PREDECESSOR_HASHES = frozenset(
    {
        "sha256:17b0d92931125f25c60f61eaa92a445bad950fd048e6638521024f0641a57d89",
        "sha256:973a9b7bb1613f94a62289dbc975aca3b8208640693fbf9954163b257d31bc74",
        "sha256:848aaaa15e4e989c8822f1e0ee66a3c992b0b9483fc5eac53df23c7529bc319e",
        "sha256:1a45d58423ec38b1dcd0361523d3997a190f5cff7f62bb5e440e4fb6dff6159c",
    }
)
PREPARE_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "case_id",
        "suite_ref",
        "case_ref",
        "candidate_ref",
        "author_execution_ref",
    }
)
EXACT_REF_FIELDS = frozenset({"path", "hash", "version"})
EXECUTION_REF_FIELDS = frozenset({"kind", "id"})
SUITE_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "target_eval_schema",
        "evaluator_files_included",
        "agent_runtime_status",
        "claim_boundary",
    }
)
CASE_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "case_id",
        "candidate_ref",
        "target_eval_schema",
        "evaluator_files_included",
        "agent_runtime_status",
        "claim_boundary",
    }
)
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
V07_SUITE_ID = "better-product-graph-prd-readability-v0.7"
V07_PHASE_BUILD_VERSIONS = {
    "RC_CANDIDATE": "0.2.18-rc.4",
    "FINAL_PUBLIC_ARTIFACT": "0.2.18",
}
V08_SUITE_ID = "better-product-graph-prd-readability-v0.8"
V08_PHASE_BUILD_VERSIONS = {
    "RC_CANDIDATE": "0.2.18-rc.5",
    "FINAL_PUBLIC_ARTIFACT": "0.2.18",
}
PHASE_SUITE_BUILD_VERSIONS = {
    V07_SUITE_ID: V07_PHASE_BUILD_VERSIONS,
    V08_SUITE_ID: V08_PHASE_BUILD_VERSIONS,
}
V07_MANIFEST_BINDING_FIELDS = frozenset({"phase", "manifest_ref"})
V07_MECHANICAL_AUTHORITY_FIELDS = frozenset(
    {
        "schema_version", "evaluation_only", "authority", "suite_id", "case_id",
        "node_id", "attempt_id", "instruction_ref", "instruction_hash",
        "input_refs", "input_hashes", "preregistration_checkpoint_ref",
        "candidate_ref", "profile_ref", "guide_ref", "reviewer_resource_ref",
        "output_contract_ref", "author_execution_ref", "reviewer_execution_ref",
        "reviewer_role", "isolated_input_refs", "claim_boundary",
    }
)
FORBIDDEN_CUSTODY_PARTS = frozenset({"evaluator", "expected", "hidden-expected"})
STATE_FIELDS = frozenset(
    {
        "schema_version",
        "run_id",
        "run_type",
        "evaluation_only",
        "suite_id",
        "case_id",
        "prepare_identity_hash",
        "prepare_payload",
        "snapshot_refs",
        "state_version",
        "generation",
        "status",
        "current_node",
        "dispatch",
        "preregistration_checkpoint_ref",
        "superseded_attempts",
        "result_ref",
    }
)
V07_STATE_FIELDS = STATE_FIELDS | frozenset({"phase_manifest_binding"})
INIT_FIELDS = frozenset(
    {
        "schema_version",
        "run_id",
        "prepare_identity_hash",
        "prepare_payload",
        "attempt_id",
        "generation",
        "bindings",
    }
)
TRANSITION_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "transition_id",
        "kind",
        "run_id",
        "attempt_id",
        "base_state_hash",
        "target_state",
        "target_state_hash",
        "base_event_head",
        "target_event",
        "target_event_hash",
        "result_ref",
        "result_value",
        "snapshot_identity",
    }
)
V07_TRANSITION_FIELDS = TRANSITION_FIELDS | frozenset({"base_state"})


def _is_phase_suite(suite_id: Any) -> bool:
    return suite_id in PHASE_SUITE_BUILD_VERSIONS


def _phase_build_versions(suite_id: str) -> dict[str, str]:
    try:
        return PHASE_SUITE_BUILD_VERSIONS[suite_id]
    except KeyError as error:
        raise WritingEvalError(
            f"Writing Eval suite has no phase execution contract: {suite_id}"
        ) from error


def _phase_schema(suite_id: str, suffix: str) -> str:
    version = suite_id.rsplit("-v", 1)[-1]
    if suite_id not in PHASE_SUITE_BUILD_VERSIONS:
        raise WritingEvalError(
            f"Writing Eval suite has no phase schema contract: {suite_id}"
        )
    return f"prd-readability-v{version}-{suffix}.v1"


def _closed(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        missing = sorted(fields - set(value)) if isinstance(value, dict) else []
        extra = sorted(set(value) - fields) if isinstance(value, dict) else []
        raise WritingEvalError(
            f"{label} must be a closed object; missing={missing}, extra={extra}"
        )
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WritingEvalError(f"{label} must be non-empty text")
    return value


def _safe_id(value: Any, label: str) -> str:
    text = _text(value, label)
    if SAFE_ID.fullmatch(text) is None:
        raise WritingEvalError(f"{label} must be path-safe")
    return text


def _exact_ref(value: Any, label: str) -> dict[str, Any]:
    ref = _closed(value, EXACT_REF_FIELDS, label)
    raw_path = _text(ref.get("path"), f"{label}.path")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != raw_path:
        raise WritingEvalError(f"{label}.path must remain relative and normalized")
    digest = ref.get("hash")
    if (
        not isinstance(digest, str)
        or len(digest) != 71
        or not digest.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in digest[7:])
    ):
        raise WritingEvalError(f"{label}.hash must be an exact lowercase sha256")
    version = ref.get("version")
    if isinstance(version, bool) or (
        not isinstance(version, (str, int))
        or (isinstance(version, str) and not version.strip())
        or (isinstance(version, int) and version < 1)
    ):
        raise WritingEvalError(
            f"{label}.version must be a non-empty string or integer >= 1"
        )
    return deepcopy(ref)


def _execution_ref(value: Any, label: str, expected_kind: str) -> dict[str, str]:
    ref = _closed(value, EXECUTION_REF_FIELDS, label)
    if ref.get("kind") != expected_kind:
        raise WritingEvalError(f"{label}.kind must be {expected_kind}")
    _safe_id(ref.get("id"), f"{label}.id")
    return deepcopy(ref)


def _resolve_project_ref(
    project_root: Path, value: Any, label: str
) -> tuple[dict[str, Any], Path]:
    ref = _exact_ref(value, label)
    lowered = {part.casefold() for part in PurePosixPath(ref["path"]).parts}
    if lowered & FORBIDDEN_CUSTODY_PARTS:
        raise WritingEvalError(f"{label} crosses evaluator-only custody")
    try:
        path = assert_managed_path(project_root, project_root / ref["path"])
    except IntegrityError as error:
        raise WritingEvalError(f"{label} escapes the Agent workspace") from error
    if (
        not path.is_file()
        or path.is_symlink()
        or sha256_file(path) != ref["hash"]
    ):
        raise WritingEvalError(f"{label} must bind one exact regular Agent input")
    return ref, path


def _installed_file_ref(
    skill_root: Path, relative: str, version: str | int
) -> dict[str, Any]:
    path = (skill_root / relative).resolve()
    try:
        path.relative_to(skill_root)
    except ValueError as error:
        raise WritingEvalError(f"installed ref escapes Skill root: {relative}") from error
    if not path.is_file() or path.is_symlink():
        raise WritingEvalError(f"installed ref is missing: {relative}")
    return {"path": relative, "hash": sha256_file(path), "version": version}


def _suite_binding(suite_id: str) -> dict[str, str]:
    try:
        return SUITE_BINDINGS[suite_id]
    except KeyError as error:
        raise WritingEvalError(f"unsupported Writing Eval suite: {suite_id}") from error


def _installed_bindings(
    project_root: Path, skill_root: Path, suite_id: str
) -> dict[str, Any]:
    bundle = _suite_binding(suite_id)
    try:
        catalog = ReferenceCatalog(skill_root)
        resources = {
            item["resource_id"]: item for item in catalog.writing_eval_resources()
        }
        if set(resources) != WRITING_EVAL_RESOURCE_IDS:
            raise WritingEvalError("Writing Eval installed resource set is not exact")
        selection = TemplateRegistry(
            skill_root / "references" / "templates"
            if (skill_root / "references" / "templates").is_dir()
            else skill_root / "templates"
        ).resolve(project_root)
    except (ReferenceCatalogError, TemplateContractError) as error:
        raise WritingEvalError(f"Writing Eval installed bindings are invalid: {error}") from error

    def ref(resource_id: str) -> dict[str, Any]:
        return {
            field: resources[resource_id][field]
            for field in ("path", "hash", "version")
        }

    instruction_ref = _installed_file_ref(
        skill_root,
        bundle["instruction_ref"],
        bundle["instruction_version"],
    )
    output_contract_ref = {
        "path": selection.output_contract_reference_path,
        "hash": selection.output_contract_sha256,
        "version": selection.output_contract_version,
    }
    output_path = (
        skill_root / output_contract_ref["path"]
        if output_contract_ref["path"].startswith("references/")
        else project_root / output_contract_ref["path"]
    )
    if (
        not output_path.is_file()
        or output_path.is_symlink()
        or sha256_file(output_path) != output_contract_ref["hash"]
    ):
        raise WritingEvalError("Writing Eval Output Contract is stale")
    plugin_root = skill_root.parents[1]
    manifest = plugin_root / "build-manifest.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise WritingEvalError("Writing Eval requires an exact installed build manifest")
    installed_build_ref = {
        "path": "build-manifest.json",
        "hash": sha256_file(manifest),
        "version": read_json(manifest).get("plugin", {}).get("version"),
    }
    _exact_ref(installed_build_ref, "installed_build_ref")
    return {
        "instruction_ref": instruction_ref,
        "profile_ref": ref(bundle["profile_resource_id"]),
        "guide_ref": ref(bundle["guide_resource_id"]),
        "reviewer_resource_ref": ref(bundle["review_resource_id"]),
        "output_contract_ref": output_contract_ref,
        "installed_build_ref": installed_build_ref,
    }


def _write_once_json(path: Path, value: dict[str, Any], label: str) -> None:
    expected = canonical_json_bytes(value) + b"\n"
    if path.exists():
        if not path.is_file() or path.is_symlink() or path.read_bytes() != expected:
            raise WritingEvalError(f"{label} identity conflict")
        return
    atomic_write_json(path, value)


def _write_once_bytes(path: Path, value: bytes, label: str) -> None:
    if path.exists():
        if not path.is_file() or path.is_symlink() or path.read_bytes() != value:
            raise WritingEvalError(f"{label} identity conflict")
        return
    atomic_write_bytes(path, value)


def _validate_prepare_payload(
    project_root: Path, payload: Any
) -> tuple[dict[str, Any], dict[str, Path]]:
    value = _closed(payload, PREPARE_FIELDS, "writing_eval_prepare")
    if value.get("schema_version") != PREPARE_SCHEMA:
        raise WritingEvalError(f"schema_version must be {PREPARE_SCHEMA}")
    suite_id = _safe_id(value.get("suite_id"), "suite_id")
    case_id = _safe_id(value.get("case_id"), "case_id")
    author = _execution_ref(
        value.get("author_execution_ref"),
        "author_execution_ref",
        "HOST_AGENT_ATTEMPT",
    )
    refs: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for field in ("suite_ref", "case_ref", "candidate_ref"):
        refs[field], paths[field] = _resolve_project_ref(
            project_root, value.get(field), field
        )
    if len({refs[field]["path"] for field in refs}) != 3:
        raise WritingEvalError("suite, case, and Candidate refs must be distinct")
    if paths["candidate_ref"].suffix.casefold() != ".md":
        raise WritingEvalError("candidate_ref must identify Markdown")
    try:
        paths["candidate_ref"].read_text(encoding="utf-8")
        suite = read_json(paths["suite_ref"])
        case = read_json(paths["case_ref"])
    except (OSError, UnicodeError, IntegrityError) as error:
        raise WritingEvalError("Writing Eval Agent inputs are unreadable") from error
    _closed(suite, SUITE_FIELDS, "agent_suite")
    _closed(case, CASE_FIELDS, "agent_case")
    for manifest, schema, label in (
        (suite, SUITE_SCHEMA, "agent_suite"),
        (case, CASE_SCHEMA, "agent_case"),
    ):
        if (
            manifest.get("schema_version") != schema
            or manifest.get("suite_id") != suite_id
            or manifest.get("target_eval_schema") != RESULT_SCHEMA
            or manifest.get("evaluator_files_included") is not False
            or manifest.get("agent_runtime_status") != "NOT_RUN"
        ):
            raise WritingEvalError(f"{label} identity or custody is invalid")
    if case.get("case_id") != case_id:
        raise WritingEvalError("agent_case case_id differs from payload")
    case_candidate = _exact_ref(case.get("candidate_ref"), "agent_case.candidate_ref")
    case_candidate_path = (paths["case_ref"].parent / case_candidate["path"]).resolve()
    if (
        case_candidate_path != paths["candidate_ref"].resolve()
        or case_candidate["hash"] != refs["candidate_ref"]["hash"]
        or case_candidate["version"] != refs["candidate_ref"]["version"]
    ):
        raise WritingEvalError("agent_case does not bind the exact Candidate")
    normalized = {
        "schema_version": PREPARE_SCHEMA,
        "suite_id": suite_id,
        "case_id": case_id,
        **refs,
        "author_execution_ref": author,
    }
    return normalized, paths


class WritingEvalRuntime:
    """One local Writer-Eval state machine with no Product Graph authority."""

    def __init__(self, project_root: Path, skill_root: Path):
        self.project_root = project_root.resolve()
        self.skill_root = skill_root.resolve()

    def run_path(self, run_id: str) -> Path:
        _safe_id(run_id, "run_id")
        return assert_managed_path(
            self.project_root,
            self.project_root / ".better-product-graph" / "writing-evals" / run_id,
        )

    def _state_path(self, run_id: str) -> Path:
        return self.run_path(run_id) / "state.json"

    def _events_path(self, run_id: str) -> Path:
        return self.run_path(run_id) / "events.jsonl"

    def _lock_path(self, run_id: str) -> Path:
        return assert_managed_path(
            self.project_root,
            self.project_root
            / ".better-product-graph"
            / "locks"
            / f"writing-eval-{run_id}.lock",
        )

    def _project_lock_path(self) -> Path:
        return assert_managed_path(
            self.project_root,
            self.project_root
            / ".better-product-graph"
            / "locks"
            / "writing-eval-project.lock",
        )

    @contextmanager
    def _operation_locks(self, run_id: str, *, create: bool = True):
        with exclusive_file_lock(self._project_lock_path(), create=create):
            with exclusive_file_lock(self._lock_path(run_id), create=create):
                yield

    def _initializing_path(self, run_id: str) -> Path:
        _safe_id(run_id, "run_id")
        return assert_managed_path(
            self.project_root,
            self.project_root
            / ".better-product-graph"
            / "writing-evals"
            / f".initializing-{run_id}",
        )

    @staticmethod
    def _inject(failpoint: str | None, boundary: str) -> None:
        if failpoint == boundary:
            raise WritingEvalError(f"injected crash at {boundary}")

    @staticmethod
    def _object_hash(value: dict[str, Any]) -> str:
        return sha256_bytes(canonical_json_bytes(value))

    def _transaction_path(self, run_id: str, transition_id: str) -> Path:
        _safe_id(transition_id, "transition_id")
        return assert_managed_path(
            self.project_root,
            self.run_path(run_id) / "transactions" / f"{transition_id}.json",
        )

    def _compose_target_event(
        self,
        *,
        transition_id: str,
        previous_hash: str | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "schema_version": "audit-event.v1",
            "event_id": f"writing-eval-transition-{transition_id}",
            "recorded_at": datetime.now(UTC).isoformat(),
            "previous_hash": previous_hash,
            **payload,
        }
        event["event_hash"] = sha256_bytes(
            canonical_json_bytes(
                {key: value for key, value in event.items() if key != "event_hash"}
            )
        )
        return event

    def _validate_transition_journal(
        self, path: Path, journal: dict[str, Any]
    ) -> None:
        target_event = journal.get("target_event")
        target_state_value = journal.get("target_state")
        v07_transition = (
            isinstance(target_state_value, dict)
            and _is_phase_suite(target_state_value.get("suite_id"))
        )
        recomputed_event_hash = (
            sha256_bytes(
                canonical_json_bytes(
                    {
                        key: value
                        for key, value in target_event.items()
                        if key != "event_hash"
                    }
                )
            )
            if isinstance(target_event, dict)
            else None
        )
        if (
            not path.is_file()
            or path.is_symlink()
            or set(journal)
            != (
                V07_TRANSITION_FIELDS
                if v07_transition
                else TRANSITION_FIELDS
            )
            or journal.get("schema_version") != TRANSITION_SCHEMA
            or journal.get("status") not in {"PREPARED", "COMMITTED"}
            or journal.get("kind")
            not in {"dispatch", "revoke", "bind_manifest", "complete"}
            or journal.get("run_id") is None
            or journal.get("attempt_id") is None
            or not isinstance(journal.get("target_state"), dict)
            or self._object_hash(journal["target_state"])
            != journal.get("target_state_hash")
            or not isinstance(journal.get("target_event"), dict)
            or journal["target_event"].get("event_hash")
            != journal.get("target_event_hash")
            or recomputed_event_hash != journal.get("target_event_hash")
            or journal["target_event"].get("previous_hash")
            != journal.get("base_event_head")
            or journal["target_event"].get("run_id") != journal.get("run_id")
            or (
                journal.get("kind") != "revoke"
                and journal["target_event"].get("attempt_id")
                != journal.get("attempt_id")
            )
            or (
                journal.get("kind") == "revoke"
                and journal["target_event"].get("successor_attempt_id")
                != journal.get("attempt_id")
            )
            or journal["target_state"].get("run_id") != journal.get("run_id")
            or journal["target_state"].get("dispatch", {}).get("attempt_id")
            != journal.get("attempt_id")
        ):
            raise WritingEvalError("Writing Eval transition journal is invalid")
        if v07_transition and (
            not isinstance(journal.get("base_state"), dict)
            or self._object_hash(journal["base_state"])
            != journal.get("base_state_hash")
        ):
            raise WritingEvalError(
                "Writing Eval v0.7 transition base state authority is invalid"
            )
        if v07_transition:
            self._validate_v07_transition_semantics(journal)
        _safe_id(journal["transition_id"], "transition_id")
        _safe_id(journal["run_id"], "run_id")
        _safe_id(journal["attempt_id"], "attempt_id")
        if journal["kind"] == "complete":
            if (
                not isinstance(journal["result_value"], dict)
                or not isinstance(journal["result_ref"], dict)
                or journal["result_ref"]
                != journal["target_state"].get("result_ref")
                or journal["target_event"].get("result_ref")
                != journal["result_ref"]
                or sha256_bytes(canonical_json_bytes(journal["result_value"]) + b"\n")
                != journal["result_ref"].get("hash")
            ):
                raise WritingEvalError(
                    "Writing Eval completion transition result binding is invalid"
                )
        elif journal["result_ref"] is not None or journal["result_value"] is not None:
            raise WritingEvalError(
                "Writing Eval non-completion transition cannot carry a result"
            )
        if path != self._transaction_path(
            journal["run_id"], journal["transition_id"]
        ):
            raise WritingEvalError("Writing Eval transition journal path is invalid")

    def _validate_v07_transition_semantics(self, journal: dict[str, Any]) -> None:
        """Bind each v0.7 journal kind to one exact Controller state transition."""

        kind = journal["kind"]
        base = journal["base_state"]
        target = journal["target_state"]
        event = journal["target_event"]
        run_id = journal["run_id"]
        attempt_id = journal["attempt_id"]
        base_dispatch = base.get("dispatch")
        target_dispatch = target.get("dispatch")
        base_attempt = (
            base_dispatch.get("attempt_id")
            if isinstance(base_dispatch, dict)
            else None
        )
        target_attempt = (
            target_dispatch.get("attempt_id")
            if isinstance(target_dispatch, dict)
            else None
        )
        common_event_fields = {
            "schema_version",
            "event_id",
            "recorded_at",
            "previous_hash",
            "event_type",
            "actor",
            "run_id",
            "attempt_id",
            "event_hash",
        }
        event_fields = {
            "dispatch": common_event_fields,
            "revoke": common_event_fields
            | {
                "successor_attempt_id",
                "predecessor_instruction_hash",
                "successor_instruction_hash",
            },
            "bind_manifest": common_event_fields | {"phase", "manifest_ref"},
            "complete": common_event_fields
            | {"result_ref", "result", "human_reader_observation"},
        }
        event_types = {
            "dispatch": "WRITING_EVAL_REVIEW_DISPATCHED",
            "revoke": "WRITING_EVAL_UNSTARTED_DISPATCH_REVOKED",
            "bind_manifest": "WRITING_EVAL_PHASE_MANIFEST_BOUND",
            "complete": "WRITING_EVAL_COMPLETED",
        }
        if (
            set(base) != V07_STATE_FIELDS
            or set(target) != V07_STATE_FIELDS
            or set(event) != event_fields[kind]
            or not isinstance(base_dispatch, dict)
            or not isinstance(target_dispatch, dict)
            or base.get("run_id") != run_id
            or target.get("run_id") != run_id
            or event.get("run_id") != run_id
            or event.get("schema_version") != "audit-event.v1"
            or event.get("event_id")
            != f"writing-eval-transition-{journal['transition_id']}"
            or event.get("event_type") != event_types[kind]
            or event.get("actor") != "writing-eval-controller"
            or not isinstance(base.get("state_version"), int)
            or target.get("state_version") != base.get("state_version") + 1
            or journal.get("transition_id")
            != f"{kind}-{attempt_id}-v{target.get('state_version')}"
        ):
            raise WritingEvalError(
                "Writing Eval v0.7 transition kind semantics are invalid"
            )

        if kind == "revoke":
            unchanged = V07_STATE_FIELDS - {
                "state_version",
                "generation",
                "dispatch",
                "preregistration_checkpoint_ref",
                "superseded_attempts",
            }
            expected_superseded = list(base.get("superseded_attempts", [])) + [
                {
                    "attempt_id": base_attempt,
                    "instruction_hash": base_dispatch.get("instruction_hash"),
                    "status": "REVOKED_UNSTARTED",
                }
            ]
            valid = (
                attempt_id == target_attempt
                and event.get("attempt_id") == base_attempt
                and event.get("successor_attempt_id") == target_attempt
                and event.get("predecessor_instruction_hash")
                == base_dispatch.get("instruction_hash")
                and event.get("successor_instruction_hash")
                == target_dispatch.get("instruction_hash")
                and base_dispatch.get("status") in {"PLANNED", "DISPATCHED"}
                and target_dispatch.get("status") == "PLANNED"
                and target.get("generation") == base.get("generation") + 1
                and target.get("superseded_attempts") == expected_superseded
                and all(target.get(field) == base.get(field) for field in unchanged)
            )
        else:
            valid = (
                attempt_id == base_attempt == target_attempt
                and event.get("attempt_id") == attempt_id
            )
            expected = deepcopy(base)
            expected["state_version"] += 1
            if kind == "dispatch":
                expected["dispatch"]["status"] = "DISPATCHED"
                valid = valid and base_dispatch.get("status") == "PLANNED"
            elif kind == "bind_manifest":
                binding = {
                    "phase": event.get("phase"),
                    "manifest_ref": event.get("manifest_ref"),
                }
                expected["phase_manifest_binding"] = binding
                valid = (
                    valid
                    and base.get("phase_manifest_binding") is None
                    and target.get("phase_manifest_binding") == binding
                )
            else:
                expected["status"] = "COMPLETED"
                expected["dispatch"]["status"] = "COMPLETED"
                expected["result_ref"] = journal.get("result_ref")
                valid = (
                    valid
                    and base.get("status") == "ACTIVE"
                    and base_dispatch.get("status") == "DISPATCHED"
                    and base.get("result_ref") is None
                    and event.get("result_ref") == journal.get("result_ref")
                    and event.get("result")
                    == (
                        journal.get("result_value", {}).get("result")
                        if isinstance(journal.get("result_value"), dict)
                        else None
                    )
                    and event.get("human_reader_observation") == "NOT_RUN"
                )
            valid = valid and target == expected
        if not valid:
            raise WritingEvalError(
                "Writing Eval v0.7 transition state delta is invalid"
            )

    def _verify_snapshot_identity(self, identity: Any) -> None:
        if identity is None:
            return
        if not isinstance(identity, list) or not identity:
            raise WritingEvalError("Writing Eval snapshot custody identity is invalid")
        for index, item in enumerate(identity):
            if not isinstance(item, dict) or set(item) != {
                "path",
                "hash",
                "device",
                "inode",
                "size",
                "mtime_ns",
            }:
                raise WritingEvalError(
                    f"Writing Eval snapshot custody item {index} is invalid"
                )
            ref = {
                "path": item["path"],
                "hash": item["hash"],
                "version": 1,
            }
            _exact_ref(ref, f"snapshot_identity[{index}]")
            path = assert_managed_path(
                self.project_root, self.project_root / item["path"]
            )
            try:
                current = os.lstat(path)
            except OSError as error:
                raise WritingEvalError("Writing Eval snapshot custody file is missing") from error
            if (
                not stat.S_ISREG(current.st_mode)
                or current.st_dev != item["device"]
                or current.st_ino != item["inode"]
                or current.st_size != item["size"]
                or current.st_mtime_ns != item["mtime_ns"]
                or sha256_file(path) != item["hash"]
            ):
                raise WritingEvalError(
                    "Writing Eval snapshot custody changed during transition"
                )

    @contextmanager
    def _open_snapshot_custody(self, state: dict[str, Any]):
        snapshot_refs = state["snapshot_refs"]
        refs = [
            snapshot_refs["suite_ref"],
            snapshot_refs["case_ref"],
            snapshot_refs["candidate_ref"],
        ]
        for pair in snapshot_refs["reader_visible_visual_pairs"]:
            refs.extend((pair["svg_ref"], pair["png_ref"]))
        handles: list[dict[str, Any]] = []
        seen: set[str] = set()
        try:
            for ref in refs:
                checked = _exact_ref(ref, "snapshot_ref")
                if checked["path"] in seen:
                    continue
                seen.add(checked["path"])
                path = assert_managed_path(
                    self.project_root, self.project_root / checked["path"]
                )
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                try:
                    descriptor = os.open(path, flags)
                except OSError as error:
                    raise WritingEvalError(
                        "Writing Eval snapshot cannot be opened safely"
                    ) from error
                before = os.fstat(descriptor)
                if not stat.S_ISREG(before.st_mode):
                    os.close(descriptor)
                    raise WritingEvalError("Writing Eval snapshot is not a regular file")
                chunks: list[bytes] = []
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                value = b"".join(chunks)
                after = os.fstat(descriptor)
                fingerprint = (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                )
                if (
                    fingerprint
                    != (
                        after.st_dev,
                        after.st_ino,
                        after.st_size,
                        after.st_mtime_ns,
                    )
                    or sha256_bytes(value) != checked["hash"]
                ):
                    os.close(descriptor)
                    raise WritingEvalError(
                        "Writing Eval snapshot changed while opening custody"
                    )
                handles.append(
                    {
                        "path": path,
                        "descriptor": descriptor,
                        "bytes": value,
                        "identity": {
                            "path": checked["path"],
                            "hash": checked["hash"],
                            "device": before.st_dev,
                            "inode": before.st_ino,
                            "size": before.st_size,
                            "mtime_ns": before.st_mtime_ns,
                        },
                    }
                )

            def verify() -> None:
                for handle in handles:
                    descriptor = handle["descriptor"]
                    expected = handle["identity"]
                    try:
                        current = os.fstat(descriptor)
                        path_stat = os.lstat(handle["path"])
                    except OSError as error:
                        raise WritingEvalError(
                            "Writing Eval snapshot custody path disappeared"
                        ) from error
                    if (
                        not stat.S_ISREG(current.st_mode)
                        or not stat.S_ISREG(path_stat.st_mode)
                        or current.st_dev != expected["device"]
                        or current.st_ino != expected["inode"]
                        or current.st_size != expected["size"]
                        or current.st_mtime_ns != expected["mtime_ns"]
                        or path_stat.st_dev != expected["device"]
                        or path_stat.st_ino != expected["inode"]
                        or path_stat.st_size != expected["size"]
                        or path_stat.st_mtime_ns != expected["mtime_ns"]
                    ):
                        raise WritingEvalError(
                            "Writing Eval snapshot custody changed during review"
                        )
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    chunks: list[bytes] = []
                    while True:
                        chunk = os.read(descriptor, 1024 * 1024)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    if sha256_bytes(b"".join(chunks)) != expected["hash"]:
                        raise WritingEvalError(
                            "Writing Eval snapshot bytes changed during review"
                        )

            candidate_path = snapshot_refs["candidate_ref"]["path"]
            candidate = next(
                handle["bytes"]
                for handle in handles
                if handle["identity"]["path"] == candidate_path
            )
            yield candidate, [handle["identity"] for handle in handles], verify
        finally:
            for handle in handles:
                try:
                    os.close(handle["descriptor"])
                except OSError:
                    pass

    def _transition_events(self, run_id: str) -> list[dict[str, Any]]:
        try:
            return verify_event_chain(self._events_path(run_id))
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval event chain is invalid") from error

    def _apply_transition(
        self,
        path: Path,
        journal: dict[str, Any],
        *,
        failpoint: str | None = None,
    ) -> None:
        self._validate_transition_journal(path, journal)
        if journal["status"] == "COMMITTED":
            return
        state_path = self._state_path(journal["run_id"])
        try:
            current_state = read_json(state_path)
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval transition base state is invalid") from error
        current_hash = self._object_hash(current_state)
        if current_hash not in {
            journal["base_state_hash"],
            journal["target_state_hash"],
        }:
            raise WritingEvalError("Writing Eval transition state prefix is ambiguous")
        events = self._transition_events(journal["run_id"])
        current_head = events[-1]["event_hash"] if events else None
        if current_head not in {
            journal["base_event_head"],
            journal["target_event_hash"],
        }:
            raise WritingEvalError("Writing Eval transition event prefix is ambiguous")
        self._verify_snapshot_identity(journal["snapshot_identity"])
        self._inject(failpoint, f"{journal['kind']}.after_journal_prepared")

        if journal["result_value"] is not None:
            result_ref = _exact_ref(journal["result_ref"], "result_ref")
            result_path = assert_managed_path(
                self.project_root, self.project_root / result_ref["path"]
            )
            _write_once_json(
                result_path,
                journal["result_value"],
                "Writing Eval transition result",
            )
            if sha256_file(result_path) != result_ref["hash"]:
                raise WritingEvalError("Writing Eval transition result hash is stale")
            self._verify_snapshot_identity(journal["snapshot_identity"])
            self._inject(failpoint, "complete.after_result")

        state_first = failpoint == f"{journal['kind']}.after_state_before_event"
        if state_first and current_hash == journal["base_state_hash"]:
            atomic_write_json(state_path, journal["target_state"])
            current_hash = journal["target_state_hash"]
            self._verify_snapshot_identity(journal["snapshot_identity"])
            self._inject(failpoint, f"{journal['kind']}.after_state_before_event")
        if current_head == journal["base_event_head"]:
            appended = append_event(
                self._events_path(journal["run_id"]), journal["target_event"]
            )
            if appended != journal["target_event"]:
                raise WritingEvalError("Writing Eval transition event identity conflict")
            current_head = journal["target_event_hash"]
            self._verify_snapshot_identity(journal["snapshot_identity"])
            self._inject(failpoint, f"{journal['kind']}.after_event_before_state")
        if current_hash == journal["base_state_hash"]:
            atomic_write_json(state_path, journal["target_state"])
            current_hash = journal["target_state_hash"]
        self._verify_snapshot_identity(journal["snapshot_identity"])
        self._inject(failpoint, f"{journal['kind']}.after_state")
        committed = {**journal, "status": "COMMITTED"}
        atomic_write_json(path, committed)

    def _recover_transitions(self, run_id: str) -> None:
        root = self.run_path(run_id) / "transactions"
        if not root.exists():
            return
        if not root.is_dir() or root.is_symlink():
            raise WritingEvalError("Writing Eval transition directory is unsafe")
        prepared: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(root.glob("*.json")):
            if not path.is_file() or path.is_symlink():
                raise WritingEvalError("Writing Eval transition journal is unsafe")
            try:
                journal = read_json(path)
            except IntegrityError as error:
                raise WritingEvalError("Writing Eval transition journal is unreadable") from error
            self._validate_transition_journal(path, journal)
            if journal["status"] == "PREPARED":
                prepared.append((path, journal))
            elif journal["snapshot_identity"] is not None:
                self._verify_snapshot_identity(journal["snapshot_identity"])
        if len(prepared) > 1:
            raise WritingEvalError("Writing Eval has multiple pending transitions")
        if prepared:
            self._apply_transition(*prepared[0])

    def _commit_transition(
        self,
        *,
        kind: str,
        base_state: dict[str, Any],
        target_state: dict[str, Any],
        event_payload: dict[str, Any],
        result_ref: dict[str, Any] | None = None,
        result_value: dict[str, Any] | None = None,
        snapshot_identity: list[dict[str, Any]] | None = None,
        failpoint: str | None = None,
    ) -> None:
        run_id = base_state["run_id"]
        attempt_id = target_state["dispatch"]["attempt_id"]
        transition_id = f"{kind}-{attempt_id}-v{target_state['state_version']}"
        path = self._transaction_path(run_id, transition_id)
        events = self._transition_events(run_id)
        base_event_head = events[-1]["event_hash"] if events else None
        target_event = self._compose_target_event(
            transition_id=transition_id,
            previous_hash=base_event_head,
            payload=event_payload,
        )
        journal = {
            "schema_version": TRANSITION_SCHEMA,
            "status": "PREPARED",
            "transition_id": transition_id,
            "kind": kind,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "base_state_hash": self._object_hash(base_state),
            "target_state": target_state,
            "target_state_hash": self._object_hash(target_state),
            "base_event_head": base_event_head,
            "target_event": target_event,
            "target_event_hash": target_event["event_hash"],
            "result_ref": result_ref,
            "result_value": result_value,
            "snapshot_identity": snapshot_identity,
        }
        if _is_phase_suite(base_state.get("suite_id")):
            journal["base_state"] = deepcopy(base_state)
        _write_once_json(path, journal, "Writing Eval transition journal")
        self._apply_transition(path, journal, failpoint=failpoint)

    def _snapshot_one(
        self,
        *,
        stage_root: Path,
        final_root: Path,
        source_ref: dict[str, Any],
        label: str,
    ) -> dict[str, Any]:
        source, source_path = _resolve_project_ref(
            self.project_root, source_ref, f"{label}.source_ref"
        )
        try:
            value = source_path.read_bytes()
        except OSError as error:
            raise WritingEvalError(f"{label} source cannot be snapshotted") from error
        if sha256_bytes(value) != source["hash"]:
            raise WritingEvalError(f"{label} source changed during snapshot")
        relative = PurePosixPath(source["path"])
        try:
            stage_path = assert_managed_path(
                self.project_root, stage_root / "inputs" / relative
            )
        except IntegrityError as error:
            raise WritingEvalError(f"{label} snapshot path is unsafe") from error
        final_path = final_root / "inputs" / relative
        _write_once_bytes(stage_path, value, f"{label} snapshot")
        if (
            not stage_path.is_file()
            or stage_path.is_symlink()
            or sha256_file(stage_path) != source["hash"]
        ):
            raise WritingEvalError(f"{label} snapshot is not exact regular bytes")
        return {
            "path": final_path.relative_to(self.project_root).as_posix(),
            "hash": source["hash"],
            "version": source["version"],
        }

    def _snapshot_inputs(
        self,
        *,
        stage_root: Path,
        final_root: Path,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            source_visual_pairs = inspect_reader_visible_visual_assets(
                self.project_root,
                self.project_root / payload["candidate_ref"]["path"],
            )
        except VisualAssetError as error:
            raise WritingEvalError(f"Writing Eval Candidate visuals are unsafe: {error}") from error
        snapshot_refs = {
            field: self._snapshot_one(
                stage_root=stage_root,
                final_root=final_root,
                source_ref=payload[field],
                label=field,
            )
            for field in ("suite_ref", "case_ref", "candidate_ref")
        }
        snapshot_pairs: list[dict[str, Any]] = []
        for pair_index, pair in enumerate(source_visual_pairs):
            snapshot_pair: dict[str, Any] = {}
            for kind in ("svg_ref", "png_ref"):
                snapshot_pair[kind] = self._snapshot_one(
                    stage_root=stage_root,
                    final_root=final_root,
                    source_ref=pair[kind],
                    label=f"visual_pairs[{pair_index}].{kind}",
                )
            snapshot_pairs.append(snapshot_pair)
        snapshot_refs["reader_visible_visual_pairs"] = snapshot_pairs
        return snapshot_refs

    def read_state(self, run_id: str) -> dict[str, Any]:
        with self._operation_locks(run_id):
            return self._read_state_locked(run_id)

    def probe_durable_run(self, run_id: str) -> str:
        """Classify durable Run presence without locks, recovery, or filesystem writes."""

        try:
            run_root = self.run_path(run_id)
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval durable Run path is unsafe") from error
        if not run_root.exists():
            return "NOT_RUN"
        if run_root.is_symlink() or not run_root.is_dir():
            raise WritingEvalError("Writing Eval durable Run path is unsafe")
        return "STARTED_OR_INVALID"

    def read_completed_evidence(self, run_id: str) -> dict[str, Any]:
        """Return Controller-verified completion evidence for evaluator scoring.

        This is a strictly non-mutating read path over existing Writing Eval
        authority. It reuses canonical event/transaction checks, installed binding
        checks, checkpoint validation, snapshot custody, and the closed v3.1 result
        validator. It does not recover transitions or accept caller-authored claims.
        """

        with self._operation_locks(run_id, create=False):
            state = self._read_state_locked(run_id, recover_transitions=False)
            bindings = _installed_bindings(
                self.project_root, self.skill_root, state["suite_id"]
            )
            if self._validate_active_bindings(state, bindings) != "EXACT":
                raise WritingEvalError(
                    "Writing Eval completed evidence installed bindings are not exact"
                )
            if (
                state["dispatch"]["writing_eval_context"].get(
                    "installed_build_ref"
                )
                != bindings["installed_build_ref"]
            ):
                raise WritingEvalError(
                    "Writing Eval completed evidence installed build is stale"
                )
            if (
                state.get("status") != "COMPLETED"
                or state.get("dispatch", {}).get("status") != "COMPLETED"
            ):
                raise WritingEvalError(
                    "Writing Eval completed evidence requires COMPLETED state"
                )
            self._validate_v07_completed_provenance(state)
            checkpoint = self._validate_checkpoint(state)
            dispatch = deepcopy(state["dispatch"])
            dispatch.pop("status", None)
            with self._open_snapshot_custody(state) as (
                candidate_bytes,
                _snapshot_identity,
                verify_snapshot,
            ):
                result = self._validate_result_file(
                    state, expected_ref=state["result_ref"]
                )
                try:
                    validated = validate_writing_eval_review(
                        self.project_root,
                        result,
                        dispatch=dispatch,
                        checkpoint_ref=state["preregistration_checkpoint_ref"],
                        expected_visual_pairs=dispatch["writing_eval_context"][
                            "reader_visible_visual_pairs"
                        ],
                        candidate_bytes=candidate_bytes,
                    )
                except (WritingEvalReviewError, IntegrityError) as error:
                    raise WritingEvalError(
                        f"Writing Eval completed evidence rejected: {error}"
                    ) from error
                verify_snapshot()

            transactions_root = self.run_path(run_id) / "transactions"
            completion_transactions: list[tuple[Path, dict[str, Any]]] = []
            if not transactions_root.is_dir() or transactions_root.is_symlink():
                raise WritingEvalError(
                    "Writing Eval completion transaction authority is missing or unsafe"
                )
            for path in sorted(transactions_root.glob("*.json")):
                if path.is_symlink() or not path.is_file():
                    raise WritingEvalError(
                        "Writing Eval completion transaction authority is unsafe"
                    )
                try:
                    transaction = read_json(path)
                except IntegrityError as error:
                    raise WritingEvalError(
                        "Writing Eval completion transaction authority is unreadable"
                    ) from error
                self._validate_transition_journal(path, transaction)
                if (
                    transaction.get("kind") == "complete"
                    and transaction.get("attempt_id")
                    == state["dispatch"]["attempt_id"]
                ):
                    completion_transactions.append((path, transaction))
            if len(completion_transactions) != 1:
                raise WritingEvalError(
                    "Writing Eval completion requires one exact Controller transaction"
                )
            transaction_path, transaction = completion_transactions[0]
            if (
                transaction.get("status") != "COMMITTED"
                or transaction.get("target_state") != state
                or transaction.get("result_ref") != state["result_ref"]
                or transaction.get("result_value") != validated
            ):
                raise WritingEvalError(
                    "Writing Eval completion transaction conflicts with durable state"
                )

            def exact_path_ref(path: Path, version: str | int = 1) -> dict[str, Any]:
                if path.is_symlink() or not path.is_file():
                    raise WritingEvalError(
                        "Writing Eval Controller evidence ref is missing or unsafe"
                    )
                return {
                    "path": path.relative_to(self.project_root).as_posix(),
                    "hash": sha256_file(path),
                    "version": version,
                }

            checkpoint_ref = state["preregistration_checkpoint_ref"]
            dispatch_ref = checkpoint["refs"]["dispatch_ref"]
            controller_refs = {
                "state_ref": exact_path_ref(self._state_path(run_id), state["state_version"]),
                "result_ref": deepcopy(state["result_ref"]),
                "events_ref": exact_path_ref(self._events_path(run_id)),
                "transaction_ref": exact_path_ref(transaction_path),
                "dispatch_ref": deepcopy(dispatch_ref),
                "checkpoint_ref": deepcopy(checkpoint_ref),
            }
            return {
                "schema_version": "writing-eval-controller-evidence.v1",
                "run_id": run_id,
                "suite_id": state["suite_id"],
                "case_id": state["case_id"],
                "attempt_id": state["dispatch"]["attempt_id"],
                "reviewer_execution_ref": deepcopy(
                    validated["reviewer_execution_ref"]
                ),
                "installed_build_ref": deepcopy(bindings["installed_build_ref"]),
                "controller_refs": controller_refs,
                "dispatch": dispatch,
                "preregistration_checkpoint_ref": deepcopy(checkpoint_ref),
                "candidate_bytes": candidate_bytes,
                "reader_visible_visual_pairs": deepcopy(
                    dispatch["writing_eval_context"]["reader_visible_visual_pairs"]
                ),
                "result": validated,
                "evaluation_only": True,
                "product_authority": "NONE",
            }

    def _validate_v07_completed_provenance(self, state: dict[str, Any]) -> None:
        """Verify every Controller transition from v0.7 preparation to completion."""

        if not _is_phase_suite(state.get("suite_id")):
            return
        suite_id = state["suite_id"]
        run_id = state["run_id"]
        run_root = self.run_path(run_id)
        init_path = run_root / "init-transaction.json"
        if init_path.is_symlink() or not init_path.is_file():
            raise WritingEvalError("Writing Eval v0.7 preparation authority is missing")
        try:
            init = read_json(init_path)
        except IntegrityError as error:
            raise WritingEvalError(
                "Writing Eval v0.7 preparation authority is invalid"
            ) from error
        events = self._transition_events(run_id)
        prepare_event_fields = {
            "schema_version", "event_id", "recorded_at", "previous_hash",
            "event_type", "actor", "run_id", "suite_id", "case_id",
            "prepare_identity_hash", "snapshot_refs_hash", "attempt_id",
            "event_hash",
        }
        if (
            set(init) != INIT_FIELDS
            or init.get("schema_version") != INIT_SCHEMA
            or init.get("run_id") != run_id
            or init.get("prepare_payload") != state.get("prepare_payload")
            or init.get("prepare_identity_hash")
            != sha256_bytes(canonical_json_bytes(init.get("prepare_payload")))
            or init.get("generation") != 1
            or not events
            or set(events[0]) != prepare_event_fields
            or events[0].get("schema_version") != "audit-event.v1"
            or events[0].get("event_type") != "WRITING_EVAL_PREPARED"
            or events[0].get("actor") != "writing-eval-controller"
            or events[0].get("run_id") != run_id
            or events[0].get("suite_id") != suite_id
            or events[0].get("case_id") != state.get("case_id")
            or events[0].get("previous_hash") is not None
            or events[0].get("attempt_id") != init.get("attempt_id")
            or events[0].get("prepare_identity_hash")
            != init.get("prepare_identity_hash")
        ):
            raise WritingEvalError(
                "Writing Eval v0.7 prepare identity provenance is invalid"
            )
        transactions_root = run_root / "transactions"
        if transactions_root.is_symlink() or not transactions_root.is_dir():
            raise WritingEvalError("Writing Eval v0.7 transition provenance is missing")
        transactions: list[dict[str, Any]] = []
        for path in transactions_root.glob("*.json"):
            if path.is_symlink() or not path.is_file():
                raise WritingEvalError("Writing Eval v0.7 transition provenance is unsafe")
            try:
                transaction = read_json(path)
            except IntegrityError as error:
                raise WritingEvalError(
                    "Writing Eval v0.7 transition provenance is unreadable"
                ) from error
            self._validate_transition_journal(path, transaction)
            if transaction.get("status") != "COMMITTED":
                raise WritingEvalError(
                    "Writing Eval v0.7 transition provenance is not committed"
                )
            transactions.append(transaction)
        transactions.sort(key=lambda item: item["target_state"]["state_version"])
        if (
            not transactions
            or len(events) != len(transactions) + 1
            or [item["target_state"]["state_version"] for item in transactions]
            != list(range(2, state["state_version"] + 1))
            or sum(item.get("kind") == "bind_manifest" for item in transactions)
            != 1
        ):
            raise WritingEvalError("Writing Eval v0.7 transition provenance is incomplete")
        predecessor = transactions[0]["base_state"]
        invariant = {
            "schema_version": STATE_SCHEMA,
            "run_id": run_id,
            "run_type": "writing_eval",
            "evaluation_only": True,
            "suite_id": suite_id,
            "case_id": state["case_id"],
            "prepare_identity_hash": init["prepare_identity_hash"],
            "prepare_payload": init["prepare_payload"],
            "snapshot_refs": state["snapshot_refs"],
            "current_node": NODE_ID,
        }
        if (
            set(predecessor) != V07_STATE_FIELDS
            or predecessor.get("state_version") != 1
            or predecessor.get("generation") != 1
            or predecessor.get("status") != "ACTIVE"
            or predecessor.get("dispatch", {}).get("status") != "PLANNED"
            or predecessor.get("phase_manifest_binding") is not None
            or predecessor.get("result_ref") is not None
            or any(predecessor.get(key) != value for key, value in invariant.items())
            or events[0].get("snapshot_refs_hash")
            != sha256_bytes(canonical_json_bytes(predecessor["snapshot_refs"]))
        ):
            raise WritingEvalError(
                "Writing Eval v0.7 prepared state provenance is invalid"
            )
        event_head = events[0]["event_hash"]
        for index, transaction in enumerate(transactions, 1):
            target = transaction["target_state"]
            if (
                transaction.get("run_id") != run_id
                or transaction.get("base_state") != predecessor
                or transaction.get("base_state_hash")
                != self._object_hash(predecessor)
                or transaction.get("base_event_head") != event_head
                or transaction.get("target_event") != events[index]
                or transaction.get("target_event_hash")
                != events[index].get("event_hash")
                or target.get("state_version")
                != predecessor.get("state_version") + 1
                or any(target.get(key) != value for key, value in invariant.items())
            ):
                raise WritingEvalError(
                    "Writing Eval v0.7 transition predecessor provenance is invalid"
                )
            self._verify_snapshot_identity(transaction.get("snapshot_identity"))
            predecessor = target
            event_head = events[index]["event_hash"]
        if predecessor != state or transactions[-1].get("kind") != "complete":
            raise WritingEvalError(
                "Writing Eval v0.7 completion provenance does not reach durable state"
            )

    def _read_state_locked(
        self, run_id: str, *, recover_transitions: bool = True
    ) -> dict[str, Any]:
        if recover_transitions:
            self._recover_transitions(run_id)
        state_path = self._state_path(run_id)
        if not state_path.is_file() or state_path.is_symlink():
            raise WritingEvalError(f"Writing Eval Run does not exist: {run_id}")
        events_path = self._events_path(run_id)
        if not events_path.is_file() or events_path.is_symlink():
            raise WritingEvalError("Writing Eval event chain is missing or unsafe")
        try:
            state = read_json(state_path)
            events = verify_event_chain(events_path)
        except IntegrityError as error:
            raise WritingEvalError(f"Writing Eval durable state is invalid: {error}") from error
        required = {
            "schema_version": STATE_SCHEMA,
            "run_id": run_id,
            "run_type": "writing_eval",
            "evaluation_only": True,
            "current_node": NODE_ID,
        }
        expected_state_fields = (
            V07_STATE_FIELDS if _is_phase_suite(state.get("suite_id")) else STATE_FIELDS
        )
        if set(state) != expected_state_fields or any(
            state.get(field) != expected for field, expected in required.items()
        ):
            raise WritingEvalError("Writing Eval durable identity is invalid")
        if (
            not isinstance(state.get("dispatch"), dict)
            or not isinstance(state.get("state_version"), int)
            or isinstance(state.get("state_version"), bool)
            or state["state_version"] < 1
            or not isinstance(state.get("generation"), int)
            or isinstance(state.get("generation"), bool)
            or state["generation"] < 1
        ):
            raise WritingEvalError("Writing Eval durable state shape is invalid")
        if not events or events[0].get("event_type") != "WRITING_EVAL_PREPARED":
            raise WritingEvalError("Writing Eval lacks its preparation audit event")
        prepare_payload = state.get("prepare_payload")
        if (
            not isinstance(prepare_payload, dict)
            or sha256_bytes(canonical_json_bytes(prepare_payload))
            != state.get("prepare_identity_hash")
            or events[0].get("prepare_identity_hash")
            != state.get("prepare_identity_hash")
            or events[0].get("suite_id") != state.get("suite_id")
            or events[0].get("case_id") != state.get("case_id")
        ):
            raise WritingEvalError("Writing Eval prepare identity is invalid")
        snapshot_refs = state.get("snapshot_refs")
        if (
            not isinstance(snapshot_refs, dict)
            or set(snapshot_refs)
            != {
                "suite_ref",
                "case_ref",
                "candidate_ref",
                "reader_visible_visual_pairs",
            }
            or events[0].get("snapshot_refs_hash")
            != sha256_bytes(canonical_json_bytes(snapshot_refs))
        ):
            raise WritingEvalError("Writing Eval snapshot identity is invalid")
        self._validate_snapshot_refs(snapshot_refs)
        self._validate_checkpoint(state)
        self._reconcile_events_and_state(state, events)
        return state

    def _validate_snapshot_refs(self, snapshot_refs: dict[str, Any]) -> None:
        for field in ("suite_ref", "case_ref", "candidate_ref"):
            try:
                _resolve_project_ref(self.project_root, snapshot_refs.get(field), field)
            except WritingEvalError as error:
                raise WritingEvalError(
                    f"Writing Eval snapshot is stale or unsafe: {field}"
                ) from error
        pairs = snapshot_refs.get("reader_visible_visual_pairs")
        if not isinstance(pairs, list):
            raise WritingEvalError("Writing Eval snapshot visual pairs must be a list")
        for index, pair in enumerate(pairs):
            if not isinstance(pair, dict) or set(pair) != {"svg_ref", "png_ref"}:
                raise WritingEvalError(
                    f"Writing Eval snapshot visual pair {index} is invalid"
                )
            for kind in ("svg_ref", "png_ref"):
                try:
                    _resolve_project_ref(
                        self.project_root,
                        pair[kind],
                        f"reader_visible_visual_pairs[{index}].{kind}",
                    )
                except WritingEvalError as error:
                    raise WritingEvalError(
                        f"Writing Eval snapshot visual is stale or unsafe: {index}.{kind}"
                    ) from error

    def _result_path(self, state: dict[str, Any]) -> Path:
        return (
            self.run_path(state["run_id"])
            / "attempts"
            / state["dispatch"]["attempt_id"]
            / "result.json"
        )

    def _validate_result_file(
        self,
        state: dict[str, Any],
        *,
        expected_ref: dict[str, Any] | None,
    ) -> dict[str, Any]:
        result_path = self._result_path(state)
        if not result_path.is_file() or result_path.is_symlink():
            raise WritingEvalError("Writing Eval completion result is missing or unsafe")
        if expected_ref is not None:
            ref = _exact_ref(expected_ref, "result_ref")
            if (
                result_path != self.project_root / ref["path"]
                or sha256_file(result_path) != ref["hash"]
            ):
                raise WritingEvalError("Writing Eval completion result ref is stale")
        try:
            result = read_json(result_path)
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval completion result is invalid") from error
        if (
            result.get("schema_version") != RESULT_SCHEMA
            or result.get("node_id") != NODE_ID
            or result.get("attempt_id") != state["dispatch"]["attempt_id"]
            or result.get("evaluation_only") is not True
        ):
            raise WritingEvalError("Writing Eval completion result schema is invalid")
        return result

    def _reconcile_events_and_state(
        self, state: dict[str, Any], events: list[dict[str, Any]]
    ) -> None:
        run_id = state["run_id"]
        allowed = {
            "WRITING_EVAL_PREPARED",
            "WRITING_EVAL_REVIEW_DISPATCHED",
            "WRITING_EVAL_UNSTARTED_DISPATCH_REVOKED",
            "WRITING_EVAL_PHASE_MANIFEST_BOUND",
            "WRITING_EVAL_COMPLETED",
        }
        if any(
            event.get("run_id") != run_id or event.get("event_type") not in allowed
            for event in events
        ):
            raise WritingEvalError("Writing Eval event chain contains foreign authority")
        if sum(event.get("event_type") == "WRITING_EVAL_PREPARED" for event in events) != 1:
            raise WritingEvalError("Writing Eval preparation event is not unique")
        attempt_id = _safe_id(state["dispatch"].get("attempt_id"), "attempt_id")
        superseded = state.get("superseded_attempts")
        if not isinstance(superseded, list):
            raise WritingEvalError("Writing Eval superseded attempts must be a list")
        superseded_ids: list[str] = []
        for index, record in enumerate(superseded):
            if (
                not isinstance(record, dict)
                or set(record) != {"attempt_id", "instruction_hash", "status"}
                or record.get("status") != "REVOKED_UNSTARTED"
            ):
                raise WritingEvalError(
                    f"Writing Eval superseded attempt {index} is invalid"
                )
            superseded_ids.append(_safe_id(record.get("attempt_id"), "attempt_id"))
        if len(superseded_ids) != len(set(superseded_ids)) or attempt_id in superseded_ids:
            raise WritingEvalError("Writing Eval attempt lineage is ambiguous")
        revoke_events = [
            event
            for event in events
            if event.get("event_type") == "WRITING_EVAL_UNSTARTED_DISPATCH_REVOKED"
        ]
        if len(revoke_events) != len(superseded):
            raise WritingEvalError(
                "Writing Eval revoke events conflict with durable attempt lineage"
            )
        valid_attempts = [*superseded_ids, attempt_id]
        for index, record in enumerate(superseded):
            matches = [
                event
                for event in revoke_events
                if event.get("attempt_id") == record["attempt_id"]
                and event.get("predecessor_instruction_hash")
                == record["instruction_hash"]
            ]
            if (
                len(matches) != 1
                or matches[0].get("successor_attempt_id")
                not in valid_attempts[index + 1 :]
            ):
                raise WritingEvalError(
                    "Writing Eval revoke event does not prove an unstarted successor"
                )
        all_started = [
            event
            for event in events
            if event.get("event_type") == "WRITING_EVAL_REVIEW_DISPATCHED"
        ]
        if any(event.get("attempt_id") not in valid_attempts for event in all_started):
            raise WritingEvalError("Writing Eval event references an unknown attempt")
        if any(event.get("attempt_id") in superseded_ids for event in all_started):
            raise WritingEvalError(
                "Writing Eval immutable event proves a revoked attempt had started"
            )
        initial_attempt = superseded_ids[0] if superseded_ids else attempt_id
        if events[0].get("attempt_id") != initial_attempt:
            raise WritingEvalError("Writing Eval preparation event has wrong initial attempt")
        started = [
            event
            for event in events
            if event.get("event_type") == "WRITING_EVAL_REVIEW_DISPATCHED"
            and event.get("attempt_id") == attempt_id
        ]
        completed = [
            event
            for event in events
            if event.get("event_type") == "WRITING_EVAL_COMPLETED"
            and event.get("attempt_id") == attempt_id
        ]
        manifest_events = [
            event
            for event in events
            if event.get("event_type") == "WRITING_EVAL_PHASE_MANIFEST_BOUND"
        ]
        binding = state.get("phase_manifest_binding")
        if _is_phase_suite(state.get("suite_id")):
            phase_build_versions = _phase_build_versions(state["suite_id"])
            if binding is None:
                if manifest_events:
                    raise WritingEvalError(
                        "Writing Eval manifest event conflicts with unbound state"
                    )
            elif (
                not isinstance(binding, dict)
                or set(binding) != V07_MANIFEST_BINDING_FIELDS
                or binding.get("phase") not in phase_build_versions
                or _exact_ref(
                    binding.get("manifest_ref"), "phase_manifest_binding.manifest_ref"
                )
                != binding["manifest_ref"]
                or len(manifest_events) != 1
                or manifest_events[0].get("attempt_id") != attempt_id
                or manifest_events[0].get("phase") != binding["phase"]
                or manifest_events[0].get("manifest_ref")
                != binding["manifest_ref"]
            ):
                raise WritingEvalError(
                    "Writing Eval manifest binding lacks exact Controller event"
                )
        elif binding is not None or manifest_events:
            raise WritingEvalError(
                "Writing Eval legacy suite cannot carry phase manifest authority"
            )
        status = state.get("status")
        dispatch_status = state["dispatch"].get("status")
        if status == "ACTIVE":
            if state.get("result_ref") is not None or completed:
                raise WritingEvalError("Writing Eval active state conflicts with completion evidence")
            if dispatch_status == "PLANNED":
                if started:
                    raise WritingEvalError(
                        "Writing Eval dispatch event proves the attempt already started"
                    )
                if self._result_path(state).exists():
                    raise WritingEvalError("Writing Eval planned attempt has a result")
            elif dispatch_status == "DISPATCHED":
                if len(started) != 1:
                    raise WritingEvalError(
                        "Writing Eval dispatched state requires one exact dispatch event"
                    )
                if self._result_path(state).exists():
                    self._validate_result_file(state, expected_ref=None)
            else:
                raise WritingEvalError("Writing Eval active dispatch status is invalid")
            return
        if status != "COMPLETED" or dispatch_status != "COMPLETED":
            raise WritingEvalError("Writing Eval durable status is invalid")
        if len(started) != 1 or len(completed) != 1:
            raise WritingEvalError(
                "Writing Eval completion requires exact dispatch and completion events"
            )
        result = self._validate_result_file(state, expected_ref=state.get("result_ref"))
        if (
            completed[0].get("result_ref") != state.get("result_ref")
            or completed[0].get("result") != result.get("result")
        ):
            raise WritingEvalError("Writing Eval completion event conflicts with result")

    def _response(self, state: dict[str, Any]) -> dict[str, Any]:
        checkpoint_ref = state["preregistration_checkpoint_ref"]
        dispatch = deepcopy(state["dispatch"])
        dispatch.pop("status", None)
        if state["status"] == "COMPLETED":
            return {
                "status": "COMPLETED",
                "run_id": state["run_id"],
                "evaluation_only": True,
                "product_authority": "NONE",
                "state": deepcopy(state),
                "result_ref": deepcopy(state["result_ref"]),
                "next_operation": None,
            }
        return {
            "status": "WRITING_EVAL_REVIEW_REQUIRED",
            "run_id": state["run_id"],
            "evaluation_only": True,
            "product_authority": "NONE",
            "state": deepcopy(state),
            "dispatch": dispatch,
            "preregistration_checkpoint_ref": deepcopy(checkpoint_ref),
            "next_operation": NODE_ID,
        }

    def _new_dispatch(
        self,
        run_id: str,
        payload: dict[str, Any],
        bindings: dict[str, Any],
        *,
        generation: int,
        snapshot_refs: dict[str, Any],
        write_root: Path | None = None,
        reference_root: Path | None = None,
        attempt_id: str | None = None,
        failpoint: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        attempt_id = attempt_id or f"writing-eval-attempt-{uuid4().hex}"
        input_refs = [
            snapshot_refs["suite_ref"]["path"],
            snapshot_refs["case_ref"]["path"],
            snapshot_refs["candidate_ref"]["path"],
        ]
        input_hashes = {
            snapshot_refs[field]["path"]: snapshot_refs[field]["hash"]
            for field in ("suite_ref", "case_ref", "candidate_ref")
        }
        isolated = [
            snapshot_refs["candidate_ref"],
            bindings["profile_ref"],
            bindings["guide_ref"],
            bindings["instruction_ref"],
            bindings["reviewer_resource_ref"],
            bindings["output_contract_ref"],
        ]
        dispatch = {
            "schema_version": DISPATCH_SCHEMA,
            "node_id": NODE_ID,
            "attempt_id": attempt_id,
            "producer_kind": "HOST_AGENT",
            "validator": "document_experience_reader_eval_v3_1",
            "instruction_ref": bindings["instruction_ref"]["path"],
            "instruction_hash": bindings["instruction_ref"]["hash"],
            "input_refs": input_refs,
            "input_hashes": input_hashes,
            "resource_refs": [
                bindings["profile_ref"],
                bindings["guide_ref"],
                bindings["reviewer_resource_ref"],
                bindings["output_contract_ref"],
            ],
            "writing_eval_context": {
                "schema_version": "writing-eval-context.v1",
                "evaluation_only": True,
                "suite_id": payload["suite_id"],
                "case_id": payload["case_id"],
                "candidate_ref": snapshot_refs["candidate_ref"],
                "profile_ref": bindings["profile_ref"],
                "guide_ref": bindings["guide_ref"],
                "reviewer_resource_ref": bindings["reviewer_resource_ref"],
                "output_contract_ref": bindings["output_contract_ref"],
                "installed_build_ref": bindings["installed_build_ref"],
                "author_execution_ref": payload["author_execution_ref"],
                "isolated_input_refs": isolated,
                "reader_visible_visual_pairs": snapshot_refs[
                    "reader_visible_visual_pairs"
                ],
                "expected_custody": "EVALUATOR_ONLY_EXCLUDED",
                "review_schema": RESULT_SCHEMA,
            },
        }
        run_root = write_root or self.run_path(run_id)
        ref_root = reference_root or self.run_path(run_id)
        try:
            dispatch_path = assert_managed_path(
                self.project_root,
                run_root / "attempts" / attempt_id / "dispatch.json",
            )
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval dispatch path is unsafe") from error
        _write_once_json(dispatch_path, dispatch, "Writing Eval dispatch")
        self._inject(failpoint, "after_dispatch_persist")
        dispatch_ref = {
            "path": (ref_root / "attempts" / attempt_id / "dispatch.json")
            .relative_to(self.project_root)
            .as_posix(),
            "hash": sha256_file(dispatch_path),
            "version": generation,
        }
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA,
            "status": "PREREGISTERED_BEFORE_RESULT",
            "run_id": run_id,
            "attempt_id": attempt_id,
            "suite_id": payload["suite_id"],
            "case_id": payload["case_id"],
            "evaluation_only": True,
            "expected_custody": "EVALUATOR_ONLY_EXCLUDED",
            "refs": {
                "source_suite_ref": payload["suite_ref"],
                "source_case_ref": payload["case_ref"],
                "source_candidate_ref": payload["candidate_ref"],
                "suite_ref": snapshot_refs["suite_ref"],
                "case_ref": snapshot_refs["case_ref"],
                "candidate_ref": snapshot_refs["candidate_ref"],
                "profile_ref": bindings["profile_ref"],
                "guide_ref": bindings["guide_ref"],
                "instruction_ref": bindings["instruction_ref"],
                "reviewer_resource_ref": bindings["reviewer_resource_ref"],
                "output_contract_ref": bindings["output_contract_ref"],
                "installed_build_ref": bindings["installed_build_ref"],
                "dispatch_ref": dispatch_ref,
            },
            "claim_boundary": "Preregistration binds inputs before Agent result; scoring is not present.",
        }
        try:
            checkpoint_path = assert_managed_path(
                self.project_root,
                run_root
                / "attempts"
                / attempt_id
                / "preregistration-checkpoint.json",
            )
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval checkpoint path is unsafe") from error
        _write_once_json(
            checkpoint_path, checkpoint, "Writing Eval preregistration checkpoint"
        )
        self._inject(failpoint, "after_checkpoint_persist")
        checkpoint_ref = {
            "path": (
                ref_root
                / "attempts"
                / attempt_id
                / "preregistration-checkpoint.json"
            )
            .relative_to(self.project_root)
            .as_posix(),
            "hash": sha256_file(checkpoint_path),
            "version": generation,
        }
        return {**dispatch, "status": "PLANNED"}, checkpoint_ref

    def _validate_active_bindings(
        self, state: dict[str, Any], bindings: dict[str, Any]
    ) -> str:
        dispatch = state["dispatch"]
        current_hash = bindings["instruction_ref"]["hash"]
        old_hash = dispatch.get("instruction_hash")
        if old_hash == current_hash:
            if dispatch.get("instruction_ref") != bindings["instruction_ref"]["path"]:
                raise WritingEvalError(
                    "Writing Eval started instruction path drift; fail closed"
                )
            for field in (
                "profile_ref",
                "guide_ref",
                "reviewer_resource_ref",
                "output_contract_ref",
            ):
                if dispatch["writing_eval_context"].get(field) != bindings[field]:
                    raise WritingEvalError(
                        f"Writing Eval started resource drift at {field}; fail closed"
                    )
            return "EXACT"
        if old_hash in KNOWN_UNSTARTED_PREDECESSOR_HASHES:
            if dispatch.get("status") != "PLANNED":
                raise WritingEvalError(
                    "Writing Eval started predecessor instruction drift; fail closed without replacement"
                )
            return "KNOWN_UNSTARTED_PREDECESSOR"
        raise WritingEvalError(
            "Writing Eval instruction drift is not a declared predecessor; fail closed"
        )

    def _prepare_initial_stage(
        self,
        *,
        run_id: str,
        normalized: dict[str, Any],
        identity_hash: str,
        bindings: dict[str, Any],
        failpoint: str | None,
    ) -> None:
        final_root = self.run_path(run_id)
        stage_root = self._initializing_path(run_id)
        transaction_path = stage_root / "init-transaction.json"
        if stage_root.exists():
            if not stage_root.is_dir() or stage_root.is_symlink():
                raise WritingEvalError("Writing Eval init transaction is unsafe")
            if not transaction_path.is_file() or transaction_path.is_symlink():
                raise WritingEvalError("Writing Eval init transaction is incomplete")
            try:
                transaction = read_json(transaction_path)
            except IntegrityError as error:
                raise WritingEvalError("Writing Eval init transaction is invalid") from error
            if (
                set(transaction) != INIT_FIELDS
                or transaction.get("schema_version") != INIT_SCHEMA
                or transaction.get("run_id") != run_id
                or transaction.get("prepare_identity_hash") != identity_hash
                or transaction.get("prepare_payload") != normalized
                or transaction.get("bindings") != bindings
                or transaction.get("generation") != 1
            ):
                raise WritingEvalError("Writing Eval init transaction identity conflict")
            attempt_id = _safe_id(transaction.get("attempt_id"), "attempt_id")
        else:
            stage_root.parent.mkdir(parents=True, exist_ok=True)
            attempt_id = f"writing-eval-attempt-{uuid4().hex}"
            transaction = {
                "schema_version": INIT_SCHEMA,
                "run_id": run_id,
                "prepare_identity_hash": identity_hash,
                "prepare_payload": normalized,
                "attempt_id": attempt_id,
                "generation": 1,
                "bindings": bindings,
            }
            creating_root = stage_root.parent / (
                f".{stage_root.name}.creating-{uuid4().hex}"
            )
            creating_root.mkdir(exist_ok=False)
            atomic_write_json(
                creating_root / "init-transaction.json", transaction
            )
            os.replace(creating_root, stage_root)
            directory = os.open(stage_root.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        self._inject(failpoint, "after_init_transaction")

        snapshot_refs = self._snapshot_inputs(
            stage_root=stage_root,
            final_root=final_root,
            payload=normalized,
        )
        snapshot_manifest = stage_root / "snapshot-refs.json"
        _write_once_json(
            snapshot_manifest,
            {
                "schema_version": "writing-eval-input-snapshot.v1",
                "refs": snapshot_refs,
            },
            "Writing Eval input snapshot manifest",
        )
        self._inject(failpoint, "after_input_snapshots")

        dispatch, checkpoint_ref = self._new_dispatch(
            run_id,
            normalized,
            bindings,
            generation=1,
            snapshot_refs=snapshot_refs,
            write_root=stage_root,
            reference_root=final_root,
            attempt_id=attempt_id,
            failpoint=failpoint,
        )
        state = {
            "schema_version": STATE_SCHEMA,
            "run_id": run_id,
            "run_type": "writing_eval",
            "evaluation_only": True,
            "suite_id": normalized["suite_id"],
            "case_id": normalized["case_id"],
            "prepare_identity_hash": identity_hash,
            "prepare_payload": normalized,
            "snapshot_refs": snapshot_refs,
            "state_version": 1,
            "generation": 1,
            "status": "ACTIVE",
            "current_node": NODE_ID,
            "dispatch": dispatch,
            "preregistration_checkpoint_ref": checkpoint_ref,
            "superseded_attempts": [],
            "result_ref": None,
        }
        if _is_phase_suite(normalized["suite_id"]):
            state["phase_manifest_binding"] = None
        _write_once_json(stage_root / "state.json", state, "Writing Eval initial state")
        self._inject(failpoint, "after_state_persist")
        events_path = stage_root / "events.jsonl"
        if events_path.exists():
            try:
                events = verify_event_chain(events_path)
            except IntegrityError as error:
                raise WritingEvalError("Writing Eval prepared event is invalid") from error
            if (
                len(events) != 1
                or events[0].get("event_type") != "WRITING_EVAL_PREPARED"
                or events[0].get("run_id") != run_id
                or events[0].get("attempt_id") != attempt_id
                or events[0].get("prepare_identity_hash") != identity_hash
                or events[0].get("snapshot_refs_hash")
                != sha256_bytes(canonical_json_bytes(snapshot_refs))
            ):
                raise WritingEvalError("Writing Eval prepared event identity conflict")
        else:
            append_event(
                events_path,
                {
                    "event_type": "WRITING_EVAL_PREPARED",
                    "actor": "writing-eval-controller",
                    "run_id": run_id,
                    "suite_id": normalized["suite_id"],
                    "case_id": normalized["case_id"],
                    "prepare_identity_hash": identity_hash,
                    "snapshot_refs_hash": sha256_bytes(
                        canonical_json_bytes(snapshot_refs)
                    ),
                    "attempt_id": attempt_id,
                },
            )
        self._inject(failpoint, "after_prepared_event")
        if final_root.exists():
            raise WritingEvalError("Writing Eval final Run appeared during initialization")
        os.replace(stage_root, final_root)
        directory = os.open(final_root.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self._inject(failpoint, "after_initial_publish")

    def prepare(
        self,
        run_id: str,
        payload: dict[str, Any],
        *,
        failpoint: str | None = None,
    ) -> dict[str, Any]:
        _safe_id(run_id, "run_id")
        normalized, _paths = _validate_prepare_payload(self.project_root, payload)
        identity_hash = sha256_bytes(canonical_json_bytes(normalized))
        bindings = _installed_bindings(
            self.project_root, self.skill_root, normalized["suite_id"]
        )
        with self._operation_locks(run_id):
            state_path = self._state_path(run_id)
            if state_path.exists():
                state = self._read_state_locked(run_id)
                if state.get("prepare_identity_hash") != identity_hash:
                    raise WritingEvalError("Writing Eval prepare identity conflict")
                compatibility = self._validate_active_bindings(state, bindings)
                if state["status"] == "COMPLETED":
                    if compatibility != "EXACT":
                        raise WritingEvalError(
                            "Writing Eval completed instruction is not exact"
                        )
                    return self._response(state)
                if compatibility == "KNOWN_UNSTARTED_PREDECESSOR":
                    base_state = deepcopy(state)
                    old = deepcopy(state["dispatch"])
                    result_path = (
                        self.run_path(run_id)
                        / "attempts"
                        / old["attempt_id"]
                        / "result.json"
                    )
                    if result_path.exists():
                        raise WritingEvalError(
                            "Writing Eval predecessor has a durable result; fail closed"
                        )
                    generation = state["generation"] + 1
                    successor_seed = sha256_bytes(
                        canonical_json_bytes(
                            {
                                "run_id": run_id,
                                "generation": generation,
                                "instruction_hash": bindings["instruction_ref"]["hash"],
                            }
                        )
                    )[7:39]
                    dispatch, checkpoint_ref = self._new_dispatch(
                        run_id,
                        normalized,
                        bindings,
                        generation=generation,
                        snapshot_refs=state["snapshot_refs"],
                        attempt_id=f"writing-eval-attempt-{successor_seed}",
                    )
                    state["superseded_attempts"].append(
                        {
                            "attempt_id": old["attempt_id"],
                            "instruction_hash": old["instruction_hash"],
                            "status": "REVOKED_UNSTARTED",
                        }
                    )
                    state["dispatch"] = dispatch
                    state["preregistration_checkpoint_ref"] = checkpoint_ref
                    state["generation"] = generation
                    state["state_version"] += 1
                    self._commit_transition(
                        kind="revoke",
                        base_state=base_state,
                        target_state=state,
                        event_payload={
                            "event_type": "WRITING_EVAL_UNSTARTED_DISPATCH_REVOKED",
                            "actor": "writing-eval-controller",
                            "run_id": run_id,
                            "attempt_id": old["attempt_id"],
                            "successor_attempt_id": dispatch["attempt_id"],
                            "predecessor_instruction_hash": old["instruction_hash"],
                            "successor_instruction_hash": dispatch["instruction_hash"],
                        },
                        failpoint=failpoint,
                    )
                    state = self._read_state_locked(run_id)
                if state["dispatch"].get("status") == "PLANNED":
                    if failpoint == "after_dispatch_planned":
                        return self._response(state)
                    base_state = deepcopy(state)
                    target_state = deepcopy(state)
                    target_state["dispatch"]["status"] = "DISPATCHED"
                    target_state["state_version"] += 1
                    self._commit_transition(
                        kind="dispatch",
                        base_state=base_state,
                        target_state=target_state,
                        event_payload={
                            "event_type": "WRITING_EVAL_REVIEW_DISPATCHED",
                            "actor": "writing-eval-controller",
                            "run_id": run_id,
                            "attempt_id": state["dispatch"]["attempt_id"],
                        },
                        failpoint=failpoint,
                    )
                    state = self._read_state_locked(run_id)
                return self._response(state)
            self._prepare_initial_stage(
                run_id=run_id,
                normalized=normalized,
                identity_hash=identity_hash,
                bindings=bindings,
                failpoint=failpoint,
            )
            state = self._read_state_locked(run_id)
            if failpoint == "after_dispatch_planned":
                return self._response(state)
            base_state = deepcopy(state)
            target_state = deepcopy(state)
            target_state["dispatch"]["status"] = "DISPATCHED"
            target_state["state_version"] += 1
            self._commit_transition(
                kind="dispatch",
                base_state=base_state,
                target_state=target_state,
                event_payload={
                    "event_type": "WRITING_EVAL_REVIEW_DISPATCHED",
                    "actor": "writing-eval-controller",
                    "run_id": run_id,
                    "attempt_id": state["dispatch"]["attempt_id"],
                },
                failpoint=failpoint,
            )
            state = self._read_state_locked(run_id)
            return self._response(state)

    def bind_phase_manifest(
        self,
        run_id: str,
        phase: str,
        manifest_ref: dict[str, Any],
    ) -> dict[str, Any]:
        """Controller-bind one prepared v0.7 Run to the exact shared manifest."""

        with self._operation_locks(run_id):
            state = self._read_state_locked(run_id)
            suite_id = state.get("suite_id")
            if not _is_phase_suite(suite_id):
                raise WritingEvalError(
                    "Writing Eval phase manifest requires a phase-bound suite"
                )
            if phase not in _phase_build_versions(suite_id):
                raise WritingEvalError("Writing Eval phase manifest phase is invalid")
            if (
                state.get("status") != "ACTIVE"
                or state.get("dispatch", {}).get("status") != "DISPATCHED"
                or state.get("result_ref") is not None
            ):
                raise WritingEvalError(
                    "Writing Eval phase manifest binding requires one prepared v0.7 Run"
                )
            checked_ref, manifest_path = _resolve_project_ref(
                self.project_root, manifest_ref, "phase_manifest_ref"
            )
            expected_path = (
                self.project_root
                / ".better-product-graph"
                / "writing-evals"
                / "execution-manifests"
                / f"{phase}.json"
            )
            if manifest_path != expected_path:
                raise WritingEvalError(
                    "Writing Eval phase manifest path is not canonical"
                )
            try:
                manifest = read_json(manifest_path)
            except IntegrityError as error:
                raise WritingEvalError(
                    "Writing Eval phase manifest is invalid"
                ) from error
            entries = manifest.get("entries") if isinstance(manifest, dict) else None
            root_stat = self.project_root.stat()
            root_identity = {
                "path": str(self.project_root),
                "device": root_stat.st_dev,
                "inode": root_stat.st_ino,
            }
            if (
                manifest.get("schema_version")
                != _phase_schema(suite_id, "execution-manifest")
                or manifest.get("status") != "FROZEN_BEFORE_AGENT_OUTPUT"
                or manifest.get("suite_id") != suite_id
                or manifest.get("phase") != phase
                or manifest.get("central_project_root") != root_identity
                or manifest.get("installed_build_ref")
                != state["dispatch"]["writing_eval_context"]["installed_build_ref"]
                or manifest.get("required_attempt_count") != 27
                or manifest.get("result_ref_null_count_at_freeze") != 27
                or manifest.get("agent_output_count_at_freeze") != 0
                or not isinstance(entries, list)
                or len(entries) != 27
            ):
                raise WritingEvalError(
                    "Writing Eval phase manifest authority is invalid"
                )
            matches = [
                entry
                for entry in entries
                if isinstance(entry, dict) and entry.get("run_id") == run_id
            ]
            if len(matches) != 1:
                raise WritingEvalError(
                    "Writing Eval phase manifest lacks one exact Run entry"
                )
            entry = matches[0]
            binding = {"phase": phase, "manifest_ref": checked_ref}
            current_binding = state.get("phase_manifest_binding")
            if current_binding is not None:
                if current_binding != binding:
                    raise WritingEvalError(
                        "Writing Eval Run is already bound to another manifest"
                    )
                return self._response(state)
            state_ref = _exact_ref(entry.get("state_ref"), "manifest state_ref")
            expected_state_ref = {
                "path": self._state_path(run_id).relative_to(self.project_root).as_posix(),
                "hash": sha256_file(self._state_path(run_id)),
                "version": state["state_version"],
            }
            context = state["dispatch"]["writing_eval_context"]
            if (
                state_ref != expected_state_ref
                or entry.get("suite_id") != suite_id
                or entry.get("phase") != phase
                or entry.get("agent_case_id") != state["case_id"]
                or entry.get("attempt_id") != state["dispatch"]["attempt_id"]
                or entry.get("author_execution_ref")
                != context["author_execution_ref"]
                or entry.get("preregistration_checkpoint_ref")
                != state["preregistration_checkpoint_ref"]
                or entry.get("installed_build_ref")
                != context["installed_build_ref"]
                or entry.get("central_project_root") != root_identity
            ):
                raise WritingEvalError(
                    "Writing Eval phase manifest entry differs from prepared Run"
                )
            for candidate in entries:
                output = candidate.get("output_target") if isinstance(candidate, dict) else None
                if not isinstance(output, str):
                    raise WritingEvalError(
                        "Writing Eval phase manifest output target is invalid"
                    )
                try:
                    output_path = assert_managed_path(
                        self.project_root, self.project_root / output
                    )
                except IntegrityError as error:
                    raise WritingEvalError(
                        "Writing Eval phase manifest output target escapes project"
                    ) from error
                if output_path.exists() or output_path.is_symlink():
                    raise WritingEvalError(
                        "Writing Eval phase manifest binding occurred after Agent output"
                    )
            target_state = deepcopy(state)
            target_state["phase_manifest_binding"] = binding
            target_state["state_version"] += 1
            self._commit_transition(
                kind="bind_manifest",
                base_state=state,
                target_state=target_state,
                event_payload={
                    "event_type": "WRITING_EVAL_PHASE_MANIFEST_BOUND",
                    "actor": "writing-eval-controller",
                    "run_id": run_id,
                    "attempt_id": state["dispatch"]["attempt_id"],
                    "phase": phase,
                    "manifest_ref": checked_ref,
                },
            )
            return self._response(self._read_state_locked(run_id))

    def _validate_checkpoint(self, state: dict[str, Any]) -> dict[str, Any]:
        checkpoint_ref = _exact_ref(
            state.get("preregistration_checkpoint_ref"),
            "preregistration_checkpoint_ref",
        )
        try:
            checkpoint_path = assert_managed_path(
                self.project_root,
                self.project_root / checkpoint_ref["path"],
            )
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval checkpoint escapes project") from error
        if (
            not checkpoint_path.is_file()
            or checkpoint_path.is_symlink()
            or sha256_file(checkpoint_path) != checkpoint_ref["hash"]
        ):
            raise WritingEvalError("Writing Eval checkpoint identity is stale")
        try:
            checkpoint = read_json(checkpoint_path)
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval checkpoint is invalid JSON") from error
        expected_keys = {
            "source_suite_ref",
            "source_case_ref",
            "source_candidate_ref",
            "suite_ref",
            "case_ref",
            "candidate_ref",
            "profile_ref",
            "guide_ref",
            "instruction_ref",
            "reviewer_resource_ref",
            "output_contract_ref",
            "installed_build_ref",
            "dispatch_ref",
        }
        if (
            checkpoint.get("schema_version") != CHECKPOINT_SCHEMA
            or checkpoint.get("status") != "PREREGISTERED_BEFORE_RESULT"
            or checkpoint.get("run_id") != state["run_id"]
            or checkpoint.get("attempt_id") != state["dispatch"]["attempt_id"]
            or checkpoint.get("evaluation_only") is not True
            or checkpoint.get("expected_custody") != "EVALUATOR_ONLY_EXCLUDED"
            or not isinstance(checkpoint.get("refs"), dict)
            or set(checkpoint["refs"]) != expected_keys
        ):
            raise WritingEvalError("Writing Eval checkpoint contract is invalid")
        payload = state["prepare_payload"]
        snapshot_refs = state["snapshot_refs"]
        context = state["dispatch"]["writing_eval_context"]
        exact_checkpoint_refs = {
            "source_suite_ref": payload["suite_ref"],
            "source_case_ref": payload["case_ref"],
            "source_candidate_ref": payload["candidate_ref"],
            "suite_ref": snapshot_refs["suite_ref"],
            "case_ref": snapshot_refs["case_ref"],
            "candidate_ref": snapshot_refs["candidate_ref"],
            "profile_ref": context["profile_ref"],
            "guide_ref": context["guide_ref"],
            "instruction_ref": {
                "path": state["dispatch"]["instruction_ref"],
                "hash": state["dispatch"]["instruction_hash"],
                "version": _suite_binding(state["suite_id"])[
                    "instruction_version"
                ],
            },
            "reviewer_resource_ref": context["reviewer_resource_ref"],
            "output_contract_ref": context["output_contract_ref"],
            "installed_build_ref": context["installed_build_ref"],
        }
        for field, expected in exact_checkpoint_refs.items():
            if checkpoint["refs"].get(field) != expected:
                raise WritingEvalError(
                    f"Writing Eval checkpoint {field} differs from durable authority"
                )
        dispatch_ref = _exact_ref(checkpoint["refs"]["dispatch_ref"], "dispatch_ref")
        try:
            dispatch_path = assert_managed_path(
                self.project_root, self.project_root / dispatch_ref["path"]
            )
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval dispatch ref escapes project") from error
        durable_dispatch = deepcopy(state["dispatch"])
        durable_dispatch.pop("status", None)
        try:
            dispatch_json = read_json(dispatch_path)
        except IntegrityError as error:
            raise WritingEvalError("Writing Eval dispatch ref is invalid") from error
        if (
            not dispatch_path.is_file()
            or dispatch_path.is_symlink()
            or sha256_file(dispatch_path) != dispatch_ref["hash"]
            or dispatch_json != durable_dispatch
        ):
            raise WritingEvalError("Writing Eval dispatch ref is stale")
        return checkpoint

    def _validate_current_agent_inputs(self, state: dict[str, Any]) -> bytes:
        payload = state["snapshot_refs"]
        self._validate_snapshot_refs(payload)
        candidate_bytes: bytes | None = None
        for field in ("suite_ref", "case_ref", "candidate_ref"):
            try:
                _ref, path = _resolve_project_ref(
                    self.project_root, payload[field], field
                )
            except WritingEvalError as error:
                raise WritingEvalError(
                    f"Writing Eval snapshot changed after preregistration: {field}"
                ) from error
            if field == "candidate_ref":
                candidate_bytes = path.read_bytes()
                if sha256_bytes(candidate_bytes) != payload[field]["hash"]:
                    raise WritingEvalError(
                        "Writing Eval Candidate snapshot changed during read"
                    )
        if candidate_bytes is None:
            raise WritingEvalError("Writing Eval Candidate snapshot is missing")
        return candidate_bytes

    def _validate_v07_manifest_transition_anchor(
        self,
        state: dict[str, Any],
        entry: dict[str, Any],
        phase: str,
        manifest_ref: dict[str, Any],
    ) -> None:
        """Bind the sole manifest transition to the frozen dispatched state ref."""

        transactions_root = self.run_path(state["run_id"]) / "transactions"
        binding_transactions: list[dict[str, Any]] = []
        for path in transactions_root.glob("*.json"):
            try:
                transaction = read_json(path)
            except IntegrityError as error:
                raise WritingEvalError(
                    "Writing Eval v0.7 manifest transition is invalid"
                ) from error
            self._validate_transition_journal(path, transaction)
            if transaction.get("kind") == "bind_manifest":
                binding_transactions.append(transaction)
        if len(binding_transactions) != 1:
            raise WritingEvalError(
                "Writing Eval v0.7 requires one manifest transition"
            )
        transaction = binding_transactions[0]
        base = transaction["base_state"]
        base_dispatch = base.get("dispatch")
        expected_state_ref = {
            "path": self._state_path(state["run_id"])
            .relative_to(self.project_root)
            .as_posix(),
            "hash": sha256_bytes(canonical_json_bytes(base) + b"\n"),
            "version": base.get("state_version"),
        }
        if (
            entry.get("state_ref") != expected_state_ref
            or base.get("status") != "ACTIVE"
            or not isinstance(base_dispatch, dict)
            or base_dispatch.get("status") != "DISPATCHED"
            or base_dispatch.get("attempt_id") != entry.get("attempt_id")
            or base.get("result_ref") is not None
            or transaction.get("attempt_id") != entry.get("attempt_id")
            or transaction.get("target_state", {}).get("phase_manifest_binding")
            != {"phase": phase, "manifest_ref": manifest_ref}
        ):
            raise WritingEvalError(
                "Writing Eval v0.7 manifest transition base state is not frozen"
            )

    def _validate_v07_batch_barrier(
        self, state: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Require the frozen 27-output receipt before any v0.7 submission."""

        if not _is_phase_suite(state.get("suite_id")):
            return
        suite_id = state["suite_id"]
        phase_build_versions = _phase_build_versions(suite_id)
        manifests_root = assert_managed_path(
            self.project_root,
            self.project_root
            / ".better-product-graph"
            / "writing-evals"
            / "execution-manifests",
        )
        candidates: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
        for phase, expected_version in phase_build_versions.items():
            manifest_path = manifests_root / f"{phase}.json"
            if manifest_path.is_symlink() or not manifest_path.is_file():
                continue
            try:
                manifest = read_json(manifest_path)
            except IntegrityError as error:
                raise WritingEvalError("Writing Eval v0.7 phase manifest is invalid") from error
            matching = [
                entry
                for entry in manifest.get("entries", [])
                if isinstance(entry, dict) and entry.get("run_id") == state["run_id"]
            ]
            if len(matching) == 1:
                if (
                    manifest.get("schema_version")
                    != _phase_schema(suite_id, "execution-manifest")
                    or manifest.get("status") != "FROZEN_BEFORE_AGENT_OUTPUT"
                    or manifest.get("suite_id") != suite_id
                    or manifest.get("phase") != phase
                    or manifest.get("required_attempt_count") != 27
                    or manifest.get("result_ref_null_count_at_freeze") != 27
                    or manifest.get("agent_output_count_at_freeze") != 0
                    or not isinstance(manifest.get("entries"), list)
                    or len(manifest["entries"]) != 27
                    or manifest.get("installed_build_ref", {}).get("version")
                    != expected_version
                ):
                    raise WritingEvalError(
                        "Writing Eval v0.7 phase manifest identity is invalid"
                    )
                candidates.append((manifest_path, manifest, matching[0]))
        if len(candidates) != 1:
            raise WritingEvalError(
                "Writing Eval v0.7 batch-validation receipt requires one exact phase manifest"
            )
        manifest_path, manifest, entry = candidates[0]
        phase = manifest["phase"]
        context = state["dispatch"]["writing_eval_context"]
        root_stat = self.project_root.stat()
        root_identity = {
            "path": str(self.project_root),
            "device": root_stat.st_dev,
            "inode": root_stat.st_ino,
        }
        exact_entry = {
            "suite_id": suite_id,
            "phase": phase,
            "agent_case_id": state["case_id"],
            "run_id": state["run_id"],
            "attempt_id": state["dispatch"]["attempt_id"],
            "author_execution_ref": context["author_execution_ref"],
            "preregistration_checkpoint_ref": state["preregistration_checkpoint_ref"],
            "installed_build_ref": context["installed_build_ref"],
            "central_project_root": root_identity,
        }
        if (
            manifest.get("central_project_root") != root_identity
            or manifest.get("installed_build_ref") != context["installed_build_ref"]
            or any(entry.get(field) != expected for field, expected in exact_entry.items())
            or entry.get("reviewer_execution_ref")
            != result.get("reviewer_execution_ref")
        ):
            raise WritingEvalError(
                "Writing Eval v0.7 result is not bound to the exact phase manifest entry"
            )
        manifest_ref = {
            "path": manifest_path.relative_to(self.project_root).as_posix(),
            "hash": sha256_file(manifest_path),
            "version": 1,
        }
        if state.get("phase_manifest_binding") != {
            "phase": phase,
            "manifest_ref": manifest_ref,
        }:
            raise WritingEvalError(
                "Writing Eval v0.7 bound manifest differs from durable Run authority"
            )
        self._validate_v07_manifest_transition_anchor(
            state, entry, phase, manifest_ref
        )
        manifest_receipt_path = manifests_root / f"{phase}.manifest-receipt.json"
        batch_receipt_path = manifests_root / f"{phase}.batch-validation-receipt.json"
        if (
            manifest_receipt_path.is_symlink()
            or not manifest_receipt_path.is_file()
            or batch_receipt_path.is_symlink()
            or not batch_receipt_path.is_file()
        ):
            raise WritingEvalError(
                "Writing Eval v0.7 batch-validation receipt is missing or unsafe"
            )
        try:
            manifest_receipt = read_json(manifest_receipt_path)
            batch_receipt = read_json(batch_receipt_path)
        except IntegrityError as error:
            raise WritingEvalError(
                "Writing Eval v0.7 batch-validation receipt is missing or invalid"
            ) from error
        if (
            manifest_receipt
            != {
                "schema_version": _phase_schema(suite_id, "manifest-receipt"),
                "status": "WRITE_ONCE_LOCKED_BEFORE_AGENT_OUTPUT",
                "suite_id": suite_id,
                "phase": phase,
                "central_project_root": root_identity,
                "installed_build_ref": context["installed_build_ref"],
                "manifest_ref": manifest_ref,
            }
            or not isinstance(batch_receipt, dict)
            or set(batch_receipt)
            != {
                "schema_version", "status", "suite_id", "phase", "manifest_ref",
                "required_attempt_count", "entries",
            }
            or batch_receipt.get("schema_version")
            != _phase_schema(suite_id, "batch-validation-receipt")
            or batch_receipt.get("status")
            != "ALL_27_FULL_RAW_RESULTS_VALIDATED_BEFORE_FIRST_SUBMISSION"
            or batch_receipt.get("suite_id") != suite_id
            or batch_receipt.get("phase") != phase
            or batch_receipt.get("manifest_ref") != manifest_ref
            or batch_receipt.get("required_attempt_count") != 27
            or not isinstance(batch_receipt.get("entries"), list)
            or len(batch_receipt["entries"]) != 27
        ):
                raise WritingEvalError(
                    "Writing Eval v0.7 batch-validation receipt identity is invalid"
                )
        receipts_by_ordinal = {
            item.get("ordinal"): item
            for item in batch_receipt["entries"]
            if isinstance(item, dict)
        }
        if len(receipts_by_ordinal) != 27:
            raise WritingEvalError(
                "Writing Eval v0.7 batch-validation receipt coverage is invalid"
            )
        selected_raw: dict[str, Any] | None = None
        for manifest_entry in manifest["entries"]:
            receipt_entry = receipts_by_ordinal.get(manifest_entry.get("ordinal"))
            if (
                not isinstance(receipt_entry, dict)
                or set(receipt_entry)
                != {
                    "ordinal", "run_id", "attempt_id", "reviewer_execution_ref",
                    "original_raw_ref", "accepted_result_ref",
                    "preflight_rejection_ref", "mechanical_correction_ref",
                }
                or receipt_entry.get("run_id") != manifest_entry.get("run_id")
                or receipt_entry.get("attempt_id") != manifest_entry.get("attempt_id")
                or receipt_entry.get("reviewer_execution_ref")
                != manifest_entry.get("reviewer_execution_ref")
            ):
                raise WritingEvalError(
                    "Writing Eval v0.7 batch-validation receipt entry is invalid"
                )
            raw_ref = _exact_ref(
                receipt_entry.get("original_raw_ref"), "batch original_raw_ref"
            )
            if raw_ref["path"] != manifest_entry.get("output_target"):
                raise WritingEvalError(
                    "Writing Eval v0.7 batch raw output target differs from manifest"
                )
            try:
                raw_path = assert_managed_path(
                    self.project_root, self.project_root / raw_ref["path"]
                )
            except IntegrityError as error:
                raise WritingEvalError(
                    "Writing Eval v0.7 batch raw output escapes project"
                ) from error
            if raw_path.is_symlink() or not raw_path.is_file() or sha256_file(raw_path) != raw_ref["hash"]:
                raise WritingEvalError(
                    "Writing Eval v0.7 batch raw output hash is stale"
                )
            accepted_ref = _exact_ref(
                receipt_entry.get("accepted_result_ref"),
                "batch accepted_result_ref",
            )
            corrected_path = raw_path.with_name(raw_path.name + ".corrected.json")
            rejection_path = raw_path.with_name(
                raw_path.name + ".preflight-rejection.json"
            )
            correction_path = raw_path.with_name(
                raw_path.name + ".mechanical-correction.json"
            )
            corrected = accepted_ref != raw_ref
            expected_accepted_path = corrected_path if corrected else raw_path
            if accepted_ref["path"] != expected_accepted_path.relative_to(
                self.project_root
            ).as_posix():
                raise WritingEvalError(
                    "Writing Eval v0.7 accepted result path is not canonical"
                )
            if (
                expected_accepted_path.is_symlink()
                or not expected_accepted_path.is_file()
                or sha256_file(expected_accepted_path) != accepted_ref["hash"]
            ):
                raise WritingEvalError(
                    "Writing Eval v0.7 accepted result hash is stale"
                )
            rejection_ref = receipt_entry.get("preflight_rejection_ref")
            correction_ref = receipt_entry.get("mechanical_correction_ref")
            if not corrected:
                if rejection_ref is not None or correction_ref is not None:
                    raise WritingEvalError(
                        "Writing Eval v0.7 valid raw result carries correction authority"
                    )
            else:
                checked_rejection_ref = _exact_ref(
                    rejection_ref, "batch preflight_rejection_ref"
                )
                checked_correction_ref = _exact_ref(
                    correction_ref, "batch mechanical_correction_ref"
                )
                expected_paths = (
                    (rejection_path, checked_rejection_ref),
                    (correction_path, checked_correction_ref),
                )
                if any(
                    path.is_symlink()
                    or not path.is_file()
                    or ref["path"]
                    != path.relative_to(self.project_root).as_posix()
                    or sha256_file(path) != ref["hash"]
                    for path, ref in expected_paths
                ):
                    raise WritingEvalError(
                        "Writing Eval v0.7 mechanical correction proof is stale"
                    )
                try:
                    rejection = read_json(rejection_path)
                    correction = read_json(correction_path)
                    original_value = read_json(raw_path)
                    corrected_value = read_json(expected_accepted_path)
                except IntegrityError as error:
                    raise WritingEvalError(
                        "Writing Eval v0.7 mechanical correction proof is invalid"
                    ) from error
                changed_fields = (
                    sorted(
                        field
                        for field in original_value
                        if original_value.get(field) != corrected_value.get(field)
                    )
                    if isinstance(original_value, dict)
                    and isinstance(corrected_value, dict)
                    and set(original_value) == set(corrected_value)
                    else []
                )
                semantic_before = (
                    {
                        field: value
                        for field, value in original_value.items()
                        if field not in V07_MECHANICAL_AUTHORITY_FIELDS
                    }
                    if isinstance(original_value, dict)
                    else None
                )
                semantic_after = (
                    {
                        field: value
                        for field, value in corrected_value.items()
                        if field not in V07_MECHANICAL_AUTHORITY_FIELDS
                    }
                    if isinstance(corrected_value, dict)
                    else None
                )
                semantic_before_hash = (
                    sha256_bytes(canonical_json_bytes(semantic_before))
                    if semantic_before is not None
                    else None
                )
                semantic_after_hash = (
                    sha256_bytes(canonical_json_bytes(semantic_after))
                    if semantic_after is not None
                    else None
                )
                if (
                    not isinstance(rejection, dict)
                    or set(rejection)
                    != {
                        "schema_version", "status", "suite_id", "phase", "ordinal",
                        "run_id", "attempt_id", "original_raw_ref",
                        "semantic_payload_hash", "copied_authority_values",
                    }
                    or rejection.get("schema_version")
                    != _phase_schema(suite_id, "public-preflight-rejection")
                    or rejection.get("status")
                    != "AUTHORITY_ONLY_REJECTED_NO_RUN_SUBMISSION"
                    or rejection.get("suite_id") != suite_id
                    or rejection.get("phase") != phase
                    or rejection.get("ordinal") != manifest_entry.get("ordinal")
                    or rejection.get("run_id") != manifest_entry.get("run_id")
                    or rejection.get("attempt_id") != manifest_entry.get("attempt_id")
                    or rejection.get("original_raw_ref") != raw_ref
                    or not isinstance(rejection.get("copied_authority_values"), dict)
                    or not rejection["copied_authority_values"]
                    or any(
                        field not in V07_MECHANICAL_AUTHORITY_FIELDS
                        for field in rejection["copied_authority_values"]
                    )
                    or not isinstance(correction, dict)
                    or correction.get("schema_version")
                    != _phase_schema(suite_id, "mechanical-correction")
                    or correction.get("status") != "AUTHORITY_COPY_ONLY"
                    or changed_fields
                    != sorted(rejection["copied_authority_values"])
                    or any(
                        corrected_value.get(field) != expected
                        for field, expected in rejection[
                            "copied_authority_values"
                        ].items()
                    )
                    or correction.get("original_raw_hash") != raw_ref["hash"]
                    or correction.get("corrected_raw_hash") != accepted_ref["hash"]
                    or correction.get("semantic_payload_hash_before")
                    != rejection.get("semantic_payload_hash")
                    or correction.get("semantic_payload_hash_after")
                    != rejection.get("semantic_payload_hash")
                    or semantic_before_hash != rejection.get("semantic_payload_hash")
                    or semantic_after_hash != rejection.get("semantic_payload_hash")
                    or correction.get("changed_fields")
                    != sorted(rejection["copied_authority_values"])
                    or correction.get("original_raw_bytes_preservation") != "REQUIRED"
                    or correction.get("same_attempt_only") is not True
                ):
                    raise WritingEvalError(
                        "Writing Eval v0.7 mechanical correction authority is invalid"
                    )
            if manifest_entry.get("run_id") == state["run_id"]:
                try:
                    selected_raw = read_json(expected_accepted_path)
                except IntegrityError as error:
                    raise WritingEvalError(
                        "Writing Eval v0.7 selected raw output is invalid"
                    ) from error
        if selected_raw != result:
            raise WritingEvalError(
                "Writing Eval v0.7 submitted result differs from prevalidated raw output"
            )

    def review(
        self,
        run_id: str,
        result: dict[str, Any],
        *,
        failpoint: str | None = None,
    ) -> dict[str, Any]:
        with self._operation_locks(run_id):
            state = self._read_state_locked(run_id)
            bindings = _installed_bindings(
                self.project_root, self.skill_root, state["suite_id"]
            )
            compatibility = self._validate_active_bindings(state, bindings)
            if state["status"] == "COMPLETED":
                if compatibility != "EXACT":
                    raise WritingEvalError(
                        "Writing Eval completed instruction is not exact"
                    )
                result_path = self.project_root / state["result_ref"]["path"]
                if canonical_json_bytes(result) + b"\n" != result_path.read_bytes():
                    raise WritingEvalError("Writing Eval completed result identity conflict")
                return self._response(state)
            if state["status"] != "ACTIVE" or state["dispatch"].get("status") != "DISPATCHED":
                raise WritingEvalError("Writing Eval review lacks one started dispatch")
            if compatibility != "EXACT":
                raise WritingEvalError("Writing Eval review instruction is not exact")
            self._validate_checkpoint(state)
            self._validate_v07_batch_barrier(state, result)
            dispatch = deepcopy(state["dispatch"])
            dispatch.pop("status", None)
            with self._open_snapshot_custody(state) as (
                candidate_bytes,
                snapshot_identity,
                verify_snapshot,
            ):
                try:
                    validated = validate_writing_eval_review(
                        self.project_root,
                        result,
                        dispatch=dispatch,
                        checkpoint_ref=state["preregistration_checkpoint_ref"],
                        expected_visual_pairs=dispatch["writing_eval_context"][
                            "reader_visible_visual_pairs"
                        ],
                        candidate_bytes=candidate_bytes,
                    )
                except (WritingEvalReviewError, IntegrityError) as error:
                    raise WritingEvalError(
                        f"Writing Eval review rejected: {error}"
                    ) from error
                verify_snapshot()
                if (
                    self._validate_active_bindings(
                        state,
                        _installed_bindings(
                            self.project_root, self.skill_root, state["suite_id"]
                        ),
                    )
                    != "EXACT"
                ):
                    raise WritingEvalError(
                        "Writing Eval installed bindings changed before commit"
                    )
                self._validate_checkpoint(state)
                verify_snapshot()
                attempt_root = (
                    self.run_path(run_id) / "attempts" / dispatch["attempt_id"]
                )
                result_path = attempt_root / "result.json"
                result_bytes = canonical_json_bytes(validated) + b"\n"
                result_ref = {
                    "path": result_path.relative_to(self.project_root).as_posix(),
                    "hash": sha256_bytes(result_bytes),
                    "version": 1,
                }
                target_state = deepcopy(state)
                target_state["status"] = "COMPLETED"
                target_state["dispatch"]["status"] = "COMPLETED"
                target_state["result_ref"] = result_ref
                target_state["state_version"] += 1
                transition_failpoint = (
                    "complete.after_result"
                    if failpoint == "after_result_persist"
                    else failpoint
                )
                self._commit_transition(
                    kind="complete",
                    base_state=state,
                    target_state=target_state,
                    event_payload={
                    "event_type": "WRITING_EVAL_COMPLETED",
                    "actor": "writing-eval-controller",
                    "run_id": run_id,
                    "attempt_id": dispatch["attempt_id"],
                    "result_ref": result_ref,
                    "result": validated["result"],
                    "human_reader_observation": "NOT_RUN",
                    },
                    result_ref=result_ref,
                    result_value=validated,
                    snapshot_identity=snapshot_identity,
                    failpoint=transition_failpoint,
                )
                verify_snapshot()
                state = self._read_state_locked(run_id)
                verify_snapshot()
                return self._response(state)
