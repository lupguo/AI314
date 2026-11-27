"""把两端 Stop hook 的 stdin payload 归一化（Claude 为 snake_case，Antigravity 为 camelCase）。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HookInput:
    transcript: Path
    cwd: str
    session: str


def parse(platform: str, raw: str) -> HookInput | None:
    try:
        d = json.loads(raw or "{}")
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    if platform == "antigravity":
        ws = d.get("workspacePaths") or []
        tp, cwd, sid = d.get("transcriptPath"), (ws[0] if ws else d.get("cwd", "")), d.get("conversationId")
    else:
        tp, cwd, sid = d.get("transcript_path"), d.get("cwd", ""), d.get("session_id")
    if not tp:
        return None
    return HookInput(Path(tp), cwd or "", sid or Path(tp).stem)
