from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aggregate_prd_readability_release import aggregate_release_phases


REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE_ROOT = REPO_ROOT / "evals" / "prd-readability-v0.8"
SUITE_ID = "better-product-graph-prd-readability-v0.8"
PHASES = ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT")


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def exact_ref(root: Path, path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": digest(path.read_bytes()),
        "version": 1,
    }


def phase_score(phase: str) -> dict[str, object]:
    return {
        "schema_version": "prd-readability-v0.8-phase-score.v1",
        "suite_id": SUITE_ID,
        "phase": phase,
        "status": "PASS",
        "selection_policy": "ALL_PRODUCED_ATTEMPTS_OCCUPY_DENOMINATOR_NO_BEST_OF_N_NO_REPLACEMENT",
        "score": {"passed": 27, "total": 27, "required": 27},
        "produced_output_count": 27,
        "installed_build_ref": {
            "path": "build-manifest.json",
            "hash": "sha256:" + ("a" if phase == PHASES[0] else "b") * 64,
            "version": "0.2.18-rc.5" if phase == PHASES[0] else "0.2.18",
        },
        "issues": [],
        "attempts": [],
        "agent_runtime_status": "COMPLETED",
        "human_reader_validation": "NOT_RUN",
    }


def build_phase(root: Path, phase: str) -> tuple[dict, dict, dict]:
    root.mkdir(parents=True)
    root_stat = root.stat()
    root_identity = {
        "path": str(root.resolve()),
        "device": root_stat.st_dev,
        "inode": root_stat.st_ino,
    }
    phase_prefix = "rc" if phase == PHASES[0] else "final"
    build_ref = phase_score(phase)["installed_build_ref"]
    entries = []
    result_attempts = []
    for ordinal in range(1, 28):
        work_order = root / "work-orders" / f"{ordinal:03d}.json"
        write_json(
            work_order,
            {"phase": phase, "ordinal": ordinal, "identity": phase_prefix},
        )
        entry = {
            "ordinal": ordinal,
            "suite_id": SUITE_ID,
            "phase": phase,
            "semantic_case_id": f"case-{((ordinal - 1) // 3) + 1:03d}",
            "agent_case_id": f"case-{((ordinal - 1) // 3) + 1:03d}",
            "repeat_index": ((ordinal - 1) % 3) + 1,
            "run_id": f"{phase_prefix}-run-{ordinal:03d}",
            "attempt_id": f"{phase_prefix}-attempt-{ordinal:03d}",
            "reviewer_execution_ref": {
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": f"{phase_prefix}-reviewer-{ordinal:03d}",
            },
            "author_execution_ref": {
                "kind": "HOST_AGENT_ATTEMPT",
                "id": f"{phase_prefix}-author-{ordinal:03d}",
            },
            "preregistration_checkpoint_ref": {
                "path": f"checkpoints/{phase_prefix}-{ordinal:03d}.json",
                "hash": "sha256:" + f"{ordinal + (100 if phase_prefix == 'rc' else 200):064x}",
                "version": 1,
            },
            "work_order_ref": exact_ref(root, work_order),
            "output_target": f"raw/{phase_prefix}/{ordinal:03d}.json",
            "central_project_root": root_identity,
            "state_ref": {
                "path": f"state/{phase_prefix}-{ordinal:03d}.json",
                "hash": "sha256:" + f"{ordinal + (300 if phase_prefix == 'rc' else 400):064x}",
                "version": 2,
            },
            "installed_build_ref": build_ref,
        }
        entries.append(entry)
        result_attempts.append(
            {
                "ordinal": ordinal,
                "run_id": entry["run_id"],
                "attempt_id": entry["attempt_id"],
                "result_ref": {
                    "path": f"results/{phase_prefix}-{ordinal:03d}.json",
                    "hash": "sha256:" + f"{ordinal + (500 if phase_prefix == 'rc' else 600):064x}",
                    "version": 1,
                },
            }
        )
    manifest = {
        "schema_version": "prd-readability-v0.8-execution-manifest.v1",
        "status": "FROZEN_BEFORE_AGENT_OUTPUT",
        "suite_id": SUITE_ID,
        "phase": phase,
        "central_project_root": root_identity,
        "installed_build_ref": build_ref,
        "required_attempt_count": 27,
        "result_ref_null_count_at_freeze": 27,
        "agent_output_count_at_freeze": 0,
        "entries": entries,
    }
    manifest_path = (
        root
        / ".better-product-graph"
        / "writing-evals"
        / "execution-manifests"
        / f"{phase}.json"
    )
    write_json(manifest_path, manifest)
    receipt = {"execution_manifest_ref": exact_ref(root, manifest_path)}
    controller_invocation = {
        "invocation": {
            "evidence_snapshot": {
                "schema_version": "prd-readability-v0.8-score-evidence-snapshot.v1",
                "suite_id": SUITE_ID,
                "phase": phase,
                "attempts": result_attempts,
            }
        }
    }
    return manifest, receipt, controller_invocation


