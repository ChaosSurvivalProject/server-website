"""站内信模块：/api/messages/* 与 /api/messages/admin/*。

实施依据：docs/站内信/站内信功能PRD.md v1.0。

接口一览：
  ── 登录用户 ──
  GET    /messages/unread-count        未读计数
  GET    /messages/replies             回复我的列表
  GET    /messages/likes               收到点赞列表（本次空数组占位）
  GET    /messages/system              系统通知列表（广播 + 审核通知）
  POST   /messages/{id}/read           标记单条已读
  POST   /messages/read-all            批量标记已读
  DELETE /messages/{id}                删除定向消息（软删）

  ── 管理员 ──
  GET    /messages/admin/page          站内信管理分页（含草稿）
  POST   /messages/admin/create        创建站内信
  PUT    /messages/admin/update/{id}   编辑站内信
  DELETE /messages/admin/delete/{id}   删除站内信（软删）
"""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import get_current_user, require_admin
from .crud import (
    _now_iso,
    get_message,
    get_messages_page,
    get_system_messages_page,
    get_unread_count,
    mark_message_read,
    mark_all_read,
    delete_user_message,
    admin_get_message,
    admin_create_message,
    admin_update_message,
    admin_delete_message,
    admin_messages_page,
)
from .database import (
    Message,
    UserMessage,
    get_db,
)
from .schemas import (
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    PageResponse,
    UnreadCountResponse,
    CommonResponse,
)
from .forum import (
    STATUS_PUBLISHED,
    COMMENT_NORMAL,
    _get_article,
    _can_view_article,
    _get_users,
    _author_brief,
    _comment_node,
    _now_iso as _forum_now_iso,
    _TZ as _TZ,
)
from .forum import ForumComment, ForumArticle, User

router = APIRouter(prefix="/messages", tags=["messages"])


# ── 常量 ──────────────────────────────────────────────────────────
_TYPE_REPLY = "reply"
_TYPE_SYSTEM_ANNOUNCEMENT = "system_announcement"
_TYPE_ACTIVITY_ANNOUNCEMENT = "activity_announcement"
_TYPE_ARTICLE_REVIEW = "article_review"
_TYPE_BETA_REVIEW = "beta_review"

_CATEGORY_SYSTEM = "system"
_CATEGORY_ACTIVITY = "activity"
_CATEGORY_ARTICLE_REVIEW = "article_review"
_CATEGORY_BETA_REVIEW = "beta_review"


# ── 辅助函数 ──────────────────────────────────────────────────────
def _ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


async def _get_user_message(db: AsyncSession, user_id: int, message_id: int) -> UserMessage | None:
    result = await db.execute(
        select(UserMessage).where(
            UserMessage.user_id == user_id,
            UserMessage.message_id == message_id,
        )
    )
    return result.scalar_one_or_none()


async def _ensure_user_message(db: AsyncSession, user_id: int, message_id: int, is_read: int = 0) -> UserMessage:
    """确保 user_messages 记录存在，不存在则创建。"""
    um = await _get_user_message(db, user_id, message_id)
    if um is None:
        now = _now_iso()
        um = UserMessage(
            user_id=user_id,
            message_id=message_id,
            is_read=is_read,
            is_deleted=0,
            created_at=now,
            updated_at=now,
        )
        db.add(um)
        await db.flush()
    return um


# ── 前台接口 ──────────────────────────────────────────────────────
@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """未读计数（含定向未读 + 广播未点击）。"""
    count = await get_unread_count(db, user.id)
    return _ok({"count": count})


