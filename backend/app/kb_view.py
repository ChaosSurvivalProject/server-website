"""知识库 SSR 展示层：/wiki/*（FLPR-71，P0 影子验证，不切流）。

读取链路见 docs/知识库/wiki与知识库打通改造方案.md §5.7 / §5.8 / §5.9：
- 按完整 slug 从 kb_nodes 查已发布文档节点，content_md 经 markdown-it-py
  （tables / anchors / container `:::` / 站内链接改写）渲染成完整 HTML；
- head 的 canonical / OG / description / FAQPage JSON-LD 从 kb_nodes 生成，
  与 VitePress config.mts 的 transformHead 逐项对齐（不依赖 JS，供抓取）；
- GET /wiki/ 首页从导航树渲染；sitemap.xml 与 404 由后端生成；
- 页面级缓存 key = path + content_hash + index_version，热更新不重启。

本期只有一个知识库「默认知识库」：不出现 多库标识列 / 知识库切换 / 多库隔离抽象。
"""
import hashlib
import html
import json
import logging
import re
import threading
from collections import OrderedDict
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, select_autoescape
from markupsafe import Markup
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.container import container_plugin
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import KB
from .database import KBDocument, KBNode, get_db

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/wiki", tags=["wiki-ssr"])

# ── 与 VitePress config.mts 对齐的站点级常量 ───────────────────────
SITE_TITLE = "星穹旅驿 Wiki · 我的世界阵营生存服"
SITE_NAME = "星穹旅驿 我的世界阵营生存服"
SITE_DESCRIPTION = (
    "星穹旅驿 Wiki：我的世界 1.21 阵营服 / Java 基岩互通服务器文档，"
    "含进服指南、黎明誓约与暮夜同盟阵营玩法、1.21.11 生存服版本支持与服务器规则。"
)
OG_IMAGE = "https://xqly.xt91tv.shop/og-cover.png"
# 主题令牌 localStorage 键（与主站 / 旧 VitePress Wiki 同款，首屏同步写入）
THEME_STORAGE_KEY = "XQ_theme_vars_v2"

MAX_DEPTH = 5          # 递归 CTE 深度上限（§5.3 / §7 风险表）
CACHE_MAX_ENTRIES = 256
PAGE_CACHE: OrderedDict[str, str] = OrderedDict()
_CACHE_LOCK = threading.Lock()


# ── Markdown 渲染管线 ──────────────────────────────────────────────


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", (text or "").strip().lower())
    slug = re.sub(r"\s+", "-", slug)
    return slug or "section"


def _container_render(name: str):
    """container_plugin 的自定义渲染：`::: tip 提示` → 带标题的 custom-block。"""

    def render(self, tokens, idx, options, env):
        token = tokens[idx]
        if token.nesting == 1:
            token.attrJoin("class", name)
            token.attrJoin("class", "custom-block")
            params = (token.info or "").strip()
            if params.startswith(name):
                params = params[len(name):].strip()
            cls = html.escape(token.attrGet("class") or "", quote=True)
            if params:
                return (
                    f'<div class="{cls}">'
                    f'<p class="custom-block-title">{html.escape(params)}</p>'
                )
            return f'<div class="{cls}">'
        return self.renderToken(tokens, idx, options, env)

    return render


_md = MarkdownIt("default", {"html": True}).enable("table")
_md.use(anchors_plugin, min_level=1, max_level=6, permalink=True, permalinkSymbol="#")
for _container_name in ("tip", "warning", "danger", "details", "info"):
    _md.use(container_plugin, _container_name)
    _md.add_render_rule(
        f"container_{_container_name}_open", _container_render(_container_name)
    )


def _link_open(tokens, idx, options, env):
    """站内链接 `/xxx/` → `/wiki/xxx/`（对齐旧 VitePress base: '/wiki'）。

    图片 `/doc-image/*` 与 API / 外链不动；`//` 协议相对链接也不动。
    """
    token = tokens[idx]
    href = token.attrGet("href") or ""
    if href.startswith("/") and not href.startswith("//"):
        if not href.startswith(("/wiki/", "/doc-image/", "/api/", "/favicon", "/og-cover")):
            token.attrSet("href", "/wiki" + href)
    return _md.renderer.renderToken(tokens, idx, options, env)


_md.renderer.rules["link_open"] = _link_open


