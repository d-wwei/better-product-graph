"""Exact project-root Git preflight; never adds, commits, pushes, or creates remotes."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .storage import atomic_write_bytes


class ProjectRootError(ValueError):
    """The requested project root is unsafe or cannot be resolved exactly."""


@dataclass(frozen=True)
class GitPreflight:
    status: str
    project_root: Path
    repository_root: Path | None
    initialized: bool
    reason: str | None = None


GITIGNORE_BASELINE = (
    ".DS_Store",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "__pycache__/",
    "*.py[cod]",
)


def _run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=False
    )


def validate_project_root(
    project_root: Path,
    *,
    forbidden_roots: tuple[Path, ...] = (),
) -> Path:
    resolved = project_root.expanduser().resolve()
    if not resolved.is_dir():
        raise ProjectRootError(f"project root does not exist or is not a directory: {resolved}")
    if resolved in {Path("/"), Path.home().resolve()}:
        raise ProjectRootError(f"broad or home project root is forbidden: {resolved}")
    for forbidden in forbidden_roots:
        boundary = forbidden.expanduser().resolve()
        try:
            resolved.relative_to(boundary)
        except ValueError:
            continue
        raise ProjectRootError(
            f"installed plugin directory cannot be used as project root: {resolved}"
        )
    return resolved


def _ensure_sensitive_gitignore(root: Path) -> None:
    path = root / ".gitignore"
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    merged = list(existing)
    for entry in GITIGNORE_BASELINE:
        if entry not in merged:
            merged.append(entry)
    atomic_write_bytes(path, ("\n".join(merged).rstrip() + "\n").encode())


def preflight_project(
    project_root: Path,
    *,
    forbidden_roots: tuple[Path, ...] = (),
) -> GitPreflight:
    root = validate_project_root(project_root, forbidden_roots=forbidden_roots)
    existing = _run_git(root, "rev-parse", "--show-toplevel")
    if existing.returncode == 0:
        repository = Path(existing.stdout.strip()).resolve()
        return GitPreflight("READY", root, repository, False)

    initialized = _run_git(root, "init", "-b", "main")
    if initialized.returncode != 0:
        return GitPreflight(
            "DEGRADED",
            root,
            None,
            False,
            reason=initialized.stderr.strip() or "git init failed",
        )
    _ensure_sensitive_gitignore(root)
    repository = Path(_run_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    return GitPreflight("READY", root, repository, True)
