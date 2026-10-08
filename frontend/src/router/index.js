import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
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
    path: '/forum',
    name: 'Forum',
    // 社区首页（双栏布局 + Banner + 板块标签 + 帖子列表 + 右侧三卡）
    component: () => import('../views/forum/CommunityHome.vue')
  },
  {
    path: '/forum/post/:id',
    name: 'ForumPost',
    // 文章详情（顶部「← 返回社区」+ 全局导航栏）
    component: () => import('../views/forum/PostDetail.vue'),
    props: true
  },
  {
    path: '/forum/new',
    name: 'ForumNew',
    // 发布文章（需登录；未登录由页面内跳登录并带 redirect）
    component: () => import('../views/forum/PostEditor.vue')
  },
  {
    path: '/forum/edit/:id',
    name: 'ForumEdit',
    // 编辑文章：与 /forum/new 复用同一页面组件（PostEditor 按路由区分 create/edit）
    component: () => import('../views/forum/PostEditor.vue'),
    props: true
  },
  {
    path: '/forum/my',
    name: 'ForumMy',
    // 我的文章（作者视角：各状态 + 驳回理由 + 编辑重提入口）
    component: () => import('../views/forum/MyPosts.vue')
  },
  {
    path: '/forum/recycle',
    name: 'ForumRecycle',
    // 回收站（作者视角：status=4 列表 + 恢复 / 彻底删除）
    component: () => import('../views/forum/RecycleBin.vue')
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