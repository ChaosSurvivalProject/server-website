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
    }
  ]
} satisfies RouteConfigsTable;