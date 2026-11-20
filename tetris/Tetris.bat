@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" /b pythonw main.py && exit /b
)
python main.py
if errorlevel 1 (
  echo.
  echo ===== ОШИБКА ЗАПУСКА — пришли скрин этого окна =====
  pause
)
