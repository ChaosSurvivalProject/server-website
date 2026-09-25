# AGENTS.md

星穹旅驿 Minecraft 服务器官方网站（frontend + backend + wiki 三合一仓库）。

整体架构、目录树与接口清单见 [README.md](README.md)；**本文件只记录项目特有的规约与坑**，通用工程惯例不在此重复。

## 仓库结构要点

- 四个子项目相互独立，各自持有 `package.json` / `node_modules`，**没有根级 workspace**，仓库也没有根级 `package.json`——所有安装、构建、开发命令必须在对应子目录（`frontend/`、`backend/`、`wiki/`、`admin-frontend/`）内执行。
- 不要提交 `node_modules/`、`dist/`、`*.db`、`backend/data/`、`wiki/.vitepress/cache|dist/`（见 `.gitignore`）。

## 常用命令

```bash
# 后端 (FastAPI, :5000)
cd backend
pip install -r requirements.txt
python3 run.py            # uvicorn --reload，开发用
python3 seed.py           # 写入示例公告数据
docker compose up -d --build   # Docker 部署（构建上下文为项目根目录，见下）

# 前端 (Vite, :5173)
cd frontend
npm install
npm run dev
npm run build             # 产物 dist/，gitignore

# Wiki (VitePress)
cd wiki
npm install
npm run dev
npm run build             # 产物 .vitepress/dist/

# 后台管理 (Vite + Element Plus, :8848)
cd admin-frontend
pnpm install
pnpm dev                  # 开发服务器（端口由 .env.development 的 VITE_PORT 决定，当前 3005，覆盖 .env 里的 8848），API 代理到后端 :5000
pnpm build                # 产物 dist/，部署到 /admin/
```

## API 契约规约

这是本项目最容易踩坑的部分，改接口前必读：

0. **统一前缀**：所有后端接口统一挂载在 `/api` 前缀下（2026-09-25 起，`backend/app/main.py` 经 `api_router` + `include_router(prefix="/api")` 实现；nginx 只反代 `/api`）。新增接口一律写 `/api/...`；正文内嵌的上传图片规范 URL 也是 `/api/announcement/uploads/...`（旧路径 `/announcement/uploads/...` 仅为存量公告兼容保留，勿用于新内容）。
1. **响应包络**：所有接口返回 `{code, message, data}`，`code=0` 表示成功。前端 `axiosInstance` 响应拦截器已统一解包（直接返回 `data`），组件代码拿到的就是裸数据——**不要在前端组件里再判断 `code`**。
2. **字段命名**：数据库/后端内部用 snake_case，对外 JSON 用 camelCase（`publishTime` / `isPublished` / `readCount` / `createTime` / `updateTime`）。Pydantic 模型通过 `alias` + `populate_by_name=True` 映射（见 `backend/app/schemas.py`），新增字段必须同时补别名。
3. **契约参照实现**：`frontend/src/api/api.js` 是前后端契约的参照。**新增或修改后端接口时必须同步该文件**，保持两侧一致。后台管理前端 `admin-frontend/src/api/` 同步维护；其 HTTP 层（`admin-frontend/src/utils/http/`）已统一解包 `{code, message, data}`，并把 HTTP 错误体（FastAPI `detail` / 包络 `message`）提取到 `error.message`，页面 catch 里直接 `ElMessage.error(e.message)` 弹提示，**不要在页面里重复解析错误体**。传 `FormData`（文件上传）时必须显式加 `Content-Type: multipart/form-data` 请求头：实例默认 `application/json` 会让 axios 把 `FormData` 序列化成 JSON，后端解析不到字段直接 422。
4. **时间格式**：统一存 ISO 字符串 `YYYY-MM-DDTHH:MM:SS`（SQLite 中为 `String(30)` 列，不用 datetime 类型）。
5. **布尔语义用 int**：如 `isPublished`，`0=草稿, 1=已发布`，不要改成 bool。
6. **监控接口**：`GET /api/monitor/server-info/{id}` 目前是 TCP 探测的最小实现（`online/offline` + 占位字段），响应结构被首页 `OnlineCounter` 组件依赖，扩展时不能破坏现有字段。
7. **公告正文双格式**：对外字段为 `rawContent`（原始内容）+ `contentType`（`'html'`=富文本 / `'markdown'`=Markdown，缺省 `html`；Pydantic 侧 Python 字段名仍是 `content`/`content_type`，仅 alias 对外）。`html` 行入库前经 `nh3` 消毒；`markdown` 行**原样入库**（nh3 会破坏 Markdown 语法），渲染全在前端——主站 `src/utils/markdown.js`（marked + DOMPurify）统一渲染并消毒，后台按格式切换 wangEditor / md-editor-v3。新加内容格式相关逻辑时不要绕过这两个入口。
8. **SSE 包络例外（全项目唯一）**：`POST /api/kb/chat` 返回 `text/event-stream`，**不返回 `{code, message, data}` 包络**——SSE 流无法包络，这不是遗漏，不要"修正"它。**仅登录用户可调用**：`get_current_user` 依赖校验 Bearer JWT，未登录/过期 401（属流前错误，标准 HTTP + `detail`）；`streamChat` 用裸 `fetch` 不走 axiosInstance，需自行携带 token。帧协议见 `docs/智能客服P0落地方案.md` §4.3（首帧 `sources`、`delta`/`reasoning` 交错、`[DONE]` 收尾；流前错误走标准 HTTP + 包络口径的 `detail`，流开始后只能发 `{"error":...}` 帧）。`frontend/src/api/api.js` 的 `chatAPI.streamChat` 因此用 `fetch` + `ReadableStream` 而非 axios。

