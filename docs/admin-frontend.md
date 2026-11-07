# 后台管理前端（admin-frontend）

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 原样下沉的专题文档（内容未改动，仅调整标题层级与文内交叉引用）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

独立的后台管理前端，基于 [pure-admin-thin](https://github.com/pure-admin/pure-admin-thin)（Vue 3 + TypeScript + Element Plus + Pinia + TailwindCSS 4 + Vite），生产部署在 `/admin/` 路径下，**hash 路由模式**。

## 页面与路由

业务路由在 `src/router/modules/home.ts` 中静态注册（登录/错误页在 `remaining.ts`），根路由 `/` 登录后重定向到 `/announcement/list`。后端未实现 `/get-async-routes` 动态菜单接口，动态路由为空，仅静态路由生效。

侧边菜单**一级即功能模块**，模块内的页面是它的子路由：

| 一级菜单 | 包含页面 |
|------|------|
| 内容运营 | 公告管理（含编辑）、阵营内测申请 |
| 社区管理 | 文章管理、板块管理、标签管理、社区配置 |
| 员工管理 | 工作人员名片、名片制作 |
| 智能客服 | 知识库 |
| 系统管理 | 服务器地址管理（含编辑）、用户管理 |

布局根路由 `/` 只作 Layout 外壳（`showLink: false` + `children: []`）不占菜单一级。注意 `formatTwoStageRoutes()` 会把三级及以上路由**拍平成二级**，所以模块记录本身没有组件、**必须写 `redirect`** 指向本模块第一个页面（否则手输 `#/content` 会落在无组件的记录上、渲染空白）；模块下只有 1 个页面时（如智能客服）要在该页 `meta` 上写 `showParent: true`，否则会被拍成单个菜单项、模块名丢失。**新增后台页面挂到对应模块的 `children` 下即可，不要新增一级菜单。**

| 路由（hash） | 页面 | 说明 |
|------|------|------|
| `/login` | 登录页 | 用户名 + 密码（JWT；无验证码） |
| `/announcement/list` | 公告管理 | 公告列表（分页，含草稿；新建/编辑/删除） |
| `/announcement/edit` | 公告编辑 | 新建或编辑公告（标题、正文、发布人、发布时间、发布状态；正文按 `contentType` 切换 wangEditor 富文本 / md-editor-v3 Markdown，富文本图片经 `/announcement/upload/image` 上传） |
| `/server/list` | 服务器地址管理 | 服务器列表（新增/编辑/删除/设为主服务器；持久化在 `servers` 表，重启不丢失，见 [api-reference.md](./api-reference.md) 的「服务器监控」） |
| `/server/edit` | 服务器编辑 | 新建或编辑服务器（名称、地址、端口、是否主服务器） |
| `/faction-beta/list` | 阵营内测申请 | 申请列表（状态过滤、详情弹窗、通过/拒绝、删除） |
| `/kb/list` | 知识库 | 统计条（文档/切片/索引版本/维度状态）+ 文档列表（来源过滤、切片预览抽屉、重建索引、删除；wiki 来源只读由 `kb_sync.py` 维护）+ 粘贴新增 |
| `/user/list` | 用户管理 | 用户列表（新增/编辑/启用/禁用/软删除/恢复、状态过滤、**禁言/解禁**、**论坛数据**；编辑模式密码留空=不修改） |
| `/staff/list` | 工作人员名片 | 台账列表（状态过滤/关键词搜索、新增/编辑、撤销（选原因）/恢复/续期/重生成码、二维码下载、CSV 导出、顶部统计条、即将到期行高亮） |
| `/staff/card` | 名片制作 | 统一名片模板出图页（选人 + 横/竖版切换；PNG/JPG 走本地 `html2canvas-pro`，PDF 走浏览器打印；二维码纯白底 200px、头像像素渲染、正面含名片版本与防伪提示） |
| `/forum/article/list` | 文章管理 | 五维检索（标题/作者/板块/标签/状态）+ 通过/驳回/置顶/加精/下架/恢复/硬删 + 改属性抽屉（**状态不变**）+ 正文预览抽屉（**只读**）+ 评论抽屉（可删单条，删顶层连带其回复）+ 封面图库（只读 + 复制 URL） |
| `/forum/category/list` | 板块管理 | 板块增删改查（名称/颜色/排序/隐藏；**系统板块不可删、不可改名、不可隐藏**；有已发布文章的板块删除被拦） |
| `/forum/tag/list` | 标签管理 | 标签库（来源筛选，默认「用户自动创建」= 清理入口）+ 重命名 + 置热 + 合并 + 删除 |
| `/forum/config` | 社区配置 | Banner 三字段（含插画上传）+ 排序默认项 + 搜索占位文案 + 三项只读统计（与首页统计卡同接口）+ 打赏预留键只读展示 |
| `/access-denied` `/server-error` | 403 / 500 | 全屏错误页 |

用户管理页（`/user/list`）额外承载社区两项能力：**禁言/解禁**（时长预设 1/3/7/30 天或永久；与「禁用」正交——禁用是不能登录，禁言是能登录但不能发帖评论）与**论坛数据**弹窗（发帖/获赞/粉丝 + 最近 5 篇）。

浏览器 URL 带部署前缀与 hash：开发 `http://localhost:3005/#/announcement/list`，生产 `http://<host>/admin/#/announcement/list`。

## HTTP 层（`src/utils/http/`）与 API 模块（`src/api/`）

- `utils/http/index.ts`（PureHttp）— axios 封装：`baseURL` 留空（同源相对路径，dev 由 Vite proxy、prod 由 Nginx 反代到后端）；请求拦截器对 `/api/auth/login`、`/api/auth/register`、`/api/auth/captcha` 白名单放行，其余自动携带 `Authorization: Bearer <token>`；响应拦截器统一解包 `{code, message, data}`（`code=0` 直接返回 `data`），业务错误与 HTTP 非 2xx 都把 FastAPI `detail` 或包络 `message` 提取到 `error.message`——页面 catch 里直接 `ElMessage.error(e.message)`，不要重复解析错误体；401（HTTP 401 或包络 401/1001）自动清除登录态并跳回登录页
- `api/` — `announcement.ts` / `server.ts` / `user.ts` / `factionBeta.ts` / `kb.ts` / `staff.ts` 分别封装对应 admin 接口，TS 类型与后端契约一致；**新增或修改后端接口时必须同步主站契约参照 `frontend/src/api/api.js` 与本目录**（见 [docs/agents/api-conventions.md](./agents/api-conventions.md)）
- 传 `FormData`（文件上传）时必须显式加 `Content-Type: multipart/form-data` 请求头，否则 axios 会把 FormData 序列化成 JSON，后端解析不到字段直接 422

## 登录与鉴权

- 登录走 `/auth/login`，token 与用户信息（含 `role`）存 localStorage（`utils/auth.ts`）；路由守卫（`router/index.ts`）对未登录访问一律重定向 `/login`，已登录访问 `/login` 保持当前页
- 后端所有 admin 接口要求 `role=admin`，普通用户 token 调用返回 403

## 环境配置（`admin-frontend/.env*`）

| 变量 | 说明 | dev（`.env.development`） | prod（`.env.production`） |
|------|------|--------------------------|---------------------------|
| `VITE_PORT` | dev server 端口（`.env` 默认 8848，被覆盖） | `3005` | — |
| `VITE_PUBLIC_PATH` | 构建基础路径 | `/` | `/admin/` |
| `VITE_ROUTER_HISTORY` | 路由模式 | `hash` | `hash` |
| `VITE_CDN` / `VITE_COMPRESSION` | CDN 依赖 / 构建压缩 | — | `false` / `none` |

页面标题等运行时配置在 `public/platform-config.json`（`Title` 等，经 `src/config/index.ts` 读取）。

## 开发与部署

```bash
cd admin-frontend
pnpm install
pnpm dev        # 开发服务器（:3005，API 经 vite proxy 转发到后端 :5000）
pnpm build      # 构建到 dist/（base: /admin/）
pnpm typecheck  # tsc + vue-tsc 类型检查
```

- 开发模式：Vite dev server（:3005），`vite.config.ts` 的 proxy 把 `/api` 转发到后端 FastAPI（:5000）
- 生产模式：`pnpm build` → `dist/`，由 Nginx 挂在 `/admin/` 路径下；hash 路由刷新无需 `try_files` 兜底，API 请求为同源相对路径，命中 Nginx 既有反代规则
- 管理员入口：主站已登录管理员点击头像下拉菜单 → 「后台管理」（仅管理员角色可见，URL 来自 `frontend` 的 `VITE_ADMIN_URL`，默认 `/admin`）
