# Lessons Loop 端到端验收记录

日期：2026-11-27　分支：`feat/lessons-loop`　环境：macOS，agy（`~/.local/bin/agy`）+ 代理 `http://127.0.0.1:8118` + `gemini-4-hydrogen-medium`

## 1. 构建与安装

- 执行 `make check` 全绿（99 个单元测试，`tclaude`/`agy plugin validate --strict` 均通过）。
- 执行 `make install-agy` 后，安装目录 `~/.gemini/config/plugins/ai314/hooks/` 与 `dist/antigravity/hooks` 内容一致。`hooks.json` 中已注册 `SessionStart` 和 `Stop` 两个事件。
- `~/.ai314/config.toml` 写入了测试环境配置。
- `ai314-lessons doctor` 显示 `network: ok`、`runner: ok`。运行前已 unset shell 中的代理变量，结果说明 `[network]` 的注入是生效的。

## 2. 真机捕获（agy 3 轮会话，临时 git 项目）

| 轮次 | 用户输入 | 写入 inbox 的信号 |
| :-- | :-- | :-- |
| 1 | 创建故意写错的 `add` 及测试，运行后询问"是否需要我修复？" | 无（首条消息不算纠正；测试失败暂存在会话状态里） |
| 2 | "不对，你不应该等我确认……修好后重跑，询问是否更新 README" | `correction`（`prev` 为上一轮 AI 回复和测试输出）、`test_flip`（`python3 -m unittest -q`） |
| 3 | "ok" | `ok`（`prev` 为"是否需要我同步更新 README？"） |

- 在 agy 的 `-p` 模式下，Stop hook 同样会触发。`.ai314/` 目录自带内容为 `*` 的 `.gitignore`。
- **本轮发现并修复的问题**：第一次跑时，纠正信号的 `prev` 是空的，OK 信号也丢了。原因是 Stop hook 每次只增量读取新内容，上一轮 AI 的回复没有持久化。已补上按轮切分的回归测试（`test_state_carries_across_turns`），修复后重跑真机，结果符合预期。

## 3. 模拟提炼、聚合、回流（隔离环境）

- 测试环境：使用独立的 `AI314_HOME` 并设 `contribute = true`；`src` 是本仓库的临时 clone，origin 指向本地 bare 仓库；`gh` 换成桩，因此**没有向 GitHub 发出任何真实 PR**。提炼和回流时的模型调用走真实的 agy + Hydrogen。
- 注入信号：在两个测试项目中各注入 16 条反面信号和 3 条 OK 信号，`session` 标记为 `sim-test`。之后从 hook 入口 `capture --foreground` 触发。
- 项目 1：提炼 22 条信号，得到 6 条反面经验（4 条 stack-go-microservice、2 条 L0）和 2 条 OK 统计，inbox 清空。回流被触发后，模型判断三个 owner 均"无成熟条目"，因为证据只来自 1 个项目。这符合成熟度规则。
- 项目 2：删除 `contrib.json` 以模拟 24h 间隔已过，再次触发。提炼得到 5 条全局经验，L0、ok-defaults、stack-go-microservice 三个 owner 都被判定为成熟，各自完成了 worktree、`make check`、push、`gh pr create`。L0 按规则开成 `--draft`。用户的 `src` 仍停在 `main`，worktree 已清理。
- 产物质量：stack 侧的 diff 是在原有条款里做最小融合（+4/−4）；planning 技能新建了「默认不再询问的决策」小节；PR 正文只出现匿名项目 id。
- **本轮发现并修复的问题**：PR 标题出现重复的 Conventional 前缀；新条目的计数总是 1。两处都已先写失败测试再修复。

## 4. 清理

已删除模拟沙盘 `/tmp/ai314-sim`（包括全局库、桩 gh、bare 仓库）以及两个测试项目（连同其中的 inbox、lessons、注入的信号）。真实的 `~/.ai314/` 下只保留 `config.toml`。验收过程中 agy 自身的会话记录（位于 `~/.gemini/antigravity-cli/brain/`）未做处理。
