---
name: stack-go-microservice
description: 当开发或维护 Go 语言微服务、后端 API、RPC 服务或高并发后端模块时强制加载此技能。
---

# Go 微服务工程规范

## 1. 钦定技术栈（禁止自行替换或重新调研）
- **语言与核心框架**：Go 1.23+，微服务框架优先 Kratos 或 Gin + gRPC (`google.golang.org/grpc`)
- **数据存储与缓存**：PostgreSQL + GORM（或 sqlc）；缓存统一使用 Redis (`github.com/redis/go-redis/v9`)
- **通信与序列化**：Protobuf v3 (`buf` 或 `protoc`) + HTTP/JSON Gateway；参数校验使用 `protovalidate` 或 `go-playground/validator`
- **可观测与基础设施**：`uber-go/zap` 结构化日志 + OpenTelemetry + `spf13/viper` 配置加载 + Wire 依赖注入

## 2. 强制目录拓扑与分层边界
```text
├── api/<service>/v1/        # .proto 接口契约与生成的 pb.go（接口唯一真相源）
├── cmd/<service>/           # 程序入口、Wire 依赖装配与平滑启停 (Graceful Shutdown)
├── internal/
│   ├── service/             # RPC/HTTP 接入层：DTO 转换与参数校验，禁止包含业务逻辑
│   ├── biz/                 # 核心领域层：UseCase 与领域接口定义（零外部基础设施依赖）
│   ├── data/                # 数据仓储层：实现 biz 层定义的 Repo 接口，操作 DB/Redis/MQ
│   └── server/              # HTTP / gRPC Server 初始化与中间件注册（鉴权、限流、Trace）
├── migrations/              # 增量 SQL 迁移脚本（up/down）
└── Makefile                 # 统一构建、Proto 生成与测试入口
```
- **分层铁律**：依赖流向严格单向为 `service -> biz <- data`。**`internal/biz/` 严禁 import `gorm`、`redis`、`gin` 或任何第三方基础设施包**；跨层调用必须通过接口解耦。

## 3. 编码范式与高频避坑红线
- **契约先行**：修改任何对外 API 或字段前，必须先修改 `api/**/*.proto` 并执行 `make proto`，严禁手改自动生成的 `.pb.go` 文件。
- **全链路 Context 透传**：所有涉及网络、数据库、缓存、消息队列的函数，第一个参数必须是 `ctx context.Context`，且必须绑定显式超时控制（`context.WithTimeout`）。
- **数据库迁移红线**：严禁在生产代码中调用 GORM 的 `AutoMigrate`；所有表结构变更必须通过 `migrations/` 下的版本化 SQL 脚本管理。
- **错误码收敛**：业务错误统一封装为标准错误码结构（`Code` / `Reason` / `Message`），基础设施底层报错（如 SQL 语法错、连接超时）必须在 `data` 层拦截记录日志并转换为内部错误，严禁透传给前端。
- **并发安全门禁**：涉及共享 Map 读写或 Goroutine 扇出聚合，优先使用 `errgroup.WithContext` 与 `sync.Map`；所有测试必须默认开启 `-race` 竞争检测。

## 4. 交付自检命令（完结门禁）
`golangci-lint run ./... && go test -race -cover ./... && go build ./cmd/...`
