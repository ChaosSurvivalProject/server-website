"""CRUD operations for announcements."""
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from .database import Announcement
from .schemas import AnnouncementCreate, AnnouncementUpdate

# 统一时区：公告时间按北京时间存储（naive ISO 字符串，见 AGENTS.md 存储约定）。
# 此前误用 datetime.now(timezone.utc)，导致落库时间比实际早 8 小时。
_TZ = ZoneInfo("Asia/Shanghai")

# 富文本 HTML 写入消毒：content 由主站 v-html 渲染，入库前用 nh3 白名单过滤。
# 注意：nh3 的 attributes 参数会【整体覆盖】内置的每标签默认白名单——
# 只传 {"*": {"style"}} 会把 img 的 src/alt、a 的 href 等全部剥掉（踩过坑：
# 图片保存后再次编辑不显示）。因此这里显式枚举编辑器产物所需的全部属性；
# "*" 为所有标签通用的 style（保留对齐/颜色等内联样式）。
# URL 白名单用 nh3 默认（http/https/mailto + 相对路径，javascript: 会被剥）。
try:
    import nh3
except ImportError:  # pragma: no cover - 可选依赖，缺失时跳过消毒（不阻断启动）
    nh3 = None

_SANITIZE_ATTRIBUTES = {
    "*": {"style"},
    "a": {"href", "target"},
    "img": {"src", "alt", "width", "height", "href"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "ol": {"start"},
    "code": {"class"},
}


def _sanitize_content(html: str) -> str:
    if nh3 is None:
        return html
    return nh3.clean(html, attributes=_SANITIZE_ATTRIBUTES)


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _normalize_publish_time(value: str | None) -> str | None:
    """兼容客户端传来的带时区 ISO 串（如 "...Z"、"+00:00"），统一转为北京时间 naive ISO 存储。"""
    if not value:
        return value
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if dt.tzinfo is None:
        return value
    return dt.astimezone(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


async def create_announcement(db: AsyncSession, data: AnnouncementCreate) -> Announcement:
    now = _now_iso()
    obj = Announcement(
        title=data.title,
        content=_sanitize_content(data.content),
        is_published=data.is_published,
        creator=data.creator,
        publish_time=_normalize_publish_time(data.publish_time),
        read_count=0,
        create_time=now,
        update_time=now,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_announcement(db: AsyncSession, announcement_id: int) -> Announcement | None:
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    return result.scalar_one_or_none()


async def get_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    is_published: int | None = None,
) -> dict:
    """Return paginated announcements matching frontend expectations."""
    page = max(page, 1)
    page_size = max(page_size, 1)
    offset = (page - 1) * page_size

    # Build base query
    stmt = select(Announcement)
    count_stmt = select(func.count()).select_from(Announcement)

    if is_published is not None:
        stmt = stmt.where(Announcement.is_published == is_published)
        count_stmt = count_stmt.where(Announcement.is_published == is_published)

    # Order by id desc (newest first)
    stmt = stmt.order_by(Announcement.id.desc()).offset(offset).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(stmt)
    items = result.scalars().all()

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


async def update_announcement(
    db: AsyncSession,
    announcement_id: int,
    data: AnnouncementUpdate,
) -> Announcement | None:
    obj = await get_announcement(db, announcement_id)
    if obj is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("publish_time") is not None:
        update_data["publish_time"] = _normalize_publish_time(
            update_data["publish_time"]
        )
    if update_data.get("content") is not None:
        update_data["content"] = _sanitize_content(update_data["content"])
    for key, value in update_data.items():
        setattr(obj, key, value)
    obj.update_time = _now_iso()

    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_announcement(db: AsyncSession, announcement_id: int) -> bool:
    obj = await get_announcement(db, announcement_id)
    if obj is None:
        return False
    await db.delete(obj)
    await db.commit()
    return True


async def add_watch_count(db: AsyncSession, announcement_id: int) -> bool:
    """Increment read_count by 1."""
    result = await db.execute(
        update(Announcement)
        .where(Announcement.id == announcement_id)
        .values(read_count=Announcement.read_count + 1)
    )
    await db.commit()
    return result.rowcount > 0