# AGENTS.md

Blind_Log is a Python desktop logbook for amateur radio QSOs with a keyboard-first UI and NVDA compatibility.

## Project layout
- `gui/`: wxPython user interface and keyboard interaction.
- `controller/`: application controller and GUI-facing commands.
- `journal/`: QSO business logic and persistence.
- `settings/`: settings manager, storage and dialog.
- `adif/`: ADIF import and export.
- `services/`: QRZ lookup and update services.
- `common/`: shared utilities, constants, transliteration, changelog and version helpers.
- `localization/`: translation loader; JSON files remain in `locales/`.
- `accessibility/`: NVDA integration.
- `help/`: localized HTML help.
- `instructions/`: architecture, project map, style guide and development notes.

Requirements:
* Do not move business logic into GUI.
* Do not change public behavior or hotkeys as part of structural changes.
* Keep localization through `tr(...)` and JSON files in `locales/`.
* Keep settings stored as codes, not translated text. Correct: `"utc"`. Incorrect: `"UTC"`, `"Задать свой часовой пояс"`.
* Preserve keyboard navigation, focus order and NVDA notifications.
* Prefer minimal diff and avoid refactoring without explicit need.
* Test changes with `python -m pytest tests`.
* Maintain backward compatibility for existing settings and saved data.
* Reply to the user in Russian; write code comments in English.
