from __future__ import annotations

import json
import hashlib
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.state_controller import StateController
from tests.controller_fixtures import position_run_internal


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstalledExecutionSpineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plugin = self.root / "plugin"
        self.project = self.root / "project"
        self.project.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _runner(self) -> Path:
        return self.plugin / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"

    def _invoke(self, *arguments: str) -> dict:
        completed = subprocess.run(
            [sys.executable, str(self._runner()), *arguments],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def _write_payload(self, name: str, payload: dict) -> Path:
        path = self.project / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    @staticmethod
    def _tree_inventory(root: Path) -> dict[str, tuple[str, int]]:
        inventory: dict[str, tuple[str, int]] = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                content = path.read_bytes()
                inventory[path.relative_to(root).as_posix()] = (
                    hashlib.sha256(content).hexdigest(),
                    len(content),
                )
        return inventory

    def test_installed_runner_accepts_new_and_returns_current_host_dispatch(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        payload = self._invoke("new", "用户希望结算失败时得到解释")
        self.assertEqual(payload["status"], "ACTIVATED")
        self.assertEqual(payload["state"]["current_node"], "signal.prepare")
        self.assertEqual(payload["dispatch"]["node_id"], "signal.prepare")
        self.assertEqual(payload["dispatch"]["producer_kind"], "HOST_AGENT")
        self.assertTrue(payload["dispatch"]["instruction_hash"].startswith("sha256:"))
        context = payload["host_execution_context"]
        self.assertEqual(Path(context["project_root"]), self.project.resolve())
        self.assertEqual(
            Path(context["skill_root"]),
            (self.plugin / "skills" / "better-product-graph").resolve(),
        )
        self.assertEqual(
            Path(context["instruction_path"]),
            (
                self.plugin
                / "skills"
                / "better-product-graph"
                / payload["dispatch"]["instruction_ref"]
            ).resolve(),
        )
        self.assertTrue(Path(context["instruction_path"]).is_file())
        self.assertEqual(
            context["dispatch_instruction_hash"], payload["dispatch"]["instruction_hash"]
        )
        self.assertEqual(
            context["installed_instruction_hash"], payload["dispatch"]["instruction_hash"]
        )
        self.assertEqual(context["instruction_compatibility"], "EXACT")
        self.assertIn("keep", context["working_directory_rule"].lower())
        self.assertIn("project_root", context["working_directory_rule"])

    def test_installed_host_context_exposes_declared_compatible_successor(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        skill = self.plugin / "skills" / "better-product-graph"
        runner_path = self._runner()
        spec = importlib.util.spec_from_file_location("installed_bpg_runner", runner_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        legacy_hash = "sha256:aa3bdd94c736ed005238c5bd85c9add81654e6fed73a57b20ba5025d289723b9"
        result = {
            "dispatch": {
                "node_id": "review.aggregate",
                "instruction_ref": "references/atomic-skills/prd-review/INSTRUCTIONS.md",
                "instruction_hash": legacy_hash,
            }
        }

        contextualized = module.with_host_execution_context(
            result,
            project_root=self.project,
            skill_root=skill,
        )
        context = contextualized["host_execution_context"]

        self.assertEqual(context["dispatch_instruction_hash"], legacy_hash)
        self.assertNotEqual(context["installed_instruction_hash"], legacy_hash)
        self.assertEqual(
            context["instruction_compatibility"], "DECLARED_COMPATIBLE_SUCCESSOR"
        )

    def test_installed_runner_refuses_plugin_tree_as_project_without_any_write(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        skill = self.plugin / "skills" / "better-product-graph"
        before = self._tree_inventory(self.plugin)

        commands = (
            ("entry", "new", "must not mutate installed plugin"),
            ("dispatch", "--operation", "dispatch", "--run-id", "run-missing"),
        )
        for label, *arguments in commands:
            with self.subTest(operation=label):
                completed = subprocess.run(
                    [sys.executable, str(self._runner()), *arguments],
                    cwd=skill,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("installed plugin", completed.stderr.lower())
                self.assertEqual(self._tree_inventory(self.plugin), before)
        self.assertFalse((skill / ".git").exists())
        self.assertFalse((skill / ".gitignore").exists())
        self.assertFalse((skill / ".better-product-graph").exists())

    def test_installed_repeated_new_same_content_creates_distinct_occurrence_bound_runs(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)

        first = self._invoke("new", "同一条产品反馈")
        second = self._invoke("new", "同一条产品反馈")

        self.assertNotEqual(first["occurrence_id"], second["occurrence_id"])
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["status"], "ACTIVATED")
        self.assertEqual(second["status"], "ACTIVATED")
        self.assertEqual(first["source_signal_id"], second["source_signal_id"])
        first_source = first["state"]["artifact_refs"]["source_signal"]
        second_source = second["state"]["artifact_refs"]["source_signal"]
        self.assertEqual(first_source["path"], second_source["path"])
        self.assertEqual(first_source["hash"], second_source["hash"])
        self.assertEqual(first["state"]["source_occurrence_id"], first["occurrence_id"])
        self.assertEqual(second["state"]["source_occurrence_id"], second["occurrence_id"])

        self._invoke("pause", first["run_id"])
        resumed = self._invoke("resume", first["run_id"])
        self.assertEqual(resumed["status"], "RESUMED")
        self.assertEqual(resumed["state"]["run_id"], first["run_id"])
        occurrences = self.project / ".better-product-graph" / "signals" / "occurrences.jsonl"
        self.assertEqual(len(occurrences.read_text(encoding="utf-8").splitlines()), 2)

    def test_installed_submit_progresses_multiple_nodes_and_executes_route_select(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        activated = self._invoke("new", "用户反复无法完成结算")
        run_id = activated["run_id"]
        prepare = activated["dispatch"]
        prepare_result = {
            "schema_version": "node-result.v1",
            "node_id": "signal.prepare",
            "attempt_id": prepare["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": prepare["instruction_ref"],
            "instruction_hash": prepare["instruction_hash"],
            "input_refs": prepare["input_refs"],
            "input_hashes": prepare["input_hashes"],
            "semantic_output": {"prepared_signal": "用户反复无法完成结算"},
            "artifact_refs": [],
        }
        prepared = self._invoke(
            "--operation", "submit",
            "--run-id", run_id,
            "--payload-file", str(self._write_payload("prepare.json", prepare_result)),
            "--requested-node", "signal.classify",
        )
        self.assertEqual(prepared["git_preflight"]["status"], "READY")
        self.assertEqual(prepared["dispatch"]["node_id"], "signal.classify")

        classify = prepared["dispatch"]
        classify_result = {
            "schema_version": "node-result.v1",
            "node_id": "signal.classify",
            "attempt_id": classify["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": classify["instruction_ref"],
            "instruction_hash": classify["instruction_hash"],
            "input_refs": classify["input_refs"],
            "input_hashes": classify["input_hashes"],
            "semantic_output": {
                "route_destination": "DISCOVERY_START",
                "existing_links": [],
                "parsed_claims": [],
                "parsed_instructions": [],
            },
            "artifact_refs": [],
        }
        routed = self._invoke(
            "--operation", "submit",
            "--run-id", run_id,
            "--payload-file", str(self._write_payload("classify.json", classify_result)),
            "--requested-node", "route.select",
        )
        self.assertEqual(routed["state"]["last_completed_node"], "route.select")
        self.assertEqual(routed["dispatch"]["node_id"], "evidence.collect")

    def test_installed_submit_infers_the_only_legal_next_node(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        activated = self._invoke("new", "用户反复无法完成结算")
        run_id = activated["run_id"]
        prepare = activated["dispatch"]
        prepare_result = {
            "schema_version": "node-result.v1",
            "node_id": "signal.prepare",
            "attempt_id": prepare["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": prepare["instruction_ref"],
            "instruction_hash": prepare["instruction_hash"],
            "input_refs": prepare["input_refs"],
            "input_hashes": prepare["input_hashes"],
            "semantic_output": {"prepared_signal": "用户反复无法完成结算"},
            "artifact_refs": [],
        }

        prepared = self._invoke(
            "--operation", "submit",
            "--run-id", run_id,
            "--payload-file", str(self._write_payload("prepare-inferred.json", prepare_result)),
        )

        self.assertEqual(prepared["dispatch"]["node_id"], "signal.classify")

    def test_installed_decision_submit_then_owner_choice_routes_independent_authority(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        activated = self._invoke("new", "需要形成产品判断")
        run_id = activated["run_id"]
        position_run_internal(
            StateController(
                self.project,
                REPO_ROOT / "src" / "core" / "graph" / "manifest.json",
            ),
            run_id,
            "product.decision",
            ["product.planning", "evidence.collect"],
        )
        decision_dispatch = self._invoke("--operation", "dispatch", "--run-id", run_id)["dispatch"]
        skill = self.plugin / "skills" / "better-product-graph"
        instruction = (skill / decision_dispatch["instruction_ref"]).read_text(
            encoding="utf-8"
        )
        match = re.search(
            r"<!-- PRODUCT_DECISION_SEMANTIC_OUTPUT_START -->\s*"
            r"```json\s*(\{.*?\})\s*```\s*"
            r"<!-- PRODUCT_DECISION_SEMANTIC_OUTPUT_END -->",
            instruction,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        draft = json.loads(match.group(1))
        decision_result = {
            "schema_version": "node-result.v1",
            "node_id": "product.decision",
            "attempt_id": decision_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": decision_dispatch["instruction_ref"],
            "instruction_hash": decision_dispatch["instruction_hash"],
            "input_refs": decision_dispatch["input_refs"],
            "input_hashes": decision_dispatch["input_hashes"],
            "semantic_output": draft,
            "artifact_refs": [],
        }
        proposed = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._write_payload("decision.json", decision_result)),
        )
        self.assertEqual(proposed["status"], "OWNER_CHOICE_REQUIRED")
        command = {
            "schema_version": "owner-choice-command.v1",
            "decision_id": proposed["proposal"]["decision_id"],
            "proposal_ref": proposed["proposal"]["proposal_ref"],
            "proposal_hash": proposed["proposal"]["proposal_ref"]["hash"],
            "actor": {"kind": "OWNER", "id": "eli"},
            "expected_state_version": proposed["state"]["state_version"],
            "choice": "COMMIT",
            "commit_timing": "NOW",
            "outcome_details": {"COMMIT": {"target": "进入 Planning"}},
        }
        chosen = self._invoke(
            "--operation", "owner-choice", "--run-id", run_id,
            "--payload-file", str(self._write_payload("owner-choice.json", command)),
        )
        self.assertEqual(chosen["state"]["decision"]["chosen_outcome"], "COMMIT")
        self.assertEqual(chosen["dispatch"]["node_id"], "product.planning")

    def test_installed_registry_maps_every_graph_node_to_one_real_instruction_and_validator(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        skill = self.plugin / "skills" / "better-product-graph"
        graph = json.loads((skill / "references" / "graph" / "manifest.json").read_text())
        registry = json.loads(
            (skill / "references" / "graph" / "node-contracts.json").read_text()
        )

        graph_nodes = {item["id"] for item in graph["nodes"]}
        contracts = registry["nodes"]
        self.assertEqual(set(contracts), graph_nodes)
        self.assertIn("handoff.dispatch", graph_nodes)
        self.assertNotIn("handoff.validate", graph_nodes)
        self.assertNotIn("plan.coverage.validate", graph_nodes)
        for node_id, contract in contracts.items():
            with self.subTest(node_id=node_id):
                instruction = skill / contract["instruction_ref"]
                self.assertTrue(instruction.is_file(), instruction)
                self.assertIn(contract["producer_kind"], {"HOST_AGENT", "DETERMINISTIC_PROGRAM"})
                self.assertTrue(contract["validator"])
                self.assertEqual(
                    sorted(contract["routes"]),
                    sorted(edge["to"] for edge in graph["edges"] if edge["from"] == node_id),
                )

    def test_installed_self_check_recomputes_inventory_and_fails_after_tamper(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        valid = subprocess.run(
            [sys.executable, str(self._runner()), "--self-check"],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertTrue(json.loads(valid.stdout)["valid"])

        installed = (
            self.plugin / "skills" / "better-product-graph" / "scripts" / "bpg" / "intents.py"
        )
        installed.write_text(installed.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        invalid = subprocess.run(
            [sys.executable, str(self._runner()), "--self-check"],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(invalid.stdout)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertFalse(payload["valid"])
        self.assertIn("inventory", " ".join(payload["errors"]))


if __name__ == "__main__":
    unittest.main()
