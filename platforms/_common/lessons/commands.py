"""手动命令：distill（立即提炼当前项目）、contribute（立即尝试回流）、doctor（真实验证网络与 runner）。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import config, contribute, distill, inbox, netcheck, paths, runner

DOCTOR_PROMPT = 'Reply with exactly this JSON and nothing else: {"ok":1}'


def _distill(project: str, env) -> int:
    root = paths.project_root(project)
    if root is None:
        print(f"not a git project: {project}")
        return 1
    proj = inbox.Project(root)
    with proj.lock() as got:
        if not got:
            print("busy: another capture/distill is running")
            return 1
        if not proj.items():
            print("inbox empty")
            return 0
        ok = distill.run(proj, config.load(env), env)
    print("distill ok" if ok else f"distill failed, see {paths.data_dir(env) / 'logs/lessons.log'}")
    return 0 if ok else 1


def _contribute(env) -> int:
    contribute.maybe_run(config.load(env), env)
    print(f"done, see {paths.data_dir(env) / 'logs/lessons.log'}")
    return 0


def doctor(env, stage: str = "distill") -> int:
    cfg = config.load(env)
    for w in cfg.warnings:
        print(f"warning: {w}")
    try:
        name, b = runner.resolve(cfg.agent_for(stage), env)
    except runner.RunError as e:
        print(f"network: skipped\nrunner: fail no_runner ({e.detail})")
        return 1
    child = netcheck.child_env(cfg.network, env)
    url = cfg.network.get("probe_url") or runner.default_probe(name, child)
    if not netcheck.probe(url, child):
        print(f"network: fail ({url}，检查 [network] 代理配置)")
        return 1
    print(f"network: ok ({url})")
    try:
        with tempfile.TemporaryDirectory(prefix="ai314-doctor-") as tmp:
            out = runner.ask(DOCTOR_PROMPT, cfg, stage, env, Path(tmp))
    except runner.RunError as e:
        print(f"runner: fail {e.kind} ({name} {b}): {e.detail[:300]}")
        return 1
    if out != {"ok": 1}:
        print(f"runner: fail bad_output ({name}): {out}")
        return 1
    print(f"runner: ok ({name} {b}, model={cfg.agent_for(stage).get('model') or 'default'})")
    return 0


def run(args, env) -> int:
    if args.cmd == "distill":
        return _distill(args.project, env)
    if args.cmd == "contribute":
        return _contribute(env)
    return doctor(env)
