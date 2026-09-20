"""wiki → 知识库 同步脚本（CLI，独立进程写同一个 SQLite 文件）。

用法（在 backend/ 下执行）：
  python3 kb_sync.py --check          # 只看变更，不写库
  python3 kb_sync.py --all            # 全量同步（逐文件按 MD5 判重，未变更零成本跳过）
  python3 kb_sync.py --incremental    # 增量同步（与 --all 同一套 MD5 机制，crontab 用）
  python3 kb_sync.py --list           # 列出库内所有文档与切片数
选项：
  --prune / --no-prune                # 删除"库内有记录但 wiki 文件已不存在"的文档（默认开）
  --wiki-dir PATH                     # 覆盖 KB_WIKI_DIR
  --force                             # Embedding 模型/维度与库内记录不一致时仍强制写入

增量同步机制（docs/智能客服P0落地方案.md §9）：
  对 KB_WIKI_DIR 下每个 *.md 计算 MD5
  ├─ kb_documents 中无 source_path 记录   → 新增（入库 + 切片 + Embedding）
  ├─ 有记录且 MD5 相同（且 status=ready） → 跳过（零成本）
  ├─ 有记录且 MD5 不同                    → 先删旧 chunks + FTS + 向量，再重建（幂等）
  └─ 有记录但文件已不存在                 → 删除记录及切片（--prune 控制，默认开）
  最后自增 kb_settings.index_version → 服务端下次对话自动重建内存索引，无需重启。

注意：本脚本是**另一个进程**写库，连接必须开 WAL + busy_timeout
（服务端 init_db 已设，两边都有才不会 database is locked）。
"""
import argparse
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app import kb_ingest  # noqa: E402
from app.config import BASE_DIR, KB  # noqa: E402
from app.database import DB_FILE  # noqa: E402

_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)


def connect_db() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_FILE), timeout=8)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=8000")
    con.execute("PRAGMA synchronous=NORMAL")
    ensure_tables(con)
    return con


