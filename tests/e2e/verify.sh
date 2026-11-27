#!/usr/bin/env bash
# 端到端验收：在真实 Agent 中确认 AI314 插件生效。
# 用法：tests/e2e/verify.sh <agy|tclaude|claude> <期望版本 x.y.z> [期望出现在宪法中的短语]
# 在临时 git 仓库中以非交互模式提问，断言输出含期望的宪法版本行、技能可用、可选短语。
set -uo pipefail
AGENT="${1:?agent}"; VERSION="${2:?version}"; PHRASE="${3:-}"
LOG_DIR="${AI314_E2E_LOG:-$(cd "$(dirname "$0")/../.." && pwd)/.superpowers/e2e}"
mkdir -p "$LOG_DIR"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
git -C "$WORK" init -q

Q="不要调用任何工具，只根据你当前上下文中已加载的 AI314 宪法与可用技能回答，严格按 3 行输出：
VERSION=<宪法中 'AI314 宪法版本：' 后面的版本号，原样>
SKILL=<可用技能中是否有 stack-go-microservice，yes 或 no>
QUOTE=<宪法第 3 条（架构设计）的最后一句话，原样>"

case "$AGENT" in
  agy) (cd "$WORK" && agy -p "$Q" --print-timeout 300s) ;;
  tclaude|claude) (cd "$WORK" && "$AGENT" -p "$Q") ;;
  *) echo "未知 agent: $AGENT" >&2; exit 2 ;;
esac > "$LOG_DIR/$AGENT-v$VERSION.out" 2>&1
OUT="$(cat "$LOG_DIR/$AGENT-v$VERSION.out")"
echo "----- $AGENT 输出 -----"; echo "$OUT"; echo "-----------------------"

fail=0
grep -Eq "VERSION=v?${VERSION//./\\.}\b" <<<"$OUT" && echo "✅ 宪法版本 v$VERSION" || { echo "❌ 未读到宪法版本 v$VERSION"; fail=1; }
grep -Eq "SKILL=yes" <<<"$OUT" && echo "✅ 技能 stack-go-microservice 可用" || { echo "❌ 技能不可用"; fail=1; }
if [[ -n "$PHRASE" ]]; then
  grep -Fq "$PHRASE" <<<"$OUT" && echo "✅ 宪法新内容可见：$PHRASE" || { echo "❌ 未见宪法新内容：$PHRASE"; fail=1; }
fi
exit $fail
