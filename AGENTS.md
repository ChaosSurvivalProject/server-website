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
- **⚠️ 字符串 `template` 组件在本项目**不会**渲染**：`frontend/vite.config.js` 没给 vue 配 `vue/dist/vue.esm-bundler.js` 别名，Vite 按 vue 的 `exports` 解析到的是**运行时版**（`vue.runtime.esm-bundler.js`，不含模板编译器）。用 `defineComponent({ template: \`...\` })` 写的组件 dev 下只有一行 "Component provided template option but runtime compilation is not supported" 警告、**渲染为空**，生产构建连警告都没有——表现为「点了按钮什么都没发生」。2026-10-03 论坛评论区「点回复没反应」就是这么来的（`ReplyForm` 曾是内联字符串模板），已抽成独立 SFC `frontend/src/components/forum/ReplyForm.vue`。**论坛/主站新增组件一律写独立 `.vue` 单文件组件**（模板由 `@vitejs/plugin-vue` 构建期编译），不要为了少建一个文件退回字符串 template，也不要为此给全站加 vue 全量构建别名（白白多打包一个编译器）。
- **子组件内部节点拿不到父组件的 scoped 样式**（Vue 只给子组件**根节点**补父组件 `data-v`）。所以评论列表与回复框共用的 `.cmt-act` / `.cmt-hint` / `.reply-to` 与整块 `.cmt-form-*` 都放在 `CommentSection.vue` 的**非 scoped** `<style>` 里，只定义一份；把共用类写进 `scoped` 块会让回复框里的「取消」按钮、字数提示失去样式。
- **模板里直接挂事件处理函数时，Vue 会把事件对象当第一个参数传进去**。`@keydown.enter="addTag"` 会让 `addTag(name)` 收到 **KeyboardEvent**，若函数里写 `(name ?? this.tagInput).trim()` 就会对事件对象调 `.trim()` 抛 TypeError，表现为"回车没反应"且控制台无提示。要区分"传字符串的调用方"（`@click="addTag(t.name)"`）就得加类型守卫：`typeof name === "string" ? name : this.tagInput`。**点建议标签（传字符串）与键盘回车（传事件）是同一函数的两类调用方**。
- **发帖/编辑页的 Markdown 编辑器与后台公告编辑器同款**（同一个 `md-editor-v3`、同款 `mdToolbars` 数组、默认左编辑右预览分屏，`:sanitize` 接本项目的 `sanitizeHtml`）。改工具栏要**两边同步**（`admin-frontend/src/views/announcement/edit.vue` 的 `mdToolbars` 与 `frontend/src/views/forum/PostEditor.vue` 的同名 computed）。注意 v7 的输入区是 CodeMirror 6（`.cm-content` contenteditable，**没有 textarea**），自动化测试要按这个选器。
- **时间解析不要用 `new Date(iso)`**：库里存的是**北京时间 naive ISO 串**，`new Date("2026-09-27T10:00:00")` 会当 UTC 解析再换算，显示会偏 8 小时。统一走 `frontend/src/utils/forumFormat.js` 的 `parseIso()`（手工拆字段构本地 Date）。同理 `_is_muted()` 里 `datetime.now(_TZ)` 带 tzinfo，与解析出的 naive 值比较前必须 `.replace(tzinfo=None)`，否则抛 `can't compare offset-naive and offset-aware datetimes`（踩过）。
- **禁言（`users.mute_until`）与 `status` 三态正交**：禁用=不能登录，禁言=能登录浏览但不能发帖/评论。判定在写操作依赖 `_ensure_not_muted()`（读操作不受限），返回 403 + `detail="账号已被禁言，至 <时间>"`。**点赞/收藏不属"发言"，禁言期间仍可用**——这是有意的，别顺手一起禁。
- **「首页/推荐」是两个系统板块**（`is_system=1`）：`home`=全部已发布，`recommend`=`is_featured=1 OR is_top=1` 且固定按 `view_count` 倒序。系统板块后台**不可删、不可改名、不可隐藏**；文章**禁止投稿到系统板块**（后端创建/修改时校验 400）。
- **置顶帖在任意排序档中都恒排最前**（`ORDER BY is_top DESC, <排序列> DESC`），不是只有默认排序才置顶。
- **⚙️ 帖子删除与回收站（`docs/论坛/论坛删除与回收站PRD.md` v1.3，2026-10-05 上线）**：
  - **作者删除帖子 = 进回收站（`status=4` + `deleted_at`），不是物理删、也不再产生 `status=3`**——`status=3` 此后只有"管理员下架"一个来源。删除 / 恢复**统一走 `_set_article_status()`**，标签 `use_count` 仍只挂"进入/离开 `status=1`"这一个转移点（彻底删除时因已是 4，天然不会重复扣减）。回收站帖**对所有人 404（含作者本人）**：详情 / 评论列表 / 点赞 / 收藏 / 评论 / 浏览全封，彻底删除只有 `DELETE /api/forum/articles/{id}/purge` 一条路。
  - **30 天保留期的唯一权威是 `deleted_at`**（不是 `status`、更不是 crontab）：恢复接口自校验（超期 **410**）、回收站列表自过滤、`backend/forum_purge.py` 清理共用同一口径。恢复目标 = `status_before_delete`（0/1/2，**不重审**），并回填 `publish_time_before_delete`——不回填则"删除→恢复"两次点击就能零成本刷排行榜。**crontab 漏挂不影响正确性**（超期帖用户看不到也恢复不了，只是数据多留几天），与员工名片 `valid_to` 同款口径。
  - **评论删除：作者侧物理删（不留痕）/ 后台软删（`status=2` 留治理痕迹）——有意不对称，别顺手统一成一种**（回收站 PRD §0.4-J / §6-D7，实现注释在 `forum.py` 模块头）。作者删顶层评论**连带其下全部回复物理删除（含他人回复）**，确认弹窗必须写明"该评论下的 N 条回复将一并删除"；后台删评论仍是软删。**禁言用户仍可删自己的内容**（删除不属"发言"，与"禁言期间点赞/收藏仍可用"同属例外）。
  - `GET /api/forum/my/articles?status=4` 是回收站列表的取数口（额外下发 `deletedAt` / `daysLeft` / `statusBeforeDelete`，**不含正文**）；**不做回收站正文预览**——要看内容先恢复（恢复零风险）。删除不清理 `uploads/forum/` 里的图片（图床冗余清理属第三阶段）。
  - **⚠️ 后台回收站筛选尚未实现**（回收站 PRD §5 第 9 项未落地，已登记 `TODO.md`）：`GET /api/forum/admin/articles` 的 `status` 参数与 `admin/articles/{id}/restore` 后端**都已支持 `4`**，但后台文章管理页的状态下拉只有 0/1/2/3，因此后台目前筛不出也操作不了回收站帖。
