from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.storage import sha256_file
from src.bpg.template_packs import TemplatePackError, configure_project_template
from src.bpg.templates import TemplateRegistry


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "src" / "core" / "templates"


class TemplatePackConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.pack = self.root / "pack"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_pack(
        self,
        *,
        version: str = "1.0.0",
        requires_bpg: str = ">=0.2.13,<0.3.0",
        template_text: str = "# {{需求名称}}\n\n## 阅读摘要\n\n{{摘要}}\n",
        manifest_overrides: dict | None = None,
    ) -> Path:
        pack = self.pack if version == "1.0.0" else self.root / f"pack-{version}"
        content = pack / "templates" / "test-product" / version
        content.mkdir(parents=True)
        template = content / "PRD_TEMPLATE.md"
        contract = content / "OUTPUT_CONTRACT.json"
        template.write_text(template_text, encoding="utf-8")
        contract.write_bytes((TEMPLATES / "contracts" / "prd-v0.2.json").read_bytes())
        manifest = {
            "schema_version": "bpg-template-pack.v1",
            "pack_id": "test.product-team",
            "version": version,
            "requires_bpg": requires_bpg,
            "profile_id": "test-product",
            "template": template.relative_to(pack).as_posix(),
            "template_sha256": sha256_file(template),
            "output_contract": contract.relative_to(pack).as_posix(),
            "output_contract_sha256": sha256_file(contract),
            "fallback_policy": "FAIL_CLOSED",
            "applicable": True,
        }
        manifest.update(manifest_overrides or {})
        (pack / "pack.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return pack

    def _configure(self, pack: Path, *, allow_version_change: bool = False) -> dict:
        return configure_project_template(
            project_root=self.project,
            templates_root=TEMPLATES,
            pack_root=pack,
            bpg_version="0.2.13",
            allow_version_change=allow_version_change,
        )

    def test_valid_pack_configures_trusted_project_template_with_exact_identity(self) -> None:
        pack = self._write_pack()

        result = self._configure(pack)

        self.assertEqual(result["status"], "CONFIGURED_AND_ACTIVE")
        self.assertEqual(result["pack_id"], "test.product-team")
        self.assertEqual(result["pack_version"], "1.0.0")
        self.assertEqual(result["bpg_version"], "0.2.13")
        installed = (
            self.project
            / ".better-product-graph"
            / "templates"
            / "test-product"
            / "1.0.0"
        )
        self.assertEqual(
            (installed / "PRD_TEMPLATE.md").read_bytes(),
            (pack / "templates/test-product/1.0.0/PRD_TEMPLATE.md").read_bytes(),
        )
        self.assertEqual(
            (installed / "OUTPUT_CONTRACT.json").read_bytes(),
            (pack / "templates/test-product/1.0.0/OUTPUT_CONTRACT.json").read_bytes(),
        )
        selection = TemplateRegistry(TEMPLATES).resolve(self.project)
        self.assertEqual(selection.origin, "PROJECT")
        self.assertEqual(selection.profile_id, "test-product")
        self.assertEqual(selection.version, "1.0.0")
        self.assertEqual(selection.sha256, result["template_sha256"])
        self.assertEqual(
            selection.output_contract_sha256,
            result["output_contract_sha256"],
        )

    def test_incompatible_bpg_version_is_rejected_without_project_configuration(self) -> None:
        pack = self._write_pack(requires_bpg=">=0.3.0,<0.4.0")

        with self.assertRaisesRegex(TemplatePackError, "requires BPG"):
            self._configure(pack)

        self.assertFalse((self.project / ".better-product-graph").exists())

    def test_prerelease_bpg_version_uses_release_core_for_compatibility(self) -> None:
        pack = self._write_pack(requires_bpg=">=0.2.13,<0.3.0")

        result = configure_project_template(
            project_root=self.project,
            templates_root=TEMPLATES,
            pack_root=pack,
            bpg_version="0.2.18-rc.4",
        )

        self.assertEqual(result["status"], "CONFIGURED_AND_ACTIVE")
        self.assertEqual(result["bpg_version"], "0.2.18-rc.4")

    def test_template_hash_mismatch_is_rejected_without_half_configuration(self) -> None:
        pack = self._write_pack(
            manifest_overrides={"template_sha256": "sha256:" + "0" * 64}
        )

        with self.assertRaisesRegex(TemplatePackError, "Template Pack template hash"):
            self._configure(pack)

        self.assertFalse(
            (self.project / ".better-product-graph/template-profile.json").exists()
        )
        self.assertFalse(
            (self.project / ".better-product-graph/templates/test-product/1.0.0").exists()
        )

    def test_invalid_output_contract_is_rejected_without_half_configuration(self) -> None:
        pack = self._write_pack()
        contract = pack / "templates/test-product/1.0.0/OUTPUT_CONTRACT.json"
        contract.write_text("{}\n", encoding="utf-8")
        manifest_path = pack / "pack.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["output_contract_sha256"] = sha256_file(contract)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaisesRegex(TemplatePackError, "output contract"):
            self._configure(pack)

        self.assertFalse(
            (self.project / ".better-product-graph/template-profile.json").exists()
        )
        self.assertFalse(
            (self.project / ".better-product-graph/templates/test-product/1.0.0").exists()
        )

    def test_invalid_required_table_row_contract_is_rejected_without_configuration(
        self,
    ) -> None:
        pack = self._write_pack()
        contract_path = pack / "templates/test-product/1.0.0/OUTPUT_CONTRACT.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["structures"]["legacy"]["required_table_rows"] = {
            "验收标准": {
                "allowed_statuses": ["已确认"],
                "reason_required_statuses": ["不涉及"],
                "rows": [
                    {
                        "label": "权限检查",
                        "status_column_index": 1,
                    }
                ],
            }
        }
        contract_path.write_text(
            json.dumps(contract, ensure_ascii=False), encoding="utf-8"
        )
        manifest_path = pack / "pack.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["output_contract_sha256"] = sha256_file(contract_path)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaisesRegex(TemplatePackError, "required table-row"):
            self._configure(pack)

        self.assertFalse(
            (self.project / ".better-product-graph/template-profile.json").exists()
        )

    def test_manifest_path_escape_and_symlink_are_rejected(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        escaped = self._write_pack(
            manifest_overrides={
                "template": "../outside.md",
                "template_sha256": sha256_file(outside),
            }
        )
        with self.assertRaisesRegex(TemplatePackError, "escapes|path"):
            self._configure(escaped)

        shutil.rmtree(self.pack)
        linked_pack = self._write_pack()
        template = linked_pack / "templates/test-product/1.0.0/PRD_TEMPLATE.md"
        template.unlink()
        template.symlink_to(outside)
        manifest_path = linked_pack / "pack.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["template_sha256"] = sha256_file(outside)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(TemplatePackError, "symlink"):
            self._configure(linked_pack)

        self.assertFalse(
            (self.project / ".better-product-graph/template-profile.json").exists()
        )

    def test_reconfiguring_same_version_is_idempotent_without_duplicate_history(self) -> None:
        pack = self._write_pack()
        first = self._configure(pack)

        second = self._configure(pack)

        self.assertEqual(first["template_sha256"], second["template_sha256"])
        self.assertEqual(second["status"], "ALREADY_ACTIVE")
        config = json.loads(
            (self.project / ".better-product-graph/template-profile.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(config["history"]), 1)

    def test_version_change_requires_explicit_authorization_and_preserves_old_version(self) -> None:
        first_pack = self._write_pack()
        self._configure(first_pack)
        config_path = self.project / ".better-product-graph/template-profile.json"
        before = config_path.read_bytes()
        second_pack = self._write_pack(
            version="1.1.0",
            template_text="# {{需求名称}}\n\n## 阅读摘要\n\n{{新版摘要}}\n",
        )

        with self.assertRaisesRegex(TemplatePackError, "explicit version change"):
            self._configure(second_pack)

        self.assertEqual(config_path.read_bytes(), before)
        self.assertFalse(
            (self.project / ".better-product-graph/templates/test-product/1.1.0").exists()
        )

        upgraded = self._configure(second_pack, allow_version_change=True)
        self.assertEqual(upgraded["status"], "CONFIGURED_AND_ACTIVE")
        self.assertEqual(upgraded["pack_version"], "1.1.0")
        self.assertTrue(
            (self.project / ".better-product-graph/templates/test-product/1.0.0").is_dir()
        )
        self.assertEqual(TemplateRegistry(TEMPLATES).resolve(self.project).version, "1.1.0")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(len(config["history"]), 2)

    def test_built_runner_exposes_internal_non_graph_configuration_action(self) -> None:
        pack = self._write_pack()
        built = self.root / "built-plugin"
        build_plugin(REPO_ROOT, built)
        runner = built / "skills/better-product-graph/scripts/bpg_runner.py"

        completed = subprocess.run(
            [
                "python3",
                str(runner),
                "--operation",
                "configure-template",
                "--pack-path",
                str(pack),
            ],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "CONFIGURED_AND_ACTIVE")
        self.assertEqual(result["configuration_action"], "PROJECT_TEMPLATE_CONFIGURE")
        self.assertEqual(result["graph_run_created"], False)
        self.assertEqual(result["bpg_version"], "0.2.19")
        self.assertFalse((self.project / ".better-product-graph/runs").exists())

    def test_legacy_install_operation_is_not_a_user_facing_entry(self) -> None:
        pack = self._write_pack()
        built = self.root / "built-plugin"
        build_plugin(REPO_ROOT, built)
        runner = built / "skills/better-product-graph/scripts/bpg_runner.py"

        completed = subprocess.run(
            [
                "python3",
                str(runner),
                "--operation",
                "install-template-pack",
                "--pack-path",
                str(pack),
            ],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr)
        self.assertFalse((self.project / ".better-product-graph").exists())


if __name__ == "__main__":
    unittest.main()
