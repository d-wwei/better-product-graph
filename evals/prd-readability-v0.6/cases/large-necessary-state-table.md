# 跨仓调拨进度

## 一句话说明

一张调拨单会经过发起仓、审核方、出库仓、运输方和接收仓。下表集中说明每次事件把哪一个来源状态变成哪一个目标状态、由谁负责以及用户接下来能做什么；这里的逐行映射比拆成散落段落更便于核对。

## 状态迁移表

| 来源状态 | 事件 | 目标状态 | 当前责任方 | 下一步或用户动作 |
|---|---|---|---|---|
| `DRAFT` | 发起人提交 | `SUBMITTED` | 审核方 | 等待审核 |
| `SUBMITTED` | 审核通过 | `APPROVED` | 出库仓 | 准备拣货 |
| `SUBMITTED` | 审核退回 | `REVISION_REQUIRED` | 发起人 | 修改数量或原因 |
| `REVISION_REQUIRED` | 重新提交 | `SUBMITTED` | 审核方 | 再次审核 |
| `APPROVED` | 开始拣货 | `PICKING` | 出库仓 | 查看拣货进度 |
| `PICKING` | 库存不足 | `STOCK_EXCEPTION` | 发起人与出库仓 | 调整数量或取消 |
| `STOCK_EXCEPTION` | 数量调整完成 | `APPROVED` | 出库仓 | 重新拣货 |
| `PICKING` | 拣货完成 | `READY_TO_SHIP` | 出库仓 | 等待承运 |
| `READY_TO_SHIP` | 车辆接单 | `IN_TRANSIT` | 运输方 | 查看运输进度 |
| `IN_TRANSIT` | 运输异常 | `TRANSIT_EXCEPTION` | 运输方 | 查看原因与预计恢复时间 |
| `TRANSIT_EXCEPTION` | 恢复运输 | `IN_TRANSIT` | 运输方 | 继续跟踪 |
| `IN_TRANSIT` | 接收仓签收 | `RECEIVING` | 接收仓 | 核对实收数量 |
| `RECEIVING` | 数量一致 | `COMPLETED` | 无 | 查看完成凭证 |
| `RECEIVING` | 数量不一致 | `RECEIPT_EXCEPTION` | 接收仓与出库仓 | 核查差异 |
| `RECEIPT_EXCEPTION` | 差异处理完成 | `COMPLETED` | 无 | 查看处理记录 |
| `DRAFT` | 发起人取消 | `CANCELLED` | 无 | 查看取消原因 |

## 共通规则

页面只能展示服务端已经确认的目标状态；用户点击动作后不能提前跳转。例如，发起人提交产生 `DRAFT` → `SUBMITTED`，这次来源→目标变化必须保留事件、责任方、时间和原因。`COMPLETED` 与 `CANCELLED` 是最终状态，仍可查看全程记录。

## 恢复路径

- `STOCK_EXCEPTION` 通过调整数量回到 `APPROVED`，不得跳过重新拣货。
- `TRANSIT_EXCEPTION` 恢复后回到 `IN_TRANSIT`，原异常记录保留。
- `RECEIPT_EXCEPTION` 由两仓确认差异后进入 `COMPLETED`，不能自动抹平实收差异。

## 风险与未知

主要风险是运输方晚到事件覆盖接收仓的新状态，因此所有事件按服务端确认顺序应用。当前未知是部分承运商能否提供预计恢复时间；缺失时页面明确写“等待承运商更新”。

## 下一步

用库存不足、运输异常和到货差异三条完整链路验证迁移与恢复，再与五个责任角色确认页面动作。本需求不改变仓库库存扣减算法。
