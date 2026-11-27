# 经验自动回流闭环（lessons loop）设计

日期：2026-11-27
状态：待审

## 1. 意图与背景

AI314 的规范改进目前全靠用户事后想起来手动调用 `ai314:contribute` / `ai314:extract-stack`。真实情况是：用户在业务项目里自测 → 发现 AI 做错 → 在对话里纠正 → 再自测通过；"哪里错了、怎么纠正的"只存在于那次会话，会话结束即丢失，同类错误在其他项目反复出现。

本设计让插件**安装即生效**地完成四段闭环：

```
① 捕获(每次会话, 纯脚本, 0 token)
   → ② 提炼(项目内批量, 无头 Agent CLI)
   → ③ 聚合(跨项目, 本机全局库)
   → ④ 回流(自动提 PR 到 AI314, 用户审 PR)
```

同一条链路也用于沉淀**新 stack**：没有对应 stack 的技术特征积累足够踩坑后，自动产出 stack 草稿 PR。

## 2. 目标 / 非目标 / 反目标

**目标**
- 安装插件后无需任何配置即开始捕获；提炼与回流自动触发，唯一人工关口是 PR 审核。
- 聚焦**反面案例**（避免同类错误重犯）；正向只记录明确信号"用户直接回 OK"，用于发现"哪类提问总被直接放行"，进而改进为默认值先行、减少用户 OK 次数。
- 本项目内立即受益：提炼出的经验下次会话即被读取，不必等 AI314 发版。
- token 消耗与"信号条数"成正比，而非与会话长度成正比。
- Claude Code 与 Antigravity 两端都生效。

**非目标**
- 不做模糊的正向经验挖掘（无明确信号的"做得好"不采纳）。
- 不做 UI / 看板。
- 不自动 clone AI314 源码仓库（不存在时跳过回流并记日志）。
- 不自动合并 PR。

**反目标（技术上完成但算失败）**
- hook 拖慢会话或在会话中弹出任何额外交互。
- 无头调用触发自身 hook 形成递归 / 风暴。
- 原始对话片段（可能含密钥、业务数据）被提交进业务仓或 AI314。
- 网络/代理问题导致 inbox 数据丢失，或被误判为"模型输出错误"反复重试烧额度。
- `lessons.md` 无限膨胀，反过来吃掉每次会话的上下文。
- PR 里出现业务名词或无证据的空泛规范。

## 3. 已定决策（用户确认）

- 捕获完全自动、不打扰用户；会话结束时（`Stop`）跑脚本分析。
- 正向信号只采纳"用户回 OK 类短回复"，用于减少 OK 频次；其余正向不采纳，聚焦反面 case。
- 提炼与回流尽量自动化，用户只在 PR 审核环节把关。
- 提炼 / 回流使用无头 Agent CLI，默认是 `claude -p`，可通过配置切换（见 4.5）；必须处理好网络代理，避免把网络问题误识别为其他错误。
- 自动提 PR 由开关 `AI314_CONTRIBUTE` 控制，**默认关闭**。开启后向 `lupguo/AI314` 提 PR，以不断完善规范。关闭时，①②③ 照常运行，只跳过 ④。
- "可默认放行的提问"（OK 统计）也要回流到 AI314。
- 提炼和回流使用的 Agent 工具、模型、网络代理都可以配置。内置支持 `claude`、`tclaude`、`agy`、`codex`，配置统一放在 `~/.ai314/` 下。测试环境配置为 `agy` + 代理 `http://127.0.0.1:8118` + 模型 Hydrogen。
- Antigravity 使用其插件 `hooks.json` 的 `Stop` 事件（已核实官方文档 https://antigravity.google/docs/hooks 支持 `SessionStart`/`Stop` 等，stdin 携带 `transcriptPath`、`conversationId`、`workspacePaths`、`lastUserInput`）。

## 4. 设计

完整流程图见同目录下的 `2026-11-27-lessons-loop-flow.puml`。

### 4.1 运行时代码与目录

