# MISTAKES.md

This file records recurring maintenance risks. Re-check each item against the current implementation before treating it as an active defect.

- Do not assume old root-level modules (`gui.py`, `controller.py`, `settings.py`, `qrz_lookup.py`, `exporter.py`, `importer.py`, `nvda_notify.py`) are the implementation locations. Current code is organized into packages such as `gui/`, `controller/`, `settings/`, `services/`, `adif/` and `accessibility/`.
- Avoid broad `except Exception` blocks when a narrower exception type is available. Unexpected errors should retain diagnostic information.
- Do not apply custom colors to native Windows checkboxes; this can alter their accessible role and keyboard interaction.
- Do not force focus into a child control when the user switches the main tabs.
- Keep help text consistent with journal export behavior: without marks in the current displayed list, export the displayed search/filter result, not the entire unfiltered journal.
- Keep date/time controls native; implement segment announcements/navigation in the accessibility helper.
