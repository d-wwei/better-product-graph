"""Closed exact asset-change input for Agent-authored PRD Candidates."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .storage import IntegrityError, assert_managed_path, sha256_bytes


class PRDAssetChangeError(ValueError):
    """A PRD asset change is ambiguous, unsafe, or not exact."""


def _safe_relative_name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PRDAssetChangeError(f"{label} must be a non-empty relative asset name")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {".", ".."} for part in pure.parts)
        or pure.parts[0] == "assets"
        or "\\" in value
        or any(character in value for character in ("\0", "%", "?", "#"))
    ):
        raise PRDAssetChangeError(f"{label} is unsafe")
    return pure.as_posix()


def _destination(value: Any, label: str) -> str:
    destination = _safe_relative_name(value, label)
    lowered = destination.casefold()
    if not (lowered.endswith(".svg") or lowered.endswith("@2x.png")):
        raise PRDAssetChangeError(
            f"{label} must end with .svg or @2x.png"
        )
    return destination


def _read_exact_source(root: Path, value: Any, label: str) -> bytes:
    if not isinstance(value, dict) or set(value) != {"path", "hash", "version"}:
        raise PRDAssetChangeError(f"{label} must be one closed exact ref")
    raw_path = value.get("path")
    expected_hash = value.get("hash")
    version = value.get("version")
    if (
        not isinstance(raw_path, str)
        or not raw_path
        or not isinstance(expected_hash, str)
        or not expected_hash.startswith("sha256:")
    ):
        raise PRDAssetChangeError(f"{label} requires exact path/hash/version")
    if isinstance(version, bool) or not (
        isinstance(version, int) and version >= 1
        or isinstance(version, str) and bool(version.strip())
    ):
        raise PRDAssetChangeError(
            f"{label}.version must be a positive integer or non-blank string"
        )
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts or "\\" in raw_path:
        raise PRDAssetChangeError(f"{label}.path is unsafe")
    try:
        path = assert_managed_path(root, root / Path(*relative.parts))
    except IntegrityError as error:
        raise PRDAssetChangeError(f"{label}.path is outside safe project input") from error
    if path.is_symlink() or not path.is_file():
        raise PRDAssetChangeError(f"{label} must be a regular non-symlink file")
    payload = path.read_bytes()
    if sha256_bytes(payload) != expected_hash:
        raise PRDAssetChangeError(f"{label}.hash differs from exact source bytes")
    return payload


def apply_prd_asset_change_set(
    project_root: Path,
    base_assets: Mapping[str, bytes],
    change_set: Any,
) -> dict[str, bytes]:
    """Apply one closed v1 change set; final visual pairing is archived separately."""

    assets = {
        _safe_relative_name(name, "base asset destination"): bytes(payload)
        for name, payload in base_assets.items()
    }
    if change_set is None:
        return assets
    if not isinstance(change_set, dict) or set(change_set) != {
        "schema_version",
        "upsert",
        "remove",
    }:
        raise PRDAssetChangeError(
            "asset_change_set must contain exactly schema_version, upsert and remove"
        )
    if change_set.get("schema_version") != "prd-asset-change-set.v1":
        raise PRDAssetChangeError(
            "asset_change_set.schema_version must be prd-asset-change-set.v1"
        )
    upsert = change_set.get("upsert")
    remove = change_set.get("remove")
    if not isinstance(upsert, list) or not isinstance(remove, list):
        raise PRDAssetChangeError("asset_change_set upsert and remove must be lists")
    removals = [
        _destination(value, f"asset_change_set.remove[{index}]")
        for index, value in enumerate(remove)
    ]
    if len(removals) != len(set(removals)):
        raise PRDAssetChangeError("asset_change_set.remove contains duplicate destinations")
    additions: dict[str, bytes] = {}
    for index, raw in enumerate(upsert):
        label = f"asset_change_set.upsert[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"destination", "source_ref"}:
            raise PRDAssetChangeError(
                f"{label} must contain exactly destination and source_ref"
            )
        destination = _destination(raw.get("destination"), f"{label}.destination")
        if destination in additions:
            raise PRDAssetChangeError(
                f"asset_change_set.upsert duplicates destination {destination}"
            )
        additions[destination] = _read_exact_source(
            project_root.resolve(), raw.get("source_ref"), f"{label}.source_ref"
        )
    conflict = sorted(set(removals) & set(additions))
    if conflict:
        raise PRDAssetChangeError(
            f"asset_change_set cannot remove and upsert {conflict[0]}"
        )
    for destination in removals:
        if destination not in assets:
            raise PRDAssetChangeError(
                f"asset_change_set.remove target does not exist: {destination}"
            )
        del assets[destination]
    assets.update(additions)
    return assets
