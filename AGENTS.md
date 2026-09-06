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

# 后台管理 (Vite + Element Plus, :9528)
cd admin-frontend
pnpm install
pnpm dev                  # 开发服务器，API 代理到后端 :5000
pnpm build                # 产物 dist/，部署到 /admin/
```

## API 契约规约

这是本项目最容易踩坑的部分，改接口前必读：

1. **响应包络**：所有接口返回 `{code, message, data}`，`code=0` 表示成功。前端 `axiosInstance` 响应拦截器已统一解包（直接返回 `data`），组件代码拿到的就是裸数据——**不要在前端组件里再判断 `code`**。
2. **字段命名**：数据库/后端内部用 snake_case，对外 JSON 用 camelCase（`publishTime` / `isPublished` / `readCount` / `createTime` / `updateTime`）。Pydantic 模型通过 `alias` + `populate_by_name=True` 映射（见 `backend/app/schemas.py`），新增字段必须同时补别名。
3. **契约参照实现**：`frontend/src/api/api.js` 是前后端契约的参照。**新增或修改后端接口时必须同步该文件**，保持两侧一致。后台管理前端 `admin-frontend/src/api/` 同步维护。
4. **时间格式**：统一存 ISO 字符串 `YYYY-MM-DDTHH:MM:SS`（SQLite 中为 `String(30)` 列，不用 datetime 类型）。
5. **布尔语义用 int**：如 `isPublished`，`0=草稿, 1=已发布`，不要改成 bool。
6. **监控接口**：`GET /monitor/server-info/{id}` 目前是 TCP 探测的最小实现（`online/offline` + 占位字段），响应结构被首页 `OnlineCounter` 组件依赖，扩展时不能破坏现有字段。

## 游戏服务器地址：单一数据源

- 游戏服务器地址**只**维护在 `backend/app/monitor.py` 的 `SERVERS` 注册表中。
- **禁止在前端硬编码服务器地址**；前端一律通过 `GET /monitor/servers` 获取（`mc-config.js` 里只保留监控接口所需的 `server.id`）。
- 新增/修改服务器 = 改 `SERVERS` 一个地方。

## 前端配置规约

- `frontend/src/config/mc-config.js` 的 `nodeEnv` 由 `import.meta.env.PROD` 自动决定（dev → 本地 5000，build → 同源相对路径），**不要改成手动切换**，也不要在别处硬编码 API 地址。
- 生产环境 API 走同源（`baseApiURL: ''`），依赖 Nginx 反代 `/announcement`、`/monitor`、`/health` 到本机 FastAPI（:5000）。
- QQ 群等站点信息集中在 `mc-config.js` 配置。
- 模板中引用的静态图片必须先 `import` 再绑定 `:src`（如 `Home.vue` 的 `bbs-*.png`、`video-bg.jpg`）；**禁止直接写 `/src/...` 绝对路径**——Vite build 不会打包该路径，生产环境会 404（dev 下看不出来）。

## Wiki 规约

- VitePress `base: '/wiki'` + `cleanUrls: true`。站内链接写相对路径（VitePress 自动加 base）；**外链必须带协议**（`http(s)://`），否则会被加上 `/wiki` 前缀。
- 内容分三大分区，新增页面放对应分区并在 `.vitepress/config.mts` 侧边栏登记：`for-new/`（萌新指南）、`management/`（服务器管理）、`develop/`（服务器建设）。
- 已知硬编码点：`wiki/index.md` hero 的「访问官网」按钮当前写死 IP 地址，绑定域名后需同步修改（文件内有注释标记）。

## Git 规约

- 远程：`git@github.com:ChaosSurvivalProject/server-website.git`，主分支 `main`。
- 提交信息使用 Conventional Commits 前缀（`feat` / `fix` / `refactor` 等，可带 scope 如 `feat(backend):`），描述用中文。

## 部署拓扑（生产）

同域单入口，Nginx 统一分发：

- `/` → `frontend` 构建产物（SPA 使用 history 路由，Nginx 需配置 `try_files $uri $uri/ /index.html;`，否则刷新 `/announcements` 等深层路由会 404）
- `/announcement`、`/monitor`、`/health` → 反代到本机 FastAPI（:5000）
- `/wiki/` → `wiki` 构建产物（VitePress 已按 `/wiki` base 打包）
- `/admin/` → `admin-frontend` 构建产物（pure-admin-thin，已按 `/admin/` base 打包）

后端 Docker 部署时注意：`docker-compose.yml` 位于 `backend/` 下，但**构建上下文是项目根目录**（`context: ..`），因为 Dockerfile 里 `COPY backend/` 依赖该路径——移动文件时两者要一起改。

## 已知遗留 / 注意事项

- 后端 CORS 当前 `allow_origins=["*"]`（开发便利），生产收紧时需与同源部署方案一起评估。
- `backend/app/monitor.py` 中 `server-info` 的 `start_time` / `end_time` / `time_period` 参数是预留参数，当前实现未使用，不要误删（前端会传）。
