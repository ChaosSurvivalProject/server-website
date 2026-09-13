"""管理员用户管理路由：/auth/admin/users/*（需管理员权限）。

支持新增、编辑（昵称/角色/邮箱/密码重置）、启用/禁用、软删除与分页查询。
账号（username）为登录标识，创建后不可修改；昵称（nickname）为展示名，可修改。
所有接口遵循项目统一响应包络 {code, message, data}（code=0 成功）；
业务失败以 HTTPException(400/401/403/404, detail=...) 抛出，前端 axios
拦截器统一读取 detail 展示。
"""
import re
from datetime import datetime
from typing import Optional

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import _TZ  # 统一北京时间（naive ISO 字符串，见 AGENTS.md 存储约定）
from ..database import (
    User,
    get_db,
    USER_STATUS_NORMAL,
    USER_STATUS_DISABLED,
    USER_STATUS_DELETED,
    ROLE_ADMIN,
    ROLE_USER,
)
from .deps import require_admin
from .schemas import UserCreateRequest, UserUpdateRequest, UserStatusRequest
from .security import hash_password, is_valid_password

router = APIRouter(prefix="/auth/admin/users", tags=["auth-admin-users"])

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._%+-]{2,100}$")


def _now_iso() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def _dump_user(obj: User) -> dict:
    """ORM 对象 → camelCase dict（密码哈希不外发）。"""
    return {
        "id": obj.id,
        "username": obj.username,
        "nickname": obj.nickname,
        "email": obj.email,
        "role": obj.role,
        "status": obj.status,
        "createTime": obj.create_time,
    }


