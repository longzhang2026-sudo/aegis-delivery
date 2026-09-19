# Aegis Delivery 国内首发素材

> 状态：可直接用于掘金、CSDN、V2EX。项目仍为 `NOT_YET_PILOTED`，不得删除或改写该边界。

## 掘金 / CSDN 长文

### 我把 AI 编码交付流程开源成了一个 Codex Skill：Aegis Delivery

AI 编码真正难的部分，往往不是“能不能生成代码”，而是下面这些问题：

- 需求边界会不会在执行过程中漂移？
- Agent 的自检能不能直接当成最终验收？
- 测试通过时，结论是否绑定了当前产物、环境和原始结果？
- 修复失败后会不会无限重试，最后没人说得清改过什么？
- 换一个会话或换一个人，任务还能不能继续？

我把自己使用的一套轻量研发交付方法整理成了开源 Codex Skill：**Aegis Delivery**。

项目地址：<https://github.com/longzhang2026-sudo/aegis-delivery>

它不是自动写代码的“万能 Agent”，也不是新的编排平台。它做的是给现有 Codex 开发任务加一条轻量、可追溯的交付主链：

```text
Request
  -> Contract
  -> Graph + Impact
  -> Execute / Builder Self Check
  -> Independent Verify
  -> Evidence
  -> Delivery + Knowledge Sync
  -> DONE
```

核心规则只有六条：

1. **Contract-first**：实现前先固定目标、范围、兼容边界、验收条件和停止条件。
2. **Impact-aware**：不只改表面入口，还检查调用方、数据、外部副作用和回归范围。
3. **Independent Verify**：Builder 自检不能自动升级成最终 PASS；标准路径由独立上下文先定预期，再看实现。
4. **Evidence-first**：PASS 必须引用当前产物、环境、输入、操作和结果，未执行就是 `NOT_VERIFIED`。
5. **Bounded Repair**：修复次数、Replan 和有效执行时间都有上限，避免无限循环。
6. **Reproducible Delivery**：交付必须包含产物、复现方式、逐项验收和知识同步结论。

### 60 秒试用

先让 Codex 从 GitHub 安装 Skill：

```text
$skill-installer
从 https://github.com/longzhang2026-sudo/aegis-delivery/tree/main/skills/aegis-delivery 安装 Skill。
```

然后在目标项目中调用：

```text
$aegis-delivery
检查并初始化当前项目，保留已有 AGENTS.md 规则；执行 inspect -> init -> check，
再识别实际 build/test/run 入口。未执行的检查保持 NOT_VERIFIED。
```

项目采用 Python 标准库和项目本地文件，不要求固定 MCP、Docker、付费 API 或第三方 Python 包。当前版本为 **v0.2.0 / Protocol V1.6**，自动检查覆盖 Windows、Linux、macOS 及 Python 3.10 / 3.13。

边界也写清楚了：它不负责生产发布和运维，不能证明 Evidence 未被伪造，也不构成操作系统级权限隔离。项目目前仍标记为 **`NOT_YET_PILOTED`**——工程检查已经建立，但真实业务项目的稳定性、效率和成本收益仍需要试点验证。

如果你正在用 Codex 做真实项目，欢迎拿一个可复现的小 Bug 或最小功能切片试用。最有价值的反馈不是“概念不错”，而是：

- 哪个步骤在真实项目里太重？
- 哪个字段或边界不够清楚？
- 哪类失败没有被正确记录或恢复？
- 哪条规则确实减少了返工？

仓库：<https://github.com/longzhang2026-sudo/aegis-delivery>

Issue：<https://github.com/longzhang2026-sudo/aegis-delivery/issues>

## V2EX 短帖

### 标题

[分享创造] 开源了一个给 Codex 用的轻量软件交付 Skill：Aegis Delivery

### 正文

最近把自己使用的一套 AI 研发交付方法整理成了开源 Codex Skill：Aegis Delivery。

它不负责“更快生成代码”，主要解决范围漂移、自检冒充验收、测试没有绑定证据、失败无限重试、交付无法复现这些问题。主链是：Contract → Impact → Builder → Independent Verify → Evidence → Delivery。

特点：Python 标准库、项目本地文件、不强依赖 MCP/Docker/付费 API；包含初始化脚本、单份 Task Record、只读 Guard、示例和跨平台 CI。

当前版本 v0.2.0，仍明确标记 `NOT_YET_PILOTED`。希望找愿意拿真实小 Bug 或功能切片试用的人，不想拿自动测试冒充真实项目效果。

项目地址：<https://github.com/longzhang2026-sudo/aegis-delivery>

欢迎直接提 Issue，尤其想听“哪里太重、哪里不清楚、什么场景不适用”。

## 推荐标签

- 掘金：`人工智能`、`开源`、`Python`、`软件工程`、`Codex`
- CSDN：`人工智能`、`软件工程`、`开源`、`Python`、`AI Agent`
- V2EX 节点：`分享创造`
