"""OpenAI 兼容 chat 流式客户端（httpx）。

覆盖 OpenAI / DeepSeek / 通义 / 硅基流动等所有 OpenAI 协议上游；
厂商私有开关（如 enable_thinking）由调用方经 KB.chat_extra_body 原样 merge 进请求体，
不为单个厂商改代码（决策记录 §4）。

调用方式：`async for kind, text in stream_chat(messages)`，
kind ∈ {"reasoning", "delta"}；网络/上游异常抛 KBUpstreamError，
由 SSE 生成器统一转成 {"error": ...} 帧。
"""
import json
import logging

import httpx

from .config import KB

logger = logging.getLogger("uvicorn.error")

TIMEOUT = httpx.Timeout(connect=10, read=120, write=10, pool=10)


class KBUpstreamError(Exception):
    """上游对话服务异常（非 200 / 流中错误对象）。"""


def _extract_delta_text(delta: dict) -> tuple[str, str]:
    """从 choices[0].delta 提取 (reasoning, content)。

    思考内容字段：DeepSeek / 通义 thinking 模型均为 reasoning_content，
    部分实现用 reasoning，两者都取，取到就发、取不到就不发（方案 §5.7）。
    """
    reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
    content = delta.get("content") or ""
    return reasoning, content


async def stream_chat(messages: list[dict]):
    """流式对话：逐段 yield ("reasoning"|"delta", text)。

    - SSE data: 行解析，[DONE] 结束；流中 {"error":...} 对象转 KBUpstreamError。
    - 连接生命周期由 async with 保证，生成器被关闭（aclose/CancelledError）时
      httpx 流与 TCP 连接随之释放（断连感知的关键）。
    """
    body: dict = {
        "model": KB.chat_model,
        "messages": messages,
        "stream": True,
        "max_tokens": KB.max_output_tokens,
    }
    if KB.chat_extra_body:
        body.update(KB.chat_extra_body)
    headers = {"Authorization": f"Bearer {KB.chat_api_key}"}
    url = f"{KB.chat_base_url}/chat/completions"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            if resp.status_code != 200:
                detail = (await resp.aread()).decode("utf-8", "replace")[:200]
                raise KBUpstreamError(f"上游返回 {resp.status_code}: {detail}")
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                if not payload:
                    continue
                if payload == "[DONE]":
                    return
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue  # 单帧解析失败不中断整条流
                if obj.get("error"):
                    raise KBUpstreamError(str(obj["error"])[:200])
                choices = obj.get("choices") or []
                delta = (choices[0].get("delta") or {}) if choices else {}
                reasoning, content = _extract_delta_text(delta)
                if reasoning:
                    yield ("reasoning", reasoning)
                if content:
                    yield ("delta", content)
