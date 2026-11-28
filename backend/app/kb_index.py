"""知识库内存向量索引（LangChain ``VectorStore`` 实现，stdlib 余弦，不用 numpy）。

- 仍从 ``kb_chunks.embedding``（float32 BLOB）重建，**SQLite 为唯一权威**，
  不引入外部向量数据库；向量只作进程内读缓存。
- 生产为香港 2C2G / 30G，内存充足；这里仍实现一个 stdlib 余弦的 LangChain
  ``VectorStore``，而不是 ``InMemoryVectorStore``（后者强依赖 numpy，为一个 20ms
  的检索引入十几 MB 常驻不值得）。接口语义与 LangChain 向量库一致
  （``Document`` + ``(doc, cosine)``），上层仍可按标准 ``VectorStore`` 使用。
- 版本失效：``kb_settings.index_version`` 每次摄入/删除后自增；服务端每次请求
  读一次轻量 SELECT 比对，不同才重建 —— **脚本改了库之后服务端无需重启**，
  这是个设计点，别改成"重启生效"。
- 加锁：asyncio.Lock 只保护重建；查询本身无副作用，可无锁。
"""
import asyncio
import logging
from array import array
from heapq import nlargest
from operator import mul
from typing import Any, Iterable

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import kb_ingest
from .config import KB

logger = logging.getLogger("uvicorn.error")

# 向量检索可用性开关：startup_check 发现库内 embed_dim/模型与配置不一致时置 False
# （只记日志不阻断启动，自动降级为仅 FTS + 引导话术，见 docs/智能客服/智能客服P0落地方案.md §5.9）
vector_available = True


async def vector_problems(db: AsyncSession) -> list[str]:
    """库内配置 + 全库实际切片维度体检；空列表表示向量检索可以安全启用。

    与 kb_migrate.chunk_dim_report 同口径：BLOB 为 float32 小端，
    维度 = length(embedding) // 4。缺设置 / 脏维度 / 缺向量都必须显式暴露，
    不允许“静默丢弃脏向量”造成检索缺口。空库（无切片）不因缺设置而报警。
    """
    problems: list[str] = []
    total = int((await db.execute(text("SELECT COUNT(*) FROM kb_chunks"))).scalar_one())
    dim_row = (
        await db.execute(text("SELECT value FROM kb_settings WHERE key='embed_dim'"))
    ).first()
    model_row = (
        await db.execute(text("SELECT value FROM kb_settings WHERE key='embed_model'"))
    ).first()
    dim = str(dim_row[0]) if dim_row else ""
    model = str(model_row[0]) if model_row else ""
    if not total:
        return problems
    if dim != str(KB.embed_dim):
        problems.append(f"库内 embed_dim={dim or '(空)'}，当前 KB_EMBED_DIM={KB.embed_dim}")
    if model != KB.embed_model:
        problems.append(f"库内 embed_model={model or '(空)'}，当前 KB_EMBED_MODEL={KB.embed_model}")
    rows = (
        await db.execute(
            text(
                "SELECT length(embedding), COUNT(*) FROM kb_chunks "
                "WHERE embedding IS NOT NULL GROUP BY length(embedding)"
            )
        )
    ).fetchall()
    bad: list[tuple[int, int]] = []
    for nbytes, count in rows:
        n = int(nbytes)
        d = -1 if n % 4 else n // 4
        if d != KB.embed_dim:
            bad.append((d, int(count)))
    if bad:
        detail = "、".join(f"{d}维×{c}条" for d, c in sorted(bad))
        problems.append(f"实际切片维度异常：{detail}（目标 {KB.embed_dim} 维）")
    nulls = int(
        (
            await db.execute(text("SELECT COUNT(*) FROM kb_chunks WHERE embedding IS NULL"))
        ).scalar_one()
    )
    if nulls:
        problems.append(f"{nulls} 条切片缺少向量")
    return problems


