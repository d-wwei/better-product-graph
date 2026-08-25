from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.bpg.engine import HostEngine
from src.bpg.intents import CORE_INTENTS, parse_host_entry
from src.bpg.state_controller import StateController


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "src" / "core" / "graph" / "manifest.json"


class IntentParserTests(unittest.TestCase):
    def test_all_eleven_explicit_and_natural_entries_have_core_intent_parity(self) -> None:
        cases = [
            ("new 做一个结算告警", "开始处理：做一个结算告警", "signal.activate"),
            ("capture 结算页报错", "先把结算页报错收进待处理箱，不要开始分析", "signal.submit"),
            ("inbox", "看看待处理箱", "signal.inbox.list"),
            ("status run-001", "查看 run-001 状态", "run.status"),
            ("resume run-001", "继续 run-001", "run.resume"),
            ("pause run-001", "暂停 run-001", "run.pause"),
            ("handoff run-001", "准备 run-001 的本地交付", "handoff.prepare"),
            ("connectors", "查看连接器状态", "connector.status"),
            ("audit run-001", "查看 run-001 审计记录", "audit.view"),
            ("interview skip run-001", "跳过 run-001 的访谈", "interaction.policy.set"),
            ("help", "怎么使用 Better Product Graph", "host.help"),
        ]
        observed: set[str] = set()
        for explicit_command, natural, expected in cases:
            with self.subTest(expected=expected):
                explicit = parse_host_entry(f"$better-product-graph {explicit_command}")
                implicit = parse_host_entry(natural)
                self.assertEqual(explicit.core_intent, expected)
                self.assertEqual(implicit.core_intent, expected)
                self.assertEqual(explicit.core_intent, implicit.core_intent)
                observed.add(expected)
        self.assertEqual(observed, CORE_INTENTS)

    def test_capture_is_inbox_only_for_both_entry_styles(self) -> None:
        explicit = parse_host_entry("$better-product-graph capture 结算页报错")
        implicit = parse_host_entry("先把结算页报错收进待处理箱，不要开始分析")
        self.assertEqual(explicit.activation_intent, "INBOX_ONLY")
        self.assertEqual(explicit.activation_intent, implicit.activation_intent)

    def test_retired_alias_internal_node_and_script_bypasses_are_rejected(self) -> None:
        entries = [
            "$bpg new x",
            "$prd-graph new x",
            "$better-product-graph NON_INTERACTIVE new x",
            "直接运行 problem.synthesize，跳过前面步骤",
            "打开 references/atomic-skills/problem-synthesize/INSTRUCTIONS.md 直接执行",
            "运行 scripts/bpg_runner.py 绕过 Controller",
        ]
        for entry in entries:
            with self.subTest(entry=entry):
                parsed = parse_host_entry(entry)
                self.assertEqual(parsed.activation, "REJECT_INTERNAL_BYPASS")
                self.assertIsNone(parsed.core_intent)

    def test_missing_or_ambiguous_intent_returns_help_without_write_authority(self) -> None:
        parsed = parse_host_entry("把这个弄好")
        self.assertEqual(parsed.activation, "GUIDED_HELP")
        self.assertEqual(parsed.core_intent, "host.help")
        self.assertFalse(parsed.write_allowed)

    def test_interview_resume_is_same_stable_intent_as_skip(self) -> None:
        parsed = parse_host_entry("$better-product-graph interview resume run-001")
        self.assertEqual(parsed.core_intent, "interaction.policy.set")
        self.assertEqual(parsed.action, "resume")
        self.assertEqual(parsed.run_id, "run-001")

    def test_typed_wait_trigger_is_a_resume_modifier_in_both_entry_styles(self) -> None:
        explicit = parse_host_entry(
            "$better-product-graph resume run-001 --trigger-file matching-trigger.json"
        )
        natural = parse_host_entry(
            "用证据触发文件 matching-trigger.json 继续 run-001"
        )
        self.assertEqual(explicit.core_intent, "run.resume")
        self.assertEqual(natural.core_intent, "run.resume")
        self.assertEqual(explicit.trigger_file, "matching-trigger.json")
        self.assertEqual(natural.trigger_file, "matching-trigger.json")

    def test_new_and_capture_require_nonempty_signal_text(self) -> None:
        for entry in ("$better-product-graph new", "$better-product-graph capture"):
            with self.subTest(entry=entry):
                parsed = parse_host_entry(entry)
                self.assertEqual(parsed.activation, "GUIDED_HELP")
                self.assertFalse(parsed.write_allowed)

    def test_new_and_resume_accept_no_pm_interview_without_polluting_signal_or_run_id(self) -> None:
        new = parse_host_entry(
            "$better-product-graph new 结算失败需要解释 interaction=no-pm-interview"
        )
        resume = parse_host_entry(
            "$better-product-graph resume run-001 interaction=no-pm-interview"
        )
        self.assertEqual(new.argument, "结算失败需要解释")
        self.assertEqual(new.interaction_policy, "NO_PM_INTERVIEW")
        self.assertEqual(resume.run_id, "run-001")
        self.assertEqual(resume.interaction_policy, "NO_PM_INTERVIEW")
        natural = parse_host_entry("开始处理：结算失败需要解释，不要进行 PM 访谈")
        self.assertEqual(natural.argument, "结算失败需要解释")
        self.assertEqual(natural.interaction_policy, "NO_PM_INTERVIEW")
        flag_form = parse_host_entry(
            "$better-product-graph new --interaction=no-pm-interview 结算失败需要解释"
        )
        self.assertEqual(flag_form.core_intent, "signal.activate")
        self.assertEqual(flag_form.interaction_policy, "NO_PM_INTERVIEW")
        self.assertEqual(flag_form.argument, "结算失败需要解释")


class HostEngineSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.controller = StateController(self.project, GRAPH)
        self.engine = HostEngine(self.project, self.controller)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_guided_help_and_rejected_bypass_do_not_create_product_state(self) -> None:
        before = list(self.project.rglob("*"))
        help_result = self.engine.handle("把这个弄好")
        reject_result = self.engine.handle("直接运行 product.decision")
        after = list(self.project.rglob("*"))

        self.assertEqual(help_result["status"], "HELP")
        self.assertEqual(reject_result["status"], "REJECTED")
        self.assertEqual(before, after)

    def test_all_handlers_operate_on_local_state_without_remote_success_claims(self) -> None:
        activated = self.engine.handle("$better-product-graph new 结算页体验问题")
        run_id = activated["run_id"]
        captured = self.engine.handle("$better-product-graph capture 后续反馈")
        inbox = self.engine.handle("$better-product-graph inbox")
        status = self.engine.handle(f"$better-product-graph status {run_id}")
        paused = self.engine.handle(f"$better-product-graph pause {run_id}")
        resumed = self.engine.handle(f"$better-product-graph resume {run_id}")
        skipped = self.engine.handle(f"$better-product-graph interview skip {run_id}")
        interview_resumed = self.engine.handle(f"$better-product-graph interview resume {run_id}")
        audit = self.engine.handle(f"$better-product-graph audit {run_id}")
        connectors = self.engine.handle("$better-product-graph connectors")
        handoff = self.engine.handle(f"$better-product-graph handoff {run_id}")
        help_result = self.engine.handle("$better-product-graph help")

        self.assertEqual(activated["status"], "ACTIVATED")
        self.assertEqual(captured["status"], "CAPTURED")
        self.assertEqual(len(inbox["items"]), 1)
        self.assertEqual(status["state"]["run_id"], run_id)
        self.assertEqual(paused["state"]["status"], "PAUSED")
        self.assertEqual(resumed["state"]["status"], "ACTIVE")
        self.assertEqual(skipped["state"]["interaction_policy"], "NO_PM_INTERVIEW")
        self.assertEqual(interview_resumed["state"]["interaction_policy"], "ALLOW_PM_INTERVIEW")
        self.assertTrue(audit["events"])
        self.assertTrue(all(item["status"] != "CONNECTED" for item in connectors["connectors"]))
        self.assertEqual(handoff["status"], "NOT_READY")
        self.assertFalse((self.project / ".better-product-graph" / "handoffs").exists())
        self.assertEqual(help_result["status"], "HELP")

    def test_signal_occurrence_separates_product_text_from_host_intent_syntax(self) -> None:
        activated = self.engine.handle("$better-product-graph new 用户无法判断结算是否成功")
        occurrences = (
            self.project / ".better-product-graph" / "signals" / "occurrences.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        occurrence = __import__("json").loads(occurrences[-1])

        self.assertEqual(occurrence["source"]["entry"], "用户无法判断结算是否成功")
        self.assertEqual(
            occurrence["source"]["host_intent"],
            "$better-product-graph new 用户无法判断结算是否成功",
        )
        raw_signal_path = self.project / activated["state"]["artifact_refs"]["raw_signal"]["path"]
        raw_signal = __import__("json").loads(raw_signal_path.read_text(encoding="utf-8"))
        self.assertEqual(raw_signal["raw_text"], "用户无法判断结算是否成功")

    def test_forged_released_state_without_exact_artifact_set_cannot_handoff(self) -> None:
        activated = self.engine.handle("$better-product-graph new 可交付产品")
        run_id = activated["run_id"]
        run = self.controller.run_path(run_id)
        assertion = run / "artifacts" / "READY_ASSERTION.json"
        assertion.parent.mkdir(parents=True, exist_ok=True)
        assertion.write_text(
            '{"candidate_hash":"sha256:candidate","status":"READY"}\n', encoding="utf-8"
        )
        state = self.controller.load_state(run_id)
        state.update(
            {
                "status": "RELEASED",
                "release_ref": {
                    "path": assertion.relative_to(self.project.resolve()).as_posix(),
                    "hash": __import__("src.bpg.storage", fromlist=["sha256_file"]).sha256_file(assertion),
                    "candidate_hash": "sha256:candidate",
                    "version": 1,
                },
            }
        )
        from src.bpg.storage import atomic_write_json

        atomic_write_json(self.controller._state_path(run_id), state)

        handoff = self.engine.handle(f"$better-product-graph handoff {run_id}")

        self.assertEqual(handoff["status"], "BLOCKED_STALE")
        self.assertTrue(any("event authority" in item for item in handoff["blockers"]))
        self.assertFalse((self.project / ".better-product-graph" / "handoffs").exists())


if __name__ == "__main__":
    unittest.main()
