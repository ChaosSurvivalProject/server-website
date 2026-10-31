# wiki（VitePress 1.6）独立构建镜像
#
# 通常不直接用：根目录 docker-compose.yml 的 web 服务已在多阶段构建里
# 编译本目录并收进统一 nginx（见 web/Dockerfile 的 build-wiki 阶段）。
# 本文件用于单独构建/推送 wiki 镜像（如需按端独立分发时）。
#
# 注意：VitePress 产物在 .vitepress/dist/（不在根 dist/）；VitePress 构建期
# 需要一个可写缓存目录（XDG_CACHE_HOME），root 下默认也能落盘，这里显式指向
# /tmp 保证只读场景不炸。
FROM node:20-alpine AS build

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY . .
ENV XDG_CACHE_HOME=/tmp/.cache
RUN npm run build

FROM nginx:stable-alpine

ENV TZ=Asia/Shanghai
RUN rm -f /etc/nginx/conf.d/default.conf

# 此镜像只含站点产物；对外必须挂在 /wiki/ 子路径下（base=/wiki 已打进产物）。
# 如独立跑容器，请自行在 nginx 里把 root 指向 /usr/share/nginx/html/wiki
# 并补 /wiki/ 的 try_files $uri $uri.html $uri/ =404（见 web/nginx.conf）。
COPY --from=build /build/.vitepress/dist/ /usr/share/nginx/html/wiki/

EXPOSE 80
