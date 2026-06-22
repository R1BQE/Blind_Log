"""
Загружает и устанавливает языковой пакет ru->en для Argos Translate.
Запускается отдельным шагом GitHub Actions перед переводом changelog.
"""

import sys
import urllib.request
import argostranslate.package

PACKAGE_URL = "https://argos-net.com/v1/translate-ru_en-1_9.argosmodel"
MODEL_FILE = "translate-ru_en-1_9.argosmodel"

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