@router.get("/replies")
async def list_replies(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """回复我的列表。"""
    result = await get_messages_page(db, user.id, msg_type="reply", page=page, page_size=pageSize)
    return _ok(result)


@router.get("/likes")
async def list_likes(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """收到点赞列表（本次功能占位，返回空数组）。"""
    result = await get_messages_page(db, user.id, msg_type="like", page=page, page_size=pageSize)
    return _ok(result)


@router.get("/system")
async def list_system(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """系统通知列表（广播消息 + 定向审核通知）。

    进入列表时，对尚未产生 user_messages 记录的广播消息批量插入（is_read=0）。
    """
    # 批量插入未点击的广播消息 user_messages 记录
    broadcast_msgs = (
        await db.execute(
            select(Message.id).where(
                Message.is_broadcast == 1,
                Message.is_deleted == 0,
                Message.status == 1,
            )
        )
    ).scalars().all()
    for msg_id in broadcast_msgs:
        await _ensure_user_message(db, user.id, msg_id, is_read=0)
    await db.commit()

    result = await get_system_messages_page(db, user.id, page=page, page_size=pageSize)
    return _ok(result)


@router.post("/{message_id}/read")
async def mark_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记单条已读（广播消息：不存在 user_messages 则插入并标记已读）。"""
    ok = await mark_message_read(db, user.id, message_id)
    if not ok:
        raise HTTPException(status_code=404, detail="消息不存在")
    return _ok()


@router.post("/read-all")
async def mark_all_read_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    msg_type: Optional[str] = Query(None),
):
    """批量标记已读（定向消息 + 可选系统/审核通知）。"""
    count = await mark_all_read(db, user.id, msg_type)
    return _ok({"count": count})


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除定向消息（软删：同时标记 messages.is_deleted=1 与 user_messages.is_deleted=1）。"""
    ok = await delete_user_message(db, user.id, message_id)
    if not ok:
        raise HTTPException(status_code=400, detail="无法删除该消息")
    return _ok()


# ── 管理员接口 ─────────────────────────────────────────────────────
admin_router = APIRouter(prefix="/messages/admin", tags=["messages-admin"])


@admin_router.get("/detail/{message_id}")
async def admin_detail(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """站内信详情。"""
    obj = await admin_get_message(db, message_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="消息不存在")
    return _ok({
        "id": obj.id,
        "type": obj.type,
        "category": obj.category,
        "title": obj.title,
        "content": obj.content,
        "relatedArticleId": obj.related_article_id,
        "relatedCommentId": obj.related_comment_id,
        "relatedUserId": obj.related_user_id,
        "fromUserId": obj.from_user_id,
        "replyContent": obj.reply_content,
        "repliedCommentContent": obj.replied_comment_content,
        "isBroadcast": obj.is_broadcast,
        "isDeleted": obj.is_deleted,
        "status": obj.status,
        "createdAt": obj.created_at,
        "updatedAt": obj.updated_at,
    })


@admin_router.get("/page")
async def admin_page(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keyword: Optional[str] = Query(default=None, description="标题/正文关键词"),
    type: Optional[str | list[str]] = Query(default=None, description="消息类型，可多选"),
    status: Optional[int] = Query(default=None, description="0=草稿, 1=已发布"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """站内信管理分页（含草稿）。"""
    result = await admin_messages_page(
        db, page=page, page_size=pageSize, keyword=keyword, msg_type=type, status=status
    )
    return _ok(result)


@admin_router.post("/create")
async def admin_create(
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """创建站内信。"""
    obj = await admin_create_message(db, data)
    return _ok({
        "id": obj.id,
        "type": obj.type,
        "category": obj.category,
        "title": obj.title,
        "content": obj.content,
        "relatedArticleId": obj.related_article_id,
        "relatedCommentId": obj.related_comment_id,
        "relatedUserId": obj.related_user_id,
        "fromUserId": obj.from_user_id,
        "replyContent": obj.reply_content,
        "repliedCommentContent": obj.replied_comment_content,
        "isBroadcast": obj.is_broadcast,
        "isDeleted": obj.is_deleted,
        "status": obj.status,
        "createdAt": obj.created_at,
        "updatedAt": obj.updated_at,
    })


@admin_router.put("/update/{message_id}")
async def admin_update(
    message_id: int,
    data: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """编辑站内信。"""
    obj = await admin_update_message(db, message_id, data)
    if obj is None:
        raise HTTPException(status_code=404, detail="消息不存在")
    return _ok({
        "id": obj.id,
        "type": obj.type,
        "category": obj.category,
        "title": obj.title,
        "content": obj.content,
        "relatedArticleId": obj.related_article_id,
        "relatedCommentId": obj.related_comment_id,
        "relatedUserId": obj.related_user_id,
        "fromUserId": obj.from_user_id,
        "replyContent": obj.reply_content,
        "repliedCommentContent": obj.replied_comment_content,
        "isBroadcast": obj.is_broadcast,
        "isDeleted": obj.is_deleted,
        "status": obj.status,
        "createdAt": obj.created_at,
        "updatedAt": obj.updated_at,
    })


@admin_router.delete("/delete/{message_id}")
async def admin_delete(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """删除站内信（软删 messages.is_deleted=1）。"""
    ok = await admin_delete_message(db, message_id)
    if not ok:
        raise HTTPException(status_code=404, detail="消息不存在")
    return _ok()


# ── 消息创建辅助（供 forum / faction_beta 调用） ─────────────────
async def create_reply_message(
    db: AsyncSession,
    *,
    article_id: int,
    comment_id: int,
    reply_user_id: int,
    target_user_id: int,
    reply_content: str,
    replied_comment_content: str,
) -> Message | None:
    """创建回复通知（定向消息）。"""
    article = await _get_article(db, article_id)
    if article is None:
        return None

    # 获取用户信息
    users = await _get_users(db, {reply_user_id, target_user_id})
    from_user = users.get(reply_user_id)
    target_user = users.get(target_user_id)

    if target_user is None:
        return None

    now = _now_iso()
    title = f"{from_user.nickname or from_user.username} 回复了你的评论"
    content = f"回复 {target_user.nickname or target_user.username}：{reply_content}"

    msg = Message(
        type=_TYPE_REPLY,
        category=None,
        title=title,
        content=content,
        related_article_id=article_id,
        related_comment_id=comment_id,
        related_user_id=target_user_id,
        from_user_id=reply_user_id,
        reply_content=reply_content,
        replied_comment_content=replied_comment_content,
        is_broadcast=0,
        is_deleted=0,
        status=1,
        created_at=now,
        updated_at=now,
    )
    db.add(msg)
    await db.flush()

    # 定向消息：立即插入 user_messages
    um = UserMessage(
        user_id=target_user_id,
        message_id=msg.id,
        is_read=0,
        is_deleted=0,
        created_at=now,
        updated_at=now,
    )
    db.add(um)
    await db.commit()
    await db.refresh(msg)
    return msg


async def create_article_comment_message(
    db: AsyncSession,
    *,
    article_id: int,
    comment_id: int,
    commenter_id: int,
    article_author_id: int,
    comment_content: str,
) -> Message | None:
    """创建文章评论通知（定向消息，用于顶层评论通知文章作者）。"""
    article = await _get_article(db, article_id)
    if article is None:
        return None

    users = await _get_users(db, {commenter_id, article_author_id})
    commenter = users.get(commenter_id)
    author = users.get(article_author_id)

    if author is None or commenter is None:
        return None

    now = _now_iso()
    title = f"{commenter.nickname or commenter.username} 评论了你的文章《{article.title}》"

    msg = Message(
        type=_TYPE_REPLY,
        category=None,
        title=title,
        content=comment_content,
        related_article_id=article_id,
        related_comment_id=comment_id,
        related_user_id=article_author_id,
        from_user_id=commenter_id,
        reply_content=comment_content,
        replied_comment_content="",
        is_broadcast=0,
        is_deleted=0,
        status=1,
        created_at=now,
        updated_at=now,
    )
    db.add(msg)
    await db.flush()

    um = UserMessage(
        user_id=article_author_id,
        message_id=msg.id,
        is_read=0,
        is_deleted=0,
        created_at=now,
        updated_at=now,
    )
    db.add(um)
    await db.commit()
    await db.refresh(msg)
    return msg


async def create_article_review_message(
    db: AsyncSession,
    *,
    article_id: int,
    author_id: int,
    status: int,
    review_note: str = "",
) -> Message | None:
    """创建文章审核通知（定向消息）。"""
    article = await _get_article(db, article_id)
    if article is None:
        return None

    users = await _get_users(db, {author_id})
    author = users.get(author_id)
    if author is None:
        return None

    status_text = "审核通过" if status == 1 else "审核驳回"
    title = f"你的文章《{article.title}》{status_text}"
    content = review_note or title

    now = _now_iso()
    msg = Message(
        type=_TYPE_ARTICLE_REVIEW,
        category=_CATEGORY_ARTICLE_REVIEW,
        title=title,
        content=content,
        related_article_id=article_id,
        related_user_id=author_id,
        is_broadcast=0,
        is_deleted=0,
        status=1,
        created_at=now,
        updated_at=now,
    )
    db.add(msg)
    await db.flush()

    um = UserMessage(
        user_id=author_id,
        message_id=msg.id,
        is_read=0,
        is_deleted=0,
        created_at=now,
        updated_at=now,
    )
    db.add(um)
    await db.commit()
    await db.refresh(msg)
    return msg


async def create_beta_review_message(
    db: AsyncSession,
    *,
    application_id: int,
    username: str,
    status: int,
    review_note: str = "",
) -> Message | None:
    """创建阵营内测审核通知（定向消息）。"""
    status_text = "审核通过" if status == 1 else "审核驳回"
    title = f"你的阵营内测申请{status_text}"
    content = review_note or title

    now = _now_iso()
    msg = Message(
        type=_TYPE_BETA_REVIEW,
        category=_CATEGORY_BETA_REVIEW,
        title=title,
        content=content,
        related_user_id=application_id,  # 关联申请 ID，前端可按需跳转
        is_broadcast=0,
        is_deleted=0,
        status=1,
        created_at=now,
        updated_at=now,
    )
    db.add(msg)
    await db.flush()

    # 查找对应用户（username 即 users.username）
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None:
        await db.commit()
        await db.refresh(msg)
        return msg

    um = UserMessage(
        user_id=user.id,
        message_id=msg.id,
        is_read=0,
        is_deleted=0,
        created_at=now,
        updated_at=now,
    )
    db.add(um)
    await db.commit()
    await db.refresh(msg)
    return msg


# ── 注册路由 ──────────────────────────────────────────────────────
def register_messages_routes(app):
    app.include_router(router)
    app.include_router(admin_router)
