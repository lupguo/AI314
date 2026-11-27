# AI314 仓库开发约定

本文件约束的是 **AI314 仓库自身** 的开发，不是分发给业务项目的宪法（宪法在 `content/L0-constitution/AGENTS.base.md`）。

- 规范内容只改 `content/`；平台差异只写在 `platforms/<平台>/adapter.py`；`dist/` 是产物，禁止手改。
- 构建器只用 Python 标准库（3.11+），不引入第三方依赖。
- 技能 frontmatter `name` 必须等于目录名；L1 以 `stack-` 开头且含 `## 1.`~`## 4.` 四章；L2 以 `mode-` 开头。
- 版本号只在 `ai314.toml`，通过 `make release NEW=x.y.z NOTE=...` 修改。
- 提交前必须 `make check` 全绿；改构建器/适配器/脚本先写失败测试（`tests/`）。
- 提交信息使用 Conventional Commits。
