from __future__ import annotations

import json
from typing import Any

from src.bpg.state_controller import StateController
from src.bpg.storage import canonical_json_bytes


def position_run_internal(
    controller: StateController,
    run_id: str,
    node_id: str,
    routes: list[str],
    *,
    artifact_refs: dict[str, dict[str, Any]] | None = None,
    state_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Internal-only test setup that advances snapshot and event authority together."""

    state = controller.load_state(run_id)
    next_state = json.loads(canonical_json_bytes(state))
    next_state.update(
        {
            "status": "ACTIVE",
            "current_node": node_id,
            "last_completed_node": state["current_node"],
            "next_allowed_nodes": routes,
            "state_version": state["state_version"] + 1,
        }
    )
    if artifact_refs is not None:
        next_state["artifact_refs"] = artifact_refs
    if state_updates is not None:
        next_state.update(json.loads(canonical_json_bytes(state_updates)))
    controller._commit_state_event(
        run_id,
        state,
        next_state,
        {
            "event_type": "NODE_TRANSITION_COMMITTED",
            "actor": "state-controller",
            "run_id": run_id,
            "from_node": state["current_node"],
            "to_node": node_id,
            "attempt_id": f"internal-test-fixture-{node_id}",
            "before_state_version": state["state_version"],
            "after_state_version": next_state["state_version"],
        },
        transaction_id=(
            f"internal-test-fixture-{node_id.replace('.', '-')}-"
            f"v{next_state['state_version']}"
        ),
    )
    return controller.load_state(run_id)
