# for-deploy — 生产部署配置留档

> ⚠️ **本目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据一律不进；普通配置里如无必要也不要写外部 IP/端口。留档前先自查一遍文件内容。

本目录存放生产服务器上实际生效、但不属于任何子项目构建产物的配置文件快照，作为仓库内的留档参照。

## 生产拓扑（2026-10-03 起：1panel + Docker）

换服务器后整套部署方式变了——旧站是裸机 nginx（`/etc/nginx/http.d/chaos-web.conf`，NAT 外部 23333 → 内部 80 且 nginx 在 80 上直接跑 SSL）。**现在是标准 443 的 1panel 托管**：

| 层 | 位置 |
| --- | --- |
| 面板 | 1panel v2，OpenResty 容器 `1Panel-openresty-TV94`（**host 网络**，监听 80/443） |
| 站点 | 1panel「静态网站」，域名 `xqly.xt91tv.shop`，站点根 `/opt/1panel/www/sites/xqly.xt91tv.shop/index` |
| 站点 conf | `/opt/1panel/www/conf.d/xqly.xt91tv.shop.conf`（1panel 生成，宿主机路径；容器内是 `/usr/local/openresty/nginx/conf/conf.d/`） |
| 自定义 location | `/opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf` |
| 后端 | Docker 容器 `announcement-backend`，只绑 `127.0.0.1:5000`；定义在仓库 `backend/docker-compose.yml` |
| 仓库 | `/opt/xqly-website`（前端三套产物已构建投放，见下） |
| 证书 | 1panel「SSL」里导入的通配符证书 `*.xt91tv.shop`（Let's Encrypt，**2026-12-24 到期**），由面板下发给站点 `ssl/` 目录 |

## 文件清单

| 文件 | 生产位置 | 说明 |
| --- | --- | --- |
| `xqly.xt91tv.shop.conf` | `/opt/1panel/www/conf.d/xqly.xt91tv.shop.conf` | 1panel 生成的站点 server 块。**除末尾那行 `include .../proxy/*.conf;` 外全部由面板生成**，不要把它当成手工配置来维护 |
| `xqly-app.conf` | `/opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf` | 手工维护的应用 location：静态资源缓存 + `/api/kb/` SSE 四件套 + `/api` 反代 + legacy 兼容路径 + `/admin`、`/wiki` 跳转 + `/wiki/` cleanUrls + **SPA fallback** |
| `crontab` | root 用户 crontab（`crontab -l`） | 生产**唯一**的定时机制：`kb_sync.py --incremental`（03:00 知识库增量同步）+ `staff_expire.py`（04:00 名片到期回写），两者都通过 `docker exec` 在容器内执行 |

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

服务器上**没有也不会**跑 Vite（那台机器内存只剩 ~1GB，与 MySQL/Redis/halo/napcat 等生产服务同机，Vite 构建峰值会触发 OOM 连坐）。三个产物在本机构建后 `scp` 投放：

| 子项目 | 构建命令（本机） | 投放位置 |
| --- | --- | --- |
| `frontend` | `npm run build` | `/opt/1panel/www/sites/xqly.xt91tv.shop/index/` |
| `admin-frontend` | `pnpm install && pnpm build`（Windows 下必须走 `pnpm`，`build` 脚本用了 `NODE_OPTIONS=…` 的 Unix 写法，靠 pnpm 的 `shell-emulator` 才能跑） | 同上 `index/admin/` |
| `wiki` | `npm run build` | 同上 `index/wiki/` |

站点根目录里 `404.html` 是 1panel 建的，`admin/`、`wiki/` 是子目录——三者与 SPA 的 `index.html` 共存，靠 `xqly-app.conf` 里的 location 分流。

## 注意（改 conf 前必读）

- **SPA fallback 勿删**：`location / { try_files $uri $uri/ /index.html; }` 撑住 history 路由（`/announcements`、`/forum/...`、扫码直达 `/staff/{身份码}`、`/team`）。1panel 模板不生成它，缺了整个前端只有首页能开。
- `/health` 与 `/announcement/uploads/` 两个 legacy location **勿删**：前者是外部监控/旧部署门禁在用，后者服务历史公告正文内嵌的旧图片 URL（存量内容兼容）。
- `/api/kb/` 的 SSE 四件套（`proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`）不能丢，否则智能客服流式变一次性返回（与后端 `X-Accel-Buffering: no` 两个都要）。
- 站点 conf 里已有 `ssl_session_cache shared:SSL:10m;`，是 1panel 生成的，不要重复声明同名 zone（`nginx -t` 会失败）。
- 服务器本地验证 TLS/路由不要用公网 IP 回环绕 NAT，直接指定解析：
  ```bash
  curl -sI --resolve xqly.xt91tv.shop:443:127.0.0.1 https://xqly.xt91tv.shop/
  ```

## 改定时任务（crontab）

生产没有 celery / APScheduler / systemd timer，**所有定时逻辑都挂 root crontab**（Ubuntu `cron.service`）。两条业务任务的代码都在仓库内（`backend/kb_sync.py`、`backend/staff_expire.py`），本目录只留 crontab 条目快照。

改法（**不要 `sed` 改 `/var/spool/cron/crontabs/root`，务必走 `crontab` 命令**，否则可能因末尾换行/属主问题被 cron 忽略）：

```bash
ssh root@<生产机> 'crontab -l > /root/crontab.bak-$(date +%Y%m%d)'   # ① 先备份
scp for-deploy/crontab root@<生产机>:/tmp/crontab.new                # ② 上传本地编辑好的快照
ssh root@<生产机> 'crontab /tmp/crontab.new && crontab -l'           # ③ 安装并回显
ssh root@<生产机> 'crontab -l' | diff - for-deploy/crontab           # ④ 确认与留档一致
```

> 别用 `ssh … 'crontab -' < for-deploy/crontab` 这种标准输入安装法——在 Windows + PowerShell 下管道会把文件重新编码，cron 直接报 `bad minute` 装不进去。用 `scp` 传文件再 `crontab <file>` 是字节安全的。

验证任务本身能跑通时，按 cron 的实际调用方式实跑一次（cron 用 `/bin/sh`，不加载交互式环境，所以条目里写的是 `docker` 绝对路径 `/usr/bin/docker`）：

```bash
/usr/bin/docker exec announcement-backend python backend/kb_sync.py --check
/usr/bin/docker exec announcement-backend python backend/staff_expire.py --dry-run
```

注意：

- **两条任务都是 0 变更空跑安全**：`kb_sync` 无变更时不动 `index_version`、`staff_expire` 无到期行时不写库，漏跑不会写坏数据。真正的影响是**时效**——`kb_sync` 漏挂则 wiki 新页面不进知识库（客服静默答不上来，不报错）；`staff_expire` 漏挂只影响后台台账状态刷新时效（判定权威是 `valid_to`，公开核验接口查询时会懒更新兜底，**不影响核验正确性**）。
- **上线清单必须逐条实跑核对**：`kb_sync` 的 crontab 曾在旧站上线清单里被默认"已完成"，实际自 2026-09-21 上线起一直未挂，直到 2026-09-26 实跑 `crontab -l` 才发现。crontab、nginx location、构建产物这类**代码侧无法自证**的上线项，一律上服务器实跑一遍再在 `TODO.md` 打勾。
- 日志在 `/var/log/kb_sync.log` 与 `/var/log/staff_expire.log`（都是 append，单行/天，暂不需轮转）。
