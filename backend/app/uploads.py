"""图片上传公共设施：目录、白名单、大小限制与落盘（公告与论坛共用）。

抽取成独立模块的原因：`/api/announcement/upload/image`（管理员）在 main.py 内联实现，
而论坛的 `/api/forum/upload/image`（登录用户，PRD §8-D1）需要**完全相同**的校验与落盘口径。
forum.py 若自行复刻一份就会出现"公告限 5MB、论坛限 10MB"这类静默分叉，故统一到本模块。

落盘路径 `<UPLOAD_DIR>/<sub_prefix>/YYYYMM/<uuid><ext>`，对外 URL 仍为
`/api/announcement/uploads/<sub_prefix>/YYYYMM/<uuid><ext>`——复用 main.py 里同一个
StaticFiles 挂载点，因此**零 nginx 改动**（新增挂载点会引入新的 location 需求，
与页面路由 /forum 同名冲突是项目既有红线，见 AGENTS.md）。
"""
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

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


async def save_image(file: UploadFile, sub_prefix: str = "") -> str:
    """校验并落盘一张图片，返回可写入正文的相对 URL。

    - 扩展名白名单（png/jpg/jpeg/gif/webp）+ Content-Type 须为 image/*，双条件缺一不可；
    - ≤ 5MB；
    - 按月份分目录 + 随机文件名（避免覆盖与路径穿越：文件名由本函数生成，不采信客户端）。

    ⚠️ 大小检查在**把请求体读进内存之前**完成：`await file.read()` 会一次性把整个
    上传内容读进进程内存，"先读后判"等于让攻击者用超大 body 直接把内存打满
    （本接口从 require_admin 放宽到所有登录用户后更需要注意）。
    因此先看 Content-Length 拦掉明显的，再**分块**读取并在累计超限时立刻中止。

    @param sub_prefix 子目录前缀（论坛传 "forum" → uploads/forum/YYYYMM/；公告传 ""）
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, detail="仅支持 png / jpg / jpeg / gif / webp 图片"
        )
    if not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="文件类型不是图片")

    # 第一道：Content-Length（缺失或不可信时跳过，交给下面的分块检查兜底）
    declared = (file.headers or {}).get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    # 第二道：分块读，累计超限立刻中止（不把超大 body 整个读进内存）
    buf = bytearray()
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

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
