# 主站 frontend（Vite 7 + Vue 3）独立构建镜像
#
# 通常不直接用：根目录 docker-compose.yml 的 web 服务已在多阶段构建里
# 编译本目录并收进统一 nginx（见 web/Dockerfile 的 build-frontend 阶段）。
# 本文件用于单独构建/推送主站镜像（如需按端独立分发时）。
FROM node:20-alpine AS build

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY . .
RUN npm run build

FROM nginx:stable-alpine

ENV TZ=Asia/Shanghai
RUN rm -f /etc/nginx/conf.d/default.conf

# 站点根即产物根；API 由部署方（统一 web 容器或 1panel OpenResty）反代
COPY --from=build /build/dist/ /usr/share/nginx/html/

EXPOSE 80
