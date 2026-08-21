from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.bpg.templates import TemplateContractError, TemplateRegistry
from src.bpg.storage import sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "src" / "core" / "templates"
FALLBACK_HASH = "sha256:ffe22669d8cff3ed7b94566d6cefa3d3381b9d4ce34d99a14039576b730dafa8"


class TemplateProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.templates = self.root / "templates"
        shutil.copytree(TEMPLATES, self.templates)
        self.registry = TemplateRegistry(self.templates)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_vendored_fallback_has_exact_frozen_upstream_hash(self) -> None:
        fallback = self.templates / "fallback" / "product-prd-template.md"
        self.assertEqual(sha256_file(fallback), FALLBACK_HASH)
        selected = self.registry.pin(self.project, "fallback", "upstream-frozen")
        self.assertEqual(selected.profile_id, "fallback")

    def test_general_v02_is_the_default_with_an_exact_output_contract(self) -> None:
        selected = self.registry.resolve(self.project)
        self.assertEqual(selected.profile_id, "general")
        self.assertEqual(selected.version, "0.2.0")
        self.assertEqual(selected.status, "RELEASED_DEFAULT")
        self.assertTrue(selected.output_contract_path.is_file())
        self.assertEqual(
            sha256_file(selected.output_contract_path),
            selected.output_contract_sha256,
        )

    def test_general_draft_can_be_explicitly_pinned_without_promotion_gate(self) -> None:
        selected = self.registry.pin(self.project, "general", "0.1.0-draft")
        resolved = self.registry.resolve(self.project)
        self.assertEqual(resolved, selected)
        self.assertEqual(resolved.status, "ARCHIVED_DRAFT")

    def test_pinned_version_does_not_silently_migrate_when_registry_adds_newer_version(self) -> None:
        pinned = self.registry.pin(self.project, "general", "0.1.0-draft")
        profiles_path = self.templates / "profiles.json"
        profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
        profiles["profiles"].append(
            {
                "id": "general",
                "version": "0.2.0-draft",
                "status": "DRAFT_BOOTSTRAP_CANDIDATE",
                "path": "general/PRD_TEMPLATE_v0.1.md",
                "sha256": pinned.sha256,
            }
        )
        profiles_path.write_text(json.dumps(profiles), encoding="utf-8")
        refreshed = TemplateRegistry(self.templates)
        self.assertEqual(refreshed.resolve(self.project), pinned)

    def test_explicit_rollback_restores_exact_prior_pin(self) -> None:
        fallback = self.registry.pin(self.project, "fallback", "upstream-frozen")
        general = self.registry.pin(self.project, "general", "0.1.0-draft")
        self.assertNotEqual(fallback.sha256, general.sha256)
        rolled_back = self.registry.rollback(self.project, fallback.sha256)
        self.assertEqual(rolled_back, fallback)
        self.assertEqual(self.registry.resolve(self.project), fallback)

    def test_changed_template_bytes_fail_closed_instead_of_silent_migration(self) -> None:
        self.registry.pin(self.project, "general", "0.1.0-draft")
        path = self.templates / "general" / "PRD_TEMPLATE_v0.1.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        with self.assertRaisesRegex(TemplateContractError, "hash"):
            TemplateRegistry(self.templates).resolve(self.project)


if __name__ == "__main__":
    unittest.main()
