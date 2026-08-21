# ADR-002: Frozen template public derivation v0.1

状态：Accepted for local RC
日期：2026-08-20
依据：Autopilot public Plugin validator、exact upstream fallback requirement
上一版本：无

## 结论

仓库在 `src/core/templates/fallback/product-prd-template.md` 保留冻结 upstream fallback 的 exact 8085 bytes，source SHA-256 为 `ffe22669d8cff3ed7b94566d6cefa3d3381b9d4ce34d99a14039576b730dafa8`。不得直接改写该文件。

冻结文件包含一行上游作者机器的绝对 `/Users/...` provenance 路径，skills-only public Plugin validator 会拒绝该路径。source→dist 构建因此执行唯一、具名、fail-closed 的 `redact-upstream-local-path-v1` 派生：只把该 exact provenance 行中的本机路径替换为 `[redacted upstream author machine path]`，不改变模板正文语义。

构建必须同时：

- 校验 exact source hash 和 exact 待替换文本只出现一次；
- 在 installed `profiles.json` 中记录 `source_sha256` 并把 active `sha256` 更新为派生文件 hash；
- 在 `build-manifest.json` 记录 transform id、relative target、source/output hashes；
- 通过 byte-determinism、installed identity 和 public validator；
- 任一 source/text/profile binding 漂移时失败，不做模糊替换。

## 边界

该派生不是模板升级、promotion 或静默迁移。项目 Template Profile 仍按 exact installed hash 显式 pin/rollback；general v0.1 仍为 Draft/Bootstrap candidate。冻结架构与 Roadmap 未修改。
