"""经验存储：项目 docs/ai314/lessons.md（人可读、机可合并）与本机全局库 data/lessons/<owner>.jsonl。"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import paths
from .inbox import file_lock

HEADER = "# 项目经验（AI314 自动维护，可手改）"
MAX_LINES, STALE_DAYS = 150, 30
FIELDS = (("scene", "场景"), ("symptom", "表现"), ("fix", "正确做法"), ("rule", "通用规则"),
          ("owner", "归属"), ("last", "最近"))
HEAD_RE = re.compile(r"^### (L-\d+) (.*)（×(\d+)）\s*$")
BULLET_RE = re.compile(r"^- (场景|表现|正确做法|通用规则|归属|最近)：(.*)$")
OK_RE = re.compile(r"^- (.*)（OK ×(\d+)）→ (.*)$")


@dataclass
class Lesson:
    id: str
    title: str
    scene: str
    symptom: str
    fix: str
    owner: str
    rule: str
    count: int
    last: str


@dataclass
class OkDefault:
    question: str
    suggest: str
    count: int


def _block(x: Lesson) -> list[str]:
    lines = [f"### {x.id} {x.title}（×{x.count}）"]
    lines += [f"- {label}：{getattr(x, attr)}" for attr, label in FIELDS]
    return lines + [""]


def render(lessons: list[Lesson], oks: list[OkDefault]) -> str:
    out = [HEADER, "", "## 反面经验", ""]
    for x in sorted(lessons, key=lambda l: (-l.count, l.id)):
        out += _block(x)
    out += ["## 可默认放行的提问", ""]
    out += [f"- {o.question}（OK ×{o.count}）→ {o.suggest}" for o in sorted(oks, key=lambda o: -o.count)]
    return "\n".join(out).rstrip() + "\n"


def load(path: Path) -> tuple[list[Lesson], list[OkDefault]]:
    if not path.is_file():
        return [], []
    label_attr = {label: attr for attr, label in FIELDS}
    lessons, oks, cur = [], [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if m := HEAD_RE.match(line):
            cur = Lesson(m.group(1), m.group(2), "", "", "", "project", "", int(m.group(3)), "")
            lessons.append(cur)
        elif cur and (m := BULLET_RE.match(line)):
            setattr(cur, label_attr[m.group(1)], m.group(2).strip())
        elif m := OK_RE.match(line):
            cur = None
            oks.append(OkDefault(m.group(1).strip(), m.group(3).strip(), int(m.group(2))))
        elif line.startswith("## "):
            cur = None
    return lessons, oks


def _archive(lessons: list[Lesson], oks, archive: Path, today: str) -> list[Lesson]:
    """超长时把"次数最低且 30 天未增长"的条目移入归档，控制每次会话的读取成本。"""
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=STALE_DAYS)).isoformat()
    keep = list(lessons)
    stale = sorted((x for x in keep if x.last and x.last < cutoff), key=lambda l: (l.count, l.last))
    moved = []
    while stale and len(render(keep, oks).splitlines()) > MAX_LINES:
        x = stale.pop(0)
        keep.remove(x)
        moved.append(x)
    if moved:
        prefix = "" if archive.exists() else "# 项目经验归档\n\n"
        with archive.open("a", encoding="utf-8") as f:
            f.write(prefix + "\n".join(line for x in moved for line in _block(x)) + "\n")
    return keep


def save(path: Path, lessons: list[Lesson], oks: list[OkDefault], archive: Path, today: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = _archive(lessons, oks, archive, today)
    path.write_text(render(keep, oks), encoding="utf-8")


def _glock(env):
    # 多个项目的后台进程可能同时读写全局库
    return file_lock(paths.data_dir(env) / "lessons" / ".lock", wait=10)


def _gfile(owner: str, env) -> Path:
    return paths.data_dir(env) / "lessons" / (owner.replace(":", "_") + ".jsonl")


def global_append(owner: str, records: list[dict], env=os.environ) -> None:
    if not records:
        return
    f = _gfile(owner, env)
    with _glock(env), f.open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps({"owner": owner, "status": "pending", **r}, ensure_ascii=False) + "\n")


def _gread(f: Path) -> list[dict]:
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def global_pending(env=os.environ) -> dict[str, list[dict]]:
    """返回 {owner: [record...]}，每条附带 "_i"（文件内行号）供 global_mark 使用。"""
    d = paths.data_dir(env) / "lessons"
    out: dict[str, list[dict]] = {}
    for f in sorted(d.glob("*.jsonl")) if d.is_dir() else []:
        for i, r in enumerate(_gread(f)):
            if r.get("status") == "pending":
                out.setdefault(r.get("owner", f.stem), []).append({**r, "_i": i})
    return out


def global_mark(owner: str, idxs: list[int], status: str, env=os.environ, **extra) -> None:
    f = _gfile(owner, env)
    with _glock(env):
        rows = _gread(f)
        for i in idxs:
            if 0 <= i < len(rows):
                rows[i].update(status=status, **extra)
        f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def register_project(pid: str, root: Path, env=os.environ) -> None:
    f = paths.data_dir(env) / "projects.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data[pid] = {"path": str(root), "name": Path(root).name}
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def project_path(pid: str, env=os.environ) -> Path | None:
    try:
        info = json.loads((paths.data_dir(env) / "projects.json").read_text(encoding="utf-8")).get(pid)
    except (OSError, ValueError):
        return None
    return Path(info["path"]) if info else None
