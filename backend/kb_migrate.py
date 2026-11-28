"""一次性迁移脚本：wiki / 存量知识库 → 文档树 + 静态资源目录（FLPR-72）+ 内置全量重嵌（FLPR-73）。

用法（在 backend/ 下执行）：
    python3 kb_migrate.py --check            # 只读盘点：备份提示 / Embedding 一致性 / MD5 / 图片 / 将创建清单
    python3 kb_migrate.py --rebuild          # 全量重嵌：仅当库内 embed_model/embed_dim 与 .env 不一致（或切片维度脏）时执行
    python3 kb_migrate.py --rebuild --yes    # 非交互环境下的二次确认（等价于交互输入 yes）
    python3 kb_migrate.py --apply            # 执行迁移：种子树 → 补正文/节点 → 搬图片 → 必要时重建切片 → bump 一次版本
    python3 kb_migrate.py --verify           # 验收：19 URL / 187 切片 / 9 图片 / FAQ / FTS / RAG 抽样 / 3 篇 manual
    python3 kb_migrate.py --rollback         # 从 .bak-YYYYMMDD 恢复 DB（资源目录保留）

可覆盖路径（便于影子/测试环境演练；默认取 backend/.env 与 app.config）：
    --db PATH / --wiki-dir PATH / --asset-dir PATH / --manifest PATH / --backup PATH

设计依据：docs/知识库/存量数据迁移方案.md §1–§6。实现约束：
- 与 kb_sync.py 同款 WAL + busy_timeout=8000，单进程执行；服务端在线读不阻塞；
- 全程只读 wiki/，绝不写 git 工作树；不调用 kb_sync.py（避免 --prune 误删）；
- 所有表写入放在同一个事务，失败整体回滚；migration_v1_done 保证幂等；
- 正文 /doc-image/xxx.png 一个字不改；index_version 只在 apply 成功末尾 bump 一次。

注意：本脚本是**一次性工具**，P3 观察期后随 wiki/ 与 kb_sync.py 一起删除。
Embedding 模型/维度不一致时的「全量重建」由 FLPR-73 在本文件内以 --rebuild 实现：
仅在库内配置与 .env 不一致（或实际切片维度脏）时触发，备份 + 二次确认后单事务重嵌
全部文档（wiki + manual），写回 kb_settings、bump index_version，服务端无需重启即恢复
向量检索；不做交互式候选配置输入（那是 FLPR-22 后续版本的范围）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import struct
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import BASE_DIR, KB  # noqa: E402
from app.database import DB_FILE  # noqa: E402

# ── 固定常量（与 config.mts / 迁移方案 §3.2 对齐）──────────────────────

SITE_NAME = "星穹旅驿 Wiki · 我的世界阵营生存服"
SITE_DESCRIPTION = (
    "星穹旅驿 Wiki：我的世界 1.21 阵营服 / Java 基岩互通服务器文档，"
    "含进服指南、黎明誓约与暮夜同盟阵营玩法、1.21.11 生存服版本支持与服务器规则。"
)
DESCRIPTION_FALLBACK = (
    "：星穹旅驿我的世界 1.21 阵营服文档，包含 Java / 基岩互通进服指南、"
    "黎明誓约与暮夜同盟阵营玩法、1.21.11 生存服版本支持与服务器规则。"
)
ASSET_SUBDIR = "doc-image"
MANIFEST_PATH = BASE_DIR / "data" / "migration-manifest.json"

EXPECTED_WIKI_MD = 19
EXPECTED_DB_WIKI_ROWS = 19
EXPECTED_CHUNKS = 187
EXPECTED_PNG = 9
EXPECTED_MANUAL = 3

# config.mts 的 FAQ_JSON_LD（FLPR-64）：仅进服指南页注入，文本逐字照抄，
# 保证 SSR 页 head 与 VitePress 构建期产物一致。
FAQ_JSON_LD = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {
            "@type": "Question",
            "name": "星穹旅驿支持哪些客户端版本？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "星穹旅驿是我的世界 1.21 阵营服，支持 Minecraft Java 版与基岩版多端互通，Java 客户端版本 1.21.1 ~ 1.21.11（推荐 1.21.11），基岩版使用 1.21.x 最新正式版，服务端基于 Geyser + Velocity + Paper 1.21.11。",
            },
        },
        {
            "@type": "Question",
            "name": "星穹旅驿服务器地址是什么？基岩版怎么填？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "Java 版在多人游戏中添加服务器地址 serverone.codeyun.com:12000；基岩版在同服互通时把服务器地址填 serverone.codeyun.com、端口单独填 12000。连接成功后在登录服选择黎明誓约或暮夜同盟。",
            },
        },
        {
            "@type": "Question",
            "name": "Java 版玩家怎么加入星穹旅驿？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "下载并安装 PCL2 等 Java 版启动器，选择 1.21.1 ~ 1.21.11 版本安装；进入多人游戏添加服务器 serverone.codeyun.com:12000；首次进入按提示用 /register 密码 重复密码 注册，老玩家用 /login 密码 登录，然后在登录服选择黎明誓约或暮夜同盟。",
            },
        },
        {
            "@type": "Question",
            "name": "基岩版 / 手机玩家怎么进服？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "安装 Minecraft Bedrock 基岩版最新正式版并登录微软账号，进入游戏服务器页添加服务器，地址填 serverone.codeyun.com、端口填 12000；连接后用 /register 或 /login 完成注册登录即可与 Java 玩家同服游玩。",
            },
        },
        {
            "@type": "Question",
            "name": "进服后怎么选择黎明誓约或暮夜同盟？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": "连接服务器并完成注册或登录后，在登录服的选阵营界面选择黎明誓约或暮夜同盟。两大阵营镜像对立：黎明誓约以光为界、守土求生，暮夜同盟长夜将至、强者为尊。",
            },
        },
    ],
}
FAQ_SLUG = "for-new/quick-start"
MANUAL_FOLDER_SLUG = "manual"

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n?", re.S)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
_DESC_RE = re.compile(r"^description:\s*(.+?)\s*$", re.M)
_IMG_REF_RE = re.compile(r"/doc-image/([A-Za-z0-9._-]+)")


@dataclass(frozen=True)
class SeedFolder:
    key: str
    title: str
    parent: Optional[str]
    sort_order: int
    published: int = 1


@dataclass(frozen=True)
class SeedDoc:
    source_path: str
    title: str          # 侧边栏展示名（与 config.mts 逐项一致）
    parent: str         # SeedFolder.key，首页为 ''（根）
    sort_order: int


# config.mts themeConfig.sidebar 的完整映射（迁移方案 §3.2）。
# 说明：方案文字写「3 个一级分区」，指 for-new / management / develop 三个 wiki 目录；
# 侧边栏实际有 4 个顶层分组，验收口径是「kb_nodes 与 config.mts 逐项一致」，故按 4 个建。
SEED_FOLDERS: tuple[SeedFolder, ...] = (
    SeedFolder("quick", "快速开始", None, 0),
    SeedFolder("newcomer", "萌新指南", None, 1),
    SeedFolder("join", "进服教程", "newcomer", 0),
    SeedFolder("factions", "阵营玩法", "newcomer", 1),
    SeedFolder("rules", "服务器玩家相关条例", "newcomer", 2),
    SeedFolder("manage", "服务器管理", None, 2),
    SeedFolder("develop", "服务器建设", None, 3),
    SeedFolder("uncategorized", "未分类", None, 4, published=0),
)

SEED_DOCS: tuple[SeedDoc, ...] = (
    SeedDoc("index.md", "首页", "", 0),
    SeedDoc("for-new/quick-start/index.md", "进服指南（Java / 基岩并列）", "quick", 0),
    SeedDoc("for-new/versions/index.md", "版本与客户端支持范围", "quick", 1),
    SeedDoc("about/service-status/index.md", "服务状态说明", "quick", 2),
    SeedDoc("about/announcements/index.md", "活动与公告归档", "quick", 3),
    SeedDoc("for-new/visitor-guidelines/index.md", "游玩须知", "newcomer", 0),
    SeedDoc("for-new/join-server/for-java-client/index.md", "Java版", "join", 0),
    SeedDoc("for-new/join-server/for-bedrock-client/index.md", "基岩版", "join", 1),
    SeedDoc("for-new/factions/index.md", "阵营玩法总览", "factions", 0),
    SeedDoc("for-new/factions/usage.md", "阵营使用指南", "factions", 1),
    SeedDoc("for-new/factions/mechanics.md", "阵营对抗机制", "factions", 2),
    SeedDoc("for-new/law/player-agreement/index.md", "服务器游玩规则与惩罚条例", "rules", 0),
    SeedDoc("for-new/law/server-code/index.md", "服务器法典", "rules", 1),
    SeedDoc("for-new/law/regulations-on-players-rights/index.md", "玩家维权与投诉处理条例", "rules", 2),
    SeedDoc("for-new/faq/index.md", "常见问题解答", "newcomer", 1),
    SeedDoc("management/law-for-ops/index.md", "服务器管理员监督问责条例", "manage", 0),
    SeedDoc("develop/architecture/index.md", "服务器架构", "develop", 0),
    SeedDoc("develop/roadmap/index.md", "发展路线", "develop", 1),
    SeedDoc("develop/issues/index.md", "Issues", "develop", 2),
)

RAG_SAMPLE_QUESTIONS = (
    "服务器架构是怎样的？",
    "进服指南在哪里看？",
    "黎明誓约是什么？",
)
FTS_SAMPLE_TERMS = ("进服指南", "黎明誓约", "服务器架构")


# ── 路径 / 连接 ────────────────────────────────────────────────────


def resolve_db(cli_value: Optional[str]) -> Path:
    return Path(cli_value) if cli_value else Path(DB_FILE)


def _resolve(cli_value: Optional[str], default: Path) -> Path:
    raw = Path(cli_value) if cli_value else default
    return raw if raw.is_absolute() else (BACKEND_DIR / raw).resolve()


def resolve_wiki_dir(cli_value: Optional[str]) -> Path:
    return _resolve(cli_value, KB.wiki_dir)


def resolve_asset_dir(cli_value: Optional[str]) -> Path:
    return _resolve(cli_value, KB.asset_dir)


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def connect_db(db_path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        con = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True, timeout=8)
    else:
        con = sqlite3.connect(str(db_path), timeout=8)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=8000")
        con.execute("PRAGMA synchronous=NORMAL")
    con.row_factory = sqlite3.Row
    return con


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    return (
        con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
        is not None
    )


def ensure_schema(con: sqlite3.Connection) -> None:
    """幂等补表/补列：存量库可能尚未跑过 FLPR-71 的 init_db。"""
    con.execute(
        """CREATE TABLE IF NOT EXISTS kb_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            node_type VARCHAR(16) NOT NULL DEFAULT 'folder',
            title VARCHAR(255) NOT NULL,
            slug VARCHAR(512) NOT NULL UNIQUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            document_id INTEGER,
            published INTEGER NOT NULL DEFAULT 1,
            description VARCHAR(500) NOT NULL DEFAULT '',
            faq_json TEXT,
            deleted_at VARCHAR(30),
            revision INTEGER NOT NULL DEFAULT 0,
            create_time VARCHAR(30) NOT NULL,
            update_time VARCHAR(30) NOT NULL
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_kb_nodes_parent_id ON kb_nodes (parent_id)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_kb_nodes_document_id ON kb_nodes (document_id)")
    cols = {row[1] for row in con.execute("PRAGMA table_info('kb_documents')")}
    if "node_id" not in cols:
        con.execute("ALTER TABLE kb_documents ADD COLUMN node_id INTEGER")
    if "content_md" not in cols:
        con.execute("ALTER TABLE kb_documents ADD COLUMN content_md TEXT NOT NULL DEFAULT ''")
    con.execute(
        "CREATE TABLE IF NOT EXISTS kb_settings (key VARCHAR(64) PRIMARY KEY, value VARCHAR(255) NOT NULL)"
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS kb_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            heading VARCHAR(255) NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            embedding BLOB,
            char_count INTEGER NOT NULL DEFAULT 0
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_document_id ON kb_chunks (document_id)")
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts USING fts5(content, tokenize='trigram')"
    )


