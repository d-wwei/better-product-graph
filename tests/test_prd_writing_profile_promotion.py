from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.promote_prd_writing_profile import (
    WritingProfilePromotionError,
    sync_prd_writing_profile_v02,
)
from src.bpg.document_experience_profile import resolve_prd_document_experience


REPO_ROOT = Path(__file__).resolve().parents[1]


def copy_promotion_inputs(target: Path) -> None:
    shutil.copytree(
        REPO_ROOT / "policies/document-experience",
        target / "policies/document-experience",
    )
    shutil.copytree(REPO_ROOT / "src/core/policies", target / "src/core/policies")


class PrdWritingProfilePromotionTests(unittest.TestCase):
    def test_released_source_runtime_and_registry_are_exact(self) -> None:
        report = sync_prd_writing_profile_v02(REPO_ROOT, check=True)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["stage"], "RELEASED_DEFAULT")
        binding = resolve_prd_document_experience(REPO_ROOT / "src/core/policies")
        self.assertEqual(binding["schema_version"], "prd-document-experience-binding.v1")
        self.assertEqual(binding["profile_ref"]["id"], "prd-plain-language-zh-CN")
        self.assertEqual(binding["profile_ref"]["version"], "0.2.0")
        self.assertEqual(binding["writing_guide_ref"]["version"], "0.2.0")
        self.assertEqual(binding["base_policy_ref"]["version"], "document-experience.v1")

    def test_check_rejects_runtime_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copy_promotion_inputs(root)
            runtime_guide = root / "src/core/policies/prd-writing-guide-v0.2.md"
            runtime_guide.write_text("drift\n", encoding="utf-8")

            with self.assertRaisesRegex(
                WritingProfilePromotionError,
                "runtime PRD writing guide differs",
            ):
                sync_prd_writing_profile_v02(root, check=True)

    def test_check_rejects_registry_default_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copy_promotion_inputs(root)
            registry_path = root / "src/core/policies/document-experience-profiles.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["default_profiles"]["prd"] = {
                "id": "other",
                "version": "9.9.9",
            }
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            with self.assertRaisesRegex(
                WritingProfilePromotionError,
                "released writing profile registry",
            ):
                sync_prd_writing_profile_v02(root, check=True)


if __name__ == "__main__":
    unittest.main()
