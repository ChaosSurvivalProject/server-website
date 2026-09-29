# AGENTS.md

星穹旅驿 Minecraft 服务器官方网站（frontend + backend + wiki 三合一仓库）。

整体架构、目录树与接口清单见 [README.md](README.md)；**本文件只记录项目特有的规约与坑**，通用工程惯例不在此重复。

## 仓库结构要点

- 四个子项目相互独立，各自持有 `package.json` / `node_modules`，**没有根级 workspace**，仓库也没有根级 `package.json`——所有安装、构建、开发命令必须在对应子目录（`frontend/`、`backend/`、`wiki/`、`admin-frontend/`）内执行。
- 不要提交 `node_modules/`、`dist/`、`*.db`、`backend/data/`、`wiki/.vitepress/cache|dist/`（见 `.gitignore`）。

## 常用命令

```bash
# 后端 (FastAPI, :5000)
cd backend
pip install -r requirements.txt
python3 run.py            # uvicorn --reload，开发用
python3 seed.py           # 写入示例公告数据
docker compose up -d --build   # Docker 部署（构建上下文为项目根目录，见下）

# 前端 (Vite, :5173)
cd frontend
npm install
npm run dev
npm run build             # 产物 dist/，gitignore

# Wiki (VitePress)
cd wiki
npm install
npm run dev
npm run build             # 产物 .vitepress/dist/

# 后台管理 (Vite + Element Plus, :8848)
cd admin-frontend
pnpm install
pnpm dev                  # 开发服务器（端口由 .env.development 的 VITE_PORT 决定，当前 3005，覆盖 .env 里的 8848），API 代理到后端 :5000
pnpm build                # 产物 dist/，部署到 /admin/
```

## API 契约规约

这是本项目最容易踩坑的部分，改接口前必读：

0. **统一前缀**：所有后端接口统一挂载在 `/api` 前缀下（2026-09-25 起，`backend/app/main.py` 经 `api_router` + `include_router(prefix="/api")` 实现；nginx 只反代 `/api`）。新增接口一律写 `/api/...`；正文内嵌的上传图片规范 URL 也是 `/api/announcement/uploads/...`（旧路径 `/announcement/uploads/...` 仅为存量公告兼容保留，勿用于新内容）。
1. **响应包络**：所有接口返回 `{code, message, data}`，`code=0` 表示成功。前端 `axiosInstance` 响应拦截器已统一解包（直接返回 `data`），组件代码拿到的就是裸数据——**不要在前端组件里再判断 `code`**。
2. **字段命名**：数据库/后端内部用 snake_case，对外 JSON 用 camelCase（`publishTime` / `isPublished` / `readCount` / `createTime` / `updateTime`）。Pydantic 模型通过 `alias` + `populate_by_name=True` 映射（见 `backend/app/schemas.py`），新增字段必须同时补别名。
3. **契约参照实现**：`frontend/src/api/api.js` 是前后端契约的参照。**新增或修改后端接口时必须同步该文件**，保持两侧一致。后台管理前端 `admin-frontend/src/api/` 同步维护；其 HTTP 层（`admin-frontend/src/utils/http/`）已统一解包 `{code, message, data}`，并把 HTTP 错误体（FastAPI `detail` / 包络 `message`）提取到 `error.message`，页面 catch 里直接 `ElMessage.error(e.message)` 弹提示，**不要在页面里重复解析错误体**。传 `FormData`（文件上传）时必须显式加 `Content-Type: multipart/form-data` 请求头：实例默认 `application/json` 会让 axios 把 `FormData` 序列化成 JSON，后端解析不到字段直接 422。
4. **时间格式**：统一存 ISO 字符串 `YYYY-MM-DDTHH:MM:SS`（SQLite 中为 `String(30)` 列，不用 datetime 类型）。
5. **布尔语义用 int**：如 `isPublished`，`0=草稿, 1=已发布`，不要改成 bool。
6. **监控接口**：`GET /api/monitor/server-info/{id}` 目前是 TCP 探测的最小实现（`online/offline` + 占位字段），响应结构被首页 `OnlineCounter` 组件依赖，扩展时不能破坏现有字段。
7. **公告正文双格式**：对外字段为 `rawContent`（原始内容）+ `contentType`（`'html'`=富文本 / `'markdown'`=Markdown，缺省 `html`；Pydantic 侧 Python 字段名仍是 `content`/`content_type`，仅 alias 对外）。`html` 行入库前经 `nh3` 消毒；`markdown` 行**原样入库**（nh3 会破坏 Markdown 语法），渲染全在前端——主站 `src/utils/markdown.js`（marked + DOMPurify）统一渲染并消毒，后台按格式切换 wangEditor / md-editor-v3。新加内容格式相关逻辑时不要绕过这两个入口。
8. **SSE 包络例外（全项目唯一）**：`POST /api/kb/chat` 返回 `text/event-stream`，**不返回 `{code, message, data}` 包络**——SSE 流无法包络，这不是遗漏，不要"修正"它。**仅登录用户可调用**：`get_current_user` 依赖校验 Bearer JWT，未登录/过期 401（属流前错误，标准 HTTP + `detail`）；`streamChat` 用裸 `fetch` 不走 axiosInstance，需自行携带 token。帧协议见 `docs/智能客服/智能客服P0落地方案.md` §4.3（首帧 `sources`、`delta`/`reasoning` 交错、`[DONE]` 收尾；流前错误走标准 HTTP + 包络口径的 `detail`，流开始后只能发 `{"error":...}` 帧）。`frontend/src/api/api.js` 的 `chatAPI.streamChat` 因此用 `fetch` + `ReadableStream` 而非 axios。

