"""员工名片模块：/staff/*（对外经 main.py 统一挂 /api 前缀 → /api/staff/*）。

实施唯一依据：docs/员工名片模块需求规格.md（v1.1）+ docs/员工名片模块评审与落地方案.md §6.2。

接口一览（附录 A）：

  GET  /staff/public/{code}               验证页数据（匿名，白名单模型，四态）
  GET  /staff/public/team                 管理组总览（匿名，仅有效期内公开字段）

  GET  /staff/admin/page                  台账分页（状态过滤 + keyword）
  GET  /staff/admin/stats                 顶部统计条（有效/即将到期/已过期/已撤销）
  POST /staff/admin                       新增工作人员（自动生成身份码 + valid_from/to）
  PUT  /staff/admin/{id}                  编辑公开信息（公开字段变更时 card_version 自增）
  POST /staff/admin/{id}/regenerate-code  重生成身份码（旧码立即失效）
  POST /staff/admin/{id}/revoke           撤销（body: {reason}，仅接受 离职/转岗/暂停/码异常）
  POST /staff/admin/{id}/restore          恢复（必须换新身份码，规格 §8.1）
  POST /staff/admin/{id}/renew            续期一年（因到期失效则自动恢复 active）
  GET  /staff/admin/{id}/qrcode           二维码 PNG（后端生成，URL 由 STAFF_PUBLIC_BASE_URL 拼接）
  GET  /staff/admin/export                导出名单 CSV（仅管理员；规格 §10.1 豁免点，见 AGENTS.md）

所有接口遵循项目统一响应包络 {code, message, data}（code=0 成功）；
二维码 PNG 与 CSV 导出为二进制/文件响应，不走包络。
业务失败以 HTTPException(400/401/403/404, detail=...) 抛出。

⚠️ 豁免约定（需求 §10.1 与 §8.1 的矛盾解，勿当漏洞"修掉"）：
  公开接口一律不下发完整身份码（验证页白名单只含展示码后四位）；
  「导出名单」与 admin 台账是 require_admin 管理端接口，允许下发完整码。
  限流与查询日志（staff_verify_log）按拍板顺延 P1，P0 不实现（§4.6/§4.7）。
"""
import csv
import io
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import require_admin
from .config import STAFF
from .crud import _TZ  # 统一北京时间（naive ISO 字符串，见 AGENTS.md 存储约定）
from .database import Staff, User, get_db

router = APIRouter(prefix="/staff", tags=["staff"])

# ── 常量（后端为唯一权威，前端选项需与此保持一致） ─────────────────
# 职务（规格 §7.1 / §8.3 推荐色由前端常量表维护，颜色只区分职务不代表权限）
ROLE_OPTIONS = ["服主", "技术员", "财务", "管理员", "建筑", "客服"]

# 撤销原因（规格 §6.2）：人工撤销四分类，后台下拉只能选不能填，避免文案漂移；
# 'expired' 是第五个枚举值，仅由到期回写写入（expire_due），后台不可选。
MANUAL_REVOKE_REASONS = ["离职", "转岗", "暂停", "码异常"]
REVOKE_REASON_EXPIRED = "expired"

STAFF_STATUS_ACTIVE = "active"
STAFF_STATUS_REVOKED = "revoked"

# 身份码：12 位 × 32 字符表（小写字母 + 数字，去掉易混的 0 1 l o），熵 = 60 bit
# （规格 §4.1 / §0.3 定稿项 2：全小写 → 查询侧不做大小写归一，只 strip()）
STAFF_CODE_LENGTH = 12
STAFF_CODE_CHARS = "23456789abcdefghijkmnpqrstuvwxyz"
_CODE_RE = re.compile(rf"^[{re.escape(STAFF_CODE_CHARS)}]{{{STAFF_CODE_LENGTH}}}$")

# 有效期 1 年；"即将到期"高亮阈值 30 天（规格 §5 / §8.1）
VALID_YEARS = 1
EXPIRING_SOON_DAYS = 30

# 公开接口单条查询码长度上限（超过直接按"未找到"处理，防超长输入打库）
_MAX_QUERY_CODE_LEN = 64

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# 派生态（对外四态，规格 §6）：valid / revoked（人工撤销）/ expired / not_found
STATE_VALID = "valid"
STATE_REVOKED = "revoked"
STATE_EXPIRED = "expired"
STATE_NOT_FOUND = "not_found"


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _parse_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def _fmt_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _add_one_year(dt: datetime) -> datetime:
    """+1 年（2/29 归 2/28）。"""
    try:
        return dt.replace(year=dt.year + VALID_YEARS)
    except ValueError:  # 2 月 29 日
        return dt.replace(year=dt.year + VALID_YEARS, month=2, day=28)


