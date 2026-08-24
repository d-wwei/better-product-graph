from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from tests.controller_fixtures import position_run_internal
from src.bpg.host_runtime import HostRuntime
from src.bpg.node_registry import NodeRegistry
from src.bpg.reference_catalog import ReferenceCatalog, ReferenceCatalogError
from src.bpg.state_controller import TransitionRejected
from src.bpg.storage import atomic_write_json, read_json, sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class InternalReferenceCatalogTests(unittest.TestCase):
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
        self.assertEqual(len({item["resource_id"] for item in catalog.all_resource_refs()}), 26)

    def test_problem_learning_and_review_dispatch_bind_installed_reference_hashes(self) -> None:
        registry = NodeRegistry(REPO_ROOT / "src" / "core", GRAPH)
        learning = registry.dispatch_envelope("problem.learning.loop", "attempt-learning", [], {})
        review = registry.dispatch_envelope("review.parallel", "attempt-review", [], {})

        self.assertEqual(len(learning["resource_refs"]), 23)
        self.assertEqual(
            {item["resource_id"] for item in review["resource_refs"]},
            {"goal-fidelity-profile", "goal-fidelity-rubric", "goal-fidelity-packet-contract"},
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
            project = root / "project"
            project.mkdir()
            build_plugin(REPO_ROOT, plugin)
            skill = plugin / "skills" / "better-product-graph"
            graph = skill / "references" / "graph" / "manifest.json"
            runtime = HostRuntime(project, graph, skill)
            run_id = "run-review-resources"
            runtime.controller.create_run(run_id, raw_signal="审查候选")
            candidate_path = project / "candidate.json"
            commitment_path = project / "commitment.json"
            atomic_write_json(candidate_path, {"candidate": "v1"})
            atomic_write_json(commitment_path, {"commitment": "目标不漂移"})
            candidate_ref = {"path": "candidate.json", "hash": sha256_file(candidate_path), "version": 1}
            commitment_ref = {"path": "commitment.json", "hash": sha256_file(commitment_path), "version": 1}
            position_run_internal(
                runtime.controller,
                run_id,
                "review.parallel",
                ["review.aggregate"],
                artifact_refs={"candidate": candidate_ref, "commitment": commitment_ref},
            )
            dispatch = runtime.dispatch_current(run_id)
            by_id = {item["resource_id"]: item for item in dispatch["resource_refs"]}

            def exact(resource_id: str) -> dict:
                return {
                    field: by_id[resource_id][field]
                    for field in ("path", "hash", "version")
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
                    "findings": [],
                },
                "artifact_refs": [],
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
