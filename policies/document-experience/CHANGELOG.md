# Document Experience Policy / Profile Changelog

## PRD Writing Profile v0.1.0 — 2026-08-24

- 状态：`RELEASED / ACTIVE`；BPG 默认 PRD 表达 Profile 为 `prd-plain-language-zh-CN@0.1.0 / RELEASED_DEFAULT`。
- 写作规范：`PRD_WRITING_GUIDE_v0.1.md`，SHA-256 `sha256:2236d05d02cbe1901937a3365acb3a29f46ef7fb30c235c9df0c7865777360eb`。
- Profile：`PRD_WRITING_PROFILE_v0.1.json`，SHA-256 `sha256:a166a74d1ca0135f36efdfdc7e4a87b83a2125e7cefe4875e31b6b3d5e77bdd0`。
- 将 PRD 的 ELI5 表达规则从 `PRD_TEMPLATE_v0.3.md` 中解耦，形成独立写作规范与 Profile。
- 新增条件式内容处置：正文中真正不适用且不影响判断的内容直接省略；Checklist 保留检查项并记录“不适用”和具体理由；未知、未设计、未执行及必填语义不得借此省略。
- 模板继续决定栏目与产品语义承载位置；写作 Profile 独立决定受众、语言、表达密度、术语解释和必要配图要求。
- Skill / Host Agent 应读取确切 Policy、Profile 和 Template 后执行，不能只依赖模型记忆，也不能把规范全文复制进每个模板。
- 已生成逐字节一致的 Runtime Profile 与写作规范，并由 `document-experience-profiles.json` 记录默认版本和精确哈希；PRD 生成上下文必须单独绑定 Template 与 Document Experience。
- 没有真实产品经理阅读测试，不能宣称可读性已经验证通过。
