from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.promote_prd_template import TemplatePromotionError, sync_prd_template_v02
from src.bpg.documents import archive_prd_candidate
from src.bpg.prd_contract import PRDContractError, assemble_prd
from src.bpg.storage import sha256_file
from src.bpg.templates import TemplateContractError, TemplateRegistry


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "src" / "core" / "templates"
GOLDENS = REPO_ROOT / "tests" / "fixtures" / "prd-v0.2-golden"


def load_fixture(name: str) -> dict:
    return json.loads((GOLDENS / f"{name}.json").read_text(encoding="utf-8"))


def copy_promotion_inputs(target: Path) -> None:
    shutil.copytree(REPO_ROOT / "templates/prd/general", target / "templates/prd/general")
    shutil.copytree(TEMPLATES, target / "src/core/templates")


class TemplatePromotionV02Tests(unittest.TestCase):
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

    def test_human_source_and_released_runtime_default_are_exact_byte_hash_twins(self) -> None:
        report = sync_prd_template_v02(REPO_ROOT, check=True)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(
            (REPO_ROOT / "templates/prd/general/PRD_TEMPLATE_v0.2.md").read_bytes(),
            (TEMPLATES / "general/PRD_TEMPLATE_v0.2.md").read_bytes(),
        )
        selected = self.registry.pin(self.project, "general", "0.2.0")
        self.assertEqual(selected.status, "RELEASED_DEFAULT")
        self.assertEqual(selected.sha256, report["template_sha256"])
        self.assertEqual(selected.output_contract_sha256, report["output_contract_sha256"])

    def test_read_only_default_resolve_does_not_create_project_control_tree(self) -> None:
        before = sorted(path.relative_to(self.project).as_posix() for path in self.project.rglob("*"))

        selected = self.registry.resolve(self.project)

        after = sorted(path.relative_to(self.project).as_posix() for path in self.project.rglob("*"))
        self.assertEqual(selected.selection_source, "REGISTRY_DEFAULT_UNPINNED")
        self.assertEqual(after, before)
        self.assertFalse((self.project / ".better-product-graph").exists())

    def test_release_check_enforces_exact_default_fallback_and_status(self) -> None:
        mutations = {
            "default": lambda registry: registry.__setitem__(
                "default_profile", {"id": "fallback", "version": "upstream-frozen"}
            ),
            "general-fallback": lambda registry: registry.__setitem__(
                "general_fallback_profile", {"id": "general", "version": "0.1.0-draft"}
            ),
            "default-status": lambda registry: next(
                item
                for item in registry["profiles"]
                if item["id"] == "general" and item["version"] == "0.2.0"
            ).__setitem__("status", "RUNTIME_CANDIDATE"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                root = self.root / f"governance-{name}"
                copy_promotion_inputs(root)
                registry_path = root / "src/core/templates/profiles.json"
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                mutate(registry)
                registry_path.write_text(json.dumps(registry), encoding="utf-8")
                with self.assertRaisesRegex(TemplatePromotionError, "Released|governance"):
                    sync_prd_template_v02(root, check=True)

    def test_release_check_executes_real_output_contract_schema_validation(self) -> None:
        root = self.root / "invalid-contract-schema"
        copy_promotion_inputs(root)
        source = root / "templates/prd/general/OUTPUT_CONTRACT_v0.2.json"
        runtime = root / "src/core/templates/contracts/prd-v0.2.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["structures"]["compact"].pop("required_semantics")
        invalid_bytes = json.dumps(payload, sort_keys=True).encode()
        source.write_bytes(invalid_bytes)
        runtime.write_bytes(invalid_bytes)
        registry_path = root / "src/core/templates/profiles.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        candidate = next(
            item
            for item in registry["profiles"]
            if item["id"] == "general" and item["version"] == "0.2.0"
        )
        candidate["output_contract_sha256"] = sha256_file(runtime)
        registry_path.write_text(json.dumps(registry), encoding="utf-8")

        with self.assertRaisesRegex(TemplatePromotionError, "schema|contract"):
            sync_prd_template_v02(root, check=True)

    def test_project_template_is_used_with_exact_contract_binding(self) -> None:
        trusted = self.project / ".better-product-graph" / "templates"
        trusted.mkdir(parents=True)
        template = trusted / "project-prd.md"
        contract = trusted / "project-prd.output-contract.json"
        template.write_text("# Project template\n", encoding="utf-8")
        contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())

        selected = self.registry.register_project_template(
            self.project,
            profile_id="project.checkout",
            version="1.0.0",
            template_path=template.relative_to(self.project),
            template_sha256=sha256_file(template),
            output_contract_path=contract.relative_to(self.project),
            output_contract_sha256=sha256_file(contract),
            fallback_policy="GENERAL_ON_UNAVAILABLE",
        )

        self.assertEqual(selected.origin, "PROJECT")
        self.assertEqual(selected.selection_source, "PROJECT_TEMPLATE")
        self.assertEqual(selected.fallback_reason, None)
        self.assertEqual(self.registry.resolve(self.project), selected)

    def test_configured_unavailable_project_template_falls_back_auditably(self) -> None:
        trusted = self.project / ".better-product-graph" / "templates"
        trusted.mkdir(parents=True)
        contract = trusted / "missing.output-contract.json"
        contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())
        config = self.project / ".better-product-graph" / "template-profile.json"
        config.write_text(
            json.dumps(
                {
                    "schema_version": "template-profile-pin.v2",
                    "active": {
                        "kind": "PROJECT",
                        "profile_id": "project.missing",
                        "version": "1.0.0",
                        "template_path": ".better-product-graph/templates/missing.md",
                        "template_sha256": "sha256:" + "0" * 64,
                        "output_contract_path": contract.relative_to(self.project).as_posix(),
                        "output_contract_sha256": sha256_file(contract),
                        "output_contract_version": "better-product-graph.prd.general.0.2",
                        "fallback_policy": "GENERAL_ON_UNAVAILABLE",
                        "applicable": True,
                    },
                    "history": [],
                    "migration_policy": "EXPLICIT_ONLY",
                }
            ),
            encoding="utf-8",
        )

        selected = self.registry.resolve(self.project)
        self.assertEqual(selected.profile_id, "general")
        self.assertEqual(selected.selection_source, "GENERAL_FALLBACK")
        self.assertEqual(selected.fallback_reason, "PROJECT_TEMPLATE_UNAVAILABLE")
        self.assertEqual(selected.requested_profile_id, "project.missing")
        self.assertEqual(selected.requested_version, "1.0.0")
        assembled = assemble_prd(load_fixture("simple-compact"), selected)
        self.assertEqual(assembled.metadata["template_profile"]["selection_source"], "GENERAL_FALLBACK")
        self.assertEqual(
            assembled.metadata["template_profile"]["requested_profile_id"],
            "project.missing",
        )
        self.assertEqual(
            assembled.metadata["template_profile"]["output_contract"]["sha256"],
            selected.output_contract_sha256,
        )
        locked = json.loads(config.read_text(encoding="utf-8"))["fallback_lock"]
        self.assertEqual(locked["reason_code"], "PROJECT_TEMPLATE_UNAVAILABLE")
        self.assertTrue(locked["requested_active_sha256"].startswith("sha256:"))
        self.assertEqual(locked["selected_template_relative_path"], selected.relative_path)
        self.assertEqual(
            locked["selected_output_contract_relative_path"],
            selected.output_contract_relative_path,
        )
        self.assertEqual(
            locked["selected_output_contract_version"], selected.output_contract_version
        )

        (trusted / "missing.md").write_text("restored later\n", encoding="utf-8")
        still_locked = TemplateRegistry(self.templates).resolve(self.project)
        self.assertEqual(still_locked.selection_source, "GENERAL_FALLBACK")
        self.assertEqual(still_locked.sha256, selected.sha256)

        restored = trusted / "missing.md"
        explicitly_registered = self.registry.register_project_template(
            self.project,
            profile_id="project.missing",
            version="1.0.0",
            template_path=restored.relative_to(self.project),
            template_sha256=sha256_file(restored),
            output_contract_path=contract.relative_to(self.project),
            output_contract_sha256=sha256_file(contract),
            fallback_policy="GENERAL_ON_UNAVAILABLE",
        )
        self.assertEqual(explicitly_registered.selection_source, "PROJECT_TEMPLATE")
        self.assertNotIn("fallback_lock", json.loads(config.read_text(encoding="utf-8")))

    def test_missing_project_side_does_not_hide_integrity_error_on_existing_side(self) -> None:
        for missing_side in ("template", "contract"):
            with self.subTest(missing_side=missing_side):
                project = self.root / f"missing-{missing_side}"
                trusted = project / ".better-product-graph" / "templates"
                trusted.mkdir(parents=True)
                template = trusted / "project.md"
                contract = trusted / "project.json"
                template.write_text("# valid before tamper\n", encoding="utf-8")
                contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())
                template_hash = sha256_file(template)
                contract_hash = sha256_file(contract)
                if missing_side == "template":
                    template.unlink()
                    contract.write_text("{}\n", encoding="utf-8")
                else:
                    contract.unlink()
                    template.write_text("tampered\n", encoding="utf-8")
                config = project / ".better-product-graph" / "template-profile.json"
                config.write_text(
                    json.dumps(
                        {
                            "schema_version": "template-profile-pin.v2",
                            "active": {
                                "kind": "PROJECT",
                                "profile_id": "project.partial",
                                "version": "1.0.0",
                                "template_path": template.relative_to(project).as_posix(),
                                "template_sha256": template_hash,
                                "output_contract_path": contract.relative_to(project).as_posix(),
                                "output_contract_sha256": contract_hash,
                                "output_contract_version": "better-product-graph.prd.general.0.2",
                                "fallback_policy": "GENERAL_ON_UNAVAILABLE",
                                "applicable": True,
                            },
                            "history": [],
                            "migration_policy": "EXPLICIT_ONLY",
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(TemplateContractError, "hash mismatch"):
                    TemplateRegistry(self.templates).resolve(project)

    def test_project_integrity_and_path_errors_fail_closed_without_fallback(self) -> None:
        trusted = self.project / ".better-product-graph" / "templates"
        trusted.mkdir(parents=True)
        template = trusted / "project.md"
        contract = trusted / "project.json"
        template.write_text("# Project\n", encoding="utf-8")
        contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())
        self.registry.register_project_template(
            self.project,
            profile_id="project.checkout",
            version="1.0.0",
            template_path=template.relative_to(self.project),
            template_sha256=sha256_file(template),
            output_contract_path=contract.relative_to(self.project),
            output_contract_sha256=sha256_file(contract),
            fallback_policy="GENERAL_ON_UNAVAILABLE",
        )
        template.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(TemplateContractError, "hash mismatch"):
            self.registry.resolve(self.project)

        config = json.loads(
            (self.project / ".better-product-graph/template-profile.json").read_text()
        )
        config["active"]["template_path"] = "../escape.md"
        (self.project / ".better-product-graph/template-profile.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        with self.assertRaisesRegex(TemplateContractError, "trusted project template area"):
            self.registry.resolve(self.project)

    def test_project_template_symlink_and_invalid_contract_fail_closed(self) -> None:
        trusted = self.project / ".better-product-graph" / "templates"
        trusted.mkdir(parents=True)
        outside = self.project / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        linked = trusted / "linked.md"
        linked.symlink_to(outside)
        contract = trusted / "contract.json"
        contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())
        with self.assertRaisesRegex(TemplateContractError, "symlink"):
            self.registry.register_project_template(
                self.project,
                profile_id="project.symlink",
                version="1.0.0",
                template_path=linked.relative_to(self.project),
                template_sha256=sha256_file(outside),
                output_contract_path=contract.relative_to(self.project),
                output_contract_sha256=sha256_file(contract),
                fallback_policy="GENERAL_ON_UNAVAILABLE",
            )

        real = trusted / "real.md"
        real.write_text("real\n", encoding="utf-8")
        contract.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(TemplateContractError, "version|schema"):
            self.registry.register_project_template(
                self.project,
                profile_id="project.invalid-contract",
                version="1.0.0",
                template_path=real.relative_to(self.project),
                template_sha256=sha256_file(real),
                output_contract_path=contract.relative_to(self.project),
                output_contract_sha256=sha256_file(contract),
                fallback_policy="GENERAL_ON_UNAVAILABLE",
            )

    def test_runtime_default_is_locked_before_registry_default_can_migrate(self) -> None:
        first = self.registry.resolve_for_runtime(self.project)
        pin = self.project / ".better-product-graph" / "template-profile.json"
        self.assertTrue(pin.is_file())

        profiles_path = self.templates / "profiles.json"
        profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
        profiles["default_profile"] = {"id": "general", "version": "0.2.0"}
        profiles_path.write_text(json.dumps(profiles), encoding="utf-8")

        resolved = TemplateRegistry(self.templates).resolve_for_runtime(self.project)
        self.assertEqual(resolved.profile_id, first.profile_id)
        self.assertEqual(resolved.version, first.version)
        self.assertEqual(resolved.sha256, first.sha256)

    def test_builtin_pin_binds_template_and_contract_paths_and_contract_version(self) -> None:
        selected = self.registry.pin(self.project, "general", "0.2.0")
        config_path = self.project / ".better-product-graph/template-profile.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        active = config["active"]
        self.assertEqual(active["template_relative_path"], selected.relative_path)
        self.assertEqual(
            active["output_contract_relative_path"], selected.output_contract_relative_path
        )
        self.assertEqual(active["output_contract_version"], selected.output_contract_version)
        for field, forged in (
            ("template_relative_path", "general/PRD_TEMPLATE_v0.1.md"),
            ("output_contract_relative_path", "contracts/prd-legacy-v1.json"),
            ("output_contract_version", "forged.contract.v9"),
        ):
            with self.subTest(field=field):
                mutated = json.loads(config_path.read_text(encoding="utf-8"))
                mutated["active"][field] = forged
                config_path.write_text(json.dumps(mutated), encoding="utf-8")
                with self.assertRaisesRegex(TemplateContractError, "pin|identity|changed"):
                    TemplateRegistry(self.templates).resolve(self.project)
                config_path.write_text(json.dumps(config), encoding="utf-8")

    def test_fallback_lock_requires_exact_general_identity_and_known_reason(self) -> None:
        trusted = self.project / ".better-product-graph" / "templates"
        trusted.mkdir(parents=True)
        contract = trusted / "contract.json"
        contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())
        config_path = self.project / ".better-product-graph/template-profile.json"
        config_path.write_text(
            json.dumps(
                {
                    "schema_version": "template-profile-pin.v2",
                    "active": {
                        "kind": "PROJECT",
                        "profile_id": "project.missing",
                        "version": "1.0.0",
                        "template_path": ".better-product-graph/templates/missing.md",
                        "template_sha256": "sha256:" + "0" * 64,
                        "output_contract_path": contract.relative_to(self.project).as_posix(),
                        "output_contract_sha256": sha256_file(contract),
                        "output_contract_version": "better-product-graph.prd.general.0.2",
                        "fallback_policy": "GENERAL_ON_UNAVAILABLE",
                        "applicable": True,
                    },
                    "history": [],
                    "migration_policy": "EXPLICIT_ONLY",
                }
            ),
            encoding="utf-8",
        )
        self.registry.resolve(self.project)
        locked = json.loads(config_path.read_text(encoding="utf-8"))
        for field, forged in (
            ("reason_code", "HASH_MISMATCH"),
            ("selected_profile_id", "fallback"),
        ):
            with self.subTest(field=field):
                mutated = json.loads(json.dumps(locked))
                mutated["fallback_lock"][field] = forged
                config_path.write_text(json.dumps(mutated), encoding="utf-8")
                with self.assertRaisesRegex(TemplateContractError, "fallback|reason|general"):
                    TemplateRegistry(self.templates).resolve(self.project)
        mutated = json.loads(json.dumps(locked))
        mutated["fallback_lock"]["reason_code"] = "PROJECT_TEMPLATE_NOT_APPLICABLE"
        config_path.write_text(json.dumps(mutated), encoding="utf-8")
        with self.assertRaisesRegex(TemplateContractError, "fallback|reason|applicable"):
            TemplateRegistry(self.templates).resolve(self.project)
        config_path.write_text(json.dumps(locked), encoding="utf-8")
        active_mutations = (
            ("kind", "BUILTIN"),
            ("profile_id", "project.forged"),
            ("version", "9.9.9"),
            ("template_path", "../escape.md"),
            ("fallback_policy", "FAIL_CLOSED"),
            ("applicable", False),
            ("template_sha256", "sha256:" + "1" * 64),
            ("output_contract_path", "../escape-contract.json"),
            ("output_contract_sha256", "sha256:" + "2" * 64),
            ("output_contract_version", "forged.contract.v9"),
            ("unknown_field", "forged"),
        )
        for field, forged in active_mutations:
            with self.subTest(active_field=field):
                mutated = json.loads(json.dumps(locked))
                mutated["active"][field] = forged
                config_path.write_text(json.dumps(mutated), encoding="utf-8")
                with self.assertRaises(TemplateContractError):
                    TemplateRegistry(self.templates).resolve(self.project)
        config_path.write_text(json.dumps(locked), encoding="utf-8")
        locked["fallback_lock"] = None
        fallback = self.registry._find("fallback", "upstream-frozen")
        locked["active"] = {
            "kind": "BUILTIN",
            "profile_id": "fallback",
            "version": "upstream-frozen",
            "template_sha256": fallback.sha256,
            "template_relative_path": fallback.relative_path,
            "output_contract_sha256": fallback.output_contract_sha256,
            "output_contract_relative_path": fallback.output_contract_relative_path,
            "output_contract_version": fallback.output_contract_version,
            "selection_source": "GENERAL_FALLBACK",
        }
        config_path.write_text(json.dumps(locked), encoding="utf-8")
        with self.assertRaisesRegex(TemplateContractError, "selection_source|fallback"):
            TemplateRegistry(self.templates).resolve(self.project)

    def test_not_applicable_fallback_lock_rejects_unavailable_reason(self) -> None:
        trusted = self.project / ".better-product-graph" / "templates"
        trusted.mkdir(parents=True)
        template = trusted / "not-applicable.md"
        contract = trusted / "not-applicable.json"
        template.write_text("# not applicable project template\n", encoding="utf-8")
        contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())
        selected = self.registry.register_project_template(
            self.project,
            profile_id="project.not-applicable",
            version="1.0.0",
            template_path=template.relative_to(self.project),
            template_sha256=sha256_file(template),
            output_contract_path=contract.relative_to(self.project),
            output_contract_sha256=sha256_file(contract),
            fallback_policy="GENERAL_ON_UNAVAILABLE",
            applicable=False,
        )
        self.assertEqual(selected.fallback_reason, "PROJECT_TEMPLATE_NOT_APPLICABLE")
        config_path = self.project / ".better-product-graph/template-profile.json"
        locked = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(
            locked["fallback_lock"]["reason_code"],
            "PROJECT_TEMPLATE_NOT_APPLICABLE",
        )
        self.assertEqual(
            self.registry.resolve(self.project).fallback_reason,
            "PROJECT_TEMPLATE_NOT_APPLICABLE",
        )

        locked["fallback_lock"]["reason_code"] = "PROJECT_TEMPLATE_UNAVAILABLE"
        config_path.write_text(json.dumps(locked), encoding="utf-8")
        with self.assertRaisesRegex(TemplateContractError, "fallback|reason|applicable"):
            TemplateRegistry(self.templates).resolve(self.project)

    def test_register_project_template_validates_everything_before_writing_config(self) -> None:
        invalid_values = (
            {"fallback_policy": "ALLOW_ANY"},
            {"applicable": "yes"},
            {"template_sha256": "sha256:" + "0" * 64},
            {"output_contract_sha256": "sha256:" + "0" * 64},
            {"invalid_contract_schema": True},
        )
        for index, overrides in enumerate(invalid_values):
            with self.subTest(overrides=overrides):
                project = self.root / f"atomic-register-{index}"
                trusted = project / ".better-product-graph" / "templates"
                trusted.mkdir(parents=True)
                template = trusted / "project.md"
                contract = trusted / "contract.json"
                template.write_text("# project\n", encoding="utf-8")
                contract.write_bytes((TEMPLATES / "contracts/prd-v0.2.json").read_bytes())
                registry = TemplateRegistry(self.templates)
                registry.pin(project, "fallback", "upstream-frozen")
                config_path = project / ".better-product-graph/template-profile.json"
                before = config_path.read_bytes()
                invalid_contract_schema = overrides.get("invalid_contract_schema", False)
                effective_overrides = {
                    key: value
                    for key, value in overrides.items()
                    if key != "invalid_contract_schema"
                }
                if invalid_contract_schema:
                    contract.write_text("{}\n", encoding="utf-8")
                arguments = {
                    "profile_id": "project.atomic",
                    "version": "1.0.0",
                    "template_path": template.relative_to(project),
                    "template_sha256": sha256_file(template),
                    "output_contract_path": contract.relative_to(project),
                    "output_contract_sha256": sha256_file(contract),
                    "fallback_policy": "FAIL_CLOSED",
                    "applicable": True,
                    **effective_overrides,
                }
                if invalid_contract_schema:
                    arguments["output_contract_sha256"] = sha256_file(contract)
                with self.assertRaises(TemplateContractError):
                    registry.register_project_template(project, **arguments)
                self.assertEqual(config_path.read_bytes(), before)

    def test_project_control_directory_symlink_is_rejected_before_config_write(self) -> None:
        project = self.root / "symlink-control"
        project.mkdir()
        outside = self.root / "outside-control"
        outside.mkdir()
        (project / ".better-product-graph").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(TemplateContractError, "symlink|project control"):
            TemplateRegistry(self.templates).resolve_for_runtime(project)
        self.assertFalse((outside / "template-profile.json").exists())

    def test_concurrent_pin_updates_preserve_every_history_entry(self) -> None:
        self.registry.pin(self.project, "fallback", "upstream-frozen")
        identities = [
            ("general", "0.1.0-draft") if index % 2 else ("fallback", "upstream-frozen")
            for index in range(20)
        ]
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(
                executor.map(
                    lambda identity: self.registry.pin(self.project, *identity),
                    identities,
                )
            )
        config = json.loads(
            (self.project / ".better-product-graph/template-profile.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(config["history"]), 21)

    def test_split_and_compact_shapes_cannot_drop_or_mix_required_semantics(self) -> None:
        selection = self.registry.pin(self.project, "general", "0.2.0")
        compact = load_fixture("simple-compact")
        compact["semantic_output"]["template_mapping"].pop("module_details")
        with self.assertRaisesRegex(PRDContractError, "module_details"):
            assemble_prd(compact, selection)

        split = load_fixture("multi-module-split")
        split["semantic_output"]["document_markdown"] += "\n## 3. 方案与功能规则\n\n冲突。\n"
        with self.assertRaisesRegex(PRDContractError, "forbidden|order"):
            assemble_prd(split, selection)

    def test_markdown_structure_scanner_ignores_fenced_code_examples(self) -> None:
        selection = self.registry.pin(self.project, "general", "0.2.0")
        case = load_fixture("simple-compact")
        case["semantic_output"]["document_markdown"] += """

```markdown
# 伪造标题示例
## 4. 功能与规则详述
| 空表示例 |
|---|
```

~~~text
## 未声明的示例标题
~~~
"""
        assembled = assemble_prd(case, selection)
        self.assertIn("伪造标题示例", assembled.markdown)

    def test_present_conditional_sections_require_substantive_content(self) -> None:
        selection = self.registry.pin(self.project, "general", "0.2.0")
        cases = {
            "empty-omit-or-explain": "## 6. 非功能性要求\n\n",
            "bare-not-applicable": "## 6. 非功能性要求\n\n不适用\n\n",
            "empty-fence": "## 6. 非功能性要求\n\n```mermaid\n\n```\n\n",
            "empty-omit-when-empty": "## 附录 A：支撑材料\n\n",
        }
        for name, section in cases.items():
            with self.subTest(name=name):
                case = load_fixture("simple-compact")
                markdown = case["semantic_output"]["document_markdown"]
                if section.startswith("## 6."):
                    markdown = markdown.replace(
                        "## 7. 兼容、灰度、降级与回滚", section + "## 7. 兼容、灰度、降级与回滚"
                    )
                else:
                    markdown = markdown.replace(
                        "## 附录 C：文档变更日志", section + "## 附录 C：文档变更日志"
                    )
                case["semantic_output"]["document_markdown"] = markdown
                with self.assertRaisesRegex(PRDContractError, "conditional section|substantive"):
                    assemble_prd(case, selection)

        substantive_fences = {
            "mermaid-only": "## 6. 非功能性要求\n\n```mermaid\nflowchart LR\n  A --> B\n```\n\n",
            "json-only": "## 6. 非功能性要求\n\n```json\n{\"retention_days\": 30}\n```\n\n",
        }
        for name, section in substantive_fences.items():
            with self.subTest(name=name):
                case = load_fixture("simple-compact")
                case["semantic_output"]["document_markdown"] = case["semantic_output"][
                    "document_markdown"
                ].replace(
                    "## 7. 兼容、灰度、降级与回滚",
                    section + "## 7. 兼容、灰度、降级与回滚",
                )
                assembled = assemble_prd(case, selection)
                self.assertIn(section.strip(), assembled.markdown)

    def test_three_local_host_authored_golden_cases_use_real_assemble_archive_path(self) -> None:
        selection = self.registry.pin(self.project, "general", "0.2.0")
        for name, expected_mode in (
            ("simple-compact", "compact"),
            ("multi-module-split", "split"),
            ("experiment-high-compliance", "split"),
        ):
            case = load_fixture(name)
            self.assertEqual(case["evidence_class"], "LOCAL_HOST_AGENT_AUTHORED_FIXTURE")
            self.assertEqual(case["semantic_output"]["structure_mode"], expected_mode)
            assembled = assemble_prd(case, selection)
            archived = archive_prd_candidate(
                self.root / f"archive-{name}", assembled, assets={}
            )
            self.assertTrue(archived.document_path.is_file())

    def test_redundant_activation_command_is_rejected_without_changing_the_default(self) -> None:
        root = self.root / "already-released"
        copy_promotion_inputs(root)
        evidence = self.root / "fixture-only-evidence.json"
        evidence.write_text(
            json.dumps(
                {
                    "schema_version": "prd-template-activation-evidence.v1",
                    "status": "PASS",
                    "authenticated_host_agent_status": "PASS",
                    "preactivation_project_pin_audit_status": "PASS",
                    "migration_policy": "EXPLICIT_ONLY",
                    "golden_cases": [
                        "simple-compact",
                        "multi-module-split",
                        "experiment-high-compliance",
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(TemplatePromotionError, "already the released default"):
            sync_prd_template_v02(
                root,
                activate_default=True,
                activation_evidence=evidence,
            )
        report = sync_prd_template_v02(root, check=True)
        self.assertEqual(report["default_activation_status"], "ACTIVE")
        self.assertEqual(
            report["authenticated_host_agent_status"],
            "NOT_ASSERTED_BY_TEMPLATE_SYNC",
        )
        default = TemplateRegistry(root / "src/core/templates").resolve(self.project)
        self.assertEqual(default.profile_id, "general")
        self.assertEqual(default.version, "0.2.0")


if __name__ == "__main__":
    unittest.main()
