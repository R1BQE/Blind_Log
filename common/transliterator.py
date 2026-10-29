"""
Модуль для транслитерации русского текста в латиницу.
Использует библиотеку transliterate для преобразования кириллицы в латиницу.
"""

try:
    import transliterate
    import transliterate.contrib.languages.ru
except ImportError:
    raise ImportError("Library 'transliterate' is not installed. Install it with: pip install transliterate")

def transliterate_russian(text):
    """
    Транслитерирует русский текст в латиницу, если он содержит кириллицу.
    Если текста нет или он не содержит кириллицы, возвращает как есть.

    :param text: Строка для транслитерации
    :return: Транслитерированная строка или оригинал
    """
    if not text:
        return text
    # Проверяем на наличие кириллических символов (базовая проверка)
    if any(ord(char) > 127 and char.isalpha() for char in text):
        try:
            return transliterate.translit(text, 'ru', reversed=True)
        except Exception as e:
            # В случае ошибки транслитерации возвращаем оригинал
            print(f"Transliteration error: {e}")
            return text
    return text