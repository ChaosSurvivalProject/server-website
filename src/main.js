import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// 创建Vue应用实例
const app = createApp(App)

// 集成vue-router
app.use(router)

// 挂载应用到DOM
app.mount('#app')
