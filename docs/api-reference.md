# 后端 API 参考

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 原样下沉的专题文档（内容未改动，仅调整标题层级与文内交叉引用）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

## 公告

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/announcement/page` | 分页查询公告（参数: page, pageSize, isPublished） |
| GET | `/api/announcement/admin/page` | 管理员分页查询（**需管理员**；含草稿，参数: page, pageSize） |
| GET | `/api/announcement/detail/{id}` | 查询公告详情 |
| GET | `/api/announcement/prev-next/{id}` | 上一篇/下一篇导航（仅已发布公告按 id 序，跳过草稿；返回 `brief={id,title,publishTime}`） |
| POST | `/api/announcement/addWatchCount` | 阅读量 +1（body: `{announcementId}`） |
| POST | `/api/announcement/create` | 创建公告（**需管理员**） |
| PUT | `/api/announcement/update/{id}` | 更新公告（部分更新，**需管理员**） |
| DELETE | `/api/announcement/delete/{id}` | 删除公告（**需管理员**） |
| POST | `/api/announcement/upload/image` | 上传富文本图片（multipart `file`，≤5MB，png/jpg/jpeg/gif/webp，**需管理员**；返回 `data.url` 相对路径，可直接写入公告内容） |
| GET | `/api/announcement/uploads/{...}` | 上传图片静态目录（按月份分目录存放） |

- 公告正文对外字段为 `rawContent`（原始内容）+ `contentType`（内容格式，`'html'`=富文本 / `'markdown'`=Markdown；create/update 传参同名字段，缺省 `html`）。Markdown 渲染在前端完成，后端不做转换。

## 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/captcha` | 获取注册用滑块拼图验证码（返回 `{captchaId, backgroundImage, pieceImage, sliderY}`，5 分钟有效；横向答案不下发仅存服务端） |
| POST | `/api/auth/captcha/verify` | 校验滑块位置（body: `{captchaId, x}`，误差 ≤5px 通过并标记该 captchaId；失败即作废，一次性防爆破） |
| POST | `/api/auth/register` | 注册（body: `{email, password, confirmPassword, captchaId}`，captchaId 须已通过滑块校验，注册时消费；邮箱作为账号，昵称默认取邮箱前缀，角色为普通用户） |
| POST | `/api/auth/login` | 登录（body: `{username, password}`，成功返回 `{token, id, username, nickname, role, avatar}`；禁用/已删除用户无法登录） |
| GET | `/api/auth/me` | 当前登录用户信息（Header: `Authorization: Bearer <token>`，返回 `{id, username, nickname, email, role, avatar}`；禁用/已删除用户的旧 token 一律失效） |
| POST | `/api/auth/avatar` | 上传头像（**登录用户**；`FormData` 字段 `file`，须显式 `Content-Type: multipart/form-data` 否则 422；仅 jpg/png/webp ≤2MB，后端中心裁剪 256×256，文件名含用户 id，覆盖上传自动删除旧文件；返回 `{url}`，落盘 `uploads/avatar/YYYYMM/`，URL 为 `/api/announcement/uploads/avatar/...`；头像非发言，**不受禁言限制**） |

- JWT 默认 24 小时有效，环境变量 `JWT_EXPIRE_HOURS` 可调；签名密钥取环境变量 `JWT_SECRET`，未设置时自动生成并持久化到数据目录。
- 系统管理员 `xqly-admin` 在后端首次启动时自动初始化，随机强密码写入数据目录 `admin_initial_password.txt`（仅首次初始化时写入，请妥善保管并及时删除）。

## 用户管理（管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/admin/users` | 分页查询用户（参数: page, pageSize, status 可选；status 1=正常, 0=禁用, 2=已删除，缺省查全部） |
| POST | `/api/auth/admin/users` | 新增用户（body: `{username, nickname?, password, role, email?}`；账号 2-100 位字母/数字及 . _ % + -，昵称 ≤50 字符，密码 8-32 位含字母数字，role 仅 admin/user） |
| PUT | `/api/auth/admin/users/{id}` | 编辑用户（body: `{nickname?, role?, email?, password?}`；**账号 username 不允许修改**；昵称/角色/邮箱可改，密码留空=不修改（忘记密码重置场景）；已删除用户禁止编辑） |
| PUT | `/api/auth/admin/users/{id}/status` | 切换用户状态（body: `{status: 1\|0\|2}`；1=启用, 0=禁用, 2=删除（软删除，数据保留可恢复）） |
| DELETE | `/api/auth/admin/users/{id}` | 软删除用户（status 置为已删除，无法登录，数据保留可恢复） |
| POST | `/api/auth/admin/users/{id}/avatar/reset` | 重置头像为默认（清空 `avatar` 列并删除头像文件；前台回退默认头像，返回更新后的用户对象） |

- 所有接口需 `Authorization: Bearer <JWT>` 且角色为 `admin`，无 token 返回 401，普通用户返回 403。
- 用户 `status` 三态：`1=正常`、`0=禁用`（无法登录，可重新启用）、`2=已删除`（软删除，无法登录，数据保留可恢复）。
- 用户表 `username`（账号）为登录标识，创建后不可修改；`nickname`（昵称）为展示名，可随时修改。
- 用户列表 / 详情（含 `/api/auth/admin/users` 的 `items`）下发 `avatar`（头像相对 URL，空串 = 未上传）。
- 存量数据库首次启动自动补 `users.status` / `users.nickname` 列（status 默认 1=正常，nickname 默认为空）与 `users.avatar` 列（默认空串 = 未上传头像）。
- 作者简卡（`_author_brief()`，文章 / 评论 / 消息各处下发）的 `avatar` 读 `users.avatar`：空串下发 `null`，前端回退内置默认图；站内信里已存的消息是**下发时点快照**，不回溯改历史消息。

## 阵营对战内测申请

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/faction-beta/apply` | 提交内测申请（**需登录**；body: `{mcId, email, faction, experience, weeklyHours, motivation}`，每账号一份，被拒后可重新提交覆盖） |
| GET | `/api/faction-beta/my` | 查询当前用户申请（**需登录**；未提交时 `data.application` 为 `null`） |
| GET | `/api/faction-beta/admin/page` | 管理员分页查询（**需管理员**；参数: page, pageSize, status 可选过滤） |
| PUT | `/api/faction-beta/admin/{id}/review` | 审核申请（**需管理员**；body: `{status: 1\|2, reviewNote?}`） |
| DELETE | `/api/faction-beta/admin/{id}` | 删除申请（**需管理员**） |

- 申请状态 `status`：`0=待审核, 1=已通过, 2=未通过`；字段 camelCase（`mcId` / `weeklyHours` / `reviewNote` / `reviewTime` 等）。
- 表单选项（期望阵营 / PvP 经验 / 每周时长）以后端 `faction_beta.py` 白名单为唯一权威，前端选项需与其保持一致。

## 服务器监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitor/servers` | 游戏服务器地址列表（前端展示的唯一数据源） |
| GET | `/api/monitor/server-info/{serverId}` | 服务器在线状态（TCP 探测，供首页在线状态组件） |
| GET | `/api/monitor/admin/servers` | 管理员获取全部服务器（**需管理员**） |
| POST | `/api/monitor/admin/servers` | 新增服务器（**需管理员**） |
| PUT | `/api/monitor/admin/servers/{id}` | 更新服务器（**需管理员**） |
| DELETE | `/api/monitor/admin/servers/{id}` | 删除服务器（**需管理员**） |
| POST | `/api/monitor/admin/servers/{id}/primary` | 设为主服务器（**需管理员**） |

