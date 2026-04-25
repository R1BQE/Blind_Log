"""
УСТАРЕВШИЙ МОДУЛЬ — не используется в проекте.
Проверка и установка обновлений выполняется через updater.py.
Оставлен для справки. Можно удалить.
"""
import os
import sys
import requests
import subprocess
import wx
from i18n import tr


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
    except FileNotFoundError:
        wx.CallAfter(wx.MessageBox, tr("version_file_not_found"), tr("error.title"), wx.ICON_ERROR)
    except Exception as e:
        wx.CallAfter(wx.MessageBox, tr("version_read_error").format(e=e), tr("error.title"), wx.ICON_ERROR)
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
        wx.CallAfter(wx.MessageBox, tr("update.version_unknown"), tr("error.title"), wx.ICON_ERROR)
        return

    try:
        response = requests.get("https://api.github.com/repos/r1oaz/blind_log/releases/latest")
        response.raise_for_status()
        data = response.json()
        latest_version = data["tag_name"]
        download_url = None

        for asset in data["assets"]:
            if asset["name"].endswith(".zip"):
                download_url = asset["browser_download_url"]
                break

        if not download_url:
            wx.CallAfter(wx.MessageBox, tr("update.no_archive"), tr("error.title"), wx.ICON_ERROR)
            return

    except requests.RequestException as e:
        wx.CallAfter(wx.MessageBox, tr("update.error").format(error=e), tr("error.title"), wx.ICON_ERROR)
        return

    if version_tuple(latest_version) <= version_tuple(current_version):
        wx.CallAfter(wx.MessageBox, tr("update.up_to_date").format(version=current_version), tr("update.title"), wx.ICON_INFORMATION)
        return

    dlg = wx.MessageDialog(
        parent_frame,
        tr("update.available").format(version=latest_version),
        tr("update.title"),
        wx.YES_NO | wx.ICON_QUESTION
    )

    if dlg.ShowModal() == wx.ID_NO:
        dlg.Destroy()
        return

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
    except Exception as e:
        wx.CallAfter(wx.MessageBox, tr("update.start_error").format(error=e), tr("error.title"), wx.ICON_ERROR)
