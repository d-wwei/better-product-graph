# Bug Baseline Check — Agent Instructions v0.1

Run only through the public Skill and Controller. Compare the exact current baseline with observed behavior and submit one classification: `IMPLEMENTATION_DEVIATION`, `PRODUCT_LOGIC_DEFECT`, or `SPEC_AMBIGUITY`.

Use `IMPLEMENTATION_DEVIATION` only when an exact current baseline exists, expected and actual behavior differ, no new product rule is required, acceptance criteria are decidable, and no material conflict exists. Otherwise choose the semantically correct alternative yourself and explain the next action. The program validates your submitted contract but will never reclassify it or invent missing product semantics.
