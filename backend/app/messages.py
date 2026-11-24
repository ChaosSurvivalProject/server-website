"""站内信模块：/api/messages/* 与 /api/messages/admin/*。

实施依据：docs/站内信/站内信功能PRD.md v1.0。

接口一览：
  ── 登录用户 ──
  GET    /messages/unread-count        未读计数
  GET    /messages/stream              站内信实时推送（SSE，第二个包络例外）
  GET    /messages/replies             回复我的列表
  GET    /messages/likes               收到点赞列表
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
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import get_current_user, require_admin
from .auth.security import decode_token
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
    USER_STATUS_DELETED,
    USER_STATUS_DISABLED,
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

logger = logging.getLogger(__name__)


# ── 常量 ──────────────────────────────────────────────────────────
_TYPE_REPLY = "reply"
_TYPE_LIKE = "like"
_TYPE_SYSTEM_ANNOUNCEMENT = "system_announcement"
_TYPE_ACTIVITY_ANNOUNCEMENT = "activity_announcement"
_TYPE_ARTICLE_REVIEW = "article_review"
_TYPE_BETA_REVIEW = "beta_review"

_CATEGORY_SYSTEM = "system"
_CATEGORY_ACTIVITY = "activity"
_CATEGORY_ARTICLE_REVIEW = "article_review"
_CATEGORY_BETA_REVIEW = "beta_review"


# ── SSE 实时推送：连接注册表（可替换接口） ─────────────────────────
# 生产为单 worker 进程，进程内注册表足够。将来多 worker 前，把
# message_streams 换成基于 Redis pub/sub 的同接口实现即可，业务代码不用改
# （与 KB 限流共享存储是同一条遗留）。
_STREAM_MAX_CONNECTIONS = 5
_STREAM_HEARTBEAT_SECONDS = 25  # ≤30s 一次心跳注释行
_STREAM_QUEUE_MAXSIZE = 32


class MessageStreamRegistry(ABC):
    """站内信 SSE 连接注册表接口。

    实现只需提供 connect / disconnect / publish 三个操作；多 worker 场景替换为
    Redis pub/sub 实现即可，create_*_message 与 stream 路由都只依赖本接口。
    """

    @abstractmethod
    async def connect(self, user_id: int) -> asyncio.Queue:
        """登记一条新连接并返回其专属事件队列。"""

    @abstractmethod
    def disconnect(self, user_id: int, queue: asyncio.Queue) -> None:
        """移除连接（生成器 finally 中调用）。"""

    @abstractmethod
    async def publish(self, user_id: int, frame: dict) -> None:
        """向目标用户的全部活跃连接广播一帧。"""


class InMemoryMessageStreamRegistry(MessageStreamRegistry):
    """进程内实现：dict[user_id, deque[asyncio.Queue]]。"""

    def __init__(self, max_per_user: int = _STREAM_MAX_CONNECTIONS):
        self._max_per_user = max_per_user
        self._connections: dict[int, deque] = {}
        # 临界区内无 await，用 threading.Lock 避免跨事件循环隐患
        self._lock = Lock()

    async def connect(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=_STREAM_QUEUE_MAXSIZE)
        with self._lock:
            conns = self._connections.setdefault(user_id, deque())
            while len(conns) >= self._max_per_user:
                oldest = conns.popleft()
                # 哨兵 None：让最旧连接立即优雅收尾（前端收到 closed 后转轮询，
                # 避免 EventSource 自动重连引发「新连接踢旧连接」的抖动）
                try:
                    oldest.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            conns.append(queue)
        return queue

    def disconnect(self, user_id: int, queue: asyncio.Queue) -> None:
        with self._lock:
            conns = self._connections.get(user_id)
            if not conns:
                return
            try:
                conns.remove(queue)
            except ValueError:
                return
            if not conns:
                self._connections.pop(user_id, None)

    async def publish(self, user_id: int, frame: dict) -> None:
        with self._lock:
            conns = list(self._connections.get(user_id, ()))
        for queue in conns:
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                # 弱网/长时间不消费：丢最旧一帧腾位置，保证新事件不被积压淹没
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(frame)
                except asyncio.QueueFull:
                    pass


# 全局唯一注册表实例；多 worker 时替换为共享存储实现（见类注释）
message_streams: MessageStreamRegistry = InMemoryMessageStreamRegistry()


def _sse_frame(event: str, data: dict) -> str:
    """把一帧业务事件格式化为 SSE 文本（包络例外：不包 {code,message,data}）。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _notify_unread(db: AsyncSession, user_id: int, refresh: bool = True) -> None:
    """以服务端为准重算未读数，并向目标用户的全部活跃连接推送。

    所有 create_*_message 以及已读/删除操作写库成功后调用；客户端角标永远以
    这里的 count 覆盖，重连/弱网场景下不会重复计数。
    """
    try:
        count = await get_unread_count(db, user_id)
    except Exception:
        logger.exception("站内信 SSE 重算未读数失败（user_id=%s）", user_id)
        return
    try:
        await message_streams.publish(user_id, {"event": "unread", "data": {"count": count}})
        if refresh:
            # 提示客户端重拉当前打开的 Tab 列表（新消息/已读状态变化都会影响列表）
            await message_streams.publish(user_id, {"event": "refresh", "data": {}})
    except Exception:
        # 推送失败绝不影响写库主流程（与点赞通知同口径：通知失败 try/except 兜底）
        logger.exception("站内信 SSE 推送失败（user_id=%s）", user_id)


