# Python Web 项目工程契约文档

> 本文档定义了 Python Web 微服务项目的通用工程规范，可直接用于 AI 辅助快速搭建新项目框架。
>
> **适用场景**: FastAPI 微服务、RESTful API 服务、后端业务系统

---

## 1. 技术栈规范

### 1.1 核心依赖

| 类别            | 技术选型  | 版本要求  | 说明                  |
| --------------- | --------- | --------- | --------------------- |
| **语言**        | Python    | >=3.12    | 推荐 3.13+            |
| **Web 框架**    | FastAPI   | >=0.128.0 | 高性能异步框架        |
| **ASGI 服务器** | Uvicorn   | >=0.40.0  | 生产级 ASGI 服务器    |
| **包管理器**    | uv        | latest    | Astral 的现代包管理器 |
| **数据验证**    | Pydantic  | >=2.0.0   | 类型安全的数据模型    |
| **HTTP 客户端** | httpx     | >=0.27.0  | 异步 HTTP 客户端      |
| **重试逻辑**    | tenacity  | >=8.2.0   | 声明式重试策略        |
| **结构化日志**  | structlog | >=24.0.0  | JSON 格式日志         |
| **配置解析**    | PyYAML    | >=6.0.0   | YAML 配置文件支持     |

### 1.2 可选依赖（按需选择）

| 类别           | 技术选型   | 版本要求 | 说明             |
| -------------- | ---------- | -------- | ---------------- |
| **数据库 ORM** | SQLAlchemy | >=2.0.0  | 异步 ORM (async) |
| **MySQL 驱动** | aiomysql   | >=0.2.0  | MySQL 异步驱动   |
| **LLM SDK**    | langchain  | >=0.3.0  | LLM 应用框架     |

### 1.3 开发依赖

```toml
[project.optional-dependencies]
dev = [
    "black>=24.0.0",           # 代码格式化
    "isort>=5.13.0",           # import 排序
    "pytest>=8.0.0",           # 测试框架
    "pytest-asyncio>=0.23.0",  # 异步测试支持
    "pytest-cov>=4.1.0",       # 测试覆盖率
    "python-dotenv>=1.0.0",    # 环境变量管理
]
```

---

## 2. 项目结构规范

### 2.1 标准目录结构（DDD 风格）

```
project_name/
├── src/
│   └── app/                    # 主应用包
│       ├── __init__.py
│       ├── main.py             # FastAPI 应用入口
│       ├── api/                # 接口层 (Interface Layer)
│       │   ├── __init__.py
│       │   ├── base.py         # 基础端点 (/, /health)
│       │   ├── {module}_api.py # 业务模块 API
│       │   └── schemas/        # API 请求/响应 DTO
│       │       ├── __init__.py
│       │       ├── api_common.py   # 通用响应模型
│       │       └── {module}_schema.py
│       ├── application/        # 应用层 (Application Layer)
│       │   ├── __init__.py
│       │   └── {module}_app.py # 业务流程编排
│       ├── domain/             # 领域层 (Domain Layer)
│       │   ├── entities/       # 领域实体
│       │   │   ├── __init__.py
│       │   │   └── {module}_entity.py
│       │   ├── services/       # 领域服务
│       │   │   ├── __init__.py
│       │   │   └── {module}_srv.py
│       │   ├── repos/          # 仓储接口（抽象）
│       │   │   ├── __init__.py
│       │   │   └── {module}_repos.py
│       │   └── valobj/         # 值对象
│       │       └── __init__.py
│       ├── infra/              # 基础设施层 (Infrastructure Layer)
│       │   ├── __init__.py
│       │   ├── config/         # 配置管理
│       │   │   ├── __init__.py
│       │   │   ├── config.py       # 统一配置获取入口
│       │   │   └── yaml_cfg.py     # YAML 配置加载
│       │   ├── dbs/            # 数据库 + 仓储实现
│       │   │   ├── __init__.py
│       │   │   ├── connection.py   # 连接管理
│       │   │   └── {module}_dbs.py # 模块仓储实现
│       │   ├── llmx/           # LLM 服务（可选）
│       │   │   └── {module}_infra.py
│       │   └── crawler/        # 爬虫服务（可选）
│       │       └── {module}_infra.py
│       ├── exceptions/         # 异常体系
│       │   ├── __init__.py
│       │   ├── base.py         # 基础异常类
│       │   ├── errors.py       # 业务异常定义
│       │   └── handlers.py     # 全局异常处理器
│       └── utils/              # 工具模块
│           ├── __init__.py
│           ├── context.py      # 请求上下文 (trace_id)
│           ├── logging.py      # 结构化日志
│           └── middleware.py   # 中间件
├── conf/                       # 配置文件目录
│   ├── app_dev.yaml            # 开发环境配置
│   ├── app_test.yaml           # 测试环境配置
│   └── app_prod.yaml           # 生产环境配置
├── tests/                      # 测试目录
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures
│   ├── unit/                   # 单元测试
│   └── test_api/               # API 集成测试
├── scripts/                    # 运维脚本
├── logs/                       # 日志目录
├── pyproject.toml              # 项目配置和依赖
├── uv.lock                     # 锁定依赖
├── Dockerfile                  # 多阶段 Docker 构建
├── start.sh                    # 启动脚本
└── README.md
```

