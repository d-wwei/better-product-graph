# Product PRD Template Reference

Canonical source: `d-wwei/Product-Prd-Skill` `references/default-prd-template.md`.
Local source used during creation: `/Users/admin/Documents/AI/agent better work/product-prd/references/default-prd-template.md`.

Use this as the default PRD-facing output structure when `better-product-plan`
produces a `brief` intended for PRD drafting, reviews a PRD, or hands scope to
`product-prd`.

## Section Order

1. 一、变更日志
2. 二、需求范围
3. 三、需求背景
4. 四、需求概述
5. 五、需求详述
6. 六、非功能性需求
7. 七、数据埋点
8. 八、多语言文案
9. 附录

## 一、变更日志

Provide a simple change table:

- 时间
- 变更人
- 主要变更内容

For a newly drafted PRD, add one initial line:

- 当前日期
- AI助理 / 需求提出人
- 初稿创建

## 二、需求范围

State:

- applicable terminals or platforms
- whether the same requirement is shared across multiple ends
- whether any ends must be split because of large interaction or rule differences

## 三、需求背景

### 3.1 产品三问法

Must answer:

- 根目的是什么
- 目标群体是谁，他们的核心问题和规模是什么
- 解决方案的 ROI 如何，是短期方案还是长期方案

### 3.2 相关OKR

Fill with:

- O
- KR

If the user does not provide formal OKRs, infer candidate objective and measurable KR, and label them as assumptions.

### 3.3 常规Checklist

Cover these items:

- 是否已了解同行产品的方案
- 是否已考虑 富途牛牛 & moomoo & 象象银行 的兼容性
- 是否已考虑 主推券商、归属市场的逻辑（平台 / 地域 / 券商）
- 是否已考虑 页面设计兼容英、日、法等文案较长的语言展示
- 是否已考虑新旧版本兼容、老用户习惯、升级或引导
- 是否已考虑如何衡量需求效果
- 是否已考虑恶意利用和舆情风险
- 是否涉及新增 SDK
- 相关功能界面的等待时间是否超过 1s；如果是，需上升决策
- 是否会影响其他业务线
- 此需求是否需要制作新的投教内容 / 修改现有投教内容
- 是否需同步至客服、市场、社区、投教等同事（帮助中心、知识库、培训等）
- 是否涉及 BI 报表调整

Every item must have a result: `不涉及 / 是 / 已考虑 / 待确认 / 已完成`. If `待确认`, include owner and impact.

### 3.3.x 项目专属 Checklist

In addition to the generic checklist, generate project-specific items from:

- product type (AI/content/data/trading/community/platform/internal tool)
- target markets and terminals
- domain risks (finance, compliance, privacy, education, content safety)
- project history and known recurring issues
- dependencies and rollout constraints

Format:

| 序号 | 确认项 | 为什么本项目需要 | 确认结果 |
|---|---|---|---|

### 3.4 合规Checklist

Cover these items:

- 许可 / 资质 / 牌照
- 网信办相关要求
- 数据和个人信息问题
- 跨境传输或存储、跨境或跨主体访问或调用、向集团外第三方提供
- 第三方知识产权或权利归属
- 广告法问题
- 促进违法犯罪风险
- 协议 / 风控 / 合同法律关系变化

If compliance affects user experience, or a feature interface wait time exceeds
1s, mark as `需上升` and record the escalation owner.

## 四、需求概述

### 4.1 功能说明

Break the requirement into modules. For each module, indicate priority:

- `Must`: must ship in this phase
- `Should`: important but can be descoped under time pressure
- `Could`: nice to have, ship if resources allow
- `Won't (this phase)`: explicitly out of scope for now

This module list becomes the table of contents for `五、需求详述`.

For AI/content-processing requirements, also state:

- how this requirement scope is bounded by concrete staged deliverables
- whether the deliverable can be clearly described
- whether effort can be estimated
- iteration plan for the broader capability

Naming rule for such requirements: use `[项目名]+[本次需求内容 or 产出概述]`; do not use only the long-running project name.

### 4.2 依赖关系

