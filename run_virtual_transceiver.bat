@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "tools\virtual_transceiver_web.py"
    goto :eof
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "tools\virtual_transceiver_web.py"
    goto :eof
)

echo Python 3 не найден. Установите Python или создайте .venv в каталоге Blind_Log.
pause