运行时放在 `platforms/_common/lessons/`（Python 3.11+ 标准库，与现有 `_common/auto-update` 同为两端共用），两个 adapter 拷贝到产物 `hooks/lessons/`，入口 `hooks/ai314-lessons`：

```
ai314-lessons capture  --platform claude|antigravity   # hook 调用，stdin 为 hook payload
ai314-lessons distill  --project <dir>                 # 由 capture 按阈值在后台拉起
ai314-lessons contribute                                # 由 distill 完成后在后台拉起
ai314-lessons status                                    # 人工排障：生效配置、inbox 数、上次运行、最近错误
ai314-lessons doctor                                    # 真实预检网络 + 试调用 runner
```

模块按职责拆分，每个文件 ≤300 行（宪法 §3）：`cli.py`、`transcript.py`（两端 transcript 解析）、`signals.py`、`inbox.py`、`config.py`（读取 config.toml 并合并环境变量）、`runner.py`（各 CLI 适配）、`netcheck.py`（代理注入 + 预检）、`store.py`（lessons.md 读写合并）、`contribute.py`。

数据位置：

| 位置 | 内容 | 是否入库 |
| :-- | :-- | :-- |
| `<项目>/.ai314/inbox.jsonl` | 原始信号片段 | 否（目录内自带 `.gitignore` 写 `*`，不改用户的 `.gitignore`） |
| `<项目>/.ai314/state.json` | 每个 transcript 已读到的偏移、退避时间、锁 | 否 |
| `<项目>/docs/ai314/lessons.md` | 提炼后的项目经验 | 是 |
| `~/.ai314/config.toml` | 统一配置（见 4.5、4.6） | 本机 |
| `~/.ai314/data/lessons/<归属>.jsonl` | 跨项目、已去业务化的通用条目 | 本机 |
| `~/.ai314/data/logs/lessons.log` | 运行日志 | 本机 |

`~/.ai314` 可通过 `AI314_HOME` 覆盖，与 auto-update 共用同一目录。远程安装时这个目录是 dist 分支的 clone，因此：
- dist 分支根目录的 `.gitignore` 必须忽略 `config.toml` 和 `data/`。由构建器写入，auto-update 判断工作区是否干净时本来就忽略未跟踪文件。
- 安装说明改为 `git init` + `fetch` + `checkout dist`，这样目录里已有配置时也能完成安装。原来的 `git clone` 写法要求目录为空。（我的决定）
- 本地开发安装时 `~/.ai314` 不是 git 仓库，auto-update 会直接退出；配置和数据照常可用。

项目根 = `git rev-parse --show-toplevel`（cwd 取自 payload：Claude 的 `cwd`、Antigravity 的 `workspacePaths[0]`）；非 git 仓库直接跳过。

### 4.2 ① 捕获（`Stop` hook，0 token）

- Claude：`hooks.json` 增加 `Stop` → `"${CLAUDE_PLUGIN_ROOT}/hooks/ai314-lessons" capture --platform claude`。
- Antigravity：插件根 `hooks.json` 的 `ai314` 分组增加 `Stop`，命令形式沿用现有 SessionStart（安装目录绝对路径、后台运行、stdout 只输出 `{}`、timeout 5）。
- hook 进程立即 fork 到后台并返回，前台耗时 < 100ms；后台出错只写日志，绝不影响会话。
- `Stop` 每轮都会触发，按 `state.json` 中 transcript 的已读行数**增量**解析，只处理新增行。
- transcript 路径一律使用 payload 给出的值，不硬编码文件名（Antigravity 文档写 `transcript.jsonl`，agent_monitor 实测为 `transcript_full.jsonl`，`type == "USER_INPUT"` 为用户消息）。Claude 为 `<config_dir>/projects/<slug>/<session>.jsonl`。

信号规则（关键词表放 `signals` 内的常量，便于后续调整）：