class FakeFrozenScorer:
    def __init__(self, bundles: dict[str, tuple]) -> None:
        self.bundles = bundles
        self.load_calls: list[tuple[str, str]] = []
        self.score_phase_calls = 0

    def namespace(self) -> dict[str, object]:
        def load_terminal(root: Path, _skill: Path, phase: str) -> dict:
            self.load_calls.append((phase, str(Path(root).resolve())))
            return self.bundles[phase][0]

        def load_bundle(_root: Path, phase: str) -> tuple:
            return self.bundles[phase]

        def score_phase(*_args: object, **_kwargs: object) -> None:
            self.score_phase_calls += 1
            raise AssertionError("release aggregation must never invoke phase scoring")

        return {
            "_load_terminal_score": load_terminal,
            "_phase_score_bundle": load_bundle,
            "score_phase": score_phase,
        }


class MultiRootReleaseAggregationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.roots = {
            PHASES[0]: base / "rc-root",
            PHASES[1]: base / "final-root",
        }
        self.skills = {
            phase: base / f"{phase.lower()}-skill" for phase in PHASES
        }
        self.bundles = {}
        self.manifests = {}
        for phase in PHASES:
            self.skills[phase].mkdir(parents=True)
            manifest, receipt, invocation = build_phase(self.roots[phase], phase)
            score = phase_score(phase)
            self.manifests[phase] = manifest
            self.bundles[phase] = (score, receipt, invocation, {}, {})
        self.scorer = FakeFrozenScorer(self.bundles)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def bindings(self) -> dict[str, dict[str, Path]]:
        return {
            phase: {
                "central_project_root": self.roots[phase],
                "skill_root": self.skills[phase],
            }
            for phase in PHASES
        }

    def aggregate(self) -> dict:
        return aggregate_release_phases(
            self.bindings(),
            suite_root=SUITE_ROOT,
            _scorer=self.scorer.namespace(),
        )

    def test_same_relative_work_order_names_in_distinct_roots_are_not_reuse(self) -> None:
        before = {
            phase: (
                self.roots[phase]
                / ".better-product-graph/writing-evals/execution-manifests"
                / f"{phase}.json"
            ).read_bytes()
            for phase in PHASES
        }

        result = self.aggregate()

        self.assertEqual(result["release_score"]["status"], "PASS")
        self.assertEqual(result["release_score"]["issues"], [])
        self.assertEqual(result["evidence"]["identity_overlap_counts"], {
            "run_id": 0,
            "attempt_id": 0,
            "reviewer_id": 0,
            "author_id": 0,
            "output_target": 0,
            "checkpoint_path": 0,
            "state_path": 0,
            "result_hash": 0,
            "work_order_identity": 0,
        })
        identities = result["evidence"]["work_order_identities"]
        self.assertEqual(len(identities), 54)
        self.assertEqual(len({item["identity_hash"] for item in identities}), 54)
        self.assertTrue(all(item["link_count"] == 1 for item in identities))
        self.assertEqual([call[0] for call in self.scorer.load_calls], list(PHASES))
        self.assertEqual(self.scorer.score_phase_calls, 0)
        for phase in PHASES:
            path = (
                self.roots[phase]
                / ".better-product-graph/writing-evals/execution-manifests"
                / f"{phase}.json"
            )
            self.assertEqual(path.read_bytes(), before[phase])

    def test_work_order_must_be_root_contained_regular_single_link_and_hash_matched(self) -> None:
        cases = ("escape", "symlink", "hardlink", "hash")
        for case in cases:
            with self.subTest(case=case):
                try:
                    entry = self.manifests[PHASES[1]]["entries"][0]
                    work_order = self.roots[PHASES[1]] / entry["work_order_ref"]["path"]
                    if case == "escape":
                        entry["work_order_ref"]["path"] = "../outside.json"
                        final_path = (
                            self.roots[PHASES[1]]
                            / ".better-product-graph/writing-evals/execution-manifests"
                            / f"{PHASES[1]}.json"
                        )
                        write_json(final_path, self.manifests[PHASES[1]])
                        self.bundles[PHASES[1]][1]["execution_manifest_ref"] = exact_ref(
                            self.roots[PHASES[1]], final_path
                        )
                        expected = "work_order_ref:path|root-relative"
                    elif case == "symlink":
                        original = work_order.with_name("original.json")
                        work_order.replace(original)
                        work_order.symlink_to(original)
                        expected = "symlink"
                    elif case == "hardlink":
                        os.link(work_order, work_order.with_name("second-link.json"))
                        expected = "single-link"
                    else:
                        work_order.write_text('{"tampered":true}\n', encoding="utf-8")
                        expected = "hash"
                    with self.assertRaisesRegex(ValueError, expected):
                        self.aggregate()
                finally:
                    self.tearDown()
                    self.setUp()

    def test_every_non_work_order_cross_phase_identity_remains_strict(self) -> None:
        mutations = {
            "run_id": lambda rc, final: final.__setitem__("run_id", rc["run_id"]),
            "attempt_id": lambda rc, final: final.__setitem__("attempt_id", rc["attempt_id"]),
            "reviewer_id": lambda rc, final: final["reviewer_execution_ref"].__setitem__("id", rc["reviewer_execution_ref"]["id"]),
            "author_id": lambda rc, final: final["author_execution_ref"].__setitem__("id", rc["author_execution_ref"]["id"]),
            "output_target": lambda rc, final: final.__setitem__("output_target", rc["output_target"]),
            "checkpoint_path": lambda rc, final: final["preregistration_checkpoint_ref"].__setitem__("path", rc["preregistration_checkpoint_ref"]["path"]),
            "state_path": lambda rc, final: final["state_ref"].__setitem__("path", rc["state_ref"]["path"]),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                mutate(
                    self.manifests[PHASES[0]]["entries"][0],
                    self.manifests[PHASES[1]]["entries"][0],
                )
                final_path = (
                    self.roots[PHASES[1]]
                    / ".better-product-graph/writing-evals/execution-manifests"
                    / f"{PHASES[1]}.json"
                )
                write_json(final_path, self.manifests[PHASES[1]])
                self.bundles[PHASES[1]][1]["execution_manifest_ref"] = exact_ref(
                    self.roots[PHASES[1]], final_path
                )
                result = self.aggregate()
                self.assertEqual(result["release_score"]["status"], "FAIL")
                self.assertGreater(result["evidence"]["identity_overlap_counts"][label], 0)
                self.tearDown()
                self.setUp()

        self.bundles[PHASES[1]][2]["invocation"]["evidence_snapshot"]["attempts"][0]["result_ref"]["hash"] = (
            self.bundles[PHASES[0]][2]["invocation"]["evidence_snapshot"]["attempts"][0]["result_ref"]["hash"]
        )
        result = self.aggregate()
        self.assertEqual(result["release_score"]["status"], "FAIL")
        self.assertEqual(result["evidence"]["identity_overlap_counts"]["result_hash"], 1)

    def test_evidence_binds_exact_repository_aggregator_hash(self) -> None:
        result = self.aggregate()
        ref = result["evidence"]["aggregator_ref"]
        path = REPO_ROOT / ref["path"]
        self.assertEqual(ref["hash"], digest(path.read_bytes()))
        self.assertEqual(ref["version"], 1)
        self.assertEqual(result, self.aggregate())

    def test_cli_exposes_both_exact_phase_roots_and_skill_roots(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/aggregate_prd_readability_release.py"),
                "--help",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        for flag in (
            "--rc-project-root",
            "--rc-skill-root",
            "--final-project-root",
            "--final-skill-root",
            "--output-dir",
        ):
            self.assertIn(flag, completed.stdout)


if __name__ == "__main__":
    unittest.main()
