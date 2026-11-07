# 部署（Docker 与生产 Nginx）

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 原样下沉的专题文档（内容未改动，仅调整标题层级与文内交叉引用）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

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

前后端同域部署，由 Nginx 统一入口：

- `frontend` 构建产物（`npm run build` → `dist/`）作为静态站点托管
- `/api` 反向代理到本机 FastAPI（5000 端口，后端所有接口统一挂 /api 前缀）；其中 `/api/kb/` 的反代需为 SSE 追加：`proxy_http_version 1.1`、`proxy_set_header Connection ''`、`proxy_buffering off`、`gzip off`、`proxy_read_timeout 300s`（与后端响应头 `X-Accel-Buffering: no` 两个都要，否则流式被缓冲成一次性返回）
- `wiki` 构建产物挂在 `/wiki/` 路径下（VitePress `base: '/wiki'`）
- `admin-frontend` 构建产物挂在 `/admin/` 路径下（pure-admin-thin，`base: '/admin/'`）
