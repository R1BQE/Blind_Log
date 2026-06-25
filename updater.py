import os
import sys
import zipfile
import requests
import subprocess
import shutil
import threading
import webbrowser
import locale
import wx
import uuid

from i18n import tr
from utils import resource_path, get_app_path, get_version, Result
from logger import log_user_action, log_error, log_debug


def _get_ui_language():
    """Возвращает 'RU' или 'EN' на основе текущего языка i18n."""
    import i18n as _i18n
    lang = _i18n._current_lang
    if lang == 'ru':
        return 'RU'
    if lang and lang != 'auto':
        return 'EN'
    # auto - смотрим системный язык
    sys_lang = locale.getlocale()[0] or ''
    return 'RU' if sys_lang.startswith('ru') else 'EN'


def _extract_changelog_for_lang(changelog_text, language):
    """Извлекает секцию changelog нужного языка.
    Формат: блоки разделены ---, внутри маркеры [RU] и [EN]."""
    if not changelog_text:
        return changelog_text
    blocks = [b.strip() for b in changelog_text.split('---') if b.strip()]
    if not blocks:
        return changelog_text.strip()
    selected = []
    for block in blocks:
        sections = {}
        cur_lang = None
        cur_lines = []
        for line in block.splitlines():
            marker = line.strip().upper()
            if marker in ('[EN]', '[RU]'):
                if cur_lang:
                    sections[cur_lang] = '\n'.join(cur_lines).strip()
                cur_lang = marker.strip('[]')
                cur_lines = []
            elif cur_lang:
                cur_lines.append(line)
        if cur_lang:
            sections[cur_lang] = '\n'.join(cur_lines).strip()
        if sections:
            text = sections.get(language, '') or sections.get('RU' if language == 'EN' else 'EN', '')
            if text:
                selected.append(text)
        else:
            selected.append(block)
    return '\n\n---\n\n'.join(selected) if selected else changelog_text.strip()


def version_tuple(v):
    """Преобразует строку версии в кортеж чисел."""
    return tuple(int(x) for x in v.strip().replace("v", "").split("."))

def check_update(parent_frame, silent_if_latest=False):
    """Проверяет наличие обновлений и запускает процесс обновления в фоне."""
    thread = threading.Thread(target=_check_update_worker, args=(parent_frame, silent_if_latest), daemon=True)
    thread.start()
    return thread


CHANGELOG_RAW_URL = "https://raw.githubusercontent.com/R1BQE/Blind_Log/main/changeLog.txt"


