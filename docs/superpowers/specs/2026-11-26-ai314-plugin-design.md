# AI314 插件化设计（一期）

> 状态：草案 v2，待用户确认
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
| D8 | 仓库目录按 L0/L1/L2 分层，平台适配文件与规范正文分离；为以后接入更多 Agent（如 Codex）预留平台位 |
| D9 | 更新全自动：CC 用 marketplace `autoUpdate`；AGY 由 SessionStart hook 检测到新版本后**在后台自动重装**，不提示用户 |
| D10 | 回流链路：业务项目内触发 `contribute` → 自动开分支并 `gh pr create` → CI 校验 → **用户 review 合并（保留人工）** → CI 自动发版 |
| D7 | 目标 6（两个 Go 项目共建 L1）一期只交付工具：`contribute` skill + 改造后的 `sync-back.sh` 及测试；不接入真实业务仓、不要求走通真实回流 PR |

## 4. 方案总览

### 4.1 目录布局（D8）

**约束**：CC 安装插件时只复制插件目录内的文件，不能引用目录外内容；因此不拆成多个平台插件目录（否则正文要么多份、要么引入构建步骤），**仓库根即插件根**，在根内按"平台适配 / 规范分层"组织。两端 manifest 都支持 `skills` 字段追加 skill 扫描目录，借此实现分层。

```
AI314/  (仓库根 = 插件根)
├── .claude-plugin/
│   ├── plugin.json              # CC manifest：skills 指向下方各层；hooks 指向 adapters/claude/hooks.json
│   └── marketplace.json         # 自托管 marketplace（source: "./"）
├── .antigravity-plugin/
│   └── plugin.json              # AGY manifest：skills 指向下方各层
├── hooks.json                   # AGY 插件 hooks（AGY 规定必须在插件根）→ 调用 adapters/antigravity/
├── rules/
│   └── ai314-core.md            # L0 常驻红线（AGY 规定 rules/ 必须在插件根）；CC hook 读同一文件注入
│
├── adapters/                    # 平台胶水，规范正文不放这里
│   ├── claude/
│   │   ├── hooks.json           # SessionStart → session-start
│   │   └── session-start        # 读取 rules/ai314-core.md，输出 additionalContext
│   ├── antigravity/
│   │   └── auto-update          # SessionStart：检测新版本并后台重装（§8.2）
│   └── README.md                # 新增平台（如 codex）时的接入约定
│
├── L0-constitution/             # L0：通用宪法
│   └── skills/
│       ├── planning/
│       └── code-review/
├── L1-stacks/                   # L1：技术栈蓝图（预期大量扩展）
│   ├── stack-go-microservice/   #   SKILL.md + Makefile.tpl
│   ├── stack-web-admin/
│   ├── stack-ios-app/
│   ├── stack-macos-menubar/     #   SKILL.md + preview_template.html
│   └── stack-crawler-script/
├── L2-modes/                    # L2：研发模式补丁
│   ├── mode-exploration-mvp/
│   └── mode-legacy-maintenance/
├── tools/                       # 规范的生命周期工具（非规范本身）
│   └── skills/
│       ├── onboard/
│       ├── extract-stack/
│       └── contribute/
│
├── scripts/                     # validate.sh / install.sh / sync-back.sh / ai314-block.sh
├── .github/workflows/           # ci.yml（PR 校验）/ release.yml（合并后发版）
├── tests/
├── AGENTS.md                    # AI314 仓库自身的开发约定（不是 L0）
├── CHANGELOG.md
└── README.md
```

- 根目录的 `hooks.json` 与 `rules/` 是 AGY 的硬性位置要求，内容只做转发/单一正文，不放逻辑。
- L1 每个 stack 是一个 skill 目录，`L1-stacks/` 本身即 skill 扫描根，新增 stack = 新增一个子目录，无需改 manifest。
- 若实现时发现某端 manifest 的 `skills` 字段不接受某种路径形式，按插件规范调整目录（D5），但必须保持三层可辨识。

