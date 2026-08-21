from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.discovery_contract import (
    validate_assumption_checkpoint,
    validate_evidence_map,
    validate_learning_submission,
    validate_problem_quality_review,
)
from src.bpg.planning_contract import validate_plan
from src.bpg.prd_contract import assemble_prd
from src.bpg.review_contract import validate_review_submission
from src.bpg.templates import TemplateRegistry


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstalledHostContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.plugin = Path(cls.temporary.name) / "plugin"
        build_plugin(REPO_ROOT, cls.plugin)
        cls.references = (
            cls.plugin / "skills" / "better-product-graph" / "references" / "atomic-skills"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def _contract(self, skill: str, marker: str) -> dict:
        instruction = (self.references / skill / "INSTRUCTIONS.md").read_text(encoding="utf-8")
        match = re.search(
            rf"<!-- {re.escape(marker)} -->\s*```json\s*(\{{.*?\}})\s*```",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, f"installed {skill} instruction must expose {marker}")
        return json.loads(match.group(1))

    def _public_contract(self, marker: str) -> dict:
        skill = (
            self.plugin / "skills" / "better-product-graph" / "SKILL.md"
        ).read_text(encoding="utf-8")
        match = re.search(
            rf"<!-- {re.escape(marker)} -->\s*```json\s*(\{{.*?\}})\s*```",
            skill,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, f"installed public Skill must expose {marker}")
        return json.loads(match.group(1))

    def test_signal_and_evidence_instructions_expose_complete_semantic_outputs(self) -> None:
        prepared = self._contract("signal-intake", "signal-prepare-semantic-output-contract")
        collected = self._contract("evidence", "evidence-collect-semantic-output-contract")
        mapped = self._contract("evidence", "evidence-map-semantic-output-contract")

        self.assertIsInstance(prepared["prepared_signal"], str)
        self.assertIsInstance(collected["sources"], list)
        self.assertEqual(validate_evidence_map(mapped).status, "READY")
        self.assertIn(mapped["claims"][0]["role"], {
            "SOURCE_ASSERTION", "OBSERVATION", "VERIFIED_CLAIM", "INFERENCE",
            "ASSUMPTION", "PREFERENCE", "PROPOSAL", "UNKNOWN", "AUTHORIZATION",
        })
        self.assertTrue(mapped["claims"][0]["source_ref"])

    def test_assumption_learning_and_synthesis_instructions_expose_complete_outputs(self) -> None:
        assumption = self._contract(
            "assumption-audit", "problem-assumption-audit-semantic-output-contract"
        )
        learning = self._contract(
            "problem-learning", "problem-learning-semantic-output-contract"
        )
        synthesis = self._contract(
            "problem-synthesize", "problem-synthesize-semantic-output-contract"
        )

        self.assertEqual(validate_assumption_checkpoint(assumption).status, "READY")
        self.assertEqual(validate_learning_submission(learning).status, "READY")
        self.assertEqual(sum(item.get("selected") is True for item in assumption["mvus"]), 1)
        self.assertEqual(learning["interaction_policy"], "NO_PM_INTERVIEW")
        self.assertIn("candidate_ref", synthesis)
        self.assertIn("problem_definition", synthesis)

    def test_problem_review_instruction_allows_honest_zero_finding_result(self) -> None:
        review = self._contract(
            "problem-quality-review", "problem-quality-review-zero-finding-contract"
        )
        self.assertEqual(review["findings"], [])
        self.assertEqual(review["dispositions"], [])
        validation = validate_problem_quality_review(review)
        self.assertEqual(validation.status, "READY", validation.repair_targets)
        roles = [item["role"] for item in review["upstream_refs"]]
        self.assertGreaterEqual(len(roles), 3)
        self.assertEqual(len(roles), len(set(roles)))
        self.assertTrue(all(item.get("path") and item.get("hash") for item in review["upstream_refs"]))

    def test_public_skill_exposes_the_exact_host_submission_control_plane(self) -> None:
        envelope = self._public_contract("host-node-result-envelope-contract")
        skill = (
            self.plugin / "skills" / "better-product-graph" / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("--operation submit", skill)
        self.assertIn("--payload-file", skill)
        self.assertEqual(envelope["schema_version"], "node-result.v1")
        self.assertEqual(envelope["producer"]["kind"], "HOST_AGENT")
        self.assertIn("semantic_output", envelope)
        self.assertIn("artifact_refs", envelope)

    def test_planning_instruction_exposes_one_validator_ready_semantic_output(self) -> None:
        plan = self._contract(
            "product-planning", "product-planning-semantic-output-contract"
        )

        validation = validate_plan(plan)
        self.assertEqual(validation.status, "READY", validation.repair_targets)
        self.assertEqual(plan["profile"]["id"], "STANDARD")
        self.assertEqual(plan["slices"][0]["id"], plan["prd_matrix"][0]["slice_id"])
        self.assertTrue(plan["shared_contracts"])
        self.assertTrue(plan["slices"][0]["dependencies"])
        contract_ids = {item["id"] for item in plan["shared_contracts"]}
        self.assertTrue(set(plan["slices"][0]["dependencies"]).issubset(contract_ids))

    def test_prd_instruction_exposes_one_assembly_ready_semantic_output(self) -> None:
        output = self._contract("prd-generate", "prd-generate-semantic-output-contract")
        submission = {
            "node_id": "prd.generate",
            "attempt_id": "attempt-installed-contract",
            "producer": {"kind": "HOST_AGENT", "host": "codex"},
            "instruction_ref": "references/atomic-skills/prd-generate/INSTRUCTIONS.md",
            "instruction_hash": "sha256:instructions",
            "input_refs": ["decision-v1.json", "plan-v1.md", "slice-v1.json"],
            "input_hashes": {
                "decision-v1.json": "sha256:decision",
                "plan-v1.md": "sha256:plan",
                "slice-v1.json": "sha256:slice",
            },
            "semantic_output": output,
            "artifact_refs": [],
        }
        selection = TemplateRegistry(REPO_ROOT / "src" / "core" / "templates").resolve(
            REPO_ROOT
        )

        assembled = assemble_prd(submission, selection)
        self.assertEqual(assembled.metadata["status"], "CANDIDATE")
        self.assertEqual(assembled.metadata["evals"]["applicability"], "RECOMMENDED")

    def test_parallel_review_instruction_exposes_honest_zero_finding_contract(self) -> None:
        output = self._contract("prd-review", "review-parallel-zero-finding-contract")
        submission = {
            "node_id": "review.parallel",
            "attempt_id": "attempt-review-installed-contract",
            "producer": {"kind": "HOST_AGENT", "host": "codex"},
            "instruction_ref": "references/atomic-skills/prd-review/INSTRUCTIONS.md",
            "instruction_hash": "sha256:review-instructions",
            "input_refs": ["prd-v0.1.md"],
            "input_hashes": {"prd-v0.1.md": "sha256:prd"},
            "semantic_output": output,
            "artifact_refs": [],
        }

        validated = validate_review_submission(submission)
        self.assertEqual(validated["findings"], [])
        self.assertEqual(validated["authority"], "ADVISORY_ONLY")


if __name__ == "__main__":
    unittest.main()
