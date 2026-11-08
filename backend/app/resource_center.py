"""资源中心模块（一阶段 MVP）：/resources/*（main.py 统一挂 /api → /api/resources/*）
与下载跳转端点 /download/asset/{assetId}（不挂 /api，nginx 另行反代）。

实施唯一依据：docs/资源中心/资源中心一阶段MVP需求.md（一阶段 MVP）。

口径红线（改代码前先读）：
- 资源与版本信息由后台**手动维护**，不做 GitHub 自动同步 / 文件代理 / hash 校验 /
  下载量同步 / 用户系统（需求 §0 与 §1.3 的「明确不做」）；
- 计数口径是「下载跳转次数」：本站记录的是下载按钮跳转点击次数，**不得称为下载量**；
- 前台不得直接暴露 GitHub URL，下载一律经 /download/asset/{assetId} 302 跳转；
- 端点不接受任何 URL 参数，跳转目标只取数据库 asset.url（防开放重定向）；
- 资产 URL 必须是 https://github.com/ 开头的 Release 资产链接（写入时校验）；
- 冗余计数 resource.download_count 的唯一维护口径：download_events 落库同事务内
  原子 UPDATE +1（与论坛 like_count 同思路）。展示/列表/排序直接读冗余列，
  避免列表页逐资源 COUNT（N+1）；后台统计条目按 events 实时聚合，可对账。

接口一览：

  ── 公开（匿名） ──
  GET  /resources                      资源列表（q/type/platform/game_version/side/channel/tag/sort/page/pageSize）
  GET  /resources/filters              筛选项字典（enabled 项，按 type 分组）
  GET  /resources/{slug}               资源详情（含版本列表 + 每版本可见资产 + 跳转统计）

  ── 管理员（require_admin） ──
  GET    /resources/admin/page          资源管理分页（keyword/status，含未发布与已软删）
  GET    /resources/admin/{id}          资源编辑回填（全字段 + 关联 key 数组）
  POST   /resources/admin               新建资源
  PUT    /resources/admin/{id}          编辑资源（slug 唯一性校验；同步三张关联表）
  POST   /resources/admin/{id}/status   状态切换（publish/hide/archive/draft）
  DELETE /resources/admin/{id}          软删除（deleted_at；前台立即可见性消失）
  GET    /resources/admin/{id}/versions          版本列表（含隐藏，含资产统计）
  POST   /resources/admin/{id}/versions          新建版本（同资源版本号唯一）
  PUT    /resources/admin/versions/{vid}         编辑版本（渠道/兼容/日志/状态/最新稳定版）
  DELETE /resources/admin/versions/{vid}         软删除版本
  GET    /resources/admin/versions/{vid}/assets  资产列表（含隐藏）
  POST   /resources/admin/versions/{vid}/assets  新建资产（URL 白名单校验）
  PUT    /resources/admin/assets/{aid}           编辑资产
  DELETE /resources/admin/assets/{aid}           软删除资产
  GET    /resources/admin/stats                  跳转统计（总览 + 按资源/版本/资产，时间范围可选）

所有接口遵循项目统一响应包络 {code, message, data}（code=0 成功）；
下载端点 302/404/410/429 为跳转语义，不走包络。
业务失败以 HTTPException(400/401/403/404, detail=...) 抛出。
"""
import hashlib
import json
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import require_admin
from .database import (
    DictItem,
    DownloadEvent,
    Resource,
    ResourceGameVersion,
    ResourcePlatform,
    ResourceTag,
    ResourceVersion,
    VersionAsset,
    get_db,
)
from .pydantic_models import (
    ResourceCreateRequest,
    ResourceUpdateRequest,
    ResourceStatusRequest,
    VersionCreateRequest,
    VersionUpdateRequest,
    AssetCreateRequest,
    AssetUpdateRequest,
    DictCreateRequest,
    DictUpdateRequest,
)

router = APIRouter(prefix="/resources", tags=["resources"])
download_router = APIRouter(tags=["download"])

_TZ = ZoneInfo("Asia/Shanghai")

# ── 常量（后端为唯一权威，前端选项需与此保持一致） ─────────────────
RESOURCE_STATUS_DRAFT = "draft"
RESOURCE_STATUS_PUBLISHED = "published"
RESOURCE_STATUS_HIDDEN = "hidden"
RESOURCE_STATUS_ARCHIVED = "archived"
RESOURCE_STATUSES = (
    RESOURCE_STATUS_DRAFT,
    RESOURCE_STATUS_PUBLISHED,
    RESOURCE_STATUS_HIDDEN,
    RESOURCE_STATUS_ARCHIVED,
)

VERSION_STATUS_VISIBLE = "visible"
VERSION_STATUS_HIDDEN = "hidden"
VERSION_STATUS_ARCHIVED = "archived"
VERSION_STATUSES = (VERSION_STATUS_VISIBLE, VERSION_STATUS_HIDDEN, VERSION_STATUS_ARCHIVED)

ASSET_STATUS_VISIBLE = "visible"
ASSET_STATUS_HIDDEN = "hidden"
ASSET_STATUSES = (ASSET_STATUS_VISIBLE, ASSET_STATUS_HIDDEN)

SIDE_CLIENT = "client"
SIDE_SERVER = "server"
SIDE_BOTH = "both"
SIDES = (SIDE_CLIENT, SIDE_SERVER, SIDE_BOTH)

CHANNEL_STABLE = "stable"
CHANNEL_BETA = "beta"
CHANNEL_ALPHA = "alpha"
CHANNELS = (CHANNEL_STABLE, CHANNEL_BETA, CHANNEL_ALPHA)

PURPOSE_MAIN = "main"
PURPOSE_ADDITIONAL = "additional"
PURPOSES = (PURPOSE_MAIN, PURPOSE_ADDITIONAL)

# 字典类型（dict_items.type 允许的取值；筛选与后台下拉共用）
DICT_TYPE_RESOURCE = "resource_type"
DICT_TYPE_PLATFORM = "platform"
DICT_TYPE_GAME_VERSION = "game_version"
DICT_TYPE_SIDE = "side"
DICT_TYPE_CHANNEL = "release_channel"
DICT_TYPE_TAG = "tag"
DICT_TYPES = (
    DICT_TYPE_RESOURCE,
    DICT_TYPE_PLATFORM,
    DICT_TYPE_GAME_VERSION,
    DICT_TYPE_SIDE,
    DICT_TYPE_CHANNEL,
    DICT_TYPE_TAG,
)

# 前台排序档（需求 §6.1）
SORT_UPDATED_DESC = "updated_desc"
SORT_NAME_ASC = "name_asc"
SORT_DOWNLOADS_DESC = "downloads_desc"
SORT_OPTIONS = (SORT_UPDATED_DESC, SORT_NAME_ASC, SORT_DOWNLOADS_DESC)

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
GITHUB_URL_PREFIX = "https://github.com/"
VERSION_MAX = 200  # 单资源版本数上限（防误批量灌库；正常运营远达不到）
ASSET_MAX = 50  # 单版本资产数上限

# 计数口径固定文案（后台 tooltip / 前台说明共用语义；前端本地也有同文案）
DOWNLOAD_COUNT_NOTE = "本站记录的是下载按钮跳转点击次数，文件由 GitHub 托管，非 GitHub 实际下载量。"

