"""SQLite database setup using SQLAlchemy async + aiosqlite."""
import logging
import os
import re
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from sqlalchemy.pool import StaticPool

logger = logging.getLogger("uvicorn.error")

# Database file path (project root / data / announcements.db)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = os.environ.get("ANNOUNCEMENT_DB", BASE_DIR / "data" / "announcements.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE}"

# Ensure data directory exists
Path(DB_FILE).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 原始内容：contentType=html 时为富文本 HTML，markdown 时为 Markdown 源码
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="html")  # 'html'=富文本, 'markdown'=Markdown（渲染在前端）
    is_published: Mapped[int] = mapped_column(Integer, default=0)  # 0=draft, 1=published
    creator: Mapped[str] = mapped_column(String(100), nullable=False)
    publish_time: Mapped[str] = mapped_column(String(30), nullable=False)  # ISO format string
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)


# 用户状态（布尔语义用 int 的项目规约扩展为三态）
USER_STATUS_NORMAL = 1   # 正常
USER_STATUS_DISABLED = 0 # 禁用（无法登录，可重新启用）
USER_STATUS_DELETED = 2  # 已删除（软删除，无法登录，数据保留可恢复）
ROLE_ADMIN = "admin"
ROLE_USER = "user"


class User(Base):
    """用户表：role 取值 'admin'（系统管理员）/ 'user'（注册普通用户）。

    注册用户的 username 即邮箱（email 与 username 同值冗余存储，
    email 可空，供后续邮箱验证 / 找回密码等扩展使用）。
    nickname 为展示用昵称（可空，可修改）；username 为登录账号（不可修改）。

    status 用户状态（三态）：1=正常, 0=禁用, 2=已删除（软删除）。
    禁用与已删除均无法登录。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 展示用昵称（可修改）
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1=正常, 0=禁用, 2=已删除
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


# ── 存量表轻量迁移 ────────────────────────────────────────────────
# SQLite 下 SQLAlchemy 的 create_all 不会给已有表补新列，
# 因此对 users.status / users.nickname（用户管理功能引入）、
# announcements.content_type（公告 Markdown 支持引入）做幂等补列
# （同步连接直接执行 PRAGMA / ALTER，不经异步池）。
_user_extra_migrated = False
_announcement_content_migrated = False


def migrate_user_extra_columns() -> None:
    """users 表补 status / nickname 列（幂等；已存在的表结构不受影响）。"""
    global _user_extra_migrated
    if _user_extra_migrated:
        return
    try:
        import sqlite3

        con = sqlite3.connect(str(DB_FILE))
        try:
            col_names = [
                row[1] for row in con.execute("PRAGMA table_info('users')")
            ]
            if "status" not in col_names:
                con.execute(
                    "ALTER TABLE users ADD COLUMN status INTEGER NOT NULL DEFAULT 1"
                )
                con.commit()
                logger.info("已为 users 表补充 status 列（1=正常, 0=禁用, 2=已删除）")
            if "nickname" not in col_names:
                con.execute(
                    "ALTER TABLE users ADD COLUMN nickname VARCHAR(50)"
                )
                con.commit()
                logger.info("已为 users 表补充 nickname 列（展示用昵称，可空）")
        finally:
            con.close()
        _user_extra_migrated = True
    except Exception as e:
        # 迁移失败不阻断启动（新库 create_all 已含新列，仅存量库需要补）
        logger.warning("users 表 status/nickname 列迁移检查失败: %s", e)


def migrate_announcement_content_columns() -> None:
    """announcements 表补 content_type 列（幂等；已存在的表结构不受影响）。

    存量行经 ALTER 的 DEFAULT 'html' 自动归为富文本格式，
    保证 Markdown 功能上线前后端行为不变。
    """
    global _announcement_content_migrated
    if _announcement_content_migrated:
        return
    try:
        import sqlite3

        con = sqlite3.connect(str(DB_FILE))
        try:
            col_names = [
                row[1] for row in con.execute("PRAGMA table_info('announcements')")
            ]
            if "content_type" not in col_names:
                con.execute(
                    "ALTER TABLE announcements ADD COLUMN content_type VARCHAR(20) "
                    "NOT NULL DEFAULT 'html'"
                )
                con.commit()
                logger.info(
                    "已为 announcements 表补充 content_type 列（'html'=富文本, 'markdown'=Markdown）"
                )
        finally:
            con.close()
        _announcement_content_migrated = True
    except Exception as e:
        # 迁移失败不阻断启动（新库 create_all 已含新列，仅存量库需要补）
        logger.warning("announcements 表 content_type 列迁移检查失败: %s", e)


class FactionBetaApplication(Base):
    """阵营对战玩法内测资格申请。

    status 取值（布尔语义用 int 的项目规约扩展为三态）：
    0=待审核, 1=已通过, 2=未通过。
    username 对站点账号唯一：每账号一份申请，被拒后可重新提交（覆盖原记录重置为待审核）。
    """

    __tablename__ = "faction_beta_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    mc_id: Mapped[str] = mapped_column(String(50), nullable=False)  # MC 游戏 ID
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # 邮箱（联系渠道）
    faction: Mapped[str] = mapped_column(String(30), nullable=False)  # 期望阵营
    experience: Mapped[str] = mapped_column(String(20), nullable=False)  # PvP 经验
    weekly_hours: Mapped[str] = mapped_column(String(30), nullable=False)  # 每周可参与时长
    motivation: Mapped[str] = mapped_column(Text, nullable=False)  # 申请理由
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0=待审核, 1=已通过, 2=未通过
    review_note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_time: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)


async def get_db():
    """FastAPI dependency: provide an async database session."""
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 存量库补列（新库 create_all 已含新列，迁移幂等直接跳过）
    migrate_user_extra_columns()
    migrate_announcement_content_columns()