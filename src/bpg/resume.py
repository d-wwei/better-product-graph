"""Exact-ref resume inspection and plain-language Resume Brief rendering."""

from __future__ import annotations

from dataclasses import dataclass

from .state_controller import StateController, TransitionRejected


@dataclass(frozen=True)
class ResumeInspection:
    status: str
    run_id: str
    current_node: str
    last_completed_node: str | None
    next_allowed_nodes: list[str]
    waiting: dict | None
    blockers: list[str]


def inspect_resume(controller: StateController, run_id: str) -> ResumeInspection:
    try:
        state = controller.authoritative_read_barrier(run_id)
    except TransitionRejected as error:
        stale = controller.load_state(run_id)
        return ResumeInspection(
            status="BLOCKED_STALE",
            run_id=run_id,
            current_node=stale["current_node"],
            last_completed_node=stale["last_completed_node"],
            next_allowed_nodes=stale["next_allowed_nodes"],
            waiting=stale.get("waiting"),
            blockers=[str(error)],
        )
    blockers: list[str] = []
    status = "READY_TO_RESUME"
    if state["status"] == "WAITING_TRIGGER":
        status = "WAIT_TRIGGER_REQUIRED"
        blockers.append("typed NEW_EVIDENCE trigger is required before WAIT can resume")
    return ResumeInspection(
        status=status,
        run_id=run_id,
        current_node=state["current_node"],
        last_completed_node=state["last_completed_node"],
        next_allowed_nodes=state["next_allowed_nodes"],
        waiting=state.get("waiting"),
        blockers=blockers,
    )


def build_resume_brief(inspection: ResumeInspection) -> str:
    completed = inspection.last_completed_node or "尚未完成第一个节点"
    next_action = "、".join(inspection.next_allowed_nodes) or "等待当前节点形成有效结果"
    waiting = inspection.waiting.get("reason") if inspection.waiting else "目前没有外部等待"
    if inspection.blockers:
        blocker = "；".join(inspection.blockers)
        return (
            f"正在处理 Run {inspection.run_id}，当前停在 {inspection.current_node}。"
            f"最近完成的是 {completed}，{waiting}。发现会阻止直接继续的变化：{blocker}。"
            "下一步应先修复或确认这些 exact 引用，不能沿旧状态盲目继续。"
        )
    return (
        f"正在处理 Run {inspection.run_id}，当前停在 {inspection.current_node}。"
        f"最近完成的是 {completed}，{waiting}。下一步允许进入：{next_action}。"
    )
