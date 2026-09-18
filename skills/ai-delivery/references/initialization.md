# 初始化与项目接入

初始化的目标是在一个现有项目内放入 Skill、项目默认值和任务模板，再核实项目运行入口。不是部署业务系统，也不安装数据库、Docker、生产服务或全局插件。

## 前置条件

- 已可使用 Codex，且允许它读取和写入目标项目。登录、账号开通、组织授权需要使用者自己完成。
- 已下载或克隆本仓库，确认来源和版本；目标项目目录已存在。
- 使用脚本需要 Python 3.10+，不需要 pip 包。不依赖固定电脑路径、API Key、MCP、GitHub 账号或 Node.js。业务项目本身的运行环境另行检查。
- 先读取目标项目上级及本级 AGENTS.md；已有开发命令和安全约束继续适用。

## 推荐：交给 Codex

告诉 Codex 工作流仓库的位置与目标项目目录，让它按本页完成以下步骤。仓库根目录的 START.md 提供可复制提示。

1. **只读检查**：确认目标目录、现有规则、Git 工作区状态（有 Git 时）、README/构建入口和现有任务/知识位置。不要读取 `.env`、凭据或不相关目录。
2. **安装**：运行下面的 inspect、init、check。初始化只写目标项目，不改用户全局 Codex 设置。脚本默认总修复 4 次、有效执行时间 120 分钟；向使用者报告采用值，已明确的用户值优先。
3. **补齐项目映射**：从实际配置识别 build/test/run 命令、必要环境、知识路径，写入 `.ai-workflow/project.json`。不要凭技术栈猜测一个命令就当它可用；尚未执行标候选。
4. **真实基线检查**：执行任务所需、在授权范围内的安全检查。安装依赖也可能运行第三方脚本，先检查项目约定；不得借初始化重置数据库、支付、发布或写生产数据。
5. **交付初始化报告**：在项目记录位置写一份报告，列文件变更、已执行命令/退出码/原始输出位置、缺失条件、采用限额、Skill 可见性与下一步。无现有位置可用 `.ai-workflow/initialization.md`。回读文件。
6. **首个试点**：在新 Codex 任务打开目标项目，显式调用 `$ai-delivery`，选一个可复现小 Bug。基线通过也不能代替此试点的交付验收。

## 手工命令

在下载的工作流仓库根目录执行，替换目标目录。示例中的路径均是占位，不能直接作为本机事实。

Windows PowerShell：

```powershell
python .\skills\ai-delivery\scripts\workflow.py inspect --project "D:\work\your-project"
python .\skills\ai-delivery\scripts\workflow.py init --project "D:\work\your-project" --max-repairs 4 --time-limit-minutes 120
python .\skills\ai-delivery\scripts\workflow.py check --project "D:\work\your-project"
```

macOS / Linux：

```bash
python3 skills/ai-delivery/scripts/workflow.py inspect --project "$HOME/work/your-project"
python3 skills/ai-delivery/scripts/workflow.py init --project "$HOME/work/your-project" --max-repairs 4 --time-limit-minutes 120
python3 skills/ai-delivery/scripts/workflow.py check --project "$HOME/work/your-project"
```

如果 Windows 上 `python` 不可用，使用已安装的 `py -3` 或 Python 解释器完整路径。Codex 自带运行时可由 Codex 查询使用；普通使用者不依赖作者电脑中的运行时位置。

安装结果：

```text
your-project/
├── AGENTS.md                         # 追加有边界标记的入口，保留既有内容
├── .agents/skills/ai-delivery/        # 独立 Skill 全部资源
└── .ai-workflow/
    ├── project.json                  # 项目默认限额、命令、知识位置
    ├── install.json                  # 安装文件 SHA-256，用于完整性检查
    └── tasks/                        # 首次 new-task 时创建
```

`project.json` 的 `commands` 初始为空，`baseline` 初始为 `NOT_VERIFIED`。例如已查明项目用 npm，可记录：

