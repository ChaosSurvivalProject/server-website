# 部署拓扑与运维规约（生产）

> 本文是 [AGENTS.md](../../AGENTS.md)「部署拓扑（生产）」（含「统一前端容器」「生产定时任务」两个子节）「for-deploy 留档目录」「已知遗留 / 注意事项」的完整原文（2026-11-07 文档重构时下沉，内容未改动）；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

## 部署拓扑（生产）

**生产对外地址：`https://xqly.xt91tv.shop`**（2026-10-03 换服务器后启用，标准 443）。旧站是裸机 nginx + NAT 外部 23333 → 内部 80 且 nginx 在 80 上直接跑 SSL，**那套拓扑已废弃**；现在由 1panel 托管，nginx 是 1panel 的 OpenResty 容器（**host 网络**，监听 80/443），证书用 1panel「SSL」里导入的通配符证书下发给站点。

- 仓库路径 `/opt/xqly-website`；后端容器 `xqly-website-backend`（`docker compose` 定义在仓库**根目录** `docker-compose.yml`，2026-10-31 从 `backend/` 迁出，**只绑 `127.0.0.1:5000`**——发布到 `0.0.0.0` 会被 Docker 的 iptables 规则绕过 ufw 直接把 API 暴露到公网）。同一 compose 的 `web` 服务（统一前端 nginx 容器 `xqly-website-web`，生产绑 `127.0.0.1:8090`、测试绑 `0.0.0.0:8090`）**生产也使用**：镜像由 GitHub Actions 构建并推 GHCR，1panel/OpenResty 按域名反代到该容器。
- 1panel 仍是站点入口（TLS/443）；生产将前端请求反代到 web 容器 `127.0.0.1:8090`（前端由 web 镜像提供，不再投放到站点根目录），`/api` 等接口 location 仍按 `for-deploy/xqly-app.conf` 维护。
- **cookie/凭据类文件只在服务器上**：`backend/.env`（已 gitignore，含 API Key）以只读卷挂进容器（`./backend/.env:/app/backend/.env:ro`），wiki 源码以 `./wiki:/app/wiki:ro` 挂入供 `kb_sync.py` 读取（`KB_WIKI_DIR=/app/wiki`；compose 里已显式注入该环境变量，防止本地 `.env` 里按宿主机路径写的 `KB_WIKI_DIR=../wiki` 污染容器）。

**⚠️ 1panel 的「静态网站」模板不生成 `try_files` 兜底、也不生成 `include proxy/*.conf`**，这两样是上线时手工补进 `/opt/1panel/www/conf.d/xqly.xt91tv.shop.conf` 的。**在面板里改动该站点的网站设置会重新生成这个文件，手工补的东西会丢**（症状：深层路由 404 + `/api` 全部 502）——改完必须回服务器核对 `grep -n 'proxy/\*\.conf'`。自定义 location 全部放在 `/opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf`。

生产 nginx 配置留档：`for-deploy/xqly.xt91tv.shop.conf`（面板生成的 server 块，含那行 `include`）+ `for-deploy/xqly-app.conf`（手工维护的应用 location），**与线上字节一致**，改 conf 前先读 `for-deploy/README.md`。

同域单入口，Nginx 统一分发：

- `/` → `frontend` 构建产物（SPA 使用 history 路由，**`try_files $uri $uri/ /index.html;` 由 `xqly-app.conf` 提供**；`/announcements` 等深层路由刷新、扫码直达 `/staff/xxx`、`/team`、`/forum/...` 都依赖它，改动时勿删）
- `/api` → 反代到本机 FastAPI（`127.0.0.1:5000`，后端所有接口统一挂 `/api` 前缀）；其中 `/api/kb/` 的反代必须为 SSE 追加 `proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`（与后端 `X-Accel-Buffering: no` 两个都要，否则流式变一次性返回）
- 兼容旧路径（勿删）：`/health` → 反代 FastAPI（外部监控/旧部署门禁在用）；`/announcement/uploads/` → 反代 FastAPI（历史公告正文内嵌的旧图片 URL，存量数据兼容）
- `/wiki/` → `wiki` 构建产物（VitePress 已按 `/wiki` base 打包，cleanUrls 靠 `try_files $uri $uri.html $uri/ =404`）
- `/admin/` → `admin-frontend` 构建产物（pure-admin-thin，已按 `/admin/` base 打包）

