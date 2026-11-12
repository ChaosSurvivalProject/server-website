"""知识库摄入：Markdown 清洗 / 切片 / Embedding（LangChain 实现）。

RAG 管线各环节统一使用 LangChain 组件：
- 切片：``langchain_text_splitters.RecursiveCharacterTextSplitter``
  （保留代码围栏保护与标题路径——这两点直接决定检索质量，见决策记录 §4）
- 向量化：``langchain_openai.OpenAIEmbeddings``
  （OpenAI 兼容端点，默认硅基流动 bge-m3；向量仍按 float32 小端 BLOB 存
  ``kb_chunks.embedding``，数据库结构不变）

被两个调用方共用（同一套切片与向量，保证检索一致性）：
- backend/kb_sync.py        同步 CLI（独立进程，sqlite3 直写）
- app/kb.py 管理接口        异步 FastAPI（AsyncSession + FTS 原生 SQL）

切片器规格见 docs/智能客服/智能客服P0落地方案.md §5.2：
代码块保护、标题路径、按段落/句子递归切分，目标 chunk_size=600、chunk_overlap=80。
"""
import logging
import math
import re
import struct
from dataclasses import dataclass
from functools import lru_cache

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import KB

logger = logging.getLogger("uvicorn.error")

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80
EMBED_BATCH_SIZE = 32
EMBED_TIMEOUT = 60.0  # 秒；单次 Embedding 请求超时


class KBIngestError(Exception):
    """摄入失败（网络 / 上游错误 / 维度不一致等），message 可直接落 error_message。"""


# ── 清洗 ─────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n?", re.S)
_CONTAINER_RE = re.compile(r"^\s*:::.*$", re.M)  # VitePress 容器标记行（::: tip ... / :::）
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_markdown(text: str) -> str:
    """wiki 源文件清洗：去 frontmatter / 容器标记 / HTML 注释，压缩连续空行。"""
    text = _FRONTMATTER_RE.sub("", text or "")
    text = _CONTAINER_RE.sub("", text)
    text = _HTML_COMMENT_RE.sub("", text)
    return _BLANK_LINES_RE.sub("\n\n", text).strip()


# ── 切片（LangChain RecursiveCharacterTextSplitter） ─────────────

# 中文场景直接把句末/分句标点作为分隔符，效果等价于原自写切片器的
# 「段落 → 行 → 句子 → 子句 → 硬切」逐级降级，但由 LangChain 统一维护。
_TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    keep_separator="end",
)


@dataclass
class Chunk:
    heading: str   # 标题路径，如「进服教程 > Java 客户端」；进 prompt 时拼【来源：…】
    content: str


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


def chunk_markdown(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    """Markdown → 切片列表（LangChain 切片器 + 代码围栏/标题路径保护）。

    1. 以 ``` 围栏为界切段：围栏内绝不切分（避免把代码劈成两半），
       单块超长时整块保留、允许超 chunk_size。
    2. 非围栏段按 #/##/### 一级分隔，记录标题路径；无标题时 heading 为空串。
    3. 段内交给 ``RecursiveCharacterTextSplitter`` 递归切分并合并到 chunk_size。
    """
    splitter = _TEXT_SPLITTER
    if chunk_size != CHUNK_SIZE or overlap != CHUNK_OVERLAP:
        # 允许调用方覆盖参数（测试/特殊源），分隔符口径保持一致。
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            keep_separator="end",
        )

    # ── 围栏切分（代码块保护与 LangChain 无关，属数据完整性前置步骤） ──
    segments: list[tuple[bool, str]] = []  # (is_code, text)
    buf: list[str] = []
    in_code = False
    for line in (text or "").split("\n"):
        if line.lstrip().startswith("```"):
            buf.append(line)
            if in_code:  # 围栏闭合
                segments.append((True, "\n".join(buf)))
                buf = []
                in_code = False
            else:  # 围栏开始：先把之前的普通文本落一段
                if "\n".join(buf[:-1]).strip():
                    segments.append((False, "\n".join(buf[:-1])))
                buf = [line]
                in_code = True
        else:
            buf.append(line)
    tail = "\n".join(buf).strip()
    if tail:
        segments.append((in_code, tail))

    # ── 标题切分 + LangChain 段落合并 ─────────────────────────
    chunks: list[Chunk] = []

    def _emit(section_text: str, heading: str) -> None:
        section_text = section_text.strip("\n")
        if not section_text.strip():
            return
        if len(section_text) <= chunk_size:
            chunks.append(Chunk(heading=heading, content=section_text))
            return
        documents = splitter.split_documents(
            [Document(page_content=section_text, metadata={"heading": heading})]
        )
        for doc in documents:
            piece = doc.page_content.strip("\n")
            if piece.strip():
                chunks.append(Chunk(heading=heading, content=piece))

    heading_path: list[str] = []
    plain_buf: list[str] = []
    for is_code, seg in segments:
        if is_code:
            _emit("\n".join(plain_buf), " > ".join(heading_path))
            plain_buf = []
            chunks.append(Chunk(heading=" > ".join(heading_path), content=seg.strip("\n")))
            continue
        for line in seg.split("\n"):
            m = _HEADING_RE.match(line)
            if m:
                _emit("\n".join(plain_buf), " > ".join(heading_path))
                plain_buf = []
                level, title = len(m.group(1)), m.group(2).strip()
                heading_path = heading_path[: level - 1] + [title]
            else:
                plain_buf.append(line)
    _emit("\n".join(plain_buf), " > ".join(heading_path))
    return [c for c in chunks if c.content.strip()]


