# Evidence — Agent Instructions v0.1

Run only through the public Skill and Controller. Start from exact local Signal, Knowledge, Product Memory, Decision, Roadmap, PRD, Eval, Incident/Bug, behavior, experiment, contract, and documentation refs. Research AI-accessible authorized sources before asking a Junior PM to retrieve facts the Agent can obtain.

Preserve immutable provenance and distinguish `SOURCE_ASSERTION`, `OBSERVATION`, `VERIFIED_CLAIM`, `INFERENCE`, `ASSUMPTION`, `PREFERENCE`, `PROPOSAL`, `UNKNOWN`, and `AUTHORIZATION`. Authority can authorize an action but cannot turn a sponsor statement into verified user evidence. Record supports, contradicts, only-proves, and may-change relationships without raising confidence because several analyses repeat the same source.

Submit a `HOST_AGENT` Node Result bound to exact instruction/input hashes. Missing or inaccessible sources remain explicit Unknowns or Evidence Requests.

At `evidence.collect`, return this complete `semantic_output`. `sources` may be empty only when the record explicitly explains that no authorized source was available; never fabricate a source:

<!-- evidence-collect-semantic-output-contract -->
```json
{
  "sources": [
    {
      "source_ref": "COPY_EXACT_AUTHORIZED_SOURCE_REF",
      "status": "AVAILABLE",
      "summary": "这份来源实际能够证明什么"
    }
  ]
}
```

At `evidence.map`, return this complete `semantic_output`. Every claim needs a non-empty `source_ref`. `role` must be exactly one of `SOURCE_ASSERTION`, `OBSERVATION`, `VERIFIED_CLAIM`, `INFERENCE`, `ASSUMPTION`, `PREFERENCE`, `PROPOSAL`, `UNKNOWN`, or `AUTHORIZATION`:

<!-- evidence-map-semantic-output-contract -->
```json
{
  "claims": [
    {
      "claim": "用户在失败后无法判断是否应该重试",
      "role": "SOURCE_ASSERTION",
      "source_ref": "COPY_EXACT_SOURCE_REF",
      "confidence": "SOURCE_REPORTED"
    }
  ]
}
```
