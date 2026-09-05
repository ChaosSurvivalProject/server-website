"""认证路由：/auth/captcha、/auth/register、/auth/login、/auth/me。

所有接口遵循项目统一响应包络 {code, message, data}（code=0 成功）；
业务失败以 HTTPException(400/401, detail=...) 抛出，前端 axios 拦截器
统一读取 detail 展示。
"""
from datetime import datetime

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import User, get_db
from .deps import get_current_user
from .schemas import LoginRequest, RegisterRequest
from .security import (
    create_access_token,
    generate_captcha,
    hash_password,
    is_valid_password,
    verify_captcha,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ── 图形验证码 ───────────────────────────────────────────────────
@router.get("/captcha")
async def get_captcha():
    """获取注册用图形验证码（6 位数字+字母，不区分大小写，5 分钟有效）。"""
    captcha_id, image = generate_captcha()
    return {"code": 0, "message": "success", "data": {"captchaId": captcha_id, "image": image}}


# ── 注册 ─────────────────────────────────────────────────────────
@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """邮箱（作为初始用户名）注册，注册成功角色为普通用户 user。"""
    # 1. 验证码（一次性，先销毁再校验）
    if not verify_captcha(req.captchaId, req.captchaCode):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期，请刷新后重试",
        )
    # 2. 邮箱格式（email-validator 本地校验，不做 DNS 递送检查）
    try:
        validate_email(req.email, check_deliverability=False)
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱格式不正确",
        ) from e
    # 3. 两次密码一致
    if req.password != req.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的密码不一致",
        )
    # 4. 密码规则：8-32 位且含字母和数字
    if not is_valid_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码需为 8-32 位且同时包含字母和数字",
        )
    # 5. 邮箱未注册
    result = await db.execute(
        select(User).where(or_(User.username == req.email, User.email == req.email))
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    user = User(
        username=req.email,
        email=req.email,
        password_hash=hash_password(req.password),
        role="user",
        create_time=_now_iso(),
    )
    db.add(user)
    await db.commit()

    return {"code": 0, "message": "注册成功", "data": {"username": user.username, "role": user.role}}


# ── 登录 ─────────────────────────────────────────────────────────
@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户名（普通用户为注册邮箱）+ 密码登录，成功签发 JWT。"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = create_access_token(user.username, user.role)
    return {
        "code": 0,
        "message": "登录成功",
        "data": {"token": token, "username": user.username, "role": user.role},
    }


# ── 当前用户 ─────────────────────────────────────────────────────
@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息（前端刷新页面时校验 token、恢复会话）。"""
    return {
        "code": 0,
        "message": "success",
        "data": {"username": user.username, "email": user.email, "role": user.role},
    }
