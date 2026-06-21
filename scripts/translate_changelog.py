"""
Заполняет английскую секцию [EN] последней записи changeLog.txt
переводом из русской секции [RU], если [EN] пустая.

Перебирает несколько публичных зеркал LibreTranslate (заданных через
переменную окружения LIBRETRANSLATE_URLS, через запятую) и устойчиво
обрабатывает недоступность или неожиданный формат ответа любого из
них. Если все зеркала недоступны, использует русский текст как
fallback для [EN], чтобы описание релиза никогда не оставалось
пустым.
"""

import os
from pathlib import Path

import requests


urls = [
    u.strip()
    for u in os.environ.get("LIBRETRANSLATE_URLS", "").split(",")
    if u.strip()
]

path = Path("changeLog.txt")

if not path.exists():
    raise SystemExit(0)


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


def translate_via(url, text):
    """Пробует один LibreTranslate-совместимый эндпоинт.

    Возвращает переведённый текст при успехе или None, если этот
    эндпоинт не сработал (недоступен, неверный формат, ошибка и
    т.п.), чтобы вызывающий код перешёл к следующему зеркалу.
    """
    try:
        response = requests.post(
            url,
            json={
                "q": text,
                "source": "ru",
                "target": "en",
                "format": "text",
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
    except Exception as exc:
        print(f"  [skip] {url}: request failed ({exc})")
        return None

    if not response.ok:
        print(f"  [skip] {url}: HTTP {response.status_code}")
        return None

    try:
        data = response.json()
    except Exception:
        print(f"  [skip] {url}: response is not valid JSON")
        return None

    if not isinstance(data, dict):
        print(f"  [skip] {url}: unexpected response format")
        return None

    translated = data.get("translatedText", "")

    if not isinstance(translated, str) or not translated.strip():
        print(f"  [skip] {url}: no translatedText in response")
        return None

    return translated.strip()


def translate(text):
    if not text.strip():
        return ""

    for url in urls:
        print(f"Trying translation mirror: {url}")
        result = translate_via(url, text)

        if result:
            print(f"  [ok] translated via {url}")
            return result

    print("All translation mirrors failed, falling back to Russian text")
    return ""


content = path.read_text(encoding="utf-8")

parts = content.split("---", 1)
first = parts[0]
rest = parts[1] if len(parts) > 1 else ""

sections = parse_sections(first)
ru = sections.get("RU", "")
en = sections.get("EN", "")

if ru and not en:
    translated = translate(ru)

    # Если все зеркала недоступны, используем русский текст как
    # fallback вместо того, чтобы оставлять [EN] пустой секцией -
    # так описание релиза никогда не остаётся без текста.
    if not translated:
        translated = ru

    new_content = "[EN]\n" + translated + "\n\n[RU]\n" + ru + "\n"

    if rest:
        new_content += "\n---" + rest

    path.write_text(new_content, encoding="utf-8")
