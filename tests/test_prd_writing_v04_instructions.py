from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.documents import hash_tree
from src.bpg.failpoints import begin_node_call, mark_dispatch_unknown, persist_node_dispatch
from src.bpg.host_runtime import HostRuntime
from src.bpg.node_registry import NodeRegistry
from src.bpg.review_contract import REVIEW_FINDING_FIELDS, validate_review_submission
from src.bpg.state_controller import TransitionRejected
from src.bpg.storage import atomic_write_json, sha256_file
from src.bpg.writing_review import validate_writing_coverage
from tests.controller_fixtures import position_run_internal


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE = REPO_ROOT / "src" / "core"
GRAPH = CORE / "graph" / "manifest.json"
GENERATE_PREDECESSOR = (
    "sha256:2d63ae1f32639741686ffefdc38c35834fa3b40e0fa91d001a294611be07572e"
)
REVIEW_PREDECESSOR = (
    "sha256:ede0efeed0da5e54043a5eab56558002f7e0ce84959aec06cb87ceb0fb4e18c0"
)
REVIEW_EXAMPLE_PREDECESSOR = (
    "sha256:d67381a6de10c48f263d3c21c7f8d2318c5eff47b3b2445d40ac567ca63110d3"
)
REVIEW_ARTIFACT_EXAMPLE_PREDECESSOR = (
    "sha256:ab15efb0dbfe8375451721c75ccc6a00310d70c68b433e8e89f3904a1ff26fc1"
)
VISUAL_REVIEW_PREDECESSOR = (
    "sha256:0f05fd222b9470ea6cf4201b743cb10472f67acea7e849f7814d7339f72e16f2"
)
STRICT_VISUAL_REVIEW_PREDECESSOR = (
    "sha256:058bd95054ea89fd4be37e467673a7ed8d5c488d85c4ea9a566878e135a56b70"
)
COMMONMARK_VISUAL_REVIEW_PREDECESSOR = (
    "sha256:06944c2706f8a0b3b6a697aca8968b0cb41e715c5ccee95f6f5b90247bbd00ca"
)


def position_review_parallel(runtime: HostRuntime, project: Path, run_id: str) -> None:
    runtime.controller.create_run(run_id, raw_signal="审查旧 review.parallel dispatch")
    candidate_root = project / "artifacts" / "prds" / "archived" / "V04"
    candidate_root.mkdir(parents=True)
    candidate = candidate_root / "V04_v0.1.md"
    candidate.write_text(
        "# 示例 PRD\n\n## 阅读摘要\n" + "\n".join(
            f"第 {line} 行产品说明" for line in range(4, 36)
        ) + "\n",
        encoding="utf-8",
    )
    profile = CORE / "policies" / "prd-writing-profile-v0.4.json"
    guide = CORE / "policies" / "prd-writing-guide-v0.4.md"
    output = CORE / "templates" / "contracts" / "prd-v0.2.json"
    metadata = candidate_root / "V04_v0.1.metadata.json"
    atomic_write_json(
        metadata,
        {
            "prd_id": "V04",
            "short_title": "示例",
            "date": "2026-08-26",
            "provenance": {"attempt_id": "attempt-author-v04"},
            "document_experience": {
                "profile_ref": {
                    "path": "references/policies/prd-writing-profile-v0.4.json",
                    "hash": sha256_file(profile),
                    "version": "0.4.0",
                },
                "writing_guide_ref": {
                    "path": "references/policies/prd-writing-guide-v0.4.md",
                    "hash": sha256_file(guide),
                    "version": "0.4.0",
                },
            },
            "template_profile": {
                "output_contract": {
                    "path": "references/templates/contracts/prd-v0.2.json",
                    "sha256": sha256_file(output),
                    "version": "better-product-graph.prd.general.0.2",
                }
            },
        },
    )
    review = candidate_root / "V04_v0.1.review.json"
    atomic_write_json(review, {"status": "NOT_RUN"})
    commitment = project / "product-commitment.json"
    atomic_write_json(commitment, {"goal": "降低遗漏风险"})
    commitment_ref = {
        "path": commitment.relative_to(project).as_posix(),
        "hash": sha256_file(commitment),
        "version": 1,
    }
    candidate_ref = {
        "role": "prd_candidate",
        "path": candidate.relative_to(project).as_posix(),
        "hash": sha256_file(candidate),
        "version": "v0.1",
        "artifact_path": candidate_root.relative_to(project).as_posix(),
        "tree_hash": hash_tree(candidate_root),
        "review_path": review.relative_to(project).as_posix(),
        "review_hash": sha256_file(review),
        "generation": 1,
    }
    position_run_internal(
        runtime.controller,
        run_id,
        "review.parallel",
        ["review.aggregate"],
        artifact_refs={
            "prd-candidate": candidate_ref,
            "product-commitment": commitment_ref,
        },
        state_updates={"current_candidate_ref": candidate_ref},
    )


