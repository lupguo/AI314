"""Claude Code 适配器：rule → hooks 注入；skill → skills/。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ai314build.build import copy_skills

HERE = Path(__file__).resolve().parent
COMMON = HERE.parent / "_common"


def _dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write(project, rule_text: str, out_dir: Path) -> None:
    _dump(out_dir / ".claude-plugin/plugin.json", {
        "name": project.name,
        "version": project.version,
        "description": project.description,
        "author": {"name": project.author},
        "repository": project.repository,
        "license": "MIT",
    })
    (out_dir / "rules").mkdir()
    (out_dir / "rules/AGENTS.md").write_text(rule_text, encoding="utf-8")
    hooks = out_dir / "hooks"
    hooks.mkdir()
    shutil.copy2(HERE / "hooks/session-start", hooks / "session-start")
    shutil.copy2(COMMON / "auto-update", hooks / "auto-update")
    _dump(hooks / "hooks.json", {"hooks": {"SessionStart": [{
        "matcher": "startup|clear|compact",
        "hooks": [{"type": "command", "command": '"${CLAUDE_PLUGIN_ROOT}/hooks/session-start"'}],
    }]}})
    copy_skills(project, out_dir / "skills")
    # marketplace 位于产物根，供 `plugin marketplace add <dist>` 使用
    _dump(out_dir.parent / ".claude-plugin/marketplace.json", {
        "name": project.name,
        "owner": {"name": project.author},
        "metadata": {"description": project.description},
        "plugins": [{"name": project.name, "source": f"./{out_dir.name}", "description": project.description}],
    })