**新增 `location` 前缀时不得与前端页面路由同名**：`location /staff` 会把 SPA 的 `/staff/:code` 一并反代走，页面再也进不去，而 dev 直连后端看不出问题。统一 `/api` 之后新模块已不需要单独加 `location`，正常不会再触发；真要加，前缀与页面路由错开（如曾考虑过的复数前缀）。旧裸机 conf 里 `location = /faction-beta { try_files /index.html =404; }` 就是历史上处理这类同名的补丁，新版 `xqly-app.conf` 已不再需要它。

**服务器上不跑 Vite / 不在服务器 build**：生产为香港 2C2G/30G，前端 Vite 构建峰值会 OOM。镜像由 GitHub Actions（`.github/workflows/release-images.yml`）在 Release 时构建并推送到 GHCR；服务器只拉取运行：`docker compose pull && docker compose up -d --no-build`。测试环境需要本机构建时用 `docker compose up -d --build`，并把 web 绑 `0.0.0.0`（根目录 `.env` 的 `WEB_BIND_IP=0.0.0.0`）。

后端 Docker 部署注意：`docker-compose.yml` 位于**仓库根目录**（2026-10-31 从 `backend/` 迁出），构建上下文即根目录（`context: .`），backend/Dockerfile 里必须写 `COPY backend/requirements.txt .`（写 `requirements.txt` 会 `not found`，2026-10-03 修过）；根目录 `.dockerignore` 负责把 `node_modules`/`dist`/`.git` 挡在 context 之外。**任何 `Dockerfile` / 依赖改动都要发 Release 让 CI 重建镜像（本地联调才用 `docker compose up -d --build`），生产走 `pull + up --no-build`**。

### 镜像发布（GitHub Actions → GHCR）

- `release-images.yml` 仅在 GitHub Release `published` 时触发，构建并推送 `ghcr.io/chaossurvivalproject/server-website-{backend,web}`；正式版额外打 `latest`，预发行版只打 Release tag。
- 服务器部署（不 build）：`IMAGE_TAG=v1.2.3 docker compose pull && IMAGE_TAG=v1.2.3 docker compose up -d --no-build`（也可在根 `.env` 固定 `IMAGE_TAG`）。首次拉取私有包需 `docker login ghcr.io`。
- `docker-compose.yml` 同时保留 `build:` 与 `image:`：本地 `up --build` 会构建并按 image 名打 tag；生产必须 `pull + up --no-build`，否则 pull 失败时会回退本地构建（2C2G 上 Vite 必 OOM）。

### 统一前端容器（web 服务）

根 compose 的 `xqly-website-web` 服务由 `web/Dockerfile`（多阶段：三个前端各自 node 构建产物）+ `web/nginx.conf`（路由规则）组成，产物收进**一个 nginx 容器** `xqly-website-web`：`/` 主站、`/admin/` 后台、`/wiki/` 文档、`/api` 与 `/health`、`/announcement/uploads/` 反代 `xqly-website-backend:5000`，宿主机只绑 `127.0.0.1:8090`（8080 已被本机其他服务占用）。要点：

- **`web/nginx.conf` 与 `for-deploy/xqly-app.conf` 是同一套路由规则的两份载体**，改其一必须同步另一份（SSE 四件套、SPA fallback、legacy location 三处不能分叉）。
- **生产使用 web 容器**：生产 web 只绑 `127.0.0.1:8090`，由 1panel/OpenResty 按域名反代；镜像由 CI 构建，绝不在服务器跑 Vite（2C2G 会 OOM）。
- **2026-10-31 容器名从 `announcement-backend` 改为 `xqly-website-backend`**，2026-11-01 起定时任务已改为**镜像内 cron**（`backend/crontab` + `backend/docker-entrypoint.sh`），不再依赖宿主机 `docker exec` + 容器名，因此该改名不会再让定时任务失效。生产服务器部署本仓库时要在 `/opt/xqly-website` 下 `docker compose pull && docker compose up -d --no-build`（**不要带 `--build`**；旧命令 `cd backend && docker compose up` 已失效）；宿主机上遗留的三条旧 crontab 条目需按 `for-deploy/README.md`「改定时任务」清空。数据卷路径已同步改为 `./backend/data` 与 `./backend/.env`——与旧 compose（在 `backend/` 下解析 `./data` / `./.env`）指向的**绝对路径相同**，生产直接 up 不会丢库。
- 生产 `.env` 的 `KB_WIKI_DIR` 应写 `/app/wiki`；compose 已显式注入 `KB_WIKI_DIR=/app/wiki` 环境变量兜底（环境变量优先于 `.env` 文件值）。