## 知识库 / 智能客服规约

- **wiki 是知识库的单一数据源**：`source_type='wiki'` 的文档由 `backend/kb_sync.py`（CLI，按文件 MD5 增量）维护，后台管理页对 wiki 来源只读（删除接口直接 400）；手动粘贴入库为 `manual` 来源。改动知识库一律先改 wiki，再跑脚本。
- **索引热更新是设计点**：脚本/后台每次摄入或删除都自增 `kb_settings.index_version`，服务端每轮对话轻量 SELECT 比对版本，不同才重建内存向量索引——**服务端不需要重启**，别改成"重启生效"。
- 检索为向量 + FTS5 trigram 双路 RRF 融合（`KB_HYBRID_ENABLED=0` 关混合）；FTS 表是**独立表**（非 external content），写入/删除时手动同步 `rowid = kb_chunks.id`，不要加触发器。
- 限流状态在**进程内**（滑动窗口 + 并发计数），P0 按单 worker 部署；改多 worker 必须换共享存储，否则限流失效。
- 知识库配置在 `backend/.env`（**已 gitignore，含 API Key 禁止提交**），`app/config.py` 启动期一次性读入模块级 `KB` 对象——改 `.env` 需重启进程，不要做请求级读取。
- 流式渲染必须复用 `frontend/src/utils/markdown.js` 管线：新增的 `splitMarkdownBlocks`（lexer 切块 → 逐块 parser → DOMPurify）与整篇 parse 等价，ChatWidget 的块级 keyed 渲染 + 末块未闭合补全都建立在它之上，不要绕开另写渲染入口。

## 员工名片模块规约

