"""内容校验：结构、命名、敏感信息、版本号。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .model import Project

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SECRET = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|password\s*=\s*['\"][^'\"]+)",
    re.IGNORECASE,
)
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STACK_SECTIONS = ("## 1.", "## 2.", "## 3.", "## 4.")
MAX_LINES_WARN = 220
TEXT_SUFFIXES = {".md", ".tpl", ".html", ".sh", ".txt", ".toml", ".json", ".yaml", ".yml", ""}


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warn"
    path: str
    msg: str


def _rel(project: Project, p: Path) -> str:
    try:
        return str(p.relative_to(project.root))
    except ValueError:
        return str(p)


def validate(project: Project) -> list[Issue]:
    issues: list[Issue] = []

    def err(p: Path, msg: str) -> None:
        issues.append(Issue("error", _rel(project, p), msg))

    def warn(p: Path, msg: str) -> None:
        issues.append(Issue("warn", _rel(project, p), msg))

    if not SEMVER.match(project.version):
        err(project.root / "ai314.toml", f"version '{project.version}' 不是 semver (x.y.z)")
    if not project.rule_path.is_file():
        err(project.rule_path, "宪法源文件不存在")

    prefixes = {l.id: l.prefix for l in project.layers}
    seen: dict[str, Path] = {}
    for s in project.skills:
        md = s.src_dir / "SKILL.md"
        if not s.name:
            err(md, "frontmatter 缺少 name")
            continue
        if s.name != s.dir_name:
            err(md, f"name '{s.name}' 与目录名 '{s.dir_name}' 不一致")
        if not NAME_RE.match(s.name) or len(s.name) > 64:
            err(md, f"name '{s.name}' 必须是 ≤64 字符的小写 kebab-case")
        prefix = prefixes.get(s.layer_id, "")
        if prefix and not s.name.startswith(prefix):
            err(md, f"{s.layer_id} 层技能名必须以 '{prefix}' 开头")
        if len(s.description) < 10:
            err(md, "description 缺失或过短（<10 字），影响技能触发")
        if s.name in seen:
            err(md, f"技能名 '{s.name}' 与 {_rel(project, seen[s.name])} 重复")
        seen[s.name] = md
        text = md.read_text(encoding="utf-8")
        if prefix == "stack-":
            for sec in STACK_SECTIONS:
                if not re.search(rf"^{re.escape(sec)}", text, re.M):
                    err(md, f"缺少标准章节 '{sec}'（技术栈/目录拓扑/编码红线/自检命令）")
        n = text.count("\n") + 1
        if n > MAX_LINES_WARN:
            warn(md, f"共 {n} 行，建议控制在 {MAX_LINES_WARN} 行内")

    for f in [project.rule_path, *(p for s in project.skills for p in s.src_dir.rglob("*") if p.is_file())]:
        if f.is_file() and f.suffix in TEXT_SUFFIXES:
            if SECRET.search(f.read_text(encoding="utf-8", errors="ignore")):
                err(f, "检测到疑似硬编码密钥或凭证")
    return issues
