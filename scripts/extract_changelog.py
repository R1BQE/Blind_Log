"""
Извлекает текст последней записи changeLog.txt для использования в
качестве описания GitHub Release.

Предпочитает английскую секцию [EN]; если она отсутствует или пуста
(например, перевод не удался, а русского текста для fallback тоже не
было), использует русскую секцию [RU], чтобы описание релиза
никогда не оставалось пустым.
"""

from pathlib import Path

content = Path("changeLog.txt").read_text(encoding="utf-8")

first_block = content.split("---", 1)[0]


def extract(marker_start, marker_end):
    lines = []
    capture = False

    for line in first_block.splitlines():
        marker = line.strip().upper()

        if marker == marker_start:
            capture = True
            continue

        if marker_end and marker == marker_end:
            break

        if capture:
            lines.append(line)

    return "\n".join(lines).strip()


text = extract("[EN]", "[RU]")

if not text:
    text = extract("[RU]", None)

print(text)