- **完整身份码是管理员端专属**：公开接口（`/api/staff/public/*`）一律不下发完整 `staffCode` 与 `remark`（验证页正文只显示展示码后四位 `••••xxxx`）；「导出名单 CSV」（`/api/staff/admin/export`）是需求 §10.1「不返回完整身份码列表」的**唯一豁免点**（需求 §8.1 要求导出名单，矛盾解已拍板）——**不要把它当漏洞"修掉"**；删除该接口前先改 `docs/员工管理/员工名片模块需求规格.md`。
- **状态两态 + `valid_to` 权威**：`staff.status` 只存 `active` / `revoked`（无第三态 expired）；过期判定**只看 `now > valid_to`**，命中时由 `expire_due()` 把 active 回写为 `revoked`（`revoked_reason='expired'`，该值仅系统写入、后台撤销下拉里不得出现）。回写两路径共用同一函数：公开验证接口查询时懒更新（幂等）+ `backend/staff_expire.py`（CLI + crontab 每日一次，`main.py` 启动时也跑一次）；**crontab 漏挂不影响核验正确性**，勿把状态判定改成"以 status 为准"。
- **续期必须能救回过期**：`renew` 对 `revoked_reason='expired'` 的记录自动恢复 active 并清空撤销字段（二维码不变）；对人工撤销（离职/转岗/暂停/码异常）返回 400，必须先 `restore`（restore 强制换新码）。缺这条会出现"续期成功但扫码仍显示失效"的静默不一致。
- **二维码 URL 由后端单一来源拼接**：`STAFF_PUBLIC_BASE_URL`（`backend/.env`，启动期读入 `config.STAFF`，无尾斜杠）→ `f"{BASE}/staff/{code}"`；前端不得拼 URL、不得传 URL。生成参数：纠错 M、border=4、box_size=10；**禁止硬编码 `version=`**（49 字节 URL 实测 v4，由库自动选版，硬编码会在域名/码长变更时直接抛 DataOverflowError）。
- **名片模板（`admin-frontend/src/views/staff/card.vue`）**：出图依赖**必须用 `html2canvas-pro`**（html2canvas 维护 fork，API 相同）——原版 1.4.1 已停更且不支持 oklch，而 pure-admin 全局挂了 Tailwind v4 主题（`:root` 色板全是 oklch），用原版导出名片必报 `Attempting to parse an unsupported color function "oklch"`（2026-09-25 踩过，勿换回 `html2canvas`）。二维码承载区**必须纯白底**（改透明/深色会扫不出来）；`.qrcode` 200px（印刷 ≥20mm 阈值）；正面含像素头像（canvas 关平滑放大）+ 游戏ID（二维码下方）+ 名片版本 + 防伪提示；PNG/JPG 走本地 npm 依赖（**勿改回 CDN**，与"不依赖第三方平台"冲突且离线不可用），PDF 走浏览器 `window.print()`；卡片子树颜色只用纯 hex/rgb（纵深防御，不能替代 html2canvas-pro）。
- **P0 有意不做**（顺延 P1，已登记 `TODO.md`，勿当缺陷补齐）：应用层限流、查询日志审计（`staff_verify_log` 表不建）、服务端名片渲染（Pillow + CJK 字体）、到期推送通知。P0 依据：身份码 12 位 × 32 字符表 ≈ 1.15×10¹⁸，枚举不可行。
- 职务配色表（服主蓝/技术员绿/财务橙/管理员紫/建筑棕/客服青，只区分职务不代表权限）在三处保持一致：`frontend/src/utils/staffRoles.js`、`admin-frontend/src/views/staff/list.vue`、`admin-frontend/src/views/staff/card.vue`。

## 社区（论坛）模块规约

实施唯一依据：`docs/论坛/论坛模块第一阶段PRD.md`（v1.4）+ 交互原型 `docs/论坛/prototype/index.html`。第一阶段已完成；本文只记录**最容易写错且各只有一处**的口径。