| kind | 规则 | 记录内容 |
| :-- | :-- | :-- |
| `correction` | 用户消息含否定/纠正词（不对、错了、不是、不要、别、应该、重新、又、还是不行、wrong、don't、should 等）且非首条消息 | 用户原话 ≤300 字 + 前一条 AI 回复摘要 ≤500 字（文本截断 + 用到的工具名与文件路径） |
| `rework` | 同一会话中同一文件被编辑 ≥3 次 | 文件路径、次数、对应时段的用户消息 |
| `test_flip` | 测试类命令（含 test/pytest/go test/make check 等）先失败后成功 | 命令、失败输出尾部 ≤500 字 |
| `tool_fail` | 同一命令连续失败 ≥2 次 | 命令、错误尾部 ≤300 字 |
| `ok` | 用户消息去标点后 ≤6 字且属于 OK 词表（ok、好、可以、继续、行、同意、yes、lgtm、就这样） | AI 上一条的最后一个问句 ≤300 字 |

每条 inbox 行：`{ts, platform, session, kind, user, prev, files, cmd, tail}`。

### 4.3 ② 提炼（项目内，无头 Agent CLI）

**触发**（capture 结束时检查）：inbox 非 ok 信号 ≥15 条，或最早一条 ≥7 天且总数 ≥3；且未持锁、不在退避期。满足则后台拉起 `distill`。

**调用方式**：模型**不使用任何工具**，脚本把输入拼成 prompt 走 stdin，要求输出严格 JSON（`--output-format json`），由脚本确定性地合并写文件。输入只有：
- inbox 新条目；
- 现有 `lessons.md` 的条目索引（id + 标题 + 归属，不含正文）；
- 可选归属清单：插件 `skills/` 下的技能名 + 项目 `AGENTS.md` 声明块中启用的 stack/mode。

模型输出：

```json
{
  "lessons": [
    {"op": "merge", "id": "L-007", "add_count": 2, "evidence": "..."},
    {"op": "new", "title": "...", "scene": "...", "symptom": "...", "fix": "...",
     "owner": "L0 | stack-xxx | mode-xxx | new-stack:<技术特征> | project",
     "generic_rule": "去业务化后的一句可核查硬约束（owner 为 project 时为空）"}
  ],
  "ok_patterns": [{"question_type": "...", "count": 4, "suggest": "此类决策默认采用 X，不再询问"}],
  "dropped": 3
}
```

**`docs/ai314/lessons.md` 格式**（`store.py` 解析/渲染，人可读、机可合并）：

```md
# 项目经验（AI314 自动维护，可手改）

## 反面经验
### L-007 改 handler 前未加载 stack 技能（×5）
- 场景 / 表现 / 正确做法 / 归属：stack-go-microservice / 最近：2026-11-27

## 可默认放行的提问
- 是否创建 docs/_drafts 草稿目录（OK ×6）→ 默认采用，不再询问
```

- 条目按次数降序；文件 >150 行时把次数最低且 30 天未增长的条目移到 `docs/ai314/lessons-archive.md`（控制每次会话读取成本）。
- 成功后清空已处理 inbox 行；`owner` 非 `project` 的条目追加到全局库 `lessons/<owner>.jsonl`（只写 `generic_rule`、计数、项目 id、日期，不写原始片段）。全局库另有 `projects.json` 记录 `项目 id → 本机绝对路径 / 目录名`，仅本机使用。项目 id = 项目根绝对路径的 sha1 前 8 位。（我的决定）
- `lessons.md` 由 distill 直接写入工作区，**不自动 commit**，随用户正常提交。

**本项目立即受益**：宪法 §零 增加一句"若项目存在 `docs/ai314/lessons.md`，开工前先阅读并避免其中的反面经验"。两端统一靠宪法生效，不依赖平台是否支持动态注入上下文。

### 4.4 ③ 聚合 + ④ 回流（自动 PR）