删除：`AGENTS.base.md`（内容拆入 `rules/` 与 `L0-constitution/`）、`stacks/`、`modes/`（迁入 `L1-stacks/`、`L2-modes/`）、`scripts/init-project.sh`、`scripts/extract-stack-skill.md`（迁入 `tools/skills/extract-stack/`）、`.DS_Store`（并加入 `.gitignore`）。

### 4.2 平台能力依据（2026-11 官方文档 + 本机 AGY 1.5.16 核实）

| 能力 | CC | AGY |
|------|----|-----|
| 插件 manifest | `.claude-plugin/plugin.json` | `plugin.json` 或 `.antigravity-plugin/plugin.json`；组件目录均在插件根 |
| 额外 skill 目录 | manifest `skills`（路径数组，追加到默认 `skills/`） | manifest `skills`（"Extra skill directories"） |
| Skill 命名 | `ai314:<name>` | `/<name>`，无插件前缀；frontmatter `name` 必须等于目录名，kebab-case ≤ 64 |
| 常驻注入 | SessionStart hook 输出 `hookSpecificOutput.additionalContext` | 插件根 `rules/*.md`，`trigger: always_on`；与全局规则共享 20k token 预算 |
| Hooks | 默认 `hooks/hooks.json`，可用 manifest `hooks` 指到别处 | 插件根 `hooks.json`，按插件名分组（参考本机 agent-monitor 插件）；SessionStart 可输出 `injectSteps`；命令可用插件内相对路径 |
| 安装 | `claude plugin marketplace add lupguo/AI314` → `claude plugin install ai314@ai314` | `agy plugin install <本地目录 \| GitHub URL>` |
| 更新 | marketplace `autoUpdate: true` 时，会话开始后 ≤10 分钟后台更新；manifest **不写 `version`** 则以 git commit SHA 为版本，main 每次合并即为新版本 | CLI 无 `update` 子命令；文档要求每次发布递增 `version` |
| 校验 | `claude plugin validate .` | `agy plugin validate --strict .` |
| 项目规则文件 | 有 `CLAUDE.md` 时只读 `CLAUDE.md`；无则读 `AGENTS.md`；`@path` 可导入 | 读 `AGENTS.md`/`GEMINI.md`（工作目录到仓库根），不读子目录规则 |

参考实现：本机已安装的 superpowers 同时提供 `.claude-plugin/` 与 `.antigravity-plugin/`；其 `hooks/session-start` 的 JSON 输出写法可参考。

## 5. L0 拆分与全覆盖映射

L0 原文（`AGENTS.base.md` 第零条 + 1~15 条）全部要点按下表落位。**原文措辞尽量保留**，只做归位与必要的压缩，不改动规则本意。

| L0 条款 | 常驻核心 `rules/ai314-core.md` | `planning` | `code-review` |
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
| `contribute` | 新增 | 按 §8.3 在 `~/.ai314` 开分支、修改、校验、自动 `gh pr create`；`~/.ai314` 不存在时提示运行 `scripts/install.sh`；旧版副本迁移时调用 `scripts/sync-back.sh` |
| `stack-*` ×5 | 迁移自 `stacks/` | 内容不变；正文顶部加"状态：草案（抽象度待共建完善）"；`go-microservice` 的 `Makefile.tpl`、`macos-menubar` 的 `preview_template.html` 作为 skill 附属文件保留 |
| `mode-*` ×2 | 迁移自 `modes/` | 内容不变 |

Skill 命名约束：目录名即 skill 名，frontmatter `name` 与目录名一致（AGY 强制）；L1 一律 `stack-` 前缀、L2 一律 `mode-` 前缀，L0 与工具类无前缀。

## 8. 安装、自动更新与回流（D9、D10）

### 8.1 安装（每台机器一次）

`scripts/install.sh`（可 `curl | bash` 或 clone 后执行）完成：

