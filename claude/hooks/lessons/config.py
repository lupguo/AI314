"""统一配置 ~/.ai314/config.toml：缺省值 + 文件 + 环境变量覆盖；未知键告警忽略（防止误放凭据）。"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field

from . import paths

LESSONS = {"mode": "on", "contribute": False, "upstream": "lupguo/AI314", "src": "~/.ai314-src",
           "distill_min": 15, "contrib_min": 3}
AGENT = {"runner": "auto", "bin": "", "model": "", "extra_args": [], "timeout": 300}
STAGE_DEFAULTS = {"contribute": {"timeout": 900}}
NETWORK = {"https_proxy": "", "http_proxy": "", "all_proxy": "", "no_proxy": "", "probe_url": ""}
STAGES = ("distill", "contribute")


@dataclass
class Config:
    lessons: dict
    agent: dict
    agent_stages: dict
    network: dict
    warnings: list = field(default_factory=list)

    def agent_for(self, stage: str) -> dict:
        merged = dict(self.agent)
        merged.update(self.agent_stages.get(stage, {}))
        return merged


def _pick(section: dict, defaults: dict, name: str, warnings: list) -> dict:
    out = dict(defaults)
    for k, v in section.items():
        if k in defaults:
            out[k] = v
        elif not isinstance(v, dict):
            warnings.append(f"config.toml: 忽略未知键 [{name}].{k}")
    return out


def _read(env) -> tuple[dict, list]:
    p = paths.home(env) / "config.toml"
    if not p.is_file():
        return {}, []
    try:
        return tomllib.loads(p.read_text(encoding="utf-8")), []
    except tomllib.TOMLDecodeError as e:
        return {}, [f"config.toml 解析失败，使用默认值: {e}"]


def _expand(p: str, env) -> str:
    if p.startswith("~"):
        return env.get("HOME", os.path.expanduser("~")) + p[1:]
    return p


def load(env=os.environ) -> Config:
    raw, warnings = _read(env)
    lessons = _pick(raw.get("lessons", {}), LESSONS, "lessons", warnings)
    agent_raw = raw.get("agent", {})
    agent = _pick(agent_raw, AGENT, "agent", warnings)
    stages = {}
    for st in STAGES:
        merged = dict(STAGE_DEFAULTS.get(st, {}))
        picked = _pick(agent_raw.get(st, {}), {k: None for k in AGENT}, f"agent.{st}", warnings)
        merged.update({k: v for k, v in picked.items() if v is not None})
        stages[st] = merged
    network = _pick(raw.get("network", {}), NETWORK, "network", warnings)
    lessons["src"] = _expand(lessons["src"], env)
    if env.get("AI314_LESSONS"):
        lessons["mode"] = env["AI314_LESSONS"]
    if env.get("AI314_CONTRIBUTE"):
        lessons["contribute"] = env["AI314_CONTRIBUTE"].lower() in ("on", "1", "true", "yes")
    return Config(lessons, agent, stages, network, warnings)
