# 服务器架构总览

本页面向玩家与建设者介绍星穹旅驿现有的技术架构。游戏服务器地址的权威数据源是官网后端的监控接口（`GET /monitor/servers`），官网与 Wiki 展示的地址始终以它为准。

## 游戏服务器

| 项目 | 说明 |
| --- | --- |
| 服务端核心 | Purpur 1.21.11（Paper 系高性能核心，Minecraft 1.21.11） |
| 主服务器地址 | `serverone.codeyun.com:12000` |
| Java 版多版本 | ViaVersion + ViaBackwards：新旧版本客户端均可进入 |
| 基岩版互通 | Geyser + Floodgate：基岩版（移动端）与 Java 版同服游玩 |

## 插件矩阵

### 玩法插件

| 插件 | 说明 |
| --- | --- |
| ImprovedFactions | 阵营玩法核心（`/f` 指令体系），支撑黎明誓约 / 暮夜同盟对抗玩法 |
| KaMenu | 服务器菜单系统，常用功能图形化直达 |

### 基础与运维插件

| 插件 | 说明 |
| --- | --- |
| ViaVersion / ViaBackwards | Java 版多版本协议兼容 |
| Geyser-Spigot / Floodgate | 基岩版互通与基岩账号桥接 |
| TAB | 玩家列表与名称展示 |
| PlaceholderAPI | 变量占位符框架 |
| spark | 性能分析 |

## 官网与周边系统（server-website）

官网是一体化 monorepo，包含四个子项目：

| 子项目 | 技术 | 说明 |
| --- | --- | --- |
| frontend | Vue 3 + Vite | 玩家主站：服务器介绍、公告、在线状态监控、阵营内测申请 |
| backend | FastAPI + SQLite | API 服务：公告、服务器监控（`/monitor`）、用户认证（`/auth`）、阵营内测（`/faction-beta`） |
| wiki | VitePress | 玩家文档站（当前站点） |
| admin-frontend | Vue 3 + Element Plus | 管理后台：公告、服务器地址、用户与内测申请管理 |

- 游戏服务器地址统一维护在后端注册表中，官网展示与在线探测统一读取，前端不硬编码；
- 官网注册登录内置滑块拼图人机验证，登录态贯穿内测申请等功能；
- 阵营内测申请支持「黎明誓约 / 暮夜同盟 / 暂不选择」三个选项，后台可审核。

## 阵营玩法的接入位置

| 系统 | 接入方式 | 状态 |
| --- | --- | --- |
| 登录服 | 选阵营界面分流，跨服互跳保持阵营前缀与增益一致 | 规划中 |
| CustomDeathMessages | 阵营专属死亡播报 | 规划中 |
| 卷轴系统 | 阵营奖励发放 | 规划中 |

> 阵营玩法设定详见[阵营玩法总览](/for-new/factions/)，对抗机制见[阵营对抗机制](/for-new/factions/mechanics)，建设计划见[发展路线](/develop/roadmap/)。
