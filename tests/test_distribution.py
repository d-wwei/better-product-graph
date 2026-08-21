from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import BuildError, build_plugin, verify_installed_identity


REPO_ROOT = Path(__file__).resolve().parents[1]


def discoverable_skills(plugin_root: Path) -> list[Path]:
    return sorted(
        path.relative_to(plugin_root)
        for path in (plugin_root / "skills").glob("*/SKILL.md")
    )


class DistributionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.output = Path(self.tempdir.name) / "better-product-graph"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_public_skill_description_uses_explicit_use_when_trigger(self) -> None:
        skill = (
            REPO_ROOT
            / "host-adapters"
            / "codex"
            / "public-skill"
            / "better-product-graph"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("description: Use when ", skill)

    def test_build_has_one_discoverable_skill_and_self_verifiable_identity(self) -> None:
        manifest = build_plugin(REPO_ROOT, self.output)

        self.assertEqual(
            discoverable_skills(self.output),
            [Path("skills/better-product-graph/SKILL.md")],
        )
        self.assertFalse(any(path.is_symlink() for path in self.output.rglob("*")))
        self.assertEqual(manifest["plugin"]["name"], "better-product-graph")
        self.assertEqual(manifest["plugin"]["version"], "0.1.20")
        installed_manifest = json.loads(
            (self.output / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(installed_manifest["version"], "0.1.20")
        self.assertEqual(manifest["architecture_baseline"]["version"], "V1.4")
        self.assertTrue(manifest["execution_contract_fingerprint"].startswith("sha256:"))
        self.assertTrue(manifest["artifact_hash"].startswith("sha256:"))
        self.assertTrue(verify_installed_identity(self.output)["valid"])

    def test_build_inventory_is_sorted_and_excludes_build_manifest_from_artifact_hash(self) -> None:
        build_plugin(REPO_ROOT, self.output)
        built = json.loads((self.output / "build-manifest.json").read_text(encoding="utf-8"))

        paths = [entry["path"] for entry in built["inventory"]]
        self.assertEqual(paths, sorted(paths))
        self.assertNotIn("build-manifest.json", paths)
        self.assertIn(".codex-plugin/plugin.json", paths)
        self.assertIn("skills/better-product-graph/SKILL.md", paths)

    def test_installed_identity_ignores_only_runtime_bytecode_cache(self) -> None:
        build_plugin(REPO_ROOT, self.output)
        cache = (
            self.output
            / "skills"
            / "better-product-graph"
            / "scripts"
            / "bpg"
            / "__pycache__"
        )
        cache.mkdir()
        (cache / "intents.cpython-314.pyc").write_bytes(b"runtime-cache")

        self.assertTrue(verify_installed_identity(self.output)["valid"])

        (cache / "unexpected.txt").write_text("not bytecode", encoding="utf-8")
        self.assertFalse(verify_installed_identity(self.output)["valid"])

    def test_manifest_listing_limits_and_brand_assets_resolve_in_installed_copy(self) -> None:
        build_plugin(REPO_ROOT, self.output)
        plugin = json.loads(
            (self.output / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        interface = plugin["interface"]

        self.assertLessEqual(len(interface["displayName"]), 30)
        self.assertLessEqual(len(interface["shortDescription"]), 30)
        for field in ("composerIcon", "logo"):
            relative = interface[field].removeprefix("./")
            self.assertTrue((self.output / relative).is_file(), field)

    def test_build_rejects_non_allowlisted_public_skill_source(self) -> None:
        public_skill = (
            REPO_ROOT
            / "host-adapters"
            / "codex"
            / "public-skill"
            / "better-product-graph"
        )
        unexpected = public_skill / "secret.txt"
        unexpected.write_text("must not ship", encoding="utf-8")
        self.addCleanup(unexpected.unlink)

        with self.assertRaisesRegex(BuildError, "not allowlisted"):
            build_plugin(REPO_ROOT, self.output)

    def test_build_rejects_a_second_discoverable_skill(self) -> None:
        internal_root = REPO_ROOT / "src" / "core" / "atomic-skills"
        bad_skill = internal_root / "bad-public-entry" / "SKILL.md"
        bad_skill.parent.mkdir(parents=True, exist_ok=True)
        bad_skill.write_text("---\nname: bad\ndescription: bad\n---\n", encoding="utf-8")
        self.addCleanup(bad_skill.parent.rmdir)
        self.addCleanup(bad_skill.unlink)

        with self.assertRaisesRegex(BuildError, "SKILL.md"):
            build_plugin(REPO_ROOT, self.output)

    def test_build_is_byte_stable_for_same_source_identity(self) -> None:
        second = Path(self.tempdir.name) / "second"

        first_manifest = build_plugin(REPO_ROOT, self.output)
        second_manifest = build_plugin(REPO_ROOT, second)

        self.assertEqual(first_manifest, second_manifest)
        first_files = {
            path.relative_to(self.output): path.read_bytes()
            for path in self.output.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second): path.read_bytes()
            for path in second.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first_files, second_files)

    def test_frozen_fallback_derivation_removes_only_public_path_and_records_both_hashes(self) -> None:
        manifest = build_plugin(REPO_ROOT, self.output)
        source = REPO_ROOT / "src" / "core" / "templates" / "fallback" / "product-prd-template.md"
        installed = (
            self.output
            / "skills"
            / "better-product-graph"
            / "references"
            / "templates"
            / "fallback"
            / "product-prd-template.md"
        )
        profiles = json.loads(
            (
                self.output
                / "skills"
                / "better-product-graph"
                / "references"
                / "templates"
                / "profiles.json"
            ).read_text(encoding="utf-8")
        )
        fallback_profile = next(item for item in profiles["profiles"] if item["id"] == "fallback")

        self.assertEqual(
            "sha256:" + __import__("hashlib").sha256(source.read_bytes()).hexdigest(),
            "sha256:ffe22669d8cff3ed7b94566d6cefa3d3381b9d4ce34d99a14039576b730dafa8",
        )
        self.assertNotIn("/Users/", installed.read_text(encoding="utf-8"))
        self.assertEqual(
            fallback_profile["sha256"],
            "sha256:" + __import__("hashlib").sha256(installed.read_bytes()).hexdigest(),
        )
        self.assertEqual(manifest["derived_transforms"][0]["transform_id"], "redact-upstream-local-path-v1")
        self.assertEqual(manifest["derived_transforms"][0]["source_sha256"], fallback_profile["source_sha256"])
        self.assertEqual(manifest["derived_transforms"][0]["output_sha256"], fallback_profile["sha256"])


if __name__ == "__main__":
    unittest.main()
