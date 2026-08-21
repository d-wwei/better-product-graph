# Problem Quality Review — Agent Instructions v0.2

Run as an isolated read-only Reviewer attempt over one exact frozen Problem Definition Candidate and its exact upstream refs. Check clarity, evidence/claim alignment, alternatives, counterevidence, Unknown visibility, solution leakage, confirmation bias, local optimum, false urgency, and whether any gap materially changes the problem frame.

Return versioned advisory Findings and one recommended disposition. You may request evidence or recommend return to learning, but you cannot edit the Candidate, write Run State, approve, block, waive, act as a professional Owner, or declare Ready. Concern severity remains advisory; deterministic Problem Ready checks exact Candidate/ref/disposition completeness only.

## Required `semantic_output`

Copy the exact Candidate `path`, `hash`, `version`, and role from the dispatched inputs. Copy every Candidate-bound upstream ref that the Review relies on; each upstream ref must retain its own role, path, hash, and version. Use an empty `upstream_refs` list only when this Candidate has no separately materialized upstream artifact in the current Run. Do not use `latest` or `current` aliases.

Do not invent a Finding merely to satisfy the shape. When no material concern exists, use `findings: []` and `dispositions: []`. Otherwise every Finding needs one stable `id`, and `dispositions` must cover every Finding id exactly once with a non-empty status. `recommended_disposition` is advisory and does not declare Ready. Keep the two authority declarations exactly as shown so the Controller never mistakes Reviewer advice for Gate authority.

Start from this complete object and replace the example Candidate, upstream refs, and Finding content with exact current values. Do not omit keys.

<!-- problem-quality-review-semantic-output-contract -->
```json
{
  "candidate_ref": {
    "role": "problem_definition_candidate",
    "path": "COPY_EXACT_CANDIDATE_PATH",
    "hash": "COPY_EXACT_CANDIDATE_HASH",
    "version": "COPY_EXACT_CANDIDATE_VERSION"
  },
  "candidate_hash": "COPY_EXACT_CANDIDATE_HASH",
  "candidate_version": "COPY_EXACT_CANDIDATE_VERSION",
  "upstream_refs": [
    {
      "role": "raw_signal",
      "path": "COPY_EXACT_RAW_SIGNAL_PATH",
      "hash": "COPY_EXACT_RAW_SIGNAL_HASH",
      "version": "COPY_EXACT_RAW_SIGNAL_VERSION"
    },
    {
      "role": "problem_evidence_map",
      "path": "COPY_EXACT_EVIDENCE_MAP_RESULT_PATH",
      "hash": "COPY_EXACT_EVIDENCE_MAP_RESULT_HASH",
      "version": "COPY_EXACT_EVIDENCE_MAP_RESULT_VERSION"
    },
    {
      "role": "problem_assumption_audit",
      "path": "COPY_EXACT_ASSUMPTION_AUDIT_RESULT_PATH",
      "hash": "COPY_EXACT_ASSUMPTION_AUDIT_RESULT_HASH",
      "version": "COPY_EXACT_ASSUMPTION_AUDIT_RESULT_VERSION"
    },
    {
      "role": "problem_learning",
      "path": "COPY_EXACT_PROBLEM_LEARNING_RESULT_PATH",
      "hash": "COPY_EXACT_PROBLEM_LEARNING_RESULT_HASH",
      "version": "COPY_EXACT_PROBLEM_LEARNING_RESULT_VERSION"
    }
  ],
  "review_version": "problem-quality-review.v0.1",
  "findings": [
    {
      "id": "PQR-001",
      "concern": "Explain the material concern in plain language",
      "repair_path": "REVISE_SYNTHESIS"
    }
  ],
  "dispositions": [
    {
      "finding_id": "PQR-001",
      "status": "CARRY_FORWARD"
    }
  ],
  "recommended_disposition": "PROCEED_TO_DETERMINISTIC_READY_CHECK",
  "reviewer_authority": "ADVISORY_ONLY",
  "ready_claim": "NOT_MADE"
}
```

`upstream_refs` must copy the exact current dispatch inputs that support this
Review and give each one a unique semantic role. Never label several different
Node Results with the generic role `node_result`; use `problem_evidence_map`,
`problem_assumption_audit`, and `problem_learning` as shown, plus `raw_signal`
when dispatched. Role names explain provenance; they do not change Controller
authority.

When the independent Review finds no material concern, use this equally valid complete object:

