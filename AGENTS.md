# AGENTS.md

星穹旅驿 Minecraft 服务器官方网站（frontend + backend + wiki 三合一仓库）。整体架构与目录树见 [README.md](README.md)，后端接口清单见 [docs/api-reference.md](docs/api-reference.md)；**本文件只记录项目特有的规约与坑**，通用工程惯例不在此重复。各规约小节的完整原文已下沉 `docs/agents/`（2026-11-07 文档重构），本文件只留硬性禁区速览——动代码前先读对应专题文档。

## 仓库结构要点

- 四个子项目相互独立，各自持有 `package.json` / `node_modules`，**没有根级 workspace**，仓库也没有根级 `package.json`——所有安装、构建、开发命令必须在对应子目录（`frontend/`、`backend/`、`wiki/`、`admin-frontend/`）内执行；不要提交 `node_modules/`、`dist/`、`*.db`、`backend/data/`、`wiki/.vitepress/cache|dist/`（见 `.gitignore`）。

## 常用命令

```bash
cd backend && pip install -r requirements.txt && python3 run.py    # 后端 (FastAPI, :5000)，uvicorn --reload 开发模式；python3 seed.py 写入示例公告数据
cd frontend && npm install && npm run dev                          # 前端 (Vite, :5173)；npm run build 产物 dist/（gitignore）
cd wiki && npm install && npm run dev                              # Wiki (VitePress)；npm run build 产物 .vitepress/dist/
cd admin-frontend && pnpm install && pnpm dev                      # 后台管理 (Vite + Element Plus)，dev 端口取 .env.development 的 VITE_PORT（当前 3005，覆盖 .env 的 8848）；pnpm build 产物 dist/ 部署到 /admin/
```

## API 契约规约

完整规约见 [docs/agents/api-conventions.md](docs/agents/api-conventions.md)。硬性禁区：接口统一挂 `/api` 前缀；响应包络 `{code, message, data}`（`code=0` 成功，前端组件不得再判 `code`；`POST /api/kb/chat` SSE 是全项目唯一包络例外）；DB snake_case / 对外 JSON camelCase（新增字段必须同步补 Pydantic alias）；**新增或修改后端接口必须同步契约参照 `frontend/src/api/api.js` 与 `admin-frontend/src/api/`**；时间统一存北京时间 naive ISO `YYYY-MM-DDTHH:MM:SS`；布尔语义用 int（`isPublished` 0=草稿/1=已发布）；上传 `FormData` 必须显式加 `Content-Type: multipart/form-data`（否则 422）。

## 知识库 / 智能客服规约

完整规约见 [docs/agents/kb.md](docs/agents/kb.md)。硬性禁区：wiki 是知识库单一数据源（先改 wiki，再跑 `backend/kb_sync.py`）；索引热更新是设计点（**服务端不需重启**，别改成"重启生效"）；限流状态在进程内（多 worker 必须换共享存储）；流式渲染必须复用 `frontend/src/utils/markdown.js` 管线。

## 员工名片模块规约

完整规约见 [docs/agents/staff.md](docs/agents/staff.md)。硬性禁区：公开接口不下发完整 `staffCode`，「导出名单 CSV」是唯一豁免点（**勿当漏洞"修掉"**）；过期判定只看 `valid_to`（回写共用 `expire_due()`）；`renew` 必须能救回过期记录；二维码 URL 由后端 `STAFF_PUBLIC_BASE_URL` 单一来源拼接、**禁止硬编码 `version=`**；名片出图必须用 `html2canvas-pro`（勿换回原版 `html2canvas`）。

## 社区（论坛）模块规约

完整规约见 [docs/agents/forum.md](docs/agents/forum.md)。硬性禁区：`forum_articles.status` 只能经 `_set_article_status()` 改（标签 `use_count` 只挂这一个转移点）；连接池必须是 `NullPool`（**不要改回 `StaticPool`**）；计数一律原子 SQL、关系切换统一走 `_toggle_relation()`（禁止 check-then-act 与 read-modify-write）；评论正文纯文本渲染、绝不走 Markdown 管线；新增组件一律独立 `.vue` SFC（字符串 `template` 本项目不渲染）；「跳登录页」`goLogin()` 与「是否已登录」不得同名混用；作者删帖进回收站（30 天保留期唯一权威 `deleted_at`）。

## 站内信模块规约

