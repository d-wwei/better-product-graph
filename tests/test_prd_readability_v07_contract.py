from __future__ import annotations

import hashlib
import json
import runpy
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.build_plugin import build_plugin
from src.bpg.storage import atomic_write_json, sha256_file
from src.bpg.writing_eval import WritingEvalError, WritingEvalRuntime
from tests.test_writing_eval_runtime import passing_review


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "evals" / "prd-readability-v0.7"
SUITE_ID = "better-product-graph-prd-readability-v0.7"
TREE_HASH = "sha256:26d3d4895de069d698eb4645beb40d4e464e1f08b34615c175fde03c076df83f"
PHASES = ("RC_CANDIDATE", "FINAL_PUBLIC_ARTIFACT")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def replay_manifest_binding_before_dispatch(
    project: Path, entry: dict
) -> None:
    """Coherently replay bind at v2 and dispatch at v3 without changing state_ref."""

    run_root = (
        project / ".better-product-graph" / "writing-evals" / entry["run_id"]
    )
    transactions_root = run_root / "transactions"
    dispatch_path = next(transactions_root.glob("dispatch-*.json"))
    bind_path = next(transactions_root.glob("bind_manifest-*.json"))
    dispatch = json.loads(dispatch_path.read_text(encoding="utf-8"))
    binding = json.loads(bind_path.read_text(encoding="utf-8"))
    events_path = run_root / "events.jsonl"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
    ]
    prepare_event = events[0]
    attempt_id = entry["attempt_id"]
    base_state = dispatch["base_state"]
    rebound_state = json.loads(json.dumps(base_state))
    rebound_state["phase_manifest_binding"] = binding["target_state"][
        "phase_manifest_binding"
    ]
    rebound_state["state_version"] = 2

    bind_transition_id = f"bind_manifest-{attempt_id}-v2"
    bind_event = json.loads(json.dumps(binding["target_event"]))
    bind_event["event_id"] = f"writing-eval-transition-{bind_transition_id}"
    bind_event["previous_hash"] = prepare_event["event_hash"]
    bind_event["event_hash"] = sha256_bytes(
        canonical_bytes(
            {key: value for key, value in bind_event.items() if key != "event_hash"}
        )
    )
    rebound = {
        **binding,
        "transition_id": bind_transition_id,
        "base_state_hash": sha256_bytes(canonical_bytes(base_state)),
        "base_state": base_state,
        "target_state": rebound_state,
        "target_state_hash": sha256_bytes(canonical_bytes(rebound_state)),
        "base_event_head": prepare_event["event_hash"],
        "target_event": bind_event,
        "target_event_hash": bind_event["event_hash"],
    }

    dispatch_transition_id = f"dispatch-{attempt_id}-v3"
    dispatch_event = json.loads(json.dumps(dispatch["target_event"]))
    dispatch_event["event_id"] = (
        f"writing-eval-transition-{dispatch_transition_id}"
    )
    dispatch_event["previous_hash"] = bind_event["event_hash"]
    dispatch_event["event_hash"] = sha256_bytes(
        canonical_bytes(
            {
                key: value
                for key, value in dispatch_event.items()
                if key != "event_hash"
            }
        )
    )
    redispatch = {
        **dispatch,
        "transition_id": dispatch_transition_id,
        "base_state_hash": sha256_bytes(canonical_bytes(rebound_state)),
        "base_state": rebound_state,
        "target_state": binding["target_state"],
        "target_state_hash": sha256_bytes(
            canonical_bytes(binding["target_state"])
        ),
        "base_event_head": bind_event["event_hash"],
        "target_event": dispatch_event,
        "target_event_hash": dispatch_event["event_hash"],
    }

    rewritten_events = [prepare_event, bind_event, dispatch_event]
    completion_paths = list(transactions_root.glob("complete-*.json"))
    if completion_paths:
        completion_path = completion_paths[0]
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        completion_event = completion["target_event"]
        completion_event["previous_hash"] = dispatch_event["event_hash"]
        completion_event["event_hash"] = sha256_bytes(
            canonical_bytes(
                {
                    key: value
                    for key, value in completion_event.items()
                    if key != "event_hash"
                }
            )
        )
        completion["base_event_head"] = dispatch_event["event_hash"]
        completion["target_event"] = completion_event
        completion["target_event_hash"] = completion_event["event_hash"]
        atomic_write_json(completion_path, completion)
        rewritten_events.append(completion_event)

    dispatch_path.unlink()
    bind_path.unlink()
    atomic_write_json(transactions_root / f"{bind_transition_id}.json", rebound)
    atomic_write_json(
        transactions_root / f"{dispatch_transition_id}.json", redispatch
    )
    events_path.write_bytes(
        b"".join(canonical_bytes(event) + b"\n" for event in rewritten_events)
    )


def load_contract() -> dict:
    return runpy.run_path(str(ROOT / "run_contract.py"))


def load_scorer() -> dict:
    return runpy.run_path(str(ROOT / "evaluator" / "score_results.py"))


def exact_ref(root: Path, path: Path, version: str | int = 1) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "hash": sha256_file(path),
        "version": version,
    }


def finding_result() -> dict:
    return {
        "suite_id": SUITE_ID,
        "case_id": "case-001",
        "attempt_id": "attempt-001",
        "reviewer_execution_ref": {
            "kind": "HOST_SUBAGENT_ATTEMPT",
            "id": "semantic-reviewer-001",
        },
        "result": "FINDING",
        "primary_diagnosis": "FLAT_PEER_OVERLOAD",
        "primary_repair_technique": "GROUP",
        "reader_outcome_failures": ["验收规则难以快速定位。"],
        "verbosity_assessment": {
            "verdict": "FINDING",
            "issue_types": ["FLAT_PEER_OVERLOAD", "DETAIL_IN_MAIN_PATH"],
            "repair_techniques": ["GROUP", "LAYER"],
            "reason": "同层规则需要分组。",
        },
        "checklist_assessment": {
            "verdict": "PASS",
            "issue_types": [],
            "repair_techniques": [],
            "reason": "清单功能没有问题。",
        },
        "visual_assessment": {
            "verdict": "PASS",
            "issue_types": [],
            "repair_techniques": [],
            "reason": "无视觉问题。",
        },
    }


