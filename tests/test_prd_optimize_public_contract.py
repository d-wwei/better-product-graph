from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]


class PRDOptimizePublicContractTests(unittest.TestCase):
    def _installed_instruction(self) -> str:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            return (
                plugin
                / "skills"
                / "better-product-graph"
                / "references"
                / "atomic-skills"
                / "prd-review"
                / "INSTRUCTIONS.md"
            ).read_text(encoding="utf-8")

    def test_installed_instruction_exposes_exact_traceability_copy_rule(self) -> None:
        instruction = self._installed_instruction()

        self.assertIn(
            "optimize_context.metadata_authority.spec_traceability",
            instruction,
        )
        self.assertIn("Copy it byte-for-byte", instruction)

    def test_installed_instruction_exposes_exact_closed_change_log_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            instruction = (
                plugin
                / "skills"
                / "better-product-graph"
                / "references"
                / "atomic-skills"
                / "prd-review"
                / "INSTRUCTIONS.md"
            ).read_text(encoding="utf-8")
            registry = json.loads(
                (
                    plugin
                    / "skills"
                    / "better-product-graph"
                    / "references"
                    / "graph"
                    / "node-contracts.json"
                ).read_text(encoding="utf-8")
            )

        match = re.search(
            r"<!-- prd-optimize-change-log-contract -->\s*```json\s*(\{.*?\})\s*```",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        contract = json.loads(match.group(1))
        self.assertEqual(contract["schema_version"], "prd-optimize-change-log.v1")
        self.assertEqual(
            contract["allowed_keys"],
            [
                "source_candidate_ref",
                "repaired_finding_ids",
                "unadopted_dispositions",
                "material_delta",
                "rereview_scope",
            ],
        )
        example = contract["valid_example"]
        self.assertEqual(set(example), set(contract["allowed_keys"]))
        self.assertIsInstance(example["source_candidate_ref"], dict)
        self.assertIsInstance(example["repaired_finding_ids"], list)
        self.assertIsInstance(example["unadopted_dispositions"], list)
        self.assertTrue(example["material_delta"])
        self.assertTrue(example["rereview_scope"])

        self.assertIn(
            "sha256:294e0ab1660a66406807d6bf846bd7578701ca39c9bebc35a22654b16ec112f5",
            registry["nodes"]["prd.optimize"]["compatible_instruction_hashes"],
        )
        self.assertIn(
            "sha256:93cf9453e27da16eba82d99550b763ef5dec5107afed4308f8afb84a23066c55",
            registry["nodes"]["prd.optimize"]["compatible_instruction_hashes"],
        )

    def test_installed_generate_keeps_legacy_asset_contract_outside_bpg_2_0(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin"
            build_plugin(REPO_ROOT, plugin)
            root = plugin / "skills/better-product-graph/references/atomic-skills"
            generate = (root / "prd-generate/INSTRUCTIONS.md").read_text(encoding="utf-8")
            review = (root / "prd-review/INSTRUCTIONS.md").read_text(encoding="utf-8")

        match = re.search(
            r"<!-- prd-asset-change-set-v1-contract -->\s*```json\s*(\{.*?\})\s*```",
            generate,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        contract = json.loads(match.group(1))
        self.assertEqual(contract["schema_version"], "prd-asset-change-set.v1")
        self.assertEqual(set(contract), {"schema_version", "upsert", "remove"})
        self.assertIn(
            "legacy asset input contract is not used by the BPG 2.0 single-PRD runtime",
            generate,
        )
        self.assertIn("Candidate visual review is source-only and semantic", review)

    def test_installed_review_exposes_mermaid_source_only_semantic_rule(self) -> None:
        instruction = self._installed_instruction()
        self.assertIn("Mermaid source in the exact Markdown", instruction)
        self.assertIn("observation_status=SOURCE_REVIEWED", instruction)
        self.assertIn("Handoff alone materializes", instruction)
        self.assertNotIn("writing_review_context.visual_source_scan", instruction)
        self.assertNotIn("observation_status=NOT_RENDERED", instruction)


if __name__ == "__main__":
    unittest.main()