1. `git clone https://github.com/lupguo/AI314 ~/.ai314`（`AI314_HOME` 可覆盖）。这份本地 clone 同时用于 AGY 安装源与 `contribute` 回流。
2. CC：`claude plugin marketplace add lupguo/AI314`，`claude plugin install ai314@ai314`，并在 `~/.claude/settings.json` 的 `extraKnownMarketplaces` 中为该 marketplace 设 `autoUpdate: true`。
3. AGY：`agy plugin install ~/.ai314`。
4. 未安装某端 CLI 时跳过该端并提示，不报错退出。

### 8.2 自动更新

**CC**：`.claude-plugin/plugin.json` 与 `marketplace.json` **均不写 `version`**，以 commit SHA 计版本；`autoUpdate` 开启后，main 合并即被各机器后台拉取，下次会话（或 `/reload-plugins`）生效。

**AGY**（后台自动重装，不打扰用户）：根 `hooks.json` 注册 SessionStart → `adapters/antigravity/auto-update`：

1. 节流：距上次检查不足 6 小时直接退出（时间戳存 `~/.ai314/.ai314-last-check`，已 gitignore）〔实现者决定〕。
2. 以 detach 方式后台执行（hook 本身立即返回 `{}`，不阻塞会话、任何失败都不影响会话）：`git -C ~/.ai314 fetch` → 若落后于 `origin/main` 且工作区干净、当前在 main 分支 → `git pull --ff-only` → `agy plugin uninstall ai314 && agy plugin install ~/.ai314`。
3. `~/.ai314` 处于非 main 分支或有未提交修改（说明正在 contribute）时跳过，避免覆盖用户工作。
4. 结果追加写入 `~/.ai314/.ai314-update.log`。新版本于下次会话生效。
5. **需冒烟验证**：会话进行中重装插件不会导致当前会话异常；若有问题，改为"本次只 pull 并写标记，下次 SessionStart 开头同步重装"。

AGY 需要 `version` 递增才能识别更新：`.antigravity-plugin/plugin.json` 保留 `version`，由 release 工作流自动递增（§8.3）。

### 8.3 回流与发版流水线

```
业务项目中触发 contribute
  → 在 ~/.ai314 新建分支 contrib/<项目名>-<stack>-<日期>
  → 修改 L1-stacks/ 或 L2-modes/ 对应目录（含附属文件）
  → 本地 make check
  → git push + gh pr create（标题遵循 Conventional Commits，正文附来源项目与改动理由）
CI（.github/workflows/ci.yml，PR 触发）
  → scripts/validate.sh + tests + 两端 plugin validate（CI 无 CLI 时跳过并标注）
用户 review → 合并（人工环节，处理两个项目改动冲突）
CI（.github/workflows/release.yml，push main 触发）
  → 依据合并的 PR 标题决定递增级别（feat→minor、fix/docs→patch、带 ! 或 BREAKING→major）
  → 更新 .antigravity-plugin/plugin.json version + CHANGELOG.md，提交 "chore(release): vX.Y.Z [skip ci]"，打 tag
  → 各机器：CC 自动更新；AGY 下次会话 hook 自动重装
```

- `contribute` 结束后切回 `~/.ai314` 的 main，保证自动更新不被阻塞。
- release 工作流需要向 main 推送权限；若 main 开启了分支保护导致无法推送，改为由 release 工作流开一个版本 PR 自动合并，或在 README 说明为 Actions 放行〔实现者决定〕。
- `sync-back.sh` 改造：用于迁移**旧版 init-project.sh 装配过的项目**中已被修改的 `.agents/skills/stack-*|mode-*/` 副本——整目录质检后写入 `~/.ai314` 的新分支（`L1-stacks/` 或 `L2-modes/`），之后同样走 PR；章节结构校验仅对 `stack-*` 生效。
- 业务仓中不保存任何 L1 草稿副本。
- 版本语义：规则收紧/新增红线 → minor；措辞/修正 → patch；声明块格式不兼容 → major。仅当声明块格式变化时，需在项目内运行 onboard 刷新；其余更新业务项目无需任何改动。

