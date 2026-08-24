#!/usr/bin/env python3
"""Freeze the accepted PRD writing profile into the BPG runtime registry."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bpg.document_experience_profile import (
    DocumentExperienceProfileError,
    resolve_prd_document_experience,
)
from src.bpg.storage import sha256_file


class WritingProfilePromotionError(RuntimeError):
    """The frozen source, runtime copy, or registry binding is inconsistent."""


def _atomic_copy(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise WritingProfilePromotionError(f"source must be a regular file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(source.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sync_prd_writing_profile_v02(repo_root: Path, *, check: bool = False) -> dict[str, Any]:
    root = repo_root.resolve()
    source_root = root / "policies/document-experience"
    runtime_root = root / "src/core/policies"
    source_profile = source_root / "PRD_WRITING_PROFILE_v0.2.json"
    source_guide = source_root / "PRD_WRITING_GUIDE_v0.2.md"
    runtime_profile = runtime_root / "prd-writing-profile-v0.2.json"
    runtime_guide = runtime_root / "prd-writing-guide-v0.2.md"
    previous_profile = source_root / "PRD_WRITING_PROFILE_v0.1.json"
    previous_guide = source_root / "PRD_WRITING_GUIDE_v0.1.md"
    previous_runtime_profile = runtime_root / "prd-writing-profile-v0.1.json"
    previous_runtime_guide = runtime_root / "prd-writing-guide-v0.1.md"
    base_policy = runtime_root / "document-experience.json"
    registry_path = runtime_root / "document-experience-profiles.json"
    for path in (source_profile, source_guide, previous_profile, previous_guide, base_policy):
        if path.is_symlink() or not path.is_file():
            raise WritingProfilePromotionError(f"required regular source missing: {path}")

    profile = json.loads(source_profile.read_text(encoding="utf-8"))
    guide_hash = sha256_file(source_guide)
    base_policy_hash = sha256_file(base_policy)
    if (
        profile.get("schema_version") != "document-experience-profile.v1"
        or profile.get("profile_id") != "prd-plain-language-zh-CN"
        or profile.get("profile_version") != "0.2.0"
        or profile.get("status") != "RELEASED"
        or profile.get("runtime_status") != "ACTIVE"
        or profile.get("writing_guide_ref", {}).get("hash") != guide_hash
        or profile.get("base_policy_ref", {}).get("hash") != base_policy_hash
    ):
        raise WritingProfilePromotionError("released writing profile source contract is invalid")

    if not check:
        _atomic_copy(source_profile, runtime_profile)
        _atomic_copy(source_guide, runtime_guide)
        _atomic_copy(previous_profile, previous_runtime_profile)
        _atomic_copy(previous_guide, previous_runtime_guide)
    if (
        not runtime_profile.is_file()
        or runtime_profile.is_symlink()
        or runtime_profile.read_bytes() != source_profile.read_bytes()
    ):
        raise WritingProfilePromotionError("runtime PRD writing profile differs from human source")
    if (
        not runtime_guide.is_file()
        or runtime_guide.is_symlink()
        or runtime_guide.read_bytes() != source_guide.read_bytes()
    ):
        raise WritingProfilePromotionError("runtime PRD writing guide differs from human source")

    expected_registry = {
        "schema_version": "document-experience-profile-registry.v1",
        "default_profiles": {
            "prd": {"id": "prd-plain-language-zh-CN", "version": "0.2.0"}
        },
        "profiles": [
            {
                "id": "prd-plain-language-zh-CN",
                "version": "0.1.0",
                "status": "RELEASED_PREVIOUS",
                "artifact_type": "PRD",
                "profile_path": "prd-writing-profile-v0.1.json",
                "profile_sha256": sha256_file(previous_profile),
                "writing_guide_path": "prd-writing-guide-v0.1.md",
                "writing_guide_sha256": sha256_file(previous_guide),
                "base_policy_path": "document-experience.json",
                "base_policy_sha256": base_policy_hash,
                "base_policy_version": "document-experience.v1",
            },
            {
                "id": "prd-plain-language-zh-CN",
                "version": "0.2.0",
                "status": "RELEASED_DEFAULT",
                "artifact_type": "PRD",
                "profile_path": "prd-writing-profile-v0.2.json",
                "profile_sha256": sha256_file(source_profile),
                "writing_guide_path": "prd-writing-guide-v0.2.md",
                "writing_guide_sha256": guide_hash,
                "base_policy_path": "document-experience.json",
                "base_policy_sha256": base_policy_hash,
                "base_policy_version": "document-experience.v1",
            }
        ],
    }
    if check:
        if (
            not registry_path.is_file()
            or registry_path.is_symlink()
            or json.loads(registry_path.read_text(encoding="utf-8")) != expected_registry
        ):
            raise WritingProfilePromotionError("released writing profile registry differs")
    else:
        registry_path.write_bytes(_canonical_json(expected_registry) + b"\n")

    try:
        binding = resolve_prd_document_experience(runtime_root)
    except DocumentExperienceProfileError as error:
        raise WritingProfilePromotionError(
            f"released writing profile runtime binding is invalid: {error}"
        ) from error
    return {
        "status": "PASS",
        "stage": "RELEASED_DEFAULT",
        "profile_id": binding["profile_ref"]["id"],
        "profile_version": binding["profile_ref"]["version"],
        "profile_sha256": binding["profile_ref"]["hash"],
        "writing_guide_sha256": binding["writing_guide_ref"]["hash"],
        "user_readability_validation": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = sync_prd_writing_profile_v02(args.repo, check=args.check)
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
