#!/bin/sh
# ============================================================================
# 后端容器入口：先拉起镜像内 cron（/etc/cron.d/xqly-jobs），再 exec 主进程。
#
# 为什么把定时任务放进镜像（而不是宿主机 root crontab + docker exec）：
#   宿主机条目不随镜像走，容器改名 / 换 tag / 换部署目录后条目会静默失效
#   （2026-10-31 容器名改名即踩过，任务整整一段时间没跑且无任何报错）。
#   放进镜像后：定时逻辑随镜像 tag 版本化、日志进 docker logs、
#   且不再依赖宿主机 PATH 里有 docker 二进制。
#
# 用 exec 顶替 PID1：uvicorn 能收到 SIGTERM 正常退出，docker stop 不被 cron
# 拖住；cron 作为后台守护进程与容器同生共死（容器停了它自然消失）。
#
# 关闭内置定时任务：CRON_ENABLED=0（本地只跑 API / 联调时用）。
# ============================================================================
set -e

if [ "${CRON_ENABLED:-1}" = "1" ]; then
    # Debian cron 默认自我 daemonize（不加 -f，前台模式会占住 PID1）；
    # 启动失败不影响 API：宁可少跑一次定时任务，也不能让站点起不来。
    if /usr/sbin/cron; then
        echo "[entrypoint] cron started (/etc/cron.d/xqly-jobs)"
    else
        echo "[entrypoint] WARN: cron failed to start; API continues without scheduled jobs" >&2
    fi
else
    echo "[entrypoint] CRON_ENABLED=0, scheduled jobs disabled"
fi

exec "$@"
