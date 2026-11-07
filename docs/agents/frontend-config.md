# 前端配置 / Wiki / 文档归档规约

> 本文汇总 [AGENTS.md](../../AGENTS.md)「前端配置规约」「Wiki 规约」「文档归档口径」三个小节的完整原文（2026-11-07 文档重构时下沉，内容未改动）；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

## 前端配置规约

- 主站配置一律走 Vite 环境变量（`VITE_` 前缀）：`frontend/.env` 存所有模式共用的默认值（QQ 群、服务器 id、版本文案、后台入口等），`.env.development` / `.env.production` 按构建模式覆盖（dev → 本地 5000，build → 同源）；本地个性化覆盖写 `.env.local`（根 `.gitignore` 的 `*.local` 已忽略）。**三个 `.env` 文件随仓库提交，禁止在组件里直接读 `import.meta.env` 或在别处硬编码这些值**。
- `frontend/src/config/mc-config.js` 只是环境变量的统一读取层（含类型转换），**不要在其中硬编码站点值**；组件一律 `import McConfig` 取值。
- 生产环境 API 走同源（`VITE_BASE_API_URL` 留空 → `baseApiURL: ''`），依赖 Nginx 反代 `/api` 到本机 FastAPI（:5000）。
- 环境变量是构建期静态替换，改 `.env*` 后需重启 dev server / 重新 build 才生效。
- 模板中引用的静态图片必须先 `import` 再绑定 `:src`（如 `Home.vue` 的 `bbs-*.png`、`video-bg.jpg`）；**禁止直接写 `/src/...` 绝对路径**——Vite build 不会打包该路径，生产环境会 404（dev 下看不出来）。

## Wiki 规约

- VitePress `base: '/wiki'` + `cleanUrls: true`。站内链接写相对路径（VitePress 自动加 base）；**外链必须带协议**（`http(s)://`），否则会被加上 `/wiki` 前缀。
- 内容分三大分区，新增页面放对应分区并在 `.vitepress/config.mts` 侧边栏登记：`for-new/`（萌新指南）、`management/`（服务器管理）、`develop/`（服务器建设）。
- 站点外链域名（2026-10-03 起）：官网为 `https://xqly.xt91tv.shop`（HTTPS 标准 443，明文 HTTP 已禁；旧部署的 `:23333` 非标端口已随换服务器废弃）。wiki 内指向官网的外链（hero「访问官网」按钮、阵营文档申请入口等）统一写此地址，不要再写死 IP。

## 文档归档口径

- `TODO.md` **只留未完成项与后续计划**：清单/上线项收口后整段搬到 `docs/归档/已完成清单.md`（按完成时间倒序），并在 `TODO.md` 留一行指向归档的链接；只有**仍有未完成条目**的清单才在 `TODO.md` 保留一个收尾小节（如「换服务器重新部署：待人工收尾」）。
- 归档只搬清单本身：技术决策与规约仍写在 `AGENTS.md` / `README.md` / 各模块方案文档里，**不要往归档文件里新增规约**。换服务器、改端口这类使历史值失效的变更，在归档条目上补一句注记（如二维码前缀 `:23333` → 443），**不要静默改写历史记录**。
