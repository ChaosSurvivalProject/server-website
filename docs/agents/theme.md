# 主题适配规约（全局）

> 本文是 [AGENTS.md](../../AGENTS.md)「主题适配规约（全局）」小节的完整原文。这是**覆盖全站所有页面与组件**的通用规约，不属于任何单一模块；硬性禁区速览见 AGENTS.md 对应小节。文中 `代码样式` 的路径均相对仓库根目录。

## 适用范围

前台主站（`frontend/`）、后台管理（`admin-frontend/`）、Wiki（`wiki/`）——**任何新增或修改的页面、组件、弹窗、抽屉、编辑器、徽章、提示条**都要同时适配浅色与深色两套主题。不是论坛或某个模块的局部要求。

## 硬性要求

- **禁止写死单一主题的色值**。新增 UI 前先确认它在浅色和深色下都能看清、不突兀；只验浅色就提交 = 不合规。
- **禁止只给一套色板**。凡是以 JS 常量表内联颜色（徽章、状态标签、色板项等）的地方，每项都必须同时给出浅色与深色两套，缺一即视为未完成。
- **主题切换必须即时生效**，不允许"切主题后要刷新页面才更新"。响应式读取主题状态是硬要求，不要用 `document.documentElement.getAttribute()` 这类一次性读法。

## 两套主题机制（别搞混）

| 端 | 主题源 | 读法 |
|---|---|---|
| 前台 `frontend/` | `frontend/src/utils/theme.js` 的 `themeState.resolved`（`light`/`dark`，已把"跟随系统"解析掉），挂载到 `<html data-theme>` | 组件里 `import { themeState }` 直接读响应式属性；CSS 用 `[data-theme='dark']` 覆盖 |
| 后台 `admin-frontend/` | pure-admin 切 `<html class="dark">`（`layout/hooks/useDataThemeChange.ts`），**没有响应式 store** | CSS 走 Element Plus 的 `--el-*` 变量自动适配；确有组件需要 JS 派生主题时，用 `MutationObserver` 监听 `html.class` |

- 前台主题令牌在 `frontend/src/style.css`：`--brand-lt-*` / `--brand-dk-*` 由单一主色派生；论坛等模块另有 `--fx-*` 令牌在 `frontend/src/assets/styles/forum.css`，`[data-theme='dark'] .forum-root` 一处切换即可全站生效。**组件样式优先引用令牌，不要自己写 hex**。
- 颜色确需 JS 内联时（如按数据项取色的徽章），以 `themeState.resolved` 为响应式依赖选套，保证浅色/深色/跟随系统三种切换都能即时重算。

## 已知踩坑（跨模块通用）

- **md-editor-v3 默认恒 light、代码块默认 `atomOneDark`**：`MdEditor` / `MdPreview` 必须绑 `:theme`（前台接 `themeState.resolved`；后台文章预览用 `MutationObserver` 派生），并加 `:code-style-reverse="false"`，否则深色下整块白底深字、浅色下代码块也是深色。踩过的前台论坛编辑器、后台文章预览、后台公告编辑器三处都要按此套路处理。
- **代码块底色全站统一**：浅色 `#f6f8fa`、深色 `#24292e`（`frontend/src/assets/styles/markdown.css` 与 `admin-frontend/src/assets/styles/markdown.css`）。highlight.js 的 `.hljs{background:#fff}` 优先级低，需显式压住；深色下用更高优先级的 `:deep()` 覆盖令牌。
- **论坛头衔/等级徽章双色板**：`FORUM_BADGES` 每项必须同时给 `color/bg` 与 `colorDark/bgDark`，`getBadgeStyle()` 读 `themeState.resolved` 自动选套；后台同名表 `admin-frontend/src/utils/forumBadges.ts` 必须同步补齐。深色用「提亮文字色 + 低透明度同色相底」（如 `colorDark: '#5eead4', bgDark: 'rgba(15,118,110,0.22)'`），保证在 `--fx-card: #1b212a` 上可读又不突兀。**新增徽章只填浅色一套 = 违规**。详见 [forum.md](./forum.md)「徽章唯一权威是常量表」条。

## 新增 UI 的自检清单

1. 浅色与深色各看一遍：文字对比度够不够、底色是否刺眼、边框是否可见。
2. 颜色是走令牌 / CSS 变量，还是 JS 内联？内联的有没有给双套？
3. 主题切换是否即时生效（不刷新页面）？响应式依赖有没有被一次性读法替代？
4. 涉及 Markdown 编辑器 / 代码块 / 图片时，是否命中上面的已知踩坑？