- **第一阶段有意不做**（顺延第二/三阶段，已登记 `TODO.md`，勿当缺陷补齐）：站内信、关注/粉丝（`followerCount` 恒 0）、打赏、等级/头衔、评论审核队列与敏感词、文章版本记录、回复折叠、回复通知、统计定时任务、全文检索、图床冗余清理、富文本。对应位置只留 UI 占位（统一走 `showForumToast()` 提示"功能开发中"，**不跳转不请求**），配置键 `forum_config.reward*` 预留但无 UI。（**"评论作者自删"已由回收站 PRD 提前实现**，只剩评论**编辑**未定，见 `TODO.md`。）
- **Banner 配图整幅铺满**：配了 `bannerImage` 就 `position:absolute; inset:0` 铺满整个横幅，`object-fit:cover` + `object-position:center`（溢出**居中裁剪**、**不拉伸**），z-index 依次为 图 0 → 压暗蒙版 1 → 文字 2 → 底部操作条 3。三条要一起写：只写 `cover` 会在偏心位置裁切，只写 `width/height:100%` 会拉伸变形。配图可能很亮，蒙版只做白字可读性保障（`background:linear-gradient(100deg, rgba(15,23,42,.62) …)`）；配图 404 时要用**响应式开关**（`artBroken`）而不是 `display:none`，才能把与它是兄弟节点的蒙版一起撤掉，否则纯渐变底上会蒙一层灰。
- **徽章只有"管理员"一种**（依据 `users.role`）：常量化在 `frontend/src/utils/forumBadges.js`（后台同名表保持一致），**不要在多个组件里硬编码颜色**；依据文档示例的"炽热行者""VIP"等等级头衔属第二阶段，不得以假数据填充。
- 论坛页面样式令牌与 Markdown 正文排版在 `frontend/src/assets/styles/forum.css`（全局，8 个公共组件共用）；类名一律 `fx-` 前缀，因为全站 `App.vue` 有像素风的全局 `.btn`，不加前缀会互相串味。
- **全站统一导航栏**：任何路由都显示 `NavBar`（含论坛的详情 / 发帖 / 编辑 / 我的文章四页）。不要再引入 `meta.hideNav` 之类的按路由隐藏机制——2026-09-27 已按需求移除，页面内用「← 返回社区」提供上下文即可。
- 端到端回归：`backend/forum_smoke_test.py`（`python3 forum_smoke_test.py`，用临时库 + `TestClient`，覆盖状态机/计数/权限/级联等 176 项断言）。改论坛后端先跑它。


