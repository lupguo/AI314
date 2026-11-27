#!/usr/bin/env python3
"""版本发布：更新 ai314.toml 版本与 CHANGELOG.md。

用法：python3 scripts/release.py <x.y.z> "<变更说明>" [--root .]
git 提交与打 tag 由 Makefile 的 release 目标在 `make check` 通过后完成。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import tomllib
from pathlib import Path

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_LINE = re.compile(r'^(version\s*=\s*)"[^"]*"', re.M)


def _parse(v: str) -> tuple[int, int, int]:
    m = SEMVER.match(v or "")
    if not m:
        raise SystemExit(f"版本号 '{v}' 不是 semver (x.y.z)")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def bump(root: Path, version: str, note: str, today: str | None = None) -> None:
    """校验通过后才写文件；任何校验失败 raise SystemExit 且不修改文件。"""
    root = Path(root)
    toml_path = root / "ai314.toml"
    toml_text = toml_path.read_text(encoding="utf-8")
    current = tomllib.loads(toml_text)["plugin"]["version"]
    if _parse(version) <= _parse(current):
        raise SystemExit(f"新版本 {version} 必须大于当前版本 {current}")
    if not note.strip():
        raise SystemExit("变更说明不能为空")

    # [plugin] 段的 version 是文件中第一个 version 键
    new_toml = VERSION_LINE.sub(rf'\g<1>"{version}"', toml_text, count=1)
    today = today or _dt.date.today().isoformat()
    entry = f"## v{version} - {today}\n\n- {note.strip()}\n"
    log_path = root / "CHANGELOG.md"
    if log_path.exists():
        log = log_path.read_text(encoding="utf-8")
        head, sep, rest = log.partition("\n## ")
        new_log = f"{head.rstrip()}\n\n{entry}\n## {rest}" if sep else f"{log.rstrip()}\n\n{entry}"
    else:
        new_log = f"# Changelog\n\n{entry}"

    toml_path.write_text(new_toml, encoding="utf-8")
    log_path.write_text(new_log, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("note")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    bump(Path(a.root), a.version, a.note)
    print(f"已更新到 v{a.version}")


if __name__ == "__main__":
    main()
