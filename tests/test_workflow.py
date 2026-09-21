"""Run: python -m unittest discover -s tests -v (no external dependencies)."""

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/aegis-delivery/scripts/workflow.py"
spec = importlib.util.spec_from_file_location("workflow", SCRIPT)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def write_record(path: Path, record: dict) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.index(workflow.RECORD_START)
    end = text.index(workflow.RECORD_END, start) + len(workflow.RECORD_END)
    block = (workflow.RECORD_START + "\n```json\n"
             + json.dumps(record, ensure_ascii=False, indent=2)
             + "\n```\n" + workflow.RECORD_END)
    path.write_text(text[:start] + block + text[end:], encoding="utf-8", newline="\n")


def issue_codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


class WorkflowChecks(unittest.TestCase):
    def installed_task(self, root: Path, task_id: str = "TASK-001") -> tuple[Path, dict]:
        workflow.initialize(root, 4, 120)
        result = workflow.new_task(root, task_id, "修复分页")
        path = root / result["task"]
        return path, workflow.extract_task_record(path.read_text(encoding="utf-8"))

    def done_record(self, record: dict) -> dict:
        record["status"] = "DONE"
        record["artifact_id"] = "git:abc123+clean"
        record["knowledge_sync"] = {"status": "UPDATED", "reason": None}
        record["delivery"] = {
            "artifact_ref": "#artifact",
            "reproduce_ref": "#reproduce",
            "acceptance_ref": "#acceptance",
        }
        record["acs"][0].update({
            "description": "切换筛选后回到第一页",
            "applicability": "APPLICABLE",
            "executed": True,
            "verdict": "PASS",
            "evidence_batch": "EV-01",
        })
        record["evidence_batches"] = [{
            "id": "EV-01",
            "artifact_id": "git:abc123+clean",
            "environment": "Windows test",
            "inputs": ["page=3, filter=new"],
            "actions": ["python -m unittest"],
            "results": ["exit 0"],
            "report_locations": ["reports/test.txt"],
        }]
        return record

    def test_install_customize_repeat_task_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "中文项目 with spaces"
            root.mkdir()
            original = b"\xef\xbb\xbf# Existing rules\r\nDo not replace.\r\n"
            (root / "AGENTS.md").write_bytes(original)
            (root / "package.json").write_text("{}", encoding="utf-8")
            before = set(root.rglob("*"))
            self.assertEqual(workflow.inspect(root)["stack_hints"], ["package.json"])
            self.assertEqual(set(root.rglob("*")), before)
            result = workflow.initialize(root, 3, 90)
            self.assertFalse(result["runtime_verified"])
            self.assertTrue((root / "AGENTS.md").read_bytes().startswith(original))
            config = root / workflow.PROFILE
            data = json.loads(config.read_text(encoding="utf-8"))
            data["package_version"] = "0.1.0"
            data["commands"] = {"test": {"command": "custom-test", "status": "NOT_VERIFIED"}}
            data["future_field"] = {"preserved": True}
            config.write_bytes(workflow.encoded(data))
            snapshot = {path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
                        for path in root.rglob("*") if path.is_file()}
            self.assertEqual(workflow.initialize(root, 8, 300)["changed_files"], [])
            self.assertEqual(snapshot, {path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
                                       for path in root.rglob("*") if path.is_file()})
            self.assertEqual(workflow.check(root)["status"], "CONFIGURED")
            result = workflow.new_task(root, "TASK-001", '修复"分页"')
            content = (root / result["task"]).read_text(encoding="utf-8")
            record = workflow.extract_task_record(content)
            self.assertEqual(record["budgets"]["task_repairs_max"], 3)
            self.assertEqual(record["budgets"]["effective_minutes_max"], 90)
            self.assertEqual(record["title"], '修复"分页"')
            self.assertNotIn("{{", content)
            draft = workflow.validate_task(root, "TASK-001")
            self.assertTrue(draft["valid"])
            self.assertIn("AC_APPLICABILITY_UNKNOWN", issue_codes(draft))
            with self.assertRaises(FileExistsError):
                workflow.new_task(root, "TASK-001", "must not overwrite")
            installed = root / workflow.INSTALL / "SKILL.md"
            installed.write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                workflow.check(root)

    def test_project_profile_validation(self):
        mutations = {
            "schema bool": lambda data: data.update(schema_version=True),
            "package empty": lambda data: data.update(package_version=""),
            "root bool": lambda data: data["defaults"].update(root_repairs=True),
            "task bool": lambda data: data["defaults"].update(task_repairs=True),
            "command empty": lambda data: data.update(commands={"test": {"command": "", "status": "NOT_VERIFIED"}}),
            "command cwd": lambda data: data.update(commands={"test": {"command": "x", "cwd": "", "status": "NOT_VERIFIED"}}),
            "command status": lambda data: data.update(commands={"test": {"command": "x", "status": "PASS"}}),
            "knowledge path": lambda data: data.update(knowledge_paths=[""]),
            "baseline": lambda data: data.update(baseline="PASS"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                workflow.initialize(root, 4, 120)
                config = root / workflow.PROFILE
                data = json.loads(config.read_text(encoding="utf-8"))
                mutate(data)
                config.write_bytes(workflow.encoded(data))
                with self.assertRaises(ValueError) as caught:
                    workflow.profile(root)
                self.assertIn(":", str(caught.exception))

    def test_task_guard_done_na_conditional_optional_and_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, record = self.installed_task(root)
            record = self.done_record(record)
            write_record(path, record)
            self.assertTrue(workflow.validate_task(root, "TASK-001")["valid"])

            required_na = json.loads(json.dumps(record))
            required_na["acs"][0].update({
                "applicability": "NOT_APPLICABLE",
                "applicability_reason": "项目没有缓存层",
                "applicability_basis": "源码检索未发现缓存依赖",
                "applicability_decision_stage": "BEFORE_AC_EXECUTION",
                "executed": False,
                "verdict": "N/A",
                "evidence_batch": None,
            })
            required_na["evidence_batches"] = []
            write_record(path, required_na)
            self.assertTrue(workflow.validate_task(root, "TASK-001")["valid"])

            late_na = json.loads(json.dumps(required_na))
            late_na["acs"][0]["executed"] = True
            write_record(path, late_na)
            self.assertIn("AC_NA_AFTER_EXECUTION", issue_codes(workflow.validate_task(root, "TASK-001")))

            conditional = json.loads(json.dumps(required_na))
            conditional["acs"][0]["type"] = "CONDITIONAL"
            conditional["acs"][0]["trigger"] = {
                "description": "项目存在缓存层", "state": "TRIGGERED", "basis": "源码检查"
            }
            write_record(path, conditional)
            self.assertIn("AC_TRIGGER_APPLICABILITY_MISMATCH",
                          issue_codes(workflow.validate_task(root, "TASK-001")))

            conditional_na = json.loads(json.dumps(required_na))
            conditional_na["acs"][0].update({
                "type": "CONDITIONAL",
                "applicability_reason": None,
                "applicability_basis": None,
                "trigger": {"description": "项目存在缓存层", "state": "NOT_TRIGGERED",
                            "basis": "源码检索未发现缓存依赖"},
            })
            write_record(path, conditional_na)
            self.assertTrue(workflow.validate_task(root, "TASK-001")["valid"])

            optional_fail = self.done_record(json.loads(json.dumps(record)))
            optional_fail["acs"][0].update({"type": "OPTIONAL", "verdict": "FAIL"})
            write_record(path, optional_fail)
            self.assertTrue(workflow.validate_task(root, "TASK-001")["valid"])

            no_evidence = self.done_record(json.loads(json.dumps(record)))
            no_evidence["acs"][0]["evidence_batch"] = None
            write_record(path, no_evidence)
            self.assertIn("AC_PASS_EVIDENCE_INCOMPLETE",
                          issue_codes(workflow.validate_task(root, "TASK-001")))

            stale = self.done_record(json.loads(json.dumps(record)))
            stale["artifact_id"] = "git:new-artifact"
            write_record(path, stale)
            result = workflow.validate_task(root, "TASK-001")
            self.assertTrue(result["valid"])
            self.assertIn("EVIDENCE_ARTIFACT_MISMATCH", issue_codes(result))

    def test_human_verification_record_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, base = self.installed_task(root)

            passed = self.done_record(json.loads(json.dumps(base)))
            passed["evidence_batches"][0].update({
                "id": "H-01",
                "environment": "staging; human verifier",
                "inputs": ["test account; page=3, filter=new"],
                "actions": ["human changed and cleared the filter"],
                "results": ["page returned to 1 and filter behavior matched expectations"],
                "report_locations": ["#human-verification-h-01"],
            })
            passed["acs"][0]["evidence_batch"] = "H-01"
            write_record(path, passed)
            self.assertTrue(workflow.validate_task(root, "TASK-001")["valid"])

            failed = json.loads(json.dumps(passed))
            failed["status"] = "ACTIVE"
            failed["acs"][0]["verdict"] = "FAIL"
            failed["evidence_batches"][0]["results"] = ["page stayed on 3"]
            write_record(path, failed)
            self.assertTrue(workflow.validate_task(root, "TASK-001")["valid"])

            blocked = json.loads(json.dumps(base))
            blocked["status"] = "BLOCKED"
            blocked["artifact_id"] = "git:abc123+clean"
            blocked["acs"][0].update({
                "description": "切换筛选后回到第一页",
                "applicability": "APPLICABLE",
                "verdict": "BLOCKED",
            })
            write_record(path, blocked)
            self.assertTrue(workflow.validate_task(root, "TASK-001")["valid"])

            duplicate = json.loads(json.dumps(passed))
            duplicate["evidence_batches"].append(json.loads(json.dumps(duplicate["evidence_batches"][0])))
            write_record(path, duplicate)
            self.assertIn("FIELD_VALUE_INVALID", issue_codes(workflow.validate_task(root, "TASK-001")))

    def test_legacy_task_and_cli_validate_are_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow.initialize(root, 4, 120)
            task = root / ".ai-workflow/tasks/LEGACY-1.md"
            task.parent.mkdir(parents=True)
            task.write_text("# Legacy\n\nNOT_VERIFIED\n", encoding="utf-8")
            before = task.read_bytes()
            result = workflow.validate_task(root, "LEGACY-1")
            self.assertFalse(result["valid"])
            self.assertEqual(issue_codes(result), {"TASK_METADATA_MISSING"})
            self.assertEqual(task.read_bytes(), before)
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "validate-task", "--project", str(root), "--id", "LEGACY-1"],
                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONUTF8="1"),
            )
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(process.stdout)["issues"][0]["code"], "TASK_METADATA_MISSING")
            self.assertEqual(task.read_bytes(), before)

            current = root / ".ai-workflow/tasks/LEGACY-2.md"
            workflow.new_task(root, "LEGACY-2", "旧名称记录")
            legacy_text = current.read_text(encoding="utf-8").replace(
                workflow.RECORD_START, workflow.LEGACY_RECORD_START
            ).replace(workflow.RECORD_END, workflow.LEGACY_RECORD_END)
            current.write_text(legacy_text, encoding="utf-8", newline="\n")
            self.assertTrue(workflow.validate_task(root, "LEGACY-2")["valid"])

    def test_inspect_depth_sorting_exclusions_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("package.json", "apps/api/pyproject.toml", "apps/web/package.json",
                             "too/deep/nested/go.mod", "node_modules/pkg/package.json",
                             "README.md", "apps/api/tests"):
                path = root / relative
                if path.suffix or path.name == "README.md":
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
                else:
                    path.mkdir(parents=True, exist_ok=True)
            hints = workflow.inspect(root)
            self.assertEqual(hints["stack_hints"], [
                "apps/api/pyproject.toml", "apps/web/package.json", "package.json"
            ])
            self.assertEqual(hints["module_hints"], ["apps/api", "apps/web"])
            self.assertEqual(hints["context_hints"], ["README.md", "apps/api/tests"])
            self.assertFalse(hints["runtime_verified"])
            self.assertFalse(hints["writes"])
            outside = root.parent / (root.name + "-outside")
            outside.mkdir()
            (outside / "package.json").write_text("{}", encoding="utf-8")
            try:
                (root / "linked-module").symlink_to(outside, target_is_directory=True)
            except OSError:
                pass
            else:
                self.assertNotIn("linked-module/package.json", workflow.inspect(root)["stack_hints"])

    def test_conflict_preflight_and_input_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            conflict = root / workflow.INSTALL / "SKILL.md"
            conflict.parent.mkdir(parents=True)
            conflict.write_text("existing custom skill", encoding="utf-8")
            with self.assertRaises(ValueError):
                workflow.initialize(root, 4, 120)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / workflow.PROFILE).exists())
            self.assertEqual(conflict.read_text(encoding="utf-8"), "existing custom skill")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / workflow.LEGACY_INSTALL
            legacy.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "rename migration guide"):
                workflow.initialize(root, 4, 120)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / workflow.PROFILE).exists())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow.initialize(root, 4, 120)
            for task_id in ("../escape", "a/b", "a\\b", "CON", "x:y", "a" * 65):
                with self.subTest(task_id=task_id), self.assertRaises(ValueError):
                    workflow.new_task(root, task_id, "title")
            with self.assertRaises(ValueError):
                workflow.new_task(root, "valid", "line\nbreak")

    def test_managed_link_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, outside = base / "project", base / "outside"
            root.mkdir()
            outside.mkdir()
            try:
                (root / ".agents").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Host does not permit directory symlinks")
            with self.assertRaises(ValueError):
                workflow.initialize(root, 4, 120)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertFalse((root / "AGENTS.md").exists())

    def test_cli_and_standalone_installed_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = dict(os.environ, PYTHONUTF8="1")

            def run(script, *args):
                return subprocess.run([sys.executable, str(script), *args, "--project", str(root)],
                                      capture_output=True, text=True, encoding="utf-8", env=env)

            failed = run(SCRIPT, "init", "--max-repairs", "0")
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(json.loads(failed.stderr)["status"], "BLOCKED")
            self.assertEqual(list(root.iterdir()), [])
            self.assertEqual(run(SCRIPT, "init").returncode, 0)
            installed = root / workflow.INSTALL / "scripts/workflow.py"
            repeated = run(installed, "init")
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout)["changed_files"], [])
            self.assertEqual(run(installed, "check").returncode, 0)
            task = run(installed, "new-task", "--id", "TASK-002", "--title", "独立安装")
            self.assertEqual(task.returncode, 0, task.stderr)
            guard = run(installed, "validate-task", "--id", "TASK-002")
            self.assertEqual(guard.returncode, 0, guard.stderr)
            self.assertTrue(json.loads(guard.stdout)["valid"])

    def test_package_metadata_and_local_document_links(self):
        portable = json.loads((REPO / "plugin.json").read_text(encoding="utf-8"))
        compatibility = json.loads((REPO / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(portable["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        self.assertNotIn("skills", portable)
        self.assertNotIn("extensions", portable)
        for key in ("name", "version", "description", "author", "homepage", "repository", "license", "keywords"):
            self.assertEqual(portable[key], compatibility[key])
        self.assertEqual(portable["version"], workflow.VERSION)
        self.assertTrue((REPO / compatibility["skills"]).is_dir())
        skill = (workflow.SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: aegis-delivery\n"))
        self.assertIn("description:", skill.split("---", 2)[1])
        openai_yaml = (workflow.SKILL / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", openai_yaml)
        for readme_name in ("README.md", "README.en.md"):
            public_readme = (REPO / readme_name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"workflow(?:\\)?\.py\s+validate-task", public_readme),
                              f"Public README exposes the maintainer-only Guard command: {readme_name}")
        example = (REPO / "examples/bug-fix.md").read_text(encoding="utf-8")
        example_result = workflow.validate_record(workflow.extract_task_record(example), "EXAMPLE-BUG-001")
        self.assertTrue(example_result["valid"])
        self.assertIn("AC_APPLICABILITY_UNKNOWN", issue_codes(example_result))
        for path in REPO.rglob("*.md"):
            if ".git" in path.parts:
                continue
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                resolved = (path.parent / target.split("#")[0]).resolve()
                self.assertTrue(resolved.is_relative_to(REPO), f"Link escapes repository: {path}: {target}")
                self.assertTrue(resolved.exists(), f"Broken link: {path}: {target}")


if __name__ == "__main__":
    unittest.main()
