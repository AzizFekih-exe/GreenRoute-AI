@echo off
title GreenRoute AI launcher
echo ====================================================
echo Starting GreenRoute AI Developer Stack...
echo ====================================================

echo [1/2] Starting Flask Backend API on http://localhost:5000...
start "GreenRoute Backend (Flask)" cmd /c "cd backend && python app.py"

if not exist "frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd frontend
  call npm install
  popd
)

echo [2/2] Starting Vite React Frontend on http://localhost:8501...
start "GreenRoute Frontend (React)" cmd /c "cd frontend && npm run dev -- --port 8501 --host 0.0.0.0"

echo ====================================================
echo Services started!
echo - Flask Backend API: http://localhost:5000
echo - React Web UI:      http://localhost:8501
echo ====================================================
pause
