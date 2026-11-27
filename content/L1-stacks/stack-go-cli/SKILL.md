---
name: stack-go-cli
description: 当开发或维护以 Go + Cobra 构建、聚合多个第三方 HTTP 上游（分级降级 / 熔断 / 本地缓存）的单二进制命令行工具时强制加载此技能。
---

# Go 多上游聚合 CLI 工程规范

> 状态：草案（自一个已发布的开源 CLI 项目逆向提炼，改进请用 `ai314:contribute` 回流）

## 1. 钦定技术栈（禁止自行替换或重新调研）
- **语言与核心框架**：Go 1.25（以 `go.mod` 的 `go` 指令为准）+ `spf13/cobra` v1.10（参数解析用 `spf13/pflag`）
- **数据存储与缓存**：无持久化存储；缓存为进程内 TTL + LRU（标准库 `container/list` + `sync.Mutex` 自研），不引入第三方缓存库
- **通信、序列化与状态**：HTTP 只用标准库 `net/http`；SOCKS5 代理用 `golang.org/x/net/proxy`；配置用 `gopkg.in/yaml.v3`（字段直接用 `time.Duration`，如 `5m`/`30s`）；输出用 `encoding/json` 带缩进写 stdout
- **可观测与基础设施**：无日志库，告警一律 `fmt.Fprintf(os.Stderr, ...)`；版本号用 `-ldflags "-X main.version=..."` 注入；GitHub Actions 矩阵交叉编译发布 + `install.sh` 一键安装
- **结构化日志 / 可观测**：[待补充]

## 2. 强制目录拓扑与分层边界
```text
cmd/<bin>/main.go        # 入口：Cobra 参数、构建 http.Client、调用 Manager、格式化输出（仅装配）
internal/
  model/                 # 统一领域模型（纯 struct + json tag），不依赖任何内部包
  config/                # 配置 struct、Load、内置默认值与回写（DefaultConfig / WriteDefault）
  provider/              # 上游适配层
    provider.go          #   Provider 接口契约（Name / Query）
    manager.go           #   分级路由 + 组内随机 + 熔断 + 缓存编排
    <upstream>.go        #   每个上游一个适配器文件
  cache/                 # 通用 TTL+LRU 缓存 → 只依赖 model
  circuit/               # 熔断器 → 只依赖标准库
config.example.yaml      # 与 DefaultConfig() 保持一致的示例配置
install.sh / Makefile / .github/workflows/release.yml
```
- **分层铁律**：依赖单向 `cmd → provider → {cache, circuit, config, model}`；`model`、`circuit` 严禁 import 任何内部包；适配器之间严禁互相 import。
- **契约位置**：上游契约只在 `provider/provider.go` 的接口中定义，新上游只能通过 Manager 内的 `buildProvider` 工厂 `switch` 注册；`cmd` 严禁直接引用具体适配器。
- **公开接口**：CLI 参数与 JSON 输出字段即对外 API，改动前先同步 `docs/base/API.md`。

## 3. 编码范式与高频避坑红线
- **[HTTP Client 注入]**：`*http.Client` 只在 `cmd` 构建一次，作为参数传入每个 `Query(ctx, client, ...)`；严禁适配器内部新建 client 或使用 `http.DefaultClient`。
- **[代理默认值]**：Transport 必须从 `Proxy: http.ProxyFromEnvironment` 起步；`--no-proxy` 显式返回 nil 代理；`--proxy` 支持 `http(s)` / `socks5(h)`（优先断言 `proxy.ContextDialer`）；两者用 `MarkFlagsMutuallyExclusive` 互斥。严禁裸写 `&http.Transport{}`——会静默丢失环境代理（曾因此返工）。
- **[超时分层]**：总超时在 `cmd` 用 `context.WithTimeout`；每次上游调用再套子 ctx 并在调用后立即 `cancel()`（循环内严禁 `defer`）；请求一律 `http.NewRequestWithContext`。配置中声明的单上游 `timeout` 字段必须接到子 ctx 上，严禁硬编码常量而让配置字段空置。
- **[适配器模板]**：构造时 `strings.TrimRight(baseURL, "/")`；非 200 返回 `fmt.Errorf("<name>: HTTP %d", code)`；上游响应用函数内匿名 `raw struct` 解码后映射到统一模型并填 `Source: p.Name()`；上游业务失败字段（如 `success:false`）必须转为 error，严禁透传空数据。
- **[降级编排]**：按 priority 分组升序遍历 → 过滤熔断打开者 → 组内 `rand.Shuffle` 分摊负载 → `Allow()` → 成功 `RecordSuccess` 并写缓存 / 失败 `RecordFailure` 后 `continue`；全部失败才返回汇总错误。
- **[并发安全]**：有状态组件（缓存、熔断器）每个公开方法首行 `mu.Lock(); defer mu.Unlock()`；私有辅助方法注释标明"调用方已持锁"，严禁重复加锁；HALF_OPEN 状态只放行一个探测请求。
- **[配置加载]**：路径为空回落 `~/.<bin>/config.yaml`；文件不存在则生成默认配置，回写失败只在 stderr 告警不中断；读取/解析错误用 `%w` 包装并带路径。`config.example.yaml` 必须与 `DefaultConfig()` 同步修改。
- **[密钥与依赖]**：上游 Token 必须支持环境变量覆盖（如 `<BIN>_<UPSTREAM>_TOKEN`），示例配置只留空串，严禁仅支持明文 yaml；`go.mod` 直接依赖严禁全部标记 `// indirect`，提交前必须 `go mod tidy`。
- **[发布与安装]**：交叉编译固定 `CGO_ENABLED=0`，产物命名 `<bin>-<os>-<arch>[.exe]` 并附 `checksums.txt`；`install.sh` 取版本先走 GitHub API，限流时回落解析 `releases/latest` 重定向；macOS 优先 `shasum -a 256` 校验。

## 4. 交付自检命令（完结门禁）
`test -z "$(gofmt -l .)" && go mod tidy -diff && go vet ./... && go test -race ./... && go build ./...`
