---
name: stack-crawler-script
description: 当开发数据采集爬虫、网页抓取、API 逆向自动化或批量数据清洗脚本时强制加载此技能。
---

# 爬虫与自动化采集脚本工程规范

## 1. 钦定技术栈（按场景二选一，禁止混用）
- **高并发 HTTP/API 采集（首选）**：Python 3.12+ + `httpx`（异步模式）+ `tenacity`（指数退避重试）+ `pydantic`（数据结构强校验落盘）。
- **强 JS 渲染/复杂反爬采集**：`Playwright`（异步 API）+ 持久化上下文（Persistent Context），严禁使用已过时的 Selenium。
- **HTML 解析**：`selectolax` 或 `parsel`（CSS/XPath 选择器），禁止用正则硬匹配复杂 HTML 结构。

## 2. 强制目录拓扑与分层边界
```text
├── config/          # 目标站点规则、请求头模板、速率限制配置（严禁放密钥）
├── core/
│   ├── client.py    # 封装带限流器（Semaphore）、代理注入与自动重试的 HTTP/Browser 客户端
│   ├── parser.py    # 纯解析逻辑（输入原始文本/HTML，输出 Pydantic 模型，便于离线单测）
│   └── storage.py   # 幂等落盘适配器（支持 SQLite / PostgreSQL / JSONL 断点续传）
├── spiders/         # 具体站点采集任务编排
├── tests/
│   └── fixtures/    # 保存真实抓回的 HTML/JSON 样本，用于离线测试解析器
└── run.py           # 统一 CLI 入口（支持 --limit, --resume, --dry-run 参数）
```
- **分层铁律**：`core/parser.py` 必须是零网络 I/O 的纯函数，严禁在解析器内部发起二次 HTTP 请求。

## 3. 编码范式与高频避坑红线
- **强制超时与速率控制**：所有网络请求必须显式设置 `connect=10s, read=30s` 超时；必须通过 `asyncio.Semaphore` 限制并发数，并在请求间加入随机抖动延迟（`random.uniform(0.8, 2.5)`），严禁无节制并发打垮目标站点。
- **幂等性与断点续传（Mandatory）**：采集任务必须支持中断后无缝恢复。每条数据必须生成唯一业务指纹（`SHA256` 主键），落盘统一使用 `UPSERT`（`INSERT OR IGNORE` / `ON CONFLICT DO UPDATE`）或本地状态游标记录，禁止重复抓取已成功页面。
- **解析与网络彻底解耦**：开发解析逻辑时，**必须先保存 1 份真实响应到 `tests/fixtures/`，基于本地样本跑通单元测试后再连网全量运行**，严禁反复请求目标网站调试 XPath/CSS 选择器。
- **异常隔离与死信记录**：单条详情页解析失败或触发 403/429 时，严禁中断整个采集进程；必须将失败的 URL、状态码与原始响应片段记录至 `logs/failed_tasks.jsonl`，供后续排查与定点重跑。
- **凭证外部化**：代理池地址（`PROXY_URL`）、登录态 `COOKIE` 或 `AUTH_TOKEN` 一律从 `.env` 读取，严禁写死在代码或 Git 历史中。

## 4. 交付自检命令（完结门禁）
`pytest tests/ && python run.py --dry-run --limit=5`
