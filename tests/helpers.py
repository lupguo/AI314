"""测试夹具：在临时目录中构造一个最小 AI314 源码树。"""
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / "build", ROOT, ROOT / "platforms/_common"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

TOML = """
[plugin]
name = "ai314"
version = "1.2.3"
description = "demo"
author = "tester"
repository = "https://example.com/ai314"

[rule]
source = "content/L0/AGENTS.base.md"

[[layers]]
id = "L0"
skills_dir = "content/L0/skills"
prefix = ""

[[layers]]
id = "L1-stacks"
skills_dir = "content/L1"
prefix = "stack-"
"""

RULE = '# 宪法\n\n第一条 "引号" 与 \\反斜杠\\ 与\ttab。\n\n## 四、 索引\n\n<!-- AI314:SKILL-INDEX -->\n'


def skill_md(name: str, desc: str = "当开发 Go 微服务时加载此技能。", body: str = "## 1.\n## 2.\n## 3.\n## 4.\n") -> str:
    return f"---\nname: {name}\ndescription: {desc}\n---\n\n# T\n\n{body}"


def make_tree() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ai314-test-"))
    (root / "ai314.toml").write_text(textwrap.dedent(TOML), encoding="utf-8")
    (root / "content/L0/skills/planning").mkdir(parents=True)
    (root / "content/L0/AGENTS.base.md").write_text(RULE, encoding="utf-8")
    (root / "content/L0/skills/planning/SKILL.md").write_text(skill_md("planning", "当规划功能时使用此技能。", "x\n"), encoding="utf-8")
    go = root / "content/L1/stack-go-microservice"
    go.mkdir(parents=True)
    (go / "SKILL.md").write_text(skill_md("stack-go-microservice"), encoding="utf-8")
    (go / "Makefile.tpl").write_text("test:\n\tgo test ./...\n", encoding="utf-8")
    return root
