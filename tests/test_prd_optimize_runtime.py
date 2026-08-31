from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.delivery_contract import derive_active_scope_ref, derive_spec_traceability
from src.bpg.documents import archive_prd_candidate
from src.bpg.failpoints import InjectedCrash, crash_at
from src.bpg.host_runtime import HostRuntime
from src.bpg.prd_contract import assemble_prd, prd_stem
from src.bpg.state_controller import StateController
from src.bpg.storage import (
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
)
from src.bpg.templates import TemplateRegistry
from tests.controller_fixtures import position_run_internal
from tests.test_planning_contract import complete_plan
from tests.test_prd_contract import prd_submission
from tests.writing_review_fixtures import attach_zero_finding_writing_coverage


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"
TEMPLATES = REPO_ROOT / "src" / "core" / "templates"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "prd-v0.2-golden"


class InstalledPRDOptimizeRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plugin = self.root / "plugin"
        self.project = self.root / "project"
        self.project.mkdir()
        self.project = self.project.resolve()
        build_plugin(REPO_ROOT, self.plugin)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _runner(self) -> Path:
        return self.plugin / "skills" / "better-product-graph" / "scripts" / "bpg_runner.py"

    def _payload(self, name: str, value: dict) -> Path:
        path = self.project / name
        atomic_write_json(path, value)
        return path

    def _input_payload(self, name: str, value: dict) -> Path:
        path = self.root / "inputs" / name
        atomic_write_json(path, value)
        return path

    def _invoke_raw(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        if arguments and not arguments[0].startswith("-"):
            scripts = self._runner().parent
            legacy_entry = (
                "import json, sys\n"
                "from pathlib import Path\n"
                "scripts = Path(sys.argv[1]).resolve()\n"
                "project = Path(sys.argv[2]).resolve()\n"
                "sys.path.insert(0, str(scripts))\n"
                "from bpg.host_runtime import HostRuntime\n"
                "skill = scripts.parent\n"
                "graph = skill / 'references' / 'graph' / 'manifest.json'\n"
                "entry = '$better-product-graph ' + ' '.join(sys.argv[3:])\n"
                "result = HostRuntime(project, graph, skill).handle_entry(entry)\n"
                "print(json.dumps(result, ensure_ascii=False))\n"
            )
            return subprocess.run(
                [
                    sys.executable,
                    "-c",
                    legacy_entry,
                    str(scripts),
                    str(self.project),
                    *arguments,
                ],
                cwd=self.project,
                text=True,
                capture_output=True,
                check=False,
            )
        return subprocess.run(
            [sys.executable, str(self._runner()), *arguments],
            cwd=self.project,
            text=True,
            capture_output=True,
            check=False,
        )

    def _invoke(self, *arguments: str) -> dict:
        completed = self._invoke_raw(*arguments)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def _invoke_error(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        completed = self._invoke_raw(*arguments)
        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        return completed

    def _inventory(self) -> dict[str, str]:
        return {
            path.relative_to(self.project).as_posix(): sha256_file(path)
            for path in sorted(self.project.rglob("*"))
            if path.is_file()
        }

    def _exact_upstreams(self, label: str) -> dict[str, dict]:
        refs: dict[str, dict] = {}
        for kind in ("decision", "roadmap", "product_plan", "slice", "knowledge", "evidence"):
            path = self.project / (
                f"product-plan-{label}-v1.md"
                if kind == "product_plan"
                else f"{kind}-{label}-v1.json"
            )
            if kind in {"decision", "evidence"}:
                atomic_write_json(path, {"kind": kind, "version": 1})
            elif kind == "product_plan":
                path.write_text(
                    f"# Product Plan {label}\n\n## Stable Slice\n\n"
                    "The Plan binds a stable PRD and Slice without Candidate version.\n",
                    encoding="utf-8",
                )
            else:
                node_id = {
                    "roadmap": "evidence.collect",
                    "slice": "product.planning",
                    "knowledge": "evidence.map",
                }[kind]
                semantic_output = {
                    "roadmap": {"sources": [{"kind": "PROJECT", "ref": "signal-v1.json"}]},
                    "knowledge": {"claims": []},
                }.get(kind)
                artifact_refs = []
                if kind == "slice":
                    semantic_output = complete_plan()
                    semantic_output["prd_matrix"][0]["planned_prd_id"] = (
                        f"PRD-OPT-{label.upper()}"
                    )
                    plan_ref = refs["product_plan"]
                    artifact_refs = [{"role": "product_plan", **plan_ref}]
                atomic_write_json(
                    path,
                    {
                        "schema_version": "node-result.v1",
                        "node_id": node_id,
                        "attempt_id": f"attempt-{kind}-{label}",
                        "producer": {"kind": "HOST_AGENT"},
                        "instruction_ref": f"references/atomic-skills/{kind}/INSTRUCTIONS.md",
                        "instruction_hash": "sha256:native-instruction",
                        "input_refs": ["signal-v1.json"],
                        "input_hashes": {"signal-v1.json": "sha256:signal"},
                        "semantic_output": semantic_output,
                        "artifact_refs": artifact_refs,
                    },
                )
            refs[kind] = {
                "path": path.relative_to(self.project).as_posix(),
                "hash": sha256_file(path),
                "version": 1,
            }
        return refs

    def _source_candidate(
        self,
        refs: dict[str, dict],
        label: str,
        *,
        source_evals: dict | None = None,
        candidate_version: str = "v0.1",
        authority_run_id: str | None = None,
        source_structure_mode: str = "legacy",
    ):
        submission = (
            json.loads((FIXTURES / "simple-compact.json").read_text(encoding="utf-8"))
            if source_structure_mode == "compact"
            else prd_submission()
        )
        metadata = submission["semantic_output"]["metadata"]
        metadata["prd_id"] = f"PRD-OPT-{label.upper()}"
        metadata["short_title"] = f"结算恢复-{label}"
        if candidate_version != metadata["version"]:
            submission["semantic_output"]["document_markdown"] = submission[
                "semantic_output"
            ]["document_markdown"].replace(metadata["version"], candidate_version)
            metadata["version"] = candidate_version
        current_stem = prd_stem(
            metadata["prd_id"],
            metadata["short_title"],
            metadata["version"],
            metadata["date"],
        )
        lines = submission["semantic_output"]["document_markdown"].splitlines()
        lines[0] = f"# {current_stem}"
        submission["semantic_output"]["document_markdown"] = "\n".join(lines) + "\n"
        metadata["decision_refs"] = [refs["decision"]]
        metadata["roadmap_snapshot_ref"] = refs["roadmap"]
        metadata["product_plan_ref"] = refs["product_plan"]
        metadata["slice_ref"] = refs["slice"]
        metadata["knowledge_snapshot_ref"] = refs["knowledge"]
        metadata["evidence_refs"] = [refs["evidence"]]
        planning_result = read_json(self.project / refs["slice"]["path"])
        metadata["active_scope_ref"] = derive_active_scope_ref(
            planning_result, refs["product_plan"], metadata["prd_id"]
        )
        origins = {
            "decision": ("product.decision", f"attempt-decision-{label}"),
            "roadmap": ("evidence.collect", f"attempt-roadmap-{label}"),
            "product_plan": ("product.planning", planning_result["attempt_id"]),
            "slice": ("product.planning", planning_result["attempt_id"]),
            "knowledge": ("evidence.map", f"attempt-knowledge-{label}"),
            "evidence": ("evidence.collect", f"attempt-evidence-{label}"),
        }
        state_artifacts = (
            list(
                StateController(self.project, GRAPH)
                .load_state(authority_run_id)["artifact_refs"]
                .values()
            )
            if authority_run_id is not None
            else []
        )
        authoritative = {}
        authority_roles = {
            "decision": "decision_record",
            "roadmap": "node_result",
            "product_plan": "product_plan",
            "slice": "node_result",
            "knowledge": "node_result",
            "evidence": "evidence",
        }
        for kind, ref in refs.items():
            matches = [
                item
                for item in state_artifacts
                if all(item.get(key) == ref[key] for key in ("path", "hash", "version"))
                and isinstance(item.get("origin_node_id", item.get("node_id")), str)
                and isinstance(item.get("origin_attempt_id", item.get("attempt_id")), str)
            ]
            authoritative[kind] = matches[0] if matches else {
                **ref,
                "role": authority_roles[kind],
                "origin_node_id": origins[kind][0],
                "origin_attempt_id": origins[kind][1],
            }
        metadata["spec_traceability"] = derive_spec_traceability(
            [(kind, refs[kind]) for kind in (
                "decision", "roadmap", "product_plan", "slice", "knowledge", "evidence"
            )],
            authoritative,
        )
        if source_evals is not None:
            metadata["evals"] = source_evals
        assembled = assemble_prd(
            submission,
            TemplateRegistry(TEMPLATES).resolve(REPO_ROOT),
        )
        return archive_prd_candidate(self.project, assembled, assets={})

    def _prepare_case(
        self,
        label: str,
        *,
        source_evals: dict | None = None,
        source_version: str = "v0.1",
        next_version: str = "v0.2",
        authoritative_upstreams: bool = False,
        source_structure_mode: str = "legacy",
    ) -> dict:
        activated = self._invoke("new", "review optimize must preserve version authority")
        run_id = activated["run_id"]
        refs = self._exact_upstreams(label)
        if authoritative_upstreams:
            controller = StateController(self.project, GRAPH)
            position_run_internal(
                controller,
                run_id,
                "product.decision",
                ["product.planning", "evidence.collect"],
            )
            decision_dispatch = self._invoke(
                "--operation", "dispatch", "--run-id", run_id
            )["dispatch"]
            decision_result = {
                "schema_version": "node-result.v1",
                "node_id": "product.decision",
                "attempt_id": decision_dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": decision_dispatch["instruction_ref"],
                "instruction_hash": decision_dispatch["instruction_hash"],
                "input_refs": decision_dispatch["input_refs"],
                "input_hashes": decision_dispatch["input_hashes"],
                "resource_refs": decision_dispatch["resource_refs"],
                "semantic_output": {
                    "recommendation": "COMMIT",
                    "reasons": ["the accepted repair is bounded", "the outcome is observable"],
                    "mvu": "whether the repaired boundary remains implementable",
                    "nearest_alternative": "EXPERIMENT",
                    "flip_condition": "the repair cannot be observed safely",
                    "next_action": "record the Owner choice",
                    "epistemic_confidence": "MEDIUM",
                    "action_risk": {
                        "level": "R1",
                        "basis": "reversible local change",
                        "reversible": True,
                        "measurable": True,
                        "rollback": "restore the prior version",
                    },
                    "non_waivable_policy_violations": [],
                    "outcome_details": {"COMMIT": {"target": "enter planning"}},
                },
                "artifact_refs": [],
            }
            proposed = self._invoke(
                "--operation", "submit", "--run-id", run_id,
                "--payload-file", str(
                    self._input_payload(f"decision-{label}.json", decision_result)
                ),
            )
            chosen = self._invoke(
                "--operation", "owner-choice", "--run-id", run_id,
                "--payload-file", str(
                    self._input_payload(
                        f"owner-choice-{label}.json",
                        {
                            "schema_version": "owner-choice-command.v1",
                            "decision_id": proposed["proposal"]["decision_id"],
                            "proposal_ref": proposed["proposal"]["proposal_ref"],
                            "proposal_hash": proposed["proposal"]["proposal_ref"]["hash"],
                            "actor": {"kind": "OWNER", "id": "eli"},
                            "expected_state_version": proposed["state"]["state_version"],
                            "choice": "COMMIT",
                            "commit_timing": "NOW",
                            "outcome_details": {"COMMIT": {"target": "enter planning"}},
                        },
                    )
                ),
            )
            refs["decision"] = chosen["state"]["decision"]["record_ref"]

            position_run_internal(
                controller,
                run_id,
                "evidence.collect",
                ["evidence.map"],
            )
            evidence_dispatch = self._invoke(
                "--operation", "dispatch", "--run-id", run_id
            )["dispatch"]
            evidence_content = {"summary": "exact accepted-repair evidence"}
            evidence_path = self.project / f"evidence-{label}-authoritative-v1.json"
            evidence = {
                "schema_version": "evidence-record.v1",
                "kind": "evidence",
                "version": 1,
                "run_id": run_id,
                "status": "RECORDED",
                "authorized": True,
                "received_at": "2026-08-20T00:00:00+00:00",
                "source": {"kind": "MANUAL"},
                "producer": {
                    "node_id": "evidence.collect",
                    "attempt_id": evidence_dispatch["attempt_id"],
                },
                "content": evidence_content,
                "content_hash": sha256_bytes(canonical_json_bytes(evidence_content)),
            }
            atomic_write_json(evidence_path, evidence)
            evidence_ref = {
                "path": evidence_path.relative_to(self.project).as_posix(),
                "hash": sha256_file(evidence_path),
                "version": 1,
            }
            evidence_result = {
                "schema_version": "node-result.v1",
                "node_id": "evidence.collect",
                "attempt_id": evidence_dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": evidence_dispatch["instruction_ref"],
                "instruction_hash": evidence_dispatch["instruction_hash"],
                "input_refs": evidence_dispatch["input_refs"],
                "input_hashes": evidence_dispatch["input_hashes"],
                "resource_refs": evidence_dispatch["resource_refs"],
                "semantic_output": {
                    "sources": [{"kind": "MANUAL", "ref": evidence_ref}]
                },
                "artifact_refs": [{"role": "evidence", **evidence_ref}],
            }
            self._invoke(
                "--operation", "submit", "--run-id", run_id,
                "--payload-file", str(
                    self._input_payload(f"evidence-result-{label}.json", evidence_result)
                ),
                "--requested-node", "evidence.map",
            )
            refs["evidence"] = evidence_ref
        archived = self._source_candidate(
            refs,
            label,
            source_evals=source_evals,
            candidate_version=source_version,
            authority_run_id=run_id if authoritative_upstreams else None,
            source_structure_mode=source_structure_mode,
        )
        source_ref = {
            "role": "prd_candidate",
            "path": archived.document_path.relative_to(self.project).as_posix(),
            "hash": archived.document_hash,
            "tree_hash": archived.tree_hash,
            "artifact_path": archived.path.relative_to(self.project).as_posix(),
            "version": archived.version,
            "review_path": archived.review_path.relative_to(self.project).as_posix(),
            "review_hash": archived.review_hash,
            "generation": 1,
            "origin_node_id": "prd.generate",
            "origin_attempt_id": f"attempt-source-candidate-{label}",
        }
        artifact_refs = (
            dict(StateController(self.project, GRAPH).load_state(run_id)["artifact_refs"])
            if authoritative_upstreams
            else {}
        )
        artifact_refs["prd-candidate"] = source_ref
        existing_paths = {
            item.get("path")
            for item in artifact_refs.values()
            if isinstance(item, dict)
        }
        authority_roles = {
            "decision": "decision_record",
            "roadmap": "node_result",
            "product_plan": "product_plan",
            "slice": "node_result",
            "knowledge": "node_result",
            "evidence": "evidence",
        }
        for kind, ref in refs.items():
            if ref["path"] not in existing_paths:
                trace = next(
                    item
                    for item in read_json(archived.document_path.with_suffix(".metadata.json"))[
                        "spec_traceability"
                    ]["refs"]
                    if item["role"] == kind
                )
                artifact_refs[f"upstream:{kind}"] = {
                    "role": authority_roles[kind],
                    **ref,
                    "origin_node_id": trace["origin_node_id"],
                    "origin_attempt_id": trace["origin_attempt_id"],
                }
                existing_paths.add(ref["path"])
        controller = StateController(self.project, GRAPH)
        position_run_internal(
            controller,
            run_id,
            "review.parallel",
            ["review.aggregate"],
            artifact_refs=artifact_refs,
            state_updates={"current_candidate_ref": source_ref, "candidate_version": 1},
        )

        review_dispatch = self._invoke(
            "--operation", "dispatch", "--run-id", run_id
        )["dispatch"]
        candidate_identity = {
            key: source_ref[key] for key in ("path", "hash", "version")
        }
        accepted = {
            "finding_id": "finding-ac-recovery",
            "topic_id": "acceptance-recovery",
            "stance": "repair-current-prd",
            "concern": "AC does not state the observable recovery result",
            "concern_level": "KEY_ATTENTION",
            "basis_refs": [source_ref["path"], refs["decision"]["path"]],
            "affected_scope": ["验收标准"],
            "possible_impact": "engineering cannot distinguish retry success from duplicate settlement",
            "professional_recommendation": "add the final observable state to AC-1",
            "repair_target": "CURRENT_PRD",
            "confidence": "high",
            "confidence_basis": "exact Candidate and Decision",
        }
        retained = {
            **accepted,
            "finding_id": "finding-future-automation",
            "topic_id": "future-automation",
            "stance": "retain-external-review",
            "concern": "automatic compensation may be useful later",
            "affected_scope": ["future scope"],
            "professional_recommendation": "retain outside this Slice",
            "repair_target": "FUTURE_PLAN",
        }
        resources = {
            item["resource_id"]: item for item in review_dispatch["resource_refs"]
        }

        def exact(resource_id: str) -> dict:
            return {
                key: resources[resource_id][key]
                for key in ("path", "hash", "version")
            }

        review_result = {
            "schema_version": "node-result.v1",
            "node_id": "review.parallel",
            "attempt_id": review_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": review_dispatch["instruction_ref"],
            "instruction_hash": review_dispatch["instruction_hash"],
            "input_refs": review_dispatch["input_refs"],
            "input_hashes": review_dispatch["input_hashes"],
            "resource_refs": review_dispatch["resource_refs"],
            "semantic_output": {
                "candidate_ref": candidate_identity,
                "reviewer_role": "combined-advisory-review",
                "reviewer_profile": "product-goal-fidelity-v0.1",
                "roles_covered": ["product", "engineering_feasibility", "testability"],
                "authority": "ADVISORY_ONLY",
                "goal_fidelity_refs": {
                    "profile_ref": exact("goal-fidelity-profile"),
                    "rubric_ref": exact("goal-fidelity-rubric"),
                    "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                    "commitment_refs": [refs["decision"]],
                },
                "goal_fidelity_packet": {
                    "goal": "Preserve exact accepted and retained review authority",
                    "candidate_ref": candidate_identity,
                    "commitment_refs": [refs["decision"]],
                },
                "findings": [accepted, retained],
            },
            "artifact_refs": [],
        }
        writing_ref = attach_zero_finding_writing_coverage(
            self.project, review_dispatch, review_result
        )
        aggregate_dispatch = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(
                self._input_payload(f"review-result-{label}.json", review_result)
            ),
            "--requested-node", "review.aggregate",
        )["dispatch"]
        aggregate = {
            "schema_version": "review-aggregate.v1",
            "authority": "ADVISORY_ONLY",
            "candidate_ref": candidate_identity,
            "attempts": [
                {
                    "attempt_id": review_dispatch["attempt_id"],
                    "status": "COMPLETED",
                    "roles_covered": ["product", "engineering_feasibility", "testability"],
                }
            ],
            "findings": [accepted, retained],
            "disagreements": [
                {
                    "topic_id": "future-automation",
                    "finding_ids": [retained["finding_id"]],
                }
            ],
            "writing_coverage_ref": writing_ref,
        }
        dispositions = {
            "schema_version": "review-dispositions.v1",
            "candidate_hash": source_ref["hash"],
            "candidate_version": source_ref["version"],
            "dispositions": [
                {
                    "finding_id": accepted["finding_id"],
                    "status": "ACCEPTED_CURRENT_PRD_REPAIR",
                    "repair_scope": ["验收标准"],
                },
                {
                    "finding_id": retained["finding_id"],
                    "status": "RETAIN_FOR_EXTERNAL_REVIEW",
                    "reason": "outside current Slice",
                },
            ],
        }
        aggregate_path = self._payload(f"review-aggregate-{label}.json", aggregate)
        dispositions_path = self._payload(f"review-dispositions-{label}.json", dispositions)
        aggregate_result = {
            "schema_version": "node-result.v1",
            "node_id": "review.aggregate",
            "attempt_id": aggregate_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": aggregate_dispatch["instruction_ref"],
            "instruction_hash": aggregate_dispatch["instruction_hash"],
            "input_refs": aggregate_dispatch["input_refs"],
            "input_hashes": aggregate_dispatch["input_hashes"],
            "resource_refs": aggregate_dispatch["resource_refs"],
            "semantic_output": {**aggregate, "dispositions": dispositions["dispositions"]},
            "artifact_refs": [
                {
                    "role": "review_aggregate",
                    "path": aggregate_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(aggregate_path),
                    "version": 1,
                },
                {
                    "role": "review_dispositions",
                    "path": dispositions_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(dispositions_path),
                    "version": 1,
                },
            ],
        }
        optimize_dispatch = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._input_payload(f"aggregate-result-{label}.json", aggregate_result)),
            "--requested-node", "prd.optimize",
        )["dispatch"]
        published_traceability = optimize_dispatch["optimize_context"][
            "metadata_authority"
        ]["spec_traceability"]

        self.assertEqual(
            optimize_dispatch["optimize_context"],
            {
                "source_candidate_ref": candidate_identity,
                "aggregate_ref": {
                    "path": aggregate_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(aggregate_path),
                    "version": 1,
                },
                "dispositions_ref": {
                    "path": dispositions_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(dispositions_path),
                    "version": 1,
                },
                "accepted_findings": [accepted],
                "accepted_dispositions": [dispositions["dispositions"][0]],
                "unadopted_dispositions": [dispositions["dispositions"][1]],
                "repair_scope": ["验收标准"],
                "next_version": next_version,
                "metadata_authority": {
                    "spec_traceability": published_traceability,
                },
            },
        )

        source_markdown = archived.document_path.read_text(encoding="utf-8")
        revised_markdown = source_markdown.replace(
            f"版本：{source_version}", f"版本：{next_version}"
        ).replace(
            f"{source_version} 首次形成候选",
            f"{next_version} 明确 AC-1 的最终可观察状态；自动补偿建议保留给外置审核，"
            "未纳入当前 Slice",
        )
        source_metadata = json.loads(
            archived.document_path.with_suffix(".metadata.json").read_text(encoding="utf-8")
        )
        revised_metadata = {
            **source_metadata,
            "version": next_version,
            "supersedes": candidate_identity,
            "evals": {
                "applicability": "RECOMMENDED",
                "fulfillment": "NOT_STARTED",
                "reason": "the revised recovery boundary would benefit from regression examples",
            },
            "change_log": {
                "source_candidate_ref": candidate_identity,
                "repaired_finding_ids": [accepted["finding_id"]],
                "unadopted_dispositions": [dispositions["dispositions"][1]],
                "material_delta": ["AC-1 now names the observable final state"],
                "rereview_scope": ["验收标准", "目标与成功边界"],
            },
        }
        revised_lines = revised_markdown.splitlines()
        revised_lines[0] = "# " + prd_stem(
            revised_metadata["prd_id"],
            revised_metadata["short_title"],
            revised_metadata["version"],
            revised_metadata["date"],
        )
        revised_markdown = "\n".join(revised_lines) + "\n"
        optimize_result = {
            "schema_version": "node-result.v1",
            "node_id": "prd.optimize",
            "attempt_id": optimize_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": optimize_dispatch["instruction_ref"],
            "instruction_hash": optimize_dispatch["instruction_hash"],
            "input_refs": optimize_dispatch["input_refs"],
            "input_hashes": optimize_dispatch["input_hashes"],
            "resource_refs": optimize_dispatch["resource_refs"],
            "semantic_output": {
                "source_candidate_ref": candidate_identity,
                "candidate_ref": {"prd_id": archived.prd_id, "version": next_version},
                "proposed_scope_projection": {
                    "id": "slice-1",
                    "user_outcome": "失败用户可安全重试并知道结果",
                    "modules": ["checkout", "recovery"],
                    "iteration": "iteration-1",
                    "dependencies": ["payment-state-v1"],
                    "validation": "端到端 AC",
                    "split_reason": "可独立交付、验证和回滚的产品闭环",
                    "delivery_intent": "COMMIT",
                },
                "document_markdown": revised_markdown,
                "template_mapping": source_metadata["template_mapping"],
                "metadata": revised_metadata,
            },
            "artifact_refs": [],
        }
        latest_state = StateController(self.project, GRAPH).load_state(run_id)
        latest_artifacts = latest_state["artifact_refs"]
        trace_pairs = [
            (kind, refs[kind])
            for kind in (
                "decision", "roadmap", "product_plan", "slice", "knowledge", "evidence"
            )
        ]
        trace_pairs.append(("source_candidate", candidate_identity))
        review_result_refs = [
            item
            for item in latest_artifacts.values()
            if isinstance(item, dict)
            and item.get("role") == "node_result"
            and item.get("node_id") == "review.aggregate"
            and item.get("path") in optimize_dispatch["input_refs"]
        ]
        self.assertEqual(len(review_result_refs), 1)
        trace_pairs.append(("review_aggregate_result", review_result_refs[0]))
        expected_traceability = derive_spec_traceability(trace_pairs, latest_artifacts)
        self.assertEqual(published_traceability, expected_traceability)
        optimize_result["semantic_output"]["metadata"][
            "spec_traceability"
        ] = deepcopy(published_traceability)
        return {
            "run_id": run_id,
            "archived": archived,
            "source_ref": source_ref,
            "source_markdown": source_markdown,
            "refs": refs,
            "optimize_dispatch": optimize_dispatch,
            "optimize_result": optimize_result,
        }

    def test_installed_optimize_archives_agent_vnext_and_rebinds_rereview(self) -> None:
        case = self._prepare_case("success")
        run_id = case["run_id"]
        optimize_result = case["optimize_result"]
        plan_path = self.project / case["refs"]["product_plan"]["path"]
        plan_hash_before = sha256_file(plan_path)
        advanced = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._input_payload("optimize-result-success.json", optimize_result)),
            "--requested-node", "review.parallel",
        )

        current = advanced["state"]["current_candidate_ref"]
        self.assertEqual(current["version"], "v0.2")
        self.assertEqual(advanced["dispatch"]["node_id"], "review.parallel")
        self.assertEqual(
            advanced["dispatch"]["input_hashes"][current["path"]],
            current["hash"],
        )
        self.assertEqual(
            case["archived"].document_path.read_text(encoding="utf-8"),
            case["source_markdown"],
        )
        self.assertTrue((self.project / current["artifact_path"]).is_dir())
        current_markdown = (self.project / current["path"]).read_text(encoding="utf-8")
        self.assertNotIn("finding-ac-recovery", current_markdown)
        self.assertNotIn("finding-future-automation", current_markdown)
        self.assertEqual(sha256_file(plan_path), plan_hash_before)
        repeated = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._input_payload("optimize-result-success.json", optimize_result)),
            "--requested-node", "review.parallel",
        )
        self.assertEqual(repeated["state"]["state_version"], advanced["state"]["state_version"])
        self.assertEqual(repeated["state"]["current_candidate_ref"], current)
        self.assertEqual(repeated["dispatch"]["attempt_id"], advanced["dispatch"]["attempt_id"])

    def test_installed_optimize_publishes_exact_traceability_authority(self) -> None:
        case = self._prepare_case("published-traceability")

        self.assertEqual(
            case["optimize_dispatch"]["optimize_context"]["metadata_authority"][
                "spec_traceability"
            ],
            case["optimize_result"]["semantic_output"]["metadata"][
                "spec_traceability"
            ],
        )

    def test_installed_started_predecessor_optimize_attempt_fails_closed_without_writes(self) -> None:
        case = self._prepare_case("predecessor-traceability")
        run_id = case["run_id"]
        attempt_id = case["optimize_dispatch"]["attempt_id"]
        predecessor_hash = (
            "sha256:93cf9453e27da16eba82d99550b763ef5dec5107afed4308f8afb84a23066c55"
        )
        controller = StateController(self.project, GRAPH)
        state = controller.load_state(run_id)
        predecessor_state = deepcopy(state)
        predecessor_state["state_version"] += 1
        durable = next(
            item for item in predecessor_state["dispatch_attempts"]
            if item["attempt_id"] == attempt_id
        )
        durable["contract"]["instruction_hash"] = predecessor_hash
        durable["contract"]["optimize_context"].pop("metadata_authority")
        durable["authorized_state_version"] = predecessor_state["state_version"]
        durable["authority_hash"] = controller._dispatch_authority_hash(
            predecessor_state
        )
        controller._commit_state_event(
            run_id,
            state,
            predecessor_state,
            {
                "event_type": "NODE_TRANSITION_COMMITTED",
                "actor": "state-controller",
                "run_id": run_id,
                "from_node": "prd.optimize",
                "to_node": "prd.optimize",
                "attempt_id": "internal-compatible-predecessor-fixture",
                "before_state_version": state["state_version"],
                "after_state_version": predecessor_state["state_version"],
            },
            transaction_id="internal-compatible-predecessor-fixture",
        )

        before = self._inventory()
        rejected = self._invoke_error(
            "--operation", "dispatch", "--run-id", run_id
        )

        self.assertIn("contract drifted", rejected.stderr)
        self.assertEqual(self._inventory(), before)

    def test_installed_optimize_accepts_template_mapped_visible_change_log(self) -> None:
        case = self._prepare_case(
            "mapped-changelog",
            source_structure_mode="compact",
        )
        result = deepcopy(case["optimize_result"])
        output = result["semantic_output"]
        output["structure_mode"] = "compact"
        output["document_markdown"] = output["document_markdown"].replace(
            "版本 v0.1：首次形成本地 Golden Candidate；",
            "版本 v0.2：明确 AC-1 的最终可观察状态；",
        )

        advanced = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("mapped-changelog-result.json", result)
            ),
            "--requested-node", "review.parallel",
        )

        self.assertEqual(advanced["state"]["current_candidate_ref"]["version"], "v0.2")
        self.assertEqual(advanced["dispatch"]["node_id"], "review.parallel")

    def test_installed_optimize_rejects_missing_mapped_change_log_without_traceback(self) -> None:
        case = self._prepare_case(
            "missing-mapped-changelog",
            source_structure_mode="compact",
        )
        result = deepcopy(case["optimize_result"])
        output = result["semantic_output"]
        output["structure_mode"] = "compact"
        output["document_markdown"] = output["document_markdown"].replace(
            "## 附录 C：文档变更日志",
            "## 附录 C：修订记录",
        )
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        failed = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("missing-mapped-changelog-result.json", result)
            ),
            "--requested-node", "review.parallel",
        )

        self.assertIn(
            "template_mapping.document_changelog does not bind a required output heading",
            failed.stderr,
        )
        self.assertNotIn("IndexError", failed.stderr)
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]), state_before
        )

    def test_installed_optimize_can_localize_the_new_version_without_renaming_source(self) -> None:
        case = self._prepare_case("localized-title")
        result = case["optimize_result"]
        metadata = result["semantic_output"]["metadata"]
        source_path = case["archived"].document_path
        source_bytes = source_path.read_bytes()

        metadata["short_title"] = "结算失败后的安全恢复"
        metadata["document_language"] = "zh-CN"
        lines = result["semantic_output"]["document_markdown"].splitlines()
        localized_stem = prd_stem(
            metadata["prd_id"],
            metadata["short_title"],
            metadata["version"],
            metadata["date"],
        )
        lines[0] = f"# {localized_stem}"
        result["semantic_output"]["document_markdown"] = "\n".join(lines) + "\n"

        advanced = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("localized-optimize.json", result)),
            "--requested-node", "review.parallel",
        )

        self.assertEqual(advanced["status"], "ADVANCED")
        self.assertEqual(source_path.read_bytes(), source_bytes)
        current = advanced["state"]["current_candidate_ref"]
        self.assertIn(localized_stem, current["path"])

    def test_installed_optimize_recomputes_scope_and_rejects_forged_hash_without_side_effects(self) -> None:
        case = self._prepare_case("forged-scope")
        result = deepcopy(case["optimize_result"])
        result["semantic_output"]["metadata"]["active_scope_ref"]["scope_hash"] = (
            "sha256:" + "f" * 64
        )
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        failed = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("forged-scope.json", result)),
            "--requested-node", "review.parallel",
        )

        self.assertRegex(failed.stderr, "active_scope_ref|scope hash|scope_hash")
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]), state_before
        )

    def test_installed_optimize_routes_material_scope_change_before_candidate_write(self) -> None:
        case = self._prepare_case("material-scope")
        result = deepcopy(case["optimize_result"])
        result["semantic_output"]["proposed_scope_projection"]["user_outcome"] = (
            "a materially different user outcome"
        )
        result["semantic_output"]["scope_changed"] = False
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])
        candidate_paths_before = sorted(
            path.relative_to(self.project).as_posix()
            for path in (self.project / "artifacts" / "prds" / "archived").rglob("*")
        )

        routed = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("material-scope.json", result)),
            "--requested-node", "product.planning",
        )

        self.assertEqual(routed["status"], "PLAN_RECONCILE_REQUIRED")
        self.assertEqual(routed["route"]["to_node"], "product.planning")
        self.assertEqual(
            routed["route"]["exact_delta"][0]["field"], "user_outcome"
        )
        state_after = StateController(self.project, GRAPH).load_state(case["run_id"])
        self.assertEqual(state_after["current_node"], "product.planning")
        self.assertEqual(
            state_after["current_candidate_ref"], state_before["current_candidate_ref"]
        )
        self.assertEqual(
            sorted(
                path.relative_to(self.project).as_posix()
                for path in (self.project / "artifacts" / "prds" / "archived").rglob("*")
            ),
            candidate_paths_before,
        )

        repeated = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("material-scope.json", result)),
            "--requested-node", "product.planning",
        )
        self.assertEqual(repeated, routed)

        planning_dispatch = self._invoke(
            "--operation", "dispatch", "--run-id", case["run_id"]
        )["dispatch"]
        self.assertEqual(
            planning_dispatch["reconciliation_context"]["exact_delta"],
            routed["route"]["exact_delta"],
        )
        self.assertEqual(
            planning_dispatch["reconciliation_context"]["source_candidate_ref"],
            {
                key: state_before["current_candidate_ref"][key]
                for key in ("path", "hash", "version")
            },
        )

    def test_installed_reconciled_plan_regenerates_exact_vnext_and_clears_route(self) -> None:
        case = self._prepare_case("reconciled-generate")
        run_id = case["run_id"]
        material = deepcopy(case["optimize_result"])
        new_outcome = "enterprise operators can recover a failed settlement with audit visibility"
        material["semantic_output"]["proposed_scope_projection"]["user_outcome"] = new_outcome
        original_plan_path = self.project / case["refs"]["product_plan"]["path"]
        original_plan_hash = sha256_file(original_plan_path)
        original_candidate_hash = case["source_ref"]["hash"]

        routed = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._input_payload("reconciled-material.json", material)),
            "--requested-node", "product.planning",
        )
        planning_dispatch = self._invoke(
            "--operation", "dispatch", "--run-id", run_id
        )["dispatch"]
        self.assertEqual(
            planning_dispatch["reconciliation_context"]["exact_delta"],
            routed["route"]["exact_delta"],
        )

        plan = complete_plan()
        plan["decision_ref"] = case["refs"]["decision"]
        plan["prd_matrix"][0]["planned_prd_id"] = case["archived"].prd_id
        plan["slices"][0]["user_outcome"] = new_outcome
        plan_path = self.project / "product-plan-reconciled-generate-v2.md"
        plan_path.write_text(
            "# Reconciled Product Plan\n\n"
            "## Activated Slice\n\n"
            f"{new_outcome}. The stable PRD identity remains {case['archived'].prd_id}.\n",
            encoding="utf-8",
        )
        plan_ref = {
            "path": plan_path.relative_to(self.project).as_posix(),
            "hash": sha256_file(plan_path),
            "version": 2,
        }
        planning_result = {
            "schema_version": "node-result.v1",
            **{
                key: planning_dispatch[key]
                for key in (
                    "node_id", "attempt_id", "instruction_ref", "instruction_hash",
                    "input_refs", "input_hashes", "resource_refs",
                )
            },
            "producer": {"kind": "HOST_AGENT"},
            "semantic_output": plan,
            "artifact_refs": [{"role": "product_plan", **plan_ref}],
        }
        advanced = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._input_payload("reconciled-plan-result.json", planning_result)),
            "--requested-node", "plan.ready.gate",
        )
        generate_dispatch = advanced["dispatch"]
        self.assertEqual(generate_dispatch["node_id"], "prd.generate")
        context = generate_dispatch["reconciliation_context"]
        self.assertEqual(context["prd_id"], case["archived"].prd_id)
        self.assertEqual(context["next_version"], "v0.2")

        state = StateController(self.project, GRAPH).load_state(run_id)
        planning_node_refs = [
            item
            for item in state["artifact_refs"].values()
            if isinstance(item, dict)
            and item.get("role") == "node_result"
            and item.get("node_id") == "product.planning"
            and item.get("attempt_id") == planning_dispatch["attempt_id"]
        ]
        self.assertEqual(len(planning_node_refs), 1)
        slice_ref = {
            key: planning_node_refs[0][key] for key in ("path", "hash", "version")
        }
        source_metadata = read_json(
            case["archived"].document_path.with_suffix(".metadata.json")
        )
        metadata = {
            **source_metadata,
            "version": "v99",
            "product_plan_ref": plan_ref,
            "slice_ref": slice_ref,
            "active_scope_ref": derive_active_scope_ref(
                read_json(self.project / slice_ref["path"]),
                plan_ref,
                case["archived"].prd_id,
            ),
            "change_log": {
                "source_candidate_ref": context["source_candidate_ref"],
                "material_delta": ["Product Planning approved the exact material Slice change"],
            },
        }
        review_results = [
            item
            for item in state["artifact_refs"].values()
            if isinstance(item, dict)
            and item.get("role") == "node_result"
            and item.get("node_id") == "review.aggregate"
            and item.get("path") in generate_dispatch["input_refs"]
        ]
        self.assertEqual(len(review_results), 1)
        trace_pairs = [
            ("decision", case["refs"]["decision"]),
            ("roadmap", case["refs"]["roadmap"]),
            ("product_plan", plan_ref),
            ("slice", slice_ref),
            ("knowledge", case["refs"]["knowledge"]),
            ("evidence", case["refs"]["evidence"]),
            ("source_candidate", context["source_candidate_ref"]),
            ("review_aggregate_result", review_results[0]),
        ]
        metadata["spec_traceability"] = derive_spec_traceability(
            trace_pairs, state["artifact_refs"]
        )
        reconciled_markdown = case["source_markdown"].replace(
            "版本：v0.1", "版本：v99"
        ).replace(
            "v0.1 首次形成候选",
            "v99 records the exact Product Planning reconciliation",
        )
        reconciled_lines = reconciled_markdown.splitlines()
        reconciled_lines[0] = "# " + prd_stem(
            metadata["prd_id"],
            metadata["short_title"],
            metadata["version"],
            metadata["date"],
        )
        reconciled_markdown = "\n".join(reconciled_lines) + "\n"
        generated = {
            "schema_version": "node-result.v1",
            **{
                key: generate_dispatch[key]
                for key in (
                    "node_id", "attempt_id", "instruction_ref", "instruction_hash",
                    "input_refs", "input_hashes", "resource_refs",
                )
            },
            "producer": {"kind": "HOST_AGENT"},
            "semantic_output": {
                "document_markdown": reconciled_markdown,
                "template_mapping": source_metadata["template_mapping"],
                "metadata": metadata,
            },
            "artifact_refs": [],
        }
        before_invalid = self._inventory()
        state_before_invalid = StateController(self.project, GRAPH).load_state(run_id)
        rejected = self._invoke_error(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._input_payload("reconciled-invalid-version.json", generated)),
            "--requested-node", "review.parallel",
        )
        self.assertIn("exact next version", rejected.stderr)
        self.assertEqual(self._inventory(), before_invalid)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(run_id), state_before_invalid
        )

        generated["semantic_output"]["metadata"]["version"] = context["next_version"]
        generated["semantic_output"]["metadata"]["supersedes"] = context[
            "source_candidate_ref"
        ]
        generated["semantic_output"]["document_markdown"] = generated[
            "semantic_output"
        ]["document_markdown"].replace("v99", context["next_version"])
        accepted = self._invoke(
            "--operation", "submit", "--run-id", run_id,
            "--payload-file", str(self._input_payload("reconciled-valid-version.json", generated)),
            "--requested-node", "review.parallel",
        )
        final_state = accepted["state"]
        self.assertEqual(final_state["current_candidate_ref"]["version"], "v0.2")
        self.assertNotIn("scope_reconciliation", final_state)
        self.assertNotIn("planning_intent", final_state)
        self.assertEqual(sha256_file(original_plan_path), original_plan_hash)
        self.assertEqual(case["source_ref"]["hash"], original_candidate_hash)

    def test_installed_reconciled_plan_rejects_current_candidate_aliases_before_write(self) -> None:
        attacks = (
            "typed_alias",
            "nested_alias",
            "key_alias",
            "product_plan_role_swap",
            "plan_version_only",
            "plan_copy_same_bytes",
        )
        for attack in attacks:
            with self.subTest(attack=attack):
                case = self._prepare_case(f"plan-alias-{attack.replace('_', '-')}")
                run_id = case["run_id"]
                material = deepcopy(case["optimize_result"])
                new_outcome = f"material outcome for {attack}"
                material["semantic_output"]["proposed_scope_projection"][
                    "user_outcome"
                ] = new_outcome
                self._invoke(
                    "--operation", "submit", "--run-id", run_id,
                    "--payload-file", str(
                        self._input_payload(f"route-{attack}.json", material)
                    ),
                    "--requested-node", "product.planning",
                )
                dispatch = self._invoke(
                    "--operation", "dispatch", "--run-id", run_id
                )["dispatch"]
                plan = complete_plan()
                plan["decision_ref"] = case["refs"]["decision"]
                plan["prd_matrix"][0]["planned_prd_id"] = case["archived"].prd_id
                plan["slices"][0]["user_outcome"] = new_outcome
                candidate_identity = {
                    "path": case["source_ref"]["path"],
                    "hash": case["source_ref"]["hash"],
                }
                if attack == "typed_alias":
                    plan["baseline_spec_ref"] = {**candidate_identity, "version": 1}
                elif attack == "nested_alias":
                    plan["extensions"] = {"baseline": candidate_identity}
                elif attack == "key_alias":
                    plan["extensions"] = {case["source_ref"]["hash"]: "opaque"}
                plan_path = self.project / f"product-plan-{attack}-v2.md"
                plan_path.write_text(
                    f"# Reconciled Plan {attack}\n\n{new_outcome}.\n",
                    encoding="utf-8",
                )
                if attack == "plan_copy_same_bytes":
                    plan_path.write_bytes(
                        (self.project / case["refs"]["product_plan"]["path"]).read_bytes()
                    )
                plan_ref = {
                    "path": plan_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(plan_path),
                    "version": 2,
                }
                if attack == "product_plan_role_swap":
                    plan_ref = {**candidate_identity, "version": 2}
                elif attack == "plan_version_only":
                    plan_ref = {**case["refs"]["product_plan"], "version": 2}
                result = {
                    "schema_version": "node-result.v1",
                    **{
                        key: dispatch[key]
                        for key in (
                            "node_id", "attempt_id", "instruction_ref", "instruction_hash",
                            "input_refs", "input_hashes", "resource_refs",
                        )
                    },
                    "producer": {"kind": "HOST_AGENT"},
                    "semantic_output": plan,
                    "artifact_refs": [{"role": "product_plan", **plan_ref}],
                }
                before = self._inventory()
                state_before = StateController(self.project, GRAPH).load_state(run_id)

                rejected = self._invoke_error(
                    "--operation", "submit", "--run-id", run_id,
                    "--payload-file", str(
                        self._input_payload(f"candidate-alias-{attack}.json", result)
                    ),
                    "--requested-node", "plan.ready.gate",
                )

                self.assertIn(
                    (
                        "new Product Plan bytes"
                        if attack in {"plan_version_only", "plan_copy_same_bytes"}
                        else "current Candidate provenance"
                    ),
                    rejected.stderr,
                )
                self.assertEqual(self._inventory(), before)
                self.assertEqual(
                    StateController(self.project, GRAPH).load_state(run_id), state_before
                )

    def test_material_scope_route_rejects_runtime_leak_before_controller_write(self) -> None:
        case = self._prepare_case("material-runtime-leak")
        result = deepcopy(case["optimize_result"])
        result["semantic_output"]["proposed_scope_projection"]["user_outcome"] = (
            "a materially different user outcome"
        )
        result["semantic_output"]["metadata"]["product_runtime_inputs"]["required"].append(
            {
                "input_id": "laundered_candidate",
                "kind": "BUSINESS_INPUT",
                "resolver": "PROJECT_CONFIG",
                "binding_scope": "PROJECT",
                "version_policy": "business-input.v1",
                "on_missing": "FAIL_CLOSED",
                "configuration": {"alias": case["source_ref"]["hash"]},
            }
        )
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        rejected = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("material-runtime-leak.json", result)),
            "--requested-node", "product.planning",
        )

        self.assertIn("SPEC_REF_IN_RUNTIME_INPUTS", rejected.stderr)
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]), state_before
        )

    def test_installed_agent_instructions_expose_lifecycle_trace_roles(self) -> None:
        generate = (
            self.plugin / "skills" / "better-product-graph" / "references"
            / "atomic-skills" / "prd-generate" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")
        review = (
            self.plugin / "skills" / "better-product-graph" / "references"
            / "atomic-skills" / "prd-review" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")
        planning = (
            self.plugin / "skills" / "better-product-graph" / "references"
            / "atomic-skills" / "product-planning" / "INSTRUCTIONS.md"
        ).read_text(encoding="utf-8")

        for role in ("problem_ready", "source_candidate", "review_aggregate_result"):
            self.assertIn(role, generate)
        for role in ("source_candidate", "review_aggregate_result"):
            self.assertIn(role, review)
        self.assertIn("reconciliation_context", planning)

    def test_installed_optimize_treats_unmapped_scope_fields_as_ambiguous(self) -> None:
        case = self._prepare_case("ambiguous-scope")
        result = deepcopy(case["optimize_result"])
        result["semantic_output"]["proposed_scope_projection"][
            "unmapped_scope_delta"
        ] = {"new_audience": "enterprise"}
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        failed = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("ambiguous-scope.json", result)),
            "--requested-node", "review.parallel",
        )

        self.assertIn("AMBIGUOUS_SCOPE_CHANGE", failed.stderr)
        self.assertIn("unmapped_scope_delta", failed.stderr)
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]), state_before
        )

    def test_installed_optimize_rejects_nested_spec_ref_in_runtime_inputs_before_write(self) -> None:
        case = self._prepare_case("runtime-leak")
        result = deepcopy(case["optimize_result"])
        metadata = result["semantic_output"]["metadata"]
        metadata["product_runtime_inputs"]["required"].append(
            {
                "input_id": "renamed_product_input",
                "kind": "BUSINESS_INPUT",
                "resolver": "PROJECT_CONFIG",
                "binding_scope": "PROJECT",
                "version_policy": "business-input.v1",
                "on_missing": "FAIL_CLOSED",
                "configuration": {
                    "alias": {
                        "source": metadata["spec_traceability"]["refs"][0]["path"]
                    }
                },
            }
        )
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        failed = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("runtime-leak.json", result)),
            "--requested-node", "review.parallel",
        )

        self.assertIn("SPEC_REF_IN_RUNTIME_INPUTS", failed.stderr)
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]), state_before
        )

    def test_installed_optimize_rejects_committed_receipt_hash_alias_before_write(self) -> None:
        case = self._prepare_case("receipt-hash-leak")
        result = deepcopy(case["optimize_result"])
        state = StateController(self.project, GRAPH).load_state(case["run_id"])
        aggregate_results = [
            item
            for item in state["artifact_refs"].values()
            if isinstance(item, dict)
            and item.get("role") == "node_result"
            and item.get("node_id") == "review.aggregate"
        ]
        self.assertEqual(len(aggregate_results), 1)
        receipt_path = (
            self.project / aggregate_results[0]["path"]
        ).with_name("result-receipt.json")
        self.assertTrue(receipt_path.is_file())
        receipt_hash = sha256_file(receipt_path)
        result["semantic_output"]["metadata"]["product_runtime_inputs"]["required"].append(
            {
                "input_id": "opaque_seed",
                "kind": "BUSINESS_INPUT",
                "resolver": "PROJECT_CONFIG",
                "binding_scope": "PROJECT",
                "version_policy": "business-input.v1",
                "on_missing": "FAIL_CLOSED",
                "configuration": {"opaque_seed": receipt_hash},
            }
        )
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        rejected = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(self._input_payload("receipt-hash-leak.json", result)),
            "--requested-node", "review.parallel",
        )

        self.assertIn("SPEC_REF_IN_RUNTIME_INPUTS", rejected.stderr)
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]), state_before
        )

    def test_installed_optimize_rejects_laundered_source_candidate_hash_before_write(self) -> None:
        for identity_field in ("hash", "tree_hash", "review_hash", "active_scope_hash"):
            with self.subTest(identity_field=identity_field):
                case = self._prepare_case(
                    f"runtime-identity-{identity_field.replace('_', '-')}"
                )
                result = deepcopy(case["optimize_result"])
                metadata = result["semantic_output"]["metadata"]
                leaked = (
                    metadata["active_scope_ref"]["scope_hash"]
                    if identity_field == "active_scope_hash"
                    else case["source_ref"][identity_field]
                )
                metadata["product_runtime_inputs"]["required"].append(
                    {
                        "input_id": "portable_seed",
                        "kind": "BUSINESS_INPUT",
                        "resolver": "PROJECT_CONFIG",
                        "binding_scope": "PROJECT",
                        "version_policy": "business-input.v1",
                        "on_missing": "FAIL_CLOSED",
                        "configuration": {"opaque_seed": leaked},
                    }
                )
                before = self._inventory()
                state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

                failed = self._invoke_error(
                    "--operation", "submit", "--run-id", case["run_id"],
                    "--payload-file", str(
                        self._input_payload(
                            f"runtime-identity-{identity_field}.json", result
                        )
                    ),
                    "--requested-node", "review.parallel",
                )

                self.assertIn("SPEC_REF_IN_RUNTIME_INPUTS", failed.stderr)
                self.assertEqual(self._inventory(), before)
                self.assertEqual(
                    StateController(self.project, GRAPH).load_state(case["run_id"]),
                    state_before,
                )

    def test_installed_optimize_rejects_stale_version_unclosed_and_metadata_tamper_without_side_effects(self) -> None:
        mutations = {
            "stale": lambda result: result["semantic_output"]["source_candidate_ref"].update(
                {"hash": "sha256:" + "0" * 64}
            ),
            "version": lambda result: (
                result["semantic_output"]["metadata"].update({"version": "v0.3"}),
                result["semantic_output"]["candidate_ref"].update({"version": "v0.3"}),
            ),
            "path": lambda result: result["semantic_output"]["source_candidate_ref"].update(
                {"path": "../outside-candidate.md"}
            ),
            "unclosed": lambda result: result["semantic_output"]["metadata"]["change_log"].update(
                {"repaired_finding_ids": []}
            ),
            "unknown_change_log_field": lambda result: result["semantic_output"]["metadata"]["change_log"].update(
                {"private_closure_claim": True}
            ),
            "metadata": lambda result: result["semantic_output"]["metadata"].update(
                {"prd_id": "PRD-TAMPERED"}
            ),
            "traceability": lambda result: result["semantic_output"]["metadata"][
                "spec_traceability"
            ]["refs"][0].update({"origin_attempt_id": "attempt-forged-origin"}),
            "evals": lambda result: result["semantic_output"]["metadata"].update(
                {
                    "evals": {
                        "applicability": "REQUIRED",
                        "fulfillment": "REVIEWED",
                        "pack_ref": {
                            "path": "unbound-eval-pack.json",
                            "hash": "sha256:" + "1" * 64,
                            "version": 1,
                        },
                        "ground_truth_provenance": "invented by optimizer",
                    }
                }
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                case = self._prepare_case(label)
                result = deepcopy(case["optimize_result"])
                mutate(result)
                before = self._inventory()
                state_before = StateController(self.project, GRAPH).load_state(case["run_id"])
                failed = self._invoke_error(
                    "--operation", "submit", "--run-id", case["run_id"],
                    "--payload-file", str(self._input_payload(f"invalid-{label}.json", result)),
                    "--requested-node", "review.parallel",
                )
                self.assertRegex(
                    failed.stderr,
                    "stale|version|change_log|changelog|identity|authority|traceability|Evals|Candidate|Product Plan|prd_matrix",
                )
                if label == "unclosed":
                    self.assertIn("metadata.change_log.repaired_finding_ids", failed.stderr)
                if label == "unknown_change_log_field":
                    self.assertIn(
                        "metadata.change_log contains unknown field private_closure_claim",
                        failed.stderr,
                    )
                self.assertEqual(self._inventory(), before)
                self.assertEqual(
                    StateController(self.project, GRAPH).load_state(case["run_id"]),
                    state_before,
                )

    def test_installed_optimize_rejects_dispatched_prd_and_aggregate_masquerading_as_reviewed_evals(self) -> None:
        case = self._prepare_case("forged-reviewed-evals")
        result = deepcopy(case["optimize_result"])
        aggregate_ref = case["optimize_dispatch"]["optimize_context"]["aggregate_ref"]
        result["semantic_output"]["metadata"]["evals"] = {
            "applicability": "REQUIRED",
            "fulfillment": "REVIEWED",
            "execution_status": "PASSED",
            "pack_ref": {
                key: case["source_ref"][key]
                for key in ("path", "hash", "version")
            },
            "review_ref": aggregate_ref,
            "ground_truth_provenance": "invented by optimizer",
        }
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        failed = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("forged-reviewed-evals-result.json", result)
            ),
            "--requested-node", "review.parallel",
        )

        self.assertRegex(failed.stderr, "Eval|role|schema|provenance|NOT_RUN")
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]),
            state_before,
        )

    def test_installed_optimize_keeps_required_evals_pending_for_future_independent_review(self) -> None:
        case = self._prepare_case("required-evals-pending")
        result = deepcopy(case["optimize_result"])
        result["semantic_output"]["metadata"]["evals"] = {
            "applicability": "REQUIRED",
            "fulfillment": "REVIEW_PENDING",
            "execution_status": "NOT_RUN",
            "reason": "the optimized Candidate requires a new independent Eval Pack review",
        }

        advanced = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("required-evals-pending-result.json", result)
            ),
            "--requested-node", "review.parallel",
        )

        current = advanced["state"]["current_candidate_ref"]
        metadata_path = (self.project / current["path"]).with_suffix(".metadata.json")
        self.assertEqual(
            read_json(metadata_path)["evals"],
            result["semantic_output"]["metadata"]["evals"],
        )
        self.assertEqual(advanced["dispatch"]["node_id"], "review.parallel")
        self.assertEqual(advanced["state"]["status"], "ACTIVE")
        self.assertFalse((self.project / "artifacts" / "prds" / "released").exists())

    def test_installed_v06_accepted_repair_rereviews_and_releases_with_no_disagreement(self) -> None:
        case = self._prepare_case(
            "v06-lifecycle",
            source_version="v0.5",
            next_version="v0.6",
            authoritative_upstreams=True,
        )
        advanced = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("optimize-result-v06.json", case["optimize_result"])
            ),
            "--requested-node", "review.parallel",
        )
        review_dispatch = advanced["dispatch"]
        candidate = advanced["state"]["current_candidate_ref"]
        candidate_identity = {
            key: candidate[key] for key in ("path", "hash", "version")
        }
        self.assertEqual(candidate["version"], "v0.6")
        resources = {
            item["resource_id"]: item for item in review_dispatch["resource_refs"]
        }

        def exact(resource_id: str) -> dict:
            return {
                key: resources[resource_id][key]
                for key in ("path", "hash", "version")
            }

        decision_ref = case["refs"]["decision"]
        verified_finding = {
            "finding_id": "finding-v06-repair-verified",
            "topic_id": "acceptance-recovery",
            "stance": "repair-verified",
            "concern": "the accepted recovery repair is now explicit",
            "concern_level": "INFORMATIONAL",
            "basis_refs": [candidate["path"], decision_ref["path"]],
            "affected_scope": ["验收标准"],
            "possible_impact": "the implementation team can verify the final state",
            "professional_recommendation": "retain the repaired acceptance boundary",
            "repair_target": "NONE",
            "confidence": "high",
            "confidence_basis": "exact revised Candidate and Decision",
        }
        review_result = {
            "schema_version": "node-result.v1",
            "node_id": "review.parallel",
            "attempt_id": review_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": review_dispatch["instruction_ref"],
            "instruction_hash": review_dispatch["instruction_hash"],
            "input_refs": review_dispatch["input_refs"],
            "input_hashes": review_dispatch["input_hashes"],
            "resource_refs": review_dispatch["resource_refs"],
            "semantic_output": {
                "candidate_ref": candidate_identity,
                "reviewer_role": "combined-advisory-rereview",
                "reviewer_profile": "product-goal-fidelity-v0.1",
                "roles_covered": ["product", "engineering_feasibility", "testability"],
                "authority": "ADVISORY_ONLY",
                "goal_fidelity_refs": {
                    "profile_ref": exact("goal-fidelity-profile"),
                    "rubric_ref": exact("goal-fidelity-rubric"),
                    "packet_contract_ref": exact("goal-fidelity-packet-contract"),
                    "commitment_refs": [decision_ref],
                },
                "goal_fidelity_packet": {
                    "goal": "verify the accepted v0.6 repair without inventing new scope",
                    "candidate_ref": candidate_identity,
                    "commitment_refs": [decision_ref],
                },
                "findings": [verified_finding],
            },
            "artifact_refs": [],
        }
        writing_ref = attach_zero_finding_writing_coverage(
            self.project, review_dispatch, review_result
        )
        aggregate_dispatch = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("rereview-result-v06.json", review_result)
            ),
            "--requested-node", "review.aggregate",
        )["dispatch"]
        aggregate = {
            "schema_version": "review-aggregate.v1",
            "authority": "ADVISORY_ONLY",
            "candidate_ref": candidate_identity,
            "attempts": [
                {
                    "attempt_id": review_dispatch["attempt_id"],
                    "status": "COMPLETED",
                    "roles_covered": ["product", "engineering_feasibility", "testability"],
                }
            ],
            "findings": [verified_finding],
            "disagreements": [],
            "writing_coverage_ref": writing_ref,
        }
        dispositions = {
            "schema_version": "review-dispositions.v1",
            "candidate_hash": candidate["hash"],
            "candidate_version": candidate["version"],
            "dispositions": [
                {
                    "finding_id": verified_finding["finding_id"],
                    "status": "ADDRESSED",
                }
            ],
        }
        aggregate_path = self._payload("rereview-aggregate-v06.json", aggregate)
        dispositions_path = self._payload("rereview-dispositions-v06.json", dispositions)
        aggregate_result = {
            "schema_version": "node-result.v1",
            "node_id": "review.aggregate",
            "attempt_id": aggregate_dispatch["attempt_id"],
            "producer": {"kind": "HOST_AGENT"},
            "instruction_ref": aggregate_dispatch["instruction_ref"],
            "instruction_hash": aggregate_dispatch["instruction_hash"],
            "input_refs": aggregate_dispatch["input_refs"],
            "input_hashes": aggregate_dispatch["input_hashes"],
            "resource_refs": aggregate_dispatch["resource_refs"],
            "semantic_output": {
                **aggregate,
                "dispositions": dispositions["dispositions"],
            },
            "artifact_refs": [
                {
                    "role": "review_aggregate",
                    "path": aggregate_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(aggregate_path),
                    "version": 1,
                },
                {
                    "role": "review_dispositions",
                    "path": dispositions_path.relative_to(self.project).as_posix(),
                    "hash": sha256_file(dispositions_path),
                    "version": 1,
                },
            ],
        }
        completed = self._invoke(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("rereview-aggregate-result-v06.json", aggregate_result)
            ),
            "--requested-node", "review.finalize",
        )

        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["state"]["current_node"], "handoff.dispatch")
        self.assertTrue(
            (
                self.project
                / "artifacts"
                / "prds"
                / "released"
                / Path(candidate["artifact_path"]).name
            ).is_dir()
        )

    def test_installed_optimize_cannot_downgrade_required_evals_applicability(self) -> None:
        case = self._prepare_case(
            "required-evals-no-downgrade",
            source_evals={
                "applicability": "REQUIRED",
                "fulfillment": "REVIEW_PENDING",
                "execution_status": "NOT_RUN",
                "reason": "independent Eval fulfillment is not available yet",
            },
        )
        result = deepcopy(case["optimize_result"])
        before = self._inventory()
        state_before = StateController(self.project, GRAPH).load_state(case["run_id"])

        failed = self._invoke_error(
            "--operation", "submit", "--run-id", case["run_id"],
            "--payload-file", str(
                self._input_payload("required-evals-downgrade-result.json", result)
            ),
            "--requested-node", "review.parallel",
        )

        self.assertIn("cannot downgrade REQUIRED Evals", failed.stderr)
        self.assertEqual(self._inventory(), before)
        self.assertEqual(
            StateController(self.project, GRAPH).load_state(case["run_id"]),
            state_before,
        )

    def test_optimize_recovers_exactly_once_across_archive_result_and_transition_crashes(self) -> None:
        installed_skill = self.plugin / "skills" / "better-product-graph"
        installed_graph = installed_skill / "references" / "graph" / "manifest.json"
        for phase in (
            "after_archive_publish",
            "after_result_persist",
            "before_transition",
            "after_transition",
        ):
            with self.subTest(phase=phase):
                label = phase.replace("_", "-")
                case = self._prepare_case(label)
                runtime = HostRuntime(self.project, installed_graph, installed_skill)
                with self.assertRaises(InjectedCrash):
                    runtime.submit_and_advance(
                        case["run_id"],
                        deepcopy(case["optimize_result"]),
                        requested_node="review.parallel",
                        failpoint=crash_at(phase),
                    )
                recovered = runtime.submit_and_advance(
                    case["run_id"],
                    deepcopy(case["optimize_result"]),
                    requested_node="review.parallel",
                )
                current = recovered["state"]["current_candidate_ref"]
                self.assertEqual(current["version"], "v0.2")
                self.assertEqual(recovered["dispatch"]["node_id"], "review.parallel")
                self.assertEqual(
                    recovered["dispatch"]["input_hashes"][current["path"]],
                    current["hash"],
                )
                archived_matches = list(
                    (self.project / "artifacts" / "prds" / "archived").glob(
                        f"{case['archived'].prd_id}_{case['archived'].short_title}_v0.2_*"
                    )
                )
                self.assertEqual(len(archived_matches), 1)


if __name__ == "__main__":
    unittest.main()
