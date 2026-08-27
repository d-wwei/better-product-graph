from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.prd_assets import PRDAssetChangeError, apply_prd_asset_change_set
from src.bpg.storage import sha256_file
from src.bpg.visual_assets import VisualAssetError, validate_managed_visual_asset_tree
from tests.test_visual_assets import png, svg


class PRDAssetChangeSetTests(unittest.TestCase):
    def _ref(self, root: Path, path: Path) -> dict[str, object]:
        return {
            "path": path.relative_to(root).as_posix(),
            "hash": sha256_file(path),
            "version": 1,
        }

    def test_add_replace_and_remove_use_exact_regular_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / ".better-product-graph/asset-inputs"
            sources.mkdir(parents=True)
            vector = sources / "flow.svg"
            raster = sources / "flow@2x.png"
            vector.write_bytes(svg(text="new"))
            raster.write_bytes(png())
            change_set = {
                "schema_version": "prd-asset-change-set.v1",
                "upsert": [
                    {"destination": "flow.svg", "source_ref": self._ref(root, vector)},
                    {"destination": "flow@2x.png", "source_ref": self._ref(root, raster)},
                ],
                "remove": ["old.svg", "old@2x.png"],
            }

            assets = apply_prd_asset_change_set(
                root,
                {"old.svg": b"old", "old@2x.png": b"old"},
                change_set,
            )

            self.assertEqual(set(assets), {"flow.svg", "flow@2x.png"})
            self.assertEqual(assets["flow.svg"], vector.read_bytes())
            pairs = validate_managed_visual_asset_tree(
                "![flow](./assets/flow.svg)", assets
            )
            self.assertEqual([item["svg_name"] for item in pairs], ["flow.svg"])

    def test_hash_symlink_traversal_extension_and_unknown_fields_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.svg"
            source.write_bytes(svg())
            good_ref = self._ref(root, source)
            cases = {
                "hash": {
                    "schema_version": "prd-asset-change-set.v1",
                    "upsert": [{
                        "destination": "flow.svg",
                        "source_ref": {**good_ref, "hash": "sha256:stale"},
                    }],
                    "remove": [],
                },
                "traversal": {
                    "schema_version": "prd-asset-change-set.v1",
                    "upsert": [{"destination": "../flow.svg", "source_ref": good_ref}],
                    "remove": [],
                },
                "extension": {
                    "schema_version": "prd-asset-change-set.v1",
                    "upsert": [{"destination": "flow.html", "source_ref": good_ref}],
                    "remove": [],
                },
                "unknown": {
                    "schema_version": "prd-asset-change-set.v1",
                    "upsert": [],
                    "remove": [],
                    "extra": True,
                },
            }
            symlink = root / "linked.svg"
            symlink.symlink_to(source)
            cases["symlink"] = {
                "schema_version": "prd-asset-change-set.v1",
                "upsert": [{
                    "destination": "flow.svg",
                    "source_ref": {
                        "path": "linked.svg",
                        "hash": sha256_file(source),
                        "version": 1,
                    },
                }],
                "remove": [],
            }
            for label, change_set in cases.items():
                with self.subTest(label=label), self.assertRaises(PRDAssetChangeError):
                    apply_prd_asset_change_set(root, {}, change_set)

    def test_omitted_change_set_preserves_base_assets(self) -> None:
        base = {
            "flow.svg": b"svg",
            "flow@2x.png": b"png",
            "data-contract.xlsx": b"xlsx",
            "interaction-demo.mp4": b"mp4",
        }
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                apply_prd_asset_change_set(Path(directory), base, None), base
            )

    def test_remove_requires_an_existing_exact_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            PRDAssetChangeError, "remove target does not exist"
        ):
            apply_prd_asset_change_set(
                Path(directory),
                {"flow.svg": svg()},
                {
                    "schema_version": "prd-asset-change-set.v1",
                    "upsert": [],
                    "remove": ["missing.svg"],
                },
            )

    def test_source_ref_version_rejects_bool_and_non_allowed_types(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.svg"
            source.write_bytes(svg())
            base = self._ref(root, source)
            for version in (True, False, 0, -1, 1.5, [], {}, "", "   "):
                change_set = {
                    "schema_version": "prd-asset-change-set.v1",
                    "upsert": [{
                        "destination": "flow.svg",
                        "source_ref": {**base, "version": version},
                    }],
                    "remove": [],
                }
                with self.subTest(version=version), self.assertRaisesRegex(
                    PRDAssetChangeError, "source_ref.version"
                ):
                    apply_prd_asset_change_set(root, {}, change_set)

    def test_delete_one_pair_member_leaves_invalid_final_tree_for_archive_validator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            assets = apply_prd_asset_change_set(
                Path(directory),
                {"flow.svg": svg(), "flow@2x.png": png()},
                {
                    "schema_version": "prd-asset-change-set.v1",
                    "upsert": [],
                    "remove": ["flow@2x.png"],
                },
            )
            self.assertEqual(set(assets), {"flow.svg"})
            with self.assertRaisesRegex(VisualAssetError, "missing PNG pair"):
                validate_managed_visual_asset_tree(
                    "![flow](./assets/flow.svg)", assets
                )


if __name__ == "__main__":
    unittest.main()
