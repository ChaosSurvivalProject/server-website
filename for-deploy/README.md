# for-deploy — 生产部署配置留档

> ⚠️ **本目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据一律不进；普通配置里如无必要也不要写外部 IP/端口。留档前先自查一遍文件内容。

本目录存放生产服务器上实际生效、但不属于任何子项目构建产物的配置文件快照，作为仓库内的留档参照。

> **2026-11 起镜像化部署**：生产镜像由 GitHub Actions（`.github/workflows/release-images.yml`）在 Release 时构建并托管在 GHCR：`ghcr.io/chaossurvivalproject/server-website-backend` / `-web`。服务器只执行 `docker compose pull && docker compose up -d --no-build`，**不在服务器 build、不跑 Vite**（香港 2C2G 跑前端构建会 OOM）。下文「前端产物从哪来」的静态投放方案降级为历史 / 备用说明；当前以 GHCR 镜像为准。

## 生产拓扑（2026-10-03 起：1panel + Docker）

换服务器后整套部署方式变了——旧站是裸机 nginx（`/etc/nginx/http.d/chaos-web.conf`，NAT 外部 23333 → 内部 80 且 nginx 在 80 上直接跑 SSL）。**现在是标准 443 的 1panel 托管**：

| 层 | 位置 |
| --- | --- |
| 面板 | 1panel v2，OpenResty 容器 `1Panel-openresty-TV94`（**host 网络**，监听 80/443） |
| 站点 | 1panel「静态网站」，域名 `xqly.xt91tv.shop`，站点根 `/opt/1panel/www/sites/xqly.xt91tv.shop/index` |
| 站点 conf | `/opt/1panel/www/conf.d/xqly.xt91tv.shop.conf`（1panel 生成，宿主机路径；容器内是 `/usr/local/openresty/nginx/conf/conf.d/`） |
| 自定义 location | `/opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf` |
| 后端 | Docker 容器 `xqly-website-backend`，只绑 `127.0.0.1:5000`；定义在仓库根目录 `docker-compose.yml`（2026-10-31 从 `backend/` 迁出，同时新增 `web` 统一前端服务，见下文） |
| 仓库 | `/opt/xqly-website`（前端三套产物已构建投放，见下） |
| 证书 | 1panel「SSL」里导入的通配符证书 `*.xt91tv.shop`（Let's Encrypt，**2026-12-24 到期**），由面板下发给站点 `ssl/` 目录 |

## 文件清单

| 文件 | 生产位置 | 说明 |
| --- | --- | --- |
| `xqly.xt91tv.shop.conf` | `/opt/1panel/www/conf.d/xqly.xt91tv.shop.conf` | 1panel 生成的站点 server 块。**除末尾那行 `include .../proxy/*.conf;` 外全部由面板生成**，不要把它当成手工配置来维护 |
| `xqly-app.conf` | `/opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf` | 手工维护的应用 location：静态资源缓存 + `/api/kb/` SSE 四件套 + `/api` 反代 + legacy 兼容路径 + `/admin`、`/wiki` 跳转 + `/wiki/` cleanUrls + **SPA fallback** |
| `crontab` | root 用户 crontab（`crontab -l`） | **已废弃（2026-11-01 起）**：三条业务任务（`kb_sync.py --incremental` 03:00 / `staff_expire.py` 04:00 / `forum_purge.py` 05:00）已改为**后端镜像内定时任务**（`backend/crontab` → 镜像 `/etc/cron.d/xqly-jobs`，由 `backend/docker-entrypoint.sh` 拉起 cron）。本文件仅作为迁移前的历史快照，生产部署新版镜像后应**清空**这些条目（见下方「改定时任务」）。原因：宿主机条目随容器改名静默失效（2026-10-31 已踩） |

## 与生产保持同步

生产配置的权威来源是服务器本体；本目录是**留档快照**，改完必须回拷。留档后用 `md5sum` 比对，确保字节一致：

```bash
ssh root@<生产机> 'md5sum /opt/1panel/www/conf.d/xqly.xt91tv.shop.conf \
                          /opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf'
md5sum for-deploy/xqly.xt91tv.shop.conf for-deploy/xqly-app.conf   # 两侧必须一致
```

改 `xqly-app.conf` 的流程（openresty 在容器里，`nginx -t` / `reload` 都要 `docker exec`）：

```bash
scp for-deploy/xqly-app.conf root@<生产机>:/opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf
ssh root@<生产机> 'docker exec 1Panel-openresty-TV94 nginx -t && docker exec 1Panel-openresty-TV94 nginx -s reload'
```