def _expiring_threshold(now: str) -> str:
    """即将到期阈值：now + 30 天。"""
    return _fmt_iso(_parse_iso(now) + timedelta(days=EXPIRING_SOON_DAYS))


def _bump_card_version(version: str) -> str:
    """名片版本自增（V1 → V2 → …）。解析失败时从残留数字续，再退回 V1。"""
    m = re.fullmatch(r"V(\d+)", version or "")
    if m:
        return f"V{int(m.group(1)) + 1}"
    digits = re.sub(r"\D", "", version or "")
    return f"V{int(digits) + 1}" if digits else "V1"


# ── 状态判定 / 到期回写（两条触发路径共用，规格 §4.5） ───────────────


def derive_state(row: Staff, now: Optional[str] = None) -> str:
    """派生对外状态。判定权威是 valid_to，status 只是快照（§4.5 规则 2）。

    优先级 revoked ＞ expired ＞ active（规格 §8.4）：
    - 人工撤销（reason ∈ 离职/转岗/暂停/码异常）恒为 revoked，即使有效期也已过；
    - reason='expired' 的撤销行 → expired；
    - active 行若 valid_to 已过（懒更新未落库的间隙）→ expired（valid_to 兜底）。
    """
    now = now or _now_iso()
    if row.status == STAFF_STATUS_REVOKED:
        if (row.revoked_reason or "") == REVOKE_REASON_EXPIRED:
            return STATE_EXPIRED
        return STATE_REVOKED
    if row.valid_to and row.valid_to < now:
        return STATE_EXPIRED
    return STATE_VALID


