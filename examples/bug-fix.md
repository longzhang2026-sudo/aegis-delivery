# 示例：筛选后重置页码

**虚构演示，未在真实项目执行。下列场景与命令都是计划，不是 PASS 证据。** 路径和命令需由实际项目填写。

<!-- ai-delivery-record:start -->
```json
{
  "record_schema_version": 1,
  "task_id": "EXAMPLE-BUG-001",
  "title": "筛选后重置页码",
  "status": "DRAFT",
  "risk": "NORMAL",
  "contract_version": 1,
  "customer_confirmation": {
    "required": false,
    "status": "NOT_REQUIRED"
  },
  "budgets": {
    "root_repairs_max": 2,
    "task_repairs_max": 4,
    "replans_max": 1,
    "effective_minutes_max": 120
  },
  "usage": {
    "root_repairs_by_id": {},
    "task_repairs": 0,
    "replans": 0,
    "effective_minutes": 0
  },
  "artifact_id": null,
  "knowledge_sync": {
    "status": "PENDING",
    "reason": null
  },
  "delivery": {
    "artifact_ref": null,
    "reproduce_ref": null,
    "acceptance_ref": null
  },
  "acs": [
    {
      "id": "AC-01",
      "type": "REQUIRED",
      "description": "第 3 页切换筛选后，页码为 1，请求含新条件",
      "trigger": null,
      "applicability": "APPLICABLE",
      "applicability_reason": null,
      "applicability_basis": null,
      "decision_ref": null,
      "applicability_decision_stage": null,
      "executed": false,
      "verdict": "NOT_VERIFIED",
      "evidence_batch": null
    },
    {
      "id": "AC-02",
      "type": "REQUIRED",
      "description": "清空筛选后回到默认条件第一页",
      "trigger": null,
      "applicability": "APPLICABLE",
      "applicability_reason": null,
      "applicability_basis": null,
      "decision_ref": null,
      "applicability_decision_stage": null,
      "executed": false,
      "verdict": "NOT_VERIFIED",
      "evidence_batch": null
    },
    {
      "id": "AC-03",
      "type": "REQUIRED",
      "description": "普通翻页保留当前筛选条件",
      "trigger": null,
      "applicability": "APPLICABLE",
      "applicability_reason": null,
      "applicability_basis": null,
      "decision_ref": null,
      "applicability_decision_stage": null,
      "executed": false,
      "verdict": "NOT_VERIFIED",
      "evidence_batch": null
    },
    {
      "id": "AC-04",
      "type": "CONDITIONAL",
      "description": "若原页面支持 URL 状态恢复，恢复行为保持不变",
      "trigger": {
        "description": "原页面存在 URL 状态恢复",
        "state": "UNKNOWN",
        "basis": null
      },
      "applicability": "UNKNOWN",
      "applicability_reason": null,
      "applicability_basis": null,
      "decision_ref": null,
      "applicability_decision_stage": null,
      "executed": false,
      "verdict": "NOT_VERIFIED",
      "evidence_batch": null
    }
  ],
  "evidence_batches": []
}
```
<!-- ai-delivery-record:end -->

机器区是演示任务的机械状态来源。AC-04 尚未判断触发条件，因此 Guard 应给 WARN；它不能被当作未触发或 N/A。

## Contract

目标：用户切换订单筛选后从第 1 页看到匹配记录。

范围：列表筛选与分页联动。非目标：API、金额计算、权限、数据写入和列表重构。风险 NORMAL，因为修改可执行逻辑，不能使用 LOW 例外。

上限采用包默认值。客户确认不作为本示例 DONE 前置条件。真实任务必须以确认的 Contract 为准。

## Graph 与 Impact

1. 定位筛选入口、页码状态与请求调用 → 确认影响链 → 源码追踪。
2. 最小修复并覆盖必要回归 → Diff / 自检报告 → 原有测试入口与实际操作。
3. 独立验证 → 逐 AC Evidence → 黑盒预期后看实现。
4. 交付与知识检查 → 可复现说明 → 回读。

Direct：列表入口，具体文件待查。Callers：分页控件、筛选事件和请求函数待查。Data：本地页码/筛选状态，需要验证，不宣称数据库行为变化。External：查请求参数是否保持兼容。Regression：清空筛选、普通翻页及已存在的恢复行为。

## Verifier Phase A 计划

准备足够多的匹配记录；分别执行 AC-01/02/03 并观察页码、请求参数、界面结果。查明 AC-04 的前提；若不存在，在执行该 AC 前记录 `NOT_TRIGGERED → NOT_APPLICABLE → N/A` 及依据，不能在失败后取消。

Phase B 读取实现后再补异步请求顺序、重复事件或旧数据覆盖等**实际存在**的风险，不预设每个项目都有这些机制。

## 待执行与交付

尚无当前产物、运行环境或原始报告。所有必要项保持 NOT_VERIFIED，不能 DONE。真实执行后在机器区写 Evidence batch，由 AC 引用；正文补充复现与长结果说明。交付前运行 `validate-task`，但 Guard 成功不能代替真实验收。
