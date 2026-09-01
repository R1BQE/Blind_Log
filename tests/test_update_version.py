import pytest

import update_version as uv


SAMPLE = (
    "filevers=(3, 4, 11, 0),\n"
    "prodvers=(3, 4, 11, 0),\n"
    "StringStruct('FileVersion', '3.4.11'),\n"
    "StringStruct('ProductVersion', '3.4.11'),\n"
    "StringStruct('FileDescription', 'Amateur radio logbook for visually impaired operators'),\n"
)


def test_apply_version_rewrites_numbers():
    out = uv.apply_version(SAMPLE, [4, 12, 1])
    assert "filevers=(4, 12, 1, 0)" in out
    assert "prodvers=(4, 12, 1, 0)" in out
    assert "StringStruct('FileVersion', '4.12.1')" in out
    assert "StringStruct('ProductVersion', '4.12.1')" in out


def test_apply_version_keeps_description():
    out = uv.apply_version(SAMPLE, [4, 12, 1])
    assert "Amateur radio logbook for visually impaired operators" in out


def test_parse_version_arg():
    assert uv._parse_version_arg("4.12.1") == [4, 12, 1]
    with pytest.raises(ValueError):
        uv._parse_version_arg("4.12")
    with pytest.raises(ValueError):
        uv._parse_version_arg("v4.12.1")
    with pytest.raises(ValueError):
        uv._parse_version_arg("abc")


def test_read_current_from_filevers():
    assert uv._read_current("filevers=(3, 4, 11, 0),\n")[:3] == [3, 4, 11]


def test_main_with_explicit_version(tmp_path, monkeypatch):
    test_file = tmp_path / "version.txt"
    test_file.write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setattr(uv, "VERSION_FILE", str(test_file))
    uv.main(["4.12.1"])
    assert "StringStruct('FileVersion', '4.12.1')" in test_file.read_text(encoding="utf-8")


def test_main_without_args_bumps_minor(tmp_path, monkeypatch):
    test_file = tmp_path / "version.txt"
    test_file.write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setattr(uv, "VERSION_FILE", str(test_file))
    uv.main([])
    content = test_file.read_text(encoding="utf-8")
    assert "filevers=(3, 5, 0, 0)" in content
    assert "StringStruct('FileVersion', '3.5.0')" in content
