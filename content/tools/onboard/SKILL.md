---
name: onboard
description: 当需要把一个项目接入 AI314 规范、为项目选择或调整启用的 stack/mode、体检项目已有的 AGENTS.md/CLAUDE.md，或清理旧版 init-project.sh 留下的规范副本时使用。
---

# AI314 项目接入

原则：**绝不覆盖**项目已有规则；所有删除/改写先列表、经用户逐条确认后再执行。项目中只保留一个声明块，不拷贝任何 L0/L1 正文。

## 1. 体检

1. 检查项目根的 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`.agents/skills/`、`.claude/skills/`。
2. 识别旧版痕迹：含"VibeCoding 工程协作宪法"全文的 AGENTS.md、`.agents/skills/stack-*` 或 `mode-*` 副本、`.claude/skills -> ../.agents/skills` 软链。
   - 副本与插件当前版本有差异：先提示用户用 `ai314:contribute` 回流，再建议删除。
3. 对已有规则文件逐条分类，用表格给用户确认：

| 原文条目 | 分类 | 建议 |
| :-- | :-- | :-- |
| … | 与宪法重复 | 删除 |
| … | 项目特有 | 保留 |
| … | 可复用的技术栈经验 | 上收到 L1（走 contribute）后删除 |

## 2. 选择技能

按项目目录结构推荐"路径范围 → 技能"映射（大仓按子目录，单栈项目用 `*`），可用技能见宪法第四节索引表，经用户确认。

## 3. 写入声明块

用插件内脚本幂等写入（块外内容不变；存在 CLAUDE.md 时自动确保其含 `@AGENTS.md`）：

```sh
printf '%s\n' '| `services/**` | ai314:stack-go-microservice |' | bash "<插件目录>/scripts/ai314-block.sh" <项目根>
```

`<插件目录>` 为本技能所在插件的根目录（本文件上两级）。

## 4. 项目骨架（仅缺失时创建）

- `docs/{00-plans,01-biz,02-prod,03-ui-design,04-arch,05-deploy,_drafts}`
- `.gitignore` 追加 `.env`、`.env.*`
