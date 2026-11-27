"""邮箱验证码：/api/email/send-code（公开）+ 校验helper（注册/验证码登录共用）。

流程：
1. 前端 POST /api/email/send-code {email, purpose} → 服务端生成 4 位验证码，
   bcrypt 哈希落库（5 分钟有效），通过官方邮箱发出；dev_mode 下只写日志并在
   响应回传 devCode 供本地测试。
2. 注册 / 验证码登录时把用户填的验证码交给 verify_email_code() 校验：
   一次性消费，连续失败 5 次作废，防止爆破。

限流：同一邮箱 60 秒内只能发一次；同一 IP 10 分钟内最多 20 次，防止刷邮件。
所有接口遵循 {code,message,data} 包络，业务失败抛 HTTPException(detail=...)。
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import MAIL
from .crud import _TZ
from .database import EmailCode, User, get_db, USER_STATUS_NORMAL
from .auth.security import hash_password, verify_password
from .mailer import build_code_email, send_mail

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/email", tags=["email"])

CODE_TTL_MINUTES = 5
SEND_INTERVAL_SECONDS = 60
MAX_ATTEMPTS = 5
IP_WINDOW_MINUTES = 10
IP_MAX_SENDS = 20


def _now() -> datetime:
    return datetime.now(_TZ)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _parse(iso_str: str) -> datetime:
    """把库里的北京时间 ISO 字符串解析成带 _TZ 时区的 datetime，避免与 _now() 比较时报 naive/aware 冲突。"""
    try:
        return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=_TZ)
    except (ValueError, TypeError):
        return _now()


class SendCodeRequest(BaseModel):
    email: str = Field(..., max_length=255, description="接收验证码的邮箱")
    purpose: str = Field(..., description="用途：register=注册验证，login=验证码登录")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "")[:64]


@router.post("/send-code")
async def send_code(
    req: SendCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """发送 4 位邮箱验证码（注册 / 验证码登录共用）。"""
    email = (req.email or "").strip().lower()
    if req.purpose not in ("register", "login"):
        raise HTTPException(status_code=400, detail="验证码用途不合法")
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    ip = _client_ip(request)
    now = _now()

    # 注册场景：已注册邮箱不再发码（避免撞库探测）
    if req.purpose == "register":
        exists = await db.execute(
            select(func.count()).select_from(User).where(User.email == email)
        )
        if exists.scalar_one() > 0:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")

    # 登录场景：必须已注册且状态正常
    else:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or user.status != USER_STATUS_NORMAL:
            # 不区分「未注册」与「被禁用」，避免账号枚举
            raise HTTPException(status_code=400, detail="该邮箱未注册或账号不可用")

    # 同一邮箱 + 同一用途 60 秒内限发（已消费的验证码不再占用冷却期，
    # 这样注册验证通过后可立即发登录验证码）；换用途可立即发。
    last = await db.execute(
        select(EmailCode)
        .where(
            EmailCode.email == email,
            EmailCode.purpose == req.purpose,
            EmailCode.used == 0,
        )
        .order_by(EmailCode.id.desc())
        .limit(1)
    )
    last_row = last.scalar_one_or_none()
    if last_row is not None:
        last_time = _parse(last_row.create_time)
        if (now - last_time).total_seconds() < SEND_INTERVAL_SECONDS:
            wait = SEND_INTERVAL_SECONDS - int((now - last_time).total_seconds())
            raise HTTPException(status_code=429, detail=f"请 {wait} 秒后再获取验证码")

    # IP 限流
    if ip:
        ip_since = _iso(now - timedelta(minutes=IP_WINDOW_MINUTES))
        ip_count = await db.execute(
            select(func.count())
            .select_from(EmailCode)
            .where(EmailCode.ip == ip, EmailCode.create_time >= ip_since)
        )
        if ip_count.scalar_one() >= IP_MAX_SENDS:
            raise HTTPException(status_code=429, detail="操作过于频繁，请稍后再试")

    code = f"{secrets.randbelow(10000):04d}"
    row = EmailCode(
        email=email,
        code_hash=hash_password(code),
        purpose=req.purpose,
        expires_at=_iso(now + timedelta(minutes=CODE_TTL_MINUTES)),
        used=0,
        attempts=0,
        ip=ip,
        create_time=_iso(now),
    )
    db.add(row)
    await db.commit()

    subject, text, html = build_code_email(code, req.purpose)
    from starlette.concurrency import run_in_threadpool

    try:
        await run_in_threadpool(send_mail, email, subject, text, html)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = {"sent": True, "expiresIn": CODE_TTL_MINUTES * 60}
    if MAIL.dev_mode:
        # 开发模式：验证码不真发，仅日志 + 回传，方便本地联调（生产务必关闭）
        data["devCode"] = code
        logger.info("[MAIL-DEV] 验证码 email=%s purpose=%s code=%s", email, req.purpose, code)
    return {"code": 0, "message": "验证码已发送", "data": data}


async def verify_email_code(
    db: AsyncSession,
    email: str,
    code: str,
    purpose: str,
) -> None:
    """校验并一次性消费邮箱验证码；失败抛 HTTPException(400)。

    连续失败 MAX_ATTEMPTS 次后该验证码作废，需重新获取。
    """
    email = (email or "").strip().lower()
    code = (code or "").strip()
    if len(code) != 4 or not code.isdigit():
        raise HTTPException(status_code=400, detail="验证码为 4 位数字")

    result = await db.execute(
        select(EmailCode)
        .where(
            EmailCode.email == email,
            EmailCode.purpose == purpose,
            EmailCode.used == 0,
        )
        .order_by(EmailCode.id.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=400, detail="请先获取验证码")

    if row.attempts >= MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="验证码错误次数过多，请重新获取")
    expire_at = _parse(row.expires_at)
    if _now() > expire_at:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")

    if not verify_password(code, row.code_hash):
        row.attempts += 1
        await db.commit()
        raise HTTPException(status_code=400, detail="验证码错误")

    row.used = 1
    await db.commit()
