"""内容模型：把 ai314.toml + content/ 解析为平台无关的 Project。"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Layer:
    id: str
    skills_dir: Path
    prefix: str


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    layer_id: str
    src_dir: Path
    dir_name: str


@dataclass
class Project:
    root: Path
    name: str
    version: str
    description: str
    author: str
    repository: str
    rule_path: Path
    layers: list[Layer] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)


def parse_frontmatter(text: str) -> dict[str, str]:
    """解析 SKILL.md 顶部 `---` 块中的单行 `key: value`；无 frontmatter 返回空字典。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.startswith((" ", "\t")):
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return {}  # 未闭合视为无 frontmatter


def load(root: Path) -> Project:
    root = Path(root).resolve()
    cfg = tomllib.loads((root / "ai314.toml").read_text(encoding="utf-8"))
    plugin = cfg["plugin"]
    proj = Project(
        root=root,
        name=plugin["name"],
        version=str(plugin["version"]),
        description=plugin.get("description", ""),
        author=plugin.get("author", ""),
        repository=plugin.get("repository", ""),
        rule_path=root / cfg["rule"]["source"],
    )
    for raw in cfg.get("layers", []):
        layer = Layer(raw["id"], root / raw["skills_dir"], raw.get("prefix", ""))
        proj.layers.append(layer)
        if not layer.skills_dir.is_dir():
            continue
        for skill_md in sorted(layer.skills_dir.glob("*/SKILL.md")):
            meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            proj.skills.append(
                Skill(
                    name=meta.get("name", ""),
                    description=meta.get("description", ""),
                    layer_id=layer.id,
                    src_dir=skill_md.parent,
                    dir_name=skill_md.parent.name,
                )
            )
    return proj
