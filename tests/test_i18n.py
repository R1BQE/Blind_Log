import locale
import sys

from i18n import load_translations, get_resolved_language, tr


def test_load_translations_with_unknown_language_falls_back_to_english():
    load_translations('xx')
    assert tr('menu.help') == 'Help'
    assert tr('menu.exit') == 'Exit'


def test_load_translations_auto_uses_system_locale(monkeypatch):
    monkeypatch.setattr(locale, 'getdefaultlocale', lambda: ('en_US', 'UTF-8'))
    load_translations('auto')
    assert tr('menu.help') == 'Help'


def test_resolved_language_returns_explicit_setting():
    load_translations('ru')
    assert get_resolved_language() == 'ru'
    load_translations('en')
    assert get_resolved_language() == 'en'


def test_resolved_language_auto_uses_system_locale(monkeypatch):
    load_translations('auto')
    monkeypatch.setattr(locale, 'getlocale', lambda *a, **k: ('ru_RU', 'UTF-8'))
    assert get_resolved_language() == 'ru'
    monkeypatch.setattr(locale, 'getlocale', lambda *a, **k: ('en_US', 'UTF-8'))
    assert get_resolved_language() == 'en'


def test_resolved_language_auto_uses_windows_ui_language(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    load_translations('auto')
    monkeypatch.setattr('i18n._windows_ui_language', lambda: 'ru')
    assert get_resolved_language() == 'ru'
    monkeypatch.setattr('i18n._windows_ui_language', lambda: 'en')
    assert get_resolved_language() == 'en'


def test_resolved_language_auto_windows_fallback_to_locale(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    load_translations('auto')
    monkeypatch.setattr('i18n._windows_ui_language', lambda: None)
    monkeypatch.setattr(locale, 'getlocale', lambda *a, **k: ('ru_RU', 'UTF-8'))
    assert get_resolved_language() == 'ru'
