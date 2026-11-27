"""退避：network/auth/no_runner 不消耗额度，指数退避 1h→24h；bad_output 每天至多重试 1 次。"""
from __future__ import annotations

import json
import os
import time

from . import paths

HOUR, DAY = 3600, 86400


def _file(env):
    return paths.data_dir(env) / "backoff.json"


def _load(env) -> dict:
    try:
        return json.loads(_file(env).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict, env) -> None:
    f = _file(env)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def blocked(stage: str, env=os.environ, now: float | None = None) -> str | None:
    s = _load(env).get(stage)
    now = time.time() if now is None else now
    return s["kind"] if s and now < s.get("until", 0) else None


def fail(stage: str, kind: str, env=os.environ, now: float | None = None) -> None:
    data = _load(env)
    now = time.time() if now is None else now
    prev = data.get(stage, {})
    n = prev.get("fails", 0) + 1 if prev.get("kind") == kind else 1
    if kind == "bad_output":
        wait = 0 if n == 1 else DAY
    else:
        wait = min(HOUR * 2 ** (n - 1), DAY)
    data[stage] = {"kind": kind, "fails": n, "until": now + wait}
    _save(data, env)


def ok(stage: str, env=os.environ) -> None:
    data = _load(env)
    if data.pop(stage, None) is not None:
        _save(data, env)


def snapshot(env=os.environ) -> dict:
    return _load(env)
