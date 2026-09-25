# for-deploy — 生产部署配置留档

> ⚠️ **本目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据一律不进；普通配置里如无必要也不要写外部 IP/端口。留档前先自查一遍文件内容。

本目录存放生产服务器上实际生效、但不属于任何子项目构建产物的配置文件快照，作为仓库内的留档参照。

## 文件清单

| 文件 | 生产位置 | 说明 |
| --- | --- | --- |
| `chaos-web.conf` | `/etc/nginx/http.d/chaos-web.conf`（156.254.7.56） | nginx 站点主配置：HTTPS（Let's Encrypt 通配符证书 `*.xt91tv.shop`，2026-12-24 到期）+ `/api` 反代 FastAPI(:5000) + `/api/kb/` SSE 四件套 + legacy 兼容路径 + `/wiki/` cleanUrls + SPA fallback |

## 与生产保持同步

- 生产 conf 的权威来源是服务器本体；本文件是**留档快照**，改 nginx 走「本地编辑 → scp → `nginx -t` → `nginx -s reload`」流程（详见 AGENTS.md 部署拓扑），改完后**把新 conf 回拷到本目录**留档：
  ```bash
  scp -P 22333 root@156.254.7.56:/etc/nginx/http.d/chaos-web.conf for-deploy/chaos-web.conf
  ```
- 留档时用 `md5sum` 比对一遍，确保与线上字节一致。

## 注意（改 conf 前必读）

- `/health` 与 `/announcement/uploads/` 两个 legacy location **勿删**：前者是外部监控/旧部署门禁在用，后者服务历史公告正文内嵌的旧图片 URL（生产库存量内容，删除会导致旧公告图片 404）。
- `/api/kb/` 的 SSE 四件套（`proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`）不能丢，否则智能客服流式变一次性返回。
- 服务器全局 nginx.conf 已声明 `shared:SSL` 共享内存区，本 conf 里不要再加 `ssl_session_cache shared:SSL:...`（区名冲突会 `nginx -t` 失败）。
- 服务器本地探测 TLS 必须写 `https://127.0.0.1:80`（nginx 在 80 上做 ssl，443 无监听）。