## 游戏服务器地址：单一数据源

- 游戏服务器地址持久化在 SQLite `servers` 表（**DB 为唯一权威**）；`backend/app/monitor.py` 的内存 `SERVERS` 字典只是读缓存，启动时 `load_servers()` 从库加载（表空时用文件内默认注册表做种子）。后台「服务器地址管理」页经 admin 接口增删改（先改内存再同步落库，失败回滚内存）。
- **禁止在前端硬编码服务器地址**；前端一律通过 `GET /api/monitor/servers` 获取（env 里只保留监控接口所需的 `VITE_SERVER_ID`，经 `mc-config.js` 暴露为 `server.id`）。
- 新增/修改服务器 = 后台管理页操作或调 admin 接口（持久化）；不要再改代码里的注册表。

## 后台管理菜单规约（admin-frontend）

- 侧边菜单**一级即功能模块**，路由静态写在 `admin-frontend/src/router/modules/home.ts`（默认导出**数组**）：`/` 只作 Layout 外壳（`showLink: false` + `children: []`，不占菜单），其余顶级记录是模块——`/content` 内容运营、`/community` 社区管理、`/staff` 员工管理、`/kb` 智能客服、`/system` 系统管理，页面（含 `showLink: false` 的编辑页）挂各自 `children` 下。**新增页面挂到对应模块里，不要新增一级菜单**；只有新增功能模块才加顶级记录，模块顺序由顶级 `meta.rank` 决定（`ascending()` 只排同级、不递归子级，模块内页面顺序 = 数组顺序）。
- pure-admin 的 `formatTwoStageRoutes()` 会把三级及以上路由**拍平成二级**，模块记录因此没有组件：**每个模块必须写 `redirect` 指向本模块第一个页面**，否则手输 `#/content` 命中无组件记录 → 渲染空白；模块下只有 1 个页面时要在该页 `meta.showParent = true`，否则 `SidebarItem` 会把模块拍成单个菜单项、模块名丢失（智能客服就是这种情况）。
- 改完菜单别只看代码：这几个函数会重排/改写路由，验证方式是「导入真实 `home.ts` → 跑 `ascending` / `formatFlatteningRoutes` / `formatTwoStageRoutes` → `createRouter` 后逐个 `router.resolve(路径)`」，确认每个页面 `matched` 仍是 `[ /, 页面 ]` 且页面记录带组件（拍平后模块记录不参与匹配，页面靠绝对路径直达）。

## 前端配置规约

