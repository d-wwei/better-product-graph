# Problem Synthesis — Agent Instructions v0.2

Run only through the public Skill and Controller after a completed `READY_FOR_SYNTHESIS` learning state. Write an exact-version Problem Definition Candidate that states user/context, desired outcome, obstacle, impact, strongest evidence and counterevidence, assumptions, Unknowns, current MVU, disagreement, and action implications.

Do not search again, prompt the PM, resolve Unknowns, choose an action, or smuggle a proposed solution into the problem. If a material gap could change user, scenario, goal, obstacle, impact, or boundary, return to Learning with a new Agent-authored MVU. A completed Candidate is reviewable, not Problem Ready and not a Product Decision.

Write the final artifact bytes before computing every submitted hash. If validation rejects the artifact, correct the payload and resubmit the same attempt_id; do not invent a new attempt or treat the rejected submission as committed.

Copy the dispatch's exact `resource_refs` to the top-level Node Result. Write the Candidate first, compute its final hash, include the same exact ref in top-level `artifact_refs`, and return this complete `semantic_output`:

<!-- problem-synthesize-semantic-output-contract -->
```json
{
  "candidate_ref": {
    "role": "problem_definition_candidate",
    "path": "COPY_EXACT_PROJECT_RELATIVE_CANDIDATE_PATH",
    "hash": "COPY_SHA256_OF_FINAL_CANDIDATE_BYTES",
    "version": 1
  },
  "problem_definition": "谁在什么场景下试图完成什么、受到什么阻碍、为什么值得处理，以及当前证据、反证和未知"
}
```
