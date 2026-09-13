#!/usr/bin/env bash
#
# dev.sh — 星穹旅驿官网四个子项目一键启动/停止脚本
#
# 仓库没有根级 workspace（四个子项目各自持有 package.json / 依赖），
# 所有命令必须在对应子目录内执行，本脚本负责逐个切换目录并后台拉起。
#
# 用法:
#   ./dev.sh              等同于 start
#   ./dev.sh start        后台启动全部（已运行/端口被占用的自动跳过，不会杀已有进程）
#   ./dev.sh stop         停止由本脚本启动的服务
#   ./dev.sh restart      stop + start
#   ./dev.sh status       查看四个服务的运行状态
#   ./dev.sh logs [name]  跟看日志；name ∈ backend|frontend|wiki|admin，缺省各打最后 20 行
#
# 端口:
#   backend   :5000  (backend/run.py 固定)
#   frontend  :5173  (vite 默认)
#   wiki      :5175  (脚本用 --port 指定，避开 frontend 的 5173，不改 wiki 配置文件)
#   admin     :3005  (读取 admin-frontend/.env.development 的 VITE_PORT，缺省 8848)
#
# 日志与 PID 统一写在 logs/ 下（.gitignore 已忽略该目录）。

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

G='\033[32m'; Y='\033[33m'; R='\033[31m'; C='\033[36m'; N='\033[0m'
ok()   { printf "${G}%s${N}\n" "$*"; }
warn() { printf "${Y}%s${N}\n" "$*"; }
err()  { printf "${R}%s${N}\n" "$*"; }
info() { printf "${C}%s${N}\n" "$*"; }

NAMES=(backend frontend wiki admin)
DIRS=("$ROOT/backend" "$ROOT/frontend" "$ROOT/wiki" "$ROOT/admin-frontend")

# admin 端口取自 .env.development 的 VITE_PORT（纯数字），读不到则回退 8848
PORT_ADMIN="$(grep -E '^[[:space:]]*VITE_PORT' "$ROOT/admin-frontend/.env.development" 2>/dev/null | head -n 1 | grep -oE '[0-9]+' || true)"
PORT_ADMIN="${PORT_ADMIN:-8848}"
PORTS=(5000 5173 5175 "$PORT_ADMIN")

pid_file() { echo "$LOG_DIR/$1.pid"; }
log_file() { echo "$LOG_DIR/$1.log"; }

port_in_use() {
  (: < "/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

is_running() {
  local f pid
  f="$(pid_file "$1")"
  [ -f "$f" ] || return 1
  pid="$(cat "$f" 2>/dev/null)"
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  rm -f "$f"
  return 1
}

# 各服务的启动命令（在其子目录内执行）
cmd_for() {
  case "$1" in
    backend)
      echo "python3 run.py"
      ;;
    frontend)
      # --strictPort：被占用就报错而不是悄悄换端口，与脚本“跳过已占用”逻辑保持一致
      echo "npm run dev -- --port 5173 --strictPort"
      ;;
    wiki)
      # wiki 默认端口同为 5173，这里固定 5175 避免与 frontend 冲突
      echo "npm run dev -- --port 5175 --strictPort"
      ;;
    admin)
      # 优先直接调 vite（复刻 package.json dev 脚本里的 NODE_OPTIONS），绕开 pnpm 的
      # verify-deps 自动 install 环节；找不到 .bin/vite 时才退回 pnpm run dev
      if [ -x "$ROOT/admin-frontend/node_modules/.bin/vite" ]; then
        echo "NODE_OPTIONS=--max-old-space-size=4096 ./node_modules/.bin/vite --port $PORT_ADMIN --strictPort"
      else
        echo "pnpm run dev"
      fi
      ;;
  esac
}

# 缺依赖时自动补装（只装缺的那份）
ensure_deps() {
  case "$1" in
    frontend|wiki)
      if [ ! -d "$ROOT/$1/node_modules" ]; then
        warn "  $1 缺少 node_modules，先执行 npm install ..."
        (cd "$ROOT/$1" && npm install) || return 1
      fi
      ;;
    admin)
      if [ ! -d "$ROOT/admin-frontend/node_modules" ]; then
        warn "  admin-frontend 缺少 node_modules，先执行 pnpm install ..."
        (cd "$ROOT/admin-frontend" && pnpm install) || return 1
      fi
      ;;
    backend)
      if ! python3 -c "import fastapi, uvicorn, sqlalchemy, aiosqlite" 2>/dev/null; then
        warn "  backend 缺少 Python 依赖，先安装 requirements.txt ..."
        python3 -m pip install --user --break-system-packages -r "$ROOT/backend/requirements.txt" || return 1
      fi
      ;;
  esac
}

