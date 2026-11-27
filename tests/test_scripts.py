import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, skill_md

BLOCK = ROOT / "content/tools/onboard/scripts/ai314-block.sh"
SYNC = ROOT / "scripts/sync-back.sh"
ROW1 = "| `services/**` | ai314:stack-go-microservice |"
ROW2 = "| `web/**` | ai314:stack-web-admin |"


def run_block(project: Path, rows: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(BLOCK), str(project)], input=rows + "\n", capture_output=True, text=True)


class BlockTest(unittest.TestCase):
    def setUp(self):
        self.p = Path(tempfile.mkdtemp(prefix="ai314-proj-"))

    def tearDown(self):
        shutil.rmtree(self.p, ignore_errors=True)

    def test_block_creates_agents_md(self):
        r = run_block(self.p, ROW1)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.p / "AGENTS.md").read_text()
        self.assertIn("<!-- AI314:BEGIN v=1 -->", text)
        self.assertIn(ROW1, text)
        self.assertIn("<!-- AI314:END -->", text)

    def test_block_idempotent(self):
        before = "# 我的项目\n\n项目自有规则 A\n"
        after = "\n## 附录\n保留内容 B\n"
        (self.p / "AGENTS.md").write_text(before)
        run_block(self.p, ROW1)
        with (self.p / "AGENTS.md").open("a") as f:
            f.write(after)
        run_block(self.p, ROW2)
        run_block(self.p, ROW2)
        text = (self.p / "AGENTS.md").read_text()
        self.assertEqual(text.count("AI314:BEGIN"), 1)
        self.assertIn(ROW2, text)
        self.assertNotIn(ROW1, text)
        self.assertTrue(text.startswith(before))
        self.assertTrue(text.endswith(after))

    def test_block_adds_claude_import(self):
        (self.p / "CLAUDE.md").write_text("# 已有 CLAUDE\n")
        run_block(self.p, ROW1)
        run_block(self.p, ROW1)
        claude = (self.p / "CLAUDE.md").read_text()
        self.assertEqual(claude.count("@AGENTS.md"), 1)
        self.assertTrue(claude.startswith("# 已有 CLAUDE\n"))

    def test_block_rejects_empty_rows(self):
        r = run_block(self.p, "")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.p / "AGENTS.md").exists())


class SyncBackTest(unittest.TestCase):
    def setUp(self):
        self.hub = Path(tempfile.mkdtemp(prefix="ai314-hub-"))
        self.proj = Path(tempfile.mkdtemp(prefix="ai314-proj-"))
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.hub)], check=True)
        (self.hub / "content/L1-stacks").mkdir(parents=True)
        (self.hub / "content/L2-modes").mkdir(parents=True)
        (self.hub / "README.md").write_text("hub\n")
        subprocess.run(["git", "-C", str(self.hub), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.hub), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], check=True)

    def tearDown(self):
        shutil.rmtree(self.hub, ignore_errors=True)
        shutil.rmtree(self.proj, ignore_errors=True)

    def sync(self, *paths):
        return subprocess.run(["bash", str(SYNC), *map(str, paths)], capture_output=True, text=True,
                              env={"AI314_SRC": str(self.hub), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})

    def test_sync_back_copies_stack_dir(self):
        d = self.proj / ".agents/skills/stack-go-microservice"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(skill_md("stack-go-microservice"))
        (d / "Makefile.tpl").write_text("t\n")
        r = self.sync(d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = self.hub / "content/L1-stacks/stack-go-microservice"
        self.assertTrue((dest / "Makefile.tpl").is_file())
        branch = subprocess.run(["git", "-C", str(self.hub), "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
        self.assertTrue(branch.startswith("contrib/"), branch)

    def test_sync_back_mode_skips_section_check(self):
        d = self.proj / ".agents/skills/mode-fast"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(skill_md("mode-fast", "当处于快速验证阶段时加载此补丁。", "x\n"))
        r = self.sync(d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.hub / "content/L2-modes/mode-fast/SKILL.md").is_file())

    def test_sync_back_rejects_secret(self):
        d = self.proj / ".agents/skills/stack-bad"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(skill_md("stack-bad") + "\nghp_" + "a" * 30 + "\n")
        r = self.sync(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.hub / "content/L1-stacks/stack-bad").exists())


if __name__ == "__main__":
    unittest.main()
