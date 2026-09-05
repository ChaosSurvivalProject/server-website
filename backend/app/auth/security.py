"""认证安全工具：密码哈希（bcrypt）、JWT（PyJWT）、图形验证码（captcha 库）。

验证码使用进程内存存储：单进程部署（uvicorn / 单容器）下足够；
重启后验证码失效属预期行为，避免引入额外持久化依赖。
"""
import base64
import os
import secrets
import string
import time
from pathlib import Path

import bcrypt
import jwt
from captcha.image import ImageCaptcha

from ..database import DB_FILE

# ── JWT ──────────────────────────────────────────────────────────
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))

# 密钥来源：环境变量 JWT_SECRET 优先；未设置时自动生成并持久化到
# 数据目录（与 SQLite 同目录，已被 .gitignore 忽略），
# 避免每次重启随机密钥导致所有登录态失效。
_DATA_DIR = Path(DB_FILE).parent
_JWT_SECRET_FILE = _DATA_DIR / "jwt_secret.txt"


def _load_jwt_secret() -> str:
    env_secret = os.environ.get("JWT_SECRET")
    if env_secret:
        return env_secret
    if _JWT_SECRET_FILE.exists():
        return _JWT_SECRET_FILE.read_text(encoding="utf-8").strip()
    secret = secrets.token_hex(32)
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _JWT_SECRET_FILE.write_text(secret, encoding="utf-8")
    try:
        _JWT_SECRET_FILE.chmod(0o600)
    except OSError:
        pass
    return secret


JWT_SECRET = _load_jwt_secret()


def create_access_token(username: str, role: str) -> str:
    """签发 JWT：sub=username，role=角色，exp 由 JWT_EXPIRE_HOURS 控制。"""
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str):
    """解码并校验 JWT，失败（过期/伪造）返回 None。"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return None


# ── 密码 ─────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """bcrypt 哈希（自动加盐）。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验密码；哈希格式异常时按不匹配处理。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


PASSWORD_MIN_LEN = 8
PASSWORD_MAX_LEN = 32


def is_valid_password(password: str) -> bool:
    """密码规则：8-32 位且同时包含字母和数字（bcrypt 上限 72 字节，32 位足够安全）。"""
    if not (PASSWORD_MIN_LEN <= len(password) <= PASSWORD_MAX_LEN):
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


def generate_strong_password(length: int = 16) -> str:
    """生成强密码：必含小写/大写/数字/符号各 1 个，其余随机填充后打乱。"""
    pools = [string.ascii_lowercase, string.ascii_uppercase, string.digits, "!@#$%^&*()-_=+"]
    all_chars = "".join(pools)
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice(all_chars) for _ in range(max(length, len(pools)) - len(pools))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


# ── 图形验证码 ───────────────────────────────────────────────────
# 6 位数字+大写字母；剔除易混淆字符（0/O、1/I），校验时不区分大小写。
CAPTCHA_LENGTH = 6
CAPTCHA_TTL_SECONDS = 300  # 5 分钟有效
_CAPTCHA_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# captcha_id -> (标准答案小写, 过期时间戳)
_captcha_store: dict[str, tuple[str, float]] = {}


def _cleanup_expired_captcha() -> None:
    now = time.time()
    expired = [cid for cid, (_, exp) in _captcha_store.items() if now > exp]
    for cid in expired:
        _captcha_store.pop(cid, None)


def generate_captcha() -> tuple[str, str]:
    """生成图形验证码，返回 (captcha_id, PNG data URI)。"""
    code = "".join(secrets.choice(_CAPTCHA_CHARS) for _ in range(CAPTCHA_LENGTH))
    image = ImageCaptcha(width=160, height=60)
    png_bytes = image.generate(code).getvalue()

    _cleanup_expired_captcha()
    captcha_id = secrets.token_urlsafe(16)
    _captcha_store[captcha_id] = (code.lower(), time.time() + CAPTCHA_TTL_SECONDS)
    return captcha_id, "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")


def verify_captcha(captcha_id: str, code: str) -> bool:
    """校验验证码：一次性（无论对错都销毁）、限时长、不区分大小写。"""
    entry = _captcha_store.pop(captcha_id or "", None)
    if entry is None:
        return False
    expected, expire_at = entry
    if time.time() > expire_at:
        return False
    return (code or "").strip().lower() == expected
