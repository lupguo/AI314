import shutil
import unittest

from helpers import make_tree, skill_md

from ai314build import build, model


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.root = make_tree()
        self.out = self.root / "dist"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_load_reads_version(self):
        p = model.load(self.root)
        self.assertEqual(p.name, "ai314")
        self.assertEqual(p.version, "1.2.3")
        self.assertEqual(sorted(s.name for s in p.skills), ["planning", "stack-go-microservice"])
        go = next(s for s in p.skills if s.name == "stack-go-microservice")
        self.assertEqual(go.layer_id, "L1-stacks")
        self.assertIn("Go 微服务", go.description)

    def test_render_rule_has_version_and_index(self):
        text = build.render_rule(model.load(self.root))
        self.assertIn("> AI314 宪法版本：v1.2.3", text)
        self.assertIn("`ai314:stack-go-microservice`", text)
        self.assertIn("`ai314:planning`", text)
        self.assertNotIn("AI314:SKILL-INDEX", text)
        # 版本行紧跟一级标题
        self.assertTrue(text.startswith("# 宪法\n\n> AI314 宪法版本：v1.2.3\n"))

    def test_rebuild_removes_stale_skill(self):
        build.build_all(model.load(self.root), self.out, ["claude", "antigravity"])
        shutil.rmtree(self.root / "content/L0/skills/planning")
        build.build_all(model.load(self.root), self.out, ["claude", "antigravity"])
        for plat in ("claude", "antigravity"):
            self.assertFalse((self.out / plat / "skills/planning").exists(), plat)
            self.assertTrue((self.out / plat / "skills/stack-go-microservice/SKILL.md").exists(), plat)

    def test_skill_assets_copied(self):
        build.build_all(model.load(self.root), self.out, ["claude", "antigravity"])
        for plat in ("claude", "antigravity"):
            tpl = self.out / plat / "skills/stack-go-microservice/Makefile.tpl"
            self.assertEqual(tpl.read_text(), "test:\n\tgo test ./...\n")

    def test_unknown_platform_fails(self):
        with self.assertRaises(SystemExit):
            build.build_all(model.load(self.root), self.out, ["nope"])

    def test_new_layer_needs_no_code_change(self):
        (self.root / "ai314.toml").write_text(
            (self.root / "ai314.toml").read_text()
            + '\n[[layers]]\nid = "L3-deploy"\nskills_dir = "content/L3"\nprefix = "deploy-"\n'
        )
        d = self.root / "content/L3/deploy-appstore"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(skill_md("deploy-appstore", "当发布 App Store 时使用此技能。", "x\n"))
        build.build_all(model.load(self.root), self.out, ["claude"])
        self.assertTrue((self.out / "claude/skills/deploy-appstore/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
