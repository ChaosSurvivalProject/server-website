# TODO

> 已完成事项见各功能的方案文档与 README；本文件只记录**已知遗留与后续计划**。

## 智能客服 P0 上线前清单（✅ 2026-09-21 已上线）

- [x] 服务器填写 `backend/.env`（按 `docs/智能客服P0落地方案.md` §8：对话模型 + Embedding 的 Base URL / API Key / 模型 / 维度），确认未被提交（已 gitignore）
- [x] `pip3 install -r requirements.txt`（唯一新依赖 httpx）
- [x] 首次全量同步：`python3 kb_sync.py --all` → `--check` 全部 unchanged → `--list` 人工核对
- [x] 重启后端，冒烟：`curl localhost:5000/api/kb/info`、`curl -N -X POST localhost:5000/api/kb/chat ...`（**2026-09-25 起接口统一 `/api` 前缀，原清单的 `/kb/` 路径已失效**）
- [x] Nginx 加 `/api/kb/` 反代（SSE 专用参数：`proxy_buffering off`、`proxy_http_version 1.1`、`proxy_set_header Connection ''`、`proxy_cache off`、`gzip off`、`proxy_read_timeout 300s`；与后端 `X-Accel-Buffering: no` 两个都要），验证生产逐字返回而非一次性吐完
- [x] 前端与后台重新构建发布（`frontend` npm run build、`admin-frontend` pnpm build）
- [x] 增量同步挂 crontab（每天 03:00）：`0 3 * * * cd /opt/chaos-web-backend && /opt/chaos-web-backend/venv/bin/python kb_sync.py --incremental >> /var/log/kb_sync.log 2>&1`（**2026-09-26 补挂**，此前遗漏；crond 在跑且 default runlevel 自启，原 crontab 备份在服务器 `/root/crontab.bak-20260926`）
- [x] 量服务常驻内存基线：**实测 69.2 MB**（< 90 MB 阈值，无需上调容器/机器限额）

## 智能客服 P1 候选（按方案 §1.2 顺延）

- [ ] 真实玩家在线人数 / 版本（`mcstatus`，替换 TCP 探测占位字段）
- [ ] 限流共享存储（Redis 等）：当前进程内滑动窗口仅支持单 worker，扩多 worker 前必须换
- [ ] 知识库自动定时任务的 systemd timer / 部署脚本化（当前 crontab 即可，已于 2026-09-26 挂上）
- [ ] 检索效果看板：未命中率统计（从日志聚合），据此调 `KB_MIN_SCORE`
- [ ] Embedding 模型/维度变更的引导式全量重建（当前手动 `kb_sync.py --all --force`）
- [ ] 后台文档上传（PDF/DOCX 解析）、标签体系、对话历史落库与满意度反馈

## 员工名片 P0 上线清单（✅ 全部完成，P0 收口）

- [x] `pip3 install -r requirements.txt`（唯一新依赖 `qrcode`；Pillow 已有）
- [x] 生产 `backend/.env` 增加 `STAFF_PUBLIC_BASE_URL=https://xqly.xt91tv.shop:23333`（无尾斜杠；改后重启 chaos-api 生效）
- [x] 重启后端，冒烟：已实测 `curl localhost:5000/api/staff/public/team` → 200；无 token 调 `/api/staff/admin/page` → 401
- [x] 到期检查挂 crontab（每天 04:00）：`0 4 * * * cd /opt/chaos-web-backend && venv/bin/python staff_expire.py >> /var/log/staff_expire.log 2>&1`（**漏挂不影响核验正确性**，查询路径懒更新会兜底；已实测 `staff_expire.py --dry-run` 正常）
- [x] 前端与后台重新构建发布（`frontend` npm run build、`admin-frontend` pnpm build）——已核对产物：主站 `StaffVerify-*.js`、后台 `card-*.js` 均在生产 webroot，`https /team` → 200
- [x] **手机实测（不可自动化，批量印名片前的最后一关）**：iPhone 相机 / 安卓相机 / 微信扫一扫 / QQ 扫一扫，全部在**移动流量**下用真实印刷尺寸扫码，关注证书警告与非标端口 23333 是否被网络策略阻断（需求规格 §10.5 / §11.2）——**2026-09-26 人工验收通过**
- [x] 名片红线复核：对已产出的名片图逐张目视核对——**不得出现私人微信号**，仅允许企业微信 / 工作邮箱 / 官方 QQ 群 / Discord / 官网（规格 §0.3 / §3.3）——**2026-09-26 人工验收通过**

> 员工名片 P0 **全部 7 项已收口**（技术项 2026-09-26 实跑复核 + 两项人工事当日人工验收通过），可批量印发名片。剩余工作全部在下方 P1 候选里。

## 员工名片模块 P1 候选（按 `docs/员工名片模块评审与落地方案.md` §4.6 / §4.7 / §7 顺延）

- [ ] **应用层限流**：分级滑动窗口（未命中 20 次/分/IP 硬限；命中走宽松兜底 120 次/分/IP），设计见方案 §4.6。启用时**必须与下一项同时上线**（限流负责封顶日志写入速率）
- [ ] **查询日志与审计**：新建 `staff_verify_log` 表 + 每次查询写入 + 90 天清理（进程启动时执行一次）+ 后台分页页，见方案 §4.7
- [ ] 名片服务端渲染（Pillow + 宿主机 CJK 字体，PNG/PDF 一键出图），见方案 §4.8 / §6.5
- [ ] 到期提醒产品化（后台统计条 / QQ 群机器人推送）
- [ ] 限流换共享存储（多 worker 前提；与客服限流共用该遗留）

> 员工名片 P0 的**有意不做项**（勿当缺陷"修掉"）：应用层限流、查询日志审计、服务端渲染、中文字体。P0 的过期状态由 `valid_to` 判定并把 `active` 回写为 `revoked`（`revoked_reason='expired'`，仅系统写入），`backend/staff_expire.py` + crontab 每日兜底——**crontab 漏挂不影响核验正确性**（判定权威是 `valid_to`）。

## 其他遗留

- [ ] 后端 CORS `allow_origins=["*"]` 生产收紧评估（同源部署下可直接收窄）
- [ ] 记忆项：HTTPS 证书 2026-12-24 到期，续签后需替换 `/etc/nginx/ssl/` 两文件并 reload（详见 `AGENTS.md`「部署拓扑」）
