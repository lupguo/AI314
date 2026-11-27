"""Antigravity 适配器：rule → rules/AGENTS.md（插件常驻规则）；skill → skills/。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ai314build.build import copy_lessons, copy_skills

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
    (out_dir / ".gitignore").write_text(".last-check\n.installed-rev\n.update.log\n", encoding="utf-8")
    # 远程自动更新：AGY 插件 hooks.json 位于插件根，按插件名分组；命令相对插件根执行
    (out_dir / "hooks").mkdir()
    shutil.copy2(COMMON / "auto-update", out_dir / "hooks/auto-update")
    copy_lessons(out_dir / "hooks")
    hook_dir = '$HOME/.gemini/config/plugins/' + project.name + '/hooks'
    (out_dir / "hooks.json").write_text(json.dumps({project.name: {
        "SessionStart": [{
            "type": "command",
            # 不依赖 hook 的 cwd：用安装目录的绝对路径；脚本不存在时静默跳过。stdout 只输出 {}
            "command": (f'f="{hook_dir}/auto-update"; '
                        '[ -x "$f" ] && ("$f" antigravity >/dev/null 2>&1 </dev/null &); echo \'{}\''),
            "timeout": 5,
        }],
        # 经验捕获：stdin 交给脚本读取后自行 fork 到后台
        "Stop": [{
            "type": "command",
            "command": (f'f="{hook_dir}/ai314-lessons"; '
                        '[ -x "$f" ] && "$f" capture --platform antigravity >/dev/null 2>&1; echo \'{}\''),
            "timeout": 5,
        }],
    }}, indent=2) + "\n", encoding="utf-8")
