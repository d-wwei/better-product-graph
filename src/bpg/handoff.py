"""Local Handoff view over an exact Released artifact set; never dispatches."""

from __future__ import annotations

from typing import Any

from .documents import ArtifactSet, hash_tree


def prepare_local_handoff(released: ArtifactSet) -> dict[str, Any]:
    if released.status != "RELEASED" or hash_tree(released.path) != released.tree_hash:
        raise ValueError("Handoff requires an exact unchanged Released artifact set")
    return {
        "status": "LOCAL_READY",
        "source": {
            "path": str(released.path),
            "tree_hash": released.tree_hash,
            "document_hash": released.document_hash,
            "version": released.version,
        },
        "next_action": "需要外部写入时，另行满足目标 Connector 的权限与 receipt 合同。",
        "sent": False,
        "connector_status": "NOT_CONFIGURED",
        "external_approval": "NOT_CLAIMED",
        "engineering_received": "NOT_CLAIMED",
        "tests_passed": "NOT_CLAIMED",
    }
