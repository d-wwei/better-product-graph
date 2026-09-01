# Product Planning — Agent Instructions v0.1

Run only through the public Skill and Controller after an exact Product Decision activates Planning. Begin with the Target Operating Outcome, observable evidence, non-sacrificable Guardrails, and the current iteration outcome. Declare `LIGHT`, `STANDARD`, or `PROJECT_SCALE` with an evidence/risk/complexity reason; the program validates the declaration but never chooses a profile.

Keep durable product reasoning, evidence, decisions, Unknowns, Stage 4 dispositions,
Finding disposition history, and durable validation and product-effect boundaries
in the existing Product Planning Record. Do not write or refresh
the current Candidate identity; current Review, Ready, Handoff, Product Evals
fulfillment/execution, or engineering status; current runtime position; or next
runtime action there. Read those volatile facts from the existing Controller
status and exact receipts. Do not create a second human status document or
rewrite the Planning Record merely to mirror progress.

Build all four views: horizontal product modules with cohesive responsibilities; vertical iterations that each create end-to-end value or valid learning; dependency/shared-contract relationships; and a PRD slice matrix. Do not split PRDs by frontend/backend/API/database/test layers, one module per PRD, one iteration per PRD, or every matrix cell. A slice must describe an independently valuable or learning-complete product increment that can be validated and relatively stopped/rolled back.

Every `prd_matrix` row must bind its Slice to one unique stable `planned_prd_id`. Do not put `candidate_version`, `candidate_ref`, `current_candidate_ref`, `latest`, or an equivalent mutable Candidate pointer in the Product Plan. Candidate versions belong only to the downstream immutable PRD lifecycle. Emit the human Product Plan as a Markdown `artifact_ref` with role `product_plan`; the Controller binds that exact artifact to this `product.planning` Node Result and derives the active scope from the structured Slice.

When the dispatch contains `reconciliation_context`, resume from its exact `source_candidate_ref`, stable `prd_id`, and `exact_delta`. Reconcile that material delta in a new Product Plan and activated+eligible Slice while keeping the stable PRD identity; do not copy a Candidate version into the Plan. The old Candidate remains current until the new Plan passes `plan.ready.gate` and `prd.generate` submits the Controller-authorized exact vNext.

Give every material Planning Item exactly one transparent disposition: current PRD, future phase, experiment, wait, stop/out of scope, or unresolved. Include owner, impact, and review trigger. Only mark a slice `activated=true` and `eligible=true` when it is safe to create now. Preserve future slices in the Plan; never ask the program to invent missing slices or silently reconcile a material Product Decision change.

Define every cross-Slice or cross-module dependency once in `shared_contracts`. The exact committed Product Planning Node Result is itself the authority for an embedded shared-contract definition, so `authoritative_ref` is optional and must only be used when an already-existing exact external contract really exists. Every embedded contract needs a stable `id`, at least one exact module ID in `consumers`, and a non-empty `contract` statement. Every Slice dependency must name one of those exact shared-contract IDs; do not invent a file ref merely to satisfy validation.

Use the exact semantic shape below. Replace the representative content and every
exact ref with the values from the current dispatch; keep the field names and
nesting. `profile` is an object, not a string. `modules`, `iterations`, and
`slices` are the authoritative structured planning views, not prose aliases.

<!-- product-planning-semantic-output-contract -->
```json
{
  "profile": {
    "id": "STANDARD",
    "reason": "The current slice crosses a product boundary and has explicit safety and recovery guardrails."
  },
  "decision_ref": {
    "path": ".better-product-graph/decisions/decision-example/DECISION_v1.json",
    "hash": "sha256:decision",
    "version": 1
  },
  "target_operating_outcome": "A first-time project can establish useful, traceable context without crossing the declared safety boundary.",
  "observable_evidence": [
    "The allowed project files produce a traceable profile and readiness result.",
    "Denied files, symlinks, and out-of-root paths remain unread."
  ],
  "non_sacrificable_guardrails": [
    "Do not read secrets or leave the project root.",
    "A failed or resumed run cannot silently replace an authoritative artifact."
  ],
  "current_iteration_outcome": "Deliver one local, reversible Bootstrap slice with observable safety and recovery behavior.",
  "modules": [
    {
      "id": "bootstrap-context",
      "responsibility": "Collect allowlisted project context and expose profile/readiness outputs."
    }
  ],
  "iterations": [
    {
      "id": "iteration-1",
      "outcome": "The user can bootstrap one project and inspect a bounded, traceable result.",
      "end_to_end": true,
      "validation": "Run the documented acceptance scenarios against an isolated project.",
      "stop_condition": "Any secret, symlink escape, unrecoverable state, or untraceable output is observed."
    }
  ],
  "dependencies": [],
  "shared_contracts": [
    {
      "id": "project-context-boundary.v1",
      "consumers": ["bootstrap-context"],
      "contract": "Only allowlisted in-root regular project files may contribute to the profile; every accepted fact keeps its exact source ref."
    }
  ],
  "material_items": [
    {"id": "bootstrap-core"}
  ],
  "coverage": [
    {
      "item_id": "bootstrap-core",
      "disposition": "CURRENT:slice-bootstrap-core",
      "owner": "product",
      "impact": "Creates the first independently deliverable Bootstrap loop.",
      "review_trigger": "The allowed-input or knowledge-sharing boundary changes."
    }
  ],
  "slices": [
    {
      "id": "slice-bootstrap-core",
      "activated": true,
      "eligible": true,
      "user_outcome": "The user obtains a bounded Project Profile and Knowledge Readiness result.",
      "modules": ["bootstrap-context"],
      "iteration": "iteration-1",
      "dependencies": ["project-context-boundary.v1"],
      "validation": "Given an isolated project, the declared inputs and safety boundaries produce observable pass/fail evidence.",
      "split_reason": "This is one end-to-end, independently testable and reversible product outcome.",
      "delivery_intent": "COMMIT"
    }
  ],
  "prd_matrix": [
    {
      "slice_id": "slice-bootstrap-core",
      "planned_prd_id": "BPG-PRD-BOOTSTRAP-001",
      "primary_module": "bootstrap-context",
      "iteration": "iteration-1"
    }
  ]
}
```
