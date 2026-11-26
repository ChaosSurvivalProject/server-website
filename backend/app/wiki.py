"""Wiki 动态文档模块：后台「内容运营 - Wiki 文档/文件」。

main.py 统一挂 /api → 对外路径 /api/wiki/*。静态 VitePress 目录仍是知识库
(kb_sync.py) 的单一数据源；本模块只管理「动态文档」——后台写完即时在 Wiki
站点的动态文档页可见，不需要重新构建静态站、不需要重启后端。

接口一览（全部遵循 {code, message, data} 包络）：

  公开：
    GET  /api/wiki/documents              已发布文档列表（Wiki 动态页读取）
    GET  /api/wiki/documents/{id}         已发布文档详情
  管理员（require_admin）：
    GET    /api/wiki/admin/documents      分页列表（keyword / category / published）
    GET    /api/wiki/admin/documents/{id} 编辑回填
    POST   /api/wiki/admin/documents      新建
    PUT    /api/wiki/admin/documents/{id} 编辑
    DELETE /api/wiki/admin/documents/{id} 删除
    POST   /api/wiki/admin/upload         上传附件（图片/文档/压缩包）
    GET    /api/wiki/admin/files          已上传附件列表
    DELETE /api/wiki/admin/files          删除附件（query: path）
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import require_admin
from .crud import _TZ
from .database import WikiDocument, get_db
from .uploads import delete_wiki_file, list_wiki_files, save_wiki_file

router = APIRouter()

# 与 Wiki 侧边栏分区对齐的枚举；公开接口用它做分类筛选。
CATEGORIES = ("for-new", "management", "develop", "about", "other")
CATEGORY_LABELS = {
    "for-new": "萌新指南",
    "management": "服务器管理",
    "develop": "服务器建设",
    "about": "站点公告",
    "other": "其他",
}


def _ok(data, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


def _now() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _doc_out(doc: WikiDocument) -> dict:
    return {
        "id": doc.id,
        "slug": doc.slug,
        "title": doc.title,
        "category": doc.category,
        "categoryLabel": CATEGORY_LABELS.get(doc.category, "其他"),
        "summary": doc.summary,
        "content": doc.content,
        "author": doc.author,
        "isPublished": doc.is_published,
        "createTime": doc.create_time,
        "updateTime": doc.update_time,
    }


def _list_out(doc: WikiDocument) -> dict:
    """列表项不下发正文，避免一次拉全量 Markdown。"""
    item = _doc_out(doc)
    item.pop("content", None)
    return item


# ── 请求体（对外 camelCase，与 admin-frontend/src/api/wiki.ts 对齐） ──
class WikiDocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    category: str = "other"
    summary: str = Field(default="", max_length=500)
    content: str = Field(default="", max_length=200000)
    author: str = Field(default="", max_length=64)
    isPublished: int = Field(default=1, ge=0, le=1)


def _validate(payload: WikiDocumentIn) -> WikiDocumentIn:
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")
    slug = payload.slug.strip().strip("/")
    if not slug:
        raise HTTPException(status_code=400, detail="访问标识不能为空")
    if not all(part and all(c.isalnum() or c in "-_" for c in part) for part in slug.split("/")):
        raise HTTPException(status_code=400, detail="访问标识只能包含字母、数字、连字符、下划线和斜杠")
    payload.slug = slug
    if payload.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="分类不合法")
    return payload


# ══════════ 公开接口（Wiki 动态文档页读取） ══════════


@router.get("/wiki/documents")
async def public_documents(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WikiDocument).where(WikiDocument.is_published == 1)
    if category and category in CATEGORIES:
        stmt = stmt.where(WikiDocument.category == category)
    stmt = stmt.order_by(WikiDocument.update_time.desc(), WikiDocument.id.desc())
    rows = (await db.execute(stmt)).scalars().all()
    items = []
    for row in rows:
        item = _list_out(row)
        if not item["summary"]:
            # 没写摘要时抓正文首个非空段落，避免动态文档页出现空卡片
            lines = [ln.strip() for ln in row.content.splitlines() if ln.strip()]
            item["summary"] = " ".join(lines[:2]).replace("#", "").replace("*", "")[:120]
        items.append(item)
    return _ok(items)


@router.get("/wiki/documents/{doc_id}")
async def public_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(WikiDocument, doc_id)
    if row is None or row.is_published != 1:
        raise HTTPException(status_code=404, detail="文档不存在或未发布")
    return _ok(_doc_out(row))


# ══════════ 管理接口 ══════════


@router.get("/wiki/admin/documents")
async def admin_documents(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: str = Query(""),
    category: Optional[str] = Query(None),
    published: Optional[int] = Query(None, ge=0, le=1),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    where = []
    if keyword.strip():
        kw = f"%{keyword.strip()}%"
        where.append(WikiDocument.title.like(kw) | WikiDocument.slug.like(kw))
    if category and category in CATEGORIES:
        where.append(WikiDocument.category == category)
    if published is not None:
        where.append(WikiDocument.is_published == published)

    # SQLAlchemy 2.0 中 .where(None) 会生成 WHERE NULL → 永远查不到；空条件必须用 true()
    cond = and_(*where) if where else true()
    total = (await db.execute(select(func.count()).select_from(WikiDocument).where(cond))).scalar_one()
    rows = (
        await db.execute(
            select(WikiDocument)
            .where(cond)
            .order_by(WikiDocument.update_time.desc(), WikiDocument.id.desc())
            .offset((page - 1) * pageSize)
            .limit(pageSize)
        )
    ).scalars().all()
    return _ok({
        "items": [_list_out(row) for row in rows],
        "page": page,
        "pageSize": pageSize,
        "total": total,
        "totalPages": (total + pageSize - 1) // pageSize,
    })


@router.get("/wiki/admin/documents/{doc_id}")
async def admin_document_detail(
    doc_id: int,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(WikiDocument, doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _ok(_doc_out(row))


@router.post("/wiki/admin/documents")
async def admin_document_create(
    payload: WikiDocumentIn,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    payload = _validate(payload)
    exists = await db.execute(select(WikiDocument.id).where(WikiDocument.slug == payload.slug))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="该访问标识已存在")
    now = _now()
    row = WikiDocument(
        slug=payload.slug,
        title=payload.title.strip(),
        category=payload.category,
        summary=payload.summary.strip(),
        content=payload.content,
        author=(_admin.username if getattr(_admin, "username", None) else payload.author),
        is_published=payload.isPublished,
        create_time=now,
        update_time=now,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _ok(_doc_out(row), "创建成功")


@router.put("/wiki/admin/documents/{doc_id}")
async def admin_document_update(
    doc_id: int,
    payload: WikiDocumentIn,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(WikiDocument, doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    payload = _validate(payload)
    dup = await db.execute(
        select(WikiDocument.id).where(WikiDocument.slug == payload.slug, WikiDocument.id != doc_id)
    )
    if dup.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="该访问标识已存在")
    row.slug = payload.slug
    row.title = payload.title.strip()
    row.category = payload.category
    row.summary = payload.summary.strip()
    row.content = payload.content
    row.is_published = payload.isPublished
    row.update_time = _now()
    await db.commit()
    await db.refresh(row)
    return _ok(_doc_out(row), "保存成功")


@router.delete("/wiki/admin/documents/{doc_id}")
async def admin_document_delete(
    doc_id: int,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(WikiDocument, doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    await db.delete(row)
    await db.commit()
    return _ok({"id": doc_id}, "删除成功")


@router.post("/wiki/admin/upload")
async def admin_upload(
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    """上传 Wiki 附件：图片可直接用 Markdown 插图，文档类给下载链接。"""
    data = await save_wiki_file(file)
    return _ok(data, "上传成功")


@router.get("/wiki/admin/files")
async def admin_files(_admin=Depends(require_admin)):
    return _ok(list_wiki_files())


@router.delete("/wiki/admin/files")
async def admin_file_delete(
    path: str = Query(..., description="uploads 下的相对路径，如 wiki/202611/xxx.png"),
    _admin=Depends(require_admin),
):
    if not delete_wiki_file(path):
        raise HTTPException(status_code=400, detail="文件不存在或路径不合法")
    return _ok({"path": path}, "删除成功")


@router.get("/wiki/admin/categories")
async def admin_categories(_admin=Depends(require_admin)):
    return _ok([{"value": key, "label": label} for key, label in CATEGORY_LABELS.items()])
