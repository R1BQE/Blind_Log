import configparser
from settings.storage import SettingsStorage


class SettingsManager:
    def __init__(self, storage=None):
        self.storage = storage or SettingsStorage()
        self.config = configparser.ConfigParser()
        self.default_settings = {
            'call': '',
            'operator_name': '',
            'my_qth': '',
            'my_city': '',
            'my_rig': '',
            'my_lat': '',
            'my_lon': '',
            'timezone': 'UTC',
            'custom_timezone': '+0',
            'qrz_username': '',
            'qrz_password': '',
            'use_qrz_lookup': '0',  # По умолчанию все флажки сняты
            'check_updates_on_start': '0',
            'auto_temp': '1',  # автосохранение сессии
            'log_enabled': '1',
            'language': 'auto',
            'journal_sort': 'datetime_desc',
            'transliterate_russian': '0',  # транслитерация русского в латиницу (по умолчанию выкл)
        }
        # Visible fields defaults (1 = visible, 0 = hidden). CALL always visible.
        self.visible_field_names = [
            'call', 'name', 'city', 'qth', 'freq', 'band', 'mode',
            'rst_received', 'rst_sent', 'comment', 'date', 'time'
        ]
        for fname in self.visible_field_names:
            key = f'visible_{fname}'
            # default: call visible, others visible by default
            self.default_settings.setdefault(key, '1' if fname != 'call' else '1')
        self.settings = {}
        # Сохраняем флаг "файл настроек был только что создан" как
        # атрибут, а не только как возвращаемое значение - это
        # позволяет вызывающему коду (main.py) проверить его после
        # создания SettingsManager() без повторного вызова
        # load_settings(), который бы вернул False, так как файл к
        # этому моменту уже существует.
        self.was_just_created = self.load_settings()
        self.apply_logging()

    def load_settings(self):
        """Load settings from storage."""
        self.config, file_created = self.storage.load_config()
        
        if not self.config.has_section('Settings') or file_created:
            # Initialize with defaults
            self.config['Settings'] = self.default_settings
            self.storage.save_config(self.config)
            file_created = True
        
        # Load settings into in-memory dict
        self.settings = {
            key: self.config.get('Settings', key, fallback=value)
            for key, value in self.default_settings.items()
        }
        self.apply_logging()
        return file_created

    def get_option(self, key, default=None):
        return self.settings.get(key, default)

    def get_bool(self, key, default=False):
        """
        Получить настройку как bool.
        
        Поддерживает значения: "1", "0", "true", "false", "yes", "no", True, False
        """
        value = self.settings.get(key, str(default).lower())
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('1', 'true', 'yes')
        return bool(value)

    def get_visible_fields(self):
        """Вернуть словарь видимости полей: { 'call': True, 'name': False, ... }"""
        res = {}
        for fname in getattr(self, 'visible_field_names', []):
            key = f'visible_{fname}'
            res[fname] = self.get_option(key, '1') == '1'
        # Ensure call always visible
        res['call'] = True
        return res

    def set_visible_field(self, field_name: str, visible: bool):
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        key = f'visible_{field_name}'
        val = '1' if visible else '0'
        self.config.set('Settings', key, val)
        self.storage.save_config(self.config)
        # refresh in-memory settings
        self.settings[key] = val

    def save_settings(self, settings):
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        for key, value in settings.items():
            self.config.set('Settings', key, value)
        self.storage.save_config(self.config)
        self.settings = settings.copy()
        self.apply_logging()

    def apply_logging(self):
        """Delegate logging configuration to the central logger module."""
        from logger import init_logger
        init_logger(self)