- 服务器地址持久化在 SQLite `servers` 表（**DB 为唯一权威，内存 `SERVERS` 字典为读缓存**）：启动时 `load_servers()` 读库填充内存，表为空时用默认注册表做种子；后台管理页的增删改先改内存再同步落库（先 commit 再返回，失败回滚内存），**重启不再丢失**（原"重启即重置"行为属 bug，已修复）。不能删除主服务器，设主 / 设 `isPrimary` 会自动清除其他服务器的主标记，全表始终至多一个主服务器。

## 网站配置（首页个性化 + 站点标识）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/site-config` | 公开：首页渲染读取（未配置键回默认值） |
| GET | `/api/site-config/admin` | 管理员：后台表单回显（全部键 + 字段定义）（**需管理员**） |
| PUT | `/api/site-config/admin` | 管理员：整包保存 `{settings: {键: 值}}`（**需管理员**） |

- 存储在 SQLite `site_settings` KV 表；键集合由 `backend/app/site_config.py` 的 `FIELD_DEFS` 定义（site.* / banner.* / hero.* / video.* / faction.* / forum.* / footer.* 七个分区），不做自由键。
- 公开响应按分区分组（`banner.enabled` / `faction.enabled` / `footer.enabled` 为布尔，其余为字符串）；**DB 无该键时回默认值**，前端另有内置默认值兜底（`Home.vue` 的 `HOME_DEFAULT_CONFIG`、`App.vue` 的 `FOOTER_DEFAULT_CONFIG`、`utils/siteBranding.js`），接口失败不开天窗。
- `site` 分区（`site.title` / `site.name` / `site.logo`）为全站品牌：`App.vue` 启动时读取并写入 `utils/siteBranding.js` 的全局响应式状态，`site.title` 作为浏览器标签页标题，`site.name` / `site.logo` 用于顶部导航栏与登录/注册页；`site.logo` 置空回退打包内默认图。
- 富文本字段（`hero.title` / `hero.subtitle` / `hero.description`）支持 `[[绿色]]` `{{紫色}}` 高亮标记，后端校验成对闭合，前端 `frontend/src/utils/highlight.js` 解析成 span（不走 v-html）。
- 图片字段存 `/api/announcement/uploads/...` 相对 URL（复用公告上传接口）；置空则前端回退打包内默认图。
- 行式列表字段（`hero.features` / `footer.sponsorDesc` / `footer.copyright` 每行一条；`footer.columns` 每行 `栏目名|链接文字|链接地址`）后端存原文，前端解析成数组。
- 布尔语义存 `"0"/"1"`（项目规约 int 布尔）。
- 后台「网站配置」页支持整包导出/导入 JSON：导出 `{exportedAt, settings}` 下载为文件；导入兼容 `{settings: {...}}` 与裸 `{键: 值}`，未知键在预览中标记忽略，确认后与当前值合并整包保存。

## 知识库 / 智能客服（P0）

官网内置基于 wiki 文档的知识库智能客服：向量 + FTS5 trigram 混合检索、SSE 流式回答、思考过程与来源引用展示，答不了时引导进 QQ 群。设计规格见 `docs/智能客服/智能客服P0落地方案.md`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/kb/info` | 客服元信息（`enabled` / `title` / `greeting` / `faq` / `model`；未配置 API Key 时 `enabled:false`，前端不渲染悬浮球） |
| POST | `/api/kb/chat` | **SSE 流式问答**（body: `{message, history?}`；`text/event-stream`，**两个不走 `{code, message, data}` 包络的接口之一**，另一个是 `/api/messages/stream`；帧协议见下方） |
| GET | `/api/kb/admin/documents` | 文档分页列表（**需管理员**；参数: page, pageSize, sourceType 可选） |
| POST | `/api/kb/admin/documents` | 手动新增知识（**需管理员**；body: `{title, content}`，同步切片 + Embedding） |
| DELETE | `/api/kb/admin/documents/{id}` | 删除文档（**需管理员**；`wiki` 来源返回 400，提示走同步脚本） |
| GET | `/api/kb/admin/documents/{id}/chunks` | 切片预览（**需管理员**） |
| POST | `/api/kb/admin/documents/{id}/reindex` | 重建（**需管理员**；幂等：wiki 来源读源文件整篇重建，manual 来源重嵌入现有切片） |
| GET | `/api/kb/admin/stats` | 统计（**需管理员**；文档数 / 切片数 / 索引版本 / 维度一致性 / 总字符数） |

### MCP 扩展（P1：Agentic RAG + MCP）

默认 **Agentic RAG**：知识库检索是内置 Function Calling 工具（`create_agent` 工具调用循环，LangChain 1.x），MCP 经官方适配器 `langchain-mcp-adapters` 动态接入（stdio / SSE / Streamable HTTP）。`KB_AGENT_ENABLED=0` 回退 P0 单轮流式；`KB_MCP_ENABLED=0` 只关 MCP（内置 RAG 保留）。以下全部 **需管理员** + 包络：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/kb/admin/mcp/servers` | MCP Server 列表（凭据脱敏：`hasToken` 等布尔，绝无原文；`authType`/`apiKeyHeader` 非凭据明文下发） |
| POST | `/api/kb/admin/mcp/servers` | 注册（body: `{name, transport: stdio\|sse\|streamable_http, url?, command?, args?, env?, headers?, authType?: none\|bearer\|api_key, authToken?, apiKeyHeader?, timeoutSeconds, enabled}`；`env` 仅 stdio 生效，stdio 恒无鉴权） |
| PUT | `/api/kb/admin/mcp/servers/{id}` | 编辑（`authToken` 留空 = 保留原值；`authType` 切 `none` 清空旧凭据；`env`/`headers` 传 `null` = 保留原值，传 `{}` = 清空） |
| DELETE | `/api/kb/admin/mcp/servers/{id}` | 删除（级联删白名单） |
| PUT | `/api/kb/admin/mcp/servers/{id}/toggle` | 独立启停（停用后其全部工具不进 LLM 上下文也不可执行，内置 RAG 不受影响） |
| POST | `/api/kb/admin/mcp/servers/test` | 连接测试（用提交的配置现场连一次+列工具，**不落库**；恒 200，`data.ok=false` 给出原因） |
| POST | `/api/kb/admin/mcp/servers/parse-json` | JSON 导入解析（粘贴标准 MCP 配置 `{"mcpServers":{...}}` → 表单字段，不落库；`env` 仅 stdio 保留，HTTP 配置的 `Authorization` 头归位 bearer） |
| GET | `/api/kb/admin/mcp/servers/{id}/tools` | 工具白名单列表（`?refresh=1` 现场重新发现并同步快照行） |
| PUT | `/api/kb/admin/mcp/tools/toggle` | 单工具勾选（body: `{serverId, toolName, enabled}`；**默认全部关闭**） |
| PUT | `/api/kb/admin/mcp/tools/batch-toggle` | 按 Server 批量勾选/取消 |
| GET | `/api/kb/admin/tool-config` | 内置检索工具配置（§2.3 系统级常驻） |
| PUT | `/api/kb/admin/tool-config` | 更新内置工具配置（工具名/描述/Top-K/命中阈值，即时生效） |
| GET | `/api/kb/admin/chat-config` | 客服模型设置（**需管理员**；返回生效 `model` + `modelDefault`(\.env) + `modelConfigured` + `baseUrl` + 当前思考强度 `reasoningEffort` 与可选项 `options`） |
| PUT | `/api/kb/admin/chat-config` | 更新对话模型 / 思考强度（**需管理员**；body: `{model?: string, reasoningEffort: off\|low\|high\|max}`；`model` 传空串 = 清除覆盖回退 `.env`、省略 = 不改动；写 `kb_settings.chat_model` / `chat_reasoning_effort`，**即时生效**、无需重启） |
| GET | `/api/kb/admin/models` | 拉取上游网关可用模型列表（**需管理员**；代理 `GET {KB_CHAT_BASE_URL}/models`，返回 `{models:[{id,name,ownedBy,reasoning}], count}`；供后台「获取模型列表」按钮选模型回填，失败 502） |

