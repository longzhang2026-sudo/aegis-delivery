# Aegis Delivery

<p align="center">
  <img src="docs/images/aegis-delivery-mark.svg" width="96" alt="Aegis Delivery logo">
</p>

[![CI](https://github.com/longzhang2026-sudo/aegis-delivery/actions/workflows/ci.yml/badge.svg)](https://github.com/longzhang2026-sudo/aegis-delivery/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Package](https://img.shields.io/badge/package-v0.2.0-22A76A.svg)](CHANGELOG.md)
[中文详细文档](README.md)

A project-local Codex Skill for lightweight, evidence-first software delivery.
Package **0.2.0** implements Long's workflow protocol **1.6**. The detailed workflow
and operational guides are currently in Chinese; this page is the English entry point.

`Request → Contract → Plan & Impact → Build → Independent Verify → Human Verification when needed → Delivery & Knowledge Sync → Done`

Use it for a reproducible bug, one feature slice, or a necessary cross-module change.
It defines acceptance before implementation, separates builder and verifier context,
limits repair attempts, and ties conclusions to actual artifact/environment evidence.
It is agent guidance plus deterministic record validation, not an unattended orchestration service or hard security boundary.
Production operations are outside the first release's scope.

## Try it in 60 seconds

Open the target project in Codex, then send this single request:

```text
$skill-installer
Install https://github.com/longzhang2026-sudo/aegis-delivery/tree/main/skills/aegis-delivery
directly into .agents/skills at the current project root; do not install it into user-level skills.
After installation, run the project-local workflow.py through inspect -> init -> check
without overwriting existing AGENTS.md rules, then identify and validate the real build/test/run entry points.
Keep checks that were not executed as NOT_VERIFIED.
```

This leaves exactly one project-scoped `aegis-delivery`; invoke `$aegis-delivery` on the next turn.

For a no-install preview, read the [fictional bug-fix example](examples/bug-fix.md).

## Install into an existing project

Requirements: a working Codex environment, write access to the target project, and
Python 3.10+ for the installer. No third-party Python packages, mandatory MCP server,
API key, Node.js runtime, or GitHub account are required by the Skill itself.

```bash
git clone https://github.com/longzhang2026-sudo/aegis-delivery.git
cd aegis-delivery
python3 skills/aegis-delivery/scripts/workflow.py inspect --project /path/to/project
python3 skills/aegis-delivery/scripts/workflow.py init --project /path/to/project
python3 skills/aegis-delivery/scripts/workflow.py check --project /path/to/project
```

On Windows, use `python` or `py -3` and a Windows project path. ZIP download also works.
The installer adds `.agents/skills/aegis-delivery`, a bounded block in `AGENTS.md`, and
`.ai-workflow/project.json`. Existing rules and valid project configuration are
preserved. Conflicting managed files are refused, not overwritten.

`CONFIGURED` means static installation checks passed; it does not mean your application
runs or a delivery is accepted. Ask Codex to inspect actual build/test/run commands,
record them in the project profile, execute authorized baseline checks, and retain
their real outputs in an initialization report. See [START](START.md) and the
[initialization guide](skills/aegis-delivery/references/initialization.md).

Existing `$ai-delivery` installations must follow the
[rename migration](skills/aegis-delivery/references/initialization.md#从旧名称迁移);
do not keep both skill names installed in one project.

Defaults are 4 total repair cycles and 120 effective execution minutes; override them
on first installation with `--max-repairs` and `--time-limit-minutes`. Existing profiles
are preserved on repeated installation. Protocol limits remain 2 repairs per root
cause and 1 substantive replan. Agents track these in task records; scripts do not
enforce runtime budgets.

## Use

Open the target project in Codex and invoke:

```text
$aegis-delivery
Fix the filter pagination bug. Preserve API behavior.
Define acceptance criteria, implement the smallest fix, run local checks,
and prepare an independent verification handoff with actual evidence.
```

Use a separate Codex task for standard verification when no authorized isolated
verifier capability is available. The verifier first derives black-box expectations
from Contract/AC/Impact, then inspects implementation and executes checks. Do not
present builder self-checks as independent verification.

When the remaining check requires your real environment, account, or device, the
Skill presents one short Human Verification Card. You reply only `A. pass`,
`B. fail: what happened`, or `C. unavailable: why`; the Skill updates the task
record, Evidence, delivery fields, and guard. High-risk or state-changing acceptance
still requires the objective evidence stated on the card—a bare “pass” is not enough.
See the [usage guide](docs/usage.md#5-%E7%9C%9F%E5%AE%9E%E7%8E%AF%E5%A2%83%E9%9C%80%E8%A6%81%E4%BA%BA%E5%B7%A5%E9%AA%8C%E8%AF%81).

Create a task record from the target project's root:

```bash
python3 .agents/skills/aegis-delivery/scripts/workflow.py new-task \
  --project . --id TASK-001 --title "Fix filter pagination"
```

Resume by giving Codex the same task record, current artifact and remaining limits.
See [usage](docs/usage.md), [protocol](skills/aegis-delivery/references/protocol.md),
[example](examples/bug-fix.md), and [design/source notes](docs/design.md).

Before delivery or resume, the Skill automatically runs its read-only record guard;
users do not need to copy a command or interpret internal fields. A valid draft may
retain gaps, while contradictory state or an unmet DONE gate stops closure. The guard
checks record consistency; it does not prove application behavior, verifier independence,
or tamper-free history. Maintainers who need manual diagnostics can use the
[usage guide](docs/usage.md#7-%E9%AA%8C%E6%94%B6%E5%90%8E%E4%BA%A4%E4%BB%98). Legacy v0.1 tasks require manual migration using the
[record schema](skills/aegis-delivery/references/task-record-schema.md#旧任务).

## Validate and contribute

```bash
python3 -m unittest discover -s tests -v
```

Installer and package checks are automated. Agent behavior scenarios and real project
pilots are separate validation work; no unrun pilot is claimed as passed.
See [testing](docs/testing.md), [contributing](CONTRIBUTING.md), and [changelog](CHANGELOG.md).
The root `plugin.json` is the portable Agent Plugin manifest. `.codex-plugin/plugin.json`
remains the Codex interface fallback; neither implies marketplace publication or tool permissions.
