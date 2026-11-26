# AI314 插件化设计（一期）

> 状态：草案，待用户确认
> 日期：2026-11-26

## 1. 意图与背景

AI314 是一套**独立的** AI VibeCoding 工程规范（L0 通用宪法 + L1 技术栈蓝图 + L2 研发模式），目标是让业务项目"零帧起手"、降低 Agent 带来的项目熵增。

现状问题（2026-11-26 盘点）：

- 引入方式是 `scripts/init-project.sh` 拷贝文件到业务仓：会**直接覆盖**目标项目已有的 `AGENTS.md`；重复执行会重复追加路由表行；不记录版本，**没有升级路径**；强制 `--stacks`，无法只装 L0。
- 拷贝式分发导致每个项目一份旧副本，L0/L1 更新后无法同步。
- `sync-back.sh` 只能回流 `stack-*`，且与 modes 的章节结构不兼容。
- README 描述与仓库不一致（`scaffold/`、`design-tokens.md` 不存在；"Scenario Packs" 与 `modes/` 命名不一致；README 列出的 go-web / go-agent-core / Python FastAPI / Wails 等 stack 不存在）。

用户日常使用 **Claude Code（CC）** 与 **Google Antigravity CLI（AGY）**。

## 2. 目标 / 非目标 / 反目标

**目标**

1. AI314 仓库本身即为一个**同时支持 CC 与 AGY 的插件**，一次安装、全系统统一一份，插件升级即全量生效，业务项目不再拷贝规范正文。
2. L0 宪法的**全部要点**（第零条 + 第 1~15 条）都被覆盖，拆为"常驻红线"与"按场景加载的阶段技能"。
3. L1 stacks、L2 modes 以插件内 skill 形式提供，按项目自定义声明启用。
4. 支持大仓（monorepo）：不同子目录声明不同 stack。
5. 已有 `AGENTS.md`/`CLAUDE.md` 的项目可安全接入：绝不覆盖，提供逐条体检（删/留/上收）由用户拍板。
6. 支持两个同类项目（一期：两个 Go 微服务）共建 `stack-go-microservice` 并回流到 AI314。
7. 有可执行的自检：manifest 校验、skill 结构 lint、hook 输出测试。

**非目标**

- 不新增 README 中列出但尚不存在的 stack（go-web、go-agent-core、Python FastAPI、Wails、Shell）；README 改为如实标注"规划中"。
- 不重写现有 stack 的技术内容，只做结构迁移与"草案"标注；抽象度提升由后续共建完成。
- 不提供脚手架代码生成（`scaffold/`）。
- 不支持 CC/AGY 以外的 Agent（Codex/Cursor 等）。

**反目标（出现即视为失败）**

- 依赖 superpowers 才能工作。AI314 必须独立；两者同时安装时不得冲突、不得重复造流程。
- 业务项目里出现 L0/L1 正文副本（又回到拷贝式分发）。
- 自动修改或删除业务项目已有规则文件内容而未经用户确认。
- 常驻注入内容过长，挤占上下文（常驻核心须 ≤ 40 行）。

## 3. 已确认的关键决策（用户决定）

| # | 决策 |
|---|------|
| D1 | AI314 是独立规范，不依赖 superpowers |
| D2 | L0 不再作为常驻全文，改为 skill 在头脑风暴 / Plan / CR 等场景加载；执行阶段以 SPEC/PLAN 文档为准 |
| D3 | 做成 CC 与 AGY 插件分发 |
| D4 | 一期范围：插件化 + L0 拆分 + L1/L2 skill 化 + 升级/回流 + 已有项目接入体检，全部做 |
| D5 | L0 内容已确认，要点必须全部覆盖；stacks / modes / scripts 可增删调整；若前期设定与插件规范冲突，按插件规范调整 |
| D6 | mode 与常驻红线冲突时：项目声明块中启用的 mode，其豁免条款优先于常驻红线，**安全底线（第 15 条）除外**。常驻核心须写明这一优先级 |
| D7 | 目标 6（两个 Go 项目共建 L1）一期只交付工具：`contribute` skill + 改造后的 `sync-back.sh` 及测试；不接入真实业务仓、不要求走通真实回流 PR |

