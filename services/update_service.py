"""Network-only release checks, independent of wxPython dialogs."""

import re
import requests
from localization.i18n import tr, get_resolved_language
from common.changelog import extract_language_section
from common.utils import get_version, Result
from logger import log_updater_error


def version_tuple(value):
    """Parse a strict X.Y.Z version, optionally prefixed with v or V."""
    if not isinstance(value, str):
        raise ValueError("Version must be a string")
    match = re.fullmatch(r"[vV]?(\d+)\.(\d+)\.(\d+)", value.strip())
    if match is None:
        raise ValueError(f"Invalid version: {value!r}")
    return tuple(int(part) for part in match.groups())

def perform_update_check(get_version_fn=None, request_get=None):
    """Проверяет наличие обновлений и возвращает Result без прямого обращения к UI."""
    get_version_fn = get_version_fn or get_version
    request_get = request_get or requests.get
    current_version = get_version_fn()
    if not current_version:
        return Result(False, error=tr("update.version_unknown"))

    try:
        response = request_get(
            "https://api.github.com/repos/R1BQE/Blind_Log/releases/latest",
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        latest_version = data.get("tag_name")
        download_url = None
        expected_sha256 = None

        for asset in data.get("assets", []):
            if asset.get("name", "").lower() == "blind_log.exe":
                download_url = asset.get("browser_download_url")
                digest = asset.get("digest") or ""
                if digest.lower().startswith("sha256:"):
                    expected_sha256 = digest.split(":", 1)[1].lower()
                break



    except requests.RequestException as error:
        # Keep technical details in updater.log; the UI receives a localized,
        # actionable message instead of a raw English requests exception.
        log_updater_error(f"Update check request failed: {error}")
        return Result(False, error=tr("update.connection_error"))

    if not latest_version:
        return Result(False, error=tr("update.version_unknown"))

    try:
        latest_version_parts = version_tuple(latest_version)
        current_version_parts = version_tuple(current_version)
    except ValueError as error:
        # A malformed release tag must not terminate the background update
        # check with an uncaught exception.
        log_updater_error(f"Invalid version received during update check: {error}")
        return Result(False, error=tr("update.invalid_version"))

    if latest_version_parts <= current_version_parts:
        return Result(True, data={
            "update_available": False,
            "current_version": current_version,
        })

    if not download_url or not expected_sha256:
        return Result(False, error=tr("update.no_executable"))

    # Тело релиза двуязычное (English + Русская версия) — берём секцию
    # под язык интерфейса. Зависимости от raw-файлов репозитория нет.
    changelog = extract_language_section(data.get("body") or "", get_resolved_language())

    return Result(True, data={
        "update_available": True,
        "latest_version": latest_version,
        "current_version": current_version,
        "download_url": download_url,
        "expected_sha256": expected_sha256,
        "changelog": changelog,
    })


