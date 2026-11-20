@echo off
chcp 65001 >nul
copy /y "%~dp0Launcher.bat" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\" >nul
if %errorlevel%==0 (
  echo Готово! Лаунчер будет запускаться вместе с Windows.
  echo Чтобы убрать автозапуск: Win+R, набери shell:startup и удали Launcher.bat
) else (
  echo Не получилось скопировать. Запусти этот файл ещё раз.
)
pause
