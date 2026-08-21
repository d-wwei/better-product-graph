#!/usr/bin/env python3
"""Deterministically sync the accepted PRD V0.2 source into the runtime registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bpg.templates import TemplateContractError, TemplateRegistry


class TemplatePromotionError(RuntimeError):
    """The human source, runtime copy, or registry provenance is inconsistent."""


def _hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_copy(source: Path, target: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise TemplatePromotionError(f"source must be a regular file: {source}")
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


def _profile(registry: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in registry.get("profiles", [])
        if item.get("id") == "general" and item.get("version") == "0.2.0"
    ]
    if len(matches) != 1:
        raise TemplatePromotionError("general@0.2.0 must exist exactly once")
    return matches[0]


def sync_prd_template_v02(
    repo_root: Path,
    *,
    check: bool = False,
    activate_default: bool = False,
    activation_evidence: Path | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    if activate_default:
        raise TemplatePromotionError(
            "general@0.2.0 is already the released default; use --check to verify it"
        )
    source_template = root / "templates/prd/general/PRD_TEMPLATE_v0.2.md"
    source_contract = root / "templates/prd/general/OUTPUT_CONTRACT_v0.2.json"
    runtime_template = root / "src/core/templates/general/PRD_TEMPLATE_v0.2.md"
    runtime_contract = root / "src/core/templates/contracts/prd-v0.2.json"
    registry_path = root / "src/core/templates/profiles.json"
    for path in (source_template, source_contract, registry_path):
        if path.is_symlink() or not path.is_file():
            raise TemplatePromotionError(f"required regular source missing: {path}")

    if not check:
        _atomic_copy(source_template, runtime_template)
        _atomic_copy(source_contract, runtime_contract)
    if (
        not runtime_template.is_file()
        or runtime_template.is_symlink()
        or runtime_template.read_bytes() != source_template.read_bytes()
    ):
        raise TemplatePromotionError("runtime PRD V0.2 template differs from human source")
    if (
        not runtime_contract.is_file()
        or runtime_contract.is_symlink()
        or runtime_contract.read_bytes() != source_contract.read_bytes()
    ):
        raise TemplatePromotionError("runtime PRD V0.2 output contract differs from human source")

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    profile = _profile(registry)
    template_hash = _hash(source_template)
    contract_hash = _hash(source_contract)
    expected = {
        "path": "general/PRD_TEMPLATE_v0.2.md",
        "sha256": template_hash,
        "source_path": "templates/prd/general/PRD_TEMPLATE_v0.2.md",
        "source_sha256": template_hash,
        "output_contract_path": "contracts/prd-v0.2.json",
        "output_contract_sha256": contract_hash,
        "output_contract_version": "better-product-graph.prd.general.0.2",
    }
    if check:
        for key, value in expected.items():
            if profile.get(key) != value:
                raise TemplatePromotionError(f"released template registry binding differs: {key}")
    else:
        profile.update(expected)

    if not check:
        registry_path.write_bytes(_canonical_json(registry) + b"\n")

    try:
        selected = TemplateRegistry(runtime_template.parents[1]).validate_release_governance()
    except Exception as error:
        raise TemplatePromotionError(f"Released template governance or output contract invalid: {error}") from error
    if selected.sha256 != template_hash or selected.output_contract_sha256 != contract_hash:
        raise TemplatePromotionError("Released template identity differs from human sources")

    return {
        "status": "PASS",
        "stage": "RELEASED_DEFAULT",
        "default_activation_status": "ACTIVE",
        "template_sha256": template_hash,
        "output_contract_sha256": contract_hash,
        "authenticated_host_agent_status": "NOT_ASSERTED_BY_TEMPLATE_SYNC",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--activate-default", action="store_true")
    parser.add_argument("--activation-evidence", type=Path)
    args = parser.parse_args()
    try:
        result = sync_prd_template_v02(
            args.repo,
            check=args.check,
            activate_default=args.activate_default,
            activation_evidence=args.activation_evidence,
        )
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