MCP 鉴权（2026-11-15）：HTTP/SSE 支持 `authType` 三选——`none` 无鉴权 / `bearer`（`Authorization: Bearer <authToken>`）/ `api_key`（自定义头 `apiKeyHeader`，空 = `X-API-Key`，值为 `authToken`）；`headers` 是额外自定义头（同名时鉴权值优先）。stdio 走 `env` 注入子进程环境变量（MCP 标准，HTTP/SSE 的 env 无意义会被忽略）；stdio 与 HTTP 的凭据字段互斥，切换传输时由后端自动清理对应字段。
| GET | `/api/kb/admin/tool-logs` | 工具调用审计日志（prompt / LLM 决策 / 实参 / 结果摘要 / 耗时 / 状态，含内置检索与 MCP 全部调用；内置检索结果摘要含每条切片的正文与余弦分数） |
| POST | `/api/kb/admin/tool-logs/cleanup` | 手动清理审计日志（body: `{mode:"days", days:N}` 清理 N 天前 或 `{mode:"date", startDate:"YYYY-MM-DD", endDate:"YYYY-MM-DD"}` 清理起止日期区间（含起止当天）；返回 `{deleted, scope}`，动作本身落审计留痕） |

生效逻辑：可用工具 =（内置检索工具，若启用）+ Σ（启用中的 MCP Server × 白名单勾选的工具）。某 Server 断连/超时 → Agent 组装时**静默剔除**其工具，对话不中断；MCP 工具失败向 LLM 注入固定错误串、绝不暴露堆栈。MCP 调用超时按 Server 配置（默认 5s，PRD §5）。

SSE 帧协议（UTF-8 JSON，空行分隔，`ensure_ascii=False`）：

```
data: {"sources":[{"id":12,"title":"进服教程 / Java 客户端","sourceType":"wiki","score":0.83}]}   ← P0 模式首帧；P1 Agent 模式在循环结束后发（可能只有 title）
data: {"tool":{"name":"search_knowledge_base","label":"📖 正在检索知识库...","state":"running"}}   ← P1 可选：工具调用链路（state ∈ running|ok|error，只有语义化动作名，绝无参数）
data: {"reasoning":"..."}    ← 思考过程（思考模型才有），与 delta 可交错
data: {"delta":"..."}        ← 回答正文增量
data: {"fallback":true}      ← 可选：命中引导话术时附带（仅 P0 模式）
data: {"error":"..."}        ← 可选：流开始后出错（流开始前走标准 HTTP 400/429/503 + 包络）
data: [DONE]                 ← 一定发（try/finally 保证）
```

- 错误输入 / 限流 / 未开放等流前错误返回标准 HTTP 状态码 + `detail`；流中错误发 `{"error":...}` 帧（header 已发出无法改状态码）。
- 限流（进程内滑动窗口，`=0` 关闭）：单 IP 每小时 `KB_RATE_LIMIT_PER_HOUR`（默认 20）+ 全局每分钟 `KB_RATE_LIMIT_GLOBAL_PER_MIN`（默认 5）+ 单 IP 并发 1；输入上限 `KB_MAX_INPUT_CHARS`（默认 300 字）超出 400。
- 多轮对话由**客户端**携带 `history` 数组（服务端只取最后 `KB_MAX_HISTORY` 条），服务端无状态、不落库。
- **wiki 是知识库单一数据源**：`source_type='wiki'` 的文档由同步脚本维护，后台只读；手动新增为 `manual` 来源。

知识库同步脚本 `backend/kb_sync.py`（在服务器上执行，按文件 MD5 增量）：

```bash
cd backend
python3 kb_sync.py --check           # 只看变更，不写库
python3 kb_sync.py --all             # 全量同步（MD5 判重，未变更零成本跳过）
python3 kb_sync.py --incremental     # 增量同步（wiki 改动后执行，可挂 crontab）
python3 kb_sync.py --list            # 列出库内文档与切片数
# 可选参数：--no-prune 不删除已消失的文件；--force 模型/维度不一致时强制写入
```

同步会自增 `kb_settings.index_version`，**服务端下次对话自动重建内存索引，无需重启**（设计点，勿改成"重启生效"）。服务与脚本可同时运行（双侧均已开 WAL + busy_timeout，不会 `database is locked`）。

知识库配置（`backend/.env`，**已 gitignore，含 API Key 勿提交**）：总开关 `KB_ENABLED`；对话模型 `KB_CHAT_BASE_URL` / `KB_CHAT_API_KEY` / `KB_CHAT_MODEL`（OpenAI 兼容）+ 思考强度缺省 `KB_CHAT_REASONING_EFFORT`（`off\|low\|high\|max`，默认 `high`=中；后台「智能客服 → 客服设置」可覆盖、即时生效）+ 可选 `KB_CHAT_EXTRA_BODY`（厂商私有参数原样 merge）；Embedding `KB_EMBED_BASE_URL` / `KB_EMBED_API_KEY` / `KB_EMBED_MODEL` / `KB_EMBED_DIM`；检索 `KB_TOP_K` / `KB_MIN_SCORE` / `KB_MAX_CHUNKS` 等；文案 `KB_TITLE` / `KB_GREETING` / `KB_FALLBACK_HINT`。改 `.env` 需重启后端生效（思考强度后台改则无需重启）。启动自检：密钥缺失 → 客服自动关闭（`/kb/info` 返回 `enabled:false`，`/kb/chat` 503）；库内向量维度/模型与配置不一致 → 关闭向量检索降级为仅 FTS，`/kb/admin/stats` 标记"需重建索引"。

## 员工名片