def controller_evidence(result: dict) -> dict:
    return {
        "suite_id": SUITE_ID,
        "case_id": result["case_id"],
        "attempt_id": result["attempt_id"],
        "reviewer_execution_ref": result["reviewer_execution_ref"],
        "evaluation_only": True,
        "product_authority": "NONE",
        "result": result,
    }


def execution_manifest(project_root: Path, phase: str = "RC_CANDIDATE") -> dict:
    stat = project_root.stat()
    root_identity = {
        "path": str(project_root.resolve()),
        "device": stat.st_dev,
        "inode": stat.st_ino,
    }
    build = {
        "path": "build-manifest.json",
        "hash": "sha256:" + "a" * 64,
        "version": "0.2.18-rc.4" if phase == "RC_CANDIDATE" else "0.2.18",
    }
    entries = []
    for ordinal in range(1, 28):
        case = f"case-{((ordinal - 1) // 3) + 1:03d}"
        repeat = ((ordinal - 1) % 3) + 1
        entries.append({
            "ordinal": ordinal,
            "suite_id": SUITE_ID,
            "phase": phase,
            "semantic_case_id": case,
            "agent_case_id": case,
            "repeat_index": repeat,
            "run_id": f"{phase.lower()}-run-{ordinal:03d}",
            "attempt_id": f"{phase.lower()}-attempt-{ordinal:03d}",
            "reviewer_execution_ref": {"kind": "HOST_SUBAGENT_ATTEMPT", "id": f"{phase.lower()}-reviewer-{ordinal:03d}"},
            "author_execution_ref": {"kind": "HOST_AGENT_ATTEMPT", "id": f"{phase.lower()}-author-{ordinal:03d}"},
            "preregistration_checkpoint_ref": {"path": f"runs/{ordinal}/checkpoint.json", "hash": "sha256:" + f"{ordinal:064x}", "version": 1},
            "work_order_ref": {"path": f"work-orders/{ordinal}.json", "hash": "sha256:" + f"{ordinal + 30:064x}", "version": 1},
            "output_target": f"raw/{phase.lower()}/{ordinal}.json",
            "central_project_root": root_identity,
            "state_ref": {"path": f"runs/{ordinal}/state.json", "hash": "sha256:" + f"{ordinal + 60:064x}", "version": 2},
            "installed_build_ref": build,
        })
    return {
        "schema_version": "prd-readability-v0.7-execution-manifest.v1",
        "status": "FROZEN_BEFORE_AGENT_OUTPUT",
        "suite_id": SUITE_ID,
        "phase": phase,
        "central_project_root": root_identity,
        "installed_build_ref": build,
        "required_attempt_count": 27,
        "result_ref_null_count_at_freeze": 27,
        "agent_output_count_at_freeze": 0,
        "entries": entries,
    }


def prepare_receipted_v07_phase(
    root: Path,
    *,
    finalize_receipt: bool = True,
    oracle_results: bool = False,
    raw_transform=None,
) -> tuple[WritingEvalRuntime, dict, list[dict], Path]:
    contract = load_contract()
    project = root / "central-project-root"
    contract["emit_agent_workspace"](project)
    plugin = root / "plugin"
    build_plugin(REPO_ROOT, plugin)
    build_manifest_path = plugin / "build-manifest.json"
    build_manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
    build_manifest["plugin"]["version"] = "0.2.18-rc.4"
    atomic_write_json(build_manifest_path, build_manifest)
    suite_path = project / "agent-suite.json"
    atomic_write_json(
        suite_path,
        {
            "schema_version": "prd-readability-agent-suite.v0.4",
            "suite_id": SUITE_ID,
            "target_eval_schema": "document-experience-reader-eval.v3.1",
            "evaluator_files_included": False,
            "agent_runtime_status": "NOT_RUN",
            "claim_boundary": "Agent input only; scoring expectations are excluded.",
        },
    )
    runtime = WritingEvalRuntime(project, plugin / "skills" / "better-product-graph")
    registrations = []
    results = []
    installed_build_ref = None
    for ordinal in range(1, 28):
        case_id = f"case-{((ordinal - 1) // 3) + 1:03d}"
        repeat = ((ordinal - 1) % 3) + 1
        run_id = f"rc-candidate-run-{ordinal:03d}"
        prepared = runtime.prepare(
            run_id,
            {
                "schema_version": "writing-eval-prepare.v1",
                "suite_id": SUITE_ID,
                "case_id": case_id,
                "suite_ref": exact_ref(project, suite_path),
                "case_ref": exact_ref(project, project / case_id / "case-manifest.json"),
                "candidate_ref": exact_ref(project, project / case_id / "candidate.md"),
                "author_execution_ref": {
                    "kind": "HOST_AGENT_ATTEMPT",
                    "id": f"rc-candidate-author-{ordinal:03d}",
                },
            },
        )
        state = runtime.read_state(run_id)
        reviewer = {
            "kind": "HOST_SUBAGENT_ATTEMPT",
            "id": f"rc-candidate-reviewer-{ordinal:03d}",
        }
        output_target = f"raw/rc-candidate/{ordinal:03d}.json"
        order = contract["build_reviewer_work_order"](
            state,
            phase="RC_CANDIDATE",
            repeat_index=repeat,
            reviewer_execution_ref=reviewer,
            output_target=output_target,
        )
        order_path = project / "work-orders" / f"{ordinal:03d}.json"
        order_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(order_path, order)
        registrations.append(
            {
                "semantic_case_id": case_id,
                "repeat_index": repeat,
                "run_id": run_id,
                "reviewer_execution_ref": reviewer,
                "work_order_ref": exact_ref(project, order_path),
                "output_target": output_target,
            }
        )
        result = passing_review(
            prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
        )
        result["reviewer_execution_ref"] = reviewer
        if oracle_results and case_id <= "case-006":
            primary_pairs = {
                "case-001": ("FLAT_PEER_OVERLOAD", "GROUP"),
                "case-002": ("SEMANTIC_REPETITION", "REFERENCE"),
                "case-003": ("REPRESENTATION_COLLISION", "TRIM"),
                "case-004": ("CHECKLIST_FUNCTION_LOSS", "RESTORE_FUNCTION"),
                "case-005": ("COMPLETION_SEMANTICS_AMBIGUOUS", "EXPLAIN"),
                "case-006": ("ARTIFACT_MATURITY_OVERCLAIM", "BOUNDARY"),
            }
            diagnosis, repair = primary_pairs[case_id]
            result["result"] = "FINDING"
            result["primary_diagnosis"] = diagnosis
            result["primary_repair_technique"] = repair
            result["verbosity_assessment"].update(
                {
                    "verdict": "FINDING",
                    "issue_types": [diagnosis],
                    "repair_techniques": [repair],
                    "reason": "该负例命中预注册的主要可读性问题。",
                }
            )
        visual_pairs = prepared["dispatch"]["writing_eval_context"][
            "reader_visible_visual_pairs"
        ]
        if visual_pairs:
            result["visual_assessment"].update(
                {
                    "verdict": "PASS",
                    "observation_status": "OBSERVED",
                    "visual_pair_refs": visual_pairs,
                    "reason": "已观察精确 SVG/PNG 视觉对。",
                }
            )
        results.append(result)
        build_ref = prepared["dispatch"]["writing_eval_context"]["installed_build_ref"]
        installed_build_ref = installed_build_ref or build_ref
        if build_ref != installed_build_ref:
            raise AssertionError("installed build changed while preparing phase")
    assert installed_build_ref is not None
    manifest = contract["freeze_execution_manifest"](
        project,
        "RC_CANDIDATE",
        installed_build_ref,
        registrations,
        runtime=runtime,
    )
    for entry, result in zip(manifest["entries"], results, strict=True):
        path = project / entry["output_target"]
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.loads(json.dumps(result))
        if raw_transform is not None:
            raw = raw_transform(entry, raw)
        atomic_write_json(path, raw)
    if finalize_receipt:
        contract["write_batch_validation_receipt"](project, manifest)
    return runtime, manifest, results, project


