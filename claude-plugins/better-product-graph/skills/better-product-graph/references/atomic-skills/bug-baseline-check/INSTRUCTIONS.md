# Bug Baseline Check — Agent Instructions v0.2

这个环节要判断：线上表现是偏离了已经明确的产品基线，还是产品规则本身需要重新讨论。只能通过公开 Skill 和 Controller 运行；不要读取内部源码猜字段，也不要让程序替你做产品判断。

保留 dispatch 中的 `attempt_id`、`instruction_ref`、`instruction_hash`、`input_refs` 和 `input_hashes` 原值，提交一个 `node-result.v1`。所有分类都必须提供非空的 `next_action`。

## 线上实现偏离现有基线

只有同时满足以下条件时，才能选择 `IMPLEMENTATION_DEVIATION`，并请求进入 `handoff.prepare`：存在一份可校验的当前基线；预期和实际行为不同；修复不需要新增产品规则；验收条件可判定；不存在会改变产品判断的实质冲突。

`semantic_output` 必须完整提交：

```json
{
  "classification": "IMPLEMENTATION_DEVIATION",
  "baseline_ref": {
    "path": "项目中的基线文件路径",
    "hash": "sha256:该文件的精确哈希",
    "version": 1
  },
  "expected": "基线要求的行为",
  "actual": "实际观察到的行为",
  "new_rule_required": false,
  "acceptance_criteria_decidable": true,
  "material_conflict": false,
  "next_action": "给研发核查、修复和回归验证的具体下一步"
}
```

`baseline_ref.path` 指向的文件必须存在，`hash` 必须匹配文件当前字节，`version` 必须是整数；`expected` 与 `actual` 不能相同。

## 产品逻辑缺陷或规格歧义

如果需要新增或修改产品规则，选择 `PRODUCT_LOGIC_DEFECT`；如果现有规格无法唯一判断正确行为，选择 `SPEC_AMBIGUITY`。这两类请求进入 `evidence.collect`，不要为了通过校验伪造 `baseline_ref` 或实现偏离的布尔字段。

```json
{
  "classification": "PRODUCT_LOGIC_DEFECT",
  "next_action": "补充证据并重新进入产品问题发现"
}
```

```json
{
  "classification": "SPEC_AMBIGUITY",
  "next_action": "查明冲突规格及其当前适用范围"
}
```

Controller 只验证你提交的合同和路线，不会改写分类、补造缺失语义或把主观判断冒充证据。
