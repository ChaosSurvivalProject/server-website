"""站点配置模块（系统管理-网站配置；首页个性化元素可配置化）。

数据形态：site_settings KV 表（app/database.py SiteSetting），键集合由
FIELD_DEFS 定义、后台整包读写，不做自由键（防脏数据、防未知键注入）。

接口：
- GET  /api/site-config            公开：首页渲染读取（未配置的键回默认值）
- GET  /api/site-config/admin      管理员：后台表单回显（全部键，含未配置）
- PUT  /api/site-config/admin      管理员：整包保存（仅接受已知键，逐键校验）

设计要点：
- 首页兜底：DB 无该键时返回 DEFAULTS 里的值，前端拉取失败也不开天窗
  （前端另有内置默认值，见 frontend/src/views/Home.vue 的 HOME_DEFAULT_CONFIG）。
- 高亮标记：富文本字段允许 [[绿字]] {{紫字}} 两段式标记，前端解析成
  主题色/紫色 span；保存时校验标记必须成对闭合，防半截标记破坏渲染。
- 图片字段存 /api/announcement/uploads/... 相对 URL（复用公告上传接口，
  零 nginx 改动，见 app/uploads.py）；置空则前端回退打包内默认图。
- 布尔语义用 int（项目规约）：banner.enabled 存 "0"/"1"。
"""
import json
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import require_admin
from .crud import _TZ as BEIJING_TZ
from .database import SiteSetting, get_db

logger = logging.getLogger("uvicorn.error")

router = APIRouter()


# ── 键定义（字段名与含义的唯一权威；后台表单/前端默认值同源于此口径） ──
# type: text=单行 / textarea=多行 / image=图片URL / int=正整数 / bool=开关
# mark: 允许 [[..]] {{..}} 高亮标记的富文本字段
FIELD_DEFS: dict[str, dict[str, Any]] = {
    # 顶部内测横幅（常驻显示）
    "banner.enabled": {"type": "bool", "label": "横幅开关"},
    "banner.text": {"type": "textarea", "label": "横幅文案", "max": 200},
    "banner.linkText": {"type": "text", "label": "横幅链接文字", "max": 20},
    "banner.linkUrl": {"type": "text", "label": "横幅链接地址", "max": 255},
    # Hero 区
    "hero.badgeIcon": {"type": "text", "label": "徽章年份", "max": 20},
    "hero.badgeText": {"type": "text", "label": "徽章团队名", "max": 30},
    "hero.title": {"type": "text", "label": "主标题", "max": 60, "mark": True},
    "hero.subtitle": {"type": "text", "label": "副标题", "max": 80, "mark": True},
    "hero.features": {"type": "textarea", "label": "特性标签（每行一个）", "max": 400},
    "hero.description": {"type": "textarea", "label": "服务器介绍", "max": 600, "mark": True},
    "hero.stat1Number": {"type": "text", "label": "统计1数值", "max": 20},
    "hero.stat1Label": {"type": "text", "label": "统计1名称", "max": 20},
    "hero.stat2Number": {"type": "text", "label": "统计2数值", "max": 20},
    "hero.stat2Label": {"type": "text", "label": "统计2名称", "max": 20},
    "hero.stat3Number": {"type": "text", "label": "统计3数值", "max": 20},
    "hero.stat3Label": {"type": "text", "label": "统计3名称", "max": 20},
    "hero.stat4Number": {"type": "text", "label": "统计4数值", "max": 20},
    "hero.stat4Label": {"type": "text", "label": "统计4名称", "max": 20},
    # 宣传视频卡片（hero 右侧）
    "video.title": {"type": "text", "label": "宣传视频标题", "max": 60},
    "video.url": {"type": "text", "label": "宣传视频链接", "max": 255},
    "video.cover": {"type": "image", "label": "宣传视频封面图"},
    # 阵营海报区（section.enabled=false 时首页隐藏整个阵营海报区块）
    "faction.enabled": {"type": "bool", "label": "阵营海报开关"},
    "faction.dawnName": {"type": "text", "label": "黎明誓约名称", "max": 30},
    "faction.dawnSlogan": {"type": "text", "label": "黎明誓约口号", "max": 60},
    "faction.dawnCall": {"type": "text", "label": "黎明誓约号召语", "max": 60},
    "faction.dawnImage": {"type": "image", "label": "黎明誓约海报图"},
    "faction.duskName": {"type": "text", "label": "暮夜同盟名称", "max": 30},
    "faction.duskSlogan": {"type": "text", "label": "暮夜同盟口号", "max": 60},
    "faction.duskCall": {"type": "text", "label": "暮夜同盟号召语", "max": 60},
    "faction.duskImage": {"type": "image", "label": "暮夜同盟海报图"},
    # 玩家社区轮播图（bbs-1/2/3 的替换位；空 = 用内置默认图）
    "forum.carouselImages": {"type": "textarea", "label": "社区轮播图（每行一个图片 URL）", "max": 1500},
    # 页脚（全站 footer，App.vue 渲染；enabled=false 时整个页脚隐藏）
    "footer.enabled": {"type": "bool", "label": "页脚开关"},
    "footer.sponsorTitle": {"type": "text", "label": "赞助栏标题", "max": 40},
    "footer.sponsorLogo": {"type": "image", "label": "赞助商 Logo 图"},
    "footer.sponsorDesc": {"type": "textarea", "label": "赞助栏描述（每行一条）", "max": 200},
    "footer.sponsorLink": {"type": "text", "label": "赞助商链接", "max": 255},
    # 链接栏目：每行一条「标题|链接」，后台所见即所存
    "footer.columns": {"type": "textarea", "label": "链接栏目（每行：栏目名|链接文字|链接地址）", "max": 1200},
    "footer.copyright": {"type": "textarea", "label": "版权信息（每行一条）", "max": 400},
}

