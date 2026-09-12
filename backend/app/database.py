"""SQLite database setup using SQLAlchemy async + aiosqlite."""
import os
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from sqlalchemy.pool import StaticPool

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
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[int] = mapped_column(Integer, default=0)  # 0=draft, 1=published
    creator: Mapped[str] = mapped_column(String(100), nullable=False)
    publish_time: Mapped[str] = mapped_column(String(30), nullable=False)  # ISO format string
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)


class User(Base):
    """用户表：role 取值 'admin'（系统管理员）/ 'user'（注册普通用户）。

    注册用户的 username 即邮箱（email 与 username 同值冗余存储，
    email 可空，供后续邮箱验证 / 找回密码等扩展使用）。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


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