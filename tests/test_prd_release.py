from __future__ import annotations

import tempfile
import unittest
import copy
from dataclasses import replace
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
from src.bpg.host_runtime import HostRuntime
from src.bpg.state_controller import TransitionRejected
from src.bpg.storage import atomic_write_json, sha256_file
from tests.controller_fixtures import position_run_internal
from tests.test_writing_review import GRAPH, SKILL_ROOT
from tests.test_prd_contract import REPO_ROOT, TEMPLATES, prd_submission
from tests.test_visual_assets import png, svg


class PRDReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        selection = TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        self.assembled = assemble_prd(prd_submission(), selection)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _v04(self, markdown: str):
        metadata = copy.deepcopy(self.assembled.metadata)
        metadata["document_experience"]["profile_ref"]["version"] = "0.4.0"
        return replace(self.assembled, markdown=markdown, metadata=metadata)

    def _v02(self, markdown: str):
        metadata = copy.deepcopy(self.assembled.metadata)
        metadata["document_experience"]["profile_ref"]["version"] = "0.2.0"
        return replace(self.assembled, markdown=markdown, metadata=metadata)

    def _v05(self, markdown: str):
        metadata = copy.deepcopy(self.assembled.metadata)
        metadata["document_experience"]["profile_ref"]["version"] = "0.5.0"
        return replace(self.assembled, markdown=markdown, metadata=metadata)

    def test_archive_and_release_are_self_contained_with_same_stem_assets(self) -> None:
        document = self.assembled.markdown.replace(
            "## 验收标准", "![状态示意](./assets/state.svg)\n\n## 验收标准"
        )
        assembled = self.assembled.with_markdown(document)
        archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={"state.svg": svg(), "state@2x.png": png()},
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
        self.assertTrue((archived.path / "assets" / "state.svg").is_file())
        self.assertTrue((archived.path / "assets" / "state@2x.png").is_file())
        self.assertTrue((released.path / f"{expected_stem}.md").is_file())
        self.assertTrue((released.path / f"{expected_stem}.review.json").is_file())
        self.assertTrue((released.path / "assets" / "state.svg").is_file())
        self.assertTrue((released.path / "assets" / "state@2x.png").is_file())
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

    def test_reader_visible_visual_pair_is_validated_before_archive_and_preserved_on_release(self) -> None:
        assembled = self._v04(
            self.assembled.markdown + "\n![主流程](./assets/main-flow.svg)\n"
        )
        archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={"main-flow.svg": svg(), "main-flow@2x.png": png()},
        )
        released = release_prd_candidate(
            self.project,
            archived,
            ready_assertion={"status": "READY", "candidate_hash": archived.document_hash},
        )

        self.assertTrue((released.path / "assets/main-flow.svg").is_file())
        self.assertTrue((released.path / "assets/main-flow@2x.png").is_file())

    def test_unsafe_reader_visible_visual_fails_before_archive_creation(self) -> None:
        assembled = self._v04(
            self.assembled.markdown + "\n![主流程](./assets/main-flow.svg)\n"
        )
        with self.assertRaisesRegex(ImmutableArtifactError, "reader-visible SVG"):
            archive_prd_candidate(
                self.project,
                assembled,
                assets={
                    "main-flow.svg": svg(extra="<script>alert(1)</script>"),
                    "main-flow@2x.png": png(),
                },
            )
        self.assertFalse((self.project / "artifacts" / "prds" / "archived").exists())

    def test_v04_archive_rejects_raw_inline_and_even_backslash_unsafe_svg(self) -> None:
        cases = {
            "raw inline SVG": (
                self.assembled.markdown
                + '\n<svg xmlns="http://www.w3.org/2000/svg"><script>x</script></svg>\n',
                {},
            ),
            "reader-visible SVG": (
                self.assembled.markdown
                + r"\n\\![unsafe](./assets/unsafe.svg)"
                + "\n",
                {
                    "unsafe.svg": svg(extra="<script>x</script>"),
                    "unsafe@2x.png": png(),
                },
            ),
        }
        for expected, (markdown, assets) in cases.items():
            project = self.project / expected.replace(" ", "-")
            with self.subTest(expected=expected), self.assertRaisesRegex(
                ImmutableArtifactError, expected
            ):
                archive_prd_candidate(
                    project,
                    self._v04(markdown),
                    assets=assets,
                )

    def test_v05_archive_and_release_require_managed_safe_visual_pairs(self) -> None:
        raw = self._v05(
            self.assembled.markdown
            + '\n<svg xmlns="http://www.w3.org/2000/svg"><text>raw</text></svg>\n'
        )
        with self.assertRaisesRegex(ImmutableArtifactError, "raw inline SVG"):
            archive_prd_candidate(self.project / "raw-v05", raw, assets={})

        safe = self._v05(
            self.assembled.markdown + "\n![主流程](./assets/main-flow.svg)\n"
        )
        archived = archive_prd_candidate(
            self.project / "safe-v05",
            safe,
            assets={"main-flow.svg": svg(), "main-flow@2x.png": png()},
        )
        released = release_prd_candidate(
            self.project / "safe-v05",
            archived,
            ready_assertion={
                "status": "READY",
                "candidate_hash": archived.document_hash,
            },
        )
        self.assertTrue((released.path / "assets/main-flow.svg").is_file())

    def test_v05_raw_inline_svg_fails_ready_before_any_receipt(self) -> None:
        runtime = HostRuntime(self.project, GRAPH, SKILL_ROOT)
        run_id = "run-v05-raw-ready"
        runtime.controller.create_run(run_id, raw_signal="旧稿进入普通审查后尝试 Ready")
        artifact = self.project / "artifacts/prds/archived/V05-RAW"
        artifact.mkdir(parents=True)
        document = artifact / "V05-RAW.md"
        document.write_text("# V05\n\n<svg><text>raw</text></svg>\n", encoding="utf-8")
        metadata = artifact / "V05-RAW.metadata.json"
        atomic_write_json(
            metadata,
            {
                "prd_id": "V05-RAW",
                "short_title": "原始视觉",
                "date": "2026-08-27",
                "document_experience": {
                    "profile_ref": {"version": "0.5.0"}
                },
            },
        )
        review = artifact / "V05-RAW.review.json"
        atomic_write_json(review, {"status": "FINALIZED"})
        candidate_ref = {
            "role": "prd_candidate",
            "path": document.relative_to(self.project).as_posix(),
            "hash": sha256_file(document),
            "version": "v0.1",
            "artifact_path": artifact.relative_to(self.project).as_posix(),
            "tree_hash": hash_tree(artifact),
            "review_path": review.relative_to(self.project).as_posix(),
            "review_hash": sha256_file(review),
            "generation": 1,
        }
        position_run_internal(
            runtime.controller,
            run_id,
            "prd.ready.gate",
            ["handoff.prepare", "review.parallel"],
            artifact_refs={"prd-candidate": candidate_ref},
            state_updates={"current_candidate_ref": candidate_ref},
        )
        dispatch = runtime._plan_dispatch(run_id)
        state = runtime.controller.load_state(run_id)

        with self.assertRaisesRegex(TransitionRejected, "raw inline SVG"):
            runtime.controller.prepare_ready_gate_evidence(
                run_id,
                dispatch["attempt_id"],
                expected_state_version=state["state_version"],
            )

        receipt_root = runtime.controller.run_path(run_id) / "receipts"
        self.assertFalse(receipt_root.exists() and any(receipt_root.rglob("*.json")))

    def test_v04_archive_comments_cannot_hide_later_reader_visible_assets(self) -> None:
        cases = (
            (
                "reader-visible SVG",
                self.assembled.markdown
                + "\n<!--\n```\n-->\n"
                + "![unsafe](./assets/unsafe.svg)\n```\n",
                {
                    "unsafe.svg": svg(extra="<script>x</script>"),
                    "unsafe@2x.png": png(),
                },
            ),
            (
                "managed local SVG",
                self.assembled.markdown
                + "\n<!-- ` -->\n"
                + "![remote](https://example.com/unsafe.svg)\n`\n",
                {},
            ),
        )
        for index, (expected, markdown, assets) in enumerate(cases):
            project = self.project / f"comment-mask-{index}"
            with self.subTest(index=index), self.assertRaisesRegex(
                ImmutableArtifactError, expected
            ):
                archive_prd_candidate(
                    project,
                    self._v04(markdown),
                    assets=assets,
                )

    def test_v05_literal_comment_markers_cannot_hide_active_svg_at_archive_ready_or_release(self) -> None:
        markdown = (
            self.assembled.markdown
            + "\n`````markdown <!-- literal comment opener\n"
            + "<svg><text>literal</text></svg>\n`````\n\n"
            + "    <!-- another literal opener\n"
            + "    <svg><text>indented literal</text></svg>\n\n"
            + "`<!--`\n\n"
            + "<svg><text>active</text></svg>\n"
        )
        assembled = self._v05(markdown)
        with self.assertRaisesRegex(ImmutableArtifactError, "raw inline SVG"):
            archive_prd_candidate(self.project / "archive-mask", assembled, assets={})

        runtime_project = self.project / "ready-mask"
        runtime = HostRuntime(runtime_project, GRAPH, SKILL_ROOT)
        run_id = "run-v05-mask-ready"
        runtime.controller.create_run(run_id, raw_signal="代码字面量不能隐藏 active SVG")
        artifact = runtime_project / "artifacts/prds/archived/V05-MASK"
        artifact.mkdir(parents=True)
        document = artifact / "V05-MASK.md"
        document.write_text(markdown, encoding="utf-8")
        metadata = artifact / "V05-MASK.metadata.json"
        atomic_write_json(
            metadata,
            {
                "prd_id": "V05-MASK",
                "short_title": "源码掩码",
                "date": "2026-08-27",
                "document_experience": {"profile_ref": {"version": "0.5.0"}},
            },
        )
        review = artifact / "V05-MASK.review.json"
        atomic_write_json(review, {"status": "FINALIZED"})
        candidate_ref = {
            "role": "prd_candidate",
            "path": document.relative_to(runtime_project).as_posix(),
            "hash": sha256_file(document),
            "version": "v0.1",
            "artifact_path": artifact.relative_to(runtime_project).as_posix(),
            "tree_hash": hash_tree(artifact),
            "review_path": review.relative_to(runtime_project).as_posix(),
            "review_hash": sha256_file(review),
            "generation": 1,
        }
        position_run_internal(
            runtime.controller,
            run_id,
            "prd.ready.gate",
            ["handoff.prepare", "review.parallel"],
            artifact_refs={"prd-candidate": candidate_ref},
            state_updates={"current_candidate_ref": candidate_ref},
        )
        dispatch = runtime._plan_dispatch(run_id)
        state = runtime.controller.load_state(run_id)
        with self.assertRaisesRegex(TransitionRejected, "raw inline SVG"):
            runtime.controller.prepare_ready_gate_evidence(
                run_id,
                dispatch["attempt_id"],
                expected_state_version=state["state_version"],
            )
        receipts = runtime.controller.run_path(run_id) / "receipts"
        self.assertFalse(receipts.exists() and any(receipts.rglob("*.json")))

        released_project = self.project / "release-mask"
        archived = archive_prd_candidate(released_project, self.assembled, assets={})
        archived.document_path.write_text(markdown, encoding="utf-8")
        metadata_path = next(archived.path.glob("*.metadata.json"))
        released_metadata = copy.deepcopy(self.assembled.metadata)
        released_metadata["document_experience"]["profile_ref"]["version"] = "0.5.0"
        atomic_write_json(metadata_path, released_metadata)
        changed = replace(
            archived,
            document_hash=sha256_file(archived.document_path),
            tree_hash=hash_tree(archived.path),
        )
        with self.assertRaisesRegex(ImmutableArtifactError, "raw inline SVG"):
            release_prd_candidate(
                released_project,
                changed,
                ready_assertion={
                    "status": "READY",
                    "candidate_hash": changed.document_hash,
                },
            )

    def test_v05_literal_svg_examples_archive_and_release_without_false_positive(self) -> None:
        markdown = (
            self.assembled.markdown
            + "\n~~~html info\n<svg></svg>\n~~~\n\n"
            + "    <svg><text>indented</text></svg>\n\n"
            + "`<svg></svg>`\n\n"
            + "<!-- <svg><text>comment</text></svg> -->\n"
        )
        archived = archive_prd_candidate(
            self.project / "literal-only", self._v05(markdown), assets={}
        )
        released = release_prd_candidate(
            self.project / "literal-only",
            archived,
            ready_assertion={
                "status": "READY",
                "candidate_hash": archived.document_hash,
            },
        )
        self.assertEqual(released.document_hash, archived.document_hash)

    def test_v05_validates_every_visual_asset_in_final_tree(self) -> None:
        cases = {
            "malicious orphan SVG": {
                "orphan.svg": svg(extra="<script>alert(1)</script>"),
                "orphan@2x.png": png(),
            },
            "missing PNG pair": {"orphan.svg": svg()},
            "orphan PNG pair": {"orphan@2x.png": png()},
            "unknown PNG": {"orphan.png": png()},
            "unknown visual": {"orphan.webp": b"webp"},
            "orphan visual pair": {
                "extra.svg": svg(),
                "extra@2x.png": png(),
            },
        }
        for expected, assets in cases.items():
            with self.subTest(expected=expected), self.assertRaisesRegex(
                ImmutableArtifactError, expected
            ):
                archive_prd_candidate(
                    self.project / expected.replace(" ", "-"),
                    self._v05(self.assembled.markdown),
                    assets=assets,
                )

    def test_v05_ready_and_release_reject_malicious_unreferenced_svg_tree(self) -> None:
        project = self.project / "malicious-final-tree"
        archived = archive_prd_candidate(
            project, self._v05(self.assembled.markdown), assets={}
        )
        assets = archived.path / "assets"
        assets.mkdir()
        (assets / "orphan.svg").write_bytes(svg(extra="<script>alert(1)</script>"))
        (assets / "orphan@2x.png").write_bytes(png())
        changed = replace(archived, tree_hash=hash_tree(archived.path))

        with self.assertRaisesRegex(ImmutableArtifactError, "malicious orphan SVG"):
            release_prd_candidate(
                project,
                changed,
                ready_assertion={
                    "status": "READY",
                    "candidate_hash": changed.document_hash,
                },
            )

        runtime = HostRuntime(project, GRAPH, SKILL_ROOT)
        run_id = "run-malicious-final-tree-ready"
        runtime.controller.create_run(run_id, raw_signal="恶意未引用 SVG 不得进入 Ready")
        candidate_ref = {
            "role": "prd_candidate",
            "path": changed.document_path.relative_to(project).as_posix(),
            "hash": changed.document_hash,
            "version": changed.version,
            "artifact_path": changed.path.relative_to(project).as_posix(),
            "tree_hash": changed.tree_hash,
            "review_path": changed.review_path.relative_to(project).as_posix(),
            "review_hash": changed.review_hash,
            "generation": 1,
        }
        position_run_internal(
            runtime.controller,
            run_id,
            "prd.ready.gate",
            ["handoff.prepare", "review.parallel"],
            artifact_refs={"prd-candidate": candidate_ref},
            state_updates={"current_candidate_ref": candidate_ref},
        )
        dispatch = runtime._plan_dispatch(run_id)
        state = runtime.controller.load_state(run_id)
        with self.assertRaisesRegex(TransitionRejected, "malicious orphan SVG"):
            runtime.controller.prepare_ready_gate_evidence(
                run_id,
                dispatch["attempt_id"],
                expected_state_version=state["state_version"],
            )
        receipts = runtime.controller.run_path(run_id) / "receipts"
        self.assertFalse(receipts.exists() and any(receipts.rglob("*.json")))

    def test_legacy_v02_archive_and_release_keep_pre_visual_contract_behavior(self) -> None:
        assembled = self._v02(
            self.assembled.markdown + "\n![旧图](./assets/legacy.svg)\n"
        )
        archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={"legacy.svg": b"<svg><script>legacy bytes</script></svg>"},
        )

        released = release_prd_candidate(
            self.project,
            archived,
            ready_assertion={"status": "READY", "candidate_hash": archived.document_hash},
        )

        self.assertEqual(
            (released.path / "assets/legacy.svg").read_bytes(),
            b"<svg><script>legacy bytes</script></svg>",
        )

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
