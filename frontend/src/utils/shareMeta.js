/**
 * 分享卡片 meta 的按路由更新（不引入新依赖）。
 *
 * 重要前提：QQ / 微信在群里抓链接卡片时基本不执行 JS，只读服务器返回的原始 HTML。
 * 真正决定卡片内容的是 frontend/index.html 里的静态 OG 标签；本模块服务于会执行 JS 的
 * 预览器（部分聊天客户端 / 桌面浏览器），并让浏览器标签标题与路由一致。FLPR-63 做
 * 静态化时可以直接复用下面的文案表。
 */
import { watch } from 'vue'
import McConfig from '../config/mc-config.js'
import { siteBranding } from './siteBranding.js'

const qqGroup = McConfig.qqGroup.id
const DEFAULT_DESCRIPTION = `《我的世界》Java/基岩双端互通阵营生存服。进服指南、黎明誓约 / 暮夜同盟阵营玩法、资源下载与玩家社区一站直达。加入 QQ 群 ${qqGroup}，服务器地址见官网。`

// 只列公开页面；未列出的路由（登录、个人主页、管理页等）沿用全局默认卡片，
// 避免把用户动态内容或需要登录的页面作为对外分享标题。
const SHARE_COPY = {
  Home: { page: '', description: DEFAULT_DESCRIPTION },
  TeamOverview: {
    page: '管理组总览',
    description: `星穹旅驿管理组现任名录与分工，了解服务器运营团队。加入 QQ 群 ${qqGroup}，服务器地址见官网。`
  },
  Forum: {
    page: '玩家社区',
    description: `星穹旅驿玩家社区：文章、攻略、公告与讨论。加入 QQ 群 ${qqGroup}，服务器地址见官网。`
  },
  Resources: {
    page: '资源中心',
    description: `星穹旅驿资源中心：整合包、插件与客户端资源下载。加入 QQ 群 ${qqGroup}，服务器地址见官网。`
  }
}

function composedTitle(page, siteName) {
  return page
    ? `${page} | ${siteName} 我的世界阵营生存服`
    : `${siteName} | 我的世界 Java/基岩双端互通阵营生存服`
}

function setContent(selector, value) {
  const el = document.head.querySelector(selector)
  if (el) el.setAttribute('content', value)
}

/** 按当前路由刷新分享卡片 meta（og:image 全站共用固定封面，无需按路由改） */
export function updateShareMeta(route) {
  const copy = SHARE_COPY[route?.name] || SHARE_COPY.Home
  const siteName = siteBranding.name || '星穹旅驿'
  const title = composedTitle(copy.page, siteName)
  const url = window.location.origin + (route?.fullPath || '/')

  document.title = title
  setContent('meta[name="description"]', copy.description)
  setContent('meta[property="og:title"]', title)
  setContent('meta[property="og:description"]', copy.description)
  setContent('meta[property="og:url"]', url)
  setContent('meta[name="twitter:title"]', title)
  setContent('meta[name="twitter:description"]', copy.description)
}

/** 在 main.js 里 app.use(router) 之后调用一次 */
export function setupShareMeta(router) {
  router.afterEach((to) => updateShareMeta(to))
  // 站点配置是异步拉取的，applySiteBranding 会改 siteBranding 与 document.title；
  // 跟随刷新一次，避免路由标题被全局站点标题覆盖。
  watch([() => siteBranding.name, () => siteBranding.title], () => {
    updateShareMeta(router.currentRoute.value)
  })
  updateShareMeta(router.currentRoute.value)
}
