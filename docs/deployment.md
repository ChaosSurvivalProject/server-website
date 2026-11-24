# 部署（Docker 与生产 Nginx）

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 下沉的专题文档（原为原样下沉，2026-11-23 按镜像化部署现状更新了「生产部署」一节）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

> 生产拓扑与运维规约（1panel、统一前端容器、镜像内 cron、for-deploy 留档）见 [docs/agents/deployment.md](./agents/deployment.md)。

compose 文件在**仓库根目录**（2026-10-31 从 `backend/` 迁出）：

```bash
docker compose up -d --build
```

起两个服务：

| 服务 | 容器 | 说明 |
|------|------|------|
| `xqly-website-backend` | `xqly-website-backend` | FastAPI，宿主机只绑 `127.0.0.1:5000` |
| `xqly-website-web` | `xqly-website-web` | 统一前端 nginx：`/` 主站 + `/admin/` 后台 + `/wiki/` 文档 + `/api` 反代，宿主机只绑 `127.0.0.1:8090` |

本机访问 `http://127.0.0.1:8090/` 即整站（前端 + 后端经 nginx 反代联通）。数据持久化在 `backend/data/`；`backend/.env`（含 API Key）以只读卷挂入容器。生产部署说明见 `for-deploy/README.md`。

## 生产部署

生产与本地/测试共用同一套 `docker-compose.yml` 和两个镜像，区别只在镜像来源与端口绑定：

- 镜像由 GitHub Actions（`.github/workflows/release-images.yml`）在 Release 时构建并推送 GHCR：`ghcr.io/chaossurvivalproject/server-website-backend` / `-web`。服务器**只拉取运行，不 build、不跑 Vite**（香港 2C2G 跑前端构建会 OOM）：

  ```bash
  docker compose pull && docker compose up -d --no-build
  ```

- 生产 `web` 只绑 `127.0.0.1:8090`（`WEB_BIND_IP` 默认回环），由 1panel/OpenResty 按域名反代对外；测试环境在根目录 `.env`（模板见 `.env.example`）设 `WEB_BIND_IP=0.0.0.0` 便于局域网访问，用 `docker compose up -d --build` 本机构建。
- 统一入口是 `xqly-website-web` 容器（`web/Dockerfile` 多阶段构建三个前端 + `web/nginx.conf` 路由）：`/` 主站 SPA、`/admin/` 后台、`/wiki/` 文档、`/api` 反代 `xqly-website-backend:5000`；`/health`、`/announcement/uploads/`、`/download/` 为兼容 location。
- `/api/kb/` 的反代需保留 SSE 四件套：`proxy_http_version 1.1`、`proxy_set_header Connection ''`、`proxy_buffering off`、`gzip off`、`proxy_read_timeout 300s`（与后端响应头 `X-Accel-Buffering: no` 两个都要，否则流式被缓冲成一次性返回）。
- 生产 1panel 站点的 conf 快照在 `for-deploy/`：`xqly.xt91tv.shop.conf`（面板生成）+ `xqly-app.conf`（手工 location），与线上字节一致。`web/nginx.conf` 与 `xqly-app.conf` 是同一套规则的两个载体，改其一必须同步另一份（详见 [docs/agents/deployment.md](./agents/deployment.md) 与 `for-deploy/README.md`）。
- 定时任务已进后端镜像（`backend/crontab` 四条，`backend/docker-entrypoint.sh` 拉起），不再挂宿主机 crontab；日志进 `docker logs xqly-website-backend`。

## 爬虫可见性与运维信息收口（SEO P4 / FLPR-66）

- `frontend/public/robots.txt` 是 AI 检索/训练立场的唯一声明源：检索 / 引用类 UA（`OAI-SearchBot`、`ChatGPT-User`、`PerplexityBot`、`Perplexity-User`、`Claude-SearchBot`、`Claude-User`）放行；训练类（`GPTBot`、`ClaudeBot`、`Google-Extended`、`CCBot`）拒绝。两者是独立开关——屏蔽 `GPTBot` 不会把站点移出 ChatGPT Search，屏蔽 `OAI-SearchBot` 才会；`User-agent: *` 段只挡后台与接口路径。
- 该文件由 `web/nginx.conf` 与 `for-deploy/xqly-app.conf` 的 `location = /robots.txt` 精确匹配提供，**任意 UA 均 200、`Content-Type: text/plain`**（`default_type` 兜底，不依赖 mime.types）；`sitemap.xml` 同款精确匹配。改 nginx 时两份配置必须同步（见上方约定）。
- 边缘网关 / CDN 的 Bot 放行属 P0，不在此仓库；CDN 默认 Bot 规则可能静默覆盖 robots.txt。**每季度对照访问日志复审一次 UA 清单**，新 UA 出现频繁；`Bytespider` 若需拦截只能在 CDN / WAF 做连接级拒绝（robots.txt 只是请求，不是墙）。
- 运维信息收口：nginx 对 `*.bak` / `*.sql` / `*.db` / `*.zip` / `*.log` / `*.pem` 等敏感后缀统一返回 404，`/admin/` 返回 `X-Robots-Tag: noindex, nofollow`。`Disallow` 不等于不可索引，敏感内容必须在服务端层面不公开。
- 公告与后台录入内容禁止写服务器路径、备份文件名、部署命令等运维细节；历史内容若已被外链引用，要从源头删除，不能只靠 robots.txt。
