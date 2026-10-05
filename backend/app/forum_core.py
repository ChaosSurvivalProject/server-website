"""社区（论坛）轻量核心逻辑（**纯 SQLAlchemy，不 import FastAPI/pydjango**）。

存在原因（与 app/staff_core.py 同款，2026-09-25 生产实测）：清理 CLI
``backend/forum_purge.py`` 需要与"作者彻底删除"共用**同一个级联删除与超期判定**
实现（语义唯一，见 docs/论坛/论坛删除与回收站PRD.md §1.3 / §5.3 / §6-D9），
而 ``app/forum.py`` 顶部是完整 APIRouter + 全部 pydantic 模型（96KB、2294 行），
CLI 冷 import 实测 33s 起、内存紧张时分钟级——**CLI 绝不能 import 它**。
因此把这几件只依赖 SQLAlchemy 的东西沉到本模块：

  RECYCLE_DAYS                30 天保留期（**唯一来源**，接口下发 recycleDays）
  recycle_days_left()         剩余可恢复天数（前端不自己算）
  is_recycle_expired()        是否已超 30 天
  purge_due()                 超期回收站帖物理清理（CLI / 启动兜底共用）
  cascade_delete_article()    文章硬删除级联（作者彻底删除 / 管理员硬删 / 超期清理共用）

``app/forum.py`` 从这里 import 并 re-export，于是查询路径与定时路径语义仍唯一。
"""
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import (
    ForumArticle,
    ForumArticleFavorite,
    ForumArticleLike,
    ForumArticleTag,
    ForumComment,
    ForumCommentLike,
    ForumTag,
)

# 统一北京时间 naive ISO（AGENTS.md 存储约定，与 app.crud._TZ / app.forum._now_iso 同值）；
# 刻意本地实现而不 import app.crud——那会连带拖入 pydantic/nh3，破坏本模块轻量性。
_TZ = ZoneInfo("Asia/Shanghai")


# ── 状态枚举（后端唯一权威，app.forum re-export 对外；前端文案表需与此保持一致）───
STATUS_PENDING = 0    # 待审核
STATUS_PUBLISHED = 1  # 已发布
STATUS_REJECTED = 2   # 已驳回
STATUS_OFFLINE = 3    # 已下架（管理员）
STATUS_RECYCLED = 4   # 回收站（作者删除后的保留态）

RECYCLE_DAYS = 30  # 回收站保留天数（前端只显示接口下发的 recycleDays，不硬编码）

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"
_DAY_SECONDS = 86400


# ── 时间口径（与 app/forum.py::_is_muted 同坑） ─────────────────────
# 库里存的是**北京时间 naive** ISO 串，_parse_iso() 解析出来的也必然是 naive；
# 而 datetime.now(_TZ) 带 tzinfo——两者直接比较/相减会抛
# "can't compare offset-naive and offset-aware datetimes"（2026-10-05 踩过，
# 与 _is_muted() 对 mute_until 那条同源）。本模块所有日期比较一律走
# _now_naive()（墙时间 naive），**严禁直接写 datetime.now(_TZ)** 参与运算。
def _now_naive() -> datetime:
    return datetime.now(_TZ).replace(tzinfo=None)


def _now_or(value: Optional[str]) -> datetime:
    """调用方（测试 / CLI）可注入 now（ISO 串），否则取当前 naive 北京时间。"""
    return _parse_iso(value) or _now_naive()


def _now_iso() -> str:
    return datetime.now(_TZ).strftime(_ISO_FMT)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, _ISO_FMT)
    except ValueError:
        return None


def _cutoff_iso(now: Optional[str] = None) -> str:
    """30 天前的北京时间 ISO（超期清理的判定时刻）。"""
    base = _now_or(now)
    return (base - timedelta(days=RECYCLE_DAYS)).strftime(_ISO_FMT)


