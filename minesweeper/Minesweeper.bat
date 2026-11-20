@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
  echo.
  echo ===== ОШИБКА - пришли скрин этого окна =====
  pause
)
