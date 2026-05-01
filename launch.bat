@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

set "FRONTEND_DIR=%~dp0frontend"
set "FRONTEND_CMD="

where pnpm >nul 2>&1 && set "FRONTEND_CMD=pnpm dev"

if not defined FRONTEND_CMD (
    where npm >nul 2>&1 && set "FRONTEND_CMD=npm run dev"
)

if not defined FRONTEND_CMD (
    where corepack >nul 2>&1 && set "FRONTEND_CMD=corepack pnpm dev"
)

if not defined FRONTEND_CMD (
    echo [ERROR] No JavaScript package manager found.
    echo Install pnpm or Node.js with npm/corepack, then run launch.bat again.
    exit /b 1
)

start "FastAPI Backend" cmd /k "%PYTHON% -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"
start "React Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && %FRONTEND_CMD%"

timeout /t 4 /nobreak >nul
start "" "http://localhost:5173"
