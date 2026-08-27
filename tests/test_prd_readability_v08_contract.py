from __future__ import annotations

import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "evals" / "prd-readability-v0.8"
V07_ROOT = REPO_ROOT / "evals" / "prd-readability-v0.7"
SUITE_ID = "better-product-graph-prd-readability-v0.8"
TREE_HASH = "sha256:da47036a8a805580542574f40d5c623ccd7a487aa15724a510001da840b69ef6"
CASE_IDS = tuple(f"case-{index:03d}" for index in range(1, 10))
REVIEW_HASHES = {
    "fixture-review/reviewer-a.json": "sha256:496d2250f8bbee379a9195cd9222d87474c723374dc3a53fae9f0c747005166a",
    "fixture-review/reviewer-b.json": "sha256:b52e32fe827eeef784bc751f6b4b1543be47deb34dadaced504b3dbf26eb3a7a",
}
OLD_INVALID_REVIEW_HASHES = {
    "sha256:8ed0d634a7853d3acf9a40c46a3f41b8ea5c5c7f354f7ea3f52a8e1aea41c2fa",
    "sha256:c7ddbc5ae47c9e88cadbc88554003722b5fa909851cfe32fdfdf761ee6f68c46",
}


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract() -> dict:
    return runpy.run_path(str(ROOT / "run_contract.py"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def exact_ref(root: Path, path: Path, version: str | int = 1) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": file_hash(path),
        "version": version,
    }


def frozen_score_report(phase: str, status: str = "FAIL") -> dict:
    passed = 27 if status == "PASS" else 26
    return {
        "schema_version": "prd-readability-v0.8-phase-score.v1",
        "suite_id": SUITE_ID,
        "phase": phase,
        "status": status,
        "selection_policy": "ALL_PRODUCED_ATTEMPTS_OCCUPY_DENOMINATOR_NO_BEST_OF_N_NO_REPLACEMENT",
        "score": {"passed": passed, "total": 27, "required": 27},
        "produced_output_count": 27,
        "installed_build_ref": {
            "path": "build-manifest.json",
            "hash": "sha256:" + "a" * 64,
            "version": "0.2.18-rc.5" if phase == "RC_CANDIDATE" else "0.2.18",
        },
        "issues": [] if status == "PASS" else ["case_failure"],
        "attempts": [
            {
                "ordinal": ordinal,
                "semantic_case_id": f"case-{((ordinal - 1) // 3) + 1:03d}",
                "repeat_index": ((ordinal - 1) % 3) + 1,
                "run_id": f"{phase.lower()}-run-{ordinal:03d}",
                "attempt_id": f"{phase.lower()}-attempt-{ordinal:03d}",
                "produced_output": True,
                "status": "PASS" if status == "PASS" or ordinal != 1 else "FAIL",
                "issues": [] if status == "PASS" or ordinal != 1 else ["case_failure"],
            }
            for ordinal in range(1, 28)
        ],
        "agent_runtime_status": "COMPLETED",
        "human_reader_validation": "NOT_RUN",
    }


def score_invocation_authority(root: Path, phase: str) -> dict:
    manifests = root / ".better-product-graph" / "writing-evals" / "execution-manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    manifest = manifests / f"{phase}.json"
    attempts = []
    for ordinal in range(1, 28):
        result = root / "durable-results" / phase / f"{ordinal:03d}.json"
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text(json.dumps({"ordinal": ordinal}) + "\n", encoding="utf-8")
        attempt = {
            "ordinal": ordinal,
            "run_id": f"{phase.lower()}-run-{ordinal:03d}",
            "attempt_id": f"{phase.lower()}-attempt-{ordinal:03d}",
            "result_ref": exact_ref(root, result),
        }
        attempts.append(attempt)
        state = (
            root
            / ".better-product-graph"
            / "writing-evals"
            / attempt["run_id"]
            / "state.json"
        )
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(
            json.dumps({"result_ref": attempt["result_ref"]}) + "\n",
            encoding="utf-8",
        )
    manifest.write_text(
        json.dumps({
            "suite_id": SUITE_ID,
            "phase": phase,
            "entries": [
                {
                    "ordinal": item["ordinal"],
                    "run_id": item["run_id"],
                    "attempt_id": item["attempt_id"],
                }
                for item in attempts
            ],
        }) + "\n",
        encoding="utf-8",
    )
    batch = manifests / f"{phase}.batch-validation-receipt.json"
    batch.write_text(
        json.dumps({
            "suite_id": SUITE_ID,
            "phase": phase,
            "status": "VALIDATED",
            "manifest_ref": exact_ref(root, manifest),
        }) + "\n",
        encoding="utf-8",
    )
    return {
        "schema_version": "prd-readability-v0.8-score-invocation.v1",
        "suite_id": SUITE_ID,
        "phase": phase,
        "execution_manifest_ref": exact_ref(root, manifest),
        "batch_validation_receipt_ref": exact_ref(root, batch),
        "scorer_ref": load_json(ROOT / "evaluator/preregistration.json")["scorer_ref"],
        "evidence_snapshot": {
            "schema_version": "prd-readability-v0.8-score-evidence-snapshot.v1",
            "suite_id": SUITE_ID,
            "phase": phase,
            "attempts": attempts,
        },
    }


def commit_frozen_score(
    scorer: dict,
    root: Path,
    phase: str,
    report: dict,
    authority: dict,
) -> dict:
    """Mint a derivation under patched test evidence, then use the closed commit API."""

    globals_dict = scorer["_derive_phase_score"].__globals__
    original_prepare = globals_dict["_prepare_score_invocation"]
    original_compute = globals_dict["_compute_phase_score"]
    globals_dict["_prepare_score_invocation"] = lambda *_args, **_kwargs: authority
    globals_dict["_compute_phase_score"] = lambda *_args, **_kwargs: report
    try:
        derivation = scorer["_derive_phase_score"](root, root, phase)
        return scorer["_commit_terminal_score"](root, phase, derivation)
    finally:
        globals_dict["_prepare_score_invocation"] = original_prepare
        globals_dict["_compute_phase_score"] = original_compute


class PrdReadabilityV08FrozenContractTests(unittest.TestCase):
    def test_exact_a2_b2_outputs_pass_closed_calibration_gate(self) -> None:
        contract = load_contract()
        approved, reasons = contract["validate_fixture_review_gate"]()
        self.assertTrue(approved, reasons)
        self.assertEqual(reasons, [])

        outcomes = {}
        reviewer_ids = []
        for relative, expected_hash in REVIEW_HASHES.items():
            path = ROOT / relative
            self.assertEqual(file_hash(path), expected_hash)
            review = load_json(path)
            self.assertEqual(set(review), {
                "schema_version", "suite_id", "reviewer_id", "claim_boundary", "reviews"
            })
            reviewer_ids.append(review["reviewer_id"])
            self.assertEqual(len(review["reviews"]), 10)
            self.assertEqual(
                {item["result"] for item in review["reviews"]},
                {"PASS", "FINDING"},
            )
            counts = {
                result: sum(item["result"] == result for item in review["reviews"])
                for result in ("FINDING", "PASS")
            }
            self.assertEqual(counts, {"FINDING": 6, "PASS": 4})
            outcomes[review["reviewer_id"]] = {
                item["exact_basis"][0]["hash"]: item["result"]
                for item in review["reviews"]
            }
        self.assertEqual(len(set(reviewer_ids)), 2)
        self.assertEqual(*outcomes.values())

    def test_calibration_gate_rejects_tamper_unknown_fields_and_old_hash_reuse(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "fixture-review"
            shutil.copytree(ROOT / "fixture-review", copied)
            review = load_json(copied / "reviewer-a.json")
            review["reviews"][0]["unexpected"] = True
            (copied / "reviewer-a.json").write_text(
                json.dumps(review, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            approved, reasons = contract["validate_fixture_review_gate"](copied)
            self.assertFalse(approved)
            self.assertTrue(reasons)

        preregistration = load_json(ROOT / "evaluator/preregistration.json")
        current_hashes = {ref["hash"] for ref in preregistration["fixture_review_refs"]}
        self.assertEqual(current_hashes, set(REVIEW_HASHES.values()))
        self.assertTrue(current_hashes.isdisjoint(OLD_INVALID_REVIEW_HASHES))

    def test_adjudication_records_unanimous_outcomes_and_unscored_paired_positive(self) -> None:
        adjudication = load_json(ROOT / "fixture-review/adjudication.json")
        self.assertEqual(adjudication["schema_version"], "prd-readability-v0.8-fixture-adjudication.v1")
        self.assertEqual(adjudication["status"], "APPROVED_FOR_PREREGISTRATION")
        self.assertEqual(adjudication["fixture_tree"]["tree_hash"], TREE_HASH)
        self.assertEqual(adjudication["approved_scored_case_ids"], list(CASE_IDS))
        self.assertEqual(adjudication["calibration_only_document"], {
            "path": "calibration/notification-priority-positive.md",
            "result": "PASS",
            "included_in_scored_denominator": False,
        })
        self.assertEqual(adjudication["agreement"], {
            "reviewers": 2,
            "finding_documents": 6,
            "pass_documents": 4,
            "outcome_disagreements": [],
        })
        self.assertEqual(adjudication["agent_runtime_status"], "NOT_RUN")

    def test_v08_suite_keeps_exact_public_product_contract(self) -> None:
        suite = load_json(ROOT / "suite.json")
        prior = load_json(V07_ROOT / "suite.json")
        self.assertEqual(suite["schema_version"], "prd-readability-suite.v0.8")
        self.assertEqual(suite["suite_id"], SUITE_ID)
        self.assertEqual(suite["case_ids"], list(CASE_IDS))
        self.assertEqual(suite["fixture_tree_hash"], TREE_HASH)
        for field in (
            "profile_ref", "guide_ref", "instruction_ref", "reviewer_resource_ref",
            "output_contract_ref", "result_schema_ref", "target_eval_schema",
        ):
            self.assertEqual(suite[field], prior[field], field)

    def test_preregistration_freezes_exact_new_27_slot_identity_before_outputs(self) -> None:
        preregistration = load_json(ROOT / "evaluator/preregistration.json")
        self.assertEqual(preregistration["schema_version"], "prd-readability-preregistration.v0.8")
        self.assertEqual(preregistration["suite_id"], SUITE_ID)
        self.assertEqual(preregistration["suite_ref"]["version"], "0.8")
        self.assertEqual(preregistration["status"], "PREREGISTERED_BEFORE_RESULTS")
        self.assertEqual(preregistration["mandatory_phases"], [
            "RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT"
        ])
        self.assertEqual(preregistration["phase_gate"], {
            "case_count": 9,
            "repeats_per_case": 3,
            "required_attempt_count": 27,
            "required_passed_attempt_count": 27,
            "required_passed_repeats_per_case": 3,
        })
        self.assertEqual(preregistration["phase_installed_build_versions"], {
            "RC_CANDIDATE": "0.2.18-rc.5",
            "FINAL_PUBLIC_ARTIFACT": "0.2.18",
        })
        self.assertEqual(
            preregistration["selection_policy"],
            "ALL_PRODUCED_ATTEMPTS_OCCUPY_DENOMINATOR_NO_BEST_OF_N_NO_REPLACEMENT",
        )
        self.assertEqual(
            preregistration["cross_phase_policy"],
            "BOTH_PHASES_PASS_NO_LATER_PHASE_RESCUE",
        )
        self.assertEqual(preregistration["phase_runtime_status"], {
            "RC_CANDIDATE": "NOT_RUN", "FINAL_PUBLIC_ARTIFACT": "NOT_RUN"
        })
        self.assertFalse(any(
            path.is_file() and path.name != "README.md"
            for path in (ROOT / "results").rglob("*")
        ))
        self.assertEqual(load_contract()["preregistration_issues"](), [])

    def test_all_new_suite_refs_are_exact_and_not_v07_aliases(self) -> None:
        preregistration = load_json(ROOT / "evaluator/preregistration.json")
        for field in (
            "suite_ref", "expected_ref", "scorer_ref", "run_contract_ref",
            "evidence_reader_ref", "fixture_adjudication_ref",
        ):
            ref = preregistration[field]
            self.assertEqual(file_hash(ROOT / ref["path"]), ref["hash"], field)
            old_path = V07_ROOT / ref["path"]
            if old_path.exists():
                self.assertNotEqual(ref["hash"], file_hash(old_path), field)
        self.assertNotIn("v0.7", json.dumps(preregistration, ensure_ascii=False))
        self.assertEqual(
            preregistration["execution_manifest_schema"]["schema_version"],
            "prd-readability-v0.8-execution-manifest.v1",
        )

    def test_manifest_contract_requires_exactly_nine_times_three_fresh_slots(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stat = root.stat()
            build = {
                "path": "build-manifest.json",
                "hash": "sha256:" + "a" * 64,
                "version": "0.2.18-rc.5",
            }
            entries = []
            for ordinal in range(1, 28):
                case_index = (ordinal - 1) // 3 + 1
                repeat = (ordinal - 1) % 3 + 1
                entries.append({
                    "ordinal": ordinal,
                    "suite_id": SUITE_ID,
                    "phase": "RC_CANDIDATE",
                    "semantic_case_id": f"case-{case_index:03d}",
                    "agent_case_id": f"case-{case_index:03d}",
                    "repeat_index": repeat,
                    "run_id": f"v08-run-{ordinal:03d}",
                    "attempt_id": f"v08-attempt-{ordinal:03d}",
                    "reviewer_execution_ref": {"kind": "HOST_SUBAGENT_ATTEMPT", "id": f"v08-reviewer-{ordinal:03d}"},
                    "author_execution_ref": {"kind": "HOST_AGENT_ATTEMPT", "id": f"v08-author-{ordinal:03d}"},
                    "preregistration_checkpoint_ref": {"path": f"checkpoints/{ordinal}.json", "hash": "sha256:" + f"{ordinal:064x}", "version": 1},
                    "work_order_ref": {"path": f"work/{ordinal}.json", "hash": "sha256:" + f"{ordinal + 27:064x}", "version": 1},
                    "output_target": f"outputs/{ordinal}.json",
                    "central_project_root": {"path": str(root.resolve()), "device": stat.st_dev, "inode": stat.st_ino},
                    "state_ref": {"path": f"state/{ordinal}.json", "hash": "sha256:" + f"{ordinal + 54:064x}", "version": 3},
                    "installed_build_ref": build,
                })
            manifest = {
                "schema_version": "prd-readability-v0.8-execution-manifest.v1",
                "status": "FROZEN_BEFORE_AGENT_OUTPUT",
                "suite_id": SUITE_ID,
                "phase": "RC_CANDIDATE",
                "central_project_root": {"path": str(root.resolve()), "device": stat.st_dev, "inode": stat.st_ino},
                "installed_build_ref": build,
                "required_attempt_count": 27,
                "result_ref_null_count_at_freeze": 27,
                "agent_output_count_at_freeze": 0,
                "entries": entries,
            }
            self.assertEqual(contract["execution_manifest_shape_issues"](manifest), [])
            manifest["entries"][-1]["run_id"] = manifest["entries"][0]["run_id"]
            self.assertIn("duplicate_run_id", contract["execution_manifest_shape_issues"](manifest))

    def test_anonymous_export_contains_only_nine_scored_cases_and_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "agent-workspace"
            load_contract()["emit_agent_workspace"](target)
            self.assertEqual(
                sorted(path.name for path in target.iterdir() if path.is_dir()),
                list(CASE_IDS),
            )
            self.assertFalse((target / "paired-positive").exists())
            forbidden = {
                "expected.json", "preregistration.json", "score_results.py",
                "evidence_reader.py", "reviewer-a.json", "reviewer-b.json",
                "adjudication.json", "notification-priority-positive.md",
            }
            self.assertTrue(forbidden.isdisjoint({path.name for path in target.rglob("*")}))
            for case_id in CASE_IDS:
                manifest = load_json(target / case_id / "case-manifest.json")
                self.assertEqual(manifest["suite_id"], SUITE_ID)
                self.assertFalse(manifest["evaluator_files_included"])

    def test_v08_scorer_preserves_one_primary_finding_and_strict_positive_semantics(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        expected = load_json(ROOT / "evaluator/expected.json")["cases"]
        finding = {
            "suite_id": SUITE_ID,
            "case_id": "case-001",
            "attempt_id": "v08-attempt-001",
            "reviewer_execution_ref": {"kind": "HOST_SUBAGENT_ATTEMPT", "id": "semantic-v08-001"},
            "result": "FINDING",
            "primary_diagnosis": "FLAT_PEER_OVERLOAD",
            "primary_repair_technique": "GROUP",
            "reader_outcome_failures": ["验收难以快速定位。"],
            "verbosity_assessment": {
                "verdict": "FINDING",
                "issue_types": ["FLAT_PEER_OVERLOAD", "DETAIL_IN_MAIN_PATH"],
                "repair_techniques": ["GROUP", "LAYER"],
            },
            "checklist_assessment": {"verdict": "PASS", "issue_types": [], "repair_techniques": []},
            "visual_assessment": {"verdict": "PASS", "issue_types": [], "repair_techniques": []},
        }
        evidence = {
            "suite_id": SUITE_ID,
            "case_id": "case-001",
            "attempt_id": "v08-attempt-001",
            "reviewer_execution_ref": finding["reviewer_execution_ref"],
            "evaluation_only": True,
            "product_authority": "NONE",
            "result": finding,
        }
        self.assertEqual(scorer["_semantic_issues"](evidence, expected["case-001"]), [])

        positive = json.loads(json.dumps(finding))
        positive.update({
            "case_id": "case-007",
            "result": "PASS",
            "primary_diagnosis": None,
            "primary_repair_technique": None,
            "reader_outcome_failures": [],
        })
        positive["verbosity_assessment"] = {
            "verdict": "PASS", "issue_types": [], "repair_techniques": []
        }
        positive_evidence = json.loads(json.dumps(evidence))
        positive_evidence.update({"case_id": "case-007", "result": positive})
        self.assertEqual(
            scorer["_semantic_issues"](positive_evidence, expected["case-007"]),
            [],
        )
        positive["reader_outcome_failures"] = ["仍有理解失败。"]
        self.assertIn(
            "positive_reader_outcome_failures",
            scorer["_semantic_issues"](positive_evidence, expected["case-007"]),
        )

    def test_scorer_cli_fails_cleanly_without_name_error_or_false_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "evaluator/score_results.py"),
                    "--project-root", str(root),
                    "--skill-root", str(root),
                    "--phase", "RC_CANDIDATE",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn("NameError", completed.stderr + completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["status"], "FAIL")

    def test_contract_cli_passes_mechanically_without_claiming_semantic_run(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_contract.py")],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["contract_status"], "PASS")
        self.assertEqual(report["agent_runtime_status"], "NOT_RUN")
        self.assertEqual(report["phase_runtime_status"], {
            "RC_CANDIDATE": "NOT_RUN", "FINAL_PUBLIC_ARTIFACT": "NOT_RUN"
        })


class PrdReadabilityV08WriteOnceScoringTests(unittest.TestCase):
    def test_preregistration_freezes_write_once_terminal_score_policy(self) -> None:
        preregistration = load_json(ROOT / "evaluator/preregistration.json")
        self.assertEqual(preregistration["phase_score_contract"], {
            "schema_version": "prd-readability-v0.8-phase-score-contract.v1",
            "invocation_schema": "prd-readability-v0.8-score-invocation.v1",
            "invocation_fields": [
                "schema_version", "suite_id", "phase", "execution_manifest_ref",
                "batch_validation_receipt_ref", "scorer_ref", "evidence_snapshot",
            ],
            "evidence_snapshot_schema": "prd-readability-v0.8-score-evidence-snapshot.v1",
            "evidence_snapshot_attempt_fields": [
                "ordinal", "run_id", "attempt_id", "result_ref",
            ],
            "score_schema": "prd-readability-v0.8-phase-score.v1",
            "score_fields": [
                "schema_version", "suite_id", "phase", "status", "selection_policy",
                "score", "produced_output_count", "installed_build_ref", "issues",
                "attempts", "agent_runtime_status", "human_reader_validation",
            ],
            "score_attempt_fields": [
                "ordinal", "semantic_case_id", "repeat_index", "run_id", "attempt_id",
                "produced_output", "status", "issues",
            ],
            "receipt_schema": "prd-readability-v0.8-phase-score-receipt.v1",
            "receipt_fields": [
                "schema_version", "status", "suite_id", "phase", "terminal_outcome",
                "write_policy", "score_ref", "scorer_ref", "execution_manifest_ref",
                "batch_validation_receipt_ref", "evidence_snapshot",
                "evidence_snapshot_hash", "controller_invocation_ref",
                "terminal_transaction_id", "validation_digest",
            ],
            "controller_invocation_schema": "prd-readability-v0.8-controller-score-invocation.v1",
            "controller_invocation_fields": [
                "schema_version", "status", "suite_id", "phase", "invocation",
                "invocation_hash", "frozen_contract_refs",
            ],
            "terminal_transaction_schema": "prd-readability-v0.8-controller-score-transaction.v1",
            "terminal_transaction_fields": [
                "schema_version", "status", "suite_id", "phase", "transaction_id",
                "controller_invocation_ref", "invocation_hash", "frozen_contract_refs",
                "execution_manifest_ref", "batch_validation_receipt_ref",
                "evidence_snapshot", "evidence_snapshot_hash", "validation_digest",
                "score_ref", "receipt_ref", "controller_ledger_ref",
            ],
            "controller_ledger_schema": "prd-readability-v0.8-controller-score-ledger.v1",
            "controller_ledger_fields": [
                "schema_version", "status", "suite_id", "phase", "transaction_id",
                "invocation_hash", "frozen_contract_refs", "validation_digest",
                "score_hash",
            ],
            "frozen_contract_ref_fields": [
                "preregistration_ref", "expected_ref", "run_contract_ref", "scorer_ref",
                "evidence_reader_ref",
            ],
            "terminal_paths": {
                "score": ".better-product-graph/writing-evals/phase-scores/<PHASE>/score.json",
                "receipt": ".better-product-graph/writing-evals/phase-scores/<PHASE>/receipt.json",
                "controller_invocation": ".better-product-graph/writing-evals/phase-scores/<PHASE>/controller-invocation.json",
                "controller_transaction": ".better-product-graph/writing-evals/phase-scores/<PHASE>/controller-transaction.json",
                "controller_ledger": ".better-product-graph/writing-evals/score-ledger/<PHASE>.json",
            },
            "first_invocation_preconditions": [
                "EXACT_EXECUTION_MANIFEST_AND_BATCH_RECEIPT_EXIST",
                "ALL_27_DURABLE_RESULT_REFS_EXIST",
                "EXACT_SCORER_HASH_MATCHES_PREREGISTRATION",
            ],
            "early_score_policy": "REJECT_WITHOUT_TERMINAL_ARTIFACT",
            "first_completed_score_policy": "INTERNAL_DERIVATION_CAPABILITY_THEN_O_EXCL_LEDGER_INVOCATION_SCORE_RECEIPT_TRANSACTION_FIRST_FAIL_IS_TERMINAL",
            "repeat_policy": "VALIDATE_CANONICAL_FREEZE_LEDGER_AND_TRANSACTION_THEN_READ_ONLY_RECOMPUTE_EVERY_SCORE_FIELD_FROM_EXACT_BOUND_EVIDENCE",
            "partial_write_policy": "FAIL_CLOSED_NO_RECOMPUTE_MANUAL_AUDIT_REQUIRED",
            "release_aggregation_policy": "READ_ONLY_REDERIVE_BOTH_EXACT_PHASES_VERIFY_LEDGER_AND_TRANSACTION_NEVER_CREATE_OR_UPDATE_PHASE_SCORE",
            "trust_boundary": "FAIL_CLOSED_FOR_SUPPORTED_CODE_PATH_ACCIDENT_REPLAY_PARTIAL_AND_DIRECT_FABRICATION_NOT_CRYPTOGRAPHIC_RESISTANCE_TO_PRIVILEGED_LOCAL_CODE_AND_EVIDENCE_REWRITE",
        })

    def test_first_fail_is_terminal_repeat_revalidates_read_only_and_evidence_change_rejects(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        function_globals = scorer["score_phase"].__globals__
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            calls = {"prepare": 0, "compute": 0}

            def prepare(*_args: object, **_kwargs: object) -> dict:
                calls["prepare"] += 1
                return authority

            def compute(*_args: object, **_kwargs: object) -> dict:
                calls["compute"] += 1
                return frozen_score_report("RC_CANDIDATE", "FAIL")

            originals = {
                name: function_globals.get(name)
                for name in ("_canonical_preregistration_issues", "_prepare_score_invocation", "_compute_phase_score")
            }
            function_globals["_canonical_preregistration_issues"] = lambda: []
            function_globals["_prepare_score_invocation"] = prepare
            function_globals["_compute_phase_score"] = compute
            try:
                first = scorer["score_phase"](root, root, "RC_CANDIDATE")
                second = scorer["score_phase"](root, root, "RC_CANDIDATE")
                self.assertEqual(first, second)
                self.assertEqual(first["status"], "FAIL")
                self.assertEqual(calls, {"prepare": 4, "compute": 2})
                result_path = root / authority["evidence_snapshot"]["attempts"][0]["result_ref"]["path"]
                result_path.write_text('{"changed":true}\n', encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "evidence|result_ref"):
                    scorer["score_phase"](root, root, "RC_CANDIDATE")
                self.assertEqual(calls, {"prepare": 4, "compute": 2})
            finally:
                for name, value in originals.items():
                    if value is None:
                        function_globals.pop(name, None)
                    else:
                        function_globals[name] = value

    def test_terminal_score_rejects_result_receipt_replacement_and_object_conflict(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            commit_frozen_score(
                scorer, root, "RC_CANDIDATE", frozen_score_report("RC_CANDIDATE"), authority
            )
            score_path, receipt_path = scorer["_phase_score_paths"](root, "RC_CANDIDATE")
            original_score = score_path.read_bytes()
            score_path.write_bytes(original_score + b" ")
            with self.assertRaisesRegex(ValueError, "score.*hash|terminal"):
                scorer["_load_terminal_score"](root, root, "RC_CANDIDATE")

            score_path.write_bytes(original_score)
            receipt = load_json(receipt_path)
            conflicting = load_json(score_path)
            conflicting["phase"] = "FINAL_PUBLIC_ARTIFACT"
            score_path.write_text(
                json.dumps(conflicting, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            receipt["score_ref"]["hash"] = file_hash(score_path)
            receipt_path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "phase|object"):
                scorer["_load_terminal_score"](root, root, "RC_CANDIDATE")

    def test_terminal_paths_reject_symlink_non_regular_and_partial_write(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            score_path, receipt_path = scorer["_phase_score_paths"](root, "RC_CANDIDATE")
            score_path.parent.mkdir(parents=True)
            foreign = root / "foreign-score.json"
            foreign.write_text("{}\n", encoding="utf-8")
            score_path.symlink_to(foreign)
            receipt_path.mkdir()
            with self.assertRaisesRegex(ValueError, "regular|symlink|partial"):
                scorer["_load_terminal_score"](root, root, "RC_CANDIDATE")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            result_ref = authority["evidence_snapshot"]["attempts"][0]["result_ref"]
            result_path = root / result_ref["path"]
            original = result_path.read_bytes()
            target = root / "same-bytes.json"
            target.write_bytes(original)
            result_path.unlink()
            result_path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symlink"):
                commit_frozen_score(
                    scorer,
                    root,
                    "RC_CANDIDATE",
                    frozen_score_report("RC_CANDIDATE"),
                    authority,
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            commit_frozen_score(
                scorer,
                root,
                "RC_CANDIDATE",
                frozen_score_report("RC_CANDIDATE"),
                authority,
            )
            _invocation, transaction = scorer["_phase_score_authority_paths"](
                root, "RC_CANDIDATE"
            )
            transaction_bytes = transaction.read_bytes()
            transaction.unlink()
            foreign = root / "foreign-transaction.json"
            foreign.write_bytes(transaction_bytes)
            transaction.symlink_to(foreign)
            with self.assertRaisesRegex(ValueError, "symlink"):
                scorer["_load_terminal_score"](root, root, "RC_CANDIDATE")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            commit_frozen_score(
                scorer,
                root,
                "RC_CANDIDATE",
                frozen_score_report("RC_CANDIDATE"),
                authority,
            )
            _invocation, transaction = scorer["_phase_score_authority_paths"](
                root, "RC_CANDIDATE"
            )
            os.link(transaction, root / "transaction-hardlink.json")
            with self.assertRaisesRegex(ValueError, "hard links"):
                scorer["_load_terminal_score"](root, root, "RC_CANDIDATE")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            score_path, _receipt_path = scorer["_phase_score_paths"](root, "RC_CANDIDATE")
            score_path.parent.mkdir(parents=True)
            score_path.write_text("{}\n", encoding="utf-8")
            calls = {"compute": 0}
            globals_dict = scorer["score_phase"].__globals__
            original = globals_dict.get("_compute_phase_score")
            globals_dict["_compute_phase_score"] = lambda *_args, **_kwargs: calls.__setitem__("compute", calls["compute"] + 1)
            try:
                with self.assertRaisesRegex(ValueError, "partial"):
                    scorer["score_phase"](root, root, "RC_CANDIDATE")
                self.assertEqual(calls["compute"], 0)
            finally:
                if original is None:
                    globals_dict.pop("_compute_phase_score", None)
                else:
                    globals_dict["_compute_phase_score"] = original

    def test_early_score_is_rejected_without_creating_terminal_artifacts(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        globals_dict = scorer["score_phase"].__globals__
        original = globals_dict["_canonical_preregistration_issues"]
        globals_dict["_canonical_preregistration_issues"] = lambda: []
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaisesRegex(ValueError, "precondition|manifest"):
                    scorer["score_phase"](root, root, "RC_CANDIDATE")
                score_path, receipt_path = scorer["_phase_score_paths"](root, "RC_CANDIDATE")
                self.assertFalse(score_path.exists() or score_path.is_symlink())
                self.assertFalse(receipt_path.exists() or receipt_path.is_symlink())
        finally:
            globals_dict["_canonical_preregistration_issues"] = original

    def test_release_aggregation_consumes_frozen_scores_without_rescoring(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for phase in ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT"):
                authority = score_invocation_authority(root, phase)
                commit_frozen_score(
                    scorer, root, phase, frozen_score_report(phase, "PASS"), authority
                )
            globals_dict = scorer["score_release_phases"].__globals__
            original_score_phase = globals_dict["score_phase"]
            original_contract = globals_dict["_contract"]
            original_compute = globals_dict["_compute_phase_score"]
            globals_dict["score_phase"] = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("release aggregation must not call score_phase")
            )
            globals_dict["_contract"] = lambda: {
                "preregistration_issues": lambda: [],
                "cross_phase_freshness_issues": lambda *_args: [],
            }
            globals_dict["_compute_phase_score"] = (
                lambda _root, _skill, phase: frozen_score_report(phase, "PASS")
            )
            try:
                report = scorer["score_release_phases"](
                    root,
                    {
                        "RC_CANDIDATE": root,
                        "FINAL_PUBLIC_ARTIFACT": root,
                    },
                )
            finally:
                globals_dict["score_phase"] = original_score_phase
                globals_dict["_contract"] = original_contract
                globals_dict["_compute_phase_score"] = original_compute
            self.assertEqual(report["status"], "PASS")
            self.assertEqual([item["phase"] for item in report["phases"]], [
                "RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT"
            ])

    def test_preseeded_self_consistent_pair_without_controller_transaction_is_rejected(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as source_directory, tempfile.TemporaryDirectory() as target_directory:
            source = Path(source_directory)
            target = Path(target_directory)
            source_authority = score_invocation_authority(source, "RC_CANDIDATE")
            score_invocation_authority(target, "RC_CANDIDATE")
            commit_frozen_score(
                scorer,
                source,
                "RC_CANDIDATE",
                frozen_score_report("RC_CANDIDATE", "PASS"),
                source_authority,
            )
            source_score, source_receipt = scorer["_phase_score_paths"](
                source, "RC_CANDIDATE"
            )
            target_score, target_receipt = scorer["_phase_score_paths"](
                target, "RC_CANDIDATE"
            )
            target_score.parent.mkdir(parents=True, exist_ok=True)
            target_score.write_bytes(source_score.read_bytes())
            target_receipt.write_bytes(source_receipt.read_bytes())
            invocation_path, transaction_path = scorer["_phase_score_authority_paths"](
                target, "RC_CANDIDATE"
            )
            self.assertFalse(invocation_path.exists())
            self.assertFalse(transaction_path.exists())
            with self.assertRaisesRegex(ValueError, "transaction|preseed|partial"):
                scorer["_load_terminal_score"](target, target, "RC_CANDIDATE")

    def test_frozen_fail_rejects_simultaneous_self_consistent_pass_pair_replacement(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as fail_directory, tempfile.TemporaryDirectory() as pass_directory:
            failed_root = Path(fail_directory)
            pass_root = Path(pass_directory)
            failed_authority = score_invocation_authority(failed_root, "RC_CANDIDATE")
            pass_authority = score_invocation_authority(pass_root, "RC_CANDIDATE")
            commit_frozen_score(
                scorer,
                failed_root,
                "RC_CANDIDATE",
                frozen_score_report("RC_CANDIDATE", "FAIL"),
                failed_authority,
            )
            commit_frozen_score(
                scorer,
                pass_root,
                "RC_CANDIDATE",
                frozen_score_report("RC_CANDIDATE", "PASS"),
                pass_authority,
            )
            failed_score, failed_receipt = scorer["_phase_score_paths"](
                failed_root, "RC_CANDIDATE"
            )
            pass_score, pass_receipt = scorer["_phase_score_paths"](
                pass_root, "RC_CANDIDATE"
            )
            failed_score.write_bytes(pass_score.read_bytes())
            failed_receipt.write_bytes(pass_receipt.read_bytes())
            with self.assertRaisesRegex(ValueError, "transaction|authority|hash"):
                scorer["_load_terminal_score"](
                    failed_root, failed_root, "RC_CANDIDATE"
                )

    def test_terminal_transaction_rejects_nonderivable_attempt_build_and_outcome(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        mutations = {
            "attempt": lambda score: score["attempts"][0].__setitem__("attempt_id", "invented-attempt"),
            "build": lambda score: score["installed_build_ref"].__setitem__("hash", "sha256:" + "f" * 64),
            "outcome": lambda score: (
                score.__setitem__("status", "PASS"),
                score.__setitem__("issues", []),
                score["score"].__setitem__("passed", 27),
                score["attempts"][0].__setitem__("status", "PASS"),
                score["attempts"][0].__setitem__("issues", []),
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                authority = score_invocation_authority(root, "RC_CANDIDATE")
                commit_frozen_score(
                    scorer,
                    root,
                    "RC_CANDIDATE",
                    frozen_score_report("RC_CANDIDATE", "FAIL"),
                    authority,
                )
                score_path, receipt_path = scorer["_phase_score_paths"](
                    root, "RC_CANDIDATE"
                )
                score = load_json(score_path)
                mutate(score)
                score_path.write_text(
                    json.dumps(score, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                receipt = load_json(receipt_path)
                receipt["score_ref"]["hash"] = file_hash(score_path)
                receipt["terminal_outcome"] = score["status"]
                receipt_path.write_text(
                    json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "transaction|validation|authority|hash"):
                    scorer["_load_terminal_score"](root, root, "RC_CANDIDATE")

    def test_stored_replay_checks_canonical_freeze_before_fast_path(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            globals_dict = scorer["score_phase"].__globals__
            original_freeze = globals_dict["_canonical_preregistration_issues"]
            original_prepare = globals_dict["_prepare_score_invocation"]
            original_compute = globals_dict["_compute_phase_score"]
            globals_dict["_canonical_preregistration_issues"] = lambda: []
            globals_dict["_prepare_score_invocation"] = (
                lambda *_args, **_kwargs: authority
            )
            globals_dict["_compute_phase_score"] = (
                lambda *_args, **_kwargs: frozen_score_report(
                    "RC_CANDIDATE", "FAIL"
                )
            )
            try:
                first = scorer["score_phase"](root, root, "RC_CANDIDATE")
                self.assertEqual(first["status"], "FAIL")
            finally:
                globals_dict["_canonical_preregistration_issues"] = original_freeze
                globals_dict["_prepare_score_invocation"] = original_prepare
                globals_dict["_compute_phase_score"] = original_compute
            globals_dict = scorer["score_phase"].__globals__
            original_freeze = globals_dict["_canonical_preregistration_issues"]
            original_compute = globals_dict["_compute_phase_score"]
            for drift in (
                "expected_ref", "run_contract_ref", "preregistration_ref", "scorer_ref"
            ):
                with self.subTest(drift=drift):
                    globals_dict["_canonical_preregistration_issues"] = lambda drift=drift: [drift]
                    globals_dict["_compute_phase_score"] = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                        AssertionError("stored replay must stop before semantic validation")
                    )
                    with self.assertRaisesRegex(ValueError, "frozen score contract"):
                        scorer["score_phase"](root, root, "RC_CANDIDATE")
            globals_dict["_canonical_preregistration_issues"] = original_freeze
            globals_dict["_compute_phase_score"] = original_compute

    def test_release_aggregation_requires_authoritative_phase_transactions(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for phase in ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT"):
                authority = score_invocation_authority(root, phase)
                commit_frozen_score(
                    scorer, root, phase, frozen_score_report(phase, "PASS"), authority
                )
            _invocation, transaction = scorer["_phase_score_authority_paths"](
                root, "FINAL_PUBLIC_ARTIFACT"
            )
            transaction.unlink()
            with self.assertRaisesRegex(ValueError, "transaction|partial"):
                scorer["score_release_phases"](
                    root,
                    {
                        "RC_CANDIDATE": root,
                        "FINAL_PUBLIC_ARTIFACT": root,
                    },
                )

    def test_commit_rejects_caller_supplied_fabricated_pass_report(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            fabricated = frozen_score_report("RC_CANDIDATE", "PASS")
            fabricated["attempts"][0]["run_id"] = "invented-run"
            fabricated["attempts"][0]["attempt_id"] = "invented-attempt"
            with self.assertRaisesRegex(
                (TypeError, ValueError), "validated derivation|caller-supplied"
            ):
                scorer["_commit_terminal_score"](
                    root, "RC_CANDIDATE", fabricated, authority
                )

    def test_release_rederives_and_rejects_two_fabricated_pass_phase_bundles(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for phase in ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT"):
                authority = score_invocation_authority(root, phase)
                fabricated = frozen_score_report(phase, "PASS")
                fabricated["attempts"][0]["run_id"] = f"invented-{phase}-run"
                fabricated["attempts"][0]["attempt_id"] = (
                    f"invented-{phase}-attempt"
                )
                commit_frozen_score(
                    scorer, root, phase, fabricated, authority
                )
            globals_dict = scorer["score_release_phases"].__globals__
            original_contract = globals_dict["_contract"]
            original_compute = globals_dict["_compute_phase_score"]
            globals_dict["_contract"] = lambda: {
                "preregistration_issues": lambda: [],
                "cross_phase_freshness_issues": lambda *_args: [],
            }
            globals_dict["_compute_phase_score"] = (
                lambda _root, _skill, phase: frozen_score_report(phase, "PASS")
            )
            try:
                with self.assertRaisesRegex(
                    (ValueError, KeyError),
                    "deriv|evidence|identity|precondition|manifest|entry",
                ):
                    scorer["score_release_phases"](
                        root,
                        {
                            "RC_CANDIDATE": root,
                            "FINAL_PUBLIC_ARTIFACT": root,
                        },
                    )
            finally:
                globals_dict["_contract"] = original_contract
                globals_dict["_compute_phase_score"] = original_compute

    def test_terminal_fail_cannot_be_unlinked_and_recreated_as_pass(self) -> None:
        scorer = runpy.run_path(str(ROOT / "evaluator/score_results.py"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = score_invocation_authority(root, "RC_CANDIDATE")
            globals_dict = scorer["score_phase"].__globals__
            original_freeze = globals_dict["_canonical_preregistration_issues"]
            original_prepare = globals_dict["_prepare_score_invocation"]
            original_compute = globals_dict["_compute_phase_score"]
            globals_dict["_canonical_preregistration_issues"] = lambda: []
            globals_dict["_prepare_score_invocation"] = (
                lambda *_args, **_kwargs: authority
            )
            globals_dict["_compute_phase_score"] = (
                lambda *_args, **_kwargs: frozen_score_report(
                    "RC_CANDIDATE", "FAIL"
                )
            )
            try:
                first = scorer["score_phase"](root, root, "RC_CANDIDATE")
                self.assertEqual(first["status"], "FAIL")
            finally:
                globals_dict["_canonical_preregistration_issues"] = original_freeze
                globals_dict["_prepare_score_invocation"] = original_prepare
                globals_dict["_compute_phase_score"] = original_compute
            score_path, receipt_path = scorer["_phase_score_paths"](
                root, "RC_CANDIDATE"
            )
            invocation_path, transaction_path = scorer[
                "_phase_score_authority_paths"
            ](root, "RC_CANDIDATE")
            for path in (
                invocation_path,
                score_path,
                receipt_path,
                transaction_path,
            ):
                path.unlink()
            original_compute = globals_dict["_compute_phase_score"]
            globals_dict["_compute_phase_score"] = (
                lambda *_args, **_kwargs: frozen_score_report(
                    "RC_CANDIDATE", "PASS"
                )
            )
            try:
                with self.assertRaisesRegex(ValueError, "ledger|terminal|ancestry"):
                    scorer["score_phase"](root, root, "RC_CANDIDATE")
            finally:
                globals_dict["_compute_phase_score"] = original_compute


if __name__ == "__main__":
    unittest.main()
