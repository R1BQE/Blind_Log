import locale

from i18n import load_translations, tr


def test_load_translations_with_unknown_language_falls_back_to_english():
    load_translations('xx')
    assert tr('menu.help') == 'Help'
    assert tr('menu.exit') == 'Exit'


def test_load_translations_auto_uses_system_locale(monkeypatch):
    monkeypatch.setattr(locale, 'getdefaultlocale', lambda: ('en_US', 'UTF-8'))
    load_translations('auto')
    assert tr('menu.help') == 'Help'
