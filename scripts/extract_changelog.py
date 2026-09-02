"""
Собирает двуязычное описание GitHub Release из последних записей
changelog-en.txt (English) и changelog-ru.txt (Русская версия).

Тело содержит секции с заголовками ``**English**`` и ``**Русская версия**``.
Программа при обновлении вырезает нужную секцию по языку интерфейса
(changelog.extract_language_section).

Если файлы отсутствуют или последние записи пусты — файл-результат
остаётся пустым, а workflow подставляет заглушку с номером версии.

Записываем результат явно в UTF-8, а не через print(): на Windows-
раннерах консоль по умолчанию не всегда использует UTF-8, и вывод
кириллицы через print() при перенаправлении в файл может упасть
с UnicodeEncodeError.
"""

from pathlib import Path

SOURCE_EN = Path("changelog-en.txt")
SOURCE_RU = Path("changelog-ru.txt")
OUTPUT = Path("changelog_release.txt")


def _read_optional(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def extract_first_entry(text):
    """Возвращает текст первой записи (до первого ---) без заголовка версии.

    Устойчив к ведущему разделителю и к заголовкам обоих языков
    (Version / Версия).
    """
    blocks = [b for b in text.split("---") if b.strip()]
    if not blocks:
        return ""

    lines = blocks[0].strip().splitlines()
    if lines:
        first = lines[0].strip().lower()
        if first.startswith("version") or first.startswith("версия"):
            lines = lines[1:]
    return "\n".join(lines).strip()


def build_release_body(en_entry, ru_entry):
    """Собирает двуязычное тело релиза из записей обоих языков."""
    sections = []
    if en_entry:
        sections.append("**English**\n\n" + en_entry)
    if ru_entry:
        sections.append("**Русская версия**\n\n" + ru_entry)
    return "\n\n".join(sections)


def main():
    en_text = _read_optional(SOURCE_EN)
    ru_text = _read_optional(SOURCE_RU)
    body = build_release_body(
        extract_first_entry(en_text),
        extract_first_entry(ru_text),
    )
    OUTPUT.write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
