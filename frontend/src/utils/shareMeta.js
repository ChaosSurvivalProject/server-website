/**
 * 分享卡片 / SEO 文案表（FLPR-62 建立，FLPR-63 复用，FLPR-64 补充长尾词）。
 *
 * 原先本模块在浏览器里用 document 逐个补 OG 标签；预渲染改为由 src/utils/seoHead.js
 * 通过 @unhead/vue 在构建期按路由注入 head，本文件只保留单一文案源：
 * - QQ / 微信等不执行 JS 的抓取器读 index.html 与各预渲染页的静态 OG 标签；
 * - 浏览器标签标题、canonical、OG 都由 useSeoHead() 统一维护，避免两处抢写 document.title。
 *
 * FLPR-64：标题一律带品类后缀（我的世界阵营生存服），描述铺「我的世界 1.21 阵营服 /
 * Java 基岩互通 服务器 / MC 双端互通服 / 1.21.11 生存服」等无人竞争的长尾位置，
 * 品牌词「星穹旅驿」始终与品类词同现，不与崩铁单独争夺泛词。
 */
import McConfig from '../config/mc-config.js'

const qqGroup = McConfig.qqGroup.id

export const DEFAULT_DESCRIPTION = `星穹旅驿是《我的世界》1.21.11 生存服：Java / 基岩互通的 MC 双端互通服，黎明誓约与暮夜同盟两大阵营对抗。提供进服指南、版本支持、资源下载与玩家社区。加入 QQ 群 ${qqGroup}，服务器地址见官网。`

// 只列公开页面；未列出的路由（登录、个人主页、管理页等）沿用全局默认卡片，
// 避免把用户动态内容或需要登录的页面作为对外分享标题。
export const SHARE_COPY = {
  Home: {
    page: '',
    description: DEFAULT_DESCRIPTION
  },
  TeamOverview: {
    page: '管理组总览',
    description: `星穹旅驿管理组现任名录与分工。我的世界 1.21 阵营服运营团队，Java / 基岩互通服务器。加入 QQ 群 ${qqGroup}，服务器地址见官网。`
  },
  Forum: {
    page: '玩家社区',
    description: `星穹旅驿玩家社区：我的世界 1.21.11 生存服攻略、黎明誓约与暮夜同盟阵营讨论、公告与活动。加入 QQ 群 ${qqGroup}，服务器地址见官网。`
  },
  Resources: {
    page: '资源中心',
    description: `星穹旅驿资源中心：我的世界 1.21 阵营服整合包、插件与客户端资源下载，Java / 基岩互通。加入 QQ 群 ${qqGroup}，服务器地址见官网。`
  },
  FactionBeta: {
    page: '阵营玩法',
    description: `黎明誓约 vs 暮夜同盟：星穹旅驿我的世界 1.21 阵营服玩法说明与常规招募入口，Java / 基岩双端互通。加入 QQ 群 ${qqGroup}，服务器地址见官网。`
  }
}

export function composedTitle(page, siteName) {
  return page
    ? `${page} | ${siteName} 我的世界阵营生存服`
    : `${siteName} | 我的世界 Java/基岩互通 1.21.11 生存服`
}
