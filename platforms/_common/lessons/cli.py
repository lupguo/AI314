"""命令入口：capture（Stop hook）| distill | contribute | status | doctor。"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from . import backoff, config, distill, hookio, inbox, paths, runner, signals, transcript

MAX_SESSIONS = 20


def _capture_locked(proj: inbox.Project, hi: hookio.HookInput, platform: str) -> None:
    st = proj.state()
    offsets = st.setdefault("offsets", {})
    key = str(hi.transcript)
    events, end = transcript.read(platform, hi.transcript, offsets.get(key, 0))
    sessions = st.setdefault("sessions", {})
    sess = sessions.setdefault(hi.session, {})
    proj.append(signals.extract(events, sess), {"platform": platform, "session": hi.session})
    offsets[key] = end
    for old in list(sessions)[:-MAX_SESSIONS]:
        sessions.pop(old, None)
    proj.save_state(st)


def _capture_work(proj, hi, platform, cfg, env) -> None:
    with proj.lock() as got:
        if not got:
            return
        proj.ensure()
        _capture_locked(proj, hi, platform)
        if cfg.lessons["mode"] != "capture-only":
            distill.maybe_run(proj, cfg, env)


def _detach() -> bool:
    """fork 到后台：父进程立即返回，hook 不阻塞会话；子进程脱离 hook 的 stdio。"""
    if os.fork() > 0:
        return False
    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(devnull, fd)
    return True


def capture(platform: str, raw: str, env, foreground: bool = False) -> int:
    if env.get("AI314_HEADLESS") == "1":
        return 0
    cfg = config.load(env)
    hi = hookio.parse(platform, raw)
    if cfg.lessons["mode"] == "off" or hi is None:
        return 0
    root = paths.project_root(hi.cwd)
    if root is None:
        return 0
    proj = inbox.Project(root)
    if proj.disabled():
        return 0
    if not foreground and not _detach():
        return 0
    try:
        _capture_work(proj, hi, platform, cfg, env)
    except Exception as e:  # 后台失败只记日志，绝不影响会话
        paths.log(f"[capture] {type(e).__name__}: {e}", env)
    if not foreground:
        os._exit(0)
    return 0


def _mask(url: str) -> str:
    if not url:
        return "-"
    u = urlparse(url)
    return f"{u.hostname}:{u.port}" if u.port else (u.hostname or "?")


def status(env, cwd: str) -> int:
    cfg = config.load(env)
    print(f"home: {paths.home(env)}")
    print(f"mode: {cfg.lessons['mode']}  contribute: {cfg.lessons['contribute']}  "
          f"upstream: {cfg.lessons['upstream']}  src: {cfg.lessons['src']}")
    agent = cfg.agent_for("distill")
    try:
        name, b = runner.resolve(agent, env)
        print(f"runner: {name} ({b})  model: {agent.get('model') or '(default)'}")
    except runner.RunError:
        print(f"runner: not found ({agent.get('runner')})")
    print(f"proxy: https={_mask(cfg.network['https_proxy'])} http={_mask(cfg.network['http_proxy'])}")
    root = paths.project_root(cwd)
    if root:
        print(f"project: {root} ({paths.project_id(root)})  inbox: {len(inbox.Project(root).items())}")
    print(f"backoff: {json.dumps(backoff.snapshot(env), ensure_ascii=False)}")
    pj = paths.data_dir(env) / "projects.json"
    if pj.is_file():
        for pid, info in json.loads(pj.read_text(encoding="utf-8")).items():
            print(f"  {pid} -> {info.get('path')}")
    for w in cfg.warnings:
        print(f"warning: {w}")
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ai314-lessons")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--platform", choices=["claude", "antigravity"], default="claude")
    c.add_argument("--foreground", action="store_true")
    d = sub.add_parser("distill")
    d.add_argument("--project", default=os.getcwd())
    sub.add_parser("contribute")
    sub.add_parser("status")
    sub.add_parser("doctor")
    return p


def main(argv: list[str], stdin=sys.stdin, env=os.environ) -> int:
    a = _parser().parse_args(argv)
    if a.cmd == "capture":
        return capture(a.platform, stdin.read(), env, a.foreground)
    if env.get("AI314_HEADLESS") == "1":
        return 0
    if a.cmd == "status":
        return status(env, os.getcwd())
    from . import commands  # 按需加载，capture 热路径保持轻量
    return commands.run(a, env)