# 默认值：与改造前首页硬编码逐字一致（升级后未配置 = 页面行为不变）
DEFAULTS: dict[str, str] = {
    "banner.enabled": "1",
    "banner.text": "🔔 全新阵营对战玩法内测开启，名额有限 · 申请时间 2026-09-21 ~ 2026-10-07",
    "banner.linkText": "申请内测",
    "banner.linkUrl": "/faction-beta",
    "hero.badgeIcon": "@2025-2026",
    "hero.badgeText": "星穹旅驿团队",
    "hero.title": "欢迎来到 [[星穹旅驿]]",
    "hero.subtitle": "在这里，体验[[阵营对抗]]乱世生存",
    "hero.features": "阵营对抗\n多端互通\n友好社区\n超多插件玩法",
    "hero.description": (
        "星穹旅驿是一个以阵营对抗为核心的乱世生存服务器。大崩裂之后，星穹界长夜与残阳交替："
        "[[黎明誓约]]立志重建秩序、点燃曙光灯塔，{{暮夜同盟}}则拥抱长夜、信奉强者为尊。"
        "选择你的立场，在这场不会终结的拉锯战中，把世界改成你想要的样子。"
        "基于 Geyser + Velocity + Paper 1.21.11 核心技术，实现 Java/基岩多端互通。"
    ),
    "hero.stat1Number": "114514",
    "hero.stat1Label": "注册玩家",
    "hero.stat2Number": "24/7",
    "hero.stat2Label": "稳定运行",
    "hero.stat3Number": "30+",
    "hero.stat3Label": "插件玩法",
    "hero.stat4Number": "6",
    "hero.stat4Label": "管理团队人数",
    "video.title": "星穹旅驿服务器宣传视频",
    "video.url": "https://www.bilibili.com/video/BV1aN6CBgEL3",
    "video.cover": "",
    "faction.enabled": "1",
    "faction.dawnName": "黎明誓约",
    "faction.dawnSlogan": "以光为界，守土求生；火种不熄，黎明必至。",
    "faction.dawnCall": "加入黎明誓约——你愿意成为火种吗？",
    "faction.dawnImage": "",
    "faction.duskName": "暮夜同盟",
    "faction.duskSlogan": "长夜将至，强者为尊；既然乱世，就燃得更旺。",
    "faction.duskCall": "加入暮夜同盟——你愿意在长夜中狩猎吗？",
    "faction.duskImage": "",
    "forum.carouselImages": "",
    "footer.enabled": "1",
    "footer.sponsorTitle": "本项目由快跑云集团扶持",
    "footer.sponsorLogo": "",
    "footer.sponsorDesc": "快跑云集团 · 基础AIDC服务商\n定义下一代AIDC算力基线",
    "footer.sponsorLink": "https://www.fastrun.com.cn/",
    "footer.columns": (
        "服务器信息|首页|/\n"
        "服务器信息|服务器公告|/announcements\n"
        "社区|进入社区|/forum\n"
        "社区|发布文章|/forum/new\n"
        "活动信息|阵营内测|/faction-beta\n"
        "联系我们|联系服主|mailto:3896301937@qq.com\n"
        "联系我们|加入我们|https://jq.qq.com/?_wv=1027194278"
    ),
    "footer.copyright": (
        "2025-2026 星穹旅驿 Minecraft服务器\n"
        "| 本服务器与Mojang及Microsoft无关\n"
        "联系我们: 3896301937@qq.com\n"
        "加入QQ群: 942235691"
    ),
}


