# 站内信功能需求规格说明书

> 版本：v1.0  
> 状态：草案  
> 最后更新：2026-10-07

---

## 1. 项目背景

当前站点没有统一的消息通知体系。用户收到回复、审核结果、系统公告时，缺乏集中、可追溯的查看入口。社区模块已承担了原公告模块的部分职能，是时候引入一站式的站内信系统，统一承载互动通知与系统公告。

## 2. 目标

- 提供统一的站内信收件箱，支持未读计数、状态标记、删除。
- 区分「定向互动通知」与「广播系统通知」两类消息，采用不同的已读与展示策略。
- 复用现有 Markdown 渲染管线与后台管理框架，最小化改造成本。
- 为后续「收到点赞」「评论详情展开」「头像上传」等功能预留扩展点。

## 3. 范围

### 3.1 本次包含

- 站内信收件箱页面（三个 Tab：回复我的、收到点赞、系统通知）。
- 头部导航栏未读消息入口与未读计数。
- 后台「站内信管理」页面（替代原公告管理）。
- 消息写入与异步补全的基础设施。
- 文章审核通过/驳回时的定向审核通知。
- 阵营内测审核通过/驳回时的定向审核通知。

### 3.2 本次不包含

- 「收到点赞」Tab（功能占位，后续迭代）。
- 评论详情展开（点击回复通知仅跳转到文章评论区，评论详情后做）。
- 头像上传（使用默认头像占位，上传功能延后到个人中心模块）。
- 消息推送实时通道（如 WebSocket / SSE 通知）。

## 4. 用户故事

| ID | 角色 | 需求 | 优先级 |
|---|---|---|---|
| US-01 | 登录用户 | 作为登录用户，我希望能看到未读消息总数，以便及时处理。 | P0 |
| US-02 | 登录用户 | 作为登录用户，我希望能查看「回复我的」列表，了解谁回复了我。 | P0 |
| US-03 | 登录用户 | 作为登录用户，我希望能查看「系统通知」列表，了解审核结果和系统公告。 | P0 |
| US-04 | 登录用户 | 作为登录用户，我希望能将消息标记为已读，避免重复提醒。 | P0 |
| US-05 | 登录用户 | 作为登录用户，我希望能删除「回复我的」消息，保持收件箱整洁。 | P0 |
| US-06 | 登录用户 | 作为登录用户，点击回复通知后，能跳转到对应文章的评论区。 | P0 |
| US-07 | 登录用户 | 作为登录用户，点击文章审核通知后，能跳转到对应文章。 | P0 |
| US-08 | 登录用户 | 作为登录用户，点击系统公告/活动公告后，抽屉展开正文内容。 | P0 |
| US-09 | 管理员 | 作为管理员，我希望能发布系统公告/活动公告，通知全体用户。 | P0 |
| US-10 | 管理员 | 作为管理员，我希望能审核文章，审核结果自动通知作者。 | P0 |
| US-11 | 管理员 | 作为管理员，系统公告/活动公告不支持删除，防止误删重要通知。 | P0 |
| US-12 | 管理员 | 作为管理员，编辑公告时不修改发布时间，保证时间线可追溯。 | P0 |

## 5. 信息架构

### 5.1 消息分类

```
messages
├── 定向消息（is_broadcast = 0）
│   ├── reply（回复我的）
│   ├── like（收到点赞）— 本次不生成，Tab 留待后续
│   ├── article_review（文章审核通知）
│   └── beta_review（阵营内测审核通知）
└── 广播消息（is_broadcast = 1）
    ├── system_announcement（系统公告）
    └── activity_announcement（活动公告）
```

> 审核通知（文章审核 / 阵营内测审核）为**定向消息**：仅通知发起审核的作者/申请人，不广播给全体用户。

### 5.2 前台展示结构

- **Tab 1：回复我的**（reply 定向消息）
  - 左侧：评论者默认头像
  - 标题：{nickname} 回复了我的评论
  - 回复内容：回复 @{targetNickname}：{content}
  - 被回复的内容：引用样式显示（Markdown `>` 块级引用）
  - 日期：当年显示月日，非当年显示年月日
  - 交互：点击跳转到对应文章的评论区

- **Tab 2：收到点赞**（like 定向消息）— **本次功能占位，不生成数据**