### 2.2 分层职责说明

| 层级           | 目录               | 职责                                         | 依赖方向      | 文件名格式                               |
| -------------- | ------------------ | -------------------------------------------- | ------------- | ---------------------------------------- |
| **接口层**     | `api/`             | HTTP 路由定义、请求/响应 DTO、参数校验       | → Application | `{module}_api.py`, `schemas/{module}_schema.py` |
| **应用层**     | `application/`     | 业务流程编排、协调多个领域服务               | → Domain      | `{module}_app.py`                        |
| **领域层**     | `domain/`          | 核心业务逻辑、领域实体、仓储接口、值对象     | → Repos 接口  | `{module}_srv.py`, `{module}_entity.py`, `{module}_repos.py` |
| **基础设施层** | `infra/`           | 外部依赖封装（数据库、HTTP 客户端、配置等）  | 实现 Repos    | `{module}_dbs.py`, `{module}_infra.py`   |
| **异常层**     | `exceptions/`      | 统一异常体系                                 | 被各层引用    | `base.py`, `errors.py`, `handlers.py`    |
| **工具层**     | `utils/`           | 通用工具函数                                 | 被各层引用    | `context.py`, `logging.py`, `middleware.py` |

**DDD 分层依赖原则**:

```
┌─────────────┐
│   API 层    │  ← HTTP 请求入口，使用 api/schemas/ 定义 DTO
├─────────────┤
│  应用层     │  ← 编排领域服务，处理跨领域事务
├─────────────┤
│  领域层     │  ← 核心业务逻辑，定义仓储接口（抽象）
├─────────────┤
│ 基础设施层  │  ← 实现仓储接口，封装外部依赖
└─────────────┘
```

- **依赖方向**: 外层 → 内层，内层不依赖外层
- **仓储模式**: `domain/repos/` 定义抽象接口，`infra/dbs/` 实现具体存储
- **DTO vs Entity**: `api/schemas/` 用于 API 层数据传输，`domain/entities/` 用于领域逻辑

### 2.3 infra 层规范

每个外部依赖独立目录存放，按模块组织：

| 子目录      | 用途                     | 示例文件               |
| ----------- | ------------------------ | ---------------------- |
| `config/`   | 配置管理                 | `config.py`, `yaml_cfg.py` |
| `dbs/`      | 数据库连接 + 仓储实现    | `connection.py`, `user_dbs.py` |
| `llmx/`     | LLM 服务封装             | `openai_infra.py`      |
| `crawler/`  | 爬虫服务                 | `crawler_infra.py`     |
| `redisx/`   | Redis 缓存               | `redis_infra.py`       |

---

## 3. 应用入口规范

### 3.1 main.py 标准模板

