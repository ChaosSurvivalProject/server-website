"""阵营对战玩法内测资格申请：/faction-beta/*。

结构参照 auth 模块（schemas + router 同文件，main.py 挂载 router）：

  POST /faction-beta/apply            提交申请（需登录；每账号一份，被拒后可重新提交）
  GET  /faction-beta/my               查询当前用户申请（需登录；未提交时 data.application 为 null）
  GET  /faction-beta/admin/page       管理员分页（可按 status 过滤）
  PUT  /faction-beta/admin/{id}/review 审核通过 / 拒绝
  DELETE /faction-beta/admin/{id}     删除申请

所有接口遵循项目统一响应包络 {code, message, data}（code=0 成功）；
业务失败以 HTTPException(400/401/403/404, detail=...) 抛出，前端 axios
拦截器统一读取 detail 展示。
"""
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import get_current_user, require_admin
from .database import FactionBetaApplication, User, get_db
from .crud import _TZ  # 统一北京时间（naive ISO 字符串，见 AGENTS.md 存储约定）

router = APIRouter(prefix="/faction-beta", tags=["faction-beta"])

# ── 申请表选项（后端为唯一权威，前端选项需与此保持一致） ─────────
# 阵营命名来自 chaos 设定文档《阵营设定_黎明誓约与暮夜同盟》
FACTION_OPTIONS = ["黎明誓约", "暮夜同盟", "暂不选择"]
EXPERIENCE_OPTIONS = ["萌新", "有一定经验", "身经百战"]
WEEKLY_HOURS_OPTIONS = ["5 小时以内", "5-15 小时", "15 小时以上"]

# 申请状态：布尔语义用 int 的项目规约扩展为三态
STATUS_PENDING = 0
STATUS_APPROVED = 1
STATUS_REJECTED = 2

_MC_ID_RE = re.compile(r"^\S{2,50}$")  # MC 游戏 ID：2-50 个非空白字符（兼容基岩版带点 ID）
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")  # 务实版邮箱校验


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


