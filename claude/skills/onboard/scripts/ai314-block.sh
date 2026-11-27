#!/usr/bin/env bash
# 幂等写入 AI314 项目声明块。
# 用法：printf '%s\n' '| `services/**` | ai314:stack-go-microservice |' | ai314-block.sh <项目根>
# 只替换 <!-- AI314:BEGIN --> ~ <!-- AI314:END --> 之间内容，块外字节不变；
# 若存在 CLAUDE.md 且未导入 AGENTS.md，则追加一行 @AGENTS.md。
set -euo pipefail
PROJECT="${1:?用法: ai314-block.sh <项目根>  (表格行从 stdin 读入)}"
ROWS="$(cat)"
if [[ -z "${ROWS//[[:space:]]/}" ]]; then
  echo "❌ 未从 stdin 读到任何 '| 路径 | 技能 |' 表格行" >&2
  exit 1
fi
python3 - "$PROJECT" "$ROWS" <<'PY'
import pathlib, re, sys
project, rows = pathlib.Path(sys.argv[1]), sys.argv[2].strip("\n")
block = (
    "<!-- AI314:BEGIN v=1 -->\n"
    "## AI314 工程规范\n\n"
    "本项目遵循 AI314 规范（插件 ai314，宪法已由插件常驻加载）。修改下列路径前先加载对应技能：\n\n"
    "| 路径范围 | 技能 |\n| :-- | :-- |\n"
    f"{rows}\n"
    "<!-- AI314:END -->"
)
agents = project / "AGENTS.md"
text = agents.read_text(encoding="utf-8") if agents.exists() else ""
pat = re.compile(r"<!-- AI314:BEGIN[^>]*-->.*?<!-- AI314:END -->", re.S)
if pat.search(text):
    text = pat.sub(lambda _: block, text, count=1)
else:
    text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block + "\n"
agents.write_text(text, encoding="utf-8")

claude = project / "CLAUDE.md"
if claude.exists():
    c = claude.read_text(encoding="utf-8")
    if not re.search(r"^@AGENTS\.md\s*$", c, re.M):
        claude.write_text(c.rstrip("\n") + "\n\n@AGENTS.md\n", encoding="utf-8")
print(f"✅ 已写入 AI314 声明块: {agents}")
PY
