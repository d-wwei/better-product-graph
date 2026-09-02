from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from src.bpg.alpha_runtime import BPG2AlphaController


ROOT = Path(__file__).resolve().parents[1]


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class BPG2VersionedResourceMigrationTests(unittest.TestCase):
    def test_delivered_resource_bytes_remain_immutable(self) -> None:
        expected = {
            "docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.2.md": "00059adeef0b95ca09c4c0398cd1b35a1a8259aad8a6dddde18e54be63d3db49",
            "docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md": "e82ec004ca7dcf7b022e8d7915f4416d332529defb2a11a138fdb4221c2b6570",
            "src/core/reviewer-profiles/prd-writing-reader-review-v3.1.json": "5659ea767a7270e82343e273ad71c50a49f03b9e3d60b040ab60b608f0a881ef",
            "src/core/reviewer-profiles/prd-writing-reader-review-v3.2.json": "ae17022d652d9486abdce8b253749185bd841271f6591021a13618260cbc65fe",
            "src/core/templates/general/PRD_TEMPLATE_v2.0-alpha.md": "762ae2df48106d8986c220b6f9c40a27a8dea34c69ab79bde29731325b218389",
            "src/core/templates/general/PRD_OUTPUT_CONTRACT_v2.0-alpha.json": "c036329b8d571f7652be12ea284c7050532e7ff18f4653da5788535139aa32a7",
        }
        for relative, expected_hash in expected.items():
            with self.subTest(relative=relative):
                self.assertEqual(sha256(relative), expected_hash)

    def test_new_resources_expose_new_exact_identities(self) -> None:
        method = (ROOT / "docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.4.md").read_text(encoding="utf-8")
        ledger = (ROOT / "docs/architecture/CHANGELOG.md").read_text(encoding="utf-8")
        reviewer_v311 = json.loads((ROOT / "src/core/reviewer-profiles/prd-writing-reader-review-v3.1.1.json").read_text(encoding="utf-8"))
        reviewer_v321 = json.loads((ROOT / "src/core/reviewer-profiles/prd-writing-reader-review-v3.2.1.json").read_text(encoding="utf-8"))
        output_contract = json.loads((ROOT / "src/core/templates/general/PRD_OUTPUT_CONTRACT_v2.0-alpha.3.json").read_text(encoding="utf-8"))

        self.assertIn("版本：v0.4", method)
        self.assertIn("BPG Product Planning Method v0.4 — 2026-09-02", ledger)
        self.assertIn("RELEASED_IN_V2.0.3 / IMMUTABLE", ledger)
        self.assertIn(sha256("docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.4.md"), ledger)
        self.assertIn("v0.3 保持不可变", ledger)
        self.assertEqual(reviewer_v311["resource_id"], "prd-writing-reader-review-v3.1.1")
        self.assertEqual(reviewer_v311["version"], "v3.1.1")
        self.assertEqual(reviewer_v321["resource_id"], "prd-writing-reader-review-v3.2.1")
        self.assertEqual(reviewer_v321["version"], "v3.2.1")
        self.assertEqual(output_contract["contract_version"], "2.0-alpha.3")

    def test_new_alpha_and_build_selectors_bind_new_paths(self) -> None:
        authority = BPG2AlphaController._review_authority_sources()
        self.assertEqual(
            BPG2AlphaController._template_source().name,
            "PRD_TEMPLATE_v2.0-alpha.3.md",
        )
        self.assertEqual(
            (authority["output_contract"][0].name, authority["output_contract"][1]),
            ("PRD_OUTPUT_CONTRACT_v2.0-alpha.3.json", "2.0-alpha.3"),
        )
        self.assertEqual(
            (
                authority["writing_review_contract"][0].name,
                authority["writing_review_contract"][1],
            ),
            ("prd-writing-reader-review-v3.1.1.json", "v3.1.1"),
        )

        build = json.loads((ROOT / "config/plugin-build.json").read_text(encoding="utf-8"))
        self.assertEqual(build["plugin_version"], "2.0.3")
        method_bindings = [
            item
            for item in build["shared_exact_files"]
            if item["source"].startswith("docs/architecture/BPG_PRODUCT_PLANNING_METHOD")
        ]
        self.assertEqual(len(method_bindings), 1)
        method_binding = method_bindings[0]
        self.assertEqual(
            method_binding,
            {
                "source": "docs/architecture/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.4.md",
                "target": "skills/better-product-graph/references/alpha/BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.4.md",
                "fingerprint": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