### 生产定时任务（镜像内 cron）

**2026-11-01 起三条任务已进后端镜像**，宿主机 root crontab 退役（原因：宿主机条目随容器改名静默失效——2026-10-31 容器名 `announcement-backend` → `xqly-website-backend` 即踩过，任务静默不跑且无报错）：

- 任务定义 `backend/crontab` → 构建期落到镜像 `/etc/cron.d/xqly-jobs`；入口脚本 `backend/docker-entrypoint.sh` 先起 `cron` 再 `exec python backend/run.py`；日志进容器 stdout（`docker logs xqly-website-backend`）。
- 三条任务与时刻不变：`0 3` kb_sync `--incremental`（wiki 按 MD5 增量入库，自增 `index_version`，后端免重启）、`0 4` staff_expire（`valid_to` 权威 + 查询时懒更新兜底）、`0 5` forum_purge（`deleted_at` 权威 + 恢复接口自校验 + 列表自过滤）。**三条都是 0 变更空跑安全，漏跑不影响正确性**（只影响时效），该口径未变。
- **两个必守口径**（改 `backend/crontab` 前必读）：① `/etc/cron.d` 的行是 6 段 `分 时 日 月 周 用户名 命令`，漏用户名会被当成 `user=cd` 而静默不执行；② **cron 不继承容器 environment，也不看 `TZ` 环境变量**——业务路径（`ANNOUNCEMENT_DB` / `ANNOUNCEMENT_UPLOAD_DIR` / `KB_WIKI_DIR`）必须写进 crontab 且与 `docker-compose.yml` 的 `environment` 同步（否则任务读写 `/app/backend/data`（镜像内路径）而非挂载卷，表现为「跑完什么也没变」）；调度时区看镜像的 `/etc/localtime`（Dockerfile 已设 `Asia/Shanghai`）。
- `CRON_ENABLED=0` 可关闭镜像内定时任务（本地只跑 API / 联调时用）。
- **迁移注意**：新镜像上线后，生产上旧的宿主机 crontab 三条 `docker exec` 条目必须清空，否则与镜像内 cron 重复执行（三条都幂等，重复跑不会写坏数据但会白跑）。迁移与验证命令见 `for-deploy/README.md`「改定时任务」。
- `for-deploy/crontab` 降级为历史快照（**已废弃**），不再是与线上字节一致的现行留档。

## for-deploy 留档目录

- `for-deploy/` 存放生产实际生效、但不属于任何子项目构建产物的配置留档（当前三个：`xqly.xt91tv.shop.conf` = 1panel 站点配置快照、`xqly-app.conf` = 应用 location 快照、`crontab` = root crontab 快照；均为**与生产字节一致**的快照，可 `md5sum` 比对，改完后须回拷留档；同步方法与改前注意事项见该目录 `README.md`）。
- **该目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据等一律不进；普通配置里如无必要也不要写外部 IP/端口。敏感文件（证书、`backend/.env`、生产库）只存在于服务器对应路径，不落仓库。

## 已知遗留 / 注意事项

- 后端 CORS 当前 `allow_origins=["*"]`（开发便利），生产收紧时需与同源部署方案一起评估。
- `backend/app/monitor.py` 中 `server-info` 的 `start_time` / `end_time` / `time_period` 参数是预留参数，当前实现未使用，不要误删（前端会传）。
- 智能客服（P0）遗留项见 `TODO.md`：真实玩家在线人数（mcstatus）、限流多 worker 共享存储、知识库自动定时任务（当前用 crontab）、检索效果看板等。
- **HTTPS 证书 2026-12-24 到期**（Let's Encrypt 通配符 `*.xt91tv.shop`，90 天一签）：到期未换证书 = **全站不可访问**。现在证书由 1panel「SSL」管理并下发给站点 `/opt/1panel/www/sites/xqly.xt91tv.shop/ssl/`，续期后在面板里替换该证书再重载 OpenResty 即可；**旧的裸机路径 `/etc/nginx/ssl/` 已不存在**。
- 生产 Nginx 的 `/api/kb/` SSE 反代已按四件套配置，现位于 `for-deploy/xqly-app.conf`（1panel 站点通过 `include .../proxy/*.conf` 引入）；生产改 nginx 时勿丢该 location。