- **`forum_articles.status` 只能经 `_set_article_status()` 改**（`backend/app/forum.py`）。标签 `use_count` 的增减**只挂在这一个转移点上**（PRD §8-D8）：进入 `status=1` 按当期标签各 +1、离开各 -1，`publish_time` 同时重写/清空。**任何绕过该函数直接 `article.status = x` 的写法都会让计数漂移**。已驳回的文章必须由作者编辑重提回 `status=0` 才能再审（管理员不能直接把 `2` 改成 `1`）。
- **作者编辑 = 重走审核，且要能救回自己发的错**：`PUT /api/forum/articles/{id}` 保存后 `status` 一律回 0、清空 `review_note`/`publish_time`/`remove_by`、`resubmit_count +1`，但**浏览/点赞/收藏/评论全部保留**（同一篇文章的修订，不是新文章）。`remove_by='admin'` 的已下架帖**必须 400 拦住**——否则等于用"编辑重提"绕过管理员下架。编辑页准入是**作者本人**（管理员也没有该路径，后台不改正文，PRD §8-D9）。
- **创建与编辑共用同一份写路径**：字段校验（`_validate_write_payload`）、摘要生成（`_build_summary`）、标签同步（`_sync_article_tags`）三者都被 `POST` 与 `PUT` 共用。**不要复制第二份**，否则必然出现"改了正文但摘要还是旧的"这类静默不一致（PRD §9-12）。
- **`comment_count` = 顶层评论数 + 回复数**（回复也算评论）。删顶层连带其下全部回复、减 `1 + 回复数`；删单条回复只减 1；两者都同步删 `forum_comment_likes` 行。**评论正文是纯文本**，前端 `white-space: pre-wrap` 渲染，**绝不走 Markdown 管线**（评论区是 XSS 最高频入口，PRD §8-D5）。
- **`parent_id` 只指向顶层评论**：对回复再回复时仍填所属顶层评论的 id，另用 `reply_to_user_id` 记"回复 @某人"；后端收到指向回复的 `parentId` 返 400，**拒绝第三级嵌套**。
- **⚠️ 连接池必须是 `NullPool`（每请求一条连接），不要改回 `StaticPool`**（`backend/app/database.py`）。2026-09-27 实测确认：`StaticPool` 只有一条底层连接，而 FastAPI **即使单 worker 也会并发处理请求**，于是所有请求共享同一个 SQLite 事务——A 的 `commit()` 连带提交 B 尚未提交的写入，会话关闭归还连接时的 ROLLBACK 又丢掉别人"已提交"的数据。实测论坛的 `like_count` / `comment_count` / 标签 `use_count` 在 6 并发下有 1/5~2/3 概率与关系表对不上，ASGI 并发探测甚至直接死锁。**论坛的原子计数只有"关系行 INSERT 与计数 UPDATE 同事务提交"才成立，因此每请求独立连接是硬要求，不是优化**。连带影响：`busy_timeout` / `synchronous` 是**连接级** PRAGMA，已从 `init_db()` 移到 engine 的 `"connect"` 事件钩子 `_set_sqlite_pragmas()`——留在 `init_db()` 里只对建表那一条连接生效，`kb_sync.py`（独立进程写同一库文件）会拿不到 `busy_timeout` 而 `database is locked`。`journal_mode=WAL` 是库级且持久化，只在 `init_db()` 设一次。
- **关系表"切换"不许先 SELECT 再决定插删**（check-then-act）。同一用户的两个并发请求会双双看到"无行"、双双 INSERT，撞唯一约束抛 `IntegrityError` → 500，而 PRD §10.3 明确要求"连续快速点击 10 次点赞"不能出错。统一走 `forum.py::_toggle_relation()`（`INSERT OR IGNORE` + 按 `rowcount` 分支返回 +1/-1/0），文章点赞 / 收藏 / 评论点赞三处都用它。两个并发切换最终是"插入 + 删除"配对，行数与计数同步归零，不会漂移。`_resolve_tag()` 同理（两人同时首次提交同名标签会撞 `forum_tags.name`）。
- **计数一律原子 SQL**（`SET x = x + 1`），**禁止 read-modify-write**（并发下会丢计数），ORM 属性自增（`obj.like_count += 1`）同样违反这条——`resubmit_count` 已改成 `update(...).values(resubmit_count=... + 1)`。浏览量同理，且**详情接口不计数**、前端挂载后单独调 `POST /articles/{id}/view`（该接口**匿名可调**，PRD §7.1 把它列在公开接口下——社区绝大多数流量是未登录访客，要求登录会让统计数字系统性少计）；重复刷新重复计数是已接受行为，去重属第二阶段。
- **搜索关键词要转义 LIKE 通配符**（`forum.py::_like_escape` + `like(..., escape="\\")`）：不转义时 `?q=%` 会返回全量文章、`?q=_` 匹配所有单字符词，属于明显的语义错误。标签名长度上限也统一为 `MAX_TAG_NAME_LEN=20`（发帖 / 后台建标签 / 后台改名三处同口径），别再出现"发帖能填 20 字、后台能建 40 字"的分叉。
- **匿名可打接口的数值入参必须有上界**（或依赖 `main.py` 的 `OverflowError` → 400 兜底处理器）：SQLite INTEGER 是 64 位有符号而 FastAPI 的 `int` 无上界，`/api/forum/articles/99999999999999999999999999` 这类请求会在绑参阶段抛 `OverflowError` → 500，可被用来刷错误日志。
- **论坛图片复用公告的静态托管，零 nginx 改动**：落盘 `uploads/forum/YYYYMM/`，对外 URL 仍是 `/api/announcement/uploads/forum/...`（同一个 `StaticFiles` 挂载点）。**不要为此新增 `location` 或新挂载点**——既会引入新的反代需求，也可能与页面路由 `/forum` 同名（项目既有红线）。校验与落盘已抽到 `backend/app/uploads.py`，公告与论坛共用一份口径。
- **代码块底色全站统一浅色 `#f6f8fa`**（以主站公告详情为基准）。两处必须显式压住 highlight.js 的 `.hljs{background:#fff}`：它优先级只有 (0,1,0)，而公告是靠 `.announcement-content pre`（0,1,1）赢的，社区当初只把底色加在外层容器上，导致两边一个灰一个白。规则写在 `frontend/src/assets/styles/markdown.css`（公告 + 社区共用）与 `admin-frontend/src/assets/styles/markdown.css`（后台，从 `main.ts` 全局引入）。
- **⚠️ md-editor-v3 的默认 `codeTheme` 是 `atomOneDark`（深色），且它把高亮主题从 unpkg CDN 动态注入**（`https://unpkg.com/@highlightjs/cdn-assets@11.12.0/styles/atom-one-dark.min.css`）。不显式写 `code-theme="github"`（浅色变体）就会渲染成深色代码块。两个 Markdown 组件都要写（`views/forum/article/list.vue` 的 `MdPreview`、`views/announcement/edit.vue` 的 `MdEditor`），且**底色/文字色另由 `admin-frontend/src/assets/styles/markdown.css` 显式钉死**——这样即使 CDN 取不到（离线/被墙），观感仍然正确，不把展示效果押在第三方资源上。注意 md-editor 还会为 katex / mermaid / echarts / prettier 继续请求 unpkg（库自身的懒加载助手，属既有行为，彻底去除需改库或本地 vendor 全部资源，不在单次需求范围内）。
- **md-editor-v3 的 `preview.css` 只有 5KB，不提供任何正文排版**（pre 底色、代码文字色、列表符号都没有），它指望宿主自己给；`admin-frontend/src/style/reset.scss` 也只设了 `pre` 的字体。所以"预览没样式"不是 bug，是没给样式——要在宿主补。
- **Markdown 的样式与消毒必须跟着渲染管线走，不能跟着调用方走**（2026-09-27 踩过）：highlight.js 主题与 `.announcement-code-block` 包装样式原本写在 `AnnouncementDetail.vue` 里，论坛文章详情（懒加载、从不加载该组件）因此拿到的是**完全没样式**的纯文本代码块——没有高亮、没有顶栏、没有圆角。现已抽到 `frontend/src/assets/styles/markdown.css`（全局，`main.js` 引入）。**新增消费 `renderMarkdownContent()` 的页面时不要把样式挂在自己组件里**。预览侧的消毒器用 `sanitizeHtml()`（同文件导出）传给 md-editor-v3 的 `:sanitize`，保持"全站一份 DOMPurify"。
- **主站上传 FormData 必须显式给 `Content-Type: multipart/form-data`**：`axiosInstance` 的实例级默认头是 `application/json`，而 axios 的 `transformRequest` 对「JSON 内容类型 + FormData」会把 FormData **序列化成 JSON**，后端 `File(...)` 拿不到 `file` 字段 → `422 Field required`。2026-09-28 论坛封面上传踩过一次（`frontend/src/api/api.js` 的 `forumAPI.uploadImage` 漏了这行），显式给 multipart 后 axios 交给浏览器补 boundary 即可。**主站的 `announcementAPI` 等若将来也开放上传，同样要加**（后台 `admin-frontend` 的 http 层已默认 multipart，见 AGENTS.md §API 契约 3）。
- **Vue Options API：`computed` 里的函数值会被当 getter 调用**。`computed: { sanitizeHtml, }`（对象简写）等价于让 Vue 拿组件实例当参数执行 `sanitizeHtml()`，computed 的值变成字符串，传给期望函数的 prop 就报 `sanitize is not a function` 并整页白屏。要暴露函数必须写显式 getter：`sanitizeHtml() { return sanitizeHtml; }`。
- **⚠️ 「跳登录页」与「是否已登录」是两个不同概念，别让它们同名**。`forumToast.js` 导出的 `goLogin(router)` 是**无条件导航**（跳 `/login?redirect=...`）且**没有返回值**；而"是否已登录"要看 `authState.token`（组件里通常是 computed `loggedIn`）。曾因把两者混成同名 `requireLogin`，在文章详情页写成 `if (!this.requireLogin(this.$router)) return;`——`requireLogin` 跳完登录页返回 `undefined`，取反恒为真，于是**登录状态下点赞/收藏也被弹去登录页，而且请求永远发不出去**（不只是跳错页，是功能完全失效）。正确写法：`if (!this.loggedIn) { this.goLogin(this.$router); return; }`。组件内需要布尔判定时方法名一律用 `ensureLoggedIn()`，与 `goLogin()` 区分。
- **模板里直接挂事件处理函数时，Vue 会把事件对象当第一个参数传进去**。`@keydown.enter="addTag"` 会让 `addTag(name)` 收到 **KeyboardEvent**，若函数里写 `(name ?? this.tagInput).trim()` 就会对事件对象调 `.trim()` 抛 TypeError，表现为"回车没反应"且控制台无提示。要区分"传字符串的调用方"（`@click="addTag(t.name)"`）就得加类型守卫：`typeof name === "string" ? name : this.tagInput`。**点建议标签（传字符串）与键盘回车（传事件）是同一函数的两类调用方**。
- **发帖/编辑页的 Markdown 编辑器与后台公告编辑器同款**（同一个 `md-editor-v3`、同款 `mdToolbars` 数组、默认左编辑右预览分屏，`:sanitize` 接本项目的 `sanitizeHtml`）。改工具栏要**两边同步**（`admin-frontend/src/views/announcement/edit.vue` 的 `mdToolbars` 与 `frontend/src/views/forum/PostEditor.vue` 的同名 computed）。注意 v7 的输入区是 CodeMirror 6（`.cm-content` contenteditable，**没有 textarea**），自动化测试要按这个选器。
- **时间解析不要用 `new Date(iso)`**：库里存的是**北京时间 naive ISO 串**，`new Date("2026-09-27T10:00:00")` 会当 UTC 解析再换算，显示会偏 8 小时。统一走 `frontend/src/utils/forumFormat.js` 的 `parseIso()`（手工拆字段构本地 Date）。同理 `_is_muted()` 里 `datetime.now(_TZ)` 带 tzinfo，与解析出的 naive 值比较前必须 `.replace(tzinfo=None)`，否则抛 `can't compare offset-naive and offset-aware datetimes`（踩过）。
- **禁言（`users.mute_until`）与 `status` 三态正交**：禁用=不能登录，禁言=能登录浏览但不能发帖/评论。判定在写操作依赖 `_ensure_not_muted()`（读操作不受限），返回 403 + `detail="账号已被禁言，至 <时间>"`。**点赞/收藏不属"发言"，禁言期间仍可用**——这是有意的，别顺手一起禁。
- **「首页/推荐」是两个系统板块**（`is_system=1`）：`home`=全部已发布，`recommend`=`is_featured=1 OR is_top=1` 且固定按 `view_count` 倒序。系统板块后台**不可删、不可改名、不可隐藏**；文章**禁止投稿到系统板块**（后端创建/修改时校验 400）。
- **置顶帖在任意排序档中都恒排最前**（`ORDER BY is_top DESC, <排序列> DESC`），不是只有默认排序才置顶。
- **第一阶段有意不做**（顺延第二/三阶段，已登记 `TODO.md`，勿当缺陷补齐）：站内信、关注/粉丝（`followerCount` 恒 0）、打赏、等级/头衔、评论审核队列与敏感词、评论作者自删、文章版本记录、回复折叠、回复通知、统计定时任务、全文检索、图床冗余清理、富文本。对应位置只留 UI 占位（统一走 `showForumToast()` 提示"功能开发中"，**不跳转不请求**），配置键 `forum_config.reward*` 预留但无 UI。
- **Banner 配图整幅铺满**：配了 `bannerImage` 就 `position:absolute; inset:0` 铺满整个横幅，`object-fit:cover` + `object-position:center`（溢出**居中裁剪**、**不拉伸**），z-index 依次为 图 0 → 压暗蒙版 1 → 文字 2 → 底部操作条 3。三条要一起写：只写 `cover` 会在偏心位置裁切，只写 `width/height:100%` 会拉伸变形。配图可能很亮，蒙版只做白字可读性保障（`background:linear-gradient(100deg, rgba(15,23,42,.62) …)`）；配图 404 时要用**响应式开关**（`artBroken`）而不是 `display:none`，才能把与它是兄弟节点的蒙版一起撤掉，否则纯渐变底上会蒙一层灰。
- **徽章只有"管理员"一种**（依据 `users.role`）：常量化在 `frontend/src/utils/forumBadges.js`（后台同名表保持一致），**不要在多个组件里硬编码颜色**；依据文档示例的"炽热行者""VIP"等等级头衔属第二阶段，不得以假数据填充。
- 论坛页面样式令牌与 Markdown 正文排版在 `frontend/src/assets/styles/forum.css`（全局，8 个公共组件共用）；类名一律 `fx-` 前缀，因为全站 `App.vue` 有像素风的全局 `.btn`，不加前缀会互相串味。
- **全站统一导航栏**：任何路由都显示 `NavBar`（含论坛的详情 / 发帖 / 编辑 / 我的文章四页）。不要再引入 `meta.hideNav` 之类的按路由隐藏机制——2026-09-27 已按需求移除，页面内用「← 返回社区」提供上下文即可。
- 端到端回归：`backend/forum_smoke_test.py`（`python3 forum_smoke_test.py`，用临时库 + `TestClient`，覆盖状态机/计数/权限/级联等 176 项断言）。改论坛后端先跑它。


