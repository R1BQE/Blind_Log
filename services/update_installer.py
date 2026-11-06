"""Download, verify and install a standalone Blind_log.exe update."""

import hashlib
import os
import shutil
import subprocess
import tempfile
import uuid

import requests

from common.utils import get_app_path, Result
from localization.i18n import tr
from logger import (
    log_updater_action, log_updater_error, log_updater_debug, log_updater_exception
)


def _get_update_root():
    """Prefer an update directory beside the application; fall back to LocalAppData."""
    app_update = os.path.join(get_app_path(), "update")
    try:
        os.makedirs(app_update, exist_ok=True)
        probe = os.path.join(app_update, ".write-test")
        with open(probe, "w", encoding="ascii") as stream:
            stream.write("ok")
        os.remove(probe)
        return app_update
    except OSError:
        local_app_data = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        fallback = os.path.join(local_app_data, "BlindLog", "update")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def _valid_windows_executable(path):
    """Check a downloaded file has a Windows PE executable signature."""
    try:
        if os.path.getsize(path) < 64:
            return False
        with open(path, "rb") as stream:
            if stream.read(2) != b"MZ":
                return False
            stream.seek(0x3C)
            offset_bytes = stream.read(4)
            if len(offset_bytes) != 4:
                return False
            pe_offset = int.from_bytes(offset_bytes, "little")
            if pe_offset < 64 or pe_offset > os.path.getsize(path) - 4:
                return False
            stream.seek(pe_offset)
            return stream.read(4) == b"PE\x00\x00"
    except OSError:
        return False


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_and_update_worker(download_url, parent_frame, progress_callback=None,
                                cancel_event=None, expected_sha256=None):
    """Download one EXE, verify its checksum and hand it to the external installer."""
    work_dir = None
    response = None
    handed_off = False
    try:
        if not expected_sha256 or len(expected_sha256) != 64:
            raise ValueError("The release does not provide a valid SHA-256 checksum.")

        update_root = _get_update_root()
        work_dir = os.path.join(update_root, str(uuid.uuid4()))
        os.makedirs(work_dir, exist_ok=False)
        exe_path = os.path.join(work_dir, "Blind_log.exe")

        log_updater_action(f"Downloading update from {download_url}")
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        try:
            total_size = int(response.headers.get("content-length") or 0)
        except (TypeError, ValueError):
            total_size = 0
        total_size = max(0, total_size)

        downloaded_size = 0
        with open(exe_path, "wb") as executable_file:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if cancel_event is not None and cancel_event.is_set():
                    return Result(False, error="Download cancelled by user.")
                if not chunk:
                    continue
                executable_file.write(chunk)
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
            raise IOError("The downloaded executable is empty.")
        if total_size and downloaded_size != total_size:
            raise IOError(
                f"Downloaded size mismatch: expected {total_size} bytes, "
                f"received {downloaded_size} bytes"
            )

        actual_sha256 = _sha256_file(exe_path)
        if actual_sha256.lower() != expected_sha256.lower():
            raise ValueError("SHA-256 checksum mismatch. The downloaded file was rejected.")
        if not _valid_windows_executable(exe_path):
            raise ValueError("The downloaded file is not a valid Windows executable.")

        log_updater_debug(f"Update executable verified: {exe_path} ({downloaded_size} bytes)")
        app_dir = get_app_path()
        confirmation_file = os.path.join(work_dir, "startup-confirmation.txt")
        confirmation_token = uuid.uuid4().hex
        ps1_path = create_update_ps1(
            exe_path, os.getpid(), app_dir, work_dir,
            confirmation_file, confirmation_token
        )

        popen_kwargs = {}
        if os.name == "nt":
            popen_kwargs.update({
                "creationflags": subprocess.CREATE_NO_WINDOW,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "stdin": subprocess.DEVNULL,
            })

        subprocess.Popen([
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
            "-File", ps1_path,
            "-NewExe", exe_path,
            "-AppDir", app_dir,
            "-ProcessId", str(os.getpid()),
            "-WorkDir", work_dir,
            "-ConfirmationFile", confirmation_file,
            "-ConfirmationToken", confirmation_token,
        ], **popen_kwargs)

        handed_off = True
        log_user_action("Verified executable handed over to external installer")
        return Result(True, data={"installer_started": True, "work_dir": work_dir})

    except requests.RequestException as error:
        log_updater_error(f"Update download request failed: {error}")
        return Result(False, error=str(error))
    except Exception as error:
        log_updater_exception(f"Unexpected update error: {error}")
        return Result(False, error=str(error))
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        if work_dir and not handed_off:
            shutil.rmtree(work_dir, ignore_errors=True)