def _strip_frontmatter(text: str) -> str:
    """去掉 YAML frontmatter（content_md 通常已清洗，这里做防御性兜底）。"""
    if not text.startswith("---"):
        return text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return "".join(lines[i + 1:]).lstrip("\n")
    return text


def _render_markdown(content_md: str) -> tuple[str, list[dict]]:
    """返回 (html, toc)；toc 项形如 {level,title,anchor}。"""
    source = _strip_frontmatter(content_md or "")
    env: dict = {}
    tokens = _md.parse(source, env)
    toc: list[dict] = []
    for i, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        inline = tokens[i + 1] if i + 1 < len(tokens) else None
        raw_title = inline.content if inline and inline.type == "inline" else ""
        title = re.sub(r"<[^>]+>", "", raw_title).strip()
        anchor = token.attrGet("id") or _slugify(title)
        toc.append({"level": int(token.tag[1]), "title": title, "anchor": anchor})
    return _md.renderer.render(tokens, _md.options, env), toc


# ── head 生成（与 config.mts transformHead 对齐） ──────────────────

_THEME_SCRIPT = (
    "<script>(function(){try{var v=localStorage.getItem('" + THEME_STORAGE_KEY +
    "');if(!v)return;var s=JSON.parse(v);var r=document.documentElement;"
    "for(var k in s){if(Object.prototype.hasOwnProperty.call(s,k))"
    "r.style.setProperty(k,s[k]);}}catch(e){}})();</script>"
)

_WEBSITE_JSON_LD = json.dumps(
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "星穹旅驿 我的世界阵营生存服",
        "alternateName": "星穹旅驿Wiki",
        "url": "https://xqly.xt91tv.shop/",
        "inLanguage": "zh-CN",
        "description": "我的世界 1.21 阵营服：Java / 基岩互通的 MC 双端互通服，黎明誓约与暮夜同盟阵营对抗，1.21.11 生存服。",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": "https://xqly.xt91tv.shop/forum?q={search_term_string}",
            },
            "query-input": "required name=search_term_string",
        },
    },
    ensure_ascii=False,
    separators=(",", ":"),
)


def _page_url(slug: str) -> str:
    """canonical / sitemap 用的绝对 URL。"""
    return f"{KB.site_url}/wiki/{slug.strip('/')}/" if slug.strip("/") else f"{KB.site_url}/wiki/"


def _wiki_path(slug: str) -> str:
    """站内导航链接：与 VitePress base '/wiki' 一致，跨端分享可用。"""
    return f"/wiki/{slug.strip('/')}/"


def _page_description(title: str, description: str) -> str:
    if description and description != SITE_TITLE and description != SITE_DESCRIPTION:
        return description
    return (
        f"{title}：星穹旅驿我的世界 1.21 阵营服文档，包含 Java / 基岩互通进服指南、"
        "黎明誓约与暮夜同盟阵营玩法、1.21.11 生存服版本支持与服务器规则。"
    )


def _page_og_title(title: str) -> str:
    plain = title
    if plain.endswith(SITE_TITLE):
        plain = plain[: -len(SITE_TITLE)].rstrip(" |")
    return f"{plain} | {SITE_NAME}" if plain else SITE_NAME


