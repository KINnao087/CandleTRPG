@echo off
setlocal

set "APP_DIR=%~dp0"
set "BACKEND_HOST=0.0.0.0"
set "BACKEND_PORT=8001"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=5173"

cd /d "%APP_DIR%"

if not exist ".env" (
  if exist ".env.example" copy ".env.example" ".env" >nul
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  py -3 -m venv ".venv" 2>nul
  if errorlevel 1 (
    python -m venv ".venv"
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo Failed to create Python environment. Please install Python 3.11+ and try again.
  pause
  exit /b 1
)

echo Installing backend dependencies...
if exist "wheelhouse" (
  ".venv\Scripts\python.exe" -m pip install --no-index --find-links "wheelhouse" -r "requirements.txt"
) else (
  ".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
)

if errorlevel 1 (
  echo Failed to install backend dependencies.
  pause
  exit /b 1
)

echo Starting backend on http://127.0.0.1:%BACKEND_PORT% ...
start "CandleTRPG Backend" cmd /k ""%APP_DIR%.venv\Scripts\python.exe" -m uvicorn backend.app.api.web_api:app --host %BACKEND_HOST% --port %BACKEND_PORT%"

echo Starting frontend on http://127.0.0.1:%FRONTEND_PORT% ...
start "CandleTRPG Frontend" cmd /k ""%APP_DIR%.venv\Scripts\python.exe" -m http.server %FRONTEND_PORT% --bind %FRONTEND_HOST% --directory frontend_dist"

timeout /t 2 >nul
start "" "http://127.0.0.1:%FRONTEND_PORT%"

echo.
echo CandleTRPG-LAN has started.
echo Local frontend:  http://127.0.0.1:%FRONTEND_PORT%
echo Local backend:   http://127.0.0.1:%BACKEND_PORT%
echo LAN backend:     http://YOUR-LAN-IP:%BACKEND_PORT%
echo.
echo Keep the backend and frontend windows open while playing.
pause
