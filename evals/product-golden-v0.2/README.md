# Product Golden Suite

Current draft: [PRODUCT_GOLDEN_SUITE_v0.2.md](PRODUCT_GOLDEN_SUITE_v0.2.md)

Version history: [CHANGELOG.md](CHANGELOG.md)

G01/G03/G04 的 fixture/contract `PASS` 仅证明输入包、oracle 隔离、expected envelope 与 rubric 可执行。没有真实 Host Agent harness 时，`agent_runtime_status` 和 `product_judgment_status` 必须为 `NOT_RUN`；不得把 deterministic fixture 通过写成 Agent 产品判断 PASS。