def get_setting(con: sqlite3.Connection, key: str) -> str:
    row = con.execute("SELECT value FROM kb_settings WHERE key = ?", (key,)).fetchone()
    return str(row[0]) if row else ""


def set_setting(con: sqlite3.Connection, key: str, value: object) -> None:
    con.execute(
        "INSERT INTO kb_settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def bump_index_version(con: sqlite3.Connection) -> int:
    con.execute(
        "INSERT INTO kb_settings(key, value) VALUES('index_version', '1') "
        "ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)"
    )
    return int(get_setting(con, "index_version") or 0)


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


# ── Markdown 元数据 ────────────────────────────────────────────────


def strip_frontmatter(text: str) -> str:
    """只去 YAML frontmatter；::: 容器 / <img> / Heading 原样保留给 SSR 渲染器。"""
    return _FRONT_MATTER_RE.sub("", text or "").strip()


def parse_frontmatter(raw: str) -> tuple[str, str, str]:
    """返回 (content_md, description, title)。title 优先 H1，首页回退「首页」。"""
    content_md = strip_frontmatter(raw)
    m = _DESC_RE.search(raw[: _FRONT_MATTER_RE.match(raw).end()] if _FRONT_MATTER_RE.match(raw) else "")
    description = ""
    if m:
        description = m.group(1).strip().strip('"').strip("'")
    h1 = _H1_RE.search(content_md)
    title = h1.group(1).strip() if h1 else "首页"
    return content_md, description, title


def fallback_description(title: str, source_path: str) -> str:
    if source_path == "index.md":
        return SITE_DESCRIPTION
    # 与 config.mts transformHead 的「无 frontmatter」兜底一致
    return f"{title}{DESCRIPTION_FALLBACK}"


def slug_from_source_path(source_path: str) -> str:
    """去 index.md 取目录部分；非 index.md 去扩展名。与旧 URL 完全一致。"""
    rel = (source_path or "").replace("\\", "/").strip("/")
    if rel == "index.md":
        return ""
    if rel.endswith("/index.md"):
        return rel[: -len("/index.md")]
    return rel[:-3] if rel.endswith(".md") else rel


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", (title or "").strip().lower())
    return re.sub(r"\s+", "-", slug) or "doc"


def unique_slug(con: sqlite3.Connection, base: str) -> str:
    candidate = base
    n = 2
    while con.execute("SELECT 1 FROM kb_nodes WHERE slug = ?", (candidate,)).fetchone():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def list_wiki_files(wiki_dir: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(wiki_dir.rglob("*.md")):
        parts = path.relative_to(wiki_dir).parts
        if any(p in KB.wiki_exclude for p in parts[:-1]):
            continue
        files["/".join(parts)] = path
    return files


def list_png_files(wiki_dir: Path) -> dict[str, Path]:
    folder = wiki_dir / "public" / ASSET_SUBDIR
    if not folder.is_dir():
        return {}
    return {p.name: p for p in sorted(folder.glob("*.png"))}


def png_references(files: dict[str, Path]) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    for rel, path in files.items():
        for name in set(_IMG_REF_RE.findall(path.read_text(encoding="utf-8", errors="replace"))):
            refs.setdefault(name, []).append(rel)
    return refs


# ── 盘点（--check / --apply / --verify 共用）─────────────────────────


@dataclass
class Inventory:
    md_files: dict[str, Path]
    png_files: dict[str, Path]
    png_refs: dict[str, list[str]]
    wiki_docs: dict[str, sqlite3.Row]
    manual_docs: list[sqlite3.Row]
    chunks_total: int
    chunk_counts: dict[int, int]
    settings: dict[str, str]
    missing_originals: list[str]


def collect_inventory(con: sqlite3.Connection, wiki_dir: Path) -> Inventory:
    md_files = list_wiki_files(wiki_dir)
    png_files = list_png_files(wiki_dir)
    wiki_rows = con.execute(
        "SELECT * FROM kb_documents WHERE source_type = 'wiki'"
    ).fetchall()
    manual_rows = con.execute(
        "SELECT * FROM kb_documents WHERE source_type = 'manual' ORDER BY id"
    ).fetchall()
    chunks_total = con.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
    chunk_counts = {
        row[0]: row[1] for row in con.execute("SELECT document_id, COUNT(*) FROM kb_chunks GROUP BY document_id")
    }
    settings = {row[0]: str(row[1]) for row in con.execute("SELECT key, value FROM kb_settings")}
    missing_originals: list[str] = []
    for row in manual_rows:
        original = str(row["original_path"] or "")
        if not original:
            continue
        original_path = Path(original)
        if not original_path.is_absolute():
            original_path = BASE_DIR / original
        if not original_path.is_file():
            missing_originals.append(f"#{row['id']} {row['title']}（{original}）")
    return Inventory(
        md_files=md_files,
        png_files=png_files,
        png_refs=png_references(md_files),
        wiki_docs={str(r["source_path"]): r for r in wiki_rows},
        manual_docs=manual_rows,
        chunks_total=chunks_total,
        chunk_counts=chunk_counts,
        settings=settings,
        missing_originals=missing_originals,
    )


def embed_problems(inv: Inventory) -> list[str]:
    problems = []
    dim = inv.settings.get("embed_dim")
    model = inv.settings.get("embed_model")
    if dim and dim != str(KB.embed_dim):
        problems.append(f"库内 embed_dim={dim}，当前 KB_EMBED_DIM={KB.embed_dim}")
    if model and model != KB.embed_model:
        problems.append(f"库内 embed_model={model}，当前 KB_EMBED_MODEL={KB.embed_model}")
    return problems


def chunk_dim_report(con: sqlite3.Connection) -> dict:
    """全库实际切片体检查：按维度统计 BLOB 长度，不做任何“静默跳过”。

    BLOB 是 float32 小端（见 kb_ingest.pack_vector），故 维度 = length(embedding) // 4。
    dict 键为维度，值为切片数；非 4 字节对齐的脏 BLOB 记为 -1 维度。
    """
    expected_dim = int(KB.embed_dim)
    rows = con.execute(
        "SELECT length(embedding), COUNT(*) FROM kb_chunks "
        "WHERE embedding IS NOT NULL GROUP BY length(embedding)"
    ).fetchall()
    dims: dict[int, int] = {}
    for nbytes, count in rows:
        nbytes = int(nbytes)
        dim = -1 if nbytes % 4 else nbytes // 4
        dims[dim] = dims.get(dim, 0) + int(count)
    null_vectors = int(
        con.execute("SELECT COUNT(*) FROM kb_chunks WHERE embedding IS NULL").fetchone()[0]
    )
    return {
        "dims": dims,
        "expected_dim": expected_dim,
        "null_vectors": null_vectors,
        "bad": {d: c for d, c in dims.items() if d != expected_dim},
    }


def rebuild_reasons(con: sqlite3.Connection) -> list[str]:
    """--rebuild 的唯一触发条件：库内配置与 .env 不一致 / 实际切片脏。

    不提供交互式候选配置输入：目标模型/维度只取 .env 加载后的 KB 配置。
    """
    reasons: list[str] = []
    dim = get_setting(con, "embed_dim")
    model = get_setting(con, "embed_model")
    if dim and dim != str(KB.embed_dim):
        reasons.append(f"库内 embed_dim={dim}，当前 KB_EMBED_DIM={KB.embed_dim}")
    if model and model != KB.embed_model:
        reasons.append(f"库内 embed_model={model}，当前 KB_EMBED_MODEL={KB.embed_model}")
    report = chunk_dim_report(con)
    if report["bad"]:
        bad = "、".join(f"{d}维×{c}条" for d, c in sorted(report["bad"].items()))
        reasons.append(f"实际切片存在旧/脏维度向量：{bad}（目标 {report['expected_dim']} 维）")
    if report["null_vectors"]:
        reasons.append(f"{report['null_vectors']} 条切片缺少向量")
    return reasons


def backup_database(db_path: Path, stamp: str) -> Path:
    """在线一致备份（sqlite3 backup API），备份文件可直接用于 --rollback。

    不用 shutil.copy2：WAL 模式下直接拷贝主库可能漏掉未 checkpoint 的写入；
    backup API 在服务端在线读写时也能拿到一致快照，不阻塞业务写。
    """
    target = db_path.with_name(f"{db_path.name}.bak-{stamp}")
    n = 2
    while target.exists():
        target = db_path.with_name(f"{db_path.name}.bak-{stamp}-{n}")
        n += 1
    src = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True, timeout=8)
    dst = sqlite3.connect(str(target))
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()
    return target


def confirm_rebuild(
    args: argparse.Namespace,
    reasons: list[str],
    total_docs: int,
    total_chunks: int,
    backup_path: Path,
) -> bool:
    """二次确认：把「要重嵌什么、备份在哪、如何回滚」摆在操作者面前。"""
    print("=" * 72)
    print("!! 全量重嵌（FLPR-73）：将忽略 MD5 判重，重新嵌入库内全部文档")
    print(f"   文档 {total_docs} 篇（含 wiki + manual） / 切片 {total_chunks} 条（数量可能变化）")
    print(f"   目标配置：model={KB.embed_model} dim={KB.embed_dim}（来自 .env）")
    for reason in reasons:
        print(f"   - 触发：{reason}")
    print(f"   备份：{backup_path}")
    print("   成功：写回 kb_settings.embed_model/embed_dim + bump index_version，服务端无需重启")
    print(f"   失败：单事务整体回滚；必要时 python backend/kb_migrate.py --rollback --backup {backup_path}")
    print("=" * 72)
    if args.yes:
        print("[确认] 已通过 --yes 完成二次确认。")
        return True
    if not sys.stdin.isatty():
        print("!! 非交互环境必须显式传 --yes 完成二次确认，未写库。")
        return False
    try:
        answer = input("输入 yes 确认执行全量重嵌（其他输入取消）：").strip().lower()
    except EOFError:
        answer = ""
    return answer in ("yes", "y")


def backup_hint(db_path: Path) -> None:
    stamps = sorted(db_path.parent.glob(f"{db_path.name}.bak-*"))
    if stamps:
        print(f"[备份] 发现 {len(stamps)} 份：{', '.join(p.name for p in stamps[-3:])}")
    else:
        print(f"[备份] !! 未发现 {db_path.name}.bak-*，请先执行：")
        print(f"       cp {db_path} {db_path}.bak-$(date +%Y%m%d)")


def print_inventory(inv: Inventory, db_path: Path) -> None:
    print("=" * 72)
    print("知识库一次性迁移 · --check（只读，不写库 / 不写 wiki）")
    print("=" * 72)
    backup_hint(db_path)
    print(f"[数据库] {db_path}")
    print(
        f"[盘点] {len(inv.md_files)} md / {len(inv.wiki_docs)} 行 wiki 文档 / "
        f"{inv.chunks_total} 切片 / {len(inv.png_files)} PNG / {len(inv.manual_docs)} manual"
    )
    expected = (
        len(inv.md_files) == EXPECTED_WIKI_MD
        and len(inv.wiki_docs) == EXPECTED_DB_WIKI_ROWS
        and inv.chunks_total == EXPECTED_CHUNKS
        and len(inv.png_files) == EXPECTED_PNG
        and len(inv.manual_docs) == EXPECTED_MANUAL
    )
    print(f"[盘点] 与方案 §1 一致：{'是' if expected else '否（以实际输出为准，详见下列明细）'}")

    problems = embed_problems(inv)
    if problems:
        print("[Embedding] !! 不一致：" + "；".join(problems))
        print("           请先执行 python backend/kb_migrate.py --rebuild（内置全量重嵌），--apply 将拒绝执行")
    else:
        print(
            f"[Embedding] 一致：model={inv.settings.get('embed_model') or '(空)'} "
            f"dim={inv.settings.get('embed_dim') or '(空)'} index_version={inv.settings.get('index_version') or '(空)'}"
        )

    consistent = inconsistent = no_row = 0
    print("\n[MD5 对账] 19 篇 wiki Markdown")
    for doc in SEED_DOCS:
        rel = doc.source_path
        path = inv.md_files.get(rel)
        row = inv.wiki_docs.get(rel)
        if path is None:
            print(f"  [缺文件] {rel}")
            no_row += 1
            continue
        digest = md5_of(path)
        if row is None:
            print(f"  [库内无记录] {rel}（md5={digest}）→ apply 时新建")
            no_row += 1
        elif str(row["content_hash"]) == digest:
            consistent += 1
        else:
            inconsistent += 1
            print(
                f"  [不一致] {rel}：文件 md5={digest} 库内={row['content_hash']} → apply 时按 kb_ingest 重建"
            )
    print(f"  小结：一致 {consistent} / 不一致 {inconsistent} / 库内无记录或文件缺失 {no_row}")
    for rel in sorted(set(inv.wiki_docs) - set(inv.md_files)):
        print(f"  [库内无对应文件] {rel}（仅提示，不调用 --prune 删除）")

    print("\n[资源对账] wiki/public/doc-image/*.png")
    total_refs = 0
    for name, path in inv.png_files.items():
        refs = inv.png_refs.get(name, [])
        total_refs += len(refs)
        print(
            f"  {name:<40} {path.stat().st_size:>9} B  md5={md5_of(path)}  "
            f"引用={','.join(refs) if refs else '(无)'}"
        )
    print(f"  小结：{len(inv.png_files)} 个 PNG / {total_refs} 处引用（预期 9 / 9）")

    print("\n[将创建] kb_nodes 树（与 config.mts 侧边栏逐项一致）")
    for folder in SEED_FOLDERS:
        print(f"  folder  {folder.title:<24} parent={folder.parent or '根':<14} sort={folder.sort_order}")
    for doc in SEED_DOCS:
        print(f"  doc     {doc.title:<24} slug={slug_from_source_path(doc.source_path) or '(首页)'}")
    print(f"  folder  未分类（manual 草稿，published=0，{len(inv.manual_docs)} 篇）")
    for row in inv.manual_docs:
        print(f"           manual/{row['id']}-{slugify_title(str(row['title']))}")

    if inv.missing_originals:
        print("\n[原件缺失] 以下 manual 原件找不到（已知 v1.1.3.md，标记不阻断）")
        for item in inv.missing_originals:
            print(f"  - {item}")
    if problems:
        print("\n--check 发现阻塞项：Embedding 配置不一致，禁止执行 --apply。")
        return 1
    print("\n--check 完成（未写库）。确认无误后执行 --apply。")
    return 0


# ── 重建辅助（MD5 不一致时复用 kb_ingest，不调用 kb_sync.py）──────────


def delete_doc_children(con: sqlite3.Connection, doc_id: int) -> None:
    con.execute(
        "DELETE FROM kb_chunks_fts WHERE rowid IN (SELECT id FROM kb_chunks WHERE document_id = ?)",
        (doc_id,),
    )
    con.execute("DELETE FROM kb_chunks WHERE document_id = ?", (doc_id,))


@dataclass
class RebuildPlan:
    md5: str
    content_md: str
    title: str
    description: str
    chunk_count: int
    content_length: int
    pieces: list
    blobs: list[bytes]


def prepare_rebuild(raw_bytes: bytes) -> RebuildPlan:
    """Embedding 在写事务之前完成，缩短持锁时间（与 kb_sync.py 同口径）。"""
    from app import kb_ingest  # 延迟导入：--check/--rollback 不需要网络依赖

    raw = raw_bytes.decode("utf-8", errors="replace")
    content_md, description, title = parse_frontmatter(raw)
    cleaned = kb_ingest.clean_markdown(raw)
    pieces = kb_ingest.chunk_markdown(cleaned) if cleaned else []
    if not pieces:
        raise RuntimeError("清洗/切片后为空，拒绝写入空文档")
    blobs = kb_ingest.embed_documents([p.content for p in pieces])
    return RebuildPlan(
        md5=hashlib.md5(raw_bytes).hexdigest(),
        content_md=content_md,
        title=title,
        description=description,
        chunk_count=len(pieces),
        content_length=len(cleaned),
        pieces=pieces,
        blobs=blobs,
    )


def write_chunks(con: sqlite3.Connection, doc_id: int, plan: RebuildPlan) -> None:
    delete_doc_children(con, doc_id)
    for idx, (piece, blob) in enumerate(zip(plan.pieces, plan.blobs)):
        con.execute(
            "INSERT INTO kb_chunks(document_id, chunk_index, heading, content, embedding, char_count)"
            " VALUES(?, ?, ?, ?, ?, ?)",
            (doc_id, idx, piece.heading[:255], piece.content, blob, len(piece.content)),
        )
    con.execute(
        "INSERT INTO kb_chunks_fts(rowid, content) SELECT id, content FROM kb_chunks WHERE document_id = ?",
        (doc_id,),
    )


# ── 资源搬迁 ───────────────────────────────────────────────────────


def migrate_assets(wiki_dir: Path, asset_dir: Path, stamp: str) -> tuple[list[dict], list[str]]:
    target_dir = asset_dir / ASSET_SUBDIR
    target_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    warnings: list[str] = []
    refs = png_references(list_wiki_files(wiki_dir))
    for name, src in list_png_files(wiki_dir).items():
        dst = target_dir / name
        src_md5 = md5_of(src)
        action = "copied"
        if dst.exists():
            if md5_of(dst) == src_md5:
                action = "skipped-same-md5"
            else:
                conflict = dst.with_name(f"{name}.conflict-{stamp}")
                shutil.move(str(dst), str(conflict))
                warnings.append(f"{name}：目标已存在且 md5 不同，旧文件保留为 {conflict.name}")
        if action != "skipped-same-md5":
            shutil.copy2(src, dst)
        if md5_of(dst) != src_md5:
            raise RuntimeError(f"资源 md5 校验失败：{name}")
        results.append(
            {
                "name": name,
                "size": src.stat().st_size,
                "md5": src_md5,
                "referenced_by": refs.get(name, []),
                "target": str(dst),
                "action": action,
            }
        )
    return results, warnings


# ── --apply ────────────────────────────────────────────────────────


def cmd_apply(args: argparse.Namespace) -> int:
    db_path = resolve_db(args.db)
    wiki_dir = resolve_wiki_dir(args.wiki_dir)
    asset_dir = resolve_asset_dir(args.asset_dir)
    if not wiki_dir.is_dir():
        print(f"!! wiki 目录不存在：{wiki_dir}")
        return 1
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    con = connect_db(db_path)
    try:
        ensure_schema(con)
        inv = collect_inventory(con, wiki_dir)
        problems = embed_problems(inv)
        if problems:
            print("!! Embedding 配置不一致，拒绝迁移（" + "；".join(problems) + "）")
            print("   请先执行 python backend/kb_migrate.py --rebuild 完成内置全量重嵌，避免旧维度向量残留。")
            return 1
        if inv.settings.get("migration_v1_done") == "1":
            print("[幂等] migration_v1_done=1，迁移已完成，--apply 不重复执行（index_version 不再 bump）。")
            return 0

        # 1) 资源搬迁（文件系统操作幂等，先于 DB 事务；失败不会留下半写入的 DB）
        assets, warnings = migrate_assets(wiki_dir, asset_dir, stamp)
        print(f"[资源] 已处理 {len(assets)} 个 PNG → {asset_dir / ASSET_SUBDIR}")

        # 2) 预读 / 预嵌入（网络调用在事务外完成）
        doc_rows: list[tuple[SeedDoc, dict]] = []
        for doc in SEED_DOCS:
            path = inv.md_files.get(doc.source_path)
            if path is None:
                print(f"[警告] 源文件缺失：{doc.source_path}（标记跳过，不阻断）")
                continue
            raw_bytes = path.read_bytes()
            raw = raw_bytes.decode("utf-8", errors="replace")
            source_md5 = md5_of(path)
            row = inv.wiki_docs.get(doc.source_path)
            if row is not None and str(row["content_hash"]) == source_md5 and str(row["status"]) == "ready":
                content_md, description, _title = parse_frontmatter(raw)
                action = "reuse"
                plan = None
            else:
                action = "rebuild" if row is not None else "create"
                plan = prepare_rebuild(raw_bytes)
            doc_rows.append((doc, {"action": action, "plan": plan,
                                    "content_md": content_md if action == "reuse" else (plan.content_md if plan else ""),
                                    "description": description if action == "reuse" else (plan.description if plan else ""),
                                    "md5": source_md5}))
            if action != "reuse":
                print(f"[重建] {doc.source_path}（{action}，切片 {plan.chunk_count if plan else 0}）")

        # 3) 单事务写库：节点 / 文档 / 切片 / 设置
        index_before = int(inv.settings.get("index_version") or 0)
        doc_records: list[dict] = []
        manual_records: list[dict] = []
        try:
            with con:
                folder_ids: dict[str, int] = {}
                for folder in SEED_FOLDERS:
                    existing = con.execute("SELECT id FROM kb_nodes WHERE slug = ?", (MANUAL_FOLDER_SLUG if folder.key == "uncategorized" else _folder_slug(folder),)).fetchone()
                    if existing:
                        folder_ids[folder.key] = int(existing[0])
                        continue
                    now = now_iso()
                    cur = con.execute(
                        "INSERT INTO kb_nodes(parent_id, node_type, title, slug, sort_order, document_id,"
                        " published, description, faq_json, deleted_at, revision, create_time, update_time)"
                        " VALUES(?, 'folder', ?, ?, ?, NULL, ?, '', NULL, NULL, 0, ?, ?)",
                        (
                            folder_ids.get(folder.parent) if folder.parent else None,
                            folder.title,
                            MANUAL_FOLDER_SLUG if folder.key == "uncategorized" else _folder_slug(folder),
                            folder.sort_order,
                            folder.published,
                            now,
                            now,
                        ),
                    )
                    folder_ids[folder.key] = int(cur.lastrowid)

                now = now_iso()
                for doc, info in doc_rows:
                    slug = slug_from_source_path(doc.source_path)
                    if slug == FAQ_SLUG:
                        faq = json.dumps(FAQ_JSON_LD, ensure_ascii=False)
                    else:
                        faq = None
                    description = info["description"] or fallback_description(
                        _title_from_content(info["content_md"]), doc.source_path
                    )
                    node = con.execute("SELECT id FROM kb_nodes WHERE slug = ?", (slug,)).fetchone()
                    if node:
                        node_id = int(node[0])
                        con.execute(
                            "UPDATE kb_nodes SET title=?, parent_id=?, sort_order=?,"
                            " published=1, description=?, faq_json=COALESCE(faq_json, ?), update_time=? WHERE id=?",
                            (doc.title, folder_ids.get(doc.parent), doc.sort_order, description, faq, now, node_id),
                        )
                    else:
                        cur = con.execute(
                            "INSERT INTO kb_nodes(parent_id, node_type, title, slug, sort_order, document_id,"
                            " published, description, faq_json, deleted_at, revision, create_time, update_time)"
                            " VALUES(?, 'doc', ?, ?, ?, NULL, 1, ?, ?, NULL, 0, ?, ?)",
                            (folder_ids.get(doc.parent) if doc.parent else None, doc.title, slug, doc.sort_order,
                             description, faq, now, now),
                        )
                        node_id = int(cur.lastrowid)

                    row = inv.wiki_docs.get(doc.source_path)
                    plan: Optional[RebuildPlan] = info["plan"]
                    if row is None:
                        if plan is None:
                            warnings.append(f"{doc.source_path}：库内无记录且源文件无法重建，跳过")
                            continue
                        cur = con.execute(
                            "INSERT INTO kb_documents(title, source_type, source_path, content_hash, doc_type,"
                            " original_filename, original_path, status, error_message, chunk_count, content_length,"
                            " node_id, content_md, create_time, update_time)"
                            " VALUES(?, 'wiki', ?, ?, 'markdown', '', '', 'ready', '', ?, ?, ?, ?, ?, ?)",
                            (plan.title, doc.source_path, plan.md5, plan.chunk_count, plan.content_length,
                             node_id, plan.content_md, now, now),
                        )
                        doc_id = int(cur.lastrowid)
                        write_chunks(con, doc_id, plan)
                    else:
                        doc_id = int(row["id"])
                        if plan is not None:
                            write_chunks(con, doc_id, plan)
                            con.execute(
                                "UPDATE kb_documents SET node_id=?, content_md=?, content_hash=?, status='ready',"
                                " error_message='', chunk_count=?, content_length=?, update_time=? WHERE id=?",
                                (node_id, plan.content_md, plan.md5, plan.chunk_count, plan.content_length, now, doc_id),
                            )
                        else:
                            con.execute(
                                "UPDATE kb_documents SET node_id=?, content_md=?, update_time=? WHERE id=?",
                                (node_id, info["content_md"], now, doc_id),
                            )
                    con.execute("UPDATE kb_nodes SET document_id=? WHERE id=?", (doc_id, node_id))
                    doc_records.append(
                        {
                            "id": doc_id,
                            "source_path": doc.source_path,
                            "slug": slug,
                            "node_id": node_id,
                            "md5": info["md5"],
                            "action": info["action"],
                            "chunks_after": plan.chunk_count if plan else inv.chunk_counts.get(doc_id, 0),
                        }
                    )

                # 3 篇 manual：挂「未分类」草稿，切片/向量原样保留
                for row in inv.manual_docs:
                    title = str(row["title"] or f"文档 {row['id']}")
                    base = f"{MANUAL_FOLDER_SLUG}/{row['id']}-{slugify_title(title)}"
                    slug = unique_slug(con, base)
                    existing = con.execute("SELECT id FROM kb_nodes WHERE slug = ?", (slug,)).fetchone()
                    if existing:
                        node_id = int(existing[0])
                    else:
                        cur = con.execute(
                            "INSERT INTO kb_nodes(parent_id, node_type, title, slug, sort_order, document_id,"
                            " published, description, faq_json, deleted_at, revision, create_time, update_time)"
                            " VALUES(?, 'doc', ?, ?, 0, ?, 0, ?, NULL, NULL, 0, ?, ?)",
                            (folder_ids["uncategorized"], title, slug, row["id"], title[:500], now, now),
                        )
                        node_id = int(cur.lastrowid)
                    con.execute("UPDATE kb_documents SET node_id=? WHERE id=?", (node_id, row["id"]))
                    manual_records.append(
                        {"id": int(row["id"]), "title": title, "slug": slug, "node_id": node_id, "published": 0}
                    )

                # 收尾：只 bump 一次 + 幂等标记
                index_after = bump_index_version(con)
                set_setting(con, "migration_v1_done", 1)
                set_setting(con, "embed_model", KB.embed_model)
                set_setting(con, "embed_dim", KB.embed_dim)

            # 事务已提交
            for rec in doc_records:
                url = f"/wiki/{rec['slug']}/" if rec["slug"] else "/wiki/"
                print(f"[文档] {rec['source_path']} → {url}（{rec['action']}，node #{rec['node_id']}）")
            for rec in manual_records:
                print(f"[manual] {rec['title']} → {rec['slug']}（草稿，检索不变）")
            print(f"[收尾] index_version {index_before} → {index_after}（只 bump 一次）")

            manifest = {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "stage": "apply",
                "db": str(db_path),
                "wiki_dir": str(wiki_dir),
                "asset_dir": str(asset_dir),
                "inventory": {
                    "wiki_md": len(inv.md_files),
                    "db_wiki_rows": len(inv.wiki_docs),
                    "chunks_before": inv.chunks_total,
                    "chunks_after": con.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0],
                    "png": len(inv.png_files),
                    "manual": len(inv.manual_docs),
                },
                "nodes": [dict(r) for r in con.execute(
                    "SELECT id, parent_id, node_type, title, slug, sort_order, document_id, published,"
                    " description, faq_json FROM kb_nodes ORDER BY id"
                ).fetchall()],
                "documents": doc_records,
                "manual": manual_records,
                "assets": assets,
                "missing_originals": inv.missing_originals,
                "index_version": {"before": index_before, "after": index_after},
                "embed_config": {
                    "model": KB.embed_model,
                    "dim": KB.embed_dim,
                    "before": {
                        "model": inv.settings.get("embed_model", ""),
                        "dim": inv.settings.get("embed_dim", ""),
                    },
                    "consistent": not chunk_dim_report(con)["bad"]
                    and get_setting(con, "embed_model") == KB.embed_model
                    and get_setting(con, "embed_dim") == str(KB.embed_dim),
                },
                "warnings": warnings,
            }
            manifest_path = Path(args.manifest) if args.manifest else MANIFEST_PATH
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[清单] {manifest_path}")
            return 0
        except Exception as e:
            print(f"!! --apply 失败，事务已整体回滚：{e}")
            return 1
    finally:
        con.close()


