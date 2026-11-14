"""GitHub Release 双轨同步核心（docs/资源中心/GitHub Release 版本同步需求说明.md）。

双轨口径（硬规则，改代码前先读 PRD §4.3 字段映射表）：
- **批量同步（只增不改）**：拉最新 20 条 Release，过滤 draft；按 release_tag
  判存——本地已有同名 Tag 一律跳过（幂等），只新增缺失的版本。新增版本默认
  可见；**最新 Release**（列表第一条非 draft）若是 stable 渠道，自动设为该资源
  最新稳定版（先清后立唯一转移；prerelease 是 Beta 渠道不设）。
  （2026-11-14 口径调整，覆盖原 PRD §4.3「默认隐藏 / 最新稳定版默认 false」。）
- **单版本同步（精准覆盖）**：按版本的 release_tag 拉 `/releases/tags/{tag}`
  单条详情，只覆盖 GitHub 能提供的字段（版本号/渠道/发布日期/更新日志 +
  资产列表）；**status / is_latest_stable / game_versions / platforms / side
  一律不覆盖**（管理员手工元数据红线）。资产是"替换自动同步来的"：
  只软删 source=github 的资产行再重建，手动录入的资产永远保留。

本模块**不 import fastapi**（与 staff_core 同思路）：异常用本模块自定义类型，
API 层（resource_center.py）翻译成 HTTPException，定时 CLI（github_sync.py）
直接复用同一套函数。Token 安全红线：GITHUB_PAT 只进 Authorization 请求头，
不进 URL、不进任何日志/异常消息。
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import func, select, update as sqlalchemy_update
from sqlalchemy.ext.asyncio import AsyncSession

from .config import GITHUB
from .database import (
    Resource,
    ResourceGameVersion,
    ResourcePlatform,
    ResourceVersion,
    VersionAsset,
)

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Shanghai")

# GitHub API 约定（PRD §2）：Accept / Api-Version 固定；PAT 存在才注入 Authorization
_GITHUB_API_BASE = "https://api.github.com"
_RELEASES_PAGE_SIZE = 20  # 批量同步只拉最新 20 条（PRD §4.1）
_REQUEST_TIMEOUT = 10.0  # 秒（PRD §6「网络超时 10 秒」）
_MAX_RETRIES = 2  # 超时/连接错误最多重试 2 次
ASSET_SYNC_MAX = 50  # 与 resource_center.ASSET_MAX 同值（避免循环 import，改一处需同步另一处）

VERSION_SOURCE_MANUAL = "manual"
VERSION_SOURCE_GITHUB = "github"

# 渠道枚举（与 resource_center.CHANNELS 同值；本模块不 import 那个 APIRouter 文件）
CHANNEL_STABLE = "stable"
CHANNEL_BETA = "beta"


class GitHubSyncError(Exception):
    """GitHub 同步失败（message 面向用户中文文案；绝不携带 Token / 完整堆栈）。"""


class GitHubRateLimitError(GitHubSyncError):
    """403/429：API 速率限制（PRD §6）。"""


class GitHubNotFoundError(GitHubSyncError):
    """404：仓库不存在或 Tag 不存在（PRD §3.2/§6）。"""


# ── 仓库地址解析 ──────────────────────────────────────────────────

# https://github.com/{owner}/{repo}[/...]；owner/repo 允许字母数字 .-_，
# 仓库名历史上有极短的（如 a），不设最小长度只限字符集。
_REPO_URL_RE = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+)/?(?:[?#].*)?$")


def parse_github_repo(url: str) -> Optional[tuple[str, str]]:
    """从资源 GitHub 仓库地址提取 (owner, repo)；非合法地址返回 None。

    只认 https://github.com/ 前缀（与资源中心资产 URL 白名单同口径），
    忽略多余路径段（tree/blob/issues 等一律不接受——同步只按仓库根拉 Release）。
    """
    u = (url or "").strip()
    m = _REPO_URL_RE.match(u)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    # git URL 里 .git 后缀兜底剥掉（https://github.com/o/r.git）
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo or None


# ── GitHub HTTP 客户端 ────────────────────────────────────────────


def _github_headers() -> dict:
    """每次请求现拼请求头；Token 只进这里，不落任何其他地方。"""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "xqly-website-resource-sync",
    }
    if GITHUB.pat:
        headers["Authorization"] = f"Bearer {GITHUB.pat}"
    return headers


async def _github_get_json(url: str) -> dict | list:
    """GET GitHub API：10s 超时、超时/网络错误最多重试 2 次（PRD §6）。

    404/403/429 语义化成专用异常；其余非 2xx 统一 GitHubSyncError（含状态码，
    不含响应体——响应体可能回显请求上下文，安全红线宁可少带信息）。
    """
    last_err: Exception | None = None
    for attempt in range(1 + _MAX_RETRIES):
        try:
            async with httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT, headers=_github_headers(), follow_redirects=False
            ) as client:
                resp = await client.get(url)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_err = e
            logger.warning("GitHub 请求网络异常（第 %d 次尝试）：%s", attempt + 1, type(e).__name__)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))
            continue
        if resp.status_code == 404:
            raise GitHubNotFoundError("无法访问仓库或 Tag 不存在（404）")
        if resp.status_code in (403, 429):
            raise GitHubRateLimitError("GitHub API 达到速率限制，请稍后再试或配置 GITHUB_PAT")
        if resp.is_success:
            try:
                return resp.json()
            except ValueError as e:
                raise GitHubSyncError("GitHub 返回了无法解析的数据") from e
        raise GitHubSyncError(f"GitHub 请求失败（HTTP {resp.status_code}）")
    raise GitHubSyncError("GitHub 请求超时，已重试仍失败，请稍后再试") from last_err


# ── Release 归一化 ────────────────────────────────────────────────


@dataclass(frozen=True)
class NormalizedRelease:
    """一条 GitHub Release 归一化后的最小字段集（资产已过滤源码包）。"""

    tag: str
    version_no: str  # tag 去 v 前缀（PRD §4.3）
    prerelease: bool
    published_at: str  # 北京时间 naive ISO「YYYY-MM-DDTHH:MM:SS」（项目时间口径）
    changelog_md: str
    assets: list[dict]  # [{filename, url}]，按 GitHub 返回顺序


_VERSION_NO_RE = re.compile(r"^v(?=\d)")  # 只剥"v+数字"前缀（vault-1.0 这类 tag 不误伤）


def _to_beijing_naive_iso(raw: str) -> str:
    """GitHub ISO（...Z UTC）→ 北京时间 naive ISO「YYYY-MM-DDTHH:MM:SS」。

    项目时间口径统一北京时间 naive（API 规约 §4）；解析失败回退空串，
    由调用方回退 created_at / 当前时间。
    """
    s = (raw or "").strip()
    if not s:
        return ""
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_TZ).strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""


def _normalize_assets(rel: dict) -> list[dict]:
    """取 Release 的可下载资产：过滤 Source code 包与非法 URL（PRD §4.1-3）。

    GitHub API 的 assets 数组本身不含源码包，但按 PRD 显式过滤一次（防御
    未来 API 行为变化）；URL 白名单与资源中心资产录入一致（https://github.com/）。
    """
    out: list[dict] = []
    for a in rel.get("assets") or []:
        if not isinstance(a, dict):
            continue
        name = str(a.get("name") or "").strip()
        url = str(a.get("browser_download_url") or "").strip()
        if not name or not url:
            continue
        if name.lower().startswith("source code"):  # Source code (zip)/(tar.gz)
            continue
        if not url.startswith("https://github.com/"):
            continue
        out.append({"filename": name[:255], "url": url[:1024]})
    return out


def normalize_release(rel: dict) -> Optional[NormalizedRelease]:
    """API Release dict → NormalizedRelease；draft 过滤、字段缺失兜底。

    published_at 缺失（极早期 Release 可能只有 created_at）逐级回退：
    published_at → created_at → 空串（调用方再回退当前时间）。
    """
    if not isinstance(rel, dict):
        return None
    if rel.get("draft"):
        return None
    tag = str(rel.get("tag_name") or "").strip()
    if not tag:
        return None
    published = _to_beijing_naive_iso(str(rel.get("published_at") or "")) or _to_beijing_naive_iso(
        str(rel.get("created_at") or "")
    )
    return NormalizedRelease(
        tag=tag,
        version_no=_VERSION_NO_RE.sub("", tag, count=1),
        prerelease=bool(rel.get("prerelease")),
        published_at=published,
        changelog_md=str(rel.get("body") or ""),
        assets=_normalize_assets(rel),
    )


# ── 资产写入（双轨共用） ──────────────────────────────────────────


def _build_asset_rows(version_id: int, assets: list[dict], now: str) -> list[VersionAsset]:
    """assets → VersionAsset 行（不入 session）：第一个 main 且主资产，其余 additional。

    GitHub 资产没有"用途"概念，首资产即主下载（与后台手工录入
    "第一个 main 自动成主资产"的既有语义一致）。
    """
    rows: list[VersionAsset] = []
    for i, a in enumerate(assets[:ASSET_SYNC_MAX]):
        rows.append(
            VersionAsset(
                version_id=version_id,
                filename=a["filename"],
                url=a["url"],
                purpose="main" if i == 0 else "additional",
                sort=i,
                is_primary=1 if i == 0 else 0,
                status="visible",
                source=VERSION_SOURCE_GITHUB,
                create_time=now,
                update_time=now,
                deleted_at="",
            )
        )
    return rows


async def _soft_delete_synced_assets(db: AsyncSession, version_id: int, now: str) -> int:
    """软删该版本下 source=github 的资产（单版本覆盖口径：手动资产一律保留）。

    软删 + 摘掉主资产标记：主下载回落排序第一个可见资产（与手工删同语义）。
    """
    rows = (
        await db.execute(
            select(VersionAsset).where(
                VersionAsset.version_id == version_id,
                VersionAsset.source == VERSION_SOURCE_GITHUB,
                VersionAsset.deleted_at == "",
            )
        )
    ).scalars().all()
    for a in rows:
        a.deleted_at = now
        a.is_primary = 0
        a.update_time = now
    return len(rows)


# ── 批量同步（只增不改，幂等） ────────────────────────────────────


@dataclass
class BatchSyncResult:
    added: int = 0
    skipped: int = 0
    fetched: int = 0  # GitHub 返回的 Release 条数（未过滤 draft）
    warnings: list[str] | None = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def channel_from_prerelease(prerelease: bool) -> str:
    """prerelease → 渠道（PRD §4.3：true=Beta，false=Stable）。"""
    return CHANNEL_BETA if prerelease else CHANNEL_STABLE


async def sync_resource_batch(db: AsyncSession, resource: Resource, *, now: str) -> BatchSyncResult:
    """单资源批量同步：拉最新 20 条 → 过滤 draft → 按 Tag 判存 → 只新增。

    幂等性保证：本地（未软删）版本里已存在的 release_tag 一律跳过，已有版本的
    字段与资产零改动。同资源下 version 唯一（DB 约束）：GitHub tag 去 v 后若与
    现有版本号撞车（如本地手工建了 1.2.0 但没填 Tag），跳过并记 warning——
    不自动合并、不覆盖，等管理员手动对齐。
    """
    parsed = parse_github_repo(resource.github_repo_url)
    if parsed is None:
        raise GitHubSyncError("资源未配置合法的 GitHub 仓库地址（需 https://github.com/ 开头）")
    owner, repo = parsed
    rel_list = await _github_get_json(
        f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/releases?per_page={_RELEASES_PAGE_SIZE}"
    )
    if not isinstance(rel_list, list):
        raise GitHubSyncError("GitHub 返回了无法解析的数据")

    releases: list[NormalizedRelease] = []
    for rel in rel_list:
        n = normalize_release(rel)
        if n is not None:
            releases.append(n)

    result = BatchSyncResult(fetched=len(rel_list))

    # 本地已有 Tag/版本号集合（**全行扫描，含软删行**）：DB 唯一约束
    # uq_resource_version 作用于全部行。版本删除已改物理删除（2026-11-14，
    # resource_center.admin_delete_version），新数据不会再有软删行；这里的
    # 全行判存是防御性兜底——历史软删行（或任何直改库产生的行）若不判存，
    # 重新同步同 Tag 会撞约束 500（2026-11-14 测试环境实测过）。软删行视为
    # 已存在并 warning 提示，不自动复活。
    existing = (
        await db.execute(
            select(ResourceVersion.release_tag, ResourceVersion.version, ResourceVersion.deleted_at).where(
                ResourceVersion.resource_id == resource.id,
            )
        )
    ).all()
    existing_tags = {t for (t, _v, _d) in existing if t}
    existing_versions = {v for (_t, v, _d) in existing}
    deleted_tags = {t for (t, _v, d) in existing if t and d}

    # 资源级兼容元数据（新增版本默认继承，PRD §4.3「默认为空或继承资源级」取继承）
    gv_keys = (
        await db.execute(
            select(ResourceGameVersion.game_version_key).where(
                ResourceGameVersion.resource_id == resource.id
            )
        )
    ).scalars().all()
    pf_keys = (
        await db.execute(
            select(ResourcePlatform.platform_key).where(
                ResourcePlatform.resource_id == resource.id
            )
        )
    ).scalars().all()

    seen_tags: set[str] = set()
    # 「最新 Release」= GitHub /releases 列表的第一条非 draft（GitHub 已按发布
    # 时间倒序，releases[0] 即最新）——若它是 stable 渠道，自动设为该资源的
    # 最新稳定版（每资源唯一，先清后立）；prerelease 渠道为 beta，不设。
    latest_release_tag = releases[0].tag if releases else None

    for n in releases:
        if n.tag in seen_tags:  # 理论不会发生，防御重复响应
            continue
        seen_tags.add(n.tag)
        if n.tag in existing_tags:
            result.skipped += 1  # 幂等：已存在直接跳过，不做任何修改
            if n.tag in deleted_tags:
                result.warnings.append(
                    f"Tag {n.tag} 的版本已被管理员删除，同步保持删除状态不再新增；如需恢复请到回收站/数据库处理"
                )
                logger.info("批量同步跳过（软删行）：资源 %s Tag=%s", resource.id, n.tag)
            continue
        if n.version_no in existing_versions:
            result.skipped += 1
            result.warnings.append(
                f"Tag {n.tag} 对应版本号 {n.version_no} 已存在（本地未填该 Tag），已跳过；请手动核对"
            )
            logger.warning(
                "批量同步跳过：资源 %s Tag=%s 的版本号 %s 已被占用", resource.id, n.tag, n.version_no
            )
            continue

        is_latest = n.tag == latest_release_tag
        v = ResourceVersion(
            resource_id=resource.id,
            version=n.version_no,
            release_tag=n.tag,
            channel=channel_from_prerelease(n.prerelease),
            published_at=n.published_at or now,
            game_versions=json.dumps(list(gv_keys), ensure_ascii=False),
            platforms=json.dumps(list(pf_keys), ensure_ascii=False),
            side=resource.side or "both",
            changelog_md=n.changelog_md,
            status="visible",  # 2026-11-14 口径调整（覆盖原 PRD §4.3 默认隐藏）：同步即上架
            is_latest_stable=0,  # 最新稳定版标记在循环后统一转移（保证唯一性）
            source=VERSION_SOURCE_GITHUB,
            github_synced_at=now,
            create_time=now,
            update_time=now,
            deleted_at="",
        )
        db.add(v)
        await db.flush()  # 拿 v.id 建资产行（同一事务内，失败整体回滚）
        for a in _build_asset_rows(v.id, n.assets, now):
            db.add(a)
        if len(n.assets) > ASSET_SYNC_MAX:
            result.warnings.append(f"版本 {n.version_no} 资产超过 {ASSET_SYNC_MAX} 个，只保留前 {ASSET_SYNC_MAX} 个")
        # 最新 Release 且是 stable 渠道 → 本批新增里它就是最新稳定版（先清后立）
        if is_latest and v.channel == CHANNEL_STABLE:
            await db.execute(
                sqlalchemy_update(ResourceVersion)
                .where(ResourceVersion.resource_id == resource.id, ResourceVersion.is_latest_stable == 1)
                .values(is_latest_stable=0)
            )
            v.is_latest_stable = 1
            result.warnings.append(f"已将版本 {n.version_no}（最新 Release）自动设为最新稳定版")
        elif is_latest:
            result.warnings.append(
                f"最新 Release {n.version_no} 是 prerelease（Beta 渠道），未设置最新稳定版；请在正式版发布后重新同步"
            )
        existing_versions.add(n.version_no)
        result.added += 1
        logger.info(
            "批量同步新增：资源 %s Tag=%s → 版本 %s（资产 %d 个%s）", resource.id, n.tag, n.version_no,
            len(n.assets), "，最新稳定版" if v.is_latest_stable else "",
        )

    return result


# ── 单版本同步（精准覆盖，不碰手工元数据） ────────────────────────


# 单版本覆盖允许写的版本字段（红线：status / is_latest_stable / game_versions /
# platforms / side 永远不在此列——管理员手工元数据，PRD §4.3）
async def sync_version_single(db: AsyncSession, v: ResourceVersion, *, now: str) -> ResourceVersion:
    """按 v.release_tag 拉单条 Release 详情，覆盖 GitHub 字段 + 重建同步资产。

    覆盖字段：version（tag 去 v）、channel、published_at、changelog_md、资产；
    不动字段：release_tag（查询键）、status、is_latest_stable、game_versions、
    platforms、side。版本号冲突（覆盖后与同资源其他版本撞号）直接报错，
    由管理员手动解决——不静默改名。
    """
    tag = (v.release_tag or "").strip()
    if not tag:
        raise GitHubSyncError("该版本未填写 GitHub Tag，无法精准同步；请先在编辑中补填 Tag")
    resource_id = v.resource_id
    resource = (
        await db.execute(select(Resource).where(Resource.id == resource_id))
    ).scalar_one_or_none()
    parsed = parse_github_repo(resource.github_repo_url) if resource else None
    if parsed is None:
        raise GitHubSyncError("资源未配置合法的 GitHub 仓库地址（需 https://github.com/ 开头）")
    owner, repo = parsed

    try:
        rel = await _github_get_json(f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/releases/tags/{tag}")
    except GitHubNotFoundError:
        # PRD §3.2：Tag 在 GitHub 上不存在（可能已被删除）——文案单独给前端
        raise GitHubNotFoundError(f"Tag {tag} 在 GitHub 上不存在，可能已被删除")

    n = normalize_release(rel)
    if n is None:
        raise GitHubSyncError(f"Tag {tag} 对应的 Release 是草稿或数据异常，无法同步")

    new_no = n.version_no
    if new_no != v.version:
        # 查重**含软删行**（DB 唯一约束覆盖全部行——软删的同号版本同样会撞约束）
        dup = (
            await db.execute(
                select(ResourceVersion.id).where(
                    ResourceVersion.resource_id == v.resource_id,
                    ResourceVersion.version == new_no,
                    ResourceVersion.id != v.id,
                )
            )
        ).scalar_one_or_none()
        if dup is not None:
            raise GitHubSyncError(
                f"覆盖后的版本号 {new_no} 与该资源下已有版本冲突（可能含已删除版本），请先手动处理重名版本"
            )
        v.version = new_no
    # ── 覆盖区（仅 GitHub 直接提供的字段） ──
    v.channel = channel_from_prerelease(n.prerelease)
    if n.published_at:
        v.published_at = n.published_at
    v.changelog_md = n.changelog_md
    # ── 保留区：status / is_latest_stable / game_versions / platforms / side 不碰 ──

    # 资产完全覆盖：只替换 source=github 的行，手动录入资产保留（PRD §4.3）
    removed = await _soft_delete_synced_assets(db, v.id, now)
    new_rows = _build_asset_rows(v.id, n.assets, now)
    if new_rows:
        # 主资产回落：若删完同步资产后已无主资产（手动资产也没设主），首条新资产顶上
        primary_left = (
            await db.execute(
                select(func.count())
                .select_from(VersionAsset)
                .where(
                    VersionAsset.version_id == v.id,
                    VersionAsset.is_primary == 1,
                    VersionAsset.deleted_at == "",
                )
            )
        ).scalar_one()
        if primary_left == 0:
            new_rows[0].is_primary = 1
    for a in new_rows:
        db.add(a)

    v.source = VERSION_SOURCE_GITHUB
    v.github_synced_at = now
    v.update_time = now
    logger.info(
        "单版本同步覆盖：版本 %s（Tag=%s）渠道=%s 资产 %d 个（替换 %d 条旧同步资产）",
        v.id, tag, v.channel, len(n.assets), removed,
    )
    return v
