#!/usr/bin/env python3
"""Build and package one deterministic Better Product Graph Plugin ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_plugin import (
    DEFAULT_HOST,
    SUPPORTED_HOSTS,
    build_plugin,
    verify_installed_identity,
)


FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _entries(plugin_root: Path) -> list[tuple[str, Path | None]]:
    entries: dict[str, Path | None] = {}
    for path in sorted(plugin_root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink is not packageable: {path.relative_to(plugin_root)}")
        relative = path.relative_to(plugin_root).as_posix()
        if "__pycache__" in path.relative_to(plugin_root).parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_dir():
            entries[relative + "/"] = None
        elif path.is_file():
            entries[relative] = path
        else:
            raise ValueError(f"unsupported package member: {relative}")
    return sorted(entries.items())


def package_plugin(
    repo_root: Path,
    output_zip: Path,
    *,
    require_clean: bool = False,
    host: str = DEFAULT_HOST,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_zip = output_zip.resolve()
    with tempfile.TemporaryDirectory(prefix="bpg-package-") as directory:
        plugin_root = Path(directory) / "plugin"
        manifest = build_plugin(repo_root, plugin_root, host=host)
        if require_clean and manifest["git"]["dirty"]:
            raise ValueError("release package requires a clean exact Git commit")
        identity = verify_installed_identity(plugin_root)
        if not identity["valid"]:
            raise ValueError("built Plugin identity failed: " + "; ".join(identity["errors"]))
        entries = _entries(plugin_root)
        output_zip.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_zip.with_name(output_zip.name + ".tmp")
        try:
            with zipfile.ZipFile(
                temporary,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
                strict_timestamps=True,
            ) as archive:
                for relative, path in entries:
                    info = zipfile.ZipInfo(relative, FIXED_TIME)
                    info.create_system = 3
                    info.compress_type = zipfile.ZIP_DEFLATED
                    if path is None:
                        info.external_attr = (stat.S_IFDIR | 0o755) << 16
                        archive.writestr(info, b"")
                    else:
                        executable = bool(path.stat().st_mode & stat.S_IXUSR)
                        info.external_attr = (
                            stat.S_IFREG | (0o755 if executable else 0o644)
                        ) << 16
                        archive.writestr(
                            info,
                            path.read_bytes(),
                            compress_type=zipfile.ZIP_DEFLATED,
                            compresslevel=9,
                        )
            temporary.replace(output_zip)
        finally:
            if temporary.exists():
                temporary.unlink()
    return {
        "status": "PASS",
        "path": str(output_zip),
        "sha256": _sha256(output_zip),
        "bytes": output_zip.stat().st_size,
        "entries": len(entries),
        "plugin": manifest["plugin"],
        "host": manifest["host"]["host_id"],
        "git": manifest["git"],
        "artifact_hash": manifest["artifact_hash"],
        "core_tree_fingerprint": manifest["core_tree_fingerprint"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_zip", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--host", choices=SUPPORTED_HOSTS, default=DEFAULT_HOST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = package_plugin(
            args.repo,
            args.output_zip,
            require_clean=args.require_clean,
            host=args.host,
        )
    except Exception as error:
        if args.json:
            print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False, sort_keys=True))
        else:
            print(f"error: {error}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{result['path']} {result['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
