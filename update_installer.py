"""Download, validate, extract, and launch the application update."""

import os
import zipfile
import requests
import subprocess
import shutil
import uuid

from utils import get_app_path, Result
from logger import log_user_action, log_error, log_debug


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
        popen_kwargs = {}
        if os.name == "nt":
            # PowerShell — консольная программа: без CREATE_NO_WINDOW Windows
            # создаёт ей видимое окно, висящее всё время замены файлов.
            # -WindowStyle Hidden окно убирает не всегда, поэтому флаг обязателен.
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            # У процесса без консоли нет stdout/stderr: без перенаправления
            # любая запись в них упадёт с ошибкой дескриптора.
            popen_kwargs["stdout"] = subprocess.DEVNULL
            popen_kwargs["stderr"] = subprocess.DEVNULL
        subprocess.Popen([
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden",
            "-File", ps1_path,
            "-ExtractedDir", extract_subdir,
            "-AppDir", get_app_path(),
            "-ProcessId", str(pid)
        ], **popen_kwargs)
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
        "# Ждём, пока exe реально освободится. PyInstaller onefile держит файл\n"
        "# открытым, пока живы оба его процесса (сторож и приложение). Слепая\n"
        "# пауза в 5 сек этого не гарантировала — exe переименовывался на живом\n"
        "# процессе, и PyInstaller показывал 'Security validation failure'.\n"
        "$targetExe = Join-Path $AppDir \"Blind_log.exe\"\n"
        "$deadline = (Get-Date).AddSeconds(60)\n"
        "while ($true) {\n"
        "    try {\n"
        "        $fs = [System.IO.File]::Open($targetExe, 'Open', 'ReadWrite', 'None')\n"
        "        $fs.Close()\n"
        "        break\n"
        "    } catch {\n"
        "        if ((Get-Date) -gt $deadline) { break }\n"
        "        Start-Sleep -Milliseconds 500\n"
        "    }\n"
        "}\n\n"
        "# Ищем новый exe рекурсивно - не важно как архив распакован\n"
        "$newExe = Get-ChildItem -Path $ExtractedDir -Filter \"Blind_log.exe\" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1\n\n"
        "if (-not $newExe) { exit 1 }\n\n"
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
    # BOM обязателен: Windows PowerShell 5.1 читает .ps1 без BOM как ANSI,
    # и пути с кириллицей (имя пользователя Windows) превращаются в мусор.
    with open(ps1_path, "w", encoding="utf-8-sig") as f:
        f.write(ps1_code)
    log_debug(f"PowerShell update script created: {ps1_path}")
