"""图片上传公共设施：目录、白名单、大小限制、类型魔数校验与落盘（公告 / 论坛 / 头像共用）。

抽取成独立模块的原因：`/api/announcement/upload/image`（管理员）在 main.py 内联实现，
而论坛的 `/api/forum/upload/image`（登录用户，PRD §8-D1）需要**完全相同**的校验与落盘口径。
forum.py 若自行复刻一份就会出现"公告限 5MB、论坛限 10MB"这类静默分叉，故统一到本模块。

头像上传（FLPR-31）复用同一份校验与落盘设施，只是额外收紧：仅 jpg/png/webp、≤2MB、
后端兜底中心裁剪 256×256、文件名含用户 id、覆盖上传时删除旧文件（见 save_avatar / delete_avatar）。

落盘路径 `<UPLOAD_DIR>/<sub_prefix>/YYYYMM/<name>`，对外 URL 仍为
`/api/announcement/uploads/<sub_prefix>/YYYYMM/<name>`——复用 main.py 里同一个
StaticFiles 挂载点，因此**零 nginx 改动**（新增挂载点会引入新的 location 需求，
与页面路由 /forum 同名冲突是项目既有红线，见 AGENTS.md）。
"""
import io
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .config import BASE_DIR
from .crud import _TZ  # 统一北京时间（分目录 YYYYMM 与落库时间同口径）
from datetime import datetime

