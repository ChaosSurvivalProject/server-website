# 星穹旅驿 - 服务器网站

基于 Vue 3 + Vite 的前端，搭配 FastAPI + SQLite 的后端。

## 项目结构

```
server-website/
├── frontend/               # Vue 3 前端
│   ├── src/                 # 前端源码
│   ├── public/              # 静态资源
│   ├── node_modules/        # 依赖
│   ├── index.html
│   ├── vite.config.js
│   ├── jsconfig.json
│   ├── package.json
│   └── package-lock.json
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI 应用入口
│   │   ├── database.py      # SQLite 数据库模型 & 连接
│   │   ├── schemas.py       # Pydantic 数据模型
│   │   └── crud.py          # CRUD 操作
│   ├── run.py               # uvicorn 启动脚本
│   ├── seed.py              # 测试数据种子
│   ├── Dockerfile           # Docker 构建文件
│   ├── requirements.txt     # 后端依赖
│   └── .venv/               # (可选) 虚拟环境
├── doc/                     # 接口文档
├── docker-compose.yml       # Docker Compose 编排
├── requirements.txt         # 后端依赖 (同 backend/requirements.txt)
└── README.md
```

## 后端 API

### 安装 & 启动

```bash
cd backend
pip install -r requirements.txt
python3 run.py
# 或: uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

服务启动在 `http://localhost:5000`。

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/announcement/page` | 分页查询公告 (参数: page, pageSize, isPublished) |
| GET | `/announcement/detail/{id}` | 查询公告详情 |
| POST | `/announcement/addWatchCount` | 增加阅读量 (body: `{announcementId}`) |
| POST | `/announcement/create` | 创建公告 (管理员) |
| PUT | `/announcement/update/{id}` | 更新公告 (管理员) |
| DELETE | `/announcement/delete/{id}` | 删除公告 (管理员) |
| GET | `/health` | 健康检查 |

### 数据库

使用 SQLite，数据库文件路径：
- 默认: `data/announcements.db` (项目根目录)
- 可通过环境变量 `ANNOUNCEMENT_DB` 自定义

### 种子数据

```bash
python3 backend/seed.py
```

### Docker 部署

```bash
docker compose up -d --build
```

## 前端

### 安装 & 启动

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器监听 `http://localhost:5173` (Vite 默认端口)。

### 前端配置

前端通过 `frontend/src/config/mc-config.js` 配置 API 地址：

```javascript
// 开发环境
baseApiURL: 'http://localhost:5000'
// 生产环境
baseApiURL: 'https://fcloud.tqclink.cn:5000'
```

修改 `nodeEnv` 切换环境 (`'development'` | `'production'`)。