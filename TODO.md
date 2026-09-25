# TODO

> 已完成事项见各功能的方案文档与 README；本文件只记录**已知遗留与后续计划**。

## 智能客服 P0 上线前清单

- [ ] 服务器填写 `backend/.env`（按 `docs/智能客服P0落地方案.md` §8：对话模型 + Embedding 的 Base URL / API Key / 模型 / 维度），确认未被提交（已 gitignore）
- [ ] `pip3 install -r requirements.txt`（唯一新依赖 httpx）
- [ ] 首次全量同步：`python3 kb_sync.py --all` → `--check` 全部 unchanged → `--list` 人工核对
- [ ] 重启后端，冒烟：`curl localhost:5000/kb/info`、`curl -N -X POST localhost:5000/kb/chat -H 'Content-Type: application/json' -d '{"message":"服务器地址是多少"}'`
- [ ] Nginx 加 `/kb/` 反代（SSE 专用参数：`proxy_buffering off`、`proxy_http_version 1.1`、`proxy_set_header Connection ''`、`proxy_cache off`、`gzip off`、`proxy_read_timeout 300s`；与后端 `X-Accel-Buffering: no` 两个都要），验证生产逐字返回而非一次性吐完
- [ ] 前端与后台重新构建发布（`frontend` npm run build、`admin-frontend` pnpm build）
- [ ] 增量同步挂 crontab（每天 03:00）：`0 3 * * * cd /path/to/backend && /usr/bin/python3 kb_sync.py --incremental >> ../logs/kb_sync.log 2>&1`
- [ ] 量服务常驻内存基线：`ps -o rss= -p "$(pgrep -f 'app.main:app')"`；基线 > 90MB 时把容器/机器限额提到 256MB（不要靠砍向量省内存，见决策记录 §2.3）

## 智能客服 P1 候选（按方案 §1.2 顺延）

- [ ] 真实玩家在线人数 / 版本（`mcstatus`，替换 TCP 探测占位字段）
- [ ] 限流共享存储（Redis 等）：当前进程内滑动窗口仅支持单 worker，扩多 worker 前必须换
- [ ] 知识库自动定时任务的 systemd timer / 部署脚本化（当前 crontab 即可）
- [ ] 检索效果看板：未命中率统计（从日志聚合），据此调 `KB_MIN_SCORE`
- [ ] Embedding 模型/维度变更的引导式全量重建（当前手动 `kb_sync.py --all --force`）
- [ ] 后台文档上传（PDF/DOCX 解析）、标签体系、对话历史落库与满意度反馈

## 员工名片模块 P1 候选（按 `docs/员工名片模块评审与落地方案.md` §4.6 / §4.7 / §7 顺延）

- [ ] **应用层限流**：分级滑动窗口（未命中 20 次/分/IP 硬限；命中走宽松兜底 120 次/分/IP），设计见方案 §4.6。启用时**必须与下一项同时上线**（限流负责封顶日志写入速率）
- [ ] **查询日志与审计**：新建 `staff_verify_log` 表 + 每次查询写入 + 90 天清理（进程启动时执行一次）+ 后台分页页，见方案 §4.7
- [ ] 名片服务端渲染（Pillow + 宿主机 CJK 字体，PNG/PDF 一键出图），见方案 §4.8 / §6.5
- [ ] 到期提醒产品化（后台统计条 / QQ 群机器人推送）
- [ ] 限流换共享存储（多 worker 前提；与客服限流共用该遗留）

> 员工名片 P0 的**有意不做项**（勿当缺陷"修掉"）：应用层限流、查询日志审计、服务端渲染、中文字体。P0 的过期状态由 `valid_to` 判定并把 `active` 回写为 `revoked`（`revoked_reason='expired'`，仅系统写入），`backend/staff_expire.py` + crontab 每日兜底——**crontab 漏挂不影响核验正确性**（判定权威是 `valid_to`）。

## 其他遗留

- [ ] 后端 CORS `allow_origins=["*"]` 生产收紧评估（同源部署下可直接收窄）
