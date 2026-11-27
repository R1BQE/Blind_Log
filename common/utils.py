"""
Общие утилиты: пути к ресурсам, каталог приложения, версия из version.txt.
"""
import os
import re
import sys


class Result:
    """Унифицированный результат операции."""

    def __init__(self, success, data=None, error=None):
        self.success = bool(success)
        self.data = data
        self.error = error

    def __bool__(self):
        return self.success

    def __repr__(self):
        return f"Result(success={self.success}, data={self.data!r}, error={self.error!r})"


def resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу, учитывая запуск из PyInstaller onefile."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_app_path():
    """Возвращает рабочий каталог приложения, включая запуск из временного EXE при обновлении."""
    # Во время автообновления новый EXE запускается из уникального каталога
    # загрузки. Переменная сохраняет доступ к существующим настройкам, БД,
    # журналам и данным Hamlib в постоянном каталоге установки.
    update_app_dir = os.environ.get("BLIND_LOG_APP_DIR")
    if update_app_dir and os.path.isdir(update_app_dir):
        return os.path.abspath(update_app_dir)
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_version():
    """Читает текущую версию из version.txt. Возвращает строку или None при ошибке."""
    try:
        path = resource_path("version.txt")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r"StringStruct\('FileVersion', '(.+?)'\)", content)
        return match.group(1) if match else None
    except Exception:
        return None


def get_version_info():
    """Читает описание, автора и версию из version.txt для диалога «О программе»."""
    result = {
        "description": "Amateur radio logging software",
        "author": "Unknown author",
        "version": "Unknown version",
    }
    try:
        path = resource_path("version.txt")
        if not os.path.exists(path):
            return result
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r"StringStruct\('ProductName', '(.+?)'\)", content)
        if m:
            result["description"] = m.group(1)
        m = re.search(r"StringStruct\('FileVersion', '(.+?)'\)", content)
        if m:
            result["version"] = m.group(1)
        m = re.search(r"StringStruct\('CompanyName', '(.+?)'\)", content)
        if m:
            result["author"] = m.group(1)
    except Exception:
        pass
    return result


def get_data_dir():
    """Return the application directory for the journal database and drafts.

    For a frozen executable this is the directory containing the EXE; when
    running from source it is the directory containing this module.
    """
    path = get_app_path()
    os.makedirs(path, exist_ok=True)
    return path
