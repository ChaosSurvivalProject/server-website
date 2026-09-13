"""认证相关请求模型。

请求体字段直接使用 camelCase（与前端 JSON 契约一致，
参照 AddWatchCountRequest 的做法）。
"""
from typing import Optional

from pydantic import BaseModel, Field


class UserAdminPageQuery(BaseModel):
    """管理员用户分页查询参数。"""

    page: int = 1
    pageSize: int = 10


class UserCreateRequest(BaseModel):
    """POST /auth/admin/users 请求体（管理员直接创建用户）。"""

    username: str = Field(..., max_length=100, description="账号（登录名，唯一，创建后不可修改）")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称（可选，用于展示）")
    password: str = Field(..., max_length=72, description="初始密码")
    role: str = Field(default="user", description="角色：admin=管理员, user=普通用户")
    email: Optional[str] = Field(None, max_length=255, description="邮箱（可选）")


class UserUpdateRequest(BaseModel):
    """PUT /auth/admin/users/{id} 请求体（编辑用户，密码字段可选——忘记密码重置场景）。

    账号（username）不允许修改；昵称（nickname）/ 角色 / 邮箱 / 密码可改。
    """

    nickname: Optional[str] = Field(None, max_length=50, description="昵称（留空=不改，显式空串=清空）")
    role: Optional[str] = Field(None, description="角色：admin=管理员, user=普通用户")
    password: Optional[str] = Field(None, max_length=72, description="重置密码（留空不改）")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")


class UserStatusRequest(BaseModel):
    """PUT /auth/admin/users/{id}/status 请求体。"""

    status: int = Field(..., description="目标状态：1=启用, 0=禁用, 2=删除（软删除）")


class CaptchaResponseData(BaseModel):
    """GET /auth/captcha 的 data。"""

    captchaId: str = Field(..., description="验证码 ID，滑块校验与注册时需回传")
    backgroundImage: str = Field(..., description="底图 PNG base64 data URI（含缺口）")
    pieceImage: str = Field(..., description="拼图块 PNG base64 data URI（透明背景）")
    sliderY: int = Field(..., description="拼图块纵向位置（px，相对底图顶部）")


class CaptchaVerifyRequest(BaseModel):
    """POST /auth/captcha/verify 请求体。"""

    captchaId: str = Field(..., description="验证码 ID")
    x: int = Field(..., ge=0, le=10000, description="拼图块横向位置（px，相对底图左侧）")


class RegisterRequest(BaseModel):
    """POST /auth/register 请求体。"""

    email: str = Field(..., max_length=255, description="邮箱（作为初始用户名）")
    password: str = Field(..., max_length=72, description="密码")
    confirmPassword: str = Field(..., max_length=72, description="确认密码")
    captchaId: str = Field(..., description="已通过滑块校验的验证码 ID")


class LoginRequest(BaseModel):
    """POST /auth/login 请求体。"""

    username: str = Field(..., max_length=100, description="用户名（普通用户为注册邮箱）")
    password: str = Field(..., max_length=72, description="密码")


class LoginResponseData(BaseModel):
    """POST /auth/login 的 data。"""

    token: str = Field(..., description="JWT，前端以 Bearer 方式携带")
    username: str
    nickname: str | None = None
    role: str = Field(..., description="admin=管理员, user=普通用户")


class MeResponseData(BaseModel):
    """GET /auth/me 的 data。"""

    username: str
    nickname: str | None = None
    email: str | None = None
    role: str