- **开关**：只有 `AI314_CONTRIBUTE=on` 时才执行回流，默认关闭。目标仓库固定为 `lupguo/AI314`，可用 `AI314_UPSTREAM` 覆盖。`gh` 账号对目标仓库有 push 权限时，直接推送分支；没有权限时，先执行 `gh repo fork`（幂等），推送到 fork，再向上游提 PR。
- distill 完成后检查全局库：某个 `owner` 下待回流条目 ≥3，且距该 owner 上次回流 ≥24h，则后台拉起 `contribute`。
- 前置条件不满足就跳过并记日志：`${AI314_SRC:-~/.ai314-src}` 存在、`gh auth status` 通过。因为使用独立 worktree，不要求 AI314_SRC 的工作区干净，也不要求它位于 main。
- 流程（git/gh 由脚本执行，模型只改文件）：
  1. 脚本：`git fetch origin main` 后用 `git worktree add` 在 `~/.ai314/data/worktrees/` 下基于 `origin/main` 建分支 `lessons/<owner>-<YYYYMMDD>`，**不切换用户在 AI314_SRC 中的当前分支**，结束后移除 worktree。（我的决定）
  2. 无头 Agent，**不授予任何工具**：脚本把目标 `content/` 文件的全文、该 owner 的待回流条目、contribute 技能里去业务化和硬约束的要求拼成 prompt。模型聚类并判断成熟度（同一规则来自 ≥2 个项目，或累计次数 ≥3），输出 JSON：`{files: [{path, content}], adopted: [...], pending: [...]}`。脚本校验 path 只能落在该 owner 对应的 `content/` 目录内，然后写入 worktree。这样各家 CLI 只需支持"prompt 进、文本出"，不依赖它们各自的工具权限模型。（我的决定）
  3. 脚本：`make check`。失败时删除分支、记日志，下次重试；成功则 commit（`feat(<owner>): ...`）、push、`gh pr create`。PR 正文用匿名项目 id（如 `p-3fa9c1d2`）列出来源和次数作为证据，不出现项目名；在本机用 `ai314-lessons status` 可以把 id 映射回项目。（我的决定）
  4. 被采纳的条目在全局库中标记为 `submitted`，未成熟的继续累积。
- **OK 统计回流**：distill 输出的 `ok_patterns` 先去业务化成通用的"提问类型"（如"是否为草稿创建目录""是否采用某项可逆的默认值"），再追加到全局库 `lessons/ok-defaults.jsonl`。同一提问类型在 ≥2 个项目中被直接放行、且累计 ≥5 次时，视为成熟，随同一 contribute 流程回流到 `content/L0-constitution/skills/planning/SKILL.md` 的"默认不再询问的决策"小节（如果没有这个小节就新建），开普通 PR。
- `owner = L0` 的条目改宪法，影响面大，一律开成 `--draft` PR。
- **新 stack**：如果 `owner = new-stack:<特征>` 的条目在 ≥2 个项目中累计达到 ≥5 条，就以产生条目最多的项目为 cwd，无头执行 extract-stack 流程。由脚本按 extract-stack 规定的扫描顺序，确定性地采样项目文件：依赖清单、2~3 层目录树、Makefile、lint 配置，再加最多 4 个核心文件，总量不超过 60KB。采样结果连同该特征的 lessons（作为"反面禁令"的依据）一起放进 prompt，模型同样不使用工具。产物放在 `content/L1-stacks/stack-<特征>/`，依据不足的地方写 `[待补充]`，开成 `--draft` PR。采样哪个项目，从 `projects.json` 中查得；draft 状态本身就是人工关口，不再额外加确认。（我的决定）
- 同步修改 `content/tools/contribute` 和 `content/tools/extract-stack` 两个技能：手动调用时也要读 `docs/ai314/lessons.md` 和全局库。

### 4.5 无头 Agent、模型与网络（`runner.py`、`netcheck.py`）

**统一配置 `~/.ai314/config.toml`**（标准库 `tomllib` 读取；文件不存在时全部取默认值）：

```toml
[lessons]
mode = "on"                    # on | capture-only | off
contribute = false             # 自动提 PR，默认关闭
upstream = "lupguo/AI314"
src = "~/.ai314-src"
distill_min = 15
contrib_min = 3

[agent]                        # 默认 Agent，distill 和 contribute 都继承这一节
runner = "auto"                # auto | claude | tclaude | agy | codex
bin = ""                       # 可执行文件路径，留空时按 runner 名在 PATH 中查找
model = ""                     # 留空时使用该 CLI 自己的默认模型
extra_args = []                # 原样追加到命令行末尾
timeout = 300                  # 单位：秒

[agent.contribute]             # 可选，按阶段覆盖上面的任意字段
timeout = 900

[network]                      # 只注入给无头子进程，不影响当前会话
https_proxy = ""
http_proxy = ""
all_proxy = ""
no_proxy = ""
probe_url = ""                 # 预检地址，留空时按 runner 取默认值
```

