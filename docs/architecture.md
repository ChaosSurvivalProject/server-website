# 项目结构

> 本文是 2026-11-07 文档重构时从 [README.md](../README.md) 原样下沉的专题文档（内容未改动，仅调整标题层级与文内交叉引用）；入口与快速开始见 [README.md](../README.md)。文中 `代码样式` 的路径均相对仓库根目录。

```
server-website/
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── api/                 # axios 实例、接口封装、统一错误处理
│   │   ├── assets/              # 图片、字体等静态资源
│   │   ├── components/          # 通用组件（NavBar、ChatWidget、OnlineCounter、Leaderboard、TrendChart 等）
│   │   ├── config/mc-config.js  # 站点配置统一读取层（值来自 .env 环境变量）
│   │   ├── router/              # 路由定义
│   │   ├── utils/               # 工具函数
│   │   ├── views/               # 页面组件
│   │   ├── App.vue              # 根组件（导航栏 + 路由视图 + 页脚）
│   │   └── main.js              # 应用入口
│   ├── .env                     # 站点配置默认值（Vite 环境变量，随仓库提交）
│   ├── .env.development         # 开发模式覆盖（API 指向本地 FastAPI）
│   ├── .env.production          # 生产模式覆盖（API 同源相对路径）
│   ├── public/                  # 原样复制的静态资源
│   ├── index.html
│   └── vite.config.js
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口与公告路由
│   │   ├── database.py          # SQLAlchemy 模型 & 异步引擎/会话（含知识库 4 表 + WAL + FTS5）
│   │   ├── schemas.py           # Pydantic 模型（camelCase 别名）
│   │   ├── crud.py              # 公告 CRUD 操作
│   │   ├── faction_beta.py      # 阵营对战内测申请（用户提交 + 管理员审核）
│   │   ├── monitor.py           # 服务器监控（DB 持久化注册表 + TCP 探测）
│   │   ├── config.py            # 知识库配置读取（零依赖 .env 加载 → 模块级 KB 对象）
│   │   ├── kb_ingest.py         # 知识库：Markdown 清洗/切片/Embedding（纯逻辑）
│   │   ├── kb_index.py          # 知识库：内存向量索引（版本失效 + TopK，纯 stdlib）
│   │   ├── kb_retrieve.py       # 知识库：向量 + FTS5 trigram + RRF 混合检索
│   │   ├── kb_llm.py            # 知识库：OpenAI 兼容 chat 流式客户端（httpx）
│   │   ├── kb.py                # 知识库：/api/kb/* 全部路由（SSE 问答 + 限流 + 管理接口）
│   │   ├── staff.py             # 员工名片：/api/staff/* 全部路由（验证页 + 台账 + 到期回写 + 二维码 + CSV）
│   │   ├── forum.py             # 社区论坛：/api/forum/* 全部路由（公开 / 登录用户 / 管理员三组）
│   │   ├── resource_center.py   # 资源中心：/api/resources/* + /download/asset/{id}（公开只读 / 管理员 / 下载 302 跳转）
│   │   ├── pydantic_models.py   # 资源中心请求模型（camelCase 别名）
│   │   └── forum_core.py        # 社区论坛轻量核心（纯 SQLAlchemy，供 CLI 复用：RECYCLE_DAYS / purge_due / cascade_delete_article）
│   ├── kb_sync.py               # wiki → 知识库 同步脚本（CLI，按 MD5 增量）
│   ├── staff_expire.py          # 员工名片到期检查脚本（CLI，镜像内 cron 每日一次）
│   ├── forum_purge.py           # 论坛回收站超期清理脚本（CLI，镜像内 cron 每日一次 + 启动兜底）
│   ├── run.py                   # uvicorn 启动脚本
│   ├── seed.py                  # 测试数据种子
│   ├── crontab                  # 镜像内定时任务定义（→ /etc/cron.d/xqly-jobs）
│   ├── docker-entrypoint.sh     # 容器入口：先起 cron 再 exec 主进程（CRON_ENABLED=0 可关）
│   ├── Dockerfile
│   ├── requirements.txt
│   └── data/                    # SQLite 数据库文件（gitignore；含密钥的 .env 亦已 gitignore）
├── docker-compose.yml           # 根编排：xqly-website-backend + xqly-website-web（统一前端，见 docs/deployment.md）
├── web/                         # 统一前端镜像：web/Dockerfile（三前端多阶段构建）+ web/nginx.conf（路由）
├── wiki/                        # VitePress 文档站
│   ├── .vitepress/config.mts    # 站点配置（base: /wiki）
│   ├── for-new/                 # 萌新指南（进服教程、玩家条例、FAQ）
│   ├── management/              # 服务器管理（管理员条例）
│   ├── develop/                 # 服务器建设（发展路线、Issues）
│   ├── index.md                 # 首页（hero 布局）
│   └── package.json
├── admin-frontend/              # 后台管理前端（pure-admin-thin，部署在 /admin/）
│   ├── src/
│   │   ├── api/                 # 接口封装（announcement / server / user / factionBeta / kb / staff / resourceCenter / routes）
│   │   ├── components/          # 通用组件（RePureTableBar、ReDialog、ReAuth 等 pure-admin 封装）
│   │   ├── config/              # 平台配置读取层（Title 等，值来自 public/platform-config.json）
│   │   ├── directives/          # 自定义指令（auth / perms / ripple / longpress 等）
│   │   ├── layout/              # 后台框架（侧边菜单 + 顶栏 + 多标签页）
│   │   ├── plugins/             # Element Plus / ECharts 全局注册
│   │   ├── router/              # 路由与守卫（modules/home.ts 业务路由、remaining.ts 登录与错误页）
│   │   ├── store/modules/       # Pinia 模块（user 存 token/role、permission、multiTags 等）
│   │   ├── utils/http/          # PureHttp：axios 封装（JWT 注入、{code,message,data} 解包、错误提取）
│   │   ├── views/               # 页面（login、announcement、server、faction-beta、kb、user、staff、resource、error）
│   │   └── main.ts              # 应用入口
│   ├── .env / .env.development / .env.production   # 端口、base 路径、路由模式
│   ├── public/platform-config.json                 # 平台标题等运行时配置
│   ├── vite.config.ts           # dev proxy 把 API 前缀转发到后端 :5000
│   └── package.json
└── README.md
```
