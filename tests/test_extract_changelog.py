import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import extract_changelog

EN = "---\nVersion 4.12.2\n- Fixed something\n- Added feature\n\n---\nVersion 4.12.1\n- Old entry\n"
RU = "---\nВерсия 4.12.2\n- Исправлено что-то\n- Добавлена функция\n\n---\nВерсия 4.12.1\n- Старая запись\n"


def test_extract_first_entry_strips_english_version_header():
    assert extract_changelog.extract_first_entry(EN) == "- Fixed something\n- Added feature"


def test_extract_first_entry_strips_russian_version_header():
    assert extract_changelog.extract_first_entry(RU) == "- Исправлено что-то\n- Добавлена функция"


def test_extract_first_entry_handles_leading_separator():
    text = "---\nVersion 4.12.2\n- Fixed something\n\n---\nVersion 4.12.1\n- Old entry\n"
    assert extract_changelog.extract_first_entry(text) == "- Fixed something"


def test_extract_first_entry_keeps_lines_when_no_version_header():
    text = "Some header\n- line one\n\n---\nVersion 1.0\n- old\n"
    assert extract_changelog.extract_first_entry(text) == "Some header\n- line one"


def test_extract_first_entry_returns_empty_for_blank_block():
    assert extract_changelog.extract_first_entry("") == ""
    assert extract_changelog.extract_first_entry("   \n\n") == ""


def test_build_release_body_contains_both_languages():
    body = extract_changelog.build_release_body("- Fixed", "- Исправлено")
    assert "**English**" in body
    assert "- Fixed" in body
    assert "**Русская версия**" in body
    assert "- Исправлено" in body


def test_build_release_body_handles_missing_entry():
    assert "**English**" in extract_changelog.build_release_body("- Fixed", "")
    assert "**Русская версия**" in extract_changelog.build_release_body("", "- Исправлено")
    assert extract_changelog.build_release_body("", "") == ""


def test_main_writes_bilingual_body(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "changelog-en.txt").write_text(EN, encoding="utf-8")
    (tmp_path / "changelog-ru.txt").write_text(RU, encoding="utf-8")
    extract_changelog.main()
    output = (tmp_path / "changelog_release.txt").read_text(encoding="utf-8")
    assert "**English**" in output
    assert "- Fixed something" in output
    assert "**Русская версия**" in output
    assert "- Исправлено что-то" in output


def test_main_writes_empty_file_when_sources_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    extract_changelog.main()
    assert (tmp_path / "changelog_release.txt").read_text(encoding="utf-8") == ""
