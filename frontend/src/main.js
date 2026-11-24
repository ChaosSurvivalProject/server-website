// FLPR-63：用 ViteSSG 替换 createApp(App).mount('#app')。
// 与 VitePress 不同，这里是主站 SPA 的「按路由预渲染」：公开页面在构建期输出
// 带正文的真实 HTML，登录 / 注册 / 发帖 / 扫码名片等仍走浏览器端渲染。
import { ViteSSG } from 'vite-ssg'
import App from './App.vue'
import { routerOptions } from './router'
// Font Awesome 6 图标库（npm 本地打包，无运行时外链）
import '@fortawesome/fontawesome-free/css/all.min.css'
// Markdown 渲染产物的全局样式（highlight.js 主题 + 代码块包装），公告与社区共用
import './assets/styles/markdown.css';
// 社区（论坛）模块的设计令牌与 Markdown 正文排版（全局，组件私有样式仍各自 scoped）
import './assets/styles/forum.css'
// 主题：恢复持久化的主题模式 / 自定义主题色，并监听系统主题变化。
// index.html 的首屏内联脚本已在浏览器同步应用过一次，这里补齐响应式状态与监听；
// 预渲染在 Node 端没有 window/localStorage，必须只在客户端初始化。
import { initTheme } from './utils/theme.js'
// 头像加载失败统一回退内置默认图（FLPR-31），各组件只需在 img 上挂 @error="onAvatarError"
import { onAvatarError } from './utils/avatar.js'

// head（title / description / canonical / OG）由 App.vue 里的 useSeoHead() 按路由注入，
// 构建期随静态 HTML 一起落盘；原先的 shareMeta.js 客户端补标签已并入该模块。

export const createApp = ViteSSG(
  App,
  routerOptions,
  ({ app, isClient }) => {
    // 全局注入头像兜底方法（与各组件本地 defaultAvatar 导入解耦）
    app.mixin({ methods: { onAvatarError } })
    // 首屏主题脚本只依赖 localStorage，SSR 阶段不要碰 DOM/存储
    if (isClient) initTheme()
  }
)