测试环境示例（同时作为 `config.example.toml` 随插件分发）：

```toml
[agent]
runner = "agy"
model = "gemini-4-hydrogen-medium"   # agy models 列出的 Hydrogen 系列
[network]
https_proxy = "http://127.0.0.1:8118"
http_proxy  = "http://127.0.0.1:8118"
```

**runner 适配表**（`runner.py` 内置；所有调用都是"prompt 走 stdin、从 stdout 取结果"，不授予工具）：

| runner | 命令模板 | 默认预检地址 |
| :-- | :-- | :-- |
| `claude` / `tclaude` | `<bin> -p [--model M] --output-format json` | `ANTHROPIC_BASE_URL`，未设置时 `https://api.anthropic.com` |
| `agy` | `<bin> -p [--model M] --output-format json --print-timeout <timeout>s --disable-slash-commands` | `https://generativelanguage.googleapis.com` |
| `codex` | `<bin> exec [-c model="M"] --sandbox read-only -` | `https://api.openai.com` |

- `auto` 时按 `claude → tclaude → agy → codex` 的顺序，取 PATH 中第一个存在的。
- 结果解析统一处理：先剥掉 CLI 外层的 JSON 包装（claude 和 agy 的 `result` 字段），再从文本中提取第一个完整的 JSON 对象，最后按 schema 校验。
- agy 和 codex 的输出包装格式以真机样本为准，在适配表中修正。这是留给实现者的。

**代理**：子进程环境 = hook 进程环境 + `[network]` 中的非空项。非空项会同时写入大写和小写两种变量名，例如 `HTTPS_PROXY` 和 `https_proxy`。`config.toml` 只接受上面列出的键，未知键记一条警告后忽略。**禁止**在里面放 Token：认证由各个 CLI 自己的登录态负责（宪法 §14）。

**预检**：调用前用 urllib 按同样的代理设置访问 `probe_url`，超时 5 秒。只判断能不能连上，不管 HTTP 状态码。

**防递归**：子进程环境设置 `AI314_HEADLESS=1`，所有 AI314 hook 一看到这个变量就立即退出。

**错误分类**，写入日志和 `state.json`：
- `network`：预检失败，或 CLI 报连接 / 超时 / 代理错误
- `auth`：CLI 报未登录或认证失败
- `no_runner`：找不到可执行文件
- `bad_output`：JSON 不合法或不符合 schema
- `check_failed`：`make check` 失败

**退避**：`network`、`auth`、`no_runner` 不消耗额度，按 1h→2h→…→24h 指数退避，inbox 保持不动。`bad_output` 每天最多重试 1 次。任何失败都不丢弃 inbox。超时后 kill 子进程，按 `network` 处理。

### 4.6 开关与排障

- 所有开关都在 `config.toml` 里。同名环境变量优先级更高，方便临时覆盖：`AI314_LESSONS=on|capture-only|off`，`AI314_CONTRIBUTE=on|off`。
- 单个项目关闭：创建 `<项目>/.ai314/disabled`。
- `ai314-lessons status`：显示当前生效的配置（代理只显示 host）、选中的 runner 和 bin、inbox 条数、上次运行时间和错误分类、退避到期时间、项目 id 与项目的映射。
- `ai314-lessons doctor`：用当前配置真实跑一次预检，再用一个极短 prompt 调用 runner，分别报告网络、认证、输出解析各自是否通过。用于在测试环境验证 agy + 代理 + Hydrogen 这套配置。

## 5. 约束

