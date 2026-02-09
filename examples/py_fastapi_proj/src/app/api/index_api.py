"""基础端点 (/, /health)"""
from fastapi import APIRouter

from app.api.schemas.api_common import ApiResponse
from app.utils.context import get_trace_id

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def root():
    """根路径"""
    return ApiResponse(
        code=0,
        msg="success",
        data={"service": "py-fastapi-proj", "version": "0.1.0"},
        trace_id=get_trace_id() or "",
    )


@router.get("/health", response_model=ApiResponse)
async def health():
    """健康检查"""
    return ApiResponse(
        code=0,
        msg="healthy",
        data={"status": "ok"},
        trace_id=get_trace_id() or "",
    )
