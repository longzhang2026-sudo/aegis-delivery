# Task Record schema v1

本页定义 `.ai-workflow/tasks/<ID>.md` 内的机器区。机器区只让确定性 Guard 检查记录自洽；Markdown 正文继续保存 Contract、Impact、场景、解释和交付细节。

## 边界与格式

机器区必须在文件中出现一次，使用以下边界；中间是一个 `json` fenced block：

````markdown
<!-- ai-delivery-record:start -->
```json
{"record_schema_version": 1}
```
<!-- ai-delivery-record:end -->
````

JSON 是状态、枚举、计数和 Evidence 引用的机械权威。正文不要重复维护另一套任务状态、额度或 verdict。未知扩展字段会被保留并忽略。

## 任务字段

| 字段 | 规则 |
| --- | --- |
| `record_schema_version` | 整数 `1` |
| `task_id` | 与文件名和 CLI `--id` 一致 |
| `title` | 非空单行，最多 200 字符 |
| `status` | `DRAFT / ACTIVE / BLOCKED / HUMAN_GATE / DONE / FAILED / CANCELLED` |
| `risk` | `LOW / NORMAL / HIGH` |
| `contract_version` | 正整数 |
| `customer_confirmation` | `required` 为布尔值；状态为 `NOT_REQUIRED / PENDING / CONFIRMED` |
| `budgets` | 同根因最多 2、Replan 最多 1；任务修复和有效分钟为正整数 |
| `usage` | 所有计数为非负整数，不得超过上限；恢复不清零 |
| `artifact_id` | 当前产物标识；未形成产物时为 `null` |
| `knowledge_sync.status` | `PENDING / UPDATED / NO_INCREMENT / SYNC_FAILED` |
| `delivery` | Artifact、Reproduce、Acceptance 的正文锚点或文件引用 |
| `acs` | AC 数组 |
| `evidence_batches` | 可由多条 AC 共用的 Evidence 数组 |

`required=false` 时客户确认状态只能是 `NOT_REQUIRED`；`required=true` 时只能是 `PENDING` 或 `CONFIRMED`。`NO_INCREMENT` 与 `SYNC_FAILED` 应在 `reason` 中说明依据。

## AC 三维模型

每条 AC 分开记录：

- `type`：`REQUIRED / CONDITIONAL / OPTIONAL`。
- `applicability`：`APPLICABLE / NOT_APPLICABLE / UNKNOWN`。
- `verdict`：`PASS / FAIL / NOT_VERIFIED / BLOCKED / N/A`。

其他字段：`id`、`description`、`trigger`、`applicability_reason`、`applicability_basis`、`decision_ref`、`applicability_decision_stage`、`executed`、`evidence_batch`。

Conditional 的 `trigger` 必须包含 `description`、`state` 和 `basis`；`state` 的合法值及映射固定为：

| trigger.state | applicability |
| --- | --- |
| `TRIGGERED` | `APPLICABLE` |
| `NOT_TRIGGERED` | `NOT_APPLICABLE` |
| `UNKNOWN` | `UNKNOWN` |

非 Conditional 的 `trigger` 使用 `null`。

## N/A 与 DONE

| 组合 | 规则 |
| --- | --- |
| Required + APPLICABLE | DONE 时必须 PASS，并引用完整 Evidence |
| Required + NOT_APPLICABLE | 可以 N/A；必须有理由、依据或决策引用，在 `BEFORE_AC_EXECUTION` 决定，且没有执行标记或 Evidence |
| Required + UNKNOWN | 不能 DONE |
| Conditional + TRIGGERED | 按适用的 Required 验收 |
| Conditional + NOT_TRIGGERED | 可以 N/A；`trigger.description` 与 `trigger.basis` 可直接作为理由和依据，避免重复填写 |
| Conditional + UNKNOWN | 不能 DONE |
| Optional | 不阻止 DONE；PASS/FAIL 仍需 Evidence，N/A 仍需不适用依据，其余 verdict 必须保留披露 |

`contract_version` 只定位 Contract，不能单独作为 N/A 依据。`BEFORE_AC_EXECUTION` 指正式执行该 AC 之前；允许先做只读检查来判断适用性。存在执行标记、实际 Evidence 或 batch 引用后不能改成 N/A。

## Evidence batch

每个 batch 包含：

- `id`：唯一非空字符串。
- `artifact_id`：被验证的实际产物。
- `environment`：实际环境说明。
- `inputs`：非空字符串数组。
- `actions`：实际命令或操作的非空字符串数组。
- `results`：真实结果的非空字符串数组。
- `report_locations`：原始报告或受控证据位置的非空字符串数组。

PASS 和 FAIL 都必须 `executed=true` 并引用完整 batch。当前 `artifact_id` 与引用 batch 的产物不一致时 Guard 给 WARN，要求复核；它不会从自然语言或 Git 状态猜测产物变化。

DONE 还要求：当前产物和三个 Delivery 引用非空；知识同步为 `UPDATED` 或 `NO_INCREMENT`；必要客户确认已完成；额度未超限；全部 Required 和已触发 Conditional 满足上表。

## 命令、退出码与错误

```bash
python .agents/skills/ai-delivery/scripts/workflow.py validate-task --project . --id TASK-001
```

输出为稳定 JSON：`valid`、`status`、`issues`。issue 含 `level`、`code`、`path`、`message`，按 `path + code + level` 排序。只有 ERROR 时退出 `2`；无 ERROR，包括只有 WARN，退出 `0`。命令只读。

常用 code：`TASK_METADATA_MISSING`、`RECORD_JSON_INVALID`、`FIELD_TYPE_INVALID`、`FIELD_VALUE_INVALID`、`AC_TRIGGER_APPLICABILITY_MISMATCH`、`AC_NA_BASIS_MISSING`、`AC_NA_AFTER_EXECUTION`、`AC_PASS_EVIDENCE_INCOMPLETE`、`EVIDENCE_ARTIFACT_MISMATCH`、`DONE_REQUIRED_AC_UNSATISFIED`、`DONE_DELIVERY_INCOMPLETE`、`DONE_KNOWLEDGE_SYNC_INCOMPLETE`、`DONE_CUSTOMER_CONFIRMATION_PENDING`、`BUDGET_EXCEEDED`。

## 旧任务

v0.1 任务没有机器区时，`validate-task` 返回 `TASK_METADATA_MISSING` 和退出码 `2`，不改文件。先备份任务，再从新版模板复制机器区，按原记录中的真实 Contract、额度、结论和 Evidence 人工填写；无法确认的值保持 `UNKNOWN / NOT_VERIFIED / PENDING`。旧任务仍可按 V1.6 人工执行，不能因迁移而补写 PASS。

## 可证明边界

Guard 只检查当前文件结构和状态组合，不能证明业务行为正确、Evidence 未伪造、独立验证真实发生，也不能证明过去的 FAIL 没有被删除。v1 不建立 append-only 事件历史，也不从自由文本推断“N/A 是否在掩盖阻塞”；这些判断由 Verifier 和负责人完成。
