from __future__ import annotations

from copy import deepcopy
import shutil
import tempfile
import unittest
from pathlib import Path

from src.bpg.prd_contract import assemble_prd
from src.bpg.ready import PRDNotReady, ready_and_release
from src.bpg.receipts import ReceiptError
from src.bpg.state_controller import StateController, TransitionRejected
from src.bpg.storage import atomic_write_json, read_json, sha256_file
from src.bpg.templates import TemplateRegistry
from src.bpg.documents import archive_prd_candidate
from src.bpg.failpoints import InjectedCrash, crash_at
from src.bpg.storage import verify_event_chain
from tests.test_prd_contract import REPO_ROOT, TEMPLATES, prd_submission
from tests.test_reviews_ready import (
    complete_ready_input,
    finalized_review_companion,
    materialize_ready_evidence,
)


GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class ControllerReceiptAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        assembled = assemble_prd(
            prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        )
        self.archived = archive_prd_candidate(
            self.project,
            assembled,
            assets={},
            review_companion=finalized_review_companion(assembled),
        )
        candidate = {
            "path": str(self.archived.path),
            "hash": self.archived.document_hash,
            "tree_hash": self.archived.tree_hash,
            "version": self.archived.version,
        }
        self.request, self.archived = materialize_ready_evidence(
            self.project, complete_ready_input(candidate), self.archived
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _receipt_payload(self, kind: str) -> dict:
        return {
            "schema_version": "controller-receipt.v1",
            "receipt_id": "forged",
            "kind": kind,
            "issuer": "state-controller",
            "status": "PASS",
            "subject_refs": [],
        }

    def _subjects(self, kind: str) -> list[dict]:
        candidate = {
            "role": "candidate_document",
            "path": self.archived.document_path.relative_to(self.project).as_posix(),
            "hash": self.archived.document_hash,
        }
        if kind == "audit_integrity":
            return [{"role": "audit_snapshot", **self.request["presentation"]["audit_snapshot_ref"]}]
        if kind == "review_finalize":
            return [
                candidate,
                {"role": "review_companion", **self.request["review"]["companion_view_ref"]},
                {"role": "review_aggregate", **self.request["review"]["aggregate_ref"]},
                {"role": "review_dispositions", **self.request["review"]["dispositions_ref"]},
            ]
        if kind == "document_experience":
            return [
                candidate,
                {"role": "template_profile", **self.request["presentation"]["template_profile_ref"]},
                {"role": "version_record", **self.request["presentation"]["version_record_ref"]},
                {"role": "document_changelog", **self.request["presentation"]["changelog_ref"]},
            ]
        return [
            candidate,
            *[
                {"role": f"upstream_{item['kind']}", **item}
                for item in self.request["upstream_refs"]
            ],
            {"role": "mechanical_validation", **self.request["mechanical_validation_ref"]},
        ]

    def _replace_authorized_ref(self, old_path: str, ref: dict) -> None:
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(self.request["run_id"])
        for key, current in state["artifact_refs"].items():
            if current.get("path") == old_path:
                state["artifact_refs"][key] = {
                    field: ref[field] for field in ("path", "hash", "version") if field in ref
                }
                break
        atomic_write_json(controller._state_path(self.request["run_id"]), state)

    def test_handwritten_receipt_outside_controller_owned_directory_is_rejected(self) -> None:
        forged = self.project / ".better-product-graph" / "forged-review.json"
        atomic_write_json(forged, self._receipt_payload("review_finalize"))
        self.request["controller_receipts"]["review_finalize"] = {
            "path": forged.relative_to(self.project).as_posix(),
            "hash": sha256_file(forged),
            "version": 1,
            "kind": "review_finalize",
        }

        with self.assertRaisesRegex(PRDNotReady, "Controller-owned|controlled"):
            ready_and_release(
                self.project,
                self.archived,
                self.request,
                controller=StateController(self.project, GRAPH),
                run_id=self.request["run_id"],
            )

    def test_copied_receipt_not_in_controller_ledger_or_state_is_rejected(self) -> None:
        original_ref = self.request["controller_receipts"]["review_finalize"]
        original = self.project / original_ref["path"]
        copied = original.parent / "copied-unregistered.json"
        shutil.copyfile(original, copied)
        self.request["controller_receipts"]["review_finalize"] = {
            **original_ref,
            "path": copied.relative_to(self.project).as_posix(),
            "hash": sha256_file(copied),
        }

        with self.assertRaisesRegex(PRDNotReady, "ledger|state authority|registered"):
            ready_and_release(
                self.project,
                self.archived,
                self.request,
                controller=StateController(self.project, GRAPH),
                run_id=self.request["run_id"],
            )

    def test_controller_refuses_empty_subject_set(self) -> None:
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(self.request["run_id"])
        with self.assertRaisesRegex(TransitionRejected, "subject"):
            controller.issue_controller_receipt(
                self.request["run_id"],
                "empty",
                "audit_integrity",
                [],
                expected_state_version=state["state_version"],
            )

    def test_controller_refuses_right_kind_with_wrong_or_missing_subject_roles(self) -> None:
        candidate_ref = {
            "path": self.archived.document_path.relative_to(self.project).as_posix(),
            "hash": self.archived.document_hash,
        }
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(self.request["run_id"])
        with self.assertRaisesRegex(TransitionRejected, "roles"):
            controller.issue_controller_receipt(
                self.request["run_id"],
                "wrong-roles",
                "document_experience",
                [{**candidate_ref, "role": "candidate_document"}],
                expected_state_version=state["state_version"],
            )

    def test_controller_refuses_duplicate_exact_subject_refs_without_side_effects(self) -> None:
        controller = StateController(self.project, GRAPH)
        run_id = self.request["run_id"]
        state = controller.load_state(run_id)
        subjects = self._subjects("mechanical_contracts")
        decision = next(item for item in subjects if item["role"] == "upstream_decision")
        evidence = next(item for item in subjects if item["role"] == "upstream_evidence")
        evidence.update(
            {
                key: decision[key]
                for key in ("path", "hash", "version")
            }
        )
        before = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }

        with self.assertRaisesRegex(TransitionRejected, "duplicate exact subject ref"):
            controller.issue_controller_receipt(
                run_id,
                "duplicate-mechanical-subject",
                "mechanical_contracts",
                subjects,
                expected_state_version=state["state_version"],
            )

        after = {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_candidate_v1_receipts_cannot_release_candidate_v2(self) -> None:
        submission = deepcopy(prd_submission())
        submission["semantic_output"]["metadata"]["version"] = "v0.2"
        submission["semantic_output"]["document_markdown"] = submission[
            "semantic_output"
        ]["document_markdown"].replace("_v0.1_2026-08-20", "_v0.2_2026-08-20", 1)
        assembled = assemble_prd(
            submission, TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
        )
        archived_v2 = archive_prd_candidate(self.project, assembled, assets={})
        changelog = self.project / "artifacts" / "prds" / "DOCUMENT_CHANGELOG.md"
        self.request["presentation"]["changelog_ref"].update(
            {"hash": sha256_file(changelog), "resolved_hash": sha256_file(changelog)}
        )
        self.request["candidate_ref"].update(
            {
                "path": str(archived_v2.path),
                "hash": archived_v2.document_hash,
                "resolved_hash": archived_v2.document_hash,
                "tree_hash": archived_v2.tree_hash,
                "version": archived_v2.version,
            }
        )
        self.request["review"]["candidate_hash"] = archived_v2.document_hash
        self.request["review"]["candidate_version"] = archived_v2.version
        self.request["review"]["companion_view_ref"]["candidate_hash"] = archived_v2.document_hash

        with self.assertRaisesRegex(PRDNotReady, "Candidate|lifecycle"):
            ready_and_release(
                self.project,
                archived_v2,
                self.request,
                controller=StateController(self.project, GRAPH),
                run_id=self.request["run_id"],
            )

    def test_receipt_publish_before_state_registration_recovers_idempotently(self) -> None:
        controller = StateController(self.project, GRAPH)
        run_id = self.request["run_id"]
        state = controller.load_state(run_id)
        audit_ref = self.request["presentation"]["audit_snapshot_ref"]
        subjects = [
            {
                "role": "audit_snapshot",
                **audit_ref,
            }
        ]
        with self.assertRaises(InjectedCrash):
            controller.issue_controller_receipt(
                run_id,
                "audit-receipt-crash",
                "audit_integrity",
                subjects,
                expected_state_version=state["state_version"],
                failpoint=crash_at("after_receipt_persist"),
            )

        recovered = controller.issue_controller_receipt(
            run_id,
            "audit-receipt-crash",
            "audit_integrity",
            subjects,
            expected_state_version=state["state_version"],
        )
        current = controller.load_state(run_id)
        ledger = verify_event_chain(
            controller.run_path(run_id) / "receipt-ledger.jsonl"
        )
        self.assertIn(recovered, current["ready_receipts"])
        self.assertEqual(
            len(
                [
                    event
                    for event in ledger
                    if event.get("receipt_ref", {}).get("path") == recovered["path"]
                ]
            ),
            1,
        )

    def test_pass_claim_cannot_hide_wrong_upstream_content_or_metadata_hash(self) -> None:
        decision = self.request["upstream_refs"][0]
        path = self.project / decision["path"]
        atomic_write_json(path, {"kind": "wrong-kind", "version": decision["version"]})
        changed = {**decision, "hash": sha256_file(path), "resolved_hash": sha256_file(path)}
        self.request["upstream_refs"][0] = changed
        self._replace_authorized_ref(decision["path"], changed)
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(self.request["run_id"])

        with self.assertRaisesRegex(TransitionRejected, "UPSTREAM|metadata|kind|hash"):
            controller.issue_controller_receipt(
                self.request["run_id"],
                "mechanical-forged-pass",
                "mechanical_contracts",
                self._subjects("mechanical_contracts"),
                expected_state_version=state["state_version"],
            )

    def test_caller_written_finalized_companion_cannot_hide_finding_mismatch(self) -> None:
        ref = self.request["review"]["dispositions_ref"]
        path = self.project / ref["path"]
        atomic_write_json(
            path,
            {
                "schema_version": "review-dispositions.v1",
                "candidate_hash": self.archived.document_hash,
                "candidate_version": self.archived.version,
                "dispositions": [{"finding_id": "not-the-aggregate-finding", "status": "DONE"}],
            },
        )
        changed = {**ref, "hash": sha256_file(path)}
        self.request["review"]["dispositions_ref"] = changed
        self._replace_authorized_ref(ref["path"], changed)
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(self.request["run_id"])

        with self.assertRaisesRegex(TransitionRejected, "Finding|disposition|review"):
            controller.issue_controller_receipt(
                self.request["run_id"],
                "review-forged-finalized",
                "review_finalize",
                self._subjects("review_finalize"),
                expected_state_version=state["state_version"],
            )

    def test_template_receipt_binds_exact_current_registry_selection(self) -> None:
        ref = self.request["presentation"]["template_profile_ref"]
        path = self.project / ref["path"]
        payload = read_json(path)
        payload["template_hash"] = "sha256:" + "0" * 64
        atomic_write_json(path, payload)
        changed = {**ref, "hash": sha256_file(path)}
        self.request["presentation"]["template_profile_ref"] = changed
        self._replace_authorized_ref(ref["path"], changed)
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(self.request["run_id"])

        with self.assertRaisesRegex(TransitionRejected, "Template|template|registry"):
            controller.issue_controller_receipt(
                self.request["run_id"],
                "document-forged-template",
                "document_experience",
                self._subjects("document_experience"),
                expected_state_version=state["state_version"],
            )

    def test_template_receipt_binds_exact_output_contract_and_resolution(self) -> None:
        ref = self.request["presentation"]["template_profile_ref"]
        path = self.project / ref["path"]
        payload = read_json(path)
        payload["output_contract_hash"] = "sha256:" + "0" * 64
        payload["selection_source"] = "FORGED_FALLBACK"
        atomic_write_json(path, payload)
        changed = {**ref, "hash": sha256_file(path)}
        self.request["presentation"]["template_profile_ref"] = changed
        self._replace_authorized_ref(ref["path"], changed)
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(self.request["run_id"])

        with self.assertRaisesRegex(TransitionRejected, "Template|template|registry"):
            controller.issue_controller_receipt(
                self.request["run_id"],
                "document-forged-output-contract",
                "document_experience",
                self._subjects("document_experience"),
                expected_state_version=state["state_version"],
            )

    def test_duplicate_receipt_is_idempotent_and_gate_attempt_remains_unique_current(self) -> None:
        controller = StateController(self.project, GRAPH)
        before = controller.load_state(self.request["run_id"])
        original = self.request["controller_receipts"]["audit_integrity"]
        repeated = controller.issue_controller_receipt(
            self.request["run_id"],
            "audit-integrity",
            "audit_integrity",
            self._subjects("audit_integrity"),
            expected_state_version=before["state_version"],
        )
        after = controller.load_state(self.request["run_id"])
        current = [
            item
            for item in after["dispatch_attempts"]
            if item.get("status") == "DISPATCHED"
            and item.get("authorized_state_version") == after["state_version"]
        ]
        self.assertEqual(repeated, original)
        self.assertEqual(after["state_version"], before["state_version"])
        self.assertEqual(len(current), 1)

    def test_direct_record_release_surface_is_not_public(self) -> None:
        self.assertFalse(hasattr(StateController(self.project, GRAPH), "record_release"))


if __name__ == "__main__":
    unittest.main()