## 知识库 / 智能客服规约

- **wiki 是知识库的单一数据源**：`source_type='wiki'` 的文档由 `backend/kb_sync.py`（CLI，按文件 MD5 增量）维护，后台管理页对 wiki 来源只读（删除接口直接 400）；手动粘贴入库为 `manual` 来源。改动知识库一律先改 wiki，再跑脚本。
- **索引热更新是设计点**：脚本/后台每次摄入或删除都自增 `kb_settings.index_version`，服务端每轮对话轻量 SELECT 比对版本，不同才重建内存向量索引——**服务端不需要重启**，别改成"重启生效"。
- 检索为向量 + FTS5 trigram 双路 RRF 融合（`KB_HYBRID_ENABLED=0` 关混合）；FTS 表是**独立表**（非 external content），写入/删除时手动同步 `rowid = kb_chunks.id`，不要加触发器。
- 限流状态在**进程内**（滑动窗口 + 并发计数），P0 按单 worker 部署；改多 worker 必须换共享存储，否则限流失效。
- 知识库配置在 `backend/.env`（**已 gitignore，含 API Key 禁止提交**），`app/config.py` 启动期一次性读入模块级 `KB` 对象——改 `.env` 需重启进程，不要做请求级读取。
- 流式渲染必须复用 `frontend/src/utils/markdown.js` 管线：新增的 `splitMarkdownBlocks`（lexer 切块 → 逐块 parser → DOMPurify）与整篇 parse 等价，ChatWidget 的块级 keyed 渲染 + 末块未闭合补全都建立在它之上，不要绕开另写渲染入口。

## 员工名片模块规约

