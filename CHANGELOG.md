# Changelog

## Unreleased

- 增加 Human Verification Card：真实环境只能由用户操作时，用户只回复通过、失败或无法验证，Skill 自动维护 Evidence、AC、Delivery 与 Guard。
- 明确高风险人工验收的客观证据要求、重复回复去重和失败/阻塞映射，并补充中英文文档、示例与回归检查。
- 项目、插件与 Skill 从 `ai-delivery-workflow` / `$ai-delivery` 统一更名为 `aegis-delivery` / `$aegis-delivery`。
- 新安装使用 `.agents/skills/aegis-delivery` 和新托管标记；检测到旧安装时拒绝静默双装并引导人工迁移。
- `validate-task` 继续读取旧 `ai-delivery-record` 机器区，已有任务记录无需因改名重写。
- 增加安装优先的中英文快速入口、插件提交材料与可缩放品牌标志。

## 0.2.0 — 2026-09-19

- 增加根目录 portable Agent Plugin 清单，保留 `.codex-plugin/plugin.json` 兼容入口。
- 将 Skill 设为 `$ai-delivery` 显式调用，避免普通对话误触发完整交付流程。
- 完整校验项目配置的版本、预算、命令、知识路径和基线字段，同时保留未知扩展字段。
- 增加 Task Record schema v1 与只读 `validate-task`，确定性检查 AC 适用性、N/A、Evidence、DONE 和额度组合。
- 明确执行前有依据确认不适用的 Required AC 可以 N/A；失败后不能豁免。
- 将 `inspect` 扩展为不跟随链接、固定深度 2、稳定排序的项目线索扫描。
- 保持 Python 标准库、单脚本、一份项目配置和一份任务记录；没有新增服务或运行时依赖。

## 0.1.0 — 2026-09-18

- 首次开源 Long 的轻量 AI 软件交付协议 V1.6 实现。
- 提供独立 `ai-delivery` Skill、可选 Codex 插件清单、任务模板与分阶段验收指引。
- 提供 Python 标准库初始化、静态检查、任务创建工具；保留既有规则，拒绝冲突覆盖。
- 增加中文初始化/使用/恢复指南、英文快速入口、明确标注未执行的示例和行为回归场景。
- 增加安装器回归检查与多操作系统 CI；真实业务试点另行记录。