```python
"""
{Service Name} - {Brief Description}
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.base import router as base_router
from app.api.{module}_api import router as module_router
from app.exceptions.handlers import register_exception_handlers
from app.infra.config import (
    get_app_env,
    get_logging_config,
    get_server_config,
    init_settings,
)
from app.utils.logging import get_logger, init_logging
from app.utils.middleware import TraceMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时: 初始化配置、日志、数据库连接
    关闭时: 清理资源、关闭连接
    """
    # ===== 启动阶段 =====
    # 1. 初始化配置系统
    init_settings()

    # 2. 获取配置
    logging_config = get_logging_config()
    server_config = get_server_config()
    app_env = get_app_env()

    # 3. 初始化日志系统
    init_logging(
        log_level=logging_config.get("level", "INFO"),
        json_format=logging_config.get("json_format", True),
        log_file=logging_config.get("log_file", ""),
    )

    logger = get_logger(__name__)
    logger.info(
        "application_starting",
        app_env=app_env,
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8080),
    )

    # 4. 初始化数据库（可选）
    # await init_database(...)

    yield  # 应用运行中

    # ===== 关闭阶段 =====
    logger.info("application_shutdown")
    # await close_database()
    # await close_http_clients()


# 创建 FastAPI 应用实例
app = FastAPI(
    title="{Service Name}",
    description="{Service Description}",
    version="0.1.0",
    lifespan=lifespan,
)

# 添加中间件
app.add_middleware(TraceMiddleware)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(base_router)
app.include_router(module_router)


if __name__ == "__main__":
    import uvicorn

    init_settings()
    server_config = get_server_config()
    app_env = get_app_env()

    uvicorn.run(
        "app.main:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8080),
        reload=app_env == "dev",
    )
```

---

## 4. 配置管理规范

### 4.1 YAML 配置文件结构

```yaml
# conf/app_{env}.yaml

# ==================== 环境标识 ====================
app_env: dev # dev | test | prod

# ==================== 服务器配置 ====================
server:
  host: 0.0.0.0
  port: 8080

# ==================== 日志配置 ====================
logging:
  level: INFO # DEBUG | INFO | WARNING | ERROR
  json_format: true # 生产环境推荐 true
  log_file: ./logs/app.log # 留空则仅输出到控制台

# ==================== 外部服务配置 ====================
external_service:
  base_url: http://api.example.com
  token: ${SERVICE_TOKEN} # 支持环境变量替换
  timeout: 30.0

# ==================== 重试策略配置 ====================
retry_policy:
  max_attempts: 3
  exponential_base: 2
  min_backoff: 1
  max_backoff: 30

# ==================== 数据库配置（可选）====================
database:
  host: localhost
  port: 3306
  username: ${DB_USER}
  password: ${DB_PASSWORD}
  database: app_db
  pool_size: 5
  max_overflow: 10
  echo: false
```

### 4.2 配置加载模块

```python
# src/app/infra/config/yaml_cfg.py
"""YAML 配置单例模块，支持环境变量替换"""
import os
from typing import Any, Dict, Optional

import yaml

_yaml_config: Optional[Dict[str, Any]] = None
_config_path: Optional[str] = None


def _resolve_env_vars(config: Any) -> Any:
    """递归替换 ${ENV_VAR} 占位符"""
    if isinstance(config, dict):
        return {k: _resolve_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_resolve_env_vars(item) for item in config]
    elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.getenv(env_var, config)
    return config


def get_config_file_path() -> str:
    """获取配置文件路径"""
    if config_file := os.getenv("CONFIG_FILE"):
        return config_file
    app_env = os.getenv("APP_ENV", "dev")
    return f"conf/app_{app_env}.yaml"


def init_yaml_config(config_path: Optional[str] = None) -> None:
    """初始化 YAML 配置单例"""
    global _yaml_config, _config_path

    if config_path is None:
        config_path = get_config_file_path()

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    _yaml_config = _resolve_env_vars(config)
    _config_path = config_path


def get_yaml_config() -> Dict[str, Any]:
    """获取完整配置"""
    if _yaml_config is None:
        init_yaml_config()
    return _yaml_config


def get_yaml_block(block_name: str) -> Dict[str, Any]:
    """获取指定配置块"""
    config = get_yaml_config()
    return config.get(block_name, {}) if block_name else config
```

### 4.3 统一配置获取入口

