"""One Codex Host entry parser for the eleven stable Core intents."""

from __future__ import annotations

import re
from dataclasses import dataclass


CORE_INTENTS = frozenset(
    {
        "signal.submit",
        "signal.activate",
        "signal.inbox.list",
        "run.status",
        "run.resume",
        "run.pause",
        "handoff.prepare",
        "connector.status",
        "audit.view",
        "interaction.policy.set",
        "host.help",
    }
)

COMMANDS = {
    "new": ("signal.activate", "ACTIVATE"),
    "capture": ("signal.submit", "INBOX_ONLY"),
    "inbox": ("signal.inbox.list", None),
    "status": ("run.status", None),
    "resume": ("run.resume", None),
    "pause": ("run.pause", None),
    "handoff": ("handoff.prepare", None),
    "connectors": ("connector.status", None),
    "audit": ("audit.view", None),
    "help": ("host.help", None),
}

WRITE_INTENTS = frozenset(
    {
        "signal.submit",
        "signal.activate",
        "run.resume",
        "run.pause",
        "handoff.prepare",
        "interaction.policy.set",
    }
)

RUN_ID = re.compile(r"\brun-[A-Za-z0-9._-]+\b", re.IGNORECASE)
INTERNAL_BYPASS = re.compile(
    r"(?:\b(?:signal|route|incident|bug|evidence|problem|product|plan|prd|review|handoff)\.[a-z][a-z0-9._-]*\b|"
    r"references/atomic-skills|src/core/atomic-skills|scripts/bpg_runner\.py|绕过\s*Controller)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HostIntent:
    raw_entry: str
    core_intent: str | None
    activation: str
    activation_intent: str | None = None
    argument: str = ""
    run_id: str | None = None
    action: str | None = None
    write_allowed: bool = False
    interaction_policy: str | None = None
    trigger_file: str | None = None


def _rejected(raw: str) -> HostIntent:
    return HostIntent(raw, None, "REJECT_INTERNAL_BYPASS", write_allowed=False)


def _help(raw: str) -> HostIntent:
    return HostIntent(raw, "host.help", "GUIDED_HELP", write_allowed=False)


def _accepted(
    raw: str,
    core_intent: str,
    *,
    activation_intent: str | None = None,
    argument: str = "",
    run_id: str | None = None,
    action: str | None = None,
    interaction_policy: str | None = None,
    trigger_file: str | None = None,
) -> HostIntent:
    return HostIntent(
        raw_entry=raw,
        core_intent=core_intent,
        activation="ACCEPTED",
        activation_intent=activation_intent,
        argument=argument.strip(),
        run_id=run_id,
        action=action,
        write_allowed=core_intent in WRITE_INTENTS,
        interaction_policy=interaction_policy,
        trigger_file=trigger_file,
    )


def _extract_run_id(text: str) -> str | None:
    match = RUN_ID.search(text)
    return match.group(0) if match else None


def _parse_explicit(raw: str, body: str) -> HostIntent:
    tokens = body.split()
    if not tokens:
        return _help(raw)
    command = tokens[0].lower()
    trigger_tokens = [item for item in tokens[1:] if item.startswith("trigger=")]
    trigger_flags = [index for index, item in enumerate(tokens[1:], start=1) if item == "--trigger-file"]
    if trigger_tokens and trigger_flags:
        return _help(raw)
    if trigger_flags:
        index = trigger_flags[0]
        if command != "resume" or len(trigger_flags) != 1 or index + 1 >= len(tokens):
            return _help(raw)
        trigger_file = tokens[index + 1]
        tokens = [item for offset, item in enumerate(tokens) if offset not in {index, index + 1}]
    elif trigger_tokens:
        if command != "resume" or len(trigger_tokens) != 1 or not trigger_tokens[0][8:]:
            return _help(raw)
        trigger_file = trigger_tokens[0][8:]
        tokens = [tokens[0], *[item for item in tokens[1:] if item != trigger_tokens[0]]]
    else:
        trigger_file = None
    no_interview_tokens = {"interaction=no-pm-interview", "--interaction=no-pm-interview"}
    no_interview = any(item in no_interview_tokens for item in tokens[1:])
    if no_interview:
        tokens = [
            tokens[0],
            *[item for item in tokens[1:] if item not in no_interview_tokens],
        ]
        if command not in {"new", "resume"}:
            return _help(raw)
    if command == "interview":
        if len(tokens) < 3 or tokens[1].lower() not in {"skip", "resume"}:
            return _help(raw)
        action = tokens[1].lower()
        run_id = tokens[2]
        if RUN_ID.fullmatch(run_id) is None:
            return _help(raw)
        return _accepted(
            raw,
            "interaction.policy.set",
            run_id=run_id,
            action=action,
        )
    mapped = COMMANDS.get(command)
    if mapped is None:
        return _help(raw)
    core_intent, activation_intent = mapped
    argument = " ".join(tokens[1:])
    if command in {"new", "capture"} and not argument.strip():
        return _help(raw)
    run_id = _extract_run_id(argument)
    if core_intent in {"run.status", "run.resume", "run.pause", "handoff.prepare", "audit.view"}:
        if run_id is None:
            return _help(raw)
    return _accepted(
        raw,
        core_intent,
        activation_intent=activation_intent,
        argument=argument,
        run_id=run_id,
        interaction_policy="NO_PM_INTERVIEW" if no_interview else None,
        trigger_file=trigger_file,
    )


def _parse_natural(raw: str) -> HostIntent:
    run_id = _extract_run_id(raw)
    trigger_match = re.search(r"(?:trigger=|证据触发文件[：:\s]+)(\S+)", raw)
    no_interview = any(
        phrase in raw for phrase in ("不要进行 PM 访谈", "不进行 PM 访谈", "无需 PM 访谈")
    )
    if "访谈" in raw and any(word in raw for word in ("跳过", "暂停")):
        return (
            _accepted(raw, "interaction.policy.set", run_id=run_id, action="skip")
            if run_id
            else _help(raw)
        )
    if "访谈" in raw and any(word in raw for word in ("恢复", "继续")):
        return (
            _accepted(raw, "interaction.policy.set", run_id=run_id, action="resume")
            if run_id
            else _help(raw)
        )
    if "连接器" in raw or "connector" in raw.lower():
        return _accepted(raw, "connector.status")
    if "审计" in raw:
        return _accepted(raw, "audit.view", run_id=run_id) if run_id else _help(raw)
    if "本地交付" in raw or ("handoff" in raw.lower() and run_id):
        return _accepted(raw, "handoff.prepare", run_id=run_id) if run_id else _help(raw)
    if "暂停" in raw and run_id:
        return _accepted(raw, "run.pause", run_id=run_id)
    if "继续" in raw and run_id:
        return _accepted(
            raw,
            "run.resume",
            run_id=run_id,
            interaction_policy="NO_PM_INTERVIEW" if no_interview else None,
            trigger_file=trigger_match.group(1) if trigger_match else None,
        )
    if "状态" in raw and run_id:
        return _accepted(raw, "run.status", run_id=run_id)
    if "待处理箱" in raw and any(word in raw for word in ("收进", "记录", "捕获", "不要开始")):
        argument = raw.split("待处理箱", 1)[0].removeprefix("先把").strip("，, ")
        return _accepted(raw, "signal.submit", activation_intent="INBOX_ONLY", argument=argument)
    if "待处理箱" in raw and any(word in raw for word in ("看", "列出", "打开")):
        return _accepted(raw, "signal.inbox.list")
    if raw.startswith("开始处理") or raw.startswith("启动处理"):
        argument = raw.split("：", 1)[1] if "：" in raw else raw[4:].lstrip(" :")
        for phrase in ("，不要进行 PM 访谈", "，不进行 PM 访谈", "，无需 PM 访谈"):
            argument = argument.removesuffix(phrase)
        return _accepted(
            raw,
            "signal.activate",
            activation_intent="ACTIVATE",
            argument=argument,
            interaction_policy="NO_PM_INTERVIEW" if no_interview else None,
        )
    if "怎么使用 Better Product Graph" in raw or "如何使用 Better Product Graph" in raw:
        return _accepted(raw, "host.help")
    return _help(raw)


def parse_host_entry(entry: str) -> HostIntent:
    raw = entry.strip()
    lowered = raw.lower()
    if lowered.startswith("$bpg") or lowered.startswith("$prd-graph"):
        return _rejected(raw)
    if "NON_INTERACTIVE" in raw or INTERNAL_BYPASS.search(raw):
        return _rejected(raw)
    prefix = "$better-product-graph"
    if lowered.startswith(prefix):
        boundary = raw[len(prefix) :]
        if boundary and not boundary[0].isspace():
            return _help(raw)
        return _parse_explicit(raw, boundary.strip())
    return _parse_natural(raw)