工作人员名片系统（只读公开核验页 + 管理员台账）：名片上印二维码 → 扫码打开 `/staff/{身份码}` 验证页 → 后台可撤销/续期/换码。实施规格见 `docs/员工管理/员工名片模块需求规格.md`，落地设计见 `docs/员工管理/员工名片模块评审与落地方案.md`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/staff/public/{code}` | 验证页数据（匿名；四态 `valid` / `revoked` / `expired` / `not_found`，白名单模型不含 remark 与完整身份码；"格式非法 / 不存在 / 超长"返回逐字节一致的 `not_found`） |
| GET | `/api/staff/public/team` | 管理组总览（匿名；仅现任且在有效期内的公开字段） |
| GET | `/api/staff/admin/page` | 台账分页（**需管理员**；参数: page, pageSize, status=`active\|expiring\|expired\|revoked`, keyword） |
| GET | `/api/staff/admin/stats` | 顶部统计条（**需管理员**；全部 / 现任 / 即将到期≤30天 / 已过期 / 已撤销） |
| POST | `/api/staff/admin` | 新增工作人员（**需管理员**；自动生成 12 位身份码 + 一年有效期） |
| PUT | `/api/staff/admin/{id}` | 编辑公开信息（**需管理员**；公开字段变更时 `cardVersion` 自动递增） |
| POST | `/api/staff/admin/{id}/regenerate-code` | 重生成身份码（**需管理员**；旧码立即失效，适用于码泄露等） |
| POST | `/api/staff/admin/{id}/revoke` | 撤销（**需管理员**；body: `{reason}`，仅接受 `离职/转岗/暂停/码异常`） |
| POST | `/api/staff/admin/{id}/restore` | 恢复已撤销人员（**需管理员**；强制换新身份码，旧码立即失效） |
| POST | `/api/staff/admin/{id}/renew` | 续期一年（**需管理员**；因到期失效的记录自动恢复 active、二维码不变；人工撤销的记录返回 400 须先恢复） |
| GET | `/api/staff/admin/{id}/qrcode` | 二维码 PNG（**需管理员**；410×410，URL 由后端 `STAFF_PUBLIC_BASE_URL` 统一拼接） |
| GET | `/api/staff/admin/export` | 导出名单 CSV（**需管理员**；⚠️ 这是"不返回完整身份码列表"的唯一豁免点——公开接口一律只给展示码后四位，勿把本豁免当漏洞"修掉"） |

- **状态模型**：`status` 只存 `active` / `revoked` 两态；过期判定权威是 `valid_to`（`now > valid_to` 即过期），命中时把 `active` **回写**为 `revoked`（`revoked_reason='expired'`，仅系统写入、后台下拉不可见）。回写有两条触发路径、共用同一函数 `expire_due()`：公开验证接口查询时懒更新（幂等）+ `backend/staff_expire.py` CLI（crontab 每日一次，服务启动时也跑一次）——**crontab 漏挂不影响核验正确性**，只影响台账刷新时效。
- **身份码**：12 位全小写（`23456789abcdefghijkmnpqrstuvwxyz`，去掉易混的 `0 1 l o`），`secrets` 安全随机 + 查重重试；对外任何公开响应都不下发完整码（页面正文只显示后四位 `••••xxxx`）。
- **二维码**：后端 `qrcode` 库生成，纠错 M、留白 4 模块、`box_size=10`（410×410px）；**禁止硬编码 `version=`**（49 字节 URL 实测 v4 / 33×33，由库自动选版）；URL 只含域名 + 路径 + 随机码，无隐私字段。
- 头像复用 `POST /api/announcement/upload/image` 上传接口（png/jpg/gif/webp、≤5MB）。
- 到期检查脚本（仿 `kb_sync.py`，可挂 crontab）：

```bash
cd backend
python3 staff_expire.py             # 全表到期回写，输出刷新行数
python3 staff_expire.py --dry-run   # 只统计，不写库
```

## 社区（论坛）

社区论坛第一阶段（MVP）：匿名可浏览 → 登录可发帖/点赞/收藏/评论（**两级楼中楼**）→ 管理员审核与运营。实施唯一依据 `docs/论坛/论坛模块第一阶段PRD.md`（v1.4）+ 交互原型 `docs/论坛/prototype/index.html`；帖子删除与回收站见 `docs/论坛/论坛删除与回收站PRD.md`（v1.3，**局部取代**第一阶段 PRD 的 §8-D16 与 §12.1 中「评论作者自删」半条）。落点 `backend/app/forum.py`（回收站轻量核心 `backend/app/forum_core.py`，超期清理 CLI `backend/forum_purge.py`）。**「先审后发」**：新帖 `status=0 待审核`，管理员通过后才公开。

**公开接口（匿名可调）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/forum/categories` | 板块列表（过滤 `isHidden`，含 2 个系统板块，带已发布文章数） |
| GET | `/api/forum/tags/hot` | 热门标签（`isHot` 优先 + `useCount` 倒序；参数 `limit`） |
| GET | `/api/forum/stats` | 社区统计 `{articleCount, viewCount, tagCount}`（`status=1` 实时聚合） |
| GET | `/api/forum/config` | 前台配置（Banner 三项 + `defaultSort` + `searchPlaceholder`；打赏预留键不下发） |
| GET | `/api/forum/articles` | 文章列表（参数 `page`,`pageSize`,`category`,`sort`,`q`,`tag`,`authorId`；`category=home`=全部 / `recommend`=置顶∪加精按浏览量；`sort=latest\|views\|comments`；`authorId`=按作者筛，**只含已发布**，个人主页「TA 的帖子」用；**置顶帖在任意排序档中都恒排最前**） |
| GET | `/api/forum/articles/{id}` | 详情（未公开文章对非作者非管理员按 404 处理；**回收站帖对所有人 404，含作者本人**；**不计数浏览量**） |
| GET | `/api/forum/articles/{id}/comments` | 评论列表（`page`,`pageSize`；**只对顶层评论分页**，每条内嵌 `replies`；已登录附每条 `liked`） |
| GET | `/api/forum/comments/{id}` | 单条评论详情（匿名可读；`id` 可为顶层评论或回复；返回 `{comment, rootComment, replies, article}`，`replies` 为所属顶层评论下全部正常回复、正序不分页；评论已删除 / 文章不可见一律 404） |
| GET | `/api/forum/articles/{id}/author-posts` | 作者其他已发布文章（最多 5 条） |
| POST | `/api/forum/articles/{id}/view` | 浏览量 +1（匿名可调；原子自增，重复刷新重复计为已接受行为） |
| GET | `/api/forum/users/{userId}/stats` | 某人的公开论坛数据（作者卡 / 个人主页头部用；`{author, postCount, likeCount, followerCount, createTime}`，`followerCount` 恒 0，不下发任何私有字段；用户不存在或已注销返 404） |
| GET | `/api/forum/users/{userId}/comments` | 某人的公开评论（个人主页「TA 的评论」用；参数 `page`,`pageSize`，按时间倒序；只含 `status=1` 文章下的 `status=1` 评论，顶层与回复都算；返回 `{articleId, articleTitle, commentId, content, createTime}`，`content` 为纯文本截断摘要；用户不存在或已注销返 404） |

