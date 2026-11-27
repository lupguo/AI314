# AI314 插件化设计（一期）

> 状态：v3（2026-11-27），用户已确认方向，进入实施
> 历史：v1 平铺插件 → v2 仓库根即插件 → v3 内容 × 平台正交 + 构建生成

## 1. 意图

AI314 是一套**独立的** AI VibeCoding 工程规范：L0 通用宪法 + L1 技术栈蓝图 + L2 研发模式（后续可扩 L3 部署等）。目标是让业务项目"零帧起手"，降低 Agent 带来的项目熵增。

旧方式（`init-project.sh` 拷贝到业务仓）的问题：覆盖已有 `AGENTS.md`、重复执行不幂等、无版本、无升级路径、每个项目一份旧副本。

新方式：**规范内容平台无关地维护一份，`make build` 按平台生成插件产物，CC 与 AGY 以插件安装，业务项目只保留一个声明块。**

用户日常使用 Claude Code（含本地发行版 tclaude，配置目录 `~/.tclaude`）与 Google Antigravity CLI（`agy` 1.5.16）。

## 2. 目标 / 非目标 / 反目标

**目标（一期）**

1. 内容（L0/L1/L2/工具）与平台适配正交：新增内容只改 `content/`，新增平台只加一个适配器。
2. `make build` 生成 `dist/claude/`、`dist/antigravity/` 两个可本地安装的插件。
3. L0 宪法整份常驻生效；L1/L2/工具以 skill 按场景加载；技能统一命名空间 `ai314:<name>`。
4. 版本发布：修改内容 → `make release` 递增版本 → 重新构建/安装 → 两端加载新版本。
5. 已有 `AGENTS.md`/`CLAUDE.md` 的项目可安全接入（onboard：不覆盖、逐条体检、用户确认）。
6. 回流工具（contribute / sync-back）与远程分发（dist 分支 + 自动更新器）一期提供实现与单测，真实远程链路不在一期验收内。

**非目标**：不新增 README 中尚不存在的 stack；不重写现有 stack 技术内容（标注"草案"）；不做脚手架代码生成；一期不实现 `mcp`/`hook` 通用内容类型与 L3（只留扩展点）；不支持 CC/AGY 以外的 Agent。

**反目标**：依赖 superpowers 才能工作；业务项目出现 L0/L1 正文副本；未经用户确认改写业务项目已有规则文件；手改 `dist/`。

## 3. 关键决策

| # | 决策 | 来源 |
|---|---|---|
| D1 | AI314 独立于 superpowers；共存时只叠加约束，不重复造流程 | 用户 |
| D2 | L0 宪法以 `AGENTS.base.md` 整份**常驻**（不拆成 skill）；`planning`/`code-review` skill 只写"怎么做"，引用宪法条款编号 | 用户确认（v3 修订） |
| D3 | CC + AGY 插件分发 | 用户 |
| D6 | 项目声明块启用的 mode，其豁免优先于宪法条款，**安全底线（第 15 条）除外** | 用户 |
| D7 | 两个 Go 项目共建 L1：一期只交付工具 | 用户 |
| D8 | 内容 × 平台正交，`make build` 生成产物到 `dist/`；产物不入 main | 用户 |
| D9 | 更新全自动：两端 SessionStart 调用同一个后台更新器（远程场景） | 用户 |
| D10 | 回流走 PR，合并前用户 review | 用户 |
| D11 | 技能只写裸名，命名空间由平台按插件名 `ai314` 自动加，两端均为 `ai314:<name>`（AGY 行为经本机历史 `/superpowers:brainstorming` 验证，官方文档未写明） | 用户 + 实测 |
| D12 | 一期只实现 `rule`、`skill` 两种内容类型；`mcp`、`hook`、L3 留扩展点 | 用户 |

## 4. 项目布局

```
AI314/
├── ai314.toml                 # 唯一元数据源：插件名/版本/描述/作者/仓库 + 层定义
├── Makefile                   # build / check / test / install-* / release / clean
├── content/                   # ① 内容层（平台无关）
│   ├── L0-constitution/
│   │   ├── AGENTS.base.md     #   宪法全文（type: rule）
│   │   └── skills/{planning,code-review}/SKILL.md
│   ├── L1-stacks/stack-*/     #   SKILL.md + 附属文件
│   ├── L2-modes/mode-*/
│   └── tools/{onboard,contribute,extract-stack}/
├── platforms/                 # ② 适配层：每平台一个包，同一接口
│   ├── claude/{adapter.py,hooks/}
│   ├── antigravity/{adapter.py,hooks/}
│   └── _common/               #   共享：auto-update 脚本
├── build/ai314build/          # ③ 构建器（Python 3.11+ 标准库）
├── dist/                      # ④ 产物（gitignore）
│   ├── .claude-plugin/marketplace.json  → ./claude
│   ├── claude/
│   └── antigravity/
├── scripts/                   # install.sh / sync-back.sh / ai314-block.sh / release.py
├── tests/                     # python unittest + e2e 验收脚本
├── .github/workflows/         # ci.yml / release.yml（推 dist 分支）
└── README.md / CHANGELOG.md / AGENTS.md（本仓库开发约定）
```

### 4.1 层与内容类型

`ai314.toml` 声明层，构建器按声明遍历，不写死层名：

```toml
[[layers]]
id = "L1-stacks"
skills_dir = "content/L1-stacks"
prefix = "stack-"
```

L0 在 `[rule]` 中声明 `source = "content/L0-constitution/AGENTS.base.md"`。新增 L3 = 加目录 + 加一条 `[[layers]]`。

