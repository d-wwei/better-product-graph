from __future__ import annotations

import copy
import ast
import hashlib
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.build_plugin import build_plugin
from src.bpg.host_runtime import HostRuntime
from src.bpg.runner import prepare_writing_eval, review_writing_eval
from src.bpg.storage import (
    append_event,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_event_chain,
)
from src.bpg.writing_eval import WritingEvalError, WritingEvalRuntime
from src.bpg.writing_eval_review_contract import RESULT_FIELDS


REPO_ROOT = Path(__file__).resolve().parents[1]


def exact_ref(root: Path, path: Path, version: str | int = 1) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": sha256_file(path),
        "version": version,
    }


def write_agent_case(project: Path, *, suite_version: str = "0.4") -> tuple[str, dict]:
    case_id = "case-001"
    suite_id = f"better-product-graph-prd-readability-v{suite_version}"
    case_root = project / case_id
    case_root.mkdir(parents=True)
    candidate = case_root / "candidate.md"
    candidate.write_text(
        "# 退款进度提醒\n\n"
        "## 一页结论\n\n用户提交退款后可以看到当前阶段和预计完成时间。\n\n"
        "## 主流程\n\n提交退款 → 审核 → 原路退回。\n\n"
        "## 精确规则\n\n失败时保留原申请并提示重试。\n\n"
        "## 验收\n\n用户可以定位当前阶段。\n\n"
        "## 风险、未知与下一步\n\n支付渠道回执时间仍需验证。\n",
        encoding="utf-8",
    )
    suite = project / "agent-suite.json"
    atomic_write_json(
        suite,
        {
            "schema_version": "prd-readability-agent-suite.v0.4",
            "suite_id": suite_id,
            "target_eval_schema": "document-experience-reader-eval.v3.1",
            "evaluator_files_included": False,
            "agent_runtime_status": "NOT_RUN",
            "claim_boundary": "Agent input only; scoring expectations are excluded.",
        },
    )
    case_manifest = case_root / "case-manifest.json"
    atomic_write_json(
        case_manifest,
        {
            "schema_version": "prd-readability-agent-case.v0.4",
            "suite_id": suite_id,
            "case_id": case_id,
            "candidate_ref": {
                "path": "candidate.md",
                "hash": sha256_file(candidate),
                "version": 1,
            },
            "target_eval_schema": "document-experience-reader-eval.v3.1",
            "evaluator_files_included": False,
            "agent_runtime_status": "NOT_RUN",
            "claim_boundary": "Fixture staging is not Writing Reviewer execution or scoring.",
        },
    )
    payload = {
        "schema_version": "writing-eval-prepare.v1",
        "suite_id": suite_id,
        "case_id": case_id,
        "suite_ref": exact_ref(project, suite),
        "case_ref": exact_ref(project, case_manifest),
        "candidate_ref": exact_ref(project, candidate),
        "author_execution_ref": {
            "kind": "HOST_AGENT_ATTEMPT",
            "id": "anon-author-case-001",
        },
    }
    return "writing-eval-case-001", payload


def basis(dispatch: dict) -> list[dict]:
    candidate = dispatch["writing_eval_context"]["candidate_ref"]
    return [
        {
            "path": candidate["path"],
            "hash": candidate["hash"],
            "start_line": 1,
            "end_line": 3,
        }
    ]


def passing_review(dispatch: dict, checkpoint_ref: dict) -> dict:
    context = dispatch["writing_eval_context"]
    return {
        "schema_version": "document-experience-reader-eval.v3.1",
        "evaluation_only": True,
        "authority": "ADVISORY_ONLY",
        "suite_id": context["suite_id"],
        "case_id": context["case_id"],
        "node_id": "writing-eval.review",
        "attempt_id": dispatch["attempt_id"],
        "instruction_ref": dispatch["instruction_ref"],
        "instruction_hash": dispatch["instruction_hash"],
        "input_refs": dispatch["input_refs"],
        "input_hashes": dispatch["input_hashes"],
        "preregistration_checkpoint_ref": checkpoint_ref,
        "candidate_ref": context["candidate_ref"],
        "profile_ref": context["profile_ref"],
        "guide_ref": context["guide_ref"],
        "reviewer_resource_ref": context["reviewer_resource_ref"],
        "output_contract_ref": context["output_contract_ref"],
        "author_execution_ref": context["author_execution_ref"],
        "reviewer_execution_ref": {
            "kind": "HOST_SUBAGENT_ATTEMPT",
            "id": "anon-reviewer-case-001",
        },
        "reviewer_role": "writing_standard",
        "isolated_input_refs": context["isolated_input_refs"],
        "reader_readback": {
            "problem_and_outcome": "退款用户需要知道进度和预计完成时间。",
            "primary_relationships": "退款申请经过审核后原路退回。",
            "mental_model": [
                {"name": "申请", "role": "发起退款"},
                {"name": "审核", "role": "确认退款条件"},
                {"name": "退款", "role": "原路返回资金"},
            ],
            "main_path_and_recovery": "主路径是提交、审核、退回；失败时保留申请并重试。",
            "decision_conditions_and_risks": "渠道回执时间仍待验证。",
            "navigation_map": [
                {"target": "PRODUCT_RULES", "location": "精确规则"},
                {"target": "ACCEPTANCE", "location": "验收"},
                {"target": "RISKS_UNKNOWNS_NEXT", "location": "风险、未知与下一步"},
            ],
        },
        "reader_outcome_failures": [],
        "verbosity_assessment": {
            "verdict": "PASS",
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": basis(dispatch),
            "reason": "主路径短且没有重复表达。",
        },
        "checklist_assessment": {
            "verdict": "PASS",
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": basis(dispatch),
            "reason": "没有把有操作功能的清单误删。",
        },
        "visual_assessment": {
            "verdict": "NOT_NEEDED",
            "observation_status": "NOT_NEEDED",
            "visual_pair_refs": [],
            "issue_types": [],
            "repair_techniques": [],
            "basis_refs": basis(dispatch),
            "reason": "这个简短线性流程不需要配图。",
        },
        "result": "PASS",
        "primary_diagnosis": None,
        "primary_repair_technique": None,
        "claim_boundary": "AGENT_EVAL_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN",
    }


def instruction_example(path: Path, marker: str) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"<!--\s*{re.escape(marker)}\s*-->\s*```json\s*(\{{.*?\}})\s*```",
        text,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing public instruction example: {marker}")
    return json.loads(match.group(1))


def hydrate_instruction_example(
    example: dict,
    dispatch: dict,
    checkpoint_ref: dict,
    *,
    reviewer_id: str,
) -> dict:
    """Replace public placeholders with exact dispatch authority, not hidden source facts."""

    result = copy.deepcopy(example)
    missing = RESULT_FIELDS - set(result)
    extra = set(result) - RESULT_FIELDS
    if missing or extra:
        raise AssertionError(
            f"instruction example missing fields: {sorted(missing)}; "
            f"extra fields: {sorted(extra)}"
        )
    exact_fields = (
        "schema_version",
        "evaluation_only",
        "authority",
        "suite_id",
        "case_id",
        "node_id",
        "attempt_id",
        "instruction_ref",
        "instruction_hash",
        "input_refs",
        "input_hashes",
        "preregistration_checkpoint_ref",
        "candidate_ref",
        "profile_ref",
        "guide_ref",
        "reviewer_resource_ref",
        "output_contract_ref",
        "author_execution_ref",
        "reviewer_role",
        "isolated_input_refs",
        "claim_boundary",
    )
    base = passing_review(dispatch, checkpoint_ref)
    for field in exact_fields:
        result[field] = copy.deepcopy(base[field])
    result["reviewer_execution_ref"] = {
        "kind": "HOST_SUBAGENT_ATTEMPT",
        "id": reviewer_id,
    }
    for failure in result["reader_outcome_failures"]:
        failure["basis_refs"] = basis(dispatch)
    for field in (
        "verbosity_assessment",
        "checklist_assessment",
        "visual_assessment",
    ):
        result[field]["basis_refs"] = basis(dispatch)
    return result


