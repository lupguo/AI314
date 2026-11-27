import shutil
import sys
import unittest
from pathlib import Path

from helpers import ROOT, make_tree

sys.path.insert(0, str(ROOT / "scripts"))
import release  # noqa: E402


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.root = make_tree()
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## v1.2.3 - 2026-01-01\n\n- old\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def snapshot(self):
        return {p: p.read_bytes() for p in (self.root / "ai314.toml", self.root / "CHANGELOG.md")}

    def test_release_updates_toml_and_changelog(self):
        release.bump(self.root, "1.3.0", "宪法第 7 条补充说明", today="2026-11-27")
        self.assertIn('version = "1.3.0"', (self.root / "ai314.toml").read_text())
        log = (self.root / "CHANGELOG.md").read_text()
        self.assertTrue(log.startswith("# Changelog\n\n## v1.3.0 - 2026-11-27\n\n- 宪法第 7 条补充说明\n"))
        self.assertIn("## v1.2.3", log)

    def test_release_rejects_non_increasing(self):
        before = self.snapshot()
        for v in ("1.2.3", "1.2.2", "0.9.9"):
            with self.assertRaises(SystemExit):
                release.bump(self.root, v, "x")
        self.assertEqual(before, self.snapshot())

    def test_release_rejects_non_semver(self):
        before = self.snapshot()
        for v in ("v1.3.0", "1.3", "1.3.0-rc1", ""):
            with self.assertRaises(SystemExit):
                release.bump(self.root, v, "x")
        self.assertEqual(before, self.snapshot())

    def test_release_creates_changelog_if_missing(self):
        (self.root / "CHANGELOG.md").unlink()
        release.bump(self.root, "2.0.0", "breaking", today="2026-11-27")
        self.assertIn("## v2.0.0 - 2026-11-27", (self.root / "CHANGELOG.md").read_text())


if __name__ == "__main__":
    unittest.main()
