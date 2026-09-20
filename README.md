# 星穹旅驿 · 服务器网站

星穹旅驿 Minecraft 服务器的官方网站，单仓库（monorepo）包含四个子项目：

| 模块 | 说明 | 技术栈 |
|------|------|--------|
| `frontend/` | 官网前端（首页、公告） | Vue 3 + Vite + Vue Router + Axios + ECharts |
| `backend/` | 官网后端（公告管理、用户认证、服务器状态） | FastAPI + SQLAlchemy (async) + SQLite (aiosqlite) + Pydantic v2 |
| `wiki/` | 服务器文档站 | VitePress |
| `admin-frontend/` | 后台管理前端（公告 / 服务器地址 / 用户 / 阵营内测申请管理） | Vue 3 + TypeScript + Element Plus + Pinia（[pure-admin-thin](https://github.com/pure-admin/pure-admin-thin)） |

## 项目结构

```
server-website/
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # axios 实例、接口封装、统一错误处理
│   │   ├── assets/              # 图片、字体等静态资源
│   │   ├── components/          # 通用组件（NavBar、ChatWidget、OnlineCounter、Leaderboard、TrendChart 等）
│   │   ├── config/mc-config.js  # 站点配置统一读取层（值来自 .env 环境变量）
│   │   ├── router/              # 路由定义
│   │   ├── utils/               # 工具函数
│   │   ├── views/               # 页面组件
│   │   ├── App.vue              # 根组件（导航栏 + 路由视图 + 页脚）
│   │   └── main.js              # 应用入口
│   ├── .env                     # 站点配置默认值（Vite 环境变量，随仓库提交）
│   ├── .env.development         # 开发模式覆盖（API 指向本地 FastAPI）
│   ├── .env.production          # 生产模式覆盖（API 同源相对路径）
│   ├── public/                  # 原样复制的静态资源
│   ├── index.html
│   └── vite.config.js
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口与公告路由
│   │   ├── database.py          # SQLAlchemy 模型 & 异步引擎/会话（含知识库 4 表 + WAL + FTS5）
│   │   ├── schemas.py           # Pydantic 模型（camelCase 别名）
│   │   ├── crud.py              # 公告 CRUD 操作
│   │   ├── faction_beta.py      # 阵营对战内测申请（用户提交 + 管理员审核）
│   │   ├── monitor.py           # 服务器监控（DB 持久化注册表 + TCP 探测）
│   │   ├── config.py            # 知识库配置读取（零依赖 .env 加载 → 模块级 KB 对象）
│   │   ├── kb_ingest.py         # 知识库：Markdown 清洗/切片/Embedding（纯逻辑）
│   │   ├── kb_index.py          # 知识库：内存向量索引（版本失效 + TopK，纯 stdlib）
│   │   ├── kb_retrieve.py       # 知识库：向量 + FTS5 trigram + RRF 混合检索
│   │   ├── kb_llm.py            # 知识库：OpenAI 兼容 chat 流式客户端（httpx）
│   │   └── kb.py                # 知识库：/kb/* 全部路由（SSE 问答 + 限流 + 管理接口）
│   ├── kb_sync.py               # wiki → 知识库 同步脚本（CLI，按 MD5 增量）
│   ├── run.py                   # uvicorn 启动脚本
│   ├── seed.py                  # 测试数据种子
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── data/                    # SQLite 数据库文件（gitignore；含密钥的 .env 亦已 gitignore）
├── wiki/                        # VitePress 文档站
│   ├── .vitepress/config.mts    # 站点配置（base: /wiki）
│   ├── for-new/                 # 萌新指南（进服教程、玩家条例、FAQ）
│   ├── management/              # 服务器管理（管理员条例）
│   ├── develop/                 # 服务器建设（发展路线、Issues）
│   ├── index.md                 # 首页（hero 布局）
│   └── package.json
├── admin-frontend/              # 后台管理前端（pure-admin-thin，部署在 /admin/）
│   ├── src/
│   │   ├── api/                 # 接口封装（announcement / server / user / factionBeta / kb / routes）
│   │   ├── components/          # 通用组件（RePureTableBar、ReDialog、ReAuth 等 pure-admin 封装）
│   │   ├── config/              # 平台配置读取层（Title 等，值来自 public/platform-config.json）
│   │   ├── directives/          # 自定义指令（auth / perms / ripple / longpress 等）
│   │   ├── layout/              # 后台框架（侧边菜单 + 顶栏 + 多标签页）
│   │   ├── plugins/             # Element Plus / ECharts 全局注册
│   │   ├── router/              # 路由与守卫（modules/home.ts 业务路由、remaining.ts 登录与错误页）
│   │   ├── store/modules/       # Pinia 模块（user 存 token/role、permission、multiTags 等）
│   │   ├── utils/http/          # PureHttp：axios 封装（JWT 注入、{code,message,data} 解包、错误提取）
│   │   ├── views/               # 页面（login、announcement、server、faction-beta、kb、user、error）
│   │   └── main.ts              # 应用入口
│   ├── .env / .env.development / .env.production   # 端口、base 路径、路由模式
│   ├── public/platform-config.json                 # 平台标题等运行时配置
│   ├── vite.config.ts           # dev proxy 把 API 前缀转发到后端 :5000
│   └── package.json
└── README.md
```

## 快速开始

环境要求：Node.js 20.19+（Vite 7 要求）、Python 3.10+。

### 后端

```bash
cd backend
pip install -r requirements.txt
python3 run.py
# 或: uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

服务启动在 `http://localhost:5000`，交互式 API 文档见 `http://localhost:5000/docs`。

### 前端

```bash
cd frontend
npm install
npm run dev
```

开发服务器监听 `http://localhost:5173`（Vite 默认端口）。开发模式下 API 请求直接指向 `http://localhost:5000`（后端已开启 CORS）。

### Wiki

```bash
cd wiki
npm install
npm run dev      # 开发服务器
npm run build    # 构建到 .vitepress/dist/
npm run preview  # 本地预览构建产物
```

站点以 `/wiki` 为 base 部署（见 `.vitepress/config.mts`）。

### 后台管理（admin-frontend）

```bash
cd admin-frontend
pnpm install
pnpm dev      # 开发服务器（端口取 .env.development 的 VITE_PORT，当前 3005，覆盖 .env 的 8848）
pnpm build    # 构建到 dist/（base: /admin/，hash 路由）
```

开发模式下 API 请求经 `vite.config.ts` 的 proxy（`/announcement`、`/monitor`、`/auth`、`/faction-beta`、`/kb`、`/health`）转发到后端 `http://localhost:5000`。登录账号即后端自动初始化的系统管理员（见「认证」一节）。

## 后端 API

### 公告

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/announcement/page` | 分页查询公告（参数: page, pageSize, isPublished） |
| GET | `/announcement/admin/page` | 管理员分页查询（**需管理员**；含草稿，参数: page, pageSize） |
| GET | `/announcement/detail/{id}` | 查询公告详情 |
| GET | `/announcement/prev-next/{id}` | 上一篇/下一篇导航（仅已发布公告按 id 序，跳过草稿；返回 `brief={id,title,publishTime}`） |
| POST | `/announcement/addWatchCount` | 阅读量 +1（body: `{announcementId}`） |
| POST | `/announcement/create` | 创建公告（**需管理员**） |
| PUT | `/announcement/update/{id}` | 更新公告（部分更新，**需管理员**） |
| DELETE | `/announcement/delete/{id}` | 删除公告（**需管理员**） |
| POST | `/announcement/upload/image` | 上传富文本图片（multipart `file`，≤5MB，png/jpg/jpeg/gif/webp，**需管理员**；返回 `data.url` 相对路径，可直接写入公告内容） |
| GET | `/announcement/uploads/{...}` | 上传图片静态目录（按月份分目录存放） |

- 公告正文对外字段为 `rawContent`（原始内容）+ `contentType`（内容格式，`'html'`=富文本 / `'markdown'`=Markdown；create/update 传参同名字段，缺省 `html`）。Markdown 渲染在前端完成，后端不做转换。

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/auth/captcha` | 获取注册用滑块拼图验证码（返回 `{captchaId, backgroundImage, pieceImage, sliderY}`，5 分钟有效；横向答案不下发仅存服务端） |
| POST | `/auth/captcha/verify` | 校验滑块位置（body: `{captchaId, x}`，误差 ≤5px 通过并标记该 captchaId；失败即作废，一次性防爆破） |
| POST | `/auth/register` | 注册（body: `{email, password, confirmPassword, captchaId}`，captchaId 须已通过滑块校验，注册时消费；邮箱作为账号，昵称默认取邮箱前缀，角色为普通用户） |
| POST | `/auth/login` | 登录（body: `{username, password}`，成功返回 `{token, username, nickname, role}`；禁用/已删除用户无法登录） |
| GET | `/auth/me` | 当前登录用户信息（Header: `Authorization: Bearer <token>`，返回 `{username, nickname, email, role}`；禁用/已删除用户的旧 token 一律失效） |

- JWT 默认 24 小时有效，环境变量 `JWT_EXPIRE_HOURS` 可调；签名密钥取环境变量 `JWT_SECRET`，未设置时自动生成并持久化到数据目录。
- 系统管理员 `xqly-admin` 在后端首次启动时自动初始化，随机强密码写入数据目录 `admin_initial_password.txt`（仅首次初始化时写入，请妥善保管并及时删除）。

### 用户管理（管理员）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/auth/admin/users` | 分页查询用户（参数: page, pageSize, status 可选；status 1=正常, 0=禁用, 2=已删除，缺省查全部） |
| POST | `/auth/admin/users` | 新增用户（body: `{username, nickname?, password, role, email?}`；账号 2-100 位字母/数字及 . _ % + -，昵称 ≤50 字符，密码 8-32 位含字母数字，role 仅 admin/user） |
| PUT | `/auth/admin/users/{id}` | 编辑用户（body: `{nickname?, role?, email?, password?}`；**账号 username 不允许修改**；昵称/角色/邮箱可改，密码留空=不修改（忘记密码重置场景）；已删除用户禁止编辑） |
| PUT | `/auth/admin/users/{id}/status` | 切换用户状态（body: `{status: 1\|0\|2}`；1=启用, 0=禁用, 2=删除（软删除，数据保留可恢复）） |
| DELETE | `/auth/admin/users/{id}` | 软删除用户（status 置为已删除，无法登录，数据保留可恢复） |

- 所有接口需 `Authorization: Bearer <JWT>` 且角色为 `admin`，无 token 返回 401，普通用户返回 403。
- 用户 `status` 三态：`1=正常`、`0=禁用`（无法登录，可重新启用）、`2=已删除`（软删除，无法登录，数据保留可恢复）。
- 用户表 `username`（账号）为登录标识，创建后不可修改；`nickname`（昵称）为展示名，可随时修改。
- 存量数据库首次启动自动补 `users.status` / `users.nickname` 列（status 默认 1=正常，nickname 默认为空）。

### 阵营对战内测申请

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/faction-beta/apply` | 提交内测申请（**需登录**；body: `{mcId, email, faction, experience, weeklyHours, motivation}`，每账号一份，被拒后可重新提交覆盖） |
| GET | `/faction-beta/my` | 查询当前用户申请（**需登录**；未提交时 `data.application` 为 `null`） |
| GET | `/faction-beta/admin/page` | 管理员分页查询（**需管理员**；参数: page, pageSize, status 可选过滤） |
| PUT | `/faction-beta/admin/{id}/review` | 审核申请（**需管理员**；body: `{status: 1\|2, reviewNote?}`） |
| DELETE | `/faction-beta/admin/{id}` | 删除申请（**需管理员**） |

- 申请状态 `status`：`0=待审核, 1=已通过, 2=未通过`；字段 camelCase（`mcId` / `weeklyHours` / `reviewNote` / `reviewTime` 等）。
- 表单选项（期望阵营 / PvP 经验 / 每周时长）以后端 `faction_beta.py` 白名单为唯一权威，前端选项需与其保持一致。

### 服务器监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/monitor/servers` | 游戏服务器地址列表（前端展示的唯一数据源） |
| GET | `/monitor/server-info/{serverId}` | 服务器在线状态（TCP 探测，供首页在线状态组件） |
| GET | `/monitor/admin/servers` | 管理员获取全部服务器（**需管理员**） |
| POST | `/monitor/admin/servers` | 新增服务器（**需管理员**） |
| PUT | `/monitor/admin/servers/{id}` | 更新服务器（**需管理员**） |
| DELETE | `/monitor/admin/servers/{id}` | 删除服务器（**需管理员**） |
| POST | `/monitor/admin/servers/{id}/primary` | 设为主服务器（**需管理员**） |

- 服务器地址持久化在 SQLite `servers` 表（**DB 为唯一权威，内存 `SERVERS` 字典为读缓存**）：启动时 `load_servers()` 读库填充内存，表为空时用默认注册表做种子；后台管理页的增删改先改内存再同步落库（先 commit 再返回，失败回滚内存），**重启不再丢失**（原"重启即重置"行为属 bug，已修复）。不能删除主服务器，设主 / 设 `isPrimary` 会自动清除其他服务器的主标记，全表始终至多一个主服务器。

### 知识库 / 智能客服（P0）

官网内置基于 wiki 文档的知识库智能客服：向量 + FTS5 trigram 混合检索、SSE 流式回答、思考过程与来源引用展示，答不了时引导进 QQ 群。设计规格见 `docs/智能客服P0落地方案.md`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/kb/info` | 客服元信息（`enabled` / `title` / `greeting` / `faq` / `model`；未配置 API Key 时 `enabled:false`，前端不渲染悬浮球） |
| POST | `/kb/chat` | **SSE 流式问答**（body: `{message, history?}`；`text/event-stream`，**全项目唯一不走 `{code, message, data}` 包络的接口**，帧协议见下方） |
| GET | `/kb/admin/documents` | 文档分页列表（**需管理员**；参数: page, pageSize, sourceType 可选） |
| POST | `/kb/admin/documents` | 手动新增知识（**需管理员**；body: `{title, content}`，同步切片 + Embedding） |
| DELETE | `/kb/admin/documents/{id}` | 删除文档（**需管理员**；`wiki` 来源返回 400，提示走同步脚本） |
| GET | `/kb/admin/documents/{id}/chunks` | 切片预览（**需管理员**） |
| POST | `/kb/admin/documents/{id}/reindex` | 重建（**需管理员**；幂等：wiki 来源读源文件整篇重建，manual 来源重嵌入现有切片） |
| GET | `/kb/admin/stats` | 统计（**需管理员**；文档数 / 切片数 / 索引版本 / 维度一致性 / 总字符数） |

SSE 帧协议（UTF-8 JSON，空行分隔，`ensure_ascii=False`）：

```
data: {"sources":[{"id":12,"title":"进服教程 / Java 客户端","sourceType":"wiki","score":0.83}]}   ← 首帧固定（无命中为 []）
data: {"reasoning":"..."}    ← 思考过程（思考模型才有），与 delta 可交错
data: {"delta":"..."}        ← 回答正文增量
data: {"fallback":true}      ← 可选：命中引导话术时附带
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

知识库配置（`backend/.env`，**已 gitignore，含 API Key 勿提交**）：总开关 `KB_ENABLED`；对话模型 `KB_CHAT_BASE_URL` / `KB_CHAT_API_KEY` / `KB_CHAT_MODEL`（OpenAI 兼容）+ 可选 `KB_CHAT_EXTRA_BODY`（厂商私有参数原样 merge）；Embedding `KB_EMBED_BASE_URL` / `KB_EMBED_API_KEY` / `KB_EMBED_MODEL` / `KB_EMBED_DIM`；检索 `KB_TOP_K` / `KB_MIN_SCORE` / `KB_MAX_CHUNKS` 等；文案 `KB_TITLE` / `KB_GREETING` / `KB_FALLBACK_HINT`。改 `.env` 需重启后端生效。启动自检：密钥缺失 → 客服自动关闭（`/kb/info` 返回 `enabled:false`，`/kb/chat` 503）；库内向量维度/模型与配置不一致 → 关闭向量检索降级为仅 FTS，`/kb/admin/stats` 标记"需重建索引"。

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/kb/info` | 智能客服元信息（见「知识库 / 智能客服」） |
| POST | `/kb/chat` | 智能客服流式问答（SSE，唯一不走包络） |

**约定**

- 响应统一为 `{code, message, data}` 结构，`code=0` 表示成功；**唯一例外是 `POST /kb/chat`（SSE 流无法包络）**。
- 公告字段使用 camelCase（`publishTime` / `isPublished` / `readCount` / `createTime` / `updateTime`），由 Pydantic 字段别名映射。
- 游戏服务器地址统一由后端维护：持久化在 `servers` 表，后台「服务器地址管理」页增删改，内存 `SERVERS` 字典（`backend/app/monitor.py`）只是读缓存；前端一律经 `/monitor/servers` 获取，禁止硬编码。
- 管理员接口使用 `Authorization: Bearer <JWT>` 鉴权：无 token 返回 401，普通用户返回 403。

### 数据库

使用 SQLite：

- 默认路径：`backend/data/announcements.db`（启动时自动建表）
- 可通过环境变量 `ANNOUNCEMENT_DB` 自定义

公告正文支持两种格式（`contentType` 字段区分，存量数据自动归为 `html`）：

- `html`：富文本编辑器（wangEditor）产出的 HTML，入库前由后端 `nh3` 白名单消毒（仅放行常用标签 + `style` 内联样式）。
- `markdown`：Markdown 源码，原样入库（nh3 会破坏 Markdown 语法），由前端渲染——主站用 `marked` + `DOMPurify` 消毒后展示，后台编辑器为 md-editor-v3（双编辑器共存，按格式自动切换）。

### 图片上传

富文本图片默认存放于 `backend/data/uploads/`（按月份分目录，随机文件名），应用启动时自动创建，经 `/announcement/uploads/` 静态目录对外提供：

- 可通过环境变量 `ANNOUNCEMENT_UPLOAD_DIR` 自定义（Docker 部署已在 docker-compose.yml 中指向挂载卷 `/app/data/uploads`）
- 生产 Nginx 已按 `/announcement` 前缀反代到 FastAPI，该子路径无需额外配置

### 种子数据

```bash
cd backend
python3 seed.py
```

### Docker 部署

```bash
cd backend
docker compose up -d --build
```

镜像基于 `python:3.14-slim`，容器内通过 `run.py` 启动服务；宿主机 5000 端口映射到容器 5000，数据持久化在 `backend/data/`。

## 前端

### 页面与路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Home | 首页：hero 横幅、服务器特色、加入服务器（地址来自 `/monitor/servers`）、论坛展示、在线状态 |
| `/announcements` | Announcements | 公告列表（分页） |
| `/announcements/:id` | AnnouncementDetail | 公告详情（自动累加阅读量） |
| `/faction-beta` | FactionBetaApply | 阵营对战玩法内测资格申请（需登录后填写，展示审核状态） |
| `/login` | AuthView（登录） | 登录页（用户名/邮箱 + 密码） |
| `/register` | AuthView（注册） | 注册页（邮箱 + 密码 + 确认密码 + 滑块拼图人机验证） |

### 关键组件

- `NavBar` — 顶部导航栏
- `ChatWidget` — 智能客服悬浮组件（流式打字机、思考过程折叠、来源引用、QQ 群引导；块级 keyed 流式渲染）
- `OnlineCounter` — 服务器在线状态（轮询 `/monitor/server-info/{id}`）
- `Leaderboard` / `TrendChart` — 排行榜与趋势图（ECharts）
- `ContentCard` / `ImageCarousel` / `SectionNav` / `CopyButton` / `BackToTop` / `Modal` — 展示与交互组件

### API 层（`src/api/`）

- `axiosInstance.js` — axios 实例，baseURL 来自环境变量 `VITE_BASE_API_URL`（经 `mc-config.js` 统一读取）；响应拦截器统一解包 `{code, message, data}`，失败时弹出错误提示；请求拦截器自动携带 JWT，401 时清除登录态并跳转 `/login`
- `api.js` — 接口封装：`authAPI` / `announcementAPI` / `factionBetaAPI` / `serverMonitorAPI` / `serverConfigAPI` / `chatAPI`（`chatAPI.streamChat` 因 SSE 流式改用 `fetch` + `ReadableStream`，其余走 axios）
- `errorHandler.js` — 统一错误弹窗工具

### 环境配置（`frontend/.env*` 文件）

站点配置通过 Vite 环境变量提供：`.env` 存放所有模式共用的默认值，`.env.development` / `.env.production` 按构建模式覆盖，本地个性化覆盖写 `.env.local`（已被 gitignore）。`src/config/mc-config.js` 是统一读取层，组件不要直接读 `import.meta.env`。

| 变量 | 说明 | dev 默认 | prod 默认 |
|------|------|----------|-----------|
| `VITE_BASE_API_URL` | API 基础地址 | `http://localhost:5000` | 留空（同源相对路径，由 Nginx 反代到后端） |
| `VITE_SERVER_ID` | 监控接口路由参数（对应后端 `SERVERS` 主服务器 id） | `1` | `1` |
| `VITE_JAVA_VERSIONS` / `VITE_BEDROCK_VERSIONS` | 支持的游戏版本文案 | 见 `.env` | 见 `.env` |
| `VITE_QQ_GROUP_ID` / `VITE_QQ_GROUP_CODE_IMG_URL` / `VITE_QQ_GROUP_INVITE_LINK_URL` | QQ 群信息 | 见 `.env` | 见 `.env` |
| `VITE_ADMIN_URL` | 后台管理入口地址 | `/admin` | `/admin` |
| `VITE_CHAT_WIDGET_ENABLED` | 智能客服悬浮球前端开关（后端 `/kb/info` enabled 为二级开关，两级都开才渲染） | `true` | `true` |
| `VITE_CHAT_WIDGET_TITLE` / `VITE_CHAT_WIDGET_GREETING` / `VITE_CHAT_WIDGET_FAQ` | 客服标题 / 欢迎语 / 首屏示例问题（`\|` 分隔） | 见 `.env` | 见 `.env` |

环境变量在构建期静态替换，修改后需重启 dev server 或重新构建才生效。

## 生产部署

前后端同域部署，由 Nginx 统一入口：

- `frontend` 构建产物（`npm run build` → `dist/`）作为静态站点托管
- `/announcement`、`/monitor`、`/auth`、`/faction-beta`、`/kb`、`/health` 等 API 路径反向代理到本机 FastAPI（5000 端口）；其中 `/kb/` 的反代需为 SSE 追加：`proxy_http_version 1.1`、`proxy_set_header Connection ''`、`proxy_buffering off`、`proxy_cache off`、`gzip off`、`proxy_read_timeout 300s`（与后端响应头 `X-Accel-Buffering: no` 两个都要，否则流式被缓冲成一次性返回）
- `wiki` 构建产物挂在 `/wiki/` 路径下（VitePress `base: '/wiki'`）
- `admin-frontend` 构建产物挂在 `/admin/` 路径下（pure-admin-thin，`base: '/admin/'`）

## 后台管理（admin-frontend）

独立的后台管理前端，基于 [pure-admin-thin](https://github.com/pure-admin/pure-admin-thin)（Vue 3 + TypeScript + Element Plus + Pinia + TailwindCSS 4 + Vite），生产部署在 `/admin/` 路径下，**hash 路由模式**。

### 页面与路由

业务路由在 `src/router/modules/home.ts` 中静态注册（登录/错误页在 `remaining.ts`），根路由 `/` 登录后重定向到 `/announcement/list`。后端未实现 `/get-async-routes` 动态菜单接口，动态路由为空，仅静态路由生效。

| 路由（hash） | 页面 | 说明 |
|------|------|------|
| `/login` | 登录页 | 用户名 + 密码（JWT；无验证码） |
| `/announcement/list` | 公告管理 | 公告列表（分页，含草稿；新建/编辑/删除） |
| `/announcement/edit` | 公告编辑 | 新建或编辑公告（标题、正文、发布人、发布时间、发布状态；正文按 `contentType` 切换 wangEditor 富文本 / md-editor-v3 Markdown，富文本图片经 `/announcement/upload/image` 上传） |
| `/server/list` | 服务器地址管理 | 服务器列表（新增/编辑/删除/设为主服务器；持久化在 `servers` 表，重启不丢失，见「服务器监控」） |
| `/server/edit` | 服务器编辑 | 新建或编辑服务器（名称、地址、端口、是否主服务器） |
| `/faction-beta/list` | 阵营内测申请 | 申请列表（状态过滤、详情弹窗、通过/拒绝、删除） |
| `/kb/list` | 知识库 | 统计条（文档/切片/索引版本/维度状态）+ 文档列表（来源过滤、切片预览抽屉、重建索引、删除；wiki 来源只读由 `kb_sync.py` 维护）+ 粘贴新增 |
| `/user/list` | 用户管理 | 用户列表（新增/编辑/启用/禁用/软删除/恢复、状态过滤；编辑模式密码留空=不修改） |
| `/access-denied` `/server-error` | 403 / 500 | 全屏错误页 |

浏览器 URL 带部署前缀与 hash：开发 `http://localhost:3005/#/announcement/list`，生产 `http://<host>/admin/#/announcement/list`。

### HTTP 层（`src/utils/http/`）与 API 模块（`src/api/`）

- `utils/http/index.ts`（PureHttp）— axios 封装：`baseURL` 留空（同源相对路径，dev 由 Vite proxy、prod 由 Nginx 反代到后端）；请求拦截器对 `/auth/login`、`/auth/register`、`/auth/captcha` 白名单放行，其余自动携带 `Authorization: Bearer <token>`；响应拦截器统一解包 `{code, message, data}`（`code=0` 直接返回 `data`），业务错误与 HTTP 非 2xx 都把 FastAPI `detail` 或包络 `message` 提取到 `error.message`——页面 catch 里直接 `ElMessage.error(e.message)`，不要重复解析错误体；401（HTTP 401 或包络 401/1001）自动清除登录态并跳回登录页
- `api/` — `announcement.ts` / `server.ts` / `user.ts` / `factionBeta.ts` / `kb.ts` 分别封装对应 admin 接口，TS 类型与后端契约一致；**新增或修改后端接口时必须同步主站契约参照 `frontend/src/api/api.js` 与本目录**（见 AGENTS.md 契约规约）
- 传 `FormData`（文件上传）时必须显式加 `Content-Type: multipart/form-data` 请求头，否则 axios 会把 FormData 序列化成 JSON，后端解析不到字段直接 422

### 登录与鉴权

- 登录走 `/auth/login`，token 与用户信息（含 `role`）存 localStorage（`utils/auth.ts`）；路由守卫（`router/index.ts`）对未登录访问一律重定向 `/login`，已登录访问 `/login` 保持当前页
- 后端所有 admin 接口要求 `role=admin`，普通用户 token 调用返回 403

### 环境配置（`admin-frontend/.env*`）

| 变量 | 说明 | dev（`.env.development`） | prod（`.env.production`） |
|------|------|--------------------------|---------------------------|
| `VITE_PORT` | dev server 端口（`.env` 默认 8848，被覆盖） | `3005` | — |
| `VITE_PUBLIC_PATH` | 构建基础路径 | `/` | `/admin/` |
| `VITE_ROUTER_HISTORY` | 路由模式 | `hash` | `hash` |
| `VITE_CDN` / `VITE_COMPRESSION` | CDN 依赖 / 构建压缩 | — | `false` / `none` |

页面标题等运行时配置在 `public/platform-config.json`（`Title` 等，经 `src/config/index.ts` 读取）。

### 开发与部署

```bash
cd admin-frontend
pnpm install
pnpm dev        # 开发服务器（:3005，API 经 vite proxy 转发到后端 :5000）
pnpm build      # 构建到 dist/（base: /admin/）
pnpm typecheck  # tsc + vue-tsc 类型检查
```

- 开发模式：Vite dev server（:3005），`vite.config.ts` 的 proxy 把 `/announcement`、`/monitor`、`/auth`、`/faction-beta`、`/kb`、`/health` 转发到后端 FastAPI（:5000）
- 生产模式：`pnpm build` → `dist/`，由 Nginx 挂在 `/admin/` 路径下；hash 路由刷新无需 `try_files` 兜底，API 请求为同源相对路径，命中 Nginx 既有反代规则
- 管理员入口：主站已登录管理员点击头像下拉菜单 → 「后台管理」（仅管理员角色可见，URL 来自 `frontend` 的 `VITE_ADMIN_URL`，默认 `/admin`）
