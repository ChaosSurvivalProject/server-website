# 星穹旅驿 · 服务器网站

星穹旅驿 Minecraft 服务器的官方网站。单仓库（monorepo）包含四个**相互独立**的子项目（无根级 workspace，命令须在对应子目录内执行）：

| 模块 | 说明 | 技术栈 |
|------|------|--------|
| `frontend/` | 官网前端（首页、公告、社区论坛、资源中心、员工名片验证） | Vue 3 + Vite + Vue Router + Axios + ECharts |
| `backend/` | 官网后端（公告、认证、论坛、资源中心、员工名片、服务器监控、知识库智能客服） | FastAPI + SQLAlchemy (async) + SQLite (aiosqlite) + Pydantic v2 |
| `wiki/` | 服务器文档站（同时是知识库的单一数据源） | VitePress |
| `admin-frontend/` | 后台管理前端（内容运营 / 社区管理 / 员工管理 / 资源中心 / 智能客服 / 系统管理） | Vue 3 + TypeScript + Element Plus + Pinia（[pure-admin-thin](https://github.com/pure-admin/pure-admin-thin)） |

## 功能特性

- 官网 + 公告系统：富文本 / Markdown 双格式公告；先审后发的社区论坛（两级评论、回收站、站内信通知）
- 资源中心：后台手动维护资源 / 版本 / 下载资产元数据，前台列表筛选 + 详情页，下载经 `/download/asset/{id}` 302 跳转 GitHub 并记录「下载跳转次数」（非 GitHub 实际下载量）
- 员工名片：二维码扫码验证页 + 管理员台账（撤销 / 续期 / 换码 / CSV 导出）
- 智能客服：基于 wiki 知识库的检索增强问答（向量 + FTS5 混合检索、SSE 流式回答）
- 服务器监控：游戏服务器地址后台可维护（DB 持久化），首页在线状态与排行榜
- 服务器文档站：VitePress（挂载于 `/wiki`），萌新指南 / 服务器管理 / 服务器建设三分区

## 快速开始

环境要求：Node.js 20.19+（Vite 7 要求）、Python 3.10+。

```bash
# 后端 (FastAPI, :5000)
cd backend
pip install -r requirements.txt
python3 run.py            # 开发模式（uvicorn --reload）；交互式 API 文档见 http://localhost:5000/docs

# 前端 (Vite, :5173)
cd frontend
npm install
npm run dev               # http://localhost:5173，开发模式 API 直连本地后端 :5000
```

其他子项目：`cd wiki && npm install && npm run dev`（VitePress，构建产物 `.vitepress/dist/`）；`cd admin-frontend && pnpm install && pnpm dev`（后台管理，dev 端口 3005，API 代理到后端 :5000）。

可选：`cd backend && python3 seed.py` 写入示例公告数据；在仓库根目录 `docker compose up -d --build` 起后端 + 统一前端容器（见 [docs/deployment.md](docs/deployment.md)）。完整安装 / 构建 / 环境变量说明见 [docs/development.md](docs/development.md)。

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 项目结构：完整目录树与各文件职责 |
| [docs/development.md](docs/development.md) | 开发指南：四子项目安装 / 运行 / 构建、种子数据、主站环境变量 |
| [docs/api-reference.md](docs/api-reference.md) | 后端 API 参考：全部接口表、SSE 帧协议、知识库同步脚本 |
| [docs/database.md](docs/database.md) | 数据库：SQLite 连接（NullPool）、双格式正文、论坛表结构 |
| [docs/frontend.md](docs/frontend.md) | 主站前端：页面路由、Markdown 渲染管线、关键组件与 API 层 |
| [docs/admin-frontend.md](docs/admin-frontend.md) | 后台管理前端：菜单结构、页面路由、HTTP 层、环境配置 |
| [docs/deployment.md](docs/deployment.md) | 部署：Docker Compose 与生产 Nginx 同域分发 |
| [docs/agents/](docs/agents/) | AI 协作规约原文（[AGENTS.md](AGENTS.md) 各小节的完整版） |
| [AGENTS.md](AGENTS.md) | AI 编码助手规约骨架：硬性禁区 + 常用命令 |
| [for-deploy/README.md](for-deploy/README.md) | 生产部署留档说明（nginx conf 快照、定时任务迁移） |
| [TODO.md](TODO.md) | 已知遗留与后续计划 |
| `docs/论坛/`、`docs/员工管理/`、`docs/智能客服/`、`docs/站内信/` | 各模块 PRD 与方案文档 |

## 参与 / 支持

- 开发规约与提交流程见 [AGENTS.md](AGENTS.md)；提交信息使用 Conventional Commits 前缀，描述用中文。
- 玩家社区：QQ 群 942235691（站点内同源展示，见 `frontend/.env`）。

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。
