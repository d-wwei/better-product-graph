from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.planning_context import (
    MAX_MATERIAL_BYTES,
    PlanningContextError,
    discover_planning_context,
    validate_planning_context_submission,
)
from src.bpg.storage import sha256_file


class PlanningContextTests(unittest.TestCase):
    def test_discovery_is_bounded_and_skips_sensitive_binary_large_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# 项目\n", encoding="utf-8")
            (root / ".env").write_text("API_TOKEN=secret-value\n", encoding="utf-8")
            (root / "package.json").write_bytes(b"\x00binary")
            (root / "PROJECT.md").write_bytes(b"x" * (MAX_MATERIAL_BYTES + 1))
            (root / "AGENTS.md").symlink_to(root / "README.md")

            discovery = discover_planning_context(root)

            self.assertEqual(
                [item["ref"]["path"] for item in discovery["available_materials"]],
                ["README.md"],
            )
            skipped = {item["path"]: item["status"] for item in discovery["skipped_materials"]}
            self.assertEqual(skipped[".env"], "SKIPPED_SENSITIVE")
            self.assertEqual(skipped["package.json"], "SKIPPED_BINARY")
            self.assertEqual(skipped["PROJECT.md"], "SKIPPED_SIZE_LIMIT")
            self.assertEqual(skipped["AGENTS.md"], "SKIPPED_UNSAFE_PATH")

    def test_limited_context_can_continue_but_only_exact_included_refs_are_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            overview = root / "README.md"
            overview.write_text("# 项目\n", encoding="utf-8")
            ref = {
                "role": "planning_context_source",
                "path": "README.md",
                "hash": sha256_file(overview),
                "version": 1,
            }
            result = {
                "semantic_output": {
                    "schema_version": "planning-context-preparation.v1",
                    "status": "LIMITED",
                    "project_identity": {
                        "name": "demo",
                        "root": ".",
                        "confidence": "MEDIUM",
                        "ambiguities": ["缺少历史 Roadmap"],
                    },
                    "materials": [
                        {
                            "ref": ref,
                            "kind": "PROJECT_OVERVIEW",
                            "decision": "INCLUDE",
                            "reason": "当前可用的唯一概览",
                        }
                    ],
                    "unavailable_sources": ["历史 Roadmap"],
                    "high_impact_gaps": [],
                    "context_summary": {
                        "project_purpose": "说明项目",
                        "current_direction": "先建立最小背景",
                        "constraints": ["背景有限"],
                        "unknowns": ["历史取舍"],
                    },
                    "review": {
                        "status": "LIMITED_CONTINUE",
                        "reviewed_by": {"kind": "HOST_AGENT", "id": "codex"},
                    },
                    "limitations": ["只对当前 Run 生效"],
                    "next_action": "evidence.collect",
                },
                "artifact_refs": [ref],
            }

            validate_planning_context_submission(result)
            result["artifact_refs"] = []
            with self.assertRaisesRegex(PlanningContextError, "exactly equal"):
                validate_planning_context_submission(result)

    def test_unknown_semantic_field_fails_closed(self) -> None:
        result = {
            "semantic_output": {
                "schema_version": "planning-context-preparation.v1",
                "status": "SKIPPED",
                "project_identity": {
                    "name": "demo",
                    "root": ".",
                    "confidence": "LOW",
                    "ambiguities": [],
                },
                "materials": [],
                "unavailable_sources": [],
                "high_impact_gaps": [],
                "context_summary": {
                    "project_purpose": "未知项目",
                    "current_direction": "继续当前需求",
                    "constraints": [],
                    "unknowns": [],
                },
                "review": {
                    "status": "SKIPPED",
                    "reviewed_by": {"kind": "OWNER", "id": "owner"},
                },
                "limitations": ["未建立额外背景"],
                "next_action": "evidence.collect",
                "secret_override": True,
            },
            "artifact_refs": [],
        }
        with self.assertRaisesRegex(PlanningContextError, "unknown field"):
            validate_planning_context_submission(result)


if __name__ == "__main__":
    unittest.main()
