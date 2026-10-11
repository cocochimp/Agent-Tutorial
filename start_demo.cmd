@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (
  python -X utf8 launch.py
) else (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Please install Python 3.11+ and enable Add Python to PATH.
    pause
    exit /b 1
  )
  py -3 -X utf8 launch.py
)
if errorlevel 1 pause
