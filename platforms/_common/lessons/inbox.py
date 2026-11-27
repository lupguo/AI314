"""项目内 .ai314/：inbox.jsonl（原始信号片段，永不入库）、state.json（偏移与会话状态）、锁。"""
from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

STALE_LOCK = 1800


class Project:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.dir = self.root / ".ai314"

    def ensure(self) -> None:
        self.dir.mkdir(exist_ok=True)
        gi = self.dir / ".gitignore"
        if not gi.exists():
            gi.write_text("*\n", encoding="utf-8")  # 自带忽略，不改用户的 .gitignore

    def disabled(self) -> bool:
        return (self.dir / "disabled").exists()

    @property
    def inbox(self) -> Path:
        return self.dir / "inbox.jsonl"

    def append(self, items: list[dict], meta: dict) -> None:
        if not items:
            return
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.inbox.open("a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps({"ts": ts, **meta, **it}, ensure_ascii=False) + "\n")

    def items(self) -> list[dict]:
        if not self.inbox.is_file():
            return []
        out = []
        for line in self.inbox.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def drop(self, n: int) -> None:
        rest = self.items()[n:]
        self.inbox.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rest), encoding="utf-8")

    def state(self) -> dict:
        try:
            return json.loads((self.dir / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save_state(self, s: dict) -> None:
        tmp = self.dir / "state.json.tmp"
        tmp.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.dir / "state.json")

    @contextlib.contextmanager
    def lock(self):
        with file_lock(self.dir / "lock") as got:
            yield got


@contextlib.contextmanager
def file_lock(path: Path):
    """O_EXCL 锁；超过 STALE_LOCK 秒视为崩溃残留并接管。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    got = False
    for _ in range(2):
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            got = True
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > STALE_LOCK:
                    path.unlink()
                    continue
            except FileNotFoundError:
                continue
            break
    try:
        yield got
    finally:
        if got:
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
