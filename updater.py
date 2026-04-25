import os
import sys
import zipfile
import requests
import subprocess
import shutil
import logging
import wx
import uuid

from utils import resource_path, get_app_path, get_version

logger = logging.getLogger(__name__)


def version_tuple(v):
    """Преобразует строку версии в кортеж чисел."""
    return tuple(int(x) for x in v.strip().replace("v", "").split("."))

def check_update(parent_frame, silent_if_latest=False):
    """Проверяет наличие обновлений и запускает процесс обновления."""
    current_version = get_version()

    if not current_version:
        wx.CallAfter(wx.MessageBox, "Не удалось определить текущую версию.", "Ошибка", wx.ICON_ERROR)
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
            wx.CallAfter(wx.MessageBox, "Не удалось найти архив обновления.", "Ошибка", wx.ICON_ERROR)
            return

    except requests.RequestException as e:
        wx.CallAfter(wx.MessageBox, f"Ошибка при получении обновления:\n{e}", "Ошибка", wx.ICON_ERROR)
        return

    if version_tuple(latest_version) <= version_tuple(current_version):
        if not silent_if_latest:
            wx.CallAfter(wx.MessageBox, f"У вас уже установлена последняя версия: {current_version}", "Обновление", wx.ICON_INFORMATION)
        return

    # Показываем changelog пользователю
    dlg = wx.Dialog(parent_frame, title=f"Доступна новая версия {latest_version} (у вас {current_version})", size=(600, 500))
    vbox = wx.BoxSizer(wx.VERTICAL)
    info = wx.StaticText(dlg, label="Что нового в этой версии:")
    vbox.Add(info, 0, wx.ALL, 10)
    text_ctrl = wx.TextCtrl(dlg, value=changelog, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
    vbox.Add(text_ctrl, 1, wx.EXPAND|wx.ALL, 10)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_update = wx.Button(dlg, label="Обновить")
    btn_cancel = wx.Button(dlg, label="Отмена")
    btn_sizer.Add(btn_update, 0, wx.RIGHT, 10)
    btn_sizer.Add(btn_cancel, 0)
    vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER|wx.ALL, 10)
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

    # Загружаем и обновляем
    download_and_update(download_url, parent_frame)

def download_and_update(download_url, parent_frame):
    """Загружает архив обновления и выполняет обновление."""
    #стройка temp: уникальный подкаталог чтобы не мешать старым остаткам
    base_temp = os.path.join(get_app_path(), "temp")
    # очищаем предыдущие временные директории
    try:
        if os.path.exists(base_temp):
            shutil.rmtree(base_temp)
    except Exception:
        pass
    temp_dir = os.path.join(base_temp, str(uuid.uuid4()))
    zip_path = os.path.join(temp_dir, "update.zip")

    try:
        # Создаём временную папку
        os.makedirs(temp_dir, exist_ok=True)

        # Создаём диалог прогресса
        progress_dialog = wx.ProgressDialog(
            "Загрузка обновления",
            "Подготовка к загрузке...",
            maximum=100,
            parent=parent_frame,
            style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT
        )

        # Загружаем архив
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
                    if total_size > 0:
                        percent = int(downloaded_size * 100 / total_size)
                        keep_going = progress_dialog.Update(percent, f"Загружено {percent}%")
                        if not keep_going:
                            progress_dialog.Destroy()
                            logger.info("Загрузка отменена пользователем.")
                            return
        progress_dialog.Destroy()
        logger.info(f"Архив загружен: {zip_path}")

        # проверка целостности: размер совпадает с заголовком
        if total_size and downloaded_size != total_size:
            raise IOError("Размер файла не совпадает с объявленным")

        # Распаковываем архив в новую подпапку
        extract_subdir = os.path.join(temp_dir, "new")
        os.makedirs(extract_subdir, exist_ok=True)
        if not extract_zip(zip_path, extract_subdir):
            wx.CallAfter(wx.MessageBox, "Ошибка распаковки архива.", "Ошибка", wx.ICON_ERROR)
            return

        # Готовим bat-скрипт, который атомарно заменит файлы
        create_update_bat(extract_subdir)

        # Запускаем бат-файл и закрываем программу
        bat_path = os.path.join(get_app_path(), "update_later.bat")
        subprocess.Popen([bat_path], shell=True)
        parent_frame.Close()

    except Exception as e:
        logger.error(f"Ошибка обновления: {e}")
        wx.CallAfter(wx.MessageBox, f"Ошибка обновления:\n{e}", "Ошибка", wx.ICON_ERROR)

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