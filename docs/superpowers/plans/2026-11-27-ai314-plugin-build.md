# AI314 插件构建系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 AI314 重构为"内容 × 平台"正交的源码仓库，`make build` 生成 CC 与 AGY 插件，可本地安装、发布新版本并在 agy 与 tclaude 上验证生效。

**Architecture:** `content/` 存平台无关的 rule/skill；`build/ai314build` 读 `ai314.toml` 构建内存模型，调用 `platforms/<p>/adapter.py` 写出 `dist/<p>/`；Makefile 串联校验、测试、安装、发布；`tests/e2e/verify.sh` 以非交互模式向真实 Agent 提问做验收。

**Tech Stack:** Python 3.11+ 标准库（tomllib、unittest、json、shutil）、bash、make、git。

**Spec:** `docs/superpowers/specs/2026-11-26-ai314-plugin-design.md`

## Global Constraints

- 插件名 `ai314`；版本只存于 `ai314.toml`，semver。
- 构建器只用 Python 标准库，不引入第三方依赖。
- skill frontmatter `name` == 目录名；`L1-stacks` 前缀 `stack-`，`L2-modes` 前缀 `mode-`；L0/tools 无前缀约束。
- 宪法条款原文不改；构建时插入 `> AI314 宪法版本：v<version>`，并替换第四节索引表。
- CC 产物：`dist/claude/.claude-plugin/plugin.json`、`hooks/hooks.json`、`hooks/session-start`、`rules/AGENTS.md`、`skills/`；marketplace 在 `dist/.claude-plugin/marketplace.json`，插件 source `./claude`。
- AGY 产物：`dist/antigravity/.antigravity-plugin/plugin.json`、`rules/AGENTS.md`、`skills/`。
- `dist/` 加入 `.gitignore`，永不手改。
- CC 系客户端命令通过 `CLAUDE_BIN` 变量选择（默认 `tclaude`）；agy 命令需代理时由 `AGY_ENV` 注入。

## Review Focus

