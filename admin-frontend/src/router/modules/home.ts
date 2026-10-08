const Layout = () => import("@/layout/index.vue");

/**
 * 后台管理静态路由（`src/router/modules/**` 由 `router/index.ts` 自动收集，登录/错误页在 `remaining.ts`）。
 *
 * ⚠️ 菜单分组口径（改菜单前先读）：
 * 1. `formatTwoStageRoutes()` 会把三级及以上路由**拍平成二级**，所以「功能模块」写成**顶级路由记录**、
 *    页面写在它的 `children` 里。拍平后页面在 vue-router 中仍是 `/xxx` 绝对路径直达
 *    （匹配结果不含模块记录，页面组件照常渲染）。
 * 2. 模块记录只用来生成侧边菜单，本身没有 `component`，因此**必须给模块加 `redirect`**（指向本模块第一个页面），
 *    否则手输 `#/content` 会命中一个没有组件的记录、渲染空白。
 * 3. 布局根路由 `/` 的 `children` 留空 + `showLink: false`：它只作为 Layout 外壳，不占菜单一级，
 *    菜单一级就是各功能模块（详见 README「后台管理（admin-frontend）· 页面与路由」）。
 * 4. `ascending()` 只按 `meta.rank` 排**同级**且不递归子级——模块顺序看 `rank`，页面顺序看数组顺序。
 */
export default [
  {
    path: "/",
    name: "Admin",
    component: Layout,
    redirect: "/announcement/list",
    meta: {
      icon: "ep/school",
      title: "后台管理",
      rank: 0,
      showLink: false
    },
    children: []
  },
  // ── 内容运营 ──
  {
    path: "/content",
    name: "ContentGroup",
    redirect: "/announcement/list",
    meta: {
      title: "内容运营",
      icon: "ep/document-copy",
      rank: 1,
      showLink: true
    },
    children: [
      {
        path: "/announcement/list",
        name: "AnnouncementList",
        component: () => import("@/views/announcement/list.vue"),
        meta: {
          title: "站内信管理",
          icon: "ep/message",
          showLink: true
        }
      },
      {
        path: "/announcement/edit",
        name: "AnnouncementEdit",
        component: () => import("@/views/announcement/edit.vue"),
        meta: {
          title: "编辑站内信",
          showLink: false,
          activeMenu: "/announcement/list"
        }
      },
      {
        path: "/faction-beta/list",
        name: "FactionBetaList",
        component: () => import("@/views/faction-beta/list.vue"),
        meta: {
          title: "阵营内测申请",
          icon: "ep/flag",
          showLink: true
        }
      }
    ]
  },
  // ── 社区（论坛）模块（PRD §3.2） ──
  {
    path: "/community",
    name: "CommunityGroup",
    redirect: "/forum/article/list",
    meta: {
      title: "社区管理",
      icon: "ep/chat-line-round",
      rank: 2,
      showLink: true
    },
    children: [
      {
        path: "/forum/article/list",
        name: "ForumArticleList",
        component: () => import("@/views/forum/article/list.vue"),
        meta: {
          title: "文章管理",
          icon: "ep/chat-dot-round",
          showLink: true
        }
      },
      {
        path: "/forum/category/list",
        name: "ForumCategoryList",
        component: () => import("@/views/forum/category/list.vue"),
        meta: {
          title: "板块管理",
          icon: "ep/folder-opened",
          showLink: true
        }
      },
      {
        path: "/forum/tag/list",
        name: "ForumTagList",
        component: () => import("@/views/forum/tag/list.vue"),
        meta: {
          title: "标签管理",
          icon: "ep/price-tag",
          showLink: true
        }
      },
      {
        path: "/forum/config",
        name: "ForumConfig",
        component: () => import("@/views/forum/config.vue"),
        meta: {
          title: "社区配置",
          icon: "ep/setting",
          showLink: true
        }
      }
    ]
  },
  // ── 员工管理（员工名片模块） ──
  {
    path: "/staff",
    name: "StaffGroup",
    redirect: "/staff/list",
    meta: {
      title: "员工管理",
      icon: "ep/postcard",
      rank: 3,
      showLink: true
    },
    children: [
      {
        path: "/staff/list",
        name: "StaffList",
        component: () => import("@/views/staff/list.vue"),
        meta: {
          title: "工作人员名片",
          icon: "ep/user-filled",
          showLink: true
        }
      },
      {
        path: "/staff/card",
        name: "StaffCard",
        component: () => import("@/views/staff/card.vue"),
        meta: {
          title: "名片制作",
          icon: "ep/printer",
          showLink: true
        }
      }
    ]
  },
  // ── 智能客服 ──
  {
    path: "/kb",
    name: "KBGroup",
    redirect: "/kb/list",
    meta: {
      title: "智能客服",
      icon: "ep/service",
      rank: 4,
      showLink: true
    },
    children: [
      {
        path: "/kb/list",
        name: "KBList",
        component: () => import("@/views/kb/list.vue"),
        meta: {
          title: "知识库",
          icon: "ep/collection",
          showLink: true,
          // 模块下只有这一个页面，不写 showParent 会被拍平成单个菜单项（模块名丢失）
          showParent: true
        }
      }
    ]
  },
  // ── 系统管理 ──
  {
    path: "/system",
    name: "SystemGroup",
    redirect: "/server/list",
    meta: {
      title: "系统管理",
      icon: "ep/setting",
      rank: 5,
      showLink: true
    },
    children: [
      {
        path: "/server/list",
        name: "ServerList",
        component: () => import("@/views/server/list.vue"),
        meta: {
          title: "服务器地址管理",
          icon: "ep/server",
          showLink: true
        }
      },
      {
        path: "/server/edit",
        name: "ServerEdit",
        component: () => import("@/views/server/edit.vue"),
        meta: {
          title: "编辑服务器",
          showLink: false,
          activeMenu: "/server/list"
        }
      },
      {
        path: "/user/list",
        name: "UserList",
        component: () => import("@/views/user/list.vue"),
        meta: {
          title: "用户管理",
          icon: "ep/user",
          showLink: true
        }
      }
    ]
  }
] satisfies Array<RouteConfigsTable>;
