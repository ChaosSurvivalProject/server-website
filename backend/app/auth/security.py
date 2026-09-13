"""认证安全工具：密码哈希（bcrypt）、JWT（PyJWT）、滑块拼图验证码（Pillow）。

验证码使用进程内存存储：单进程部署（uvicorn / 单容器）下足够；
重启后验证码失效属预期行为，避免引入额外持久化依赖。
"""
import base64
import io
import os
import secrets
import string
import time
from pathlib import Path

import bcrypt
import jwt
from PIL import Image, ImageDraw, ImageFilter

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


# ── 滑块拼图验证码 ───────────────────────────────────────────────
# 后端生成随机底图并抠出一块拼图，横向正确位置 target_x 只存服务端；
# 前端拖动滑块后回传 x，误差 ≤ SLIDER_TOLERANCE 视为通过。
# 流程：GET /auth/captcha 取图 → POST /auth/captcha/verify 校验（失败即作废，
# 防拖库爆破）→ 注册时 captchaId 必须处于「已通过滑块校验」状态。
SLIDER_BG_W = 300            # 底图宽
SLIDER_BG_H = 150            # 底图高
SLIDER_PIECE = 44            # 拼图方块边长
SLIDER_KNOB_R = 9            # 拼图凸起/凹口半径
SLIDER_PAD = 8               # 拼图位置距边缘最小留白
SLIDER_TOLERANCE = 5         # 横向位置容差（px）
CAPTCHA_TTL_SECONDS = 300    # 5 分钟有效

# captcha_id -> (target_x, 过期时间戳, 是否已通过滑块校验)
_slider_store: dict[str, tuple[int, float, bool]] = {}


def _cleanup_expired_captcha() -> None:
    now = time.time()
    expired = [cid for cid, (_, exp, _) in _slider_store.items() if now > exp]
    for cid in expired:
        _slider_store.pop(cid, None)


def _rand_range(lo: int, hi: int) -> int:
    """[lo, hi] 闭区间随机整数（secrets，避免可预测随机数）。"""
    return lo + secrets.randbelow(hi - lo + 1)


def _gen_slider_background() -> Image.Image:
    """生成随机底图：双色渐变 + 半透明随机形状 + 轻微模糊。"""
    w, h = SLIDER_BG_W, SLIDER_BG_H
    c1 = tuple(_rand_range(110, 240) for _ in range(3))
    c2 = tuple(_rand_range(60, 180) for _ in range(3))
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        row = tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
        draw.line([(0, y), (w, y)], fill=row)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for _ in range(_rand_range(9, 14)):
        color = tuple(_rand_range(0, 255) for _ in range(3)) + (_rand_range(35, 90),)
        shape = _rand_range(0, 2)
        x1, y1 = _rand_range(-40, w), _rand_range(-40, h)
        x2, y2 = x1 + _rand_range(30, 130), y1 + _rand_range(20, 90)
        if shape == 0:
            odraw.ellipse([x1, y1, x2, y2], fill=color)
        else:
            odraw.rectangle([x1, y1, x2, y2], fill=color)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img.filter(ImageFilter.GaussianBlur(0.8))


def _puzzle_mask() -> Image.Image:
    """拼图块与底图缺口共用的 alpha 蒙版（二者轮廓完全一致）。

    形状 = 方块 + 左侧凸起 + 右侧凹口（凸起朝向与缺口鼓包一致，拖到正确
    位置时拼图与缺口严丝合缝）。画布 (PIECE+R)×PIECE：方块占 [R, R+PIECE)，
    左凸起为圆心 (R, PIECE/2)、半径 R 的整圆（向左凸出 R），右凹口为圆心
    (R+PIECE, PIECE/2) 的减去圆。底图压暗与拼图抠图均以画布左上角为锚点。
    """
    p, r = SLIDER_PIECE, SLIDER_KNOB_R
    m = Image.new("L", (p + r, p), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([r, 0, r + p - 1, p - 1], radius=6, fill=255)
    d.ellipse([0, p // 2 - r, 2 * r, p // 2 + r], fill=255)       # 左凸起
    d.ellipse([p, p // 2 - r, p + 2 * r, p // 2 + r], fill=0)     # 右凹口
    return m


def _png_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def generate_slider_captcha() -> dict:
    """生成滑块拼图验证码。

    返回 dict：captcha_id / background（底图 data URI，含缺口）/
    piece（拼图块 data URI，RGBA 透明背景）/ slider_y（拼图块纵向位置）。
    横向正确位置 target_x 不下发，仅存服务端；x/y 均为拼图画布（含左凸起）
    左上角锚点，与前端拖动上报的横向坐标同语义。
    """
    p, r, pad = SLIDER_PIECE, SLIDER_KNOB_R, SLIDER_PAD
    target_x = _rand_range(pad, SLIDER_BG_W - (p + r) - pad)
    target_y = _rand_range(pad, SLIDER_BG_H - p - pad)

    bg = _gen_slider_background()
    mask = _puzzle_mask()

    # 抠出拼图块（RGBA；纹理取自缺口处保持正向，仅轮廓形状定向）
    region = bg.crop((target_x, target_y, target_x + p + r, target_y + p))
    piece = Image.new("RGBA", (p + r, p), (0, 0, 0, 0))
    piece.paste(region, (0, 0), mask)

    # 底图上压暗缺口区域（与拼图块同轮廓）
    shade = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    dark = Image.new("RGBA", (p + r, p), (0, 0, 0, 115))
    shade.paste(dark, (target_x, target_y), mask)
    bg = Image.alpha_composite(bg.convert("RGBA"), shade).convert("RGB")

    _cleanup_expired_captcha()
    captcha_id = secrets.token_urlsafe(16)
    _slider_store[captcha_id] = (target_x, time.time() + CAPTCHA_TTL_SECONDS, False)
    return {
        "captcha_id": captcha_id,
        "background": _png_data_uri(bg),
        "piece": _png_data_uri(piece),
        "slider_y": target_y,
    }


def verify_slider_captcha(captcha_id: str, x: int) -> bool:
    """校验滑块横向位置（x 为拼图画布左上角的横向自然坐标，与生成锚点同语义）。

    成功：该 captcha_id 标记为已验证（保留至过期，注册时消费）；
    失败：无论错位/过期/不存在均立即作废该条记录（一次性，防爆破）。
    """
    entry = _slider_store.get(captcha_id or "")
    if entry is None:
        return False
    target_x, expire_at, _ = entry
    if time.time() > expire_at:
        _slider_store.pop(captcha_id, None)
        return False
    try:
        offset = int(x)
    except (TypeError, ValueError):
        _slider_store.pop(captcha_id, None)
        return False
    if abs(offset - target_x) <= SLIDER_TOLERANCE:
        _slider_store[captcha_id] = (target_x, expire_at, True)
        return True
    _slider_store.pop(captcha_id, None)
    return False


def consume_verified_captcha(captcha_id: str) -> bool:
    """注册时消费验证码：必须存在、未过期且已通过滑块校验，取出即销毁（一次性）。"""
    entry = _slider_store.pop(captcha_id or "", None)
    if entry is None:
        return False
    _, expire_at, verified = entry
    return verified and time.time() <= expire_at
