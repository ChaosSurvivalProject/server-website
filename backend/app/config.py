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
class StaffConfig:
    """员工名片模块配置（docs/员工管理/员工名片模块需求规格.md §0.2 定值清单）。

    public_base_url 是二维码 URL 前缀的**唯一来源**（后端拼接
    f"{public_base_url}/staff/{身份码}"，前端不得拼 URL、不得传 URL）。
    无尾斜杠；改 .env 后需重启进程生效（与 KB 同语义）。
    """

    public_base_url: str


STAFF = StaffConfig(
    public_base_url=_env_str(
        "STAFF_PUBLIC_BASE_URL", "https://xqly.xt91tv.shop"
    ).rstrip("/"),
)


@dataclass(frozen=True)
class GitHubConfig:
    """GitHub Release 版本同步配置（docs/资源中心/GitHub Release 版本同步需求说明.md §2）。

    pat 为空时降级为未认证请求（60 次/小时核心 API 限额，够少量资源手动同步；
    定时全量扫描建议配 PAT——5000 次/小时）。安全红线：Token 只进请求头，
    绝不出现在任何响应 / 日志 / 堆栈里（见 resource_sync_core 的错误处理口径）。
    """

    pat: str


GITHUB = GitHubConfig(
    pat=_env_str("GITHUB_PAT"),
)


@dataclass(frozen=True)
class KBConfig:
    # 总开关
    enabled: bool
    # 对话模型（OpenAI 兼容）
    chat_base_url: str
    chat_api_key: str
    chat_model: str
    chat_extra_body: dict
    chat_reasoning_effort: str   # 思考强度缺省值：off/low/high/max（后台可覆盖，high=中）
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
    # 文档上传（FLPR-67）
    upload_dir: Path           # 上传原始文件落盘目录（与入库 Markdown 分开存放）
    upload_max_mb: int         # 单文件大小上限（MiB）
    # 知识源与文案
    wiki_dir: Path
    wiki_exclude: tuple
    title: str
    greeting: str
    fallback_hint: str
    system_prompt_extra: str
    # Agent 层（智能客服 P1：Agentic RAG + MCP）
    agent_enabled: bool          # False 时回退 P0 单轮流式（检索注入，不走工具调用）
    agent_max_steps: int         # 工具调用循环上限（recursion_limit 同步收紧）
    agent_tool_timeout: float    # 内置工具执行超时（秒）
    mcp_enabled: bool            # MCP 扩展总开关（关 = 只剩内置 RAG 工具）
    mcp_call_timeout: float      # MCP 工具调用超时（秒；PRD §5 要求 3-5s）
    mcp_tool_cache_seconds: float  # 工具清单缓存（连接测试/白名单页共用，防刷）


KB = KBConfig(
    enabled=_env_bool("KB_ENABLED", True),
    chat_base_url=_env_str("KB_CHAT_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
    chat_api_key=_env_str("KB_CHAT_API_KEY"),
    chat_model=_env_str("KB_CHAT_MODEL", "deepseek-chat"),
    chat_extra_body=_env_json("KB_CHAT_EXTRA_BODY"),
    # 思考强度缺省（off/low/high/max）。后台「客服设置」可覆盖、即时生效；
    # 这里只是未配置时的兜底。high = DeepSeek 默认均衡档（即「中」强度）。
    chat_reasoning_effort=_env_str("KB_CHAT_REASONING_EFFORT", "high").lower(),
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
    # 文档上传：默认落 backend/data/kb_uploads（已 gitignore），20MB 上限
    upload_dir=Path(_env_str("KB_UPLOAD_DIR") or str(BASE_DIR / "data" / "kb_uploads")),
    upload_max_mb=_env_int("KB_UPLOAD_MAX_MB", 20),
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
    # Agent 层（P1）
    agent_enabled=_env_bool("KB_AGENT_ENABLED", True),
    agent_max_steps=_env_int("KB_AGENT_MAX_STEPS", 8),
    agent_tool_timeout=_env_float("KB_AGENT_TOOL_TIMEOUT", 10.0),
    mcp_enabled=_env_bool("KB_MCP_ENABLED", True),
    mcp_call_timeout=_env_float("KB_MCP_CALL_TIMEOUT", 5.0),
    mcp_tool_cache_seconds=_env_float("KB_MCP_TOOL_CACHE_SECONDS", 30.0),
)
