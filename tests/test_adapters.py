import json
import os
import shutil
import subprocess
import unittest

from helpers import make_tree

from ai314build import build, model


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.root = make_tree()
        self.out = self.root / "dist"
        build.build_all(model.load(self.root), self.out, ["claude", "antigravity"])

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_claude_layout(self):
        c = self.out / "claude"
        m = json.loads((c / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(m["name"], "ai314")
        self.assertEqual(m["version"], "1.2.3")
        self.assertEqual(m["author"], {"name": "tester"})
        hooks = json.loads((c / "hooks/hooks.json").read_text())
        cmd = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/hooks/session-start", cmd)
        self.assertTrue(os.access(c / "hooks/session-start", os.X_OK))
        self.assertIn("> AI314 宪法版本：v1.2.3", (c / "rules/AGENTS.md").read_text())
        self.assertTrue((c / "skills/stack-go-microservice/SKILL.md").is_file())

    def test_marketplace_points_to_claude(self):
        mp = json.loads((self.out / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(mp["name"], "ai314")
        self.assertEqual(mp["plugins"][0]["name"], "ai314")
        self.assertEqual(mp["plugins"][0]["source"], "./claude")

    def test_agy_layout(self):
        a = self.out / "antigravity"
        m = json.loads((a / ".antigravity-plugin/plugin.json").read_text())
        self.assertEqual((m["name"], m["version"]), ("ai314", "1.2.3"))
        self.assertEqual(m["displayName"], "AI314")
        rule = (a / "rules/AGENTS.md").read_text()
        self.assertIn("> AI314 宪法版本：v1.2.3", rule)
        self.assertTrue((a / "skills/planning/SKILL.md").is_file())
        hooks = json.loads((a / "hooks.json").read_text())
        self.assertIn("./hooks/auto-update antigravity", hooks["ai314"]["SessionStart"][0]["command"])
        self.assertTrue(os.access(a / "hooks/auto-update", os.X_OK))

    def test_session_start_json_escaping(self):
        c = self.out / "claude"
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(c))
        r = subprocess.run([str(c / "hooks/session-start")], env=env, capture_output=True, text=True, check=True)
        data = json.loads(r.stdout)
        ctx = data["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(data["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("> AI314 宪法版本：v1.2.3", ctx)
        self.assertIn('"引号"', ctx)
        self.assertIn("\\反斜杠\\", ctx)

    def test_session_start_missing_rule_is_silent(self):
        c = self.out / "claude"
        (c / "rules/AGENTS.md").unlink()
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(c))
        r = subprocess.run([str(c / "hooks/session-start")], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout or "{}").get("hookSpecificOutput", {}).get("additionalContext", ""), "")


if __name__ == "__main__":
    unittest.main()
