"""Download, validate, extract, and launch the application update."""

import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile

import requests

from common.utils import get_app_path, Result
from localization.i18n import tr
from logger import log_user_action, log_error, log_debug, log_exception


def _get_update_temp_root():
    """Return a per-user staging directory outside the application folder."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return os.path.join(local_app_data, "BlindLog", "updates")
    return os.path.join(tempfile.gettempdir(), "BlindLog", "updates")


def _is_safe_zip_member(name):
    """Reject absolute paths and parent traversal in ZIP member names."""
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    meaningful_parts = [part for part in parts if part]
    return (
        bool(normalized)
        and not normalized.startswith("/")
        and not (len(normalized) >= 2 and normalized[1] == ":")
        and all(part != ".." for part in meaningful_parts)
    )


def extract_zip(zip_path, extract_to):
    """Validate and safely extract an update archive."""
    try:
        os.makedirs(extract_to, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as archive:
            unsafe = [item.filename for item in archive.infolist()
                      if not _is_safe_zip_member(item.filename)]
            if unsafe:
                raise ValueError("Archive contains an unsafe file path")
            bad_member = archive.testzip()
            if bad_member is not None:
                raise zipfile.BadZipFile(f"Corrupt archive member: {bad_member}")
            archive.extractall(extract_to)

        new_exe = _find_update_exe(extract_to)
        if not new_exe or os.path.getsize(new_exe) <= 0:
            raise ValueError("The archive does not contain a valid Blind_log.exe")

        log_debug(f"Archive unpacked and validated: {extract_to}")
        return True
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        log_error(f"Unpacking/validation error: {error}")
        return False


def _find_update_exe(directory):
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower() == "blind_log.exe":
                return os.path.join(root, filename)
    return None


def _download_and_update_worker(download_url, parent_frame, progress_callback=None, cancel_event=None):
    """Download and validate the update, then hand installation to PowerShell."""
    temp_dir = None
    response = None
    handed_off = False
    try:
        temp_root = _get_update_temp_root()
        os.makedirs(temp_root, exist_ok=True)
        temp_dir = os.path.join(temp_root, str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=False)
        zip_path = os.path.join(temp_dir, "update.zip")

        log_user_action(f"Downloading update from {download_url}")
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        try:
            total_size = int(response.headers.get("content-length") or 0)
        except (TypeError, ValueError):
            total_size = 0
        if total_size < 0:
            total_size = 0

        downloaded_size = 0
        with open(zip_path, "wb") as archive_file:
            for chunk in response.iter_content(chunk_size=8192):
                if cancel_event is not None and cancel_event.is_set():
                    log_debug("Update download cancelled by user.")
                    return Result(False, error="Download cancelled by user.")
                if not chunk:
                    continue
                archive_file.write(chunk)
                downloaded_size += len(chunk)
                if total_size and progress_callback is not None:
                    percent = min(99, int(downloaded_size * 100 / total_size))
                    progress_callback(
                        percent,
                        tr("update.downloaded_percent").format(percent=percent)
                    )

        if cancel_event is not None and cancel_event.is_set():
            return Result(False, error="Download cancelled by user.")
        if downloaded_size == 0:
            raise IOError("The update archive is empty")
        if total_size and downloaded_size != total_size:
            raise IOError(
                f"Downloaded size mismatch: expected {total_size} bytes, "
                f"received {downloaded_size} bytes"
            )

        log_debug(f"Update archive downloaded: {zip_path} ({downloaded_size} bytes)")
        extract_dir = os.path.join(temp_dir, "new")
        if not extract_zip(zip_path, extract_dir):
            raise ValueError("The update archive is damaged or does not contain Blind_log.exe")

        extracted_exe = _find_update_exe(extract_dir)
        if not extracted_exe:
            raise ValueError("Blind_log.exe was not found in the update archive")

        app_dir = get_app_path()
        ps1_path = create_update_ps1(extract_dir, os.getpid(), app_dir, temp_dir)
        popen_kwargs = {}
        if os.name == "nt":
            popen_kwargs.update({
                "creationflags": subprocess.CREATE_NO_WINDOW,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "stdin": subprocess.DEVNULL,
            })

        subprocess.Popen([
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden",
            "-File", ps1_path,
            "-ExtractedDir", extract_dir,
            "-AppDir", app_dir,
            "-ProcessId", str(os.getpid()),
            "-WorkDir", temp_dir,
        ], **popen_kwargs)

        handed_off = True
        log_user_action("Validated update handed over to external installer")
        return Result(True, data={"installer_started": True, "work_dir": temp_dir})

    except requests.RequestException as error:
        log_error(f"Update download request failed: {error}")
        return Result(False, error=str(error))
    except Exception as error:
        log_exception(f"Unexpected update error: {error}")
        return Result(False, error=str(error))
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        if temp_dir and not handed_off:
            shutil.rmtree(temp_dir, ignore_errors=True)


def create_update_ps1(extracted_dir, pid, app_dir=None, work_dir=None):
    """Create a guarded installer script with logging and rollback."""
    app_dir = app_dir or get_app_path()
    work_dir = work_dir or os.path.dirname(extracted_dir)
    ps1_path = os.path.join(work_dir, "install_update.ps1")
    ps1_code = r'''param(
    [Parameter(Mandatory=$true)][string]$ExtractedDir,
    [Parameter(Mandatory=$true)][string]$AppDir,
    [Parameter(Mandatory=$true)][int]$ProcessId,
    [Parameter(Mandatory=$true)][string]$WorkDir
)

$ErrorActionPreference = "Stop"
$targetExe = Join-Path $AppDir "Blind_log.exe"
$backupExe = Join-Path $AppDir "Blind_log.exe.bak"
$stagedExe = Join-Path $AppDir "Blind_log.exe.new"
$stateDir = Join-Path $env:LOCALAPPDATA "BlindLog"
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$logFile = Join-Path $stateDir "update-install.log"
$statusFile = Join-Path $stateDir "update-status.txt"
$backupCreated = $false

function Write-UpdateLog([string]$Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logFile -Value "$stamp $Message" -Encoding UTF8
}

try {
    Write-UpdateLog "Installer started. PID=$ProcessId"
    if ($ProcessId -gt 0) {
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($process) {
            if (-not $process.WaitForExit(90000)) {
                throw "The application did not exit within 90 seconds."
            }
        }
    }

    $deadline = (Get-Date).AddSeconds(90)
    while ($true) {
        try {
            $stream = [System.IO.File]::Open(
                $targetExe,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
            $stream.Dispose()
            break
        } catch {
            if ((Get-Date) -ge $deadline) {
                throw "The application executable is still locked."
            }
            Start-Sleep -Milliseconds 500
        }
    }

    $newExe = Get-ChildItem -LiteralPath $ExtractedDir -Filter "Blind_log.exe" -Recurse |
        Select-Object -First 1
    if (-not $newExe -or $newExe.Length -le 0) {
        throw "A valid Blind_log.exe was not found in the extracted update."
    }

    Copy-Item -LiteralPath $newExe.FullName -Destination $stagedExe -Force
    if ((Get-Item -LiteralPath $stagedExe).Length -ne $newExe.Length) {
        throw "The staged executable size does not match the downloaded executable."
    }

    if (Test-Path -LiteralPath $backupExe) {
        Remove-Item -LiteralPath $backupExe -Force
    }
    if (Test-Path -LiteralPath $targetExe) {
        Move-Item -LiteralPath $targetExe -Destination $backupExe
        $backupCreated = $true
    }

    Move-Item -LiteralPath $stagedExe -Destination $targetExe
    if (-not (Test-Path -LiteralPath $targetExe)) {
        throw "The new executable was not installed."
    }
    if ((Get-Item -LiteralPath $targetExe).Length -ne $newExe.Length) {
        throw "The installed executable size does not match."
    }

    Set-Content -LiteralPath $statusFile -Value "installed" -Encoding UTF8
    Write-UpdateLog "New executable installed. Starting application."
    Start-Process -FilePath $targetExe
    Write-UpdateLog "Application process started."
    Start-Sleep -Seconds 2
    if (Test-Path -LiteralPath $backupExe) {
        Remove-Item -LiteralPath $backupExe -Force
    }
    Set-Content -LiteralPath $statusFile -Value "started" -Encoding UTF8
    Remove-Item -LiteralPath $WorkDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-UpdateLog "INSTALLATION FAILED: $message"
    try {
        if ($backupCreated -and (Test-Path -LiteralPath $backupExe)) {
            if (Test-Path -LiteralPath $targetExe) {
                Remove-Item -LiteralPath $targetExe -Force
            }
            Move-Item -LiteralPath $backupExe -Destination $targetExe -Force
            Write-UpdateLog "Previous executable restored."
            Start-Process -FilePath $targetExe
        }
    } catch {
        Write-UpdateLog "ROLLBACK FAILED: $($_.Exception.Message)"
    }
    Set-Content -LiteralPath $statusFile -Value "failed" -Encoding UTF8
    exit 1
}
'''
    with open(ps1_path, "w", encoding="utf-8-sig") as script_file:
        script_file.write(ps1_code)
    log_debug(f"PowerShell update installer created: {ps1_path}")
    return ps1_path