```python
# src/app/infra/config/config.py
"""统一配置获取模块"""
from typing import Any, Dict, Literal

from . import yaml_cfg


def get_app_env() -> Literal["dev", "test", "prod"]:
    """获取应用环境"""
    return yaml_cfg.get_yaml_block("").get("app_env", "dev")


def get_server_config() -> Dict[str, Any]:
    """获取服务器配置"""
    return yaml_cfg.get_yaml_block("server")


def get_logging_config() -> Dict[str, Any]:
    """获取日志配置"""
    return yaml_cfg.get_yaml_block("logging")


# ... 其他配置获取函数
```

---

## 5. API 响应规范

### 5.1 统一响应格式

```python
# src/app/api/schemas/api_common.py
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    通用 API 响应包装器

    所有 API 端点必须使用此格式响应
    """
    code: int = Field(..., description="错误码: 0=成功, 非0=错误")
    msg: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="业务数据")
    trace_id: str = Field(..., description="请求追踪 ID")


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="机器可读的错误代码")
    message: str = Field(..., description="人类可读的错误消息")
    details: Optional[dict] = Field(None, description="额外错误上下文")
```

### 5.2 响应示例

```json
// 成功响应
{
    "code": 0,
    "msg": "success",
    "data": { ... },
    "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}

// 错误响应
{
    "code": 40001,
    "msg": "Invalid query parameter",
    "data": null,
    "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 5.3 错误码规范

| 错误码范围  | 类别         | 说明                     |
| ----------- | ------------ | ------------------------ |
| 0           | 成功         | 请求处理成功             |
| 40001-40099 | 参数验证错误 | 请求参数不合法 (422)     |
| 50001-50099 | 业务异常     | 内部业务逻辑错误 (500)   |
| 50201-50299 | 网关错误     | 外部服务返回错误 (502)   |
| 50301-50399 | 服务不可用   | 外部服务暂时不可用 (503) |
| 50401-50499 | 超时错误     | 外部服务请求超时 (504)   |

---

## 6. 异常处理规范

### 6.1 异常层次结构

```python
# src/app/exceptions/base.py
from typing import Any, Dict, Optional


class AppException(Exception):
    """
    应用基础异常类

    所有自定义异常的父类，提供统一的异常处理接口
    """
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 API 响应）"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }
```

### 6.2 业务异常定义

```python
# src/app/exceptions/errors.py
from app.exceptions.base import AppException


class ConfigurationError(AppException):
    """配置错误"""
    pass


class ValidationError(AppException):
    """验证错误"""
    pass


class ServiceUnavailableError(AppException):
    """服务不可用"""
    pass


# 外部客户端异常层次
class ExternalClientError(AppException):
    """外部客户端错误基类"""
    pass


class ExternalTimeoutError(ExternalClientError):
    """外部服务超时"""
    pass


class ExternalTransientError(ExternalClientError):
    """外部服务临时错误（可重试）"""
    pass


class ExternalValidationError(ExternalClientError):
    """外部服务验证错误（不可重试）"""
    pass