start_one() {
  local i="$1" name port dir cmd pidfile
  name="${NAMES[i]}"; port="${PORTS[i]}"; dir="${DIRS[i]}"
  pidfile="$(pid_file "$name")"

  if is_running "$name"; then
    info "  $name 已在运行 (pid $(cat "$pidfile"), :$port)，跳过"
    return 0
  fi

  if port_in_use "$port"; then
    warn "  端口 :$port 已被其他进程占用，跳过 $name（若非本脚本启动的服务请自行确认）"
    return 0
  fi

  ensure_deps "$name" || { err "  $name 依赖安装失败，跳过"; return 1; }

  cmd="$(cmd_for "$name")"
  printf '\n===== %s start: %s =====\n' "$(date '+%F %T')" "$cmd" >> "$(log_file "$name")"
  (
    cd "$dir" || exit 1
    setsid bash -c "$cmd" >> "$(log_file "$name")" 2>&1 &
    echo $! > "$pidfile"
  )

  if is_running "$name"; then
    ok "  $name 已启动 (pid $(cat "$pidfile"), :$port)"
  else
    err "  $name 启动失败，查看日志: ./dev.sh logs $name"
  fi
}

do_start() {
  info "启动星穹旅驿 dev 环境（日志目录: logs/）"
  local i
  for i in "${!NAMES[@]}"; do
    start_one "$i"
  done
  wait_all_up
  echo
  do_status
}

# 起完后统一等端口就绪（vite/wiki/admin 冷启动可能要几秒）
wait_all_up() {
  local i name port pending deadline=$((SECONDS + 30))
  while [ $SECONDS -lt $deadline ]; do
    pending=0
    for i in "${!NAMES[@]}"; do
      name="${NAMES[i]}"; port="${PORTS[i]}"
      if is_running "$name" && ! port_in_use "$port"; then
        pending=1
      fi
    done
    [ "$pending" -eq 0 ] && return 0
    sleep 1
  done
}

stop_one() {
  local name="$1" pidfile pid waited=0
  pidfile="$(pid_file "$name")"
  [ -f "$pidfile" ] || return 0
  pid="$(cat "$pidfile" 2>/dev/null || true)"

  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    # 服务经 setsid 独立成进程组，连子进程（uvicorn reloader / vite / esbuild）一起杀
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null
    while kill -0 "$pid" 2>/dev/null && [ $waited -lt 10 ]; do
      sleep 0.5; waited=$((waited + 1))
    done
    kill -0 "$pid" 2>/dev/null && kill -9 -- "-$pid" 2>/dev/null
    ok "  $name 已停止 (pid $pid)"
  else
    info "  $name 未在运行"
  fi
  rm -f "$pidfile"
}

do_stop() {
  info "停止 dev 服务..."
  local i
  for i in "${!NAMES[@]}"; do
    stop_one "${NAMES[i]}"
  done
}

do_status() {
  local i name port pidfile pid state
  printf '%-10s %-8s %-12s %s\n' "服务" "端口" "状态" "地址"
  for i in "${!NAMES[@]}"; do
    name="${NAMES[i]}"; port="${PORTS[i]}"
    pidfile="$(pid_file "$name")"
    if [ -f "$pidfile" ]; then pid="$(cat "$pidfile" 2>/dev/null)"; else pid=""; fi
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      state="$(printf '%s运行中%s (pid %s)' "$G" "$N" "$pid")"
    elif port_in_use "$port"; then
      state="$(printf '%s端口被占用%s(非本脚本启动)' "$Y" "$N")"
    else
      state="$(printf '%s未启动%s' "$R" "$N")"
    fi
    printf '%-10s :%-7s %b\n' "$name" "$port" "$state"
  done
  echo
  echo "官网 http://localhost:5173   Wiki http://localhost:5175   后台 http://localhost:$PORT_ADMIN   API http://localhost:5000/docs"
}

do_logs() {
  local name="${1:-}" f
  if [ -n "$name" ]; then
    f="$(log_file "$name")"
    [ -f "$f" ] || { err "没有 $name 的日志: $f"; exit 1; }
    tail -n 50 -f "$f"
  else
    local n
    for n in "${NAMES[@]}"; do
      f="$(log_file "$n")"
      echo "===== $n ($(log_file "$n")) ====="
      [ -f "$f" ] && tail -n 20 "$f" || echo "(暂无日志)"
      echo
    done
  fi
}

usage() {
  sed -n '2,25p' "$0" | grep -E '^#' | sed 's/^# \{0,1\}//'
}

case "${1:-start}" in
  start)   do_start ;;
  stop)    do_stop ;;
  restart) do_stop; sleep 1; do_start ;;
  status)  do_status ;;
  logs)    shift || true; do_logs "${1:-}" ;;
  help|-h|--help) usage ;;
  *) err "未知命令: $1"; usage; exit 1 ;;
esac
