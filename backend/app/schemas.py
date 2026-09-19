"""Pydantic schemas for announcement API.

Field aliases use camelCase to match the Vue frontend expectations
(publishTime / isPublished / readCount / createTime / updateTime).

公告正文对外字段为 rawContent（原始内容）+ contentType（内容格式）：
- contentType='html'：存量富文本 HTML（后端写入时 nh3 消毒）
- contentType='markdown'：Markdown 源码，渲染由前端完成（marked + DOMPurify）
"""
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AnnouncementBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., max_length=255, description="公告标题")
    content: str = Field(
        ...,
        alias="rawContent",
        description="公告原始内容：contentType=html 时为富文本 HTML，markdown 时为 Markdown 源码（渲染在前端）",
    )
    content_type: Literal["html", "markdown"] = Field(
        default="html", alias="contentType", description="内容格式：html=富文本, markdown=Markdown"
    )
    is_published: int = Field(default=0, alias="isPublished", description="0=草稿, 1=已发布")
    creator: str = Field(..., max_length=100, description="发布人")
    publish_time: str = Field(..., alias="publishTime", description="发布时间，ISO 格式字符串")


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, alias="rawContent")
    content_type: Optional[Literal["html", "markdown"]] = Field(None, alias="contentType")
    is_published: Optional[int] = Field(None, alias="isPublished")
    creator: Optional[str] = None
    publish_time: Optional[str] = Field(None, alias="publishTime")


class AnnouncementResponse(AnnouncementBase):
    id: int
    read_count: int = Field(default=0, alias="readCount")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PageResponse(BaseModel):
    """Paginated response matching frontend expectations."""
    items: list[AnnouncementResponse]
    page: int
    pageSize: int
    totalPages: int
    total: int
    hasNext: bool
    hasPrev: bool


class AddWatchCountRequest(BaseModel):
    announcementId: int = Field(..., description="公告ID")


class AnnouncementBrief(BaseModel):
    """公告简要信息（上一篇/下一篇导航等只需标题的场景，不返回正文）。"""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    title: str
    publish_time: str = Field(..., alias="publishTime")


class PrevNextResponse(BaseModel):
    """上一篇/下一篇导航（按 id 顺序，即列表页的新旧序，仅统计已发布公告）。

    prev=上一篇（比当前更早，id 更小）；next=下一篇（比当前更新，id 更大）；
    边界处无对应公告时为 null。
    """

    prev: Optional[AnnouncementBrief]
    next: Optional[AnnouncementBrief]


class CommonResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None