**登录用户接口**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/forum/articles` | 发布文章（`status=0`；body `{categoryId,title,content,coverUrl?,tags[]}`；受禁言拦截） |
| GET | `/api/forum/articles/{id}/edit` | 编辑回填（**仅作者本人**；越权/不存在一律 404；`remove_by='admin'` 的已下架帖 400） |
| PUT | `/api/forum/articles/{id}` | 作者编辑重提（**仅作者本人**；`status` 一律回 0、清空 `reviewNote`/`publishTime`/`removeBy`、`resubmitCount+1`，**浏览/点赞/收藏/评论全部保留**） |
| DELETE | `/api/forum/articles/{id}` | 作者删除 → **进回收站**（`status=4` + `deleted_at`，保留 30 天；**不再产生 `status=3`**，后者只剩管理员下架一个来源） |
| POST | `/api/forum/articles/{id}/restore` | 从回收站恢复 → `status_before_delete`（0/1/2，不重审）；**超 30 天返 410** |
| DELETE | `/api/forum/articles/{id}/purge` | 回收站内**彻底删除**（物理 + 级联，不可恢复；前端一律二次确认） |
| DELETE | `/api/forum/comments/{id}` | 作者删自己的评论/回复（**物理删除不留痕**；删顶层连带其下全部回复） |
| GET | `/api/forum/my/articles` | 我的文章（各状态 + `reviewNote`/`removeBy`/`resubmitCount`；`status=4` 时额外下发 `deletedAt`/`daysLeft`/`statusBeforeDelete`，回收站页面据此取数） |
| GET | `/api/forum/my/stats` | 侧边栏用户卡 `{postCount, likeCount, followerCount}`（`followerCount` 恒 0） |
| GET | `/api/forum/my/titles` | 我的头衔管理页 `{exp:{exp,level,levelName,updateTime}, titles:[...]}`；只下发本人数据，`titles` 含撤销历史（生效在前），每条 `{id,titleCode,titleText,source,grantedAt,grantedBy,revokedAt,revokedBy,active,displayed}` |
| PUT | `/api/forum/my/titles/{titleCode}/display` | 自助佩戴 / 隐藏头衔（body `{displayed: 0\|1}`，**只改 displayed、不碰授予留痕**）；仅限本人**生效中**头衔，已撤销或非本人 404，非法值 422 |
| POST | `/api/forum/articles/{id}/like` | 文章点赞切换（幂等）→ `{liked, likeCount}` |
| POST | `/api/forum/articles/{id}/favorite` | 文章收藏切换（幂等）→ `{favorited, favoriteCount}` |
| POST | `/api/forum/articles/{id}/comments` | 发表评论 / 发表回复（body `{content, parentId?, replyToUserId?}`；`parentId` **只指向顶层评论**，指向回复返 400） |
| POST | `/api/forum/comments/{id}/like` | 评论点赞切换（顶层与回复通用） |
| POST | `/api/forum/upload/image` | 图片上传（登录用户；落盘 `uploads/forum/YYYYMM/`，URL 仍是 `/api/announcement/uploads/forum/...`） |

**管理员接口（`require_admin`）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/forum/admin/articles` | 检索分页（`keyword`,`author`,`categoryId`,`tagId`,`status`） |
| GET | `/api/forum/admin/articles/{id}` | 文章全量详情（正文源码 + 标签名 + 审核备注） |
| PUT | `/api/forum/admin/articles/{id}/review` | 审核（`{status: 1\|2, reviewNote?}`；驳回理由必填；通过时重写 `publishTime`） |
| POST | `/api/forum/admin/articles/{id}/top` `/feature` | 置顶 / 加精切换（幂等） |
| POST | `/api/forum/admin/articles/{id}/offline` | 下架（`{reason?}`；写 `remove_by='admin'`，作者此后**不能**编辑重提） |
| POST | `/api/forum/admin/articles/{id}/restore` | 恢复上架（`remove_by=''`，`publish_time` 重写，**不重新审核**）；`status=4` 时为**回收站恢复** → `status_before_delete`（超 30 天 410） |
| PUT | `/api/forum/admin/articles/{id}` | 改板块/标签/封面/标题（**状态不变**，不重新审核；**正文只读**） |
| DELETE | `/api/forum/admin/articles/{id}` | 硬删除（级联评论/点赞/收藏/标签关联；回收站帖同样走这里） |
| GET | `/api/forum/admin/articles/{id}/comments` | 评论抽屉（含已删除标记） |
| DELETE | `/api/forum/admin/comments/{id}` | 删评论（**软删 `status=2` 留治理痕迹**；删顶层连带其全部回复并清 `comment_likes`）——与作者侧物理删**有意不对称** |
| GET/POST/PUT/DELETE | `/api/forum/admin/categories[/{id}]` | 板块管理（系统板块不可删/改名/隐藏；有已发布文章的板块删除 400） |
| GET/POST/PUT/DELETE | `/api/forum/admin/tags[/{id}]` | 标签管理（重命名 / 置热 / 删除） |
| POST | `/api/forum/admin/tags/{id}/merge` | 标签合并（`{targetTagId}`；引用全部迁移、删源、重算 `use_count`） |
| GET/PUT | `/api/forum/admin/config` | 社区配置读写（白名单键；打赏 `reward*` 为预留键，第一阶段无 UI） |
| GET | `/api/forum/admin/covers` | 封面图库（只读列表；冗余清理归第三阶段） |
| GET | `/api/forum/admin/user-stats/{userId}` | 用户论坛数据（发帖/获赞/粉丝 + 最近 5 篇） |
| GET | `/api/forum/admin/users/{userId}/exp` | 用户经验与等级进度 `{exp, level, levelName, updateTime}`（无记录视为 0 / Lv.1） |
| GET | `/api/forum/admin/users/{userId}/titles` | 用户头衔列表（**含撤销历史**，撤销不删行） |
| POST | `/api/forum/admin/users/{userId}/titles` | 手动授予头衔（body `{titleCode}`，操作人与时间留痕；生效中重复授予 400） |
| DELETE | `/api/forum/admin/users/{userId}/titles/{titleCode}` | 撤销头衔（写 `revokedAt`/`revokedBy` 留痕；前台实时失效） |
| PUT | `/api/auth/admin/users/{id}/mute` | 禁言/解禁（body `{muteUntil}`，空串=解禁；与 `status` 三态**正交**） |

