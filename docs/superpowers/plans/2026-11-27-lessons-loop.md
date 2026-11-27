# Lessons Loop 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal：** 插件装好就自动生效，走通"捕获 → 提炼 → 聚合 → 回流"的经验闭环。

**Architecture：**
- 运行时放在 `platforms/_common/lessons/`，是一个纯标准库的 Python 包，入口 `platforms/_common/ai314-lessons`，两个平台的 adapter 都把它拷到产物的 `hooks/` 下。
- 两个平台的 `Stop` hook 调 `ai314-lessons capture`：先读 stdin，再 fork 到后台，前台立即返回。后台进程按顺序执行 增量捕获 → 按阈值 distill → 按开关和阈值 contribute。
- 模型调用一律不给工具：输入是 prompt，输出是 JSON，文件由脚本按确定的规则写入。

**Tech Stack：** Python 3.11+ 标准库（`tomllib`、`urllib`、`subprocess`、`unittest`），外部命令为 git、gh、Agent CLI（claude/tclaude/agy/codex）。

**Spec：** `docs/superpowers/specs/2026-11-27-lessons-loop-design.md`；流程图：`docs/superpowers/specs/2026-11-27-lessons-loop-flow.puml`

## Global Constraints

- 只用标准库；单文件 ≤300 行，单函数 ≤50 行（宪法 §3）。
- 平台差异只能出现在 `platforms/<平台>/adapter.py`（hook 注册），以及 `lessons/hookio.py` 的 payload 字段映射；`dist/` 不手改。
- 后台任何失败都要分类写入 `~/.ai314/data/logs/lessons.log`，不得静默吞掉，也不得影响会话（宪法 §12）。
- 原始片段只存在 `<项目>/.ai314/`，该目录自带内容为 `*` 的 `.gitignore`；全局库和 PR 只写去业务化后的规则；`config.toml` 不收凭据（宪法 §14）。
- `AI314_HEADLESS=1` 时所有入口立即退出。
- 默认值：`mode=on`、`contribute=false`、`upstream=lupguo/AI314`、`src=~/.ai314-src`、`distill_min=15`、`contrib_min=3`、`agent.runner=auto`、`agent.timeout=300`、`agent.contribute.timeout=900`。
- `AI314_HOME` 默认 `~/.ai314`；数据目录为 `$AI314_HOME/data`。
- 提交使用 Conventional Commits，结尾带 Co-Authored-By 行。

## Review Focus

1. 非 git 目录、空 transcript、transcript 路径不存在：capture 静默退出，不写 inbox → Task 3 测试 `test_capture_skips_non_git` / `test_missing_transcript`。
2. transcript 中出现半行或损坏的 JSON（正在写入时被读到）：跳过坏行，偏移只推进到最后一个完整行 → Task 2 测试 `test_partial_last_line`。
3. 同一 transcript 被并发的两次 Stop 处理：靠锁避免重复写入 → Task 3 测试 `test_lock_prevents_double`。
4. runner 返回的 JSON 外面包了 markdown 代码块或带前后缀文字：仍能提取出 JSON → Task 5 测试 `test_extract_json_fenced`。
5. 模型返回的文件路径越出 owner 目录（如 `../../etc`、`ai314.toml`）：拒绝写入，按 `bad_output` 处理 → Task 8 测试 `test_rejects_path_escape`。

---

## 文件结构

