# AI314 构建入口。所有内容在 content/，平台适配在 platforms/，产物在 dist/（勿手改）。
SHELL := /bin/bash
PY ?= python3
BUILD := PYTHONPATH=build $(PY) -m ai314build
DIST ?= dist
PLATFORMS ?= claude,antigravity
CLAUDE_BIN ?= tclaude
AGY_BIN ?= agy
# agy 访问网络需要代理时：make install-agy AGY_ENV="https_proxy=http://127.0.0.1:8118"
AGY_ENV ?=
AGY := env $(AGY_ENV) $(AGY_BIN)
NAME := $(shell sed -n 's/^name *= *"\(.*\)"/\1/p' ai314.toml | head -1)
VERSION := $(shell sed -n 's/^version *= *"\(.*\)"/\1/p' ai314.toml | head -1)

.PHONY: help build validate test check verify-dist install install-claude install-agy uninstall release clean

help:
	@echo "make build | check | install | install-claude | install-agy | release NEW=x.y.z NOTE='...' | clean"

validate:
	@$(BUILD) validate

build:
	@$(BUILD) build --out $(DIST) --platforms $(PLATFORMS)

test:
	@cd tests && PYTHONPATH=../build:.. $(PY) -m unittest -q

# 产物校验：对应 CLI 不存在时跳过
verify-dist: build
	@if command -v $(CLAUDE_BIN) >/dev/null; then $(CLAUDE_BIN) plugin validate $(DIST) && $(CLAUDE_BIN) plugin validate $(DIST)/claude; else echo "跳过: 未找到 $(CLAUDE_BIN)"; fi
	@if command -v $(AGY_BIN) >/dev/null; then $(AGY) plugin validate --strict $(DIST)/antigravity; else echo "跳过: 未找到 $(AGY_BIN)"; fi

check: validate test verify-dist
	@echo "✅ check 通过 (v$(VERSION))"

# CC 系客户端：目录型 marketplace 原地加载 dist/claude，重建后下次会话即生效
install-claude: validate test build
	@if $(CLAUDE_BIN) plugin marketplace list 2>/dev/null | grep -q "$(NAME)"; then \
	  $(CLAUDE_BIN) plugin marketplace update $(NAME); \
	else \
	  $(CLAUDE_BIN) plugin marketplace add "$(abspath $(DIST))"; \
	fi
	@if $(CLAUDE_BIN) plugin list 2>/dev/null | grep -q "$(NAME)@$(NAME)"; then \
	  $(CLAUDE_BIN) plugin update $(NAME)@$(NAME); \
	else \
	  $(CLAUDE_BIN) plugin install $(NAME)@$(NAME); \
	fi
	@echo "✅ $(CLAUDE_BIN) 已安装 $(NAME) v$(VERSION)（新会话生效）"

# AGY 无 update 命令：卸载后重装
install-agy: validate test build
	@$(AGY) plugin uninstall $(NAME) >/dev/null 2>&1 || true
	@$(AGY) plugin install "$(abspath $(DIST))/antigravity"
	@echo "✅ $(AGY_BIN) 已安装 $(NAME) v$(VERSION)"

install: install-claude install-agy

uninstall:
	-@$(CLAUDE_BIN) plugin uninstall $(NAME)@$(NAME)
	-@$(CLAUDE_BIN) plugin marketplace remove $(NAME)
	-@$(AGY) plugin uninstall $(NAME)

# 发布：改版本与 CHANGELOG → 全量校验 → 提交并打 tag
release:
	@test -n "$(NEW)" || { echo "用法: make release NEW=x.y.z NOTE='变更说明'"; exit 1; }
	@test -z "$$(git status --porcelain)" || { echo "❌ 工作区不干净：请先提交内容改动，再发布版本"; exit 1; }
	@! git rev-parse -q --verify "refs/tags/v$(NEW)" >/dev/null || { echo "❌ tag v$(NEW) 已存在"; exit 1; }
	@$(PY) scripts/release.py "$(NEW)" "$(NOTE)"
	@$(MAKE) --no-print-directory check || { \
	  git checkout -- ai314.toml; \
	  if git ls-files --error-unmatch CHANGELOG.md >/dev/null 2>&1; then git checkout -- CHANGELOG.md; else rm -f CHANGELOG.md; fi; \
	  echo "❌ check 失败，已回滚版本号与 CHANGELOG"; exit 1; }
	@git add ai314.toml CHANGELOG.md && git commit -qm "chore(release): v$(NEW)" && git tag "v$(NEW)"
	@echo "✅ 已发布 v$(NEW)（commit + tag）。运行 make install 让本机两端加载新版本"

clean:
	rm -rf $(DIST)
