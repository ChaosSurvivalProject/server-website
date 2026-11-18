"""OpenAI 兼容 chat 流式客户端（LangChain ``ChatOpenAI`` 实现）。

覆盖 OpenAI / DeepSeek / 通义 / 硅基流动等所有 OpenAI 协议上游；
厂商私有开关（如 enable_thinking）由调用方经 KB.chat_extra_body 原样合并进请求体
（通过 OpenAI SDK 的 ``extra_body``，避免 LangChain 1.x 把 ``max_tokens`` 强制改名
为 ``max_completion_tokens`` 后部分兼容端点不认），不为单个厂商改代码（决策记录 §4）。

思考强度（2026-11-18 新增）：默认走 DeepSeek 原生字段
``enable_thinking`` + ``reasoning_effort(low/high/max)``，默认均衡档 high，
由后台「客服设置」实时配置（kb_settings.chat_reasoning_effort），见下方常量说明。

调用方式：``async for kind, text in stream_chat(messages)``，
kind ∈ {"reasoning", "delta"}；网络/上游异常抛 KBUpstreamError，
由 SSE 生成器统一转成 {"error": ...} 帧。
"""
import logging
from functools import lru_cache

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import KB

logger = logging.getLogger("uvicorn.error")

TIMEOUT = 120.0  # 秒

# ── 思考强度（reasoning effort）─────────────────────────────────
# 约定：OpenAI 兼容网关按 DeepSeek 原生字段开启思考——
#   enable_thinking(bool) + reasoning_effort("low" | "high" | "max")。
# DeepSeek 原生只有 off/low/high/max 四档、**没有 "medium"**；
# 「中（默认均衡档）」对应 high。值来自 kb_settings.chat_reasoning_effort
# （后台「客服设置」可改，每次对话实时读取、即时生效），缺省回落
# KB.chat_reasoning_effort（.env KB_CHAT_REASONING_EFFORT）。
REASONING_EFFORT_VALUES = ("off", "low", "high", "max")
DEFAULT_REASONING_EFFORT = "high"


def normalize_reasoning_effort(value: str | None) -> str:
    """归一化思考强度：非法/空值回落「默认均衡档」(high)。"""
    v = (value or "").strip().lower()
    if v in REASONING_EFFORT_VALUES:
        return v
    fallback = (getattr(KB, "chat_reasoning_effort", "") or "").strip().lower()
    return fallback if fallback in REASONING_EFFORT_VALUES else DEFAULT_REASONING_EFFORT


def reasoning_extra_body(effort: str | None) -> dict:
    """把思考强度翻译成请求体字段。

    - off：显式关闭（enable_thinking=false），不传 reasoning_effort；
    - low/high/max：enable_thinking=true + reasoning_effort=<档位>。
    由调用方用 ``setdefault`` 合并，保证 ``KB_CHAT_EXTRA_BODY`` 里的显式厂商字段优先。
    """
    effort = normalize_reasoning_effort(effort)
    if effort == "off":
        return {"enable_thinking": False}
    return {"enable_thinking": True, "reasoning_effort": effort}


class KBUpstreamError(Exception):
    """上游对话服务异常（非 200 / 流中错误对象 / SDK 异常）。"""


_ROLE_MAP = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


