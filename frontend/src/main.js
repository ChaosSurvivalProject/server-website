import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// Font Awesome 6 图标库（npm 本地打包，无运行时外链）
import '@fortawesome/fontawesome-free/css/all.min.css'
// Markdown 渲染产物的全局样式（highlight.js 主题 + 代码块包装），公告与社区共用
import './assets/styles/markdown.css';
// 社区（论坛）模块的设计令牌与 Markdown 正文排版（全局，组件私有样式仍各自 scoped）
import './assets/styles/forum.css'

// 创建Vue应用实例
const app = createApp(App)

// 集成vue-router
app.use(router)

// 挂载应用到DOM
app.mount('#app')
