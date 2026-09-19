#!/usr/bin/env python3
"""Project-local installer, inspector, task starter, and task record guard."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

VERSION = "0.2.0"
SKILL = Path(__file__).resolve().parents[1]
INSTALL = ".agents/skills/ai-delivery"
PROFILE = ".ai-workflow/project.json"
RECEIPT = ".ai-workflow/install.json"
START = "<!-- ai-delivery:start -->"
END = "<!-- ai-delivery:end -->"
RECORD_START = "<!-- ai-delivery-record:start -->"
RECORD_END = "<!-- ai-delivery-record:end -->"
BLOCK = f"""{START}
## AI Delivery workflow
For requested software delivery, initialization, verification or task recovery,
read `.agents/skills/ai-delivery/SKILL.md` and `.ai-workflow/project.json`.
Keep one task record. Actual evidence is required for acceptance; installation
checks do not prove application correctness. Preserve existing project rules.
{END}"""

STACK_MARKERS = {
    "Cargo.toml", "build.gradle", "build.gradle.kts", "go.mod", "package.json",
    "pom.xml", "pyproject.toml", "requirements.txt", "settings.gradle",
    "settings.gradle.kts",
}
CONTEXT_DIRS = {"docs", "test", "tests"}
EXCLUDED_DIRS = {
    ".agents", ".ai-workflow", ".git", ".mypy_cache", ".pytest_cache", ".venv",
    "__pycache__", "build", "coverage", "dist", "node_modules", "out", "target", "venv",
}
TASK_STATUSES = {"DRAFT", "ACTIVE", "BLOCKED", "HUMAN_GATE", "DONE", "FAILED", "CANCELLED"}
RISKS = {"LOW", "NORMAL", "HIGH"}
AC_TYPES = {"REQUIRED", "CONDITIONAL", "OPTIONAL"}
APPLICABILITY = {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}
VERDICTS = {"PASS", "FAIL", "NOT_VERIFIED", "BLOCKED", "N/A"}
TRIGGER_STATES = {"TRIGGERED", "NOT_TRIGGERED", "UNKNOWN"}
TRIGGER_MAP = {"TRIGGERED": "APPLICABLE", "NOT_TRIGGERED": "NOT_APPLICABLE", "UNKNOWN": "UNKNOWN"}


def linked(path: Path) -> bool:
    """Reject symlinks and Windows junction/reparse points in managed paths."""
    return path.is_symlink() or (
        path.exists()
        and bool(getattr(path.lstat(), "st_file_attributes", 0)
                 & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    )


def managed(root: Path, relative: str) -> Path:
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in {".", ".."} or ":" in p for p in parts):
        raise ValueError(f"Unsafe managed path: {relative}")
    path = root
    for part in parts:
        path = path / part
        if linked(path):
            raise ValueError(f"Managed path is a link/reparse point: {path}")
    path.resolve().relative_to(root.resolve())
    return path


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def integer(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def skill_files() -> dict[str, bytes]:
    result = {}
    for path in sorted(SKILL.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if linked(path):
            raise ValueError(f"Source skill must not contain links: {path}")
        if path.is_file():
            result[path.relative_to(SKILL).as_posix()] = path.read_bytes()
    return result


def profile(root: Path) -> dict:
    data = json.loads(managed(root, PROFILE).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("project: must be an object")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version: expected integer 1")
    if data.get("protocol") != "1.6":
        raise ValueError('protocol: expected string "1.6"')
    package_version = data.get("package_version")
    if not nonempty(package_version) or not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", package_version):
        raise ValueError("package_version: expected a nonempty SemVer-like string")
    limits = data.get("defaults")
    if not isinstance(limits, dict):
        raise ValueError("defaults: must be an object")
    for key in ("root_repairs", "task_repairs", "effective_minutes", "replans"):
        if not integer(limits.get(key), 1):
            raise ValueError(f"defaults.{key}: expected a positive integer")
    if limits["root_repairs"] != 2:
        raise ValueError("defaults.root_repairs: protocol 1.6 requires 2")
    if limits["replans"] != 1:
        raise ValueError("defaults.replans: protocol 1.6 requires 1")
    commands = data.get("commands")
    if not isinstance(commands, dict):
        raise ValueError("commands: must be an object")
    for name, command in commands.items():
        path = f"commands.{name}"
        if not nonempty(name):
            raise ValueError("commands: command names must be nonempty strings")
        if not isinstance(command, dict):
            raise ValueError(f"{path}: must be an object")
        if not nonempty(command.get("command")):
            raise ValueError(f"{path}.command: must be a nonempty string")
        if "cwd" in command and not nonempty(command["cwd"]):
            raise ValueError(f"{path}.cwd: must be a nonempty string when present")
        if command.get("status") not in {"NOT_VERIFIED", "VERIFIED", "BLOCKED"}:
            raise ValueError(f"{path}.status: expected NOT_VERIFIED, VERIFIED, or BLOCKED")
    knowledge_paths = data.get("knowledge_paths")
    if not isinstance(knowledge_paths, list) or any(not nonempty(value) for value in knowledge_paths):
        raise ValueError("knowledge_paths: expected an array of nonempty strings")
    if data.get("baseline") not in {"NOT_VERIFIED", "READY", "BLOCKED"}:
        raise ValueError("baseline: expected NOT_VERIFIED, READY, or BLOCKED")
    return data


def agents_content(root: Path) -> bytes:
    path = managed(root, "AGENTS.md")
    raw = path.read_bytes() if path.exists() else b""
    text = raw.decode("utf-8-sig")
    if START in text or END in text:
        if text.count(START) != 1 or text.count(END) != 1:
            raise ValueError("Conflicting AGENTS.md managed markers; review manually")
        segment = text[text.index(START):text.index(END) + len(END)]
        if segment.replace("\r\n", "\n") != BLOCK:
            raise ValueError("AGENTS.md managed block differs; review manually")
        return raw
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    addition = BLOCK.replace("\n", newline.decode()).encode("utf-8") + newline
    return raw + (newline * 2 if raw else b"") + addition


def inspect(root: Path) -> dict:
    stack_hints: list[str] = []
    module_hints: set[str] = set()
    context_hints: list[str] = []
    pending = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        for path in sorted(directory.iterdir(), key=lambda value: value.name.casefold(), reverse=True):
            if linked(path):
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_file():
                if path.name in STACK_MARKERS:
                    stack_hints.append(relative)
                    if path.parent != root:
                        module_hints.add(path.parent.relative_to(root).as_posix())
                if path.name.casefold().startswith("readme"):
                    context_hints.append(relative)
            elif path.is_dir() and path.name not in EXCLUDED_DIRS:
                if path.name.casefold() in CONTEXT_DIRS:
                    context_hints.append(relative)
                if depth < 2:
                    pending.append((path, depth + 1))
    return {
        "status": "INSTALLED_PENDING_CHECK" if managed(root, PROFILE).exists() else "NOT_INSTALLED",
        "stack_hints": sorted(stack_hints),
        "module_hints": sorted(module_hints),
        "context_hints": sorted(set(context_hints)),
        "python": sys.version.split()[0],
        "runtime_verified": False,
        "writes": False,
    }


def initialize(root: Path, repairs: int, minutes: int) -> dict:
    if not integer(repairs, 1) or not integer(minutes, 1):
        raise ValueError("Budgets must be positive integers")
    source = skill_files()
    planned = {f"{INSTALL}/{name}": content for name, content in source.items()}
    config = {"schema_version": 1, "protocol": "1.6", "package_version": VERSION,
              "defaults": {"root_repairs": 2, "task_repairs": repairs,
                           "effective_minutes": minutes, "replans": 1},
              "commands": {}, "knowledge_paths": [], "baseline": "NOT_VERIFIED"}
    config_path = managed(root, PROFILE)
    if config_path.exists():
        profile(root)
    else:
        planned[PROFILE] = encoded(config)
    planned[RECEIPT] = encoded({"package_version": VERSION, "files": {
        f"{INSTALL}/{name}": digest(content) for name, content in source.items()}})
    planned["AGENTS.md"] = agents_content(root)
    writes = []
    for name, content in planned.items():
        path = managed(root, name)
        for parent in path.parents:
            if parent == root:
                break
            if parent.exists() and not parent.is_dir():
                raise ValueError(f"Parent is not a directory: {parent}")
        if path.exists():
            if not path.is_file():
                raise ValueError(f"Expected a file: {path}")
            if path.read_bytes() == content:
                continue
            if name != "AGENTS.md":
                raise ValueError(f"Existing file differs; no files changed: {path}")
        writes.append((path, content))
    for path, content in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"status": "INSTALLED_PENDING_CHECK",
            "changed_files": [path.relative_to(root).as_posix() for path, _ in writes],
            "runtime_verified": False, "defaults": profile(root)["defaults"]}


def check(root: Path) -> dict:
    profile(root)
    record = json.loads(managed(root, RECEIPT).read_text(encoding="utf-8"))
    if not isinstance(record, dict) or not nonempty(record.get("package_version")):
        raise ValueError("Invalid installation receipt")
    files = record.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Missing installation file hashes")
    required = {f"{INSTALL}/{name}" for name in (
        "SKILL.md", "scripts/workflow.py", "assets/task.md", "references/protocol.md",
        "references/initialization.md", "references/task-record-schema.md", "agents/openai.yaml")}
    if not required.issubset(files):
        raise ValueError("Installation receipt is incomplete")
    for name, expected in files.items():
        if not name.startswith(INSTALL + "/"):
            raise ValueError("Installation receipt includes an unmanaged file")
        if not nonempty(expected) or digest(managed(root, name).read_bytes()) != expected:
            raise ValueError(f"Installed file changed or incomplete: {name}")
    path = managed(root, "AGENTS.md")
    if not path.is_file():
        raise ValueError("Missing AGENTS.md")
    raw = path.read_bytes()
    if START not in raw.decode("utf-8-sig") or agents_content(root) != raw:
        raise ValueError("Missing AGENTS.md managed block")
    return {"status": "CONFIGURED", "runtime_verified": False,
            "message": "Static installation checks passed. Run and record project baseline separately."}


def validate_task_id(task_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", task_id):
        raise ValueError("Task ID must be 1-64 letters/digits/hyphens/underscores")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}
    if task_id.split(".")[0].upper() in reserved:
        raise ValueError("Reserved Windows task ID")


def valid_title(title: str) -> bool:
    return nonempty(title) and len(title) <= 200 and not any(ord(char) < 32 for char in title)


def new_task(root: Path, task_id: str, title: str) -> dict:
    check(root)
    validate_task_id(task_id)
    if not valid_title(title):
        raise ValueError("Title must be one nonempty line, at most 200 characters")
    path = managed(root, f".ai-workflow/tasks/{task_id}.md")
    template = managed(root, f"{INSTALL}/assets/task.md").read_text(encoding="utf-8")
    limits = profile(root)["defaults"]
    values = {
        "TASK_ID": task_id,
        "TITLE": title.strip(),
        "TASK_ID_JSON": json.dumps(task_id, ensure_ascii=False),
        "TITLE_JSON": json.dumps(title.strip(), ensure_ascii=False),
        "TASK_REPAIRS": str(limits["task_repairs"]),
        "EFFECTIVE_MINUTES": str(limits["effective_minutes"]),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(template)
    return {"status": "DRAFT", "task": path.relative_to(root).as_posix()}


def extract_task_record(text: str) -> dict:
    if text.count(RECORD_START) != 1 or text.count(RECORD_END) != 1:
        raise ValueError("Task record must contain exactly one machine block")
    start = text.index(RECORD_START) + len(RECORD_START)
    end = text.index(RECORD_END, start)
    block = text[start:end].strip()
    lines = block.splitlines()
    if len(lines) < 3 or lines[0].strip() != "```json" or lines[-1].strip() != "```":
        raise ValueError("Task machine block must contain one fenced json object")
    record = json.loads("\n".join(lines[1:-1]))
    if not isinstance(record, dict):
        raise ValueError("Task machine block must be a JSON object")
    return record


def add_issue(issues: list[dict], level: str, code: str, path: str, message: str) -> None:
    issues.append({"level": level, "code": code, "path": path, "message": message})


def field_enum(record: dict, key: str, values: set[str], issues: list[dict], path: str | None = None) -> object:
    value = record.get(key)
    field_path = path or key
    if value not in values:
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", field_path,
                  f"Expected one of: {', '.join(sorted(values))}")
    return value


def nullable_string(value: object) -> bool:
    return value is None or nonempty(value)


def string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(nonempty(item) for item in value)


def validate_record(record: dict, expected_task_id: str) -> dict:
    issues: list[dict] = []
    if type(record.get("record_schema_version")) is not int or record["record_schema_version"] != 1:
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "record_schema_version", "Expected integer 1")
    task_id = record.get("task_id")
    if not nonempty(task_id) or task_id != expected_task_id:
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "task_id", "Must match the task filename and --id")
    title = record.get("title")
    if not isinstance(title, str) or not valid_title(title):
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "title", "Expected one nonempty line, at most 200 characters")
    status = field_enum(record, "status", TASK_STATUSES, issues)
    field_enum(record, "risk", RISKS, issues)
    if not integer(record.get("contract_version"), 1):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "contract_version", "Expected a positive integer")

    confirmation = record.get("customer_confirmation")
    if not isinstance(confirmation, dict):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "customer_confirmation", "Expected an object")
        confirmation = {}
    required = confirmation.get("required")
    confirmation_status = confirmation.get("status")
    if type(required) is not bool:
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "customer_confirmation.required", "Expected a boolean")
    if confirmation_status not in {"NOT_REQUIRED", "PENDING", "CONFIRMED"}:
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "customer_confirmation.status",
                  "Expected NOT_REQUIRED, PENDING, or CONFIRMED")
    elif required is False and confirmation_status != "NOT_REQUIRED":
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "customer_confirmation.status",
                  "required=false requires NOT_REQUIRED")
    elif required is True and confirmation_status == "NOT_REQUIRED":
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "customer_confirmation.status",
                  "required=true cannot use NOT_REQUIRED")

    budgets = record.get("budgets")
    usage = record.get("usage")
    if not isinstance(budgets, dict):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "budgets", "Expected an object")
        budgets = {}
    if not isinstance(usage, dict):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "usage", "Expected an object")
        usage = {}
    expected_limits = {"root_repairs_max": 2, "replans_max": 1}
    for key in ("root_repairs_max", "task_repairs_max", "replans_max", "effective_minutes_max"):
        if not integer(budgets.get(key), 1):
            add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"budgets.{key}", "Expected a positive integer")
    for key, expected in expected_limits.items():
        if integer(budgets.get(key), 1) and budgets[key] != expected:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"budgets.{key}", f"Protocol 1.6 requires {expected}")
    root_usage = usage.get("root_repairs_by_id")
    if not isinstance(root_usage, dict):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "usage.root_repairs_by_id", "Expected an object")
    else:
        for root_id, value in root_usage.items():
            path = f"usage.root_repairs_by_id.{root_id}"
            if not nonempty(root_id) or not integer(value):
                add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", path, "Expected a nonnegative integer under a nonempty root id")
            elif value > 2:
                add_issue(issues, "ERROR", "BUDGET_EXCEEDED", path, "Root repair count exceeds 2")
    for used_key, limit_key in (("task_repairs", "task_repairs_max"),
                                ("replans", "replans_max"),
                                ("effective_minutes", "effective_minutes_max")):
        value = usage.get(used_key)
        if not integer(value):
            add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"usage.{used_key}", "Expected a nonnegative integer")
        elif integer(budgets.get(limit_key), 1) and value > budgets[limit_key]:
            add_issue(issues, "ERROR", "BUDGET_EXCEEDED", f"usage.{used_key}", "Usage exceeds its budget")

    artifact_id = record.get("artifact_id")
    if not nullable_string(artifact_id):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "artifact_id", "Expected null or a nonempty string")
    knowledge = record.get("knowledge_sync")
    if not isinstance(knowledge, dict):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "knowledge_sync", "Expected an object")
        knowledge = {}
    knowledge_status = knowledge.get("status")
    if knowledge_status not in {"PENDING", "UPDATED", "NO_INCREMENT", "SYNC_FAILED"}:
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "knowledge_sync.status",
                  "Expected PENDING, UPDATED, NO_INCREMENT, or SYNC_FAILED")
    if not nullable_string(knowledge.get("reason")):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "knowledge_sync.reason", "Expected null or a nonempty string")
    if knowledge_status in {"NO_INCREMENT", "SYNC_FAILED"} and not nonempty(knowledge.get("reason")):
        add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", "knowledge_sync.reason", "This status requires a reason")
    delivery = record.get("delivery")
    if not isinstance(delivery, dict):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "delivery", "Expected an object")
        delivery = {}
    for key in ("artifact_ref", "reproduce_ref", "acceptance_ref"):
        if not nullable_string(delivery.get(key)):
            add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"delivery.{key}", "Expected null or a nonempty string")

    batches = record.get("evidence_batches")
    batch_map: dict[str, dict] = {}
    if not isinstance(batches, list):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "evidence_batches", "Expected an array")
        batches = []
    for index, batch in enumerate(batches):
        path = f"evidence_batches[{index}]"
        if not isinstance(batch, dict):
            add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", path, "Expected an object")
            continue
        batch_id = batch.get("id")
        if not nonempty(batch_id):
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.id", "Expected a nonempty string")
        elif batch_id in batch_map:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.id", "Evidence batch id must be unique")
        else:
            batch_map[batch_id] = batch
        for key in ("artifact_id", "environment"):
            if not nonempty(batch.get(key)):
                add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.{key}", "Expected a nonempty string")
        for key in ("inputs", "actions", "results", "report_locations"):
            if not string_list(batch.get(key)):
                add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.{key}", "Expected a nonempty array of nonempty strings")

    acs = record.get("acs")
    if not isinstance(acs, list):
        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", "acs", "Expected an array")
        acs = []
    seen_ac: set[str] = set()
    for index, ac in enumerate(acs):
        path = f"acs[{index}]"
        if not isinstance(ac, dict):
            add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", path, "Expected an object")
            continue
        ac_id = ac.get("id")
        if not nonempty(ac_id):
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.id", "Expected a nonempty string")
        elif ac_id in seen_ac:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.id", "AC id must be unique")
        else:
            seen_ac.add(ac_id)
        ac_type = ac.get("type")
        applicability = ac.get("applicability")
        verdict = ac.get("verdict")
        if ac_type not in AC_TYPES:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.type", "Expected REQUIRED, CONDITIONAL, or OPTIONAL")
        if applicability not in APPLICABILITY:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.applicability",
                      "Expected APPLICABLE, NOT_APPLICABLE, or UNKNOWN")
        if verdict not in VERDICTS:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.verdict",
                      "Expected PASS, FAIL, NOT_VERIFIED, BLOCKED, or N/A")
        description = ac.get("description")
        if not nullable_string(description):
            add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"{path}.description", "Expected null or a nonempty string")
        elif description is None:
            level = "ERROR" if status == "DONE" else "WARN"
            add_issue(issues, level, "AC_DESCRIPTION_MISSING", f"{path}.description", "Acceptance behavior is not defined")
        for key in ("applicability_reason", "applicability_basis", "decision_ref", "evidence_batch"):
            if not nullable_string(ac.get(key)):
                add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"{path}.{key}", "Expected null or a nonempty string")
        stage = ac.get("applicability_decision_stage")
        if stage not in {None, "BEFORE_AC_EXECUTION", "AFTER_AC_EXECUTION"}:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.applicability_decision_stage",
                      "Expected null, BEFORE_AC_EXECUTION, or AFTER_AC_EXECUTION")
        if type(ac.get("executed")) is not bool:
            add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"{path}.executed", "Expected a boolean")

        trigger = ac.get("trigger")
        trigger_state = None
        if ac_type == "CONDITIONAL":
            if not isinstance(trigger, dict):
                add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"{path}.trigger", "Conditional AC requires a trigger object")
            else:
                trigger_state = trigger.get("state")
                if trigger_state not in TRIGGER_STATES:
                    add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.trigger.state",
                              "Expected TRIGGERED, NOT_TRIGGERED, or UNKNOWN")
                for key in ("description", "basis"):
                    if not nullable_string(trigger.get(key)):
                        add_issue(issues, "ERROR", "FIELD_TYPE_INVALID", f"{path}.trigger.{key}",
                                  "Expected null or a nonempty string")
                if trigger_state in TRIGGER_MAP and applicability in APPLICABILITY and TRIGGER_MAP[trigger_state] != applicability:
                    add_issue(issues, "ERROR", "AC_TRIGGER_APPLICABILITY_MISMATCH", f"{path}.applicability",
                              f"{trigger_state} requires {TRIGGER_MAP[trigger_state]}")
        elif trigger is not None:
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.trigger", "Only Conditional AC uses trigger")

        if applicability == "UNKNOWN":
            level = "ERROR" if status == "DONE" else "WARN"
            add_issue(issues, level, "AC_APPLICABILITY_UNKNOWN", f"{path}.applicability",
                      "Applicability still needs a decision")
            if verdict in {"PASS", "FAIL", "N/A"}:
                add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.verdict", "UNKNOWN applicability cannot have this verdict")
        if applicability == "APPLICABLE" and verdict == "N/A":
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.verdict", "Applicable AC cannot be N/A")
        if applicability == "NOT_APPLICABLE" and verdict != "N/A":
            add_issue(issues, "ERROR", "FIELD_VALUE_INVALID", f"{path}.verdict", "Not-applicable AC must use N/A")
        if verdict == "N/A":
            trigger_reason = trigger.get("description") if isinstance(trigger, dict) else None
            trigger_basis = trigger.get("basis") if isinstance(trigger, dict) else None
            if not (nonempty(ac.get("applicability_reason")) or nonempty(trigger_reason)) or not (
                    nonempty(ac.get("applicability_basis")) or nonempty(ac.get("decision_ref"))
                    or nonempty(trigger_basis)):
                add_issue(issues, "ERROR", "AC_NA_BASIS_MISSING", path,
                          "N/A requires a reason and a basis source")
            if stage != "BEFORE_AC_EXECUTION" or ac.get("executed") is not False or ac.get("evidence_batch") is not None:
                add_issue(issues, "ERROR", "AC_NA_AFTER_EXECUTION", path,
                          "N/A must be decided before AC execution and have no Evidence reference")
        evidence_id = ac.get("evidence_batch")
        if verdict in {"PASS", "FAIL"}:
            code = "AC_PASS_EVIDENCE_INCOMPLETE" if verdict == "PASS" else "AC_FAIL_EVIDENCE_INCOMPLETE"
            if ac.get("executed") is not True or not nonempty(evidence_id) or evidence_id not in batch_map:
                add_issue(issues, "ERROR", code, f"{path}.evidence_batch",
                          f"{verdict} requires executed=true and a complete Evidence batch")
        if nonempty(evidence_id) and evidence_id not in batch_map:
            add_issue(issues, "ERROR", "AC_EVIDENCE_REFERENCE_UNKNOWN", f"{path}.evidence_batch",
                      "Referenced Evidence batch does not exist")
        if nonempty(evidence_id) and evidence_id in batch_map and nonempty(artifact_id):
            if batch_map[evidence_id].get("artifact_id") != artifact_id:
                add_issue(issues, "WARN", "EVIDENCE_ARTIFACT_MISMATCH", f"{path}.evidence_batch",
                          "Evidence refers to a different artifact; re-verify before relying on it")

        if status == "DONE":
            required_now = ac_type == "REQUIRED" or (ac_type == "CONDITIONAL" and trigger_state == "TRIGGERED")
            if required_now and not (
                (applicability == "APPLICABLE" and verdict == "PASS")
                or (ac_type == "REQUIRED" and applicability == "NOT_APPLICABLE" and verdict == "N/A")
            ):
                add_issue(issues, "ERROR", "DONE_REQUIRED_AC_UNSATISFIED", path,
                          "DONE requires every applicable Required or triggered Conditional AC to pass")

    if status == "DONE":
        if not acs:
            add_issue(issues, "ERROR", "DONE_REQUIRED_AC_UNSATISFIED", "acs", "DONE requires at least one AC")
        if not nonempty(artifact_id) or any(not nonempty(delivery.get(key)) for key in (
                "artifact_ref", "reproduce_ref", "acceptance_ref")):
            add_issue(issues, "ERROR", "DONE_DELIVERY_INCOMPLETE", "delivery",
                      "DONE requires artifact_id and Artifact/Reproduce/Acceptance references")
        if knowledge_status not in {"UPDATED", "NO_INCREMENT"}:
            add_issue(issues, "ERROR", "DONE_KNOWLEDGE_SYNC_INCOMPLETE", "knowledge_sync.status",
                      "DONE requires UPDATED or NO_INCREMENT")
        if required is True and confirmation_status != "CONFIRMED":
            add_issue(issues, "ERROR", "DONE_CUSTOMER_CONFIRMATION_PENDING", "customer_confirmation.status",
                      "Required customer confirmation is still pending")

    issues.sort(key=lambda item: (item["path"], item["code"], item["level"], item["message"]))
    return {"valid": not any(issue["level"] == "ERROR" for issue in issues),
            "status": status if isinstance(status, str) else None, "issues": issues}


def validate_task(root: Path, task_id: str) -> dict:
    check(root)
    validate_task_id(task_id)
    path = managed(root, f".ai-workflow/tasks/{task_id}.md")
    if not path.is_file():
        raise ValueError(f"Task file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if RECORD_START not in text and RECORD_END not in text:
        return {"valid": False, "status": None, "issues": [{
            "level": "ERROR", "code": "TASK_METADATA_MISSING", "path": "$",
            "message": "Legacy task has no schema v1 machine block; migrate it manually without inventing evidence",
        }]}
    try:
        record = extract_task_record(text)
    except (ValueError, json.JSONDecodeError) as error:
        return {"valid": False, "status": None, "issues": [{
            "level": "ERROR", "code": "RECORD_JSON_INVALID", "path": "$",
            "message": str(error),
        }]}
    return validate_record(record, task_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "init", "check", "new-task", "validate-task"):
        command = commands.add_parser(name)
        command.add_argument("--project", required=True, type=Path)
        if name == "init":
            command.add_argument("--max-repairs", type=int, default=4)
            command.add_argument("--time-limit-minutes", type=int, default=120)
        if name in {"new-task", "validate-task"}:
            command.add_argument("--id", required=True)
        if name == "new-task":
            command.add_argument("--title", required=True)
    args = parser.parse_args()
    try:
        root = args.project.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Project must be an existing directory")
        if args.command == "inspect":
            result = inspect(root)
        elif args.command == "init":
            result = initialize(root, args.max_repairs, args.time_limit_minutes)
        elif args.command == "check":
            result = check(root)
        elif args.command == "new-task":
            result = new_task(root, args.id, args.title)
        else:
            result = validate_task(root, args.id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.command != "validate-task" or result["valid"] else 2
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