- **状态机**（`forum_articles.status`）：`0 待审核 → 1 已发布 / 2 已驳回`；`1 → 3 已下架`（**仅管理员**）`→ 1 恢复`；`0/1/2 ──作者删除──▶ 4 回收站`；`4 ──恢复（作者或管理员）──▶ status_before_delete`；`4 ──彻底删除/后台硬删/超期清理──▶ 物理删除`（级联，不可恢复）。任意可编辑态（0/1/2/3 且 `remove_by='author'`）经**作者编辑保存 → 0**（`resubmit_count+1`）；**回收站帖必须先恢复才能编辑**。已驳回的文章必须由作者重提回 0 才能再审。
- **回收站三列**（`deleted_at` / `status_before_delete` / `publish_time_before_delete`，`migrate_forum_article_recycle_columns()` 幂等补列）：`deleted_at` 是 **30 天保留期的唯一权威**（恢复接口自校验 + 列表自过滤 + `forum_purge.py` 清理共用）；恢复时回填删前 `publish_time`，否则「删除→恢复」两次点击即可零成本刷榜。超期清理主路径是 crontab 每日 05:00 跑 `forum_purge.py`，`main.py` 启动兜底一次——**漏挂 crontab 不影响正确性**（超期帖用户看不到也恢复不了，只是数据多留几天）。
- **`remove_by` 决定作者能否编辑重提**：`''` 未移除 / `'author'` 作者自删（已在回收站，须先恢复）/ `'admin'` 管理员下架（**不可重提**，返 400，否则等于绕过下架）。
- **标签 `use_count` = 被 `status=1` 文章引用的数量**，只挂在状态转移这一个点上；浏览/点赞/收藏/评论计数一律原子 SQL 自增。
- **`comment_count` = 顶层评论数 + 回复数**（回复也算评论）；评论纯文本存储，不接受 Markdown/HTML。
- **用户个人主页（FLPR-34）**：`/forum/user/:id`（未登录可浏览）只聚合已公开内容——帖子走 `/api/forum/articles?authorId=`（后端恒 `status=1`，含置顶/精华标记），评论走 `/api/forum/users/{id}/comments`（仅已发布文章下的正常评论）；下架/驳回/回收站帖与已删评论一律不出现。禁用 / 禁言用户的已公开内容照常展示（两者只限登录与写操作），不存在 / 已注销（users.status=2）由两个公开接口统一 404，前端给明确空态。头像位等 FLPR-31、等级徽章位等 FLPR-36 落地后自然点亮，当前不填假数据。
- **禁言语义**：能登录浏览，但**不能发帖/评论/上传**（点赞收藏不受影响）；命中返回 403 + `detail="账号已被禁言，至 <时间>"`。**删自己的帖子/评论属例外，禁言期间仍可用**。
- **后台回收站已打通**（2026-11-18）：`GET /api/forum/admin/articles?status=4` 可筛出回收站帖（列表项带 `deletedAt` / `daysLeft` / `statusBeforeDelete`，**不含正文**），`POST /api/forum/admin/articles/{id}/restore` 按 `status_before_delete` 恢复；后台文章管理页对 `status=4` 行只留「恢复 / 删除」，隐藏通过 / 驳回 / 下架 / 置顶 / 加精 / 改属性。
- 端到端回归脚本：`cd backend && python3 forum_smoke_test.py`（临时库 + `TestClient`，覆盖状态机/计数/回收站/权限/级联等断言）。

### 等级 / 头衔 / 经验体系（FLPR-36，2026-11-22）

**数据模型**（四张新表，不动 `users`；`backend/app/database.py`）：
- `forum_user_levels`：等级阈值常量表，`level` / `name` / `required_exp`，由 `seed_forum_user_levels()` 启动时幂等写入；
- `forum_user_exp`：每人一行 `exp`（只增不减）/ `level`（由阈值推导）/ `update_time`；
- `forum_user_titles`：`user_id` / `title_code` / `source`（`system`|`manual`）/ `granted_at` / `granted_by` / `revoked_at` / `revoked_by` / **`displayed`**（`0` 隐藏 / `1` 展示，用户自助佩戴开关，与撤销状态无关；存量列默认 1）——**撤销不删行，手动头衔全程留痕**，`revoked_at=''` 即生效；
- `forum_exp_ledger`：经验发放流水，`dedup_key` 唯一，是「取消再点赞不重复加经验」的权威（点赞关系表取消时物理删行，必须以独立流水去重）。

**阈值表（首版常量，调整需另开工单；不清空用户已有 exp，按新阈值重算等级）**：

| 等级 | 名称 | 所需累计经验 |
|------|------|--------------|
| Lv.1 | 见习旅人 | 0 |
| Lv.2 | 旅人 | 10 |
| Lv.3 | 探索者 | 30 |
| Lv.4 | 冒险家 | 60 |
| Lv.5 | 先驱者 | 100 |
| Lv.6 | 荣耀行者 | 200 |
| Lv.7 | 传奇 | 400 |

**经验规则（只增不减、不降级）**：文章过审 +10（按文章去重，驳回后编辑重提再过审不重复加）、文章被赞 +2（给作者，自赞不计）、评论被赞 +1（给评论作者，自赞不计）、每日登录 +1（北京时间自然日封顶，重复登录不重复加）。禁用 / 已删除用户不再累计；历史 `forum_user_exp` 行不删，历史等级徽章仍正常展示。

**头衔**（首版示例名上线前与运营定稿；`code` 稳定，展示名/色板可改）：`pioneer` 开荒先锋 / `veteran` 资深旅人 / `contributor` 社区贡献者 / `official` 官方认证 / `legend` 传奇行者。

**契约变更**：`author.badge` 由单值字符串（`null`|`"管理员"`）改为**数组**（如 `["管理员","Lv.3","开荒先锋"]`，顺序 管理员 → 等级 → 头衔），已注销用户返回 `[]`。后台不缓存，author 下发即实时查询，撤销头衔前台即时失效。前端改动收敛在 `frontend/src/utils/forumBadges.js` 与 `frontend/src/components/forum/UserBadge.vue`（后台同名表 `admin-frontend/src/utils/forumBadges.ts`），其余组件经 `author.badge` 透传零改动。**不做**经验商城 / 排行榜 / 存量 retrofit（从上线起算，不补算历史行为）。

## 站内信（消息中心）