```
platforms/_common/ai314-lessons           # 可执行入口：sys.path 指向自身目录后调用 lessons.cli.main
platforms/_common/config.example.toml     # 配置示例（测试环境：agy + 8118 代理 + Hydrogen）
platforms/_common/lessons/__init__.py
  paths.py      # AI314_HOME、data 目录、项目根、项目 id、日志
  config.py     # 读 config.toml，叠加环境变量，按 stage 取 agent 配置
  hookio.py     # 把两个平台的 hook payload 归一化为 HookInput
  transcript.py # 把两个平台的 transcript 归一化为 Event 列表，支持增量偏移
  signals.py    # 从 Event 中抽取 5 类信号
  inbox.py      # 项目 .ai314/ 下的 inbox、state、锁
  netcheck.py   # 代理注入 + 预检
  runner.py     # 各 CLI 的命令模板、调用、解包、JSON 提取、错误分类
  backoff.py    # 退避状态（全局 data/backoff.json）
  store.py      # lessons.md 的解析/渲染/合并 + 全局库读写
  distill.py    # 提炼流程
  contribute.py # 回流流程（git worktree、make check、gh）
  sampler.py    # new-stack 的项目文件采样
  cli.py        # capture | distill | contribute | status | doctor
tests/test_lessons_core.py      # transcript、signals、inbox、capture
tests/test_lessons_runner.py    # config、runner、netcheck、backoff
tests/test_lessons_distill.py   # store、distill
tests/test_lessons_contrib.py   # contribute、sampler
tests/fixtures/lessons/claude.jsonl、agy.jsonl   # 脱敏样本
```

修改：`platforms/claude/adapter.py`、`platforms/antigravity/adapter.py`、`build/ai314build/build.py`（写 `dist/.gitignore`）、`tests/helpers.py`（sys.path 加入 `platforms/_common`）、`tests/test_adapters.py`、`content/L0-constitution/AGENTS.base.md`、`content/tools/contribute/SKILL.md`、`content/tools/extract-stack/SKILL.md`、`README.md`。

---

### Task 1：paths + config

**Files：** Create `lessons/__init__.py`、`paths.py`、`config.py`；Modify `tests/helpers.py`；Test `tests/test_lessons_runner.py`

**Interfaces（Produces）：**
- `paths.home(env=os.environ) -> Path`（`AI314_HOME`，默认 `~/.ai314`）；`paths.data_dir(env) -> Path`；`paths.log(msg: str, env=os.environ) -> None`（追加写入 `data/logs/lessons.log`，带时间戳）
- `paths.project_root(cwd: str) -> Path | None`（执行 `git -C cwd rev-parse --show-toplevel`，失败返回 None）
- `paths.project_id(root: Path) -> str`（取 `"p-" +` 根路径 sha1 的前 8 位）
- `config.load(env=os.environ) -> Config`，其中 `Config` 为 dataclass，字段 `lessons: dict`、`agent: dict`、`agent_stages: dict[str, dict]`、`network: dict`、`warnings: list[str]`
- `Config.agent_for(stage: str) -> dict`（`[agent]` 与 `[agent.<stage>]` 合并）
- 环境变量覆盖：`AI314_LESSONS` 对应 `lessons.mode`，`AI314_CONTRIBUTE=on|off` 对应 `lessons.contribute`

- [ ] Step 1：写测试 `test_defaults_when_missing`（文件不存在时取 Global Constraints 中的全部默认值）、`test_stage_override`（`agent_for("contribute")["timeout"] == 900`，且 runner 从 `[agent]` 继承）、`test_env_overrides`（`AI314_CONTRIBUTE=on` 时 `lessons["contribute"] is True`）、`test_unknown_key_warns`（`[network] token="x"` 会进入 warnings，且不出现在 network 中）、`test_project_id_stable`
- [ ] Step 2：`make test` → FAIL（模块不存在）
- [ ] Step 3：实现；`tests/helpers.py` 的 sys.path 循环中加入 `ROOT / "platforms/_common"`
- [ ] Step 4：`make test` → PASS
- [ ] Step 5：commit `feat(lessons): add paths and config loader`

### Task 2：transcript 归一化 + 信号

**Files：** Create `hookio.py`、`transcript.py`、`signals.py`、`tests/fixtures/lessons/{claude,agy}.jsonl`；Test `tests/test_lessons_core.py`

