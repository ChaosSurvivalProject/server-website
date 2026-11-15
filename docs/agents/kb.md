# 知识库 / 智能客服规约

> 本文是 [AGENTS.md](../../AGENTS.md) 对应规约小节的完整原文（2026-11-07 文档重构时下沉，内容未改动）；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

- **wiki 是知识库的单一数据源**：`source_type='wiki'` 的文档由 `backend/kb_sync.py`（CLI，按文件 MD5 增量）维护，后台管理页对 wiki 来源只读（删除接口直接 400）；手动粘贴入库为 `manual` 来源。改动知识库一律先改 wiki，再跑脚本。
- **索引热更新是设计点**：脚本/后台每次摄入或删除都自增 `kb_settings.index_version`，服务端每轮对话轻量 SELECT 比对版本，不同才重建内存向量索引——**服务端不需要重启**，别改成"重启生效"。
- 检索为向量 + FTS5 trigram 双路 RRF 融合（`KB_HYBRID_ENABLED=0` 关混合）；FTS 表是**独立表**（非 external content），写入/删除时手动同步 `rowid = kb_chunks.id`，不要加触发器。
- 限流状态在**进程内**（滑动窗口 + 并发计数），P0 按单 worker 部署；改多 worker 必须换共享存储，否则限流失效。
- 知识库配置在 `backend/.env`（**已 gitignore，含 API Key 禁止提交**），`app/config.py` 启动期一次性读入模块级 `KB` 对象——改 `.env` 需重启进程，不要做请求级读取。
- **RAG 内部实现自 2026-11-12 起改用 LangChain 组件**（切片 `RecursiveCharacterTextSplitter`、Embedding `OpenAIEmbeddings`、向量库自实现 `VectorStore`（stdlib 余弦，不用 numpy）、FTS 适配 `BaseRetriever` + 自研 RRF、对话 `ChatOpenAI`）。**硬性规约不变**：wiki 单一数据源、`index_version` 热更新、FTS5 独立表、SSE 帧协议、`.env` 启动期一次性读取。依赖以 `backend/requirements.txt` 为准，不要引入 `langchain-community`。
- 流式渲染必须复用 `frontend/src/utils/markdown.js` 管线：新增的 `splitMarkdownBlocks`（lexer 切块 → 逐块 parser → DOMPurify）与整篇 parse 等价，ChatWidget 的块级 keyed 渲染 + 末块未闭合补全都建立在它之上，不要绕开另写渲染入口。
- **MCP Server 鉴权与 env（2026-11-15）**：`env` 是 stdio 子进程的环境变量注入（MCP 标准），**仅 stdio 传输生效**，HTTP/SSE 配了会被忽略——别把它当"HTTP 服务的参数"实现（用户最初需求即此误解）；HTTP/SSE 鉴权走 `authType` 三选（none / bearer / api_key，后者自定义头名 `apiKeyHeader` 空 = `X-API-Key`），stdio 恒无鉴权。凭据红线不变：`auth_token`/`env_json`/`headers_json` 原文绝不下发，只回 `hasToken`/`hasEnv`/`hasHeaders` 布尔；切换传输/鉴权方式时由后端清对应字段（`_apply_upsert` 单一转移点）。
- **执行过程的"非思考文本"分块展示（2026-11-15）**：Agent 循环里 LLM 在工具调用之间输出的**非思考正文**（delta）要在过程时间线中按块展示（参考主流 Agent UI），最终答案仍进气泡。**实现必须在前端**：`ChatWidget.onEvent` 收到 `step:act` 帧时，把气泡 `_rawAnswer` 已累积文本 hoist 成独立 `narrative` 步骤块并清空气泡。**不要在 `kb_agent._agent_stream` 里按相位把 delta 拆 narrative/answer**——"最后一段究竟是叙述还是最终答案"流式实时判定不了（踩过：后端拆 narrative 时 delta 全进气泡、叙述块全空）。顺序关键：后端 `on_tool_event(running)` 先 `_transition("act")` 再发 tool 帧，故 hoist 必须挂在 `step:act` 而非 `tool:running`，否则叙述块会排到执行步骤之后。
