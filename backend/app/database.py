"""SQLite database setup using SQLAlchemy async + aiosqlite."""
import logging
import os
import re
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy import event
from sqlalchemy.pool import NullPool

logger = logging.getLogger("uvicorn.error")

# Database file path (project root / data / announcements.db)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = os.environ.get("ANNOUNCEMENT_DB", BASE_DIR / "data" / "announcements.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE}"

# Ensure data directory exists
Path(DB_FILE).parent.mkdir(parents=True, exist_ok=True)

# ⚠️ 连接池必须给**每个并发请求一条独立连接**（NullPool），不要改回 StaticPool。
# 原因（2026-09-27 实测确认）：StaticPool 只有一条底层连接，FastAPI 即使单 worker
# 也会**并发**处理请求，于是所有请求共享同一个 SQLite 事务——A 请求的 commit()
# 会连带提交 B 尚未提交的写入，而会话关闭时连接归还触发的 ROLLBACK 又会把
# 别人"已提交"的数据丢掉。实测 forum 的 like_count / comment_count / 标签 use_count
# 在 6 并发下有 1/5~2/3 的概率与关系表对不上，甚至直接死锁（ASGI 并发探测挂死）。
# 论坛的冗余计数（原子 SET x = x + 1）只有"关系行 INSERT 与计数 UPDATE 同事务提交"
# 才成立，因此每请求独立连接是**硬要求**，不是优化。
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
    echo=False,
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """每条新连接都要设连接级 PRAGMA。

    busy_timeout / synchronous 是**连接级**而非库级，原来在 init_db() 里设只对当时
    那条 StaticPool 连接有效；改成每请求独立连接后必须挂到 connect 事件上，
    否则 kb_sync.py（独立进程写同一个库文件）会拿不到 busy_timeout 而
    "database is locked"。journal_mode=WAL 是**库级**且持久化在文件里，只设一次即可。
    """
    cur = dbapi_connection.cursor()
    try:
        cur.execute("PRAGMA busy_timeout=8000")
        cur.execute("PRAGMA synchronous=NORMAL")
    finally:
        cur.close()


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
    # 禁言（论坛模块引入）：空串/None = 未禁言，now < mute_until 视为禁言中。
    # 与 status 正交——status=0 是「不能登录」，mute_until 是「能登录但不能发帖/评论」。
    mute_until: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


# ── 存量表轻量迁移 ────────────────────────────────────────────────
# SQLite 下 SQLAlchemy 的 create_all 不会给已有表补新列，
# 因此对 users.status / users.nickname（用户管理功能引入）、
# announcements.content_type（公告 Markdown 支持引入）做幂等补列
# （同步连接直接执行 PRAGMA / ALTER，不经异步池）。
_user_extra_migrated = False
_announcement_content_migrated = False
_user_mute_migrated = False


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


def migrate_user_mute_column() -> None:
    """users 表补 mute_until 列（论坛禁言功能引入；幂等）。

    空串/None = 未禁言；now < mute_until 视为禁言中。禁言与 status 三态正交：
    禁用（status=0）是不能登录，禁言是能登录浏览但不能发帖/评论（PRD §2）。
    迁移失败只记 warning 不阻断启动（与既有两个迁移函数同款）。
    """
    global _user_mute_migrated
    if _user_mute_migrated:
        return
    try:
        import sqlite3

        con = sqlite3.connect(str(DB_FILE))
        try:
            col_names = [row[1] for row in con.execute("PRAGMA table_info('users')")]
            if "mute_until" not in col_names:
                con.execute("ALTER TABLE users ADD COLUMN mute_until VARCHAR(30)")
                con.commit()
                logger.info("已为 users 表补充 mute_until 列（禁言到期时间，空=未禁言）")
        finally:
            con.close()
        _user_mute_migrated = True
    except Exception as e:
        logger.warning("users 表 mute_until 列迁移检查失败: %s", e)


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


# ── 知识库（智能客服 P0） ──────────────────────────────────────────
# 设计见 docs/智能客服/智能客服P0落地方案.md §3。与 Announcement/User 并列，不新建包。


class KBDocument(Base):
    """知识库文档：wiki 同步或后台手动粘贴产生，正文切片存 kb_chunks。"""

    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'wiki' | 'manual'
    source_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")  # wiki 相对路径
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")  # 内容 MD5
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")  # ready | failed
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)


