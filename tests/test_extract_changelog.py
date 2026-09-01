import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import extract_changelog


def test_extract_first_entry_returns_first_block_without_version_header():
    text = "Version 3.4.12\n- Fixed something\n- Added feature\n\n---\nVersion 3.4.11\n- Old entry\n"
    assert extract_changelog.extract_first_entry(text) == "- Fixed something\n- Added feature"


def test_extract_first_entry_handles_leading_separator():
    text = "---\nVersion 3.4.12\n- Fixed something\n\n---\nVersion 3.4.11\n- Old entry\n"
    assert extract_changelog.extract_first_entry(text) == "- Fixed something"


def test_extract_first_entry_keeps_lines_when_no_version_header():
    text = "Some header\n- line one\n\n---\nVersion 1.0\n- old\n"
    assert extract_changelog.extract_first_entry(text) == "Some header\n- line one"


def test_extract_first_entry_returns_empty_for_blank_block():
    assert extract_changelog.extract_first_entry("") == ""
    assert extract_changelog.extract_first_entry("   \n\n") == ""


def test_main_writes_body_with_russian_link(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "changelog-en.txt").write_text(
        "---\nVersion 3.4.12\n- Fixed the bug\n\n---\nVersion 3.4.11\n- Old\n",
        encoding="utf-8",
    )
    extract_changelog.main()
    output = (tmp_path / "changelog_release.txt").read_text(encoding="utf-8")
    assert output == (
        "- Fixed the bug\n\n"
        "[Русская версия](https://github.com/R1BQE/Blind_Log/blob/main/changelog-ru.txt)"
    )


def test_main_writes_empty_file_when_source_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    extract_changelog.main()
    assert (tmp_path / "changelog_release.txt").read_text(encoding="utf-8") == ""
