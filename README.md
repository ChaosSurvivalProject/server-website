# 星穹旅驿 · 服务器网站

星穹旅驿 Minecraft 服务器的官方网站，单仓库（monorepo）包含三个子项目：

| 模块 | 说明 | 技术栈 |
|------|------|--------|
| `frontend/` | 官网前端（首页、公告） | Vue 3 + Vite + Vue Router + Axios + ECharts |
| `backend/` | 官网后端（公告管理、服务器状态） | FastAPI + SQLAlchemy (async) + SQLite (aiosqlite) + Pydantic v2 |
| `wiki/` | 服务器文档站 | VitePress |

## 项目结构

```
server-website/
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # axios 实例、接口封装、统一错误处理
│   │   ├── assets/              # 图片、字体等静态资源
│   │   ├── components/          # 通用组件（NavBar、OnlineCounter、Leaderboard、TrendChart 等）
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
│   │   ├── database.py          # SQLAlchemy 模型 & 异步引擎/会话
│   │   ├── schemas.py           # Pydantic 模型（camelCase 别名）
│   │   ├── crud.py              # 公告 CRUD 操作
│   │   └── monitor.py           # 服务器监控（地址注册表 + TCP 探测）
│   ├── run.py                   # uvicorn 启动脚本
│   ├── seed.py                  # 测试数据种子
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── data/                    # SQLite 数据库文件（gitignore）
├── wiki/                        # VitePress 文档站
│   ├── .vitepress/config.mts    # 站点配置（base: /wiki）
│   ├── for-new/                 # 萌新指南（进服教程、玩家条例、FAQ）
│   ├── management/              # 服务器管理（管理员条例）
│   ├── develop/                 # 服务器建设（发展路线、Issues）
│   ├── index.md                 # 首页（hero 布局）
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

## 后端 API

### 公告

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/announcement/page` | 分页查询公告（参数: page, pageSize, isPublished） |
| GET | `/announcement/detail/{id}` | 查询公告详情 |
| POST | `/announcement/addWatchCount` | 阅读量 +1（body: `{announcementId}`） |
| POST | `/announcement/create` | 创建公告（**需管理员**） |
| PUT | `/announcement/update/{id}` | 更新公告（部分更新，**需管理员**） |
| DELETE | `/announcement/delete/{id}` | 删除公告（**需管理员**） |
| POST | `/announcement/upload/image` | 上传富文本图片（multipart `file`，≤5MB，png/jpg/jpeg/gif/webp，**需管理员**；返回 `data.url` 相对路径，可直接写入公告内容） |
| GET | `/announcement/uploads/{...}` | 上传图片静态目录（按月份分目录存放） |

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/auth/captcha` | 获取注册用图形验证码（返回 `{captchaId, image}`，5 分钟有效、一次性） |
| POST | `/auth/register` | 注册（body: `{email, password, confirmPassword, captchaId, captchaCode}`，邮箱作为初始用户名，角色为普通用户） |
| POST | `/auth/login` | 登录（body: `{username, password}`，成功返回 `{token, username, role}`） |
| GET | `/auth/me` | 当前登录用户信息（Header: `Authorization: Bearer <token>`） |

- JWT 默认 24 小时有效，环境变量 `JWT_EXPIRE_HOURS` 可调；签名密钥取环境变量 `JWT_SECRET`，未设置时自动生成并持久化到数据目录。
- 系统管理员 `xqly-admin` 在后端首次启动时自动初始化，随机强密码写入数据目录 `admin_initial_password.txt`（仅首次初始化时写入，请妥善保管并及时删除）。

### 服务器监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/monitor/servers` | 游戏服务器地址列表（前端展示的唯一数据源） |
| GET | `/monitor/server-info/{serverId}` | 服务器在线状态（TCP 探测，供首页在线状态组件） |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

**约定**