def rewrite_as_legacy_instruction(
    project: Path,
    runtime: WritingEvalRuntime,
    run_id: str,
    *,
    status: str,
    started_event: bool,
    legacy_hash: str = "sha256:17b0d92931125f25c60f61eaa92a445bad950fd048e6638521024f0641a57d89",
) -> str:
    state_path = runtime.run_path(run_id) / "state.json"
    state = read_json(state_path)
    checkpoint_path = project.resolve() / state["preregistration_checkpoint_ref"]["path"]
    checkpoint = read_json(checkpoint_path)
    dispatch_ref = checkpoint["refs"]["dispatch_ref"]
    dispatch_path = project.resolve() / dispatch_ref["path"]
    legacy_dispatch = read_json(dispatch_path)
    legacy_dispatch["instruction_hash"] = legacy_hash
    for ref in legacy_dispatch["writing_eval_context"]["isolated_input_refs"]:
        if ref["path"] == legacy_dispatch["instruction_ref"]:
            ref["hash"] = legacy_hash
    atomic_write_json(dispatch_path, legacy_dispatch)
    checkpoint["refs"]["instruction_ref"]["hash"] = legacy_hash
    checkpoint["refs"]["dispatch_ref"]["hash"] = sha256_file(dispatch_path)
    atomic_write_json(checkpoint_path, checkpoint)
    state["preregistration_checkpoint_ref"]["hash"] = sha256_file(checkpoint_path)
    state["dispatch"] = {**legacy_dispatch, "status": status}
    atomic_write_json(state_path, state)
    if started_event:
        append_event(
            runtime.run_path(run_id) / "events.jsonl",
            {
                "event_type": "WRITING_EVAL_REVIEW_DISPATCHED",
                "actor": "writing-eval-controller",
                "run_id": run_id,
                "attempt_id": state["dispatch"]["attempt_id"],
            },
        )
    return legacy_hash


class WritingEvalRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.plugin = Path(cls.temporary.name) / "plugin"
        build_plugin(REPO_ROOT, cls.plugin)
        cls.skill = cls.plugin / "skills" / "better-product-graph"
        cls.graph = cls.skill / "references" / "graph" / "manifest.json"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_prepare_preregisters_exact_hidden_expected_free_work_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)

            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )

            self.assertEqual(prepared["status"], "WRITING_EVAL_REVIEW_REQUIRED")
            self.assertEqual(prepared["state"]["run_type"], "writing_eval")
            self.assertTrue(prepared["state"]["evaluation_only"])
            self.assertEqual(prepared["state"]["current_node"], "writing-eval.review")
            self.assertEqual(prepared["dispatch"]["node_id"], "writing-eval.review")
            self.assertEqual(
                prepared["dispatch"]["validator"],
                "document_experience_reader_eval_v3_1",
            )
            checkpoint_ref = prepared["preregistration_checkpoint_ref"]
            checkpoint = read_json(project / checkpoint_ref["path"])
            self.assertEqual(checkpoint["status"], "PREREGISTERED_BEFORE_RESULT")
            self.assertEqual(
                set(checkpoint["refs"]),
                {
                    "source_suite_ref",
                    "source_case_ref",
                    "source_candidate_ref",
                    "suite_ref",
                    "case_ref",
                    "candidate_ref",
                    "profile_ref",
                    "guide_ref",
                    "instruction_ref",
                    "reviewer_resource_ref",
                    "output_contract_ref",
                    "installed_build_ref",
                    "dispatch_ref",
                },
            )
            durable = (project / ".better-product-graph" / "writing-evals" / run_id)
            all_bytes = b"\n".join(
                path.read_bytes() for path in durable.rglob("*") if path.is_file()
            )
            for forbidden in (
                b"expected.json",
                b"preregistration.json",
                b"required_primary_diagnosis",
            ):
                self.assertNotIn(forbidden, all_bytes)
            self.assertFalse(
                (project / ".better-product-graph" / "runs" / run_id).exists()
            )

    def test_v05_exported_case_prepares_against_installed_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            contract = REPO_ROOT / "evals" / "prd-readability-v0.5" / "run_contract.py"
            exported = subprocess.run(
                [
                    "python3",
                    str(contract),
                    "--emit-agent-workspace",
                    str(project),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                json.loads(exported.stdout)["workspace_export_status"],
                "EMITTED_NOT_RUN",
            )

            suite = project / "agent-suite.json"
            atomic_write_json(
                suite,
                {
                    "schema_version": "prd-readability-agent-suite.v0.4",
                    "suite_id": "better-product-graph-prd-readability-v0.5",
                    "target_eval_schema": "document-experience-reader-eval.v3.1",
                    "evaluator_files_included": False,
                    "agent_runtime_status": "NOT_RUN",
                    "claim_boundary": "Agent input only; scoring expectations are excluded.",
                },
            )
            case = project / "case-001" / "case-manifest.json"
            candidate = project / "case-001" / "candidate.md"
            payload = {
                "schema_version": "writing-eval-prepare.v1",
                "suite_id": "better-product-graph-prd-readability-v0.5",
                "case_id": "case-001",
                "suite_ref": exact_ref(project, suite),
                "case_ref": exact_ref(project, case),
                "candidate_ref": exact_ref(project, candidate),
                "author_execution_ref": {
                    "kind": "HOST_AGENT_ATTEMPT",
                    "id": "v05-export-author-case-001",
                },
            }

            prepared = WritingEvalRuntime(project, self.skill).prepare(
                "writing-eval-v05-export-case-001",
                payload,
            )

            self.assertEqual(prepared["status"], "WRITING_EVAL_REVIEW_REQUIRED")
            checkpoint = read_json(
                project / prepared["preregistration_checkpoint_ref"]["path"]
            )
            self.assertEqual(
                checkpoint["refs"]["source_case_ref"],
                payload["case_ref"],
            )

    def test_completed_evidence_read_path_revalidates_closed_result_and_controller_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project, suite_version="0.5")
            runtime = WritingEvalRuntime(project, self.skill)
            prepared = runtime.prepare(run_id, payload)
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            runtime.review(run_id, result)

            evidence = runtime.read_completed_evidence(run_id)
            self.assertEqual(evidence["schema_version"], "writing-eval-controller-evidence.v1")
            self.assertEqual(evidence["run_id"], run_id)
            self.assertEqual(evidence["attempt_id"], result["attempt_id"])
            self.assertEqual(evidence["result"], result)
            self.assertEqual(evidence["installed_build_ref"], prepared["dispatch"]["writing_eval_context"]["installed_build_ref"])
            installed_manifest = self.skill.parents[1] / evidence["installed_build_ref"]["path"]
            self.assertTrue(
                installed_manifest.is_file() and not installed_manifest.is_symlink()
            )
            self.assertEqual(
                evidence["installed_build_ref"]["hash"],
                sha256_file(installed_manifest),
            )
            self.assertEqual(
                set(evidence["controller_refs"]),
                {"state_ref", "result_ref", "events_ref", "transaction_ref", "dispatch_ref", "checkpoint_ref"},
            )
            for ref in evidence["controller_refs"].values():
                path = project / ref["path"]
                self.assertTrue(path.is_file() and not path.is_symlink())
                self.assertEqual(ref["hash"], sha256_file(path))

            for index, mutate in enumerate(
                (
                    lambda value: value.pop("reader_readback"),
                    lambda value: value.__setitem__("unknown_field", True),
                    lambda value: value["verbosity_assessment"].pop("basis_refs"),
                    lambda value: value["verbosity_assessment"].pop("reason"),
                    lambda value: value.__setitem__("schema_version", "wrong.v1"),
                ),
                1,
            ):
                bad_run_id = f"writing-eval-invalid-contract-{index}"
                _, bad_payload = write_agent_case(
                    project / f"invalid-{index}", suite_version="0.5"
                )
                bad_project = project / f"invalid-{index}"
                bad_runtime = WritingEvalRuntime(bad_project, self.skill)
                bad_prepared = bad_runtime.prepare(bad_run_id, bad_payload)
                bad = passing_review(
                    bad_prepared["dispatch"],
                    bad_prepared["preregistration_checkpoint_ref"],
                )
                mutate(bad)
                with self.subTest(index=index):
                    with self.assertRaisesRegex(WritingEvalError, "review rejected"):
                        bad_runtime.review(bad_run_id, bad)

            transaction_path = (
                project / evidence["controller_refs"]["transaction_ref"]["path"]
            )
            transaction = read_json(transaction_path)
            transaction["target_state_hash"] = "sha256:" + "0" * 64
            atomic_write_json(transaction_path, transaction)
            with self.assertRaisesRegex(
                WritingEvalError, "transition journal is invalid"
            ):
                runtime.read_completed_evidence(run_id)

    def test_v05_selects_v32_identity_while_reusing_v31_result_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project, suite_version="0.5")

            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )

            dispatch = prepared["dispatch"]
            context = dispatch["writing_eval_context"]
            self.assertEqual(
                dispatch["instruction_ref"],
                "references/atomic-skills/prd-writing-eval-review-v3.2/INSTRUCTIONS.md",
            )
            self.assertEqual(
                context["reviewer_resource_ref"]["path"],
                "references/reviewer-profiles/prd-writing-eval-reader-review-v3.2.json",
            )
            self.assertEqual(context["reviewer_resource_ref"]["version"], "v3.2")
            self.assertEqual(context["profile_ref"]["version"], "0.5.0")
            self.assertEqual(context["guide_ref"]["version"], "0.5.0")
            self.assertEqual(
                context["review_schema"], "document-experience-reader-eval.v3.1"
            )
            self.assertEqual(
                dispatch["validator"], "document_experience_reader_eval_v3_1"
            )
            serialized = canonical_json_bytes(dispatch)
            for hidden in (
                b"primary_objective",
                b"allowed_primary_pairs",
                b"expected.json",
                b"required_primary_diagnosis",
                b"score_threshold",
            ):
                self.assertNotIn(hidden, serialized)

    def test_v04_dispatch_remains_on_byte_exact_v31_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)

            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            dispatch = prepared["dispatch"]
            context = dispatch["writing_eval_context"]

            self.assertEqual(
                dispatch["instruction_ref"],
                "references/atomic-skills/prd-writing-eval-review/INSTRUCTIONS.md",
            )
            self.assertEqual(
                dispatch["instruction_hash"],
                "sha256:cd83efe1ba620e03ad2a0f8a2f2c5b2bb8f3b8e713e87bf0ac7f8fb79800cd9e",
            )
            self.assertEqual(
                context["reviewer_resource_ref"],
                {
                    "path": "references/reviewer-profiles/prd-writing-eval-reader-review-v3.1.json",
                    "hash": "sha256:a56fe9a226b604aa41db1dfaf137f6b671db39a8ac100faa5e1f731038fc65ca",
                    "version": "v3.1",
                },
            )
            self.assertEqual(context["profile_ref"]["version"], "0.4.0")
            self.assertEqual(context["guide_ref"]["version"], "0.4.0")
            self.assertEqual(
                sha256_file(
                    self.skill
                    / "references"
                    / "schemas"
                    / "document-experience-reader-eval-v3.1.schema.json"
                ),
                "sha256:6aa12505bf4e89b99a5d9d7693f03fde99cdfa50cd9514c4a8310165c176b366",
            )

            before = canonical_json_bytes(prepared["state"])
            retried = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            self.assertEqual(canonical_json_bytes(retried["state"]), before)

    def test_eval_result_rejects_evaluator_only_primary_objective(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project, suite_version="0.5")
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            result["primary_objective"] = "MAKE_PEER_STRUCTURE_SCANNABLE"

            with self.assertRaisesRegex(WritingEvalError, "extra|closed"):
                review_writing_eval(
                    project,
                    self.graph,
                    run_id,
                    result,
                    skill_root=self.skill,
                )

    def test_v32_instruction_examples_are_complete_legal_v31_results(self) -> None:
        instruction_path = (
            self.skill
            / "references"
            / "atomic-skills"
            / "prd-writing-eval-review-v3.2"
            / "INSTRUCTIONS.md"
        )
        pass_example = instruction_example(
            instruction_path, "writing-eval-result-contract"
        )
        finding_example = instruction_example(
            instruction_path, "writing-eval-finding-example"
        )
        self.assertEqual(set(pass_example), RESULT_FIELDS)
        self.assertEqual(set(finding_example), RESULT_FIELDS)
        self.assertEqual(
            pass_example["schema_version"],
            "document-experience-reader-eval.v3.1",
        )
        self.assertEqual(finding_example["result"], "FINDING")

        incomplete = copy.deepcopy(pass_example)
        del incomplete["candidate_ref"]
        with self.assertRaisesRegex(AssertionError, "missing.*candidate_ref"):
            hydrate_instruction_example(
                incomplete,
                {
                    "writing_eval_context": {},
                },
                {},
                reviewer_id="anon-incomplete-example",
            )

        for label, example, expected in (
            ("pass", pass_example, "PASS"),
            ("finding", finding_example, "FINDING"),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project, suite_version="0.5")
                prepared = prepare_writing_eval(
                    project, self.graph, run_id, payload, skill_root=self.skill
                )
                result = hydrate_instruction_example(
                    example,
                    prepared["dispatch"],
                    prepared["preregistration_checkpoint_ref"],
                    reviewer_id=f"anon-v32-{label}",
                )

                completed = review_writing_eval(
                    project,
                    self.graph,
                    run_id,
                    result,
                    skill_root=self.skill,
                )

                self.assertEqual(completed["status"], "COMPLETED")
                committed = read_json(project / completed["result_ref"]["path"])
                self.assertEqual(committed["result"], expected)

    def test_valid_review_closes_eval_without_product_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )

            completed = review_writing_eval(
                project,
                self.graph,
                run_id,
                passing_review(
                    prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
                ),
                skill_root=self.skill,
            )

            self.assertEqual(completed["status"], "COMPLETED")
            self.assertTrue(completed["evaluation_only"])
            self.assertEqual(completed["state"]["status"], "COMPLETED")
            self.assertEqual(completed["state"]["current_node"], "writing-eval.review")
            self.assertIsNone(completed["next_operation"])
            self.assertEqual(completed["product_authority"], "NONE")
            serialized = canonical_json_bytes(completed)
            for forbidden in (b"review.aggregate", b"prd.ready.gate", b"handoff", b"release"):
                self.assertNotIn(forbidden, serialized)

    def test_review_identity_schema_and_basis_attacks_fail_without_writes(self) -> None:
        attacks = {
            "same execution": lambda result: result.update(
                {"reviewer_execution_ref": copy.deepcopy(result["author_execution_ref"])}
            ),
            "wrong schema": lambda result: result.update(
                {"schema_version": "document-experience-reader-review.v3"}
            ),
            "stale candidate": lambda result: result["candidate_ref"].update(
                {"hash": "sha256:" + "0" * 64}
            ),
            "basis out of bounds": lambda result: result["verbosity_assessment"][
                "basis_refs"
            ][0].update({"end_line": 999}),
            "hidden expected": lambda result: result.update(
                {"expected_ref": {"path": "expected.json", "hash": "sha256:" + "0" * 64, "version": 1}}
            ),
        }
        for label, attack in attacks.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project)
                prepared = prepare_writing_eval(
                    project, self.graph, run_id, payload, skill_root=self.skill
                )
                result = passing_review(
                    prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
                )
                attack(result)
                runtime = WritingEvalRuntime(project, self.skill)
                before = runtime.read_state(run_id)
                eval_root = runtime.run_path(run_id)
                before_files = {
                    path.relative_to(eval_root).as_posix(): path.read_bytes()
                    for path in eval_root.rglob("*")
                    if path.is_file()
                }

                with self.assertRaises(WritingEvalError):
                    runtime.review(run_id, result)

                self.assertEqual(runtime.read_state(run_id), before)
                self.assertEqual(
                    {
                        path.relative_to(eval_root).as_posix(): path.read_bytes()
                        for path in eval_root.rglob("*")
                        if path.is_file()
                    },
                    before_files,
                )

    def test_retry_is_idempotent_and_identity_drift_is_zero_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            first = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            eval_root = runtime.run_path(run_id)
            before_files = {
                path.relative_to(eval_root).as_posix(): path.read_bytes()
                for path in eval_root.rglob("*")
                if path.is_file()
            }

            retry = prepare_writing_eval(
                project, self.graph, run_id, copy.deepcopy(payload), skill_root=self.skill
            )
            self.assertEqual(retry["dispatch"]["attempt_id"], first["dispatch"]["attempt_id"])
            self.assertEqual(
                {
                    path.relative_to(eval_root).as_posix(): path.read_bytes()
                    for path in eval_root.rglob("*")
                    if path.is_file()
                },
                before_files,
            )

            changed = copy.deepcopy(payload)
            changed["author_execution_ref"]["id"] = "anon-different-author"
            with self.assertRaises(WritingEvalError):
                prepare_writing_eval(
                    project, self.graph, run_id, changed, skill_root=self.skill
                )
            self.assertEqual(
                {
                    path.relative_to(eval_root).as_posix(): path.read_bytes()
                    for path in eval_root.rglob("*")
                    if path.is_file()
                },
                before_files,
            )

    def test_prepare_resume_rejects_tampered_checkpoint_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            checkpoint = project / prepared["preregistration_checkpoint_ref"]["path"]
            checkpoint.write_bytes(checkpoint.read_bytes() + b" ")
            eval_root = runtime.run_path(run_id)
            before = {
                path.relative_to(eval_root).as_posix(): path.read_bytes()
                for path in eval_root.rglob("*")
                if path.is_file()
            }

            with self.assertRaisesRegex(WritingEvalError, "checkpoint"):
                runtime.prepare(run_id, payload)

            self.assertEqual(
                {
                    path.relative_to(eval_root).as_posix(): path.read_bytes()
                    for path in eval_root.rglob("*")
                    if path.is_file()
                },
                before,
            )

    def test_review_rejects_changed_suite_input_and_state_identity_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            suite_path = (
                project
                / prepared["state"]["snapshot_refs"]["suite_ref"]["path"]
            )
            suite_path.write_bytes(suite_path.read_bytes() + b" ")
            eval_root = runtime.run_path(run_id)
            before = {
                path.relative_to(eval_root).as_posix(): path.read_bytes()
                for path in eval_root.rglob("*")
                if path.is_file()
            }

            with self.assertRaisesRegex(WritingEvalError, "snapshot"):
                runtime.review(
                    run_id,
                    passing_review(
                        prepared["dispatch"],
                        prepared["preregistration_checkpoint_ref"],
                    ),
                )

            self.assertEqual(
                {
                    path.relative_to(eval_root).as_posix(): path.read_bytes()
                    for path in eval_root.rglob("*")
                    if path.is_file()
                },
                before,
            )
            result_path = (
                runtime.run_path(run_id)
                / "attempts"
                / prepared["dispatch"]["attempt_id"]
                / "result.json"
            )
            self.assertFalse(result_path.exists())

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            state_path = runtime.run_path(run_id) / "state.json"
            state = read_json(state_path)
            state["prepare_identity_hash"] = "sha256:" + "f" * 64
            atomic_write_json(state_path, state)

            with self.assertRaisesRegex(WritingEvalError, "identity"):
                runtime.read_state(run_id)

    def test_completed_state_requires_exact_completion_event_and_result(self) -> None:
        for materialize_result in (False, True):
            with self.subTest(materialize_result=materialize_result), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project)
                prepared = prepare_writing_eval(
                    project, self.graph, run_id, payload, skill_root=self.skill
                )
                runtime = WritingEvalRuntime(project, self.skill)
                state_path = runtime.run_path(run_id) / "state.json"
                state = read_json(state_path)
                result = passing_review(
                    prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
                )
                result_path = (
                    runtime.run_path(run_id)
                    / "attempts"
                    / prepared["dispatch"]["attempt_id"]
                    / "result.json"
                )
                if materialize_result:
                    atomic_write_json(result_path, result)
                state["status"] = "COMPLETED"
                state["dispatch"]["status"] = "COMPLETED"
                state["result_ref"] = {
                    "path": result_path.relative_to(runtime.project_root).as_posix(),
                    "hash": sha256_file(result_path) if materialize_result else "sha256:" + "0" * 64,
                    "version": 1,
                }
                atomic_write_json(state_path, state)
                before = {
                    path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                    for path in runtime.run_path(run_id).rglob("*")
                    if path.is_file()
                }

                with self.assertRaisesRegex(WritingEvalError, "completion|result"):
                    runtime.read_state(run_id)
                with self.assertRaisesRegex(WritingEvalError, "completion|result"):
                    runtime.prepare(run_id, payload)

                self.assertEqual(
                    {
                        path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                        for path in runtime.run_path(run_id).rglob("*")
                        if path.is_file()
                    },
                    before,
                )

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            completed = runtime.review(
                run_id,
                passing_review(
                    prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
                ),
            )
            result_path = project / completed["result_ref"]["path"]
            replacement = project / "replacement-result.json"
            replacement.write_bytes(result_path.read_bytes())
            result_path.unlink()
            result_path.symlink_to(replacement)

            with self.assertRaisesRegex(WritingEvalError, "result.*unsafe"):
                runtime.read_state(run_id)

    def test_started_event_cannot_be_hidden_by_mutable_planned_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            state_path = runtime.run_path(run_id) / "state.json"
            state = read_json(state_path)
            state["dispatch"]["status"] = "PLANNED"
            atomic_write_json(state_path, state)
            before = {
                path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                for path in runtime.run_path(run_id).rglob("*")
                if path.is_file()
            }

            with self.assertRaisesRegex(WritingEvalError, "started|dispatch event"):
                runtime.prepare(run_id, payload)

            self.assertEqual(
                {
                    path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                    for path in runtime.run_path(run_id).rglob("*")
                    if path.is_file()
                },
                before,
            )

    def test_initial_prepare_recovers_every_prepublish_crash_boundary(self) -> None:
        failpoints = (
            "after_init_transaction",
            "after_input_snapshots",
            "after_dispatch_persist",
            "after_checkpoint_persist",
            "after_state_persist",
            "after_prepared_event",
            "after_initial_publish",
        )
        for failpoint in failpoints:
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project)
                runtime = WritingEvalRuntime(project, self.skill)

                with self.assertRaisesRegex(WritingEvalError, "injected crash"):
                    runtime.prepare(run_id, payload, failpoint=failpoint)

                transaction = next(
                    (
                        path
                        for path in (
                            project / ".better-product-graph" / "writing-evals"
                        ).glob(f".initializing-{run_id}")
                    ),
                    None,
                )
                expected_attempt = None
                if transaction is not None:
                    expected_attempt = read_json(
                        transaction / "init-transaction.json"
                    )["attempt_id"]
                elif runtime.run_path(run_id).exists():
                    expected_attempt = read_json(
                        runtime.run_path(run_id) / "state.json"
                    )["dispatch"]["attempt_id"]

                recovered = runtime.prepare(run_id, payload)

                self.assertEqual(recovered["status"], "WRITING_EVAL_REVIEW_REQUIRED")
                self.assertEqual(recovered["dispatch"]["attempt_id"], expected_attempt)
                self.assertFalse(
                    (
                        project
                        / ".better-product-graph"
                        / "writing-evals"
                        / f".initializing-{run_id}"
                    ).exists()
                )

    def test_review_uses_controller_snapshot_and_rechecks_it_before_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            original_candidate = (project / payload["candidate_ref"]["path"]).read_bytes()
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            context = prepared["dispatch"]["writing_eval_context"]
            snapshot = project / context["candidate_ref"]["path"]
            self.assertTrue(snapshot.is_file())
            self.assertFalse(snapshot.is_symlink())
            self.assertEqual(snapshot.read_bytes(), original_candidate)
            self.assertNotIn("expected", context["candidate_ref"]["path"].casefold())

            (project / payload["candidate_ref"]["path"]).write_text(
                "# source changed after prepare\n", encoding="utf-8"
            )
            (project / payload["suite_ref"]["path"]).write_text(
                "{}\n", encoding="utf-8"
            )
            completed = runtime.review(
                run_id,
                passing_review(
                    prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
                ),
            )
            self.assertEqual(completed["status"], "COMPLETED")

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            candidate_snapshot = (
                project
                / prepared["dispatch"]["writing_eval_context"]["candidate_ref"]["path"]
            )
            import src.bpg.writing_eval as writing_eval_module

            real_validate = writing_eval_module.validate_writing_eval_review

            def validate_then_replace(*args, **kwargs):
                validated = real_validate(*args, **kwargs)
                candidate_snapshot.write_text("# tampered after validation\n", encoding="utf-8")
                return validated

            with mock.patch.object(
                writing_eval_module,
                "validate_writing_eval_review",
                side_effect=validate_then_replace,
            ):
                with self.assertRaisesRegex(WritingEvalError, "snapshot"):
                    runtime.review(run_id, result)

            result_path = (
                runtime.run_path(run_id)
                / "attempts"
                / prepared["dispatch"]["attempt_id"]
                / "result.json"
            )
            self.assertFalse(result_path.exists())

    def test_snapshot_replacement_at_result_write_never_commits_or_returns_completed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            runtime = WritingEvalRuntime(project, self.skill)
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            candidate_snapshot = (
                project.resolve()
                / prepared["dispatch"]["writing_eval_context"]["candidate_ref"]["path"]
            )
            replacement = candidate_snapshot.with_name("replacement-candidate.md")
            replacement.write_bytes(candidate_snapshot.read_bytes())
            import src.bpg.writing_eval as writing_eval_module

            real_write_once = writing_eval_module._write_once_json
            replaced = False

            def replace_snapshot_before_result(path, value, label):
                nonlocal replaced
                if label == "Writing Eval transition result" and not replaced:
                    replaced = True
                    replacement.replace(candidate_snapshot)
                return real_write_once(path, value, label)

            with mock.patch.object(
                writing_eval_module,
                "_write_once_json",
                side_effect=replace_snapshot_before_result,
            ):
                with self.assertRaisesRegex(WritingEvalError, "snapshot custody"):
                    runtime.review(run_id, result)

            raw_state = read_json(runtime.run_path(run_id) / "state.json")
            self.assertEqual(raw_state["status"], "ACTIVE")
            events = verify_event_chain(runtime.run_path(run_id) / "events.jsonl")
            self.assertFalse(
                any(event["event_type"] == "WRITING_EVAL_COMPLETED" for event in events)
            )
            journals = [
                read_json(path)
                for path in (runtime.run_path(run_id) / "transactions").glob("complete-*.json")
            ]
            self.assertEqual(len(journals), 1)
            self.assertEqual(journals[0]["status"], "PREPARED")
            with self.assertRaisesRegex(WritingEvalError, "snapshot custody"):
                runtime.read_state(run_id)

    def test_result_first_crash_recovers_same_attempt_without_duplicate_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepared = prepare_writing_eval(
                project, self.graph, run_id, payload, skill_root=self.skill
            )
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            runtime = WritingEvalRuntime(project, self.skill)
            with self.assertRaisesRegex(WritingEvalError, "injected crash"):
                runtime.review(run_id, result, failpoint="after_result_persist")
            recovered_state = runtime.read_state(run_id)
            self.assertEqual(recovered_state["status"], "COMPLETED")
            result_path = (
                runtime.run_path(run_id)
                / "attempts"
                / prepared["dispatch"]["attempt_id"]
                / "result.json"
            )
            result_bytes = result_path.read_bytes()

            completed = runtime.review(run_id, result)

            self.assertEqual(completed["status"], "COMPLETED")
            self.assertEqual(result_path.read_bytes(), result_bytes)
            events = [
                json.loads(line)
                for line in (runtime.run_path(run_id) / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                sum(item["event_type"] == "WRITING_EVAL_COMPLETED" for item in events),
                1,
            )

    def test_completed_evidence_reader_rejects_pending_transition_without_recovery_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project, suite_version="0.5")
            runtime = WritingEvalRuntime(project, self.skill)
            prepared = runtime.prepare(run_id, payload)
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            with self.assertRaisesRegex(WritingEvalError, "injected crash"):
                runtime.review(
                    run_id,
                    result,
                    failpoint="complete.after_journal_prepared",
                )

            def exact_tree() -> tuple[dict[str, bytes], str]:
                files = {
                    path.relative_to(project).as_posix(): path.read_bytes()
                    for path in sorted(project.rglob("*"))
                    if path.is_file()
                }
                digest = sha256_bytes(
                    canonical_json_bytes(
                        {
                            path: sha256_bytes(value)
                            for path, value in files.items()
                        }
                    )
                )
                return files, digest

            before_files, before_hash = exact_tree()
            with self.assertRaisesRegex(
                WritingEvalError, "completed evidence requires COMPLETED state"
            ):
                runtime.read_completed_evidence(run_id)
            after_files, after_hash = exact_tree()
            self.assertEqual(after_files, before_files)
            self.assertEqual(after_hash, before_hash)

            recovered = runtime.review(run_id, result)
            self.assertEqual(recovered["status"], "COMPLETED")

            outside = project / "unsafe-probe-target"
            outside.mkdir()
            unsafe = (
                project
                / ".better-product-graph"
                / "writing-evals"
                / "unsafe-probe-run"
            )
            unsafe.symlink_to(outside, target_is_directory=True)
            before_unsafe_probe = exact_tree()
            with self.assertRaisesRegex(
                WritingEvalError, "durable Run path is unsafe"
            ):
                runtime.probe_durable_run("unsafe-probe-run")
            self.assertEqual(exact_tree(), before_unsafe_probe)

    def test_dispatch_transition_journal_recovers_both_event_state_orders(self) -> None:
        failpoints = (
            "dispatch.after_journal_prepared",
            "dispatch.after_event_before_state",
            "dispatch.after_state_before_event",
            "dispatch.after_state",
        )
        for failpoint in failpoints:
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project)
                runtime = WritingEvalRuntime(project, self.skill)
                planned = runtime.prepare(
                    run_id, payload, failpoint="after_dispatch_planned"
                )
                attempt_id = planned["dispatch"]["attempt_id"]

                with self.assertRaisesRegex(WritingEvalError, "injected crash"):
                    runtime.prepare(run_id, payload, failpoint=failpoint)

                recovered = runtime.prepare(run_id, payload)
                self.assertEqual(recovered["dispatch"]["attempt_id"], attempt_id)
                self.assertEqual(recovered["state"]["dispatch"]["status"], "DISPATCHED")
                events = verify_event_chain(runtime.run_path(run_id) / "events.jsonl")
                self.assertEqual(
                    sum(
                        event["event_type"] == "WRITING_EVAL_REVIEW_DISPATCHED"
                        and event["attempt_id"] == attempt_id
                        for event in events
                    ),
                    1,
                )

    def test_complete_transition_journal_recovers_result_and_both_orders(self) -> None:
        failpoints = (
            "complete.after_journal_prepared",
            "complete.after_result",
            "complete.after_event_before_state",
            "complete.after_state_before_event",
            "complete.after_state",
        )
        for failpoint in failpoints:
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project)
                prepared = prepare_writing_eval(
                    project, self.graph, run_id, payload, skill_root=self.skill
                )
                runtime = WritingEvalRuntime(project, self.skill)
                result = passing_review(
                    prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
                )

                with self.assertRaisesRegex(WritingEvalError, "injected crash"):
                    runtime.review(run_id, result, failpoint=failpoint)

                recovered = runtime.review(run_id, result)
                self.assertEqual(recovered["status"], "COMPLETED")
                self.assertEqual(
                    recovered["state"]["dispatch"]["attempt_id"],
                    prepared["dispatch"]["attempt_id"],
                )
                events = verify_event_chain(runtime.run_path(run_id) / "events.jsonl")
                self.assertEqual(
                    sum(event["event_type"] == "WRITING_EVAL_COMPLETED" for event in events),
                    1,
                )

    def test_unstarted_known_predecessor_can_be_revoked_but_started_is_zero_write_blocked(self) -> None:
        for status, started_event, should_redispatch in (
            ("PLANNED", False, True),
            ("PLANNED", True, False),
            ("DISPATCHED", True, False),
        ):
            with self.subTest(status=status, started_event=started_event), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project)
                runtime = WritingEvalRuntime(project, self.skill)
                runtime.prepare(run_id, payload, failpoint="after_dispatch_planned")
                legacy_hash = rewrite_as_legacy_instruction(
                    project,
                    runtime,
                    run_id,
                    status=status,
                    started_event=started_event,
                )
                before = {
                    path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                    for path in runtime.run_path(run_id).rglob("*")
                    if path.is_file()
                }

                if should_redispatch:
                    response = runtime.prepare(run_id, payload)
                    self.assertNotEqual(
                        response["dispatch"]["instruction_hash"], legacy_hash
                    )
                    self.assertEqual(response["state"]["superseded_attempts"][0]["status"], "REVOKED_UNSTARTED")
                else:
                    with self.assertRaisesRegex(WritingEvalError, "started|fail closed"):
                        runtime.prepare(run_id, payload)
                    self.assertEqual(
                        {
                            path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                            for path in runtime.run_path(run_id).rglob("*")
                            if path.is_file()
                        },
                        before,
                    )

    def test_public_instruction_predecessors_only_unstarted_can_be_redispatched(self) -> None:
        predecessor_hashes = (
            "sha256:848aaaa15e4e989c8822f1e0ee66a3c992b0b9483fc5eac53df23c7529bc319e",
            "sha256:1a45d58423ec38b1dcd0361523d3997a190f5cff7f62bb5e440e4fb6dff6159c",
        )
        cases = (
            ("PLANNED", False, True),
            ("PLANNED", True, False),
            ("DISPATCHED", True, False),
        )
        for predecessor_hash in predecessor_hashes:
            for status, started_event, should_redispatch in cases:
                with self.subTest(
                    predecessor_hash=predecessor_hash,
                    status=status,
                    started_event=started_event,
                ), tempfile.TemporaryDirectory() as directory:
                    project = Path(directory)
                    run_id, payload = write_agent_case(project)
                    runtime = WritingEvalRuntime(project, self.skill)
                    runtime.prepare(run_id, payload, failpoint="after_dispatch_planned")
                    rewrite_as_legacy_instruction(
                        project,
                        runtime,
                        run_id,
                        status=status,
                        started_event=started_event,
                        legacy_hash=predecessor_hash,
                    )
                    before = {
                        path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                        for path in runtime.run_path(run_id).rglob("*")
                        if path.is_file()
                    }

                    if should_redispatch:
                        response = runtime.prepare(run_id, payload)
                        self.assertNotEqual(
                            response["dispatch"]["instruction_hash"], predecessor_hash
                        )
                        self.assertEqual(
                            response["state"]["superseded_attempts"][0]["status"],
                            "REVOKED_UNSTARTED",
                        )
                    else:
                        with self.assertRaisesRegex(WritingEvalError, "started|fail closed"):
                            runtime.prepare(run_id, payload)
                        self.assertEqual(
                            {
                                path.relative_to(runtime.run_path(run_id)).as_posix(): path.read_bytes()
                                for path in runtime.run_path(run_id).rglob("*")
                                if path.is_file()
                            },
                            before,
                        )

    def test_revoke_transition_journal_recovers_both_event_state_orders(self) -> None:
        failpoints = (
            "revoke.after_journal_prepared",
            "revoke.after_event_before_state",
            "revoke.after_state_before_event",
            "revoke.after_state",
        )
        for failpoint in failpoints:
            with self.subTest(failpoint=failpoint), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                run_id, payload = write_agent_case(project)
                runtime = WritingEvalRuntime(project, self.skill)
                planned = runtime.prepare(
                    run_id, payload, failpoint="after_dispatch_planned"
                )
                old_attempt = planned["dispatch"]["attempt_id"]
                rewrite_as_legacy_instruction(
                    project,
                    runtime,
                    run_id,
                    status="PLANNED",
                    started_event=False,
                )

                with self.assertRaisesRegex(WritingEvalError, "injected crash"):
                    runtime.prepare(run_id, payload, failpoint=failpoint)

                recovered = runtime.prepare(run_id, payload)
                self.assertNotEqual(recovered["dispatch"]["attempt_id"], old_attempt)
                self.assertEqual(
                    recovered["state"]["superseded_attempts"][0]["attempt_id"],
                    old_attempt,
                )
                events = verify_event_chain(runtime.run_path(run_id) / "events.jsonl")
                self.assertEqual(
                    sum(
                        event["event_type"]
                        == "WRITING_EVAL_UNSTARTED_DISPATCH_REVOKED"
                        for event in events
                    ),
                    1,
                )

    def test_evals_generator_contract_fingerprints_remain_exact(self) -> None:
        import src.bpg.evals_fulfillment as fulfillment
        import src.bpg.evals_generator as generator
        import src.bpg.host_runtime as host_runtime
        import src.bpg.runner as runner

        def function_hash(module, name: str) -> str:
            source = Path(module.__file__).read_text(encoding="utf-8")
            tree = ast.parse(source)
            matches = [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name
            ]
            self.assertEqual(len(matches), 1, name)
            segment = ast.get_source_segment(source, matches[0])
            self.assertIsNotNone(segment)
            return "sha256:" + hashlib.sha256(segment.encode()).hexdigest()

        self.assertEqual(
            function_hash(host_runtime, "prepare_evals"),
            "sha256:c813f80e7cd345fd0af6a5cbfe88b475e2178ea5e90ea005a2749afdfd36aa51",
        )
        self.assertEqual(
            function_hash(host_runtime, "stage_evals"),
            "sha256:1d183a8cbb5b8fc2ac14304a87dae8fed0b2f03c7743c03ec1dc9be844748b21",
        )
        self.assertEqual(
            function_hash(runner, "prepare_evals"),
            "sha256:1f6bd3c7de02aba643228a5bab63ed8d3ce7e475f703be3660bb73de2ffbb7d7",
        )
        self.assertEqual(
            function_hash(runner, "stage_evals"),
            "sha256:8f9ace98e3bec863eb6d6544d798f6d192db0aa72d557428c4445fa0ec3b1445",
        )
        self.assertEqual(
            function_hash(runner, "fulfill_evals"),
            "sha256:62ca77473f274b994845a7e4bf51fcaae534d9d6ae4cc531071e12e0113d47ae",
        )
        self.assertEqual(
            sha256_file(Path(generator.__file__)),
            "sha256:25e88faaf2257c7c0952a835b6635ab11588aae9305c439b33655d607c32f0e1",
        )
        self.assertEqual(
            sha256_file(Path(fulfillment.__file__)),
            "sha256:b0a7977a3e7085b85ef2450eb41254726fcf50aee0a6c5d8b32f5947cca4d5da",
        )
        fixed_files = {
            "src/core/atomic-skills/evals-build/INSTRUCTIONS.md": "sha256:09b5a631d783d271d8e5de606db7328d1b63723da78062b74cd77ea1d077f51b",
            "src/core/atomic-skills/evals-review/INSTRUCTIONS.md": "sha256:895c60778c50470f9da287be1415fb421847b8283e885b05886f59daf353d6e3",
            "src/core/schemas/eval-pack-review.schema.json": "sha256:5f3a5badcd738b24169db34bb642a74b9ec92c839fba8367b93022378c2d651b",
            "src/core/schemas/eval-pack.schema.json": "sha256:c56943ef5805bf7f0004eef46084d29fa2872ad9bcf69ffea041eeed7bbcfb28",
            "src/core/schemas/product-eval-pack.schema.json": "sha256:59acc650828c1749d7616c8fe02b80db373817dd69ab247dd39ee23f5364c078",
            "src/core/schemas/product-eval-review.schema.json": "sha256:ef59e3e3a517d56365b36febb55c27de718e0ffef330ea1c82f2eb652d08e27e",
            "src/core/schemas/product-eval-execution-receipt.schema.json": "sha256:a2bc90b5d82bfd19a6d43f448fa76bc29fdd6eda22b90535888f3e189634bf16",
        }
        for relative, expected in fixed_files.items():
            self.assertEqual(sha256_file(REPO_ROOT / relative), expected, relative)

    def test_installed_public_operations_run_prepare_and_review_to_eval_only_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepare_payload = project / "prepare.json"
            atomic_write_json(prepare_payload, payload)
            runner = (
                self.plugin
                / "skills"
                / "better-product-graph"
                / "scripts"
                / "bpg_runner.py"
            )

            prepared_process = subprocess.run(
                [
                    "python3",
                    str(runner),
                    "--operation",
                    "writing-eval.prepare",
                    "--run-id",
                    run_id,
                    "--payload-file",
                    str(prepare_payload),
                ],
                cwd=project,
                check=True,
                capture_output=True,
                text=True,
            )
            prepared = json.loads(prepared_process.stdout)
            self.assertEqual(prepared["status"], "WRITING_EVAL_REVIEW_REQUIRED")
            self.assertEqual(
                prepared["host_execution_context"]["instruction_compatibility"],
                "EXACT",
            )
            instruction_path = Path(
                prepared["host_execution_context"]["instruction_path"]
            )
            self.assertEqual(
                instruction_path.name,
                "INSTRUCTIONS.md",
            )
            self.assertEqual(
                instruction_path.parent.name,
                "prd-writing-eval-review",
            )

            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            result_path = project / "review-result.json"
            atomic_write_json(result_path, result)
            completed_process = subprocess.run(
                [
                    "python3",
                    str(runner),
                    "--operation",
                    "writing-eval.review",
                    "--run-id",
                    run_id,
                    "--payload-file",
                    str(result_path),
                ],
                cwd=project,
                check=True,
                capture_output=True,
                text=True,
            )
            completed = json.loads(completed_process.stdout)
            self.assertEqual(completed["status"], "COMPLETED")
            self.assertEqual(completed["product_authority"], "NONE")
            self.assertFalse(
                (project / ".better-product-graph" / "runs" / run_id).exists()
            )

    def test_installed_completed_retry_checks_current_instruction_before_early_return(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_id, payload = write_agent_case(project)
            prepare_path = project / "prepare.json"
            atomic_write_json(prepare_path, payload)
            runner = self.skill / "scripts" / "bpg_runner.py"

            def invoke(operation: str, payload_path: Path) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        "python3",
                        str(runner),
                        "--operation",
                        operation,
                        "--run-id",
                        run_id,
                        "--payload-file",
                        str(payload_path),
                    ],
                    cwd=project,
                    check=False,
                    capture_output=True,
                    text=True,
                )

            prepared_process = invoke("writing-eval.prepare", prepare_path)
            self.assertEqual(prepared_process.returncode, 0, prepared_process.stderr)
            prepared = json.loads(prepared_process.stdout)
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            result_path = project / "review-result.json"
            atomic_write_json(result_path, result)
            completed_process = invoke("writing-eval.review", result_path)
            self.assertEqual(completed_process.returncode, 0, completed_process.stderr)

            for operation, payload_file in (
                ("writing-eval.prepare", prepare_path),
                ("writing-eval.review", result_path),
            ):
                with self.subTest(exact_retry=operation):
                    exact = invoke(operation, payload_file)
                    self.assertEqual(exact.returncode, 0, exact.stderr)
                    self.assertEqual(json.loads(exact.stdout)["status"], "COMPLETED")

            runtime = WritingEvalRuntime(project, self.skill)
            rewrite_as_legacy_instruction(
                project,
                runtime,
                run_id,
                status="COMPLETED",
                started_event=False,
                legacy_hash="sha256:848aaaa15e4e989c8822f1e0ee66a3c992b0b9483fc5eac53df23c7529bc319e",
            )
            eval_root = runtime.run_path(run_id)
            before = {
                path.relative_to(eval_root).as_posix(): path.read_bytes()
                for path in eval_root.rglob("*")
                if path.is_file()
            }
            for operation, payload_file in (
                ("writing-eval.prepare", prepare_path),
                ("writing-eval.review", result_path),
            ):
                with self.subTest(stale_completed=operation):
                    rejected = invoke(operation, payload_file)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn(
                        "started predecessor instruction drift",
                        rejected.stderr + rejected.stdout,
                    )
                    self.assertEqual(
                        {
                            path.relative_to(eval_root).as_posix(): path.read_bytes()
                            for path in eval_root.rglob("*")
                            if path.is_file()
                        },
                        before,
                    )

    def test_installed_instruction_examples_are_complete_and_enforced_by_public_review(self) -> None:
        instruction_path = (
            self.skill
            / "references"
            / "atomic-skills"
            / "prd-writing-eval-review"
            / "INSTRUCTIONS.md"
        )
        instruction_text = instruction_path.read_text(encoding="utf-8")
        for required in (
            "verbosity_assessment.verdict`: `PASS | FINDING`",
            "checklist_assessment.verdict`: `PASS | FINDING`",
            "visual_assessment.verdict`: `PASS | FINDING | NOT_NEEDED`",
            "observation_status`: `OBSERVED | NOT_OBSERVED | NOT_NEEDED`",
            "`result`: `PASS | FINDING`",
            "Never emit `FAIL` or `NOT_PROVIDED`",
            "must have `verdict=FINDING`",
            "between three and five components",
            "component `name` must be unique",
            "exactly three entries, one for each required target",
            "Each `reader_outcome_failures[]` object has exactly",
            "Each outcome may appear at most once",
        ):
            self.assertIn(required, instruction_text)

        pass_example = instruction_example(
            instruction_path, "writing-eval-result-contract"
        )
        finding_example = instruction_example(
            instruction_path, "writing-eval-finding-example"
        )
        runner = self.skill / "scripts" / "bpg_runner.py"

        def execute(
            example: dict,
            *,
            suffix: str,
            mutation=None,
        ) -> subprocess.CompletedProcess[str]:
            directory = tempfile.TemporaryDirectory()
            self.addCleanup(directory.cleanup)
            project = Path(directory.name)
            run_id, payload = write_agent_case(project)
            prepare_path = project / "prepare.json"
            atomic_write_json(prepare_path, payload)
            prepared_process = subprocess.run(
                [
                    "python3",
                    str(runner),
                    "--operation",
                    "writing-eval.prepare",
                    "--run-id",
                    run_id,
                    "--payload-file",
                    str(prepare_path),
                ],
                cwd=project,
                check=True,
                capture_output=True,
                text=True,
            )
            prepared = json.loads(prepared_process.stdout)
            result = hydrate_instruction_example(
                example,
                prepared["dispatch"],
                prepared["preregistration_checkpoint_ref"],
                reviewer_id=f"anon-reviewer-{suffix}",
            )
            if mutation is not None:
                mutation(result)
            result_path = project / "review-result.json"
            atomic_write_json(result_path, result)
            return subprocess.run(
                [
                    "python3",
                    str(runner),
                    "--operation",
                    "writing-eval.review",
                    "--run-id",
                    run_id,
                    "--payload-file",
                    str(result_path),
                ],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )

        for label, example, expected in (
            ("pass", pass_example, "PASS"),
            ("finding", finding_example, "FINDING"),
        ):
            with self.subTest(label=label):
                completed = execute(example, suffix=label)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                response = json.loads(completed.stdout)
                self.assertEqual(response["status"], "COMPLETED")
                result_ref = response["state"]["result_ref"]
                committed = read_json(Path(completed.args[-1]).parent / result_ref["path"])
                self.assertEqual(committed["result"], expected)

        def duplicate_outcome(result: dict) -> None:
            failure = {
                "outcome": "SEE",
                "basis_refs": copy.deepcopy(result["visual_assessment"]["basis_refs"]),
                "reason": "相同观察不能登记两次",
            }
            result["reader_outcome_failures"] = [failure, copy.deepcopy(failure)]

        attacks = {
            "undisclosed assessment FAIL": (
                lambda result: result["verbosity_assessment"].update({"verdict": "FAIL"}),
                "verbosity_assessment.verdict is invalid",
            ),
            "undisclosed NOT_PROVIDED": (
                lambda result: result["visual_assessment"].update(
                    {"observation_status": "NOT_PROVIDED"}
                ),
                "visual FINDING must truthfully bind observed or missing visuals",
            ),
            "finding without repair": (
                lambda result: result["visual_assessment"].update(
                    {"repair_techniques": []}
                ),
                "FINDING requires diagnosis and repair technique",
            ),
            "six mental components": (
                lambda result: result["reader_readback"]["mental_model"].extend(
                    [
                        {"name": "对象四", "role": "补充对象"},
                        {"name": "对象五", "role": "补充对象"},
                        {"name": "对象六", "role": "超出上限"},
                    ]
                ),
                "mental_model requires three to five components",
            ),
            "duplicate mental name": (
                lambda result: result["reader_readback"]["mental_model"][1].update(
                    {"name": result["reader_readback"]["mental_model"][0]["name"]}
                ),
                "mental_model component names must be unique",
            ),
            "missing navigation target": (
                lambda result: result["reader_readback"]["navigation_map"].pop(),
                "navigation_map must cover all three targets once",
            ),
            "duplicate navigation target": (
                lambda result: result["reader_readback"]["navigation_map"].append(
                    copy.deepcopy(result["reader_readback"]["navigation_map"][0])
                ),
                "navigation_map must cover all three targets once",
            ),
            "duplicate reader outcome": (
                duplicate_outcome,
                "reader_outcome_failures must be unique",
            ),
        }
        for label, (mutation, expected_error) in attacks.items():
            with self.subTest(label=label):
                rejected = execute(finding_example, suffix=label.replace(" ", "-"), mutation=mutation)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn(expected_error, rejected.stderr + rejected.stdout)


if __name__ == "__main__":
    unittest.main()