- 主站配置一律走 Vite 环境变量（`VITE_` 前缀）：`frontend/.env` 存所有模式共用的默认值（QQ 群、服务器 id、版本文案、后台入口等），`.env.development` / `.env.production` 按构建模式覆盖（dev → 本地 5000，build → 同源）；本地个性化覆盖写 `.env.local`（根 `.gitignore` 的 `*.local` 已忽略）。**三个 `.env` 文件随仓库提交，禁止在组件里直接读 `import.meta.env` 或在别处硬编码这些值**。
- `frontend/src/config/mc-config.js` 只是环境变量的统一读取层（含类型转换），**不要在其中硬编码站点值**；组件一律 `import McConfig` 取值。
- 生产环境 API 走同源（`VITE_BASE_API_URL` 留空 → `baseApiURL: ''`），依赖 Nginx 反代 `/api` 到本机 FastAPI（:5000）。
- 环境变量是构建期静态替换，改 `.env*` 后需重启 dev server / 重新 build 才生效。
- 模板中引用的静态图片必须先 `import` 再绑定 `:src`（如 `Home.vue` 的 `bbs-*.png`、`video-bg.jpg`）；**禁止直接写 `/src/...` 绝对路径**——Vite build 不会打包该路径，生产环境会 404（dev 下看不出来）。

## Wiki 规约

- VitePress `base: '/wiki'` + `cleanUrls: true`。站内链接写相对路径（VitePress 自动加 base）；**外链必须带协议**（`http(s)://`），否则会被加上 `/wiki` 前缀。
- 内容分三大分区，新增页面放对应分区并在 `.vitepress/config.mts` 侧边栏登记：`for-new/`（萌新指南）、`management/`（服务器管理）、`develop/`（服务器建设）。
- 站点外链域名（2026-10-03 起）：官网为 `https://xqly.xt91tv.shop`（HTTPS 标准 443，明文 HTTP 已禁；旧部署的 `:23333` 非标端口已随换服务器废弃）。wiki 内指向官网的外链（hero「访问官网」按钮、阵营文档申请入口等）统一写此地址，不要再写死 IP。

## Git 规约

- 远程：`git@github.com:ChaosSurvivalProject/server-website.git`，主分支 `main`。
- 提交信息使用 Conventional Commits 前缀（`feat` / `fix` / `refactor` 等，可带 scope 如 `feat(backend):`），描述用中文。

## 文档归档口径

- `TODO.md` **只留未完成项与后续计划**：清单/上线项收口后整段搬到 `docs/归档/已完成清单.md`（按完成时间倒序），并在 `TODO.md` 留一行指向归档的链接；只有**仍有未完成条目**的清单才在 `TODO.md` 保留一个收尾小节（如「换服务器重新部署：待人工收尾」）。
- 归档只搬清单本身：技术决策与规约仍写在 `AGENTS.md` / `README.md` / 各模块方案文档里，**不要往归档文件里新增规约**。换服务器、改端口这类使历史值失效的变更，在归档条目上补一句注记（如二维码前缀 `:23333` → 443），**不要静默改写历史记录**。

## 部署拓扑（生产）

**生产对外地址：`https://xqly.xt91tv.shop`**（2026-10-03 换服务器后启用，标准 443）。旧站是裸机 nginx + NAT 外部 23333 → 内部 80 且 nginx 在 80 上直接跑 SSL，**那套拓扑已废弃**；现在由 1panel 托管，nginx 是 1panel 的 OpenResty 容器（**host 网络**，监听 80/443），证书用 1panel「SSL」里导入的通配符证书下发给站点。

- 仓库路径 `/opt/xqly-website`；后端容器 `announcement-backend`（`docker compose` 定义在仓库 `backend/docker-compose.yml`，**只绑 `127.0.0.1:5000`**——发布到 `0.0.0.0` 会被 Docker 的 iptables 规则绕过 ufw 直接把 API 暴露到公网）。
- 站点是 1panel「静态网站」，站点根 `/opt/1panel/www/sites/xqly.xt91tv.shop/index`，三个前端产物都投放在这里（`admin/`、`wiki/` 为子目录，与 SPA 的 `index.html` 共存）。
- **cookie/凭据类文件只在服务器上**：`backend/.env`（已 gitignore，含 API Key）以只读卷挂进容器（`./.env:/app/backend/.env:ro`），wiki 源码以 `../wiki:/app/wiki:ro` 挂入供 `kb_sync.py` 读取（`KB_WIKI_DIR=/app/wiki`）。