**Interfaces（Produces）：**
- `hookio.parse(platform: str, raw: str) -> HookInput | None`，其中 `HookInput(transcript: Path, cwd: str, session: str)`
  - claude：`transcript_path`、`cwd`、`session_id`
  - antigravity：`transcriptPath`、`workspacePaths[0]`、`conversationId`
- `transcript.Event`：dataclass，字段 `role: str`（`user|assistant|call|result`）、`text=""`、`tool=""`、`cmd=""`、`path=""`、`error=False`
- `transcript.read(platform: str, path: Path, start: int) -> tuple[list[Event], int]`（start 和返回值都是"已完整读取的行数"）
  - claude：
    - user：`type=="user"`、content 为 str、非 isMeta、不以 `<` 开头
    - assistant：text 块
    - call：tool_use 块。Bash 取 `input.command`；Edit/Write/MultiEdit/NotebookEdit 取 `input.file_path`
    - result：tool_result 块，`is_error` 作为 error
  - agy：
    - user：`USER_INPUT`，只取 `<USER_REQUEST>` 内的文本
    - assistant：`PLANNER_RESPONSE.content`
    - call：`tool_calls` 中的每一项。它可能是 list，也可能是 Python repr 字符串，后者用 `ast.literal_eval` 解析。`run_command.CommandLine` 作为 cmd；`edit_file`/`write_file` 的 `Path` 作为 path
    - result：`GENERIC` 步骤。`status=="ERROR"`，或内容匹配 `exited with code (\d+)` 且退出码非 0 时，error 为 True；result 按顺序与前面的 call 配对，补上 cmd
- `signals.extract(events: list[Event], sess: dict) -> list[dict]`。`sess` 是该 session 的跨轮状态，函数会原地更新，键为 `edit_turns: dict[path, int]`、`reworked: list`、`test_failed: str|None`、`last_fail: str|None`、`user_seen: int`
- 输出 dict 的键：`kind, user, prev, files, cmd, tail`；字段截断长度与关键词表按 spec 4.2

- [ ] Step 1：用本仓库真实会话的格式手写两个小型 fixture（各约 12 行，覆盖纠正、OK、测试先失败后成功、同一命令连续失败两次、同一文件跨 3 轮编辑），写测试：
  - `test_claude_events` / `test_agy_events`：断言 role 序列、cmd、path、error
  - `test_partial_last_line`：最后一行没有换行符时不计入，返回的偏移量不包含它
  - `test_signal_kinds`：两个 fixture 抽出的 kind 集合都等于 `{"correction","ok","test_flip","tool_fail","rework"}`
  - `test_first_message_not_correction`
  - `test_ok_only_short`："ok 但是把 X 改成 Y" 不算 ok
  - `test_ok_records_question`：`prev` 等于 AI 上一条消息中最后一个以 `？` 或 `?` 结尾的句子
- [ ] Step 2：`make test` → FAIL
- [ ] Step 3：实现
- [ ] Step 4：`make test` → PASS
- [ ] Step 5：commit `feat(lessons): normalize transcripts and extract signals`

### Task 3：inbox + capture 命令

**Files：** Create `inbox.py`、`cli.py`（先只实现 capture 和 status）、`platforms/_common/ai314-lessons`；Test `tests/test_lessons_core.py`

**Interfaces（Produces）：**
- `inbox.Project(root: Path)`：属性 `dir`（`root/.ai314`）；方法：
  - `ensure()`：建目录，并写入内容为 `*` 的 `.gitignore`
  - `disabled() -> bool`
  - `append(items: list[dict], meta: dict)`：每条写入时带 `ts`、`platform`、`session`
  - `items() -> list[dict]`
  - `drop(n: int)`：删除前 n 条
  - `state() -> dict`；`save_state(s: dict)`
  - `lock() -> contextmanager[bool]`：用 O_EXCL 建锁文件，超过 1800s 视为过期锁并接管
