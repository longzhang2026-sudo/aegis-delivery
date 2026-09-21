# 使用手册：从需求到交付

先按 [初始化指南](../skills/aegis-delivery/references/initialization.md) 接入项目。本文中的路径相对业务项目根目录；TASK-001 只是示例 ID。所有示例结果均待实际执行。

## 1. 启动一个任务

在目标项目的 Codex 任务中输入：

```text
$aegis-delivery
任务：<问题或希望实现的一个功能切片>
当前行为：<真实情况与复现输入>
期望行为：<可观察结果>
范围与兼容要求：<要做与不做的内容>
请基于项目规则整理 Contract、Graph 和 Impact，完成必要实现和自检，
准备独立验收。未知关键语义先问，其他已授权可逆工作继续。
```

也可以先创建记录（在目标项目根目录运行）：

```bash
python .agents/skills/aegis-delivery/scripts/workflow.py new-task --project . --id TASK-001 --title "修复筛选分页联动"
```

生成 `.ai-workflow/tasks/TASK-001.md`。同 ID 已存在时拒绝覆盖；恢复用原记录，不新建副本。新模板在同一文件内包含 Task Record schema v1 JSON 机器区和人读正文。机器区是状态、计数和 Evidence 引用的机械来源，详细规则见 [Task Record schema](../skills/aegis-delivery/references/task-record-schema.md)。

## 2. 把“完成”变成可观察的验收

不要只写“优化体验”“保证稳定”。例如“在第 3 页切换筛选后，页码变为 1，请求携带新筛选条件；普通翻页继续使用当前筛选”。明确输入与预期后，才能验证。

- Required：适用时必须 PASS；执行该 AC 前有依据确认本任务实例不适用时，可以记录 `NOT_APPLICABLE + N/A`、理由和依据。
- Conditional：先写触发条件；`TRIGGERED / NOT_TRIGGERED / UNKNOWN` 必须对应 `APPLICABLE / NOT_APPLICABLE / UNKNOWN`。触发后加入必要验收，未知不能默认不适用。
- Optional：不影响必要交付，但 PASS 仍需 Evidence，N/A 仍需不适用依据，其他结论必须披露；不能把原 Required 随意降级。

规则冲突、范围扩大或兼容要求不清才由人决策。用户原请求已定义清楚时，Agent 可以记录该授权依据继续，不要求每个字段重新确认。

## 3. 实现并自检

Builder 检查调用链与必要回归，按编号小步实现。复用既有构建/测试命令，不建立重复框架。把实际命令、退出码、运行报告和当前产物写入记录。

正式交接应区分：

- **Phase A 输入**：Contract、AC、Impact；不夹带“已修好”或 Builder 对实现正确性的解释。
- **Phase B 输入**：Graph、Diff/版本、构建运行入口、测试数据、已知问题和原始报告。

未提交变更要记录 Diff 和新增/删除清单；只有 commit SHA 无法标识整个工作产物。

Builder 自检完成后可运行 `validate-task` 检查当前记录。WARN 表示 DRAFT 中仍有合法缺口；ERROR 表示结构或状态矛盾。Guard 不替代下一步独立验证。

## 4. 进行独立验证

有经过授权的独立上下文能力时按宿主方式使用。没有时，由使用者在同一项目打开新的 Codex 任务，粘贴：

```text
$aegis-delivery
独立验证 .ai-workflow/tasks/TASK-001.md。
先仅阅读 Contract / AC / Impact，写下黑盒场景和预期；
完成 Phase A 后再读实现与 Diff，补充实现特有风险并实际执行检查。
不要改业务代码，不把 Builder 的自检结论当证据。
请保存原始输出，逐 AC 记录 PASS / FAIL / NOT_VERIFIED / BLOCKED。
若需要修复，指出根因与最小复现，交还 Builder。
```

两个上下文不要同时修改同一份记录：交接后暂停 Builder 写入，Verifier 完成后再交还；不需要为首次使用建设并发系统。

不能获得独立验证时，可以交付候选和缺口说明，标准任务不能声明已独立 PASS。LOW 例外须逐项符合 [协议白名单](../skills/aegis-delivery/references/protocol.md)，不能由风险标签自动获得。

## 5. 真实环境需要人工验证

