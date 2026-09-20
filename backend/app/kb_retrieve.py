"""知识库检索：向量 Top-6 + FTS5 trigram Top-6 → RRF 融合 → 最终 Top KB_TOP_K。

- RRF：score = Σ 1/(60 + rank)，rank 为该路结果中的名次（1 起）。
- 展示与阈值用的 score 是余弦相似度（向量路才有）；KB_MIN_SCORE 与它比较。
- FTS 查询构造不出合法 MATCH 串（全是 <3 字符片段）时跳过 FTS 这一路，
  绝不把非法 MATCH 字符串塞给 SQLite。
"""
import asyncio
import logging
import re

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from . import kb_index, kb_ingest
from . import database as _database
from .config import KB

logger = logging.getLogger("uvicorn.error")

_RRF_K = 60
_PER_PATH_K = 6  # 每一路召回数（最终融合后再截 KB.top_k）

_SEPS = r"[\s，。！？；：、,.!?;:()（）\[\]「」【】]+"


def build_match_query(question: str, max_terms: int = 8) -> str | None:
    """把问题切成 ≥3 字符的片段（trigram 只支持 ≥3 字符子串匹配），拼成 OR MATCH 串。

    例：'服务器IP是多少' → '"服务器IP是多少"'；无可用片段时返回 None。
    """
    segs = [s.strip() for s in re.split(_SEPS, question or "")]
    segs = [s for s in segs if len(s) >= 3][:max_terms]
    if not segs:
        return None
    return " OR ".join('"' + s.replace('"', '""') + '"' for s in segs)


async def retrieve(db: AsyncSession, question: str, allow_vector: bool = True) -> list[dict]:
    """混合检索，返回 [{id, title, source_type, heading, content, score}]（最多 KB.top_k 条）。

    score 为余弦相似度（仅向量路命中时非 None）；整体为空列表表示两路均未命中。
    """
    # ── 向量路 ────────────────────────────────────────────────
    vec_ranked: list[tuple[int, float]] = []  # [(chunk_id, cosine)]
    if KB.vector_enabled and allow_vector and kb_index.vector_available:
        loaded = await kb_index.index.ensure_loaded(db)
        if loaded:
            try:
                qv = await asyncio.to_thread(kb_ingest.embed_query, question)
                vec_ranked = kb_index.index.top_k(qv, _PER_PATH_K)
            except kb_ingest.KBIngestError as e:
                # 查询向量失败降级为仅 FTS，不让一次网络抖动打死整条对话
                logger.warning("查询向量生成失败，降级为仅全文检索：%s", e)

    # ── FTS 路（trigram） ─────────────────────────────────────
    fts_ranked: list[int] = []
    if KB.hybrid_enabled and _database.fts_available:
        match_query = build_match_query(question)
        if match_query:
            result = await db.execute(
                text(
                    "SELECT c.id FROM kb_chunks_fts f "
                    "JOIN kb_chunks c ON c.id = f.rowid "
                    "WHERE kb_chunks_fts MATCH :q ORDER BY rank LIMIT :k"
                ),
                {"q": match_query, "k": _PER_PATH_K},
            )
            fts_ranked = [row[0] for row in result]

    if not vec_ranked and not fts_ranked:
        return []

    # ── RRF 融合 ──────────────────────────────────────────────
    rrf_scores: dict[int, float] = {}
    cosines: dict[int, float] = {}
    for rank, (chunk_id, cosine) in enumerate(vec_ranked, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank)
        cosines[chunk_id] = cosine
    for rank, chunk_id in enumerate(fts_ranked, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (_RRF_K + rank)

    ordered_ids = [
        chunk_id
        for chunk_id, _ in sorted(rrf_scores.items(), key=lambda kv: kv[1], reverse=True)[: KB.top_k]
    ]
    if not ordered_ids:
        return []

    # ── 取回切片明细（按融合顺序输出） ─────────────────────────
    result = await db.execute(
        text(
            "SELECT c.id, c.heading, c.content, d.title, d.source_type "
            "FROM kb_chunks c JOIN kb_documents d ON d.id = c.document_id "
            "WHERE c.id IN :ids"
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": ordered_ids},
    )
    by_id = {
        row[0]: {
            "id": row[0],
            "heading": row[1],
            "content": row[2],
            "title": row[3],
            "source_type": row[4],
        }
        for row in result
    }
    chunks = []
    for chunk_id in ordered_ids:
        if chunk_id in by_id:
            item = by_id[chunk_id]
            item["score"] = cosines.get(chunk_id)
            chunks.append(item)
    return chunks


def best_score(chunks: list[dict]) -> float | None:
    """所有命中切片中的最高余弦分（无向量分时返回 None）。"""
    scores = [c["score"] for c in chunks if c.get("score") is not None]
    return max(scores) if scores else None


def is_hit(chunks: list[dict]) -> bool:
    """命中判定：有向量分时与 KB_MIN_SCORE 比较；仅 FTS（无向量分）时非空即命中。"""
    if not chunks:
        return False
    top = best_score(chunks)
    if top is None:
        return True
    return top >= KB.min_score
