"""员工名片核心状态逻辑（纯 SQLAlchemy，无 FastAPI/pydantic 依赖）。

独立成模块的原因（2026-09-25 生产实测）：规格 §4.5 硬规则要求查询路径
（公开验证接口懒更新 / main.py 启动兜底）与定时批量（staff_expire.py CLI）
共用同一个 expire_due——语义唯一；但 app.staff 顶部是完整的 APIRouter，
import 即构建全部路由的 pydantic/fastapi schema，而生产机内存仅 122MB 且
CPU 有配额，CLI 冷 import 实测 33s、内存紧张时放大到分钟级。定时任务改为
从本模块 import 绕开路由构建；app.staff 从这里 re-export，两条路径语义仍唯一。
"""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Staff

# 统一北京时间 naive ISO（AGENTS.md 存储约定，与 app.crud._TZ / _now_iso 同值）；
# 刻意本地实现而不 import app.crud——那会连带拖入 pydantic/nh3，破坏本模块轻量性
_TZ = ZoneInfo("Asia/Shanghai")


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


# 状态枚举（后端唯一权威，app.staff re-export 对外；前端选项需与此保持一致）
STAFF_STATUS_ACTIVE = "active"
STAFF_STATUS_REVOKED = "revoked"
REVOKE_REASON_EXPIRED = "expired"  # 仅由到期回写写入，后台撤销下拉不可见

# 派生态（对外四态，规格 §6）：valid / revoked（人工撤销）/ expired / not_found
STATE_VALID = "valid"
STATE_REVOKED = "revoked"
STATE_EXPIRED = "expired"
STATE_NOT_FOUND = "not_found"


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