前台展示名「消息中心」，模块 / 接口 / 表名仍是站内信。实施依据 `docs/站内信/站内信功能PRD.md`；规约见 `docs/agents/messages.md`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/messages/unread-count` | 未读计数（定向未读 + 广播未点击），走包络 |
| GET | `/api/messages/stream` | **SSE 实时推送**（`text/event-stream`，第二个不走 `{code, message, data}` 包络的接口；需登录，帧协议见下） |
| GET | `/api/messages/replies` / `/likes` / `/system` | 三个分页列表（参数 page / pageSize），走包络 |
| POST | `/api/messages/{id}/read`、`/read-all`；DELETE | 标记单条 / 批量已读、删除定向消息，走包络 |

**SSE 帧协议（`GET /api/messages/stream`）**

- **鉴权**：原生 `EventSource` 不能自定义请求头，token 经 query 参数 `?token=<JWT>` 传递（后端 `get_stream_user` 专用依赖，同时兼容 `Authorization: Bearer`）。缺失 / 过期 token 在流前返回标准 HTTP 401 + `detail`；前端 EventSource error 后先由浏览器原生重连，连续失败 3 次则关闭连接并降级 60s 轮询。query token 可能出现在访问日志中，这是原生 EventSource 的固有限制。
- `event: unread` → `data: {"count": N}`：未读数。**建连首帧必发**；断线自动重连后以服务端值覆盖本地，弱网不错数。
- `event: refresh` → `data: {}`：提示客户端重拉当前打开的 Tab 列表；由常驻的 NavBar 转交给弹层（同一连接，弹层不另开 EventSource）。
- `event: closed` → `data: {"reason":"too_many_connections"}`：控制帧。同一用户上限 5 连接，超出立即优雅关闭最旧连接；收到后客户端应停掉 SSE 转轮询，避免自动重连来回踢连接。
- **心跳**：服务端每 ≤30s 发送注释行 `: ping\n\n` 保活。nginx 复用 kb/chat 的 SSE 四件套，两份配置 `web/nginx.conf` 与 `for-deploy/xqly-app.conf` 必须同步。
- **推送触发**：`messages.py` 各 `create_*_message` 写库成功后重算未读数并广播；已读 / 批量已读 / 删除成功后同样广播，保证多标签页一致。管理员 `POST /api/messages/admin/create`、`PUT /api/messages/admin/update/{id}`、`DELETE /api/messages/admin/delete/{id}` 写库成功后亦触达：广播消息经 `MessageStreamRegistry.online_users()` 遍历全部在线用户，逐用户重算未读并推送（每个用户未读数不同，不能复用单用户 publish 的单一帧）；定向消息只通知 `related_user_id` 指向的接收者。连接注册表 `InMemoryMessageStreamRegistry` 实现可替换接口 `MessageStreamRegistry`，仅适用生产单 worker；多 worker 前必须换成 Redis pub/sub（与限流共享存储同一条遗留）。

## 资源中心

资源中心一阶段 MVP：后台手动维护资源/版本/下载资产元数据，前台展示列表与详情，下载一律经本站端点 302 跳转到后台录入的 GitHub Release 资产链接。实施依据 `docs/资源中心/资源中心一阶段MVP需求.md`；GitHub Release **双轨同步**（2026-11-14 新增，覆盖原「不做自动同步」口径）：`docs/资源中心/GitHub Release 版本同步需求说明.md`，核心在 `backend/app/resource_sync_core.py`（纯 SQLAlchemy+httpx，API 层与定时 CLI 共用），定时任务 `backend/github_sync.py`。落点 `backend/app/resource_center.py`（请求模型 `app/pydantic_models.py`，五表 `app/database.py`：`dict_items` / `resources`（+三张关联表）/ `resource_versions` / `version_assets` / `download_events`）。**计数口径是「下载跳转次数」**——本站记录的是下载按钮跳转点击次数，文件由 GitHub 托管，不是 GitHub 实际下载量；**不做** 文件代理 / SHA-256 校验 / 下载量同步 / 用户系统（PRD「明确不做」）。

**公开接口（匿名可调）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/resources` | 资源列表（参数 `q`,`type`,`platform`,`game_version`,`side`,`channel`,`tag`,`sort`,`page`,`pageSize`；多值参数逗号分隔；`sort=updated_desc\|name_asc\|downloads_desc`；featured 恒排最前；多对多筛选走子查询 IN **无重复行**） |
| GET | `/api/resources/filters` | 筛选项字典（enabled 项按 type 分组：`resource_type`/`platform`/`game_version`/`side`/`release_channel`/`tag`；后台下拉与前台筛选共用一个来源） |
| GET | `/api/resources/{slug}` | 资源详情（只含 published；含版本列表（最新稳定版在前）+ 每版本可见资产 + `downloadCount`（按事件实时聚合）+ `downloadCountNote` 口径说明） |

**下载跳转端点（不挂 /api）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/download/asset/{assetId}` | 记录跳转事件后 **302** 到后台录入的 GitHub URL。资产/版本/资源任一隐藏、下架、非 published、软删 → **410**；不存在 → **404**；同 IP 超过 30 次/分 → **429**。**不接受任何 URL 参数**（跳转目标只取库内 `asset.url`，防开放重定向）；事件存 IP 哈希（sha256 截 16 位）+ UA/Referer 截断，不存原始 IP |

**管理员接口（`require_admin`）**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/resources/admin/page` | 资源管理分页（`keyword`,`status`=`draft\|published\|hidden\|archived\|deleted`；`deleted` 查回收站；带版本/资产计数） |
| GET | `/api/resources/admin/{id}` | 资源编辑回填（全字段 + 三组关联 key 数组） |
| POST | `/api/resources/admin` | 新建资源（slug 全局唯一、3-64 位小写字母/数字/连字符；`platforms`/`gameVersions`/`tags` 是字典 key 数组，未知 key 400） |
| PUT | `/api/resources/admin/{id}` | 编辑资源（部分更新；关联数组传了即全量重写） |
| POST | `/api/resources/admin/{id}/status` | 状态切换（`{status}`） |
| DELETE | `/api/resources/admin/{id}` | 软删除（`deleted_at`；数据保留可追溯） |
| POST | `/api/resources/admin/{id}/restore` | 从回收站恢复 |
| GET | `/api/resources/admin/{id}/versions` | 版本列表（含隐藏；每版本内嵌资产数组） |
| POST | `/api/resources/admin/{id}/versions` | 新建版本（同资源版本号唯一；`isLatestStable` 可直接勾选） |
| PUT | `/api/resources/admin/versions/{vid}` | 编辑版本（`isLatestStable=true` 触发唯一转移；非 stable 渠道 400） |
| DELETE | `/api/resources/admin/versions/{vid}` | **物理删除**版本（2026-11-14 改口径，原软删）：版本行及其全部资产行一并硬删（`resource_versions` 有 (resource_id,version) 全行唯一约束，软删会让 GitHub 批量同步撞约束 500、同号版本无法重建）；其 download_events 保留（统计口径不丢数据）。**不可恢复**，前端确认框已明示 |
| GET | `/api/resources/admin/versions/{vid}/assets` | 资产列表（含隐藏） |
| POST | `/api/resources/admin/versions/{vid}/assets` | 新建资产（URL 必须 `https://github.com/` 开头，否则 400；第一个 main 资产自动成为主资产） |
| PUT | `/api/resources/admin/assets/{aid}` | 编辑资产（`isPrimary=true` 同版本唯一转移；隐藏即时不可下载） |
| DELETE | `/api/resources/admin/assets/{aid}` | 软删除资产（主下载回落 sort 第一个可见资产） |
| GET | `/api/resources/admin/stats` | 下载跳转统计（`start`/`end`=`YYYY-MM-DD` 可选时间范围；返回 `total` + `byResource`/`byVersion`/`byAsset`（带名称）+ `daily` 曲线 + `note` 口径说明） |
| POST | `/api/resources/admin/{id}/github-sync` | **批量同步 GitHub Release**（只增不改，幂等）：拉最新 20 条 Release（`per_page=20`），过滤 draft 与 Source code 资产，按 `release_tag` 判存——本地已有同名 Tag 直接跳过，只新增缺失版本（新增默认 `status=visible`；**最新 Release**（列表第一条非 draft）若是 stable 渠道自动设为该资源最新稳定版（先清后立唯一转移，Beta 渠道不设并 warning）；兼容/平台继承资源级、首资产为主资产）。返回 `{added, skipped, fetched, warnings, syncedAt}`；message 固定文案「同步完成：新增 X 个版本，跳过 Y 个已存在版本」。整资源一个事务 |
| POST | `/api/resources/admin/versions/{vid}/github-sync` | **单版本精准同步**：按版本 `release_tag` 调 `/repos/{owner}/{repo}/releases/tags/{tag}` 覆盖 GitHub 字段（`version`=Tag 去 v、`channel`（prerelease→Beta/Stable）、`publishedAt`（北京时间 ISO）、`changelogMd`）+ 资产列表（**只替换 `source=github` 的资产行**，手动录入资产保留）。**绝不覆盖**：`status`/`isLatestStable`/`gameVersions`/`platforms`/`side`/`releaseTag`。404=Tag 不存在（可能已删除）、429=限流、400=未填 Tag/版本号冲突/仓库地址非法 |