## 9. 质量门禁

- `scripts/validate.sh`：`L0-constitution/skills/`、`L1-stacks/`、`L2-modes/`、`tools/skills/` 下所有 `SKILL.md` frontmatter 含 `name`（与目录一致、前缀与所在层匹配）与 `description`（≥ 10 字）；`stack-*` 含 `## 1.`~`## 4.` 章节；行数警告阈值 220；敏感信息正则扫描；CC manifest 与 marketplace 不含 `version`、AGY manifest 含合法 semver；`rules/ai314-core.md` ≤ 40 行且含 `trigger: always_on`；两端 manifest 的 `skills` 列表覆盖全部层目录。
- `claude plugin validate .` 与 `agy plugin validate --strict .` 均通过。
- `tests/`：bash 测试脚本，至少覆盖：CC hook 输出为合法 JSON 且含 core 内容；AGY auto-update 在"已最新 / 落后 / 非 main 分支 / 脏工作区 / 节流期内"五种情况下的行为（用临时 git 仓库与假 `agy` 命令桩）；release 版本递增逻辑（PR 标题 → 级别）；validate.sh 对坏样例报错；sync-back.sh 临时目录回流；`ai314-block.sh` 声明块幂等替换。
- `make check`（新增 Makefile）一条命令跑完以上全部。
- **端到端冒烟（手动，需记录结果到 `docs/smoke/`）**：在一个临时 git 仓库中分别用 CC 与 AGY 安装插件，确认 ① 会话开始可见常驻核心；② 询问"帮我规划一个功能"会加载 `planning`；③ 询问 Go 微服务相关任务会加载 `stack-go-microservice`；④ onboard 能写入声明块；⑤ AGY：在 `~/.ai314` 落后一个提交时开启会话，后台重装成功且当前会话不受影响。

## 10. 留给实现者的决定

- 常驻核心与各 skill 的具体措辞压缩方式（须满足 §5 映射全覆盖与行数约束）。
- onboard 的声明块写入是纯 skill 指令完成，还是配一个小脚本（建议：配脚本 `scripts/ai314-block.sh` 以便测试幂等）。
- hook 脚本的跨平台细节（参考 superpowers `hooks/session-start`）；一期仅保证 macOS/Linux。
- README 重写结构（需反映插件安装/升级/回流用法，并如实标注规划中的 stack）。

## 11. 风险与待实测项

0. 本机已安装 AGY CLI 1.5.16（`agy`），AGY 端冒烟可在本机执行。
1. **AGY 无 update 命令**（已确认）→ 以 §8.2 的 hook 后台重装解决；需冒烟验证会话中重装的安全性。
2. AGY 插件 `rules/` 加载已由官方文档确认；冒烟仍需验证 `trigger: always_on` 生效。
3. **Skill 命名差异**（已确认）：CC 为 `ai314:<name>`，AGY 为 `/<name>`。声明块、常驻核心与各 skill 中引用技能时一律写**裸名**（如 `stack-go-microservice`），并在常驻核心说明"CC 下带 `ai314:` 前缀"。
4. **Skill 触发不保证**：靠常驻核心中的路由表 + 声明块兜底；冒烟测试覆盖主要场景。
5. **AGY hook 环境**：官方未文档化插件 hook 的环境变量（无插件根路径变量）；脚本以 `~/.ai314` 固定路径（或 `AI314_HOME`）定位，不依赖插件根。hook 的网络访问继承用户 shell 代理设置。
6. **CC 不写 version 的副作用**：每次 main 提交都会触发 CC 更新，含纯文档提交；可接受。
7. CC 在同时存在 CLAUDE.md 与 AGENTS.md 时只读 CLAUDE.md，onboard 必须处理 `@AGENTS.md` 导入，否则声明块对 CC 不可见。