- **Tab 3：系统通知**
  - **子类型 A：系统公告 / 活动公告（广播消息）**
    - 左侧：通知图标
    - 分类标签：系统公告 / 活动公告
    - 标题：公告标题
    - 正文：Markdown 渲染（可选）
    - 日期：同年显示月日，非同年显示年月日
    - 交互：点击抽屉展开正文
    - 已读规则：进入列表即视为「可读」，点击后写入 `user_messages` 记录（`is_read = 1`）
  - **子类型 B：文章审核通知 / 阵营内测审核通知（定向消息）**
    - 左侧：通知图标
    - 分类标签：文章审核通知 / 阵营内测审核通知
    - 标题：根据分类动态生成（如「你的文章《xxx》审核通过」）
    - 正文：Markdown 渲染（可选）
    - 日期：同年显示月日，非同年显示年月日
    - 交互：点击跳转对应文章（文章审核）或对应申请页（阵营内测审核）
    - 已读规则：初始未读，点击后标记已读

### 5.3 未读计数规则

- **统计范围**：所有消息中用户尚未标记为已读的数量。
- **定向消息**（reply / article_review / beta_review）：创建时即插入 `user_messages`，`is_read = 0`，计入未读。
- **广播消息**（system_announcement / activity_announcement）：
  - 创建时**不预插** `user_messages`；
  - 用户进入「系统通知」Tab 时，对该用户尚未产生 `user_messages` 记录的广播消息，**批量插入** `user_messages` 记录（`is_read = 0`），这些消息随即计入未读计数；
  - 用户点击具体某条广播消息后，更新该条 `user_messages` 为 `is_read = 1`，该条从计数中移除。
- **已读判断**：
  - 定向消息：`user_messages.is_read = 1`
  - 广播消息：`user_messages` 中存在该消息的记录且 `is_read = 1`；不存在记录即视为未读。
- **软删除排除**：
  - `messages.is_deleted = 1` 的消息不参与任何列表查询与未读计数；
  - 用户删除定向消息时，同时标记 `messages.is_deleted = 1` 与 `user_messages.is_deleted = 1`。

## 6. 数据模型

### 6.1 messages（消息主表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| type | TEXT NOT NULL | 消息类型：reply / system_announcement / activity_announcement / article_review / beta_review |
| category | TEXT | 系统通知分类：system / activity / article_review / beta_review |
| title | TEXT NOT NULL | 标题 |
| content | TEXT | Markdown 正文（可选） |
| related_article_id | INTEGER | 关联文章 ID（回复通知 / 文章审核通知） |
| related_comment_id | INTEGER | 关联评论 ID（回复通知） |
| related_user_id | INTEGER | 关联用户 ID（审核通知：被通知的作者/申请人） |
| from_user_id | INTEGER | 触发者 ID（回复通知：谁回复的） |
| reply_content | TEXT | 回复内容（回复通知） |
| replied_comment_content | TEXT | 被回复的内容（回复通知） |
| is_broadcast | INTEGER DEFAULT 0 | 0=定向，1=广播 |
| is_deleted | INTEGER DEFAULT 0 | 0=正常，1=已删除（软删；广播消息由管理员操作，定向消息由接收用户操作） |
| status | INTEGER DEFAULT 1 | 0=草稿，1=已发布（仅广播消息有效） |
| created_at | TEXT NOT NULL | 创建时间（北京时间 ISO） |
| updated_at | TEXT NOT NULL | 更新时间（北京时间 ISO） |

### 6.2 user_messages（用户消息状态表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| user_id | INTEGER NOT NULL | 接收用户 ID |
| message_id | INTEGER NOT NULL | 关联消息 ID |
| is_read | INTEGER DEFAULT 0 | 0=未读，1=已读 |
| is_deleted | INTEGER DEFAULT 0 | 0=正常，1=已删除（软删） |
| created_at | TEXT NOT NULL | 创建时间 |
| updated_at | TEXT NOT NULL | 更新时间 |

- 唯一约束：`UNIQUE(user_id, message_id)`
- 定向消息创建时即插入 `user_messages`，`is_read = 0`（reply / article_review / beta_review）。
- 广播消息用户点击后插入 `user_messages`，`is_read = 1`（system_announcement / activity_announcement）。

### 6.3 tasks（通用任务表）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| type | TEXT NOT NULL | 任务类型：send_reply_notification |
| payload | TEXT NOT NULL | JSON 负载：`{comment_id, reply_id, ...}` |
| status | INTEGER DEFAULT 0 | 0=pending，1=processing，2=done，3=failed |
| retry_count | INTEGER DEFAULT 0 | 重试次数 |
| error_message | TEXT | 错误信息 |
| created_at | TEXT NOT NULL | 创建时间 |
| updated_at | TEXT NOT NULL | 更新时间 |