1. 重复执行 `make build`：必须先清空 `dist/<p>/`，不残留已删除的 skill。→ Task 2 测试 `test_rebuild_removes_stale_skill`。
2. skill 附属文件（`Makefile.tpl`、`preview_template.html`）必须原样复制。→ Task 2 测试 `test_skill_assets_copied`。
3. 宪法中含 `"`、`\`、换行、中文时 hook 输出仍是合法 JSON。→ Task 3 测试 `test_session_start_json_escaping`。
4. `make release` 版本不大于当前、或非 semver 时必须拒绝且不改文件。→ Task 5 测试 `test_release_rejects_non_increasing`。
5. `ai314-block.sh` 对已有块重复写入只替换块内、块外字节不变。→ Task 6 测试 `test_block_idempotent`。

---

### Task 1: 内容迁移与元数据

**Files:**
- Create: `ai314.toml`, `content/**`（由 `AGENTS.base.md`、`stacks/`、`modes/`、`scripts/extract-stack-skill.md` 迁移）, `content/L0-constitution/skills/{planning,code-review}/SKILL.md`, `content/tools/{onboard,contribute,extract-stack}/SKILL.md`, `.gitignore`
- Delete: `AGENTS.base.md`, `stacks/`, `modes/`, `scripts/init-project.sh`, `scripts/extract-stack-skill.md`, `.DS_Store`

**Interfaces:**
- Produces: `ai314.toml` 结构：`[plugin] name version description author repository`；`[rule] source`；`[[layers]] id skills_dir prefix`（prefix 可为空串）。

- [ ] Step 1: `git mv` 迁移现有文件到 `content/` 对应层；stack 正文顶部加 `> 状态：草案（抽象度待共建完善）`。
- [ ] Step 2: 宪法第四节标题下保留表头占位行 `<!-- AI314:SKILL-INDEX -->`；第零条后追加 D6 优先级与 D11 命名两句说明。
- [ ] Step 3: 编写 5 个新 skill（planning、code-review、onboard、contribute、extract-stack），description 按场景写。
- [ ] Step 4: `.gitignore` 加 `dist/`、`.DS_Store`、`__pycache__/`；Commit `refactor: move specs into layered content/`.

### Task 2: 构建器核心

**Files:**
- Create: `build/ai314build/__init__.py`, `model.py`, `build.py`, `validate.py`, `cli.py`
- Test: `tests/test_build.py`, `tests/test_validate.py`

**Interfaces:**
- Produces:
  - `model.load(root: Path) -> Project`；`Project(name, version, description, author, repository, rule_path: Path, skills: list[Skill])`；`Skill(name, description, layer_id, src_dir: Path)`
  - `build.render_rule(project) -> str`（插入版本行、替换索引占位符）
  - `build.build_all(project, out: Path, platforms: list[str]) -> None`，按名 import `platforms.<p>.adapter.write(project, rule_text, out_dir)`
  - `validate.validate(project) -> list[Issue]`；`Issue(level: 'error'|'warn', path, msg)`
  - `python3 -m ai314build {build,validate} [--root .] [--out dist]`（`PYTHONPATH=build:.`）

- [ ] Step 1: 写测试：`test_load_reads_version`、`test_render_rule_has_version_and_index`（含 `ai314:stack-go-microservice`）、`test_rebuild_removes_stale_skill`、`test_skill_assets_copied`、`test_validate_flags_bad_prefix`、`test_validate_flags_name_mismatch`、`test_validate_flags_secret`。用临时目录夹具。
- [ ] Step 2: 运行 `make test`，期望失败。
- [ ] Step 3: 实现；frontmatter 解析用简单的 `---` 块逐行 `key: value`。
- [ ] Step 4: `make test` 通过；Commit。

### Task 3: 平台适配器

**Files:**
- Create: `platforms/__init__.py`, `platforms/claude/{__init__.py,adapter.py,hooks/session-start}`, `platforms/antigravity/{__init__.py,adapter.py}`, `platforms/_common/auto-update`
- Test: `tests/test_adapters.py`

**Interfaces:**
- Consumes: `Project`, `render_rule` 结果
- Produces: `adapter.write(project, rule_text: str, out_dir: Path) -> None`；claude 适配器另写 `out_dir.parent/.claude-plugin/marketplace.json`。

- [ ] Step 1: 写测试：`test_claude_layout`（manifest 字段 name/version、hooks.json 指向 `${CLAUDE_PLUGIN_ROOT}/hooks/session-start`）、`test_agy_layout`、`test_session_start_json_escaping`（执行 hook 脚本，`CLAUDE_PLUGIN_ROOT` 指向产物，`json.loads` 成功且 additionalContext 含版本行）、`test_marketplace_points_to_claude`。
- [ ] Step 2: 运行失败；Step 3: 实现（session-start 用 python3 输出 JSON 以保证转义正确）；Step 4: 通过；Commit。

### Task 4: Makefile 与安装

**Files:** Create `Makefile`, `scripts/install-local.sh`

- [ ] Step 1: 目标：`build`、`validate`、`test`（`python3 -m unittest discover -s tests`）、`check`（validate+test+build+两端 `plugin validate`，CLI 缺失跳过）、`install-agy`（uninstall 忽略失败 + install `dist/antigravity`）、`install-claude`（`$(CLAUDE_BIN) plugin marketplace add dist` 已存在则 `marketplace update ai314`；`plugin install ai314@ai314` 已装则 `plugin update`）、`install`、`release`、`clean`。
- [ ] Step 2: `make check` 全绿；`make build` 产出两套目录。Commit。

### Task 5: 发布脚本

**Files:** Create `scripts/release.py`, `CHANGELOG.md`；Test `tests/test_release.py`

**Interfaces:** `release.bump(root: Path, version: str, note: str) -> None`；非法时 `raise SystemExit` 且不改文件。

- [ ] Step 1: 测试 `test_release_updates_toml_and_changelog`、`test_release_rejects_non_increasing`、`test_release_rejects_non_semver`。
- [ ] Step 2~4: 失败→实现→通过；`make release VERSION= NOTE=` 调用 bump 后 `make check` 并 `git commit` + `git tag`。Commit。

### Task 6: 声明块与回流脚本

**Files:** Create `scripts/ai314-block.sh`；Modify `scripts/sync-back.sh`（目标改 `content/L1-stacks|L2-modes`，支持 mode，整目录复制）；Test `tests/test_scripts.py`

- [ ] Step 1: 测试 `test_block_creates_agents_md`、`test_block_idempotent`、`test_block_adds_claude_import`、`test_sync_back_copies_stack_dir`。
- [ ] Step 2~4: 失败→实现→通过；Commit。

### Task 7: E2E 验收与文档

**Files:** Create `tests/e2e/verify.sh`, `docs/smoke/2026-11-27-acceptance.md`；Modify `README.md`, `AGENTS.md`（仓库开发约定）, `.github/workflows/{ci,release}.yml`

- [ ] Step 1: `verify.sh <agy|tclaude> <version>`：在临时目录以非交互模式提问"你的上下文中 AI314 宪法版本是多少？只回答版本号。另外列出可用的 ai314 技能名中是否包含 stack-go-microservice，回答 yes/no"，断言含 `v<version>` 与 `yes`。
- [ ] Step 2: 验收 1+2：`make build && make install-agy && tests/e2e/verify.sh agy 0.1.0`。
- [ ] Step 3: 验收 4（前半）：`make install-claude && tests/e2e/verify.sh tclaude 0.1.0`。
- [ ] Step 4: 验收 3：改宪法（例如第 7 条补一句）→ `make release VERSION=0.2.0` → `make install` → 两端 `verify.sh ... 0.2.0`。
- [ ] Step 5: 把各命令输出摘要记入 `docs/smoke/`；更新 README；Commit。
