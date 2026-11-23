import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// Font Awesome 6 图标库（npm 本地打包，无运行时外链）
import '@fortawesome/fontawesome-free/css/all.min.css'
// Markdown 渲染产物的全局样式（highlight.js 主题 + 代码块包装），公告与社区共用
import './assets/styles/markdown.css';
// 社区（论坛）模块的设计令牌与 Markdown 正文排版（全局，组件私有样式仍各自 scoped）
import './assets/styles/forum.css'
// 主题：恢复持久化的主题模式 / 自定义主题色，并监听系统主题变化。
// index.html 的首屏内联脚本已同步应用过一次，这里补齐响应式状态与监听。
import { initTheme } from './utils/theme.js'
initTheme()
// 头像加载失败统一回退内置默认图（FLPR-31），各组件只需在 img 上挂 @error="onAvatarError"
import { onAvatarError } from './utils/avatar.js'
// 分享卡片 meta：QQ/微信主抓取读 index.html 静态 OG 标签，这里按路由补齐浏览器与
// 执行 JS 的预览器标题；静态 OG 标签本身见 frontend/index.html
import { setupShareMeta } from './utils/shareMeta.js'

// 创建Vue应用实例
const app = createApp(App)

// 全局注入头像兜底方法（与各组件本地 defaultAvatar 导入解耦）
app.mixin({ methods: { onAvatarError } })

// 集成vue-router
app.use(router)
setupShareMeta(router)

// 挂载应用到DOM
app.mount('#app')
