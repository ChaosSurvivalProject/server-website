"""社区（论坛）模块：/forum/*（对外经 main.py 统一挂 /api 前缀 → /api/forum/*）。

实施唯一依据：docs/论坛/论坛模块第一阶段PRD.md（v1.4）
+ docs/论坛/论坛删除与回收站PRD.md（v1.3，**局部取代**前者的 §8-D16「评论不提供作者自删」
与 §12.1「评论作者自删与编辑」中的自删半条——评论**编辑**仍不在范围内）。

接口一览（PRD §7 + 回收站 PRD §5，模块内不得手写 /api）：

  ── 公开（匿名可调）──
  GET    /forum/categories                 板块列表（过滤 is_hidden，含系统板块，带文章数）
  GET    /forum/tags/hot                   热门标签（is_hot 优先 + use_count 倒序）
  GET    /forum/stats                      社区统计 {articleCount, viewCount, tagCount}
  GET    /forum/config                     前台配置（Banner 三项 + defaultSort + searchPlaceholder）
  GET    /forum/articles                   文章列表（category/sort/q/tag/page）
  GET    /forum/articles/{id}              详情（未公开文章对非作者/管理员按 404 处理）
  GET    /forum/articles/{id}/comments     评论列表（只对顶层评论分页，每条内嵌 replies）
  GET    /forum/articles/{id}/author-posts 作者其他已发布文章（最多 5 条）
  POST   /forum/articles/{id}/view         浏览量 +1（原子自增，重复刷新重复计，已接受）

  ── 登录用户 ──
  POST   /forum/articles                   发布文章（status=0 待审核）
  GET    /forum/articles/{id}/edit         编辑回填（仅作者本人；越权/不存在一律 404）
  PUT    /forum/articles/{id}              作者编辑重提（仅作者本人；状态一律回到 0）
  GET    /forum/my/articles                我的文章（各状态 + reviewNote + recycleDays）
  GET    /forum/my/stats                   侧边栏用户卡 {postCount, likeCount, followerCount}
  DELETE /forum/articles/{id}              作者删除 → **进回收站**（status=4，非物理删）
  POST   /forum/articles/{id}/restore      作者从回收站恢复 → status_before_delete（超 30 天 410）
  DELETE /forum/articles/{id}/purge        回收站内彻底删除（物理 + 级联，不可恢复）
  DELETE /forum/comments/{id}              作者删自己的评论/回复（**物理删除不留痕**，顶层连带回复）
  POST   /forum/articles/{id}/like         文章点赞切换（新增点赞→站内信通知作者，v1.1）
  POST   /forum/articles/{id}/favorite     文章收藏切换
  POST   /forum/articles/{id}/comments     发表评论 / 发表回复（两级楼中楼）
  POST   /forum/comments/{id}/like         评论点赞切换（新增点赞→站内信通知评论作者，v1.1）
  POST   /forum/upload/image               图片上传（登录用户；落盘 uploads/forum/YYYYMM/）

  ── 管理员（require_admin）──
  GET    /forum/admin/articles             检索分页（keyword/author/categoryId/tagId/status）
  PUT    /forum/admin/articles/{id}/review 审核（1=通过 / 2=驳回）
  POST   /forum/admin/articles/{id}/top|feature|offline|restore
  PUT    /forum/admin/articles/{id}        改板块/标签/封面/标题（**状态不变**）
  DELETE /forum/admin/articles/{id}        硬删除（级载评论/点赞/收藏/标签关联）
  GET    /forum/admin/articles/{id}/comments  评论列表（含已删除）
  DELETE /forum/admin/comments/{id}        删评论（**软删** status=2；顶层连带其回复）
  GET/POST/PUT/DELETE /forum/admin/categories|admin/tags|admin/config
  POST   /forum/admin/tags/{id}/merge      标签合并
  GET    /forum/admin/covers               封面图库（只读）
  GET    /forum/admin/user-stats/{userId}  用户论坛数据

所有接口遵循项目统一响应包络 {code, message, data}（code=0 成功）；
业务失败以 HTTPException(400/401/403/404/410, detail=...) 抛出。

四条最容易写错、且各只有一处的口径（改动前先读）：
1. **标签 use_count 只挂在"文章是否处于 status=1"这一个转移点上**（第一阶段 PRD §8-D8）——
   入口统一是 `_set_article_status()`，删除/恢复进回收站也走它，不要在别处直接改 article.status。
2. **评论 comment_count = 顶层评论数 + 回复数**；删顶层连带其回复减 `1 + 回复数`。
3. **作者删评论 = 物理删除不留痕**，后台删评论 = 软删留"已删除"标记——
   **有意不对称**，别顺手统一成一种（回收站 PRD §0.4-J / §6-D7）。
4. **作者删除帖子 = 进回收站（status=4），不是物理删、也不再产生 status=3**；
   回收站对**所有人** 404（含作者本人），彻底删除另有 /purge 接口。
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, delete, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import get_current_user, get_optional_user, require_admin
from .crud import _TZ
from .database import (
    ForumArticle,
    ForumArticleFavorite,
    ForumArticleLike,
    ForumArticleTag,
    ForumCategory,
    ForumComment,
    ForumCommentLike,
    ForumConfig,
    ForumTag,
    User,
    get_db,
)
# 回收站轻量核心（纯 SQLAlchemy，**forum_purge.py CLI 从 forum_core 直连、不 import 本模块**——
# 本模块顶部是完整 APIRouter + 全部 pydantic 模型，CLI 冷 import 实测 33s 起，见该模块头注释）。
# 这里 import 并 re-export，保证"作者彻底删除 / 管理员硬删 / 超期自动清理"三条路径语义唯一。
from .forum_core import (  # noqa: F401  （re-export 供 main.py / 冒烟测试 / CLI 旁路引用）
    RECYCLE_DAYS,
    cascade_delete_article,
    is_recycle_expired,
    purge_due,
    recycle_days_left,
)
from .uploads import UPLOAD_DIR, save_image

router = APIRouter(prefix="/forum", tags=["forum"])

# ── 常量（后端为唯一权威，前端选项需与此保持一致） ─────────────────
# 文章状态机（第一阶段 PRD §4.3 + 回收站 PRD §1.1）
STATUS_PENDING = 0    # 待审核
STATUS_PUBLISHED = 1  # 已发布
STATUS_REJECTED = 2   # 已驳回
STATUS_OFFLINE = 3    # 已下架（**仅管理员**这一个来源）
STATUS_RECYCLED = 4   # 回收站（作者删除后的保留态，30 天内可恢复）
ARTICLE_STATUS_TEXT = {
    STATUS_PENDING: "待审核",
    STATUS_PUBLISHED: "已发布",
    STATUS_REJECTED: "已驳回",
    STATUS_OFFLINE: "已下架",
    STATUS_RECYCLED: "回收站",
}

# 可被作者删除（进回收站）的状态；status=3 且 remove_by='admin' **不可删**——
# 否则作者能把管理员的下架记录搬进回收站、30 天后被自动清除，等于销毁治理证据。
DELETABLE_STATUSES = (STATUS_PENDING, STATUS_PUBLISHED, STATUS_REJECTED)
# 恢复的合法目标（只可能是删前状态，绝不重审）
RESTORE_TARGETS = (STATUS_PENDING, STATUS_PUBLISHED, STATUS_REJECTED)

# 评论状态
COMMENT_NORMAL = 1
COMMENT_DELETED = 2

# remove_by：谁把文章移出公开（决定作者能否编辑重提）
REMOVE_BY_AUTHOR = "author"
REMOVE_BY_ADMIN = "admin"

# 系统板块 code：首页=全部已发布聚合， 推荐=置顶∪加精聚合（PRD §0.3-D）
CODE_HOME = "home"
CODE_RECOMMEND = "recommend"

# 前台排序档（置顶帖在三档排序中都恒排最前）
SORT_LATEST = "latest"
SORT_VIEWS = "views"
SORT_COMMENTS = "comments"
SORT_OPTIONS = (SORT_LATEST, SORT_VIEWS, SORT_COMMENTS)

MAX_TAGS_PER_ARTICLE = 5
MAX_TAG_NAME_LEN = 20
TITLE_MIN, TITLE_MAX = 2, 100
CONTENT_MIN, CONTENT_MAX = 10, 50000
COMMENT_MIN, COMMENT_MAX = 1, 500
REVIEW_NOTE_MAX = 200
SUMMARY_LEN = 100

# 预置板块（PRD §0.4 首次启动种子数据，与首页标签栏一一对应）
SEED_CATEGORIES = [
    # (code, name, color, sort_order, is_system)
    (CODE_HOME, "首页", "#3b82f6", 0, 1),
    (CODE_RECOMMEND, "推荐", "#f59e0b", 1, 1),
    ("chat", "闲聊灌水", "#22c55e", 2, 0),
    ("guide", "攻略教程", "#6366f1", 3, 0),
    ("help", "求助问答", "#ef4444", 4, 0),
    ("resource", "资源分享", "#14b8a6", 5, 0),
    ("news", "新闻活动", "#ec4899", 6, 0),
    ("suggest", "功能建议", "#8b5cf6", 7, 0),
]

# 社区配置键：首次启动写入默认值（PRD §4.7）
FORUM_CONFIG_DEFAULTS = {
    "bannerTitle": "星穹旅驿站",
    "bannerSubtitle": "分享建筑、红石与开服心得，向大佬提问，一起把服务器玩出花。",
    "bannerImage": "",  # 空 → 前端渲染内置占位图，不外链第三方图床
    "defaultSort": SORT_LATEST,
    "searchPlaceholder": "搜索帖子…",
    # 打赏预留键（§0.3-E）：管理接口可读写，但第一阶段**不提供**任何 UI
    "rewardEnabled": "0",
    "rewardPresets": "1,5,10",
    "rewardCommission": "0",
}
# 前台配置接口只下发这五个（打赏键不出现在任何公开响应）
PUBLIC_CONFIG_KEYS = (
    "bannerTitle",
    "bannerSubtitle",
    "bannerImage",
    "defaultSort",
    "searchPlaceholder",
)

_CODE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~", re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_EMPHASIS_RE = re.compile(r"[*_~`>]+")


# ── 基础工具 ──────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _is_muted(user: User) -> bool:
    """禁言判定：now < mute_until 即禁言中（空值/格式异常一律按未禁言处理）。

    注意比较口径：mute_until 存的是**北京时间 naive** ISO 字符串，而
    `datetime.now(_TZ)` 带 tzinfo（ZoneInfo）——直接比较会抛
    "can't compare offset-naive and offset-aware datetimes"。这里统一取
    `.replace(tzinfo=None)` 的北京墙上时间再比，与入库口径一致。
    """
    until = _parse_iso(user.mute_until)
    if until is None:
        return False
    now_beijing_naive = datetime.now(_TZ).replace(tzinfo=None)
    return now_beijing_naive < until


def _ensure_not_muted(user: User) -> None:
    """写操作（发帖/评论/上传）统一禁言校验；读操作不受限（PRD §2）。"""
    if _is_muted(user):
        raise HTTPException(
            status_code=403, detail=f"账号已被禁言，至 {user.mute_until}"
        )


def _like_escape(term: str) -> str:
    """转义 LIKE 模式里的通配符，使搜索按**字面量**匹配。

    不转义时 `?q=%` 会匹配所有文章、`?q=_` 匹配所有单字符词——用户输入
    "%" 得到全量结果属于明显的语义错误，也容易被当成可放大的查询面。
    配 ESCAPE '\' 使用。
    """
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _build_summary(content: str) -> str:
    """从 Markdown 正文自动截取摘要（PRD §8-D2，摘要不由用户填写）。

    依次剔除代码围栏、行内代码、图片、标题符号、链接语法与强调符号，
    压掉空白后取前 100 字；空正文兜底为空串。
    """
    text = content or ""
    text = _CODE_FENCE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(" ", text)
    text = _MD_IMAGE_RE.sub(" ", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _HEADING_RE.sub("", text)
    text = _MD_EMPHASIS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:SUMMARY_LEN]


def _first_image(content: str) -> str:
    """正文第一幅图（缩略图来源之一，PRD §0.5 缩略图）。"""
    m = _MD_IMAGE_RE.search(content or "")
    return m.group(1) if m else ""


def _thumb_url(article: ForumArticle) -> str:
    """缩略图：封面优先，其次正文首图，都没有则空串（前端据此不渲染该位）。"""
    return article.cover_url or _first_image(article.content)


# ── 请求 schemas ──────────────────────────────────────────────────
class ArticleCreateRequest(BaseModel):
    """发帖 / 作者编辑重提共用同一份请求体（PRD §9-12：写路径必须单一实现）。

    extra="forbid"：多传字段（如误传 `status` / `authorId`）直接 422。
    处理器本来就不读这些字段，不构成越权，但静默忽略会让前端字段名写错时
    表现为"改了没反应"，很难排查。
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    category_id: int = Field(..., alias="categoryId", description="所属普通板块 id")
    title: str = Field(..., max_length=255)
    content: str = Field(..., description="Markdown 源码")
    cover_url: str = Field(default="", alias="coverUrl", max_length=512)
    tags: list[str] = Field(default_factory=list, description=f"最多 {MAX_TAGS_PER_ARTICLE} 个")


