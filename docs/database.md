# 数据库

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 原样下沉的专题文档（内容未改动，仅调整标题层级与文内交叉引用）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

使用 SQLite：

- 默认路径：`backend/data/announcements.db`（启动时自动建表）
- 可通过环境变量 `ANNOUNCEMENT_DB` 自定义
- **连接池用 `NullPool`（每请求一条连接），不要改回 `StaticPool`**：单连接会让并发请求共享同一个事务，导致社区论坛的原子计数（点赞/评论/标签 `use_count`）与关系表对不上。连接级 PRAGMA（`busy_timeout` / `synchronous`）挂在 engine 的 `connect` 事件上，`journal_mode=WAL` 在 `init_db()` 设一次。详见 [docs/agents/forum.md](./agents/forum.md)。

公告正文支持两种格式（`contentType` 字段区分，存量数据自动归为 `html`）：

- `html`：富文本编辑器（wangEditor）产出的 HTML，入库前由后端 `nh3` 白名单消毒（仅放行常用标签 + `style` 内联样式）。
- `markdown`：Markdown 源码，原样入库（nh3 会破坏 Markdown 语法），由前端渲染——主站用 `marked` + `DOMPurify` 消毒后展示，后台编辑器为 md-editor-v3（双编辑器共存，按格式自动切换）。

社区（论坛）模块的 9 张表由 `Base.metadata.create_all` 自动建，存量表补列由 4 个幂等迁移函数在 `init_db()` 里完成（`migrate_user_extra_columns()` / `migrate_announcement_content_columns()` / `migrate_user_mute_column()` / `migrate_forum_article_recycle_columns()`，失败只记 warning、不阻断启动）。其中回收站迁移会补 `forum_articles` 三列，并把旧语义的作者自删帖（`status=3 AND remove_by='author'`）刷成 `status=4` + `deleted_at=update_time`：

| 表 | 用途 |
|----|------|
| `forum_categories` | 板块（2 个系统板块 `home`/`recommend` 不可删改名隐藏） |
| `forum_tags` | 标签（`use_count` = 被已发布文章引用数） |
| `forum_articles` | 文章（`status` 0待审核/1已发布/2已驳回/3已下架(管理员)/4回收站；`remove_by` + `resubmit_count` + 回收站三列 `deleted_at`/`status_before_delete`/`publish_time_before_delete`） |
| `forum_comments` | 评论（`parent_id` 只指向顶层评论；两级楼中楼） |
| `forum_article_likes` / `forum_article_favorites` / `forum_comment_likes` | 点赞与收藏关系（`(x, user_id)` 联合唯一，切换语义） |
| `forum_article_tags` | 文章—标签关联（不用逗号串，否则合并/重命名/删除会写坏数据） |
| `forum_config` | 社区键值配置（Banner / 排序 / 搜索文案 + 打赏预留键） |

首次启动自动写入**8 个预置板块**与 8 个配置键默认值（`forum.ensure_seeded()`，幂等：按 `code`/`key` 判存，不会覆盖管理员改过的值）。

资源中心模块的 7 张表同样由 `Base.metadata.create_all` 自动建（资源中心一阶段 MVP，2026-11-08）：

| 表 | 用途 |
|----|------|
| `dict_items` | 字典（资源类型/平台/游戏版本/侧别/渠道/标签；预置 24 项种子幂等写入，`(type, key)` 唯一，停用用 `enabled=0`） |
| `resources` | 资源主表（`slug` 唯一；`status` draft/published/hidden/archived 字符串枚举；`deleted_at` 软删；`download_count` 冗余计数与事件同事务维护） |
| `resource_platforms` / `resource_game_versions` / `resource_tags` | 资源—字典 key 关联（联合唯一，列表筛选用，子查询 IN 天然去重） |
| `resource_versions` | 版本（`(resource_id, version)` 唯一；`is_latest_stable` 每资源≤1，唯一转移点 `_set_latest_stable`；`game_versions`/`platforms` 存 JSON 数组） |
| `version_assets` | 下载资产（URL 必须 `https://github.com/` 开头；`is_primary` 每版本≤1） |
| `download_events` | 下载跳转事件（一次有效跳转一行；**不存原始 IP**，只存 sha256 截 16 位 `ip_hash`） |
