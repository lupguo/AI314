"""回流：把全局库中成熟的经验在独立 worktree 中改进 content/，make check 通过后向 upstream 提 PR。"""
from __future__ import annotations

import json
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

from . import backoff, paths, runner, sampler, store
from .inbox import file_lock

GAP, CHECK_TIMEOUT = 86400, 600
NEW_STACK_MIN, NEW_STACK_PROJECTS = 5, 2
DRAFT = ("L0",)
CC_PREFIX = re.compile(r"^\s*\w+(\([^)]*\))?!?:\s*")  # 模型常自带 Conventional 前缀，统一由脚本加

PROMPT = """你是 AI314 工程规范仓库的维护者。下面是从多个业务项目自动汇总的经验条目（已去业务化，project 为匿名 id）。
请判断哪些条目已成熟（同一规则来自 ≥2 个项目，或累计次数 ≥3{ok_rule}），只把成熟条目以最小改动融入目标文件。

要求：
1. 去业务化：不得出现任何具体业务名词、项目名。
2. 只写可核查的硬约束（选型结论、物理边界、代码范式或反面禁令），禁止空泛说教。
3. 保持目标文件原有结构与风格，最小 diff；不要改动与条目无关的内容。{extra}
4. 只能修改或新建目标文件：{target}
5. 只输出一个 JSON 对象，不要任何解释：
{{"files":[{{"path":"{target}","content":"<修改后的完整文件内容>"}}],"adopted":[条目编号],"pending":[条目编号],"title":"<不超过 50 字的中文标题，不要带 feat(...): 前缀>"}}
没有成熟条目时输出 {{"files":[],"adopted":[],"pending":[全部编号],"title":""}}。

目标文件当前内容：
<<<
{current}
>>>

经验条目：
{records}
{sample}"""


class GitError(Exception):
    pass


def target(owner: str) -> tuple[str, str]:
    if owner == "L0":
        return "content/L0-constitution/AGENTS.base.md", "content/L0-constitution"
    if owner == "ok-defaults":
        return "content/L0-constitution/skills/planning/SKILL.md", "content/L0-constitution/skills/planning"
    if owner.startswith("new-stack:"):
        d = f"content/L1-stacks/stack-{owner.split(':', 1)[1]}"
        return f"{d}/SKILL.md", d
    layer = "content/L1-stacks" if owner.startswith("stack-") else "content/L2-modes"
    return f"{layer}/{owner}/SKILL.md", f"{layer}/{owner}"


def _scope(owner: str) -> str:
    if owner == "L0":
        return "constitution"
    if owner == "ok-defaults":
        return "planning"
    return "stack-" + owner.split(":", 1)[1] if owner.startswith("new-stack:") else owner


