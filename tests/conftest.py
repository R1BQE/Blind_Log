import exporter as exporter_module
import utils
import pytest

class DummySettingsManager:
    def __init__(self, settings=None):
        defaults = {
            'call': 'TESTOP',
            'operator_name': 'Test Operator',
            'my_qth': 'KP00AA',
            'my_city': 'TestCity',
            'my_rig': 'TestRig',
            'my_lat': '55.0',
            'my_lon': '37.0',
            'qrz_username': '',
            'qrz_password': '',
            'use_qrz_lookup': '0',
            'auto_temp': '0',
            'timezone': 'UTC',
            'custom_timezone': '0',
        }
        self.settings = defaults if settings is None else {**defaults, **settings}

    def get_option(self, key, default=None):
        return self.settings.get(key, default)

    def get_visible_fields(self):
        return {
            'call': True,
            'name': True,
            'city': True,
            'qth': True,
            'freq': True,
            'band': True,
            'mode': True,
            'rst_received': True,
            'rst_sent': True,
            'comment': True,
            'date': True,
            'time': True,
        }

    def load_settings(self):
        pass


@pytest.fixture(autouse=True)
def disable_wx_messagebox(monkeypatch):
    monkeypatch.setattr(exporter_module.wx, 'MessageBox', lambda *args, **kwargs: 0)


@pytest.fixture
def settings_manager():
    return DummySettingsManager()


@pytest.fixture
def qso_manager(settings_manager, monkeypatch, tmp_path):
    monkeypatch.setattr(utils, 'get_app_path', lambda: str(tmp_path))
    from qso_manager import QSOManager
    return QSOManager(settings_manager)
