"""Network-only release checks, independent of wxPython dialogs."""

import requests
from i18n import tr, get_resolved_language
from changelog import extract_language_section
from utils import get_version, Result


def version_tuple(v):
    """Преобразует строку версии в кортеж чисел."""
    return tuple(int(x) for x in v.strip().replace("v", "").split("."))

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

    # Тело релиза двуязычное (English + Русская версия) — берём секцию
    # под язык интерфейса. Зависимости от raw-файлов репозитория нет.
    changelog = extract_language_section(data.get("body") or "", get_resolved_language())

    return Result(True, data={
        "update_available": True,
        "latest_version": latest_version,
        "current_version": current_version,
        "download_url": download_url,
        "changelog": changelog,
    })