async def _get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ── 分页查询（含禁用/已删除，可按状态过滤） ──────────────────────
@router.get("")
async def admin_list_users(
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    status: Optional[int] = Query(default=None, description="1=正常, 0=禁用, 2=已删除；缺省查全部"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：分页查询用户（含禁用/已删除，可按状态过滤）。"""
    page_size = max(pageSize, 1)
    offset = (page - 1) * page_size

    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if status is not None:
        stmt = stmt.where(User.status == status)
        count_stmt = count_stmt.where(User.status == status)

    stmt = stmt.order_by(User.id.desc()).offset(offset).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    items = (await db.execute(stmt)).scalars().all()
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [_dump_user(u) for u in items],
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "total": total,
            "hasNext": page < total_pages,
            "hasPrev": page > 1,
        },
    }


# ── 新增用户 ──────────────────────────────────────────────────────
@router.post("")
async def admin_create_user(
    req: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：直接创建用户账号（运营场景：给玩家/管理发账号）。

    校验规则：
    - 账号（username）2-100 个字母/数字/. _ % + -，全局唯一，创建后不可修改
    - 昵称（nickname）可选，最长 50 个字符
    - 密码 8-32 位且含字母和数字（与注册同一规则）
    - 角色仅允许 admin / user；邮箱可选，填写时须合法且唯一
    """
    username = req.username.strip()
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(
            status_code=400,
            detail="账号需为 2-100 个字符，仅可包含字母、数字及 . _ % + -",
        )
    nickname = (req.nickname or "").strip() or None
    if nickname is not None and len(nickname) > 50:
        raise HTTPException(status_code=400, detail="昵称最长 50 个字符")
    if req.role not in (ROLE_ADMIN, ROLE_USER):
        raise HTTPException(status_code=400, detail="角色仅支持 admin 或 user")
    if not is_valid_password(req.password):
        raise HTTPException(
            status_code=400, detail="密码需为 8-32 位且同时包含字母和数字"
        )

    email = (req.email or "").strip() or None
    if email is not None:
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            raise HTTPException(status_code=400, detail="邮箱格式不正确")

    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="该账号已被占用")
    if email is not None:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(status_code=400, detail="该邮箱已被其他账号使用")

    user = User(
        username=username,
        nickname=nickname,
        email=email,
        password_hash=hash_password(req.password),
        role=req.role,
        status=USER_STATUS_NORMAL,
        create_time=_now_iso(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"code": 0, "message": "创建成功", "data": _dump_user(user)}


# ── 编辑用户（用户名 / 角色 / 邮箱 / 密码重置） ──────────────────
@router.put("/{user_id}")
async def admin_update_user(
    user_id: int,
    req: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：编辑用户。

    可改字段（部分更新，全部留空 = 无操作）：
    - nickname：昵称（用于展示；留空=不改，显式空串=清空）
    - role：admin / user
    - email：邮箱（可选）
    - password：重置密码（忘记密码场景；留空则不修改）
    账号（username）不允许修改（登录标识不可变）。
    已删除（软删除）用户禁止编辑，需先启用/恢复。
    """
    user = await _get_user_by_id(db, user_id)
    if user is None or user.status == USER_STATUS_DELETED:
        raise HTTPException(status_code=404, detail="用户不存在")

    changed = False

    # 昵称（留空 = 不改；显式空串 = 清空）
    if req.nickname is not None:
        new_nickname = req.nickname.strip() or None
        if new_nickname is not None and len(new_nickname) > 50:
            raise HTTPException(status_code=400, detail="昵称最长 50 个字符")
        if new_nickname != user.nickname:
            user.nickname = new_nickname
            changed = True

    # 角色
    if req.role is not None and req.role != user.role:
        if req.role not in (ROLE_ADMIN, ROLE_USER):
            raise HTTPException(status_code=400, detail="角色仅支持 admin 或 user")
        user.role = req.role
        changed = True

    # 邮箱（留空 = 清空；传 null/缺省 = 不修改）
    if req.email is not None:
        new_email = req.email.strip() or None
        if new_email is not None:
            try:
                validate_email(new_email, check_deliverability=False)
            except EmailNotValidError:
                raise HTTPException(status_code=400, detail="邮箱格式不正确")
            if new_email != user.email:
                dup = await db.execute(select(User).where(User.email == new_email))
                if dup.scalar_one_or_none() is not None:
                    raise HTTPException(status_code=400, detail="该邮箱已被其他账号使用")
        if new_email != user.email:
            user.email = new_email
            changed = True

    # 密码重置（忘记密码场景：留空不修改）
    if req.password is not None and req.password != "":
        if not is_valid_password(req.password):
            raise HTTPException(
                status_code=400, detail="密码需为 8-32 位且同时包含字母和数字"
            )
        user.password_hash = hash_password(req.password)
        changed = True

    if changed:
        await db.commit()
        await db.refresh(user)

    return {"code": 0, "message": "success", "data": _dump_user(user)}


# ── 启用 / 禁用 / 删除（软删除） ─────────────────────────────────
@router.put("/{user_id}/status")
async def admin_set_user_status(
    user_id: int,
    req: UserStatusRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """管理员：切换用户状态（一个接口覆盖启用/禁用/删除/恢复）。

    status: 1=启用, 0=禁用, 2=删除（软删除，数据保留可恢复）。
    启用可恢复禁用/已删除用户；删除为软删除（可再启用恢复）。
    不允许操作自己（防止管理员锁死自己的账号）。
    """
    if req.status not in (USER_STATUS_NORMAL, USER_STATUS_DISABLED, USER_STATUS_DELETED):
        raise HTTPException(
            status_code=400, detail="status 仅支持 1（启用）、0（禁用）、2（删除）"
        )

    user = await _get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == _admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的账号状态")

    user.status = req.status
    await db.commit()
    await db.refresh(user)

    msg = {
        USER_STATUS_NORMAL: "已启用",
        USER_STATUS_DISABLED: "已禁用",
        USER_STATUS_DELETED: "已删除（软删除，可恢复）",
    }[req.status]
    return {"code": 0, "message": msg, "data": _dump_user(user)}


# ── 删除（软删除） ───────────────────────────────────────────────
@router.delete("/{user_id}")
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """软删除用户：status 置为 2（已删除，数据保留可恢复），无法登录。"""
    user = await _get_user_by_id(db, user_id)
    if user is None or user.status == USER_STATUS_DELETED:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == _admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    user.status = USER_STATUS_DELETED
    await db.commit()
    await db.refresh(user)
    return {"code": 0, "message": "已删除（软删除，可恢复）", "data": _dump_user(user)}