```

### 6.3 全局异常处理器

```python
# src/app/exceptions/handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.exceptions.base import AppException
from app.exceptions.errors import (
    ValidationError,
    ExternalClientError,
    ExternalTimeoutError,
    ExternalTransientError,
)
from app.utils.context import get_trace_id
from app.utils.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        trace_id = get_trace_id()
        logger.error("validation_error", message=exc.message, trace_id=trace_id)
        return JSONResponse(
            status_code=422,
            content={"code": 40001, "msg": exc.message, "data": None, "trace_id": trace_id},
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_error_handler(request: Request, exc: PydanticValidationError):
        trace_id = get_trace_id()
        logger.error("pydantic_validation_error", errors=exc.errors(), trace_id=trace_id)
        return JSONResponse(
            status_code=422,
            content={"code": 40002, "msg": "Request validation failed", "data": None, "trace_id": trace_id},
        )

    @app.exception_handler(ExternalTimeoutError)
    async def timeout_error_handler(request: Request, exc: ExternalTimeoutError):
        trace_id = get_trace_id()
        logger.error("external_timeout", message=exc.message, trace_id=trace_id)
        return JSONResponse(
            status_code=504,
            content={"code": 50401, "msg": exc.message, "data": None, "trace_id": trace_id},
        )

    @app.exception_handler(ExternalTransientError)
    async def transient_error_handler(request: Request, exc: ExternalTransientError):
        trace_id = get_trace_id()
        logger.error("external_transient", message=exc.message, trace_id=trace_id)
        return JSONResponse(
            status_code=503,
            content={"code": 50301, "msg": exc.message, "data": None, "trace_id": trace_id},
        )

    @app.exception_handler(ExternalClientError)
    async def client_error_handler(request: Request, exc: ExternalClientError):
        trace_id = get_trace_id()
        logger.error("external_client_error", message=exc.message, trace_id=trace_id)
        return JSONResponse(
            status_code=502,
            content={"code": 50201, "msg": exc.message, "data": None, "trace_id": trace_id},
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        trace_id = get_trace_id()
        logger.error("app_exception", message=exc.message, trace_id=trace_id)
        return JSONResponse(
            status_code=500,
            content={"code": 50001, "msg": exc.message, "data": None, "trace_id": trace_id},
        )
```

---

## 7. 可观测性规范

### 7.1 请求上下文管理

```python
# src/app/utils/context.py
"""使用 contextvars 在异步请求中传递上下文信息"""
from contextvars import ContextVar
from typing import Optional

trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def get_trace_id() -> Optional[str]:
    """获取当前请求的 trace_id"""
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """设置当前请求的 trace_id"""
    trace_id_var.set(trace_id)
```

### 7.2 Trace 中间件

```python
# src/app/utils/middleware.py
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.context import set_trace_id
from app.utils.logging import get_logger

logger = get_logger(__name__)


def extract_trace_id(header_value: Optional[str]) -> str:
    """从 Header 提取或生成 trace_id"""
    if header_value and header_value.strip():
        return header_value.strip()
    return str(uuid.uuid4())


class TraceMiddleware(BaseHTTPMiddleware):
    """全链路追踪中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. 提取或生成 trace_id
        trace_id = extract_trace_id(request.headers.get("X-TRACE-ID"))
        set_trace_id(trace_id)

        # 2. 记录请求开始
        start_time = time.time()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            trace_id=trace_id,
        )

        # 3. 执行请求
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed_ms,
                error=str(exc),
                trace_id=trace_id,
            )
            raise

        # 4. 记录响应
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            trace_id=trace_id,
        )

        # 5. 响应头注入 trace_id
        response.headers["X-TRACE-ID"] = trace_id
        return response
```

### 7.3 结构化日志

```python
# src/app/utils/logging.py
"""基于 structlog 的结构化日志，自动注入 trace_id"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict

from app.utils.context import get_trace_id


def add_trace_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """自动添加 trace_id 到日志"""
    if trace_id := get_trace_id():
        event_dict["trace_id"] = trace_id
    return event_dict


def configure_logging(log_level: str = "INFO", json_format: bool = True, log_file: str = "") -> None:
    """配置全局日志系统"""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    log_level_value = getattr(logging, log_level.upper())
    root_logger.setLevel(log_level_value)

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_value)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    # 文件 Handler（可选）
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level_value)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(file_handler)

    # structlog 处理器链
    processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder([
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.FUNC_NAME,
        ]),
        add_trace_id,
        structlog.processors.format_exc_info,
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取日志记录器"""
    return structlog.get_logger(name)


def init_logging(log_level: str = "INFO", json_format: bool = True, log_file: str = "") -> None:
    """初始化日志系统（应用启动时调用）"""
    configure_logging(log_level=log_level, json_format=json_format, log_file=log_file)
```

---

## 8. 外部客户端规范

### 8.1 HTTP 客户端基类

```python
# src/app/infra/{service}_client.py
"""外部服务 HTTP 客户端基类，封装认证、重试、错误处理"""
from typing import Any, Dict

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.exceptions.errors import (
    ExternalClientError,
    ExternalTimeoutError,
    ExternalTransientError,
    ExternalValidationError,
)
from app.infra.config import get_service_config, get_retry_policy
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BaseHttpClient:
    """
    HTTP 客户端基类

    提供:
    - httpx.AsyncClient 管理
    - 认证 Token 注入
    - 统一请求接口
    - 重试逻辑（指数退避）
    - 错误响应转换
    """

    def __init__(self):
        config = get_service_config()
        self.base_url = config["base_url"]
        self.token = config["token"]
        self.timeout = config.get("timeout", 30.0)

        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.timeout, connect=5.0),
        )

    async def close(self):
        """关闭连接"""
        await self.client.aclose()

    def _get_retry_decorator(self):
        """获取重试装饰器"""
        policy = get_retry_policy()
        return retry(
            retry=retry_if_exception_type(ExternalTransientError),
            stop=stop_after_attempt(policy.get("max_attempts", 3)),
            wait=wait_exponential(
                multiplier=1,
                min=policy.get("min_backoff", 1),
                max=policy.get("max_backoff", 10),
            ),
        )

    async def request(self, method: str, url: str, payload: Any) -> httpx.Response:
        """统一请求方法"""
        retry_decorator = self._get_retry_decorator()

        @retry_decorator
        async def _execute():
            request_body = payload.model_dump(exclude_none=True) if isinstance(payload, BaseModel) else payload

            logger.info("http_request", method=method, url=url)

            try:
                response = await self.client.request(method, url, json=request_body)
                logger.info("http_response", status_code=response.status_code)
                return response
            except httpx.TimeoutException as e:
                logger.error("http_timeout", url=url)
                raise ExternalTimeoutError(f"Request timeout: {url}") from e
            except httpx.ConnectError as e:
                logger.error("http_connect_error", url=url, error=str(e))
                raise ExternalTransientError(f"Connection failed: {url}") from e
            except Exception as e:
                logger.error("http_error", url=url, error=str(e))
                raise ExternalClientError(f"Request failed: {str(e)}") from e

        return await _execute()
```

### 8.2 重试策略

| 场景           | 是否重试 | 说明                     |
| -------------- | -------- | ------------------------ |
| 5xx 服务器错误 | 是       | 临时性错误，重试可能成功 |
| 请求超时       | 是       | 网络波动，重试可能成功   |
| 连接错误       | 是       | 网络问题，重试可能成功   |
| 4xx 客户端错误 | 否       | 参数错误，重试无意义     |
| 认证失败       | 否       | 配置问题，重试无意义     |

---

## 9. 数据库规范

### 9.1 异步数据库连接管理

```python
# src/app/infra/database/connection.py
"""SQLAlchemy 2.0 异步数据库连接管理"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """数据库管理器（单例模式）"""

    _instance: Optional["DatabaseManager"] = None
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
    ) -> None:
        """初始化数据库连接"""
        if self._engine is not None:
            return

        database_url = f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"

        self._engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info("database_initialized", host=host, database=database)

    async def close(self) -> None:
        """关闭连接"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("database_closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# 全局实例
