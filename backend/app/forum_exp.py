"""论坛经验 / 等级 / 头衔的写入与读取helper（FLPR-36）。

抽成独立模块的原因：写入点分散在 forum.py（过审、两个点赞 toggle）与
auth/router.py（每日登录），而 forum.py 顶部是完整 APIRouter + 大量 Pydantic 模型，
登录模块冷 import 它代价很高（forum_core.py 的同款考量）。本模块只依赖 database.py，
两边都能安全引用。

核心不变量：
- 经验只增不减；发放以 forum_exp_ledger 的 `INSERT OR IGNORE` rowcount=1 为唯一触发点。
  点赞关系表取消时物理删行，若以"关系表新增行"为触发点，取消再点回会重复加经验；
  ledger 的 dedup_key 唯一约束让"取消再点回"天然不发第二次经验。
- 已注销 / 禁用用户（users.status != 1）不再累计经验；历史 forum_user_exp 行不删，
  故历史等级徽章仍正常展示。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .crud import _TZ
from .database import (
    FORUM_EXP_DAILY_LOGIN,
    FORUM_LEVEL_SEED,
    FORUM_TITLE_META,
    ForumExpLedger,
    ForumUserExp,
    ForumUserTitle,
    User,
)


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def level_for_exp(exp: int) -> tuple[int, str]:
    """按阈值常量表求 (level, 等级名)；只取 required_exp <= exp 的最高档。"""
    level, name = 1, "见习旅人"
    for lv, lv_name, required in FORUM_LEVEL_SEED:
        if exp >= required:
            level, name = lv, lv_name
    return level, name


async def user_badges(db: AsyncSession, user: User) -> list[str]:
    """作者徽章数组：管理员 → 等级 → 生效中的手动头衔（顺序即展示顺序）。"""
    badges: list[str] = []
    if user.role == "admin":
        badges.append("管理员")

    r = await db.execute(
        select(ForumUserExp.level).where(ForumUserExp.user_id == user.id)
    )
    level = r.scalar_one_or_none() or 1
    badges.append(f"Lv.{level}")

    r = await db.execute(
        select(ForumUserTitle.title_code)
        .where(
            ForumUserTitle.user_id == user.id,
            ForumUserTitle.revoked_at == "",
        )
        .order_by(ForumUserTitle.granted_at.asc(), ForumUserTitle.id.asc())
    )
    for code in r.scalars().all():
        meta = FORUM_TITLE_META.get(code)
        if meta:
            badges.append(meta["text"])
    return badges


async def grant_exp(
    db: AsyncSession,
    user_id: int,
    amount: int,
    dedup_key: str,
    reason: str,
    ref_id: int = 0,
    actor_id: int = 0,
) -> bool:
    """发放经验（幂等）。返回 True 表示本次真正入账。调用方负责 commit。

    dedup_key 由各写入点自行拼装，必须能唯一标识"一次应发经验的行为"：
      article_publish:<article_id>:<create_time>
      article_like:<article_id>:<create_time>:<liker_id>
      comment_like:<comment_id>:<create_time>:<liker_id>
      daily_login:<YYYY-MM-DD>:<user_id>
    内容 id 后带 create_time 是因为 SQLite 在物理删行后会复用 rowid
    （如作者删评论），只用 id 会与新内容的旧 ledger 行误撞、漏发经验。
    """
    if amount <= 0 or not dedup_key:
        return False
    # 封存 / 已删除 / 不存在用户不再累计
    r = await db.execute(select(User.status).where(User.id == user_id))
    status = r.scalar_one_or_none()
    if status != 1:
        return False

    now = _now_iso()
    res = await db.execute(
        text(
            "INSERT OR IGNORE INTO forum_exp_ledger "
            "(user_id, amount, reason, ref_id, actor_id, dedup_key, create_time) "
            "VALUES (:user_id, :amount, :reason, :ref_id, :actor_id, :dedup_key, :create_time)"
        ),
        {
            "user_id": user_id,
            "amount": amount,
            "reason": reason,
            "ref_id": ref_id,
            "actor_id": actor_id,
            "dedup_key": dedup_key,
            "create_time": now,
        },
    )
    if res.rowcount != 1:
        return False  # 已发过（含取消再点回），不重复加

    await db.execute(
        text(
            "INSERT OR IGNORE INTO forum_user_exp (user_id, exp, level, update_time) "
            "VALUES (:user_id, 0, 1, :now)"
        ),
        {"user_id": user_id, "now": now},
    )
    await db.execute(
        text(
            "UPDATE forum_user_exp SET exp = exp + :amount, update_time = :now "
            "WHERE user_id = :user_id"
        ),
        {"amount": amount, "now": now, "user_id": user_id},
    )
    r = await db.execute(
        select(ForumUserExp.exp).where(ForumUserExp.user_id == user_id)
    )
    level, _name = level_for_exp(r.scalar_one() or 0)
    await db.execute(
        text("UPDATE forum_user_exp SET level = :level WHERE user_id = :user_id"),
        {"level": level, "user_id": user_id},
    )
    return True


async def grant_daily_login_exp(db: AsyncSession, user_id: int) -> bool:
    """每日登录 +1，同一自然日（北京时间）只发一次。"""
    today = datetime.now(_TZ).strftime("%Y-%m-%d")
    return await grant_exp(
        db,
        user_id=user_id,
        amount=FORUM_EXP_DAILY_LOGIN,
        dedup_key=f"daily_login:{today}:{user_id}",
        reason="daily_login",
    )


async def user_exp_detail(db: AsyncSession, user_id: int) -> Optional[dict]:
    """当前经验进度（后台用户管理展示用；无记录视为 0 经验 / Lv.1）。"""
    r = await db.execute(
        select(ForumUserExp.exp, ForumUserExp.level, ForumUserExp.update_time).where(
            ForumUserExp.user_id == user_id
        )
    )
    row = r.one_or_none()
    if row is None:
        return {"exp": 0, "level": 1, "levelName": level_for_exp(0)[1], "updateTime": ""}
    exp_value, level, update_time = row
    return {
        "exp": exp_value,
        "level": level,
        "levelName": level_for_exp(exp_value)[1],
        "updateTime": update_time,
    }