- 宪法 §3：每个文件 ≤300 行，每个函数 ≤50 行。capture/distill/contribute 按模块拆开，相互不跨层调用。
- 宪法 §5：零新增依赖，运行时与构建器都只用 Python 标准库；外部命令只用 `git`、`gh`，以及配置中选定的 Agent CLI。
- 宪法 §12：后台失败一律分类写日志，禁止静默吞掉异常。
- 宪法 §14：原始片段只保存在 `.ai314/`，该目录自带 gitignore；全局库和 PR 只写去业务化后的规则；`config.toml` 不接受任何凭据类键。
- AGENTS.md：平台差异只写在 `platforms/<平台>/adapter.py`，即 hook 注册方式和 payload 字段映射；`dist/` 不手改；改动脚本前先写失败测试。

## 6. 公开接口变更清单

- 插件 hooks：Claude 和 Antigravity 都新增 `Stop` 事件。
- 新配置文件 `~/.ai314/config.toml`（schema 见 4.5），并随插件分发 `config.example.toml`。
- 环境变量：`AI314_LESSONS`、`AI314_CONTRIBUTE`（覆盖配置）、`AI314_HOME`（已有，沿用）、`AI314_HEADLESS`（内部使用）。
- dist 分支根目录 `.gitignore` 新增 `config.toml`、`data/`；README 中的远程安装命令改为 init + fetch + checkout 写法。
- 新增 CLI：`hooks/ai314-lessons capture|distill|contribute|status|doctor`。
- 新增项目内文件约定：`.ai314/`、`docs/ai314/lessons.md`。
- 宪法 §零新增一句（见 4.3）；修改 `contribute` 和 `extract-stack` 两个技能的说明。

## 7. docs/base 影响清单

AI314 仓库目前没有 `docs/base/`，因此无需回写。README 的文档地图中需要补一行，说明经验闭环的位置和开关。

## 8. 测试策略（TDD 2/8，放在 `tests/`）

- transcript 解析：两端各用一个小型 fixture（脱敏样本），验证能正确取出用户消息、AI 回复和工具调用。
- 信号：覆盖 5 种 kind 的命中和不命中；首条消息不算 correction；OK 只匹配短回复。
- 增量：同一 transcript 连续调用两次 capture，不重复写入。
- 防递归：设置 `AI314_HEADLESS=1` 时 capture 不产生任何输出。
- distill：用桩 `claude` 返回固定 JSON，验证合并、计数、归档、全局库写入、inbox 清空；返回非法 JSON 时 inbox 保留。
- 配置：config.toml 不存在时取默认值；按阶段覆盖生效；环境变量优先于文件；遇到未知键记警告后忽略。
- runner：4 种 runner 各自生成正确的命令行和环境（含代理的大小写两种变量）；`auto` 按顺序选择；用桩可执行文件分别返回 claude、agy 两种 JSON 包装，都能解析。
- 网络：预检失败时归类为 `network`，进入退避，inbox 保留，且不调用 runner。
- contribute 开关：`AI314_CONTRIBUTE` 未设置时不拉起 contribute；没有 push 权限时走 fork 路径（用桩 `gh` 模拟）。
- contribute：用本地 bare 仓库加桩 `gh`、桩 `claude`（沿用 `test_auto_update.py` 的做法），验证 make check 失败时不提 PR，成功时分支名和 PR 参数正确。
- adapter：两端产物的 hooks 中都包含 `Stop`，运行时文件都已拷贝。

## 9. 留给实现者的判断

- 关键词表和阈值的初始值可以根据 fixture 微调。
- agy、codex 的输出包装格式与认证错误文案：以真机样本为准，修正 runner 适配表。
- Claude 的 `Stop` payload 中是否带 `cwd`、Antigravity 的 `Stop` 是否在每次执行结束都触发：以真机样本为准，在 adapter 层做字段映射。
- distill / contribute 的 prompt 措辞。

## 10. 执行方式

预计 8~10 个任务，模块之间边界清晰，推荐使用子代理驱动执行。最后在真机上跑端到端冒烟，记录到 `docs/smoke/`：用测试环境配置（agy + 代理 + Hydrogen）先跑 `doctor`，再走一遍 capture → distill；如果 contribute 开着，对一个测试仓库走一遍完整回流。
