---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "星穹旅驿"
  text: "Wiki"
  tagline: Minecraft纯净生存服务器wiki
  image:
    src: https://img.fastmirror.net/s/2025/12/21/6947940d0d8a6.png
    alt: 星穹旅驿生存服logo
  actions:
    - theme: brand
      text: 查看文档 
      link: /for-new/visitor-guidelines
    - theme: alt
      text: 访问官网
      # 外链（带协议）不会被 VitePress 加 base 前缀；绑定域名后需同步改这里
      link: http://156.254.7.56:23333/

features:
  - title: 趣味生存
    details: 服务器核心为Purpur 1.21.10，并添加商店、领地、技能等插件玩法；
    icon: 🎯
  - title: 基础设施完善
    details: 拥有服务器官网，qq群，服务器文档等；
    icon: 🛠️   
  - title: 社区活跃
    details: 拥有活跃的社区，对问题或建议的响应速度快； 
    icon: ✨
---

::: tip 📢服务器更新公告 2025.12.21
Purpur 1.21.10 已发布，服务器已升级，欢迎大家游玩，尽情享受新的功能带来的乐趣！<br>
**版本变化**：1.21.8 -> 1.21.10<br>
**更新内容**：
1. 服务器核心升级至Purpur 1.21.10；
2. 新增`箱子商店`和`全球市场`插件，支持玩家购买物品；
3. 新增`领地`插件，玩家可使用`木锄`进行圈地；
4. 添加`技能`插件，在挖矿、击杀、种植的过程中提升自己的技能点，以解锁更多技能；
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
