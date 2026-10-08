"""Pydantic schemas for messages API.

Field aliases use camelCase to match the Vue frontend expectations.
消息正文对外字段为 rawContent（原始内容）+ contentType（内容格式）：
- contentType='markdown'：Markdown 源码，渲染由前端完成（marked + DOMPurify）
"""
from datetime import datetime
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# ── 站内信 ──────────────────────────────────────────────────────────
class MessageBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Optional[str] = Field(None, description="消息类型：reply / system_announcement / activity_announcement / article_review / beta_review")
    category: Optional[str] = Field(None, description="系统通知分类：system / activity / article_review / beta_review")
    title: str = Field(..., max_length=255, description="标题")
    content: Optional[str] = Field(None, alias="rawContent", description="Markdown 正文（可选）")
    related_article_id: Optional[int] = Field(None, alias="relatedArticleId")
    related_comment_id: Optional[int] = Field(None, alias="relatedCommentId")
    related_user_id: Optional[int] = Field(None, alias="relatedUserId")
    from_user_id: Optional[int] = Field(None, alias="fromUserId")
    reply_content: Optional[str] = Field(None, alias="replyContent")
    replied_comment_content: Optional[str] = Field(None, alias="repliedCommentContent")
    is_broadcast: int = Field(default=0, alias="isBroadcast", description="0=定向, 1=广播")
    status: int = Field(default=1, alias="status", description="0=草稿, 1=已发布（仅广播消息有效）")


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, alias="rawContent")
    category: Optional[str] = Field(None)
    is_broadcast: Optional[int] = Field(None, alias="isBroadcast")
    status: Optional[int] = Field(None, alias="status")


class MessageResponse(MessageBase):
    id: int
    is_deleted: int = Field(default=0, alias="isDeleted")
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class MessageItem(MessageResponse):
    """列表项：额外携带已读/删除用户态字段。"""
    is_read: int = Field(default=0, alias="isRead")
    is_user_deleted: int = Field(default=0, alias="isUserDeleted")


class UserMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    user_id: int = Field(..., alias="userId")
    message_id: int = Field(..., alias="messageId")
    is_read: int = Field(..., alias="isRead")
    is_deleted: int = Field(..., alias="isDeleted")
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")


class UnreadCountResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    count: int = Field(..., alias="count")


class PageResponse(BaseModel):
    """分页响应结构。"""
    items: list[MessageItem]
    page: int
    pageSize: int
    totalPages: int
    total: int
    hasNext: bool
    hasPrev: bool


class CommonResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None
