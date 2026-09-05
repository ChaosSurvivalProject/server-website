import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// Font Awesome 6 图标库（npm 本地打包，无运行时外链）
import '@fortawesome/fontawesome-free/css/all.min.css'

// 创建Vue应用实例
const app = createApp(App)

// 集成vue-router
app.use(router)

// 挂载应用到DOM
app.mount('#app')
