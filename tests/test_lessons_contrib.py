"""lessons 回流：git worktree + make check + gh PR（本地 bare 仓库与桩 gh/runner）、new-stack 采样。"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  注入 sys.path

from lessons import config, contribute, sampler, store

GH_STUB = r'''#!/usr/bin/env bash
echo "$*" >> "$GH_LOG"
case "$1 $2" in
  "auth status") exit 0;;
  "api repos/lupguo/AI314") echo "${GH_PUSH:-true}";;
  "api user") echo tester;;
  "repo fork") exit 0;;
  "pr create") echo "https://github.com/lupguo/AI314/pull/7";;
esac
'''


def sh(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class ContribTest(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="ai314-contrib-")).resolve()
        self.home, self.bin = self.t / "home", self.t / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.bare = self._seed_origin()
        self.src = self.t / "src"
        sh("git", "clone", "-q", str(self.bare), str(self.src))
        sh("git", "-C", str(self.src), "config", "user.email", "t@t")
        sh("git", "-C", str(self.src), "config", "user.name", "t")
        (self.bin / "gh").write_text(GH_STUB)
        (self.bin / "gh").chmod(0o755)
        self.env = {"AI314_HOME": str(self.home), "HOME": str(self.home), "GH_LOG": str(self.t / "gh.log"),
                    "PATH": f"{self.bin}:{os.environ['PATH']}"}

    def tearDown(self):
        shutil.rmtree(self.t, ignore_errors=True)

    def _seed_origin(self) -> Path:
        seed = self.t / "seed"
        for rel in ("content/L1-stacks/stack-go-microservice/SKILL.md", "content/L0-constitution/AGENTS.base.md",
                    "content/L0-constitution/skills/planning/SKILL.md"):
            (seed / rel).parent.mkdir(parents=True, exist_ok=True)
            (seed / rel).write_text("# old\n")
        (seed / "Makefile").write_text('check:\n\t@test "$$CHECK_FAIL" != 1\n')
        sh("git", "init", "-q", "-b", "main", str(seed))
        sh("git", "-C", str(seed), "add", "-A")
        sh("git", "-C", str(seed), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
        bare = self.t / "origin.git"
        sh("git", "clone", "-q", "--bare", str(seed), str(bare))
        return bare

    def stub_runner(self, result: dict, contribute_on=True):
        stub = self.bin / "stub-claude"
        wrapper = json.dumps({"type": "result", "is_error": False, "result": json.dumps(result, ensure_ascii=False)})
        (self.t / "out.json").write_text(wrapper)
        stub.write_text(f'#!/usr/bin/env bash\ncat > "{self.t}/prompt.txt"\ncat "{self.t}/out.json"\n')
        stub.chmod(0o755)
        (self.home / "config.toml").write_text(
            f'[lessons]\ncontribute = {"true" if contribute_on else "false"}\nsrc = "{self.src}"\n'
            f'[agent]\nrunner = "claude"\nbin = "{stub}"\n[network]\nprobe_url = "file://{stub}"\n')

    def seed_pending(self, owner="stack-go-microservice", n=3, projects=("p-aaaaaaaa",)):
        recs = [{"rule": f"规则{i}", "title": f"t{i}", "project": projects[i % len(projects)], "count": 1,
                 "date": "2026-11-27"} for i in range(n)]
        store.global_append(owner, recs, self.env)

    def gh_log(self) -> str:
        p = self.t / "gh.log"
        return p.read_text() if p.exists() else ""

    def files_result(self, path="content/L1-stacks/stack-go-microservice/SKILL.md", title="吸收 3 条经验"):
        return {"files": [{"path": path, "content": "# new\n"}], "adopted": [0, 1, 2], "pending": [], "title": title}

    def test_contrib_disabled_by_default(self):
        self.stub_runner(self.files_result(), contribute_on=False)
        self.seed_pending()
        contribute.maybe_run(config.load(self.env), self.env)
        self.assertEqual(self.gh_log(), "")

    def test_contrib_pr_flow_push(self):
        self.stub_runner(self.files_result())
        self.seed_pending()
        contribute.maybe_run(config.load(self.env), self.env)
        log = self.gh_log()
        self.assertIn("pr create --repo lupguo/AI314 --base main", log)
        self.assertIn("p-aaaaaaaa", log)
        self.assertNotIn("--draft", log)
        heads = subprocess.run(["git", "-C", str(self.bare), "branch", "--list", "lessons/*"],
                               capture_output=True, text=True).stdout
        self.assertIn("lessons/stack-go-microservice-", heads)
        self.assertEqual(store.global_pending(self.env), {})
        cur = subprocess.run(["git", "-C", str(self.src), "branch", "--show-current"], capture_output=True, text=True)
        self.assertEqual(cur.stdout.strip(), "main")
        self.assertIn("规则0", (self.t / "prompt.txt").read_text())

    def test_contrib_fork_flow(self):
        fork = self.t / "fork.git"
        sh("git", "clone", "-q", "--bare", str(self.bare), str(fork))
        sh("git", "-C", str(self.src), "config", f"url.{fork}.insteadOf", "https://github.com/tester/AI314.git")
        self.stub_runner(self.files_result())
        self.seed_pending()
        env = dict(self.env, GH_PUSH="false")
        contribute.maybe_run(config.load(env), env)
        log = self.gh_log()
        self.assertIn("repo fork lupguo/AI314 --clone=false", log)
        self.assertIn("--head tester:lessons/stack-go-microservice-", log)
        heads = subprocess.run(["git", "-C", str(fork), "branch", "--list", "lessons/*"],
                               capture_output=True, text=True).stdout
        self.assertIn("lessons/", heads)

    def test_check_failed_no_pr(self):
        self.stub_runner(self.files_result())
        self.seed_pending()
        env = dict(self.env, CHECK_FAIL="1")
        contribute.maybe_run(config.load(env), env)
        self.assertNotIn("pr create", self.gh_log())
        self.assertEqual(len(store.global_pending(env)["stack-go-microservice"]), 3)
        self.assertIn("check_failed", (self.home / "data/logs/lessons.log").read_text())
        wt = subprocess.run(["git", "-C", str(self.src), "worktree", "list"], capture_output=True, text=True).stdout
        self.assertEqual(len(wt.strip().splitlines()), 1)

    def test_rejects_path_escape(self):
        self.stub_runner(self.files_result(path="content/L1-stacks/stack-go-microservice/../../../ai314.toml"))
        self.seed_pending()
        contribute.maybe_run(config.load(self.env), self.env)
        self.assertNotIn("pr create", self.gh_log())
        self.assertIn("bad_output", (self.home / "data/logs/lessons.log").read_text())

    def test_title_prefix_not_duplicated(self):
        self.stub_runner(self.files_result(title="docs(stack-go-microservice): 沉淀分层红线"))
        self.seed_pending()
        contribute.maybe_run(config.load(self.env), self.env)
        self.assertIn("--title feat(stack-go-microservice): 沉淀分层红线 --body", self.gh_log())

    def test_draft_for_l0(self):
        self.stub_runner(self.files_result(path="content/L0-constitution/AGENTS.base.md"))
        self.seed_pending(owner="L0")
        contribute.maybe_run(config.load(self.env), self.env)
        self.assertIn("--draft", self.gh_log())
        self.assertIn("feat(constitution):", self.gh_log())

    def test_new_stack_ready_rule(self):
        cfg = config.load(self.env)
        one = {"new-stack:rust-cli": [{"project": "p-1"}] * 5}
        two = {"new-stack:rust-cli": [{"project": "p-1"}] * 4 + [{"project": "p-2"}]}
        self.assertEqual(contribute.ready(one, cfg, self.env), [])
        self.assertEqual(contribute.ready(two, cfg, self.env), ["new-stack:rust-cli"])
        self.assertEqual(contribute.ready({"mode-x": [{"project": "p"}] * 2}, cfg, self.env), [])
        self.assertEqual(contribute.target("new-stack:rust-cli"),
                         ("content/L1-stacks/stack-rust-cli/SKILL.md", "content/L1-stacks/stack-rust-cli"))
        self.assertEqual(contribute.target("ok-defaults")[0], "content/L0-constitution/skills/planning/SKILL.md")


class SamplerTest(unittest.TestCase):
    def test_sampler_limit(self):
        d = Path(tempfile.mkdtemp())
        (d / "go.mod").write_text("module x\n")
        (d / "Makefile").write_text("test:\n")
        (d / "internal/svc").mkdir(parents=True)
        for i in range(8):
            (d / f"internal/svc/f{i}.go").write_text("package svc\n" + "// x\n" * (i * 3000))
        (d / ".git").mkdir()
        (d / ".git/config").write_text("secret")
        out = sampler.sample(d, limit=20_000)
        self.assertLessEqual(len(out), 20_000)
        self.assertIn("go.mod", out)
        self.assertIn("internal/", out)
        self.assertNotIn("secret", out)
        shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
