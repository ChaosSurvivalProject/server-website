# syntax=docker/dockerfile:1
# ============================================================================
# 星穹旅驿官网 · 统一前端镜像（web）
#
# 三个前端（主站 frontend / 后台管理 admin-frontend / wiki）在多阶段构建里
# 各自编译成静态产物，最终收进一个 nginx:alpine 单容器统一对外：
#   /        → frontend 构建产物（SPA，history 路由由 try_files 兜底）
#   /admin/  → admin-frontend 构建产物（pure-admin-thin，VITE_PUBLIC_PATH=/admin/）
#   /wiki/   → wiki 构建产物（VitePress，base=/wiki，cleanUrls 靠 try_files）
#   /api     → 反代 xqly-website-backend:5000（SSE location 已单独配四件套）
#
# 与生产拓扑的对应关系：生产是 1panel OpenResty（host 网络）按
# for-deploy/xqly-app.conf 分发到站点目录 + 127.0.0.1:5000；本镜像把同一套
# 路由规则搬进容器（web/nginx.conf），用于自包含部署 / 本地整栈联调。
# 注意：生产构建产物仍按 for-deploy/README.md 在本机构建后投放，不跑本镜像。
# ============================================================================
FROM node:20-alpine AS build-frontend

WORKDIR /build/frontend
# 先只拷贝 manifest 以最大化利用层缓存（依赖不变时跳过 npm ci）
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY frontend/ ./
RUN npm run build
# 产物：/build/frontend/dist


FROM node:20-alpine AS build-admin

WORKDIR /build/admin-frontend
COPY admin-frontend/package.json admin-frontend/pnpm-lock.yaml admin-frontend/.npmrc ./
# lockfileVersion 9.0 → 钉 pnpm 9：pnpm 10 默认拦截依赖构建脚本（esbuild /
# @parcel/watcher / vue-demi 等，ERR_PNPM_IGNORED_BUILDS），pnpm 9 无此限制，
# 且与仓库 lockfile 版本严格匹配
RUN corepack enable \
    && corepack prepare pnpm@9.15.9 --activate \
    && npm config set registry https://registry.npmmirror.com \
    && pnpm config set registry https://registry.npmmirror.com \
    && pnpm install --frozen-lockfile

COPY admin-frontend/ ./
# pnpm-workspace.yaml 是 pnpm 10/11 的构建脚本白名单（allowBuilds），且无 packages
# 字段——pnpm 9 会把目录误判为 workspace 并在 pnpm build 时报
# "packages field missing or empty"。安装已用 pnpm 9 完成（pnpm 9 默认执行全部
# 构建脚本），该文件对 vite build 无用，构建期移除。
RUN rm -f pnpm-workspace.yaml && pnpm build
# 产物：/build/admin-frontend/dist


FROM node:20-alpine AS build-wiki

WORKDIR /build/wiki
COPY wiki/package.json wiki/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY wiki/ ./
RUN npm run build
# 产物：/build/wiki/.vitepress/dist（VitePress 1.x，含 index.md 转出的 404.html）


FROM nginx:stable-alpine

ENV TZ=Asia/Shanghai

# 先清掉发行版默认配置，再放我们的路由规则（web/nginx.conf，规则对齐 for-deploy/xqly-app.conf）
RUN rm -f /etc/nginx/conf.d/default.conf
COPY web/nginx.conf /etc/nginx/conf.d/app.conf

# 三个前端的静态产物按生产站点目录的同款层级归位：
#   /usr/share/nginx/html/           ← frontend dist（站点根）
#   /usr/share/nginx/html/admin/     ← admin dist
#   /usr/share/nginx/html/wiki/      ← wiki .vitepress/dist
COPY --from=build-frontend /build/frontend/dist/ /usr/share/nginx/html/
COPY --from=build-admin    /build/admin-frontend/dist/ /usr/share/nginx/html/admin/
COPY --from=build-wiki     /build/wiki/.vitepress/dist/ /usr/share/nginx/html/wiki/

EXPOSE 80
