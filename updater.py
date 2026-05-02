import os
import sys
import zipfile
import requests
import subprocess
import shutil
import logging
import threading
import wx
import uuid

from i18n import tr
from utils import resource_path, get_app_path, get_version, Result

logger = logging.getLogger(__name__)


def version_tuple(v):
    """Преобразует строку версии в кортеж чисел."""
    return tuple(int(x) for x in v.strip().replace("v", "").split("."))

def check_update(parent_frame, silent_if_latest=False):
    """Проверяет наличие обновлений и запускает процесс обновления в фоне."""
    thread = threading.Thread(target=_check_update_worker, args=(parent_frame, silent_if_latest), daemon=True)
    thread.start()
    return thread


def _check_update_worker(parent_frame, silent_if_latest):
    current_version = get_version()

    if not current_version:
        wx.CallAfter(wx.MessageBox, tr("update.version_unknown"), tr("error.title"), wx.ICON_ERROR)
        return

    try:
        response = requests.get("https://api.github.com/repos/r1oaz/blind_log/releases/latest", timeout=15)
        response.raise_for_status()
        data = response.json()
        latest_version = data["tag_name"]
        download_url = None
        changelog = data.get("body", "")

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
        if not silent_if_latest:
            wx.CallAfter(wx.MessageBox, tr("update.up_to_date").format(version=current_version), tr("update.title"), wx.ICON_INFORMATION)
        return

    wx.CallAfter(_show_update_dialog, parent_frame, latest_version, current_version, changelog, download_url)


def _show_update_dialog(parent_frame, latest_version, current_version, changelog, download_url):
    dlg = wx.Dialog(parent_frame, title=tr("update.title"), size=(600, 500))
    vbox = wx.BoxSizer(wx.VERTICAL)
    info = wx.StaticText(dlg, label=tr("update.changelog_info"))
    vbox.Add(info, 0, wx.ALL, 10)
    text_ctrl = wx.TextCtrl(dlg, value=changelog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    vbox.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 10)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_update = wx.Button(dlg, label=tr("button.update"))
    btn_cancel = wx.Button(dlg, label=tr("button.cancel"))
    btn_sizer.Add(btn_update, 0, wx.RIGHT, 10)
    btn_sizer.Add(btn_cancel, 0)
    vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
    dlg.SetSizer(vbox)

    result = [None]

    def on_update(evt):
        result[0] = True
        dlg.Close()

    def on_cancel(evt):
        result[0] = False
        dlg.Close()

    btn_update.Bind(wx.EVT_BUTTON, on_update)
    btn_cancel.Bind(wx.EVT_BUTTON, on_cancel)
    dlg.ShowModal()
    dlg.Destroy()

    if not result[0]:
        return

    _start_download_thread(download_url, parent_frame)


def _start_download_thread(download_url, parent_frame):
    progress_dialog = wx.ProgressDialog(
        "Загрузка обновления",
        "Подготовка к загрузке...",
        maximum=100,
        parent=parent_frame,
        style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT
    )
    cancel_event = threading.Event()

    def _update_progress_ui(percent, message):
        keep_going = progress_dialog.Update(percent, message)
        if not keep_going:
            cancel_event.set()

    def update_progress(percent, message):
        wx.CallAfter(_update_progress_ui, percent, message)

    def worker():
        result = _download_and_update_worker(download_url, parent_frame, update_progress, cancel_event)
        wx.CallAfter(_on_download_finished, result, progress_dialog, parent_frame)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def _on_download_finished(result, progress_dialog, parent_frame):
    try:
        if progress_dialog:
            progress_dialog.Destroy()
    except Exception:
        pass

    if not result.success:
        wx.MessageBox(tr("update.error").format(error=result.error), tr("error.title"), wx.OK | wx.ICON_ERROR)
    else:
        if parent_frame is not None and parent_frame.IsShown():
            parent_frame.Close()


def _download_and_update_worker(download_url, parent_frame, progress_callback=None, cancel_event=None):
    """Загружает архив обновления и сохраняет его на диск."""
    base_temp = os.path.join(get_app_path(), "temp")
    try:
        if os.path.exists(base_temp):
            shutil.rmtree(base_temp)
    except Exception:
        pass
    temp_dir = os.path.join(base_temp, str(uuid.uuid4()))
    zip_path = os.path.join(temp_dir, "update.zip")

    try:
        os.makedirs(temp_dir, exist_ok=True)

        logger.info(f"Скачиваем обновление из {download_url}")
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0 and progress_callback is not None:
                        percent = int(downloaded_size * 100 / total_size)
                        progress_callback(percent, f"Загружено {percent}%")
                    if cancel_event is not None and cancel_event.is_set():
                        logger.info("Загрузка отменена пользователем.")
                        return Result(False, error="Загрузка отменена пользователем.")

        logger.info(f"Архив загружен: {zip_path}")

        if total_size and downloaded_size != total_size:
            raise IOError("Размер файла не совпадает с объявленным")

        extract_subdir = os.path.join(temp_dir, "new")
        os.makedirs(extract_subdir, exist_ok=True)
        if not extract_zip(zip_path, extract_subdir):
            return Result(False, error="Ошибка распаковки архива.")

        create_update_bat(extract_subdir)
        bat_path = os.path.join(get_app_path(), "update_later.bat")
        subprocess.Popen([bat_path], shell=True)
        return Result(True, data=None)

    except Exception as e:
        logger.error(f"Ошибка обновления: {e}")
        return Result(False, error=str(e))

def extract_zip(zip_path, extract_to):
    """Распаковывает архив в указанную директорию."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        logger.info(f"Архив распакован в {extract_to}")
        return True
    except Exception as e:
        logger.error(f"Ошибка распаковки: {e}")
        return False

def create_update_bat(extracted_dir):
    """Создаёт bat-файл, который подождёт закрытия программы и
    атомарно переместит файлы из extracted_dir в каталог приложения.
    Предыдущий exe будет переименован в .bak на время обмена."""
    bat_code = f"""@echo off
cd /d %~dp0
""" + """timeout /t 3 /nobreak > nul
rem -- если backup уже есть, удаляем его
if exist "Blind_log.exe.bak" del /q "Blind_log.exe.bak"
rem -- переместим текущий exe в backup
if exist "Blind_log.exe" move /Y "Blind_log.exe" "Blind_log.exe.bak"
rem -- копируем новые файлы
xcopy /E /Y "{extracted_dir}\\*" "%~dp0"
rem -- очистка временной папки
rd /s /q "{extracted_dir}"
rem -- удалить весь temp-каталог, если остался
rd /s /q "{os.path.join(get_app_path(), 'temp')}"
rem -- удалить архив, если остался
if exist "{extracted_dir}.zip" del /q "{extracted_dir}.zip"
start "" "Blind_log.exe"
del "%~f0"
"""
    bat_path = os.path.join(get_app_path(), "update_later.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_code)
    logger.info(f"Создан bat-файл: {bat_path}")