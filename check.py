"""
DEPRECATED: этот модуль устарел и не используется в текущем проекте.
Проверка и установка обновлений выполняются через updater.py.
Файл оставлен только для совместимости и справки.
"""
import os
import sys
import requests
import subprocess
import wx
from i18n import tr
from utils import Result


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def parse_version_txt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "FileVersion" in line:
                    parts = line.split("'")
                    if len(parts) >= 4:
                        return parts[3]
    except (FileNotFoundError, UnicodeDecodeError, OSError):
        pass
    return None


def version_tuple(v):
    return tuple(int(x) for x in v.strip().replace("v", "").split("."))

def create_update_bat(zip_filename):
    bat_code = f"""@echo off
ping 127.0.0.1 -n 4 > nul
powershell -command "Expand-Archive -Path '{zip_filename}' -DestinationPath 'temp'"
move /Y "temp\\updater.exe" "updater.exe"
rd /s /q temp
del "{zip_filename}"
del "%~f0"
"""
    bat_path = os.path.join(get_app_path(), "update_later.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_code)

def check_update(parent_frame):
    version_path = resource_path("version.txt")
    current_version = parse_version_txt(version_path)

    if not current_version:
        error_message = tr("update.version_unknown")
        wx.CallAfter(wx.MessageBox, error_message, tr("error.title"), wx.OK | wx.ICON_ERROR)
        return Result(False, error=error_message)

    try:
        response = requests.get("https://api.github.com/repos/r1oaz/blind_log/releases/latest")
        response.raise_for_status()
        data = response.json()
        latest_version = data.get("tag_name")
        download_url = None

        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".zip"):
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            error_message = tr("update.no_archive")
            wx.CallAfter(wx.MessageBox, error_message, tr("error.title"), wx.OK | wx.ICON_ERROR)
            return Result(False, error=error_message)

    except requests.RequestException as e:
        error_message = tr("update.error").format(error=e)
        wx.CallAfter(wx.MessageBox, error_message, tr("error.title"), wx.OK | wx.ICON_ERROR)
        return Result(False, error=error_message)

    if not latest_version:
        error_message = tr("update.version_unknown")
        wx.CallAfter(wx.MessageBox, error_message, tr("error.title"), wx.OK | wx.ICON_ERROR)
        return Result(False, error=error_message)

    if version_tuple(latest_version) <= version_tuple(current_version):
        message = tr("update.up_to_date").format(version=current_version)
        wx.CallAfter(wx.MessageBox, message, tr("update.title"), wx.OK | wx.ICON_INFORMATION)
        return Result(True, data={"update_available": False, "current_version": current_version})

    dlg = wx.MessageDialog(
        parent_frame,
        tr("update.available").format(version=latest_version),
        tr("update.title"),
        wx.YES_NO | wx.ICON_QUESTION
    )

    if dlg.ShowModal() == wx.ID_NO:
        dlg.Destroy()
        return Result(True, data={"update_available": False})

    dlg.Destroy()

    pid = os.getpid()

    # Определяем, какой файл запускать: updater.py или updater.exe
    if getattr(sys, 'frozen', False):
        # Запуск из упакованного .exe
        updater_path = os.path.join(get_app_path(), "updater.exe")
    else:
        # Запуск из скрипта
        updater_path = os.path.join(get_app_path(), "updater.py")

    try:
        if updater_path.endswith(".py"):
            # Запуск updater.py через интерпретатор Python
            subprocess.Popen([
                sys.executable, updater_path,
                "--url", download_url,
                "--pid", str(pid)
            ])
        else:
            # Запуск updater.exe
            subprocess.Popen([
                updater_path,
                "--url", download_url,
                "--pid", str(pid)
            ])
        parent_frame.Close()
        return Result(True, data={"update_available": True})
    except (OSError, subprocess.SubprocessError) as e:
        error_message = tr("update.start_error").format(error=e)
        wx.CallAfter(wx.MessageBox, error_message, tr("error.title"), wx.OK | wx.ICON_ERROR)
        return Result(False, error=error_message)
