"""lessons 捕获链路：transcript 归一化、信号抽取、inbox、capture 命令。"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  注入 sys.path

from lessons import cli, hookio, inbox, signals, transcript

FIX = Path(__file__).resolve().parent / "fixtures/lessons"
ENTRY = helpers.ROOT / "platforms/_common/ai314-lessons"


class TranscriptTest(unittest.TestCase):
    def test_claude_events(self):
        ev, off = transcript.read("claude", FIX / "claude.jsonl", 0)
        self.assertEqual(off, (FIX / "claude.jsonl").stat().st_size)
        users = [e.text for e in ev if e.role == "user"]
        self.assertEqual(users, ["帮我在 app.py 加一个 add 函数，不要改别的文件", "不对，不要放宽规则，应该修代码", "ok"])
        calls = [(e.tool, e.cmd, e.path) for e in ev if e.role == "call"]
        self.assertEqual(calls[0], ("Edit", "", "/p/app.py"))
        self.assertEqual(calls[1], ("Bash", "python -m pytest -q", ""))
        results = [(e.cmd, e.error) for e in ev if e.role == "result"]
        self.assertEqual(results[1], ("python -m pytest -q", True))
        self.assertEqual(results[4], ("", False))

    def test_agy_events(self):
        ev, _ = transcript.read("antigravity", FIX / "agy.jsonl", 0)
        users = [e.text for e in ev if e.role == "user"]
        self.assertEqual(users, ["帮我在 app.py 加一个 add 函数", "错了，应该修代码而不是放宽规则", "好的"])
        calls = [(e.tool, e.cmd, e.path) for e in ev if e.role == "call"]
        self.assertEqual(calls[1], ("run_command", "go test ./...", ""))
        self.assertEqual(calls[4], ("write_file", "", "/p/app.py"))
        results = [(e.cmd, e.error) for e in ev if e.role == "result"]
        self.assertEqual(results[1:5], [("go test ./...", True), ("make lint", True), ("make lint", True),
                                        ("", False)])

    def test_partial_last_line(self):
        d = Path(tempfile.mkdtemp())
        p = d / "t.jsonl"
        full = (FIX / "claude.jsonl").read_text(encoding="utf-8")
        p.write_text(full + '{"type":"user","message":{"role":"user","con', encoding="utf-8")
        ev, off = transcript.read("claude", p, 0)
        self.assertEqual(off, len(full.encode("utf-8")))
        ev2, off2 = transcript.read("claude", p, off)
        self.assertEqual((ev2, off2), ([], off))
        shutil.rmtree(d)

    def test_bad_line_skipped(self):
        d = Path(tempfile.mkdtemp())
        p = d / "t.jsonl"
        p.write_text("not json\n" + (FIX / "claude.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
        ev, _ = transcript.read("claude", p, 0)
        self.assertEqual(len([e for e in ev if e.role == "user"]), 3)
        shutil.rmtree(d)


class SignalsTest(unittest.TestCase):
    def run_fix(self, plat, name):
        ev, _ = transcript.read(plat, FIX / name, 0)
        return signals.extract(ev, {})

    def test_signal_kinds(self):
        for plat, name in (("claude", "claude.jsonl"), ("antigravity", "agy.jsonl")):
            kinds = {s["kind"] for s in self.run_fix(plat, name)}
            self.assertEqual(kinds, {"correction", "ok", "test_flip", "tool_fail", "rework"}, plat)

    def test_first_message_not_correction(self):
        sigs = self.run_fix("claude", "claude.jsonl")
        corr = [s for s in sigs if s["kind"] == "correction"]
        self.assertEqual(len(corr), 1)
        self.assertEqual(corr[0]["user"], "不对，不要放宽规则，应该修代码")
        self.assertIn("要不要我把 lint 规则放宽", corr[0]["prev"])
        self.assertIn("Bash make lint", corr[0]["prev"])

    def test_ok_only_short(self):
        ev = [transcript.Event("user", "先做别的"), transcript.Event("assistant", "继续吗？"),
              transcript.Event("user", "ok 但是把 X 改成 Y")]
        self.assertEqual([s["kind"] for s in signals.extract(ev, {})], [])

    def test_ok_records_question(self):
        ok = [s for s in self.run_fix("claude", "claude.jsonl") if s["kind"] == "ok"]
        self.assertEqual(ok[0]["prev"], "另外是否同时更新 README？")

    def test_flip_and_fail_details(self):
        sigs = {s["kind"]: s for s in self.run_fix("antigravity", "agy.jsonl")}
        self.assertEqual(sigs["test_flip"]["cmd"], "go test ./...")
        self.assertIn("FAIL: TestAdd", sigs["test_flip"]["tail"])
        self.assertEqual(sigs["tool_fail"]["cmd"], "make lint")
        self.assertEqual(sigs["rework"]["files"], ["/p/app.py"])

    def test_state_carries_across_turns(self):
        # 真机 Stop hook 每轮增量读取：按用户消息切片，sess 经 JSON 往返模拟 state.json 持久化
        for plat, name in (("claude", "claude.jsonl"), ("antigravity", "agy.jsonl")):
            ev, _ = transcript.read(plat, FIX / name, 0)
            idx = [i for i, e in enumerate(ev) if e.role == "user"] + [len(ev)]
            sess, sigs = {}, []
            for a, b in zip([0] + idx[1:-1], idx[1:]):
                sigs += signals.extract(ev[a:b], sess)
                sess = json.loads(json.dumps(sess))
            by_kind = {s["kind"]: s for s in sigs}
            self.assertEqual(set(by_kind), {"correction", "ok", "test_flip", "tool_fail", "rework"}, plat)
            self.assertIn("lint 规则放宽", by_kind["correction"]["prev"], plat)
            self.assertIn("make lint", by_kind["correction"]["prev"], plat)
            self.assertIn("README", by_kind["ok"]["prev"], plat)
            self.assertEqual(len([s for s in sigs if s["kind"] == "rework"]), 1, plat)


class HookIoTest(unittest.TestCase):
    def test_parse_both(self):
        c = hookio.parse("claude", json.dumps({"transcript_path": "/t.jsonl", "cwd": "/w", "session_id": "s"}))
        self.assertEqual((str(c.transcript), c.cwd, c.session), ("/t.jsonl", "/w", "s"))
        a = hookio.parse("antigravity", json.dumps({"transcriptPath": "/a.jsonl", "workspacePaths": ["/w2"],
                                                    "conversationId": "c"}))
        self.assertEqual((str(a.transcript), a.cwd, a.session), ("/a.jsonl", "/w2", "c"))
        self.assertIsNone(hookio.parse("claude", "garbage"))


def git_project() -> Path:
    d = Path(tempfile.mkdtemp(prefix="ai314-proj-"))
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    return d


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="ai314-home-"))
        self.proj = git_project()
        self.env = {"AI314_HOME": str(self.home), "HOME": str(self.home), "PATH": os.environ["PATH"]}
        self.tr = self.home / "t.jsonl"
        shutil.copy(FIX / "claude.jsonl", self.tr)

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.proj, ignore_errors=True)

    def payload(self, cwd=None):
        return json.dumps({"transcript_path": str(self.tr), "cwd": str(cwd or self.proj), "session_id": "s1"})

    def capture(self, env=None, cwd=None):
        return cli.capture("claude", self.payload(cwd), env or self.env, foreground=True)

    def test_capture_writes_inbox(self):
        self.assertEqual(self.capture(), 0)
        items = inbox.Project(self.proj.resolve()).items()
        self.assertEqual(len(items), 5)
        self.assertEqual({i["session"] for i in items}, {"s1"})
        self.assertEqual(items[0]["platform"], "claude")
        self.assertIn("ts", items[0])
        self.assertEqual((self.proj / ".ai314/.gitignore").read_text(), "*\n")

    def test_capture_incremental(self):
        self.capture()
        self.capture()
        self.assertEqual(len(inbox.Project(self.proj.resolve()).items()), 5)

    def test_capture_skips_non_git(self):
        d = Path(tempfile.mkdtemp())
        self.assertEqual(self.capture(cwd=d), 0)
        self.assertFalse((d / ".ai314").exists())
        shutil.rmtree(d)

    def test_missing_transcript(self):
        self.tr.unlink()
        self.assertEqual(self.capture(), 0)
        self.assertEqual(inbox.Project(self.proj.resolve()).items(), [])

    def test_headless_noop(self):
        self.capture(env=dict(self.env, AI314_HEADLESS="1"))
        self.assertFalse((self.proj / ".ai314").exists())

    def test_disabled_and_off(self):
        self.capture(env=dict(self.env, AI314_LESSONS="off"))
        self.assertFalse((self.proj / ".ai314").exists())
        (self.proj / ".ai314").mkdir()
        (self.proj / ".ai314/disabled").touch()
        self.capture()
        self.assertEqual(inbox.Project(self.proj.resolve()).items(), [])

    def test_lock_prevents_double(self):
        p = inbox.Project(self.proj.resolve())
        p.ensure()
        with p.lock() as got:
            self.assertTrue(got)
            self.capture()
        self.assertEqual(p.items(), [])

    def test_entry_script_runs(self):
        r = subprocess.run([str(ENTRY), "status"], cwd=self.proj, env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("runner", r.stdout)


if __name__ == "__main__":
    unittest.main()
