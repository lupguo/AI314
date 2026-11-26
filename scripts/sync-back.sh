#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# AI314 (github.com/lupguo/AI314) 经验反向同步与质检脚本
# 用法:
#   ./sync-back.sh                        # 自动扫描当前项目 .agents/skills/stack-* 并同步
#   ./sync-back.sh path/to/SKILL.md       # 指定单个 SKILL.md 文件同步
#   ./sync-back.sh --force                # 跳过部分警告强制同步
# ==============================================================================

DEFAULT_HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HUB_DIR="${AI314_HUB:-$DEFAULT_HUB_DIR}"
FORCE=false
TARGET_FILES=()

for arg in "$@"; do
  case $arg in
    --force)
      FORCE=true
      shift
      ;;
    -h|--help)
      echo "用法: $0 [path/to/SKILL.md] [--force]"
      echo "说明: 将业务项目中沉淀或更新的 stack-* SKILL.md 质检后同步回 $HUB_DIR/stacks/"
      exit 0
      ;;
    *)
      if [[ -f "$arg" ]]; then
        TARGET_FILES+=("$arg")
      else
        echo "❌ 错误: 找不到指定文件 [$arg]"
        exit 1
      fi
      ;;
  esac
done

if [[ ! -d "$HUB_DIR/stacks" ]]; then
  echo "❌ 错误: 中央仓库目录不存在 ($HUB_DIR/stacks)"
  exit 1
fi

if [[ ${#TARGET_FILES[@]} -eq 0 ]]; then
  if [[ -d ".agents/skills" ]]; then
    while IFS= read -r -d '' file; do
      TARGET_FILES+=("$file")
    done < <(find .agents/skills -maxdepth 2 -path "*/stack-*/SKILL.md" -print0)
  fi
fi

if [[ ${#TARGET_FILES[@]} -eq 0 ]]; then
  echo "⚠️  未在当前项目发现任何 stack-*/SKILL.md 文件。"
  echo "提示: 如果是新提炼的规范，请先保存至 .agents/skills/stack-<name>/SKILL.md 或直接传入文件路径。"
  exit 0
fi

validate_skill() {
  local file="$1"
  local errors=0
  local warnings=0

  echo "🔍 正在质检: $file"

  if ! head -n 1 "$file" | grep -qx "---"; then
    echo "  ❌ [格式错误] 文件首行必须为 YAML Frontmatter 分隔符 '---'"
    ((errors++))
  fi

  local skill_name
  skill_name=$(awk '/^---$/{p++;next} p==1 && /^name:/{sub(/^name:[[:space:]]*/, ""); print; exit}' "$file" | tr -d '"' | tr -d "'")
  if [[ -z "$skill_name" ]]; then
    echo "  ❌ [元数据缺失] Frontmatter 中缺少 'name:' 字段"
    ((errors++))
  elif [[ ! "$skill_name" =~ ^stack-[a-z0-9-]+$ ]]; then
    echo "  ❌ [命名不规范] name='$skill_name' 必须符合 'stack-<小写字母/数字/短横线>' 格式"
    ((errors++))
  fi

  local skill_desc
  skill_desc=$(awk '/^---$/{p++;next} p==1 && /^description:/{sub(/^description:[[:space:]]*/, ""); print; exit}' "$file")
  if [[ -z "$skill_desc" || ${#skill_desc} -lt 10 ]]; then
    echo "  ❌ [元数据缺失] Frontmatter 中 'description:' 缺失或过短（影响路由触发）"
    ((errors++))
  fi

  local required_sections=("## 1." "## 2." "## 3." "## 4.")
  for sec in "${required_sections[@]}"; do
    if ! grep -q "^${sec}" "$file"; then
      echo "  ❌ [结构残缺] 缺少标准章节标题 '${sec} ...'（需包含：技术栈/目录拓扑/编码红线/自检命令）"
      ((errors++))
    fi
  done

  local line_count
  line_count=$(wc -l < "$file" | xargs)
  if [[ "$line_count" -gt 220 ]]; then
    echo "  ⚠️  [体积警告] 当前共 ${line_count} 行（建议控制在 80~180 行以保持高信噪比）"
    ((warnings++))
  fi

  if grep -Eqi "(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|password[[:space:]]*=[[:space:]]*['"][^'"]+)" "$file"; then
    echo "  ❌ [安全红线] 检测到疑似硬编码密钥或敏感凭证，严禁同步至中央仓库！"
    ((errors++))
  fi

  if [[ "$errors" -gt 0 ]]; then
    echo "  🚫 质检未通过（共 $errors 项错误），已阻止同步。"
    return 1
  fi

  if [[ "$warnings" -gt 0 && "$FORCE" == false ]]; then
    echo "  ⚠️  存在 $warnings 项警告，如需忽略警告强行同步请附加 --force 参数。"
    return 1
  fi

  VALIDATED_SKILL_NAME="$skill_name"
  return 0
}

SYNCED_COUNT=0

for file in "${TARGET_FILES[@]}"; do
  VALIDATED_SKILL_NAME=""
  if ! validate_skill "$file"; then
    continue
  fi

  stack_dir_name="${VALIDATED_SKILL_NAME#stack-}"
  dest_dir="$HUB_DIR/stacks/$stack_dir_name"
  dest_file="$dest_dir/SKILL.md"

  mkdir -p "$dest_dir"

  if [[ -f "$dest_file" ]]; then
    if cmp -s "$file" "$dest_file"; then
      echo "  ✨ [$stack_dir_name] 内容与中央仓库完全一致，无需更新。"
      continue
    else
      echo "  📝 检测到 [$stack_dir_name] 有增量更新，差异预览如下："
      diff -u "$dest_file" "$file" | head -n 30 || true
      cp "$file" "$dest_file"
      echo "  ✅ 已覆盖更新: $dest_file"
      ((SYNCED_COUNT++))
    fi
  else
    cp "$file" "$dest_file"
    echo "  🆕 已新增技术栈规范: $dest_file"
    ((SYNCED_COUNT++))
  fi
done

if [[ "$SYNCED_COUNT" -gt 0 ]]; then
  echo ""
  echo "🎉 共同步 $SYNCED_COUNT 份规范至 $HUB_DIR/stacks/。"
  if [[ -d "$HUB_DIR/.git" ]]; then
    echo "💡 建议执行以下命令提交经验版本至 github.com/lupguo/AI314："
    echo "   git -C "$HUB_DIR" status -s"
    echo "   git -C "$HUB_DIR" add stacks/ && git -C "$HUB_DIR" commit -m "chore(skills): sync stack specs from $(basename "$(pwd)")""
  fi
fi