def _times(env) -> dict:
    try:
        return json.loads((paths.data_dir(env) / "contrib.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _touch(owner: str, env) -> None:
    data = _times(env)
    data[owner] = time.time()
    (paths.data_dir(env) / "contrib.json").write_text(json.dumps(data), encoding="utf-8")


def ready(pending: dict, cfg, env, now: float | None = None) -> list[str]:
    now = time.time() if now is None else now
    last = _times(env)
    out = []
    for owner, recs in sorted(pending.items()):
        if now - last.get(owner, 0) < GAP:
            continue
        if owner.startswith("new-stack:"):
            ok = len(recs) >= NEW_STACK_MIN and len({r.get("project") for r in recs}) >= NEW_STACK_PROJECTS
        else:
            ok = len(recs) >= cfg.lessons["contrib_min"]
        if ok:
            out.append(owner)
    return out


def _run(argv: list[str], env, cwd=None, timeout=120) -> str:
    r = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise GitError(f"{' '.join(argv[:3])}: {(r.stderr or r.stdout).strip()[-300:]}")
    return r.stdout.strip()


def _gh(env) -> str | None:
    return runner.which("gh", env)


def maybe_run(cfg, env) -> None:
    if not cfg.lessons["contribute"] or backoff.blocked("contribute", env):
        return
    src, gh = Path(cfg.lessons["src"]), _gh(env)
    if not (src / ".git").exists() or not gh:
        paths.log(f"[contribute] skip: src={src} exists={src.exists()} gh={gh}", env)
        return
    if subprocess.run([gh, "auth", "status"], env=env, capture_output=True).returncode != 0:
        paths.log("[contribute] skip: gh not authenticated", env)
        return
    with file_lock(paths.data_dir(env) / "contrib.lock") as got:
        if not got:
            return
        pending = store.global_pending(env)
        for owner in ready(pending, cfg, env):
            try:
                url = run_owner(owner, pending[owner], cfg, env)
                paths.log(f"[contribute] {owner}: {url or 'nothing mature'}", env)
            except Exception as e:  # 单个 owner 失败不影响其他 owner
                paths.log(f"[contribute] {owner} {type(e).__name__}: {e}", env)


def _upstream_url(cfg) -> str:
    # 以 upstream 为准：src 的 origin 可能是用户自己的 fork 或其他仓库
    return f"https://github.com/{cfg.lessons['upstream']}.git"


def _worktree(src: Path, owner: str, cfg, env) -> tuple[Path, str]:
    branch = f"lessons/{owner.replace(':', '-')}-{time.strftime('%Y%m%d-%H%M%S')}"
    wt = paths.data_dir(env) / "worktrees" / branch.replace("/", "_")
    wt.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "-C", str(src), "fetch", "-q", _upstream_url(cfg), "main"], env)
    # 独立 worktree：不切换用户在 src 中的当前分支
    _run(["git", "-C", str(src), "worktree", "add", "-q", "-b", branch, str(wt), "FETCH_HEAD"], env)
    return wt, branch


def _cleanup(src: Path, wt: Path, branch: str, env) -> None:
    subprocess.run(["git", "-C", str(src), "worktree", "remove", "--force", str(wt)], env=env, capture_output=True)
    subprocess.run(["git", "-C", str(src), "branch", "-D", branch], env=env, capture_output=True)


def _prompt(owner: str, recs: list[dict], wt: Path, env) -> str:
    tgt, _ = target(owner)
    cur = (wt / tgt).read_text(encoding="utf-8") if (wt / tgt).is_file() else "（文件不存在，需新建）"
    lines = [json.dumps({"n": i, **{k: v for k, v in r.items() if k not in ("_i", "status", "owner")}},
                        ensure_ascii=False) for i, r in enumerate(recs)]
    extra, sample, ok_rule = "", "", ""
    if owner == "ok-defaults":
        ok_rule = "；提问类条目需 ≥2 个项目且累计 ≥5 次"
        extra = "\n   提问类条目写入目标文件的「默认不再询问的决策」小节（不存在则新建），每条一行：问题类型 → 默认做法。"
    if owner.startswith("new-stack:"):
        extra = ("\n   这是新建 L1 技术栈规范：frontmatter name 必须为目录名，description 以\"当…时强制加载此技能\"句式，"
                 "正文含 `## 1.`~`## 4.` 四章；经验条目作为反面禁令依据，依据不足处写 [待补充]。")
        top = Counter(r.get("project") for r in recs).most_common(1)[0][0]
        root = store.project_path(top, env)
        sample = "\n项目采样：\n" + sampler.sample(root) if root and root.is_dir() else ""
    return PROMPT.format(ok_rule=ok_rule, extra=extra, target=tgt, current=cur, records="\n".join(lines),
                         sample=sample)


def _write(wt: Path, files: list, allowed: str) -> int:
    base = (wt / allowed).resolve()
    for f in files:
        if not isinstance(f, dict) or not isinstance(f.get("content"), str):
            raise runner.RunError("bad_output", "file entry malformed")
        dest = (wt / str(f.get("path", ""))).resolve()
        if base != dest.parent and base not in dest.parents:
            raise runner.RunError("bad_output", f"path escapes {allowed}: {f.get('path')}")
    for f in files:
        dest = (wt / f["path"]).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f["content"], encoding="utf-8")
    return len(files)