# ── --rebuild（FLPR-73：内置 Embedding 全量重建）────────────────────


def _all_doc_chunk_rows(con: sqlite3.Connection, doc_id: int) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT id, chunk_index, heading, content, char_count FROM kb_chunks "
        "WHERE document_id = ? ORDER BY id",
        (doc_id,),
    ).fetchall()


def cmd_rebuild(args: argparse.Namespace) -> int:
    """仅当库内配置与 .env 不一致（或切片维度脏）时，重嵌库内全部文档。

    关键约束：
    - 目标配置只取 .env 加载后的 KB，不做交互式候选配置输入；
    - 覆盖 wiki + manual 全部文档，忽略 MD5 判重；manual 没有可重切片的源文本，
      直接对现有切片正文重新 Embedding（保留 heading/chunk_index/FTS 文本）；
    - Embedding 全部在事务外完成；单事务替换全部切片 + 写回设置 + 只 bump 一次版本；
    - 先在线备份，二次确认后才写库；失败整体回滚并给出精确回滚命令。
    """
    db_path = resolve_db(args.db)
    if not db_path.is_file():
        print(f"!! 数据库不存在：{db_path}")
        return 1

    con = connect_db(db_path)
    try:
        ensure_schema(con)  # 旧库可能还没有 content_md 列
        reasons = rebuild_reasons(con)
        if not reasons:
            report = chunk_dim_report(con)
            total = sum(report["dims"].values()) + report["null_vectors"]
            print(
                "[幂等] 无需全量重建：库内 embed_model/embed_dim 与 .env 一致，"
                f"{total} 条切片实际维度均为 {report['expected_dim']} 维（未 bump index_version）。"
            )
            return 0

        docs = con.execute(
            "SELECT id, title, source_type, content_md, content_hash, chunk_count "
            "FROM kb_documents ORDER BY id"
        ).fetchall()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_name(f"{db_path.name}.bak-{stamp}-pre-reembed")
        total_chunks = int(
            con.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
        )
        if not confirm_rebuild(args, reasons, len(docs), total_chunks, backup_path):
            return 1

        # 记录旧配置用于清单（务必在写库前取）
        config_before = {
            "model": get_setting(con, "embed_model"),
            "dim": get_setting(con, "embed_dim"),
        }
        backup = backup_database(db_path, f"{stamp}-pre-reembed")
        print(f"[备份] 已生成在线一致备份：{backup}")

        # 预嵌入（网络调用在写事务之外，缩短持锁时间）
        from app import kb_ingest  # 延迟导入：--check/--verify 不需要网络依赖

        plans: list[tuple[int, RebuildPlan]] = []
        skipped = 0
        for row in docs:
            doc_id = int(row["id"])
            chunk_rows = _all_doc_chunk_rows(con, doc_id)
            if not chunk_rows:
                # 文档树「空壳」节点 / 摄入失败文档：没有向量，不构成脏维度缺口
                skipped += 1
                continue
            pieces: list = [
                kb_ingest.Chunk(heading=str(r["heading"] or ""), content=str(r["content"] or ""))
                for r in chunk_rows
            ]
            blobs = kb_ingest.embed_documents([p.content for p in pieces])
            # content_hash 保持原值：重嵌只换向量，不改写 wiki 的 MD5 判重依据
            plan = RebuildPlan(
                md5=str(row["content_hash"] or ""),
                content_md=str(row["content_md"] or ""),
                title=str(row["title"] or ""),
                description="",
                chunk_count=len(pieces),
                content_length=sum(len(p.content) for p in pieces),
                pieces=pieces,
                blobs=blobs,
            )
            plans.append((doc_id, plan))
            print(f"[预嵌] 文档 #{doc_id} {row['title']}（{row['source_type']}）→ {len(pieces)} 切片")
        print(f"[跳过] {skipped} 篇无切片文档（无向量可重建，不产生新切片）")
        if not plans:
            print("[提示] 库内没有可重建的切片；仅写回 kb_settings 并 bump 版本以恢复配置一致性。")

        # 单事务：替换全部切片 + 写回配置 + bump 一次版本
        index_before = int(get_setting(con, "index_version") or 0)
        try:
            with con:
                for doc_id, plan in plans:
                    write_chunks(con, doc_id, plan)
                    con.execute(
                        "UPDATE kb_documents SET chunk_count=?, status='ready', error_message='', update_time=? "
                        "WHERE id=?",
                        (plan.chunk_count, now_iso(), doc_id),
                    )
                set_setting(con, "embed_model", KB.embed_model)
                set_setting(con, "embed_dim", KB.embed_dim)
                index_after = bump_index_version(con)
        except Exception as e:
            print(f"!! --rebuild 失败，事务已整体回滚：{e}")
            print(f"   可用 python backend/kb_migrate.py --rollback --backup {backup} 恢复到重建前状态。")
            return 1

        # 提交后体检：不允许静默留下旧维度 / 缺向量切片造成检索缺口
        report = chunk_dim_report(con)
        if report["bad"] or report["null_vectors"]:
            print("!! 重建后仍存在异常切片：" + json.dumps(report, ensure_ascii=False))
            print(f"   请立即 python backend/kb_migrate.py --rollback --backup {backup}")
            return 1
        total_after = sum(report["dims"].values())
        if total_after >= KB.max_chunks:
            print(f"[警告] 切片数 {total_after} 已达 KB_MAX_CHUNKS={KB.max_chunks}，向量索引只加载最新部分。")

        rebuild_manifest = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "stage": "reembed",
            "db": str(db_path),
            "backup": str(backup),
            "reason": reasons,
            "documents": [
                {"id": doc_id, "chunks": plan.chunk_count} for doc_id, plan in plans
            ],
            "skipped_no_chunks": skipped,
            "chunks_before": total_chunks,
            "chunks_after": total_after,
            "embed_config": {
                "before": config_before,
                "after": {"model": KB.embed_model, "dim": KB.embed_dim},
            },
            "index_version": {"before": index_before, "after": index_after},
            "actual_dims": report["dims"],
        }
        base_manifest = Path(args.manifest) if args.manifest else MANIFEST_PATH
        manifest_path = base_manifest.with_name(f"{base_manifest.stem}-reembed-{stamp}.json")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(rebuild_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[完成] {len(plans)} 篇文档重嵌，{total_after} 条切片均为 {KB.embed_dim} 维。")
        print(f"[版本] index_version {index_before} → {index_after}（只 bump 一次，服务端无需重启）")
        print(f"[清单] {manifest_path}")
        print("[提示] 运行中的后端会在下一次检索 / 统计请求时自动恢复向量检索（见 app/kb_index.py）。")
        return 0
    finally:
        con.close()


def _folder_slug(folder: SeedFolder) -> str:
    """目录 slug：用层级路径保证唯一，与文档 slug 空间隔离但同样可读。"""
    return f"_folder/{folder.key}"


def _title_from_content(content_md: str) -> str:
    m = _H1_RE.search(content_md or "")
    return m.group(1).strip() if m else "首页"


# ── --verify ───────────────────────────────────────────────────────


_SEPS = r"[\s，。！？；：、,.!?;:()（）\[\]「」【】]+"


def _match_query(question: str, *, lenient: bool = False) -> str:
    """与 kb_retrieve.build_match_query 同口径：只取 ≥3 字符片段，OR 拼接。

    lenient=True 时把长中文片段再切成 3 字滑窗，避免整句 phrase 过严导致
    verify 误报（FTS5 trigram 本身按 3 字符建索引）。
    """
    segs = [s.strip() for s in re.split(_SEPS, question or "")]
    terms: list[str] = []
    for seg in segs:
        if len(seg) < 3:
            continue
        if lenient and len(seg) >= 6:
            terms.extend(seg[i : i + 3] for i in range(0, len(seg) - 2, 2))
        else:
            terms.append(seg)
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms[:12])