async def refresh_vector_available(db: AsyncSession) -> list[str]:
    """运行时复核向量可用性，返回问题清单。

    startup_check 发现不一致时会把开关置 False；迁移脚本是独立进程，无法翻转
    运行中服务的内存开关。这里在每次检索 / 统计请求（开关关闭时）重新读库，
    kb_settings 与实际维度恢复一致后立即自愈，**无需重启后端**。
    """
    global vector_available
    problems = await vector_problems(db)
    if problems and vector_available:
        vector_available = False
        logger.error("知识库向量检索已关闭（仅 FTS）：%s", "；".join(problems))
    elif not problems and not vector_available:
        vector_available = True
        logger.info("知识库向量检索已在运行时恢复（迁移重建已写回一致配置）")
    return problems


class StdlibCosineVectorStore(VectorStore):
    """LangChain ``VectorStore`` 的极简实现：纯 stdlib 点积（向量已 L2 归一化）。

    2000×1024 上限实测 <20 ms/query，远小于远端 LLM 延迟（决策记录 §2.2）。
    """

    def __init__(self, embedding: Embeddings) -> None:
        self._embedding = embedding
        self._ids: list[str] = []
        self._vectors: list[array] = []  # array('f')：与库内 BLOB 同构，内存 ≈4KB/向量
        self._metadatas: list[dict] = []
        self._texts: list[str] = []

    @property
    def embeddings(self) -> Embeddings:  # type: ignore[override]
        return self._embedding

    def add_vectors(
        self,
        ids: list[str],
        vectors: list[array | list[float]],
        metadatas: list[dict] | None = None,
    ) -> list[str]:
        """直接写入已算好的向量（重建索引时用，避免再打一遍 Embedding 网络）。"""
        metadatas = metadatas or [{} for _ in vectors]
        for vec_id, vec, meta in zip(ids, vectors, metadatas):
            self._ids.append(str(vec_id))
            # 统一转 array('f')，与 kb_chunks.embedding 的 float32 BLOB 同口径，省内存
            self._vectors.append(vec if isinstance(vec, array) else array("f", vec))
            self._metadatas.append(meta)
            self._texts.append("")  # 正文不回内存，命中后按 id 回库取
        return [str(i) for i in ids]

    def add_texts(  # type: ignore[override]
        self,
        texts: Iterable[str],
        metadatas: list[dict] | None = None,
        *,
        ids: list[str] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        texts = list(texts)
        vectors = self._embedding.embed_documents(texts)
        if ids is None:
            ids = [str(i) for i in range(len(texts))]
        return self.add_vectors(ids, vectors, metadatas)

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> list[Document]:  # type: ignore[override]
        vector = self._embedding.embed_query(query)
        return self.similarity_search_by_vector(vector, k=k, **kwargs)

    def similarity_search_by_vector(
        self, embedding: list[float], k: int = 4, **kwargs: Any
    ) -> list[Document]:
        return [doc for doc, _ in self.similarity_search_with_score_by_vector(embedding, k=k, **kwargs)]

    def similarity_search_with_score_by_vector(
        self,
        embedding: list[float],
        k: int = 4,
        **kwargs: Any,
    ) -> list[tuple[Document, float]]:
        if not self._vectors or len(embedding) != len(self._vectors[0]):
            return []
        scored = ((sum(map(mul, vec, embedding)), i) for i, vec in enumerate(self._vectors))
        return [
            (
                Document(
                    id=self._ids[i],
                    page_content=self._texts[i],
                    metadata=self._metadatas[i],
                ),
                float(score),
            )
            for score, i in nlargest(k, scored)
        ]

    @classmethod
    def from_texts(  # type: ignore[override]
        cls,
        texts: list[str],
        embedding: Embeddings,
        metadatas: list[dict] | None = None,
        *,
        ids: list[str] | None = None,
        **kwargs: Any,
    ) -> "StdlibCosineVectorStore":
        store = cls(embedding)
        store.add_texts(texts, metadatas, ids=ids)
        return store


class VectorIndex:
    """与 kb_chunks 表同构的内存向量库：``StdlibCosineVectorStore`` + chunk_id 元数据。"""

    def __init__(self) -> None:
        self.ids: list[int] = []
        self.dim: int = 0
        self.version: str | None = None  # 对应 kb_settings.index_version
        self.dim_mismatch_count: int = 0  # 实际维度与配置不符的切片数（不允许静默丢弃）
        self._store: StdlibCosineVectorStore | None = None
        self._lock = asyncio.Lock()

    @property
    def rows(self) -> list[int]:
        """兼容原有 ``bool(index.rows)`` 语义：有向量行即非空。"""
        return self.ids

    async def _read_version(self, db: AsyncSession) -> str:
        row = (
            await db.execute(text("SELECT value FROM kb_settings WHERE key = 'index_version'"))
        ).first()
        return str(row[0]) if row else "0"

    async def ensure_loaded(self, db: AsyncSession) -> bool:
        """读 index_version 并按需重建。版本相同则零开销直接返回（一次轻量 SELECT）。

        返回 False 表示索引不可用（无向量数据或维度异常），调用方应跳过向量检索。
        """
        current = await self._read_version(db)
        if self.version == current:
            return bool(self.ids)
        async with self._lock:
            current = await self._read_version(db)  # double-check：等锁期间可能已被别的协程重建
            if self.version == current:
                return bool(self.ids)
            await self._rebuild(db, current)
        return bool(self.ids)

    async def _rebuild(self, db: AsyncSession, version: str) -> None:
        """SELECT 最新 KB_MAX_CHUNKS 条向量重建内存向量库；越界时打 WARNING。"""
        result = await db.execute(
            text(
                "SELECT id, embedding FROM kb_chunks "
                "WHERE embedding IS NOT NULL ORDER BY id DESC LIMIT :lim"
            ),
            {"lim": KB.max_chunks},
        )
        ids: list[str] = []
        vectors: list[array] = []
        metadatas: list[dict] = []
        dim_mismatch = 0
        for chunk_id, blob in result:
            arr = array("f")
            arr.frombytes(bytes(blob))
            if len(arr) != KB.embed_dim:
                dim_mismatch += 1  # 脏行直接丢弃，不让单条坏数据炸掉整个索引
                continue
            ids.append(str(chunk_id))
            vectors.append(arr)
            metadatas.append({"chunk_id": int(chunk_id)})

        store = StdlibCosineVectorStore(embedding=kb_ingest.get_embeddings())
        if ids:
            store.add_vectors(ids, vectors, metadatas)

        if len(ids) >= KB.max_chunks:
            logger.warning("知识库向量数已达 KB_MAX_CHUNKS=%d 上限，仅加载最新部分", KB.max_chunks)
        self.dim_mismatch_count = dim_mismatch
        if dim_mismatch:
            # 脏维度向量不能被静默跳过：下面的 refresh_vector_available 会关闭整路
            # 向量检索（降级为 FTS），等全量重嵌后自愈，避免留下检索缺口。
            logger.error(
                "知识库有 %d 条向量维度与 KB_EMBED_DIM 不符，已关闭向量检索（避免检索缺口），"
                "请执行 python backend/kb_migrate.py --rebuild 做全量重嵌",
                dim_mismatch,
            )
        self.ids, self.dim, self.version, self._store = [int(i) for i in ids], KB.embed_dim, version, store
        await refresh_vector_available(db)
        logger.info("知识库向量索引已加载：%d 条切片（index_version=%s）", len(ids), version)

    def top_k(self, qv: list[float], k: int) -> list[tuple[int, float]]:
        """返回 [(chunk_id, 余弦相似度), ...]，按相似度降序。"""
        if self._store is None or not self.ids or len(qv) != self.dim:
            return []
        results = self._store.similarity_search_with_score_by_vector(qv, k=k)
        pairs: list[tuple[int, float]] = []
        for doc, score in results:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id is not None:
                pairs.append((int(chunk_id), float(score)))
        return pairs


# 模块级单例（进程内唯一索引；kb.py 检索时调用 ensure_loaded）
index = VectorIndex()
