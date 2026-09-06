import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 开发代理：公告富文本中的图片以相对路径 /announcement/uploads/... 存储，
  // dev server 需转发到本地后端才能显示（生产为同源 Nginx 反代，无需此配置）
  server: {
    proxy: {
      '/announcement': 'http://localhost:5000'
    }
  }
})