def recycle_days_left(deleted_at: Optional[str], now: Optional[str] = None) -> int:
    """剩余可恢复天数（**后端算，前端只显示**，PRD §7.4）。

    - deleted_at 空/格式异常 → 0（不在回收站或数据异常，不该显示"还有 N 天"）；
    - 已超 30 天 → 0（前端据此显示「今天到期」，且列表已过滤不再出现）；
    - 其余 → 向上取整的整天数，删后第 1 天返回 30。
    """
    deleted = _parse_iso(deleted_at)
    if deleted is None:
        return 0
    base = _now_or(now)
    remain = RECYCLE_DAYS * _DAY_SECONDS - (base - deleted).total_seconds()
    if remain <= 0:
        return 0
    return int((remain + _DAY_SECONDS - 1) // _DAY_SECONDS)


def is_recycle_expired(deleted_at: Optional[str], now: Optional[str] = None) -> bool:
    """是否已过保留期。**deleted_at 是唯一权威**（PRD §0.4-F）。"""
    deleted = _parse_iso(deleted_at)
    if deleted is None:
        return False
    base = _now_or(now)
    return (base - deleted).total_seconds() > RECYCLE_DAYS * _DAY_SECONDS


# ── 标签 use_count 原子增减（口径与 app.forum._bump_tag_use_count 完全一致）───
async def _tag_ids_of(db: AsyncSession, article_id: int) -> list[int]:
    r = await db.execute(
        select(ForumArticleTag.tag_id).where(ForumArticleTag.article_id == article_id)
    )
    return list(r.scalars().all())


async def _bump_tag_use_count(db: AsyncSession, tag_ids: list[int], delta: int) -> None:
    """use_count 原子增减（禁止 read-modify-write，否则并发下丢计数）。"""
    if not tag_ids or delta == 0:
        return
    await db.execute(
        update(ForumTag)
        .where(ForumTag.id.in_(tag_ids))
        .values(use_count=ForumTag.use_count + delta)
    )


async def cascade_delete_article(db: AsyncSession, article: ForumArticle) -> None:
    """物理删除一篇文章及其全部关联数据（不留孤儿行）。

    三条删除路径**共用本函数**，语义唯一（PRD §6-D9 / §5.3）：
      1. 作者在回收站页面点「删除」（purge，立即物理删，不可恢复）；
      2. 管理员后台硬删（一直存在的行为，本 PRD 不改其口径）；
      3. forum_purge.py 超期自动清理。

    标签 use_count：**只在删前确为 status=1 时扣减一次**。回收站帖（status=4）
    进站时已由 _set_article_status(4) 扣过，这里再判 status==1 天然不会重复扣。
    文件（封面 / 正文内嵌图）**不删**——图床冗余清理归第三阶段（PRD §6-D12）。
    """
    if article.status == STATUS_PUBLISHED:
        await _bump_tag_use_count(db, await _tag_ids_of(db, article.id), -1)
    comment_ids = list(
        (
            await db.execute(
                select(ForumComment.id).where(ForumComment.article_id == article.id)
            )
        )
        .scalars()
        .all()
    )
    if comment_ids:
        await db.execute(
            delete(ForumCommentLike).where(ForumCommentLike.comment_id.in_(comment_ids))
        )
    await db.execute(delete(ForumComment).where(ForumComment.article_id == article.id))
    await db.execute(
        delete(ForumArticleLike).where(ForumArticleLike.article_id == article.id)
    )
    await db.execute(
        delete(ForumArticleFavorite).where(ForumArticleFavorite.article_id == article.id)
    )
    await db.execute(
        delete(ForumArticleTag).where(ForumArticleTag.article_id == article.id)
    )
    await db.delete(article)
    await db.flush()


async def due_recycle_ids(db: AsyncSession, now: Optional[str] = None) -> list[int]:
    """已超保留期的回收站文章 id（dry-run 与实跑共用同一查询，口径不漂）。"""
    cutoff = _cutoff_iso(now)
    r = await db.execute(
        select(ForumArticle.id)
        .where(
            ForumArticle.status == STATUS_RECYCLED,
            ForumArticle.deleted_at != "",
            ForumArticle.deleted_at < cutoff,
        )
        .order_by(ForumArticle.id.asc())
    )
    return list(r.scalars().all())


async def purge_due(
    db: AsyncSession, dry_run: bool = False, now: Optional[str] = None
) -> tuple[int, list[int]]:
    """超期回收站帖物理清理。

    返回 (清理条数, 文章 id 列表)。**幂等**：第二次跑已无 due 行，返回 0。
    漏挂 crontab 不影响正确性（恢复接口自校验 + 列表自过滤，超期帖用户根本
    看不到也恢复不了，数据只是多留几天，与员工名片 valid_to 同款口径）。

    ``--dry-run`` 只统计不写库，输出格式对齐 staff_expire.py。
    """
    ids = await due_recycle_ids(db, now)
    if dry_run or not ids:
        return len(ids), ids
    for article_id in ids:
        article = (
            await db.execute(select(ForumArticle).where(ForumArticle.id == article_id))
        ).scalar_one_or_none()
        if article is None:
            continue
        await cascade_delete_article(db, article)
    await db.commit()
    return len(ids), ids
