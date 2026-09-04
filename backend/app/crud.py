"""CRUD operations for announcements."""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from .database import Announcement
from .schemas import AnnouncementCreate, AnnouncementUpdate


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


async def create_announcement(db: AsyncSession, data: AnnouncementCreate) -> Announcement:
    now = _now_iso()
    obj = Announcement(
        title=data.title,
        content=data.content,
        is_published=data.is_published,
        creator=data.creator,
        publish_time=data.publish_time,
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