## 游戏服务器地址：单一数据源

- 游戏服务器地址持久化在 SQLite `servers` 表（**DB 为唯一权威**）；`backend/app/monitor.py` 的内存 `SERVERS` 字典只是读缓存，启动时 `load_servers()` 从库加载（表空时用文件内默认注册表做种子）。后台「服务器地址管理」页经 admin 接口增删改（先改内存再同步落库，失败回滚内存）。
- **禁止在前端硬编码服务器地址**；前端一律通过 `GET /api/monitor/servers` 获取（env 里只保留监控接口所需的 `VITE_SERVER_ID`，经 `mc-config.js` 暴露为 `server.id`）。
- 新增/修改服务器 = 后台管理页操作或调 admin 接口（持久化）；不要再改代码里的注册表。

## 前端配置规约

- 主站配置一律走 Vite 环境变量（`VITE_` 前缀）：`frontend/.env` 存所有模式共用的默认值（QQ 群、服务器 id、版本文案、后台入口等），`.env.development` / `.env.production` 按构建模式覆盖（dev → 本地 5000，build → 同源）；本地个性化覆盖写 `.env.local`（根 `.gitignore` 的 `*.local` 已忽略）。**三个 `.env` 文件随仓库提交，禁止在组件里直接读 `import.meta.env` 或在别处硬编码这些值**。
- `frontend/src/config/mc-config.js` 只是环境变量的统一读取层（含类型转换），**不要在其中硬编码站点值**；组件一律 `import McConfig` 取值。
- 生产环境 API 走同源（`VITE_BASE_API_URL` 留空 → `baseApiURL: ''`），依赖 Nginx 反代 `/api` 到本机 FastAPI（:5000）。
- 环境变量是构建期静态替换，改 `.env*` 后需重启 dev server / 重新 build 才生效。
- 模板中引用的静态图片必须先 `import` 再绑定 `:src`（如 `Home.vue` 的 `bbs-*.png`、`video-bg.jpg`）；**禁止直接写 `/src/...` 绝对路径**——Vite build 不会打包该路径，生产环境会 404（dev 下看不出来）。