> ⚠️ **`include` 行会丢**：`xqly.xt91tv.shop.conf` 由 1panel 生成，1panel 的「静态网站」模板**既不生成 `try_files` 兜底、也不生成 `include proxy/*.conf`**，这两样都是上线时手工补的。在面板里改动该站点的网站设置（域名/端口/证书/HTTPS 开关等）会重新生成该文件，**`include` 行随之丢失**，站点会立刻表现为「深层路由 404 + `/api` 全部 502」。改完站点设置后必须回服务器核对：
> ```bash
> grep -n 'proxy/\*\.conf' /opt/1panel/www/conf.d/xqly.xt91tv.shop.conf || echo 'include 丢了，需要补回'
> # 补回：在 server 块末尾（最后一个 } 之前）加
> #   include /www/sites/xqly.xt91tv.shop/proxy/*.conf;
> ```

## 前端产物从哪来

服务器上**没有也不会**跑 Vite（生产为香港 2C2G/30G，Vite 构建峰值会 OOM）；前端与后端都改由 GitHub Actions 构建 GHCR 镜像，服务器只 pull 运行。以下静态投放表为历史 / 备用方案：

| 子项目 | 构建命令（本机） | 投放位置 |
| --- | --- | --- |
| `frontend` | `npm run build` | `/opt/1panel/www/sites/xqly.xt91tv.shop/index/` |
| `admin-frontend` | `pnpm install && pnpm build`（Windows 下必须走 `pnpm`，`build` 脚本用了 `NODE_OPTIONS=…` 的 Unix 写法，靠 pnpm 的 `shell-emulator` 才能跑） | 同上 `index/admin/` |
| `wiki` | `npm run build` | 同上 `index/wiki/` |

站点根目录里 `404.html` 是 1panel 建的，`admin/`、`wiki/` 是子目录——三者与 SPA 的 `index.html` 共存，靠 `xqly-app.conf` 里的 location 分流。

## 生产/自包含部署（根 docker-compose.yml 的 web 服务）

仓库根目录 `docker-compose.yml` 定义了 `xqly-website-web` 服务（`web/Dockerfile` + `web/nginx.conf`）：三个前端在镜像内多阶段构建、收进**一个 nginx 容器**（`xqly-website-web`），按与 `xqly-app.conf` 相同的规则分发 `/` 主站、`/admin/`、`/wiki/`，并反代 `/api` 到 `xqly-website-backend:5000`。生产由 1panel/OpenResty 反代 `127.0.0.1:8090`；测试环境绑 `0.0.0.0:8090` 便于局域网访问。镜像统一由 CI 构建后 `pull` 运行。

两点注意：

- **生产前端也走 `web` 镜像（GHCR，CI 构建）**，服务器不跑 Vite；生产 `web` 只绑 `127.0.0.1:8090`，由 1panel/OpenResty 反代。测试环境才把 web 绑 `0.0.0.0:8090` 便于局域网访问。
- `web/nginx.conf` 与 `for-deploy/xqly-app.conf` 是**同一套路由规则的两份载体**，改其一须同步另一份（SSE 四件套、SPA fallback、legacy location 三处尤其不能分叉）。

## 注意（改 conf 前必读）

- **SPA fallback 勿删**：`location / { try_files $uri $uri/ /index.html; }` 撑住 history 路由（`/announcements`、`/forum/...`、扫码直达 `/staff/{身份码}`、`/team`）。1panel 模板不生成它，缺了整个前端只有首页能开。
- `/health` 与 `/announcement/uploads/` 两个 legacy location **勿删**：前者是外部监控/旧部署门禁在用，后者服务历史公告正文内嵌的旧图片 URL（存量内容兼容）。
- `/api/kb/` 的 SSE 四件套（`proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`）不能丢，否则智能客服流式变一次性返回（与后端 `X-Accel-Buffering: no` 两个都要）。
- 站点 conf 里已有 `ssl_session_cache shared:SSL:10m;`，是 1panel 生成的，不要重复声明同名 zone（`nginx -t` 会失败）。
- 服务器本地验证 TLS/路由不要用公网 IP 回环绕 NAT，直接指定解析：
  ```bash
  curl -sI --resolve xqly.xt91tv.shop:443:127.0.0.1 https://xqly.xt91tv.shop/
  ```

## 改定时任务（cron）

**2026-11-01 起，定时任务已进后端镜像**，不再挂宿主机 root crontab：

