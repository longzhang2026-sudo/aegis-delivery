# AI Delivery Workflow

[中文详细文档](README.md) · [MIT](LICENSE)

A project-local Codex Skill for lightweight, evidence-first software delivery.
Package **0.1.0** implements Long's workflow protocol **1.6**. The detailed workflow
and operational guides are currently in Chinese; this page is the English entry point.

`Request → Contract → Plan & Impact → Build → Independent Verify → Delivery & Knowledge Sync → Done`

Use it for a reproducible bug, one feature slice, or a necessary cross-module change.
It defines acceptance before implementation, separates builder and verifier context,
limits repair attempts, and ties conclusions to actual artifact/environment evidence.
It is agent guidance, not an unattended orchestration service or hard security boundary.
Production operations are outside the first release's scope.

## Install into an existing project

Requirements: a working Codex environment, write access to the target project, and
Python 3.10+ for the installer. No third-party Python packages, mandatory MCP server,
API key, Node.js runtime, or GitHub account are required by the Skill itself.

```bash
git clone https://github.com/longzhang2026-sudo/ai-delivery-workflow.git
cd ai-delivery-workflow
python3 skills/ai-delivery/scripts/workflow.py inspect --project /path/to/project
python3 skills/ai-delivery/scripts/workflow.py init --project /path/to/project
python3 skills/ai-delivery/scripts/workflow.py check --project /path/to/project
```

On Windows, use `python` or `py -3` and a Windows project path. ZIP download also works.
The installer adds `.agents/skills/ai-delivery`, a bounded block in `AGENTS.md`, and
`.ai-workflow/project.json`. Existing rules and valid project configuration are
preserved. Conflicting managed files are refused, not overwritten.

`CONFIGURED` means static installation checks passed; it does not mean your application
runs or a delivery is accepted. Ask Codex to inspect actual build/test/run commands,
record them in the project profile, execute authorized baseline checks, and retain
their real outputs in an initialization report. See [START](START.md) and the
[initialization guide](skills/ai-delivery/references/initialization.md).

Defaults are 4 total repair cycles and 120 effective execution minutes; override them
on first installation with `--max-repairs` and `--time-limit-minutes`. Existing profiles
are preserved on repeated installation. Protocol limits remain 2 repairs per root
cause and 1 substantive replan. Agents track these in task records; scripts do not
enforce runtime budgets.

## Use

Open the target project in Codex and invoke:

```text
$ai-delivery
Fix the filter pagination bug. Preserve API behavior.
Define acceptance criteria, implement the smallest fix, run local checks,
and prepare an independent verification handoff with actual evidence.
```

Use a separate Codex task for standard verification when no authorized isolated
verifier capability is available. The verifier first derives black-box expectations
from Contract/AC/Impact, then inspects implementation and executes checks. Do not
present builder self-checks as independent verification.

Create a task record from the target project's root:

```bash
python3 .agents/skills/ai-delivery/scripts/workflow.py new-task \
  --project . --id TASK-001 --title "Fix filter pagination"
```

Resume by giving Codex the same task record, current artifact and remaining limits.
See [usage](docs/usage.md), [protocol](skills/ai-delivery/references/protocol.md),
[example](examples/bug-fix.md), and [design/source notes](docs/design.md).

## Validate and contribute

```bash
python3 -m unittest discover -s tests -v
```

Installer and package checks are automated. Agent behavior scenarios and real project
pilots are separate validation work; no unrun pilot is claimed as passed.
See [testing](docs/testing.md), [contributing](CONTRIBUTING.md), and [changelog](CHANGELOG.md).
The optional `.codex-plugin/plugin.json` manifest supports Codex plugin packaging;
it does not imply official marketplace publication or tool permissions.