- **完整身份码是管理员端专属**：公开接口（`/api/staff/public/*`）一律不下发完整 `staffCode` 与 `remark`（验证页正文只显示展示码后四位 `••••xxxx`）；「导出名单 CSV」（`/api/staff/admin/export`）是需求 §10.1「不返回完整身份码列表」的**唯一豁免点**（需求 §8.1 要求导出名单，矛盾解已拍板）——**不要把它当漏洞"修掉"**；删除该接口前先改 `docs/员工名片模块需求规格.md`。
- **状态两态 + `valid_to` 权威**：`staff.status` 只存 `active` / `revoked`（无第三态 expired）；过期判定**只看 `now > valid_to`**，命中时由 `expire_due()` 把 active 回写为 `revoked`（`revoked_reason='expired'`，该值仅系统写入、后台撤销下拉里不得出现）。回写两路径共用同一函数：公开验证接口查询时懒更新（幂等）+ `backend/staff_expire.py`（CLI + crontab 每日一次，`main.py` 启动时也跑一次）；**crontab 漏挂不影响核验正确性**，勿把状态判定改成"以 status 为准"。
- **续期必须能救回过期**：`renew` 对 `revoked_reason='expired'` 的记录自动恢复 active 并清空撤销字段（二维码不变）；对人工撤销（离职/转岗/暂停/码异常）返回 400，必须先 `restore`（restore 强制换新码）。缺这条会出现"续期成功但扫码仍显示失效"的静默不一致。
- **二维码 URL 由后端单一来源拼接**：`STAFF_PUBLIC_BASE_URL`（`backend/.env`，启动期读入 `config.STAFF`，无尾斜杠）→ `f"{BASE}/staff/{code}"`；前端不得拼 URL、不得传 URL。生成参数：纠错 M、border=4、box_size=10；**禁止硬编码 `version=`**（49 字节 URL 实测 v4，由库自动选版，硬编码会在域名/码长变更时直接抛 DataOverflowError）。
- **名片模板（`admin-frontend/src/views/staff/card.vue`）**：出图依赖**必须用 `html2canvas-pro`**（html2canvas 维护 fork，API 相同）——原版 1.4.1 已停更且不支持 oklch，而 pure-admin 全局挂了 Tailwind v4 主题（`:root` 色板全是 oklch），用原版导出名片必报 `Attempting to parse an unsupported color function "oklch"`（2026-09-25 踩过，勿换回 `html2canvas`）。二维码承载区**必须纯白底**（改透明/深色会扫不出来）；`.qrcode` 200px（印刷 ≥20mm 阈值）；正面含像素头像（canvas 关平滑放大）+ 游戏ID（二维码下方）+ 名片版本 + 防伪提示；PNG/JPG 走本地 npm 依赖（**勿改回 CDN**，与"不依赖第三方平台"冲突且离线不可用），PDF 走浏览器 `window.print()`；卡片子树颜色只用纯 hex/rgb（纵深防御，不能替代 html2canvas-pro）。
- **P0 有意不做**（顺延 P1，已登记 `TODO.md`，勿当缺陷补齐）：应用层限流、查询日志审计（`staff_verify_log` 表不建）、服务端名片渲染（Pillow + CJK 字体）、到期推送通知。P0 依据：身份码 12 位 × 32 字符表 ≈ 1.15×10¹⁸，枚举不可行。
- 职务配色表（服主蓝/技术员绿/财务橙/管理员紫/建筑棕/客服青，只区分职务不代表权限）在三处保持一致：`frontend/src/utils/staffRoles.js`、`admin-frontend/src/views/staff/list.vue`、`admin-frontend/src/views/staff/card.vue`。

## 游戏服务器地址：单一数据源

- 游戏服务器地址持久化在 SQLite `servers` 表（**DB 为唯一权威**）；`backend/app/monitor.py` 的内存 `SERVERS` 字典只是读缓存，启动时 `load_servers()` 从库加载（表空时用文件内默认注册表做种子）。后台「服务器地址管理」页经 admin 接口增删改（先改内存再同步落库，失败回滚内存）。
- **禁止在前端硬编码服务器地址**；前端一律通过 `GET /api/monitor/servers` 获取（env 里只保留监控接口所需的 `VITE_SERVER_ID`，经 `mc-config.js` 暴露为 `server.id`）。
- 新增/修改服务器 = 后台管理页操作或调 admin 接口（持久化）；不要再改代码里的注册表。

## 前端配置规约

- 主站配置一律走 Vite 环境变量（`VITE_` 前缀）：`frontend/.env` 存所有模式共用的默认值（QQ 群、服务器 id、版本文案、后台入口等），`.env.development` / `.env.production` 按构建模式覆盖（dev → 本地 5000，build → 同源）；本地个性化覆盖写 `.env.local`（根 `.gitignore` 的 `*.local` 已忽略）。**三个 `.env` 文件随仓库提交，禁止在组件里直接读 `import.meta.env` 或在别处硬编码这些值**。
- `frontend/src/config/mc-config.js` 只是环境变量的统一读取层（含类型转换），**不要在其中硬编码站点值**；组件一律 `import McConfig` 取值。
- 生产环境 API 走同源（`VITE_BASE_API_URL` 留空 → `baseApiURL: ''`），依赖 Nginx 反代 `/api` 到本机 FastAPI（:5000）。
- 环境变量是构建期静态替换，改 `.env*` 后需重启 dev server / 重新 build 才生效。
- 模板中引用的静态图片必须先 `import` 再绑定 `:src`（如 `Home.vue` 的 `bbs-*.png`、`video-bg.jpg`）；**禁止直接写 `/src/...` 绝对路径**——Vite build 不会打包该路径，生产环境会 404（dev 下看不出来）。

## Wiki 规约

- VitePress `base: '/wiki'` + `cleanUrls: true`。站内链接写相对路径（VitePress 自动加 base）；**外链必须带协议**（`http(s)://`），否则会被加上 `/wiki` 前缀。
- 内容分三大分区，新增页面放对应分区并在 `.vitepress/config.mts` 侧边栏登记：`for-new/`（萌新指南）、`management/`（服务器管理）、`develop/`（服务器建设）。
- 站点外链域名（2026-09-25 起）：官网为 `https://xqly.xt91tv.shop:23333`（HTTPS，明文 HTTP 已禁）。wiki 内指向官网的外链（hero「访问官网」按钮、阵营文档申请入口等）统一写此地址，不要再写死 IP。

