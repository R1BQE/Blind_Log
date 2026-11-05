# STYLE_GUIDE.md

This guide describes the project-specific coding conventions for Blind_Log.

## Python style
- Keep functions small and focused.
- Favor early return and low nesting.
- Use `Result(success, data, error)` where that pattern is already established.
- Keep GUI logic out of business modules.
- Use explicit imports and avoid wildcard imports.
- Prefer clear error messages and useful logging over silent exception handling.

## Naming
- Use snake_case for functions, methods and variables; PascalCase for classes.
- Keep settings keys as code strings, not localized labels.
- Keep internal QSO dictionary keys stable: `call`, `name`, `city`, `qth`, `band`, `mode`, `freq`, `rst_received`, `rst_sent`, `comment`, `datetime`.

## wxPython and GUI
- Put window and control implementation in the appropriate modules under `gui/`.
- Settings UI belongs in `settings/dialog.py`; persistence and defaults belong in `settings/`.
- Preserve keyboard shortcuts after UI rebuilds.
- Keep `wx.adv.DatePickerCtrl` and `wx.adv.TimePickerCtrl` as native controls.
- Do not perform business validation inside widget event handlers.
- Do not forcibly redirect focus when switching the main tabs.
- Do not apply custom colors to native Windows checkboxes.

## Accessibility
- Treat keyboard navigation and screen-reader output as functional requirements.
- Announce meaningful state changes without unnecessary repetition.
- Date/time segment navigation belongs in `accessibility/datetime_segments.py`.
- Test focus order, accessible role/state and NVDA output after GUI changes.

## Logging and threading
- Use the project's logging helpers in `logger.py`; do not suppress unexpected exceptions silently.
- Background tasks must not directly update UI controls. Use `wx.CallAfter` or established controller/bridge callbacks.

## Existing responsibilities
- `SettingsManager` owns application configuration.
- `ApplicationController` coordinates GUI actions and business logic.
- `QSOManager` owns QSO data consistency and validation.
- `adif/Exporter` and `adif/Importer` own ADIF serialization and parsing.
- `common/theme.py` resolves and applies the application color theme.