class KBChunk(Base):
    """知识库切片：embedding 为 L2 归一化 float32 BLOB（点积即余弦）。"""

    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heading: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # 标题路径，进 prompt 用
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class KBSetting(Base):
    """知识库键值设置（index_version / embed_model / embed_dim / kb_schema_version）。"""

    __tablename__ = "kb_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False, default="")


class Staff(Base):
    """工作人员名片台账（员工名片模块 P0，见 docs/员工管理/员工名片模块需求规格.md §7.1）。

    status 仅两态：active / revoked（不引入第三态 expired）。
    过期判定权威是 valid_to（now > valid_to 即已过期），命中时由
    app.staff.expire_due() 把 active 回写为 revoked（revoked_reason='expired'）——
    status 只是快照，避免"定时任务漏跑 = 已过期却显示有效"（规格 §4.5）。

    revoked_reason 取值：离职 / 转岗 / 暂停 / 码异常（人工撤销，后台只能选）+
    'expired'（仅系统写入，后台下拉框不可见）。

    本表不得包含任何隐私字段（真实姓名 / 手机号 / 住址 / 身份证等），
    规格 §3.3 红线从数据层天然满足。
    """

    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    staff_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)  # 完整身份码（唯一，任何公开响应不下发）
    display_code: Mapped[str] = mapped_column(String(16), nullable=False, default="")  # 展示码（身份码后四位，页面只回这个）
    game_id: Mapped[str] = mapped_column(String(50), nullable=False)  # 游戏 ID
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 公开昵称（可空）
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # 服主/技术员/财务/管理员/建筑/客服
    duty: Mapped[str] = mapped_column(Text, nullable=False, default="")  # 职责范围
    avatar_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")  # 头像相对 URL（复用公告上传目录），默认空
    public_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 工作邮箱（可空）
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active | revoked
    card_version: Mapped[str] = mapped_column(String(16), nullable=False, default="V1")  # 名片版本
    valid_from: Mapped[str] = mapped_column(String(30), nullable=False)  # 生效时间（北京时间 ISO 字符串）
    valid_to: Mapped[str] = mapped_column(String(30), nullable=False)  # 到期时间（过期判定唯一权威）
    remark: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # 内部备注（任何对外响应不下发）
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)
    revoked_at: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # 撤销/失效时间
    revoked_reason: Mapped[str] = mapped_column(String(30), nullable=False, default="")  # 离职|转岗|暂停|码异常|expired


class ServerRecord(Base):
    """游戏服务器地址持久化（monitor.SERVERS 的权威存储，内存字典为读缓存）。

    id 沿用原有数字 id 语义；is_primary 布尔语义用 int（项目规约）。
    """

    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    is_primary: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)


# ── 社区（论坛）模块 ──────────────────────────────────────────────
# 实施依据：docs/论坛/论坛模块第一阶段PRD.md §4。9 张新表全部由
# Base.metadata.create_all 自动建（无 migrate_* 补列，唯一存量表补列是 users.mute_until）。
# 布尔语义一律 int（项目规约 §9-5）；时间列一律 String(30) 北京时间 ISO 字符串。
#
# 冗余计数（like_count / view_count / comment_count / favorite_count / use_count）
# 的唯一维护口径见 PRD §8-D6 / §8-D8——只挂在"文章是否处于 status=1"这一个转移点上。