> 本表作为**通用任务模块**的初始版本，调度与执行均在独立 worker 进程中完成。后续新增任务类型（如消息推送、数据清理等）可直接复用该表。

## 7. 接口设计

### 7.1 前台接口

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/messages/unread-count` | 未读计数（含定向未读 + 广播未点击） | 登录 |
| GET | `/api/messages/replies` | 回复我的列表 | 登录 |
| GET | `/api/messages/likes` | 收到点赞列表（本次返回空数组） | 登录 |
| GET | `/api/messages/system` | 系统通知列表（含广播公告 + 定向审核通知） | 登录 |
| POST | `/api/messages/{id}/read` | 标记单条已读 | 登录 |
| POST | `/api/messages/read-all` | 批量标记已读 | 登录 |
| DELETE | `/api/messages/{id}` | 删除定向消息（软删：同时标记 messages.is_deleted = 1 与 user_messages.is_deleted = 1） | 登录 |

### 7.2 管理员接口

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/messages/admin/page` | 站内信管理分页（含草稿） | 管理员 |
| POST | `/api/messages/admin/create` | 创建站内信 | 管理员 |
| PUT | `/api/messages/admin/update/{id}` | 编辑站内信 | 管理员 |
| DELETE | `/api/messages/admin/delete/{id}` | 删除站内信（软删 messages.is_deleted = 1；系统公告/活动公告/审核通知均可删除） | 管理员 |

### 7.3 论坛模块内部触发

- 评论创建成功后，同步写入 `tasks` 一条 `send_reply_notification` 任务（payload 包含评论 ID）。

### 7.4 后台审核触发

- 文章审核通过/驳回时，创建 `article_review` 类型的定向消息（`is_broadcast = 0`），仅通知文章作者。
- 阵营内测审核通过/驳回时，创建 `beta_review` 类型的定向消息（`is_broadcast = 0`），仅通知申请人。

## 8. 前端设计

### 8.1 页面路由

- `/messages`：站内信收件箱（三个 Tab：回复我的、收到点赞、系统通知）。

### 8.2 导航栏

- 已登录状态下，导航栏站内信按钮显示未读角标。
- 点击按钮跳转 `/messages` 页面。
- 进入页面后自动拉取未读计数；**只有用户点击具体某条消息后，才标记该条为已读**。

### 8.3 列表项交互

| 消息类型 | 点击行为 |
|---|---|
| reply | 跳转到 `/forum/post/{related_article_id}`，路由 query 携带 `commentId={related_comment_id}` |
| article_review | 跳转到 `/forum/post/{related_article_id}` |
| beta_review | 跳转到 `/faction-beta`（或申请详情页） |
| system_announcement / activity_announcement | 抽屉展开正文（Markdown 渲染） |

### 8.4 删除

- **定向消息**（回复我的 / 审核通知）：
  - 用户点击删除按钮后，同时标记 `messages.is_deleted = 1` 与 `user_messages.is_deleted = 1`；
  - 删除后该消息对当前用户不可见，列表中不再展示。
- **广播消息**（系统公告 / 活动公告）：
  - 前台**不展示删除按钮**，禁止用户删除；
  - 仅管理员可在后台操作删除（软删 `messages.is_deleted = 1`），删除后全体用户均不可见。
- **收到点赞**Tab：本次占位，删除按钮后续补充。

## 9. 后台设计

### 9.1 页面改造

原「公告管理」页面改造为「站内信管理」页面，路由路径不变。

### 9.2 表单字段

| 字段 | 行为 |
|---|---|
| 标题 | 保留，必填 |
| 内容格式 | 只保留 Markdown，富文本置灰不可选 |
| 内容 | Markdown 编辑器，前端限制 200 字，超出提示 |
| 发布人 | **移除**，固定为 system |
| 发布时间 | **移除**编辑权限，保存时写入当前时间，编辑不修改 |
| 发布状态 | 保留（草稿/已发布），草稿不对外展示 |
| 分类 | 新增下拉选择：系统公告 / 活动公告（仅广播消息可选；审核通知由后台审核动作自动生成） |

### 9.3 列表操作

| 操作 | 行为 |
|---|---|
| 新建 | 路由跳转到编辑页 |
| 编辑 | 回显数据，发布时间置灰不可改 |
| 删除 | 系统公告/活动公告：管理员可删除（软删 messages.is_deleted = 1，全体用户不可见）；审核通知：管理员可删除 |

