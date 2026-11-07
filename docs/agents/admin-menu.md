# 后台管理菜单规约（admin-frontend）

> 本文是 [AGENTS.md](../../AGENTS.md) 对应规约小节的完整原文（2026-11-07 文档重构时下沉，内容未改动）；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

- 侧边菜单**一级即功能模块**，路由静态写在 `admin-frontend/src/router/modules/home.ts`（默认导出**数组**）：`/` 只作 Layout 外壳（`showLink: false` + `children: []`，不占菜单），其余顶级记录是模块——`/content` 内容运营、`/community` 社区管理、`/staff` 员工管理、`/kb` 智能客服、`/system` 系统管理，页面（含 `showLink: false` 的编辑页）挂各自 `children` 下。**新增页面挂到对应模块里，不要新增一级菜单**；只有新增功能模块才加顶级记录，模块顺序由顶级 `meta.rank` 决定（`ascending()` 只排同级、不递归子级，模块内页面顺序 = 数组顺序）。
- pure-admin 的 `formatTwoStageRoutes()` 会把三级及以上路由**拍平成二级**，模块记录因此没有组件：**每个模块必须写 `redirect` 指向本模块第一个页面**，否则手输 `#/content` 命中无组件记录 → 渲染空白；模块下只有 1 个页面时要在该页 `meta.showParent = true`，否则 `SidebarItem` 会把模块拍成单个菜单项、模块名丢失（智能客服就是这种情况）。
- 改完菜单别只看代码：这几个函数会重排/改写路由，验证方式是「导入真实 `home.ts` → 跑 `ascending` / `formatFlatteningRoutes` / `formatTwoStageRoutes` → `createRouter` 后逐个 `router.resolve(路径)`」，确认每个页面 `matched` 仍是 `[ /, 页面 ]` 且页面记录带组件（拍平后模块记录不参与匹配，页面靠绝对路径直达）。
