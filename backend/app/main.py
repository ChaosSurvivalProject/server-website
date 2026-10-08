"""FastAPI application — 星穹旅驿官网后端。

所有业务接口统一挂载在 /api 前缀下（nginx 按前缀反代；下表省略 /api）。
Endpoints:
  GET  /health                       健康检查
  /api/messages/*                    站内信（前台 + 管理员）
  /api/auth/*                        认证（验证码 / 注册 / 登录 / 当前用户 / 管理员用户管理）
  /api/faction-beta/*                阵营对战玩法内测资格申请
  /api/kb/*                          智能客服（/api/kb/chat SSE 唯一不走包络）
  /api/staff/*                       工作人员名片（公开 + 管理员）
  /api/forum/*                       社区论坛（公开 + 登录用户 + 管理员）
"""
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, FastAPI, Depends, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .database import BASE_DIR, init_db, get_db
from .monitor import router as monitor_router, load_servers
from . import kb as kb_module
from . import staff as staff_module
from . import forum as forum_module
from . import messages as messages_module
from .auth import bootstrap
from .auth.deps import require_admin
from .auth.router import router as auth_router
from .auth.users_admin import router as auth_admin_users_router
from .faction_beta import router as faction_beta_router
from .uploads import UPLOAD_DIR, save_image

logger = logging.getLogger("uvicorn.error")

# ── 富文本图片上传配置 ────────────────────────────────────────────
# UPLOAD_DIR 与白名单/落盘逻辑已抽到 app/uploads.py（公告与论坛共用同一份口径，
# 见该文件头注释）；此处只保留 re-export 供下方 StaticFiles 挂载使用。

app = FastAPI(
    title="星穹旅驿官网 API",
    description="基于 FastAPI + SQLite 的星穹旅驿官网后端",
    version="2.0.0",
)

# CORS — allow the Vue frontend (dev + prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一 API 前缀：全部业务路由挂在 /api 下
api_router = APIRouter(prefix="/api")

# 服务器监控（最小 TCP 探测实现）
app.include_router(monitor_router, prefix="/api")

# 认证（验证码 / 注册 / 登录 / 当前用户）
app.include_router(auth_router, prefix="/api")

# 管理员用户管理（新增 / 编辑 / 启停 / 软删除 / 分页）
app.include_router(auth_admin_users_router, prefix="/api")

# 阵营对战玩法内测资格申请
app.include_router(faction_beta_router, prefix="/api")

# 知识库 / 智能客服（/api/kb/info、/api/kb/chat SSE、/api/kb/admin/*）
app.include_router(kb_module.router, prefix="/api")

# 员工名片（/api/staff/public/*、/api/staff/admin/*）
app.include_router(staff_module.router, prefix="/api")

# 社区论坛（/api/forum/*）
app.include_router(forum_module.router, prefix="/api")

# 站内信（/api/messages/* + /api/messages/admin/*）
app.include_router(messages_module.router, prefix="/api")
app.include_router(messages_module.admin_router, prefix="/api")

app.include_router(api_router)

# 静态托管上传的图片（论坛封面 / 内嵌图共用）。
app.mount(
    "/api/announcement/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads",
)
# 存量兼容：历史公告正文内嵌的旧 URL /announcement/uploads/...
app.mount(
    "/announcement/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads-legacy",
)


@app.on_event("startup")
async def on_startup():
    await init_db()
    # 检测系统管理员是否初始化，未初始化则创建（密码写入临时 txt 文件）
    await bootstrap.ensure_admin()
    # 服务器地址持久化
    await load_servers()
    # 智能客服启动三查 + 预热向量索引
    await kb_module.startup_check()
    # 社区论坛种子数据
    await forum_module.ensure_seeded()
    # 员工名片到期检查
    try:
        from .database import async_session_maker
        async with async_session_maker() as session:
            changed = await staff_module.expire_due(session)
            if changed:
                logger.info("员工名片启动到期检查：回写 %s 条为 revoked('expired')", changed)
    except Exception as e:
        logger.warning("员工名片启动到期检查失败: %s", e)
    # 社区回收站超期清理
    try:
        from .database import async_session_maker
        async with async_session_maker() as session:
            purged, ids = await forum_module.purge_due(session)
            if purged:
                logger.info("论坛回收站启动兜底清理：物理清除 %s 条超 30 天帖子（ids=%s）", purged, ids)
    except Exception as e:
        logger.warning("论坛回收站启动兜底清理失败: %s", e)


# ── 健康检查 ──────────────────────────────────────────────────────
@app.get("/health")
@api_router.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


# ── 统一把未预期的数值异常收敛成 400 ──────────────────────────────
@app.exception_handler(OverflowError)
async def overflow_error_handler(request, exc: OverflowError):
    logger.warning("请求参数数值越界: %s %s — %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": "参数数值超出允许范围"},
    )
