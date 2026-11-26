#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# AI314 (github.com/lupguo/AI314) 项目规范一键装配脚本
# 用法: ./init-project.sh --stacks=go-microservice,web-admin [--modes=exploration-mvp] [--target=/path/to/project]
# ==============================================================================

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$(pwd)"
STACKS_ARG=""
MODES_ARG=""

for arg in "$@"; do
  case $arg in
    --stacks=*)
      STACKS_ARG="${arg#*=}"
      shift
      ;;
    --modes=*)
      MODES_ARG="${arg#*=}"
      shift
      ;;
    --target=*)
      TARGET_DIR="${arg#*=}"
      shift
      ;;
    -h|--help)
      echo "用法: $0 --stacks=<stack1,stack2> [--modes=<mode1>] [--target=<dir>]"
      echo "可用 Stacks: $(ls -1 "$HUB_DIR/stacks" 2>/dev/null | tr '
' ' ')"
      echo "可用 Modes:  $(ls -1 "$HUB_DIR/modes" 2>/dev/null | tr '
' ' ')"
      exit 0
      ;;
    *)
      echo "❌ 未知参数: $arg"
      exit 1
      ;;
  esac
done

if [[ -z "$STACKS_ARG" ]]; then
  echo "❌ 错误: 必须通过 --stacks 指定至少一个技术栈 (例如: --stacks=web-admin,crawler-script)"
  exit 1
fi

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

echo "🚀 [AI314] 开始在 [$TARGET_DIR] 装配 VibeCoding 工程规范..."

# 1. 创建标准化文档与技能目录
mkdir -p docs/{00-plans,01-biz,02-prod,03-ui-design,04-arch,05-deploy,_drafts}
mkdir -p .agents/skills scripts

# 2. 复制通用宪法基底
cp "$HUB_DIR/AGENTS.base.md" "./AGENTS.md"

# 3. 注入选定的技术栈 (Stacks)
IFS=',' read -ra STACKS <<< "$STACKS_ARG"
for stack in "${STACKS[@]}"; do
  stack=$(echo "$stack" | xargs)
  SRC_STACK="$HUB_DIR/stacks/$stack"
  
  if [[ ! -d "$SRC_STACK" ]]; then
    echo "⚠️  警告: 未找到技术栈 [$stack]，已跳过。"
    continue
  fi

  DEST_SKILL=".agents/skills/stack-$stack"
  mkdir -p "$DEST_SKILL"
  cp -r "$SRC_STACK/"* "$DEST_SKILL/"

  # 提取 SKILL.md 的 description 写入 AGENTS.md 动态路由表
  DESC=$(grep -m1 '^description:' "$SRC_STACK/SKILL.md" | sed 's/^description:[[:space:]]*//')
  echo "| \`stack-$stack\` | \`.agents/skills/stack-$stack/SKILL.md\` | ${DESC:-开发 $stack 相关模块时必读} |" >> "./AGENTS.md"

  # 如果存在标准 Makefile 模板且当前项目无 Makefile，则自动初始化
  if [[ -f "$SRC_STACK/Makefile.tpl" && ! -f "./Makefile" ]]; then
    cp "$SRC_STACK/Makefile.tpl" "./Makefile"
    echo "  📄 已初始化基础 Makefile (源自 $stack)"
  fi

  echo "  ✅ 已注入技术栈技能: stack-$stack"
done

# 4. 注入选定的研发模式 (Modes)
if [[ -n "$MODES_ARG" ]]; then
  IFS=',' read -ra MODES <<< "$MODES_ARG"
  for mode in "${MODES[@]}"; do
    mode=$(echo "$mode" | xargs)
    SRC_MODE="$HUB_DIR/modes/$mode"

    if [[ ! -d "$SRC_MODE" ]]; then
      echo "⚠️  警告: 未找到研发模式 [$mode]，已跳过。"
      continue
    fi

    DEST_MODE=".agents/skills/mode-$mode"
    mkdir -p "$DEST_MODE"
    cp -r "$SRC_MODE/"* "$DEST_MODE/"

    DESC=$(grep -m1 '^description:' "$SRC_MODE/SKILL.md" | sed 's/^description:[[:space:]]*//')
    echo "| \`mode-$mode\` | \`.agents/skills/mode-$mode/SKILL.md\` | ${DESC:-处于 $mode 模式时覆盖默认规则} |" >> "./AGENTS.md"

    echo "  ✅ 已注入研发模式补丁: mode-$mode"
  done
fi

# 5. 建立兼容性符号链接与安全忽略规则
if [[ ! -e ".claude" ]]; then
  mkdir -p .claude
  ln -s ../.agents/skills .claude/skills
fi

if [[ ! -f ".gitignore" ]]; then
  touch .gitignore
fi

for ignore_entry in ".env" ".env.*" "docs/_drafts/*.tmp.html"; do
  if ! grep -qxF "$ignore_entry" .gitignore; then
    echo "$ignore_entry" >> .gitignore
  fi
done

echo "🎉 装配完成！请检查根目录 AGENTS.md 与 .agents/skills/ 目录。"
