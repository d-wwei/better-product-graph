#!/usr/bin/env python3
"""Build one deterministic, host-specific Better Product Graph Marketplace ZIP."""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_plugin import DEFAULT_HOST, SUPPORTED_HOSTS, build_plugin
from scripts.package_plugin import FIXED_TIME, _entries, _sha256


MARKETPLACE_NAME = "better-product-graph"
PLUGIN_NAME = "better-product-graph"


def _marketplace_contract(host: str) -> tuple[Path, Path, dict[str, Any]]:
    if host == "codex":
        plugin_root = Path("plugins") / PLUGIN_NAME
        manifest_path = Path(".agents") / "plugins" / "marketplace.json"
        manifest = {
            "name": MARKETPLACE_NAME,
            "interface": {"displayName": "Better Product Graph"},
            "plugins": [
                {
                    "name": PLUGIN_NAME,
                    "source": {
                        "source": "local",
                        "path": f"./{plugin_root.as_posix()}",
                    },
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_USE",
                    },
                    "category": "Productivity",
                }
            ],
        }
        return plugin_root, manifest_path, manifest
    if host == "claude":
        plugin_root = Path("claude-plugins") / PLUGIN_NAME
        manifest_path = Path(".claude-plugin") / "marketplace.json"
        manifest = {
            "name": MARKETPLACE_NAME,
            "description": "Better Product Graph official Developer Alpha marketplace.",
            "owner": {"name": "eli and Better Product Graph contributors"},
            "plugins": [
                {
                    "name": PLUGIN_NAME,
                    "source": f"./{plugin_root.as_posix()}",
                    "description": "Turn product signals into auditable decisions, plans, PRDs, and local handoffs.",
                }
            ],
        }
        return plugin_root, manifest_path, manifest
    raise ValueError(f"unsupported host target: {host}")


def build_marketplace(repo_root: Path, output_root: Path, *, host: str) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    plugin_relative, manifest_relative, marketplace = _marketplace_contract(host)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    plugin = build_plugin(repo_root, output_root / plugin_relative, host=host)
    manifest_path = output_root / manifest_relative
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(marketplace, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    for name in ("LICENSE", "NOTICE"):
        source = repo_root / name
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"required release file missing or unsafe: {name}")
        shutil.copyfile(source, output_root / name)
    return {
        "host": host,
        "marketplace": MARKETPLACE_NAME,
        "manifest_path": manifest_relative.as_posix(),
        "plugin_path": plugin_relative.as_posix(),
        "plugin": plugin,
    }


def package_marketplace(
    repo_root: Path,
    output_zip: Path,
    *,
    host: str = DEFAULT_HOST,
    require_clean: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_zip = output_zip.resolve()
    with tempfile.TemporaryDirectory(prefix=f"bpg-{host}-marketplace-") as directory:
        marketplace_root = Path(directory) / "marketplace"
        built = build_marketplace(repo_root, marketplace_root, host=host)
        plugin = built["plugin"]
        if require_clean and plugin["git"]["dirty"]:
            raise ValueError("release marketplace requires a clean exact Git commit")
        entries = _entries(marketplace_root)
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
        "host": host,
        "marketplace": MARKETPLACE_NAME,
        "plugin_path": built["plugin_path"],
        "git": plugin["git"],
        "artifact_hash": plugin["artifact_hash"],
        "core_tree_fingerprint": plugin["core_tree_fingerprint"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_zip", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--host", choices=SUPPORTED_HOSTS, default=DEFAULT_HOST)
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = package_marketplace(
            args.repo,
            args.output_zip,
            host=args.host,
            require_clean=args.require_clean,
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