## Wiki 规约

- VitePress `base: '/wiki'` + `cleanUrls: true`。站内链接写相对路径（VitePress 自动加 base）；**外链必须带协议**（`http(s)://`），否则会被加上 `/wiki` 前缀。
- 内容分三大分区，新增页面放对应分区并在 `.vitepress/config.mts` 侧边栏登记：`for-new/`（萌新指南）、`management/`（服务器管理）、`develop/`（服务器建设）。
- 站点外链域名（2026-09-25 起）：官网为 `https://xqly.xt91tv.shop:23333`（HTTPS，明文 HTTP 已禁）。wiki 内指向官网的外链（hero「访问官网」按钮、阵营文档申请入口等）统一写此地址，不要再写死 IP。

## Git 规约

- 远程：`git@github.com:ChaosSurvivalProject/server-website.git`，主分支 `main`。
- 提交信息使用 Conventional Commits 前缀（`feat` / `fix` / `refactor` 等，可带 scope 如 `feat(backend):`），描述用中文。

## 部署拓扑（生产）

**生产对外地址：`https://xqly.xt91tv.shop:23333`**（2026-09-25 起启用）。NAT 外部 23333 → 内部 80，nginx 在内部 80 上**直接跑 SSL**——不是 80→443 跳转，443 无监听；明文 HTTP 请求触发 497，经 `error_page 497` 301 到 HTTPS。

