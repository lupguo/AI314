# L0 宪法精简 + docs/base 活文档 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按设计稿重写 L0 宪法为 14 条、调整 planning / code-review / onboard / mode-exploration-mvp，新增 `ai314:docs-base-sync`，并在 agy 与 tclaude 两端验收生效。

**Architecture:** 纯 `content/` 内容改动，构建器与适配器不变；宪法由构建器注入版本行与技能索引，通过 SessionStart hook / rules 常驻加载。

**Tech Stack:** Markdown 技能文件；Python 3.11 标准库构建器；`make check` / `make install`；`tests/e2e/verify.sh`。

**Spec:** `docs/superpowers/specs/2026-11-27-constitution-docs-base-design.md`

## Global Constraints

- 只改 `content/`、`tests/e2e/verify.sh`、`README.md`；`dist/` 禁止手改。
- 技能 frontmatter `name` 等于目录名；新技能目录 `content/tools/docs-base-sync/`。
- 宪法条款数量、编号、含义以 spec 第 4 节为准；保留 `<!-- AI314:SKILL-INDEX -->` 占位符。
- 每次提交前 `make check` 全绿；Conventional Commits；提交尾注 `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`。
- `content/L1-stacks/stack-go-microservice/SKILL.md` 的未提交空行改动不纳入任何提交。
- 版本号不变（v0.2.0），不执行 `make release`。

## Review Focus

- 旧条款号残留：任何 `content/` 文件仍引用旧编号（如"宪法第 14 条"指自检）或 `docs/00-plans/` → 用 `grep -rn "00-plans\|01-biz\|05-deploy" content/` 应无输出。
- 新宪法第 3 条末句必须可被 e2e 原样引用：`超限时先拆分再继续加功能。`
- 构建产物 `dist/*/rules/AGENTS.md` 末尾技能索引含 `ai314:docs-base-sync`。
- `.gitignore` 建议项在 onboard 中只在缺失时追加，不重复。
- README 中技能数量/条款数描述与实际一致（14 条，tools 含 docs-base-sync）。

---

### Task 1: 分支与 spec 提交

- [ ] 从 main 建分支 `feat/constitution-docs-base`。
- [ ] 提交 spec 与本 plan：`docs(specs): constitution slim-down and docs/base design`。

### Task 2: 宪法重写 + e2e 引用

**Files:** Modify `content/L0-constitution/AGENTS.base.md`（全文替换为 spec §4 代码块内容）、`tests/e2e/verify.sh:15`。

- [ ] 将 verify.sh 的 QUOTE 提问改为 `宪法第 3 条（架构设计）的最后一句话，原样`。
- [ ] 替换宪法全文。
- [ ] `make check` → 末行 `✅ check 通过 (v0.2.0)`；`grep -c "超限时先拆分再继续加功能" dist/claude/rules/AGENTS.md` → `1`。
- [ ] 提交 `feat(constitution)!: slim to 14 clauses aligned with original intent`。

### Task 3: planning 与 code-review

**Files:** Modify `content/L0-constitution/skills/planning/SKILL.md`、`content/L0-constitution/skills/code-review/SKILL.md`，内容按 spec §5.1、§5.2 与 §7。

- [ ] planning：删 00-plans 与门禁节；新增"公开接口变更清单""docs/base 影响清单"；`自检命令` 不挂条款号；条款号全部改为新编号。
- [ ] code-review：检查表按新编号重排；第 3 条给 `wc -l` 测量；第 4 条依据 `docs/base/API.md`；第 8 条回写检查；legacy 特征测试；严重度定义。
- [ ] `make check` 全绿；提交 `feat(constitution): align planning and code-review with new clauses`。

### Task 4: docs-base-sync 新技能 + 引用修正

**Files:** Create `content/tools/docs-base-sync/SKILL.md`；Modify `content/tools/onboard/SKILL.md`、`content/L2-modes/mode-exploration-mvp/SKILL.md`、`README.md`。

- [ ] 新技能按 spec §5.3（模式 A 存量盘点、模式 B 特性回写、五个文件建议大纲、与 extract-stack 区别）；单文件 ≤300 行。
- [ ] onboard 按 spec §5.4；mvp 转正结论改为输出 spec；README 改"14 条"并在工具列表加入 docs-base-sync。
- [ ] `grep -rn "00-plans\|01-biz\|05-deploy" content/` 无输出；`make check` 显示技能数 13；`grep -c "ai314:docs-base-sync" dist/claude/rules/AGENTS.md` ≥1。
- [ ] 提交 `feat(tools): add docs-base-sync and drop docs/0x layout`。

### Task 5: 审查、合并、推送

- [ ] 用 `ai314:code-review` 清单自审分支 diff，修正发现项。
- [ ] 合并到 main（fast-forward），`git push origin main`。

### Task 6: 本地安装与两端验收

- [ ] `make install`（agy 需代理时加 `AGY_ENV`）→ 两端均输出 `✅ … 已安装 ai314 v0.2.0`。
- [ ] `tests/e2e/verify.sh agy 0.2.0 "超限时先拆分再继续加功能"` → 三项 ✅。
- [ ] `tests/e2e/verify.sh tclaude 0.2.0 "超限时先拆分再继续加功能"` → 三项 ✅。
- [ ] 若需要，将验收结果追加到 `docs/smoke/`，提交并推送。