class PrdReadabilityV07ContractTests(unittest.TestCase):
    def test_installed_v07_binding_uses_unchanged_v32_v05_v31_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "central-project-root"
            load_contract()["emit_agent_workspace"](project)
            plugin = root / "plugin"
            build_plugin(REPO_ROOT, plugin)
            suite_path = project / "agent-suite.json"
            atomic_write_json(
                suite_path,
                {
                    "schema_version": "prd-readability-agent-suite.v0.4",
                    "suite_id": SUITE_ID,
                    "target_eval_schema": "document-experience-reader-eval.v3.1",
                    "evaluator_files_included": False,
                    "agent_runtime_status": "NOT_RUN",
                    "claim_boundary": "Agent input only; scoring expectations are excluded.",
                },
            )
            case = project / "case-001" / "case-manifest.json"
            candidate = project / "case-001" / "candidate.md"
            prepared = WritingEvalRuntime(
                project, plugin / "skills" / "better-product-graph"
            ).prepare(
                "writing-eval-v07-binding-case-001",
                {
                    "schema_version": "writing-eval-prepare.v1",
                    "suite_id": SUITE_ID,
                    "case_id": "case-001",
                    "suite_ref": exact_ref(project, suite_path),
                    "case_ref": exact_ref(project, case),
                    "candidate_ref": exact_ref(project, candidate),
                    "author_execution_ref": {
                        "kind": "HOST_AGENT_ATTEMPT",
                        "id": "v07-binding-author-case-001",
                    },
                },
            )
            suite = json.loads((ROOT / "suite.json").read_text())
            context = prepared["dispatch"]["writing_eval_context"]
            self.assertEqual(prepared["status"], "WRITING_EVAL_REVIEW_REQUIRED")
            self.assertEqual(context["review_schema"], "document-experience-reader-eval.v3.1")
            for dispatch_field, suite_field in (
                ("profile_ref", "profile_ref"),
                ("guide_ref", "guide_ref"),
                ("reviewer_resource_ref", "reviewer_resource_ref"),
            ):
                self.assertEqual(
                    {field: context[dispatch_field][field] for field in ("hash", "version")},
                    {field: suite[suite_field][field] for field in ("hash", "version")},
                )
            self.assertEqual(
                prepared["dispatch"]["instruction_hash"],
                suite["instruction_ref"]["hash"],
            )

    def test_frozen_oracle_preserves_v06_aligned_single_finding_semantics(self) -> None:
        scorer = load_scorer()
        oracle = json.loads((ROOT / "evaluator" / "expected.json").read_text())["cases"]["case-001"]
        evidence = controller_evidence(finding_result())
        self.assertEqual(scorer["_semantic_issues"](evidence, oracle), [])

        evidence["result"]["checklist_assessment"] = {
            "verdict": "FINDING",
            "issue_types": ["CHECKLIST_FUNCTION_LOSS"],
            "repair_techniques": ["RESTORE_FUNCTION"],
            "reason": "第二个 finding。",
        }
        self.assertIn(
            "finding_assessment_count",
            scorer["_semantic_issues"](evidence, oracle),
        )

    def test_unregistered_primary_pair_fails_even_when_secondary_values_are_enum_valid(self) -> None:
        scorer = load_scorer()
        oracle = json.loads((ROOT / "evaluator" / "expected.json").read_text())["cases"]["case-001"]
        result = finding_result()
        result["primary_diagnosis"] = "DETAIL_IN_MAIN_PATH"
        result["primary_repair_technique"] = "MOVE"
        issues = scorer["_semantic_issues"](controller_evidence(result), oracle)
        self.assertIn("unregistered_primary_pair", issues)

    def test_positive_requires_pass_null_primary_zero_failures_and_zero_findings(self) -> None:
        scorer = load_scorer()
        oracle = json.loads((ROOT / "evaluator" / "expected.json").read_text())["cases"]["case-007"]
        result = finding_result()
        result.update({
            "case_id": "case-007",
            "result": "PASS",
            "primary_diagnosis": None,
            "primary_repair_technique": None,
            "reader_outcome_failures": [],
        })
        result["verbosity_assessment"] = {
            "verdict": "PASS", "issue_types": [], "repair_techniques": [], "reason": "通过。"
        }
        self.assertEqual(scorer["_semantic_issues"](controller_evidence(result), oracle), [])
        result["reader_outcome_failures"] = ["仍然难以理解。"]
        self.assertIn(
            "positive_reader_outcome_failures",
            scorer["_semantic_issues"](controller_evidence(result), oracle),
        )

    def test_preregistration_requires_two_independent_non_rescuing_27_of_27_phases(self) -> None:
        prereg = json.loads((ROOT / "evaluator" / "preregistration.json").read_text())
        self.assertEqual(prereg["fixture_tree"]["tree_hash"], TREE_HASH)
        self.assertEqual(prereg["mandatory_phases"], list(PHASES))
        self.assertEqual(prereg["phase_gate"], {
            "case_count": 9,
            "repeats_per_case": 3,
            "required_attempt_count": 27,
            "required_passed_attempt_count": 27,
            "required_passed_repeats_per_case": 3,
        })
        self.assertEqual(prereg["cross_phase_policy"], "BOTH_PHASES_PASS_NO_LATER_PHASE_RESCUE")
        self.assertEqual(load_contract()["preregistration_issues"](), [])

    def test_preregistration_hash_binds_every_transitive_evaluator_module(self) -> None:
        prereg = json.loads((ROOT / "evaluator" / "preregistration.json").read_text())
        for field, relative in (
            ("run_contract_ref", "run_contract.py"),
            ("evidence_reader_ref", "evaluator/evidence_reader.py"),
        ):
            self.assertEqual(prereg[field]["path"], relative)
            self.assertEqual(
                prereg[field]["hash"], sha256_file(ROOT / relative)
            )

        scorer = load_scorer()
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "suite"
            shutil.copytree(ROOT, copied)
            reader = copied / "evaluator" / "evidence_reader.py"
            reader.write_bytes(reader.read_bytes() + b"\n# tampered\n")
            globals_dict = scorer["_contract"].__globals__
            original_root = globals_dict["ROOT"]
            globals_dict["ROOT"] = copied
            try:
                with self.assertRaisesRegex(ValueError, "evidence_reader_ref"):
                    scorer["_contract"]()
            finally:
                globals_dict["ROOT"] = original_root

    def test_manifest_shape_binds_every_identity_and_rejects_replacements(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            manifest = execution_manifest(Path(directory))
            self.assertEqual(contract["execution_manifest_shape_issues"](manifest), [])
            manifest["entries"][26]["run_id"] = manifest["entries"][0]["run_id"]
            self.assertIn("duplicate_run_id", contract["execution_manifest_shape_issues"](manifest))

    def test_phase_manifest_rejects_wrong_exact_release_build(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            manifest = execution_manifest(Path(directory), "RC_CANDIDATE")
            manifest["installed_build_ref"]["version"] = "0.2.18"
            for entry in manifest["entries"]:
                entry["installed_build_ref"] = manifest["installed_build_ref"]
            self.assertIn(
                "phase_installed_build_version",
                contract["execution_manifest_shape_issues"](manifest),
            )

    def test_cross_phase_freshness_rejects_reused_runs_attempts_reviewers_outputs_and_build(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rc = execution_manifest(root, "RC_CANDIDATE")
            final = execution_manifest(root, "FINAL_PUBLIC_ARTIFACT")
            for field in ("run_id", "attempt_id", "reviewer_execution_ref", "output_target"):
                final["entries"][0][field] = rc["entries"][0][field]
            final["installed_build_ref"] = rc["installed_build_ref"]
            for entry in final["entries"]:
                entry["installed_build_ref"] = final["installed_build_ref"]
            issues = contract["cross_phase_freshness_issues"](rc, final)
            for expected in (
                "cross_phase_run_id_reuse",
                "cross_phase_attempt_id_reuse",
                "cross_phase_reviewer_id_reuse",
                "cross_phase_output_target_reuse",
                "cross_phase_build_identity_reuse",
            ):
                self.assertIn(expected, issues)

    def test_release_scorer_cannot_rescue_cross_phase_identity_reuse(self) -> None:
        scorer = load_scorer()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifests_root = (
                root
                / ".better-product-graph"
                / "writing-evals"
                / "execution-manifests"
            )
            manifests_root.mkdir(parents=True)
            rc = execution_manifest(root, "RC_CANDIDATE")
            final = execution_manifest(root, "FINAL_PUBLIC_ARTIFACT")
            final["entries"][0]["run_id"] = rc["entries"][0]["run_id"]
            final["entries"][0]["attempt_id"] = rc["entries"][0]["attempt_id"]
            final["entries"][0]["reviewer_execution_ref"] = rc["entries"][0][
                "reviewer_execution_ref"
            ]
            final["entries"][0]["output_target"] = rc["entries"][0][
                "output_target"
            ]
            (manifests_root / "RC_CANDIDATE.json").write_text(
                json.dumps(rc), encoding="utf-8"
            )
            (manifests_root / "FINAL_PUBLIC_ARTIFACT.json").write_text(
                json.dumps(final), encoding="utf-8"
            )
            rc_skill = root / "rc-skill"
            final_skill = root / "final-skill"
            rc_skill.mkdir()
            final_skill.mkdir()
            report = scorer["score_release_phases"](
                root,
                {
                    "RC_CANDIDATE": rc_skill,
                    "FINAL_PUBLIC_ARTIFACT": final_skill,
                },
            )
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("cross_phase_run_id_reuse", report["issues"])
            self.assertIn("cross_phase_reviewer_id_reuse", report["issues"])

    def test_produced_validator_rejection_still_occupies_the_27_attempt_denominator(self) -> None:
        scorer = load_scorer()
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            manifest = execution_manifest(project)
            manifest_path = project / ".better-product-graph" / "writing-evals" / "execution-manifests" / "RC_CANDIDATE.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            first_output = project / manifest["entries"][0]["output_target"]
            first_output.parent.mkdir(parents=True)
            first_output.write_bytes(b"not-json-agent-output")
            unbound_extra = first_output.parent / "replacement-run.json"
            unbound_extra.write_text("{}", encoding="utf-8")
            skill = project / "installed-skill"
            skill.mkdir()
            report = scorer["score_phase"](project, skill, "RC_CANDIDATE")
            self.assertEqual(report["score"]["total"], 27)
            self.assertEqual(report["produced_output_count"], 1)
            self.assertIn("controller_rejected_produced_output", report["attempts"][0]["issues"])
            self.assertNotEqual(report["produced_output_count"], 2, "unbound replacement output must not enter the phase")

    def test_all_27_raw_authority_envelopes_must_match_before_first_submission(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            manifest = execution_manifest(project)
            for entry in manifest["entries"][:-1]:
                path = project / entry["output_target"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({
                        "suite_id": entry["suite_id"],
                        "case_id": entry["agent_case_id"],
                        "attempt_id": entry["attempt_id"],
                        "reviewer_execution_ref": entry["reviewer_execution_ref"],
                        "author_execution_ref": entry["author_execution_ref"],
                        "preregistration_checkpoint_ref": entry["preregistration_checkpoint_ref"],
                    }),
                    encoding="utf-8",
                )
            issues = contract["validate_raw_output_batch_before_submission"](
                project, manifest
            )
            self.assertIn("all_27_raw_outputs_required_before_first_submission", issues)
            last = manifest["entries"][-1]
            path = project / last["output_target"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({
                    "suite_id": last["suite_id"],
                    "case_id": last["agent_case_id"],
                    "attempt_id": last["attempt_id"],
                    "reviewer_execution_ref": last["reviewer_execution_ref"],
                    "author_execution_ref": last["author_execution_ref"],
                    "preregistration_checkpoint_ref": last["preregistration_checkpoint_ref"],
                }),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    issue.startswith("raw_result_contract:")
                    for issue in contract[
                        "validate_raw_output_batch_before_submission"
                    ](project, manifest)
                ),
                "six authority fields are not a complete closed v3.1 result",
            )

    def test_v07_runtime_review_requires_frozen_manifest_and_batch_receipt(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "central-project-root"
            contract["emit_agent_workspace"](project)
            plugin = root / "plugin"
            build_plugin(REPO_ROOT, plugin)
            suite_path = project / "agent-suite.json"
            atomic_write_json(
                suite_path,
                {
                    "schema_version": "prd-readability-agent-suite.v0.4",
                    "suite_id": SUITE_ID,
                    "target_eval_schema": "document-experience-reader-eval.v3.1",
                    "evaluator_files_included": False,
                    "agent_runtime_status": "NOT_RUN",
                    "claim_boundary": "Agent input only; scoring expectations are excluded.",
                },
            )
            runtime = WritingEvalRuntime(project, plugin / "skills" / "better-product-graph")
            prepared = runtime.prepare(
                "v07-review-barrier-run",
                {
                    "schema_version": "writing-eval-prepare.v1",
                    "suite_id": SUITE_ID,
                    "case_id": "case-001",
                    "suite_ref": exact_ref(project, suite_path),
                    "case_ref": exact_ref(project, project / "case-001" / "case-manifest.json"),
                    "candidate_ref": exact_ref(project, project / "case-001" / "candidate.md"),
                    "author_execution_ref": {
                        "kind": "HOST_AGENT_ATTEMPT",
                        "id": "v07-barrier-author",
                    },
                },
            )
            result = passing_review(
                prepared["dispatch"], prepared["preregistration_checkpoint_ref"]
            )
            result["reviewer_execution_ref"]["id"] = "v07-barrier-reviewer"
            with self.assertRaisesRegex(WritingEvalError, "batch-validation receipt"):
                runtime.review("v07-review-barrier-run", result)

    def test_v07_runtime_review_accepts_exact_prevalidated_raw_after_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, manifest, results, _project = prepare_receipted_v07_phase(
                Path(directory)
            )
            response = runtime.review(manifest["entries"][0]["run_id"], results[0])
            self.assertEqual(response["status"], "COMPLETED")

    def test_manifest_replacement_after_receipt_blocks_actual_runtime_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, manifest, results, project = prepare_receipted_v07_phase(
                Path(directory)
            )
            manifest_path = (
                project
                / ".better-product-graph"
                / "writing-evals"
                / "execution-manifests"
                / "RC_CANDIDATE.json"
            )
            replaced = json.loads(manifest_path.read_text(encoding="utf-8"))
            replaced["entries"][-1]["output_target"] = "raw/replacement.json"
            manifest_path.write_text(json.dumps(replaced), encoding="utf-8")
            with self.assertRaisesRegex(WritingEvalError, "bound manifest"):
                runtime.review(manifest["entries"][0]["run_id"], results[0])

    def test_coherent_manifest_and_receipt_rewrite_cannot_replace_controller_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, manifest, results, project = prepare_receipted_v07_phase(
                Path(directory)
            )
            receipts_root = (
                project
                / ".better-product-graph"
                / "writing-evals"
                / "execution-manifests"
            )
            manifest_path = receipts_root / "RC_CANDIDATE.json"
            manifest_receipt_path = receipts_root / "RC_CANDIDATE.manifest-receipt.json"
            batch_receipt_path = receipts_root / "RC_CANDIDATE.batch-validation-receipt.json"
            rewritten = json.loads(manifest_path.read_text(encoding="utf-8"))
            replacement_reviewer = {
                "kind": "HOST_SUBAGENT_ATTEMPT",
                "id": "coherently-rewritten-reviewer-027",
            }
            rewritten["entries"][-1]["reviewer_execution_ref"] = replacement_reviewer
            atomic_write_json(manifest_path, rewritten)
            rewritten_ref = exact_ref(project, manifest_path)
            manifest_receipt = json.loads(
                manifest_receipt_path.read_text(encoding="utf-8")
            )
            manifest_receipt["manifest_ref"] = rewritten_ref
            atomic_write_json(manifest_receipt_path, manifest_receipt)
            batch_receipt = json.loads(batch_receipt_path.read_text(encoding="utf-8"))
            batch_receipt["manifest_ref"] = rewritten_ref
            batch_receipt["entries"][-1][
                "reviewer_execution_ref"
            ] = replacement_reviewer
            atomic_write_json(batch_receipt_path, batch_receipt)
            with self.assertRaisesRegex(WritingEvalError, "bound manifest"):
                runtime.review(manifest["entries"][0]["run_id"], results[0])

    def test_frozen_evidence_reader_accepts_controller_bound_completed_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, manifest, results, project = prepare_receipted_v07_phase(
                Path(directory)
            )
            entry = manifest["entries"][0]
            runtime.review(entry["run_id"], results[0])
            reader = runpy.run_path(str(ROOT / "evaluator" / "evidence_reader.py"))
            evidence = reader["read_completed_evidence"](
                project, runtime.skill_root, entry
            )
            self.assertEqual(evidence["run_id"], entry["run_id"])

    def test_live_and_frozen_evidence_reject_rewritten_completion_base_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, manifest, results, project = prepare_receipted_v07_phase(
                Path(directory)
            )
            entry = manifest["entries"][0]
            runtime.review(entry["run_id"], results[0])
            run_root = (
                project / ".better-product-graph" / "writing-evals" / entry["run_id"]
            )
            completion_path = next(
                (run_root / "transactions").glob("complete-*.json")
            )
            completion = json.loads(completion_path.read_text(encoding="utf-8"))
            completion["base_state_hash"] = "sha256:" + "d" * 64
            atomic_write_json(completion_path, completion)
            reader = runpy.run_path(str(ROOT / "evaluator" / "evidence_reader.py"))
            accepted = []
            for label, operation in (
                ("live", lambda: runtime.read_completed_evidence(entry["run_id"])),
                (
                    "frozen",
                    lambda: reader["read_completed_evidence"](
                        project, runtime.skill_root, entry
                    ),
                ),
            ):
                try:
                    operation()
                except (WritingEvalError, ValueError):
                    continue
                accepted.append(label)
            self.assertEqual(accepted, [], "every evidence path must verify predecessor state")

    def test_frozen_evidence_rejects_rewritten_prepare_identity_in_target_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, manifest, results, project = prepare_receipted_v07_phase(
                Path(directory)
            )
            entry = manifest["entries"][0]
            runtime.review(entry["run_id"], results[0])
            run_root = (
                project / ".better-product-graph" / "writing-evals" / entry["run_id"]
            )
            state_path = run_root / "state.json"
            completion_path = next(
                (run_root / "transactions").glob("complete-*.json")
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["prepare_identity_hash"] = "sha256:" + "e" * 64
            atomic_write_json(state_path, state)
            completion = json.loads(completion_path.read_text(encoding="utf-8"))
            completion["target_state"] = state
            completion["target_state_hash"] = sha256_bytes(
                json.dumps(
                    state,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            )
            atomic_write_json(completion_path, completion)
            reader = runpy.run_path(str(ROOT / "evaluator" / "evidence_reader.py"))
            with self.assertRaisesRegex(ValueError, "prepare identity|provenance"):
                reader["read_completed_evidence"](
                    project, runtime.skill_root, entry
                )

    def test_runtime_and_scorer_reject_relabelled_manifest_binding_transaction(self) -> None:
        with self.subTest(surface="actual_runtime_review"):
            with tempfile.TemporaryDirectory() as directory:
                runtime, manifest, results, project = prepare_receipted_v07_phase(
                    Path(directory)
                )
                entry = manifest["entries"][0]
                transaction_path = next(
                    (
                        project
                        / ".better-product-graph"
                        / "writing-evals"
                        / entry["run_id"]
                        / "transactions"
                    ).glob("bind_manifest-*.json")
                )
                transaction = json.loads(
                    transaction_path.read_text(encoding="utf-8")
                )
                transaction["kind"] = "dispatch"
                atomic_write_json(transaction_path, transaction)
                with self.assertRaisesRegex(WritingEvalError, "transition"):
                    runtime.review(entry["run_id"], results[0])

        with self.subTest(surface="frozen_phase_scorer"):
            with tempfile.TemporaryDirectory() as directory:
                runtime, manifest, results, project = prepare_receipted_v07_phase(
                    Path(directory), oracle_results=True
                )
                for entry, result in zip(manifest["entries"], results, strict=True):
                    runtime.review(entry["run_id"], result)
                entry = manifest["entries"][0]
                transaction_path = next(
                    (
                        project
                        / ".better-product-graph"
                        / "writing-evals"
                        / entry["run_id"]
                        / "transactions"
                    ).glob("bind_manifest-*.json")
                )
                transaction = json.loads(
                    transaction_path.read_text(encoding="utf-8")
                )
                transaction["kind"] = "dispatch"
                atomic_write_json(transaction_path, transaction)
                report = load_scorer()["score_phase"](
                    project, runtime.skill_root, "RC_CANDIDATE"
                )
                self.assertEqual(report["status"], "FAIL")
                self.assertIn(
                    "controller_validation_rejection_preserved",
                    report["attempts"][0]["issues"],
                )

    def test_runtime_and_scorer_reject_foreign_identity_in_nonfinal_transaction(self) -> None:
        def corrupt_dispatch(project: Path, run_id: str) -> None:
            transaction_path = next(
                (
                    project
                    / ".better-product-graph"
                    / "writing-evals"
                    / run_id
                    / "transactions"
                ).glob("dispatch-*.json")
            )
            transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
            transaction["run_id"] = "foreign-run"
            transaction["attempt_id"] = "foreign-attempt"
            atomic_write_json(transaction_path, transaction)

        with self.subTest(surface="actual_runtime_review"):
            with tempfile.TemporaryDirectory() as directory:
                runtime, manifest, results, project = prepare_receipted_v07_phase(
                    Path(directory)
                )
                entry = manifest["entries"][0]
                corrupt_dispatch(project, entry["run_id"])
                with self.assertRaisesRegex(WritingEvalError, "transition"):
                    runtime.review(entry["run_id"], results[0])

        with self.subTest(surface="frozen_phase_scorer"):
            with tempfile.TemporaryDirectory() as directory:
                runtime, manifest, results, project = prepare_receipted_v07_phase(
                    Path(directory), oracle_results=True
                )
                for entry, result in zip(manifest["entries"], results, strict=True):
                    runtime.review(entry["run_id"], result)
                entry = manifest["entries"][0]
                corrupt_dispatch(project, entry["run_id"])
                report = load_scorer()["score_phase"](
                    project, runtime.skill_root, "RC_CANDIDATE"
                )
                self.assertEqual(report["status"], "FAIL")
                self.assertIn(
                    "controller_validation_rejection_preserved",
                    report["attempts"][0]["issues"],
                )

    def test_runtime_and_scorer_reject_coherent_bind_before_frozen_dispatch(self) -> None:
        with self.subTest(surface="actual_runtime_review"):
            with tempfile.TemporaryDirectory() as directory:
                runtime, manifest, results, project = prepare_receipted_v07_phase(
                    Path(directory)
                )
                entry = manifest["entries"][0]
                unchanged_state_ref = json.loads(json.dumps(entry["state_ref"]))
                replay_manifest_binding_before_dispatch(project, entry)
                self.assertEqual(entry["state_ref"], unchanged_state_ref)
                with self.assertRaisesRegex(
                    WritingEvalError, "manifest|state|transition"
                ):
                    runtime.review(entry["run_id"], results[0])

        with self.subTest(surface="frozen_phase_scorer"):
            with tempfile.TemporaryDirectory() as directory:
                runtime, manifest, results, project = prepare_receipted_v07_phase(
                    Path(directory), oracle_results=True
                )
                for entry, result in zip(manifest["entries"], results, strict=True):
                    runtime.review(entry["run_id"], result)
                entry = manifest["entries"][0]
                unchanged_state_ref = json.loads(json.dumps(entry["state_ref"]))
                replay_manifest_binding_before_dispatch(project, entry)
                self.assertEqual(entry["state_ref"], unchanged_state_ref)
                report = load_scorer()["score_phase"](
                    project, runtime.skill_root, "RC_CANDIDATE"
                )
                self.assertEqual(report["status"], "FAIL")
                self.assertIn(
                    "controller_validation_rejection_preserved",
                    report["attempts"][0]["issues"],
                )

    def test_reviewer_projection_excludes_oracle_and_other_reviewer_work(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _runtime, manifest, _results, anonymous = prepare_receipted_v07_phase(root)
            work_order = anonymous / manifest["entries"][0]["work_order_ref"]["path"]
            reviewer_id = manifest["entries"][0]["reviewer_execution_ref"]["id"]
            target = root / "projection"
            contract["emit_reviewer_projection"](
                manifest, reviewer_id, anonymous, target
            )
            self.assertTrue((target / "candidate.md").is_file())
            self.assertEqual(
                (target / "work-order.json").read_bytes(), work_order.read_bytes()
            )
            self.assertFalse((target / "case-002").exists())
            files = [path.relative_to(target).as_posix().lower() for path in target.rglob("*") if path.is_file()]
            for forbidden in ("expected", "preregistration", "score_results", "fixture-review", "adjudication"):
                self.assertFalse(any(forbidden in path for path in files), forbidden)
            projection = json.loads((target / "reviewer-projection.json").read_text())
            self.assertFalse(projection["evaluator_files_included"])
            self.assertEqual(projection["reviewer_execution_ref"]["id"], reviewer_id)

    def test_real_reviewer_projection_resolves_all_six_isolated_refs_locally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _runtime, manifest, _results, project = prepare_receipted_v07_phase(root)
            contract = load_contract()
            entry = manifest["entries"][0]
            reviewer_id = entry["reviewer_execution_ref"]["id"]
            target = root / "self-contained-projection"
            contract["emit_reviewer_projection"](
                manifest, reviewer_id, project, target
            )
            order = json.loads((target / "work-order.json").read_text(encoding="utf-8"))
            self.assertEqual(len(order["isolated_input_refs"]), 6)
            for ref in order["isolated_input_refs"]:
                local = target / ref["path"]
                self.assertTrue(local.is_file() and not local.is_symlink(), ref["path"])
                self.assertEqual(sha256_file(local), ref["hash"])

    def test_reviewer_projection_rejects_any_file_outside_canonical_export_manifest(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _runtime, manifest, _results, anonymous = prepare_receipted_v07_phase(root)
            (anonymous / "case-001" / "oracle-hint.json").write_text(
                json.dumps({"required_result": "FINDING"}), encoding="utf-8"
            )
            reviewer_id = manifest["entries"][0]["reviewer_execution_ref"]["id"]
            with self.assertRaisesRegex(ValueError, "canonical export manifest"):
                contract["emit_reviewer_projection"](
                    manifest, reviewer_id, anonymous, root / "projection"
                )

    def test_reviewer_projection_rejects_oracle_fields_in_closed_work_order(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _runtime, manifest, _results, anonymous = prepare_receipted_v07_phase(root)
            work_order = anonymous / manifest["entries"][0]["work_order_ref"]["path"]
            order = json.loads(work_order.read_text(encoding="utf-8"))
            order["required_result"] = "FINDING"
            atomic_write_json(work_order, order)
            reviewer_id = manifest["entries"][0]["reviewer_execution_ref"]["id"]
            with self.assertRaises(ValueError):
                contract["emit_reviewer_projection"](
                    manifest, reviewer_id, anonymous, root / "projection"
                )

    def test_reviewer_projection_rejects_rebased_nonexact_dispatch_authority(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _runtime, manifest, _results, anonymous = prepare_receipted_v07_phase(root)
            entry = manifest["entries"][0]
            work_order = anonymous / entry["work_order_ref"]["path"]
            order = json.loads(work_order.read_text(encoding="utf-8"))
            order["instruction_ref"] = "oracle-hint.json"
            atomic_write_json(work_order, order)
            reviewer_id = entry["reviewer_execution_ref"]["id"]
            with self.assertRaises(ValueError):
                contract["emit_reviewer_projection"](
                    manifest, reviewer_id, anonymous, root / "projection"
                )

    def test_authority_only_mechanical_correction_preserves_raw_and_semantic_hash(self) -> None:
        contract = load_contract()
        original = finding_result()
        original["case_id"] = "wrong-case"
        corrected = json.loads(json.dumps(original))
        corrected["case_id"] = "case-001"
        original_bytes = json.dumps(original, ensure_ascii=False, indent=2).encode()
        corrected_bytes = json.dumps(corrected, ensure_ascii=False, indent=2).encode()
        record = contract["mechanical_correction_record"](
            original_bytes,
            corrected_bytes,
            {"case_id": "case-001"},
        )
        self.assertEqual(record["changed_fields"], ["case_id"])
        self.assertEqual(record["original_raw_hash"], sha256_bytes(original_bytes))
        self.assertEqual(record["semantic_payload_hash_before"], record["semantic_payload_hash_after"])

        semantically_changed = json.loads(json.dumps(corrected))
        semantically_changed["primary_repair_technique"] = "LAYER"
        with self.assertRaisesRegex(ValueError, "semantic payload"):
            contract["mechanical_correction_record"](
                original_bytes,
                json.dumps(semantically_changed).encode(),
                {"case_id": "case-001"},
            )

    def test_authority_only_preflight_correction_reaches_runtime_and_phase_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def wrong_authority(entry: dict, raw: dict) -> dict:
                if entry["ordinal"] == 1:
                    raw["case_id"] = "case-999"
                return raw

            runtime, manifest, results, project = prepare_receipted_v07_phase(
                root,
                finalize_receipt=False,
                oracle_results=True,
                raw_transform=wrong_authority,
            )
            contract = load_contract()
            self.assertIn(
                "preflight_raw_output_batch", contract,
                "public non-submitting batch preflight is required",
            )
            preflight_issues = contract["preflight_raw_output_batch"](
                project, manifest
            )
            self.assertIn("mechanical_correction_required:1", preflight_issues)
            entry = manifest["entries"][0]
            original_path = project / entry["output_target"]
            original_bytes = original_path.read_bytes()
            rejection_path = original_path.with_name(
                original_path.name + ".preflight-rejection.json"
            )
            self.assertTrue(rejection_path.is_file())
            corrected_path = original_path.with_name(
                original_path.name + ".corrected.json"
            )
            atomic_write_json(corrected_path, results[0])
            record = contract["mechanical_correction_record"](
                original_bytes,
                corrected_path.read_bytes(),
                {"case_id": results[0]["case_id"]},
            )
            atomic_write_json(
                original_path.with_name(
                    original_path.name + ".mechanical-correction.json"
                ),
                record,
            )
            contract["write_batch_validation_receipt"](project, manifest)
            self.assertEqual(original_path.read_bytes(), original_bytes)
            for manifest_entry, result in zip(
                manifest["entries"], results, strict=True
            ):
                response = runtime.review(manifest_entry["run_id"], result)
                self.assertEqual(response["status"], "COMPLETED")
            report = load_scorer()["score_phase"](
                project, runtime.skill_root, "RC_CANDIDATE"
            )
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["score"], {"passed": 27, "total": 27, "required": 27})

    def test_preflight_rejects_semantic_change_in_corrected_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def wrong_authority(entry: dict, raw: dict) -> dict:
                if entry["ordinal"] == 1:
                    raw["case_id"] = "case-999"
                return raw

            _runtime, manifest, results, project = prepare_receipted_v07_phase(
                root,
                finalize_receipt=False,
                raw_transform=wrong_authority,
            )
            contract = load_contract()
            self.assertIn(
                "preflight_raw_output_batch", contract,
                "public non-submitting batch preflight is required",
            )
            self.assertIn(
                "mechanical_correction_required:1",
                contract["preflight_raw_output_batch"](project, manifest),
            )
            entry = manifest["entries"][0]
            original_path = project / entry["output_target"]
            corrected = json.loads(json.dumps(results[0]))
            corrected["reader_readback"]["problem_and_outcome"] = "语义被替换。"
            corrected_path = original_path.with_name(
                original_path.name + ".corrected.json"
            )
            atomic_write_json(corrected_path, corrected)
            atomic_write_json(
                original_path.with_name(
                    original_path.name + ".mechanical-correction.json"
                ),
                {"schema_version": "forged"},
            )
            with self.assertRaisesRegex(ValueError, "semantic|correction|batch"):
                contract["write_batch_validation_receipt"](project, manifest)

    def test_anonymous_export_contains_no_evaluator_or_fixture_review_custody(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "anonymous"
            contract["emit_agent_workspace"](target)
            paths = [path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()]
            lowered = "\n".join(paths).lower()
            for forbidden in ("expected", "preregistration", "score_results", "fixture-review", "adjudication"):
                self.assertNotIn(forbidden, lowered)
            all_bytes = b"\n".join(path.read_bytes() for path in target.rglob("*") if path.is_file())
            self.assertNotIn(b"allowed_primary_pairs", all_bytes)

    def test_contract_run_is_mechanical_pass_while_all_product_statuses_remain_not_run(self) -> None:
        payload = load_contract()["contract_payload"](export_requested=False)
        self.assertEqual(payload["contract_status"], "PASS")
        self.assertEqual(payload["fixture_review_status"], "APPROVED")
        self.assertEqual(payload["agent_runtime_status"], "NOT_RUN")
        self.assertEqual(payload["phase_runtime_status"], {
            "RC_CANDIDATE": "NOT_RUN",
            "FINAL_PUBLIC_ARTIFACT": "NOT_RUN",
        })
        self.assertEqual(payload["real_prd_review_status"], "NOT_RUN")
        self.assertEqual(payload["human_reader_validation"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
