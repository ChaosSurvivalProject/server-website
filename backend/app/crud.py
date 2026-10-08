"""CRUD operations for messages."""
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_, insert

from .database import Message, UserMessage, User
from .schemas import MessageCreate, MessageUpdate

# 统一时区：消息时间按北京时间存储（naive ISO 字符串，见 AGENTS.md 存储约定）。
_TZ = ZoneInfo("Asia/Shanghai")


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


# ── Message CRUD ────────────────────────────────────────────────────
async def create_message(db: AsyncSession, data: MessageCreate) -> Message:
    now = _now_iso()
    obj = Message(
        type=data.type,
        category=data.category,
        title=data.title,
        content=data.content,
        related_article_id=data.related_article_id,
        related_comment_id=data.related_comment_id,
        related_user_id=data.related_user_id,
        from_user_id=data.from_user_id,
        reply_content=data.reply_content,
        replied_comment_content=data.replied_comment_content,
        is_broadcast=data.is_broadcast,
        is_deleted=0,
        status=data.status if data.is_broadcast else 1,
        created_at=now,
        updated_at=now,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_message(db: AsyncSession, message_id: int) -> Message | None:
    result = await db.execute(select(Message).where(Message.id == message_id))
    return result.scalar_one_or_none()


async def update_message(
    db: AsyncSession, message_id: int, data: MessageUpdate
) -> Message | None:
    obj = await get_message(db, message_id)
    if obj is None:
        return None
    update_data = data.model_dump(exclude_unset=True, by_alias=False)
    for key, value in update_data.items():
        setattr(obj, key, value)
    obj.updated_at = _now_iso()
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_messages_page(
    db: AsyncSession,
    user_id: int,
    msg_type: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """分页查询用户消息列表（含已读/删除状态）。

    - 过滤掉 messages.is_deleted=1 的消息
    - 过滤掉当前用户 user_messages.is_deleted=1 的记录
    - msg_type='reply' 只返回 reply 类型；msg_type='system' 返回广播 + 审核通知
    """
    page = max(page, 1)
    page_size = max(page_size, 1)
    offset = (page - 1) * page_size

    # 构建类型过滤条件
    type_filter = None
    if msg_type == "reply":
        type_filter = Message.type == "reply"
    elif msg_type == "system":
        type_filter = or_(
            Message.is_broadcast == 1,
            Message.type.in_(["article_review", "beta_review"]),
        )
    elif msg_type == "like":
        type_filter = Message.type == "like"

    stmt = (
        select(Message, UserMessage)
        .join(UserMessage, UserMessage.message_id == Message.id)
        .where(
            UserMessage.user_id == user_id,
            Message.is_deleted == 0,
            UserMessage.is_deleted == 0,
        )
    )
    count_stmt = select(func.count()).select_from(Message).join(
        UserMessage, UserMessage.message_id == Message.id
    ).where(
        UserMessage.user_id == user_id,
        Message.is_deleted == 0,
        UserMessage.is_deleted == 0,
    )

    if type_filter is not None:
        stmt = stmt.where(type_filter)
        count_stmt = count_stmt.where(type_filter)

    stmt = stmt.order_by(Message.created_at.desc()).offset(offset).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for msg, um in rows:
        items.append(
            {
                "id": msg.id,
                "type": msg.type,
                "category": msg.category,
                "title": msg.title,
                "content": msg.content,
                "relatedArticleId": msg.related_article_id,
                "relatedCommentId": msg.related_comment_id,
                "relatedUserId": msg.related_user_id,
                "fromUserId": msg.from_user_id,
                "replyContent": msg.reply_content,
                "repliedCommentContent": msg.replied_comment_content,
                "isBroadcast": msg.is_broadcast,
                "isDeleted": msg.is_deleted,
                "status": msg.status,
                "createdAt": msg.created_at,
                "updatedAt": msg.updated_at,
                "isRead": um.is_read,
                "isUserDeleted": um.is_deleted,
            }
        )

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


async def get_system_messages_page(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """系统通知列表（广播消息 + 定向审核通知）。

    广播消息：用户点击后才插入 user_messages，此处 LEFT JOIN 确保未点击的也能列出。
    """
    page = max(page, 1)
    page_size = max(page_size, 1)
    offset = (page - 1) * page_size

    # 广播消息：所有已发布且未删除的（只连接未删除的 user_messages）
    broadcast_rows = (
        await db.execute(
            select(Message, UserMessage)
            .outerjoin(
                UserMessage,
                and_(
                    UserMessage.message_id == Message.id,
                    UserMessage.user_id == user_id,
                    UserMessage.is_deleted == 0,
                ),
            )
            .where(
                Message.is_broadcast == 1,
                Message.is_deleted == 0,
                Message.status == 1,
            )
            .order_by(Message.created_at.desc())
        )
    ).all()

    # 定向审核通知：该用户有 user_messages 记录且未删除
    directed_rows = (
        await db.execute(
            select(Message, UserMessage)
            .join(UserMessage, UserMessage.message_id == Message.id)
            .where(
                Message.type.in_(["article_review", "beta_review"]),
                Message.is_deleted == 0,
                UserMessage.user_id == user_id,
                UserMessage.is_deleted == 0,
            )
            .order_by(Message.created_at.desc())
        )
    ).all()

    # 合并并去重（广播与定向不会重复），然后按创建时间倒序
    seen = set()
    raw_items = []
    for msg, um in broadcast_rows + directed_rows:
        if msg.id in seen:
            continue
        seen.add(msg.id)
        raw_items.append((msg, um))

    raw_items.sort(key=lambda x: x[0].created_at, reverse=True)

    total = len(raw_items)
    page_items = raw_items[offset : offset + page_size]

    items = []
    for msg, um in page_items:
        items.append(
            {
                "id": msg.id,
                "type": msg.type,
                "category": msg.category,
                "title": msg.title,
                "content": msg.content,
                "relatedArticleId": msg.related_article_id,
                "relatedCommentId": msg.related_comment_id,
                "relatedUserId": msg.related_user_id,
                "fromUserId": msg.from_user_id,
                "replyContent": msg.reply_content,
                "repliedCommentContent": msg.replied_comment_content,
                "isBroadcast": msg.is_broadcast,
                "isDeleted": msg.is_deleted,
                "status": msg.status,
                "createdAt": msg.created_at,
                "updatedAt": msg.updated_at,
                "isRead": um.is_read if um is not None else 0,
                "isUserDeleted": um.is_deleted if um is not None else 0,
            }
        )

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


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    """未读计数：定向未读 + 广播未点击。

    定向消息：user_messages.is_read=0 且 is_deleted=0
    广播消息：不存在 user_messages 记录 或 is_read=0 且 is_deleted=0
    """
    # 定向未读（不含广播消息，避免与下方广播统计重复）
    directed = await db.execute(
        select(func.count())
        .select_from(UserMessage)
        .join(Message, UserMessage.message_id == Message.id)
        .where(
            UserMessage.user_id == user_id,
            UserMessage.is_read == 0,
            UserMessage.is_deleted == 0,
            Message.is_broadcast == 0,
        )
    )
    directed_count = directed.scalar_one()

    # 广播未点击：messages 中 is_broadcast=1 且未删除，但该用户没有 user_messages 记录
    # 或记录存在但 is_read=0
    broadcast_with_um = (
        select(func.count())
        .select_from(Message)
        .join(UserMessage, UserMessage.message_id == Message.id)
        .where(
            Message.is_broadcast == 1,
            Message.is_deleted == 0,
            Message.status == 1,
            UserMessage.user_id == user_id,
            UserMessage.is_deleted == 0,
            UserMessage.is_read == 0,
        )
    )
    broadcast_count = (await db.execute(broadcast_with_um)).scalar_one()

    # 广播消息中用户完全没有点击过的（没有 user_messages 记录）
    # 通过 left join 找 messages 中广播消息但该用户无 user_messages 的
    broadcast_no_um = (
        select(func.count())
        .select_from(Message)
        .outerjoin(
            UserMessage,
            and_(
                UserMessage.message_id == Message.id,
                UserMessage.user_id == user_id,
            ),
        )
        .where(
            Message.is_broadcast == 1,
            Message.is_deleted == 0,
            Message.status == 1,
            UserMessage.id.is_(None),
        )
    )
    broadcast_no_um_count = (await db.execute(broadcast_no_um)).scalar_one()

    # 去重：同一条广播消息若既被 join 计入、又被 left join 计入，会重复统计
    broadcast_count = max(0, broadcast_count - broadcast_no_um_count)
    
    return directed_count + broadcast_count + broadcast_no_um_count


async def mark_message_read(db: AsyncSession, user_id: int, message_id: int) -> bool:
    """标记单条消息为已读（广播消息：不存在则插入并标记已读）。"""
    # 检查消息是否存在且未被删除
    msg = await get_message(db, message_id)
    if msg is None or msg.is_deleted == 1:
        return False

    # 查找或创建 user_messages 记录
    um = (
        await db.execute(
            select(UserMessage).where(
                UserMessage.user_id == user_id,
                UserMessage.message_id == message_id,
            )
        )
    ).scalar_one_or_none()

    if um is None:
        now = _now_iso()
        um = UserMessage(
            user_id=user_id,
            message_id=message_id,
            is_read=1,
            is_deleted=0,
            created_at=now,
            updated_at=now,
        )
        db.add(um)
    else:
        um.is_read = 1
        um.updated_at = _now_iso()

    await db.commit()
    return True


async def mark_all_read(db: AsyncSession, user_id: int, msg_type: str | None = None) -> int:
    """批量标记已读。

    - msg_type='reply'：只标记 reply 定向消息
    - msg_type='system'：标记 article_review / beta_review 定向审核通知 + 广播消息
    - msg_type=None（默认）：标记所有定向消息（不含广播消息；广播消息点击后才写入 user_messages）
    """
    stmt = select(UserMessage).where(
        UserMessage.user_id == user_id,
        UserMessage.is_read == 0,
        UserMessage.is_deleted == 0,
    )
    
    if msg_type == "reply":
        stmt = stmt.join(Message, Message.id == UserMessage.message_id).where(Message.type == "reply")
    elif msg_type == "system":
        stmt = stmt.join(Message, Message.id == UserMessage.message_id).where(
            or_(
                Message.is_broadcast == 1,
                Message.type.in_(["article_review", "beta_review"]),
            )
        )
    else:
        stmt = stmt.join(Message, Message.id == UserMessage.message_id).where(Message.is_broadcast == 0)

    rows = (await db.execute(stmt)).scalars().all()
    now = _now_iso()
    for um in rows:
        um.is_read = 1
        um.updated_at = now

    count = len(rows)

    if msg_type == "system":
        broadcast_no_um = (
            select(Message.id)
            .where(
                Message.is_broadcast == 1,
                Message.is_deleted == 0,
                Message.status == 1,
                ~Message.id.in_(select(UserMessage.message_id).where(UserMessage.user_id == user_id)),
            )
        )
        missing_ids = (await db.execute(broadcast_no_um)).scalars().all()
        if missing_ids:
            db.add_all(
                [
                    UserMessage(
                        user_id=user_id,
                        message_id=msg_id,
                        is_read=1,
                        is_deleted=0,
                        created_at=now,
                        updated_at=now,
                    )
                    for msg_id in missing_ids
                ]
            )
            count += len(missing_ids)

    if count:
        await db.commit()
    return count


async def delete_user_message(db: AsyncSession, user_id: int, message_id: int) -> bool:
    """软删除定向消息（同时标记 messages.is_deleted=1 与 user_messages.is_deleted=1）。"""
    msg = await get_message(db, message_id)
    if msg is None or msg.is_deleted == 1:
        return False
    if msg.is_broadcast == 1:
        return False  # 广播消息前台不可删除

    msg.is_deleted = 1
    msg.updated_at = _now_iso()

    um = (
        await db.execute(
            select(UserMessage).where(
                UserMessage.user_id == user_id,
                UserMessage.message_id == message_id,
            )
        )
    ).scalar_one_or_none()
    if um is not None:
        um.is_deleted = 1
        um.updated_at = _now_iso()

    await db.commit()
    return True


# ── 管理员 Message CRUD ────────────────────────────────────────────
async def admin_get_message(db: AsyncSession, message_id: int) -> Message | None:
    return await get_message(db, message_id)


async def admin_create_message(db: AsyncSession, data: MessageCreate) -> Message:
    # 广播消息：根据 category 自动设置 type；固定为已发布
    if data.is_broadcast:
        data.status = 1
        if data.category == "activity":
            data.type = "activity_announcement"
        else:
            data.type = "system_announcement"
            data.category = data.category or "system"
    return await create_message(db, data)


async def admin_update_message(
    db: AsyncSession, message_id: int, data: MessageUpdate
) -> Message | None:
    # 广播消息编辑不修改发布时间（created_at 不变）
    obj = await update_message(db, message_id, data)
    if obj is None:
        return None

    # 编辑后重新标记未读：广播消息影响全部用户，定向消息只影响相关用户
    if obj.is_broadcast == 1:
        await db.execute(
            update(UserMessage)
            .where(UserMessage.message_id == message_id)
            .values(is_read=0, is_deleted=0, updated_at=_now_iso())
        )
    else:
        if obj.related_user_id is not None:
            await db.execute(
                update(UserMessage)
                .where(
                    UserMessage.message_id == message_id,
                    UserMessage.user_id == obj.related_user_id,
                )
                .values(is_read=0, is_deleted=0, updated_at=_now_iso())
            )
    await db.commit()
    return obj


async def admin_delete_message(db: AsyncSession, message_id: int) -> bool:
    msg = await get_message(db, message_id)
    if msg is None:
        return False
    msg.is_deleted = 1
    msg.updated_at = _now_iso()
    await db.commit()
    return True


async def admin_messages_page(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    msg_type: str | None = None,
    status: int | None = None,
) -> dict:
    """管理员：站内信管理分页（含草稿）。"""
    page = max(page, 1)
    page_size = max(page_size, 1)
    offset = (page - 1) * page_size

    stmt = select(Message)
    count_stmt = select(func.count()).select_from(Message)

    conditions = []
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(or_(Message.title.like(like), Message.content.like(like)))
    if msg_type:
        conditions.append(Message.type == msg_type)
    if status is not None:
        conditions.append(Message.status == status)

    if conditions:
        cond = and_(*conditions)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    stmt = stmt.order_by(Message.id.desc()).offset(offset).limit(page_size)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt)).scalars().all()

    items = []
    for msg in rows:
        items.append(
            {
                "id": msg.id,
                "type": msg.type,
                "category": msg.category,
                "title": msg.title,
                "content": msg.content,
                "relatedArticleId": msg.related_article_id,
                "relatedCommentId": msg.related_comment_id,
                "relatedUserId": msg.related_user_id,
                "fromUserId": msg.from_user_id,
                "replyContent": msg.reply_content,
                "repliedCommentContent": msg.replied_comment_content,
                "isBroadcast": msg.is_broadcast,
                "isDeleted": msg.is_deleted,
                "status": msg.status,
                "createdAt": msg.created_at,
                "updatedAt": msg.updated_at,
            }
        )

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

    await db.refresh(task)
    return task
