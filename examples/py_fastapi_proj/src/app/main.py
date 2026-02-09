"""
py-fastapi-proj - Python FastAPI Project Skeleton
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.base import router as base_router
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
    title="py-fastapi-proj",
    description="Python FastAPI Project Skeleton",
    version="0.1.0",
    lifespan=lifespan,
)

# 添加中间件
app.add_middleware(TraceMiddleware)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(base_router)


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