独立 Verifier 已固定预期并完成可执行检查，但剩余 AC 必须由用户进入测试环境、使用特定身份或设备操作时，Skill 应生成一张 Human Verification Card。用户不需要打开或编辑 `.ai-workflow`。

```text
构建和独立工程检查已完成，还需要你在测试环境确认 1 组行为。

请验证：
1. 打开订单详情页。
2. 对测试订单点击“查询物流”。
3. 预期：正常物流可展示；异常物流数据不会导致页面报错。

证据要求：本项只需回复结果；如失败可附截图。

请回复其中一种：
A. 通过
B. 失败：实际现象……
C. 暂时无法验证：原因……
```

Skill 自动读取当前任务、Artifact 和待验 AC，并在收到回复后更新同一 Task Record：

- A 且证据充分：生成 Human Evidence，逐 AC PASS；其余 DONE 门禁满足后运行 `validate-task` 并关闭任务。
- A 但缺少 Contract 预先要求的材料：只追问一个必要证据。高风险操作不能凭裸“通过”PASS。
- B：记录失败 Evidence，返回 Builder 做 Delta Repair。
- C：保持 NOT_VERIFIED/BLOCKED，写明恢复条件，不消耗代码修复次数。

普通 UI 展示或只读查询可以按 Contract 接受脱敏文字观察；API、状态变化、数据写入、权限、金额、库存、迁移或不可逆副作用应在卡片中提前要求响应、截图、日志、前后状态或对账。不要粘贴密码、Token 或完整客户资料。

Artifact 无法自动绑定时，Skill 只能追问一个用户可观察的版本标识，例如页面构建号；不能让用户填写内部 hash。重复回复不得生成重复 Evidence。详细机器规则见[协议的 Human Verification Card](../skills/aegis-delivery/references/protocol.md#41-human-verification-card)。

## 6. 失败、阻塞与继续

正式 FAIL 后先分类和查额度，不能把每次重试都当新任务。任务记录正文按触发追加以下说明，并同步更新机器区 usage；不要在正文维护第二套累计值：

```text
Loop / Exception
根因 R-01：<有证据的原因>
失败 Evidence：<报告位置>
本周期：<根因第几次 / 任务累计第几次修复>
实际动作与再次验证：<真实记录>
累计有效执行时间 / Replan 次数：<真实值>
若等待：<原因、需要的决策/条件、恢复步骤、剩余额度>
```

恢复提示：

```text
$aegis-delivery
继续 .ai-workflow/tasks/TASK-001.md。
先复核原 Contract、当前产物、Evidence 的有效性与累计额度；
恢复条件是：<已补充的条件/决策>。
从受阻阶段继续，不清零计数，也不要重写已执行结果。
```

额度耗尽由人决定终止、缩小范围或明确追加授权，不自行恢复默认额度。正式调整 Contract 时保留旧决定与调整依据。

## 7. 验收后交付

最终交付必须让另一位使用者能够复现：

1. 产物：版本或文件、Diff、已知限制。
2. 运行：必要环境、安装/初始化、构建与运行命令、最小测试输入。
3. 验收：逐 AC 结果、原始证据位置、未覆盖边界。
4. 知识：更新了哪些已有文档并回读；或者查阅后无增量及理由。

只有协议 DONE 条件全部满足才标完成。若客户确认在 Contract 中是必需，技术验收通过后仍需该确认；若未要求，不能临时增加一道审批。

标记 DONE 前运行：

```bash
python .agents/skills/aegis-delivery/scripts/workflow.py validate-task --project . --id TASK-001
```

只有无 ERROR 才能继续由负责人依据真实证据关闭任务。产物不一致 WARN 必须先复核 Evidence；Guard 成功本身不能作为业务 PASS。

## 8. 团队与首轮试点

建议把不含敏感信息的 Skill、AGENTS 入口、项目配置和任务记录纳入业务项目版本控制。不要提交密钥、完整客户数据、大量敏感原始日志；报告采用必要脱敏信息和可控存储位置。

先走一个 Bug，再做一个功能切片，最后做必要跨模块变更。按 [协议的六项指标](../skills/aegis-delivery/references/protocol.md) 记录实际成本与缺口。反复出现的同类问题才增加工具机制，避免一次性构建重型平台。
