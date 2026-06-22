"""
Загружает и устанавливает языковой пакет ru->en для Argos Translate.
Запускается отдельным шагом GitHub Actions перед переводом changelog.

Источник: LibreTranslate/LibreTranslate-Models на GitHub (raw.githubusercontent.com)
доступен из GitHub Actions напрямую без блокировок, в отличие от
argos-net.com, который блокирует CI-запросы с кодом 403.
"""

import sys
import urllib.request
import argostranslate.package

PACKAGE_URL = (
    "https://raw.githubusercontent.com/"
    "LibreTranslate/LibreTranslate-Models/main/ru_en.argosmodel"
)
MODEL_FILE = "ru_en.argosmodel"

print(f"Downloading Argos Translate package from: {PACKAGE_URL}")
try:
    urllib.request.urlretrieve(PACKAGE_URL, MODEL_FILE)
except Exception as exc:
    print(f"ERROR: Failed to download language package: {exc}")
    sys.exit(1)

print("Installing language package...")
try:
    argostranslate.package.install_from_path(MODEL_FILE)
except Exception as exc:
    print(f"ERROR: Failed to install language package: {exc}")
    sys.exit(1)

print("Done: ru->en language package installed successfully.")
