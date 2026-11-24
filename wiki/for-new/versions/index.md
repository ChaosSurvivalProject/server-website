---
description: 星穹旅驿客户端版本支持范围：我的世界 1.21 阵营服 / Java 基岩互通服务器，Java 版 1.21.1 ~ 1.21.11（推荐 1.21.11），基岩版 1.21.x，ViaVersion / Geyser 多端互通。
---
# 版本与客户端支持范围

星穹旅驿服务端核心为 **Purpur 1.21.11**（Paper 系高性能核心），通过插件层同时兼容
新旧 Java 版客户端与基岩版客户端。本页面给出可索引的版本范围速查。

## Java 版

| 项目 | 说明 |
| --- | --- |
| 推荐版本 | `1.21.11` |
| 支持范围 | `1.21.1 ~ 1.21.11` |
| 多版本兼容 | ViaVersion + ViaBackwards，新旧客户端均可进入 |
| 服务器地址 | `serverone.codeyun.com:12000` |

使用 `1.21.1 ~ 1.21.11` 之外的客户端时，建议先升级启动器内安装的游戏版本；
多版本兼容由服务端插件提供，客户端无需额外安装 Mod。详见图解版
[Java 版加入服务器指南](/for-new/join-server/for-java-client/)。

## 基岩版

| 项目 | 说明 |
| --- | --- |
| 推荐版本 | 最新正式版（`1.21.x`） |
| 互通方案 | Geyser-Spigot + Floodgate |
| 服务器地址 | `serverone.codeyun.com` |
| 端口 | `12000` |

基岩版与 Java 版在同一服务器游玩，账号体系由 Floodgate 桥接；由于两端特性差异，
部分 Java 版机制在基岩版可能表现不同。详见
[基岩版加入服务器指南](/for-new/join-server/for-bedrock-client/)。

## 版本兼容相关的插件

| 插件 | 用途 |
| --- | --- |
| ViaVersion / ViaBackwards | Java 版多版本协议兼容 |
| Geyser-Spigot / Floodgate | 基岩版互通与账号桥接 |
| Purpur 1.21.11 | 服务端核心（1.21.11 协议基线） |

更多技术细节见[服务器架构总览](/develop/architecture/)；
按步骤操作见[进服指南（Java / 基岩并列）](/for-new/quick-start/)。