生产 nginx 站点配置：服务器 `/etc/nginx/http.d/chaos-web.conf`，**仓库内留档在 `for-deploy/chaos-web.conf`**（改 conf 前先读 `for-deploy/README.md`）。

同域单入口，Nginx 统一分发：

- `/` → `frontend` 构建产物（SPA 使用 history 路由，**`try_files $uri $uri/ /index.html;` 已配置并生效**，可直接在 `for-deploy/chaos-web.conf` 的兜底 `location /` 核对；`/announcements` 等深层路由刷新、扫码直达 `/staff/xxx` 都依赖它，改动时勿删）
- `/api` → 反代到本机 FastAPI（:5000，后端所有接口统一挂 `/api` 前缀）；其中 `/api/kb/` 的反代必须为 SSE 追加 `proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`（与后端 `X-Accel-Buffering: no` 两个都要，否则流式变一次性返回）
- 兼容旧路径（勿删）：`/health` → 反代 FastAPI（外部监控/旧部署门禁在用）；`/announcement/uploads/` → 反代 FastAPI（历史公告正文内嵌的旧图片 URL，存量数据兼容）
- `/wiki/` → `wiki` 构建产物（VitePress 已按 `/wiki` base 打包）
- `/admin/` → `admin-frontend` 构建产物（pure-admin-thin，已按 `/admin/` base 打包）

