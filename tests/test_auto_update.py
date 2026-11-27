"""远程自动更新器 platforms/_common/auto-update 的行为测试（本地 bare 仓库 + agy 桩）。"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

UPDATER = ROOT / "platforms/_common/auto-update"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]


def git(*args, cwd):
    return subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class AutoUpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ai314-upd-"))
        self.remote = self.tmp / "remote.git"
        self.pub = self.tmp / "pub"
        self.home = self.tmp / "home"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "dist", str(self.remote)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.remote), str(self.pub)], check=True, capture_output=True)
        git("switch", "-q", "-c", "dist", cwd=self.pub)
        self.publish("v1")
        subprocess.run(["git", "clone", "-q", "-b", "dist", str(self.remote), str(self.home)], check=True, capture_output=True)
        # agy 桩：记录调用；AGY_FAIL_INSTALL=1 时 install 失败
        self.calls = self.tmp / "agy.calls"
        self.stub = self.tmp / "agy"
        self.stub.write_text(
            '#!/usr/bin/env bash\necho "$*" >> "%s"\n'
            '[ "$2" = install ] && [ -n "${AGY_FAIL_INSTALL:-}" ] && exit 1\nexit 0\n' % self.calls
        )
        self.stub.chmod(0o755)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def publish(self, tag):
        (self.pub / "antigravity").mkdir(exist_ok=True)
        (self.pub / "antigravity/VERSION").write_text(tag)
        git("add", "-A", cwd=self.pub)
        git("commit", "-qm", tag, cwd=self.pub)
        git("push", "-q", "origin", "dist", cwd=self.pub)

    def run_updater(self, platform="antigravity", interval="0", **env):
        e = dict(os.environ, AI314_HOME=str(self.home), AI314_UPDATE_INTERVAL=interval, AI314_AGY_BIN=str(self.stub), **env)
        r = subprocess.run([str(UPDATER), platform], env=e, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def agy_calls(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def head(self):
        return git("rev-parse", "HEAD", cwd=self.home)

    def test_missing_home_is_noop(self):
        shutil.rmtree(self.home)
        self.run_updater()
        self.assertEqual(self.agy_calls(), [])

    def test_pulls_and_reinstalls_when_behind(self):
        self.publish("v2")
        self.run_updater()
        self.assertEqual((self.home / "antigravity/VERSION").read_text(), "v2")
        self.assertEqual(self.agy_calls()[-1], f"plugin install {self.home}/antigravity")
        self.assertEqual((self.home / ".installed-rev").read_text().strip(), self.head())

    def test_up_to_date_and_installed_does_nothing(self):
        self.run_updater()
        n = len(self.agy_calls())
        self.run_updater()
        self.assertEqual(len(self.agy_calls()), n)

    def test_failed_install_is_retried_next_session(self):
        self.publish("v2")
        self.run_updater(AGY_FAIL_INSTALL="1")
        self.assertFalse((self.home / ".installed-rev").exists())
        # 远端无新提交、仍在节流期内，但上次安装失败 → 必须重试
        self.run_updater(interval="999999")
        self.assertEqual(self.agy_calls()[-1], f"plugin install {self.home}/antigravity")
        self.assertEqual((self.home / ".installed-rev").read_text().strip(), self.head())

    def test_throttle_skips_fetch(self):
        self.run_updater()
        self.publish("v2")
        self.run_updater(interval="999999")
        self.assertEqual((self.home / "antigravity/VERSION").read_text(), "v1")

    def test_skips_non_dist_branch(self):
        git("switch", "-q", "-c", "contrib/x", cwd=self.home)
        self.publish("v2")
        self.run_updater()
        self.assertEqual((self.home / "antigravity/VERSION").read_text(), "v1")
        self.assertEqual(self.agy_calls(), [])

    def test_skips_dirty_tree(self):
        (self.home / "antigravity/VERSION").write_text("local edit")
        self.publish("v2")
        self.run_updater()
        self.assertEqual((self.home / "antigravity/VERSION").read_text(), "local edit")
        self.assertEqual(self.agy_calls(), [])

    def test_claude_platform_pulls_without_agy(self):
        self.publish("v2")
        self.run_updater(platform="claude")
        self.assertEqual((self.home / "antigravity/VERSION").read_text(), "v2")
        self.assertEqual(self.agy_calls(), [])


if __name__ == "__main__":
    unittest.main()
