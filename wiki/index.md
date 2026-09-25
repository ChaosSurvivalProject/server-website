---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "星穹旅驿"
  text: "Wiki"
  tagline: Minecraft 乱世生存 · 阵营对抗服务器 Wiki
  image:
    src: /logo.png
    alt: 星穹旅驿生存服logo
  actions:
    - theme: brand
      text: 查看文档 
      link: /for-new/visitor-guidelines
    - theme: alt
      text: 阵营玩法
      link: /for-new/factions/
    - theme: alt
      text: 访问官网
      # 外链（带协议）不会被 VitePress 加 base 前缀；2026-09-25 起官网为 HTTPS xqly.xt91tv.shop:23333
      link: https://xqly.xt91tv.shop:23333/

features:
  - title: 乱世生存 · 阵营对抗
    details: 服务器核心为 Purpur 1.21.11，两大阵营「黎明誓约」与「暮夜同盟」争夺星穹界的未来，你的立场决定世界的样子；
    icon: ⚔️
  - title: 多版本 · 全平台互通
    details: ViaVersion / ViaBackwards 支持多版本 Java 版客户端，Geyser 支持基岩版跨平台联机，PC 与手机同服游玩；
    icon: 🌉
  - title: 阵营玩法系统
    details: 阵营体系基于 ImprovedFactions 搭建，死亡播报、卷轴奖励等联动玩法持续研发；
    icon: 🧩
  - title: 基础设施完善
    details: 拥有服务器官网、Wiki 文档、后台管理系统与在线状态监控；
    icon: 🛠️
---

::: tip 📢服务器更新公告 2026.09.14
服务器核心为 **Purpur 1.21.11**，通过 ViaVersion / ViaBackwards 支持多版本 Java 版客户端，并通过 Geyser 支持基岩版互通。<br>
全新「**阵营对战**」玩法设定定稿：**黎明誓约 vs 暮夜同盟**，两大阵营争夺星穹界的未来！<br>
**内测资格申请**已在[服务器官网](https://xqly.xt91tv.shop:23333/faction-beta)开放，欢迎前往申请；玩法介绍见[阵营玩法总览](/for-new/factions/)。
:::

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: -webkit-linear-gradient(120deg, #bd34fe, #41d1ff);
}

.image-src {
  border-radius: 50%!important;
  height: 320px!important;
  width: 320px!important;
}

/*爱的魔力转圈圈*/
.image-src:hover {
  transform: translate(-50%, -50%) rotate(300turn);
  transition: transform 59s 0s cubic-bezier(0.3, 0, 0.8, 1);
}

.VPButton {
  transition: transform 0.3s ease!important;
}


.VPButton:hover {
  transform: translateY(-5px);
}

.VPFeature {
    transition: transform 0.3s ease!important;
}

.VPFeature:hover {
  transform: translateY(-5px);
}

.m-home-layout .details small {
  opacity: 0.8;
}

.m-home-layout .bottom-small {
  display: block;
  margin-top: 2em;
  text-align: right;
}
</style>
