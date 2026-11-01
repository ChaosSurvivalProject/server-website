FROM python:3.14-slim

WORKDIR /app

# Install dependencies
# 注意：构建上下文是项目根目录（docker-compose.yml 的 context: ..），
# 所以这里必须写 backend/requirements.txt，不能写 requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 定时任务运行时（镜像内 cron，见 backend/crontab 与 docker-entrypoint.sh）：
#   - cron：Debian cron 守护进程，读取 /etc/cron.d/xqly-jobs
#   - tzdata：cron 按 /etc/localtime 调度（Python 侧另有 pip 的 tzdata）
#   - libpam-runtime / libpam-modules：slim 镜像不带 PAM 模块，缺了 cron 拉起
#     任务会报 `Module is unknown` 并静默失败（不是任务写错，是运行时缺件）
# 只在最终层装、并清理 apt 列表，避免把构建缓存留在镜像里。
# DEBIAN_FRONTEND 必须显式给：tzdata 的 debconf 在无 TTY 的构建里可能等待输入
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      cron tzdata libpam-runtime libpam-modules \
 && rm -rf /var/lib/apt/lists/* \
 && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
 && echo "Asia/Shanghai" > /etc/timezone

# Copy application
COPY backend/ ./backend/

# 镜像内定时任务：随镜像版本发布（不再依赖宿主机 root crontab + docker exec）
COPY backend/crontab /etc/cron.d/xqly-jobs
# /etc/cron.d 下的文件必须 root 属主、非 world-writable，否则 cron 静默跳过
RUN chown root:root /etc/cron.d/xqly-jobs && chmod 0644 /etc/cron.d/xqly-jobs

# Create data directory
RUN mkdir -p /app/data

# 入口脚本：先拉起 cron 再 exec 主进程（CRON_ENABLED=0 可关闭）
COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "backend/run.py"]
