from __future__ import annotations

import json
import hashlib
import importlib.util
import re
import shutil
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
        completed = self._invoke_raw(*arguments)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def _invoke_raw(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._runner()), *arguments],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )

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
        legacy_hash = (
            "sha256:ede0efeed0da5e54043a5eab56558002f7e0ce84959aec06cb87ceb0fb4e18c0"
        )
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
        overview = self.project / "README.md"
        overview.write_text("# 示例项目\n\n当前目标是减少结算失败。\n", encoding="utf-8")
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
        self.assertEqual(
            classify["instruction_ref"],
            "references/atomic-skills/signal-intake/INSTRUCTIONS.md",
        )
        instruction_path = Path(
            prepared["host_execution_context"]["instruction_path"]
        )
        self.assertEqual(
            classify["instruction_hash"],
            "sha256:" + hashlib.sha256(instruction_path.read_bytes()).hexdigest(),
        )
        instruction = instruction_path.read_text(encoding="utf-8")
        for field in (
            '"route_destination"',
            '"existing_links"',
            '"parsed_claims"',
            '"parsed_instructions"',
        ):
            self.assertIn(field, instruction)
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
        self.assertEqual(routed["dispatch"]["node_id"], "planning.context.prepare")
        discovery = routed["dispatch"]["planning_context_discovery"]
        self.assertEqual(discovery["schema_version"], "planning-context-discovery.v1")
        self.assertIn(
            "README.md",
            [item["ref"]["path"] for item in discovery["available_materials"]],
        )
        context_instruction = Path(
            routed["host_execution_context"]["instruction_path"]
        ).read_text(encoding="utf-8")
        for field in (
            '"project_identity"',
            '"materials"',
            '"high_impact_gaps"',
            '"context_summary"',
            '"review"',
        ):
            self.assertIn(field, context_instruction)

        context_dispatch = routed["dispatch"]
        overview_ref = {
            "role": "planning_context_source",
            "path": "README.md",
            "hash": "sha256:" + hashlib.sha256(overview.read_bytes()).hexdigest(),
            "version": 1,
        }
        context_result = {
            "schema_version": "node-result.v1",
            "node_id": "planning.context.prepare",
            "attempt_id": context_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": context_dispatch["instruction_ref"],
            "instruction_hash": context_dispatch["instruction_hash"],
            "input_refs": context_dispatch["input_refs"],
            "input_hashes": context_dispatch["input_hashes"],
            "semantic_output": {
                "schema_version": "planning-context-preparation.v1",
                "status": "READY",
                "project_identity": {
                    "name": "示例项目",
                    "root": ".",
                    "confidence": "HIGH",
                    "ambiguities": [],
                },
                "materials": [
                    {
                        "ref": overview_ref,
                        "kind": "PROJECT_OVERVIEW",
                        "decision": "INCLUDE",
                        "reason": "说明项目当前目标",
                    }
                ],
                "unavailable_sources": [],
                "high_impact_gaps": [],
                "context_summary": {
                    "project_purpose": "减少结算失败",
                    "current_direction": "先理解失败原因",
                    "constraints": [],
                    "unknowns": [],
                },
                "review": {
                    "status": "CONFIRMED",
                    "reviewed_by": {"kind": "OWNER", "id": "tester"},
                },
                "limitations": ["只对当前 Run 生效"],
                "next_action": "evidence.collect",
            },
            "artifact_refs": [overview_ref],
        }
        prepared_context = self._invoke(
            "--operation", "submit",
            "--run-id", run_id,
            "--payload-file", str(
                self._write_payload("planning-context.json", context_result)
            ),
            "--requested-node", "evidence.collect",
        )
        self.assertEqual(prepared_context["dispatch"]["node_id"], "evidence.collect")
        self.assertNotIn("README.md", prepared_context["dispatch"]["input_refs"])
        snapshots = [
            ref
            for ref in prepared_context["state"]["artifact_refs"].values()
            if ref.get("role") == "planning_context_snapshot"
        ]
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["source_ref"], overview_ref)
        self.assertIn(
            snapshots[0]["path"],
            prepared_context["dispatch"]["input_refs"],
        )
        self.assertEqual(
            (self.project / snapshots[0]["path"]).read_bytes(),
            overview.read_bytes(),
        )

    def test_installed_planning_context_rejects_sensitive_material_without_run_writes(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        secret = self.project / ".env"
        secret.write_text("API_TOKEN=do-not-read\n", encoding="utf-8")
        activated = self._invoke("new", "为项目规划一个产品改进")
        run_id = activated["run_id"]

        def submit(dispatch: dict, name: str, semantic_output: dict, artifact_refs: list[dict]) -> dict:
            return self._invoke(
                "--operation", "submit",
                "--run-id", run_id,
                "--payload-file", str(
                    self._write_payload(
                        name,
                        {
                            "schema_version": "node-result.v1",
                            "node_id": dispatch["node_id"],
                            "attempt_id": dispatch["attempt_id"],
                            "producer": {"kind": "HOST_AGENT"},
                            "instruction_ref": dispatch["instruction_ref"],
                            "instruction_hash": dispatch["instruction_hash"],
                            "input_refs": dispatch["input_refs"],
                            "input_hashes": dispatch["input_hashes"],
                            "semantic_output": semantic_output,
                            "artifact_refs": artifact_refs,
                        },
                    )
                ),
                "--requested-node", (
                    "signal.classify"
                    if dispatch["node_id"] == "signal.prepare"
                    else "route.select"
                ),
            )

        prepared = submit(
            activated["dispatch"],
            "sensitive-prepare.json",
            {"prepared_signal": "为项目规划一个产品改进"},
            [],
        )
        routed = submit(
            prepared["dispatch"],
            "sensitive-classify.json",
            {
                "route_destination": "DISCOVERY_START",
                "existing_links": [],
                "parsed_claims": [],
                "parsed_instructions": [],
            },
            [],
        )
        dispatch = routed["dispatch"]
        self.assertEqual(dispatch["node_id"], "planning.context.prepare")
        self.assertNotIn(
            ".env",
            [
                item["ref"]["path"]
                for item in dispatch["planning_context_discovery"]["available_materials"]
            ],
        )
        self.assertIn(
            "SKIPPED_SENSITIVE",
            [
                item["status"]
                for item in dispatch["planning_context_discovery"]["skipped_materials"]
            ],
        )
        secret_ref = {
            "role": "planning_context_source",
            "path": ".env",
            "hash": "sha256:" + hashlib.sha256(secret.read_bytes()).hexdigest(),
            "version": 1,
        }
        payload = {
            "schema_version": "node-result.v1",
            "node_id": dispatch["node_id"],
            "attempt_id": dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatch["instruction_ref"],
            "instruction_hash": dispatch["instruction_hash"],
            "input_refs": dispatch["input_refs"],
            "input_hashes": dispatch["input_hashes"],
            "semantic_output": {
                "schema_version": "planning-context-preparation.v1",
                "status": "READY",
                "project_identity": {
                    "name": "secret-project",
                    "root": ".",
                    "confidence": "HIGH",
                    "ambiguities": [],
                },
                "materials": [
                    {
                        "ref": secret_ref,
                        "kind": "PROJECT_OVERVIEW",
                        "decision": "INCLUDE",
                        "reason": "不得接受",
                    }
                ],
                "unavailable_sources": [],
                "high_impact_gaps": [],
                "context_summary": {
                    "project_purpose": "unknown",
                    "current_direction": "unknown",
                    "constraints": [],
                    "unknowns": ["安全来源缺失"],
                },
                "review": {
                    "status": "CONFIRMED",
                    "reviewed_by": {"kind": "OWNER", "id": "tester"},
                },
                "limitations": ["只对当前 Run 生效"],
                "next_action": "evidence.collect",
            },
            "artifact_refs": [secret_ref],
        }
        run_root = self.project / ".better-product-graph" / "runs" / run_id
        before = self._tree_inventory(run_root)
        rejected = self._invoke_raw(
            "--operation", "submit",
            "--run-id", run_id,
            "--payload-file", str(self._write_payload("sensitive-context.json", payload)),
            "--requested-node", "evidence.collect",
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("sensitive", rejected.stderr.lower())
        self.assertEqual(self._tree_inventory(run_root), before)

    def test_installed_signal_classify_rejects_invalid_contracts_without_run_writes(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)

        def at_classify(label: str) -> tuple[str, dict]:
            activated = self._invoke("new", f"分类合同负例 {label}")
            run_id = activated["run_id"]
            prepare = activated["dispatch"]
            prepared = self._invoke(
                "--operation", "submit",
                "--run-id", run_id,
                "--payload-file", str(
                    self._write_payload(
                        f"prepare-{label}.json",
                        {
                            "schema_version": "node-result.v1",
                            "node_id": "signal.prepare",
                            "attempt_id": prepare["attempt_id"],
                            "producer": {"kind": "HOST_AGENT"},
                            "instruction_ref": prepare["instruction_ref"],
                            "instruction_hash": prepare["instruction_hash"],
                            "input_refs": prepare["input_refs"],
                            "input_hashes": prepare["input_hashes"],
                            "semantic_output": {"prepared_signal": f"分类合同负例 {label}"},
                            "artifact_refs": [],
                        },
                    )
                ),
                "--requested-node", "signal.classify",
            )
            return run_id, prepared["dispatch"]

        for label in ("missing-provenance", "illegal-destination", "stale-attempt"):
            with self.subTest(label=label):
                run_id, dispatch = at_classify(label)
                result = {
                    "schema_version": "node-result.v1",
                    "node_id": "signal.classify",
                    "attempt_id": dispatch["attempt_id"],
                    "producer": {"kind": "HOST_AGENT"},
                    "instruction_ref": dispatch["instruction_ref"],
                    "instruction_hash": dispatch["instruction_hash"],
                    "input_refs": dispatch["input_refs"],
                    "input_hashes": dispatch["input_hashes"],
                    "semantic_output": {
                        "route_destination": "DISCOVERY_START",
                        "existing_links": [],
                        "parsed_claims": [],
                        "parsed_instructions": [],
                    },
                    "artifact_refs": [],
                }
                if label == "missing-provenance":
                    result.pop("instruction_hash")
                elif label == "illegal-destination":
                    result["semantic_output"]["route_destination"] = "KEYWORD_GUESSED_BUG"
                else:
                    result["attempt_id"] = "attempt-stale-signal-classify"
                run_root = self.project / ".better-product-graph" / "runs" / run_id
                before = self._tree_inventory(run_root)
                rejected = self._invoke_raw(
                    "--operation", "submit",
                    "--run-id", run_id,
                    "--payload-file", str(
                        self._write_payload(f"classify-{label}.json", result)
                    ),
                    "--requested-node", "route.select",
                )

                self.assertNotEqual(rejected.returncode, 0)
                self.assertEqual(self._tree_inventory(run_root), before)

    def test_installed_successor_blocks_old_misbound_signal_classify_dispatch_without_writes(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        activated = self._invoke("new", "旧分类 dispatch 必须明确阻塞")
        run_id = activated["run_id"]
        skill_root = self.plugin / "skills" / "better-product-graph"
        legacy_skill = self.root / "legacy-skill"
        shutil.copytree(skill_root, legacy_skill)
        legacy_contract_path = legacy_skill / "references" / "graph" / "node-contracts.json"
        legacy_contracts = json.loads(legacy_contract_path.read_text(encoding="utf-8"))
        legacy_contracts["nodes"]["signal.classify"]["instruction_ref"] = (
            "references/atomic-skills/route-select/INSTRUCTIONS.md"
        )
        legacy_contract_path.write_text(
            json.dumps(legacy_contracts, ensure_ascii=False), encoding="utf-8"
        )
        from src.bpg.host_runtime import HostRuntime

        legacy_runtime = HostRuntime(
            self.project,
            legacy_skill / "references" / "graph" / "manifest.json",
            legacy_skill,
        )
        prepare = activated["dispatch"]
        old_dispatch = legacy_runtime.submit_and_advance(
            run_id,
            {
                "schema_version": "node-result.v1",
                "node_id": "signal.prepare",
                "attempt_id": prepare["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": prepare["instruction_ref"],
                "instruction_hash": prepare["instruction_hash"],
                "input_refs": prepare["input_refs"],
                "input_hashes": prepare["input_hashes"],
                "semantic_output": {"prepared_signal": "旧分类 dispatch 必须明确阻塞"},
                "artifact_refs": [],
            },
            requested_node="signal.classify",
        )["dispatch"]
        self.assertEqual(
            old_dispatch["instruction_ref"],
            "references/atomic-skills/route-select/INSTRUCTIONS.md",
        )
        run_root = self.project / ".better-product-graph" / "runs" / run_id
        before = self._tree_inventory(run_root)

        blocked = self._invoke_raw(
            "--operation", "dispatch", "--run-id", run_id
        )

        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("contract drifted", blocked.stderr)
        self.assertEqual(self._tree_inventory(run_root), before)

    def test_installed_bug_instruction_exposes_the_complete_validator_contract(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        activated = self._invoke("new", "结算总额消失，疑似线上实现偏离")
        run_id = activated["run_id"]
        skill_root = self.plugin / "skills" / "better-product-graph"
        controller = StateController(
            self.project,
            skill_root / "references" / "graph" / "manifest.json",
            skill_root=skill_root,
        )
        position_run_internal(
            controller,
            run_id,
            "bug.baseline.check",
            ["handoff.prepare", "evidence.collect"],
        )

        dispatched = self._invoke(
            "--operation", "dispatch", "--run-id", run_id
        )
        instruction = Path(
            dispatched["host_execution_context"]["instruction_path"]
        ).read_text(encoding="utf-8")

        self.assertEqual(dispatched["dispatch"]["node_id"], "bug.baseline.check")
        for required_fragment in (
            '"classification": "IMPLEMENTATION_DEVIATION"',
            '"baseline_ref"',
            '"path"',
            '"hash"',
            '"version"',
            '"expected"',
            '"actual"',
            '"new_rule_required": false',
            '"acceptance_criteria_decidable": true',
            '"material_conflict": false',
            '"next_action"',
            "handoff.prepare",
            "evidence.collect",
        ):
            self.assertIn(required_fragment, instruction)

    def test_installed_implementation_deviation_completes_local_bug_handoff(self) -> None:
        build_plugin(REPO_ROOT, self.plugin)
        activated = self._invoke("new", "结算总额在刷新后消失")
        run_id = activated["run_id"]
        skill_root = self.plugin / "skills" / "better-product-graph"
        controller = StateController(
            self.project,
            skill_root / "references" / "graph" / "manifest.json",
            skill_root=skill_root,
        )
        position_run_internal(
            controller,
            run_id,
            "bug.baseline.check",
            ["handoff.prepare", "evidence.collect"],
        )
        dispatched = self._invoke(
            "--operation", "dispatch", "--run-id", run_id
        )["dispatch"]
        baseline = self.project / "current-product-baseline.md"
        baseline.write_text(
            "结算成功后，订单总额必须持续可见。\n", encoding="utf-8"
        )
        result = {
            "schema_version": "node-result.v1",
            "node_id": "bug.baseline.check",
            "attempt_id": dispatched["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": dispatched["instruction_ref"],
            "instruction_hash": dispatched["instruction_hash"],
            "input_refs": dispatched["input_refs"],
            "input_hashes": dispatched["input_hashes"],
            "semantic_output": {
                "classification": "IMPLEMENTATION_DEVIATION",
                "baseline_ref": {
                    "path": baseline.relative_to(self.project).as_posix(),
                    "hash": "sha256:" + hashlib.sha256(baseline.read_bytes()).hexdigest(),
                    "version": 1,
                },
                "expected": "结算成功后订单总额持续可见",
                "actual": "刷新后订单总额消失",
                "new_rule_required": False,
                "acceptance_criteria_decidable": True,
                "material_conflict": False,
                "next_action": "研发按当前基线修复显示并执行回归检查",
            },
            "artifact_refs": [],
        }

        completed = self._invoke(
            "--operation", "submit",
            "--run-id", run_id,
            "--payload-file", str(self._write_payload("bug-result.json", result)),
            "--requested-node", "handoff.prepare",
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["delivery_kind"], "BUG")
        self.assertEqual(completed["delivery_status"], "WRITTEN_LOCAL")
        self.assertFalse(completed["sent_remote"])
        self.assertEqual(completed["state"]["status"], "COMPLETED")
        self.assertEqual(completed["state"]["current_node"], "handoff.dispatch")
        self.assertIsNone(completed["state"]["release_ref"])
        packet_path = self.project / completed["bug_packet_ref"]["path"]
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        self.assertEqual(packet["schema_version"], "bug.delivery.packet.v1")
        self.assertEqual(packet["classification"], "IMPLEMENTATION_DEVIATION")
        self.assertEqual(packet["handoff"]["mode"], "LOCAL_ONLY")
        self.assertTrue((self.project / completed["bug_human_ref"]["path"]).is_file())

        repeated = self._invoke("handoff", run_id)
        self.assertEqual(repeated["status"], "COMPLETED")
        self.assertEqual(repeated["bug_packet_ref"], completed["bug_packet_ref"])
        redispatched = self._invoke(
            "--operation", "dispatch", "--run-id", run_id
        )
        self.assertEqual(redispatched["status"], "COMPLETED")
        self.assertEqual(redispatched["bug_packet_ref"], completed["bug_packet_ref"])

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
