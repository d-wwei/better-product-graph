from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from tests.controller_fixtures import position_run_internal
from src.bpg.host_runtime import HostRuntime
from src.bpg.documents import archive_prd_candidate
from src.bpg.prd_contract import assemble_prd
from src.bpg.node_registry import NodeRegistry
from src.bpg.reference_catalog import (
    EXPECTED_REFERENCE_RESOURCE_IDS,
    ReferenceCatalog,
    ReferenceCatalogError,
)
from src.bpg.state_controller import TransitionRejected
from src.bpg.storage import atomic_write_json, read_json, sha256_file
from src.bpg.templates import TemplateRegistry
from tests.test_prd_contract import TEMPLATES, prd_submission


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class InternalReferenceCatalogTests(unittest.TestCase):
    def test_review_resources_include_exact_writing_standard_contracts(self) -> None:
        catalog = ReferenceCatalog(REPO_ROOT / "src" / "core")
        resources = {item["resource_id"]: item for item in catalog.review_resources()}

        self.assertIn("writing-standard-coverage-contract", resources)
        self.assertIn("prd-writing-profile-v0.2", resources)
        self.assertIn("prd-writing-guide-v0.2", resources)

    def test_review_resources_keep_v04_as_non_default_with_distinct_v3_contract(self) -> None:
        catalog = ReferenceCatalog(REPO_ROOT / "src" / "core")
        resources = {item["resource_id"]: item for item in catalog.review_resources()}

        self.assertEqual(resources["prd-writing-profile-v0.4"]["version"], "0.4.0")
        self.assertEqual(resources["prd-writing-guide-v0.4"]["version"], "0.4.0")
        self.assertEqual(resources["prd-writing-reader-review-v3"]["version"], "v3")
        contract = read_json(
            catalog.resolve(resources["prd-writing-reader-review-v3"]["path"])
        )
        self.assertEqual(
            contract["reader_readback_contract"]["required_fields"],
            [
                "problem_and_outcome",
                "primary_relationships",
                "mental_model",
                "main_path_and_recovery",
                "decision_conditions_and_risks",
                "navigation_map",
            ],
        )
        self.assertEqual(
            contract["finding_union_rule"],
            "TOP_LEVEL_FINDING_REFS_EQUAL_OUTCOME_AND_ASSESSMENT_FINDING_UNION",
        )
        registry = read_json(
            REPO_ROOT / "src" / "core" / "policies" / "document-experience-profiles.json"
        )
        self.assertEqual(
            registry["default_profiles"]["prd"],
            {"id": "prd-plain-language-zh-CN", "version": "0.5.0"},
        )

    def test_review_resources_preserve_v31_and_stage_v311_and_v321(self) -> None:
        catalog = ReferenceCatalog(REPO_ROOT / "src" / "core")
        resources = {item["resource_id"]: item for item in catalog.review_resources()}

        self.assertIn("prd-writing-profile-v0.5", resources)
        self.assertIn("prd-writing-guide-v0.5", resources)
        self.assertIn("prd-writing-reader-review-v3.1", resources)
        self.assertIn("prd-writing-reader-review-v3.1.1", resources)
        self.assertIn("prd-writing-reader-review-v3.2.1", resources)
        self.assertEqual(resources["prd-writing-profile-v0.5"]["version"], "0.5.0")
        self.assertEqual(resources["prd-writing-guide-v0.5"]["version"], "0.5.0")
        self.assertEqual(resources["prd-writing-reader-review-v3.1"]["version"], "v3.1")
        self.assertEqual(
            resources["prd-writing-reader-review-v3.1"]["hash"],
            "sha256:5659ea767a7270e82343e273ad71c50a49f03b9e3d60b040ab60b608f0a881ef",
        )
        self.assertEqual(resources["prd-writing-reader-review-v3.1.1"]["version"], "v3.1.1")
        self.assertEqual(resources["prd-writing-reader-review-v3.2.1"]["version"], "v3.2.1")
        contract = read_json(
            catalog.resolve(resources["prd-writing-reader-review-v3.1.1"]["path"])
        )
        self.assertEqual(contract["review_schema"], "document-experience-reader-review.v3")
        self.assertEqual(contract["authority"], "ADVISORY_ONLY")
        self.assertEqual(contract["supported_profile_version"], "0.5.0")
        self.assertNotIn("primary_objective", contract)

    def test_source_extraction_manifest_rehashes_all_twenty_declared_cognitive_bases(self) -> None:
        upstream = Path("/Users/example/Documents/AI/认知基座")
        if not upstream.is_dir():
            self.skipTest("local upstream cognitive-base source is not available")
        manifest = read_json(
            REPO_ROOT / "src" / "core" / "reasoning-catalog" / "extraction-manifest-v0.1.json"
        )
        cognitive = read_json(
            REPO_ROOT / "src" / "core" / "reasoning-catalog" / "cognitive-base-catalog-v0.1.json"
        )
        declared = {item["resource_id"]: item for item in manifest["entries"]}
        extracted = {item["id"]: item["source_sha256"] for item in cognitive["bases"]}
        self.assertEqual(len(declared), 20)
        self.assertEqual(set(declared), set(extracted))
        for resource_id, entry in declared.items():
            with self.subTest(resource_id=resource_id):
                self.assertEqual(entry["source_sha256"], extracted[resource_id])
                self.assertEqual(
                    entry["source_sha256"],
                    sha256_file(upstream / entry["source_relative_path"]),
                )

    def test_source_catalog_has_better_question_router_and_exactly_twenty_non_discoverable_bases(self) -> None:
        catalog = ReferenceCatalog(REPO_ROOT / "src" / "core")
        self.assertEqual(len(catalog.cognitive_bases), 20)
        self.assertEqual(
            {item["resource_id"] for item in catalog.core_reasoning_resources()},
            {"better-question", "cognitive-router", "cognitive-base-catalog"},
        )
        self.assertTrue(all("SKILL.md" not in item["path"] for item in catalog.all_resource_refs()))
        self.assertEqual(
            {item["resource_id"] for item in catalog.all_resource_refs()},
            EXPECTED_REFERENCE_RESOURCE_IDS,
        )

    def test_writing_eval_resource_is_dedicated_and_not_in_ordinary_review(self) -> None:
        catalog = ReferenceCatalog(REPO_ROOT / "src" / "core")
        ordinary = {item["resource_id"] for item in catalog.review_resources()}
        evaluation = {item["resource_id"] for item in catalog.writing_eval_resources()}

        self.assertNotIn("prd-writing-eval-reader-review-v3.1", ordinary)
        self.assertNotIn("prd-writing-eval-reader-review-v3.2", ordinary)
        self.assertEqual(
            evaluation,
            {
                "prd-writing-profile-v0.4",
                "prd-writing-guide-v0.4",
                "prd-writing-eval-reader-review-v3.1",
                "prd-writing-profile-v0.5",
                "prd-writing-guide-v0.5",
                "prd-writing-eval-reader-review-v3.2",
            },
        )
        v32 = next(
            item
            for item in catalog.writing_eval_resources()
            if item["resource_id"] == "prd-writing-eval-reader-review-v3.2"
        )
        contract = read_json(catalog.resolve(v32["path"]))
        self.assertEqual(
            contract["result_schema"], "document-experience-reader-eval.v3.1"
        )
        self.assertEqual(contract["supported_profile_version"], "0.5.0")
        self.assertEqual(contract["authority"], "EVALUATION_ONLY_ADVISORY")
        for hidden in (
            "primary_objective",
            "allowed_primary_pairs",
            "expected",
            "threshold",
        ):
            self.assertNotIn(hidden, contract)

    def test_problem_learning_and_review_dispatch_bind_installed_reference_hashes(self) -> None:
        registry = NodeRegistry(REPO_ROOT / "src" / "core", GRAPH)
        learning = registry.dispatch_envelope("problem.learning.loop", "attempt-learning", [], {})
        review = registry.dispatch_envelope("review.parallel", "attempt-review", [], {})

        self.assertEqual(len(learning["resource_refs"]), 23)
        self.assertEqual(
            {item["resource_id"] for item in review["resource_refs"]},
            {
                "goal-fidelity-profile",
                "goal-fidelity-rubric",
                "goal-fidelity-packet-contract",
                "writing-standard-coverage-contract",
                "prd-writing-profile-v0.2",
                "prd-writing-guide-v0.2",
                "prd-writing-reader-review-v3",
                "prd-writing-profile-v0.4",
                "prd-writing-guide-v0.4",
                "prd-writing-reader-review-v3.1",
                "prd-writing-reader-review-v3.1.1",
                "prd-writing-reader-review-v3.2",
                "prd-writing-reader-review-v3.2.1",
                "prd-writing-profile-v0.5",
                "prd-writing-guide-v0.5",
            },
        )
        self.assertTrue(all(item["hash"].startswith("sha256:") for item in learning["resource_refs"] + review["resource_refs"]))

    def test_installed_catalog_fails_closed_when_one_reference_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            skill = plugin / "skills" / "better-product-graph"
            catalog = ReferenceCatalog(skill)
            missing = skill / catalog.cognitive_bases[0]["path"]
            missing.unlink()

            with self.assertRaisesRegex(ReferenceCatalogError, "missing|hash"):
                ReferenceCatalog(skill)

    def test_installed_controller_requires_exact_dispatch_review_resources_and_commitments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "plugin"
            project = (root / "project").resolve()
            project.mkdir()
            build_plugin(REPO_ROOT, plugin)
            skill = plugin / "skills" / "better-product-graph"
            graph = skill / "references" / "graph" / "manifest.json"
            runtime = HostRuntime(project, graph, skill)
            run_id = "run-review-resources"
            runtime.controller.create_run(run_id, raw_signal="审查候选")
            commitment_path = project / "commitment.json"
            atomic_write_json(commitment_path, {"commitment": "目标不漂移"})
            assembled = assemble_prd(
                prd_submission(), TemplateRegistry(TEMPLATES).resolve(REPO_ROOT)
            )
            archived = archive_prd_candidate(project, assembled, assets={})
            candidate_ref = {
                "path": archived.document_path.relative_to(project).as_posix(),
                "hash": archived.document_hash,
                "tree_hash": archived.tree_hash,
                "artifact_path": archived.path.relative_to(project).as_posix(),
                "version": archived.version,
                "review_path": archived.review_path.relative_to(project).as_posix(),
                "review_hash": archived.review_hash,
                "generation": 1,
            }
            commitment_ref = {"path": "commitment.json", "hash": sha256_file(commitment_path), "version": 1}
            position_run_internal(
                runtime.controller,
                run_id,
                "review.parallel",
                ["review.aggregate"],
                artifact_refs={"candidate": candidate_ref, "commitment": commitment_ref},
                state_updates={"current_candidate_ref": candidate_ref},
            )
            dispatch = runtime.dispatch_current(run_id)
            by_id = {item["resource_id"]: item for item in dispatch["resource_refs"]}

            def exact(resource_id: str) -> dict:
                return {
                    field: by_id[resource_id][field]
                    for field in ("path", "hash", "version")
                }

            writing = dispatch["writing_review_context"]
            writing_path = project / "writing-coverage.json"
            atomic_write_json(
                writing_path,
                {
                    "schema_version": "document-experience-reader-review.v3",
                    "authority": "ADVISORY_ONLY",
                    "candidate_ref": writing["candidate_ref"],
                    "candidate_tree_hash": writing["candidate_tree_hash"],
                    "profile_ref": writing["profile_ref"],
                    "guide_ref": writing["guide_ref"],
                    "review_contract_ref": writing["review_contract_ref"],
                    "output_contract_ref": writing["output_contract_ref"],
                    "author_execution_ref": writing["author_execution_ref"],
                    "reviewer_execution_ref": {
                        "kind": "HOST_SUBAGENT_ATTEMPT",
                        "id": "attempt-writing-review",
                    },
                    "reviewer_role": "writing_standard",
                    "isolated_input_refs": writing["isolated_input_refs"],
                    "reader_readback": {
                        "problem_and_outcome": "用户需要稳定完成任务，产品要降低失败风险。",
                        "primary_relationships": "输入经过规则处理后形成可验收结果。",
                        "mental_model": [
                            {"name": "输入", "role": "提供待处理信息"},
                            {"name": "规则", "role": "约束产品行为"},
                            {"name": "结果", "role": "形成可验收输出"},
                        ],
                        "main_path_and_recovery": "系统处理输入并返回结果；失败时保留输入并允许重试。",
                        "decision_conditions_and_risks": "仅在规则明确时采用；主要风险是结果与输入不一致。",
                        "navigation_map": [
                            {"target": "PRODUCT_RULES", "location": "产品规则"},
                            {"target": "ACCEPTANCE", "location": "验收标准"},
                            {"target": "RISKS_UNKNOWNS_NEXT", "location": "风险与未知"},
                        ],
                    },
                    "reader_outcome_failures": [],
                    "verbosity_assessment": {
                        "verdict": "PASS",
                        "issue_types": [],
                        "repair_techniques": [],
                        "basis_refs": [],
                        "finding_refs": [],
                        "reason": "主路径没有重复合同。",
                    },
                    "checklist_assessment": {
                        "verdict": "PASS",
                        "issue_types": [],
                        "repair_techniques": [],
                        "basis_refs": [],
                        "finding_refs": [],
                        "reason": "交付检查功能保持完整。",
                    },
                    "visual_assessment": {
                        "verdict": "NOT_NEEDED",
                        "observation_status": "NOT_NEEDED",
                        "visual_pair_refs": [],
                        "issue_types": [],
                        "repair_techniques": [],
                        "basis_refs": [],
                        "finding_refs": [],
                        "reason": "关系简单，文字足够表达。",
                    },
                    "finding_refs": [],
                    "claim_boundary": (
                        "AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN"
                    ),
                },
            )
            writing_ref = {
                "path": writing_path.relative_to(project).as_posix(),
                "hash": sha256_file(writing_path),
                "version": 1,
            }

            result = {
                "schema_version": "node-result.v1",
                "node_id": "review.parallel",
                "attempt_id": dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": dispatch["instruction_ref"],
                "instruction_hash": dispatch["instruction_hash"],
                "input_refs": dispatch["input_refs"],
                "input_hashes": dispatch["input_hashes"],
                "resource_refs": dispatch["resource_refs"],
                "semantic_output": {
                    "candidate_ref": candidate_ref,
                    "reviewer_role": "product",
                    "roles_covered": ["product"],
                    "authority": "ADVISORY_ONLY",
                    "goal_fidelity_refs": {
                        "profile_ref": exact("goal-fidelity-profile"),
                        "rubric_ref": exact("goal-fidelity-rubric"),
                        "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                        "commitment_refs": [commitment_ref],
                    },
                    "goal_fidelity_packet": {
                        "goal": "保持产品目标",
                        "candidate_ref": candidate_ref,
                        "commitment_refs": [commitment_ref],
                    },
                    "writing_coverage_ref": writing_ref,
                    "findings": [],
                },
                "artifact_refs": [{"role": "writing_coverage", **writing_ref}],
            }

            with self.assertRaisesRegex(TransitionRejected, "resource"):
                runtime.controller.submit_result(run_id, {**result, "resource_refs": []})
            forged_profile = {**result, "semantic_output": dict(result["semantic_output"])}
            forged_profile["semantic_output"]["goal_fidelity_refs"] = {
                **result["semantic_output"]["goal_fidelity_refs"],
                "profile_ref": {**exact("goal-fidelity-profile"), "hash": "sha256:forged"},
            }
            with self.assertRaisesRegex(TransitionRejected, "Goal Fidelity"):
                runtime.controller.submit_result(run_id, forged_profile)
            unbound = project / "unbound-commitment.json"
            atomic_write_json(unbound, {"commitment": "不在 dispatch inputs"})
            unbound_ref = {"path": "unbound-commitment.json", "hash": sha256_file(unbound), "version": 1}
            forged_commitment = {**result, "semantic_output": dict(result["semantic_output"])}
            forged_commitment["semantic_output"]["goal_fidelity_refs"] = {
                **result["semantic_output"]["goal_fidelity_refs"],
                "commitment_refs": [unbound_ref],
            }
            forged_commitment["semantic_output"]["goal_fidelity_packet"] = {
                **result["semantic_output"]["goal_fidelity_packet"],
                "commitment_refs": [unbound_ref],
            }
            with self.assertRaisesRegex(TransitionRejected, "commitment"):
                runtime.controller.submit_result(run_id, forged_commitment)

            self.assertTrue(runtime.controller.submit_result(run_id, result).is_file())

            learning_run = "run-learning-resources"
            runtime.controller.create_run(learning_run, raw_signal="学习未知")
            position_run_internal(
                runtime.controller,
                learning_run,
                "problem.learning.loop",
                ["problem.synthesize"],
            )
            learning_dispatch = runtime.dispatch_current(learning_run)
            learning_result = {
                "schema_version": "node-result.v1",
                "node_id": "problem.learning.loop",
                "attempt_id": learning_dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": learning_dispatch["instruction_ref"],
                "instruction_hash": learning_dispatch["instruction_hash"],
                "input_refs": learning_dispatch["input_refs"],
                "input_hashes": learning_dispatch["input_hashes"],
                "resource_refs": learning_dispatch["resource_refs"],
                "semantic_output": {
                    "learning_disposition": "READY_FOR_SYNTHESIS",
                    "runtime_status": "COMPLETED",
                    "interaction_policy": "ALLOW_PM_INTERVIEW",
                    "next_actions": [],
                    "material_challenges": [],
                    "reasoning_usage": {
                        "used_resource_ids": ["invented-cognitive-base"],
                        "selection_rationale": "Agent-declared use",
                    },
                },
                "artifact_refs": [],
            }
            with self.assertRaisesRegex(TransitionRejected, "reasoning resource"):
                runtime.controller.submit_result(learning_run, learning_result)
            learning_result["semantic_output"]["reasoning_usage"]["used_resource_ids"] = [
                "better-question",
                "first-principles",
            ]
            self.assertTrue(
                runtime.controller.submit_result(learning_run, learning_result).is_file()
            )


if __name__ == "__main__":
    unittest.main()