async def expire_due(db: AsyncSession, only_id: Optional[int] = None) -> int:
    """到期回写：把 status='active' 且 now > valid_to 的行刷成 revoked('expired')。

    幂等（仅 active → revoked 写一次）；查询路径（公开验证接口命中时传 only_id）
    与定时批量（staff_expire.py / main.py 启动时全表）共用本函数，语义唯一。
    返回刷新行数。
    """
    now = _now_iso()
    stmt = (
        update(Staff)
        .where(Staff.status == STAFF_STATUS_ACTIVE, Staff.valid_to < now)
        .values(
            status=STAFF_STATUS_REVOKED,
            revoked_reason=REVOKE_REASON_EXPIRED,
            revoked_at=now,
            update_time=now,
        )
    )
    if only_id is not None:
        stmt = stmt.where(Staff.id == only_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0


# ── 身份码 ────────────────────────────────────────────────────────


def _random_code() -> str:
    return "".join(secrets.choice(STAFF_CODE_CHARS) for _ in range(STAFF_CODE_LENGTH))


async def _generate_unique_code(db: AsyncSession) -> str:
    """安全随机生成 12 位身份码，插入前查重，冲突重试（规格 §4.1）。"""
    for _ in range(10):
        code = _random_code()
        exists = (
            await db.execute(select(Staff.id).where(Staff.staff_code == code))
        ).scalar_one_or_none()
        if exists is None:
            return code
    raise HTTPException(status_code=500, detail="身份码生成失败，请重试")


def _set_new_code(row: Staff, code: str) -> None:
    row.staff_code = code
    row.display_code = code[-4:]


# ── 响应模型（白名单） ────────────────────────────────────────────


class StaffAdminResponse(BaseModel):
    """管理端台账视图（require_admin；完整 staffCode 仅在此下发——
    公开接口不下发完整码，导出豁免说明见 AGENTS.md 与本模块 docstring）。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    staff_code: str = Field(..., alias="staffCode")
    display_code: str = Field(..., alias="displayCode")
    game_id: str = Field(..., alias="gameId")
    nickname: Optional[str] = None
    role: str
    duty: str
    avatar_path: str = Field(default="", alias="avatarPath")
    public_email: Optional[str] = Field(default=None, alias="publicEmail")
    status: str
    card_version: str = Field(..., alias="cardVersion")
    valid_from: str = Field(..., alias="validFrom")
    valid_to: str = Field(..., alias="validTo")
    remark: str = ""
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")
    revoked_at: Optional[str] = Field(default=None, alias="revokedAt")
    revoked_reason: str = Field(default="", alias="revokedReason")
    state: str = STATE_VALID  # 派生态：valid | revoked | expired（前端展示用）
    expiring_soon: bool = Field(default=False, alias="expiringSoon")  # ≤30 天即将到期


def _admin_payload(row: Staff, now: Optional[str] = None) -> dict:
    now = now or _now_iso()
    return {
        "id": row.id,
        "staffCode": row.staff_code,
        "displayCode": row.display_code,
        "gameId": row.game_id,
        "nickname": row.nickname,
        "role": row.role,
        "duty": row.duty,
        "avatarPath": row.avatar_path or "",
        "publicEmail": row.public_email,
        "status": row.status,
        "cardVersion": row.card_version,
        "validFrom": row.valid_from,
        "validTo": row.valid_to,
        "remark": row.remark or "",
        "createTime": row.create_time,
        "updateTime": row.update_time,
        "revokedAt": row.revoked_at,
        "revokedReason": row.revoked_reason or "",
        "state": derive_state(row, now),
        "expiringSoon": bool(
            row.status == STAFF_STATUS_ACTIVE
            and row.valid_to >= now
            and row.valid_to <= _expiring_threshold(now)
        ),
    }


def _dump_admin(row: Staff, now: Optional[str] = None) -> dict:
    return StaffAdminResponse(**_admin_payload(row, now)).model_dump(by_alias=True)


class StaffPageResponse(BaseModel):
    """分页结构（与公告 PageResponse 保持一致）。"""

    items: list[dict]
    page: int
    pageSize: int
    totalPages: int
    total: int
    hasNext: bool
    hasPrev: bool


# ── 请求模型 ──────────────────────────────────────────────────────


class StaffCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    game_id: str = Field(..., alias="gameId", max_length=50, description="游戏 ID")
    nickname: Optional[str] = Field(None, alias="nickname", max_length=50, description="公开昵称")
    role: str = Field(..., max_length=30, description="职务")
    duty: str = Field(..., min_length=1, max_length=1000, description="职责范围")
    avatar_path: Optional[str] = Field(None, alias="avatarPath", max_length=512, description="头像相对 URL")
    public_email: Optional[str] = Field(None, alias="publicEmail", max_length=255, description="工作邮箱")
    remark: Optional[str] = Field(None, max_length=255, description="内部备注（任何对外响应不下发）")

    @field_validator("game_id", "nickname", "role", "duty", "avatar_path", "public_email", "remark", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class StaffUpdateRequest(BaseModel):
    """编辑公开信息：公开字段（gameId/nickname/role/duty/avatarPath/publicEmail）
    任一变更时 card_version 自动递增；remark 是内部备注，不计入。"""

    model_config = ConfigDict(populate_by_name=True)

    game_id: Optional[str] = Field(None, alias="gameId", max_length=50)
    nickname: Optional[str] = Field(None, alias="nickname", max_length=50)
    role: Optional[str] = Field(None, max_length=30)
    duty: Optional[str] = Field(None, min_length=1, max_length=1000)
    avatar_path: Optional[str] = Field(None, alias="avatarPath", max_length=512)
    public_email: Optional[str] = Field(None, alias="publicEmail", max_length=255)
    remark: Optional[str] = Field(None, max_length=255)

    @field_validator("game_id", "nickname", "role", "duty", "avatar_path", "public_email", "remark", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class RevokeRequest(BaseModel):
    reason: str = Field(..., max_length=30, description="撤销原因：离职/转岗/暂停/码异常")


def _validate_role(role: str) -> None:
    if role not in ROLE_OPTIONS:
        raise HTTPException(status_code=400, detail=f"职务仅支持：{' / '.join(ROLE_OPTIONS)}")


def _validate_email(email: Optional[str]) -> None:
    if email and (not _EMAIL_RE.fullmatch(email) or len(email) > 254):
        raise HTTPException(status_code=400, detail="请填写正确的工作邮箱地址")


async def _get_staff_or_404(db: AsyncSession, staff_id: int) -> Staff:
    row = (
        await db.execute(select(Staff).where(Staff.id == staff_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="工作人员不存在")
    return row


# ── 台账过滤（状态分类互斥；过期筛选双保险，规格 §4.5 规则 6） ────────


def _status_filter(status: str, now: str):
    """按台账筛选口径返回 SQLAlchemy 条件；'' 表示全部。

    分类互斥定义：
    - active   现任有效：status=active 且 valid_to ≥ now
    - expiring 即将到期：status=active 且 now ≤ valid_to ≤ now+30d
    - expired  已过期：reason='expired' 的撤销行，或 active 但 valid_to 已过
               （双保险：定时任务未跑 + 无人扫码期间也能被筛出）
    - revoked  已撤销（人工）：status=revoked 且 reason ≠ 'expired'
    """
    threshold = _expiring_threshold(now)
    if status == "active":
        return and_(Staff.status == STAFF_STATUS_ACTIVE, Staff.valid_to >= now)
    if status == "expiring":
        return and_(
            Staff.status == STAFF_STATUS_ACTIVE,
            Staff.valid_to >= now,
            Staff.valid_to <= threshold,
        )
    if status == "expired":
        return or_(
            Staff.revoked_reason == REVOKE_REASON_EXPIRED,
            and_(Staff.status == STAFF_STATUS_ACTIVE, Staff.valid_to < now),
        )
    if status == "revoked":
        return and_(
            Staff.status == STAFF_STATUS_REVOKED,
            Staff.revoked_reason != REVOKE_REASON_EXPIRED,
        )
    return None


async def _query_rows(db: AsyncSession, status: str, keyword: str):
    now = _now_iso()
    stmt = select(Staff)
    cond = _status_filter((status or "").strip(), now)
    if cond is not None:
        stmt = stmt.where(cond)
    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        stmt = stmt.where(or_(Staff.game_id.ilike(like), Staff.nickname.ilike(like)))
    stmt = stmt.order_by(Staff.id.desc())
    return (await db.execute(stmt)).scalars().all()


# ════════════════════════════ 公开接口 ════════════════════════════


def _not_found_response() -> dict:
    """"格式非法"与"确实不存在"必须逐字节一致（规格 §6.4 / §10.1）：
    统一 state=not_found，不带任何其他字段，不暴露判断逻辑。"""
    return {"code": 0, "message": "success", "data": {"state": STATE_NOT_FOUND}}


def _public_valid_payload(row: Staff) -> dict:
    """有效态白名单：不含 remark、不含完整 staffCode（只给展示码后四位）。"""
    return {
        "state": STATE_VALID,
        "displayCode": row.display_code,
        "gameId": row.game_id,
        "nickname": row.nickname,
        "role": row.role,
        "duty": row.duty,
        "avatarPath": row.avatar_path or "",
        "publicEmail": row.public_email,
        "cardVersion": row.card_version,
        "updateTime": row.update_time,
        "validFrom": row.valid_from,
        "validTo": row.valid_to,
    }


@router.get("/public/team")
async def public_team(db: AsyncSession = Depends(get_db)):
    """管理组总览（匿名）：仅现任且在有效期内的公开字段（白名单，规格 §9.2）。

    本页是有意公开的现任名录，与"不能通过验证页查别人"不冲突（规格 §5-#11）。
    """
    now = _now_iso()
    rows = (
        (
            await db.execute(
                select(Staff)
                .where(Staff.status == STAFF_STATUS_ACTIVE, Staff.valid_to >= now)
                .order_by(Staff.id.asc())
            )
        )
        .scalars()
        .all()
    )
    items = [
        {
            "gameId": r.game_id,
            "nickname": r.nickname,
            "role": r.role,
            "duty": r.duty,
            "avatarPath": r.avatar_path or "",
        }
        for r in rows
    ]
    return {"code": 0, "message": "success", "data": {"items": items, "total": len(items)}}


@router.get("/public/{code}")
async def public_verify(code: str, db: AsyncSession = Depends(get_db)):
    """验证页数据（匿名，四态；规格 §6 / §9.1）。

    - 查询只做 strip()（身份码本就全小写，不做大小写归一）；
    - 格式非法 / 不存在 / 超长输入 → 同一响应体（state=not_found）；
    - 命中 active 且已过期的行先懒更新（expire_due，幂等），再按派生态返回；
    - 撤销/过期态是白名单：只返回状态（与原因），其余字段全部不下发（§6.2）。
    """
    code = (code or "").strip()
    if len(code) > _MAX_QUERY_CODE_LEN or not _CODE_RE.fullmatch(code):
        return _not_found_response()

    row = (
        await db.execute(select(Staff).where(Staff.staff_code == code))
    ).scalar_one_or_none()
    if row is None:
        return _not_found_response()

    # 查询时懒更新（规格 §4.5 触发路径 1）：active 且已过期 → 回写 revoked('expired')
    if row.status == STAFF_STATUS_ACTIVE and row.valid_to < _now_iso():
        await expire_due(db, only_id=row.id)
        await db.refresh(row)

    state = derive_state(row)
    if state == STATE_VALID:
        return {"code": 0, "message": "success", "data": _public_valid_payload(row)}
    if state == STATE_EXPIRED:
        return {"code": 0, "message": "success", "data": {"state": STATE_EXPIRED}}
    # 人工撤销：只回状态 + 原因分类（离职/转岗/暂停/码异常）
    return {
        "code": 0,
        "message": "success",
        "data": {"state": STATE_REVOKED, "reason": row.revoked_reason or ""},
    }


# ════════════════════════════ 管理端接口 ══════════════════════════


@router.get("/admin/page")
async def admin_page(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    status: str = Query(default="", description="active|expiring|expired|revoked，空=全部"),
    keyword: str = Query(default="", max_length=50, description="按游戏ID/昵称模糊搜索"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """台账分页（覆盖"查看历史人员"；即将到期行由 expiringSoon 标记供前端高亮）。"""
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    # 过滤条件先拼进 count，再分页取当页
    base_cond = _status_filter((status or "").strip(), _now_iso())
    kw = (keyword or "").strip()
    kw_cond = None
    if kw:
        like = f"%{kw}%"
        kw_cond = or_(Staff.game_id.ilike(like), Staff.nickname.ilike(like))

    count_stmt = select(func.count()).select_from(Staff)
    if base_cond is not None:
        count_stmt = count_stmt.where(base_cond)
    if kw_cond is not None:
        count_stmt = count_stmt.where(kw_cond)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = select(Staff)
    if base_cond is not None:
        stmt = stmt.where(base_cond)
    if kw_cond is not None:
        stmt = stmt.where(kw_cond)
    stmt = stmt.order_by(Staff.id.desc()).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "items": [_dump_admin(r) for r in rows],
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "total": total,
        "hasNext": page < total_pages,
        "hasPrev": page > 1,
    }


@router.get("/admin/stats")
async def admin_stats(db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    """顶部统计条（规格 §5：提前 30 天提醒降级为后台可见性）。"""
    now = _now_iso()
    threshold = _expiring_threshold(now)

    async def _count(cond) -> int:
        return (await db.execute(select(func.count()).select_from(Staff).where(cond))).scalar_one()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": (await db.execute(select(func.count()).select_from(Staff))).scalar_one(),
            "active": await _count(
                and_(Staff.status == STAFF_STATUS_ACTIVE, Staff.valid_to >= now)
            ),
            "expiringSoon": await _count(
                and_(
                    Staff.status == STAFF_STATUS_ACTIVE,
                    Staff.valid_to >= now,
                    Staff.valid_to <= threshold,
                )
            ),
            "expired": await _count(
                or_(
                    Staff.revoked_reason == REVOKE_REASON_EXPIRED,
                    and_(Staff.status == STAFF_STATUS_ACTIVE, Staff.valid_to < now),
                )
            ),
            "revoked": await _count(
                and_(
                    Staff.status == STAFF_STATUS_REVOKED,
                    Staff.revoked_reason != REVOKE_REASON_EXPIRED,
                )
            ),
        },
    }


@router.post("/admin")
async def admin_create(
    data: StaffCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """新增工作人员：自动生成身份码，valid_from=now、valid_to=now+1 年（规格 §5/§12.1）。"""
    _validate_role(data.role)
    _validate_email(data.public_email)

    now = _now_iso()
    code = await _generate_unique_code(db)
    row = Staff(
        staff_code=code,
        display_code=code[-4:],
        game_id=data.game_id,
        nickname=data.nickname or None,
        role=data.role,
        duty=data.duty,
        avatar_path=data.avatar_path or "",
        public_email=data.public_email or None,
        status=STAFF_STATUS_ACTIVE,
        card_version="V1",
        valid_from=now,
        valid_to=_fmt_iso(_add_one_year(_parse_iso(now))),
        remark=data.remark or "",
        create_time=now,
        update_time=now,
        revoked_at=None,
        revoked_reason="",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"code": 0, "message": "已新增工作人员并生成身份码", "data": _dump_admin(row)}


@router.put("/admin/{staff_id}")
async def admin_update(
    staff_id: int,
    data: StaffUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """编辑公开信息；公开字段任一变更时 card_version 自动递增（规格 §8.1）。"""
    row = await _get_staff_or_404(db, staff_id)

    if data.role is not None:
        _validate_role(data.role)
    if data.public_email is not None:
        _validate_email(data.public_email)

    now = _now_iso()
    public_changed = False
    for field in ("game_id", "nickname", "role", "duty", "avatar_path", "public_email"):
        new_value = getattr(data, field)
        if new_value is None:
            continue
        if field == "avatar_path":
            new_value = new_value or ""
        old_value = getattr(row, field)
        if (old_value or None) != (new_value or None):
            setattr(row, field, new_value)
            public_changed = True
    if data.remark is not None:
        row.remark = data.remark
    if public_changed:
        row.card_version = _bump_card_version(row.card_version)
    row.update_time = now
    await db.commit()
    await db.refresh(row)
    return {"code": 0, "message": "已保存", "data": _dump_admin(row)}


@router.post("/admin/{staff_id}/regenerate-code")
async def admin_regenerate_code(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """重生成身份码：旧码立即失效（离职/转岗/码泄露/信息实质变化等场景，规格 §4.3/§12.4）。"""
    row = await _get_staff_or_404(db, staff_id)
    old_code = row.staff_code
    _set_new_code(row, await _generate_unique_code(db))
    row.card_version = _bump_card_version(row.card_version)
    row.update_time = _now_iso()
    await db.commit()
    await db.refresh(row)
    return {
        "code": 0,
        "message": "已重生成身份码，旧码立即失效",
        "data": {**_dump_admin(row), "oldStaffCode": old_code},
    }


@router.post("/admin/{staff_id}/revoke")
async def admin_revoke(
    staff_id: int,
    data: RevokeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """人工撤销（原因只能从四分类里选；'expired' 仅系统写入，规格 §4.5 规则 4）。"""
    reason = (data.reason or "").strip()
    if reason not in MANUAL_REVOKE_REASONS:
        raise HTTPException(
            status_code=400,
            detail=f"撤销原因仅支持：{' / '.join(MANUAL_REVOKE_REASONS)}",
        )
    row = await _get_staff_or_404(db, staff_id)
    if row.status == STAFF_STATUS_REVOKED:
        raise HTTPException(status_code=400, detail="该记录已是撤销状态")
    now = _now_iso()
    row.status = STAFF_STATUS_REVOKED
    row.revoked_reason = reason
    row.revoked_at = now
    row.update_time = now
    await db.commit()
    await db.refresh(row)
    return {"code": 0, "message": f"已撤销（{reason}）", "data": _dump_admin(row)}


@router.post("/admin/{staff_id}/restore")
async def admin_restore(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """恢复已撤销人员：清撤销字段 + **必须换新身份码**（旧码立即失效，规格 §8.1），
    card_version 自增。因到期失效的记录走「续期」救回（不换码），不走本接口。"""
    row = await _get_staff_or_404(db, staff_id)
    if row.status != STAFF_STATUS_REVOKED:
        raise HTTPException(status_code=400, detail="该记录不在撤销状态，无需恢复")
    now = _now_iso()
    row.status = STAFF_STATUS_ACTIVE
    row.revoked_at = None
    row.revoked_reason = ""
    _set_new_code(row, await _generate_unique_code(db))
    row.card_version = _bump_card_version(row.card_version)
    row.update_time = now
    # 有效期若已整体过完，恢复后立即过期会造成"恢复即失效"的怪态：顺延一年
    if row.valid_to < now:
        row.valid_from = now
        row.valid_to = _fmt_iso(_add_one_year(_parse_iso(now)))
    await db.commit()
    await db.refresh(row)
    return {"code": 0, "message": "已恢复并生成新身份码，旧码立即失效", "data": _dump_admin(row)}


@router.post("/admin/{staff_id}/renew")
async def admin_renew(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """续期一年（规格 §5 续期语义，规则不可省）：

    - active 且未过期：valid_to +1 年（二维码不变，旧码继续可用）；
    - 因到期而失效（reason='expired'）：自动恢复 active、清空撤销字段，再 +1 年——
      缺了这条会出现"续期已成功、玩家扫码却仍显示失效"的静默不一致（§4.5 规则 3）；
    - 人工撤销：拒绝（400），必须先 restore（restore 会换新码）。
    """
    row = await _get_staff_or_404(db, staff_id)
    now = _now_iso()

    if row.status == STAFF_STATUS_REVOKED and (row.revoked_reason or "") != REVOKE_REASON_EXPIRED:
        raise HTTPException(
            status_code=400,
            detail="人工撤销的记录不能直接续期，请先执行「恢复」（恢复将生成新身份码）",
        )

    rescued = False
    if row.status == STAFF_STATUS_REVOKED:  # reason == 'expired'：救回
        row.status = STAFF_STATUS_ACTIVE
        row.revoked_at = None
        row.revoked_reason = ""
        rescued = True

    # 已过期的行从 now 起算 +1 年；未过期从当前 valid_to 顺延（避免"恢复即再过期"）
    base = row.valid_to if row.valid_to > now else now
    row.valid_to = _fmt_iso(_add_one_year(_parse_iso(base)))
    row.update_time = now
    await db.commit()
    await db.refresh(row)
    return {
        "code": 0,
        "message": "已续期一年" + ("，并已恢复为有效（二维码不变，旧码继续可用）" if rescued else ""),
        "data": _dump_admin(row),
    }


@router.get("/admin/{staff_id}/qrcode")
async def admin_qrcode(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """二维码 PNG（后端生成；规格 §8.2 / §6.2.1）。

    - URL 由后端拼接 f"{STAFF_PUBLIC_BASE_URL}/staff/{staff_code}"，前端不得拼 URL；
    - 纠错 M + border=4 + box_size=10 → 410×410 px（印刷不糊，前端展示再 CSS 缩放）；
    - **禁止硬编码 version=**——交给库自动选版（当前 49 字节 URL 实测 v4 / 33×33），
      将来域名或码长变化时硬编码会直接抛 DataOverflowError。
    """
    row = await _get_staff_or_404(db, staff_id)
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except ImportError as e:  # pragma: no cover - requirements.txt 已含 qrcode
        raise HTTPException(status_code=500, detail="服务端未安装 qrcode 依赖") from e

    url = f"{STAFF.public_base_url}/staff/{row.staff_code}"
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)  # 版本自动选择，不硬编码
    img = qr.make_image(fill_color="black", back_color="white")  # 纯白底：承载区不得透明/深色
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


_CSV_HEADERS = [
    "ID", "游戏ID", "公开昵称", "职务", "职责范围", "状态", "名片版本",
    "身份码", "展示码", "生效时间", "到期时间", "撤销时间", "撤销原因",
    "工作邮箱", "头像URL", "创建时间", "更新时间", "内部备注",
]
_STATE_LABELS = {STATE_VALID: "有效", STATE_REVOKED: "已撤销", STATE_EXPIRED: "已过期"}


@router.get("/admin/export")
async def admin_export(
    status: str = Query(default="", description="active|expiring|expired|revoked，空=全部"),
    keyword: str = Query(default="", max_length=50),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """导出名单 CSV（仅管理员）——规格 §10.1「不返回完整身份码列表」的**唯一豁免点**
    （与 §8.1「导出当前名单」的需求矛盾解，豁免关系登记在 AGENTS.md，勿当漏洞修掉）。
    P0 无操作审计日志（§4.7 顺延），导出动作本身不留痕。"""
    rows = await _query_rows(db, status, keyword)
    now = _now_iso()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_HEADERS)
    for r in rows:
        writer.writerow([
            r.id,
            r.game_id,
            r.nickname or "",
            r.role,
            r.duty,
            _STATE_LABELS.get(derive_state(r, now), r.status),
            r.card_version,
            r.staff_code,
            r.display_code,
            r.valid_from,
            r.valid_to,
            r.revoked_at or "",
            r.revoked_reason or "",
            r.public_email or "",
            r.avatar_path or "",
            r.create_time,
            r.update_time,
            r.remark or "",
        ])
    data = "\ufeff" + buf.getvalue()  # UTF-8 BOM：Excel 直接打开不乱码
    filename = f"staff-{datetime.now(_TZ).strftime('%Y%m%d')}.csv"
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
