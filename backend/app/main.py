"""FastAPI application — 服务器公告后端。

Endpoints (matching the existing Vue frontend):
  GET  /announcement/page          分页查询公告
  GET  /announcement/detail/{id}   查询公告详情
  POST /announcement/addWatchCount 增加公告阅读量
  POST /announcement/create        创建公告（管理员）
  PUT  /announcement/update/{id}   更新公告（管理员）
  DELETE /announcement/delete/{id} 删除公告（管理员）
  POST /announcement/upload/image  上传富文本图片（管理员）
  GET  /announcement/uploads/*     上传图片静态目录
  GET  /auth/captcha               图形验证码
  POST /auth/register              注册
  POST /auth/login                 登录（签发 JWT）
  GET  /auth/me                    当前用户信息
  POST /faction-beta/apply         提交阵营对战内测申请（需登录）
  GET  /faction-beta/my            查询当前用户申请（需登录）
  GET  /faction-beta/admin/page    管理员分页查询申请（需管理员）
  PUT  /faction-beta/admin/{id}/review  审核申请（需管理员）
  DELETE /faction-beta/admin/{id}  删除申请（需管理员）
"""
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .database import BASE_DIR, init_db, get_db, Announcement
from .monitor import router as monitor_router
from .auth import bootstrap
from .auth.deps import require_admin
from .auth.router import router as auth_router
from .faction_beta import router as faction_beta_router
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
    _TZ as BEIJING_TZ,
)

# ── 富文本图片上传配置 ────────────────────────────────────────
# 上传目录：默认 backend/data/uploads，可用环境变量覆盖（Docker 中指向挂载卷 /app/data/uploads）
UPLOAD_DIR = Path(
    os.environ.get("ANNOUNCEMENT_UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))
)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


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

# 阵营对战玩法内测资格申请
app.include_router(faction_beta_router)

# 静态托管富文本上传的图片。
# 生产 Nginx 已按 /announcement 前缀反代到本服务，该子路径无需额外配置即可访问。
app.mount(
    "/announcement/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads",
)


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


# ── 公告图片上传（管理员接口，富文本编辑器使用） ───────────────
@app.post("/announcement/upload/image")
async def upload_image_endpoint(
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    """上传公告富文本图片，返回可写入正文的相对 URL（与部署域无关）。"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, detail="仅支持 png / jpg / jpeg / gif / webp 图片"
        )
    if not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不是图片")

    data = await file.read()
    if len(data) > _MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    # 按月份分目录 + 随机文件名（避免覆盖与路径穿越）
    sub_dir = datetime.now(BEIJING_TZ).strftime("%Y%m")
    target_dir = UPLOAD_DIR / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (target_dir / name).write_bytes(data)

    url = f"/announcement/uploads/{sub_dir}/{name}"
    return {"code": 0, "message": "success", "data": {"url": url}}


# ── 健康检查 ──────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}