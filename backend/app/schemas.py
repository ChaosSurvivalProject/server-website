"""Pydantic schemas for announcement API.

Field aliases use camelCase to match the Vue frontend expectations
(publishTime / isPublished / readCount / createTime / updateTime).
"""
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class AnnouncementBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., max_length=255, description="公告标题")
    content: str = Field(..., description="公告内容（HTML/Markdown）")
    is_published: int = Field(default=0, alias="isPublished", description="0=草稿, 1=已发布")
    creator: str = Field(..., max_length=100, description="发布人")
    publish_time: str = Field(..., alias="publishTime", description="发布时间，ISO 格式字符串")


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
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


class CommonResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None