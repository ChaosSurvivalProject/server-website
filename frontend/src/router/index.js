import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/announcements',
    name: 'Announcements',
    // 懒加载Announcements组件
    component: () => import('../views/Announcements.vue')
  },
  {
    path: '/announcements/:id',
    name: 'AnnouncementDetail',
    // 懒加载AnnouncementDetail组件
    component: () => import('../views/AnnouncementDetail.vue'),
    // 路由参数
    props: true
  },
  {
    path: '/login',
    name: 'Login',
    // 登录/注册共用 AuthView，通过 initialMode 区分
    component: () => import('../views/AuthView.vue'),
    props: { initialMode: 'login' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/AuthView.vue'),
    props: { initialMode: 'register' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 配置当前激活路由的类名
  linkActiveClass: 'active',
  linkExactActiveClass: 'exact-active',
  // 配置滚动行为
  scrollBehavior(to, from, savedPosition) {
    // 如果有保存的位置，使用它（如浏览器前进/后退按钮）
    if (savedPosition) {
      return savedPosition
    } else {
      // 否则滚动到页面顶部
      return { top: 0 }
    }
  }
})

export default router