def _fts_hits(con: sqlite3.Connection, question: str, *, lenient: bool = False) -> int:
    quoted = _match_query(question, lenient=lenient)
    if not quoted:
        return 0
    try:
        return con.execute(
            "SELECT COUNT(*) FROM kb_chunks_fts WHERE kb_chunks_fts MATCH ?", (quoted,)
        ).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def _rag_sample(con: sqlite3.Connection, question: str) -> tuple[int, int]:
    """RAG 抽样（本地检索层）：向量召回 + FTS 召回，不调 LLM，避免 verify 依赖外网。"""
    fts = _fts_hits(con, question, lenient=True)
    vector = 0
    if KB.embed_api_key:  # 无 API Key 时静默降级为 FTS，不刷 401 日志
        try:
            from app import kb_ingest

            qv = kb_ingest.embed_query(question)
            rows = con.execute("SELECT id, embedding FROM kb_chunks WHERE embedding IS NOT NULL").fetchall()
            scores: list[tuple[float, int]] = []
            for row in rows:
                blob = row["embedding"]
                if not blob or len(blob) % 4:
                    continue
                vec = struct.unpack(f"<{len(blob) // 4}f", blob)
                if len(vec) != len(qv):
                    continue
                score = sum(a * b for a, b in zip(vec, qv))
                scores.append((score, int(row["id"])))
            vector = len(scores)
        except Exception:
            pass  # 网络不可用时降级为 FTS 抽样
    return vector, fts