| 依赖方 | 依赖内容 | 状态 | 负责人 |
|---|---|---|---|
| (team or system) | (what is needed) | 已确认 / 待确认 / 有风险 | (name or TBD) |

### 4.3 流程图（可选）

If no image or flowchart is available, provide a textual process summary and explicitly mark it as `流程说明（文字版）`.

## 五、需求详述

Expand by module:

- 5.1 模块 A
- 5.2 模块 B
- 5.3 模块 C

### Standardized Module Skeleton

```markdown
### 5.x 模块名称

**优先级**：Must / Should / Could

**用户故事**：作为 [角色]，我想要 [行为]，以便 [目标]

**触发条件**：[何时 / 何地 / 如何进入此模块]

**业务规则**：
1. 规则一（来源：已确认 / 假设）
2. 规则二

**交互说明**：[前后端交互逻辑 / 状态变化]

**分支逻辑**：
| 条件 | 处理方式 |
|---|---|

**异常处理**：
| 异常场景 | 处理方式 |
|---|---|

**验收标准**：
- AC-1: Given [前提条件], When [用户操作], Then [期望结果]
- AC-2: Given [前提条件], When [用户操作], Then [期望结果]
```

Use concise paragraphs, bullets, and image-above text-below layout if visuals exist.

For AI/content-processing modules, include these additional subsections when relevant:

- 业务流程
- 内容来源及范围
- 内容处理要求（理想态，可附案例）
- 兜底逻辑（边界情况如何处理）
- 输出内容要求（如评测集、语种、时区、对象范围、版本/季度选择）
- 评测结果（评测后填写）

## 六、非功能性需求

### 6.1 性能要求

| 指标 | 目标值 | 备注 |
|---|---|---|
| 页面加载时间 | (e.g., < 1s) | |
| 接口响应时间 | (e.g., < 500ms P99) | |
| 并发支持 | (e.g., X QPS) | |

If no performance requirements are relevant, state `本需求不涉及新增性能敏感场景` and briefly explain why.

### 6.2 安全要求

- 数据传输加密要求
- 权限与鉴权规则
- 敏感数据脱敏规则
- 防攻击/防刷策略

### 6.3 兼容性要求

- 最低支持的系统版本 / 浏览器版本
- 屏幕尺寸适配
- 与现有功能的兼容性影响

### 6.4 无障碍访问（可选）

- 是否需要支持屏幕阅读器
- 色彩对比度要求
- 键盘导航支持

### 6.5 降级、灰度与回滚策略

- **降级方案**：当核心依赖不可用时的表现
- **灰度策略**：发布范围和选用户策略
- **回滚条件**：触发回滚的指标和流程

## 七、数据埋点

### 7.1 新增事件表

Try to provide rows with:

- 事件ID
- 事件名
- 事件说明
- 属性说明

If no real event ID exists yet, mark the ID as `待申请`.
If events are required, PRD should state that IDs must be applied for before development and product acceptance must verify reporting quality.

### 7.2 数据分析思路

Describe:

- what user behavior or business result will be measured
- what funnel / conversion / retention / usage signals matter
- how the proposed events support later analysis

## 八、多语言文案

### 8.1 文案 Checklist

At minimum clarify:

- 是否对外向用户展示
- 面向哪些市场

### 8.2 文案内容

Provide a list or table of candidate copy.
If final wording is pending, provide placeholders and label them clearly.
If multilingual copy is required, PRD should track copy review status and copy ID backfill status for development.

## 附录

### A. 支撑材料

Link or reference supporting materials when available:

- 数据分析报告
- 用户调研报告
- 设计分析报告

If no materials are available yet, leave placeholders rather than deleting the appendix.

### B. 决策日志

| 决策项 | 结论 | 来源 | 日期 |
|---|---|---|---|
| (decision topic) | (what was decided) | 已确认 / 假设 | (date) |

### C. 待确认事项

| 待确认项 | 原因 | 建议确认人 | 影响范围 |
|---|---|---|---|
| (item) | (why unresolved) | (who can resolve) | (which sections are affected) |
