# Blind_Log

[Русская версия](readme_ru.md)

Blind_Log is a desktop amateur radio logbook application for visually impaired operators.
The application is written in Python with wxPython and uses NVDA-compatible speech output.

## Features

* Add, edit, delete and browse QSO records
* Export the log to ADIF format
* Import ADIF files using `adif-io`
* QRZ.ru callsign lookup for automatic `name` and `city` filling
* Auto-save temporary session and restore after restart
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
* Temporary recovery data is stored in `blind_log_temp.json`
* Localization files are in `locales/en.json` and `locales/ru.json`
* Built-in help pages are `help.htm` and `help_en.htm`
* Changelog is available in `changeLog.txt`

## Project structure

* `main.py` — application entry point
* `gui.py` — wxPython user interface and dialogs
* `controller.py` — bridge between GUI and business logic
* `qso_manager.py` — QSO data handling and validation
* `exporter.py` — ADIF export
* `importer.py` — ADIF import
* `settings.py` — settings manager and settings dialog
* `settings_storage.py` — settings file read/write support
* `welcome_dialog.py` — first-run welcome dialog and settings prompt
* `updater.py` — update checking and installer flow
* `qrz_lookup.py` — QRZ.ru API integration
* `nvda_notify.py` — screen reader notifications

## Testing

Run the repository tests with:

    python -m pytest tests

## Help

In-app help is available with **F1**.