async def get_stream_user(
    request: Request,
    token: Optional[str] = Query(
        default=None,
        description="EventSource 无法自定义请求头，登录 token 经 query 参数传递",
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    """SSE 专用鉴权：优先读 ?token=，兼容 Authorization: Bearer 头。

    与 get_current_user 同口径：缺失/过期 token、用户不存在/已删除 → 401；
    被禁用用户 → 403。流前错误走标准 HTTP + detail，不进入 SSE 流。
    """
    raw = token
    if not raw:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            raw = auth_header[7:].strip()
    if not raw:
        raise HTTPException(status_code=401, detail="未登录或缺少认证信息")
    payload = decode_token(raw)
    if payload is None:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None or user.status == USER_STATUS_DELETED:
        raise HTTPException(status_code=401, detail="用户不存在或已被删除")
    if user.status == USER_STATUS_DISABLED:
        raise HTTPException(status_code=403, detail="该账号已被禁用，无法继续操作")
    return user


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


@router.get("/stream")
async def message_stream(
    request: Request,
    user: User = Depends(get_stream_user),
    db: AsyncSession = Depends(get_db),
):
    """站内信实时推送（SSE，第二个不走 {code,message,data} 包络的接口）。

    事件：
      unread  data:{count}   未读数（建连首帧必发；重连后以服务端 unread 为准）
      refresh data:{}        提示客户端重拉当前 Tab 列表
      closed  data:{reason}  控制帧：连接数超上限被挤掉，客户端应停 SSE 转轮询
    心跳：每 25s 一行 ": ping" 注释保活并探断连。
    鉴权失败在流前以标准 HTTP + detail 返回（401/403），不进入事件流。
    """
    # 建连即以服务端未读数打底：重连/弱网不错数，首帧覆盖客户端旧值
    initial_count = await get_unread_count(db, user.id)
    queue = await message_streams.connect(user.id)

    async def _generate():
        try:
            yield _sse_frame("unread", {"count": initial_count})
            while True:
                if await request.is_disconnected():
                    break
                try:
                    frame = await asyncio.wait_for(
                        queue.get(), timeout=_STREAM_HEARTBEAT_SECONDS
                    )
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                if frame is None:
                    # 被第 6 条连接挤掉：通知前端转轮询后结束，避免自动重连抖动
                    yield _sse_frame("closed", {"reason": "too_many_connections"})
                    break
                yield _sse_frame(frame["event"], frame["data"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("站内信 SSE 流异常（user_id=%s）", user.id)
        finally:
            message_streams.disconnect(user.id, queue)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # 只对 proxy_pass 直连生效；nginx 侧仍需 proxy_buffering off（两个都要）
            "X-Accel-Buffering": "no",
        },
    )


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
    """收到点赞列表（v1.1：文章/评论被点赞后定向通知作者）。"""
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
    # 多标签页一致：已读状态变化后同步刷新其他标签的角标与列表
    await _notify_unread(db, user.id)
    return _ok()


@router.post("/read-all")
async def mark_all_read_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    msg_type: Optional[str] = Query(None),
):
    """批量标记已读（定向消息 + 可选系统/审核通知）。"""
    count = await mark_all_read(db, user.id, msg_type)
    await _notify_unread(db, user.id)
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
    await _notify_unread(db, user.id)
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
    # 新消息实时触达：推送未读数 + 列表刷新给该用户全部活跃连接
    await _notify_unread(db, target_user_id)
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
    await _notify_unread(db, article_author_id)
    return msg


async def create_like_message(
    db: AsyncSession,
    *,
    article_id: int,
    comment_id: Optional[int],
    liker_id: int,
    author_id: int,
    comment_content: str = "",
    reply_to_nickname: str = "",
) -> Message | None:
    """创建点赞通知（定向消息，PRD v1.1 §7.3）。

    - 文章点赞（comment_id 为空）：标题「{点赞者} 点赞了我的文章」，内容为文章标题快照（带书名号《》）；
    - 评论点赞：标题「{点赞者} 点赞了我的评论」，内容为评论正文快照
      （回复类评论带「回复 @{被回复者昵称}：」前缀）；
    - **自己赞自己不通知**；点赞通知失败不影响点赞主流程（调用方 try/except 兜底）；
    - **同一点赞者对同一内容只保留一条未删除通知**：否则「赞 → 取消 → 再赞」的反复
      切换会给作者刷出多条重复通知（接收者删掉旧通知后，新的点赞仍会生成新通知）。
    """
    if liker_id == author_id:
        return None

    article = await _get_article(db, article_id)
    if article is None:
        return None

    # 去重：同一点赞者 + 同一文章 + 同一评论（文章点赞时 related_comment_id 为 NULL）
    dup_cond = [
        Message.type == _TYPE_LIKE,
        Message.from_user_id == liker_id,
        Message.related_article_id == article_id,
        Message.is_deleted == 0,
    ]
    if comment_id:
        dup_cond.append(Message.related_comment_id == comment_id)
    else:
        dup_cond.append(Message.related_comment_id.is_(None))
    existing = (await db.execute(select(Message.id).where(*dup_cond))).first()
    if existing is not None:
        return None

    users = await _get_users(db, {liker_id, author_id})
    liker = users.get(liker_id)
    author = users.get(author_id)
    if liker is None or author is None:
        return None

    liker_name = liker.nickname or liker.username

    if comment_id:
        title = f"{liker_name} 点赞了我的评论"
        content = comment_content
        if reply_to_nickname:
            content = f"回复 @{reply_to_nickname}：{comment_content}"
    else:
        title = f"{liker_name} 点赞了我的文章"
        content = f"《{article.title}》"

    now = _now_iso()
    msg = Message(
        type=_TYPE_LIKE,
        category=None,
        title=title,
        content=content,
        related_article_id=article_id,
        related_comment_id=comment_id,
        related_user_id=author_id,
        from_user_id=liker_id,
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
    await _notify_unread(db, author_id)
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
    await _notify_unread(db, author_id)
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
    await _notify_unread(db, user.id)
    return msg


# ── 注册路由 ──────────────────────────────────────────────────────
def register_messages_routes(app):
    app.include_router(router)
    app.include_router(admin_router)
