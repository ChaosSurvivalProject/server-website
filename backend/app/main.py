"""FastAPI application — 服务器公告后端。

Endpoints (matching the existing Vue frontend):
  GET  /announcement/page          分页查询公告
  GET  /announcement/detail/{id}   查询公告详情
  POST /announcement/addWatchCount 增加公告阅读量
  POST /announcement/create        创建公告（管理员）
  PUT  /announcement/update/{id}   更新公告（管理员）
  DELETE /announcement/delete/{id} 删除公告（管理员）
  GET  /auth/captcha               图形验证码
  POST /auth/register              注册
  POST /auth/login                 登录（签发 JWT）
  GET  /auth/me                    当前用户信息
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import init_db, get_db, Announcement
from .monitor import router as monitor_router
from .auth import bootstrap
from .auth.deps import require_admin
from .auth.router import router as auth_router
from .schemas import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    PageResponse,
    AddWatchCountRequest,
    CommonResponse,
)
from .crud import (
    create_announcement,
    get_announcement,
    get_page,
    update_announcement,
    delete_announcement,
    add_watch_count,
)


app = FastAPI(
    title="服务器公告 API",
    description="基于 FastAPI + SQLite 的服务器公告后端",
    version="1.0.0",
)

# CORS — allow the Vue frontend (dev + prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务器监控（最小 TCP 探测实现）
app.include_router(monitor_router)

# 认证（验证码 / 注册 / 登录 / 当前用户）
app.include_router(auth_router)


@app.on_event("startup")
async def on_startup():
    await init_db()
    # 检测系统管理员是否初始化，未初始化则创建（密码写入临时 txt 文件）
    await bootstrap.ensure_admin()


# ── 公告分页查询 ──────────────────────────────────────────────
@app.get("/announcement/page", response_model=PageResponse)
async def query_page(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    isPublished: int = Query(default=1, description="0=草稿, 1=已发布"),
    db=Depends(get_db),
):
    """分页查询公告列表。"""
    return await get_page(db, page=page, page_size=pageSize, is_published=isPublished)


# ── 公告详情 ──────────────────────────────────────────────────
@app.get("/announcement/detail/{announcement_id}", response_model=AnnouncementResponse)
async def get_detail(
    announcement_id: int,
    db=Depends(get_db),
):
    """获取单条公告详情。"""
    obj = await get_announcement(db, announcement_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="公告不存在")
    return obj


# ── 增加阅读量 ────────────────────────────────────────────────
@app.post("/announcement/addWatchCount")
async def add_watch_count_endpoint(
    req: AddWatchCountRequest,
    db=Depends(get_db),
):
    """增加公告阅读量（+1）。"""
    ok = await add_watch_count(db, req.announcementId)
    if not ok:
        raise HTTPException(status_code=404, detail="公告不存在")
    return {"code": 0, "message": "success"}


# ── 公告创建（管理员接口） ─────────────────────────────────────
@app.post("/announcement/create", response_model=AnnouncementResponse)
async def create_announcement_endpoint(
    data: AnnouncementCreate,
    db=Depends(get_db),
    _admin=Depends(require_admin),
):
    """创建新公告。"""
    obj = await create_announcement(db, data)
    return obj


# ── 公告更新（管理员接口） ─────────────────────────────────────
@app.put("/announcement/update/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement_endpoint(
    announcement_id: int,
    data: AnnouncementUpdate,
    db=Depends(get_db),
    _admin=Depends(require_admin),
):
    """更新公告（部分更新）。"""
    obj = await update_announcement(db, announcement_id, data)
    if obj is None:
        raise HTTPException(status_code=404, detail="公告不存在")
    return obj


# ── 公告删除（管理员接口） ─────────────────────────────────────
@app.delete("/announcement/delete/{announcement_id}")
async def delete_announcement_endpoint(
    announcement_id: int,
    db=Depends(get_db),
    _admin=Depends(require_admin),
):
    """删除公告。"""
    ok = await delete_announcement(db, announcement_id)
    if not ok:
        raise HTTPException(status_code=404, detail="公告不存在")
    return {"code": 0, "message": "success"}


# ── 管理员：公告分页（含草稿） ─────────────────────────────────
@app.get("/announcement/admin/page", response_model=PageResponse)
async def admin_query_page(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db=Depends(get_db),
    _admin=Depends(require_admin),
):
    """管理员：分页查询所有公告（包括草稿，不过滤 isPublished）。"""
    return await get_page(db, page=page, page_size=pageSize, is_published=None)


# ── 健康检查 ──────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}