# 上传目录：默认 backend/data/uploads，可用 ANNOUNCEMENT_UPLOAD_DIR 覆盖
# （Docker 中指向挂载卷 /app/data/uploads，与公告上传保持同一目录）
UPLOAD_DIR = Path(
    os.environ.get("ANNOUNCEMENT_UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))
)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 对外 URL 前缀（与 main.py 的 StaticFiles 挂载点一一对应，勿单方面改动）
UPLOAD_URL_PREFIX = "/api/announcement/uploads"

# 白名单：扩展名 → Content-Type（后缀与 MIME 双重校验，见 save_image）
ALLOWED_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# Wiki 动态文档附件：图片 + 常见文档/压缩包，≤20MB（与 nginx client_max_body_size 一致）。
# 落盘复用同一 StaticFiles 挂载点，故 URL 仍是 /api/announcement/uploads/...，**零 nginx 改动**。
# 不放行 svg：svg 可内嵌脚本，同域静态托管会形成存储型 XSS。
WIKI_FILE_TYPES = {
    **ALLOWED_IMAGE_TYPES,
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".zip": "application/zip",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    ".json": "application/json",
}
MAX_WIKI_FILE_SIZE = 20 * 1024 * 1024  # 20MB
WIKI_SUB_PREFIX = "wiki"

# 头像专用口径（FLPR-31）：仅 jpg/png/webp、≤2MB、中心裁剪 256×256
AVATAR_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB
AVATAR_OUTPUT_SIZE = (256, 256)
AVATAR_SUB_PREFIX = "avatar"

# 类型魔数：扩展名 / Content-Type / 文件头三重校验，挡住"改后缀的木马"
_MAGIC_CHECKS = {
    ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    ".jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    ".gif": lambda b: b.startswith((b"GIF87a", b"GIF89a")),
    ".webp": lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP",
}


async def _read_validated_image(
    file: UploadFile, allowed_types: dict[str, str], max_size: int, size_label: str
) -> tuple[bytearray, str]:
    """读取并校验一张图片，返回 (内容, 扩展名)。

    ⚠️ 大小检查在**把请求体读进内存之前**完成：`await file.read()` 会一次性把整个
    上传内容读进进程内存，"先读后判"等于让攻击者用超大 body 直接把内存打满
    （本接口从 require_admin 放宽到所有登录用户后更需要注意）。
    因此先看 Content-Length 拦掉明显的，再**分块**读取并在累计超限时立刻中止。
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed_types:
        # 头像收紧到 jpg/png/webp；公告与论坛保持既有五类白名单文案
        hint = (
            "仅支持 jpg / png / webp 图片"
            if allowed_types is AVATAR_IMAGE_TYPES
            else "仅支持 png / jpg / jpeg / gif / webp 图片"
        )
        raise HTTPException(status_code=400, detail=hint)
    if not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不是图片")

    # 第一道：Content-Length（缺失或不可信时跳过，交给下面的分块检查兜底）
    declared = (file.headers or {}).get("content-length")
    if declared and declared.isdigit() and int(declared) > max_size:
        raise HTTPException(status_code=400, detail=f"图片大小不能超过 {size_label}")

    # 第二道：分块读，累计超限立刻中止（不把超大 body 整个读进内存）
    buf = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_size:
            raise HTTPException(status_code=400, detail=f"图片大小不能超过 {size_label}")

    # 第三道：类型魔数（防"改后缀"上传；扩展名 / Content-Type / 文件头须一致）
    if not _MAGIC_CHECKS[ext](bytes(buf)):
        raise HTTPException(status_code=400, detail="图片内容与扩展名不符，或文件已损坏")
    return buf, ext


async def save_image(file: UploadFile, sub_prefix: str = "") -> str:
    """校验并落盘一张图片，返回可写入正文的相对 URL。

    - 扩展名白名单（png/jpg/jpeg/gif/webp）+ Content-Type + 类型魔数，三者缺一不可；
    - ≤ 5MB；
    - 按月份分目录 + 随机文件名（避免覆盖与路径穿越：文件名由本函数生成，不采信客户端）。

    @param sub_prefix 子目录前缀（论坛传 "forum" → uploads/forum/YYYYMM/；公告传 ""）
    """
    buf, ext = await _read_validated_image(file, ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE, "5MB")

    # 按月份分目录 + 随机文件名
    sub_dir = datetime.now(_TZ).strftime("%Y%m")
    target_dir = UPLOAD_DIR / sub_prefix / sub_dir if sub_prefix else UPLOAD_DIR / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (target_dir / name).write_bytes(bytes(buf))

    parts = [UPLOAD_URL_PREFIX]
    if sub_prefix:
        parts.append(sub_prefix)
    parts.append(sub_dir)
    parts.append(name)
    return "/".join(parts)


def _wiki_dir() -> Path:
    return UPLOAD_DIR / WIKI_SUB_PREFIX


def _safe_wiki_filename(filename: str, ext: str) -> str:
    """清洗客户端文件名：只保留安全字符 + 随机后缀，避免路径穿越与覆盖。"""
    stem = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff_-]+", "_", Path(filename).stem).strip("_")[:60]
    return f"{stem or 'file'}_{uuid.uuid4().hex[:8]}{ext}"


async def save_wiki_file(file: UploadFile) -> dict:
    """校验并落盘一个 Wiki 附件，返回 {url, name, size, contentType, path}。

    图片走扩展名 + Content-Type + 魔数三重校验；文档类只按扩展名白名单拦截，
    不盲信客户端 Content-Type。大小与 nginx 上传上限对齐（20MB）。
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in WIKI_FILE_TYPES:
        allowed = " / ".join(sorted(WIKI_FILE_TYPES))
        raise HTTPException(status_code=400, detail=f"不支持的文件类型，允许：{allowed}")
    if ext in _MAGIC_CHECKS and not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="图片文件的 Content-Type 不正确")

    declared = (file.headers or {}).get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_WIKI_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 20MB")

    buf = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > MAX_WIKI_FILE_SIZE:
            raise HTTPException(status_code=400, detail="文件大小不能超过 20MB")
    if ext in _MAGIC_CHECKS and not _MAGIC_CHECKS[ext](bytes(buf)):
        raise HTTPException(status_code=400, detail="图片内容与扩展名不符，或文件已损坏")

    sub_dir = datetime.now(_TZ).strftime("%Y%m")
    target_dir = _wiki_dir() / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = _safe_wiki_filename(file.filename or "file", ext)
    (target_dir / name).write_bytes(bytes(buf))
    rel = f"{WIKI_SUB_PREFIX}/{sub_dir}/{name}"
    return {
        "url": f"{UPLOAD_URL_PREFIX}/{rel}",
        "name": name,
        "size": len(buf),
        "contentType": WIKI_FILE_TYPES[ext],
        "path": rel,
    }


def list_wiki_files() -> list[dict]:
    """列出已上传的 Wiki 附件（按月目录倒序， newest first）。"""
    root = _wiki_dir()
    if not root.is_dir():
        return []
    items: list[dict] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(UPLOAD_DIR).as_posix()
        stat = path.stat()
        items.append({
            "name": path.name,
            "path": rel,
            "url": f"{UPLOAD_URL_PREFIX}/{rel}",
            "size": stat.st_size,
            "contentType": WIKI_FILE_TYPES.get(path.suffix.lower(), ""),
            "updateTime": datetime.fromtimestamp(stat.st_mtime, _TZ).strftime("%Y-%m-%dT%H:%M:%S"),
        })
    items.sort(key=lambda x: x["updateTime"], reverse=True)
    return items


