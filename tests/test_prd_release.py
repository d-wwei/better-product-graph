from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.documents import (
    ImmutableArtifactError,
    archive_prd_candidate,
    hash_tree,
    release_prd_candidate,
)
from src.bpg.failpoints import InjectedCrash, crash_at
from src.bpg.prd_contract import assemble_prd
from src.bpg.templates import TemplateRegistry
from tests.test_prd_contract import REPO_ROOT, TEMPLATES, prd_submission


class PRDReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        selection = TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        self.assembled = assemble_prd(prd_submission(), selection)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_archive_and_release_are_self_contained_with_same_stem_assets(self) -> None:
        document = self.assembled.markdown.replace(
            "## 验收标准", "![状态示意](./assets/state.png)\n\n## 验收标准"
        )
        assembled = self.assembled.with_markdown(document)
        archived = archive_prd_candidate(
            self.project, assembled, assets={"state.png": b"PNG-BYTES"}
        )
        released = release_prd_candidate(
            self.project,
            archived,
            ready_assertion={"status": "READY", "candidate_hash": archived.document_hash},
        )

        expected_stem = "PRD-CHECKOUT-001_结算恢复体验_v0.1_2026-08-20"
        self.assertEqual(archived.path.name, expected_stem)
        self.assertTrue((archived.path / f"{expected_stem}.md").is_file())
        self.assertTrue((archived.path / f"{expected_stem}.review.json").is_file())
        self.assertTrue((archived.path / "assets" / "state.png").is_file())
        self.assertTrue((released.path / f"{expected_stem}.md").is_file())
        self.assertTrue((released.path / f"{expected_stem}.review.json").is_file())
        self.assertTrue((released.path / "assets" / "state.png").is_file())
        self.assertEqual(hash_tree(released.path), released.tree_hash)

    def test_empty_assets_directory_is_omitted(self) -> None:
        archived = archive_prd_candidate(self.project, self.assembled, assets={})
        self.assertFalse((archived.path / "assets").exists())

    def test_release_is_exactly_idempotent_and_never_overwrites_conflicting_directory(self) -> None:
        archived = archive_prd_candidate(self.project, self.assembled, assets={})
        first = release_prd_candidate(
            self.project,
            archived,
            ready_assertion={"status": "READY", "candidate_hash": archived.document_hash},
        )
        same = release_prd_candidate(
            self.project,
            archived,
            ready_assertion={"status": "READY", "candidate_hash": archived.document_hash},
        )
        self.assertEqual(first.tree_hash, same.tree_hash)
        self.assertEqual(hash_tree(first.path), first.tree_hash)

    def test_archive_and_release_recover_publish_before_changelog_without_duplicate_entries(self) -> None:
        with self.assertRaises(InjectedCrash):
            archive_prd_candidate(
                self.project,
                self.assembled,
                assets={},
                failpoint=crash_at("after_archive_publish"),
            )
        archived = archive_prd_candidate(self.project, self.assembled, assets={})
        assertion = {"status": "READY", "candidate_hash": archived.document_hash}
        with self.assertRaises(InjectedCrash):
            release_prd_candidate(
                self.project,
                archived,
                ready_assertion=assertion,
                failpoint=crash_at("after_release_publish"),
            )
        released = release_prd_candidate(self.project, archived, ready_assertion=assertion)

        changelog = (self.project / "artifacts/prds/DOCUMENT_CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(changelog.count("CANDIDATE_ARCHIVED"), 1)
        self.assertEqual(changelog.count("RELEASED"), 1)
        self.assertEqual(hash_tree(released.path), released.tree_hash)

    def test_missing_referenced_asset_fails_before_archive_creation(self) -> None:
        assembled = self.assembled.with_markdown(
            self.assembled.markdown + "\n![missing](./assets/missing.png)\n"
        )
        with self.assertRaisesRegex(ImmutableArtifactError, "missing.png"):
            archive_prd_candidate(self.project, assembled, assets={})
        self.assertFalse((self.project / "artifacts" / "prds" / "archived").exists())

    def test_document_changelog_records_archive_and_release_without_rewriting_documents(self) -> None:
        archived = archive_prd_candidate(self.project, self.assembled, assets={})
        before = archived.document_path.read_bytes()
        release_prd_candidate(
            self.project,
            archived,
            ready_assertion={"status": "READY", "candidate_hash": archived.document_hash},
        )
        changelog = self.project / "artifacts" / "prds" / "DOCUMENT_CHANGELOG.md"
        self.assertIn("CANDIDATE_ARCHIVED", changelog.read_text(encoding="utf-8"))
        self.assertIn("RELEASED", changelog.read_text(encoding="utf-8"))
        self.assertEqual(archived.document_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
