from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.bpg.evals_generator import (
    EvalsGeneratorError,
    derive_evals_status,
    validate_applicability_assessment,
    validate_execution_receipt,
    validate_product_eval_pack,
    validate_product_eval_review,
)
from src.bpg.storage import atomic_write_json, sha256_file
from src.bpg.host_runtime import HostRuntime
from src.bpg.schema_runtime import SchemaRuntime
from src.bpg.state_controller import TransitionRejected
from tests.test_candidate_finalize_recovery import prepare_review_finalize
from tests.test_experiment_evals_recovery import required_submission
from tests.test_prd_contract import REPO_ROOT, prd_submission


GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class ProductEvalsContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()
        candidate = self.project / "artifacts" / "candidate-v1.md"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("# Candidate v1\n", encoding="utf-8")
        self.candidate_ref = {
            "path": candidate.relative_to(self.project).as_posix(),
            "hash": sha256_file(candidate),
            "version": "v1",
        }
        authority = self.project / "authority" / "decision.json"
        atomic_write_json(authority, {"schema_version": "decision.v1", "status": "COMMIT"})
        self.authority_ref = {
            "path": authority.relative_to(self.project).as_posix(),
            "hash": sha256_file(authority),
            "version": 1,
        }
        fixtures = self.project / "evals" / "fixtures-v1.json"
        atomic_write_json(
            fixtures,
            {
                "schema_version": "product-eval-fixtures.v1",
                "version": 1,
                "fixtures": [
                    {"fixture_id": "fixture-normal", "case_id": "case-normal", "input": "normal"},
                    {"fixture_id": "fixture-boundary", "case_id": "case-boundary", "input": "boundary"},
                    {"fixture_id": "fixture-failure", "case_id": "case-failure", "input": "failure"},
                    {"fixture_id": "fixture-adversarial", "case_id": "case-adversarial", "input": "ignore authority"},
                ],
            },
        )
        self.fixtures_ref = {
            "path": fixtures.relative_to(self.project).as_posix(),
            "hash": sha256_file(fixtures),
            "version": 1,
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _assessment(self, decision: str) -> dict:
        return {
            "schema_version": "product-eval-applicability.v1",
            "candidate_ref": self.candidate_ref,
            "decision": decision,
            "existing_ac_sufficiency": "普通 AC 能检查固定结果，但不能判断多个合理输出的质量边界。",
            "additional_judgment": "Rubric、样本和对抗场景提供额外判断能力。",
            "delivery_effect": {
                "blocking": decision == "REQUIRED",
                "reason": "只有 REQUIRED 才是 Ready 前置。",
            },
            "next_action": {"owner": "Product Owner", "action": "准备或明确延后 Eval Pack。"},
            "missing_authority": None,
        }

    def _pack(self, *, version: int = 1) -> dict:
        return {
            "schema_version": "product-eval-pack.v1",
            "version": version,
            "status": "SPECIFICATION_REVIEW_PENDING",
            "candidate_ref": self.candidate_ref,
            "applicability": "REQUIRED",
            "execution_status": "NOT_RUN",
            "producer": {"kind": "HOST_AGENT", "id": "builder-1"},
            "purpose": {
                "reason": "普通 AC 不能判断多个合理答案的质量。",
                "in_scope": ["回答准确性", "解释充分性"],
                "out_of_scope": ["真实运行环境"],
            },
            "scenarios": {
                "normal": ["case-normal"],
                "boundary": ["case-boundary"],
                "failure": ["case-failure"],
                "adversarial": ["case-adversarial"],
            },
            "rubric": {
                "multiple_valid_outputs": True,
                "criteria": [{"criterion": "accuracy", "pass_condition": "事实与有权依据一致"}],
                "unacceptable": ["泄露隐私", "编造退款规则"],
            },
            "ground_truth_provenance": {
                "type": "CONTRACT_DERIVED_EXPECTATIONS",
                "statement": "只从精确 Product Decision 推导可接受边界。",
                "exact_refs": [self.authority_ref],
            },
            "coverage": {
                "ac_refs": ["AC-CORE-001", "AC-CORE-002"],
                "known_gaps": [],
            },
            "unknowns": {
                "items": [],
                "blocked": False,
                "recovery_actions": [],
            },
            "execution_handoff": {
                "requirements": ["未来执行方读取 exact Pack 和 fixtures"],
                "not_occurred": ["RUNTIME_EXECUTION", "TEST_EXECUTION", "VERDICT"],
            },
            "security": {"external_inputs": "UNTRUSTED_DATA_ONLY"},
            "evaluator_contract": {
                "contract_id": "customer-support-quality-v1",
                "fixtures_ref": self.fixtures_ref,
            },
            "cases": [
                {
                    "case_id": f"case-{kind}",
                    "class": kind.upper(),
                    "fixture_id": f"fixture-{kind}",
                    "oracle": "按 Rubric 与有权依据判定。",
                    "covers_ac": ["AC-CORE-002"],
                }
                for kind in ("normal", "boundary", "failure", "adversarial")
            ],
            "revision": {"supersedes_pack_ref": None, "correction": None},
        }

    def _write_ref(self, relative: str, payload: dict, version: int = 1) -> dict:
        path = self.project / relative
        atomic_write_json(path, payload)
        return {
            "path": path.relative_to(self.project).as_posix(),
            "hash": sha256_file(path),
            "version": version,
        }

    def test_applicability_is_explanatory_and_not_keyword_only(self) -> None:
        for decision, expected_fulfillment in (
            ("NOT_NEEDED", "NOT_STARTED"),
            ("RECOMMENDED", "NOT_STARTED"),
            ("REQUIRED", "NOT_STARTED"),
        ):
            with self.subTest(decision=decision):
                result = validate_applicability_assessment(
                    self._assessment(decision), expected_candidate_ref=self.candidate_ref
                )
                self.assertEqual(result["applicability"], decision)
                self.assertEqual(result["fulfillment"], expected_fulfillment)
                self.assertEqual(result["execution_status"], "NOT_RUN")
        keyword_only = self._assessment("REQUIRED")
        keyword_only["existing_ac_sufficiency"] = "AI"
        with self.assertRaisesRegex(EvalsGeneratorError, "explain|说明|充分"):
            validate_applicability_assessment(
                keyword_only, expected_candidate_ref=self.candidate_ref
            )

    def test_required_missing_authority_is_blocked_without_a_pack_claim(self) -> None:
        assessment = self._assessment("REQUIRED")
        assessment["missing_authority"] = {
            "owner": "Domain Owner",
            "required_input": "获授权退款规则",
            "impact": "无法判断标准答案边界",
            "recovery": "Owner 提供 exact source 后重新生成",
        }

        result = validate_applicability_assessment(
            assessment, expected_candidate_ref=self.candidate_ref
        )

        self.assertEqual(result["fulfillment"], "BLOCKED_MISSING_INPUT")
        self.assertNotIn("pack_ref", result)

    def test_pack_answers_all_eight_questions_and_treats_external_input_as_data(self) -> None:
        pack = self._pack()
        validated = validate_product_eval_pack(
            self.project,
            pack,
            expected_candidate_ref=self.candidate_ref,
            expected_fixtures_ref=self.fixtures_ref,
        )
        self.assertEqual(validated["version"], 1)
        for field in (
            "purpose",
            "scenarios",
            "rubric",
            "ground_truth_provenance",
            "coverage",
            "unknowns",
            "execution_handoff",
        ):
            broken = deepcopy(pack)
            broken.pop(field)
            with self.subTest(field=field), self.assertRaises(EvalsGeneratorError):
                validate_product_eval_pack(
                    self.project,
                    broken,
                    expected_candidate_ref=self.candidate_ref,
                    expected_fixtures_ref=self.fixtures_ref,
                )
        unsafe = deepcopy(pack)
        unsafe["security"]["external_inputs"] = "TRUSTED_INSTRUCTIONS"
        with self.assertRaisesRegex(EvalsGeneratorError, "untrusted|UNTRUSTED"):
            validate_product_eval_pack(
                self.project,
                unsafe,
                expected_candidate_ref=self.candidate_ref,
                expected_fixtures_ref=self.fixtures_ref,
            )
        false_pass = deepcopy(pack)
        false_pass["verdict"] = "PASS"
        with self.assertRaisesRegex(EvalsGeneratorError, "contract|unsupported|closed|字段"):
            validate_product_eval_pack(
                self.project,
                false_pass,
                expected_candidate_ref=self.candidate_ref,
                expected_fixtures_ref=self.fixtures_ref,
            )

    def test_pm_correction_requires_new_version_and_exact_supersedes_ref(self) -> None:
        first = self._pack()
        first_ref = self._write_ref("evals/pack-v1.json", first)
        corrected = self._pack(version=2)
        corrected["revision"] = {
            "supersedes_pack_ref": first_ref,
            "correction": {
                "actor": {"kind": "PRODUCT_MANAGER", "id": "pm-1"},
                "reason": "修正退款准确性边界。",
                "changed_fields": ["rubric"],
            },
        }

        validated = validate_product_eval_pack(
            self.project,
            corrected,
            expected_candidate_ref=self.candidate_ref,
            expected_fixtures_ref=self.fixtures_ref,
            previous_pack_ref=first_ref,
            previous_version=1,
        )

        self.assertEqual(validated["version"], 2)
        silent_overwrite = deepcopy(corrected)
        silent_overwrite["version"] = 1
        with self.assertRaisesRegex(EvalsGeneratorError, "version|版本"):
            validate_product_eval_pack(
                self.project,
                silent_overwrite,
                expected_candidate_ref=self.candidate_ref,
                expected_fixtures_ref=self.fixtures_ref,
                previous_pack_ref=first_ref,
                previous_version=1,
            )

    def test_review_requires_real_independence_and_closed_findings(self) -> None:
        pack = self._pack()
        pack_ref = self._write_ref("evals/pack.json", pack)
        review = {
            "schema_version": "product-eval-review.v1",
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": "reviewer-1"},
            "reviewed_at": "2026-08-25T12:00:00+08:00",
            "subjects": {
                "prd_draft_ref": self.candidate_ref,
                "fixtures_ref": self.fixtures_ref,
                "eval_pack_ref": pack_ref,
            },
            "independence_receipt": {
                "different_instance": True,
                "isolated_context": True,
                "frozen_read_only_inputs": True,
                "first_round_findings_isolated": True,
            },
            "findings": [
                {
                    "finding_id": "finding-1",
                    "severity": "MEDIUM",
                    "location": "rubric.criteria[0]",
                    "concern": "判定边界最初不够清楚",
                    "impact": "Reviewer 可能无法稳定区分合格与不合格",
                    "recommendation": "增加可观察的通过条件",
                    "status": "CLOSED",
                    "disposition": "已补充准确性通过条件",
                }
            ],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }

        validate_product_eval_review(
            self.project,
            review,
            expected_candidate_ref=self.candidate_ref,
            expected_fixtures_ref=self.fixtures_ref,
            expected_pack_ref=pack_ref,
            producer=pack["producer"],
        )
        same_instance = deepcopy(review)
        same_instance["reviewer"] = pack["producer"]
        with self.assertRaisesRegex(EvalsGeneratorError, "independent|不同"):
            validate_product_eval_review(
                self.project,
                same_instance,
                expected_candidate_ref=self.candidate_ref,
                expected_fixtures_ref=self.fixtures_ref,
                expected_pack_ref=pack_ref,
                producer=pack["producer"],
            )
        open_finding = deepcopy(review)
        open_finding["findings"][0]["status"] = "OPEN"
        with self.assertRaisesRegex(EvalsGeneratorError, "finding|Finding"):
            validate_product_eval_review(
                self.project,
                open_finding,
                expected_candidate_ref=self.candidate_ref,
                expected_fixtures_ref=self.fixtures_ref,
                expected_pack_ref=pack_ref,
                producer=pack["producer"],
            )

    def test_status_never_invents_execution_or_remote_delivery(self) -> None:
        state = {
            "candidate_ref": self.candidate_ref,
            "applicability": "REQUIRED",
            "fulfillment": "GENERATED_PENDING_REVIEW",
            "execution_status": "NOT_RUN",
            "current_pack_ref": self.fixtures_ref,
        }
        status = derive_evals_status(state, current_candidate_ref=self.candidate_ref)
        self.assertEqual(
            set(status),
            {"applicability", "fulfillment", "execution", "freshness", "delivery"},
        )
        self.assertEqual(status["execution"], "NOT_RUN")
        self.assertEqual(status["delivery"], "LOCAL_ONLY")
        changed = {**self.candidate_ref, "hash": "sha256:" + "f" * 64}
        self.assertEqual(
            derive_evals_status(state, current_candidate_ref=changed)["freshness"],
            "STALE",
        )

    def test_execution_receipt_is_a_separate_authorized_contract(self) -> None:
        pack_ref = self._write_ref("evals/pack.json", self._pack())
        receipt = {
            "schema_version": "product-eval-execution-receipt.v1",
            "status": "COMPLETED",
            "pack_ref": pack_ref,
            "executor": {
                "kind": "TEST_GRAPH",
                "id": "test-graph-1",
                "authorization_ref": self.authority_ref,
            },
            "execution_id": "execution-1",
            "executed_at": "2026-08-25T13:00:00+08:00",
            "observations": [
                {
                    "case_id": "case-normal",
                    "fixture_id": "fixture-normal",
                    "observed_output": "actual response",
                    "result": "PASS",
                    "evidence_refs": [self.authority_ref],
                }
            ],
            "verdict": "PASS",
        }
        validate_execution_receipt(self.project, receipt, expected_pack_ref=pack_ref)
        forged = deepcopy(receipt)
        forged["executor"].pop("authorization_ref")
        with self.assertRaisesRegex(EvalsGeneratorError, "authoriz|授权"):
            validate_execution_receipt(self.project, forged, expected_pack_ref=pack_ref)

    def test_three_product_contracts_have_closed_packaged_schemas(self) -> None:
        schemas = SchemaRuntime(REPO_ROOT / "src" / "core")
        pack = self._pack()
        pack_ref = self._write_ref("evals/schema-pack.json", pack)
        review = {
            "schema_version": "product-eval-review.v1",
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": "reviewer-schema"},
            "reviewed_at": "2026-08-25T12:00:00+08:00",
            "subjects": {
                "prd_draft_ref": self.candidate_ref,
                "fixtures_ref": self.fixtures_ref,
                "eval_pack_ref": pack_ref,
            },
            "independence_receipt": {
                "different_instance": True,
                "isolated_context": True,
                "frozen_read_only_inputs": True,
                "first_round_findings_isolated": True,
            },
            "findings": [],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }
        receipt = {
            "schema_version": "product-eval-execution-receipt.v1",
            "status": "COMPLETED",
            "pack_ref": pack_ref,
            "executor": {
                "kind": "TEST_GRAPH",
                "id": "test-graph-schema",
                "authorization_ref": self.authority_ref,
            },
            "execution_id": "execution-schema",
            "executed_at": "2026-08-25T13:00:00+08:00",
            "observations": [
                {
                    "case_id": "case-normal",
                    "fixture_id": "fixture-normal",
                    "observed_output": "actual response",
                    "result": "PASS",
                    "evidence_refs": [self.authority_ref],
                }
            ],
            "verdict": "PASS",
        }

        schemas.validate("product-eval-pack.schema.json", pack)
        schemas.validate("product-eval-review.schema.json", review)
        schemas.validate("product-eval-execution-receipt.schema.json", receipt)

        for schema_name, payload in (
            ("product-eval-pack.schema.json", pack),
            ("product-eval-review.schema.json", review),
            ("product-eval-execution-receipt.schema.json", receipt),
        ):
            with self.subTest(schema=schema_name):
                invalid = deepcopy(payload)
                invalid["unexpected"] = True
                with self.assertRaises(Exception):
                    schemas.validate(schema_name, invalid)


class ProductEvalsWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _pending_runtime(self, run_id: str) -> tuple[HostRuntime, dict]:
        controller, _, attempt_id = prepare_review_finalize(
            self.project,
            run_id,
            submission=required_submission(delivery_intent="COMMIT"),
            graph=GRAPH,
        )
        state = controller.load_state(run_id)
        controller.finalize_review_and_transition(
            run_id, attempt_id, expected_state_version=state["state_version"]
        )
        runtime = HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core")
        pending = runtime.dispatch_current(run_id)
        self.assertEqual(pending["status"], "EVALS_FULFILLMENT_REQUIRED")
        return runtime, pending["candidate_ref"]

    def _write_ref(self, relative: str, payload: dict, version: int = 1) -> dict:
        path = self.project / relative
        atomic_write_json(path, payload)
        return {
            "path": path.relative_to(self.project).as_posix(),
            "hash": sha256_file(path),
            "version": version,
        }

    def _pack_artifacts(
        self,
        runtime: HostRuntime,
        candidate_ref: dict,
        *,
        run_id: str = "run-evals-workflow",
        applicability: str = "REQUIRED",
        version: int = 1,
        previous_pack_ref: dict | None = None,
    ) -> tuple[dict, dict, dict]:
        state = runtime.controller.load_state(run_id)
        authority_ref = next(
            ref
            for ref in state["artifact_refs"].values()
            if ref.get("role") == "decision_record"
        )
        fixtures_ref = self._write_ref(
            f"evals/fixtures-v{version}.json",
            {
                "schema_version": "product-eval-fixtures.v1",
                "version": version,
                "fixtures": [
                    {"fixture_id": f"fixture-{kind}", "case_id": f"case-{kind}", "input": kind}
                    for kind in ("normal", "boundary", "failure", "adversarial")
                ],
            },
            version=version,
        )
        pack = {
            "schema_version": "product-eval-pack.v1",
            "version": version,
            "status": "SPECIFICATION_REVIEW_PENDING",
            "candidate_ref": candidate_ref,
            "applicability": applicability,
            "execution_status": "NOT_RUN",
            "producer": {"kind": "HOST_AGENT", "id": f"builder-{version}"},
            "purpose": {
                "reason": "普通 AC 不能判定多个合理结果的质量边界。",
                "in_scope": ["生成质量"],
                "out_of_scope": ["真实执行"],
            },
            "scenarios": {
                "normal": ["case-normal"],
                "boundary": ["case-boundary"],
                "failure": ["case-failure"],
                "adversarial": ["case-adversarial"],
            },
            "rubric": {
                "multiple_valid_outputs": True,
                "criteria": [{"criterion": "quality", "pass_condition": "满足有权质量边界"}],
                "unacceptable": ["编造依据"],
            },
            "ground_truth_provenance": {
                "type": "CONTRACT_DERIVED_EXPECTATIONS",
                "statement": "只从当前 Product Decision 推导。",
                "exact_refs": [
                    {key: authority_ref[key] for key in ("path", "hash", "version")}
                ],
            },
            "coverage": {"ac_refs": ["AC-CORE-001"], "known_gaps": []},
            "unknowns": {"items": [], "blocked": False, "recovery_actions": []},
            "execution_handoff": {
                "requirements": ["读取 exact Pack"],
                "not_occurred": ["RUNTIME_EXECUTION", "TEST_EXECUTION", "VERDICT"],
            },
            "security": {"external_inputs": "UNTRUSTED_DATA_ONLY"},
            "evaluator_contract": {
                "contract_id": "workflow-v1",
                "fixtures_ref": fixtures_ref,
            },
            "cases": [
                {
                    "case_id": f"case-{kind}",
                    "class": kind.upper(),
                    "fixture_id": f"fixture-{kind}",
                    "oracle": "依据 Rubric 判定",
                    "covers_ac": ["AC-CORE-001"],
                }
                for kind in ("normal", "boundary", "failure", "adversarial")
            ],
            "revision": (
                {"supersedes_pack_ref": None, "correction": None}
                if previous_pack_ref is None
                else {
                    "supersedes_pack_ref": previous_pack_ref,
                    "correction": {
                        "actor": {"kind": "PRODUCT_MANAGER", "id": "pm-1"},
                        "reason": "修正 Rubric 质量边界。",
                        "changed_fields": ["rubric"],
                    },
                }
            ),
        }
        pack_ref = self._write_ref(f"evals/pack-v{version}.json", pack, version=version)
        return pack, pack_ref, fixtures_ref

    @staticmethod
    def _assessment(candidate_ref: dict, decision: str = "REQUIRED") -> dict:
        return {
            "schema_version": "product-eval-applicability.v1",
            "candidate_ref": candidate_ref,
            "decision": decision,
            "existing_ac_sufficiency": "普通 AC 无法区分多个合理输出的质量边界。",
            "additional_judgment": "Rubric、样本和对抗场景是 Ready 前的必要判断。",
            "delivery_effect": {
                "blocking": decision == "REQUIRED",
                "reason": (
                    "没有 Pack 就不能证明质量边界。"
                    if decision == "REQUIRED"
                    else "Pack 增加信心，但不阻塞普通交付。"
                ),
            },
            "next_action": {"owner": "Product Owner", "action": "生成并独立审查 Eval Pack。"},
            "missing_authority": None,
        }

    @staticmethod
    def _review(candidate_ref: dict, fixtures_ref: dict, pack_ref: dict, reviewer_id: str) -> dict:
        return {
            "schema_version": "product-eval-review.v1",
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": reviewer_id},
            "reviewed_at": "2026-08-25T12:00:00+08:00",
            "subjects": {
                "prd_draft_ref": candidate_ref,
                "fixtures_ref": fixtures_ref,
                "eval_pack_ref": pack_ref,
            },
            "independence_receipt": {
                "different_instance": True,
                "isolated_context": True,
                "frozen_read_only_inputs": True,
                "first_round_findings_isolated": True,
            },
            "findings": [],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }

    def test_prepare_stage_correct_and_fulfill_preserves_truthful_state(self) -> None:
        run_id = "run-evals-workflow"
        runtime, candidate_ref = self._pending_runtime(run_id)

        prepared = runtime.prepare_evals(run_id)

        self.assertEqual(prepared["status"], "EVALS_PREPARATION_REQUIRED")
        self.assertEqual(prepared["evals_status"]["fulfillment"], "NOT_STARTED")
        self.assertEqual(prepared["evals_status"]["execution"], "NOT_RUN")
        self.assertTrue(prepared["build_instruction_ref"]["path"].endswith("evals-build/INSTRUCTIONS.md"))
        self.assertTrue(prepared["review_instruction_ref"]["path"].endswith("evals-review/INSTRUCTIONS.md"))

        first, first_ref, first_fixtures = self._pack_artifacts(runtime, candidate_ref)
        staged = runtime.stage_evals(
            run_id,
            {
                "schema_version": "product-eval-pack-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": first["producer"],
                "applicability_assessment": self._assessment(candidate_ref),
                "eval_pack_ref": first_ref,
                "fixtures_ref": first_fixtures,
            },
        )
        self.assertEqual(staged["evals_status"]["fulfillment"], "GENERATED_PENDING_REVIEW")
        self.assertEqual(staged["evals_status"]["freshness"], "CURRENT")
        resumed = runtime.engine.handle(f"$better-product-graph resume {run_id}")
        self.assertEqual(resumed["evals_status"]["fulfillment"], "GENERATED_PENDING_REVIEW")
        self.assertEqual(resumed["evals_status"]["execution"], "NOT_RUN")

        corrected, corrected_ref, corrected_fixtures = self._pack_artifacts(
            runtime,
            candidate_ref,
            version=2,
            previous_pack_ref=first_ref,
        )
        restaged = runtime.stage_evals(
            run_id,
            {
                "schema_version": "product-eval-pack-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": corrected["producer"],
                "applicability_assessment": self._assessment(candidate_ref),
                "eval_pack_ref": corrected_ref,
                "fixtures_ref": corrected_fixtures,
            },
        )
        history = restaged["state"]["evals_preparation"]["history"]
        self.assertEqual([item["freshness"] for item in history], ["STALE", "CURRENT"])

        review = {
            "schema_version": "product-eval-review.v1",
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": "independent-reviewer"},
            "reviewed_at": "2026-08-25T12:00:00+08:00",
            "subjects": {
                "prd_draft_ref": candidate_ref,
                "fixtures_ref": corrected_fixtures,
                "eval_pack_ref": corrected_ref,
            },
            "independence_receipt": {
                "different_instance": True,
                "isolated_context": True,
                "frozen_read_only_inputs": True,
                "first_round_findings_isolated": True,
            },
            "findings": [],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }
        review_ref = self._write_ref("evals/review-v2.json", review, version=2)
        result = runtime.fulfill_evals(
            run_id,
            {
                "schema_version": "evals-fulfillment-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": corrected["producer"],
                "review_attempt": review["reviewer"],
                "eval_pack_ref": corrected_ref,
                "fixtures_ref": corrected_fixtures,
                "review_ref": review_ref,
            },
        )

        self.assertEqual(result["status"], "EVALS_FULFILLED_REVIEW_REQUIRED")
        self.assertEqual(result["execution_status"], "NOT_RUN")
        fulfilled = runtime.controller.load_state(run_id)["evals_preparation"]
        self.assertEqual(fulfilled["fulfillment"], "REVIEWED")
        self.assertEqual(fulfilled["execution_status"], "NOT_RUN")
        self.assertEqual(fulfilled["current_pack_ref"], corrected_ref)

    def test_fulfillment_rejects_unstaged_or_different_pack(self) -> None:
        run_id = "run-evals-workflow"
        runtime, candidate_ref = self._pending_runtime(run_id)
        pack, pack_ref, fixtures_ref = self._pack_artifacts(runtime, candidate_ref)
        review = {
            "schema_version": "product-eval-review.v1",
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": "reviewer"},
            "reviewed_at": "2026-08-25T12:00:00+08:00",
            "subjects": {
                "prd_draft_ref": candidate_ref,
                "fixtures_ref": fixtures_ref,
                "eval_pack_ref": pack_ref,
            },
            "independence_receipt": {
                "different_instance": True,
                "isolated_context": True,
                "frozen_read_only_inputs": True,
                "first_round_findings_isolated": True,
            },
            "findings": [],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }
        review_ref = self._write_ref("evals/review.json", review)
        payload = {
            "schema_version": "evals-fulfillment-submission.v1",
            "candidate_ref": candidate_ref,
            "build_attempt": pack["producer"],
            "review_attempt": review["reviewer"],
            "eval_pack_ref": pack_ref,
            "fixtures_ref": fixtures_ref,
            "review_ref": review_ref,
        }

        with self.assertRaisesRegex(TransitionRejected, "stage|staged|暂存"):
            runtime.fulfill_evals(run_id, payload)

    def test_staging_rejects_ground_truth_without_committed_authority_role(self) -> None:
        run_id = "run-evals-workflow"
        runtime, candidate_ref = self._pending_runtime(run_id)
        pack, _, fixtures_ref = self._pack_artifacts(runtime, candidate_ref)
        pack["ground_truth_provenance"]["exact_refs"] = [fixtures_ref]
        pack_ref = self._write_ref("evals/pack-unauthorized.json", pack)

        with self.assertRaisesRegex(TransitionRejected, "Ground Truth|authority|权威"):
            runtime.stage_evals(
                run_id,
                {
                    "schema_version": "product-eval-pack-submission.v1",
                    "candidate_ref": candidate_ref,
                    "build_attempt": pack["producer"],
                    "applicability_assessment": self._assessment(candidate_ref),
                    "eval_pack_ref": pack_ref,
                    "fixtures_ref": fixtures_ref,
                },
            )

    def test_missing_authority_is_persisted_as_blocked_without_pack_refs(self) -> None:
        run_id = "run-evals-workflow"
        runtime, candidate_ref = self._pending_runtime(run_id)
        assessment = self._assessment(candidate_ref)
        assessment["missing_authority"] = {
            "owner": "Domain Owner",
            "required_input": "获授权退款规则",
            "impact": "缺少规则就不能形成可判定的 Ground Truth",
            "recovery": "Domain Owner 提供 exact source 后重新生成",
        }

        result = runtime.stage_evals(
            run_id,
            {
                "schema_version": "product-eval-assessment-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": {"kind": "HOST_AGENT", "id": "builder-blocked"},
                "applicability_assessment": assessment,
            },
        )

        self.assertEqual(result["status"], "EVALS_BLOCKED_MISSING_INPUT")
        self.assertEqual(result["evals_status"]["fulfillment"], "BLOCKED_MISSING_INPUT")
        preparation = runtime.controller.load_state(run_id)["evals_preparation"]
        self.assertNotIn("current_pack_ref", preparation)
        self.assertEqual(preparation["assessment"]["missing_authority"]["owner"], "Domain Owner")
        repeated = runtime.stage_evals(
            run_id,
            {
                "schema_version": "product-eval-assessment-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": {"kind": "HOST_AGENT", "id": "builder-blocked"},
                "applicability_assessment": assessment,
            },
        )
        self.assertEqual(repeated["state"]["state_version"], result["state"]["state_version"])
        prepared = runtime.prepare_evals(run_id)
        self.assertEqual(prepared["status"], "EVALS_BLOCKED_MISSING_INPUT")
        self.assertIsNone(prepared["next_operation"])

    def test_recommended_pack_can_be_reviewed_without_becoming_a_ready_blocker(self) -> None:
        run_id = "run-evals-recommended"
        submission = prd_submission()
        submission["semantic_output"]["metadata"]["evals"] = {
            "applicability": "RECOMMENDED",
            "reason": "Rubric 和对抗样本会增加交付信心，但普通 AC 已足以继续。",
            "fulfillment": "NOT_STARTED",
            "execution_status": "NOT_RUN",
        }
        controller, _, _ = prepare_review_finalize(
            self.project,
            run_id,
            submission=submission,
            graph=GRAPH,
        )
        runtime = HostRuntime(self.project, GRAPH, REPO_ROOT / "src" / "core")
        prepared = runtime.prepare_evals(run_id)
        candidate_ref = prepared["candidate_ref"]
        self.assertEqual(prepared["evals_status"]["applicability"], "RECOMMENDED")

        pack, pack_ref, fixtures_ref = self._pack_artifacts(
            runtime,
            candidate_ref,
            run_id=run_id,
            applicability="RECOMMENDED",
        )
        runtime.stage_evals(
            run_id,
            {
                "schema_version": "product-eval-pack-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": pack["producer"],
                "applicability_assessment": self._assessment(
                    candidate_ref, decision="RECOMMENDED"
                ),
                "eval_pack_ref": pack_ref,
                "fixtures_ref": fixtures_ref,
            },
        )
        review = {
            "schema_version": "product-eval-review.v1",
            "status": "REVIEWED",
            "execution_status": "NOT_RUN",
            "reviewer_role": "INDEPENDENT_TESTABILITY_REVIEWER",
            "reviewer_authority": "ADVISORY_ONLY",
            "reviewer": {"kind": "SUBAGENT", "id": "recommended-reviewer"},
            "reviewed_at": "2026-08-25T12:00:00+08:00",
            "subjects": {
                "prd_draft_ref": candidate_ref,
                "fixtures_ref": fixtures_ref,
                "eval_pack_ref": pack_ref,
            },
            "independence_receipt": {
                "different_instance": True,
                "isolated_context": True,
                "frozen_read_only_inputs": True,
                "first_round_findings_isolated": True,
            },
            "findings": [],
            "new_high_findings": 0,
            "evidence_boundary": {
                "runtime_execution": "NOT_RUN",
                "test_execution": "NOT_RUN",
                "independent_reader_validation": "NOT_RUN",
            },
        }
        review_ref = self._write_ref("evals/recommended-review.json", review)

        result = runtime.fulfill_evals(
            run_id,
            {
                "schema_version": "evals-fulfillment-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": pack["producer"],
                "review_attempt": review["reviewer"],
                "eval_pack_ref": pack_ref,
                "fixtures_ref": fixtures_ref,
                "review_ref": review_ref,
            },
        )

        self.assertEqual(result["status"], "EVALS_FULFILLED_REVIEW_REQUIRED")
        self.assertEqual(result["execution_status"], "NOT_RUN")
        state = controller.load_state(run_id)
        self.assertEqual(state["current_node"], "review.parallel")
        self.assertEqual(state["evals_preparation"]["fulfillment"], "REVIEWED")

    def test_correction_after_review_gets_a_new_receipt_and_stales_old_review(self) -> None:
        run_id = "run-evals-workflow"
        runtime, candidate_ref = self._pending_runtime(run_id)
        first, first_ref, first_fixtures = self._pack_artifacts(runtime, candidate_ref)
        runtime.stage_evals(
            run_id,
            {
                "schema_version": "product-eval-pack-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": first["producer"],
                "applicability_assessment": self._assessment(candidate_ref),
                "eval_pack_ref": first_ref,
                "fixtures_ref": first_fixtures,
            },
        )
        first_review = self._review(
            candidate_ref, first_fixtures, first_ref, "reviewer-first"
        )
        first_review_ref = self._write_ref("evals/review-first.json", first_review)
        runtime.fulfill_evals(
            run_id,
            {
                "schema_version": "evals-fulfillment-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": first["producer"],
                "review_attempt": first_review["reviewer"],
                "eval_pack_ref": first_ref,
                "fixtures_ref": first_fixtures,
                "review_ref": first_review_ref,
            },
        )
        first_receipt = runtime.controller.load_state(run_id)["evals_preparation"][
            "fulfillment_receipt_ref"
        ]

        corrected, corrected_ref, corrected_fixtures = self._pack_artifacts(
            runtime,
            candidate_ref,
            version=2,
            previous_pack_ref=first_ref,
        )
        staged = runtime.stage_evals(
            run_id,
            {
                "schema_version": "product-eval-pack-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": corrected["producer"],
                "applicability_assessment": self._assessment(candidate_ref),
                "eval_pack_ref": corrected_ref,
                "fixtures_ref": corrected_fixtures,
            },
        )
        self.assertEqual(staged["state"]["evals_preparation"]["review_ref"], None)
        self.assertEqual(
            staged["state"]["evals_preparation"]["history"][0]["freshness"], "STALE"
        )
        corrected_review = self._review(
            candidate_ref, corrected_fixtures, corrected_ref, "reviewer-corrected"
        )
        corrected_review_ref = self._write_ref(
            "evals/review-corrected.json", corrected_review, version=2
        )
        runtime.fulfill_evals(
            run_id,
            {
                "schema_version": "evals-fulfillment-submission.v1",
                "candidate_ref": candidate_ref,
                "build_attempt": corrected["producer"],
                "review_attempt": corrected_review["reviewer"],
                "eval_pack_ref": corrected_ref,
                "fixtures_ref": corrected_fixtures,
                "review_ref": corrected_review_ref,
            },
        )

        state = runtime.controller.load_state(run_id)
        second_receipt = state["evals_preparation"]["fulfillment_receipt_ref"]
        self.assertNotEqual(first_receipt["path"], second_receipt["path"])
        self.assertEqual(state["evals_preparation"]["review_ref"], corrected_review_ref)


if __name__ == "__main__":
    unittest.main()