**⚠️ 1panel 的「静态网站」模板不生成 `try_files` 兜底、也不生成 `include proxy/*.conf`**，这两样是上线时手工补进 `/opt/1panel/www/conf.d/xqly.xt91tv.shop.conf` 的。**在面板里改动该站点的网站设置会重新生成这个文件，手工补的东西会丢**（症状：深层路由 404 + `/api` 全部 502）——改完必须回服务器核对 `grep -n 'proxy/\*\.conf'`。自定义 location 全部放在 `/opt/1panel/www/sites/xqly.xt91tv.shop/proxy/xqly-app.conf`。

生产 nginx 配置留档：`for-deploy/xqly.xt91tv.shop.conf`（面板生成的 server 块，含那行 `include`）+ `for-deploy/xqly-app.conf`（手工维护的应用 location），**与线上字节一致**，改 conf 前先读 `for-deploy/README.md`。

同域单入口，Nginx 统一分发：

- `/` → `frontend` 构建产物（SPA 使用 history 路由，**`try_files $uri $uri/ /index.html;` 由 `xqly-app.conf` 提供**；`/announcements` 等深层路由刷新、扫码直达 `/staff/xxx`、`/team`、`/forum/...` 都依赖它，改动时勿删）
- `/api` → 反代到本机 FastAPI（`127.0.0.1:5000`，后端所有接口统一挂 `/api` 前缀）；其中 `/api/kb/` 的反代必须为 SSE 追加 `proxy_buffering off` + `proxy_http_version 1.1` + `proxy_set_header Connection ''` + `gzip off`（与后端 `X-Accel-Buffering: no` 两个都要，否则流式变一次性返回）
- 兼容旧路径（勿删）：`/health` → 反代 FastAPI（外部监控/旧部署门禁在用）；`/announcement/uploads/` → 反代 FastAPI（历史公告正文内嵌的旧图片 URL，存量数据兼容）
- `/wiki/` → `wiki` 构建产物（VitePress 已按 `/wiki` base 打包，cleanUrls 靠 `try_files $uri $uri.html $uri/ =404`）
- `/admin/` → `admin-frontend` 构建产物（pure-admin-thin，已按 `/admin/` base 打包）

**新增 `location` 前缀时不得与前端页面路由同名**：`location /staff` 会把 SPA 的 `/staff/:code` 一并反代走，页面再也进不去，而 dev 直连后端看不出问题。统一 `/api` 之后新模块已不需要单独加 `location`，正常不会再触发；真要加，前缀与页面路由错开（如曾考虑过的复数前缀）。旧裸机 conf 里 `location = /faction-beta { try_files /index.html =404; }` 就是历史上处理这类同名的补丁，新版 `xqly-app.conf` 已不再需要它。

**前端产物在本机构建后投放，服务器上不跑 Vite**：生产机内存只剩 ~1GB 且与 MySQL/Redis/halo/napcat 等同机，Vite 构建峰值会 OOM 连坐。构建命令与投放位置见 `for-deploy/README.md`「前端产物从哪来」。

后端 Docker 部署注意：`docker-compose.yml` 位于 `backend/` 下，但**构建上下文是项目根目录**（`context: ..`），Dockerfile 里必须写 `COPY backend/requirements.txt .`（写 `requirements.txt` 会 `not found`，2026-10-03 修过）；根目录 `.dockerignore` 负责把 `node_modules`/`dist`/`.git` 挡在 context 之外。**任何 `docker-compose.yml` / `Dockerfile` 改动都要 `docker compose up -d --build` 重新构建**。

