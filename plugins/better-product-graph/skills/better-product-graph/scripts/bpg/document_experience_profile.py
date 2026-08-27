"""Resolve immutable Document Experience bindings for PRD generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import read_json, sha256_file


class DocumentExperienceProfileError(ValueError):
    """The installed policy, profile, guide, or registry identity is invalid."""


def _installed_policy_root() -> Path:
    module = Path(__file__).resolve()
    candidates = (
        module.parents[1] / "core" / "policies",
        module.parents[2] / "references" / "policies",
    )
    for candidate in candidates:
        if candidate.is_dir() and not candidate.is_symlink():
            return candidate
    raise DocumentExperienceProfileError("Document Experience policy root is missing")


def _regular_file(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise DocumentExperienceProfileError(f"{label} escapes policy root") from error
    if not path.is_file() or path.is_symlink():
        raise DocumentExperienceProfileError(f"{label} is missing")
    return path


def _exact_ref(path: Path, *, logical_name: str, version: str, **extra: Any) -> dict[str, Any]:
    return {
        "path": f"references/policies/{logical_name}",
        "hash": sha256_file(path),
        "version": version,
        **extra,
    }


def resolve_prd_document_experience(policy_root: Path | None = None) -> dict[str, Any]:
    """Return the exact released PRD writing policy/profile/guide binding."""

    root = (policy_root or _installed_policy_root()).resolve()
    registry_path = _regular_file(
        root, "document-experience-profiles.json", "Document Experience profile registry"
    )
    registry = read_json(registry_path)
    if registry.get("schema_version") != "document-experience-profile-registry.v1":
        raise DocumentExperienceProfileError(
            "Document Experience profile registry schema is invalid"
        )
    expected_default = registry.get("default_profiles", {}).get("prd")
    if (
        not isinstance(expected_default, dict)
        or expected_default.get("id") != "prd-plain-language-zh-CN"
        or not isinstance(expected_default.get("version"), str)
        or not expected_default["version"]
    ):
        raise DocumentExperienceProfileError(
            "released PRD writing profile is not the exact registry default"
        )
    matches = [
        item
        for item in registry.get("profiles", [])
        if isinstance(item, dict)
        and item.get("id") == expected_default["id"]
        and item.get("version") == expected_default["version"]
    ]
    if len(matches) != 1:
        raise DocumentExperienceProfileError(
            "released PRD writing profile must exist exactly once"
        )
    selected = matches[0]
    if selected.get("status") != "RELEASED_DEFAULT":
        raise DocumentExperienceProfileError(
            "released PRD writing profile registry status is invalid"
        )

    policy_path = _regular_file(root, selected.get("base_policy_path", ""), "base policy")
    profile_path = _regular_file(root, selected.get("profile_path", ""), "writing profile")
    guide_path = _regular_file(root, selected.get("writing_guide_path", ""), "writing guide")
    exact_hashes = {
        "base_policy_sha256": sha256_file(policy_path),
        "profile_sha256": sha256_file(profile_path),
        "writing_guide_sha256": sha256_file(guide_path),
    }
    for field, actual in exact_hashes.items():
        if selected.get(field) != actual:
            raise DocumentExperienceProfileError(
                f"released PRD writing profile registry hash differs: {field}"
            )

    policy = read_json(policy_path)
    profile = read_json(profile_path)
    if policy.get("schema_version") != selected.get("base_policy_version"):
        raise DocumentExperienceProfileError("base policy version differs from registry")
    immutable_evaluated_promotion = (
        selected.get("lifecycle_authority")
        == "REGISTRY_PROMOTION_OVER_IMMUTABLE_EVALUATED_ARTIFACT"
        and expected_default["version"] == "0.5.0"
        and profile.get("status") == "CANDIDATE"
        and profile.get("runtime_status") == "CANDIDATE_NON_DEFAULT"
    )
    if (
        profile.get("schema_version") != "document-experience-profile.v1"
        or profile.get("profile_id") != selected["id"]
        or profile.get("profile_version") != expected_default["version"]
        or (
            not immutable_evaluated_promotion
            and (
                profile.get("status") != "RELEASED"
                or profile.get("runtime_status") != "ACTIVE"
            )
        )
        or profile.get("artifact_type") != "PRD"
        or profile.get("template_independent") is not True
    ):
        raise DocumentExperienceProfileError("released PRD writing profile is invalid")
    if profile.get("base_policy_ref") != {
        "path": "references/policies/document-experience.json",
        "schema_version": selected["base_policy_version"],
        "hash": exact_hashes["base_policy_sha256"],
    }:
        raise DocumentExperienceProfileError("writing profile base policy binding is invalid")
    if profile.get("writing_guide_ref") != {
        "path": f"references/policies/{selected['writing_guide_path']}",
        "version": expected_default["version"],
        "hash": exact_hashes["writing_guide_sha256"],
    }:
        raise DocumentExperienceProfileError("writing profile guide binding is invalid")

    return {
        "schema_version": "prd-document-experience-binding.v1",
        "base_policy_ref": _exact_ref(
            policy_path,
            logical_name="document-experience.json",
            version=selected["base_policy_version"],
        ),
        "profile_ref": _exact_ref(
            profile_path,
            logical_name=selected["profile_path"],
            version=expected_default["version"],
            id=selected["id"],
        ),
        "writing_guide_ref": _exact_ref(
            guide_path,
            logical_name=selected["writing_guide_path"],
            version=expected_default["version"],
        ),
    }