- 任务定义：`backend/crontab`（构建时落到镜像内 `/etc/cron.d/xqly-jobs`）
- 启动方式：`backend/docker-entrypoint.sh` 先起 `cron` 再 `exec python backend/run.py`
- 日志：追加到 `/proc/1/fd/1`，即 `docker logs xqly-website-backend`
- 关闭开关：容器环境变量 `CRON_ENABLED=0`（本地只跑 API 时用）

改调度时间 / 加新任务 = 改 `backend/crontab` → 提交并发布 Release（由 GitHub Actions 重建 backend 镜像）→ 服务器 `docker compose pull && docker compose up -d --no-build`。

⚠️ 两个必守口径（改之前先读 `backend/crontab` 顶部注释）：

1. **`/etc/cron.d` 的行是 6 段**：`分 时 日 月 周 用户名 命令`，漏写用户名会被当成 `user=cd` 而静默不执行。
2. **cron 不继承容器 environment**，也不看 `TZ` 环境变量：
   - 业务路径（`ANNOUNCEMENT_DB` / `ANNOUNCEMENT_UPLOAD_DIR` / `KB_WIKI_DIR`）必须写进 crontab 文件，**并与 `docker-compose.yml` 的 `environment` 同步**，否则任务读写 `/app/backend/data`（镜像内路径，非挂载卷），表现为「跑完什么也没变」；
   - 调度时区看镜像的 `/etc/localtime`（Dockerfile 已设 `Asia/Shanghai`），所以 `0 3` 就是北京时间 03:00。

### 从宿主机 crontab 迁移（一次性）

生产部署带新 entrypoint 的镜像后，宿主机那三条 `docker exec` 条目必须**删掉**，否则与镜像内 cron **重复执行**（三条任务都是幂等空跑安全的，重复跑不会写坏数据，但会白跑并产生重复日志）：

```bash
ssh root@<生产机> 'crontab -l > /root/crontab.bak-$(date +%Y%m%d)'   # ① 先备份
ssh root@<生产机> 'crontab -r'                                       # ② 清空（或只删三条 docker exec 行）
ssh root@<生产机> 'crontab -l'                                       # ③ 确认已空
```

然后确认镜像内 cron 已生效：

```bash
docker logs xqly-website-backend | grep '[entrypoint] cron started'
docker exec xqly-website-backend crontab -l            # 应报 /etc/cron.d 无关，仅验证容器内可执行
docker exec xqly-website-backend ls -l /etc/cron.d/xqly-jobs   # 属主 root、权限 0644
```

按 cron 的实际调用方式实跑一次任务本身（验证路径与 env 口径正确）：

```bash
docker exec xqly-website-backend python backend/kb_sync.py --check
docker exec xqly-website-backend python backend/staff_expire.py --dry-run
docker exec xqly-website-backend python backend/forum_purge.py --dry-run
```

> 注意：`docker exec` 会**继承容器 environment**（有 `ANNOUNCEMENT_DB` 等），而 cron 不继承——所以上面三条通过**不能**证明 crontab 里的路径写对了。真正的验证是等一次调度（或临时把某条改成 `*/2 * * * *` 重建观察 `docker logs`），看日志里没有 `sqlite3.OperationalError: unable to open database file`。

注意：

- **三条任务都是 0 变更空跑安全**：`kb_sync` 无变更时不动 `index_version`、`staff_expire` 无到期行时不写库、`forum_purge` 无超期帖时不写库，漏跑不会写坏数据。真正的影响是**时效**——`kb_sync` 漏挂则 wiki 新页面不进知识库（客服静默答不上来，不报错）；`staff_expire` 漏挂只影响后台台账状态刷新时效（判定权威是 `valid_to`，公开核验接口查询时会懒更新兜底，**不影响核验正确性**）；`forum_purge` 漏挂只让超 30 天的回收站帖多留几天（判定权威是 `deleted_at`，恢复接口自校验 + 列表自过滤，超期帖用户看不到也恢复不了）。
- **上线清单必须逐条实跑核对**：`kb_sync` 的 crontab 曾在旧站上线清单里被默认"已完成"，实际自 2026-09-21 上线起一直未挂，直到 2026-09-26 实跑 `crontab -l` 才发现。crontab、nginx location、构建产物这类**代码侧无法自证**的上线项，一律上服务器实跑一遍再在 `TODO.md` 打勾。
- 日志统一进容器 stdout（`docker logs xqly-website-backend`），不再落宿主机 `/var/log/*.log`；如需留存历史，用 docker 的 log driver 或 `docker logs --since`，暂不需轮转。
