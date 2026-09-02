import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseSourceIdentityTests(unittest.TestCase):
    def test_release_source_uses_each_host_manifest_fingerprint(self) -> None:
        release = json.loads((ROOT / "RELEASE_SOURCE.json").read_text(encoding="utf-8"))
        codex = json.loads(
            (
                ROOT
                / "plugins"
                / "better-product-graph"
                / "build-manifest.json"
            ).read_text(encoding="utf-8")
        )
        claude = json.loads(
            (
                ROOT
                / "claude-plugins"
                / "better-product-graph"
                / "build-manifest.json"
            ).read_text(encoding="utf-8")
        )

        artifacts = release["release_artifacts"]
        codex_release = artifacts["codex_marketplace_zip"]
        claude_release = artifacts["claude_marketplace_zip"]

        self.assertEqual(release["plugin_version"], codex["plugin"]["version"])
        self.assertEqual(release["plugin_version"], claude["plugin"]["version"])
        self.assertEqual(
            release["artifact_build_source_commit"], codex["git"]["commit"]
        )
        self.assertEqual(
            release["artifact_build_source_commit"], claude["git"]["commit"]
        )
        self.assertFalse(codex["git"]["dirty"])
        self.assertFalse(claude["git"]["dirty"])

        self.assertEqual(codex_release["plugin_artifact_hash"], codex["artifact_hash"])
        self.assertEqual(
            claude_release["plugin_artifact_hash"], claude["artifact_hash"]
        )
        self.assertEqual(
            codex_release["execution_contract_fingerprint"],
            codex["execution_contract_fingerprint"],
        )
        self.assertEqual(
            claude_release["execution_contract_fingerprint"],
            claude["execution_contract_fingerprint"],
        )
        self.assertNotEqual(
            codex_release["execution_contract_fingerprint"],
            claude_release["execution_contract_fingerprint"],
        )
        self.assertEqual(
            artifacts["core_tree_fingerprint"], codex["core_tree_fingerprint"]
        )
        self.assertEqual(
            artifacts["core_tree_fingerprint"], claude["core_tree_fingerprint"]
        )


if __name__ == "__main__":
    unittest.main()
