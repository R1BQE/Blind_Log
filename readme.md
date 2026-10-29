# Blind_Log

[Русская версия](readme_ru.md)

Blind_Log is a desktop amateur radio logbook application for visually impaired operators.
The application is written in Python with wxPython and uses NVDA-compatible speech output.

## Features

* Add, edit, delete and browse QSO records
* Export the log to ADIF format
* Import ADIF files using `adif-io`
* QRZ.ru callsign lookup for automatic `name` and `city` filling
* Persistent SQLite storage for QSO records with automatic saving
* Transliterate Russian text to Latin for LoTW, eQSL, Club Log
* Automatic update check via GitHub Releases API
* English and Russian interface via JSON localization

## Requirements

* Python 3.x
* wxPython
* requests
* transliterate
* adif-io
* accessible-output3
* pytest (for tests)

Install dependencies from `requirements.txt`:

    python -m pip install -r requirements.txt

## Run from source

From the repository root:

    python main.py

## Build

The repository includes `compile.bat` to build a standalone executable with PyInstaller.
It installs dependencies into the local `.venv` and runs `PyInstaller Blind_log.spec`.

## Settings and data

* Application settings are stored in `settings.ini`
* The QSO journal is stored in `blind_log.db` in the application directory; the unfinished form draft is stored in `qso_draft.json`
* Localization files are in `locales/en.json` and `locales/ru.json`
* Built-in help pages are `help.htm` and `help_en.htm`
* Changelog: `changelog-en.txt` (English), `changelog-ru.txt` (Russian)

ADIF export creates a separate file for exchange and backup; it is not needed to persist records inside the application. An old `blind_log_temp.json` may be migrated to the database on the first launch of the new version. Periodically export the journal to ADIF or copy the closed application's `blind_log.db` file to a safe location.

## Project structure

* `main.py` — application entry point
* `gui.py` — wxPython user interface and dialogs
* `controller.py` — bridge between GUI and business logic
* `journal/manager.py` — QSO data handling and validation
* `journal/storage.py` — persistent SQLite storage for the journal and form draft
* `exporter.py` — ADIF export
* `importer.py` — ADIF import
* `settings.py` — settings manager and settings dialog
* `settings/storage.py` — settings file read/write support
* `welcome_dialog.py` — first-run welcome dialog and settings prompt
* `services/updater.py` — update checking and installer flow
* `qrz_lookup.py` — QRZ.ru API integration
* `nvda_notify.py` — screen reader notifications

## Testing

Run the repository tests with:

    python -m pytest tests

## Help

In-app help is available with **F1**.