class AdminArticleUpdateRequest(BaseModel):
    """后台改属性：板块/标签/封面/标题。**状态不变**（管理员本人即审核者，PRD §8-D14）。"""

    model_config = ConfigDict(populate_by_name=True)

    category_id: Optional[int] = Field(None, alias="categoryId")
    title: Optional[str] = Field(None, max_length=255)
    cover_url: Optional[str] = Field(None, alias="coverUrl", max_length=512)
    tags: Optional[list[str]] = None


class ReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: int = Field(..., description="1=通过, 2=驳回")
    review_note: str = Field(default="", alias="reviewNote", max_length=REVIEW_NOTE_MAX)


class OfflineRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reason: str = Field(default="", max_length=REVIEW_NOTE_MAX)


class CommentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(..., description="纯文本，不接受 Markdown 与 HTML（PRD §8-D5）")
    parent_id: int = Field(default=0, alias="parentId", description="0=顶层评论；非 0=所属顶层评论 id")
    reply_to_user_id: Optional[int] = Field(default=None, alias="replyToUserId")


class CategoryCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=32, description="小写字母数字，创建后不可改")
    color: str = Field(default="#6366f1", max_length=16)
    sort_order: int = Field(default=99, alias="sortOrder")


class CategoryUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=16)
    sort_order: Optional[int] = Field(None, alias="sortOrder")
    is_hidden: Optional[int] = Field(None, alias="isHidden")


class TagCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., max_length=50)


class TagUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, max_length=50)
    is_hot: Optional[int] = Field(None, alias="isHot")


class TagMergeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_tag_id: int = Field(..., alias="targetTagId")


class ConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    bannerTitle: Optional[str] = Field(None, max_length=50)
    bannerSubtitle: Optional[str] = Field(None, max_length=100)
    bannerImage: Optional[str] = Field(None, max_length=512)
    defaultSort: Optional[str] = Field(None, max_length=20)
    searchPlaceholder: Optional[str] = Field(None, max_length=30)
    rewardEnabled: Optional[str] = Field(None, max_length=4)
    rewardPresets: Optional[str] = Field(None, max_length=64)
    rewardCommission: Optional[str] = Field(None, max_length=8)


# ── 响应构造（camelCase 契约，PRD §7.4） ─────────────────────────
def _author_brief(user: Optional[User]) -> dict:
    """作者简卡。第一阶段无用户头像字段（users 表无 avatar 列），avatar 恒为 None，
    前端回退内置默认头像；徽章只区分管理员（等级/头衔属第二阶段，PRD §6.5.3）。"""
    if user is None:
        return {"id": 0, "name": "已注销用户", "avatar": None, "badge": None}
    return {
        "id": user.id,
        "name": user.nickname or user.username,
        "avatar": None,
        "badge": "管理员" if user.role == "admin" else None,
    }


def _category_brief(cat: Optional[ForumCategory]) -> Optional[dict]:
    if cat is None:
        return None
    return {
        "id": cat.id,
        "code": cat.code,
        "name": cat.name,
        "color": cat.color,
        "sortOrder": cat.sort_order,
        "isSystem": cat.is_system,
        "isHidden": cat.is_hidden,
    }


def _tag_brief(tag: ForumTag) -> dict:
    return {"id": tag.id, "name": tag.name, "useCount": tag.use_count}


def _ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


def _page_payload(items: list, page: int, page_size: int, total: int) -> dict:
    """分页包络（结构与公告 PageResponse 保持一致）。"""
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


# ── 查询helper ────────────────────────────────────────────────────
async def _get_category_by_id(db: AsyncSession, category_id: int) -> Optional[ForumCategory]:
    r = await db.execute(select(ForumCategory).where(ForumCategory.id == category_id))
    return r.scalar_one_or_none()


async def _get_category_by_code(db: AsyncSession, code: str) -> Optional[ForumCategory]:
    r = await db.execute(select(ForumCategory).where(ForumCategory.code == code))
    return r.scalar_one_or_none()


async def _get_article(db: AsyncSession, article_id: int) -> Optional[ForumArticle]:
    r = await db.execute(select(ForumArticle).where(ForumArticle.id == article_id))
    return r.scalar_one_or_none()


async def _get_users(db: AsyncSession, user_ids: set[int]) -> dict[int, User]:
    ids = [i for i in user_ids if i]
    if not ids:
        return {}
    r = await db.execute(select(User).where(User.id.in_(ids)))
    return {u.id: u for u in r.scalars().all()}


async def _get_tags_of_articles(db: AsyncSession, article_ids: list[int]) -> dict[int, list[ForumTag]]:
    """一次取出多篇文章的标签（避免 N+1 查询）。"""
    if not article_ids:
        return {}
    r = await db.execute(
        select(ForumArticleTag.article_id, ForumTag)
        .join(ForumTag, ForumTag.id == ForumArticleTag.tag_id)
        .where(ForumArticleTag.article_id.in_(article_ids))
        .order_by(ForumTag.id.asc())
    )
    out: dict[int, list[ForumTag]] = {}
    for article_id, tag in r.all():
        out.setdefault(article_id, []).append(tag)
    return out


async def _article_item(db: AsyncSession, article: ForumArticle, user: Optional[User] = None) -> dict:
    """文章列表项 / 详情项的公共部分（详情再叠加 content / liked / favorited）。"""
    cat = await _get_category_by_id(db, article.category_id)
    author = await _get_users(db, {article.author_id})
    tags = (await _get_tags_of_articles(db, [article.id])).get(article.id, [])
    item = {
        "id": article.id,
        "title": article.title,
        "summary": article.summary,
        "coverUrl": article.cover_url,
        "thumbUrl": _thumb_url(article),
        "category": _category_brief(cat),
        "tags": [{"id": t.id, "name": t.name} for t in tags],
        "isTop": article.is_top,
        "isFeatured": article.is_featured,
        "status": article.status,
        "statusText": ARTICLE_STATUS_TEXT.get(article.status, ""),
        "removeBy": article.remove_by,
        "resubmitCount": article.resubmit_count,
        "author": _author_brief(author.get(article.author_id)),
        "viewCount": article.view_count,
        "likeCount": article.like_count,
        "commentCount": article.comment_count,
        "favoriteCount": article.favorite_count,
        "publishTime": article.publish_time,
        "createTime": article.create_time,
        "updateTime": article.update_time,
    }
    if user is not None:
        # 作者/管理员视角才下发 reviewNote（公开列表不含，PRD §7.4）
        if article.author_id == user.id or user.role == "admin":
            item["reviewNote"] = article.review_note
    if article.status == STATUS_RECYCLED:
        # 回收站帖只补列表字段（删除时间 / 剩余天数 / 删除前状态），**不含正文**——
        # 要看完整内容先恢复，恢复是零风险操作（回收站 PRD §1.4 / §0.4-G）
        item.update(_recycle_fields(article))
    return item


async def _article_items(
    db: AsyncSession, articles: list[ForumArticle], user: Optional[User] = None
) -> list[dict]:
    """批量构造列表项：一次取齐分类/作者/标签，避免逐条查询。"""
    if not articles:
        return []
    cat_ids = {a.category_id for a in articles}
    author_ids = {a.author_id for a in articles}
    cat_rows = (
        (await db.execute(select(ForumCategory).where(ForumCategory.id.in_(cat_ids)))).scalars().all()
    )
    cat_map = {c.id: c for c in cat_rows}
    user_map = await _get_users(db, author_ids)
    tag_map = await _get_tags_of_articles(db, [a.id for a in articles])

    show_note = user is not None
    items = []
    for a in articles:
        item = {
            "id": a.id,
            "title": a.title,
            "summary": a.summary,
            "coverUrl": a.cover_url,
            "thumbUrl": _thumb_url(a),
            "category": _category_brief(cat_map.get(a.category_id)),
            "tags": [{"id": t.id, "name": t.name} for t in tag_map.get(a.id, [])],
            "isTop": a.is_top,
            "isFeatured": a.is_featured,
            "status": a.status,
            "statusText": ARTICLE_STATUS_TEXT.get(a.status, ""),
            "removeBy": a.remove_by,
            "resubmitCount": a.resubmit_count,
            "author": _author_brief(user_map.get(a.author_id)),
            "viewCount": a.view_count,
            "likeCount": a.like_count,
            "commentCount": a.comment_count,
            "favoriteCount": a.favorite_count,
            "publishTime": a.publish_time,
            "createTime": a.create_time,
            "updateTime": a.update_time,
        }
        if show_note and (a.author_id == user.id or user.role == "admin"):
            item["reviewNote"] = a.review_note
        if a.status == STATUS_RECYCLED:
            item.update(_recycle_fields(a))
        items.append(item)
    return items


# ── 标签与计数服务（PRD §8-D6 / §8-D8 的唯一落点） ─────────────────
async def _tag_ids_of(db: AsyncSession, article_id: int) -> list[int]:
    r = await db.execute(
        select(ForumArticleTag.tag_id).where(ForumArticleTag.article_id == article_id)
    )
    return list(r.scalars().all())


async def _bump_tag_use_count(db: AsyncSession, tag_ids: list[int], delta: int) -> None:
    """use_count 原子增减（禁止 read-modify-write，否则并发下计数丢失）。"""
    if not tag_ids or delta == 0:
        return
    await db.execute(
        update(ForumTag)
        .where(ForumTag.id.in_(tag_ids))
        .values(use_count=ForumTag.use_count + delta)
    )


async def _recalc_tag_use_count(db: AsyncSession, tag_ids: list[int]) -> None:
    """按 status=1 文章重算 use_count（标签合并/删除后对受影响标签整体重算）。"""
    if not tag_ids:
        return
    r = await db.execute(
        select(ForumArticleTag.tag_id, func.count())
        .select_from(ForumArticleTag)
        .join(ForumArticle, ForumArticle.id == ForumArticleTag.article_id)
        .where(ForumArticleTag.tag_id.in_(tag_ids), ForumArticle.status == STATUS_PUBLISHED)
        .group_by(ForumArticleTag.tag_id)
    )
    counted = {tag_id: cnt for tag_id, cnt in r.all()}
    for tag_id in tag_ids:
        await db.execute(
            update(ForumTag).where(ForumTag.id == tag_id).values(use_count=counted.get(tag_id, 0))
        )


async def _resolve_tag(db: AsyncSession, name: str) -> ForumTag:
    """按名称取标签，不存在则新建（发帖时回车自动新建，source='user'）。"""
    name = name.strip()
    r = await db.execute(select(ForumTag).where(ForumTag.name == name))
    tag = r.scalar_one_or_none()
    if tag is not None:
        return tag
    tag = ForumTag(
        name=name,
        use_count=0,
        is_hot=0,
        source="user",
        create_time=_now_iso(),
    )
    db.add(tag)
    await db.flush()  # 取主键，不提交
    return tag