class ReasoningChatOpenAI(ChatOpenAI):
    """ChatOpenAI 适配：把 ``reasoning_content`` 增量带回 ``additional_kwargs``。

    langchain-openai 1.x 的默认 delta 转换会丢弃 DeepSeek / 通义等返回的
    ``reasoning_content`` 字段（只取 content），而前端需要 ``{"reasoning":...}`` 帧
    展示思考过程。这里在子类里补一步，不 monkeypatch 第三方模块。
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ):
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        if generation_chunk is None:
            return None
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            reasoning = delta.get("reasoning_content") or delta.get("reasoning")
            if reasoning and isinstance(generation_chunk.message, AIMessageChunk):
                generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning
        return generation_chunk


def _resolve_model(model: str | None) -> str:
    """对话模型：显式传入（后台配置）优先，空则回落 .env 的 KB_CHAT_MODEL。"""
    m = (model or "").strip()
    return m or KB.chat_model


@lru_cache(maxsize=32)
def _get_model(effort: str = "", model: str = "") -> ChatOpenAI:
    """按 (思考强度, 对话模型) 分档缓存 ChatOpenAI（惰性构造：真正发起对话时才读配置建客户端）。

    effort / model 均由每次对话实时读库得到（后台「客服设置」可改、即时生效）；
    这里按组合分别缓存，避免每轮重建客户端，同时保证改档/改模型后下一次对话即生效
    （不同档位/模型是不同的缓存键）。"""
    extra_body = dict(KB.chat_extra_body)
    # 用 extra_body 透传 max_tokens：LangChain 1.x 会把构造参数 max_tokens
    # 自动改名为 max_completion_tokens，而 DeepSeek 等兼容端点只认 max_tokens。
    extra_body.setdefault("max_tokens", KB.max_output_tokens)
    # 思考强度：enable_thinking + reasoning_effort（KB_CHAT_EXTRA_BODY 显式字段优先）
    for _k, _v in reasoning_extra_body(effort).items():
        extra_body.setdefault(_k, _v)
    return ReasoningChatOpenAI(
        model=_resolve_model(model),
        api_key=KB.chat_api_key or "not-needed",
        base_url=KB.chat_base_url,
        streaming=True,
        max_retries=1,
        timeout=TIMEOUT,
        extra_body=extra_body,
    )


def _to_lc_messages(messages: list[dict]) -> list:
    """项目内 messages 是 OpenAI 风格 [{role, content}]，转 LangChain Message。"""
    lc_messages = []
    for item in messages:
        role = item.get("role", "user")
        cls = _ROLE_MAP.get(role, HumanMessage)
        lc_messages.append(cls(content=item.get("content") or ""))
    return lc_messages


def _split_chunk(chunk) -> tuple[str, str]:
    """从 AIMessageChunk 提取 (reasoning, content)。

    - 思考内容：``ReasoningChatOpenAI`` 已写入 ``additional_kwargs['reasoning_content']``；
      部分实现用 ``reasoning``；新版内容块也可能带 type=reasoning，一并兼容。
    - 正文：content 可能是 str，也可能是 content blocks 列表。
    """
    reasoning_parts: list[str] = []
    text_parts: list[str] = []

    additional = getattr(chunk, "additional_kwargs", None) or {}
    reasoning = additional.get("reasoning_content") or additional.get("reasoning")
    if reasoning:
        reasoning_parts.append(str(reasoning))

    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        if content:
            text_parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") in ("reasoning", "reasoning_content"):
                    value = block.get("reasoning") or block.get("text") or ""
                    if value:
                        reasoning_parts.append(str(value))
                else:
                    value = block.get("text") or ""
                    if value:
                        text_parts.append(str(value))
    return "".join(reasoning_parts), "".join(text_parts)


def get_model(effort: str = "", model: str = "") -> ChatOpenAI:
    """暴露进程内（按思考强度 + 对话模型分档的）模型单例（kb_agent 复用）。"""
    return _get_model(effort, model)


def split_chunk(chunk) -> tuple[str, str]:
    """公开 chunk 拆包（kb_agent 流式循环复用）：返回 (reasoning, content)。"""
    return _split_chunk(chunk)


async def stream_chat(messages: list[dict], effort: str = "", model: str = ""):
    """流式对话：逐段 yield ("reasoning"|"delta", text)。

    effort 为思考强度（off/low/high/max，见模块顶部说明），空值取默认均衡档；
    model 为空则用 .env 的 KB_CHAT_MODEL。异常统一包成 KBUpstreamError；
    连接生命周期由 ``astream`` 的异步生成器保证，被关闭（aclose/CancelledError）
    时底层连接随之释放（断连感知的关键）。
    """
    model = _get_model(effort, model)
    try:
        async for chunk in model.astream(_to_lc_messages(messages)):
            reasoning, content = _split_chunk(chunk)
            if reasoning:
                yield ("reasoning", reasoning)
            if content:
                yield ("delta", content)
    except Exception as e:  # 不捕获 CancelledError（BaseException），保证断连能立即终止
        logger.warning("kb chat 上游异常：%s", e)
        raise KBUpstreamError(str(e)[:200]) from e