# ── 下载端点限速（按 IP+资产，进程内滑动窗口；与 kb.py 同思路） ────
# 一阶段单 worker 部署（uvicorn 默认），进程内窗口够用；扩多 worker 需换共享存储
# （与 TODO.md「限流共享存储」遗留同一条，不单独新增 TODO）。
DOWNLOAD_RATE_PER_MIN = 30  # 每 IP 每分钟最多 30 次跳转
_download_minute: dict[str, deque] = defaultdict(deque)


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _client_ip(request: Request) -> str:
    """取 IP 顺序与 kb.py 完全一致：XFF 首段 → X-Real-IP → client.host。"""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


def _ip_hash(ip: str) -> str:
    """IP 哈希：sha256(ip + salt) 截 16 位（需求 §2「不存原始 IP」）。
    salt 取固定进程内值——一阶段只要求不可反推与同 IP 可去重，不要求防彩虹表。"""
    return hashlib.sha256(f"{ip}:xqly-resource-center".encode()).hexdigest()[:16]


def _check_download_rate(ip: str) -> None:
    """IP+ 分钟滑动窗口限速；检查与记录之间无 await，天然原子（kb.py 同思路）。"""
    now = time.monotonic()
    window = _download_minute[ip]
    cutoff = now - 60
    while window and window[0] <= cutoff:
        window.popleft()
    if len(window) >= DOWNLOAD_RATE_PER_MIN:
        raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")
    window.append(now)


def _like_escape(term: str) -> str:
    """LIKE 字面量转义（forum._like_escape 同款）。"""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ok(data=None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


def _page_payload(items: list, page: int, page_size: int, total: int) -> dict:
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


def _loads_json_array(raw: str) -> list:
    """版本表 JSON 数组列的容错解析（脏数据按空数组处理，不让详情页白屏）。"""
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def _validate_github_asset_url(url: str) -> str:
    """资产 URL 白名单：只接受 https://github.com/ 开头（需求 §2/§4.3）。

    统一在写入侧拦截（后台录入与 P1 辅助解析共用），读取侧零校验成本。
    """
    u = (url or "").strip()
    if not u.startswith(GITHUB_URL_PREFIX):
        raise HTTPException(
            status_code=400,
            detail="资产 URL 必须是 https://github.com/ 开头的 GitHub Release 资产链接",
        )
    if len(u) > 1024:
        raise HTTPException(status_code=400, detail="URL 过长（≤1024 字符）")
    return u


async def _validate_dict_keys(
    db: AsyncSession, dtype: str, keys: list[str]
) -> list[str]:
    """校验一组字典 key 属于指定 type 且 enabled（后台录入与前台筛选共用）。"""
    if not keys:
        return []
    uniq = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
    if not uniq:
        return []
    r = await db.execute(
        select(DictItem.key).where(
            DictItem.type == dtype,
            DictItem.key.in_(uniq),
            DictItem.enabled == 1,
        )
    )
    valid = {k for (k,) in r.all()}
    unknown = [k for k in uniq if k not in valid]
    if unknown:
        raise HTTPException(status_code=400, detail=f"未知或已停用的字典项：{', '.join(unknown)}")
    return uniq


# ════════════════════════ 序列化（snake_case → camelCase） ════════════════════════


def _resource_brief(row: Resource, extra: Optional[dict] = None) -> dict:
    """列表卡片字段（前台/后台通用；详情另有全量序列）。"""
    d = {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "resourceType": row.resource_type,
        "summary": row.summary,
        "iconUrl": row.icon_url or "",
        "coverUrl": row.cover_url or "",
        "side": row.side,
        "status": row.status,
        "featured": row.featured,
        "sortWeight": row.sort_weight,
        "downloadCount": row.download_count,
        "updateTime": row.update_time,
    }
    if extra:
        d.update(extra)
    return d


async def _resource_relation_keys(db: AsyncSession, resource_ids: list[int]) -> dict:
    """批量取关联 key（一次三查，杜绝列表 N+1）。"""
    platforms: dict[int, list] = defaultdict(list)
    game_versions: dict[int, list] = defaultdict(list)
    tags: dict[int, list] = defaultdict(list)
    if not resource_ids:
        return {"platforms": platforms, "gameVersions": game_versions, "tags": tags}
    r = await db.execute(
        select(ResourcePlatform.resource_id, ResourcePlatform.platform_key)
        .where(ResourcePlatform.resource_id.in_(resource_ids))
        .order_by(ResourcePlatform.id)
    )
    for rid, key in r.all():
        platforms[rid].append(key)
    r = await db.execute(
        select(ResourceGameVersion.resource_id, ResourceGameVersion.game_version_key)
        .where(ResourceGameVersion.resource_id.in_(resource_ids))
        .order_by(ResourceGameVersion.id)
    )
    for rid, key in r.all():
        game_versions[rid].append(key)
    r = await db.execute(
        select(ResourceTag.resource_id, ResourceTag.tag_key)
        .where(ResourceTag.resource_id.in_(resource_ids))
        .order_by(ResourceTag.id)
    )
    for rid, key in r.all():
        tags[rid].append(key)
    return {"platforms": platforms, "gameVersions": game_versions, "tags": tags}


def _version_brief(v: ResourceVersion, assets: Optional[list] = None, download_count: Optional[int] = None, *, with_changelog: bool = False) -> dict:
    d = {
        "id": v.id,
        "resourceId": v.resource_id,
        "version": v.version,
        "releaseTag": v.release_tag or "",
        "channel": v.channel,
        "publishedAt": v.published_at or "",
        "gameVersions": _loads_json_array(v.game_versions),
        "platforms": _loads_json_array(v.platforms),
        "side": v.side,
        "status": v.status,
        "isLatestStable": v.is_latest_stable,
        "updateTime": v.update_time,
    }
    if with_changelog:
        d["changelogMd"] = v.changelog_md or ""
    if download_count is not None:
        d["downloadCount"] = download_count
    if assets is not None:
        d["assets"] = assets
    return d


def _asset_brief(a: VersionAsset) -> dict:
    return {
        "id": a.id,
        "versionId": a.version_id,
        "filename": a.filename,
        # ⚠️ 公开响应含 url 是有意的：详情页 tooltip 展示文件来源域名；
        # 下载入口仍是 /download/asset/{id}（前端不得直接以 <a href=url> 下发——契约如此约定）。
        "url": a.url,
        "purpose": a.purpose,
        "sort": a.sort,
        "isPrimary": a.is_primary,
        "status": a.status,
        "updateTime": a.update_time,
    }


# ══════════════════════════════ 公开接口 ══════════════════════════════


@router.get("")
async def list_resources(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=12, ge=1, le=50),
    q: str = Query(default="", max_length=100, description="名称/简介关键词"),
    type: str = Query(default="", description="资源类型 key，空=全部"),
    platform: str = Query(default="", description="平台 key，逗号分隔多值"),
    game_version: str = Query(default="", description="游戏版本 key，逗号分隔多值"),
    side: str = Query(default="", description="client/server/both"),
    channel: str = Query(default="", description="stable/beta/alpha（命中任一版本的渠道）"),
    tag: str = Query(default="", description="标签 key，逗号分隔多值"),
    sort: str = Query(default=SORT_UPDATED_DESC, description="updated_desc | name_asc | downloads_desc"),
    db: AsyncSession = Depends(get_db),
):
    """公开资源列表：只含 status=published 且未软删。

    多对多筛选（platform/game_version/tag）一律 id IN (子查询) 去重，
    不会因一资源命中多个平台而产生重复行（需求 §6.1/§7-11）。
    channel 是版本级筛选：命中「该资源存在该渠道的可见版本」。
    """
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    stmt = select(Resource).where(
        Resource.status == RESOURCE_STATUS_PUBLISHED, Resource.deleted_at == ""
    )
    count_stmt = select(func.count()).select_from(Resource).where(
        Resource.status == RESOURCE_STATUS_PUBLISHED, Resource.deleted_at == ""
    )

    keyword = (q or "").strip()
    if keyword:
        like = f"%{_like_escape(keyword)}%"
        cond = or_(Resource.name.like(like, escape="\\"), Resource.summary.like(like, escape="\\"))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    type_key = (type or "").strip()
    if type_key:
        stmt = stmt.where(Resource.resource_type == type_key)
        count_stmt = count_stmt.where(Resource.resource_type == type_key)

    side_key = (side or "").strip()
    if side_key:
        if side_key not in SIDES:
            raise HTTPException(status_code=400, detail=f"side 仅支持 {'/'.join(SIDES)}")
        stmt = stmt.where(Resource.side == side_key)
        count_stmt = count_stmt.where(Resource.side == side_key)

    # 多对多筛选：子查询 IN，天然去重
    for col_model, col_field, raw in (
        (ResourcePlatform, "platform_key", platform),
        (ResourceGameVersion, "game_version_key", game_version),
        (ResourceTag, "tag_key", tag),
    ):
        keys = [k.strip() for k in (raw or "").split(",") if k.strip()]
        if not keys:
            continue
        dtype = {
            "platform_key": DICT_TYPE_PLATFORM,
            "game_version_key": DICT_TYPE_GAME_VERSION,
            "tag_key": DICT_TYPE_TAG,
        }[col_field]
        await _validate_dict_keys(db, dtype, keys)
        sub = select(col_model.resource_id).where(col_field_key(col_model).in_(keys))
        stmt = stmt.where(Resource.id.in_(sub))
        count_stmt = count_stmt.where(Resource.id.in_(sub))

    # 渠道筛选：存在该渠道的可见版本
    channel_key = (channel or "").strip()
    if channel_key:
        if channel_key not in CHANNELS:
            raise HTTPException(status_code=400, detail=f"channel 仅支持 {'/'.join(CHANNELS)}")
        sub = select(ResourceVersion.resource_id).where(
            ResourceVersion.resource_id == Resource.id,
            ResourceVersion.channel == channel_key,
            ResourceVersion.status == VERSION_STATUS_VISIBLE,
            ResourceVersion.deleted_at == "",
        )
        stmt = stmt.where(sub.exists())
        count_stmt = count_stmt.where(sub.exists())

    sort_key = sort if sort in SORT_OPTIONS else SORT_UPDATED_DESC
    if sort_key == SORT_NAME_ASC:
        order_cols = (Resource.sort_weight.desc(), Resource.name.asc(), Resource.id.desc())
    elif sort_key == SORT_DOWNLOADS_DESC:
        order_cols = (Resource.download_count.desc(), Resource.sort_weight.desc(), Resource.id.desc())
    else:  # updated_desc：推荐位与权重优先级低于时间（最近更新在前）
        order_cols = (Resource.update_time.desc(), Resource.id.desc())
    # 推荐资源恒排最前（sort_weight 只在同档内细分；需求 §5.2 排序项不含"推荐"，
    # 用 featured 做稳定的第一排序键是列表页的实际观感需求）
    stmt = stmt.order_by(Resource.featured.desc(), *order_cols).offset(offset).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt)).scalars().all()
    rels = await _resource_relation_keys(db, [r.id for r in rows])
    items = [
        _resource_brief(
            r,
            {
                "platforms": rels["platforms"].get(r.id, []),
                "gameVersions": rels["gameVersions"].get(r.id, []),
                "tags": rels["tags"].get(r.id, []),
            },
        )
        for r in rows
    ]
    return _ok(_page_payload(items, page, page_size, total))


