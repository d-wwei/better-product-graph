---
document: Better Product Graph 通用 PRD 模板 v0.3 设计处置
version: 0.3-draft
status: INVALIDATED
date: 2026-08-24
predecessor: ./DESIGN_NOTES_v0.2.md
replacement_writing_profile: ../../../policies/document-experience/PRD_WRITING_PROFILE_v0.1.json
---

# 通用 PRD 模板 v0.3：撤回说明

## 1. 结论

“通过模板 v0.3 改善 PRD 表达”的方向已撤回。

原模板结构不是主要问题。真正的问题是大段文字堆叠、主次不清、技术术语过早出现、中英文夹杂、假设读者已经理解项目背景，以及缺少真正帮助理解的配图。

这些都是横向表达问题，不应由某一个 PRD 模板版本独占。

## 2. 为什么模板耦合是错误设计

模板回答“PRD 必须包含哪些产品语义，以及放在哪些栏目”。写作规范回答“面向某类读者时，怎样把这些内容讲清楚”。

如果把二者写在同一个文件里：

- 换模板可能意外换掉表达标准。
- 更新表达标准会制造没有结构变化的模板新版本。
- 不同项目模板会复制同一套规则并逐渐漂移。
- Skill、Renderer 和 Validator 无法独立绑定确切的 Template 与 Document Experience Profile。

这与已确认的 BPG Document Experience 架构冲突。架构已经明确：模板决定怎么排，Policy 决定至少让人理解什么，Profile 决定某类产物需要多重的表达。

## 3. 新的归属关系

- **结构真源**：`PRD_TEMPLATE_v0.2.md`，继续作为 `general@0.2.0 / RELEASED_DEFAULT`。
- **表达真源**：`policies/document-experience/PRD_WRITING_GUIDE_v0.1.md`。
- **组合与受众配置**：`policies/document-experience/PRD_WRITING_PROFILE_v0.1.json`。
- **执行者**：Skill / Host Agent 读取确切 Policy、Profile 和 Template 后写作。
- **检查者**：Validator 检查确定性绑定与最低理解项；Readability Reviewer 判断术语堆叠、主次和图示质量。

只把规则写进 Skill 也不够，因为 Agent 可能遗漏、使用过期规则或无法证明绑定了哪个版本。Skill 应执行独立规范，而不是成为规范的唯一真源。

## 4. 历史文件处置

- `PRD_TEMPLATE_v0.3.md` 只保留撤回说明，不再是可用模板。
- 原表达耦合实验归档到 `experiments/PRD_TEMPLATE_v0.3_expression-coupled_INVALIDATED.md`。
- `OUTPUT_CONTRACT_v0.3.json` 保留为未注册的历史草案，不用于生成或校验新 PRD。
- 旧的结构重排 Bootstrap 预览继续保持 `INVALIDATED`。
- 新的 Bootstrap 表达预览绑定“模板 v0.2 + 写作 Profile v0.1”，二者分别记录确切路径、版本和 hash。

## 5. 生命周期边界

撤回模板 v0.3 这件事没有修改或取代任何正式 PRD。后续独立冻结动作已经注册 Runtime Profile，并让 PRD 生成、归档和 Ready 校验绑定确切表达版本；它仍不恢复模板 v0.3，也不改变任何既有正式 PRD 的生命周期状态。

独立写作 Profile 已冻结为 `prd-plain-language-zh-CN@0.1.0 / RELEASED_DEFAULT`，但没有真实产品经理阅读测试，不能宣称可读性已经验证通过。这个状态变化不恢复已失效的模板 v0.3，也不改变 `general@0.2.0` 的结构。
