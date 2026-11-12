"""OpenAI 兼容 chat 流式客户端（LangChain ``ChatOpenAI`` 实现）。

覆盖 OpenAI / DeepSeek / 通义 / 硅基流动等所有 OpenAI 协议上游；
厂商私有开关（如 enable_thinking）由调用方经 KB.chat_extra_body 原样合并进请求体
（通过 OpenAI SDK 的 ``extra_body``，避免 LangChain 1.x 把 ``max_tokens`` 强制改名
为 ``max_completion_tokens`` 后部分兼容端点不认），不为单个厂商改代码（决策记录 §4）。

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


@lru_cache(maxsize=1)
def _get_model() -> ChatOpenAI:
    """进程内单例 ChatOpenAI（惰性构造：仅真正发起对话时读配置并建客户端）。"""
    extra_body = dict(KB.chat_extra_body)
    # 用 extra_body 透传 max_tokens：LangChain 1.x 会把构造参数 max_tokens
    # 自动改名为 max_completion_tokens，而 DeepSeek 等兼容端点只认 max_tokens。
    extra_body.setdefault("max_tokens", KB.max_output_tokens)
    return ReasoningChatOpenAI(
        model=KB.chat_model,
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


async def stream_chat(messages: list[dict]):
    """流式对话：逐段 yield ("reasoning"|"delta", text)。

    异常统一包成 KBUpstreamError；连接生命周期由 ``astream`` 的异步生成器保证，
    被关闭（aclose/CancelledError）时底层连接随之释放（断连感知的关键）。
    """
    model = _get_model()
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