class ForumCategory(Base):
    """板块（首页标签栏一项）。

    is_system=1 的两条是「首页」与「推荐」：不可删、不可改 code/name，只可改颜色与排序；
    文章禁止投稿到系统板块（PRD §6.2.3）。
    """

    __tablename__ = "forum_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)  # URL 参数用
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 展示名
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#6366f1")  # 彩色小圆点 hex
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 标签栏排序（升序）
    is_system: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1=系统板块
    is_hidden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1=标签栏隐藏（直链仍可访问）
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumTag(Base):
    """标签（与板块正交，一帖 ≤5 个，发帖时回车可新建）。

    use_count 冗余计数 = 被多少篇 status=1 文章引用，热门排序用（维护口径见 PRD §8-D8）。
    source='user' 即"发帖时自动新建"，后台按此筛出待清理标签。
    """

    __tablename__ = "forum_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_hot: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1=后台手动置热
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user")  # system | user
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumArticle(Base):
    """文章（先审后发：投稿 status=0，管理员通过后 1）。

    状态机（PRD §4.3 完整版）：
      0 待审核 → 1 已发布 / 2 已驳回；1 → 3 已下架；3 → 1 恢复；
      任意可编辑状态经作者编辑保存 → 0 待审核（resubmit_count +1，互动数据全部保留）。
    remove_by 决定"谁把文章移出公开"，进而决定作者能否编辑重提：
      '' 未移除 / 'author' 作者自删（可编辑重提） / 'admin' 管理员下架（不可编辑重提）。
    """

    __tablename__ = "forum_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 必填普通板块
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown 源码，原样入库
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="markdown")  # 第一阶段固定 markdown
    summary: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # 后端从正文截取，不让用户填
    cover_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")  # 封面相对 URL
    author_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0待审核 1已发布 2已驳回 3已下架
    review_note: Mapped[str] = mapped_column(String(255), nullable=False, default="")  # 驳回理由 / 下架原因
    is_top: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1=置顶
    is_featured: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1=精华
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 顶层评论数 + 回复数
    publish_time: Mapped[str] = mapped_column(String(30), nullable=False, default="")  # 非 status=1 时为空串
    remove_by: Mapped[str] = mapped_column(String(16), nullable=False, default="")  # '' | author | admin
    resubmit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 编辑重提次数
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)
    update_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumComment(Base):
    """评论（两级楼中楼：parent_id 只指向顶层评论；回复的回复仍挂同一顶层评论）。

    status 1=正常 2=已删除（软删，不出现在列表，comment_count 同步递减）。
    content 为纯文本——不接受 Markdown 与 HTML（PRD §8-D5），渲染时转义 + pre-wrap。
    """

    __tablename__ = "forum_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0=顶层评论
    reply_to_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 被回复者（仅用于显示"回复 @某人"）
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1=正常, 2=已删除
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumArticleLike(Base):
    """文章点赞关系（切换语义：存在即删、不存在即插）。"""

    __tablename__ = "forum_article_likes"
    __table_args__ = (UniqueConstraint("article_id", "user_id", name="uq_forum_article_likes"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumArticleFavorite(Base):
    """文章收藏关系（切换语义同点赞）。"""

    __tablename__ = "forum_article_favorites"
    __table_args__ = (
        UniqueConstraint("article_id", "user_id", name="uq_forum_article_favorites"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumCommentLike(Base):
    """评论点赞关系（顶层评论与回复都可点赞）。

    评论被删除（含删顶层时的连带回复）时同步删除对应行，不留孤儿数据（PRD §8-D15 ④）。
    """

    __tablename__ = "forum_comment_likes"
    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_forum_comment_likes"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumArticleTag(Base):
    """文章—标签关联表（不用逗号串字段，否则标签合并/重命名/删除会写坏数据）。"""

    __tablename__ = "forum_article_tags"
    __table_args__ = (
        UniqueConstraint("article_id", "tag_id", name="uq_forum_article_tags"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    create_time: Mapped[str] = mapped_column(String(30), nullable=False)


class ForumConfig(Base):
    """社区键值配置（结构仿 KBSetting）。

    读写走白名单（FORUM_CONFIG_KEYS），后台键预留 reward* 三项（PRD §0.3-E，第一阶段无 UI）。
    """

    __tablename__ = "forum_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False, default="")


# FTS5 可用性标志（init_db 时探测；个别发行版的 SQLite 未编译 FTS5 时降级为仅向量检索）
fts_available = True


async def init_db():
    """Create all tables on startup."""
    global fts_available
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # WAL：kb_sync.py 是另一个进程要写同一个库文件，不开 WAL 必然 database is locked。
        # journal_mode 是**库级**且持久化在库文件里，建表时设一次即可；
        # busy_timeout / synchronous 是**连接级**，已挂到 engine 的 "connect" 事件
        # （_set_sqlite_pragmas）——每请求独立连接后，在这里设只对这一条连接有效。
        (await conn.exec_driver_sql("PRAGMA journal_mode=WAL")).scalar()
        # FTS5 全文索引：trigram 分词（unicode61 不切分中文，中文检索会完全失效）。
        # 独立表（非 external content）：写入时显式指定 rowid = kb_chunks.id，
        # 删除时 DELETE ... WHERE rowid IN (...)，不需要触发器（决策记录 §4）。
        try:
            await conn.exec_driver_sql(
                "CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts "
                "USING fts5(content, tokenize='trigram')"
            )
            fts_available = True
        except Exception as e:  # 编译期未带 FTS5 的 SQLite：不阻断启动，降级仅向量
            fts_available = False
            logger.error("SQLite 不支持 FTS5，知识库全文检索不可用（仅向量检索）: %s", e)
    # 存量库补列（新库 create_all 已含新列，迁移幂等直接跳过）
    migrate_user_extra_columns()
    migrate_announcement_content_columns()
    migrate_user_mute_column()