async def _sync_article_tags(
    db: AsyncSession, article: ForumArticle, tag_names: list[str]
) -> None:
    """把文章的标签关联整份替换为 tag_names 对应的集合。

    - 标签名去重（去首尾空白）后逐个解析，不存在的自动新建；
    - 差集写关联表；文章处于 status=1 时按差集增减 use_count（PRD §8-D8 ③）。
    """
    names: list[str] = []
    for raw in tag_names:
        n = (raw or "").strip()
        if n and n not in names:
            names.append(n)
    if len(names) > MAX_TAGS_PER_ARTICLE:
        raise HTTPException(status_code=400, detail=f"标签最多 {MAX_TAGS_PER_ARTICLE} 个")
    for n in names:
        if len(n) > MAX_TAG_NAME_LEN:
            raise HTTPException(status_code=400, detail=f"单个标签不能超过 {MAX_TAG_NAME_LEN} 字")

    new_tags = [await _resolve_tag(db, n) for n in names]
    new_ids = {t.id for t in new_tags}

    r = await db.execute(
        select(ForumArticleTag).where(ForumArticleTag.article_id == article.id)
    )
    rows = r.scalars().all()
    old_ids = {row.tag_id for row in rows}
    if old_ids == new_ids:
        return

    now = _now_iso()
    for row in rows:
        if row.tag_id not in new_ids:
            await db.delete(row)
    for tag_id in new_ids - old_ids:
        db.add(
            ForumArticleTag(
                article_id=article.id, tag_id=tag_id, create_time=now
            )
        )
    if article.status == STATUS_PUBLISHED:
        await _bump_tag_use_count(db, list(new_ids - old_ids), +1)
        await _bump_tag_use_count(db, list(old_ids - new_ids), -1)
    await db.flush()


async def _set_article_status(
    db: AsyncSession,
    article: ForumArticle,
    new_status: int,
    publish_time_override: Optional[str] = None,
) -> None:
    """文章状态转移的唯一入口（第一阶段 PRD §8-D8 + 回收站 PRD §1.1）。

    use_count 只挂在这一个转移点上：
    - 进入 status=1（审核通过 / 恢复上架 / **从回收站恢复回已发布**）→ 按当期标签各 +1，
      重写 publish_time（`publish_time_override` 非空时用它替代 _now_iso()——
      回收站恢复回填删除前的发布时间，防"删除→恢复"刷榜）；
    - 离开 status=1（下架 / 作者编辑重提 / **作者删除进回收站** / 硬删除前置）→
      按当期标签各 -1，清空 publish_time。

    ⚠️ 任何绕过本函数直接 `article.status = x` 的写法都会让 use_count 漂移。
    """
    old_status = article.status
    if old_status == new_status:
        return
    tag_ids = await _tag_ids_of(db, article.id)
    if new_status == STATUS_PUBLISHED:
        article.publish_time = publish_time_override or _now_iso()
        if old_status != STATUS_PUBLISHED:
            await _bump_tag_use_count(db, tag_ids, +1)
    else:
        article.publish_time = ""
        if old_status == STATUS_PUBLISHED:
            await _bump_tag_use_count(db, tag_ids, -1)
    article.status = new_status
    await db.flush()


# ── 回收站字段下发（前端不自己算剩余天数，§7.4） ──────────────────
def _recycle_fields(article: ForumArticle) -> dict:
    """回收站帖专属下发字段。只给列表字段，**绝不下发正文**（回收站 PRD §1.4）。"""
    return {
        "deletedAt": article.deleted_at,
        "daysLeft": recycle_days_left(article.deleted_at),
        "statusBeforeDelete": article.status_before_delete,
    }