def ensure_tables(con: sqlite3.Connection) -> None:
    """确保知识库表存在（与 app/database.py 的 ORM 定义保持一致）。

    服务端 init_db 也会建表（幂等）；这里补一份，让首次部署可以
    在服务从未启动过的全新库上直接执行同步。
    """
    con.execute(
        """CREATE TABLE IF NOT EXISTS kb_documents (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255) NOT NULL,
            source_type VARCHAR(16) NOT NULL,
            source_path VARCHAR(512) NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            status VARCHAR(16) NOT NULL,
            error_message TEXT NOT NULL,
            chunk_count INTEGER NOT NULL,
            content_length INTEGER NOT NULL,
            create_time VARCHAR(30) NOT NULL,
            update_time VARCHAR(30) NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS kb_chunks (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            heading VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB,
            char_count INTEGER NOT NULL
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_document_id ON kb_chunks (document_id)")
    con.execute(
        """CREATE TABLE IF NOT EXISTS kb_settings (
            key VARCHAR(64) NOT NULL PRIMARY KEY,
            value VARCHAR(255) NOT NULL
        )"""
    )
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts USING fts5(content, tokenize='trigram')"
    )


def resolve_wiki_dir(cli_value: str | None) -> Path:
    raw = Path(cli_value) if cli_value else KB.wiki_dir
    return raw if raw.is_absolute() else (BACKEND_DIR / raw).resolve()


def list_wiki_files(wiki_dir: Path) -> dict[str, Path]:
    """收集 wiki 目录下全部 *.md：{posix 相对路径: 绝对路径}，排除 KB_WIKI_EXCLUDE 目录。"""
    files: dict[str, Path] = {}
    for path in sorted(wiki_dir.rglob("*.md")):
        rel_parts = path.relative_to(wiki_dir).parts
        if any(part in KB.wiki_exclude for part in rel_parts[:-1]):
            continue
        files["/".join(rel_parts)] = path
    return files


def get_setting(con: sqlite3.Connection, key: str) -> str | None:
    row = con.execute("SELECT value FROM kb_settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_setting(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO kb_settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def bump_index_version(con: sqlite3.Connection) -> None:
    con.execute(
        "INSERT INTO kb_settings(key, value) VALUES('index_version', '1') "
        "ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)"
    )


def delete_doc_children(con: sqlite3.Connection, doc_id: int) -> None:
    """删除文档的全部切片与 FTS 行（幂等重建 / prune 共用）。"""
    con.execute("DELETE FROM kb_chunks_fts WHERE rowid IN (SELECT id FROM kb_chunks WHERE document_id = ?)", (doc_id,))
    con.execute("DELETE FROM kb_chunks WHERE document_id = ?", (doc_id,))


def doc_title(cleaned: str, rel_path: str) -> str:
    m = _H1_RE.search(cleaned)
    if m:
        return m.group(1).strip()[:255]
    return Path(rel_path).stem[:255]


def ingest_file(con: sqlite3.Connection, path: Path, rel_path: str, doc: tuple | None) -> str:
    """同步单个 wiki 文件；doc 为库内已有行 (id, content_hash, status)。返回 'created' | 'updated'。"""
    raw = path.read_bytes()
    content_hash = hashlib.md5(raw).hexdigest()
    content = raw.decode("utf-8", errors="replace")
    cleaned = kb_ingest.clean_markdown(content)
    pieces = kb_ingest.chunk_markdown(cleaned) if cleaned else []
    if not pieces:
        return "empty"

    # Embedding 在写库之前完成：持有写事务的时间只覆盖纯本地 SQL，不会与在线服务冲突
    blobs = kb_ingest.embed_documents([p.content for p in pieces])
    title = doc_title(cleaned, rel_path)
    from datetime import datetime

    from app.crud import _TZ

    now = datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S")

    if doc is None:
        cur = con.execute(
            "INSERT INTO kb_documents(title, source_type, source_path, content_hash, status,"
            " error_message, chunk_count, content_length, create_time, update_time)"
            " VALUES(?, 'wiki', ?, ?, 'ready', '', ?, ?, ?, ?)",
            (title, rel_path, content_hash, len(pieces), len(cleaned), now, now),
        )
        doc_id = cur.lastrowid
        action = "created"
    else:
        doc_id = doc[0]
        delete_doc_children(con, doc_id)
        con.execute(
            "UPDATE kb_documents SET title = ?, content_hash = ?, status = 'ready',"
            " error_message = '', chunk_count = ?, content_length = ?, update_time = ? WHERE id = ?",
            (title, content_hash, len(pieces), len(cleaned), now, doc_id),
        )
        action = "updated"

    for idx, (piece, blob) in enumerate(zip(pieces, blobs)):
        con.execute(
            "INSERT INTO kb_chunks(document_id, chunk_index, heading, content, embedding, char_count)"
            " VALUES(?, ?, ?, ?, ?, ?)",
            (doc_id, idx, piece.heading[:255], piece.content, blob, len(piece.content)),
        )
    con.execute(
        "INSERT INTO kb_chunks_fts(rowid, content)"
        " SELECT id, content FROM kb_chunks WHERE document_id = ?",
        (doc_id,),
    )
    return action


def check_embed_consistency(con: sqlite3.Connection, force: bool) -> bool:
    """库内 embed_model / embed_dim 与当前配置不一致时拒绝写入（防止脏检索引擎）。"""
    problems = []
    dim = get_setting(con, "embed_dim")
    model = get_setting(con, "embed_model")
    if dim and dim != str(KB.embed_dim):
        problems.append(f"库内 embed_dim={dim}，当前 KB_EMBED_DIM={KB.embed_dim}")
    if model and model != KB.embed_model:
        problems.append(f"库内 embed_model={model}，当前 KB_EMBED_MODEL={KB.embed_model}")
    if not problems:
        return True
    print("!! " + "；".join(problems))
    if force:
        print("!! 已按 --force 强制写入；建议之后执行 --all 全量重索引")
        return True
    print("!! 拒绝写入：请先全量重建（python3 kb_sync.py --all --force），或修正 backend/.env 配置")
    return False


def cmd_sync(wiki_dir: Path, check_only: bool, prune: bool, force: bool) -> int:
    files = list_wiki_files(wiki_dir)
    con = connect_db()
    try:
        if not check_only and not check_embed_consistency(con, force):
            return 1
        rows = con.execute(
            "SELECT id, source_path, content_hash, status FROM kb_documents WHERE source_type = 'wiki'"
        ).fetchall()
        by_path = {row[1]: row for row in rows}

        created = updated = skipped = failed = pruned = 0
        changed = False
        for rel_path, path in files.items():
            doc = by_path.get(rel_path)
            content_hash = hashlib.md5(path.read_bytes()).hexdigest()
            if (
                doc is not None
                and doc[2] == content_hash
                and doc[3] == "ready"
            ):
                skipped += 1
                continue
            if check_only:
                print(f"[check] {rel_path}: {'新增' if doc is None else '更新'}"
                      f"（{len(path.read_bytes())} 字节）")
                changed = True
                continue
            try:
                action = ingest_file(con, path, rel_path, doc)
            except Exception as e:  # 单文件失败不中断整轮同步
                failed += 1
                print(f"[失败] {rel_path}: {e}")
                continue
            if action == "created":
                created += 1
            elif action == "updated":
                updated += 1
            else:
                skipped += 1
                print(f"[跳过] {rel_path}: 清洗/切片后为空")
            print(f"[ok] {rel_path}")
            changed = True

        if prune and not check_only:
            for rel_path, row in by_path.items():
                if rel_path not in files:
                    delete_doc_children(con, row[0])
                    con.execute("DELETE FROM kb_documents WHERE id = ?", (row[0],))
                    pruned += 1
                    changed = True
                    print(f"[prune] {rel_path}: 文件已不存在，删除库内记录")
        elif prune and check_only:
            missing = [rel for rel in by_path if rel not in files]
            for rel in missing:
                print(f"[check] {rel}: 文件已不存在，将删除库内记录")
                changed = True

        if changed and not check_only:
            set_setting(con, "embed_model", KB.embed_model)
            set_setting(con, "embed_dim", KB.embed_dim)
            bump_index_version(con)  # 服务端下次对话自动重建内存索引，无需重启
        con.commit()
        if check_only:
            print(f"\n检查完成：{len(files)} 个 wiki 文件；变更 {created + updated} 处（未写库）")
        else:
            print(f"\n同步完成：新增 {created} / 更新 {updated} / 跳过 {skipped} / 删除 {pruned} / 失败 {failed}")
            if failed:
                return 1
        return 0
    finally:
        con.close()


def cmd_list() -> int:
    con = connect_db()
    try:
        rows = con.execute(
            "SELECT id, title, source_type, source_path, status, chunk_count, content_length, update_time"
            " FROM kb_documents ORDER BY source_type, source_path"
        ).fetchall()
        if not rows:
            print("知识库为空：先执行 python3 kb_sync.py --all")
            return 0
        print(f"{'ID':>4}  {'来源':<6} {'状态':<6} {'切片':>4} {'字符':>8}  标题（路径）")
        for row in rows:
            print(
                f"{row[0]:>4}  {row[2]:<6} {row[4]:<6} {row[5]:>4} {row[6]:>8}  {row[1]}"
                + (f"（{row[3]}）" if row[3] else "")
            )
        chunks = con.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
        print(f"\n共 {len(rows)} 篇文档 / {chunks} 条切片")
        return 0
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="wiki → 知识库 同步脚本")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="只看变更，不写库")
    mode.add_argument("--all", action="store_true", help="全量同步（MD5 判重，未变更零成本跳过）")
    mode.add_argument("--incremental", action="store_true", help="增量同步（crontab 用，同一套 MD5 机制）")
    mode.add_argument("--list", action="store_true", help="列出库内所有文档与切片数")
    parser.add_argument("--wiki-dir", default=None, help="覆盖 KB_WIKI_DIR（默认 ../wiki）")
    parser.add_argument("--prune", dest="prune", action="store_true", default=True,
                        help="删除文件已不存在的库内记录（默认开）")
    parser.add_argument("--no-prune", dest="prune", action="store_false", help="不删除已消失的文件")
    parser.add_argument("--force", action="store_true", help="Embedding 模型/维度不一致时仍强制写入")
    args = parser.parse_args()

    if args.list:
        return cmd_list()
    wiki_dir = resolve_wiki_dir(args.wiki_dir)
    if not wiki_dir.is_dir():
        print(f"!! wiki 目录不存在：{wiki_dir}（可用 --wiki-dir 指定）")
        return 1
    return cmd_sync(wiki_dir, check_only=args.check, prune=args.prune, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
