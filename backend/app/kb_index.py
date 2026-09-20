"""知识库内存向量索引：加载 / 版本失效 / TopK（纯 stdlib，无 numpy/sqlite-vec）。

- 全量余弦检索：预切行 array('f') + sum(map(mul)) + heapq.nlargest，
  2000×1536 上限实测 ~20 ms/query（决策记录 §2.1），远小于 LLM 延迟。
- 版本失效：kb_settings.index_version 每次摄入/删除后自增；服务端每次请求
  读一次轻量 SELECT 比对，不同才重建 —— **脚本改了库之后服务端无需重启**，
  这是个设计点，别改成"重启生效"。
- 加锁：asyncio.Lock 只保护重建；查询本身无副作用，可无锁。
"""
import asyncio
import logging
from array import array
from operator import mul
from heapq import nlargest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import KB

logger = logging.getLogger("uvicorn.error")

# 向量检索可用性开关：startup_check 发现库内 embed_dim/模型与配置不一致时置 False
# （只记日志不阻断启动，自动降级为仅 FTS + 引导话术，见 docs/智能客服P0落地方案.md §5.9）
vector_available = True


class VectorIndex:
    """与 kb_chunks 表同构的内存矩阵：ids[i] 对应 rows[i]。"""

    def __init__(self) -> None:
        self.ids: list[int] = []
        self.rows: list[array] = []  # array('f')，已 L2 归一化
        self.dim: int = 0
        self.version: str | None = None  # 对应 kb_settings.index_version
        self._lock = asyncio.Lock()

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
            return bool(self.rows)
        async with self._lock:
            current = await self._read_version(db)  # double-check：等锁期间可能已被别的协程重建
            if self.version == current:
                return bool(self.rows)
            await self._rebuild(db, current)
        return bool(self.rows)

    async def _rebuild(self, db: AsyncSession, version: str) -> None:
        """SELECT 最新 KB_MAX_CHUNKS 条向量重建矩阵；越界时打 WARNING（硬保险，绝不无界）。"""
        result = await db.execute(
            text(
                "SELECT id, embedding FROM kb_chunks "
                "WHERE embedding IS NOT NULL ORDER BY id DESC LIMIT :lim"
            ),
            {"lim": KB.max_chunks},
        )
        ids: list[int] = []
        rows: list[array] = []
        dim_mismatch = 0
        for chunk_id, blob in result:
            arr = array("f")
            arr.frombytes(bytes(blob))
            if len(arr) != KB.embed_dim:
                dim_mismatch += 1  # 脏行直接丢弃，不让单条坏数据炸掉整个索引
                continue
            ids.append(chunk_id)
            rows.append(arr)
        if len(ids) >= KB.max_chunks:
            logger.warning("知识库向量数已达 KB_MAX_CHUNKS=%d 上限，仅加载最新部分", KB.max_chunks)
        if dim_mismatch:
            logger.warning("知识库有 %d 条向量维度与 KB_EMBED_DIM 不符，已跳过", dim_mismatch)
        self.ids, self.rows, self.dim, self.version = ids, rows, KB.embed_dim, version
        logger.info("知识库向量索引已加载：%d 条切片（index_version=%s）", len(ids), version)

    def top_k(self, qv: list[float], k: int) -> list[tuple[int, float]]:
        """返回 [(chunk_id, 余弦相似度), ...]，按相似度降序。"""
        if not self.rows or len(qv) != self.dim:
            return []
        scored = ((sum(map(mul, row, qv)), i) for i, row in enumerate(self.rows))
        return [(self.ids[i], score) for score, i in nlargest(k, scored)]


# 模块级单例（进程内唯一索引；kb.py 检索时调用 ensure_loaded）
index = VectorIndex()