## 4. 方案总览

```
AI314/  (仓库根 = 插件根)
├── .claude-plugin/
│   ├── plugin.json            # CC manifest（name: ai314）
│   └── marketplace.json       # 自托管 marketplace，source: "./"
├── .antigravity-plugin/
│   └── plugin.json            # AGY manifest（name: ai314）
├── rules/
│   └── ai314-core.md          # L0 常驻红线：AGY 作为 always_on 规则直接加载；CC 由 hook 读取注入
├── hooks/
│   ├── hooks.json             # CC：SessionStart 注入 rules/ai314-core.md
│   └── session-start          # 注入脚本（bash）
├── skills/
│   ├── planning/              # L0 阶段技能：头脑风暴/设计/写计划
│   ├── code-review/           # L0 阶段技能：代码审查清单
│   ├── onboard/               # 接入/体检/更新项目声明块
│   ├── extract-stack/         # 从项目逆向提炼 L1（原 scripts/extract-stack-skill.md）
│   ├── contribute/            # 回流到 AI314（原 sync-back 流程）
│   ├── stack-go-microservice/ # L1（由 stacks/ 迁移）
│   ├── stack-web-admin/
│   ├── stack-ios-app/
│   ├── stack-macos-menubar/
│   ├── stack-crawler-script/
│   ├── mode-exploration-mvp/  # L2（由 modes/ 迁移）
│   └── mode-legacy-maintenance/
├── scripts/
│   ├── validate.sh            # lint 全部 skill + manifest 版本一致性 + 敏感信息扫描
│   ├── bump-version.sh        # 同步修改两个 manifest + marketplace 的 version
│   └── sync-back.sh           # 改造：项目 → AI314 skills/ 的回流质检与拷贝
├── tests/                     # 见 §9
├── AGENTS.md                  # AI314 仓库自身的开发约定（非 L0）
├── CHANGELOG.md
└── README.md
```

删除：`AGENTS.base.md`（内容拆入 `rules/` 与 `skills/`）、`stacks/`、`modes/`、`scripts/init-project.sh`、`scripts/extract-stack-skill.md`、`.DS_Store`（并加入 `.gitignore`）。

### 4.1 平台能力依据（2026-11 文档核实）

| 能力 | CC | AGY |
|------|----|-----|
| 插件 manifest | `.claude-plugin/plugin.json` | `plugin.json` 或 `.antigravity-plugin/plugin.json` |
| 插件 skills | `skills/<name>/SKILL.md`，命名空间 `ai314:<name>` | `skills/<name>/SKILL.md`，frontmatter `name` 必须与目录名一致；**无插件前缀**，以 `/<name>` 暴露 |
| 常驻注入 | 插件 `hooks/hooks.json` 的 SessionStart，输出 `hookSpecificOutput.additionalContext` | 插件根 `rules/` 目录（官方 build-plugins 文档已确认）：`rules/<name>.md` 带 frontmatter `trigger: always_on`；always_on 与全局规则共享 20k token 预算。AGY 的插件 hooks 文件在插件根 `hooks.json`（与 CC 的 `hooks/hooks.json` 路径不同，互不干扰），一期 AGY 不使用 hook |
| 安装 | `/plugin marketplace add lupguo/AI314` → `/plugin install ai314@ai314` | `agy plugin install https://github.com/lupguo/AI314`（本地开发：`agy plugin install ./`） |
| 校验 | `claude plugin validate .` | `agy plugin validate --strict .` |
| 更新 | 修改 `version` 后 `claude plugin update ai314` | 文档要求每次发布递增 `version` 供客户端检测更新；但 AGY CLI 1.5.16 **没有 `update` 子命令**（本机已确认），CLI 用户更新方式为 `agy plugin uninstall ai314 && agy plugin install https://github.com/lupguo/AI314` |
| 项目规则文件 | 有 `CLAUDE.md` 时只读 `CLAUDE.md`；无则读 `AGENTS.md`；`@path` 可导入 | 读 `AGENTS.md`/`GEMINI.md`（工作目录到仓库根），不读子目录规则 |

