"""FastAPI 依赖：当前登录用户 / 管理员权限。"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import User, get_db, USER_STATUS_DISABLED, USER_STATUS_DELETED
from .security import decode_token

# auto_error=False：未携带 Authorization 头时返回 None，由依赖统一给 401
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """解析 Bearer token 并返回当前用户；无效/过期/用户不存在均 401。"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或缺少认证信息",
        )
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效，请重新登录",
        )
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效，请重新登录",
        )
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被删除",
        )
    # 已删除（软删除）/ 禁用用户的旧 token 一律失效，避免被禁用后仍持有效会话
    if user.status == USER_STATUS_DELETED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被删除",
        )
    if user.status == USER_STATUS_DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已被禁用，无法继续操作",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """要求管理员角色，否则 403。"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """可选登录态：带合法 token 返回用户，否则返回 None（**不抛 401**）。

    供"匿名可调、登录后多返回个性化字段"的公开接口使用（论坛的列表/详情/评论
    需要回传 liked / favorited 当前态；公告类接口无此需求）。

    与 get_current_user 的差别只在失败语义：token 无效/用户已删除/已禁用一律按
    匿名处理，而不是中断请求——公开页面不应该因为一个过期 cookie 就白屏。
    """
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None:
        return None
    username = payload.get("sub")
    if not username:
        return None
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or user.status in (USER_STATUS_DISABLED, USER_STATUS_DELETED):
        return None
    return user
