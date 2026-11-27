"""构建编排：渲染宪法并调用各平台适配器。"""
from __future__ import annotations

import importlib
import re
import shutil
from pathlib import Path

from .model import Project

INDEX_MARK = "<!-- AI314:SKILL-INDEX -->"
PLATFORMS = ("claude", "antigravity")


def render_index(project: Project) -> str:
    rows = ["| 技能 | 层 | 触发时机与适用范围 |", "| :-- | :-- | :-- |"]
    for s in project.skills:
        desc = s.description.replace("|", "\\|")
        rows.append(f"| `{project.name}:{s.name}` | {s.layer_id} | {desc} |")
    return "\n".join(rows)


def render_rule(project: Project) -> str:
    """在一级标题后插入版本行，并把索引占位符替换为技能表。"""
    text = project.rule_path.read_text(encoding="utf-8")
    version_line = f"> AI314 宪法版本：v{project.version}"
    m = re.match(r"(# [^\n]*\n)", text)
    if m:
        text = f"{m.group(1)}\n{version_line}\n{text[m.end():]}"
    else:
        text = f"{version_line}\n\n{text}"
    if INDEX_MARK in text:
        text = text.replace(INDEX_MARK, render_index(project))
    return text


def copy_skills(project: Project, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for s in project.skills:
        shutil.copytree(s.src_dir, dest / s.name, ignore=shutil.ignore_patterns(".DS_Store"))


def build_all(project: Project, out: Path, platforms: list[str]) -> None:
    unknown = [p for p in platforms if p not in PLATFORMS]
    if unknown:
        raise SystemExit(f"未知平台: {unknown}，可选 {list(PLATFORMS)}")
    rule_text = render_rule(project)
    out = Path(out)
    for plat in platforms:
        target = out / plat
        if target.exists():
            shutil.rmtree(target)  # 每次全量重建，避免残留已删除技能
        target.mkdir(parents=True)
        adapter = importlib.import_module(f"platforms.{plat}.adapter")
        adapter.write(project, rule_text, target)
