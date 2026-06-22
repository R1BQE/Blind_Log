"""
Заполняет английскую секцию [EN] последней записи changeLog.txt
переводом из русской секции [RU], если [EN] пустая.

Использует локальный перевод через библиотеку argostranslate.
Языковой пакет ru->en должен быть установлен заранее отдельным шагом
GitHub Actions (см. .github/workflows/release.yml).

Если перевод не удался по любой причине — скрипт завершается
с ненулевым кодом и понятным сообщением, чтобы сборка явно упала,
а не молча опубликовала релиз без английского описания.
"""

import sys
from pathlib import Path

import argostranslate.package
import argostranslate.translate


FROM_CODE = "ru"
TO_CODE = "en"

path = Path("changeLog.txt")

if not path.exists():
    print("changeLog.txt not found, skipping translation.")
    sys.exit(0)


def parse_sections(text):
    sections = {}
    current = None
    lines = []

    for line in text.splitlines():
        marker = line.strip().upper()

        if marker in ("[EN]", "[RU]"):
            if current:
                sections[current] = "\n".join(lines).strip()
            current = marker[1:-1]
            lines = []
        elif current:
            lines.append(line)

    if current:
        sections[current] = "\n".join(lines).strip()

    return sections


def get_translator():
    """Возвращает объект перевода ru->en из установленных пакетов.

    Завершает процесс с кодом 1, если пакет не установлен — это
    приводит к явному падению шага сборки с понятным сообщением,
    а не к молчаливой публикации релиза без перевода.
    """
    installed = argostranslate.translate.get_installed_languages()
    from_lang = next((l for l in installed if l.code == FROM_CODE), None)
    to_lang = next((l for l in installed if l.code == TO_CODE), None)

    if from_lang is None:
        print(
            f"ERROR: Argos Translate language package '{FROM_CODE}' is not installed.\n"
            f"Make sure the install-argos-package step ran successfully before this step."
        )
        sys.exit(1)

    if to_lang is None:
        print(
            f"ERROR: Argos Translate language package '{TO_CODE}' is not installed.\n"
            f"Make sure the install-argos-package step ran successfully before this step."
        )
        sys.exit(1)

    translator = from_lang.get_translation(to_lang)

    if translator is None:
        print(
            f"ERROR: No translation found from '{FROM_CODE}' to '{TO_CODE}'.\n"
            f"The language packages may be installed, but the ru->en pair is missing."
        )
        sys.exit(1)

    return translator


def translate(text, translator):
    if not text.strip():
        return ""
    try:
        result = translator.translate(text)
        if not result or not result.strip():
            print("ERROR: Argos Translate returned an empty result.")
            sys.exit(1)
        return result.strip()
    except Exception as exc:
        print(f"ERROR: Translation failed: {exc}")
        sys.exit(1)


content = path.read_text(encoding="utf-8")

parts = content.split("---", 1)
first = parts[0]
rest = parts[1] if len(parts) > 1 else ""

sections = parse_sections(first)
ru = sections.get("RU", "")
en = sections.get("EN", "")

if not ru:
    print("No [RU] section found in the latest changelog entry, nothing to translate.")
    sys.exit(0)

if en:
    print("[EN] section already filled, skipping translation.")
    sys.exit(0)

print(f"Translating changelog from {FROM_CODE} to {TO_CODE} using Argos Translate...")
translator = get_translator()
translated = translate(ru, translator)

print("Translation successful.")

new_content = "[EN]\n" + translated + "\n\n[RU]\n" + ru + "\n"

if rest:
    new_content += "\n---" + rest

path.write_text(new_content, encoding="utf-8")
print("changeLog.txt updated.")