```json
{
  "build": {"command": "npm run build", "cwd": ".", "status": "NOT_VERIFIED"},
  "test": {"command": "npm test", "cwd": ".", "status": "NOT_VERIFIED"}
}
```

把这段作为 `commands` 的值，不要覆盖整个配置。具体项目没有该脚本就不要登记。真实执行后补报告位置和结果，保留产物/环境边界。脚本**不会执行**配置里的命令。

## 状态与成功标准

| 状态 | 能说明什么 |
| --- | --- |
| NOT_INSTALLED | 尚未发现项目配置 |
| INSTALLED_PENDING_CHECK | 文件安装结束或发现配置，尚需检查 |
| CONFIGURED | `check` 校验安装内容、入口块及基本配置成功；只代表静态安装 |
| READY（由 Agent 报告） | 静态检查通过，必要项目运行入口已实际检查，证据在初始化报告中；作用域仅该项目基线 |
| BLOCKED | 脚本出错，或必要环境/权限/依赖尚未满足；必须写原因和恢复步骤 |

命令成功退出码 0，错误退出码 2，JSON 错误写 stderr。`CONFIGURED` 始终返回 `runtime_verified: false`，不能改名为交付完成。

## 重复执行、冲突与升级

同版本 init 可重复执行，保持相同文件不变，保留已有合法项目配置、命令及限额；命令行传入的新限额不会覆盖现有配置。调整默认值请明确修改配置，并在新任务中采用；进行中的任务仍以已确认 Contract 为准。

已有 Skill 文件或托管入口块内容不同会拒绝覆盖；全部文件碰撞会在开始写入前检查。单个文件原子写入，整个安装不是事务，磁盘失败可能留下部分安装，修复环境后重跑可继续。不要同时对同一项目运行两个初始化进程。

目标管理路径中的符号链接/Windows junction 会被拒绝。显式指定的项目根目录先解析为实际目录；确认你确实要写该目录。脚本不支持以链接路径绕过规则，不修改全局环境。

升级时先对比新旧 Skill 和协议变更，备份本项目安装目录、入口块和配置，再由使用者/Codex 合并；不提供强制覆盖开关。重新安装前只移走确认属于本包的旧 Skill 和 install.json，保留项目配置、任务与知识。初版不自动升级或自动卸载。

卸载时删除经确认未被其他工作引用的 `.agents/skills/ai-delivery`、仅移除 AGENTS.md 中本包 `ai-delivery:start/end` 块；保留其他规则。`.ai-workflow` 含任务证据，不默认删除。移除入口与 Skill 后不要再运行该项目的 check。

## 无 Python 与其他 Agent

可手工复制整个 `skills/ai-delivery` 目录到目标项目 `.agents/skills/ai-delivery`，按 init 输出结构创建项目配置/入口，并声明“手工安装，未运行脚本完整性检查”。缺少运行时不等于必需安装全套 Python 开发环境。

Agent Skills 兼容工具可读取同一个 SKILL.md；每个工具的发现目录、独立上下文能力和权限机制不同，需按该工具文档接入。首版主要针对 Codex 验证，不宣称所有 Agent 都即装即用。仓库提供 Codex 插件清单供插件分发，但无需安装插件即可使用项目内 Skill。

## 常见问题

- **找不到 `$ai-delivery`**：确认是完整 Skill 目录，且打开的是目标项目；刷新 Skill 列表或重新打开项目任务。也可明确要求读取 `.agents/skills/ai-delivery/SKILL.md`。入口能被读取与列表发现分开检查。
- **check 失败**：读取 JSON 错误，核对缺失或被修改文件。不要删掉证据或重写哈希来伪装通过。
- **项目无法构建**：保存实际失败报告，标 BLOCKED；先确认是原有基线、依赖或本次变更问题。不得报 READY。
- **没有独立 Agent 工具**：在另一个 Codex 任务进行 Verifier 交接，不假冒独立上下文。
- **仓库有自定义 AGENTS**：原内容保留。对真正冲突的业务或权限规则做必要决策，不以本 Skill 覆盖它们。
