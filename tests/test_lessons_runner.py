"""lessons 运行时：配置、runner、网络预检、退避。"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  注入 sys.path

from lessons import backoff, config, netcheck, paths, runner


def tmp_home() -> Path:
    return Path(tempfile.mkdtemp(prefix="ai314-home-"))


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.home = tmp_home()
        self.env = {"AI314_HOME": str(self.home), "HOME": str(self.home)}

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def write(self, text):
        (self.home / "config.toml").write_text(text, encoding="utf-8")

    def test_defaults_when_missing(self):
        c = config.load(self.env)
        self.assertEqual(c.lessons["mode"], "on")
        self.assertIs(c.lessons["contribute"], False)
        self.assertEqual(c.lessons["upstream"], "lupguo/AI314")
        self.assertEqual(c.lessons["src"], str(self.home / ".ai314-src"))
        self.assertEqual((c.lessons["distill_min"], c.lessons["contrib_min"]), (15, 3))
        self.assertEqual(c.agent_for("distill")["runner"], "auto")
        self.assertEqual(c.agent_for("distill")["timeout"], 300)
        self.assertEqual(c.agent_for("contribute")["timeout"], 900)

    def test_stage_override(self):
        self.write('[agent]\nrunner = "agy"\nmodel = "m1"\n[agent.contribute]\ntimeout = 50\n')
        c = config.load(self.env)
        self.assertEqual(c.agent_for("contribute")["timeout"], 50)
        self.assertEqual(c.agent_for("contribute")["runner"], "agy")
        self.assertEqual(c.agent_for("distill")["model"], "m1")

    def test_env_overrides(self):
        self.write('[lessons]\ncontribute = false\nmode = "on"\n')
        c = config.load(dict(self.env, AI314_CONTRIBUTE="on", AI314_LESSONS="capture-only"))
        self.assertIs(c.lessons["contribute"], True)
        self.assertEqual(c.lessons["mode"], "capture-only")

    def test_unknown_key_warns(self):
        self.write('[network]\nhttps_proxy = "http://p:1"\ntoken = "x"\n')
        c = config.load(self.env)
        self.assertNotIn("token", c.network)
        self.assertEqual(c.network["https_proxy"], "http://p:1")
        self.assertTrue(any("token" in w for w in c.warnings))

    def test_project_id_stable(self):
        a = paths.project_id(Path("/x/y"))
        self.assertEqual(a, paths.project_id(Path("/x/y")))
        self.assertRegex(a, r"^p-[0-9a-f]{8}$")


def stub_bin(dirpath: Path, name: str, body: str) -> Path:
    p = dirpath / name
    p.write_text("#!/usr/bin/env bash\n" + body + "\n", encoding="utf-8")
    p.chmod(0o755)
    return p


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.home = tmp_home()
        self.env = {"AI314_HOME": str(self.home), "HOME": str(self.home), "PATH": "/usr/bin:/bin"}

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def test_build_argv_each_runner(self):
        a = {"model": "M", "extra_args": ["--x"], "timeout": 60}
        self.assertEqual(runner.build("claude", "/b/claude", a, "P"),
                         (["/b/claude", "-p", "--output-format", "json", "--model", "M", "--x"], "P"))
        self.assertEqual(runner.build("tclaude", "/b/tclaude", dict(a, model=""), "P"),
                         (["/b/tclaude", "-p", "--output-format", "json", "--x"], "P"))
        self.assertEqual(runner.build("agy", "/b/agy", a, "P"),
                         (["/b/agy", "--output-format", "json", "--print-timeout", "60s",
                           "--disable-slash-commands", "--model", "M", "--x", "-p", "P"], None))
        self.assertEqual(runner.build("codex", "/b/codex", a, "P"),
                         (["/b/codex", "exec", "-c", 'model="M"', "--sandbox", "read-only", "--x", "-"], "P"))

    def test_child_env_proxy_cases(self):
        e = netcheck.child_env({"https_proxy": "http://127.0.0.1:8118", "no_proxy": ""}, {"PATH": "/bin"})
        self.assertEqual(e["HTTPS_PROXY"], "http://127.0.0.1:8118")
        self.assertEqual(e["https_proxy"], "http://127.0.0.1:8118")
        self.assertNotIn("NO_PROXY", e)
        self.assertEqual(e["AI314_HEADLESS"], "1")
        self.assertEqual(e["PATH"], "/bin")

    def test_auto_resolve_order(self):
        d = self.home / "bin"
        d.mkdir()
        stub_bin(d, "tclaude", "true")
        stub_bin(d, "agy", "true")
        name, path = runner.resolve({"runner": "auto", "bin": ""}, dict(self.env, PATH=str(d)))
        self.assertEqual((name, path), ("tclaude", str(d / "tclaude")))

    def test_resolve_missing(self):
        with self.assertRaises(runner.RunError) as cm:
            runner.resolve({"runner": "codex", "bin": "/nope/codex"}, self.env)
        self.assertEqual(cm.exception.kind, "no_runner")

    def test_unwrap_claude(self):
        out = json.dumps({"type": "result", "is_error": False, "result": "x {\"a\": 1}"})
        self.assertEqual(runner.unwrap("claude", out), 'x {"a": 1}')
        bad = json.dumps({"type": "result", "is_error": True, "result": "Invalid API key · Please run /login"})
        with self.assertRaises(runner.RunError) as cm:
            runner.unwrap("claude", bad)
        self.assertEqual(cm.exception.kind, "auth")

    def test_unwrap_agy(self):
        ok = '{"conversation_id":"b0","status":"SUCCESS","response":"{\\"ok\\":1}\\n","num_turns":1}'
        self.assertEqual(runner.extract_json(runner.unwrap("agy", ok)), {"ok": 1})
        err = json.dumps({"status": "ERROR", "response": "", "error":
                          'Eligibility check failed: Post "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist": EOF'})
        with self.assertRaises(runner.RunError) as cm:
            runner.unwrap("agy", "error: something\n" + err)
        self.assertEqual(cm.exception.kind, "network")

    def test_extract_json_fenced(self):
        text = '好的，结果如下：\n```json\n{"a": {"b": "}"}, "c": [1]}\n```\n以上。'
        self.assertEqual(runner.extract_json(text), {"a": {"b": "}"}, "c": [1]})
        with self.assertRaises(runner.RunError) as cm:
            runner.extract_json("no json here")
        self.assertEqual(cm.exception.kind, "bad_output")

    def test_probe_unreachable(self):
        self.assertFalse(netcheck.probe("http://127.0.0.1:9", {}, timeout=2))

    def test_ask_network_no_call(self):
        d = self.home / "bin"
        d.mkdir()
        mark = self.home / "called"
        stub_bin(d, "claude", f'touch "{mark}"; echo "{{}}"')
        (self.home / "config.toml").write_text(
            f'[agent]\nrunner = "claude"\nbin = "{d / "claude"}"\n[network]\nprobe_url = "http://127.0.0.1:9"\n')
        cfg = config.load(self.env)
        with self.assertRaises(runner.RunError) as cm:
            runner.ask("hi", cfg, "distill", self.env, self.home)
        self.assertEqual(cm.exception.kind, "network")
        self.assertFalse(mark.exists())

    def test_classify(self):
        self.assertEqual(runner.classify("dial tcp: connection refused"), "network")
        self.assertEqual(runner.classify("401 Unauthorized"), "auth")
        self.assertEqual(runner.classify("weird"), "bad_output")


class BackoffTest(unittest.TestCase):
    def setUp(self):
        self.home = tmp_home()
        self.env = {"AI314_HOME": str(self.home)}

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def test_backoff_schedule(self):
        self.assertIsNone(backoff.blocked("distill", self.env, now=0))
        backoff.fail("distill", "network", self.env, now=0)
        self.assertEqual(backoff.blocked("distill", self.env, now=3599), "network")
        self.assertIsNone(backoff.blocked("distill", self.env, now=3600))
        backoff.fail("distill", "network", self.env, now=3600)
        self.assertEqual(backoff.blocked("distill", self.env, now=3600 + 7199), "network")
        for _ in range(10):
            backoff.fail("distill", "network", self.env, now=0)
        self.assertIsNone(backoff.blocked("distill", self.env, now=86400))
        backoff.ok("distill", self.env)
        backoff.fail("distill", "bad_output", self.env, now=0)
        self.assertIsNone(backoff.blocked("distill", self.env, now=1))
        backoff.fail("distill", "bad_output", self.env, now=1)
        self.assertEqual(backoff.blocked("distill", self.env, now=2), "bad_output")


class CommandsTest(unittest.TestCase):
    def setUp(self):
        self.home = tmp_home()
        self.env = {"AI314_HOME": str(self.home), "HOME": str(self.home), "PATH": os.environ["PATH"]}

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def run_cli(self, *argv):
        import contextlib
        import io

        from lessons import cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli.main(list(argv), env=self.env)
        return rc, buf.getvalue()

    def test_doctor_stub_ok(self):
        out_json = self.home / "out.json"
        out_json.write_text(json.dumps({"type": "result", "is_error": False, "result": '{"ok":1}'}))
        stub = stub_bin(self.home, "stub", f'cat >/dev/null; cat "{out_json}"')
        (self.home / "config.toml").write_text(
            f'[agent]\nrunner = "claude"\nbin = "{stub}"\n[network]\nprobe_url = "file://{stub}"\n')
        rc, out = self.run_cli("doctor")
        self.assertEqual(rc, 0, out)
        self.assertIn("network: ok", out)
        self.assertIn("runner: ok", out)

    def test_doctor_network_fail(self):
        (self.home / "config.toml").write_text('[network]\nprobe_url = "http://127.0.0.1:9"\n[agent]\nbin = "/bin/echo"\n')
        rc, out = self.run_cli("doctor")
        self.assertEqual(rc, 1)
        self.assertIn("network: fail", out)

    def test_status_masks_proxy(self):
        (self.home / "config.toml").write_text('[network]\nhttps_proxy = "http://user:pw@127.0.0.1:8118"\n')
        rc, out = self.run_cli("status")
        self.assertEqual(rc, 0)
        self.assertIn("127.0.0.1:8118", out)
        self.assertNotIn("pw", out)


if __name__ == "__main__":
    unittest.main()
