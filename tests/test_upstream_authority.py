from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.host_runtime import HostRuntime
from src.bpg.storage import atomic_write_json, canonical_json_bytes, sha256_bytes, sha256_file
from src.bpg.upstream_authority import validate_ready_evidence
from tests.controller_fixtures import position_run_internal


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class UpstreamAuthorityTests(unittest.TestCase):
    def test_problem_learning_loop_can_commit_authoritative_later_round_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            runtime = HostRuntime(project, GRAPH, REPO_ROOT / "src" / "core")
            run_id = "run-learning-evidence"
            runtime.controller.create_run(run_id, raw_signal="later learning evidence")
            position_run_internal(
                runtime.controller,
                run_id,
                "problem.learning.loop",
                ["problem.synthesize"],
            )
            dispatch = runtime.dispatch_current(run_id)
            content = {"summary": "New interview evidence changed the active unknown"}
            evidence = {
                "schema_version": "evidence-record.v1",
                "kind": "evidence",
                "version": 2,
                "run_id": run_id,
                "status": "RECORDED",
                "authorized": True,
                "received_at": "2026-08-20T09:30:00+08:00",
                "source": {"kind": "PM_INTERVIEW"},
                "producer": {
                    "node_id": "problem.learning.loop",
                    "attempt_id": dispatch["attempt_id"],
                },
                "content": content,
                "content_hash": sha256_bytes(canonical_json_bytes(content)),
            }
            evidence_path = project / "learning-evidence-v2.json"
            atomic_write_json(evidence_path, evidence)
            evidence_ref = {
                "path": evidence_path.relative_to(project).as_posix(),
                "hash": sha256_file(evidence_path),
                "version": 2,
            }
            result = {
                "schema_version": "node-result.v1",
                "node_id": "problem.learning.loop",
                "attempt_id": dispatch["attempt_id"],
                "producer": {"kind": "HOST_AGENT"},
                "instruction_ref": dispatch["instruction_ref"],
                "instruction_hash": dispatch["instruction_hash"],
                "input_refs": dispatch["input_refs"],
                "input_hashes": dispatch["input_hashes"],
                "resource_refs": dispatch["resource_refs"],
                "semantic_output": {
                    "learning_disposition": "READY_FOR_SYNTHESIS",
                    "runtime_status": "COMPLETED",
                    "interaction_policy": "ALLOW_PM_INTERVIEW",
                    "next_actions": [],
                    "material_challenges": [],
                    "reasoning_usage": {
                        "used_resource_ids": ["better-question"],
                        "selection_rationale": "The interview resolved the current MVU.",
                    },
                },
                "artifact_refs": [{"role": "evidence", **evidence_ref}],
            }

            runtime.submit_and_advance(
                run_id,
                result,
                requested_node="problem.synthesize",
            )

            validate_ready_evidence(project, run_id, evidence_ref, evidence)


if __name__ == "__main__":
    unittest.main()