def create_update_ps1(new_exe, pid, app_dir=None, work_dir=None,
                      confirmation_file=None, confirmation_token=None):
    """Create a PowerShell installer with startup confirmation and rollback."""
    app_dir = app_dir or get_app_path()
    work_dir = work_dir or os.path.dirname(new_exe)
    confirmation_file = confirmation_file or os.path.join(work_dir, "startup-confirmation.txt")
    confirmation_token = confirmation_token or uuid.uuid4().hex
    ps1_path = os.path.join(work_dir, "install_update.ps1")
    ps1_code = r'''param(
    [Parameter(Mandatory=$true)][string]$NewExe,
    [Parameter(Mandatory=$true)][string]$AppDir,
    [Parameter(Mandatory=$true)][int]$ProcessId,
    [Parameter(Mandatory=$true)][string]$WorkDir,
    [Parameter(Mandatory=$true)][string]$ConfirmationFile,
    [Parameter(Mandatory=$true)][string]$ConfirmationToken
)

$ErrorActionPreference = "Stop"
$targetExe = Join-Path $AppDir "Blind_log.exe"
$backupExe = Join-Path $AppDir "Blind_log.exe.bak"
$stagedExe = Join-Path $AppDir "Blind_log.exe.new"
$stateDir = Join-Path $env:LOCALAPPDATA "BlindLog"
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    $stateDir = Join-Path $env:TEMP "BlindLog"
}
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$logFile = Join-Path $stateDir "installer.log"
$backupCreated = $false
$newProcess = $null

function Write-UpdateLog([string]$Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logFile -Value "$stamp $Message" -Encoding UTF8
}

try {
    Write-UpdateLog "Installer started. Old PID=$ProcessId"
    if ($ProcessId -gt 0) {
        $oldProcess = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($oldProcess -and -not $oldProcess.WaitForExit(90000)) {
            throw "Blind Log did not close within 90 seconds. Update cancelled."
        }
    }

    $deadline = (Get-Date).AddSeconds(30)
    while ($true) {
        try {
            $stream = [System.IO.File]::Open($targetExe, 'Open', 'ReadWrite', 'None')
            $stream.Dispose()
            break
        } catch {
            if ((Get-Date) -ge $deadline) { throw "The current executable is still locked." }
            Start-Sleep -Milliseconds 300
        }
    }

    if (-not (Test-Path -LiteralPath $NewExe) -or (Get-Item -LiteralPath $NewExe).Length -le 0) {
        throw "The downloaded executable is missing or empty."
    }
    Copy-Item -LiteralPath $NewExe -Destination $stagedExe -Force
    if ((Get-Item -LiteralPath $stagedExe).Length -ne (Get-Item -LiteralPath $NewExe).Length) {
        throw "The staged executable size does not match."
    }

    if (Test-Path -LiteralPath $backupExe) { Remove-Item -LiteralPath $backupExe -Force }
    if (Test-Path -LiteralPath $targetExe) {
        Move-Item -LiteralPath $targetExe -Destination $backupExe
        $backupCreated = $true
    }
    Move-Item -LiteralPath $stagedExe -Destination $targetExe
    Write-UpdateLog "New executable installed; launching for startup confirmation."

    $arguments = '--update-confirmation "' + $ConfirmationFile + '" --update-token ' + $ConfirmationToken
    $newProcess = Start-Process -FilePath $targetExe -ArgumentList $arguments -PassThru

    $deadline = (Get-Date).AddSeconds(60)
    $confirmed = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $ConfirmationFile) {
            $value = (Get-Content -LiteralPath $ConfirmationFile -Raw).Trim()
            if ($value -eq $ConfirmationToken) {
                $confirmed = $true
                break
            }
        }
        if ($newProcess.HasExited) { throw "The new version exited before confirming successful startup." }
        Start-Sleep -Milliseconds 300
    }
    if (-not $confirmed) { throw "The new version did not confirm startup within 60 seconds." }

    Write-UpdateLog "New version confirmed successful initialization."
    if (Test-Path -LiteralPath $backupExe) { Remove-Item -LiteralPath $backupExe -Force }
    Write-UpdateLog "Backup removed. Update completed."

    # A separate PowerShell process removes the working directory after this
    # installer exits, so the running script never tries to delete itself.
    $cleanup = "Start-Sleep -Seconds 2; Remove-Item -LiteralPath '" + $WorkDir.Replace("'", "''") + "' -Recurse -Force -ErrorAction SilentlyContinue"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cleanup))
    Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile", "-EncodedCommand", $encoded)
    exit 0
}
catch {
    Write-UpdateLog "INSTALLATION FAILED: $($_.Exception.Message)"
    try {
        if ($newProcess -and -not $newProcess.HasExited) {
            Stop-Process -Id $newProcess.Id -Force -ErrorAction SilentlyContinue
            Wait-Process -Id $newProcess.Id -Timeout 10 -ErrorAction SilentlyContinue
        }
        if ($backupCreated -and (Test-Path -LiteralPath $backupExe)) {
            if (Test-Path -LiteralPath $targetExe) { Remove-Item -LiteralPath $targetExe -Force }
            Move-Item -LiteralPath $backupExe -Destination $targetExe -Force
            Write-UpdateLog "Previous executable restored."
            Start-Process -FilePath $targetExe
        }
    } catch {
        Write-UpdateLog "ROLLBACK FAILED: $($_.Exception.Message)"
    }
    exit 1
}
'''
    with open(ps1_path, "w", encoding="utf-8-sig") as script_file:
        script_file.write(ps1_code)
    log_debug(f"PowerShell update installer created: {ps1_path}")
    return ps1_path
