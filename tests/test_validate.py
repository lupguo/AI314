import shutil
import unittest

from helpers import make_tree, skill_md

from ai314build import model, validate


def errors(root):
    return [i for i in validate.validate(model.load(root)) if i.level == "error"]


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.root = make_tree()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_clean_tree_has_no_errors(self):
        self.assertEqual(errors(self.root), [])

    def test_validate_flags_bad_prefix(self):
        d = self.root / "content/L1/go-web"
        d.mkdir()
        (d / "SKILL.md").write_text(skill_md("go-web"))
        msgs = [i.msg for i in errors(self.root)]
        self.assertTrue(any("stack-" in m for m in msgs), msgs)

    def test_validate_flags_name_mismatch(self):
        d = self.root / "content/L1/stack-a"
        d.mkdir()
        (d / "SKILL.md").write_text(skill_md("stack-b"))
        self.assertTrue(any("目录名" in i.msg for i in errors(self.root)))

    def test_validate_flags_missing_sections(self):
        d = self.root / "content/L1/stack-thin"
        d.mkdir()
        (d / "SKILL.md").write_text(skill_md("stack-thin", body="nothing\n"))
        self.assertTrue(any("## 1." in i.msg for i in errors(self.root)))

    def test_validate_flags_secret(self):
        p = self.root / "content/L1/stack-go-microservice/SKILL.md"
        p.write_text(p.read_text() + "\ntoken ghp_" + "a" * 30 + "\n")
        self.assertTrue(any("密钥" in i.msg for i in errors(self.root)))

    def test_validate_flags_bad_version(self):
        t = self.root / "ai314.toml"
        t.write_text(t.read_text().replace('"1.2.3"', '"v1.2"'))
        self.assertTrue(any("semver" in i.msg for i in errors(self.root)))

    def test_validate_flags_short_description(self):
        d = self.root / "content/L1/stack-x"
        d.mkdir()
        (d / "SKILL.md").write_text(skill_md("stack-x", desc="短"))
        self.assertTrue(any("description" in i.msg for i in errors(self.root)))


if __name__ == "__main__":
    unittest.main()
