"""new-stack 采样：按 extract-stack 的扫描顺序确定性抽取项目关键文件，替代给模型开放文件工具。"""
from __future__ import annotations

from pathlib import Path

DEPS = ("go.mod", "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "Package.swift",
        "Gemfile", "pom.xml", "build.gradle", "build.gradle.kts", ".env.example")
TOOLING = ("Makefile", ".golangci.yml", ".golangci.yaml", "eslint.config.js", "eslint.config.mjs", "ruff.toml",
           ".swiftlint.yml", "tsconfig.json", "Dockerfile")
SRC_EXT = {".go", ".py", ".ts", ".tsx", ".js", ".swift", ".rs", ".java", ".kt", ".rb"}
SKIP_DIRS = {"node_modules", "vendor", "dist", "build", "target", "Pods", "DerivedData", "__pycache__"}
PER_FILE, CORE_FILES = 8000, 4


def _skip(p: Path, root: Path) -> bool:
    return any(part.startswith(".") or part in SKIP_DIRS for part in p.relative_to(root).parts)


def _tree(root: Path, depth: int = 3) -> str:
    lines = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if len(rel.parts) > depth or _skip(p, root):
            continue
        lines.append("  " * (len(rel.parts) - 1) + rel.name + ("/" if p.is_dir() else ""))
    return "\n".join(lines[:400])


def _core(root: Path) -> list[Path]:
    srcs = [p for p in root.rglob("*") if p.is_file() and p.suffix in SRC_EXT and not _skip(p, root)
            and "test" not in p.name.lower()]
    srcs.sort(key=lambda p: p.stat().st_size)
    mid = len(srcs) // 2
    return srcs[max(mid - CORE_FILES // 2, 0):mid + CORE_FILES // 2 + CORE_FILES % 2]


def _section(title: str, body: str) -> str:
    return f"\n===== {title} =====\n{body}\n"


def sample(root: Path, limit: int = 60_000) -> str:
    root = Path(root)
    parts = [_section(n, (root / n).read_text(encoding="utf-8", errors="replace")[:PER_FILE])
             for n in DEPS if (root / n).is_file()]
    parts.append(_section("目录树（3 层）", _tree(root)))
    parts += [_section(n, (root / n).read_text(encoding="utf-8", errors="replace")[:PER_FILE])
              for n in TOOLING if (root / n).is_file()]
    parts += [_section(str(p.relative_to(root)), p.read_text(encoding="utf-8", errors="replace")[:PER_FILE])
              for p in _core(root)]
    out = ""
    for s in parts:
        if len(out) + len(s) > limit:
            out += s[:max(limit - len(out), 0)]
            break
        out += s
    return out
