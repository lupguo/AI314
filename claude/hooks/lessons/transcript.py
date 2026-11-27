"""两端 transcript JSONL → 统一 Event 序列；按字节偏移增量读取，只消费完整行。"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

CLAUDE_EDIT = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
AGY_EDIT = {"edit_file", "write_file"}
SKIP_PREFIX = ("<", "Base directory for this skill", "[Request interrupted")
AGY_EXIT = re.compile(r"exited with code (\d+)")
AGY_REQ = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.S)


@dataclass
class Event:
    role: str            # user | assistant | call | result
    text: str = ""
    tool: str = ""
    cmd: str = ""
    path: str = ""
    error: bool = False


def _lines(path: Path, start: int) -> tuple[list[str], int]:
    with path.open("rb") as f:
        f.seek(start)
        buf = f.read()
    end = buf.rfind(b"\n") + 1
    return buf[:end].decode("utf-8", "replace").splitlines(), start + end


def _json(line: str):
    try:
        return json.loads(line)
    except ValueError:
        return None


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def _claude_user(d: dict, calls: dict, out: list) -> None:
    content = d["message"].get("content")
    if isinstance(content, list) and any(c.get("type") == "tool_result" for c in content if isinstance(c, dict)):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_result":
                cmd = calls.get(c.get("tool_use_id"), "")
                out.append(Event("result", _text_of(c.get("content")), cmd=cmd, error=bool(c.get("is_error"))))
        return
    text = _text_of(content).strip()
    if d.get("isMeta") or not text or text.startswith(SKIP_PREFIX):
        return
    out.append(Event("user", text))


def _claude_assistant(d: dict, calls: dict, out: list) -> None:
    for c in d["message"].get("content") or []:
        if not isinstance(c, dict):
            continue
        if c.get("type") == "text" and c.get("text", "").strip():
            out.append(Event("assistant", c["text"].strip()))
        elif c.get("type") == "tool_use":
            inp, name = c.get("input") or {}, c.get("name", "")
            cmd = inp.get("command", "") if name == "Bash" else ""
            path = inp.get("file_path", "") if name in CLAUDE_EDIT else ""
            calls[c.get("id")] = cmd
            out.append(Event("call", tool=name, cmd=cmd, path=path))


def _claude(records: list[dict]) -> list[Event]:
    out, calls = [], {}
    for d in records:
        if d.get("type") == "user" and isinstance(d.get("message"), dict):
            _claude_user(d, calls, out)
        elif d.get("type") == "assistant" and isinstance(d.get("message"), dict):
            _claude_assistant(d, calls, out)
    return out


def _agy_calls(raw) -> list[dict]:
    if isinstance(raw, str):
        try:
            raw = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return []
    return [c for c in raw or [] if isinstance(c, dict)]


def _agy(records: list[dict]) -> list[Event]:
    out, pending = [], []
    for d in records:
        t = d.get("type")
        if t == "USER_INPUT":
            raw = str(d.get("content") or "")
            m = AGY_REQ.search(raw)
            text = (m.group(1) if m else raw).strip()
            if text and not text.startswith("/"):
                out.append(Event("user", text))
        elif t == "PLANNER_RESPONSE":
            if str(d.get("content") or "").strip():
                out.append(Event("assistant", str(d["content"]).strip()))
            for c in _agy_calls(d.get("tool_calls")):
                args, name = c.get("args") or {}, c.get("name", "")
                cmd = args.get("CommandLine", "") if name == "run_command" else ""
                path = args.get("Path", "") if name in AGY_EDIT else ""
                pending.append(cmd)
                out.append(Event("call", tool=name, cmd=cmd, path=path))
        elif t == "GENERIC" and pending:
            text = str(d.get("content") or "")
            m = AGY_EXIT.search(text)
            err = d.get("status") == "ERROR" or bool(m and m.group(1) != "0")
            out.append(Event("result", text, cmd=pending.pop(0), error=err))
    return out


def read(platform: str, path: Path, start: int) -> tuple[list[Event], int]:
    if not path.is_file():
        return [], start
    if path.stat().st_size < start:
        start = 0  # 文件被截断/轮转：从头读
    lines, end = _lines(path, start)
    records = [r for r in (_json(x) for x in lines if x.strip()) if isinstance(r, dict)]
    events = _agy(records) if platform == "antigravity" else _claude(records)
    return events, end