| 类型 | 源 | CC 产物 | AGY 产物 |
|---|---|---|---|
| rule | `AGENTS.base.md` | `rules/AGENTS.md`，由 `hooks/session-start` 读入并以 `hookSpecificOutput.additionalContext` 注入 | `rules/AGENTS.md`（AGY 约定的插件常驻规则文件名） |
| skill | `<layer>/<name>/SKILL.md` + 附属文件 | `skills/<name>/` | `skills/<name>/` |

构建时对 rule：在标题下插入版本标记行 `> AI314 宪法版本：v<version>`；把末尾《已挂载技能索引表》替换为由全部 skill 的 name/description 自动生成的表（技能写作 `ai314:<name>`）。

扩展点（D12，二期）：`mcp`（`mcp/*.toml` → CC `.mcp.json` / AGY `mcp_config.json`）、`hook`（抽象事件 + 共享 shim 做输入输出转换）；适配器声明能力矩阵，不支持的类型构建期告警，`required` 则失败。

### 4.2 平台事实（2026-11 核实）

| | CC / tclaude | AGY 1.5.16 |
|---|---|---|
| manifest | `.claude-plugin/plugin.json` | `.antigravity-plugin/plugin.json` |
| 常驻 | SessionStart hook `additionalContext` | 插件 `rules/AGENTS.md` |
| hooks 文件 | `hooks/hooks.json` | 插件根 `hooks.json`，按插件名分组 |
| 本地安装 | `plugin marketplace add <dist>` + `plugin install ai314@ai314`；目录型 marketplace 的相对路径插件原地加载，重建后下次会话生效 | `agy plugin install <dir>`（复制到 `~/.gemini/config/plugins/ai314`）；无 update 命令，更新 = uninstall + install |
| 校验 | `plugin validate <dir>` | `agy plugin validate --strict <dir>` |
| 非交互 | `-p` | `-p` |

## 5. L0 与 skill

- `AGENTS.base.md` 全文常驻，条款内容不改；第四节索引表改为构建生成。新增一行优先级说明落实 D6，一行命名说明落实 D11。
- `planning`：在产出 SPEC/PLAN 时，把相关宪法条款（按编号）与已启用的 stack/mode 约束写进计划文档每个任务的"约束"与"自检命令"小节。已有其他流程技能在驱动时沿用其流程，只叠加本清单。
- `code-review`：按宪法条款检查清单审查，输出按严重度排序的问题表。
- skill frontmatter `name` 等于目录名；L1 必须 `stack-` 前缀，L2 必须 `mode-` 前缀；`description` 按任务场景写。

## 6. 项目声明块

```markdown
<!-- AI314:BEGIN v=1 -->
## AI314 工程规范
本项目遵循 AI314 规范（插件 ai314）。按路径加载对应技能：

| 路径范围 | 技能 |
| :-- | :-- |
| `services/**` | ai314:stack-go-microservice |
<!-- AI314:END -->
```

- 放仓库根 `AGENTS.md`；存在 `CLAUDE.md` 时确保其含 `@AGENTS.md`。大仓也只放根目录（AGY 不读子目录规则）。
- `v=` 是声明块格式版本。`scripts/ai314-block.sh` 幂等写入/替换 BEGIN~END 之间内容，块外一字不动。

## 7. 工具 skill

| 技能 | 职责 |
|---|---|
| onboard | 识别旧版 init-project.sh 痕迹与已有规则文件 → 体检表（重复→建议删 / 特有→留 / 可复用→建议上收）→ 用户逐条确认 → 调 `ai314-block.sh` 写声明块；创建 `docs/` 标准目录、`.gitignore` 补 `.env*` |
| extract-stack | 从当前项目逆向提炼 L1 草稿 |
| contribute | 在本机 AI314 源码 clone（`~/.ai314-src`）开分支 → 改 `content/` → `make check` → `gh pr create`；旧版副本迁移调用 `scripts/sync-back.sh` |

## 8. 版本、发布与更新

- 版本只写在 `ai314.toml`，构建时注入两端 manifest 与宪法版本标记。
- `make release VERSION=x.y.z`：校验 semver 且大于当前 → 改 `ai314.toml` → `CHANGELOG.md` 顶部插入条目 → `make check` → git commit `chore(release): vX.Y.Z` + tag。
- 本地更新：`make install`（重建 + CC 原地生效 + AGY 卸载重装）。
- 远程（一期实现、不验收）：`release.yml` 在 tag 推送后构建并推 `dist` 分支；用户机器 `~/.ai314` 为 dist 分支 clone；两端 SessionStart 调 `platforms/_common/auto-update`：6 小时节流、detach 后台、仅当在 dist 分支且工作区干净时 `git pull --ff-only`，AGY 额外重装，日志写 `~/.ai314/.update.log`，任何失败不影响会话。本地开发安装（`~/.ai314` 不存在）时更新器直接退出。

## 9. 质量门禁与验收

`make check` = 内容校验（frontmatter、前缀、`stack-*` 四章节、行数告警、敏感信息扫描、版本 semver）+ 构建 + 产物校验（两端 `plugin validate`，CLI 不存在则跳过）+ 单测。

**一期验收（用户给定）**

1. `make build` 生成插件，可本地安装。
2. AGY 安装插件，测试用例可见插件生效。
3. 修改宪法并发布新版本，AGY 重新安装后加载到新版本。
4. 同样流程在 tclaude 上通过。

验收脚本：`tests/e2e/verify.sh <agy|tclaude> <expected-version>`，非交互询问"AI314 宪法版本"，断言输出含期望版本，并询问技能 `ai314:stack-go-microservice` 是否可用。