- 响应统一为 `{code, message, data}` 结构，`code=0` 表示成功。
- 公告字段使用 camelCase（`publishTime` / `isPublished` / `readCount` / `createTime` / `updateTime`），由 Pydantic 字段别名映射。
- 游戏服务器地址统一由后端维护（`backend/app/monitor.py` 的 `SERVERS` 注册表），前端不再硬编码；新增或修改服务器地址只需改这个文件。
- 管理员接口使用 `Authorization: Bearer <JWT>` 鉴权：无 token 返回 401，普通用户返回 403。

### 数据库

使用 SQLite：

- 默认路径：`backend/data/announcements.db`（启动时自动建表）
- 可通过环境变量 `ANNOUNCEMENT_DB` 自定义

公告内容为富文本编辑器（wangEditor）产出的 HTML，入库前由后端 `nh3` 白名单消毒（仅放行常用标签 + `style` 内联样式）。

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
| `/login` | AuthView（登录） | 登录页（用户名/邮箱 + 密码） |
| `/register` | AuthView（注册） | 注册页（邮箱 + 密码 + 确认密码 + 图形验证码） |

### 关键组件

- `NavBar` — 顶部导航栏
- `OnlineCounter` — 服务器在线状态（轮询 `/monitor/server-info/{id}`）
- `Leaderboard` / `TrendChart` — 排行榜与趋势图（ECharts）
- `ContentCard` / `ImageCarousel` / `SectionNav` / `CopyButton` / `BackToTop` / `Modal` — 展示与交互组件

### API 层（`src/api/`）

- `axiosInstance.js` — axios 实例，baseURL 来自环境变量 `VITE_BASE_API_URL`（经 `mc-config.js` 统一读取）；响应拦截器统一解包 `{code, message, data}`，失败时弹出错误提示；请求拦截器自动携带 JWT，401 时清除登录态并跳转 `/login`
- `api.js` — 接口封装：`authAPI` / `announcementAPI` / `serverMonitorAPI` / `serverConfigAPI`
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

环境变量在构建期静态替换，修改后需重启 dev server 或重新构建才生效。

## 生产部署

前后端同域部署，由 Nginx 统一入口：

- `frontend` 构建产物（`npm run build` → `dist/`）作为静态站点托管
- `/announcement`、`/monitor`、`/auth`、`/health` 等 API 路径反向代理到本机 FastAPI（5000 端口）
- `wiki` 构建产物挂在 `/wiki/` 路径下（VitePress `base: '/wiki'`）
- `admin-frontend` 构建产物挂在 `/admin/` 路径下（pure-admin-thin，`base: '/admin/'`）

## 后台管理（admin-frontend）

独立的后台管理前端，基于 [pure-admin-thin](https://github.com/pure-admin/pure-admin-thin)（Vue 3 + TypeScript + Element Plus + Pinia + Vite + TailwindCSS），部署在 `/admin/` 路径下。

### 模块与页面

| 路径 | 页面 | 说明 |
|------|------|------|
| `/admin/login` | 登录页 | 管理员 JWT 登录 |
| `/admin/announcement/list` | 公告管理 | 公告列表（分页、新建/编辑/删除） |
| `/admin/announcement/edit` | 公告编辑 | 新建或编辑公告（标题、内容、发布人、发布时间、状态） |
| `/admin/server/list` | 服务器地址管理 | 服务器列表（新建/编辑/删除/设为主） |
| `/admin/server/edit` | 服务器编辑 | 新建或编辑服务器（名称、地址、端口、是否主服务器） |

### 开发命令

```bash
cd admin-frontend
pnpm dev      # 开发服务器（:9528，API 代理到后端 :5000）
pnpm build    # 构建到 dist/
```

### 部署

- 开发模式：Vite dev server（:9528），API 通过 `vite.config.ts` 中的 proxy 转发到后端 FastAPI（:5000）
- 生产模式：`pnpm build` → `dist/`，由 Nginx 将 `/admin/` 路径反向代理到 `dist/` 目录
- 管理员入口：主站已登录管理员点击头像下拉菜单 → 「后台管理」（仅管理员角色可见）
