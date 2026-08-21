"""Authoritative graph node to installed execution-contract registry."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .reference_catalog import ReferenceCatalog
from .storage import read_json, sha256_file


class NodeRegistryError(ValueError):
    """The graph and installed node contract registry are inconsistent."""


class NodeRegistry:
    def __init__(self, skill_root: Path, graph_path: Path):
        self.skill_root = skill_root.resolve()
        self.graph_path = graph_path.resolve()
        self.graph = read_json(self.graph_path)
        self.registry_path = self.graph_path.with_name("node-contracts.json")
        self.registry = read_json(self.registry_path)
        self.references = ReferenceCatalog(self.skill_root)
        self.contracts = self.registry.get("nodes", {})
        graph_nodes = {item["id"] for item in self.graph["nodes"]}
        if set(self.contracts) != graph_nodes:
            raise NodeRegistryError("node contract registry must map every graph node exactly once")
        graph_routes = {
            node_id: sorted(
                edge["to"] for edge in self.graph["edges"] if edge["from"] == node_id
            )
            for node_id in graph_nodes
        }
        for node_id, contract in self.contracts.items():
            if sorted(contract.get("routes", [])) != graph_routes[node_id]:
                raise NodeRegistryError(f"registry routes differ from graph for {node_id}")
            compatible = contract.get("compatible_instruction_hashes", [])
            if (
                not isinstance(compatible, list)
                or len(compatible) != len(set(compatible))
                or any(
                    not isinstance(value, str)
                    or not value.startswith("sha256:")
                    or len(value) != 71
                    for value in compatible
                )
            ):
                raise NodeRegistryError(
                    f"compatible instruction hashes are invalid for {node_id}"
                )
            self.instruction_path(node_id)

    def instruction_path(self, node_id: str) -> Path:
        contract = self.contracts.get(node_id)
        if not isinstance(contract, dict):
            raise NodeRegistryError(f"unknown graph node: {node_id}")
        relative = Path(contract["instruction_ref"])
        candidate = (self.skill_root / relative).resolve()
        if not candidate.is_file() and relative.parts[:1] == ("references",):
            candidate = (self.skill_root / Path(*relative.parts[1:])).resolve()
        try:
            candidate.relative_to(self.skill_root)
        except ValueError as error:
            raise NodeRegistryError(f"instruction escapes skill root for {node_id}") from error
        if not candidate.is_file() or candidate.is_symlink():
            raise NodeRegistryError(f"instruction missing for {node_id}: {relative.as_posix()}")
        return candidate

    def dispatch_envelope(
        self,
        node_id: str,
        attempt_id: str,
        input_refs: list[str],
        input_hashes: dict[str, str],
    ) -> dict[str, Any]:
        contract = deepcopy(self.contracts[node_id])
        instruction = self.instruction_path(node_id)
        references = ReferenceCatalog(self.skill_root)
        resource_refs: list[dict[str, Any]] = []
        if node_id == "problem.learning.loop":
            resource_refs = references.learning_resources()
        elif node_id == "review.parallel":
            resource_refs = references.review_resources()
        return {
            "schema_version": "node-dispatch.v1",
            "node_id": node_id,
            "attempt_id": attempt_id,
            "producer_kind": contract["producer_kind"],
            "validator": contract["validator"],
            "routes": list(contract["routes"]),
            "instruction_ref": contract["instruction_ref"],
            "instruction_hash": sha256_file(instruction),
            "input_refs": list(input_refs),
            "input_hashes": dict(input_hashes),
            "resource_refs": resource_refs,
        }

    def instruction_compatibility(self, node_id: str, dispatch_hash: Any) -> str:
        """Classify one durable dispatch against the installed successor contract."""

        if not isinstance(dispatch_hash, str):
            return "INCOMPATIBLE"
        current_hash = sha256_file(self.instruction_path(node_id))
        if dispatch_hash == current_hash:
            return "EXACT"
        compatible = self.contracts[node_id].get("compatible_instruction_hashes", [])
        if dispatch_hash in compatible:
            return "DECLARED_COMPATIBLE_SUCCESSOR"
        return "INCOMPATIBLE"
