# Product Graph Evals v0.1 — Legacy Disposition v0.2

Status: **LEGACY / DOCUMENT-ONLY / NOT A V1.4 ACCEPTANCE BASELINE**

结论：`evals/product-graph` v0.1 的既有文件保持原字节不变，只作为 v0.2 迁移来源与历史对照。它没有在当前 runtime 执行，不得记录 PASS，也不得从文件存在、Schema 可读或 Plugin Contract PASS 推导产品验收结果。

迁移处置：

- `ProductSpecPackage` → 当前 versioned PRD Candidate、Released artifact set 与 local Handoff 合同；旧字段不再是正式状态。
- `owner_approval` / `PRODUCT_OWNER_APPROVED` → 已退役的重复确认；当前 Product Decision 保留一次有权结果，PRD Ready 是程序化完整性计算。
- `DEV_ACCEPTED` / `TEST_ACCEPTED` → 外部消费者状态；本地候选不得声称已接收、已批准或测试通过。
- Reviewer block / waiver → Reviewer 仅 advisory；专业外置阻断由项目 policy/外部系统负责。
- 旧 synthetic cases → 仅可作为迁移素材，不自动进入 Product Golden v0.2，也不贡献 PASS。

Provenance：冻结文档 `PRD_GRAPH_v1.4.md` §1.6 与 Roadmap v0.12 Wave 4。当前实现另建 `evals/product-golden-v0.2/`，不原位改写 v0.1。