### 生产定时任务（root crontab）

生产**只有 crontab 一种定时机制**（无 celery / APScheduler / systemd timer），知识库 / 名片到期 / 论坛回收站超期清理三条链路都通过 `docker exec` 在容器内执行：

- `0 3 * * *` → `/usr/bin/docker exec announcement-backend python backend/kb_sync.py --incremental >> /var/log/kb_sync.log 2>&1`（wiki 改动按 MD5 入库，自增 `index_version`，后端免重启）
- `0 4 * * *` → `/usr/bin/docker exec announcement-backend python backend/staff_expire.py >> /var/log/staff_expire.log 2>&1`（**漏挂不影响核验正确性**，`valid_to` 权威 + 查询时懒更新兜底，只影响台账刷新时效）
- `0 5 * * *` → `/usr/bin/docker exec announcement-backend python backend/forum_purge.py >> /var/log/forum_purge.log 2>&1`（物理清除超 30 天的回收站帖；**漏挂不影响正确性**，`deleted_at` 权威 + 恢复接口自校验 + 列表自过滤，只是数据多留几天）

条目里用 `/usr/bin/docker` 绝对路径（cron 用 `/bin/sh` 且不加载交互式环境，PATH 里未必有 docker）。改 crontab 前先 `crontab -l > /root/crontab.bak-YYYYMMDD` 备份，再 `crontab <文件>` 安装（**勿直接改 `/var/spool/cron/crontabs/root`**，务必走 `crontab` 命令）。三条任务**都是 0 变更空跑安全**（kb_sync 无变更不动 `index_version`、forum_purge 无超期帖不写库），漏跑不会写坏数据——但漏挂 `kb_sync` 会导致 wiki 新页面不进知识库，客服对未同步内容直接答不上来。**完整条目快照留档在 `for-deploy/crontab`，改法与验证命令见 `for-deploy/README.md`「改定时任务」节**。

## for-deploy 留档目录

- `for-deploy/` 存放生产实际生效、但不属于任何子项目构建产物的配置留档（当前三个：`xqly.xt91tv.shop.conf` = 1panel 站点配置快照、`xqly-app.conf` = 应用 location 快照、`crontab` = root crontab 快照；均为**与生产字节一致**的快照，可 `md5sum` 比对，改完后须回拷留档；同步方法与改前注意事项见该目录 `README.md`）。
- **该目录随仓库提交到公开仓库，禁止放任何敏感信息**：SSL 证书/私钥、API Key、密码/token/JWT secret、生产数据库数据等一律不进；普通配置里如无必要也不要写外部 IP/端口。敏感文件（证书、`backend/.env`、生产库）只存在于服务器对应路径，不落仓库。

## 已知遗留 / 注意事项

- 后端 CORS 当前 `allow_origins=["*"]`（开发便利），生产收紧时需与同源部署方案一起评估。
- `backend/app/monitor.py` 中 `server-info` 的 `start_time` / `end_time` / `time_period` 参数是预留参数，当前实现未使用，不要误删（前端会传）。
- 智能客服（P0）遗留项见 `TODO.md`：真实玩家在线人数（mcstatus）、限流多 worker 共享存储、知识库自动定时任务（当前用 crontab）、检索效果看板等。
- **HTTPS 证书 2026-12-24 到期**（Let's Encrypt 通配符 `*.xt91tv.shop`，90 天一签）：到期未换证书 = **全站不可访问**。现在证书由 1panel「SSL」管理并下发给站点 `/opt/1panel/www/sites/xqly.xt91tv.shop/ssl/`，续期后在面板里替换该证书再重载 OpenResty 即可；**旧的裸机路径 `/etc/nginx/ssl/` 已不存在**。
- 生产 Nginx 的 `/api/kb/` SSE 反代已按四件套配置，现位于 `for-deploy/xqly-app.conf`（1panel 站点通过 `include .../proxy/*.conf` 引入）；生产改 nginx 时勿丢该 location。
