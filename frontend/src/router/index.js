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
    path: '/faction-beta',
    name: 'FactionBeta',
    // 阵营对战玩法内测资格申请（需登录后填写）
    component: () => import('../views/FactionBetaApply.vue')
  },
  {
    path: '/staff/:code',
    name: 'StaffVerify',
    // 工作人员名片验证页（扫码直达，SPA 深层路由依赖 nginx try_files 兜底）
    component: () => import('../views/StaffVerify.vue'),
    props: true
  },
  {
    path: '/team',
    name: 'TeamOverview',
    // 管理组总览（公开的现任名录；/staff 前缀留给验证页，故用 /team）
    component: () => import('../views/TeamOverview.vue')
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