- `cli.main(argv: list[str], stdin=sys.stdin, env=os.environ) -> int`
- `cli.capture(platform, raw_stdin, env, foreground: bool) -> int`：处理顺序为
  1. 检查 `AI314_HEADLESS`、mode=off、项目根、disabled
  2. 不是 foreground 时 `os.fork()`，父进程立即返回 0
  3. 加锁
  4. 按 `state["offsets"][transcript]` 增量读取
  5. 抽取信号，追加写入
  6. 若 mode 不为 `capture-only`，调用 `distill.maybe_run(project, cfg, env)`（Task 6 提供；本 Task 先写成 no-op 桩）
- 入口脚本：`#!/usr/bin/env python3`，把脚本所在目录插入 sys.path[0]，然后 `raise SystemExit(cli.main(sys.argv[1:]))`；需带可执行权限

- [ ] Step 1：测试（都用 `--foreground`，项目放在临时 git 仓库）：
  - `test_capture_writes_inbox`：断言 inbox 行数、字段，以及 `.ai314/.gitignore` 的内容为 `*`
  - `test_capture_incremental`：连续调用两次，行数不变
  - `test_capture_skips_non_git`
  - `test_missing_transcript`
  - `test_headless_noop`：设置 `AI314_HEADLESS=1` 时不创建 `.ai314`
  - `test_lock_prevents_double`：锁被占用时直接返回，不写入
  - `test_entry_script_runs`：用 subprocess 执行入口脚本 `status`，退出码为 0
- [ ] Step 2：FAIL
- [ ] Step 3：实现
- [ ] Step 4：PASS
- [ ] Step 5：commit `feat(lessons): add inbox and capture hook command`

### Task 4：构建与 hook 注册

**Files：** Modify `platforms/claude/adapter.py`、`platforms/antigravity/adapter.py`、`build/ai314build/build.py`、`tests/test_adapters.py`；Create `platforms/_common/config.example.toml`

**Interfaces：**
- 两个 adapter 都调用新的 `copy_lessons(out_dir/"hooks")`。该函数放在 `build.py` 中，和 `copy_skills` 并列：用 `shutil.copytree`（忽略 `__pycache__`）复制 `lessons/`，再复制 `ai314-lessons` 和 `config.example.toml`
- claude 的 `hooks.json` 增加：`"Stop": [{"hooks": [{"type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/ai314-lessons\" capture --platform claude"}]}]`
- antigravity 的 `hooks.json` 在 `ai314` 分组下增加 `"Stop"`，命令为 `f="$HOME/.gemini/config/plugins/ai314/hooks/ai314-lessons"; [ -x "$f" ] && "$f" capture --platform antigravity >/dev/null 2>&1; echo '{}'`，`timeout` 为 5
- `build_all` 写入 `out/.gitignore`，内容为 `config.toml\ndata/\n`

- [ ] Step 1：测试：
  - `test_claude_stop_hook`：hooks 中包含 Stop，命令里有 `ai314-lessons" capture --platform claude`，入口文件可执行，`hooks/lessons/cli.py` 存在
  - `test_agy_stop_hook`：同上
  - `test_dist_gitignore`
- [ ] Step 2：FAIL
- [ ] Step 3：实现
- [ ] Step 4：`make check` → 全绿（包含两端的 plugin validate）
- [ ] Step 5：commit `feat(build): ship lessons runtime and register Stop hooks`

### Task 5：netcheck + runner + backoff

**Files：** Create `netcheck.py`、`runner.py`、`backoff.py`；Test `tests/test_lessons_runner.py`