# ── Pydantic schemas ─────────────────────────────────────────────
class FactionBetaApplyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mc_id: str = Field(..., alias="mcId", max_length=50, description="MC 游戏 ID")
    email: str = Field(..., max_length=254, description="邮箱")
    faction: str = Field(..., max_length=30, description="期望阵营")
    experience: str = Field(..., max_length=20, description="PvP 经验")
    weekly_hours: str = Field(..., alias="weeklyHours", max_length=30, description="每周可参与测试时长")
    motivation: str = Field(..., max_length=500, description="申请理由")

    @field_validator("mc_id", "email", "faction", "experience", "weekly_hours", "motivation", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class FactionBetaReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: int = Field(..., description="审核结果：1=通过, 2=拒绝")
    review_note: Optional[str] = Field(None, alias="reviewNote", max_length=255, description="审核备注（可选）")


class FactionBetaApplicationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    username: str
    mc_id: str = Field(..., alias="mcId")
    email: str
    faction: str
    experience: str
    weekly_hours: str = Field(..., alias="weeklyHours")
    motivation: str
    status: int = STATUS_PENDING
    review_note: str = Field(default="", alias="reviewNote")
    review_time: Optional[str] = Field(None, alias="reviewTime")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")


class FactionBetaPageResponse(BaseModel):
    """分页结构（与公告 PageResponse 保持一致）。"""

    items: list[FactionBetaApplicationResponse]
    page: int
    pageSize: int
    totalPages: int
    total: int
    hasNext: bool
    hasPrev: bool


def _dump(obj: FactionBetaApplication) -> dict:
    """ORM 对象 → camelCase dict（用于响应包络 data 字段）。"""
    return FactionBetaApplicationResponse.model_validate(obj).model_dump(by_alias=True)


async def _get_by_username(db: AsyncSession, username: str) -> FactionBetaApplication | None:
    result = await db.execute(
        select(FactionBetaApplication).where(FactionBetaApplication.username == username)
    )
    return result.scalar_one_or_none()


# ── 用户端：提交申请 ──────────────────────────────────────────────
@router.post("/apply")
async def apply(
    data: FactionBetaApplyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交内测申请（需登录）。每账号仅一份申请；被拒后可重新提交覆盖原记录。"""
    # 1. 字段校验（友好错误信息，走 HTTPException → 前端 detail 展示）
    if not _MC_ID_RE.fullmatch(data.mc_id):
        raise HTTPException(status_code=400, detail="MC 游戏 ID 需为 2-50 个字符且不含空格")
    if not _EMAIL_RE.fullmatch(data.email) or len(data.email) > 254:
        raise HTTPException(status_code=400, detail="请填写正确的邮箱地址")
    if data.faction not in FACTION_OPTIONS:
        raise HTTPException(status_code=400, detail="请选择期望阵营")
    if data.experience not in EXPERIENCE_OPTIONS:
        raise HTTPException(status_code=400, detail="请选择 PvP 经验")
    if data.weekly_hours not in WEEKLY_HOURS_OPTIONS:
        raise HTTPException(status_code=400, detail="请选择每周可参与测试时长")
    if not (5 <= len(data.motivation) <= 500):
        raise HTTPException(status_code=400, detail="申请理由需为 5-500 个字符")

    # 2. 每账号一份：待审核/已通过时禁止重复提交，被拒后允许重新提交
    existing = await _get_by_username(db, user.username)
    now = _now_iso()
    if existing is not None:
        if existing.status == STATUS_PENDING:
            raise HTTPException(status_code=400, detail="您已提交过申请，请耐心等待审核")
        if existing.status == STATUS_APPROVED:
            raise HTTPException(status_code=400, detail="您的申请已通过，无需重复提交")
        # 未通过 → 覆盖原申请，重置为待审核
        existing.mc_id = data.mc_id
        existing.email = data.email
        existing.faction = data.faction
        existing.experience = data.experience
        existing.weekly_hours = data.weekly_hours
        existing.motivation = data.motivation
        existing.status = STATUS_PENDING
        existing.review_note = ""
        existing.review_time = None
        existing.update_time = now
        await db.commit()
        await db.refresh(existing)
        return {
            "code": 0,
            "message": "已重新提交申请，请等待管理员审核",
            "data": _dump(existing),
        }

    obj = FactionBetaApplication(
        username=user.username,
        mc_id=data.mc_id,
        email=data.email,
        faction=data.faction,
        experience=data.experience,
        weekly_hours=data.weekly_hours,
        motivation=data.motivation,
        status=STATUS_PENDING,
        review_note="",
        review_time=None,
        create_time=now,
        update_time=now,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return {"code": 0, "message": "申请已提交，请等待管理员审核", "data": _dump(obj)}


# ── 用户端：查询自己的申请 ────────────────────────────────────────
@router.get("/my")
async def my_application(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询当前登录用户的申请（未提交时 data.application 为 null）。"""
    obj = await _get_by_username(db, user.username)
    return {
        "code": 0,
        "message": "success",
        "data": {"application": _dump(obj) if obj is not None else None},
    }


# ── 管理端：分页查询 ─────────────────────────────────────────────
@router.get("/admin/page", response_model=FactionBetaPageResponse)
async def admin_page(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    status: Optional[int] = Query(default=None, description="0=待审核, 1=已通过, 2=未通过；缺省查全部"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：分页查询内测申请（可按状态过滤，按提交时间倒序）。"""
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    stmt = select(FactionBetaApplication)
    count_stmt = select(func.count()).select_from(FactionBetaApplication)
    if status is not None:
        stmt = stmt.where(FactionBetaApplication.status == status)
        count_stmt = count_stmt.where(FactionBetaApplication.status == status)

    stmt = stmt.order_by(FactionBetaApplication.id.desc()).offset(offset).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    items = (await db.execute(stmt)).scalars().all()
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "total": total,
        "hasNext": page < total_pages,
        "hasPrev": page > 1,
    }


# ── 管理端：审核 ─────────────────────────────────────────────────
@router.put("/admin/{application_id}/review")
async def review(
    application_id: int,
    data: FactionBetaReviewRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """审核申请：通过 / 拒绝（可选审核备注，展示给申请人）。"""
    if data.status not in (STATUS_APPROVED, STATUS_REJECTED):
        raise HTTPException(status_code=400, detail="status 仅支持 1（通过）或 2（拒绝）")

    result = await db.execute(
        select(FactionBetaApplication).where(FactionBetaApplication.id == application_id)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="申请不存在")

    obj.status = data.status
    obj.review_note = (data.review_note or "").strip()
    obj.review_time = _now_iso()
    obj.update_time = _now_iso()
    await db.commit()
    await db.refresh(obj)
    return {"code": 0, "message": "审核完成", "data": _dump(obj)}


# ── 管理端：删除 ─────────────────────────────────────────────────
@router.delete("/admin/{application_id}")
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """删除申请（不可恢复）。"""
    result = await db.execute(
        select(FactionBetaApplication).where(FactionBetaApplication.id == application_id)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    await db.delete(obj)
    await db.commit()
    return {"code": 0, "message": "success"}
