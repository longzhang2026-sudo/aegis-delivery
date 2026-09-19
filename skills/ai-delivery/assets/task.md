# {{TASK_ID}} · {{TITLE}}

<!-- ai-delivery-record:start -->
```json
{
  "record_schema_version": 1,
  "task_id": {{TASK_ID_JSON}},
  "title": {{TITLE_JSON}},
  "status": "DRAFT",
  "risk": "NORMAL",
  "contract_version": 1,
  "customer_confirmation": {
    "required": false,
    "status": "NOT_REQUIRED"
  },
  "budgets": {
    "root_repairs_max": 2,
    "task_repairs_max": {{TASK_REPAIRS}},
    "replans_max": 1,
    "effective_minutes_max": {{EFFECTIVE_MINUTES}}
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
      "description": null,
      "trigger": null,
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

机器区是状态、计数和 Evidence 引用的唯一机械来源。字段与合法组合见项目内 `.agents/skills/ai-delivery/references/task-record-schema.md`。正文记录判断依据与可复现细节，不重复维护另一套状态。

## Contract

- 目标与交付形态：待填写
- 范围 / 非目标 / 兼容边界：待填写
- 业务规则 / 环境 / 权限：待填写，不保存密钥
- 依据与确认：待记录用户请求或必要补充决策
- Human Gate：H1 关键语义；H2 范围/AC/兼容改变；H3 必要高风险授权；H4 上限或证据冲突

### AC 详情

- AC-01 输入与可观察预期：待填写
- AC-01 必要证据：待定义

## Graph

1. 待填写动作 → 输出 → 检查方式。

## Impact

- Direct：待查
- Callers：待查
- Data：待查
- External：待查
- Regression：待查

## Evidence

验收方式：待确定独立 Verifier；满足全部 LOW 白名单条件时记录例外依据。

- Phase A 场景与预期：待独立 Verifier 在读取实现之前固定。
- Phase B 补充风险：待读取实现后补充。
- Evidence batch 说明：在机器区登记实际产物、环境、输入、动作、结果和原始报告位置；正文可补充长日志摘要，不保存敏感数据。
- 有效执行时间：使用粗粒度真实片段；正式修复 / Replan / Reset 首次发生时再追加说明，累计值只写机器区，恢复不清零。

## Delivery

- Artifact：待交付；机器区 `artifact_id` 与 `delivery.artifact_ref` 指向当前产物和本节说明。
- Reproduce：待提供环境、初始化、构建运行、测试数据和操作步骤。
- Acceptance：待引用逐 AC Evidence；记录未覆盖边界与限制。
- 客户接收：按 Contract 处理。

## Knowledge Sync

待查相关现有文档。结论只能是已更新并回读、无增量及理由或同步失败；机器区保存状态，正文列出来源、版本/环境边界和文档位置。

完成正文与机器区后运行 `validate-task`。该命令不执行测试，也不证明业务结果真实。
