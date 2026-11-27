"""从 Event 序列抽取信号：纠正 / 返工 / 测试先挂后过 / 同命令连续失败 / 直接 OK。纯规则，0 token。"""
from __future__ import annotations

import re

from .transcript import Event

CORRECTION = ("不对", "错了", "搞错", "不要", "不应该", "应该", "重新", "还是不行", "不行", "又错", "又出",
              "别再", "别用", "别改", "改回", "回滚", "不是这样", "wrong", "don't", "dont", "should",
              "instead", "revert")
OK_WORDS = {"ok", "okay", "好", "好的", "可以", "继续", "行", "同意", "yes", "y", "lgtm", "就这样", "没问题",
            "确认", "嗯", "对"}
TEST_RE = re.compile(r"\b(test|tests|pytest|unittest|jest|vitest|go test|cargo test|make check|xcodebuild test)\b")
PUNCT_RE = re.compile(r"[\s\.,!?~，。！？、…；;:：\"'`]+")
QUESTION_RE = re.compile(r"[^。！？!?\n]*[？?]")
REWORK_TURNS = 3


def _cut(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[:n] + "…"


def _is_ok(text: str) -> bool:
    norm = PUNCT_RE.sub("", text.lower())
    return 0 < len(norm) <= 6 and norm in OK_WORDS


def _is_correction(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in CORRECTION)


def _last_question(text: str) -> str:
    qs = [q.strip() for q in QUESTION_RE.findall(text) if q.strip()]
    return _cut(qs[-1], 300) if qs else ""


class _Turn:
    """一轮 = 两条用户消息之间 AI 的回复与工具调用。"""

    def __init__(self):
        self.text, self.tools, self.files = "", [], []

    def summary(self) -> str:
        tools = ", ".join(self.tools[-8:])
        return _cut(self.text, 500) + (f"\n[tools: {tools}]" if tools else "")


def _on_user(e: Event, turn: _Turn, sess: dict, out: list) -> None:
    seen = sess.get("user_seen", 0)
    sess["user_seen"] = seen + 1
    if seen == 0:
        return
    if _is_ok(e.text):
        q = _last_question(turn.text)
        if q:
            out.append({"kind": "ok", "user": e.text, "prev": q, "files": [], "cmd": "", "tail": ""})
    elif _is_correction(e.text):
        out.append({"kind": "correction", "user": _cut(e.text, 300), "prev": turn.summary(),
                    "files": sorted(set(turn.files)), "cmd": "", "tail": ""})


def _close_turn(turn: _Turn, sess: dict, last_user: str, out: list) -> None:
    counts = sess.setdefault("edit_turns", {})
    reworked = sess.setdefault("reworked", [])
    for f in sorted(set(turn.files)):
        counts[f] = counts.get(f, 0) + 1
        if counts[f] >= REWORK_TURNS and f not in reworked:
            reworked.append(f)
            out.append({"kind": "rework", "user": _cut(last_user, 300), "prev": "", "files": [f],
                        "cmd": "", "tail": f"edited in {counts[f]} turns"})


def _on_result(e: Event, sess: dict, out: list) -> None:
    if not e.cmd:
        return
    is_test = bool(TEST_RE.search(e.cmd))
    if e.error:
        if sess.get("last_fail") == e.cmd:
            out.append({"kind": "tool_fail", "user": "", "prev": "", "files": [], "cmd": _cut(e.cmd, 300),
                        "tail": _cut(e.text[-300:], 300)})
            sess["last_fail"] = None
        else:
            sess["last_fail"] = e.cmd
        if is_test and not sess.get("test_failed"):
            sess["test_failed"] = [e.cmd, e.text[-500:]]
        return
    sess["last_fail"] = None
    if is_test and sess.get("test_failed"):
        cmd, tail = sess["test_failed"]
        out.append({"kind": "test_flip", "user": "", "prev": "", "files": [], "cmd": _cut(cmd, 300),
                    "tail": _cut(tail, 500)})
        sess["test_failed"] = None


def extract(events: list[Event], sess: dict) -> list[dict]:
    """sess 为该会话的跨轮状态（JSON 可序列化），原地更新。"""
    out, turn = [], _Turn()
    last_user = sess.get("last_user", "")
    for e in events:
        if e.role == "user":
            _close_turn(turn, sess, last_user, out)
            _on_user(e, turn, sess, out)
            turn, last_user = _Turn(), e.text
        elif e.role == "assistant":
            turn.text = e.text
        elif e.role == "call":
            turn.tools.append(f"{e.tool} {e.cmd or e.path}".strip()[:80])
            if e.path:
                turn.files.append(e.path)
        elif e.role == "result":
            _on_result(e, sess, out)
    _close_turn(turn, sess, last_user, out)
    sess["last_user"] = _cut(last_user, 300)
    return out
