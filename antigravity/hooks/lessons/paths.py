"""路径约定：AI314_HOME（默认 ~/.ai314）下 config.toml 与 data/；项目根与匿名项目 id。"""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path


def home(env=os.environ) -> Path:
    h = env.get("AI314_HOME")
    if h:
        return Path(h).expanduser()
    return Path(env.get("HOME", str(Path.home()))) / ".ai314"


def data_dir(env=os.environ) -> Path:
    return home(env) / "data"


def log(msg: str, env=os.environ) -> None:
    p = data_dir(env) / "logs/lessons.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%F %T')} {msg}\n")


def project_root(cwd: str) -> Path | None:
    if not cwd or not Path(cwd).is_dir():
        return None
    r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def project_id(root: Path) -> str:
    # PR 与全局库只出现匿名 id，避免业务项目名外泄
    return "p-" + hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:8]
