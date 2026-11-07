# 主站前端（frontend）

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 原样下沉的专题文档（内容未改动，仅调整标题层级与文内交叉引用）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

## 页面与路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | Home | 首页：hero 横幅、服务器特色、加入服务器（地址来自 `/monitor/servers`）、论坛展示、在线状态 |
| `/announcements` | Announcements | 公告列表（分页） |
| `/announcements/:id` | AnnouncementDetail | 公告详情（自动累加阅读量） |
| `/faction-beta` | FactionBetaApply | 阵营对战玩法内测资格申请（需登录后填写，展示审核状态） |
| `/staff/:code` | StaffVerify | 工作人员名片验证页（扫码直达；四态横幅 + 防伪提示，正文不显示完整身份码） |
| `/team` | TeamOverview | 管理组总览（公开的现任名录 + 官方入口 + 安全提示） |
| `/forum` | forum/CommunityHome | 社区首页（双栏 7:3；Banner + 板块标签 + 排序/搜索 + 帖子列表 + 右侧三卡；筛选态全部走 `route.query`） |
| `/forum/post/:id` | forum/PostDetail | 文章详情（顶部「← 返回社区」+ 全局导航栏；Markdown 渲染 + 点赞/收藏/分享 + 两级评论区 + 作者卡） |
| `/forum/new` | forum/PostEditor | 发布文章（与编辑页复用同一组件；md-editor-v3 分屏编辑器；本地草稿防丢失） |
| `/forum/edit/:id` | forum/PostEditor | 编辑文章（`mode=edit`；**仅作者本人**，保存后回待审核重走审核） |
| `/forum/my` | forum/MyPosts | 我的文章（各状态 + 驳回理由 + 编辑重提 + 删除进回收站 + 入口「查看已删除文章」） |
| `/forum/recycle` | forum/RecycleBin | 回收站（保留期与剩余天数、逐条恢复 / 彻底删除；不可恢复的删除一律二次确认） |
| `/login` | AuthView（登录） | 登录页（用户名/邮箱 + 密码） |
| `/register` | AuthView（注册） | 注册页（邮箱 + 密码 + 确认密码 + 滑块拼图人机验证） |

## Markdown 渲染（`src/utils/markdown.js`）

全站**唯一**的 Markdown 渲染入口（marked + DOMPurify + highlight.js）。代码块底色统一浅色 `#f6f8fa`（基准 = 公告详情），主站与后台的规则分别在 `frontend/src/assets/styles/markdown.css` 与 `admin-frontend/src/assets/styles/markdown.css`，**改代码块观感只改这两个文件**：公告正文与社区文章正文都走它。导出 `renderMarkdownContent(content)`（纯 Markdown，社区用）与 `renderAnnouncementContent(content, contentType)`（按格式分支，公告详情页用），另有 `splitMarkdownBlocks(text)`（智能客服流式渲染用）。**不要另写一套渲染管线**。

## 关键组件

- `NavBar` — 顶部导航栏
- `ChatWidget` — 智能客服悬浮组件（流式打字机、思考过程折叠、来源引用、QQ 群引导；块级 keyed 流式渲染）
- `OnlineCounter` — 服务器在线状态（轮询 `/monitor/server-info/{id}`）
- `Leaderboard` / `TrendChart` — 排行榜与趋势图（ECharts）
- `ContentCard` / `ImageCarousel` / `SectionNav` / `CopyButton` / `BackToTop` / `Modal` — 展示与交互组件
- `components/forum/` — 社区组件（props 驱动，后续阶段只扩 props 不改结构）：`PostCard`（帖子卡片）/ `CategoryTabs`（板块标签栏）/ `CommunityBanner`（Banner + 排序/搜索）/ `SidebarUserCard` + `SidebarStats` + `SidebarHotTags`（右侧三卡）/ `CommentSection`（两级评论区，自取数据）/ `AuthorCard`（作者卡）/ `Pager`（翻页）/ `UserBadge`（徽章）/ `ConfirmDialog`（二次确认）/ `ForumToast`（占位功能轻提示）
- `utils/forumFormat.js`（相对时间 / 北京时间解析 / HTML 转义）、`utils/forumBadges.js`（徽章与状态常量表）、`utils/forumToast.js`（轻提示单例 + 未登录跳转）

## API 层（`src/api/`）

- `axiosInstance.js` — axios 实例，baseURL 来自环境变量 `VITE_BASE_API_URL`（经 `mc-config.js` 统一读取）；响应拦截器统一解包 `{code, message, data}`，失败时弹出错误提示；请求拦截器自动携带 JWT，401 时清除登录态并跳转 `/login`
- `api.js` — 接口封装：`authAPI` / `announcementAPI` / `factionBetaAPI` / `forumAPI`（社区）/ `staffAPI`（验证页与总览页的公开只读接口，silent 模式） / `serverMonitorAPI` / `serverConfigAPI` / `chatAPI`（`chatAPI.streamChat` 因 SSE 流式改用 `fetch` + `ReadableStream`，其余走 axios）
- `errorHandler.js` — 统一错误弹窗工具
