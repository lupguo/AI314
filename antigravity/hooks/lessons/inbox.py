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

    def defer(self, record: dict) -> None:
        """锁被占用时登记 transcript，由当前持锁者补处理（该会话可能不会再有 Stop）。"""
        self.dir.mkdir(exist_ok=True)
        with (self.dir / "pending.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def take_deferred(self) -> list[dict]:
        src = self.dir / "pending.jsonl"
        if not src.exists():
            return []
        mine = self.dir / f"pending.{os.getpid()}.jsonl"
        src.replace(mine)  # 改名后读取：期间新的登记会写入新文件，留待下次
        rows = [json.loads(x) for x in mine.read_text(encoding="utf-8").splitlines() if x.strip()]
        mine.unlink()
        return rows

    @contextlib.contextmanager
    def lock(self):
        with file_lock(self.dir / "lock") as got:
            yield got


def _holder_alive(path: Path) -> bool:
    try:
        pid = int(path.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        pid = 0
    if pid <= 0:  # 无法识别持有者：仅按时间判断残留
        try:
            return time.time() - path.stat().st_mtime < STALE_LOCK
        except FileNotFoundError:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _try_acquire_once(path: Path) -> bool:
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as f:
        f.write(str(os.getpid()))
    return True


def _try_acquire(path: Path) -> bool:
    if _try_acquire_once(path):
        return True
    if _holder_alive(path):
        return False
    with contextlib.suppress(FileNotFoundError):
        path.unlink()  # 持有者已退出：接管残留锁
    return _try_acquire_once(path)


@contextlib.contextmanager
def file_lock(path: Path, wait: float = 0):
    """PID 锁：持有者进程不存在才视为残留；释放时只删除自己持有的锁。wait>0 时轮询等待。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + wait
    got = _try_acquire(path)
    while not got and time.time() < deadline:
        time.sleep(0.1)
        got = _try_acquire(path)
    try:
        yield got
    finally:
        if got:
            with contextlib.suppress(OSError, ValueError):
                if path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                    path.unlink()
