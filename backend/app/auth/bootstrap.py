"""启动引导：检测并初始化系统管理员账户。

系统启动（init_db 之后）时检查 users 表是否存在 xqly-admin：
- 已存在：不做任何事（不重置密码、不重复写密码文件）
- 不存在：随机生成强密码，写入数据目录下的 admin_initial_password.txt
  （0600 权限，仅首次初始化时写入），由管理员自行查看后登录。
"""
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from ..database import DB_FILE, User, async_session_maker
from .security import generate_strong_password, hash_password

logger = logging.getLogger("uvicorn.error")

ADMIN_USERNAME = "xqly-admin"
ADMIN_PASSWORD_FILE = "admin_initial_password.txt"


def _now_iso() -> str:
    """与公告字段一致：ISO 格式字符串 YYYY-MM-DDTHH:MM:SS。"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _write_password_file(password: str) -> Path:
    """将初始密码写入数据目录（与 SQLite 同目录，受 ANNOUNCEMENT_DB 影响）。"""
    path = Path(DB_FILE).parent / ADMIN_PASSWORD_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    # 先写临时文件再原子替换，避免半写入导致密码文件损坏
    tmp = path.with_suffix(".txt.tmp")
    tmp.write_text(password + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


async def ensure_admin() -> None:
    """检测系统管理员是否已初始化，未初始化则创建。"""
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.username == ADMIN_USERNAME))
        if result.scalar_one_or_none() is not None:
            return

        password = generate_strong_password()
        # 先落密码文件再入库：若文件写失败则不创建管理员，下次启动重试
        password_path = _write_password_file(password)
        admin = User(
            username=ADMIN_USERNAME,
            email=None,
            password_hash=hash_password(password),
            role="admin",
            create_time=_now_iso(),
        )
        db.add(admin)
        await db.commit()

        logger.warning(
            "已初始化系统管理员账户 [%s]，初始密码见文件: %s（首次登录后请尽快修改并删除该文件）",
            ADMIN_USERNAME,
            password_path,
        )