## Git 规约

- 远程：`git@github.com:ChaosSurvivalProject/server-website.git`，主分支 `main`。
- 提交信息使用 Conventional Commits 前缀（`feat` / `fix` / `refactor` 等，可带 scope 如 `feat(backend):`），描述用中文。

## 部署拓扑（生产）

**生产对外地址：`https://xqly.xt91tv.shop:23333`**（2026-09-25 起启用）。NAT 外部 23333 → 内部 80，nginx 在内部 80 上**直接跑 SSL**——不是 80→443 跳转，443 无监听；明文 HTTP 请求触发 497，经 `error_page 497` 301 到 HTTPS。

生产 nginx 站点配置：服务器 `/etc/nginx/http.d/chaos-web.conf`，**仓库内留档在 `for-deploy/chaos-web.conf`**（改 conf 前先读 `for-deploy/README.md`）。

同域单入口，Nginx 统一分发：

- `/` → `frontend` 构建产物（SPA 使用 history 路由，**`try_files $uri $uri/ /index.html;` 已配置并生效**，可直接在 `for-deploy/chaos-web.conf` 的兜底 `location /` 核对；`/announcements` 等深层路由刷新、扫码直达 `/staff/xxx` 都依赖它，改动时勿删）
- `/api` → 反代到本机 FastAPI（:5000，后端所有接口统一挂 `/api` 前缀）；其中 `/api/kb/` 的反代必须为 SSE 追加 `proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`（与后端 `X-Accel-Buffering: no` 两个都要，否则流式变一次性返回）
- 兼容旧路径（勿删）：`/health` → 反代 FastAPI（外部监控/旧部署门禁在用）；`/announcement/uploads/` → 反代 FastAPI（历史公告正文内嵌的旧图片 URL，存量数据兼容）
- `/wiki/` → `wiki` 构建产物（VitePress 已按 `/wiki` base 打包）
- `/admin/` → `admin-frontend` 构建产物（pure-admin-thin，已按 `/admin/` base 打包）

**新增 `location` 前缀时不得与前端页面路由同名**：`location /staff` 会把 SPA 的 `/staff/:code` 一并反代走，页面再也进不去，而 dev 直连后端看不出问题。统一 `/api` 之后新模块已不需要单独加 `location`，正常不会再触发；真要加，前缀与页面路由错开（如曾考虑过的复数前缀）。`chaos-web.conf` 里 `location = /faction-beta { try_files /index.html =404; }` 就是历史上处理这类同名的补丁。

后端 Docker 部署时注意：`docker-compose.yml` 位于 `backend/` 下，但**构建上下文是项目根目录**（`context: ..`），因为 Dockerfile 里 `COPY backend/` 依赖该路径——移动文件时两者要一起改。

## for-deploy 留档目录

- `for-deploy/` 存放生产实际生效、但不属于任何子项目构建产物的配置留档（当前 `chaos-web.conf` = nginx 站点配置快照；同步方法与改 conf 前的注意事项见该目录 `README.md`）。
- **该目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据等一律不进；普通配置里如无必要也不要写外部 IP/端口。敏感文件（证书、`backend/.env`、生产库）只存在于服务器对应路径，不落仓库。

## 已知遗留 / 注意事项

- 后端 CORS 当前 `allow_origins=["*"]`（开发便利），生产收紧时需与同源部署方案一起评估。
- `backend/app/monitor.py` 中 `server-info` 的 `start_time` / `end_time` / `time_period` 参数是预留参数，当前实现未使用，不要误删（前端会传）。
- 智能客服（P0）遗留项见 `TODO.md`：真实玩家在线人数（mcstatus）、限流多 worker 共享存储、知识库自动定时任务（当前用 crontab）、检索效果看板等。
- **HTTPS 证书 2026-12-24 到期**（Let's Encrypt 通配符 `*.xt91tv.shop`，90 天一签）：到期未换证书 = **全站不可访问**。续期后替换 `/etc/nginx/ssl/` 下证书与私钥并 `nginx -s reload`，同时更新 `for-deploy/chaos-web.conf` 头部注释里的到期日期。
- 生产 Nginx 的 `/api/kb/` SSE 反代已按四件套配置（2026-09-21 起上线，2026-09-25 随 `/api` 前缀改造迁移）；生产改 nginx 时勿丢该 location。
