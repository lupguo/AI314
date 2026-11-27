"""提炼：把项目 inbox 的原始信号交给无头 Agent 归纳为经验，合并进 lessons.md 并汇总到全局库。"""
from __future__ import annotations

import datetime as dt
import json
import re
import tempfile
import time
from pathlib import Path

from . import backoff, paths, runner, store

OWNER_RE = re.compile(r"^(L0|project|(stack|mode)-[a-z0-9-]+|new-stack:[a-z0-9-]+)$")
STALE_SECONDS = 7 * 86400
PLUGIN_SKILLS = Path(__file__).resolve().parents[2] / "skills"

PROMPT = """你是 AI314 工程规范的经验提炼器。下面是某个项目中 AI Agent 被用户纠正、返工、测试失败、或用户直接回复 OK 的原始信号片段。
请归纳出"可避免同类错误重犯"的反面经验，并统计"用户总是直接放行的提问类型"。

规则：
1. 只保留有明确证据、可复用的经验；噪声（正常需求描述误判为纠正等）直接丢弃并计入 dropped。
2. 与已有条目同类的用 merge（给出已有 id 与本批新增次数 add_count），否则用 new（count 为本批支撑该条目的信号数）。
3. owner 只能取：{owners}。仅与本项目业务相关的用 project。
4. generic_rule：去业务化后的一句可核查硬约束，禁止出现项目名、业务名词；owner 为 project 时留空。
5. ok_patterns.question_type 也必须去业务化（如"是否为草稿创建目录"），suggest 写"此类决策默认采用 X，不再询问"。
6. 只输出一个 JSON 对象，不要任何解释。格式：
{{"lessons":[{{"op":"merge","id":"L-001","add_count":2}},{{"op":"new","title":"","scene":"","symptom":"","fix":"","owner":"","generic_rule":"","count":1}}],
 "ok_patterns":[{{"question_type":"","count":1,"suggest":""}}],"dropped":0}}

已有条目索引：
{index}

原始信号（JSON Lines）：
{signals}
"""


def _age(item: dict, now: float) -> float:
    try:
        return now - time.mktime(time.strptime(item.get("ts", ""), "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return 0


def should_run(items: list[dict], cfg, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    if sum(1 for i in items if i.get("kind") != "ok") >= cfg.lessons["distill_min"]:
        return True
    return len(items) >= 3 and _age(items[0], now) >= STALE_SECONDS


def maybe_run(project, cfg, env) -> None:
    items = project.items()
    if items and should_run(items, cfg) and not backoff.blocked("distill", env):
        run(project, cfg, env)


def _owners() -> list[str]:
    names = sorted(p.name for p in PLUGIN_SKILLS.glob("*") if p.name.startswith(("stack-", "mode-")))
    return ["L0", "project", *names, "new-stack:<技术特征>"]


def _valid_owner(owner: str, owners: list[str]) -> bool:
    if not OWNER_RE.match(owner or ""):
        return False
    known = [o for o in owners if o.startswith(("stack-", "mode-"))]
    return not owner.startswith(("stack-", "mode-")) or not known or owner in known


def _prompt(items, lessons, owners) -> str:
    index = "\n".join(f"- {x.id} {x.title}（归属 {x.owner}）" for x in lessons) or "（无）"
    sigs = "\n".join(json.dumps({k: v for k, v in i.items() if k not in ("ts", "session")}, ensure_ascii=False)
                     for i in items)
    return PROMPT.format(owners="、".join(owners), index=index, signals=sigs)


def _pos(v) -> int:
    """模型给的次数可能是字符串或缺失：容错为 ≥1 的整数。"""
    try:
        return max(int(v), 1)
    except (TypeError, ValueError):
        return 1


def _next_id(lessons) -> str:
    n = max((int(x.id[2:]) for x in lessons), default=0)
    return f"L-{n + 1:03d}"


def _apply_lessons(out, lessons, owners, today, pid, env) -> list[tuple[str, dict]]:
    by_id, glob = {x.id: x for x in lessons}, []
    for it in out.get("lessons") or []:
        if not isinstance(it, dict):
            continue
        if it.get("op") == "merge" and it.get("id") in by_id:
            x, add = by_id[it["id"]], _pos(it.get("add_count"))
            x.count, x.last = x.count + add, today
        elif it.get("op") == "new" and it.get("title") and _valid_owner(it.get("owner", ""), owners):
            x = store.Lesson(_next_id(lessons), it["title"], it.get("scene", ""), it.get("symptom", ""),
                             it.get("fix", ""), it["owner"], it.get("generic_rule", ""), 1, today)
            x.count = add = _pos(it.get("count"))
            lessons.append(x)
            by_id[x.id] = x
        else:
            paths.log(f"[distill] skip invalid item: {json.dumps(it, ensure_ascii=False)[:200]}", env)
            continue
        if x.owner != "project" and x.rule:
            glob.append((x.owner, {"rule": x.rule, "title": x.title, "project": pid, "count": add, "date": today}))
    return glob


def _apply_oks(out, oks, today, pid) -> list[dict]:
    by_q, recs = {o.question: o for o in oks}, []
    for p in out.get("ok_patterns") or []:
        if not isinstance(p, dict) or not p.get("question_type"):
            continue
        q, n, s = p["question_type"], _pos(p.get("count")), p.get("suggest", "")
        if q in by_q:
            by_q[q].count += n
        else:
            by_q[q] = store.OkDefault(q, s, n)
            oks.append(by_q[q])
        recs.append({"question": q, "suggest": s, "project": pid, "count": n, "date": today})
    return recs


def run(project, cfg, env, today: str | None = None) -> bool:
    """调用方需持有项目锁。失败时 inbox 原样保留并进入退避。"""
    today = today or dt.date.today().isoformat()
    items = project.items()
    md = project.root / "docs/ai314/lessons.md"
    lessons, oks = store.load(md)
    owners = _owners()
    try:
        with tempfile.TemporaryDirectory(prefix="ai314-distill-") as tmp:
            out = runner.ask(_prompt(items, lessons, owners), cfg, "distill", env, Path(tmp))
        if not isinstance(out.get("lessons", []), list) or not isinstance(out.get("ok_patterns", []), list):
            raise runner.RunError("bad_output", "schema mismatch")
    except runner.RunError as e:
        backoff.fail("distill", e.kind, env)
        paths.log(f"[distill] {project.root} {e.kind}: {e.detail[:300]}", env)
        return False
    pid = paths.project_id(project.root)
    glob = _apply_lessons(out, lessons, owners, today, pid, env)
    ok_recs = _apply_oks(out, oks, today, pid)
    store.save(md, lessons, oks, md.with_name("lessons-archive.md"), today)
    for owner, rec in glob:
        store.global_append(owner, [rec], env)
    store.global_append("ok-defaults", ok_recs, env)
    store.register_project(pid, project.root, env)
    project.drop(len(items))
    backoff.ok("distill", env)
    paths.log(f"[distill] {project.root} ok: {len(items)} signals, {len(glob)} global, {len(ok_recs)} ok", env)
    from . import contribute
    contribute.maybe_run(cfg, env)
    return True
