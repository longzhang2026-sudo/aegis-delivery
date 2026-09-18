#!/usr/bin/env python3
"""Project-local installer and task starter. Python 3.10+, standard library only."""

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

VERSION = "0.1.0"
SKILL = Path(__file__).resolve().parents[1]
INSTALL = ".agents/skills/ai-delivery"
PROFILE = ".ai-workflow/project.json"
RECEIPT = ".ai-workflow/install.json"
START = "<!-- ai-delivery:start -->"
END = "<!-- ai-delivery:end -->"
BLOCK = f"""{START}
## AI Delivery workflow
For requested software delivery, initialization, verification or task recovery,
read `.agents/skills/ai-delivery/SKILL.md` and `.ai-workflow/project.json`.
Keep one task record. Actual evidence is required for acceptance; installation
checks do not prove application correctness. Preserve existing project rules.
{END}"""


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
    path.resolve().relative_to(root)
    return path


def encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("protocol") != "1.6":
        raise ValueError("Unsupported project profile; expected schema 1, protocol 1.6")
    limits = data.get("defaults", {})
    if not isinstance(limits, dict):
        raise ValueError("defaults must be an object")
    for key in ("task_repairs", "effective_minutes"):
        if type(limits.get(key)) is not int or limits[key] < 1:
            raise ValueError(f"Invalid positive integer: defaults.{key}")
    if limits.get("root_repairs") != 2 or limits.get("replans") != 1:
        raise ValueError("Protocol 1.6 requires root_repairs=2 and replans=1")
    if not isinstance(data.get("commands"), dict):
        raise ValueError("commands must be an object")
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
    # Preserve original bytes, including BOM and line endings, when appending.
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    addition = BLOCK.replace("\n", newline.decode()).encode("utf-8") + newline
    return raw + (newline * 2 if raw else b"") + addition


def inspect(root: Path) -> dict:
    # ponytail: top-level hints only; let the agent inspect actual monorepo commands.
    markers = [name for name in ("package.json", "pyproject.toml", "requirements.txt",
                                "pom.xml", "build.gradle", "go.mod", "Cargo.toml")
               if managed(root, name).is_file()]
    return {"status": "INSTALLED_PENDING_CHECK" if managed(root, PROFILE).exists() else "NOT_INSTALLED",
            "stack_hints": markers, "python": sys.version.split()[0],
            "runtime_verified": False, "writes": False}


def initialize(root: Path, repairs: int, minutes: int) -> dict:
    if repairs < 1 or minutes < 1:
        raise ValueError("Budgets must be positive integers")
    source = skill_files()
    planned = {f"{INSTALL}/{name}": content for name, content in source.items()}
    config = {"schema_version": 1, "protocol": "1.6", "package_version": VERSION,
              "defaults": {"root_repairs": 2, "task_repairs": repairs,
                           "effective_minutes": minutes, "replans": 1},
              "commands": {}, "knowledge_paths": [],
              "baseline": "NOT_VERIFIED"}
    config_path = managed(root, PROFILE)
    if config_path.exists():
        profile(root)  # Preserve customized commands, budgets and baseline.
    else:
        planned[PROFILE] = encoded(config)
    planned[RECEIPT] = encoded({"package_version": VERSION, "files": {
        f"{INSTALL}/{name}": digest(content) for name, content in source.items()}})
    planned["AGENTS.md"] = agents_content(root)
    writes = []
    # Preflight every collision before the first write. No force/overwrite option.
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
        # Atomic per file; a disk failure can leave a partial install. Rerun to resume.
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"status": "INSTALLED_PENDING_CHECK", "changed_files": [p.relative_to(root).as_posix() for p, _ in writes],
            "runtime_verified": False, "defaults": profile(root)["defaults"]}


def check(root: Path) -> dict:
    profile(root)
    record = json.loads(managed(root, RECEIPT).read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Invalid installation receipt")
    files = record.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Missing installation file hashes")
    required = {f"{INSTALL}/{name}" for name in (
        "SKILL.md", "scripts/workflow.py", "assets/task.md",
        "references/protocol.md", "references/initialization.md", "agents/openai.yaml")}
    if not required.issubset(files):
        raise ValueError("Installation receipt is incomplete")
    for name, expected in files.items():
        if not name.startswith(INSTALL + "/"):
            raise ValueError("Installation receipt includes an unmanaged file")
        if digest(managed(root, name).read_bytes()) != expected:
            raise ValueError(f"Installed file changed or incomplete: {name}")
    path = managed(root, "AGENTS.md")
    if not path.is_file():
        raise ValueError("Missing AGENTS.md")
    raw = path.read_bytes()
    if START not in raw.decode("utf-8-sig") or agents_content(root) != raw:
        raise ValueError("Missing AGENTS.md managed block")
    return {"status": "CONFIGURED", "runtime_verified": False,
            "message": "Static installation checks passed. Run and record project baseline separately."}


def new_task(root: Path, task_id: str, title: str) -> dict:
    check(root)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", task_id):
        raise ValueError("Task ID must be 1-64 letters/digits/hyphens/underscores")
    if task_id.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}:
        raise ValueError("Reserved Windows task ID")
    if not title.strip() or len(title) > 200 or any(ord(c) < 32 for c in title):
        raise ValueError("Title must be one nonempty line, at most 200 characters")
    path = managed(root, f".ai-workflow/tasks/{task_id}.md")
    template = managed(root, f"{INSTALL}/assets/task.md").read_text(encoding="utf-8")
    limits = profile(root)["defaults"]
    values = {"TASK_ID": task_id, "TITLE": title.strip(),
              "TASK_REPAIRS": str(limits["task_repairs"]),
              "EFFECTIVE_MINUTES": str(limits["effective_minutes"])}
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(template)
    return {"status": "DRAFT", "task": path.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "init", "check", "new-task"):
        command = commands.add_parser(name)
        command.add_argument("--project", required=True, type=Path)
        if name == "init":
            command.add_argument("--max-repairs", type=int, default=4)
            command.add_argument("--time-limit-minutes", type=int, default=120)
        if name == "new-task":
            command.add_argument("--id", required=True)
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
        else:
            result = new_task(root, args.id, args.title)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
