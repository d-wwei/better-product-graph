from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.bpg.git_preflight import ProjectRootError, preflight_project


def git_toplevel(path: Path) -> Path:
    output = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return Path(output).resolve()


class GitPreflightTests(unittest.TestCase):
    def test_initializes_only_exact_non_git_project_and_does_not_commit_or_add_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "product-a"
            project.mkdir()

            result = preflight_project(project)

            self.assertEqual(result.status, "READY")
            self.assertTrue(result.initialized)
            self.assertEqual(git_toplevel(project), project.resolve())
            self.assertTrue((project / ".gitignore").is_file())
            self.assertEqual(
                subprocess.run(
                    ["git", "remote"], cwd=project, check=True, capture_output=True, text=True
                ).stdout,
                "",
            )
            self.assertNotEqual(
                subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD"],
                    cwd=project,
                    capture_output=True,
                    text=True,
                ).returncode,
                0,
            )

    def test_reuses_containing_repository_without_nested_git(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "repository"
            child = parent / "products" / "checkout"
            child.mkdir(parents=True)
            subprocess.run(["git", "init", "-b", "main"], cwd=parent, check=True, capture_output=True)

            result = preflight_project(child)

            self.assertFalse(result.initialized)
            self.assertEqual(result.repository_root, parent.resolve())
            self.assertFalse((child / ".git").exists())

    def test_rejects_home_or_filesystem_root_as_project(self) -> None:
        for unsafe in (Path.home(), Path("/")):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(ProjectRootError):
                    preflight_project(unsafe)

    def test_failed_git_init_leaves_existing_project_files_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "product-a"
            project.mkdir()
            existing = project / ".gitignore"
            existing.write_bytes(b"existing-rule\n")

            responses = [
                subprocess.CompletedProcess(["git"], 128, "", "not a repository"),
                subprocess.CompletedProcess(["git"], 1, "", "simulated init failure"),
            ]
            with patch("src.bpg.git_preflight._run_git", side_effect=responses):
                result = preflight_project(project)

            self.assertEqual(result.status, "DEGRADED")
            self.assertEqual(existing.read_bytes(), b"existing-rule\n")
            self.assertFalse((project / ".git").exists())


if __name__ == "__main__":
    unittest.main()
