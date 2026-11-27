# AI314

AI314 = AI31415926…：一套沉淀 AI VibeCoding 工程实践的方法论与规范库，用来降低 Agent 开发过程中的项目熵增，让新项目"零帧起手"。

规范以**插件**形式分发到 Claude Code（含 tclaude）与 Google Antigravity（agy）：全系统一份规范，插件升级即全量生效，业务项目里不再拷贝规范正文。

## 三层规范

| 层 | 目录 | 加载方式 | 内容 |
| :-- | :-- | :-- | :-- |
| L0 宪法 | `content/L0-constitution/` | `AGENTS.base.md` 每次会话常驻；`planning`、`code-review` 按场景加载 | 阶段门禁、最小变更、TDD 纠偏、安全红线等 15 条 |
| L1 技术栈 | `content/L1-stacks/stack-*` | 按场景或项目声明块加载 | go-microservice、web-admin、ios-app、macos-menubar、crawler-script（均为草案） |
| L2 研发模式 | `content/L2-modes/mode-*` | 项目声明块启用 | exploration-mvp、legacy-maintenance |
| 工具 | `content/tools/` | 按需调用 | onboard（项目接入）、contribute（回流）、extract-stack（逆向提炼） |

技能统一命名为 `ai314:<技能名>`，两端写法相同，如 `/ai314:stack-go-microservice`。

规划中的 stack：go-web、go-agent-core、python-fastapi、wails-go、shell。

## 仓库结构

```
ai314.toml        # 插件元数据、版本、层定义（唯一版本来源）
content/          # ① 规范内容，平台无关
platforms/        # ② 平台适配器：claude / antigravity / _common
build/ai314build/ # ③ 构建器（Python 3.11+ 标准库）
dist/             # ④ 构建产物（gitignore，勿手改）
scripts/          # release.py、sync-back.sh
tests/            # 单测 + e2e 验收
```

新增一层（如 L3 部署）只需新增 `content/L3-deploy/` 并在 `ai314.toml` 加一条 `[[layers]]`；新增平台只需新增 `platforms/<平台>/adapter.py`。

## 使用

```sh
make check                    # 校验内容 + 单测 + 构建 + 两端 plugin validate
make install                  # 构建并安装到 tclaude 与 agy（新会话生效）
make install-claude CLAUDE_BIN=claude   # 安装到官方 Claude Code
make install-agy AGY_ENV="https_proxy=http://127.0.0.1:8118"
make uninstall
```

在业务项目中接入：打开 Agent 执行 `/ai314:onboard`，它会体检已有的 `AGENTS.md`/`CLAUDE.md`，经你确认后写入一个声明块（路径 → 技能），不会覆盖已有内容。

## 发布新版本

```sh
# 1. 修改 content/ 并提交
git commit -am "feat(constitution): ..."
# 2. 发布：改 ai314.toml 版本 + CHANGELOG → make check → commit + tag
make release NEW=0.3.0 NOTE="变更说明"
# 3. 本机两端加载新版本
make install
# 4. 验证
tests/e2e/verify.sh agy 0.3.0
tests/e2e/verify.sh tclaude 0.3.0
```

远程分发（推送 tag 后 CI 构建并推送 `dist` 分支；其他机器将 `dist` 分支 clone 到 `~/.ai314`，两端 SessionStart hook 每 6 小时在后台自动拉取并重装）已实现，详见设计文档。

## 回流改进

在业务项目中发现规范缺口时执行 `/ai314:contribute`：在 `~/.ai314-src` 开分支修改 `content/`，`make check` 后 `gh pr create`，review 合并后发布。

## 文档

- 设计：`docs/superpowers/specs/2026-11-26-ai314-plugin-design.md`
- 计划：`docs/superpowers/plans/2026-11-27-ai314-plugin-build.md`
- 验收记录：`docs/smoke/2026-11-27-acceptance.md`

## 参考资料

软件工程；DDD 领域驱动设计、Clean 架构；极客时间《架构设计原则》；superpowers 插件；pstack SKILL。
