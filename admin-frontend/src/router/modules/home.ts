const Layout = () => import("@/layout/index.vue");

export default {
  path: "/",
  name: "Admin",
  component: Layout,
  redirect: "/announcement/list",
  meta: {
    icon: "ep/school",
    title: "后台管理",
    rank: 0
  },
  children: [
    {
      path: "/announcement/list",
      name: "AnnouncementList",
      component: () => import("@/views/announcement/list.vue"),
      meta: {
        title: "公告管理",
        icon: "ep/bullhorn",
        showLink: true
      }
    },
    {
      path: "/announcement/edit",
      name: "AnnouncementEdit",
      component: () => import("@/views/announcement/edit.vue"),
      meta: {
        title: "编辑公告",
        showLink: false,
        activeMenu: "/announcement/list"
      }
    },
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
      path: "/faction-beta/list",
      name: "FactionBetaList",
      component: () => import("@/views/faction-beta/list.vue"),
      meta: {
        title: "阵营内测申请",
        icon: "ep/flag",
        showLink: true
      }
    },
    {
      path: "/kb/list",
      name: "KBList",
      component: () => import("@/views/kb/list.vue"),
      meta: {
        title: "知识库",
        icon: "ep/collection",
        showLink: true
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
    },
    {
      path: "/staff/list",
      name: "StaffList",
      component: () => import("@/views/staff/list.vue"),
      meta: {
        title: "工作人员名片",
        icon: "ep/postcard",
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
    },
    // ── 社区（论坛）模块（PRD §3.2） ──
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
} satisfies RouteConfigsTable;
