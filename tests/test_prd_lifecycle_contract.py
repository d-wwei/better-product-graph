from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.documents import archive_prd_candidate
from src.bpg.engine import HostEngine
from src.bpg.prd_contract import assemble_prd
from src.bpg.ready import ready_and_release
from src.bpg.state_controller import StateController
from src.bpg.storage import read_json, sha256_bytes, sha256_file, verify_event_chain
from src.bpg.templates import TemplateRegistry
from tests.test_prd_contract import REPO_ROOT, TEMPLATES, prd_submission
from tests.test_reviews_ready import complete_ready_input, materialize_ready_evidence


GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class PRDLifecycleContractTests(unittest.TestCase):
    def test_exact_stem_self_contained_companion_and_structured_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            submission = prd_submission()
            submission["semantic_output"]["metadata"]["requirement_relationships"] = {
                "schema_version": "requirement-relationships.v1",
                "supersedes_forward_delivery_target": [
                    {
                        "prd_id": "PRD-LEGACY-001",
                        "version": "v1.0",
                        "document_ref": {
                            "path": "artifacts/prds/released/PRD-LEGACY-001/PRD-LEGACY-001.md",
                            "hash": "sha256:legacy",
                            "version": "v1.0",
                        },
                        "preserve_historical_status": True,
                    }
                ],
                "invalidates": ["旧流程必须一次性交付全部能力"],
            }
            assembled = assemble_prd(
                submission, TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
            )
            candidate_hash = sha256_bytes(assembled.markdown.encode())
            companion = {
                "schema_version": "prd-review-companion.v1",
                "prd_id": assembled.metadata["prd_id"],
                "version": assembled.metadata["version"],
                "candidate_hash": candidate_hash,
                "status": "FINALIZED",
                "authority": "ADVISORY_ONLY",
                "finding_count": 0,
            }
            archived = archive_prd_candidate(
                project,
                assembled,
                assets={"state.png": b"PNG-BYTES"},
                review_companion=companion,
            )

            stem = "PRD-CHECKOUT-001_结算恢复体验_v0.1_2026-08-20"
            self.assertEqual(archived.path.name, stem)
            self.assertTrue((archived.path / f"{stem}.md").is_file())
            archived_review = archived.path / f"{stem}.review.json"
            self.assertTrue(archived_review.is_file())
            self.assertTrue((archived.path / "assets" / "state.png").is_file())
            self.assertEqual(archived.review_hash, sha256_file(archived_review))

            candidate = {
                "path": str(archived.path),
                "candidate_hash": archived.document_hash,
                "hash": archived.document_hash,
                "tree_hash": archived.tree_hash,
                "version": archived.version,
            }
            request, archived = materialize_ready_evidence(
                project, complete_ready_input(candidate), archived
            )
            controller = StateController(project, GRAPH)
            released = ready_and_release(
                project,
                archived,
                request,
                controller=controller,
                run_id=request["run_id"],
            )
            self.assertTrue((released.path / f"{stem}.md").is_file())
            self.assertTrue((released.path / f"{stem}.review.json").is_file())
            self.assertTrue((released.path / "assets" / "state.png").is_file())

            events = verify_event_chain(
                project / "artifacts" / "prds" / "PRODUCT_DOCUMENT_CHANGELOG.jsonl"
            )
            self.assertEqual([event["status"] for event in events], ["CANDIDATE_ARCHIVED", "RELEASED"])
            release = events[-1]
            self.assertEqual(
                {item["kind"] for item in release["upstream_refs"]},
                {"decision", "roadmap", "product_plan", "slice", "knowledge", "evidence"},
            )
            self.assertTrue(release["template_ref"]["hash"].startswith("sha256:"))
            self.assertIn("requested_profile_id", release["template_ref"])
            self.assertIn("requested_version", release["template_ref"])
            self.assertTrue(release["policy_ref"]["hash"].startswith("sha256:"))
            self.assertEqual(release["review_ref"]["hash"], archived.review_hash)
            self.assertEqual(release["ready_ref"]["hash"], sha256_file(released.path / "READY_ASSERTION.json"))
            self.assertEqual(release["asset_refs"][0]["hash"], sha256_file(released.path / "assets" / "state.png"))
            self.assertEqual(
                release["requirement_relationships"],
                assembled.metadata["requirement_relationships"],
            )

            release_manifest = read_json(
                project / "artifacts" / "prds" / "RELEASE_MANIFEST.json"
            )
            self.assertEqual(release_manifest["schema_version"], "prd-release-manifest.v1")
            current = release_manifest["forward_implementation_targets"]
            self.assertEqual(len(current), 1)
            self.assertEqual(current[0]["prd_id"], "PRD-CHECKOUT-001")
            self.assertEqual(current[0]["document_ref"]["hash"], released.document_hash)
            self.assertEqual(
                current[0]["requirement_relationships"]["supersedes_forward_delivery_target"][0]["prd_id"],
                "PRD-LEGACY-001",
            )
            self.assertEqual(release_manifest["authority"], "DERIVED_NAVIGATION_ONLY")
            self.assertNotIn("latest", release_manifest)

            run_id = request["run_id"]
            released_state = controller.load_state(run_id)
            self.assertEqual(released_state["status"], "RELEASED")
            self.assertEqual(released_state["current_node"], "handoff.prepare")
            handoff = HostEngine(project, controller).handle(
                f"$better-product-graph handoff {run_id}"
            )
            self.assertEqual(handoff["status"], "COMPLETED")
            self.assertEqual(handoff["delivery_status"], "WRITTEN_LOCAL")
            self.assertFalse(handoff["sent_remote"])
            handoff_packet = read_json(project / handoff["handoff_ref"]["path"])
            self.assertEqual(
                handoff_packet["requirement_relationships"],
                assembled.metadata["requirement_relationships"],
            )
            self.assertEqual(
                handoff_packet["release_manifest_ref"]["hash"],
                sha256_file(project / handoff_packet["release_manifest_ref"]["path"]),
            )
            lifecycle_view = project / handoff["human_lifecycle_view_ref"]["path"]
            lifecycle_text = lifecycle_view.read_text(encoding="utf-8")
            self.assertIn("需求文档：RELEASED", lifecycle_text)
            self.assertIn("代码实现：NOT_CLAIMED", lifecycle_text)
            self.assertIn("测试 / Evals：NOT_RUN", lifecycle_text)
            self.assertIn("本地交接：WRITTEN_LOCAL", lifecycle_text)
            self.assertIn("远程发送：NOT_CONFIGURED", lifecycle_text)
            self.assertNotIn("功能已完成", lifecycle_text)
            completed_state = controller.load_state(run_id)
            self.assertEqual(completed_state["status"], "COMPLETED")
            self.assertEqual(completed_state["current_node"], "handoff.dispatch")


if __name__ == "__main__":
    unittest.main()
