# for-deploy — 生产部署配置留档

> ⚠️ **本目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据一律不进；普通配置里如无必要也不要写外部 IP/端口。留档前先自查一遍文件内容。

本目录存放生产服务器上实际生效、但不属于任何子项目构建产物的配置文件快照，作为仓库内的留档参照。

## 文件清单

| 文件 | 生产位置 | 说明 |
| --- | --- | --- |
| `chaos-web.conf` | `/etc/nginx/http.d/chaos-web.conf`（156.254.7.56） | nginx 站点主配置：HTTPS（Let's Encrypt 通配符证书 `*.xt91tv.shop`，2026-12-24 到期）+ `/api` 反代 FastAPI(:5000) + `/api/kb/` SSE 四件套 + legacy 兼容路径 + `/wiki/` cleanUrls + SPA fallback |
| `crontab` | root 用户 crontab：`/var/spool/cron/crontabs/root`（Alpine busybox） | 生产**唯一**的定时机制：两条业务任务——`kb_sync.py --incremental`（03:00，知识库增量同步）+ `staff_expire.py`（04:00，名片到期回写）。上半段的 `run-parts /etc/periodic/*` 是 busybox 系统默认项，非本项目配置 |

## 与生产保持同步

- 生产 conf 的权威来源是服务器本体；本文件是**留档快照**，改 nginx 走「本地编辑 → scp → `nginx -t` → `nginx -s reload`」流程（详见 AGENTS.md 部署拓扑），改完后**把新 conf 回拷到本目录**留档：
  ```bash
  scp -P 22333 root@156.254.7.56:/etc/nginx/http.d/chaos-web.conf for-deploy/chaos-web.conf
  ```
- crontab 改法见下方「改定时任务」，改完同样回拷留档：
  ```bash
  ssh -p 22333 root@156.254.7.56 'crontab -l' > for-deploy/crontab
  ```
- 留档时用 `md5sum` 比对一遍，确保与线上字节一致（`crontab` 可直接比对 `ssh … 'crontab -l' | md5sum`）。

## 注意（改 conf 前必读）

- `/health` 与 `/announcement/uploads/` 两个 legacy location **勿删**：前者是外部监控/旧部署门禁在用，后者服务历史公告正文内嵌的旧图片 URL（生产库存量内容，删除会导致旧公告图片 404）。
- `/api/kb/` 的 SSE 四件套（`proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`）不能丢，否则智能客服流式变一次性返回。
- 服务器全局 nginx.conf 已声明 `shared:SSL` 共享内存区，本 conf 里不要再加 `ssl_session_cache shared:SSL:...`（区名冲突会 `nginx -t` 失败）。
- 服务器本地探测 TLS 必须写 `https://127.0.0.1:80`（nginx 在 80 上做 ssl，443 无监听）。

## 改定时任务（crontab）

生产没有 celery / APScheduler / systemd timer，**所有定时逻辑都挂 crontab**（`crond -c /etc/crontabs -f`，default runlevel 自启）。两条业务任务的代码都在仓库内（`backend/kb_sync.py`、`backend/staff_expire.py`），本目录只留 crontab 条目快照。

改法（**不要 ssh 里 `sed` 改 /var/spool/cron/crontabs/root，务必走 `crontab` 命令**，否则可能因末尾换行/属主问题被 crond 忽略）：

```bash
ssh -p 22333 root@156.254.7.56 'crontab -l > /root/crontab.bak-$(date +%Y%m%d)'   # ① 先备份
# ② 本地编辑 for-deploy/crontab，然后上传安装（保留 busybox 默认的 run-parts 段）
ssh -p 22333 root@156.254.7.56 'crontab -' < for-deploy/crontab
ssh -p 22333 root@156.254.7.56 'crontab -l' | diff - for-deploy/crontab           # ③ 确认一致
```

改完**把生产 crontab 回拷到本目录**留档（见上节）。验证任务本身能跑通时，按 crond 的实际调用方式实跑一次（crond 用 `/bin/sh`，且不加载交互式环境）：

```bash
ssh -p 22333 root@156.254.7.56 '/bin/sh -c "cd /opt/chaos-web-backend && /opt/chaos-web-backend/venv/bin/python kb_sync.py --incremental >> /var/log/kb_sync.log 2>&1"'
```

注意：

- **两条任务都是 0 变更空跑安全**：`kb_sync` 无变更时不动 `index_version`、`staff_expire` 无到期行时不写库，漏跑不会写坏数据。真正的影响是**时效**——`kb_sync` 漏挂则 wiki 新页面不进知识库（客服静默答不上来，不报错）；`staff_expire` 漏挂只影响后台台账状态刷新时效（判定权威是 `valid_to`，公开核验接口查询时会懒更新兜底，**不影响核验正确性**）。
- **上线清单必须逐条实跑核对**：`kb_sync` 的 crontab 曾在上线清单里被默认"已完成"，实际自 2026-09-21 上线起一直未挂，直到 2026-09-26 实跑 `crontab -l` 才发现。crontab、nginx location、构建产物这类**代码侧无法自证**的上线项，一律上服务器实跑一遍再在 `TODO.md` 打勾。
- 日志在 `/var/log/kb_sync.log` 与 `/var/log/staff_expire.log`（都是 append，单行/天，暂不需轮转）。
