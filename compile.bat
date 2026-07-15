@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

set PYTHON=%~dp0\.venv\Scripts\python.exe

echo ================================
echo проверяем окружение и устанавливаем зависимости
echo ================================
"%PYTHON%" -m pip install -r "%~dp0requirements.txt"
"%PYTHON%" -m pip install pyinstaller

echo ================================
echo собираем файл программы
echo ================================
rmdir /s /q "%~dp0build"
rmdir /s /q "%~dp0dist"
"%PYTHON%" -m PyInstaller "%~dp0Blind_log.spec"
pause