**Interfaces（Produces）：**
- `netcheck.child_env(network: dict, env) -> dict`：在 env 基础上，把 network 中非空的项同时写成大写和小写两种变量名，并加上 `AI314_HEADLESS=1`
- `netcheck.probe(url: str, env: dict, timeout=5) -> bool`：用 urllib 的 ProxyHandler，代理从 env 中取，并遵守 no_proxy；收到 HTTPError 也算连通
- `runner.RunError(kind: str, detail: str)`：异常，kind 取值 `network|auth|no_runner|bad_output`
- `runner.resolve(agent: dict, env) -> tuple[str, str]`（返回 runner 名和 bin 路径）：`auto` 时按 `claude→tclaude→agy→codex` 的顺序查找；在 `shutil.which` 之外，还要查 `~/.local/bin`、`/opt/homebrew/bin`、`/usr/local/bin`。找不到时抛 `RunError("no_runner")`
- `runner.build(name, bin, agent, prompt) -> tuple[list[str], str | None]`（返回 argv 和 stdin）：
  - claude/tclaude：`[bin, "-p", "--output-format", "json", ("--model", m)?, *extra]`，prompt 走 stdin
  - agy：`[bin, "--output-format", "json", "--print-timeout", f"{timeout}s", "--disable-slash-commands", ("--model", m)?, *extra, "-p", prompt]`，stdin 为 None（真机已验证：prompt 必须作为 `-p` 的参数紧跟其后）
  - codex：`[bin, "exec", ("-c", f'model="{m}"')?, "--sandbox", "read-only", *extra, "-"]`，prompt 走 stdin
- `runner.default_probe(name, env) -> str`：claude/tclaude 用 `ANTHROPIC_BASE_URL`，没有时用 `https://api.anthropic.com`；agy 用 `https://daily-cloudcode-pa.googleapis.com`（真机抓到的 agy 实际访问主机）；codex 用 `https://api.openai.com`
- `runner.unwrap(name, stdout) -> str`：
  - claude：取 `json.result`；`is_error` 为真时按 result 文本分类并抛错
  - agy：`status=="SUCCESS"` 时取 `response`，否则按 `error` 分类并抛错
  - codex：原样返回
- `runner.extract_json(text) -> dict`：先剥掉 ``` 代码块，再找第一个括号配对完整的 `{…}`；失败抛 `RunError("bad_output")`
- `runner.classify(text) -> str`：
  - 命中 network 关键词（`EOF|timeout|timed out|connection|dial tcp|proxy|ECONNREFUSED|ENOTFOUND|SSL|TLS|network|Eligibility check failed`）返回 network
  - 命中 auth 关键词（`401|unauthorized|not logged|login|authenticat|credential|api key`）返回 auth
  - 其余返回 bad_output
- `runner.ask(prompt: str, cfg: Config, stage: str, env, cwd: Path) -> dict`：依次 resolve → child_env → probe（失败抛 network）→ `subprocess.run`（超时抛 network）→ unwrap → extract_json
- `backoff.blocked(stage, env) -> str | None`：返回仍在退避中的 kind，否则 None
- `backoff.fail(stage, kind, env)`：network/auth/no_runner 按 `min(3600·2^(n-1), 86400)` 秒退避；bad_output 第 1 次不退避，第 2 次起退避 86400 秒
- `backoff.ok(stage, env)`：清除退避状态

- [ ] Step 1：测试：
  - `test_build_argv_each_runner`：4 种 runner 生成的 argv 和 stdin 全部精确断言
  - `test_child_env_proxy_cases`：断言 `HTTPS_PROXY` 和 `https_proxy` 都存在，且 `AI314_HEADLESS=="1"`
  - `test_auto_resolve_order`：用临时目录放桩可执行文件 tclaude 和 agy，结果应选中 tclaude
  - `test_unwrap_claude` / `test_unwrap_agy`：agy 用真机样本 `{"status":"SUCCESS","response":"{\"ok\":1}\n"}`，以及 ERROR 样本 `"Eligibility check failed: Post ...: EOF"`，后者应得到 network
  - `test_extract_json_fenced`
  - `test_probe_unreachable`：访问 `http://127.0.0.1:9` 返回 False
  - `test_ask_network_no_call`：probe 打桩为 False 时抛 network，且桩 bin 没有被调用（用标记文件判断）
  - `test_backoff_schedule`
