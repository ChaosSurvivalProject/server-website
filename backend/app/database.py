"""SQLite database setup using SQLAlchemy async + aiosqlite."""
import os
from pathlib import Path
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


async def get_db():
    """FastAPI dependency: provide an async database session."""
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)