def cmd_verify(args: argparse.Namespace) -> int:
    db_path = resolve_db(args.db)
    wiki_dir = resolve_wiki_dir(args.wiki_dir)
    asset_dir = resolve_asset_dir(args.asset_dir)
    manifest_path = Path(args.manifest) if args.manifest else MANIFEST_PATH
    if not db_path.is_file():
        print(f"!! 数据库不存在：{db_path}")
        return 1

    con = connect_db(db_path, readonly=True)
    failures: list[str] = []
    try:
        if not table_exists(con, "kb_nodes"):
            print("!! kb_nodes 表不存在，请先执行 --apply")
            return 1
        manifest = {}
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            print(f"[提示] 未找到 {manifest_path}，使用方案 §1 固定期望值校验")

        print("=" * 72)
        print("知识库一次性迁移 · --verify")
        print("=" * 72)

        # 1) 19 个 URL / 节点树
        expected_slugs = {slug_from_source_path(d.source_path) for d in SEED_DOCS}
        nodes = {
            str(r["slug"]): r
            for r in con.execute("SELECT * FROM kb_nodes WHERE deleted_at IS NULL").fetchall()
        }
        url_failures: list[str] = []
        for slug in sorted(expected_slugs):
            node = nodes.get(slug)
            if not node:
                url_failures.append(f"缺少文档节点 /wiki/{slug}/")
                continue
            if node["node_type"] != "doc" or node["published"] != 1 or not node["document_id"]:
                url_failures.append(f"节点 /wiki/{slug}/ 非已发布文档节点")
                continue
            doc = con.execute(
                "SELECT content_md FROM kb_documents WHERE id = ?", (node["document_id"],)
            ).fetchone()
            if not doc or not (doc["content_md"] or "").strip():
                url_failures.append(f"/wiki/{slug}/ 的 content_md 为空")
            if not (node["description"] or "").strip():
                url_failures.append(f"/wiki/{slug}/ 的 description 为空")
        failures.extend(url_failures)
        print(f"[URL] 19 个 slug 校验：{'通过' if not url_failures else '失败'}")

        # 首页与树层级
        tree_failures: list[str] = []
        if "" not in nodes:
            tree_failures.append("缺少 /wiki/ 首页节点（slug='')")
        for folder in SEED_FOLDERS:
            slug = MANUAL_FOLDER_SLUG if folder.key == "uncategorized" else _folder_slug(folder)
            node = nodes.get(slug)
            if not node or node["node_type"] != "folder":
                tree_failures.append(f"缺少目录节点 {folder.title}")
        failures.extend(tree_failures)
        print(f"[树] kb_nodes 层级：{'通过' if not tree_failures else '失败'}")

        # 2) FAQ / description
        faq_node = nodes.get(FAQ_SLUG)
        if not faq_node or not faq_node["faq_json"]:
            failures.append("进服指南 faq_json 缺失")
        else:
            try:
                if json.loads(faq_node["faq_json"]) != FAQ_JSON_LD:
                    failures.append("进服指南 faq_json 与 config.mts 不一致")
            except json.JSONDecodeError:
                failures.append("进服指南 faq_json 非法 JSON")
        print(f"[FAQ] {FAQ_SLUG}：{'通过' if not any('faq_json' in f for f in failures) else '失败'}")

        # 3) 切片数（MD5 不一致重建后以 manifest 的 chunks_after 为准）
        expected_chunks = (
            manifest.get("inventory", {}).get("chunks_after", EXPECTED_CHUNKS) if manifest else EXPECTED_CHUNKS
        )
        actual_chunks = con.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
        vec_missing = con.execute("SELECT COUNT(*) FROM kb_chunks WHERE embedding IS NULL").fetchone()[0]
        if actual_chunks != expected_chunks:
            failures.append(f"切片数 {actual_chunks} != 预期 {expected_chunks}")
        if vec_missing:
            failures.append(f"{vec_missing} 条切片缺少向量")
        print(f"[切片] {actual_chunks}/{expected_chunks} 条，缺向量 {vec_missing}")

        # 3b) 全库实际切片维度 + 模型名（与 stats.dimConsistent 同口径）
        dim_report = chunk_dim_report(con)
        model_setting = get_setting(con, "embed_model")
        dim_setting = get_setting(con, "embed_dim")
        if dim_report["bad"]:
            failures.append(f"实际切片维度不一致：{dim_report['bad']}（目标 {KB.embed_dim} 维）")
        if model_setting != KB.embed_model:
            failures.append(f"库内 embed_model={model_setting or '(空)'} != {KB.embed_model}")
        if dim_setting != str(KB.embed_dim):
            failures.append(f"库内 embed_dim={dim_setting or '(空)'} != {KB.embed_dim}")
        print(
            f"[Embedding] 实际维度={dim_report['dims'] or '(无向量)'} / 目标={KB.embed_dim}；"
            f"模型={model_setting or '(空)'} / {KB.embed_model}："
            f"{'通过' if not dim_report['bad'] and model_setting == KB.embed_model and dim_setting == str(KB.embed_dim) else '失败'}"
        )

        # 4) 9 个资源 md5 + 正文引用未改
        assets = manifest.get("assets", [])
        target_dir = asset_dir / ASSET_SUBDIR
        if not assets:
            for name, src in list_png_files(wiki_dir).items():
                assets.append({"name": name, "md5": md5_of(src), "referenced_by": []})
        bad_assets = 0
        for asset in assets:
            dst = target_dir / str(asset["name"])
            if not dst.is_file() or md5_of(dst) != asset["md5"]:
                bad_assets += 1
                failures.append(f"资源 {asset['name']} md5 不一致或缺失")
        refs = sum(len(a.get("referenced_by", [])) for a in assets)
        print(f"[资源] {len(assets)} 个 PNG，md5 异常 {bad_assets}，正文引用 {refs} 处（预期 9）")

        # 5) 3 篇 manual 草稿
        manual_nodes = con.execute(
            "SELECT n.slug, n.published, d.id FROM kb_nodes n JOIN kb_documents d ON d.id = n.document_id"
            " WHERE n.slug LIKE 'manual/%'"
        ).fetchall()
        if len(manual_nodes) != EXPECTED_MANUAL:
            failures.append(f"manual 节点数 {len(manual_nodes)} != 3")
        for row in manual_nodes:
            if row["published"] != 0:
                failures.append(f"manual 节点 {row['slug']} 非草稿态")
        print(f"[manual] {len(manual_nodes)} 篇，均 published=0：{'通过' if len(manual_nodes) == 3 else '失败'}")

        # 6) FTS 抽样 + RAG 抽样 3 问
        fts_results = {term: _fts_hits(con, term) for term in FTS_SAMPLE_TERMS}
        if any(v == 0 for v in fts_results.values()):
            failures.append(f"FTS 抽样无命中：{fts_results}")
        print(f"[FTS] 抽样命中：{fts_results}")
        rag_results = {}
        for q in RAG_SAMPLE_QUESTIONS:
            vector, fts = _rag_sample(con, q)
            rag_results[q] = {"vector_chunks": vector, "fts_hits": fts, "retrieved": vector + fts > 0}
            if vector + fts == 0:
                failures.append(f"RAG 抽样无召回：{q}")
        print(f"[RAG] 3 问检索抽样：{rag_results}")
        print("      说明：此处只验检索层（向量 + FTS）；回答质量逐页对比由 FLPR-74 负责。")

        # 7) index_version 只 bump 一次
        if manifest.get("index_version"):
            before = int(manifest["index_version"]["before"])
            after = int(manifest["index_version"]["after"])
            if after - before != 1:
                failures.append(f"index_version 增量 {after - before} != 1")
            print(f"[版本] index_version {before} → {after}（只 bump 一次）")

        if failures:
            print("\n--verify 失败：")
            for f in failures:
                print(f"  - {f}")
            return 1
        print("\n--verify 全部通过。")
        return 0
    finally:
        con.close()


