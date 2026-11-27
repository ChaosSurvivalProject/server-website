"""官方邮箱推送：/api/admin/mail/*（需管理员权限）。

- POST /mail/send             给指定玩家或全部玩家发推送邮件，落 mail_logs 回执
- GET  /mail/logs             分页查看推送记录（含成功/失败状态）
- GET  /mail/recipients       可选收件人列表（后端查询，供后台下拉选择）

推送是「尽力而为」：单个收件人发送失败只记录 failed 回执，不影响其他收件人；
接口返回成功/失败计数，管理员据此判断是否重发。
所有接口遵循 {code,message,data} 包络。
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .config import MAIL
from .crud import _TZ
from .database import MailLog, User, get_db, USER_STATUS_NORMAL, USER_STATUS_DELETED
from .auth.deps import require_admin
from .mailer import send_mail

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/admin/mail", tags=["admin-mail"])


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


class SendMailRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200, description="邮件主题")
    content: str = Field(..., min_length=1, max_length=5000, description="邮件正文")
    userIds: Optional[list[int]] = Field(default=None, description="指定收件人 id 列表；空=全部玩家")
    onlyVerified: bool = Field(default=True, description="群发时是否仅发给已验证邮箱的玩家")


@router.post("/send")
async def send_push(
    req: SendMailRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员：给指定玩家或全部玩家发送官方推送邮件。"""
    subject = req.subject.strip()
    content = req.content.strip()
    if not subject or not content:
        raise HTTPException(status_code=400, detail="邮件主题和正文不能为空")

    if req.userIds:
        result = await db.execute(
            select(User).where(
                User.id.in_(req.userIds),
                User.email.isnot(None),
                User.email != "",
                User.status != USER_STATUS_DELETED,
            )
        )
        recipients = result.scalars().all()
    else:
        stmt = select(User).where(
            User.email.isnot(None),
            User.email != "",
            User.status == USER_STATUS_NORMAL,
        )
        if req.onlyVerified:
            stmt = stmt.where(User.email_verified == 1)
        recipients = (await db.execute(stmt)).scalars().all()

    if not recipients:
        raise HTTPException(status_code=400, detail="没有可发送的收件人（请确认玩家已绑定邮箱）")

    success = 0
    failed = 0
    for user in recipients:
        status = "success"
        error = ""
        try:
            await run_in_threadpool(
                send_mail, user.email, subject, content, ""
            )
            success += 1
        except Exception as e:
            status = "failed"
            error = str(e)[:300]
            failed += 1
        db.add(
            MailLog(
                email=user.email,
                username=user.username,
                subject=subject,
                content=content,
                status=status,
                error=error,
                admin_id=admin.id,
                admin_name=admin.username,
                create_time=_now_iso(),
            )
        )
    await db.commit()

    return {
        "code": 0,
        "message": "推送完成",
        "data": {
            "total": len(recipients),
            "success": success,
            "failed": failed,
            "devMode": MAIL.dev_mode,
        },
    }


@router.get("/logs")
async def list_logs(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="success / failed"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：分页查看邮件推送记录。"""
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    where = []
    if status in ("success", "failed"):
        where.append(MailLog.status == status)
    cond = None
    if where:
        from sqlalchemy import and_

        cond = and_(*where)

    count_stmt = select(func.count()).select_from(MailLog)
    stmt = select(MailLog)
    if cond is not None:
        count_stmt = count_stmt.where(cond)
        stmt = stmt.where(cond)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        (await db.execute(stmt.order_by(MailLog.id.desc()).offset(offset).limit(page_size)))
        .scalars()
        .all()
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0

    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                {
                    "id": r.id,
                    "email": r.email,
                    "username": r.username,
                    "subject": r.subject,
                    "content": r.content,
                    "status": r.status,
                    "error": r.error,
                    "adminName": r.admin_name,
                    "createTime": r.create_time,
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "hasNext": page < total_pages,
            "hasPrev": page > 1,
        },
    }


@router.get("/recipients")
async def list_recipients(
    q: str = Query(default="", description="按邮箱/账号/昵称模糊搜索"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：获取可收件玩家列表（已绑定邮箱、未软删除）。"""
    stmt = select(User).where(
        User.email.isnot(None),
        User.email != "",
        User.status != USER_STATUS_DELETED,
    )
    if q.strip():
        kw = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(User.email.like(kw), User.username.like(kw), User.nickname.like(kw))
        )
    rows = (await db.execute(stmt.order_by(User.id.desc()).limit(limit))).scalars().all()
    return {
        "code": 0,
        "message": "success",
        "data": [
            {
                "id": u.id,
                "username": u.username,
                "nickname": u.nickname,
                "email": u.email,
                "emailVerified": bool(u.email_verified),
            }
            for u in rows
        ],
    }
