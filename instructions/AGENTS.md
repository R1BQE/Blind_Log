# AGENTS.md

Blind_Log is a Python desktop logbook for amateur radio QSOs with a keyboard-first UI and NVDA compatibility.

Focus on preserving the existing layered architecture:
* UI layer in `gui.py`
* Controller in `controller.py`
* Business logic in `qso_manager.py`
* Infrastructure in `settings.py`, `settings_storage.py`, `exporter.py`, `importer.py`, `updater.py`, `qrz_lookup.py`, `nvda_notify.py`, `i18n.py`, `logger.py`, `welcome_dialog.py`, `utils.py`, `constants.py`, `transliterator.py`, `update_version.py`

Requirements:
* Do not move business logic into GUI.
* Do not change public behavior or hotkeys.
* Keep localization through `tr(...)` and JSON files in `locales/`.
* Keep settings stored as codes, not translated text. Correct: `"utc"`. Incorrect: `"UTC"`, `"Задать свой часовой пояс"`.
* Preserve keyboard navigation, focus order and NVDA notifications.
* Prefer minimal diff and avoid refactoring without explicit need.
* Test changes with `python -m pytest tests`.
* Maintain backward compatibility for existing settings and saved data.
* Reply to the user in Russian; write code comments in English.
