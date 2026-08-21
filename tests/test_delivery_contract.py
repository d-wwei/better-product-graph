from __future__ import annotations

import unittest
from copy import deepcopy

from src.bpg.delivery_contract import (
    DeliveryContractError,
    derive_active_scope_ref,
    derive_spec_traceability,
    evaluate_runtime_input_readiness,
    validate_candidate_delivery_contract,
)
from src.bpg.storage import canonical_json_bytes, sha256_bytes
from tests.test_planning_contract import complete_plan
from tests.test_prd_contract import prd_submission


def exact(path: str, digest: str, version: int = 1) -> dict:
    return {"path": path, "hash": f"sha256:{digest}", "version": version}


def planning_result() -> tuple[dict, dict]:
    plan_ref = exact("artifacts/product-plan-v1.md", "plan")
    plan = complete_plan()
    plan["prd_matrix"][0]["planned_prd_id"] = "PRD-CHECKOUT-001"
    result = {
        "schema_version": "node-result.v1",
        "node_id": "product.planning",
        "attempt_id": "attempt-plan-authority",
        "producer": {"kind": "HOST_AGENT"},
        "instruction_ref": "references/atomic-skills/product-planning/INSTRUCTIONS.md",
        "instruction_hash": "sha256:instruction",
        "input_refs": ["decision.json"],
        "input_hashes": {"decision.json": "sha256:decision"},
        "semantic_output": plan,
        "artifact_refs": [{"role": "product_plan", **plan_ref}],
    }
    return result, plan_ref


