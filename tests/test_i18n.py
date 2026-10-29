import locale
import sys

from localization.i18n import load_translations, get_resolved_language, tr


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
    # Test the locale fallback independently of the Windows UI-language API.
    monkeypatch.setattr(sys, 'platform', 'linux')
    load_translations('auto')
    monkeypatch.setattr(locale, 'getlocale', lambda *a, **k: ('ru_RU', 'UTF-8'))
    assert get_resolved_language() == 'ru'
    monkeypatch.setattr(locale, 'getlocale', lambda *a, **k: ('en_US', 'UTF-8'))
    assert get_resolved_language() == 'en'


def test_resolved_language_auto_uses_windows_ui_language(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    load_translations('auto')
    monkeypatch.setattr('localization.i18n._windows_ui_language', lambda: 'ru')
    assert get_resolved_language() == 'ru'
    monkeypatch.setattr('localization.i18n._windows_ui_language', lambda: 'en')
    assert get_resolved_language() == 'en'


def test_resolved_language_auto_windows_fallback_to_locale(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    load_translations('auto')
    monkeypatch.setattr('localization.i18n._windows_ui_language', lambda: None)
    monkeypatch.setattr(locale, 'getlocale', lambda *a, **k: ('ru_RU', 'UTF-8'))
    assert get_resolved_language() == 'ru'

def test_about_and_export_mark_labels_are_localized():
    load_translations("ru")
    assert tr("about.description") == "Журнал радиосвязей для незрячих радиолюбителей."
    assert tr("about.author") == "Автор"
    assert tr("about.version") == "Версия"
    assert tr("journal.mark_export") == "Отметить запись для экспорта"
    assert tr("menu.export_adif") == "Экспорт в ADIF"
    assert tr("journal.undo_success") == "Последнее изменение журнала отменено"

    load_translations("en")
    assert tr("about.description") == "Amateur radio logbook for visually impaired operators."
    assert tr("about.author") == "Author"
    assert tr("about.version") == "Version"
    assert tr("journal.mark_export") == "Mark record for export"
    assert tr("menu.export_adif") == "Export to ADIF"
    assert tr("journal.undo_success") == "Last journal change undone"

