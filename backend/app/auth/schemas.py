"""认证相关请求模型。

请求体字段直接使用 camelCase（与前端 JSON 契约一致，
参照 AddWatchCountRequest 的做法）。
"""
from pydantic import BaseModel, Field


class CaptchaResponseData(BaseModel):
    """GET /auth/captcha 的 data。"""

    captchaId: str = Field(..., description="验证码 ID，注册时需回传")
    image: str = Field(..., description="PNG 图片 base64 data URI")


class RegisterRequest(BaseModel):
    """POST /auth/register 请求体。"""

    email: str = Field(..., max_length=255, description="邮箱（作为初始用户名）")
    password: str = Field(..., max_length=72, description="密码")
    confirmPassword: str = Field(..., max_length=72, description="确认密码")
    captchaId: str = Field(..., description="图形验证码 ID")
    captchaCode: str = Field(..., description="用户输入的验证码（不区分大小写）")


class LoginRequest(BaseModel):
    """POST /auth/login 请求体。"""

    username: str = Field(..., max_length=100, description="用户名（普通用户为注册邮箱）")
    password: str = Field(..., max_length=72, description="密码")


class LoginResponseData(BaseModel):
    """POST /auth/login 的 data。"""

    token: str = Field(..., description="JWT，前端以 Bearer 方式携带")
    username: str
    role: str = Field(..., description="admin=管理员, user=普通用户")


class MeResponseData(BaseModel):
    """GET /auth/me 的 data。"""

    username: str
    email: str | None = None
    role: str