参考实现：本机已安装的 superpowers 7.0.0 同时提供 `.claude-plugin/` 与 `.antigravity-plugin/`，其 `hooks/session-start` 的 JSON 输出分支可作为参考。

## 5. L0 拆分与全覆盖映射

L0 原文（`AGENTS.base.md` 第零条 + 1~15 条）全部要点按下表落位。**原文措辞尽量保留**，只做归位与必要的压缩，不改动规则本意。

| L0 条款 | 常驻核心 `rules/ai314-core.md` | `skills/planning` | `skills/code-review` |
|---|---|---|---|
| 零、技能路由（按场景先读对应 skill，禁止跳过钦定规范） | ✅ 改写为"按场景加载 ai314 技能 + 读取项目 AI314 声明块" | | |
| 1 阶段隔离与审批门禁 | ✅ 一句话红线："Plan/原型未获明确 Approved 前不改业务源码" | ✅ 详细 | |
| 2 HTML 优先可视化对齐 | | ✅ | |
| 3 文档即契约（docs/ 目录约定、增量更新） | | ✅ | ✅ 检查文档是否同步 |
| 4 前置澄清与默认值先行 | | ✅ | |
| 5 模型路由与上下文隔离 | | ✅ | |
| 6 直觉化产品与交互 | | ✅ | ✅ |
| 7 架构与物理复杂度上限（300 行 / 50 行 / 无跨层/循环依赖） | ✅ 数字红线 | ✅ | ✅ |
| 8 最小变更半径 | ✅ | | ✅ |
| 9 技术依赖白名单 | ✅ "新增依赖前核对锁文件并说明理由" | ✅ Plan 中声明 | ✅ |
| 10 高信噪比注释 | | | ✅ |
| 11 根因与证据链闭环 | ✅ "完成汇报必须附实际运行命令与通过摘要；不盲猜、不吞异常" | | ✅ |
| 12 2/8 TDD 纠偏、禁止篡改断言 | ✅ 禁止项 | ✅ 测试策略 | ✅ |
| 13 重复操作脚本化 | | ✅ | ✅ |
| 14 完结自检门禁 | ✅ | | |
| 15 安全底线 | ✅ | | ✅ |

**常驻核心的约束**：≤ 40 行；只放"任何阶段都必须守"的红线 + 技能路由说明；不放流程细节；须含 D6 的优先级声明（声明块启用的 mode 豁免优先，安全底线不可豁免）。

**`planning` 的核心职责**（用户决策 D2 的落点）：在产出 SPEC/PLAN 时，把与本任务相关的 L0 规则、已启用的 L1 stack / L2 mode 约束**显式写入计划文档**（例如每个任务附"约束"小节与自检命令），使执行阶段的子代理只读计划也能遵守。

**与 superpowers 共存**：`planning` 与 `code-review` 写成"约束清单 + 产出物要求"，不定义必须走完的独立流程。skill 正文中声明："若当前已有其他流程类技能在驱动（如 brainstorming / writing-plans / requesting-code-review），沿用其流程，仅叠加本清单约束；产出物位置以本项目 `docs/` 约定为准"。

**触发设计**：skill 的 `description` 按任务场景描述（如"规划新功能、做方案设计、编写实现计划时"、"审查代码或 PR 时"），不引用 superpowers 的名称。常驻核心中再列一张"场景 → 技能"简表作为兜底路由。

## 6. 项目声明块：L1/L2 自定义启用与大仓

业务项目里**只保留一个带标记的声明块**，不含 L0/L1 正文：

