# Changelog

## v0.4.0 - 2026-11-27

- 新增经验自动回流闭环（lessons loop）：Stop hook 0 token 捕获纠正/返工/测试先挂后过/命令连续失败/OK 信号，按阈值无头提炼为项目 docs/ai314/lessons.md 并汇总全局库，可选自动向 upstream 提 PR；Agent/模型/代理统一配置于 ~/.ai314/config.toml

## v0.3.0 - 2026-11-27

- 宪法精简为 14 条并对齐原稿意图；文档即契约改为 superpowers spec + docs/base 活文档；新增 ai314:docs-base-sync；planning/code-review/onboard 同步调整

## v0.2.0 - 2026-11-27

- 宪法第 7 条：超出复杂度上限时必须先拆分再继续添加功能

## v0.1.0 - 2026-11-27

- 首个插件化版本：内容 × 平台正交构建，支持 Claude Code 与 Antigravity。