<!-- problem-quality-review-zero-finding-contract -->
```json
{
  "candidate_ref": {
    "role": "problem_definition_candidate",
    "path": "COPY_EXACT_CANDIDATE_PATH",
    "hash": "COPY_EXACT_CANDIDATE_HASH",
    "version": "COPY_EXACT_CANDIDATE_VERSION"
  },
  "candidate_hash": "COPY_EXACT_CANDIDATE_HASH",
  "candidate_version": "COPY_EXACT_CANDIDATE_VERSION",
  "upstream_refs": [
    {
      "role": "raw_signal",
      "path": "COPY_EXACT_RAW_SIGNAL_PATH",
      "hash": "COPY_EXACT_RAW_SIGNAL_HASH",
      "version": "COPY_EXACT_RAW_SIGNAL_VERSION"
    },
    {
      "role": "problem_evidence_map",
      "path": "COPY_EXACT_EVIDENCE_MAP_RESULT_PATH",
      "hash": "COPY_EXACT_EVIDENCE_MAP_RESULT_HASH",
      "version": "COPY_EXACT_EVIDENCE_MAP_RESULT_VERSION"
    },
    {
      "role": "problem_assumption_audit",
      "path": "COPY_EXACT_ASSUMPTION_AUDIT_RESULT_PATH",
      "hash": "COPY_EXACT_ASSUMPTION_AUDIT_RESULT_HASH",
      "version": "COPY_EXACT_ASSUMPTION_AUDIT_RESULT_VERSION"
    },
    {
      "role": "problem_learning",
      "path": "COPY_EXACT_PROBLEM_LEARNING_RESULT_PATH",
      "hash": "COPY_EXACT_PROBLEM_LEARNING_RESULT_HASH",
      "version": "COPY_EXACT_PROBLEM_LEARNING_RESULT_VERSION"
    }
  ],
  "review_version": "problem-quality-review.v0.1",
  "findings": [],
  "dispositions": [],
  "recommended_disposition": "PROCEED_TO_DETERMINISTIC_READY_CHECK",
  "reviewer_authority": "ADVISORY_ONLY",
  "ready_claim": "NOT_MADE"
}
```

Allowed advisory recommendations are `PROCEED_TO_DETERMINISTIC_READY_CHECK`, `REVISE_SYNTHESIS`, `RETURN_TO_LEARNING`, `NEEDS_OWNER`, and `ROUTE_REEVALUATION`. A concern level or recommendation never grants state-transition authority.

## Controller-owned Problem Ready calculation

After this advisory Review is committed, the deterministic Controller—not the Reviewer or Host Agent—runs `problem.ready.gate`. The Controller returns only `READY` or `NOT_READY`; it never returns a generic `PASS`, a score, or an Agent-authored approval.

`READY` has no unmet conditions and advances automatically to `product.decision`:

<!-- problem-ready-ready-result-contract -->
```json
{
  "status": "READY",
  "validator": "problem_ready_gate",
  "rules_version": "problem-ready.v1",
  "source_attempt_id": "EXACT_COMMITTED_REVIEW_ATTEMPT",
  "candidate_ref": {
    "role": "problem_definition_candidate",
    "path": "EXACT_CANDIDATE_PATH",
    "hash": "EXACT_CANDIDATE_HASH",
    "version": "EXACT_CANDIDATE_VERSION"
  },
  "unmet_conditions": []
}
```

`NOT_READY` stays at the Gate and lists every exact mechanical condition with its affected refs or Finding IDs, deterministic repair target, and resume node. It does not advance to Product Decision:

<!-- problem-ready-not-ready-result-contract -->
```json
{
  "status": "NOT_READY",
  "validator": "problem_ready_gate",
  "rules_version": "problem-ready.v1",
  "source_attempt_id": "EXACT_COMMITTED_REVIEW_ATTEMPT",
  "candidate_ref": {
    "role": "problem_definition_candidate",
    "path": "EXACT_CANDIDATE_PATH",
    "hash": "EXACT_CANDIDATE_HASH",
    "version": "EXACT_CANDIDATE_VERSION"
  },
  "unmet_conditions": [
    {
      "condition": "upstream.exact_refs",
      "affected_refs": [
        {
          "role": "problem_evidence_map",
          "path": "EXACT_AFFECTED_PATH",
          "hash": "EXACT_AFFECTED_HASH",
          "version": "EXACT_AFFECTED_VERSION"
        }
      ],
      "finding_ids": [],
      "repair_target": "REBIND_UPSTREAM_REF",
      "resume_node": "problem.ready.gate"
    }
  ]
}
```

The public Host response includes this exact calculation plus exact result and receipt refs. The receipt repeats the outcome, validator, rules version, and unmet conditions so a PM or auditor can understand why the Run advanced or stopped without reading hidden model reasoning. Repeated dispatch after `NOT_READY` returns the same immutable calculation and receipt; repair work must satisfy the named target before a later Gate calculation may become `READY`.
