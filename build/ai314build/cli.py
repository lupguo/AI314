"""命令行入口：python3 -m ai314build {build,validate} [--root .] [--out dist] [--platforms claude,antigravity]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import build, model, validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ai314build")
    ap.add_argument("command", choices=["build", "validate"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--platforms", default=",".join(build.PLATFORMS))
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))  # 让 platforms 包可导入
    project = model.load(root)

    issues = validate.validate(project)
    for i in issues:
        print(f"[{i.level}] {i.path}: {i.msg}", file=sys.stderr)
    if any(i.level == "error" for i in issues):
        print(f"校验失败：{sum(i.level == 'error' for i in issues)} 个错误", file=sys.stderr)
        return 1
    if args.command == "validate":
        print(f"校验通过：{len(project.skills)} 个技能，版本 v{project.version}")
        return 0

    plats = [p for p in args.platforms.split(",") if p]
    out = (root / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    build.build_all(project, out, plats)
    print(f"构建完成：v{project.version} → {out} ({', '.join(plats)})，{len(project.skills)} 个技能")
    return 0
