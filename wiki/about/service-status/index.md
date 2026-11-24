---
description: 星穹旅驿服务状态说明：服务器地址 serverone.codeyun.com:12000，官网实时 MOTD 与 UptimeKuma 监控，以及连不上服务器时的排查步骤。
---
# 服务状态说明

星穹旅驿官网首页设有「实时查看服务状态」区块，嵌入第三方 MOTD 状态卡片，
展示当前在线状态、延迟与版本兼容信息。该区块由浏览器按后端监控接口返回的
服务器地址动态生成，因此**不运行 JavaScript 时看不到卡片**，但可以从本页与
[进服指南](/for-new/quick-start/)直接读到纯文字的状态说明与地址。

## 查看渠道

| 渠道 | 说明 |
| --- | --- |
| 官网首页状态卡片 | 地址：`serverone.codeyun.com:12000`，实时状态由 MOTD 服务提供 |
| UptimeKuma 监控 | 官网「保障完善游戏体验」区块说明的可用性监控，目标在线率 99% |
| 服务器公告 | 计划维护与异常说明见[活动与公告归档](/about/announcements/) |

> 服务器地址的权威数据源是官网后端监控接口（`GET /api/monitor/servers`）。
> 若地址发生变更，以官网首页展示为准；本页与 Wiki 文档中的地址仅作静态说明。

## 连不上服务器时怎么办

1. 先确认地址与端口：Java 版填 `serverone.codeyun.com:12000`；基岩版地址
   `serverone.codeyun.com`、端口 `12000`。
2. 确认客户端版本在 [支持范围](/for-new/versions/) 内（Java 版 `1.21.1 ~ 1.21.11`，推荐 `1.21.11`）。
3. 查看官网首页的状态卡片是否显示离线；离线时稍后重试，维护信息见公告归档。
4. 仍无法连接可加入 QQ 群 `942235691` 反馈，或联系管理员。

## 相关文档

- [进服指南（Java / 基岩并列）](/for-new/quick-start/)
- [版本与客户端支持范围](/for-new/versions/)
- [服务器架构总览](/develop/architecture/)
- [常见问题解答](/for-new/faq/)
- [返回星穹旅驿官网](https://xqly.xt91tv.shop/)