class DeliveryContractTests(unittest.TestCase):
    def test_controller_derives_stable_scope_and_ignores_module_dependency_order(self) -> None:
        result, plan_ref = planning_result()
        expected = derive_active_scope_ref(result, plan_ref, "PRD-CHECKOUT-001")
        reordered = deepcopy(result)
        reordered["semantic_output"]["slices"][0]["modules"].reverse()
        reordered["semantic_output"]["slices"][0]["dependencies"].reverse()

        self.assertEqual(
            derive_active_scope_ref(reordered, plan_ref, "PRD-CHECKOUT-001"),
            expected,
        )
        self.assertEqual(expected["slice_id"], "slice-1")
        self.assertNotIn("candidate_version", expected)

    def test_every_authoritative_scope_field_changes_the_scope_hash(self) -> None:
        result, plan_ref = planning_result()
        original = derive_active_scope_ref(result, plan_ref, "PRD-CHECKOUT-001")
        mutations = {
            "id": "slice-renamed",
            "user_outcome": "different outcome",
            "modules": ["checkout"],
            "iteration": "iteration-other",
            "dependencies": [],
            "validation": "different validation",
            "split_reason": "different split",
            "delivery_intent": "EXPERIMENT",
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                changed = deepcopy(result)
                changed["semantic_output"]["slices"][0][field] = replacement
                if field == "id":
                    changed["semantic_output"]["prd_matrix"][0]["slice_id"] = replacement
                if field == "iteration":
                    changed["semantic_output"]["iterations"].append(
                        {
                            "id": replacement,
                            "outcome": "changed but valid iteration",
                            "end_to_end": True,
                            "validation": "changed iteration validation",
                            "stop_condition": "scope reconciliation",
                        }
                    )
                    changed["semantic_output"]["prd_matrix"][0]["iteration"] = replacement
                self.assertNotEqual(
                    derive_active_scope_ref(changed, plan_ref, "PRD-CHECKOUT-001")[
                        "scope_hash"
                    ],
                    original["scope_hash"],
                )

    def test_inactive_or_ineligible_slice_cannot_become_active_scope(self) -> None:
        for field in ("activated", "eligible"):
            with self.subTest(field=field):
                result, plan_ref = planning_result()
                result["semantic_output"]["slices"][0][field] = False
                with self.assertRaisesRegex(
                    DeliveryContractError, "activated=true|eligible=true|not Ready"
                ):
                    derive_active_scope_ref(
                        result, plan_ref, "PRD-CHECKOUT-001"
                    )

    def test_traceability_is_derived_from_committed_origin_not_caller_aliases(self) -> None:
        plan_ref = exact("artifacts/product-plan-v1.md", "plan")
        slice_ref = exact("runs/run-clean/product-planning-result.json", "slice")
        authoritative = {
            "plan": {
                **plan_ref,
                "role": "product_plan",
                "node_id": "product.planning",
                "attempt_id": "attempt-plan-authority",
            },
            "slice": {
                **slice_ref,
                "role": "node_result",
                "node_id": "product.planning",
                "attempt_id": "attempt-plan-authority",
            },
        }
        derived = derive_spec_traceability(
            [("product_plan", plan_ref), ("slice", slice_ref)], authoritative
        )

        self.assertEqual(derived["schema_version"], "spec-traceability.v1")
        self.assertEqual(
            {item["origin_attempt_id"] for item in derived["refs"]},
            {"attempt-plan-authority"},
        )
        forged = deepcopy(derived)
        forged["refs"][0]["role"] = "portable_business_input"
        forged["refs"][0]["origin_attempt_id"] = "attempt-forged"
        metadata = prd_submission()["semantic_output"]["metadata"]
        metadata["spec_traceability"] = forged
        with self.assertRaisesRegex(DeliveryContractError, "spec_traceability"):
            validate_candidate_delivery_contract(
                metadata,
                expected_active_scope=metadata["active_scope_ref"],
                expected_traceability=derived,
            )

    def test_traceability_role_is_bound_to_committed_role_and_origin(self) -> None:
        roadmap_ref = exact("runs/run-clean/roadmap.json", "roadmap")
        authoritative = {
            "roadmap": {
                **roadmap_ref,
                "role": "node_result",
                "node_id": "evidence.collect",
                "attempt_id": "attempt-roadmap",
            }
        }

        with self.assertRaisesRegex(DeliveryContractError, "role|origin"):
            derive_spec_traceability(
                [("product_plan", roadmap_ref)], authoritative
            )

    def test_fresh_project_runtime_readiness_needs_only_workspace_and_signal(self) -> None:
        contract = prd_submission()["semantic_output"]["metadata"][
            "product_runtime_inputs"
        ]
        ready = evaluate_runtime_input_readiness(
            contract,
            {"project_workspace": "/tmp/new-project", "product_signal": "raw idea"},
        )
        self.assertEqual(ready, {"status": "READY", "missing": []})
        self.assertNotIn("run-ad2ec7712339", canonical_json_bytes(ready).decode())

        missing_signal = evaluate_runtime_input_readiness(
            contract, {"project_workspace": "/tmp/new-project"}
        )
        self.assertEqual(
            missing_signal,
            {
                "status": "NOT_READY",
                "missing": [
                    {"input_id": "product_signal", "on_missing": "REQUEST_SIGNAL"}
                ],
            },
        )
        missing_workspace = evaluate_runtime_input_readiness(
            contract, {"product_signal": "raw idea"}
        )
        self.assertEqual(
            missing_workspace,
            {
                "status": "NOT_READY",
                "missing": [
                    {"input_id": "project_workspace", "on_missing": "FAIL_CLOSED"}
                ],
            },
        )
        empty_values = evaluate_runtime_input_readiness(
            contract, {"project_workspace": "", "product_signal": None}
        )
        self.assertEqual(
            empty_values,
            {
                "status": "NOT_READY",
                "missing": [
                    {"input_id": "project_workspace", "on_missing": "FAIL_CLOSED"},
                    {"input_id": "product_signal", "on_missing": "REQUEST_SIGNAL"},
                ],
            },
        )

    def test_nested_spec_value_leak_is_rejected_even_under_a_forged_role(self) -> None:
        metadata = deepcopy(prd_submission()["semantic_output"]["metadata"])
        metadata["product_runtime_inputs"]["required"].append(
            {
                "input_id": "portable_alias",
                "kind": "BUSINESS_INPUT",
                "resolver": "PROJECT_CONFIG",
                "binding_scope": "PROJECT",
                "version_policy": "business-contract.v1",
                "on_missing": "FAIL_CLOSED",
                "configuration": {
                    "unrelated_label": metadata["spec_traceability"]["refs"][0]["path"]
                },
            }
        )
        with self.assertRaisesRegex(
            DeliveryContractError, "SPEC_REF_IN_RUNTIME_INPUTS|product_runtime_inputs"
        ):
            validate_candidate_delivery_contract(
                metadata,
                expected_active_scope=metadata["active_scope_ref"],
                expected_traceability=metadata["spec_traceability"],
            )

    def test_nested_spec_key_and_lifecycle_aliases_are_rejected(self) -> None:
        metadata = deepcopy(prd_submission()["semantic_output"]["metadata"])
        metadata["product_runtime_inputs"]["required"].append(
            {
                "input_id": "portable_alias",
                "kind": "BUSINESS_INPUT",
                "resolver": "PROJECT_CONFIG",
                "binding_scope": "PROJECT",
                "version_policy": "business-contract.v1",
                "on_missing": "FAIL_CLOSED",
                "configuration": {
                    metadata["spec_traceability"]["refs"][0]["path"]: "opaque",
                    "source_candidate_version": "v0.1",
                    "problem_ready_receipt_hash": "sha256:untrusted-alias",
                },
            }
        )
        with self.assertRaisesRegex(
            DeliveryContractError, "SPEC_REF|LIFECYCLE_REF|product_runtime_inputs"
        ):
            validate_candidate_delivery_contract(
                metadata,
                expected_active_scope=metadata["active_scope_ref"],
                expected_traceability=metadata["spec_traceability"],
            )

    def test_complete_typed_bpg_exception_is_allowed_but_current_run_path_is_not(self) -> None:
        metadata = deepcopy(prd_submission()["semantic_output"]["metadata"])
        typed = {
            "input_id": "policy_catalog",
            "kind": "BPG_ARTIFACT",
            "resolver": "PROJECT_ARTIFACT_REGISTRY",
            "binding_scope": "PROJECT",
            "version_policy": "pinned-compatible.v1",
            "on_missing": "FAIL_CLOSED",
            "bpg_artifact_exception": {
                "business_reason": "The shipped product evaluates a customer-owned policy catalog.",
                "portable_resolver": "PROJECT_ARTIFACT_REGISTRY",
                "project_binding": "PROJECT",
                "version_policy": "pinned-compatible.v1",
                "on_unavailable": "FAIL_CLOSED",
            },
        }
        metadata["product_runtime_inputs"]["required"].append(typed)
        validate_candidate_delivery_contract(
            metadata,
            expected_active_scope=metadata["active_scope_ref"],
            expected_traceability=metadata["spec_traceability"],
        )

        metadata["product_runtime_inputs"]["required"][-1]["configuration"] = {
            "path": ".better-product-graph/runs/run-clean/current/policy.json"
        }
        with self.assertRaisesRegex(DeliveryContractError, "current|SPEC_REF"):
            validate_candidate_delivery_contract(
                metadata,
                expected_active_scope=metadata["active_scope_ref"],
                expected_traceability=metadata["spec_traceability"],
            )

        for bypass in (
            {"configuration": {"path": "file:///Users/example/secret"}},
            {"resolver": "PROJECT_CONFIG?version=latest"},
            {"resolver": "registry:current"},
        ):
            with self.subTest(bypass=bypass):
                attacked = deepcopy(prd_submission()["semantic_output"]["metadata"])
                attacked["product_runtime_inputs"]["required"].append(
                    {**typed, **bypass}
                )
                with self.assertRaisesRegex(
                    DeliveryContractError, "portable|current|latest"
                ):
                    validate_candidate_delivery_contract(
                        attacked,
                        expected_active_scope=attacked["active_scope_ref"],
                        expected_traceability=attacked["spec_traceability"],
                    )

        optional = deepcopy(prd_submission()["semantic_output"]["metadata"])
        optional["product_runtime_inputs"]["optional"].append(
            {
                **typed,
                "configuration": {
                    "path": optional["spec_traceability"]["refs"][0]["path"]
                },
            }
        )
        with self.assertRaisesRegex(DeliveryContractError, "SPEC_REF"):
            validate_candidate_delivery_contract(
                optional,
                expected_active_scope=optional["active_scope_ref"],
                expected_traceability=optional["spec_traceability"],
            )

    def test_typed_bpg_exception_cannot_contradict_the_runtime_item(self) -> None:
        metadata = deepcopy(prd_submission()["semantic_output"]["metadata"])
        metadata["product_runtime_inputs"]["required"].append(
            {
                "input_id": "policy_catalog",
                "kind": "BPG_ARTIFACT",
                "resolver": "HOST_LOCAL_CACHE",
                "binding_scope": "MACHINE",
                "version_policy": "host-build.v1",
                "on_missing": "IGNORE",
                "bpg_artifact_exception": {
                    "business_reason": "customer-owned policy catalog",
                    "portable_resolver": "PROJECT_ARTIFACT_REGISTRY",
                    "project_binding": "PROJECT",
                    "version_policy": "pinned-compatible.v1",
                    "on_unavailable": "FAIL_CLOSED",
                },
            }
        )
        with self.assertRaisesRegex(
            DeliveryContractError, "exception|portable|binding|version|unavailable"
        ):
            validate_candidate_delivery_contract(
                metadata,
                expected_active_scope=metadata["active_scope_ref"],
                expected_traceability=metadata["spec_traceability"],
            )


if __name__ == "__main__":
    unittest.main()
