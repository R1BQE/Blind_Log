"""
Извлекает текст последней записи changelog-en.txt для использования в
качестве описания GitHub Release (английский — основной язык релиза).
В конце добавляет ссылку на русскую версию changelog.

Если файл отсутствует или первая запись пуста — файл-результат остаётся
пустым, а workflow подставляет заглушку с номером версии.

Записываем результат явно в UTF-8, а не через print(): на Windows-
раннерах консоль по умолчанию не всегда использует UTF-8, и вывод
кириллицы через print() при перенаправлении в файл может упасть
с UnicodeEncodeError.
"""

from pathlib import Path

SOURCE = Path("changelog-en.txt")
OUTPUT = Path("changelog_release.txt")
RU_LINK = "https://github.com/R1BQE/Blind_Log/blob/main/changelog-ru.txt"


def extract_first_entry(text):
    """Возвращает текст первой записи (до первого ---) без заголовка версии.

    Устойчив к ведущему разделителю: блоки разделяются маркером ---,
    первым берётся первый непустой блок независимо от того, начинается
    ли файл с разделителя или с заголовка версии.
    """
    blocks = [b for b in text.split("---") if b.strip()]
    if not blocks:
        return ""

    lines = blocks[0].strip().splitlines()
    if lines and lines[0].strip().lower().startswith("version"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def main():
    if SOURCE.exists():
        text = extract_first_entry(SOURCE.read_text(encoding="utf-8"))
    else:
        text = ""

    body = text + "\n\n[Русская версия](%s)" % RU_LINK if text else ""
    OUTPUT.write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
