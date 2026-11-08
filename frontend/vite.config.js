import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 开发代理：
  // - /api → 后端（新接口统一前缀，新上传图片返回 /api/announcement/uploads/...）
  // - /announcement/uploads/... → 历史公告正文内嵌的旧图片 URL（存量数据兼容）
  // - /download/... → 资源中心下载跳转端点（后端 302 到 GitHub，不挂 /api 前缀）
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
      '/announcement': 'http://localhost:5000',
      '/download': 'http://localhost:5000'
    }
  }
})