def delete_wiki_file(rel_path: str) -> bool:
    """删除一个 Wiki 附件。仅接受本模块生成的 wiki/YYYYMM/<name> 相对路径。"""
    parts = rel_path.split("/")
    if len(parts) != 3 or parts[0] != WIKI_SUB_PREFIX or not parts[1].isdigit() or len(parts[1]) != 6:
        return False
    if Path(parts[2]).name != parts[2]:
        return False
    path = UPLOAD_DIR / parts[0] / parts[1] / parts[2]
    try:
        if path.is_file():
            path.unlink()
            return True
    except OSError:
        return False
    return False


async def save_avatar(file: UploadFile, user_id: int) -> str:
    """校验、中心裁剪并落盘一张用户头像，返回相对 URL（FLPR-31）。

    与 save_image 共用后缀 / MIME / 大小 / 魔数四重校验，额外收紧口径：
    - 仅 jpg / png / webp，≤ 2MB；
    - PIL 后端兜底中心裁剪到 256×256（前端裁剪是可选优化，后端不能省）；
    - 文件名含用户 id：`avatar_<user_id>_<uuid>.<ext>`，便于排查孤儿文件；
    - 落盘 `uploads/avatar/YYYYMM/`，URL 仍是 `/api/announcement/uploads/avatar/...`。

    覆盖上传的旧文件由调用方在数据库提交成功后调用 delete_avatar() 清理。
    """
    buf, ext = await _read_validated_image(file, AVATAR_IMAGE_TYPES, AVATAR_MAX_SIZE, "2MB")

    try:
        with Image.open(io.BytesIO(bytes(buf))) as img:
            img = ImageOps.exif_transpose(img)  # 手机竖拍带 EXIF 方向时先转正
            img = ImageOps.fit(img, AVATAR_OUTPUT_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            # JPEG 不支持 RGBA / P 模式，统一转 RGB；png/webp 保留原模式
            if ext in (".jpg", ".jpeg") and img.mode != "RGB":
                img = img.convert("RGB")
            out = io.BytesIO()
            save_kwargs = {"quality": 90, "optimize": True} if ext in (".jpg", ".jpeg") else {}
            img.save(out, format=_PIL_FORMAT[ext], **save_kwargs)
            avatar_bytes = out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise HTTPException(status_code=400, detail="图片无法解析或已损坏") from e

    sub_dir = datetime.now(_TZ).strftime("%Y%m")
    target_dir = UPLOAD_DIR / AVATAR_SUB_PREFIX / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"avatar_{user_id}_{uuid.uuid4().hex}{ext}"
    (target_dir / name).write_bytes(avatar_bytes)
    return f"{UPLOAD_URL_PREFIX}/{AVATAR_SUB_PREFIX}/{sub_dir}/{name}"


# PIL 保存时需要的 format 名（与扩展名一一对应）
_PIL_FORMAT = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
}


def delete_avatar(url: str, user_id: int) -> bool:
    """删除旧头像文件（覆盖上传 / 后台重置时调用，防孤儿文件）。

    安全边界：只处理本项目 avatar 前缀下的 URL，且文件名必须属于该 user_id——
    避免持有任意 URL 的调用方借本函数删掉别人头像或公告图片。
    返回是否真的删掉了一个文件；路径不存在视为幂等成功。
    """
    prefix = f"{UPLOAD_URL_PREFIX}/{AVATAR_SUB_PREFIX}/"
    if not url or not url.startswith(prefix):
        return False
    rel = url[len(prefix):]
    # rel 形如 202611/avatar_12_abcd.png；禁止路径穿越与多余层级
    parts = rel.split("/")
    if len(parts) != 2 or not parts[0].isdigit() or len(parts[0]) != 6:
        return False
    fname = parts[1]
    if not fname.startswith(f"avatar_{user_id}_") or Path(fname).name != fname:
        return False
    path = UPLOAD_DIR / AVATAR_SUB_PREFIX / parts[0] / fname
    try:
        if path.is_file():
            path.unlink()
            return True
    except OSError:
        # 删文件失败不阻断主流程（数据库已提交，新头像已生效）
        return False
    return False