def predecessor_review_dispatch(runtime: HostRuntime, run_id: str, attempt_id: str) -> dict:
    state = runtime.controller.load_state(run_id)
    input_hashes = {
        ref["path"]: ref["hash"] for ref in state["artifact_refs"].values()
    }
    envelope = runtime.registry.dispatch_envelope(
        "review.parallel", attempt_id, list(input_hashes), input_hashes
    )
    context = runtime.controller.writing_review_context(state, envelope["resource_refs"])
    envelope["resource_refs"] = runtime.controller.exact_writing_review_resources(
        envelope["resource_refs"], context
    )
    envelope["writing_review_context"] = context
    envelope["instruction_hash"] = REVIEW_PREDECESSOR
    return envelope


def extract_json(instruction: str, marker: str) -> dict:
    match = re.search(
        rf"<!-- {re.escape(marker)} -->\s*```json\s*(\{{.*?\}})\s*```",
        instruction,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"instruction is missing {marker}")
    return json.loads(match.group(1))


class PRDWritingV04InstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.plugin = Path(cls.temporary.name) / "plugin"
        build_plugin(REPO_ROOT, cls.plugin)
        cls.installed_core = cls.plugin / "skills" / "better-product-graph"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_explicit_v04_author_contract_is_reader_first_without_length_gates(self) -> None:
        source = (
            CORE / "atomic-skills" / "prd-generate" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("PRD_WRITING_PROFILE_V04_CANDIDATE", source)
        self.assertIn("explicitly binds Profile `0.4.0`", source)
        for rule_id in (
            "ONE_SEMANTIC_ONE_CANONICAL_LOCATION",
            "MAIN_PATH_CORE_PRODUCT_RESULTS_ONLY",
            "GROUP_TO_COMPRESS_WITHOUT_SEMANTIC_LOSS",
            "ONE_PRIMARY_REPRESENTATION_PER_RELATIONSHIP",
            "TABLES_ONLY_FOR_COMPARISON_AND_MAPPING",
            "PRESERVE_FUNCTION_NOT_REPETITION",
            "TRUTHFUL_PRECISE_STATUS",
            "PLAIN_LANGUAGE_BEFORE_MACHINE_NAME",
        ):
            self.assertIn(rule_id, source)
        for outcome in ("UNDERSTAND", "SEE", "MODEL", "RETELL", "DECIDE", "LOCATE"):
            self.assertIn(outcome, source)
        for truth in (
            "PROPOSED_NOT_IMPLEMENTED",
            "NOT_RUN",
            "local Handoff",
            "Engineering SPEC",
        ):
            self.assertIn(truth, source)
        self.assertIn("must not use word, line, section, or table-row counts", source)
        self.assertIn("Profile `0.2.0`", source)

    def test_v3_review_contract_is_isolated_two_pass_compact_and_advisory(self) -> None:
        source = (
            CORE / "atomic-skills" / "prd-review" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("COMPACT_V3_WRITING_REVIEW", source)
        self.assertIn("HOST_SUBAGENT_ATTEMPT", source)
        self.assertIn("exact Candidate", source)
        self.assertIn("exact Writing Profile", source)
        self.assertIn("exact Writing Guide", source)
        self.assertIn("exact v3 Review Contract", source)
        self.assertIn("exact PRD Output Contract", source)
        self.assertIn("First pass", source)
        self.assertIn("Second pass", source)
        self.assertIn("must not emit a 13+10 PASS wall", source)
        self.assertIn("ADVISORY_ONLY", source)
        self.assertIn("AGENT_REVIEW_RECORDED_HUMAN_READER_OBSERVATION_NOT_RUN", source)
        self.assertIn("long document", source)
        self.assertIn("large necessary table", source)
        self.assertIn("long appendix", source)
        self.assertIn("document-experience-coverage.v1", source)
        for issue in (
            "SEMANTIC_REPETITION",
            "FLAT_PEER_OVERLOAD",
            "REPRESENTATION_COLLISION",
            "DETAIL_IN_MAIN_PATH",
            "DENSE_TABLE",
            "JARGON_INTRUSION",
            "CHECKLIST_FUNCTION_LOSS",
            "COMPLETION_SEMANTICS_AMBIGUOUS",
            "ARTIFACT_MATURITY_OVERCLAIM",
        ):
            self.assertIn(issue, source)
        for repair in (
            "REORDER", "GROUP", "EXPLAIN", "EXAMPLE", "VISUALIZE", "LAYER",
            "MERGE", "REFERENCE", "MOVE", "TRIM", "RESTORE_FUNCTION", "BOUNDARY",
        ):
            self.assertIn(repair, source)

    def test_v3_public_instruction_exposes_mermaid_source_review_contract(self) -> None:
        source = (
            CORE / "atomic-skills" / "prd-review" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Candidate visual review is source-only and semantic", source)
        self.assertIn("Mermaid source in the exact Markdown", source)
        self.assertIn("observation_status=SOURCE_REVIEWED", source)
        self.assertIn("empty `visual_pair_refs`", source)
        self.assertIn("Handoff alone materializes", source)
        self.assertNotIn("reader_visible_visual_pairs", source)
        self.assertNotIn("coordinate space, not pixels", source)
        self.assertNotIn("short side\nof at least 320 px", source)

    def test_v3_examples_are_complete_validator_ready_contracts(self) -> None:
        instruction = (
            CORE / "atomic-skills" / "prd-review" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")
        zero = extract_json(instruction, "writing-reader-review-v3-zero-finding-contract")
        one = extract_json(instruction, "writing-reader-review-v3-one-finding-contract")

        for payload, findings in ((zero, set()), (one, {"f-writing-001"})):
            validated = validate_writing_coverage(
                payload,
                expected_candidate_ref=payload["candidate_ref"],
                expected_candidate_tree_hash=payload["candidate_tree_hash"],
                expected_profile_ref=payload["profile_ref"],
                expected_guide_ref=payload["guide_ref"],
                expected_review_contract_ref=payload["review_contract_ref"],
                expected_output_contract_ref=payload["output_contract_ref"],
                expected_author_execution_ref=payload["author_execution_ref"],
                required_rule_ids=[],
                required_check_ids=[],
                candidate_line_count=100,
                available_finding_ids=findings,
            )
            self.assertEqual(validated, payload)
        self.assertEqual(zero["finding_refs"], [])
        self.assertEqual(one["finding_refs"], ["f-writing-001"])

    def test_installed_one_finding_example_is_a_complete_valid_node_result(self) -> None:
        instruction = (
            self.installed_core
            / "references"
            / "atomic-skills"
            / "prd-review"
            / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")
        published = extract_json(
            instruction, "review-parallel-v3-one-finding-node-result-contract"
        )
        self.assertEqual(
            published["artifact_refs"],
            [{"role": "writing_coverage", **published["semantic_output"]["writing_coverage_ref"]}],
        )

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            installed_graph = (
                self.installed_core / "references" / "graph" / "manifest.json"
            )
            runtime = HostRuntime(project, installed_graph, self.installed_core)
            run_id = "run-installed-published-one-finding"
            position_review_parallel(runtime, project, run_id)
            dispatch = runtime.dispatch_current(run_id)
            context = dispatch["writing_review_context"]
            result = json.loads(json.dumps(published))
            writing = extract_json(
                instruction, "writing-reader-review-v3-one-finding-contract"
            )
            for field in (
                "candidate_ref",
                "candidate_tree_hash",
                "profile_ref",
                "guide_ref",
                "review_contract_ref",
                "output_contract_ref",
                "author_execution_ref",
                "isolated_input_refs",
            ):
                writing[field] = json.loads(json.dumps(context[field]))
            basis = {
                "path": context["candidate_ref"]["path"],
                "hash": context["candidate_ref"]["hash"],
                "start_line": 20,
                "end_line": 28,
            }
            writing["reader_outcome_failures"][0]["basis_refs"] = [basis]
            writing["verbosity_assessment"]["basis_refs"] = [basis]
            writing_path = project / ".better-product-graph" / "runs" / run_id / "artifacts" / "writing-review-v3.json"
            writing_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(writing_path, writing)
            writing_ref = {
                "path": writing_path.relative_to(project).as_posix(),
                "hash": sha256_file(writing_path),
                "version": 3,
            }
            state = runtime.controller.load_state(run_id)
            candidate_ref = state["current_candidate_ref"]
            commitment_ref = state["artifact_refs"]["product-commitment"]
            resources = {
                item["resource_id"]: item for item in dispatch["resource_refs"]
            }

            def exact(resource_id: str) -> dict:
                return {
                    key: resources[resource_id][key]
                    for key in ("path", "hash", "version")
                }

            result.update(
                {
                    "attempt_id": dispatch["attempt_id"],
                    "instruction_ref": dispatch["instruction_ref"],
                    "instruction_hash": dispatch["instruction_hash"],
                    "input_refs": dispatch["input_refs"],
                    "input_hashes": dispatch["input_hashes"],
                    "resource_refs": dispatch["resource_refs"],
                }
            )
            semantic = result["semantic_output"]
            semantic["candidate_ref"] = candidate_ref
            semantic["goal_fidelity_refs"] = {
                "profile_ref": exact("goal-fidelity-profile"),
                "rubric_ref": exact("goal-fidelity-rubric"),
                "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                "commitment_refs": [commitment_ref],
            }
            semantic["goal_fidelity_packet"]["candidate_ref"] = candidate_ref
            semantic["goal_fidelity_packet"]["commitment_refs"] = [commitment_ref]
            semantic["writing_coverage_ref"] = writing_ref
            finding = semantic["findings"][0]
            finding["basis_refs"] = [basis]
            finding["upstream_commitment_refs"] = [commitment_ref]
            result["artifact_refs"] = [{"role": "writing_coverage", **writing_ref}]

            self.assertEqual(set(finding), REVIEW_FINDING_FIELDS)
            self.assertEqual(validate_review_submission(result), semantic)
            self.assertTrue(runtime.controller.submit_result(run_id, result).is_file())

    def test_every_node_sharing_changed_instructions_declares_exact_predecessor(self) -> None:
        for skill_root, graph in (
            (CORE, GRAPH),
            (
                self.installed_core,
                self.installed_core / "references" / "graph" / "manifest.json",
            ),
        ):
            registry = NodeRegistry(skill_root, graph)
            by_ref = {
                "references/atomic-skills/prd-generate/INSTRUCTIONS.md": GENERATE_PREDECESSOR,
                "references/atomic-skills/prd-review/INSTRUCTIONS.md": REVIEW_PREDECESSOR,
            }
            for node_id, contract in registry.contracts.items():
                predecessor = by_ref.get(contract["instruction_ref"])
                if predecessor is None:
                    continue
                self.assertEqual(
                    registry.instruction_compatibility(node_id, predecessor),
                    "DECLARED_COMPATIBLE_SUCCESSOR",
                    node_id,
                )
                if contract["instruction_ref"].endswith("prd-review/INSTRUCTIONS.md"):
                    for exact_predecessor in (
                        REVIEW_ARTIFACT_EXAMPLE_PREDECESSOR,
                        REVIEW_EXAMPLE_PREDECESSOR,
                    ):
                        self.assertEqual(
                            registry.instruction_compatibility(
                                node_id, exact_predecessor
                            ),
                            "DECLARED_COMPATIBLE_SUCCESSOR",
                            node_id,
                        )
            self.assertEqual(
                registry.attempt_instruction_compatibility(
                    "review.parallel", REVIEW_PREDECESSOR, "PLANNED"
                ),
                "DECLARED_COMPATIBLE_SUCCESSOR",
            )
            self.assertEqual(
                registry.attempt_instruction_compatibility(
                    "review.parallel", REVIEW_PREDECESSOR, "DISPATCHED"
                ),
                "INCOMPATIBLE",
            )
            for predecessor in (
                VISUAL_REVIEW_PREDECESSOR,
                STRICT_VISUAL_REVIEW_PREDECESSOR,
                COMMONMARK_VISUAL_REVIEW_PREDECESSOR,
            ):
                for node_id in ("review.parallel", "review.aggregate", "prd.optimize"):
                    self.assertEqual(
                        registry.attempt_instruction_compatibility(
                            node_id, predecessor, "PLANNED"
                        ),
                        "DECLARED_COMPATIBLE_SUCCESSOR",
                        node_id,
                    )
                    self.assertEqual(
                        registry.attempt_instruction_compatibility(
                            node_id, predecessor, "DISPATCHED"
                        ),
                        "INCOMPATIBLE",
                        node_id,
                    )
            for node_id in ("review.parallel", "review.aggregate", "prd.optimize"):
                contract = registry.contracts[node_id]
                for predecessor in contract["compatible_instruction_hashes"]:
                    self.assertEqual(
                        registry.attempt_instruction_compatibility(
                            node_id, predecessor, "PLANNED"
                        ),
                        "DECLARED_COMPATIBLE_SUCCESSOR",
                        (node_id, predecessor),
                    )
                    self.assertEqual(
                        registry.attempt_instruction_compatibility(
                            node_id, predecessor, "DISPATCHED"
                        ),
                        "INCOMPATIBLE",
                        (node_id, predecessor),
                    )
            self.assertEqual(
                registry.attempt_instruction_compatibility(
                    "review.parallel", VISUAL_REVIEW_PREDECESSOR, "PLANNED"
                ),
                "DECLARED_COMPATIBLE_SUCCESSOR",
            )
            self.assertEqual(
                registry.attempt_instruction_compatibility(
                    "review.parallel", VISUAL_REVIEW_PREDECESSOR, "DISPATCHED"
                ),
                "INCOMPATIBLE",
            )

    def test_installed_distribution_contains_exact_source_instructions(self) -> None:
        for skill in ("prd-generate", "prd-review"):
            source = CORE / "atomic-skills" / skill / "INSTRUCTIONS.md"
            installed = (
                self.installed_core
                / "references"
                / "atomic-skills"
                / skill
                / "INSTRUCTIONS.md"
            )
            self.assertEqual(installed.read_bytes(), source.read_bytes())

    def test_unstarted_predecessor_review_dispatch_is_redispatched_with_current_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            runtime = HostRuntime(project, GRAPH, CORE)
            run_id = "run-review-predecessor-planned"
            position_review_parallel(runtime, project, run_id)
            old_attempt = "attempt-old-review-planned"
            persist_node_dispatch(
                runtime.controller,
                run_id,
                old_attempt,
                contract=predecessor_review_dispatch(runtime, run_id, old_attempt),
            )

            dispatch = runtime.dispatch_current(run_id)
            state = runtime.controller.load_state(run_id)
            attempts = {item["attempt_id"]: item for item in state["dispatch_attempts"]}

            self.assertNotEqual(dispatch["attempt_id"], old_attempt)
            self.assertNotEqual(dispatch["instruction_hash"], REVIEW_PREDECESSOR)
            self.assertEqual(attempts[old_attempt]["status"], "PLANNED")
            self.assertEqual(attempts[dispatch["attempt_id"]]["status"], "DISPATCHED")

    def test_started_predecessor_review_dispatch_fails_closed_without_writes(self) -> None:
        for status in ("DISPATCHED", "UNKNOWN_SIDE_EFFECT"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                runtime = HostRuntime(project, GRAPH, CORE)
                run_id = f"run-review-predecessor-{status.lower()}"
                position_review_parallel(runtime, project, run_id)
                attempt_id = f"attempt-old-review-{status.lower()}"
                persist_node_dispatch(
                    runtime.controller,
                    run_id,
                    attempt_id,
                    contract=predecessor_review_dispatch(runtime, run_id, attempt_id),
                )
                begin_node_call(runtime.controller, run_id, attempt_id)
                if status == "UNKNOWN_SIDE_EFFECT":
                    mark_dispatch_unknown(runtime.controller, run_id, attempt_id)
                run_path = runtime.controller.run_path(run_id)
                before = {
                    path.relative_to(run_path).as_posix(): path.read_bytes()
                    for path in run_path.rglob("*")
                    if path.is_file()
                }

                with self.assertRaisesRegex(TransitionRejected, "contract drifted"):
                    runtime.dispatch_current(run_id)

                after = {
                    path.relative_to(run_path).as_posix(): path.read_bytes()
                    for path in run_path.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
