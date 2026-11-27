"""lessons 提炼：lessons.md 读写合并、全局库、distill 流程（桩 runner）。"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  注入 sys.path

from lessons import config, distill, inbox, store

TODAY = "2026-11-27"


def lesson(i, count=2, owner="stack-go-microservice", last=TODAY):
    return store.Lesson(f"L-{i:03d}", f"标题{i}", "场景", "表现", "做法", owner, f"规则{i}", count, last)


def make_env(home: Path, stub_result: dict | str, extra: str = "") -> dict:
    stub = home / "stub-claude"
    payload = stub_result if isinstance(stub_result, str) else json.dumps(stub_result, ensure_ascii=False)
    wrapper = json.dumps({"type": "result", "is_error": False, "result": payload}, ensure_ascii=False)
    (home / "out.json").write_text(wrapper, encoding="utf-8")
    stub.write_text(f'#!/usr/bin/env bash\ncat > "{home}/prompt.txt"\ncat "{home}/out.json"\n', encoding="utf-8")
    stub.chmod(0o755)
    (home / "config.toml").write_text(
        f'[agent]\nrunner = "claude"\nbin = "{stub}"\n[network]\nprobe_url = "file://{stub}"\n{extra}',
        encoding="utf-8")
    return {"AI314_HOME": str(home), "HOME": str(home), "PATH": os.environ["PATH"]}


def sig(kind="correction", **kw):
    return {"kind": kind, "user": "不对", "prev": "x", "files": [], "cmd": "", "tail": "", **kw}


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_store_roundtrip(self):
        p = self.d / "lessons.md"
        store.save(p, [lesson(1, 5), lesson(2, 1)], [store.OkDefault("是否创建草稿目录", "默认创建", 6)],
                   self.d / "archive.md", TODAY)
        text = p.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# 项目经验（AI314 自动维护，可手改）"))
        self.assertIn("### L-001 标题1（×5）", text)
        self.assertIn("- 是否创建草稿目录（OK ×6）→ 默认创建", text)
        p.write_text(text.replace("- 正确做法：做法", "- 正确做法：手改过的做法", 1), encoding="utf-8")
        ls, oks = store.load(p)
        self.assertEqual([x.id for x in ls], ["L-001", "L-002"])
        self.assertEqual(ls[0].fix, "手改过的做法")
        self.assertEqual((ls[0].owner, ls[0].rule, ls[0].count), ("stack-go-microservice", "规则1", 5))
        self.assertEqual(oks[0].count, 6)

    def test_archive_over_150_lines(self):
        old = [lesson(i, 1, last="2026-09-01") for i in range(1, 30)]
        fresh = [lesson(i, 9) for i in range(30, 33)]
        p, arc = self.d / "lessons.md", self.d / "archive.md"
        store.save(p, old + fresh, [], arc, TODAY)
        self.assertLessEqual(len(p.read_text(encoding="utf-8").splitlines()), 150)
        kept, _ = store.load(p)
        self.assertTrue({"L-030", "L-031", "L-032"} <= {x.id for x in kept})
        self.assertIn("### L-001", arc.read_text(encoding="utf-8"))


class DistillTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="ai314-home-"))
        self.root = Path(tempfile.mkdtemp(prefix="ai314-proj-")).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.proj = inbox.Project(self.root)
        self.proj.ensure()

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.root, ignore_errors=True)

    def seed(self, n=3):
        self.proj.append([sig() for _ in range(n)] + [sig("ok", prev="是否更新 README？")], {"session": "s"})

    def test_should_run_thresholds(self):
        cfg = config.load({"AI314_HOME": str(self.home)})
        now = 1_800_000_000
        fresh = {"ts": "2027-01-15T08:00:00"}
        self.assertFalse(distill.should_run([dict(sig(), **fresh)] * 14 + [dict(sig("ok"), **fresh)] * 9, cfg, now))
        self.assertTrue(distill.should_run([dict(sig(), **fresh)] * 15, cfg, now))
        old = {"ts": "2026-12-01T00:00:00"}
        self.assertTrue(distill.should_run([dict(sig(), **old)] * 3, cfg, now))
        self.assertFalse(distill.should_run([dict(sig(), **old)] * 2, cfg, now))

    def test_distill_merge_and_new(self):
        md = self.root / "docs/ai314/lessons.md"
        md.parent.mkdir(parents=True)
        store.save(md, [lesson(1, 2)], [], md.with_name("lessons-archive.md"), TODAY)
        self.seed()
        env = make_env(self.home, {"lessons": [
            {"op": "merge", "id": "L-001", "add_count": 2, "evidence": "e"},
            {"op": "new", "title": "新坑", "scene": "s", "symptom": "y", "fix": "f", "owner": "project",
             "generic_rule": "", "count": 3}], "ok_patterns": [], "dropped": 1})
        self.assertTrue(distill.run(self.proj, config.load(env), env, today=TODAY))
        ls, _ = store.load(md)
        self.assertEqual([(x.id, x.count) for x in ls], [("L-001", 4), ("L-002", 3)])
        self.assertEqual(self.proj.items(), [])
        prompt = (self.home / "prompt.txt").read_text(encoding="utf-8")
        self.assertIn("L-001", prompt)
        self.assertIn("不对", prompt)

    def test_distill_global_and_ok(self):
        self.seed()
        env = make_env(self.home, {"lessons": [
            {"op": "new", "title": "未加载技能", "scene": "s", "symptom": "y", "fix": "f",
             "owner": "stack-go-microservice", "generic_rule": "改 handler 前先加载 stack 技能"}],
            "ok_patterns": [{"question_type": "是否同步更新 README", "count": 4, "suggest": "默认同步更新"}]})
        self.assertTrue(distill.run(self.proj, config.load(env), env, today=TODAY))
        pend = store.global_pending(env)
        self.assertEqual(pend["stack-go-microservice"][0]["rule"], "改 handler 前先加载 stack 技能")
        self.assertRegex(pend["stack-go-microservice"][0]["project"], r"^p-[0-9a-f]{8}$")
        self.assertEqual(pend["ok-defaults"][0]["question"], "是否同步更新 README")
        projects = json.loads((self.home / "data/projects.json").read_text())
        self.assertEqual(list(projects.values())[0]["path"], str(self.root))
        _, oks = store.load(self.root / "docs/ai314/lessons.md")
        self.assertEqual((oks[0].question, oks[0].count), ("是否同步更新 README", 4))

    def test_distill_bad_output_keeps_inbox(self):
        self.seed()
        env = make_env(self.home, "抱歉，我无法输出 JSON")
        self.assertFalse(distill.run(self.proj, config.load(env), env, today=TODAY))
        self.assertEqual(len(self.proj.items()), 4)
        self.assertFalse((self.root / "docs/ai314/lessons.md").exists())
        log = (self.home / "data/logs/lessons.log").read_text(encoding="utf-8")
        self.assertIn("bad_output", log)

    def test_distill_invalid_owner_rejected(self):
        self.seed()
        env = make_env(self.home, {"lessons": [
            {"op": "new", "title": "坏归属", "scene": "s", "symptom": "y", "fix": "f", "owner": "../etc",
             "generic_rule": "x"},
            {"op": "merge", "id": "L-999", "add_count": 1},
            {"op": "new", "title": "好", "scene": "s", "symptom": "y", "fix": "f", "owner": "L0",
             "generic_rule": "规则"}]})
        self.assertTrue(distill.run(self.proj, config.load(env), env, today=TODAY))
        ls, _ = store.load(self.root / "docs/ai314/lessons.md")
        self.assertEqual([x.title for x in ls], ["好"])
        self.assertEqual(list(store.global_pending(env)), ["L0"])

    def test_batch_cap_keeps_rest(self):
        self.proj.append([sig() for _ in range(distill.MAX_BATCH + 7)], {"session": "s"})
        env = make_env(self.home, {"lessons": [], "ok_patterns": []})
        self.assertTrue(distill.run(self.proj, config.load(env), env, today=TODAY))
        self.assertEqual(len(self.proj.items()), 7)

    def test_distill_does_not_contribute_inline(self):
        self.seed()
        env = make_env(self.home, {"lessons": [], "ok_patterns": []})
        import lessons.contribute as c
        called = []
        orig, c.maybe_run = c.maybe_run, lambda *a: called.append(1)
        try:
            distill.run(self.proj, config.load(env), env, today=TODAY)
        finally:
            c.maybe_run = orig
        self.assertEqual(called, [])

    def test_maybe_run_respects_backoff(self):
        self.proj.append([sig() for _ in range(15)], {"session": "s"})
        env = make_env(self.home, "not json")
        cfg = config.load(env)
        distill.maybe_run(self.proj, cfg, env)
        distill.maybe_run(self.proj, cfg, env)  # 第二次 bad_output 后进入 24h 退避
        (self.home / "prompt.txt").unlink()
        distill.maybe_run(self.proj, cfg, env)
        self.assertFalse((self.home / "prompt.txt").exists())
        self.assertEqual(len(self.proj.items()), 15)


if __name__ == "__main__":
    unittest.main()