# ── Embedding（LangChain OpenAIEmbeddings，OpenAI 兼容 /embeddings） ──


@lru_cache(maxsize=1)
def get_embeddings() -> OpenAIEmbeddings:
    """OpenAI 兼容 Embedding 客户端（进程内单例）。

    - ``base_url`` 指向硅基流动等 OpenAI 协议端点；
    - ``check_embedding_ctx_length=False``：非 OpenAI 模型不要先用 tiktoken 切 token；
    - ``model_kwargs={"encoding_format": "float"}``：直接拿浮点向量，避免 base64 解码口径差异；
    - ``chunk_size`` 与历史批大小一致（32），``max_retries=1`` 等价原「失败重试一次」。
    """
    return OpenAIEmbeddings(
        model=KB.embed_model,
        api_key=KB.embed_api_key or "not-needed",
        base_url=KB.embed_base_url,
        check_embedding_ctx_length=False,  # 非 OpenAI 模型不要先用 tiktoken 切 token
        tiktoken_enabled=False,
        chunk_size=EMBED_BATCH_SIZE,
        max_retries=1,
        timeout=EMBED_TIMEOUT,
        # 直接要浮点向量（OpenAIEmbeddings 1.x 无独立 encoding_format 字段）
        model_kwargs={"encoding_format": "float"},
    )


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return vec
    return [x / norm for x in vec]


def pack_vector(vec: list[float]) -> bytes:
    """float32 小端打包（写入 kb_chunks.embedding 的 BLOB）。"""
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack_vector(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def _normalize_and_check(vectors: list[list[float]]) -> list[list[float]]:
    """维度校验 + L2 归一化（库内向量点积即余弦相似度）。"""
    normalized: list[list[float]] = []
    for vec in vectors:
        if len(vec) != KB.embed_dim:
            raise KBIngestError(
                f"Embedding 维度不符：模型返回 {len(vec)} 维，配置 KB_EMBED_DIM={KB.embed_dim}，"
                "请检查模型与 KB_EMBED_DIM 是否一致"
            )
        normalized.append(_l2_normalize([float(x) for x in vec]))
    return normalized


def embed_documents(texts: list[str]) -> list[bytes]:
    """批量 Embedding，返回 L2 归一化 float32 BLOB 列表（与库内历史数据同口径）。"""
    if not texts:
        return []
    try:
        vectors = get_embeddings().embed_documents(list(texts))
    except KBIngestError:
        raise
    except Exception as e:  # 网络 / 上游 / SDK 异常统一转摄入错误，便于落 error_message
        logger.warning("Embedding 请求失败：%s", e)
        raise KBIngestError(f"Embedding 请求失败：{e}") from e
    if len(vectors) != len(texts):
        raise KBIngestError(f"Embedding 返回条数不符：期望 {len(texts)}，实际 {len(vectors)}")
    return [pack_vector(vec) for vec in _normalize_and_check(vectors)]


def embed_query(text: str) -> list[float]:
    """查询向量：同样 L2 归一化，与库内向量点积即余弦相似度。"""
    try:
        vec = get_embeddings().embed_query(text)
    except KBIngestError:
        raise
    except Exception as e:
        logger.warning("查询向量生成失败：%s", e)
        raise KBIngestError(f"Embedding 请求失败：{e}") from e
    if len(vec) != KB.embed_dim:
        raise KBIngestError(
            f"Embedding 维度不符：模型返回 {len(vec)} 维，配置 KB_EMBED_DIM={KB.embed_dim}"
        )
    return _l2_normalize([float(x) for x in vec])


def prompt_block(title: str, heading: str, content: str) -> str:
    """进 prompt 的切片形态：【来源：{title}｜{heading}】\\n{content}（heading 单独存，此处拼接）。"""
    source = f"{title}｜{heading}" if heading else title
    return f"【来源：{source}】\n{content}"
