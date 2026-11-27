---
name: contribute
description: 当在项目开发中发现 AI314 的 stack/mode/宪法规范有缺口或错误，需要把改进回流到 AI314 中央仓库并提交 Pull Request 时使用。
---

# 回流到 AI314

业务仓中**不保存**规范草稿副本，直接在本机 AI314 源码仓库修改。

1. 源码仓库位置：`$AI314_SRC`，默认 `~/.ai314-src`。不存在时征得用户同意后执行 `gh repo clone lupguo/AI314 ~/.ai314-src`。
2. 确认工作区干净，`git switch main && git pull --ff-only`，新建分支 `contrib/<项目名>-<技能名>-<YYYYMMDD>`。
3. 修改 `content/` 下对应目录（L1 在 `content/L1-stacks/stack-*/`，L2 在 `content/L2-modes/mode-*/`，宪法在 `content/L0-constitution/AGENTS.base.md`）：
   - 去业务化：不得出现具体业务名词。
   - 只写可核查的硬约束。
4. 运行 `make check`，必须全绿。
5. 提交（Conventional Commits，如 `feat(stack-go-microservice): ...`），`git push -u origin HEAD`，`gh pr create`，正文写明来源项目、改动理由与证据。
6. 切回 `main`。PR 由维护者 review 合并后自动发版。

旧版 init-project.sh 装配过的项目中被改过的 `.agents/skills/stack-*` 副本，可用 `scripts/sync-back.sh <副本目录>` 质检后拷入源码仓库分支。