完整规约见 [docs/agents/messages.md](docs/agents/messages.md)。硬性禁区：前台展示叫「消息中心」但模块/接口/表名仍是站内信（勿改名）；点赞通知只在 `forum.py` 两个 toggle 点触发、内容是快照不是引用；定向消息的已读/删除仅接收者本人可操作。

## 游戏服务器地址：单一数据源

DB `servers` 表是唯一权威（内存 `SERVERS` 只是读缓存）。硬性禁区：**禁止在前端硬编码服务器地址**，前端一律经 `GET /api/monitor/servers` 获取；新增/修改走后台管理页或 admin 接口，不要再改代码里的注册表。详见 [docs/agents/deployment.md](docs/agents/deployment.md)。

## 后台管理菜单规约（admin-frontend）

完整规约见 [docs/agents/admin-menu.md](docs/agents/admin-menu.md)。硬性禁区：**新增页面挂到对应模块的 `children` 下，不要新增一级菜单**；每个模块记录必须写 `redirect`（`formatTwoStageRoutes()` 会拍平三级及以上路由）；单页模块记得 `meta.showParent = true`。

## 前端配置规约

完整规约见 [docs/agents/frontend-config.md](docs/agents/frontend-config.md)。硬性禁区：站点配置一律走 Vite 环境变量并经 `mc-config.js` 读取（三个 `.env` 文件随仓库提交，**禁止组件直读 `import.meta.env` 或硬编码站点值**）；模板静态图片必须先 `import` 再绑 `:src`，**禁止写 `/src/...` 绝对路径**（生产 404，dev 看不出来）。

## Wiki 规约

完整规约见 [docs/agents/frontend-config.md](docs/agents/frontend-config.md)。要点：VitePress `base: '/wiki'`，站内链接写相对路径、外链必须带协议；新增页面放三大分区（`for-new/` / `management/` / `develop/`）并在 `.vitepress/config.mts` 侧边栏登记；官网外链统一 `https://xqly.xt91tv.shop`（勿写死 IP 或旧 `:23333` 端口）。

## Git 规约

远程 `git@github.com:ChaosSurvivalProject/server-website.git`，主分支 `main`；提交信息使用 Conventional Commits 前缀（`feat` / `fix` / `refactor` 等，可带 scope 如 `feat(backend):`），描述用中文。

## 文档归档口径

完整规约见 [docs/agents/frontend-config.md](docs/agents/frontend-config.md)。要点：`TODO.md` 只留未完成项，收口清单整段搬 `docs/归档/已完成清单.md` 并留一行链接；归档只搬清单本身，不要往归档文件新增规约、不静默改写历史记录。

## 部署拓扑（生产）

完整规约见 [docs/agents/deployment.md](docs/agents/deployment.md)。硬性红线：1panel 面板改站点设置会重新生成 nginx conf、丢手工补的 `try_files` 兜底与 `include proxy/*.conf`（改完回服务器核对）；新增 `location` 前缀不得与前端页面路由同名；前端产物本机构建后投放，**服务器上不跑 Vite**（生产机 OOM）；根 compose `docker compose up -d --build`（任何 compose/Dockerfile 改动都要重建）。

### 统一前端容器（web 服务，本地/自包含用）

生产不用 web 容器；`web/nginx.conf` 与 `for-deploy/xqly-app.conf` 是同一套路由规则的两份载体，**改其一必须同步另一份**（SSE 四件套、SPA fallback、legacy location 三处不能分叉）。

### 生产定时任务（镜像内 cron）

三条任务已进后端镜像（`backend/crontab` → `/etc/cron.d/xqly-jobs`：0 3 kb_sync --incremental、0 4 staff_expire、0 5 forum_purge，均空跑安全）；**cron 不继承容器 environment**，业务路径必须写进 crontab 且与 docker-compose.yml 的 environment 同步；`CRON_ENABLED=0` 可关闭。

## for-deploy 留档目录

生产实际生效的配置快照目录（与线上字节一致，可 `md5sum` 比对，改完回拷留档）；**随公开仓库提交，禁止放任何敏感信息**——SSL 证书/私钥、API Key、密码、生产数据库数据等一律不进。

## 已知遗留 / 注意事项

完整清单见 [docs/agents/deployment.md](docs/agents/deployment.md) 与 [TODO.md](TODO.md)。硬性提醒：**HTTPS 证书 2026-12-24 到期**（Let's Encrypt 通配符，到期未换 = 全站不可访问）；`backend/app/monitor.py` 的 `start_time` / `end_time` / `time_period` 是预留参数（前端会传），不要误删。
