# 员工名片模块规约

> 本文是 [AGENTS.md](../../AGENTS.md) 对应规约小节的完整原文（2026-11-07 文档重构时下沉，内容未改动）；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

- **完整身份码是管理员端专属**：公开接口（`/api/staff/public/*`）一律不下发完整 `staffCode` 与 `remark`（验证页正文只显示展示码后四位 `••••xxxx`）；「导出名单 CSV」（`/api/staff/admin/export`）是需求 §10.1「不返回完整身份码列表」的**唯一豁免点**（需求 §8.1 要求导出名单，矛盾解已拍板）——**不要把它当漏洞"修掉"**；删除该接口前先改 `docs/员工管理/员工名片模块需求规格.md`。
- **状态两态 + `valid_to` 权威**：`staff.status` 只存 `active` / `revoked`（无第三态 expired）；过期判定**只看 `now > valid_to`**，命中时由 `expire_due()` 把 active 回写为 `revoked`（`revoked_reason='expired'`，该值仅系统写入、后台撤销下拉里不得出现）。回写两路径共用同一函数：公开验证接口查询时懒更新（幂等）+ `backend/staff_expire.py`（CLI + crontab 每日一次，`main.py` 启动时也跑一次）；**crontab 漏挂不影响核验正确性**，勿把状态判定改成"以 status 为准"。
- **续期必须能救回过期**：`renew` 对 `revoked_reason='expired'` 的记录自动恢复 active 并清空撤销字段（二维码不变）；对人工撤销（离职/转岗/暂停/码异常）返回 400，必须先 `restore`（restore 强制换新码）。缺这条会出现"续期成功但扫码仍显示失效"的静默不一致。
- **二维码 URL 由后端单一来源拼接**：`STAFF_PUBLIC_BASE_URL`（`backend/.env`，启动期读入 `config.STAFF`，无尾斜杠）→ `f"{BASE}/staff/{code}"`；前端不得拼 URL、不得传 URL。生成参数：纠错 M、border=4、box_size=10；**禁止硬编码 `version=`**（49 字节 URL 实测 v4，由库自动选版，硬编码会在域名/码长变更时直接抛 DataOverflowError）。
- **名片模板（`admin-frontend/src/views/staff/card.vue`）**：出图依赖**必须用 `html2canvas-pro`**（html2canvas 维护 fork，API 相同）——原版 1.4.1 已停更且不支持 oklch，而 pure-admin 全局挂了 Tailwind v4 主题（`:root` 色板全是 oklch），用原版导出名片必报 `Attempting to parse an unsupported color function "oklch"`（2026-09-25 踩过，勿换回 `html2canvas`）。二维码承载区**必须纯白底**（改透明/深色会扫不出来）；`.qrcode` 200px（印刷 ≥20mm 阈值）；正面含像素头像（canvas 关平滑放大）+ 游戏ID（二维码下方）+ 名片版本 + 防伪提示；PNG/JPG 走本地 npm 依赖（**勿改回 CDN**，与"不依赖第三方平台"冲突且离线不可用），PDF 走浏览器 `window.print()`；卡片子树颜色只用纯 hex/rgb（纵深防御，不能替代 html2canvas-pro）。
- **P0 有意不做**（顺延 P1，已登记 `TODO.md`，勿当缺陷补齐）：应用层限流、查询日志审计（`staff_verify_log` 表不建）、服务端名片渲染（Pillow + CJK 字体）、到期推送通知。P0 依据：身份码 12 位 × 32 字符表 ≈ 1.15×10¹⁸，枚举不可行。
- 职务配色表（服主蓝/技术员绿/财务橙/管理员紫/建筑棕/客服青，只区分职务不代表权限）在三处保持一致：`frontend/src/utils/staffRoles.js`、`admin-frontend/src/views/staff/list.vue`、`admin-frontend/src/views/staff/card.vue`。
