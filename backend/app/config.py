"""知识库（智能客服）配置：backend/.env 零依赖加载 + 模块级 KB 配置对象。

- 不引 python-dotenv：约 20 行 stdlib 解析（决策记录 §4）。
- 已存在的进程环境变量优先：systemd Environment= / Docker -e 可覆盖 .env。
- 所有值在进程启动期读取到模块级 KB 对象（dataclass），不做请求级读取——
  改 .env 后需重启后端进程才生效。
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """解析 .env：KEY=VALUE，# 开头为注释行；已存在的环境变量优先，不覆盖。"""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        # 未加引号的值去掉行内注释（` #` 及其后的内容），如 `KB_TOP_K=5  # 说明`；
        # 带引号的值取引号内原文（支持 JSON 值如 KB_CHAT_EXTRA_BODY={"a":1}）
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        else:
            v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
        if k and k not in os.environ:  # 已存在的环境变量优先
            os.environ[k] = v


_load_env_file(BASE_DIR / ".env")


def _env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, "").strip() or default)
    except (TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, "").strip() or default)
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() not in ("", "0", "false", "no", "off")


def _env_json(key: str) -> dict:
    """厂商私有请求体开关（如 {"enable_thinking":true}），解析失败按空处理。"""
    raw = _env_str(key)
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


@dataclass(frozen=True)
class KBConfig:
    # 总开关
    enabled: bool
    # 对话模型（OpenAI 兼容）
    chat_base_url: str
    chat_api_key: str
    chat_model: str
    chat_extra_body: dict
    max_output_tokens: int
    # Embedding（OpenAI 兼容）
    embed_base_url: str
    embed_api_key: str
    embed_model: str
    embed_dim: int
    # 检索
    vector_enabled: bool
    hybrid_enabled: bool
    top_k: int
    min_score: float
    max_chunks: int
    # 输入与限流
    max_input_chars: int
    max_history: int
    rate_limit_per_hour: int
    rate_limit_global_per_min: int
    rate_limit_concurrent_per_ip: int
    # 知识源与文案
    wiki_dir: Path
    wiki_exclude: tuple
    title: str
    greeting: str
    fallback_hint: str
    system_prompt_extra: str


KB = KBConfig(
    enabled=_env_bool("KB_ENABLED", True),
    chat_base_url=_env_str("KB_CHAT_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
    chat_api_key=_env_str("KB_CHAT_API_KEY"),
    chat_model=_env_str("KB_CHAT_MODEL", "deepseek-chat"),
    chat_extra_body=_env_json("KB_CHAT_EXTRA_BODY"),
    max_output_tokens=_env_int("KB_MAX_OUTPUT_TOKENS", 800),
    embed_base_url=_env_str("KB_EMBED_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/"),
    embed_api_key=_env_str("KB_EMBED_API_KEY"),
    embed_model=_env_str("KB_EMBED_MODEL", "BAAI/bge-m3"),
    embed_dim=_env_int("KB_EMBED_DIM", 1024),
    vector_enabled=_env_bool("KB_VECTOR_ENABLED", True),
    hybrid_enabled=_env_bool("KB_HYBRID_ENABLED", True),
    top_k=_env_int("KB_TOP_K", 5),
    min_score=_env_float("KB_MIN_SCORE", 0.35),
    max_chunks=_env_int("KB_MAX_CHUNKS", 2000),
    max_input_chars=_env_int("KB_MAX_INPUT_CHARS", 300),
    max_history=_env_int("KB_MAX_HISTORY", 6),
    rate_limit_per_hour=_env_int("KB_RATE_LIMIT_PER_HOUR", 20),
    rate_limit_global_per_min=_env_int("KB_RATE_LIMIT_GLOBAL_PER_MIN", 5),
    rate_limit_concurrent_per_ip=_env_int("KB_RATE_LIMIT_CONCURRENT_PER_IP", 1),
    wiki_dir=Path(_env_str("KB_WIKI_DIR", "../wiki")),
    wiki_exclude=tuple(
        s.strip() for s in _env_str("KB_WIKI_EXCLUDE", "node_modules,.vitepress,dist").split(",") if s.strip()
    ),
    title=_env_str("KB_TITLE", "星驿助手"),
    greeting=_env_str("KB_GREETING", "你好，我是星穹旅驿的智能助手，可以问我进服、指令、规则相关的问题。"),
    fallback_hint=_env_str(
        "KB_FALLBACK_HINT", "抱歉，这个问题我暂时答不上来，你可以到 QQ 群 942235691 咨询管理员。"
    ),
    system_prompt_extra=_env_str("KB_SYSTEM_PROMPT_EXTRA"),
)
