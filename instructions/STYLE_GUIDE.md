# STYLE_GUIDE.md

This guide describes the project-specific coding conventions for Blind_Log.

Python style

* Keep functions small and focused.
* Favor early return and low nesting.
* Use `Result(success, data, error)` for unified operation results.
* Avoid GUI logic in business modules.
* Use explicit imports and avoid wildcard imports.
* Prefer clear error messages and logging over silent exceptions.

Naming

* Use snake_case for functions, methods and variables.
* Use PascalCase for classes.
* Keep settings keys as code strings, not localized labels.
* Keep internal QSO dictionary keys stable: `call`, `name`, `city`, `qth`, `band`, `mode`, `freq`, `rst_received`, `rst_sent`, `comment`, `datetime`.

wxPython rules

* Keep UI creation in `gui.py`, `welcome_dialog.py`, and `settings.py` only.
* Bind events to controller methods through `GUIBridge` when possible.
* Use accelerator tables for shortcuts and preserve them after UI rebuilds.
* Use `wx.adv.DatePickerCtrl` and `wx.adv.TimePickerCtrl` for date/time input.
* Do not perform business validation inside widget event handlers.

Logging and errors

* Use `logger.py` helper functions for application events.
* Do not suppress exceptions silently.
* Record errors with `log_error` and user actions with `log_user_action`.
* Catch specific exceptions when possible; avoid bare `except:`.

Threading and background work

* Background tasks must not directly update UI.
* Use `wx.CallAfter` or controller/bridge callbacks for safe UI updates.
* Keep background operations separate from dialog logic.

Type hints

* Use simple type hints where helpful, but do not over-engineer.
* Document complex return values in docstrings if needed.

Patterns

* `SettingsManager` owns application configuration.
* `ApplicationController` owns the flow between UI and business logic.
* `QSOManager` owns data consistency and validation.
* `Exporter` and `Importer` own serialization formats only.