def _faq_json_ld(raw: Optional[str]) -> str:
    """faq_json 存的是 JSON-LD 字符串；非法内容直接忽略，不打断页面。"""
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return ""
    if not isinstance(obj, dict) or obj.get("@type") != "FAQPage":
        return ""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# ── Jinja2 模板 ───────────────────────────────────────────────────

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<meta name="description" content="{{ description }}">
<link rel="canonical" href="{{ canonical }}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="星穹旅驿 我的世界阵营生存服">
<meta property="og:title" content="{{ ogTitle }}">
<meta property="og:description" content="{{ description }}">
<meta property="og:url" content="{{ canonical }}">
<meta property="og:image" content="{{ ogImage }}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ ogTitle }}">
<meta name="twitter:description" content="{{ description }}">
<meta name="twitter:image" content="{{ ogImage }}">
<script type="application/ld+json">{{ websiteLd }}</script>
{% if faqLd %}<script type="application/ld+json">{{ faqLd }}</script>
{% endif %}{{ themeScript }}
<style>
:root{--vp-c-brand-1:var(--brand-lt,#4caf50);--vp-c-brand-2:var(--brand-lt-hover,#43a047);--vp-c-brand-3:var(--brand-lt-active,#388e3c);--vp-c-brand-soft:var(--brand-lt-tint,#e8f5e9)}
html.dark{--vp-c-brand-1:var(--brand-dk,#66bb6a);--vp-c-brand-2:var(--brand-dk-hover,#7bc87f);--vp-c-brand-3:var(--brand-dk-active,#55a55a);--vp-c-brand-soft:var(--brand-dk-tint,rgba(102,187,106,.16))}
:root{--vp-c-bg:#fff;--vp-c-bg-alt:#f6f6f6;--vp-c-text-1:#213547;--vp-c-text-2:#476582;--vp-c-divider:#e2e2e2;--vp-c-border:#d0d7de}
html.dark{--vp-c-bg:#1b1b1f;--vp-c-bg-alt:#252529;--vp-c-text-1:#e6e6e6;--vp-c-text-2:#b0b0b0;--vp-c-divider:#3a3a3f;--vp-c-border:#3a3a3f}
*{box-sizing:border-box}
body{margin:0;background:var(--vp-c-bg);color:var(--vp-c-text-1);font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif;line-height:1.6}
a{color:var(--vp-c-brand-1);text-decoration:none}
a:hover{text-decoration:underline}
.topbar{display:flex;align-items:center;gap:16px;padding:10px 20px;border-bottom:1px solid var(--vp-c-divider);background:var(--vp-c-bg-alt);position:sticky;top:0;z-index:20}
.topbar .brand{font-weight:700;color:var(--vp-c-text-1);white-space:nowrap}
.topnav{display:flex;gap:16px;align-items:center;margin-left:auto;flex-wrap:wrap}
.topnav .more{display:none}
.theme-btn,.menu-btn{border:1px solid var(--vp-c-border);background:transparent;color:var(--vp-c-text-1);border-radius:6px;min-width:36px;min-height:36px;cursor:pointer}
.layout{display:grid;grid-template-columns:260px minmax(0,1fr) 220px;gap:24px;max-width:1280px;margin:0 auto;padding:24px}
.sidebar{border-right:1px solid var(--vp-c-divider);padding-right:12px}
.nav-list{list-style:none;margin:0;padding-left:14px}
.sidebar>.nav-list{padding-left:0}
.nav-list summary{cursor:pointer;font-weight:600;padding:4px 0;color:var(--vp-c-text-1)}
.nav-list li{margin:4px 0}
.nav-list a{display:block;padding:4px 6px;border-radius:6px;color:var(--vp-c-text-2)}
.nav-list a.active{background:var(--vp-c-brand-soft);color:var(--vp-c-brand-1)}
.main{min-width:0}
.content{overflow-wrap:anywhere}
.content img{max-width:100%;height:auto}
.content pre{overflow-x:auto;background:var(--vp-c-bg-alt);padding:12px;border-radius:8px}
.content table{display:block;max-width:100%;overflow-x:auto;border-collapse:collapse}
.content th,.content td{border:1px solid var(--vp-c-border);padding:6px 10px}
.content .header-anchor{opacity:.45;margin-left:.3em}
.custom-block{border-left:4px solid var(--vp-c-brand-1);background:var(--vp-c-brand-soft);padding:8px 14px;border-radius:6px;margin:12px 0}
.custom-block.warning{border-color:#e6a700;background:rgba(230,167,0,.12)}
.custom-block.danger{border-color:#e64646;background:rgba(230,70,70,.12)}
.custom-block-title{font-weight:700;margin:0 0 4px}
.toc{font-size:14px;border-left:1px solid var(--vp-c-divider);padding-left:12px;align-self:start;position:sticky;top:80px}
.toc-title{font-weight:700;margin-bottom:6px}
.toc ul{list-style:none;margin:0;padding-left:0}
.toc li{margin:4px 0}
.toc a{color:var(--vp-c-text-2)}
.toc-mobile{display:none}
.drawer-mask{display:none}
footer{border-top:1px solid var(--vp-c-divider);padding:16px 20px;text-align:center;color:var(--vp-c-text-2);font-size:13px}
@media (max-width:768px){
  .layout{grid-template-columns:1fr;padding:16px}
  .sidebar{position:fixed;left:0;top:0;bottom:0;width:85vw;max-width:320px;background:var(--vp-c-bg);z-index:40;transform:translateX(-100%);transition:transform .2s;overflow-y:auto;padding:56px 16px 16px;border-right:1px solid var(--vp-c-divider)}
  .sidebar.open{transform:translateX(0)}
  .drawer-mask.open{display:block;position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:30}
  .menu-btn{display:block}
  .toc{display:none}
  .toc-mobile{display:block;margin-bottom:16px;border:1px solid var(--vp-c-divider);border-radius:6px;padding:8px 12px}
  .topnav .nav-item{display:none}
  .topnav .more{display:inline-block}
}
@media (min-width:769px){.menu-btn{display:none}}
@media (max-width:480px){.topbar{padding:8px 12px;gap:8px}.layout{padding:12px}}
</style>
</head>
<body>
<header class="topbar">
<button class="menu-btn" type="button" aria-label="目录" onclick="toggleDrawer()">☰</button>
<a class="brand" href="/wiki/">星穹旅驿 Wiki</a>
<nav class="topnav">
<a class="nav-item" href="/wiki/">主页</a>
<a class="nav-item" href="https://www.ilanzou.com/s/f6FnIguj" target="_blank" rel="noopener">资源下载（网盘）</a>
<a class="nav-item" href="https://simpfun.cn/auth?type=register&code=303249736" target="_blank" rel="noopener">简幻欢</a>
<a class="nav-item" href="https://minekuai.com/index/register?inviteCode=lwpnw2K" target="_blank" rel="noopener">麦块联机</a>
<a class="more" href="/wiki/">更多</a>
</nav>
<button class="theme-btn" type="button" aria-label="切换主题" onclick="cycleTheme()">◐</button>
</header>
<div class="layout">
<aside class="sidebar" id="sidebar">{{ navHtml }}</aside>
<div class="drawer-mask" id="drawerMask" onclick="toggleDrawer()"></div>
<main class="main">
{{ tocMobileHtml }}
<article class="content">{{ body }}</article>
</main>
<aside class="toc">{{ tocHtml }}</aside>
</div>
<footer>联系邮箱: <a href="mailto:3896301937@qq.com">3896301937@qq.com</a><br>© 2025-2026 星穹旅驿 Minecraft 服务器 | 本服务器与Mojang及Microsoft无关</footer>
<script>
function toggleDrawer(){var s=document.getElementById('sidebar'),m=document.getElementById('drawerMask');s.classList.toggle('open');m.classList.toggle('open');}
function cycleTheme(){var r=document.documentElement,d=r.classList.contains('dark');if(d){r.classList.remove('dark');localStorage.setItem('wiki-theme','light');}else{r.classList.add('dark');localStorage.setItem('wiki-theme','dark');}}
(function(){try{var t=localStorage.getItem('wiki-theme');if(t==='dark')document.documentElement.classList.add('dark');}catch(e){}})();
document.querySelectorAll('.sidebar a').forEach(function(a){a.addEventListener('click',function(){var s=document.getElementById('sidebar'),m=document.getElementById('drawerMask');s.classList.remove('open');m.classList.remove('open');a.classList.add('active');});});
</script>
</body>
</html>
"""

_JINJA = Environment(autoescape=select_autoescape(["html"]))
_TEMPLATE = _JINJA.from_string(PAGE_TEMPLATE)


def _render_page(
    *,
    title: str,
    description: str,
    canonical: str,
    og_title: str,
    faq_json: Optional[str],
    body: str,
    nav_html: str,
    toc_html: str,
    toc_mobile_html: str,
) -> str:
    return _TEMPLATE.render(
        title=title,
        description=description,
        canonical=canonical,
        ogTitle=og_title,
        faqLd=Markup(_faq_json_ld(faq_json)),
        websiteLd=Markup(_WEBSITE_JSON_LD),
        themeScript=Markup(_THEME_SCRIPT),
        ogImage=OG_IMAGE,
        body=Markup(body),
        navHtml=Markup(nav_html),
        tocHtml=Markup(toc_html),
        tocMobileHtml=Markup(toc_mobile_html),
    )


# ── 导航树（递归 CTE，过滤整支 deleted_at） ───────────────────────

_NAV_CTE = """
WITH RECURSIVE tree(id, parent_id, node_type, title, slug, sort_order, depth, ord) AS (
    SELECT id, parent_id, node_type, title, slug, sort_order, 0,
           printf('%04d', sort_order)
    FROM kb_nodes
    WHERE parent_id IS NULL AND deleted_at IS NULL
      AND (node_type = 'folder' OR published = 1)
    UNION ALL
    SELECT n.id, n.parent_id, n.node_type, n.title, n.slug, n.sort_order,
           t.depth + 1, t.ord || '/' || printf('%04d', n.sort_order)
    FROM kb_nodes n
    JOIN tree t ON n.parent_id = t.id
    WHERE n.deleted_at IS NULL AND t.depth < :max_depth
      AND (n.node_type = 'folder' OR n.published = 1)
)
SELECT id, parent_id, node_type, title, slug, sort_order, depth, ord
FROM tree ORDER BY ord
"""


async def _nav_rows(db: AsyncSession) -> list[dict]:
    result = await db.execute(text(_NAV_CTE), {"max_depth": MAX_DEPTH})
    return [
        {
            "id": r[0], "parentId": r[1], "nodeType": r[2], "title": r[3],
            "slug": r[4], "sortOrder": r[5], "depth": r[6],
        }
        for r in result
    ]


async def build_nav(db: AsyncSession) -> list[dict]:
    """公开导航树：camelCase 嵌套 JSON，已过滤软删除整支与所有祖先（§5.8）。"""
    rows = await _nav_rows(db)
    by_parent: dict[Optional[int], list[dict]] = {}
    for row in rows:
        node = {
            "id": row["id"],
            "title": row["title"],
            "nodeType": row["nodeType"],
            "url": _wiki_path(row["slug"]) if row["nodeType"] == "doc" else None,
            "children": [],
        }
        by_parent.setdefault(row["parentId"], []).append(node)

    def attach(parent_id: Optional[int]) -> list[dict]:
        children = by_parent.get(parent_id, [])
        for child in children:
            child["children"] = attach(child["id"])
        return children

    return attach(None)


def _nav_html(nodes: list[dict], current_id: Optional[int] = None) -> str:
    parts = ['<ul class="nav-list">']
    for node in nodes:
        title = html.escape(node["title"] or "")
        if node["nodeType"] == "folder":
            parts.append(
                f'<li><details open><summary>{title}</summary>'
                + _nav_html(node["children"], current_id)
                + "</details></li>"
            )
        else:
            active = ' class="active"' if node["id"] == current_id else ""
            url = html.escape(node.get("url") or "#", quote=True)
            parts.append(f'<li><a href="{url}"{active}>{title}</a></li>')
    parts.append("</ul>")
    return "".join(parts)


def _toc_html(toc: list[dict], *, mobile: bool = False) -> str:
    if not toc:
        return ""
    items = "".join(
        f'<li><a href="#{html.escape(t["anchor"], quote=True)}">'
        f'{html.escape(t["title"])}</a></li>'
        for t in toc
    )
    body = f"<ul>{items}</ul>"
    if mobile:
        return f'<details class="toc-mobile"><summary>本页目录</summary>{body}</details>'
    return f'<div class="toc-title">本页目录</div>{body}'


# ── 页面缓存 ──────────────────────────────────────────────────────


def _cache_get(key: str) -> Optional[str]:
    with _CACHE_LOCK:
        value = PAGE_CACHE.get(key)
        if value is not None:
            PAGE_CACHE.move_to_end(key)
        return value


def _cache_set(key: str, value: str) -> None:
    with _CACHE_LOCK:
        PAGE_CACHE[key] = value
        PAGE_CACHE.move_to_end(key)
        while len(PAGE_CACHE) > CACHE_MAX_ENTRIES:
            PAGE_CACHE.popitem(last=False)


async def _index_version(db: AsyncSession) -> str:
    row = (
        await db.execute(
            text("SELECT value FROM kb_settings WHERE key = 'index_version'")
        )
    ).first()
    return row[0] if row else "0"


# ── 路由 ──────────────────────────────────────────────────────────


@router.get("/sitemap.xml", response_class=Response)
async def wiki_sitemap(db: AsyncSession = Depends(get_db)):
    """sitemap.xml 由后端生成，覆盖全部已发布文档节点（替代 VitePress 构建期产物）。"""
    rows = (
        await db.execute(
            select(KBNode.slug)
            .where(
                KBNode.node_type == "doc",
                KBNode.published == 1,
                KBNode.deleted_at.is_(None),
            )
            .order_by(KBNode.slug)
        )
    ).scalars().all()
    urls = "".join(
        f"<url><loc>{html.escape(_page_url(slug))}</loc></url>" for slug in rows
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + urls
        + "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/", response_class=HTMLResponse)
async def wiki_home(request: Request, db: AsyncSession = Depends(get_db)):
    """首页：从导航树渲染目录入口（§5.7）。"""
    nav = await build_nav(db)
    version = await _index_version(db)
    nav_hash = hashlib.md5(
        json.dumps(nav, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cache_key = f"/|{nav_hash}|{version}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return HTMLResponse(cached)

    nav_html = _nav_html(nav)
    body = (
        "<h1>星穹旅驿 Wiki</h1>"
        "<p>我的世界 1.21 阵营服 / Java 基岩互通服务器文档站：进服指南、"
        "黎明誓约与暮夜同盟阵营玩法、版本支持与服务器规则。</p>"
        + nav_html
    )
    rendered = _render_page(
        title=SITE_TITLE,
        description=SITE_DESCRIPTION,
        canonical=_page_url(""),
        og_title=SITE_NAME,
        faq_json=None,
        body=body,
        nav_html=nav_html,
        toc_html="",
        toc_mobile_html="",
    )
    _cache_set(cache_key, rendered)
    return HTMLResponse(rendered)


@router.get("/{path:path}", response_class=HTMLResponse)
async def wiki_page(
    path: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """按完整 slug 查已发布文档节点并 SSR；未命中返回后端生成的 404 HTML。"""
    slug = (path or "").strip("/")
    row = (
        await db.execute(
            select(KBNode, KBDocument)
            .join(KBDocument, KBNode.document_id == KBDocument.id)
            .where(
                KBNode.node_type == "doc",
                KBNode.slug == slug,
                KBNode.published == 1,
                KBNode.deleted_at.is_(None),
            )
        )
    ).first()
    if row is None:
        return HTMLResponse(_not_found_html(nav_html=_nav_html(await build_nav(db))), status_code=404)

    node, document = row
    # 祖先整支软删除时，子节点同样不可访问（§7 风险表）
    if await _has_deleted_ancestor(db, node):
        return HTMLResponse(_not_found_html(nav_html=_nav_html(await build_nav(db))), status_code=404)

    version = await _index_version(db)
    content_hash = document.content_hash or hashlib.md5(
        (document.content_md or "").encode("utf-8")
    ).hexdigest()
    # revision 参与缓存 key：改 title/description/faq/slug 等 SEO 字段后立即刷新页面，
    # 但不必 bump index_version（避免无谓触发向量索引重建）。
    cache_key = f"{slug}|{content_hash}|{version}|{node.revision}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return HTMLResponse(cached)

    body_html, toc = _render_markdown(document.content_md or "")
    nav = await build_nav(db)
    rendered = _render_page(
        title=node.title,
        description=node.description or "",
        canonical=_page_url(slug),
        og_title=_page_og_title(node.title),
        faq_json=node.faq_json,
        body=body_html,
        nav_html=_nav_html(nav, current_id=node.id),
        toc_html=_toc_html(toc),
        toc_mobile_html=_toc_html(toc, mobile=True),
    )
    _cache_set(cache_key, rendered)
    return HTMLResponse(rendered)


async def _has_deleted_ancestor(db: AsyncSession, node: KBNode) -> bool:
    parent_id = node.parent_id
    for _ in range(MAX_DEPTH):
        if parent_id is None:
            return False
        parent = (
            await db.execute(select(KBNode).where(KBNode.id == parent_id))
        ).scalar_one_or_none()
        if parent is None or parent.deleted_at is not None:
            return True
        parent_id = parent.parent_id
    return False


def _not_found_html(*, nav_html: str) -> str:
    return _render_page(
        title=f"页面未找到 | {SITE_NAME}",
        description=SITE_DESCRIPTION,
        canonical=_page_url(""),
        og_title=f"页面未找到 | {SITE_NAME}",
        faq_json=None,
        body="<h1>404 · 页面未找到</h1><p>这个页面不存在或已被移除，请从左侧目录继续浏览。</p>",
        nav_html=nav_html,
        toc_html="",
        toc_mobile_html="",
    )
