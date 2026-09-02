from changelog import extract_language_section


BILINGUAL = (
    "**English**\n"
    "- Fixed the bug\n"
    "- Added feature\n"
    "\n"
    "**Русская версия**\n"
    "- Исправлена ошибка\n"
    "- Добавлена возможность\n"
)


def test_returns_russian_section_for_ru():
    assert extract_language_section(BILINGUAL, "ru") == (
        "- Исправлена ошибка\n- Добавлена возможность"
    )


def test_returns_english_section_for_en():
    assert extract_language_section(BILINGUAL, "en") == (
        "- Fixed the bug\n- Added feature"
    )


def test_falls_back_to_other_language():
    en_only = "**English**\n- Fixed the bug\n"
    assert extract_language_section(en_only, "ru") == "- Fixed the bug"


def test_returns_whole_body_without_markers():
    plain = "Just a plain text\nwith two lines"
    assert extract_language_section(plain, "ru") == plain


def test_returns_empty_for_empty_body():
    assert extract_language_section("", "ru") == ""
    assert extract_language_section(None, "ru") == ""
