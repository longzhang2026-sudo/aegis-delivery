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
SCRIPT = REPO / "skills/ai-delivery/scripts/workflow.py"
spec = importlib.util.spec_from_file_location("workflow", SCRIPT)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class WorkflowChecks(unittest.TestCase):
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
            data["commands"] = {"test": {"command": "custom-test", "status": "NOT_VERIFIED"}}
            config.write_bytes(workflow.encoded(data))
            snapshot = {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
                        for p in root.rglob("*") if p.is_file()}
            self.assertEqual(workflow.initialize(root, 8, 300)["changed_files"], [])
            self.assertEqual(snapshot, {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
                                       for p in root.rglob("*") if p.is_file()})
            self.assertEqual(workflow.check(root)["status"], "CONFIGURED")
            result = workflow.new_task(root, "TASK-001", "修复分页")
            content = (root / result["task"]).read_text(encoding="utf-8")
            self.assertIn("任务总修复 3 次", content)
            self.assertIn("NOT_VERIFIED", content)
            self.assertNotIn("{{", content)
            with self.assertRaises(FileExistsError):
                workflow.new_task(root, "TASK-001", "must not overwrite")
            installed = root / workflow.INSTALL / "SKILL.md"
            installed.write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                workflow.check(root)

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
            workflow.initialize(root, 4, 120)
            for task_id in ("../escape", "a/b", "a\\b", "CON", "x:y", "a" * 65):
                with self.subTest(task_id=task_id), self.assertRaises(ValueError):
                    workflow.new_task(root, task_id, "title")
            with self.assertRaises(ValueError):
                workflow.new_task(root, "valid", "line\nbreak")
            config = root / workflow.PROFILE
            data = json.loads(config.read_text(encoding="utf-8"))
            data["defaults"]["task_repairs"] = True
            config.write_bytes(workflow.encoded(data))
            with self.assertRaises(ValueError):
                workflow.check(root)

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

    def test_package_metadata_and_local_document_links(self):
        manifest = json.loads((REPO / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "ai-delivery-workflow")
        self.assertEqual(manifest["version"], workflow.VERSION)
        self.assertTrue((REPO / manifest["skills"]).is_dir())
        skill = (workflow.SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: ai-delivery\n"))
        self.assertIn("description:", skill.split("---", 2)[1])
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