- [ ] Step 2：FAIL
- [ ] Step 3：实现
- [ ] Step 4：PASS
- [ ] Step 5：commit `feat(lessons): add configurable headless runner with proxy and backoff`

### Task 6：store + distill

**Files：** Create `store.py`、`distill.py`；Modify `cli.py`（把桩换成实际实现，并新增 `distill` 子命令）；Test `tests/test_lessons_distill.py`

**Interfaces（Produces）：**
- `store.Lesson`：dataclass，字段 `id, title, scene, symptom, fix, owner, rule, count, last`
- `store.OkDefault`：dataclass，字段 `question, suggest, count`
- `store.load(path) -> tuple[list[Lesson], list[OkDefault]]`
- `store.save(path, lessons, oks, archive_path)`：渲染格式按 spec 4.3；每条反面经验有"场景/表现/正确做法/通用规则/归属/最近"6 个 bullet，按 count 降序；渲染结果超过 150 行时，把 count 最低且 `last` 早于 30 天前的条目移到 archive
- `store.global_append(owner: str, records: list[dict], env)`：写入 `data/lessons/<owner>.jsonl`。记录字段为 `rule, project, count, date, status="pending"`；ok 类记录使用 `question, suggest`，owner 为 `ok-defaults`
- `store.global_pending(env) -> dict[str, list[dict]]`；`store.global_mark(owner, idxs, status, env)`
- `distill.should_run(items: list[dict], cfg) -> bool`：非 ok 的条目数 ≥ `distill_min`，或"最早一条超过 7 天且总数 ≥3"
- `distill.maybe_run(project, cfg, env) -> None`：在 should_run 为真且 `backoff.blocked("distill")` 为假时调用 `run`
- `distill.run(project, cfg, env) -> bool`：
  1. 构造 prompt，内容包括 inbox 条目、现有条目索引、可选 owner（插件 `skills/` 下的目录名，加上 `L0`、`project`、`new-stack:<特征>`）、输出 schema
  2. 调用 `runner.ask(..., stage="distill", cwd=tempdir)`
  3. 校验：owner 合法；`merge` 的 id 存在；`new` 的必填字段齐全
  4. 合并后保存；非 project 的条目写入全局库；ok_patterns 写入 `ok-defaults`；`projects.json` 记录 id 到 `{path, name}` 的映射
  5. 调用 `inbox.drop(n)`，再调用 `backoff.ok`
  6. 最后调用 `contribute.maybe_run(cfg, env)`（Task 7 提供，本 Task 先写成 no-op）

  任何 RunError 都执行 `backoff.fail` 并写日志，返回 False，inbox 不动。
- `docs/ai314/lessons.md` 文件头固定为 `# 项目经验（AI314 自动维护，可手改）`

- [ ] Step 1：测试（桩 runner 用 `cfg.agent["bin"]` 指向一个脚本，按 claude 格式输出固定 JSON）：
  - `test_should_run_thresholds`
  - `test_distill_merge_and_new`：已有 L-001（×2）时，执行 merge `add_count=2` 加一条 new，结果为 L-001×4 和新增的 L-002；inbox 被清空
  - `test_distill_global_and_ok`：全局库 `stack-go-microservice.jsonl` 新增 1 条 pending 记录，`ok-defaults.jsonl` 新增 1 条
  - `test_distill_bad_output_keeps_inbox`
  - `test_distill_invalid_owner_rejected`
  - `test_store_roundtrip`：手改过的 md 再 load 一次，内容不丢
  - `test_archive_over_150_lines`
- [ ] Step 2：FAIL
- [ ] Step 3：实现
- [ ] Step 4：PASS
- [ ] Step 5：commit `feat(lessons): distill inbox into project lessons and global library`

### Task 7：contribute + sampler

**Files：** Create `contribute.py`、`sampler.py`；Modify `cli.py`（新增 `contribute` 子命令）；Test `tests/test_lessons_contrib.py`