**新增 `location` 前缀时不得与前端页面路由同名**：`location /staff` 会把 SPA 的 `/staff/:code` 一并反代走，页面再也进不去，而 dev 直连后端看不出问题。统一 `/api` 之后新模块已不需要单独加 `location`，正常不会再触发；真要加，前缀与页面路由错开（如曾考虑过的复数前缀）。`chaos-web.conf` 里 `location = /faction-beta { try_files /index.html =404; }` 就是历史上处理这类同名的补丁。

后端 Docker 部署时注意：`docker-compose.yml` 位于 `backend/` 下，但**构建上下文是项目根目录**（`context: ..`），因为 Dockerfile 里 `COPY backend/` 依赖该路径——移动文件时两者要一起改。

### 生产定时任务（root crontab）

生产**只有 crontab 一种定时机制**（无 celery / APScheduler / systemd timer），知识库与名片到期两条链路都挂在这里：

- `0 3 * * *` → `cd /opt/chaos-web-backend && /opt/chaos-web-backend/venv/bin/python kb_sync.py --incremental >> /var/log/kb_sync.log 2>&1`（wiki 改动按 MD5 入库，自增 `index_version`；**2026-09-26 补挂，此前上线时遗漏**）
- `0 4 * * *` → `cd /opt/chaos-web-backend && venv/bin/python staff_expire.py >> /var/log/staff_expire.log 2>&1`（**漏挂不影响核验正确性**，`valid_to` 权威 + 查询时懒更新兜底，只影响台账刷新时效）

改 crontab 前先 `crontab -l > /root/crontab.bak-YYYYMMDD` 备份，再 `crontab 新文件` 安装（**勿直接 sed 改 `/var/spool/cron/crontabs/root`**，务必走 `crontab` 命令）。两条任务**都是 0 变更空跑安全**（kb_sync 无变更不动 `index_version`），漏跑不会写坏数据——但漏挂 `kb_sync` 会导致 wiki 新页面不进知识库，客服对未同步内容直接答不上来。**完整条目快照留档在 `for-deploy/crontab`（与 `chaos-web.conf` 同性质，md5 可与线上比对），改法与验证命令见 `for-deploy/README.md`「改定时任务」节**。

## for-deploy 留档目录

- `for-deploy/` 存放生产实际生效、但不属于任何子项目构建产物的配置留档（当前两个：`chaos-web.conf` = nginx 站点配置快照、`crontab` = root crontab 快照；均为**与生产字节一致**的快照，可 `md5sum` 比对，改完后须回拷留档；同步方法与改前注意事项见该目录 `README.md`）。
- **该目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据等一律不进；普通配置里如无必要也不要写外部 IP/端口。敏感文件（证书、`backend/.env`、生产库）只存在于服务器对应路径，不落仓库。

## 已知遗留 / 注意事项

- 后端 CORS 当前 `allow_origins=["*"]`（开发便利），生产收紧时需与同源部署方案一起评估。
- `backend/app/monitor.py` 中 `server-info` 的 `start_time` / `end_time` / `time_period` 参数是预留参数，当前实现未使用，不要误删（前端会传）。
- 智能客服（P0）遗留项见 `TODO.md`：真实玩家在线人数（mcstatus）、限流多 worker 共享存储、知识库自动定时任务（当前用 crontab）、检索效果看板等。
- **HTTPS 证书 2026-12-24 到期**（Let's Encrypt 通配符 `*.xt91tv.shop`，90 天一签）：到期未换证书 = **全站不可访问**。续期后替换 `/etc/nginx/ssl/` 下证书与私钥并 `nginx -s reload`，同时更新 `for-deploy/chaos-web.conf` 头部注释里的到期日期。
- 生产 Nginx 的 `/api/kb/` SSE 反代已按四件套配置（2026-09-21 起上线，2026-09-25 随 `/api` 前缀改造迁移）；生产改 nginx 时勿丢该 location。