_db_manager = DatabaseManager()


async def init_database(**kwargs) -> None:
    """初始化数据库"""
    await _db_manager.initialize(**kwargs)


async def close_database() -> None:
    """关闭数据库"""
    await _db_manager.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入"""
    async with _db_manager.session() as session:
        yield session
```

---

## 10. 容器化规范

### 10.1 多阶段 Dockerfile

```dockerfile
# ============================================
# Stage 1: Builder - 构建依赖环境
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖到虚拟环境
RUN uv sync --frozen --no-install-project --no-dev

# ============================================
# Stage 2: Runtime - 运行环境
# ============================================
FROM python:3.12-slim

WORKDIR /app

# 从 builder 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制应用代码
COPY ./src /app/src
COPY ./conf /app/conf
COPY ./start.sh /app/start.sh

# 设置环境变量
ENV TZ='Asia/Shanghai' \
    LC_ALL=en_US.utf8 \
    APP_ENV=prod \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

# 启动命令
CMD ["./start.sh", "--conf", "./conf/app_prod.yaml"]
```

### 10.2 启动脚本

```bash
#!/bin/bash
# start.sh

# 解析命令行参数
CONFIG_FILE="conf/app_dev.yaml"
while [[ $# -gt 0 ]]; do
    case $1 in
        --conf)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

export CONFIG_FILE

# 启动应用
exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --workers ${WORKERS:-1}
```

---

## 11. 测试规范

### 11.1 pytest 配置

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
asyncio_mode = "auto"
addopts = "-v --cov=src --cov-report=term-missing"
```

### 11.2 测试 Fixtures

```python
# tests/conftest.py
"""测试配置和共享 fixtures"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_http_client():
    """Mock HTTP 客户端"""
    client = MagicMock()
    client.request = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_db_session():
    """Mock 数据库会话"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session
```

---

## 12. pyproject.toml 完整模板

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/app"]

[project]
name = "project-name"
version = "0.1.0"
description = "Project Description"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    # Web 框架
    "fastapi>=0.128.0",
    "uvicorn>=0.40.0",
    # 数据验证
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    # 日志
    "structlog>=24.0.0",
    # HTTP 客户端
    "httpx>=0.27.0",
    # 重试
    "tenacity>=8.2.0",
    # 配置
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "black>=24.0.0",
    "isort>=5.13.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "python-dotenv>=1.0.0",
]

db = [
    "sqlalchemy>=2.0.0",
    "aiomysql>=0.2.0",
]

[tool.uv]
package = true

[tool.black]
line-length = 100
target-version = ['py312']

[tool.isort]
profile = "black"
line_length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --cov=src --cov-report=term-missing"
```

---

## 13. 快速启动清单

### 13.1 新项目初始化步骤

```bash
# 1. 创建项目目录
mkdir project_name && cd project_name

# 2. 初始化 uv 项目
uv init

# 3. 创建 DDD 目录结构
mkdir -p src/app/api/schemas
mkdir -p src/app/application
mkdir -p src/app/domain/{entities,services,repos,valobj}
mkdir -p src/app/infra/{config,dbs}
mkdir -p src/app/{exceptions,utils}
mkdir -p conf tests/{unit,test_api} scripts logs

# 4. 创建 __init__.py 文件
touch src/app/__init__.py
touch src/app/api/__init__.py src/app/api/schemas/__init__.py
touch src/app/application/__init__.py
touch src/app/domain/__init__.py
touch src/app/domain/{entities,services,repos,valobj}/__init__.py
touch src/app/infra/__init__.py src/app/infra/{config,dbs}/__init__.py
touch src/app/{exceptions,utils}/__init__.py
touch tests/__init__.py

# 5. 复制模板文件
# - pyproject.toml
# - conf/app_dev.yaml
# - src/app/main.py
# - src/app/api/base.py
# - src/app/api/schemas/api_common.py
# - src/app/exceptions/{base,errors,handlers}.py
# - src/app/utils/{context,logging,middleware}.py
# - src/app/infra/config/{yaml_cfg,config}.py

# 6. 安装依赖
uv sync

# 7. 启动服务
PYTHONPATH=src python -m app.main
```

### 13.2 开发命令速查

```bash
# 依赖管理
uv add <package>           # 添加依赖
uv sync                    # 同步依赖

# 代码格式化
black . && isort .

# 运行测试
pytest tests/

# 启动服务
./start.sh --conf conf/app_dev.yaml
# 或
APP_ENV=dev PYTHONPATH=src python -m app.main
```

---

## 附录 A: 命名规范

| 类型      | 规范             | 示例                    |
| --------- | ---------------- | ----------------------- |
| 模块文件  | snake_case       | `search_service.py`     |
| 类名      | PascalCase       | `SearchService`         |
| 函数/方法 | snake_case       | `hybrid_search()`       |
| 常量      | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`       |
| API 路径  | kebab-case       | `/api/v1/hybrid-search` |
| 配置键    | snake_case       | `max_attempts`          |

---

## 附录 B: 代码风格

1. **行长度**: 100 字符
2. **缩进**: 4 空格
3. **引号**: 双引号优先
4. **导入顺序**: 标准库 → 第三方库 → 本地模块
5. **类型注解**: 所有公共接口必须有类型注解
6. **文档字符串**: 所有公共函数/类必须有 docstring

---

_文档版本: 1.1.0_
_最后更新: 2025-02_
_变更记录: 采用 DDD 分层架构，调整目录结构（api/schemas, domain/, infra/config），配置目录改为 conf/_
