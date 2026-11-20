@echo off
setlocal
set "SCRIPT=%~dp0main.py"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw "%SCRIPT%"
) else (
  start "" python "%SCRIPT%"
)
endlocal
