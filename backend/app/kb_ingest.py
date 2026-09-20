"""知识库摄入纯逻辑：Markdown 清洗 / 切片 / Embedding（无 FastAPI 依赖）。

被两个调用方共用（同一套切片与向量，保证检索一致性）：
- backend/kb_sync.py        同步 CLI（独立进程，sqlite3 直写）
- app/kb.py 管理接口        异步 FastAPI（AsyncSession + FTS 原生 SQL）

切片器规格见 docs/智能客服P0落地方案.md §5.2：代码块保护、标题路径、
按段落/句子递归切分，目标 chunk_size=600、chunk_overlap=80。
"""
import logging
import math
import re
import struct
from dataclasses import dataclass

import httpx

from .config import KB

logger = logging.getLogger("uvicorn.error")

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80
EMBED_BATCH_SIZE = 32
EMBED_TIMEOUT = httpx.Timeout(connect=10, read=60, write=10, pool=10)


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


# ── 切片 ─────────────────────────────────────────────────────────


@dataclass
class Chunk:
    heading: str   # 标题路径，如「进服教程 > Java 客户端」；进 prompt 时拼【来源：…】
    content: str


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_SENTENCE_RE = re.compile(r"(?<=[。！？；])")
_CLAUSE_RE = re.compile(r"(?<=[，,])")


def _split_long_text(text: str, chunk_size: int) -> list[str]:
    """单段超长时按 段落 → 行 → 句子 → 子句 → 硬切 逐级降级拆成小块。"""
    if len(text) <= chunk_size:
        return [text]
    units: list[str] = []
    for line in text.split("\n"):
        if len(line) <= chunk_size:
            units.append(line)
            continue
        for sentence in _SENTENCE_RE.split(line):
            if len(sentence) <= chunk_size:
                units.append(sentence)
                continue
            for clause in _CLAUSE_RE.split(sentence):
                if len(clause) <= chunk_size:
                    units.append(clause)
                else:  # 无任何分隔符的超长串：硬切
                    units.extend(clause[i:i + chunk_size] for i in range(0, len(clause), chunk_size))
    return units


def _merge_units(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    """贪心合并小块到 chunk_size；超出时换新块并携带上一块尾部 overlap 字符。"""
    chunks: list[str] = []
    buf = ""
    for unit in units:
        unit = unit.strip("\n")
        if not unit:
            continue
        candidate = f"{buf}\n{unit}" if buf else unit
        if len(candidate) <= chunk_size:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
        if len(unit) > chunk_size:
            # 理论到不了这里（_split_long_text 已拆），防御性硬切
            chunks.extend(unit[i:i + chunk_size] for i in range(0, len(unit), chunk_size))
            buf = ""
        else:
            tail = buf[-overlap:] if overlap > 0 and len(buf) > overlap else ""
            # 尾部尽量对齐到空白处，避免 overlap 截断在半个词中间
            half = tail[: len(tail) // 2]
            cut = half.find(" ") + 1 if " " in half else 0
            buf = (tail[cut:].lstrip() + "\n" + unit).strip("\n") if tail else unit
    if buf:
        chunks.append(buf)
    return chunks


def chunk_markdown(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    """Markdown → 切片列表。

    1. 以 ``` 围栏为界切段：围栏内绝不切分（避免把代码劈成两半），
       单块超长时整块保留、允许超 chunk_size。
    2. 非围栏段按 #/##/### 一级分隔，记录标题路径；无标题时 heading 为空串。
    3. 段内按段落/句子切分并贪心合并到 chunk_size。
    """
    # ── 围栏切分 ──────────────────────────────────────────────
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

    # ── 标题切分 + 段落合并 ───────────────────────────────────
    chunks: list[Chunk] = []

    def _emit(section_text: str, heading: str) -> None:
        section_text = section_text.strip("\n")
        if not section_text.strip():
            return
        if len(section_text) <= chunk_size:
            chunks.append(Chunk(heading=heading, content=section_text))
            return
        units = _split_long_text(section_text, chunk_size)
        for piece in _merge_units(units, chunk_size, overlap):
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


# ── Embedding（OpenAI 兼容 /embeddings） ─────────────────────────


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


def _post_embeddings(texts: list[str]) -> list[list[float]]:
    """单批 Embedding 请求：失败（超时/5xx）重试一次，仍失败抛 KBIngestError。"""
    url = f"{KB.embed_base_url}/embeddings"
    headers = {"Authorization": f"Bearer {KB.embed_api_key}"}
    last_error: Exception | None = None
    for attempt in (1, 2):  # 失败重试一次
        try:
            resp = httpx.post(
                url,
                headers=headers,
                json={"model": KB.embed_model, "input": texts},
                timeout=EMBED_TIMEOUT,
            )
            if resp.status_code >= 500:
                raise KBIngestError(f"Embedding 服务返回 {resp.status_code}")
            if resp.status_code != 200:
                detail = resp.text[:200]
                raise KBIngestError(f"Embedding 服务返回 {resp.status_code}: {detail}")
            data = resp.json().get("data") or []
            if len(data) != len(texts):
                raise KBIngestError(f"Embedding 返回条数不符：期望 {len(texts)}，实际 {len(data)}")
            rows = sorted(data, key=lambda item: item.get("index", 0))
            vectors = [row.get("embedding") or [] for row in rows]
            for vec in vectors:
                if len(vec) != KB.embed_dim:
                    raise KBIngestError(
                        f"Embedding 维度不符：模型返回 {len(vec)} 维，配置 KB_EMBED_DIM={KB.embed_dim}，"
                        "请检查模型与 KB_EMBED_DIM 是否一致"
                    )
            return [_l2_normalize(vec) for vec in vectors]
        except (httpx.TransportError, KBIngestError) as e:
            last_error = e
            logger.warning("Embedding 请求失败（第 %d 次）：%s", attempt, e)
    raise KBIngestError(f"Embedding 请求失败：{last_error}")


def embed_documents(texts: list[str]) -> list[bytes]:
    """批量 Embedding（批大小 32，顺序请求，不做并发），返回 L2 归一化 float32 BLOB 列表。"""
    vectors: list[bytes] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]
        vectors.extend(pack_vector(vec) for vec in _post_embeddings(batch))
    return vectors


def embed_query(text: str) -> list[float]:
    """查询向量：同样 L2 归一化，与库内向量点积即余弦相似度。"""
    return _post_embeddings([text])[0]


def prompt_block(title: str, heading: str, content: str) -> str:
    """进 prompt 的切片形态：【来源：{title}｜{heading}】\\n{content}（heading 单独存，此处拼接）。"""
    source = f"{title}｜{heading}" if heading else title
    return f"【来源：{source}】\n{content}"
