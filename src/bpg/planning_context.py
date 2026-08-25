"""Safe discovery and validation for one Run-scoped planning context."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

from .storage import IntegrityError, assert_managed_path, sha256_file


class PlanningContextError(ValueError):
    """A planning-context submission is incomplete, unsafe, or not exact."""


MAX_DISCOVERED_MATERIALS = 24
MAX_MATERIAL_BYTES = 512_000
MAX_TOTAL_BYTES = 3_000_000

_ROOT_CANDIDATES = (
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "PROJECT.md",
    "pyproject.toml",
    "package.json",
)
_DISCOVERY_GLOBS = (
    ".assistant/project.md",
    ".assistant/last-session.md",
    "docs/architecture/*.md",
    "docs/roadmap/*.md",
    "docs/product-plans/released/*.md",
    "artifacts/prds/released/**/*.md",
    "src/core/graph/manifest.json",
)
_DENIED_PARTS = frozenset(
    {
        ".git",
        ".better-product-graph",
        ".ssh",
        ".aws",
        ".gnupg",
        "node_modules",
        "__pycache__",
        "secrets",
        "credentials",
    }
)
_DENIED_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        "credentials.json",
        "secrets.json",
    }
)
_SECRET_CONTENT = re.compile(
    rb"(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"AKIA[0-9A-Z]{16}|"
    rb"(?i:(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*[^\s]{8,}))"
)


def _relative_path(root: Path, path: Path) -> str:
    try:
        managed = assert_managed_path(root, path)
        return managed.relative_to(root.resolve()).as_posix()
    except (IntegrityError, ValueError) as error:
        raise PlanningContextError("planning context source escapes project root or is a symlink") from error


def _sensitive_path(relative: str) -> bool:
    pure = PurePosixPath(relative)
    lowered = pure.name.casefold()
    return (
        any(part.casefold() in _DENIED_PARTS for part in pure.parts)
        or lowered in _DENIED_NAMES
        or lowered.startswith(".env.")
        or lowered.endswith((".pem", ".key", ".p12", ".pfx"))
    )


def _kind(relative: str) -> str:
    lowered = relative.casefold()
    if lowered.startswith("artifacts/prds/released/"):
        return "RELEASED_PRD"
    if "/roadmap" in lowered:
        return "ROADMAP"
    if "/architecture" in lowered or lowered.endswith("/manifest.json"):
        return "ARCHITECTURE"
    if lowered.startswith(".assistant/"):
        return "PROJECT_MEMORY"
    if lowered.startswith("readme") or lowered in {"project.md", "agents.md"}:
        return "PROJECT_OVERVIEW"
    return "PROJECT_CONFIG"


def _version_key(relative: str) -> tuple[int, ...]:
    """Return the final filename version as a tuple suitable for newest-first sorting."""

    matches = re.findall(r"(?:^|[_-])v(\d+(?:\.\d+)*)", PurePosixPath(relative).name, re.I)
    if not matches:
        return (-1,)
    return tuple(int(part) for part in matches[-1].split("."))


def _newest_first(paths: list[str]) -> list[str]:
    return sorted(paths, key=lambda item: (_version_key(item), item.casefold()), reverse=True)


def _candidate_paths(root: Path) -> list[Path]:
    paths = [root / name for name in _ROOT_CANDIDATES]
    for pattern in _DISCOVERY_GLOBS:
        paths.extend(root.glob(pattern))
    unique: dict[str, Path] = {}
    for path in paths:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        unique.setdefault(relative, path)
    priority = {
        "PROJECT_OVERVIEW": 0,
        "PROJECT_MEMORY": 1,
        "ROADMAP": 2,
        "ARCHITECTURE": 3,
        "RELEASED_PRD": 4,
        "PROJECT_CONFIG": 5,
    }
    grouped: dict[str, list[str]] = {kind: [] for kind in priority}
    for relative in unique:
        grouped[_kind(relative)].append(relative)
    for kind in grouped:
        grouped[kind] = _newest_first(grouped[kind])

    # Reserve the first positions for one current representative of every important
    # product context class. Otherwise a long Roadmap history can consume the bounded
    # budget before the current architecture, Graph manifest, or Released PRD is seen.
    representatives: list[str] = []
    overview = next(
        (item for item in grouped["PROJECT_OVERVIEW"] if item.casefold() == "readme.md"),
        grouped["PROJECT_OVERVIEW"][0] if grouped["PROJECT_OVERVIEW"] else None,
    )
    memory = next(
        (item for item in grouped["PROJECT_MEMORY"] if item == ".assistant/project.md"),
        grouped["PROJECT_MEMORY"][0] if grouped["PROJECT_MEMORY"] else None,
    )
    newest_roadmap = grouped["ROADMAP"][0] if grouped["ROADMAP"] else None
    newest_architecture = next(
        (item for item in grouped["ARCHITECTURE"] if item != "src/core/graph/manifest.json"),
        None,
    )
    graph_manifest = (
        "src/core/graph/manifest.json"
        if "src/core/graph/manifest.json" in grouped["ARCHITECTURE"]
        else None
    )
    newest_released_prd = grouped["RELEASED_PRD"][0] if grouped["RELEASED_PRD"] else None
    for item in (
        overview,
        memory,
        newest_roadmap,
        newest_architecture,
        graph_manifest,
        newest_released_prd,
    ):
        if item is not None and item not in representatives:
            representatives.append(item)

    remaining = [
        item
        for kind in sorted(priority, key=priority.get)
        for item in grouped[kind]
        if item not in representatives
    ]
    return [unique[item] for item in representatives + remaining]


def discover_planning_context(project_root: Path) -> dict[str, Any]:
    """Return bounded safe material identities; never return material contents."""

    root = project_root.resolve()
    available: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    total_bytes = 0
    truncated_materials = 0

    explicit_sensitive = [
        path
        for path in root.iterdir()
        if path.name.casefold() in _DENIED_NAMES or path.name.casefold().startswith(".env.")
    ]
    for path in explicit_sensitive:
        skipped.append({"path": path.name, "status": "SKIPPED_SENSITIVE"})

    for path in _candidate_paths(root):
        try:
            relative = _relative_path(root, path)
        except PlanningContextError:
            skipped.append({"path": path.name, "status": "SKIPPED_UNSAFE_PATH"})
            continue
        if _sensitive_path(relative):
            skipped.append({"path": relative, "status": "SKIPPED_SENSITIVE"})
            continue
        if not path.is_file() or path.is_symlink():
            continue
        if len(available) >= MAX_DISCOVERED_MATERIALS:
            skipped.append({"path": relative, "status": "SKIPPED_MATERIAL_LIMIT"})
            truncated_materials += 1
            continue
        size = path.stat().st_size
        if size > MAX_MATERIAL_BYTES or total_bytes + size > MAX_TOTAL_BYTES:
            skipped.append({"path": relative, "status": "SKIPPED_SIZE_LIMIT"})
            continue
        data = path.read_bytes()
        if b"\x00" in data[:8192]:
            skipped.append({"path": relative, "status": "SKIPPED_BINARY"})
            continue
        if _SECRET_CONTENT.search(data):
            skipped.append({"path": relative, "status": "SKIPPED_SENSITIVE"})
            continue
        available.append(
            {
                "ref": {
                    "role": "planning_context_source",
                    "path": relative,
                    "hash": sha256_file(path),
                    "version": 1,
                },
                "kind": _kind(relative),
                "size": size,
                "status": "AVAILABLE",
            }
        )
        total_bytes += size

    return {
        "schema_version": "planning-context-discovery.v1",
        "project_identity": {
            "name": root.name,
            "root": ".",
            "confidence": "HIGH",
        },
        "available_materials": available,
        "skipped_materials": skipped,
        "limits": {
            "max_materials": MAX_DISCOVERED_MATERIALS,
            "max_material_bytes": MAX_MATERIAL_BYTES,
            "max_total_bytes": MAX_TOTAL_BYTES,
            "truncated_materials": truncated_materials,
        },
        "scope": "CURRENT_RUN_ONLY",
    }


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlanningContextError(f"{label} must be an object")
    return value


def _exact_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise PlanningContextError(f"{label} contains unknown field {extra[0]}")


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlanningContextError(f"{label} must be a non-empty string")
    return value


def _canonical_ref(ref: Any) -> tuple[str, str, int | str]:
    value = _require_object(ref, "material ref")
    _exact_keys(value, {"role", "path", "hash", "version"}, "material ref")
    if value.get("role") != "planning_context_source":
        raise PlanningContextError("material ref role must be planning_context_source")
    path = _require_nonempty_string(value.get("path"), "material ref path")
    digest = _require_nonempty_string(value.get("hash"), "material ref hash")
    version = value.get("version")
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise PlanningContextError("material ref hash must be an exact sha256")
    if isinstance(version, bool) or not (
        isinstance(version, int) and version > 0
        or isinstance(version, str) and bool(version.strip())
    ):
        raise PlanningContextError("material ref version is invalid")
    if _sensitive_path(path):
        raise PlanningContextError(f"sensitive planning context source is forbidden: {path}")
    return path, digest, version


def validate_planning_context_submission(result: dict[str, Any]) -> None:
    """Validate one Agent-authored Run context without inventing its semantics."""

    output = _require_object(result.get("semantic_output"), "planning context semantic_output")
    required = {
        "schema_version",
        "status",
        "project_identity",
        "materials",
        "unavailable_sources",
        "high_impact_gaps",
        "context_summary",
        "review",
        "limitations",
        "next_action",
    }
    _exact_keys(output, required, "planning context semantic_output")
    missing = sorted(required - set(output))
    if missing:
        raise PlanningContextError(f"planning context semantic_output requires {missing[0]}")
    if output["schema_version"] != "planning-context-preparation.v1":
        raise PlanningContextError("planning context schema_version is invalid")
    if output["status"] not in {"READY", "LIMITED", "SKIPPED"}:
        raise PlanningContextError("planning context status must be READY, LIMITED, or SKIPPED")
    if output["next_action"] != "evidence.collect":
        raise PlanningContextError("planning context next_action must be evidence.collect")

    identity = _require_object(output["project_identity"], "project_identity")
    _exact_keys(identity, {"name", "root", "confidence", "ambiguities"}, "project_identity")
    _require_nonempty_string(identity.get("name"), "project_identity name")
    if identity.get("root") != ".":
        raise PlanningContextError("project_identity root must be the current project root")
    if identity.get("confidence") not in {"HIGH", "MEDIUM", "LOW"}:
        raise PlanningContextError("project_identity confidence is invalid")
    if not isinstance(identity.get("ambiguities"), list):
        raise PlanningContextError("project_identity ambiguities must be a list")

    materials = output["materials"]
    if not isinstance(materials, list) or len(materials) > MAX_DISCOVERED_MATERIALS:
        raise PlanningContextError("planning context materials exceed the bounded list")
    included: list[tuple[str, str, int | str]] = []
    for item in materials:
        material = _require_object(item, "material")
        _exact_keys(material, {"ref", "kind", "decision", "reason"}, "material")
        identity_ref = _canonical_ref(material.get("ref"))
        _require_nonempty_string(material.get("kind"), "material kind")
        if material.get("decision") not in {"INCLUDE", "EXCLUDE"}:
            raise PlanningContextError("material decision must be INCLUDE or EXCLUDE")
        _require_nonempty_string(material.get("reason"), "material reason")
        if material["decision"] == "INCLUDE":
            included.append(identity_ref)
    if len(included) != len(set(included)):
        raise PlanningContextError("planning context contains duplicate included material refs")

    artifact_refs = result.get("artifact_refs")
    if not isinstance(artifact_refs, list):
        raise PlanningContextError("planning context artifact_refs must be a list")
    bound = [_canonical_ref(item) for item in artifact_refs]
    if sorted(bound) != sorted(included):
        raise PlanningContextError(
            "planning context artifact_refs must exactly equal included material refs"
        )

    for label in ("unavailable_sources", "high_impact_gaps", "limitations"):
        if not isinstance(output[label], list):
            raise PlanningContextError(f"{label} must be a list")
    summary = _require_object(output["context_summary"], "context_summary")
    _exact_keys(
        summary,
        {"project_purpose", "current_direction", "constraints", "unknowns"},
        "context_summary",
    )
    _require_nonempty_string(summary.get("project_purpose"), "context_summary project_purpose")
    _require_nonempty_string(summary.get("current_direction"), "context_summary current_direction")
    if not isinstance(summary.get("constraints"), list) or not isinstance(
        summary.get("unknowns"), list
    ):
        raise PlanningContextError("context_summary constraints and unknowns must be lists")

    review = _require_object(output["review"], "review")
    _exact_keys(review, {"status", "reviewed_by"}, "review")
    expected_review = {
        "READY": "CONFIRMED",
        "LIMITED": "LIMITED_CONTINUE",
        "SKIPPED": "SKIPPED",
    }[output["status"]]
    if review.get("status") != expected_review:
        raise PlanningContextError(
            f"planning context {output['status']} requires review status {expected_review}"
        )
    reviewer = _require_object(review.get("reviewed_by"), "reviewed_by")
    _exact_keys(reviewer, {"kind", "id"}, "reviewed_by")
    if reviewer.get("kind") not in {"OWNER", "HOST_AGENT"}:
        raise PlanningContextError("reviewed_by kind is invalid")
    _require_nonempty_string(reviewer.get("id"), "reviewed_by id")
    if output["status"] == "READY" and not included:
        raise PlanningContextError("READY planning context requires at least one included material")
