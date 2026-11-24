import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // FLPR-63：主站改为 vite-ssg 预渲染。只输出公开、可索引的页面；
  // 登录/注册、发帖、扫码名片等需要登录或按用户取数的路由不生成静态 HTML，
  // 由 nginx 的 SPA 兜底继续在浏览器端渲染（不进 sitemap、不预渲染）。
  ssgOptions: {
    includedRoutes(paths) {
      const excluded = /^\/(login|register|faction-beta)(\/|$)|^\/forum\/(new|edit|my|titles|recycle)(\/|$)|^\/staff\//;
      // 动态路由（/resources/:slug、/forum/post/:id 等）没有确定 slug，
      // 预渲染只会产出带 :slug 字面的死链并触发无意义的接口请求，直接跳过。
      return paths.filter((path) => !path.includes(':') && !excluded.test(path));
    }
  },
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