async def _toggle_relation(
    db: AsyncSession, table: str, create: dict, match: dict
) -> int:
    """关系表切换（存在即删、不存在即插），返回 +1 新增 / -1 删除 / 0 无变化。

    为什么不用「先 SELECT 再决定插还是删」：那是 check-then-act，同一用户的两个并发
    请求会双双看到"无行"、双双 INSERT，撞 `(article_id, user_id)` 唯一约束抛
    IntegrityError → 500（PRD §10.3 明确要求"连续快速点击 10 次点赞"不能出错）。

    改用 `INSERT OR IGNORE` + 按 rowcount 分支：每条语句自身原子，再与计数 UPDATE
    同事务提交，因此「关系行数 == 冗余计数」的不变量在并发下依然成立——
    两个并发点赞最终是"插入 + 删除"配对，行数与计数同步归零，不会漂移。

    table / 列名都是本模块的内部字面量（不接受任何外部输入），只有值走绑定参数。
    """
    cols = ", ".join(create)
    placeholders = ", ".join(f":{c}" for c in create)
    result = await db.execute(
        text(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"), create
    )
    if result.rowcount == 1:
        return 1
    where = " AND ".join(f"{k} = :{k}" for k in match)
    result = await db.execute(text(f"DELETE FROM {table} WHERE {where}"), match)
    return -1 if result.rowcount == 1 else 0


async def _bump_comment_count(db: AsyncSession, article_id: int, delta: int) -> None:
    """comment_count 原子增减（顶层评论与回复都算 1，PRD §8-D15 ②）。"""
    await db.execute(
        update(ForumArticle)
        .where(ForumArticle.id == article_id)
        .values(comment_count=ForumArticle.comment_count + delta)
    )


# ── 可见性判定 ────────────────────────────────────────────────────
def _is_admin(user: Optional[User]) -> bool:
    return user is not None and user.role == "admin"


def _can_view_article(article: ForumArticle, user: Optional[User]) -> bool:
    """文章可见性（第一阶段 PRD §5.4.2 + 回收站 PRD §1.4）。

    - status=1 全文公开；
    - 未公开（0/2/3）仅作者本人与管理员可见；
    - **status=4 回收站对所有人一律不可见，含作者本人与管理员**（§6-D4）：
      _can_view_article 被详情/评论/点赞/收藏/浏览/作者其他帖子六个接口共用，
      这里放行作者就得在每个接口再补一层 status==1 守卫，不如一开始就不放行——
      回收站的数据源是 GET /my/articles?status=4，不经过详情接口。
    """
    if article.status == STATUS_RECYCLED:
        return False
    if article.status == STATUS_PUBLISHED:
        return True
    if user is None:
        return False
    return article.author_id == user.id or user.role == "admin"


# ══════════════════════════════════════════════════════════════════
# 公开接口
# ══════════════════════════════════════════════════════════════════
@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """板块列表（过滤 is_hidden，含系统板块，带文章数）。"""
    r = await db.execute(select(ForumCategory).where(ForumCategory.is_hidden == 0).order_by(ForumCategory.sort_order.asc()))
    cats = r.scalars().all()
    # 前台的 articleCount 保持"已发布"口径（纯展示；注意与后台删除守卫的
    # "全部状态"口径**故意不同**，那里是安全判定不是展示）
    cnt_r = await db.execute(
        select(ForumCategory.id, func.count())
        .select_from(ForumArticle)
        .where(ForumArticle.category_id == ForumCategory.id, ForumArticle.status == STATUS_PUBLISHED)
        .group_by(ForumCategory.id)
    )
    counts = dict(cnt_r.all())
    items = []
    for c in cats:
        d = _category_brief(c)
        d["articleCount"] = counts.get(c.id, 0)
        items.append(d)
    return _ok(items)


@router.get("/tags/hot")
async def list_hot_tags(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """热门标签：is_hot=1 优先，其余按 use_count 倒序补齐。"""
    r = await db.execute(
        select(ForumTag)
        .order_by(ForumTag.is_hot.desc(), ForumTag.use_count.desc(), ForumTag.id.desc())
        .limit(limit)
    )
    return _ok([_tag_payload(t) for t in r.scalars().all()])


@router.get("/stats")
async def forum_stats(db: AsyncSession = Depends(get_db)):
    """社区统计：文章数 / 浏览数（已发布之和）/ 标签数（被已发布文章引用的去重标签数）。"""
    art_r = await db.execute(
        select(func.count(), func.coalesce(func.sum(ForumArticle.view_count), 0)).where(
            ForumArticle.status == STATUS_PUBLISHED
        )
    )
    article_count, view_count = art_r.one()
    tag_r = await db.execute(
        select(func.count(func.distinct(ForumArticleTag.tag_id)))
        .select_from(ForumArticleTag)
        .join(ForumArticle, ForumArticle.id == ForumArticleTag.article_id)
        .where(ForumArticle.status == STATUS_PUBLISHED)
    )
    return _ok(
        {
            "articleCount": article_count or 0,
            "viewCount": view_count or 0,
            "tagCount": tag_r.scalar() or 0,
        }
    )


@router.get("/config")
async def public_config(db: AsyncSession = Depends(get_db)):
    """前台配置（只下发 PUBLIC_CONFIG_KEYS，打赏预留键不出现在公开响应）。"""
    await ensure_seeded()
    r = await db.execute(select(ForumConfig))
    values = {row.key: row.value for row in r.scalars().all()}
    data = {k: values.get(k, FORUM_CONFIG_DEFAULTS[k]) for k in PUBLIC_CONFIG_KEYS}
    if data.get("defaultSort") not in SORT_OPTIONS:
        data["defaultSort"] = SORT_LATEST
    return _ok(data)


@router.get("/articles")
async def list_articles(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=12, ge=1, le=100),
    category: Optional[str] = Query(default=None, description="板块 code；缺省或 home=全部，recommend=置顶∪加精"),
    sort: str = Query(default=SORT_LATEST, description="latest | views | comments"),
    q: Optional[str] = Query(default=None, description="标题 / 摘要关键词"),
    tag: Optional[str] = Query(default=None, description="标签名精确匹配"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """公开文章列表：只含 status=1；置顶帖在任意排序档中都恒排最前。"""
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    stmt = select(ForumArticle).where(ForumArticle.status == STATUS_PUBLISHED)
    count_stmt = select(func.count()).select_from(ForumArticle).where(
        ForumArticle.status == STATUS_PUBLISHED
    )

    code = (category or CODE_HOME).strip() or CODE_HOME
    if code == CODE_RECOMMEND:
        # §0.3-D：推荐 = is_featured=1 OR is_top=1，且按热度（view_count）排序
        stmt = stmt.where(
            or_(ForumArticle.is_featured == 1, ForumArticle.is_top == 1)
        )
        count_stmt = count_stmt.where(
            or_(ForumArticle.is_featured == 1, ForumArticle.is_top == 1)
        )
        sort_key = SORT_VIEWS  # 推荐档固定按浏览量
    else:
        sort_key = sort if sort in SORT_OPTIONS else SORT_LATEST
        if code != CODE_HOME:
            cat = await _get_category_by_code(db, code)
            if cat is None:
                return _ok(_page_payload([], page, page_size, 0))
            stmt = stmt.where(ForumArticle.category_id == cat.id)
            count_stmt = count_stmt.where(ForumArticle.category_id == cat.id)

    keyword = (q or "").strip()
    if keyword:
        like = f"%{_like_escape(keyword)}%"
        cond = or_(
            ForumArticle.title.like(like, escape="\\"),
            ForumArticle.summary.like(like, escape="\\"),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    tag_name = (tag or "").strip()
    if tag_name:
        sub = (
            select(ForumArticleTag.article_id)
            .join(ForumTag, ForumTag.id == ForumArticleTag.tag_id)
            .where(ForumTag.name == tag_name)
        )
        stmt = stmt.where(ForumArticle.id.in_(sub))
        count_stmt = count_stmt.where(ForumArticle.id.in_(sub))

    sort_col = {
        SORT_LATEST: ForumArticle.publish_time,
        SORT_VIEWS: ForumArticle.view_count,
        SORT_COMMENTS: ForumArticle.comment_count,
    }[sort_key]
    stmt = (
        stmt.order_by(ForumArticle.is_top.desc(), sort_col.desc(), ForumArticle.id.desc())
        .offset(offset)
        .limit(page_size)
    )

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt)).scalars().all()
    return _ok(_page_payload(await _article_items(db, list(rows), user), page, page_size, total))


@router.get("/articles/{article_id}")
async def get_article_detail(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """文章详情（含 Markdown 源码、作者卡、当前用户的 liked/favorited 态）。

    浏览量**不在**这里计数——前端挂载后单独调 POST /articles/{id}/view（§8-D4）。
    未公开（待审核/已驳回/已下架）对非作者非管理员一律 404，不暴露存在性。
    """
    article = await _get_article(db, article_id)
    if article is None or not _can_view_article(article, user):
        raise HTTPException(status_code=404, detail="帖子不存在或已被删除")

    item = await _article_item(db, article, user)
    item["content"] = article.content
    item["contentType"] = article.content_type
    item["reviewNote"] = article.review_note

    liked = favorited = False
    if user is not None:
        liked = (
            await db.execute(
                select(ForumArticleLike.id).where(
                    ForumArticleLike.article_id == article_id,
                    ForumArticleLike.user_id == user.id,
                )
            )
        ).scalar_one_or_none() is not None
        favorited = (
            await db.execute(
                select(ForumArticleFavorite.id).where(
                    ForumArticleFavorite.article_id == article_id,
                    ForumArticleFavorite.user_id == user.id,
                )
            )
        ).scalar_one_or_none() is not None
    item["liked"] = liked
    item["favorited"] = favorited
    return _ok(item)


def _comment_node(
    comment: ForumComment,
    author: Optional[User],
    liked_ids: set[int],
    reply_to_name: Optional[str] = None,
    replies: Optional[list[dict]] = None,
) -> dict:
    node = {
        "id": comment.id,
        "articleId": comment.article_id,
        "content": comment.content,
        "parentId": comment.parent_id,
        "replyToUserId": comment.reply_to_user_id,
        "replyToName": reply_to_name,
        "likeCount": comment.like_count,
        "liked": comment.id in liked_ids,
        "status": comment.status,
        "author": _author_brief(author),
        "createTime": comment.create_time,
    }
    if replies is not None:
        node["replies"] = replies
    return node


async def _comment_nodes(
    db: AsyncSession, comments: list[ForumComment], viewer: Optional[User]
) -> list[dict]:
    """批量构造评论树：只对顶层评论分页，顶层按时间倒序、其下回复按时间正序。"""
    if not comments:
        return []
    top = [c for c in comments if c.parent_id == 0]
    replies = [c for c in comments if c.parent_id != 0]
    all_rows = top + replies

    user_map = await _get_users(db, {c.author_id for c in all_rows} | {c.reply_to_user_id or 0 for c in all_rows})
    liked_ids: set[int] = set()
    if viewer is not None:
        r = await db.execute(
            select(ForumCommentLike.comment_id).where(
                ForumCommentLike.user_id == viewer.id,
                ForumCommentLike.comment_id.in_([c.id for c in all_rows]),
            )
        )
        liked_ids = set(r.scalars().all())

    by_parent: dict[int, list[ForumComment]] = {}
    for c in replies:
        by_parent.setdefault(c.parent_id, []).append(c)
    for lst in by_parent.values():
        lst.sort(key=lambda c: (c.create_time, c.id))  # 回复正序：先来后到

    nodes = []
    for c in top:
        child_nodes = [
            _comment_node(
                rc,
                user_map.get(rc.author_id),
                liked_ids,
                reply_to_name=(
                    user_map[rc.reply_to_user_id].nickname or user_map[rc.reply_to_user_id].username
                    if rc.reply_to_user_id and rc.reply_to_user_id in user_map
                    else None
                ),
            )
            for rc in by_parent.get(c.id, [])
        ]
        nodes.append(_comment_node(c, user_map.get(c.author_id), liked_ids, replies=child_nodes))
    return nodes


@router.get("/articles/{article_id}/comments")
async def list_comments(
    article_id: int,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """评论列表：只对顶层评论分页（每页 10 条），其下回复一次性全返且不嵌套 replies。"""
    article = await _get_article(db, article_id)
    if article is None or not _can_view_article(article, user):
        raise HTTPException(status_code=404, detail="帖子不存在或已被删除")

    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    cnt_r = await db.execute(
        select(func.count())
        .select_from(ForumComment)
        .where(
            ForumComment.article_id == article_id,
            ForumComment.parent_id == 0,
            ForumComment.status == COMMENT_NORMAL,
        )
    )
    total = cnt_r.scalar_one()
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    nodes: list[dict] = []
    if offset < total:
        top_r = await db.execute(
            select(ForumComment)
            .where(
                ForumComment.article_id == article_id,
                ForumComment.parent_id == 0,
                ForumComment.status == COMMENT_NORMAL,
            )
            .order_by(ForumComment.create_time.desc(), ForumComment.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        top_rows = list(top_r.scalars().all())
        top_ids = [c.id for c in top_rows]
        reply_rows: list[ForumComment] = []
        if top_ids:
            reply_r = await db.execute(
                select(ForumComment).where(
                    ForumComment.article_id == article_id,
                    ForumComment.parent_id.in_(top_ids),
                    ForumComment.status == COMMENT_NORMAL,
                )
            )
            reply_rows = list(reply_r.scalars().all())
        nodes = await _comment_nodes(db, top_rows + reply_rows, user)

    return _ok(_page_payload(nodes, page, page_size, total))


@router.get("/articles/{article_id}/author-posts")
async def author_other_posts(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """作者其他已发布文章（最多 5 条，按发布时间倒序，不含当前文章）。

    可见性校验与详情/评论接口保持一致：未公开文章对非作者非管理员按 404 处理。
    缺这一步会被用来枚举未公开文章的 id → 作者（详情 404 但本接口 200）。
    """
    article = await _get_article(db, article_id)
    if article is None or not _can_view_article(article, user):
        raise HTTPException(status_code=404, detail="帖子不存在或已被删除")
    r = await db.execute(
        select(ForumArticle)
        .where(
            ForumArticle.author_id == article.author_id,
            ForumArticle.status == STATUS_PUBLISHED,
            ForumArticle.id != article_id,
        )
        .order_by(ForumArticle.publish_time.desc(), ForumArticle.id.desc())
        .limit(5)
    )
    return _ok(
        [
            {"id": a.id, "title": a.title, "viewCount": a.view_count, "publishTime": a.publish_time}
            for a in r.scalars().all()
        ]
    )


@router.post("/articles/{article_id}/view")
async def add_view(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    """浏览量 +1（原子自增；重复刷新重复计数为**已接受行为**，去重属第二阶段）。

    回传新的浏览量，前端可直接就地更新，不必再拉一次详情。

    **匿名可调**（PRD §7.1 把它列在"公开接口"下）：社区站点的绝大多数流量是未登录
    访客，若要求登录会让 viewCount 与 /api/forum/stats 系统性少计——统计数字必须
    与真实浏览一致。本接口不返回任何用户信息，匿名调用无信息泄露面。
    """
    result = await db.execute(
        update(ForumArticle)
        .where(ForumArticle.id == article_id, ForumArticle.status == STATUS_PUBLISHED)
        .values(view_count=ForumArticle.view_count + 1)
    )
    if result.rowcount == 0:
        await db.commit()
        raise HTTPException(status_code=404, detail="帖子不存在或已被删除")
    new_count = (
        await db.execute(
            select(ForumArticle.view_count).where(ForumArticle.id == article_id)
        )
    ).scalar_one()
    await db.commit()
    return _ok({"viewCount": new_count})


@router.get("/users/{user_id}/stats")
async def user_forum_stats(
    user_id: int, db: AsyncSession = Depends(get_db)
):
    """指定用户的公开论坛数据（详情页作者卡用，匿名可调）。

    与 GET /api/forum/my/stats 同结构（同为"某人的发帖/获赞/粉丝"），
    区别只是前者取当前登录用户、这个按 id 取任意用户——**不下发任何私有字段**
    （无邮箱、无禁言时间、无状态，PRD §10.6）。
    """
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _ok(await _user_forum_stats(db, user))


# ══════════════════════════════════════════════════════════════════
# 登录用户接口
# ══════════════════════════════════════════════════════════════════
async def _validate_write_payload(db: AsyncSession, data: ArticleCreateRequest) -> ForumCategory:
    """创建与编辑共用的字段校验（板块必须为非系统板块，PRD §6.2.3）。"""
    title = (data.title or "").strip()
    if not (TITLE_MIN <= len(title) <= TITLE_MAX):
        raise HTTPException(status_code=400, detail=f"标题需为 {TITLE_MIN}-{TITLE_MAX} 个字符")
    content = data.content or ""
    if not (CONTENT_MIN <= len(content) <= CONTENT_MAX):
        raise HTTPException(status_code=400, detail=f"正文需为 {CONTENT_MIN}-{CONTENT_MAX} 个字符")
    cat = await _get_category_by_id(db, data.category_id)
    if cat is None:
        raise HTTPException(status_code=400, detail="请选择板块")
    if cat.is_system:
        raise HTTPException(status_code=400, detail="不能发布到系统板块，请选择一个普通板块")
    return cat


@router.post("/articles")
async def create_article(
    data: ArticleCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """发布文章（先审后发：status=0 待审核，publish_time 为空串）。"""
    _ensure_not_muted(user)
    cat = await _validate_write_payload(db, data)
    now = _now_iso()
    article = ForumArticle(
        category_id=cat.id,
        title=(data.title or "").strip(),
        content=data.content,
        content_type="markdown",
        summary=_build_summary(data.content),
        cover_url=(data.cover_url or "").strip(),
        author_id=user.id,
        status=STATUS_PENDING,
        review_note="",
        is_top=0,
        is_featured=0,
        view_count=0,
        like_count=0,
        favorite_count=0,
        comment_count=0,
        publish_time="",
        remove_by="",
        resubmit_count=0,
        create_time=now,
        update_time=now,
    )
    db.add(article)
    await db.flush()
    await _sync_article_tags(db, article, data.tags or [])
    await db.commit()
    return _ok({"id": article.id, "status": article.status}, "已提交，等待管理员审核")


@router.get("/articles/{article_id}/edit")
async def get_article_for_edit(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """编辑回填（**仅作者本人**；越权/不存在一律 404，不暴露文章存在性）。

    管理员下架的帖子（status=3 且 remove_by='admin'）返回 400，
    因为作者不能靠"编辑重提"绕过下架（PRD §8-D13）。
    回收站帖子（status=4）返回 400"请先恢复"——编辑入口只能从正常状态进，
    回收站里只有「恢复」与「彻底删除」两个动作（回收站 PRD §3.2）。
    """
    article = await _get_article(db, article_id)
    if article is None or article.author_id != user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == STATUS_OFFLINE and article.remove_by == REMOVE_BY_ADMIN:
        raise HTTPException(status_code=400, detail="该帖已被管理员下架，请联系管理员处理")
    if article.status == STATUS_RECYCLED:
        raise HTTPException(status_code=400, detail="该帖已在回收站，请先恢复后再编辑")

    cat = await _get_category_by_id(db, article.category_id)
    tags = (await _get_tags_of_articles(db, [article.id])).get(article.id, [])
    return _ok(
        {
            "id": article.id,
            "categoryId": article.category_id,
            "title": article.title,
            "content": article.content,
            "contentType": article.content_type,
            "coverUrl": article.cover_url,
            "tags": [t.name for t in tags],
            "status": article.status,
            "statusText": ARTICLE_STATUS_TEXT.get(article.status, ""),
            "removeBy": article.remove_by,
            "resubmitCount": article.resubmit_count,
            "reviewNote": article.review_note,
            "canEdit": not (
                article.status == STATUS_OFFLINE and article.remove_by == REMOVE_BY_ADMIN
            ),
            "updateTime": article.update_time,
        }
    )


@router.put("/articles/{article_id}")
async def update_article(
    article_id: int,
    data: ArticleCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """作者编辑重提（**仅作者本人**）：状态一律回到 0 待审核，须管理员重新审核后才公开。

    - 准入范围：0 待审核 / 1 已发布 / 2 已驳回 / 3 已下架且 remove_by='author'；
    - `remove_by='admin'` 的已下架帖返回 400（防止用重提绕过管理员下架）；
    - 回收站帖（status=4）返回 400"请先恢复"——回收站里**没有编辑路径**，
      否则等于开了第二个不用恢复就能改已删帖的口子（回收站 PRD §1.1）；
    - 浏览量 / 点赞 / 收藏 / 评论**全部保留**（同一篇文章的修订，不是新文章）；
    - 标签与摘要走与创建完全相同的实现（PRD §9-12），杜绝"改了正文摘要还是旧的"。
    """
    _ensure_not_muted(user)
    article = await _get_article(db, article_id)
    if article is None or article.author_id != user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == STATUS_OFFLINE and article.remove_by == REMOVE_BY_ADMIN:
        raise HTTPException(status_code=400, detail="该帖已被管理员下架，请联系管理员处理")
    if article.status == STATUS_RECYCLED:
        raise HTTPException(status_code=400, detail="该帖已在回收站，请先恢复后再编辑")

    cat = await _validate_write_payload(db, data)
    article.category_id = cat.id
    article.title = (data.title or "").strip()
    article.content = data.content
    article.content_type = "markdown"
    article.summary = _build_summary(data.content)
    article.cover_url = (data.cover_url or "").strip()
    await _sync_article_tags(db, article, data.tags or [])

    # 状态回退：先按"离开 status=1"扣减标签 use_count，再置 0（统一走唯一入口）
    await _set_article_status(db, article, STATUS_PENDING)
    article.review_note = ""
    article.remove_by = ""
    # 原子自增：与 like/favorite 同一原则（并发编辑同一篇时 ORM 属性自增会丢计数）
    await db.execute(
        update(ForumArticle)
        .where(ForumArticle.id == article.id)
        .values(resubmit_count=ForumArticle.resubmit_count + 1)
    )
    article.update_time = _now_iso()
    await db.commit()
    return _ok(
        {"id": article.id, "status": article.status, "resubmitCount": article.resubmit_count},
        "已重新提交，等待审核",
    )


@router.delete("/articles/{article_id}")
async def delete_own_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """作者删除自己的文章 → **进回收站**（status=4，非物理删）。

    （2026-10-05 语义变更，见 docs/论坛/论坛删除与回收站PRD.md §1.1：旧实现是
    软删 status=3 + remove_by='author'，作者只能靠编辑重提找回；现改为真正的
    删除/恢复闭环。）

    规则：
    - 准入状态 ∈ {0 待审核, 1 已发布, 2 已驳回}；
    - `status=3 且 remove_by='admin'`（管理员下架）→ **400**，否则作者能把治理
      证据搬进回收站、30 天后被自动清除；
    - 已在回收站 → 400「该帖已在回收站」；
    - 越权/不存在 → 404（与本站"越权一律 404"风格一致，不暴露存在性）；
    - 禁言用户**可删**（§0.4-K：删除不是"发言"，与禁言期间仍可点赞/收藏同款例外），
      故此处**不调** _ensure_not_muted；
    - 删前是已发布 → 标签 use_count -1、publish_time 存入新列后清空
      （§1.5，一律走 _set_article_status 单点，不在别处直接改 status）；
    - 浏览量/点赞/收藏/评论**全部保留**（这就是"恢复"的意义）。
    """
    article = await _get_article(db, article_id)
    if article is None or article.author_id != user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == STATUS_RECYCLED:
        raise HTTPException(status_code=400, detail="该帖已在回收站")
    if article.status == STATUS_OFFLINE and article.remove_by == REMOVE_BY_ADMIN:
        raise HTTPException(
            status_code=400, detail="该帖已被管理员下架，请联系管理员处理"
        )
    if article.status not in DELETABLE_STATUSES:
        raise HTTPException(status_code=400, detail="当前状态不允许删除")

    now = _now_iso()
    article.status_before_delete = article.status
    # 删前非已发布时 publish_time 本就是空串，原样存/原样回填即可
    article.publish_time_before_delete = article.publish_time
    article.deleted_at = now
    article.remove_by = REMOVE_BY_AUTHOR
    # 离开 status=1 时标签 -1、publish_time 清空（唯一转移点）
    await _set_article_status(db, article, STATUS_RECYCLED)
    article.update_time = now
    await db.commit()
    return _ok(
        {
            "id": article.id,
            "status": article.status,
            "deletedAt": article.deleted_at,
            "daysLeft": recycle_days_left(article.deleted_at),
        },
        "已移入回收站，30 天内可恢复",
    )


@router.post("/articles/{article_id}/restore")
async def restore_own_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """作者从回收站恢复 → **删除前状态**（status_before_delete），内容零改动、不重审。

    （§0.4-C / §6-D2：回收站是"撤销删除"，不是重新投稿；删前是待审核/已驳回的，
    恢复后仍是待审核/已驳回，照旧等管理员审。）

    - `status != 4` → 404（含已彻底删除 / 从未删除）；
    - **超 30 天 → 410 Gone**（deleted_at 是唯一权威，接口自校验，§0.4-F）：
      漏挂 crontab 也不影响正确性，超期帖恢复不了也列不出来，只是数据多留几天；
    - 恢复到 status=1 时回填删除前的 publish_time（§0.4-D 防刷榜）；
      **存量迁移帖该列为空时兜底为当前时间**（历史数据无法还原原发布时间）；
    - 清空 deleted_at / status_before_delete / publish_time_before_delete 与 remove_by；
    - 禁言用户**可恢复**（同删除，不属"发言"）。
    """
    article = await _get_article(db, article_id)
    if article is None or article.author_id != user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status != STATUS_RECYCLED:
        raise HTTPException(status_code=404, detail="该帖不在回收站")
    if is_recycle_expired(article.deleted_at):
        raise HTTPException(
            status_code=410, detail="已超过 30 天保留期，无法恢复"
        )

    target = article.status_before_delete
    if target not in RESTORE_TARGETS:
        # 纵深防御：数据异常时按待审核兜底（最保守，不会把未过审内容直接公开）
        target = STATUS_PENDING
    now = _now_iso()
    await _set_article_status(
        db,
        article,
        target,
        publish_time_override=article.publish_time_before_delete or None,
    )
    article.deleted_at = ""
    article.status_before_delete = 0
    article.publish_time_before_delete = ""
    article.remove_by = ""
    article.update_time = now
    await db.commit()
    return _ok(
        await _article_item(db, article, user),
        "已恢复上架，重新公开" if target == STATUS_PUBLISHED else "已恢复",
    )


@router.delete("/articles/{article_id}/purge")
async def purge_own_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """回收站内**彻底删除**（物理删 + 级联，**不可恢复**，也不进任何回收站）。

    与 `DELETE /articles/{id}`（进回收站，可恢复）刻意分成两个动作：
    入口在回收站页面行内，前端必须走 ConfirmDialog 二次确认（§3.2 / §6-D14），
    点"取消"不发请求。

    - 仅作者本人；越权/不存在/已被超期清理 → 404；
    - `status != 4` → 400（正常状态的帖子要走"删除进回收站"，不走这里——
      防止把"删一下试试"直接变成不可恢复的硬删）；
    - 级联与超期清理、管理员硬删**共用** forum_core.cascade_delete_article；
    - 标签 use_count **不再扣减**（进回收站时已扣过，§1.5）；
    - **不动 uploads/forum/ 下的图片文件**（图床冗余清理归第三阶段，§6-D12）。
    """
    article = await _get_article(db, article_id)
    if article is None or article.author_id != user.id:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status != STATUS_RECYCLED:
        raise HTTPException(status_code=400, detail="该帖不在回收站")
    await cascade_delete_article(db, article)
    await db.commit()
    return _ok({"id": article_id}, "已永久删除")


@router.get("/my/articles")
async def my_articles(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    status: Optional[int] = Query(default=None, description="0待审核 1已发布 2已驳回 3已下架 4回收站；缺省全部"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """我的文章：当前用户全部状态的文章（含 reviewNote、removeBy、resubmitCount）。

    **回收站页面的数据源**（§5.1）：传 status=4 即得回收站列表，列表项额外下发
    deletedAt / daysLeft / statusBeforeDelete；响应再整体下发 `recycleDays`
    （保留期**单一来源**，前端提示条与"剩余 N 天"都取它，不硬编码 30）。
    """
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size
    stmt = select(ForumArticle).where(ForumArticle.author_id == user.id)
    count_stmt = select(func.count()).select_from(ForumArticle).where(
        ForumArticle.author_id == user.id
    )
    if status is not None:
        stmt = stmt.where(ForumArticle.status == status)
        count_stmt = count_stmt.where(ForumArticle.status == status)
    else:
        # 回收站已有独立页面 /forum/recycle，"我的文章"默认全部排除回收站
        stmt = stmt.where(ForumArticle.status != STATUS_RECYCLED)
        count_stmt = count_stmt.where(ForumArticle.status != STATUS_RECYCLED)
    stmt = stmt.order_by(ForumArticle.update_time.desc(), ForumArticle.id.desc()).offset(offset).limit(page_size)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt)).scalars().all()
    payload = _page_payload(await _article_items(db, list(rows), user), page, page_size, total)
    # 保留期天数由后端**单一来源**下发（改 RECYCLE_DAYS 一处，前端零改动）
    payload["recycleDays"] = RECYCLE_DAYS
    return _ok(payload)


async def _user_forum_stats(db: AsyncSession, user: User) -> dict:
    """某人的公开论坛三项数据：发帖数（已发布）/ 获赞数（其文章 like_count 之和）/ 粉丝数。

    三个接口共用它：/my/stats（当前登录用户）、/users/{id}/stats（详情页作者卡，
    匿名可调）、/admin/user-stats/{id}（后台）。口径不一致会导致"详情页与
    /forum/my 数字对不上"这种难查的问题，故单一实现。
    """
    r = await db.execute(
        select(func.count(), func.coalesce(func.sum(ForumArticle.like_count), 0)).where(
            ForumArticle.author_id == user.id, ForumArticle.status == STATUS_PUBLISHED
        )
    )
    post_count, like_count = r.one()
    return {
        "author": _author_brief(user),
        "postCount": post_count or 0,
        "likeCount": like_count or 0,
        # 关注体系属第二阶段（§0.3-B）：由接口返回 0，前端不写死
        "followerCount": 0,
    }


@router.get("/my/stats")
async def my_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """侧边栏用户卡数据。followerCount 恒 0（关注体系属第二阶段，PRD §0.3-B）——
    由接口返回而非前端写死，第二阶段改一处即可。"""
    return _ok(await _user_forum_stats(db, user))


@router.post("/articles/{article_id}/like")
async def toggle_article_like(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """文章点赞切换（幂等：存在即删、不存在即插），计数与关系表同事务。"""
    article = await _get_article(db, article_id)
    if article is None or not _can_view_article(article, user):
        raise HTTPException(status_code=404, detail="帖子不存在或已被删除")

    delta = await _toggle_relation(
        db,
        "forum_article_likes",
        {"article_id": article_id, "user_id": user.id, "create_time": _now_iso()},
        {"article_id": article_id, "user_id": user.id},
    )
    if delta:
        await db.execute(
            update(ForumArticle)
            .where(ForumArticle.id == article_id)
            .values(like_count=ForumArticle.like_count + delta)
        )
    await db.commit()
    new_count = (await _get_article(db, article_id)).like_count

    # 站内信：新增点赞（delta=+1）且非作者自赞时，定向通知文章作者（PRD v1.1 §7.3）。
    # 取消点赞（delta=-1）不产生通知；通知失败不影响点赞主流程。
    if delta == 1 and article.author_id and article.author_id != user.id:
        try:
            from .messages import create_like_message

            await create_like_message(
                db,
                article_id=article_id,
                comment_id=None,
                liker_id=user.id,
                author_id=article.author_id,
            )
        except Exception as e:
            logger.warning("发送点赞通知失败: %s", e)

    return _ok({"liked": delta == 1, "likeCount": max(new_count, 0)})


@router.post("/articles/{article_id}/favorite")
async def toggle_article_favorite(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """文章收藏切换（幂等，语义同点赞）。"""
    article = await _get_article(db, article_id)
    if article is None or not _can_view_article(article, user):
        raise HTTPException(status_code=404, detail="帖子不存在或已被删除")

    delta = await _toggle_relation(
        db,
        "forum_article_favorites",
        {"article_id": article_id, "user_id": user.id, "create_time": _now_iso()},
        {"article_id": article_id, "user_id": user.id},
    )
    if delta:
        await db.execute(
            update(ForumArticle)
            .where(ForumArticle.id == article_id)
            .values(favorite_count=ForumArticle.favorite_count + delta)
        )
    await db.commit()
    new_count = (await _get_article(db, article_id)).favorite_count
    return _ok({"favorited": delta == 1, "favoriteCount": max(new_count, 0)})


@router.post("/articles/{article_id}/comments")
async def create_comment(
    article_id: int,
    data: CommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """发表评论 / 发表回复（两级楼中楼，PRD §8-D15）。

    - 省略 parentId 或 =0 → 顶层评论；
    - 传 parentId → 回复，parentId **只允许指向顶层评论**（拒绝第三级嵌套）；
    - replyToUserId 记录"回复给谁"（对回复再回复时仍挂同一顶层评论）。
    """
    _ensure_not_muted(user)
    article = await _get_article(db, article_id)
    if article is None or not _can_view_article(article, user):
        raise HTTPException(status_code=404, detail="帖子不存在或已被删除")

    content = (data.content or "").strip()
    if not (COMMENT_MIN <= len(content) <= COMMENT_MAX):
        raise HTTPException(status_code=400, detail=f"评论需为 {COMMENT_MIN}-{COMMENT_MAX} 个字符")

    parent_id = data.parent_id or 0
    if parent_id:
        parent = (
            await db.execute(select(ForumComment).where(ForumComment.id == parent_id))
        ).scalar_one_or_none()
        if parent is None or parent.article_id != article_id or parent.parent_id != 0:
            raise HTTPException(status_code=400, detail="要回复的评论不存在")
        if parent.status != COMMENT_NORMAL:
            raise HTTPException(status_code=400, detail="要回复的评论已被删除")
    elif data.reply_to_user_id:
        raise HTTPException(status_code=400, detail="回复他人时必须指定所属的顶层评论")

    comment = ForumComment(
        article_id=article_id,
        author_id=user.id,
        content=content,
        parent_id=parent_id,
        reply_to_user_id=data.reply_to_user_id,
        status=COMMENT_NORMAL,
        like_count=0,
        create_time=_now_iso(),
    )
    db.add(comment)
    await db.flush()
    await _bump_comment_count(db, article_id, +1)
    await db.commit()

    # 站内信：评论创建成功后，直接发送通知
    try:
        from .messages import create_reply_message, create_article_comment_message

        if parent_id:
            # 回复评论：通知被回复的人
            target_user_id = data.reply_to_user_id or parent.author_id
            if target_user_id and target_user_id != user.id:
                await create_reply_message(
                    db,
                    article_id=article_id,
                    comment_id=comment.id,
                    reply_user_id=user.id,
                    target_user_id=target_user_id,
                    reply_content=comment.content,
                    replied_comment_content=parent.content,
                )
        else:
            # 顶层评论：通知文章作者
            if article.author_id and article.author_id != user.id:
                await create_article_comment_message(
                    db,
                    article_id=article_id,
                    comment_id=comment.id,
                    commenter_id=user.id,
                    article_author_id=article.author_id,
                    comment_content=comment.content,
                )
    except Exception as e:
        logger.warning("发送回复通知失败: %s", e)

    node = _comment_node(comment, user, set())
    if data.reply_to_user_id:
        target = (
            await db.execute(select(User).where(User.id == data.reply_to_user_id))
        ).scalar_one_or_none()
        if target is not None:
            node["replyToName"] = target.nickname or target.username
    return _ok(node)


@router.post("/comments/{comment_id}/like")
async def toggle_comment_like(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """评论点赞切换（顶层评论与回复通用，幂等）。"""
    comment = (
        await db.execute(select(ForumComment).where(ForumComment.id == comment_id))
    ).scalar_one_or_none()
    if comment is None or comment.status != COMMENT_NORMAL:
        raise HTTPException(status_code=404, detail="评论不存在")
    # 评论本身可见还不够：它可能挂在未公开文章下，同样要按文章可见性拦住
    article = await _get_article(db, comment.article_id)
    if article is None or not _can_view_article(article, user):
        raise HTTPException(status_code=404, detail="评论不存在")

    delta = await _toggle_relation(
        db,
        "forum_comment_likes",
        {"comment_id": comment_id, "user_id": user.id, "create_time": _now_iso()},
        {"comment_id": comment_id, "user_id": user.id},
    )
    if delta:
        await db.execute(
            update(ForumComment)
            .where(ForumComment.id == comment_id)
            .values(like_count=ForumComment.like_count + delta)
        )
    await db.commit()
    new_count = (
        await db.execute(select(ForumComment).where(ForumComment.id == comment_id))
    ).scalar_one()

    # 站内信：新增点赞（delta=+1）且非作者自赞时，定向通知评论作者（PRD v1.1 §7.3）。
    # 回复类评论的内容快照带「回复 @{被回复者昵称}：」前缀，与前端评论区展示口径一致。
    if delta == 1 and comment.author_id and comment.author_id != user.id:
        try:
            from .messages import create_like_message

            reply_to_nickname = ""
            if comment.parent_id and comment.reply_to_user_id:
                target = await _get_users(db, {comment.reply_to_user_id})
                target_user = target.get(comment.reply_to_user_id)
                if target_user is not None:
                    reply_to_nickname = target_user.nickname or target_user.username
            await create_like_message(
                db,
                article_id=comment.article_id,
                comment_id=comment_id,
                liker_id=user.id,
                author_id=comment.author_id,
                comment_content=comment.content,
                reply_to_nickname=reply_to_nickname,
            )
        except Exception as e:
            logger.warning("发送点赞通知失败: %s", e)

    return _ok({"liked": delta == 1, "likeCount": max(new_count.like_count, 0)})


@router.delete("/comments/{comment_id}")
async def delete_own_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """作者删除**自己**的评论/回复 → **物理删除，不留任何痕迹**。

    与后台 `DELETE /admin/comments/{id}`（软删 status=2 + "已删除"标记）**有意不对称**
    （回收站 PRD §0.4-J / §6-D7）：后台删评论要留治理痕迹供纠纷/举报追溯，
    作者删自己的话则真的拿走——不写占位节点、不建审计表、不保留 status=2 行。
    **不要"顺手统一"成一种**，这条不对称必须写在这里和 AGENTS.md 里。

    连带与计数（§2.2，与第一阶段 §8-D15 ④ 同口径，只把"软删"换成"物理删"）：
    - 删顶层评论 → 其下**全部回复**（**含他人回复**，代价由确认弹窗文案告知，§0.4-H）
      及上述所有评论的 forum_comment_likes 行一并物理删除，comment_count 原子减
      `1 + 回复数`；
    - 删单条回复 → 只删该行与其点赞行，原子减 1；
    - 只数 status=1 的行：已被后台软删的回复早已扣过 comment_count，不重复扣。

    权限（§2.3）：**仅该评论的作者本人**——楼主不能删自己帖子下别人的评论
    （本阶段不引入版主/楼主治理权），删他人内容一律走管理员后台。
    越权 / 不存在 / 已被后台软删 → 一律 **404**（不泄露存在性）。
    禁言用户**可删**（§0.4-K：删除不是"发言"）。
    """
    comment = (
        await db.execute(select(ForumComment).where(ForumComment.id == comment_id))
    ).scalar_one_or_none()
    # 归属校验失败、目标不存在、目标已被后台软删 → 一律 404，不区分提示
    if comment is None or comment.author_id != user.id or comment.status != COMMENT_NORMAL:
        raise HTTPException(status_code=404, detail="评论不存在或已被删除")
    article = await _get_article(db, comment.article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="评论不存在或已被删除")

    if comment.parent_id == 0:
        child_ids = list(
            (
                await db.execute(
                    select(ForumComment.id).where(
                        ForumComment.parent_id == comment_id,
                        ForumComment.status == COMMENT_NORMAL,
                    )
                )
            )
            .scalars()
            .all()
        )
        if child_ids:
            await db.execute(
                delete(ForumCommentLike).where(ForumCommentLike.comment_id.in_(child_ids))
            )
            await db.execute(delete(ForumComment).where(ForumComment.id.in_(child_ids)))
        await _bump_comment_count(db, comment.article_id, -(1 + len(child_ids)))
        deleted_count = 1 + len(child_ids)
    else:
        await _bump_comment_count(db, comment.article_id, -1)
        deleted_count = 1

    await db.execute(
        delete(ForumCommentLike).where(ForumCommentLike.comment_id == comment_id)
    )
    await db.execute(delete(ForumComment).where(ForumComment.id == comment_id))
    await db.commit()

    # commentCount 由前端拿本响应值**直接回写**（比本地 -delta 抗漂移，§3.4）
    new_count = (
        await db.execute(
            select(ForumArticle.comment_count).where(ForumArticle.id == comment.article_id)
        )
    ).scalar_one()
    return _ok(
        {"id": comment_id, "deletedCount": deleted_count, "commentCount": max(new_count, 0)},
        "已删除",
    )


@router.post("/upload/image")
async def upload_forum_image(
    file: UploadFile = File(...),
    _user: User = Depends(get_current_user),
):
    """登录用户上传图片（封面 / 正文内嵌图共用）。

    落盘 uploads/forum/YYYYMM/，对外 URL 仍是 /api/announcement/uploads/forum/...——
    复用 main.py 已有的同一个 StaticFiles 挂载点，因此**零 nginx 改动**（PRD §8-D1）。
    """
    _ensure_not_muted(_user)
    url = await save_image(file, sub_prefix="forum")
    return _ok({"url": url})


# ══════════════════════════════════════════════════════════════════
# 管理员接口
# ══════════════════════════════════════════════════════════════════
@router.get("/admin/articles")
async def admin_list_articles(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keyword: Optional[str] = Query(default=None, description="标题模糊搜索"),
    author: Optional[str] = Query(default=None, description="昵称 / 账号模糊搜索"),
    categoryId: Optional[int] = Query(default=None),
    tagId: Optional[int] = Query(default=None),
    status: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员文章检索分页（默认按 create_time 倒序，含全部状态）。"""
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size
    stmt = select(ForumArticle)
    count_stmt = select(func.count()).select_from(ForumArticle)

    kw = (keyword or "").strip()
    if kw:
        like = f"%{_like_escape(kw)}%"
        stmt = stmt.where(ForumArticle.title.like(like, escape="\\"))
        count_stmt = count_stmt.where(ForumArticle.title.like(like, escape="\\"))
    au = (author or "").strip()
    if au:
        like = f"%{_like_escape(au)}%"
        sub = select(ForumArticle.author_id).where(
            or_(
                User.nickname.like(like, escape="\\"),
                User.username.like(like, escape="\\"),
            )
        )
        stmt = stmt.where(ForumArticle.author_id.in_(sub))
        count_stmt = count_stmt.where(ForumArticle.author_id.in_(sub))
    if categoryId is not None:
        stmt = stmt.where(ForumArticle.category_id == categoryId)
        count_stmt = count_stmt.where(ForumArticle.category_id == categoryId)
    if tagId is not None:
        sub = select(ForumArticleTag.article_id).where(ForumArticleTag.tag_id == tagId)
        stmt = stmt.where(ForumArticle.id.in_(sub))
        count_stmt = count_stmt.where(ForumArticle.id.in_(sub))
    if status is not None:
        stmt = stmt.where(ForumArticle.status == status)
        count_stmt = count_stmt.where(ForumArticle.status == status)

    stmt = stmt.order_by(ForumArticle.create_time.desc(), ForumArticle.id.desc()).offset(offset).limit(page_size)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt)).scalars().all()
    return _ok(_page_payload(await _article_items(db, list(rows), _admin), page, page_size, total))


@router.get("/admin/articles/{article_id}")
async def admin_get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """后台查看文章全量（正文源码 + 标签名 + 驳回理由），用于编辑抽屉与预览。"""
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    item = await _article_item(db, article, _admin)
    item["content"] = article.content
    item["contentType"] = article.content_type
    item["reviewNote"] = article.review_note
    tags = (await _get_tags_of_articles(db, [article.id])).get(article.id, [])
    item["tagNames"] = [t.name for t in tags]
    return _ok(item)


@router.put("/admin/articles/{article_id}/review")
async def admin_review(
    article_id: int,
    data: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """审核：1=通过（重写 publish_time + 标签 use_count 各 +1）/ 2=驳回（理由必填）。"""
    if data.status not in (STATUS_PUBLISHED, STATUS_REJECTED):
        raise HTTPException(status_code=400, detail="status 仅支持 1（通过）或 2（驳回）")
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status != STATUS_PENDING:
        raise HTTPException(status_code=400, detail="仅待审核文章可通过或驳回")

    if data.status == STATUS_REJECTED:
        note = (data.review_note or "").strip()
        if not note:
            raise HTTPException(status_code=400, detail="驳回必须填写理由")
        if len(note) > REVIEW_NOTE_MAX:
            raise HTTPException(status_code=400, detail=f"驳回理由不能超过 {REVIEW_NOTE_MAX} 个字符")
        article.review_note = note
    else:
        article.review_note = ""

    await _set_article_status(db, article, data.status)
    article.update_time = _now_iso()
    await db.commit()

    # 站内信：文章审核结果通知作者
    try:
        from .messages import create_article_review_message
        await create_article_review_message(
            db,
            article_id=article.id,
            author_id=article.author_id,
            status=data.status,
            review_note=article.review_note,
        )
    except Exception as e:
        logger.warning("写入文章审核通知失败: %s", e)

    return _ok(await _article_item(db, article, _admin), "审核完成")


async def _toggle_flag(db: AsyncSession, article_id: int, field: str) -> dict:
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == STATUS_RECYCLED:
        # 回收站帖对全站不可见，置顶/加精它没有任何展示意义（PRD §4）
        raise HTTPException(status_code=400, detail="回收站的文章不可置顶或加精")
    setattr(article, field, 0 if getattr(article, field) else 1)
    article.update_time = _now_iso()
    await db.commit()
    return await _article_item(db, article)


@router.post("/admin/articles/{article_id}/top")
async def admin_toggle_top(
    article_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """置顶切换（幂等）。"""
    return _ok(await _toggle_flag(db, article_id, "is_top"))


@router.post("/admin/articles/{article_id}/feature")
async def admin_toggle_feature(
    article_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """加精切换（幂等）。"""
    return _ok(await _toggle_flag(db, article_id, "is_featured"))


@router.post("/admin/articles/{article_id}/offline")
async def admin_offline(
    article_id: int,
    data: OfflineRequest = OfflineRequest(),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """下架：status=3 且 remove_by='admin'（下架后作者不能编辑重提）。原因会展示给作者。

    回收站帖（status=4）**不可下架**——它对全站已经不可见，再打一层 remove_by='admin'
    只会把"作者自删"和"管理员下架"混进同一个状态里，正是新增 status=4 要消除的歧义。
    要处理回收站帖请走「恢复」或「删除」。
    """
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == STATUS_RECYCLED:
        raise HTTPException(status_code=400, detail="回收站的文章不可下架，请先恢复或删除")
    if article.status in (STATUS_OFFLINE, STATUS_PENDING):
        raise HTTPException(status_code=400, detail="仅已发布或已驳回的文章可下架")
    article.review_note = (data.reason or "").strip()
    await _set_article_status(db, article, STATUS_OFFLINE)
    article.remove_by = REMOVE_BY_ADMIN
    article.update_time = _now_iso()
    await db.commit()
    return _ok(await _article_item(db, article, _admin), "已下架")


@router.post("/admin/articles/{article_id}/restore")
async def admin_restore(
    article_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """恢复上架。**两种来源，同一条路由**（回收站 PRD §4 / §0.4-E）：

    - `status=3`（管理员下架）：行为与第一阶段**完全不变**——回 1 已发布、
      remove_by=''、publish_time 重写为当前时间、不重审；
    - `status=4`（作者自删进回收站）：回到 **status_before_delete**（不重审），
      回到已发布时回填删除前的 publish_time（防刷榜），并清空回收站三列；
    - 其它状态 → 400。

    管理员硬删仍是不可恢复的（DELETE /admin/articles/{id}），这条只做恢复。
    """
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == STATUS_RECYCLED:
        target = article.status_before_delete
        if target not in RESTORE_TARGETS:
            target = STATUS_PENDING  # 数据异常兜底成最保守的待审核
        await _set_article_status(
            db,
            article,
            target,
            publish_time_override=article.publish_time_before_delete or None,
        )
        article.deleted_at = ""
        article.status_before_delete = 0
        article.publish_time_before_delete = ""
        article.remove_by = ""
        article.update_time = _now_iso()
        await db.commit()
        return _ok(await _article_item(db, article, _admin), "已从回收站恢复")
    if article.status != STATUS_OFFLINE:
        raise HTTPException(status_code=400, detail="仅已下架或回收站的文章可恢复")
    article.review_note = ""
    await _set_article_status(db, article, STATUS_PUBLISHED)
    article.remove_by = ""
    article.update_time = _now_iso()
    await db.commit()
    return _ok(await _article_item(db, article, _admin), "已恢复上架")


@router.put("/admin/articles/{article_id}")
async def admin_update_article(
    article_id: int,
    data: AdminArticleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """后台改属性（板块 / 标签 / 封面 / 标题）。**状态不变**，不重新审核（PRD §8-D14）。

    正文**只读**：后台不提供改正文能力，需要改内容由作者自行编辑重提（PRD §8-D9），
    这样改动照样过审，责任链与留痕都清晰。
    **回收站帖（status=4）不可改属性**：它已对全站不可见，改板块/标题只会让回收站
    列表展示出与原文不一致的信息，要处理请先「恢复」或「删除」。
    """
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.status == STATUS_RECYCLED:
        raise HTTPException(status_code=400, detail="回收站的文章不可修改属性，请先恢复或删除")

    if data.category_id is not None:
        cat = await _get_category_by_id(db, data.category_id)
        if cat is None:
            raise HTTPException(status_code=400, detail="板块不存在")
        if cat.is_system:
            raise HTTPException(status_code=400, detail="不能把文章归到系统板块")
        article.category_id = cat.id
    if data.title is not None:
        title = data.title.strip()
        if not (TITLE_MIN <= len(title) <= TITLE_MAX):
            raise HTTPException(status_code=400, detail=f"标题需为 {TITLE_MIN}-{TITLE_MAX} 个字符")
        article.title = title
    if data.cover_url is not None:
        article.cover_url = data.cover_url.strip()
    if data.tags is not None:
        await _sync_article_tags(db, article, data.tags)
    article.update_time = _now_iso()
    await db.commit()
    return _ok(await _article_item(db, article, _admin), "已保存")


@router.delete("/admin/articles/{article_id}")
async def admin_delete_article(
    article_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """硬删除（不可恢复）：级联清理评论、评论点赞、文章点赞、收藏、标签关联。

    级联实现是 forum_core.cascade_delete_article（与"作者回收站彻底删除"、
    "forum_purge.py 超期清理"共用同一份，语义唯一）。
    """
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    await cascade_delete_article(db, article)
    await db.commit()
    return _ok({"id": article_id}, "已删除")


@router.get("/admin/articles/{article_id}/comments")
async def admin_list_comments(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """后台评论抽屉：列出该文章**全部**评论与回复（含已删除标记），回复缩进展示。"""
    article = await _get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    r = await db.execute(
        select(ForumComment)
        .where(ForumComment.article_id == article_id)
        .order_by(ForumComment.parent_id.asc(), ForumComment.create_time.asc(), ForumComment.id.asc())
    )
    rows = list(r.scalars().all())
    user_map = await _get_users(
        db, {c.author_id for c in rows} | {c.reply_to_user_id or 0 for c in rows}
    )

    def node(c: ForumComment, with_replies: bool) -> dict:
        d = _comment_node(
            c,
            user_map.get(c.author_id),
            set(),
            reply_to_name=(
                user_map[c.reply_to_user_id].nickname or user_map[c.reply_to_user_id].username
                if c.reply_to_user_id and c.reply_to_user_id in user_map
                else None
            ),
        )
        if with_replies:
            d["replies"] = []
        return d

    tops = [c for c in rows if c.parent_id == 0]
    replies_by_parent: dict[int, list[ForumComment]] = {}
    for c in rows:
        if c.parent_id:
            replies_by_parent.setdefault(c.parent_id, []).append(c)
    items = []
    for c in tops:
        d = node(c, True)
        d["replies"] = [node(rc, False) for rc in replies_by_parent.get(c.id, [])]
        items.append(d)
    return _ok(items)


@router.delete("/admin/comments/{comment_id}")
async def admin_delete_comment(
    comment_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """删除评论（软删 status=2）。

    - 删顶层评论 → 其下所有回复**一并软删**，comment_count 减 `1 + 回复数`；
    - 删单条回复 → 只减 1；
    - 两种情况都同步清理 forum_comment_likes，不留孤儿数据（PRD §8-D15 ④）。
    """
    comment = (
        await db.execute(select(ForumComment).where(ForumComment.id == comment_id))
    ).scalar_one_or_none()
    if comment is None:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.status == COMMENT_DELETED:
        raise HTTPException(status_code=400, detail="该评论已删除")

    now = _now_iso()
    if comment.parent_id == 0:
        children = list(
            (
                await db.execute(
                    select(ForumComment).where(
                        ForumComment.parent_id == comment_id, ForumComment.status == COMMENT_NORMAL
                    )
                )
            )
            .scalars()
            .all()
        )
        child_ids = [c.id for c in children]
        if child_ids:
            await db.execute(
                update(ForumComment)
                .where(ForumComment.id.in_(child_ids))
                .values(status=COMMENT_DELETED, like_count=0)
            )
            await db.execute(
                delete(ForumCommentLike).where(ForumCommentLike.comment_id.in_(child_ids))
            )
        await _bump_comment_count(db, comment.article_id, -(1 + len(children)))
        reply_count = len(children)
    else:
        await _bump_comment_count(db, comment.article_id, -1)
        reply_count = 0

    comment.status = COMMENT_DELETED
    comment.like_count = 0  # 点赞行已一并清空，计数归零以免后台抽屉显示过期数字
    await db.execute(
        delete(ForumCommentLike).where(ForumCommentLike.comment_id == comment_id)
    )
    await db.commit()
    return _ok({"id": comment_id, "replyCount": reply_count}, "已删除")


# ── 板块管理 ──────────────────────────────────────────────────────
def _category_payload(c: ForumCategory, article_count: int = 0) -> dict:
    d = _category_brief(c)
    d["articleCount"] = article_count
    d["createTime"] = c.create_time
    d["updateTime"] = c.update_time
    return d


async def _article_counts_by_category(db: AsyncSession) -> dict[int, int]:
    """各板块的**全部状态**文章数（后台"有文章不可删"的判定依据）。

    必须与删除守卫同口径（都数全部状态）：后台按钮的可点性由这个数字决定，
    若它只数已发布而守卫数全部，会出现"按钮能点、点了报 400"的不一致。
    """
    r = await db.execute(
        select(ForumCategory.id, func.count(ForumArticle.id))
        .select_from(ForumCategory)
        .outerjoin(ForumArticle, ForumArticle.category_id == ForumCategory.id)
        .group_by(ForumCategory.id)
    )
    return {cid: cnt for cid, cnt in r.all()}


@router.get("/admin/categories")
async def admin_list_categories(
    db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """板块全量（含隐藏），带已发布文章数。"""
    r = await db.execute(select(ForumCategory).order_by(ForumCategory.sort_order.asc(), ForumCategory.id.asc()))
    cats = r.scalars().all()
    counts = await _article_counts_by_category(db)
    return _ok([_category_payload(c, counts.get(c.id, 0)) for c in cats])


@router.post("/admin/categories")
async def admin_create_category(
    data: CategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """新增板块（code 唯一且创建后不可改）。"""
    name = (data.name or "").strip()
    code = (data.code or "").strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="请填写板块名称")
    if not _CODE_RE.fullmatch(code):
        raise HTTPException(status_code=400, detail="code 需为 2-31 位小写字母/数字/下划线/短横线，且以字母开头")
    color = (data.color or "").strip()
    if not _COLOR_RE.fullmatch(color):
        raise HTTPException(status_code=400, detail="颜色需为 #RRGGBB 格式")
    if await _get_category_by_code(db, code) is not None:
        raise HTTPException(status_code=400, detail="该 code 已被占用")
    dup = (
        await db.execute(select(ForumCategory).where(ForumCategory.name == name))
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=400, detail="该板块名称已存在")

    now = _now_iso()
    cat = ForumCategory(
        code=code,
        name=name,
        color=color,
        sort_order=data.sort_order,
        is_system=0,
        is_hidden=0,
        create_time=now,
        update_time=now,
    )
    db.add(cat)
    await db.commit()
    return _ok(_category_payload(cat), "已新增板块")


@router.put("/admin/categories/{category_id}")
async def admin_update_category(
    category_id: int,
    data: CategoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """编辑板块：系统板块只可改名称之外的视觉项（PRD §0.4：名称/code 不可改、不可删）。"""
    cat = await _get_category_by_id(db, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="板块不存在")

    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="板块名称不能为空")
        if cat.is_system:
            raise HTTPException(status_code=400, detail="系统板块不可改名")
        dup = (
            await db.execute(
                select(ForumCategory).where(
                    ForumCategory.name == name, ForumCategory.id != category_id
                )
            )
        ).scalar_one_or_none()
        if dup is not None:
            raise HTTPException(status_code=400, detail="该板块名称已存在")
        cat.name = name
    if data.color is not None:
        color = data.color.strip()
        if not _COLOR_RE.fullmatch(color):
            raise HTTPException(status_code=400, detail="颜色需为 #RRGGBB 格式")
        cat.color = color
    if data.sort_order is not None:
        cat.sort_order = data.sort_order
    if data.is_hidden is not None:
        if cat.is_system:
            raise HTTPException(status_code=400, detail="系统板块不可隐藏")
        cat.is_hidden = 1 if data.is_hidden else 0
    cat.update_time = _now_iso()
    await db.commit()
    return _ok(_category_payload(cat), "已保存")


@router.delete("/admin/categories/{category_id}")
async def admin_delete_category(
    category_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """删除板块：**仅当该板块下无已发布文章时允许**（不提供级联删除，防误删）。"""
    cat = await _get_category_by_id(db, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="板块不存在")
    if cat.is_system:
        raise HTTPException(status_code=400, detail="系统板块不可删除")
    # 必须数**全部状态**的文章：若只数已发布的，板块下残留"待审核/已驳回/已下架"
    # 的帖子时板块会被删掉，那些文章的 category_id 变成悬空外键，接口回
    # "category": null，前端 MyPosts.vue 直接读 a.category.name 会白屏——
    # 作者连编辑入口都点不进去。PRD §6.2.1 的原文是"无文章"，不是"无已发布文章"。
    n = (
        await db.execute(
            select(func.count())
            .select_from(ForumArticle)
            .where(ForumArticle.category_id == category_id)
        )
    ).scalar_one()
    if n:
        raise HTTPException(status_code=400, detail=f"请先迁移或删除该板块下的 {n} 篇文章")
    await db.delete(cat)
    await db.commit()
    return _ok({"id": category_id}, "已删除板块")


# ── 标签管理 ──────────────────────────────────────────────────────
def _tag_payload(t: ForumTag) -> dict:
    """后台标签项。必须带 isHot（PRD §7.4 明列）——漏了会让后台「是否置热」列
    永远空着、「置热/取消置热」按钮文案也永远显示错。"""
    d = _tag_brief(t)
    d["isHot"] = t.is_hot
    d["source"] = t.source
    d["createTime"] = t.create_time
    return d


@router.get("/admin/tags")
async def admin_list_tags(
    source: Optional[str] = Query(default=None, description="user=只看待清理的用户标签"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """标签全量（可按 source 筛选；默认把 user 来源排在前面作为清理入口）。"""
    stmt = select(ForumTag)
    if source:
        stmt = stmt.where(ForumTag.source == source)
    stmt = stmt.order_by(ForumTag.is_hot.desc(), ForumTag.use_count.desc(), ForumTag.id.desc())
    return _ok([_tag_payload(t) for t in (await db.execute(stmt)).scalars().all()])


@router.post("/admin/tags")
async def admin_create_tag(
    data: TagCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """后台手工建标签（source='system'）。"""
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写标签名")
    # 与发帖时新建标签（_sync_article_tags）用同一个上限，别出现"发帖能填 20 字、
    # 后台能建 40 字"的口径分叉
    if len(name) > MAX_TAG_NAME_LEN:
        raise HTTPException(
            status_code=400, detail=f"单个标签不能超过 {MAX_TAG_NAME_LEN} 字"
        )
    dup = (await db.execute(select(ForumTag).where(ForumTag.name == name))).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=400, detail="该标签已存在")
    tag = ForumTag(
        name=name, use_count=0, is_hot=0, source="system", create_time=_now_iso()
    )
    db.add(tag)
    await db.commit()
    return _ok(_tag_payload(tag), "已新增标签")


@router.put("/admin/tags/{tag_id}")
async def admin_update_tag(
    tag_id: int,
    data: TagUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """重命名 / 置热。重命名不影响 use_count（引用的是 tag_id 不是名字）。"""
    tag = (await db.execute(select(ForumTag).where(ForumTag.id == tag_id))).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="标签名不能为空")
        if len(name) > MAX_TAG_NAME_LEN:
            raise HTTPException(
                status_code=400, detail=f"单个标签不能超过 {MAX_TAG_NAME_LEN} 字"
            )
        dup = (
            await db.execute(
                select(ForumTag).where(ForumTag.name == name, ForumTag.id != tag_id)
            )
        ).scalar_one_or_none()
        if dup is not None:
            raise HTTPException(status_code=400, detail="该标签已存在")
        tag.name = name
    if data.is_hot is not None:
        tag.is_hot = 1 if data.is_hot else 0
    await db.commit()
    return _ok(_tag_payload(tag), "已保存")


@router.post("/admin/tags/{tag_id}/merge")
async def admin_merge_tag(
    tag_id: int,
    data: TagMergeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """合并标签：把源标签的全部引用迁到目标标签，删除源标签，重算目标 use_count。

    若某篇文章已同时挂了两个标签，则只删掉源关联（不产生重复行，联合唯一索引保证）。
    """
    src = (await db.execute(select(ForumTag).where(ForumTag.id == tag_id))).scalar_one_or_none()
    if src is None:
        raise HTTPException(status_code=404, detail="源标签不存在")
    if src.id == data.target_tag_id:
        raise HTTPException(status_code=400, detail="不能合并到自身")
    target = (
        await db.execute(select(ForumTag).where(ForumTag.id == data.target_tag_id))
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="目标标签不存在")

    rows = list(
        (
            await db.execute(
                select(ForumArticleTag).where(ForumArticleTag.tag_id == src.id)
            )
        )
        .scalars()
        .all()
    )
    affected: set[int] = set()
    for row in rows:
        exists = (
            await db.execute(
                select(ForumArticleTag.id).where(
                    ForumArticleTag.article_id == row.article_id,
                    ForumArticleTag.tag_id == target.id,
                )
            )
        ).scalar_one_or_none()
        if exists is not None:
            await db.delete(row)
        else:
            row.tag_id = target.id
        affected.add(row.article_id)
    await db.flush()
    await _recalc_tag_use_count(db, [target.id])
    if affected:
        await db.execute(
            update(ForumArticle)
            .where(ForumArticle.id.in_(list(affected)))
            .values(update_time=_now_iso())
        )
    await db.delete(src)
    await db.commit()
    return _ok({"target": _tag_payload(target), "articleCount": len(affected)}, "合并完成")


@router.delete("/admin/tags/{tag_id}")
async def admin_delete_tag(
    tag_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """删除标签：从文章关联中移除该标签，并回写受影响文章的 update_time。"""
    tag = (await db.execute(select(ForumTag).where(ForumTag.id == tag_id))).scalar_one_or_none()
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    rows = list(
        (
            await db.execute(
                select(ForumArticleTag).where(ForumArticleTag.tag_id == tag_id)
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        await db.delete(row)
    if rows:
        await db.execute(
            update(ForumArticle)
            .where(ForumArticle.id.in_([r.article_id for r in rows]))
            .values(update_time=_now_iso())
        )
    await db.delete(tag)
    await db.commit()
    return _ok({"id": tag_id, "articleCount": len(rows)}, "已删除标签")


# ── 社区配置 ──────────────────────────────────────────────────────
@router.get("/admin/config")
async def admin_get_config(
    db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """后台读取全部配置键（含打赏预留键，第一阶段只读展示）。"""
    await ensure_seeded()
    r = await db.execute(select(ForumConfig))
    values = {row.key: row.value for row in r.scalars().all()}
    return _ok({k: values.get(k, v) for k, v in FORUM_CONFIG_DEFAULTS.items()})


@router.put("/admin/config")
async def admin_update_config(
    data: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """保存配置（白名单内键；传 null 的键保持不变）。保存后首页即时生效（后端不缓存）。"""
    await ensure_seeded()
    if data.defaultSort is not None and data.defaultSort not in SORT_OPTIONS:
        raise HTTPException(status_code=400, detail="排序默认项仅支持 latest / views / comments")
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="没有需要保存的配置项")
    for key, value in payload.items():
        if key not in FORUM_CONFIG_DEFAULTS:
            continue
        row = (
            await db.execute(select(ForumConfig).where(ForumConfig.key == key))
        ).scalar_one_or_none()
        if row is None:
            db.add(ForumConfig(key=key, value=value))
        else:
            row.value = value
    await db.commit()
    return _ok(data, "已保存")


@router.get("/admin/covers")
async def admin_list_covers(
    _admin: User = Depends(require_admin),
):
    """封面图库：列出 uploads/forum/ 下的图片（只读；冗余文件清理归第三阶段）。"""
    root = Path(UPLOAD_DIR) / "forum"
    items: list[dict] = []
    if root.is_dir():
        for f in sorted(root.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                continue
            rel = f.relative_to(Path(UPLOAD_DIR)).as_posix()
            st = f.stat()
            items.append(
                {
                    "name": f.name,
                    "url": f"/api/announcement/uploads/{rel}",
                    "size": st.st_size,
                    "mtime": datetime.fromtimestamp(st.st_mtime, _TZ).strftime("%Y-%m-%dT%H:%M:%S"),
                }
            )
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return _ok(items)


# ── 用户论坛数据 ──────────────────────────────────────────────────
@router.get("/admin/user-stats/{user_id}")
async def admin_user_stats(
    user_id: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    """用户论坛数据：发帖数（已发布）/ 获赞数（其文章 like_count 之和）/ 粉丝数（恒 0）+ 最近 5 篇。"""
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = await _user_forum_stats(db, target)
    recent = (
        await db.execute(
            select(ForumArticle)
            .where(ForumArticle.author_id == user_id)
            .order_by(ForumArticle.update_time.desc(), ForumArticle.id.desc())
            .limit(5)
        )
    ).scalars().all()
    data["recentPosts"] = [
        {
            "id": a.id,
            "title": a.title,
            "status": a.status,
            "statusText": ARTICLE_STATUS_TEXT.get(a.status, ""),
            "updateTime": a.update_time,
        }
        for a in recent
    ]
    return _ok(data)


# ══════════════════════════════════════════════════════════════════
# 首次启动种子数据
# ══════════════════════════════════════════════════════════════════
_seeded = False


async def ensure_seeded() -> None:
    """写入预置板块与配置默认值（幂等：已存在则跳过；进程内只跑一次）。

    板块用 code 判存、配置用 key 判存，因此管理员改过的值不会被种子覆盖。
    """
    global _seeded
    if _seeded:
        return
    _seeded = True
    try:
        from .database import async_session_maker

        async with async_session_maker() as session:
            now = _now_iso()
            for code, name, color, order, is_system in SEED_CATEGORIES:
                exists = await _get_category_by_code(session, code)
                if exists is None:
                    session.add(
                        ForumCategory(
                            code=code,
                            name=name,
                            color=color,
                            sort_order=order,
                            is_system=is_system,
                            is_hidden=0,
                            create_time=now,
                            update_time=now,
                        )
                    )
            r = await session.execute(select(ForumConfig))
            existing_keys = {row.key for row in r.scalars().all()}
            for key, value in FORUM_CONFIG_DEFAULTS.items():
                if key not in existing_keys:
                    session.add(ForumConfig(key=key, value=value))
            await session.commit()
    except Exception:  # 种子失败不阻断启动：板块/配置可由后台手工补齐
        import logging

        logging.getLogger("uvicorn.error").warning("论坛种子数据写入失败", exc_info=True)
        _seeded = False