**Interfaces（Produces）：**
- `contribute.target(owner: str) -> tuple[str, str]`（返回目标文件和允许写入的目录）：
  - `L0` → `content/L0-constitution/AGENTS.base.md`
  - `stack-x` → `content/L1-stacks/stack-x/SKILL.md`
  - `mode-x` → `content/L2-modes/mode-x/SKILL.md`
  - `ok-defaults` → `content/L0-constitution/skills/planning/SKILL.md`
  - `new-stack:x` → `content/L1-stacks/stack-x/SKILL.md`（这是新建文件）
- `contribute.ready(pending: dict, cfg, env) -> list[str]`：返回可以回流的 owner。普通 owner 需要 pending 数 ≥ `contrib_min` 且距上次回流 ≥24h（时间记录在 `data/contrib.json`）；`new-stack:*` 需要 pending 数 ≥5 且来自 ≥2 个不同 project
- `contribute.maybe_run(cfg, env)`：满足以下全部条件才继续：`lessons.contribute` 为真、`src` 存在、`gh auth status` 返回 0、持有全局锁 `data/contrib.lock`、`backoff.blocked("contribute")` 为假。之后逐个 owner 调用 `run_owner`
- `contribute.run_owner(owner, records, cfg, env) -> str | None`（返回 PR url）：
  1. `git -C src fetch origin main`
  2. `git -C src worktree add -b lessons/<owner 中 ':' 替换为 '-'>-<YYYYMMDD-HHMM> data/worktrees/<同名> origin/main`
  3. 构造 prompt，内容包括目标文件全文（不存在则为空）、编号后的 records、contribute 技能中的去业务化和硬约束要求，以及 new-stack 时 `sampler.sample(project_path)` 的结果；输出 schema 为 `{files:[{path,content}], adopted:[int], pending:[int], title:str}`
  4. `runner.ask(stage="contribute", cwd=worktree)`
  5. 校验每个 path 都在允许写入的目录内，不在则抛 `RunError("bad_output")`；files 为空时清理并返回 None
  6. 写入文件，执行 `make check CLAUDE_BIN=__none__ AGY_BIN=__none__`，超时 600s。失败时记为 `check_failed`：清理 worktree 和分支，并写日志
  7. 用 `git -c user.*`（沿用 src 仓库的身份配置）执行 commit，提交信息为 `feat(<scope>): <title>`。scope：L0 为 `constitution`，ok-defaults 为 `planning`，new-stack 为 `stack-x`，其余为 owner 名
  8. 推送。`gh api repos/<upstream> --jq .permissions.push` 为 `true` 时执行 `git push origin HEAD:<branch>`；否则先执行 `gh repo fork <upstream> --clone=false`，再推送到 `https://github.com/<login>/<repo>.git`，head 写成 `<login>:<branch>`
  9. `gh pr create --repo <upstream> --base main --head <head> --title ... --body ...`。L0 和 new-stack 加 `--draft`。body 中按匿名 project id 列出次数
  10. `store.global_mark(adopted, "submitted")`，更新 `contrib.json`，移除 worktree（分支保留）
- `sampler.sample(root: Path, limit=60_000) -> str`：按依赖清单 → 目录树（3 层，忽略隐藏目录和 node_modules）→ Makefile/lint 配置 → 最多 4 个核心源文件（按大小选中位数附近的）的顺序采样，总长不超过 limit

- [ ] Step 1：测试（本地 bare 仓库作为 origin，src 为它的 clone，其中放一个最小 Makefile，`check:` 目标的退出码由环境变量控制；用 PATH 前置的桩 `gh` 记录收到的参数，用桩 runner 返回 files）：
  - `test_contrib_disabled_by_default`：桩 gh 没有被调用
  - `test_contrib_pr_flow_push`：分支被推送到 bare 仓库；gh 收到的参数包含 `pr create --repo lupguo/AI314`，且 body 中有 `p-` 开头的 id；被采纳的记录状态变为 submitted；src 仓库的当前分支没有变化
  - `test_contrib_fork_flow`：permissions.push 为 false 时依次走 `repo fork` 和 `--head <login>:`
  - `test_check_failed_no_pr`
  - `test_rejects_path_escape`
  - `test_draft_for_l0`
  - `test_new_stack_ready_rule`
  - `test_sampler_limit`
