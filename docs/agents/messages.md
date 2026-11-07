# 站内信模块规约

> 本文是 [AGENTS.md](../../AGENTS.md) 对应规约小节的完整原文（2026-11-07 文档重构时下沉，内容未改动）；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

实施依据：`docs/站内信/站内信功能PRD.md`（v1.1，含「收到点赞」Tab）。消息主表 `messages` + 用户状态表 `user_messages`；**定向消息**（reply / like / article_review / beta_review）创建时即插 `user_messages`（`is_read=0`），**广播消息**（system_announcement / activity_announcement）进入「系统通知」Tab 时才批量补插、点击后置已读。

- **前台展示名叫「消息中心」，模块/接口/文档仍叫站内信**（2026-10-09 定）：用户可见的只有两处——`Messages.vue` 弹窗头部（圆角矩形浅绿底消息图标 `fa-regular fa-comment-dots`，`align-items: stretch` 让图标高度覆盖「消息中心」标题 + 未读副标题；副标题为全局未读口径「当前有 N 条未读消息 / 当前无未读消息」，与导航栏角标同源）与 `NavBar.vue` 铃铛按钮的 `title` / `aria-label`。后台管理端仍是「站内信管理」，`/api/messages/*` 路径与 `messages` / `user_messages` 表名不动——别把模块也改名，那会牵动 API 契约和后台菜单。

- **点赞通知的触发点只有两个**（`backend/app/forum.py` 的 `toggle_article_like` / `toggle_comment_like`），且必须同时满足三条才发：`delta == 1`（新增点赞，取消不触发）、非作者自赞、同一点赞者对同一内容（`from_user_id + related_article_id + related_comment_id`）没有未删除的旧通知（去重，防「赞→取消→再赞」刷屏）。实现是 `messages.py::create_like_message()`，**forum 里只写触发、 messages 里只写一份创建逻辑**，与回复通知同口径：通知失败 try/except 兜底，绝不影响点赞主流程（禁言期间点赞仍可用，通知照发）。
- **点赞通知内容是快照不是引用**：文章点赞存文章标题（带书名号《》），评论点赞存评论正文（回复类带 `回复 @{被回复者昵称}：` 前缀，与评论区展示口径一致）。文章后来被改名/删除都不影响已发通知——这与回复通知一致，别改成"跳转时实时查"。
- **定向消息的已读/删除仅接收者本人可操作**（`crud.py::mark_message_read` / `delete_user_message` 均校验 `user_messages` 归属）：`messages.is_deleted` 是**全局标记**，不校验归属就等于任意登录用户凭 ID 删掉别人的收件箱内容；他人操作返回 404/400。广播消息不受此限（补插即已读是设计语义）。
- **`mark_all_read` 的 `msg_type` 与 Tab 一一对应**（reply / like / system，缺省=全部定向）：新增 Tab 时必须同步补分支，否则「全部已读」会静默漏掉该类。前台 `Messages.vue` 的 tabs / load / loadAllTabUnread / handleClick / handleMarkAllRead 五处都要带 like，后台 `announcement/list.vue` 的类型筛选与 `typeLabel` 同步补「收到点赞」。
- 点赞通知计入未读总数（定向未读口径天然覆盖，无需特判）；前台点击跳 `/forum/post/{articleId}`，评论点赞额外带 `?commentId=` 定位。
