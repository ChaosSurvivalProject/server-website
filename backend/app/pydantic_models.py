"""资源中心模块的 Pydantic 请求模型（camelCase 别名，契约参照 app/schemas.py）。

独立成文件而非塞进 schemas.py 的原因：schemas.py 目前只承载站内信模型，
资源中心的模型数量多（7 个），单独一文件便于整模块对照 PRD 评审；
数据库列见 app/database.py（ResourceCenter 五表）。
"""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResourceCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slug: str = Field(..., max_length=64, description="URL 标识，全局唯一")
    name: str = Field(..., max_length=100)
    resource_type: str = Field("mod", alias="resourceType", max_length=32)
    summary: str = Field("", max_length=255)
    description_md: str = Field("", alias="descriptionMd")
    icon_url: str = Field("", alias="iconUrl", max_length=512)
    cover_url: str = Field("", alias="coverUrl", max_length=512)
    side: str = Field("both", max_length=16)
    status: str = Field("draft", max_length=16)
    featured: bool = Field(False)
    sort_weight: int = Field(0, alias="sortWeight")
    github_repo_url: str = Field("", alias="githubRepoUrl", max_length=512)
    issues_url: str = Field("", alias="issuesUrl", max_length=512)
    docs_url: str = Field("", alias="docsUrl", max_length=512)
    platforms: List[str] = Field(default_factory=list)
    game_versions: List[str] = Field(default_factory=list, alias="gameVersions")
    tags: List[str] = Field(default_factory=list)


class ResourceUpdateRequest(BaseModel):
    """部分更新：None = 不改；platforms/game_versions/tags 传数组即全量重写，不传即不动。"""

    model_config = ConfigDict(populate_by_name=True)

    slug: Optional[str] = Field(None, max_length=64)
    name: Optional[str] = Field(None, max_length=100)
    resource_type: Optional[str] = Field(None, alias="resourceType", max_length=32)
    summary: Optional[str] = Field(None, max_length=255)
    description_md: Optional[str] = Field(None, alias="descriptionMd")
    icon_url: Optional[str] = Field(None, alias="iconUrl", max_length=512)
    cover_url: Optional[str] = Field(None, alias="coverUrl", max_length=512)
    side: Optional[str] = Field(None, max_length=16)
    featured: Optional[bool] = None
    sort_weight: Optional[int] = Field(None, alias="sortWeight")
    github_repo_url: Optional[str] = Field(None, alias="githubRepoUrl", max_length=512)
    issues_url: Optional[str] = Field(None, alias="issuesUrl", max_length=512)
    docs_url: Optional[str] = Field(None, alias="docsUrl", max_length=512)
    platforms: Optional[List[str]] = None
    game_versions: Optional[List[str]] = Field(None, alias="gameVersions")
    tags: Optional[List[str]] = None


class ResourceStatusRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(..., max_length=16, description="draft | published | hidden | archived")


class VersionCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version: str = Field(..., max_length=64)
    release_tag: str = Field("", alias="releaseTag", max_length=128)
    channel: str = Field("stable", max_length=16)
    published_at: str = Field("", alias="publishedAt", max_length=30)
    game_versions: List[str] = Field(default_factory=list, alias="gameVersions")
    platforms: List[str] = Field(default_factory=list)
    side: str = Field("both", max_length=16)
    changelog_md: str = Field("", alias="changelogMd")
    status: Optional[str] = Field("visible", max_length=16)
    is_latest_stable: bool = Field(False, alias="isLatestStable")


class VersionUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version: Optional[str] = Field(None, max_length=64)
    release_tag: Optional[str] = Field(None, alias="releaseTag", max_length=128)
    channel: Optional[str] = Field(None, max_length=16)
    published_at: Optional[str] = Field(None, alias="publishedAt", max_length=30)
    game_versions: Optional[List[str]] = Field(None, alias="gameVersions")
    platforms: Optional[List[str]] = None
    side: Optional[str] = Field(None, max_length=16)
    changelog_md: Optional[str] = Field(None, alias="changelogMd")
    status: Optional[str] = Field(None, max_length=16)
    is_latest_stable: Optional[bool] = Field(None, alias="isLatestStable")


class AssetCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(..., max_length=255)
    url: str = Field(..., max_length=1024, description="https://github.com/ 开头的 Release 资产链接")
    purpose: str = Field("main", max_length=16)
    sort: int = Field(0)
    is_primary: bool = Field(False, alias="isPrimary")
    status: Optional[str] = Field("visible", max_length=16)


class AssetUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filename: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=1024)
    purpose: Optional[str] = Field(None, max_length=16)
    sort: Optional[int] = None
    is_primary: Optional[bool] = Field(None, alias="isPrimary")
    status: Optional[str] = Field(None, max_length=16)


class DictCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(..., max_length=32, description="resource_type | platform | game_version | side | release_channel | tag")
    key: str = Field(..., max_length=64, description="小写字母/数字/连字符；筛选 URL 参数值，创建后不可改")
    label: str = Field(..., max_length=64)
    sort: int = Field(0)
    enabled: Optional[bool] = Field(True)


class DictUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    label: Optional[str] = Field(None, max_length=64)
    sort: Optional[int] = None
    enabled: Optional[bool] = None