## 10. 异步处理

### 10.1 方案选择

采用 **方案 A：独立 Python CLI + crontab 定时轮询**。

- 与现有 `kb_sync.py`、`staff_expire.py`、`forum_purge.py` 口径一致。
- 生产 crontab 新增一条：
  ```
  * * * * * /usr/bin/docker exec announcement-backend python backend/message_worker.py >> /var/log/message_worker.log 2>&1
  ```

### 10.2 处理流程

```
定时触发（每分钟）
    ↓
SELECT * FROM tasks WHERE status = 0 ORDER BY created_at ASC LIMIT 10
    ↓
for task in tasks:
    UPDATE tasks SET status = 1 WHERE id = task.id
    try:
        process_task(task)
        UPDATE tasks SET status = 2 WHERE id = task.id
    except Exception as e:
        UPDATE tasks SET status = 3, error_message = e WHERE id = task.id
```

### 10.3 任务补全逻辑

- `send_reply_notification`：
  1. 根据 payload 中的评论 ID 查询评论内容、回复内容、文章 ID。
  2. 查询被回复者的用户信息（昵称）。
  3. 查询回复者的用户信息（昵称、头像）。
  4. 组装 `messages` 行 + `user_messages` 行（定向给被回复者）。

- `send_review_notification`（由后台审核动作同步触发，不经过 worker 任务表）：
  1. 文章审核：根据文章 ID 查询作者 ID，组装 `article_review` 类型的定向消息。
  2. 阵营内测审核：根据申请 ID 查询用户名，组装 `beta_review` 类型的定向消息。
  3. 直接写入 `messages` + `user_messages`（`is_read = 0`）。

## 11. 兼容性处理

| 原有模块 | 处理方式 |
|---|---|
| 前台 `/announcements` 页面 | **直接移除**，不再使用 |
| 前台 `/announcements/:id` 页面 | **直接移除**，不再使用 |
| 后台公告管理页 | **改造为站内信管理**，保留路由 `/announcement/list` 和 `/announcement/edit` |
| 原 `announcements` 表数据 | **迁移到 `messages` 表后删除旧表** |
| 旧接口 `/api/announcement/*` | 不再兼容，前端不再调用 |

## 12. 时间格式

- 统一存储北京时间 naive ISO 字符串：`YYYY-MM-DDTHH:MM:SS`。
- 前端解析避免使用 `new Date(iso)`（会被当作 UTC 解析），统一走项目内 `parseIso()` 工具函数。

## 13. 安全与性能

- 所有接口遵循统一响应包络 `{code, message, data}`。
- 布尔语义用 int（0/1），不用 bool。
- 匿名可打接口的数值入参必须有上界。
- 关系表插入/删除走原子 SQL，避免 read-modify-write。
- Worker 单次处理 10 条任务，防止单次轮询耗时过长。

## 14. 待办事项

| ID | 事项 | 优先级 | 备注 |
|---|---|---|---|
| TODO-01 | 收到点赞 Tab | P1 | 本次功能占位，后续迭代 |
| TODO-02 | 评论详情展开 | P1 | 点击回复通知仅跳转到文章页，评论详情报后期 |
| TODO-03 | 头像上传功能 | P2 | 延后到个人中心模块统一实现 |
| TODO-04 | 消息实时推送 | P2 | WebSocket / SSE 可选方案待评估 |
| TODO-05 | 消息搜索与筛选 | P3 | 支持按关键词、时间范围搜索 |

## 15. 里程碑

| 里程碑 | 内容 | 预计工期 |
|---|---|---|
| M1 | 数据模型迁移 + 后台站内信管理 | 2 天 |
| M2 | 前台收件箱页面 + 导航栏未读入口 | 2 天 |
| M3 | 回复通知触发链路 + Worker 异步补全 | 1 天 |
| M4 | 文章审核通知触发 + 联调 | 1 天 |
| M5 | 冒烟测试 + 生产部署 | 1 天 |

---

## 附录：术语表

| 术语 | 说明 |
|---|---|
| 定向消息 | 仅发送给特定用户的消息（如回复通知） |
| 广播消息 | 面向全体用户的消息（如系统公告） |
| 软删除 | 数据物理保留，通过 `is_deleted` 标记为不可见 |
| Worker | 独立 Python 脚本，定时从 `tasks` 消费待处理任务 |
| naive ISO | 不带时区后缀的北京时间字符串，如 `2026-10-07T14:30:00` |
