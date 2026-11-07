import configparser

import pytest

from settings.storage import SettingsStorage


def test_malformed_settings_raise_error_instead_of_returning_empty_config(tmp_path):
    path = tmp_path / "settings.ini"
    path.write_text("[Settings\ncall = R1BQE\n", encoding="utf-8")

    storage = SettingsStorage(str(path))

    with pytest.raises(OSError, match="Cannot read settings file"):
        storage.load_config()


def test_legacy_cp1251_settings_are_still_supported(tmp_path):
    path = tmp_path / "settings.ini"
    path.write_bytes("[Settings]\noperator_name = Иван\n".encode("cp1251"))

    config, created = SettingsStorage(str(path)).load_config()

    assert created is False
    assert config.get("Settings", "operator_name") == "Иван"



def test_theme_setting_defaults_to_system_and_can_be_saved(tmp_path):
    from settings.manager import SettingsManager

    storage = SettingsStorage(str(tmp_path / "settings.ini"))
    manager = SettingsManager(storage=storage)

    assert manager.get_option("theme") == "system"

    manager.save_settings({**manager.settings, "theme": "dark"})
    manager.load_settings()

    assert manager.get_option("theme") == "dark"



def test_settings_save_failure_preserves_previous_file_and_cleans_temp(
    tmp_path, monkeypatch
):
    import settings.storage as settings_storage

    path = tmp_path / "settings.ini"
    path.write_text("[Settings]\\ncall = R1BQE\\n", encoding="utf-8")
    config = configparser.ConfigParser()
    config["Settings"] = {"call": "NEW"}

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(settings_storage.os, "replace", fail_replace)

    with pytest.raises(IOError, match="simulated replace failure"):
        SettingsStorage(str(path)).save_config(config)

    assert path.read_text(encoding="utf-8") == "[Settings]\\ncall = R1BQE\\n"
    assert list(tmp_path.glob("settings.ini.*.tmp")) == []


def test_settings_save_creates_missing_parent_directory(tmp_path):
    path = tmp_path / "nested" / "settings.ini"
    config = configparser.ConfigParser()
    config["Settings"] = {"call": "R1BQE"}

    SettingsStorage(str(path)).save_config(config)

    loaded, created = SettingsStorage(str(path)).load_config()
    assert created is False
    assert loaded.get("Settings", "call") == "R1BQE"
