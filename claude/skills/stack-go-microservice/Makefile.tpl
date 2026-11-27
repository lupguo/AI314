.PHONY: proto lint test build run clean

GO ?= go
SERVICE_NAME ?= app

# 编译 Protobuf 契约
proto:
	@if [ -d "api" ]; then \
		find api -name "*.proto" -exec protoc --go_out=. --go_opt=paths=source_relative --go-grpc_out=. --go-grpc_opt=paths=source_relative {} + ; \
		echo "✅ Proto 编译完成"; \
	fi

# 静态代码检查
lint:
	golangci-lint run ./...

# 运行单元测试（强制开启竞态检测）
test:
	$(GO) test -race -v ./...

# 编译二进制产物
build:
	$(GO) build -ldflags="-s -w" -o bin/$(SERVICE_NAME) ./cmd/...

# 清理构建产物
clean:
	rm -rf bin/