- [ ] Step 2：FAIL
- [ ] Step 3：实现
- [ ] Step 4：PASS
- [ ] Step 5：commit `feat(lessons): auto-contribute mature lessons as PRs`

### Task 8：status / doctor + 内容与文档

**Files：** Modify `cli.py`（status 输出完整内容，新增 doctor）、`content/L0-constitution/AGENTS.base.md`、`content/tools/contribute/SKILL.md`、`content/tools/extract-stack/SKILL.md`、`README.md`；Test `tests/test_lessons_runner.py`

- `status`：输出生效的配置（代理只显示 host）、runner 名和 bin 路径、当前项目的 inbox 条数、退避状态、`projects.json` 中的映射
- `doctor`：依次输出 `network: ok|fail`（probe）、`runner: ok|fail <detail>`（用 prompt `Reply with exactly this JSON and nothing else: {"ok":1}` 调用 ask，结果必须是 `{"ok":1}`）。全部通过返回 0，否则返回 1
- 宪法 §零 在"与流程技能协作"之后增加一条：`- **项目经验**：项目存在 docs/ai314/lessons.md 时，开工前先阅读并避免其中的反面经验；其中"可默认放行的提问"直接采用默认值，不再询问。`
- contribute 技能增加一步：先读 `docs/ai314/lessons.md` 和 `~/.ai314/data/lessons/`，作为证据来源。extract-stack 技能的扫描顺序增加第 5 步：读取 lessons 中与本技术栈相关的条目，作为"反面禁令"的依据。
- README：增加"经验闭环"一小节，写明配置文件位置、开关、`status`/`doctor` 命令；远程安装命令改为 `git init ~/.ai314 && git -C ~/.ai314 fetch <repo> dist && git -C ~/.ai314 checkout -b dist FETCH_HEAD`（并设置 origin）
- [ ] Step 1：测试 `test_doctor_stub_ok`（使用桩 runner）、`test_status_masks_proxy`
- [ ] Step 2：FAIL → Step 3：实现 → Step 4：`make check` 全绿
- [ ] Step 5：commit `feat(lessons): add status/doctor and wire constitution + docs`

### Task 9：验收（真机）

- [ ] 写入 `~/.ai314/config.toml`，内容为测试环境配置：agy + `http://127.0.0.1:8118` + `gemini-4-hydrogen-medium`，`contribute=false`
- [ ] 执行 `make install-agy`。在临时 git 项目中先跑 `ai314-lessons doctor`，再用 agy 跑几轮包含纠正、OK、测试失败的对话，检查 `.ai314/inbox.jsonl` 的内容
- [ ] 模拟回流：用一个临时 `AI314_HOME`，`src` 指向一个临时 clone，其 origin 为本地 bare 仓库，gh 用桩；向 inbox 注入达到阈值的测试信号，以 foreground 方式运行，依次检查 lessons.md、全局库，以及桩 gh 收到的 `pr create` 参数
- [ ] 清理测试信号、临时 HOME 和测试项目；将结果记录到 `docs/smoke/2026-11-27-lessons-loop.md`
- [ ] 执行 `ai314:code-review` 自查，然后 commit

## 公开接口变更 / docs/base 影响

接口变更与 spec §6 相同。仓库没有 `docs/base/`，因此不需要回写，只更新 README。

## 执行方式

在当前会话中原生执行（Native）。理由：9 个任务之间的接口串联很紧，调用链是 capture → distill → contribute，而且真机验收需要沿用当前会话中已经验证过的环境细节，比如 agy alias 和沙箱。全部完成后，派一个独立 reviewer 审查整个分支。