def _body(owner: str, recs: list[dict], adopted: list[int]) -> str:
    counts = Counter()
    for i in adopted:
        counts[recs[i].get("project", "?")] += int(recs[i].get("count", 1))
    rows = "\n".join(f"| {pid} | {n} |" for pid, n in counts.most_common())
    rules = "\n".join(f"- {recs[i].get('rule') or recs[i].get('question')}" for i in adopted)
    return (f"由 AI314 lessons loop 自动生成，归属 `{owner}`。\n\n## 采纳的经验\n{rules}\n\n"
            f"## 证据（匿名项目 id）\n| 项目 | 次数 |\n| :-- | :-- |\n{rows}\n")


def _push(wt: Path, branch: str, cfg, env) -> tuple[str, str]:
    """返回 (PR 的 --head, 推送目标 URL)。"""
    gh, up = _gh(env), cfg.lessons["upstream"]
    perm = subprocess.run([gh, "api", f"repos/{up}", "--jq", ".permissions.push"], env=env,
                          capture_output=True, text=True).stdout.strip()
    if perm == "true":
        url = _upstream_url(cfg)
        _run(["git", "-C", str(wt), "push", "-q", url, f"HEAD:refs/heads/{branch}"], env)
        return branch, url
    _run([gh, "repo", "fork", up, "--clone=false"], env)
    login = _run([gh, "api", "user", "--jq", ".login"], env)
    fork = f"https://github.com/{login}/{up.split('/')[-1]}.git"
    _run(["git", "-C", str(wt), "push", "-q", fork, f"HEAD:refs/heads/{branch}"], env)
    return f"{login}:{branch}", fork


def _publish(owner, recs, out, wt, branch, cfg, env) -> str:
    adopted = [i for i in out.get("adopted") or [] if isinstance(i, int) and 0 <= i < len(recs)]
    subject = CC_PREFIX.sub("", str(out.get("title") or "")).strip() or "吸收项目经验"
    title = f"feat({_scope(owner)}): {subject[:60]}"
    _run(["git", "-C", str(wt), "add", "-A"], env)
    _run(["git", "-C", str(wt), "commit", "-qm", title + "\n\n由 AI314 lessons loop 自动生成。"], env)
    head, remote = _push(wt, branch, cfg, env)
    argv = [_gh(env), "pr", "create", "--repo", cfg.lessons["upstream"], "--base", "main", "--head", head,
            "--title", title, "--body", _body(owner, recs, adopted)]
    if owner in DRAFT or owner.startswith("new-stack:"):
        argv.append("--draft")
    try:
        url = (_run(argv, env).splitlines() or [""])[-1]
    except GitError:
        # PR 未建成：删除已推送的远端分支，避免残留；条目保持 pending 等待下次
        subprocess.run(["git", "-C", str(wt), "push", "-q", remote, "--delete", branch], env=env, capture_output=True)
        raise
    store.global_mark(owner, [recs[i]["_i"] for i in adopted], "submitted", env, pr=url)
    return url


def run_owner(owner: str, recs: list[dict], cfg, env) -> str | None:
    src = Path(cfg.lessons["src"])
    wt, branch = _worktree(src, owner, cfg, env)
    _touch(owner, env)  # 无论成败，同一 owner 24h 内不重复尝试
    try:
        out = runner.ask(_prompt(owner, recs, wt, env), cfg, "contribute", env, wt)
        files = out.get("files") or []
        if not files:
            return None
        _write(wt, files, target(owner)[1])
        r = subprocess.run(["make", "check", "CLAUDE_BIN=__none__", "AGY_BIN=__none__"], cwd=wt, env=env,
                           capture_output=True, text=True, timeout=CHECK_TIMEOUT)
        if r.returncode != 0:
            paths.log(f"[contribute] {owner} check_failed: {(r.stdout + r.stderr)[-500:]}", env)
            return None
        url = _publish(owner, recs, out, wt, branch, cfg, env)
        backoff.ok("contribute", env)
        return url
    except runner.RunError as e:
        backoff.fail("contribute", e.kind, env)
        paths.log(f"[contribute] {owner} {e.kind}: {e.detail[:300]}", env)
        return None
    finally:
        _cleanup(src, wt, branch, env)
