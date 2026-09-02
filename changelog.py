"""Разбор двуязычного тела релиза на секции по языку.

Тело релиза формируется на этапе публикации (scripts/extract_changelog.py)
и содержит секции с заголовками ``**English**`` и ``**Русская версия**``.
Функция извлекает секцию под язык интерфейса и умеет откатываться на
другой язык или на весь текст, если разметки нет.
"""

LANG_HEADERS = {
    "en": {"english"},
    "ru": {"русская версия", "russian"},
}


def _header_key(line):
    return line.strip().strip("*#").strip().lower()


def extract_language_section(body, lang):
    """Возвращает секцию тела релиза для языка 'ru'/'en'.

    Приоритет: секция запрошенного языка, затем секция другого языка,
    затем весь текст целиком (для тел без разметки).
    """
    if not body:
        return ""
    if not lang:
        lang = "en"

    current = None
    sections = {"en": [], "ru": []}
    for raw in body.splitlines():
        key = _header_key(raw)
        if key in LANG_HEADERS["en"]:
            current = "en"
            continue
        if key in LANG_HEADERS["ru"]:
            current = "ru"
            continue
        if current:
            sections[current].append(raw)

    for code in (lang, "en" if lang == "ru" else "ru"):
        text = "\n".join(sections[code]).strip()
        if text:
            return text
    return body.strip()
