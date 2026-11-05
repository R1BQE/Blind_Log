# Blind_Log

[Русская версия](readme_ru.md)

Blind_Log is a keyboard-first desktop amateur radio logbook for visually impaired operators. It is written in Python with wxPython and designed for screen-reader use, including NVDA.

## Features
- Add, edit and delete QSO records; search, sort and filter the journal.
- Store the journal in SQLite and automatically save unfinished form data.
- Import and export ADIF, including selective export using journal marks.
- Look up callsigns through the QRZ.ru XML API.
- Transliterate Russian text to Latin when enabled.
- Choose a light, dark or system-based application theme.
- Configure optional field visibility and interface language.
- Use keyboard shortcuts for journal navigation and QSO entry.
- Check for updates through GitHub Releases.

## Requirements
Python 3.x, wxPython, requests, transliterate, adif-io, accessible-output3 and pytest.

Install dependencies:

    python -m pip install -r requirements.txt

## Run from source

    python main.py

## Build
Use `compile.bat` to prepare the local `.venv` environment and build the standalone Windows executable with PyInstaller and `Blind_log.spec`.

## Settings and data
- Settings: `settings.ini` in the application directory.
- QSO journal: `blind_log.db` in the application directory.
- Unfinished form draft: `qso_draft.json` in the application directory.
- Translations: `locales/en.json` and `locales/ru.json`.
- Built-in help: `help/help.htm` and `help/help_en.htm`.
- Release notes: `changelog-ru.txt` and `changelog-en.txt`.

ADIF export creates a separate file for exchange and backup; it is not required to save records inside Blind_Log. An old `blind_log_temp.json` may be migrated on first launch. For a full backup, close the application before copying `blind_log.db`.

## Project structure
- `main.py` — application entry point.
- `gui/` — wxPython windows, controls, layout and keyboard interaction.
- `controller/` — application flow and commands invoked by the GUI.
- `journal/` — QSO business logic, operations and SQLite storage.
- `settings/` — settings manager, storage and settings dialog.
- `adif/` — ADIF import and export.
- `services/` — QRZ.ru lookup and update services.
- `accessibility/` — screen-reader notifications and date/time segment navigation.
- `common/` — shared utilities, constants, themes, transliteration and version helpers.
- `localization/` and `locales/` — translation loader and JSON translations.
- `help/` — localized HTML help.
- `instructions/` — development documentation.
- `tests/` — automated tests.
- `scripts/` — helper scripts.

## Testing

    python -m pytest tests -q

In-app help is available with **F1**.
