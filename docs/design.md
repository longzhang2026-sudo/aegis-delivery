# 设计来源与实现边界

## 原始流程

Long 的《轻量级 AI 软件开发标准化工作流 V1.6》，2026-09-18，11 页，是本项目的流程来源。源码中的中文协议是面向执行的整理，不依赖原作者本机的 PDF 路径。

| 原文主题 / 页码 | 本包位置 |
| --- | --- |
| 主链与适用范围 / 1–2 | protocol.md 第 1 节、SKILL 路由 |
| Contract / Graph / Impact / 3 | 协议第 2 节、任务模板 |
| Capability 与角色权限 / 4 | 协议第 3 节、初始化指南 |
| 独立上下文与验证 / 5 | 协议第 4 节、Verifier 提示 |
| 一份记录与有效执行时间 / 6 | 协议第 7 节、任务模板 |
| Evidence 与结论 / 7 | 协议第 5 节 |
| 有限修复与 Human Gate / 8 | 协议第 6 节 |
| Delivery / Knowledge Sync / 9 | 协议第 8 节 |
| 治理与最小载体 / 10 | 项目入口、配置与文档复用原则 |
| 三类试点 / 11 | testing.md 与协议第 10 节 |

安装状态、默认 4 次/120 分钟、Conditional 适用性与修复周期计数是本包明确的实现约定，见 [协议第 9 节](../skills/ai-delivery/references/protocol.md)。不会把这些默认值冒充原文固定要求。

## 参考的专业 Skill 组织方式

截至 2026-09-18 查阅以下公开来源，参考的是结构与接口，不复制其具体实现：

- [Agent Skills specification](https://agentskills.io/specification)：SKILL.md 的 name/description、可选资源和渐进加载。
- [OpenAI Build skills](https://developers.openai.com/zh-Hans/docs/build-skills)：项目 `.agents/skills`、显式/隐式调用，以及按需读取资源。
- [OpenAI plugins](https://github.com/openai/plugins)：插件根清单与 skills 目录分发结构。
- [OpenAI skills](https://github.com/openai/skills)：该仓库 README 已提示迁移至 plugins，作为历史结构参考，不依赖其旧安装路径。
- [Anthropic skills](https://github.com/anthropics/skills)：自包含 Skill、脚本/参考材料/资产分离、示例说明。其各目录许可不同；本项目没有直接引入这些文件。

## 为什么只实现一个小脚本

工作流本身用可读规则、一个项目配置和一份任务记录即可运行。脚本只做容易误操作且可确定检查的文件安装、完整性检查和任务模板生成。源码搜索、代码实现、真实验证和交付由 Codex 利用项目现有工具执行。

没有硬编码模型、云服务、数据库、收费供应商或个人目录。没有后台服务、状态数据库、计时守护进程、自动并发 Agent，也没有把文档规则包装成安全隔离机制。只有真实试点暴露重复痛点后才扩展。

## 版本和维护

包版本遵循 SemVer；当前 0.x 阶段允许演进，但必须在 CHANGELOG 标明不兼容行为。协议版本独立保留，修改流程判定不能只改安装器版本。升级不自动覆盖用户规则和进行中的 Contract。

安装校验用的 SHA-256 用来发现意外变动，不是防恶意篡改的签名系统。首先信任/审查获取来源；不要把用户可改的 install.json 当作供应链认证。
