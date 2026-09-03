"""
ResourceHub Backend — FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.response import error_response, APIError
from app.core.errors import ErrorCode
from app.routers import auth, notes, prompts, categories

app = FastAPI(
    title="ResourceHub API",
    description="个人知识管理与 AI 提示词管理的一体化工具",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(notes.router, prefix="/api/notes", tags=["笔记"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["提示词"])
app.include_router(categories.router, prefix="/api/categories", tags=["分类"])


@app.on_event("startup")
async def startup():
    """启动时创建数据库表（开发环境）"""
    async with engine.begin() as conn:
        from app.models import user, note, prompt, category  # noqa
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health_check():
    return {"code": 200, "data": {"status": "ok", "version": "0.1.0"}, "msg": "ok"}


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    自定义 API 异常处理器
    将 APIError 转换为标准响应格式
    """
    return JSONResponse(
        status_code=exc.code if exc.code < 600 else 400,
        content=error_response(msg=exc.msg, code=exc.code, data=exc.data),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP 异常处理器
    将 FastAPI 的 HTTPException 转换为标准响应格式
    """
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", exc.status_code)
        msg = exc.detail.get("message", str(exc.detail))
        data = exc.detail.get("data")
    else:
        code = exc.status_code
        msg = str(exc.detail) if exc.detail else "请求错误"
        data = None

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(msg=msg, code=code, data=data),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    请求验证异常处理器
    将 Pydantic 验证错误转换为标准响应格式
    """
    errors = []
    for err in exc.errors():
        errors.append({
            "loc": err.get("loc", []),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        })

    return JSONResponse(
        status_code=ErrorCode.VALIDATION_ERROR,
        content=error_response(
            msg="请求参数验证失败",
            code=ErrorCode.VALIDATION_ERROR,
            data={"errors": errors},
        ),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    捕获所有未处理的异常，返回统一格式
    """
    return JSONResponse(
        status_code=ErrorCode.INTERNAL_ERROR,
        content=error_response(
            msg="服务器内部错误",
            code=ErrorCode.INTERNAL_ERROR,
            data={"detail": str(exc)} if settings.DEBUG else None,
        ),
    )