```markdown
<!-- AI314:BEGIN v=0.1.0 -->
## AI314 工程规范
本项目遵循 AI314 规范（插件 ai314）。按下表加载对应技能：

| 路径范围 | 技能 |
| :-- | :-- |
| `services/**` | stack-go-microservice |
| `web/**` | stack-web-admin |
| `*` | mode-legacy-maintenance |
<!-- AI314:END -->
```

- **放在哪**：项目根 `AGENTS.md`（AGY 与无 CLAUDE.md 的 CC 都会读）。若项目存在 `CLAUDE.md`，onboard 确保其中含 `@AGENTS.md` 导入（这是 CC 在同时存在两者时读到 AGENTS.md 的方式）；若只有 `CLAUDE.md` 且用户不愿新增 AGENTS.md，则写入 `CLAUDE.md`。
- **大仓**：由于 AGY 不加载子目录规则，声明块统一放在**仓库根**，用路径范围表分发 stack。单一技术栈项目路径写 `*`。
- **版本标记** `v=` 记录写入时的插件版本，onboard 再次运行时据此提示是否需要刷新声明块格式。
- 声明块是机器可维护区：onboard 只改 BEGIN/END 之间的内容，块外内容一字不动。

## 7. 技能清单与职责

| 技能 | 来源 | 职责 |
|---|---|---|
| `planning` | L0 | 见 §5 |
| `code-review` | L0 | 见 §5；输出按严重度排序的问题清单 |
| `onboard` | 新增（替代 init-project.sh） | ⓪ 识别旧版 init-project.sh 痕迹（AGENTS.md 含 `VibeCoding 工程协作宪法` 全文、`.agents/skills/stack-*`/`mode-*` 副本、`.claude/skills` 软链），在体检表中列为"建议删除（已由插件提供）"；副本与 AI314 当前版本有差异时先提示走 contribute 回流〔实现者决定〕；① 无规则文件：创建 AGENTS.md + 声明块、`docs/{00-plans,01-biz,02-prod,03-ui-design,04-arch,05-deploy,_drafts}`、`.gitignore` 补 `.env`/`.env.*`；② 已有规则文件：**体检**——逐条把现有内容分为"与 L0 重复→建议删"、"项目特有→保留"、"可抽象复用→建议上收到 L1（走 contribute）"，以表格呈现，**用户逐条确认后**才改；③ 交互式选择 stack/mode 与路径范围，写入/刷新声明块；④ 幂等：重复运行不产生重复内容 |
| `extract-stack` | 迁移自 `scripts/extract-stack-skill.md` | 从当前项目逆向提炼 L1 SKILL.md 草稿 |
| `contribute` | 新增（包装 sync-back.sh） | 指导把项目中改进的 stack/mode 内容回流：本地有 AI314 clone 时调用 `scripts/sync-back.sh`，生成 diff，**以分支 + PR 方式提交**，不直推 main |
| `stack-*` ×5 | 迁移自 `stacks/` | 内容不变；正文顶部加"状态：草案（抽象度待共建完善）"；`go-microservice` 的 `Makefile.tpl`、`macos-menubar` 的 `preview_template.html` 作为 skill 附属文件保留 |
| `mode-*` ×2 | 迁移自 `modes/` | 内容不变 |

Skill 文件名约束：目录名即 skill 名（去掉 `stack-`/`mode-` 以外的前缀），frontmatter `name` 与目录名一致。

## 8. 升级与回流

**升级（AI314 → 各项目）**

1. AI314 改动合入 main 后，执行 `scripts/bump-version.sh <x.y.z>`（同步三处 version）并更新 `CHANGELOG.md`，打 tag `vX.Y.Z`。
2. 各机器：CC `claude plugin update ai314`；AGY 卸载后重装（见 §4.1），或运行 `scripts/update.sh`。
3. 由于正文全部在插件内，业务项目**无需任何改动**即获得新 L0/L1。仅当声明块格式变化时，在项目内运行 onboard 刷新。

版本语义：规则收紧/新增红线 → minor；措辞/修正 → patch；声明块格式不兼容 → major。

**回流（项目 → AI314）**

- 两个 Go 微服务项目在各自开发中发现 stack 规范缺口时，**直接在本机 AI314 clone 上改**（默认 `~/.ai314`，可用 `AI314_HUB` 覆盖），不在业务仓保存任何 L1 草稿副本（避免触发反目标）。`contribute` 流程：确认 clone 存在（不存在则提示用户执行 `gh repo clone lupguo/AI314 ~/.ai314`，经确认后代为执行）→ 在 clone 中新建分支 → 修改对应 `skills/stack-*/` 目录（含附属文件）→ 运行 `scripts/validate.sh` → 提交并 `gh pr create`。〔实现者决定〕
- 两个项目的修改可能冲突，以 PR review 合并为准，不做自动合并。
- `sync-back.sh` 改造点：保留"从业务项目的 `.agents/skills/stack-*|mode-*/` 目录整体回流"能力，用于迁移**旧版 init-project.sh 装配过的项目**中已被修改的副本；目标目录改为 `skills/`；同时支持 `stack-*` 与 `mode-*`（整个目录，含附属文件）；章节结构校验仅对 `stack-*` 生效；在 AI314 clone 中新建分支后写入，不直接写当前分支。〔实现者决定〕

## 9. 质量门禁

- `scripts/validate.sh`：所有 `skills/*/SKILL.md` frontmatter 含 `name`（与目录一致）与 `description`（≥ 10 字）；`stack-*` 含 `## 1.`~`## 4.` 章节；行数警告阈值 220；敏感信息正则扫描；三处 version 一致；`rules/ai314-core.md` ≤ 40 行且含 `trigger: always_on`。
- `claude plugin validate .` 与 `agy plugin validate --strict .` 均通过。
- `tests/`：bash 测试脚本，至少覆盖：hook 输出为合法 JSON 且含 core 内容；validate.sh 对故意构造的坏样例报错；sync-back.sh 在临时目录中的回流行为；onboard 的声明块幂等替换逻辑如果落为脚本则同样测试。
- `make check`（新增 Makefile）一条命令跑完以上全部。
- **端到端冒烟（手动，需记录结果）**：在一个临时 git 仓库中分别用 CC 与 AGY 本地安装插件，确认 ① 会话开始可见常驻核心；② 询问"帮我规划一个功能"会加载 `planning`；③ onboard 能写入声明块。

## 10. 留给实现者的决定

- 常驻核心与各 skill 的具体措辞压缩方式（须满足 §5 映射全覆盖与行数约束）。
- onboard 的声明块写入是纯 skill 指令完成，还是配一个小脚本（建议：配脚本 `scripts/ai314-block.sh` 以便测试幂等）。
- hook 脚本的跨平台细节（参考 superpowers `hooks/session-start`）。
- README 重写结构（需反映插件安装/升级/回流用法，并如实标注规划中的 stack）。

## 11. 风险与待实测项

0. 本机已安装 AGY CLI 1.5.16（`agy`），AGY 端冒烟可在本机执行。
1. **AGY 无 update 命令**（已确认）→ README 写明卸载重装方式；可提供 `scripts/update.sh` 一键完成 CC update + AGY 重装。〔实现者决定〕
2. AGY 插件 `rules/` 加载已由官方文档确认；冒烟仍需验证 `trigger: always_on` 生效。
3. **Skill 命名差异**（已确认）：CC 为 `ai314:<name>`，AGY 为 `/<name>`。声明块、常驻核心与各 skill 中引用技能时一律写**裸名**（如 `stack-go-microservice`），并在常驻核心说明"CC 下带 `ai314:` 前缀"。
4. **Skill 触发不保证**：靠常驻核心中的路由表 + 声明块兜底；冒烟测试覆盖主要场景。
5. CC 在同时存在 CLAUDE.md 与 AGENTS.md 时只读 CLAUDE.md，onboard 必须处理 `@AGENTS.md` 导入，否则声明块对 CC 不可见。
