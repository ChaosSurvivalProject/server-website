import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/servers',
    name: 'ServerList',
    // 懒加载ServerList组件
    component: () => import('../views/ServerList.vue')
  },
  {
    path: '/servers/:id',
    name: 'ServerDetail',
    // 懒加载ServerDetail组件
    component: () => import('../views/ServerDetail.vue'),
    // 路由参数
    props: true
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