def _now_iso() -> str:
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _validate_marks(value: str) -> None:
    """校验高亮标记成对闭合（[[..]] 与 {{..}} 不得交叉嵌套、不得半截）。

    只做配对性检查不解析内容：解析在前端（见 frontend/src/utils/highlight.js），
    后端把关防半截标记入库。
    """
    for open_mark, close_mark in (("[[", "]]"), ("{{", "}}")):
        count_open = value.count(open_mark)
        count_close = value.count(close_mark)
        if count_open != count_close:
            raise HTTPException(
                status_code=400,
                detail=f"高亮标记不闭合：{open_mark} 出现 {count_open} 次但 {close_mark} 出现 {count_close} 次",
            )


def _validate_value(key: str, value: str) -> str:
    """逐键校验并规范化；返回规范化后的存储值。"""
    field = FIELD_DEFS.get(key)
    if field is None:
        raise HTTPException(status_code=400, detail=f"未知的配置键：{key}")
    value = (value or "").strip()
    ftype = field["type"]
    if ftype == "bool":
        if value not in ("0", "1"):
            raise HTTPException(status_code=400, detail=f"{field['label']} 只能为开或关")
        return value
    if ftype == "int":
        if not value.isdigit() or int(value) < 0:
            raise HTTPException(status_code=400, detail=f"{field['label']} 必须为非负整数")
        return value
    # text / textarea / image：长度上限 + 富文本字段校验标记闭合
    max_len = field.get("max", 255)
    if len(value) > max_len:
        raise HTTPException(status_code=400, detail=f"{field['label']} 不能超过 {max_len} 字")
    if field.get("mark"):
        _validate_marks(value)
    return value


def _merge_defaults(rows: dict[str, str]) -> dict[str, str]:
    """DB 已配置值覆盖默认值；未配置的键回默认（首页不开天窗）。"""
    return {k: rows.get(k, DEFAULTS[k]) for k in FIELD_DEFS}


def _envelope(data: Any) -> dict[str, Any]:
    return {"code": 0, "message": "success", "data": data}


async def _load_rows(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(select(SiteSetting))
    return {row.key: row.value for row in result.scalars()}


@router.get("/site-config")
async def get_site_config(db: AsyncSession = Depends(get_db)):
    """公开：首页渲染读取（未配置键回默认值）。

    Response: {code, message, data: {banner: {...}, hero: {...}, video: {...}, faction: {...}, forum: {...}}}
    """
    rows = await _load_rows(db)
    merged = _merge_defaults(rows)
    grouped: dict[str, dict[str, Any]] = {
        "banner": {},
        "hero": {},
        "video": {},
        "faction": {},
        "forum": {},
        "footer": {},
    }
    for key, value in merged.items():
        section, field = key.split(".", 1)
        if field == "enabled":
            grouped[section][field] = value == "1"
        else:
            grouped[section][field] = value
    # 首页用不到 enabled 的分区不造空壳（video/faction/forum 无开关语义）
    return _envelope(grouped)


class SiteConfigUpdateRequest(BaseModel):
    """整包保存请求：settings 为 {完整键名: 值}，仅接受 FIELD_DEFS 已知键。"""

    settings: dict[str, str]


@router.get("/site-config/admin")
async def admin_get_site_config(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """管理员：后台表单回显（全部键；未配置的键给默认值便于直接改）。"""
    rows = await _load_rows(db)
    merged = _merge_defaults(rows)
    return _envelope({"settings": merged, "fields": [
        {"key": k, "label": v["label"], "type": v["type"], "max": v.get("max", 255), "mark": v.get("mark", False)}
        for k, v in FIELD_DEFS.items()
    ]})


@router.put("/site-config/admin")
async def admin_update_site_config(
    req: SiteConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """管理员：整包保存（先全量校验再落库，全部通过才写，避免半保存状态）。"""
    # 1) 全量校验（含未知键拒绝、bool 值域、长度上限、标记闭合）
    validated: dict[str, str] = {}
    for key, value in req.settings.items():
        validated[key] = _validate_value(key, str(value))
    missing = [k for k in FIELD_DEFS if k not in validated]
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少配置键：{', '.join(missing)}")

    # 2) 落库（upsert 已知键；site_settings 表极小，逐键 upsert 即可）
    now = _now_iso()
    try:
        result = await db.execute(select(SiteSetting).where(SiteSetting.key.in_(list(validated))))
        existing = {row.key: row for row in result.scalars()}
        for key, value in validated.items():
            row = existing.get(key)
            if row is None:
                db.add(SiteSetting(key=key, value=value, update_time=now))
            elif row.value != value:
                row.value = value
                row.update_time = now
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("保存站点配置失败: %s", e)
        raise HTTPException(status_code=500, detail="保存站点配置失败")
    logger.info("站点配置已更新（%d 个键）", len(validated))
    return _envelope({"updated": len(validated)})
