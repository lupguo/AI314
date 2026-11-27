"""Antigravity 适配器：rule → rules/AGENTS.md（插件常驻规则）；skill → skills/。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ai314build.build import copy_skills

COMMON = Path(__file__).resolve().parent.parent / "_common"


def write(project, rule_text: str, out_dir: Path) -> None:
    manifest = out_dir / ".antigravity-plugin/plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({
        "name": project.name,
        "displayName": "AI314",
        "version": project.version,
        "description": project.description,
        "author": {"name": project.author},
        "repository": project.repository,
        "license": "MIT",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "rules").mkdir()
    (out_dir / "rules/AGENTS.md").write_text(rule_text, encoding="utf-8")
    copy_skills(project, out_dir / "skills")
    # 远程自动更新：AGY 插件 hooks.json 位于插件根，按插件名分组；命令相对插件根执行
    (out_dir / "hooks").mkdir()
    shutil.copy2(COMMON / "auto-update", out_dir / "hooks/auto-update")
    (out_dir / "hooks.json").write_text(json.dumps({project.name: {"SessionStart": [{
        "type": "command",
        "command": "./hooks/auto-update antigravity >/dev/null 2>&1 </dev/null & echo '{}'",
        "timeout": 5,
    }]}}, indent=2) + "\n", encoding="utf-8")
