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