- **唯一性口径**：slug 全局唯一（`_ensure_slug_free`）；同资源版本号唯一；「最新稳定版」每资源最多一个（唯一转移点 `_set_latest_stable`，先清后立同事务）；「主资产」每版本最多一个（`_set_primary_asset` 同款）。
- **冗余计数**：`resources.download_count` 与 `download_events` 插入**同事务**原子 UPDATE（与论坛 like_count 同思路，NullPool 每请求独立连接不会失配）；列表/排序读冗余列避免 N+1，详情与后台统计按事件实时聚合，两者可互相对账。
- **可见性三级联动**：下载端点实时校验「资产 visible + 版本 visible + 资源 published + 三方未软删」，版本/资源隐藏即时生效，无需物化处理资产。
- **GitHub 双轨同步口径**（`resource_sync_core.py`，唯一权威）：**批量=只增不改**（Tag 是唯一匹配键，重复执行幂等；新增版本默认 `visible`，**最新 Release** 是 stable 渠道时自动设最新稳定版——2026-11-14 调整，覆盖原「默认 hidden」口径）；**单版本=精准覆盖**（覆盖白名单仅 `version/channel/published_at/changelog_md/资产`，`status/is_latest_stable/game_versions/platforms/side/release_tag` 红线不碰）。版本与资产带 `source`（`manual`/`github`）与 `github_synced_at` 标记列（存量库幂等补列）。鉴权走 `.env` 的 `GITHUB_PAT`（留空=未认证 60 次/h；注入 `Authorization: Bearer` + `Accept: application/vnd.github+json` + `X-GitHub-Api-Version: 2022-11-28`；**Token 绝不进响应/日志/堆栈**）。请求 10s 超时、网络错误最多重试 2 次。资源 `githubRepoUrl` 保存时校验（`https://github.com/{owner}/{repo}`）。定时批量 `backend/github_sync.py`（03:30 遍历已发布且有合法仓库地址的资源，crontab 进镜像）。
- **字典表**：预置 24 项种子（类型/平台/游戏版本/侧别/渠道，幂等按 `type+key` 判存，不覆盖后台改过的值）；tag 无预置项由后台自建；停用用 `enabled=0`（MVP 无删除入口）。
- 端到端回归脚本：`cd backend && python3 resource_center_smoke_test.py`（临时库 + `TestClient`，66 项断言：CRUD/唯一性/可见性/302 与事件/防重定向/限速/筛选排序/软删/统计）。

## Wiki 动态文档（后台内容运营）

静态 VitePress 目录仍是知识库 `kb_sync.py` 的单一数据源；本节接口只管理「动态文档」——在后台「内容运营 → Wiki 文档/附件」维护，保存后 Wiki 站点的 `/wiki/dynamic-docs/` 立即可见，不需要重新构建静态站或重启后端。实现见 `backend/app/wiki.py`，表名 `wiki_documents`。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/wiki/documents` | 公开 | 已发布文档列表（`category` 可选；列表项不含正文） |
| GET | `/api/wiki/documents/{id}` | 公开 | 已发布文档详情（含 Markdown 正文） |
| GET | `/api/wiki/admin/documents` | 管理员 | 分页列表（`page/pageSize/keyword/category/published`） |
| GET | `/api/wiki/admin/documents/{id}` | 管理员 | 编辑回填（含正文） |
| POST | `/api/wiki/admin/documents` | 管理员 | 新建（`title/slug/category/summary/content/author/isPublished`；`slug` 唯一） |
| PUT | `/api/wiki/admin/documents/{id}` | 管理员 | 编辑（同上，`slug` 唯一性校验排除自身） |
| DELETE | `/api/wiki/admin/documents/{id}` | 管理员 | 删除 |
| POST | `/api/wiki/admin/upload` | 管理员 | 附件上传（`multipart/form-data`，字段名 `file`；≤20MB） |
| GET | `/api/wiki/admin/files` | 管理员 | 已上传附件列表 |
| DELETE | `/api/wiki/admin/files?path=` | 管理员 | 删除附件（仅允许 `wiki/YYYYMM/<name>` 相对路径） |
| GET | `/api/wiki/admin/categories` | 管理员 | 分类字典（与 Wiki 侧边栏分区对齐） |

附件落盘在 `uploads/wiki/YYYYMM/`，对外 URL 是 `/api/announcement/uploads/wiki/YYYYMM/<name>`，**复用现有静态挂载点、零 nginx 改动**。白名单：图片（png/jpg/jpeg/gif/webp，带魔数校验）+ PDF / Markdown / txt / Office / 压缩包 / JSON；不放行 SVG（同域托管可形成存储型 XSS）。`isPublished` 用 int（0=草稿，1=已发布），时间为北京时间 naive ISO 字符串，全部接口遵循 `{code, message, data}` 包络。

## 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/kb/info` | 智能客服元信息（见本文「知识库 / 智能客服」一节） |
| POST | `/api/kb/chat` | 智能客服流式问答（SSE，两个包络例外之一） |
| GET | `/api/messages/stream` | 站内信实时推送（SSE，另一个包络例外；见「站内信」一节） |
| * | `/api/kb/admin/mcp/*`、`/api/kb/admin/tool-config`、`/api/kb/admin/tool-logs`、`/api/kb/admin/chat-config`、`/api/kb/admin/models` | 智能客服 P1：MCP Server 管理 / 工具白名单 / 内置工具配置 / 调用审计 / 客服模型设置（模型+思考强度）/ 上游模型列表（见「MCP 扩展」小节） |

## 图片上传

富文本图片默认存放于 `backend/data/uploads/`（按月份分目录，随机文件名），应用启动时自动创建，经 `/api/announcement/uploads/` 静态目录对外提供（2026-09-25 起接口统一 /api 前缀；`/announcement/uploads/` 旧路径保留别名，兼容历史正文内嵌的旧图片 URL）：

- 可通过环境变量 `ANNOUNCEMENT_UPLOAD_DIR` 自定义（Docker 部署已在 docker-compose.yml 中指向挂载卷 `/app/data/uploads`）
- 生产 Nginx 将 `/api` 反代到 FastAPI，该子路径无需额外配置；`/announcement/uploads/` 旧路径保留兼容反代
- **社区图片复用同一挂载点**（因此**零 nginx 改动**）：论坛上传落盘到 `uploads/forum/YYYYMM/`，对外 URL 为 `/api/announcement/uploads/forum/YYYYMM/<uuid>.<ext>`。校验与落盘逻辑抽在 `backend/app/uploads.py`，公告与论坛共用一份口径（白名单 png/jpg/jpeg/gif/webp + `image/*` + ≤5MB + 随机文件名）
