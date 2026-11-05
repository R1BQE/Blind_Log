# AGENTS.md

Blind_Log is a Python desktop logbook for amateur radio QSOs. Its interface is keyboard-first and designed for screen-reader compatibility.

## Project layout
- `gui/`: wxPython windows, QSO form, journal, dialogs and keyboard interaction.
- `controller/`: application controller and GUI-facing actions.
- `journal/`: QSO business logic and persistence.
- `settings/`: settings manager, storage and settings dialog. User settings `settings.ini` remains in the project root.
- `adif/`: ADIF import and export.
- `services/`: QRZ.ru lookup and update services.
- `common/`: shared utilities, constants, themes, transliteration and version helpers.
- `localization/`: translation loader; JSON files remain in `locales/`.
- `accessibility/`: screen-reader notifications and date/time segment navigation.
- `help/`: localized HTML help.
- `instructions/`: development documentation.

## Requirements
- Do not move business logic into GUI modules.
- Do not change public behavior, hotkeys, focus order or screen-reader announcements without an explicit task.
- Preserve keyboard navigation and native Windows control accessibility. Do not custom-color native checkboxes.
- Keep localization through `tr(...)` and JSON files in `locales/`.
- Keep settings stored as stable codes, not translated text.
- Preserve compatibility with existing settings and saved user data.
- Keep native wxPython date/time pickers; segment navigation belongs in `accessibility/datetime_segments.py`.
- Test changes with `python -m pytest tests -q`.
- Update both Russian and English user documentation when behavior changes.
- Reply to the user in Russian; write code comments in English.
