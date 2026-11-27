"""Makefile release 目标的守卫与回滚测试（在临时 git 仓库中复制最小源码树）。"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

GITC = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]


class MakeReleaseTest(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix="ai314-mk-"))
        for name in ("Makefile", "ai314.toml", "content", "platforms", "build", "scripts", "tests"):
            src = ROOT / name
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, self.repo / name,
                                                               **({"ignore": shutil.ignore_patterns("__pycache__")} if src.is_dir() else {}))
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        (self.repo / ".gitignore").write_text("dist/\n__pycache__/\n")
        subprocess.run([*GITC, "add", "-A"], cwd=self.repo, check=True)
        subprocess.run([*GITC, "commit", "-qm", "init"], cwd=self.repo, check=True)
        self.toml = (self.repo / "ai314.toml").read_text()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def make_release(self, new):
        return subprocess.run(["make", "release", f"NEW={new}", "NOTE=n", "CLAUDE_BIN=__none__", "AGY_BIN=__none__"],
                              cwd=self.repo, capture_output=True, text=True,
                              env={"PATH": os.path.dirname(sys.executable) + ":/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(self.repo),
                                   "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})

    def test_rollback_when_changelog_untracked(self):
        # 制造 check 失败：放入一个名字与目录不一致的技能
        bad = self.repo / "content/L1-stacks/stack-bad"
        bad.mkdir()
        (bad / "SKILL.md").write_text("---\nname: stack-other\ndescription: 当开发某种服务时加载此技能。\n---\n## 1.\n## 2.\n## 3.\n## 4.\n")
        subprocess.run([*GITC, "add", "-A"], cwd=self.repo, check=True)
        subprocess.run([*GITC, "commit", "-qm", "bad"], cwd=self.repo, check=True)
        r = self.make_release("9.9.9")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((self.repo / "ai314.toml").read_text(), self.toml)
        self.assertFalse((self.repo / "CHANGELOG.md").exists())

    def test_refuses_existing_tag(self):
        subprocess.run(["git", "tag", "v9.9.9"], cwd=self.repo, check=True)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout
        r = self.make_release("9.9.9")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("v9.9.9", r.stdout + r.stderr)
        self.assertEqual((self.repo / "ai314.toml").read_text(), self.toml)
        self.assertEqual(subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout, head)

    def test_install_targets_depend_on_validate_and_test(self):
        r = subprocess.run(["make", "-n", "install-agy", "AGY_BIN=__none__"], cwd=self.repo, capture_output=True, text=True)
        self.assertIn("unittest", r.stdout)
        self.assertIn("ai314build validate", r.stdout)


class AgyHookCommandTest(unittest.TestCase):
    def test_hook_command_resolves_without_plugin_cwd(self):
        import json
        tmp = Path(tempfile.mkdtemp(prefix="ai314-hk-"))
        try:
            from helpers import make_tree
            from ai314build import build, model
            root = make_tree()
            build.build_all(model.load(root), root / "dist", ["antigravity"])
            cmd = json.loads((root / "dist/antigravity/hooks.json").read_text())["ai314"]["SessionStart"][0]["command"]
            self.assertIn("$HOME/.gemini/config/plugins/ai314/hooks/auto-update", cmd)
            # 在无关目录执行，必须成功并输出 {}
            r = subprocess.run(["bash", "-c", cmd], cwd=tmp, capture_output=True, text=True,
                               env={"PATH": "/usr/bin:/bin", "HOME": str(tmp)})
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "{}")
            shutil.rmtree(root, ignore_errors=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
