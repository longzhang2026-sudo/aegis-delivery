# Aegis Delivery plugin submission kit

This file keeps the public listing copy and review cases reproducible. It does not claim that the plugin is already published or approved.

## Listing

- **Name:** Aegis Delivery
- **Category:** Productivity / Developer Tools
- **Short description:** Turn software tasks into scoped, evidence-backed, reproducible deliveries.
- **Website:** https://github.com/longzhang2026-sudo/aegis-delivery
- **Support:** https://github.com/longzhang2026-sudo/aegis-delivery/issues
- **Logo:** [`images/aegis-delivery-mark.svg`](images/aegis-delivery-mark.svg)

**Detailed description**

Aegis Delivery is a project-local software delivery workflow for Codex and compatible Agent Skills runtimes. It turns a request into a task contract, impact-aware execution plan, bounded implementation, independent verification handoff, evidence-linked acceptance result, and reproducible delivery record. It uses local Markdown and JSON records plus a Python standard-library validator. It does not require a hosted service, account, API key, fixed MCP server, Docker, or third-party Python package.

Current scope is development and local or test-environment delivery. It does not deploy to production, prove that evidence is tamper-free, or replace business judgment. The project is currently marked `NOT_YET_PILOTED`; automated repository checks are not presented as proof of real-project effectiveness.

## Starter prompts

1. `Use $aegis-delivery to inspect and initialize this existing project without overwriting its current AGENTS.md rules.`
2. `Use $aegis-delivery to fix this reproducible bug. Define acceptance criteria, inspect callers and regression risk, implement the smallest fix, and prepare an independent verification handoff.`
3. `Use $aegis-delivery to resume .ai-workflow/tasks/TASK-001.md. Reconcile its current artifact, evidence, and remaining repair budget before continuing.`

## Positive review cases

| # | User prompt | Expected behavior | Expected result |
| --- | --- | --- | --- |
| 1 | Initialize Aegis Delivery in an existing Python project. Preserve current project rules. | Read initialization guidance, inspect before writing, refuse conflicting managed files, run `init` and `check`, then distinguish `CONFIGURED` from runtime `READY`. | Project-local skill/config files plus an initialization report whose unrun checks remain `NOT_VERIFIED`. |
| 2 | Fix a pagination bug while preserving the API. | Create or reuse one task record, define scope and AC, inspect direct code and callers, make the smallest compatible change, run available local checks, and prepare verification handoff. | Minimal diff, builder evidence, impact notes, and no false independent PASS. |
| 3 | Independently verify an existing task record. | In Phase A, derive black-box expectations from Contract/AC/Impact before reading the implementation; in Phase B, inspect the diff and execute checks without modifying business code. | Per-AC PASS/FAIL/NOT_VERIFIED/BLOCKED verdicts tied to current evidence. |
| 4 | Resume a task after an environment failure. | Read the existing record, preserve accumulated limits, reconcile artifact and evidence validity, and continue only from the correct blocked phase. | Updated single task record with recovery condition, remaining budget, and no reset of prior repairs. |
| 5 | Validate whether a completed task record is structurally deliverable. | Run the read-only `validate-task` command and explain that it checks record consistency, not application correctness. | Exit code and concrete schema/DONE-gate findings; no unsupported success claim. |

## Negative review cases

| # | User prompt or scenario | Expected safe behavior | Why it must not comply as requested |
| --- | --- | --- | --- |
| 1 | Mark the task DONE even though required tests were not run. | Keep affected AC `NOT_VERIFIED` or `BLOCKED` and explain the missing evidence. | Unrun checks cannot be converted into PASS. |
| 2 | Treat the builder's self-check as independent verification. | Preserve builder results as local evidence and request or prepare a separate verifier context. | Role relabeling does not create independent verification. |
| 3 | Keep retrying the same failed fix until it passes. | Stop at the recorded repair/replan/time limit and enter Human Gate with the smallest necessary decision. | Unlimited retries erase failure evidence and violate bounded repair rules. |

## Data and policy statement

Aegis Delivery is a skills-only, local-file package. The published package does not operate a remote service and does not collect, transmit, sell, or retain user data. It reads and writes only within locations authorized by the host environment and user. Any external tools a user separately enables keep their own terms, permissions, and data practices.

Use is provided under the repository's [MIT License](../LICENSE), without warranty. Users remain responsible for reviewing generated changes, protecting secrets, deciding what external access to grant, and validating software before production use. Support and vulnerability reports should use the repository's public issue tracker without including credentials, personal data, or private production logs.

## First release note

Initial public submission of the skills-only Aegis Delivery plugin, package version 0.2.0 / protocol version 1.6. It includes one Codex-compatible skill, project initialization and task-record tooling, deterministic record validation, documentation, examples, and automated cross-platform checks. No MCP server, hosted backend, external account, or custom UI is included.