def col_field_key(col_model):
    """多对多筛选列的 key 字段（SQLAlchemy 不允许字符串拼列名，此处集中映射）。"""
    return {
        ResourcePlatform: ResourcePlatform.platform_key,
        ResourceGameVersion: ResourceGameVersion.game_version_key,
        ResourceTag: ResourceTag.tag_key,
    }[col_model]


@router.get("/filters")
async def list_filters(db: AsyncSession = Depends(get_db)):
    """筛选项字典：enabled 项按 type 分组（前台筛选栏与后台下拉共用一个来源）。"""
    r = await db.execute(
        select(DictItem)
        .where(DictItem.enabled == 1)
        .order_by(DictItem.type.asc(), DictItem.sort.asc(), DictItem.id.asc())
    )
    groups: dict[str, list] = {t: [] for t in DICT_TYPES}
    for item in r.scalars().all():
        groups.setdefault(item.type, []).append({"key": item.key, "label": item.label})
    return _ok(groups)


# ── 字典管理（管理员；需求评审补充：标签等字典项后台可维护） ────────
# MVP 原则的"停用代替删除"：删除入口不开放（已有资源引用的 key 删掉会让
# 关联表成孤儿），enabled=0 即从所有下拉与筛选里消失，数据保留可追溯。


def _dump_dict(d: DictItem) -> dict:
    return {
        "id": d.id,
        "type": d.type,
        "key": d.key,
        "label": d.label,
        "sort": d.sort,
        "enabled": d.enabled,
        "updateTime": d.update_time,
    }


