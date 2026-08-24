#!/usr/bin/env python3
"""Installed Skill bootstrap; semantic product work remains in the Host Agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


# The installed plugin is immutable. Importing its runtime must never create
# bytecode cache files inside the installed tree.
sys.dont_write_bytecode = True


def installed_paths() -> dict[str, str]:
    script = Path(__file__).resolve()
    skill_root = script.parents[1]
    plugin_root = skill_root.parents[1]
    return {
        "plugin_root": str(plugin_root),
        "skill_root": str(skill_root),
        "identity_path": str(plugin_root / "build-manifest.json"),
    }


def with_host_execution_context(
    result: dict[str, object],
    *,
    project_root: Path,
    skill_root: Path,
) -> dict[str, object]:
    dispatch = result.get("dispatch")
    instruction_path: str | None = None
    dispatch_instruction_hash: str | None = None
    installed_instruction_hash: str | None = None
    instruction_compatibility: str | None = None
    if isinstance(dispatch, dict):
        dispatch_instruction_hash = dispatch.get("instruction_hash")
        instruction_ref = dispatch.get("instruction_ref")
        node_id = dispatch.get("node_id")
        if isinstance(instruction_ref, str) and instruction_ref:
            candidate = (skill_root / instruction_ref).resolve()
            try:
                candidate.relative_to(skill_root.resolve())
            except ValueError:
                candidate = Path("/__invalid_instruction_path__")
            if candidate.is_file() and not candidate.is_symlink():
                instruction_path = str(candidate)
                installed_instruction_hash = "sha256:" + hashlib.sha256(
                    candidate.read_bytes()
                ).hexdigest()
                registry_path = skill_root / "references" / "graph" / "node-contracts.json"
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                contract = registry.get("nodes", {}).get(node_id, {})
                if contract.get("instruction_ref") == instruction_ref:
                    if dispatch_instruction_hash == installed_instruction_hash:
                        instruction_compatibility = "EXACT"
                    elif dispatch_instruction_hash in contract.get(
                        "compatible_instruction_hashes", []
                    ):
                        instruction_compatibility = "DECLARED_COMPATIBLE_SUCCESSOR"
                    else:
                        instruction_compatibility = "INCOMPATIBLE"
    result["host_execution_context"] = {
        "project_root": str(project_root.resolve()),
        "skill_root": str(skill_root.resolve()),
        "instruction_path": instruction_path,
        "dispatch_instruction_hash": dispatch_instruction_hash,
        "installed_instruction_hash": installed_instruction_hash,
        "instruction_compatibility": instruction_compatibility,
        "working_directory_rule": (
            "Keep project_root as the working directory for every runner call; "
            "read installed resources through instruction_path and never cd into skill_root."
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Better Product Graph installed Skill bootstrap")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument(
        "--operation",
        choices=("entry", "dispatch", "submit", "owner-choice", "fulfill-evals"),
        default="entry",
    )
    parser.add_argument("--run-id")
    parser.add_argument("--payload-file")
    parser.add_argument("--requested-node")
    parser.add_argument("entry", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    paths = installed_paths()
    skill_root = Path(paths["skill_root"])
    scripts_root = skill_root / "scripts"
    sys.path.insert(0, str(scripts_root))
    if args.self_check:
        from bpg.installed_identity import verify_installed_identity

        result = {**paths, **verify_installed_identity(Path(paths["plugin_root"]))}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["valid"] else 1
    from bpg.installed_identity import verify_installed_identity

    identity = verify_installed_identity(Path(paths["plugin_root"]))
    if not identity["valid"]:
        print(json.dumps({"status": "INSTALLED_IDENTITY_INVALID", **identity}, ensure_ascii=False, sort_keys=True))
        return 1
    if args.operation == "entry" and not args.entry:
        parser.error("A stable Better Product Graph intent is required through the Host Skill")
    if args.operation != "entry" and not args.run_id:
        parser.error("--run-id is required for installed non-entry operations")
    if args.operation in {"submit", "owner-choice", "fulfill-evals"} and not args.payload_file:
        parser.error("--payload-file is required for installed mutation operations")
    from bpg.runner import dispatch, fulfill_evals, handle_entry, owner_choice, submit

    graph = skill_root / "references" / "graph" / "manifest.json"
    if args.operation == "entry":
        entry = " ".join(args.entry)
        if not entry.lstrip().startswith("$better-product-graph"):
            entry = "$better-product-graph " + entry
        result = handle_entry(Path.cwd(), graph, entry, skill_root=skill_root)
    elif args.operation == "dispatch":
        result = dispatch(Path.cwd(), graph, args.run_id, skill_root=skill_root)
    else:
        payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            parser.error("--payload-file must contain one JSON object")
        if args.operation == "submit":
            result = submit(
                Path.cwd(), graph, args.run_id, payload,
                requested_node=args.requested_node, skill_root=skill_root,
            )
        elif args.operation == "owner-choice":
            result = owner_choice(Path.cwd(), graph, args.run_id, payload, skill_root=skill_root)
        else:
            result = fulfill_evals(Path.cwd(), graph, args.run_id, payload, skill_root=skill_root)
    result = with_host_execution_context(
        result,
        project_root=Path.cwd(),
        skill_root=skill_root,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
