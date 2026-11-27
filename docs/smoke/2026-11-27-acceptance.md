# 一期验收记录（2026-11-27）

环境：macOS，agy 1.5.16，tclaude 0.1.10（@tencent/tclaude，配置目录 ~/.tclaude）。

| # | 验收项 | 命令 | 结果 |
| :-- | :-- | :-- | :-- |
| 1 | make 构建并可本地安装 | `make check`；`make install-agy`；`make install-claude` | ✅ 两端 plugin validate 通过；agy 显示 skills 12 · rules 1 · hooks 1；tclaude 显示 ai314@ai314 Version 0.1.0 |
| 2 | agy 安装后插件生效 | `tests/e2e/verify.sh agy 0.1.0` | ✅ VERSION=v0.1.0，SKILL=yes |
| 3 | 修改宪法并发布新版本，agy 加载新版 | 修改 §7 → `make release NEW=0.2.0` → `make install` → `tests/e2e/verify.sh agy 0.2.0 "超出上限时必须先拆分再继续添加功能"` | ✅ VERSION=v0.2.0，新句子可见 |
| 4 | tclaude 同流程 | `tests/e2e/verify.sh tclaude 0.1.0`；发布后 `tests/e2e/verify.sh tclaude 0.2.0 "…"` | ✅ 两个版本均通过，新句子可见 |
| 附 | AGY 命名空间调用 | `agy -p "/ai314:code-review …"` | ✅ LOADED=yes，正确复述技能内容 |

## 原始输出

### agy-v0.1.0

```
VERSION=v0.1.0
SKILL=yes
QUOTE=单文件不超过 300 行，单函数不超过 50 行，严禁跨层直接调用与循环依赖。
```

### tclaude-v0.1.0

```
VERSION=v0.1.0
SKILL=yes
QUOTE=**单文件不超过 300 行，单函数不超过 50 行，严禁跨层直接调用与循环依赖。**
```

### agy-v0.2.0

```
VERSION=v0.2.0
SKILL=yes
QUOTE=超出上限时必须先拆分再继续添加功能。
```

### tclaude-v0.2.0

```
VERSION=v0.2.0
SKILL=yes
QUOTE=超出上限时必须先拆分再继续添加功能。
```