@router.get("/admin/dict")
async def admin_list_dict(
    type: str = Query(default="", description="留空=全部类型"),
    includeDisabled: bool = Query(default=True, description="后台管理含停用项"),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """字典项列表（后台下拉/标签管理用；含停用项，前台 filters 只回 enabled）。"""
    q = select(DictItem)
    dtype = (type or "").strip()
    if dtype:
        if dtype not in DICT_TYPES:
            raise HTTPException(status_code=400, detail=f"type 仅支持 {'/'.join(DICT_TYPES)}")
        q = q.where(DictItem.type == dtype)
    if not includeDisabled:
        q = q.where(DictItem.enabled == 1)
    q = q.order_by(DictItem.type.asc(), DictItem.sort.asc(), DictItem.id.asc())
    rows = (await db.execute(q)).scalars().all()
    return _ok([_dump_dict(d) for d in rows])


@router.post("/admin/dict")
async def admin_create_dict(
    data: DictCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """新增字典项：(type, key) 唯一；key 规则同 slug（小写字母/数字/连字符）。"""
    dtype = (data.type or "").strip()
    key = (data.key or "").strip()
    label = (data.label or "").strip()
    if dtype not in DICT_TYPES:
        raise HTTPException(status_code=400, detail=f"type 仅支持 {'/'.join(DICT_TYPES)}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}[a-z0-9]", key):
        raise HTTPException(status_code=400, detail="key 需为 2-64 位小写字母/数字/连字符，以字母或数字开头结尾")
    if not label or len(label) > 64:
        raise HTTPException(status_code=400, detail="label（展示名）必填且 ≤64 字")
    dup = (
        await db.execute(select(DictItem.id).where(DictItem.type == dtype, DictItem.key == key))
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=400, detail=f"该类型下已存在 key「{key}」")
    now = _now_iso()
    d = DictItem(
        type=dtype,
        key=key,
        label=label,
        sort=data.sort or 0,
        enabled=1 if data.enabled is None else (1 if data.enabled else 0),
        create_time=now,
        update_time=now,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return _ok(_dump_dict(d))


@router.put("/admin/dict/{dict_id}")
async def admin_update_dict(
    dict_id: int,
    data: DictUpdateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑字典项（label/sort/enabled；key 是筛选 URL 参数值，创建后不可改）。"""
    d = (
        await db.execute(select(DictItem).where(DictItem.id == dict_id))
    ).scalar_one_or_none()
    if d is None:
        raise HTTPException(status_code=404, detail="字典项不存在")
    if data.label is not None:
        label = data.label.strip()
        if not label or len(label) > 64:
            raise HTTPException(status_code=400, detail="label（展示名）必填且 ≤64 字")
        d.label = label
    if data.sort is not None:
        d.sort = data.sort
    if data.enabled is not None:
        d.enabled = 1 if data.enabled else 0
    d.update_time = _now_iso()
    await db.commit()
    await db.refresh(d)
    return _ok(_dump_dict(d))


@router.get("/{slug}")
async def get_resource_detail(slug: str, db: AsyncSession = Depends(get_db)):
    """公开资源详情：全量字段 + 版本列表（含每版本可见资产）+ 跳转统计。

    非已发布 / 已软删一律 404（不区分"不存在"与"未公开"，避免探测）。
    """
    row = (
        await db.execute(
            select(Resource).where(
                Resource.slug == slug.strip(), Resource.deleted_at == ""
            )
        )
    ).scalar_one_or_none()
    if row is None or row.status != RESOURCE_STATUS_PUBLISHED:
        raise HTTPException(status_code=404, detail="资源不存在或未公开")

    rels = await _resource_relation_keys(db, [row.id])
    vr = (
        await db.execute(
            select(ResourceVersion)
            .where(
                ResourceVersion.resource_id == row.id,
                ResourceVersion.status == VERSION_STATUS_VISIBLE,
                ResourceVersion.deleted_at == "",
            )
            .order_by(
                ResourceVersion.is_latest_stable.desc(),
                ResourceVersion.published_at.desc(),
                ResourceVersion.id.desc(),
            )
        )
    )
    versions = vr.scalars().all()

    # 一次取全部可见版本的资产，按 sort 分组（避免逐版本查资产 N+1）
    asset_map: dict[int, list] = defaultdict(list)
    if versions:
        ar = await db.execute(
            select(VersionAsset)
            .where(
                VersionAsset.version_id.in_([v.id for v in versions]),
                VersionAsset.status == ASSET_STATUS_VISIBLE,
                VersionAsset.deleted_at == "",
            )
            .order_by(VersionAsset.is_primary.desc(), VersionAsset.sort.asc(), VersionAsset.id.asc())
        )
        for a in ar.scalars().all():
            asset_map[a.version_id].append(_asset_brief(a))

    # 每版本跳转次数（一次 GROUP BY，杜绝表格逐行 COUNT N+1）
    version_counts: dict[int, int] = {}
    if versions:
        vc = await db.execute(
            select(DownloadEvent.version_id, func.count())
            .where(DownloadEvent.version_id.in_([v.id for v in versions]))
            .group_by(DownloadEvent.version_id)
        )
        version_counts = dict(vc.all())

    version_items = []
    for v in versions:
        item = _version_brief(v, asset_map.get(v.id, []), version_counts.get(v.id, 0), with_changelog=True)
        version_items.append(item)
    total_downloads = (
        await db.execute(
            select(func.count()).select_from(DownloadEvent).where(DownloadEvent.resource_id == row.id)
        )
    ).scalar_one()

    data = _resource_brief(row)
    data.update(
        {
            "descriptionMd": row.description_md or "",
            "githubRepoUrl": row.github_repo_url or "",
            "issuesUrl": row.issues_url or "",
            "docsUrl": row.docs_url or "",
            "createTime": row.create_time,
            "platforms": rels["platforms"].get(row.id, []),
            "gameVersions": rels["gameVersions"].get(row.id, []),
            "tags": rels["tags"].get(row.id, []),
            "versions": version_items,
            "downloadCount": total_downloads,  # 详情页按事件实时聚合（与冗余列可互相对账）
            "downloadCountNote": DOWNLOAD_COUNT_NOTE,
        }
    )
    return _ok(data)


# ══════════════════════════════ 下载跳转端点 ══════════════════════════════


@download_router.get("/download/asset/{asset_id}")
async def download_asset(asset_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """下载跳转（需求 §2 权威口径，五步缺一不可）：

    1. 查资产 → 版本 → 资源（一跳取齐，不做三次往返）；
    2. 校验可见性：资产 visible、版本 visible、资源 published、三方均未软删；
    3. 校验 URL 白名单（历史数据被绕过后台改动时兜底，正常写路径已拦）；
    4. 记录 download_event（IP 哈希 + UA/Referer 截断）并原子累加冗余计数；
    5. 302 到 asset.url。

    不接受任何 URL 参数；不可用 404/410；限速 429。
    """
    _check_download_rate(_client_ip(request))

    r = (
        await db.execute(
            select(VersionAsset, ResourceVersion, Resource)
            .join(ResourceVersion, ResourceVersion.id == VersionAsset.version_id)
            .join(Resource, Resource.id == ResourceVersion.resource_id)
            .where(VersionAsset.id == asset_id)
        )
    ).first()
    if r is None:
        raise HTTPException(status_code=404, detail="下载资源不存在")
    asset, version, resource = r

    gone = (
        asset.deleted_at != ""
        or asset.status != ASSET_STATUS_VISIBLE
        or version.deleted_at != ""
        or version.status != VERSION_STATUS_VISIBLE
        or resource.deleted_at != ""
        or resource.status != RESOURCE_STATUS_PUBLISHED
    )
    if gone:
        # 410=曾存在但已下架/隐藏（语义比 404 准确；两者前端都按"不可下载"处理）
        raise HTTPException(status_code=410, detail="该文件已下架或隐藏，暂不可下载")

    url = (asset.url or "").strip()
    if not url.startswith(GITHUB_URL_PREFIX):
        raise HTTPException(status_code=410, detail="该文件的下载链接配置无效")

    now = _now_iso()
    ip = _client_ip(request)
    ua = (request.headers.get("user-agent", "") or "")[:255]
    referer = (request.headers.get("referer", "") or "")[:255]
    db.add(
        DownloadEvent(
            resource_id=resource.id,
            version_id=version.id,
            asset_id=asset.id,
            created_at=now,
            ip_hash=_ip_hash(ip),
            user_agent=ua,
            referer=referer,
        )
    )
    # 冗余计数与事件同事务提交（forum 原子计数同思路；NullPool 下每请求独立连接，
    # 事务内两写要么同时可见要么同时回滚，与关系表不会失配）
    await db.execute(
        update(Resource)
        .where(Resource.id == resource.id)
        .values(download_count=Resource.download_count + 1)
    )
    await db.commit()

    return RedirectResponse(url=url, status_code=302)


# ══════════════════════════════ 管理员接口 ══════════════════════════════


async def _get_resource_or_404(db: AsyncSession, resource_id: int, include_deleted: bool = True) -> Resource:
    row = (
        await db.execute(select(Resource).where(Resource.id == resource_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    if row.deleted_at != "" and not include_deleted:
        raise HTTPException(status_code=404, detail="资源不存在")
    return row


async def _get_version_or_404(db: AsyncSession, version_id: int) -> ResourceVersion:
    v = (
        await db.execute(select(ResourceVersion).where(ResourceVersion.id == version_id))
    ).scalar_one_or_none()
    if v is None or v.deleted_at != "":
        raise HTTPException(status_code=404, detail="版本不存在")
    return v


async def _get_asset_or_404(db: AsyncSession, asset_id: int) -> VersionAsset:
    a = (
        await db.execute(select(VersionAsset).where(VersionAsset.id == asset_id))
    ).scalar_one_or_none()
    if a is None or a.deleted_at != "":
        raise HTTPException(status_code=404, detail="资产不存在")
    return a


async def _sync_resource_relations(
    db: AsyncSession,
    resource: Resource,
    *,
    platforms: Optional[list[str]] = None,
    game_versions: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    now: str,
) -> None:
    """全量重写资源的三组关联 key（None=不改，[] =清空）。

    量级：单资源关联项 ≤ 数十行，全删全插比 diff 简单且不会漏改（一阶段口径）。
    """
    groups = (
        (ResourcePlatform, "platform_key", DICT_TYPE_PLATFORM, platforms),
        (ResourceGameVersion, "game_version_key", DICT_TYPE_GAME_VERSION, game_versions),
        (ResourceTag, "tag_key", DICT_TYPE_TAG, tags),
    )
    for model, key_col, dtype, keys in groups:
        if keys is None:
            continue
        valid = await _validate_dict_keys(db, dtype, keys)
        await db.execute(delete_stmt(model, resource.id))
        for k in valid:
            db.add(model(**{"resource_id": resource.id, key_col: k, "create_time": now}))


def delete_stmt(model, resource_id: int):
    """关联表全删语句（集中一处便于审计；delete 已在模块顶部 import）。"""
    return delete(model).where(model.resource_id == resource_id)


@router.get("/admin/page")
async def admin_page(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keyword: str = Query(default="", max_length=100, description="按名称/slug/简介搜索"),
    status: str = Query(default="", description="draft|published|hidden|archived|deleted，空=全部（不含已删）"),
    _admin: "object" = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """资源管理分页（含未发布；status=deleted 查回收站；软删数据保留可追溯）。"""
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    conds = []
    status_key = (status or "").strip()
    if status_key == "deleted":
        conds.append(Resource.deleted_at != "")
    else:
        conds.append(Resource.deleted_at == "")
        if status_key:
            if status_key not in RESOURCE_STATUSES:
                raise HTTPException(status_code=400, detail=f"status 仅支持 {'/'.join(RESOURCE_STATUSES)}/deleted")
            conds.append(Resource.status == status_key)

    kw = (keyword or "").strip()
    if kw:
        like = f"%{_like_escape(kw)}%"
        conds.append(
            or_(Resource.name.like(like, escape="\\"), Resource.slug.like(like, escape="\\"),
                Resource.summary.like(like, escape="\\"))
        )

    where = and_(*conds) if conds else None
    count_stmt = select(func.count()).select_from(Resource)
    stmt = select(Resource)
    if where is not None:
        count_stmt = count_stmt.where(where)
        stmt = stmt.where(where)
    stmt = stmt.order_by(Resource.update_time.desc(), Resource.id.desc()).offset(offset).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt)).scalars().all()
    rels = await _resource_relation_keys(db, [r.id for r in rows])

    # 一次聚合每资源的版本数/资产数（管理列表展示用；避免逐行 COUNT N+1）
    version_counts: dict[int, int] = {}
    asset_counts: dict[int, int] = {}
    if rows:
        vcnt = await db.execute(
            select(ResourceVersion.resource_id, func.count())
            .where(
                ResourceVersion.resource_id.in_([r.id for r in rows]),
                ResourceVersion.deleted_at == "",
            )
            .group_by(ResourceVersion.resource_id)
        )
        version_counts = dict(vcnt.all())
        acnt = await db.execute(
            select(ResourceVersion.resource_id, func.count())
            .select_from(VersionAsset)
            .join(ResourceVersion, ResourceVersion.id == VersionAsset.version_id)
            .where(
                ResourceVersion.resource_id.in_([r.id for r in rows]),
                VersionAsset.deleted_at == "",
            )
            .group_by(ResourceVersion.resource_id)
        )
        asset_counts = dict(acnt.all())

    items = [
        _resource_brief(
            r,
            {
                "platforms": rels["platforms"].get(r.id, []),
                "gameVersions": rels["gameVersions"].get(r.id, []),
                "tags": rels["tags"].get(r.id, []),
                "versionCount": version_counts.get(r.id, 0),
                "assetCount": asset_counts.get(r.id, 0),
                "createTime": r.create_time,
                "githubRepoUrl": r.github_repo_url or "",
                "deletedAt": r.deleted_at or "",
                "createdBy": r.created_by or "",
            },
        )
        for r in rows
    ]
    return _ok(_page_payload(items, page, page_size, total))


# ── 统计（需求 §4.4） ─────────────────────────────────────────────
# ⚠️ 必须声明在 GET /admin/{resource_id} 之前：FastAPI 按声明顺序匹配，
# 否则 "stats" 会被当成 resource_id 解析出 422（踩过一次，勿移回下方）。
@router.get("/admin/stats")
async def admin_stats(
    start: str = Query(default="", description="起始时间 YYYY-MM-DD（北京时间，含当日）"),
    end: str = Query(default="", description="结束时间 YYYY-MM-DD（含当日）"),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """下载跳转统计：总览 + 按资源 + 按版本 + 按资产，支持时间范围（按事件 created_at）。"""
    conds = []
    start_s = (start or "").strip()
    end_s = (end or "").strip()
    if start_s:
        conds.append(DownloadEvent.created_at >= f"{start_s[:10]}T00:00:00")
    if end_s:
        conds.append(DownloadEvent.created_at <= f"{end_s[:10]}T23:59:59")
    where = and_(*conds) if conds else None

    async def _group_count(group_col):
        stmt = select(
            group_col,
            func.count().label("cnt"),
        ).group_by(group_col)
        if where is not None:
            stmt = stmt.where(where)
        return dict((await db.execute(stmt)).all())

    async def _named_rows(*, name_col, parent_name_col, join_model):
        """带名称的分组统计。

        三组维度各自的名称列与 join 链不同（写死三个分支，避免动态 join 拼错）：
          按资源   → join resources，名称=name，父列=slug；
          按版本   → join resource_versions + resources，名称=version，父列=资源名；
          按资产   → join version_assets + resource_versions + resources，名称=filename，父列=资源名。
        """
        stmt = (
            select(
                join_model.id.label("id"),
                name_col.label("name"),
                parent_name_col.label("parent_name"),
                func.count().label("cnt"),
            )
            .select_from(DownloadEvent)
        )
        if join_model is Resource:
            # 按资源：join 一次，名称与父列都来自 resources 本身
            stmt = stmt.join(Resource, Resource.id == DownloadEvent.resource_id)
        elif join_model is ResourceVersion:
            # 按版本：先连 resource_versions，再连 resources 拿资源名
            stmt = stmt.join(ResourceVersion, ResourceVersion.id == DownloadEvent.version_id)
            stmt = stmt.join(Resource, Resource.id == ResourceVersion.resource_id)
        else:
            # 按资产：先连 version_assets，再连 resource_versions、resources 拿资源名
            stmt = stmt.join(VersionAsset, VersionAsset.id == DownloadEvent.asset_id)
            stmt = stmt.join(ResourceVersion, ResourceVersion.id == VersionAsset.version_id)
            stmt = stmt.join(Resource, Resource.id == ResourceVersion.resource_id)
        stmt = (
            stmt.group_by(join_model.id, name_col, parent_name_col)
            .order_by(func.count().desc())
            .limit(100)
        )
        if where is not None:
            stmt = stmt.where(where)
        rows = (await db.execute(stmt)).all()
        return [{"id": r.id, "name": r.name, "parent": r.parent_name, "count": r.cnt} for r in rows]

    total_stmt = select(func.count()).select_from(DownloadEvent)
    if where is not None:
        total_stmt = total_stmt.where(where)
    total = (await db.execute(total_stmt)).scalar_one()

    by_resource = await _named_rows(
        name_col=Resource.name,
        parent_name_col=Resource.slug,
        join_model=Resource,
    )
    by_version = await _named_rows(
        name_col=ResourceVersion.version,
        parent_name_col=Resource.name,
        join_model=ResourceVersion,
    )
    by_asset = await _named_rows(
        name_col=VersionAsset.filename,
        parent_name_col=Resource.name,
        join_model=VersionAsset,
    )

    # 近 30 天每日曲线（趋势图用；无事件的日期由前端补零）
    daily_rows = (
        await db.execute(
            select(
                func.substr(DownloadEvent.created_at, 1, 10).label("day"),
                func.count().label("cnt"),
            )
            .group_by("day")
            .order_by("day")
        )
    ).all()
    daily = [{"day": r.day, "count": r.cnt} for r in daily_rows]

    return _ok(
        {
            "total": total,
            "byResource": by_resource,
            "byVersion": by_version,
            "byAsset": by_asset,
            "daily": daily,
            "note": DOWNLOAD_COUNT_NOTE,
        }
    )




@router.get("/admin/{resource_id}")
async def admin_get_resource(
    resource_id: int, _admin=Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """资源编辑回填：全字段 + 三组关联 key + 版本/资产计数。"""
    row = await _get_resource_or_404(db, resource_id)
    rels = await _resource_relation_keys(db, [row.id])
    version_count = (
        await db.execute(
            select(func.count())
            .select_from(ResourceVersion)
            .where(ResourceVersion.resource_id == row.id, ResourceVersion.deleted_at == "")
        )
    ).scalar_one()
    data = _resource_brief(row)
    data.update(
        {
            "descriptionMd": row.description_md or "",
            "githubRepoUrl": row.github_repo_url or "",
            "issuesUrl": row.issues_url or "",
            "docsUrl": row.docs_url or "",
            "createTime": row.create_time,
            "deletedAt": row.deleted_at or "",
            "createdBy": row.created_by or "",
            "platforms": rels["platforms"].get(row.id, []),
            "gameVersions": rels["gameVersions"].get(row.id, []),
            "tags": rels["tags"].get(row.id, []),
            "versionCount": version_count,
        }
    )
    return _ok(data)


@router.post("/admin")
async def admin_create_resource(
    data: ResourceCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """新建资源（默认草稿态；slug 全局唯一，创建后仍可改但需唯一）。"""
    slug = (data.slug or "").strip()
    _validate_slug(slug)
    await _ensure_slug_free(db, slug, exclude_id=None)
    _validate_status(data.status)
    _validate_side(data.side)
    now = _now_iso()
    row = Resource(
        slug=slug,
        name=data.name.strip(),
        resource_type=data.resource_type.strip() or DICT_TYPE_RESOURCE and "mod",
        summary=data.summary.strip(),
        description_md=data.description_md or "",
        icon_url=(data.icon_url or "").strip(),
        cover_url=(data.cover_url or "").strip(),
        side=data.side,
        status=data.status,
        featured=1 if data.featured else 0,
        sort_weight=data.sort_weight or 0,
        github_repo_url=(data.github_repo_url or "").strip(),
        issues_url=(data.issues_url or "").strip(),
        docs_url=(data.docs_url or "").strip(),
        created_by=_admin.username,
        download_count=0,
        create_time=now,
        update_time=now,
        deleted_at="",
    )
    # 类型 key 需在字典内（避免后台下拉与字典脱节）
    await _validate_dict_keys(db, DICT_TYPE_RESOURCE, [row.resource_type])
    db.add(row)
    await db.flush()  # 拿到 id 再写关联表
    await _sync_resource_relations(
        db, row,
        platforms=data.platforms, game_versions=data.game_versions, tags=data.tags, now=now,
    )
    await db.commit()
    await db.refresh(row)
    return _ok(_resource_brief(row))


@router.put("/admin/{resource_id}")
async def admin_update_resource(
    resource_id: int,
    data: ResourceUpdateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑资源（部分更新；slug 改动同样过唯一性校验；关联表按传入数组全量重写）。"""
    row = await _get_resource_or_404(db, resource_id)
    now = _now_iso()

    if data.slug is not None and data.slug.strip() != row.slug:
        slug = data.slug.strip()
        _validate_slug(slug)
        await _ensure_slug_free(db, slug, exclude_id=row.id)
        row.slug = slug
    if data.name is not None:
        if not data.name.strip():
            raise HTTPException(status_code=400, detail="资源名称不能为空")
        row.name = data.name.strip()
    if data.resource_type is not None:
        await _validate_dict_keys(db, DICT_TYPE_RESOURCE, [data.resource_type.strip()])
        row.resource_type = data.resource_type.strip()
    if data.summary is not None:
        row.summary = data.summary.strip()
    if data.description_md is not None:
        row.description_md = data.description_md
    if data.icon_url is not None:
        row.icon_url = data.icon_url.strip()
    if data.cover_url is not None:
        row.cover_url = data.cover_url.strip()
    if data.side is not None:
        _validate_side(data.side)
        row.side = data.side
    if data.featured is not None:
        row.featured = 1 if data.featured else 0
    if data.sort_weight is not None:
        row.sort_weight = data.sort_weight
    if data.github_repo_url is not None:
        row.github_repo_url = data.github_repo_url.strip()
    if data.issues_url is not None:
        row.issues_url = data.issues_url.strip()
    if data.docs_url is not None:
        row.docs_url = data.docs_url.strip()

    row.update_time = now
    await _sync_resource_relations(
        db, row,
        platforms=data.platforms, game_versions=data.game_versions, tags=data.tags, now=now,
    )
    await db.commit()
    await db.refresh(row)
    return _ok(_resource_brief(row))


@router.post("/admin/{resource_id}/status")
async def admin_set_resource_status(
    resource_id: int,
    data: ResourceStatusRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """状态切换：publish/hide/archive/draft（回收站走 DELETE，不混入本端点）。"""
    row = await _get_resource_or_404(db, resource_id)
    if row.deleted_at != "":
        raise HTTPException(status_code=400, detail="已删除的资源请先恢复后再改状态")
    if data.status not in RESOURCE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status 仅支持 {'/'.join(RESOURCE_STATUSES)}")
    row.status = data.status
    row.update_time = _now_iso()
    await db.commit()
    await db.refresh(row)
    return _ok(_resource_brief(row))


@router.delete("/admin/{resource_id}")
async def admin_delete_resource(
    resource_id: int, _admin=Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """软删除（deleted_at；数据保留可追溯，需求 §4.4）。前台立即可见性消失。"""
    row = await _get_resource_or_404(db, resource_id)
    if row.deleted_at != "":
        raise HTTPException(status_code=400, detail="该资源已在回收站")
    row.deleted_at = _now_iso()
    row.update_time = _now_iso()
    await db.commit()
    return _ok({"id": row.id, "deletedAt": row.deleted_at})


@router.post("/admin/{resource_id}/restore")
async def admin_restore_resource(
    resource_id: int, _admin=Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """从回收站恢复软删除的资源（回到删除前状态，状态机不重置）。"""
    row = await _get_resource_or_404(db, resource_id)
    if row.deleted_at == "":
        raise HTTPException(status_code=400, detail="该资源不在回收站")
    row.deleted_at = ""
    row.update_time = _now_iso()
    await db.commit()
    return _ok(_resource_brief(row))


# ── 版本管理 ──────────────────────────────────────────────────────


@router.get("/admin/{resource_id}/versions")
async def admin_list_versions(
    resource_id: int, _admin=Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """版本管理列表（含隐藏/归档，不含软删；带每版本资产数组便于后台直接编辑）。"""
    resource = await _get_resource_or_404(db, resource_id)
    vr = (
        await db.execute(
            select(ResourceVersion)
            .where(
                ResourceVersion.resource_id == resource.id,
                ResourceVersion.deleted_at == "",
            )
            .order_by(
                ResourceVersion.is_latest_stable.desc(),
                ResourceVersion.published_at.desc(),
                ResourceVersion.id.desc(),
            )
        )
    )
    versions = vr.scalars().all()
    asset_map: dict[int, list] = defaultdict(list)
    if versions:
        ar = await db.execute(
            select(VersionAsset)
            .where(
                VersionAsset.version_id.in_([v.id for v in versions]),
                VersionAsset.deleted_at == "",
            )
            .order_by(VersionAsset.is_primary.desc(), VersionAsset.sort.asc(), VersionAsset.id.asc())
        )
        for a in ar.scalars().all():
            asset_map[a.version_id].append(_asset_brief(a))
    return _ok([_version_brief(v, asset_map.get(v.id, [])) for v in versions])


@router.post("/admin/{resource_id}/versions")
async def admin_create_version(
    resource_id: int,
    data: VersionCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """新建版本：同资源下 version 唯一；channel/side 枚举校验；兼容范围是字典 key 数组。"""
    resource = await _get_resource_or_404(db, resource_id)
    version_no = (data.version or "").strip()
    if not version_no or len(version_no) > 64:
        raise HTTPException(status_code=400, detail="版本号必填且 ≤64 字符")
    dup = (
        await db.execute(
            select(ResourceVersion.id).where(
                ResourceVersion.resource_id == resource.id,
                ResourceVersion.version == version_no,
                ResourceVersion.deleted_at == "",
            )
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=400, detail=f"该资源下已存在版本 {version_no}")
    _validate_channel(data.channel)
    _validate_side(data.side)
    count = (
        await db.execute(
            select(func.count())
            .select_from(ResourceVersion)
            .where(ResourceVersion.resource_id == resource.id, ResourceVersion.deleted_at == "")
        )
    ).scalar_one()
    if count >= VERSION_MAX:
        raise HTTPException(status_code=400, detail=f"单资源版本数已达上限（{VERSION_MAX}）")

    now = _now_iso()
    gv_keys = await _validate_dict_keys(db, DICT_TYPE_GAME_VERSION, data.game_versions or [])
    pf_keys = await _validate_dict_keys(db, DICT_TYPE_PLATFORM, data.platforms or [])
    v = ResourceVersion(
        resource_id=resource.id,
        version=version_no,
        release_tag=(data.release_tag or "").strip(),
        channel=data.channel,
        published_at=(data.published_at or now)[:30],
        game_versions=json.dumps(gv_keys, ensure_ascii=False),
        platforms=json.dumps(pf_keys, ensure_ascii=False),
        side=data.side,
        changelog_md=data.changelog_md or "",
        status=VERSION_STATUS_VISIBLE if data.status is None else data.status,
        is_latest_stable=0,
        create_time=now,
        update_time=now,
        deleted_at="",
    )
    _validate_version_status(v.status)
    db.add(v)
    # 显式勾选"最新稳定版"时执行唯一性转移
    if data.is_latest_stable:
        await _set_latest_stable(db, resource.id, v, now=now)
    await db.commit()
    await db.refresh(v)
    return _ok(_version_brief(v))


@router.put("/admin/versions/{version_id}")
async def admin_update_version(
    version_id: int,
    data: VersionUpdateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑版本（部分更新；is_latest_stable=true 时执行"每资源唯一"转移，
    =false 时清掉本版本的标记但不自动补位——补位由后台在别的版本上显式勾选）。"""
    v = await _get_version_or_404(db, version_id)
    now = _now_iso()

    if data.version is not None:
        new_no = data.version.strip()
        if not new_no or len(new_no) > 64:
            raise HTTPException(status_code=400, detail="版本号必填且 ≤64 字符")
        if new_no != v.version:
            dup = (
                await db.execute(
                    select(ResourceVersion.id).where(
                        ResourceVersion.resource_id == v.resource_id,
                        ResourceVersion.version == new_no,
                        ResourceVersion.deleted_at == "",
                        ResourceVersion.id != v.id,
                    )
                )
            ).scalar_one_or_none()
            if dup is not None:
                raise HTTPException(status_code=400, detail=f"该资源下已存在版本 {new_no}")
            v.version = new_no
    if data.release_tag is not None:
        v.release_tag = data.release_tag.strip()
    if data.channel is not None:
        _validate_channel(data.channel)
        v.channel = data.channel
    if data.published_at is not None:
        v.published_at = (data.published_at or "")[:30]
    if data.game_versions is not None:
        v.game_versions = json.dumps(
            await _validate_dict_keys(db, DICT_TYPE_GAME_VERSION, data.game_versions),
            ensure_ascii=False,
        )
    if data.platforms is not None:
        v.platforms = json.dumps(
            await _validate_dict_keys(db, DICT_TYPE_PLATFORM, data.platforms),
            ensure_ascii=False,
        )
    if data.side is not None:
        _validate_side(data.side)
        v.side = data.side
    if data.changelog_md is not None:
        v.changelog_md = data.changelog_md
    if data.status is not None:
        _validate_version_status(data.status)
        v.status = data.status
    if data.is_latest_stable is True:
        await _set_latest_stable(db, v.resource_id, v, now=now)
    elif data.is_latest_stable is False and v.is_latest_stable:
        v.is_latest_stable = 0

    v.update_time = now
    # 版本隐藏/下架时其资产不再可下载——由下载端点实时校验版本状态，无需物化处理
    await db.commit()
    await db.refresh(v)
    return _ok(_version_brief(v))


async def _set_latest_stable(db: AsyncSession, resource_id: int, target: ResourceVersion, *, now: str) -> None:
    """「每个资源最多一个最新稳定版」的唯一转移点（先清后立，同事务原子）。"""
    if target.channel != CHANNEL_STABLE:
        raise HTTPException(status_code=400, detail="只有 stable 渠道的版本才能设为最新稳定版")
    await db.execute(
        update(ResourceVersion)
        .where(ResourceVersion.resource_id == resource_id, ResourceVersion.is_latest_stable == 1)
        .values(is_latest_stable=0)
    )
    target.is_latest_stable = 1
    target.update_time = now


@router.delete("/admin/versions/{version_id}")
async def admin_delete_version(
    version_id: int, _admin=Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """软删除版本（其资产随版本不可下载，下载端点实时校验；数据保留）。"""
    v = await _get_version_or_404(db, version_id)
    now = _now_iso()
    v.deleted_at = now
    v.is_latest_stable = 0
    v.update_time = now
    await db.commit()
    return _ok({"id": v.id, "deletedAt": v.deleted_at})


# ── 资产管理 ──────────────────────────────────────────────────────


@router.get("/admin/versions/{version_id}/assets")
async def admin_list_assets(
    version_id: int, _admin=Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """资产列表（含隐藏；主资产排前，其余按 sort）。"""
    v = await _get_version_or_404(db, version_id)
    ar = (
        await db.execute(
            select(VersionAsset)
            .where(VersionAsset.version_id == v.id, VersionAsset.deleted_at == "")
            .order_by(VersionAsset.is_primary.desc(), VersionAsset.sort.asc(), VersionAsset.id.asc())
        )
    )
    return _ok([_asset_brief(a) for a in ar.scalars().all()])


@router.post("/admin/versions/{version_id}/assets")
async def admin_create_asset(
    version_id: int,
    data: AssetCreateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """新建资产：URL 白名单（github.com）+ 文件名必填 + is_primary 每版本唯一转移。"""
    v = await _get_version_or_404(db, version_id)
    filename = (data.filename or "").strip()
    if not filename or len(filename) > 255:
        raise HTTPException(status_code=400, detail="文件名必填且 ≤255 字符")
    if data.purpose not in PURPOSES:
        raise HTTPException(status_code=400, detail=f"purpose 仅支持 {'/'.join(PURPOSES)}")
    url = _validate_github_asset_url(data.url)
    count = (
        await db.execute(
            select(func.count())
            .select_from(VersionAsset)
            .where(VersionAsset.version_id == v.id, VersionAsset.deleted_at == "")
        )
    ).scalar_one()
    if count >= ASSET_MAX:
        raise HTTPException(status_code=400, detail=f"单版本资产数已达上限（{ASSET_MAX}）")

    now = _now_iso()
    a = VersionAsset(
        version_id=v.id,
        filename=filename,
        url=url,
        purpose=data.purpose,
        sort=data.sort or 0,
        is_primary=0,
        status=ASSET_STATUS_VISIBLE if data.status is None else data.status,
        create_time=now,
        update_time=now,
        deleted_at="",
    )
    _validate_asset_status(a.status)
    db.add(a)
    await db.flush()
    if data.is_primary:
        await _set_primary_asset(db, v.id, a, now=now)
    elif a.purpose == PURPOSE_MAIN:
        # 第一个 main 资产自动成为主资产（需求 §4.3「无主资产取排序第一个可见资产」，
        # 直接物化主标记让后台语义更直观；后续 main 不再抢占）
        primary_exists = (
            await db.execute(
                select(func.count())
                .select_from(VersionAsset)
                .where(
                    VersionAsset.version_id == v.id,
                    VersionAsset.is_primary == 1,
                    VersionAsset.deleted_at == "",
                    VersionAsset.id != a.id,
                )
            )
        ).scalar_one()
        if primary_exists == 0:
            a.is_primary = 1
    await db.commit()
    await db.refresh(a)
    return _ok(_asset_brief(a))


@router.put("/admin/assets/{asset_id}")
async def admin_update_asset(
    asset_id: int,
    data: AssetUpdateRequest,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """编辑资产（部分更新；is_primary=true 时同版本唯一转移；隐藏资产即时不可下载）。"""
    a = await _get_asset_or_404(db, asset_id)
    now = _now_iso()
    if data.filename is not None:
        filename = data.filename.strip()
        if not filename or len(filename) > 255:
            raise HTTPException(status_code=400, detail="文件名必填且 ≤255 字符")
        a.filename = filename
    if data.url is not None:
        a.url = _validate_github_asset_url(data.url)
    if data.purpose is not None:
        if data.purpose not in PURPOSES:
            raise HTTPException(status_code=400, detail=f"purpose 仅支持 {'/'.join(PURPOSES)}")
        a.purpose = data.purpose
    if data.sort is not None:
        a.sort = data.sort
    if data.status is not None:
        _validate_asset_status(data.status)
        a.status = data.status
    if data.is_primary is True:
        await _set_primary_asset(db, a.version_id, a, now=now)
    elif data.is_primary is False and a.is_primary:
        a.is_primary = 0
    a.update_time = now
    await db.commit()
    await db.refresh(a)
    return _ok(_asset_brief(a))


async def _set_primary_asset(db: AsyncSession, version_id: int, target: VersionAsset, *, now: str) -> None:
    """「主下载资产每版本最多一个」的唯一转移点（先清后立）。"""
    await db.execute(
        update(VersionAsset)
        .where(VersionAsset.version_id == version_id, VersionAsset.is_primary == 1)
        .values(is_primary=0)
    )
    target.is_primary = 1
    target.update_time = now


@router.delete("/admin/assets/{asset_id}")
async def admin_delete_asset(
    asset_id: int, _admin=Depends(require_admin), db: AsyncSession = Depends(get_db)
):
    """软删除资产。若删的是主资产，主下载自动回落到 sort 第一个可见资产
    （查询侧 is_primary DESC, sort ASC 排序已保证，无需物化补位）。"""
    a = await _get_asset_or_404(db, asset_id)
    now = _now_iso()
    a.deleted_at = now
    a.is_primary = 0
    a.update_time = now
    await db.commit()
    return _ok({"id": a.id, "deletedAt": a.deleted_at})


# ── 枚举校验小工具 ────────────────────────────────────────────────


def _validate_slug(slug: str) -> None:
    if not SLUG_RE.fullmatch(slug):
        raise HTTPException(
            status_code=400,
            detail="slug 需为 3-64 位小写字母/数字/连字符，且以字母或数字开头结尾",
        )


async def _ensure_slug_free(db: AsyncSession, slug: str, *, exclude_id: Optional[int]) -> None:
    q = select(Resource.id).where(Resource.slug == slug, Resource.deleted_at == "")
    if exclude_id is not None:
        q = q.where(Resource.id != exclude_id)
    if (await db.execute(q)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail=f"slug「{slug}」已被占用")


def _validate_status(status: str) -> None:
    if status not in RESOURCE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status 仅支持 {'/'.join(RESOURCE_STATUSES)}")


def _validate_side(side: str) -> None:
    if side not in SIDES:
        raise HTTPException(status_code=400, detail=f"side 仅支持 {'/'.join(SIDES)}")


def _validate_channel(channel: str) -> None:
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"channel 仅支持 {'/'.join(CHANNELS)}")


def _validate_version_status(status: str) -> None:
    if status not in VERSION_STATUSES:
        raise HTTPException(status_code=400, detail=f"版本 status 仅支持 {'/'.join(VERSION_STATUSES)}")


def _validate_asset_status(status: str) -> None:
    if status not in ASSET_STATUSES:
        raise HTTPException(status_code=400, detail=f"资产 status 仅支持 {'/'.join(ASSET_STATUSES)}")
