"""无头 Agent 调用：claude / tclaude / agy / codex 统一为"prompt 进、JSON 出"，不授予任何工具。"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import netcheck

ORDER = ("claude", "tclaude", "agy", "codex")
# prompt 内含不可信的会话片段：一律禁用工具 / MCP，防止提示注入借用户的权限配置执行操作
CLAUDE_NO_TOOLS = ["--tools", "", "--strict-mcp-config", "--permission-mode", "default"]
AGY_NO_TOOLS = ["--mode", "plan", "--sandbox"]  # 不带 --dangerously-skip-permissions，工具请求在 print 模式被拒绝
EXTRA_DIRS = ("~/.local/bin", "/opt/homebrew/bin", "/usr/local/bin")
NET_RE = re.compile(r"EOF|timeout|timed out|connection|dial tcp|proxy|ECONNREFUSED|ENOTFOUND|SSL|TLS|"
                    r"network|Eligibility check failed", re.I)
AUTH_RE = re.compile(r"\b401\b|unauthori[sz]ed|not logged|/login|log ?in|authenticat|credential|api key", re.I)


class RunError(Exception):
    def __init__(self, kind: str, detail: str = ""):
        super().__init__(f"{kind}: {detail[:300]}")
        self.kind, self.detail = kind, detail


def classify(text: str) -> str:
    if AUTH_RE.search(text):
        return "auth"
    if NET_RE.search(text):
        return "network"
    return "bad_output"


def which(name: str, env) -> str | None:
    found = shutil.which(name, path=env.get("PATH", ""))
    if found:
        return found
    # hook 进程的 PATH 可能比交互 shell 精简（如缺 ~/.local/bin）
    for d in EXTRA_DIRS:
        p = Path(d.replace("~", env.get("HOME", "~"), 1)) / name
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None


def resolve(agent: dict, env) -> tuple[str, str]:
    name = agent.get("runner") or "auto"
    if agent.get("bin"):
        b = os.path.expanduser(agent["bin"])
        if not os.access(b, os.X_OK):
            raise RunError("no_runner", b)
        return (Path(b).name if name == "auto" else name), b
    for cand in (ORDER if name == "auto" else (name,)):
        found = which(cand, env)
        if found:
            return cand, found
    raise RunError("no_runner", name)


def build(name: str, bin_: str, agent: dict, prompt: str) -> tuple[list[str], str | None]:
    model, extra = agent.get("model") or "", list(agent.get("extra_args") or [])
    if name == "agy":
        # 真机验证：agy 的 -p 必须紧跟 prompt 参数，不读 stdin
        argv = [bin_, "--output-format", "json", "--print-timeout", f"{agent.get('timeout', 300)}s",
                "--disable-slash-commands", *AGY_NO_TOOLS]
        argv += ["--model", model] if model else []
        return argv + extra + ["-p", prompt], None
    if name == "codex":
        argv = [bin_, "exec"] + (["-c", f'model="{model}"'] if model else [])
        return argv + ["--sandbox", "read-only"] + extra + ["-"], prompt
    argv = [bin_, "-p", "--output-format", "json", *CLAUDE_NO_TOOLS] + (["--model", model] if model else [])
    return argv + extra, prompt


def default_probe(name: str, env) -> str:
    if name == "agy":
        return "https://daily-cloudcode-pa.googleapis.com"
    if name == "codex":
        return "https://api.openai.com"
    return env.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"


def _last_json_line(stdout: str) -> dict | None:
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def unwrap(name: str, stdout: str) -> str:
    if name == "codex":
        return stdout
    d = _last_json_line(stdout)
    if d is None:
        raise RunError(classify(stdout), stdout)
    if name == "agy":
        if d.get("status") != "SUCCESS":
            err = str(d.get("error") or stdout)
            raise RunError(classify(err), err)
        return str(d.get("response") or "")
    if d.get("is_error"):
        err = str(d.get("result") or stdout)
        raise RunError(classify(err), err)
    return str(d.get("result") or "")


def extract_json(text: str) -> dict:
    """取第一个括号配平的 JSON 对象，兼容 ```json 代码块与前后说明文字。"""
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except ValueError:
                        pass
                    break
        start = text.find("{", start + 1)
    raise RunError("bad_output", text[:300])


def ask(prompt: str, cfg, stage: str, env, cwd: Path) -> dict:
    agent = cfg.agent_for(stage)
    name, bin_ = resolve(agent, env)
    child = netcheck.child_env(cfg.network, env)
    url = cfg.network.get("probe_url") or default_probe(name, child)
    if not netcheck.probe(url, child):
        raise RunError("network", f"probe failed: {url}")
    argv, stdin = build(name, bin_, agent, prompt)
    try:
        r = subprocess.run(argv, input=stdin, capture_output=True, text=True, cwd=str(cwd),
                           env=child, timeout=agent.get("timeout", 300))
    except subprocess.TimeoutExpired:
        raise RunError("network", f"timeout after {agent.get('timeout')}s") from None
    except OSError as e:  # 如 prompt 作为 argv 超过 ARG_MAX（E2BIG）
        raise RunError("bad_output", f"spawn failed: {e}") from None
    if r.returncode != 0 and not r.stdout.strip():
        raise RunError(classify(r.stderr), r.stderr)
    return extract_json(unwrap(name, r.stdout))