def _fetch_changelog_from_repo():
    """Читает changeLog.txt напрямую из репозитория. Возвращает текст или пустую строку."""
    try:
        resp = requests.get(CHANGELOG_RAW_URL, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        log_debug(f"Could not fetch changeLog.txt from repo: {e}")
        return ""


def perform_update_check():
    """Проверяет наличие обновлений и возвращает Result без прямого обращения к UI."""
    current_version = get_version()
    if not current_version:
        return Result(False, error=tr("update.version_unknown"))

    try:
        response = requests.get(
            "https://api.github.com/repos/r1oaz/blind_log/releases/latest",
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        latest_version = data.get("tag_name")
        download_url = None

        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".zip"):
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            return Result(False, error=tr("update.no_archive"))

    except requests.RequestException as e:
        return Result(False, error=tr("update.error").format(error=e))

    if not latest_version:
        return Result(False, error=tr("update.version_unknown"))

    if version_tuple(latest_version) <= version_tuple(current_version):
        return Result(True, data={
            "update_available": False,
            "current_version": current_version,
        })

    # Читаем changelog из файла в репозитории — там есть и [RU] и [EN]
    changelog = _fetch_changelog_from_repo()

    return Result(True, data={
        "update_available": True,
        "latest_version": latest_version,
        "current_version": current_version,
        "download_url": download_url,
        "changelog": changelog,
    })


def _check_update_worker(parent_frame, silent_if_latest):
    result = perform_update_check()

    if not result.success:
        wx.CallAfter(wx.MessageBox, result.error, tr("error.title"), wx.OK | wx.ICON_ERROR)
        return

    update_info = result.data
    if not update_info.get("update_available", False):
        if not silent_if_latest:
            wx.CallAfter(
                wx.MessageBox,
                tr("update.up_to_date").format(version=update_info.get("current_version", "")),
                tr("update.title"),
                wx.OK | wx.ICON_INFORMATION
            )
        return

    wx.CallAfter(
        _show_update_dialog,
        parent_frame,
        update_info["latest_version"],
        update_info["current_version"],
        update_info["changelog"],
        update_info["download_url"]
    )


def _show_update_dialog(parent_frame, latest_version, current_version, changelog, download_url):
    dlg = wx.Dialog(parent_frame, title=tr("update.title"), size=(600, 500))
    vbox = wx.BoxSizer(wx.VERTICAL)
    info = wx.StaticText(dlg, label=tr("update.changelog_info"))
    vbox.Add(info, 0, wx.ALL, 10)
    lang = _get_ui_language()
    changelog_localized = _extract_changelog_for_lang(changelog, lang)
    text_ctrl = wx.TextCtrl(dlg, value=changelog_localized, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    vbox.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 10)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_update = wx.Button(dlg, label=tr("button.update"))
    btn_manual = wx.Button(dlg, label=tr("button.manual_download"))
    btn_cancel = wx.Button(dlg, label=tr("button.cancel"))
    btn_sizer.Add(btn_update, 0, wx.RIGHT, 10)
    btn_sizer.Add(btn_manual, 0, wx.RIGHT, 10)
    btn_sizer.Add(btn_cancel, 0)
    vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
    dlg.SetSizer(vbox)

    result = [None]

    def on_update(evt):
        result[0] = "update"
        dlg.Close()

    def on_manual_download(evt):
        # Не закрываем диалог - пользователь может посмотреть changelog
        # и потом всё-таки нажать "Обновить", если передумает.
        # Ссылка всегда указывает на последний релиз и не зависит от
        # того, ответил ли GitHub API на этот конкретный запрос -
        # поэтому она работает как надёжный запасной вариант, даже
        # если automatic update недоступен по какой-то причине.
        webbrowser.open("https://github.com/r1bqe/Blind_Log/releases/latest/download/Blind_log.zip")

    def on_cancel(evt):
        result[0] = "cancel"
        dlg.Close()

    btn_update.Bind(wx.EVT_BUTTON, on_update)
    btn_manual.Bind(wx.EVT_BUTTON, on_manual_download)
    btn_cancel.Bind(wx.EVT_BUTTON, on_cancel)
    dlg.ShowModal()
    dlg.Destroy()

    if result[0] != "update":
        return

    _start_download_thread(download_url, parent_frame)


def _start_download_thread(download_url, parent_frame):
    progress_dialog = wx.ProgressDialog(
        tr("update.downloading"),
        tr("update.preparing"),
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
    except (OSError, RuntimeError):
        pass

    if not result.success:
        wx.MessageBox(tr("update.error").format(error=result.error), tr("error.title"), wx.OK | wx.ICON_ERROR)
    else:
        # Close main window only if it exists and is visible
        try:
            if parent_frame is not None and parent_frame.IsShown():
                parent_frame.Close()
        except Exception:
            pass


def _download_and_update_worker(download_url, parent_frame, progress_callback=None, cancel_event=None):
    """Загружает архив обновления и сохраняет его на диск."""
    base_temp = os.path.join(get_app_path(), "temp")
    try:
        if os.path.exists(base_temp):
            shutil.rmtree(base_temp)
    except OSError:
        pass
    temp_dir = os.path.join(base_temp, str(uuid.uuid4()))
    zip_path = os.path.join(temp_dir, "update.zip")

    try:
        os.makedirs(temp_dir, exist_ok=True)

        log_user_action(f"Downloading update from {download_url}")
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
                        progress_callback(percent, tr("update.downloaded_percent").format(percent=percent))
                    if cancel_event is not None and cancel_event.is_set():
                        log_debug("Download cancelled by user.")
                        return Result(False, error="Download cancelled by user.")

        log_debug(f"Archive downloaded: {zip_path}")

        if total_size and downloaded_size != total_size:
            raise IOError("File size does not match declared size")

        extract_subdir = os.path.join(temp_dir, "new")
        os.makedirs(extract_subdir, exist_ok=True)
        if not extract_zip(zip_path, extract_subdir):
            return Result(False, error="Archive unpacking error.")

        pid = os.getpid()
        create_update_ps1(extract_subdir, pid)
        ps1_path = os.path.join(get_app_path(), "update_later.ps1")
        subprocess.Popen([
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden",
            "-File", ps1_path,
            "-ExtractedDir", extract_subdir,
            "-AppDir", get_app_path(),
            "-ProcessId", str(pid)
        ])
        return Result(True, data=None)

    except (requests.RequestException, OSError, shutil.Error, zipfile.BadZipFile, subprocess.SubprocessError, ValueError) as e:
        log_error(f"Update error: {e}")
        return Result(False, error=str(e))

def extract_zip(zip_path, extract_to):
    """Распаковывает архив в указанную директорию."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        log_debug(f"Archive unpacked to {extract_to}")
        return True
    except (zipfile.BadZipFile, OSError) as e:
        log_error(f"Unpacking error: {e}")
        return False

def create_update_ps1(extracted_dir, pid):
    """Создаёт PowerShell-скрипт который ждёт завершения процесса,
    рекурсивно ищет новый exe и копирует его на место старого.
    При ошибке автоматически восстанавливает backup."""
    app_dir = get_app_path()
    ps1_code = (
        "# update_later.ps1 - автоматически создаётся при обновлении\n"
        "param(\n"
        f"    [string]$ExtractedDir = \"{extracted_dir}\",\n"
        f"    [string]$AppDir = \"{app_dir}\",\n"
        f"    [int]$ProcessId = {pid}\n"
        ")\n\n"
        "# Ждём завершения основного процесса\n"
        "if ($ProcessId -gt 0) {\n"
        "    try {\n"
        "        $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue\n"
        "        if ($proc) { $proc.WaitForExit(15000) }\n"
        "    } catch {}\n"
        "}\n\n"
        "# Пауза чтобы PyInstaller успел очистить временную папку _MEI\n"
        "Start-Sleep -Seconds 5\n\n"
        "# Ищем новый exe рекурсивно - не важно как архив распакован\n"
        "$newExe = Get-ChildItem -Path $ExtractedDir -Filter \"Blind_log.exe\" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1\n\n"
        "if (-not $newExe) { exit 1 }\n\n"
        "$targetExe = Join-Path $AppDir \"Blind_log.exe\"\n"
        "$backupExe = Join-Path $AppDir \"Blind_log.exe.bak\"\n\n"
        "# Удаляем старый backup если есть\n"
        "if (Test-Path $backupExe) { Remove-Item $backupExe -Force -ErrorAction SilentlyContinue }\n\n"
        "# Переименовываем текущий exe в backup\n"
        "if (Test-Path $targetExe) { Move-Item $targetExe $backupExe -Force }\n\n"
        "# Копируем новый exe на место\n"
        "Copy-Item $newExe.FullName $targetExe -Force\n\n"
        "if (Test-Path $targetExe) {\n"
        "    # Удаляем temp папку\n"
        "    Remove-Item -Path (Join-Path $AppDir \"temp\") -Recurse -Force -ErrorAction SilentlyContinue\n"
        "    # Запускаем обновлённую программу\n"
        "    Start-Process $targetExe\n"
        "} else {\n"
        "    # Что-то пошло не так - восстанавливаем из backup\n"
        "    if (Test-Path $backupExe) {\n"
        "        Move-Item $backupExe $targetExe -Force\n"
        "        Start-Process $targetExe\n"
        "    }\n"
        "    exit 1\n"
        "}\n\n"
        "# Удаляем себя\n"
        "$self = $MyInvocation.MyCommand.Path\n"
        "Start-Sleep -Seconds 1\n"
        "Remove-Item $self -Force -ErrorAction SilentlyContinue\n"
    )
    ps1_path = os.path.join(app_dir, "update_later.ps1")
    with open(ps1_path, "w", encoding="utf-8") as f:
        f.write(ps1_code)
    log_debug(f"PowerShell update script created: {ps1_path}")