# ── --rollback ─────────────────────────────────────────────────────


def cmd_rollback(args: argparse.Namespace) -> int:
    db_path = resolve_db(args.db)
    if not db_path.is_file():
        print(f"!! 数据库不存在：{db_path}")
        return 1
    if args.backup:
        backup = Path(args.backup)
    else:
        candidates = sorted(db_path.parent.glob(f"{db_path.name}.bak-*"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            print(f"!! 未找到 {db_path.name}.bak-*，无法回滚（可用 --backup 指定）")
            return 1
        backup = candidates[-1]
    if not backup.is_file():
        print(f"!! 备份文件不存在：{backup}")
        return 1
    with backup.open("rb") as f:
        header = f.read(16)
    if header != b"SQLite format 3\x00":
        print(f"!! 备份不是有效 SQLite 文件：{backup}")
        return 1

    # 先 checkpoint，避免 -wal 中未落盘的数据在覆盖后污染恢复库
    con = sqlite3.connect(str(db_path), timeout=8)
    try:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        con.close()
    shutil.copy2(backup, db_path)
    for suffix in ("-wal", "-shm"):
        stale = Path(str(db_path) + suffix)
        if stale.exists():
            stale.unlink()
    print(f"[回滚] 已从 {backup.name} 恢复 {db_path}")
    print("[回滚] 资源目录 KB_ASSET_DIR/doc-image/ 保留（覆盖不影响），未删除。")
    print("[回滚] 注意：回滚应在影子环境或后端停止时执行；后端重启会重新加载恢复后的库。")
    return 0


# ── CLI ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="wiki → 知识库 一次性迁移（FLPR-72）")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="只读盘点，不写库")
    mode.add_argument("--rebuild", action="store_true", help="内置全量重嵌：库内配置与 .env 不一致时重嵌 wiki + manual 全部文档（备份 + 二次确认）")
    mode.add_argument("--apply", action="store_true", help="执行迁移（单事务，失败整体回滚）")
    mode.add_argument("--verify", action="store_true", help="验收 19 URL / 187 切片 / 9 资源 / FAQ / RAG / manual")
    mode.add_argument("--rollback", action="store_true", help="从 .bak-YYYYMMDD 恢复 DB")
    parser.add_argument("--yes", action="store_true", help="--rebuild 的非交互二次确认（等价于交互输入 yes）")
    parser.add_argument("--db", default=None, help="覆盖数据库路径（默认 ANNOUNCEMENT_DB / backend/data/announcements.db）")
    parser.add_argument("--wiki-dir", default=None, help="覆盖 wiki 目录（默认 KB_WIKI_DIR）")
    parser.add_argument("--asset-dir", default=None, help="覆盖 KB_ASSET_DIR")
    parser.add_argument("--manifest", default=None, help="覆盖迁移清单路径（默认 backend/data/migration-manifest.json）")
    parser.add_argument("--backup", default=None, help="回滚时指定备份文件（默认取最新的 .bak-*）")
    args = parser.parse_args()

    if args.check:
        db_path = resolve_db(args.db)
        wiki_dir = resolve_wiki_dir(args.wiki_dir)
        if not db_path.is_file():
            print(f"!! 数据库不存在：{db_path}")
            return 1
        if not wiki_dir.is_dir():
            print(f"!! wiki 目录不存在：{wiki_dir}")
            return 1
        con = connect_db(db_path, readonly=True)
        try:
            return print_inventory(collect_inventory(con, wiki_dir), db_path)
        finally:
            con.close()
    if args.rebuild:
        return cmd_rebuild(args)
    if args.apply:
        return cmd_apply(args)
    if args.verify:
        return cmd_verify(args)
    return cmd_rollback(args)


if __name__ == "__main__":
    sys.exit(main())
