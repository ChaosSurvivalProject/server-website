@echo off
chcp 65001 >nul
rem ============================================================
rem dev.bat — 星穹旅驿官网 dev 环境一键启动（Windows 版，对应 dev.sh）
rem 每个服务开一个独立窗口：日志直接看窗口，关闭窗口即停止该服务。
rem 首次运行会自动补装缺失依赖（pip install / npm install / pnpm install）。
rem ============================================================

set "ROOT=%~dp0"

echo [1/4] backend   http://localhost:5000/docs
start "backend" cmd /k "cd /d "%ROOT%backend" & python -c ""import fastapi,uvicorn,sqlalchemy,aiosqlite"" >nul 2>&1 || python -m pip install -r requirements.txt & python run.py"

echo [2/4] frontend  http://localhost:5173
start "frontend" cmd /k "cd /d "%ROOT%frontend" & (if not exist node_modules (npm install)) & npm run dev -- --port 5173 --strictPort"

echo [3/4] wiki      http://localhost:5174
start "wiki" cmd /k "cd /d "%ROOT%wiki" & (if not exist node_modules (npm install)) & npm run dev -- --port 5174 --strictPort"

echo [4/4] admin     http://localhost:3005
start "admin" cmd /k "cd /d "%ROOT%admin-frontend" & (if not exist node_modules (pnpm install)) & pnpm dev"

echo.
echo 四个服务已在独立窗口中启动，关闭对应窗口即可停止。
echo 官网 http://localhost:5173   Wiki http://localhost:5174   后台 http://localhost:3005   API http://localhost:5000/docs
pause
