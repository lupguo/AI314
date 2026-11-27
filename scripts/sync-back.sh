#!/usr/bin/env bash
# 把旧版 init-project.sh 装配项目中被修改过的 stack-*/mode-* 副本，质检后回流到 AI314 源码仓库的新分支。
# 用法：AI314_SRC=~/.ai314-src scripts/sync-back.sh <副本目录>... [--force]
# 之后在源码仓库中 `make check`、提交并 `gh pr create`（见 ai314:contribute）。
set -euo pipefail
SRC="${AI314_SRC:-$HOME/.ai314-src}"
FORCE=false
DIRS=()
for a in "$@"; do
  case "$a" in
    --force) FORCE=true ;;
    -h|--help) sed -n '2,4p' "$0"; exit 0 ;;
    *) [[ -d "$a" ]] || { echo "❌ 不是目录: $a" >&2; exit 1; }; DIRS+=("$a") ;;
  esac
done
[[ ${#DIRS[@]} -gt 0 ]] || { echo "❌ 请指定至少一个 stack-*/mode-* 目录" >&2; exit 1; }
[[ -d "$SRC/.git" && -d "$SRC/content" ]] || { echo "❌ AI314 源码仓库不存在: $SRC" >&2; exit 1; }

validate() {  # $1=目录 $2=技能名；输出错误并返回非 0
  local dir="$1" name="$2" md="$1/SKILL.md" errs=0
  [[ -f "$md" ]] || { echo "  ❌ 缺少 SKILL.md"; return 1; }
  [[ "$(head -n1 "$md")" == "---" ]] || { echo "  ❌ 首行必须是 frontmatter '---'"; errs=$((errs+1)); }
  local fm_name desc
  fm_name=$(awk '/^---$/{c++;next} c==1 && /^name:/{sub(/^name:[[:space:]]*/,"");print;exit}' "$md")
  desc=$(awk '/^---$/{c++;next} c==1 && /^description:/{sub(/^description:[[:space:]]*/,"");print;exit}' "$md")
  [[ "$fm_name" == "$name" ]] || { echo "  ❌ name '$fm_name' 与目录名 '$name' 不一致"; errs=$((errs+1)); }
  [[ ${#desc} -ge 10 ]] || { echo "  ❌ description 缺失或过短"; errs=$((errs+1)); }
  if [[ "$name" == stack-* ]]; then
    for sec in "## 1." "## 2." "## 3." "## 4."; do
      grep -q "^${sec}" "$md" || { echo "  ❌ 缺少章节 '${sec}'"; errs=$((errs+1)); }
    done
  fi
  if grep -rEqi "(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|password[[:space:]]*=[[:space:]]*['\"][^'\"]+)" "$dir"; then
    echo "  ❌ 检测到疑似硬编码密钥"; errs=$((errs+1))
  fi
  local lines; lines=$(wc -l < "$md" | tr -d ' ')
  if [[ "$lines" -gt 220 && "$FORCE" == false ]]; then echo "  ❌ 共 ${lines} 行，超过 220（--force 忽略）"; errs=$((errs+1)); fi
  return $errs
}

# 先全部质检，任何一个失败都不动源码仓库
for d in "${DIRS[@]}"; do
  name="$(basename "$d")"
  case "$name" in stack-*|mode-*) ;; *) echo "❌ 目录名必须以 stack- 或 mode- 开头: $name" >&2; exit 1 ;; esac
  echo "🔍 质检 $name"
  validate "$d" "$name" || { echo "🚫 质检未通过，已中止" >&2; exit 1; }
done

[[ -z "$(git -C "$SRC" status --porcelain)" ]] || { echo "❌ 源码仓库有未提交修改: $SRC" >&2; exit 1; }
branch="contrib/sync-back-$(date +%Y%m%d%H%M%S)"
git -C "$SRC" switch -q -c "$branch"
for d in "${DIRS[@]}"; do
  name="$(basename "$d")"
  layer="L1-stacks"; [[ "$name" == mode-* ]] && layer="L2-modes"
  dest="$SRC/content/$layer/$name"
  rm -rf "$dest"; mkdir -p "$dest"
  cp -R "$d/." "$dest/"
  echo "  ✅ $name → content/$layer/$name"
done
echo "🎉 已写入分支 $branch。下一步：cd $SRC && make check && git add -A && git commit && gh pr create"
