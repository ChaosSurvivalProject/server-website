# 开发指南（安装 · 运行 · 构建）

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 原样下沉的专题文档（内容未改动，仅调整标题层级与文内交叉引用）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

环境要求：Node.js 20.19+（Vite 7 要求）、Python 3.10+。

## 后端

```bash
cd backend
pip install -r requirements.txt
python3 run.py
# 或: uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

服务启动在 `http://localhost:5000`，交互式 API 文档见 `http://localhost:5000/docs`。

## 前端

```bash
cd frontend
npm install
npm run dev
```

开发服务器监听 `http://localhost:5173`（Vite 默认端口）。开发模式下 API 请求直接指向 `http://localhost:5000`（后端已开启 CORS）。

## Wiki

```bash
cd wiki
npm install
npm run dev      # 开发服务器
npm run build    # 构建到 .vitepress/dist/
npm run preview  # 本地预览构建产物
```

站点以 `/wiki` 为 base 部署（见 `.vitepress/config.mts`）。

## 后台管理（admin-frontend）

```bash
cd admin-frontend
pnpm install
pnpm dev      # 开发服务器（端口取 .env.development 的 VITE_PORT，当前 3005，覆盖 .env 的 8848）
pnpm build    # 构建到 dist/（base: /admin/，hash 路由）
```

开发模式下 API 请求经 `vite.config.ts` 的 proxy（`/api`）转发到后端 `http://localhost:5000`。登录账号即后端自动初始化的系统管理员（见 [api-reference.md](./api-reference.md) 的「认证」一节）。

## 种子数据

```bash
cd backend
python3 seed.py
```

## 环境配置（`frontend/.env*` 文件）

站点配置通过 Vite 环境变量提供：`.env` 存放所有模式共用的默认值，`.env.development` / `.env.production` 按构建模式覆盖，本地个性化覆盖写 `.env.local`（已被 gitignore）。`src/config/mc-config.js` 是统一读取层，组件不要直接读 `import.meta.env`。

| 变量 | 说明 | dev 默认 | prod 默认 |
|------|------|----------|-----------|
| `VITE_BASE_API_URL` | API 基础地址 | `http://localhost:5000` | 留空（同源相对路径，由 Nginx 反代到后端） |
| `VITE_SERVER_ID` | 监控接口路由参数（对应后端 `SERVERS` 主服务器 id） | `1` | `1` |
| `VITE_JAVA_VERSIONS` / `VITE_BEDROCK_VERSIONS` | 支持的游戏版本文案 | 见 `.env` | 见 `.env` |
| `VITE_QQ_GROUP_ID` / `VITE_QQ_GROUP_CODE_IMG_URL` / `VITE_QQ_GROUP_INVITE_LINK_URL` | QQ 群信息 | 见 `.env` | 见 `.env` |
| `VITE_ADMIN_URL` | 后台管理入口地址 | `/admin` | `/admin` |
| `VITE_CHAT_WIDGET_ENABLED` | 智能客服悬浮球前端开关（后端 `/kb/info` enabled 为二级开关，两级都开才渲染） | `true` | `true` |
| `VITE_CHAT_WIDGET_TITLE` / `VITE_CHAT_WIDGET_GREETING` / `VITE_CHAT_WIDGET_FAQ` | 客服标题 / 欢迎语 / 首屏示例问题（`\|` 分隔） | 见 `.env` | 见 `.env` |
| `VITE_SERVER_NAME` | 服务器名称（名片验证页 / 总览页展示） | `星穹旅驿` | 同左 |
| `VITE_STAFF_OFFICIAL_URL` | 验证页展示的官方网址（二维码前缀在后端 `STAFF_PUBLIC_BASE_URL`，前端不拼 URL） | 见 `.env` | 同左 |
| `VITE_STAFF_DISCORD_URL` | 官方 Discord 入口（留空则验证页不展示该项） | 留空 | 同左 |
| `VITE_STAFF_ANTI_FRAUD_TEXT` | 防伪提示文案（需求 §9.3，`\|` 分行） | 见 `.env` | 同左 |

环境变量在构建期静态替换，修改后需重启 dev server 或重新构建才生效。
